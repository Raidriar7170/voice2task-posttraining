# ruff: noqa: E501
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

CHANGE_ID = "design-hybrid-slot-representation-v1"
INPUT_BOUNDARY_PASSED = "HYBRID_DESIGN_INPUT_BOUNDARY_PASSED"
INPUT_BOUNDARY_BLOCKED = "DESIGN_BLOCKED_INVALID_INPUT"
DECISION_COPY_SLICE_FIRST = "HYBRID_DESIGN_READY_COPY_SLICE_FIRST"

RAW_INPUTS = Path("reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs")
SLOT_ANALYSIS = Path("reports/public-sample/slot-error-mechanism-analysis")
INTERNAL_CORE = Path("reports/public-sample/internal-contract-v2-core/summary.json")
DEFAULT_OUTPUT_DIR = Path("reports/public-sample/hybrid-slot-representation-v1")
DEFAULT_DOC_PATH = Path("docs/hybrid-slot-representation-v1.md")

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
REPORT_FILES = (
    "summary.md",
    "summary.json",
    "representation-matrix.json",
    "feasibility-projection.json",
    "recommended-next-change.md",
    "blocked.json",
)

MODEL_TARGET_COMPARISON = [
    {
        "option": "A",
        "name": "model_outputs_value_system_verifies_span",
        "recommendation": "primary",
        "chinese_asr_stability": "highest; value text survives minor transcript formatting changes better than offsets",
        "learning_difficulty": "lowest for current V1-style generative target",
        "json_complexity": "low",
        "verifiability": "high when deterministic verifier can attach a unique span; ambiguous duplicates remain unresolved",
        "duplicate_text_risk": "system must fail closed or request disambiguation when multiple identical spans exist",
        "current_7b_fit": "best fit because current model already emits V1 slot values",
        "v1_compatibility": "best; no target migration required",
    },
    {
        "option": "B",
        "name": "model_outputs_candidate_source_snippet_system_resolves_offset",
        "recommendation": "fallback_for_approved_copy_heavy_slots",
        "chinese_asr_stability": "medium; snippets can drift with ASR punctuation or spacing",
        "learning_difficulty": "medium",
        "json_complexity": "medium",
        "verifiability": "medium; snippet remains untrusted until exact offset validation succeeds",
        "duplicate_text_risk": "higher than value-only unless candidate context is added",
        "current_7b_fit": "usable only as a narrowed fallback",
        "v1_compatibility": "requires additional internal candidate pointer metadata",
    },
    {
        "option": "C",
        "name": "model_outputs_start_end_offsets",
        "recommendation": "rejected_for_v1",
        "chinese_asr_stability": "lowest; offsets are brittle under transcript edits",
        "learning_difficulty": "highest for current 7B generative model",
        "json_complexity": "high",
        "verifiability": "high after output, but invalid offsets are common failure modes",
        "duplicate_text_risk": "low if offsets are correct, but correctness is hard to learn",
        "current_7b_fit": "poor without a new target and focused training",
        "v1_compatibility": "weak; requires target migration",
    },
]

FIELD_DEFINITIONS = [
    {
        "name": "value",
        "owner": "model",
        "description": "V1-compatible slot value or bounded structured value authored by the model.",
    },
    {
        "name": "value_type",
        "owner": "system",
        "description": "Coarse type derived from the value: text, number, boolean, object, list, null, or unknown.",
    },
    {
        "name": "representation_kind",
        "owner": "system",
        "description": "Primary representation strategy selected from evidence and task scope.",
    },
    {
        "name": "source_span",
        "owner": "system",
        "description": "Optional verifier-owned source slice containing start, end, text, and source_text_hash.",
    },
    {
        "name": "normalization_rule",
        "owner": "system",
        "description": "Optional allowlisted deterministic normalization rule applied after source back-slice validation.",
    },
    {
        "name": "verification_status",
        "owner": "system",
        "description": "Verifier result: verified, unsupported, or unresolved.",
    },
    {
        "name": "provenance",
        "owner": "system",
        "description": "Verifier provenance: source_verified, deterministic_derived, schema_constrained, structured_generated, free_generated, or unknown.",
    },
    {
        "name": "fallback_behavior",
        "owner": "system",
        "description": "Fail-closed outcome: emit_v1_value, fail_closed, clarify, diagnostic_only, or resolver_required.",
    },
]

SOURCE_SPAN_SEMANTICS = {
    "source_basis": "original_input_text_or_fixed_sanitized_transcript",
    "offset_unit": "unicode_character",
    "start": "inclusive",
    "end": "exclusive",
    "requires_source_text_hash": True,
    "requires_exact_back_slice": True,
    "allows_similarity_only": False,
    "allows_discontiguous_span": False,
}

