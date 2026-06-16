import json
from pathlib import Path
from typing import Any

import voice2task.evaluation as evaluation
import voice2task.reports as reports
from voice2task.cli import eval as eval_cli
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
COVERAGE_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-confirmation-marker-coverage"
POLICY_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-confirmation-field-policy"
EXTENSION_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-confirmation-marker-coverage-extension"
HUMAN_BRIEF = (
    REPO_ROOT
    / "docs"
    / "human-briefs"
    / "2026-06-16-extend-form-fill-confirmation-marker-coverage.html"
)
ARCHIVED_CHANGE_DIR = (
    REPO_ROOT
    / "openspec"
    / "changes"
    / "archive"
    / "2026-06-16-extend-form-fill-confirmation-marker-coverage"
)


def _inputs() -> dict[str, dict[str, Any]]:
    return {
        "coverage": read_json(COVERAGE_DIR / "form_fill_confirmation_marker_coverage.json"),
        "policy": read_json(POLICY_DIR / "form_fill_confirmation_field_policy.json"),
    }


def _extension() -> dict[str, Any]:
    assert hasattr(evaluation, "design_form_fill_confirmation_marker_coverage_extension")
    return evaluation.design_form_fill_confirmation_marker_coverage_extension(**_inputs())


def test_confirmation_marker_extension_design_preserves_sources_and_counts() -> None:
    extension = _extension()

    assert extension["evidence_kind"] == "form_fill_confirmation_marker_coverage_extension_design"
    assert extension["design_kind"] == "public_form_fill_confirmation_marker_coverage_extension"
    assert extension["source_artifacts"] == {
        "coverage": (
            "reports/public-sample/form-fill-confirmation-marker-coverage/"
            "form_fill_confirmation_marker_coverage.json"
        ),
        "policy": "reports/public-sample/form-fill-confirmation-field-policy/form_fill_confirmation_field_policy.json",
    }
    assert extension["source_manifest_id"] == "public-sample-20260616T022151Z"
    assert extension["source_bucket"] == "missing_confirmation_marker"
    assert extension["source_count_consistency"] == {
        "ok": True,
        "coverage_policy_source_family_counts_match": True,
        "source_family_count": 12,
        "proposed_case_count": 12,
        "represented_source_family_count": 12,
        "source_family_incidence_total": 27,
        "policy_cluster_row_incidence_total": 27,
        "policy_residual_field_total": 27,
        "coverage_cluster_row_incidence_total": 27,
        "coverage_residual_field_total": 27,
        "proposed_case_count_matches_source_family_count": True,
        "incidence_total_matches_policy_cluster_rows": True,
        "incidence_total_matches_policy_residual_fields": True,
    }
    assert extension["summary"] == {
        "design_decision": "extend_confirmation_marker_coverage_with_source_family_cases",
        "source_family_count": 12,
        "proposed_case_count": 12,
        "represented_source_family_count": 12,
        "represented_source_family_incidence_total": 27,
        "uncovered_source_family_count_after_design": 0,
        "legacy_confirmation_candidate_case_count": 3,
        "legacy_candidate_field_label_count": 3,
        "field_labels_derived_count": 3,
        "field_labels_not_derivable_count": 9,
        "recommended_next_step": "materialize_bounded_confirmation_marker_extension_candidates_in_later_phase",
    }


def test_confirmation_marker_extension_design_cases_are_family_level_and_public_safe() -> None:
    extension = _extension()
    cases = extension["proposed_candidate_cases"]

    assert len(cases) == 12
    assert [case["source_family_id"] for case in cases] == sorted(
        extension["source_family_counts"].keys()
    )
    assert sum(case["source_family_incidence_count"] for case in cases) == 27
    assert extension["represented_source_families"] == sorted(extension["source_family_counts"])
    assert extension["uncovered_source_families_after_design"] == []

    derived = {
        case["source_family_id"]: case["derived_field_label"]
        for case in cases
        if case["field_label_derivation_status"] == "derived_from_committed_coverage_examples"
    }
    assert derived == {
        "family-form_fill-dev-1": "手机号",
        "family-form_fill-dev-2": "收货地址",
        "family-form_fill-dev-3": "发票抬头",
    }
    assert sum(
        case["field_label_derivation_status"] == "not_derivable_from_committed_coverage_policy_artifacts"
        for case in cases
    ) == 9
    for case in cases:
        assert case["case_id"].startswith("ff-confirm-marker-extension-")
        assert case["source_manifest_id"] == "public-sample-20260616T022151Z"
        assert case["source_bucket"] == "missing_confirmation_marker"
        assert case["field_paths"] == ["normalized_command"]
        assert case["expected_confirmation_marker"] == "并确认"
        assert case["materialization_status"] == "not_materialized"
        assert case["recommended_split_role"] == "candidate_design_only"
        assert case["requires_later_openspec_materialization"] is True


