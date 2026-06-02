from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from voice2task.io import read_jsonl
from voice2task.schemas import DPOPair, ValidationError, as_contract

REJECTION_SLICE = {
    "wrong_task_type": "task_type",
    "wrong_route": "route",
    "unsafe_allowance": "safety",
    "missing_confirmation": "confirmation",
    "missing_slot": "slot",
    "wrong_slot": "slot",
    "underspecified_request": "underspecified",
    "malformed_schema": "schema",
}


def validate_dpo_pair(pair: DPOPair) -> None:
    chosen = as_contract(pair.chosen_contract).to_dict()
    rejected = pair.rejected_contract_dict()
    if chosen == rejected:
        raise ValidationError(f"weak_pair: {pair.id} chosen and rejected contracts are identical")
    if pair.rejection_reason == "wrong_route" and chosen.get("route") == rejected.get("route"):
        raise ValidationError(f"wrong_route: {pair.id} rejected contract must change route")
    if pair.rejection_reason == "unsafe_allowance" and chosen.get("safety", {}).get("allow") == rejected.get(
        "safety", {}
    ).get("allow"):
        raise ValidationError(f"unsafe_allowance: {pair.id} rejected contract must change safety.allow")
    if pair.rejection_reason == "missing_confirmation":
        if chosen.get("confirmation_required") is not True or rejected.get("confirmation_required") is not False:
            raise ValidationError(
                f"missing_confirmation: {pair.id} chosen must require confirmation and rejected must omit it"
            )
    if pair.rejection_reason == "missing_slot" and len(rejected.get("slots", {})) >= len(chosen.get("slots", {})):
        raise ValidationError(f"missing_slot: {pair.id} rejected contract must remove a slot")
    if pair.rejection_reason == "wrong_slot" and chosen.get("slots") == rejected.get("slots"):
        raise ValidationError(f"wrong_slot: {pair.id} rejected contract must alter slots")
    if pair.rejection_reason == "underspecified_request" and rejected.get("route") != "clarify":
        raise ValidationError(f"underspecified_request: {pair.id} rejected contract must route to clarify")
    if pair.rejection_reason == "malformed_schema" and "route" in rejected:
        raise ValidationError(f"malformed_schema: {pair.id} rejected contract must violate required schema")


def validate_dpo_pairs_file(path: Path) -> list[DPOPair]:
    pairs: list[DPOPair] = []
    for record in read_jsonl(path):
        pair = DPOPair(**record)
        validate_dpo_pair(pair)
        pairs.append(pair)
    return pairs


def summarize_dpo_slices(pairs: list[DPOPair]) -> dict[str, Any]:
    category_counts = Counter(pair.rejection_reason for pair in pairs)
    slice_counts: Counter[str] = Counter(REJECTION_SLICE[pair.rejection_reason] for pair in pairs)
    summary: dict[str, Any] = {
        "aggregate": {
            "total_pairs": len(pairs),
            "rejection_categories": dict(sorted(category_counts.items())),
        }
    }
    for slice_name in ("task_type", "route", "safety", "confirmation", "slot", "schema", "underspecified"):
        examples = [pair.id for pair in pairs if REJECTION_SLICE[pair.rejection_reason] == slice_name][:5]
        summary[slice_name] = {"count": slice_counts.get(slice_name, 0), "examples": examples}
    return summary
