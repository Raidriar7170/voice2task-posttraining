from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from voice2task.dpo import validate_dpo_pair
from voice2task.io import read_json, read_jsonl
from voice2task.schemas import DPOPair, SFTDatasetRow, ValidationError, validate_public_record

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_PUBLIC_MANIFEST_REF = "data/public-samples/manifest_public_sample.json"
FORMAL_TRAIN_ARTIFACT_REF = "data/public-samples/sft_train_public_sample.jsonl"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    failures: list[dict[str, str]]
    counts: dict[str, int]


def _resolve_train_only_artifact(manifest_path: Path, raw_path: object) -> Path:
    if not isinstance(raw_path, str) or not raw_path or "\\" in raw_path:
        raise ValueError("train-only artifact path must be a relative canonical POSIX path")
    relative_path = PurePosixPath(raw_path)
    is_windows_drive_path = len(raw_path) >= 2 and raw_path[0].isalpha() and raw_path[1] == ":"
    if relative_path.is_absolute() or is_windows_drive_path or ".." in relative_path.parts:
        raise ValueError("train-only artifact path must remain within the manifest directory")
    if relative_path.as_posix() != raw_path or any(part in {"", "."} for part in relative_path.parts):
        raise ValueError("train-only artifact path must be canonical")

    is_formal_manifest = manifest_path.resolve() == (REPO_ROOT / FORMAL_PUBLIC_MANIFEST_REF).resolve()
    if is_formal_manifest:
        if raw_path != FORMAL_TRAIN_ARTIFACT_REF:
            raise ValueError("formal train-only artifact path must use the canonical repo-relative reference")
        root = REPO_ROOT
    else:
        if len(relative_path.parts) != 1:
            raise ValueError("non-formal train-only artifact path must be a canonical basename")
        root = manifest_path.parent
    if root.is_symlink():
        raise ValueError("train-only artifact root must not be a symlink")
    candidate = root.joinpath(*relative_path.parts)
    current = root
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("train-only artifact path must not contain symlinks")
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError("train-only artifact must exist within the manifest directory") from exc
    if not candidate.is_file():
        raise ValueError("train-only artifact must be a regular file")
    return candidate


def _parse_canonical_jsonl(payload: bytes) -> list[dict[str, Any]]:
    try:
        text = payload.decode("utf-8")
        rows = [json.loads(line) for line in text.splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("train-only artifact must contain UTF-8 JSONL") from exc
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("train-only artifact rows must be objects")
    canonical = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")
    if payload != canonical:
        raise ValueError("train-only artifact bytes must be canonical JSONL")
    return rows


def _validate_train_only_artifact(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    mixed_sft_rows: list[dict[str, Any]],
    public: bool,
) -> int:
    files = manifest.get("files")
    source_summary = manifest.get("source_summary")
    files = files if isinstance(files, dict) else {}
    source_summary = source_summary if isinstance(source_summary, dict) else {}
    path_present = "sft_train" in files
    metadata_present = "sft_train_artifact" in source_summary
    if not path_present and not metadata_present:
        if public:
            raise ValueError("public datasets require a complete train-only artifact binding")
        return 0
    if not path_present or not metadata_present:
        raise ValueError("train-only artifact path and integrity metadata must both be present")

    binding = source_summary["sft_train_artifact"]
    if not isinstance(binding, dict):
        raise ValueError("train-only artifact metadata must be an object")
    sha256 = binding.get("sha256")
    row_count = binding.get("row_count")
    if (
        not isinstance(sha256, str)
        or len(sha256) != 64
        or any(character not in "0123456789abcdef" for character in sha256)
        or not isinstance(row_count, int)
        or isinstance(row_count, bool)
        or row_count < 0
        or binding.get("split") != "train"
        or binding.get("canonical_jsonl") is not True
    ):
        raise ValueError("train-only artifact integrity metadata is invalid")

    artifact_path = _resolve_train_only_artifact(manifest_path, files["sft_train"])
    payload = artifact_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != sha256:
        raise ValueError("train-only artifact SHA-256 mismatch")
    rows = _parse_canonical_jsonl(payload)
    if len(rows) != row_count:
        raise ValueError("train-only artifact row count mismatch")

    row_ids = [row.get("id") for row in rows]
    if any(not isinstance(row_id, str) or not row_id.strip() for row_id in row_ids):
        raise ValueError("train-only artifact IDs must be non-empty strings")
    if len(set(row_ids)) != len(row_ids):
        raise ValueError("train-only artifact IDs must be unique")
    if any(row.get("split") != "train" for row in rows):
        raise ValueError("train-only artifact must contain only train rows")
    if public:
        for row in rows:
            validate_public_record(row)

    expected_rows = [row for row in mixed_sft_rows if row.get("split") == "train"]
    if rows != expected_rows:
        raise ValueError("train-only artifact must equal the ordered mixed-SFT train subsequence")
    return len(rows)


def validate_dataset_artifacts(
    sft_path: Path,
    dpo_path: Path,
    manifest_path: Path,
    public: bool,
    raise_on_error: bool = False,
) -> ValidationResult:
    failures: list[dict[str, str]] = []
    sft_count = 0
    sft_rows: list[dict[str, Any]] = []
    sft_train_count = 0
    dpo_count = 0

    for record in read_jsonl(sft_path):
        try:
            row = SFTDatasetRow(**record)
            if public:
                validate_public_record(row.to_dict())
            sft_count += 1
            sft_rows.append(record)
        except Exception as exc:  # noqa: BLE001 - validation reports need category and id.
            failures.append(
                {"id": str(record.get("id", "<unknown>")), "category": type(exc).__name__, "message": str(exc)}
            )

    for record in read_jsonl(dpo_path):
        try:
            pair = DPOPair(**record)
            validate_dpo_pair(pair)
            if public:
                validate_public_record(pair.to_dict())
            dpo_count += 1
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {"id": str(record.get("id", "<unknown>")), "category": type(exc).__name__, "message": str(exc)}
            )

    try:
        manifest = read_json(manifest_path)
        if public:
            validate_public_record(manifest)
        expected_sft = int(manifest.get("counts", {}).get("sft_rows", sft_count))
        expected_dpo = int(manifest.get("counts", {}).get("dpo_pairs", dpo_count))
        if expected_sft != sft_count:
            failures.append({"id": "manifest", "category": "count_mismatch", "message": "sft_rows count mismatch"})
        if expected_dpo != dpo_count:
            failures.append({"id": "manifest", "category": "count_mismatch", "message": "dpo_pairs count mismatch"})
        try:
            sft_train_count = _validate_train_only_artifact(
                manifest=manifest,
                manifest_path=manifest_path,
                mixed_sft_rows=sft_rows,
                public=public,
            )
        except Exception as exc:  # noqa: BLE001 - one stable category for the optional binding contract.
            failures.append(
                {
                    "id": "sft_train",
                    "category": "train_only_artifact_invalid",
                    "message": str(exc),
                }
            )
    except Exception as exc:  # noqa: BLE001
        failures.append({"id": "manifest", "category": type(exc).__name__, "message": str(exc)})

    result = ValidationResult(
        ok=not failures,
        failures=failures,
        counts={"sft_rows": sft_count, "sft_train_rows": sft_train_count, "dpo_pairs": dpo_count},
    )
    if raise_on_error and not result.ok:
        raise ValidationError(f"dataset validation failed: {failures}")
    return result
