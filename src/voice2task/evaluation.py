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


def _source_family_id(row: SFTDatasetRow) -> str:
    source_id = row.provenance.get("source_id") if isinstance(row.provenance, dict) else None
    return _sanitize_id(str(source_id or row.id))


def _contract_family_key(contract: BrowserTaskContract) -> str:
    slot_keys = ",".join(sorted(str(key) for key in contract.slots)) or "none"
    confirmation = str(bool(contract.confirmation_required)).lower()
    reason = _sanitize_public_summary(str(contract.safety.get("reason", "unknown")))
    return f"{contract.task_type}|{contract.route}|{reason}|confirm:{confirmation}|slots:{slot_keys}"


def _family_row_summary(rows: list[SFTDatasetRow]) -> dict[str, dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for row in rows:
        contract = as_contract(row.target_contract)
        source_family = _source_family_id(row)
        entry = families.setdefault(
            source_family,
            {
                "source_family_id": source_family,
                "contract_family_key": _contract_family_key(contract),
                "task_type": contract.task_type,
                "route": contract.route,
                "safety_reason": _sanitize_public_summary(str(contract.safety.get("reason", "unknown"))),
                "confirmation_required": contract.confirmation_required,
                "slot_keys": sorted(str(key) for key in contract.slots),
                "split_counts": {},
                "row_count": 0,
                "row_ids": [],
            },
        )
        entry["row_count"] += 1
        entry["split_counts"][row.split] = entry["split_counts"].get(row.split, 0) + 1
        entry["row_ids"].append(_sanitize_id(row.id))
    return dict(sorted(families.items()))


def _coverage_by_split(rows: list[SFTDatasetRow]) -> dict[str, dict[str, Any]]:
    coverage: dict[str, dict[str, Any]] = {}
    for split in sorted({row.split for row in rows}):
        split_rows = [row for row in rows if row.split == split]
        contracts = [as_contract(row.target_contract) for row in split_rows]
        coverage[split] = {
            "row_count": len(split_rows),
            "source_family_counts": _count_by([_source_family_id(row) for row in split_rows]),
            "contract_family_counts": _count_by([_contract_family_key(contract) for contract in contracts]),
            "task_type_counts": _count_by([contract.task_type for contract in contracts]),
            "route_counts": _count_by([contract.route for contract in contracts]),
            "safety_reason_counts": _count_by(
                [_sanitize_public_summary(str(contract.safety.get("reason", "unknown"))) for contract in contracts]
            ),
            "confirmation_counts": _count_by(
                [f"confirm:{str(bool(contract.confirmation_required)).lower()}" for contract in contracts]
            ),
            "slot_key_counts": _count_by(
                [",".join(sorted(str(key) for key in contract.slots)) or "none" for contract in contracts]
            ),
        }
    return coverage


_DPO_CATEGORY_BY_CONTRACT_FAMILY = {
    "blocked|deny|unsafe_payment|confirm:true|slots:reason": "blocked_payment_action_drift",
    "clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity": "clarify_action_drift",
    "form_fill|fill_form|requires_confirmation|confirm:true|slots:field": "form_confirmation_drift",
    "navigate|open_url|public_readonly|confirm:false|slots:url": "navigate_canonical_url_drift",
}


def _field_mismatch_counts_for_family(alignment: dict[str, Any], row_ids: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    rows = alignment.get("rows") if isinstance(alignment, dict) else []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or str(row.get("row_id", "")) not in row_ids:
            continue
        mismatches = row.get("mismatches")
        for mismatch in mismatches if isinstance(mismatches, list) else []:
            if not isinstance(mismatch, dict):
                continue
            field_path = _sanitize_public_summary(str(mismatch.get("field_path", "unknown")))
            counts[field_path] = counts.get(field_path, 0) + 1
    return dict(sorted(counts.items()))


def _targeted_residual_field_value(value: Any) -> Any:
    if value is _MISSING:
        return "missing"
    return _sanitize_public_value(value)


def _targeted_slot_value_drift_bucket(gold_value: Any, prediction_value: Any) -> str:
    if isinstance(gold_value, dict) and isinstance(prediction_value, dict):
        gold_keys = set(gold_value)
        prediction_keys = set(prediction_value)
        if gold_keys == prediction_keys == {"field"}:
            gold_field = str(gold_value.get("field", "")).strip().lower()
            prediction_field = str(prediction_value.get("field", "")).strip().lower()
            if gold_field != prediction_field and {gold_field, prediction_field} == {"邮箱", "email"}:
                return "slot_value_language_variant"
        if gold_keys == prediction_keys:
            return "slot_value_canonical_phrase_drift"
    return "other_value_drift"


def _targeted_value_drift_bucket(field_path: str, gold_value: Any, prediction_value: Any) -> str:
    if field_path == "normalized_command":
        return "normalized_command_paraphrase_drift"
    if field_path == "slots":
        return _targeted_slot_value_drift_bucket(gold_value, prediction_value)
    return "other_value_drift"


def _alignment_rows_by_id(alignment: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows = alignment.get("rows") if isinstance(alignment, dict) else []
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        row_id = _sanitize_id(str(row.get("row_id", "")))
        mismatches = row.get("mismatches")
        by_id[row_id] = [mismatch for mismatch in mismatches if isinstance(mismatch, dict)] if isinstance(
            mismatches, list
        ) else []
    return by_id


def diagnose_targeted_slot_value_residuals(
    *,
    targeted_manifest: dict[str, Any],
    rows_by_split: dict[str, list[SFTDatasetRow]],
    predictions_by_split: dict[str, dict[str, Any]],
    alignment_by_split: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    residuals: list[dict[str, Any]] = []
    split_results = targeted_manifest.get("split_results", {})

    for split in ("dev", "test"):
        rows = rows_by_split.get(split, [])
        row_by_id = {_sanitize_id(row.id): row for row in rows}
        predictions = predictions_by_split.get(split, {})
        alignment_rows = _alignment_rows_by_id(alignment_by_split.get(split, {}))
        for row_id, mismatches in sorted(alignment_rows.items()):
            row = row_by_id.get(row_id)
            if row is None:
                continue
            gold = as_contract(row.target_contract).to_dict()
            raw_prediction = predictions.get(row.id)
            parsed_prediction = raw_prediction
            if isinstance(raw_prediction, str):
                try:
                    parsed_prediction = json.loads(raw_prediction)
                except json.JSONDecodeError:
                    parsed_prediction = {}
            prediction_object = parsed_prediction if isinstance(parsed_prediction, dict) else {}
            for mismatch in mismatches:
                field_path = _sanitize_public_summary(str(mismatch.get("field_path", "unknown")))
                gold_value = _field_value(gold, field_path)
                prediction_value = _field_value(prediction_object, field_path)
                drift_bucket = _targeted_value_drift_bucket(field_path, gold_value, prediction_value)
                residuals.append(
                    {
                        "split": split,
                        "row_id": row_id,
                        "source_family_id": _source_family_id(row),
                        "field_path": field_path,
                        "drift_bucket": drift_bucket,
                        "mismatch_category": _sanitize_public_summary(
                            str(mismatch.get("mismatch_category", "unknown"))
                        ),
                        "gold_value": _targeted_residual_field_value(gold_value),
                        "predicted_value": _targeted_residual_field_value(prediction_value),
                        "gold_value_summary": _alignment_value_summary(gold_value, missing=gold_value is _MISSING),
                        "predicted_value_summary": _alignment_value_summary(
                            prediction_value,
                            missing=prediction_value is _MISSING,
                        ),
                    }
                )

    by_split = _count_by([entry["split"] for entry in residuals])
    by_field = _count_by([entry["field_path"] for entry in residuals])
    by_family = _count_by([entry["source_family_id"] for entry in residuals])
    by_bucket = _count_by([entry["drift_bucket"] for entry in residuals])
    strict_exact = {
        split: float(split_results.get(split, {}).get("contract_exact_match", 0.0)) for split in ("dev", "test")
    }
    structure_metrics_ok = all(
        float(split_results.get(split, {}).get(metric, 0.0)) == 1.0
        for split in ("dev", "test")
        for metric in (
            "json_valid_rate",
            "task_type_accuracy",
            "route_accuracy",
            "confirmation_accuracy",
            "safety_precision",
            "safety_recall",
        )
    ) and all(
        int(split_results.get(split, {}).get("schema_invalid_prediction_count", 0)) == 0
        for split in ("dev", "test")
    )

    return {
        "evidence_kind": "targeted_slot_value_residual_diagnosis",
        "diagnostic_mode": "local_public_safe_no_training_no_generation_no_metric_change",
        "source_targeted_probe": {
            "evidence_kind": _sanitize_public_summary(str(targeted_manifest.get("evidence_kind", "unknown"))),
            "dataset_manifest_id": _sanitize_public_summary(str(targeted_manifest.get("dataset_manifest_id", ""))),
            "base_model": _sanitize_public_summary(str(targeted_manifest.get("base_model", ""))),
            "overall_interpretation": _sanitize_public_summary(
                str(targeted_manifest.get("overall_interpretation", "unknown"))
            ),
            "training_source_ids": _sanitize_public_value(targeted_manifest.get("training_source_ids", [])),
        },
        "summary": {
            "strict_contract_exact_match": strict_exact,
            "json_schema_task_route_safety_confirmation_ok": structure_metrics_ok,
            "residual_row_count": len(residuals),
            "residual_field_counts": by_field,
            "residual_drift_bucket_counts": by_bucket,
            "broad_scaling_recommended_now": False,
            "dpo_recommended_now": False,
            "recommended_next_step": "design_slot_value_generalization_cases_before_broad_scaling_or_dpo",
        },
        "aggregates": {
            "by_split": by_split,
            "by_field_path": by_field,
            "by_source_family": by_family,
            "by_drift_bucket": by_bucket,
        },
        "residuals": residuals,
        "execution_scope": {
            "local_public_sample_only": True,
            "new_data_generated": False,
            "training_run": False,
            "dpo_run": False,
            "a100_execution": False,
            "prediction_run": False,
            "evaluator_metric_change": False,
            "prediction_repair_or_replacement": False,
        },
        "claims": {
            "diagnosis_only": True,
            "model_recovery_claim": False,
            "held_out_generalization_recovered": False,
            "private_corpus_generalization_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
            "prediction_repair_or_replacement": False,
            "semantic_equivalence_primary_metric": False,
            "evaluator_relaxation": False,
            "soft_slot_f1_primary_metric": False,
        },
    }


def _merged_split_metric(
    split_results: dict[str, Any],
    split: str,
    metric: str,
    default: float = 0.0,
) -> float:
    split_payload = split_results.get(split, {})
    if not isinstance(split_payload, dict):
        return default
    value = split_payload.get(metric, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _merged_residual_category(
    *,
    split_results: dict[str, Any],
    split: str,
    field_path: str,
) -> str:
    if field_path == "slots":
        strict_slot_f1 = _merged_split_metric(split_results, split, "slot_f1")
        soft_slot_f1 = _merged_split_metric(split_results, split, "slot_f1_soft")
        if strict_slot_f1 < 1.0 and soft_slot_f1 >= 1.0:
            return "slot_value_strict_mismatch_soft_match"
        return "slot_strict_mismatch"
    if field_path == "normalized_command":
        return "normalized_command_strict_string_mismatch"
    if field_path.startswith("safety."):
        return "safety_field_strict_mismatch"
    return f"{field_path.replace('.', '_')}_strict_mismatch"


def _expected_residual_row_count(split_results: dict[str, Any], split: str) -> int:
    split_payload = split_results.get(split, {})
    if not isinstance(split_payload, dict) or "residual_row_count" not in split_payload:
        return 0
    try:
        return int(split_payload["residual_row_count"])
    except (TypeError, ValueError):
        return 0


def diagnose_merged_slot_value_residuals(
    *,
    merged_manifest: dict[str, Any],
    rows_by_split: dict[str, list[SFTDatasetRow]],
    predictions_by_split: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    split_results = merged_manifest.get("split_results", {})
    split_results = split_results if isinstance(split_results, dict) else {}
    residuals: list[dict[str, Any]] = []
    residual_row_keys: set[tuple[str, str]] = set()

    for split in ("dev", "test"):
        predictions = predictions_by_split.get(split, {})
        for row in rows_by_split.get(split, []):
            gold_contract = as_contract(row.target_contract)
            gold = gold_contract.to_dict()
            raw_prediction = predictions.get(row.id)
            predicted_contract = _prediction_to_contract(raw_prediction)
            if predicted_contract is None:
                residual_row_keys.add((split, _sanitize_id(row.id)))
                residuals.append(
                    {
                        "split": split,
                        "row_id": _sanitize_id(row.id),
                        "source_family_id": _source_family_id(row),
                        "task_family": _contract_family_key(gold_contract),
                        "field_path": "schema",
                        "category": "schema_invalid_prediction",
                        "mismatch_category": "schema_invalid_prediction",
                        "gold_value_summary": "valid Browser Task Contract",
                        "predicted_value_summary": _observed_value_summary(raw_prediction),
                    }
                )
                continue
            prediction = predicted_contract.to_dict()
            if prediction == gold:
                continue
            residual_row_keys.add((split, _sanitize_id(row.id)))
            for field_path in _ALIGNMENT_FIELD_PATHS:
                gold_value = _field_value(gold, field_path)
                prediction_value = _field_value(prediction, field_path)
                if gold_value == prediction_value:
                    continue
                mismatch = _alignment_mismatch(
                    row_id=row.id,
                    field_path=field_path,
                    gold_value=gold_value,
                    prediction_value=prediction_value,
                )
                residuals.append(
                    {
                        "split": split,
                        "row_id": _sanitize_id(row.id),
                        "source_family_id": _source_family_id(row),
                        "task_family": _contract_family_key(gold_contract),
                        "field_path": field_path,
                        "category": _merged_residual_category(
                            split_results=split_results,
                            split=split,
                            field_path=field_path,
                        ),
                        "mismatch_category": mismatch["mismatch_category"],
                        "gold_value": _targeted_residual_field_value(gold_value),
                        "predicted_value": _targeted_residual_field_value(prediction_value),
                        "gold_value_summary": mismatch["gold_value_summary"],
                        "predicted_value_summary": mismatch["prediction_value_summary"],
                    }
                )

    strict_exact = {
        split: _merged_split_metric(split_results, split, "contract_exact_match") for split in ("dev", "test")
    }
    strict_slot_f1 = {split: _merged_split_metric(split_results, split, "slot_f1") for split in ("dev", "test")}
    soft_slot_f1 = {split: _merged_split_metric(split_results, split, "slot_f1_soft") for split in ("dev", "test")}
    residual_fields = [entry["field_path"] for entry in residuals]
    residual_categories = [entry["category"] for entry in residuals]
    residual_rows_by_split = _count_by([split for split, _row_id in sorted(residual_row_keys)])
    source_count_by_split: dict[str, dict[str, Any]] = {}
    for split in ("dev", "test"):
        expected = _expected_residual_row_count(split_results, split)
        computed = int(residual_rows_by_split.get(split, 0))
        source_count_by_split[split] = {
            "expected": expected,
            "computed": computed,
            "ok": computed == expected,
        }
    source_count_consistency = {
        "ok": all(entry["ok"] for entry in source_count_by_split.values()),
        "by_split": source_count_by_split,
    }
    if not source_count_consistency["ok"]:
        raise ValueError(f"residual count mismatch: {source_count_by_split}")

    return {
        "evidence_kind": "merged_slot_value_residual_diagnosis",
        "diagnostic_mode": "public_safe_no_training_no_prediction_no_metric_change",
        "source_merged_eval": {
            "evidence_kind": _sanitize_public_summary(str(merged_manifest.get("evidence_kind", "unknown"))),
            "dataset_manifest_id": _sanitize_public_summary(str(merged_manifest.get("dataset_manifest_id", ""))),
            "base_model": _sanitize_public_summary(str(merged_manifest.get("base_model", ""))),
        },
        "summary": {
            "strict_contract_exact_match": strict_exact,
            "strict_slot_f1": strict_slot_f1,
            "soft_slot_f1": soft_slot_f1,
            "soft_slot_f1_primary_metric": False,
            "residual_row_count": len(residual_row_keys),
            "source_count_consistency": source_count_consistency,
            "residual_field_counts": _count_by(residual_fields),
            "residual_category_counts": _count_by(residual_categories),
            "recommended_next_step": "review_residual_buckets_before_data_or_training_change",
        },
        "aggregates": {
            "by_split_residual_rows": residual_rows_by_split,
            "by_split_residual_fields": _count_by([entry["split"] for entry in residuals]),
            "by_field_path": _count_by(residual_fields),
            "by_category": _count_by(residual_categories),
            "by_source_family": _count_by([entry["source_family_id"] for entry in residuals]),
            "by_task_family": _count_by([entry["task_family"] for entry in residuals]),
        },
        "residuals": residuals,
        "execution_scope": {
            "local_public_sample_only": True,
            "private_predictions_read_as_input": True,
            "new_data_generated": False,
            "training_run": False,
            "dpo_run": False,
            "prediction_run": False,
            "evaluator_metric_change": False,
            "prediction_repair_or_replacement": False,
            "slot_normalization": False,
        },
        "claims": {
            "diagnosis_only": True,
            "model_recovery_claim": False,
            "held_out_recovery_claim": False,
            "held_out_generalization_recovered": False,
            "private_corpus_generalization_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
            "prediction_repair_or_replacement": False,
            "semantic_equivalence_primary_metric": False,
            "evaluator_relaxation": False,
            "soft_slot_f1_primary_metric": False,
        },
    }


def diagnose_formal_heldout_residual_families(
    *,
    formal_manifest: dict[str, Any],
    rows_by_split: dict[str, list[SFTDatasetRow]],
    predictions_by_split: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    diagnosis = diagnose_merged_slot_value_residuals(
        merged_manifest=formal_manifest,
        rows_by_split=rows_by_split,
        predictions_by_split=predictions_by_split,
    )
    source = diagnosis.pop("source_merged_eval", {})
    diagnosis["evidence_kind"] = "formal_heldout_residual_family_diagnosis"
    diagnosis["diagnostic_kind"] = "formal_public_heldout_residual_family_diagnosis"
    diagnosis["source_formal_heldout_evidence"] = {
        "evidence_kind": _sanitize_public_summary(str(formal_manifest.get("evidence_kind", "unknown"))),
        "dataset_manifest_id": _sanitize_public_summary(str(formal_manifest.get("dataset_manifest_id", ""))),
        "base_model": _sanitize_public_summary(str(formal_manifest.get("base_model", source.get("base_model", "")))),
        "overall_interpretation": _sanitize_public_summary(
            str(formal_manifest.get("overall_interpretation", "unknown"))
        ),
        "prediction_splits": _sanitize_public_value(formal_manifest.get("prediction_splits", ["dev", "test"])),
    }
    diagnosis["summary"]["recommended_next_step"] = (
        "inspect_residual_family_clusters_before_data_training_or_evaluator_change"
    )
    diagnosis["execution_scope"]["source_formal_heldout_predictions_read_as_input"] = True
    return diagnosis


def _family_short_name(task_family: str) -> str:
    return _sanitize_public_summary(task_family.split("|", 1)[0] if task_family else "unknown")


def _deferred_target_reason(short_name: str) -> str:
    if short_name == "blocked":
        return "safety-sensitive target; needs a dedicated safety-policy proposal before data or training changes"
    if short_name == "clarify":
        return "route/intent ambiguity target; should follow a separate ontology-boundary proposal"
    if short_name == "extract":
        return "smaller row cluster and mixed slot/route residuals; keep after the largest scoped target"
    if short_name in {"search", "navigate"}:
        return "smaller mostly canonical wording or slot-value target; defer until larger clusters are handled"
    return "lower-ranked row cluster for the current formal held-out residual diagnosis"


def _residual_cluster_action_candidate(short_name: str) -> str:
    if short_name == "form_fill":
        return "inspect_form_fill_boundary_and_field_specificity_before_new_data_or_training"
    if short_name == "blocked":
        return "dedicated_safety_boundary_inspection_before_data_or_training"
    if short_name == "clarify":
        return "route_intent_boundary_inspection_before_data_or_training"
    if short_name == "extract":
        return "extract_target_canonicalization_review_before_data_or_training"
    if short_name in {"search", "navigate"}:
        return "label_canonicalization_review_before_data_or_training"
    return "inspect_lower_ranked_cluster_before_data_or_training"


def inspect_formal_heldout_residual_clusters(
    *,
    residual_diagnosis: dict[str, Any],
) -> dict[str, Any]:
    if residual_diagnosis.get("evidence_kind") != "formal_heldout_residual_family_diagnosis":
        raise ValueError("residual diagnosis must be formal_heldout_residual_family_diagnosis evidence")

    residuals = [entry for entry in residual_diagnosis.get("residuals", []) if isinstance(entry, dict)]
    cluster_rows: dict[tuple[str, str, str, str], dict[str, set[str]]] = {}
    cluster_sources: dict[tuple[str, str, str, str], dict[str, int]] = {}
    cluster_examples: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    unique_row_keys: set[tuple[str, str]] = set()
    for residual in residuals:
        task_family = _sanitize_public_summary(str(residual.get("task_family", "unknown")))
        split = _sanitize_public_summary(str(residual.get("split", "unknown")))
        row_id = _sanitize_id(str(residual.get("row_id", "")))
        field_path = _sanitize_public_summary(str(residual.get("field_path", "unknown")))
        category = _sanitize_public_summary(str(residual.get("category", "unknown")))
        mismatch_category = _sanitize_public_summary(str(residual.get("mismatch_category", "unknown")))
        source_family_id = _sanitize_id(str(residual.get("source_family_id", "")))
        cluster_key = (task_family, field_path, category, mismatch_category)
        unique_row_keys.add((split, row_id))

        cluster_rows.setdefault(cluster_key, {}).setdefault(split, set()).add(row_id)
        sources = cluster_sources.setdefault(cluster_key, {})
        sources[source_family_id] = sources.get(source_family_id, 0) + 1
        examples = cluster_examples.setdefault(cluster_key, [])
        if len(examples) < 5:
            examples.append(
                {
                    "split": split,
                    "row_id": row_id,
                    "source_family_id": source_family_id,
                    "field_path": field_path,
                    "category": category,
                    "mismatch_category": mismatch_category,
                    "gold_value_summary": _sanitize_public_summary(
                        str(residual.get("gold_value_summary", "unknown"))
                    ),
                    "predicted_value_summary": _sanitize_public_summary(
                        str(residual.get("predicted_value_summary", "unknown"))
                    ),
                }
            )

    clusters: list[dict[str, Any]] = []
    for cluster_key, rows_by_split in cluster_rows.items():
        task_family, field_path, category, mismatch_category = cluster_key
        split_row_counts = {split: len(rows) for split, rows in sorted(rows_by_split.items())}
        total_rows = sum(split_row_counts.values())
        source_counts = dict(sorted(cluster_sources.get(cluster_key, {}).items()))
        residual_field_count = sum(source_counts.values())
        short_name = _family_short_name(task_family)
        clusters.append(
            {
                "task_family": task_family,
                "short_name": short_name,
                "field_path": field_path,
                "category": category,
                "mismatch_category": mismatch_category,
                "residual_row_count": total_rows,
                "residual_rows_by_split": split_row_counts,
                "residual_field_count": residual_field_count,
                "source_family_counts": source_counts,
                "representative_examples": cluster_examples.get(cluster_key, []),
                "recommended_action_candidate": _residual_cluster_action_candidate(short_name),
            }
        )
    clusters.sort(
        key=lambda item: (
            -int(item["residual_row_count"]),
            -int(item["residual_field_count"]),
            str(item["task_family"]),
        )
    )
    if not clusters:
        raise ValueError("residual diagnosis contains no residual clusters")

    expected_rows = int(residual_diagnosis.get("summary", {}).get("residual_row_count", 0))
    expected_fields = len(residuals)
    clustered_rows = len(unique_row_keys)
    clustered_fields = sum(int(cluster["residual_field_count"]) for cluster in clusters)
    source_count_consistency = {
        "expected_residual_rows": expected_rows,
        "clustered_residual_rows": clustered_rows,
        "expected_residual_fields": expected_fields,
        "clustered_residual_fields": clustered_fields,
        "ok": expected_rows == clustered_rows and expected_fields == clustered_fields,
    }
    if not source_count_consistency["ok"]:
        raise ValueError("clustered residual rows do not match source residual row count")

    top_cluster = clusters[0]
    summary = residual_diagnosis.get("summary", {})
    return {
        "evidence_kind": "formal_heldout_residual_cluster_inspection",
        "diagnostic_kind": "formal_public_heldout_residual_cluster_inspection",
        "source_residual_diagnosis": {
            "evidence_kind": _sanitize_public_summary(str(residual_diagnosis.get("evidence_kind", ""))),
            "diagnostic_kind": _sanitize_public_summary(str(residual_diagnosis.get("diagnostic_kind", ""))),
            "source_formal_heldout_evidence": _sanitize_public_value(
                residual_diagnosis.get("source_formal_heldout_evidence", {})
            ),
            "diagnosis_artifact": (
                "reports/public-sample/formal-heldout-residual-family-diagnosis/"
                "formal_heldout_residual_family_diagnosis.json"
            ),
        },
        "summary": {
            "strict_contract_exact_match": summary.get("strict_contract_exact_match", {}),
            "strict_slot_f1": summary.get("strict_slot_f1", {}),
            "soft_slot_f1": summary.get("soft_slot_f1", {}),
            "soft_slot_f1_primary_metric": False,
            "residual_row_count": expected_rows,
            "source_residual_field_count": expected_fields,
            "cluster_count": len(clusters),
            "top_cluster_task_family": top_cluster["task_family"],
            "top_cluster_field_path": top_cluster["field_path"],
            "top_cluster_residual_rows": top_cluster["residual_row_count"],
            "top_cluster_residual_fields": top_cluster["residual_field_count"],
            "recommended_next_step": "review_ranked_clusters_before_data_training_or_evaluator_change",
        },
        "source_count_consistency": source_count_consistency,
        "aggregates": {
            "by_split_residual_rows": _sanitize_public_value(
                residual_diagnosis.get("aggregates", {}).get("by_split_residual_rows", {})
            ),
            "by_field_path": _sanitize_public_value(
                residual_diagnosis.get("aggregates", {}).get("by_field_path", {})
            ),
            "by_category": _sanitize_public_value(
                residual_diagnosis.get("aggregates", {}).get("by_category", {})
            ),
            "by_source_family": _sanitize_public_value(
                residual_diagnosis.get("aggregates", {}).get("by_source_family", {})
            ),
        },
        "residual_clusters": clusters,
        "execution_scope": {
            "source_residual_diagnosis_read_as_input": True,
            "raw_predictions_read": False,
            "prediction_run": False,
            "training_run": False,
            "sft_training_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "dataset_mutation": False,
            "a100_job": False,
            "new_data_generated": False,
            "gold_policy_change": False,
            "prompt_change": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
            "semantic_equivalence_scoring": False,
            "prediction_repair": False,
            "prediction_replacement": False,
            "prediction_repair_or_replacement": False,
            "prediction_rescore": False,
        },
        "claims": {
            "analysis_only": True,
            "model_recovery_claim": False,
            "held_out_recovery_claim": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
            "adapter_release_claim": False,
            "checkpoint_release_claim": False,
        },
    }


_FORM_FILL_TASK_FAMILY = "form_fill|fill_form|requires_confirmation|confirm:true|slots:field"


def _form_fill_boundary_field_specificity_bucket(cluster: dict[str, Any]) -> tuple[str, str]:
    field_path = str(cluster.get("field_path", "unknown"))
    if field_path == "normalized_command":
        return (
            "missing_confirmation_marker",
            "normalized_command omits or alters explicit confirmation wording such as 并确认",
        )
    if field_path == "slots":
        return (
            "field_specificity_or_alias_drift",
            "slot field labels differ by specificity or alias while staying in form-fill shape",
        )
    if field_path in {"task_type", "route", "safety.reason"}:
        return (
            "route_intent_leakage",
            "form-fill request is interpreted as a different intent or route boundary",
        )
    return (
        "other_form_fill_boundary_residual",
        "lower-ranked form-fill residual needing separate manual inspection",
    )


def inspect_form_fill_boundary_field_specificity(
    *,
    residual_cluster_inspection: dict[str, Any],
) -> dict[str, Any]:
    if residual_cluster_inspection.get("evidence_kind") != "formal_heldout_residual_cluster_inspection":
        raise ValueError("residual cluster inspection must be formal_heldout_residual_cluster_inspection evidence")

    source_evidence = (
        residual_cluster_inspection.get("source_residual_diagnosis", {}).get("source_formal_heldout_evidence", {})
    )
    source_manifest_id = _sanitize_public_summary(str(source_evidence.get("dataset_manifest_id", "")))
    clusters = [
        cluster
        for cluster in residual_cluster_inspection.get("residual_clusters", [])
        if isinstance(cluster, dict) and cluster.get("task_family") == _FORM_FILL_TASK_FAMILY
    ]
    if not clusters:
        raise ValueError("residual cluster inspection contains no form_fill clusters")

    bucket_accumulator: dict[str, dict[str, Any]] = {}
    for cluster in clusters:
        bucket_name, interpretation = _form_fill_boundary_field_specificity_bucket(cluster)
        bucket = bucket_accumulator.setdefault(
            bucket_name,
            {
                "bucket": bucket_name,
                "diagnostic_interpretation": interpretation,
                "cluster_count": 0,
                "cluster_row_incidence_total": 0,
                "residual_field_total": 0,
                "split_counts": {},
                "field_paths": set(),
                "categories": {},
                "source_family_counts": {},
                "representative_examples": [],
                "recommended_action_candidate": "",
            },
        )
        bucket["cluster_count"] += 1
        bucket["cluster_row_incidence_total"] += int(cluster.get("residual_row_count", 0))
        bucket["residual_field_total"] += int(cluster.get("residual_field_count", 0))
        bucket["field_paths"].add(_sanitize_public_summary(str(cluster.get("field_path", "unknown"))))
        category = _sanitize_public_summary(str(cluster.get("category", "unknown")))
        bucket["categories"][category] = bucket["categories"].get(category, 0) + int(
            cluster.get("residual_field_count", 0)
        )
        for split, count in cluster.get("residual_rows_by_split", {}).items():
            split_name = _sanitize_public_summary(str(split))
            bucket["split_counts"][split_name] = bucket["split_counts"].get(split_name, 0) + int(count)
        for source_family, count in cluster.get("source_family_counts", {}).items():
            family_id = _sanitize_id(str(source_family))
            bucket["source_family_counts"][family_id] = bucket["source_family_counts"].get(family_id, 0) + int(
                count
            )
        for example in cluster.get("representative_examples", []):
            if len(bucket["representative_examples"]) >= 5 or not isinstance(example, dict):
                continue
            bucket["representative_examples"].append(_sanitize_public_value(example))

    action_candidates = {
        "missing_confirmation_marker": "define_form_fill_confirmation_marker_policy_before_data_or_training",
        "field_specificity_or_alias_drift": "define_form_fill_field_specificity_policy_before_data_or_training",
        "route_intent_leakage": "inspect_form_fill_clarify_boundary_before_data_or_training",
        "other_form_fill_boundary_residual": "inspect_lower_ranked_form_fill_residual_before_data_or_training",
    }
    buckets: list[dict[str, Any]] = []
    for bucket in bucket_accumulator.values():
        bucket["field_paths"] = sorted(bucket["field_paths"])
        bucket["categories"] = dict(sorted(bucket["categories"].items()))
        bucket["split_counts"] = dict(sorted(bucket["split_counts"].items()))
        bucket["source_family_counts"] = dict(sorted(bucket["source_family_counts"].items()))
        bucket["recommended_action_candidate"] = action_candidates.get(
            bucket["bucket"], "inspect_form_fill_bucket_before_data_or_training"
        )
        buckets.append(bucket)
    buckets.sort(
        key=lambda item: (
            -int(item["cluster_row_incidence_total"]),
            -int(item["residual_field_total"]),
            str(item["bucket"]),
        )
    )

    cluster_count = len(clusters)
    bucketed_cluster_count = sum(int(bucket["cluster_count"]) for bucket in buckets)
    residual_field_total = sum(int(cluster.get("residual_field_count", 0)) for cluster in clusters)
    bucketed_field_total = sum(int(bucket["residual_field_total"]) for bucket in buckets)
    cluster_row_total = sum(int(cluster.get("residual_row_count", 0)) for cluster in clusters)
    bucketed_cluster_row_total = sum(int(bucket["cluster_row_incidence_total"]) for bucket in buckets)
    source_count_consistency = {
        "source_form_fill_cluster_count": cluster_count,
        "bucketed_form_fill_cluster_count": bucketed_cluster_count,
        "source_form_fill_cluster_row_incidence_total": cluster_row_total,
        "bucketed_form_fill_cluster_row_incidence_total": bucketed_cluster_row_total,
        "source_form_fill_residual_fields": residual_field_total,
        "bucketed_form_fill_residual_fields": bucketed_field_total,
        "ok": (
            cluster_count == bucketed_cluster_count
            and cluster_row_total == bucketed_cluster_row_total
            and residual_field_total == bucketed_field_total
        ),
    }
    if not source_count_consistency["ok"]:
        raise ValueError("form-fill bucket counts do not match source clusters")

    source_summary = residual_cluster_inspection.get("summary", {})
    return {
        "evidence_kind": "form_fill_boundary_field_specificity_inspection",
        "diagnostic_kind": "formal_public_form_fill_boundary_field_specificity_inspection",
        "source_residual_cluster_inspection": {
            "evidence_kind": _sanitize_public_summary(str(residual_cluster_inspection.get("evidence_kind", ""))),
            "diagnostic_kind": _sanitize_public_summary(
                str(residual_cluster_inspection.get("diagnostic_kind", ""))
            ),
            "source_manifest_id": source_manifest_id,
            "cluster_artifact": (
                "reports/public-sample/formal-heldout-residual-cluster-inspection/"
                "formal_heldout_residual_cluster_inspection.json"
            ),
        },
        "summary": {
            "strict_contract_exact_match": source_summary.get("strict_contract_exact_match", {}),
            "strict_slot_f1": source_summary.get("strict_slot_f1", {}),
            "soft_slot_f1": source_summary.get("soft_slot_f1", {}),
            "soft_slot_f1_primary_metric": False,
            "form_fill_cluster_count": cluster_count,
            "form_fill_cluster_row_incidence_total": cluster_row_total,
            "form_fill_residual_field_total": residual_field_total,
            "bucket_count": len(buckets),
            "top_bucket": buckets[0]["bucket"],
            "recommended_next_step": (
                "define_form_fill_confirmation_and_field_specificity_policy_before_data_or_training"
            ),
        },
        "source_count_consistency": source_count_consistency,
        "form_fill_buckets": buckets,
        "unsupported_buckets": {
            "harmless_strict_wording_mismatch": "not observed from current form-fill cluster-only evidence"
        },
        "execution_scope": {
            "source_residual_cluster_inspection_read_as_input": True,
            "raw_predictions_read": False,
            "prediction_run": False,
            "a100_job": False,
            "training_run": False,
            "sft_training_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "dataset_mutation": False,
            "new_data_generated": False,
            "gold_policy_change": False,
            "prompt_change": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
            "semantic_equivalence_scoring": False,
            "prediction_repair": False,
            "prediction_replacement": False,
            "prediction_repair_or_replacement": False,
            "prediction_rescore": False,
        },
        "claims": {
            "analysis_only": True,
            "model_recovery_claim": False,
            "held_out_recovery_claim": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
            "adapter_release_claim": False,
            "checkpoint_release_claim": False,
        },
    }


def _policy_section_from_form_fill_bucket(
    bucket: dict[str, Any],
    *,
    section: str,
    label: str,
    policy_statement: str,
    candidate_next_action: str,
) -> dict[str, Any]:
    return {
        "section": section,
        "label": label,
        "source_bucket": _sanitize_public_summary(str(bucket.get("bucket", ""))),
        "policy_statement": policy_statement,
        "source_evidence": {
            "cluster_count": int(bucket.get("cluster_count", 0)),
            "cluster_row_incidence_total": int(bucket.get("cluster_row_incidence_total", 0)),
            "residual_field_total": int(bucket.get("residual_field_total", 0)),
            "split_counts": _sanitize_public_value(bucket.get("split_counts", {})),
            "field_paths": _sanitize_public_value(bucket.get("field_paths", [])),
            "categories": _sanitize_public_value(bucket.get("categories", {})),
            "source_family_counts": _sanitize_public_value(bucket.get("source_family_counts", {})),
            "representative_examples": _sanitize_public_value(bucket.get("representative_examples", [])),
        },
        "candidate_next_action": candidate_next_action,
        "requires_separate_openspec_change_before_execution": True,
    }


def define_form_fill_confirmation_field_policy(
    form_fill_inspection: dict[str, Any],
    *,
    inspection_artifact: str | None = None,
) -> dict[str, Any]:
    if form_fill_inspection.get("evidence_kind") != "form_fill_boundary_field_specificity_inspection":
        raise ValueError("form-fill inspection must be form_fill_boundary_field_specificity_inspection evidence")

    source = form_fill_inspection.get("source_residual_cluster_inspection", {})
    source_summary = form_fill_inspection.get("summary", {})
    buckets = {
        str(bucket.get("bucket")): bucket
        for bucket in form_fill_inspection.get("form_fill_buckets", [])
        if isinstance(bucket, dict)
    }
    required_buckets = (
        "missing_confirmation_marker",
        "field_specificity_or_alias_drift",
        "route_intent_leakage",
    )
    missing_buckets = [bucket for bucket in required_buckets if bucket not in buckets]
    if missing_buckets:
        raise ValueError("form-fill inspection missing required bucket(s): " + ", ".join(missing_buckets))

    policy_sections = [
        _policy_section_from_form_fill_bucket(
            buckets["missing_confirmation_marker"],
            section="confirmation_markers",
            label="Confirmation markers",
            policy_statement=(
                "Future form-fill remediation should preserve explicit user confirmation wording in "
                "normalized_command when the source command asks to submit or confirm a filled form."
            ),
            candidate_next_action=(
                "propose_bounded_confirmation_marker_data_or_prompt_remediation_after_policy_review"
            ),
        ),
        _policy_section_from_form_fill_bucket(
            buckets["field_specificity_or_alias_drift"],
            section="field_specificity_or_alias_drift",
            label="Field specificity or alias drift",
            policy_statement=(
                "Future remediation should decide field-label canonicalization and alias boundaries before "
                "adding examples or changing prompt wording for slots."
            ),
            candidate_next_action=(
                "propose_bounded_field_specificity_or_alias_policy_remediation_after_policy_review"
            ),
        ),
        _policy_section_from_form_fill_bucket(
            buckets["route_intent_leakage"],
            section="route_intent_leakage",
            label="Route or intent boundary leakage",
            policy_statement=(
                "Future remediation should keep form-fill route and intent boundaries separate from search, "
                "clarification, and safety-stop behavior unless a later OpenSpec phase changes that contract."
            ),
            candidate_next_action="inspect_route_intent_boundary_before_any_remediation",
        ),
    ]

    source_count_consistency = _sanitize_public_value(form_fill_inspection.get("source_count_consistency", {}))
    if isinstance(source_count_consistency, dict) and not bool(source_count_consistency.get("ok", False)):
        raise ValueError("form-fill inspection source count consistency is not ok")

    unsupported_changes = [
        {
            "change": "evaluator_relaxation",
            "reason": "strict contract_exact_match and strict slot_f1 remain authoritative",
        },
        {
            "change": "soft_metric_promotion",
            "reason": "slot_f1_soft remains diagnostic-only and is not promoted to a primary metric",
        },
        {
            "change": "data_mutation",
            "reason": "policy definition does not add, delete, rewrite, or regenerate dataset rows",
        },
        {
            "change": "training_run",
            "reason": "policy definition does not run SFT, DPO, GRPO, or any A100 job",
        },
        {
            "change": "prediction_repair",
            "reason": "policy definition does not repair, replace, normalize, or re-score predictions",
        },
        {
            "change": "prompt_change",
            "reason": "prompt or formatting changes require a separate approved OpenSpec phase",
        },
        {
            "change": "gold_policy_mutation",
            "reason": "gold contract policy changes require a separate approved OpenSpec phase",
        },
    ]

    return {
        "evidence_kind": "form_fill_confirmation_field_policy",
        "policy_kind": "public_form_fill_confirmation_and_field_specificity_policy",
        "source_form_fill_inspection": {
            "evidence_kind": _sanitize_public_summary(str(form_fill_inspection.get("evidence_kind", ""))),
            "diagnostic_kind": _sanitize_public_summary(str(form_fill_inspection.get("diagnostic_kind", ""))),
            "source_manifest_id": _sanitize_public_summary(str(source.get("source_manifest_id", ""))),
            "inspection_artifact": _sanitize_public_summary(
                inspection_artifact
                or (
                    "reports/public-sample/form-fill-boundary-field-specificity-inspection/"
                    "form_fill_boundary_field_specificity_inspection.json"
                )
            ),
            "source_cluster_artifact": _sanitize_public_summary(str(source.get("cluster_artifact", ""))),
        },
        "summary": {
            "strict_contract_exact_match": _sanitize_public_value(
                source_summary.get("strict_contract_exact_match", {})
            ),
            "strict_slot_f1": _sanitize_public_value(source_summary.get("strict_slot_f1", {})),
            "slot_f1_soft": _sanitize_public_value(source_summary.get("soft_slot_f1", {})),
            "slot_f1_soft_primary_metric": False,
            "source_bucket_count": int(source_summary.get("bucket_count", len(buckets))),
            "policy_section_count": len(policy_sections),
            "cluster_row_incidence_total": int(source_summary.get("form_fill_cluster_row_incidence_total", 0)),
            "residual_field_total": int(source_summary.get("form_fill_residual_field_total", 0)),
            "recommended_next_step": "open_separate_policy_remediation_phase_after_review",
        },
        "metric_authority": {
            "contract_exact_match": "authoritative_strict_metric",
            "slot_f1": "authoritative_strict_metric",
            "slot_f1_soft": "diagnostic_only_not_primary",
            "contract_evaluation_ladder": "authoritative",
            "prediction_repair_or_rescore": False,
        },
        "source_count_consistency": source_count_consistency,
        "policy_sections": policy_sections,
        "unsupported_changes": unsupported_changes,
        "candidate_next_actions": [
            section["candidate_next_action"] for section in policy_sections
        ],
        "execution_scope": {
            "form_fill_inspection_read_as_input": True,
            "raw_predictions_read": False,
            "prediction_run": False,
            "a100_job": False,
            "training_run": False,
            "sft_training_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "dataset_mutation": False,
            "candidate_generation": False,
            "gold_policy_change": False,
            "prompt_change": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
            "semantic_equivalence_scoring": False,
            "prediction_repair": False,
            "prediction_replacement": False,
            "prediction_repair_or_replacement": False,
            "prediction_rescore": False,
        },
        "claims": {
            "analysis_only": True,
            "policy_only": True,
            "model_recovery_claim": False,
            "held_out_recovery_claim": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
            "adapter_release_claim": False,
            "checkpoint_release_claim": False,
        },
    }


def select_formal_heldout_remediation_target(
    *,
    residual_diagnosis: dict[str, Any],
) -> dict[str, Any]:
    if residual_diagnosis.get("evidence_kind") != "formal_heldout_residual_family_diagnosis":
        raise ValueError("residual diagnosis must be formal_heldout_residual_family_diagnosis evidence")

    residuals = [entry for entry in residual_diagnosis.get("residuals", []) if isinstance(entry, dict)]
    family_rows: dict[str, dict[str, set[str]]] = {}
    family_fields: dict[str, dict[str, int]] = {}
    family_examples: dict[str, list[dict[str, Any]]] = {}
    for residual in residuals:
        task_family = _sanitize_public_summary(str(residual.get("task_family", "unknown")))
        split = _sanitize_public_summary(str(residual.get("split", "unknown")))
        row_id = _sanitize_id(str(residual.get("row_id", "")))
        field_path = _sanitize_public_summary(str(residual.get("field_path", "unknown")))
        family_rows.setdefault(task_family, {}).setdefault(split, set()).add(row_id)
        field_counts = family_fields.setdefault(task_family, {})
        field_counts[field_path] = field_counts.get(field_path, 0) + 1
        examples = family_examples.setdefault(task_family, [])
        if len(examples) < 5:
            examples.append(
                {
                    "split": split,
                    "row_id": row_id,
                    "source_family_id": _sanitize_id(str(residual.get("source_family_id", ""))),
                    "field_path": field_path,
                    "mismatch_category": _sanitize_public_summary(
                        str(residual.get("mismatch_category", "unknown"))
                    ),
                    "gold_value_summary": _sanitize_public_summary(
                        str(residual.get("gold_value_summary", "unknown"))
                    ),
                    "predicted_value_summary": _sanitize_public_summary(
                        str(residual.get("predicted_value_summary", "unknown"))
                    ),
                }
            )

    ranked_families: list[dict[str, Any]] = []
    for task_family, rows_by_split in family_rows.items():
        split_row_counts = {split: len(rows) for split, rows in sorted(rows_by_split.items())}
        total_rows = sum(split_row_counts.values())
        field_counts = dict(sorted(family_fields.get(task_family, {}).items()))
        total_fields = sum(field_counts.values())
        ranked_families.append(
            {
                "task_family": task_family,
                "short_name": _family_short_name(task_family),
                "residual_row_count": total_rows,
                "residual_rows_by_split": split_row_counts,
                "residual_field_count": total_fields,
                "residual_field_counts": field_counts,
                "representative_examples": family_examples.get(task_family, []),
            }
        )
    ranked_families.sort(
        key=lambda item: (
            -int(item["residual_row_count"]),
            -int(item["residual_field_count"]),
            str(item["task_family"]),
        )
    )
    if not ranked_families:
        raise ValueError("residual diagnosis contains no residual families")

    selected = ranked_families[0]
    selected_short_name = str(selected["short_name"])
    selected_slug = selected_short_name.replace("_", "-")
    deferred = [
        {
            "task_family": item["task_family"],
            "short_name": item["short_name"],
            "residual_row_count": item["residual_row_count"],
            "reason": _deferred_target_reason(str(item["short_name"])),
        }
        for item in ranked_families[1:4]
    ]
    source_consistency = residual_diagnosis.get("summary", {}).get("source_count_consistency", {})
    total_ranked_rows = sum(int(item["residual_row_count"]) for item in ranked_families)
    expected_rows = int(residual_diagnosis.get("summary", {}).get("residual_row_count", 0))
    count_consistency = {
        "source_count_consistency_ok": bool(
            isinstance(source_consistency, dict) and source_consistency.get("ok") is True
        ),
        "expected_residual_rows": expected_rows,
        "ranked_residual_rows": total_ranked_rows,
        "ok": expected_rows == total_ranked_rows,
    }
    if not count_consistency["ok"]:
        raise ValueError("ranked residual rows do not match source residual row count")

    return {
        "evidence_kind": "formal_heldout_remediation_target_selection",
        "selection_status": "selected_first_bounded_target",
        "source_residual_diagnosis": {
            "evidence_kind": _sanitize_public_summary(str(residual_diagnosis.get("evidence_kind", ""))),
            "diagnostic_kind": _sanitize_public_summary(str(residual_diagnosis.get("diagnostic_kind", ""))),
            "source_formal_heldout_evidence": _sanitize_public_value(
                residual_diagnosis.get("source_formal_heldout_evidence", {})
            ),
            "diagnosis_artifact": (
                "reports/public-sample/formal-heldout-residual-family-diagnosis/"
                "formal_heldout_residual_family_diagnosis.json"
            ),
        },
        "summary": {
            "selected_target": selected_short_name,
            "selected_task_family": selected["task_family"],
            "selected_residual_row_count": selected["residual_row_count"],
            "selected_residual_field_count": selected["residual_field_count"],
            "ranked_family_count": len(ranked_families),
            "source_count_consistency": count_consistency,
            "strict_contract_exact_match": residual_diagnosis.get("summary", {}).get(
                "strict_contract_exact_match",
                {},
            ),
            "strict_slot_f1": residual_diagnosis.get("summary", {}).get("strict_slot_f1", {}),
            "soft_slot_f1": residual_diagnosis.get("summary", {}).get("soft_slot_f1", {}),
            "soft_slot_f1_primary_metric": False,
            "recommended_next_change": f"remediate-{selected_slug}-formal-heldout-residuals",
            "recommended_next_step": (
                f"open_bounded_remediate-{selected_slug}-formal-heldout-residuals_proposal_"
                "before_data_training_or_metric_changes"
            ),
        },
        "selection": {
            "selected": selected,
            "rationale": [
                "largest affected strict residual row cluster in the current formal held-out diagnosis",
                "field distribution points to a bounded family-specific remediation target",
                "lower policy risk than starting with the safety-sensitive blocked_payment cluster",
            ],
            "deferred_targets": deferred,
        },
        "ranked_families": ranked_families,
        "execution_scope": {
            "source_residual_diagnosis_read_as_input": True,
            "raw_predictions_read": False,
            "training_run": False,
            "dpo_run": False,
            "prediction_run": False,
            "a100_job": False,
            "new_data_generated": False,
            "gold_policy_change": False,
            "evaluator_metric_change": False,
            "slot_normalization": False,
        },
        "claims": {
            "model_recovery_claim": False,
            "held_out_recovery_claim": False,
            "production_readiness_claim": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
            "adapter_release_claim": False,
            "checkpoint_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
    }


_FORM_FILL_TASK_FAMILY = "form_fill|fill_form|requires_confirmation|confirm:true|slots:field"


def _is_form_fill_clarify_boundary_residual(residual: dict[str, Any]) -> bool:
    predicted_value = residual.get("predicted_value")
    if str(residual.get("field_path", "")) in {"task_type", "route"} and predicted_value == "clarify":
        return True
    if str(residual.get("field_path", "")) == "safety.reason" and predicted_value == "ambiguous_request":
        return True
    if isinstance(predicted_value, dict) and "ambiguity" in predicted_value:
        return True
    return False


def _form_fill_remediation_bucket(residual: dict[str, Any]) -> str:
    if _is_form_fill_clarify_boundary_residual(residual):
        return "clarify_boundary_confusion"
    field_path = str(residual.get("field_path", ""))
    gold_value = residual.get("gold_value")
    predicted_value = residual.get("predicted_value")
    if field_path == "slots":
        return "field_name_specificity_drift"
    if field_path == "normalized_command":
        gold_text = str(gold_value)
        predicted_text = str(predicted_value)
        if "并确认" in gold_text and not predicted_text.endswith("并确认"):
            return "confirmation_marker_missing_or_reordered"
        return "field_name_specificity_drift"
    return "other_form_fill_strict_drift"


def diagnose_form_fill_remediation_plan(
    *,
    residual_diagnosis: dict[str, Any],
    target_selection: dict[str, Any],
) -> dict[str, Any]:
    selected_target = target_selection.get("summary", {}).get("selected_target")
    selected_task_family = target_selection.get("summary", {}).get("selected_task_family")
    if selected_target != "form_fill" or selected_task_family != _FORM_FILL_TASK_FAMILY:
        raise ValueError("target selection must select form_fill before publishing this diagnosis")

    source_residuals = [entry for entry in residual_diagnosis.get("residuals", []) if isinstance(entry, dict)]
    form_fill_residuals = [
        entry for entry in source_residuals if str(entry.get("task_family", "")) == _FORM_FILL_TASK_FAMILY
    ]
    row_ids = {
        (str(entry.get("split", "")), _sanitize_id(str(entry.get("row_id", "")))) for entry in form_fill_residuals
    }
    expected_rows = int(target_selection.get("summary", {}).get("selected_residual_row_count", 0))
    expected_fields = int(target_selection.get("summary", {}).get("selected_residual_field_count", 0))
    if len(row_ids) != expected_rows or len(form_fill_residuals) != expected_fields:
        raise ValueError("form_fill residual counts do not match target selection summary")

    buckets: dict[str, dict[str, Any]] = {}
    residual_entries: list[dict[str, Any]] = []
    for residual in form_fill_residuals:
        bucket = _form_fill_remediation_bucket(residual)
        split = _sanitize_public_summary(str(residual.get("split", "unknown")))
        row_id = _sanitize_id(str(residual.get("row_id", "")))
        source_family_id = _sanitize_id(str(residual.get("source_family_id", "")))
        field_path = _sanitize_public_summary(str(residual.get("field_path", "unknown")))
        entry = buckets.setdefault(
            bucket,
            {
                "bucket": bucket,
                "residual_field_count": 0,
                "residual_rows": set(),
                "by_split": {},
                "by_field_path": {},
                "by_source_family": {},
                "representative_examples": [],
            },
        )
        entry["residual_field_count"] += 1
        entry["residual_rows"].add(f"{split}:{row_id}")
        entry["by_split"][split] = entry["by_split"].get(split, 0) + 1
        entry["by_field_path"][field_path] = entry["by_field_path"].get(field_path, 0) + 1
        entry["by_source_family"][source_family_id] = entry["by_source_family"].get(source_family_id, 0) + 1
        example = {
            "split": split,
            "row_id": row_id,
            "source_family_id": source_family_id,
            "field_path": field_path,
            "gold_value": _sanitize_public_value(residual.get("gold_value")),
            "predicted_value": _sanitize_public_value(residual.get("predicted_value")),
            "gold_value_summary": _sanitize_public_summary(str(residual.get("gold_value_summary", "unknown"))),
            "predicted_value_summary": _sanitize_public_summary(
                str(residual.get("predicted_value_summary", "unknown"))
            ),
        }
        if len(entry["representative_examples"]) < 5:
            entry["representative_examples"].append(example)
        residual_entries.append(
            {
                **example,
                "bucket": bucket,
                "mismatch_category": _sanitize_public_summary(str(residual.get("mismatch_category", "unknown"))),
            }
        )

    bucket_summaries: list[dict[str, Any]] = []
    for bucket, entry in buckets.items():
        rows = sorted(entry.pop("residual_rows"))
        bucket_summaries.append(
            {
                **entry,
                "bucket": bucket,
                "residual_row_count": len(rows),
                "residual_row_refs": rows,
                "by_split": dict(sorted(entry["by_split"].items())),
                "by_field_path": dict(sorted(entry["by_field_path"].items())),
                "by_source_family": dict(sorted(entry["by_source_family"].items())),
            }
        )
    bucket_summaries.sort(
        key=lambda item: (
            -int(item["residual_row_count"]),
            -int(item["residual_field_count"]),
            str(item["bucket"]),
        )
    )

    bucket_counts = {item["bucket"]: item["residual_field_count"] for item in bucket_summaries}
    row_bucket_counts = {item["bucket"]: item["residual_row_count"] for item in bucket_summaries}
    field_counts = _count_by([entry["field_path"] for entry in residual_entries])
    split_counts = _count_by([entry["split"] for entry in residual_entries])
    source_family_counts = _count_by([entry["source_family_id"] for entry in residual_entries])

    return {
        "evidence_kind": "formal_heldout_form_fill_remediation_plan",
        "remediation_status": "plan_only_no_data_no_training_no_metric_change",
        "source_target_selection": {
            "evidence_kind": _sanitize_public_summary(str(target_selection.get("evidence_kind", ""))),
            "selection_artifact": (
                "reports/public-sample/formal-heldout-remediation-target-selection/"
                "formal_heldout_remediation_target_selection.json"
            ),
            "selected_target": "form_fill",
            "selected_task_family": _FORM_FILL_TASK_FAMILY,
        },
        "source_residual_diagnosis": {
            "evidence_kind": _sanitize_public_summary(str(residual_diagnosis.get("evidence_kind", ""))),
            "diagnosis_artifact": (
                "reports/public-sample/formal-heldout-residual-family-diagnosis/"
                "formal_heldout_residual_family_diagnosis.json"
            ),
        },
        "summary": {
            "target": "form_fill",
            "target_task_family": _FORM_FILL_TASK_FAMILY,
            "residual_row_count": len(row_ids),
            "residual_field_count": len(form_fill_residuals),
            "bucket_field_counts": bucket_counts,
            "bucket_row_counts": row_bucket_counts,
            "by_field_path": field_counts,
            "by_split": split_counts,
            "by_source_family": source_family_counts,
            "count_consistency": {
                "expected_residual_rows": expected_rows,
                "computed_residual_rows": len(row_ids),
                "expected_residual_fields": expected_fields,
                "computed_residual_fields": len(form_fill_residuals),
                "ok": len(row_ids) == expected_rows and len(form_fill_residuals) == expected_fields,
            },
            "recommended_strategy": "prompt_policy_clarification_plus_targeted_public_safe_case_design",
            "recommended_next_change": "design-form-fill-remediation-cases",
            "training_recommended_now": False,
            "dpo_recommended_now": False,
            "evaluator_change_recommended_now": False,
        },
        "remediation_buckets": bucket_summaries,
        "residuals": residual_entries,
        "acceptance_boundary": {
            "must_preserve_strict_contract_exact_match_as_primary": True,
            "must_preserve_strict_slot_f1_as_primary": True,
            "slot_f1_soft_diagnostic_only": True,
            "future_case_design_must_not_mutate_current_heldout_splits": True,
            "future_training_requires_separate_user_confirmed_phase": True,
        },
        "execution_scope": {
            "source_residual_diagnosis_read_as_input": True,
            "source_target_selection_read_as_input": True,
            "raw_predictions_read": False,
            "new_data_generated": False,
            "public_heldout_modified": False,
            "gold_policy_change": False,
            "training_run": False,
            "dpo_run": False,
            "prediction_run": False,
            "a100_job": False,
            "evaluator_metric_change": False,
            "slot_normalization": False,
        },
        "claims": {
            "model_recovery_claim": False,
            "held_out_recovery_claim": False,
            "production_readiness_claim": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
            "adapter_release_claim": False,
            "checkpoint_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
    }


_FORM_FILL_CASE_DESIGN_GROUPS = {
    "confirmation_marker_missing_or_reordered": {
        "case_group_id": "form-fill-confirmation-marker-preservation",
        "policy_guidance_id": "form-fill-confirmation-marker-policy",
        "policy_guidance": (
            "When the user explicitly asks to confirm after filling a form field, preserve that "
            "confirmation intent in `normalized_command`, set `confirmation_required=true`, and keep "
            "`safety.reason=requires_confirmation`."
        ),
        "review_rationale": (
            "The largest residual bucket drops or reorders the explicit `并确认` marker even when the "
            "contract otherwise stays in the form-fill family."
        ),
        "candidate_cases": [
            {
                "case_id": "ff-confirm-phone",
                "input_intent": "填写手机号并确认",
                "expected_normalized_command_pattern": "填写手机号并确认",
                "expected_slots": {"field": "手机号"},
                "avoid": "Do not shorten to 填写手机号 when the input explicitly includes confirmation.",
            },
            {
                "case_id": "ff-confirm-shipping-address",
                "input_intent": "填写收货地址并确认",
                "expected_normalized_command_pattern": "填写收货地址并确认",
                "expected_slots": {"field": "收货地址"},
                "avoid": "Do not rewrite to a generic address form-fill command that drops confirmation.",
            },
            {
                "case_id": "ff-confirm-invoice-title",
                "input_intent": "填写发票抬头并确认",
                "expected_normalized_command_pattern": "填写发票抬头并确认",
                "expected_slots": {"field": "发票抬头"},
                "avoid": "Do not emit only 填写发票抬头 when confirmation is requested.",
            },
        ],
    },
    "field_name_specificity_drift": {
        "case_group_id": "form-fill-field-specificity-preservation",
        "policy_guidance_id": "form-fill-field-specificity-policy",
        "policy_guidance": (
            "For `form_fill` slots, preserve the most specific field name from the request; do not "
            "collapse domain-specific fields such as 收货地址, 发票抬头, or 预约时间 into generic aliases."
        ),
        "review_rationale": (
            "The second-largest bucket keeps the slot shape but loses specificity, for example "
            "收货地址 to 地址 or 发票抬头 to 抬头."
        ),
        "candidate_cases": [
            {
                "case_id": "ff-field-shipping-address",
                "input_intent": "填写收货地址",
                "expected_normalized_command_pattern": "填写收货地址",
                "expected_slots": {"field": "收货地址"},
                "avoid": "Do not collapse the field to 地址.",
            },
            {
                "case_id": "ff-field-invoice-title",
                "input_intent": "填写发票抬头",
                "expected_normalized_command_pattern": "填写发票抬头",
                "expected_slots": {"field": "发票抬头"},
                "avoid": "Do not collapse the field to 抬头 or 发票信息.",
            },
            {
                "case_id": "ff-field-appointment-time",
                "input_intent": "填写预约时间",
                "expected_normalized_command_pattern": "填写预约时间",
                "expected_slots": {"field": "预约时间"},
                "avoid": "Do not collapse the field to 时间.",
            },
        ],
    },
    "clarify_boundary_confusion": {
        "case_group_id": "form-fill-clarify-boundary-protection",
        "policy_guidance_id": "form-fill-clarify-boundary-policy",
        "policy_guidance": (
            "If the user specifies a concrete form field and asks the assistant to fill or confirm it, "
            "route to `form_fill` even when the value itself is absent; use `clarify` only when the target "
            "field/action is ambiguous."
        ),
        "review_rationale": (
            "A small but high-impact bucket turns concrete field-fill requests into `clarify`, changing "
            "task type, route, safety reason, and slot shape."
        ),
        "candidate_cases": [
            {
                "case_id": "ff-boundary-appointment-time",
                "input_intent": "填写预约时间并确认",
                "expected_normalized_command_pattern": "填写预约时间并确认",
                "expected_slots": {"field": "预约时间"},
                "expected_contract": {
                    "confirmation_required": True,
                    "route": "fill_form",
                    "safety.reason": "requires_confirmation",
                    "task_type": "form_fill",
                },
                "avoid": "Do not switch to clarify when the field is explicit.",
            },
            {
                "case_id": "ff-boundary-delivery-info",
                "input_intent": "确认前填写配送信息",
                "expected_normalized_command_pattern": "填写配送信息并确认",
                "expected_slots": {"field": "配送信息"},
                "expected_contract": {
                    "confirmation_required": True,
                    "route": "fill_form",
                    "safety.reason": "requires_confirmation",
                    "task_type": "form_fill",
                },
                "avoid": "Do not treat confirmation wording as an ambiguity request.",
            },
            {
                "case_id": "ff-boundary-contact-phone",
                "input_intent": "填联系电话，提交前确认",
                "expected_normalized_command_pattern": "填写联系电话并确认",
                "expected_slots": {"field": "联系电话"},
                "expected_contract": {
                    "confirmation_required": True,
                    "route": "fill_form",
                    "safety.reason": "requires_confirmation",
                    "task_type": "form_fill",
                },
                "avoid": "Do not emit slots.ambiguity when the field target is present.",
            },
        ],
    },
}


def design_form_fill_remediation_cases(*, remediation_plan: dict[str, Any]) -> dict[str, Any]:
    if remediation_plan.get("evidence_kind") != "formal_heldout_form_fill_remediation_plan":
        raise ValueError("source must be a formal_heldout_form_fill_remediation_plan form_fill remediation plan")
    if remediation_plan.get("remediation_status") != "plan_only_no_data_no_training_no_metric_change":
        raise ValueError("source form_fill remediation plan must be plan-only before case design")

    summary = remediation_plan.get("summary", {})
    if summary.get("target") != "form_fill" or summary.get("target_task_family") != _FORM_FILL_TASK_FAMILY:
        raise ValueError("source must be a form_fill remediation plan for the selected form_fill family")
    if summary.get("recommended_next_change") != "design-form-fill-remediation-cases":
        raise ValueError("source form_fill remediation plan does not recommend this case-design change")
    if summary.get("count_consistency", {}).get("ok") is not True:
        raise ValueError("source form_fill remediation plan count consistency must be ok")

    buckets = [bucket for bucket in remediation_plan.get("remediation_buckets", []) if isinstance(bucket, dict)]
    buckets_by_name = {str(bucket.get("bucket", "")): bucket for bucket in buckets}
    missing_buckets = sorted(set(_FORM_FILL_CASE_DESIGN_GROUPS) - set(buckets_by_name))
    if missing_buckets:
        raise ValueError(f"source form_fill remediation plan missing buckets: {missing_buckets}")

    guidance: list[dict[str, Any]] = []
    case_groups: list[dict[str, Any]] = []
    for bucket_name, template in sorted(_FORM_FILL_CASE_DESIGN_GROUPS.items()):
        bucket = buckets_by_name[bucket_name]
        candidate_cases = _sanitize_public_value(template["candidate_cases"])
        guidance.append(
            {
                "guidance_id": template["policy_guidance_id"],
                "source_bucket": bucket_name,
                "guidance": template["policy_guidance"],
                "review_rationale": template["review_rationale"],
            }
        )
        case_groups.append(
            {
                "case_group_id": template["case_group_id"],
                "source_bucket": bucket_name,
                "source_bucket_field_count": int(bucket.get("residual_field_count", 0)),
                "source_bucket_row_count": int(bucket.get("residual_row_count", 0)),
                "source_field_paths": _sanitize_public_value(bucket.get("by_field_path", {})),
                "source_representative_row_refs": _sanitize_public_value(bucket.get("residual_row_refs", []))[:8],
                "case_purpose": template["review_rationale"],
                "policy_guidance_id": template["policy_guidance_id"],
                "candidate_cases": candidate_cases,
                "candidate_case_count": len(candidate_cases),
                "recommended_split_role": "candidate_dataset_design_only",
                "materialization_requires_user_review": True,
                "public_sample_materialized": False,
            }
        )

    bucket_field_counts = summary.get("bucket_field_counts", {})
    return {
        "evidence_kind": "form_fill_remediation_case_design",
        "design_status": "design_only_not_materialized",
        "source_remediation_plan": {
            "evidence_kind": _sanitize_public_summary(str(remediation_plan.get("evidence_kind", "unknown"))),
            "remediation_status": _sanitize_public_summary(str(remediation_plan.get("remediation_status", "unknown"))),
            "plan_artifact": "reports/public-sample/form-fill-remediation-plan/form_fill_remediation_plan.json",
            "summary": _sanitize_public_value(summary),
        },
        "summary": {
            "target": "form_fill",
            "target_task_family": _FORM_FILL_TASK_FAMILY,
            "source_residual_row_count": int(summary.get("residual_row_count", 0)),
            "source_residual_field_count": int(summary.get("residual_field_count", 0)),
            "case_group_count": len(case_groups),
            "candidate_case_count": sum(group["candidate_case_count"] for group in case_groups),
            "covered_bucket_field_counts": _sanitize_public_value(bucket_field_counts),
            "covered_bucket_row_counts": _sanitize_public_value(summary.get("bucket_row_counts", {})),
            "source_count_consistency": _sanitize_public_value(summary.get("count_consistency", {})),
            "public_sample_modified": False,
            "new_data_generated": False,
            "recommended_next_step": "review_then_materialize_independent_candidate_dataset_in_later_change",
        },
        "policy_guidance": guidance,
        "case_groups": case_groups,
        "acceptance_boundary": {
            "must_preserve_strict_contract_exact_match_as_primary": True,
            "must_preserve_strict_slot_f1_as_primary": True,
            "slot_f1_soft_diagnostic_only": True,
            "case_design_does_not_authorize_materialization": True,
            "materialization_requires_later_user_confirmed_phase": True,
            "future_training_requires_separate_user_confirmed_phase": True,
        },
        "execution_scope": {
            "source_remediation_plan_read_as_input": True,
            "raw_predictions_read": False,
            "new_data_generated": False,
            "seed_traces_modified": False,
            "public_sample_modified": False,
            "public_heldout_modified": False,
            "gold_policy_change": False,
            "training_run": False,
            "dpo_run": False,
            "prediction_run": False,
            "a100_job": False,
            "evaluator_metric_change": False,
            "slot_normalization": False,
            "prediction_repair_or_replacement": False,
        },
        "claims": {
            "design_only": True,
            "model_recovery_claim": False,
            "held_out_recovery_claim": False,
            "production_readiness_claim": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
            "adapter_release_claim": False,
            "checkpoint_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
    }


def _unique_public_values(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


_SLOT_VALUE_CASE_GROUP_IDS = {
    ("seed-clarify-ambiguous", "slot_value_canonical_phrase_drift"): (
        "clarify-ambiguous-slot-value-canonical-phrase"
    ),
    ("seed-form-email", "slot_value_language_variant"): "form-email-slot-value-language-variant",
    ("seed-open-example", "normalized_command_paraphrase_drift"): "navigate-open-url-normalized-command-paraphrase",
    ("seed-block-purchase", "normalized_command_paraphrase_drift"): (
        "blocked-payment-normalized-command-paraphrase"
    ),
}


_SLOT_VALUE_CASE_PURPOSES = {
    "clarify-ambiguous-slot-value-canonical-phrase": (
        "teach the canonical ambiguity scope phrase without evaluator-side normalization"
    ),
    "form-email-slot-value-language-variant": "teach Chinese canonical slot values instead of English aliases",
    "navigate-open-url-normalized-command-paraphrase": (
        "teach open-url canonical command wording without accepting paraphrase drift"
    ),
    "blocked-payment-normalized-command-paraphrase": (
        "teach blocked-payment canonical command wording without accepting action paraphrase drift"
    ),
}


def design_slot_value_generalization_cases(
    *,
    residual_diagnosis: dict[str, Any],
    residual_manifest: dict[str, Any],
) -> dict[str, Any]:
    residuals = [entry for entry in residual_diagnosis.get("residuals", []) if isinstance(entry, dict)]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for residual in residuals:
        source_family = _sanitize_public_summary(str(residual.get("source_family_id", "unknown")))
        drift_bucket = _sanitize_public_summary(str(residual.get("drift_bucket", "unknown")))
        grouped.setdefault((source_family, drift_bucket), []).append(residual)

    candidate_groups: list[dict[str, Any]] = []
    for key, entries in sorted(grouped.items()):
        source_family, drift_bucket = key
        group_id = _SLOT_VALUE_CASE_GROUP_IDS.get(
            key,
            f"{source_family}-{drift_bucket}".replace("_", "-"),
        )
        field_paths = sorted({_sanitize_public_summary(str(entry.get("field_path", "unknown"))) for entry in entries})
        canonical_values = _unique_public_values(
            [
                {
                    "field_path": _sanitize_public_summary(str(entry.get("field_path", "unknown"))),
                    "value": _sanitize_public_value(entry.get("gold_value")),
                }
                for entry in entries
            ]
        )
        wrong_values = _unique_public_values(
            [
                {
                    "field_path": _sanitize_public_summary(str(entry.get("field_path", "unknown"))),
                    "value": _sanitize_public_value(entry.get("predicted_value")),
                }
                for entry in entries
            ]
        )
        candidate_groups.append(
            {
                "case_group_id": group_id,
                "source_family_id": source_family,
                "residual_bucket": drift_bucket,
                "residual_row_ids": sorted(_sanitize_id(str(entry.get("row_id", ""))) for entry in entries),
                "affected_field_paths": field_paths,
                "canonical_gold_values": canonical_values,
                "observed_wrong_values": wrong_values,
                "case_purpose": _SLOT_VALUE_CASE_PURPOSES.get(
                    group_id,
                    "teach canonical value selection without evaluator-side normalization",
                ),
                "recommended_split_role": "candidate_train_or_validation_design_only",
                "materialization_requires_user_review": True,
                "public_sample_materialized": False,
            }
        )

    covered_bucket_counts = residual_diagnosis.get("summary", {}).get("residual_drift_bucket_counts", {})
    return {
        "evidence_kind": "slot_value_generalization_case_design",
        "design_status": "design_only_not_materialized",
        "source_residual_diagnosis": {
            "evidence_kind": _sanitize_public_summary(str(residual_diagnosis.get("evidence_kind", "unknown"))),
            "summary": _sanitize_public_value(residual_diagnosis.get("summary", {})),
        },
        "source_residual_manifest": {
            "evidence_kind": _sanitize_public_summary(str(residual_manifest.get("evidence_kind", "unknown"))),
            "summary": _sanitize_public_value(residual_manifest.get("summary", {})),
        },
        "summary": {
            "candidate_group_count": len(candidate_groups),
            "covered_residual_bucket_counts": _sanitize_public_value(covered_bucket_counts),
            "public_sample_modified": False,
            "new_data_generated": False,
            "recommended_next_step": "materialize_reviewed_cases_in_later_openspec_change",
        },
        "candidate_case_groups": candidate_groups,
        "execution_scope": {
            "local_public_sample_only": True,
            "new_data_generated": False,
            "public_sample_modified": False,
            "training_run": False,
            "prediction_run": False,
            "dpo_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
            "prediction_repair_or_replacement": False,
        },
        "claims": {
            "design_only": True,
            "model_recovery_claim": False,
            "held_out_generalization_recovered": False,
            "private_corpus_generalization_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
            "prediction_repair_or_replacement": False,
            "semantic_equivalence_primary_metric": False,
            "soft_slot_f1_primary_metric": False,
            "evaluator_relaxation": False,
        },
    }


def diagnose_heldout_family_strategy(
    *,
    load_rows_path: Path,
    manifest_path: Path,
    tiny_overfit_manifest: dict[str, Any],
    heldout_manifest: dict[str, Any],
    heldout_alignment_by_split: dict[str, dict[str, Any]],
    heldout_schema_by_split: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = load_sft_rows(load_rows_path)
    manifest = read_json(manifest_path)
    row_by_id = {row.id: row for row in rows}
    family_summary = _family_row_summary(rows)
    train_rows = [row for row in rows if row.split == "train"]
    train_contract_families = _family_row_summary(train_rows)

    tiny_row_ids = [
        _sanitize_id(str(row_id))
        for row_id in tiny_overfit_manifest.get("training_row_ids", [])
        if isinstance(row_id, str)
    ]
    tiny_rows = [row_by_id[row_id] for row_id in tiny_row_ids if row_id in row_by_id]
    tiny_families = _family_row_summary(tiny_rows)
    tiny_contract_family_counts = _count_by(
        [_contract_family_key(as_contract(row.target_contract)) for row in tiny_rows]
    )
    heldout_splits = [split for split in ("dev", "test") if split in heldout_manifest.get("split_results", {})]
    residual_entries: list[dict[str, Any]] = []

    for split in heldout_splits:
        split_rows = [row for row in rows if row.split == split]
        split_schema = heldout_schema_by_split.get(split, {})
        schema_rows_raw = split_schema.get("rows") if isinstance(split_schema, dict) else []
        schema_rows = schema_rows_raw if isinstance(schema_rows_raw, list) else []
        schema_invalid_row_ids = {
            _sanitize_id(str(row.get("row_id", "")))
            for row in schema_rows
            if isinstance(row, dict) and row.get("issues")
        }
        for source_family, source_entry in _family_row_summary(split_rows).items():
            contract_family_key = str(source_entry["contract_family_key"])
            family_row_ids = set(source_entry["row_ids"])
            train_analogs = [
                entry
                for entry in train_contract_families.values()
                if entry["contract_family_key"] == contract_family_key
            ]
            train_analog_row_count = sum(int(entry["row_count"]) for entry in train_analogs)
            tiny_subset_row_count = tiny_contract_family_counts.get(contract_family_key, 0)
            heldout_result = heldout_manifest["split_results"][split]
            field_counts = _field_mismatch_counts_for_family(
                heldout_alignment_by_split.get(split, {}),
                family_row_ids,
            )
            residual_entries.append(
                {
                    "source_family_id": source_family,
                    "split": split,
                    "contract_family_key": contract_family_key,
                    "task_type": source_entry["task_type"],
                    "route": source_entry["route"],
                    "row_count": int(source_entry["row_count"]),
                    "row_ids": list(source_entry["row_ids"]),
                    "train_analog_family_id": str(train_analogs[0]["source_family_id"]) if train_analogs else None,
                    "train_analog_row_count": train_analog_row_count,
                    "tiny_subset_row_count": tiny_subset_row_count,
                    "contract_exact_match": heldout_result.get("contract_exact_match"),
                    "schema_invalid_prediction_count": len(family_row_ids & schema_invalid_row_ids),
                    "field_mismatch_counts": field_counts,
                    "dpo_hard_negative_category": _DPO_CATEGORY_BY_CONTRACT_FAMILY.get(contract_family_key),
                    "strategy_bucket": "targeted_sft_family_coverage"
                    if train_analog_row_count > 0 and tiny_subset_row_count == 0
                    else "inspect_data_or_objective_gap",
                }
            )

    heldout_exact = {
        split: float(heldout_manifest["split_results"][split].get("contract_exact_match", 0.0))
        for split in heldout_splits
    }
    absent_from_tiny = sorted(
        {
            entry["contract_family_key"]
            for entry in residual_entries
            if int(entry["tiny_subset_row_count"]) == 0
        }
    )
    analog_covered = sorted(
        {
            entry["contract_family_key"]
            for entry in residual_entries
            if int(entry["train_analog_row_count"]) > 0
        }
    )
    dpo_categories = sorted(
        {
            str(entry["dpo_hard_negative_category"])
            for entry in residual_entries
            if entry.get("dpo_hard_negative_category")
        }
    )
    return {
        "evidence_kind": "heldout_family_strategy_diagnosis",
        "diagnostic_mode": "local_public_safe_no_training_no_generation",
        "source_manifest": {
            "manifest_id": _sanitize_public_summary(str(manifest.get("manifest_id", "unknown"))),
            "counts": _sanitize_public_value(manifest.get("counts", {})),
            "split_counts": _sanitize_public_value(manifest.get("split_counts", {})),
        },
        "summary": {
            "heldout_contract_exact_match": heldout_exact,
            "heldout_strict_exact_match_failed": bool(heldout_exact)
            and all(value == 0.0 for value in heldout_exact.values()),
            "tiny_training_subset_family_count": len(tiny_families),
            "heldout_residual_family_count": len(residual_entries),
            "heldout_contract_families_absent_from_tiny_subset": absent_from_tiny,
            "heldout_contract_families_with_train_analog_coverage": analog_covered,
            "broad_data_scaling_recommended": False,
            "recommended_next_step": "propose_targeted_family_coverage_probe",
        },
        "coverage_by_split": _coverage_by_split(rows),
        "source_family_coverage": family_summary,
        "tiny_training_subset": {
            "row_count": len(tiny_rows),
            "row_ids": tiny_row_ids,
            "source_family_counts": _count_by([_source_family_id(row) for row in tiny_rows]),
            "contract_family_counts": tiny_contract_family_counts,
        },
        "heldout_family_residuals": residual_entries,
        "dpo_hard_negative_signal": {
            "categories_available_for_residual_families": dpo_categories,
            "category_count": len(dpo_categories),
            "execute_dpo_in_this_phase": False,
        },
        "strategy_recommendation": {
            "primary": "targeted_family_coverage_probe_before_broad_scaling",
            "requires_user_confirmation": True,
            "rationale": [
                "heldout strict exact match is zero on current dev/test",
                "all heldout contract families have train analog coverage in the dataset",
                "the current tiny adapter subset trained only one search-family source",
                "therefore the next falsifiable step should test targeted family coverage before broad data scaling",
            ],
            "candidate_next_phases": [
                "propose_targeted_sft_family_coverage_probe",
                "validate_residual_family_dpo_hard_negatives",
                "inspect_prompt_policy_only_if_targeted_coverage_still_fails",
            ],
        },
        "execution_scope": {
            "local_public_sample_only": True,
            "new_data_generated": False,
            "training_run": False,
            "dpo_run": False,
            "a100_execution": False,
            "prediction_run": False,
            "evaluator_metric_change": False,
        },
        "claims": {
            "diagnosis_only": True,
            "model_recovery_claim": False,
            "held_out_generalization_claim": False,
            "private_corpus_generalization_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
            "prediction_repair_or_replacement": False,
            "semantic_equivalence_primary_metric": False,
        },
    }


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
