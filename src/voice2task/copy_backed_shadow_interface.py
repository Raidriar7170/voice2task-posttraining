from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from voice2task.copy_backed_slot_verification import (
    VERIFIED_EXACT_UNIQUE,
    VERIFIED_NORMALIZED_UNIQUE,
    CopyBackedScope,
    CopyBackedVerificationResult,
    SourceSpan,
    source_text_hash,
    verify_copy_backed_value,
    verify_source_span,
)
from voice2task.io import read_json
from voice2task.schemas import as_contract, canonical_contract_json
from voice2task.slot_error_analysis import flatten_slot_values

EXPECTED_POLICY_ID = "copy-backed-scope-policy-v1"
EXPECTED_ENABLED_TRIPLES = (
    "search:search_web:query",
    "form_fill:fill_form:field",
    "extract:extract_page:target",
)
POLICY_HASH_ALGORITHM = "sha256_canonical_json_without_policy_hash"

GOLD_FIELD_FRAGMENTS = ("gold", "correct", "accuracy", "score", "evaluator")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_scope_policy(path: Path) -> dict[str, Any]:
    return read_json(path)


def canonical_policy_payload(policy: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(policy)
    payload.pop("policy_hash", None)
    return payload


def compute_policy_hash(policy: dict[str, Any]) -> str:
    return stable_hash(canonical_policy_payload(policy))


def scope_key(task_type: str, route: str, slot_path: str) -> str:
    return f"{task_type}:{route}:{slot_path}"


def validate_scope_policy(policy: dict[str, Any]) -> dict[str, Any]:
    blocking_reasons: list[str] = []
    if policy.get("policy_id") != EXPECTED_POLICY_ID:
        blocking_reasons.append("policy_id_drift")
    if policy.get("policy_hash_algorithm") != POLICY_HASH_ALGORITHM:
        blocking_reasons.append("policy_hash_algorithm_drift")
    if policy.get("action_enabled") is not False:
        blocking_reasons.append("action_enabled_drift")
    if policy.get("normalized_trusted") is not False:
        blocking_reasons.append("normalized_trusted_drift")
    if tuple(policy.get("enabled_triples", [])) != EXPECTED_ENABLED_TRIPLES:
        blocking_reasons.append("enabled_triples_drift")
    if policy.get("policy_hash") != compute_policy_hash(policy):
        blocking_reasons.append("policy_hash_drift")
    return {
        "ok": not blocking_reasons,
        "blocking_reasons": blocking_reasons,
        "policy_id": policy.get("policy_id"),
        "policy_version": policy.get("policy_version"),
        "policy_hash": policy.get("policy_hash"),
        "computed_policy_hash": compute_policy_hash(policy),
        "enabled_triples": policy.get("enabled_triples", []),
        "disabled_triples": policy.get("disabled_triples", []),
        "action_enabled": policy.get("action_enabled"),
        "normalized_trusted": policy.get("normalized_trusted"),
    }


def policy_by_scope_key(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = policy.get("scope_rows", [])
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = scope_key(str(row["task_type"]), str(row["route"]), str(row["slot_path"]))
        result[key] = row
    return result


def _scope_from_policy(
    *,
    task_type: str,
    route: str,
    slot_path: str,
    policy: dict[str, Any],
) -> CopyBackedScope:
    row = policy_by_scope_key(policy).get(scope_key(task_type, route, slot_path))
    if row is None:
        return CopyBackedScope(
            task_type=task_type,
            route=route,
            slot_path=slot_path,
            enabled=False,
            policy_version=str(policy.get("policy_id", EXPECTED_POLICY_ID)),
            exclusion_reason="slot_path_or_task_scope_not_enabled_for_shadow_policy",
        )
    return CopyBackedScope(
        task_type=task_type,
        route=route,
        slot_path=slot_path,
        enabled=bool(row.get("enabled")),
        policy_version=str(policy.get("policy_id", EXPECTED_POLICY_ID)),
        evidence_reference=row.get("evidence_reference"),
        exclusion_reason=row.get("exclusion_reason"),
    )


def validate_trusted_source_span(
    *,
    source_text: str,
    source_hash: str,
    predicted_value: Any,
    result: CopyBackedVerificationResult,
    policy_enabled: bool,
) -> bool:
    if not policy_enabled:
        return False
    if result.status != VERIFIED_EXACT_UNIQUE or result.match_kind != "exact":
        return False
    if result.candidate_span_count != 1:
        return False
    if result.source_span is None:
        return False
    if result.source_span.source_text_hash != source_hash:
        return False
    if not verify_source_span(source_text, result.source_span):
        return False
    if not isinstance(predicted_value, str):
        return False
    return source_text[result.source_span.start : result.source_span.end] == predicted_value


def _span_to_dict(span: SourceSpan | None) -> dict[str, Any] | None:
    if span is None:
        return None
    return span.to_dict()


def _diagnostic_for_slot(
    *,
    source_text: str,
    source_hash: str,
    task_type: str,
    route: str,
    slot_path: str,
    predicted_value: Any,
    scope_policy: dict[str, Any],
) -> dict[str, Any]:
    scope = _scope_from_policy(task_type=task_type, route=route, slot_path=slot_path, policy=scope_policy)
    result = verify_copy_backed_value(predicted_value, source_text, scope)
    policy_enabled = bool(scope.enabled)
    trusted = validate_trusted_source_span(
        source_text=source_text,
        source_hash=source_hash,
        predicted_value=predicted_value,
        result=result,
        policy_enabled=policy_enabled,
    )
    candidate = (
        policy_enabled
        and result.status == VERIFIED_NORMALIZED_UNIQUE
        and result.match_kind == "normalized"
        and result.candidate_span_count == 1
    )
    return {
        "slot_path": slot_path,
        "scope_key": scope.key,
        "task_type": task_type,
        "route": route,
        "policy_enabled": policy_enabled,
        "status": result.status,
        "match_kind": result.match_kind,
        "trusted_provenance": trusted,
        "candidate_provenance": candidate,
        "provenance": "system_verified_source" if trusted else "candidate_source_span" if candidate else "unresolved",
        "source_span": _span_to_dict(result.source_span),
        "predicted_value_hash": stable_hash(predicted_value),
        "candidate_span_count": result.candidate_span_count,
        "normalization_rule": result.normalization_rule,
        "normalization_trusted": False,
        "failure_reason": None if trusted or candidate else result.reason,
        "predicted_value_type": type(predicted_value).__name__,
    }


def generate_online_shadow_sidecar(
    source_text: str,
    prediction_contract: dict[str, Any],
    *,
    request_id: str,
    scope_policy: dict[str, Any],
    sample_id: str | None = None,
    split: str | None = None,
    run_role: str | None = None,
) -> dict[str, Any]:
    contract = as_contract(prediction_contract).to_dict()
    source_hash = source_text_hash(source_text)
    slots = flatten_slot_values(contract["slots"])
    diagnostics = [
        _diagnostic_for_slot(
            source_text=source_text,
            source_hash=source_hash,
            task_type=contract["task_type"],
            route=contract["route"],
            slot_path=slot_path,
            predicted_value=slots[slot_path],
            scope_policy=scope_policy,
        )
        for slot_path in sorted(slots)
    ]
    return {
        "interface": "OnlineShadowSidecar",
        "interface_version": "copy-backed-shadow-interface-v1",
        "request_id": request_id,
        "sample_id": sample_id,
        "split": split,
        "run_role": run_role,
        "task_type": contract["task_type"],
        "route": contract["route"],
        "shadow_mode_enabled": True,
        "enforcement_enabled": False,
        "policy_id": scope_policy["policy_id"],
        "policy_version": scope_policy["policy_version"],
        "policy_hash": scope_policy["policy_hash"],
        "input_hash": source_hash,
        "prediction_contract_hash": stable_hash(canonical_contract_json(contract)),
        "slot_diagnostics": diagnostics,
    }


def _contains_forbidden_gold_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if any(fragment in str(key).lower() for fragment in GOLD_FIELD_FRAGMENTS):
                return True
            if _contains_forbidden_gold_field(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_gold_field(item) for item in value)
    return False


def online_sidecar_has_no_gold_fields(sidecar: dict[str, Any]) -> bool:
    return not _contains_forbidden_gold_field(sidecar)


class _Missing:
    pass


MISSING = _Missing()


def _gold_correct_exact(
    *,
    predicted_contract: dict[str, Any],
    gold_contract: dict[str, Any],
    slot_path: str,
    predicted_value: Any,
) -> bool:
    if (
        predicted_contract["task_type"] != gold_contract["task_type"]
        or predicted_contract["route"] != gold_contract["route"]
    ):
        return False
    gold_slots = flatten_slot_values(gold_contract["slots"])
    return gold_slots.get(slot_path, MISSING) == predicted_value


def build_evaluation_audits(
    online_sidecar: dict[str, Any],
    prediction_contract: dict[str, Any],
    gold_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    prediction = as_contract(prediction_contract).to_dict()
    gold = as_contract(gold_contract).to_dict()
    prediction_slots = flatten_slot_values(prediction["slots"])
    audits: list[dict[str, Any]] = []
    for diagnostic in online_sidecar["slot_diagnostics"]:
        slot_path = diagnostic["slot_path"]
        predicted_value = prediction_slots.get(slot_path, MISSING)
        trusted = bool(diagnostic["trusted_provenance"])
        audits.append(
            {
                "interface": "EvaluationAudit",
                "interface_version": "copy-backed-shadow-interface-v1",
                "request_id": online_sidecar["request_id"],
                "sample_id": online_sidecar.get("sample_id"),
                "split": online_sidecar.get("split"),
                "run_role": online_sidecar.get("run_role"),
                "scope_key": diagnostic["scope_key"],
                "slot_path": slot_path,
                "status": diagnostic["status"],
                "trusted_provenance": trusted,
                "candidate_provenance": bool(diagnostic["candidate_provenance"]),
                "gold_correct_exact": _gold_correct_exact(
                    predicted_contract=prediction,
                    gold_contract=gold,
                    slot_path=slot_path,
                    predicted_value=predicted_value,
                )
                if trusted
                else None,
                "gold_value_present": slot_path in flatten_slot_values(gold["slots"]),
                "offline_only": True,
            }
        )
    return audits


def count_provenance_false_accepts(
    online_sidecar: dict[str, Any],
    source_text: str,
    scope_policy: dict[str, Any],
) -> int:
    source_hash = source_text_hash(source_text)
    policy_rows = policy_by_scope_key(scope_policy)
    false_accepts = 0
    for diagnostic in online_sidecar.get("slot_diagnostics", []):
        if not diagnostic.get("trusted_provenance"):
            continue
        if online_sidecar.get("policy_hash") != scope_policy.get("policy_hash"):
            false_accepts += 1
            continue
        if diagnostic.get("status") != VERIFIED_EXACT_UNIQUE or diagnostic.get("match_kind") != "exact":
            false_accepts += 1
            continue
        if diagnostic.get("candidate_span_count") != 1:
            false_accepts += 1
            continue
        policy_row = policy_rows.get(str(diagnostic["scope_key"]))
        if policy_row is None or not policy_row.get("enabled"):
            false_accepts += 1
            continue
        span_dict = diagnostic.get("source_span")
        if not isinstance(span_dict, dict):
            false_accepts += 1
            continue
        span = SourceSpan(
            start=int(span_dict["start"]),
            end=int(span_dict["end"]),
            text=str(span_dict["text"]),
            source_text_hash=str(span_dict["source_text_hash"]),
        )
        if span.source_text_hash != source_hash or not verify_source_span(source_text, span):
            false_accepts += 1
            continue
        if diagnostic.get("predicted_value_hash") != stable_hash(span.text):
            false_accepts += 1
    return false_accepts
