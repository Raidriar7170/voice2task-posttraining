import json
from pathlib import Path
from typing import Any

import voice2task.evaluation as evaluation
import voice2task.reports as reports
from voice2task.cli import eval as eval_cli
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-confirmation-field-policy"
CASE_DESIGN_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-remediation-case-design"
MATERIALIZATION_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-remediation-materialized-candidates"
MERGE_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-remediation-public-sample-merge"
RESIDUAL_CLUSTER_DIR = REPO_ROOT / "reports" / "public-sample" / "formal-heldout-residual-cluster-inspection"
COVERAGE_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-confirmation-marker-coverage"
HUMAN_BRIEF = (
    REPO_ROOT
    / "docs"
    / "human-briefs"
    / "2026-06-16-assess-form-fill-confirmation-marker-coverage.html"
)
ARCHIVED_CHANGE_DIR = (
    REPO_ROOT
    / "openspec"
    / "changes"
    / "archive"
    / "2026-06-16-assess-form-fill-confirmation-marker-coverage"
)


def _inputs() -> dict[str, dict[str, Any]]:
    return {
        "policy": read_json(POLICY_DIR / "form_fill_confirmation_field_policy.json"),
        "case_design": read_json(CASE_DESIGN_DIR / "form_fill_remediation_case_design.json"),
        "materialization": read_json(MATERIALIZATION_DIR / "form_fill_remediation_materialization.json"),
        "merge": read_json(MERGE_DIR / "form_fill_remediation_public_sample_merge.json"),
        "residual_clusters": read_json(RESIDUAL_CLUSTER_DIR / "formal_heldout_residual_cluster_inspection.json"),
    }


def _coverage() -> dict[str, Any]:
    assert hasattr(evaluation, "assess_form_fill_confirmation_marker_coverage")
    return evaluation.assess_form_fill_confirmation_marker_coverage(**_inputs())


def test_confirmation_marker_coverage_assessment_preserves_policy_and_legacy_sources() -> None:
    coverage = _coverage()

    assert coverage["evidence_kind"] == "form_fill_confirmation_marker_coverage_assessment"
    assert coverage["assessment_kind"] == "public_form_fill_confirmation_marker_coverage"
    assert coverage["source_artifacts"] == {
        "policy": "reports/public-sample/form-fill-confirmation-field-policy/form_fill_confirmation_field_policy.json",
        "case_design": "reports/public-sample/form-fill-remediation-case-design/form_fill_remediation_case_design.json",
        "materialization": (
            "reports/public-sample/form-fill-remediation-materialized-candidates/"
            "form_fill_remediation_materialization.json"
        ),
        "merge": (
            "reports/public-sample/form-fill-remediation-public-sample-merge/"
            "form_fill_remediation_public_sample_merge.json"
        ),
        "residual_cluster_inspection": (
            "reports/public-sample/formal-heldout-residual-cluster-inspection/"
            "formal_heldout_residual_cluster_inspection.json"
        ),
        "source_residual_diagnosis": (
            "reports/public-sample/formal-heldout-residual-family-diagnosis/"
            "formal_heldout_residual_family_diagnosis.json"
        ),
        "source_formal_heldout_evidence": {
            "base_model": "Qwen/Qwen2.5-7B-Instruct",
            "dataset_manifest_id": "public-sample-20260616T074315Z",
            "evidence_kind": "a100_formal_public_heldout_prediction",
            "overall_interpretation": "formal_public_heldout_partial_signal",
            "prediction_splits": ["dev", "test"],
        },
    }
    assert coverage["source_count_consistency"] == {
        "ok": True,
        "policy_cluster_row_incidence_total": 27,
        "current_top_cluster_residual_rows": 27,
        "policy_residual_field_total": 27,
        "current_top_cluster_residual_fields": 27,
        "case_design_candidate_count": 3,
        "materialized_candidate_seed_count": 3,
        "materialized_candidate_sft_count": 3,
        "policy_cluster_rows_match_current_top_cluster": True,
        "policy_residual_fields_match_current_top_cluster": True,
        "case_design_count_matches_materialized_seed_count": True,
        "case_design_count_matches_materialized_sft_count": True,
        "residual_cluster_source_count_consistency": {
            "clustered_residual_fields": 204,
            "clustered_residual_rows": 97,
            "expected_residual_fields": 204,
            "expected_residual_rows": 97,
            "ok": True,
        },
    }
    assert coverage["source_policy"]["source_manifest_id"] == "public-sample-20260616T022151Z"
    assert coverage["source_policy"]["policy_bucket"] == "missing_confirmation_marker"
    assert coverage["source_policy"]["cluster_row_incidence_total"] == 27
    assert coverage["source_policy"]["residual_field_total"] == 27
    assert coverage["source_policy"]["source_family_count"] == 12
    assert coverage["source_policy"]["field_paths"] == ["normalized_command"]

    assert coverage["existing_remediation"]["legacy_bucket"] == "confirmation_marker_missing_or_reordered"
    assert coverage["existing_remediation"]["case_design_candidate_count"] == 3
    assert coverage["existing_remediation"]["materialized_candidate_seed_count"] == 3
    assert coverage["existing_remediation"]["materialized_candidate_sft_count"] == 3
    assert coverage["existing_remediation"]["represented_field_labels"] == ["发票抬头", "手机号", "收货地址"]
    assert coverage["existing_remediation"]["all_candidate_patterns_preserve_confirmation_marker"] is True
    assert coverage["existing_remediation"]["merge_status"] == "formal_public_sample_rebuilt"
    assert coverage["existing_remediation"]["candidate_dpo_pairs"] == 81
    assert coverage["existing_remediation"]["formal_public_sample_counts"] == {
        "dpo_pairs": 742,
        "seed_rows": 86,
        "sft_rows": 240,
    }

    assert coverage["current_residual_status"]["residual_still_observed"] is True
    assert coverage["current_residual_status"]["top_cluster_field_path"] == "normalized_command"
    assert coverage["current_residual_status"]["top_cluster_residual_rows"] == 27
    assert coverage["current_residual_status"]["top_cluster_residual_fields"] == 27

    assert coverage["summary"]["coverage_decision"] == "partial_legacy_coverage_current_residual_still_observed"
    assert coverage["summary"]["legacy_candidate_field_label_count"] == 3
    assert coverage["summary"]["policy_source_family_count"] == 12
    assert coverage["summary"]["represented_field_label_to_source_family_ratio"] == 0.25
    assert coverage["summary"]["recommended_next_step"] == (
        "propose_bounded_confirmation_marker_coverage_extension_before_training"
    )


