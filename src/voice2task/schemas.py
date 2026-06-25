from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


class ValidationError(ValueError):
    """Raised when a row or contract violates the Voice2Task contract."""


SPLITS = {"train", "dev", "test"}
TASK_TYPES = {"search", "navigate", "form_fill", "extract", "clarify", "blocked"}
ROUTES = {"search_web", "open_url", "fill_form", "extract_page", "clarify", "deny"}
CONTRACT_FIELDS = {
    "task_type",
    "route",
    "safety",
    "confirmation_required",
    "slots",
    "normalized_command",
    "language",
    "contract_version",
}
TASK_TYPE_SEMANTICS: dict[str, dict[str, Any]] = {
    "search": {
        "route": "search_web",
        "safety_allow": True,
        "safety_reason": "public_readonly",
        "confirmation_required": False,
        "required_slots": ("query",),
    },
    "navigate": {
        "route": "open_url",
        "safety_allow": True,
        "safety_reason": "public_readonly",
        "confirmation_required": False,
        "required_slots": ("url",),
    },
    "form_fill": {
        "route": "fill_form",
        "safety_allow": True,
        "safety_reason": "requires_confirmation",
        "confirmation_required": True,
        "required_slots": ("field",),
    },
    "extract": {
        "route": "extract_page",
        "safety_allow": True,
        "safety_reason": "public_readonly",
        "confirmation_required": False,
        "required_slots": ("target",),
    },
    "clarify": {
        "route": "clarify",
        "safety_allow": True,
        "safety_reason": "ambiguous_request",
        "confirmation_required": True,
        "required_slots": ("ambiguity",),
    },
    "blocked": {
        "route": "deny",
        "safety_allow": False,
        "safety_reason": "unsafe_payment",
        "confirmation_required": (False, True),
        "required_slots": ("reason",),
    },
}
REJECTION_CATEGORIES = {
    "wrong_task_type",
    "wrong_route",
    "unsafe_allowance",
    "missing_confirmation",
    "missing_slot",
    "wrong_slot",
    "decomposed_search_slots",
    "extract_search_fallback",
    "extract_query_slot",
    "extract_generic_price_wording",
    "extract_listed_price_wording",
    "extract_extra_particle_wording",
    "clarify_action_drift",
    "blocked_payment_action_drift",
    "form_confirmation_drift",
    "navigate_canonical_url_drift",
    "underspecified_request",
    "malformed_schema",
}

_USERS_PREFIX = "/" + "Users"
_ROOT_PREFIX = "/" + "root"
_TMP_PREFIX = "/" + "tmp"
_MNT_DATA_PREFIX = "/" + "mnt/data"
PRIVATE_PATH_RE = re.compile(
    rf"({_USERS_PREFIX}/[^\s\"')]+|{_ROOT_PREFIX}/[^\s\"')]+|{_TMP_PREFIX}/[^\s\"')]+|"
    rf"{_MNT_DATA_PREFIX}/[^\s\"')]+)"
)
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|"
    r"(?i:(?:api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_./+=-]{8,}))"
)
PRIVATE_IP_RE = re.compile(
    r"\b("
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}"
    r")\b"
)


