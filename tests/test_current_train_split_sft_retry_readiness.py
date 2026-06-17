import json
from pathlib import Path
from typing import Any

from voice2task.cli import report as report_cli
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.training import run_sft

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_MANIFEST = REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json"
CONFIG_DIR = REPO_ROOT / "configs"
SFT_RETRY_CONFIG = CONFIG_DIR / "sft-a100-current-train-split-retry.json"
DEV_PREDICTION_CONFIG = CONFIG_DIR / "sft-a100-current-train-split-retry-dev-prediction.json"
TEST_PREDICTION_CONFIG = CONFIG_DIR / "sft-a100-current-train-split-retry-test-prediction.json"
CURRENT_BASELINE_EVIDENCE = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "a100-current-manifest-sft-v3-prediction-baseline"
    / "formal_public_heldout_prediction.json"
)
PUBLIC_MERGE_EVIDENCE = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "blocked-payment-safety-repair-public-sample-merge"
    / "blocked_payment_safety_repair_public_sample_merge.json"
)
READINESS_DIR = REPO_ROOT / "reports" / "public-sample" / "current-train-split-sft-retry-readiness"
RETRY_EVIDENCE_DIR = REPO_ROOT / "reports" / "public-sample" / "a100-current-train-split-sft-retry"


def _current_manifest() -> dict[str, Any]:
    return read_json(PUBLIC_SAMPLE_MANIFEST)


def test_current_train_split_retry_configs_are_public_safe_templates() -> None:
    current_manifest = _current_manifest()
    train_config = read_json(SFT_RETRY_CONFIG)
    dev_config = read_json(DEV_PREDICTION_CONFIG)
    test_config = read_json(TEST_PREDICTION_CONFIG)
    serialized = json.dumps(
        {"train": train_config, "dev": dev_config, "test": test_config},
        ensure_ascii=False,
        sort_keys=True,
    )

    assert train_config["current_train_split_sft_retry"] is True
    assert train_config["dataset_manifest_id"] == current_manifest["manifest_id"]
    assert train_config["dataset_split"] == "train"
    assert train_config["allow_heavy_training"] is True
    assert train_config["private_override_required"] is True
    assert train_config["generalization_claim"] is False
    assert train_config["output_root"] == "<a100_project_root>"
    assert train_config["output_dir"] == "<a100_project_root>/runs/a100-current-train-split-sft-retry"
    assert train_config["adapter_output_dir"] == (
        "<a100_project_root>/runs/a100-current-train-split-sft-retry/adapter"
    )
    assert train_config["reference_runtime"] == "a100-current-train-split-sft-retry"

    for split, config in {"dev": dev_config, "test": test_config}.items():
        assert config["current_train_split_sft_retry_prediction"] is True
        assert config["dataset_manifest_id"] == current_manifest["manifest_id"]
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["private_override_required"] is True
        assert config["generalization_claim"] is False
        assert config["adapter_path"] == "<a100_project_root>/runs/a100-current-train-split-sft-retry/adapter"
        assert config["source_adapter_runtime"] == "a100-current-train-split-sft-retry"
        assert "allow_heavy_training" not in config

    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "a100-form-fill-remediation-sft-v3/adapter" not in serialized
    assert scan_paths([SFT_RETRY_CONFIG, DEV_PREDICTION_CONFIG, TEST_PREDICTION_CONFIG]).ok is True


def test_current_train_split_retry_dry_run_selects_repair_rows(tmp_path: Path) -> None:
    current_manifest = _current_manifest()
    metadata = run_sft(SFT_RETRY_CONFIG, PUBLIC_SAMPLE_MANIFEST, tmp_path / "retry-dry-run", dry_run=True)

    assert metadata["dry_run"] is True
    assert metadata["training_status"] == "dry_run"
    assert metadata["dataset_manifest_id"] == current_manifest["manifest_id"]
    assert metadata["training_split"] == "train"
    assert metadata["training_rows_used"] == current_manifest["split_counts"]["train"] == 118
    assert metadata["training_rows_before_source_filter"] == 118
    assert metadata["heavy_training_gate"]["will_run_heavy_training"] is False

    row_ids = set(metadata["training_row_ids"])
    assert sum(row_id.startswith("candidate-form-fill-remediation-") for row_id in row_ids) == 9
    assert sum(row_id.startswith("candidate-form-fill-confirmation-marker-extension-") for row_id in row_ids) == 12
    assert sum(row_id.startswith("candidate-blocked-payment-repair-") for row_id in row_ids) == 4


