import json
from pathlib import Path

from voice2task import formatting
from voice2task.formatting import SYSTEM_PROMPT, format_dpo_pair, format_sft_messages
from voice2task.schemas import ROUTES, TASK_TYPES, BrowserTaskContract, DPOPair, SFTDatasetRow
from voice2task.training import run_dpo, run_sft


def _contract() -> BrowserTaskContract:
    return BrowserTaskContract(
        task_type="search",
        route="search_web",
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"query": "高铁票"},
        normalized_command="搜索高铁票",
    )


class _ChatTemplateTokenizer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        self.calls.append(
            {
                "messages": messages,
                "tokenize": tokenize,
                "add_generation_prompt": add_generation_prompt,
            }
        )
        rendered = "".join(f"<{message['role']}>{message['content']}</{message['role']}>" for message in messages)
        if add_generation_prompt:
            rendered += "<assistant>"
        return rendered


class _TemplateRenderError(Exception):
    pass


_TemplateRenderError.__module__ = "jinja2.exceptions"


class _FailingChatTemplateTokenizer:
    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        raise _TemplateRenderError("template render failed")


def test_sft_formatter_uses_contract_json_only() -> None:
    row = SFTDatasetRow(
        id="sft-1",
        split="train",
        input_text="帮我搜高铁票",
        target_contract=_contract(),
        provenance={"source_id": "seed-1", "public_safe": True},
    )

    messages = format_sft_messages(row)

    assert [message["role"] for message in messages] == ["system", "user", "assistant"]
    assistant = messages[-1]["content"]
    assert assistant.startswith("{")
    assert "我可以" not in assistant
    assert json.loads(assistant)["route"] == "search_web"


def test_sft_training_text_uses_tokenizer_chat_template_when_available() -> None:
    row = SFTDatasetRow(
        id="sft-1",
        split="train",
        input_text="帮我搜高铁票",
        target_contract=_contract(),
        provenance={"source_id": "seed-1", "public_safe": True},
    )
    tokenizer = _ChatTemplateTokenizer()

    text = formatting.format_sft_training_text(row, tokenizer=tokenizer)

    assert text.startswith("<system>")
    assert "<assistant>" in text
    assert json.loads(text.split("<assistant>", 1)[1].split("</assistant>", 1)[0])["route"] == "search_web"
    assert tokenizer.calls == [
        {
            "messages": format_sft_messages(row),
            "tokenize": False,
            "add_generation_prompt": False,
        }
    ]


def test_sft_prediction_prompt_uses_generation_prompt_without_gold_contract() -> None:
    row = SFTDatasetRow(
        id="sft-1",
        split="train",
        input_text="帮我处理这个公开页面",
        target_contract=BrowserTaskContract(
            task_type="search",
            route="search_web",
            safety={"allow": True, "reason": "public_readonly"},
            confirmation_required=False,
            slots={"query": "gold-only-token"},
            normalized_command="搜索 gold-only-token",
        ),
        provenance={"source_id": "seed-1", "public_safe": True},
    )
    tokenizer = _ChatTemplateTokenizer()

    prompt = formatting.format_sft_prediction_prompt(row, tokenizer=tokenizer)

    assert prompt.endswith("<assistant>")
    assert "gold-only-token" not in prompt
    assert "task_type" in prompt
    assert all(task_type in prompt for task_type in TASK_TYPES)
    assert "route" in prompt
    assert all(route in prompt for route in ROUTES)
    assert "route 不是 URL/path" in prompt
    assert "slots 必须是 JSON object" in prompt
    assert "不是 array/list" in prompt
    assert tokenizer.calls[0]["add_generation_prompt"] is True
    assert [message["role"] for message in tokenizer.calls[0]["messages"]] == ["system", "user"]


