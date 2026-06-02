from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from voice2task.dpo import validate_dpo_pair
from voice2task.io import read_json, read_jsonl
from voice2task.schemas import DPOPair, SFTDatasetRow, ValidationError, validate_public_record


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    failures: list[dict[str, str]]
    counts: dict[str, int]


def validate_dataset_artifacts(
    sft_path: Path,
    dpo_path: Path,
    manifest_path: Path,
    public: bool,
    raise_on_error: bool = False,
) -> ValidationResult:
    failures: list[dict[str, str]] = []
    sft_count = 0
    dpo_count = 0

    for record in read_jsonl(sft_path):
        try:
            row = SFTDatasetRow(**record)
            if public:
                validate_public_record(row.to_dict())
            sft_count += 1
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
    except Exception as exc:  # noqa: BLE001
        failures.append({"id": "manifest", "category": type(exc).__name__, "message": str(exc)})

    result = ValidationResult(
        ok=not failures,
        failures=failures,
        counts={"sft_rows": sft_count, "dpo_pairs": dpo_count},
    )
    if raise_on_error and not result.ok:
        raise ValidationError(f"dataset validation failed: {failures}")
    return result
