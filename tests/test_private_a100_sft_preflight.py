from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from voice2task import training
from voice2task.cli import train as train_cli


def _policy(config: dict[str, Any], output_dir: Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    return training.validate_sft_output_policy(config, output_dir, repo_root=repo_root)


def test_output_policy_requires_output_root(tmp_path: Path) -> None:
    result = _policy({}, tmp_path / "run")

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_ROOT_MISSING"]


def test_output_policy_rejects_relative_output_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path("root").mkdir()

    result = _policy({"output_root": "root"}, (tmp_path / "root" / "run"))

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_ROOT_NOT_ABSOLUTE"]


def test_output_policy_rejects_relative_output_dir(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    result = _policy({"output_root": root.as_posix()}, Path("run"))

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_DIR_NOT_ABSOLUTE"]


def test_output_policy_rejects_output_dir_equal_to_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    result = _policy({"output_root": root.as_posix()}, root)

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_PATH_OUTSIDE_ROOT"]


def test_output_policy_rejects_dotdot_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    result = _policy({"output_root": root.as_posix()}, root / ".." / "outside")

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_PATH_OUTSIDE_ROOT"]


def test_output_policy_rejects_parent_symlink_to_outside(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)

    result = _policy({"output_root": root.as_posix()}, root / "linked" / "run")

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_PATH_SYMLINK", "OUTPUT_PATH_OUTSIDE_ROOT"]


def test_output_policy_rejects_final_output_dir_symlink(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = root / "target"
    root.mkdir()
    target.mkdir()
    output_dir = root / "run"
    output_dir.symlink_to(target, target_is_directory=True)

    result = _policy({"output_root": root.as_posix()}, output_dir)

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_PATH_SYMLINK"]


def test_output_policy_rejects_nonempty_existing_output_dir(tmp_path: Path) -> None:
    root = tmp_path / "root"
    output_dir = root / "run"
    output_dir.mkdir(parents=True)
    (output_dir / "adapter_model.safetensors").write_bytes(b"existing")

    result = _policy({"output_root": root.as_posix()}, output_dir)

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_DIRECTORY_NOT_EMPTY"]


def test_output_policy_rejects_existing_empty_output_dir(tmp_path: Path) -> None:
    root = tmp_path / "root"
    output_dir = root / "run"
    output_dir.mkdir(parents=True)

    result = _policy({"output_root": root.as_posix(), "min_free_disk_gib": 0}, output_dir)

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_DIRECTORY_EXISTS"]


def test_output_policy_accepts_new_absolute_child_without_creating_it(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "runs").mkdir()
    output_dir = root / "runs" / "smoke"

    result = _policy({"output_root": root.as_posix(), "min_free_disk_gib": 0}, output_dir)

    assert result["ready"] is True
    assert result["blockers"] == []
    assert result["root_path_sha256"] == training._sha256_text(root.resolve().as_posix())  # noqa: SLF001
    assert result["output_path_sha256"] == training._sha256_text(output_dir.resolve().as_posix())  # noqa: SLF001
    assert not output_dir.exists()
    serialized = json.dumps(result, sort_keys=True)
    assert root.as_posix() not in serialized
    assert output_dir.as_posix() not in serialized


def test_output_policy_checks_nearest_existing_parent_writability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    nearest_parent = root / "runs"
    nearest_parent.mkdir(parents=True)
    output_dir = nearest_parent / "smoke"
    checked_paths: list[Path] = []

    def fake_access(path: Path, mode: int) -> bool:
        assert mode == training.os.W_OK
        checked_paths.append(Path(path))
        return Path(path) != nearest_parent

    monkeypatch.setattr(training.os, "access", fake_access)

    result = _policy({"output_root": root.as_posix(), "min_free_disk_gib": 0}, output_dir)

    assert result["ready"] is False
    assert "OUTPUT_NOT_WRITABLE" in result["blockers"]
    assert nearest_parent in checked_paths


@pytest.mark.parametrize(
    ("probe", "expected_blocker"),
    [
        ("access", "OUTPUT_FILESYSTEM_UNAVAILABLE"),
        ("disk", "OUTPUT_DISK_CHECK_FAILED"),
    ],
)
def test_output_policy_converts_probe_errors_to_private_safe_blockers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    expected_blocker: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    private_detail = "/private/model/secret-token"
    if probe == "access":
        monkeypatch.setattr(training.os, "access", lambda *args: (_ for _ in ()).throw(OSError(private_detail)))
    else:
        monkeypatch.setattr(
            training.shutil,
            "disk_usage",
            lambda *args: (_ for _ in ()).throw(OSError(private_detail)),
        )

    result = _policy(
        {"output_root": root.as_posix(), "min_free_disk_gib": 20},
        root / "smoke",
    )

    assert result["ready"] is False
    assert expected_blocker in result["blockers"]
    assert private_detail not in json.dumps(result, sort_keys=True)


def test_output_policy_converts_path_resolution_error_to_private_safe_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    original_resolve = Path.resolve
    private_detail = "/private/model/secret-token"

    def selective_resolve(path: Path, *args: Any, **kwargs: Any) -> Path:
        if path == root:
            raise OSError(private_detail)
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", selective_resolve)

    result = _policy({"output_root": root.as_posix()}, root / "smoke")

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_FILESYSTEM_UNAVAILABLE"]
    assert private_detail not in json.dumps(result, sort_keys=True)


def test_output_policy_rejects_repository_location(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "runs").mkdir()
    output_dir = repo_root / "runs" / "smoke"

    result = _policy(
        {"output_root": repo_root.as_posix(), "min_free_disk_gib": 0},
        output_dir,
        repo_root=repo_root,
    )

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_PATH_GIT_TRACKED"]


def test_output_claim_fails_closed_if_candidate_appears_after_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    output_dir = root / "smoke"
    original_mkdir = training.os.mkdir

    def racing_mkdir(path: Any, *args: Any, **kwargs: Any) -> None:
        if path == output_dir.name and kwargs.get("dir_fd") is not None:
            original_mkdir(path, *args, **kwargs)
            raise FileExistsError(path)
        original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(training.os, "mkdir", racing_mkdir)

    with pytest.raises(training.SFTOutputPolicyError) as exc_info:
        training._claim_sft_output_directory(  # noqa: SLF001
            {"output_root": root.as_posix(), "min_free_disk_gib": 0},
            output_dir,
        )

    assert exc_info.value.blockers == ["OUTPUT_DIRECTORY_EXISTS"]


def test_output_policy_rejects_symlink_output_root(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    root = tmp_path / "root"
    root.symlink_to(target, target_is_directory=True)

    result = _policy({"output_root": root.as_posix()}, root / "run")

    assert result["ready"] is False
    assert result["blockers"] == ["OUTPUT_ROOT_SYMLINK"]


def test_dpo_run_training_checks_output_policy_before_metadata_or_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    config = tmp_path / "dpo.json"
    config.write_text(
        json.dumps({"allow_heavy_training": True, "output_root": root.as_posix()}),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    repo_root = tmp_path / "checkout"
    repo_root.mkdir()
    monkeypatch.setattr(training, "_git_repository_root_for_manifest", lambda path: repo_root)
    output_dir = tmp_path / "outside" / "dpo"
    monkeypatch.setattr(
        training,
        "_metadata_common",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("metadata path must not run before output gate")),
    )
    monkeypatch.setattr(
        training,
        "_train_dependencies_available",
        lambda: (_ for _ in ()).throw(AssertionError("dependency probe must not run before output gate")),
    )

    result = training.run_dpo(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_blocked_by_output_policy"
    assert result["blockers"] == ["OUTPUT_PATH_OUTSIDE_ROOT"]
    assert not output_dir.exists()


def test_real_dpo_rechecks_output_policy_before_import_or_model_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    output_dir = tmp_path / "outside" / "dpo"
    imports: list[str] = []

    class FailModule(types.ModuleType):
        def __getattr__(self, name: str) -> Any:
            imports.append(f"{self.__name__}.{name}")
            raise AssertionError("training dependency must not import before the output gate")

    for module_name in ("datasets", "peft", "transformers", "trl"):
        monkeypatch.setitem(sys.modules, module_name, FailModule(module_name))

    with pytest.raises(training.SFTOutputPolicyError) as exc_info:
        training._run_real_dpo(  # noqa: SLF001
            {"adapter_path": (output_dir / "adapter").as_posix()},
            {"output_root": root.as_posix(), "min_free_disk_gib": 0},
            tmp_path / "manifest.json",
            output_dir,
            repo_root=tmp_path / "checkout",
        )

    assert exc_info.value.blockers == ["OUTPUT_PATH_OUTSIDE_ROOT"]
    assert imports == []
    assert not output_dir.exists()


def test_dpo_real_mode_derives_repo_from_manifest_when_process_cwd_is_unrelated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "checkout"
    manifest = repo_root / "data" / "public-samples" / "manifest_public_sample.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"manifest_id":"test"}\n', encoding="utf-8")
    output_root = tmp_path / "private-output"
    output_root.mkdir()
    output_dir = output_root / "dpo-smoke"
    config = repo_root / "dpo.json"
    config.write_text(
        json.dumps({"allow_heavy_training": True, "output_root": output_root.as_posix()}),
        encoding="utf-8",
    )
    unrelated = tmp_path / "unrelated-cwd"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    git_commands: list[list[str]] = []

    def fake_git(command: list[str], **kwargs: Any) -> Any:
        git_commands.append(command)
        assert command == ["git", "-C", manifest.parent.as_posix(), "rev-parse", "--show-toplevel"]
        return types.SimpleNamespace(returncode=0, stdout=repo_root.as_posix() + "\n")

    monkeypatch.setattr(training.subprocess, "run", fake_git)
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    received_roots: list[Path] = []

    def run_real(
        metadata: dict[str, Any],
        config_snapshot: dict[str, Any],
        manifest_path: Path,
        run_output_dir: Path,
        *,
        repo_root: Path,
    ) -> None:
        received_roots.append(repo_root)

    monkeypatch.setattr(training, "_run_real_dpo", run_real)

    result = training.run_dpo(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_completed"
    assert git_commands
    assert received_roots == [repo_root]


def test_dpo_real_mode_fails_closed_without_manifest_checkout_before_any_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "dpo.json"
    config.write_text("{}\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    output_dir = tmp_path / "output" / "dpo"
    monkeypatch.setattr(training, "_git_repository_root_for_manifest", lambda path: None)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("repo-root failure must precede config, metadata, dependencies, and runner")

    monkeypatch.setattr(training, "_load_config", forbidden)
    monkeypatch.setattr(training, "_metadata_common", forbidden)
    monkeypatch.setattr(training, "_train_dependencies_available", forbidden)
    monkeypatch.setattr(training, "_run_real_dpo", forbidden)

    result = training.run_dpo(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_blocked_by_output_policy"
    assert result["blockers"] == ["OUTPUT_REPOSITORY_UNAVAILABLE"]
    assert not output_dir.exists()


def _write_preflight_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    output_root = tmp_path.parent / f"{tmp_path.name}-private-output"
    output_root.mkdir()
    model_root = tmp_path / "private-model"
    model_root.mkdir()
    (model_root / "config.json").write_text('{"model_type":"qwen2"}\n', encoding="utf-8")
    (model_root / "tokenizer_config.json").write_text("{}\n", encoding="utf-8")
    (model_root / "model.safetensors.index.json").write_text("{}\n", encoding="utf-8")
    (model_root / "model-00001-of-00001.safetensors").write_bytes(b"weights")

    public_dir = tmp_path / "data" / "public-samples"
    public_dir.mkdir(parents=True)
    rows_path = public_dir / "sft_public_sample.jsonl"
    rows = [
        {
            "id": f"sft-{index}",
            "split": "train",
            "input_text": f"搜索天气 {index}",
            "target_contract": {
                "task_type": "search",
                "route": "search_web",
                "safety": {"allow": True, "reason": "public_readonly"},
                "confirmation_required": False,
                "slots": {"query": f"天气 {index}"},
                "normalized_command": f"搜索天气 {index}",
                "language": "zh-CN",
                "contract_version": "v1",
            },
            "provenance": {"source_id": f"seed-{index}", "public_safe": True},
        }
        for index in (1, 2)
    ]
    rows_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    manifest = public_dir / "manifest_public_sample.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_id": "public-sample-20260619T090925Z",
                "public_safe": True,
                "files": {"sft": "data/public-samples/sft_public_sample.jsonl"},
                "split_counts": {"train": 2, "dev": 0, "test": 0},
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "data" / "local-private" / "runtime" / "sft-a100-smoke.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "base_model_public_id": "Qwen/Qwen2.5-7B-Instruct",
                "base_model_runtime_path": model_root.as_posix(),
                "allow_heavy_training": True,
                "local_files_only": True,
                "trust_remote_code": False,
                "dtype": "bfloat16",
                "torch_dtype": "bfloat16",
                "dataset_split": "train",
                "dataset_manifest_id": "public-sample-20260619T090925Z",
                "max_train_rows": 2,
                "max_steps": 1,
                "per_device_train_batch_size": 1,
                "gradient_accumulation_steps": 1,
                "max_seq_length": 1024,
                "bf16": True,
                "fp16": False,
                "tf32": True,
                "gradient_checkpointing": True,
                "use_cache": False,
                "low_cpu_mem_usage": True,
                "save_strategy": "no",
                "logging_steps": 1,
                "seed": 42,
                "report_to": [],
                "output_root": output_root.as_posix(),
                "min_free_disk_gib": 20,
                "lora": {
                    "r": 8,
                    "alpha": 16,
                    "dropout": 0.05,
                    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
                },
            }
        ),
        encoding="utf-8",
    )
    return config, manifest, output_root / "sft-smoke-test"


def _install_ready_preflight_probes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        training,
        "_probe_private_sft_config",
        lambda config_path, repo_root: (
            {"under_private_runtime": True, "git_ignored": True, "git_tracked": False},
            [],
        ),
        raising=False,
    )
    monkeypatch.setattr(
        training,
        "_probe_sft_git",
        lambda repo_root: ({"commit_sha": "a" * 40, "tracked_worktree_clean": True}, []),
        raising=False,
    )
    monkeypatch.setattr(
        training,
        "_probe_sft_dependencies",
        lambda: (
            {
                "python": "3.12.0",
                "versions": {
                    name: "test" for name in ("torch", "accelerate", "datasets", "peft", "transformers", "trl")
                },
                "pip_check": "ok",
            },
            [],
        ),
        raising=False,
    )
    monkeypatch.setattr(
        training,
        "_probe_sft_gpu",
        lambda: (
            {
                "explicit_selection": True,
                "visible_device_count": 1,
                "name": "NVIDIA A100-SXM4-80GB",
                "compute_capability": "8.0",
                "total_memory_gib": 79.15,
                "cuda_version": "12.4",
                "bf16_supported": True,
            },
            [],
        ),
        raising=False,
    )
    def ready_model_probe(
        config: dict[str, Any],
        rows: list[Any],
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        model_root = Path(config["base_model_runtime_path"])
        fingerprints, inventory = training._stable_local_model_inventory(model_root)  # noqa: SLF001
        return (
            {
                "public_id": "Qwen/Qwen2.5-7B-Instruct",
                "local_files_only": True,
                "stable_fingerprints": fingerprints,
                "weight_inventory": inventory,
            },
            {
                "records_checked": len(rows),
                "prompt_labels_masked": True,
                "assistant_target_present": True,
                "max_sequence_length": 1024,
            },
            [],
        )

    monkeypatch.setattr(training, "_probe_sft_model_and_objective", ready_model_probe, raising=False)


def test_sft_preflight_ready_schema_is_complete_and_private_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["schema_version"] == "voice2task-sft-preflight-v1"
    assert result["ready"] is True
    assert result["status"] == "ready"
    assert result["blockers"] == []
    assert set(result) >= {
        "git",
        "config",
        "dataset",
        "model",
        "runtime",
        "gpu",
        "output",
        "objective",
    }
    assert result["dataset"]["selected_row_count"] == 2
    assert len(result["dataset"]["manifest_sha256"]) == 64
    assert len(result["dataset"]["sft_sha256"]) == 64
    assert len(result["dataset"]["selected_row_ids_sha256"]) == 64
    serialized = json.dumps(result, sort_keys=True)
    assert tmp_path.as_posix() not in serialized
    assert "private-model" not in serialized
    assert "private-output" not in serialized


@pytest.mark.parametrize("entrypoint", ["preflight", "real_sft"])
def test_shared_sft_preflight_wrapper_converts_unexpected_exception_to_private_safe_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)

    def broken_dependency_probe() -> tuple[dict[str, Any], list[str]]:
        raise RuntimeError("/private/secret-dependency-probe")

    monkeypatch.setattr(training, "_probe_sft_dependencies", broken_dependency_probe)

    if entrypoint == "preflight":
        result = training.run_sft_preflight(config, manifest, output_dir)
        preflight = result
    else:
        result = training.run_sft(config, manifest, output_dir, dry_run=False)
        assert result["training_status"] == "training_blocked_by_preflight"
        assert result["blockers"] == ["PREFLIGHT_INTERNAL_ERROR"]
        preflight = result["preflight"]

    assert preflight == {
        "schema_version": "voice2task-sft-preflight-v1",
        "ready": False,
        "status": "blocked",
        "blockers": ["PREFLIGHT_INTERNAL_ERROR"],
        "git": {},
        "config": {},
        "dataset": {},
        "model": {},
        "runtime": {},
        "gpu": {},
        "output": {},
        "objective": {},
    }
    serialized = json.dumps(result, sort_keys=True)
    assert "/private/secret-dependency-probe" not in serialized
    assert tmp_path.as_posix() not in serialized
    assert not output_dir.exists()


@pytest.mark.parametrize(
    ("case", "expected_blocker"),
    [
        ("outside", "CONFIG_PATH_NOT_PRIVATE"),
        ("symlink", "CONFIG_PATH_SYMLINK"),
        ("not_ignored", "CONFIG_FILE_NOT_IGNORED"),
        ("tracked", "CONFIG_FILE_TRACKED"),
    ],
)
def test_private_config_policy_fails_closed_for_each_bypass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    expected_blocker: str,
) -> None:
    config_path, manifest, _ = _write_preflight_fixture(tmp_path)
    repo_root = manifest.parents[2]
    candidate = config_path
    if case == "outside":
        candidate = tmp_path.parent / f"{tmp_path.name}-outside-config.json"
        candidate.write_bytes(config_path.read_bytes())
    elif case == "symlink":
        target = tmp_path.parent / f"{tmp_path.name}-config-target.json"
        target.write_bytes(config_path.read_bytes())
        config_path.unlink()
        config_path.symlink_to(target)

    if case == "not_ignored":
        git_state = (False, False, True)
    elif case == "tracked":
        git_state = (True, True, True)
    else:
        git_state = (True, False, True)
    monkeypatch.setattr(
        training,
        "_git_config_path_state",
        lambda *args: git_state,
        raising=False,
    )

    _, blockers = training._probe_private_sft_config(candidate, repo_root)  # noqa: SLF001

    assert blockers == [expected_blocker]


@pytest.mark.parametrize(
    ("mutations", "blocker"),
    [
        ({"allow_heavy_training": False}, "CONFIG_HEAVY_TRAINING_NOT_ALLOWED"),
        ({"dataset_split": "dev"}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_train_rows": 3}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_train_rows": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_train_rows": 1.0}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_steps": 2}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_steps": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_steps": 1.0}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"per_device_train_batch_size": 2}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"per_device_train_batch_size": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"per_device_train_batch_size": 1.0}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"gradient_accumulation_steps": 2}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"gradient_accumulation_steps": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"gradient_accumulation_steps": 1.0}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_seq_length": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_seq_length": 0}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_seq_length": 4097}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_seq_length": 1024.0}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"max_seq_length": "/private/secret-sequence-policy"}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"seed": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"seed": 42.0}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"logging_steps": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"logging_steps": 1.0}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"logging_steps": 0}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"save_strategy": "steps"}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"report_to": ["wandb"]}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"base_model_public_id": "Qwen/Qwen2.5-0.5B-Instruct"}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"local_files_only": False}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"bf16": False}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"fp16": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"tf32": False}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"gradient_checkpointing": False}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"use_cache": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"trust_remote_code": True}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"dtype": "float16"}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"torch_dtype": "float16"}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"min_free_disk_gib": 19}, "CONFIG_NOT_SMOKE_BOUNDED"),
        ({"lora": {"r": 0, "alpha": 16, "dropout": 0.05, "target_modules": ["q_proj"]}}, "CONFIG_NOT_SMOKE_BOUNDED"),
        (
            {
                "lora": {
                    "r": 8,
                    "alpha": 16,
                    "dropout": 0.05,
                    "target_modules": ["lm_head"],
                }
            },
            "CONFIG_NOT_SMOKE_BOUNDED",
        ),
    ],
)
def test_sft_preflight_blocks_non_smoke_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutations: dict[str, Any],
    blocker: str,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload.update(mutations)
    config.write_text(json.dumps(payload), encoding="utf-8")
    _install_ready_preflight_probes(monkeypatch)

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert blocker in result["blockers"]
    assert "/private/secret-sequence-policy" not in json.dumps(result, sort_keys=True)


