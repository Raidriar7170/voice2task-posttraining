import json
from pathlib import Path
from typing import Any

import pytest

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import design_form_fill_remediation_cases
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_form_fill_remediation_case_design_report

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-remediation-plan"
DESIGN_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-remediation-case-design"
HUMAN_BRIEF = REPO_ROOT / "docs" / "human-briefs" / "2026-06-16-design-form-fill-remediation-cases.html"


def _plan() -> dict[str, Any]:
    return read_json(PLAN_DIR / "form_fill_remediation_plan.json")


def test_form_fill_remediation_case_design_maps_plan_buckets_without_materialization() -> None:
    design = design_form_fill_remediation_cases(remediation_plan=_plan())

    assert design["evidence_kind"] == "form_fill_remediation_case_design"
    assert design["design_status"] == "design_only_not_materialized"
    assert design["source_remediation_plan"]["evidence_kind"] == "formal_heldout_form_fill_remediation_plan"
    assert design["summary"]["target"] == "form_fill"
    assert design["summary"]["source_residual_row_count"] == 29
    assert design["summary"]["source_residual_field_count"] == 49
    assert design["summary"]["case_group_count"] == 3
    assert design["summary"]["candidate_case_count"] == 9
    assert design["summary"]["covered_bucket_field_counts"] == {
        "clarify_boundary_confusion": 8,
        "confirmation_marker_missing_or_reordered": 23,
        "field_name_specificity_drift": 18,
    }
    assert design["summary"]["recommended_next_step"] == (
        "review_then_materialize_independent_candidate_dataset_in_later_change"
    )

    groups = {group["case_group_id"]: group for group in design["case_groups"]}
    assert set(groups) == {
        "form-fill-clarify-boundary-protection",
        "form-fill-confirmation-marker-preservation",
        "form-fill-field-specificity-preservation",
    }
    assert groups["form-fill-confirmation-marker-preservation"]["source_bucket"] == (
        "confirmation_marker_missing_or_reordered"
    )
    assert groups["form-fill-confirmation-marker-preservation"]["candidate_cases"][0][
        "expected_normalized_command_pattern"
    ].endswith("并确认")
    assert groups["form-fill-field-specificity-preservation"]["candidate_cases"][0]["expected_slots"] == {
        "field": "收货地址"
    }
    assert groups["form-fill-clarify-boundary-protection"]["candidate_cases"][0]["expected_contract"] == {
        "confirmation_required": True,
        "route": "fill_form",
        "safety.reason": "requires_confirmation",
        "task_type": "form_fill",
    }
    assert all(group["materialization_requires_user_review"] is True for group in groups.values())

    assert design["execution_scope"]["new_data_generated"] is False
    assert design["execution_scope"]["public_sample_modified"] is False
    assert design["execution_scope"]["training_run"] is False
    assert design["execution_scope"]["a100_job"] is False
    assert design["execution_scope"]["evaluator_metric_change"] is False
    assert design["claims"]["model_recovery_claim"] is False
    assert design["claims"]["soft_slot_f1_primary_metric"] is False


def test_form_fill_remediation_case_design_rejects_wrong_source_boundary() -> None:
    plan = _plan()
    plan["summary"]["target"] = "clarify"

    with pytest.raises(ValueError, match="form_fill remediation plan"):
        design_form_fill_remediation_cases(remediation_plan=plan)

    plan = _plan()
    plan["remediation_status"] = "materialized"
    with pytest.raises(ValueError, match="plan-only"):
        design_form_fill_remediation_cases(remediation_plan=plan)


def test_form_fill_remediation_case_design_cli_writes_public_safe_report(
    tmp_path: Path,
    capsys: Any,
) -> None:
    output_dir = tmp_path / "form-fill-case-design"

    assert (
        eval_cli.main(
            [
                "design-form-fill-remediation-cases",
                "--remediation-plan",
                (PLAN_DIR / "form_fill_remediation_plan.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == (output_dir / "form_fill_remediation_case_design.json").as_posix()
    assert cli_output["paths"]["markdown"] == (output_dir / "form_fill_remediation_case_design.md").as_posix()
    assert cli_output["paths"]["manifest"] == (output_dir / "manifest.json").as_posix()

    design = read_json(output_dir / "form_fill_remediation_case_design.json")
    manifest = read_json(output_dir / "manifest.json")
    markdown = (output_dir / "form_fill_remediation_case_design.md").read_text(encoding="utf-8")
    assert design["summary"]["case_group_count"] == 3
    assert manifest["artifact_policy"]["new_data_generated"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert "design-only evidence" in markdown
    assert "does not materialize seed rows" in markdown
    assert scan_paths([output_dir]).ok is True

    direct_paths = write_form_fill_remediation_case_design_report(design, tmp_path / "direct")
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_form_fill_remediation_case_design_is_bounded_and_public_safe() -> None:
    manifest = read_json(DESIGN_DIR / "manifest.json")
    design = read_json(DESIGN_DIR / "form_fill_remediation_case_design.json")

    assert manifest["evidence_kind"] == "form_fill_remediation_case_design"
    assert manifest["design_status"] == "design_only_not_materialized"
    assert manifest["summary"]["case_group_count"] == 3
    assert manifest["summary"]["candidate_case_count"] == 9
    assert manifest["execution_scope"]["new_data_generated"] is False
    assert manifest["execution_scope"]["public_sample_modified"] is False
    assert manifest["execution_scope"]["training_run"] is False
    assert manifest["artifact_policy"]["a100_job"] is False
    assert design["claims"]["held_out_recovery_claim"] is False
    assert design["claims"]["adapter_release_claim"] is False
    assert design["claims"]["production_readiness_claim"] is False
    assert HUMAN_BRIEF.exists()
    assert scan_paths([DESIGN_DIR, HUMAN_BRIEF]).ok is True
