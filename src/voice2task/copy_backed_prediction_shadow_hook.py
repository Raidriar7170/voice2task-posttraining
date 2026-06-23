from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from voice2task.copy_backed_shadow_interface import (
    compute_policy_hash,
    generate_online_shadow_sidecar,
    load_scope_policy,
    stable_hash,
    validate_scope_policy,
)
from voice2task.copy_backed_slot_verification import VERIFIED_EXACT_UNIQUE, VERIFIED_NORMALIZED_UNIQUE, source_text_hash
from voice2task.schemas import ValidationError, as_contract, canonical_contract_json

HOOK_VERSION = "copy-backed-prediction-shadow-hook-v1"
SIDECAR_VERSION = "copy-prediction-shadow-v1"


@dataclass(frozen=True)
class PredictionShadowHookConfig:
    enabled: bool = False
    policy_path: Path | None = None
    sidecar_output_path: Path | None = None
    retain_span_text: bool = False
    retain_input_text: bool = False
    retain_raw_model_output: bool = False
    fail_isolated: bool = True


@dataclass(frozen=True)
class PredictionShadowPolicySnapshot:
    policy: dict[str, Any]
    policy_path: Path
    policy_id: str
    policy_version: str
    policy_hash: str
    policy_start_hash: str
    policy_loaded_once: bool = True


@dataclass(frozen=True)
class PredictionShadowHookOutcome:
    hook_status: str
    sidecar: dict[str, Any] | None
    error_code: str | None
    trusted_provenance_count: int
    candidate_provenance_count: int
    sidecar_write_status: str
    main_prediction_unchanged: bool
    exception_isolated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook_status": self.hook_status,
            "sidecar": self.sidecar,
            "error_code": self.error_code,
            "trusted_provenance_count": self.trusted_provenance_count,
            "candidate_provenance_count": self.candidate_provenance_count,
            "sidecar_write_status": self.sidecar_write_status,
            "main_prediction_unchanged": self.main_prediction_unchanged,
            "exception_isolated": self.exception_isolated,
        }


class ShadowSink(Protocol):
    def write(self, sidecar: dict[str, Any]) -> str:
        ...


class NullShadowSink:
    def write(self, sidecar: dict[str, Any]) -> str:
        return "disabled"


class JsonlShadowSink:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, sidecar: dict[str, Any]) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sidecar, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        return "written"


def shadow_config_from_mapping(
    raw_config: Any,
    *,
    config_dir: Path,
    output_dir: Path,
) -> PredictionShadowHookConfig:
    if not isinstance(raw_config, dict) or raw_config.get("enabled") is not True:
        return PredictionShadowHookConfig(enabled=False)
    policy_path = _resolve_path(raw_config.get("policy_path"), base_dir=config_dir, fallback_to_cwd=True)
    if policy_path is None:
        policy_path = _resolve_path("configs/copy-backed-scope-policy-v1.json", base_dir=Path.cwd())
    sidecar_output_path = _resolve_path(
        raw_config.get("sidecar_output_path", raw_config.get("sidecar_path")),
        base_dir=output_dir,
    )
    return PredictionShadowHookConfig(
        enabled=True,
        policy_path=policy_path,
        sidecar_output_path=sidecar_output_path,
        retain_span_text=bool(raw_config.get("retain_span_text", False)),
        retain_input_text=bool(raw_config.get("retain_input_text", False)),
        retain_raw_model_output=bool(raw_config.get("retain_raw_model_output", False)),
        fail_isolated=bool(raw_config.get("fail_isolated", True)),
    )


