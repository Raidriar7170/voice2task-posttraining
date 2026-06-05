from __future__ import annotations

import json
from typing import Any

from voice2task.schemas import ROUTES, TASK_TYPES, BrowserTaskContract, DPOPair, SFTDatasetRow, canonical_contract_json

_TASK_TYPE_ENUM = ", ".join(sorted(TASK_TYPES))
_ROUTE_ENUM = ", ".join(sorted(ROUTES))
CONTRACT_REQUIRED_FIELD_SKELETON = (
    "Browser Task Contract required skeleton: "
    '{"task_type":"<one of task_type enum>","route":"<one of route enum>",'
    '"safety":{"allow":<boolean>,"reason":"<non-empty string>"},'
    '"confirmation_required":<boolean>,"slots":{...},'
    '"normalized_command":"<Chinese normalized command>","language":"zh-CN","contract_version":"v1"}。'
    "Required-field checklist: task_type, route, safety, confirmation_required, slots, "
    "normalized_command, language, contract_version. 每次输出都必须包含全部 8 个顶层字段；"
    "confirmation_required 必须是 boolean；低风险公开只读搜索通常为 false。"
    "即使字段值很简单，也不能省略 safety、confirmation_required、normalized_command 或 contract_version。"
)
CONTRACT_CANONICAL_ONE_SHOT = canonical_contract_json(
    BrowserTaskContract(
        task_type="search",
        route="search_web",
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"query": "公开信息"},
        normalized_command="搜索公开信息",
    )
)
CONTRACT_OUTPUT_BOUNDARY_RULES = (
    "第一个非空字符必须是 `{`；最后一个非空字符必须是 `}`。"
    "不要 Markdown/code fences/prose；不要解释、不要自然语言前后缀。"
)
ROUTE_ONTOLOGY_RULES = (
    "route 是 Browser Task Contract execution channel，只能表示执行通道。"
    "route 不是 domain/topic/intent/URL/path；weather、shopping、email、media、URL host 等领域词"
    "必须放进 task_type, slots, normalized_command，不要当作 route。"
    '天气请求示例: task_type="search", route="search_web", confirmation_required=false, '
    'slots={"query":"北京 明天 天气"}。'
)

SYSTEM_PROMPT = (
    "你是 Voice2Task contract normalizer。只输出一个 Browser Task Contract JSON object。"
    "必须包含且只使用这些顶层字段：task_type, route, safety, confirmation_required, slots, "
    "normalized_command, language, contract_version。"
    f"task_type enum: {_TASK_TYPE_ENUM}。"
    f"route enum: {_ROUTE_ENUM}；route 不是 URL/path；route 必须使用上面的 enum 值。"
    f"{ROUTE_ONTOLOGY_RULES}"
    "slots 必须是 JSON object，不是 array/list。"
    "safety 必须包含 safety.allow 和 safety.reason；language 必须为 zh-CN；contract_version 必须为 v1。"
    f"{CONTRACT_REQUIRED_FIELD_SKELETON}"
    f"Canonical valid one-shot example: {CONTRACT_CANONICAL_ONE_SHOT}。这是格式示例，不是当前用户的目标答案。"
    f"{CONTRACT_OUTPUT_BOUNDARY_RULES}"
    "不要生成 GUI 动作或浏览器点击/输入步骤。"
)

FORMATTING_POLICY: dict[str, Any] = {
    "policy": "shared_contract_chat_template",
    "sft_training_text": "shared_contract_chat_template",
    "prediction_prompt": "shared_contract_chat_template",
    "tokenizer_chat_template": "used_when_available_with_tokenize_false",
    "fallback": "deterministic_role_plain_text",
    "prediction_target_policy": "generation_prompt_without_gold_contract",
}


