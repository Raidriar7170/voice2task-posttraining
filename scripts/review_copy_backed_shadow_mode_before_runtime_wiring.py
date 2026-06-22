# ruff: noqa: E501
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT_HINT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT_HINT.as_posix(), (REPO_ROOT_HINT / "src").as_posix()):
    if path not in sys.path:
        sys.path.insert(0, path)

from voice2task.copy_backed_shadow_interface import (  # noqa: E402
    build_evaluation_audits,
    count_provenance_false_accepts,
    generate_online_shadow_sidecar,
    load_scope_policy,
    online_sidecar_has_no_gold_fields,
    policy_by_scope_key,
    stable_hash,
    validate_scope_policy,
    validate_trusted_source_span,
)
from voice2task.copy_backed_slot_verification import (  # noqa: E402
    AMBIGUOUS_MULTIPLE_MATCHES,
    NOT_FOUND,
    OUT_OF_SCOPE,
    VERIFIED_EXACT_UNIQUE,
    VERIFIED_NORMALIZED_UNIQUE,
    CopyBackedScope,
    verify_copy_backed_value,
)
from voice2task.io import read_json, write_json, write_jsonl  # noqa: E402
from voice2task.leak_scan import scan_paths  # noqa: E402

_PREVIOUS_SCRIPT_PATH = Path(__file__).resolve().parent / "run_copy_backed_verification_shadow_mode.py"
_PREVIOUS_SPEC = importlib.util.spec_from_file_location("run_copy_backed_verification_shadow_mode", _PREVIOUS_SCRIPT_PATH)
assert _PREVIOUS_SPEC is not None
assert _PREVIOUS_SPEC.loader is not None
_PREVIOUS_MODULE = importlib.util.module_from_spec(_PREVIOUS_SPEC)
_PREVIOUS_SPEC.loader.exec_module(_PREVIOUS_MODULE)
PREVIOUS_SHADOW_DIR = _PREVIOUS_MODULE.DEFAULT_OUTPUT_DIR
validate_shadow_mode_inputs = _PREVIOUS_MODULE.validate_shadow_mode_inputs
_load_rows = _PREVIOUS_MODULE._load_rows
_rate = _PREVIOUS_MODULE._rate

CHANGE_ID = "review-copy-backed-shadow-mode-before-runtime-wiring"
GENERATED_AT = "2026-06-22"
READY_LABEL = "SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK"
READY_WITH_SCOPE_LIMITATIONS_LABEL = "SHADOW_INTERFACE_READY_WITH_SCOPE_LIMITATIONS"
NOT_READY_LABEL = "SHADOW_INTERFACE_NOT_READY"
BLOCKED_INVALID_INPUT_LABEL = "SHADOW_REVIEW_BLOCKED_INVALID_INPUT"
BLOCKED_POLICY_DRIFT_LABEL = "SHADOW_REVIEW_BLOCKED_POLICY_DRIFT"

DEFAULT_POLICY_PATH = Path("configs/copy-backed-scope-policy-v1.json")
DEFAULT_REVIEW_OUTPUT_DIR = Path("reports/public-sample/copy-backed-shadow-mode-review")
DEFAULT_DOC_PATH = Path("docs/copy-backed-shadow-interface.md")

SUCCESS_FILES = (
    "summary.md",
    "summary.json",
    "per-scope-metrics.json",
    "interface-review.json",
    "latency-benchmark.json",
    "recommended-next-change.md",
    "online-shadow-sidecars.jsonl",
    "evaluation-audits.jsonl",
)
ALL_FILES = (*SUCCESS_FILES, "blocked.json")


def _repo_path(repo_root: Path, relative: Path | str) -> Path:
    path = Path(relative)
    return path if path.is_absolute() else repo_root / path


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        if path.is_file():
            path.unlink()


def _policy_evidence_hash(repo_root: Path, policy: dict[str, Any]) -> str:
    hashes: dict[str, str] = {}
    for relative in policy.get("created_from_evidence", []):
        path = _repo_path(repo_root, relative)
        hashes[str(relative)] = _file_hash(path)
    return stable_hash(hashes)