def run_prediction_shadow_hook(
    *,
    source_text: Any,
    prediction: Any,
    config: PredictionShadowHookConfig,
    request_id: str,
    sink: ShadowSink | None = None,
    policy_snapshot: PredictionShadowPolicySnapshot | None = None,
    policy_error_code: str | None = None,
    sidecar_path_conflict: bool = False,
) -> PredictionShadowHookOutcome:
    started = time.perf_counter()
    if not config.enabled:
        return _outcome(
            "SKIPPED_DISABLED",
            sidecar=None,
            sidecar_write_status="disabled",
            started=started,
        )
    config_error_code = prediction_shadow_config_error_code(config)
    if config_error_code is not None:
        return _outcome(
            "SHADOW_CONFIG_INVALID_ISOLATED",
            sidecar=None,
            error_code=config_error_code,
            sidecar_write_status="disabled",
            exception_isolated=True,
            started=started,
        )
    if sidecar_path_conflict:
        return _outcome(
            "SHADOW_SINK_PATH_CONFLICT_ISOLATED",
            sidecar=None,
            error_code="sidecar_path_conflicts_with_primary_artifact",
            sidecar_write_status="disabled",
            exception_isolated=True,
            started=started,
        )
    if not isinstance(source_text, str) or not source_text:
        return _outcome(
            "SHADOW_INVALID_INPUT",
            sidecar=None,
            error_code="source_text_missing",
            sidecar_write_status="disabled",
            exception_isolated=True,
            started=started,
        )
    if policy_error_code is not None:
        return _outcome(
            "SHADOW_POLICY_INVALID",
            sidecar=None,
            error_code=policy_error_code,
            sidecar_write_status="disabled",
            exception_isolated=True,
            started=started,
        )
    try:
        if policy_snapshot is None:
            policy_snapshot = load_prediction_shadow_policy_snapshot(config, loaded_once=False)
        policy = policy_snapshot.policy
    except Exception:
        return _outcome(
            "SHADOW_POLICY_INVALID",
            sidecar=None,
            error_code="policy_load_or_validation_failed",
            sidecar_write_status="disabled",
            exception_isolated=True,
            started=started,
        )
    parsed_prediction, invalid_status = _parse_prediction(prediction)
    if invalid_status is not None:
        return _outcome(
            invalid_status["hook_status"],
            sidecar=None,
            error_code=invalid_status["error_code"],
            sidecar_write_status="disabled",
            exception_isolated=True,
            started=started,
        )
    assert parsed_prediction is not None
    try:
        sidecar = _build_prediction_sidecar(
            source_text=source_text,
            prediction_contract=parsed_prediction,
            request_id=request_id,
            scope_policy=policy,
            policy_loaded_once=policy_snapshot.policy_loaded_once,
            policy_start_hash=policy_snapshot.policy_start_hash,
            retain_span_text=config.retain_span_text,
            started=started,
        )
    except Exception:
        return _outcome(
            "SHADOW_VERIFIER_ERROR_ISOLATED",
            sidecar=None,
            error_code="verifier_failed",
            sidecar_write_status="disabled",
            exception_isolated=True,
            started=started,
        )
    trusted_count = _trusted_count(sidecar)
    candidate_count = _candidate_count(sidecar)
    try:
        json.dumps(sidecar, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        sidecar["hook_status"] = "SHADOW_SERIALIZATION_ERROR_ISOLATED"
        sidecar["sidecar_write_status"] = "failed_isolated"
        return _outcome(
            "SHADOW_SERIALIZATION_ERROR_ISOLATED",
            sidecar=sidecar,
            error_code="sidecar_serialization_failed",
            trusted_provenance_count=trusted_count,
            candidate_provenance_count=candidate_count,
            sidecar_write_status="failed_isolated",
            exception_isolated=True,
            started=started,
        )
    active_sink = sink if sink is not None else _sink_for_config(config)
    expected_write_status = "disabled" if isinstance(active_sink, NullShadowSink) else "written"
    sidecar["sidecar_write_status"] = expected_write_status
    try:
        sidecar_write_status = active_sink.write(sidecar)
    except Exception:
        sidecar["hook_status"] = "SHADOW_SINK_ERROR_ISOLATED"
        sidecar["sidecar_write_status"] = "failed_isolated"
        return _outcome(
            "SHADOW_SINK_ERROR_ISOLATED",
            sidecar=sidecar,
            error_code="sink_write_failed",
            trusted_provenance_count=trusted_count,
            candidate_provenance_count=candidate_count,
            sidecar_write_status="failed_isolated",
            exception_isolated=True,
            started=started,
        )
    sidecar["sidecar_write_status"] = sidecar_write_status
    return _outcome(
        "COMPLETED",
        sidecar=sidecar,
        trusted_provenance_count=trusted_count,
        candidate_provenance_count=candidate_count,
        sidecar_write_status=sidecar_write_status,
        started=started,
    )


def summarize_prediction_shadow_outcomes(
    outcomes: list[PredictionShadowHookOutcome],
    *,
    enabled: bool,
    policy_snapshot: PredictionShadowPolicySnapshot | None = None,
) -> dict[str, Any]:
    hook_status_counts: dict[str, int] = {}
    error_code_counts: dict[str, int] = {}
    sidecar_write_statuses: set[str] = set()
    for outcome in outcomes:
        hook_status_counts[outcome.hook_status] = hook_status_counts.get(outcome.hook_status, 0) + 1
        if outcome.error_code:
            error_code_counts[outcome.error_code] = error_code_counts.get(outcome.error_code, 0) + 1
        sidecar_write_statuses.add(outcome.sidecar_write_status)
    summary: dict[str, Any] = {
        "enabled": enabled,
        "hook_version": HOOK_VERSION,
        "sidecar_version": SIDECAR_VERSION,
        "hook_invocation_count": len(outcomes),
        "hook_status_counts": hook_status_counts,
        "error_code_counts": error_code_counts,
        "trusted_provenance_count": sum(outcome.trusted_provenance_count for outcome in outcomes),
        "candidate_provenance_count": sum(outcome.candidate_provenance_count for outcome in outcomes),
        "exception_isolated_count": sum(1 for outcome in outcomes if outcome.exception_isolated),
        "sidecar_write_status": _summary_sidecar_write_status(sidecar_write_statuses),
        "main_prediction_unchanged": all(outcome.main_prediction_unchanged for outcome in outcomes),
        "gold_fields_absent": True,
        "contract_mutated": False,
        "runtime_decision_changed": False,
        "path_conflict_count": hook_status_counts.get("SHADOW_SINK_PATH_CONFLICT_ISOLATED", 0),
    }
    if policy_snapshot is not None:
        policy_end_hash = _current_policy_end_hash(policy_snapshot.policy_path)
        summary.update(
            {
                "policy_loaded_once": policy_snapshot.policy_loaded_once,
                "policy_id": policy_snapshot.policy_id,
                "policy_version": policy_snapshot.policy_version,
                "policy_hash": policy_snapshot.policy_hash,
                "policy_start_hash": policy_snapshot.policy_start_hash,
                "policy_end_hash": policy_end_hash,
                "policy_drift_detected": policy_end_hash != policy_snapshot.policy_start_hash,
            }
        )
    return summary


def prediction_shadow_config_error_code(config: PredictionShadowHookConfig) -> str | None:
    if config.retain_input_text:
        return "reserved_config_non_default:retain_input_text"
    if config.retain_raw_model_output:
        return "reserved_config_non_default:retain_raw_model_output"
    if config.fail_isolated is not True:
        return "reserved_config_non_default:fail_isolated"
    return None


def load_prediction_shadow_policy_snapshot(
    config: PredictionShadowHookConfig,
    *,
    loaded_once: bool = True,
) -> PredictionShadowPolicySnapshot:
    policy_path = _required_policy_path(config)
    policy = load_scope_policy(policy_path)
    policy_validation = validate_scope_policy(policy)
    if not policy_validation.get("ok"):
        raise ValueError("copy-backed shadow policy validation failed")
    policy_hash = str(policy_validation["policy_hash"])
    return PredictionShadowPolicySnapshot(
        policy=policy,
        policy_path=policy_path,
        policy_id=str(policy_validation["policy_id"]),
        policy_version=str(policy_validation["policy_version"]),
        policy_hash=policy_hash,
        policy_start_hash=str(policy_validation["computed_policy_hash"]),
        policy_loaded_once=loaded_once,
    )


def sidecar_path_conflicts(sidecar_output_path: Path | None, reserved_artifact_paths: list[Path]) -> bool:
    if sidecar_output_path is None:
        return False
    sidecar_path = _canonical_path(sidecar_output_path)
    return any(sidecar_path == _canonical_path(path) for path in reserved_artifact_paths)


def _canonical_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _current_policy_end_hash(path: Path) -> str | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return compute_policy_hash(raw)


def _resolve_path(value: Any, *, base_dir: Path, fallback_to_cwd: bool = False) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = base_dir / path
    if fallback_to_cwd and not candidate.exists():
        cwd_candidate = Path.cwd() / path
        if cwd_candidate.exists():
            return cwd_candidate
    return candidate


def _required_policy_path(config: PredictionShadowHookConfig) -> Path:
    if config.policy_path is None:
        raise ValueError("copy-backed shadow policy_path is required when enabled")
    return config.policy_path


def _sink_for_config(config: PredictionShadowHookConfig) -> ShadowSink:
    if config.sidecar_output_path is None:
        return NullShadowSink()
    return JsonlShadowSink(config.sidecar_output_path)


def _parse_prediction(prediction: Any) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    value = prediction
    if isinstance(prediction, str):
        if not prediction.strip():
            return None, {"hook_status": "SHADOW_INVALID_INPUT", "error_code": "prediction_empty"}
        try:
            value = json.loads(prediction)
        except json.JSONDecodeError:
            return None, {"hook_status": "SHADOW_INVALID_INPUT", "error_code": "prediction_malformed_json"}
    if not isinstance(value, dict):
        return None, {"hook_status": "SHADOW_INVALID_INPUT", "error_code": "prediction_unsupported_type"}
    try:
        return as_contract(value).to_dict(), None
    except ValidationError:
        return None, {"hook_status": "SHADOW_INVALID_CONTRACT", "error_code": "prediction_schema_invalid"}


def _build_prediction_sidecar(
    *,
    source_text: str,
    prediction_contract: dict[str, Any],
    request_id: str,
    scope_policy: dict[str, Any],
    policy_loaded_once: bool,
    policy_start_hash: str,
    retain_span_text: bool,
    started: float,
) -> dict[str, Any]:
    online_sidecar = generate_online_shadow_sidecar(
        source_text,
        prediction_contract,
        request_id=request_id,
        scope_policy=scope_policy,
        retain_span_text=retain_span_text,
        retain_request_id=False,
    )
    diagnostics = [_prediction_diagnostic(diagnostic) for diagnostic in online_sidecar["slot_diagnostics"]]
    return {
        "sidecar_version": SIDECAR_VERSION,
        "hook_version": HOOK_VERSION,
        "request_id_hash": stable_hash(request_id),
        "prediction_hash": stable_hash(canonical_contract_json(prediction_contract)),
        "input_hash": source_text_hash(source_text),
        "policy_id": scope_policy["policy_id"],
        "policy_version": scope_policy["policy_version"],
        "policy_hash": scope_policy["policy_hash"],
        "policy_loaded_once": policy_loaded_once,
        "policy_start_hash": policy_start_hash,
        "hook_status": "COMPLETED",
        "slot_diagnostics": diagnostics,
        "contract_mutated": False,
        "runtime_decision_changed": False,
        "main_prediction_unchanged": True,
        "hook_latency_ms": _elapsed_ms(started),
        "sidecar_write_status": "pending",
    }


def _prediction_diagnostic(diagnostic: dict[str, Any]) -> dict[str, Any]:
    verification_status = str(diagnostic.get("verification_status", diagnostic.get("status", "")))
    trusted = (
        verification_status == VERIFIED_EXACT_UNIQUE
        and diagnostic.get("match_kind") == "exact"
        and diagnostic.get("candidate_span_count") == 1
        and diagnostic.get("policy_enabled") is True
        and diagnostic.get("trusted_provenance") is True
    )
    candidate = (
        verification_status == VERIFIED_NORMALIZED_UNIQUE
        and diagnostic.get("match_kind") == "normalized"
        and diagnostic.get("candidate_span_count") == 1
        and diagnostic.get("policy_enabled") is True
        and diagnostic.get("candidate_provenance") is True
    )
    return {
        "task_type": diagnostic.get("task_type"),
        "route": diagnostic.get("route"),
        "slot_path": diagnostic.get("slot_path"),
        "scope_key": diagnostic.get("scope_key"),
        "policy_enabled": diagnostic.get("policy_enabled") is True,
        "policy_version": diagnostic.get("scope_policy_version"),
        "verification_status": verification_status,
        "match_kind": diagnostic.get("match_kind"),
        "trusted_provenance": trusted,
        "candidate_provenance": candidate and not trusted,
        "source_span": diagnostic.get("source_span"),
        "candidate_span_count": diagnostic.get("candidate_span_count"),
        "normalization_rule": diagnostic.get("normalization_rule"),
        "failure_reason": diagnostic.get("failure_reason"),
        "predicted_value_hash": diagnostic.get("predicted_value_hash"),
    }


def _trusted_count(sidecar: dict[str, Any]) -> int:
    return sum(1 for diagnostic in sidecar.get("slot_diagnostics", []) if diagnostic.get("trusted_provenance") is True)


def _candidate_count(sidecar: dict[str, Any]) -> int:
    return sum(
        1
        for diagnostic in sidecar.get("slot_diagnostics", [])
        if diagnostic.get("candidate_provenance") is True
    )


def _outcome(
    hook_status: str,
    *,
    sidecar: dict[str, Any] | None,
    error_code: str | None = None,
    trusted_provenance_count: int = 0,
    candidate_provenance_count: int = 0,
    sidecar_write_status: str,
    exception_isolated: bool = False,
    started: float,
) -> PredictionShadowHookOutcome:
    if sidecar is not None:
        sidecar["hook_latency_ms"] = _elapsed_ms(started)
    return PredictionShadowHookOutcome(
        hook_status=hook_status,
        sidecar=sidecar,
        error_code=error_code,
        trusted_provenance_count=trusted_provenance_count,
        candidate_provenance_count=candidate_provenance_count,
        sidecar_write_status=sidecar_write_status,
        main_prediction_unchanged=True,
        exception_isolated=exception_isolated,
    )


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 6)


def _summary_sidecar_write_status(statuses: set[str]) -> str:
    if "failed_isolated" in statuses:
        return "failed_isolated"
    if "written" in statuses:
        return "written"
    return "disabled"
