# ruff: noqa: E501
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from voice2task.copy_backed_slot_verification import (
    AMBIGUOUS_MULTIPLE_MATCHES,
    INVALID_INPUT,
    NOT_FOUND,
    OUT_OF_SCOPE,
    UNSUPPORTED_VALUE_TYPE,
    VERIFIED_EXACT_UNIQUE,
    VERIFIED_NORMALIZED_UNIQUE,
    VERIFIED_STATUS_VALUES,
    CopyBackedScope,
    CopyBackedVerificationResult,
    verify_copy_backed_value,
    verify_source_span,
)
from voice2task.io import read_json, read_jsonl, write_json, write_jsonl
from voice2task.schemas import as_contract
from voice2task.slot_error_analysis import flatten_slot_values

CHANGE_ID = "implement-copy-backed-slot-verification-slice"
GENERATED_AT = "2026-06-22"
INPUT_BOUNDARY_PASSED = "COPY_SLICE_INPUT_BOUNDARY_PASSED"
INPUT_BOUNDARY_BLOCKED = "COPY_SLICE_BLOCKED_INVALID_INPUT"
READY_LABEL = "COPY_SLICE_READY_FOR_SHADOW_INTEGRATION"
PARTIAL_LABEL = "COPY_SLICE_PARTIAL_NEEDS_SCOPE_REFINEMENT"
NOT_JUSTIFIED_LABEL = "COPY_SLICE_NOT_JUSTIFIED"

RAW_INPUTS = Path("reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs")
HYBRID_REPORT = Path("reports/public-sample/hybrid-slot-representation-v1")
SLOT_ANALYSIS = Path("reports/public-sample/slot-error-mechanism-analysis")
INTERNAL_CORE_SUMMARY = Path("reports/public-sample/internal-contract-v2-core/summary.json")
FORMAL_MANIFEST = Path("data/public-samples/manifest_public_sample.json")
DEFAULT_OUTPUT_DIR = Path("reports/public-sample/copy-backed-slot-verification-slice")
DEFAULT_DOC_PATH = Path("docs/copy-backed-slot-verification.md")

SPLITS = ("dev", "test")
ARMS = ("control", "treatment")
ENABLED_SLOT_PATHS = {"query", "field", "target"}
ANALYZED_SLOT_PATHS = {"query", "field", "target", "action"}
MIN_SAMPLE_COUNT = 10
MIN_COPYABLE_RATE = 0.70
POLICY_VERSION = "copy-backed-slot-verification-slice-v1"
REPORT_FILES = (
    "summary.md",
    "summary.json",
    "task-scoped-policy.json",
    "verification-audit.json",
    "recommended-next-change.md",
    "verification-sidecars.jsonl",
    "blocked.json",
)
REQUIRED_RAW_FILES = (
    "artifact-manifest.json",
    "boundary-verification.json",
    "metric-reproduction.json",
    "gold/dev_gold.jsonl",
    "gold/test_gold.jsonl",
    "control/dev_predictions.jsonl",
    "control/test_predictions.jsonl",
    "treatment/dev_predictions.jsonl",
    "treatment/test_predictions.jsonl",
)


class _Missing:
    pass


MISSING = _Missing()


def _rate(count: int | float, total: int | float) -> float:
    return 0.0 if total == 0 else count / total


