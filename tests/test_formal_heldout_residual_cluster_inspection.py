import json
from pathlib import Path
from typing import Any

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import inspect_formal_heldout_residual_clusters
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_formal_heldout_residual_cluster_inspection_report

REPO_ROOT = Path(__file__).resolve().parents[1]
RESIDUAL_DIR = REPO_ROOT / "reports" / "public-sample" / "formal-heldout-residual-family-diagnosis"
CLUSTER_DIR = REPO_ROOT / "reports" / "public-sample" / "formal-heldout-residual-cluster-inspection"
ARCHIVED_CHANGE_DIR = (
    REPO_ROOT
    / "openspec"
    / "changes"
    / "archive"
    / "2026-06-16-inspect-formal-heldout-residual-clusters"
)
HUMAN_BRIEF = REPO_ROOT / "docs" / "human-briefs" / "2026-06-16-inspect-formal-heldout-residual-clusters.html"


def _inspection() -> dict[str, Any]:
    return inspect_formal_heldout_residual_clusters(
        residual_diagnosis=read_json(RESIDUAL_DIR / "formal_heldout_residual_family_diagnosis.json")
    )


def test_formal_heldout_residual_cluster_inspection_groups_current_clusters() -> None:
    inspection = _inspection()

    assert inspection["evidence_kind"] == "formal_heldout_residual_cluster_inspection"
    assert inspection["diagnostic_kind"] == "formal_public_heldout_residual_cluster_inspection"
    assert inspection["source_residual_diagnosis"]["source_formal_heldout_evidence"]["dataset_manifest_id"] == (
        "public-sample-20260616T074315Z"
    )
    assert inspection["summary"]["residual_row_count"] == 97
    assert inspection["summary"]["source_residual_field_count"] == 204
    assert inspection["summary"]["cluster_count"] == 27
    assert inspection["summary"]["top_cluster_task_family"] == (
        "form_fill|fill_form|requires_confirmation|confirm:true|slots:field"
    )
    assert inspection["summary"]["top_cluster_field_path"] == "normalized_command"
    assert inspection["summary"]["top_cluster_residual_rows"] == 27
    assert inspection["summary"]["top_cluster_residual_fields"] == 27
    assert inspection["summary"]["recommended_next_step"] == (
        "review_ranked_clusters_before_data_training_or_evaluator_change"
    )
    assert inspection["summary"]["soft_slot_f1_primary_metric"] is False

    clusters = inspection["residual_clusters"]
    assert [cluster["short_name"] for cluster in clusters[:3]] == ["form_fill", "blocked", "form_fill"]
    assert [cluster["residual_row_count"] for cluster in clusters[:3]] == [27, 18, 16]
    top_cluster = clusters[0]
    assert top_cluster["field_path"] == "normalized_command"
    assert top_cluster["category"] == "normalized_command_strict_string_mismatch"
    assert top_cluster["mismatch_category"] == "value_mismatch"
    assert top_cluster["residual_rows_by_split"] == {"dev": 11, "test": 16}
    assert top_cluster["source_family_counts"]["family-form_fill-test-3"] == 3
    assert top_cluster["recommended_action_candidate"] == (
        "inspect_form_fill_boundary_and_field_specificity_before_new_data_or_training"
    )
    assert clusters[1]["recommended_action_candidate"] == (
        "dedicated_safety_boundary_inspection_before_data_or_training"
    )
    assert len(top_cluster["representative_examples"]) <= 5

    assert inspection["aggregates"]["by_category"]["slot_strict_mismatch"] == 76
    assert inspection["aggregates"]["by_field_path"]["normalized_command"] == 77
    assert inspection["source_count_consistency"] == {
        "expected_residual_rows": 97,
        "clustered_residual_rows": 97,
        "expected_residual_fields": 204,
        "clustered_residual_fields": 204,
        "ok": True,
    }
    assert inspection["execution_scope"]["prediction_run"] is False
    assert inspection["execution_scope"]["training_run"] is False
    assert inspection["execution_scope"]["sft_training_run"] is False
    assert inspection["execution_scope"]["evaluator_metric_change"] is False
    assert inspection["execution_scope"]["evaluator_relaxation"] is False
    assert inspection["execution_scope"]["semantic_equivalence_scoring"] is False
    assert inspection["execution_scope"]["dataset_mutation"] is False
    assert inspection["execution_scope"]["prediction_repair"] is False
    assert inspection["execution_scope"]["prediction_replacement"] is False
    assert inspection["claims"]["held_out_recovery_claim"] is False
    assert inspection["claims"]["semantic_equivalence_primary_metric"] is False


def test_formal_heldout_residual_cluster_inspection_cli_writes_public_safe_report(
    tmp_path: Path, capsys: Any
) -> None:
    output_dir = tmp_path / "formal-heldout-residual-cluster-inspection"

    assert (
        eval_cli.main(
            [
                "inspect-formal-heldout-residual-clusters",
                "--residual-diagnosis",
                (RESIDUAL_DIR / "formal_heldout_residual_family_diagnosis.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    json_path = output_dir / "formal_heldout_residual_cluster_inspection.json"
    markdown_path = output_dir / "formal_heldout_residual_cluster_inspection.md"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == json_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()

    inspection = read_json(json_path)
    markdown = markdown_path.read_text(encoding="utf-8")
    assert inspection["summary"]["top_cluster_residual_rows"] == 27
    assert "analysis-only residual cluster inspection" in markdown
    assert "strict `contract_exact_match` remains primary" in markdown
    assert "does not authorize data, training, prompt, or evaluator changes" in markdown
    assert scan_paths([output_dir]).ok is True

    direct_paths = write_formal_heldout_residual_cluster_inspection_report(inspection, tmp_path / "direct")
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_formal_heldout_residual_cluster_inspection_is_bounded_and_public_safe() -> None:
    manifest = read_json(CLUSTER_DIR / "manifest.json")
    inspection = read_json(CLUSTER_DIR / "formal_heldout_residual_cluster_inspection.json")

    assert manifest["evidence_kind"] == "formal_heldout_residual_cluster_inspection"
    assert manifest["source_residual_diagnosis"]["source_formal_heldout_evidence"]["dataset_manifest_id"] == (
        "public-sample-20260616T074315Z"
    )
    assert manifest["summary"]["cluster_count"] == 27
    assert manifest["summary"]["top_cluster_residual_rows"] == 27
    assert manifest["source_count_consistency"]["ok"] is True
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["held_out_recovery_claim"] is False
    assert manifest["artifact_policy"]["prediction_run"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert manifest["artifact_policy"]["sft_training_run"] is False
    assert manifest["artifact_policy"]["evaluator_metric_change"] is False
    assert manifest["artifact_policy"]["evaluator_relaxation"] is False
    assert manifest["artifact_policy"]["semantic_equivalence_scoring"] is False
    assert manifest["artifact_policy"]["dataset_mutation"] is False
    assert manifest["artifact_policy"]["prediction_repair"] is False
    assert manifest["artifact_policy"]["prediction_replacement"] is False
    assert inspection["claims"]["production_readiness_claim"] is False
    assert inspection["claims"]["semantic_equivalence_primary_metric"] is False
    assert scan_paths([CLUSTER_DIR, ARCHIVED_CHANGE_DIR, HUMAN_BRIEF]).ok is True
