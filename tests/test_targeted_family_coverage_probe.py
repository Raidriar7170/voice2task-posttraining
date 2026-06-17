import json
from pathlib import Path

from voice2task.leak_scan import scan_paths
from voice2task.training import run_sft

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_MANIFEST = REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json"
TARGETED_SOURCE_IDS = [
    "seed-open-help",
    "seed-clarify-target",
    "seed-form-nickname",
    "seed-block-transfer",
]
TARGETED_ROW_IDS = [
    "seed-open-help",
    "seed-open-help-aug-1",
    "seed-open-help-aug-2",
    "seed-clarify-target",
    "seed-clarify-target-aug-1",
    "seed-clarify-target-aug-2",
    "seed-form-nickname",
    "seed-form-nickname-aug-1",
    "seed-form-nickname-aug-2",
    "seed-block-transfer",
    "seed-block-transfer-aug-1",
    "seed-block-transfer-aug-2",
]


def test_sft_dry_run_records_targeted_train_source_id_selection(tmp_path: Path) -> None:
    config_path = tmp_path / "targeted-sft.json"
    config_path.write_text(
        json.dumps(
            {
                "base_model": "Qwen/Qwen2.5-7B-Instruct",
                "allow_heavy_training": True,
                "dataset_split": "train",
                "train_source_ids": TARGETED_SOURCE_IDS,
                "output_root": "<a100_project_root>",
                "lora": {
                    "r": 16,
                    "alpha": 32,
                    "dropout": 0.05,
                    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
                },
            }
        ),
        encoding="utf-8",
    )

    metadata = run_sft(
        config_path=config_path,
        manifest_path=PUBLIC_SAMPLE_MANIFEST,
        output_dir=tmp_path / "run",
        dry_run=True,
    )

    assert metadata["training_split"] == "train"
    assert metadata["training_source_ids"] == TARGETED_SOURCE_IDS
    assert metadata["training_rows_before_source_filter"] == 261
    assert metadata["training_rows_used"] == 12
    assert metadata["training_row_ids"] == TARGETED_ROW_IDS
    assert metadata["training_source_id_counts"] == {
        "seed-block-transfer": 3,
        "seed-clarify-target": 3,
        "seed-form-nickname": 3,
        "seed-open-help": 3,
    }
    assert metadata["dataset_load"]["training_rows_before_source_filter"] == 261
    assert metadata["dataset_load"]["training_rows_used"] == 12
    assert metadata["dataset_load"]["training_source_ids"] == TARGETED_SOURCE_IDS


def test_targeted_family_coverage_a100_configs_are_split_specific_and_public_safe() -> None:
    sft_config_path = REPO_ROOT / "configs" / "sft-a100-targeted-family-coverage-rerun.json"
    prediction_config_paths = {
        "train": REPO_ROOT / "configs" / "sft-a100-targeted-family-coverage-train-prediction.json",
        "dev": REPO_ROOT / "configs" / "sft-a100-targeted-family-coverage-dev-prediction.json",
        "test": REPO_ROOT / "configs" / "sft-a100-targeted-family-coverage-test-prediction.json",
    }

    sft_config = json.loads(sft_config_path.read_text(encoding="utf-8"))
    serialized_sft = json.dumps(sft_config, ensure_ascii=False, sort_keys=True)
    assert sft_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert sft_config["dataset_manifest_id"] == "public-sample-20260613T072200Z"
    assert sft_config["dataset_split"] == "train"
    assert sft_config["allow_heavy_training"] is True
    assert sft_config["targeted_family_coverage_probe"] is True
    assert sft_config["train_source_ids"] == TARGETED_SOURCE_IDS
    assert sft_config["output_root"] == "<a100_project_root>"
    assert sft_config["adapter_output_dir"] == (
        "<a100_project_root>/runs/a100-targeted-family-coverage-probe/adapter"
    )
    assert "/mnt/data/" not in serialized_sft
    assert "/Users/" not in serialized_sft

    for split, config_path in prediction_config_paths.items():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

        assert config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
        assert config["dataset_manifest_id"] == "public-sample-20260613T072200Z"
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["targeted_family_coverage_probe"] is True
        assert config["generalization_claim"] is False
        assert config["output_root"] == "<a100_project_root>"
        assert config["adapter_path"] == (
            "<a100_project_root>/runs/a100-targeted-family-coverage-probe/adapter"
        )
        assert config["evidence_output_dir"] == (
            f"<a100_project_root>/evidence/a100-targeted-family-coverage-probe/{split}"
        )
        assert "allow_heavy_training" not in config
        assert "adapter_output_dir" not in config
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized
        assert scan_paths([config_path]).ok is True

    assert scan_paths([sft_config_path, *prediction_config_paths.values()]).ok is True


