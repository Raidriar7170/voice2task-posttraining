from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, cast

DESIGN_INPUT_WHITELIST = (
    "reports/public-sample/contract-compiler-v2-causal-boundary/summary.json",
    "openspec/specs/contract-compiler-v2-causal-audit/spec.md",
    "CONTEXT.md",
    "data/public-samples/manifest_public_sample.json",
    "reports/public-sample/split-integrity-audit/summary.json",
    "data/lockbox/lockbox-v1.manifest.json",
    "reports/lockbox-v1/final-evaluation/run-card.json",
    "reports/lockbox-v1/final-evaluation/base/metrics.json",
    "reports/lockbox-v1/final-evaluation/final-sft/metrics.json",
    "reports/lockbox-v1/final-evaluation/comparison.json",
)

EXPECTED_SOURCE_SHA256 = {
    "reports/public-sample/contract-compiler-v2-causal-boundary/summary.json": (
        "5bfcbedfb6130207c577f6b03608a555086ac33f1295d4a7f225917be0cde1c1"
    ),
    "openspec/specs/contract-compiler-v2-causal-audit/spec.md": (
        "5db529a5e603b610e79a4ba1e2b3765ba6fa6c263de48b2df629b69863e7e26c"
    ),
    "CONTEXT.md": "becc5b54eaf66f90789b77fb4fef1a6fc14bd62ae8ef50f9f26a0791edd4b993",
    "data/public-samples/manifest_public_sample.json": (
        "f866c173795e97953b1dec85611b405867d0a29497910282f99d399f109cda95"
    ),
    "reports/public-sample/split-integrity-audit/summary.json": (
        "ac10bd0a1c3fefb717433de68ae29d049069b521bae8599234b7f52faec8f598"
    ),
    "data/lockbox/lockbox-v1.manifest.json": (
        "72471bac59749f3bc9d21d73db47dafe1f160b978f5ac3971434e13527ddedde"
    ),
    "reports/lockbox-v1/final-evaluation/run-card.json": (
        "39e59cd6e16baa7adadb6b3c474e7fce8bfe8223e5980a1288a1c50432acec66"
    ),
    "reports/lockbox-v1/final-evaluation/base/metrics.json": (
        "400fa753e6e8bde611af4e4f9623155ceff6664454bfea0f57748043243cd02f"
    ),
    "reports/lockbox-v1/final-evaluation/final-sft/metrics.json": (
        "aaecc8dcdad90e70c0f8a7c59a21d2e65d8d42bae3e304e4dce9b049390bc829"
    ),
    "reports/lockbox-v1/final-evaluation/comparison.json": (
        "48fae0e85e016c1872477881939716076d96998d0c63f83adf1e9be42d9ed544"
    ),
}

HISTORICAL_SOURCE_SNAPSHOT_OVERRIDES = {
    "CONTEXT.md": (
        "reports/public-sample/clean-matched-causal-evidence-design/source-snapshots/"
        "CONTEXT.becc5b54eaf66f90789b77fb4fef1a6fc14bd62ae8ef50f9f26a0791edd4b993.md"
    )
}

DENIED_INPUTS = (
    "data/lockbox/lockbox-v1.jsonl",
    "data/lockbox/lockbox-v1.draft.jsonl",
    "reports/lockbox-v1/final-evaluation/row-failures.jsonl",
    "raw/private-predictions/",
    "private-corpora/",
    ".cache/",
    "adapters/",
    "checkpoints/",
    "logs/",
    "secrets/",
    ".env",
    ".ssh/",
)

EXECUTION_BINDING_FIELDS = (
    "acquisition_source",
    "acquisition_frame_version",
    "semantic_family_key",
    "partition_algorithm",
    "partition_seed",
    "strata_definition",
    "target_total_family_count",
    "target_partition_allocation",
    "minimum_families_per_partition",
    "compiler_control",
    "compiler_intervention",
    "model_control",
    "model_training_intervention",
    "paired_model_seed_list",
    "compiler_effect_scale",
    "model_effect_scale",
    "compiler_mde_or_sensitivity_target",
    "model_mde_or_sensitivity_target",
    "compiler_target_power_or_beta",
    "model_target_power_or_beta",
    "alpha",
    "compiler_family_variance_or_icc_assumption",
    "model_family_variance_or_icc_assumption",
    "paired_seed_correlation_assumption",
    "seed_failure_or_attrition_assumption",
    "compiler_interval_and_multiplicity_method",
    "model_interval_and_multiplicity_method",
    "guardrail_margins",
    "stop_rules",
)

