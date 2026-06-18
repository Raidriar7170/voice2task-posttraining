import json
from pathlib import Path
from typing import Any

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import select_scaled_residual_remediation_target
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_scaled_residual_remediation_target_selection_report

REPO_ROOT = Path(__file__).resolve().parents[1]
SCALED_CLUSTER_DIR = (
    REPO_ROOT / "reports" / "public-sample" / "scaled-current-123-adapter-residual-cluster-inspection"
)
TARGET_SELECTION_DIR = (
    REPO_ROOT / "reports" / "public-sample" / "scaled-residual-remediation-target-selection"
)
ARCHIVED_CHANGE_DIR = (
    REPO_ROOT
    / "openspec"
    / "changes"
    / "archive"
    / "2026-06-18-select-scaled-residual-remediation-target"
)
HUMAN_BRIEF = (
    REPO_ROOT
    / "docs"
    / "human-briefs"
    / "2026-06-18-select-scaled-residual-remediation-target.html"
)


def _source_cluster_inspection() -> dict[str, Any]:
    return read_json(SCALED_CLUSTER_DIR / "formal_heldout_residual_cluster_inspection.json")


def test_scaled_residual_target_selection_selects_clarify_slots_and_defers_safety() -> None:
    selection = select_scaled_residual_remediation_target(
        residual_cluster_inspection=_source_cluster_inspection(),
        cluster_inspection_artifact=(
            "reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/"
            "formal_heldout_residual_cluster_inspection.json"
        ),
    )

    assert selection["evidence_kind"] == "scaled_residual_remediation_target_selection"
    assert selection["selection_status"] == "selected_first_bounded_target"
    assert selection["source_residual_cluster_inspection"]["source_manifest_id"] == (
        "public-sample-20260617T152259Z"
    )
    assert selection["summary"]["selected_target"] == "clarify"
    assert selection["summary"]["selected_task_family"] == (
        "clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity"
    )
    assert selection["summary"]["selected_field_path"] == "slots"
    assert selection["summary"]["selected_residual_row_count"] == 78
    assert selection["summary"]["selected_residual_field_count"] == 78
    assert selection["summary"]["ranked_cluster_count"] == 29
    assert selection["summary"]["source_residual_row_count"] == 321
    assert selection["summary"]["source_residual_field_count"] == 540
    assert selection["summary"]["soft_slot_f1_primary_metric"] is False
    assert selection["summary"]["recommended_next_change"] == (
        "design-scaled-clarify-slot-boundary-candidates"
    )

    selected = selection["selection"]["selected"]
    assert selected["rank"] == 1
    assert selected["short_name"] == "clarify"
    assert selected["field_path"] == "slots"
    assert selected["recommended_action_candidate"] == (
        "route_intent_boundary_inspection_before_data_or_training"
    )
    assert selected["residual_rows_by_split"] == {"dev": 42, "test": 36}

    deferred = selection["selection"]["deferred_targets"]
    assert deferred[0]["short_name"] == "blocked"
    assert deferred[0]["field_path"] == "slots"
    assert deferred[0]["reason"] == "defer_to_dedicated_safety_boundary_phase"
    assert deferred[1]["short_name"] == "search"
    assert deferred[1]["reason"] == "defer_to_later_label_canonicalization_phase"
    assert selection["execution_scope"]["a100_job"] is False
    assert selection["execution_scope"]["training_run"] is False
    assert selection["execution_scope"]["prediction_run"] is False
    assert selection["execution_scope"]["data_materialization"] is False
    assert selection["execution_scope"]["evaluator_metric_change"] is False
    assert selection["execution_scope"]["evaluator_relaxation"] is False
    assert selection["claims"]["target_selection_only"] is True
    assert selection["claims"]["held_out_recovery_claim"] is False
    assert selection["claims"]["model_recovery_claim"] is False
    assert selection["claims"]["semantic_equivalence_primary_metric"] is False