CLAIMS = {
    "training_performed": False,
    "prediction_rerun_performed": False,
    "data_mutation_performed": False,
    "schema_migration_performed": False,
    "contract_core_v2_changed": False,
    "evaluator_relaxation_performed": False,
    "runtime_integration_performed": False,
    "model_improvement_claim": False,
    "slot_performance_improvement_claim": False,
    "executable_quality_improvement_claim": False,
    "production_readiness_claim": False,
    "adapter_or_checkpoint_release": False,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _rate(count: int | float, total: int | float) -> float:
    return 0.0 if total == 0 else count / total


def _repo_path(repo_root: Path, relative: Path | str) -> Path:
    return repo_root / relative


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_half_open_span(source_text: str, start: int, end: int, expected_text: str) -> bool:
    if start < 0 or end < start or end > len(source_text):
        return False
    return source_text[start:end] == expected_text


def _clean_output_dir(output_dir: Path, *, keep_blocked: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in REPORT_FILES:
        path = output_dir / filename
        if path.exists() and not (keep_blocked and filename == "blocked.json"):
            path.unlink()


def validate_hybrid_design_inputs(repo_root: Path) -> dict[str, Any]:
    raw_dir = _repo_path(repo_root, RAW_INPUTS)
    slot_summary_path = _repo_path(repo_root, SLOT_ANALYSIS / "summary.json")
    slot_profile_path = _repo_path(repo_root, SLOT_ANALYSIS / "slot-profile.json")
    internal_core_path = _repo_path(repo_root, INTERNAL_CORE)
    blocking_reasons: list[str] = []

    for relative in REQUIRED_RAW_FILES:
        if not (raw_dir / relative).exists():
            blocking_reasons.append(f"missing raw input: {RAW_INPUTS / relative}")
    for path in (slot_summary_path, slot_profile_path, internal_core_path):
        if not path.exists():
            blocking_reasons.append(f"missing required artifact: {path.relative_to(repo_root)}")

    slot_summary: dict[str, Any] = {}
    internal_core: dict[str, Any] = {}
    metric_reproduction: dict[str, Any] = {}
    raw_manifest: dict[str, Any] = {}
    if slot_summary_path.exists():
        slot_summary = read_json(slot_summary_path)
    if internal_core_path.exists():
        internal_core = read_json(internal_core_path)
    metric_path = raw_dir / "metric-reproduction.json"
    manifest_path = raw_dir / "artifact-manifest.json"
    if metric_path.exists():
        metric_reproduction = read_json(metric_path)
    if manifest_path.exists():
        raw_manifest = read_json(manifest_path)

    metric_status = metric_reproduction.get("status") or raw_manifest.get("metric_reproduction_status")
    if metric_status != "reproduced":
        blocking_reasons.append(f"metric reproduction is not reproduced: {metric_status}")

    slot_decision = slot_summary.get("decision_label")
    if slot_decision != "MIXED_SLOT_REPRESENTATION_REQUIRED":
        blocking_reasons.append(f"slot analysis decision is not MIXED_SLOT_REPRESENTATION_REQUIRED: {slot_decision}")

    source_boundary = slot_summary.get("source_boundary", {})
    if not source_boundary.get("projection_inputs_ready"):
        blocking_reasons.append("slot analysis source boundary does not mark projection inputs ready")
    if source_boundary.get("decision_label") != "SLOT_ANALYSIS_INPUT_BOUNDARY_PASSED":
        blocking_reasons.append("slot analysis source boundary did not pass")
    if source_boundary.get("raw_model_output_used_for_analysis") is not False:
        blocking_reasons.append("slot analysis did not use prediction_contract as the analysis authority")

    external_schema = internal_core.get("default_external_schema")
    if external_schema != "BrowserTaskContract V1":
        blocking_reasons.append(f"external schema is not BrowserTaskContract V1: {external_schema}")
    if internal_core.get("training_target_changed") is not False:
        blocking_reasons.append("training target appears changed")
    if internal_core.get("claims", {}).get("v2_training_target_enabled") is not False:
        blocking_reasons.append("V2 training target appears enabled")
    if internal_core.get("claims", {}).get("external_v1_schema_changed") is not False:
        blocking_reasons.append("external V1 schema appears changed")
    if internal_core.get("claims", {}).get("downstream_runtime_migrated") is not False:
        blocking_reasons.append("downstream runtime appears migrated")

    return {
        "change_id": CHANGE_ID,
        "decision_label": INPUT_BOUNDARY_BLOCKED if blocking_reasons else INPUT_BOUNDARY_PASSED,
        "blocking_reasons": blocking_reasons,
        "recovered_prediction_inputs_available": not any(
            reason.startswith("missing raw input") for reason in blocking_reasons
        ),
        "metric_reproduction_status": metric_status,
        "slot_analysis_decision_label": slot_decision,
        "external_schema": external_schema,
        "training_target_changed": internal_core.get("training_target_changed"),
        "contract_core_v2_changed": False,
        "contract_core_v2_scope": "internal_core_and_envelope_boundary_only",
        "source_boundary": source_boundary,
    }


def _source_support_total(profile: dict[str, Any]) -> int:
    return sum(int(value) for value in profile.get("source_support_counts", {}).values())


def _exact_copyable_rate(profile: dict[str, Any]) -> float:
    total = _source_support_total(profile)
    return _rate(int(profile.get("source_support_counts", {}).get("exact_source_supported", 0)), total)


def _normalized_copyable_rate(profile: dict[str, Any]) -> float:
    total = _source_support_total(profile)
    return _rate(int(profile.get("source_support_counts", {}).get("normalized_source_supported", 0)), total)


def _source_absent_rate(profile: dict[str, Any]) -> float:
    total = _source_support_total(profile)
    return _rate(int(profile.get("source_support_counts", {}).get("source_absent_or_generation_required", 0)), total)


def _task_scope(profile: dict[str, Any]) -> str:
    counts = profile.get("task_family_counts", {})
    if not counts:
        return "unknown"
    return ", ".join(sorted(counts))


def _current_value_type(slot_path: str) -> str:
    if slot_path in {"ambiguity", "reason"}:
        return "text_or_object"
    if slot_path == "url":
        return "url_text"
    return "text"


def _strategy_for_profile(profile: dict[str, Any]) -> str:
    slot_path = profile["slot_path"]
    if slot_path in {"query", "field", "target", "action"}:
        return "copy"
    if slot_path in {"ambiguity", "reason"}:
        return "bounded_structured"
    if slot_path == "url":
        return "unresolved"
    if slot_path == "city":
        return "task_schema_constrained"
    if profile.get("copyable_rate", 0.0) >= 0.75:
        return "copy"
    return "unresolved"


def _verifier_requirement(strategy: str, slot_path: str) -> str:
    if strategy == "copy":
        return "exact_or_allowlisted_normalized_source_span_required"
    if strategy == "copy_then_normalize":
        return "source_span_then_allowlisted_normalization_required"
    if strategy == "enum":
        return "schema_or_policy_enum_membership_required"
    if strategy == "task_schema_constrained":
        return "task_type_required_optional_forbidden_key_policy_required"
    if strategy == "bounded_structured":
        return "bounded_structure_schema_required; provenance remains system-derived"
    if strategy == "limited_free_generation":
        return "slot_path_whitelist_and_stricter_downstream_verifier_required"
    return "unsupported_or_resolver_required_fail_closed"


def _fallback_behavior(strategy: str, slot_path: str) -> str:
    if strategy == "copy":
        return "fail_closed_or_unresolved_when_span_not_verified"
    if strategy == "copy_then_normalize":
        return "fail_closed_when_rule_not_allowlisted"
    if strategy == "task_schema_constrained":
        return "diagnostic_only_until_validator_slice"
    if strategy == "bounded_structured":
        return "clarify_or_unresolved_when_structure_not_supported"
    if slot_path == "url":
        return "resolver_required_or_clarify"
    if strategy == "limited_free_generation":
        return "fail_closed_without_whitelist"
    return "fail_closed"


def _matrix_row(profile: dict[str, Any]) -> dict[str, Any]:
    strategy = _strategy_for_profile(profile)
    slot_path = profile["slot_path"]
    return {
        "slot_path": slot_path,
        "task_type_scope": _task_scope(profile),
        "sample_count": int(profile.get("sample_count", 0)),
        "gold_slot_event_count": _source_support_total(profile),
        "exact_copyable_rate": _exact_copyable_rate(profile),
        "normalized_copyable_rate": _normalized_copyable_rate(profile),
        "source_absent_rate": _source_absent_rate(profile),
        "missing_key_rate": float(profile.get("missing_key_rate", 0.0)),
        "extra_key_rate": float(profile.get("extra_key_rate", 0.0)),
        "partial_span_rate": float(profile.get("partial_span_rate", 0.0)),
        "wrong_entity_rate": float(profile.get("wrong_entity_rate", 0.0)),
        "unsupported_prediction_rate": float(profile.get("unsupported_prediction_rate", 0.0)),
        "current_value_type": _current_value_type(slot_path),
        "proposed_representation": strategy,
        "verifier_requirement": _verifier_requirement(strategy, slot_path),
        "fallback_behavior": _fallback_behavior(strategy, slot_path),
        "confidence_level": profile.get("confidence", "LOW"),
        "evidence_reference": f"reports/public-sample/slot-error-mechanism-analysis/slot-profile.json#{slot_path}",
    }


def _build_representation_matrix(slot_profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_matrix_row(profile) for profile in sorted(slot_profiles, key=lambda item: item["slot_path"])]


def _task_key_policy(repo_root: Path) -> list[dict[str, Any]]:
    totals: Counter[str] = Counter()
    key_counts: dict[str, Counter[str]] = defaultdict(Counter)
    gold_dir = _repo_path(repo_root, RAW_INPUTS / "gold")
    for filename in ("dev_gold.jsonl", "test_gold.jsonl"):
        for line in (gold_dir / filename).read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            contract = record["gold_contract"]
            scope = f"{contract['task_type']}:{contract['route']}"
            totals[scope] += 1
            for key in contract.get("slots", {}):
                key_counts[scope][key] += 1

    policies: list[dict[str, Any]] = []
    for scope in sorted(totals):
        total = totals[scope]
        required = sorted(key for key, count in key_counts[scope].items() if count == total)
        optional = sorted(key for key, count in key_counts[scope].items() if 0 < count < total)
        policies.append(
            {
                "task_type_scope": scope,
                "sample_count": total,
                "required_slot_keys": required,
                "optional_slot_keys": optional,
                "forbidden_slot_keys": ["unknown_unlisted_keys"],
                "alias_handling": "canonicalization_candidate_only; strict historical evaluator unchanged",
                "unknown_key_policy": "fail_closed_or_diagnostic_only",
                "missing_required_key_behavior": "unresolved_or_clarify",
                "extra_key_behavior": "validation_failure_or_diagnostic_only",
            }
        )
    return policies


def _projection(matrix: list[dict[str, Any]], summary_metrics: dict[str, Any]) -> dict[str, Any]:
    gold_total = int(summary_metrics["gold_slot_events"])
    prediction_total = int(summary_metrics["prediction_slot_events"])
    strategy_counts: Counter[str] = Counter()
    task_distribution: Counter[str] = Counter()
    slot_distribution: dict[str, int] = {}
    for row in matrix:
        gold_count = int(row["gold_slot_event_count"])
        if gold_count:
            strategy_counts[row["proposed_representation"]] += gold_count
            slot_distribution[row["slot_path"]] = gold_count
            for scope in row["task_type_scope"].split(", "):
                if scope and scope != "unknown":
                    task_distribution[scope] += gold_count

    copy_count = strategy_counts["copy"]
    copy_normalize_source_possible = int(round(summary_metrics["normalized_copyable_rate"] * gold_total))
    bounded_count = strategy_counts["bounded_structured"]
    limited_count = strategy_counts["limited_free_generation"]
    unresolved_count = strategy_counts["unresolved"]
    task_schema_count = strategy_counts["task_schema_constrained"]
    enum_count = strategy_counts["enum"]
    represented_count = copy_count + bounded_count + unresolved_count + task_schema_count + enum_count

    verifiable_prediction_rate = float(summary_metrics["predicted_source_supported_rate"])
    fail_closed_prediction_rate = float(summary_metrics["prediction_unsupported_by_source_rate"]) + float(
        summary_metrics["partial_span_rate"]
    )

    return {
        "change_id": CHANGE_ID,
        "evidence_kind": "read_only_hybrid_slot_representation_feasibility_projection",
        "gold_slot_event_count": gold_total,
        "prediction_slot_event_count": prediction_total,
        "representation_event_counts": dict(sorted(strategy_counts.items())),
        "coverage": {
            "overall_representation_coverage": _rate(represented_count, gold_total),
            "copy_backed_coverage": copy_count,
            "copy_backed_rate": _rate(copy_count, gold_total),
            "copy_normalize_possible_count": copy_normalize_source_possible,
            "copy_normalize_possible_rate": float(summary_metrics["normalized_copyable_rate"]),
            "enum_classification_coverage": enum_count,
            "enum_classification_rate": _rate(enum_count, gold_total),
            "bounded_structured_coverage": bounded_count,
            "bounded_structured_rate": _rate(bounded_count, gold_total),
            "limited_free_generation_coverage": limited_count,
            "limited_free_generation_rate": _rate(limited_count, gold_total),
            "task_schema_constrained_coverage": task_schema_count,
            "task_schema_constrained_rate": _rate(task_schema_count, gold_total),
            "unresolved_coverage": unresolved_count,
            "unresolved_rate": _rate(unresolved_count, gold_total),
        },
        "prediction_verification": {
            "currently_verifiable_prediction_rate": verifiable_prediction_rate,
            "currently_verifiable_prediction_count_estimate": int(round(verifiable_prediction_rate * prediction_total)),
            "currently_fail_closed_prediction_rate": fail_closed_prediction_rate,
            "currently_fail_closed_prediction_count_estimate": int(round(fail_closed_prediction_rate * prediction_total)),
            "source_supported_rate_from_slot_analysis": float(summary_metrics["predicted_source_supported_rate"]),
            "unsupported_by_source_rate_from_slot_analysis": float(
                summary_metrics["prediction_unsupported_by_source_rate"]
            ),
            "partial_span_rate_from_slot_analysis": float(summary_metrics["partial_span_rate"]),
        },
        "task_family_distribution": dict(sorted(task_distribution.items())),
        "slot_path_distribution": dict(sorted(slot_distribution.items())),
        "does_not_mutate_predictions": True,
        "does_not_recalculate_model_success_metrics": True,
        "projection_is_not_model_improvement": True,
    }


def _recommended_next_change() -> dict[str, Any]:
    return {
        "change_id": "implement-copy-backed-slot-verification-slice",
        "scope": "Implement only the verifier-owned copy-backed span/provenance slice for high-copyability slot paths while keeping BrowserTaskContract V1 external serialization unchanged.",
        "target_slot_paths": ["query", "field", "target", "action"],
        "why_first": [
            "These paths have high observed copyability and concrete partial/copy residuals.",
            "The slice can be evaluated offline on current prediction artifacts without training.",
            "It adds fail-closed verifier-owned metadata without changing the external V1 schema.",
        ],
        "acceptance_criteria": [
            "No training, data mutation, evaluator relaxation, or V1 schema migration.",
            "Source spans use half-open Unicode offsets and exact back-slice validation.",
            "Provenance and verification_status are system-derived only.",
            "Unsupported or ambiguous spans fail closed or become unresolved.",
        ],
    }


def _fallback_next_change() -> dict[str, Any]:
    return {
        "change_id": "implement-task-specific-slot-schema-validator",
        "scope": "Low-risk validator-only slice for required/optional/forbidden slot keys after the copy verifier if copy ambiguity blocks implementation.",
        "why_fallback": "Key-boundary errors are not the largest residual, but a validator can be implemented without changing model targets or strict historical evaluator semantics.",
    }


def build_hybrid_slot_representation_design(repo_root: Path) -> dict[str, Any]:
    boundary = validate_hybrid_design_inputs(repo_root)
    if boundary["decision_label"] != INPUT_BOUNDARY_PASSED:
        return {
            "change_id": CHANGE_ID,
            "decision_label": INPUT_BOUNDARY_BLOCKED,
            "input_boundary": boundary,
        }

    slot_summary = read_json(_repo_path(repo_root, SLOT_ANALYSIS / "summary.json"))
    slot_profiles = read_json(_repo_path(repo_root, SLOT_ANALYSIS / "slot-profile.json"))["slot_profiles"]
    matrix = _build_representation_matrix(slot_profiles)
    projection = _projection(matrix, slot_summary["summary_metrics"])

    return {
        "change_id": CHANGE_ID,
        "decision_label": DECISION_COPY_SLICE_FIRST,
        "input_boundary": boundary,
        "hybrid_slot_value": {
            "name": "HybridSlotValue",
            "status": "internal_design_only_not_implemented_schema",
            "fields": FIELD_DEFINITIONS,
            "representation_kinds": [
                "copy",
                "copy_then_normalize",
                "enum",
                "task_schema_constrained",
                "bounded_structured",
                "limited_free_generation",
                "unresolved",
            ],
            "verification_statuses": ["verified", "unsupported", "unresolved"],
            "provenance_values": [
                "source_verified",
                "deterministic_derived",
                "schema_constrained",
                "structured_generated",
                "free_generated",
                "unknown",
            ],
            "source_span_contains": ["start", "end", "text", "source_text_hash"],
        },
        "source_span_semantics": SOURCE_SPAN_SEMANTICS,
        "model_target_recommendation": {
            "primary": "model_outputs_value_system_verifies_span",
            "fallback": "model_outputs_candidate_source_snippet_system_resolves_offset",
            "rejected": "model_outputs_start_end_offsets",
            "answer": "模型不需要直接输出 offsets；V1 推荐模型输出 value，由系统验证并附加 source span。",
            "comparison": MODEL_TARGET_COMPARISON,
        },
        "representation_matrix": matrix,
        "task_specific_key_policy": _task_key_policy(repo_root),
        "ambiguity_design": {
            "recommended": "ambiguity_type_enum_plus_related_slot_keys_plus_optional_display_text",
            "allowed_types_from_current_evidence": [
                "missing_information",
                "unresolved_reference",
                "multiple_targets",
                "insufficient_context",
            ],
            "rejected": "unrestricted_free_text_as_default",
            "compatibility": "maps back to current V1 slots.ambiguity string/object shape in a future implementation",
        },
        "reason_design": {
            "recommended": "bounded_reason_code_or_deterministic_safety_reason_reference",
            "deduplication_proposal": "avoid duplicating the same safety rationale across safety.reason, slots.reason, and normalized_command",
            "implementation_status": "design_only",
        },
        "url_design": {
            "recommended": "exact_or_normalized_copy_else_resolver_required_or_unresolved",
            "paths": [
                "exact_or_normalized_copy",
                "deterministic_resolution_from_future_allowlist",
                "unresolved_or_clarification",
            ],
            "resolver_implemented": False,
        },
        "v1_contract_core_v2_compatibility": {
            "external_schema": "BrowserTaskContract V1",
            "contract_core_v2_changed": False,
            "training_target_changed": False,
            "future_representation_status": "internal_slot_boundary_proposal_only",
        },
        "feasibility_projection": projection,
        "recommended_next_change": _recommended_next_change(),
        "fallback_next_change": _fallback_next_change(),
        "why_not_full_hybrid_system_now": [
            "The design mixes copy verification, key validation, URL resolver policy, and bounded generation; implementing all at once would change multiple contracts at once.",
            "URL and ambiguity/reason substructures still need narrower verifier and resolver evidence.",
            "A copy-backed slice gives the clearest offline fail-closed evaluation without training or external schema migration.",
        ],
        "claims": CLAIMS,
        "cannot_claim": [
            "slot accuracy improved",
            "executable pass improved",
            "span extraction works in production",
            "hybrid representation is implemented",
            "new training target is active",
            "V1 schema has migrated",
            "production or safety readiness",
            "held-out recovery",
            "live browser improvement",
        ],
    }


def _summary_json(design: dict[str, Any]) -> dict[str, Any]:
    return {
        "change_id": CHANGE_ID,
        "decision_label": design["decision_label"],
        "evidence_kind": "design_only_hybrid_slot_representation_v1",
        "input_boundary": design["input_boundary"],
        "hybrid_slot_value": design["hybrid_slot_value"],
        "source_span_semantics": design["source_span_semantics"],
        "model_target_recommendation": design["model_target_recommendation"],
        "coverage": design["feasibility_projection"]["coverage"],
        "prediction_verification": design["feasibility_projection"]["prediction_verification"],
        "recommended_next_change": design["recommended_next_change"],
        "fallback_next_change": design["fallback_next_change"],
        "why_not_full_hybrid_system_now": design["why_not_full_hybrid_system_now"],
        "claims": design["claims"],
        "cannot_claim": design["cannot_claim"],
    }


def _render_summary_md(summary: dict[str, Any]) -> str:
    coverage = summary["coverage"]
    pred = summary["prediction_verification"]
    return f"""# Hybrid Slot Representation V1

- Decision label: `{summary["decision_label"]}`
- Evidence kind: design-only feasibility projection, not model-quality evidence.
- HybridSlotValue final fields: `value`, `value_type`, `representation_kind`, `source_span`, `normalization_rule`, `verification_status`, `provenance`, `fallback_behavior`.
- Model target recommendation: model outputs V1-compatible value; system verifies and attaches source span/provenance. The model does not directly output offsets.
- Source span semantics: Unicode character offsets, start inclusive, end exclusive, exact back-slice required, `source_text_hash` required.
- Overall representation coverage: {coverage["overall_representation_coverage"]:.2%}
- Copy-backed coverage: {coverage["copy_backed_rate"]:.2%}
- Copy-normalize possible coverage: {coverage["copy_normalize_possible_rate"]:.2%}
- Bounded structured coverage: {coverage["bounded_structured_rate"]:.2%}
- Limited free-generation coverage: {coverage["limited_free_generation_rate"]:.2%}
- Unresolved coverage: {coverage["unresolved_rate"]:.2%}
- Currently verifiable prediction rate: {pred["currently_verifiable_prediction_rate"]:.2%}
- Currently fail-closed prediction rate: {pred["currently_fail_closed_prediction_rate"]:.2%}
- Recommended next change: `{summary["recommended_next_change"]["change_id"]}`
- Fallback next change: `{summary["fallback_next_change"]["change_id"]}`

## Claim Boundary

No training, prediction rerun, data mutation, schema migration, evaluator relaxation, runtime integration, checkpoint release, model improvement claim, slot performance improvement claim, or executable-quality improvement claim occurred.
"""


def _render_next_change_md(summary: dict[str, Any]) -> str:
    next_change = summary["recommended_next_change"]
    fallback = summary["fallback_next_change"]
    lines = [
        "# Recommended Next Change",
        "",
        f"- Decision label: `{summary['decision_label']}`",
        f"- Primary change id: `{next_change['change_id']}`",
        f"- Scope: {next_change['scope']}",
        f"- Target slot paths: {', '.join(next_change['target_slot_paths'])}",
        f"- Fallback change id: `{fallback['change_id']}`",
        f"- Fallback scope: {fallback['scope']}",
        "",
        "## Why This Slice First",
        "",
    ]
    lines.extend(f"- {item}" for item in next_change["why_first"])
    lines.extend(
        [
            "",
            "## Acceptance Criteria",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in next_change["acceptance_criteria"])
    lines.extend(
        [
            "",
            "## Hard Stop",
            "",
            "This phase stops after design. It does not implement the vertical slice, train, expand data, modify schema, or build a challenge set.",
        ]
    )
    return "\n".join(lines)


def _render_design_doc(design: dict[str, Any]) -> str:
    summary = _summary_json(design)
    coverage = summary["coverage"]
    pred = summary["prediction_verification"]
    rows = design["representation_matrix"]
    matrix_lines = [
        "| Slot path | Scope | Proposed representation | Confidence | Fallback | Evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        matrix_lines.append(
            "| {slot_path} | {task_type_scope} | `{proposed_representation}` | {confidence_level} | {fallback_behavior} | {evidence_reference} |".format(
                **row
            )
        )

    fields = "\n".join(
        f"- `{field['name']}` ({field['owner']}): {field['description']}"
        for field in design["hybrid_slot_value"]["fields"]
    )
    key_policy = "\n".join(
        f"- `{policy['task_type_scope']}`: required={policy['required_slot_keys']}; optional={policy['optional_slot_keys']}; forbidden={policy['forbidden_slot_keys']}; alias={policy['alias_handling']}; unknown={policy['unknown_key_policy']}; missing={policy['missing_required_key_behavior']}; extra={policy['extra_key_behavior']}"
        for policy in design["task_specific_key_policy"]
    )
    model_comparison = "\n".join(
        f"- Option {item['option']} `{item['name']}`: {item['recommendation']}; fit={item['current_7b_fit']}; V1={item['v1_compatibility']}"
        for item in design["model_target_recommendation"]["comparison"]
    )
    cannot_claim = "\n".join(f"- {item}" for item in design["cannot_claim"])

    return f"""# Hybrid Slot Representation V1

## Problem statement

The current slot-analysis decision is `MIXED_SLOT_REPRESENTATION_REQUIRED`: copyable paths and generation-required paths coexist, so a single span-only or unrestricted-generation representation would be inaccurate.

## Evidence summary

- Samples: 414 dev/test samples.
- Gold slot events: 471.
- Gold exact/normalized source-copyable rate: 50.53%.
- Source-absent or generation-required rate: 49.47%.
- Typed-derivable coverage: 0.00%.
- Prediction unsupported-by-source rate: 32.17%.
- Control to Treatment movement: recovered=10, regressed=12, net=-2.

## Design principles

- Keep external `BrowserTaskContract` V1 unchanged.
- Keep current `ContractCoreV2` unchanged.
- Treat this as a future internal slot boundary proposal, not a schema implementation.
- Make source span, provenance, normalization, and verification status system-derived.
- Fail closed for unsupported or unverifiable values.
- Do not convert all slots to spans or keep all slots as unrestricted free generation.

## Internal proposal

`HybridSlotValue` final proposed fields:

{fields}

`source_span` contains `start`, `end`, `text`, and `source_text_hash`. The hash is system-derived from the source text.

## Source-span semantics

Source span offsets are Unicode character offsets over the original input text or fixed sanitized transcript. `start` is inclusive, `end` is exclusive, and `source_text[start:end]` must exactly recover the verified source text before normalization. Similarity-only spans are not verified copy. Discontiguous spans require an explicit list representation.

## Representation kinds

- `copy`: value should be source-backed and verifier-owned span/provenance must succeed.
- `copy_then_normalize`: value comes from source and then uses an allowlisted deterministic normalization rule.
- `enum`: finite schema/policy value only.
- `task_schema_constrained`: key boundary validation for required/optional/forbidden slot keys.
- `bounded_structured`: finite structure for generation-required fields such as ambiguity/reason.
- `limited_free_generation`: narrow whitelist only when copy, normalization, enum, and structure do not apply.
- `unresolved`: verifier cannot prove the value; future policy may clarify, reject, or fallback.

## Model-authored vs system-derived fields

Model-authored:

- `value` or a bounded structure.
- enum/code only when that strategy requires it.

System-derived:

- `value_type`, `representation_kind`, verified `source_span`, `normalization_rule`, `verification_status`, `provenance`, `source_text_hash`, task-key validation result, fallback decision, and runtime compatibility metadata.

模型不需要直接输出 offsets；主推荐是模型输出 value，系统验证并附加 source span。Snippet may be retained as one fallback candidate pointer for approved copy-heavy slots, but it remains untrusted until verified.

Future model-target option comparison:

{model_comparison}

## Task-specific slot policy

{key_policy}

Alias handling is diagnostic/canonicalization-candidate only and does not change the historical strict evaluator.

## Clarify ambiguity design

Recommended shape: `ambiguity_type` enum plus `related_slot_keys` and optional `display_text`. Candidate observed categories are `missing_information`, `unresolved_reference`, `multiple_targets`, and `insufficient_context`. This reduces unrestricted generation while still mapping back to current V1 `slots.ambiguity` in a future implementation.

## Reason design

Recommended shape: bounded reason code or deterministic reference to `safety.reason` when the reason is policy-derived. Avoid duplicating the same safety rationale across `safety.reason`, `slots.reason`, and `normalized_command`. This is a de-duplication proposal only.

## URL design

URL uses a three-way strategy: exact/normalized copy when source-supported, deterministic resolver only if a future allowlist source is defined, otherwise unresolved/clarify. This phase does not implement a resolver and does not classify every source-absent URL as hallucination.

## V1 / ContractCoreV2 compatibility

External schema remains `BrowserTaskContract` V1. Current training targets remain V1 contract JSON. Current `ContractCoreV2` remains an internal core/envelope boundary. The hybrid representation is not serialized to public runtime contracts in this phase.

## Offline feasibility results

- Overall representation coverage: {coverage["overall_representation_coverage"]:.2%}
- Copy-backed coverage: {coverage["copy_backed_rate"]:.2%}
- Copy-normalize possible coverage: {coverage["copy_normalize_possible_rate"]:.2%}
- Bounded structured coverage: {coverage["bounded_structured_rate"]:.2%}
- Limited free-generation coverage: {coverage["limited_free_generation_rate"]:.2%}
- Unresolved coverage: {coverage["unresolved_rate"]:.2%}
- Currently verifiable prediction rate: {pred["currently_verifiable_prediction_rate"]:.2%}
- Currently fail-closed prediction rate: {pred["currently_fail_closed_prediction_rate"]:.2%}

Representation matrix:

{chr(10).join(matrix_lines)}

## Recommended vertical slice

Primary next change: `{design["recommended_next_change"]["change_id"]}`.

Why: query/field/target/action have high observed copyability, the slice can run offline without training, and verifier-owned span/provenance can fail closed while preserving V1.

Fallback: `{design["fallback_next_change"]["change_id"]}` if copy verification ambiguity blocks implementation.

## Migration risks

- Internal representation could drift from V1 serialization.
- Typed normalization could be mistaken for evaluator relaxation.
- Span provenance could be overclaimed without deterministic verifier evidence.
- URL resolver semantics are not yet authoritative.
- Ambiguity/reason structures can become free generation unless bounded.

## Claim boundaries

This is representation feasibility, not model improvement. It does not mutate predictions, repair outputs, rerun evaluation, or recalculate model success metrics.

## Current claims that remain unsupported

{cannot_claim}

## Non-goals

No training, prediction rerun, data mutation, schema implementation, runtime integration, evaluator modification, model target change, LLM judge, prediction repair, span extraction model, typed normalizer, task-specific validator implementation, checkpoint/adapter release, production readiness, or live-browser improvement.
"""


def write_hybrid_slot_representation_reports(repo_root: Path, output_dir: Path, doc_path: Path) -> dict[str, Any]:
    boundary = validate_hybrid_design_inputs(repo_root)
    _clean_output_dir(output_dir)
    if boundary["decision_label"] != INPUT_BOUNDARY_PASSED:
        blocked = {
            "change_id": CHANGE_ID,
            "decision_label": INPUT_BOUNDARY_BLOCKED,
            "input_boundary": boundary,
            "claims": CLAIMS,
        }
        write_json(output_dir / "blocked.json", blocked)
        return {"summary": blocked, "feasibility_projection": {}, "representation_matrix": []}

    design = build_hybrid_slot_representation_design(repo_root)
    summary = _summary_json(design)
    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "representation-matrix.json", design["representation_matrix"])
    write_json(output_dir / "feasibility-projection.json", design["feasibility_projection"])
    write_text(output_dir / "summary.md", _render_summary_md(summary))
    write_text(output_dir / "recommended-next-change.md", _render_next_change_md(summary))
    write_text(doc_path, _render_design_doc(design))
    return {
        "summary": summary,
        "feasibility_projection": design["feasibility_projection"],
        "representation_matrix": design["representation_matrix"],
        "doc_sha256": _sha256_text(doc_path.read_text(encoding="utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Design Hybrid Slot Representation V1 from current evidence.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--doc-path", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir or repo_root / DEFAULT_OUTPUT_DIR
    doc_path = args.doc_path or repo_root / DEFAULT_DOC_PATH
    result = write_hybrid_slot_representation_reports(repo_root, output_dir, doc_path)
    print(json.dumps({"decision_label": result["summary"]["decision_label"], "output_dir": str(output_dir)}, ensure_ascii=False))
    return 0 if result["summary"]["decision_label"] != INPUT_BOUNDARY_BLOCKED else 1


if __name__ == "__main__":
    raise SystemExit(main())