def test_current_train_split_retry_readiness_cli_writes_public_safe_non_claiming_evidence(
    tmp_path: Path,
    capsys: Any,
) -> None:
    dry_run = run_sft(SFT_RETRY_CONFIG, PUBLIC_SAMPLE_MANIFEST, tmp_path / "retry-dry-run", dry_run=True)
    output_dir = tmp_path / "readiness"

    assert (
        report_cli.main(
            [
                "current-train-split-sft-retry-readiness",
                "--dry-run-metadata",
                dry_run["metadata_path"],
                "--public-manifest",
                PUBLIC_SAMPLE_MANIFEST.as_posix(),
                "--current-baseline-evidence",
                CURRENT_BASELINE_EVIDENCE.as_posix(),
                "--public-merge-evidence",
                PUBLIC_MERGE_EVIDENCE.as_posix(),
                "--sft-config",
                SFT_RETRY_CONFIG.as_posix(),
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
    evidence = read_json(output_dir / "current_train_split_sft_retry_readiness.json")
    manifest = read_json(output_dir / "manifest.json")
    markdown = (output_dir / "current_train_split_sft_retry_readiness.md").read_text(encoding="utf-8")

    assert payload["ok"] is True
    assert evidence["evidence_kind"] == "current_train_split_sft_retry_readiness"
    assert evidence["summary"]["dataset_manifest_id"] == _current_manifest()["manifest_id"]
    assert evidence["summary"]["training_rows_used"] == 118
    assert evidence["summary"]["form_fill_repair_train_rows"] == 21
    assert evidence["summary"]["blocked_payment_repair_train_rows"] == 4
    assert evidence["summary"]["readiness_status"] == "ready_for_bounded_a100_sft_retry_phase"
    assert evidence["summary"]["recommended_next_change"] == "run-a100-current-train-split-sft-retry"
    assert evidence["current_strict_metrics"]["dev"]["contract_exact_match"] == 0.463768115942029
    assert evidence["current_strict_metrics"]["dev"]["safety_recall"] == 0.5555555555555556
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["execution_scope"]["prediction_run"] is False
    assert evidence["execution_scope"]["dataset_mutation"] is False
    assert evidence["claims"]["safety_improvement_claim"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert manifest["artifact_policy"]["private_paths_omitted"] is True
    assert "readiness-only" in markdown
    assert "run-a100-current-train-split-sft-retry" in markdown
    assert scan_paths([output_dir]).ok is True


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _metrics_payload(
    *,
    exact: float,
    slot_f1: float,
    soft: float,
    route: float,
    safety_recall: float,
) -> dict[str, Any]:
    return {
        "metrics": {
            "contract_exact_match": exact,
            "json_valid_rate": 1.0,
            "slot_f1": slot_f1,
            "slot_f1_soft": soft,
            "task_type_accuracy": route,
            "route_accuracy": route,
            "safety_precision": 1.0,
            "safety_recall": safety_recall,
            "confirmation_accuracy": 1.0,
        },
        "failure_slices": {"slot": {"count": 1}, "safety": {"count": 1}},
    }


def _prediction_metadata(split: str, count: int = 69) -> dict[str, Any]:
    return {
        "dataset_manifest_id": _current_manifest()["manifest_id"],
        "prediction_split": split,
        "prediction_count": count,
        "prediction_status": "private_adapter_predictions_written",
        "adapter_path": "/mnt/data/minghongsun/private/adapter",
    }


def test_current_train_split_retry_cli_writes_training_retry_evidence_without_release_claims(
    tmp_path: Path,
    capsys: Any,
) -> None:
    output_dir = tmp_path / "retry-evidence"
    training_metadata = _write_json(
        tmp_path / "adapter_metadata.json",
        {
            "dataset_manifest_id": _current_manifest()["manifest_id"],
            "training_status": "training_completed",
            "training_rows_used": 118,
            "adapter_path": "/mnt/data/minghongsun/private/adapter",
            "base_model": "/mnt/data/minghongsun/models/qwen2.5-7b-instruct",
            "base_model_public_id": "Qwen/Qwen2.5-7B-Instruct",
        },
    )
    dev_metrics = _write_json(tmp_path / "dev" / "metrics.json", _metrics_payload(
        exact=0.50,
        slot_f1=0.60,
        soft=0.82,
        route=0.90,
        safety_recall=0.70,
    ))
    test_metrics = _write_json(tmp_path / "test" / "metrics.json", _metrics_payload(
        exact=0.40,
        slot_f1=0.55,
        soft=0.78,
        route=0.93,
        safety_recall=1.0,
    ))
    dev_metadata = _write_json(tmp_path / "dev" / "prediction_metadata.json", _prediction_metadata("dev"))
    test_metadata = _write_json(tmp_path / "test" / "prediction_metadata.json", _prediction_metadata("test"))

    assert (
        report_cli.main(
            [
                "current-train-split-sft-retry",
                "--training-metadata",
                training_metadata.as_posix(),
                "--public-manifest",
                PUBLIC_SAMPLE_MANIFEST.as_posix(),
                "--current-baseline-evidence",
                CURRENT_BASELINE_EVIDENCE.as_posix(),
                "--dev-metrics",
                dev_metrics.as_posix(),
                "--test-metrics",
                test_metrics.as_posix(),
                "--dev-prediction-metadata",
                dev_metadata.as_posix(),
                "--test-prediction-metadata",
                test_metadata.as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    evidence = read_json(output_dir / "current_train_split_sft_retry.json")
    manifest = read_json(output_dir / "manifest.json")
    markdown = (output_dir / "report.md").read_text(encoding="utf-8")
    serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True)

    assert payload["ok"] is True
    assert evidence["evidence_kind"] == "a100_current_train_split_sft_retry"
    assert evidence["run_status"] == "observed"
    assert evidence["dataset_manifest_id"] == _current_manifest()["manifest_id"]
    assert evidence["training_status"] == "training_completed"
    assert evidence["training_rows_used"] == 118
    assert evidence["execution_scope"]["training_run"] is True
    assert evidence["execution_scope"]["prediction_run"] is True
    assert evidence["execution_scope"]["dataset_mutation"] is False
    assert evidence["split_results"]["dev"]["prediction_count"] == 69
    assert evidence["split_results"]["dev"]["contract_exact_match"] == 0.50
    assert evidence["comparison_to_current_baseline"]["strict_exact_delta"]["dev"] > 0
    assert evidence["comparison_to_current_baseline"]["strict_exact_delta"]["test"] > 0
    assert evidence["comparison_to_current_baseline"]["direct_comparison_valid"] is True
    assert evidence["claims"]["training_performed"] is True
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert evidence["claims"]["checkpoint_release"] is False
    assert evidence["claims"]["production_readiness_claim"] is False
    assert evidence["claims"]["soft_slot_f1_primary_metric"] is False
    assert manifest["diagnostic_artifacts"]["evidence"].endswith("current_train_split_sft_retry.json")
    assert "training completed" in markdown.lower()
    assert "/mnt/data/" not in serialized
    assert scan_paths([output_dir]).ok is True


def test_committed_current_train_split_retry_readiness_evidence_is_current_and_non_claiming() -> None:
    evidence = read_json(READINESS_DIR / "current_train_split_sft_retry_readiness.json")
    manifest = read_json(READINESS_DIR / "manifest.json")
    dry_run = read_json(READINESS_DIR / "sft-dry-run" / "adapter_metadata.json")

    assert evidence["summary"]["dataset_manifest_id"] == _current_manifest()["manifest_id"]
    assert evidence["summary"]["training_rows_used"] == 118
    assert evidence["summary"]["blocked_payment_repair_train_rows"] == 4
    assert evidence["summary"]["form_fill_repair_train_rows"] == 21
    assert evidence["summary"]["readiness_status"] == "ready_for_bounded_a100_sft_retry_phase"
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["execution_scope"]["prediction_run"] is False
    assert evidence["claims"]["production_readiness_claim"] is False
    assert evidence["claims"]["private_corpus_generalization_claim"] is False
    assert evidence["claims"]["safety_improvement_claim"] is False
    assert dry_run["training_rows_used"] == 118
    assert dry_run["dataset_manifest_id"] == evidence["summary"]["dataset_manifest_id"]
    assert manifest["diagnostic_artifacts"]["dry_run_metadata"].endswith("sft-dry-run/adapter_metadata.json")
    assert scan_paths([READINESS_DIR, SFT_RETRY_CONFIG, DEV_PREDICTION_CONFIG, TEST_PREDICTION_CONFIG]).ok is True


def test_committed_current_train_split_retry_evidence_records_observed_partial_signal() -> None:
    evidence = read_json(RETRY_EVIDENCE_DIR / "current_train_split_sft_retry.json")
    manifest = read_json(RETRY_EVIDENCE_DIR / "manifest.json")
    preflight = read_json(RETRY_EVIDENCE_DIR / "a100_preflight_status.json")
    leak_scan = read_json(RETRY_EVIDENCE_DIR / "leak_scan_result.json")
    report = (RETRY_EVIDENCE_DIR / "report.md").read_text(encoding="utf-8")
    combined_public_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in RETRY_EVIDENCE_DIR.rglob("*")
        if path.is_file()
    )

    assert evidence["evidence_kind"] == "a100_current_train_split_sft_retry"
    assert evidence["run_status"] == "observed"
    assert evidence["dataset_manifest_id"] == _current_manifest()["manifest_id"]
    assert evidence["training_status"] == "training_completed"
    assert evidence["training_rows_used"] == 118
    assert evidence["overall_interpretation"] == "current_train_split_sft_retry_partial_signal"

    dev = evidence["split_results"]["dev"]
    test = evidence["split_results"]["test"]
    assert dev["prediction_count"] == 69
    assert test["prediction_count"] == 69
    assert dev["contract_exact_match"] == 0.43478260869565216
    assert dev["slot_f1"] == 0.5797101449275363
    assert dev["safety_recall"] == 1.0
    assert test["contract_exact_match"] == 0.4057971014492754
    assert test["slot_f1"] == 0.5386473429951691
    assert test["safety_recall"] == 1.0

    comparison = evidence["comparison_to_current_baseline"]
    assert comparison["direct_comparison_valid"] is True
    assert comparison["strict_exact_delta"]["dev"] < 0
    assert comparison["strict_exact_delta"]["test"] > 0
    assert comparison["strict_slot_f1_delta"]["dev"] > 0
    assert comparison["strict_slot_f1_delta"]["test"] > 0
    assert comparison["safety_recall_delta"]["dev"] > 0
    assert comparison["safety_recall_delta"]["test"] == 0.0

    assert evidence["execution_scope"]["training_run"] is True
    assert evidence["execution_scope"]["prediction_run"] is True
    assert evidence["execution_scope"]["dataset_mutation"] is False
    assert evidence["claims"]["training_performed"] is True
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert evidence["claims"]["checkpoint_release"] is False
    assert evidence["claims"]["production_readiness_claim"] is False
    assert evidence["claims"]["soft_slot_f1_primary_metric"] is False
    assert manifest["diagnostic_artifacts"]["evidence"].endswith("current_train_split_sft_retry.json")
    assert preflight["training_status"] == "training_completed"
    assert preflight["process_interruption"] is False
    assert leak_scan["ok"] is True
    assert "training completed" in report.lower()
    assert "minghongsun" not in combined_public_text
    assert "/mnt/data/" not in combined_public_text
    assert scan_paths([RETRY_EVIDENCE_DIR]).ok is True
