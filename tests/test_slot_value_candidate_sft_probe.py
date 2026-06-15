import json
from pathlib import Path
from typing import Any

from voice2task.cli import report as report_cli
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.training import run_sft

REPO_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_MANIFEST = REPO_ROOT / "data" / "public-samples" / "manifest_slot_value_candidate_probe.json"
SFT_CONFIG = REPO_ROOT / "configs" / "sft-a100-slot-value-candidate-probe.json"
PREDICTION_CONFIG = REPO_ROOT / "configs" / "sft-a100-slot-value-candidate-probe-prediction.json"
FORMAL_PUBLIC_MANIFEST = REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json"
PROBE_DIR = REPO_ROOT / "reports" / "public-sample" / "slot-value-candidate-sft-probe"
MATERIALIZATION_MANIFEST = (
    REPO_ROOT / "reports" / "public-sample" / "slot-value-generalization-materialized-candidates" / "manifest.json"
)


def test_candidate_probe_manifest_and_configs_are_bounded_and_public_safe() -> None:
    manifest = read_json(CANDIDATE_MANIFEST)
    sft_config = read_json(SFT_CONFIG)
    prediction_config = read_json(PREDICTION_CONFIG)
    serialized = json.dumps(
        {"manifest": manifest, "sft": sft_config, "prediction": prediction_config},
        ensure_ascii=False,
        sort_keys=True,
    )

    assert manifest["mode"] == "slot_value_candidate_probe"
    assert manifest["files"]["sft"] == (
        "reports/public-sample/slot-value-generalization-materialized-candidates/sft_candidate_rows.jsonl"
    )
    assert manifest["counts"] == {
        "candidate_seed_rows": 4,
        "formal_public_sample_dpo_pairs": 90,
        "formal_public_sample_seed_rows": 10,
        "formal_public_sample_sft_rows": 30,
        "sft_rows": 12,
    }
    assert manifest["split_counts"] == {"dev": 0, "test": 0, "train": 12}
    assert manifest["formal_public_sample_modified"] is False
    assert manifest["claims"]["held_out_generalization_recovered"] is False

    assert sft_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert prediction_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert sft_config["candidate_sft_probe"] is True
    assert prediction_config["candidate_sft_probe"] is True
    assert sft_config["allow_heavy_training"] is True
    assert prediction_config["allow_private_prediction"] is True
    assert sft_config["dataset_manifest_id"] == manifest["manifest_id"]
    assert prediction_config["dataset_manifest_id"] == manifest["manifest_id"]
    assert sft_config["public_sample_manifest"] == "data/public-samples/manifest_slot_value_candidate_probe.json"
    assert prediction_config["public_sample_manifest"] == "data/public-samples/manifest_slot_value_candidate_probe.json"
    assert sft_config["max_train_rows"] == 12
    assert prediction_config["max_prediction_rows"] == 12
    assert sft_config["train_source_ids"] == [
        "candidate-blocked-payment-canonical-command",
        "candidate-clarify-ambiguous-canonical-scope",
        "candidate-form-email-canonical-field",
        "candidate-navigate-open-url-canonical-command",
    ]
    assert sft_config["generalization_claim"] is False
    assert prediction_config["generalization_claim"] is False
    assert "<a100_project_root>" in sft_config["output_root"]
    assert "<a100_project_root>" in prediction_config["output_root"]
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([CANDIDATE_MANIFEST, SFT_CONFIG, PREDICTION_CONFIG]).ok is True


def test_candidate_probe_sft_dry_run_selects_only_materialized_candidate_rows(tmp_path: Path) -> None:
    metadata = run_sft(SFT_CONFIG, CANDIDATE_MANIFEST, tmp_path / "candidate-sft-dry-run", dry_run=True)

    assert metadata["dry_run"] is True
    assert metadata["training_status"] == "dry_run"
    assert metadata["dataset_manifest_id"] == "slot-value-candidate-probe-20260615"
    assert metadata["training_split"] == "train"
    assert metadata["training_row_limit"] == 12
    assert metadata["training_rows_used"] == 12
    assert metadata["training_source_ids"] == [
        "candidate-blocked-payment-canonical-command",
        "candidate-clarify-ambiguous-canonical-scope",
        "candidate-form-email-canonical-field",
        "candidate-navigate-open-url-canonical-command",
    ]
    assert metadata["training_source_id_counts"] == {
        "candidate-blocked-payment-canonical-command": 3,
        "candidate-clarify-ambiguous-canonical-scope": 3,
        "candidate-form-email-canonical-field": 3,
        "candidate-navigate-open-url-canonical-command": 3,
    }
    assert all(row_id.startswith("candidate-") for row_id in metadata["training_row_ids"])
    assert metadata["heavy_training_gate"]["will_run_heavy_training"] is False
    assert read_json(FORMAL_PUBLIC_MANIFEST)["counts"] == {"dpo_pairs": 90, "seed_rows": 10, "sft_rows": 30}
    assert Path(metadata["metadata_path"]).exists()


