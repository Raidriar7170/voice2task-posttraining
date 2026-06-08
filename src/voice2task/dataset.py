from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from voice2task.io import read_jsonl, write_json, write_jsonl
from voice2task.schemas import (
    BrowserTaskContract,
    DatasetManifest,
    DPOPair,
    SFTDatasetRow,
    as_contract,
    validate_public_record,
)

HARD_NEGATIVE_CATEGORIES = [
    "wrong_route",
    "unsafe_allowance",
    "missing_confirmation",
    "missing_slot",
    "wrong_slot",
    "decomposed_search_slots",
    "underspecified_request",
    "malformed_schema",
]


def _now_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}"


def _read_seed_rows(seed_path: Path) -> list[dict[str, Any]]:
    raw_rows = read_jsonl(seed_path)
    for row in raw_rows:
        as_contract(row["target_contract"])
    return raw_rows


def _compact_query_phrase(value: str) -> str:
    return "".join(value.split())


def _canonical_public_search_target(contract: BrowserTaskContract | dict[str, Any]) -> BrowserTaskContract:
    target = as_contract(contract)
    if not (
        target.task_type == "search"
        and target.route == "search_web"
        and bool(target.safety.get("allow")) is True
        and target.safety.get("reason") == "public_readonly"
        and target.confirmation_required is False
    ):
        return target

    normalized_suffix = ""
    if target.normalized_command.startswith("搜索"):
        normalized_suffix = _compact_query_phrase(target.normalized_command.removeprefix("搜索"))
    query_value = target.slots.get("query")
    if normalized_suffix:
        compact_query = normalized_suffix
    elif isinstance(query_value, str):
        compact_query = _compact_query_phrase(query_value)
    else:
        compact_query = ""
    if not compact_query:
        return target

    return _replace_contract(
        target,
        slots={"query": compact_query},
        normalized_command=f"搜索{compact_query}",
    )


def _base_row(seed: dict[str, Any], public_safe: bool) -> SFTDatasetRow:
    target_contract = seed["target_contract"]
    if public_safe:
        target_contract = _canonical_public_search_target(target_contract)
    provenance = {
        "source_id": seed["id"],
        "source_mode": "sanitized_seed",
        "public_safe": public_safe,
        "augmentation": "original",
    }
    return SFTDatasetRow(
        id=seed["id"],
        split=seed["split"],
        input_text=seed["input_text"],
        target_contract=target_contract,
        provenance=provenance,
    )


def expand_sft_rows(seed_rows: list[dict[str, Any]], public_safe: bool) -> list[SFTDatasetRow]:
    rows: list[SFTDatasetRow] = []
    for seed in seed_rows:
        base = _base_row(seed, public_safe=public_safe)
        rows.append(base)
        for index, paraphrase in enumerate(seed.get("augmentations", []), start=1):
            rows.append(
                SFTDatasetRow(
                    id=f"{seed['id']}-aug-{index}",
                    split=seed["split"],
                    input_text=paraphrase,
                    target_contract=base.target_contract,
                    provenance={
                        "source_id": seed["id"],
                        "source_mode": "schema_preserving_augmentation",
                        "public_safe": public_safe,
                        "augmentation": f"paraphrase-{index}",
                    },
                )
            )
    return rows


def _replace_contract(contract: BrowserTaskContract, **updates: Any) -> BrowserTaskContract:
    data = contract.to_dict()
    data.update(updates)
    return BrowserTaskContract.from_dict(data)


def _decomposed_weather_slots(query: str) -> dict[str, str] | None:
    compact = _compact_query_phrase(query)
    if not compact.endswith("天气"):
        return None
    stem = compact.removesuffix("天气")
    for date in ("今天", "明天", "后天"):
        if stem.endswith(date):
            city = stem[: -len(date)]
            if city:
                return {"city": city, "date": date, "topic": ""}
    return None


def _decomposed_search_slots_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    if not (
        contract.task_type == "search"
        and contract.route == "search_web"
        and bool(contract.safety.get("allow")) is True
        and contract.safety.get("reason") == "public_readonly"
        and contract.confirmation_required is False
    ):
        return None
    query = contract.slots.get("query")
    if not isinstance(query, str):
        return None
    decomposed_slots = _decomposed_weather_slots(query)
    if decomposed_slots is None:
        return None
    return _replace_contract(
        contract,
        slots=decomposed_slots,
        safety={**contract.safety, "reason": "decomposed_search_slots"},
    )


def _negative_contract(contract: BrowserTaskContract, category: str) -> BrowserTaskContract | dict[str, Any]:
    if category == "wrong_route":
        route = "open_url" if contract.route != "open_url" else "search_web"
        return _replace_contract(contract, route=route, safety={**contract.safety, "reason": "wrong_route"})
    if category == "unsafe_allowance":
        safety = {"allow": not bool(contract.safety["allow"]), "reason": "unsafe_allowance"}
        return _replace_contract(contract, safety=safety)
    if category == "missing_confirmation":
        return _replace_contract(
            contract,
            confirmation_required=False,
            safety={**contract.safety, "reason": "missing_confirmation"},
        )
    if category == "missing_slot":
        slots = dict(contract.slots)
        if slots:
            slots.pop(next(iter(slots)))
        return _replace_contract(contract, slots=slots, safety={**contract.safety, "reason": "missing_slot"})
    if category == "wrong_slot":
        slots = dict(contract.slots)
        if slots:
            first_key = next(iter(slots))
            slots[first_key] = f"{slots[first_key]}_wrong"
        else:
            slots["missing"] = "wrong"
        return _replace_contract(contract, slots=slots, safety={**contract.safety, "reason": "wrong_slot"})
    if category == "decomposed_search_slots":
        decomposed = _decomposed_search_slots_negative(contract)
        if decomposed is None:
            raise ValueError("decomposed_search_slots applies only to compact public-readonly weather search")
        return decomposed
    if category == "underspecified_request":
        return _replace_contract(
            contract,
            route="clarify",
            confirmation_required=True,
            slots={},
            safety={**contract.safety, "reason": "underspecified_request"},
        )
    if category == "malformed_schema":
        malformed = contract.to_dict()
        malformed.pop("route", None)
        malformed["malformed_reason"] = "route_removed"
        return malformed
    raise ValueError(f"unknown hard-negative category: {category}")