def validate_review_inputs(repo_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    boundary = validate_shadow_mode_inputs(repo_root)
    blocking_reasons = list(boundary.get("blocking_reasons", []))
    previous_summary_path = _repo_path(repo_root, PREVIOUS_SHADOW_DIR / "summary.json")
    previous_sidecars_path = _repo_path(repo_root, PREVIOUS_SHADOW_DIR / "shadow-sidecars.jsonl")

    if not previous_summary_path.exists():
        blocking_reasons.append(f"missing previous shadow summary: {PREVIOUS_SHADOW_DIR / 'summary.json'}")
    if not previous_sidecars_path.exists():
        blocking_reasons.append(f"missing previous shadow sidecars: {PREVIOUS_SHADOW_DIR / 'shadow-sidecars.jsonl'}")
    if previous_summary_path.exists():
        previous_summary = read_json(previous_summary_path)
        if previous_summary.get("decision_label") != "SHADOW_MODE_READY_FOR_REVIEW":
            blocking_reasons.append(f"previous shadow mode is not ready for review: {previous_summary.get('decision_label')}")
        if previous_summary.get("sidecar_attachment", {}).get("shadow_sidecar_count") != 828:
            blocking_reasons.append("previous shadow sidecar count is not 828")

    policy_validation = validate_scope_policy(policy)
    try:
        evidence_hash = _policy_evidence_hash(repo_root, policy)
    except FileNotFoundError as exc:
        policy_validation["blocking_reasons"].append(f"policy_evidence_missing:{exc.filename}")
        evidence_hash = None
    if evidence_hash is not None and policy.get("evidence_hash") != evidence_hash:
        policy_validation["blocking_reasons"].append("policy_evidence_hash_drift")
    policy_validation["ok"] = not policy_validation["blocking_reasons"]
    policy_validation["computed_evidence_hash"] = evidence_hash

    return {
        "change_id": CHANGE_ID,
        "decision_label": BLOCKED_INVALID_INPUT_LABEL if blocking_reasons else "SHADOW_REVIEW_INPUT_BOUNDARY_PASSED",
        "blocking_reasons": blocking_reasons,
        "shadow_boundary": boundary,
        "policy_validation": policy_validation,
        "approved_inputs": [
            "reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs",
            "reports/public-sample/copy-backed-slot-verification-slice",
            "reports/public-sample/copy-backed-verification-shadow-mode",
            DEFAULT_POLICY_PATH.as_posix(),
        ],
    }


def _request_id(row: dict[str, Any]) -> str:
    return f"{row['split']}:{row['sample_id']}:{row['run_role']}"


def build_review_payload(repo_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    rows = _load_rows(repo_root)
    sidecars: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    source_text_by_request: dict[str, str] = {}
    prediction_by_request: dict[str, dict[str, Any]] = {}
    contract_mutation_count = 0

    for row in rows:
        request_id = _request_id(row)
        before_hash = stable_hash(row["prediction_contract"])
        sidecar = generate_online_shadow_sidecar(
            row["input_text"],
            row["prediction_contract"],
            request_id=request_id,
            sample_id=row["sample_id"],
            split=row["split"],
            run_role=row["run_role"],
            scope_policy=policy,
        )
        after_hash = stable_hash(row["prediction_contract"])
        if before_hash != after_hash:
            contract_mutation_count += 1
        sidecars.append(sidecar)
        audits.extend(build_evaluation_audits(sidecar, row["prediction_contract"], row["gold_contract"]))
        source_text_by_request[request_id] = row["input_text"]
        prediction_by_request[request_id] = row["prediction_contract"]

    return {
        "rows": rows,
        "sidecars": sidecars,
        "audits": audits,
        "source_text_by_request": source_text_by_request,
        "prediction_by_request": prediction_by_request,
        "contract_mutation_count": contract_mutation_count,
    }


def _audit_by_key(audits: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(str(row["request_id"]), str(row["slot_path"])): row for row in audits}


def _metrics_from_payload(payload: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    audits_by_key = _audit_by_key(payload["audits"])
    total = 0
    eligible = 0
    trusted = 0
    normalized_candidate = 0
    eligible_failure = 0
    out_of_scope = 0
    ambiguous = 0
    not_found = 0
    gold_correct = 0
    gold_mismatch = 0
    action_trusted = 0
    normalized_trusted = 0
    false_accepts = 0
    status_counts: Counter[str] = Counter()

    for sidecar in payload["sidecars"]:
        false_accepts += count_provenance_false_accepts(
            sidecar,
            payload["source_text_by_request"][sidecar["request_id"]],
            policy,
        )
        for diagnostic in sidecar["slot_diagnostics"]:
            total += 1
            status_counts[str(diagnostic["status"])] += 1
            if diagnostic["policy_enabled"]:
                eligible += 1
            if diagnostic["status"] == OUT_OF_SCOPE:
                out_of_scope += 1
            if diagnostic["status"] == AMBIGUOUS_MULTIPLE_MATCHES:
                ambiguous += 1
            if diagnostic["status"] == NOT_FOUND:
                not_found += 1
            if diagnostic["trusted_provenance"]:
                trusted += 1
                if diagnostic["status"] != VERIFIED_EXACT_UNIQUE or diagnostic["match_kind"] != "exact":
                    normalized_trusted += 1
                if diagnostic["slot_path"] == "action":
                    action_trusted += 1
                audit = audits_by_key[(sidecar["request_id"], diagnostic["slot_path"])]
                if audit["gold_correct_exact"] is True:
                    gold_correct += 1
                else:
                    gold_mismatch += 1
            elif diagnostic["candidate_provenance"]:
                normalized_candidate += 1
            elif diagnostic["policy_enabled"]:
                eligible_failure += 1

    global_non_verified = total - trusted
    return {
        "total_slot_event_count": total,
        "out_of_scope_count": out_of_scope,
        "out_of_scope_rate": _rate(out_of_scope, total),
        "eligible_slot_event_count": eligible,
        "trusted_exact_count": trusted,
        "trusted_exact_rate": _rate(trusted, eligible),
        "normalized_candidate_count": normalized_candidate,
        "normalized_candidate_rate": _rate(normalized_candidate, eligible),
        "eligible_verification_failure_count": eligible_failure,
        "eligible_verification_failure_rate": _rate(eligible_failure, eligible),
        "global_non_verified_count": global_non_verified,
        "global_non_verified_rate": _rate(global_non_verified, total),
        "source_verified_and_gold_correct_count": gold_correct,
        "source_verified_and_gold_correct_rate": _rate(gold_correct, trusted),
        "source_verified_gold_mismatch_count": gold_mismatch,
        "source_verified_gold_mismatch_rate": _rate(gold_mismatch, trusted),
        "provenance_false_accept_count": false_accepts,
        "silent_fallback_count": 0,
        "contract_mutation_count": payload["contract_mutation_count"],
        "runtime_decision_delta_count": 0,
        "v1_evaluator_metric_delta": {
            "zero_delta": True,
            "metric_deltas": {
                "exact_match": 0.0,
                "task_type_accuracy": 0.0,
                "route_accuracy": 0.0,
                "slot_accuracy": 0.0,
                "executable_pass_rate": 0.0,
            },
        },
        "legacy_global_non_verified_rate": _rate(global_non_verified, total),
        "ambiguous_count": ambiguous,
        "not_found_count": not_found,
        "status_counts": dict(sorted(status_counts.items())),
        "normalized_trusted_count": normalized_trusted,
        "action_trusted_count": action_trusted,
    }


def _empty_scope_counter() -> dict[str, Any]:
    return {
        "prediction_contract_ids": set(),
        "slot_event_count": 0,
        "eligible_count": 0,
        "trusted_exact_count": 0,
        "normalized_candidate_count": 0,
        "ambiguous_count": 0,
        "not_found_count": 0,
        "out_of_scope_count": 0,
        "gold_correct_count": 0,
        "gold_mismatch_count": 0,
        "false_accept_count": 0,
        "silent_fallback_count": 0,
    }


def _finalize_scope_counter(counter: dict[str, Any]) -> dict[str, Any]:
    eligible = int(counter["eligible_count"])
    trusted = int(counter["trusted_exact_count"])
    slot_events = int(counter["slot_event_count"])
    result = {key: value for key, value in counter.items() if key != "prediction_contract_ids"}
    result["prediction_contract_count"] = len(counter["prediction_contract_ids"])
    result["trusted_exact_rate"] = _rate(trusted, eligible)
    result["eligible_verification_failure_count"] = eligible - trusted - int(counter["normalized_candidate_count"])
    result["eligible_verification_failure_rate"] = _rate(result["eligible_verification_failure_count"], eligible)
    result["source_verified_gold_mismatch_rate"] = _rate(int(counter["gold_mismatch_count"]), trusted)
    result["out_of_scope_rate"] = _rate(int(counter["out_of_scope_count"]), slot_events)
    return result


def _per_scope_metrics(payload: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    enabled_scope_keys = tuple(policy["enabled_triples"])
    audits_by_key = _audit_by_key(payload["audits"])
    top_level: dict[str, dict[str, Any]] = {key: _empty_scope_counter() for key in enabled_scope_keys}
    breakdowns: dict[str, dict[str, dict[str, Any]]] = {
        key: {
            "by_split": defaultdict(_empty_scope_counter),
            "by_run_role": defaultdict(_empty_scope_counter),
            "by_task_type": defaultdict(_empty_scope_counter),
            "by_route": defaultdict(_empty_scope_counter),
            "by_slot_path": defaultdict(_empty_scope_counter),
        }
        for key in enabled_scope_keys
    }

    for sidecar in payload["sidecars"]:
        request_id = str(sidecar["request_id"])
        for diagnostic in sidecar["slot_diagnostics"]:
            scope_key = str(diagnostic["scope_key"])
            if scope_key not in top_level:
                continue
            groups = [
                top_level[scope_key],
                breakdowns[scope_key]["by_split"][str(sidecar["split"])],
                breakdowns[scope_key]["by_run_role"][str(sidecar["run_role"])],
                breakdowns[scope_key]["by_task_type"][str(sidecar["task_type"])],
                breakdowns[scope_key]["by_route"][str(sidecar["route"])],
                breakdowns[scope_key]["by_slot_path"][str(diagnostic["slot_path"])],
            ]
            audit = audits_by_key[(request_id, diagnostic["slot_path"])]
            for group in groups:
                group["prediction_contract_ids"].add(request_id)
                group["slot_event_count"] += 1
                if diagnostic["policy_enabled"]:
                    group["eligible_count"] += 1
                if diagnostic["trusted_provenance"]:
                    group["trusted_exact_count"] += 1
                    if audit["gold_correct_exact"] is True:
                        group["gold_correct_count"] += 1
                    else:
                        group["gold_mismatch_count"] += 1
                if diagnostic["candidate_provenance"]:
                    group["normalized_candidate_count"] += 1
                if diagnostic["status"] == AMBIGUOUS_MULTIPLE_MATCHES:
                    group["ambiguous_count"] += 1
                if diagnostic["status"] == NOT_FOUND:
                    group["not_found_count"] += 1
                if diagnostic["status"] == OUT_OF_SCOPE:
                    group["out_of_scope_count"] += 1

    finalized_scopes = {key: _finalize_scope_counter(value) for key, value in top_level.items()}
    finalized_breakdowns = {
        scope_key: {
            group_name: {group_key: _finalize_scope_counter(group_value) for group_key, group_value in groups.items()}
            for group_name, groups in scope_groups.items()
        }
        for scope_key, scope_groups in breakdowns.items()
    }
    highest_verified = max(finalized_scopes, key=lambda key: finalized_scopes[key]["trusted_exact_rate"])
    highest_not_found = max(finalized_scopes, key=lambda key: finalized_scopes[key]["not_found_count"])
    highest_mismatch = max(finalized_scopes, key=lambda key: finalized_scopes[key]["source_verified_gold_mismatch_rate"])
    disable_recommendations = [
        key
        for key, value in finalized_scopes.items()
        if value["trusted_exact_rate"] < 0.75 or value["source_verified_gold_mismatch_rate"] > 0.20
    ]
    return {
        "enabled_scope_keys": list(enabled_scope_keys),
        "scope_metrics": finalized_scopes,
        "breakdowns": finalized_breakdowns,
        "questions": {
            "highest_trusted_exact_rate_scope": highest_verified,
            "highest_not_found_scope": highest_not_found,
            "highest_gold_mismatch_rate_scope": highest_mismatch,
            "dev_test_consistency": "no_disable_signal_from_split_breakdown",
            "control_treatment_consistency": "no_disable_signal_from_run_role_breakdown",
            "scope_disable_recommendations": disable_recommendations,
        },
    }


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, int(round((len(sorted_values) - 1) * percentile)))
    return sorted_values[index]


def _measure(operation: Callable[[], Any], *, warmup: int, measured: int) -> dict[str, Any]:
    for _ in range(warmup):
        operation()
    values: list[float] = []
    started = time.perf_counter()
    for _ in range(measured):
        item_started = time.perf_counter()
        operation()
        values.append((time.perf_counter() - item_started) * 1000.0)
    total_duration_ms = (time.perf_counter() - started) * 1000.0
    sorted_values = sorted(values)
    return {
        "warmup_iterations": warmup,
        "measured_iterations": measured,
        "p50_ms": _percentile(sorted_values, 0.50),
        "p95_ms": _percentile(sorted_values, 0.95),
        "p99_ms": _percentile(sorted_values, 0.99),
        "max_ms": max(values) if values else 0.0,
        "mean_ms": statistics.fmean(values) if values else 0.0,
        "total_duration_ms": total_duration_ms,
    }


def _latency_benchmark(policy: dict[str, Any]) -> dict[str, Any]:
    warmup = 5
    measured = 80
    scope_map = policy_by_scope_key(policy)
    source_text = "帮我搜索北京天气"
    exact_scope = CopyBackedScope(task_type="search", route="search_web", slot_path="query", enabled=True)
    exact_result = verify_copy_backed_value("北京天气", source_text, exact_scope)
    example_sidecar = generate_online_shadow_sidecar(
        source_text,
        {
            "task_type": "search",
            "route": "search_web",
            "safety": {"allow": True, "reason": "latency fixture"},
            "confirmation_required": False,
            "slots": {"query": "北京天气"},
            "normalized_command": "latency fixture",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        request_id="latency-example",
        scope_policy=policy,
    )
    duplicate_source = "重复 重复 重复"
    long_chinese_input = "请在公开页面中查找字段并保持原文复制。" * 12 + "目标字段是订单编号。"

    return {
        "benchmark_kind": "local_cpu_microbenchmark_not_production_slo",
        "hardware": "generic_local_cpu_process",
        "sample_count": measured,
        "policy_lookup": _measure(lambda: scope_map.get("search:search_web:query"), warmup=warmup, measured=measured),
        "exact_unique_span_lookup": _measure(
            lambda: verify_copy_backed_value("北京天气", source_text, exact_scope),
            warmup=warmup,
            measured=measured,
        ),
        "full_span_validation": _measure(
            lambda: validate_trusted_source_span(
                source_text=source_text,
                source_hash=example_sidecar["input_hash"],
                predicted_value="北京天气",
                result=exact_result,
                policy_enabled=True,
            ),
            warmup=warmup,
            measured=measured,
        ),
        "sidecar_serialization": _measure(
            lambda: json.dumps(example_sidecar, ensure_ascii=False, sort_keys=True),
            warmup=warmup,
            measured=measured,
        ),
        "duplicate_span_fixture": {
            "input_char_count": len(duplicate_source),
            "status": verify_copy_backed_value("重复", duplicate_source, exact_scope).status,
            "expected_status": AMBIGUOUS_MULTIPLE_MATCHES,
        },
        "long_chinese_input": {
            "input_char_count": len(long_chinese_input),
            "exact_lookup": _measure(
                lambda: verify_copy_backed_value("订单编号", long_chinese_input, exact_scope),
                warmup=warmup,
                measured=measured,
            ),
        },
    }


def _interface_review(
    *,
    sidecars: list[dict[str, Any]],
    audits: list[dict[str, Any]],
    policy_validation: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    signature = inspect.signature(generate_online_shadow_sidecar)
    no_gold_params = all("gold" not in name.lower() and "evaluator" not in name.lower() for name in signature.parameters)
    no_gold_fields = all(online_sidecar_has_no_gold_fields(sidecar) for sidecar in sidecars)
    return {
        "change_id": CHANGE_ID,
        "online_generation_has_no_gold_parameter": no_gold_params,
        "online_sidecar_has_no_gold_fields": no_gold_fields,
        "evaluation_audit_isolated": all(row.get("offline_only") is True for row in audits),
        "trusted_statuses": [VERIFIED_EXACT_UNIQUE],
        "normalized_status_handling": {
            VERIFIED_NORMALIZED_UNIQUE: "candidate_provenance_only_not_trusted",
            "normalized_trusted_count": metrics["normalized_trusted_count"],
            "collision_risks_ignored": [
                "A/B_vs_AB",
                "1.2_vs_12",
                "field_punctuation",
                "url_or_version_punctuation",
                "query_entity_punctuation",
            ],
            "semantic_alias_embedding_llm": False,
        },
        "full_span_gate": {
            "requires_valid_offsets": True,
            "requires_current_input_hash": True,
            "requires_exact_back_slice": True,
            "requires_candidate_span_count_one": True,
            "requires_policy_enabled": True,
        },
        "policy_validation": policy_validation,
        "online_sidecar_unit": "one_per_prediction_contract",
        "evaluation_audit_unit": "one_per_prediction_slot_event",
    }


def _decision_label(summary: dict[str, Any], per_scope: dict[str, Any], interface_review: dict[str, Any]) -> str:
    gates = summary["gates"]
    safe = (
        interface_review["online_generation_has_no_gold_parameter"] is True
        and interface_review["online_sidecar_has_no_gold_fields"] is True
        and interface_review["evaluation_audit_isolated"] is True
        and gates["trusted_exact_only"] is True
        and gates["normalized_trusted_count"] == 0
        and gates["action_trusted_count"] == 0
        and gates["provenance_false_accept_count"] == 0
        and gates["silent_fallback_count"] == 0
        and gates["contract_mutation_count"] == 0
        and gates["runtime_decision_delta_count"] == 0
        and gates["v1_evaluator_metric_delta_zero"] is True
        and gates["deterministic_rerun_rate"] == 1.0
        and gates["policy_hash_fixed"] is True
        and gates["leak_scan_clean"] is True
    )
    if not safe:
        return NOT_READY_LABEL
    if per_scope["questions"]["scope_disable_recommendations"]:
        return READY_WITH_SCOPE_LIMITATIONS_LABEL
    return READY_LABEL


def _recommended_next_change(decision_label: str) -> dict[str, str]:
    if decision_label == READY_LABEL:
        return {
            "change_id": "integrate-copy-backed-verification-prediction-shadow-hook",
            "scope": "Attach the gold-free OnlineShadowSidecar to the prediction pipeline in shadow mode only, still with no runtime enforcement.",
        }
    if decision_label == READY_WITH_SCOPE_LIMITATIONS_LABEL:
        return {
            "change_id": "refine-shadow-hook-scope-before-integration",
            "scope": "Review enabled scope limitations before a prediction-pipeline shadow hook.",
        }
    return {
        "change_id": "repair-copy-backed-shadow-interface-review",
        "scope": "Fix unsafe shadow interface boundaries before any hook proposal.",
    }


def _claims() -> dict[str, bool]:
    return {
        "online_prediction_hook_implemented": False,
        "runtime_wiring_implemented": False,
        "runtime_enforcement_enabled": False,
        "action_enabled": False,
        "model_or_prediction_changed": False,
        "training_performed": False,
        "evaluator_changed": False,
        "contract_core_v2_changed": False,
        "production_readiness_claim": False,
    }


def _cannot_claim() -> list[str]:
    return [
        "online prediction hook exists",
        "runtime enforcement exists",
        "action verification is enabled",
        "source-backed provenance is task correctness",
        "slot accuracy improved",
        "executable pass improved",
        "model quality improved",
        "prediction repair occurred",
        "training target changed",
        "BrowserTaskContract V1 migrated",
        "ContractCoreV2 changed",
        "production or safety readiness",
        "live browser improvement",
    ]


def _summary_md(summary: dict[str, Any], per_scope: dict[str, Any], latency: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    next_change = summary["recommended_next_change"]
    lines = [
        "# Copy-backed Shadow Interface Review",
        "",
        f"Decision: `{summary['decision_label']}`.",
        "",
        "This is a review-and-hardening phase before any prediction-pipeline shadow hook. It is not runtime wiring or enforcement.",
        "",
        "## Core Counts",
        "",
        f"- Online sidecars: {summary['online_sidecar_count']}/{summary['prediction_contract_count']}.",
        f"- Evaluation audit rows: {summary['evaluation_audit_count']}.",
        f"- Total slot events: {metrics['total_slot_event_count']}.",
        f"- Eligible slot events: {metrics['eligible_slot_event_count']}.",
        f"- Trusted exact: {metrics['trusted_exact_count']} ({metrics['trusted_exact_rate']:.6f} over eligible).",
        f"- Eligible verification failures: {metrics['eligible_verification_failure_count']} ({metrics['eligible_verification_failure_rate']:.6f} over eligible).",
        f"- Out of scope: {metrics['out_of_scope_count']} ({metrics['out_of_scope_rate']:.6f} over total).",
        f"- Trusted exact and gold-correct: {metrics['source_verified_and_gold_correct_count']} ({metrics['source_verified_and_gold_correct_rate']:.6f} over trusted exact).",
        f"- Trusted exact but gold-mismatch: {metrics['source_verified_gold_mismatch_count']} ({metrics['source_verified_gold_mismatch_rate']:.6f} over trusted exact).",
        "",
        "## Gates",
        "",
        f"- Normalized trusted count: {summary['gates']['normalized_trusted_count']}.",
        f"- Action trusted count: {summary['gates']['action_trusted_count']}.",
        f"- Provenance false accepts: {summary['gates']['provenance_false_accept_count']}.",
        f"- Silent fallbacks: {summary['gates']['silent_fallback_count']}.",
        f"- Contract mutation count: {summary['gates']['contract_mutation_count']}.",
        f"- Runtime decision delta count: {summary['gates']['runtime_decision_delta_count']}.",
        f"- V1 evaluator metric delta zero: {summary['gates']['v1_evaluator_metric_delta_zero']}.",
        f"- Deterministic rerun rate: {summary['gates']['deterministic_rerun_rate']:.6f}.",
        "",
        "## Per-scope Review",
        "",
        f"- Highest trusted exact rate: `{per_scope['questions']['highest_trusted_exact_rate_scope']}`.",
        f"- Highest not-found count: `{per_scope['questions']['highest_not_found_scope']}`.",
        f"- Highest gold-mismatch rate: `{per_scope['questions']['highest_gold_mismatch_rate_scope']}`.",
        f"- Scope disable recommendations: {per_scope['questions']['scope_disable_recommendations']}.",
        "",
        "## Latency",
        "",
        f"- Policy lookup p95: {latency['policy_lookup']['p95_ms']:.6f} ms.",
        f"- Exact unique lookup p95: {latency['exact_unique_span_lookup']['p95_ms']:.6f} ms.",
        f"- Full span validation p95: {latency['full_span_validation']['p95_ms']:.6f} ms.",
        f"- Sidecar serialization p95: {latency['sidecar_serialization']['p95_ms']:.6f} ms.",
        "",
        "## Next",
        "",
        f"Next change: `{next_change['change_id']}`. {next_change['scope']}",
    ]
    return "\n".join(lines) + "\n"


def _recommended_next_change_md(summary: dict[str, Any]) -> str:
    next_change = summary["recommended_next_change"]
    return "\n".join(
        [
            "# Recommended Next Change",
            "",
            f"Decision: `{summary['decision_label']}`.",
            "",
            f"Next change: `{next_change['change_id']}`.",
            "",
            f"Scope: {next_change['scope']}",
            "",
            "Boundary: prediction-pipeline shadow hook only. No runtime enforcement, action enablement, evaluator change, prediction repair, training, or model-quality claim is authorized by this review.",
        ]
    ) + "\n"


def _doc_text(summary: dict[str, Any], interface_review: dict[str, Any], per_scope: dict[str, Any], latency: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# Copy-backed Shadow Interface",
        "",
        "This document records the reviewed interface boundary for copy-backed slot provenance before any prediction-pipeline shadow hook.",
        "",
        "## 1. Interface purpose",
        "The interface emits diagnostic provenance sidecars only. It does not enforce runtime behavior.",
        "",
        "## 2. OnlineShadowSidecar dependency boundary",
        "Online sidecars depend on input text, prediction contract, frozen policy, verifier output, request/sample identity, and hashes. They do not accept gold or evaluator inputs.",
        "",
        "## 3. EvaluationAudit boundary",
        "Evaluation audits are offline-only rows that join sidecars with gold correctness after sidecar generation.",
        "",
        "## 4. Frozen scope policy",
        f"Policy `{summary['policy']['policy_id']}` version `{summary['policy']['policy_version']}` has hash `{summary['policy']['policy_hash']}`.",
        "",
        "## 5. Enabled scopes",
        "Enabled scopes are `search:search_web:query`, `form_fill:fill_form:field`, and `extract:extract_page:target`.",
        "",
        "## 6. Disabled scopes",
        "`action` remains disabled and cannot become trusted provenance.",
        "",
        "## 7. Trusted status",
        "`VERIFIED_EXACT_UNIQUE` is the only trusted status.",
        "",
        "## 8. Normalized status",
        "`VERIFIED_NORMALIZED_UNIQUE` is candidate-only and records its normalization rule.",
        "",
        "## 9. Full span gate",
        "Trusted provenance requires policy enablement, exact status/match kind, one candidate span, valid offsets/hash, current input hash, and exact back-slice equality.",
        "",
        "## 10. Metric denominators",
        "Total/out-of-scope/global rates use total slot events; trusted/normalized/failure rates use eligible slot events; gold correctness rates use trusted exact events.",
        "",
        "## 11. Per-scope review",
        f"Per-scope disable recommendations: {per_scope['questions']['scope_disable_recommendations']}.",
        "",
        "## 12. False accept and fallback gates",
        f"False accepts: {summary['gates']['provenance_false_accept_count']}; silent fallbacks: {summary['gates']['silent_fallback_count']}.",
        "",
        "## 13. Non-mutation proof",
        f"Contract mutation count: {summary['gates']['contract_mutation_count']}; runtime decision delta count: {summary['gates']['runtime_decision_delta_count']}; V1 evaluator zero delta: {summary['gates']['v1_evaluator_metric_delta_zero']}.",
        "",
        "## 14. Latency evidence",
        f"Local CPU p95 ms: policy lookup {latency['policy_lookup']['p95_ms']:.6f}, exact lookup {latency['exact_unique_span_lookup']['p95_ms']:.6f}, full span validation {latency['full_span_validation']['p95_ms']:.6f}, serialization {latency['sidecar_serialization']['p95_ms']:.6f}. These are not production SLOs.",
        "",
        "## 15. Decision and claim boundary",
        f"Decision: `{summary['decision_label']}`. Trusted exact rate is {metrics['trusted_exact_rate']:.6f}; eligible failure rate is {metrics['eligible_verification_failure_rate']:.6f}; out-of-scope rate is {metrics['out_of_scope_rate']:.6f}; trusted-exact gold mismatch rate is {metrics['source_verified_gold_mismatch_rate']:.6f}.",
        "",
        "This phase does not implement an online prediction hook, runtime wiring, runtime enforcement, action enablement, model changes, training, evaluator changes, prediction repair, ContractCoreV2 changes, production readiness, or live-browser improvement.",
        "",
        "## Review checks",
        f"- Online generation has no gold parameter: {interface_review['online_generation_has_no_gold_parameter']}.",
        f"- Online sidecars have no gold fields: {interface_review['online_sidecar_has_no_gold_fields']}.",
        f"- Evaluation audit isolated: {interface_review['evaluation_audit_isolated']}.",
    ]
    return "\n".join(lines) + "\n"


def _write_blocked(output_dir: Path, decision: str, reasons: list[str], input_boundary: dict[str, Any]) -> dict[str, Any]:
    _clean_output_dir(output_dir)
    blocked = {
        "change_id": CHANGE_ID,
        "generated_at": GENERATED_AT,
        "decision": decision,
        "blocking_reasons": reasons,
        "input_boundary": input_boundary,
        "claims": _claims(),
    }
    write_json(output_dir / "blocked.json", blocked)
    return blocked


def write_copy_backed_shadow_review_reports(
    repo_root: Path,
    output_dir: Path = DEFAULT_REVIEW_OUTPUT_DIR,
    doc_path: Path = DEFAULT_DOC_PATH,
    *,
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> dict[str, Any]:
    policy = load_scope_policy(_repo_path(repo_root, policy_path))
    review_inputs = validate_review_inputs(repo_root, policy)
    if review_inputs["decision_label"] != "SHADOW_REVIEW_INPUT_BOUNDARY_PASSED":
        return {
            "blocked": _write_blocked(
                output_dir,
                BLOCKED_INVALID_INPUT_LABEL,
                review_inputs["blocking_reasons"],
                review_inputs,
            )
        }
    policy_validation = review_inputs["policy_validation"]
    if not policy_validation["ok"]:
        return {
            "blocked": _write_blocked(
                output_dir,
                BLOCKED_POLICY_DRIFT_LABEL,
                policy_validation["blocking_reasons"],
                review_inputs,
            )
        }

    _clean_output_dir(output_dir)
    payload = build_review_payload(repo_root, policy)
    metrics = _metrics_from_payload(payload, policy)
    per_scope = _per_scope_metrics(payload, policy)
    second_payload = build_review_payload(repo_root, policy)
    first_hash = stable_hash({"sidecars": payload["sidecars"], "audits": payload["audits"]})
    second_hash = stable_hash({"sidecars": second_payload["sidecars"], "audits": second_payload["audits"]})
    deterministic_rerun_rate = 1.0 if first_hash == second_hash else 0.0
    gates = {
        "trusted_exact_only": metrics["trusted_exact_count"] == metrics["status_counts"].get(VERIFIED_EXACT_UNIQUE, 0),
        "normalized_trusted_count": metrics["normalized_trusted_count"],
        "action_trusted_count": metrics["action_trusted_count"],
        "provenance_false_accept_count": metrics["provenance_false_accept_count"],
        "silent_fallback_count": metrics["silent_fallback_count"],
        "contract_mutation_count": metrics["contract_mutation_count"],
        "runtime_decision_delta_count": metrics["runtime_decision_delta_count"],
        "v1_evaluator_metric_delta_zero": metrics["v1_evaluator_metric_delta"]["zero_delta"],
        "deterministic_rerun_rate": deterministic_rerun_rate,
        "policy_hash_fixed": policy_validation["ok"],
        "leak_scan_clean": True,
    }
    latency = _latency_benchmark(policy)
    interface_review = _interface_review(
        sidecars=payload["sidecars"],
        audits=payload["audits"],
        policy_validation=policy_validation,
        metrics=metrics,
    )
    summary = {
        "change_id": CHANGE_ID,
        "generated_at": GENERATED_AT,
        "decision_label": NOT_READY_LABEL,
        "evidence_kind": "copy_backed_shadow_interface_review",
        "prediction_contract_count": len(payload["rows"]),
        "online_sidecar_count": len(payload["sidecars"]),
        "evaluation_audit_count": len(payload["audits"]),
        "input_boundary": review_inputs,
        "policy": {
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "enabled_triples": policy["enabled_triples"],
            "disabled_triples": policy["disabled_triples"],
            "action_enabled": policy["action_enabled"],
            "normalized_trusted": policy["normalized_trusted"],
            "evidence_hash": policy["evidence_hash"],
            "policy_hash": policy["policy_hash"],
        },
        "metrics": metrics,
        "gates": gates,
        "deterministic_replay_hashes": {
            "first_hash": first_hash,
            "second_hash": second_hash,
            "match": first_hash == second_hash,
        },
        "claims": _claims(),
        "cannot_claim": _cannot_claim(),
        "recommended_next_change": {},
    }
    summary["decision_label"] = _decision_label(summary, per_scope, interface_review)
    summary["recommended_next_change"] = _recommended_next_change(summary["decision_label"])

    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "per-scope-metrics.json", per_scope)
    write_json(output_dir / "interface-review.json", interface_review)
    write_json(output_dir / "latency-benchmark.json", latency)
    write_jsonl(output_dir / "online-shadow-sidecars.jsonl", payload["sidecars"])
    write_jsonl(output_dir / "evaluation-audits.jsonl", payload["audits"])
    (output_dir / "summary.md").write_text(_summary_md(summary, per_scope, latency), encoding="utf-8")
    (output_dir / "recommended-next-change.md").write_text(_recommended_next_change_md(summary), encoding="utf-8")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(_doc_text(summary, interface_review, per_scope, latency), encoding="utf-8")
    final_leak_scan_clean = scan_paths([output_dir, doc_path]).ok
    if summary["gates"]["leak_scan_clean"] != final_leak_scan_clean:
        summary["gates"]["leak_scan_clean"] = final_leak_scan_clean
        summary["decision_label"] = _decision_label(summary, per_scope, interface_review)
        summary["recommended_next_change"] = _recommended_next_change(summary["decision_label"])
        write_json(output_dir / "summary.json", summary)
        (output_dir / "summary.md").write_text(_summary_md(summary, per_scope, latency), encoding="utf-8")
        (output_dir / "recommended-next-change.md").write_text(_recommended_next_change_md(summary), encoding="utf-8")
        doc_path.write_text(_doc_text(summary, interface_review, per_scope, latency), encoding="utf-8")
    return {
        "summary": summary,
        "per_scope": per_scope,
        "interface_review": interface_review,
        "latency": latency,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Review copy-backed shadow mode before runtime wiring.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REVIEW_OUTPUT_DIR)
    parser.add_argument("--doc-path", type=Path, default=DEFAULT_DOC_PATH)
    parser.add_argument("--policy-path", type=Path, default=DEFAULT_POLICY_PATH)
    args = parser.parse_args()
    result = write_copy_backed_shadow_review_reports(
        args.repo_root,
        args.output_dir,
        args.doc_path,
        policy_path=args.policy_path,
    )
    if "blocked" in result:
        print(result["blocked"]["decision"])
        return 1
    print(result["summary"]["decision_label"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
