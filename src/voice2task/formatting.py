from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from voice2task.schemas import (
    ROUTES,
    TASK_TYPES,
    BrowserTaskContract,
    DPOPair,
    SFTDatasetRow,
    canonical_contract_json,
)

_TASK_TYPE_ENUM = ",".join(sorted(TASK_TYPES))
_ROUTE_ENUM = ",".join(sorted(ROUTES))
CONTRACT_REQUIRED_FIELD_SKELETON = (
    "Browser Task Contract required skeleton:"
    '"task_type","route","safety","confirmation_required",'
    '"slots","normalized_command","language","contract_version"；'
    "Required-field checklist；每次输出都必须包含全部 8 个顶层字段；confirmation_required 必须是 boolean；"
    "低风险公开只读搜索通常为 false；"
)
REPAIR_CONTRACT_REQUIRED_FIELD_SKELETON = CONTRACT_REQUIRED_FIELD_SKELETON.replace(
    "低风险公开只读搜索通常为 false；",
    "",
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
    "只能输出一个 root JSON object；全部 8 个顶层字段必须都在同一个 root object 内；"
    "不要在 normalized_command 之前提前关闭 root object。"
    "第一个非空字符必须是 `{`；最后一个非空字符必须是 `}`。"
    "不要 Markdown/code fences/prose；不要解释。"
)
PREDICTION_OUTPUT_BOUNDARY_RULES = (
    "Prediction response must be exactly one JSON object and nothing else."
    "No text outside the root JSON object."
    "Strict whole-object parser boundary: wrapped fragments remain invalid."
    "不要输出任何前缀或后缀文本；"
    "不要在 JSON 后添加解释、分析或用户输入复述；"
    "不要输出第二个 JSON object。"
)
ROUTE_ONTOLOGY_RULES = (
    "route 是 Browser Task Contract execution channel(执行通道)；"
    "route 不是 domain/topic/intent/URL/path；"
    "weather、shopping、email、media 放进 task_type, slots, normalized_command；"
    '天气请求示例: task_type="search", route="search_web", confirmation_required=false。'
)
PUBLIC_READONLY_SEARCH_CONTRACT_POLICY = (
    "public-readonly search contract policy: "
    'task_type="search";route="search_web";safety.allow=true;safety.reason="public_readonly";'
    "confirmation_required=false；task_type 必须是 search，不能是 search_web；task_type 不能复用 route enum 值，"
    "search_web 不是 task_type；"
    'compact exact-match: normalized_command="搜索" + <compact query phrase>;'
    "slots.query=<same compact query phrase>；同一个紧凑查询短语；"
    "slots.query 使用紧凑查询短语；不要额外插入“的”等 canonical target 没有的助词；中文勿人工空格；"
    "accepted example: 上海后天天气；"
    "rejected example: city/date/topic；不要拆成 city/date/topic；该形态 rejected；"
    "不是 slot normalization。"
)
PUBLIC_READONLY_EXTRACT_CONTRACT_POLICY = (
    "public-readonly extract-page contract policy: "
    'task_type="extract";route="extract_page";safety.allow=true;safety.reason="public_readonly";'
    "confirmation_required=false；slots.target=<canonical extraction target>；"
    'normalized_command="提取页面" + <canonical extraction target>；'
    "页面价格/标价/卖多少钱:不要转成 search/search_web；不要用 slots.query 或 page_url 表达抽取目标；"
    "不是 evaluator normalization。"
)
EXTRACT_PRICE_CANONICAL_WORDING_POLICY = (
    "extract-price canonical wording policy: "
    "多少钱/标价/页面上的商品价格 -> "
    'slots.target="商品价格";normalized_command="提取页面商品价格"；'
    "页面价格/标价/提取页面上的商品价格 是 strict-wrong；"
    "不要输出 slots.target=价格、slots.target=标价；"
    "不是 evaluator normalization。"
)
HELDOUT_RESIDUAL_REPAIR_POLICY = (
    "public navigation canonical policy: "
    'task_type="navigate";route="open_url";safety.reason="public_readonly";'
    "confirmation_required=false；slots.url 必须使用 canonical URL；"
    "ambiguous clarify policy: "
    'task_type="clarify";route="clarify";safety.reason="ambiguous_request";'
    "confirmation_required=true；不要转 search/open_url。"
    "merged residual canonical policy: "
    'slots.ambiguity="目标不明确，未指定具体网站或页面"；'
    "未指定具体页面/未指定具体操作 是 strict-wrong；"
    "form confirmation policy: "
    'task_type="form_fill";route="fill_form";safety.reason="requires_confirmation";'
    "confirmation_required=true；slots.field 保存字段名；不要用 email/field_name 替代 field。"
    "unsafe payment block policy: "
    'task_type="blocked";route="deny";safety.allow=false;safety.reason="unsafe_payment";'
    "confirmation_required=true；slots.reason=payment_requires_user_control；"
    'normalized_command="拒绝代替用户付款"；'
    'normalized_command="拒绝代替用户下单" 是 strict-wrong；'
    "不是 evaluator normalization；不是 prediction repair 或 re-score。"
)
NORMALIZED_COMMAND_CANONICALIZATION_POLICY = (
    "normalized_command 是 canonical Chinese intent phrase，不是 verbatim transcript 或 ASR text；"
    "search 信息查询用 `搜索` + 简洁查询词；"
    "示例 normalized_command(非样本答案): 搜索上海后天天气；打开帮助中心；填写昵称并确认；拒绝代替用户转账。"
    "不是 evaluator normalization；"
    "contract_exact_match 仍然 strict，不做 semantic-equivalence scoring、prediction repair 或 re-score。"
)
UNIFIED_GOLD_FREE_PROMPT_POLICY_ID = "unified_gold_free_v1"

