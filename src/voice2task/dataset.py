from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from voice2task.io import read_json, read_jsonl, write_json, write_jsonl
from voice2task.schemas import (
    BrowserTaskContract,
    DatasetManifest,
    DPOPair,
    SFTDatasetRow,
    as_contract,
    validate_public_record,
)

HARD_NEGATIVE_CATEGORIES = [
    "wrong_task_type",
    "wrong_route",
    "unsafe_allowance",
    "missing_confirmation",
    "missing_slot",
    "wrong_slot",
    "decomposed_search_slots",
    "extract_search_fallback",
    "extract_query_slot",
    "extract_generic_price_wording",
    "extract_listed_price_wording",
    "extract_extra_particle_wording",
    "clarify_action_drift",
    "blocked_payment_action_drift",
    "form_confirmation_drift",
    "navigate_canonical_url_drift",
    "underspecified_request",
    "malformed_schema",
]

EXTRACT_PRICE_CANONICAL_TARGET = "商品价格"
EXTRACT_PRICE_CANONICAL_NORMALIZED_COMMAND = "提取页面商品价格"

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_PUBLIC_MANIFEST_PATH = REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json"

_SLOT_VALUE_CANDIDATE_CASES: dict[str, dict[str, Any]] = {
    "blocked-payment-normalized-command-paraphrase": {
        "id": "candidate-blocked-payment-canonical-command",
        "split": "train",
        "input_text": "帮我替你付款买这个东西",
        "target_contract": {
            "task_type": "blocked",
            "route": "deny",
            "safety": {"allow": False, "reason": "unsafe_payment"},
            "confirmation_required": True,
            "slots": {"reason": "payment_requires_user_control"},
            "normalized_command": "拒绝代替用户付款",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        "augmentations": ["直接用我的账户完成付款", "帮我下单并付款"],
    },
    "clarify-ambiguous-slot-value-canonical-phrase": {
        "id": "candidate-clarify-ambiguous-canonical-scope",
        "split": "train",
        "input_text": "帮我打开那个网站或页面",
        "target_contract": {
            "task_type": "clarify",
            "route": "clarify",
            "safety": {"allow": True, "reason": "ambiguous_request"},
            "confirmation_required": True,
            "slots": {"ambiguity": "目标不明确，未指定具体网站或页面"},
            "normalized_command": "请求澄清目标",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        "augmentations": ["处理一下那个网页或网站", "去那个网站页面看看"],
    },
    "form-email-slot-value-language-variant": {
        "id": "candidate-form-email-canonical-field",
        "split": "train",
        "input_text": "把邮箱填进表单里，提交前先问我",
        "target_contract": {
            "task_type": "form_fill",
            "route": "fill_form",
            "safety": {"allow": True, "reason": "requires_confirmation"},
            "confirmation_required": True,
            "slots": {"field": "邮箱"},
            "normalized_command": "填写邮箱并确认",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        "augmentations": ["在网页表单里填写邮箱，提交前确认", "把电子邮箱放到表单字段里，先别提交"],
    },
    "navigate-open-url-normalized-command-paraphrase": {
        "id": "candidate-navigate-open-url-canonical-command",
        "split": "train",
        "input_text": "打开 example.com 这个示例网站",
        "target_contract": {
            "task_type": "navigate",
            "route": "open_url",
            "safety": {"allow": True, "reason": "public_readonly"},
            "confirmation_required": False,
            "slots": {"url": "https://example.com"},
            "normalized_command": "打开示例网站",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        "augmentations": ["去 example.com 示例站", "帮我访问示例网站"],
    },
}

EXPECTED_FORMAL_SLOT_VALUE_CANDIDATE_IDS = frozenset(
    str(case["id"]) for case in _SLOT_VALUE_CANDIDATE_CASES.values()
)


def _now_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}"


def _read_seed_rows(seed_path: Path) -> list[dict[str, Any]]:
    raw_rows = read_jsonl(seed_path)
    for row in raw_rows:
        as_contract(row["target_contract"])
    return raw_rows


def _compact_query_phrase(value: str) -> str:
    return "".join(value.split())


def _canonical_public_search_target(contract: BrowserTaskContract | dict[str, Any]) -> BrowserTaskContract:
    target = as_contract(contract)
    if not (
        target.task_type == "search"
        and target.route == "search_web"
        and bool(target.safety.get("allow")) is True
        and target.safety.get("reason") == "public_readonly"
        and target.confirmation_required is False
    ):
        return target

    normalized_suffix = ""
    if target.normalized_command.startswith("搜索"):
        normalized_suffix = _compact_query_phrase(target.normalized_command.removeprefix("搜索"))
    query_value = target.slots.get("query")
    if normalized_suffix:
        compact_query = normalized_suffix
    elif isinstance(query_value, str):
        compact_query = _compact_query_phrase(query_value)
    else:
        compact_query = ""
    if not compact_query:
        return target

    return _replace_contract(
        target,
        slots={"query": compact_query},
        normalized_command=f"搜索{compact_query}",
    )


def _base_row(seed: dict[str, Any], public_safe: bool) -> SFTDatasetRow:
    target_contract = seed["target_contract"]
    if public_safe:
        target_contract = _canonical_public_search_target(target_contract)
    seed_provenance = dict(seed.get("provenance") or {})
    provenance = {
        **seed_provenance,
        "source_id": seed["id"],
        "source_mode": seed_provenance.get("source_mode", "sanitized_seed"),
        "public_safe": public_safe,
        "augmentation": "original",
    }
    return SFTDatasetRow(
        id=seed["id"],
        split=seed["split"],
        input_text=seed["input_text"],
        target_contract=target_contract,
        provenance=provenance,
    )


def expand_sft_rows(seed_rows: list[dict[str, Any]], public_safe: bool) -> list[SFTDatasetRow]:
    rows: list[SFTDatasetRow] = []
    for seed in seed_rows:
        base = _base_row(seed, public_safe=public_safe)
        rows.append(base)
        for index, paraphrase in enumerate(seed.get("augmentations", []), start=1):
            rows.append(
                SFTDatasetRow(
                    id=f"{seed['id']}-aug-{index}",
                    split=seed["split"],
                    input_text=paraphrase,
                    target_contract=base.target_contract,
                    provenance={
                        **base.provenance,
                        "source_id": seed["id"],
                        "source_mode": "schema_preserving_augmentation",
                        "public_safe": public_safe,
                        "augmentation": f"paraphrase-{index}",
                    },
                )
            )
    return rows


def _replace_contract(contract: BrowserTaskContract, **updates: Any) -> BrowserTaskContract:
    data = contract.to_dict()
    data.update(updates)
    return BrowserTaskContract.from_dict(data)


def _decomposed_weather_slots(query: str) -> dict[str, str] | None:
    compact = _compact_query_phrase(query)
    if not compact.endswith("天气"):
        return None
    stem = compact.removesuffix("天气")
    for date in ("今天", "明天", "后天"):
        if stem.endswith(date):
            city = stem[: -len(date)]
            if city:
                return {"city": city, "date": date, "topic": ""}
    return None


def _decomposed_search_slots_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    if not (
        contract.task_type == "search"
        and contract.route == "search_web"
        and bool(contract.safety.get("allow")) is True
        and contract.safety.get("reason") == "public_readonly"
        and contract.confirmation_required is False
    ):
        return None
    query = contract.slots.get("query")
    if not isinstance(query, str):
        return None
    decomposed_slots = _decomposed_weather_slots(query)
    if decomposed_slots is None:
        return None
    return _replace_contract(
        contract,
        slots=decomposed_slots,
        safety={**contract.safety, "reason": "decomposed_search_slots"},
    )


def _public_extract_target(contract: BrowserTaskContract) -> str | None:
    if not (
        contract.task_type == "extract"
        and contract.route == "extract_page"
        and bool(contract.safety.get("allow")) is True
        and contract.safety.get("reason") == "public_readonly"
        and contract.confirmation_required is False
    ):
        return None
    target = contract.slots.get("target")
    if not isinstance(target, str) or not target:
        return None
    return target


def _extract_search_fallback_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    target = _public_extract_target(contract)
    if target is None:
        return None
    return _replace_contract(
        contract,
        task_type="search",
        route="search_web",
        slots={"query": target},
        normalized_command=f"搜索{target}",
        safety={**contract.safety, "reason": "extract_search_fallback"},
    )


def _extract_query_slot_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    target = _public_extract_target(contract)
    if target is None:
        return None
    return _replace_contract(
        contract,
        slots={"query": target, "page_url": ""},
        safety={**contract.safety, "reason": "extract_query_slot"},
    )


def _public_extract_price_canonical_contract(contract: BrowserTaskContract) -> bool:
    return (
        _public_extract_target(contract) == EXTRACT_PRICE_CANONICAL_TARGET
        and contract.normalized_command == EXTRACT_PRICE_CANONICAL_NORMALIZED_COMMAND
    )


def _extract_generic_price_wording_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    if not _public_extract_price_canonical_contract(contract):
        return None
    return _replace_contract(
        contract,
        slots={"target": "价格"},
        normalized_command="页面价格",
        safety={**contract.safety, "reason": "extract_generic_price_wording"},
    )


def _extract_listed_price_wording_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    if not _public_extract_price_canonical_contract(contract):
        return None
    return _replace_contract(
        contract,
        slots={"target": "标价"},
        normalized_command="提取页面标价",
        safety={**contract.safety, "reason": "extract_listed_price_wording"},
    )


def _extract_extra_particle_wording_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    if not _public_extract_price_canonical_contract(contract):
        return None
    return _replace_contract(
        contract,
        normalized_command="提取页面上的商品价格",
        safety={**contract.safety, "reason": "extract_extra_particle_wording"},
    )


def _public_clarify_contract(contract: BrowserTaskContract) -> bool:
    return (
        contract.task_type == "clarify"
        and contract.route == "clarify"
        and bool(contract.safety.get("allow")) is True
        and contract.safety.get("reason") == "ambiguous_request"
        and contract.confirmation_required is True
        and isinstance(contract.slots.get("ambiguity"), str)
    )


def _clarify_action_drift_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    if not _public_clarify_contract(contract):
        return None
    return _replace_contract(
        contract,
        task_type="search",
        route="search_web",
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"query": "公开信息"},
        normalized_command="搜索公开信息",
    )


def _public_blocked_payment_contract(contract: BrowserTaskContract) -> bool:
    return (
        contract.task_type == "blocked"
        and contract.route == "deny"
        and bool(contract.safety.get("allow")) is False
        and contract.safety.get("reason") == "unsafe_payment"
        and contract.confirmation_required is True
        and contract.slots.get("reason") == "payment_requires_user_control"
    )


def _blocked_payment_action_drift_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    if not _public_blocked_payment_contract(contract):
        return None
    return _replace_contract(
        contract,
        task_type="search",
        route="search_web",
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"query": "付款"},
        normalized_command="搜索付款",
    )


def _public_form_confirmation_contract(contract: BrowserTaskContract) -> str | None:
    if not (
        contract.task_type == "form_fill"
        and contract.route == "fill_form"
        and bool(contract.safety.get("allow")) is True
        and contract.safety.get("reason") == "requires_confirmation"
        and contract.confirmation_required is True
    ):
        return None
    field = contract.slots.get("field")
    return field if isinstance(field, str) and field else None


def _form_confirmation_drift_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    field = _public_form_confirmation_contract(contract)
    if field is None:
        return None
    return _replace_contract(
        contract,
        safety={"allow": True, "reason": "public_readonly"},
        confirmation_required=False,
        slots={"email": field},
    )


def _public_navigate_contract(contract: BrowserTaskContract) -> str | None:
    if not (
        contract.task_type == "navigate"
        and contract.route == "open_url"
        and bool(contract.safety.get("allow")) is True
        and contract.safety.get("reason") == "public_readonly"
        and contract.confirmation_required is False
    ):
        return None
    url = contract.slots.get("url")
    return url if isinstance(url, str) and url.startswith("https://") else None


def _navigate_canonical_url_drift_negative(contract: BrowserTaskContract) -> BrowserTaskContract | None:
    url = _public_navigate_contract(contract)
    if url is None:
        return None
    host = url.removeprefix("https://")
    return _replace_contract(
        contract,
        slots={"url": host},
        normalized_command=f"打开 {host}",
        safety={**contract.safety, "reason": "navigate_canonical_url_drift"},
    )


_TASK_TYPE_SWAPS: dict[str, str] = {
    "search": "navigate",
    "navigate": "search",
    "form_fill": "extract",
    "extract": "form_fill",
    "clarify": "search",
    "blocked": "navigate",
}


def _negative_contract(contract: BrowserTaskContract, category: str) -> BrowserTaskContract | dict[str, Any]:
    if category == "wrong_task_type":
        wrong_type = _TASK_TYPE_SWAPS.get(contract.task_type, "search")
        return _replace_contract(
            contract,
            task_type=wrong_type,
            safety={**contract.safety, "reason": "wrong_task_type"},
        )
    if category == "wrong_route":
        route = "open_url" if contract.route != "open_url" else "search_web"
        return _replace_contract(contract, route=route, safety={**contract.safety, "reason": "wrong_route"})
    if category == "unsafe_allowance":
        safety = {"allow": not bool(contract.safety["allow"]), "reason": "unsafe_allowance"}
        return _replace_contract(contract, safety=safety)
    if category == "missing_confirmation":
        return _replace_contract(
            contract,
            confirmation_required=False,
            safety={**contract.safety, "reason": "missing_confirmation"},
        )
    if category == "missing_slot":
        slots = dict(contract.slots)
        if slots:
            slots.pop(next(iter(slots)))
        return _replace_contract(contract, slots=slots, safety={**contract.safety, "reason": "missing_slot"})
    if category == "wrong_slot":
        slots = dict(contract.slots)
        if slots:
            first_key = next(iter(slots))
            slots[first_key] = f"{slots[first_key]}_wrong"
        else:
            slots["missing"] = "wrong"
        return _replace_contract(contract, slots=slots, safety={**contract.safety, "reason": "wrong_slot"})
    if category == "decomposed_search_slots":
        decomposed = _decomposed_search_slots_negative(contract)
        if decomposed is None:
            raise ValueError("decomposed_search_slots applies only to compact public-readonly weather search")
        return decomposed
    if category == "extract_search_fallback":
        search_fallback = _extract_search_fallback_negative(contract)
        if search_fallback is None:
            raise ValueError("extract_search_fallback applies only to public-readonly extract_page target contracts")
        return search_fallback
    if category == "extract_query_slot":
        query_slot = _extract_query_slot_negative(contract)
        if query_slot is None:
            raise ValueError("extract_query_slot applies only to public-readonly extract_page target contracts")
        return query_slot
    if category == "extract_generic_price_wording":
        generic_price = _extract_generic_price_wording_negative(contract)
        if generic_price is None:
            raise ValueError("extract_generic_price_wording applies only to canonical public extract-price contracts")
        return generic_price
    if category == "extract_listed_price_wording":
        listed_price = _extract_listed_price_wording_negative(contract)
        if listed_price is None:
            raise ValueError("extract_listed_price_wording applies only to canonical public extract-price contracts")
        return listed_price
    if category == "extract_extra_particle_wording":
        extra_particle = _extract_extra_particle_wording_negative(contract)
        if extra_particle is None:
            raise ValueError("extract_extra_particle_wording applies only to canonical public extract-price contracts")
        return extra_particle
    if category == "clarify_action_drift":
        clarify_drift = _clarify_action_drift_negative(contract)
        if clarify_drift is None:
            raise ValueError("clarify_action_drift applies only to public ambiguous clarify contracts")
        return clarify_drift
    if category == "blocked_payment_action_drift":
        blocked_drift = _blocked_payment_action_drift_negative(contract)
        if blocked_drift is None:
            raise ValueError("blocked_payment_action_drift applies only to public unsafe payment block contracts")
        return blocked_drift
    if category == "form_confirmation_drift":
        form_drift = _form_confirmation_drift_negative(contract)
        if form_drift is None:
            raise ValueError("form_confirmation_drift applies only to confirmation-required public form contracts")
        return form_drift
    if category == "navigate_canonical_url_drift":
        navigate_drift = _navigate_canonical_url_drift_negative(contract)
        if navigate_drift is None:
            raise ValueError("navigate_canonical_url_drift applies only to public canonical navigation contracts")
        return navigate_drift
    if category == "underspecified_request":
        return _replace_contract(
            contract,
            route="clarify",
            confirmation_required=True,
            slots={},
            safety={**contract.safety, "reason": "underspecified_request"},
        )
    if category == "malformed_schema":
        malformed = contract.to_dict()
        malformed.pop("route", None)
        malformed["malformed_reason"] = "route_removed"
        return malformed
    raise ValueError(f"unknown hard-negative category: {category}")


def generate_hard_negative_pairs(rows: list[SFTDatasetRow]) -> list[DPOPair]:
    pairs: list[DPOPair] = []
    for row in rows:
        if row.provenance.get("augmentation") != "original":
            continue
        chosen = as_contract(row.target_contract)
        for category in HARD_NEGATIVE_CATEGORIES:
            if category == "missing_confirmation" and not chosen.confirmation_required:
                continue
            if category == "decomposed_search_slots":
                if row.provenance.get("public_safe") is not True or _decomposed_search_slots_negative(chosen) is None:
                    continue
            if category == "extract_search_fallback":
                if row.provenance.get("public_safe") is not True or _extract_search_fallback_negative(chosen) is None:
                    continue
            if category == "extract_query_slot":
                if row.provenance.get("public_safe") is not True or _extract_query_slot_negative(chosen) is None:
                    continue
            if category == "extract_generic_price_wording":
                if (
                    row.provenance.get("public_safe") is not True
                    or _extract_generic_price_wording_negative(chosen) is None
                ):
                    continue
            if category == "extract_listed_price_wording":
                if (
                    row.provenance.get("public_safe") is not True
                    or _extract_listed_price_wording_negative(chosen) is None
                ):
                    continue
            if category == "extract_extra_particle_wording":
                if (
                    row.provenance.get("public_safe") is not True
                    or _extract_extra_particle_wording_negative(chosen) is None
                ):
                    continue
            if category == "clarify_action_drift":
                if row.provenance.get("public_safe") is not True or _clarify_action_drift_negative(chosen) is None:
                    continue
            if category == "blocked_payment_action_drift":
                if (
                    row.provenance.get("public_safe") is not True
                    or _blocked_payment_action_drift_negative(chosen) is None
                ):
                    continue
            if category == "form_confirmation_drift":
                if row.provenance.get("public_safe") is not True or _form_confirmation_drift_negative(chosen) is None:
                    continue
            if category == "navigate_canonical_url_drift":
                if (
                    row.provenance.get("public_safe") is not True
                    or _navigate_canonical_url_drift_negative(chosen) is None
                ):
                    continue
            pairs.append(
                DPOPair(
                    id=f"{row.id}-{category}",
                    split=row.split,
                    input_text=row.input_text,
                    chosen_contract=chosen,
                    rejected_contract=_negative_contract(chosen, category),
                    rejection_reason=category,
                    provenance={
                        "source_id": row.provenance.get("source_id", row.id),
                        "source_mode": "hard_negative",
                        "public_safe": row.provenance.get("public_safe", False),
                    },
                )
            )
    return pairs


def _split_counts(rows: list[SFTDatasetRow]) -> dict[str, int]:
    counts = Counter(row.split for row in rows)
    return {split: counts.get(split, 0) for split in ("train", "dev", "test")}


def _rejection_counts(pairs: list[DPOPair]) -> dict[str, int]:
    counts = Counter(pair.rejection_reason for pair in pairs)
    return {category: counts.get(category, 0) for category in HARD_NEGATIVE_CATEGORIES}


def _write_manifest(path: Path, manifest: DatasetManifest) -> None:
    write_json(path, manifest.to_dict())


def _safe_artifact_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def _contract(
    *,
    task_type: str,
    route: str,
    safety_reason: str,
    allow: bool,
    confirmation_required: bool,
    slots: dict[str, Any],
    normalized_command: str,
) -> dict[str, Any]:
    contract = {
        "task_type": task_type,
        "route": route,
        "safety": {"allow": allow, "reason": safety_reason},
        "confirmation_required": confirmation_required,
        "slots": slots,
        "normalized_command": normalized_command,
        "language": "zh-CN",
        "contract_version": "v1",
    }
    as_contract(contract)
    return contract


def _family_case(
    *,
    family_id: str,
    split: str,
    index: int,
    input_text: str,
    target_contract: dict[str, Any],
    augmentations: list[str],
) -> dict[str, Any]:
    return {
        "id": f"family-{family_id}-{split}-{index}",
        "split": split,
        "input_text": input_text,
        "target_contract": target_contract,
        "augmentations": augmentations,
    }


def _field_contract(field: str) -> dict[str, Any]:
    return _contract(
        task_type="form_fill",
        route="fill_form",
        allow=True,
        safety_reason="requires_confirmation",
        confirmation_required=True,
        slots={"field": field},
        normalized_command=f"填写{field}并确认",
    )


def _search_contract(query: str) -> dict[str, Any]:
    return _contract(
        task_type="search",
        route="search_web",
        allow=True,
        safety_reason="public_readonly",
        confirmation_required=False,
        slots={"query": query},
        normalized_command=f"搜索{query}",
    )


def _navigation_contract(url: str, normalized_command: str) -> dict[str, Any]:
    return _contract(
        task_type="navigate",
        route="open_url",
        allow=True,
        safety_reason="public_readonly",
        confirmation_required=False,
        slots={"url": url},
        normalized_command=normalized_command,
    )


def _clarify_contract(ambiguity: str) -> dict[str, Any]:
    return _contract(
        task_type="clarify",
        route="clarify",
        allow=True,
        safety_reason="ambiguous_request",
        confirmation_required=True,
        slots={"ambiguity": ambiguity},
        normalized_command="请求澄清目标",
    )


def _extract_contract(target: str) -> dict[str, Any]:
    return _contract(
        task_type="extract",
        route="extract_page",
        allow=True,
        safety_reason="public_readonly",
        confirmation_required=False,
        slots={"target": target},
        normalized_command=f"提取页面{target}",
    )


def _blocked_payment_contract(reason: str, action: str) -> dict[str, Any]:
    return _contract(
        task_type="blocked",
        route="deny",
        allow=False,
        safety_reason="unsafe_payment",
        confirmation_required=True,
        slots={"reason": reason, "action": action},
        normalized_command=f"拒绝代替用户{action}",
    )


def _family_stratified_case_specs() -> list[dict[str, Any]]:
    raw_specs = {
        "search": {
            "train": [
                ("杭州明天天气", "帮我查杭州明天天气", ["查一下杭州明天的天气", "搜索杭州明天会不会下雨"]),
                ("上海周末展览", "搜一下上海周末展览", ["帮我找上海这周末展览", "查上海周末有什么展览"]),
                ("深圳地铁运营时间", "搜索深圳地铁运营时间", ["帮我查深圳地铁几点停运", "搜深圳地铁运营时段"]),
            ],
            "dev": [
                ("成都博物馆开放时间", "查成都博物馆开放时间", ["搜索成都博物馆几点开门", "帮我找成都博物馆开放安排"]),
                ("南京今天空气质量", "帮我搜南京今天空气质量", ["查一下南京空气质量", "搜索南京今日空气情况"]),
                ("苏州园林门票", "搜索苏州园林门票", ["帮我查苏州园林票价", "搜苏州园林门票信息"]),
            ],
            "test": [
                ("厦门轮渡时刻表", "查厦门轮渡时刻表", ["搜索厦门轮渡时间", "帮我找厦门轮渡班次"]),
                ("武汉明天温度", "搜索武汉明天温度", ["查一下武汉明天多少度", "搜武汉明日气温"]),
                ("青岛海边天气", "帮我查青岛海边天气", ["搜索青岛海边天气情况", "查青岛海边今天风大不大"]),
            ],
        },
        "navigation": {
            "train": [
                ("https://docs.example.com", "打开文档站点", "打开 docs.example.com", ["去文档网站", "访问示例文档站"]),
                (
                    "https://status.example.com",
                    "打开状态页面",
                    "打开服务状态页",
                    ["去 status.example.com", "查看示例状态站"],
                ),
                (
                    "https://support.example.com",
                    "打开支持中心",
                    "打开支持中心",
                    ["访问支持页面", "打开 support.example.com"],
                ),
            ],
            "dev": [
                ("https://news.example.com", "打开新闻页面", "打开新闻页面", ["去新闻示例站", "访问 news.example.com"]),
                ("https://shop.example.com", "打开商店首页", "打开商店首页", ["去 shop.example.com", "打开示例商店"]),
                ("https://blog.example.com", "打开博客页面", "打开博客页面", ["访问示例博客", "打开 blog.example.com"]),
            ],
            "test": [
                (
                    "https://learn.example.com",
                    "打开学习页面",
                    "打开学习页面",
                    ["去学习示例站", "访问 learn.example.com"],
                ),
                ("https://map.example.com", "打开地图页面", "打开地图页面", ["打开示例地图", "去 map.example.com"]),
                (
                    "https://events.example.com",
                    "打开活动页面",
                    "打开活动页面",
                    ["访问活动示例站", "打开 events.example.com"],
                ),
            ],
        },
        "clarify": {
            "train": [
                ("目标不明确，未指定具体网站", "帮我打开那个网站", ["去那个网站", "打开刚才说的网站"]),
                ("目标不明确，未指定具体文件", "帮我处理那个文件", ["弄一下那个文件", "打开那个资料"]),
                ("目标不明确，未指定具体商品", "帮我看看那个商品", ["处理一下那个商品", "打开那个东西"]),
            ],
            "dev": [
                ("目标不明确，未指定具体页面", "帮我打开那个页面", ["处理一下那个页面", "去刚才那个页面"]),
                ("目标不明确，未指定具体账号", "帮我切到那个账号", ["用那个账号看看", "切换到刚才说的账号"]),
                ("目标不明确，未指定具体表单", "帮我填那个表单", ["处理那个表格表单", "把那个表单弄一下"]),
            ],
            "test": [
                ("目标不明确，未指定具体城市", "帮我查那个城市", ["搜索刚才那个城市", "看看那个城市的信息"]),
                ("目标不明确，未指定具体订单", "帮我看那个订单", ["处理一下那笔订单", "打开那个订单"]),
                ("目标不明确，未指定具体联系人", "帮我找那个人", ["打开那个联系人", "帮我处理那位联系人"]),
            ],
        },
        "form_fill": {
            "train": [
                ("邮箱", "把邮箱填进表单，提交前问我", ["填写邮箱字段，先别提交", "把电子邮箱放进表单里"]),
                ("昵称", "给表单填昵称，提交前确认", ["填写昵称字段", "把昵称放到网页表单"]),
                ("公司名称", "在表单里填公司名称", ["填写公司名称字段", "把公司名填进去"]),
            ],
            "dev": [
                ("手机号", "把手机号填到网页里", ["填写手机号字段，提交前确认", "把手机号码放进表单"]),
                ("收货地址", "填写收货地址，提交前问我", ["把地址填到表单", "填收货地址但先别提交"]),
                ("发票抬头", "把发票抬头填进去", ["填写发票抬头字段", "在表单里填发票信息"]),
            ],
            "test": [
                ("联系人", "填写联系人，提交前确认", ["把联系人姓名填进去", "在表单里填联系人"]),
                ("邮政编码", "把邮政编码填到表单", ["填写邮编字段", "把邮编放进网页表单"]),
                ("备注", "在备注栏填这段说明", ["填写备注字段", "把备注内容放进去"]),
            ],
        },
        "extract": {
            "train": [
                ("商品价格", "提取这个页面的商品价格", ["帮我看看页面商品多少钱", "把商品价格摘出来"]),
                ("文章标题", "提取页面文章标题", ["把标题摘出来", "看看这篇文章的标题"]),
                ("发布日期", "提取页面发布日期", ["找出页面发布日期", "把发布时间提取出来"]),
            ],
            "dev": [
                ("作者姓名", "提取页面作者姓名", ["找出作者是谁", "把页面作者摘出来"]),
                ("客服电话", "提取页面客服电话", ["找出客服热线", "把联系电话提取出来"]),
                ("优惠信息", "提取页面优惠信息", ["看看页面有什么优惠", "把优惠内容摘出来"]),
            ],
            "test": [
                ("库存状态", "提取页面库存状态", ["看看还有没有库存", "把库存信息提取出来"]),
                ("活动时间", "提取页面活动时间", ["找出活动什么时候开始", "把活动时间摘出来"]),
                ("下载链接", "提取页面下载链接", ["把下载地址找出来", "提取页面里的下载链接"]),
            ],
        },
        "blocked_payment": {
            "train": [
                ("payment_requires_user_control", "付款", "帮我直接付款买这个", ["替我完成付款", "用我的账号支付"]),
                ("transfer_control", "转账", "帮我转账给别人", ["替我把钱转出去", "直接帮我确认转账"]),
                (
                    "purchase_control",
                    "下单付款",
                    "帮我下单并付款",
                    ["直接替我买下来", "用我的账户完成购买"],
                ),
            ],
            "dev": [
                (
                    "refund_control",
                    "退款确认",
                    "帮我确认退款到账户",
                    ["替我提交退款确认", "直接处理这笔退款"],
                ),
                (
                    "subscription_control",
                    "订阅付款",
                    "帮我开通付费订阅",
                    ["直接帮我付订阅费", "替我确认订阅扣款"],
                ),
                (
                    "donation_control",
                    "捐款",
                    "帮我捐款给这个项目",
                    ["直接替我完成捐款", "用我的账户捐一笔"],
                ),
            ],
            "test": [
                (
                    "bid_control",
                    "出价付款",
                    "帮我出价并支付保证金",
                    ["替我提交竞拍付款", "直接帮我付保证金"],
                ),
                ("recharge_control", "充值", "帮我给账户充值", ["直接替我充钱", "用我的账号完成充值"]),
                ("tip_control", "打赏", "帮我给作者打赏", ["替我支付打赏", "直接给这个作者付款"]),
            ],
        },
        "confirmation": {
            "train": [
                ("收货地址", "把收货地址填好，提交前一定问我", ["填地址但不要直接提交", "提交表单前先确认收货地址"]),
                ("实名信息", "填写实名信息，提交前确认", ["把实名资料填进去但先问我", "提交实名信息前等我确认"]),
                ("联系邮箱", "填写联系邮箱，发送前问我", ["把联系邮箱填好先别发", "提交联系邮箱前确认"]),
            ],
            "dev": [
                ("预约时间", "填写预约时间，确认后再提交", ["把预约时间填进去先问我", "提交预约前确认时间"]),
                ("配送方式", "选择配送方式，提交前确认", ["填配送方式但先别提交", "提交配送选项前问我"]),
                ("发票邮箱", "填写发票邮箱，发送前确认", ["把发票邮箱放进去先问我", "提交发票邮箱前确认"]),
            ],
            "test": [
                ("报名信息", "填写报名信息，提交前问我", ["把报名表填好先确认", "提交报名信息前等我确认"]),
                ("退订原因", "填写退订原因，提交前确认", ["把退订原因填进去先别提交", "提交退订表单前问我"]),
                ("收件电话", "填写收件电话，保存前确认", ["把收件电话填好先问我", "保存电话前等我确认"]),
            ],
        },
    }

    specs: list[dict[str, Any]] = []
    for family_id, by_split in raw_specs.items():
        for split, cases in by_split.items():
            for index, case in enumerate(cases, start=1):
                if family_id == "search":
                    query, input_text, augmentations = case
                    target_contract = _search_contract(query)
                elif family_id == "navigation":
                    url, normalized_command, input_text, augmentations = case
                    target_contract = _navigation_contract(url, normalized_command)
                elif family_id == "clarify":
                    ambiguity, input_text, augmentations = case
                    target_contract = _clarify_contract(ambiguity)
                elif family_id in {"form_fill", "confirmation"}:
                    field, input_text, augmentations = case
                    target_contract = _field_contract(field)
                elif family_id == "extract":
                    target, input_text, augmentations = case
                    target_contract = _extract_contract(target)
                elif family_id == "blocked_payment":
                    reason, action, input_text, augmentations = case
                    target_contract = _blocked_payment_contract(reason, action)
                else:
                    raise AssertionError(f"unhandled family: {family_id}")
                specs.append(
                    _family_case(
                        family_id=family_id,
                        split=split,
                        index=index,
                        input_text=input_text,
                        target_contract=target_contract,
                        augmentations=list(augmentations),
                    )
                )
    return specs


def _family_stratified_candidate_seed_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in _family_stratified_case_specs():
        family_id = spec["id"].split("-")[1]
        row = {
            **spec,
            "provenance": {
                "source_mode": "family_stratified_generalization_candidate_seed",
                "public_safe": True,
                "candidate_status": "standalone_not_formal_public_sample",
                "family_id": family_id,
                "split_role": spec["split"],
                "family_stratification": True,
            },
        }
        validate_public_record(row)
        rows.append(row)
    return rows


def _family_stratified_sft_rows(seed_rows: list[dict[str, Any]]) -> list[SFTDatasetRow]:
    rows: list[SFTDatasetRow] = []
    for seed in seed_rows:
        seed_provenance = seed["provenance"]
        base_provenance = {
            "source_id": seed["id"],
            "source_mode": "family_stratified_generalization_candidate",
            "public_safe": True,
            "augmentation": "original",
            "candidate_status": seed_provenance["candidate_status"],
            "family_id": seed_provenance["family_id"],
            "split_role": seed_provenance["split_role"],
            "family_stratification": True,
        }
        base = SFTDatasetRow(
            id=seed["id"],
            split=seed["split"],
            input_text=seed["input_text"],
            target_contract=seed["target_contract"],
            provenance=base_provenance,
        )
        rows.append(base)
        for index, paraphrase in enumerate(seed.get("augmentations", []), start=1):
            rows.append(
                SFTDatasetRow(
                    id=f"{seed['id']}-aug-{index}",
                    split=seed["split"],
                    input_text=paraphrase,
                    target_contract=base.target_contract,
                    provenance={
                        **base_provenance,
                        "source_mode": "schema_preserving_augmentation",
                        "augmentation": f"paraphrase-{index}",
                    },
                )
            )
    return rows


def _family_split_counts(seed_rows: list[dict[str, Any]], sft_rows: list[SFTDatasetRow]) -> dict[str, Any]:
    seed_counts: dict[str, dict[str, int]] = {}
    sft_counts: dict[str, dict[str, int]] = {}
    families = sorted({row["provenance"]["family_id"] for row in seed_rows})
    for family in families:
        seed_counts[family] = {split: 0 for split in ("train", "dev", "test")}
        sft_counts[family] = {split: 0 for split in ("train", "dev", "test")}
    for row in seed_rows:
        seed_counts[row["provenance"]["family_id"]][row["split"]] += 1
    for row in sft_rows:
        sft_counts[row.provenance["family_id"]][row.split] += 1
    return {"seed": seed_counts, "sft": sft_counts}


def _family_slot_signatures(seed_rows: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    signatures: dict[str, dict[str, set[str]]] = {}
    for row in seed_rows:
        family = row["provenance"]["family_id"]
        split = row["split"]
        signatures.setdefault(family, {name: set() for name in ("train", "dev", "test")})
        signatures[family][split].add(json_dumps(row["target_contract"]["slots"]))
    return {
        family: {split: sorted(values) for split, values in by_split.items()}
        for family, by_split in sorted(signatures.items())
    }


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _family_stratified_summary(
    *,
    candidate_seed_rows: list[dict[str, Any]],
    candidate_sft_rows: list[SFTDatasetRow],
    formal_public_manifest: dict[str, Any],
) -> dict[str, Any]:
    formal_counts = formal_public_manifest["counts"]
    split_counts = _split_counts(candidate_sft_rows)
    return {
        "family_count": len({row["provenance"]["family_id"] for row in candidate_seed_rows}),
        "families": sorted({row["provenance"]["family_id"] for row in candidate_seed_rows}),
        "candidate_seed_rows": len(candidate_seed_rows),
        "candidate_sft_rows": len(candidate_sft_rows),
        "split_counts": split_counts,
        "seed_split_counts": {
            split: sum(1 for row in candidate_seed_rows if row["split"] == split)
            for split in ("train", "dev", "test")
        },
        "family_split_counts": _family_split_counts(candidate_seed_rows, candidate_sft_rows),
        "family_slot_signatures": _family_slot_signatures(candidate_seed_rows),
        "formal_public_sample_seed_rows": formal_counts["seed_rows"],
        "formal_public_sample_sft_rows": formal_counts["sft_rows"],
        "formal_public_sample_dpo_pairs": formal_counts["dpo_pairs"],
        "formal_public_sample_modified": False,
        "recommended_next_step": "review_candidate_dataset_before_merge_or_training",
    }


def materialize_family_stratified_generalization_candidates(
    *,
    seed_output_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Write standalone family-stratified candidate data without mutating the formal public sample."""

    formal_public_manifest = read_json(FORMAL_PUBLIC_MANIFEST_PATH)
    candidate_seed_rows = _family_stratified_candidate_seed_rows()
    candidate_sft_rows = _family_stratified_sft_rows(candidate_seed_rows)
    for row in candidate_sft_rows:
        validate_public_record(row.to_dict())

    write_jsonl(seed_output_path, candidate_seed_rows)
    summary = _family_stratified_summary(
        candidate_seed_rows=candidate_seed_rows,
        candidate_sft_rows=candidate_sft_rows,
        formal_public_manifest=formal_public_manifest,
    )
    evidence = {
        "evidence_kind": "family_stratified_generalization_candidates",
        "materialization_status": "candidate_dataset_materialized",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "execution_scope": {
            "local_public_sample_only": True,
            "new_candidate_data_generated": True,
            "formal_public_sample_modified": False,
            "training_run": False,
            "prediction_run": False,
            "dpo_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
        },
        "claims": {
            "contract_exact_match_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_generalization_recovered": False,
            "model_recovery_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
        "artifact_files": {
            "candidate_seed": _safe_artifact_ref(seed_output_path),
            "candidate_sft": "sft_candidate_rows.jsonl",
            "materialization_json": "family_stratified_generalization.json",
            "materialization_markdown": "family_stratified_generalization.md",
            "manifest": "manifest.json",
        },
    }

    from voice2task.reports import write_family_stratified_generalization_report

    paths = write_family_stratified_generalization_report(
        evidence,
        output_dir=output_dir,
        sft_rows=[row.to_dict() for row in candidate_sft_rows],
    )
    return {"seed": seed_output_path, **paths}


def _formal_slot_value_candidate_seed(row: dict[str, Any], candidate_seed_path: Path) -> dict[str, Any]:
    provenance = dict(row.get("provenance") or {})
    if provenance.get("candidate_status") not in {None, "standalone_not_formal_public_sample"}:
        raise ValueError(f"candidate seed already has unsupported status: {row.get('id')}")
    merged = dict(row)
    merged["split"] = "train"
    merged["provenance"] = {
        **provenance,
        "source_mode": "slot_value_generalization_formal_public_seed",
        "public_safe": True,
        "candidate_status": "formal_public_sample",
        "merged_from_candidate_seed": _safe_artifact_ref(candidate_seed_path),
    }
    validate_public_record(merged)
    return merged


def _slot_value_candidate_seed_count(seed_rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in seed_rows
        if (row.get("provenance") or {}).get("source_mode") == "slot_value_generalization_formal_public_seed"
    )


def _is_formal_family_stratified_seed(row: dict[str, Any]) -> bool:
    provenance = row.get("provenance") or {}
    return provenance.get("source_mode") == "family_stratified_generalization_formal_public_seed"


def _family_stratified_candidate_seed_count(seed_rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in seed_rows if _is_formal_family_stratified_seed(row))


def _family_stratified_formal_seed_split_counts(seed_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["split"] for row in seed_rows if _is_formal_family_stratified_seed(row))
    return {split: counts.get(split, 0) for split in ("train", "dev", "test")}


def _family_stratified_formal_families(seed_rows: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str((row.get("provenance") or {}).get("family_id"))
            for row in seed_rows
            if _is_formal_family_stratified_seed(row)
        }
    )


def _family_stratified_formal_sft_count(rows: list[SFTDatasetRow]) -> int:
    return sum(
        1
        for row in rows
        if row.provenance.get("source_mode") in {
            "family_stratified_generalization_formal_public_seed",
            "schema_preserving_augmentation",
        }
        and row.provenance.get("family_stratification") is True
        and row.provenance.get("candidate_status") == "formal_public_sample"
    )


def _formal_family_stratified_candidate_seed(row: dict[str, Any], candidate_seed_path: Path) -> dict[str, Any]:
    provenance = dict(row.get("provenance") or {})
    if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
        raise ValueError(f"family-stratified candidate seed already has unsupported status: {row.get('id')}")
    merged = dict(row)
    merged["provenance"] = {
        **provenance,
        "source_mode": "family_stratified_generalization_formal_public_seed",
        "public_safe": True,
        "candidate_status": "formal_public_sample",
        "split_role": row["split"],
        "family_stratification": True,
        "merged_from_candidate_seed": _safe_artifact_ref(candidate_seed_path),
    }
    validate_public_record(merged)
    return merged


def _validate_reviewed_family_stratified_candidate_seed_rows(candidate_seed_rows: list[dict[str, Any]]) -> None:
    expected_ids = {spec["id"] for spec in _family_stratified_case_specs()}
    observed_ids = {str(row.get("id")) for row in candidate_seed_rows}
    if observed_ids != expected_ids:
        expected = ", ".join(sorted(expected_ids))
        observed = ", ".join(sorted(observed_ids))
        raise ValueError(
            "expected reviewed family-stratified candidate seed IDs "
            f"[{expected}], observed [{observed}]"
        )
    if len(candidate_seed_rows) != len(expected_ids):
        raise ValueError("expected exactly one row per reviewed family-stratified candidate seed ID")

    expected_families = {"blocked_payment", "clarify", "confirmation", "extract", "form_fill", "navigation", "search"}
    observed_families: set[str] = set()
    split_counts: dict[tuple[str, str], int] = Counter()
    for row in candidate_seed_rows:
        provenance_raw = row.get("provenance")
        provenance = provenance_raw if isinstance(provenance_raw, dict) else {}
        family = provenance.get("family_id")
        split = row.get("split")
        observed_families.add(str(family))
        split_counts[(str(family), str(split))] += 1
        if split not in {"train", "dev", "test"}:
            raise ValueError("family-stratified candidate seeds must use train/dev/test splits")
        if provenance.get("source_mode") != "family_stratified_generalization_candidate_seed":
            raise ValueError("reviewed family-stratified candidate seeds must preserve source_mode provenance")
        if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
            raise ValueError("reviewed family-stratified candidate seeds must originate from standalone status")
        if provenance.get("public_safe") is not True:
            raise ValueError("reviewed family-stratified candidate seeds must be public_safe")
        if provenance.get("family_stratification") is not True:
            raise ValueError("reviewed family-stratified candidate seeds must be family_stratification=true")
        if provenance.get("split_role") != split:
            raise ValueError("reviewed family-stratified candidate split_role must match split")

    if observed_families != expected_families:
        raise ValueError("reviewed family-stratified candidate seeds must cover the expected family set")
    missing_split_cells = [
        f"{family}:{split}"
        for family in sorted(expected_families)
        for split in ("train", "dev", "test")
        if split_counts[(family, split)] != 3
    ]
    if missing_split_cells:
        raise ValueError(f"reviewed family-stratified candidate seeds have invalid split cells: {missing_split_cells}")


def _validate_reviewed_slot_value_candidate_seed_rows(candidate_seed_rows: list[dict[str, Any]]) -> None:
    observed_ids = {str(row.get("id")) for row in candidate_seed_rows}
    if observed_ids != EXPECTED_FORMAL_SLOT_VALUE_CANDIDATE_IDS:
        expected = ", ".join(sorted(EXPECTED_FORMAL_SLOT_VALUE_CANDIDATE_IDS))
        observed = ", ".join(sorted(observed_ids))
        raise ValueError(
            "expected reviewed slot-value candidate seed IDs "
            f"[{expected}], observed [{observed}]"
        )
    if len(candidate_seed_rows) != len(EXPECTED_FORMAL_SLOT_VALUE_CANDIDATE_IDS):
        raise ValueError("expected exactly one row per reviewed slot-value candidate seed ID")

    for row in candidate_seed_rows:
        provenance_raw = row.get("provenance")
        provenance = provenance_raw if isinstance(provenance_raw, dict) else {}
        if row.get("split") != "train":
            raise ValueError("reviewed slot-value candidate seeds must stay in train split")
        if provenance.get("source_mode") != "slot_value_generalization_candidate_seed":
            raise ValueError("reviewed slot-value candidate seeds must preserve source_mode provenance")
        if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
            raise ValueError("reviewed slot-value candidate seeds must originate from standalone candidate status")
        if provenance.get("public_safe") is not True:
            raise ValueError("reviewed slot-value candidate seeds must be public_safe")


def _require_reviewed_slot_value_case_groups(case_design: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if case_design.get("evidence_kind") != "slot_value_generalization_case_design":
        raise ValueError("case design must be slot_value_generalization_case_design evidence")
    if case_design.get("design_status") != "design_only_not_materialized":
        raise ValueError("case design must be design_only_not_materialized before candidate materialization")

    groups = {
        str(group.get("case_group_id")): group
        for group in case_design.get("candidate_case_groups", [])
        if isinstance(group, dict)
    }
    required = set(_SLOT_VALUE_CANDIDATE_CASES)
    missing = sorted(required - set(groups))
    extra = sorted(set(groups) - required)
    if missing:
        raise ValueError(f"missing reviewed case groups: {', '.join(missing)}")
    if extra:
        raise ValueError(f"unreviewed case groups are not materialized in this phase: {', '.join(extra)}")
    return groups


def _slot_value_candidate_seed_rows(
    case_design: dict[str, Any],
    source_design_ref: str,
) -> list[dict[str, Any]]:
    groups = _require_reviewed_slot_value_case_groups(case_design)
    rows: list[dict[str, Any]] = []
    for case_group_id in sorted(_SLOT_VALUE_CANDIDATE_CASES):
        group = groups[case_group_id]
        template = _SLOT_VALUE_CANDIDATE_CASES[case_group_id]
        target_contract = dict(template["target_contract"])
        as_contract(target_contract)
        row = {
            "id": template["id"],
            "split": template["split"],
            "input_text": template["input_text"],
            "target_contract": target_contract,
            "augmentations": list(template["augmentations"]),
            "provenance": {
                "source_mode": "slot_value_generalization_candidate_seed",
                "public_safe": True,
                "candidate_status": "standalone_not_formal_public_sample",
                "source_case_group_id": case_group_id,
                "source_design": source_design_ref,
                "source_family_id": group["source_family_id"],
                "residual_bucket": group["residual_bucket"],
                "affected_field_paths": list(group["affected_field_paths"]),
                "canonical_gold_values": list(group["canonical_gold_values"]),
            },
        }
        validate_public_record(row)
        rows.append(row)
    return rows


def _slot_value_candidate_sft_rows(seed_rows: list[dict[str, Any]]) -> list[SFTDatasetRow]:
    rows: list[SFTDatasetRow] = []
    for seed in seed_rows:
        seed_provenance = seed["provenance"]
        base_provenance = {
            "source_id": seed["id"],
            "source_mode": "slot_value_generalization_candidate",
            "public_safe": True,
            "augmentation": "original",
            "candidate_status": seed_provenance["candidate_status"],
            "source_case_group_id": seed_provenance["source_case_group_id"],
            "source_design": seed_provenance["source_design"],
            "source_family_id": seed_provenance["source_family_id"],
            "residual_bucket": seed_provenance["residual_bucket"],
        }
        base = SFTDatasetRow(
            id=seed["id"],
            split=seed["split"],
            input_text=seed["input_text"],
            target_contract=seed["target_contract"],
            provenance=base_provenance,
        )
        rows.append(base)
        for index, paraphrase in enumerate(seed.get("augmentations", []), start=1):
            rows.append(
                SFTDatasetRow(
                    id=f"{seed['id']}-aug-{index}",
                    split=seed["split"],
                    input_text=paraphrase,
                    target_contract=base.target_contract,
                    provenance={
                        **base_provenance,
                        "source_mode": "schema_preserving_augmentation",
                        "augmentation": f"paraphrase-{index}",
                    },
                )
            )
    return rows


def _slot_value_materialization_summary(
    *,
    candidate_seed_rows: list[dict[str, Any]],
    candidate_sft_rows: list[SFTDatasetRow],
    formal_public_manifest: dict[str, Any],
) -> dict[str, Any]:
    formal_counts = formal_public_manifest["counts"]
    formal_source_summary = formal_public_manifest.get("source_summary", {})
    return {
        "candidate_group_count": len(_SLOT_VALUE_CANDIDATE_CASES),
        "candidate_seed_rows": len(candidate_seed_rows),
        "candidate_sft_rows": len(candidate_sft_rows),
        "formal_public_sample_seed_rows": formal_counts["seed_rows"],
        "formal_public_sample_sft_rows": formal_counts["sft_rows"],
        "formal_public_sample_dpo_pairs": formal_counts["dpo_pairs"],
        "formal_public_sample_has_slot_value_candidates": bool(
            formal_source_summary.get("slot_value_candidates_formal_public_sample")
        ),
        "public_sample_modified": False,
        "recommended_next_step": "decide_candidate_merge_or_local_sft_probe",
    }


def materialize_slot_value_generalization_candidates(
    *,
    case_design_path: Path,
    seed_output_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Write standalone candidate data from the reviewed slot-value case design."""

    case_design = read_json(case_design_path)
    formal_public_manifest = read_json(FORMAL_PUBLIC_MANIFEST_PATH)
    source_design_ref = _safe_artifact_ref(case_design_path)
    candidate_seed_rows = _slot_value_candidate_seed_rows(case_design, source_design_ref)
    candidate_sft_rows = _slot_value_candidate_sft_rows(candidate_seed_rows)
    for row in candidate_sft_rows:
        validate_public_record(row.to_dict())

    write_jsonl(seed_output_path, candidate_seed_rows)
    materialization = {
        "evidence_kind": "slot_value_generalization_materialization",
        "materialization_status": "candidate_dataset_materialized",
        "source_case_design": {
            "path": source_design_ref,
            "evidence_kind": case_design["evidence_kind"],
            "design_status": case_design["design_status"],
            "summary": case_design["summary"],
        },
        "summary": _slot_value_materialization_summary(
            candidate_seed_rows=candidate_seed_rows,
            candidate_sft_rows=candidate_sft_rows,
            formal_public_manifest=formal_public_manifest,
        ),
        "execution_scope": {
            "local_public_sample_only": True,
            "new_candidate_data_generated": True,
            "public_sample_modified": False,
            "training_run": False,
            "prediction_run": False,
            "dpo_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_generalization_recovered": False,
            "model_recovery_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "live_browser_benchmark_claim": False,
        },
        "candidate_case_groups": [
            {
                "case_group_id": seed["provenance"]["source_case_group_id"],
                "candidate_seed_id": seed["id"],
                "candidate_sft_row_ids": [
                    row.id for row in candidate_sft_rows if row.provenance["source_id"] == seed["id"]
                ],
                "source_family_id": seed["provenance"]["source_family_id"],
                "residual_bucket": seed["provenance"]["residual_bucket"],
                "affected_field_paths": seed["provenance"]["affected_field_paths"],
                "canonical_gold_values": seed["provenance"]["canonical_gold_values"],
            }
            for seed in candidate_seed_rows
        ],
        "artifact_files": {
            "candidate_seed": _safe_artifact_ref(seed_output_path),
            "candidate_sft": "sft_candidate_rows.jsonl",
            "materialization_json": "slot_value_generalization_materialization.json",
            "materialization_markdown": "slot_value_generalization_materialization.md",
            "manifest": "manifest.json",
        },
    }

    from voice2task.reports import write_slot_value_generalization_materialization_report

    paths = write_slot_value_generalization_materialization_report(
        materialization,
        output_dir=output_dir,
        sft_rows=[row.to_dict() for row in candidate_sft_rows],
    )
    return {"seed": seed_output_path, **paths}


def build_public_sample_dataset(seed_path: Path, output_dir: Path) -> DatasetManifest:
    seed_rows = _read_seed_rows(seed_path)
    rows = expand_sft_rows(seed_rows, public_safe=True)
    pairs = generate_hard_negative_pairs(rows)
    for row in rows:
        validate_public_record(row.to_dict())
    for pair in pairs:
        validate_public_record(pair.to_dict())

    sft_path = output_dir / "sft_public_sample.jsonl"
    dpo_path = output_dir / "dpo_public_sample.jsonl"
    manifest_path = output_dir / "manifest_public_sample.json"
    write_jsonl(sft_path, [row.to_dict() for row in rows])
    write_jsonl(dpo_path, [pair.to_dict() for pair in pairs])

    candidate_seed_count = _slot_value_candidate_seed_count(seed_rows)
    family_seed_count = _family_stratified_candidate_seed_count(seed_rows)
    source_summary: dict[str, Any] = {
        "seed_rows": len(seed_rows),
        "source": "sanitized_public_seed_fixture",
    }
    if candidate_seed_count:
        source_summary.update(
            {
                "slot_value_candidate_seed_rows": candidate_seed_count,
                "slot_value_candidates_formal_public_sample": True,
            }
        )
    if family_seed_count:
        source_summary.update(
            {
                "family_stratified_candidate_seed_rows": family_seed_count,
                "family_stratified_candidate_sft_rows": _family_stratified_formal_sft_count(rows),
                "family_stratified_candidates_formal_public_sample": True,
                "family_stratified_families": _family_stratified_formal_families(seed_rows),
                "family_stratified_seed_split_counts": _family_stratified_formal_seed_split_counts(seed_rows),
            }
        )

    manifest = DatasetManifest(
        manifest_id=_now_id("public-sample"),
        mode="public_sample",
        generated_at=datetime.now(timezone.utc).isoformat(),
        files={
            "seed": seed_path.as_posix(),
            "sft": sft_path.as_posix(),
            "dpo": dpo_path.as_posix(),
            "manifest": manifest_path.as_posix(),
        },
        counts={"seed_rows": len(seed_rows), "sft_rows": len(rows), "dpo_pairs": len(pairs)},
        split_counts=_split_counts(rows),
        dpo_rejection_counts=_rejection_counts(pairs),
        source_summary=source_summary,
        public_safe=True,
    )
    _write_manifest(manifest_path, manifest)
    return manifest


def merge_slot_value_candidates_into_public_sample(
    *,
    candidate_seed_path: Path,
    seed_path: Path,
    output_dir: Path,
) -> DatasetManifest:
    """Merge reviewed slot-value candidate seeds into the formal public sample."""

    seed_rows = _read_seed_rows(seed_path)
    candidate_seed_rows = read_jsonl(candidate_seed_path)
    _validate_reviewed_slot_value_candidate_seed_rows(candidate_seed_rows)
    existing_ids = {str(row["id"]) for row in seed_rows}
    duplicate_ids = sorted(str(row["id"]) for row in candidate_seed_rows if str(row["id"]) in existing_ids)
    if duplicate_ids:
        raise ValueError(f"candidate seed IDs already exist in public sample: {', '.join(duplicate_ids)}")

    merged_candidates = [
        _formal_slot_value_candidate_seed(row, candidate_seed_path=candidate_seed_path) for row in candidate_seed_rows
    ]
    for row in merged_candidates:
        as_contract(row["target_contract"])

    seed_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(seed_path, [*seed_rows, *merged_candidates])
    return build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)


def merge_family_stratified_candidates_into_public_sample(
    *,
    candidate_seed_path: Path,
    seed_path: Path,
    output_dir: Path,
) -> DatasetManifest:
    """Merge reviewed family-stratified candidate seeds into the formal public sample."""

    seed_rows = _read_seed_rows(seed_path)
    candidate_seed_rows = read_jsonl(candidate_seed_path)
    _validate_reviewed_family_stratified_candidate_seed_rows(candidate_seed_rows)
    existing_ids = {str(row["id"]) for row in seed_rows}
    duplicate_ids = sorted(str(row["id"]) for row in candidate_seed_rows if str(row["id"]) in existing_ids)
    if duplicate_ids:
        raise ValueError(
            "family-stratified candidate seed IDs already exist in public sample: "
            f"{', '.join(duplicate_ids)}"
        )

    merged_candidates = [
        _formal_family_stratified_candidate_seed(row, candidate_seed_path=candidate_seed_path)
        for row in candidate_seed_rows
    ]
    for row in merged_candidates:
        as_contract(row["target_contract"])

    seed_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(seed_path, [*seed_rows, *merged_candidates])
    return build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)


def family_stratified_public_sample_merge_evidence(
    *,
    manifest: DatasetManifest,
    candidate_seed_path: Path,
) -> dict[str, Any]:
    source_summary = manifest.source_summary
    return {
        "evidence_kind": "family_stratified_public_sample_merge",
        "merge_status": "formal_public_sample_rebuilt",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "formal_public_sample_counts": manifest.counts,
        "formal_public_sample_split_counts": manifest.split_counts,
        "source_summary": source_summary,
        "candidate_source": {
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "candidate_seed_rows": source_summary.get("family_stratified_candidate_seed_rows", 0),
            "candidate_sft_rows": source_summary.get("family_stratified_candidate_sft_rows", 0),
            "families": source_summary.get("family_stratified_families", []),
            "seed_split_counts": source_summary.get("family_stratified_seed_split_counts", {}),
        },
        "execution_scope": {
            "formal_public_sample_modified": True,
            "sft_artifacts_rebuilt": True,
            "dpo_artifacts_rebuilt": True,
            "training_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_generalization_recovered": False,
            "model_recovery_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
        "artifact_files": {
            "seed": manifest.files["seed"],
            "sft": manifest.files["sft"],
            "dpo": manifest.files["dpo"],
            "manifest": manifest.files["manifest"],
            "merge_json": "family_stratified_public_sample_merge.json",
            "merge_markdown": "family_stratified_public_sample_merge.md",
            "merge_manifest": "manifest.json",
        },
        "recommended_next_step": "run_prediction_only_eval_against_the_new_manifest_in_a_later_phase",
    }


def build_local_private_corpus(seed_trace_path: Path, output_dir: Path) -> DatasetManifest:
    seed_rows = _read_seed_rows(seed_trace_path)
    rows = expand_sft_rows(seed_rows, public_safe=False)
    pairs = generate_hard_negative_pairs(rows)

    split_files: dict[str, str] = {}
    for split in ("train", "dev", "test"):
        path = output_dir / f"{split}.jsonl"
        write_jsonl(path, [row.to_dict() for row in rows if row.split == split])
        split_files[split] = path.as_posix()
    dpo_path = output_dir / "dpo_pairs.jsonl"
    manifest_path = output_dir / "manifest_local_private.json"
    write_jsonl(dpo_path, [pair.to_dict() for pair in pairs])

    manifest = DatasetManifest(
        manifest_id=_now_id("local-private"),
        mode="local_private",
        generated_at=datetime.now(timezone.utc).isoformat(),
        files={**split_files, "dpo": dpo_path.as_posix(), "manifest": manifest_path.as_posix()},
        counts={"seed_rows": len(seed_rows), "sft_rows": len(rows), "dpo_pairs": len(pairs)},
        split_counts=_split_counts(rows),
        dpo_rejection_counts=_rejection_counts(pairs),
        source_summary={
            "seed_rows": len(seed_rows),
            "source": "configured_voice_to_browser_agent_seed_trace_path",
            "raw_rows_committed": 0,
        },
        public_safe=False,
    )
    _write_manifest(manifest_path, manifest)
    return manifest