def test_confirmation_marker_coverage_assessment_bounds_changes_and_claims() -> None:
    coverage = _coverage()

    assert coverage["metric_authority"]["contract_exact_match"] == "authoritative_strict_metric"
    assert coverage["metric_authority"]["slot_f1"] == "authoritative_strict_metric"
    assert coverage["metric_authority"]["slot_f1_soft"] == "diagnostic_only_not_primary"

    assert coverage["execution_scope"]["committed_public_artifacts_read"] is True
    for flag in [
        "raw_predictions_read",
        "new_candidate_rows_generated",
        "dataset_mutation",
        "public_sample_modified",
        "seed_traces_modified",
        "sft_rows_modified",
        "dpo_pairs_modified",
        "held_out_gold_labels_modified",
        "gold_policy_change",
        "prompt_change",
        "prediction_run",
        "prediction_replacement",
        "prediction_rescore",
        "training_run",
        "checkpoints_or_adapters_modified",
        "a100_job",
        "evaluator_metric_change",
        "evaluator_relaxation",
        "prediction_repair",
    ]:
        assert coverage["execution_scope"][flag] is False

    assert coverage["claims"]["coverage_assessment_only"] is True
    for claim in [
        "adapter_release_claim",
        "checkpoint_release_claim",
        "held_out_recovery_claim",
        "live_browser_benchmark_claim",
        "model_recovery_claim",
        "private_corpus_generalization_claim",
        "production_readiness_claim",
        "public_full_corpus_release_claim",
        "semantic_equivalence_primary_metric",
        "soft_slot_f1_primary_metric",
    ]:
        assert coverage["claims"][claim] is False

    unsupported = {entry["change"] for entry in coverage["unsupported_changes"]}
    assert {
        "data_mutation",
        "prompt_change",
        "training_run",
        "evaluator_relaxation",
        "prediction_repair",
        "held_out_recovery_claim",
    }.issubset(unsupported)