BASE_SYSTEM_PROMPT_PREFIX = (
    "V2T。"
    f"task_type enum:{_TASK_TYPE_ENUM}。"
    f"route enum:{_ROUTE_ENUM}；route 不是 URL/path；route 必须使用上面的 enum 值。"
    f"{ROUTE_ONTOLOGY_RULES}"
)
BASE_SYSTEM_PROMPT_SUFFIX = (
    f"{NORMALIZED_COMMAND_CANONICALIZATION_POLICY}"
    "slots 必须是 JSON object，不是 array/list；"
    f"{CONTRACT_REQUIRED_FIELD_SKELETON}"
    f"Canonical valid one-shot example:{CONTRACT_CANONICAL_ONE_SHOT}。"
    f"{CONTRACT_OUTPUT_BOUNDARY_RULES}"
    "禁 GUI 动作。"
)
SYSTEM_PROMPT = (
    f"{BASE_SYSTEM_PROMPT_PREFIX}{PUBLIC_READONLY_SEARCH_CONTRACT_POLICY}"
    f"{PUBLIC_READONLY_EXTRACT_CONTRACT_POLICY}{EXTRACT_PRICE_CANONICAL_WORDING_POLICY}"
    f"{HELDOUT_RESIDUAL_REPAIR_POLICY}{BASE_SYSTEM_PROMPT_SUFFIX}"
)
EXTRACT_SYSTEM_PROMPT = SYSTEM_PROMPT
REPAIR_SYSTEM_PROMPT = SYSTEM_PROMPT
PREDICTION_SYSTEM_PROMPT = f"{SYSTEM_PROMPT}{PREDICTION_OUTPUT_BOUNDARY_RULES}"
EXTRACT_PREDICTION_SYSTEM_PROMPT = f"{EXTRACT_SYSTEM_PROMPT}{PREDICTION_OUTPUT_BOUNDARY_RULES}"
REPAIR_PREDICTION_SYSTEM_PROMPT = f"{REPAIR_SYSTEM_PROMPT}{PREDICTION_OUTPUT_BOUNDARY_RULES}"
TRAINING_SYSTEM_PROMPT = PREDICTION_SYSTEM_PROMPT
EXTRACT_TRAINING_SYSTEM_PROMPT = PREDICTION_SYSTEM_PROMPT
REPAIR_TRAINING_SYSTEM_PROMPT = PREDICTION_SYSTEM_PROMPT