def test_scaled_residual_target_selection_cli_writes_public_safe_report(
    tmp_path: Path, capsys: Any
) -> None:
    output_dir = tmp_path / "scaled-residual-remediation-target-selection"

    assert (
        eval_cli.main(
            [
                "select-scaled-residual-remediation-target",
                "--residual-clusters",
                (SCALED_CLUSTER_DIR / "formal_heldout_residual_cluster_inspection.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    json_path = output_dir / "scaled_residual_remediation_target_selection.json"
    markdown_path = output_dir / "scaled_residual_remediation_target_selection.md"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == json_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()

    selection = read_json(json_path)
    markdown = markdown_path.read_text(encoding="utf-8")
    manifest = read_json(output_dir / "manifest.json")
    assert selection["summary"]["selected_target"] == "clarify"
    assert "target-selection evidence only" in markdown
    assert "Blocked-payment residuals are deferred" in markdown
    assert "does not authorize materialization, training, prompts, predictions, or evaluator changes" in markdown
    assert manifest["artifact_policy"]["target_selection_only"] is True
    assert manifest["artifact_policy"]["training_run"] is False
    assert manifest["artifact_policy"]["a100_job"] is False
    assert manifest["diagnostic_artifacts"] == {
        "selection": "scaled-residual-remediation-target-selection/scaled_residual_remediation_target_selection.json",
        "markdown": "scaled-residual-remediation-target-selection/scaled_residual_remediation_target_selection.md",
        "manifest": "scaled-residual-remediation-target-selection/manifest.json",
    }
    assert scan_paths([output_dir]).ok is True

    direct_paths = write_scaled_residual_remediation_target_selection_report(
        selection,
        tmp_path / "direct-scaled-target-selection",
    )
    direct_manifest = read_json(direct_paths["manifest"])
    assert direct_manifest["diagnostic_artifacts"] == {
        "selection": "direct-scaled-target-selection/scaled_residual_remediation_target_selection.json",
        "markdown": "direct-scaled-target-selection/scaled_residual_remediation_target_selection.md",
        "manifest": "direct-scaled-target-selection/manifest.json",
    }


def test_committed_scaled_residual_target_selection_is_bounded_and_public_safe() -> None:
    manifest = read_json(TARGET_SELECTION_DIR / "manifest.json")
    selection = read_json(TARGET_SELECTION_DIR / "scaled_residual_remediation_target_selection.json")
    report = (TARGET_SELECTION_DIR / "scaled_residual_remediation_target_selection.md").read_text(
        encoding="utf-8"
    )
    leak_scan = read_json(TARGET_SELECTION_DIR / "final_leak_scan_result.json")

    assert manifest["evidence_kind"] == "scaled_residual_remediation_target_selection"
    assert manifest["source_residual_cluster_inspection"]["source_manifest_id"] == (
        "public-sample-20260617T152259Z"
    )
    assert manifest["source_residual_cluster_inspection"]["inspection_artifact"] == (
        "reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/"
        "formal_heldout_residual_cluster_inspection.json"
    )
    assert manifest["summary"]["selected_target"] == "clarify"
    assert manifest["summary"]["selected_field_path"] == "slots"
    assert manifest["summary"]["selected_residual_row_count"] == 78
    assert manifest["summary"]["selected_residual_field_count"] == 78
    assert manifest["summary"]["ranked_cluster_count"] == 29
    assert manifest["summary"]["source_residual_row_count"] == 321
    assert manifest["summary"]["source_residual_field_count"] == 540
    assert manifest["summary"]["recommended_next_change"] == (
        "design-scaled-clarify-slot-boundary-candidates"
    )
    assert manifest["artifact_policy"]["target_selection_only"] is True
    assert manifest["artifact_policy"]["a100_job"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert manifest["artifact_policy"]["prediction_run"] is False
    assert manifest["artifact_policy"]["data_materialization"] is False
    assert manifest["artifact_policy"]["dataset_mutation"] is False
    assert manifest["artifact_policy"]["evaluator_metric_change"] is False
    assert manifest["artifact_policy"]["evaluator_relaxation"] is False
    assert manifest["artifact_policy"]["semantic_equivalence_scoring"] is False
    assert manifest["diagnostic_artifacts"] == {
        "selection": (
            "reports/public-sample/scaled-residual-remediation-target-selection/"
            "scaled_residual_remediation_target_selection.json"
        ),
        "markdown": (
            "reports/public-sample/scaled-residual-remediation-target-selection/"
            "scaled_residual_remediation_target_selection.md"
        ),
        "manifest": "reports/public-sample/scaled-residual-remediation-target-selection/manifest.json",
    }
    assert selection["claims"]["target_selection_only"] is True
    assert selection["claims"]["held_out_recovery_claim"] is False
    assert selection["claims"]["model_recovery_claim"] is False
    assert selection["claims"]["soft_slot_f1_primary_metric"] is False
    assert selection["selection"]["deferred_targets"][0]["reason"] == (
        "defer_to_dedicated_safety_boundary_phase"
    )
    assert leak_scan["ok"] is True
    assert "target-selection evidence only" in report
    scan_targets = [TARGET_SELECTION_DIR, HUMAN_BRIEF]
    if ARCHIVED_CHANGE_DIR.exists():
        scan_targets.append(ARCHIVED_CHANGE_DIR)
    assert scan_paths(scan_targets).ok is True
