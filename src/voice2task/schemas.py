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
REJECTION_CATEGORIES = {
    "wrong_task_type",
    "wrong_route",
    "unsafe_allowance",
    "missing_confirmation",
    "missing_slot",
    "wrong_slot",
    "underspecified_request",
    "malformed_schema",
}

_USERS_PREFIX = "/" + "Users"
_ROOT_PREFIX = "/" + "root"
_TMP_PREFIX = "/" + "tmp"
PRIVATE_PATH_RE = re.compile(
    rf"({_USERS_PREFIX}/[^\s\"')]+|{_ROOT_PREFIX}/[^\s\"')]+|{_TMP_PREFIX}/[^\s\"')]+)"
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
        required = {
            "task_type",
            "route",
            "safety",
            "confirmation_required",
            "slots",
            "normalized_command",
            "language",
            "contract_version",
        }
        missing = sorted(required - set(value))
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
