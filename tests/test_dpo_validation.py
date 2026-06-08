from pathlib import Path

import pytest

from voice2task.dpo import summarize_dpo_slices, validate_dpo_pair, validate_dpo_pairs_file
from voice2task.io import write_jsonl
from voice2task.schemas import BrowserTaskContract, DPOPair, ValidationError


def _contract(
    task_type: str = "search",
    route: str = "search_web",
    confirmation_required: bool = False,
    query: str = "酒店",
    slots: dict[str, str] | None = None,
    safety_reason: str = "public_readonly",
) -> BrowserTaskContract:
    return BrowserTaskContract(
        task_type=task_type,
        route=route,
        safety={"allow": True, "reason": safety_reason},
        confirmation_required=confirmation_required,
        slots=slots or {"query": query},
        normalized_command=f"搜索{query}",
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


def test_validate_dpo_pair_accepts_decomposed_search_slot_negative() -> None:
    pair = DPOPair(
        id="search-decomposed-slots",
        split="train",
        input_text="查北京明天天气",
        chosen_contract=_contract(query="北京明天天气"),
        rejected_contract=_contract(
            slots={"city": "北京", "date": "明天", "topic": ""},
            safety_reason="decomposed_search_slots",
        ),
        rejection_reason="decomposed_search_slots",
        provenance={"source_id": "seed-search-weather", "public_safe": True},
    )

    validate_dpo_pair(pair)

    summary = summarize_dpo_slices([pair])
    assert summary["slot"]["count"] == 1
    assert summary["aggregate"]["rejection_categories"] == {"decomposed_search_slots": 1}


@pytest.mark.parametrize(
    ("rejected_contract", "message"),
    [
        (
            _contract(slots={"city": "北京", "date": "明天"}, safety_reason="decomposed_search_slots"),
            "replace query with city/date/topic slots",
        ),
        (
            _contract(
                slots={"query": "北京明天天气", "city": "北京", "date": "明天", "topic": ""},
                safety_reason="decomposed_search_slots",
            ),
            "replace query with city/date/topic slots",
        ),
        (
            _contract(
                route="open_url",
                slots={"city": "北京", "date": "明天", "topic": ""},
                safety_reason="decomposed_search_slots",
            ),
            "public-readonly search/search_web contract",
        ),
        (
            _contract(
                task_type="navigate",
                route="search_web",
                slots={"city": "北京", "date": "明天", "topic": ""},
                safety_reason="decomposed_search_slots",
            ),
            "public-readonly search/search_web contract",
        ),
    ],
)
def test_validate_dpo_pair_rejects_malformed_decomposed_search_slot_negative(
    rejected_contract: BrowserTaskContract,
    message: str,
) -> None:
    pair = DPOPair(
        id="bad-search-decomposed-slots",
        split="train",
        input_text="查北京明天天气",
        chosen_contract=_contract(query="北京明天天气"),
        rejected_contract=rejected_contract,
        rejection_reason="decomposed_search_slots",
        provenance={"source_id": "seed-search-weather", "public_safe": True},
    )

    with pytest.raises(ValidationError, match=message):
        validate_dpo_pair(pair)