READINESS_LIFECYCLE = (
    "DESIGN_ONLY",
    "EXPERIMENT_BINDINGS_COMPLETE",
    "PROTOCOL_FROZEN",
    "POPULATION_MATERIALIZED_AND_SEALED",
    "ARM_ARTIFACTS_FROZEN",
    "ELIGIBLE_FOR_ONE_LOOK",
)

_EXECUTION_FLAG_NAMES = (
    "clean_row_creation",
    "clean_row_selection",
    "clean_row_annotation",
    "clean_outcome_access",
    "compiler_implementation",
    "decoder_implementation",
    "training_run",
    "prediction_run",
    "a100_execution",
    "data_mutation",
    "prompt_change",
    "schema_change",
    "evaluator_change",
    "runtime_change",
    "lockbox_row_level_read",
    "experiment_execution",
)

_CLAIM_FLAG_NAMES = (
    "clean_independent_evidence_claim",
    "compiler_causal_effect_claim",
    "model_learning_causal_effect_claim",
    "model_improvement_claim",
    "executable_improvement_claim",
    "natural_asr_generalization_claim",
    "checkpoint_release_claim",
    "adapter_release_claim",
    "production_readiness_claim",
    "safety_readiness_claim",
    "live_browser_benchmark_claim",
)

_SOURCE_ANCHORS = {
    "reports/public-sample/contract-compiler-v2-causal-boundary/summary.json": (
        '"audit_status": "ARCHIVED"',
        '"status": "CAUSAL_IDENTIFICATION_BLOCKED"',
        '"implementation_status": "NOT_IMPLEMENTED_HYPOTHETICAL"',
    ),
    "openspec/specs/contract-compiler-v2-causal-audit/spec.md": (
        "### Requirement: Classify evidence fail closed",
        "CAUSAL_IDENTIFICATION_BLOCKED",
        "consumed one-look lockbox-v1",
    ),
    "CONTEXT.md": (
        "UNBOUND_BY_DESIGN",
        "clean_population_status=NOT_MATERIALIZED",
        "execution_readiness=false",
    ),
    "data/public-samples/manifest_public_sample.json": (
        '"manifest_id": "public-sample-20260619T090925Z"',
        '"seed_rows": 247',
        '"sft_rows": 696',
        '"dpo_pairs": 2100',
    ),
    "reports/public-sample/split-integrity-audit/summary.json": (
        '"evidence_status": "DEVELOPMENT_ONLY_SPENT"',
        '"passed": false',
    ),
    "data/lockbox/lockbox-v1.manifest.json": (
        '"frozen": true',
        '"family_count": 120',
        '"row_count": 120',
    ),
    "reports/lockbox-v1/final-evaluation/run-card.json": (
        '"final_lockbox_evaluation_run_once": true',
        '"lockbox_tuning_after_result": false',
        '"row_level_failure_analysis_public": false',
    ),
    "reports/lockbox-v1/final-evaluation/base/metrics.json": (
        '"aggregate_metrics_only": true',
        '"row_level_failure_analysis_included": false',
        '"row_count": 120',
    ),
    "reports/lockbox-v1/final-evaluation/final-sft/metrics.json": (
        '"aggregate_metrics_only": true',
        '"row_level_failure_analysis_included": false',
        '"row_count": 120',
    ),
    "reports/lockbox-v1/final-evaluation/comparison.json": (
        '"comparison": "final_sft_minus_base"',
        '"aggregate_metrics_only": true',
        '"lockbox_tuning_after_result": false',
    ),
}


