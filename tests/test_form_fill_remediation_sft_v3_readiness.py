import json
from pathlib import Path
from typing import Any

from public_sample_fixtures import PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID, write_pre_scaled_public_sample_fixture

from voice2task.cli import report as report_cli
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.training import run_sft

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_MANIFEST = REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json"
CONFIG_DIR = REPO_ROOT / "configs"
SFT_V3_CONFIG = CONFIG_DIR / "sft-a100-form-fill-remediation-v3.json"
DEV_PREDICTION_CONFIG = CONFIG_DIR / "sft-a100-form-fill-remediation-v3-dev-prediction.json"
TEST_PREDICTION_CONFIG = CONFIG_DIR / "sft-a100-form-fill-remediation-v3-test-prediction.json"
BASELINE_EVIDENCE = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "a100-formal-public-heldout-prediction-after-a100-recovery"
    / "formal_public_heldout_prediction.json"
)
TARGET_SELECTION = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "formal-heldout-remediation-target-selection"
    / "formal_heldout_remediation_target_selection.json"
)
REMEDIATION_PLAN = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "form-fill-remediation-plan"
    / "form_fill_remediation_plan.json"
)
READINESS_DIR = REPO_ROOT / "reports" / "public-sample" / "form-fill-remediation-sft-v3-readiness"


