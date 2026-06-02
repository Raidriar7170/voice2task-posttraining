from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from voice2task.formatting import format_dpo_pair, format_sft_messages
from voice2task.io import read_json, read_jsonl, write_json
from voice2task.schemas import DPOPair, SFTDatasetRow


def _load_config(config_path: Path) -> dict[str, Any]:
    if config_path.suffix != ".json":
        raise ValueError("bootstrap training configs are JSON in this phase")
    return read_json(config_path)


def _resolve_manifest_file(manifest_path: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = Path(value)
    if candidate.exists():
        return candidate
    relative_candidate = manifest_path.parent / candidate.name
    if relative_candidate.exists():
        return relative_candidate
    return None


def _manifest_load_summary(manifest_path: Path, stage: str) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    files = manifest.get("files", {})
    if not isinstance(files, dict):
        files = {}
    dataset_key = "dpo" if stage == "dpo" else "sft"
    dataset_path = _resolve_manifest_file(manifest_path, files.get(dataset_key))
    loaded_rows = len(read_jsonl(dataset_path)) if dataset_path is not None else 0
    return {
        "manifest_id": str(manifest.get("manifest_id", manifest_path.stem)),
        "manifest_counts": manifest.get("counts", {}),
        "dataset_key": dataset_key,
        "dataset_path": dataset_path.as_posix() if dataset_path is not None else None,
        "loaded_rows": loaded_rows,
    }


def _heavy_training_allowed(config: dict[str, Any]) -> bool:
    return bool(config.get("allow_heavy_training"))


def _sanitized_package_versions() -> dict[str, str]:
    versions = {"python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"}
    for package in ("accelerate", "datasets", "peft", "transformers", "trl"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not_installed"
    return versions


def _gpu_selection_policy(config: dict[str, Any]) -> dict[str, str]:
    policy = config.get("gpu_selection_policy")
    if not isinstance(policy, str) or not policy:
        policy = "not_selected_locally_select_idle_gpu_for_a100"
    identifier_policy = config.get("gpu_identifier_policy")
    if not isinstance(identifier_policy, str) or not identifier_policy:
        identifier_policy = "policy_only_no_host_ip_or_gpu_uuid"
    return {
        "policy": policy,
        "identifier_policy": identifier_policy,
    }


def _heavy_training_gate(config: dict[str, Any], dry_run: bool) -> dict[str, bool]:
    cli_run_training = not dry_run
    config_allows = _heavy_training_allowed(config)
    return {
        "cli_run_training": cli_run_training,
        "config_allow_heavy_training": config_allows,
        "will_run_heavy_training": cli_run_training and config_allows,
    }


def _output_dir_within_configured_root(config: dict[str, Any], output_dir: Path) -> bool:
    output_root = config.get("output_root")
    if not isinstance(output_root, str) or not output_root:
        return True
    if "<" in output_root or ">" in output_root:
        return False
    candidate = output_dir.expanduser()
    root = Path(output_root).expanduser()
    if not candidate.is_absolute() or not root.is_absolute():
        return False
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _output_paths(
    *,
    config: dict[str, Any],
    output_dir: Path,
    adapter_path: Path,
    metadata_path: Path,
) -> dict[str, Any]:
    paths: dict[str, Any] = {
        "run_output_dir": output_dir.as_posix(),
        "adapter_path": adapter_path.as_posix(),
        "metadata_path": metadata_path.as_posix(),
    }
    for config_key, output_key in (
        ("output_root", "configured_output_root"),
        ("output_dir", "configured_output_dir"),
        ("adapter_output_dir", "configured_adapter_output_dir"),
        ("evidence_output_dir", "configured_evidence_output_dir"),
    ):
        value = config.get(config_key)
        if isinstance(value, str) and value:
            paths[output_key] = value
    return paths


def _command_summary(
    *,
    stage: str,
    config_path: Path,
    manifest_path: Path,
    output_dir: Path,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "entrypoint": f"voice2task-train {stage}",
        "config": config_path.as_posix(),
        "manifest": manifest_path.as_posix(),
        "output_dir": output_dir.as_posix(),
        "mode": "dry_run" if dry_run else "run_training",
        "requires_cli_run_training": not dry_run,
        "requires_config_allow_heavy_training": True,
    }


def _metadata_common(
    *,
    stage: str,
    config_path: Path,
    manifest_path: Path,
    output_dir: Path,
    dry_run: bool,
) -> dict[str, Any]:
    config = _load_config(config_path)
    load_summary = _manifest_load_summary(manifest_path, stage)
    adapter_path = output_dir / "adapter"
    metadata_path = output_dir / "adapter_metadata.json"
    mode_flag = "--dry-run" if dry_run else "--run-training"
    heavy_training_gate = _heavy_training_gate(config, dry_run)
    return {
        "stage": stage,
        "stack": "transformers+peft+trl",
        "base_model": config.get("base_model"),
        "adapter_path": adapter_path.as_posix(),
        "dataset_manifest_id": load_summary["manifest_id"],
        "dataset_manifest_path": manifest_path.as_posix(),
        "dataset_load": load_summary,
        "hyperparameters": config,
        "dry_run": dry_run,
        "release_status": "not_released",
        "training_status": "dry_run" if dry_run else "pending_heavy_training",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "package_versions": _sanitized_package_versions(),
        "gpu_selection_policy": _gpu_selection_policy(config),
        "heavy_training_gate": heavy_training_gate,
        "output_paths": _output_paths(
            config=config,
            output_dir=output_dir,
            adapter_path=adapter_path,
            metadata_path=metadata_path,
        ),
        "command_summary": _command_summary(
            stage=stage,
            config_path=config_path,
            manifest_path=manifest_path,
            output_dir=output_dir,
            dry_run=dry_run,
        ),
        "training_command": (
            f"voice2task-train {stage} --config {config_path.as_posix()} "
            f"--manifest {manifest_path.as_posix()} --output-dir {output_dir.as_posix()} {mode_flag}"
        ),
        "metadata_path": metadata_path.as_posix(),
        "notes": "Dry-run metadata only; no model download or heavy training was executed."
        if dry_run
        else "Training entrypoint checked; install train extras and provide runtime resources for heavy execution.",
    }


def _train_dependencies_available() -> bool:
    return all(importlib.util.find_spec(module) is not None for module in ("datasets", "peft", "transformers", "trl"))


def _write_training_plan(metadata: dict[str, Any], stage: str) -> dict[str, Any]:
    metadata["release_status"] = "not_released"
    metadata["training_status"] = "training_unavailable"
    metadata["trainer_available"] = False
    metadata["notes"] = (
        f"{stage.upper()} real-training entrypoint is wired, but train extras are not installed in this runtime. "
        "Install the train dependency group before running heavy training."
    )
    write_json(Path(metadata["metadata_path"]), metadata)
    return metadata


def _write_training_skipped(metadata: dict[str, Any], stage: str) -> dict[str, Any]:
    metadata["release_status"] = "not_released"
    metadata["training_status"] = "training_skipped_by_config"
    metadata["trainer_available"] = False
    metadata["notes"] = (
        f"{stage.upper()} real-training entrypoint is available, but this config does not set "
        "`allow_heavy_training: true`. This prevents accidental model downloads during bootstrap validation."
    )
    write_json(Path(metadata["metadata_path"]), metadata)
    return metadata


def _write_training_blocked_by_output_policy(metadata: dict[str, Any], stage: str) -> dict[str, Any]:
    config_output_root = metadata.get("hyperparameters", {}).get("output_root")
    unresolved_template = isinstance(config_output_root, str) and (
        "<" in config_output_root or ">" in config_output_root
    )
    metadata["release_status"] = "not_released"
    metadata["training_status"] = "training_blocked_by_output_policy"
    metadata["trainer_available"] = False
    metadata["heavy_training_gate"]["will_run_heavy_training"] = False
    if unresolved_template:
        metadata["notes"] = (
            f"{stage.upper()} heavy training was blocked because config output_root is an unresolved output_root "
            "template. Create a private A100 override that resolves it before running heavy training."
        )
    else:
        metadata["notes"] = (
            f"{stage.upper()} heavy training was blocked because the requested output directory is outside "
            "configured output_root. A100 smoke outputs must stay under the configured project directory."
        )
    write_json(Path(metadata["metadata_path"]), metadata)
    return metadata


def _training_error_category(exc: Exception) -> str:
    message = str(exc).lower()
    if (
        "network is unreachable" in message
        or "couldn't connect" in message
        or "localentrynotfound" in message
        or "huggingface.co" in message
    ):
        return "model_download_unavailable"
    return "training_failed"


def _write_training_failed(metadata: dict[str, Any], stage: str, exc: Exception) -> None:
    metadata["release_status"] = "not_released"
    metadata["training_status"] = "training_failed"
    metadata["trainer_available"] = True
    metadata["heavy_training_gate"]["will_run_heavy_training"] = False
    metadata["error_category"] = _training_error_category(exc)
    metadata["error_summary"] = "Training failed before completion; raw logs remain private."
    metadata["notes"] = (
        f"{stage.upper()} heavy training failed before completion. Sanitized metadata was written; "
        "raw remote logs, caches, checkpoints, and adapters remain outside git."
    )
    write_json(Path(metadata["metadata_path"]), metadata)


def _lora_config(config: dict[str, Any]) -> Any:
    from peft import LoraConfig  # type: ignore[import-not-found, unused-ignore]

    lora = config.get("lora", {})
    return LoraConfig(
        r=int(lora.get("r", 8)),
        lora_alpha=int(lora.get("alpha", 16)),
        lora_dropout=float(lora.get("dropout", 0.05)),
        target_modules=list(lora.get("target_modules", ["q_proj", "v_proj"])),
        task_type="CAUSAL_LM",
    )


def _training_arguments(config: dict[str, Any], output_dir: Path) -> Any:
    from transformers import TrainingArguments

    return TrainingArguments(
        output_dir=output_dir.as_posix(),
        num_train_epochs=float(config.get("num_train_epochs", 1)),
        per_device_train_batch_size=int(config.get("per_device_train_batch_size", 1)),
        logging_steps=int(config.get("logging_steps", 1)),
        save_strategy=str(config.get("save_strategy", "no")),
        report_to=[],
    )


def _load_sft_training_rows(manifest_path: Path, split: str) -> list[SFTDatasetRow]:
    summary = _manifest_load_summary(manifest_path, "sft")
    dataset_path = summary["dataset_path"]
    if dataset_path is None:
        return []
    return [row for row in (SFTDatasetRow(**record) for record in read_jsonl(Path(dataset_path))) if row.split == split]


def _load_dpo_training_pairs(manifest_path: Path, split: str) -> list[DPOPair]:
    summary = _manifest_load_summary(manifest_path, "dpo")
    dataset_path = summary["dataset_path"]
    if dataset_path is None:
        return []
    return [pair for pair in (DPOPair(**record) for record in read_jsonl(Path(dataset_path))) if pair.split == split]


def _run_real_sft(metadata: dict[str, Any], config: dict[str, Any], manifest_path: Path, output_dir: Path) -> None:
    from datasets import Dataset  # type: ignore[import-not-found, unused-ignore]
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTTrainer  # type: ignore[import-not-found, unused-ignore]

    rows = _load_sft_training_rows(manifest_path, split=str(config.get("dataset_split", "train")))
    texts = [
        "\n".join(f"{message['role']}: {message['content']}" for message in format_sft_messages(row))
        for row in rows
    ]
    dataset = Dataset.from_list([{"text": text} for text in texts])
    tokenizer = AutoTokenizer.from_pretrained(config["base_model"])
    model = AutoModelForCausalLM.from_pretrained(config["base_model"])
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=_training_arguments(config, output_dir),
        peft_config=_lora_config(config),
        dataset_text_field="text",
        max_seq_length=int(config.get("max_seq_length", 1024)),
    )
    trainer.train()
    trainer.model.save_pretrained(metadata["adapter_path"])


def _run_real_dpo(metadata: dict[str, Any], config: dict[str, Any], manifest_path: Path, output_dir: Path) -> None:
    from datasets import Dataset  # type: ignore[import-not-found, unused-ignore]
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import DPOTrainer  # type: ignore[import-not-found, unused-ignore]

    pairs = _load_dpo_training_pairs(manifest_path, split=str(config.get("dataset_split", "train")))
    dataset = Dataset.from_list(
        [
            {
                "prompt": json.dumps(format_dpo_pair(pair)["prompt"], ensure_ascii=False),
                "chosen": format_dpo_pair(pair)["chosen"],
                "rejected": format_dpo_pair(pair)["rejected"],
            }
            for pair in pairs
        ]
    )
    tokenizer = AutoTokenizer.from_pretrained(config["base_model"])
    model = AutoModelForCausalLM.from_pretrained(config["base_model"])
    trainer = DPOTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=_training_arguments(config, output_dir),
        peft_config=_lora_config(config),
        beta=float(config.get("beta", 0.1)),
        max_length=int(config.get("max_seq_length", 1024)),
        max_prompt_length=int(config.get("max_prompt_length", 768)),
    )
    trainer.train()
    trainer.model.save_pretrained(metadata["adapter_path"])


