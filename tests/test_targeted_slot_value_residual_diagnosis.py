import json
from pathlib import Path
from typing import Any

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import (
    diagnose_targeted_slot_value_residuals,
    load_predictions,
    load_sft_rows,
)
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_targeted_slot_value_residual_report

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETED_DIR = REPO_ROOT / "reports" / "public-sample" / "a100-targeted-family-coverage-probe"
DIAGNOSIS_DIR = REPO_ROOT / "reports" / "public-sample" / "targeted-slot-value-residual-diagnosis"


def _current_inputs() -> dict[str, Any]:
    return {
        "targeted_manifest": read_json(TARGETED_DIR / "manifest.json"),
        "rows_by_split": {
            split: load_sft_rows(TARGETED_DIR / split / f"{split}_gold.jsonl") for split in ("dev", "test")
        },
        "predictions_by_split": {
            split: load_predictions(TARGETED_DIR / split / "predictions.jsonl") for split in ("dev", "test")
        },
        "alignment_by_split": {
            split: read_json(TARGETED_DIR / split / "alignment_diagnostics.json") for split in ("dev", "test")
        },
    }


def test_targeted_slot_value_residual_diagnostic_classifies_remaining_value_drift() -> None:
    diagnosis = diagnose_targeted_slot_value_residuals(**_current_inputs())

    assert diagnosis["evidence_kind"] == "targeted_slot_value_residual_diagnosis"
    assert diagnosis["diagnostic_mode"] == "local_public_safe_no_training_no_generation_no_metric_change"
    assert diagnosis["source_targeted_probe"]["evidence_kind"] == "a100_targeted_family_coverage_probe"
    assert diagnosis["summary"]["strict_contract_exact_match"] == {"dev": 1 / 6, "test": 1 / 6}
    assert diagnosis["summary"]["residual_row_count"] == 10
    assert diagnosis["summary"]["residual_field_counts"] == {"normalized_command": 4, "slots": 6}
    assert diagnosis["summary"]["residual_drift_bucket_counts"] == {
        "normalized_command_paraphrase_drift": 4,
        "slot_value_canonical_phrase_drift": 3,
        "slot_value_language_variant": 3,
    }
    assert diagnosis["summary"]["broad_scaling_recommended_now"] is False
    assert diagnosis["summary"]["recommended_next_step"] == (
        "design_slot_value_generalization_cases_before_broad_scaling_or_dpo"
    )

    residuals = {(entry["split"], entry["row_id"]): entry for entry in diagnosis["residuals"]}
    assert residuals[("dev", "seed-open-example")]["drift_bucket"] == "normalized_command_paraphrase_drift"
    assert residuals[("dev", "seed-clarify-ambiguous")]["drift_bucket"] == "slot_value_canonical_phrase_drift"
    assert residuals[("test", "seed-form-email")]["drift_bucket"] == "slot_value_language_variant"
    assert residuals[("test", "seed-block-purchase")]["drift_bucket"] == "normalized_command_paraphrase_drift"
    assert residuals[("test", "seed-form-email")]["gold_value"] == {"field": "邮箱"}
    assert residuals[("test", "seed-form-email")]["predicted_value"] == {"field": "email"}

    assert diagnosis["aggregates"]["by_source_family"] == {
        "seed-block-purchase": 2,
        "seed-clarify-ambiguous": 3,
        "seed-form-email": 3,
        "seed-open-example": 2,
    }
    assert diagnosis["execution_scope"]["training_run"] is False
    assert diagnosis["execution_scope"]["prediction_run"] is False
    assert diagnosis["execution_scope"]["evaluator_metric_change"] is False
    assert diagnosis["claims"]["held_out_generalization_recovered"] is False
    assert diagnosis["claims"]["semantic_equivalence_primary_metric"] is False
    assert diagnosis["claims"]["prediction_repair_or_replacement"] is False


def test_targeted_slot_value_residual_cli_writes_public_safe_report(tmp_path: Path, capsys: Any) -> None:
    output_dir = tmp_path / "targeted-slot-value-residuals"

    assert (
        eval_cli.main(
            [
                "diagnose-targeted-slot-value-residuals",
                "--targeted-manifest",
                (TARGETED_DIR / "manifest.json").as_posix(),
                "--dev-gold",
                (TARGETED_DIR / "dev" / "dev_gold.jsonl").as_posix(),
                "--dev-predictions",
                (TARGETED_DIR / "dev" / "predictions.jsonl").as_posix(),
                "--dev-alignment",
                (TARGETED_DIR / "dev" / "alignment_diagnostics.json").as_posix(),
                "--test-gold",
                (TARGETED_DIR / "test" / "test_gold.jsonl").as_posix(),
                "--test-predictions",
                (TARGETED_DIR / "test" / "predictions.jsonl").as_posix(),
                "--test-alignment",
                (TARGETED_DIR / "test" / "alignment_diagnostics.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == (output_dir / "targeted_slot_value_residual_diagnosis.json").as_posix()
    assert cli_output["paths"]["markdown"] == (
        output_dir / "targeted_slot_value_residual_diagnosis.md"
    ).as_posix()
    assert cli_output["paths"]["manifest"] == (output_dir / "manifest.json").as_posix()

    diagnosis = read_json(output_dir / "targeted_slot_value_residual_diagnosis.json")
    markdown = (output_dir / "targeted_slot_value_residual_diagnosis.md").read_text(encoding="utf-8")
    manifest = read_json(output_dir / "manifest.json")
    assert diagnosis["summary"]["residual_drift_bucket_counts"]["slot_value_language_variant"] == 3
    assert manifest["claims"]["held_out_generalization_recovered"] is False
    assert "strict `contract_exact_match` remains primary" in markdown
    assert "not broad scaling yet" in markdown
    assert scan_paths([output_dir]).ok is True

    direct_paths = write_targeted_slot_value_residual_report(diagnosis, tmp_path / "direct")
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()
    assert direct_paths["manifest"].exists()


def test_committed_targeted_slot_value_residual_evidence_is_bounded_and_public_safe() -> None:
    manifest = read_json(DIAGNOSIS_DIR / "manifest.json")
    diagnosis = read_json(DIAGNOSIS_DIR / "targeted_slot_value_residual_diagnosis.json")

    assert manifest["evidence_kind"] == "targeted_slot_value_residual_diagnosis"
    assert manifest["summary"]["residual_row_count"] == 10
    assert manifest["summary"]["residual_field_counts"] == {"normalized_command": 4, "slots": 6}
    assert manifest["summary"]["broad_scaling_recommended_now"] is False
    assert manifest["summary"]["recommended_next_step"] == (
        "design_slot_value_generalization_cases_before_broad_scaling_or_dpo"
    )
    assert diagnosis["claims"]["held_out_generalization_recovered"] is False
    assert diagnosis["claims"]["model_recovery_claim"] is False
    assert diagnosis["claims"]["adapter_release"] is False
    assert diagnosis["claims"]["checkpoint_release"] is False
    assert diagnosis["claims"]["production_readiness_claim"] is False
    assert diagnosis["claims"]["semantic_equivalence_primary_metric"] is False
    assert scan_paths([DIAGNOSIS_DIR]).ok is True
