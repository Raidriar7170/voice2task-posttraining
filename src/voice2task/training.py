from __future__ import annotations

import hashlib
import importlib
import importlib.util
import inspect
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
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
SFT_MINIMUM_PYTHON = (3, 10)
FORMAL_PUBLIC_MANIFEST_RELATIVE_PATH = Path(
    "data/public-samples/manifest_public_sample.json"
)
FORMAL_PUBLIC_SFT_RELATIVE_PATH = Path("data/public-samples/sft_public_sample.jsonl")
FORMAL_PUBLIC_MANIFEST_ID = "public-sample-20260619T090925Z"
PRIVATE_SFT_CONFIG_DIRECTORY = Path("data/local-private/runtime")


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


def public_training_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized = _sanitize_training_metadata_value(metadata)
    if not isinstance(sanitized, dict):
        raise AssertionError("training metadata must remain a mapping after sanitization")
    return cast(dict[str, Any], sanitized)


PUBLIC_TRAINING_RESULT_FIELDS = (
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
)

PUBLIC_TRAINING_BUDGET_FIELDS = (
    "configured_max_steps",
    "observed_optimizer_steps",
    "num_train_epochs",
    "per_device_train_batch_size",
    "gradient_accumulation_steps",
    "effective_batch_size",
    "scheduler_max_steps",
    "train_row_count",
    "theoretical_examples_seen",
    "target_tokens_per_single_pass",
    "target_tokens_seen_estimate",
    "target_tokens_seen_status",
    "step_matching_unit",
    "step_matched_not_token_matched",
)
PUBLIC_TRAINING_METRIC_FIELDS = (
    "train_runtime",
    "train_samples_per_second",
    "train_steps_per_second",
    "train_loss",
    "epoch",
    "global_step",
    "trainable_parameter_count",
    "adapter_tensor_count",
    "adapter_state_digest_before",
    "adapter_state_digest_after",
    "changed_adapter_tensor_count",
    "all_adapter_tensors_finite",
)

PUBLIC_SFT_PREFLIGHT_SECTION_FIELDS: dict[str, tuple[str, ...]] = {
    "git": ("commit_sha", "tracked_worktree_clean"),
    "config": (
        "config_sha256",
        "allow_heavy_training",
        "base_model_public_id",
        "dataset_split",
        "max_train_rows",
        "max_steps",
        "per_device_train_batch_size",
        "gradient_accumulation_steps",
        "max_seq_length",
        "seed",
        "logging_steps",
        "save_strategy",
        "report_to_empty",
        "local_files_only",
        "bf16",
        "fp16",
        "tf32",
        "gradient_checkpointing",
        "use_cache",
        "low_cpu_mem_usage",
        "trust_remote_code",
        "dtype_is_bfloat16",
        "torch_dtype_is_bfloat16",
        "minimum_free_disk_gib",
        "lora_policy_valid",
        "private_file",
    ),
    "dataset": (
        "manifest_file",
        "manifest_sha256",
        "manifest_id",
        "sft_file",
        "sft_sha256",
        "selected_split",
        "selected_row_count",
        "selected_row_ids_sha256",
        "non_train_rows_selected",
    ),
    "model": (
        "public_id",
        "local_files_only",
        "stable_fingerprints",
        "weight_inventory",
        "total_weight_bytes",
        "minimum_weight_bytes",
        "geometry_matches_qwen2_5_7b",
        "snapshot_revision_sha256",
    ),
    "runtime": ("python", "python_requirement", "versions", "missing", "pip_check"),
    "gpu": (
        "explicit_selection",
        "visible_device_count",
        "name",
        "compute_capability",
        "total_memory_gib",
        "minimum_memory_gib",
        "free_memory_gib",
        "minimum_free_memory_gib",
        "compute_process_count",
        "idle_verified",
        "cuda_version",
        "bf16_supported",
    ),
    "output": (
        "ready",
        "blockers",
        "root_path_sha256",
        "output_path_sha256",
        "writable",
        "free_disk_gib",
        "minimum_free_disk_gib",
    ),
    "objective": (
        "records_checked",
        "prompt_labels_masked",
        "assistant_target_present",
        "max_sequence_length",
        "maximum_observed_tokens",
    ),
}

_INVALID_PUBLIC_VALUE = object()


def _public_preflight_scalar(section: str, key: str, value: Any) -> Any:
    if not isinstance(value, str):
        if isinstance(value, float) and not math.isfinite(value):
            return _INVALID_PUBLIC_VALUE
        return value if value is None or isinstance(value, int | float | bool) else _INVALID_PUBLIC_VALUE
    exact_values: dict[tuple[str, str], set[str]] = {
        ("config", "base_model_public_id"): {"Qwen/Qwen2.5-7B-Instruct"},
        ("config", "dataset_split"): {"train"},
        ("config", "save_strategy"): {"no"},
        ("dataset", "manifest_file"): {"manifest_public_sample.json"},
        ("dataset", "manifest_id"): {FORMAL_PUBLIC_MANIFEST_ID},
        ("dataset", "sft_file"): {"sft_public_sample.jsonl"},
        ("dataset", "selected_split"): {"train"},
        ("model", "public_id"): {"Qwen/Qwen2.5-7B-Instruct"},
        ("runtime", "python_requirement"): {">=3.10"},
        ("runtime", "pip_check"): {"ok", "conflict", "not_run"},
    }
    allowed = exact_values.get((section, key))
    if allowed is not None:
        return value if value in allowed else _INVALID_PUBLIC_VALUE
    if key == "commit_sha":
        return value if re.fullmatch(r"[0-9a-f]{40}", value) else _INVALID_PUBLIC_VALUE
    if key.endswith("sha256"):
        return value if re.fullmatch(r"[0-9a-f]{64}", value) else _INVALID_PUBLIC_VALUE
    if section == "runtime" and key == "python":
        return value if re.fullmatch(r"\d+\.\d+\.\d+", value) else _INVALID_PUBLIC_VALUE
    if section == "gpu" and key in {"compute_capability", "cuda_version"}:
        return value if re.fullmatch(r"(?:\d+(?:\.\d+)+|unknown)", value) else _INVALID_PUBLIC_VALUE
    if section == "gpu" and key == "name":
        return (
            value
            if re.fullmatch(r"[A-Za-z0-9 ._()+-]{1,100}", value)
            and re.search(r"\bA100\b", value, flags=re.IGNORECASE)
            else _INVALID_PUBLIC_VALUE
        )
    return _INVALID_PUBLIC_VALUE


def _public_sft_preflight_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    if value.get("schema_version") == "voice2task-sft-preflight-v1":
        result["schema_version"] = "voice2task-sft-preflight-v1"
    if isinstance(value.get("ready"), bool):
        result["ready"] = value["ready"]
    if value.get("status") in {"ready", "blocked"}:
        result["status"] = value["status"]
    blockers = value.get("blockers")
    if isinstance(blockers, list):
        result["blockers"] = [
            code
            for code in blockers
            if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", code)
        ]
    for section, allowed_fields in PUBLIC_SFT_PREFLIGHT_SECTION_FIELDS.items():
        raw_section = value.get(section)
        if not isinstance(raw_section, dict):
            continue
        public_section: dict[str, Any] = {}
        for key in allowed_fields:
            if key not in raw_section:
                continue
            raw_value = raw_section[key]
            if key in {"private_file", "versions", "missing", "stable_fingerprints", "weight_inventory", "blockers"}:
                public_section[key] = raw_value
                continue
            public_value = _public_preflight_scalar(section, key, raw_value)
            if public_value is not _INVALID_PUBLIC_VALUE:
                public_section[key] = public_value
        if section == "config" and isinstance(public_section.get("private_file"), dict):
            private_file = cast(dict[str, Any], public_section["private_file"])
            public_section["private_file"] = {
                key: private_file[key]
                for key in ("under_private_runtime", "nonsymlink", "git_ignored", "git_tracked")
                if key in private_file and isinstance(private_file[key], bool)
            }
        elif section == "runtime":
            versions = public_section.get("versions")
            if isinstance(versions, dict):
                public_section["versions"] = {
                    key: versions[key]
                    for key in ("torch", "accelerate", "datasets", "peft", "transformers", "trl")
                    if key in versions
                    and isinstance(versions[key], str)
                    and re.fullmatch(r"[A-Za-z0-9.+_-]{1,80}", versions[key])
                }
            missing = public_section.get("missing")
            if isinstance(missing, list):
                allowed_dependencies = {"torch", "accelerate", "datasets", "peft", "transformers", "trl"}
                public_section["missing"] = [name for name in missing if name in allowed_dependencies]
        elif section == "model":
            fingerprints = public_section.get("stable_fingerprints")
            if isinstance(fingerprints, dict):
                allowed_fingerprints = {
                    "config.json",
                    "generation_config.json",
                    "tokenizer.json",
                    "tokenizer_config.json",
                    "special_tokens_map.json",
                    "vocab.json",
                    "merges.txt",
                    "model.safetensors.index.json",
                    "pytorch_model.bin.index.json",
                }
                public_section["stable_fingerprints"] = {
                    key: fingerprints[key]
                    for key in allowed_fingerprints
                    if key in fingerprints
                    and isinstance(fingerprints[key], str)
                    and re.fullmatch(r"[0-9a-f]{64}", fingerprints[key])
                }
            inventory = public_section.get("weight_inventory")
            if isinstance(inventory, list):
                public_inventory: list[dict[str, Any]] = []
                for item in inventory:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("name")
                    size = item.get("size")
                    if (
                        isinstance(name, str)
                        and name
                        and Path(name).name == name
                        and type(size) is int
                        and size >= 0
                    ):
                        public_inventory.append({"name": name, "size": size})
                public_section["weight_inventory"] = public_inventory
        elif section == "output" and isinstance(public_section.get("blockers"), list):
            public_section["blockers"] = [
                code
                for code in cast(list[Any], public_section["blockers"])
                if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", code)
            ]
        result[section] = public_section
    return result