def test_sft_prediction_prompt_includes_required_field_skeleton_without_gold_contract() -> None:
    row = SFTDatasetRow(
        id="sft-1",
        split="train",
        input_text="帮我处理这个公开页面",
        target_contract=BrowserTaskContract(
            task_type="search",
            route="search_web",
            safety={"allow": True, "reason": "public_readonly"},
            confirmation_required=False,
            slots={"query": "gold-only-token"},
            normalized_command="搜索 gold-only-token",
        ),
        provenance={"source_id": "seed-1", "public_safe": True},
    )

    prompt = formatting.format_sft_prediction_prompt(row, tokenizer=None)
    summary = formatting.prompt_constraint_summary()

    assert "Browser Task Contract required skeleton" in prompt
    for field in (
        '"task_type"',
        '"route"',
        '"safety"',
        '"confirmation_required"',
        '"slots"',
        '"normalized_command"',
        '"language"',
        '"contract_version"',
    ):
        assert field in prompt
    assert '"allow"' in prompt
    assert '"reason"' in prompt
    assert "每次输出都必须包含全部 8 个顶层字段" in prompt
    assert "gold-only-token" not in prompt
    assert summary["required_field_skeleton_visible"] is True
    assert summary["required_field_checklist_visible"] is True


def test_sft_prediction_prompt_includes_canonical_one_shot_and_whole_object_boundaries_without_gold_contract() -> None:
    row = SFTDatasetRow(
        id="sft-1",
        split="train",
        input_text="帮我处理这个公开页面",
        target_contract=BrowserTaskContract(
            task_type="search",
            route="search_web",
            safety={"allow": True, "reason": "public_readonly"},
            confirmation_required=False,
            slots={"query": "gold-only-token"},
            normalized_command="搜索 gold-only-token",
        ),
        provenance={"source_id": "seed-1", "public_safe": True},
    )

    prompt = formatting.format_sft_prediction_prompt(row, tokenizer=None)
    summary = formatting.prompt_constraint_summary()

    assert "Canonical valid one-shot example" in prompt
    assert '"task_type":"search"' in prompt
    assert '"route":"search_web"' in prompt
    assert '"safety":{"allow":true,"reason":"public_readonly"}' in prompt
    assert '"confirmation_required":false' in prompt
    assert '"slots":{"query":"公开信息"}' in prompt
    assert '"normalized_command":"搜索公开信息"' in prompt
    assert "第一个非空字符必须是 `{`" in prompt
    assert "最后一个非空字符必须是 `}`" in prompt
    assert "不要 Markdown/code fences/prose" in prompt
    assert "gold-only-token" not in prompt
    assert summary["canonical_json_one_shot_visible"] is True
    assert summary["whole_object_boundary_visible"] is True


def test_sft_training_text_exposes_route_execution_channel_ontology() -> None:
    row = SFTDatasetRow(
        id="sft-weather-1",
        split="train",
        input_text="帮我查上海明天的天气",
        target_contract=BrowserTaskContract(
            task_type="search",
            route="search_web",
            safety={"allow": True, "reason": "public_readonly"},
            confirmation_required=False,
            slots={"query": "上海明天天气"},
            normalized_command="搜索上海明天天气",
        ),
        provenance={"source_id": "seed-search-weather", "public_safe": True},
    )

    text = formatting.format_sft_training_text(row, tokenizer=None)
    summary = formatting.prompt_constraint_summary()

    assert "route 是 Browser Task Contract execution channel" in text
    assert "route 不是 domain/topic/intent/URL/path" in text
    assert "weather、shopping、email、media" in text
    assert "放进 task_type, slots, normalized_command" in text
    assert '天气请求示例: task_type="search", route="search_web"' in text
    assert "confirmation_required=false" in text
    assert 'route="weather"' not in text
    assert summary["route_execution_channel_visible"] is True
    assert summary["route_domain_values_not_route_visible"] is True
    assert summary["weather_to_search_route_example_visible"] is True
    assert summary["weather_to_search_confirmation_false_visible"] is True