def _validate_design_input_path(relative_path: str) -> str:
    raw_path = str(relative_path)
    if not raw_path or "\\" in raw_path:
        raise ValueError(
            f"design input path must be a non-empty repo-relative POSIX path: {raw_path!r}"
        )
    path = PurePosixPath(raw_path)
    is_windows_drive_path = len(raw_path) >= 2 and raw_path[0].isalpha() and raw_path[1] == ":"
    if path.is_absolute() or is_windows_drive_path:
        raise ValueError(f"design input path must be repo-relative: {raw_path}")
    if ".." in path.parts:
        raise ValueError(f"design input path traversal is forbidden: {raw_path}")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise ValueError(f"design input path must name a file: {raw_path!r}")
    for denied in DENIED_INPUTS:
        denied_boundary = denied.rstrip("/")
        if normalized == denied_boundary or normalized.startswith(f"{denied_boundary}/"):
            raise ValueError(f"design input path is denylisted: {normalized}")
    return normalized


def _validated_whitelist_paths() -> tuple[str, ...]:
    paths = tuple(_validate_design_input_path(path) for path in DESIGN_INPUT_WHITELIST)
    if len(set(paths)) != len(paths):
        raise ValueError("design input whitelist contains duplicates after normalization")
    if set(paths) != set(EXPECTED_SOURCE_SHA256):
        raise ValueError("design input whitelist and frozen hash inventory differ")
    return paths


def _require_whitelisted_path(relative_path: str) -> str:
    normalized = _validate_design_input_path(relative_path)
    if normalized not in _validated_whitelist_paths():
        raise ValueError(f"design input path is not in the explicit whitelist: {normalized}")
    return normalized


def _resolve_design_source_path(repo_root: Path, relative_path: str) -> Path:
    relative_path = _require_whitelisted_path(relative_path)
    physical_path = _validate_design_input_path(
        HISTORICAL_SOURCE_SNAPSHOT_OVERRIDES.get(relative_path, relative_path)
    )
    try:
        resolved_root = repo_root.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ValueError(f"required design source root missing: {repo_root}") from exc
    expected_path = resolved_root / physical_path
    try:
        resolved_path = expected_path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ValueError(f"required design source missing: {relative_path}") from exc
    if resolved_path != expected_path:
        raise ValueError(
            f"design source symlink or alternate logical location is forbidden: {relative_path}"
        )
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"design source resolves outside repository: {relative_path}") from exc
    if not resolved_path.is_file():
        raise ValueError(f"required design source is not a regular file: {relative_path}")
    return resolved_path


def _read_design_source_bytes(repo_root: Path, relative_path: str) -> bytes:
    return _resolve_design_source_path(repo_root, relative_path).read_bytes()


def _sha256(repo_root: Path, relative_path: str) -> str:
    relative_path = _require_whitelisted_path(relative_path)
    return hashlib.sha256(_read_design_source_bytes(repo_root, relative_path)).hexdigest()


def _source_text(repo_root: Path, relative_path: str) -> str:
    relative_path = _require_whitelisted_path(relative_path)
    try:
        return _read_design_source_bytes(repo_root, relative_path).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"required design source is not UTF-8: {relative_path}") from exc


def _validate_source_anchors(repo_root: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for relative_path in _validated_whitelist_paths():
        text = _source_text(repo_root, relative_path)
        anchors = _SOURCE_ANCHORS[relative_path]
        missing = [anchor for anchor in anchors if anchor not in text]
        if missing:
            raise ValueError(f"source anchor missing from {relative_path}: {missing}")
        results.append({"path": relative_path, "anchors": list(anchors), "valid": True})
    return results


def _source_manifest(repo_root: Path) -> list[dict[str, str]]:
    return cast(list[dict[str, str]], _source_evidence(repo_root)["source_manifest"])


def _source_evidence(repo_root: Path) -> dict[str, Any]:
    manifest: list[dict[str, str]] = []
    anchor_results: list[dict[str, object]] = []
    for relative_path in _validated_whitelist_paths():
        content = _read_design_source_bytes(repo_root, relative_path)
        actual = hashlib.sha256(content).hexdigest()
        expected = EXPECTED_SOURCE_SHA256[relative_path]
        if actual != expected:
            raise ValueError(
                f"frozen design source hash drift for {relative_path}: expected {expected}, got {actual}"
            )
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"required design source is not UTF-8: {relative_path}") from exc
        anchors = _SOURCE_ANCHORS[relative_path]
        missing = [anchor for anchor in anchors if anchor not in text]
        if missing:
            raise ValueError(f"source anchor missing from {relative_path}: {missing}")
        manifest.append({"path": relative_path, "sha256": actual})
        anchor_results.append(
            {"path": relative_path, "anchors": list(anchors), "valid": True}
        )
    return {
        "source_manifest": manifest,
        "source_anchor_validation": anchor_results,
    }


