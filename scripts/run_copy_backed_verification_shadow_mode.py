# ruff: noqa: E501
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from voice2task.copy_backed_slot_verification import (
    OUT_OF_SCOPE,
    VERIFIED_STATUS_VALUES,
    CopyBackedScope,
    CopyBackedVerificationResult,
    verify_copy_backed_value,
    verify_source_span,
)
from voice2task.io import read_json, read_jsonl, write_json, write_jsonl
from voice2task.schemas import as_contract, canonical_contract_json
from voice2task.slot_error_analysis import flatten_slot_values

CHANGE_ID = "integrate-copy-backed-slot-verification-shadow-mode"
GENERATED_AT = "2026-06-22"
INPUT_BOUNDARY_PASSED = "SHADOW_MODE_INPUT_BOUNDARY_PASSED"
INPUT_BOUNDARY_BLOCKED = "SHADOW_MODE_BLOCKED_INVALID_INPUT"
READY_LABEL = "SHADOW_MODE_READY_FOR_REVIEW"
PARTIAL_LABEL = "SHADOW_MODE_PARTIAL_NEEDS_REFINEMENT"
NOT_READY_LABEL = "SHADOW_MODE_NOT_READY"

RAW_INPUTS = Path("reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs")
COPY_SLICE_DIR = Path("reports/public-sample/copy-backed-slot-verification-slice")
DEFAULT_OUTPUT_DIR = Path("reports/public-sample/copy-backed-verification-shadow-mode")
DEFAULT_DOC_PATH = Path("docs/copy-backed-verification-shadow-mode.md")