def test_confirmation_marker_coverage_cli_writes_public_safe_report(
    tmp_path: Path,
    capsys: Any,
) -> None:
    output_dir = tmp_path / "confirmation-marker-coverage"

    assert (
        eval_cli.main(
            [
                "assess-form-fill-confirmation-marker-coverage",
                "--policy",
                (POLICY_DIR / "form_fill_confirmation_field_policy.json").as_posix(),
                "--case-design",
                (CASE_DESIGN_DIR / "form_fill_remediation_case_design.json").as_posix(),
                "--materialization",
                (MATERIALIZATION_DIR / "form_fill_remediation_materialization.json").as_posix(),
                "--merge",
                (MERGE_DIR / "form_fill_remediation_public_sample_merge.json").as_posix(),
                "--residual-clusters",
                (RESIDUAL_CLUSTER_DIR / "formal_heldout_residual_cluster_inspection.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    json_path = output_dir / "form_fill_confirmation_marker_coverage.json"
    markdown_path = output_dir / "form_fill_confirmation_marker_coverage.md"
    manifest_path = output_dir / "manifest.json"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == json_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()
    assert cli_output["paths"]["manifest"] == manifest_path.as_posix()

    coverage = read_json(json_path)
    manifest = read_json(manifest_path)
    markdown = markdown_path.read_text(encoding="utf-8")
    assert coverage["summary"]["coverage_decision"] == "partial_legacy_coverage_current_residual_still_observed"
    assert manifest["evidence_kind"] == "form_fill_confirmation_marker_coverage_assessment"
    assert manifest["source_artifacts"] == coverage["source_artifacts"]
    assert manifest["source_count_consistency"]["ok"] is True
    assert manifest["artifact_policy"]["data_mutation"] is False
    for flag in [
        "raw_predictions_copied_to_git",
        "raw_logs_copied_to_git",
        "checkpoints_or_adapters_copied_to_git",
        "private_overrides_copied_to_git",
        "new_candidate_rows_generated",
        "data_mutation",
        "dataset_mutation",
        "public_sample_modified",
        "seed_traces_modified",
        "sft_rows_modified",
        "dpo_pairs_modified",
        "held_out_gold_labels_modified",
        "prompt_change",
        "gold_policy_change",
        "training_run",
        "checkpoints_or_adapters_modified",
        "prediction_run",
        "a100_job",
        "evaluator_metric_change",
        "evaluator_relaxation",
        "prediction_repair",
        "prediction_replacement",
        "prediction_rescore",
        "soft_metric_promotion",
    ]:
        assert manifest["artifact_policy"][flag] is False
    assert "coverage assessment only" in markdown
    assert "partial legacy coverage" in markdown
    assert scan_paths([output_dir]).ok is True

    assert hasattr(reports, "write_form_fill_confirmation_marker_coverage_report")
    direct_paths = reports.write_form_fill_confirmation_marker_coverage_report(coverage, tmp_path / "direct")
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_confirmation_marker_coverage_artifacts_are_fresh_bounded_and_public_safe() -> None:
    coverage = read_json(COVERAGE_DIR / "form_fill_confirmation_marker_coverage.json")
    manifest = read_json(COVERAGE_DIR / "manifest.json")
    markdown = (COVERAGE_DIR / "form_fill_confirmation_marker_coverage.md").read_text(encoding="utf-8")
    regenerated = _coverage()

    assert coverage == regenerated
    assert manifest["evidence_kind"] == "form_fill_confirmation_marker_coverage_assessment"
    assert manifest["source_artifacts"] == coverage["source_artifacts"]
    assert manifest["source_count_consistency"] == coverage["source_count_consistency"]
    assert manifest["summary"]["coverage_decision"] == "partial_legacy_coverage_current_residual_still_observed"
    assert manifest["claims"]["held_out_recovery_claim"] is False
    assert manifest["artifact_policy"]["prompt_change"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert manifest["artifact_policy"]["evaluator_relaxation"] is False
    assert coverage["current_residual_status"]["residual_still_observed"] is True
    assert "no held-out recovery claim" in markdown

    assert HUMAN_BRIEF.exists()
    assert ARCHIVED_CHANGE_DIR.exists()
    assert scan_paths([COVERAGE_DIR, HUMAN_BRIEF, ARCHIVED_CHANGE_DIR]).ok is True