def _population_design(execution_bindings: dict[str, str]) -> dict[str, object]:
    mechanics_fields = (
        "acquisition_source",
        "acquisition_frame_version",
        "semantic_family_key",
        "partition_algorithm",
        "partition_seed",
        "strata_definition",
        "target_total_family_count",
        "target_partition_allocation",
        "minimum_families_per_partition",
    )
    future_partition = {
        "materialization_status": "NOT_MATERIALIZED",
        "membership_assignment_status": "NOT_ASSIGNED",
        "sealing_status": "NOT_SEALED",
        "one_look_state": "NOT_AVAILABLE",
        "future_family_disjoint": True,
    }
    return {
        "acquisition_plan_count": 1,
        "acquisition_status": "NOT_STARTED",
        "family_registry_status": "NOT_CREATED",
        "partition_count": 2,
        "shared_sequential_partition": False,
        "partitions": [
            {"id": "compiler_system_evaluation", **future_partition},
            {"id": "model_learning_evaluation", **future_partition},
        ],
        "partition_mechanics": {
            "freeze_required_before_acquisition": True,
            "protocol_frozen_now": False,
            "mechanics_bindings": {
                field: execution_bindings[field] for field in mechanics_fields
            },
        },
        "partition_mechanics_frozen_now": False,
        "future_membership_assignment": {
            "source": "future_source_hashed_acquisition_frame",
            "unit": "semantic_family",
            "assignment_count": "EXACTLY_ONCE_IN_FUTURE_MATERIALIZATION",
            "before": ["row_authoring", "annotation", "gold_access", "outcome_access"],
            "realized_counts_are_design_bindings": False,
            "membership_attestation_created_now": False,
        },
        "lineage_contract": {
            "excluded_ancestry": [
                "current_public_train",
                "current_public_dev",
                "current_public_test",
                "remediation_artifacts",
                "challenge_artifacts",
                "prediction_artifacts",
                "lockbox_v1",
            ],
            "predeclared_disjointness_checks": [
                "exact",
                "normalized",
                "template",
                "semantic_family",
                "provenance",
            ],
            "lockbox_overlap_interface": "SEALED_AGGREGATE_ATTESTATION_ONLY",
            "lockbox_row_access": False,
            "new_creation_timestamp_establishes_cleanliness": False,
            "synthetic_origin_establishes_natural_asr": False,
        },
        "family_disjointness_rules": {
            "one_family_in_exactly_one_evaluation_partition": True,
            "training_use": False,
            "development_use": False,
            "remediation_use": False,
            "challenge_use": False,
            "post_hoc_repartitioning": False,
            "outcome_aware_allocation": False,
        },
        "independent_one_look_contract": {
            "compiler_open_consumes": ["compiler_system_evaluation"],
            "compiler_open_preserves": ["model_learning_evaluation"],
            "cross_partition_inspection": False,
            "compiler_result_driven_model_changes": False,
            "partition_reuse_for_other_estimand": False,
        },
        "artifacts_created": {
            "clean_rows": False,
            "family_registry": False,
            "partition_membership": False,
            "clean_manifest": False,
            "gold_labels": False,
            "predictions": False,
        },
        "claims_allowed": {
            "clean_independent_evidence": False,
            "natural_asr": False,
            "population_materialized": False,
            "partitions_sealed": False,
        },
    }


