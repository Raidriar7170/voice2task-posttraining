from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from voice2task.io import read_json, read_jsonl, write_json

METHODOLOGY_VERSION = "voice2task.split_integrity.v1"
_DIGIT_RUN_RE = re.compile(r"\d+")
_WHITESPACE_RE = re.compile(r"\s+")
_VALID_SPLITS = {"dev", "test", "train"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


def _source_record(path: Path, repo_root: Path) -> dict[str, str | None]:
    return {
        "path": _source_path(path, repo_root),
        "sha256": _sha256(path) if path.is_file() else None,
    }


def _validation_error(
    errors: list[dict[str, str]],
    *,
    source: str,
    category: str,
    row_id: str,
    message: str,
) -> None:
    errors.append(
        {
            "source": source,
            "category": category,
            "row_id": row_id,
            "message": message,
        }
    )


def _read_jsonl_for_audit(
    path: Path,
    source: str,
    errors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    try:
        return read_jsonl(path)
    except Exception as exc:  # noqa: BLE001 - invalid input must still produce a report.
        _validation_error(
            errors,
            source=source,
            category="unreadable_jsonl",
            row_id="<file>",
            message=str(exc),
        )
        return []


def _read_manifest_for_audit(
    path: Path,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    try:
        return read_json(path)
    except Exception as exc:  # noqa: BLE001 - invalid input must still produce a report.
        _validation_error(
            errors,
            source="manifest",
            category="unreadable_json",
            row_id="<file>",
            message=str(exc),
        )
        return {}


def _validate_rows(
    source: str,
    rows: list[dict[str, Any]],
    *,
    required_fields: tuple[str, ...],
    object_fields: tuple[str, ...],
    list_fields: tuple[str, ...] = (),
    errors: list[dict[str, str]],
) -> None:
    if not rows:
        _validation_error(
            errors,
            source=source,
            category="empty_input",
            row_id="<file>",
            message=f"{source} must contain at least one row",
        )
        return

    seen_ids: set[str] = set()
    observed_splits: set[str] = set()
    for index, row in enumerate(rows, start=1):
        row_label = str(row.get("id", f"<row-{index}>"))
        missing = [field for field in required_fields if field not in row]
        if missing:
            _validation_error(
                errors,
                source=source,
                category="missing_required_fields",
                row_id=row_label,
                message=f"missing required fields: {', '.join(missing)}",
            )
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            _validation_error(
                errors,
                source=source,
                category="invalid_id",
                row_id=row_label,
                message="id must be a non-empty string",
            )
        elif row_id in seen_ids:
            _validation_error(
                errors,
                source=source,
                category="duplicate_id",
                row_id=row_id,
                message=f"duplicate id in {source}",
            )
        else:
            seen_ids.add(row_id)

        split = row.get("split")
        if split not in _VALID_SPLITS:
            _validation_error(
                errors,
                source=source,
                category="invalid_split",
                row_id=row_label,
                message=f"split must be one of {sorted(_VALID_SPLITS)}, got {split!r}",
            )
        else:
            observed_splits.add(str(split))
        if not isinstance(row.get("input_text"), str) or not str(row.get("input_text", "")).strip():
            _validation_error(
                errors,
                source=source,
                category="invalid_input_text",
                row_id=row_label,
                message="input_text must be a non-empty string",
            )
        for field in object_fields:
            if not isinstance(row.get(field), dict):
                _validation_error(
                    errors,
                    source=source,
                    category="invalid_object_field",
                    row_id=row_label,
                    message=f"{field} must be an object",
                )
        for field in list_fields:
            if not isinstance(row.get(field), list):
                _validation_error(
                    errors,
                    source=source,
                    category="invalid_list_field",
                    row_id=row_label,
                    message=f"{field} must be an array",
                )

    for split in sorted(_VALID_SPLITS - observed_splits):
        _validation_error(
            errors,
            source=source,
            category="missing_split",
            row_id="<file>",
            message=f"missing required split: {split}",
        )


def _validate_manifest_binding(
    manifest: dict[str, Any],
    *,
    seed_rows: list[dict[str, Any]],
    sft_rows: list[dict[str, Any]],
    dpo_rows: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    for field in ("files", "counts", "split_counts"):
        if not isinstance(manifest.get(field), dict):
            _validation_error(
                errors,
                source="manifest",
                category="invalid_object_field",
                row_id="manifest",
                message=f"{field} must be an object",
            )
    if not isinstance(manifest.get("manifest_id"), str) or not manifest.get("manifest_id"):
        _validation_error(
            errors,
            source="manifest",
            category="invalid_manifest_id",
            row_id="manifest",
            message="manifest_id must be a non-empty string",
        )
    counts = manifest.get("counts")
    split_counts = manifest.get("split_counts")
    if isinstance(counts, dict):
        expected_counts = {
            "seed_rows": len(seed_rows),
            "sft_rows": len(sft_rows),
            "dpo_pairs": len(dpo_rows),
        }
        for name, expected in expected_counts.items():
            if counts.get(name) != expected:
                _validation_error(
                    errors,
                    source="manifest",
                    category="count_mismatch",
                    row_id="manifest",
                    message=f"{name} expected {expected}, got {counts.get(name)!r}",
                )
    if isinstance(split_counts, dict):
        for split in sorted(_VALID_SPLITS):
            expected = sum(row.get("split") == split for row in sft_rows)
            if split_counts.get(split) != expected:
                _validation_error(
                    errors,
                    source="manifest",
                    category="split_count_mismatch",
                    row_id="manifest",
                    message=f"{split} expected {expected}, got {split_counts.get(split)!r}",
                )


def _usable_rows(rows: list[dict[str, Any]], *, contract_field: str) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if isinstance(row.get("id"), str)
        and row.get("split") in _VALID_SPLITS
        and isinstance(row.get("input_text"), str)
        and isinstance(row.get(contract_field), dict)
    ]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digit_template(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip()
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return _DIGIT_RUN_RE.sub("<NUM>", normalized)


def _structural_contract(contract: dict[str, Any]) -> dict[str, Any]:
    safety = contract.get("safety")
    slots = contract.get("slots")
    return {
        "task_type": contract.get("task_type"),
        "route": contract.get("route"),
        "safety": safety if isinstance(safety, dict) else None,
        "confirmation_required": contract.get("confirmation_required"),
        "slot_keys": sorted(slots) if isinstance(slots, dict) else [],
        "language": contract.get("language"),
        "contract_version": contract.get("contract_version"),
    }


def _overlap_diagnostic(
    train_rows: list[dict[str, Any]],
    heldout_rows: list[dict[str, Any]],
    signature: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    train_ids_by_signature: dict[str, list[str]] = defaultdict(list)
    for row in train_rows:
        train_ids_by_signature[signature(row)].append(str(row["id"]))

    findings: list[dict[str, Any]] = []
    for row in heldout_rows:
        train_ids = train_ids_by_signature.get(signature(row), [])
        if train_ids:
            findings.append(
                {
                    "heldout_row_id": str(row["id"]),
                    "heldout_split": str(row["split"]),
                    "train_match_count": len(train_ids),
                    "train_row_ids": sorted(train_ids)[:10],
                }
            )
    findings.sort(key=lambda item: (item["heldout_split"], item["heldout_row_id"]))
    return {"heldout_row_count": len(findings), "examples": findings[:10]}


def _digit_template_diagnostic(seed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows_by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in seed_rows:
        rows_by_signature[_digit_template(str(row["input_text"]))].append(row)

    cross_split: list[tuple[str, list[dict[str, Any]]]] = []
    for signature, rows in rows_by_signature.items():
        if len({str(row["split"]) for row in rows}) > 1:
            cross_split.append((signature, rows))
    cross_split.sort(key=lambda item: item[0])
    examples = [
        {
            "signature": signature,
            "splits": sorted({str(row["split"]) for row in rows}),
            "row_ids": sorted(str(row["id"]) for row in rows),
        }
        for signature, rows in cross_split[:10]
    ]
    return {
        "affected_seed_rows": sum(len(rows) for _, rows in cross_split),
        "cross_split_signature_count": len(cross_split),
        "examples": examples,
    }


def _declared_heldout_splits(provenance: dict[str, Any]) -> set[str]:
    source_splits = provenance.get("source_splits")
    if isinstance(source_splits, dict):
        return {str(split) for split in source_splits if split in {"dev", "test"}}
    if isinstance(source_splits, list):
        return {str(split) for split in source_splits if split in {"dev", "test"}}
    return set()


def _provenance_diagnostic(
    seed_rows: list[dict[str, Any]], sft_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    source_split_by_id = {
        str(row["id"]): str(row["split"])
        for row in [*seed_rows, *sft_rows]
        if "id" in row and "split" in row
    }
    findings: list[dict[str, Any]] = []
    for row in sft_rows:
        if row.get("split") != "train":
            continue
        provenance = row.get("provenance")
        if not isinstance(provenance, dict):
            continue
        reasons: list[str] = []
        declared = _declared_heldout_splits(provenance)
        reasons.extend(f"source_splits:{split}" for split in sorted(declared))

        source_row_ids = provenance.get("source_row_ids", [])
        if isinstance(source_row_ids, list):
            for source_id in sorted(str(value) for value in source_row_ids):
                source_split = source_split_by_id.get(source_id)
                if source_split in {"dev", "test"}:
                    reasons.append(f"source_row_ids:{source_id}:{source_split}")

        for key in ("source_family_id", "source_id"):
            candidate_source_id = provenance.get(key)
            if isinstance(candidate_source_id, str):
                source_split = source_split_by_id.get(candidate_source_id)
                if source_split in {"dev", "test"}:
                    reasons.append(f"{key}:{candidate_source_id}:{source_split}")

        if reasons:
            findings.append({"train_row_id": str(row["id"]), "reasons": sorted(set(reasons))})
    findings.sort(key=lambda item: item["train_row_id"])
    return {"train_row_count": len(findings), "examples": findings[:20]}


def audit_split_integrity(
    *,
    seed_path: Path,
    sft_path: Path,
    dpo_path: Path,
    manifest_path: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    validation_errors: list[dict[str, str]] = []
    raw_seed_rows = _read_jsonl_for_audit(seed_path, "seed", validation_errors)
    raw_sft_rows = _read_jsonl_for_audit(sft_path, "sft", validation_errors)
    raw_dpo_rows = _read_jsonl_for_audit(dpo_path, "dpo", validation_errors)
    manifest = _read_manifest_for_audit(manifest_path, validation_errors)
    _validate_rows(
        "seed",
        raw_seed_rows,
        required_fields=("id", "split", "input_text", "target_contract", "augmentations"),
        object_fields=("target_contract",),
        list_fields=("augmentations",),
        errors=validation_errors,
    )
    _validate_rows(
        "sft",
        raw_sft_rows,
        required_fields=("id", "split", "input_text", "target_contract", "provenance"),
        object_fields=("target_contract", "provenance"),
        errors=validation_errors,
    )
    _validate_rows(
        "dpo",
        raw_dpo_rows,
        required_fields=(
            "id",
            "split",
            "input_text",
            "chosen_contract",
            "rejected_contract",
            "rejection_reason",
            "provenance",
        ),
        object_fields=("chosen_contract", "rejected_contract", "provenance"),
        errors=validation_errors,
    )
    _validate_manifest_binding(
        manifest,
        seed_rows=raw_seed_rows,
        sft_rows=raw_sft_rows,
        dpo_rows=raw_dpo_rows,
        errors=validation_errors,
    )
    validation_errors.sort(
        key=lambda error: (
            error["source"],
            error["category"],
            error["row_id"],
            error["message"],
        )
    )
    input_valid = not validation_errors
    seed_rows = _usable_rows(raw_seed_rows, contract_field="target_contract")
    sft_rows = _usable_rows(raw_sft_rows, contract_field="target_contract")
    split_counts = {
        split: sum(row.get("split") == split for row in raw_sft_rows)
        for split in ("dev", "test", "train")
    }
    train_rows = [row for row in sft_rows if row.get("split") == "train"]
    heldout_rows = [row for row in sft_rows if row.get("split") in {"dev", "test"}]

    def target_signature(row: dict[str, Any]) -> str:
        return _canonical_json(row.get("target_contract"))

    diagnostics = {
        "digit_normalized_seed_templates": _digit_template_diagnostic(seed_rows),
        "exact_input": _overlap_diagnostic(
            train_rows, heldout_rows, lambda row: str(row.get("input_text", ""))
        ),
        "full_target_contract": _overlap_diagnostic(train_rows, heldout_rows, target_signature),
        "normalized_command": _overlap_diagnostic(
            train_rows,
            heldout_rows,
            lambda row: str(row.get("target_contract", {}).get("normalized_command", "")),
        ),
        "slots": _overlap_diagnostic(
            train_rows,
            heldout_rows,
            lambda row: _canonical_json(row.get("target_contract", {}).get("slots")),
        ),
        "structural_contract": _overlap_diagnostic(
            train_rows,
            heldout_rows,
            lambda row: _canonical_json(_structural_contract(row.get("target_contract", {}))),
        ),
        "train_provenance_to_dev_test": _provenance_diagnostic(seed_rows, sft_rows),
    }
    violations = {
        "cross_split_digit_template_signatures": diagnostics["digit_normalized_seed_templates"][
            "cross_split_signature_count"
        ],
        "heldout_exact_input_rows_overlapping_train": diagnostics["exact_input"][
            "heldout_row_count"
        ],
        "train_rows_with_dev_test_provenance": diagnostics["train_provenance_to_dev_test"][
            "train_row_count"
        ],
    }
    gate_passed = input_valid and all(count == 0 for count in violations.values())
    return {
        "methodology_version": METHODOLOGY_VERSION,
        "methodology": {
            "digit_template": (
                "Unicode NFKC, trim/collapse whitespace, replace each Unicode decimal digit run "
                "with <NUM>"
            ),
            "overlap_boundary": "train versus the union of dev and test; counts are affected held-out rows",
            "structural_contract": (
                "task_type, route, safety, confirmation_required, sorted slot keys, language, "
                "and contract_version"
            ),
            "provenance_resolution": (
                "source_splits plus source_row_ids/source_family_id/source_id resolved against "
                "seed and SFT row IDs"
            ),
        },
        "sources": {
            "seed": _source_record(seed_path, root),
            "sft": _source_record(sft_path, root),
            "dpo": _source_record(dpo_path, root),
            "manifest": _source_record(manifest_path, root),
        },
        "input_counts": {
            "seed_rows": len(raw_seed_rows),
            "sft_rows": len(raw_sft_rows),
            "dpo_pairs": len(raw_dpo_rows),
            "sft_split_counts": split_counts,
        },
        "input_validation": {"valid": input_valid, "errors": validation_errors},
        "clean_gate": {
            "passed": gate_passed,
            "input_validation_passed": input_valid,
            "violation_counts": violations,
            "diagnostic_only_checks": [
                "full_target_contract",
                "normalized_command",
                "slots",
                "structural_contract",
            ],
        },
        "diagnostics": diagnostics,
        "evidence_status": (
            "INVALID_INPUT"
            if not input_valid
            else "CLEAN_GATE_PASSED_CANDIDATE"
            if gate_passed
            else "DEVELOPMENT_ONLY_SPENT"
        ),
        "historical_rows_mutated": False,
        "historical_metrics_rescored": False,
        "claims": {
            "independent_blind_generalization_claim": False,
            "leakage_free_claim": False,
            "model_quality_claim": False,
            "natural_asr_provenance_claim": False,
        },
        "limitations": [
            "Lexical and digit-template checks do not establish semantic independence.",
            "Provenance checks are bounded to declared source fields and resolvable committed IDs.",
            "This audit does not establish natural-ASR provenance or model quality.",
            (
                "Repeated target, normalized-command, slot, or structural labels are diagnostic-only "
                "because ontology reuse can be legitimate."
            ),
        ],
    }


def render_split_integrity_markdown(audit: dict[str, Any]) -> str:
    counts = audit["input_counts"]
    violations = audit["clean_gate"]["violation_counts"]
    diagnostics = audit["diagnostics"]
    lines = [
        "# Public Split Integrity Audit",
        "",
        f"- Methodology: `{audit['methodology_version']}`",
        f"- Evidence status: `{audit['evidence_status']}`",
        f"- Input validation passed: `{str(audit['input_validation']['valid']).lower()}`",
        f"- Input validation errors: {len(audit['input_validation']['errors'])}",
        f"- Clean gate passed: `{str(audit['clean_gate']['passed']).lower()}`",
        f"- Inputs: {counts['seed_rows']} seed rows; {counts['sft_rows']} SFT rows; "
        f"{counts['dpo_pairs']} DPO pairs; "
        f"train/dev/test = {counts['sft_split_counts']['train']}/"
        f"{counts['sft_split_counts']['dev']}/{counts['sft_split_counts']['test']}",
        "- Historical rows mutated: `false`",
        "- Historical metrics rescored: `false`",
        "",
        "## Strict-zero gate",
        "",
        "| check | count |",
        "| --- | ---: |",
    ]
    for name, count in sorted(violations.items()):
        lines.append(f"| `{name}` | {count} |")
    lines.extend(
        [
            "",
            "## Overlap inventory",
            "",
            "| check | held-out rows | role |",
            "| --- | ---: | --- |",
        ]
    )
    for name in ("exact_input", "full_target_contract", "normalized_command", "slots", "structural_contract"):
        role = "strict-zero gate" if name == "exact_input" else "diagnostic-only"
        lines.append(f"| `{name}` | {diagnostics[name]['heldout_row_count']} | {role} |")
    template = diagnostics["digit_normalized_seed_templates"]
    provenance = diagnostics["train_provenance_to_dev_test"]
    lines.extend(
        [
            "",
            f"Digit-normalized seed templates: {template['cross_split_signature_count']} cross-split signatures "
            f"covering {template['affected_seed_rows']} seed rows.",
            f"Train provenance: {provenance['train_row_count']} rows resolve to dev/test sources.",
            "",
            "## Interpretation boundary",
            "",
            "The current public dev/test boundary is development-only/spent, not blind, independent, "
            "or leakage-free evidence. Historical data and metrics remain preserved and were not recomputed.",
            "Lexical/template/provenance checks do not establish semantic independence, natural-ASR provenance, "
            "or model quality. Repeated target and ontology signatures remain diagnostic-only.",
            "",
            "## Sources",
            "",
            f"- `{audit['sources']['seed']['path']}` — `{audit['sources']['seed']['sha256']}`",
            f"- `{audit['sources']['sft']['path']}` — `{audit['sources']['sft']['sha256']}`",
            f"- `{audit['sources']['dpo']['path']}` — `{audit['sources']['dpo']['sha256']}`",
            f"- `{audit['sources']['manifest']['path']}` — `{audit['sources']['manifest']['sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_split_integrity_report(audit: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    json_path = output_dir / "summary.json"
    markdown_path = output_dir / "summary.md"
    write_json(json_path, audit)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_split_integrity_markdown(audit), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}