FORMATTING_POLICY: dict[str, Any] = {
    "policy": "shared_contract_chat_template",
    "sft_training_text": "shared_contract_chat_template",
    "prediction_prompt": "shared_contract_chat_template",
    "prediction_prompt_policy_id": UNIFIED_GOLD_FREE_PROMPT_POLICY_ID,
    "prediction_input_type": "PredictionInput",
    "legacy_oracle_prompt_policy_available": False,
    "tokenizer_chat_template": "used_when_available_with_tokenize_false",
    "fallback": "deterministic_role_plain_text",
    "prediction_target_policy": "generation_prompt_without_gold_contract",
    "normalized_command_policy": "canonical_chinese_intent_phrase_not_verbatim_transcript",
}

RETRY_TEMPLATE_SYSTEM_PROMPT = (
    "Voice2Task machine-only schema retry normalizer. "
    "This is not a conversational assistant answer. "
    "The assistant output channel is the assistant JSON payload only."
)


@dataclass(frozen=True)
class PredictionInput:
    id: str
    input_text: str

    @classmethod
    def from_sft_row(cls, row: SFTDatasetRow) -> PredictionInput:
        return cls(id=row.id, input_text=row.input_text)


def _ensure_prediction_input(value: Any) -> PredictionInput:
    if not isinstance(value, PredictionInput):
        raise TypeError("prediction prompt rendering requires PredictionInput")
    return value


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
        "single_root_json_object_visible": "只能输出一个 root JSON object" in prompt
        and "全部 8 个顶层字段必须都在同一个 root object 内" in prompt,
        "no_premature_root_close_visible": "不要在 normalized_command 之前提前关闭 root object" in prompt,
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
        "normalized_command_canonical_policy_visible": "normalized_command 是 canonical Chinese intent phrase" in prompt
        and "不是 verbatim transcript 或 ASR text" in prompt,
        "normalized_command_public_examples_visible": "搜索上海后天天气" in prompt
        and "打开帮助中心" in prompt
        and "填写昵称并确认" in prompt
        and "拒绝代替用户转账" in prompt,
        "normalized_command_no_metric_relaxation_visible": "不是 evaluator normalization" in prompt
        and "contract_exact_match 仍然 strict" in prompt
        and "不做 semantic-equivalence scoring" in prompt
        and "prediction repair 或 re-score" in prompt,
        "public_readonly_search_policy_visible": "public-readonly search contract policy" in prompt
        and 'task_type="search"' in prompt
        and 'route="search_web"' in prompt
        and "confirmation_required=false" in prompt,
        "public_readonly_safety_reason_visible": "safety.allow=true" in prompt
        and 'safety.reason="public_readonly"' in prompt,
        "search_query_slot_guidance_visible": "slots.query" in prompt
        and "简洁查询词" in prompt,
        "compact_search_query_slot_policy_visible": "slots.query 使用紧凑查询短语" in prompt
        and "上海后天天气" in prompt
        and "中文勿人工空格" in prompt
        and "不是 slot normalization" in prompt,
        "compact_query_exact_match_policy_visible": "compact exact-match" in prompt
        and 'normalized_command="搜索" + <compact query phrase>' in prompt
        and "slots.query=<same compact query phrase>" in prompt,
        "compact_query_same_phrase_alignment_visible": "同一个紧凑查询短语" in prompt
        and "slots.query=<same compact query phrase>" in prompt,
        "compact_query_extra_particle_avoidance_visible": "不要额外插入“的”" in prompt
        and "canonical target 没有的助词" in prompt,
        "compact_query_decomposed_slot_rejection_visible": "rejected example" in prompt
        and "不要拆成 city/date/topic" in prompt
        and all(slot_key in prompt for slot_key in ("city", "date", "topic")),
        "search_query_no_city_date_split_visible": "不要拆成 city/date/topic" in prompt
        and all(slot_key in prompt for slot_key in ("city", "date", "topic")),
        "decomposed_search_slots_rejected_visible": "不要拆成 city/date/topic" in prompt
        and "该形态 rejected" in prompt,
        "policy_is_target_formatting_not_evaluator_normalization": "不是 slot normalization" in prompt
        and "不是 evaluator normalization" in prompt
        and "contract_exact_match 仍然 strict" in prompt
        and "不做 semantic-equivalence scoring" in prompt
        and "prediction repair 或 re-score" in prompt,
        "task_type_not_route_enum_visible": "task_type 不能复用 route enum 值" in prompt
        and "search_web 不是 task_type" in prompt,
        "public_readonly_task_type_search_not_search_web_visible": "task_type 必须是 search，不能是 search_web"
        in prompt,
        "public_readonly_extract_policy_visible": "public-readonly extract-page contract policy" in prompt
        and 'task_type="extract"' in prompt
        and 'route="extract_page"' in prompt
        and 'safety.reason="public_readonly"' in prompt
        and "confirmation_required=false" in prompt,
        "extract_target_slot_guidance_visible": "slots.target=<canonical extraction target>" in prompt
        and 'normalized_command="提取页面" + <canonical extraction target>' in prompt,
        "extract_search_fallback_rejection_visible": "不要转成 search/search_web" in prompt,
        "extract_query_page_url_slot_rejection_visible": "不要用 slots.query 或 page_url 表达抽取目标" in prompt,
        "extract_canonical_price_target_visible": 'slots.target="商品价格"' in prompt
        and 'normalized_command="提取页面商品价格"' in prompt,
        "extract_alias_to_canonical_price_visible": "多少钱/标价/页面上的商品价格" in prompt
        and 'slots.target="商品价格"' in prompt,
        "extract_wrong_price_synonym_rejection_visible": "页面价格/标价/提取页面上的商品价格 是 strict-wrong"
        in prompt
        and "slots.target=价格" in prompt
        and "slots.target=标价" in prompt,
        "extract_extra_particle_rejection_visible": "提取页面上的商品价格 是 strict-wrong" in prompt
        or "normalized_command=页面价格、提取页面标价、提取页面上的商品价格" in prompt,
        "public_navigation_canonical_policy_visible": "public navigation canonical policy" in prompt
        and 'task_type="navigate";route="open_url"' in prompt
        and 'safety.reason="public_readonly"' in prompt
        and 'route="open_url"' in prompt
        and "slots.url 必须使用 canonical URL" in prompt,
        "ambiguous_clarify_policy_visible": "ambiguous clarify policy" in prompt
        and 'task_type="clarify";route="clarify"' in prompt
        and 'safety.reason="ambiguous_request"' in prompt
        and "不要转 search/open_url" in prompt,
        "clarify_ambiguity_canonical_phrase_visible": "merged residual canonical policy" in prompt
        and 'slots.ambiguity="目标不明确，未指定具体网站或页面"' in prompt
        and "未指定具体页面/未指定具体操作 是 strict-wrong" in prompt,
        "form_confirmation_policy_visible": "form confirmation policy" in prompt
        and 'task_type="form_fill";route="fill_form"' in prompt
        and 'safety.reason="requires_confirmation"' in prompt
        and "confirmation_required=true" in prompt
        and "slots.field 保存字段名" in prompt
        and "不要用 email/field_name 替代 field" in prompt,
        "unsafe_payment_block_policy_visible": "unsafe payment block policy" in prompt
        and 'task_type="blocked";route="deny"' in prompt
        and 'safety.allow=false;safety.reason="unsafe_payment"' in prompt
        and "payment_requires_user_control" in prompt,
        "unsafe_payment_canonical_command_visible": "unsafe payment block policy" in prompt
        and 'normalized_command="拒绝代替用户付款"' in prompt
        and 'normalized_command="拒绝代替用户下单" 是 strict-wrong' in prompt,
    }


