import json
from pathlib import Path
from typing import Any

import voice2task.evaluation as evaluation
import voice2task.reports as reports
from voice2task.cli import eval as eval_cli
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-boundary-field-specificity-inspection"
POLICY_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-confirmation-field-policy"
HUMAN_BRIEF = (
    REPO_ROOT
    / "docs"
    / "human-briefs"
    / "2026-06-16-define-form-fill-confirmation-field-policy.html"
)
ARCHIVED_CHANGE_DIR = (
    REPO_ROOT
    / "openspec"
    / "changes"
    / "archive"
    / "2026-06-16-define-form-fill-confirmation-field-policy"
)


def _source_inspection() -> dict[str, Any]:
    return read_json(INSPECTION_DIR / "form_fill_boundary_field_specificity_inspection.json")


def _policy() -> dict[str, Any]:
    assert hasattr(evaluation, "define_form_fill_confirmation_field_policy")
    return evaluation.define_form_fill_confirmation_field_policy(form_fill_inspection=_source_inspection())


def test_form_fill_confirmation_field_policy_preserves_source_evidence_and_metric_authority() -> None:
    policy = _policy()

    assert policy["evidence_kind"] == "form_fill_confirmation_field_policy"
    assert policy["policy_kind"] == "public_form_fill_confirmation_and_field_specificity_policy"
    assert policy["source_form_fill_inspection"]["source_manifest_id"] == "public-sample-20260616T022151Z"
    assert policy["source_form_fill_inspection"]["inspection_artifact"] == (
        "reports/public-sample/form-fill-boundary-field-specificity-inspection/"
        "form_fill_boundary_field_specificity_inspection.json"
    )
    assert policy["summary"]["source_bucket_count"] == 3
    assert policy["summary"]["cluster_row_incidence_total"] == 49
    assert policy["summary"]["residual_field_total"] == 49
    assert policy["summary"]["policy_section_count"] == 3
    assert policy["summary"]["strict_contract_exact_match"] == {
        "dev": 0.30434782608695654,
        "test": 0.2898550724637681,
    }
    assert policy["summary"]["strict_slot_f1"] == {
        "dev": 0.391304347826087,
        "test": 0.5072463768115942,
    }
    assert policy["summary"]["slot_f1_soft"] == {
        "dev": 0.7315387631291138,
        "test": 0.7609315000619348,
    }
    assert policy["metric_authority"] == {
        "contract_exact_match": "authoritative_strict_metric",
        "slot_f1": "authoritative_strict_metric",
        "slot_f1_soft": "diagnostic_only_not_primary",
        "contract_evaluation_ladder": "authoritative",
        "prediction_repair_or_rescore": False,
    }
    assert policy["source_count_consistency"]["ok"] is True

    sections = policy["policy_sections"]
    assert [section["section"] for section in sections] == [
        "confirmation_markers",
        "field_specificity_or_alias_drift",
        "route_intent_leakage",
    ]
    assert [section["label"] for section in sections] == [
        "Confirmation markers",
        "Field specificity or alias drift",
        "Route or intent boundary leakage",
    ]
    assert [section["source_bucket"] for section in sections] == [
        "missing_confirmation_marker",
        "field_specificity_or_alias_drift",
        "route_intent_leakage",
    ]
    assert [section["source_evidence"]["cluster_row_incidence_total"] for section in sections] == [27, 16, 6]
    assert [section["source_evidence"]["residual_field_total"] for section in sections] == [27, 16, 6]
    assert sections[0]["source_evidence"]["field_paths"] == ["normalized_command"]
    assert sections[1]["source_evidence"]["field_paths"] == ["slots"]
    assert sections[2]["source_evidence"]["field_paths"] == ["route", "safety.reason", "task_type"]
    assert "family-form_fill-test-3" in sections[0]["source_evidence"]["source_family_counts"]


