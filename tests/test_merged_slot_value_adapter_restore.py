import json
from pathlib import Path

import pytest

from voice2task.cli import report as report_cli
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_MANIFEST = REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json"
PRIOR_MERGED_MANIFEST = REPO_ROOT / "reports" / "public-sample" / "a100-merged-slot-value-heldout-eval" / "manifest.json"


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _training_metadata(private_root: str) -> dict:
    return {
        "adapter_path": f"{private_root}/runs/a100-merged-slot-value-heldout-eval/adapter",
        "dataset_manifest_id": "public-sample-20260615T040231Z",
        "training_status": "training_completed",
        "package_versions": {
            "datasets": "5.0.0",
            "peft": "0.18.1",
            "transformers": "5.5.0",
            "trl": "1.5.1",
        },
        "hyperparameters": {
            "base_model": f"{private_root}/models/qwen2.5-7b-instruct",
            "base_model_public_id": "Qwen/Qwen2.5-7B-Instruct",
            "dataset_split": "train",
            "allow_heavy_training": True,
            "adapter_output_dir": f"{private_root}/runs/a100-merged-slot-value-heldout-eval/adapter",
        },
    }


def test_merged_slot_value_adapter_restore_report_writes_regenerated_public_safe_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    private_root = "/mnt" + "/data/minghongsun/fine_tuning"
    training_metadata = _write_json(tmp_path / "training_metadata.raw.json", _training_metadata(private_root))
    output_dir = tmp_path / "adapter-restore"

    assert (
        report_cli.main(
            [
                "merged-slot-value-adapter-restore",
                "--public-manifest",
                PUBLIC_MANIFEST.as_posix(),
                "--prior-merged-manifest",
                PRIOR_MERGED_MANIFEST.as_posix(),
                "--restore-status",
                "available",
                "--acquisition-method",
                "regenerated",
                "--adapter-check",
                "adapter_config.json=present",
                "--adapter-check",
                "adapter_model.safetensors=present",
                "--training-metadata",
                training_metadata.as_posix(),
                "--dependency-status",
                "train_venv_available",
                "--gpu-status",
                "idle_gpu_selected",
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    evidence = read_json(output_dir / "merged_slot_value_adapter_restore.json")
    manifest = read_json(output_dir / "manifest.json")
    report = (output_dir / "report.md").read_text(encoding="utf-8")
    serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True)

    assert payload["ok"] is True
    assert payload["summary"]["restore_status"] == "available"
    assert evidence["evidence_kind"] == "a100_merged_slot_value_adapter_restore"
    assert evidence["restore_status"] == "available"
    assert evidence["acquisition_method"] == "regenerated"
    assert evidence["adapter_available"] is True
    assert "prior_merged_exact" not in evidence
    assert evidence["required_adapter_files"] == {
        "adapter_config.json": True,
        "adapter_model.safetensors": True,
    }
    assert evidence["claims"]["prediction_metrics_produced"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert evidence["claims"]["checkpoint_release"] is False
    assert evidence["claims"]["private_corpus_generalization_claim"] is False
    assert manifest["evidence_kind"] == "a100_merged_slot_value_adapter_restore"
    assert "prerequisite adapter evidence" in report
    assert "/mnt/data/" not in serialized
    assert scan_paths([output_dir]).ok is True


def test_merged_slot_value_adapter_restore_report_writes_restored_public_safe_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    private_root = "/mnt" + "/data/minghongsun/fine_tuning"
    training_metadata = _write_json(tmp_path / "training_metadata.raw.json", _training_metadata(private_root))
    output_dir = tmp_path / "restored-adapter-restore"

    assert (
        report_cli.main(
            [
                "merged-slot-value-adapter-restore",
                "--public-manifest",
                PUBLIC_MANIFEST.as_posix(),
                "--prior-merged-manifest",
                PRIOR_MERGED_MANIFEST.as_posix(),
                "--restore-status",
                "available",
                "--acquisition-method",
                "restored",
                "--adapter-check",
                "adapter_config.json=present",
                "--adapter-check",
                "adapter_model.safetensors=present",
                "--training-metadata",
                training_metadata.as_posix(),
                "--dependency-status",
                "existing_adapter_found",
                "--gpu-status",
                "not_used",
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    evidence = read_json(output_dir / "merged_slot_value_adapter_restore.json")

    assert payload["summary"]["acquisition_method"] == "restored"
    assert evidence["restore_status"] == "available"
    assert evidence["acquisition_method"] == "restored"
    assert evidence["adapter_available"] is True
    assert scan_paths([output_dir]).ok is True


def test_merged_slot_value_adapter_restore_report_writes_blocked_public_safe_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    output_dir = tmp_path / "blocked-adapter-restore"

    assert (
        report_cli.main(
            [
                "merged-slot-value-adapter-restore",
                "--public-manifest",
                PUBLIC_MANIFEST.as_posix(),
                "--prior-merged-manifest",
                PRIOR_MERGED_MANIFEST.as_posix(),
                "--restore-status",
                "blocked",
                "--acquisition-method",
                "not_available",
                "--blocked-reason",
                "training_dependency_missing",
                "--dependency-status",
                "missing_trl",
                "--gpu-status",
                "idle_gpu_selected",
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    evidence = read_json(output_dir / "merged_slot_value_adapter_restore.json")
    serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True)

    assert payload["ok"] is True
    assert payload["summary"]["restore_status"] == "blocked"
    assert evidence["restore_status"] == "blocked"
    assert evidence["blocked_reason"] == "training_dependency_missing"
    assert evidence["adapter_available"] is False
    assert evidence["required_adapter_files"] == {}
    assert evidence["claims"]["prediction_metrics_produced"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert "/mnt/data/" not in serialized
    assert scan_paths([output_dir]).ok is True


@pytest.mark.parametrize(
    ("restore_status", "acquisition_method", "message"),
    [
        ("available", "not_available", "available adapter restore requires restored or regenerated acquisition"),
        ("blocked", "regenerated", "blocked adapter restore requires not_available acquisition"),
        ("blocked", "restored", "blocked adapter restore requires not_available acquisition"),
    ],
)
def test_merged_slot_value_adapter_restore_report_rejects_inconsistent_status_and_acquisition(
    tmp_path: Path,
    restore_status: str,
    acquisition_method: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        report_cli.main(
            [
                "merged-slot-value-adapter-restore",
                "--public-manifest",
                PUBLIC_MANIFEST.as_posix(),
                "--prior-merged-manifest",
                PRIOR_MERGED_MANIFEST.as_posix(),
                "--restore-status",
                restore_status,
                "--acquisition-method",
                acquisition_method,
                "--blocked-reason",
                "training_dependency_missing",
                "--adapter-check",
                "adapter_config.json=present",
                "--adapter-check",
                "adapter_model.safetensors=present",
                "--output",
                (tmp_path / f"{restore_status}-{acquisition_method}").as_posix(),
            ]
        )


def test_merged_slot_value_adapter_restore_report_rejects_blocked_status_without_reason(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="blocked merged-slot-value-adapter-restore requires --blocked-reason"):
        report_cli.main(
            [
                "merged-slot-value-adapter-restore",
                "--public-manifest",
                PUBLIC_MANIFEST.as_posix(),
                "--prior-merged-manifest",
                PRIOR_MERGED_MANIFEST.as_posix(),
                "--restore-status",
                "blocked",
                "--acquisition-method",
                "not_available",
                "--output",
                (tmp_path / "blocked-adapter-restore").as_posix(),
            ]
        )
