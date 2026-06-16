import json
from pathlib import Path
from typing import Any

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import (
    diagnose_formal_heldout_residual_families,
    load_predictions,
    load_sft_rows,
)
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_formal_heldout_residual_family_report

REPO_ROOT = Path(__file__).resolve().parents[1]
FORMAL_DIR = REPO_ROOT / "reports" / "public-sample" / "a100-formal-public-heldout-prediction"
DIAGNOSIS_DIR = REPO_ROOT / "reports" / "public-sample" / "formal-heldout-residual-family-diagnosis"


def _rows(split: str) -> list[Any]:
    return load_sft_rows(FORMAL_DIR / split / f"{split}_gold.jsonl")


def _predictions(split: str) -> dict[str, Any]:
    return load_predictions(FORMAL_DIR / split / "predictions.jsonl")


def _diagnosis() -> dict[str, Any]:
    return diagnose_formal_heldout_residual_families(
        formal_manifest=read_json(FORMAL_DIR / "formal_public_heldout_prediction.json"),
        rows_by_split={"dev": _rows("dev"), "test": _rows("test")},
        predictions_by_split={"dev": _predictions("dev"), "test": _predictions("test")},
    )


def test_formal_heldout_residual_family_diagnosis_groups_current_residuals() -> None:
    diagnosis = _diagnosis()

    assert diagnosis["evidence_kind"] == "formal_heldout_residual_family_diagnosis"
    assert diagnosis["diagnostic_kind"] == "formal_public_heldout_residual_family_diagnosis"
    assert diagnosis["source_formal_heldout_evidence"]["dataset_manifest_id"] == (
        "public-sample-20260616T022151Z"
    )
    assert diagnosis["source_formal_heldout_evidence"]["overall_interpretation"] == (
        "formal_public_heldout_partial_signal"
    )
    assert diagnosis["summary"]["strict_contract_exact_match"] == {
        "dev": 0.30434782608695654,
        "test": 0.2898550724637681,
    }
    assert diagnosis["summary"]["soft_slot_f1_primary_metric"] is False
    assert diagnosis["summary"]["residual_row_count"] == 97
    assert diagnosis["summary"]["source_count_consistency"] == {
        "ok": True,
        "by_split": {
            "dev": {"expected": 48, "computed": 48, "ok": True},
            "test": {"expected": 49, "computed": 49, "ok": True},
        },
    }
    assert diagnosis["summary"]["residual_field_counts"] == {
        "confirmation_required": 2,
        "normalized_command": 77,
        "route": 16,
        "safety.allow": 5,
        "safety.reason": 12,
        "slots": 76,
        "task_type": 16,
    }
    assert diagnosis["aggregates"]["by_split_residual_rows"] == {"dev": 48, "test": 49}
    by_task_family = diagnosis["aggregates"]["by_task_family"]
    assert by_task_family["clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity"] == 44
    assert by_task_family["extract|extract_page|public_readonly|confirm:false|slots:target"] == 26
    assert by_task_family["form_fill|fill_form|requires_confirmation|confirm:true|slots:field"] == 49
    assert diagnosis["execution_scope"]["training_run"] is False
    assert diagnosis["execution_scope"]["prediction_run"] is False
    assert diagnosis["execution_scope"]["evaluator_metric_change"] is False
    assert diagnosis["claims"]["held_out_recovery_claim"] is False
    assert diagnosis["claims"]["soft_slot_f1_primary_metric"] is False


def test_formal_heldout_residual_family_cli_writes_public_safe_report(
    tmp_path: Path, capsys: Any
) -> None:
    output_dir = tmp_path / "formal-heldout-residual-family-diagnosis"

    assert (
        eval_cli.main(
            [
                "diagnose-formal-heldout-residual-families",
                "--formal-manifest",
                (FORMAL_DIR / "formal_public_heldout_prediction.json").as_posix(),
                "--dev-gold",
                (FORMAL_DIR / "dev" / "dev_gold.jsonl").as_posix(),
                "--dev-predictions",
                (FORMAL_DIR / "dev" / "predictions.jsonl").as_posix(),
                "--test-gold",
                (FORMAL_DIR / "test" / "test_gold.jsonl").as_posix(),
                "--test-predictions",
                (FORMAL_DIR / "test" / "predictions.jsonl").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    json_path = output_dir / "formal_heldout_residual_family_diagnosis.json"
    markdown_path = output_dir / "formal_heldout_residual_family_diagnosis.md"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == json_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()

    diagnosis = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert diagnosis["summary"]["residual_row_count"] == 97
    assert "not training, not a prediction rerun" in markdown
    assert "internal diagnostic-only" in markdown
    assert scan_paths([output_dir]).ok is True

    direct_output = tmp_path / "direct"
    direct_paths = write_formal_heldout_residual_family_report(diagnosis, direct_output)
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_formal_heldout_residual_family_evidence_is_bounded_and_public_safe() -> None:
    manifest = read_json(DIAGNOSIS_DIR / "manifest.json")
    diagnosis = read_json(DIAGNOSIS_DIR / "formal_heldout_residual_family_diagnosis.json")

    assert manifest["evidence_kind"] == "formal_heldout_residual_family_diagnosis"
    assert manifest["summary"]["residual_row_count"] == 97
    assert manifest["summary"]["source_count_consistency"]["ok"] is True
    assert manifest["summary"]["soft_slot_f1_primary_metric"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["held_out_recovery_claim"] is False
    assert manifest["artifact_policy"]["prediction_repair_or_replacement"] is False
    assert manifest["artifact_policy"]["evaluator_metric_change"] is False
    assert manifest["artifact_policy"]["training_run"] is False
    assert diagnosis["claims"]["production_readiness_claim"] is False
    assert diagnosis["claims"]["semantic_equivalence_primary_metric"] is False
    assert scan_paths([DIAGNOSIS_DIR]).ok is True
