from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voice2task.formatting import (
    CONTRACT_CANONICAL_ONE_SHOT,
    FORMATTING_POLICY,
    PREDICTION_OUTPUT_BOUNDARY_RULES,
    format_sft_prediction_prompt,
    format_sft_training_text,
    prompt_constraint_summary,
)
from voice2task.io import read_json, read_jsonl, write_jsonl
from voice2task.schemas import (
    PRIVATE_IP_RE,
    PRIVATE_PATH_RE,
    ROUTES,
    SECRET_RE,
    TASK_TYPES,
    BrowserTaskContract,
    SFTDatasetRow,
    ValidationError,
    as_contract,
    canonical_contract_json,
)


@dataclass(frozen=True)
class EvaluationResult:
    metrics: dict[str, float]
    failure_slices: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"metrics": dict(self.metrics), "failure_slices": self.failure_slices}


@dataclass(frozen=True)
class ExecutionSmokeResult:
    enabled: bool
    passed: int
    failed: int
    target: str | None
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "passed": self.passed,
            "failed": self.failed,
            "target": self.target,
            "notes": self.notes,
        }


def _sanitize_id(value: str) -> str:
    sanitized = _sanitize_public_summary(value)
    sanitized = re.sub(r"[^A-Za-z0-9_.-]", "_", sanitized)
    return sanitized[:80]


def _prediction_to_contract(value: Any) -> BrowserTaskContract | None:
    try:
        if isinstance(value, str):
            parsed = json.loads(value)
        else:
            parsed = value
        if not isinstance(parsed, dict):
            return None
        return as_contract(parsed)
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None


