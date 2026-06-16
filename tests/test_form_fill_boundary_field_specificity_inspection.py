import json
from pathlib import Path
from typing import Any

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import inspect_form_fill_boundary_field_specificity
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_form_fill_boundary_field_specificity_report

REPO_ROOT = Path(__file__).resolve().parents[1]
CLUSTER_DIR = REPO_ROOT / "reports" / "public-sample" / "formal-heldout-residual-cluster-inspection"
INSPECTION_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-boundary-field-specificity-inspection"
HUMAN_BRIEF = (
    REPO_ROOT / "docs" / "human-briefs" / "2026-06-16-inspect-form-fill-boundary-field-specificity.html"
)
ACTIVE_CHANGE_DIR = REPO_ROOT / "openspec" / "changes" / "inspect-form-fill-boundary-field-specificity"
ARCHIVED_CHANGE_DIR = (
    REPO_ROOT / "openspec" / "changes" / "archive" / "2026-06-16-inspect-form-fill-boundary-field-specificity"
)


def _inspection() -> dict[str, Any]:
    return inspect_form_fill_boundary_field_specificity(
        residual_cluster_inspection=read_json(CLUSTER_DIR / "formal_heldout_residual_cluster_inspection.json")
    )


def test_form_fill_boundary_field_specificity_inspection_groups_current_buckets() -> None:
    inspection = _inspection()

    assert inspection["evidence_kind"] == "form_fill_boundary_field_specificity_inspection"
    assert inspection["diagnostic_kind"] == "formal_public_form_fill_boundary_field_specificity_inspection"
    assert inspection["source_residual_cluster_inspection"]["source_manifest_id"] == (
        "public-sample-20260616T074315Z"
    )
    assert inspection["summary"]["form_fill_cluster_count"] == 5
    assert inspection["summary"]["form_fill_cluster_row_incidence_total"] == 49
    assert inspection["summary"]["form_fill_residual_field_total"] == 49
    assert inspection["summary"]["bucket_count"] == 3
    assert inspection["summary"]["top_bucket"] == "missing_confirmation_marker"
    assert inspection["summary"]["recommended_next_step"] == (
        "define_form_fill_confirmation_and_field_specificity_policy_before_data_or_training"
    )
    assert inspection["summary"]["soft_slot_f1_primary_metric"] is False

    buckets = inspection["form_fill_buckets"]
    assert [bucket["bucket"] for bucket in buckets] == [
        "missing_confirmation_marker",
        "field_specificity_or_alias_drift",
        "route_intent_leakage",
    ]
    assert [bucket["cluster_row_incidence_total"] for bucket in buckets] == [27, 16, 6]
    assert [bucket["residual_field_total"] for bucket in buckets] == [27, 16, 6]
    assert buckets[0]["cluster_count"] == 1
    assert buckets[1]["cluster_count"] == 1
    assert buckets[2]["cluster_count"] == 3
    assert buckets[0]["field_paths"] == ["normalized_command"]
    assert buckets[1]["field_paths"] == ["slots"]
    assert buckets[2]["field_paths"] == ["route", "safety.reason", "task_type"]
    assert "family-form_fill-test-3" in buckets[0]["source_family_counts"]

    assert inspection["source_count_consistency"] == {
        "source_form_fill_cluster_count": 5,
        "bucketed_form_fill_cluster_count": 5,
        "source_form_fill_cluster_row_incidence_total": 49,
        "bucketed_form_fill_cluster_row_incidence_total": 49,
        "source_form_fill_residual_fields": 49,
        "bucketed_form_fill_residual_fields": 49,
        "ok": True,
    }
    assert inspection["execution_scope"]["prediction_run"] is False
    assert inspection["execution_scope"]["sft_training_run"] is False
    assert inspection["execution_scope"]["dpo_run"] is False
    assert inspection["execution_scope"]["grpo_run"] is False
    assert inspection["execution_scope"]["dataset_mutation"] is False
    assert inspection["execution_scope"]["evaluator_relaxation"] is False
    assert inspection["execution_scope"]["prediction_repair"] is False
    assert inspection["claims"]["held_out_recovery_claim"] is False
    assert inspection["claims"]["semantic_equivalence_primary_metric"] is False


def test_form_fill_boundary_field_specificity_cli_writes_public_safe_report(
    tmp_path: Path, capsys: Any
) -> None:
    output_dir = tmp_path / "form-fill-boundary-field-specificity-inspection"

    assert (
        eval_cli.main(
            [
                "inspect-form-fill-boundary-field-specificity",
                "--residual-clusters",
                (CLUSTER_DIR / "formal_heldout_residual_cluster_inspection.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    json_path = output_dir / "form_fill_boundary_field_specificity_inspection.json"
    markdown_path = output_dir / "form_fill_boundary_field_specificity_inspection.md"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == json_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()

    inspection = read_json(json_path)
    markdown = markdown_path.read_text(encoding="utf-8")
    assert inspection["summary"]["form_fill_cluster_row_incidence_total"] == 49
    assert inspection["summary"]["form_fill_residual_field_total"] == 49
    assert "analysis-only form-fill boundary and field-specificity inspection" in markdown
    assert "strict `contract_exact_match` remains primary" in markdown
    assert "does not authorize data, training, prompt, or evaluator changes" in markdown
    assert scan_paths([output_dir]).ok is True

    direct_paths = write_form_fill_boundary_field_specificity_report(inspection, tmp_path / "direct")
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_form_fill_boundary_field_specificity_inspection_is_bounded_and_public_safe() -> None:
    manifest = read_json(INSPECTION_DIR / "manifest.json")
    inspection = read_json(INSPECTION_DIR / "form_fill_boundary_field_specificity_inspection.json")

    assert manifest["evidence_kind"] == "form_fill_boundary_field_specificity_inspection"
    assert manifest["summary"]["bucket_count"] == 3
    assert manifest["source_count_consistency"]["ok"] is True
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["held_out_recovery_claim"] is False
    assert manifest["artifact_policy"]["prediction_run"] is False
    assert manifest["artifact_policy"]["sft_training_run"] is False
    assert manifest["artifact_policy"]["dpo_run"] is False
    assert manifest["artifact_policy"]["grpo_run"] is False
    assert manifest["artifact_policy"]["dataset_mutation"] is False
    assert manifest["artifact_policy"]["evaluator_relaxation"] is False
    assert manifest["artifact_policy"]["prediction_repair"] is False
    assert inspection["claims"]["production_readiness_claim"] is False
    assert inspection["claims"]["semantic_equivalence_primary_metric"] is False

    change_paths = [path for path in (ACTIVE_CHANGE_DIR, ARCHIVED_CHANGE_DIR) if path.exists()]
    assert change_paths
    assert scan_paths([INSPECTION_DIR, HUMAN_BRIEF, *change_paths]).ok is True