def _require_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class BrowserTaskContract:
    task_type: str
    route: str
    safety: dict[str, Any]
    confirmation_required: bool
    slots: dict[str, Any]
    normalized_command: str
    language: str = "zh-CN"
    contract_version: str = "v1"

    def __post_init__(self) -> None:
        if self.task_type not in TASK_TYPES:
            raise ValidationError(f"task_type must be one of {sorted(TASK_TYPES)}")
        if self.route not in ROUTES:
            raise ValidationError(f"route must be one of {sorted(ROUTES)}")
        if not isinstance(self.safety, dict):
            raise ValidationError("safety must be an object")
        if not isinstance(self.safety.get("allow"), bool):
            raise ValidationError("safety.allow must be a boolean")
        _require_nonempty_string(self.safety.get("reason"), "safety.reason")
        if not isinstance(self.confirmation_required, bool):
            raise ValidationError("confirmation_required must be a boolean")
        if not isinstance(self.slots, dict):
            raise ValidationError("slots must be an object")
        _require_nonempty_string(self.normalized_command, "normalized_command")
        if self.language != "zh-CN":
            raise ValidationError("language must be zh-CN")
        if self.contract_version != "v1":
            raise ValidationError("contract_version must be v1")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> BrowserTaskContract:
        missing = sorted(CONTRACT_FIELDS - set(value))
        if missing:
            raise ValidationError(f"missing required fields: {', '.join(missing)}")
        return cls(
            task_type=value["task_type"],
            route=value["route"],
            safety=value["safety"],
            confirmation_required=value["confirmation_required"],
            slots=value["slots"],
            normalized_command=value["normalized_command"],
            language=value["language"],
            contract_version=value["contract_version"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "route": self.route,
            "safety": dict(self.safety),
            "confirmation_required": self.confirmation_required,
            "slots": dict(self.slots),
            "normalized_command": self.normalized_command,
            "language": self.language,
            "contract_version": self.contract_version,
        }


def as_contract(value: BrowserTaskContract | dict[str, Any]) -> BrowserTaskContract:
    if isinstance(value, BrowserTaskContract):
        return value
    if not isinstance(value, dict):
        raise ValidationError("contract must be an object")
    return BrowserTaskContract.from_dict(value)


def _contract_issue(
    field_path: str,
    issue_category: str,
    expected_constraint: str,
    observed_value: Any,
) -> dict[str, str]:
    return {
        "field_path": field_path,
        "issue_category": issue_category,
        "expected_constraint": expected_constraint,
        "observed_value_summary": json.dumps(observed_value, ensure_ascii=False, sort_keys=True),
    }


def validate_contract_semantics(contract: BrowserTaskContract | dict[str, Any]) -> list[dict[str, str]]:
    candidate = as_contract(contract)
    rules = TASK_TYPE_SEMANTICS[candidate.task_type]
    issues: list[dict[str, str]] = []

    if candidate.route != rules["route"]:
        issues.append(
            _contract_issue(
                "route",
                "task_route_mismatch",
                f"task_type={candidate.task_type} requires route={rules['route']}",
                candidate.route,
            )
        )
    if candidate.safety["allow"] != rules["safety_allow"]:
        issues.append(
            _contract_issue(
                "safety.allow",
                "safety_allow_mismatch",
                f"task_type={candidate.task_type} requires safety.allow={rules['safety_allow']}",
                candidate.safety["allow"],
            )
        )
    if candidate.safety["reason"] != rules["safety_reason"]:
        issues.append(
            _contract_issue(
                "safety.reason",
                "safety_reason_mismatch",
                f"task_type={candidate.task_type} requires safety.reason={rules['safety_reason']}",
                candidate.safety["reason"],
            )
        )
    confirmation_rule = rules["confirmation_required"]
    allowed_confirmation = (
        confirmation_rule if isinstance(confirmation_rule, tuple) else (confirmation_rule,)
    )
    if candidate.confirmation_required not in allowed_confirmation:
        issues.append(
            _contract_issue(
                "confirmation_required",
                "confirmation_policy_mismatch",
                f"task_type={candidate.task_type} requires confirmation_required in {allowed_confirmation}",
                candidate.confirmation_required,
            )
        )
    for slot_name in rules["required_slots"]:
        if slot_name not in candidate.slots:
            issues.append(
                _contract_issue(
                    f"slots.{slot_name}",
                    "missing_required_slot",
                    f"task_type={candidate.task_type} requires slot '{slot_name}'",
                    sorted(candidate.slots),
                )
            )
    return issues


def validate_contract_status(value: Any) -> dict[str, Any]:
    status: dict[str, Any] = {
        "schema_valid": False,
        "strict_schema_valid": False,
        "validation_error": None,
        "missing_required_fields": [],
        "extra_top_level_fields": [],
        "semantic_valid": False,
        "semantic_evaluated": False,
        "semantic_issues": [],
    }
    if isinstance(value, BrowserTaskContract):
        candidate_value = value.to_dict()
    elif isinstance(value, dict):
        candidate_value = value
    else:
        status["validation_error"] = "prediction must be a JSON object matching Browser Task Contract"
        status["missing_required_fields"] = sorted(CONTRACT_FIELDS)
        return status

    missing = sorted(CONTRACT_FIELDS - set(candidate_value))
    extra = sorted(set(candidate_value) - CONTRACT_FIELDS)
    status["missing_required_fields"] = missing
    status["extra_top_level_fields"] = extra
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing required fields: {', '.join(missing)}")
        if extra:
            parts.append(f"extra top-level fields: {', '.join(extra)}")
        status["validation_error"] = "; ".join(parts)
        return status

    try:
        candidate = BrowserTaskContract.from_dict(candidate_value)
    except ValidationError as exc:
        status["validation_error"] = str(exc)
        return status

    semantic_issues = validate_contract_semantics(candidate)
    status.update(
        {
            "schema_valid": True,
            "strict_schema_valid": True,
            "semantic_valid": not semantic_issues,
            "semantic_evaluated": True,
            "semantic_issues": semantic_issues,
        }
    )
    return status


def canonical_contract_json(contract: BrowserTaskContract | dict[str, Any]) -> str:
    return json.dumps(as_contract(contract).to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class SFTDatasetRow:
    id: str
    split: str
    input_text: str
    target_contract: BrowserTaskContract | dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty_string(self.id, "id")
        if self.split not in SPLITS:
            raise ValidationError(f"split must be one of {sorted(SPLITS)}")
        _require_nonempty_string(self.input_text, "input_text")
        object.__setattr__(self, "target_contract", as_contract(self.target_contract))
        if not isinstance(self.provenance, dict):
            raise ValidationError("provenance must be an object")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "split": self.split,
            "input_text": self.input_text,
            "target_contract": as_contract(self.target_contract).to_dict(),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class DPOPair:
    id: str
    split: str
    input_text: str
    chosen_contract: BrowserTaskContract | dict[str, Any]
    rejected_contract: BrowserTaskContract | dict[str, Any]
    rejection_reason: str
    provenance: dict[str, Any] = field(default_factory=dict)
    rejected_input_text: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.id, "id")
        if self.split not in SPLITS:
            raise ValidationError(f"split must be one of {sorted(SPLITS)}")
        _require_nonempty_string(self.input_text, "input_text")
        if self.rejected_input_text is not None and self.rejected_input_text != self.input_text:
            raise ValidationError("DPO pair must use the same input for chosen and rejected contracts")
        if self.rejection_reason not in REJECTION_CATEGORIES:
            raise ValidationError(f"rejection_reason must be one of {sorted(REJECTION_CATEGORIES)}")
        object.__setattr__(self, "chosen_contract", as_contract(self.chosen_contract))
        if self.rejection_reason == "malformed_schema":
            if not isinstance(self.rejected_contract, dict) or not self.rejected_contract:
                raise ValidationError("malformed_schema rejected_contract must be a non-empty object")
        else:
            object.__setattr__(self, "rejected_contract", as_contract(self.rejected_contract))
        if not isinstance(self.provenance, dict):
            raise ValidationError("provenance must be an object")

    def rejected_contract_dict(self) -> dict[str, Any]:
        if isinstance(self.rejected_contract, BrowserTaskContract):
            return self.rejected_contract.to_dict()
        return dict(self.rejected_contract)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "split": self.split,
            "input_text": self.input_text,
            "chosen_contract": as_contract(self.chosen_contract).to_dict(),
            "rejected_contract": self.rejected_contract_dict(),
            "rejection_reason": self.rejection_reason,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class DatasetManifest:
    manifest_id: str
    mode: str
    generated_at: str
    files: dict[str, str]
    counts: dict[str, int]
    split_counts: dict[str, int]
    dpo_rejection_counts: dict[str, int]
    source_summary: dict[str, Any]
    public_safe: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "mode": self.mode,
            "generated_at": self.generated_at,
            "files": dict(self.files),
            "counts": dict(self.counts),
            "split_counts": dict(self.split_counts),
            "dpo_rejection_counts": dict(self.dpo_rejection_counts),
            "source_summary": dict(self.source_summary),
            "public_safe": self.public_safe,
        }


def validate_public_text(text: str) -> None:
    if PRIVATE_PATH_RE.search(text):
        raise ValidationError("private_path: public artifacts must not contain local absolute paths")
    if SECRET_RE.search(text):
        raise ValidationError("secret: public artifacts must not contain tokens or API keys")
    if PRIVATE_IP_RE.search(text):
        raise ValidationError("private_ip: public artifacts must not contain private IP addresses")


def validate_public_record(record: dict[str, Any]) -> None:
    validate_public_text(json.dumps(record, ensure_ascii=False, sort_keys=True))