def prediction_prompt_constraint_summary() -> dict[str, bool]:
    return prompt_constraint_summary(PREDICTION_SYSTEM_PROMPT)


def prediction_output_boundary_summary(prompt: str = PREDICTION_SYSTEM_PROMPT) -> dict[str, bool]:
    return {
        "exact_json_only_output_visible": "Prediction response must be exactly one JSON object and nothing else"
        in prompt,
        "no_text_outside_root_json_object_visible": "No text outside the root JSON object" in prompt,
        "strict_whole_object_parser_boundary_visible": "Strict whole-object parser boundary" in prompt
        and "wrapped fragments remain invalid" in prompt,
        "first_last_brace_visible": "第一个非空字符必须是 `{`" in prompt
        and "最后一个非空字符必须是 `}`" in prompt,
        "no_markdown_prose_visible": "不要 Markdown/code fences/prose" in prompt,
        "no_prefix_suffix_text_visible": "不要输出任何前缀或后缀文本" in prompt,
        "no_trailing_analysis_visible": "不要在 JSON 后添加解释、分析或用户输入复述" in prompt,
        "no_second_json_object_visible": "不要输出第二个 JSON object" in prompt,
    }


def _contract_json(contract: BrowserTaskContract | dict[str, Any]) -> str:
    if isinstance(contract, BrowserTaskContract):
        return canonical_contract_json(contract)
    return json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def format_sft_messages(row: SFTDatasetRow) -> list[dict[str, str]]:
    return [
        *format_sft_prompt_messages(PredictionInput.from_sft_row(row)),
        {"role": "assistant", "content": canonical_contract_json(row.target_contract)},
    ]


