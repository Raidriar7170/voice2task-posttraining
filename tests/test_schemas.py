import pytest

from voice2task.schemas import (
    BrowserTaskContract,
    DPOPair,
    SFTDatasetRow,
    ValidationError,
    canonical_contract_json,
    validate_public_text,
)


def test_browser_task_contract_canonical_json_is_stable() -> None:
    contract = BrowserTaskContract(
        task_type="search",
        route="search_web",
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"query": "天气 北京"},
        normalized_command="搜索北京天气",
    )

    expected = (
        '{"confirmation_required":false,"contract_version":"v1","language":"zh-CN",'
        '"normalized_command":"搜索北京天气","route":"search_web",'
        '"safety":{"allow":true,"reason":"public_readonly"},'
        '"slots":{"query":"天气 北京"},"task_type":"search"}'
    )
    assert canonical_contract_json(contract) == expected


def test_browser_task_contract_from_dict_rejects_missing_required_fields() -> None:
    incomplete = {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "normalized_command": "搜索北京天气",
    }

    with pytest.raises(ValidationError, match="missing required fields"):
        BrowserTaskContract.from_dict(incomplete)


def test_dataset_row_rejects_invalid_split() -> None:
    contract = BrowserTaskContract(
        task_type="navigate",
        route="open_url",
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"url": "https://example.com"},
        normalized_command="打开示例网站",
    )

    with pytest.raises(ValidationError, match="split"):
        SFTDatasetRow(
            id="bad-split",
            split="holdout",
            input_text="打开示例网站",
            target_contract=contract,
            provenance={"source_id": "seed-1", "public_safe": True},
        )


def test_dpo_pair_requires_same_input_and_rejection_reason() -> None:
    chosen = BrowserTaskContract(
        task_type="form_fill",
        route="fill_form",
        safety={"allow": True, "reason": "requires_confirmation"},
        confirmation_required=True,
        slots={"field": "邮箱"},
        normalized_command="填写邮箱",
    )
    rejected = BrowserTaskContract(
        task_type="form_fill",
        route="fill_form",
        safety={"allow": True, "reason": "missing_confirmation"},
        confirmation_required=False,
        slots={"field": "邮箱"},
        normalized_command="填写邮箱",
    )

    with pytest.raises(ValidationError, match="same input"):
        DPOPair(
            id="pair-1",
            split="train",
            input_text="把邮箱填进去",
            rejected_input_text="另一个输入",
            chosen_contract=chosen,
            rejected_contract=rejected,
            rejection_reason="missing_confirmation",
            provenance={"source_id": "seed-1", "public_safe": True},
        )

    with pytest.raises(ValidationError, match="rejection_reason"):
        DPOPair(
            id="pair-2",
            split="train",
            input_text="把邮箱填进去",
            chosen_contract=chosen,
            rejected_contract=rejected,
            rejection_reason="",
            provenance={"source_id": "seed-1", "public_safe": True},
        )


def test_public_policy_rejects_private_paths_and_tokens() -> None:
    private_path = "/" + "Users" + "/example/private.jsonl"
    with pytest.raises(ValidationError, match="private_path"):
        validate_public_text(f"see {private_path}")

    secret = "OPENAI_API_KEY=" + "sk-live-secret"
    with pytest.raises(ValidationError, match="secret"):
        validate_public_text(secret)