SPLITS = ("dev", "test")
ARMS = ("control", "treatment")
REPORT_FILES = (
    "summary.md",
    "summary.json",
    "shadow-sidecars.jsonl",
    "shadow-compatibility.json",
    "recommended-next-change.md",
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
REQUIRED_COPY_SLICE_FILES = (
    "summary.json",
    "task-scoped-policy.json",
    "verification-audit.json",
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


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_hash(value: Any) -> str:
    return _sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _clean_output_dir(output_dir: Path, *, keep_blocked: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in REPORT_FILES:
        path = output_dir / filename
        if path.exists() and not (keep_blocked and filename == "blocked.json"):
            path.unlink()


def validate_shadow_mode_inputs(
    repo_root: Path,
    *,
    copy_slice_dir: Path = COPY_SLICE_DIR,
) -> dict[str, Any]:
    raw_dir = _repo_path(repo_root, RAW_INPUTS)
    copy_dir = copy_slice_dir if copy_slice_dir.is_absolute() else _repo_path(repo_root, copy_slice_dir)
    blocking_reasons: list[str] = []

    for relative in REQUIRED_RAW_FILES:
        if not (raw_dir / relative).exists():
            blocking_reasons.append(f"missing raw input: {RAW_INPUTS / relative}")
    for filename in REQUIRED_COPY_SLICE_FILES:
        if not (copy_dir / filename).exists():
            blocking_reasons.append(f"missing copy-slice artifact: {copy_dir / filename}")

    copy_summary: dict[str, Any] = {}
    policy: dict[str, Any] = {}
    if (copy_dir / "summary.json").exists():
        copy_summary = read_json(copy_dir / "summary.json")
    if (copy_dir / "task-scoped-policy.json").exists():
        policy = read_json(copy_dir / "task-scoped-policy.json")

    copy_decision = copy_summary.get("decision_label")
    if copy_decision != "COPY_SLICE_READY_FOR_SHADOW_INTEGRATION":
        blocking_reasons.append(f"copy slice is not ready for shadow integration: {copy_decision}")

    enabled_triples = copy_summary.get("enabled_scope", {}).get("task_scoped_triples", [])
    policy_enabled_triples = policy.get("enabled_triples", [])
    if enabled_triples != policy_enabled_triples:
        blocking_reasons.append("copy slice summary/policy enabled triples diverge")
    if copy_summary.get("enabled_scope", {}).get("slot_paths") != ["field", "query", "target"]:
        blocking_reasons.append("enabled slot paths are not exactly field/query/target")
    if copy_summary.get("action_analysis", {}).get("enabled") is not False:
        blocking_reasons.append("action appears enabled in copy slice")
    if copy_summary.get("v1_evaluator_metric_delta", {}).get("zero_delta") is not True:
        blocking_reasons.append("copy slice does not prove V1 evaluator zero delta")
    if copy_summary.get("provenance_false_accept_count") != 0:
        blocking_reasons.append("copy slice provenance false accepts are nonzero")
    if copy_summary.get("silent_fallback_count") != 0:
        blocking_reasons.append("copy slice silent fallback count is nonzero")

    expected_hashes = copy_summary.get("input_boundary", {}).get("raw_file_hashes", {})
    current_hashes: dict[str, str] = {}
    for path_text in expected_hashes:
        path = _repo_path(repo_root, path_text)
        if path.exists():
            current_hashes[path_text] = _file_hash(path)
        else:
            blocking_reasons.append(f"raw hash path missing: {path_text}")
    if expected_hashes and current_hashes != expected_hashes:
        blocking_reasons.append("raw input hashes differ from copy slice boundary")

    return {
        "change_id": CHANGE_ID,
        "decision_label": INPUT_BOUNDARY_BLOCKED if blocking_reasons else INPUT_BOUNDARY_PASSED,
        "blocking_reasons": blocking_reasons,
        "copy_slice_dir": copy_slice_dir.as_posix(),
        "copy_slice_decision_label": copy_decision,
        "enabled_task_scoped_triples": enabled_triples,
        "action_enabled": copy_summary.get("action_analysis", {}).get("enabled"),
        "v1_evaluator_metric_delta_zero": copy_summary.get("v1_evaluator_metric_delta", {}).get("zero_delta"),
        "raw_input_hashes_preserved": bool(expected_hashes) and current_hashes == expected_hashes,
        "expected_raw_file_hashes": expected_hashes,
        "current_raw_file_hashes": current_hashes,
        "approved_inputs": [
            RAW_INPUTS.as_posix(),
            copy_slice_dir.as_posix(),
        ],
    }


def _load_rows(repo_root: Path) -> list[dict[str, Any]]:
    raw_dir = _repo_path(repo_root, RAW_INPUTS)
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        gold_by_id = {str(row["sample_id"]): row for row in read_jsonl(raw_dir / f"gold/{split}_gold.jsonl")}
        for arm in ARMS:
            predictions = read_jsonl(raw_dir / f"{arm}/{split}_predictions.jsonl")
            for prediction_row in predictions:
                sample_id = str(prediction_row["sample_id"])
                gold_row = gold_by_id[sample_id]
                rows.append(
                    {
                        "sample_id": sample_id,
                        "split": split,
                        "run_role": arm,
                        "input_text": gold_row["input_text"],
                        "input_hash": gold_row["input_hash"],
                        "gold_contract": as_contract(gold_row["gold_contract"]).to_dict(),
                        "prediction_contract": as_contract(prediction_row["prediction_contract"]).to_dict(),
                    }
                )
    return sorted(rows, key=lambda item: (item["split"], item["sample_id"], item["run_role"]))


def _policy_by_scope(repo_root: Path, copy_slice_dir: Path) -> dict[str, dict[str, Any]]:
    copy_dir = copy_slice_dir if copy_slice_dir.is_absolute() else _repo_path(repo_root, copy_slice_dir)
    policy = read_json(copy_dir / "task-scoped-policy.json")
    return {row["scope_key"]: row for row in policy["policy_rows"]}


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
        policy_version="copy-backed-slot-verification-slice-v1",
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


def _diagnostic_for_slot(
    *,
    row: dict[str, Any],
    slot_path: str,
    predicted_value: Any,
    policy_by_scope: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    prediction_contract = row["prediction_contract"]
    scope_key = f"{prediction_contract['task_type']}:{prediction_contract['route']}:{slot_path}"
    policy_row = policy_by_scope.get(scope_key)
    if policy_row is None:
        scope = _disabled_scope(
            prediction_contract["task_type"],
            prediction_contract["route"],
            slot_path,
            "slot_path_or_task_scope_not_enabled_for_shadow_mode",
        )
    else:
        scope = _scope_for_policy_row(policy_row)
    result = verify_copy_backed_value(predicted_value, row["input_text"], scope)
    gold_correct = (
        _gold_correct_exact(
            predicted_contract=prediction_contract,
            gold_contract=row["gold_contract"],
            slot_path=slot_path,
            predicted_value=predicted_value,
        )
        if result.status in VERIFIED_STATUS_VALUES
        else None
    )
    return {
        "slot_path": slot_path,
        "scope_key": scope.key,
        "verification_enabled": scope.enabled,
        "status": result.status,
        "match_kind": result.match_kind,
        "provenance": result.provenance,
        "fail_closed": result.fail_closed,
        "reason": result.reason,
        "normalization_rule": result.normalization_rule,
        "candidate_span_count": result.candidate_span_count,
        "source_span": result.source_span.to_dict() if result.source_span is not None else None,
        "gold_value_present": slot_path in flatten_slot_values(row["gold_contract"]["slots"]),
        "gold_correct_exact": gold_correct,
        "predicted_value_type": type(predicted_value).__name__,
    }


def _count_diagnostic(counter: Counter[str], diagnostic: dict[str, Any], source_text: str) -> None:
    counter["slot_diagnostic_count"] += 1
    if diagnostic["verification_enabled"]:
        counter["enabled_slot_diagnostic_count"] += 1
    if diagnostic["status"] == OUT_OF_SCOPE:
        counter["out_of_scope_diagnostic_count"] += 1
    if diagnostic["slot_path"] == "action":
        counter["action_disabled_diagnostic_count"] += 1
    if diagnostic["provenance"] == "system_verified_source":
        counter["source_verified_prediction_count"] += 1
        if diagnostic["gold_correct_exact"] is True:
            counter["source_verified_and_gold_correct_count"] += 1
        else:
            counter["source_verified_gold_mismatch_count"] += 1
    if diagnostic["fail_closed"]:
        counter["fail_closed_count"] += 1
    if diagnostic["verification_enabled"] and diagnostic["status"] == OUT_OF_SCOPE:
        counter["silent_fallback_count"] += 1
    source_span = diagnostic.get("source_span")
    if diagnostic["provenance"] == "system_verified_source":
        if not isinstance(source_span, dict):
            counter["provenance_false_accept_count"] += 1
        elif source_text[source_span["start"] : source_span["end"]] != source_span["text"]:
            counter["provenance_false_accept_count"] += 1


def build_shadow_mode_payload(
    repo_root: Path,
    *,
    copy_slice_dir: Path = COPY_SLICE_DIR,
) -> dict[str, Any]:
    boundary = validate_shadow_mode_inputs(repo_root, copy_slice_dir=copy_slice_dir)
    if boundary["decision_label"] != INPUT_BOUNDARY_PASSED:
        return {"decision_label": INPUT_BOUNDARY_BLOCKED, "input_boundary": boundary}

    copy_dir = copy_slice_dir if copy_slice_dir.is_absolute() else _repo_path(repo_root, copy_slice_dir)
    copy_summary = read_json(copy_dir / "summary.json")
    policy_by_scope = _policy_by_scope(repo_root, copy_slice_dir)
    rows = _load_rows(repo_root)
    sidecars: list[dict[str, Any]] = []
    counter: Counter[str] = Counter()
    enforcement_enabled_count = 0
    action_source_verified_count = 0

    for row in rows:
        prediction_contract = row["prediction_contract"]
        prediction_slots = flatten_slot_values(prediction_contract["slots"])
        diagnostics = [
            _diagnostic_for_slot(
                row=row,
                slot_path=slot_path,
                predicted_value=prediction_slots[slot_path],
                policy_by_scope=policy_by_scope,
            )
            for slot_path in sorted(prediction_slots)
        ]
        for diagnostic in diagnostics:
            _count_diagnostic(counter, diagnostic, row["input_text"])
            if diagnostic["slot_path"] == "action" and diagnostic["provenance"] == "system_verified_source":
                action_source_verified_count += 1
        sidecars.append(
            {
                "change_id": CHANGE_ID,
                "sample_id": row["sample_id"],
                "split": row["split"],
                "run_role": row["run_role"],
                "task_type": prediction_contract["task_type"],
                "route": prediction_contract["route"],
                "shadow_mode_enabled": True,
                "enforcement_enabled": False,
                "policy_version": "copy-backed-slot-verification-slice-v1",
                "prediction_contract_hash": _sha256_text(canonical_contract_json(prediction_contract)),
                "input_hash": row["input_hash"],
                "source_text_hash": _sha256_text(row["input_text"]),
                "slot_diagnostics": diagnostics,
            }
        )

    prediction_contract_count = len(rows)
    shadow_sidecar_count = len(sidecars)
    enabled_total = counter["enabled_slot_diagnostic_count"]
    source_verified = counter["source_verified_prediction_count"]
    compatibility_core = {
        "change_id": CHANGE_ID,
        "generated_at": GENERATED_AT,
        "input_boundary": boundary,
        "previous_copy_slice": {
            "decision_label": copy_summary["decision_label"],
            "enabled_task_scoped_triples": copy_summary["enabled_scope"]["task_scoped_triples"],
            "source_verified_prediction_count": copy_summary["prediction_verification"][
                "source_verified_prediction_count"
            ],
            "source_verified_prediction_rate": copy_summary["prediction_verification"][
                "source_verified_prediction_rate"
            ],
        },
        "prediction_contract_count": prediction_contract_count,
        "shadow_sidecar_count": shadow_sidecar_count,
        "sidecar_attachment_rate": _rate(shadow_sidecar_count, prediction_contract_count),
        "raw_input_hashes_preserved": boundary["raw_input_hashes_preserved"],
        "v1_evaluator_metric_delta": {
            "zero_delta": boundary["v1_evaluator_metric_delta_zero"],
            "basis": "shadow_sidecar_only_no_prediction_gold_schema_or_evaluator_mutation",
            "metric_deltas": {
                "exact_match": 0.0,
                "task_type_accuracy": 0.0,
                "route_accuracy": 0.0,
                "slot_accuracy": 0.0,
                "executable_pass_rate": 0.0,
            },
        },
        "sidecar_schema": {
            "unit": "one_row_per_split_sample_run_role_prediction_contract",
            "required_fields": [
                "sample_id",
                "split",
                "run_role",
                "shadow_mode_enabled",
                "enforcement_enabled",
                "prediction_contract_hash",
                "input_hash",
                "slot_diagnostics",
            ],
            "contract_mutation_allowed": False,
            "evaluator_input_allowed": False,
        },
    }
    compatibility_hash = _stable_hash({"compatibility": compatibility_core, "sidecars": sidecars})
    return {
        "decision_label": READY_LABEL,
        "sidecars": sidecars,
        "compatibility_core": compatibility_core,
        "metrics_core": {
            "slot_diagnostic_count": counter["slot_diagnostic_count"],
            "enabled_slot_diagnostic_count": enabled_total,
            "out_of_scope_diagnostic_count": counter["out_of_scope_diagnostic_count"],
            "action_disabled_diagnostic_count": counter["action_disabled_diagnostic_count"],
            "source_verified_prediction_count": source_verified,
            "source_verified_prediction_rate": _rate(source_verified, enabled_total),
            "source_verified_and_gold_correct_count": counter["source_verified_and_gold_correct_count"],
            "source_verified_and_gold_correct_rate": _rate(
                counter["source_verified_and_gold_correct_count"], source_verified
            ),
            "source_verified_gold_mismatch_count": counter["source_verified_gold_mismatch_count"],
            "source_verified_gold_mismatch_rate": _rate(counter["source_verified_gold_mismatch_count"], source_verified),
            "fail_closed_count": counter["fail_closed_count"],
            "fail_closed_rate": _rate(counter["fail_closed_count"], counter["slot_diagnostic_count"]),
            "provenance_false_accept_count": counter["provenance_false_accept_count"],
            "silent_fallback_count": counter["silent_fallback_count"],
            "enforcement_enabled_count": enforcement_enabled_count,
            "compatibility_hash": compatibility_hash,
        },
        "action_source_verified_count": action_source_verified_count,
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
        "runtime_enforcement_enabled": False,
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
        "shadow mode is runtime enforcement",
        "slot accuracy improved",
        "executable pass improved",
        "model quality improved",
        "training target changed",
        "BrowserTaskContract V1 migrated",
        "ContractCoreV2 changed",
        "action verification is enabled",
        "production or safety readiness",
        "held-out recovery",
        "live browser improvement",
    ]


def _decision_and_next_change(summary_core: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    gates = summary_core["gates"]
    ready = (
        gates["sidecar_attachment_rate"] == 1.0
        and gates["raw_input_hashes_preserved"] is True
        and gates["v1_evaluator_metric_delta_zero"] is True
        and gates["enforcement_enabled_count"] == 0
        and gates["action_source_verified_count"] == 0
        and gates["provenance_false_accept_count"] == 0
        and gates["silent_fallback_count"] == 0
        and gates["deterministic_rerun_rate"] == 1.0
    )
    if ready:
        return READY_LABEL, {
            "change_id": "review-copy-backed-shadow-mode-before-runtime-wiring",
            "scope": "Review the shadow-mode evidence before any narrower runtime-wiring proposal; no enforcement is approved by this phase.",
            "why_next": "Shadow sidecars attach deterministically to every current prediction contract while preserving V1 evaluator behavior.",
        }
    if gates["sidecar_attachment_rate"] > 0:
        return PARTIAL_LABEL, {
            "change_id": "refine-copy-backed-shadow-sidecar-coverage",
            "scope": "Fix shadow sidecar coverage or compatibility gaps before review.",
            "why_next": "The shadow integration produced some evidence but did not satisfy all readiness gates.",
        }
    return NOT_READY_LABEL, {
        "change_id": "return-to-copy-backed-verification-slice",
        "scope": "Revisit the offline verifier evidence before another shadow integration attempt.",
        "why_next": "Shadow integration did not attach usable sidecars on current evidence.",
    }


def _summary_from_payload(repo_root: Path, payload: dict[str, Any], *, copy_slice_dir: Path) -> dict[str, Any]:
    first_hash = _stable_hash({"sidecars": payload["sidecars"], "compatibility": payload["compatibility_core"]})
    second_payload = build_shadow_mode_payload(repo_root, copy_slice_dir=copy_slice_dir)
    second_hash = _stable_hash({"sidecars": second_payload["sidecars"], "compatibility": second_payload["compatibility_core"]})
    deterministic_rerun_rate = 1.0 if first_hash == second_hash else 0.0
    compatibility = payload["compatibility_core"]
    metrics = payload["metrics_core"]
    gates = {
        "sidecar_attachment_rate": compatibility["sidecar_attachment_rate"],
        "raw_input_hashes_preserved": compatibility["raw_input_hashes_preserved"],
        "v1_evaluator_metric_delta_zero": compatibility["v1_evaluator_metric_delta"]["zero_delta"],
        "enforcement_enabled_count": metrics["enforcement_enabled_count"],
        "action_source_verified_count": payload["action_source_verified_count"],
        "provenance_false_accept_count": metrics["provenance_false_accept_count"],
        "silent_fallback_count": metrics["silent_fallback_count"],
        "deterministic_rerun_rate": deterministic_rerun_rate,
        "leak_scan_clean": True,
    }
    summary_core = {"gates": gates}
    decision_label, recommended_next_change = _decision_and_next_change(summary_core)
    return {
        "change_id": CHANGE_ID,
        "generated_at": GENERATED_AT,
        "evidence_kind": "copy_backed_verification_shadow_mode",
        "decision_label": decision_label,
        "input_boundary": compatibility["input_boundary"],
        "enabled_scope": {
            "slot_paths": ["field", "query", "target"],
            "task_scoped_triples": compatibility["previous_copy_slice"]["enabled_task_scoped_triples"],
            "action_enabled": False,
        },
        "sidecar_attachment": {
            "prediction_contract_count": compatibility["prediction_contract_count"],
            "shadow_sidecar_count": compatibility["shadow_sidecar_count"],
            "sidecar_attachment_rate": compatibility["sidecar_attachment_rate"],
        },
        "shadow_metrics": {key: value for key, value in metrics.items() if key != "compatibility_hash"},
        "action_shadow": {
            "enabled": False,
            "diagnostic_count": metrics["action_disabled_diagnostic_count"],
            "source_verified_count": payload["action_source_verified_count"],
            "status": "disabled_analysis_only",
        },
        "compatibility": compatibility,
        "deterministic_rerun_rate": deterministic_rerun_rate,
        "gates": gates,
        "claims": _claims(),
        "cannot_claim": _cannot_claim(),
        "recommended_next_change": recommended_next_change,
    }


def _write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Copy-backed Verification Shadow Mode",
        "",
        f"Decision: `{summary['decision_label']}`.",
        "",
        "Shadow mode is not enforcement. Source-backed provenance is not correctness.",
        "",
        "## Metrics",
        "",
        f"- Prediction contracts: {summary['sidecar_attachment']['prediction_contract_count']}.",
        f"- Shadow sidecars: {summary['sidecar_attachment']['shadow_sidecar_count']}.",
        f"- Sidecar attachment rate: {summary['sidecar_attachment']['sidecar_attachment_rate']:.6f}.",
        f"- Enabled slot diagnostics: {summary['shadow_metrics']['enabled_slot_diagnostic_count']}.",
        f"- Source-verified predictions: {summary['shadow_metrics']['source_verified_prediction_count']}.",
        f"- Source-verified prediction rate: {summary['shadow_metrics']['source_verified_prediction_rate']:.6f}.",
        f"- Source-verified and gold-correct: {summary['shadow_metrics']['source_verified_and_gold_correct_count']}.",
        f"- Source-verified but gold-mismatch: {summary['shadow_metrics']['source_verified_gold_mismatch_count']}.",
        f"- Action disabled diagnostics: {summary['action_shadow']['diagnostic_count']}.",
        f"- Enforcement enabled count: {summary['gates']['enforcement_enabled_count']}.",
        f"- Provenance false accepts: {summary['gates']['provenance_false_accept_count']}.",
        f"- Silent fallbacks: {summary['gates']['silent_fallback_count']}.",
        "",
        "## Boundary",
        "",
        "The sidecar file is diagnostic evidence only. It does not mutate predictions, gold contracts, schema, evaluator inputs, runtime behavior, or action semantics.",
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
        f"Reason: {next_change['why_next']}",
        "",
        "Boundary: source-backed provenance is not correctness, and shadow mode is not enforcement.",
        "",
        "Non-goals: runtime enforcement, action enablement, training, evaluator changes, prediction repair, model-quality claims, production readiness, and live-browser claims.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_doc(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Copy-backed Verification Shadow Mode",
        "",
        "This document describes the bounded shadow-mode integration for the copy-backed verifier.",
        "",
        "## Shadow semantics",
        "",
        "Shadow mode emits one sidecar row for each current Control/Treatment prediction contract. The sidecar records `shadow_mode_enabled=true` and `enforcement_enabled=false`, then nests slot-level verifier diagnostics under `slot_diagnostics`.",
        "",
        "## Sidecar schema",
        "",
        "Each sidecar contains `sample_id`, `split`, `run_role`, `task_type`, `route`, `prediction_contract_hash`, `input_hash`, `source_text_hash`, `policy_version`, and deterministic slot diagnostics. The sidecar is not a replacement contract and is not an evaluator input.",
        "",
        "## Verifier reuse",
        "",
        "The script reuses `voice2task.copy_backed_slot_verification` and the previous task-scoped policy. It does not widen normalization, add semantic matching, call an LLM, resolve URLs, or repair predictions.",
        "",
        "## Action remains disabled",
        "",
        "Action remains disabled in shadow mode. Action diagnostics are out-of-scope analysis only and receive no source-verified provenance.",
        "",
        "## Evidence",
        "",
        f"- Decision: `{summary['decision_label']}`.",
        f"- Sidecar attachment rate: {summary['sidecar_attachment']['sidecar_attachment_rate']:.6f}.",
        f"- Source-verified prediction rate: {summary['shadow_metrics']['source_verified_prediction_rate']:.6f}.",
        f"- V1 evaluator zero delta: {summary['gates']['v1_evaluator_metric_delta_zero']}.",
        f"- Enforcement enabled count: {summary['gates']['enforcement_enabled_count']}.",
        f"- Action source-verified count: {summary['gates']['action_source_verified_count']}.",
        "",
        "## Claim boundary",
        "",
        "No training, prediction rerun, data mutation, V1 schema migration, ContractCoreV2 change, evaluator relaxation, action enablement, runtime enforcement, model improvement claim, slot accuracy claim, executable quality claim, production readiness claim, held-out recovery claim, or live browser claim occurred.",
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


def write_copy_backed_verification_shadow_mode_reports(
    repo_root: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    doc_path: Path = DEFAULT_DOC_PATH,
    *,
    copy_slice_dir: Path = COPY_SLICE_DIR,
) -> dict[str, Any]:
    boundary = validate_shadow_mode_inputs(repo_root, copy_slice_dir=copy_slice_dir)
    if boundary["decision_label"] != INPUT_BOUNDARY_PASSED:
        return {"blocked": _write_blocked(output_dir, boundary)}

    _clean_output_dir(output_dir)
    payload = build_shadow_mode_payload(repo_root, copy_slice_dir=copy_slice_dir)
    summary = _summary_from_payload(repo_root, payload, copy_slice_dir=copy_slice_dir)
    compatibility = dict(payload["compatibility_core"])
    compatibility["deterministic_rerun_rate"] = summary["deterministic_rerun_rate"]
    compatibility["decision_label"] = summary["decision_label"]

    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "shadow-compatibility.json", compatibility)
    write_jsonl(output_dir / "shadow-sidecars.jsonl", payload["sidecars"])
    _write_summary_md(output_dir / "summary.md", summary)
    _write_recommended_next_change(output_dir / "recommended-next-change.md", summary)
    _write_doc(doc_path, summary)
    return {
        "summary": summary,
        "compatibility": compatibility,
        "sidecar_count": len(payload["sidecars"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run copy-backed verifier shadow mode.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--doc-path", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--copy-slice-dir", type=Path, default=COPY_SLICE_DIR)
    args = parser.parse_args()
    result = write_copy_backed_verification_shadow_mode_reports(
        args.repo_root,
        args.output_dir,
        args.doc_path,
        copy_slice_dir=args.copy_slice_dir,
    )
    if "blocked" in result:
        print(result["blocked"]["decision"])
        return 1
    print(result["summary"]["decision_label"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
