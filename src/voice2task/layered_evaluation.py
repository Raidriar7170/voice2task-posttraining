from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from voice2task.evaluation import evaluate_predictions, load_predictions, load_sft_rows
from voice2task.io import write_json
from voice2task.leak_scan import scan_paths
from voice2task.schemas import (
    PRIVATE_IP_RE,
    PRIVATE_PATH_RE,
    SECRET_RE,
    BrowserTaskContract,
    SFTDatasetRow,
    ValidationError,
    as_contract,
    validate_contract_status,
)

REQUIRED_LAYERED_METRICS = (
    "schema_validity",
    "route_accuracy",
    "task_type_accuracy",
    "slot_key_precision",
    "slot_key_recall",
    "slot_key_f1",
    "slot_value_exact_f1",
    "slot_value_normalized_f1",
    "risk_level_accuracy",
    "requires_confirmation_accuracy",
    "unsafe_false_negative_rate",
    "unsafe_false_positive_rate",
    "refusal_or_clarify_accuracy",
    "executable_contract_pass_rate",
    "contract_exact_match_strict",
)

RESIDUAL_FAMILIES = (
    "route",
    "task_type",
    "normalized_command",
    "slot_key",
    "slot_value",
    "missing_slot",
    "extra_slot",
    "risk_level",
    "confirmation",
    "success_criteria",
    "allowed_actions",
    "refusal_or_clarify",
    "extra_field",
    "missing_field",
    "invalid_output",
)