@pytest.mark.parametrize("invalid_row_limit", [True, 1.0])
def test_sft_preflight_does_not_select_rows_for_non_integer_max_train_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_row_limit: Any,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["max_train_rows"] = invalid_row_limit
    config.write_text(json.dumps(payload), encoding="utf-8")
    _install_ready_preflight_probes(monkeypatch)

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert "CONFIG_NOT_SMOKE_BOUNDED" in result["blockers"]
    assert "TRAIN_ROW_SELECTION_INVALID" in result["blockers"]
    assert result["dataset"]["selected_row_count"] == 0


def test_sft_preflight_public_config_facts_never_echo_unapproved_private_strings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload.update(
        {
            "base_model_public_id": "/private/secret-model-identity",
            "dataset_split": "/private/secret-split",
            "save_strategy": "/private/secret-save-strategy",
        }
    )
    config.write_text(json.dumps(payload), encoding="utf-8")
    _install_ready_preflight_probes(monkeypatch)

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert "CONFIG_NOT_SMOKE_BOUNDED" in result["blockers"]
    serialized = json.dumps(result, sort_keys=True)
    assert "/private/secret" not in serialized
    assert result["config"]["base_model_public_id"] is None
    assert result["config"]["dataset_split"] is None
    assert result["config"]["save_strategy"] is None


