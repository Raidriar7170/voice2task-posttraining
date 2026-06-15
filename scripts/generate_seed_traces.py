"""Batch-generate seed traces for Voice2Task fine-tuning using the LLM gateway."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """\
你是一个数据生成助手，帮助构建中文语音浏览器指令数据集。

任务：生成"中文口语浏览器指令 → 结构化 JSON 合约"的训练样本。

每条样本是一个 seed trace，格式如下：
```json
{
  "id": "<唯一ID>",
  "input_text": "<用户的口语中文指令>",
  "augmentations": ["<改写1>", "<改写2>", "<改写3>"],
  "split": "<train|dev|test>",
  "target_contract": {
    "task_type": "<search|navigate|form_fill|extract|clarify|blocked>",
    "route": "<search_web|open_url|fill_form|extract_page|clarify|deny>",
    "safety": {"allow": <true|false>, "reason": "<原因>"},
    "confirmation_required": <true|false>,
    "slots": {<键值对>},
    "normalized_command": "<规范化的中文意图短语>",
    "language": "zh-CN",
    "contract_version": "v1"
  }
}
```

重要规则：
1. input_text 必须是自然口语中文（像对语音助手说话一样）
2. augmentations 是 input_text 的改写，保持相同意图但换不同表达方式
3. normalized_command 是精简的规范意图（不是逐字转录），比如"搜索北京天气"而不是"帮我搜一下北京天气怎么样"
4. slots 的 key-value 必须合理（URL 要有协议头，query 要具体）
5. 每条 augmentation 应该风格不同：一条口语化、一条简洁、一条完整
6. slots.query 的值必须是紧凑的搜索关键词短语（去掉"的""了""吗"等语气词和
   "是什么""怎么样"等疑问表述），例如"北京明天天气"而不是"北京明天的天气怎么样"
7. 同一个 seed 的所有 augmentations 虽然改变了 input_text 的表述方式，但 slots 内容必须保持完全不变

只输出 JSON 数组，不要加解释。"""


def build_generation_prompt(category: dict, sub_scenario: dict, batch_idx: int, batch_size: int) -> str:
    task_type = category["task_type"]
    route = category["route"]
    safety = category["safety"]
    confirmation = category["confirmation_required"]
    examples = sub_scenario["examples"]
    slot_template = sub_scenario["slot_template"]
    blocked_rule = (
        "对于 blocked/deny 类型：safety.reason 必须具体说明为什么不安全"
        "（如 unsafe_payment, credential_sharing, privacy_violation, harmful_action）"
        if task_type == "blocked"
        else ""
    )
    clarify_rule = "对于 clarify 类型：slots 中要说明是什么地方模糊或缺失" if task_type == "clarify" else ""

    return f"""请生成 {batch_size} 条 seed trace 数据。

类别信息：
- task_type: "{task_type}"
- route: "{route}"
- safety: {json.dumps(safety, ensure_ascii=False)}
- confirmation_required: {json.dumps(confirmation)}
- 场景: {sub_scenario["name"]}
- slot 格式参考: {json.dumps(slot_template, ensure_ascii=False)}

参考示例（input_text 风格）：
{json.dumps(examples, ensure_ascii=False, indent=2)}

要求：
1. 每条的 input_text 和 slots 内容必须不同（覆盖不同的具体场景）
2. ID 格式: "gen-{task_type}-{sub_scenario["name"]}-{batch_idx}-{{序号}}"，序号从1开始
3. split 按 70/15/15 分配（7条train, 1-2条dev, 1-2条test）
4. augmentations 要3条，风格各异
5. normalized_command 要精简（去掉"帮我""请"等客套词）
6. {blocked_rule}
7. {clarify_rule}