def _preregistration_cards(execution_bindings: dict[str, str]) -> dict[str, object]:
    return {
        "compiler_system": {
            "partition": "compiler_system_evaluation",
            "observation_unit": "one_frozen_raw_record",
            "eligible_population": "future_clean_fixed_eligible_population",
            "bindings": {
                "compiler_control": execution_bindings["compiler_control"],
                "compiler_intervention": execution_bindings["compiler_intervention"],
            },
            "future_named_arm_requirements": {
                "control": "one_named_identity_or_preserve_legacy_path",
                "intervention": "one_named_candidate_compiler",
                "complete_now": False,
            },
            "primary_outcome": "compiled_v1_strict_exact_full_population_itt",
            "primary_denominator": "complete_fixed_eligible_population",
            "primary_failure_categories": [
                "invalid",
                "renderer_unsupported",
                "compiler_error",
                "missing",
            ],
            "supported_only_secondary_diagnostic": True,
            "supported_only_denominator_must_be_printed": True,
            "arm_invariants": [
                "byte_identical_model_output",
                "semantic_core_identity",
                "legacy_envelope_metadata_identity",
                "row_and_order_identity",
                "source_hash_identity",
                "prompt_and_decoding_provenance_identity",
                "evaluator_version_identity",
                "no_prediction_repair",
            ],
            "paired_analysis": {
                "record_contrast": "paired_within_record_before_aggregation",
                "family_aggregation": (
                    "aggregate_record_contrasts_within_semantic_family"
                ),
                "interval": (
                    "family_clustered_paired_or_randomization_method_UNBOUND_BY_DESIGN"
                ),
                "row_independence_assumed": False,
                "multiplicity_bound_before_outcomes": True,
            },
            "guardrails": ["safety", "confirmation", "slots", "executable_gates"],
            "negative_controls": [
                "constant_only",
                "field_copy_only",
                "policy_default_only",
                "evaluation_plumbing",
            ],
            "effect_label_if_future_identified": "system_compiler_transformation_effect",
            "causal_identification": "CAUSAL_IDENTIFICATION_BLOCKED",
        },
        "model_learning": {
            "partition": "model_learning_evaluation",
            "observation_unit": "one_preregistered_evaluation_family",
            "bindings": {
                "model_control": execution_bindings["model_control"],
                "model_training_intervention": execution_bindings[
                    "model_training_intervention"
                ],
                "paired_model_seed_list": execution_bindings["paired_model_seed_list"],
            },
            "exactly_one_training_intervention_required": True,
            "bound_training_intervention_count": 0,
            "matched_arm_requirements": [
                "data_boundary_identity",
                "prompt_identity",
                "output_schema_identity",
                "decoding_identity",
                "compiler_policy_identity",
                "evaluator_version_identity",
                "optimization_budget_identity",
                "eligible_evaluation_population_identity",
            ],
            "minimum_assigned_paired_seeds": 3,
            "assigned_seed_list_status": execution_bindings["paired_model_seed_list"],
            "primary_seed_denominator": "all_assigned_paired_seeds",
            "seed_failure_policy": {
                "failure_codes": [
                    "MISSING_CONTROL_ARM",
                    "MISSING_INTERVENTION_ARM",
                    "TRAINING_FAILURE",
                    "INVALID_EVALUATION",
                ],
                "drop_seed": False,
                "replace_seed": False,
                "selective_rerun": False,
            },
            "aggregation_order": [
                "aggregate_within_semantic_family_for_each_assigned_seed",
                "pair_same_assigned_seed_list_across_arms",
                "retain_failure_coded_seeds_in_primary_itt",
            ],
            "primary_outcome_scope": "model_authored_fields_only",
            "model_authored_outcomes": ["intent", "slots", "risk", "clarification"],
            "excluded_primary_outcomes": [
                "compiler_filled_constants",
                "route",
                "safety",
                "confirmation",
                "normalized_command",
                "language",
                "contract_version",
                "compiled_full_v1_exact",
            ],
            "bundled_pipeline_comparison_identifies_model_learning": False,
            "pipeline_metrics_reported_separately": True,
            "causal_identification": "CAUSAL_IDENTIFICATION_BLOCKED",
        },
    }


