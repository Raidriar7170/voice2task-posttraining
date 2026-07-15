from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

import voice2task.clean_matched_causal_evidence_design as design_module

REPO_ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_CONTEXT_SHA256 = "becc5b54eaf66f90789b77fb4fef1a6fc14bd62ae8ef50f9f26a0791edd4b993"
HISTORICAL_CONTEXT_SNAPSHOT = (
    "reports/public-sample/clean-matched-causal-evidence-design/source-snapshots/"
    f"CONTEXT.{HISTORICAL_CONTEXT_SHA256}.md"
)
HISTORICAL_MANIFEST_SHA256 = "f866c173795e97953b1dec85611b405867d0a29497910282f99d399f109cda95"
HISTORICAL_MANIFEST_SNAPSHOT = (
    "reports/public-sample/formal-manifest-history/"
    f"manifest_public_sample.{HISTORICAL_MANIFEST_SHA256}.json"
)
HISTORICAL_SPLIT_SUMMARY_SHA256 = "ac10bd0a1c3fefb717433de68ae29d049069b521bae8599234b7f52faec8f598"
HISTORICAL_SPLIT_SUMMARY_SNAPSHOT = (
    "reports/public-sample/split-integrity-audit/source-snapshots/"
    f"summary.{HISTORICAL_SPLIT_SUMMARY_SHA256}.json"
)