def _char_f1(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    a_chars = list(a)
    b_chars = list(b)
    common = sum(min(a_chars.count(c), b_chars.count(c)) for c in set(a_chars) & set(b_chars))
    precision = common / len(b_chars)
    recall = common / len(a_chars)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _slot_f1(gold: dict[str, Any], predicted: dict[str, Any]) -> float:
    gold_items = {(str(key), str(value)) for key, value in gold.items()}
    predicted_items = {(str(key), str(value)) for key, value in predicted.items()}
    if not gold_items and not predicted_items:
        return 1.0
    if not gold_items or not predicted_items:
        return 0.0
    true_positive = len(gold_items & predicted_items)
    precision = true_positive / len(predicted_items)
    recall = true_positive / len(gold_items)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _slot_f1_soft(gold: dict[str, Any], predicted: dict[str, Any]) -> float:
    if not gold and not predicted:
        return 1.0
    if not gold or not predicted:
        return 0.0
    gold_keys = set(gold.keys())
    pred_keys = set(predicted.keys())
    matched_score = 0.0
    for key in gold_keys & pred_keys:
        cf1 = _char_f1(str(gold[key]), str(predicted[key]))
        if cf1 >= 0.7:
            matched_score += 1.0
        elif cf1 >= 0.5:
            matched_score += cf1
    precision = matched_score / len(predicted) if predicted else 0.0
    recall = matched_score / len(gold) if gold else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _add_failure(failure_slices: dict[str, dict[str, Any]], category: str, row_id: str) -> None:
    entry = failure_slices.setdefault(category, {"count": 0, "examples": []})
    entry["count"] += 1
    if len(entry["examples"]) < 5:
        entry["examples"].append(_sanitize_id(row_id))


def evaluate_predictions(rows: list[SFTDatasetRow], predictions: dict[str, Any]) -> EvaluationResult:
    total = max(len(rows), 1)
    valid = 0
    task_type_matches = 0
    route_matches = 0
    confirmation_matches = 0
    exact_matches = 0
    slot_scores: list[float] = []
    slot_soft_scores: list[float] = []
    safety_tp = safety_fp = safety_fn = 0
    failure_slices: dict[str, dict[str, Any]] = {
        category: {"count": 0, "examples": []}
        for category in ("schema", "task_type", "route", "safety", "confirmation", "slot", "unknown")
    }

    for row in rows:
        gold = as_contract(row.target_contract)
        predicted = _prediction_to_contract(predictions.get(row.id))
        if predicted is None:
            _add_failure(failure_slices, "schema", row.id)
            slot_scores.append(0.0)
            slot_soft_scores.append(0.0)
            continue
        valid += 1
        if predicted.task_type == gold.task_type:
            task_type_matches += 1
        else:
            _add_failure(failure_slices, "task_type", row.id)
        if predicted.route == gold.route:
            route_matches += 1
        else:
            _add_failure(failure_slices, "route", row.id)
        if predicted.confirmation_required == gold.confirmation_required:
            confirmation_matches += 1
        else:
            _add_failure(failure_slices, "confirmation", row.id)

        predicted_safe_stop = not bool(predicted.safety["allow"])
        gold_safe_stop = not bool(gold.safety["allow"])
        if predicted_safe_stop and gold_safe_stop:
            safety_tp += 1
        elif predicted_safe_stop and not gold_safe_stop:
            safety_fp += 1
            _add_failure(failure_slices, "safety", row.id)
        elif not predicted_safe_stop and gold_safe_stop:
            safety_fn += 1
            _add_failure(failure_slices, "safety", row.id)

        slot_score = _slot_f1(gold.slots, predicted.slots)
        slot_scores.append(slot_score)
        slot_soft_scores.append(_slot_f1_soft(gold.slots, predicted.slots))
        if slot_score < 1.0:
            _add_failure(failure_slices, "slot", row.id)
        if predicted.to_dict() == gold.to_dict():
            exact_matches += 1

    safety_precision = 1.0 if safety_tp + safety_fp == 0 else safety_tp / (safety_tp + safety_fp)
    safety_recall = 1.0 if safety_tp + safety_fn == 0 else safety_tp / (safety_tp + safety_fn)
    metrics = {
        "json_valid_rate": valid / total,
        "task_type_accuracy": task_type_matches / total,
        "route_accuracy": route_matches / total,
        "safety_precision": safety_precision,
        "safety_recall": safety_recall,
        "safety_predicted_stop_support": float(safety_tp + safety_fp),
        "safety_gold_stop_support": float(safety_tp + safety_fn),
        "confirmation_accuracy": confirmation_matches / total,
        "slot_f1": sum(slot_scores) / total,
        "slot_f1_soft": sum(slot_soft_scores) / total,
        "contract_exact_match": exact_matches / total,
    }
    return EvaluationResult(metrics=metrics, failure_slices=failure_slices)


_REQUIRED_CONTRACT_FIELDS = {
    "task_type",
    "route",
    "safety",
    "confirmation_required",
    "slots",
    "normalized_command",
    "language",
    "contract_version",
}


def _sanitize_public_summary(text: str) -> str:
    sanitized = PRIVATE_PATH_RE.sub("<private_path>", text)
    sanitized = PRIVATE_IP_RE.sub("<private_ip>", sanitized)
    return SECRET_RE.sub("<secret>", sanitized)


def _sanitize_public_value(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_public_summary(value)
    if isinstance(value, dict):
        return {str(_sanitize_public_value(key)): _sanitize_public_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_public_value(item) for item in value]
    return value


def _observed_value_summary(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "empty string"
        return _sanitize_public_summary(f"string({len(value)}): {text[:80]}")
    if isinstance(value, dict):
        if not value:
            return "empty object"
        keys = ", ".join(sorted(str(key) for key in value.keys())[:8])
        return _sanitize_public_summary(f"object with keys: {keys}")
    if isinstance(value, list):
        return _sanitize_public_summary(f"array with {len(value)} item(s)")
    if value is None:
        return "null"
    return _sanitize_public_summary(f"{type(value).__name__}: {str(value)[:80]}")


def _alignment_value_summary(value: Any, *, missing: bool = False) -> str:
    if missing:
        return "missing"
    return _observed_value_summary(value)


def _issue(
    *,
    row_id: str,
    field_path: str,
    issue_category: str,
    observed_value: Any,
    expected_constraint: str,
) -> dict[str, str]:
    return {
        "row_id": _sanitize_id(row_id),
        "field_path": field_path,
        "issue_category": issue_category,
        "observed_value_summary": _observed_value_summary(observed_value),
        "expected_constraint": expected_constraint,
    }


_ALIGNMENT_FIELD_PATHS = (
    "task_type",
    "route",
    "safety.allow",
    "safety.reason",
    "confirmation_required",
    "slots",
    "normalized_command",
    "language",
    "contract_version",
)


_MISSING = object()


def _field_value(value: dict[str, Any], field_path: str) -> Any:
    current: Any = value
    for part in field_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _alignment_mismatch(
    *,
    row_id: str,
    field_path: str,
    gold_value: Any,
    prediction_value: Any,
) -> dict[str, str]:
    gold_missing = gold_value is _MISSING
    prediction_missing = prediction_value is _MISSING
    if prediction_missing:
        mismatch_category = "missing_prediction_field"
    elif gold_missing:
        mismatch_category = "missing_gold_field"
    elif type(gold_value) is not type(prediction_value):
        mismatch_category = "type_mismatch"
    else:
        mismatch_category = "value_mismatch"
    return {
        "row_id": _sanitize_id(row_id),
        "field_path": field_path,
        "mismatch_category": mismatch_category,
        "gold_value_summary": _alignment_value_summary(gold_value, missing=gold_missing),
        "prediction_value_summary": _alignment_value_summary(prediction_value, missing=prediction_missing),
    }


def diagnose_alignment_mismatches(rows: list[SFTDatasetRow], predictions: dict[str, Any]) -> dict[str, Any]:
    diagnostics_rows: list[dict[str, Any]] = []
    field_mismatch_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    schema_invalid_prediction_count = 0

    for row in rows:
        gold = as_contract(row.target_contract).to_dict()
        raw_prediction = predictions.get(row.id)
        parsed_prediction = raw_prediction
        if isinstance(raw_prediction, str):
            try:
                parsed_prediction = json.loads(raw_prediction)
            except json.JSONDecodeError:
                parsed_prediction = None
        if _prediction_to_contract(raw_prediction) is None:
            schema_invalid_prediction_count += 1

        prediction_object = parsed_prediction if isinstance(parsed_prediction, dict) else {}
        mismatches: list[dict[str, str]] = []
        for field_path in _ALIGNMENT_FIELD_PATHS:
            gold_value = _field_value(gold, field_path)
            prediction_value = _field_value(prediction_object, field_path)
            if gold_value == prediction_value:
                continue
            mismatch = _alignment_mismatch(
                row_id=row.id,
                field_path=field_path,
                gold_value=gold_value,
                prediction_value=prediction_value,
            )
            mismatches.append(mismatch)
            field_mismatch_counts[field_path] = field_mismatch_counts.get(field_path, 0) + 1
            category = mismatch["mismatch_category"]
            category_counts[category] = category_counts.get(category, 0) + 1
        if mismatches:
            diagnostics_rows.append({"row_id": _sanitize_id(row.id), "mismatches": mismatches})

    return {
        "diagnostic_kind": "browser_task_contract_alignment_mismatch",
        "summary": {
            "gold_row_count": len(rows),
            "prediction_count": len(predictions),
            "row_mismatch_count": len(diagnostics_rows),
            "schema_invalid_prediction_count": schema_invalid_prediction_count,
            "field_mismatch_counts": dict(sorted(field_mismatch_counts.items())),
            "mismatch_category_counts": dict(sorted(category_counts.items())),
        },
        "rows": diagnostics_rows,
        "claims": {
            "invalid_predictions_remain_invalid": True,
            "field_level_public_sample_evidence_only": True,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "full_private_corpus_claim": False,
            "live_browser_benchmark_claim": False,
        },
    }


def _schema_guard_rows_by_id(schema_guard_summary: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(schema_guard_summary, dict):
        return {}
    rows = schema_guard_summary.get("rows")
    if not isinstance(rows, list):
        return {}
    guard_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id") or row.get("row_id")
        if isinstance(row_id, str):
            guard_rows[_sanitize_id(row_id)] = row
    return guard_rows


def _metrics_payload(metrics: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(metrics, dict):
        return {}
    payload = metrics.get("metrics")
    return payload if isinstance(payload, dict) else {}


def _primary_confirmation_rerun_failure_family(
    *,
    raw_prediction: Any,
    mismatches: list[dict[str, str]],
    schema_guard: dict[str, Any],
) -> str:
    mismatch_paths = {mismatch["field_path"] for mismatch in mismatches}
    missing_fields = schema_guard.get("raw_attempt_missing_required_fields")
    missing_required_fields = missing_fields if isinstance(missing_fields, list) else []
    if _prediction_to_contract(raw_prediction) is None:
        if "confirmation_required" in missing_required_fields or "confirmation_required" in mismatch_paths:
            return "missing_required_field_schema_failure"
        return "schema_failure"
    if mismatch_paths & {"task_type", "route", "safety.reason"}:
        return "semantic_task_route_safety_mismatch"
    if mismatch_paths == {"normalized_command"}:
        return "strict_string_field_exact_match_mismatch"
    if "normalized_command" in mismatch_paths:
        return "strict_string_field_exact_match_mismatch"
    return "other_field_exact_match_mismatch"


def _confirmation_rerun_claims() -> dict[str, bool]:
    return {
        "local_evidence_only_analysis": True,
        "does_not_repair_normalize_coerce_replace_or_rescore": True,
        "a100_execution_performed": False,
        "training_or_prediction_rerun_performed": False,
        "prompt_training_decoding_or_metric_logic_changed": False,
        "checkpoint_release": False,
        "adapter_release": False,
        "held_out_generalization_claim": False,
        "production_readiness_claim": False,
        "public_full_corpus_release_claim": False,
        "live_browser_benchmark_improvement_claim": False,
        "model_quality_improvement_claim": False,
    }


def diagnose_confirmation_rerun_row_mismatches(
    rows: list[SFTDatasetRow],
    predictions: dict[str, Any],
    *,
    metrics: dict[str, Any] | None = None,
    schema_guard_summary: dict[str, Any] | None = None,
    source_artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    alignment = diagnose_alignment_mismatches(rows, predictions)
    guard_rows = _schema_guard_rows_by_id(schema_guard_summary)
    alignment_rows = {row["row_id"]: row for row in alignment.get("rows", [])}
    family_counts: dict[str, int] = {}
    diagnostic_rows: list[dict[str, Any]] = []

    for row in rows:
        row_id = _sanitize_id(row.id)
        alignment_row = alignment_rows.get(row_id, {"row_id": row_id, "mismatches": []})
        mismatches = alignment_row["mismatches"]
        schema_guard = guard_rows.get(row_id, {})
        family = _primary_confirmation_rerun_failure_family(
            raw_prediction=predictions.get(row.id),
            mismatches=mismatches,
            schema_guard=schema_guard,
        )
        _increment_count(family_counts, family)
        diagnostic_rows.append(
            {
                "row_id": row_id,
                "primary_failure_family": family,
                "source_prediction_status": {
                    "schema_valid_prediction": _prediction_to_contract(predictions.get(row.id)) is not None,
                    "validated_output_schema_valid": schema_guard.get("validated_output_schema_valid"),
                    "validated_output_source": schema_guard.get("validated_output_source"),
                    "raw_attempt_missing_required_fields": schema_guard.get(
                        "raw_attempt_missing_required_fields", []
                    ),
                },
                "mismatches": mismatches,
            }
        )

    metric_values = _metrics_payload(metrics)
    summary = {
        **alignment["summary"],
        "family_counts": dict(sorted(family_counts.items())),
        "strict_final_json_valid_rate": metric_values.get("json_valid_rate"),
        "strict_final_task_type_accuracy": metric_values.get("task_type_accuracy"),
        "strict_final_route_accuracy": metric_values.get("route_accuracy"),
        "strict_final_confirmation_accuracy": metric_values.get("confirmation_accuracy"),
        "strict_final_slot_f1": metric_values.get("slot_f1"),
        "strict_final_contract_exact_match": metric_values.get("contract_exact_match"),
        "metrics_preserved_from_source": bool(metric_values),
    }
    safe_source_artifacts = {
        str(key): _sanitize_public_summary(str(value)) for key, value in (source_artifacts or {}).items()
    }
    return {
        "diagnostic_kind": "confirmation_required_rerun_row_mismatch_diagnosis",
        "summary": summary,
        "rows": diagnostic_rows,
        "source_artifacts": safe_source_artifacts,
        "source_artifact_policy": {
            "uses_prior_public_sample_artifacts_only": True,
            "a100_execution_performed": False,
            "prediction_rerun_performed": False,
            "training_or_decoding_changed": False,
            "prompt_changed": False,
            "evaluator_metrics_changed": False,
        },
        "claims": _confirmation_rerun_claims(),
    }


def _primary_a100_normalized_rerun_failure_family(
    *,
    raw_prediction: Any,
    mismatches: list[dict[str, str]],
    schema_guard: dict[str, Any],
) -> str:
    mismatch_paths = {mismatch["field_path"] for mismatch in mismatches}
    missing_fields = schema_guard.get("raw_attempt_missing_required_fields")
    missing_required_fields = missing_fields if isinstance(missing_fields, list) else []
    if "confirmation_required" in missing_required_fields or "confirmation_required" in mismatch_paths:
        return "schema_missing_confirmation_required"

    parsed_prediction = raw_prediction
    if isinstance(raw_prediction, str):
        try:
            parsed_prediction = json.loads(raw_prediction)
        except json.JSONDecodeError:
            parsed_prediction = {}
    if isinstance(parsed_prediction, dict):
        task_type = parsed_prediction.get("task_type")
        if isinstance(task_type, str) and task_type not in TASK_TYPES:
            return "schema_invalid_task_type_enum"

    if _prediction_to_contract(raw_prediction) is None:
        return "schema_invalid_prediction_other"
    if mismatch_paths & {"task_type", "route", "safety.allow", "safety.reason", "slots"}:
        return "schema_valid_task_route_safety_slot_mismatch"
    if mismatch_paths == {"normalized_command"}:
        return "strict_string_field_exact_match_mismatch"
    if "normalized_command" in mismatch_paths:
        return "normalized_command_with_other_field_mismatch"
    return "other_field_exact_match_mismatch"


def _normalized_rerun_counts(
    *,
    metrics: dict[str, Any] | None,
    schema_guard_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    schema_summary = (
        schema_guard_summary.get("summary", {}) if isinstance(schema_guard_summary, dict) else {}
    )
    metric_counts = metrics.get("normalized_command_counts", {}) if isinstance(metrics, dict) else {}
    if not isinstance(schema_summary, dict):
        schema_summary = {}
    if not isinstance(metric_counts, dict):
        metric_counts = {}
    return {
        "normalized_command_exact_match_count": schema_summary.get(
            "normalized_command_exact_match_count", metric_counts.get("exact_match_count")
        ),
        "normalized_command_mismatch_count": schema_summary.get(
            "normalized_command_mismatch_count", metric_counts.get("mismatch_count")
        ),
        "validated_output_schema_valid_count": schema_summary.get("validated_output_schema_valid_count"),
    }


def diagnose_a100_normalized_rerun_row_mismatches(
    rows: list[SFTDatasetRow],
    predictions: dict[str, Any],
    *,
    metrics: dict[str, Any] | None = None,
    schema_guard_summary: dict[str, Any] | None = None,
    source_artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    alignment = diagnose_alignment_mismatches(rows, predictions)
    guard_rows = _schema_guard_rows_by_id(schema_guard_summary)
    alignment_rows = {row["row_id"]: row for row in alignment.get("rows", [])}
    family_counts: dict[str, int] = {}
    diagnostic_rows: list[dict[str, Any]] = []

    for row in rows:
        row_id = _sanitize_id(row.id)
        alignment_row = alignment_rows.get(row_id, {"row_id": row_id, "mismatches": []})
        mismatches = alignment_row["mismatches"]
        schema_guard = guard_rows.get(row_id, {})
        raw_prediction = predictions.get(row.id)
        family = _primary_a100_normalized_rerun_failure_family(
            raw_prediction=raw_prediction,
            mismatches=mismatches,
            schema_guard=schema_guard,
        )
        _increment_count(family_counts, family)
        diagnostic_rows.append(
            {
                "row_id": row_id,
                "primary_failure_family": family,
                "source_prediction_status": {
                    "schema_valid_prediction": _prediction_to_contract(raw_prediction) is not None,
                    "validated_output_schema_valid": schema_guard.get("validated_output_schema_valid"),
                    "validated_output_source": schema_guard.get("validated_output_source"),
                    "raw_attempt_missing_required_fields": schema_guard.get(
                        "raw_attempt_missing_required_fields", []
                    ),
                    "raw_attempt_validation_error": schema_guard.get("raw_attempt_validation_error"),
                },
                "mismatches": mismatches,
            }
        )

    metric_values = _metrics_payload(metrics)
    normalized_counts = _normalized_rerun_counts(metrics=metrics, schema_guard_summary=schema_guard_summary)
    summary = {
        **alignment["summary"],
        "family_counts": dict(sorted(family_counts.items())),
        "strict_final_json_valid_rate": metric_values.get("json_valid_rate"),
        "strict_final_task_type_accuracy": metric_values.get("task_type_accuracy"),
        "strict_final_route_accuracy": metric_values.get("route_accuracy"),
        "strict_final_confirmation_accuracy": metric_values.get("confirmation_accuracy"),
        "strict_final_slot_f1": metric_values.get("slot_f1"),
        "strict_final_contract_exact_match": metric_values.get("contract_exact_match"),
        "metrics_preserved_from_source": bool(metric_values),
        **normalized_counts,
    }
    safe_source_artifacts = {
        str(key): _sanitize_public_summary(str(value)) for key, value in (source_artifacts or {}).items()
    }
    return {
        "diagnostic_kind": "a100_normalized_rerun_row_mismatch_diagnosis",
        "summary": summary,
        "rows": diagnostic_rows,
        "source_artifacts": safe_source_artifacts,
        "source_artifact_policy": {
            "uses_prior_public_sample_artifacts_only": True,
            "a100_execution_performed": False,
            "prediction_rerun_performed": False,
            "training_or_decoding_changed": False,
            "prompt_changed": False,
            "schema_or_parser_changed": False,
            "retry_changed": False,
            "evaluator_metrics_changed": False,
            "normalization_or_semantic_equivalence_added": False,
        },
        "claims": {
            **_confirmation_rerun_claims(),
            "semantic_equivalence_scoring_performed": False,
            "normalized_command_normalization_performed": False,
            "normalized_command_semantic_equivalence_marked": False,
            "prediction_repair_or_rescore_performed": False,
            "predictions_repaired_or_replaced": False,
            "predictions_rescored": False,
            "invalid_predictions_remain_invalid": True,
        },
    }


def _normalized_command_context_kind(row: dict[str, Any], mismatch_paths: set[str]) -> str:
    family = row.get("primary_failure_family")
    status = row.get("source_prediction_status")
    schema_valid_prediction = status.get("schema_valid_prediction") if isinstance(status, dict) else None
    if family == "missing_required_field_schema_failure" or schema_valid_prediction is False:
        return "co_occurs_with_schema_failure"
    if family == "semantic_task_route_safety_mismatch" or mismatch_paths & {
        "task_type",
        "route",
        "safety.allow",
        "safety.reason",
    }:
        return "co_occurs_with_semantic_task_route_safety"
    if mismatch_paths == {"normalized_command"}:
        return "strict_string_only"
    return "co_occurs_with_other_field_mismatch"


def diagnose_normalized_command_string_mismatches(
    row_mismatch_diagnostics: dict[str, Any],
    *,
    source_artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_summary = row_mismatch_diagnostics.get("summary", {})
    source_rows = row_mismatch_diagnostics.get("rows", [])
    if not isinstance(source_summary, dict):
        source_summary = {}
    if not isinstance(source_rows, list):
        source_rows = []

    context_counts: dict[str, int] = {}
    diagnostic_rows: list[dict[str, Any]] = []
    for row in source_rows:
        if not isinstance(row, dict):
            continue
        mismatches = row.get("mismatches", [])
        if not isinstance(mismatches, list):
            continue
        normalized_mismatches = [
            mismatch
            for mismatch in mismatches
            if isinstance(mismatch, dict) and mismatch.get("field_path") == "normalized_command"
        ]
        if not normalized_mismatches:
            continue
        mismatch_paths = {
            str(mismatch.get("field_path"))
            for mismatch in mismatches
            if isinstance(mismatch, dict) and isinstance(mismatch.get("field_path"), str)
        }
        context_kind = _normalized_command_context_kind(row, mismatch_paths)
        _increment_count(context_counts, context_kind)
        co_occurring_fields = sorted(path for path in mismatch_paths if path != "normalized_command")
        sanitized_mismatch = {
            str(key): _sanitize_public_summary(str(value)) for key, value in normalized_mismatches[0].items()
        }
        diagnostic_rows.append(
            {
                "row_id": _sanitize_id(str(row.get("row_id", "unknown-row"))),
                "context_kind": context_kind,
                "source_primary_failure_family": _sanitize_public_summary(
                    str(row.get("primary_failure_family", "unknown"))
                ),
                "co_occurring_field_paths": co_occurring_fields,
                "source_prediction_status": row.get("source_prediction_status", {}),
                "mismatch": sanitized_mismatch,
            }
        )

    strict_metric_keys = (
        "strict_final_json_valid_rate",
        "strict_final_task_type_accuracy",
        "strict_final_route_accuracy",
        "strict_final_confirmation_accuracy",
        "strict_final_slot_f1",
        "strict_final_contract_exact_match",
    )
    strict_metrics = {key: source_summary.get(key) for key in strict_metric_keys}
    inherited_source_artifacts = (
        row_mismatch_diagnostics.get("source_artifacts", {})
        if isinstance(row_mismatch_diagnostics.get("source_artifacts"), dict)
        else {}
    )
    safe_source_artifacts = {
        str(key): _sanitize_public_summary(str(value))
        for key, value in (source_artifacts or {}).items()
    }
    safe_transitive_source_artifacts = {
        str(key): _sanitize_public_summary(str(value)) for key, value in inherited_source_artifacts.items()
    }
    summary = {
        "source_diagnostic_kind": row_mismatch_diagnostics.get("diagnostic_kind"),
        "source_row_mismatch_count": source_summary.get("row_mismatch_count"),
        "normalized_command_mismatch_count": len(diagnostic_rows),
        "string_only_count": context_counts.get("strict_string_only", 0),
        "co_occurs_with_schema_failure_count": context_counts.get("co_occurs_with_schema_failure", 0),
        "co_occurs_with_semantic_task_route_safety_count": context_counts.get(
            "co_occurs_with_semantic_task_route_safety", 0
        ),
        "context_counts": dict(sorted(context_counts.items())),
        "strict_metrics_preserved": bool(source_summary.get("metrics_preserved_from_source")),
        "metrics_preserved_from_source": bool(source_summary.get("metrics_preserved_from_source")),
        **strict_metrics,
    }
    return {
        "diagnostic_kind": "normalized_command_string_mismatch_diagnosis",
        "summary": summary,
        "rows": diagnostic_rows,
        "source_artifacts": safe_source_artifacts,
        "transitive_source_artifacts": safe_transitive_source_artifacts,
        "source_artifact_policy": {
            "uses_prior_public_sample_artifacts_only": True,
            "derives_from_row_mismatch_diagnostics": True,
            "primary_inputs_are_row_mismatch_artifacts": True,
            "transitive_rerun_artifacts_are_linked_for_traceability_only": True,
            "a100_execution_performed": False,
            "prediction_rerun_performed": False,
            "training_or_decoding_changed": False,
            "prompt_changed": False,
            "evaluator_metrics_changed": False,
            "normalization_or_semantic_equivalence_added": False,
        },
        "claims": {
            **_confirmation_rerun_claims(),
            "semantic_equivalence_scoring_performed": False,
            "normalized_command_normalization_performed": False,
            "normalized_command_semantic_equivalence_marked": False,
            "does_not_normalize_or_semantically_score_normalized_command": True,
            "predictions_repaired_or_replaced": False,
            "predictions_rescored": False,
            "search_query_terms_marked_equivalent": False,
        },
    }


def _retry_template_slot_family(gold_slots: Any, predicted_slots: Any) -> str:
    if not isinstance(gold_slots, dict) or not isinstance(predicted_slots, dict):
        return "slot_type_or_shape_mismatch"
    gold_keys = set(gold_slots)
    predicted_keys = set(predicted_slots)
    if gold_keys == {"query"} and {"city", "date"} <= predicted_keys and "query" not in predicted_keys:
        return "city_date_slots_instead_of_query"
    if "query" in gold_slots and "query" in predicted_slots and gold_slots["query"] != predicted_slots["query"]:
        return "query_slot_strict_string_mismatch"
    if gold_slots != predicted_slots:
        return "other_slot_exact_match_mismatch"
    return "slot_matches"


def diagnose_retry_template_slot_exact_match_mismatches(
    rows: list[SFTDatasetRow],
    predictions: dict[str, Any],
    *,
    metrics: dict[str, Any] | None = None,
    schema_guard_summary: dict[str, Any] | None = None,
    source_artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    alignment = diagnose_alignment_mismatches(rows, predictions)
    guard_rows = _schema_guard_rows_by_id(schema_guard_summary)
    alignment_rows = {row["row_id"]: row for row in alignment.get("rows", [])}
    slot_family_counts: dict[str, int] = {}
    diagnostic_rows: list[dict[str, Any]] = []

    for row in rows:
        row_id = _sanitize_id(row.id)
        raw_prediction = predictions.get(row.id)
        parsed_prediction = _parse_prediction_object(raw_prediction)
        prediction_object = parsed_prediction if isinstance(parsed_prediction, dict) else {}
        gold_contract = as_contract(row.target_contract).to_dict()
        slot_family = _retry_template_slot_family(
            gold_contract.get("slots"),
            prediction_object.get("slots"),
        )
        if slot_family != "slot_matches":
            _increment_count(slot_family_counts, slot_family)
        alignment_row = alignment_rows.get(row_id, {"row_id": row_id, "mismatches": []})
        mismatches = alignment_row["mismatches"]
        mismatch_paths = {
            str(mismatch.get("field_path"))
            for mismatch in mismatches
            if isinstance(mismatch, dict) and isinstance(mismatch.get("field_path"), str)
        }
        schema_guard = guard_rows.get(row_id, {})
        diagnostic_rows.append(
            {
                "row_id": row_id,
                "primary_slot_mismatch_family": slot_family,
                "normalized_command_mismatch_present": "normalized_command" in mismatch_paths,
                "source_prediction_status": {
                    "schema_valid_prediction": _prediction_to_contract(raw_prediction) is not None,
                    "validated_output_schema_valid": schema_guard.get("validated_output_schema_valid"),
                    "validated_output_source": schema_guard.get("validated_output_source"),
                    "raw_attempt_missing_required_fields": schema_guard.get(
                        "raw_attempt_missing_required_fields", []
                    ),
                    "raw_attempt_validation_error": schema_guard.get("raw_attempt_validation_error"),
                },
                "mismatches": mismatches,
            }
        )

    metric_values = _metrics_payload(metrics)
    schema_summary = (
        schema_guard_summary.get("summary", {}) if isinstance(schema_guard_summary, dict) else {}
    )
    if not isinstance(schema_summary, dict):
        schema_summary = {}
    field_counts = alignment["summary"].get("field_mismatch_counts", {})
    normalized_command_mismatch_count = (
        field_counts.get("normalized_command", 0) if isinstance(field_counts, dict) else 0
    )
    safe_source_artifacts = {
        str(key): _sanitize_public_summary(str(value)) for key, value in (source_artifacts or {}).items()
    }
    return {
        "diagnostic_kind": "retry_template_slot_exact_match_mismatch_diagnosis",
        "summary": {
            **alignment["summary"],
            "slot_family_counts": dict(sorted(slot_family_counts.items())),
            "normalized_command_mismatch_count": normalized_command_mismatch_count,
            "validated_output_schema_valid_count": schema_summary.get("validated_output_schema_valid_count"),
            "strict_final_json_valid_rate": metric_values.get("json_valid_rate"),
            "strict_final_task_type_accuracy": metric_values.get("task_type_accuracy"),
            "strict_final_route_accuracy": metric_values.get("route_accuracy"),
            "strict_final_confirmation_accuracy": metric_values.get("confirmation_accuracy"),
            "strict_final_slot_f1": metric_values.get("slot_f1"),
            "strict_final_contract_exact_match": metric_values.get("contract_exact_match"),
            "metrics_preserved_from_source": bool(metric_values),
        },
        "rows": diagnostic_rows,
        "source_artifacts": safe_source_artifacts,
        "source_artifact_policy": {
            "uses_prior_public_sample_artifacts_only": True,
            "a100_execution_performed": False,
            "prediction_rerun_performed": False,
            "training_or_decoding_changed": False,
            "prompt_changed": False,
            "schema_or_parser_changed": False,
            "retry_changed": False,
            "evaluator_metrics_changed": False,
            "slot_normalization_performed": False,
            "normalization_or_semantic_equivalence_added": False,
        },
        "claims": {
            **_confirmation_rerun_claims(),
            "slot_normalization_performed": False,
            "normalized_command_normalization_performed": False,
            "semantic_equivalence_scoring_performed": False,
            "prediction_repair_or_rescore_performed": False,
            "predictions_repaired_or_replaced": False,
            "predictions_rescored": False,
            "model_quality_improvement_claim": False,
        },
    }


def _count_values(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _is_path_like_route(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return text.startswith(("/", "./", "../")) or "://" in text or text.startswith("www.")


def _parse_prediction_object(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _limited_examples(examples: list[dict[str, str]], limit: int = 5) -> list[dict[str, str]]:
    return examples[:limit]


def _target_shape_summary(rows: list[SFTDatasetRow]) -> dict[str, Any]:
    path_like_examples: list[dict[str, str]] = []
    list_slots_examples: list[dict[str, str]] = []
    for row in rows:
        contract = as_contract(row.target_contract).to_dict()
        if _is_path_like_route(contract.get("route")):
            path_like_examples.append(
                {
                    "row_id": _sanitize_id(row.id),
                    "route": _observed_value_summary(contract.get("route")),
                }
            )
        if isinstance(contract.get("slots"), list):
            list_slots_examples.append(
                {
                    "row_id": _sanitize_id(row.id),
                    "slots": _observed_value_summary(contract.get("slots")),
                }
            )
    return {
        "path_like_route_count": len(path_like_examples),
        "list_slots_count": len(list_slots_examples),
        "path_like_route_examples": _limited_examples(path_like_examples),
        "list_slots_examples": _limited_examples(list_slots_examples),
    }


def _prediction_symptom_summary(rows: list[SFTDatasetRow], predictions: dict[str, Any]) -> dict[str, Any]:
    path_like_examples: list[dict[str, str]] = []
    list_slots_examples: list[dict[str, str]] = []
    missing_confirmation_required_examples: list[dict[str, str]] = []
    schema_invalid_prediction_count = 0
    missing_prediction_count = 0
    for row in rows:
        if row.id not in predictions:
            missing_prediction_count += 1
            continue
        raw_prediction = predictions[row.id]
        parsed_prediction = _parse_prediction_object(raw_prediction)
        if _prediction_to_contract(raw_prediction) is None:
            schema_invalid_prediction_count += 1
        if not isinstance(parsed_prediction, dict):
            continue
        if "confirmation_required" not in parsed_prediction:
            missing_confirmation_required_examples.append(
                {
                    "row_id": _sanitize_id(row.id),
                    "prediction": _observed_value_summary(parsed_prediction),
                }
            )
        route = parsed_prediction.get("route")
        if _is_path_like_route(route):
            path_like_examples.append(
                {
                    "row_id": _sanitize_id(row.id),
                    "route": _observed_value_summary(route),
                }
            )
        slots = parsed_prediction.get("slots")
        if isinstance(slots, list):
            list_slots_examples.append(
                {
                    "row_id": _sanitize_id(row.id),
                    "slots": _observed_value_summary(slots),
                }
            )
    return {
        "prediction_count": len(predictions),
        "missing_prediction_count": missing_prediction_count,
        "path_like_route_count": len(path_like_examples),
        "list_slots_count": len(list_slots_examples),
        "schema_invalid_prediction_count": schema_invalid_prediction_count,
        "missing_confirmation_required_count": len(missing_confirmation_required_examples),
        "invalid_predictions_remain_invalid": True,
        "path_like_route_examples": _limited_examples(path_like_examples),
        "list_slots_examples": _limited_examples(list_slots_examples),
        "missing_confirmation_required_examples": _limited_examples(missing_confirmation_required_examples),
    }


def _split_coverage(
    rows: list[SFTDatasetRow],
    *,
    training_config: dict[str, Any],
    prediction_metadata: dict[str, Any],
) -> dict[str, Any]:
    training_split = str(training_config.get("dataset_split", "train"))
    prediction_split = str(prediction_metadata.get("prediction_split", training_config.get("prediction_split", "all")))
    split_counts = _count_values([row.split for row in rows])
    training_rows = [row for row in rows if row.split == training_split]
    prediction_rows = rows if prediction_split == "all" else [row for row in rows if row.split == prediction_split]
    return {
        "configured_training_split": training_split,
        "configured_prediction_split": prediction_split,
        "gold_split_counts": split_counts,
        "training_row_count": len(training_rows),
        "prediction_gold_row_count": len(prediction_rows),
    }


def _training_coverage(rows: list[SFTDatasetRow], training_split: str) -> dict[str, Any]:
    training_rows = [row for row in rows if row.split == training_split]
    contracts = [as_contract(row.target_contract) for row in training_rows]
    return {
        "task_type_counts": _count_values([contract.task_type for contract in contracts]),
        "route_counts": _count_values([contract.route for contract in contracts]),
    }


_PROMPT_CONSTRAINT_FIELDS = (
    "task_type_enum_visible",
    "route_enum_visible",
    "route_not_url_or_path_visible",
    "route_execution_channel_visible",
    "route_domain_values_not_route_visible",
    "weather_to_search_route_example_visible",
    "confirmation_required_boolean_visible",
    "weather_to_search_confirmation_false_visible",
    "slots_object_not_array_visible",
)


def _prediction_run_prompt_evidence(prediction_metadata: dict[str, Any]) -> dict[str, Any]:
    raw_constraints = prediction_metadata.get("prompt_constraints")
    constraints = raw_constraints if isinstance(raw_constraints, dict) else {}
    constraint_summary = {
        field: bool(constraints[field]) for field in _PROMPT_CONSTRAINT_FIELDS if field in constraints
    }
    evidence_gaps: list[str] = []
    if not isinstance(raw_constraints, dict):
        evidence_gaps.append("prompt_constraints_at_prediction_time")
    missing_fields = [field for field in _PROMPT_CONSTRAINT_FIELDS if field not in constraints]
    if isinstance(raw_constraints, dict) and missing_fields:
        evidence_gaps.append("prompt_constraint_fields")
    return {
        "prompt_constraints_present": isinstance(raw_constraints, dict),
        "fields_present": sorted(constraint_summary),
        "constraints": constraint_summary,
        "evidence_gaps": evidence_gaps,
        "current_prompt_constraints_are_rerun_preparation_not_old_run_evidence": not isinstance(
            raw_constraints, dict
        ),
    }


def _decoding_evidence(prediction_metadata: dict[str, Any]) -> dict[str, Any]:
    raw_policy = prediction_metadata.get("decoding_policy")
    policy = raw_policy if isinstance(raw_policy, dict) else {}
    fields = (
        "strategy",
        "do_sample",
        "max_new_tokens",
        "raw_decoded_sidecar_written",
        "schema_repair_applied",
    )
    policy_summary = {field: policy[field] for field in fields if field in policy}
    evidence_gaps: list[str] = []
    if not isinstance(raw_policy, dict):
        evidence_gaps.append("decoding_policy")
    if policy.get("raw_decoded_sidecar_written") is not True:
        evidence_gaps.append("raw_decoded_sidecar")
    if "generated_token_count" not in policy and "generated_token_count" not in prediction_metadata:
        evidence_gaps.append("generated_token_count")
    finish_keys = {"eos_reached", "eos_token_seen", "finish_reason", "finish_state"}
    if not any(key in policy or key in prediction_metadata for key in finish_keys):
        evidence_gaps.append("eos_or_finish_state")
    return {
        "decoding_policy_present": isinstance(raw_policy, dict),
        "fields_present": sorted(policy_summary),
        "policy": policy_summary,
        "evidence_gaps": evidence_gaps,
        "interprets_gaps_as_missing_evidence_not_cause": True,
    }


def _alignment_rows(rows: list[SFTDatasetRow], predictions: dict[str, Any], split: str) -> list[SFTDatasetRow]:
    if predictions:
        predicted_ids = set(predictions)
        return [row for row in rows if row.id in predicted_ids]
    if split == "all":
        return rows
    return [row for row in rows if row.split == split]


def _system_user_prefix(text: str) -> str:
    marker = "\nassistant:"
    if marker in text:
        return text.split(marker, 1)[0]
    return text


def _core_system_user_prefix(text: str) -> str:
    core = _system_user_prefix(text).replace(PREDICTION_OUTPUT_BOUNDARY_RULES, "")
    return core.replace(f"Canonical valid one-shot example:{CONTRACT_CANONICAL_ONE_SHOT}。", "")


def _target_span(training_text: str, assistant_target: str) -> dict[str, Any]:
    start = training_text.find(assistant_target)
    if start < 0:
        return {"status": "not_found", "start": None, "end": None}
    return {"status": "found", "start": start, "end": start + len(assistant_target)}


def _public_config_value(value: Any, *, private_placeholder: str = "<private_value>") -> Any:
    if isinstance(value, dict):
        return {
            str(key): _public_config_value(item, private_placeholder=private_placeholder)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_public_config_value(item, private_placeholder=private_placeholder) for item in value]
    if not isinstance(value, str):
        return value
    if any(value.startswith(prefix) for prefix in ("/mnt/data/", "/Users/", "/root/", "/tmp/", "/private/")):
        return private_placeholder
    return _sanitize_public_summary(value)


def _metadata_field_alignment(config_value: Any, metadata_value: Any) -> dict[str, Any]:
    config_public = _public_config_value(config_value)
    metadata_public = _public_config_value(metadata_value)
    return {
        "training_config": config_public,
        "prediction_metadata": metadata_public,
        "matches": config_public == metadata_public,
    }


def _base_model_alignment(training_config: dict[str, Any], prediction_metadata: dict[str, Any]) -> dict[str, Any]:
    config_base = _public_config_value(training_config.get("base_model"), private_placeholder="<private_base_model>")
    metadata_base = _public_config_value(
        prediction_metadata.get("base_model"),
        private_placeholder="<private_base_model>",
    )
    if metadata_base == "<private_base_model>" and isinstance(config_base, str) and config_base:
        status = "prediction_metadata_private_placeholder"
    elif config_base == metadata_base:
        status = "matches"
    else:
        status = "differs"
    return {
        "training_config": config_base,
        "prediction_metadata": metadata_base,
        "status": status,
    }


def _adapter_gate(training_config: dict[str, Any], prediction_metadata: dict[str, Any]) -> dict[str, Any]:
    prediction_gate = prediction_metadata.get("prediction_gate")
    gate = prediction_gate if isinstance(prediction_gate, dict) else {}
    adapter_path = training_config.get("adapter_path")
    return {
        "adapter_configured": bool(
            gate.get("adapter_configured")
            if "adapter_configured" in gate
            else isinstance(adapter_path, str) and bool(adapter_path.strip())
        ),
        "cli_run_prediction": bool(gate.get("cli_run_prediction", False)),
        "config_allow_private_prediction": bool(
            gate.get("config_allow_private_prediction", training_config.get("allow_private_prediction", False))
        ),
        "fixture_mode": bool(gate.get("fixture_mode", False)),
        "will_run_private_prediction": bool(gate.get("will_run_private_prediction", False)),
        "adapter_path_public_safe": "<configured_not_disclosed>"
        if isinstance(adapter_path, str) and adapter_path.strip()
        else "<not_configured>",
    }


def _formatting_policy_alignment(prediction_metadata: dict[str, Any]) -> dict[str, Any]:
    metadata_policy = prediction_metadata.get("formatting_policy")
    public_metadata_policy = {
        key: _public_config_value(metadata_policy.get(key))
        for key in FORMATTING_POLICY
        if isinstance(metadata_policy, dict) and key in metadata_policy
    }
    return {
        "expected": dict(FORMATTING_POLICY),
        "prediction_metadata": public_metadata_policy,
        "matches": public_metadata_policy == FORMATTING_POLICY,
    }


def _real_label_provenance_available(objective_inspection: dict[str, Any]) -> bool:
    label_source = objective_inspection.get("label_source")
    provenance = objective_inspection.get("label_provenance")
    if label_source not in {"real_training_labels", "actual_training_labels", "trl_collator_labels"}:
        return False
    if isinstance(provenance, dict):
        source_kind = str(provenance.get("source_kind", ""))
        non_real_source = source_kind in {
            "fixture",
            "simulated",
            "fixture_collator",
            "simulated_collator",
            "unavailable",
            "unspecified",
        }
        return provenance.get("real_training_path") is True and not non_real_source
    return provenance in {
        "real_training_labels",
        "actual_training_labels",
        "training_runtime",
        "private_training_runtime",
    }


def _label_provenance_payload(objective_inspection: dict[str, Any]) -> dict[str, Any]:
    provenance = objective_inspection.get("label_provenance")
    if isinstance(provenance, dict):
        return dict(provenance)
    if isinstance(provenance, str) and provenance:
        return {"source_kind": provenance}
    return {"source_kind": "unavailable", "real_training_path": False}


def _label_evidence_gaps(objective_inspection: dict[str, Any], *extra_gaps: str) -> list[str]:
    gaps: list[str] = []
    objective_gaps = objective_inspection.get("evidence_gaps")
    if isinstance(objective_gaps, list):
        gaps.extend(str(gap) for gap in objective_gaps if gap)
    gaps.extend(extra_gaps)
    for gap in ("real_training_labels_not_inspected", "real_training_label_provenance_missing"):
        if gap not in gaps:
            gaps.append(gap)
    return sorted(dict.fromkeys(gaps))


def _fixture_label_provenance(objective_inspection: dict[str, Any]) -> bool:
    provenance = _label_provenance_payload(objective_inspection)
    source_kind = str(provenance.get("source_kind", ""))
    if source_kind in {"fixture", "simulated", "fixture_collator", "simulated_collator"}:
        return True
    label_source = objective_inspection.get("label_source")
    return label_source in {"fixture_labels", "simulated_labels", "fixture_collator_labels"}


def _label_mask_evidence(objective_inspection: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(objective_inspection, dict):
        return {
            "status": "labels_unavailable",
            "true_label_mask_status": "unavailable",
            "source": "objective_inspection_not_loaded",
            "tokenizer_template_status": "unavailable",
            "collator_status": "unavailable",
            "label_source": "unavailable",
            "label_provenance": {"source_kind": "unavailable", "real_training_path": False},
            "label_tensor_available": False,
            "prompt_token_count": None,
            "assistant_token_count": None,
            "prompt_tokens_masked": None,
            "assistant_tokens_carry_loss": None,
            "evidence_gaps": ["real_training_labels_not_inspected", "real_training_label_provenance_missing"],
        }
    prompt_tokens_masked = objective_inspection.get("prompt_tokens_masked")
    assistant_tokens_carry_loss = objective_inspection.get("assistant_tokens_carry_loss")
    common = {
        "source": "objective_inspection",
        "inspection_status": objective_inspection.get("inspection_status", "unknown"),
        "tokenizer_template_status": objective_inspection.get("tokenizer_template_status", "unknown"),
        "collator_status": objective_inspection.get("collator_status", "unknown"),
        "label_source": objective_inspection.get("label_source", "unavailable"),
        "label_provenance": _label_provenance_payload(objective_inspection),
        "label_tensor_available": bool(objective_inspection.get("label_tensor_available", False)),
        "prompt_token_count": objective_inspection.get("prompt_token_count"),
        "assistant_token_count": objective_inspection.get("assistant_token_count"),
    }
    if (
        objective_inspection.get("inspection_status") == "inspectable"
        and _real_label_provenance_available(objective_inspection)
        and isinstance(prompt_tokens_masked, bool)
        and isinstance(assistant_tokens_carry_loss, bool)
    ):
        return {
            "status": "labels_inspected",
            "true_label_mask_status": "inspectable",
            **common,
            "prompt_tokens_masked": prompt_tokens_masked,
            "assistant_tokens_carry_loss": assistant_tokens_carry_loss,
            "evidence_gaps": [],
        }
    if _fixture_label_provenance(objective_inspection):
        return {
            "status": "labels_unavailable",
            "true_label_mask_status": "fixture_only",
            **common,
            "prompt_tokens_masked": None,
            "assistant_tokens_carry_loss": None,
            "evidence_gaps": _label_evidence_gaps(objective_inspection, "fixture_labels_not_real_training_proof"),
        }
    return {
        "status": "labels_unavailable",
        "true_label_mask_status": "unavailable",
        **common,
        "prompt_tokens_masked": None,
        "assistant_tokens_carry_loss": None,
        "evidence_gaps": _label_evidence_gaps(objective_inspection),
    }


def _prior_artifacts(
    *,
    prior_artifact_paths: dict[str, str] | None,
    prediction_metadata: dict[str, Any],
) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    if isinstance(prior_artifact_paths, dict):
        artifacts.update(
            {
                str(key): _sanitize_public_summary(str(value))
                for key, value in prior_artifact_paths.items()
                if isinstance(value, str) and value
            }
        )
    for section_name in ("diagnostic_artifacts", "sidecars"):
        section = prediction_metadata.get(section_name)
        if isinstance(section, dict):
            artifacts.update(
                {
                    str(key): _sanitize_public_summary(str(value))
                    for key, value in section.items()
                    if isinstance(value, str) and value
                }
            )
    return dict(sorted(artifacts.items()))


def _diagnose_sft_target_template_alignment(
    rows: list[SFTDatasetRow],
    predictions: dict[str, Any],
    *,
    training_config: dict[str, Any],
    prediction_metadata: dict[str, Any],
    prior_artifact_paths: dict[str, str] | None = None,
    objective_inspection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prediction_split = str(prediction_metadata.get("prediction_split", training_config.get("prediction_split", "all")))
    selected_rows = _alignment_rows(rows, predictions, prediction_split)
    row_evidence: list[dict[str, Any]] = []
    for row in selected_rows:
        training_text = format_sft_training_text(row, tokenizer=None)
        prediction_prompt = format_sft_prediction_prompt(row, tokenizer=None)
        assistant_target = canonical_contract_json(as_contract(row.target_contract))
        span = _target_span(training_text, assistant_target)
        same_prefix = _system_user_prefix(training_text) == _system_user_prefix(prediction_prompt)
        same_core_prefix = _core_system_user_prefix(training_text) == _core_system_user_prefix(prediction_prompt)
        prediction_boundary_visible = PREDICTION_OUTPUT_BOUNDARY_RULES in prediction_prompt
        target_in_training = assistant_target in training_text
        target_in_prompt = assistant_target in prediction_prompt
        row_evidence.append(
            {
                "row_id": _sanitize_id(row.id),
                "split": row.split,
                "training_text_sha256": hashlib.sha256(training_text.encode("utf-8")).hexdigest(),
                "prediction_prompt_sha256": hashlib.sha256(prediction_prompt.encode("utf-8")).hexdigest(),
                "assistant_contract_target_sha256": hashlib.sha256(assistant_target.encode("utf-8")).hexdigest(),
                "training_text_char_count": len(training_text),
                "prediction_prompt_char_count": len(prediction_prompt),
                "assistant_contract_target_char_count": len(assistant_target),
                "same_system_user_prefix": same_prefix,
                "same_core_system_user_prefix": same_core_prefix,
                "prediction_only_boundary_suffix_visible": prediction_boundary_visible,
                "assistant_contract_target_in_training_text": target_in_training,
                "assistant_contract_target_in_prediction_prompt": target_in_prompt,
                "assistant_target_only_in_training_text": target_in_training and not target_in_prompt,
                "prediction_prompt_ends_with_generation_boundary": prediction_prompt.rstrip().endswith("assistant:"),
                "assistant_target_span": span,
                "structural_proxy_status": "assistant_target_span_found"
                if span["status"] == "found"
                else "assistant_target_span_unavailable",
            }
        )
    no_matching_rows = not row_evidence
    evidence_gaps = ["no_matching_prediction_rows"] if no_matching_rows else []
    return {
        "diagnostic_kind": "sft_target_template_alignment",
        "summary": {
            "diagnostic_status": "public_safe_structural_evidence",
            "row_count": len(row_evidence),
            "prediction_split": prediction_split,
            "all_rows_share_system_user_prefix": bool(row_evidence)
            and all(row["same_system_user_prefix"] for row in row_evidence),
            "all_rows_share_core_system_user_prefix": bool(row_evidence)
            and all(row["same_core_system_user_prefix"] for row in row_evidence),
            "all_prediction_prompts_include_prediction_output_boundary": bool(row_evidence)
            and all(row["prediction_only_boundary_suffix_visible"] for row in row_evidence),
            "all_training_text_contains_assistant_target": all(
                row["assistant_contract_target_in_training_text"] for row in row_evidence
            )
            if row_evidence
            else False,
            "all_prediction_prompts_exclude_assistant_target": bool(row_evidence)
            and all(
                not row["assistant_contract_target_in_prediction_prompt"] for row in row_evidence
            ),
            "structural_target_span_status": "found"
            if row_evidence and all(row["assistant_target_span"]["status"] == "found" for row in row_evidence)
            else "unavailable",
            "evidence_gaps": evidence_gaps,
        },
        "rows": row_evidence,
        "label_mask_evidence": _label_mask_evidence(objective_inspection),
        "chat_template_evidence": {
            "formatting_policy": dict(FORMATTING_POLICY),
            "rendering_source": "fallback",
            "fallback_policy": FORMATTING_POLICY["fallback"],
            "tokenizer_template_status": "not_loaded",
            "tokenizer_template_inspected": False,
            "evidence_gaps": ["tokenizer_chat_template_not_loaded"],
        },
        "metadata_alignment": {
            "base_model": _base_model_alignment(training_config, prediction_metadata),
            "model_source": _metadata_field_alignment(
                training_config.get("model_source"),
                prediction_metadata.get("model_source"),
            ),
            "stack": _metadata_field_alignment(
                training_config.get("stack", "transformers+peft+trl"),
                prediction_metadata.get("stack"),
            ),
            "prediction_split": _metadata_field_alignment(
                training_config.get("prediction_split", prediction_split),
                prediction_metadata.get("prediction_split"),
            ),
            "adapter_gate": _adapter_gate(training_config, prediction_metadata),
            "adapter_release_status": _sanitize_public_summary(
                str(prediction_metadata.get("adapter_release_status", "unknown"))
            ),
            "prediction_source_kind": _sanitize_public_summary(
                str(prediction_metadata.get("prediction_source_kind", "unknown"))
            ),
            "formatting_policy": _formatting_policy_alignment(prediction_metadata),
        },
        "prior_artifacts": _prior_artifacts(
            prior_artifact_paths=prior_artifact_paths,
            prediction_metadata=prediction_metadata,
        ),
        "claims": {
            "public_sample_only": True,
            "does_not_run_private_prediction": True,
            "does_not_retrain": True,
            "does_not_repair_outputs": True,
            "checkpoint_release": False,
            "adapter_release": False,
            "does_not_prove_dev_test_generalization": True,
            "production_readiness_claim": False,
            "live_browser_benchmark_improvement_claim": False,
        },
    }


def _count_by(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _target_pressure_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "max_training_text_char_count": 0,
            "max_assistant_target_char_count": 0,
            "min_assistant_target_char_ratio": 0.0,
            "max_assistant_target_char_ratio": 0.0,
            "rows_over_2048_chars": [],
            "tokenizer_specific_token_counts_available": False,
        }
    ratios = [float(row["assistant_target_char_ratio"]) for row in rows]
    return {
        "max_training_text_char_count": max(int(row["training_text_char_count"]) for row in rows),
        "max_assistant_target_char_count": max(int(row["assistant_contract_target_char_count"]) for row in rows),
        "min_assistant_target_char_ratio": min(ratios),
        "max_assistant_target_char_ratio": max(ratios),
        "rows_over_2048_chars": [
            row["row_id"] for row in rows if int(row["training_text_char_count"]) > 2048
        ],
        "tokenizer_specific_token_counts_available": False,
        "tokenizer_specific_token_counts_gap": "tokenizer_not_loaded_for_local_public_safe_diagnostic",
    }


def _prior_repair_summary(prior_repair_diagnosis: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(prior_repair_diagnosis, dict):
        return {
            "available": False,
            "overall_interpretation": "unavailable",
            "split_exact_match": {},
            "split_json_valid_rate": {},
            "recommended_next_step": "unavailable",
        }
    summary = prior_repair_diagnosis.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    return {
        "available": True,
        "overall_interpretation": _sanitize_public_summary(
            str(summary.get("overall_interpretation", "unknown"))
        ),
        "split_exact_match": summary.get("split_exact_match", {}),
        "split_json_valid_rate": summary.get("split_json_valid_rate", {}),
        "recommended_next_step": _sanitize_public_summary(
            str(summary.get("recommended_next_step", "unknown"))
        ),
    }


def diagnose_sft_contract_learning_signal(
    *,
    load_rows_path: Path,
    manifest_path: Path,
    prior_repair_diagnosis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = load_sft_rows(load_rows_path)
    manifest = read_json(manifest_path)
    row_evidence: list[dict[str, Any]] = []
    for row in rows:
        contract = as_contract(row.target_contract)
        target = canonical_contract_json(contract)
        training_text = format_sft_training_text(row, tokenizer=None)
        span = _target_span(training_text, target)
        target_count = len(target)
        training_count = len(training_text)
        ratio = target_count / training_count if training_count else 0.0
        row_evidence.append(
            {
                "row_id": _sanitize_id(row.id),
                "split": row.split,
                "task_type": contract.task_type,
                "route": contract.route,
                "training_text_sha256": hashlib.sha256(training_text.encode("utf-8")).hexdigest(),
                "assistant_contract_target_sha256": hashlib.sha256(target.encode("utf-8")).hexdigest(),
                "training_text_char_count": training_count,
                "assistant_contract_target_char_count": target_count,
                "assistant_target_char_ratio": ratio,
                "target_top_level_field_count": len(contract.to_dict()),
                "target_slot_count": len(contract.slots),
                "assistant_target_span": span,
                "assistant_target_span_found": span["status"] == "found",
                "structural_proxy_status": "assistant_target_span_found"
                if span["status"] == "found"
                else "assistant_target_span_unavailable",
            }
        )
    label_mask = _label_mask_evidence(None)
    all_spans_found = bool(row_evidence) and all(row["assistant_target_span_found"] for row in row_evidence)
    true_label_status = str(label_mask["true_label_mask_status"])
    if all_spans_found and true_label_status == "unavailable":
        recommendation = "run_bounded_runtime_label_or_tiny_overfit_diagnostic"
    else:
        recommendation = "repair_local_prompt_or_data_signal_before_heavy_rerun"
    source_manifest = {
        "manifest_id": _sanitize_public_summary(str(manifest.get("manifest_id", "unknown"))),
        "path": manifest_path.as_posix(),
        "sft_path": load_rows_path.as_posix(),
        "counts": manifest.get("counts", {}),
    }
    return {
        "evidence_kind": "sft_contract_learning_signal",
        "diagnostic_mode": "local_public_safe_no_model_download",
        "source_manifest": source_manifest,
        "summary": {
            "row_count": len(rows),
            "split_counts": _count_by([row.split for row in rows]),
            "task_type_counts": _count_by([as_contract(row.target_contract).task_type for row in rows]),
            "route_counts": _count_by([as_contract(row.target_contract).route for row in rows]),
            "all_rows_have_assistant_target_span": all_spans_found,
            "true_runtime_label_mask_status": true_label_status,
            "evidence_gaps": list(label_mask["evidence_gaps"]),
        },
        "target_pressure": _target_pressure_summary(row_evidence),
        "rows": row_evidence,
        "label_mask_evidence": label_mask,
        "prior_repair_evidence": _prior_repair_summary(prior_repair_diagnosis),
        "execution_scope": {
            "local_public_sample_only": True,
            "model_download_allowed": False,
            "private_adapter_load_allowed": False,
            "a100_execution": False,
            "training_run": False,
            "prediction_run": False,
        },
        "rendering_evidence": {
            "rendering_source": "fallback",
            "assistant_boundary_marker": "assistant:",
            "raw_training_text_written": False,
            "raw_assistant_target_written": False,
            "formatting_policy": dict(FORMATTING_POLICY),
        },
        "recommended_next_step": recommendation,
        "claims": {
            "public_sample_only": True,
            "does_not_train": True,
            "does_not_run_prediction": True,
            "does_not_download_model": True,
            "does_not_load_private_adapter": True,
            "does_not_repair_outputs": True,
            "does_not_relax_evaluator": True,
            "model_recovery_claim": False,
            "held_out_generalization_claim": False,
            "private_corpus_generalization_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
        },
    }


_LABEL_MASK_FIELD_KEYS = (
    "true_label_mask_status",
    "prompt_tokens_masked",
    "assistant_tokens_carry_loss",
    "prompt_token_count",
    "assistant_token_count",
    "label_source_kind",
    "evidence_gaps",
)


def _artifact_manifest_id(artifact: dict[str, Any] | None) -> str | None:
    if not isinstance(artifact, dict):
        return None
    for key in ("dataset_manifest_id", "public_sample_manifest_id"):
        value = artifact.get(key)
        if isinstance(value, str) and value:
            return _sanitize_public_summary(value)
    source_manifest = artifact.get("source_manifest")
    if isinstance(source_manifest, dict):
        value = source_manifest.get("manifest_id")
        if isinstance(value, str) and value:
            return _sanitize_public_summary(value)
    return None


def _artifact_freshness(artifact: dict[str, Any] | None, current_manifest_id: str) -> str:
    if not isinstance(artifact, dict):
        return "unavailable"
    source_manifest_id = _artifact_manifest_id(artifact)
    if not source_manifest_id:
        return "manifest_id_unavailable"
    if source_manifest_id == current_manifest_id:
        return "fresh_current_manifest"
    return "stale_manifest_mismatch"


def _runtime_label_mask_fields(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {
            "true_label_mask_status": "unavailable",
            "prompt_tokens_masked": None,
            "assistant_tokens_carry_loss": None,
            "prompt_token_count": None,
            "assistant_token_count": None,
            "label_source_kind": "unavailable",
            "evidence_gaps": ["runtime_label_evidence_unavailable"],
        }
    fields = {key: artifact.get(key) for key in _LABEL_MASK_FIELD_KEYS}
    fields["true_label_mask_status"] = fields.get("true_label_mask_status") or "unavailable"
    fields["label_source_kind"] = fields.get("label_source_kind") or "unavailable"
    evidence_gaps = fields.get("evidence_gaps")
    fields["evidence_gaps"] = evidence_gaps if isinstance(evidence_gaps, list) else []
    sanitized = _sanitize_public_value(fields)
    if not isinstance(sanitized, dict):
        raise AssertionError("runtime label mask fields must remain a mapping")
    return sanitized


def _runtime_label_evidence_summary(
    artifact: dict[str, Any] | None,
    *,
    current_manifest_id: str,
) -> dict[str, Any]:
    freshness = _artifact_freshness(artifact, current_manifest_id)
    prior_fields = _runtime_label_mask_fields(artifact)
    current_fields = prior_fields if freshness == "fresh_current_manifest" else {}
    return {
        "available": isinstance(artifact, dict),
        "freshness": freshness,
        "current_manifest_proof": freshness == "fresh_current_manifest",
        "source_manifest_id": _artifact_manifest_id(artifact) or "unavailable",
        "current_manifest_id": current_manifest_id,
        "evidence_status": _sanitize_public_summary(str(artifact.get("evidence_status", "unavailable")))
        if isinstance(artifact, dict)
        else "unavailable",
        "runtime_check_status": _sanitize_public_summary(str(artifact.get("runtime_check_status", "unavailable")))
        if isinstance(artifact, dict)
        else "unavailable",
        "prior_label_mask_fields": prior_fields,
        "current_label_mask_fields": current_fields,
        "assistant_only_loss_mask_claim": bool(artifact.get("assistant_only_loss_mask_claim", False))
        if isinstance(artifact, dict)
        else False,
    }


def _tiny_overfit_evidence_summary(
    artifact: dict[str, Any] | None,
    *,
    current_manifest_id: str,
) -> dict[str, Any]:
    freshness = _artifact_freshness(artifact, current_manifest_id)
    assistant_only_objective = {}
    if isinstance(artifact, dict) and isinstance(artifact.get("assistant_only_objective"), dict):
        assistant_only_objective = _sanitize_public_value(artifact["assistant_only_objective"])
    return {
        "available": isinstance(artifact, dict),
        "freshness": freshness,
        "current_manifest_proof": freshness == "fresh_current_manifest",
        "source_manifest_id": _artifact_manifest_id(artifact) or "unavailable",
        "current_manifest_id": current_manifest_id,
        "overfit_diagnostic": bool(artifact.get("overfit_diagnostic", False)) if isinstance(artifact, dict) else False,
        "prediction_split": _sanitize_public_summary(str(artifact.get("prediction_split", "unavailable")))
        if isinstance(artifact, dict)
        else "unavailable",
        "training_rows_used": artifact.get("training_rows_used") if isinstance(artifact, dict) else None,
        "assistant_only_objective": assistant_only_objective,
        "claims": _sanitize_public_value(artifact.get("claims", {})) if isinstance(artifact, dict) else {},
    }


def _learning_signal_summary(learning_signal: dict[str, Any] | None, current_manifest_id: str) -> dict[str, Any]:
    if not isinstance(learning_signal, dict):
        return {
            "available": False,
            "freshness": "unavailable",
            "source_manifest_id": "unavailable",
            "all_rows_have_assistant_target_span": None,
            "true_runtime_label_mask_status": "unavailable",
            "recommended_next_step": "unavailable",
        }
    source_manifest_id = _artifact_manifest_id(learning_signal) or "unavailable"
    summary = learning_signal.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    return {
        "available": True,
        "freshness": "fresh_current_manifest"
        if source_manifest_id == current_manifest_id
        else "stale_manifest_mismatch",
        "source_manifest_id": source_manifest_id,
        "all_rows_have_assistant_target_span": summary.get("all_rows_have_assistant_target_span"),
        "true_runtime_label_mask_status": summary.get("true_runtime_label_mask_status", "unavailable"),
        "evidence_gaps": _sanitize_public_value(summary.get("evidence_gaps", [])),
        "target_pressure": _sanitize_public_value(learning_signal.get("target_pressure", {})),
        "recommended_next_step": _sanitize_public_summary(str(learning_signal.get("recommended_next_step", "unknown"))),
    }


def _tiny_overfit_readiness(runtime_summary: dict[str, Any], tiny_summary: dict[str, Any]) -> dict[str, Any]:
    if runtime_summary["freshness"] != "fresh_current_manifest":
        return {
            "status": "blocked_until_fresh_runtime_label_check",
            "reason": "current_manifest_runtime_label_evidence_missing_or_stale",
        }
    fields = runtime_summary.get("current_label_mask_fields", {})
    prompt_masked = fields.get("prompt_tokens_masked") is True
    assistant_loss = fields.get("assistant_tokens_carry_loss") is True
    label_status = fields.get("true_label_mask_status")
    if label_status == "inspectable" and prompt_masked and assistant_loss:
        if tiny_summary["freshness"] == "fresh_current_manifest":
            return {
                "status": "current_tiny_overfit_evidence_available",
                "reason": "fresh_current_manifest_tiny_overfit_artifact_present",
            }
        return {
            "status": "ready_for_1_to_3_row_probe",
            "reason": "fresh_assistant_only_runtime_label_evidence_available",
        }
    return {
        "status": "repair_runtime_label_mask_before_training",
        "reason": "fresh_runtime_labels_do_not_show_assistant_only_loss_mask",
    }


def _runtime_tiny_recommendation(readiness: dict[str, Any]) -> str:
    status = readiness["status"]
    if status == "blocked_until_fresh_runtime_label_check":
        return "run_fresh_current_manifest_runtime_label_check"
    if status == "ready_for_1_to_3_row_probe":
        return "run_1_to_3_row_current_manifest_tiny_overfit_probe"
    if status == "current_tiny_overfit_evidence_available":
        return "diagnose_preference_signal_or_data_scale_after_current_tiny_overfit"
    return "repair_runtime_label_mask_before_training"


def diagnose_runtime_label_tiny_overfit_readiness(
    *,
    manifest_path: Path,
    learning_signal: dict[str, Any] | None = None,
    prior_repair_diagnosis: dict[str, Any] | None = None,
    runtime_label_evidence: dict[str, Any] | None = None,
    tiny_overfit_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    current_manifest_id = _sanitize_public_summary(str(manifest.get("manifest_id", manifest_path.stem)))
    runtime_summary = _runtime_label_evidence_summary(
        runtime_label_evidence,
        current_manifest_id=current_manifest_id,
    )
    tiny_summary = _tiny_overfit_evidence_summary(
        tiny_overfit_evidence,
        current_manifest_id=current_manifest_id,
    )
    learning_summary = _learning_signal_summary(learning_signal, current_manifest_id)
    readiness = _tiny_overfit_readiness(runtime_summary, tiny_summary)
    current_label_fields = runtime_summary.get("current_label_mask_fields", {})
    current_true_label_status = current_label_fields.get("true_label_mask_status", "unavailable")
    return {
        "evidence_kind": "runtime_label_tiny_overfit_diagnostic",
        "diagnostic_mode": "local_public_safe_prior_artifact_comparison",
        "current_manifest": {
            "manifest_id": current_manifest_id,
            "path": manifest_path.as_posix(),
            "counts": _sanitize_public_value(manifest.get("counts", {})),
            "split_counts": _sanitize_public_value(manifest.get("split_counts", {})),
            "public_safe": bool(manifest.get("public_safe", False)),
        },
        "summary": {
            "current_runtime_label_status": runtime_summary["freshness"],
            "current_true_label_mask_status": current_true_label_status,
            "tiny_overfit_status": tiny_summary["freshness"],
            "tiny_overfit_readiness": readiness["status"],
            "prior_repair_train_contract_exact_match": _prior_repair_summary(prior_repair_diagnosis)
            .get("split_exact_match", {})
            .get("train"),
            "prior_repair_dev_contract_exact_match": _prior_repair_summary(prior_repair_diagnosis)
            .get("split_exact_match", {})
            .get("dev"),
            "prior_repair_test_contract_exact_match": _prior_repair_summary(prior_repair_diagnosis)
            .get("split_exact_match", {})
            .get("test"),
        },
        "learning_signal_evidence": learning_summary,
        "prior_repair_evidence": _prior_repair_summary(prior_repair_diagnosis),
        "runtime_label_evidence": runtime_summary,
        "tiny_overfit_evidence": tiny_summary,
        "tiny_overfit_readiness": readiness,
        "recommended_next_step": _runtime_tiny_recommendation(readiness),
        "artifact_policy": {
            "raw_rendered_prompts_written": False,
            "raw_assistant_targets_written": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_paths_omitted": True,
            "host_details_omitted": True,
            "ssh_details_omitted": True,
            "private_corpus_rows_omitted": True,
        },
        "execution_scope": {
            "local_public_artifact_comparison_only": True,
            "model_download_allowed": False,
            "private_adapter_load_allowed": False,
            "a100_execution": False,
            "full_sft_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "prediction_run": False,
        },
        "claims": {
            "public_sample_only": True,
            "does_not_train": True,
            "does_not_run_prediction": True,
            "does_not_download_model": True,
            "does_not_load_private_adapter": True,
            "does_not_repair_outputs": True,
            "does_not_relax_evaluator": True,
            "model_recovery_claim": False,
            "held_out_generalization_claim": False,
            "private_corpus_generalization_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
    }


def diagnose_source_alignment(
    rows: list[SFTDatasetRow],
    predictions: dict[str, Any],
    *,
    training_config: dict[str, Any],
    prediction_metadata: dict[str, Any],
    prior_artifact_paths: dict[str, str] | None = None,
    objective_inspection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    split_coverage = _split_coverage(
        rows,
        training_config=training_config,
        prediction_metadata=prediction_metadata,
    )
    return {
        "diagnostic_kind": "browser_task_contract_source_alignment",
        "summary": {
            "gold_row_count": len(rows),
            "prediction_count": len(predictions),
        },
        "target_shape": _target_shape_summary(rows),
        "prediction_symptoms": _prediction_symptom_summary(rows, predictions),
        "split_coverage": split_coverage,
        "training_coverage": _training_coverage(rows, split_coverage["configured_training_split"]),
        "current_prompt_constraints": prompt_constraint_summary(),
        "prediction_run_prompt_evidence": _prediction_run_prompt_evidence(prediction_metadata),
        "decoding_evidence": _decoding_evidence(prediction_metadata),
        "sft_target_template_alignment": _diagnose_sft_target_template_alignment(
            rows,
            predictions,
            training_config=training_config,
            prediction_metadata=prediction_metadata,
            prior_artifact_paths=prior_artifact_paths,
            objective_inspection=objective_inspection,
        ),
        "claims": {
            "invalid_predictions_remain_invalid": True,
            "does_not_repair_normalize_coerce_or_replace_predictions": True,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "full_private_corpus_claim": False,
            "live_browser_benchmark_claim": False,
        },
    }


def _diagnose_contract_object(row_id: str, prediction: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    missing = sorted(_REQUIRED_CONTRACT_FIELDS - set(prediction))
    for field_name in missing:
        issues.append(
            _issue(
                row_id=row_id,
                field_path=field_name,
                issue_category="missing_required_field",
                observed_value=None,
                expected_constraint="Browser Task Contract requires this top-level field",
            )
        )

    if "task_type" in prediction and prediction["task_type"] not in TASK_TYPES:
        issues.append(
            _issue(
                row_id=row_id,
                field_path="task_type",
                issue_category="invalid_enum",
                observed_value=prediction["task_type"],
                expected_constraint=f"must be one of {sorted(TASK_TYPES)}",
            )
        )
    if "route" in prediction and prediction["route"] not in ROUTES:
        issues.append(
            _issue(
                row_id=row_id,
                field_path="route",
                issue_category="invalid_enum",
                observed_value=prediction["route"],
                expected_constraint=f"must be one of {sorted(ROUTES)}",
            )
        )
    if "safety" in prediction:
        safety = prediction["safety"]
        if not isinstance(safety, dict):
            issues.append(
                _issue(
                    row_id=row_id,
                    field_path="safety",
                    issue_category="invalid_type",
                    observed_value=safety,
                    expected_constraint="must be an object with boolean allow and non-empty string reason",
                )
            )
        else:
            if "allow" not in safety:
                issues.append(
                    _issue(
                        row_id=row_id,
                        field_path="safety.allow",
                        issue_category="missing_required_field",
                        observed_value=None,
                        expected_constraint="must be a boolean",
                    )
                )
            elif not isinstance(safety["allow"], bool):
                issues.append(
                    _issue(
                        row_id=row_id,
                        field_path="safety.allow",
                        issue_category="invalid_type",
                        observed_value=safety["allow"],
                        expected_constraint="must be a boolean",
                    )
                )
            if "reason" not in safety:
                issues.append(
                    _issue(
                        row_id=row_id,
                        field_path="safety.reason",
                        issue_category="missing_required_field",
                        observed_value=None,
                        expected_constraint="must be a non-empty string",
                    )
                )
            elif not isinstance(safety["reason"], str):
                issues.append(
                    _issue(
                        row_id=row_id,
                        field_path="safety.reason",
                        issue_category="invalid_type",
                        observed_value=safety["reason"],
                        expected_constraint="must be a non-empty string",
                    )
                )
            elif not safety["reason"].strip():
                issues.append(
                    _issue(
                        row_id=row_id,
                        field_path="safety.reason",
                        issue_category="empty_required_string",
                        observed_value=safety["reason"],
                        expected_constraint="must be a non-empty string",
                )
            )
    if "confirmation_required" in prediction and not isinstance(prediction["confirmation_required"], bool):
        issues.append(
            _issue(
                row_id=row_id,
                field_path="confirmation_required",
                issue_category="invalid_type",
                observed_value=prediction["confirmation_required"],
                expected_constraint="must be a boolean",
            )
        )
    if "slots" in prediction and not isinstance(prediction["slots"], dict):
        issues.append(
            _issue(
                row_id=row_id,
                field_path="slots",
                issue_category="invalid_type",
                observed_value=prediction["slots"],
                expected_constraint="must be an object",
            )
        )
    if "normalized_command" in prediction:
        normalized_command = prediction["normalized_command"]
        if not isinstance(normalized_command, str):
            issues.append(
                _issue(
                    row_id=row_id,
                    field_path="normalized_command",
                    issue_category="invalid_type",
                    observed_value=normalized_command,
                    expected_constraint="must be a non-empty string",
                )
            )
        elif not normalized_command.strip():
            issues.append(
                _issue(
                    row_id=row_id,
                    field_path="normalized_command",
                    issue_category="empty_required_string",
                    observed_value=normalized_command,
                    expected_constraint="must be a non-empty string",
                )
            )
    if "language" in prediction and prediction["language"] != "zh-CN":
        issues.append(
            _issue(
                row_id=row_id,
                field_path="language",
                issue_category="invalid_literal",
                observed_value=prediction["language"],
                expected_constraint="must be zh-CN",
            )
        )
    if "contract_version" in prediction and prediction["contract_version"] != "v1":
        issues.append(
            _issue(
                row_id=row_id,
                field_path="contract_version",
                issue_category="invalid_literal",
                observed_value=prediction["contract_version"],
                expected_constraint="must be v1",
            )
        )
    return issues


def diagnose_schema_mismatches(rows: list[SFTDatasetRow], predictions: dict[str, Any]) -> dict[str, Any]:
    diagnostics_rows: list[dict[str, Any]] = []
    issue_counts: dict[str, int] = {}
    invalid_prediction_count = 0

    for row in rows:
        row_id = _sanitize_id(row.id)
        raw_prediction = predictions.get(row.id)
        parsed_prediction = raw_prediction
        issues: list[dict[str, str]] = []
        if isinstance(raw_prediction, str):
            try:
                parsed_prediction = json.loads(raw_prediction)
            except json.JSONDecodeError:
                issues.append(
                    _issue(
                        row_id=row.id,
                        field_path="$",
                        issue_category="invalid_json",
                        observed_value=raw_prediction,
                        expected_constraint="prediction must be a JSON object matching Browser Task Contract",
                    )
                )
        if not issues:
            if not isinstance(parsed_prediction, dict):
                issues.append(
                    _issue(
                        row_id=row.id,
                        field_path="$",
                        issue_category="invalid_type",
                        observed_value=parsed_prediction,
                        expected_constraint="prediction must be an object matching Browser Task Contract",
                    )
                )
            elif _prediction_to_contract(parsed_prediction) is None:
                issues.extend(_diagnose_contract_object(row.id, parsed_prediction))
                if not issues:
                    issues.append(
                        _issue(
                            row_id=row.id,
                            field_path="$",
                            issue_category="schema_validation_error",
                            observed_value=parsed_prediction,
                            expected_constraint="must satisfy Browser Task Contract validator",
                        )
                    )
        if issues:
            invalid_prediction_count += 1
            for issue in issues:
                issue_counts[issue["issue_category"]] = issue_counts.get(issue["issue_category"], 0) + 1
            diagnostics_rows.append({"row_id": row_id, "issues": issues})

    return {
        "diagnostic_kind": "browser_task_contract_schema_mismatch",
        "summary": {
            "gold_row_count": len(rows),
            "prediction_count": len(predictions),
            "invalid_prediction_count": invalid_prediction_count,
            "issue_counts": dict(sorted(issue_counts.items())),
        },
        "rows": diagnostics_rows,
        "claims": {
            "invalid_predictions_remain_invalid": True,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "full_private_corpus_claim": False,
            "live_browser_benchmark_claim": False,
        },
    }


_JSON_STRING_FIELD_RE = re.compile(r'"(?P<field>task_type|route)"\s*:\s*"(?P<value>[^"]+)"')


def _attempt_text(attempt: dict[str, Any]) -> str:
    decoded_text = attempt.get("decoded_text")
    if isinstance(decoded_text, str):
        return _sanitize_public_summary(decoded_text)
    prefix = str(attempt.get("decoded_prefix", ""))
    suffix = str(attempt.get("decoded_suffix", ""))
    if not prefix:
        return _sanitize_public_summary(suffix)
    if not suffix or suffix == prefix:
        return _sanitize_public_summary(prefix)
    return _sanitize_public_summary(f"{prefix}\n{suffix}")


def _attempt_field_values(text: str, field: str) -> list[str]:
    return [match.group("value") for match in _JSON_STRING_FIELD_RE.finditer(text) if match.group("field") == field]


def _is_legacy_task_type_alias(value: str) -> bool:
    if value in TASK_TYPES:
        return False
    return (
        value in ROUTES
        or value in {"search_web", "open_url", "query_weather_request"}
        or value.startswith(("query_", "search_", "open_"))
        or value.endswith(("_request", "_action"))
    )


def _has_prose_or_markdown_wrapper(attempt: dict[str, Any], text: str) -> bool:
    parse_status = str(attempt.get("parse_status", "missing"))
    stripped = text.strip()
    if parse_status.startswith("json_fragment"):
        return True
    return bool(stripped) and (not stripped.startswith("{") or not stripped.endswith("}") or "```" in stripped)


def _increment_count(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def diagnose_constrained_contract_decoding(
    predictions: dict[str, Any],
    raw_decoded_summary_rows: list[dict[str, Any]],
    evidence_context: str = "local_decoder_output_shape_hardening",
) -> dict[str, Any]:
    valid_contexts = {"local_decoder_output_shape_hardening", "a100_prediction_rerun"}
    if evidence_context not in valid_contexts:
        raise ValueError(f"Unsupported constrained decoding evidence_context: {evidence_context}")

    parse_status_counts: dict[str, dict[str, int]] = {"raw_attempt": {}, "retry_attempt": {}}
    legacy_task_type_alias_examples: list[dict[str, str]] = []
    path_like_route_examples: list[dict[str, str]] = []
    prose_markdown_wrapper_examples: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    raw_schema_valid_count = 0
    retry_schema_valid_count = 0
    validated_schema_valid_count = 0

    for summary_row in raw_decoded_summary_rows:
        row_id = _sanitize_id(str(summary_row.get("id", "")))
        schema_guard = summary_row.get("schema_guard")
        guard = schema_guard if isinstance(schema_guard, dict) else {}
        if guard.get("raw_attempt_schema_valid") is True:
            raw_schema_valid_count += 1
        if guard.get("retry_attempt_schema_valid") is True:
            retry_schema_valid_count += 1
        if guard.get("validated_output_schema_valid") is True:
            validated_schema_valid_count += 1

        row_symptoms: list[dict[str, str]] = []
        for source_name in ("raw_attempt", "retry_attempt"):
            attempt = summary_row.get(source_name)
            if not isinstance(attempt, dict):
                continue
            parse_status = str(attempt.get("parse_status", "missing"))
            _increment_count(parse_status_counts[source_name], parse_status)
            text = _attempt_text(attempt)
            for value in _attempt_field_values(text, "task_type"):
                if _is_legacy_task_type_alias(value):
                    example = {
                        "row_id": row_id,
                        "source": source_name,
                        "task_type": _observed_value_summary(value),
                    }
                    legacy_task_type_alias_examples.append(example)
                    row_symptoms.append(
                        {
                            "source": source_name,
                            "symptom": "legacy_task_type_alias",
                            "observed_value_summary": example["task_type"],
                        }
                    )
                    break
            for value in _attempt_field_values(text, "route"):
                if _is_path_like_route(value):
                    example = {
                        "row_id": row_id,
                        "source": source_name,
                        "route": _observed_value_summary(value),
                    }
                    path_like_route_examples.append(example)
                    row_symptoms.append(
                        {
                            "source": source_name,
                            "symptom": "path_like_route",
                            "observed_value_summary": example["route"],
                        }
                    )
                    break
            if _has_prose_or_markdown_wrapper(attempt, text):
                example = {"row_id": row_id, "source": source_name, "parse_status": parse_status}
                prose_markdown_wrapper_examples.append(example)
                row_symptoms.append(
                    {
                        "source": source_name,
                        "symptom": "prose_markdown_wrapper",
                        "observed_value_summary": parse_status,
                    }
                )
        rows.append(
            {
                "row_id": row_id,
                "raw_parse_status": summary_row.get("raw_attempt", {}).get("parse_status")
                if isinstance(summary_row.get("raw_attempt"), dict)
                else None,
                "retry_parse_status": summary_row.get("retry_attempt", {}).get("parse_status")
                if isinstance(summary_row.get("retry_attempt"), dict)
                else None,
                "schema_guard": {
                    "raw_attempt_schema_valid": bool(guard.get("raw_attempt_schema_valid")),
                    "retry_attempt_schema_valid": guard.get("retry_attempt_schema_valid"),
                    "validated_output_schema_valid": bool(guard.get("validated_output_schema_valid")),
                    "validated_output_source": str(guard.get("validated_output_source", "unknown")),
                },
                "symptoms": row_symptoms,
            }
        )

    prediction_schema_valid_count = sum(1 for prediction in predictions.values() if _prediction_to_contract(prediction))
    return {
        "diagnostic_kind": "constrained_contract_decoding_diagnosis",
        "summary": {
            "prediction_count": len(predictions),
            "decoded_summary_row_count": len(raw_decoded_summary_rows),
            "prediction_schema_valid_count": prediction_schema_valid_count,
            "invalid_prediction_count": len(predictions) - prediction_schema_valid_count,
            "raw_attempt_schema_valid_count": raw_schema_valid_count,
            "retry_attempt_schema_valid_count": retry_schema_valid_count,
            "validated_output_schema_valid_count": validated_schema_valid_count,
            "parse_status_counts": {
                source: dict(sorted(counts.items())) for source, counts in parse_status_counts.items()
            },
            "legacy_task_type_alias_count": len(legacy_task_type_alias_examples),
            "path_like_route_count": len(path_like_route_examples),
            "prose_markdown_wrapper_count": len(prose_markdown_wrapper_examples),
            "invalid_predictions_remain_invalid": True,
        },
        "examples": {
            "legacy_task_type_alias": _limited_examples(legacy_task_type_alias_examples),
            "path_like_route": _limited_examples(path_like_route_examples),
            "prose_markdown_wrapper": _limited_examples(prose_markdown_wrapper_examples),
        },
        "rows": rows,
        "claims": {
            "evidence_context": evidence_context,
            "invalid_predictions_remain_invalid": True,
            "does_not_coerce_or_replace_invalid_predictions": True,
            "local_decoder_output_shape_hardening_only": (
                evidence_context == "local_decoder_output_shape_hardening"
            ),
            "a100_prediction_rerun_evidence": evidence_context == "a100_prediction_rerun",
            "checkpoint_release": False,
            "adapter_release": False,
            "held_out_generalization_claim": False,
            "production_readiness_claim": False,
            "full_private_corpus_claim": False,
            "live_browser_benchmark_claim": False,
            "a100_model_recovery_claim": False,
        },
    }


def rule_baseline_predictions(rows: list[SFTDatasetRow]) -> dict[str, dict[str, Any]]:
    predictions: dict[str, dict[str, Any]] = {}
    for row in rows:
        text = row.input_text
        if any(marker in text for marker in ("搜", "搜索", "查")):
            query = text.replace("帮我", "").replace("搜索", "").replace("搜", "").replace("查一下", "").strip()
            contract = BrowserTaskContract(
                task_type="search",
                route="search_web",
                safety={"allow": True, "reason": "public_readonly"},
                confirmation_required=False,
                slots={"query": query or text},
                normalized_command=f"搜索{query or text}",
            )
        elif "打开" in text:
            contract = BrowserTaskContract(
                task_type="navigate",
                route="open_url",
                safety={"allow": True, "reason": "public_readonly"},
                confirmation_required=False,
                slots={"url": "about:blank"},
                normalized_command=text,
            )
        else:
            contract = BrowserTaskContract(
                task_type="clarify",
                route="clarify",
                safety={"allow": False, "reason": "underspecified_request"},
                confirmation_required=True,
                slots={},
                normalized_command=text,
            )
        predictions[row.id] = contract.to_dict()
    return predictions


def prompt_fixture_predictions(rows: list[SFTDatasetRow], fixture_path: Path) -> dict[str, Any]:
    expected_ids = {row.id for row in rows}
    predictions = load_predictions(fixture_path)
    missing = sorted(expected_ids - set(predictions))
    if missing:
        raise ValidationError(f"prompt_fixture_missing_predictions: {', '.join(missing)}")
    return {row_id: predictions[row_id] for row_id in sorted(expected_ids)}


def _run_validation_command(command: list[str], row: SFTDatasetRow, contract: BrowserTaskContract) -> bool:
    payload = json.dumps(
        {"id": row.id, "input_text": row.input_text, "contract": contract.to_dict()},
        ensure_ascii=False,
    )
    completed = subprocess.run(
        command,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return False
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False
    return bool(result.get("ok"))


def run_execution_smoke(
    rows: list[SFTDatasetRow],
    predictions: dict[str, Any],
    enabled: bool,
    target_path: Path | None = None,
) -> ExecutionSmokeResult:
    if not enabled:
        return ExecutionSmokeResult(enabled=False, passed=0, failed=0, target=None, notes="disabled")
    if target_path is None:
        return ExecutionSmokeResult(enabled=True, passed=0, failed=len(rows), target=None, notes="target_path_missing")
    target = read_json(target_path)
    command = target.get("command")
    if isinstance(command, list) and all(isinstance(item, str) for item in command):
        passed = 0
        failed = 0
        for row in rows:
            prediction = _prediction_to_contract(predictions.get(row.id))
            if prediction is not None and _run_validation_command(command, row, prediction):
                passed += 1
            else:
                failed += 1
        return ExecutionSmokeResult(
            enabled=True,
            passed=passed,
            failed=failed,
            target=target_path.as_posix(),
            notes="controlled_validation_command",
        )
    if target.get("accepts_contracts") is not True:
        return ExecutionSmokeResult(
            enabled=True,
            passed=0,
            failed=len(rows),
            target=target_path.as_posix(),
            notes="target_does_not_accept_contracts",
        )
    passed = sum(1 for row in rows if _prediction_to_contract(predictions.get(row.id)) is not None)
    return ExecutionSmokeResult(
        enabled=True,
        passed=passed,
        failed=len(rows) - passed,
        target=target_path.as_posix(),
        notes="controlled_contract_consumer_smoke",
    )


def load_sft_rows(path: Path) -> list[SFTDatasetRow]:
    return [SFTDatasetRow(**record) for record in read_jsonl(path)]


def load_predictions(path: Path) -> dict[str, Any]:
    predictions: dict[str, Any] = {}
    for record in read_jsonl(path):
        row_id = str(record.get("id", ""))
        if "prediction" in record:
            predictions[row_id] = record["prediction"]
        elif "contract" in record:
            predictions[row_id] = record["contract"]
        else:
            predictions[row_id] = {key: value for key, value in record.items() if key != "id"}
    return predictions


def write_predictions(path: Path, predictions: dict[str, dict[str, Any]]) -> None:
    write_jsonl(path, [{"id": row_id, "prediction": prediction} for row_id, prediction in predictions.items()])