def _power_and_uncertainty(execution_bindings: dict[str, str]) -> dict[str, object]:
    compiler_fields = (
        "compiler_effect_scale",
        "compiler_mde_or_sensitivity_target",
        "compiler_target_power_or_beta",
        "alpha",
        "compiler_family_variance_or_icc_assumption",
        "compiler_interval_and_multiplicity_method",
        "guardrail_margins",
        "stop_rules",
    )
    model_fields = (
        "model_effect_scale",
        "model_mde_or_sensitivity_target",
        "model_target_power_or_beta",
        "alpha",
        "model_family_variance_or_icc_assumption",
        "paired_seed_correlation_assumption",
        "seed_failure_or_attrition_assumption",
        "model_interval_and_multiplicity_method",
        "guardrail_margins",
        "stop_rules",
    )
    return {
        "compiler_system": {
            "bound_before_clean_outcomes": True,
            "binding_values": {field: execution_bindings[field] for field in compiler_fields},
            "dependence_structure": ["paired_record", "semantic_family_cluster"],
            "row_independent_interval_allowed": False,
        },
        "model_learning": {
            "bound_before_clean_outcomes": True,
            "binding_values": {field: execution_bindings[field] for field in model_fields},
            "dependence_structure": ["semantic_family_cluster", "paired_seed"],
            "row_independent_interval_allowed": False,
            "incomplete_seed_deletion_allowed": False,
        },
        "historical_inputs": "AGGREGATE_ONLY_SENSITIVITY_INPUTS",
        "resize_after_clean_outcome_access": False,
        "repartition_after_clean_outcome_access": False,
        "select_after_clean_outcome_access": False,
    }


def _invariant_matrix() -> list[dict[str, object]]:
    records = (
        ("source_hashes_match", "all"),
        ("execution_bindings_complete_before_freeze", "all"),
        ("family_partition_disjointness", "population"),
        ("no_early_outcome_access", "population"),
        ("compiler_arm_identity_except_compiler", "compiler_system"),
        ("model_arm_identity_except_one_training_intervention", "model_learning"),
        ("all_assigned_seeds_retained", "model_learning"),
        ("one_look_state_independence", "population"),
    )
    return [
        {
            "name": name,
            "scope": scope,
            "machine_checkable": True,
            "status_now": "DESIGN_RULE_ONLY",
        }
        for name, scope in records
    ]


def _hard_stops() -> list[dict[str, object]]:
    codes = (
        "MISSING_BINDINGS",
        "LINEAGE_AMBIGUITY",
        "PARTITION_FAMILY_OVERLAP",
        "SOURCE_HASH_DRIFT",
        "EARLY_OUTCOME_ACCESS",
        "ARM_MISMATCH",
        "SEED_LOSS",
        "PREDICTION_REPAIR",
        "UNSUPPORTED_CASE_FILTERING",
        "ONE_LOOK_REUSE",
    )
    return [
        {
            "code": code,
            "machine_checkable": True,
            "action": "STOP_READINESS_NO_CAUSAL_CLAIM",
        }
        for code in codes
    ]