def prompt_constraint_summary(prompt: str = SYSTEM_PROMPT) -> dict[str, bool]:
    prompt_lower = prompt.lower()
    return {
        "task_type_enum_visible": all(task_type in prompt for task_type in TASK_TYPES),
        "route_enum_visible": all(route in prompt for route in ROUTES),
        "route_not_url_or_path_visible": "route 不是 URL/path" in prompt
        or ("route" in prompt and "not" in prompt_lower and "url" in prompt_lower and "path" in prompt_lower),
        "slots_object_not_array_visible": "slots" in prompt
        and "JSON object" in prompt
        and ("不是 array/list" in prompt or ("not" in prompt_lower and "array" in prompt_lower)),
        "required_field_skeleton_visible": "Browser Task Contract required skeleton" in prompt
        and all(f'"{field}"' in prompt for field in ("task_type", "route", "safety", "slots")),
        "required_field_checklist_visible": "Required-field checklist" in prompt
        and "每次输出都必须包含全部 8 个顶层字段" in prompt,
        "canonical_json_one_shot_visible": "Canonical valid one-shot example" in prompt
        and CONTRACT_CANONICAL_ONE_SHOT in prompt,
        "whole_object_boundary_visible": "第一个非空字符必须是 `{`" in prompt
        and "最后一个非空字符必须是 `}`" in prompt
        and "不要 Markdown/code fences/prose" in prompt,
        "route_execution_channel_visible": "route 是 Browser Task Contract execution channel" in prompt
        and "执行通道" in prompt,
        "route_domain_values_not_route_visible": "route 不是 domain/topic/intent/URL/path" in prompt
        and "weather、shopping、email、media" in prompt
        and "放进 task_type, slots, normalized_command" in prompt,
        "weather_to_search_route_example_visible": '天气请求示例: task_type="search", route="search_web"' in prompt
        and 'route="weather"' not in prompt,
        "confirmation_required_boolean_visible": "confirmation_required 必须是 boolean" in prompt
        and "低风险公开只读搜索通常为 false" in prompt,
        "weather_to_search_confirmation_false_visible": '天气请求示例: task_type="search", route="search_web"'
        in prompt
        and "confirmation_required=false" in prompt
        and 'route="weather"' not in prompt,
    }


def _contract_json(contract: BrowserTaskContract | dict[str, Any]) -> str:
    if isinstance(contract, BrowserTaskContract):
        return canonical_contract_json(contract)
    return json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def format_sft_messages(row: SFTDatasetRow) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": row.input_text},
        {"role": "assistant", "content": canonical_contract_json(row.target_contract)},
    ]


def format_sft_prompt_messages(row: SFTDatasetRow) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": row.input_text},
    ]


def _fallback_chat_text(messages: list[dict[str, str]], *, add_generation_prompt: bool) -> str:
    lines = [f"{message['role']}: {message['content']}" for message in messages]
    if add_generation_prompt:
        lines.append("assistant:")
    return "\n".join(lines)


def _chat_template_text(
    messages: list[dict[str, str]],
    *,
    tokenizer: Any | None,
    add_generation_prompt: bool,
) -> str:
    apply_chat_template = getattr(tokenizer, "apply_chat_template", None)
    if callable(apply_chat_template):
        try:
            rendered = apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=add_generation_prompt,
            )
        except (AttributeError, TypeError, ValueError):
            rendered = None
        except Exception as exc:
            if not _is_template_render_error(exc):
                raise
            rendered = None
        if isinstance(rendered, str):
            return rendered
    return _fallback_chat_text(messages, add_generation_prompt=add_generation_prompt)


def _is_template_render_error(exc: Exception) -> bool:
    exc_type = type(exc)
    return exc_type.__module__.startswith("jinja2.") and exc_type.__name__.endswith("Error")


def format_sft_training_text(row: SFTDatasetRow, *, tokenizer: Any | None = None) -> str:
    return _chat_template_text(format_sft_messages(row), tokenizer=tokenizer, add_generation_prompt=False)


def format_sft_prediction_prompt(row: SFTDatasetRow, *, tokenizer: Any | None = None) -> str:
    return _chat_template_text(format_sft_prompt_messages(row), tokenizer=tokenizer, add_generation_prompt=True)


def format_dpo_pair(pair: DPOPair) -> dict[str, Any]:
    return {
        "id": pair.id,
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": pair.input_text},
        ],
        "chosen": canonical_contract_json(pair.chosen_contract),
        "rejected": _contract_json(pair.rejected_contract),
        "rejection_reason": pair.rejection_reason,
    }
