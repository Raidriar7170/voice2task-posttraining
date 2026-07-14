from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Any

import pytest

from voice2task import training
from voice2task.cli import train as train_cli

PUBLIC_RESULT_KEYS = {
    "schema_version",
    "stage",
    "training_status",
    "smoke_status",
    "blockers",
    "preflight",
    "observed_optimizer_steps",
    "training_rows_used",
    "training_budget",
    "train_result_metrics",
    "adapter_files",
    "clean_evaluation",
}


@pytest.mark.parametrize(
    "private_path",
    [
        "/home/alice/private/model",
        "/data/secret/output",
        "/workspace/company/config.json",
        "/opt/private/adapter",
        "/srv/custom-absolute/private-run",
    ],
)
def test_public_training_result_is_exact_allowlist_for_arbitrary_absolute_paths(private_path: str) -> None:
    metadata = {
        "schema_version": "voice2task-training-result-v1",
        "stage": "sft",
        "training_status": "training_completed",
        "smoke_status": "SMOKE_COMPLETED",
        "blockers": [],
        "preflight": {"ready": True, "status": "ready", "blockers": []},
        "observed_optimizer_steps": 1,
        "training_rows_used": 2,
        "training_budget": {"configured_max_steps": 1},
        "train_result_metrics": {"train_loss": 1.0},
        "adapter_files": [
            {"name": "adapter_model.safetensors", "size": 7, "sha256": "a" * 64, "path": private_path}
        ],
        "clean_evaluation": {"execution_readiness": False},
        "hyperparameters": {"base_model_runtime_path": private_path},
        "base_model_runtime_path": private_path,
        "output_root": private_path,
        "adapter_path": private_path,
        "metadata_path": private_path,
        "dataset_path": private_path,
        "output_paths": [private_path],
        "training_command": ["--output-dir", private_path],
        "command_summary": f"run --output-dir {private_path}",
        "private_config": {"path": private_path},
    }

    result = training.public_training_result(metadata)

    assert set(result) == PUBLIC_RESULT_KEYS
    assert result["adapter_files"] == [
        {"name": "adapter_model.safetensors", "size": 7, "sha256": "a" * 64}
    ]
    assert private_path not in json.dumps(result, sort_keys=True)


@pytest.mark.parametrize(
    "private_path",
    ["/home/a/private", "/data/private", "/workspace/private", "/opt/private", "/custom/private/root"],
)
def test_training_cli_stdout_uses_public_result_allowlist(
    monkeypatch: pytest.MonkeyPatch,
    capsys: Any,
    private_path: str,
) -> None:
    monkeypatch.setattr(
        train_cli,
        "run_sft",
        lambda *args, **kwargs: {
            "schema_version": "voice2task-training-result-v1",
            "stage": "sft",
            "training_status": "training_completed",
            "blockers": [],
            "adapter_files": [],
            "hyperparameters": {"output_root": private_path},
            "metadata_path": f"{private_path}/adapter_metadata.json",
        },
    )

    exit_code = train_cli.main(
        ["sft", "--config", "config.json", "--manifest", "manifest.json", "--output-dir", "run"]
    )

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 0
    assert set(result).issubset(PUBLIC_RESULT_KEYS)
    assert private_path not in captured.out
    assert captured.err == ""


def test_public_training_result_rebuilds_preflight_without_unknown_nested_private_fields() -> None:
    private_path = "/workspace/acme/secret-model"
    metadata = {
        "training_status": "training_blocked_by_preflight",
        "blockers": ["MODEL_PATH_UNRESOLVED"],
        "preflight": {
            "schema_version": "voice2task-sft-preflight-v1",
            "ready": False,
            "status": "blocked",
            "blockers": ["MODEL_PATH_UNRESOLVED"],
            "model": {
                "public_id": "Qwen/Qwen2.5-7B-Instruct",
                "local_files_only": True,
                "private_runtime_path": private_path,
                "unknown": {"deep_secret": private_path},
            },
            "unknown_section": {"path": private_path},
        },
    }
    result = training.public_training_result(metadata)

    assert private_path not in json.dumps(result, sort_keys=True)
    assert result["preflight"] == {
        "schema_version": "voice2task-sft-preflight-v1",
        "ready": False,
        "status": "blocked",
        "blockers": ["MODEL_PATH_UNRESOLVED"],
        "model": {
            "public_id": "Qwen/Qwen2.5-7B-Instruct",
            "local_files_only": True,
        },
    }


