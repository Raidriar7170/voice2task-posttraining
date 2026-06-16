import json
from pathlib import Path

import pytest

from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_formal_public_heldout_prediction_report
from voice2task.training import run_sft_prediction_export

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_MANIFEST = REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json"
CONFIG_DIR = REPO_ROOT / "configs"


def test_formal_public_heldout_prediction_configs_use_current_manifest_and_private_override() -> None:
    current_manifest = read_json(PUBLIC_SAMPLE_MANIFEST)
    config_paths = {
        "dev": CONFIG_DIR / "sft-a100-formal-public-heldout-dev-prediction.json",
        "test": CONFIG_DIR / "sft-a100-formal-public-heldout-test-prediction.json",
    }

    for split, config_path in config_paths.items():
        config = read_json(config_path)
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

        assert config["dataset_manifest_id"] == current_manifest["manifest_id"]
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["generalization_claim"] is False
        assert config["formal_public_sample_heldout_prediction"] is True
        assert config["private_override_required"] is True
        assert config["output_root"] == "<a100_project_root>"
        assert config["adapter_path"] == (
            "<a100_project_root>/runs/a100-merged-slot-value-heldout-eval/adapter"
        )
        assert config["evidence_output_dir"] == (
            f"<a100_project_root>/evidence/a100-formal-public-heldout-prediction/{split}"
        )
        assert "allow_heavy_training" not in config
        assert "adapter_output_dir" not in config
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized

    assert scan_paths(list(config_paths.values())).ok is True


def test_formal_public_heldout_prediction_fixture_checks_current_dev_test_row_selection(
    tmp_path: Path,
) -> None:
    expected_counts = {"dev": 69, "test": 69}
    for split, expected_count in expected_counts.items():
        metadata = run_sft_prediction_export(
            config_path=CONFIG_DIR / f"sft-a100-formal-public-heldout-{split}-prediction.json",
            manifest_path=PUBLIC_SAMPLE_MANIFEST,
            output_path=tmp_path / split / "predictions.jsonl",
            dry_run=False,
            fixture_mode=True,
        )

        assert metadata["dataset_manifest_id"] == read_json(PUBLIC_SAMPLE_MANIFEST)["manifest_id"]
        assert metadata["prediction_split"] == split
        assert metadata["prediction_status"] == "fixture_predictions_written"
        assert metadata["prediction_source_kind"] == "public_sample_contract_fixture"
        assert metadata["prediction_count"] == expected_count
        assert metadata["prediction_rows_before_limit"] == expected_count
        assert len(metadata["prediction_row_ids"]) == expected_count
        assert all(f"-{split}-" in row_id or row_id.startswith("seed-") for row_id in metadata["prediction_row_ids"])


def test_formal_public_heldout_prediction_report_records_blocked_status_without_quality_claims(
    tmp_path: Path,
) -> None:
    paths = write_formal_public_heldout_prediction_report(
        public_manifest=read_json(PUBLIC_SAMPLE_MANIFEST),
        output_dir=tmp_path / "formal-public-heldout",
        run_status="blocked",
        blocked_reason="private_adapter_not_confirmed",
        metrics_by_split={},
        prediction_metadata_by_split={},
        artifact_paths_by_split={},
        leak_scan_result={"ok": True, "findings": []},
    )

    evidence = read_json(paths["json"])
    manifest = read_json(paths["manifest"])
    markdown = paths["markdown"].read_text(encoding="utf-8")

    assert evidence["evidence_kind"] == "a100_formal_public_heldout_prediction"
    assert evidence["run_status"] == "blocked"
    assert evidence["blocked_reason"] == "private_adapter_not_confirmed"
    assert evidence["dataset_manifest_id"] == read_json(PUBLIC_SAMPLE_MANIFEST)["manifest_id"]
    assert evidence["prediction_splits"] == ["dev", "test"]
    assert evidence["split_results"] == {}
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert evidence["claims"]["prediction_repair_or_rescore"] is False
    assert manifest["evidence_kind"] == evidence["evidence_kind"]
    assert manifest["run_status"] == "blocked"
    assert "private_adapter_not_confirmed" in markdown
    assert scan_paths([paths["json"], paths["markdown"], paths["manifest"]]).ok is True


def test_committed_formal_public_heldout_prediction_evidence_is_observed_but_not_recovered() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-formal-public-heldout-prediction"
    evidence = read_json(evidence_dir / "formal_public_heldout_prediction.json")
    manifest = read_json(evidence_dir / "manifest.json")
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    leak_scan = read_json(evidence_dir / "leak_scan_result.json")

    assert evidence["evidence_kind"] == "a100_formal_public_heldout_prediction"
    assert evidence["run_status"] == "observed"
    assert evidence["dataset_manifest_id"] == "public-sample-20260616T022151Z"
    assert evidence["formal_public_sample_counts"] == {"dpo_pairs": 742, "seed_rows": 86, "sft_rows": 240}
    assert evidence["formal_public_sample_split_counts"] == {"dev": 69, "test": 69, "train": 102}
    assert evidence["training_status"] == "prediction_only_no_training"
    assert evidence["prediction_splits"] == ["dev", "test"]
    assert evidence["overall_interpretation"] == "formal_public_heldout_partial_signal"

    split_results = evidence["split_results"]
    assert split_results["dev"]["prediction_count"] == 69
    assert split_results["dev"]["contract_exact_match"] == pytest.approx(0.30434782608695654)
    assert split_results["dev"]["json_valid_rate"] == 1.0
    assert split_results["dev"]["task_type_accuracy"] == pytest.approx(0.855072463768116)
    assert split_results["dev"]["route_accuracy"] == pytest.approx(0.855072463768116)
    assert split_results["dev"]["slot_f1"] == pytest.approx(0.391304347826087)
    assert split_results["dev"]["slot_f1_soft"] == pytest.approx(0.7315387631291138)
    assert split_results["dev"]["safety_recall"] == pytest.approx(0.6666666666666666)
    assert split_results["test"]["prediction_count"] == 69
    assert split_results["test"]["contract_exact_match"] == pytest.approx(0.2898550724637681)
    assert split_results["test"]["json_valid_rate"] == 1.0
    assert split_results["test"]["task_type_accuracy"] == pytest.approx(0.9130434782608695)
    assert split_results["test"]["route_accuracy"] == pytest.approx(0.9130434782608695)
    assert split_results["test"]["slot_f1"] == pytest.approx(0.5072463768115942)
    assert split_results["test"]["slot_f1_soft"] == pytest.approx(0.7609315000619348)
    assert split_results["test"]["safety_recall"] == pytest.approx(0.9166666666666666)

    claims = evidence["claims"]
    assert claims["prediction_only"] is True
    assert claims["training_performed"] is False
    assert claims["held_out_generalization_recovered"] is False
    assert claims["model_recovery_claim"] is False
    assert claims["adapter_release"] is False
    assert claims["checkpoint_release"] is False
    assert claims["prediction_repair_or_rescore"] is False
    assert claims["soft_slot_f1_primary_metric"] is False
    assert manifest["overall_interpretation"] == evidence["overall_interpretation"]
    assert leak_scan["ok"] is True
    assert "Strict `contract_exact_match` remains primary." in report
    assert "not held-out recovery" in report
    assert scan_paths([evidence_dir]).ok is True