def test_form_fill_sft_v3_configs_are_current_public_safe_templates() -> None:
    current_manifest = read_json(PUBLIC_SAMPLE_MANIFEST)
    train_config = read_json(SFT_V3_CONFIG)
    dev_config = read_json(DEV_PREDICTION_CONFIG)
    test_config = read_json(TEST_PREDICTION_CONFIG)
    serialized = json.dumps(
        {"train": train_config, "dev": dev_config, "test": test_config},
        ensure_ascii=False,
        sort_keys=True,
    )

    assert train_config["form_fill_remediation_sft_v3"] is True
    assert train_config["dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert train_config["dataset_manifest_id"] != current_manifest["manifest_id"]
    assert train_config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
    assert train_config["dataset_split"] == "train"
    assert train_config["allow_heavy_training"] is True
    assert train_config["private_override_required"] is True
    assert train_config["generalization_claim"] is False
    assert train_config["output_root"] == "<a100_project_root>"
    assert train_config["adapter_output_dir"] == (
        "<a100_project_root>/runs/a100-form-fill-remediation-sft-v3/adapter"
    )
    assert train_config["reference_runtime"] == "a100-form-fill-remediation-sft-v3"

    for split, config in {"dev": dev_config, "test": test_config}.items():
        assert config["form_fill_remediation_sft_v3_prediction"] is True
        assert config["dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
        assert config["dataset_manifest_id"] != current_manifest["manifest_id"]
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["generalization_claim"] is False
        assert config["private_override_required"] is True
        assert config["output_root"] == "<a100_project_root>"
        assert config["adapter_path"] == "<a100_project_root>/runs/a100-form-fill-remediation-sft-v3/adapter"
        assert "allow_heavy_training" not in config

    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([SFT_V3_CONFIG, DEV_PREDICTION_CONFIG, TEST_PREDICTION_CONFIG]).ok is True


def test_form_fill_sft_v3_dry_run_selects_current_train_split_and_merged_form_fill_rows(
    tmp_path: Path,
) -> None:
    manifest_path = write_pre_scaled_public_sample_fixture(tmp_path)
    manifest = read_json(manifest_path)
    metadata = run_sft(SFT_V3_CONFIG, manifest_path, tmp_path / "sft-v3-dry-run", dry_run=True)

    assert metadata["dry_run"] is True
    assert metadata["training_status"] == "dry_run"
    assert metadata["dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert metadata["training_split"] == "train"
    assert metadata["training_row_limit"] is None
    assert metadata["training_rows_used"] == manifest["split_counts"]["train"] == 123
    assert metadata["training_rows_before_source_filter"] == 123
    assert metadata["heavy_training_gate"]["will_run_heavy_training"] is False

    row_ids = set(metadata["training_row_ids"])
    assert sum(row_id.startswith("candidate-form-fill-remediation-") for row_id in row_ids) == 9
    assert sum(row_id.startswith("candidate-form-fill-confirmation-marker-extension-") for row_id in row_ids) == 12


def test_form_fill_sft_v3_readiness_report_cli_writes_public_safe_non_claiming_evidence(
    tmp_path: Path,
    capsys: Any,
) -> None:
    manifest_path = write_pre_scaled_public_sample_fixture(tmp_path)
    dry_run = run_sft(SFT_V3_CONFIG, manifest_path, tmp_path / "sft-v3-dry-run", dry_run=True)
    output_dir = tmp_path / "readiness"

    assert (
        report_cli.main(
            [
                "form-fill-remediation-sft-v3-readiness",
                "--dry-run-metadata",
                dry_run["metadata_path"],
                "--public-manifest",
                manifest_path.as_posix(),
                "--baseline-evidence",
                BASELINE_EVIDENCE.as_posix(),
                "--target-selection",
                TARGET_SELECTION.as_posix(),
                "--remediation-plan",
                REMEDIATION_PLAN.as_posix(),
                "--sft-config",
                SFT_V3_CONFIG.as_posix(),
                "--dev-prediction-config",
                DEV_PREDICTION_CONFIG.as_posix(),
                "--test-prediction-config",
                TEST_PREDICTION_CONFIG.as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    evidence = read_json(output_dir / "form_fill_remediation_sft_v3_readiness.json")
    manifest = read_json(output_dir / "manifest.json")
    markdown = (output_dir / "form_fill_remediation_sft_v3_readiness.md").read_text(encoding="utf-8")

    assert payload["ok"] is True
    assert evidence["evidence_kind"] == "form_fill_remediation_sft_v3_readiness"
    assert evidence["summary"]["dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert evidence["summary"]["training_rows_used"] == 123
    assert evidence["summary"]["form_fill_remediation_train_rows"] == 21
    assert evidence["summary"]["readiness_status"] == "ready_for_bounded_a100_sft_v3_phase"
    assert evidence["summary"]["recommended_next_change"] == "run-a100-form-fill-remediation-sft-v3"
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["execution_scope"]["prediction_run"] is False
    assert evidence["execution_scope"]["dataset_mutation"] is False
    assert evidence["execution_scope"]["evaluator_metric_change"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert "readiness-only" in markdown
    assert "run-a100-form-fill-remediation-sft-v3" in markdown
    assert scan_paths([output_dir]).ok is True


def test_committed_form_fill_sft_v3_readiness_evidence_is_current_and_non_claiming() -> None:
    evidence = read_json(READINESS_DIR / "form_fill_remediation_sft_v3_readiness.json")
    manifest = read_json(READINESS_DIR / "manifest.json")
    dry_run = read_json(READINESS_DIR / "sft-dry-run" / "adapter_metadata.json")

    assert evidence["summary"]["dataset_manifest_id"] == "public-sample-20260616T165835Z"
    assert evidence["summary"]["baseline_interpretation"] == "formal_public_heldout_partial_signal"
    assert evidence["summary"]["training_rows_used"] == 118
    assert evidence["summary"]["form_fill_remediation_train_rows"] == 21
    assert evidence["summary"]["selected_residual_row_count"] == 29
    assert evidence["summary"]["selected_residual_field_count"] == 49
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["execution_scope"]["prediction_run"] is False
    assert evidence["claims"]["production_readiness_claim"] is False
    assert evidence["claims"]["private_corpus_generalization_claim"] is False
    assert dry_run["training_rows_used"] == 118
    assert dry_run["dataset_manifest_id"] == evidence["summary"]["dataset_manifest_id"]
    assert manifest["diagnostic_artifacts"]["dry_run_metadata"].endswith("sft-dry-run/adapter_metadata.json")
    assert scan_paths([READINESS_DIR, SFT_V3_CONFIG, DEV_PREDICTION_CONFIG, TEST_PREDICTION_CONFIG]).ok is True