def test_public_training_result_rejects_private_paths_in_every_allowed_string_container() -> None:
    private_path = "/workspace/acme/secret-model"
    metadata = {
        "schema_version": private_path,
        "stage": private_path,
        "training_status": private_path,
        "smoke_status": private_path,
        "preflight": {
            "schema_version": private_path,
            "ready": False,
            "status": private_path,
            "blockers": [],
            "git": {"commit_sha": private_path},
            "config": {
                "config_sha256": private_path,
                "base_model_public_id": private_path,
                "dataset_split": private_path,
                "save_strategy": private_path,
            },
            "dataset": {
                "manifest_file": private_path,
                "manifest_sha256": private_path,
                "manifest_id": private_path,
                "sft_file": private_path,
                "sft_sha256": private_path,
                "selected_split": private_path,
                "selected_row_ids_sha256": private_path,
            },
            "model": {
                "public_id": private_path,
                "stable_fingerprints": {"config.json": private_path},
                "weight_inventory": [{"name": private_path, "size": 12}],
                "snapshot_revision_sha256": private_path,
            },
            "runtime": {
                "python": private_path,
                "python_requirement": private_path,
                "versions": {"torch": private_path},
                "pip_check": private_path,
            },
            "gpu": {
                "name": private_path,
                "compute_capability": private_path,
                "cuda_version": private_path,
            },
            "output": {
                "root_path_sha256": private_path,
                "output_path_sha256": private_path,
            },
        },
    }

    result = training.public_training_result(metadata)

    assert private_path not in json.dumps(result, sort_keys=True)


