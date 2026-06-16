import json
from pathlib import Path
from typing import Any

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import select_formal_heldout_remediation_target
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_formal_heldout_remediation_target_selection_report

REPO_ROOT = Path(__file__).resolve().parents[1]
RESIDUAL_DIR = REPO_ROOT / "reports" / "public-sample" / "formal-heldout-residual-family-diagnosis"
SELECTION_DIR = REPO_ROOT / "reports" / "public-sample" / "formal-heldout-remediation-target-selection"


def _selection() -> dict[str, Any]:
    return select_formal_heldout_remediation_target(
        residual_diagnosis=read_json(RESIDUAL_DIR / "formal_heldout_residual_family_diagnosis.json")
    )


def test_formal_heldout_remediation_target_selection_ranks_current_residual_families() -> None:
    selection = _selection()

    assert selection["evidence_kind"] == "formal_heldout_remediation_target_selection"
    assert selection["selection_status"] == "selected_first_bounded_target"
    assert selection["summary"]["selected_target"] == "form_fill"
    assert selection["summary"]["selected_task_family"] == (
        "form_fill|fill_form|requires_confirmation|confirm:true|slots:field"
    )
    assert selection["summary"]["selected_residual_row_count"] == 29
    assert selection["summary"]["selected_residual_field_count"] == 49
    assert selection["summary"]["recommended_next_change"] == "remediate-form-fill-formal-heldout-residuals"
    assert selection["summary"]["soft_slot_f1_primary_metric"] is False
    assert selection["source_residual_diagnosis"]["source_formal_heldout_evidence"]["dataset_manifest_id"] == (
        "public-sample-20260616T074315Z"
    )
    assert selection["summary"]["source_count_consistency"] == {
        "source_count_consistency_ok": True,
        "expected_residual_rows": 97,
        "ranked_residual_rows": 97,
        "ok": True,
    }
    ranked = selection["ranked_families"]
    assert [item["short_name"] for item in ranked[:3]] == ["form_fill", "blocked", "clarify"]
    assert [item["residual_row_count"] for item in ranked[:3]] == [29, 18, 17]
    assert ranked[0]["residual_field_counts"] == {
        "normalized_command": 27,
        "route": 2,
        "safety.reason": 2,
        "slots": 16,
        "task_type": 2,
    }
    assert selection["execution_scope"]["training_run"] is False
    assert selection["execution_scope"]["new_data_generated"] is False
    assert selection["execution_scope"]["evaluator_metric_change"] is False
    assert selection["claims"]["held_out_recovery_claim"] is False


def test_formal_heldout_remediation_target_selection_cli_writes_public_safe_report(
    tmp_path: Path, capsys: Any
) -> None:
    output_dir = tmp_path / "formal-heldout-remediation-target-selection"

    assert (
        eval_cli.main(
            [
                "select-formal-heldout-remediation-target",
                "--residual-diagnosis",
                (RESIDUAL_DIR / "formal_heldout_residual_family_diagnosis.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    json_path = output_dir / "formal_heldout_remediation_target_selection.json"
    markdown_path = output_dir / "formal_heldout_remediation_target_selection.md"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == json_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()

    selection = read_json(json_path)
    markdown = markdown_path.read_text(encoding="utf-8")
    assert selection["summary"]["selected_target"] == "form_fill"
    assert "not training, not new data generation" in markdown
    assert "slot_f1_soft` remains internal diagnostic-only" in markdown
    assert scan_paths([output_dir]).ok is True

    direct_output = tmp_path / "direct"
    direct_paths = write_formal_heldout_remediation_target_selection_report(selection, direct_output)
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_formal_heldout_remediation_target_selection_is_bounded_and_public_safe() -> None:
    manifest = read_json(SELECTION_DIR / "manifest.json")
    selection = read_json(SELECTION_DIR / "formal_heldout_remediation_target_selection.json")

    assert manifest["evidence_kind"] == "formal_heldout_remediation_target_selection"
    assert manifest["source_residual_diagnosis"]["source_formal_heldout_evidence"]["dataset_manifest_id"] == (
        "public-sample-20260616T074315Z"
    )
    assert manifest["summary"]["selected_target"] == "form_fill"
    assert manifest["summary"]["source_count_consistency"]["ok"] is True
    assert manifest["summary"]["soft_slot_f1_primary_metric"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["held_out_recovery_claim"] is False
    assert manifest["artifact_policy"]["data_generation"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert manifest["artifact_policy"]["a100_job"] is False
    assert selection["claims"]["production_readiness_claim"] is False
    assert selection["claims"]["semantic_equivalence_primary_metric"] is False
    assert scan_paths([SELECTION_DIR]).ok is True