def run_sft(config_path: Path, manifest_path: Path, output_dir: Path, dry_run: bool = True) -> dict[str, Any]:
    config = _load_config(config_path)
    metadata = _metadata_common(
        stage="sft",
        config_path=config_path,
        manifest_path=manifest_path,
        output_dir=output_dir,
        dry_run=dry_run,
    )
    if not dry_run and not _heavy_training_allowed(config):
        return _write_training_skipped(metadata, "sft")
    if not dry_run and not _output_dir_within_configured_root(config, output_dir):
        return _write_training_blocked_by_output_policy(metadata, "sft")
    if not dry_run and not _train_dependencies_available():
        return _write_training_plan(metadata, "sft")
    metadata["trainer_available"] = not dry_run
    if not dry_run:
        try:
            _run_real_sft(metadata, config, manifest_path, output_dir)
        except Exception as exc:
            _write_training_failed(metadata, "sft", exc)
            raise
        metadata["release_status"] = "not_released"
        metadata["training_status"] = "training_completed"
        metadata["notes"] = "SFT training ran locally; adapter metadata is not a public checkpoint release."
    write_json(Path(metadata["metadata_path"]), metadata)
    return metadata


def run_dpo(config_path: Path, manifest_path: Path, output_dir: Path, dry_run: bool = True) -> dict[str, Any]:
    config = _load_config(config_path)
    metadata = _metadata_common(
        stage="dpo",
        config_path=config_path,
        manifest_path=manifest_path,
        output_dir=output_dir,
        dry_run=dry_run,
    )
    metadata["sft_model_ref"] = config.get("sft_model_ref")
    metadata["dpo_initialization"] = "base_model_lora"
    if not dry_run and not _heavy_training_allowed(config):
        return _write_training_skipped(metadata, "dpo")
    if not dry_run and not _output_dir_within_configured_root(config, output_dir):
        return _write_training_blocked_by_output_policy(metadata, "dpo")
    if not dry_run and not _train_dependencies_available():
        return _write_training_plan(metadata, "dpo")
    metadata["trainer_available"] = not dry_run
    if not dry_run:
        try:
            _run_real_dpo(metadata, config, manifest_path, output_dir)
        except Exception as exc:
            _write_training_failed(metadata, "dpo", exc)
            raise
        metadata["release_status"] = "not_released"
        metadata["training_status"] = "training_completed"
        metadata["notes"] = "DPO training ran locally; adapter metadata is not a public checkpoint release."
    write_json(Path(metadata["metadata_path"]), metadata)
    return metadata