@pytest.mark.parametrize("missing", ["torch", "accelerate"])
def test_sft_preflight_blocks_missing_torch_or_accelerate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    monkeypatch.setattr(
        training,
        "_probe_sft_dependencies",
        lambda: ({"missing": [missing], "versions": {}}, ["DEPENDENCY_MISSING"]),
    )

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert result["blockers"] == ["DEPENDENCY_MISSING"]


def test_git_probe_uses_bound_repo_and_sanitizes_subprocess_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Path] = []

    def broken_git(*args: Any, **kwargs: Any) -> None:
        calls.append(Path(kwargs["cwd"]))
        raise OSError("private git transport detail")

    monkeypatch.setattr(training.subprocess, "run", broken_git)

    facts, blockers = training._probe_sft_git(tmp_path)  # noqa: SLF001

    assert calls == [tmp_path]
    assert facts == {"commit_sha": None, "tracked_worktree_clean": False}
    assert blockers == ["GIT_PROBE_FAILED"]


@pytest.mark.parametrize(
    "blocker",
    [
        "CUDA_UNAVAILABLE",
        "BF16_UNSUPPORTED",
        "GPU_MEMORY_INSUFFICIENT",
        "GPU_SELECTION_NOT_EXPLICIT",
    ],
)
def test_sft_preflight_blocks_invalid_gpu_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    blocker: str,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    monkeypatch.setattr(training, "_probe_sft_gpu", lambda: ({"available": False}, [blocker]))

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert result["blockers"] == [blocker]