def test_sft_prompts_expose_normalized_command_canonicalization_policy_without_gold_target() -> None:
    row = SFTDatasetRow(
        id="sft-weather-1",
        split="train",
        input_text="帮我查上海明天的天气",
        target_contract=BrowserTaskContract(
            task_type="search",
            route="search_web",
            safety={"allow": True, "reason": "public_readonly"},
            confirmation_required=False,
            slots={"query": "gold-weather-token"},
            normalized_command="搜索 gold-weather-token",
        ),
        provenance={"source_id": "seed-search-weather", "public_safe": True},
    )

    training_text = formatting.format_sft_training_text(row, tokenizer=None)
    prediction_prompt = formatting.format_sft_prediction_prompt(row, tokenizer=None)
    summary = formatting.prompt_constraint_summary()

    for text in (training_text, prediction_prompt):
        assert "normalized_command 是 canonical Chinese intent phrase" in text
        assert "不是 verbatim transcript 或 ASR text" in text
        assert "search 信息查询用 `搜索` + 简洁查询词" in text
        assert (
            "示例 normalized_command(非样本答案): "
            "搜索上海后天天气；打开帮助中心；填写昵称并确认；拒绝代替用户转账"
        ) in text
        assert "不是 evaluator normalization" in text
        assert "contract_exact_match 仍然 strict" in text
        assert "不做 semantic-equivalence scoring" in text
        assert "prediction repair 或 re-score" in text
    assert "gold-weather-token" in training_text
    assert "gold-weather-token" not in prediction_prompt
    assert summary["normalized_command_canonical_policy_visible"] is True
    assert summary["normalized_command_public_examples_visible"] is True
    assert summary["normalized_command_no_metric_relaxation_visible"] is True


def test_sft_prompts_expose_public_readonly_search_contract_policy_without_gold_target() -> None:
    row = SFTDatasetRow(
        id="sft-weather-1",
        split="train",
        input_text="帮我查上海明天的天气",
        target_contract=BrowserTaskContract(
            task_type="search",
            route="search_web",
            safety={"allow": True, "reason": "public_readonly"},
            confirmation_required=False,
            slots={"query": "gold-weather-token"},
            normalized_command="搜索 gold-weather-token",
        ),
        provenance={"source_id": "seed-search-weather", "public_safe": True},
    )

    training_text = formatting.format_sft_training_text(row, tokenizer=None)
    prediction_prompt = formatting.format_sft_prediction_prompt(row, tokenizer=None)
    summary = formatting.prompt_constraint_summary()

    for text in (training_text, prediction_prompt):
        assert "public-readonly search contract policy" in text
        assert 'task_type="search"' in text
        assert 'route="search_web"' in text
        assert 'safety.reason="public_readonly"' in text
        assert "safety.allow=true" in text
        assert "confirmation_required=false" in text
        assert "slots.query" in text
        assert "task_type 不能复用 route enum 值" in text
        assert "search_web 不是 task_type" in text
        assert "只能输出一个 root JSON object" in text
        assert "全部 8 个顶层字段必须都在同一个 root object 内" in text
        assert "不要在 normalized_command 之前提前关闭 root object" in text
        assert "task_type 必须是 search，不能是 search_web" in text
    assert "gold-weather-token" in training_text
    assert "gold-weather-token" not in prediction_prompt
    assert summary["public_readonly_search_policy_visible"] is True
    assert summary["public_readonly_safety_reason_visible"] is True
    assert summary["search_query_slot_guidance_visible"] is True
    assert summary["task_type_not_route_enum_visible"] is True
    assert summary["single_root_json_object_visible"] is True
    assert summary["no_premature_root_close_visible"] is True
    assert summary["public_readonly_task_type_search_not_search_web_visible"] is True


def test_public_sample_sft_training_text_stays_within_runtime_sequence_budget() -> None:
    rows_path = Path("data/public-samples/sft_public_sample.jsonl")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    for payload in rows:
        row = SFTDatasetRow(
            id=payload["id"],
            split=payload["split"],
            input_text=payload["input_text"],
            target_contract=payload["target_contract"],
            provenance=payload["provenance"],
        )

        assert len(formatting.format_sft_training_text(row, tokenizer=None)) <= 2048


