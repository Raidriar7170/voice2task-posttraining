from __future__ import annotations

import json
from typing import Any

from voice2task.schemas import BrowserTaskContract, DPOPair, SFTDatasetRow, canonical_contract_json

SYSTEM_PROMPT = (
    "你是 Voice2Task contract normalizer。只输出 browser task contract JSON，"
    "不要解释、不要添加 Markdown、不要生成 GUI 动作。"
)


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
