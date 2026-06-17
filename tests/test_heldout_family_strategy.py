import json
from pathlib import Path
from typing import Any

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import diagnose_heldout_family_strategy
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_heldout_family_strategy_report

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_DIR = REPO_ROOT / "data" / "public-samples"
TINY_TRAIN_DIR = REPO_ROOT / "reports" / "public-sample" / "current-manifest-tiny-overfit-probe"
HELDOUT_DIR = REPO_ROOT / "reports" / "public-sample" / "current-tiny-adapter-heldout-prediction"
DIAGNOSIS_DIR = REPO_ROOT / "reports" / "public-sample" / "heldout-family-strategy-diagnosis"


def _current_inputs() -> dict[str, Any]:
    return {
        "load_rows_path": PUBLIC_SAMPLE_DIR / "sft_public_sample.jsonl",
        "manifest_path": PUBLIC_SAMPLE_DIR / "manifest_public_sample.json",
        "tiny_overfit_manifest": read_json(TINY_TRAIN_DIR / "manifest.json"),
        "heldout_manifest": read_json(HELDOUT_DIR / "manifest.json"),
        "heldout_alignment_by_split": {
            split: read_json(HELDOUT_DIR / split / "alignment_diagnostics.json") for split in ("dev", "test")
        },
        "heldout_schema_by_split": {
            split: read_json(HELDOUT_DIR / split / "schema_diagnostics.json") for split in ("dev", "test")
        },
    }


def test_heldout_family_strategy_diagnostic_separates_tiny_subset_from_dataset_coverage() -> None:
    diagnosis = diagnose_heldout_family_strategy(**_current_inputs())
    current_manifest = read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")

    assert diagnosis["evidence_kind"] == "heldout_family_strategy_diagnosis"
    assert diagnosis["source_manifest"]["manifest_id"] == current_manifest["manifest_id"]
    assert diagnosis["summary"]["heldout_contract_exact_match"] == {"dev": 0.0, "test": 0.0}
    assert diagnosis["summary"]["tiny_training_subset_family_count"] == 1
    assert diagnosis["summary"]["heldout_residual_family_count"] == 138
    assert diagnosis["summary"]["broad_data_scaling_recommended"] is False
    assert diagnosis["strategy_recommendation"]["primary"] == (
        "targeted_family_coverage_probe_before_broad_scaling"
    )
    assert diagnosis["strategy_recommendation"]["requires_user_confirmation"] is True
    assert diagnosis["execution_scope"]["training_run"] is False
    assert diagnosis["claims"]["model_recovery_claim"] is False
    assert diagnosis["claims"]["held_out_generalization_claim"] is False

    residuals = {entry["source_family_id"]: entry for entry in diagnosis["heldout_family_residuals"]}
    assert {
        "seed-block-purchase",
        "seed-clarify-ambiguous",
        "seed-form-email",
        "seed-open-example",
    }.issubset(residuals)
    assert residuals["seed-open-example"]["train_analog_row_count"] == 35
    assert residuals["seed-open-example"]["tiny_subset_row_count"] == 0
    assert residuals["seed-open-example"]["train_analog_family_id"] == (
        "candidate-current-retry-public-navigation-non-confirmation-preservation"
    )
    assert residuals["seed-open-example"]["contract_family_key"] == (
        "navigate|open_url|public_readonly|confirm:false|slots:url"
    )
    assert residuals["seed-clarify-ambiguous"]["dpo_hard_negative_category"] == "clarify_action_drift"
    assert residuals["seed-form-email"]["schema_invalid_prediction_count"] == 2
    assert residuals["seed-block-purchase"]["train_analog_family_id"] == "candidate-blocked-payment-canonical-command"


def test_heldout_family_strategy_cli_writes_public_safe_report(tmp_path: Path, capsys: Any) -> None:
    output_dir = tmp_path / "heldout-family-strategy"

    assert (
        eval_cli.main(
            [
                "diagnose-heldout-family-strategy",
                "--sft",
                (PUBLIC_SAMPLE_DIR / "sft_public_sample.jsonl").as_posix(),
                "--manifest",
                (PUBLIC_SAMPLE_DIR / "manifest_public_sample.json").as_posix(),
                "--tiny-overfit-manifest",
                (TINY_TRAIN_DIR / "manifest.json").as_posix(),
                "--heldout-manifest",
                (HELDOUT_DIR / "manifest.json").as_posix(),
                "--dev-alignment",
                (HELDOUT_DIR / "dev" / "alignment_diagnostics.json").as_posix(),
                "--test-alignment",
                (HELDOUT_DIR / "test" / "alignment_diagnostics.json").as_posix(),
                "--dev-schema",
                (HELDOUT_DIR / "dev" / "schema_diagnostics.json").as_posix(),
                "--test-schema",
                (HELDOUT_DIR / "test" / "schema_diagnostics.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    json_path = output_dir / "heldout_family_strategy_diagnosis.json"
    markdown_path = output_dir / "heldout_family_strategy_diagnosis.md"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == json_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()

    diagnosis = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert diagnosis["strategy_recommendation"]["primary"] == (
        "targeted_family_coverage_probe_before_broad_scaling"
    )
    assert "not blind data scaling" in markdown
    assert "targeted family coverage" in markdown
    assert "not a model recovery claim" in markdown
    assert scan_paths([output_dir]).ok is True

    direct_output = tmp_path / "direct"
    direct_paths = write_heldout_family_strategy_report(diagnosis, direct_output)
    assert direct_paths["json"].exists()
    assert direct_paths["markdown"].exists()


def test_committed_heldout_family_strategy_evidence_is_bounded_and_public_safe() -> None:
    manifest = read_json(DIAGNOSIS_DIR / "manifest.json")
    diagnosis = read_json(DIAGNOSIS_DIR / "heldout_family_strategy_diagnosis.json")

    assert manifest["evidence_kind"] == "heldout_family_strategy_diagnosis"
    assert manifest["summary"]["heldout_contract_exact_match"] == {"dev": 0.0, "test": 0.0}
    assert manifest["summary"]["broad_data_scaling_recommended"] is False
    assert manifest["strategy_recommendation"]["primary"] == (
        "targeted_family_coverage_probe_before_broad_scaling"
    )
    assert manifest["strategy_recommendation"]["requires_user_confirmation"] is True
    assert manifest["execution_scope"]["training_run"] is False
    assert manifest["execution_scope"]["new_data_generated"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert diagnosis["claims"]["model_recovery_claim"] is False
    assert diagnosis["claims"]["held_out_generalization_claim"] is False
    assert scan_paths([DIAGNOSIS_DIR]).ok is True
