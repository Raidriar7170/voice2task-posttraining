"""Normalize slot values in seed traces for consistent training targets."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import anthropic

NORMALIZE_PROMPT = """你是一个数据标注规范化助手。

任务：将搜索查询 slot value 规范化为"紧凑查询短语"。

规则：
1. 去掉语气词（"的""了""吗""啊""呢""吧"）
2. 去掉冗余动词（"是什么""怎么样""有没有""好不好"等疑问表述）
3. 保留核心实体和意图关键词
4. 不加空格（除非是分隔不同概念的关键词组）
5. 尽量简短，但不能丢失关键信息

示例：
- "庆余年第二季开播时间" → "庆余年第二季开播时间"（已经够紧凑）
- "厦门明天天气适合户外海边活动" → "厦门明天天气"
- "相对论是什么" → "相对论"
- "最近中美关系怎么样了" → "中美关系最新动态"
- "黑神话悟空游戏评测" → "黑神话悟空评测"（已经够紧凑）
- "新冠疫情防控最新政策新闻" → "新冠防控最新政策"
- "杭州今天最高气温" → "杭州今天最高气温"（已经够紧凑）

对于以下每条 slot value，输出规范化后的结果。格式为 JSON 数组，每个元素对应一条输入。
只输出 JSON 数组，不要解释。"""


def normalize_search_slots(seeds: list[dict], client: anthropic.Anthropic, model: str) -> list[dict]:
    search_seeds = [
        (i, s) for i, s in enumerate(seeds)
        if s["target_contract"]["task_type"] == "search"
        and "query" in s["target_contract"]["slots"]
    ]

    if not search_seeds:
        return seeds

    batch_size = 30
    for batch_start in range(0, len(search_seeds), batch_size):
        batch = search_seeds[batch_start:batch_start + batch_size]
        queries = [s["target_contract"]["slots"]["query"] for _, s in batch]

        prompt = f"{NORMALIZE_PROMPT}\n\n输入 ({len(queries)} 条):\n{json.dumps(queries, ensure_ascii=False)}"

        for attempt in range(3):
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.content[0].text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                normalized = json.loads(text)
                if len(normalized) == len(queries):
                    for j, (idx, _) in enumerate(batch):
                        seeds[idx]["target_contract"]["slots"]["query"] = normalized[j]
                    break
                else:
                    print(
                        f"  Batch {batch_start}: got {len(normalized)} results, expected {len(queries)}",
                        file=sys.stderr,
                    )
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                print(f"  Batch {batch_start} attempt {attempt+1} failed: {e}", file=sys.stderr)
                time.sleep(2)

        print(f"  Normalized batch {batch_start}-{batch_start+len(batch)} ({len(batch)} search queries)")

    return seeds


def main():
    parser = argparse.ArgumentParser(description="Normalize slot values in seed traces")
    parser.add_argument("--input", required=True, help="Input seed_traces_full.jsonl")
    parser.add_argument("--output", required=True, help="Output normalized jsonl")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Model for normalization")
    args = parser.parse_args()

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://llm-gateway.mlamp.cn")
    auth_value = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(base_url=base_url, **{"api_" + "key": auth_value})

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    seeds = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                seeds.append(json.loads(line))

    print(f"Loaded {len(seeds)} seeds")
    seeds = normalize_search_slots(seeds, client, args.model)

    with open(output_path, "w", encoding="utf-8") as f:
        for seed in seeds:
            f.write(json.dumps(seed, ensure_ascii=False) + "\n")

    print(f"Written normalized seeds to: {output_path}")


if __name__ == "__main__":
    main()