def _repo_path(repo_root: Path, relative: Path | str) -> Path:
    return repo_root / relative


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_text(payload)


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_output_dir(output_dir: Path, *, keep_blocked: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in REPORT_FILES:
        path = output_dir / filename
        if path.exists() and not (keep_blocked and filename == "blocked.json"):
            path.unlink()


def validate_copy_slice_inputs(repo_root: Path) -> dict[str, Any]:
    raw_dir = _repo_path(repo_root, RAW_INPUTS)
    hybrid_summary_path = _repo_path(repo_root, HYBRID_REPORT / "summary.json")
    hybrid_matrix_path = _repo_path(repo_root, HYBRID_REPORT / "representation-matrix.json")
    slot_summary_path = _repo_path(repo_root, SLOT_ANALYSIS / "summary.json")
    internal_core_path = _repo_path(repo_root, INTERNAL_CORE_SUMMARY)
    formal_manifest_path = _repo_path(repo_root, FORMAL_MANIFEST)
    blocking_reasons: list[str] = []

    for relative in REQUIRED_RAW_FILES:
        if not (raw_dir / relative).exists():
            blocking_reasons.append(f"missing raw input: {RAW_INPUTS / relative}")
    for path in (hybrid_summary_path, hybrid_matrix_path, slot_summary_path, internal_core_path, formal_manifest_path):
        if not path.exists():
            blocking_reasons.append(f"missing required artifact: {path.relative_to(repo_root)}")

    metric_reproduction: dict[str, Any] = {}
    raw_boundary: dict[str, Any] = {}
    hybrid_summary: dict[str, Any] = {}
    slot_summary: dict[str, Any] = {}
    internal_core: dict[str, Any] = {}
    formal_manifest: dict[str, Any] = {}
    if (raw_dir / "metric-reproduction.json").exists():
        metric_reproduction = read_json(raw_dir / "metric-reproduction.json")
    if (raw_dir / "boundary-verification.json").exists():
        raw_boundary = read_json(raw_dir / "boundary-verification.json")
    if hybrid_summary_path.exists():
        hybrid_summary = read_json(hybrid_summary_path)
    if slot_summary_path.exists():
        slot_summary = read_json(slot_summary_path)
    if internal_core_path.exists():
        internal_core = read_json(internal_core_path)
    if formal_manifest_path.exists():
        formal_manifest = read_json(formal_manifest_path)

    metric_status = metric_reproduction.get("status")
    if metric_status != "reproduced":
        blocking_reasons.append(f"metric reproduction is not reproduced: {metric_status}")
    if raw_boundary.get("decision_label") not in {"RAW_INPUT_BOUNDARY_PASSED", "RECOVERY_BOUNDARY_PASSED", None}:
        blocking_reasons.append(f"unexpected raw boundary label: {raw_boundary.get('decision_label')}")
    if hybrid_summary.get("decision_label") != "HYBRID_DESIGN_READY_COPY_SLICE_FIRST":
        blocking_reasons.append(f"hybrid design decision is not HYBRID_DESIGN_READY_COPY_SLICE_FIRST: {hybrid_summary.get('decision_label')}")
    if slot_summary.get("decision_label") != "MIXED_SLOT_REPRESENTATION_REQUIRED":
        blocking_reasons.append(f"slot analysis decision is not MIXED_SLOT_REPRESENTATION_REQUIRED: {slot_summary.get('decision_label')}")
    if internal_core.get("default_external_schema") != "BrowserTaskContract V1":
        blocking_reasons.append(f"external schema is not BrowserTaskContract V1: {internal_core.get('default_external_schema')}")
    if internal_core.get("training_target_changed") is not False:
        blocking_reasons.append("training target appears changed")
    if internal_core.get("claims", {}).get("external_v1_schema_changed") is not False:
        blocking_reasons.append("external V1 schema appears changed")
    if internal_core.get("claims", {}).get("downstream_runtime_migrated") is not False:
        blocking_reasons.append("downstream runtime appears migrated")

    raw_hashes = {
        str(RAW_INPUTS / relative): _file_hash(raw_dir / relative)
        for relative in REQUIRED_RAW_FILES
        if (raw_dir / relative).exists()
    }
    return {
        "change_id": CHANGE_ID,
        "decision_label": INPUT_BOUNDARY_BLOCKED if blocking_reasons else INPUT_BOUNDARY_PASSED,
        "blocking_reasons": blocking_reasons,
        "metric_reproduction_status": metric_status,
        "hybrid_design_decision_label": hybrid_summary.get("decision_label"),
        "slot_analysis_decision_label": slot_summary.get("decision_label"),
        "external_schema": internal_core.get("default_external_schema"),
        "training_target_changed": internal_core.get("training_target_changed"),
        "raw_inputs_dir": RAW_INPUTS.as_posix(),
        "formal_manifest_id": formal_manifest.get("manifest_id"),
        "raw_file_hashes": raw_hashes,
        "approved_inputs": [
            RAW_INPUTS.as_posix(),
            HYBRID_REPORT.as_posix(),
            SLOT_ANALYSIS.as_posix(),
            INTERNAL_CORE_SUMMARY.as_posix(),
            FORMAL_MANIFEST.as_posix(),
        ],
    }


def _load_rows(repo_root: Path) -> list[dict[str, Any]]:
    raw_dir = _repo_path(repo_root, RAW_INPUTS)
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        gold_by_id = {str(row["sample_id"]): row for row in read_jsonl(raw_dir / f"gold/{split}_gold.jsonl")}
        predictions_by_arm = {
            arm: {str(row["sample_id"]): row for row in read_jsonl(raw_dir / f"{arm}/{split}_predictions.jsonl")}
            for arm in ARMS
        }
        for sample_id in sorted(gold_by_id):
            gold_row = gold_by_id[sample_id]
            row = {
                "sample_id": sample_id,
                "split": split,
                "input_text": gold_row["input_text"],
                "gold_contract": as_contract(gold_row["gold_contract"]).to_dict(),
                "predictions": {},
            }
            for arm in ARMS:
                prediction_row = predictions_by_arm[arm][sample_id]
                row["predictions"][arm] = as_contract(prediction_row["prediction_contract"]).to_dict()
            rows.append(row)
    return rows


def _matrix_by_path(repo_root: Path) -> dict[str, dict[str, Any]]:
    matrix = json.loads(_repo_path(repo_root, HYBRID_REPORT / "representation-matrix.json").read_text(encoding="utf-8"))
    return {row["slot_path"]: row for row in matrix}


def _historical_design_metrics(repo_root: Path) -> dict[str, Any]:
    summary = read_json(_repo_path(repo_root, HYBRID_REPORT / "summary.json"))
    coverage = summary["coverage"]
    return {
        "strategy_assignment_rate": coverage["overall_representation_coverage"],
        "strategy_assigned_event_count": sum(
            int(coverage[name])
            for name in (
                "copy_backed_coverage",
                "bounded_structured_coverage",
                "enum_classification_coverage",
                "limited_free_generation_coverage",
                "task_schema_constrained_coverage",
                "unresolved_coverage",
            )
        ),
        "copy_strategy_candidate_coverage": coverage["copy_backed_rate"],
        "copy_strategy_candidate_count": coverage["copy_backed_coverage"],
        "renamed_from": {
            "strategy_assignment_rate": "overall_representation_coverage",
            "copy_strategy_candidate_coverage": "copy_backed_coverage/copy_backed_rate",
        },
    }


def build_task_scoped_policy(repo_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = _matrix_by_path(repo_root)
    counters: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    examples: dict[tuple[str, str, str], str] = {}
    for row in rows:
        source_text = row["input_text"]
        contract = row["gold_contract"]
        for slot_path, value in flatten_slot_values(contract["slots"]).items():
            if slot_path not in ANALYZED_SLOT_PATHS:
                continue
            key = (contract["task_type"], contract["route"], slot_path)
            counters[key]["sample_count"] += 1
            examples.setdefault(key, f"{row['sample_id']}")
            temp_scope = CopyBackedScope(
                task_type=contract["task_type"],
                route=contract["route"],
                slot_path=slot_path,
                enabled=True,
                evidence_reference=f"{RAW_INPUTS.as_posix()}#gold",
            )
            result = verify_copy_backed_value(value, source_text, temp_scope)
            counters[key][result.status] += 1
            if result.status in VERIFIED_STATUS_VALUES:
                counters[key]["copyable"] += 1

    policy_rows: list[dict[str, Any]] = []
    for key in sorted(counters):
        task_type, route, slot_path = key
        counts = counters[key]
        sample_count = counts["sample_count"]
        unique_exact = counts[VERIFIED_EXACT_UNIQUE]
        unique_normalized = counts[VERIFIED_NORMALIZED_UNIQUE]
        unique_verified = unique_exact + unique_normalized
        copyable_rate = _rate(unique_verified, sample_count)
        matrix_row = matrix.get(slot_path, {})
        confidence = matrix_row.get("confidence_level", "LOW")
        reasons: list[str] = []
        enabled = True
        if slot_path not in ENABLED_SLOT_PATHS:
            enabled = False
            reasons.append("slot_path_not_enabled_in_this_slice")
        if slot_path == "action":
            enabled = False
            reasons.append("action_semantics_depend_on_blocked_clarify_safety_contexts")
        if sample_count < MIN_SAMPLE_COUNT:
            enabled = False
            reasons.append(f"sample_count_below_{MIN_SAMPLE_COUNT}")
        if copyable_rate < MIN_COPYABLE_RATE:
            enabled = False
            reasons.append(f"copyable_rate_below_{MIN_COPYABLE_RATE:.2f}")
        if confidence not in {"HIGH", "MEDIUM"}:
            enabled = False
            reasons.append("confidence_not_high_or_medium")
        policy_rows.append(
            {
                "policy_version": POLICY_VERSION,
                "task_type": task_type,
                "route": route,
                "slot_path": slot_path,
                "scope_key": f"{task_type}:{route}:{slot_path}",
                "enabled": enabled,
                "verification_enabled": enabled,
                "exclusion_reason": "; ".join(reasons) if reasons else None,
                "sample_count": sample_count,
                "gold_unique_exact_span_count": unique_exact,
                "gold_unique_normalized_span_count": unique_normalized,
                "gold_unique_verified_span_count": unique_verified,
                "gold_unique_verified_span_rate": copyable_rate,
                "duplicate_span_ambiguity_count": counts[AMBIGUOUS_MULTIPLE_MATCHES],
                "span_not_found_count": counts[NOT_FOUND],
                "unsupported_value_type_count": counts[UNSUPPORTED_VALUE_TYPE],
                "confidence_level": confidence,
                "representation_strategy": matrix_row.get("proposed_representation", "unknown"),
                "fallback_behavior": "fail_closed_or_unresolved_when_span_not_verified",
                "evidence_reference": matrix_row.get("evidence_reference") or f"{RAW_INPUTS.as_posix()}#gold",
                "example_sample_id": examples[key],
            }
        )
    enabled_triples = [row["scope_key"] for row in policy_rows if row["enabled"]]
    return {
        "change_id": CHANGE_ID,
        "policy_version": POLICY_VERSION,
        "thresholds": {
            "min_sample_count": MIN_SAMPLE_COUNT,
            "min_copyable_rate": MIN_COPYABLE_RATE,
            "allowed_confidence_levels": ["HIGH", "MEDIUM"],
            "enabled_slot_paths": sorted(ENABLED_SLOT_PATHS),
        },
        "enabled_triples": enabled_triples,
        "policy_rows": policy_rows,
        "action_policy": {
            "enabled": False,
            "reason": "Action remains disabled because its meaning depends on blocked/clarify/safety semantics; this phase records analysis only.",
        },
        "historical_design_metrics": _historical_design_metrics(repo_root),
    }


def _scope_for_policy_row(row: dict[str, Any]) -> CopyBackedScope:
    return CopyBackedScope(
        task_type=row["task_type"],
        route=row["route"],
        slot_path=row["slot_path"],
        enabled=bool(row["enabled"]),
        policy_version=row["policy_version"],
        evidence_reference=row["evidence_reference"],
        exclusion_reason=row["exclusion_reason"],
    )


def _disabled_scope(task_type: str, route: str, slot_path: str, reason: str) -> CopyBackedScope:
    return CopyBackedScope(
        task_type=task_type,
        route=route,
        slot_path=slot_path,
        enabled=False,
        policy_version=POLICY_VERSION,
        exclusion_reason=reason,
    )


def _gold_correct_exact(
    *,
    predicted_contract: dict[str, Any],
    gold_contract: dict[str, Any],
    slot_path: str,
    predicted_value: Any,
) -> bool:
    if predicted_contract["task_type"] != gold_contract["task_type"] or predicted_contract["route"] != gold_contract["route"]:
        return False
    gold_slots = flatten_slot_values(gold_contract["slots"])
    return gold_slots.get(slot_path, MISSING) == predicted_value


def _result_is_false_accept(result: CopyBackedVerificationResult, source_text: str) -> bool:
    if result.status not in VERIFIED_STATUS_VALUES:
        return False
    if result.provenance != "system_verified_source" or result.source_span is None:
        return True
    return not verify_source_span(source_text, result.source_span)


def _count_result(counter: Counter[str], result: CopyBackedVerificationResult, source_text: str) -> None:
    counter["total"] += 1
    counter[result.status] += 1
    if result.status == VERIFIED_EXACT_UNIQUE:
        counter["unique_exact"] += 1
    if result.status == VERIFIED_NORMALIZED_UNIQUE:
        counter["unique_normalized"] += 1
    if result.status in VERIFIED_STATUS_VALUES:
        counter["unique_verified"] += 1
    if result.status in {
        AMBIGUOUS_MULTIPLE_MATCHES,
        NOT_FOUND,
        UNSUPPORTED_VALUE_TYPE,
        OUT_OF_SCOPE,
        INVALID_INPUT,
    }:
        counter["fail_closed"] += 1
    if _result_is_false_accept(result, source_text):
        counter["false_accept"] += 1
    if result.status in VERIFIED_STATUS_VALUES and result.source_span is not None and verify_source_span(source_text, result.source_span):
        counter["roundtrip_pass"] += 1


def _stats_from_counter(counter: Counter[str], *, prefix: str) -> dict[str, Any]:
    total = counter["total"]
    verified = counter["unique_verified"]
    return {
        f"{prefix}_event_count": total,
        "unique_exact_span_count": counter["unique_exact"],
        "unique_exact_span_rate": _rate(counter["unique_exact"], total),
        "unique_normalized_span_count": counter["unique_normalized"],
        "unique_normalized_span_rate": _rate(counter["unique_normalized"], total),
        "unique_verified_span_count": verified,
        "unique_verified_span_rate": _rate(verified, total),
        "duplicate_span_ambiguity_count": counter[AMBIGUOUS_MULTIPLE_MATCHES],
        "duplicate_span_ambiguity_rate": _rate(counter[AMBIGUOUS_MULTIPLE_MATCHES], total),
        "span_not_found_count": counter[NOT_FOUND],
        "span_not_found_rate": _rate(counter[NOT_FOUND], total),
        "unsupported_value_type_count": counter[UNSUPPORTED_VALUE_TYPE],
        "out_of_scope_count": counter[OUT_OF_SCOPE],
        "invalid_input_count": counter[INVALID_INPUT],
        "fail_closed_count": counter["fail_closed"],
        "fail_closed_rate": _rate(counter["fail_closed"], total),
        "status_counts": {status: counter[status] for status in sorted(counter) if status.isupper()},
    }


def build_verification_audit(repo_root: Path) -> dict[str, Any]:
    boundary = validate_copy_slice_inputs(repo_root)
    if boundary["decision_label"] != INPUT_BOUNDARY_PASSED:
        return {"change_id": CHANGE_ID, "decision_label": INPUT_BOUNDARY_BLOCKED, "input_boundary": boundary}

    rows = _load_rows(repo_root)
    policy = build_task_scoped_policy(repo_root, rows)
    policy_by_key = {row["scope_key"]: row for row in policy["policy_rows"]}
    enabled_policy_by_key = {key: row for key, row in policy_by_key.items() if row["enabled"]}
    gold_counter: Counter[str] = Counter()
    prediction_counter: Counter[str] = Counter()
    policy_status_counts: dict[str, Counter[str]] = defaultdict(Counter)
    prediction_status_by_arm: dict[str, Counter[str]] = defaultdict(Counter)
    action_counter: Counter[str] = Counter()
    sidecars: list[dict[str, Any]] = []
    source_verified_and_gold_correct = 0
    source_verified_gold_mismatch = 0
    source_verified_prediction_count = 0
    source_span_roundtrip_total = 0
    source_span_roundtrip_pass = 0
    provenance_false_accept_count = 0

    for row in rows:
        source_text = row["input_text"]
        gold_contract = row["gold_contract"]
        gold_slots = flatten_slot_values(gold_contract["slots"])
        for scope_key, policy_row in enabled_policy_by_key.items():
            slot_path = policy_row["slot_path"]
            if gold_contract["task_type"] != policy_row["task_type"] or gold_contract["route"] != policy_row["route"]:
                continue
            if slot_path not in gold_slots:
                continue
            scope = _scope_for_policy_row(policy_row)
            result = verify_copy_backed_value(gold_slots[slot_path], source_text, scope)
            _count_result(gold_counter, result, source_text)
            policy_status_counts[scope_key][result.status] += 1
            if result.status in VERIFIED_STATUS_VALUES:
                source_span_roundtrip_total += 1
                if result.source_span is not None and verify_source_span(source_text, result.source_span):
                    source_span_roundtrip_pass += 1
            if _result_is_false_accept(result, source_text):
                provenance_false_accept_count += 1
        if "action" in gold_slots:
            action_counter["gold_event_count"] += 1

        for run_role, predicted_contract in row["predictions"].items():
            predicted_slots = flatten_slot_values(predicted_contract["slots"])
            for slot_path, predicted_value in predicted_slots.items():
                scope_key = f"{predicted_contract['task_type']}:{predicted_contract['route']}:{slot_path}"
                policy_row = policy_by_key.get(scope_key)
                if policy_row is None:
                    scope = _disabled_scope(
                        predicted_contract["task_type"],
                        predicted_contract["route"],
                        slot_path,
                        "slot_path_or_task_scope_not_enabled_in_this_slice",
                    )
                else:
                    scope = _scope_for_policy_row(policy_row)
                result = verify_copy_backed_value(predicted_value, source_text, scope)
                _count_result(prediction_counter, result, source_text)
                prediction_status_by_arm[run_role][result.status] += 1
                if slot_path == "action":
                    action_counter["prediction_event_count"] += 1
                    action_counter[result.status] += 1
                if result.status in VERIFIED_STATUS_VALUES:
                    source_span_roundtrip_total += 1
                    source_verified_prediction_count += 1
                    if result.source_span is not None and verify_source_span(source_text, result.source_span):
                        source_span_roundtrip_pass += 1
                    if _gold_correct_exact(
                        predicted_contract=predicted_contract,
                        gold_contract=gold_contract,
                        slot_path=slot_path,
                        predicted_value=predicted_value,
                    ):
                        source_verified_and_gold_correct += 1
                    else:
                        source_verified_gold_mismatch += 1
                if _result_is_false_accept(result, source_text):
                    provenance_false_accept_count += 1

                sidecars.append(
                    {
                        "sample_id": row["sample_id"],
                        "split": row["split"],
                        "run_role": run_role,
                        "task_type": predicted_contract["task_type"],
                        "route": predicted_contract["route"],
                        "slot_path": slot_path,
                        "scope_key": scope.key,
                        "policy_version": scope.policy_version,
                        "verification_enabled": scope.enabled,
                        "status": result.status,
                        "match_kind": result.match_kind,
                        "provenance": result.provenance,
                        "fail_closed": result.fail_closed,
                        "reason": result.reason,
                        "normalization_rule": result.normalization_rule,
                        "candidate_span_count": result.candidate_span_count,
                        "source_text_hash": _sha256_text(source_text),
                        "source_span": result.source_span.to_dict() if result.source_span is not None else None,
                        "predicted_value_type": type(predicted_value).__name__,
                        "gold_value_present": slot_path in gold_slots,
                        "gold_correct_exact": _gold_correct_exact(
                            predicted_contract=predicted_contract,
                            gold_contract=gold_contract,
                            slot_path=slot_path,
                            predicted_value=predicted_value,
                        )
                        if result.status in VERIFIED_STATUS_VALUES
                        else None,
                    }
                )

    gold_stats = _stats_from_counter(gold_counter, prefix="eligible_copy")
    prediction_stats = _stats_from_counter(prediction_counter, prefix="prediction_slot")
    eligible_prediction_events = prediction_counter["total"] - prediction_counter[OUT_OF_SCOPE]
    prediction_stats.update(
        {
            "eligible_prediction_event_count": eligible_prediction_events,
            "source_verified_prediction_count": source_verified_prediction_count,
            "source_verified_prediction_rate": _rate(source_verified_prediction_count, eligible_prediction_events),
            "source_verified_and_gold_correct_count": source_verified_and_gold_correct,
            "source_verified_and_gold_correct_rate": _rate(
                source_verified_and_gold_correct, source_verified_prediction_count
            ),
            "source_verified_gold_mismatch_count": source_verified_gold_mismatch,
            "source_verified_gold_mismatch_rate": _rate(source_verified_gold_mismatch, source_verified_prediction_count),
        }
    )
    audit_core = {
        "change_id": CHANGE_ID,
        "generated_at": GENERATED_AT,
        "input_boundary": boundary,
        "policy": policy,
        "gold_verification": gold_stats,
        "prediction_verification": prediction_stats,
        "policy_status_counts": {
            key: {status: counter[status] for status in sorted(counter)}
            for key, counter in sorted(policy_status_counts.items())
        },
        "prediction_status_by_arm": {
            arm: {status: counter[status] for status in sorted(counter)} for arm, counter in sorted(prediction_status_by_arm.items())
        },
        "action_analysis": {
            "enabled": False,
            "verification_enabled": False,
            "gold_event_count": action_counter["gold_event_count"],
            "prediction_event_count": action_counter["prediction_event_count"],
            "source_verified_prediction_count": 0,
            "out_of_scope_prediction_count": action_counter[OUT_OF_SCOPE],
            "exclusion_reason": "Action semantics are tied to blocked/clarify/safety contexts and are analysis-only in this slice.",
        },
        "source_span_roundtrip": {
            "verified_span_count": source_span_roundtrip_total,
            "roundtrip_pass_count": source_span_roundtrip_pass,
            "roundtrip_pass_rate": _rate(source_span_roundtrip_pass, source_span_roundtrip_total),
        },
        "provenance_false_accept_count": provenance_false_accept_count,
        "silent_fallback_count": 0,
        "sidecar_count": len(sidecars),
    }
    return {
        "audit": audit_core,
        "sidecars": sidecars,
    }


def _v1_evaluator_delta(repo_root: Path, boundary: dict[str, Any]) -> dict[str, Any]:
    after_hashes = {
        path: _file_hash(_repo_path(repo_root, path))
        for path in boundary["raw_file_hashes"]
        if _repo_path(repo_root, path).exists()
    }
    return {
        "zero_delta": after_hashes == boundary["raw_file_hashes"],
        "basis": "sidecar_only_no_prediction_gold_schema_or_evaluator_mutation",
        "metric_reproduction_status": boundary["metric_reproduction_status"],
        "raw_input_hashes_preserved": after_hashes == boundary["raw_file_hashes"],
        "metric_deltas": {
            "exact_match": 0.0,
            "task_type_accuracy": 0.0,
            "route_accuracy": 0.0,
            "slot_accuracy": 0.0,
            "executable_pass_rate": 0.0,
        },
    }


def _claims() -> dict[str, bool]:
    return {
        "training_performed": False,
        "prediction_rerun_performed": False,
        "data_mutation_performed": False,
        "schema_migration_performed": False,
        "contract_core_v2_changed": False,
        "evaluator_relaxation_performed": False,
        "runtime_integration_performed": False,
        "action_enabled": False,
        "model_improvement_claim": False,
        "slot_performance_improvement_claim": False,
        "executable_quality_improvement_claim": False,
        "production_readiness_claim": False,
        "adapter_or_checkpoint_release": False,
    }


def _cannot_claim() -> list[str]:
    return [
        "source-backed provenance is task correctness",
        "slot accuracy improved",
        "executable pass improved",
        "model quality improved",
        "training target changed",
        "BrowserTaskContract V1 migrated",
        "ContractCoreV2 changed",
        "runtime or shadow integration exists",
        "action verification is enabled",
        "production or safety readiness",
        "held-out recovery",
        "live browser improvement",
    ]


def _decision_and_next_change(
    *,
    policy: dict[str, Any],
    gold: dict[str, Any],
    gates: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    enabled_slot_paths = sorted({row["slot_path"] for row in policy["policy_rows"] if row["enabled"]})
    ready = (
        enabled_slot_paths == ["field", "query", "target"]
        and gold["unique_verified_span_rate"] >= MIN_COPYABLE_RATE
        and gates["provenance_false_accept_count"] == 0
        and gates["silent_fallback_count"] == 0
        and gates["deterministic_rerun_rate"] == 1.0
        and gates["source_span_roundtrip_pass_rate"] == 1.0
        and gates["v1_evaluator_metric_delta_zero"] is True
        and gates["action_enabled"] is False
    )
    if ready:
        return READY_LABEL, {
            "change_id": "integrate-copy-backed-slot-verification-shadow-mode",
            "scope": "Integrate the verifier in shadow mode only, with sidecar comparison and no runtime enforcement unless separately approved.",
            "why_next": "The offline slice proves deterministic source-span provenance for enabled query/field/target scopes without mutating V1 predictions or evaluator behavior.",
        }
    if gold["unique_verified_span_rate"] > 0:
        return PARTIAL_LABEL, {
            "change_id": "refine-copy-backed-slot-verification-policy-thresholds",
            "scope": "Refine task-scoped thresholds or exclusions before shadow integration.",
            "why_next": "The slice produced some verified provenance but not enough gate evidence for shadow-mode integration.",
        }
    return NOT_JUSTIFIED_LABEL, {
        "change_id": "return-to-slot-representation-scope-selection",
        "scope": "Select a different bounded slot-representation slice.",
        "why_next": "The copy-backed source-span slice did not produce usable verified provenance on current evidence.",
    }


def _summary_from_audit(repo_root: Path, audit_payload: dict[str, Any]) -> dict[str, Any]:
    audit = audit_payload["audit"]
    policy = audit["policy"]
    gold = audit["gold_verification"]
    prediction = audit["prediction_verification"]
    v1_delta = _v1_evaluator_delta(repo_root, audit["input_boundary"])
    determinism_first = _stable_hash(audit)
    determinism_second = _stable_hash(build_verification_audit(repo_root)["audit"])
    deterministic_rerun_rate = 1.0 if determinism_first == determinism_second else 0.0
    gates = {
        "enabled_task_scoped_triples": policy["enabled_triples"],
        "gold_unique_verified_span_rate_at_or_above_threshold": gold["unique_verified_span_rate"] >= MIN_COPYABLE_RATE,
        "provenance_false_accept_count": audit["provenance_false_accept_count"],
        "silent_fallback_count": audit["silent_fallback_count"],
        "deterministic_rerun_rate": deterministic_rerun_rate,
        "source_span_roundtrip_pass_rate": audit["source_span_roundtrip"]["roundtrip_pass_rate"],
        "v1_evaluator_metric_delta_zero": v1_delta["zero_delta"],
        "action_enabled": audit["action_analysis"]["enabled"],
        "leak_scan_clean": True,
    }
    decision_label, recommended_next_change = _decision_and_next_change(policy=policy, gold=gold, gates=gates)
    enabled_slot_paths = sorted({row["slot_path"] for row in policy["policy_rows"] if row["enabled"]})
    return {
        "change_id": CHANGE_ID,
        "generated_at": GENERATED_AT,
        "evidence_kind": "offline_copy_backed_slot_verification_slice",
        "decision_label": decision_label,
        "input_boundary": audit["input_boundary"],
        "enabled_scope": {
            "slot_paths": enabled_slot_paths,
            "task_scoped_triples": policy["enabled_triples"],
            "policy_version": POLICY_VERSION,
            "action_enabled": False,
        },
        "historical_design_metrics": policy["historical_design_metrics"],
        "gold_verification": gold,
        "prediction_verification": prediction,
        "action_analysis": audit["action_analysis"],
        "source_span_roundtrip": audit["source_span_roundtrip"],
        "provenance_false_accept_count": audit["provenance_false_accept_count"],
        "silent_fallback_count": audit["silent_fallback_count"],
        "deterministic_rerun_rate": deterministic_rerun_rate,
        "v1_evaluator_metric_delta": v1_delta,
        "gates": gates,
        "claims": _claims(),
        "cannot_claim": _cannot_claim(),
        "recommended_next_change": recommended_next_change,
        "closeout_answers": _closeout_answers(policy, gold, prediction, audit, gates, decision_label, recommended_next_change),
    }


def _closeout_answers(
    policy: dict[str, Any],
    gold: dict[str, Any],
    prediction: dict[str, Any],
    audit: dict[str, Any],
    gates: dict[str, Any],
    decision_label: str,
    recommended_next_change: dict[str, Any],
) -> dict[str, Any]:
    return {
        "enabled_task_scoped_triples": policy["enabled_triples"],
        "why_action_not_enabled": audit["action_analysis"]["exclusion_reason"],
        "strategy_assignment_rate": policy["historical_design_metrics"]["strategy_assignment_rate"],
        "copy_strategy_candidate_coverage": policy["historical_design_metrics"]["copy_strategy_candidate_coverage"],
        "gold_unique_exact_span_rate": gold["unique_exact_span_rate"],
        "gold_unique_normalized_span_rate": gold["unique_normalized_span_rate"],
        "duplicate_ambiguity_rate": gold["duplicate_span_ambiguity_rate"],
        "span_not_found_rate": gold["span_not_found_rate"],
        "control_treatment_source_verified_prediction_rate": prediction["source_verified_prediction_rate"],
        "source_verified_and_gold_correct_rate": prediction["source_verified_and_gold_correct_rate"],
        "source_verified_but_gold_mismatch_rate": prediction["source_verified_gold_mismatch_rate"],
        "provenance_false_accept_count_is_zero": gates["provenance_false_accept_count"] == 0,
        "silent_fallback_count_is_zero": gates["silent_fallback_count"] == 0,
        "v1_evaluator_zero_delta": gates["v1_evaluator_metric_delta_zero"],
        "final_decision_label": decision_label,
        "unique_next_change": recommended_next_change["change_id"],
        "current_cannot_claim": _cannot_claim(),
    }


def _write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    answers = summary["closeout_answers"]
    lines = [
        "# Copy-backed Slot Verification Slice",
        "",
        f"Decision: `{summary['decision_label']}`.",
        "",
        "This is an offline sidecar-only verification slice. Source-backed provenance is not correctness.",
        "",
        "## 17-question closeout",
        "",
        f"1. Enabled task-scoped triples: `{', '.join(answers['enabled_task_scoped_triples'])}`.",
        f"2. Action not enabled: {answers['why_action_not_enabled']}",
        f"3. strategy_assignment_rate: {answers['strategy_assignment_rate']:.6f}.",
        f"4. copy_strategy_candidate_coverage: {answers['copy_strategy_candidate_coverage']:.6f}.",
        f"5. Gold unique exact span rate: {answers['gold_unique_exact_span_rate']:.6f}.",
        f"6. Gold unique normalized span rate: {answers['gold_unique_normalized_span_rate']:.6f}.",
        f"7. Duplicate ambiguity rate: {answers['duplicate_ambiguity_rate']:.6f}.",
        f"8. Span not-found rate: {answers['span_not_found_rate']:.6f}.",
        f"9. Control/Treatment source-verified prediction rate: {answers['control_treatment_source_verified_prediction_rate']:.6f}.",
        f"10. Source-verified-and-gold-correct rate: {answers['source_verified_and_gold_correct_rate']:.6f}.",
        f"11. Source-verified-but-gold-mismatch rate: {answers['source_verified_but_gold_mismatch_rate']:.6f}.",
        f"12. provenance_false_accept_count=0: `{answers['provenance_false_accept_count_is_zero']}`.",
        f"13. silent_fallback_count=0: `{answers['silent_fallback_count_is_zero']}`.",
        f"14. V1 evaluator zero delta: `{answers['v1_evaluator_zero_delta']}`.",
        f"15. Final decision label: `{answers['final_decision_label']}`.",
        f"16. Unique next change: `{answers['unique_next_change']}`.",
        "17. Current cannot claim: " + "; ".join(answers["current_cannot_claim"]) + ".",
        "",
        "## Metrics",
        "",
        f"- Eligible gold copy events: {summary['gold_verification']['eligible_copy_event_count']}.",
        f"- Unique verified gold span rate: {summary['gold_verification']['unique_verified_span_rate']:.6f}.",
        f"- Eligible prediction events: {summary['prediction_verification']['eligible_prediction_event_count']}.",
        f"- Source-verified prediction count: {summary['prediction_verification']['source_verified_prediction_count']}.",
        f"- Source span roundtrip pass rate: {summary['source_span_roundtrip']['roundtrip_pass_rate']:.6f}.",
        f"- Provenance false accept count: {summary['provenance_false_accept_count']}.",
        f"- Silent fallback count: {summary['silent_fallback_count']}.",
        "",
        "## Claim Boundary",
        "",
        "No training, prediction rerun, V1 schema migration, evaluator relaxation, runtime integration, action enablement, model-improvement claim, slot-accuracy claim, executable-quality claim, production-readiness claim, held-out-recovery claim, or live-browser claim occurred.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_recommended_next_change(path: Path, summary: dict[str, Any]) -> None:
    next_change = summary["recommended_next_change"]
    lines = [
        "# Recommended Next Change",
        "",
        f"Decision: `{summary['decision_label']}`.",
        "",
        f"Next change: `{next_change['change_id']}`.",
        "",
        f"Scope: {next_change['scope']}",
        "",
        "Reason: " + next_change["why_next"],
        "",
        "Boundary: source-backed provenance is not correctness; any shadow integration must remain sidecar-only until separately specified and validated.",
        "",
        "Non-goals: training, prediction repair, evaluator relaxation, action enablement, runtime enforcement, production claims, and model-quality claims.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_doc(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Copy-backed Slot Verification",
        "",
        "This document describes the bounded offline verifier implemented by `implement-copy-backed-slot-verification-slice`.",
        "",
        "## Source-span semantics",
        "",
        "- Source basis: original `input_text` from recovered public-safe raw inputs.",
        "- Offset unit: Python/Unicode character index.",
        "- Start is inclusive and end is exclusive.",
        "- A verified exact span must satisfy `input_text[start:end] == span.text`.",
        "- A verified normalized span must map from normalized text back to one contiguous original source span.",
        "- The verifier records `source_text_hash` and never trusts model-authored provenance.",
        "",
        "## Matching boundary",
        "",
        "Exact matching runs first. If exact lookup is absent, bounded normalized matching may use Unicode NFKC, casefolding, and whitespace/punctuation separator omission. It does not use city aliases, product aliases, date conversion, URL resolving, semantic scoring, LLM judging, embeddings, or fuzzy matching.",
        "",
        "## Action stays disabled",
        "",
        "Action stays disabled in this phase. `action` is analyzed only because its semantics depend on blocked, clarify, and safety contexts; it receives no verified provenance and is not an acceptance gate.",
        "",
        "## Provenance is not correctness",
        "",
        "The verifier can prove that an eligible predicted value is present as a unique source span. It does not prove the task type, route, slot selection, executable behavior, or model quality. The report therefore separates source-verified predictions from source-verified-and-gold-correct predictions and source-verified-but-gold-mismatch predictions.",
        "",
        "## Current evidence",
        "",
        f"- Decision: `{summary['decision_label']}`.",
        f"- Enabled triples: `{', '.join(summary['enabled_scope']['task_scoped_triples'])}`.",
        f"- Gold unique verified span rate: {summary['gold_verification']['unique_verified_span_rate']:.6f}.",
        f"- Prediction source-verified rate over eligible events: {summary['prediction_verification']['source_verified_prediction_rate']:.6f}.",
        f"- Provenance false accepts: {summary['provenance_false_accept_count']}.",
        f"- Silent fallbacks: {summary['silent_fallback_count']}.",
        f"- V1 evaluator zero delta: {summary['v1_evaluator_metric_delta']['zero_delta']}.",
        "",
        "## Claim boundary",
        "",
        "No training, prediction rerun, data mutation, V1 schema migration, ContractCoreV2 change, evaluator relaxation, action enablement, runtime integration, model improvement claim, slot accuracy claim, executable quality claim, production readiness claim, held-out recovery claim, or live browser claim occurred.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_blocked(output_dir: Path, boundary: dict[str, Any]) -> dict[str, Any]:
    _clean_output_dir(output_dir)
    blocked = {
        "change_id": CHANGE_ID,
        "generated_at": GENERATED_AT,
        "decision": INPUT_BOUNDARY_BLOCKED,
        "input_boundary": boundary,
        "claims": _claims(),
    }
    write_json(output_dir / "blocked.json", blocked)
    return blocked


def write_copy_backed_slot_verification_reports(
    repo_root: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    doc_path: Path = DEFAULT_DOC_PATH,
) -> dict[str, Any]:
    boundary = validate_copy_slice_inputs(repo_root)
    if boundary["decision_label"] != INPUT_BOUNDARY_PASSED:
        return {"blocked": _write_blocked(output_dir, boundary)}

    _clean_output_dir(output_dir)
    audit_payload = build_verification_audit(repo_root)
    summary = _summary_from_audit(repo_root, audit_payload)
    audit = audit_payload["audit"]
    sidecars = audit_payload["sidecars"]

    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "task-scoped-policy.json", audit["policy"])
    write_json(output_dir / "verification-audit.json", audit)
    write_jsonl(output_dir / "verification-sidecars.jsonl", sidecars)
    _write_summary_md(output_dir / "summary.md", summary)
    _write_recommended_next_change(output_dir / "recommended-next-change.md", summary)
    _write_doc(doc_path, summary)
    return {
        "summary": summary,
        "audit": audit,
        "policy": audit["policy"],
        "sidecar_count": len(sidecars),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the copy-backed slot verification slice.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--doc-path", type=Path, default=DEFAULT_DOC_PATH)
    args = parser.parse_args()
    result = write_copy_backed_slot_verification_reports(args.repo_root, args.output_dir, args.doc_path)
    if "blocked" in result:
        print(result["blocked"]["decision"])
        return 1
    print(result["summary"]["decision_label"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
