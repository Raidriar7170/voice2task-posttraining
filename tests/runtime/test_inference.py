from __future__ import annotations

import json

import pytest

from voice2task.formatting import PREDICTION_SYSTEM_PROMPT
from voice2task.runtime.inference import (
    FixtureVoice2TaskProvider,
    LocalPeftVoice2TaskProvider,
    ProviderError,
    parse_strict_contract_json,
)

DEMO_CASES = [
    ("帮我搜索北京明天的天气", "search", "search_web"),
    ("打开帮助中心", "navigate", "open_url"),
    ("帮我提取这个页面上的商品价格", "extract", "extract_page"),
    ("把邮箱填进表单里，提交前先问我", "form_fill", "fill_form"),
    ("帮我打开那个页面", "clarify", "clarify"),
    ("替我完成付款", "blocked", "deny"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("utterance", "task_type", "route"), DEMO_CASES)
async def test_fixture_provider_matches_only_the_six_exact_utterances(
    utterance: str, task_type: str, route: str
) -> None:
    result = await FixtureVoice2TaskProvider().infer(utterance)

    assert result.inference_mode == "fixture"
    assert result.contract.task_type == task_type
    assert result.contract.route == route
    assert result.schema_valid is True
    assert result.semantic_valid is True


@pytest.mark.asyncio
async def test_fixture_provider_rejects_unknown_or_whitespace_modified_input() -> None:
    provider = FixtureVoice2TaskProvider()

    for value in ("搜索天气", " 帮我搜索北京明天的天气", "帮我搜索北京明天的天气 "):
        with pytest.raises(ProviderError, match="FIXTURE_INPUT_UNSUPPORTED") as exc_info:
            await provider.infer(value)
        assert exc_info.value.code == "FIXTURE_INPUT_UNSUPPORTED"


def test_strict_parser_rejects_wrapped_json_fragment() -> None:
    payload = {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": "北京明天天气"},
        "normalized_command": "搜索北京明天天气",
        "language": "zh-CN",
        "contract_version": "v1",
    }

    with pytest.raises(ProviderError, match="MODEL_OUTPUT_SCHEMA_INVALID"):
        parse_strict_contract_json(f"结果如下：{json.dumps(payload, ensure_ascii=False)}")


@pytest.mark.asyncio
async def test_private_provider_uses_gold_free_prompt_and_one_schema_retry() -> None:
    valid = {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": "北京明天天气"},
        "normalized_command": "搜索北京明天天气",
        "language": "zh-CN",
        "contract_version": "v1",
    }
    prompts: list[str] = []
    outputs = iter(["{}", json.dumps(valid, ensure_ascii=False)])

    async def decode(prompt: str) -> str:
        prompts.append(prompt)
        return next(outputs)

    provider = LocalPeftVoice2TaskProvider(decoder=decode)
    result = await provider.infer("帮我搜索北京明天的天气")

    assert result.inference_mode == "private_model"
    assert result.retry_attempted is True
    assert len(prompts) == 2
    assert PREDICTION_SYSTEM_PROMPT in prompts[0]
    assert "帮我搜索北京明天的天气" in prompts[0]
    assert "machine_contract_regeneration" in prompts[1]


@pytest.mark.asyncio
async def test_private_provider_loads_tokenizer_before_rendering_first_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": "北京明天天气"},
        "normalized_command": "搜索北京明天天气",
        "language": "zh-CN",
        "contract_version": "v1",
    }
    calls: list[str] = []

    class TemplateTokenizer:
        def apply_chat_template(
            self,
            messages: list[dict[str, str]],
            *,
            tokenize: bool,
            add_generation_prompt: bool,
        ) -> str:
            assert tokenize is False
            assert add_generation_prompt is True
            calls.append("render")
            return f"template::{messages[-1]['content']}"

    provider = LocalPeftVoice2TaskProvider()

    async def load() -> None:
        calls.append("load")
        provider._tokenizer = TemplateTokenizer()

    async def decode(prompt: str) -> str:
        calls.append(f"decode::{prompt}")
        return json.dumps(valid, ensure_ascii=False)

    monkeypatch.setattr(provider, "load", load)
    monkeypatch.setattr(provider, "_decode", decode)

    result = await provider.infer("帮我搜索北京明天的天气")

    assert result.inference_mode == "private_model"
    assert calls == [
        "load",
        "render",
        "decode::template::帮我搜索北京明天的天气",
    ]


@pytest.mark.asyncio
async def test_private_provider_never_falls_back_to_fixture() -> None:
    calls = 0

    async def decode(_prompt: str) -> str:
        nonlocal calls
        calls += 1
        return "not json"

    provider = LocalPeftVoice2TaskProvider(decoder=decode)

    with pytest.raises(ProviderError, match="MODEL_OUTPUT_SCHEMA_INVALID") as exc_info:
        await provider.infer("帮我搜索北京明天的天气")

    assert calls == 2
    assert exc_info.value.code == "MODEL_OUTPUT_SCHEMA_INVALID"


@pytest.mark.asyncio
async def test_private_provider_does_not_retry_semantic_failure() -> None:
    calls = 0
    schema_valid_semantically_invalid = {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": "北京明天天气"},
        "normalized_command": "搜索北京明天天气",
        "language": "zh-CN",
        "contract_version": "v1",
    }
    schema_valid_semantically_invalid["route"] = "open_url"

    async def decode(_prompt: str) -> str:
        nonlocal calls
        calls += 1
        return json.dumps(schema_valid_semantically_invalid, ensure_ascii=False)

    provider = LocalPeftVoice2TaskProvider(decoder=decode)

    with pytest.raises(ProviderError, match="MODEL_OUTPUT_SEMANTIC_INVALID"):
        await provider.infer("帮我搜索北京明天的天气")

    assert calls == 1