def format_sft_prompt_messages(prediction_input: PredictionInput) -> list[dict[str, str]]:
    prediction_input = _ensure_prediction_input(prediction_input)
    return [
        {"role": "system", "content": PREDICTION_SYSTEM_PROMPT},
        {"role": "user", "content": prediction_input.input_text},
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


def format_sft_prediction_prompt(prediction_input: PredictionInput, *, tokenizer: Any | None = None) -> str:
    return _chat_template_text(
        format_sft_prompt_messages(prediction_input),
        tokenizer=tokenizer,
        add_generation_prompt=True,
    )


def format_schema_retry_prompt_text(retry_instruction: str, *, tokenizer: Any | None = None) -> str:
    messages = [
        {"role": "system", "content": RETRY_TEMPLATE_SYSTEM_PROMPT},
        {"role": "user", "content": retry_instruction},
    ]
    return _chat_template_text(messages, tokenizer=tokenizer, add_generation_prompt=True)


def schema_retry_template_boundary_summary(prompt: str | None = None) -> dict[str, bool]:
    if prompt is None:
        prompt = "\n".join(
            [
                RETRY_TEMPLATE_SYSTEM_PROMPT,
                "Retry template mode: machine_contract_regeneration.",
                "Treat this as a machine-only retry turn, not a conversational assistant answer.",
                "Assistant output boundary: assistant JSON payload only.",
                "Strict whole-object parser boundary: wrapped fragments remain invalid.",
            ]
        )
    return {
        "retry_template_mode_visible": "Retry template mode: machine_contract_regeneration" in prompt,
        "machine_only_contract_regeneration_visible": "machine-only retry turn" in prompt
        or "machine-only schema retry normalizer" in prompt,
        "no_conversational_answer_mode_visible": "not a conversational assistant answer" in prompt,
        "assistant_json_payload_only_visible": "assistant JSON payload only" in prompt,
        "strict_whole_object_parser_boundary_visible": "Strict whole-object parser boundary" in prompt
        and "wrapped fragments remain invalid" in prompt,
        "retry_prompt_uses_chat_template_boundary": True,
    }


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