def test_confirmation_marker_extension_design_bounds_changes_and_claims() -> None:
    extension = _extension()

    assert extension["metric_authority"]["contract_exact_match"] == "authoritative_strict_metric"
    assert extension["metric_authority"]["slot_f1"] == "authoritative_strict_metric"
    assert extension["metric_authority"]["slot_f1_soft"] == "diagnostic_only_not_primary"

    assert extension["execution_scope"]["committed_public_artifacts_read"] is True
    for flag in [
        "raw_predictions_read",
        "new_candidate_rows_generated",
        "dataset_mutation",
        "public_sample_modified",
        "seed_traces_modified",
        "sft_rows_modified",
        "dpo_pairs_modified",
        "held_out_gold_labels_modified",
        "prompt_change",
        "gold_policy_change",
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
        assert extension["execution_scope"][flag] is False

    assert extension["claims"]["design_only"] is True
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
        assert extension["claims"][claim] is False


def test_confirmation_marker_extension_cli_writes_public_safe_report(
    tmp_path: Path,
    capsys: Any,
) -> None:
    output_dir = tmp_path / "confirmation-marker-coverage-extension"

    assert (
        eval_cli.main(
            [
                "design-form-fill-confirmation-marker-coverage-extension",
                "--coverage",
                (COVERAGE_DIR / "form_fill_confirmation_marker_coverage.json").as_posix(),
                "--policy",
                (POLICY_DIR / "form_fill_confirmation_field_policy.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    json_path = output_dir / "form_fill_confirmation_marker_coverage_extension.json"
    markdown_path = output_dir / "form_fill_confirmation_marker_coverage_extension.md"
    manifest_path = output_dir / "manifest.json"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == json_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()
    assert cli_output["paths"]["manifest"] == manifest_path.as_posix()

    extension = read_json(json_path)
    manifest = read_json(manifest_path)
    markdown = markdown_path.read_text(encoding="utf-8")
    assert extension["summary"]["design_decision"] == (
        "extend_confirmation_marker_coverage_with_source_family_cases"
    )
    assert manifest["evidence_kind"] == "form_fill_confirmation_marker_coverage_extension_design"
    assert manifest["source_count_consistency"]["ok"] is True
    assert manifest["artifact_policy"]["data_mutation"] is False
    assert manifest["artifact_policy"]["new_candidate_rows_generated"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert manifest["artifact_policy"]["prediction_repair"] is False
    assert "design-only" in markdown
    assert "no held-out recovery claim" in markdown
    assert scan_paths([output_dir]).ok is True

    assert hasattr(reports, "write_form_fill_confirmation_marker_coverage_extension_report")
    direct_paths = reports.write_form_fill_confirmation_marker_coverage_extension_report(
        extension,
        tmp_path / "direct",
    )
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_confirmation_marker_extension_artifacts_are_fresh_bounded_and_public_safe() -> None:
    extension = read_json(EXTENSION_DIR / "form_fill_confirmation_marker_coverage_extension.json")
    manifest = read_json(EXTENSION_DIR / "manifest.json")
    markdown = (
        EXTENSION_DIR / "form_fill_confirmation_marker_coverage_extension.md"
    ).read_text(encoding="utf-8")
    regenerated = _extension()

    assert extension == regenerated
    assert manifest["evidence_kind"] == "form_fill_confirmation_marker_coverage_extension_design"
    assert manifest["source_artifacts"] == extension["source_artifacts"]
    assert manifest["source_count_consistency"] == extension["source_count_consistency"]
    assert manifest["summary"]["design_decision"] == (
        "extend_confirmation_marker_coverage_with_source_family_cases"
    )
    assert manifest["claims"]["held_out_recovery_claim"] is False
    assert manifest["artifact_policy"]["prompt_change"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert manifest["artifact_policy"]["evaluator_relaxation"] is False
    assert extension["summary"]["proposed_case_count"] == 12
    assert "no held-out recovery claim" in markdown

    assert HUMAN_BRIEF.exists()
    assert ARCHIVED_CHANGE_DIR.exists()
    assert scan_paths([EXTENSION_DIR, HUMAN_BRIEF, ARCHIVED_CHANGE_DIR]).ok is True
