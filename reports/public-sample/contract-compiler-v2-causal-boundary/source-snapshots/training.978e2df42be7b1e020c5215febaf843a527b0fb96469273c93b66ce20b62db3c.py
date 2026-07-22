from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import re
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, cast

from voice2task.copy_backed_prediction_shadow_hook import (
    PredictionShadowHookOutcome,
    load_prediction_shadow_policy_snapshot,
    prediction_shadow_config_error_code,
    run_prediction_shadow_hook,
    shadow_config_from_mapping,
    sidecar_path_conflicts,
    summarize_prediction_shadow_outcomes,
)
from voice2task.formatting import (
    FORMATTING_POLICY,
    UNIFIED_GOLD_FREE_PROMPT_POLICY_ID,
    PredictionInput,
    format_dpo_pair,
    format_schema_retry_prompt_text,
    format_sft_prediction_prompt,
    format_sft_training_text,
    prediction_output_boundary_summary,
    prediction_prompt_constraint_summary,
    prompt_constraint_summary,
    schema_retry_template_boundary_summary,
)
from voice2task.io import read_json, read_jsonl, write_json
from voice2task.schemas import (
    PRIVATE_IP_RE,
    PRIVATE_PATH_RE,
    ROUTES,
    SECRET_RE,
    TASK_TYPES,
    DPOPair,
    SFTDatasetRow,
    as_contract,
    canonical_contract_json,
    validate_contract_status,
)


def _load_config(config_path: Path) -> dict[str, Any]:
    if config_path.suffix != ".json":
        raise ValueError("bootstrap training configs are JSON in this phase")
    return read_json(config_path)


def _resolve_manifest_file(manifest_path: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    relative_candidate = manifest_path.parent / candidate.name
    if relative_candidate.exists():
        return relative_candidate
    if candidate.exists():
        return candidate
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


PRIVATE_PATH_PREFIXES = ("/mnt/data/", "/Users/", "/root/", "/tmp/", "/private/")
_MNT_DATA_PREFIX = "/" + "mnt/data"
PRIVATE_DECODED_PATH_RE = re.compile(rf"({_MNT_DATA_PREFIX}/[^\s\"')]+)")
PRIVATE_METADATA_PATH_RE = re.compile(r"(/(?:mnt/data|Users|root|tmp|private)/[^\s\"')]+)")
MARKDOWN_FENCE_SUPPRESSION_TOKEN_SOURCES = ("```", "```json", "```JSON")


def _public_display_path(value: Path | str, placeholder: str) -> str:
    raw = value.as_posix() if isinstance(value, Path) else str(value)
    if any(raw.startswith(prefix) for prefix in PRIVATE_PATH_PREFIXES):
        return placeholder
    return raw


def _public_display_model(value: Any) -> str:
    if isinstance(value, str) and value:
        return _public_display_path(value, "<private_base_model>")
    return "unknown"


def _public_base_model(config: dict[str, Any]) -> str:
    return str(config.get("base_model_public_id") or config.get("base_model") or "unknown")


def _runtime_base_model(config: dict[str, Any]) -> str:
    return str(config.get("base_model_runtime_path") or config.get("base_model"))


def _public_display_artifact_path(value: Path, placeholder: str) -> str:
    raw = value.as_posix()
    if any(raw.startswith(prefix) for prefix in PRIVATE_PATH_PREFIXES):
        return placeholder
    return raw


def _sanitize_training_metadata_value(value: Any) -> Any:
    if isinstance(value, str):
        sanitized = PRIVATE_METADATA_PATH_RE.sub("<private_path>", value)
        sanitized = PRIVATE_PATH_RE.sub("<private_path>", sanitized)
        sanitized = PRIVATE_IP_RE.sub("<private_ip>", sanitized)
        return SECRET_RE.sub("<secret>", sanitized)
    if isinstance(value, dict):
        return {
            str(_sanitize_training_metadata_value(str(key))): _sanitize_training_metadata_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_training_metadata_value(item) for item in value]
    return value


def _manifest_metadata_without_dataset_load(manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    return {
        "manifest_id": str(manifest.get("manifest_id", manifest_path.stem)),
        "manifest_counts": manifest.get("counts", {}),
        "manifest_public_safe": bool(manifest.get("public_safe", False)),
    }


def _runtime_private_fields(config: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in (
        "adapter_path",
        "evidence_output_dir",
        "output_root",
        "runtime_check_output_dir",
        "private_override_path",
    ):
        value = config.get(key)
        if isinstance(value, str) and value:
            fields[key] = value
    return fields


def _unresolved_runtime_fields(config: dict[str, Any]) -> list[str]:
    return sorted(
        key
        for key, value in _runtime_private_fields(config).items()
        if "<" in value or ">" in value
    )


def _runtime_output_root_policy(config: dict[str, Any], unresolved_fields: list[str]) -> dict[str, Any]:
    raw_output_root = config.get("output_root")
    policy = str(config.get("output_root_policy", config.get("a100_project_root_policy", "")) or "")
    if "output_root" in unresolved_fields:
        status = "blocked_unresolved_template"
    elif isinstance(raw_output_root, str) and raw_output_root:
        status = "resolved_private_override_not_run"
    else:
        status = "missing_output_root"
    return {
        "status": status,
        "approved_policy": policy or "must_resolve_to_approved_private_a100_project_root",
        "output_root": _sanitize_training_metadata_value(raw_output_root or "<missing_output_root>"),
        "public_template_output_root": "<a100_project_root>",
    }


def _runtime_check_output_root_policy(
    config: dict[str, Any],
    output_path: Path,
    unresolved_fields: list[str],
) -> dict[str, Any]:
    runtime_root = config.get("runtime_check_output_dir") or config.get("output_root")
    policy = str(config.get("output_root_policy", config.get("a100_project_root_policy", "")) or "")
    if "output_root" in unresolved_fields or "runtime_check_output_dir" in unresolved_fields:
        status = "blocked_unresolved_template"
    elif _output_file_within_configured_runtime_root(config, output_path):
        status = "approved_private_root"
    else:
        status = "blocked_output_outside_approved_root"
    return {
        "status": status,
        "approved_policy": policy or "must_resolve_to_approved_private_a100_project_root",
        "runtime_check_output_dir": _sanitize_training_metadata_value(
            runtime_root or "<missing_runtime_check_output_dir>"
        ),
        "requested_output": _sanitize_training_metadata_value(output_path.as_posix()),
        "public_template_output_root": "<a100_project_root>",
    }


def _output_file_within_configured_runtime_root(config: dict[str, Any], output_path: Path) -> bool:
    root_value = config.get("runtime_check_output_dir") or config.get("output_root")
    if not isinstance(root_value, str) or not root_value:
        return False
    if "<" in root_value or ">" in root_value:
        return False
    candidate = output_path.expanduser()
    root = Path(root_value).expanduser()
    if not candidate.is_absolute() or not root.is_absolute():
        return False
    candidate = candidate.resolve(strict=False)
    root = root.resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _runtime_check_status(
    *,
    unresolved_fields: list[str],
    config_allows_runtime_check: bool,
) -> str:
    if unresolved_fields:
        return "blocked_unresolved_private_override"
    if not config_allows_runtime_check:
        return "skipped_no_runtime_opt_in"
    return "prepared_private_override_resolved_not_run"


def prepare_sft_runtime_label_provenance(
    config_path: Path,
    manifest_path: Path,
    *,
    metadata_path: Path | None = None,
) -> dict[str, Any]:
    config = _load_config(config_path)
    manifest_summary = _manifest_metadata_without_dataset_load(manifest_path)
    unresolved_fields = _unresolved_runtime_fields(config)
    config_allows_runtime_check = bool(config.get("allow_runtime_label_provenance_check", False))
    private_override_required = bool(config.get("private_override_required", True))
    private_override_resolved = private_override_required and not unresolved_fields
    runtime_check_status = _runtime_check_status(
        unresolved_fields=unresolved_fields,
        config_allows_runtime_check=config_allows_runtime_check,
    )
    evidence_gaps = [
        "runtime_check_not_executed",
        "real_training_labels_not_inspected",
        "real_training_label_provenance_missing",
    ]
    if unresolved_fields:
        evidence_gaps.append("private_override_unresolved")
    if not config_allows_runtime_check:
        evidence_gaps.append("runtime_opt_in_missing")
    metadata = {
        "evidence_kind": "sft_runtime_label_provenance_prep",
        "stage": "sft_runtime_label_provenance_prep",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_path": _sanitize_training_metadata_value(config_path.as_posix()),
        "dataset_manifest_path": _sanitize_training_metadata_value(manifest_path.as_posix()),
        "dataset_manifest_id": manifest_summary["manifest_id"],
        "manifest_counts": manifest_summary["manifest_counts"],
        "manifest_public_safe": manifest_summary["manifest_public_safe"],
        "runtime_check_status": runtime_check_status,
        "runtime_gate": {
            "cli_requested_runtime_check": False,
            "config_allow_runtime_label_provenance_check": config_allows_runtime_check,
            "private_override_resolved": private_override_resolved,
            "will_run_runtime_label_provenance_check": False,
        },
        "private_override": {
            "required": private_override_required,
            "status": "resolved" if private_override_resolved else "unresolved",
            "unresolved_fields": unresolved_fields,
            "requirements": _sanitize_training_metadata_value(config.get("private_override_requirements", [])),
            "public_placeholder": "<a100_project_root>",
        },
        "output_root_policy": _runtime_output_root_policy(config, unresolved_fields),
        "dependency_policy": {
            "policy": str(config.get("dependency_policy", "prep_only_no_train_dependency_import_no_model_download")),
            "train_dependencies_imported": False,
            "model_download_allowed": False,
            "private_adapter_load_allowed": False,
            "a100_connection_allowed": False,
        },
        "label_provenance_intent": {
            "intent": str(
                config.get(
                    "label_provenance_intent",
                    "inspect_real_tokenizer_collator_labels_later",
                )
            ),
            "private_labels_inspected": False,
            "runtime_path": "future_authorized_private_tokenizer_collator_check",
        },
        "label_tensor_available": False,
        "true_label_mask_status": "unavailable",
        "inspection_status": "runtime_check_not_executed",
        "evidence_gaps": _deduped_gaps(evidence_gaps),
        "prior_artifacts": _sanitize_training_metadata_value(config.get("prior_artifacts", {})),
        "claims": {
            "runtime_readiness_proves_contract_learning": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "held_out_generalization_claim": False,
            "production_readiness_claim": False,
            "live_browser_benchmark_claim": False,
        },
        "artifact_policy": {
            "raw_rendered_prompts_written": False,
            "raw_logs_copied_to_git": False,
            "checkpoints_or_adapters_copied_to_git": False,
            "private_paths_omitted": True,
        },
        "metadata_path": metadata_path.as_posix() if metadata_path is not None else "not_written",
        "notes": (
            "Preparation metadata only; no A100/private adapter execution occurred, no model was downloaded, "
            "and no true runtime labels were inspected."
        ),
    }
    sanitized = _sanitize_training_metadata_value(metadata)
    if not isinstance(sanitized, dict):
        raise AssertionError("runtime label provenance prep metadata must be a mapping")
    return cast(dict[str, Any], sanitized)


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


def _loss_mask_policy(stage: str) -> dict[str, Any]:
    if stage == "sft":
        return {
            "policy": "assistant_only_completion_only",
            "prompt_label_id": -100,
            "assistant_target": "browser_task_contract_json",
            "trainer_integration": "trl_sfttrainer_pretokenized_input_ids_attention_mask_labels",
            "full_text_causal_lm_labels": False,
        }
    return {"policy": "dpo_pairwise_preference_loss"}


def _training_stack(stage: str) -> str:
    if stage == "sft":
        return "transformers+peft+trl+pretokenized_assistant_only_labels"
    return "transformers+peft+trl"


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
        "stack": _training_stack(stage),
        "base_model": _public_base_model(config),
        "adapter_path": adapter_path.as_posix(),
        "dataset_manifest_id": load_summary["manifest_id"],
        "dataset_manifest_path": manifest_path.as_posix(),
        "dataset_load": load_summary,
        "hyperparameters": config,
        "dry_run": dry_run,
        "release_status": "not_released",
        "adapter_release_status": "not_released",
        "training_status": "dry_run" if dry_run else "pending_heavy_training",
        "formatting_policy": dict(FORMATTING_POLICY),
        "loss_mask_policy": _loss_mask_policy(stage),
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


def _runtime_label_dependencies_available() -> bool:
    return importlib.util.find_spec("transformers") is not None or globals().get("AutoTokenizer") is not None


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
        max_steps=int(config.get("max_steps", -1)),
        per_device_train_batch_size=int(config.get("per_device_train_batch_size", 1)),
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 1)),
        learning_rate=float(config.get("learning_rate", 5e-5)),
        warmup_ratio=float(config.get("warmup_ratio", 0.0)),
        logging_steps=int(config.get("logging_steps", 1)),
        save_strategy=str(config.get("save_strategy", "no")),
        seed=int(config.get("seed", 42)),
        report_to=[],
    )