def test_gpu_probe_rejects_non_a100_even_when_other_cuda_facts_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")

    class FakeCuda:
        @staticmethod
        def is_available() -> bool:
            return True

        @staticmethod
        def device_count() -> int:
            return 1

        @staticmethod
        def get_device_properties(index: int) -> Any:
            assert index == 0
            return types.SimpleNamespace(total_memory=80 * 1024**3)

        @staticmethod
        def get_device_capability(index: int) -> tuple[int, int]:
            assert index == 0
            return (8, 9)

        @staticmethod
        def is_bf16_supported() -> bool:
            return True

        @staticmethod
        def get_device_name(index: int) -> str:
            assert index == 0
            return "NVIDIA GeForce RTX 4090"

        @staticmethod
        def mem_get_info(index: int) -> tuple[int, int]:
            assert index == 0
            return (80 * 1024**3, 80 * 1024**3)

    monkeypatch.setitem(
        sys.modules,
        "torch",
        types.SimpleNamespace(cuda=FakeCuda(), version=types.SimpleNamespace(cuda="12.4")),
    )
    monkeypatch.setattr(
        training.subprocess,
        "run",
        lambda *args, **kwargs: types.SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001

    assert facts["name"] == "NVIDIA GeForce RTX 4090"
    assert blockers == ["GPU_NOT_A100"]


def test_gpu_probe_converts_cuda_api_exception_to_stable_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")

    class BrokenCuda:
        @staticmethod
        def is_available() -> bool:
            return True

        @staticmethod
        def device_count() -> int:
            raise RuntimeError("private CUDA driver detail")

    monkeypatch.setitem(
        sys.modules,
        "torch",
        types.SimpleNamespace(cuda=BrokenCuda(), version=types.SimpleNamespace(cuda="12.4")),
    )

    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001

    assert facts["visible_device_count"] == 0
    assert blockers == ["CUDA_PROBE_FAILED"]


def test_sft_preflight_blocks_missing_private_model_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["base_model_runtime_path"] = (tmp_path / "missing-model").as_posix()
    config.write_text(json.dumps(payload), encoding="utf-8")
    _install_ready_preflight_probes(monkeypatch)

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert "MODEL_PATH_UNRESOLVED" in result["blockers"]
    assert "missing-model" not in json.dumps(result)


def test_sft_preflight_blocks_manifest_id_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["dataset_manifest_id"] = "different-id"
    config.write_text(json.dumps(payload), encoding="utf-8")
    _install_ready_preflight_probes(monkeypatch)

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert "DATASET_HASH_OR_ID_MISMATCH" in result["blockers"]


def test_sft_preflight_rejects_noncanonical_manifest_before_dataset_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, canonical_manifest, output_dir = _write_preflight_fixture(tmp_path)
    alternate_manifest = tmp_path / "manifest_public_sample.json"
    alternate_manifest.write_bytes(canonical_manifest.read_bytes())
    _install_ready_preflight_probes(monkeypatch)

    def forbidden_dataset_read(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("noncanonical manifest must be rejected before SFT access")

    monkeypatch.setattr(training, "_load_selected_smoke_rows", forbidden_dataset_read)

    result = training.run_sft_preflight(config, alternate_manifest, output_dir)

    assert result["ready"] is False
    assert result["blockers"] == ["MANIFEST_PATH_NOT_CANONICAL"]


def test_sft_preflight_rejects_noncanonical_sft_binding_before_row_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["files"]["sft"] = "data/public-samples/alternate-sft.jsonl"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    _install_ready_preflight_probes(monkeypatch)

    def forbidden_row_parse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("noncanonical SFT binding must be rejected before row parsing")

    monkeypatch.setattr(training, "_load_selected_smoke_rows", forbidden_row_parse)

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert result["blockers"] == ["DATASET_HASH_OR_ID_MISMATCH"]


def test_sft_preflight_selection_hash_changes_with_train_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    first = training.run_sft_preflight(config, manifest, output_dir)
    rows_path = manifest.parent / "sft_public_sample.jsonl"
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]
    rows.reverse()
    rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    second = training.run_sft_preflight(config, manifest, output_dir)

    assert first["dataset"]["selected_row_ids_sha256"] != second["dataset"]["selected_row_ids_sha256"]
    assert first["dataset"]["sft_sha256"] != second["dataset"]["sft_sha256"]


def test_sft_preflight_stops_parsing_after_exact_bounded_train_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    rows_path = manifest.parent / "sft_public_sample.jsonl"
    with rows_path.open("a", encoding="utf-8") as handle:
        handle.write("this later dev/test payload must never be parsed\n")
    _install_ready_preflight_probes(monkeypatch)

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is True
    assert result["dataset"]["selected_row_count"] == 2
    assert result["dataset"]["non_train_rows_selected"] == 0


@pytest.mark.parametrize(
    "blocker",
    ["ASSISTANT_ONLY_LABELS_INVALID", "MAX_SEQUENCE_LENGTH_EXCEEDED"],
)
def test_sft_preflight_blocks_invalid_objective(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    blocker: str,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    monkeypatch.setattr(
        training,
        "_probe_sft_model_and_objective",
        lambda config, rows: ({"local_files_only": True}, {"records_checked": 0}, [blocker]),
    )

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert result["blockers"] == [blocker]


@pytest.mark.parametrize(
    ("training_status", "expected_exit"),
    [
        ("dry_run", 0),
        ("training_completed", 0),
        ("training_skipped_by_config", 1),
        ("training_unavailable", 1),
        ("training_blocked_by_output_policy", 1),
        ("training_blocked_by_preflight", 1),
        ("training_failed", 1),
    ],
)
def test_sft_cli_maps_training_status_to_exit_code_and_one_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    training_status: str,
    expected_exit: int,
) -> None:
    monkeypatch.setattr(train_cli, "run_sft", lambda *args, **kwargs: {"training_status": training_status})

    exit_code = train_cli.main(
        [
            "sft",
            "--config",
            "config.json",
            "--manifest",
            "manifest.json",
            "--output-dir",
            "/approved/run",
            "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == expected_exit
    assert json.loads(captured.out) == {"training_status": training_status}
    assert captured.err == ""


@pytest.mark.parametrize(("ready", "expected_exit"), [(True, 0), (False, 1)])
def test_sft_preflight_cli_maps_ready_to_exit_code_and_one_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    ready: bool,
    expected_exit: int,
) -> None:
    result = {
        "schema_version": "voice2task-sft-preflight-v1",
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "blockers": [] if ready else ["CUDA_UNAVAILABLE"],
    }
    monkeypatch.setattr(train_cli, "run_sft_preflight", lambda *args, **kwargs: result, raising=False)

    exit_code = train_cli.main(
        [
            "sft-preflight",
            "--config",
            "config.json",
            "--manifest",
            "manifest.json",
            "--output-dir",
            "/approved/run",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == expected_exit
    assert json.loads(captured.out) == result
    assert captured.err == ""


def test_sft_preflight_cli_missing_config_is_stable_blocked_preflight_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_config = tmp_path / "missing-private-config.json"

    exit_code = train_cli.main(
        [
            "sft-preflight",
            "--config",
            missing_config.as_posix(),
            "--manifest",
            (tmp_path / "manifest.json").as_posix(),
            "--output-dir",
            (tmp_path / "approved" / "run").as_posix(),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert json.loads(captured.out) == {
        "schema_version": "voice2task-sft-preflight-v1",
        "ready": False,
        "status": "blocked",
        "blockers": ["CONFIG_FILE_MISSING"],
        "git": {},
        "config": {},
        "dataset": {},
        "model": {},
        "runtime": {},
        "gpu": {},
        "output": {},
        "objective": {},
    }
    assert captured.err == ""
    assert missing_config.as_posix() not in captured.out


def test_sft_preflight_malformed_config_is_sanitized_blocked_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    config.write_text("{not-json", encoding="utf-8")
    _install_ready_preflight_probes(monkeypatch)

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["schema_version"] == "voice2task-sft-preflight-v1"
    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert result["blockers"] == ["CONFIG_LOAD_FAILED"]
    serialized = json.dumps(result)
    assert config.as_posix() not in serialized
    assert "not-json" not in serialized


def test_sft_cli_runtime_exception_is_sanitized_nonzero_single_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("private failure at /" + "Users/person/model with token=secret")

    monkeypatch.setattr(train_cli, "run_sft", fail)

    exit_code = train_cli.main(
        [
            "sft",
            "--config",
            "config.json",
            "--manifest",
            "manifest.json",
            "--output-dir",
            "/approved/run",
            "--run-training",
        ]
    )

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 1
    assert result == {
        "schema_version": "voice2task-training-result-v1",
        "training_status": "training_failed",
        "blockers": ["TRAINING_RUNTIME_ERROR"],
    }
    assert captured.err == ""
    assert "Users" not in captured.out
    assert "secret" not in captured.out


def test_sft_cli_sanitizes_private_paths_in_normal_blocked_result(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        train_cli,
        "run_sft",
        lambda *args, **kwargs: {
            "training_status": "training_blocked_by_preflight",
            "blockers": ["CUDA_UNAVAILABLE"],
            "hyperparameters": {
                "base_model_runtime_path": "/" + "Users/person/private-model",
                "output_root": "/" + "mnt/data/person/private-output",
            },
        },
    )

    exit_code = train_cli.main(
        [
            "sft",
            "--config",
            "config.json",
            "--manifest",
            "manifest.json",
            "--output-dir",
            "/approved/run",
            "--run-training",
        ]
    )

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert exit_code == 1
    assert "hyperparameters" not in result
    assert "Users/person" not in captured.out
    assert "mnt/data/person" not in captured.out
    assert captured.err == ""


def _ready_preflight_result() -> dict[str, Any]:
    return {
        "schema_version": "voice2task-sft-preflight-v1",
        "ready": True,
        "status": "ready",
        "blockers": [],
        "git": {"commit_sha": "a" * 40, "tracked_worktree_clean": True},
        "config": {"config_sha256": "b" * 64},
        "dataset": {
            "manifest_sha256": "c" * 64,
            "sft_sha256": "d" * 64,
            "selected_row_ids_sha256": "e" * 64,
            "selected_row_count": 2,
        },
        "model": {"public_id": "Qwen/Qwen2.5-7B-Instruct"},
        "runtime": {"versions": {"torch": "test"}},
        "gpu": {"name": "NVIDIA A100-SXM4-80GB"},
        "output": {"ready": True, "blockers": [], "output_path_sha256": "f" * 64},
        "objective": {"records_checked": 2},
    }


def test_run_sft_returns_preflight_blocker_without_writing_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    blocked = _ready_preflight_result()
    blocked.update({"ready": False, "status": "blocked", "blockers": ["CUDA_UNAVAILABLE"]})
    monkeypatch.setattr(
        training,
        "_run_sft_preflight_core",
        lambda *args: (blocked, None),
    )
    model_loads: list[str] = []
    monkeypatch.setattr(training, "_run_real_sft", lambda *args: model_loads.append("loaded"))

    result = training.run_sft(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_blocked_by_preflight"
    assert result["blockers"] == ["CUDA_UNAVAILABLE"]
    assert model_loads == []
    assert not output_dir.exists()


def test_run_sft_blocked_real_mode_calls_preflight_before_all_legacy_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    blocked = _ready_preflight_result()
    blocked.update({"ready": False, "status": "blocked", "blockers": ["CUDA_UNAVAILABLE"]})
    calls: list[str] = []

    def shared_core(*args: Any) -> tuple[dict[str, Any], None]:
        calls.append("preflight")
        return blocked, None

    def forbidden_read(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("real SFT must not use legacy config/metadata/dataset reads around preflight")

    monkeypatch.setattr(training, "_run_sft_preflight_core", shared_core)
    monkeypatch.setattr(training, "_load_config", forbidden_read)
    monkeypatch.setattr(training, "_metadata_common", forbidden_read)
    monkeypatch.setattr(training, "_manifest_load_summary", forbidden_read)
    monkeypatch.setattr(training, "read_jsonl", forbidden_read)

    result = training.run_sft(config, manifest, output_dir, dry_run=False)

    assert calls == ["preflight"]
    assert result["training_status"] == "training_blocked_by_preflight"
    assert result["blockers"] == ["CUDA_UNAVAILABLE"]
    assert result["preflight"] == blocked
    assert not output_dir.exists()


def test_run_sft_ready_real_mode_builds_metadata_only_from_bound_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None
    calls: list[str] = []

    def shared_core(*args: Any) -> tuple[dict[str, Any], object]:
        calls.append("preflight")
        return preflight, execution_context

    def forbidden_read(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("ready real SFT must use only bound preflight context")

    monkeypatch.setattr(training, "_run_sft_preflight_core", shared_core)
    monkeypatch.setattr(training, "_load_config", forbidden_read)
    monkeypatch.setattr(training, "_metadata_common", forbidden_read)
    monkeypatch.setattr(training, "_manifest_load_summary", forbidden_read)
    monkeypatch.setattr(training, "read_jsonl", forbidden_read)

    def run_real(
        metadata: dict[str, Any],
        config_snapshot: dict[str, Any],
        bound_manifest: Path,
        bound_output: Path,
        *,
        execution_context: object,
    ) -> None:
        assert config_snapshot == execution_context.config_snapshot()
        assert bound_manifest == execution_context.manifest_path
        assert bound_output == execution_context.output_dir
        adapter = bound_output / "adapter"
        adapter.mkdir(parents=True)
        (adapter / "adapter_config.json").write_text("{}\n", encoding="utf-8")
        (adapter / "adapter_model.safetensors").write_bytes(b"adapter")
        metadata.update(
            {
                "observed_optimizer_steps": 1,
                "training_rows_used": 2,
                "train_result_metrics": {"train_loss": 1.25},
                "trainable_parameter_count": 8,
                "adapter_tensor_count": 2,
                "adapter_state_digest_before": "a" * 64,
                "adapter_state_digest_after": "b" * 64,
                "changed_adapter_tensor_count": 1,
                "all_adapter_tensors_finite": True,
            }
        )

    monkeypatch.setattr(training, "_run_real_sft", run_real)

    result = training.run_sft(config, manifest, output_dir, dry_run=False)

    assert calls == ["preflight"]
    assert result["training_status"] == "training_completed"
    assert result["dataset_manifest_id"] == execution_context.manifest_id
    assert result["dataset_load"]["loaded_rows"] == 2
    assert result["preflight"] == preflight


def test_run_sft_does_not_read_dataset_before_blocked_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    blocked = _ready_preflight_result()
    blocked.update({"ready": False, "status": "blocked", "blockers": ["CUDA_UNAVAILABLE"]})
    monkeypatch.setattr(
        training,
        "_run_sft_preflight_core",
        lambda *args: (blocked, None),
    )

    def forbidden_legacy_dataset_read(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("real run must not select dataset rows before preflight")

    monkeypatch.setattr(
        training,
        "_record_sft_training_selection_from_config",
        forbidden_legacy_dataset_read,
    )

    result = training.run_sft(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_blocked_by_preflight"
    assert result["blockers"] == ["CUDA_UNAVAILABLE"]
    assert not output_dir.exists()


def test_run_sft_uses_shared_preflight_core_and_passes_bound_context_to_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    preflight, bound_context = training._run_sft_preflight_core(  # noqa: SLF001
        config,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert bound_context is not None
    core_calls: list[tuple[Path, Path, Path]] = []
    runner_contexts: list[object] = []

    def shared_core(
        config_path: Path,
        manifest_path: Path,
        candidate: Path,
    ) -> tuple[dict[str, Any], object]:
        core_calls.append((config_path, manifest_path, candidate))
        return preflight, bound_context

    monkeypatch.setattr(training, "_run_sft_preflight_core", shared_core, raising=False)

    def forbidden_public_wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("real execution must call the shared preflight core")

    monkeypatch.setattr(training, "run_sft_preflight", forbidden_public_wrapper)
    monkeypatch.setattr(
        training,
        "validate_sft_output_policy",
        lambda *args, **kwargs: {"ready": True, "blockers": [], "output_path_sha256": "f" * 64},
    )

    def run_real(
        metadata: dict[str, Any],
        config_snapshot: dict[str, Any],
        manifest_path: Path,
        run_output_dir: Path,
        *,
        execution_context: object,
    ) -> None:
        runner_contexts.append(execution_context)
        adapter = run_output_dir / "adapter"
        adapter.mkdir(parents=True)
        (adapter / "adapter_config.json").write_text("{}\n", encoding="utf-8")
        (adapter / "adapter_model.safetensors").write_bytes(b"adapter")
        metadata.update(
            {
                "observed_optimizer_steps": 1,
                "training_rows_used": 2,
                "train_result_metrics": {"train_loss": 1.25},
                "trainable_parameter_count": 8,
                "adapter_tensor_count": 2,
                "adapter_state_digest_before": "a" * 64,
                "adapter_state_digest_after": "b" * 64,
                "changed_adapter_tensor_count": 1,
                "all_adapter_tensors_finite": True,
            }
        )

    monkeypatch.setattr(training, "_run_real_sft", run_real)

    result = training.run_sft(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_completed"
    assert core_calls == [(config, manifest, output_dir)]
    assert runner_contexts == [bound_context]


def test_run_sft_rechecks_output_policy_after_ready_preflight_and_blocks_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None
    monkeypatch.setattr(
        training,
        "_run_sft_preflight_core",
        lambda *args: (preflight, execution_context),
    )
    policy_calls: list[Path] = []

    def drifted_policy(config: dict[str, Any], candidate: Path, **kwargs: Any) -> dict[str, Any]:
        policy_calls.append(candidate)
        return {
            "ready": False,
            "blockers": ["OUTPUT_PATH_SYMLINK"],
            "root_path_sha256": "a" * 64,
            "output_path_sha256": "b" * 64,
        }

    monkeypatch.setattr(training, "validate_sft_output_policy", drifted_policy)
    model_loads: list[str] = []
    monkeypatch.setattr(training, "_run_real_sft", lambda *args: model_loads.append("loaded"))

    result = training.run_sft(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_blocked_by_output_policy"
    assert result["blockers"] == ["OUTPUT_PATH_SYMLINK"]
    assert policy_calls == [output_dir]
    assert model_loads == []
    assert not output_dir.exists()


def test_run_sft_does_not_write_when_final_in_runner_output_check_detects_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None
    monkeypatch.setattr(
        training,
        "_run_sft_preflight_core",
        lambda *args: (preflight, execution_context),
    )
    policies = iter(
        [
            {"ready": True, "blockers": [], "output_path_sha256": "a" * 64},
            {"ready": False, "blockers": ["OUTPUT_PATH_SYMLINK"], "output_path_sha256": "a" * 64},
        ]
    )
    monkeypatch.setattr(training, "validate_sft_output_policy", lambda *args, **kwargs: next(policies))

    result = training.run_sft(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_blocked_by_output_policy"
    assert result["blockers"] == ["OUTPUT_IDENTITY_CHANGED"]
    assert not output_dir.exists()


def test_run_sft_returns_stable_blocker_when_bound_preflight_input_drifts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None
    monkeypatch.setattr(
        training,
        "_run_sft_preflight_core",
        lambda *args: (preflight, execution_context),
    )
    monkeypatch.setattr(
        training,
        "validate_sft_output_policy",
        lambda *args, **kwargs: {"ready": True, "blockers": []},
    )

    def drifted_runner(*args: Any, **kwargs: Any) -> None:
        raise training.SFTPreflightDriftError(["CONFIG_DRIFT_DETECTED"])

    monkeypatch.setattr(training, "_run_real_sft", drifted_runner)

    result = training.run_sft(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_blocked_by_preflight"
    assert result["blockers"] == ["CONFIG_DRIFT_DETECTED"]
    assert not output_dir.exists()


def test_run_sft_smoke_completion_preserves_clean_evaluation_blockers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None
    monkeypatch.setattr(
        training,
        "_run_sft_preflight_core",
        lambda *args: (preflight, execution_context),
    )
    monkeypatch.setattr(
        training,
        "validate_sft_output_policy",
        lambda *args, **kwargs: {"ready": True, "blockers": [], "output_path_sha256": "f" * 64},
    )

    def run_real(
        metadata: dict[str, Any],
        config: dict[str, Any],
        manifest_path: Path,
        run_output_dir: Path,
        *,
        execution_context: object,
    ) -> None:
        adapter = run_output_dir / "adapter"
        adapter.mkdir(parents=True)
        (adapter / "adapter_config.json").write_text("{}\n", encoding="utf-8")
        (adapter / "adapter_model.safetensors").write_bytes(b"adapter")
        metadata.update(
            {
                "observed_optimizer_steps": 1,
                "training_rows_used": 2,
                "train_result_metrics": {"train_loss": 1.25},
                "training_budget": {"configured_max_steps": 1, "observed_optimizer_steps": 1},
                "trainable_parameter_count": 8,
                "adapter_tensor_count": 2,
                "adapter_state_digest_before": "a" * 64,
                "adapter_state_digest_after": "b" * 64,
                "changed_adapter_tensor_count": 1,
                "all_adapter_tensors_finite": True,
            }
        )

    monkeypatch.setattr(training, "_run_real_sft", run_real)

    result = training.run_sft(config, manifest, output_dir, dry_run=False)

    assert result["training_status"] == "training_completed"
    assert result["smoke_status"] == "SMOKE_COMPLETED"
    assert result["observed_optimizer_steps"] == 1
    assert result["training_rows_used"] == 2
    assert result["adapter_files"] == [
        {
            "name": "adapter_config.json",
            "size": 3,
            "sha256": training._sha256_file(  # noqa: SLF001
                output_dir / "adapter" / "adapter_config.json"
            ),
        },
        {
            "name": "adapter_model.safetensors",
            "size": 7,
            "sha256": training._sha256_file(  # noqa: SLF001
                output_dir / "adapter" / "adapter_model.safetensors"
            ),
        },
    ]
    assert result["clean_evaluation"] == {
        "acquisition_source_status": "UNAVAILABLE",
        "authoritatively_bound_binding_count": 0,
        "human_acceptance_status": "NOT_RECORDED",
        "protocol_freeze_status": "NOT_FROZEN",
        "clean_population_status": "NOT_MATERIALIZED",
        "freeze_authorized": False,
        "execution_readiness": False,
    }
    assert result["preflight"] == preflight


@pytest.mark.parametrize(
    ("case", "expected_blocker"),
    [
        ("boolean_loss", "TRAINING_LOSS_INVALID"),
        ("missing_adapter_config", "ADAPTER_OUTPUT_INVALID"),
        ("full_weight_outside_adapter", "FULL_MODEL_WEIGHTS_DETECTED"),
        ("row_count_mismatch", "TRAIN_ROW_SELECTION_INVALID"),
    ],
)
def test_sft_smoke_postconditions_fail_closed_on_invalid_artifacts_and_budget(
    tmp_path: Path,
    case: str,
    expected_blocker: str,
) -> None:
    run_dir = tmp_path / "run"
    adapter = run_dir / "adapter"
    adapter.mkdir(parents=True)
    (adapter / "adapter_config.json").write_text("{}\n", encoding="utf-8")
    (adapter / "adapter_model.safetensors").write_bytes(b"adapter")
    metadata: dict[str, Any] = {
        "adapter_path": adapter.as_posix(),
        "metadata_path": (run_dir / "adapter_metadata.json").as_posix(),
        "hyperparameters": {"max_train_rows": 2},
        "observed_optimizer_steps": 1,
        "training_rows_used": 2,
        "train_result_metrics": {"train_loss": 1.25},
    }

    if case == "boolean_loss":
        metadata["train_result_metrics"] = {"train_loss": True}
    elif case == "missing_adapter_config":
        (adapter / "adapter_config.json").unlink()
    elif case == "full_weight_outside_adapter":
        checkpoint = run_dir / "checkpoint-1"
        checkpoint.mkdir()
        (checkpoint / "model-00001-of-00002.safetensors").write_bytes(b"base")
    else:
        metadata["training_rows_used"] = 1

    blockers = training._sft_smoke_postconditions(metadata)  # noqa: SLF001

    assert expected_blocker in blockers


def test_real_sft_rechecks_output_before_tokenizer_or_model_loading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path, manifest, output_dir = _write_preflight_fixture(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config_path,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None
    monkeypatch.setattr(training, "_probe_sft_gpu", lambda: ({"idle_verified": True}, []))
    loads: list[str] = []
    monkeypatch.setattr(
        training,
        "validate_sft_output_policy",
        lambda *args, **kwargs: {
            "ready": False,
            "blockers": ["OUTPUT_PATH_SYMLINK"],
            "output_path_sha256": "a" * 64,
        },
    )

    class FailIfLoaded:
        @staticmethod
        def from_pretrained(*args: Any, **kwargs: Any) -> None:
            loads.append("loaded")

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(AutoModelForCausalLM=FailIfLoaded, AutoTokenizer=FailIfLoaded),
    )
    monkeypatch.setitem(sys.modules, "datasets", types.SimpleNamespace(Dataset=object))
    monkeypatch.setitem(sys.modules, "trl", types.SimpleNamespace(SFTTrainer=object))

    with pytest.raises(training.SFTOutputPolicyError) as exc_info:
        training._run_real_sft(  # noqa: SLF001
            {"adapter_path": (output_dir / "adapter").as_posix(), "dataset_load": {}},
            config,
            manifest,
            output_dir,
            execution_context=execution_context,
        )

    assert exc_info.value.blockers == ["OUTPUT_IDENTITY_CHANGED"]
    assert loads == []
    assert not output_dir.exists()


def test_real_sft_blocks_config_drift_before_any_model_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config_path,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["max_steps"] = 2
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    model_loads: list[str] = []

    class FailIfLoaded:
        @staticmethod
        def from_pretrained(*args: Any, **kwargs: Any) -> None:
            model_loads.append("loaded")
            raise AssertionError("model/tokenizer load must not occur after preflight drift")

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(AutoModelForCausalLM=FailIfLoaded, AutoTokenizer=FailIfLoaded),
    )
    monkeypatch.setitem(sys.modules, "datasets", types.SimpleNamespace(Dataset=object))
    monkeypatch.setitem(sys.modules, "trl", types.SimpleNamespace(SFTTrainer=object))

    with pytest.raises(RuntimeError) as exc_info:
        training._run_real_sft(  # noqa: SLF001
            {"adapter_path": (output_dir / "adapter").as_posix(), "dataset_load": {}},
            payload,
            manifest,
            output_dir,
            execution_context=execution_context,
        )

    assert getattr(exc_info.value, "blockers", None) == ["CONFIG_DRIFT_DETECTED"]
    assert model_loads == []
    assert not output_dir.exists()


@pytest.mark.parametrize(
    ("mutated_input", "expected_blocker"),
    [
        ("manifest", "MANIFEST_DRIFT_DETECTED"),
        ("sft", "SFT_DRIFT_DETECTED"),
        ("model", "MODEL_DRIFT_DETECTED"),
    ],
)
def test_bound_preflight_context_detects_each_mutable_input_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutated_input: str,
    expected_blocker: str,
) -> None:
    config_path, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config_path,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None

    if mutated_input == "manifest":
        with manifest.open("a", encoding="utf-8") as handle:
            handle.write("\n")
    elif mutated_input == "sft":
        with (manifest.parent / "sft_public_sample.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("{}\n")
    else:
        model_path = Path(json.loads(config_path.read_text(encoding="utf-8"))["base_model_runtime_path"])
        with (model_path / "model-00001-of-00001.safetensors").open("ab") as handle:
            handle.write(b"drift")

    assert training._preflight_input_drift_blockers(execution_context) == [  # noqa: SLF001
        expected_blocker
    ]


def test_preflight_context_binds_model_inventory_returned_by_validated_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    model_root = Path(config["base_model_runtime_path"])
    weight_path = model_root / "model-00001-of-00001.safetensors"
    original_size = weight_path.stat().st_size

    def probe_then_swap(
        config_snapshot: dict[str, Any],
        rows: list[Any],
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        fingerprints, inventory = training._stable_local_model_inventory(model_root)  # noqa: SLF001
        weight_path.write_bytes(weight_path.read_bytes() + b"swapped-after-probe")
        return (
            {
                "public_id": "Qwen/Qwen2.5-7B-Instruct",
                "local_files_only": True,
                "stable_fingerprints": fingerprints,
                "weight_inventory": inventory,
                "total_weight_bytes": sum(int(item["size"]) for item in inventory),
                "minimum_weight_bytes": 12 * 1024**3,
                "geometry_matches_qwen2_5_7b": True,
                "snapshot_revision_sha256": "f" * 64,
            },
            {
                "records_checked": len(rows),
                "prompt_labels_masked": True,
                "assistant_target_present": True,
                "max_sequence_length": 1024,
            },
            [],
        )

    monkeypatch.setattr(training, "_probe_sft_model_and_objective", probe_then_swap)

    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config_path,
        manifest,
        output_dir,
    )

    assert preflight["ready"] is True
    assert preflight["model"]["weight_inventory"][0]["size"] == original_size
    assert execution_context is not None
    assert training._preflight_input_drift_blockers(execution_context) == [  # noqa: SLF001
        "MODEL_DRIFT_DETECTED"
    ]


def test_real_sft_passes_local_bf16_options_and_bounded_training_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path, manifest, output_dir = _write_preflight_fixture(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config_path,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None
    calls: dict[str, Any] = {"order": []}
    monkeypatch.setattr(
        training,
        "_probe_sft_gpu",
        lambda: calls["order"].append("gpu") or ({"idle_verified": True}, []),
    )
    fake_bfloat16 = object()

    class FakeTokenizer:
        pad_token_id = None
        pad_token = None
        eos_token_id = 2
        eos_token = "<eos>"

    tokenizer = FakeTokenizer()

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(path: str, **kwargs: Any) -> FakeTokenizer:
            calls["order"].append("tokenizer")
            calls["tokenizer"] = {"path": path, **kwargs}
            return tokenizer

    class FakeModel:
        def __init__(self) -> None:
            self.config = types.SimpleNamespace(use_cache=True)
            self.gradient_checkpointing_enabled = False

        def gradient_checkpointing_enable(self) -> None:
            self.gradient_checkpointing_enabled = True

        def save_pretrained(self, path: str) -> None:
            adapter = Path(path)
            adapter.mkdir(parents=True)
            (adapter / "adapter_model.safetensors").write_bytes(b"adapter")

    model = FakeModel()

    class FakeAutoModelForCausalLM:
        @staticmethod
        def from_pretrained(path: str, **kwargs: Any) -> FakeModel:
            calls["order"].append("model")
            calls["model"] = {"path": path, **kwargs}
            return model

    class FakeDataset:
        @staticmethod
        def from_list(records: list[dict[str, list[int]]]) -> list[dict[str, list[int]]]:
            calls["records"] = records
            return records

    class FakeTrainingArguments:
        def __init__(self, **kwargs: Any) -> None:
            calls["training_arguments"] = kwargs

    class FakeSFTTrainer:
        def __init__(
            self,
            *,
            model: Any,
            processing_class: Any,
            train_dataset: Any,
            args: Any,
            peft_config: Any,
            data_collator: Any,
        ) -> None:
            self.model = model
            self.state = types.SimpleNamespace(global_step=1)

        def train(self) -> Any:
            return types.SimpleNamespace(metrics={"train_loss": 0.5})

    monkeypatch.setitem(sys.modules, "torch", types.SimpleNamespace(bfloat16=fake_bfloat16))
    monkeypatch.setitem(sys.modules, "datasets", types.SimpleNamespace(Dataset=FakeDataset))
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(
            AutoModelForCausalLM=FakeAutoModelForCausalLM,
            AutoTokenizer=FakeAutoTokenizer,
            TrainingArguments=FakeTrainingArguments,
        ),
    )
    monkeypatch.setitem(sys.modules, "trl", types.SimpleNamespace(SFTTrainer=FakeSFTTrainer))
    monkeypatch.setitem(sys.modules, "peft", types.SimpleNamespace(LoraConfig=lambda **kwargs: kwargs))
    output_policy_results = iter(
        [
            {
                "ready": True,
                "blockers": [],
                "output_path_sha256": json.loads(execution_context.output_facts_json)["output_path_sha256"],
            },
            {
                "ready": False,
                "blockers": ["OUTPUT_DIRECTORY_EXISTS"],
                "output_path_sha256": json.loads(execution_context.output_facts_json)["output_path_sha256"],
            },
        ]
    )
    monkeypatch.setattr(
        training,
        "validate_sft_output_policy",
        lambda *args, **kwargs: calls["order"].append("policy") or next(output_policy_results),
    )
    monkeypatch.setattr(
        training,
        "_assistant_only_training_record",
        lambda row, tokenizer, max_seq_length: {
            "input_ids": [1, 2],
            "attention_mask": [1, 1],
            "labels": [-100, 2],
            "assistant_token_indices": [1],
        },
    )
    monkeypatch.setattr(
        training,
        "_record_sft_training_selection_from_config",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("runner must consume rows from bound preflight context")
        ),
    )
    metadata: dict[str, Any] = {"adapter_path": (output_dir / "adapter").as_posix(), "dataset_load": {}}

    training._run_real_sft(  # noqa: SLF001
        metadata,
        config,
        manifest,
        output_dir,
        execution_context=execution_context,
    )

    assert calls["order"] == ["gpu", "policy", "tokenizer", "gpu", "model"]
    assert calls["tokenizer"] == {
        "path": config["base_model_runtime_path"],
        "local_files_only": True,
        "trust_remote_code": False,
    }
    assert calls["model"]["path"] == config["base_model_runtime_path"]
    assert calls["model"]["local_files_only"] is True
    assert calls["model"]["trust_remote_code"] is False
    assert calls["model"]["torch_dtype"] is fake_bfloat16
    assert calls["model"]["low_cpu_mem_usage"] is True
    assert "device_map" not in calls["model"]
    assert tokenizer.pad_token == tokenizer.eos_token
    assert model.gradient_checkpointing_enabled is True
    assert model.config.use_cache is False
    expected_training_arguments = {
        "max_steps": 1,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 1,
        "save_strategy": "no",
        "logging_steps": 1,
        "seed": 42,
        "bf16": True,
        "fp16": False,
        "tf32": True,
        "gradient_checkpointing": True,
        "report_to": [],
    }
    assert {key: calls["training_arguments"][key] for key in expected_training_arguments} == expected_training_arguments
    assert metadata["observed_optimizer_steps"] == 1
    assert metadata["training_rows_used"] == 2
    assert metadata["train_result_metrics"]["train_loss"] == 0.5


def test_model_objective_probe_passes_local_files_only_to_config_and_tokenizer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path, manifest, _ = _write_preflight_fixture(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rows = training._load_sft_training_rows(manifest, split="train")  # noqa: SLF001
    model_root = Path(config["base_model_runtime_path"])
    (model_root / "model-00001-of-00001.safetensors").open("r+b").truncate(12 * 1024**3)
    calls: list[dict[str, Any]] = []

    class FakeAutoConfig:
        @staticmethod
        def from_pretrained(path: str, **kwargs: Any) -> Any:
            calls.append({"kind": "config", "path": path, **kwargs})
            return types.SimpleNamespace(
                model_type="qwen2",
                architectures=["Qwen2ForCausalLM"],
                hidden_size=3584,
                intermediate_size=18944,
                num_hidden_layers=28,
                num_attention_heads=28,
                num_key_value_heads=4,
                vocab_size=152064,
            )

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(path: str, **kwargs: Any) -> object:
            calls.append({"kind": "tokenizer", "path": path, **kwargs})
            return object()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(AutoConfig=FakeAutoConfig, AutoTokenizer=FakeAutoTokenizer),
    )
    monkeypatch.setattr(
        training,
        "_assistant_only_training_record",
        lambda row, tokenizer, max_seq_length: {
            "input_ids": [1, 2],
            "attention_mask": [1, 1],
            "labels": [-100, 2],
            "assistant_token_indices": [1],
        },
    )

    model, objective, blockers = training._probe_sft_model_and_objective(config, rows)  # noqa: SLF001

    assert blockers == []
    assert [call["kind"] for call in calls] == ["config", "tokenizer"]
    assert all(call["local_files_only"] is True for call in calls)
    assert all(call["trust_remote_code"] is False for call in calls)
    assert model["stable_fingerprints"]
    assert model["weight_inventory"] == [
        {"name": "model-00001-of-00001.safetensors", "size": 12 * 1024**3}
    ]
    assert objective["records_checked"] == 2


def test_sft_preflight_rejects_one_prompt_label_leak_even_with_other_masked_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, manifest, output_dir = _write_preflight_fixture(tmp_path)
    actual_model_probe = training._probe_sft_model_and_objective  # noqa: SLF001
    _install_ready_preflight_probes(monkeypatch)
    monkeypatch.setattr(training, "_probe_sft_model_and_objective", actual_model_probe)
    config_payload = json.loads(config.read_text(encoding="utf-8"))
    model_root = Path(config_payload["base_model_runtime_path"])
    (model_root / "model-00001-of-00001.safetensors").open("r+b").truncate(12 * 1024**3)

    class FakeAutoConfig:
        @staticmethod
        def from_pretrained(path: str, **kwargs: Any) -> Any:
            return types.SimpleNamespace(
                model_type="qwen2",
                architectures=["Qwen2ForCausalLM"],
                hidden_size=3584,
                intermediate_size=18944,
                num_hidden_layers=28,
                num_attention_heads=28,
                num_key_value_heads=4,
                vocab_size=152064,
            )

    class FakeTokenizer:
        def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
            return {
                "input_ids": [10, 11, 12, 13],
                "attention_mask": [1, 1, 1, 1],
                "offset_mapping": [(0, 1), (1, 2), (2, 3), (3, 4)],
            }

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(path: str, **kwargs: Any) -> FakeTokenizer:
            return FakeTokenizer()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(AutoConfig=FakeAutoConfig, AutoTokenizer=FakeAutoTokenizer),
    )
    monkeypatch.setattr(training, "format_sft_training_text", lambda row, tokenizer: "abcd")
    monkeypatch.setattr(training, "canonical_contract_json", lambda target: "cd")
    monkeypatch.setattr(
        training,
        "_assistant_only_labels_from_encoded",
        lambda **kwargs: ([-100, 11, 12, 13], []),
    )

    result = training.run_sft_preflight(config, manifest, output_dir)

    assert result["ready"] is False
    assert result["blockers"] == ["ASSISTANT_ONLY_LABELS_INVALID"]


def test_real_sft_rechecks_gpu_idle_state_before_model_weight_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path, manifest, output_dir = _write_preflight_fixture(tmp_path)
    _install_ready_preflight_probes(monkeypatch)
    preflight, execution_context = training._run_sft_preflight_core(  # noqa: SLF001
        config_path,
        manifest,
        output_dir,
    )
    assert preflight["ready"] is True
    assert execution_context is not None
    monkeypatch.setattr(
        training,
        "_probe_sft_gpu",
        lambda: (
            {"free_memory_gib": 34.0, "compute_process_count": 0, "idle_verified": False},
            ["GPU_FREE_MEMORY_INSUFFICIENT"],
        ),
    )
    model_loads: list[str] = []

    class FailIfLoaded:
        @staticmethod
        def from_pretrained(*args: Any, **kwargs: Any) -> None:
            model_loads.append("loaded")

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(AutoModelForCausalLM=FailIfLoaded, AutoTokenizer=FailIfLoaded),
    )
    with pytest.raises(training.SFTPreflightDriftError) as exc_info:
        training._run_real_sft(  # noqa: SLF001
            {"adapter_path": (output_dir / "adapter").as_posix(), "dataset_load": {}},
            execution_context.config_snapshot(),
            manifest,
            output_dir,
            execution_context=execution_context,
        )
    assert exc_info.value.blockers == ["GPU_FREE_MEMORY_INSUFFICIENT"]
    assert model_loads == []
    assert not output_dir.exists()


def test_model_probe_rejects_generic_qwen2_geometry_and_tiny_weight_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path, manifest, _ = _write_preflight_fixture(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rows = training._load_sft_training_rows(manifest, split="train")  # noqa: SLF001

    class GenericQwenConfig:
        @staticmethod
        def from_pretrained(path: str, **kwargs: Any) -> Any:
            return types.SimpleNamespace(model_type="qwen2")

    class FakeTokenizer:
        @staticmethod
        def from_pretrained(path: str, **kwargs: Any) -> object:
            return object()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(AutoConfig=GenericQwenConfig, AutoTokenizer=FakeTokenizer),
    )
    monkeypatch.setattr(
        training,
        "_assistant_only_training_record",
        lambda row, tokenizer, max_seq_length: {
            "input_ids": [1, 2],
            "attention_mask": [1, 1],
            "labels": [-100, 2],
            "assistant_token_indices": [1],
        },
    )

    _, _, blockers = training._probe_sft_model_and_objective(config, rows)  # noqa: SLF001

    assert blockers == ["MODEL_IDENTITY_MISMATCH", "MODEL_WEIGHT_INSUFFICIENT"]


def test_public_a100_smoke_example_is_disabled_bounded_and_path_safe() -> None:
    path = Path(__file__).resolve().parents[1] / "configs" / "sft-a100-smoke.example.json"

    assert path.is_file()
    config = json.loads(path.read_text(encoding="utf-8"))
    assert config == {
        "base_model_public_id": "Qwen/Qwen2.5-7B-Instruct",
        "base_model_runtime_path": "<private-local-qwen2.5-7b-instruct-path>",
        "allow_heavy_training": False,
        "local_files_only": True,
        "trust_remote_code": False,
        "dtype": "bfloat16",
        "torch_dtype": "bfloat16",
        "dataset_split": "train",
        "dataset_manifest_id": "public-sample-20260619T090925Z",
        "max_train_rows": 2,
        "max_steps": 1,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 1,
        "max_seq_length": 1024,
        "bf16": True,
        "fp16": False,
        "tf32": True,
        "gradient_checkpointing": True,
        "use_cache": False,
        "low_cpu_mem_usage": True,
        "save_strategy": "no",
        "logging_steps": 1,
        "seed": 42,
        "report_to": [],
        "min_free_disk_gib": 20,
        "output_root": "<approved-private-output-root>",
        "lora": {
            "r": 8,
            "alpha": 16,
            "dropout": 0.05,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
        },
    }
    assert "/mnt/data/" not in path.read_text(encoding="utf-8")
    assert "/Users/" not in path.read_text(encoding="utf-8")
