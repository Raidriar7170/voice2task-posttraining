import json
from pathlib import Path

import pytest
from public_sample_fixtures import (
    PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID,
    SCALED_PUBLIC_SAMPLE_MANIFEST_ID,
    write_pre_scaled_public_sample_fixture,
)

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

        assert config["dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
        assert config["dataset_manifest_id"] != current_manifest["manifest_id"]
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
            "<a100_project_root>/evidence/"
            f"a100-formal-public-heldout-prediction-after-confirmation-marker-merge/{split}"
        )
        assert "allow_heavy_training" not in config
        assert "adapter_output_dir" not in config
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized

    assert scan_paths(list(config_paths.values())).ok is True


def test_formal_public_heldout_prediction_fixture_checks_current_dev_test_row_selection(
    tmp_path: Path,
) -> None:
    manifest_path = write_pre_scaled_public_sample_fixture(tmp_path)
    expected_counts = {"dev": 69, "test": 69}
    for split, expected_count in expected_counts.items():
        metadata = run_sft_prediction_export(
            config_path=CONFIG_DIR / f"sft-a100-formal-public-heldout-{split}-prediction.json",
            manifest_path=manifest_path,
            output_path=tmp_path / split / "predictions.jsonl",
            dry_run=False,
            fixture_mode=True,
        )

        assert metadata["dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
        assert metadata["prediction_split"] == split
        assert metadata["prediction_status"] == "fixture_predictions_written"
        assert metadata["prediction_source_kind"] == "public_sample_contract_fixture"
        assert metadata["prediction_count"] == expected_count
        assert metadata["prediction_rows_before_limit"] == expected_count
        assert len(metadata["prediction_row_ids"]) == expected_count
        assert all(f"-{split}-" in row_id or row_id.startswith("seed-") for row_id in metadata["prediction_row_ids"])


def test_scaled_public_sample_current_123_adapter_prediction_configs_preserve_boundaries() -> None:
    config_paths = {
        "dev": CONFIG_DIR / "sft-a100-scaled-public-sample-current-123-adapter-dev-prediction.json",
        "test": CONFIG_DIR / "sft-a100-scaled-public-sample-current-123-adapter-test-prediction.json",
    }

    for split, config_path in config_paths.items():
        config = read_json(config_path)
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

        assert config["dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
        assert config["target_dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
        assert config["source_adapter_runtime"] == "a100-current-train-split-sft-retry"
        assert config["source_adapter_dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
        assert config["requires_paired_training_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
        assert config["adapter_path"] == "<a100_project_root>/runs/a100-current-train-split-sft-retry/adapter"
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["generalization_claim"] is False
        assert config["formal_public_sample_heldout_prediction"] is True
        assert config["private_override_required"] is True
        assert config["output_root"] == "<a100_project_root>"
        training_only_keys = {
            "adapter_output_dir",
            "allow_heavy_training",
            "gradient_accumulation_steps",
            "learning_rate",
            "logging_steps",
            "lora_rank",
            "max_steps",
            "num_train_epochs",
            "save_steps",
            "train_split",
        }
        assert training_only_keys.isdisjoint(config)
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized

    assert scan_paths(list(config_paths.values())).ok is True


def test_scaled_public_sample_current_123_adapter_prediction_fixture_checks_dev_test_row_selection(
    tmp_path: Path,
) -> None:
    expected_counts = {"dev": 207, "test": 207}
    for split, expected_count in expected_counts.items():
        metadata = run_sft_prediction_export(
            config_path=CONFIG_DIR / f"sft-a100-scaled-public-sample-current-123-adapter-{split}-prediction.json",
            manifest_path=PUBLIC_SAMPLE_MANIFEST,
            output_path=tmp_path / split / "predictions.jsonl",
            dry_run=False,
            fixture_mode=True,
        )

        assert metadata["dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
        assert metadata["prediction_split"] == split
        assert metadata["prediction_status"] == "fixture_predictions_written"
        assert metadata["prediction_source_kind"] == "public_sample_contract_fixture"
        assert metadata["prediction_count"] == expected_count
        assert metadata["prediction_rows_before_limit"] == expected_count
        assert len(metadata["prediction_row_ids"]) == expected_count


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


def test_formal_public_heldout_prediction_report_records_boundary_changed_semantics(
    tmp_path: Path,
) -> None:
    current_manifest = read_json(PUBLIC_SAMPLE_MANIFEST)
    paths = write_formal_public_heldout_prediction_report(
        public_manifest=current_manifest,
        output_dir=tmp_path / "formal-public-heldout-after-confirmation-marker-merge",
        run_status="blocked",
        blocked_reason="idle_gpu_unavailable",
        metrics_by_split={},
        prediction_metadata_by_split={},
        artifact_paths_by_split={},
        leak_scan_result={"ok": True, "findings": []},
        comparison_boundary={
            "prior_dataset_manifest_id": "public-sample-20260616T022151Z",
            "prior_evidence_dir": "reports/public-sample/a100-formal-public-heldout-prediction",
            "direct_improvement_regression_comparison_valid": True,
            "reason": "formal_public_sample_boundary_changed_after_confirmation_marker_extension_merge",
        },
    )

    evidence = read_json(paths["json"])
    manifest = read_json(paths["manifest"])
    markdown = paths["markdown"].read_text(encoding="utf-8")

    expected_boundary = {
        "current_dataset_manifest_id": current_manifest["manifest_id"],
        "prior_dataset_manifest_id": "public-sample-20260616T022151Z",
        "prior_evidence_dir": "reports/public-sample/a100-formal-public-heldout-prediction",
        "direct_improvement_regression_comparison_valid": False,
        "reason": "formal_public_sample_boundary_changed_after_confirmation_marker_extension_merge",
    }
    assert evidence["comparison_boundary"] == expected_boundary
    assert manifest["comparison_boundary"] == expected_boundary
    assert current_manifest["manifest_id"] in markdown
    assert "public-sample-20260616T022151Z" in markdown
    assert "not a clean direct improvement/regression comparison" in markdown
    assert scan_paths([paths["json"], paths["markdown"], paths["manifest"]]).ok is True


def test_formal_public_heldout_prediction_report_records_source_adapter_runtime(
    tmp_path: Path,
) -> None:
    paths = write_formal_public_heldout_prediction_report(
        public_manifest=read_json(PUBLIC_SAMPLE_MANIFEST),
        output_dir=tmp_path / "current-manifest-sft-v3-baseline",
        run_status="blocked",
        blocked_reason="private_adapter_not_confirmed",
        source_adapter_runtime="a100-form-fill-remediation-sft-v3",
        leak_scan_result={"ok": True, "findings": []},
    )

    evidence = read_json(paths["json"])
    manifest = read_json(paths["manifest"])
    markdown = paths["markdown"].read_text(encoding="utf-8")

    assert evidence["source_adapter_runtime"] == "a100-form-fill-remediation-sft-v3"
    assert manifest["source_adapter_runtime"] == "a100-form-fill-remediation-sft-v3"
    assert "a100-form-fill-remediation-sft-v3" in markdown
    assert "a100-merged-slot-value-heldout-eval" not in markdown
    assert scan_paths([paths["json"], paths["markdown"], paths["manifest"]]).ok is True


def test_committed_post_confirmation_marker_merge_evidence_is_blocked_fail_closed() -> None:
    evidence_dir = (
        REPO_ROOT
        / "reports"
        / "public-sample"
        / "a100-formal-public-heldout-prediction-after-confirmation-marker-merge"
    )
    evidence = read_json(evidence_dir / "formal_public_heldout_prediction.json")
    manifest = read_json(evidence_dir / "manifest.json")
    preflight = read_json(evidence_dir / "a100_preflight_status.json")
    leak_scan = read_json(evidence_dir / "leak_scan_result.json")
    phase_leak_scan = read_json(evidence_dir / "phase_validation_leak_scan_result.json")
    final_phase_leak_scan = read_json(evidence_dir / "final_phase_leak_scan_result.json")
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")

    assert evidence["run_status"] == "blocked"
    assert evidence["blocked_reason"] == "a100_ssh_timeout_remote_dependency_unavailable"
    assert evidence["dataset_manifest_id"] == "public-sample-20260616T074315Z"
    assert evidence["formal_public_sample_counts"] == {"dpo_pairs": 850, "seed_rows": 98, "sft_rows": 252}
    assert evidence["formal_public_sample_split_counts"] == {"dev": 69, "test": 69, "train": 114}
    assert evidence["split_results"] == {}
    assert evidence["prediction_metadata_by_split"] == {}
    assert evidence["overall_interpretation"] == "formal_public_heldout_prediction_blocked"
    assert evidence["claims"]["prediction_only"] is True
    assert evidence["claims"]["training_performed"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert evidence["claims"]["production_readiness_claim"] is False
    assert evidence["claims"]["prediction_repair_or_replacement"] is False
    assert evidence["comparison_boundary"]["current_dataset_manifest_id"] == "public-sample-20260616T074315Z"
    assert evidence["comparison_boundary"]["prior_dataset_manifest_id"] == "public-sample-20260616T022151Z"
    assert evidence["comparison_boundary"]["direct_improvement_regression_comparison_valid"] is False
    assert manifest["diagnostic_artifacts"]["a100_preflight_status"].endswith("a100_preflight_status.json")
    assert manifest["diagnostic_artifacts"]["phase_validation_leak_scan"].endswith(
        "phase_validation_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["final_phase_leak_scan"].endswith("final_phase_leak_scan_result.json")
    assert preflight["status"] == "blocked"
    assert preflight["artifact_policy"]["host_details_omitted"] is True
    assert leak_scan["ok"] is True
    assert phase_leak_scan["ok"] is True
    assert final_phase_leak_scan["ok"] is True
    assert "No model-quality metrics" in report
    assert scan_paths([evidence_dir]).ok is True


def test_committed_scaled_public_sample_current_123_adapter_prediction_is_blocked_fail_closed() -> None:
    evidence_dir = (
        REPO_ROOT
        / "reports"
        / "public-sample"
        / "a100-scaled-public-sample-current-123-adapter-prediction-baseline"
    )
    evidence = read_json(evidence_dir / "formal_public_heldout_prediction.json")
    manifest = read_json(evidence_dir / "manifest.json")
    preflight = read_json(evidence_dir / "a100_preflight_status.json")
    leak_scan = read_json(evidence_dir / "leak_scan_result.json")
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")

    assert evidence["run_status"] == "blocked"
    assert evidence["blocked_reason"] == "a100_ssh_timeout_remote_dependency_unavailable"
    assert evidence["dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert evidence["source_adapter_runtime"] == "a100-current-train-split-sft-retry"
    assert evidence["formal_public_sample_counts"] == {"seed_rows": 240, "sft_rows": 675, "dpo_pairs": 2046}
    assert evidence["formal_public_sample_split_counts"] == {"train": 261, "dev": 207, "test": 207}
    assert evidence["split_results"] == {}
    assert evidence["prediction_metadata_by_split"] == {}
    assert evidence["overall_interpretation"] == "formal_public_heldout_prediction_blocked"
    assert evidence["claims"]["prediction_only"] is True
    assert evidence["claims"]["training_performed"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert evidence["claims"]["production_readiness_claim"] is False
    assert evidence["claims"]["prediction_repair_or_replacement"] is False

    boundary = evidence["comparison_boundary"]
    assert boundary["current_dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert boundary["target_dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert boundary["prior_dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert boundary["source_adapter_dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert boundary["source_adapter_runtime"] == "a100-current-train-split-sft-retry"
    assert boundary["direct_improvement_regression_comparison_valid"] is False

    assert manifest["run_status"] == "blocked"
    assert manifest["dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert manifest["source_adapter_runtime"] == "a100-current-train-split-sft-retry"
    assert preflight["status"] == "blocked"
    assert preflight["execution_scope"]["prediction_run"] is False
    assert preflight["execution_scope"]["metrics_generated"] is False
    assert preflight["artifact_policy"]["host_details_omitted"] is True
    assert leak_scan["ok"] is True
    assert "No model-quality metrics" in report
    assert "not a clean direct improvement/regression comparison" in report
    assert scan_paths([evidence_dir]).ok is True


def test_committed_scaled_public_sample_current_123_adapter_prediction_after_a100_recovery_is_observed() -> None:
    evidence_dir = (
        REPO_ROOT
        / "reports"
        / "public-sample"
        / "a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery"
    )
    evidence = read_json(evidence_dir / "formal_public_heldout_prediction.json")
    manifest = read_json(evidence_dir / "manifest.json")
    preflight = read_json(evidence_dir / "a100_preflight_status.json")
    leak_scan = read_json(evidence_dir / "leak_scan_result.json")
    phase_leak_scan = read_json(evidence_dir / "phase_validation_leak_scan_result.json")
    final_phase_leak_scan = read_json(evidence_dir / "final_phase_leak_scan_result.json")
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")

    assert evidence["run_status"] == "observed"
    assert evidence["dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert evidence["source_adapter_runtime"] == "a100-current-train-split-sft-retry"
    assert evidence["formal_public_sample_counts"] == {"seed_rows": 240, "sft_rows": 675, "dpo_pairs": 2046}
    assert evidence["formal_public_sample_split_counts"] == {"train": 261, "dev": 207, "test": 207}
    assert evidence["overall_interpretation"] == "formal_public_heldout_partial_signal"

    dev = evidence["split_results"]["dev"]
    test = evidence["split_results"]["test"]
    assert dev["prediction_count"] == 207
    assert test["prediction_count"] == 207
    assert dev["contract_exact_match"] == pytest.approx(0.2463768115942029)
    assert dev["slot_f1"] == pytest.approx(0.28743961352657005)
    assert dev["slot_f1_soft"] == pytest.approx(0.6372298122661537)
    assert dev["route_accuracy"] == pytest.approx(0.961352657004831)
    assert dev["safety_recall"] == pytest.approx(1.0)
    assert dev["json_valid_rate"] == pytest.approx(1.0)
    assert test["contract_exact_match"] == pytest.approx(0.2028985507246377)
    assert test["slot_f1"] == pytest.approx(0.2592592592592593)
    assert test["slot_f1_soft"] == pytest.approx(0.6107811374904073)
    assert test["route_accuracy"] == pytest.approx(0.9758454106280193)
    assert test["safety_recall"] == pytest.approx(1.0)
    assert test["json_valid_rate"] == pytest.approx(1.0)

    boundary = evidence["comparison_boundary"]
    assert boundary["current_dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert boundary["target_dataset_manifest_id"] == SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert boundary["prior_dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert boundary["source_adapter_dataset_manifest_id"] == PRE_SCALED_PUBLIC_SAMPLE_MANIFEST_ID
    assert boundary["source_adapter_runtime"] == "a100-current-train-split-sft-retry"
    assert boundary["prior_evidence_dir"] == "reports/public-sample/a100-current-123-train-split-sft-retry"
    assert boundary["runtime_recovery_retry"] is True
    assert boundary["direct_improvement_regression_comparison_valid"] is False

    claims = evidence["claims"]
    assert claims["prediction_only"] is True
    assert claims["training_performed"] is False
    assert claims["held_out_generalization_recovered"] is False
    assert claims["model_recovery_claim"] is False
    assert claims["adapter_release"] is False
    assert claims["checkpoint_release"] is False
    assert claims["production_readiness_claim"] is False
    assert claims["prediction_repair_or_replacement"] is False
    assert claims["soft_slot_f1_primary_metric"] is False

    assert manifest["run_status"] == "observed"
    assert manifest["overall_interpretation"] == evidence["overall_interpretation"]
    assert preflight["status"] == "observed"
    assert preflight["execution_scope"]["prediction_run"] is True
    assert preflight["execution_scope"]["training_run"] is False
    assert preflight["execution_scope"]["metrics_generated"] is True
    assert preflight["selected_gpu_policy"]["explicit_cuda_visible_devices_used"] is True
    assert preflight["artifact_policy"]["private_paths_omitted"] is True
    assert preflight["artifact_policy"]["host_details_omitted"] is True
    assert leak_scan["ok"] is True
    assert phase_leak_scan["ok"] is True
    assert final_phase_leak_scan["ok"] is True
    assert "runtime-recovery prediction-only retry" in report
    assert "not a training change" in report
    assert "model-recovery claim" in report
    assert scan_paths([evidence_dir]).ok is True


def test_committed_current_manifest_sft_v3_prediction_baseline_is_observed_without_recovery_claim() -> None:
    evidence_dir = (
        REPO_ROOT
        / "reports"
        / "public-sample"
        / "a100-current-manifest-sft-v3-prediction-baseline"
    )
    evidence = read_json(evidence_dir / "formal_public_heldout_prediction.json")
    manifest = read_json(evidence_dir / "manifest.json")
    preflight = read_json(evidence_dir / "a100_preflight_status.json")
    leak_scan = read_json(evidence_dir / "leak_scan_result.json")
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")

    assert evidence["run_status"] == "observed"
    assert evidence["dataset_manifest_id"] == "public-sample-20260616T165835Z"
    assert evidence["source_adapter_runtime"] == "a100-form-fill-remediation-sft-v3"
    assert evidence["formal_public_sample_counts"] == {"seed_rows": 100, "sft_rows": 256, "dpo_pairs": 864}
    assert evidence["formal_public_sample_split_counts"] == {"train": 118, "dev": 69, "test": 69}
    assert evidence["overall_interpretation"] == "formal_public_heldout_partial_signal"

    dev = evidence["split_results"]["dev"]
    test = evidence["split_results"]["test"]
    assert dev["prediction_count"] == 69
    assert test["prediction_count"] == 69
    assert dev["contract_exact_match"] == pytest.approx(0.463768115942029)
    assert dev["slot_f1"] == pytest.approx(0.5652173913043478)
    assert dev["safety_recall"] == pytest.approx(0.5555555555555556)
    assert test["contract_exact_match"] == pytest.approx(0.34782608695652173)
    assert test["slot_f1"] == pytest.approx(0.49758454106280187)
    assert test["safety_recall"] == pytest.approx(1.0)

    boundary = evidence["comparison_boundary"]
    assert boundary["current_dataset_manifest_id"] == "public-sample-20260616T165835Z"
    assert boundary["prior_dataset_manifest_id"] == "public-sample-20260616T074315Z"
    assert boundary["direct_improvement_regression_comparison_valid"] is False

    claims = evidence["claims"]
    assert claims["prediction_only"] is True
    assert claims["training_performed"] is False
    assert claims["held_out_generalization_recovered"] is False
    assert claims["model_recovery_claim"] is False
    assert claims["adapter_release"] is False
    assert claims["checkpoint_release"] is False
    assert claims["soft_slot_f1_primary_metric"] is False

    assert manifest["source_adapter_runtime"] == "a100-form-fill-remediation-sft-v3"
    assert preflight["status"] == "ok"
    assert preflight["artifact_policy"]["private_paths_omitted"] is True
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert "public-sample-20260616T165835Z" in report
    assert "not a clean direct improvement/regression comparison" in report
    assert scan_paths([evidence_dir]).ok is True


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


def test_committed_a100_recovery_retry_evidence_is_observed_but_not_recovery_claim() -> None:
    evidence_dir = (
        REPO_ROOT
        / "reports"
        / "public-sample"
        / "a100-formal-public-heldout-prediction-after-a100-recovery"
    )
    evidence = read_json(evidence_dir / "formal_public_heldout_prediction.json")
    manifest = read_json(evidence_dir / "manifest.json")
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    leak_scan = read_json(evidence_dir / "phase_validation_leak_scan_result.json")

    assert evidence["run_status"] == "observed"
    assert evidence["dataset_manifest_id"] == "public-sample-20260616T074315Z"
    assert evidence["formal_public_sample_counts"] == {"seed_rows": 98, "sft_rows": 252, "dpo_pairs": 850}
    assert evidence["formal_public_sample_split_counts"] == {"train": 114, "dev": 69, "test": 69}
    assert evidence["claims"]["training_performed"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert evidence["claims"]["production_readiness_claim"] is False
    assert evidence["claims"]["soft_slot_f1_primary_metric"] is False
    assert evidence["comparison_boundary"]["runtime_recovery_retry"] is True
    assert evidence["comparison_boundary"]["direct_improvement_regression_comparison_valid"] is False
    assert manifest["run_status"] == "observed"
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert "runtime-recovery prediction-only retry" in report
    assert "not a training change" in report
    assert "model-recovery claim" in report
    assert scan_paths([evidence_dir]).ok is True