def test_form_fill_confirmation_field_policy_bounds_unsupported_changes() -> None:
    policy = _policy()

    unsupported = {entry["change"] for entry in policy["unsupported_changes"]}
    assert {
        "evaluator_relaxation",
        "soft_metric_promotion",
        "data_mutation",
        "training_run",
        "prediction_repair",
    }.issubset(unsupported)

    assert policy["execution_scope"]["prediction_run"] is False
    assert policy["execution_scope"]["a100_job"] is False
    assert policy["execution_scope"]["sft_training_run"] is False
    assert policy["execution_scope"]["dpo_run"] is False
    assert policy["execution_scope"]["grpo_run"] is False
    assert policy["execution_scope"]["dataset_mutation"] is False
    assert policy["execution_scope"]["candidate_generation"] is False
    assert policy["execution_scope"]["prompt_change"] is False
    assert policy["execution_scope"]["gold_policy_change"] is False
    assert policy["execution_scope"]["evaluator_relaxation"] is False
    assert policy["execution_scope"]["semantic_equivalence_scoring"] is False
    assert policy["execution_scope"]["prediction_repair"] is False
    assert policy["execution_scope"]["prediction_replacement"] is False
    assert policy["execution_scope"]["prediction_rescore"] is False
    assert policy["claims"]["held_out_recovery_claim"] is False
    assert policy["claims"]["model_recovery_claim"] is False
    assert policy["claims"]["production_readiness_claim"] is False
    assert policy["claims"]["live_browser_benchmark_claim"] is False


def test_form_fill_confirmation_field_policy_cli_writes_public_safe_report(
    tmp_path: Path, capsys: Any
) -> None:
    output_dir = tmp_path / "form-fill-confirmation-field-policy"

    assert (
        eval_cli.main(
            [
                "define-form-fill-confirmation-field-policy",
                "--form-fill-inspection",
                (INSPECTION_DIR / "form_fill_boundary_field_specificity_inspection.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    json_path = output_dir / "form_fill_confirmation_field_policy.json"
    markdown_path = output_dir / "form_fill_confirmation_field_policy.md"
    manifest_path = output_dir / "manifest.json"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == json_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()
    assert cli_output["paths"]["manifest"] == manifest_path.as_posix()

    policy = read_json(json_path)
    manifest = read_json(manifest_path)
    markdown = markdown_path.read_text(encoding="utf-8")
    assert policy["summary"]["source_bucket_count"] == 3
    assert manifest["evidence_kind"] == "form_fill_confirmation_field_policy"
    assert manifest["source_form_fill_inspection"]["source_manifest_id"] == "public-sample-20260616T022151Z"
    assert manifest["source_count_consistency"]["ok"] is True
    assert manifest["artifact_policy"]["evaluator_relaxation"] is False
    assert manifest["artifact_policy"]["soft_metric_promotion"] is False
    assert manifest["artifact_policy"]["data_mutation"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert manifest["artifact_policy"]["prediction_repair"] is False
    assert "policy-only form-fill confirmation and field-specificity artifact" in markdown
    assert "strict `contract_exact_match` and strict `slot_f1` remain authoritative" in markdown
    assert "`slot_f1_soft` remains diagnostic-only" in markdown
    assert "does not repair, replace, normalize, or re-score predictions" in markdown
    assert scan_paths([output_dir]).ok is True

    assert hasattr(reports, "write_form_fill_confirmation_field_policy_report")
    direct_paths = reports.write_form_fill_confirmation_field_policy_report(policy, tmp_path / "direct")
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_form_fill_confirmation_field_policy_artifacts_are_bounded_and_public_safe() -> None:
    policy = read_json(POLICY_DIR / "form_fill_confirmation_field_policy.json")
    manifest = read_json(POLICY_DIR / "manifest.json")
    markdown = (POLICY_DIR / "form_fill_confirmation_field_policy.md").read_text(encoding="utf-8")
    regenerated_policy = _policy()

    assert policy == regenerated_policy
    assert manifest["evidence_kind"] == "form_fill_confirmation_field_policy"
    assert manifest["summary"]["source_bucket_count"] == 3
    assert manifest["source_count_consistency"]["ok"] is True
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["held_out_recovery_claim"] is False
    assert manifest["artifact_policy"]["evaluator_relaxation"] is False
    assert manifest["artifact_policy"]["soft_metric_promotion"] is False
    assert manifest["artifact_policy"]["data_mutation"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert manifest["artifact_policy"]["prediction_repair"] is False
    assert policy["claims"]["public_full_corpus_release_claim"] is False
    assert policy["metric_authority"]["slot_f1_soft"] == "diagnostic_only_not_primary"
    assert "cluster-row incidence total" in markdown

    assert HUMAN_BRIEF.exists()
    assert ARCHIVED_CHANGE_DIR.exists()
    assert scan_paths([POLICY_DIR, HUMAN_BRIEF, ARCHIVED_CHANGE_DIR]).ok is True