def build_clean_matched_causal_evidence_design(repo_root: Path) -> dict[str, Any]:
    execution_bindings = {field: "UNBOUND_BY_DESIGN" for field in EXECUTION_BINDING_FIELDS}
    source_evidence = _source_evidence(repo_root)
    lifecycle_blockers = {
        "DESIGN_ONLY": [],
        "EXPERIMENT_BINDINGS_COMPLETE": ["execution_bindings_unbound"],
        "PROTOCOL_FROZEN": ["protocol_not_frozen"],
        "POPULATION_MATERIALIZED_AND_SEALED": ["clean_population_not_materialized"],
        "ARM_ARTIFACTS_FROZEN": ["arm_artifacts_not_frozen"],
        "ELIGIBLE_FOR_ONE_LOOK": ["one_look_not_eligible"],
    }
    return {
        "methodology_version": "clean-matched-causal-evidence-design.v1",
        "status": {
            "evidence_status": "DESIGN_ONLY",
            "decision": "PREREGISTRATION_DESIGN_READY_EXECUTION_BLOCKED",
            "design_contract_status": "REVIEWED_DESIGN_ONLY",
            "protocol_freeze_status": "NOT_FROZEN",
            "clean_population_status": "NOT_MATERIALIZED",
            "compiler_causal_identification": "CAUSAL_IDENTIFICATION_BLOCKED",
            "model_learning_causal_identification": "CAUSAL_IDENTIFICATION_BLOCKED",
            "experiment_preregistration_status": "NOT_EXECUTABLE",
            "execution_readiness": False,
        },
        "input_policy": {
            "whitelist": list(_validated_whitelist_paths()),
            "denylist": list(DENIED_INPUTS),
            "aggregate_lockbox_only": True,
            "broad_directory_discovery": False,
        },
        "source_manifest": source_evidence["source_manifest"],
        "source_anchor_validation": source_evidence["source_anchor_validation"],
        "execution_bindings": execution_bindings,
        "binding_inventory_count": len(execution_bindings),
        "unbound_binding_count": len(execution_bindings),
        "bound_binding_count": 0,
        "execution_bindings_complete": False,
        "population_design": _population_design(execution_bindings),
        "preregistration_cards": _preregistration_cards(execution_bindings),
        "power_and_uncertainty": _power_and_uncertainty(execution_bindings),
        "invariant_matrix": _invariant_matrix(),
        "hard_stops": _hard_stops(),
        "negative_controls": [
            "constant_only",
            "field_copy_only",
            "policy_default_only",
            "evaluation_plumbing",
            "compiler_filled_fields_not_model_learning",
        ],
        "readiness_lifecycle": [
            {
                "state": state,
                "ordinal": ordinal,
                "reached": ordinal == 0,
                "blocked_reasons": lifecycle_blockers[state],
            }
            for ordinal, state in enumerate(READINESS_LIFECYCLE)
        ],
        "current_readiness_state": "DESIGN_ONLY",
        "maximum_state_this_change": "DESIGN_ONLY",
        "state_skipping_allowed": False,
        "document_presence_implies_readiness": False,
        "blocked_reasons": {
            "execution_readiness": [
                "execution_bindings_unbound",
                "protocol_not_frozen",
                "clean_population_not_materialized",
                "arm_artifacts_not_frozen",
                "one_look_not_eligible",
            ],
            "compiler_causal_identification": [
                "no_clean_matched_compiler_comparison",
                "compiler_control_unbound",
                "compiler_intervention_unbound",
            ],
            "model_learning_causal_identification": [
                "no_clean_matched_multi_seed_model_comparison",
                "model_control_unbound",
                "model_training_intervention_unbound",
                "paired_model_seed_list_unbound",
            ],
        },
        "execution_flags": {name: False for name in _EXECUTION_FLAG_NAMES},
        "claim_flags": {name: False for name in _CLAIM_FLAG_NAMES},
        "next_phase_recommendations": [
            {
                "change": (
                    "materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1"
                ),
                "executed": False,
                "separate_review_required": True,
                "may_run_compiler_or_model_experiment": False,
            }
        ],
    }


