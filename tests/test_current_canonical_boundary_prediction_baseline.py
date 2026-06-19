import json
from pathlib import Path

from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.training import run_sft_prediction_export

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_MANIFEST = REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json"
CONFIG_DIR = REPO_ROOT / "configs"
EVIDENCE_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "a100-current-canonical-boundary-prediction-baseline"
)

CURRENT_CANONICAL_MANIFEST_ID = "public-sample-20260619T090925Z"
SOURCE_ADAPTER_RUNTIME = "a100-current-train-split-sft-retry"
SOURCE_ADAPTER_MANIFEST_ID = "public-sample-20260617T045941Z"
PRIOR_EVALUATED_MANIFEST_ID = "public-sample-20260617T152259Z"


def test_current_canonical_boundary_prediction_configs_bind_current_manifest() -> None:
    current_manifest = read_json(PUBLIC_SAMPLE_MANIFEST)
    assert current_manifest["manifest_id"] == CURRENT_CANONICAL_MANIFEST_ID

    config_paths = {
        "dev": CONFIG_DIR / "sft-a100-current-canonical-boundary-dev-prediction.json",
        "test": CONFIG_DIR / "sft-a100-current-canonical-boundary-test-prediction.json",
    }

    for split, config_path in config_paths.items():
        config = read_json(config_path)
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

        assert config["dataset_manifest_id"] == CURRENT_CANONICAL_MANIFEST_ID
        assert config["target_dataset_manifest_id"] == CURRENT_CANONICAL_MANIFEST_ID
        assert config["source_adapter_runtime"] == SOURCE_ADAPTER_RUNTIME
        assert config["source_adapter_dataset_manifest_id"] == SOURCE_ADAPTER_MANIFEST_ID
        assert config["requires_paired_training_manifest_id"] == SOURCE_ADAPTER_MANIFEST_ID
        assert config["prediction_split"] == split
        assert config["formal_public_sample_heldout_prediction"] is True
        assert config["allow_private_prediction"] is True
        assert config["generalization_claim"] is False
        assert config["private_override_required"] is True
        assert config["output_root"] == "<a100_project_root>"
        assert config["adapter_path"] == (
            "<a100_project_root>/runs/a100-current-train-split-sft-retry/adapter"
        )
        assert config["evidence_output_dir"] == (
            "<a100_project_root>/evidence/"
            f"a100-current-canonical-boundary-prediction-baseline/{split}"
        )
        assert config["output_policy"] == (
            "current_canonical_boundary_prediction_requires_private_override_no_direct_public_template_run"
        )
        assert config["prediction_artifact_policy"] == (
            "commit_only_sanitized_public_sample_predictions_sidecars_metrics_manifest_and_report"
        )
        assert "allow_heavy_training" not in config
        assert "adapter_output_dir" not in config
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized

    assert scan_paths(list(config_paths.values())).ok is True


def test_current_canonical_boundary_prediction_fixture_checks_dev_test_rows(
    tmp_path: Path,
) -> None:
    expected_counts = {"dev": 207, "test": 207}
    for split, expected_count in expected_counts.items():
        metadata = run_sft_prediction_export(
            config_path=CONFIG_DIR / f"sft-a100-current-canonical-boundary-{split}-prediction.json",
            manifest_path=PUBLIC_SAMPLE_MANIFEST,
            output_path=tmp_path / split / "predictions.jsonl",
            dry_run=False,
            fixture_mode=True,
        )

        assert metadata["dataset_manifest_id"] == CURRENT_CANONICAL_MANIFEST_ID
        assert metadata["prediction_split"] == split
        assert metadata["prediction_status"] == "fixture_predictions_written"
        assert metadata["prediction_source_kind"] == "public_sample_contract_fixture"
        assert metadata["prediction_count"] == expected_count
        assert metadata["prediction_rows_before_limit"] == expected_count
        assert len(metadata["prediction_row_ids"]) == expected_count


def test_committed_current_canonical_boundary_prediction_evidence_is_observed_or_blocked() -> None:
    evidence = read_json(EVIDENCE_DIR / "formal_public_heldout_prediction.json")
    manifest = read_json(EVIDENCE_DIR / "manifest.json")
    preflight = read_json(EVIDENCE_DIR / "a100_preflight_status.json")
    leak_scan = read_json(EVIDENCE_DIR / "leak_scan_result.json")
    phase_leak_scan = read_json(EVIDENCE_DIR / "phase_validation_leak_scan_result.json")
    final_phase_leak_scan = read_json(EVIDENCE_DIR / "final_phase_leak_scan_result.json")
    report = (EVIDENCE_DIR / "report.md").read_text(encoding="utf-8")

    assert evidence["evidence_kind"] == "a100_formal_public_heldout_prediction"
    assert evidence["dataset_manifest_id"] == CURRENT_CANONICAL_MANIFEST_ID
    assert evidence["source_adapter_runtime"] == SOURCE_ADAPTER_RUNTIME
    assert evidence["run_status"] in {"observed", "blocked"}
    assert evidence["formal_public_sample_counts"] == {
        "seed_rows": 247,
        "sft_rows": 696,
        "dpo_pairs": 2100,
    }
    assert evidence["formal_public_sample_split_counts"] == {
        "train": 282,
        "dev": 207,
        "test": 207,
    }
    assert evidence["claims"]["prediction_only"] is True
    assert evidence["claims"]["training_performed"] is False
    assert evidence["claims"]["data_changed"] is False
    assert evidence["claims"]["prediction_repair_or_replacement"] is False
    assert evidence["claims"]["soft_slot_f1_primary_metric"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert evidence["claims"]["checkpoint_release"] is False
    assert evidence["claims"]["production_readiness_claim"] is False
    assert evidence["claims"]["live_browser_benchmark_claim"] is False

    boundary = evidence["comparison_boundary"]
    assert boundary["current_dataset_manifest_id"] == CURRENT_CANONICAL_MANIFEST_ID
    assert boundary["target_dataset_manifest_id"] == CURRENT_CANONICAL_MANIFEST_ID
    assert boundary["prior_dataset_manifest_id"] == PRIOR_EVALUATED_MANIFEST_ID
    assert boundary["source_adapter_dataset_manifest_id"] == SOURCE_ADAPTER_MANIFEST_ID
    assert boundary["direct_improvement_regression_comparison_valid"] is False

    assert manifest["dataset_manifest_id"] == CURRENT_CANONICAL_MANIFEST_ID
    assert manifest["overall_interpretation"] == evidence["overall_interpretation"]
    assert preflight["artifact_policy"]["host_details_omitted"] is True
    assert preflight["artifact_policy"]["ssh_details_omitted"] is True
    assert leak_scan["ok"] is True
    assert phase_leak_scan["ok"] is True
    assert final_phase_leak_scan["ok"] is True
    assert "strict `contract_exact_match` and strict `slot_f1` remain primary" in report
    assert "not a clean direct improvement/regression comparison" in report

    if evidence["run_status"] == "observed":
        assert set(evidence["split_results"]) == {"dev", "test"}
        for split in ("dev", "test"):
            result = evidence["split_results"][split]
            assert result["prediction_count"] == 207
            assert "contract_exact_match" in result
            assert "slot_f1" in result
            assert "slot_f1_soft" in result
            assert "json_valid_rate" in result
    else:
        assert evidence["overall_interpretation"] == "formal_public_heldout_prediction_blocked"
        assert evidence["split_results"] == {}
        assert "No model-quality metrics" in report

    assert scan_paths([EVIDENCE_DIR]).ok is True