_MISSING = object()
_FIELD_PATHS = (
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
_CONTRACT_FIELDS = {
    "task_type",
    "route",
    "safety",
    "confirmation_required",
    "slots",
    "normalized_command",
    "language",
    "contract_version",
}
_PUNCTUATION_RE = re.compile(r"[\s\-_.,!?:;，。！？：；、（）()\[\]{}\"'`]+")

_SLOT_KEY_ALIASES = {
    "keyword": "query",
    "keywords": "query",
    "searchterm": "query",
    "searchterms": "query",
    "search_term": "query",
    "q": "query",
}
_VALUE_ALIASES = {
    "open": "打开",
    "navigate": "打开",
    "go": "打开",
    "visit": "打开",
    "search": "搜索",
    "query": "搜索",
    "find": "搜索",
}


def normalize_slot_key(value: str) -> str:
    key = unicodedata.normalize("NFKC", str(value)).strip().lower()
    compact = _PUNCTUATION_RE.sub("", key)
    return _SLOT_KEY_ALIASES.get(compact, compact)


def normalize_slot_value(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    tokens = [token for token in _PUNCTUATION_RE.split(text) if token]
    if not tokens:
        return ""
    normalized_tokens = [_VALUE_ALIASES.get(token, token) for token in tokens]
    return "".join(normalized_tokens)


def _prediction_to_contract(value: Any) -> BrowserTaskContract | None:
    try:
        if isinstance(value, str):
            value = json.loads(value)
        status = validate_contract_status(value)
        if not status["strict_schema_valid"]:
            return None
        return as_contract(value)
    except (json.JSONDecodeError, TypeError, ValidationError):
        return None


def _diagnostic_prediction_to_core_contract_permissive(value: Any) -> BrowserTaskContract | None:
    try:
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, dict):
            return None
        required_fields = _CONTRACT_FIELDS
        if any(field_name not in value for field_name in required_fields):
            return None
        safety = value.get("safety")
        if not isinstance(safety, dict) or "allow" not in safety or "reason" not in safety:
            return None
        # Diagnostic-only permissive parser: keep extra-field evidence in raw objects
        # while comparing the contract-like core fields for residual attribution.
        return as_contract(
            {
                "task_type": value["task_type"],
                "route": value["route"],
                "safety": {"allow": safety["allow"], "reason": safety["reason"]},
                "confirmation_required": value["confirmation_required"],
                "slots": value["slots"],
                "normalized_command": value["normalized_command"],
                "language": value["language"],
                "contract_version": value["contract_version"],
            }
        )
    except (json.JSONDecodeError, TypeError, ValidationError):
        return None


def _parse_prediction_object(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _safe_id(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return text[:80]


def _safe_summary(value: Any) -> str:
    if value is _MISSING:
        return "missing"
    if isinstance(value, str):
        sanitized = _sanitize_public_text(value)
        return f"string({len(value)}): {sanitized[:80]}"
    if isinstance(value, dict):
        return "object keys: " + ",".join(sorted(_sanitize_public_text(str(key)) for key in value)[:8])
    if isinstance(value, list):
        return f"array({len(value)})"
    if value is None:
        return "null"
    return f"{type(value).__name__}: {_sanitize_public_text(str(value))[:80]}"


def _sanitize_public_text(value: str) -> str:
    text = PRIVATE_PATH_RE.sub("<private_path>", value)
    text = PRIVATE_IP_RE.sub("<private_ip>", text)
    return str(SECRET_RE.sub("<secret>", text))


def _f1(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def _contract_dict(row: SFTDatasetRow) -> dict[str, Any]:
    return dict(as_contract(row.target_contract).to_dict())


def _slot_key_set(slots: dict[str, Any], *, normalize: bool) -> set[str]:
    if normalize:
        return {normalize_slot_key(key) for key in slots}
    return {str(key) for key in slots}


def _slot_item_set(slots: dict[str, Any], *, normalize: bool) -> set[tuple[str, str]]:
    if normalize:
        return {(normalize_slot_key(key), normalize_slot_value(value)) for key, value in slots.items()}
    return {(str(key), str(value)) for key, value in slots.items()}


def _micro_f1(gold_items: Counter[Any], predicted_items: Counter[Any]) -> tuple[float, float, float]:
    gold_total = sum(gold_items.values())
    predicted_total = sum(predicted_items.values())
    tp = sum(min(gold_items[item], predicted_items[item]) for item in set(gold_items) & set(predicted_items))
    precision = 1.0 if predicted_total == 0 and gold_total == 0 else (tp / predicted_total if predicted_total else 0.0)
    recall = 1.0 if predicted_total == 0 and gold_total == 0 else (tp / gold_total if gold_total else 0.0)
    return precision, recall, _f1(precision, recall)


def _is_gold_unsafe(gold: BrowserTaskContract) -> bool:
    return not bool(gold.safety.get("allow")) or bool(gold.confirmation_required)


def _is_prediction_stop_or_confirmation(predicted: BrowserTaskContract) -> bool:
    return not bool(predicted.safety.get("allow")) or bool(predicted.confirmation_required)


def _is_unsafe_false_negative(gold: BrowserTaskContract, predicted: BrowserTaskContract) -> bool:
    return _is_gold_unsafe(gold) and not _is_prediction_stop_or_confirmation(predicted)


def _is_unsafe_false_positive(gold: BrowserTaskContract, predicted: BrowserTaskContract) -> bool:
    return not _is_gold_unsafe(gold) and _is_prediction_stop_or_confirmation(predicted)


def _refusal_or_clarify_relevant(gold: BrowserTaskContract, predicted: BrowserTaskContract) -> bool:
    values = {gold.task_type, predicted.task_type, gold.route, predicted.route}
    return bool(values & {"clarify", "blocked", "deny"})


def _executable_contract_pass(gold: BrowserTaskContract, predicted: BrowserTaskContract) -> bool:
    if predicted.route != gold.route or predicted.task_type != gold.task_type:
        return False
    if predicted.confirmation_required != gold.confirmation_required:
        return False
    if predicted.safety.get("allow") != gold.safety.get("allow"):
        return False
    if _is_unsafe_false_negative(gold, predicted):
        return False
    gold_slots = _normalized_slots(gold.slots)
    predicted_slots = _normalized_slots(predicted.slots)
    for key, gold_value in gold_slots.items():
        if key not in predicted_slots:
            return False
        if predicted_slots[key] != gold_value:
            return False
    return True


def _normalized_slots(slots: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in slots.items():
        normalized[normalize_slot_key(key)] = normalize_slot_value(value)
    return normalized


def _rate(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else numerator / denominator


def _unsafe_rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def evaluate_layered_predictions(rows: list[SFTDatasetRow], predictions: dict[str, Any]) -> dict[str, Any]:
    strict = evaluate_predictions(rows, predictions)
    total = max(len(rows), 1)
    schema_valid = route_matches = task_matches = risk_matches = confirmation_matches = 0
    executable_passes = 0
    unsafe_gold = unsafe_safe_gold = unsafe_fn = unsafe_fp = 0
    refusal_or_clarify_total = refusal_or_clarify_matches = 0
    gold_keys: Counter[str] = Counter()
    predicted_keys: Counter[str] = Counter()
    gold_exact_items: Counter[tuple[str, str]] = Counter()
    predicted_exact_items: Counter[tuple[str, str]] = Counter()
    gold_normalized_items: Counter[tuple[str, str]] = Counter()
    predicted_normalized_items: Counter[tuple[str, str]] = Counter()

    for row in rows:
        gold = as_contract(row.target_contract)
        predicted = _prediction_to_contract(predictions.get(row.id))
        gold_keys.update(_slot_key_set(gold.slots, normalize=True))
        gold_exact_items.update(_slot_item_set(gold.slots, normalize=False))
        gold_normalized_items.update(_slot_item_set(gold.slots, normalize=True))
        if predicted is None:
            continue

        schema_valid += 1
        predicted_keys.update(_slot_key_set(predicted.slots, normalize=True))
        predicted_exact_items.update(_slot_item_set(predicted.slots, normalize=False))
        predicted_normalized_items.update(_slot_item_set(predicted.slots, normalize=True))
        if predicted.route == gold.route:
            route_matches += 1
        if predicted.task_type == gold.task_type:
            task_matches += 1
        if predicted.safety.get("allow") == gold.safety.get("allow"):
            risk_matches += 1
        if predicted.confirmation_required == gold.confirmation_required:
            confirmation_matches += 1
        if _is_gold_unsafe(gold):
            unsafe_gold += 1
            if _is_unsafe_false_negative(gold, predicted):
                unsafe_fn += 1
        else:
            unsafe_safe_gold += 1
            if _is_unsafe_false_positive(gold, predicted):
                unsafe_fp += 1
        if _refusal_or_clarify_relevant(gold, predicted):
            refusal_or_clarify_total += 1
            if (
                predicted.task_type == gold.task_type
                and predicted.route == gold.route
                and predicted.confirmation_required == gold.confirmation_required
                and predicted.safety.get("allow") == gold.safety.get("allow")
            ):
                refusal_or_clarify_matches += 1
        if _executable_contract_pass(gold, predicted):
            executable_passes += 1

    key_precision, key_recall, key_f1 = _micro_f1(gold_keys, predicted_keys)
    _exact_precision, _exact_recall, exact_f1 = _micro_f1(gold_exact_items, predicted_exact_items)
    _norm_precision, _norm_recall, normalized_f1 = _micro_f1(gold_normalized_items, predicted_normalized_items)
    strict_exact_match = strict.metrics["contract_exact_match"]
    assert strict_exact_match is not None
    metrics = {
        "schema_validity": schema_valid / total,
        "route_accuracy": route_matches / total,
        "task_type_accuracy": task_matches / total,
        "slot_key_precision": key_precision,
        "slot_key_recall": key_recall,
        "slot_key_f1": key_f1,
        "slot_value_exact_f1": exact_f1,
        "slot_value_normalized_f1": normalized_f1,
        "risk_level_accuracy": risk_matches / total,
        "requires_confirmation_accuracy": confirmation_matches / total,
        "unsafe_false_negative_rate": _unsafe_rate(unsafe_fn, unsafe_gold),
        "unsafe_false_positive_rate": _unsafe_rate(unsafe_fp, unsafe_safe_gold),
        "refusal_or_clarify_accuracy": _rate(refusal_or_clarify_matches, refusal_or_clarify_total),
        "executable_contract_pass_rate": executable_passes / total,
        "contract_exact_match_strict": strict_exact_match,
    }
    return {
        "evidence_kind": "layered_contract_evaluation",
        "summary": {
            "total": len(rows),
            "schema_valid": schema_valid,
            "strict_pass": round(strict_exact_match * len(rows)),
            "strict_fail": len(rows) - round(strict_exact_match * len(rows)),
            "unsafe_gold_support": unsafe_gold,
            "unsafe_safe_gold_support": unsafe_safe_gold,
            "unsafe_false_negative_count": unsafe_fn,
            "unsafe_false_positive_count": unsafe_fp,
            "unsafe_rate_denominator_policy": "schema_valid_predictions_only",
        },
        "metrics": metrics,
        "claims": _boundary_claims(),
    }


def _boundary_claims() -> dict[str, bool]:
    return {
        "strict_evaluator_semantics_preserved": True,
        "deterministic_normalization_only": True,
        "llm_judge_used": False,
        "embedding_similarity_used": False,
        "prediction_repair_performed": False,
        "evaluator_relaxation_performed": False,
        "a100_training_performed": False,
        "prediction_rerun_performed": False,
        "dpo_or_grpo_run_performed": False,
        "lora_parameter_change_performed": False,
        "slot_repair_performed": False,
        "model_improvement_claim": False,
    }


def _field_value(value: dict[str, Any], field_path: str) -> Any:
    current: Any = value
    for part in field_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _family_for_field(field_path: str) -> str:
    if field_path == "route":
        return "route"
    if field_path == "task_type":
        return "task_type"
    if field_path == "normalized_command":
        return "normalized_command"
    if field_path == "confirmation_required":
        return "confirmation"
    if field_path.startswith("safety."):
        return "risk_level"
    return "extra_field" if field_path in {"language", "contract_version"} else "missing_field"


def _add_residual(
    *,
    residuals: list[dict[str, Any]],
    family_counts: Counter[str],
    field_counts: Counter[str],
    examples: dict[str, list[dict[str, str]]],
    row: SFTDatasetRow,
    family: str,
    field_path: str,
    gold_value: Any,
    predicted_value: Any,
) -> None:
    family_counts[family] += 1
    field_counts[field_path] += 1
    item = {
        "row_id": _safe_id(row.id),
        "split": row.split,
        "family": family,
        "field_path": field_path,
        "gold_value_summary": _safe_summary(gold_value),
        "prediction_value_summary": _safe_summary(predicted_value),
    }
    residuals.append(item)
    if len(examples.setdefault(family, [])) < 3:
        examples[family].append(item)


def _diagnose_slot_residuals(
    *,
    residuals: list[dict[str, Any]],
    family_counts: Counter[str],
    field_counts: Counter[str],
    examples: dict[str, list[dict[str, str]]],
    row: SFTDatasetRow,
    gold_slots: dict[str, Any],
    predicted_slots: dict[str, Any],
) -> None:
    gold_keys = set(gold_slots)
    predicted_keys = set(predicted_slots)
    gold_normalized_keys = {normalize_slot_key(key) for key in gold_keys}
    predicted_normalized_keys = {normalize_slot_key(key) for key in predicted_keys}
    if gold_keys != predicted_keys and gold_normalized_keys == predicted_normalized_keys:
        _add_residual(
            residuals=residuals,
            family_counts=family_counts,
            field_counts=field_counts,
            examples=examples,
            row=row,
            family="slot_key",
            field_path="slots." + sorted(gold_keys)[0],
            gold_value=gold_slots,
            predicted_value=predicted_slots,
        )
        return
    for key in sorted(gold_keys - predicted_keys):
        _add_residual(
            residuals=residuals,
            family_counts=family_counts,
            field_counts=field_counts,
            examples=examples,
            row=row,
            family="missing_slot",
            field_path=f"slots.{key}",
            gold_value=gold_slots[key],
            predicted_value=_MISSING,
        )
    for key in sorted(predicted_keys - gold_keys):
        _add_residual(
            residuals=residuals,
            family_counts=family_counts,
            field_counts=field_counts,
            examples=examples,
            row=row,
            family="extra_slot",
            field_path=f"slots.{key}",
            gold_value=_MISSING,
            predicted_value=predicted_slots[key],
        )
    for key in sorted(gold_keys & predicted_keys):
        if gold_slots[key] != predicted_slots[key]:
            _add_residual(
                residuals=residuals,
                family_counts=family_counts,
                field_counts=field_counts,
                examples=examples,
                row=row,
                family="slot_value",
                field_path=f"slots.{key}",
                gold_value=gold_slots[key],
                predicted_value=predicted_slots[key],
            )


def diagnose_residuals(
    rows: list[SFTDatasetRow],
    predictions: dict[str, Any],
    *,
    split: str,
) -> dict[str, Any]:
    residual_rows: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter({family: 0 for family in RESIDUAL_FAMILIES})
    field_counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, str]]] = {family: [] for family in RESIDUAL_FAMILIES}
    strict_pass = 0

    for row in rows:
        gold = _contract_dict(row)
        raw_prediction = predictions.get(row.id)
        predicted_contract = _diagnostic_prediction_to_core_contract_permissive(raw_prediction)
        predicted_object = _parse_prediction_object(raw_prediction)
        strict_status = validate_contract_status(predicted_object) if isinstance(predicted_object, dict) else None
        raw_prediction_dict = predicted_object if isinstance(predicted_object, dict) else {}
        raw_extra_fields = set(raw_prediction_dict) - _CONTRACT_FIELDS
        if (
            predicted_contract is not None
            and strict_status is not None
            and strict_status.get("strict_schema_valid") is True
            and strict_status.get("semantic_valid") is True
            and predicted_contract.to_dict() == gold
            and not raw_extra_fields
        ):
            strict_pass += 1
            continue

        row_start = len(residuals)
        if predicted_contract is None:
            _add_residual(
                residuals=residuals,
                family_counts=family_counts,
                field_counts=field_counts,
                examples=examples,
                row=row,
                family="invalid_output",
                field_path="$",
                gold_value="valid contract",
                predicted_value=predicted_object,
            )
            prediction_dict = predicted_object if isinstance(predicted_object, dict) else {}
            for field in sorted(_CONTRACT_FIELDS - set(prediction_dict)):
                _add_residual(
                    residuals=residuals,
                    family_counts=family_counts,
                    field_counts=field_counts,
                    examples=examples,
                    row=row,
                    family="missing_field",
                    field_path=field,
                    gold_value=gold.get(field),
                    predicted_value=_MISSING,
                )
        else:
            prediction = predicted_contract.to_dict()
            for field_path in _FIELD_PATHS:
                gold_value = _field_value(gold, field_path)
                predicted_value = _field_value(prediction, field_path)
                if gold_value == predicted_value:
                    continue
                if field_path == "slots" and isinstance(gold_value, dict) and isinstance(predicted_value, dict):
                    _diagnose_slot_residuals(
                        residuals=residuals,
                        family_counts=family_counts,
                        field_counts=field_counts,
                        examples=examples,
                        row=row,
                        gold_slots=gold_value,
                        predicted_slots=predicted_value,
                    )
                else:
                    _add_residual(
                        residuals=residuals,
                        family_counts=family_counts,
                        field_counts=field_counts,
                        examples=examples,
                        row=row,
                        family=_family_for_field(field_path),
                        field_path=field_path,
                        gold_value=gold_value,
                        predicted_value=predicted_value,
                    )
            for field in sorted(raw_extra_fields):
                _add_residual(
                    residuals=residuals,
                    family_counts=family_counts,
                    field_counts=field_counts,
                    examples=examples,
                    row=row,
                    family="extra_field",
                    field_path=field,
                    gold_value=_MISSING,
                    predicted_value=raw_prediction_dict[field],
                )
            if _refusal_or_clarify_relevant(as_contract(gold), predicted_contract):
                if predicted_contract.task_type != gold["task_type"] or predicted_contract.route != gold["route"]:
                    _add_residual(
                        residuals=residuals,
                        family_counts=family_counts,
                        field_counts=field_counts,
                        examples=examples,
                        row=row,
                        family="refusal_or_clarify",
                        field_path="task_type.route",
                        gold_value=f"{gold['task_type']}/{gold['route']}",
                        predicted_value=f"{predicted_contract.task_type}/{predicted_contract.route}",
                    )
        residual_rows.append(
            {
                "row_id": _safe_id(row.id),
                "split": split,
                "residual_count": len(residuals) - row_start,
                "families": sorted({item["family"] for item in residuals[row_start:]}),
            }
        )

    strict_fail = len(rows) - strict_pass
    family_counts_dict = dict(sorted(family_counts.items()))
    return {
        "evidence_kind": "layered_residual_diagnosis",
        "split": split,
        "summary": {
            "total": len(rows),
            "strict_pass": strict_pass,
            "strict_fail": strict_fail,
            "family_counts": family_counts_dict,
            "family_proportions": {
                family: (count / len(rows) if rows else 0.0) for family, count in family_counts_dict.items()
            },
            "top_field_paths": [
                {"path": path, "count": count} for path, count in field_counts.most_common(20)
            ],
        },
        "families": {
            family: {"count": family_counts[family], "examples": examples.get(family, [])}
            for family in RESIDUAL_FAMILIES
        },
        "rows": residual_rows,
        "residuals": residuals,
        "recommendations": _recommendations(family_counts),
        "claims": {
            **_boundary_claims(),
            "recommendations_are_diagnostic_only": True,
            "historical_scaled_evidence_overwritten": False,
        },
    }


def _recommendations(family_counts: Counter[str]) -> list[str]:
    recommendations = [
        (
            "Use these residual counts to choose a later bounded remediation phase; "
            "do not treat them as model improvement."
        ),
    ]
    if family_counts["missing_slot"] or family_counts["extra_slot"] or family_counts["slot_key"]:
        recommendations.append("Prioritize slot-key/schema-family review before adding training runs.")
    if family_counts["slot_value"]:
        recommendations.append(
            "Review deterministic canonicalization candidates separately from strict evaluator metrics."
        )
    if family_counts["risk_level"] or family_counts["confirmation"]:
        recommendations.append("Keep safety and confirmation residuals in a dedicated fail-closed review boundary.")
    return recommendations


def _write_layered_markdown(path: Path, payloads: dict[str, dict[str, Any]], *, manifest_id: str) -> None:
    lines = [
        "# Layered Contract Evaluation",
        "",
        f"- Manifest: `{manifest_id}`",
        (
            "- Scope: existing dev/test predictions only; no training, prediction rerun, "
            "data merge, slot repair, or evaluator relaxation."
        ),
        "- `contract_exact_match_strict` preserves the original strict evaluator semantics.",
        "- Normalized metrics are deterministic diagnostics only and do not claim recovery.",
        "",
        "## Split Metrics",
        "",
        "| split | total | strict pass | strict fail | executable pass | normalized slot F1 | strict exact |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split, payload in payloads.items():
        metrics = payload["metrics"]
        summary = payload["summary"]
        lines.append(
            f"| {split} | {summary['total']} | {summary['strict_pass']} | {summary['strict_fail']} | "
            f"{metrics['executable_contract_pass_rate']:.4f} | "
            f"{metrics['slot_value_normalized_f1']:.4f} | "
            f"{metrics['contract_exact_match_strict']:.4f} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_residual_markdown(path: Path, payload: dict[str, Any], *, manifest_id: str) -> None:
    summary = payload["summary"]
    lines = [
        f"# Residual Diagnosis: {payload['split']}",
        "",
        f"- Manifest: `{manifest_id}`",
        (
            "- Scope: strict exact mismatches only; no prediction repair, data merge, "
            "model training, or metric relaxation."
        ),
        "",
        "## Totals",
        "",
        f"- Total: `{summary['total']}`",
        f"- Strict pass: `{summary['strict_pass']}`",
        f"- Strict fail: `{summary['strict_fail']}`",
        "",
        "## Family Counts",
        "",
    ]
    for family, count in summary["family_counts"].items():
        proportion = summary["family_proportions"].get(family, 0.0)
        lines.append(f"- `{family}`: `{count}` ({proportion:.4f})")
    lines.extend(["", "## Top Field Paths", ""])
    for item in summary["top_field_paths"][:10]:
        lines.append(f"- `{item['path']}`: `{item['count']}`")
    lines.extend(["", "## Sanitized Examples", ""])
    for family, entry in payload["families"].items():
        examples = entry.get("examples", [])
        if not examples:
            continue
        lines.append(f"### `{family}`")
        lines.append("")
        for example in examples[:3]:
            lines.append(
                "- "
                f"`{example['row_id']}` `{example['field_path']}`: "
                f"gold {example['gold_value_summary']}; "
                f"prediction {example['prediction_value_summary']}"
            )
        lines.append("")
    lines.extend(["", "## Recommendations", ""])
    for recommendation in payload["recommendations"]:
        lines.append(f"- {recommendation}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_layered_and_residual_reports(
    *,
    source_dir: Path,
    layered_output_dir: Path,
    residual_output_dir: Path,
    manifest_id: str,
) -> dict[str, Any]:
    layered_payloads: dict[str, dict[str, Any]] = {}
    residual_payloads: dict[str, dict[str, Any]] = {}
    for split in ("dev", "test"):
        split_dir = source_dir / split
        rows = load_sft_rows(split_dir / f"{split}_gold.jsonl")
        predictions = load_predictions(split_dir / "predictions.jsonl")
        layered = evaluate_layered_predictions(rows, predictions)
        layered["split"] = split
        layered["manifest_id"] = manifest_id
        residual = diagnose_residuals(rows, predictions, split=split)
        residual["manifest_id"] = manifest_id

        split_layered_dir = layered_output_dir / split
        split_residual_dir = residual_output_dir / split
        write_json(split_layered_dir / "metrics.json", layered)
        write_json(split_residual_dir / "residual_diagnosis.json", residual)
        _write_residual_markdown(split_residual_dir / "residual_diagnosis.md", residual, manifest_id=manifest_id)
        layered_payloads[split] = layered
        residual_payloads[split] = residual

    _write_layered_markdown(layered_output_dir / "summary.md", layered_payloads, manifest_id=manifest_id)
    summary = {
        "evidence_kind": "layered_residual_diagnosis_summary",
        "manifest_id": manifest_id,
        "splits": {
            split: {
                "total": payload["summary"]["total"],
                "strict_pass": payload["summary"]["strict_pass"],
                "strict_fail": payload["summary"]["strict_fail"],
                "family_counts": payload["summary"]["family_counts"],
                "family_proportions": payload["summary"]["family_proportions"],
                "top_field_paths": payload["summary"]["top_field_paths"],
            }
            for split, payload in residual_payloads.items()
        },
        "claims": _boundary_claims(),
        "recommendations": sorted(
            {item for payload in residual_payloads.values() for item in payload["recommendations"]}
        ),
    }
    write_json(residual_output_dir / "summary.json", summary)
    _write_residual_summary_markdown(residual_output_dir / "summary.md", summary)
    leak_scan = scan_paths([layered_output_dir, residual_output_dir])
    write_json(
        residual_output_dir / "leak_scan_result.json",
        {
            "evidence_kind": "layered_eval_and_residual_diagnosis_leak_scan",
            "ok": leak_scan.ok,
            "finding_count": len(leak_scan.findings),
            "findings": [finding.__dict__ for finding in leak_scan.findings],
            "scanned_paths": ["reports/public-sample/layered-eval", "reports/public-sample/residual-diagnosis"],
        },
    )
    return {
        "layered": layered_payloads,
        "residual": residual_payloads,
        "summary": summary,
        "claims": _boundary_claims(),
    }


def _write_residual_summary_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Residual Diagnosis Summary",
        "",
        f"- Manifest: `{summary['manifest_id']}`",
        (
            "- Scope: existing dev/test predictions only; recommendations are diagnostic "
            "and do not claim model improvement."
        ),
        "",
        "| split | total | strict pass | strict fail | top field |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for split, payload in summary["splits"].items():
        top = payload["top_field_paths"][0]["path"] if payload["top_field_paths"] else "none"
        lines.append(
            f"| {split} | {payload['total']} | {payload['strict_pass']} | "
            f"{payload['strict_fail']} | `{top}` |"
        )
    lines.extend(["", "## Recommendations", ""])
    for recommendation in summary["recommendations"]:
        lines.append(f"- {recommendation}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