def test_candidate_probe_report_cli_writes_blocked_a100_evidence(
    tmp_path: Path,
    capsys: Any,
) -> None:
    dry_run_dir = tmp_path / "candidate-sft-dry-run"
    metadata = run_sft(SFT_CONFIG, CANDIDATE_MANIFEST, dry_run_dir, dry_run=True)
    dry_run_metadata = Path(metadata["metadata_path"])
    output_dir = tmp_path / "candidate-probe-report"

    assert (
        report_cli.main(
            [
                "slot-value-candidate-sft-probe",
                "--dry-run-metadata",
                dry_run_metadata.as_posix(),
                "--candidate-manifest",
                CANDIDATE_MANIFEST.as_posix(),
                "--materialization-manifest",
                MATERIALIZATION_MANIFEST.as_posix(),
                "--sft-config",
                SFT_CONFIG.as_posix(),
                "--prediction-config",
                PREDICTION_CONFIG.as_posix(),
                "--a100-ssh-status",
                "ok",
                "--a100-output-root-status",
                "ok",
                "--a100-idle-gpu-status",
                "idle_gpu_available",
                "--a100-selected-gpu-index",
                "3",
                "--a100-train-dependencies",
                "torch,transformers,peft,accelerate",
                "--a100-missing-dependencies",
                "trl,datasets",
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    evidence = read_json(output_dir / "slot_value_candidate_sft_probe.json")
    manifest = read_json(output_dir / "manifest.json")
    markdown = (output_dir / "slot_value_candidate_sft_probe.md").read_text(encoding="utf-8")

    assert evidence["evidence_kind"] == "slot_value_candidate_sft_probe"
    assert evidence["summary"]["candidate_sft_rows"] == 12
    assert evidence["summary"]["selected_candidate_training_rows"] == 12
    assert evidence["summary"]["a100_training_status"] == "blocked_missing_train_dependencies"
    assert evidence["a100_preflight"]["safe_to_launch_training"] is False
    assert evidence["a100_preflight"]["missing_train_dependencies"] == ["trl", "datasets"]
    assert evidence["execution_scope"]["formal_public_sample_modified"] is False
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert "blocked_missing_train_dependencies" in markdown
    assert "candidate-only dry-run evidence" in markdown
    assert scan_paths([output_dir]).ok is True


def test_committed_candidate_probe_evidence_is_public_safe_and_non_claiming() -> None:
    evidence = read_json(PROBE_DIR / "slot_value_candidate_sft_probe.json")
    manifest = read_json(PROBE_DIR / "manifest.json")
    dry_run = read_json(PROBE_DIR / "sft-dry-run" / "adapter_metadata.json")

    assert evidence["summary"]["candidate_sft_rows"] == 12
    assert evidence["summary"]["selected_candidate_training_rows"] == 12
    assert evidence["summary"]["formal_public_sample_modified"] is False
    assert evidence["summary"]["a100_training_status"] == "blocked_missing_train_dependencies"
    assert evidence["execution_scope"]["training_run"] is False
    assert evidence["execution_scope"]["prediction_run"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert dry_run["training_rows_used"] == 12
    assert manifest["diagnostic_artifacts"]["dry_run_metadata"].endswith("sft-dry-run/adapter_metadata.json")
    assert read_json(FORMAL_PUBLIC_MANIFEST)["counts"] == {"dpo_pairs": 90, "seed_rows": 10, "sft_rows": 30}
    assert scan_paths([PROBE_DIR, CANDIDATE_MANIFEST, SFT_CONFIG, PREDICTION_CONFIG]).ok is True