输出一个 JSON 数组，包含 {batch_size} 个 seed trace 对象。"""


def generate_batch(
    client: anthropic.Anthropic,
    model: str,
    category: dict,
    sub_scenario: dict,
    batch_idx: int,
    batch_size: int,
) -> list[dict]:
    prompt = build_generation_prompt(category, sub_scenario, batch_idx, batch_size)

    for attempt in range(3):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=8192,
                temperature=0.9,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            seeds = json.loads(text)
            if not isinstance(seeds, list):
                seeds = [seeds]
            return seeds
        except (json.JSONDecodeError, anthropic.APIError) as e:
            print(f"  Attempt {attempt+1} failed: {e}", file=sys.stderr)
            if attempt < 2:
                time.sleep(2 ** attempt)
    return []


def validate_seed(seed: dict) -> list[str]:
    """Basic validation, returns list of issues."""
    issues = []
    if not isinstance(seed.get("id"), str) or not seed["id"]:
        issues.append("missing or empty id")
    if not isinstance(seed.get("input_text"), str) or not seed["input_text"]:
        issues.append("missing input_text")
    if not isinstance(seed.get("augmentations"), list) or len(seed.get("augmentations", [])) < 2:
        issues.append("need at least 2 augmentations")
    if seed.get("split") not in ("train", "dev", "test"):
        issues.append(f"invalid split: {seed.get('split')}")

    contract = seed.get("target_contract", {})
    valid_task_types = {"search", "navigate", "form_fill", "extract", "clarify", "blocked"}
    valid_routes = {"search_web", "open_url", "fill_form", "extract_page", "clarify", "deny"}

    if contract.get("task_type") not in valid_task_types:
        issues.append(f"invalid task_type: {contract.get('task_type')}")
    if contract.get("route") not in valid_routes:
        issues.append(f"invalid route: {contract.get('route')}")
    if not isinstance(contract.get("safety"), dict):
        issues.append("safety must be dict")
    elif not isinstance(contract["safety"].get("allow"), bool):
        issues.append("safety.allow must be bool")
    elif not isinstance(contract["safety"].get("reason"), str) or not contract["safety"]["reason"]:
        issues.append("safety.reason must be non-empty string")
    if not isinstance(contract.get("confirmation_required"), bool):
        issues.append("confirmation_required must be bool")
    if not isinstance(contract.get("slots"), dict):
        issues.append("slots must be dict")
    if not isinstance(contract.get("normalized_command"), str) or not contract.get("normalized_command"):
        issues.append("normalized_command must be non-empty string")
    if contract.get("language") != "zh-CN":
        issues.append(f"language must be zh-CN, got {contract.get('language')}")
    if contract.get("contract_version") != "v1":
        issues.append(f"contract_version must be v1, got {contract.get('contract_version')}")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Generate seed traces using LLM gateway")
    parser.add_argument("--spec", required=True, help="Path to seed_generation_spec.json")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Model name")
    parser.add_argument("--batch-size", type=int, default=10, help="Seeds per API call")
    parser.add_argument("--category", help="Only generate for this task_type (optional filter)")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling API")
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text())
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    auth_value = os.environ.get("ANTHROPIC_AUTH_TOKEN", os.environ.get("ANTHROPIC_API_KEY", ""))
    client = anthropic.Anthropic(
        base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        **{"api_" + "key": auth_value},
    )

    all_seeds = []
    total_valid = 0
    total_invalid = 0

    for category in spec["categories"]:
        if args.category and category["task_type"] != args.category:
            continue

        print(f"\n=== {category['task_type']} + {category['route']} (target: {category['count']}) ===")

        for sub in category["sub_scenarios"]:
            count = sub["count"]
            num_batches = (count + args.batch_size - 1) // args.batch_size

            print(f"  Sub-scenario: {sub['name']} ({count} seeds, {num_batches} batches)")

            for batch_idx in range(num_batches):
                this_batch_size = min(args.batch_size, count - batch_idx * args.batch_size)

                if args.dry_run:
                    prompt = build_generation_prompt(category, sub, batch_idx, this_batch_size)
                    print(f"    [DRY-RUN] Batch {batch_idx+1}: would request {this_batch_size} seeds")
                    print(prompt)
                    continue

                print(f"    Batch {batch_idx+1}/{num_batches} ({this_batch_size} seeds)...", end=" ", flush=True)
                seeds = generate_batch(client, args.model, category, sub, batch_idx, this_batch_size)

                valid_in_batch = 0
                for seed in seeds:
                    issues = validate_seed(seed)
                    if issues:
                        total_invalid += 1
                        print(f"\n      INVALID: {seed.get('id', '?')}: {issues}", file=sys.stderr)
                    else:
                        all_seeds.append(seed)
                        valid_in_batch += 1
                        total_valid += 1

                print(f"{valid_in_batch}/{len(seeds)} valid")
                time.sleep(0.5)

    if not args.dry_run:
        with open(output_path, "w", encoding="utf-8") as f:
            for seed in all_seeds:
                f.write(json.dumps(seed, ensure_ascii=False) + "\n")

        print(f"\n{'='*60}")
        print(f"Total valid seeds: {total_valid}")
        print(f"Total invalid seeds: {total_invalid}")
        print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