def _summary_markdown(design: dict[str, Any]) -> str:
    status = design["status"]
    bindings = design["execution_bindings"]
    population = design["population_design"]
    cards = design["preregistration_cards"]
    power = design["power_and_uncertainty"]
    lifecycle = design["readiness_lifecycle"]
    source_manifest = design["source_manifest"]
    next_phase = design["next_phase_recommendations"][0]

    lines = [
        "# Clean Matched Compiler / Model Causal Evidence Design",
        "",
        (
            "This is a reviewed design-only contract. It does not materialize clean evidence, "
            "freeze an executable protocol, or run either experiment."
        ),
        "",
        "## Exact truth surface",
        "",
        f"- evidence_status={status['evidence_status']}",
        f"- decision={status['decision']}",
        f"- design_contract_status={status['design_contract_status']}",
        f"- protocol_freeze_status={status['protocol_freeze_status']}",
        f"- clean_population_status={status['clean_population_status']}",
        (
            "- compiler_causal_identification="
            f"{status['compiler_causal_identification']}"
        ),
        (
            "- model_learning_causal_identification="
            f"{status['model_learning_causal_identification']}"
        ),
        (
            "- experiment_preregistration_status="
            f"{status['experiment_preregistration_status']}"
        ),
        f"- execution_readiness={str(status['execution_readiness']).lower()}",
        "",
        "## Frozen source manifest",
        "",
        "| path | sha256 |",
        "| --- | --- |",
    ]
    lines.extend(f"| `{record['path']}` | `{record['sha256']}` |" for record in source_manifest)
    lines.extend(
        [
            "",
            "## Canonical execution bindings",
            "",
            "29 / 29 execution bindings remain `UNBOUND_BY_DESIGN`.",
            "",
            "| field | value |",
            "| --- | --- |",
        ]
    )
    lines.extend(f"| `{field}` | `{value}` |" for field, value in bindings.items())
    lines.extend(
        [
            "",
            "## Future clean acquisition and partition contract",
            "",
            f"- Acquisition plans: {population['acquisition_plan_count']} (status: "
            f"`{population['acquisition_status']}`).",
        ]
    )
    for partition in population["partitions"]:
        lines.append(
            f"- `{partition['id']}`: materialization `{partition['materialization_status']}`, "
            f"sealing `{partition['sealing_status']}`, one-look "
            f"`{partition['one_look_state']}`."
        )
    lines.extend(
        [
            "- Family assignment happens exactly once in a future materialization from "
            "frozen mechanics, before row authoring, annotation, gold access, or outcome access.",
            "- No clean row, family registry, membership, gold label, or prediction was created.",
            "",
            "## Separate preregistration cards",
            "",
            f"### Compiler / system (`{cards['compiler_system']['partition']}`)",
            "",
            "- Full fixed-population ITT; invalid, unsupported, compiler-error, and missing "
            "records remain primary failures.",
            "- Paired within-record contrasts aggregate within semantic family; row-independent "
            "intervals are forbidden.",
            "- Any future identified effect is labeled "
            "`system_compiler_transformation_effect` only.",
            "",
            f"### Model learning (`{cards['model_learning']['partition']}`)",
            "",
            "- Exactly one future training intervention, matched arms, and at least three "
            "all-assigned paired seeds are required.",
            "- Failed or missing assigned seeds receive preregistered failure codes and remain "
            "in the seed-level ITT denominator.",
            "- Compiler-filled outcomes cannot identify model learning.",
            "",
            "## Power and uncertainty",
            "",
            f"- Compiler dependence: {', '.join(power['compiler_system']['dependence_structure'])}.",
            f"- Model dependence: {', '.join(power['model_learning']['dependence_structure'])}.",
            "- MDE, target power/beta, alpha, ICC/family variance, paired-seed correlation, "
            "seed attrition, interval/multiplicity methods, guardrail margins, and stop rules "
            "remain pre-outcome `UNBOUND_BY_DESIGN` bindings.",
            "",
            "## Readiness lifecycle",
            "",
        ]
    )
    lines.extend(
        f"{entry['ordinal']}. `{entry['state']}` — reached="
        f"{str(entry['reached']).lower()}"
        for entry in lifecycle
    )
    lines.extend(
        [
            "",
            "## Next phase",
            "",
            f"- `{next_phase['change']}`",
            f"- executed={str(next_phase['executed']).lower()}",
            "- A separate review is required; that phase may not run compiler or model experiments.",
            "",
        ]
    )
    return "\n".join(lines)


def render_clean_matched_causal_evidence_design(
    repo_root: Path, output_dir: Path | None = None
) -> list[Path]:
    design = build_clean_matched_causal_evidence_design(repo_root)
    if output_dir is None:
        output_dir = repo_root / "reports/public-sample/clean-matched-causal-evidence-design"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "summary.json"
    markdown_path = output_dir / "summary.md"
    json_path.write_text(
        json.dumps(design, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_summary_markdown(design), encoding="utf-8")
    return [json_path, markdown_path]