def public_training_result(metadata: dict[str, Any]) -> dict[str, Any]:
    """Build CLI output from an exact allowlist; never copy private metadata wholesale."""
    result: dict[str, Any] = {}
    top_level_enums: dict[str, set[str]] = {
        "schema_version": {"voice2task-training-result-v1"},
        "stage": {"sft", "dpo"},
        "training_status": {
            "dry_run",
            "training_completed",
            "training_failed",
            "training_skipped_by_config",
            "training_unavailable",
            "training_blocked_by_output_policy",
            "training_blocked_by_preflight",
        },
        "smoke_status": {"SMOKE_COMPLETED", "SMOKE_FAILED"},
    }
    for key, allowed in top_level_enums.items():
        if metadata.get(key) in allowed:
            result[key] = metadata[key]
    for key in ("observed_optimizer_steps", "training_rows_used"):
        if type(metadata.get(key)) is int:
            result[key] = metadata[key]
    if "preflight" in metadata:
        result["preflight"] = _public_sft_preflight_result(metadata["preflight"])
    blockers = metadata.get("blockers")
    if isinstance(blockers, list):
        result["blockers"] = [
            code
            for code in blockers
            if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", code)
        ]
    raw_budget = metadata.get("training_budget")
    if isinstance(raw_budget, dict):
        result["training_budget"] = {
            key: raw_budget[key]
            for key in PUBLIC_TRAINING_BUDGET_FIELDS
            if key in raw_budget
            and (
                raw_budget[key] is None
                or isinstance(raw_budget[key], int | bool)
                or (
                    isinstance(raw_budget[key], float)
                    and math.isfinite(raw_budget[key])
                )
                or raw_budget[key]
                in {
                    "estimated_from_label_tokens_and_step_budget",
                    "optimizer_steps",
                }
            )
        }
    raw_metrics = metadata.get("train_result_metrics")
    public_metrics: dict[str, Any] = {}
    if isinstance(raw_metrics, dict):
        for key in PUBLIC_TRAINING_METRIC_FIELDS:
            value = raw_metrics.get(key)
            if isinstance(value, int | bool) or (
                isinstance(value, float) and math.isfinite(value)
            ) or (
                key.startswith("adapter_state_digest_")
                and isinstance(value, str)
                and re.fullmatch(r"[0-9a-f]{64}", value)
            ):
                public_metrics[key] = value
    for key in PUBLIC_TRAINING_METRIC_FIELDS[6:]:
        if key in metadata:
            value = metadata[key]
            if isinstance(value, int | bool) or (
                key.startswith("adapter_state_digest_")
                and isinstance(value, str)
                and re.fullmatch(r"[0-9a-f]{64}", value)
            ):
                public_metrics[key] = value
    if public_metrics or isinstance(raw_metrics, dict):
        result["train_result_metrics"] = public_metrics
    raw_adapter_files = metadata.get("adapter_files")
    if isinstance(raw_adapter_files, list):
        adapter_files: list[dict[str, Any]] = []
        for item in raw_adapter_files:
            if not isinstance(item, dict):
                continue
            raw_name = item.get("name")
            if (
                not isinstance(raw_name, str)
                or not raw_name
                or Path(raw_name).is_absolute()
                or ".." in Path(raw_name).parts
            ):
                continue
            public_item = {
                key: item[key]
                for key in ("name", "size", "sha256")
                if key in item
            }
            if (
                type(public_item.get("size")) is int
                and public_item["size"] >= 0
                and isinstance(public_item.get("sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", public_item["sha256"])
            ):
                adapter_files.append(public_item)
        result["adapter_files"] = adapter_files
    if "clean_evaluation" in metadata:
        result["clean_evaluation"] = _clean_evaluation_truth_surface()
    return result


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
    return bool(validate_sft_output_policy(config, output_dir)["ready"])


def _path_has_symlink_below(root: Path, candidate: Path) -> bool:
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return candidate.is_symlink()
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _strict_descendant(candidate: Path, root: Path) -> bool:
    if candidate == root:
        return False
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _nearest_existing_parent(candidate: Path) -> Path:
    current = candidate.parent
    while not current.exists():
        current = current.parent
    return current


class SFTOutputPolicyError(RuntimeError):
    def __init__(self, blockers: list[str]) -> None:
        self.blockers = list(dict.fromkeys(blockers))
        super().__init__(",".join(self.blockers))


@dataclass(frozen=True)
class _OutputIdentity:
    st_dev: int
    st_ino: int
    st_uid: int
    st_gid: int
    st_mode: int


@dataclass(frozen=True)
class _BoundOutputIdentities:
    root: _OutputIdentity
    parent: _OutputIdentity


def _identity_from_stat(value: os.stat_result) -> _OutputIdentity:
    return _OutputIdentity(
        st_dev=int(value.st_dev),
        st_ino=int(value.st_ino),
        st_uid=int(value.st_uid),
        st_gid=int(value.st_gid),
        st_mode=int(value.st_mode),
    )


def _bind_output_identities(root: Path, parent: Path) -> _BoundOutputIdentities:
    try:
        root_stat = root.lstat()
        parent_stat = parent.lstat()
    except OSError as exc:
        raise SFTOutputPolicyError(["OUTPUT_IDENTITY_UNAVAILABLE"]) from exc
    if root.is_symlink() or parent.is_symlink():
        raise SFTOutputPolicyError(["OUTPUT_PATH_SYMLINK"])
    if not stat.S_ISDIR(root_stat.st_mode) or not stat.S_ISDIR(parent_stat.st_mode):
        raise SFTOutputPolicyError(["OUTPUT_IDENTITY_UNAVAILABLE"])
    return _BoundOutputIdentities(
        root=_identity_from_stat(root_stat),
        parent=_identity_from_stat(parent_stat),
    )


def _open_bound_output_parent(
    root: Path,
    parent: Path,
    expected: _BoundOutputIdentities,
) -> tuple[int, int]:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    root_fd = -1
    parent_fd = -1
    try:
        root_fd = os.open(root, flags)
        if _identity_from_stat(os.fstat(root_fd)) != expected.root:
            raise SFTOutputPolicyError(["OUTPUT_IDENTITY_CHANGED"])
        relative_parent = parent.relative_to(root)
        parent_fd = os.dup(root_fd)
        for component in relative_parent.parts:
            next_fd = os.open(component, flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        if _identity_from_stat(os.fstat(parent_fd)) != expected.parent:
            raise SFTOutputPolicyError(["OUTPUT_IDENTITY_CHANGED"])
        return root_fd, parent_fd
    except SFTOutputPolicyError:
        if parent_fd >= 0:
            os.close(parent_fd)
        if root_fd >= 0:
            os.close(root_fd)
        raise
    except (OSError, ValueError) as exc:
        if parent_fd >= 0:
            os.close(parent_fd)
        if root_fd >= 0:
            os.close(root_fd)
        raise SFTOutputPolicyError(["OUTPUT_IDENTITY_CHANGED"]) from exc


def validate_sft_output_policy(
    config: dict[str, Any],
    output_dir: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return a public-safe, no-write decision for a real SFT output directory."""
    blockers: list[str] = []
    try:
        configured_minimum_free_disk_gib = float(config.get("min_free_disk_gib", 20))
    except (TypeError, ValueError):
        configured_minimum_free_disk_gib = 20.0
    raw_root = config.get("output_root")
    if not isinstance(raw_root, str) or not raw_root or "<" in raw_root or ">" in raw_root:
        blockers.append("OUTPUT_ROOT_MISSING")
        return {
            "ready": False,
            "blockers": blockers,
            "root_path_sha256": None,
            "output_path_sha256": None,
            "writable": False,
            "free_disk_gib": None,
            "minimum_free_disk_gib": configured_minimum_free_disk_gib,
        }

    root = Path(raw_root).expanduser()
    candidate = output_dir.expanduser()
    if not root.is_absolute():
        blockers.append("OUTPUT_ROOT_NOT_ABSOLUTE")
    if not candidate.is_absolute():
        blockers.append("OUTPUT_DIR_NOT_ABSOLUTE")
    if blockers:
        return {
            "ready": False,
            "blockers": blockers,
            "root_path_sha256": None,
            "output_path_sha256": None,
            "writable": False,
            "free_disk_gib": None,
            "minimum_free_disk_gib": configured_minimum_free_disk_gib,
        }

    try:
        if root.is_symlink():
            blockers.append("OUTPUT_ROOT_SYMLINK")
        if not root.exists() or not root.is_dir():
            blockers.append("OUTPUT_ROOT_NOT_DIRECTORY")
    except OSError:
        blockers.append("OUTPUT_FILESYSTEM_UNAVAILABLE")
    if blockers:
        return {
            "ready": False,
            "blockers": blockers,
            "root_path_sha256": None,
            "output_path_sha256": None,
            "writable": False,
            "free_disk_gib": None,
            "minimum_free_disk_gib": configured_minimum_free_disk_gib,
        }

    try:
        root_resolved = root.resolve(strict=True)
        candidate_resolved = candidate.resolve(strict=False)
        if _path_has_symlink_below(root, candidate):
            blockers.append("OUTPUT_PATH_SYMLINK")
        candidate_is_descendant = _strict_descendant(candidate_resolved, root_resolved)
        if not candidate_is_descendant:
            blockers.append("OUTPUT_PATH_OUTSIDE_ROOT")
        parent = candidate.parent
        if candidate_is_descendant and (not parent.exists() or not parent.is_dir()):
            blockers.append("OUTPUT_PARENT_MISSING")
        elif candidate_is_descendant and parent.is_symlink():
            blockers.append("OUTPUT_PATH_SYMLINK")
        if candidate_is_descendant and candidate.exists() and not candidate.is_symlink():
            if not candidate.is_dir() or any(candidate.iterdir()):
                blockers.append("OUTPUT_DIRECTORY_NOT_EMPTY")
            else:
                blockers.append("OUTPUT_DIRECTORY_EXISTS")

        if repo_root is not None:
            resolved_repo = repo_root.resolve(strict=False)
            if _strict_descendant(candidate_resolved, resolved_repo) or candidate_resolved == resolved_repo:
                blockers.append("OUTPUT_PATH_GIT_TRACKED")
    except (OSError, RuntimeError):
        return {
            "ready": False,
            "blockers": ["OUTPUT_FILESYSTEM_UNAVAILABLE"],
            "root_path_sha256": None,
            "output_path_sha256": None,
            "writable": False,
            "free_disk_gib": None,
            "minimum_free_disk_gib": configured_minimum_free_disk_gib,
        }

    writable = False
    free_disk_gib: float | None = None
    structural_blockers = {
        "OUTPUT_PARENT_MISSING",
        "OUTPUT_PATH_OUTSIDE_ROOT",
        "OUTPUT_PATH_SYMLINK",
        "OUTPUT_PATH_GIT_TRACKED",
    }
    if any(code in structural_blockers for code in blockers):
        return {
            "ready": False,
            "blockers": list(dict.fromkeys(blockers)),
            "root_path_sha256": _sha256_text(root_resolved.as_posix()),
            "output_path_sha256": _sha256_text(candidate_resolved.as_posix()),
            "writable": False,
            "free_disk_gib": None,
            "minimum_free_disk_gib": configured_minimum_free_disk_gib,
        }
    try:
        writable_parent = candidate_resolved.parent
        writable = os.access(writable_parent, os.W_OK)
    except OSError:
        writable_parent = root_resolved
        blockers.append("OUTPUT_FILESYSTEM_UNAVAILABLE")
    if "OUTPUT_FILESYSTEM_UNAVAILABLE" not in blockers and not writable:
        blockers.append("OUTPUT_NOT_WRITABLE")
    try:
        minimum_free_disk_gib = configured_minimum_free_disk_gib
        free_disk_gib = shutil.disk_usage(writable_parent).free / float(1024**3)
    except (OSError, TypeError, ValueError):
        minimum_free_disk_gib = 20.0
        blockers.append("OUTPUT_DISK_CHECK_FAILED")
    if free_disk_gib is not None and free_disk_gib < minimum_free_disk_gib:
        blockers.append("OUTPUT_DISK_INSUFFICIENT")

    return {
        "ready": not blockers,
        "blockers": list(dict.fromkeys(blockers)),
        "root_path_sha256": _sha256_text(root_resolved.as_posix()),
        "output_path_sha256": _sha256_text(candidate_resolved.as_posix()),
        "writable": writable,
        "free_disk_gib": round(free_disk_gib, 3) if free_disk_gib is not None else None,
        "minimum_free_disk_gib": minimum_free_disk_gib,
    }


def _claim_sft_output_directory(
    config: dict[str, Any],
    output_dir: Path,
    *,
    repo_root: Path | None = None,
    expected_output_path_sha256: str | None = None,
    expected_identities: _BoundOutputIdentities | None = None,
) -> None:
    """Claim one leaf under a namespace kept stable across the final mkdirat boundary.

    Identity checkpoints fail closed on observable drift and never trigger pathname
    cleanup after uncertainty. This does not claim syscall-atomic protection from a
    malicious same-UID rename between the final checkpoint and mkdirat; deployment
    must prevent that namespace mutation during this narrow claim window.
    """
    initial = validate_sft_output_policy(config, output_dir, repo_root=repo_root)
    if initial.get("ready") is not True:
        if expected_identities is not None:
            initial_blockers = [str(code) for code in initial.get("blockers", [])]
            if initial_blockers in (["OUTPUT_DIRECTORY_EXISTS"], ["OUTPUT_DIRECTORY_NOT_EMPTY"]):
                raise SFTOutputPolicyError(["OUTPUT_DIRECTORY_EXISTS"])
            raise SFTOutputPolicyError(["OUTPUT_IDENTITY_CHANGED"])
        raise SFTOutputPolicyError([str(code) for code in initial.get("blockers", [])])
    expected_hash = expected_output_path_sha256 or initial.get("output_path_sha256")
    raw_root = config.get("output_root")
    if not isinstance(raw_root, str):
        raise SFTOutputPolicyError(["OUTPUT_ROOT_MISSING"])
    root = Path(raw_root).expanduser().resolve(strict=True)
    parent = output_dir.expanduser().parent.resolve(strict=True)
    identities = expected_identities or _bind_output_identities(root, parent)
    root_fd = -1
    parent_fd = -1
    try:
        root_fd, parent_fd = _open_bound_output_parent(root, parent, identities)
        try:
            path_identities = _bind_output_identities(root, parent)
        except SFTOutputPolicyError as exc:
            raise SFTOutputPolicyError(["OUTPUT_IDENTITY_CHANGED"]) from exc
        if (
            _identity_from_stat(os.fstat(root_fd)) != identities.root
            or _identity_from_stat(os.fstat(parent_fd)) != identities.parent
            or path_identities != identities
        ):
            raise SFTOutputPolicyError(["OUTPUT_IDENTITY_CHANGED"])
        os.mkdir(output_dir.name, mode=0o700, dir_fd=parent_fd)
        if (
            _identity_from_stat(os.fstat(root_fd)) != identities.root
            or _identity_from_stat(os.fstat(parent_fd)) != identities.parent
        ):
            raise SFTOutputPolicyError(["OUTPUT_IDENTITY_CHANGED"])
    except FileExistsError as exc:
        raise SFTOutputPolicyError(["OUTPUT_DIRECTORY_EXISTS"]) from exc
    except SFTOutputPolicyError:
        raise
    except OSError as exc:
        raise SFTOutputPolicyError(["OUTPUT_CREATE_FAILED"]) from exc
    finally:
        if parent_fd >= 0:
            os.close(parent_fd)
        if root_fd >= 0:
            os.close(root_fd)

    try:
        current = _bind_output_identities(root, parent)
    except SFTOutputPolicyError as exc:
        raise SFTOutputPolicyError(["OUTPUT_IDENTITY_CHANGED"]) from exc
    if current != identities:
        raise SFTOutputPolicyError(["OUTPUT_IDENTITY_CHANGED"])
    current_hash = _sha256_text(output_dir.expanduser().resolve(strict=True).as_posix())
    if not isinstance(expected_hash, str) or current_hash != expected_hash:
        raise SFTOutputPolicyError(["OUTPUT_PATH_CHANGED"])


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_repository_root() -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return Path(value) if value else None


def _git_repository_root_for_manifest(manifest_path: Path) -> Path | None:
    anchor = manifest_path.expanduser().parent
    try:
        result = subprocess.run(
            ["git", "-C", anchor.as_posix(), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip() if result.returncode == 0 else ""
    if not value:
        return None
    try:
        repo_root = Path(value).expanduser().resolve(strict=True)
        manifest_path.expanduser().resolve(strict=False).relative_to(repo_root)
    except (OSError, RuntimeError, ValueError):
        return None
    return repo_root


def _probe_sft_git(root: Path) -> tuple[dict[str, Any], list[str]]:
    facts: dict[str, Any] = {"commit_sha": None, "tracked_worktree_clean": False}
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return facts, ["GIT_PROBE_FAILED"]
    blockers: list[str] = []
    sha = commit.stdout.strip() if commit.returncode == 0 else ""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        blockers.append("GIT_COMMIT_UNAVAILABLE")
    else:
        facts["commit_sha"] = sha
    clean = status.returncode == 0 and not status.stdout.strip()
    facts["tracked_worktree_clean"] = clean
    if not clean:
        blockers.append("WORKTREE_NOT_CLEAN")
    return facts, blockers


def _installed_module_version(module_name: str, module: Any) -> str:
    module_version = getattr(module, "__version__", None)
    if isinstance(module_version, str) and module_version:
        return module_version
    try:
        return version(module_name)
    except PackageNotFoundError:
        return "unknown"


def _probe_sft_dependencies() -> tuple[dict[str, Any], list[str]]:
    required = ("torch", "accelerate", "datasets", "peft", "transformers", "trl")
    missing: list[str] = []
    versions: dict[str, str] = {}
    for module_name in required:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            missing.append(module_name)
            continue
        versions[module_name] = _installed_module_version(module_name, module)

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    facts: dict[str, Any] = {
        "python": python_version,
        "python_requirement": ">=3.10",
        "versions": versions,
        "missing": missing,
        "pip_check": "not_run",
    }
    blockers: list[str] = []
    if sys.version_info[:2] < SFT_MINIMUM_PYTHON:
        blockers.append("DEPENDENCY_CONFLICT")
    if missing:
        blockers.append("DEPENDENCY_MISSING")
    try:
        pip_check = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        pip_check = None
    if pip_check is None or pip_check.returncode != 0:
        facts["pip_check"] = "conflict"
        blockers.append("DEPENDENCY_CONFLICT")
    else:
        facts["pip_check"] = "ok"
    return facts, list(dict.fromkeys(blockers))


SFT_GPU_HELPER_SCHEMA_VERSION = "voice2task-sft-gpu-helper-v2"
SFT_GPU_HELPER_STATUSES = {
    "OK",
    "CUDA_UNAVAILABLE",
    "CUDA_PROBE_FAILED",
    "GPU_SELECTION_NOT_SINGLE",
}
SFT_GPU_HELPER_FACT_FIELDS = {
    "cuda_available",
    "visible_device_count",
    "name",
    "compute_capability",
    "total_memory_gib",
    "free_memory_gib",
    "cuda_version",
    "bf16_supported",
}


def _empty_sft_gpu_facts(*, explicit_selection: bool) -> dict[str, Any]:
    return {
        "explicit_selection": explicit_selection,
        "visible_device_count": 0,
        "name": None,
        "compute_capability": None,
        "total_memory_gib": None,
        "minimum_memory_gib": 35.0,
        "free_memory_gib": None,
        "minimum_free_memory_gib": 35.0,
        "compute_process_count": None,
        "idle_verified": False,
        "cuda_version": None,
        "bf16_supported": False,
    }


def _sample_sft_gpu_compute_process_count(selector: str) -> int:
    try:
        occupancy = subprocess.run(
            [
                "nvidia-smi",
                f"--id={selector}",
                "--query-compute-apps=pid",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED") from exc
    if occupancy.returncode != 0:
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    process_count = 0
    for line in occupancy.stdout.splitlines():
        value = line.strip()
        if not value:
            continue
        if not value.isdigit():
            raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
        process_count += 1
    return process_count


def _validated_sft_gpu_helper_result(value: Any) -> dict[str, Any]:
    expected_fields = {*SFT_GPU_HELPER_FACT_FIELDS, "status"}
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    status = value.get("status")
    cuda_available = value.get("cuda_available")
    visible_device_count = value.get("visible_device_count")
    bf16_supported = value.get("bf16_supported")
    cuda_version = value.get("cuda_version")
    if (
        not isinstance(status, str)
        or status not in SFT_GPU_HELPER_STATUSES
        or not isinstance(cuda_available, bool)
        or type(visible_device_count) is not int
        or visible_device_count < 0
        or not isinstance(bf16_supported, bool)
        or not isinstance(cuda_version, str)
        or not re.fullmatch(r"(?:\d+(?:\.\d+)+|unknown)", cuda_version)
    ):
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    for key in ("total_memory_gib", "free_memory_gib"):
        number = value.get(key)
        if number is not None and (
            isinstance(number, bool)
            or not isinstance(number, int | float)
            or not math.isfinite(float(number))
            or float(number) < 0
        ):
            raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    name = value.get("name")
    capability = value.get("compute_capability")
    if name is not None and (
        not isinstance(name, str) or re.fullmatch(r"[A-Za-z0-9 ._()+-]{1,100}", name) is None
    ):
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    if capability is not None and (
        not isinstance(capability, str) or re.fullmatch(r"\d+\.\d+", capability) is None
    ):
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    device_fact_values = (
        name,
        capability,
        value.get("total_memory_gib"),
        value.get("free_memory_gib"),
    )
    if status == "OK":
        if not cuda_available or visible_device_count != 1 or any(
            item is None for item in device_fact_values
        ):
            raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    elif status == "GPU_SELECTION_NOT_SINGLE":
        if (
            not cuda_available
            or visible_device_count == 1
            or any(item is not None for item in device_fact_values)
            or bf16_supported
        ):
            raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    elif (
        cuda_available
        or visible_device_count != 0
        or any(item is not None for item in device_fact_values)
        or bf16_supported
    ):
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    return {"status": status, **{key: value[key] for key in SFT_GPU_HELPER_FACT_FIELDS}}


def _run_sft_gpu_fact_helper(selector: str) -> dict[str, Any]:
    environment = {
        "CUDA_VISIBLE_DEVICES": selector,
        "PYTHONNOUSERSITE": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "LC_ALL": "C",
        "LANG": "C",
    }
    try:
        python_executable = Path(sys.executable).expanduser()
        if not python_executable.is_absolute() or not python_executable.is_file():
            raise OSError
        helper_path = Path(__file__).with_name("_sft_gpu_probe_helper.py").resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED") from exc
    try:
        completed = subprocess.run(
            [python_executable.as_posix(), "-I", helper_path.as_posix()],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED") from exc
    if completed.returncode != 0:
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    try:
        payload = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SFT_GPU_HELPER_SCHEMA_VERSION:
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    if set(payload) != {*SFT_GPU_HELPER_FACT_FIELDS, "schema_version", "status"}:
        raise RuntimeError("GPU_OCCUPANCY_PROBE_FAILED")
    return _validated_sft_gpu_helper_result(
        {
            "status": payload["status"],
            **{key: payload[key] for key in SFT_GPU_HELPER_FACT_FIELDS},
        }
    )


def _probe_sft_gpu() -> tuple[dict[str, Any], list[str]]:
    selected = os.environ.get("CUDA_VISIBLE_DEVICES")
    selected_parts = [part.strip() for part in selected.split(",") if part.strip()] if selected else []
    facts = _empty_sft_gpu_facts(explicit_selection=bool(selected_parts))
    blockers: list[str] = []
    if len(selected_parts) != 1 or selected_parts == ["-1"]:
        blockers.append("GPU_SELECTION_NOT_EXPLICIT" if not selected_parts else "GPU_SELECTION_NOT_SINGLE")
        return facts, blockers
    selector = selected_parts[0]
    try:
        pre_count = _sample_sft_gpu_compute_process_count(selector)
    except Exception:
        return facts, ["GPU_OCCUPANCY_PROBE_FAILED"]
    facts["compute_process_count"] = pre_count
    if pre_count:
        return facts, ["GPU_BUSY"]
    helper_result: dict[str, Any] | None = None
    helper_failed = False
    try:
        helper_result = _validated_sft_gpu_helper_result(_run_sft_gpu_fact_helper(selector))
    except Exception:
        helper_failed = True
    try:
        post_count = _sample_sft_gpu_compute_process_count(selector)
    except Exception:
        return facts, ["GPU_OCCUPANCY_PROBE_FAILED"]
    facts["compute_process_count"] = post_count
    if post_count:
        return facts, ["GPU_BUSY"]
    if helper_failed or helper_result is None:
        return facts, ["GPU_OCCUPANCY_PROBE_FAILED"]
    facts["idle_verified"] = True
    helper_status = str(helper_result["status"])
    cuda_available = bool(helper_result["cuda_available"])
    visible_count = int(helper_result["visible_device_count"])
    facts["visible_device_count"] = visible_count
    if helper_status == "CUDA_UNAVAILABLE":
        return facts, ["CUDA_UNAVAILABLE"]
    if helper_status == "CUDA_PROBE_FAILED":
        return facts, ["CUDA_PROBE_FAILED"]
    if helper_status == "GPU_SELECTION_NOT_SINGLE":
        return facts, ["GPU_SELECTION_NOT_SINGLE"]
    if helper_status != "OK" or not cuda_available or visible_count != 1:
        return facts, ["GPU_OCCUPANCY_PROBE_FAILED"]
    gpu_name = str(helper_result["name"])
    capability_text = str(helper_result["compute_capability"])
    try:
        capability = tuple(int(value) for value in capability_text.split("."))
        total_memory_gib = float(helper_result["total_memory_gib"])
        free_memory_gib = float(helper_result["free_memory_gib"])
    except (TypeError, ValueError):
        return facts, ["GPU_OCCUPANCY_PROBE_FAILED"]
    bf16_supported = bool(helper_result["bf16_supported"])
    facts.update(
        {
            "name": gpu_name,
            "compute_capability": capability_text,
            "total_memory_gib": round(total_memory_gib, 3),
            "free_memory_gib": round(free_memory_gib, 3),
            "cuda_version": str(helper_result["cuda_version"]),
            "bf16_supported": bf16_supported,
        }
    )
    if capability < (8, 0) or not bf16_supported:
        blockers.append("BF16_UNSUPPORTED")
    if total_memory_gib < 35.0:
        blockers.append("GPU_MEMORY_INSUFFICIENT")
    if free_memory_gib < 35.0:
        blockers.append("GPU_FREE_MEMORY_INSUFFICIENT")
    if re.search(r"\bA100\b", gpu_name, flags=re.IGNORECASE) is None:
        blockers.append("GPU_NOT_A100")
    return facts, list(dict.fromkeys(blockers))


def _smoke_config_facts(config_path: Path, config: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    if config.get("allow_heavy_training") is not True:
        blockers.append("CONFIG_HEAVY_TRAINING_NOT_ALLOWED")
    lora = config.get("lora")
    lora_valid = False
    if isinstance(lora, dict):
        rank = lora.get("r")
        alpha = lora.get("alpha")
        dropout = lora.get("dropout")
        target_modules = lora.get("target_modules")
        lora_valid = (
            type(rank) is int
            and 1 <= rank <= 64
            and type(alpha) is int
            and 1 <= alpha <= 128
            and isinstance(dropout, int | float)
            and not isinstance(dropout, bool)
            and 0.0 <= float(dropout) <= 0.2
            and isinstance(target_modules, list)
            and len(target_modules) == 4
            and set(target_modules) == {"q_proj", "k_proj", "v_proj", "o_proj"}
        )
    minimum_free_disk_gib = config.get("min_free_disk_gib")
    normalized_minimum_free_disk_gib = (
        float(minimum_free_disk_gib)
        if isinstance(minimum_free_disk_gib, int | float) and not isinstance(minimum_free_disk_gib, bool)
        else None
    )
    disk_floor_valid = (
        normalized_minimum_free_disk_gib is not None and normalized_minimum_free_disk_gib >= 20.0
    )
    max_train_rows = config.get("max_train_rows")
    max_train_rows_valid = type(max_train_rows) is int and max_train_rows in (1, 2)
    max_steps = config.get("max_steps")
    max_steps_valid = type(max_steps) is int and max_steps == 1
    per_device_train_batch_size = config.get("per_device_train_batch_size")
    per_device_train_batch_size_valid = (
        type(per_device_train_batch_size) is int and per_device_train_batch_size == 1
    )
    gradient_accumulation_steps = config.get("gradient_accumulation_steps")
    gradient_accumulation_steps_valid = (
        type(gradient_accumulation_steps) is int and gradient_accumulation_steps == 1
    )
    max_seq_length = config.get("max_seq_length")
    max_seq_length_valid = type(max_seq_length) is int and 1 <= max_seq_length <= 4096
    seed = config.get("seed")
    seed_valid = type(seed) is int
    logging_steps = config.get("logging_steps")
    logging_steps_valid = type(logging_steps) is int and logging_steps > 0
    bounded = (
        config.get("dataset_split") == "train"
        and max_train_rows_valid
        and max_steps_valid
        and per_device_train_batch_size_valid
        and gradient_accumulation_steps_valid
        and max_seq_length_valid
        and seed_valid
        and logging_steps_valid
        and config.get("save_strategy") == "no"
        and config.get("report_to") == []
        and config.get("base_model_public_id") == "Qwen/Qwen2.5-7B-Instruct"
        and config.get("local_files_only") is True
        and config.get("bf16") is True
        and config.get("fp16") is False
        and config.get("tf32") is True
        and config.get("gradient_checkpointing") is True
        and config.get("use_cache") is False
        and config.get("low_cpu_mem_usage") is True
        and config.get("trust_remote_code") is False
        and config.get("dtype") == "bfloat16"
        and config.get("torch_dtype") == "bfloat16"
        and disk_floor_valid
        and lora_valid
    )
    if not bounded:
        blockers.append("CONFIG_NOT_SMOKE_BOUNDED")
    return {
        "config_sha256": _sha256_file(config_path),
        "allow_heavy_training": config.get("allow_heavy_training") is True,
        "base_model_public_id": (
            "Qwen/Qwen2.5-7B-Instruct"
            if config.get("base_model_public_id") == "Qwen/Qwen2.5-7B-Instruct"
            else None
        ),
        "dataset_split": "train" if config.get("dataset_split") == "train" else None,
        "max_train_rows": max_train_rows if max_train_rows_valid else None,
        "max_steps": max_steps if max_steps_valid else None,
        "per_device_train_batch_size": (
            per_device_train_batch_size if per_device_train_batch_size_valid else None
        ),
        "gradient_accumulation_steps": (
            gradient_accumulation_steps if gradient_accumulation_steps_valid else None
        ),
        "max_seq_length": max_seq_length if max_seq_length_valid else None,
        "seed": seed if seed_valid else None,
        "logging_steps": logging_steps if logging_steps_valid else None,
        "save_strategy": "no" if config.get("save_strategy") == "no" else None,
        "report_to_empty": config.get("report_to") == [],
        "local_files_only": config.get("local_files_only") is True,
        "bf16": config.get("bf16") is True,
        "fp16": config.get("fp16") is True,
        "tf32": config.get("tf32") is True,
        "gradient_checkpointing": config.get("gradient_checkpointing") is True,
        "use_cache": config.get("use_cache") is True,
        "low_cpu_mem_usage": config.get("low_cpu_mem_usage") is True,
        "trust_remote_code": config.get("trust_remote_code") is True,
        "dtype_is_bfloat16": config.get("dtype") == "bfloat16",
        "torch_dtype_is_bfloat16": config.get("torch_dtype") == "bfloat16",
        "minimum_free_disk_gib": (
            normalized_minimum_free_disk_gib if disk_floor_valid else None
        ),
        "lora_policy_valid": lora_valid,
    }, blockers


def _load_selected_smoke_rows(
    manifest_path: Path,
    config: dict[str, Any],
) -> tuple[dict[str, Any], list[SFTDatasetRow], list[str]]:
    empty_facts: dict[str, Any] = {
        "manifest_file": manifest_path.name,
        "manifest_sha256": None,
        "manifest_id": None,
        "sft_file": None,
        "sft_sha256": None,
        "selected_split": "train",
        "selected_row_count": 0,
        "selected_row_ids_sha256": None,
        "non_train_rows_selected": 0,
    }
    row_limit = config.get("max_train_rows")
    row_limit_valid = type(row_limit) is int and row_limit in (1, 2)
    blockers: list[str] = []
    if not row_limit_valid or config.get("train_source_ids") is not None:
        blockers.append("TRAIN_ROW_SELECTION_INVALID")
    repo_root = _repo_root_from_canonical_manifest(manifest_path)
    if repo_root is None:
        return empty_facts, [], ["MANIFEST_PATH_NOT_CANONICAL"]
    sft_path = repo_root / FORMAL_PUBLIC_SFT_RELATIVE_PATH
    try:
        manifest = read_json(manifest_path)
        manifest_hash = _sha256_file(manifest_path)
        sft_hash = _sha256_file(sft_path)
        selected_rows: list[SFTDatasetRow] = []
        if row_limit_valid:
            with sft_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    if not isinstance(record, dict) or record.get("split") != "train":
                        blockers.append("TRAIN_ROW_SELECTION_INVALID")
                        break
                    selected_rows.append(SFTDatasetRow(**record))
                    if len(selected_rows) == row_limit:
                        break
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return empty_facts, [], ["DATASET_HASH_OR_ID_MISMATCH"]

    if not selected_rows:
        blockers.append("TRAIN_SPLIT_EMPTY")
    elif len(selected_rows) != row_limit:
        blockers.append("TRAIN_ROW_SELECTION_INVALID")
    selected_ids = [row.id for row in selected_rows]
    if len(selected_ids) != len(set(selected_ids)):
        blockers.append("TRAIN_ROW_SELECTION_INVALID")
    selected_hash = _sha256_text(json.dumps(selected_ids, ensure_ascii=False, separators=(",", ":")))
    manifest_id = str(manifest.get("manifest_id", ""))
    if config.get("dataset_manifest_id") != FORMAL_PUBLIC_MANIFEST_ID:
        blockers.append("DATASET_HASH_OR_ID_MISMATCH")
    for expected_key, actual in (
        ("expected_manifest_sha256", manifest_hash),
        ("expected_sft_sha256", sft_hash),
        ("expected_train_row_selection_sha256", selected_hash),
    ):
        expected = config.get(expected_key)
        if expected is not None and expected != actual:
            blocker = (
                "DATASET_HASH_OR_ID_MISMATCH"
                if "row_selection" not in expected_key
                else "TRAIN_ROW_SELECTION_INVALID"
            )
            blockers.append(blocker)
    facts = {
        "manifest_file": manifest_path.name,
        "manifest_sha256": manifest_hash,
        "manifest_id": manifest_id,
        "sft_file": sft_path.name,
        "sft_sha256": sft_hash,
        "selected_split": "train",
        "selected_row_count": len(selected_rows),
        "selected_row_ids_sha256": selected_hash,
        "non_train_rows_selected": 0,
    }
    return facts, selected_rows, list(dict.fromkeys(blockers))


def _stable_local_model_inventory(model_root: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    fingerprint_names = (
        "config.json",
        "generation_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "vocab.json",
        "merges.txt",
        "model.safetensors.index.json",
        "pytorch_model.bin.index.json",
    )
    fingerprints = {
        name: _sha256_file(model_root / name)
        for name in fingerprint_names
        if (model_root / name).is_file()
    }
    weight_files = sorted(
        path for pattern in ("*.safetensors", "*.bin") for path in model_root.glob(pattern) if path.is_file()
    )
    inventory = [{"name": path.name, "size": path.stat().st_size} for path in weight_files]
    return fingerprints, inventory


def _probe_sft_model_and_objective(
    config: dict[str, Any],
    rows: list[SFTDatasetRow],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    model_facts: dict[str, Any] = {
        "public_id": "Qwen/Qwen2.5-7B-Instruct",
        "local_files_only": True,
        "stable_fingerprints": {},
        "weight_inventory": [],
        "total_weight_bytes": 0,
        "minimum_weight_bytes": 12 * 1024**3,
        "geometry_matches_qwen2_5_7b": False,
        "snapshot_revision_sha256": None,
    }
    objective_facts: dict[str, Any] = {
        "records_checked": 0,
        "prompt_labels_masked": False,
        "assistant_target_present": False,
        "max_sequence_length": int(config.get("max_seq_length", 0) or 0),
    }
    runtime_value = config.get("base_model_runtime_path")
    if not isinstance(runtime_value, str) or not runtime_value or "<" in runtime_value or ">" in runtime_value:
        return model_facts, objective_facts, ["MODEL_PATH_UNRESOLVED"]
    model_root = Path(runtime_value).expanduser()
    if not model_root.is_absolute() or not model_root.is_dir():
        return model_facts, objective_facts, ["MODEL_PATH_UNRESOLVED"]
    try:
        from transformers import AutoConfig, AutoTokenizer

        trust_remote_code = bool(config.get("trust_remote_code", False))
        local_config = AutoConfig.from_pretrained(
            model_root.as_posix(),
            local_files_only=True,
            trust_remote_code=trust_remote_code,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            model_root.as_posix(),
            local_files_only=True,
            trust_remote_code=trust_remote_code,
        )
        fingerprints, inventory = _stable_local_model_inventory(model_root)
        if "config.json" not in fingerprints or not inventory:
            return model_facts, objective_facts, ["MODEL_LOCAL_LOAD_FAILED"]
        architectures = getattr(local_config, "architectures", None)
        geometry_matches = (
            getattr(local_config, "model_type", None) == "qwen2"
            and isinstance(architectures, list)
            and architectures == ["Qwen2ForCausalLM"]
            and getattr(local_config, "hidden_size", None) == 3584
            and getattr(local_config, "intermediate_size", None) == 18944
            and getattr(local_config, "num_hidden_layers", None) == 28
            and getattr(local_config, "num_attention_heads", None) == 28
            and getattr(local_config, "num_key_value_heads", None) == 4
            and getattr(local_config, "vocab_size", None) == 152064
        )
        total_weight_bytes = sum(int(item["size"]) for item in inventory)
        model_facts.update(
            {
                "stable_fingerprints": fingerprints,
                "weight_inventory": inventory,
                "total_weight_bytes": total_weight_bytes,
                "geometry_matches_qwen2_5_7b": geometry_matches,
                "snapshot_revision_sha256": _sha256_text(model_root.resolve().name),
            }
        )
        model_identity_blockers: list[str] = []
        if not geometry_matches:
            model_identity_blockers.append("MODEL_IDENTITY_MISMATCH")
        if total_weight_bytes < 12 * 1024**3:
            model_identity_blockers.append("MODEL_WEIGHT_INSUFFICIENT")
        if model_identity_blockers:
            return model_facts, objective_facts, model_identity_blockers
        max_seq_length = int(config.get("max_seq_length", 1024))
        records = [_assistant_only_training_record(row, tokenizer, max_seq_length=max_seq_length) for row in rows]
    except Exception as exc:
        blocker = "MAX_SEQUENCE_LENGTH_EXCEEDED" if "max_seq_length_exceeded" in str(exc) else "MODEL_LOCAL_LOAD_FAILED"
        if "assistant-only SFT labels unavailable" in str(exc) and blocker != "MAX_SEQUENCE_LENGTH_EXCEEDED":
            blocker = "ASSISTANT_ONLY_LABELS_INVALID"
        return model_facts, objective_facts, [blocker]

    if not records or not all(_assistant_only_record_is_valid(record) for record in records):
        return model_facts, objective_facts, ["ASSISTANT_ONLY_LABELS_INVALID"]
    objective_facts.update(
        {
            "records_checked": len(records),
            "prompt_labels_masked": True,
            "assistant_target_present": True,
            "maximum_observed_tokens": max(len(record["input_ids"]) for record in records),
        }
    )
    return model_facts, objective_facts, []


@dataclass(frozen=True)
class _SFTPreflightExecutionContext:
    config_path: Path
    config_sha256: str
    config_json: str
    repo_root: Path
    manifest_path: Path
    manifest_sha256: str
    manifest_id: str
    sft_path: Path
    sft_sha256: str
    selected_rows_json: tuple[str, ...]
    selected_row_ids_sha256: str
    model_root: Path
    model_inventory_sha256: str
    output_root: Path
    output_dir: Path
    output_identities: _BoundOutputIdentities
    output_facts_json: str

    def config_snapshot(self) -> dict[str, Any]:
        parsed = json.loads(self.config_json)
        if not isinstance(parsed, dict):
            raise ValueError("bound SFT config snapshot must remain an object")
        return cast(dict[str, Any], parsed)

    def selected_rows(self) -> tuple[SFTDatasetRow, ...]:
        return tuple(SFTDatasetRow(**json.loads(record)) for record in self.selected_rows_json)


class SFTPreflightDriftError(RuntimeError):
    def __init__(self, blockers: list[str]) -> None:
        self.blockers = list(dict.fromkeys(blockers))
        super().__init__(",".join(self.blockers))


def _preflight_input_drift_blockers(
    execution_context: _SFTPreflightExecutionContext,
) -> list[str]:
    blockers: list[str] = []
    try:
        config_matches = (
            execution_context.config_path.is_file()
            and not execution_context.config_path.is_symlink()
            and _sha256_file(execution_context.config_path) == execution_context.config_sha256
        )
    except (OSError, RuntimeError):
        config_matches = False
    if not config_matches:
        blockers.append("CONFIG_DRIFT_DETECTED")
    try:
        if _sha256_file(execution_context.manifest_path) != execution_context.manifest_sha256:
            blockers.append("MANIFEST_DRIFT_DETECTED")
    except (OSError, RuntimeError):
        blockers.append("MANIFEST_DRIFT_DETECTED")
    try:
        if _sha256_file(execution_context.sft_path) != execution_context.sft_sha256:
            blockers.append("SFT_DRIFT_DETECTED")
    except (OSError, RuntimeError):
        blockers.append("SFT_DRIFT_DETECTED")
    try:
        fingerprints, inventory = _stable_local_model_inventory(execution_context.model_root)
        current_inventory_sha256 = _sha256_text(
            json.dumps(
                {"fingerprints": fingerprints, "weights": inventory},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        if current_inventory_sha256 != execution_context.model_inventory_sha256:
            blockers.append("MODEL_DRIFT_DETECTED")
    except (OSError, RuntimeError):
        blockers.append("MODEL_DRIFT_DETECTED")
    return list(dict.fromkeys(blockers))


def _blocked_sft_preflight_result(blockers: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "voice2task-sft-preflight-v1",
        "ready": False,
        "status": "blocked",
        "blockers": list(dict.fromkeys(blockers)),
        "git": {},
        "config": {},
        "dataset": {},
        "model": {},
        "runtime": {},
        "gpu": {},
        "output": {},
        "objective": {},
    }


def _repo_root_from_canonical_manifest(manifest_path: Path) -> Path | None:
    try:
        resolved_manifest = manifest_path.expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    relative_parts = FORMAL_PUBLIC_MANIFEST_RELATIVE_PATH.parts
    if resolved_manifest.parts[-len(relative_parts) :] != relative_parts:
        return None
    repo_root = resolved_manifest.parents[len(relative_parts) - 1]
    expected_manifest = repo_root / FORMAL_PUBLIC_MANIFEST_RELATIVE_PATH
    try:
        if expected_manifest.resolve(strict=True) != resolved_manifest:
            return None
    except (OSError, RuntimeError):
        return None
    return repo_root


def _git_config_path_state(
    config_path: Path,
    repo_root: Path,
) -> tuple[bool, bool, bool]:
    try:
        relative_path = config_path.relative_to(repo_root).as_posix()
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", "--", relative_path],
            cwd=repo_root,
            check=False,
            capture_output=True,
            timeout=30,
        )
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative_path],
            cwd=repo_root,
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
        return False, False, False
    ignored_known = ignored.returncode in (0, 1)
    tracked_known = tracked.returncode in (0, 1)
    return ignored.returncode == 0, tracked.returncode == 0, ignored_known and tracked_known


def _probe_private_sft_config(
    config_path: Path,
    repo_root: Path,
) -> tuple[dict[str, Any], list[str]]:
    candidate = config_path.expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    private_root = repo_root / PRIVATE_SFT_CONFIG_DIRECTORY
    facts: dict[str, Any] = {
        "under_private_runtime": False,
        "nonsymlink": False,
        "git_ignored": False,
        "git_tracked": False,
    }
    try:
        candidate.relative_to(private_root)
    except ValueError:
        return facts, ["CONFIG_PATH_NOT_PRIVATE"]

    current = repo_root
    symlink_detected = False
    try:
        for part in candidate.relative_to(repo_root).parts:
            current = current / part
            if current.is_symlink():
                symlink_detected = True
                break
    except (OSError, RuntimeError, ValueError):
        return facts, ["CONFIG_PATH_NOT_PRIVATE"]
    if symlink_detected:
        return facts, ["CONFIG_PATH_SYMLINK"]
    try:
        resolved_candidate = candidate.resolve(strict=True)
        resolved_private_root = private_root.resolve(strict=True)
        resolved_candidate.relative_to(resolved_private_root)
    except (OSError, RuntimeError, ValueError):
        return facts, ["CONFIG_PATH_NOT_PRIVATE"]

    ignored, tracked, available = _git_config_path_state(resolved_candidate, repo_root)
    facts.update(
        {
            "under_private_runtime": True,
            "nonsymlink": True,
            "git_ignored": ignored,
            "git_tracked": tracked,
        }
    )
    blockers: list[str] = []
    if not available:
        blockers.append("CONFIG_GIT_POLICY_UNAVAILABLE")
    else:
        if not ignored:
            blockers.append("CONFIG_FILE_NOT_IGNORED")
        if tracked:
            blockers.append("CONFIG_FILE_TRACKED")
    return facts, blockers


def _run_sft_preflight_core_unchecked(
    config_path: Path,
    manifest_path: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], _SFTPreflightExecutionContext | None]:
    if not config_path.is_file():
        return _blocked_sft_preflight_result(["CONFIG_FILE_MISSING"]), None
    repo_root = _repo_root_from_canonical_manifest(manifest_path)
    if repo_root is None:
        return _blocked_sft_preflight_result(["MANIFEST_PATH_NOT_CANONICAL"]), None
    private_config_facts, private_config_blockers = _probe_private_sft_config(
        config_path,
        repo_root,
    )
    if private_config_blockers:
        result = _blocked_sft_preflight_result(private_config_blockers)
        result["config"] = {"private_file": private_config_facts}
        return result, None
    try:
        manifest = read_json(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return _blocked_sft_preflight_result(["DATASET_HASH_OR_ID_MISMATCH"]), None
    files = manifest.get("files")
    if (
        manifest.get("manifest_id") != FORMAL_PUBLIC_MANIFEST_ID
        or not isinstance(files, dict)
        or files.get("sft") != FORMAL_PUBLIC_SFT_RELATIVE_PATH.as_posix()
    ):
        return _blocked_sft_preflight_result(["DATASET_HASH_OR_ID_MISMATCH"]), None
    try:
        config = _load_config(config_path)
    except (OSError, TypeError, ValueError):
        return _blocked_sft_preflight_result(["CONFIG_LOAD_FAILED"]), None
    config_facts, config_blockers = _smoke_config_facts(config_path, config)
    config_facts["private_file"] = private_config_facts
    git_facts, git_blockers = _probe_sft_git(repo_root)
    runtime_facts, dependency_blockers = _probe_sft_dependencies()
    gpu_facts, gpu_blockers = _probe_sft_gpu()
    dataset_facts, selected_rows, dataset_blockers = _load_selected_smoke_rows(manifest_path, config)

    runtime_value = config.get("base_model_runtime_path")
    model_path_valid = (
        isinstance(runtime_value, str)
        and bool(runtime_value)
        and "<" not in runtime_value
        and ">" not in runtime_value
        and Path(runtime_value).expanduser().is_absolute()
        and Path(runtime_value).expanduser().is_dir()
    )
    model_blockers: list[str] = []
    model_facts: dict[str, Any] = {
        "public_id": "Qwen/Qwen2.5-7B-Instruct",
        "local_files_only": config.get("local_files_only") is True,
        "stable_fingerprints": {},
        "weight_inventory": [],
    }
    objective_facts: dict[str, Any] = {"records_checked": 0}
    if not model_path_valid:
        model_blockers.append("MODEL_PATH_UNRESOLVED")
    elif not config_blockers and not dependency_blockers and not dataset_blockers and selected_rows:
        model_facts, objective_facts, model_blockers = _probe_sft_model_and_objective(config, selected_rows)

    output_facts = validate_sft_output_policy(config, output_dir, repo_root=repo_root)
    blockers = list(
        dict.fromkeys(
            [
                *config_blockers,
                *git_blockers,
                *dependency_blockers,
                *gpu_blockers,
                *dataset_blockers,
                *model_blockers,
                *[str(code) for code in output_facts["blockers"]],
            ]
        )
    )
    ready = not blockers
    public_result = {
        "schema_version": "voice2task-sft-preflight-v1",
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "blockers": blockers,
        "git": git_facts,
        "config": config_facts,
        "dataset": dataset_facts,
        "model": model_facts,
        "runtime": runtime_facts,
        "gpu": gpu_facts,
        "output": output_facts,
        "objective": objective_facts,
    }
    if not ready or repo_root is None:
        return public_result, None

    sft_path = _resolve_manifest_file(
        manifest_path,
        files.get("sft") if isinstance(files, dict) else None,
    )
    runtime_value = config.get("base_model_runtime_path")
    raw_output_root = config.get("output_root")
    if (
        sft_path is None
        or not isinstance(runtime_value, str)
        or not isinstance(raw_output_root, str)
    ):
        return public_result, None
    model_fingerprints = model_facts.get("stable_fingerprints")
    model_inventory = model_facts.get("weight_inventory")
    if not isinstance(model_fingerprints, dict) or not isinstance(model_inventory, list):
        return public_result, None
    resolved_output_root = Path(raw_output_root).expanduser().resolve(strict=True)
    resolved_output_dir = output_dir.expanduser().resolve(strict=False)
    output_identities = _bind_output_identities(resolved_output_root, resolved_output_dir.parent)
    context = _SFTPreflightExecutionContext(
        config_path=config_path.resolve(strict=True),
        config_sha256=str(config_facts["config_sha256"]),
        config_json=json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        repo_root=repo_root.resolve(strict=True),
        manifest_path=manifest_path.resolve(strict=True),
        manifest_sha256=str(dataset_facts["manifest_sha256"]),
        manifest_id=str(dataset_facts["manifest_id"]),
        sft_path=sft_path.resolve(strict=True),
        sft_sha256=str(dataset_facts["sft_sha256"]),
        selected_rows_json=tuple(
            json.dumps(row.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for row in selected_rows
        ),
        selected_row_ids_sha256=str(dataset_facts["selected_row_ids_sha256"]),
        model_root=Path(runtime_value).expanduser().resolve(strict=True),
        model_inventory_sha256=_sha256_text(
            json.dumps(
                {"fingerprints": model_fingerprints, "weights": model_inventory},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        ),
        output_root=resolved_output_root,
        output_dir=resolved_output_dir,
        output_identities=output_identities,
        output_facts_json=json.dumps(
            output_facts,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    return public_result, context


def _run_sft_preflight_core(
    config_path: Path,
    manifest_path: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], _SFTPreflightExecutionContext | None]:
    try:
        return _run_sft_preflight_core_unchecked(config_path, manifest_path, output_dir)
    except Exception:
        return _blocked_sft_preflight_result(["PREFLIGHT_INTERNAL_ERROR"]), None


def run_sft_preflight(config_path: Path, manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    public_result, _ = _run_sft_preflight_core(config_path, manifest_path, output_dir)
    return public_result


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


def _metadata_from_sft_execution_context(
    preflight: dict[str, Any],
    execution_context: _SFTPreflightExecutionContext,
) -> dict[str, Any]:
    config = execution_context.config_snapshot()
    output_dir = execution_context.output_dir
    adapter_path = output_dir / "adapter"
    metadata_path = output_dir / "adapter_metadata.json"
    runtime_facts = preflight.get("runtime")
    versions = runtime_facts.get("versions") if isinstance(runtime_facts, dict) else None
    package_versions = dict(versions) if isinstance(versions, dict) else {}
    if isinstance(runtime_facts, dict) and isinstance(runtime_facts.get("python"), str):
        package_versions["python"] = str(runtime_facts["python"])
    dataset_load = {
        "manifest_id": execution_context.manifest_id,
        "manifest_sha256": execution_context.manifest_sha256,
        "dataset_key": "sft",
        "dataset_path": execution_context.sft_path.as_posix(),
        "sft_sha256": execution_context.sft_sha256,
        "loaded_rows": len(execution_context.selected_rows_json),
        "selected_row_ids_sha256": execution_context.selected_row_ids_sha256,
    }
    return {
        "stage": "sft",
        "stack": _training_stack("sft"),
        "base_model": _public_base_model(config),
        "adapter_path": adapter_path.as_posix(),
        "dataset_manifest_id": execution_context.manifest_id,
        "dataset_manifest_path": execution_context.manifest_path.as_posix(),
        "dataset_load": dataset_load,
        "hyperparameters": config,
        "dry_run": False,
        "release_status": "not_released",
        "adapter_release_status": "not_released",
        "training_status": "pending_heavy_training",
        "formatting_policy": dict(FORMATTING_POLICY),
        "loss_mask_policy": _loss_mask_policy("sft"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "package_versions": package_versions,
        "gpu_selection_policy": _gpu_selection_policy(config),
        "heavy_training_gate": _heavy_training_gate(config, False),
        "output_paths": _output_paths(
            config=config,
            output_dir=output_dir,
            adapter_path=adapter_path,
            metadata_path=metadata_path,
        ),
        "command_summary": _command_summary(
            stage="sft",
            config_path=execution_context.config_path,
            manifest_path=execution_context.manifest_path,
            output_dir=output_dir,
            dry_run=False,
        ),
        "training_command": (
            f"voice2task-train sft --config {execution_context.config_path.as_posix()} "
            f"--manifest {execution_context.manifest_path.as_posix()} "
            f"--output-dir {output_dir.as_posix()} --run-training"
        ),
        "metadata_path": metadata_path.as_posix(),
        "preflight": preflight,
        "notes": "Training entrypoint passed shared preflight; real execution remains smoke-bounded.",
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


def _blocked_sft_result(
    metadata: dict[str, Any],
    *,
    status: str,
    blockers: list[str],
) -> dict[str, Any]:
    metadata["release_status"] = "not_released"
    metadata["training_status"] = status
    metadata["trainer_available"] = False
    metadata["blockers"] = list(dict.fromkeys(blockers))
    metadata["heavy_training_gate"]["will_run_heavy_training"] = False
    metadata["notes"] = "Real SFT execution was blocked before model weights loaded."
    return metadata


def _minimal_blocked_sft_preflight_result(
    preflight: dict[str, Any],
    *,
    status: str,
    blockers: list[str],
) -> dict[str, Any]:
    config_facts = preflight.get("config")
    config_allows = isinstance(config_facts, dict) and config_facts.get("allow_heavy_training") is True
    return {
        "schema_version": "voice2task-training-result-v1",
        "stage": "sft",
        "dry_run": False,
        "release_status": "not_released",
        "adapter_release_status": "not_released",
        "training_status": status,
        "trainer_available": False,
        "blockers": list(dict.fromkeys(blockers)),
        "preflight": preflight,
        "heavy_training_gate": {
            "cli_run_training": True,
            "config_allow_heavy_training": config_allows,
            "will_run_heavy_training": False,
        },
        "notes": "Real SFT execution was blocked by shared preflight before legacy metadata reads.",
    }


def _blocked_training_output_policy_result(stage: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "voice2task-training-result-v1",
        "stage": stage,
        "dry_run": False,
        "release_status": "not_released",
        "adapter_release_status": "not_released",
        "training_status": "training_blocked_by_output_policy",
        "trainer_available": False,
        "blockers": list(dict.fromkeys(blockers)),
        "heavy_training_gate": {
            "cli_run_training": True,
            "config_allow_heavy_training": False,
            "will_run_heavy_training": False,
        },
        "notes": "Training was blocked by the output policy before dependency imports or model loading.",
    }


def _clean_evaluation_truth_surface() -> dict[str, Any]:
    return {
        "acquisition_source_status": "UNAVAILABLE",
        "authoritatively_bound_binding_count": 0,
        "human_acceptance_status": "NOT_RECORDED",
        "protocol_freeze_status": "NOT_FROZEN",
        "clean_population_status": "NOT_MATERIALIZED",
        "freeze_authorized": False,
        "execution_readiness": False,
    }


@dataclass(frozen=True)
class _AdapterStateSnapshot:
    tensors: tuple[tuple[str, int, str], ...]
    trainable_parameter_count: int
    all_finite: bool
    digest: str


def _capture_adapter_state(model: Any) -> _AdapterStateSnapshot:
    import torch

    tensors: list[tuple[str, int, str]] = []
    digest = hashlib.sha256()
    trainable_parameter_count = 0
    all_finite = True
    named_parameters = getattr(model, "named_parameters", None)
    if not callable(named_parameters):
        return _AdapterStateSnapshot((), 0, False, hashlib.sha256().hexdigest())
    for name, parameter in sorted(named_parameters(), key=lambda item: item[0]):
        if not bool(getattr(parameter, "requires_grad", False)):
            continue
        detached = parameter.detach().cpu().contiguous()
        trainable_parameter_count += int(detached.numel())
        normalized_name = str(name).lower()
        if "lora_" not in normalized_name and "adapter" not in normalized_name:
            continue
        raw = detached.view(torch.uint8).numpy().tobytes()
        tensor_hash = hashlib.sha256(raw).hexdigest()
        parameter_count = int(detached.numel())
        all_finite = all_finite and bool(torch.isfinite(detached.float()).all().item())
        tensors.append((str(name), parameter_count, tensor_hash))
        digest.update(str(name).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(tuple(detached.shape)).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(detached.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(raw)
    return _AdapterStateSnapshot(
        tensors=tuple(tensors),
        trainable_parameter_count=trainable_parameter_count,
        all_finite=all_finite,
        digest=digest.hexdigest(),
    )


def _adapter_update_evidence(
    before: _AdapterStateSnapshot,
    after: _AdapterStateSnapshot,
) -> dict[str, Any]:
    before_hashes = {name: tensor_hash for name, _, tensor_hash in before.tensors}
    after_hashes = {name: tensor_hash for name, _, tensor_hash in after.tensors}
    changed = sum(
        1
        for name, tensor_hash in after_hashes.items()
        if before_hashes.get(name) != tensor_hash
    )
    same_tensor_set = before_hashes.keys() == after_hashes.keys()
    return {
        "trainable_parameter_count": after.trainable_parameter_count,
        "adapter_tensor_count": len(after.tensors),
        "adapter_state_digest_before": before.digest,
        "adapter_state_digest_after": after.digest,
        "changed_adapter_tensor_count": changed if same_tensor_set else 0,
        "all_adapter_tensors_finite": before.all_finite and after.all_finite,
    }


def _sft_smoke_postconditions(metadata: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    observed_steps = metadata.get("observed_optimizer_steps")
    if not isinstance(observed_steps, int) or isinstance(observed_steps, bool) or observed_steps != 1:
        blockers.append("OPTIMIZER_STEP_MISMATCH")
    configured = metadata.get("hyperparameters")
    configured_rows = configured.get("max_train_rows") if isinstance(configured, dict) else None
    rows_used = metadata.get("training_rows_used")
    if (
        not isinstance(configured_rows, int)
        or isinstance(configured_rows, bool)
        or configured_rows not in (1, 2)
        or rows_used != configured_rows
    ):
        blockers.append("TRAIN_ROW_SELECTION_INVALID")
    metrics = metadata.get("train_result_metrics")
    loss = metrics.get("train_loss") if isinstance(metrics, dict) else None
    if isinstance(loss, bool) or not isinstance(loss, int | float) or not math.isfinite(float(loss)):
        blockers.append("TRAINING_LOSS_INVALID")

    trainable_parameter_count = metadata.get("trainable_parameter_count")
    adapter_tensor_count = metadata.get("adapter_tensor_count")
    before_digest = metadata.get("adapter_state_digest_before")
    after_digest = metadata.get("adapter_state_digest_after")
    changed_adapter_tensor_count = metadata.get("changed_adapter_tensor_count")
    all_adapter_tensors_finite = metadata.get("all_adapter_tensors_finite")
    if (
        type(trainable_parameter_count) is not int
        or trainable_parameter_count <= 0
        or type(adapter_tensor_count) is not int
        or adapter_tensor_count <= 0
        or not isinstance(before_digest, str)
        or len(before_digest) != 64
        or not isinstance(after_digest, str)
        or len(after_digest) != 64
        or before_digest == after_digest
        or type(changed_adapter_tensor_count) is not int
        or changed_adapter_tensor_count <= 0
        or all_adapter_tensors_finite is not True
    ):
        blockers.append("ADAPTER_UPDATE_NOT_OBSERVED")

    adapter_path = Path(str(metadata.get("adapter_path", "")))
    try:
        adapter_files = sorted(
            path for path in adapter_path.rglob("*") if path.is_file() and path.stat().st_size > 0
        )
        metadata["adapter_files"] = [
            {
                "name": path.relative_to(adapter_path).as_posix(),
                "size": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
            for path in adapter_files
        ]
    except OSError:
        adapter_files = []
        metadata["adapter_files"] = []
    adapter_names = {path.name for path in adapter_files}
    has_adapter_config = "adapter_config.json" in adapter_names
    has_adapter_weights = bool(adapter_names & {"adapter_model.safetensors", "adapter_model.bin"})
    if not has_adapter_config or not has_adapter_weights:
        blockers.append("ADAPTER_OUTPUT_INVALID")
    metadata_path = Path(str(metadata.get("metadata_path", "")))
    run_root = metadata_path.parent
    try:
        run_files = [path for path in run_root.rglob("*") if path.is_file()]
    except OSError:
        run_files = []
        blockers.append("ADAPTER_OUTPUT_INVALID")
    full_weight_names = {
        "model.safetensors",
        "model.safetensors.index.json",
        "pytorch_model.bin",
        "pytorch_model.bin.index.json",
    }
    if any(
        path.name in full_weight_names
        or path.name.startswith("model-")
        or path.name.startswith("pytorch_model-")
        for path in run_files
    ):
        blockers.append("FULL_MODEL_WEIGHTS_DETECTED")
    return list(dict.fromkeys(blockers))


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
        report_to=list(config.get("report_to", [])),
        bf16=bool(config.get("bf16", False)),
        fp16=bool(config.get("fp16", False)),
        tf32=bool(config.get("tf32", False)),
        gradient_checkpointing=bool(config.get("gradient_checkpointing", False)),
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


def _record_bound_sft_training_selection(
    metadata: dict[str, Any],
    config: dict[str, Any],
    execution_context: _SFTPreflightExecutionContext,
) -> list[SFTDatasetRow]:
    rows = list(execution_context.selected_rows())
    row_limit = int(config["max_train_rows"])
    _record_sft_training_row_selection(
        metadata,
        split="train",
        rows=rows,
        row_limit=row_limit,
        source_ids=None,
        loaded_rows_before_limit=len(rows),
        loaded_rows_before_source_filter=len(rows),
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


def _assistant_token_indices_from_offsets(
    *,
    offsets: list[tuple[int, int]],
    assistant_start: int,
    assistant_end: int,
) -> tuple[list[int], list[str]]:
    if not offsets:
        return [], ["token_offsets_unavailable"]
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
    return sorted(assistant_indices), []


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
    assistant_indices, evidence_gaps = _assistant_token_indices_from_offsets(
        offsets=offsets,
        assistant_start=assistant_start,
        assistant_end=assistant_end,
    )
    if evidence_gaps:
        return [], evidence_gaps
    assistant_index_set = set(assistant_indices)

    return [
        token_id if index in assistant_index_set else -100
        for index, token_id in enumerate(input_ids)
    ], []


def _assistant_only_record_is_valid(record: dict[str, Any]) -> bool:
    input_ids = _token_list(record.get("input_ids"))
    attention_mask = _token_list(record.get("attention_mask"))
    labels = _token_list(record.get("labels"))
    raw_indices = record.get("assistant_token_indices")
    if not isinstance(raw_indices, list) or not raw_indices:
        return False
    if not all(type(index) is int for index in raw_indices):
        return False
    assistant_indices = cast(list[int], raw_indices)
    if assistant_indices != sorted(set(assistant_indices)):
        return False
    if assistant_indices != list(range(assistant_indices[0], assistant_indices[-1] + 1)):
        return False
    if not input_ids or len(input_ids) != len(attention_mask) or len(input_ids) != len(labels):
        return False
    if assistant_indices[0] < 0 or assistant_indices[-1] >= len(input_ids):
        return False
    assistant_set = set(assistant_indices)
    for index, (token_id, label) in enumerate(zip(input_ids, labels, strict=True)):
        if index in assistant_set:
            if label == -100 or label != token_id:
                return False
        elif label != -100:
            return False
    return True


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
    assistant_indices, index_gaps = _assistant_token_indices_from_offsets(
        offsets=offsets,
        assistant_start=assistant_start,
        assistant_end=assistant_end,
    )
    if index_gaps:
        gaps = ",".join(index_gaps)
        raise ValueError(f"assistant-only SFT labels unavailable: {gaps}")
    record = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
        "assistant_token_indices": assistant_indices,
    }
    if not _assistant_only_record_is_valid(record):
        raise ValueError("assistant-only SFT labels unavailable: assistant_label_region_invalid")
    return record


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


def _run_real_sft(
    metadata: dict[str, Any],
    config: dict[str, Any],
    manifest_path: Path,
    output_dir: Path,
    *,
    execution_context: _SFTPreflightExecutionContext | object | None = None,
) -> None:
    if not isinstance(execution_context, _SFTPreflightExecutionContext):
        raise RuntimeError("PREFLIGHT_CONTEXT_MISSING")
    drift_blockers = _preflight_input_drift_blockers(execution_context)
    if drift_blockers:
        raise SFTPreflightDriftError(drift_blockers)
    _, gpu_blockers = _probe_sft_gpu()
    if gpu_blockers:
        raise SFTPreflightDriftError(gpu_blockers)
    config = execution_context.config_snapshot()
    output_dir = execution_context.output_dir
    _claim_sft_output_directory(
        config,
        output_dir,
        repo_root=execution_context.repo_root,
        expected_output_path_sha256=json.loads(execution_context.output_facts_json).get("output_path_sha256"),
        expected_identities=execution_context.output_identities,
    )

    from datasets import Dataset  # type: ignore[import-not-found, unused-ignore]
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTTrainer  # type: ignore[import-not-found, unused-ignore]

    rows = _record_bound_sft_training_selection(metadata, config, execution_context)
    base_model = execution_context.model_root.as_posix()
    local_files_only = bool(config.get("local_files_only", True))
    trust_remote_code = bool(config.get("trust_remote_code", False))
    tokenizer = AutoTokenizer.from_pretrained(
        base_model,
        local_files_only=local_files_only,
        trust_remote_code=trust_remote_code,
    )
    if getattr(tokenizer, "pad_token_id", None) is None:
        if getattr(tokenizer, "eos_token_id", None) is None or getattr(tokenizer, "eos_token", None) is None:
            raise RuntimeError("TOKENIZER_PAD_TOKEN_UNAVAILABLE")
        tokenizer.pad_token = tokenizer.eos_token
    max_seq_length = int(config.get("max_seq_length", 1024))
    records = [_assistant_only_training_record(row, tokenizer, max_seq_length=max_seq_length) for row in rows]
    dataset = Dataset.from_list(records)
    import torch

    _, immediate_gpu_blockers = _probe_sft_gpu()
    if immediate_gpu_blockers:
        raise SFTPreflightDriftError(immediate_gpu_blockers)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        local_files_only=local_files_only,
        trust_remote_code=trust_remote_code,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=bool(config.get("low_cpu_mem_usage", True)),
    )
    if bool(config.get("gradient_checkpointing", False)):
        gradient_checkpointing_enable = getattr(model, "gradient_checkpointing_enable", None)
        if callable(gradient_checkpointing_enable):
            gradient_checkpointing_enable()
        model.config.use_cache = False
    else:
        model.config.use_cache = bool(config.get("use_cache", True))
    metadata["runtime_options"] = {
        "torch_dtype": "bfloat16",
        "bf16": bool(config.get("bf16", False)),
        "fp16": bool(config.get("fp16", False)),
        "tf32": bool(config.get("tf32", False)),
        "gradient_checkpointing": bool(config.get("gradient_checkpointing", False)),
        "use_cache": bool(getattr(model.config, "use_cache", False)),
        "low_cpu_mem_usage": bool(config.get("low_cpu_mem_usage", True)),
        "local_files_only": local_files_only,
        "trust_remote_code": trust_remote_code,
        "seed": int(config.get("seed", 42)),
        "max_steps": int(config.get("max_steps", -1)),
        "max_train_rows": config.get("max_train_rows"),
        "per_device_train_batch_size": int(config.get("per_device_train_batch_size", 1)),
        "gradient_accumulation_steps": int(config.get("gradient_accumulation_steps", 1)),
        "save_strategy": str(config.get("save_strategy", "no")),
        "logging_steps": int(config.get("logging_steps", 1)),
    }
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=_training_arguments(config, output_dir),
        peft_config=_lora_config(config),
        data_collator=_AssistantOnlyCausalLmDataCollator(tokenizer),
        **_sft_trainer_tokenizer_kwargs(SFTTrainer, tokenizer),
    )
    adapter_state_before = _capture_adapter_state(trainer.model)
    train_result = trainer.train()
    adapter_state_after = _capture_adapter_state(trainer.model)
    metadata.update(_adapter_update_evidence(adapter_state_before, adapter_state_after))
    _record_sft_training_budget_metadata(
        metadata,
        config=config,
        train_row_count=len(rows),
        records=records,
        trainer=trainer,
        train_result=train_result,
    )
    trainer.model.save_pretrained(metadata["adapter_path"])


def _run_real_dpo(
    metadata: dict[str, Any],
    config: dict[str, Any],
    manifest_path: Path,
    output_dir: Path,
    *,
    repo_root: Path,
) -> None:
    _claim_sft_output_directory(config, output_dir, repo_root=repo_root)

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
    if dry_run:
        config = _load_config(config_path)
        metadata = _metadata_common(
            stage="sft",
            config_path=config_path,
            manifest_path=manifest_path,
            output_dir=output_dir,
            dry_run=True,
        )
        _record_sft_training_selection_from_config(metadata, config, manifest_path)
        metadata["trainer_available"] = False
        write_json(Path(metadata["metadata_path"]), metadata)
        return metadata

    preflight, execution_context = _run_sft_preflight_core(config_path, manifest_path, output_dir)
    preflight_blockers = [str(code) for code in preflight.get("blockers", [])]
    if preflight.get("ready") is not True:
        if "CONFIG_HEAVY_TRAINING_NOT_ALLOWED" in preflight_blockers:
            status = "training_skipped_by_config"
        elif any(code.startswith("OUTPUT_") for code in preflight_blockers):
            status = "training_blocked_by_output_policy"
        elif any(code.startswith("DEPENDENCY_") for code in preflight_blockers):
            status = "training_unavailable"
        else:
            status = "training_blocked_by_preflight"
        return _minimal_blocked_sft_preflight_result(preflight, status=status, blockers=preflight_blockers)

    if not isinstance(execution_context, _SFTPreflightExecutionContext):
        return _minimal_blocked_sft_preflight_result(
            preflight,
            status="training_blocked_by_preflight",
            blockers=["PREFLIGHT_CONTEXT_MISSING"],
        )
    config = execution_context.config_snapshot()
    metadata = _metadata_from_sft_execution_context(preflight, execution_context)
    final_output_policy = validate_sft_output_policy(
        config,
        execution_context.output_dir,
        repo_root=execution_context.repo_root,
    )
    if final_output_policy.get("ready") is not True:
        return _blocked_sft_result(
            metadata,
            status="training_blocked_by_output_policy",
            blockers=[str(code) for code in final_output_policy.get("blockers", [])],
        )
    metadata["trainer_available"] = True
    try:
        _run_real_sft(
            metadata,
            config,
            execution_context.manifest_path,
            execution_context.output_dir,
            execution_context=execution_context,
        )
    except SFTOutputPolicyError as exc:
        return _blocked_sft_result(
            metadata,
            status="training_blocked_by_output_policy",
            blockers=exc.blockers,
        )
    except SFTPreflightDriftError as exc:
        return _blocked_sft_result(
            metadata,
            status="training_blocked_by_preflight",
            blockers=exc.blockers,
        )
    except Exception as exc:
        _write_training_failed(metadata, "sft", exc)
        raise
    postcondition_blockers = _sft_smoke_postconditions(metadata)
    metadata["clean_evaluation"] = _clean_evaluation_truth_surface()
    if postcondition_blockers:
        metadata["training_status"] = "training_failed"
        metadata["blockers"] = postcondition_blockers
        metadata["smoke_status"] = "SMOKE_FAILED"
        metadata["notes"] = "SFT smoke ran but failed bounded completion postconditions."
    else:
        metadata["release_status"] = "not_released"
        metadata["training_status"] = "training_completed"
        metadata["smoke_status"] = "SMOKE_COMPLETED"
        metadata["notes"] = (
            "One-step SFT infrastructure smoke completed; this is not a model-improvement or readiness claim."
        )
    write_json(Path(metadata["metadata_path"]), metadata)
    return metadata


def run_dpo(config_path: Path, manifest_path: Path, output_dir: Path, dry_run: bool = True) -> dict[str, Any]:
    repo_root: Path | None = None
    if not dry_run:
        repo_root = _git_repository_root_for_manifest(manifest_path)
        if repo_root is None:
            return _blocked_training_output_policy_result("dpo", ["OUTPUT_REPOSITORY_UNAVAILABLE"])
    config = _load_config(config_path)
    if not dry_run:
        output_policy = validate_sft_output_policy(config, output_dir, repo_root=repo_root)
        if output_policy.get("ready") is not True:
            return _blocked_training_output_policy_result(
                "dpo",
                [str(code) for code in output_policy.get("blockers", [])],
            )
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
    if not dry_run and not _train_dependencies_available():
        return _write_training_plan(metadata, "dpo")
    metadata["trainer_available"] = not dry_run
    if not dry_run:
        try:
            if repo_root is None:
                raise SFTOutputPolicyError(["OUTPUT_REPOSITORY_UNAVAILABLE"])
            _run_real_dpo(metadata, config, manifest_path, output_dir, repo_root=repo_root)
        except SFTOutputPolicyError as exc:
            return _blocked_sft_result(
                metadata,
                status="training_blocked_by_output_policy",
                blockers=exc.blockers,
            )
        except Exception as exc:
            _write_training_failed(metadata, "dpo", exc)
            raise
        metadata["release_status"] = "not_released"
        metadata["training_status"] = "training_completed"
        metadata["notes"] = "DPO training ran locally; adapter metadata is not a public checkpoint release."
    write_json(Path(metadata["metadata_path"]), metadata)
    return metadata