def test_targeted_family_coverage_evidence_records_partial_transfer_without_release_claims() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-targeted-family-coverage-probe"
    manifest_path = evidence_dir / "manifest.json"
    report_path = evidence_dir / "report.md"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report_text = report_path.read_text(encoding="utf-8")

    assert manifest["evidence_kind"] == "a100_targeted_family_coverage_probe"
    assert manifest["evidence_status"] == "private_adapter_public_split_predictions_written"
    assert manifest["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert manifest["dataset_manifest_id"] == "public-sample-20260613T072200Z"
    assert manifest["training_source_ids"] == TARGETED_SOURCE_IDS
    assert manifest["training_rows_used"] == 12
    assert manifest["training_row_ids"] == TARGETED_ROW_IDS
    assert manifest["overall_interpretation"] == "targeted_family_coverage_partial_transfer"

    split_results = manifest["split_results"]
    assert split_results["train"]["prediction_count"] == 18
    assert split_results["train"]["contract_exact_match"] == 1.0
    assert split_results["train"]["slot_f1"] == 1.0
    assert split_results["dev"]["prediction_count"] == 6
    assert split_results["dev"]["contract_exact_match"] == 1 / 6
    assert split_results["dev"]["slot_f1"] == 0.5
    assert split_results["dev"]["slot_f1_soft"] == 0.9333333333333332
    assert split_results["test"]["prediction_count"] == 6
    assert split_results["test"]["contract_exact_match"] == 1 / 6
    assert split_results["test"]["slot_f1"] == 0.5
    assert split_results["test"]["slot_f1_soft"] == 0.5

    comparison = manifest["comparison"]
    assert comparison["current_tiny_adapter_heldout_exact"] == {"dev": 0.0, "test": 0.0}
    assert comparison["prior_broad_residual_repair_exact"] == {
        "train": 1 / 3,
        "dev": 0.0,
        "test": 0.0,
    }
    assert comparison["targeted_family_coverage_exact"] == {
        "train": 1.0,
        "dev": 1 / 6,
        "test": 1 / 6,
    }
    assert comparison["dev_test_improved_from_current_tiny"] == {"dev": True, "test": True}
    assert comparison["train_exact_improved_from_prior_broad_residual_repair"] is True

    claims = manifest["claims"]
    assert claims["targeted_family_coverage_probe"] is True
    assert claims["held_out_generalization_recovered"] is False
    assert claims["model_recovery_claim"] is False
    assert claims["private_corpus_generalization_claim"] is False
    assert claims["adapter_release"] is False
    assert claims["checkpoint_release"] is False
    assert claims["production_readiness_claim"] is False
    assert claims["semantic_equivalence_primary_metric"] is False
    assert claims["evaluator_relaxation"] is False
    assert claims["prediction_repair_or_replacement"] is False

    assert "partial held-out movement" in report_text
    assert "did not fully recover held-out generalization" in report_text
    assert "strict `contract_exact_match` remains primary" in report_text
    assert scan_paths([evidence_dir]).ok is True