def test_public_sample_prediction_prompt_policy_examples_do_not_include_gold_targets() -> None:
    rows_path = Path("data/public-samples/sft_public_sample.jsonl")
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    for payload in rows:
        row = SFTDatasetRow(
            id=payload["id"],
            split=payload["split"],
            input_text=payload["input_text"],
            target_contract=payload["target_contract"],
            provenance=payload["provenance"],
        )

        system_prompt = formatting.format_sft_prompt_messages(row)[0]["content"]
        prediction_prompt = formatting.format_sft_prediction_prompt(row, tokenizer=None)

        assert row.target_contract.normalized_command not in system_prompt
        if row.target_contract.normalized_command not in row.input_text:
            assert row.target_contract.normalized_command not in prediction_prompt


def test_sft_prediction_prompt_exposes_route_ontology_without_row_gold_target_or_bad_weather_route_example() -> None:
    row = SFTDatasetRow(
        id="sft-weather-1",
        split="train",
        input_text="帮我查上海明天的天气",
        target_contract=BrowserTaskContract(
            task_type="search",
            route="search_web",
            safety={"allow": True, "reason": "public_readonly"},
            confirmation_required=False,
            slots={"query": "gold-weather-token"},
            normalized_command="搜索 gold-weather-token",
        ),
        provenance={"source_id": "seed-search-weather", "public_safe": True},
    )

    prompt = formatting.format_sft_prediction_prompt(row, tokenizer=None)

    assert "route 是 Browser Task Contract execution channel" in prompt
    assert "route 不是 domain/topic/intent/URL/path" in prompt
    assert "weather、shopping、email、media" in prompt
    assert '天气请求示例: task_type="search", route="search_web"' in prompt
    assert "confirmation_required=false" in prompt
    assert "gold-weather-token" not in prompt
    assert 'route="weather"' not in prompt


def test_sft_training_text_fallback_is_deterministic_contract_only_text() -> None:
    row = SFTDatasetRow(
        id="sft-1",
        split="train",
        input_text="帮我搜高铁票",
        target_contract=_contract(),
        provenance={"source_id": "seed-1", "public_safe": True},
    )

    text = formatting.format_sft_training_text(row, tokenizer=None)

    assistant_line = (
        "assistant: "
        f"{json.dumps(_contract().to_dict(), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
    )
    assert text == "\n".join(
        [
            f"system: {SYSTEM_PROMPT}",
            "user: 帮我搜高铁票",
            assistant_line,
        ]
    )


def test_chat_template_render_error_falls_back_to_deterministic_text() -> None:
    row = SFTDatasetRow(
        id="sft-1",
        split="train",
        input_text="帮我搜高铁票",
        target_contract=_contract(),
        provenance={"source_id": "seed-1", "public_safe": True},
    )

    text = formatting.format_sft_prediction_prompt(row, tokenizer=_FailingChatTemplateTokenizer())

    assert text == "\n".join(
        [
            f"system: {SYSTEM_PROMPT}",
            "user: 帮我搜高铁票",
            "assistant:",
        ]
    )


def test_system_prompt_enumerates_contract_fields_and_non_goals() -> None:
    for field in (
        "task_type",
        "route",
        "safety.allow",
        "safety.reason",
        "confirmation_required",
        "slots",
        "normalized_command",
        "language",
        "contract_version",
    ):
        assert field in SYSTEM_PROMPT
    for forbidden in ("不要解释", "Markdown", "GUI 动作"):
        assert forbidden in SYSTEM_PROMPT
    assert "confirmation_required 必须是 boolean" in SYSTEM_PROMPT
    assert "低风险公开只读搜索通常为 false" in SYSTEM_PROMPT


def test_system_prompt_exposes_contract_value_constraints() -> None:
    assert all(task_type in SYSTEM_PROMPT for task_type in TASK_TYPES)
    assert all(route in SYSTEM_PROMPT for route in ROUTES)
    assert "route 不是 URL/path" in SYSTEM_PROMPT
    assert "route 必须使用上面的 enum 值" in SYSTEM_PROMPT
    assert "slots 必须是 JSON object" in SYSTEM_PROMPT
    assert "不是 array/list" in SYSTEM_PROMPT
    summary = formatting.prompt_constraint_summary()
    assert summary["confirmation_required_boolean_visible"] is True
    assert summary["weather_to_search_confirmation_false_visible"] is True
    assert summary["normalized_command_canonical_policy_visible"] is True
    assert summary["public_readonly_search_policy_visible"] is True
    assert summary["public_readonly_safety_reason_visible"] is True
    assert summary["search_query_slot_guidance_visible"] is True
    assert summary["task_type_not_route_enum_visible"] is True
    assert formatting.FORMATTING_POLICY["normalized_command_policy"] == (
        "canonical_chinese_intent_phrase_not_verbatim_transcript"
    )