def _load_sft_training_rows(manifest_path: Path, split: str) -> list[SFTDatasetRow]:
    summary = _manifest_load_summary(manifest_path, "sft")
    dataset_path = summary["dataset_path"]
    if dataset_path is None:
        return []
    return [row for row in (SFTDatasetRow(**record) for record in read_jsonl(Path(dataset_path))) if row.split == split]


def _configured_sft_training_row_limit(config: dict[str, Any]) -> int | None:
    value = config.get("max_train_rows")
    if value is None:
        return None
    row_limit = int(value)
    if row_limit < 1:
        raise ValueError("max_train_rows must be at least 1 when configured")
    return row_limit


def _configured_sft_training_source_ids(config: dict[str, Any]) -> list[str] | None:
    value = config.get("train_source_ids")
    if value is None:
        return None
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError("train_source_ids must be a non-empty list of source_id strings when configured")
    return list(value)


def _sft_row_source_id(row: SFTDatasetRow) -> str:
    source_id = row.provenance.get("source_id") if isinstance(row.provenance, dict) else None
    return str(source_id or row.id)


def _source_id_counts(rows: list[SFTDatasetRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        source_id = _sft_row_source_id(row)
        counts[source_id] = counts.get(source_id, 0) + 1
    return dict(sorted(counts.items()))


def _limited_sft_training_rows(
    rows: list[SFTDatasetRow],
    config: dict[str, Any],
) -> tuple[list[SFTDatasetRow], int | None, list[str] | None, int, int]:
    source_ids = _configured_sft_training_source_ids(config)
    rows_before_source_filter = len(rows)
    if source_ids is not None:
        source_id_set = set(source_ids)
        rows = [row for row in rows if _sft_row_source_id(row) in source_id_set]
    rows_before_limit = len(rows)
    row_limit = _configured_sft_training_row_limit(config)
    if row_limit is None:
        return rows, None, source_ids, rows_before_source_filter, rows_before_limit
    return rows[:row_limit], row_limit, source_ids, rows_before_source_filter, rows_before_limit


def _record_sft_training_row_selection(
    metadata: dict[str, Any],
    *,
    split: str,
    rows: list[SFTDatasetRow],
    row_limit: int | None,
    source_ids: list[str] | None,
    loaded_rows_before_limit: int,
    loaded_rows_before_source_filter: int,
) -> None:
    row_ids = [row.id for row in rows]
    metadata["training_split"] = split
    metadata["training_source_ids"] = source_ids
    metadata["training_row_limit"] = row_limit
    metadata["training_rows_used"] = len(rows)
    metadata["training_row_ids"] = row_ids
    metadata["training_source_id_counts"] = _source_id_counts(rows)
    metadata["training_rows_before_source_filter"] = loaded_rows_before_source_filter
    dataset_load = metadata.setdefault("dataset_load", {})
    if isinstance(dataset_load, dict):
        dataset_load["training_split"] = split
        dataset_load["training_source_ids"] = source_ids
        dataset_load["training_row_limit"] = row_limit
        dataset_load["training_rows_used"] = len(rows)
        dataset_load["training_row_ids"] = row_ids
        dataset_load["training_source_id_counts"] = _source_id_counts(rows)
        dataset_load["training_rows_before_source_filter"] = loaded_rows_before_source_filter
        dataset_load["loaded_rows_before_training_row_limit"] = loaded_rows_before_limit


def _record_sft_training_selection_from_config(
    metadata: dict[str, Any],
    config: dict[str, Any],
    manifest_path: Path,
) -> list[SFTDatasetRow]:
    split = str(config.get("dataset_split", "train"))
    all_rows = _load_sft_training_rows(manifest_path, split=split)
    rows, row_limit, source_ids, rows_before_source_filter, rows_before_limit = _limited_sft_training_rows(
        all_rows, config
    )
    _record_sft_training_row_selection(
        metadata,
        split=split,
        rows=rows,
        row_limit=row_limit,
        source_ids=source_ids,
        loaded_rows_before_limit=rows_before_limit,
        loaded_rows_before_source_filter=rows_before_source_filter,
    )
    return rows


def _target_token_count(records: list[dict[str, Any]]) -> int:
    total = 0
    for record in records:
        labels = _token_list(record.get("labels"))
        total += sum(1 for label in labels if label != -100)
    return total


def _safe_training_metric_value(value: Any) -> int | float | str | bool | None:
    if value is None or isinstance(value, str | bool):
        return value
    if isinstance(value, int | float):
        return value
    return str(value)


def _observed_optimizer_steps(trainer: Any, train_result: Any) -> int | None:
    state = getattr(trainer, "state", None)
    value = getattr(state, "global_step", None)
    if value is None:
        value = getattr(train_result, "global_step", None)
    if value is None:
        metrics = getattr(train_result, "metrics", None)
        if isinstance(metrics, dict):
            value = metrics.get("global_step")
    if isinstance(value, int | float):
        return int(value)
    return None


def _record_sft_training_budget_metadata(
    metadata: dict[str, Any],
    *,
    config: dict[str, Any],
    train_row_count: int,
    records: list[dict[str, Any]],
    trainer: Any,
    train_result: Any,
) -> None:
    effective_batch_size = int(config.get("per_device_train_batch_size", 1)) * int(
        config.get("gradient_accumulation_steps", 1)
    )
    configured_max_steps = int(config.get("max_steps", -1))
    observed_steps = _observed_optimizer_steps(trainer, train_result)
    step_budget = observed_steps if observed_steps is not None else configured_max_steps
    if step_budget > 0:
        theoretical_examples_seen = step_budget * effective_batch_size
    else:
        theoretical_examples_seen = int(round(train_row_count * float(config.get("num_train_epochs", 1))))
    target_tokens_per_single_pass = _target_token_count(records)
    target_tokens_seen_estimate = (
        int(round(target_tokens_per_single_pass * theoretical_examples_seen / train_row_count))
        if train_row_count
        else 0
    )
    metrics = getattr(train_result, "metrics", None)
    metadata["training_budget"] = {
        "configured_max_steps": configured_max_steps,
        "observed_optimizer_steps": observed_steps,
        "num_train_epochs": float(config.get("num_train_epochs", 1)),
        "per_device_train_batch_size": int(config.get("per_device_train_batch_size", 1)),
        "gradient_accumulation_steps": int(config.get("gradient_accumulation_steps", 1)),
        "effective_batch_size": effective_batch_size,
        "scheduler_max_steps": configured_max_steps if configured_max_steps > 0 else None,
        "train_row_count": train_row_count,
        "theoretical_examples_seen": theoretical_examples_seen,
        "target_tokens_per_single_pass": target_tokens_per_single_pass,
        "target_tokens_seen_estimate": target_tokens_seen_estimate,
        "target_tokens_seen_status": "estimated_from_label_tokens_and_step_budget",
        "step_matching_unit": "optimizer_steps",
        "step_matched_not_token_matched": True,
    }
    metadata["observed_optimizer_steps"] = observed_steps
    metadata["target_tokens_seen"] = target_tokens_seen_estimate
    metadata["target_tokens_seen_status"] = "estimated_from_label_tokens_and_step_budget"
    if isinstance(metrics, dict):
        metadata["train_result_metrics"] = {
            str(key): _safe_training_metric_value(value) for key, value in sorted(metrics.items())
        }


def _load_sft_prediction_rows(manifest_path: Path, split: str) -> list[SFTDatasetRow]:
    summary = _manifest_load_summary(manifest_path, "sft")
    dataset_path = summary["dataset_path"]
    if dataset_path is None:
        return []
    rows = [SFTDatasetRow(**record) for record in read_jsonl(Path(dataset_path))]
    if split == "all":
        return rows
    return [row for row in rows if row.split == split]


def _configured_sft_prediction_row_limit(config: dict[str, Any]) -> int | None:
    value = config.get("max_prediction_rows")
    if value is None:
        return None
    row_limit = int(value)
    if row_limit < 1:
        raise ValueError("max_prediction_rows must be at least 1 when configured")
    return row_limit


def _limited_sft_prediction_rows(
    rows: list[SFTDatasetRow],
    config: dict[str, Any],
) -> tuple[list[SFTDatasetRow], int | None]:
    row_limit = _configured_sft_prediction_row_limit(config)
    if row_limit is None:
        return rows, None
    return rows[:row_limit], row_limit


def _record_sft_prediction_row_selection(
    metadata: dict[str, Any],
    *,
    rows: list[SFTDatasetRow],
    row_limit: int | None,
    loaded_rows_before_limit: int,
) -> None:
    metadata["prediction_row_limit"] = row_limit
    metadata["prediction_row_ids"] = [row.id for row in rows]
    metadata["prediction_rows_before_limit"] = loaded_rows_before_limit


def _prediction_gate(config: dict[str, Any], dry_run: bool, fixture_mode: bool) -> dict[str, bool]:
    config_allows = bool(config.get("allow_private_prediction"))
    adapter_configured = isinstance(config.get("adapter_path"), str) and bool(str(config.get("adapter_path")).strip())
    return {
        "cli_run_prediction": not dry_run,
        "fixture_mode": fixture_mode,
        "config_allow_private_prediction": config_allows,
        "adapter_configured": adapter_configured,
        "will_run_private_prediction": (not dry_run) and (not fixture_mode) and config_allows and adapter_configured,
    }


def _decoding_policy(config: dict[str, Any]) -> dict[str, Any]:
    schema_retry_enabled = bool(config.get("schema_retry_enabled", True))
    return {
        "strategy": "greedy",
        "do_sample": False,
        "max_new_tokens": int(config.get("max_new_tokens", 256)),
        "markdown_fence_suppression_enabled": True,
        "markdown_fence_suppression_strategy": "bad_words_ids",
        "markdown_fence_suppression_token_sources": list(MARKDOWN_FENCE_SUPPRESSION_TOKEN_SOURCES),
        "raw_decoded_sidecar_written": False,
        "generation_trace_sidecar_written": False,
        "schema_repair_applied": False,
        "schema_guard_enabled": True,
        "schema_retry_enabled": schema_retry_enabled,
        "schema_retry_max_attempts": 1 if schema_retry_enabled else 0,
    }


def _prediction_sidecar_paths(output_path: Path) -> dict[str, Path]:
    return {
        "prompt_snapshot": output_path.parent / "prompt_snapshot.json",
        "raw_decoded_summary": output_path.parent / "raw_decoded_summary.jsonl",
        "generation_trace": output_path.parent / "generation_trace.jsonl",
    }


def _public_sidecar_paths(sidecar_paths: dict[str, Path]) -> dict[str, str]:
    placeholders = {
        "prompt_snapshot": "<a100_prompt_snapshot>",
        "raw_decoded_summary": "<a100_raw_decoded_summary>",
        "generation_trace": "<a100_generation_trace>",
    }
    return {
        name: _public_display_artifact_path(path, placeholders.get(name, "<a100_prediction_sidecar>"))
        for name, path in sidecar_paths.items()
    }


def _diagnostic_artifact_paths(output_path: Path, *, overfit_diagnostic: bool) -> dict[str, str]:
    if not overfit_diagnostic:
        return {}
    return {
        "objective_inspection": _public_display_artifact_path(
            output_path.parent / "objective_inspection.json",
            "<a100_objective_inspection>",
        ),
        "leak_scan": _public_display_artifact_path(
            output_path.parent / "leak_scan_result.json",
            "<a100_leak_scan_result>",
        ),
    }


def _prediction_metadata_common(
    *,
    config_path: Path,
    manifest_path: Path,
    output_path: Path,
    dry_run: bool,
    fixture_mode: bool,
) -> dict[str, Any]:
    config = _load_config(config_path)
    load_summary = _manifest_load_summary(manifest_path, "sft")
    sidecar_paths = _prediction_sidecar_paths(output_path)
    return {
        "stage": "sft_prediction",
        "stack": "transformers+peft+trl",
        "base_model": _public_display_model(_public_base_model(config)),
        "model_source": config.get("model_source", "unknown"),
        "dataset_manifest_id": load_summary["manifest_id"],
        "dataset_manifest_path": _public_display_path(manifest_path, "data/public-samples/manifest_public_sample.json"),
        "prediction_output_path": _public_display_path(output_path, "<a100_prediction_output>"),
        "prediction_split": str(config.get("prediction_split", "all")),
        "overfit_diagnostic": bool(config.get("overfit_diagnostic", False)),
        "generalization_claim": bool(config.get("generalization_claim", False)),
        "prediction_source_kind": "none",
        "prediction_status": "pending",
        "prediction_count": 0,
        "release_status": "not_released",
        "adapter_release_status": "not_released",
        "formatting_policy": dict(FORMATTING_POLICY),
        "prompt_policy": UNIFIED_GOLD_FREE_PROMPT_POLICY_ID,
        "prompt_constraints": prediction_prompt_constraint_summary(),
        "prediction_output_boundary": prediction_output_boundary_summary(),
        "retry_prompt_constraints": schema_retry_prompt_constraint_summary(),
        "retry_template_boundary": schema_retry_template_boundary_summary(),
        "decoding_policy": _decoding_policy(config),
        "sidecars": _public_sidecar_paths(sidecar_paths),
        "diagnostic_artifacts": _diagnostic_artifact_paths(
            output_path,
            overfit_diagnostic=bool(config.get("overfit_diagnostic", False)),
        ),
        "metadata_path": _public_display_artifact_path(
            output_path.parent / "prediction_metadata.json",
            "<a100_prediction_metadata>",
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prediction_gate": _prediction_gate(config, dry_run, fixture_mode),
        "command_summary": {
            "entrypoint": "voice2task-train sft-predict",
            "config": _public_display_path(config_path, "<private_prediction_config>"),
            "manifest": _public_display_path(manifest_path, "data/public-samples/manifest_public_sample.json"),
            "output": _public_display_path(output_path, "<a100_prediction_output>"),
            "mode": "fixture_mode" if fixture_mode else ("dry_run" if dry_run else "run_prediction"),
            "requires_cli_run_prediction": not dry_run,
            "requires_config_allow_private_prediction": True,
            "prompt_policy": UNIFIED_GOLD_FREE_PROMPT_POLICY_ID,
        },
        "notes": "Prediction metadata only; no private adapter artifacts were loaded.",
    }


def _write_fixture_predictions(rows: list[SFTDatasetRow], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "id": row.id,
            "prediction": as_contract(row.target_contract).to_dict(),
            "prediction_source_kind": "public_sample_contract_fixture",
            "provenance": {"public_safe": True, "source_id": row.provenance.get("source_id", row.id)},
        }
        for row in rows
    ]
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return len(records)


def _run_copy_backed_prediction_shadow_hook(
    *,
    config: dict[str, Any],
    config_path: Path,
    rows: list[SFTDatasetRow],
    output_path: Path,
) -> dict[str, Any] | None:
    if "copy_backed_shadow" not in config:
        return None
    hook_config = shadow_config_from_mapping(
        config.get("copy_backed_shadow"),
        config_dir=config_path.parent,
        output_dir=output_path.parent,
    )
    if not hook_config.enabled:
        return summarize_prediction_shadow_outcomes([], enabled=False)
    row_by_id = {row.id: row for row in rows}
    outcomes: list[PredictionShadowHookOutcome] = []
    reserved_artifact_paths = [
        output_path,
        output_path.parent / "prediction_metadata.json",
        *_prediction_sidecar_paths(output_path).values(),
    ]
    path_conflict = sidecar_path_conflicts(hook_config.sidecar_output_path, reserved_artifact_paths)
    policy_snapshot = None
    policy_error_code = None
    if prediction_shadow_config_error_code(hook_config) is None and not path_conflict:
        try:
            policy_snapshot = load_prediction_shadow_policy_snapshot(hook_config)
        except Exception:
            policy_error_code = "policy_load_or_validation_failed"
    for record in read_jsonl(output_path):
        row_id = str(record.get("id", ""))
        source_row = row_by_id.get(row_id)
        outcomes.append(
            run_prediction_shadow_hook(
                source_text=source_row.input_text if source_row is not None else None,
                prediction=record.get("prediction"),
                config=hook_config,
                request_id=row_id,
                policy_snapshot=policy_snapshot,
                policy_error_code=policy_error_code,
                sidecar_path_conflict=path_conflict,
            )
        )
    return summarize_prediction_shadow_outcomes(outcomes, enabled=True, policy_snapshot=policy_snapshot)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sanitize_preview(text: str, limit: int = 240) -> str:
    return _sanitize_decoded_prediction_text(text)[:limit]


def _prompt_snapshot_row(row: SFTDatasetRow, prompt: str) -> dict[str, Any]:
    sanitized_prompt = _sanitize_decoded_prediction_text(prompt)
    return {
        "id": row.id,
        "prompt_sha256": _sha256_text(sanitized_prompt),
        "prompt_char_count": len(sanitized_prompt),
        "prompt_preview": sanitized_prompt[:240],
        "prompt_constraints": prompt_constraint_summary(sanitized_prompt),
        "input_text_preview": _sanitize_preview(row.input_text, limit=120),
        "provenance": {"public_safe": True, "source_id": row.provenance.get("source_id", row.id)},
    }


def _write_prompt_snapshot(
    rows: list[dict[str, Any]],
    path: Path,
    *,
    prediction_split: str,
    decoding_policy: dict[str, Any],
) -> None:
    write_json(
        path,
        {
            "artifact_kind": "sft_prediction_prompt_snapshot",
            "prediction_split": prediction_split,
            "formatting_policy": dict(FORMATTING_POLICY),
            "prompt_policy": UNIFIED_GOLD_FREE_PROMPT_POLICY_ID,
            "prompt_constraints": prediction_prompt_constraint_summary(),
            "prediction_output_boundary": prediction_output_boundary_summary(),
            "retry_prompt_constraints": schema_retry_prompt_constraint_summary(),
            "retry_template_boundary": schema_retry_template_boundary_summary(),
            "decoding_policy": dict(decoding_policy),
            "rows": rows,
            "claims": {
                "prompt_snapshot_only": True,
                "contains_gold_contract": False,
                "public_safe": True,
            },
        },
    )


def _decoded_parse_status(decoded: str) -> str:
    stripped = decoded.strip()
    if not stripped:
        return "empty"
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None
    else:
        return "json_object" if isinstance(parsed, dict) else "json_non_object"
    object_start = stripped.find("{")
    object_end = stripped.rfind("}")
    if object_start >= 0 and object_end > object_start:
        try:
            parsed = json.loads(stripped[object_start : object_end + 1])
        except json.JSONDecodeError:
            return "non_json"
        return "json_fragment_object" if isinstance(parsed, dict) else "json_fragment_non_object"
    return "non_json"


def _decoded_attempt_summary(decoded: str) -> dict[str, Any]:
    sanitized = _sanitize_decoded_prediction_text(decoded)
    return {
        "parse_status": _decoded_parse_status(sanitized),
        "decoded_sha256": _sha256_text(sanitized),
        "decoded_char_count": len(sanitized),
        "decoded_prefix": sanitized[:240],
        "decoded_suffix": sanitized[-240:],
        "private_values_sanitized": sanitized != decoded,
    }


def _raw_decoded_summary_row(
    row_id: str,
    decoded: str,
    *,
    schema_guard: dict[str, Any] | None = None,
    retry_decoded: str | None = None,
) -> dict[str, Any]:
    raw_attempt = _decoded_attempt_summary(decoded)
    row = {
        "id": row_id,
        **raw_attempt,
        "raw_attempt": raw_attempt,
        "retry_attempt": _decoded_attempt_summary(retry_decoded) if retry_decoded is not None else None,
        "schema_repair_applied": False,
    }
    if schema_guard is not None:
        row["schema_guard"] = schema_guard
    return row


def _write_jsonl_records(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _sidecar_written_decoding_policy(config: dict[str, Any]) -> dict[str, Any]:
    policy = _decoding_policy(config)
    policy["raw_decoded_sidecar_written"] = True
    policy["generation_trace_sidecar_written"] = True
    return policy


def _token_list(value: Any) -> list[Any]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, list):
        if len(value) == 1 and isinstance(value[0], (list, tuple)):
            return list(value[0])
        return value
    return []


def _generation_trace_row(
    *,
    row_id: str,
    attempt: str,
    prediction_source_kind: str,
    generated_tokens: Any,
    max_new_tokens: int,
    eos_token_id: Any,
    finish_state: str | None = None,
) -> dict[str, Any]:
    tokens = _token_list(generated_tokens)
    eos_seen = eos_token_id is not None and eos_token_id in tokens
    max_new_tokens_hit = max_new_tokens > 0 and len(tokens) >= max_new_tokens
    resolved_finish_state = finish_state or ("eos_observed" if eos_seen else "no_eos_observed")
    finish_state_basis = "explicit_fixture_status" if finish_state else "tokenizer_eos_membership"
    if finish_state == "fixture_no_generation":
        stop_reason_evidence = "fixture_no_generation"
    elif eos_seen:
        stop_reason_evidence = "tokenizer_eos_observed"
    elif max_new_tokens_hit:
        stop_reason_evidence = "max_new_tokens_reached_without_tokenizer_eos"
    else:
        stop_reason_evidence = "not_recorded_below_max_without_tokenizer_eos"
    return {
        "id": row_id,
        "attempt": attempt,
        "prediction_source_kind": prediction_source_kind,
        "strategy": "greedy",
        "do_sample": False,
        "max_new_tokens": max_new_tokens,
        "generated_token_count": len(tokens),
        "max_new_tokens_hit": max_new_tokens_hit,
        "eos_token_id_available": eos_token_id is not None,
        "eos_token_seen": eos_seen,
        "finish_state": resolved_finish_state,
        "finish_state_basis": finish_state_basis,
        "stop_reason_evidence": stop_reason_evidence,
        "actual_stop_reason_recorded": False,
        "actual_stop_reason": None,
    }


def _write_fixture_sidecars(
    *,
    rows: list[SFTDatasetRow],
    output_path: Path,
    sidecar_paths: dict[str, Path],
    prediction_split: str,
    max_new_tokens: int,
    decoding_policy: dict[str, Any],
) -> None:
    prompt_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    for row in rows:
        prompt = format_sft_prediction_prompt(PredictionInput.from_sft_row(row), tokenizer=None)
        prompt_rows.append(_prompt_snapshot_row(row, prompt))
        decoded = json.dumps(as_contract(row.target_contract).to_dict(), ensure_ascii=False, sort_keys=True)
        raw_rows.append(_raw_decoded_summary_row(row.id, decoded))
        trace_rows.append(
            _generation_trace_row(
                row_id=row.id,
                attempt="raw_attempt",
                prediction_source_kind="public_sample_contract_fixture",
                generated_tokens=[],
                max_new_tokens=max_new_tokens,
                eos_token_id=None,
                finish_state="fixture_no_generation",
            )
        )
    _write_prompt_snapshot(
        prompt_rows,
        sidecar_paths["prompt_snapshot"],
        prediction_split=prediction_split,
        decoding_policy=decoding_policy,
    )
    _write_jsonl_records(sidecar_paths["raw_decoded_summary"], raw_rows)
    _write_jsonl_records(sidecar_paths["generation_trace"], trace_rows)


def _mark_sidecars_written(metadata: dict[str, Any]) -> None:
    metadata["decoding_policy"]["raw_decoded_sidecar_written"] = True
    metadata["decoding_policy"]["generation_trace_sidecar_written"] = True


def _write_prediction_metadata(output_path: Path, metadata: dict[str, Any]) -> None:
    write_json(output_path.parent / "prediction_metadata.json", metadata)


def _write_private_prediction_unavailable(metadata: dict[str, Any]) -> dict[str, Any]:
    metadata["prediction_status"] = "prediction_unavailable_private_runtime"
    metadata["prediction_source_kind"] = "private_adapter_not_run_locally"
    metadata["prediction_gate"]["will_run_private_prediction"] = False
    metadata["notes"] = (
        "Private trained-adapter prediction requires the A100 runtime, train dependencies, and a private adapter "
        "path. No public predictions were written by this local command."
    )
    return metadata


def _prediction_dependencies_available() -> bool:
    return all(importlib.util.find_spec(module) is not None for module in ("peft", "torch", "transformers"))


def _extract_json_object(text: str) -> Any:
    stripped = text.strip()
    if stripped:
        try:
            return _sanitize_prediction_value(json.loads(stripped))
        except json.JSONDecodeError:
            pass
    object_start = stripped.find("{")
    object_end = stripped.rfind("}")
    if object_start >= 0 and object_end > object_start:
        try:
            parsed = json.loads(stripped[object_start : object_end + 1])
        except json.JSONDecodeError:
            pass
        else:
            return _sanitize_prediction_value(parsed)
    return _sanitize_decoded_prediction_text(stripped)


def _extract_strict_json_object(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return ""
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return _sanitize_decoded_prediction_text(stripped)
    return _sanitize_prediction_value(parsed)


def _required_field_missing(prediction: Any) -> list[str]:
    required = {
        "task_type",
        "route",
        "safety",
        "confirmation_required",
        "slots",
        "normalized_command",
        "language",
        "contract_version",
    }
    if not isinstance(prediction, dict):
        return sorted(required)
    return sorted(required - set(prediction))


def _schema_guard_status(prediction: Any) -> dict[str, Any]:
    return validate_contract_status(prediction)


def _schema_retry_prompt(prediction_input: PredictionInput, raw_prediction: Any, guard_status: dict[str, Any]) -> str:
    if not isinstance(prediction_input, PredictionInput):
        raise TypeError("schema retry prompt rendering requires PredictionInput")
    missing = guard_status.get("missing_required_fields", [])
    missing_text = ", ".join(str(field) for field in missing) if missing else "unknown"
    extra = guard_status.get("extra_top_level_fields", [])
    extra_text = ", ".join(str(field) for field in extra) if extra else "none"
    validation_error = str(guard_status.get("validation_error") or "unknown")
    raw_summary = json.dumps(_sanitize_prediction_value(raw_prediction), ensure_ascii=False, sort_keys=True)
    canonical_skeleton = json.dumps(
        {
            "task_type": "search",
            "route": "search_web",
            "safety": {"allow": True, "reason": "public_readonly"},
            "confirmation_required": False,
            "slots": {},
            "normalized_command": prediction_input.input_text,
            "language": "zh-CN",
            "contract_version": "v1",
        },
        ensure_ascii=False,
    )
    return "\n".join(
        [
            "你刚才输出的 JSON 不是合法 Browser Task Contract。",
            f"缺失字段: {missing_text}。",
            f"额外顶层字段: {extra_text}。",
            f"schema 违规摘要: {validation_error}。",
            "如果存在额外顶层字段，必须删除；root object 只能包含规定的 8 个顶层字段。",
            f"合法 task_type enum: {', '.join(sorted(TASK_TYPES))}。",
            f"合法 route enum: {', '.join(sorted(ROUTES))}。",
            "请重新输出一个完整 Browser Task Contract JSON object，必须包含全部 8 个顶层字段：",
            "task_type, route, safety, confirmation_required, slots, normalized_command, language, contract_version。",
            f"Canonical required skeleton: {canonical_skeleton}",
            "safety 必须是 object，且包含 boolean safety.allow 和非空字符串 safety.reason。",
            "route 是 enum，不是 URL/path；不要输出 /weather、https://...、www... 或文件路径。",
            "task_type 不能使用 search_web、open_url、query_weather_request，也不能使用 app/action name。",
            "public-readonly search: task_type 必须是 search，不能是 search_web；route 必须是 search_web。",
            "只输出一个 minified JSON object；全部 8 个顶层字段必须都在同一个 root object 内。",
            "Retry response must be exactly one JSON object and nothing else.",
            "No text outside the root JSON object; no preamble, wrapper, suffix, or trailing analysis.",
            "Return a machine-readable only retry response; do not include human-facing commentary.",
            "Retry template mode: machine_contract_regeneration.",
            "Treat this as a machine-only retry turn, not a conversational assistant answer.",
            "Assistant output boundary: assistant JSON payload only.",
            "Strict whole-object parser boundary: wrapped fragments remain invalid.",
            "不要在 normalized_command 之前提前关闭 root object。",
            "第一个非空字符必须是 `{`；最后一个非空字符必须是 `}`。",
            "不要 Markdown/code fences/prose；不要解释、不要自然语言前后缀。",
            "不要输出任何前缀或后缀文本；不要以“这是”或“以下”开头；不要使用 Here is。",
            "不要使用自然语言 wrapper/preamble，例如“这是”、“以下”或 Here is。",
            "不要在 JSON 后添加解释、分析或用户输入复述；不要输出第二个 JSON object。",
            "否则 strict parser 会拒绝 retry attempt。",
            f"用户输入: {prediction_input.input_text}",
            f"上一轮输出摘要: {raw_summary[:500]}",
        ]
    )


def schema_retry_prompt_constraint_summary(prompt: str | None = None) -> dict[str, bool]:
    if prompt is None:
        row = SFTDatasetRow(
            id="retry-constraint-summary",
            split="test",
            input_text="帮我搜索北京明天的天气",
            target_contract={
                "task_type": "search",
                "route": "search_web",
                "safety": {"allow": True, "reason": "public_readonly"},
                "confirmation_required": False,
                "slots": {"query": "北京 明天 天气"},
                "normalized_command": "搜索北京明天天气",
                "language": "zh-CN",
                "contract_version": "v1",
            },
            provenance={"source_id": "retry-constraint-summary", "public_safe": True},
        )
        raw_prediction = {
            "route": "search_web",
            "safety": {"allow": True, "reason": "public_readonly"},
            "confirmation_required": False,
            "slots": {"query": "北京明天天气"},
            "normalized_command": "搜索北京明天天气",
            "language": "zh-CN",
            "contract_version": "v1",
        }
        prompt = _schema_retry_prompt(
            PredictionInput.from_sft_row(row),
            raw_prediction,
            _schema_guard_status(raw_prediction),
        )
    return {
        "minified_json_only_visible": "只输出一个 minified JSON object" in prompt,
        "single_root_json_object_visible": "同一个 root object" in prompt,
        "first_last_brace_visible": "第一个非空字符必须是 `{`" in prompt
        and "最后一个非空字符必须是 `}`" in prompt,
        "no_markdown_prose_visible": "不要 Markdown/code fences/prose" in prompt,
        "no_prefix_suffix_text_visible": "不要输出任何前缀或后缀文本" in prompt,
        "no_zh_this_following_prefix_visible": "不要以“这是”或“以下”开头" in prompt,
        "no_here_is_visible": "不要使用 Here is" in prompt,
        "no_trailing_analysis_visible": "不要在 JSON 后添加解释、分析或用户输入复述" in prompt,
        "no_second_json_object_visible": "不要输出第二个 JSON object" in prompt,
        "exact_json_only_output_visible": "Retry response must be exactly one JSON object and nothing else" in prompt,
        "no_text_outside_root_json_object_visible": "No text outside the root JSON object" in prompt,
        "no_natural_language_wrapper_or_preamble_visible": "不要使用自然语言 wrapper/preamble" in prompt,
        "machine_readable_only_retry_response_visible": "machine-readable only retry response" in prompt,
        "strict_parser_rejection_warning_visible": "否则 strict parser 会拒绝 retry attempt" in prompt,
        "task_type_search_not_search_web_visible": "task_type 必须是 search，不能是 search_web" in prompt,
    }


def _encode_suppression_sequence(tokenizer: Any, text: str) -> list[int]:
    encode = getattr(tokenizer, "encode", None)
    if callable(encode):
        try:
            encoded = encode(text, add_special_tokens=False)
        except TypeError:
            encoded = encode(text)
        if isinstance(encoded, list):
            return [int(token_id) for token_id in encoded if isinstance(token_id, int)]
    if callable(tokenizer):
        try:
            encoded_mapping = tokenizer(text, add_special_tokens=False)
        except TypeError:
            return []
        input_ids = encoded_mapping.get("input_ids") if isinstance(encoded_mapping, dict) else None
        if isinstance(input_ids, list):
            return [int(token_id) for token_id in input_ids if isinstance(token_id, int)]
    return []


def _markdown_fence_bad_words_ids(tokenizer: Any) -> list[list[int]]:
    sequences: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for source in MARKDOWN_FENCE_SUPPRESSION_TOKEN_SOURCES:
        token_ids = _encode_suppression_sequence(tokenizer, source)
        sequence_key = tuple(token_ids)
        if len(token_ids) == 1 and sequence_key not in seen:
            sequences.append(token_ids)
            seen.add(sequence_key)
    return sequences


def _decode_prediction_attempt(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    max_new_tokens: int,
    torch_module: Any,
) -> tuple[str, Any, Any]:
    inputs: Any = tokenizer(prompt, return_tensors="pt").to(model.device)
    bad_words_ids = _markdown_fence_bad_words_ids(tokenizer)
    generation_kwargs: dict[str, Any] = {
        **inputs,
        "max_new_tokens": max_new_tokens,
        "do_sample": False,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if bad_words_ids:
        generation_kwargs["bad_words_ids"] = bad_words_ids
    with torch_module.no_grad():
        generated: Any = model.generate(**generation_kwargs)
    new_tokens = generated[0][inputs["input_ids"].shape[-1] :]
    decoded_value = tokenizer.decode(new_tokens, skip_special_tokens=True)
    decoded = decoded_value if isinstance(decoded_value, str) else str(decoded_value)
    return decoded, new_tokens, inputs


def _merge_and_unload_if_available(model: Any) -> Any:
    merge_and_unload = getattr(model, "merge_and_unload", None)
    if callable(merge_and_unload):
        return merge_and_unload()
    return model


def _build_schema_guard(
    *,
    raw_status: dict[str, Any],
    retry_enabled: bool,
    retry_attempted: bool,
    retry_status: dict[str, Any] | None,
) -> dict[str, Any]:
    retry_schema_valid = None if retry_status is None else retry_status["schema_valid"]
    if raw_status["schema_valid"]:
        validated_source = "raw_attempt"
        validated_valid = True
    elif retry_status is not None and retry_status["schema_valid"]:
        validated_source = "retry_attempt"
        validated_valid = True
    else:
        validated_source = "none"
        validated_valid = False
    return {
        "raw_attempt_schema_valid": raw_status["schema_valid"],
        "raw_attempt_validation_error": raw_status["validation_error"],
        "raw_attempt_missing_required_fields": raw_status["missing_required_fields"],
        "retry_enabled": retry_enabled,
        "retry_attempted": retry_attempted,
        "retry_attempt_schema_valid": retry_schema_valid,
        "retry_attempt_validation_error": None if retry_status is None else retry_status["validation_error"],
        "validated_output_schema_valid": validated_valid,
        "validated_output_source": validated_source,
    }


def _sanitize_prediction_object(value: dict[str, Any]) -> dict[str, Any]:
    return {
        _sanitize_decoded_prediction_text(key): _sanitize_prediction_value(item)
        for key, item in value.items()
    }


def _sanitize_prediction_value(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_decoded_prediction_text(value)
    if isinstance(value, dict):
        return _sanitize_prediction_object(value)
    if isinstance(value, list):
        return [_sanitize_prediction_value(item) for item in value]
    return value


def _sanitize_decoded_prediction_text(text: str) -> str:
    sanitized = PRIVATE_METADATA_PATH_RE.sub("<private_path>", text)
    sanitized = PRIVATE_PATH_RE.sub("<private_path>", sanitized)
    sanitized = PRIVATE_IP_RE.sub("<private_ip>", sanitized)
    sanitized = SECRET_RE.sub("<secret>", sanitized)
    return sanitized


def _run_real_sft_prediction(
    config: dict[str, Any],
    rows: list[SFTDatasetRow],
    output_path: Path,
    *,
    sidecar_paths: dict[str, Path] | None = None,
) -> int:
    import torch
    from peft import PeftModel  # type: ignore[import-not-found, unused-ignore]
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_model = _runtime_base_model(config)
    adapter_path = str(config["adapter_path"])
    tokenizer: Any = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    sft_adapter_path = config.get("sft_adapter_path")
    if sft_adapter_path:
        model: Any = AutoModelForCausalLM.from_pretrained(
            base_model, torch_dtype=dtype, trust_remote_code=True,
        )
        model = PeftModel.from_pretrained(model, sft_adapter_path)
        model = _merge_and_unload_if_available(model)
        if hasattr(model, "peft_config"):
            del model.peft_config
        model = PeftModel.from_pretrained(model, adapter_path)
        model = _merge_and_unload_if_available(model)
        model = model.to("cuda" if torch.cuda.is_available() else "cpu")
    else:
        model = AutoModelForCausalLM.from_pretrained(
            base_model, device_map="auto", torch_dtype=dtype, trust_remote_code=True,
        )
        model = PeftModel.from_pretrained(model, adapter_path)
        model = _merge_and_unload_if_available(model)
    model.eval()
    max_new_tokens = int(config.get("max_new_tokens", 256))
    schema_retry_enabled = bool(config.get("schema_retry_enabled", True))
    prompt_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            prediction_input = PredictionInput.from_sft_row(row)
            prompt = format_sft_prediction_prompt(prediction_input, tokenizer=tokenizer)
            prompt_rows.append(_prompt_snapshot_row(row, prompt))
            decoded, new_tokens, _ = _decode_prediction_attempt(
                model=model,
                tokenizer=tokenizer,
                prompt=prompt,
                max_new_tokens=max_new_tokens,
                torch_module=torch,
            )
            raw_prediction = _extract_strict_json_object(decoded)
            raw_status = _schema_guard_status(raw_prediction)
            retry_status: dict[str, Any] | None = None
            retry_prediction: Any = None
            retry_decoded: str | None = None
            retry_new_tokens: Any = None
            retry_attempted = False
            if schema_retry_enabled and not raw_status["schema_valid"]:
                retry_attempted = True
                retry_instruction = _schema_retry_prompt(prediction_input, raw_prediction, raw_status)
                retry_prompt = format_schema_retry_prompt_text(retry_instruction, tokenizer=tokenizer)
                retry_decoded, retry_new_tokens, _ = _decode_prediction_attempt(
                    model=model,
                    tokenizer=tokenizer,
                    prompt=retry_prompt,
                    max_new_tokens=max_new_tokens,
                    torch_module=torch,
                )
                retry_prediction = _extract_strict_json_object(retry_decoded)
                retry_status = _schema_guard_status(retry_prediction)
            schema_guard = _build_schema_guard(
                raw_status=raw_status,
                retry_enabled=schema_retry_enabled,
                retry_attempted=retry_attempted,
                retry_status=retry_status,
            )
            final_prediction = (
                retry_prediction if schema_guard["validated_output_source"] == "retry_attempt" else raw_prediction
            )
            raw_rows.append(
                _raw_decoded_summary_row(
                    row.id,
                    decoded,
                    schema_guard=schema_guard,
                    retry_decoded=retry_decoded,
                )
            )
            trace_rows.append(
                _generation_trace_row(
                    row_id=row.id,
                    attempt="raw_attempt",
                    prediction_source_kind="private_a100_adapter",
                    generated_tokens=new_tokens,
                    max_new_tokens=max_new_tokens,
                    eos_token_id=getattr(tokenizer, "eos_token_id", None),
                )
            )
            if retry_attempted:
                trace_rows.append(
                    _generation_trace_row(
                        row_id=row.id,
                        attempt="retry_attempt",
                        prediction_source_kind="private_a100_adapter",
                        generated_tokens=retry_new_tokens,
                        max_new_tokens=max_new_tokens,
                        eos_token_id=getattr(tokenizer, "eos_token_id", None),
                    )
                )
            record = {
                "id": row.id,
                "prediction": final_prediction,
                "schema_guard": schema_guard,
                "prediction_source_kind": "private_a100_adapter",
                "provenance": {"public_safe": True, "source_id": row.provenance.get("source_id", row.id)},
            }
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    if sidecar_paths is not None:
        _write_prompt_snapshot(
            prompt_rows,
            sidecar_paths["prompt_snapshot"],
            prediction_split=str(config.get("prediction_split", "all")),
            decoding_policy=_sidecar_written_decoding_policy(config),
        )
        _write_jsonl_records(sidecar_paths["raw_decoded_summary"], raw_rows)
        _write_jsonl_records(sidecar_paths["generation_trace"], trace_rows)
    return len(rows)


def _run_real_prediction_with_optional_sidecars(
    config: dict[str, Any],
    rows: list[SFTDatasetRow],
    output_path: Path,
    sidecar_paths: dict[str, Path],
) -> int:
    return _run_real_sft_prediction(config, rows, output_path, sidecar_paths=sidecar_paths)


def run_sft_prediction_export(
    config_path: Path,
    manifest_path: Path,
    output_path: Path,
    *,
    dry_run: bool = True,
    fixture_mode: bool = False,
) -> dict[str, Any]:
    config = _load_config(config_path)
    sidecar_paths = _prediction_sidecar_paths(output_path)
    metadata = _prediction_metadata_common(
        config_path=config_path,
        manifest_path=manifest_path,
        output_path=output_path,
        dry_run=dry_run,
        fixture_mode=fixture_mode,
    )
    if dry_run and not fixture_mode:
        metadata["prediction_status"] = "prediction_skipped_no_opt_in"
        return metadata
    raw_rows = _load_sft_prediction_rows(manifest_path, split=str(config.get("prediction_split", "all")))
    rows, row_limit = _limited_sft_prediction_rows(raw_rows, config)
    _record_sft_prediction_row_selection(
        metadata,
        rows=rows,
        row_limit=row_limit,
        loaded_rows_before_limit=len(raw_rows),
    )
    if fixture_mode:
        metadata["prediction_count"] = _write_fixture_predictions(rows, output_path)
        _mark_sidecars_written(metadata)
        _write_fixture_sidecars(
            rows=rows,
            output_path=output_path,
            sidecar_paths=sidecar_paths,
            prediction_split=str(config.get("prediction_split", "all")),
            max_new_tokens=int(config.get("max_new_tokens", 256)),
            decoding_policy=metadata["decoding_policy"],
        )
        copy_shadow = _run_copy_backed_prediction_shadow_hook(
            config=config,
            config_path=config_path,
            rows=rows,
            output_path=output_path,
        )
        if copy_shadow is not None:
            metadata["copy_backed_shadow"] = copy_shadow
        metadata["prediction_status"] = "fixture_predictions_written"
        metadata["prediction_source_kind"] = "public_sample_contract_fixture"
        metadata["notes"] = (
            "Fixture-mode predictions mirror public-sample target contracts to validate the evidence pipeline. "
            "No private adapter artifacts were loaded."
        )
        _write_prediction_metadata(output_path, metadata)
        return metadata
    adapter_path = config.get("adapter_path")
    if not isinstance(adapter_path, str) or not adapter_path.strip():
        metadata["prediction_status"] = "prediction_blocked_missing_adapter"
        metadata["prediction_source_kind"] = "none"
        metadata["prediction_gate"]["will_run_private_prediction"] = False
        metadata["notes"] = "Private prediction was blocked because no adapter_path was configured."
        return metadata
    if not bool(config.get("allow_private_prediction")):
        metadata["prediction_status"] = "prediction_blocked_by_config"
        metadata["prediction_source_kind"] = "none"
        metadata["prediction_gate"]["will_run_private_prediction"] = False
        metadata["notes"] = "Private prediction was blocked because allow_private_prediction is not true."
        return metadata
    if "<" in adapter_path or ">" in adapter_path:
        metadata["prediction_status"] = "prediction_blocked_by_adapter_template"
        metadata["prediction_source_kind"] = "none"
        metadata["prediction_gate"]["will_run_private_prediction"] = False
        metadata["notes"] = "Private prediction was blocked because adapter_path is an unresolved template."
        return metadata
    if not _prediction_dependencies_available():
        return _write_private_prediction_unavailable(metadata)
    metadata["prediction_count"] = _run_real_prediction_with_optional_sidecars(config, rows, output_path, sidecar_paths)
    _mark_sidecars_written(metadata)
    copy_shadow = _run_copy_backed_prediction_shadow_hook(
        config=config,
        config_path=config_path,
        rows=rows,
        output_path=output_path,
    )
    if copy_shadow is not None:
        metadata["copy_backed_shadow"] = copy_shadow
    metadata["prediction_status"] = "private_adapter_predictions_written"
    metadata["prediction_source_kind"] = "private_a100_adapter"
    metadata["notes"] = (
        "Private A100 adapter predictions were written as sanitized public-sample contract prediction rows. "
        "No checkpoints, adapters, raw logs, or private paths were copied into the prediction artifact."
    )
    _write_prediction_metadata(output_path, metadata)
    return metadata


def _loss_interpretation() -> dict[str, bool]:
    return {
        "loss_improvement_alone_proves_contract_learning": False,
        "requires_assistant_loss_evidence": True,
    }


def _label_provenance(
    value: dict[str, Any] | str | None,
    *,
    source_kind: str,
    real_training_path: bool,
) -> dict[str, Any]:
    if isinstance(value, dict):
        provenance = dict(value)
    elif isinstance(value, str) and value:
        provenance = {"source_kind": value}
    else:
        provenance = {"source_kind": source_kind}
    provenance.setdefault("source_kind", source_kind)
    provenance.setdefault("real_training_path", real_training_path)
    return provenance


_REAL_LABEL_SOURCES = {"real_training_labels", "actual_training_labels", "trl_collator_labels"}
_NON_REAL_LABEL_SOURCE_KINDS = {
    "fixture",
    "fixture_collator",
    "simulated",
    "simulated_collator",
    "unavailable",
    "unspecified",
}


def _deduped_gaps(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _real_training_label_provenance(
    *,
    label_source: str,
    collator_status: str,
    provenance: dict[str, Any],
) -> bool:
    source_kind = str(provenance.get("source_kind", "unspecified"))
    return (
        label_source in _REAL_LABEL_SOURCES
        and collator_status == "labels_inspected"
        and provenance.get("real_training_path") is True
        and source_kind not in _NON_REAL_LABEL_SOURCE_KINDS
    )


def _fixture_or_simulated_label_provenance(label_source: str, provenance: dict[str, Any]) -> bool:
    source_kind = str(provenance.get("source_kind", "unspecified"))
    return source_kind in {"fixture", "fixture_collator", "simulated", "simulated_collator"} or label_source in {
        "fixture_labels",
        "fixture_collator_labels",
        "simulated_labels",
        "simulated_collator_labels",
    }


def _true_label_mask_status(
    *,
    label_source: str,
    provenance: dict[str, Any],
    real_training_path: bool,
) -> str:
    if real_training_path:
        return "inspectable"
    if _fixture_or_simulated_label_provenance(label_source, provenance):
        return "fixture_only"
    return "unavailable"


def _inspectable_label_evidence_gaps(
    *,
    label_source: str,
    provenance: dict[str, Any],
    explicit_provenance_supplied: bool,
    real_training_path: bool,
) -> list[str]:
    if real_training_path:
        return []
    gaps = ["real_training_labels_not_inspected", "real_training_label_provenance_missing"]
    if _fixture_or_simulated_label_provenance(label_source, provenance):
        gaps.append("fixture_labels_not_real_training_proof")
    if not explicit_provenance_supplied:
        gaps.append("label_provenance_unspecified")
    if provenance.get("real_training_path") is not True:
        gaps.append("label_provenance_not_real_training_path")
    return _deduped_gaps(gaps)


def _objective_unavailable(
    reason: str,
    *,
    inspection_status: str = "dependency_unavailable",
    dependency_unavailable: bool = True,
    tokenizer_status: str = "unavailable",
    tokenizer_template_status: str = "unavailable",
    collator_status: str = "unavailable",
    evidence_gaps: list[str] | None = None,
) -> dict[str, Any]:
    resolved_gaps = list(evidence_gaps or [])
    for gap in ("real_training_labels_not_inspected", "real_training_label_provenance_missing"):
        if gap not in resolved_gaps:
            resolved_gaps.append(gap)
    return {
        "inspection_status": inspection_status,
        "dependency_unavailable": dependency_unavailable,
        "unavailable_reason": reason,
        "tokenizer_status": tokenizer_status,
        "tokenizer_template_status": tokenizer_template_status,
        "collator_status": collator_status,
        "label_source": "unavailable",
        "label_provenance": _label_provenance(None, source_kind="unavailable", real_training_path=False),
        "label_tensor_available": False,
        "true_label_mask_status": "unavailable",
        "prompt_token_count": None,
        "assistant_token_count": None,
        "prompt_tokens_masked": None,
        "assistant_tokens_carry_loss": None,
        "evidence_gaps": resolved_gaps,
        "loss_interpretation": _loss_interpretation(),
    }


def _flatten_offsets(value: Any) -> list[tuple[int, int]]:
    offsets = _token_list(value)
    normalized: list[tuple[int, int]] = []
    for item in offsets:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            normalized.append((int(item[0]), int(item[1])))
    return normalized


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _tokenizer_template_status(tokenizer: Any | None) -> str:
    if tokenizer is None:
        return "unavailable"
    chat_template = getattr(tokenizer, "chat_template", None)
    if isinstance(chat_template, str) and chat_template.strip():
        return "template_available"
    if callable(getattr(tokenizer, "apply_chat_template", None)):
        return "template_callable"
    return "fallback"


def _collator_labels(
    *,
    collator: Any | None,
    encoded: Any,
    assistant_start: int,
    assistant_end: int,
    offsets: list[tuple[int, int]],
    row_id: str,
) -> tuple[list[Any], str, str, list[str]]:
    if collator is None:
        labels, evidence_gaps = _assistant_only_labels_from_encoded(
            encoded=encoded,
            offsets=offsets,
            assistant_start=assistant_start,
            assistant_end=assistant_end,
        )
        if labels and not evidence_gaps:
            return labels, "assistant_only_constructed_labels", "assistant_only_labels_constructed", []
        return [], "unavailable", "assistant_only_labels_unavailable", evidence_gaps
    if not callable(collator):
        return [], "unavailable", "not_callable", ["collator_not_callable"]
    feature = dict(encoded) if isinstance(encoded, dict) else {"input_ids": _mapping_value(encoded, "input_ids")}
    feature["label_provenance_row_id"] = row_id
    feature["label_provenance_assistant_start"] = assistant_start
    feature["label_provenance_assistant_end"] = assistant_end
    try:
        batch = collator([feature])
    except Exception:
        return [], "unavailable", "error", ["collator_label_extraction_failed"]
    labels = _token_list(_mapping_value(batch, "labels"))
    if labels:
        return labels, "trl_collator_labels", "labels_inspected", []
    return [], "unavailable", "labels_missing", ["label_tensor_unavailable"]


def _assistant_target_span(training_text: str, assistant_text: str) -> tuple[str, int | None, int | None]:
    if not assistant_text:
        return "assistant_span_unavailable", None, None
    starts: list[int] = []
    next_start = training_text.find(assistant_text)
    while next_start >= 0:
        starts.append(next_start)
        next_start = training_text.find(assistant_text, next_start + len(assistant_text))
    if not starts:
        return "assistant_span_unavailable", None, None
    if len(starts) > 1:
        return "assistant_span_ambiguous", None, None
    start = starts[0]
    return "available", start, start + len(assistant_text)


def _assistant_only_labels_from_encoded(
    *,
    encoded: Any,
    offsets: list[tuple[int, int]],
    assistant_start: int,
    assistant_end: int,
) -> tuple[list[Any], list[str]]:
    input_ids = _token_list(_mapping_value(encoded, "input_ids"))
    if not input_ids:
        return [], ["input_ids_unavailable"]
    if not offsets or len(input_ids) != len(offsets):
        gaps = ["token_offsets_unavailable"] if not offsets else ["label_token_offset_length_mismatch"]
        return [], gaps

    assistant_indices: set[int] = set()
    boundary_overlap = False
    for index, (start, end) in enumerate(offsets):
        if start == end:
            continue
        if (start < assistant_start < end) or (start < assistant_end < end):
            boundary_overlap = True
            continue
        if start >= assistant_start and end <= assistant_end:
            assistant_indices.add(index)

    if boundary_overlap:
        return [], ["assistant_span_token_boundary_unavailable"]
    if not assistant_indices:
        return [], ["assistant_target_tokens_unavailable"]

    return [
        token_id if index in assistant_indices else -100
        for index, token_id in enumerate(input_ids)
    ], []


def _assistant_only_training_record(
    row: SFTDatasetRow,
    tokenizer: Any,
    *,
    max_seq_length: int | None = None,
) -> dict[str, list[Any]]:
    training_text = format_sft_training_text(row, tokenizer=tokenizer)
    assistant_text = canonical_contract_json(row.target_contract)
    span_status, assistant_start, assistant_end = _assistant_target_span(training_text, assistant_text)
    if span_status != "available" or assistant_start is None or assistant_end is None:
        raise ValueError(f"assistant-only SFT labels unavailable: {span_status}")

    encoded = tokenizer(training_text, return_offsets_mapping=True, add_special_tokens=False)
    input_ids = _token_list(_mapping_value(encoded, "input_ids"))
    offsets = _flatten_offsets(_mapping_value(encoded, "offset_mapping"))
    labels, evidence_gaps = _assistant_only_labels_from_encoded(
        encoded=encoded,
        offsets=offsets,
        assistant_start=assistant_start,
        assistant_end=assistant_end,
    )
    if not labels or evidence_gaps:
        gaps = ",".join(evidence_gaps) if evidence_gaps else "label_tensor_unavailable"
        raise ValueError(f"assistant-only SFT labels unavailable: {gaps}")
    if max_seq_length is not None and len(input_ids) > max_seq_length:
        raise ValueError("assistant-only SFT labels unavailable: max_seq_length_exceeded")

    attention_mask = _token_list(_mapping_value(encoded, "attention_mask"))
    if len(attention_mask) != len(input_ids):
        attention_mask = [1 for _ in input_ids]
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


class _AssistantOnlyCausalLmDataCollator:
    def __init__(self, tokenizer: Any, *, tensorize: bool = True) -> None:
        self._tokenizer = tokenizer
        self._tensorize = tensorize

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        pad_token_id = getattr(self._tokenizer, "pad_token_id", None)
        if pad_token_id is None:
            pad_token_id = getattr(self._tokenizer, "eos_token_id", 0)
        max_length = max(len(_token_list(feature.get("input_ids"))) for feature in features)
        batch: dict[str, list[list[Any]]] = {"input_ids": [], "attention_mask": [], "labels": []}
        for feature in features:
            input_ids = _token_list(feature.get("input_ids"))
            seq_len = len(input_ids)
            attention_mask = _token_list(feature.get("attention_mask"))[:seq_len]
            labels = _token_list(feature.get("labels"))[:seq_len]
            if len(attention_mask) < seq_len:
                attention_mask = attention_mask + [1] * (seq_len - len(attention_mask))
            if len(labels) < seq_len:
                labels = labels + [-100] * (seq_len - len(labels))
            pad_length = max_length - seq_len
            batch["input_ids"].append(input_ids + [pad_token_id] * pad_length)
            batch["attention_mask"].append(attention_mask + [0] * pad_length)
            batch["labels"].append(labels + [-100] * pad_length)
        if not self._tensorize:
            return batch
        import torch

        return {key: torch.tensor(value, dtype=torch.long) for key, value in batch.items()}


def _sft_trainer_tokenizer_kwargs(trainer_class: Any, tokenizer: Any) -> dict[str, Any]:
    try:
        parameters = inspect.signature(trainer_class.__init__).parameters
    except (TypeError, ValueError):
        return {"processing_class": tokenizer}
    if "processing_class" in parameters:
        return {"processing_class": tokenizer}
    if "tokenizer" in parameters:
        return {"tokenizer": tokenizer}
    return {}


def inspect_sft_objective(
    row: SFTDatasetRow,
    *,
    tokenizer: Any | None = None,
    collator: Any | None = None,
    label_source: str | None = None,
    label_provenance: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    if tokenizer is None:
        if not _train_dependencies_available():
            return _objective_unavailable("train dependencies or tokenizer are not available in this runtime")
        return {
            **_objective_unavailable(
                "tokenizer was not supplied for local non-heavy inspection",
                inspection_status="tokenizer_unavailable",
                tokenizer_status="unavailable",
                tokenizer_template_status="unavailable",
                collator_status="unavailable",
            ),
            "inspection_status": "tokenizer_unavailable",
        }

    template_status = _tokenizer_template_status(tokenizer)
    training_text = format_sft_training_text(row, tokenizer=tokenizer)
    assistant_text = canonical_contract_json(row.target_contract)
    span_status, assistant_start, assistant_end = _assistant_target_span(training_text, assistant_text)
    if span_status != "available" or assistant_start is None or assistant_end is None:
        return _objective_unavailable(
            "assistant target span was not found in rendered training text",
            inspection_status=span_status,
            dependency_unavailable=False,
            tokenizer_status="available",
            tokenizer_template_status=template_status,
            collator_status="unavailable" if collator is None else "not_inspected",
            evidence_gaps=[span_status],
        )

    encoded = tokenizer(training_text, return_offsets_mapping=True, add_special_tokens=False)
    offsets = _flatten_offsets(_mapping_value(encoded, "offset_mapping"))
    labels, inferred_label_source, collator_status, label_evidence_gaps = _collator_labels(
        collator=collator,
        encoded=encoded,
        assistant_start=assistant_start,
        assistant_end=assistant_end,
        offsets=offsets,
        row_id=row.id,
    )
    if not labels or not offsets or len(labels) != len(offsets):
        gaps = ["label_tensor_unavailable", *label_evidence_gaps]
        if not offsets:
            gaps.append("token_offsets_unavailable")
        return _objective_unavailable(
            "labels or token offsets were not available from the inspected local path",
            inspection_status="labels_unavailable",
            dependency_unavailable=False,
            tokenizer_status="available",
            tokenizer_template_status=template_status,
            collator_status=collator_status,
            evidence_gaps=gaps,
        )

    prompt_indices = [index for index, (_, end) in enumerate(offsets) if end <= assistant_start]
    assistant_indices = [
        index
        for index, (start, end) in enumerate(offsets)
        if start >= assistant_start and end <= assistant_end and start != end
    ]
    prompt_tokens_masked = bool(prompt_indices) and all(labels[index] == -100 for index in prompt_indices)
    assistant_tokens_carry_loss = bool(assistant_indices) and any(labels[index] != -100 for index in assistant_indices)
    resolved_label_source = label_source or inferred_label_source
    resolved_label_provenance = _label_provenance(
        label_provenance,
        source_kind="unspecified" if label_provenance is None else "training_runtime",
        real_training_path=False,
    )
    real_training_path = _real_training_label_provenance(
        label_source=resolved_label_source,
        collator_status=collator_status,
        provenance=resolved_label_provenance,
    )
    true_label_mask_status = _true_label_mask_status(
        label_source=resolved_label_source,
        provenance=resolved_label_provenance,
        real_training_path=real_training_path,
    )
    evidence_gaps = _inspectable_label_evidence_gaps(
        label_source=resolved_label_source,
        provenance=resolved_label_provenance,
        explicit_provenance_supplied=label_provenance is not None,
        real_training_path=real_training_path,
    )
    return {
        "inspection_status": "inspectable",
        "dependency_unavailable": False,
        "row_id": row.id,
        "tokenizer_status": "available",
        "tokenizer_template_status": template_status,
        "collator_status": collator_status,
        "label_source": resolved_label_source,
        "label_provenance": resolved_label_provenance,
        "label_tensor_available": True,
        "true_label_mask_status": true_label_mask_status,
        "prompt_token_count": len(prompt_indices),
        "assistant_token_count": len(assistant_indices),
        "prompt_tokens_masked": prompt_tokens_masked,
        "assistant_tokens_carry_loss": assistant_tokens_carry_loss,
        "evidence_gaps": evidence_gaps,
        "loss_interpretation": _loss_interpretation(),
    }


def inspect_sft_objective_from_manifest(manifest_path: Path, *, split: str = "train") -> dict[str, Any]:
    rows = _load_sft_training_rows(manifest_path, split=split)
    if not rows:
        result = _objective_unavailable(f"no SFT rows found for split={split}")
        result["inspection_status"] = "row_unavailable"
        return result
    return inspect_sft_objective(rows[0], tokenizer=None)


def _runtime_label_provenance_claims() -> dict[str, bool]:
    return {
        "checkpoint_release": False,
        "adapter_release": False,
        "held_out_generalization_claim": False,
        "production_readiness_claim": False,
        "live_browser_benchmark_claim": False,
        "model_recovery_claim": False,
    }


def _runtime_label_provenance_artifact_policy() -> dict[str, bool]:
    return {
        "raw_rendered_prompts_written": False,
        "raw_logs_copied_to_git": False,
        "checkpoints_or_adapters_copied_to_git": False,
        "private_paths_omitted": True,
    }


def _inspect_runtime_sft_objective(row: SFTDatasetRow, config: dict[str, Any]) -> dict[str, Any]:
    if not _runtime_label_dependencies_available():
        return _objective_unavailable("runtime tokenizer dependency is not available in this runtime")
    base_model = config.get("base_model")
    if not isinstance(base_model, str) or not base_model:
        if isinstance(config.get("base_model_public_id"), str) and config.get("base_model_public_id"):
            return _objective_unavailable(
                "runtime base model must be a repo-external private local path for this check",
                inspection_status="tokenizer_unavailable",
                tokenizer_status="unavailable",
                tokenizer_template_status="unavailable",
                collator_status="unavailable",
                evidence_gaps=["runtime_base_model_not_private_local_path"],
            )
        return _objective_unavailable(
            "runtime base model was not configured",
            inspection_status="tokenizer_unavailable",
            tokenizer_status="unavailable",
            tokenizer_template_status="unavailable",
            collator_status="unavailable",
            evidence_gaps=["runtime_base_model_missing"],
        )
    if "<" in base_model or ">" in base_model or not Path(base_model).expanduser().is_absolute():
        return _objective_unavailable(
            "runtime base model must be a repo-external private local path for this check",
            inspection_status="tokenizer_unavailable",
            tokenizer_status="unavailable",
            tokenizer_template_status="unavailable",
            collator_status="unavailable",
            evidence_gaps=["runtime_base_model_not_private_local_path"],
        )
    try:
        tokenizer_factory = cast(Any, globals().get("AutoTokenizer"))
        if tokenizer_factory is None:
            from transformers import AutoTokenizer

            tokenizer_factory = AutoTokenizer

        tokenizer = tokenizer_factory.from_pretrained(base_model, trust_remote_code=True, local_files_only=True)
    except Exception:
        return _objective_unavailable(
            "runtime tokenizer could not be loaded; raw model/runtime error details remain private",
            inspection_status="tokenizer_unavailable",
            tokenizer_status="unavailable",
            tokenizer_template_status="unavailable",
            collator_status="unavailable",
            evidence_gaps=["runtime_tokenizer_load_failed"],
        )
    try:
        max_seq_length = int(config.get("max_seq_length", 1024))
        training_record = _assistant_only_training_record(row, tokenizer, max_seq_length=max_seq_length)
        training_collator = _AssistantOnlyCausalLmDataCollator(tokenizer, tensorize=False)

        def runtime_training_collator(features: list[dict[str, Any]]) -> dict[str, Any]:
            return training_collator([training_record])

        return inspect_sft_objective(
            row,
            tokenizer=tokenizer,
            collator=runtime_training_collator,
            label_source="actual_training_labels",
            label_provenance={"source_kind": "private_training_runtime", "real_training_path": True},
        )
    except Exception:
        return _objective_unavailable(
            "runtime label inspection failed; raw tokenizer/collator error details remain private",
            inspection_status="labels_unavailable",
            dependency_unavailable=False,
            tokenizer_status="available",
            tokenizer_template_status=_tokenizer_template_status(tokenizer),
            collator_status="unavailable",
            evidence_gaps=["runtime_label_inspection_failed"],
        )


def _runtime_label_evidence_status(objective_inspection: dict[str, Any]) -> str:
    provenance = objective_inspection.get("label_provenance")
    source_kind = str(provenance.get("source_kind", "")) if isinstance(provenance, dict) else str(provenance or "")
    real_training_path = isinstance(provenance, dict) and provenance.get("real_training_path") is True
    if objective_inspection.get("true_label_mask_status") == "fixture_only" or source_kind in {
        "fixture",
        "fixture_collator",
        "simulated",
        "simulated_collator",
    }:
        return "fixture_only"
    if (
        objective_inspection.get("inspection_status") == "inspectable"
        and objective_inspection.get("label_tensor_available") is True
        and objective_inspection.get("true_label_mask_status") == "inspectable"
        and real_training_path
    ):
        return "labels_inspected"
    if objective_inspection.get("label_tensor_available") is True:
        return "labels_available_but_not_real_training_proof"
    return "labels_unavailable"


def _runtime_label_metadata_base(
    *,
    config_path: Path,
    manifest_path: Path,
    output_path: Path,
    split: str,
    status: str,
    config: dict[str, Any],
    manifest_summary: dict[str, Any],
    unresolved_fields: list[str],
    run_runtime_check: bool,
    output_root_policy: dict[str, Any],
    evidence_gaps: list[str] | None = None,
) -> dict[str, Any]:
    config_allows_runtime_check = bool(config.get("allow_runtime_label_provenance_check", False))
    private_override_required = bool(config.get("private_override_required", True))
    private_override_resolved = not unresolved_fields
    return {
        "evidence_kind": "sft_runtime_label_provenance_observed",
        "stage": "sft_runtime_label_provenance_observed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_path": _sanitize_training_metadata_value(config_path.as_posix()),
        "dataset_manifest_path": _sanitize_training_metadata_value(manifest_path.as_posix()),
        "dataset_manifest_id": manifest_summary["manifest_id"],
        "manifest_counts": manifest_summary["manifest_counts"],
        "manifest_public_safe": manifest_summary["manifest_public_safe"],
        "split": split,
        "metadata_path": _sanitize_training_metadata_value(output_path.as_posix()),
        "runtime_source_kind": "private_a100_runtime",
        "runtime_check_status": status,
        "evidence_status": status,
        "runtime_gate": {
            "cli_requested_runtime_check": run_runtime_check,
            "config_allow_runtime_label_provenance_check": config_allows_runtime_check,
            "private_override_resolved": private_override_resolved,
            "will_run_runtime_label_provenance_check": (
                run_runtime_check
                and config_allows_runtime_check
                and private_override_resolved
                and output_root_policy.get("status") == "approved_private_root"
            ),
        },
        "private_override": {
            "required": private_override_required,
            "status": "resolved" if private_override_resolved else "unresolved",
            "unresolved_fields": unresolved_fields,
            "requirements": _sanitize_training_metadata_value(config.get("private_override_requirements", [])),
            "public_placeholder": "<a100_project_root>",
        },
        "output_root_policy": output_root_policy,
        "dependency_policy": {
            "policy": str(config.get("dependency_policy", "runtime_check_no_public_model_download_in_local_tests")),
            "model_download_allowed": False,
            "private_adapter_load_allowed": False,
            "raw_private_logs_copied_to_git": False,
        },
        "package_versions": _sanitized_package_versions(),
        "label_tensor_available": False,
        "true_label_mask_status": "unavailable",
        "inspection_status": status,
        "label_source": "unavailable",
        "label_source_kind": "unavailable",
        "label_provenance": {"source_kind": "unavailable", "real_training_path": False},
        "prompt_tokens_masked": None,
        "assistant_tokens_carry_loss": None,
        "evidence_gaps": _deduped_gaps(evidence_gaps or []),
        "prior_artifacts": _sanitize_training_metadata_value(config.get("prior_artifacts", {})),
        "release_status": "not_released",
        "claims": _runtime_label_provenance_claims(),
        "artifact_policy": _runtime_label_provenance_artifact_policy(),
    }


def _maybe_write_runtime_label_metadata(output_path: Path, metadata: dict[str, Any]) -> None:
    output_root_policy = metadata.get("output_root_policy", {})
    if not isinstance(output_root_policy, dict) or output_root_policy.get("status") != "approved_private_root":
        return
    write_json(output_path, metadata)


def run_sft_runtime_label_provenance_check(
    config_path: Path,
    manifest_path: Path,
    *,
    split: str = "train",
    output_path: Path,
    run_runtime_check: bool = False,
    objective_inspector: Callable[[SFTDatasetRow, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config = _load_config(config_path)
    manifest_summary = _manifest_metadata_without_dataset_load(manifest_path)
    unresolved_fields = _unresolved_runtime_fields(config)
    output_root_policy = _runtime_check_output_root_policy(config, output_path, unresolved_fields)
    config_allows_runtime_check = bool(config.get("allow_runtime_label_provenance_check", False))

    status = "executed_runtime_label_provenance_check"
    gaps: list[str] = []
    if not run_runtime_check or not config_allows_runtime_check:
        status = "skipped_no_runtime_opt_in"
        gaps.extend(["runtime_check_not_executed", "runtime_opt_in_missing"])
    elif unresolved_fields:
        status = "blocked_unresolved_private_override"
        gaps.extend(["runtime_check_not_executed", "private_override_unresolved"])
    elif output_root_policy["status"] != "approved_private_root":
        status = "blocked_output_outside_approved_root"
        gaps.extend(["runtime_check_not_executed", "runtime_output_outside_approved_root"])

    metadata = _runtime_label_metadata_base(
        config_path=config_path,
        manifest_path=manifest_path,
        output_path=output_path,
        split=split,
        status=status,
        config=config,
        manifest_summary=manifest_summary,
        unresolved_fields=unresolved_fields,
        run_runtime_check=run_runtime_check,
        output_root_policy=output_root_policy,
        evidence_gaps=gaps,
    )
    if status != "executed_runtime_label_provenance_check":
        sanitized = _sanitize_training_metadata_value(metadata)
        if not isinstance(sanitized, dict):
            raise AssertionError("runtime label provenance metadata must be a mapping")
        result = cast(dict[str, Any], sanitized)
        _maybe_write_runtime_label_metadata(output_path, result)
        return result

    rows = _load_sft_training_rows(manifest_path, split=split)
    if not rows:
        metadata["runtime_check_status"] = "blocked_no_sft_rows"
        metadata["evidence_status"] = "blocked_no_sft_rows"
        metadata["inspection_status"] = "row_unavailable"
        metadata["evidence_gaps"] = ["runtime_check_not_executed", "sft_rows_unavailable"]
        sanitized = _sanitize_training_metadata_value(metadata)
        if not isinstance(sanitized, dict):
            raise AssertionError("runtime label provenance metadata must be a mapping")
        result = cast(dict[str, Any], sanitized)
        _maybe_write_runtime_label_metadata(output_path, result)
        return result

    inspector = objective_inspector or _inspect_runtime_sft_objective
    objective_inspection = inspector(rows[0], config)
    provenance = objective_inspection.get("label_provenance")
    if not isinstance(provenance, dict):
        provenance = _label_provenance(
            provenance if isinstance(provenance, str) else None,
            source_kind="unavailable",
            real_training_path=False,
        )
    evidence_status = _runtime_label_evidence_status(objective_inspection)
    metadata.update(
        {
            "evidence_status": evidence_status,
            "inspection_status": objective_inspection.get("inspection_status", "unknown"),
            "tokenizer_status": objective_inspection.get("tokenizer_status", "unknown"),
            "tokenizer_template_status": objective_inspection.get("tokenizer_template_status", "unknown"),
            "collator_status": objective_inspection.get("collator_status", "unknown"),
            "label_source": objective_inspection.get("label_source", "unavailable"),
            "label_source_kind": str(provenance.get("source_kind", "unavailable")),
            "label_provenance": dict(provenance),
            "label_tensor_available": bool(objective_inspection.get("label_tensor_available", False)),
            "true_label_mask_status": objective_inspection.get("true_label_mask_status", "unavailable"),
            "prompt_token_count": objective_inspection.get("prompt_token_count"),
            "assistant_token_count": objective_inspection.get("assistant_token_count"),
            "prompt_tokens_masked": objective_inspection.get("prompt_tokens_masked"),
            "assistant_tokens_carry_loss": objective_inspection.get("assistant_tokens_carry_loss"),
            "evidence_gaps": _deduped_gaps(
                [str(gap) for gap in objective_inspection.get("evidence_gaps", []) if gap]
            ),
            "loss_interpretation": _sanitize_training_metadata_value(
                objective_inspection.get("loss_interpretation", _loss_interpretation())
            ),
            "notes": (
                "Runtime label provenance metadata records objective-path evidence only. It is not a checkpoint "
                "release, adapter release, held-out generalization claim, production-readiness claim, or "
                "live-browser benchmark improvement claim."
            ),
        }
    )
    sanitized = _sanitize_training_metadata_value(metadata)
    if not isinstance(sanitized, dict):
        raise AssertionError("runtime label provenance metadata must be a mapping")
    result = cast(dict[str, Any], sanitized)
    write_json(output_path, result)
    return result


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

    rows = _record_sft_training_selection_from_config(metadata, config, manifest_path)
    base_model = _runtime_base_model(config)
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    max_seq_length = int(config.get("max_seq_length", 1024))
    records = [_assistant_only_training_record(row, tokenizer, max_seq_length=max_seq_length) for row in rows]
    dataset = Dataset.from_list(records)
    model = AutoModelForCausalLM.from_pretrained(base_model)
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=_training_arguments(config, output_dir),
        peft_config=_lora_config(config),
        data_collator=_AssistantOnlyCausalLmDataCollator(tokenizer),
        **_sft_trainer_tokenizer_kwargs(SFTTrainer, tokenizer),
    )
    train_result = trainer.train()
    _record_sft_training_budget_metadata(
        metadata,
        config=config,
        train_row_count=len(rows),
        records=records,
        trainer=trainer,
        train_result=train_result,
    )
    trainer.model.save_pretrained(metadata["adapter_path"])


def _run_real_dpo(metadata: dict[str, Any], config: dict[str, Any], manifest_path: Path, output_dir: Path) -> None:
    from datasets import Dataset  # type: ignore[import-not-found, unused-ignore]
    from peft import PeftModel  # type: ignore[import-not-found, unused-ignore]
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import DPOConfig, DPOTrainer  # type: ignore[import-not-found, unused-ignore]

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
    tokenizer = AutoTokenizer.from_pretrained(config["base_model"], trust_remote_code=True)
    sft_adapter_path = config.get("sft_adapter_path")
    if sft_adapter_path:
        base_model = AutoModelForCausalLM.from_pretrained(config["base_model"], trust_remote_code=True)
        model = PeftModel.from_pretrained(base_model, sft_adapter_path)
        model = model.merge_and_unload()
    else:
        model = AutoModelForCausalLM.from_pretrained(config["base_model"], trust_remote_code=True)

    dpo_config = DPOConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=int(config.get("per_device_train_batch_size", 2)),
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 4)),
        num_train_epochs=int(config.get("num_train_epochs", 2)),
        learning_rate=float(config.get("learning_rate", 5e-5)),
        warmup_ratio=float(config.get("warmup_ratio", 0.1)),
        beta=float(config.get("beta", 0.1)),
        max_length=int(config.get("max_seq_length", 1024)),
        logging_steps=int(config.get("logging_steps", 1)),
        save_strategy=str(config.get("save_strategy", "no")),
        report_to=[],
        remove_unused_columns=False,
    )
    trainer = DPOTrainer(
        model=model,
        args=dpo_config,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=_lora_config(config),
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
    _record_sft_training_selection_from_config(metadata, config, manifest_path)
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
