from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from voice2task.schemas import (
    PRIVATE_IP_RE,
    PRIVATE_PATH_RE,
    SECRET_RE,
    BrowserTaskContract,
    as_contract,
    validate_contract_status,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SessionStatus(str, Enum):
    CREATED = "CREATED"
    INPUT_RECEIVED = "INPUT_RECEIVED"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSCRIPT_READY = "TRANSCRIPT_READY"
    INFERRING = "INFERRING"
    CONTRACT_READY = "CONTRACT_READY"
    CONTRACT_REJECTED = "CONTRACT_REJECTED"
    PLAN_READY = "PLAN_READY"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATUSES = frozenset(
    {
        SessionStatus.COMPLETED,
        SessionStatus.BLOCKED,
        SessionStatus.CLARIFICATION_REQUIRED,
        SessionStatus.FAILED,
        SessionStatus.CANCELLED,
    }
)


class EventType(str, Enum):
    SESSION_CREATED = "SESSION_CREATED"
    INPUT_RECEIVED = "INPUT_RECEIVED"
    AUDIO_ACCEPTED = "AUDIO_ACCEPTED"
    ASR_STARTED = "ASR_STARTED"
    ASR_COMPLETED = "ASR_COMPLETED"
    ASR_FAILED = "ASR_FAILED"
    TRANSCRIPT_CONFIRMED = "TRANSCRIPT_CONFIRMED"
    TRANSCRIPT_EDITED = "TRANSCRIPT_EDITED"
    INFERENCE_STARTED = "INFERENCE_STARTED"
    INFERENCE_COMPLETED = "INFERENCE_COMPLETED"
    CONTRACT_VALIDATED = "CONTRACT_VALIDATED"
    CONTRACT_REJECTED = "CONTRACT_REJECTED"
    PLAN_COMPILED = "PLAN_COMPILED"
    POLICY_ALLOWED = "POLICY_ALLOWED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    CONFIRMATION_ACCEPTED = "CONFIRMATION_ACCEPTED"
    CONFIRMATION_REJECTED = "CONFIRMATION_REJECTED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    ACTION_STARTED = "ACTION_STARTED"
    ACTION_COMPLETED = "ACTION_COMPLETED"
    ACTION_FAILED = "ACTION_FAILED"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    SESSION_FAILED = "SESSION_FAILED"
    SESSION_CANCELLED = "SESSION_CANCELLED"


class ActionKind(str, Enum):
    NAVIGATE = "navigate"
    FILL = "fill"
    CLICK = "click"
    EXTRACT_TEXT = "extract_text"


class CheckType(str, Enum):
    URL_MATCHES = "url_matches"
    FIELD_VALUE_EQUALS = "field_value_equals"
    TEXT_EQUALS = "text_equals"
    RESULTS_CONTAIN = "results_contain"
    NO_EXECUTION = "no_execution"


class SafetyPayload(StrictModel):
    allow: bool
    reason: str = Field(min_length=1)


class BrowserTaskContractPayload(StrictModel):
    task_type: Literal["search", "navigate", "form_fill", "extract", "clarify", "blocked"]
    route: Literal["search_web", "open_url", "fill_form", "extract_page", "clarify", "deny"]
    safety: SafetyPayload
    confirmation_required: bool
    slots: dict[str, Any]
    normalized_command: str = Field(min_length=1)
    language: Literal["zh-CN"] = "zh-CN"
    contract_version: Literal["v1"] = "v1"

    @model_validator(mode="after")
    def validate_domain_contract(self) -> BrowserTaskContractPayload:
        status = validate_contract_status(self.model_dump())
        if not status["strict_schema_valid"]:
            raise ValueError(f"contract schema invalid: {status['validation_error']}")
        if not status["semantic_valid"]:
            raise ValueError(f"contract semantic invalid: {status['semantic_issues']}")
        return self

    @property
    def validation_status(self) -> dict[str, Any]:
        return validate_contract_status(self.model_dump())

    def to_domain(self) -> BrowserTaskContract:
        return as_contract(self.model_dump())


class Profile(StrictModel):
    email: str = Field(default="demo@example.com", min_length=3, max_length=320)


class SessionContext(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)
    profile: Profile = Field(default_factory=Profile)
    selected_capability: str | None = Field(default=None, max_length=128)
    plan_version: int = Field(default=1, ge=1)
    plan_issued_at: datetime

    @model_validator(mode="after")
    def require_timezone(self) -> SessionContext:
        if self.plan_issued_at.tzinfo is None:
            raise ValueError("plan_issued_at must be timezone-aware")
        return self


class ExecutionAction(StrictModel):
    action_id: str = Field(min_length=1, max_length=128)
    kind: ActionKind
    capability_id: str = Field(min_length=1, max_length=128)
    locator_id: str | None = Field(default=None, max_length=128)
    value_source: str | None = Field(default=None, max_length=128)
    timeout_ms: int = Field(default=5000, ge=100, le=5000)


class Postcondition(StrictModel):
    check_type: CheckType
    capability_id: str = Field(min_length=1, max_length=128)
    locator_id: str | None = Field(default=None, max_length=128)
    expected_source: str | None = Field(default=None, max_length=128)


class ExecutionPlan(StrictModel):
    plan_id: str = Field(min_length=8, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    plan_version: int = Field(ge=1)
    route: str = Field(min_length=1, max_length=64)
    capability_id: str | None = Field(default=None, max_length=128)
    requires_confirmation: bool
    actions: list[ExecutionAction] = Field(max_length=5)
    postconditions: list[Postcondition]
    max_actions: int = Field(default=5, ge=0, le=5)
    expires_at: datetime

    @model_validator(mode="after")
    def validate_action_limit(self) -> ExecutionPlan:
        if len(self.actions) > self.max_actions:
            raise ValueError("plan exceeds max_actions")
        return self


class CompileResult(StrictModel):
    outcome: Literal["ready", "blocked", "clarification_required", "rejected"]
    plan: ExecutionPlan | None = None
    reason_code: str | None = None
    message: str


class PolicyResult(StrictModel):
    allowed: bool
    requires_confirmation: bool
    reason_code: str
    message: str


class VerificationCheck(StrictModel):
    check_type: CheckType
    passed: bool
    expected: str
    observed: str
    evidence_ref: str | None = None


class VerificationResult(StrictModel):
    passed: bool
    checks: list[VerificationCheck]
    failure_code: str | None = None

    @model_validator(mode="after")
    def checks_match_result(self) -> VerificationResult:
        if self.passed != all(check.passed for check in self.checks):
            raise ValueError("verification result must match all checks")
        return self


class ExecutionEvent(StrictModel):
    session_id: str
    seq: int = Field(ge=1)
    event_type: EventType
    stage: str
    status: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class InferenceResult(StrictModel):
    contract: BrowserTaskContractPayload
    inference_mode: Literal["fixture", "private_model"]
    schema_valid: bool = True
    semantic_valid: bool = True
    retry_attempted: bool = False


class ASRResult(StrictModel):
    text: str = Field(min_length=1)
    language: str = "zh"
    segments: list[dict[str, Any]] = Field(default_factory=list)
    duration_ms: int = Field(default=0, ge=0)
    provider: str


class AudioInput(StrictModel):
    content: bytes
    mime_type: str
    fixture_id: str | None = None


class ArtifactRecord(StrictModel):
    id: str
    session_id: str
    kind: str
    relative_path: str
    sha256: str
    created_at: datetime


class ExecutionOutcome(StrictModel):
    browser_context_created: bool
    action_count: int = Field(ge=0)
    final_url_path: str | None = None
    values: dict[str, str] = Field(default_factory=dict)
    screenshots: list[str] = Field(default_factory=list)
    elapsed_ms: int = Field(default=0, ge=0)


class SessionRecord(StrictModel):
    id: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus
    input_kind: str
    context: SessionContext
    transcript_original: str | None = None
    transcript: str | None = None
    transcript_edited: bool = False
    inference_mode: str
    asr_mode: str
    execution_mode: str
    contract: dict[str, Any] | None = None
    contract_validation: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    error_code: str | None = None
    plan_version: int = 1
    confirmation_status: str = "not_required"
    confirmation_token_hash: str | None = Field(default=None, exclude=True)
    confirmation_plan_id: str | None = None
    confirmation_expires_at: datetime | None = None
    confirmation_consumed_at: datetime | None = None
    execution_claimed: bool = False
    cancel_requested: bool = False
    last_event_seq: int = 0


_HOST_RE = re.compile(r"\b(?:host|hostname)=[^\s,;]+", re.IGNORECASE)
_PID_RE = re.compile(r"\bpid=\d+", re.IGNORECASE)
_GPU_UUID_RE = re.compile(r"\bGPU-[0-9a-f-]{16,}\b", re.IGNORECASE)
_DROP_KEYS = frozenset({"traceback", "stack", "stacktrace", "raw_selector", "selector"})


def sanitize_public_text(value: str) -> str:
    sanitized = PRIVATE_PATH_RE.sub("<private_path>", value)
    sanitized = PRIVATE_IP_RE.sub("<private_ip>", sanitized)
    sanitized = SECRET_RE.sub("<secret>", sanitized)
    sanitized = _HOST_RE.sub("host=<redacted>", sanitized)
    sanitized = _PID_RE.sub("pid=<redacted>", sanitized)
    sanitized = _GPU_UUID_RE.sub("<gpu_uuid>", sanitized)
    return sanitized


def sanitize_public_payload(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_public_text(value)
    if isinstance(value, dict):
        return {
            sanitize_public_text(str(key)): sanitize_public_payload(item)
            for key, item in value.items()
            if str(key).lower() not in _DROP_KEYS
        }
    if isinstance(value, list):
        return [sanitize_public_payload(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_public_payload(item) for item in value]
    return value