EXPECTED_DESIGN_INPUT_WHITELIST = (
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

EXPECTED_EXECUTION_BINDING_FIELDS = (
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

EXPECTED_READINESS_LIFECYCLE = (
    "DESIGN_ONLY",
    "EXPERIMENT_BINDINGS_COMPLETE",
    "PROTOCOL_FROZEN",
    "POPULATION_MATERIALIZED_AND_SEALED",
    "ARM_ARTIFACTS_FROZEN",
    "ELIGIBLE_FOR_ONE_LOOK",
)

EXPECTED_FALSE_EXECUTION_FLAGS = {
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
}

EXPECTED_FALSE_CLAIM_FLAGS = {
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
}


def test_clean_matched_causal_evidence_design_module_exists() -> None:
    assert importlib.util.find_spec("voice2task.clean_matched_causal_evidence_design") is not None


def test_design_source_policy_is_exactly_public_safe_aggregate_only() -> None:
    assert getattr(design_module, "DESIGN_INPUT_WHITELIST", None) == (
        EXPECTED_DESIGN_INPUT_WHITELIST
    )
    assert getattr(design_module, "EXPECTED_SOURCE_SHA256", None) == EXPECTED_SOURCE_SHA256
    denied = getattr(design_module, "DENIED_INPUTS", ())
    assert {
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
    } <= set(denied)
    assert set(EXPECTED_DESIGN_INPUT_WHITELIST).isdisjoint(denied)
    assert len(EXPECTED_DESIGN_INPUT_WHITELIST) == 10


@pytest.mark.parametrize(
    "relative_path",
    (
        "",
        "/etc/passwd",
        "../CONTEXT.md",
        "reports/../CONTEXT.md",
        r"reports\public-sample\summary.json",
        "C:/private/predictions.jsonl",
        "data/lockbox/lockbox-v1.jsonl",
        "data/lockbox/lockbox-v1.jsonl/child",
        "raw/private-predictions/run.jsonl",
        "private-corpora/rows.jsonl",
        ".cache/cache.bin",
        "adapters/run/adapter.bin",
        "checkpoints/run/model.bin",
        "logs/raw.log",
        "secrets/token.txt",
        ".env",
        ".env/child",
        ".ssh/id_ed25519",
    ),
)
def test_design_input_path_rejects_unsafe_or_denied_paths(relative_path: str) -> None:
    validator = getattr(design_module, "_validate_design_input_path", None)
    assert callable(validator)
    with pytest.raises(ValueError):
        validator(relative_path)


@pytest.mark.parametrize(
    "relative_path",
    (
        "data/lockbox/lockbox-v1.jsonl.safe",
        "logs-safe/summary.json",
        "reports/private-corpora-summary.json",
        "checkpoints.md",
        "reports/.env-safe.json",
    ),
)
def test_design_input_path_allows_safe_near_names(relative_path: str) -> None:
    validator = getattr(design_module, "_validate_design_input_path", None)
    assert callable(validator)
    assert validator(relative_path) == relative_path


def test_hash_and_text_reads_require_exact_whitelist_membership() -> None:
    source_text = getattr(design_module, "_source_text", None)
    sha256 = getattr(design_module, "_sha256", None)
    assert callable(source_text)
    assert callable(sha256)
    with pytest.raises(ValueError, match="whitelist"):
        source_text(REPO_ROOT, "README.md")
    with pytest.raises(ValueError, match="whitelist"):
        sha256(REPO_ROOT, "README.md")


def test_source_manifest_uses_all_and_only_frozen_whitelist_hashes() -> None:
    source_manifest = getattr(design_module, "_source_manifest", None)
    assert callable(source_manifest)
    manifest = source_manifest(REPO_ROOT)
    assert [record["path"] for record in manifest] == list(EXPECTED_DESIGN_INPUT_WHITELIST)
    assert {record["path"]: record["sha256"] for record in manifest} == (
        EXPECTED_SOURCE_SHA256
    )
    for path, expected in EXPECTED_SOURCE_SHA256.items():
        resolved = design_module._resolve_design_source_path(REPO_ROOT, path)
        assert hashlib.sha256(resolved.read_bytes()).hexdigest() == expected


def test_historical_context_snapshot_preserves_design_replay_after_live_context_advances() -> None:
    assert design_module.HISTORICAL_SOURCE_SNAPSHOT_OVERRIDES == {
        "CONTEXT.md": HISTORICAL_CONTEXT_SNAPSHOT,
        "data/public-samples/manifest_public_sample.json": HISTORICAL_MANIFEST_SNAPSHOT,
        "reports/public-sample/split-integrity-audit/summary.json": (
            HISTORICAL_SPLIT_SUMMARY_SNAPSHOT
        ),
    }
    snapshot = design_module._resolve_design_source_path(REPO_ROOT, "CONTEXT.md")
    assert snapshot == REPO_ROOT / HISTORICAL_CONTEXT_SNAPSHOT
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == HISTORICAL_CONTEXT_SHA256
    assert hashlib.sha256((REPO_ROOT / "CONTEXT.md").read_bytes()).hexdigest() != (
        HISTORICAL_CONTEXT_SHA256
    )


def test_historical_manifest_snapshot_preserves_design_replay_after_live_manifest_advances() -> None:
    snapshot = design_module._resolve_design_source_path(
        REPO_ROOT, "data/public-samples/manifest_public_sample.json"
    )
    assert snapshot == REPO_ROOT / HISTORICAL_MANIFEST_SNAPSHOT
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == HISTORICAL_MANIFEST_SHA256
    assert hashlib.sha256(
        (REPO_ROOT / "data/public-samples/manifest_public_sample.json").read_bytes()
    ).hexdigest() != HISTORICAL_MANIFEST_SHA256


def test_historical_split_summary_snapshot_preserves_design_replay_after_current_report_advances() -> None:
    snapshot = design_module._resolve_design_source_path(
        REPO_ROOT, "reports/public-sample/split-integrity-audit/summary.json"
    )
    assert snapshot == REPO_ROOT / HISTORICAL_SPLIT_SUMMARY_SNAPSHOT
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == HISTORICAL_SPLIT_SUMMARY_SHA256
    assert hashlib.sha256(
        (REPO_ROOT / "reports/public-sample/split-integrity-audit/summary.json").read_bytes()
    ).hexdigest() != HISTORICAL_SPLIT_SUMMARY_SHA256


def test_source_anchor_validation_fails_closed_on_authoritative_drift(
    monkeypatch: Any,
) -> None:
    validate_source_anchors = getattr(design_module, "_validate_source_anchors", None)
    source_text = getattr(design_module, "_source_text", None)
    assert callable(validate_source_anchors)
    assert callable(source_text)

    real_source_text = source_text

    def hide_anchor(repo_root: Path, relative_path: str) -> str:
        text = real_source_text(repo_root, relative_path)
        if relative_path == "CONTEXT.md":
            return text.replace("UNBOUND_BY_DESIGN", "REMOVED_ANCHOR", 1)
        return text

    monkeypatch.setattr(design_module, "_source_text", hide_anchor)
    with pytest.raises(ValueError, match="source anchor"):
        validate_source_anchors(REPO_ROOT)


@pytest.mark.parametrize("link_kind", ("final", "parent"))
def test_design_sources_reject_external_symlink_before_target_read(
    tmp_path: Path,
    monkeypatch: Any,
    link_kind: str,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    logical_path = EXPECTED_DESIGN_INPUT_WHITELIST[0]
    logical = repo_root / logical_path
    outside_target = outside / "summary.json"
    outside_target.write_text("outside-secret-sentinel", encoding="utf-8")

    if link_kind == "final":
        logical.parent.mkdir(parents=True)
        logical.symlink_to(outside_target)
    else:
        outside_parent = outside / "public-sample/contract-compiler-v2-causal-boundary"
        outside_parent.mkdir(parents=True)
        (outside_parent / "summary.json").write_text(
            "outside-secret-sentinel", encoding="utf-8"
        )
        (repo_root / "reports").symlink_to(outside, target_is_directory=True)

    reads: list[Path] = []
    real_read_bytes = Path.read_bytes

    def read_spy(path: Path) -> bytes:
        reads.append(path)
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_spy)
    for operation in (
        design_module._source_text,
        design_module._sha256,
        design_module.build_clean_matched_causal_evidence_design,
    ):
        arguments = (
            (repo_root, logical_path)
            if operation is not design_module.build_clean_matched_causal_evidence_design
            else (repo_root,)
        )
        with pytest.raises(ValueError, match="symlink|logical location|outside"):
            operation(*arguments)
    assert reads == []


def test_design_sources_reject_missing_file(tmp_path: Path) -> None:
    missing_root = tmp_path / "repo"
    missing_root.mkdir()
    for operation in (design_module._source_text, design_module._sha256):
        with pytest.raises(ValueError, match="missing"):
            operation(missing_root, EXPECTED_DESIGN_INPUT_WHITELIST[0])
    with pytest.raises(ValueError, match="missing"):
        design_module.build_clean_matched_causal_evidence_design(missing_root)


def test_design_build_rejects_real_source_hash_drift(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    for relative_path in EXPECTED_DESIGN_INPUT_WHITELIST:
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO_ROOT / relative_path).read_bytes())
    drifted = repo_root / EXPECTED_DESIGN_INPUT_WHITELIST[0]
    drifted.write_bytes(drifted.read_bytes() + b"x")

    with pytest.raises(ValueError, match="hash drift"):
        design_module.build_clean_matched_causal_evidence_design(repo_root)


@pytest.mark.parametrize(
    "relative_path",
    ("README.md", "data/lockbox/lockbox-v1.jsonl", "raw/private-predictions/run.jsonl"),
)
def test_rejected_design_path_performs_no_read(
    monkeypatch: Any,
    relative_path: str,
) -> None:
    reads: list[Path] = []

    def forbidden_read(path: Path) -> bytes:
        reads.append(path)
        raise AssertionError("rejected path must not be read")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    for operation in (design_module._source_text, design_module._sha256):
        with pytest.raises(ValueError):
            operation(REPO_ROOT, relative_path)
    assert reads == []


def test_design_build_reads_each_source_once_for_hash_text_and_anchors(
    monkeypatch: Any,
) -> None:
    read_source_bytes = getattr(design_module, "_read_design_source_bytes", None)
    assert callable(read_source_bytes)
    counts = {relative_path: 0 for relative_path in EXPECTED_DESIGN_INPUT_WHITELIST}

    def counted_read(repo_root: Path, relative_path: str) -> bytes:
        counts[relative_path] += 1
        if counts[relative_path] > 1:
            raise AssertionError(f"source read more than once: {relative_path}")
        return read_source_bytes(repo_root, relative_path)

    monkeypatch.setattr(design_module, "_read_design_source_bytes", counted_read)
    design = design_module.build_clean_matched_causal_evidence_design(REPO_ROOT)

    assert counts == {relative_path: 1 for relative_path in EXPECTED_DESIGN_INPUT_WHITELIST}
    assert [record["path"] for record in design["source_manifest"]] == list(
        EXPECTED_DESIGN_INPUT_WHITELIST
    )
    assert all(record["valid"] is True for record in design["source_anchor_validation"])


def test_design_schema_uses_one_exact_unbound_execution_inventory() -> None:
    build = getattr(design_module, "build_clean_matched_causal_evidence_design", None)
    assert callable(build)
    design = build(REPO_ROOT)
    assert getattr(design_module, "EXECUTION_BINDING_FIELDS", None) == (
        EXPECTED_EXECUTION_BINDING_FIELDS
    )
    assert len(EXPECTED_EXECUTION_BINDING_FIELDS) == 29
    assert design["execution_bindings"] == {
        field: "UNBOUND_BY_DESIGN" for field in EXPECTED_EXECUTION_BINDING_FIELDS
    }
    assert design["binding_inventory_count"] == 29
    assert design["unbound_binding_count"] == 29
    assert design["bound_binding_count"] == 0
    assert design["execution_bindings_complete"] is False


def test_design_terminal_statuses_are_exactly_blocked_design_only() -> None:
    build = getattr(design_module, "build_clean_matched_causal_evidence_design", None)
    assert callable(build)
    design = build(REPO_ROOT)
    assert design["methodology_version"] == "clean-matched-causal-evidence-design.v1"
    assert design["status"] == {
        "evidence_status": "DESIGN_ONLY",
        "decision": "PREREGISTRATION_DESIGN_READY_EXECUTION_BLOCKED",
        "design_contract_status": "REVIEWED_DESIGN_ONLY",
        "protocol_freeze_status": "NOT_FROZEN",
        "clean_population_status": "NOT_MATERIALIZED",
        "compiler_causal_identification": "CAUSAL_IDENTIFICATION_BLOCKED",
        "model_learning_causal_identification": "CAUSAL_IDENTIFICATION_BLOCKED",
        "experiment_preregistration_status": "NOT_EXECUTABLE",
        "execution_readiness": False,
    }


def test_readiness_lifecycle_is_ordered_and_only_design_only_is_reached() -> None:
    build = getattr(design_module, "build_clean_matched_causal_evidence_design", None)
    assert callable(build)
    design = build(REPO_ROOT)
    assert getattr(design_module, "READINESS_LIFECYCLE", None) == EXPECTED_READINESS_LIFECYCLE
    lifecycle = design["readiness_lifecycle"]
    assert [entry["state"] for entry in lifecycle] == list(EXPECTED_READINESS_LIFECYCLE)
    assert [entry["ordinal"] for entry in lifecycle] == list(range(6))
    assert [entry["reached"] for entry in lifecycle] == [True, False, False, False, False, False]
    assert design["current_readiness_state"] == "DESIGN_ONLY"
    assert design["maximum_state_this_change"] == "DESIGN_ONLY"
    assert design["state_skipping_allowed"] is False
    assert design["document_presence_implies_readiness"] is False


def test_design_emits_machine_readable_blockers_and_all_flags_false() -> None:
    build = getattr(design_module, "build_clean_matched_causal_evidence_design", None)
    assert callable(build)
    design = build(REPO_ROOT)
    assert {
        "execution_bindings_unbound",
        "protocol_not_frozen",
        "clean_population_not_materialized",
        "arm_artifacts_not_frozen",
        "one_look_not_eligible",
    } <= set(design["blocked_reasons"]["execution_readiness"])
    assert "no_clean_matched_compiler_comparison" in design["blocked_reasons"][
        "compiler_causal_identification"
    ]
    assert "no_clean_matched_multi_seed_model_comparison" in design["blocked_reasons"][
        "model_learning_causal_identification"
    ]
    assert set(design["execution_flags"]) == EXPECTED_FALSE_EXECUTION_FLAGS
    assert set(design["claim_flags"]) == EXPECTED_FALSE_CLAIM_FLAGS
    assert set(design["execution_flags"].values()) == {False}
    assert set(design["claim_flags"].values()) == {False}


def test_one_future_acquisition_defines_exactly_two_unmaterialized_partitions() -> None:
    design = design_module.build_clean_matched_causal_evidence_design(REPO_ROOT)
    population = design["population_design"]
    assert population["acquisition_plan_count"] == 1
    assert population["acquisition_status"] == "NOT_STARTED"
    assert population["family_registry_status"] == "NOT_CREATED"
    partitions = population["partitions"]
    assert [partition["id"] for partition in partitions] == [
        "compiler_system_evaluation",
        "model_learning_evaluation",
    ]
    for partition in partitions:
        assert partition["materialization_status"] == "NOT_MATERIALIZED"
        assert partition["membership_assignment_status"] == "NOT_ASSIGNED"
        assert partition["sealing_status"] == "NOT_SEALED"
        assert partition["one_look_state"] == "NOT_AVAILABLE"
        assert partition["future_family_disjoint"] is True
    assert population["partition_count"] == 2
    assert population["shared_sequential_partition"] is False


def test_partition_mechanics_freeze_before_acquisition_and_assign_future_families_once() -> None:
    population = design_module.build_clean_matched_causal_evidence_design(REPO_ROOT)[
        "population_design"
    ]
    mechanics = population["partition_mechanics"]
    assert mechanics["freeze_required_before_acquisition"] is True
    assert mechanics["protocol_frozen_now"] is False
    assert mechanics["mechanics_bindings"] == {
        field: "UNBOUND_BY_DESIGN"
        for field in (
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
    }
    assignment = population["future_membership_assignment"]
    assert assignment["source"] == "future_source_hashed_acquisition_frame"
    assert assignment["unit"] == "semantic_family"
    assert assignment["assignment_count"] == "EXACTLY_ONCE_IN_FUTURE_MATERIALIZATION"
    assert assignment["before"] == [
        "row_authoring",
        "annotation",
        "gold_access",
        "outcome_access",
    ]
    assert assignment["realized_counts_are_design_bindings"] is False
    assert assignment["membership_attestation_created_now"] is False
    assert population["partition_mechanics_frozen_now"] is False


def test_partition_lineage_one_look_and_no_row_boundaries_are_fail_closed() -> None:
    population = design_module.build_clean_matched_causal_evidence_design(REPO_ROOT)[
        "population_design"
    ]
    lineage = population["lineage_contract"]
    assert {
        "current_public_train",
        "current_public_dev",
        "current_public_test",
        "remediation_artifacts",
        "challenge_artifacts",
        "prediction_artifacts",
        "lockbox_v1",
    } == set(lineage["excluded_ancestry"])
    assert lineage["predeclared_disjointness_checks"] == [
        "exact",
        "normalized",
        "template",
        "semantic_family",
        "provenance",
    ]
    assert lineage["lockbox_overlap_interface"] == "SEALED_AGGREGATE_ATTESTATION_ONLY"
    assert lineage["lockbox_row_access"] is False
    assert lineage["new_creation_timestamp_establishes_cleanliness"] is False
    assert lineage["synthetic_origin_establishes_natural_asr"] is False

    rules = population["family_disjointness_rules"]
    assert rules["one_family_in_exactly_one_evaluation_partition"] is True
    assert rules["training_use"] is False
    assert rules["development_use"] is False
    assert rules["remediation_use"] is False
    assert rules["challenge_use"] is False
    assert rules["post_hoc_repartitioning"] is False
    assert rules["outcome_aware_allocation"] is False

    one_look = population["independent_one_look_contract"]
    assert one_look["compiler_open_consumes"] == ["compiler_system_evaluation"]
    assert one_look["compiler_open_preserves"] == ["model_learning_evaluation"]
    assert one_look["cross_partition_inspection"] is False
    assert one_look["compiler_result_driven_model_changes"] is False
    assert one_look["partition_reuse_for_other_estimand"] is False

    assert population["artifacts_created"] == {
        "clean_rows": False,
        "family_registry": False,
        "partition_membership": False,
        "clean_manifest": False,
        "gold_labels": False,
        "predictions": False,
    }
    assert population["claims_allowed"] == {
        "clean_independent_evidence": False,
        "natural_asr": False,
        "population_materialized": False,
        "partitions_sealed": False,
    }


def test_compiler_card_is_full_itt_paired_and_family_clustered() -> None:
    design = design_module.build_clean_matched_causal_evidence_design(REPO_ROOT)
    card = design["preregistration_cards"]["compiler_system"]
    assert card["partition"] == "compiler_system_evaluation"
    assert card["observation_unit"] == "one_frozen_raw_record"
    assert card["bindings"] == {
        "compiler_control": "UNBOUND_BY_DESIGN",
        "compiler_intervention": "UNBOUND_BY_DESIGN",
    }
    assert card["future_named_arm_requirements"] == {
        "control": "one_named_identity_or_preserve_legacy_path",
        "intervention": "one_named_candidate_compiler",
        "complete_now": False,
    }
    assert card["primary_outcome"] == "compiled_v1_strict_exact_full_population_itt"
    assert card["primary_denominator"] == "complete_fixed_eligible_population"
    assert card["primary_failure_categories"] == [
        "invalid",
        "renderer_unsupported",
        "compiler_error",
        "missing",
    ]
    assert card["supported_only_secondary_diagnostic"] is True
    assert card["supported_only_denominator_must_be_printed"] is True
    assert {
        "byte_identical_model_output",
        "semantic_core_identity",
        "legacy_envelope_metadata_identity",
        "row_and_order_identity",
        "source_hash_identity",
        "prompt_and_decoding_provenance_identity",
        "evaluator_version_identity",
        "no_prediction_repair",
    } == set(card["arm_invariants"])
    assert card["paired_analysis"] == {
        "record_contrast": "paired_within_record_before_aggregation",
        "family_aggregation": "aggregate_record_contrasts_within_semantic_family",
        "interval": "family_clustered_paired_or_randomization_method_UNBOUND_BY_DESIGN",
        "row_independence_assumed": False,
        "multiplicity_bound_before_outcomes": True,
    }
    assert card["guardrails"] == ["safety", "confirmation", "slots", "executable_gates"]
    assert card["negative_controls"] == [
        "constant_only",
        "field_copy_only",
        "policy_default_only",
        "evaluation_plumbing",
    ]
    assert card["effect_label_if_future_identified"] == (
        "system_compiler_transformation_effect"
    )
    assert card["causal_identification"] == "CAUSAL_IDENTIFICATION_BLOCKED"


def test_model_card_allows_exactly_one_intervention_and_retains_all_assigned_seeds() -> None:
    design = design_module.build_clean_matched_causal_evidence_design(REPO_ROOT)
    card = design["preregistration_cards"]["model_learning"]
    assert card["partition"] == "model_learning_evaluation"
    assert card["observation_unit"] == "one_preregistered_evaluation_family"
    assert card["bindings"] == {
        "model_control": "UNBOUND_BY_DESIGN",
        "model_training_intervention": "UNBOUND_BY_DESIGN",
        "paired_model_seed_list": "UNBOUND_BY_DESIGN",
    }
    assert card["exactly_one_training_intervention_required"] is True
    assert card["bound_training_intervention_count"] == 0
    assert card["matched_arm_requirements"] == [
        "data_boundary_identity",
        "prompt_identity",
        "output_schema_identity",
        "decoding_identity",
        "compiler_policy_identity",
        "evaluator_version_identity",
        "optimization_budget_identity",
        "eligible_evaluation_population_identity",
    ]
    assert card["minimum_assigned_paired_seeds"] == 3
    assert card["assigned_seed_list_status"] == "UNBOUND_BY_DESIGN"
    assert card["primary_seed_denominator"] == "all_assigned_paired_seeds"
    assert card["seed_failure_policy"]["failure_codes"] == [
        "MISSING_CONTROL_ARM",
        "MISSING_INTERVENTION_ARM",
        "TRAINING_FAILURE",
        "INVALID_EVALUATION",
    ]
    assert card["seed_failure_policy"]["drop_seed"] is False
    assert card["seed_failure_policy"]["replace_seed"] is False
    assert card["seed_failure_policy"]["selective_rerun"] is False
    assert card["aggregation_order"] == [
        "aggregate_within_semantic_family_for_each_assigned_seed",
        "pair_same_assigned_seed_list_across_arms",
        "retain_failure_coded_seeds_in_primary_itt",
    ]
    assert card["primary_outcome_scope"] == "model_authored_fields_only"
    assert set(card["model_authored_outcomes"]) == {"intent", "slots", "risk", "clarification"}
    assert {
        "compiler_filled_constants",
        "route",
        "safety",
        "confirmation",
        "normalized_command",
        "language",
        "contract_version",
        "compiled_full_v1_exact",
    } == set(card["excluded_primary_outcomes"])
    assert card["bundled_pipeline_comparison_identifies_model_learning"] is False
    assert card["pipeline_metrics_reported_separately"] is True
    assert card["causal_identification"] == "CAUSAL_IDENTIFICATION_BLOCKED"


def test_power_and_uncertainty_contracts_are_separate_pre_outcome_and_hierarchical() -> None:
    design = design_module.build_clean_matched_causal_evidence_design(REPO_ROOT)
    contracts = design["power_and_uncertainty"]
    compiler = contracts["compiler_system"]
    model = contracts["model_learning"]
    assert compiler["bound_before_clean_outcomes"] is True
    assert model["bound_before_clean_outcomes"] is True
    assert compiler["binding_values"] == {
        field: "UNBOUND_BY_DESIGN"
        for field in (
            "compiler_effect_scale",
            "compiler_mde_or_sensitivity_target",
            "compiler_target_power_or_beta",
            "alpha",
            "compiler_family_variance_or_icc_assumption",
            "compiler_interval_and_multiplicity_method",
            "guardrail_margins",
            "stop_rules",
        )
    }
    assert model["binding_values"] == {
        field: "UNBOUND_BY_DESIGN"
        for field in (
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
    }
    assert compiler["dependence_structure"] == ["paired_record", "semantic_family_cluster"]
    assert model["dependence_structure"] == ["semantic_family_cluster", "paired_seed"]
    assert compiler["row_independent_interval_allowed"] is False
    assert model["row_independent_interval_allowed"] is False
    assert model["incomplete_seed_deletion_allowed"] is False
    assert contracts["historical_inputs"] == "AGGREGATE_ONLY_SENSITIVITY_INPUTS"
    assert contracts["resize_after_clean_outcome_access"] is False
    assert contracts["repartition_after_clean_outcome_access"] is False
    assert contracts["select_after_clean_outcome_access"] is False


def test_invariants_negative_controls_and_single_next_phase_fail_closed() -> None:
    design = design_module.build_clean_matched_causal_evidence_design(REPO_ROOT)
    hard_stops = {record["code"]: record for record in design["hard_stops"]}
    assert set(hard_stops) == {
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
    }
    assert {record["action"] for record in hard_stops.values()} == {
        "STOP_READINESS_NO_CAUSAL_CLAIM"
    }
    assert all(record["machine_checkable"] is True for record in hard_stops.values())
    invariant_names = {record["name"] for record in design["invariant_matrix"]}
    assert {
        "source_hashes_match",
        "execution_bindings_complete_before_freeze",
        "family_partition_disjointness",
        "no_early_outcome_access",
        "compiler_arm_identity_except_compiler",
        "model_arm_identity_except_one_training_intervention",
        "all_assigned_seeds_retained",
        "one_look_state_independence",
    } <= invariant_names
    assert set(design["negative_controls"]) == {
        "constant_only",
        "field_copy_only",
        "policy_default_only",
        "evaluation_plumbing",
        "compiler_filled_fields_not_model_learning",
    }
    assert design["next_phase_recommendations"] == [
        {
            "change": "materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1",
            "executed": False,
            "separate_review_required": True,
            "may_run_compiler_or_model_experiment": False,
        }
    ]


def test_renderer_writes_byte_deterministic_complete_json_and_markdown(tmp_path: Path) -> None:
    render = getattr(design_module, "render_clean_matched_causal_evidence_design", None)
    summary_markdown = getattr(design_module, "_summary_markdown", None)
    assert callable(render)
    assert callable(summary_markdown)

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_paths = render(REPO_ROOT, first_dir)
    second_paths = render(REPO_ROOT, second_dir)
    assert [path.name for path in first_paths] == ["summary.json", "summary.md"]
    assert [path.name for path in second_paths] == ["summary.json", "summary.md"]
    assert (first_dir / "summary.json").read_bytes() == (second_dir / "summary.json").read_bytes()
    assert (first_dir / "summary.md").read_bytes() == (second_dir / "summary.md").read_bytes()

    payload = json.loads((first_dir / "summary.json").read_text(encoding="utf-8"))
    assert payload == design_module.build_clean_matched_causal_evidence_design(REPO_ROOT)
    assert len(payload["source_manifest"]) == 10
    markdown = (first_dir / "summary.md").read_text(encoding="utf-8")
    for exact_truth in (
        "evidence_status=DESIGN_ONLY",
        "decision=PREREGISTRATION_DESIGN_READY_EXECUTION_BLOCKED",
        "design_contract_status=REVIEWED_DESIGN_ONLY",
        "protocol_freeze_status=NOT_FROZEN",
        "clean_population_status=NOT_MATERIALIZED",
        "experiment_preregistration_status=NOT_EXECUTABLE",
        "execution_readiness=false",
        "compiler_causal_identification=CAUSAL_IDENTIFICATION_BLOCKED",
        "model_learning_causal_identification=CAUSAL_IDENTIFICATION_BLOCKED",
    ):
        assert exact_truth in markdown
    assert "compiler_system_evaluation" in markdown
    assert "model_learning_evaluation" in markdown
    assert "29 / 29 execution bindings remain `UNBOUND_BY_DESIGN`" in markdown
    assert "No clean row, family registry, membership, gold label, or prediction was created" in markdown
    assert "materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1" in markdown
    assert "executed=false" in markdown