def test_output_policy_requires_existing_parent(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    result = training.validate_sft_output_policy(
        {"output_root": root.as_posix(), "min_free_disk_gib": 0},
        root / "missing-parent" / "run",
    )
    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_PARENT_MISSING"]


def test_output_claim_rejects_concurrent_final_leaf_creation(tmp_path: Path) -> None:
    root = tmp_path / "root"
    parent = root / "runs"
    parent.mkdir(parents=True)
    output = parent / "smoke"
    config = {"output_root": root.as_posix(), "min_free_disk_gib": 0}
    identities = training._bind_output_identities(root, parent)  # noqa: SLF001
    output.mkdir()

    with pytest.raises(training.SFTOutputPolicyError) as exc_info:
        training._claim_sft_output_directory(  # noqa: SLF001
            config,
            output,
            expected_identities=identities,
        )
    assert exc_info.value.blockers == ["OUTPUT_DIRECTORY_EXISTS"]


def test_output_claim_blocks_root_same_path_inode_exchange_without_external_mutation(tmp_path: Path) -> None:
    root = tmp_path / "root"
    parent = root / "runs"
    parent.mkdir(parents=True)
    output = parent / "smoke"
    config = {"output_root": root.as_posix(), "min_free_disk_gib": 0}
    identities = training._bind_output_identities(root, parent)  # noqa: SLF001
    old_root = tmp_path / "old-root"
    root.rename(old_root)
    root.mkdir()
    (root / "runs").mkdir()

    with pytest.raises(training.SFTOutputPolicyError) as exc_info:
        training._claim_sft_output_directory(config, output, expected_identities=identities)  # noqa: SLF001
    assert exc_info.value.blockers == ["OUTPUT_IDENTITY_CHANGED"]
    assert not output.exists()


def test_output_claim_blocks_parent_exchange_to_external_symlink_with_zero_external_mutation(tmp_path: Path) -> None:
    root = tmp_path / "root"
    parent = root / "runs"
    outside = tmp_path / "outside"
    parent.mkdir(parents=True)
    outside.mkdir()
    output = parent / "smoke"
    config = {"output_root": root.as_posix(), "min_free_disk_gib": 0}
    identities = training._bind_output_identities(root, parent)  # noqa: SLF001
    parent.rename(root / "old-runs")
    parent.symlink_to(outside, target_is_directory=True)

    with pytest.raises(training.SFTOutputPolicyError) as exc_info:
        training._claim_sft_output_directory(config, output, expected_identities=identities)  # noqa: SLF001
    assert exc_info.value.blockers == ["OUTPUT_IDENTITY_CHANGED"]
    assert list(outside.iterdir()) == []


def test_missing_parent_becoming_external_symlink_remains_blocked_with_zero_external_mutation(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    parent = root / "missing"
    output = parent / "smoke"
    config = {"output_root": root.as_posix(), "min_free_disk_gib": 0}
    assert training.validate_sft_output_policy(config, output)["blockers"] == ["OUTPUT_PARENT_MISSING"]
    parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(training.SFTOutputPolicyError):
        training._claim_sft_output_directory(config, output)  # noqa: SLF001
    assert list(outside.iterdir()) == []


def test_output_claim_blocks_existing_parent_inode_exchange(tmp_path: Path) -> None:
    root = tmp_path / "root"
    parent = root / "runs"
    parent.mkdir(parents=True)
    output = parent / "smoke"
    config = {"output_root": root.as_posix(), "min_free_disk_gib": 0}
    identities = training._bind_output_identities(root, parent)  # noqa: SLF001
    parent.rename(root / "old-runs")
    parent.mkdir()
    with pytest.raises(training.SFTOutputPolicyError) as exc_info:
        training._claim_sft_output_directory(config, output, expected_identities=identities)  # noqa: SLF001
    assert exc_info.value.blockers == ["OUTPUT_IDENTITY_CHANGED"]
    assert not output.exists()


def test_output_claim_checks_parent_path_identity_after_open_before_leaf_mkdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    parent = root / "runs"
    outside = tmp_path / "outside"
    parent.mkdir(parents=True)
    outside.mkdir()
    moved_parent = outside / "moved-runs"
    output = parent / "smoke"
    config = {"output_root": root.as_posix(), "min_free_disk_gib": 0}
    identities = training._bind_output_identities(root, parent)  # noqa: SLF001
    original_open = training._open_bound_output_parent  # noqa: SLF001

    def open_then_move(*args: Any, **kwargs: Any) -> tuple[int, int]:
        descriptors = original_open(*args, **kwargs)
        parent.rename(moved_parent)
        return descriptors

    monkeypatch.setattr(training, "_open_bound_output_parent", open_then_move)

    with pytest.raises(training.SFTOutputPolicyError) as exc_info:
        training._claim_sft_output_directory(  # noqa: SLF001
            config,
            output,
            expected_identities=identities,
        )
    assert exc_info.value.blockers == ["OUTPUT_IDENTITY_CHANGED"]
    assert not (moved_parent / "smoke").exists()


def test_gpu_probe_reports_free_memory_and_idle_aggregate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "3")
    monkeypatch.setattr(training, "_sample_sft_gpu_compute_process_count", lambda selector: 0)
    monkeypatch.setattr(
        training,
        "_run_sft_gpu_fact_helper",
        lambda selector: {
            "status": "OK",
            "cuda_available": True,
            "visible_device_count": 1,
            "name": "NVIDIA A100-SXM4-80GB",
            "compute_capability": "8.0",
            "total_memory_gib": 80.0,
            "free_memory_gib": 80.0,
            "cuda_version": "12.4",
            "bf16_supported": True,
        },
    )
    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001
    assert blockers == []
    assert facts["free_memory_gib"] == 80.0
    assert facts["minimum_free_memory_gib"] == 35.0
    assert facts["compute_process_count"] == 0
    assert facts["idle_verified"] is True
    serialized = json.dumps(facts)
    for forbidden in ("pid", "username", "uuid", "hostname", "command"):
        assert forbidden not in serialized.lower()


@pytest.mark.parametrize(
    ("free_gib", "process_count", "expected"),
    [
        (34.0, 0, "GPU_FREE_MEMORY_INSUFFICIENT"),
        (80.0, 1, "GPU_BUSY"),
    ],
)
def test_gpu_probe_blocks_insufficient_free_memory_or_busy_device(
    monkeypatch: pytest.MonkeyPatch,
    free_gib: float,
    process_count: int,
    expected: str,
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(training, "_sample_sft_gpu_compute_process_count", lambda selector: process_count)
    monkeypatch.setattr(
        training,
        "_run_sft_gpu_fact_helper",
        lambda selector: {
            "status": "OK",
            "cuda_available": True,
            "visible_device_count": 1,
            "name": "NVIDIA A100-SXM4-80GB",
            "compute_capability": "8.0",
            "total_memory_gib": 80.0,
            "free_memory_gib": free_gib,
            "cuda_version": "12.4",
            "bf16_supported": True,
        },
    )
    _, blockers = training._probe_sft_gpu()  # noqa: SLF001
    assert expected in blockers


def test_gpu_probe_fails_closed_when_occupancy_probe_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(
        training.subprocess,
        "run",
        lambda *args, **kwargs: types.SimpleNamespace(returncode=1, stdout="private pid 123", stderr="secret"),
    )
    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001
    assert blockers == ["GPU_OCCUPANCY_PROBE_FAILED"]
    assert facts["compute_process_count"] is None
    assert facts["idle_verified"] is False
    assert "123" not in json.dumps(facts)


def test_assistant_label_validator_rejects_single_prompt_token_leak() -> None:
    record = {
        "input_ids": [10, 11, 12, 13],
        "attention_mask": [1, 1, 1, 1],
        "labels": [-100, 11, 12, 13],
        "assistant_token_indices": [2, 3],
    }
    assert training._assistant_only_record_is_valid(record) is False  # noqa: SLF001


def test_adapter_state_evidence_requires_real_finite_change() -> None:
    torch = pytest.importorskip("torch")
    class TinyAdapter(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.adapter_weight = torch.nn.Parameter(torch.zeros(1, 2))

    model = TinyAdapter()
    before = training._capture_adapter_state(model)  # noqa: SLF001
    with torch.no_grad():
        model.adapter_weight.add_(1.0)
    after = training._capture_adapter_state(model)  # noqa: SLF001
    evidence = training._adapter_update_evidence(before, after)  # noqa: SLF001
    assert evidence["trainable_parameter_count"] == 2
    assert evidence["adapter_tensor_count"] == 1
    assert evidence["adapter_state_digest_before"] != evidence["adapter_state_digest_after"]
    assert evidence["changed_adapter_tensor_count"] == 1
    assert evidence["all_adapter_tensors_finite"] is True


def test_smoke_postconditions_require_adapter_update_evidence(tmp_path: Path) -> None:
    adapter = tmp_path / "run" / "adapter"
    adapter.mkdir(parents=True)
    (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
    (adapter / "adapter_model.safetensors").write_bytes(b"adapter")
    metadata = {
        "adapter_path": adapter.as_posix(),
        "metadata_path": (tmp_path / "run" / "adapter_metadata.json").as_posix(),
        "hyperparameters": {"max_train_rows": 1},
        "observed_optimizer_steps": 1,
        "training_rows_used": 1,
        "train_result_metrics": {"train_loss": 1.0},
    }
    blockers = training._sft_smoke_postconditions(metadata)  # noqa: SLF001
    assert "ADAPTER_UPDATE_NOT_OBSERVED" in blockers
    assert all("sha256" in item for item in metadata["adapter_files"])