def test_dpo_formatter_keeps_same_prompt_with_chosen_and_rejected_contracts() -> None:
    chosen = _contract()
    rejected = BrowserTaskContract(
        task_type="search",
        route="open_url",
        safety={"allow": True, "reason": "wrong_route"},
        confirmation_required=False,
        slots={"query": "高铁票"},
        normalized_command="搜索高铁票",
    )
    pair = DPOPair(
        id="dpo-1",
        split="train",
        input_text="帮我搜高铁票",
        chosen_contract=chosen,
        rejected_contract=rejected,
        rejection_reason="wrong_route",
        provenance={"source_id": "seed-1", "public_safe": True},
    )

    formatted = format_dpo_pair(pair)

    assert formatted["prompt"][-1]["content"] == "帮我搜高铁票"
    assert json.loads(formatted["chosen"])["route"] == "search_web"
    assert json.loads(formatted["rejected"])["route"] == "open_url"
    assert formatted["rejection_reason"] == "wrong_route"


def test_sft_and_dpo_dry_runs_write_honest_adapter_metadata(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"manifest_id": "public-sample-1"}), encoding="utf-8")
    sft_config = tmp_path / "sft.json"
    dpo_config = tmp_path / "dpo.json"
    sft_config.write_text(json.dumps({"base_model": "Qwen/Qwen2.5-0.5B-Instruct", "lora": {"r": 8}}), encoding="utf-8")
    dpo_config.write_text(
        json.dumps({"base_model": "Qwen/Qwen2.5-0.5B-Instruct", "sft_model_ref": "adapters/sft-dev", "lora": {"r": 8}}),
        encoding="utf-8",
    )

    sft_meta = run_sft(config_path=sft_config, manifest_path=manifest_path, output_dir=tmp_path / "sft", dry_run=True)
    dpo_meta = run_dpo(config_path=dpo_config, manifest_path=manifest_path, output_dir=tmp_path / "dpo", dry_run=True)

    assert sft_meta["dry_run"] is True
    assert sft_meta["release_status"] == "not_released"
    assert sft_meta["dataset_manifest_id"] == "public-sample-1"
    assert sft_meta["formatting_policy"]["sft_training_text"] == "shared_contract_chat_template"
    assert sft_meta["formatting_policy"]["prediction_prompt"] == "shared_contract_chat_template"
    assert Path(sft_meta["metadata_path"]).exists()
    assert dpo_meta["sft_model_ref"] == "adapters/sft-dev"
    assert dpo_meta["release_status"] == "not_released"
    assert Path(dpo_meta["metadata_path"]).exists()


def test_sft_and_dpo_non_dry_run_report_missing_train_dependencies(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"manifest_id": "public-sample-1"}), encoding="utf-8")
    config = tmp_path / "train.json"
    config.write_text(json.dumps({"base_model": "Qwen/Qwen2.5-0.5B-Instruct"}), encoding="utf-8")

    sft_meta = run_sft(config_path=config, manifest_path=manifest_path, output_dir=tmp_path / "sft", dry_run=False)
    dpo_meta = run_dpo(config_path=config, manifest_path=manifest_path, output_dir=tmp_path / "dpo", dry_run=False)

    assert sft_meta["dry_run"] is False
    assert sft_meta["release_status"] in {"not_released", "training_skipped_by_config", "training_unavailable"}
    assert "always disabled" not in sft_meta["notes"]
    assert dpo_meta["dry_run"] is False
    assert dpo_meta["release_status"] in {"not_released", "training_skipped_by_config", "training_unavailable"}
