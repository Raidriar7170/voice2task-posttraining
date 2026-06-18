import json
from pathlib import Path
from typing import Any

import pytest

from voice2task.io import write_json
from voice2task.leak_scan import scan_paths
from voice2task.remediation_target_selection import (
    load_remediation_target_inputs,
    select_residual_driven_remediation_targets,
    write_remediation_target_selection_reports,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYERED_DIR = REPO_ROOT / "reports" / "public-sample" / "layered-eval"
RESIDUAL_DIR = REPO_ROOT / "reports" / "public-sample" / "residual-diagnosis"
SELECTION_DIR = REPO_ROOT / "reports" / "public-sample" / "remediation-target-selection"


def _synthetic_layered(split: str, total: int, unsafe_false_negative_count: int) -> dict[str, Any]:
    return {
        "evidence_kind": "layered_contract_evaluation",
        "manifest_id": "public-sample-test",
        "split": split,
        "summary": {
            "total": total,
            "strict_pass": 1,
            "strict_fail": max(0, total - 1),
            "unsafe_false_negative_count": unsafe_false_negative_count,
        },
        "metrics": {
            "contract_exact_match_strict": 0.1,
            "executable_contract_pass_rate": 0.2,
            "slot_key_f1": 0.8,
            "slot_value_exact_f1": 0.25,
            "slot_value_normalized_f1": 0.25,
            "route_accuracy": 0.9,
            "task_type_accuracy": 0.9,
            "risk_level_accuracy": 0.8,
            "requires_confirmation_accuracy": 0.7,
            "unsafe_false_negative_rate": 1.0 if unsafe_false_negative_count else 0.0,
            "refusal_or_clarify_accuracy": 0.6,
        },
    }


def _synthetic_residual(split: str, slot_count: int, allowed_actions_count: int = 0) -> dict[str, Any]:
    residuals = [
        {
            "split": split,
            "row_id": f"family-search-{split}-{index}",
            "family": "slot_value",
            "field_path": "slots.query",
            "gold_value_summary": "string(6): 搜索天气",
            "prediction_value_summary": "string(4): 搜天气",
        }
        for index in range(slot_count)
    ]
    residuals.extend(
        {
            "split": split,
            "row_id": f"family-form-fill-{split}-{index}",
            "family": "allowed_actions",
            "field_path": "allowed_actions",
            "gold_value_summary": "list(1): fill_form",
            "prediction_value_summary": "missing",
        }
        for index in range(allowed_actions_count)
    )
    return {
        "evidence_kind": "layered_residual_diagnosis",
        "manifest_id": "public-sample-test",
        "split": split,
        "summary": {
            "total": len(residuals),
            "strict_pass": 1,
            "strict_fail": len(residuals),
            "family_counts": {
                "slot_value": slot_count,
                "allowed_actions": allowed_actions_count,
            },
        },
        "families": {
            "slot_value": {"count": slot_count, "examples": residuals[:3]},
            "allowed_actions": {
                "count": allowed_actions_count,
                "examples": [item for item in residuals if item["family"] == "allowed_actions"][:3],
            },
        },
        "residuals": residuals,
    }


def _write_input_fixture(root: Path, *, unsafe_false_negative_count: int = 0) -> tuple[Path, Path]:
    layered_dir = root / "layered-eval"
    residual_dir = root / "residual-diagnosis"
    write_json(layered_dir / "dev" / "metrics.json", _synthetic_layered("dev", 10, 0))
    write_json(
        layered_dir / "test" / "metrics.json",
        _synthetic_layered("test", 10, unsafe_false_negative_count),
    )
    write_json(residual_dir / "dev" / "residual_diagnosis.json", _synthetic_residual("dev", 9))
    write_json(
        residual_dir / "test" / "residual_diagnosis.json",
        _synthetic_residual("test", 8, allowed_actions_count=3),
    )
    return layered_dir, residual_dir


def test_selection_reads_current_committed_layered_and_residual_layouts() -> None:
    inputs = load_remediation_target_inputs(
        layered_eval_dir=LAYERED_DIR,
        residual_diagnosis_dir=RESIDUAL_DIR,
    )

    assert inputs.manifest_id == "public-sample-20260617T152259Z"
    assert set(inputs.layered_by_split) == {"dev", "test"}
    assert set(inputs.residual_by_split) == {"dev", "test"}
    assert inputs.layered_by_split["dev"]["metrics"]["contract_exact_match_strict"] == pytest.approx(
        0.2463768115942029
    )
    assert inputs.residual_by_split["test"]["summary"]["family_counts"]["slot_value"] == 176


def test_selection_aggregates_families_and_maps_remediation_strategies() -> None:
    inputs = load_remediation_target_inputs(
        layered_eval_dir=LAYERED_DIR,
        residual_diagnosis_dir=RESIDUAL_DIR,
    )
    selection = select_residual_driven_remediation_targets(inputs)

    assert selection["evidence_kind"] == "residual_driven_remediation_target_selection"
    assert selection["summary"]["manifest_id"] == "public-sample-20260617T152259Z"
    assert selection["metrics_by_split"]["dev"]["sample_count"] == 207
    assert selection["metrics_by_split"]["test"]["unsafe_false_negative_rate"] == pytest.approx(
        0.008333333333333333
    )

    families = {item["family"]: item for item in selection["failure_families"]}
    assert families["slot_value_mismatch"]["count"] == 336
    assert families["normalized_command_mismatch"]["count"] == 194
    assert families["slot_value_mismatch"]["dev_count"] == 160
    assert families["slot_value_mismatch"]["test_count"] == 176
    assert families["slot_value_mismatch"]["strategy"] == "SCHEMA_CANONICALIZATION"
    assert families["allowed_actions_mismatch"]["strategy"] == "DETERMINISTIC_POSTPROCESSOR"
    assert families["success_criteria_mismatch"]["strategy"] == "DETERMINISTIC_POSTPROCESSOR"
    assert families["unsafe_false_negative"]["strategy"] == "SAFETY_REPAIR"
    assert families["route_mismatch"]["strategy"] == "DEFER"
    assert len(families["slot_value_mismatch"]["examples"]) <= 3

    targets = selection["selected_targets"]
    assert 1 <= len(targets) <= 2
    assert targets[0]["target_id"] == "safety-repair-unsafe-false-negative"
    assert targets[0]["strategy"] == "SAFETY_REPAIR"
    assert targets[0]["evidence_count"] == 1
    assert targets[1]["target_id"] == "slot-value-canonicalization-policy"
    assert targets[1]["proposed_next_change_id"] == "design-slot-canonicalization-policy"
    assert selection["recommended_next_change"]["proposed_change_id"] == "design-safety-repair-candidates"
    assert selection["recommended_next_change"]["evidence_from_current_artifacts"]["primary_source"] == (
        "layered_eval_summary"
    )
    assert selection["claims"]["model_improvement_claim"] is False
    assert selection["execution_scope"]["training_run"] is False
    assert selection["execution_scope"]["evaluator_metric_change"] is False


def test_safety_target_is_prioritized_over_larger_slot_counts(tmp_path: Path) -> None:
    layered_dir, residual_dir = _write_input_fixture(tmp_path, unsafe_false_negative_count=1)

    selection = select_residual_driven_remediation_targets(
        load_remediation_target_inputs(layered_eval_dir=layered_dir, residual_diagnosis_dir=residual_dir)
    )

    assert [target["target_id"] for target in selection["selected_targets"]] == [
        "safety-repair-unsafe-false-negative",
        "slot-value-canonicalization-policy",
    ]
    families = {item["family"]: item for item in selection["failure_families"]}
    assert families["allowed_actions_mismatch"]["count"] == 3
    assert families["allowed_actions_mismatch"]["strategy"] == "DETERMINISTIC_POSTPROCESSOR"


def test_report_writer_outputs_required_public_safe_files(tmp_path: Path) -> None:
    inputs = load_remediation_target_inputs(
        layered_eval_dir=LAYERED_DIR,
        residual_diagnosis_dir=RESIDUAL_DIR,
    )
    selection = select_residual_driven_remediation_targets(inputs)

    paths = write_remediation_target_selection_reports(selection, tmp_path)

    assert set(paths) == {"summary_json", "summary_md", "top_failures_md", "recommended_next_change_md"}
    for path in paths.values():
        assert path.exists()
    summary = json.loads(paths["summary_json"].read_text(encoding="utf-8"))
    assert summary["selected_targets"][0]["target_id"] == "safety-repair-unsafe-false-negative"
    assert "strict exact is the canonical diagnostic" in paths["summary_md"].read_text(encoding="utf-8")
    top_failures = paths["top_failures_md"].read_text(encoding="utf-8")
    assert "slot_value_mismatch" in top_failures
    assert "inferred task hint" in top_failures
    recommended = paths["recommended_next_change_md"].read_text(encoding="utf-8")
    assert "proposed change id: `design-safety-repair-candidates`" in recommended
    assert "Evidence from Current Layered/Residual Artifacts" in recommended
    assert "Non-goals" in recommended
    assert scan_paths([tmp_path]).ok is True


def test_committed_remediation_target_selection_is_bounded_and_public_safe() -> None:
    summary = json.loads((SELECTION_DIR / "summary.json").read_text(encoding="utf-8"))
    summary_md = (SELECTION_DIR / "summary.md").read_text(encoding="utf-8")
    top_failures = (SELECTION_DIR / "top-failures.md").read_text(encoding="utf-8")
    recommended = (SELECTION_DIR / "recommended-next-change.md").read_text(encoding="utf-8")

    assert summary["evidence_kind"] == "residual_driven_remediation_target_selection"
    assert summary["selected_targets"][0]["strategy"] == "SAFETY_REPAIR"
    assert summary["selected_targets"][1]["strategy"] == "SCHEMA_CANONICALIZATION"
    assert summary["execution_scope"]["training_run"] is False
    assert summary["execution_scope"]["prediction_run"] is False
    assert summary["execution_scope"]["data_mutation"] is False
    assert summary["execution_scope"]["evaluator_metric_change"] is False
    assert summary["claims"]["held_out_recovery_claim"] is False
    assert summary["recommended_next_change"]["evidence_from_current_artifacts"]["primary_source"] == (
        "layered_eval_summary"
    )
    assert "current stage does not claim model improvement" in summary_md
    assert "normalized_command_mismatch" in top_failures
    assert "inferred source-family hint" in top_failures
    assert "Claim boundaries" in recommended
    assert scan_paths([SELECTION_DIR]).ok is True
