from __future__ import annotations

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
        if (row.get("provenance") or {}).get("candidate_status") == "formal_public_sample"
        or (row.get("provenance") or {}).get("source_mode") == "slot_value_generalization_formal_public_seed"
    )


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