def generate_hard_negative_pairs(rows: list[SFTDatasetRow]) -> list[DPOPair]:
    pairs: list[DPOPair] = []
    for row in rows:
        if row.provenance.get("augmentation") != "original":
            continue
        chosen = as_contract(row.target_contract)
        for category in HARD_NEGATIVE_CATEGORIES:
            if category == "missing_confirmation" and not chosen.confirmation_required:
                continue
            if category == "decomposed_search_slots":
                if row.provenance.get("public_safe") is not True or _decomposed_search_slots_negative(chosen) is None:
                    continue
            pairs.append(
                DPOPair(
                    id=f"{row.id}-{category}",
                    split=row.split,
                    input_text=row.input_text,
                    chosen_contract=chosen,
                    rejected_contract=_negative_contract(chosen, category),
                    rejection_reason=category,
                    provenance={
                        "source_id": row.provenance.get("source_id", row.id),
                        "source_mode": "hard_negative",
                        "public_safe": row.provenance.get("public_safe", False),
                    },
                )
            )
    return pairs


def _split_counts(rows: list[SFTDatasetRow]) -> dict[str, int]:
    counts = Counter(row.split for row in rows)
    return {split: counts.get(split, 0) for split in ("train", "dev", "test")}


def _rejection_counts(pairs: list[DPOPair]) -> dict[str, int]:
    counts = Counter(pair.rejection_reason for pair in pairs)
    return {category: counts.get(category, 0) for category in HARD_NEGATIVE_CATEGORIES}


def _write_manifest(path: Path, manifest: DatasetManifest) -> None:
    write_json(path, manifest.to_dict())


def build_public_sample_dataset(seed_path: Path, output_dir: Path) -> DatasetManifest:
    seed_rows = _read_seed_rows(seed_path)
    rows = expand_sft_rows(seed_rows, public_safe=True)
    pairs = generate_hard_negative_pairs(rows)
    for row in rows:
        validate_public_record(row.to_dict())
    for pair in pairs:
        validate_public_record(pair.to_dict())

    sft_path = output_dir / "sft_public_sample.jsonl"
    dpo_path = output_dir / "dpo_public_sample.jsonl"
    manifest_path = output_dir / "manifest_public_sample.json"
    write_jsonl(sft_path, [row.to_dict() for row in rows])
    write_jsonl(dpo_path, [pair.to_dict() for pair in pairs])

    manifest = DatasetManifest(
        manifest_id=_now_id("public-sample"),
        mode="public_sample",
        generated_at=datetime.now(timezone.utc).isoformat(),
        files={
            "seed": seed_path.as_posix(),
            "sft": sft_path.as_posix(),
            "dpo": dpo_path.as_posix(),
            "manifest": manifest_path.as_posix(),
        },
        counts={"seed_rows": len(seed_rows), "sft_rows": len(rows), "dpo_pairs": len(pairs)},
        split_counts=_split_counts(rows),
        dpo_rejection_counts=_rejection_counts(pairs),
        source_summary={"seed_rows": len(seed_rows), "source": "sanitized_public_seed_fixture"},
        public_safe=True,
    )
    _write_manifest(manifest_path, manifest)
    return manifest


def build_local_private_corpus(seed_trace_path: Path, output_dir: Path) -> DatasetManifest:
    seed_rows = _read_seed_rows(seed_trace_path)
    rows = expand_sft_rows(seed_rows, public_safe=False)
    pairs = generate_hard_negative_pairs(rows)

    split_files: dict[str, str] = {}
    for split in ("train", "dev", "test"):
        path = output_dir / f"{split}.jsonl"
        write_jsonl(path, [row.to_dict() for row in rows if row.split == split])
        split_files[split] = path.as_posix()
    dpo_path = output_dir / "dpo_pairs.jsonl"
    manifest_path = output_dir / "manifest_local_private.json"
    write_jsonl(dpo_path, [pair.to_dict() for pair in pairs])

    manifest = DatasetManifest(
        manifest_id=_now_id("local-private"),
        mode="local_private",
        generated_at=datetime.now(timezone.utc).isoformat(),
        files={**split_files, "dpo": dpo_path.as_posix(), "manifest": manifest_path.as_posix()},
        counts={"seed_rows": len(seed_rows), "sft_rows": len(rows), "dpo_pairs": len(pairs)},
        split_counts=_split_counts(rows),
        dpo_rejection_counts=_rejection_counts(pairs),
        source_summary={
            "seed_rows": len(seed_rows),
            "source": "configured_voice_to_browser_agent_seed_trace_path",
            "raw_rows_committed": 0,
        },
        public_safe=False,
    )
    _write_manifest(manifest_path, manifest)
    return manifest
