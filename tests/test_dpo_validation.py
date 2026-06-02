from pathlib import Path

import pytest

from voice2task.dpo import summarize_dpo_slices, validate_dpo_pairs_file
from voice2task.io import write_jsonl
from voice2task.schemas import BrowserTaskContract, DPOPair, ValidationError


def _contract(route: str = "search_web", confirmation_required: bool = False) -> BrowserTaskContract:
    return BrowserTaskContract(
        task_type="search",
        route=route,
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=confirmation_required,
        slots={"query": "酒店"},
        normalized_command="搜索酒店",
    )


def test_validate_dpo_pairs_file_rejects_weak_pairs(tmp_path: Path) -> None:
    weak = {
        "id": "weak-1",
        "split": "train",
        "input_text": "搜酒店",
        "chosen_contract": _contract().to_dict(),
        "rejected_contract": _contract().to_dict(),
        "rejection_reason": "wrong_route",
        "provenance": {"source_id": "seed-1", "public_safe": True},
    }
    path = tmp_path / "weak.jsonl"
    write_jsonl(path, [weak])

    with pytest.raises(ValidationError, match="weak_pair"):
        validate_dpo_pairs_file(path)


def test_validate_dpo_pairs_file_rejects_mislabeled_wrong_route_pair(tmp_path: Path) -> None:
    mislabeled = {
        "id": "bad-route-label",
        "split": "train",
        "input_text": "搜酒店",
        "chosen_contract": _contract(route="search_web").to_dict(),
        "rejected_contract": _contract(route="search_web", confirmation_required=True).to_dict(),
        "rejection_reason": "wrong_route",
        "provenance": {"source_id": "seed-1", "public_safe": True},
    }
    path = tmp_path / "mislabeled.jsonl"
    write_jsonl(path, [mislabeled])

    with pytest.raises(ValidationError, match="wrong_route"):
        validate_dpo_pairs_file(path)


def test_dpo_slice_summary_counts_rejection_categories() -> None:
    pairs = [
        DPOPair(
            id="route-1",
            split="train",
            input_text="搜酒店",
            chosen_contract=_contract(),
            rejected_contract=_contract(route="open_url"),
            rejection_reason="wrong_route",
            provenance={"source_id": "seed-1", "public_safe": True},
        ),
        DPOPair(
            id="confirm-1",
            split="train",
            input_text="搜酒店",
            chosen_contract=_contract(confirmation_required=True),
            rejected_contract=_contract(confirmation_required=False),
            rejection_reason="missing_confirmation",
            provenance={"source_id": "seed-2", "public_safe": True},
        ),
    ]

    summary = summarize_dpo_slices(pairs)

    assert summary["route"]["count"] == 1
    assert summary["confirmation"]["count"] == 1
    assert summary["aggregate"]["total_pairs"] == 2
