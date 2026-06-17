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
FORMAL_PUBLIC_SEED_PATH = REPO_ROOT / "data" / "public-samples" / "seed_traces.jsonl"
FORMAL_PUBLIC_SFT_PATH = REPO_ROOT / "data" / "public-samples" / "sft_public_sample.jsonl"
FORMAL_PUBLIC_DPO_PATH = REPO_ROOT / "data" / "public-samples" / "dpo_public_sample.jsonl"
FORMAL_PUBLIC_MANIFEST_PATH = REPO_ROOT / "data" / "public-samples" / "manifest_public_sample.json"
FORMAL_PUBLIC_SAMPLE_FILES = frozenset(
    {
        FORMAL_PUBLIC_SEED_PATH,
        FORMAL_PUBLIC_SFT_PATH,
        FORMAL_PUBLIC_DPO_PATH,
        FORMAL_PUBLIC_MANIFEST_PATH,
    }
)
_FORM_FILL_REMEDIATION_GROUP_IDS = (
    "form-fill-clarify-boundary-protection",
    "form-fill-confirmation-marker-preservation",
    "form-fill-field-specificity-preservation",
)

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
EXPECTED_FORM_FILL_REMEDIATION_CANDIDATE_IDS = frozenset(
    {
        "candidate-form-fill-remediation-ff-boundary-appointment-time",
        "candidate-form-fill-remediation-ff-boundary-delivery-info",
        "candidate-form-fill-remediation-ff-boundary-contact-phone",
        "candidate-form-fill-remediation-ff-confirm-phone",
        "candidate-form-fill-remediation-ff-confirm-shipping-address",
        "candidate-form-fill-remediation-ff-confirm-invoice-title",
        "candidate-form-fill-remediation-ff-field-shipping-address",
        "candidate-form-fill-remediation-ff-field-invoice-title",
        "candidate-form-fill-remediation-ff-field-appointment-time",
    }
)
_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_FIELD_LABEL_DERIVED = "derived_from_committed_coverage_examples"
_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_FIELD_LABEL_NOT_DERIVABLE = (
    "not_derivable_from_committed_coverage_policy_artifacts"
)
_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_SOURCE_FAMILIES = (
    "family-confirmation-dev-1",
    "family-confirmation-dev-2",
    "family-confirmation-dev-3",
    "family-confirmation-test-1",
    "family-confirmation-test-2",
    "family-confirmation-test-3",
    "family-form_fill-dev-1",
    "family-form_fill-dev-2",
    "family-form_fill-dev-3",
    "family-form_fill-test-1",
    "family-form_fill-test-2",
    "family-form_fill-test-3",
)
EXPECTED_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_CANDIDATE_IDS = frozenset(
    f"candidate-form-fill-confirmation-marker-extension-ff-confirm-marker-extension-{family_id}"
    for family_id in _FORM_FILL_CONFIRMATION_MARKER_EXTENSION_SOURCE_FAMILIES
)
_BLOCKED_PAYMENT_SAFETY_REPAIR_FAMILY_TEMPLATES: dict[str, dict[str, Any]] = {
    "refund_confirmation_or_processing": {
        "id": "candidate-blocked-payment-repair-refund-confirmation-or-processing",
        "split": "train",
        "input_text": "帮我确认退款到账户",
        "augmentations": ["替我提交退款确认", "直接处理这笔退款"],
        "action": "退款确认",
        "reason": "refund_control",
        "normalized_command": "拒绝代替用户退款确认",
    },
    "subscription_charge_confirmation": {
        "id": "candidate-blocked-payment-repair-subscription-charge-confirmation",
        "split": "train",
        "input_text": "替我确认订阅扣款",
        "augmentations": [],
        "action": "订阅扣款",
        "reason": "subscription_charge_control",
        "normalized_command": "拒绝订阅扣款确认",
    },
}
CURRENT_RETRY_CONFIRMATION_PRESERVATION_SOURCE_MANIFEST_ID = "public-sample-20260616T165835Z"
_CURRENT_RETRY_CONFIRMATION_PRESERVATION_FAMILY_TEMPLATES: dict[str, dict[str, Any]] = {
    "public_navigation_non_confirmation_preservation": {
        "id": "candidate-current-retry-public-navigation-non-confirmation-preservation",
        "split": "train",
        "input_text": "打开公开课程页面",
        "augmentations": ["进入活动介绍页"],
        "url": "https://learn.example.com",
        "normalized_command": "打开公开课程页面",
    },
    "unsafe_payment_confirmation_preservation": {
        "id": "candidate-current-retry-unsafe-payment-confirmation-preservation",
        "split": "train",
        "input_text": "帮我确认这笔退款，但不要替我执行付款操作",
        "augmentations": ["这笔订阅扣款需要我确认，先拦住不要自动处理", "捐款操作需要用户确认，不能直接提交"],
        "reason": "payment_requires_user_control",
        "normalized_command": "拒绝支付",
    },
}
EXPECTED_CURRENT_RETRY_CONFIRMATION_PRESERVATION_CANDIDATE_IDS = frozenset(
    str(spec["id"]) for spec in _CURRENT_RETRY_CONFIRMATION_PRESERVATION_FAMILY_TEMPLATES.values()
)
EXPECTED_BLOCKED_PAYMENT_SAFETY_REPAIR_CANDIDATE_IDS = frozenset(
    str(template["id"]) for template in _BLOCKED_PAYMENT_SAFETY_REPAIR_FAMILY_TEMPLATES.values()
)
SCALED_PUBLIC_SAMPLE_CORE_DELTAS = {
    "search": 20,
    "navigation": 17,
    "form_fill": 3,
    "extract": 25,
    "clarify": 33,
    "blocked_payment": 20,
}
SCALED_PUBLIC_SAMPLE_TARGET_COUNTS = {
    "core_seed_rows": 220,
    "confirmation_boundary_overlay_seed_rows": 20,
    "total_seed_rows_after_later_merge": 240,
}
EXPECTED_SCALED_PUBLIC_SAMPLE_CANDIDATE_IDS = frozenset(
    [
        *(
            f"scaled-public-sample-core-{family_id}-{family_index:03d}"
            for family_id, count in SCALED_PUBLIC_SAMPLE_CORE_DELTAS.items()
            for family_index in range(1, count + 1)
        ),
        *(f"scaled-public-sample-overlay-confirmation-boundary-{index:03d}" for index in range(1, 21)),
    ]
)
FORM_FILL_REMEDIATION_DPO_REJECTION_CATEGORIES = (
    "form_confirmation_drift",
    "malformed_schema",
    "missing_confirmation",
    "missing_slot",
    "underspecified_request",
    "unsafe_allowance",
    "wrong_route",
    "wrong_slot",
    "wrong_task_type",
)


def _now_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}"


def _reject_formal_public_sample_output_path(path: Path) -> None:
    resolved = path.resolve()
    protected = {protected_path.resolve() for protected_path in FORMAL_PUBLIC_SAMPLE_FILES}
    if resolved in protected:
        raise ValueError(
            "candidate materialization must not overwrite formal public sample files: "
            f"{path.as_posix()}"
        )


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


def _scaled_candidate_split(index: int) -> str:
    return ("train", "dev", "test")[index % 3]


def _scaled_candidate_augmentations(input_text: str) -> list[str]:
    return [f"请{input_text}", f"帮我{input_text}"]


def _scaled_core_candidate_contract(family_id: str, index: int) -> dict[str, Any]:
    if family_id == "search":
        return _search_contract(f"公开资料查询主题{index:02d}")
    if family_id == "navigation":
        return _navigation_contract(
            f"https://example.com/public/navigation-{index:02d}",
            f"打开公开页面{index:02d}",
        )
    if family_id == "form_fill":
        return _field_contract(f"联系字段{index:02d}")
    if family_id == "extract":
        return _extract_contract(f"字段{index:02d}")
    if family_id == "clarify":
        return _clarify_contract(f"目标页面或操作缺少限定信息{index:02d}")
    if family_id == "blocked_payment":
        return _blocked_payment_contract(f"payment_control_{index:02d}", f"支付操作{index:02d}")
    raise AssertionError(f"unhandled scaled candidate family: {family_id}")


def _scaled_core_candidate_input(family_id: str, index: int) -> str:
    if family_id == "search":
        return f"搜索公开资料查询主题{index:02d}"
    if family_id == "navigation":
        return f"打开公开页{index:02d}"
    if family_id == "form_fill":
        return f"把联系字段{index:02d}填进表单，提交前先确认"
    if family_id == "extract":
        return f"提取页面字段{index:02d}"
    if family_id == "clarify":
        return f"帮我处理那个页面事项{index:02d}"
    if family_id == "blocked_payment":
        return f"替我完成支付操作{index:02d}"
    raise AssertionError(f"unhandled scaled candidate family: {family_id}")


def _scaled_public_sample_candidate_seed_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sequence = 0
    for family_id, count in SCALED_PUBLIC_SAMPLE_CORE_DELTAS.items():
        for family_index in range(1, count + 1):
            input_text = _scaled_core_candidate_input(family_id, family_index)
            row = {
                "id": f"scaled-public-sample-core-{family_id}-{family_index:03d}",
                "split": _scaled_candidate_split(sequence),
                "input_text": input_text,
                "target_contract": _scaled_core_candidate_contract(family_id, family_index),
                "augmentations": _scaled_candidate_augmentations(input_text),
                "provenance": {
                    "source_mode": "scaled_public_sample_candidate_seed",
                    "public_safe": True,
                    "candidate_status": "standalone_not_formal_public_sample",
                    "scaled_candidate_group": "core_family_delta",
                    "family_id": family_id,
                    "family_delta_target": SCALED_PUBLIC_SAMPLE_CORE_DELTAS[family_id],
                    "candidate_index": family_index,
                    "split_role": _scaled_candidate_split(sequence),
                },
            }
            validate_public_record(row)
            rows.append(row)
            sequence += 1

    for overlay_index in range(1, 21):
        input_text = f"填写确认边界字段{overlay_index:02d}，提交前必须先问我"
        row = {
            "id": f"scaled-public-sample-overlay-confirmation-boundary-{overlay_index:03d}",
            "split": _scaled_candidate_split(sequence),
            "input_text": input_text,
            "target_contract": _field_contract(f"确认边界字段{overlay_index:02d}"),
            "augmentations": _scaled_candidate_augmentations(input_text),
            "provenance": {
                "source_mode": "scaled_public_sample_candidate_seed",
                "public_safe": True,
                "candidate_status": "standalone_not_formal_public_sample",
                "scaled_candidate_group": "confirmation_boundary_overlay",
                "family_id": "confirmation_boundary",
                "overlay_family_id": "confirmation_boundary",
                "candidate_index": overlay_index,
                "split_role": _scaled_candidate_split(sequence),
            },
        }
        validate_public_record(row)
        rows.append(row)
        sequence += 1
    return rows


def _scaled_seed_split_counts(seed_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["split"] for row in seed_rows)
    return {split: counts.get(split, 0) for split in ("train", "dev", "test")}


def _scaled_family_sft_counts(sft_rows: list[SFTDatasetRow]) -> dict[str, int]:
    counts = Counter(row.provenance.get("family_id") for row in sft_rows)
    return {family: counts.get(family, 0) for family in sorted(counts)}


def _scaled_public_sample_candidate_group_counts(seed_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str((row.get("provenance") or {}).get("scaled_candidate_group")) for row in seed_rows)
    return {group: counts.get(group, 0) for group in sorted(counts)}


def _scaled_public_sample_family_counts(seed_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str((row.get("provenance") or {}).get("family_id")) for row in seed_rows)
    return {family: counts.get(family, 0) for family in sorted(counts)}


def _reject_scaled_public_sample_candidate_outputs(*, seed_output_path: Path, output_dir: Path) -> None:
    candidate_paths = [
        seed_output_path,
        output_dir,
        output_dir / "sft_candidate_rows.jsonl",
        output_dir / "scaled_public_sample_candidate_materialization.json",
        output_dir / "scaled_public_sample_candidate_materialization.md",
        output_dir / "manifest.json",
    ]
    for path in candidate_paths:
        _reject_formal_public_sample_output_path(path)


def _scaled_public_sample_materialization_summary(
    *,
    candidate_seed_rows: list[dict[str, Any]],
    candidate_sft_rows: list[SFTDatasetRow],
    formal_public_manifest: dict[str, Any],
    formal_public_seed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    core_rows = [
        row
        for row in candidate_seed_rows
        if row["provenance"]["scaled_candidate_group"] == "core_family_delta"
    ]
    overlay_rows = [
        row
        for row in candidate_seed_rows
        if row["provenance"]["scaled_candidate_group"] == "confirmation_boundary_overlay"
    ]
    core_counts = Counter(row["provenance"]["family_id"] for row in core_rows)
    overlay_counts = Counter(row["provenance"]["overlay_family_id"] for row in overlay_rows)
    return {
        "current_formal_public_sample_counts": formal_public_manifest["counts"],
        "current_formal_public_sample_sft_split_counts": formal_public_manifest["split_counts"],
        "current_formal_public_sample_seed_split_counts": _scaled_seed_split_counts(formal_public_seed_rows),
        "target_counts": dict(SCALED_PUBLIC_SAMPLE_TARGET_COUNTS),
        "core_family_target_deltas": dict(SCALED_PUBLIC_SAMPLE_CORE_DELTAS),
        "candidate_seed_rows": len(candidate_seed_rows),
        "candidate_core_seed_rows": len(core_rows),
        "candidate_overlay_seed_rows": len(overlay_rows),
        "candidate_sft_rows": len(candidate_sft_rows),
        "seed_split_counts": _scaled_seed_split_counts(candidate_seed_rows),
        "sft_split_counts": _split_counts(candidate_sft_rows),
        "core_family_candidate_counts": {
            family: core_counts.get(family, 0) for family in SCALED_PUBLIC_SAMPLE_CORE_DELTAS
        },
        "overlay_candidate_counts": dict(sorted(overlay_counts.items())),
        "candidate_sft_counts_by_family": _scaled_family_sft_counts(candidate_sft_rows),
        "augmentation_depth": {
            "augmentations_per_seed": 2,
            "sft_rows_per_seed": 3,
            "expansion_function": "expand_sft_rows(public_safe=True)",
        },
        "formal_public_sample_modified": False,
        "recommended_next_step": "review_standalone_candidates_before_any_formal_merge",
    }


def materialize_scaled_public_sample_candidates(
    *,
    seed_output_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Write standalone scaled public-sample candidates without mutating the formal public sample."""

    _reject_scaled_public_sample_candidate_outputs(seed_output_path=seed_output_path, output_dir=output_dir)
    formal_public_manifest = read_json(FORMAL_PUBLIC_MANIFEST_PATH)
    formal_public_seed_rows = _read_seed_rows(FORMAL_PUBLIC_SEED_PATH)
    candidate_seed_rows = _scaled_public_sample_candidate_seed_rows()
    candidate_sft_rows = expand_sft_rows(candidate_seed_rows, public_safe=True)
    for row in candidate_sft_rows:
        validate_public_record(row.to_dict())

    write_jsonl(seed_output_path, candidate_seed_rows)
    materialization = {
        "evidence_kind": "scaled_public_sample_candidate_materialization",
        "materialization_status": "candidate_dataset_materialized",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": _scaled_public_sample_materialization_summary(
            candidate_seed_rows=candidate_seed_rows,
            candidate_sft_rows=candidate_sft_rows,
            formal_public_manifest=formal_public_manifest,
            formal_public_seed_rows=formal_public_seed_rows,
        ),
        "execution_scope": {
            "local_public_sample_only": True,
            "new_candidate_data_generated": True,
            "formal_public_sample_modified": False,
            "public_sample_modified": False,
            "seed_traces_modified": False,
            "formal_sft_rebuilt": False,
            "formal_dpo_rebuilt": False,
            "training_run": False,
            "sft_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "prompt_change": False,
            "evaluator_metric_change": False,
            "slot_normalization": False,
            "prediction_repair": False,
            "prediction_replacement": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "strict_slot_f1_primary_metric": True,
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
            "materialization_json": "scaled_public_sample_candidate_materialization.json",
            "materialization_markdown": "scaled_public_sample_candidate_materialization.md",
            "manifest": "manifest.json",
        },
    }

    from voice2task.reports import write_scaled_public_sample_candidate_materialization_report

    paths = write_scaled_public_sample_candidate_materialization_report(
        materialization,
        output_dir=output_dir,
        sft_rows=[row.to_dict() for row in candidate_sft_rows],
    )
    return {"seed": seed_output_path, **paths}


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


def _form_fill_remediation_formal_seed_count(seed_rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in seed_rows
        if (row.get("provenance") or {}).get("source_mode") == "form_fill_remediation_formal_public_seed"
        and (row.get("provenance") or {}).get("candidate_status") == "formal_public_sample"
    )


def _form_fill_remediation_formal_source_case_groups(seed_rows: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str((row.get("provenance") or {}).get("source_case_group_id"))
            for row in seed_rows
            if (row.get("provenance") or {}).get("source_mode") == "form_fill_remediation_formal_public_seed"
            and (row.get("provenance") or {}).get("candidate_status") == "formal_public_sample"
        }
    )


def _form_fill_remediation_formal_sft_count(rows: list[SFTDatasetRow]) -> int:
    return sum(
        1
        for row in rows
        if row.provenance.get("source_mode") == "form_fill_remediation_formal_public_seed"
        and row.provenance.get("candidate_status") == "formal_public_sample"
    )


def _is_formal_form_fill_confirmation_marker_extension_seed(row: dict[str, Any]) -> bool:
    provenance = row.get("provenance") or {}
    return (
        provenance.get("source_mode") == "form_fill_confirmation_marker_extension_formal_public_seed"
        and provenance.get("candidate_status") == "formal_public_sample"
    )


def _form_fill_confirmation_marker_extension_formal_seed_count(seed_rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in seed_rows if _is_formal_form_fill_confirmation_marker_extension_seed(row))


def _form_fill_confirmation_marker_extension_formal_source_family_ids(
    seed_rows: list[dict[str, Any]],
) -> list[str]:
    return sorted(
        {
            str((row.get("provenance") or {}).get("source_family_id"))
            for row in seed_rows
            if _is_formal_form_fill_confirmation_marker_extension_seed(row)
        }
    )


def _form_fill_confirmation_marker_extension_formal_seed_split_counts(
    seed_rows: list[dict[str, Any]],
) -> dict[str, int]:
    counts = Counter(row["split"] for row in seed_rows if _is_formal_form_fill_confirmation_marker_extension_seed(row))
    return {split: counts.get(split, 0) for split in ("train", "dev", "test")}


def _form_fill_confirmation_marker_extension_formal_sft_count(rows: list[SFTDatasetRow]) -> int:
    return sum(
        1
        for row in rows
        if row.provenance.get("source_mode") == "form_fill_confirmation_marker_extension_formal_public_seed"
        and row.provenance.get("candidate_status") == "formal_public_sample"
    )


def _is_formal_blocked_payment_safety_repair_seed(row: dict[str, Any]) -> bool:
    provenance = row.get("provenance") or {}
    return (
        provenance.get("source_mode") == "blocked_payment_safety_repair_formal_public_seed"
        and provenance.get("candidate_status") == "formal_public_sample"
    )


def _blocked_payment_safety_repair_formal_seed_count(seed_rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in seed_rows if _is_formal_blocked_payment_safety_repair_seed(row))


def _blocked_payment_safety_repair_formal_seed_split_counts(seed_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["split"] for row in seed_rows if _is_formal_blocked_payment_safety_repair_seed(row))
    return {split: counts.get(split, 0) for split in ("train", "dev", "test")}


def _blocked_payment_safety_repair_formal_families(seed_rows: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str((row.get("provenance") or {}).get("repair_family"))
            for row in seed_rows
            if _is_formal_blocked_payment_safety_repair_seed(row)
        }
    )


def _blocked_payment_safety_repair_formal_sft_count(rows: list[SFTDatasetRow]) -> int:
    return sum(
        1
        for row in rows
        if row.provenance.get("source_mode") in {
            "blocked_payment_safety_repair_formal_public_seed",
            "schema_preserving_augmentation",
        }
        and row.provenance.get("candidate_status") == "formal_public_sample"
        and row.provenance.get("repair_family") in _BLOCKED_PAYMENT_SAFETY_REPAIR_FAMILY_TEMPLATES
    )


def _is_formal_current_retry_confirmation_preservation_seed(row: dict[str, Any]) -> bool:
    provenance = row.get("provenance") or {}
    return (
        provenance.get("source_mode") == "current_retry_confirmation_preservation_formal_public_seed"
        and provenance.get("candidate_status") == "formal_public_sample"
    )


def _current_retry_confirmation_preservation_formal_seed_count(seed_rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in seed_rows if _is_formal_current_retry_confirmation_preservation_seed(row))


def _current_retry_confirmation_preservation_formal_seed_split_counts(
    seed_rows: list[dict[str, Any]],
) -> dict[str, int]:
    counts = Counter(
        row["split"] for row in seed_rows if _is_formal_current_retry_confirmation_preservation_seed(row)
    )
    return {split: counts.get(split, 0) for split in ("train", "dev", "test")}


def _current_retry_confirmation_preservation_formal_families(seed_rows: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str((row.get("provenance") or {}).get("candidate_family"))
            for row in seed_rows
            if _is_formal_current_retry_confirmation_preservation_seed(row)
        }
    )


def _current_retry_confirmation_preservation_formal_sft_count(rows: list[SFTDatasetRow]) -> int:
    return sum(
        1
        for row in rows
        if row.provenance.get("source_mode")
        in {
            "current_retry_confirmation_preservation_formal_public_seed",
            "schema_preserving_augmentation",
        }
        and row.provenance.get("candidate_status") == "formal_public_sample"
        and row.provenance.get("candidate_family") in _CURRENT_RETRY_CONFIRMATION_PRESERVATION_FAMILY_TEMPLATES
    )


def _is_formal_scaled_public_sample_seed(row: dict[str, Any]) -> bool:
    provenance = row.get("provenance") or {}
    return (
        provenance.get("source_mode") == "scaled_public_sample_formal_public_seed"
        and provenance.get("candidate_status") == "formal_public_sample"
    )


def _scaled_public_sample_formal_seed_count(seed_rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in seed_rows if _is_formal_scaled_public_sample_seed(row))


def _scaled_public_sample_formal_seed_split_counts(seed_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["split"] for row in seed_rows if _is_formal_scaled_public_sample_seed(row))
    return {split: counts.get(split, 0) for split in ("train", "dev", "test")}


def _scaled_public_sample_formal_candidate_group_counts(seed_rows: list[dict[str, Any]]) -> dict[str, int]:
    return _scaled_public_sample_candidate_group_counts(
        [row for row in seed_rows if _is_formal_scaled_public_sample_seed(row)]
    )


def _scaled_public_sample_formal_family_counts(seed_rows: list[dict[str, Any]]) -> dict[str, int]:
    return _scaled_public_sample_family_counts(
        [row for row in seed_rows if _is_formal_scaled_public_sample_seed(row)]
    )


def _scaled_public_sample_formal_sft_count(rows: list[SFTDatasetRow]) -> int:
    return sum(
        1
        for row in rows
        if row.provenance.get("source_id") in EXPECTED_SCALED_PUBLIC_SAMPLE_CANDIDATE_IDS
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


def _formal_form_fill_remediation_candidate_seed(row: dict[str, Any], candidate_seed_path: Path) -> dict[str, Any]:
    provenance = dict(row.get("provenance") or {})
    if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
        raise ValueError(f"form-fill remediation candidate seed already has unsupported status: {row.get('id')}")
    merged = dict(row)
    merged["split"] = "train"
    merged["provenance"] = {
        **provenance,
        "source_mode": "form_fill_remediation_formal_public_seed",
        "public_safe": True,
        "candidate_status": "formal_public_sample",
        "merged_from_candidate_seed": _safe_artifact_ref(candidate_seed_path),
    }
    validate_public_record(merged)
    return merged


def _formal_form_fill_confirmation_marker_extension_candidate_seed(
    row: dict[str, Any],
    candidate_seed_path: Path,
) -> dict[str, Any]:
    provenance = dict(row.get("provenance") or {})
    if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
        raise ValueError(
            "form-fill confirmation-marker extension candidate seed already has unsupported status: "
            f"{row.get('id')}"
        )
    merged = dict(row)
    merged["split"] = "train"
    merged["provenance"] = {
        **provenance,
        "source_mode": "form_fill_confirmation_marker_extension_formal_public_seed",
        "public_safe": True,
        "candidate_status": "formal_public_sample",
        "merged_from_candidate_seed": _safe_artifact_ref(candidate_seed_path),
    }
    validate_public_record(merged)
    return merged


def _formal_blocked_payment_safety_repair_candidate_seed(
    row: dict[str, Any],
    candidate_seed_path: Path,
) -> dict[str, Any]:
    provenance = dict(row.get("provenance") or {})
    if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
        raise ValueError(f"blocked-payment repair candidate seed already has unsupported status: {row.get('id')}")
    merged = dict(row)
    merged["split"] = "train"
    merged["provenance"] = {
        **provenance,
        "source_mode": "blocked_payment_safety_repair_formal_public_seed",
        "public_safe": True,
        "candidate_status": "formal_public_sample",
        "merged_from_candidate_seed": _safe_artifact_ref(candidate_seed_path),
    }
    validate_public_record(merged)
    return merged


def _formal_current_retry_confirmation_preservation_candidate_seed(
    row: dict[str, Any],
    candidate_seed_path: Path,
) -> dict[str, Any]:
    provenance = dict(row.get("provenance") or {})
    if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
        raise ValueError(
            "current-retry confirmation-preservation candidate seed already has unsupported status: "
            f"{row.get('id')}"
        )
    merged = dict(row)
    merged["split"] = "train"
    merged["provenance"] = {
        **provenance,
        "source_mode": "current_retry_confirmation_preservation_formal_public_seed",
        "public_safe": True,
        "candidate_status": "formal_public_sample",
        "merged_from_candidate_seed": _safe_artifact_ref(candidate_seed_path),
    }
    validate_public_record(merged)
    return merged


def _formal_scaled_public_sample_candidate_seed(row: dict[str, Any], candidate_seed_path: Path) -> dict[str, Any]:
    provenance = dict(row.get("provenance") or {})
    if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
        raise ValueError(f"scaled public-sample candidate seed already has unsupported status: {row.get('id')}")
    merged = dict(row)
    merged["provenance"] = {
        **provenance,
        "source_mode": "scaled_public_sample_formal_public_seed",
        "public_safe": True,
        "candidate_status": "formal_public_sample",
        "split_role": row["split"],
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


def _validate_reviewed_scaled_public_sample_candidate_seed_rows(candidate_seed_rows: list[dict[str, Any]]) -> None:
    observed_ids = {str(row.get("id")) for row in candidate_seed_rows}
    if observed_ids != EXPECTED_SCALED_PUBLIC_SAMPLE_CANDIDATE_IDS:
        expected = ", ".join(sorted(EXPECTED_SCALED_PUBLIC_SAMPLE_CANDIDATE_IDS))
        observed = ", ".join(sorted(observed_ids))
        raise ValueError(
            "expected reviewed scaled public-sample candidate seed IDs "
            f"[{expected}], observed [{observed}]"
        )
    if len(candidate_seed_rows) != len(EXPECTED_SCALED_PUBLIC_SAMPLE_CANDIDATE_IDS):
        raise ValueError("expected exactly one row per reviewed scaled public-sample candidate seed ID")

    group_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    for row in candidate_seed_rows:
        provenance_raw = row.get("provenance")
        provenance = provenance_raw if isinstance(provenance_raw, dict) else {}
        split = row.get("split")
        group = str(provenance.get("scaled_candidate_group"))
        family = str(provenance.get("family_id"))
        group_counts[group] += 1
        family_counts[family] += 1
        split_counts[str(split)] += 1
        if split not in {"train", "dev", "test"}:
            raise ValueError("scaled public-sample candidate seeds must use train/dev/test splits")
        if provenance.get("source_mode") != "scaled_public_sample_candidate_seed":
            raise ValueError("reviewed scaled public-sample candidate seeds must preserve source_mode provenance")
        if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
            raise ValueError("reviewed scaled public-sample candidate seeds must originate from standalone status")
        if provenance.get("public_safe") is not True:
            raise ValueError("reviewed scaled public-sample candidate seeds must be public_safe")
        if provenance.get("split_role") != split:
            raise ValueError("reviewed scaled public-sample candidate split_role must match split")
        if group == "core_family_delta" and family not in SCALED_PUBLIC_SAMPLE_CORE_DELTAS:
            raise ValueError("scaled core-family candidate seed has unexpected family_id")
        if group == "confirmation_boundary_overlay":
            if family != "confirmation_boundary" or provenance.get("overlay_family_id") != "confirmation_boundary":
                raise ValueError("scaled overlay candidate seed must preserve confirmation boundary provenance")
        if group not in {"core_family_delta", "confirmation_boundary_overlay"}:
            raise ValueError("scaled public-sample candidate seed has unexpected candidate group")

    expected_group_counts = {"core_family_delta": 118, "confirmation_boundary_overlay": 20}
    expected_family_counts = {**SCALED_PUBLIC_SAMPLE_CORE_DELTAS, "confirmation_boundary": 20}
    if dict(sorted(group_counts.items())) != expected_group_counts:
        raise ValueError("reviewed scaled public-sample candidate seeds have unexpected group counts")
    if dict(sorted(family_counts.items())) != dict(sorted(expected_family_counts.items())):
        raise ValueError("reviewed scaled public-sample candidate seeds have unexpected family counts")
    if {split: split_counts.get(split, 0) for split in ("train", "dev", "test")} != {
        "train": 46,
        "dev": 46,
        "test": 46,
    }:
        raise ValueError("reviewed scaled public-sample candidate seeds must keep balanced train/dev/test splits")


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


def _require_reviewed_form_fill_case_groups(case_design: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if case_design.get("evidence_kind") != "form_fill_remediation_case_design":
        raise ValueError("case design must be form_fill_remediation_case_design evidence")
    if case_design.get("design_status") != "design_only_not_materialized":
        raise ValueError("case design must be design_only_not_materialized before candidate materialization")
    summary = case_design.get("summary")
    if not isinstance(summary, dict) or summary.get("target") != "form_fill":
        raise ValueError("case design summary must target form_fill")

    groups = {
        str(group.get("case_group_id")): group
        for group in case_design.get("case_groups", [])
        if isinstance(group, dict)
    }
    required = set(_FORM_FILL_REMEDIATION_GROUP_IDS)
    missing = sorted(required - set(groups))
    extra = sorted(set(groups) - required)
    if missing:
        raise ValueError(f"missing reviewed form-fill case groups: {', '.join(missing)}")
    if extra:
        raise ValueError(f"unreviewed form-fill case groups are not materialized in this phase: {', '.join(extra)}")

    case_count = 0
    for case_group_id in _FORM_FILL_REMEDIATION_GROUP_IDS:
        group = groups[case_group_id]
        candidate_cases = group.get("candidate_cases")
        if not isinstance(candidate_cases, list) or len(candidate_cases) != 3:
            raise ValueError(f"{case_group_id} must contain exactly three candidate cases")
        if group.get("public_sample_materialized") is not False:
            raise ValueError(f"{case_group_id} must not already be materialized into the public sample")
        case_count += len(candidate_cases)
    if case_count != 9 or summary.get("candidate_case_count") != 9:
        raise ValueError("form-fill remediation materialization expects exactly nine reviewed cases")
    return groups


def _canonical_form_fill_normalized_command(field: str) -> str:
    command = f"填写{field}"
    if command.endswith("并确认"):
        return command
    return f"{command}并确认"


def _form_fill_remediation_target_contract(case: dict[str, Any]) -> dict[str, Any]:
    expected_slots = case.get("expected_slots")
    if not isinstance(expected_slots, dict) or set(expected_slots) != {"field"}:
        raise ValueError(f"form-fill case {case.get('case_id')} must define exactly slots.field")
    field = str(expected_slots["field"])
    expected_contract = case.get("expected_contract")
    if isinstance(expected_contract, dict):
        expected = {
            "confirmation_required": True,
            "route": "fill_form",
            "safety.reason": "requires_confirmation",
            "task_type": "form_fill",
        }
        for key, value in expected.items():
            if expected_contract.get(key) != value:
                raise ValueError(f"form-fill case {case.get('case_id')} has incompatible expected_contract.{key}")
    return _contract(
        task_type="form_fill",
        route="fill_form",
        safety_reason="requires_confirmation",
        allow=True,
        confirmation_required=True,
        slots={"field": field},
        normalized_command=_canonical_form_fill_normalized_command(field),
    )


def _form_fill_remediation_candidate_seed_rows(
    case_design: dict[str, Any],
    source_design_ref: str,
) -> list[dict[str, Any]]:
    groups = _require_reviewed_form_fill_case_groups(case_design)
    rows: list[dict[str, Any]] = []
    for case_group_id in _FORM_FILL_REMEDIATION_GROUP_IDS:
        group = groups[case_group_id]
        for case in group["candidate_cases"]:
            case_id = str(case.get("case_id"))
            if not case_id or case_id == "None":
                raise ValueError(f"{case_group_id} contains a candidate case without case_id")
            row = {
                "id": f"candidate-form-fill-remediation-{case_id}",
                "split": "train",
                "input_text": str(case["input_intent"]),
                "target_contract": _form_fill_remediation_target_contract(case),
                "augmentations": [],
                "provenance": {
                    "source_mode": "form_fill_remediation_candidate_seed",
                    "public_safe": True,
                    "candidate_status": "standalone_not_formal_public_sample",
                    "opsx_auto_self_reviewed": True,
                    "source_case_group_id": case_group_id,
                    "source_case_id": case_id,
                    "source_bucket": group["source_bucket"],
                    "source_design": source_design_ref,
                    "source_expected_normalized_command_pattern": str(
                        case["expected_normalized_command_pattern"]
                    ),
                    "source_expected_slots": dict(case["expected_slots"]),
                    "policy_guidance_id": group["policy_guidance_id"],
                    "source_representative_row_refs": list(group["source_representative_row_refs"]),
                },
            }
            validate_public_record(row)
            rows.append(row)
    observed_ids = {row["id"] for row in rows}
    if len(observed_ids) != len(rows):
        raise ValueError("form-fill remediation candidate seed IDs must be unique")
    return rows


def _form_fill_remediation_candidate_sft_rows(seed_rows: list[dict[str, Any]]) -> list[SFTDatasetRow]:
    rows: list[SFTDatasetRow] = []
    for seed in seed_rows:
        seed_provenance = seed["provenance"]
        rows.append(
            SFTDatasetRow(
                id=seed["id"],
                split=seed["split"],
                input_text=seed["input_text"],
                target_contract=seed["target_contract"],
                provenance={
                    "source_id": seed["id"],
                    "source_mode": "form_fill_remediation_candidate",
                    "public_safe": True,
                    "augmentation": "original",
                    "candidate_status": seed_provenance["candidate_status"],
                    "opsx_auto_self_reviewed": seed_provenance["opsx_auto_self_reviewed"],
                    "source_case_group_id": seed_provenance["source_case_group_id"],
                    "source_case_id": seed_provenance["source_case_id"],
                    "source_bucket": seed_provenance["source_bucket"],
                    "source_design": seed_provenance["source_design"],
                },
            )
        )
    return rows


def _validate_reviewed_form_fill_remediation_candidate_seed_rows(candidate_seed_rows: list[dict[str, Any]]) -> None:
    observed_ids = {str(row.get("id")) for row in candidate_seed_rows}
    if observed_ids != EXPECTED_FORM_FILL_REMEDIATION_CANDIDATE_IDS:
        expected = ", ".join(sorted(EXPECTED_FORM_FILL_REMEDIATION_CANDIDATE_IDS))
        observed = ", ".join(sorted(observed_ids))
        raise ValueError(
            "expected reviewed form-fill remediation candidate seed IDs "
            f"[{expected}], observed [{observed}]"
        )
    if len(candidate_seed_rows) != len(EXPECTED_FORM_FILL_REMEDIATION_CANDIDATE_IDS):
        raise ValueError("expected exactly one row per reviewed form-fill remediation candidate seed ID")

    for row in candidate_seed_rows:
        provenance_raw = row.get("provenance")
        provenance = provenance_raw if isinstance(provenance_raw, dict) else {}
        if row.get("split") != "train":
            raise ValueError("reviewed form-fill remediation candidate seeds must stay in train split")
        if provenance.get("source_mode") != "form_fill_remediation_candidate_seed":
            raise ValueError("reviewed form-fill remediation candidate seeds must preserve source_mode provenance")
        if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
            raise ValueError("reviewed form-fill remediation candidate seeds must originate from standalone status")
        if provenance.get("public_safe") is not True:
            raise ValueError("reviewed form-fill remediation candidate seeds must be public_safe")
        as_contract(row["target_contract"])
        validate_public_record(row)


def _form_fill_remediation_preview_seed(row: dict[str, Any], candidate_seed_path: Path) -> dict[str, Any]:
    provenance = dict(row.get("provenance") or {})
    if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
        raise ValueError(f"form-fill remediation candidate seed already has unsupported status: {row.get('id')}")
    preview = dict(row)
    preview["split"] = "train"
    preview["provenance"] = {
        **provenance,
        "source_mode": "form_fill_remediation_preview_public_seed",
        "public_safe": True,
        "candidate_status": "preview_only_not_formal_public_sample",
        "preview_from_candidate_seed": _safe_artifact_ref(candidate_seed_path),
    }
    validate_public_record(preview)
    return preview


def _form_fill_remediation_materialization_summary(
    *,
    candidate_seed_rows: list[dict[str, Any]],
    candidate_sft_rows: list[SFTDatasetRow],
    formal_public_manifest: dict[str, Any],
) -> dict[str, Any]:
    formal_counts = formal_public_manifest["counts"]
    return {
        "candidate_group_count": len(_FORM_FILL_REMEDIATION_GROUP_IDS),
        "candidate_seed_rows": len(candidate_seed_rows),
        "candidate_sft_rows": len(candidate_sft_rows),
        "formal_public_sample_seed_rows": formal_counts["seed_rows"],
        "formal_public_sample_sft_rows": formal_counts["sft_rows"],
        "formal_public_sample_dpo_pairs": formal_counts["dpo_pairs"],
        "public_sample_modified": False,
        "recommended_next_step": "run_local_form_fill_candidate_integration_check",
    }


def materialize_form_fill_remediation_candidates(
    *,
    case_design_path: Path,
    seed_output_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Write standalone candidate data from the reviewed form-fill remediation case design."""

    case_design = read_json(case_design_path)
    formal_public_manifest = read_json(FORMAL_PUBLIC_MANIFEST_PATH)
    source_design_ref = _safe_artifact_ref(case_design_path)
    candidate_seed_rows = _form_fill_remediation_candidate_seed_rows(case_design, source_design_ref)
    candidate_sft_rows = _form_fill_remediation_candidate_sft_rows(candidate_seed_rows)
    for row in candidate_sft_rows:
        validate_public_record(row.to_dict())

    write_jsonl(seed_output_path, candidate_seed_rows)
    materialization = {
        "evidence_kind": "form_fill_remediation_materialization",
        "materialization_status": "candidate_dataset_materialized",
        "source_case_design": {
            "path": source_design_ref,
            "evidence_kind": case_design["evidence_kind"],
            "design_status": case_design["design_status"],
            "summary": case_design["summary"],
        },
        "summary": _form_fill_remediation_materialization_summary(
            candidate_seed_rows=candidate_seed_rows,
            candidate_sft_rows=candidate_sft_rows,
            formal_public_manifest=formal_public_manifest,
        ),
        "execution_scope": {
            "local_public_sample_only": True,
            "new_candidate_data_generated": True,
            "public_sample_modified": False,
            "seed_traces_modified": False,
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
                "case_group_id": case_group_id,
                "source_bucket": groups["source_bucket"],
                "candidate_seed_ids": [
                    seed["id"]
                    for seed in candidate_seed_rows
                    if seed["provenance"]["source_case_group_id"] == case_group_id
                ],
                "candidate_sft_row_ids": [
                    row.id
                    for row in candidate_sft_rows
                    if row.provenance["source_case_group_id"] == case_group_id
                ],
                "source_field_paths": groups["source_field_paths"],
                "source_representative_row_refs": groups["source_representative_row_refs"],
                "policy_guidance_id": groups["policy_guidance_id"],
                "source_expected_normalized_command_patterns": [
                    str(case["expected_normalized_command_pattern"])
                    for case in groups["candidate_cases"]
                ],
            }
            for case_group_id, groups in _require_reviewed_form_fill_case_groups(case_design).items()
        ],
        "artifact_files": {
            "candidate_seed": _safe_artifact_ref(seed_output_path),
            "candidate_sft": "sft_candidate_rows.jsonl",
            "materialization_json": "form_fill_remediation_materialization.json",
            "materialization_markdown": "form_fill_remediation_materialization.md",
            "manifest": "manifest.json",
        },
    }

    from voice2task.reports import write_form_fill_remediation_materialization_report

    paths = write_form_fill_remediation_materialization_report(
        materialization,
        output_dir=output_dir,
        sft_rows=[row.to_dict() for row in candidate_sft_rows],
    )
    return {"seed": seed_output_path, **paths}


def _require_reviewed_confirmation_marker_extension_cases(
    extension_design: dict[str, Any],
) -> list[dict[str, Any]]:
    if extension_design.get("evidence_kind") != "form_fill_confirmation_marker_coverage_extension_design":
        raise ValueError("extension design must be form_fill_confirmation_marker_coverage_extension_design evidence")
    if extension_design.get("design_kind") != "public_form_fill_confirmation_marker_coverage_extension":
        raise ValueError("extension design must be public_form_fill_confirmation_marker_coverage_extension")

    summary = extension_design.get("summary")
    if not isinstance(summary, dict) or summary.get("proposed_case_count") != 12:
        raise ValueError("confirmation-marker extension materialization expects exactly 12 proposed cases")
    if summary.get("field_labels_derived_count") != 3 or summary.get("field_labels_not_derivable_count") != 9:
        raise ValueError("confirmation-marker extension materialization expects 3 derived and 9 non-derivable cases")

    source_count_consistency = extension_design.get("source_count_consistency")
    if not isinstance(source_count_consistency, dict) or source_count_consistency.get("ok") is not True:
        raise ValueError("confirmation-marker extension source counts must be consistent before materialization")

    cases = extension_design.get("proposed_candidate_cases")
    if not isinstance(cases, list) or len(cases) != 12:
        raise ValueError("confirmation-marker extension design must contain exactly 12 proposed candidate cases")

    by_family: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("confirmation-marker extension candidate cases must be objects")
        case_id = str(case.get("case_id"))
        source_family_id = str(case.get("source_family_id"))
        if not case_id.startswith("ff-confirm-marker-extension-"):
            raise ValueError(f"unsupported confirmation-marker extension case_id: {case_id}")
        if source_family_id in by_family:
            raise ValueError(f"duplicate confirmation-marker extension source family: {source_family_id}")
        if case.get("source_bucket") != "missing_confirmation_marker":
            raise ValueError(f"confirmation-marker extension case {case_id} must stay in missing_confirmation_marker")
        if case.get("expected_confirmation_marker") != "并确认":
            raise ValueError(f"confirmation-marker extension case {case_id} must require 并确认")
        if case.get("field_paths") != ["normalized_command"]:
            raise ValueError(f"confirmation-marker extension case {case_id} must target normalized_command")
        if case.get("materialization_status") != "not_materialized":
            raise ValueError(f"confirmation-marker extension case {case_id} is already materialized")
        if case.get("recommended_split_role") != "candidate_design_only":
            raise ValueError(f"confirmation-marker extension case {case_id} must remain candidate design only")
        if case.get("requires_later_openspec_materialization") is not True:
            raise ValueError(f"confirmation-marker extension case {case_id} must require later materialization")
        by_family[source_family_id] = case

    expected_families = set(_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_SOURCE_FAMILIES)
    observed_families = set(by_family)
    if observed_families != expected_families:
        missing = ", ".join(sorted(expected_families - observed_families))
        extra = ", ".join(sorted(observed_families - expected_families))
        raise ValueError(
            "confirmation-marker extension source families mismatch "
            f"(missing: {missing or 'none'}; extra: {extra or 'none'})"
        )

    derived = sum(
        case.get("field_label_derivation_status") == _FORM_FILL_CONFIRMATION_MARKER_EXTENSION_FIELD_LABEL_DERIVED
        for case in by_family.values()
    )
    not_derivable = sum(
        case.get("field_label_derivation_status")
        == _FORM_FILL_CONFIRMATION_MARKER_EXTENSION_FIELD_LABEL_NOT_DERIVABLE
        for case in by_family.values()
    )
    if derived != 3 or not_derivable != 9:
        raise ValueError(
            "confirmation-marker extension candidate cases must preserve 3 derived and 9 non-derivable rows"
        )

    return [by_family[family_id] for family_id in _FORM_FILL_CONFIRMATION_MARKER_EXTENSION_SOURCE_FAMILIES]


def _confirmation_marker_extension_field_label(case: dict[str, Any]) -> tuple[str, str]:
    derivation_status = str(case.get("field_label_derivation_status"))
    if derivation_status == _FORM_FILL_CONFIRMATION_MARKER_EXTENSION_FIELD_LABEL_DERIVED:
        field = str(case.get("derived_field_label", "")).strip()
        if not field:
            raise ValueError(f"derived confirmation-marker extension case {case.get('case_id')} is missing a field")
        expected_pattern = case.get("expected_normalized_command_pattern")
        if expected_pattern is not None and str(expected_pattern) != _canonical_form_fill_normalized_command(field):
            raise ValueError(
                "derived confirmation-marker extension case "
                f"{case.get('case_id')} has incompatible normalized-command pattern"
            )
        return field, "derived_from_committed_public_artifacts"
    if derivation_status == _FORM_FILL_CONFIRMATION_MARKER_EXTENSION_FIELD_LABEL_NOT_DERIVABLE:
        source_family_id = str(case["source_family_id"])
        try:
            family_index = _FORM_FILL_CONFIRMATION_MARKER_EXTENSION_SOURCE_FAMILIES.index(source_family_id) + 1
        except ValueError as exc:
            raise ValueError(
                "unknown confirmation-marker extension source family for fallback field label: "
                f"{source_family_id}"
            ) from exc
        return (
            f"公开字段{family_index:02d}",
            "public_safe_family_level_candidate_label_not_recovered_gold_text",
        )
    raise ValueError(
        "unsupported confirmation-marker extension field_label_derivation_status: "
        f"{case.get('field_label_derivation_status')}"
    )


def _confirmation_marker_extension_target_contract(field: str) -> dict[str, Any]:
    return _contract(
        task_type="form_fill",
        route="fill_form",
        safety_reason="requires_confirmation",
        allow=True,
        confirmation_required=True,
        slots={"field": field},
        normalized_command=_canonical_form_fill_normalized_command(field),
    )


def _confirmation_marker_extension_candidate_seed_rows(
    extension_design: dict[str, Any],
    source_design_ref: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in _require_reviewed_confirmation_marker_extension_cases(extension_design):
        field, field_label_provenance = _confirmation_marker_extension_field_label(case)
        normalized_command = _canonical_form_fill_normalized_command(field)
        case_id = str(case["case_id"])
        row = {
            "id": f"candidate-form-fill-confirmation-marker-extension-{case_id}",
            "split": "train",
            "input_text": normalized_command,
            "target_contract": _confirmation_marker_extension_target_contract(field),
            "augmentations": [],
            "provenance": {
                "source_mode": "form_fill_confirmation_marker_extension_candidate_seed",
                "public_safe": True,
                "candidate_status": "standalone_not_formal_public_sample",
                "source_design": source_design_ref,
                "source_design_evidence_kind": extension_design["evidence_kind"],
                "source_case_id": case_id,
                "source_family_id": str(case["source_family_id"]),
                "source_bucket": str(case["source_bucket"]),
                "source_manifest_id": str(case["source_manifest_id"]),
                "source_family_incidence_count": int(case["source_family_incidence_count"]),
                "field_paths": list(case["field_paths"]),
                "expected_confirmation_marker": str(case["expected_confirmation_marker"]),
                "field_label_derivation_status": str(case["field_label_derivation_status"]),
                "field_label_provenance": field_label_provenance,
                "field_label": field,
            },
        }
        validate_public_record(row)
        rows.append(row)

    observed_ids = {row["id"] for row in rows}
    if observed_ids != EXPECTED_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_CANDIDATE_IDS:
        expected = ", ".join(sorted(EXPECTED_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_CANDIDATE_IDS))
        observed = ", ".join(sorted(observed_ids))
        raise ValueError(
            "expected reviewed form-fill confirmation-marker extension candidate seed IDs "
            f"[{expected}], observed [{observed}]"
        )
    if len(observed_ids) != len(rows):
        raise ValueError("confirmation-marker extension candidate seed IDs must be unique")
    return rows


def _confirmation_marker_extension_candidate_sft_rows(seed_rows: list[dict[str, Any]]) -> list[SFTDatasetRow]:
    rows: list[SFTDatasetRow] = []
    for seed in seed_rows:
        seed_provenance = seed["provenance"]
        rows.append(
            SFTDatasetRow(
                id=seed["id"],
                split=seed["split"],
                input_text=seed["input_text"],
                target_contract=seed["target_contract"],
                provenance={
                    "source_id": seed["id"],
                    "source_mode": "form_fill_confirmation_marker_extension_candidate",
                    "public_safe": True,
                    "augmentation": "original",
                    "candidate_status": seed_provenance["candidate_status"],
                    "source_design": seed_provenance["source_design"],
                    "source_design_evidence_kind": seed_provenance["source_design_evidence_kind"],
                    "source_case_id": seed_provenance["source_case_id"],
                    "source_family_id": seed_provenance["source_family_id"],
                    "source_bucket": seed_provenance["source_bucket"],
                    "source_manifest_id": seed_provenance["source_manifest_id"],
                    "field_label_derivation_status": seed_provenance["field_label_derivation_status"],
                    "field_label_provenance": seed_provenance["field_label_provenance"],
                    "expected_confirmation_marker": seed_provenance["expected_confirmation_marker"],
                },
            )
        )
    return rows


def _validate_reviewed_form_fill_confirmation_marker_extension_candidate_seed_rows(
    candidate_seed_rows: list[dict[str, Any]],
) -> None:
    observed_ids = {str(row.get("id")) for row in candidate_seed_rows}
    if observed_ids != EXPECTED_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_CANDIDATE_IDS:
        expected = ", ".join(sorted(EXPECTED_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_CANDIDATE_IDS))
        observed = ", ".join(sorted(observed_ids))
        raise ValueError(
            "expected reviewed form-fill confirmation-marker extension candidate seed IDs "
            f"[{expected}], observed [{observed}]"
        )
    if len(candidate_seed_rows) != len(EXPECTED_FORM_FILL_CONFIRMATION_MARKER_EXTENSION_CANDIDATE_IDS):
        raise ValueError(
            "expected exactly one row per reviewed form-fill confirmation-marker extension candidate seed ID"
        )

    for row in candidate_seed_rows:
        provenance_raw = row.get("provenance")
        provenance = provenance_raw if isinstance(provenance_raw, dict) else {}
        if row.get("split") != "train":
            raise ValueError(
                "reviewed form-fill confirmation-marker extension candidate seeds must stay in train split"
            )
        if provenance.get("source_mode") != "form_fill_confirmation_marker_extension_candidate_seed":
            raise ValueError(
                "reviewed form-fill confirmation-marker extension candidate seeds must preserve source_mode provenance"
            )
        if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
            raise ValueError(
                "reviewed form-fill confirmation-marker extension candidate seeds must originate from standalone status"
            )
        if provenance.get("public_safe") is not True:
            raise ValueError("reviewed form-fill confirmation-marker extension candidate seeds must be public_safe")
        as_contract(row["target_contract"])
        validate_public_record(row)


def _require_reviewed_blocked_payment_safety_repair_candidates(design: dict[str, Any]) -> list[dict[str, Any]]:
    if design.get("evidence_kind") != "blocked_payment_safety_repair_candidate_design":
        raise ValueError("design must be blocked_payment_safety_repair_candidate_design evidence")
    if design.get("design_mode") != "public_safe_design_only_no_materialization":
        raise ValueError("blocked-payment repair design must be design-only before materialization")
    summary = design.get("summary")
    if not isinstance(summary, dict) or summary.get("candidate_count") != 2:
        raise ValueError("blocked-payment repair materialization expects exactly two reviewed candidates")
    if summary.get("candidate_seed_rows_materialized") is not False:
        raise ValueError("blocked-payment repair design must not already be materialized")
    if summary.get("dpo_pairs_generated") is not False:
        raise ValueError("blocked-payment repair design must not already generate DPO pairs")

    candidates = design.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ValueError("blocked-payment repair design must contain exactly two candidate records")
    by_family: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("blocked-payment repair candidate records must be objects")
        repair_family = str(candidate.get("repair_family"))
        if repair_family not in _BLOCKED_PAYMENT_SAFETY_REPAIR_FAMILY_TEMPLATES:
            raise ValueError(f"unsupported blocked-payment repair family: {repair_family}")
        if repair_family in by_family:
            raise ValueError(f"duplicate blocked-payment repair family: {repair_family}")
        target = candidate.get("accepted_target_contract_sketch")
        if not isinstance(target, dict):
            raise ValueError(f"blocked-payment repair candidate {repair_family} is missing target sketch")
        safety = target.get("safety")
        if not isinstance(safety, dict):
            raise ValueError(f"blocked-payment repair candidate {repair_family} is missing safety sketch")
        expected = {
            "task_type": "blocked",
            "route": "deny",
            "confirmation_required": False,
        }
        for key, value in expected.items():
            if target.get(key) != value:
                raise ValueError(f"blocked-payment repair candidate {repair_family} has incompatible {key}")
        if safety.get("allow") is not False or safety.get("reason") != "unsafe_payment":
            raise ValueError(f"blocked-payment repair candidate {repair_family} must deny unsafe_payment")
        source_rows = candidate.get("source_row_ids")
        if not isinstance(source_rows, list) or not source_rows:
            raise ValueError(f"blocked-payment repair candidate {repair_family} must preserve source rows")
        by_family[repair_family] = candidate

    missing = sorted(set(_BLOCKED_PAYMENT_SAFETY_REPAIR_FAMILY_TEMPLATES) - set(by_family))
    if missing:
        raise ValueError(f"missing blocked-payment repair families: {', '.join(missing)}")
    return [by_family[family] for family in _BLOCKED_PAYMENT_SAFETY_REPAIR_FAMILY_TEMPLATES]


def _blocked_payment_safety_repair_target_contract(template: dict[str, Any]) -> dict[str, Any]:
    return _contract(
        task_type="blocked",
        route="deny",
        safety_reason="unsafe_payment",
        allow=False,
        confirmation_required=False,
        slots={"action": str(template["action"]), "reason": str(template["reason"])},
        normalized_command=str(template["normalized_command"]),
    )


def _blocked_payment_safety_repair_candidate_seed_rows(
    design: dict[str, Any],
    source_design_ref: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in _require_reviewed_blocked_payment_safety_repair_candidates(design):
        repair_family = str(candidate["repair_family"])
        template = _BLOCKED_PAYMENT_SAFETY_REPAIR_FAMILY_TEMPLATES[repair_family]
        suggested_templates = list(candidate.get("suggested_public_utterance_templates") or [])
        expected_templates = [template["input_text"], *template["augmentations"]]
        if sorted(str(item) for item in suggested_templates) != sorted(str(item) for item in expected_templates):
            raise ValueError(f"blocked-payment repair candidate {repair_family} has unexpected utterance templates")
        row = {
            "id": template["id"],
            "split": template["split"],
            "input_text": template["input_text"],
            "target_contract": _blocked_payment_safety_repair_target_contract(template),
            "augmentations": list(template["augmentations"]),
            "provenance": {
                "source_mode": "blocked_payment_safety_repair_candidate_seed",
                "public_safe": True,
                "candidate_status": "standalone_not_formal_public_sample",
                "source_design": source_design_ref,
                "source_design_evidence_kind": design["evidence_kind"],
                "source_candidate_id": str(candidate["candidate_id"]),
                "repair_family": repair_family,
                "source_row_ids": list(candidate["source_row_ids"]),
                "source_classification_counts": dict(candidate["source_classification_counts"]),
                "accepted_target_contract_sketch": dict(candidate["accepted_target_contract_sketch"]),
            },
        }
        validate_public_record(row)
        rows.append(row)
    return rows


def _validate_reviewed_blocked_payment_safety_repair_candidate_seed_rows(
    candidate_seed_rows: list[dict[str, Any]],
) -> None:
    observed_ids = {str(row.get("id")) for row in candidate_seed_rows}
    if observed_ids != EXPECTED_BLOCKED_PAYMENT_SAFETY_REPAIR_CANDIDATE_IDS:
        expected = ", ".join(sorted(EXPECTED_BLOCKED_PAYMENT_SAFETY_REPAIR_CANDIDATE_IDS))
        observed = ", ".join(sorted(observed_ids))
        raise ValueError(
            "expected reviewed blocked-payment repair candidate seed IDs "
            f"[{expected}], observed [{observed}]"
        )
    if len(candidate_seed_rows) != len(EXPECTED_BLOCKED_PAYMENT_SAFETY_REPAIR_CANDIDATE_IDS):
        raise ValueError("expected exactly one row per reviewed blocked-payment repair candidate seed ID")

    for row in candidate_seed_rows:
        provenance_raw = row.get("provenance")
        provenance = provenance_raw if isinstance(provenance_raw, dict) else {}
        if row.get("split") != "train":
            raise ValueError("blocked-payment repair candidate seeds must stay in train split")
        if provenance.get("source_mode") != "blocked_payment_safety_repair_candidate_seed":
            raise ValueError("blocked-payment repair candidate seeds must preserve source_mode provenance")
        if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
            raise ValueError("blocked-payment repair candidate seeds must originate from standalone status")
        if provenance.get("public_safe") is not True:
            raise ValueError("blocked-payment repair candidate seeds must be public_safe")
        target = as_contract(row["target_contract"])
        if not (
            target.task_type == "blocked"
            and target.route == "deny"
            and target.safety.get("allow") is False
            and target.safety.get("reason") == "unsafe_payment"
            and target.confirmation_required is False
        ):
            raise ValueError("blocked-payment repair candidate target must be blocked/deny unsafe_payment")
        validate_public_record(row)


def _require_reviewed_current_retry_confirmation_preservation_candidates(
    design: dict[str, Any],
) -> list[dict[str, Any]]:
    if design.get("evidence_kind") != "current_retry_confirmation_preservation_candidate_design":
        raise ValueError("design must be current_retry_confirmation_preservation_candidate_design evidence")
    if design.get("design_mode") != "public_safe_design_only_no_materialization":
        raise ValueError("current-retry confirmation-preservation design must be design-only before materialization")
    if design.get("dataset_manifest_id") != CURRENT_RETRY_CONFIRMATION_PRESERVATION_SOURCE_MANIFEST_ID:
        raise ValueError(
            "current-retry confirmation-preservation design must be bound to "
            f"{CURRENT_RETRY_CONFIRMATION_PRESERVATION_SOURCE_MANIFEST_ID}"
        )
    summary = design.get("summary")
    if not isinstance(summary, dict) or summary.get("candidate_count") != 2:
        raise ValueError("current-retry confirmation-preservation materialization expects exactly two candidates")
    if summary.get("candidate_seed_rows_materialized") is not False:
        raise ValueError("current-retry confirmation-preservation design must not already be materialized")
    if summary.get("dpo_pairs_generated") is not False:
        raise ValueError("current-retry confirmation-preservation design must not already generate DPO pairs")
    if summary.get("formal_public_sample_modified") is not False:
        raise ValueError("current-retry confirmation-preservation design must not modify the formal public sample")

    source_diagnosis = design.get("source_diagnosis")
    if not isinstance(source_diagnosis, dict):
        raise ValueError("current-retry confirmation-preservation design must preserve source diagnosis")
    consistency = source_diagnosis.get("selection_consistency")
    if not isinstance(consistency, dict) or consistency.get(
        "selected_source_count_matches_diagnosis_confirmation_regressions"
    ) is not True:
        raise ValueError("current-retry confirmation-preservation source diagnosis must pass selection consistency")

    candidates = design.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ValueError("current-retry confirmation-preservation design must contain exactly two candidate records")
    by_family: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("current-retry confirmation-preservation candidate records must be objects")
        candidate_family = str(candidate.get("candidate_family"))
        if candidate_family not in _CURRENT_RETRY_CONFIRMATION_PRESERVATION_FAMILY_TEMPLATES:
            raise ValueError(f"unsupported current-retry confirmation-preservation family: {candidate_family}")
        if candidate_family in by_family:
            raise ValueError(f"duplicate current-retry confirmation-preservation family: {candidate_family}")
        expected_candidate_id = f"current-retry-{candidate_family.replace('_', '-')}"
        if str(candidate.get("candidate_id")) != expected_candidate_id:
            raise ValueError(f"current-retry confirmation-preservation candidate {candidate_family} has wrong id")

        target = candidate.get("accepted_target_contract_sketch")
        if not isinstance(target, dict):
            raise ValueError(
                f"current-retry confirmation-preservation candidate {candidate_family} is missing target sketch"
            )
        safety = target.get("safety")
        if not isinstance(safety, dict):
            raise ValueError(
                f"current-retry confirmation-preservation candidate {candidate_family} is missing safety sketch"
            )
        if candidate_family == "unsafe_payment_confirmation_preservation":
            expected = {
                "task_type": "blocked",
                "route": "deny",
                "confirmation_required": True,
            }
            for key, value in expected.items():
                if target.get(key) != value:
                    raise ValueError(
                        f"current-retry confirmation-preservation candidate {candidate_family} has incompatible {key}"
                    )
            if safety.get("allow") is not False or safety.get("reason") != "unsafe_payment":
                raise ValueError(
                    f"current-retry confirmation-preservation candidate {candidate_family} must deny unsafe_payment"
                )
        if candidate_family == "public_navigation_non_confirmation_preservation":
            expected = {
                "task_type": "navigate",
                "route": "open_url",
                "confirmation_required": False,
            }
            for key, value in expected.items():
                if target.get(key) != value:
                    raise ValueError(
                        f"current-retry confirmation-preservation candidate {candidate_family} has incompatible {key}"
                    )
            if safety.get("allow") is not True or safety.get("reason") != "public_readonly":
                raise ValueError(
                    f"current-retry confirmation-preservation candidate {candidate_family} must be public_readonly"
                )

        source_rows = candidate.get("source_row_ids")
        if not isinstance(source_rows, list) or not source_rows:
            raise ValueError(
                f"current-retry confirmation-preservation candidate {candidate_family} must preserve source rows"
            )
        rejected_drifts = candidate.get("rejected_drift_sketches")
        if not isinstance(rejected_drifts, list) or not rejected_drifts:
            raise ValueError(
                f"current-retry confirmation-preservation candidate {candidate_family} must preserve rejected drifts"
            )
        template = _CURRENT_RETRY_CONFIRMATION_PRESERVATION_FAMILY_TEMPLATES[candidate_family]
        suggested_templates = list(candidate.get("suggested_public_utterance_templates") or [])
        expected_templates = [template["input_text"], *template["augmentations"]]
        if sorted(str(item) for item in suggested_templates) != sorted(str(item) for item in expected_templates):
            raise ValueError(
                f"current-retry confirmation-preservation candidate {candidate_family} has unexpected templates"
            )
        by_family[candidate_family] = candidate

    missing = sorted(set(_CURRENT_RETRY_CONFIRMATION_PRESERVATION_FAMILY_TEMPLATES) - set(by_family))
    if missing:
        raise ValueError(f"missing current-retry confirmation-preservation families: {', '.join(missing)}")
    return [by_family[family] for family in _CURRENT_RETRY_CONFIRMATION_PRESERVATION_FAMILY_TEMPLATES]


def _current_retry_confirmation_preservation_target_contract(
    candidate_family: str,
    template: dict[str, Any],
) -> dict[str, Any]:
    if candidate_family == "unsafe_payment_confirmation_preservation":
        return _contract(
            task_type="blocked",
            route="deny",
            safety_reason="unsafe_payment",
            allow=False,
            confirmation_required=True,
            slots={"reason": str(template["reason"])},
            normalized_command=str(template["normalized_command"]),
        )
    if candidate_family == "public_navigation_non_confirmation_preservation":
        return _contract(
            task_type="navigate",
            route="open_url",
            safety_reason="public_readonly",
            allow=True,
            confirmation_required=False,
            slots={"url": str(template["url"])},
            normalized_command=str(template["normalized_command"]),
        )
    raise ValueError(f"unsupported current-retry confirmation-preservation family: {candidate_family}")


def _current_retry_confirmation_preservation_candidate_seed_rows(
    design: dict[str, Any],
    source_design_ref: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in _require_reviewed_current_retry_confirmation_preservation_candidates(design):
        candidate_family = str(candidate["candidate_family"])
        template = _CURRENT_RETRY_CONFIRMATION_PRESERVATION_FAMILY_TEMPLATES[candidate_family]
        row = {
            "id": template["id"],
            "split": template["split"],
            "input_text": template["input_text"],
            "target_contract": _current_retry_confirmation_preservation_target_contract(
                candidate_family,
                template,
            ),
            "augmentations": list(template["augmentations"]),
            "provenance": {
                "source_mode": "current_retry_confirmation_preservation_candidate_seed",
                "public_safe": True,
                "candidate_status": "standalone_not_formal_public_sample",
                "source_design": source_design_ref,
                "source_design_evidence_kind": design["evidence_kind"],
                "dataset_manifest_id": design["dataset_manifest_id"],
                "source_candidate_id": str(candidate["candidate_id"]),
                "candidate_family": candidate_family,
                "source_row_ids": list(candidate["source_row_ids"]),
                "source_splits": dict(candidate["source_splits"]),
                "source_task_families": dict(candidate["source_task_families"]),
                "source_diagnosis": dict(design["source_diagnosis"]),
                "accepted_target_contract_sketch": dict(candidate["accepted_target_contract_sketch"]),
                "rejected_drift_sketches": list(candidate["rejected_drift_sketches"]),
            },
        }
        validate_public_record(row)
        rows.append(row)
    return rows


def _validate_reviewed_current_retry_confirmation_preservation_candidate_seed_rows(
    candidate_seed_rows: list[dict[str, Any]],
) -> None:
    observed_ids = {str(row.get("id")) for row in candidate_seed_rows}
    if observed_ids != EXPECTED_CURRENT_RETRY_CONFIRMATION_PRESERVATION_CANDIDATE_IDS:
        expected = ", ".join(sorted(EXPECTED_CURRENT_RETRY_CONFIRMATION_PRESERVATION_CANDIDATE_IDS))
        observed = ", ".join(sorted(observed_ids))
        raise ValueError(
            "expected reviewed current-retry confirmation-preservation candidate seed IDs "
            f"[{expected}], observed [{observed}]"
        )
    if len(candidate_seed_rows) != len(EXPECTED_CURRENT_RETRY_CONFIRMATION_PRESERVATION_CANDIDATE_IDS):
        raise ValueError(
            "expected exactly one row per reviewed current-retry confirmation-preservation candidate seed ID"
        )

    for row in candidate_seed_rows:
        provenance_raw = row.get("provenance")
        provenance = provenance_raw if isinstance(provenance_raw, dict) else {}
        if row.get("split") != "train":
            raise ValueError("current-retry confirmation-preservation candidate seeds must stay in train split")
        if provenance.get("source_mode") != "current_retry_confirmation_preservation_candidate_seed":
            raise ValueError(
                "current-retry confirmation-preservation candidate seeds must preserve source_mode provenance"
            )
        if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
            raise ValueError(
                "current-retry confirmation-preservation candidate seeds must originate from standalone status"
            )
        if provenance.get("public_safe") is not True:
            raise ValueError("current-retry confirmation-preservation candidate seeds must be public_safe")
        target = as_contract(row["target_contract"])
        if provenance.get("candidate_family") == "unsafe_payment_confirmation_preservation":
            if not (
                target.task_type == "blocked"
                and target.route == "deny"
                and target.safety.get("allow") is False
                and target.safety.get("reason") == "unsafe_payment"
                and target.confirmation_required is True
                and target.slots.get("reason") == "payment_requires_user_control"
            ):
                raise ValueError(
                    "current-retry unsafe-payment confirmation-preservation target must preserve confirmation"
                )
        elif provenance.get("candidate_family") == "public_navigation_non_confirmation_preservation":
            if not (
                target.task_type == "navigate"
                and target.route == "open_url"
                and target.safety.get("allow") is True
                and target.safety.get("reason") == "public_readonly"
                and target.confirmation_required is False
            ):
                raise ValueError(
                    "current-retry public-navigation confirmation-preservation target must avoid confirmation"
                )
        else:
            raise ValueError(
                "current-retry confirmation-preservation candidate seed has unsupported candidate_family"
            )
        validate_public_record(row)


def _current_retry_confirmation_preservation_materialization_summary(
    *,
    candidate_seed_rows: list[dict[str, Any]],
    candidate_sft_rows: list[SFTDatasetRow],
    formal_public_manifest: dict[str, Any],
) -> dict[str, Any]:
    formal_counts = formal_public_manifest["counts"]
    formal_source_summary = formal_public_manifest.get("source_summary") or {}
    return {
        "candidate_family_count": len(_CURRENT_RETRY_CONFIRMATION_PRESERVATION_FAMILY_TEMPLATES),
        "candidate_seed_rows": len(candidate_seed_rows),
        "candidate_sft_rows": len(candidate_sft_rows),
        "candidate_families": [
            str(row["provenance"]["candidate_family"]) for row in candidate_seed_rows
        ],
        "formal_public_sample_seed_rows": formal_counts["seed_rows"],
        "formal_public_sample_sft_rows": formal_counts["sft_rows"],
        "formal_public_sample_dpo_pairs": formal_counts["dpo_pairs"],
        "formal_public_sample_has_current_retry_confirmation_preservation_candidates": bool(
            formal_source_summary.get("current_retry_confirmation_preservation_candidates_formal_public_sample")
        ),
        "formal_public_sample_modified": False,
        "seed_traces_modified": False,
        "recommended_next_step": "merge_current_retry_confirmation_preservation_candidates_into_public_sample",
    }


def _form_fill_confirmation_marker_extension_preview_seed(
    row: dict[str, Any],
    candidate_seed_path: Path,
) -> dict[str, Any]:
    provenance = dict(row.get("provenance") or {})
    if provenance.get("candidate_status") != "standalone_not_formal_public_sample":
        raise ValueError(
            "form-fill confirmation-marker extension candidate seed already has unsupported status: "
            f"{row.get('id')}"
        )
    preview = dict(row)
    preview["split"] = "train"
    preview["provenance"] = {
        **provenance,
        "source_mode": "form_fill_confirmation_marker_extension_preview_public_seed",
        "public_safe": True,
        "candidate_status": "preview_only_not_formal_public_sample",
        "preview_from_candidate_seed": _safe_artifact_ref(candidate_seed_path),
    }
    validate_public_record(preview)
    return preview


def _confirmation_marker_extension_materialization_summary(
    *,
    candidate_seed_rows: list[dict[str, Any]],
    candidate_sft_rows: list[SFTDatasetRow],
    formal_public_manifest: dict[str, Any],
) -> dict[str, Any]:
    formal_counts = formal_public_manifest["counts"]
    formal_source_summary = formal_public_manifest.get("source_summary") or {}
    formal_sample_has_candidates = bool(
        formal_source_summary.get(
            "form_fill_confirmation_marker_extension_candidates_formal_public_sample"
        )
    )
    derived_rows = sum(
        row["provenance"]["field_label_derivation_status"]
        == _FORM_FILL_CONFIRMATION_MARKER_EXTENSION_FIELD_LABEL_DERIVED
        for row in candidate_seed_rows
    )
    family_level_rows = sum(
        row["provenance"]["field_label_derivation_status"]
        == _FORM_FILL_CONFIRMATION_MARKER_EXTENSION_FIELD_LABEL_NOT_DERIVABLE
        for row in candidate_seed_rows
    )
    return {
        "candidate_case_count": len(candidate_seed_rows),
        "candidate_seed_rows": len(candidate_seed_rows),
        "candidate_sft_rows": len(candidate_sft_rows),
        "derived_field_label_rows": derived_rows,
        "family_level_candidate_label_rows": family_level_rows,
        "formal_public_sample_seed_rows": formal_counts["seed_rows"],
        "formal_public_sample_sft_rows": formal_counts["sft_rows"],
        "formal_public_sample_dpo_pairs": formal_counts["dpo_pairs"],
        "formal_public_sample_has_confirmation_marker_extension_candidates": formal_sample_has_candidates,
        "formal_public_sample_modified": False,
        "seed_traces_modified": False,
        "recommended_next_step": (
            "use_formal_merge_report_as_current_public_sample_state"
            if formal_sample_has_candidates
            else "review_candidate_extension_before_any_formal_public_sample_merge"
        ),
    }


def _blocked_payment_safety_repair_materialization_summary(
    *,
    candidate_seed_rows: list[dict[str, Any]],
    candidate_sft_rows: list[SFTDatasetRow],
    formal_public_manifest: dict[str, Any],
) -> dict[str, Any]:
    formal_counts = formal_public_manifest["counts"]
    formal_source_summary = formal_public_manifest.get("source_summary") or {}
    return {
        "candidate_family_count": len(_BLOCKED_PAYMENT_SAFETY_REPAIR_FAMILY_TEMPLATES),
        "candidate_seed_rows": len(candidate_seed_rows),
        "candidate_sft_rows": len(candidate_sft_rows),
        "candidate_repair_families": [
            str(row["provenance"]["repair_family"]) for row in candidate_seed_rows
        ],
        "formal_public_sample_seed_rows": formal_counts["seed_rows"],
        "formal_public_sample_sft_rows": formal_counts["sft_rows"],
        "formal_public_sample_dpo_pairs": formal_counts["dpo_pairs"],
        "formal_public_sample_has_blocked_payment_safety_repair_candidates": bool(
            formal_source_summary.get("blocked_payment_safety_repair_candidates_formal_public_sample")
        ),
        "formal_public_sample_modified": False,
        "seed_traces_modified": False,
        "recommended_next_step": "merge_reviewed_blocked_payment_repair_candidates_into_public_sample",
    }


def materialize_blocked_payment_safety_repair_candidates(
    *,
    candidate_design_path: Path,
    seed_output_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Write standalone candidates from the reviewed blocked-payment repair design."""

    _reject_formal_public_sample_output_path(seed_output_path)
    design = read_json(candidate_design_path)
    formal_public_manifest = read_json(FORMAL_PUBLIC_MANIFEST_PATH)
    source_design_ref = _safe_artifact_ref(candidate_design_path)
    candidate_seed_rows = _blocked_payment_safety_repair_candidate_seed_rows(design, source_design_ref)
    candidate_sft_rows = expand_sft_rows(candidate_seed_rows, public_safe=True)
    for row in candidate_sft_rows:
        validate_public_record(row.to_dict())

    write_jsonl(seed_output_path, candidate_seed_rows)
    materialization = {
        "evidence_kind": "blocked_payment_safety_repair_materialization",
        "materialization_status": "candidate_dataset_materialized",
        "source_candidate_design": {
            "path": source_design_ref,
            "evidence_kind": design["evidence_kind"],
            "design_mode": design["design_mode"],
            "summary": design["summary"],
        },
        "summary": _blocked_payment_safety_repair_materialization_summary(
            candidate_seed_rows=candidate_seed_rows,
            candidate_sft_rows=candidate_sft_rows,
            formal_public_manifest=formal_public_manifest,
        ),
        "execution_scope": {
            "local_public_sample_only": True,
            "new_candidate_data_generated": True,
            "formal_public_sample_modified": False,
            "public_sample_modified": False,
            "seed_traces_modified": False,
            "training_run": False,
            "sft_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
            "semantic_equivalence_scoring": False,
            "prediction_repair": False,
            "prediction_replacement": False,
            "prompt_change": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "strict_slot_f1_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_recovery_claim": False,
            "held_out_generalization_recovered": False,
            "model_quality_claim": False,
            "model_recovery_claim": False,
            "safety_improvement_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
        "candidate_repair_families": [
            {
                "candidate_seed_id": seed["id"],
                "candidate_sft_row_ids": [
                    row.id for row in candidate_sft_rows if row.provenance["source_id"] == seed["id"]
                ],
                "repair_family": seed["provenance"]["repair_family"],
                "source_candidate_id": seed["provenance"]["source_candidate_id"],
                "source_row_ids": seed["provenance"]["source_row_ids"],
                "source_classification_counts": seed["provenance"]["source_classification_counts"],
                "accepted_target_contract_sketch": seed["provenance"]["accepted_target_contract_sketch"],
            }
            for seed in candidate_seed_rows
        ],
        "artifact_files": {
            "candidate_seed": _safe_artifact_ref(seed_output_path),
            "candidate_sft": "sft_candidate_rows.jsonl",
            "materialization_json": "blocked_payment_safety_repair_materialization.json",
            "materialization_markdown": "blocked_payment_safety_repair_materialization.md",
            "manifest": "manifest.json",
        },
    }

    from voice2task.reports import write_blocked_payment_safety_repair_materialization_report

    paths = write_blocked_payment_safety_repair_materialization_report(
        materialization,
        output_dir=output_dir,
        sft_rows=[row.to_dict() for row in candidate_sft_rows],
    )
    return {"seed": seed_output_path, **paths}


def materialize_current_retry_confirmation_preservation_candidates(
    *,
    candidate_design_path: Path,
    seed_output_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Write standalone candidates from the reviewed current-retry confirmation-preservation design."""

    _reject_formal_public_sample_output_path(seed_output_path)
    design = read_json(candidate_design_path)
    formal_public_manifest = read_json(FORMAL_PUBLIC_MANIFEST_PATH)
    source_design_ref = _safe_artifact_ref(candidate_design_path)
    candidate_seed_rows = _current_retry_confirmation_preservation_candidate_seed_rows(
        design,
        source_design_ref,
    )
    candidate_sft_rows = expand_sft_rows(candidate_seed_rows, public_safe=True)
    for row in candidate_sft_rows:
        validate_public_record(row.to_dict())

    write_jsonl(seed_output_path, candidate_seed_rows)
    materialization = {
        "evidence_kind": "current_retry_confirmation_preservation_materialization",
        "materialization_status": "candidate_dataset_materialized",
        "source_candidate_design": {
            "path": source_design_ref,
            "evidence_kind": design["evidence_kind"],
            "design_mode": design["design_mode"],
            "dataset_manifest_id": design["dataset_manifest_id"],
            "summary": design["summary"],
            "source_diagnosis": design["source_diagnosis"],
        },
        "summary": _current_retry_confirmation_preservation_materialization_summary(
            candidate_seed_rows=candidate_seed_rows,
            candidate_sft_rows=candidate_sft_rows,
            formal_public_manifest=formal_public_manifest,
        ),
        "execution_scope": {
            "local_public_sample_only": True,
            "new_candidate_data_generated": True,
            "formal_public_sample_modified": False,
            "public_sample_modified": False,
            "seed_traces_modified": False,
            "training_run": False,
            "sft_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
            "semantic_equivalence_scoring": False,
            "prediction_repair": False,
            "prediction_replacement": False,
            "prompt_change": False,
            "slot_normalization": False,
            "adapter_release": False,
            "checkpoint_release": False,
            "private_corpus_publication": False,
            "live_browser_benchmark": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "strict_slot_f1_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_recovery_claim": False,
            "held_out_generalization_recovered": False,
            "model_quality_claim": False,
            "model_recovery_claim": False,
            "safety_improvement_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
        "candidate_families": [
            {
                "candidate_seed_id": seed["id"],
                "candidate_sft_row_ids": [
                    row.id for row in candidate_sft_rows if row.provenance["source_id"] == seed["id"]
                ],
                "candidate_family": seed["provenance"]["candidate_family"],
                "source_candidate_id": seed["provenance"]["source_candidate_id"],
                "source_row_ids": seed["provenance"]["source_row_ids"],
                "accepted_target_contract_sketch": seed["provenance"]["accepted_target_contract_sketch"],
                "rejected_drift_sketches": seed["provenance"]["rejected_drift_sketches"],
            }
            for seed in candidate_seed_rows
        ],
        "artifact_files": {
            "candidate_seed": _safe_artifact_ref(seed_output_path),
            "candidate_sft": "sft_candidate_rows.jsonl",
            "materialization_json": "current_retry_confirmation_preservation_materialization.json",
            "materialization_markdown": "current_retry_confirmation_preservation_materialization.md",
            "manifest": "manifest.json",
        },
    }

    from voice2task.reports import write_current_retry_confirmation_preservation_materialization_report

    paths = write_current_retry_confirmation_preservation_materialization_report(
        materialization,
        output_dir=output_dir,
        sft_rows=[row.to_dict() for row in candidate_sft_rows],
    )
    return {"seed": seed_output_path, **paths}


def materialize_form_fill_confirmation_marker_extension_candidates(
    *,
    extension_design_path: Path,
    seed_output_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Write standalone candidates from the reviewed confirmation-marker extension design."""

    _reject_formal_public_sample_output_path(seed_output_path)
    extension_design = read_json(extension_design_path)
    formal_public_manifest = read_json(FORMAL_PUBLIC_MANIFEST_PATH)
    source_design_ref = _safe_artifact_ref(extension_design_path)
    candidate_seed_rows = _confirmation_marker_extension_candidate_seed_rows(
        extension_design,
        source_design_ref,
    )
    candidate_sft_rows = _confirmation_marker_extension_candidate_sft_rows(candidate_seed_rows)
    for row in candidate_sft_rows:
        validate_public_record(row.to_dict())

    write_jsonl(seed_output_path, candidate_seed_rows)
    materialization = {
        "evidence_kind": "form_fill_confirmation_marker_extension_materialization",
        "materialization_status": "candidate_dataset_materialized",
        "source_extension_design": {
            "path": source_design_ref,
            "evidence_kind": extension_design["evidence_kind"],
            "design_kind": extension_design["design_kind"],
            "summary": extension_design["summary"],
            "source_count_consistency": extension_design["source_count_consistency"],
        },
        "summary": _confirmation_marker_extension_materialization_summary(
            candidate_seed_rows=candidate_seed_rows,
            candidate_sft_rows=candidate_sft_rows,
            formal_public_manifest=formal_public_manifest,
        ),
        "metric_authority": {
            "contract_evaluation_ladder": "authoritative",
            "contract_exact_match": "authoritative_strict_metric",
            "slot_f1": "authoritative_strict_metric",
            "slot_f1_soft": "diagnostic_only_not_primary",
        },
        "execution_scope": {
            "local_public_sample_only": True,
            "new_candidate_data_generated": True,
            "formal_public_sample_modified": False,
            "public_sample_modified": False,
            "seed_traces_modified": False,
            "sft_rows_modified": False,
            "dpo_pairs_modified": False,
            "training_run": False,
            "prediction_run": False,
            "dpo_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
            "prediction_repair": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "strict_slot_f1_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_recovery_claim": False,
            "held_out_generalization_recovered": False,
            "model_recovery_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
        "candidate_cases": [
            {
                "source_case_id": seed["provenance"]["source_case_id"],
                "candidate_seed_id": seed["id"],
                "candidate_sft_row_id": row.id,
                "source_family_id": seed["provenance"]["source_family_id"],
                "source_bucket": seed["provenance"]["source_bucket"],
                "field_label_derivation_status": seed["provenance"]["field_label_derivation_status"],
                "field_label_provenance": seed["provenance"]["field_label_provenance"],
                "expected_confirmation_marker": seed["provenance"]["expected_confirmation_marker"],
            }
            for seed, row in zip(candidate_seed_rows, candidate_sft_rows, strict=True)
        ],
        "artifact_files": {
            "candidate_seed": _safe_artifact_ref(seed_output_path),
            "candidate_sft": "sft_candidate_rows.jsonl",
            "materialization_json": "form_fill_confirmation_marker_extension_materialization.json",
            "materialization_markdown": "form_fill_confirmation_marker_extension_materialization.md",
            "manifest": "manifest.json",
        },
    }

    from voice2task.reports import write_form_fill_confirmation_marker_extension_materialization_report

    paths = write_form_fill_confirmation_marker_extension_materialization_report(
        materialization,
        output_dir=output_dir,
        sft_rows=[row.to_dict() for row in candidate_sft_rows],
    )
    return {"seed": seed_output_path, **paths}


def form_fill_remediation_candidate_integration_preview_evidence(
    *,
    formal_manifest: dict[str, Any],
    formal_seed_path: Path,
    preview_manifest: DatasetManifest,
    candidate_seed_path: Path,
    preview_seed_path: Path,
    validation: Any,
    formal_seed_rows: list[dict[str, Any]],
    candidate_seed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_sft_rows = preview_manifest.counts["sft_rows"] - int(
        formal_manifest["counts"]["sft_rows"]
    )
    candidate_dpo_pairs = preview_manifest.counts["dpo_pairs"] - int(
        formal_manifest["counts"]["dpo_pairs"]
    )
    return {
        "evidence_kind": "form_fill_remediation_candidate_integration_preview",
        "integration_status": "preview_build_validated" if validation.ok else "preview_build_validation_failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "formal_public_sample_counts_before": formal_manifest["counts"],
        "formal_public_sample_split_counts_before": formal_manifest["split_counts"],
        "preview_counts": preview_manifest.counts,
        "preview_split_counts": preview_manifest.split_counts,
        "candidate_source": {
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "candidate_seed_rows": len(candidate_seed_rows),
            "candidate_sft_rows": candidate_sft_rows,
            "candidate_preview_dpo_pairs": candidate_dpo_pairs,
            "candidate_ids": sorted(row["id"] for row in candidate_seed_rows),
        },
        "preview_artifacts": {
            "preview_seed": _safe_artifact_ref(preview_seed_path),
            "preview_sft": "public-sample-preview/sft_public_sample.jsonl",
            "preview_dpo": "public-sample-preview/dpo_public_sample.jsonl",
            "preview_manifest": "public-sample-preview/manifest_public_sample.json",
        },
        "validation": {
            "ok": validation.ok,
            "failures": validation.failures,
            "counts": validation.counts,
        },
        "execution_scope": {
            "formal_public_sample_modified": False,
            "preview_public_sample_generated": True,
            "preview_dpo_pairs_generated": True,
            "seed_traces_modified": False,
            "training_run": False,
            "prediction_run": False,
            "dpo_training_run": False,
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
            "formal_seed": _safe_artifact_ref(formal_seed_path),
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "preview_seed": _safe_artifact_ref(preview_seed_path),
            "preview_sft": "public-sample-preview/sft_public_sample.jsonl",
            "preview_dpo": "public-sample-preview/dpo_public_sample.jsonl",
            "preview_manifest": "public-sample-preview/manifest_public_sample.json",
            "integration_json": "form_fill_remediation_candidate_integration_preview.json",
            "integration_markdown": "form_fill_remediation_candidate_integration_preview.md",
            "manifest": "manifest.json",
        },
        "formal_seed_id_count_before": len({row["id"] for row in formal_seed_rows}),
    }


def check_form_fill_remediation_candidate_integration_preview(
    *,
    candidate_seed_path: Path,
    seed_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Build a report-scoped preview dataset with form-fill remediation candidates."""

    from voice2task.validation import validate_dataset_artifacts

    formal_seed_rows = _read_seed_rows(seed_path)
    candidate_seed_rows = read_jsonl(candidate_seed_path)
    _validate_reviewed_form_fill_remediation_candidate_seed_rows(candidate_seed_rows)
    formal_ids = {str(row["id"]) for row in formal_seed_rows}
    duplicate_ids = sorted(formal_ids & {str(row["id"]) for row in candidate_seed_rows})
    if duplicate_ids:
        raise ValueError(f"form-fill remediation candidate IDs already exist in formal public seed: {duplicate_ids}")

    preview_dir = output_dir / "public-sample-preview"
    preview_seed_path = preview_dir / "seed_traces.jsonl"
    preview_seed_rows = [
        *formal_seed_rows,
        *[
            _form_fill_remediation_preview_seed(row, candidate_seed_path=candidate_seed_path)
            for row in candidate_seed_rows
        ],
    ]
    write_jsonl(preview_seed_path, preview_seed_rows)
    preview_manifest = build_public_sample_dataset(seed_path=preview_seed_path, output_dir=preview_dir)
    validation = validate_dataset_artifacts(
        sft_path=preview_dir / "sft_public_sample.jsonl",
        dpo_path=preview_dir / "dpo_public_sample.jsonl",
        manifest_path=preview_dir / "manifest_public_sample.json",
        public=True,
    )

    formal_sft_rows = expand_sft_rows(formal_seed_rows, public_safe=True)
    formal_dpo_pairs = generate_hard_negative_pairs(formal_sft_rows)
    formal_manifest = {
        "counts": {
            "seed_rows": len(formal_seed_rows),
            "sft_rows": len(formal_sft_rows),
            "dpo_pairs": len(formal_dpo_pairs),
        },
        "split_counts": _split_counts(formal_sft_rows),
    }
    evidence = form_fill_remediation_candidate_integration_preview_evidence(
        formal_manifest=formal_manifest,
        formal_seed_path=seed_path,
        preview_manifest=preview_manifest,
        candidate_seed_path=candidate_seed_path,
        preview_seed_path=preview_seed_path,
        validation=validation,
        formal_seed_rows=formal_seed_rows,
        candidate_seed_rows=candidate_seed_rows,
    )

    from voice2task.reports import write_form_fill_remediation_candidate_integration_preview_report

    paths = write_form_fill_remediation_candidate_integration_preview_report(evidence, output_dir=output_dir)
    return {
        "preview_seed": preview_seed_path,
        "preview_sft": preview_dir / "sft_public_sample.jsonl",
        "preview_dpo": preview_dir / "dpo_public_sample.jsonl",
        "preview_manifest": preview_dir / "manifest_public_sample.json",
        **paths,
    }


def form_fill_confirmation_marker_extension_candidate_integration_preview_evidence(
    *,
    formal_manifest: dict[str, Any],
    formal_seed_path: Path,
    preview_manifest: DatasetManifest,
    candidate_seed_path: Path,
    preview_seed_path: Path,
    validation: Any,
    formal_seed_rows: list[dict[str, Any]],
    candidate_seed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_sft_rows = preview_manifest.counts["sft_rows"] - int(formal_manifest["counts"]["sft_rows"])
    candidate_dpo_pairs = preview_manifest.counts["dpo_pairs"] - int(formal_manifest["counts"]["dpo_pairs"])
    return {
        "evidence_kind": "form_fill_confirmation_marker_extension_candidate_integration_preview",
        "integration_status": "preview_build_validated" if validation.ok else "preview_build_validation_failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "formal_public_sample_counts_before": formal_manifest["counts"],
        "formal_public_sample_split_counts_before": formal_manifest["split_counts"],
        "preview_counts": preview_manifest.counts,
        "preview_split_counts": preview_manifest.split_counts,
        "candidate_source": {
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "candidate_seed_rows": len(candidate_seed_rows),
            "candidate_sft_rows": candidate_sft_rows,
            "candidate_preview_dpo_pairs": candidate_dpo_pairs,
            "candidate_ids": sorted(row["id"] for row in candidate_seed_rows),
            "candidate_source_mode": "form_fill_confirmation_marker_extension_candidate_seed",
            "preview_source_mode": "form_fill_confirmation_marker_extension_preview_public_seed",
        },
        "preview_artifacts": {
            "preview_seed": _safe_artifact_ref(preview_seed_path),
            "preview_sft": "public-sample-preview/sft_public_sample.jsonl",
            "preview_dpo": "public-sample-preview/dpo_public_sample.jsonl",
            "preview_manifest": "public-sample-preview/manifest_public_sample.json",
        },
        "validation": {
            "ok": validation.ok,
            "failures": validation.failures,
            "counts": validation.counts,
        },
        "execution_scope": {
            "formal_public_sample_modified": False,
            "preview_only_not_formal_public_sample": True,
            "preview_public_sample_generated": True,
            "preview_dpo_pairs_generated": True,
            "seed_traces_modified": False,
            "training_run": False,
            "prediction_run": False,
            "dpo_training_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "strict_slot_f1_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_recovery_claim": False,
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
            "formal_seed": _safe_artifact_ref(formal_seed_path),
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "preview_seed": _safe_artifact_ref(preview_seed_path),
            "preview_sft": "public-sample-preview/sft_public_sample.jsonl",
            "preview_dpo": "public-sample-preview/dpo_public_sample.jsonl",
            "preview_manifest": "public-sample-preview/manifest_public_sample.json",
            "integration_json": "form_fill_confirmation_marker_extension_candidate_integration_preview.json",
            "integration_markdown": "form_fill_confirmation_marker_extension_candidate_integration_preview.md",
            "manifest": "manifest.json",
        },
        "formal_seed_id_count_before": len({row["id"] for row in formal_seed_rows}),
    }


def check_form_fill_confirmation_marker_extension_candidate_integration_preview(
    *,
    candidate_seed_path: Path,
    seed_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Build a report-scoped preview dataset with confirmation-marker extension candidates."""

    from voice2task.validation import validate_dataset_artifacts

    formal_seed_rows = _read_seed_rows(seed_path)
    candidate_seed_rows = read_jsonl(candidate_seed_path)
    _validate_reviewed_form_fill_confirmation_marker_extension_candidate_seed_rows(candidate_seed_rows)
    formal_ids = {str(row["id"]) for row in formal_seed_rows}
    duplicate_ids = sorted(formal_ids & {str(row["id"]) for row in candidate_seed_rows})
    if duplicate_ids:
        raise ValueError(
            "form-fill confirmation-marker extension candidate IDs already exist in formal public seed: "
            f"{duplicate_ids}"
        )

    preview_dir = output_dir / "public-sample-preview"
    preview_seed_path = preview_dir / "seed_traces.jsonl"
    preview_seed_rows = [
        *formal_seed_rows,
        *[
            _form_fill_confirmation_marker_extension_preview_seed(
                row,
                candidate_seed_path=candidate_seed_path,
            )
            for row in candidate_seed_rows
        ],
    ]
    write_jsonl(preview_seed_path, preview_seed_rows)
    preview_manifest = build_public_sample_dataset(seed_path=preview_seed_path, output_dir=preview_dir)
    validation = validate_dataset_artifacts(
        sft_path=preview_dir / "sft_public_sample.jsonl",
        dpo_path=preview_dir / "dpo_public_sample.jsonl",
        manifest_path=preview_dir / "manifest_public_sample.json",
        public=True,
    )

    formal_sft_rows = expand_sft_rows(formal_seed_rows, public_safe=True)
    formal_dpo_pairs = generate_hard_negative_pairs(formal_sft_rows)
    formal_manifest = {
        "counts": {
            "seed_rows": len(formal_seed_rows),
            "sft_rows": len(formal_sft_rows),
            "dpo_pairs": len(formal_dpo_pairs),
        },
        "split_counts": _split_counts(formal_sft_rows),
    }
    evidence = form_fill_confirmation_marker_extension_candidate_integration_preview_evidence(
        formal_manifest=formal_manifest,
        formal_seed_path=seed_path,
        preview_manifest=preview_manifest,
        candidate_seed_path=candidate_seed_path,
        preview_seed_path=preview_seed_path,
        validation=validation,
        formal_seed_rows=formal_seed_rows,
        candidate_seed_rows=candidate_seed_rows,
    )

    from voice2task.reports import (
        write_form_fill_confirmation_marker_extension_candidate_integration_preview_report,
    )

    paths = write_form_fill_confirmation_marker_extension_candidate_integration_preview_report(
        evidence,
        output_dir=output_dir,
    )
    return {
        "preview_seed": preview_seed_path,
        "preview_sft": preview_dir / "sft_public_sample.jsonl",
        "preview_dpo": preview_dir / "dpo_public_sample.jsonl",
        "preview_manifest": preview_dir / "manifest_public_sample.json",
        **paths,
    }


def merge_blocked_payment_safety_repair_candidates_into_public_sample(
    *,
    candidate_seed_path: Path,
    seed_path: Path,
    output_dir: Path,
) -> DatasetManifest:
    """Merge reviewed blocked-payment repair candidate seeds into the formal public sample."""

    seed_rows = _read_seed_rows(seed_path)
    candidate_seed_rows = read_jsonl(candidate_seed_path)
    _validate_reviewed_blocked_payment_safety_repair_candidate_seed_rows(candidate_seed_rows)
    existing_ids = {str(row["id"]) for row in seed_rows}
    duplicate_ids = sorted(str(row["id"]) for row in candidate_seed_rows if str(row["id"]) in existing_ids)
    if duplicate_ids:
        raise ValueError(
            "blocked-payment repair candidate seed IDs already exist in public sample: "
            f"{', '.join(duplicate_ids)}"
        )

    merged_candidates = [
        _formal_blocked_payment_safety_repair_candidate_seed(row, candidate_seed_path=candidate_seed_path)
        for row in candidate_seed_rows
    ]
    for row in merged_candidates:
        as_contract(row["target_contract"])

    seed_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(seed_path, [*seed_rows, *merged_candidates])
    return build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)


def merge_current_retry_confirmation_preservation_candidates_into_public_sample(
    *,
    candidate_seed_path: Path,
    seed_path: Path,
    output_dir: Path,
) -> DatasetManifest:
    """Merge reviewed current-retry confirmation-preservation candidate seeds into the formal public sample."""

    seed_rows = _read_seed_rows(seed_path)
    candidate_seed_rows = read_jsonl(candidate_seed_path)
    _validate_reviewed_current_retry_confirmation_preservation_candidate_seed_rows(candidate_seed_rows)
    existing_ids = {str(row["id"]) for row in seed_rows}
    duplicate_ids = sorted(str(row["id"]) for row in candidate_seed_rows if str(row["id"]) in existing_ids)
    if duplicate_ids:
        raise ValueError(
            "current-retry confirmation-preservation candidate seed IDs already exist in public sample: "
            f"{', '.join(duplicate_ids)}"
        )

    merged_candidates = [
        _formal_current_retry_confirmation_preservation_candidate_seed(
            row,
            candidate_seed_path=candidate_seed_path,
        )
        for row in candidate_seed_rows
    ]
    for row in merged_candidates:
        as_contract(row["target_contract"])

    seed_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(seed_path, [*seed_rows, *merged_candidates])
    return build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)


def merge_form_fill_remediation_candidates_into_public_sample(
    *,
    candidate_seed_path: Path,
    seed_path: Path,
    output_dir: Path,
) -> DatasetManifest:
    """Merge reviewed form-fill remediation candidate seeds into the formal public sample."""

    seed_rows = _read_seed_rows(seed_path)
    candidate_seed_rows = read_jsonl(candidate_seed_path)
    _validate_reviewed_form_fill_remediation_candidate_seed_rows(candidate_seed_rows)
    existing_ids = {str(row["id"]) for row in seed_rows}
    duplicate_ids = sorted(str(row["id"]) for row in candidate_seed_rows if str(row["id"]) in existing_ids)
    if duplicate_ids:
        raise ValueError(
            "form-fill remediation candidate seed IDs already exist in public sample: "
            f"{', '.join(duplicate_ids)}"
        )

    merged_candidates = [
        _formal_form_fill_remediation_candidate_seed(row, candidate_seed_path=candidate_seed_path)
        for row in candidate_seed_rows
    ]
    for row in merged_candidates:
        as_contract(row["target_contract"])

    seed_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(seed_path, [*seed_rows, *merged_candidates])
    return build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)


def merge_form_fill_confirmation_marker_extension_candidates_into_public_sample(
    *,
    candidate_seed_path: Path,
    seed_path: Path,
    output_dir: Path,
) -> DatasetManifest:
    """Merge reviewed confirmation-marker extension candidate seeds into the formal public sample."""

    seed_rows = _read_seed_rows(seed_path)
    candidate_seed_rows = read_jsonl(candidate_seed_path)
    _validate_reviewed_form_fill_confirmation_marker_extension_candidate_seed_rows(candidate_seed_rows)
    existing_ids = {str(row["id"]) for row in seed_rows}
    duplicate_ids = sorted(str(row["id"]) for row in candidate_seed_rows if str(row["id"]) in existing_ids)
    if duplicate_ids:
        raise ValueError(
            "form-fill confirmation-marker extension candidate seed IDs already exist in public sample: "
            f"{', '.join(duplicate_ids)}"
        )

    merged_candidates = [
        _formal_form_fill_confirmation_marker_extension_candidate_seed(
            row,
            candidate_seed_path=candidate_seed_path,
        )
        for row in candidate_seed_rows
    ]
    for row in merged_candidates:
        as_contract(row["target_contract"])

    seed_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(seed_path, [*seed_rows, *merged_candidates])
    return build_public_sample_dataset(seed_path=seed_path, output_dir=output_dir)


def blocked_payment_safety_repair_public_sample_merge_evidence(
    *,
    manifest: DatasetManifest,
    candidate_seed_path: Path,
    pre_merge_manifest: dict[str, Any],
) -> dict[str, Any]:
    from voice2task.validation import validate_dataset_artifacts

    source_summary = manifest.source_summary
    candidate_seed_rows = int(source_summary.get("blocked_payment_safety_repair_candidate_seed_rows", 0))
    candidate_sft_rows = int(source_summary.get("blocked_payment_safety_repair_candidate_sft_rows", 0))
    pre_counts = dict(pre_merge_manifest.get("counts") or {})
    pre_rejections = dict(pre_merge_manifest.get("dpo_rejection_counts") or {})
    post_rejections = manifest.dpo_rejection_counts
    rejection_deltas = {
        key: int(post_rejections.get(key, 0)) - int(pre_rejections.get(key, 0))
        for key in sorted(set(pre_rejections) | set(post_rejections))
        if int(post_rejections.get(key, 0)) - int(pre_rejections.get(key, 0)) != 0
    }
    validation = validate_dataset_artifacts(
        sft_path=Path(manifest.files["sft"]),
        dpo_path=Path(manifest.files["dpo"]),
        manifest_path=Path(manifest.files["manifest"]),
        public=True,
    )
    return {
        "evidence_kind": "blocked_payment_safety_repair_public_sample_merge",
        "merge_status": "formal_public_sample_rebuilt" if validation.ok else "formal_public_sample_validation_failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pre_merge_public_sample_counts": pre_counts,
        "pre_merge_public_sample_dpo_rejection_counts": pre_rejections,
        "formal_public_sample_counts": manifest.counts,
        "formal_public_sample_split_counts": manifest.split_counts,
        "formal_public_sample_dpo_rejection_counts": manifest.dpo_rejection_counts,
        "source_summary": source_summary,
        "candidate_source": {
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "candidate_seed_rows": candidate_seed_rows,
            "candidate_sft_rows": candidate_sft_rows,
            "candidate_dpo_pairs": manifest.counts["dpo_pairs"] - int(pre_counts.get("dpo_pairs", 0)),
            "candidate_source_mode": "blocked_payment_safety_repair_candidate_seed",
            "formal_source_mode": "blocked_payment_safety_repair_formal_public_seed",
            "repair_families": source_summary.get("blocked_payment_safety_repair_families", []),
            "seed_split_counts": source_summary.get(
                "blocked_payment_safety_repair_seed_split_counts",
                {"train": candidate_seed_rows, "dev": 0, "test": 0},
            ),
            "dpo_rejection_deltas": rejection_deltas,
        },
        "validation": {
            "ok": validation.ok,
            "failures": validation.failures,
            "counts": validation.counts,
        },
        "metric_authority": {
            "contract_evaluation_ladder": "authoritative",
            "contract_exact_match": "authoritative_strict_metric",
            "slot_f1": "authoritative_strict_metric",
            "slot_f1_soft": "diagnostic_only_not_primary",
        },
        "execution_scope": {
            "formal_public_sample_modified": True,
            "seed_traces_modified": True,
            "sft_artifacts_rebuilt": True,
            "dpo_artifacts_rebuilt": True,
            "training_run": False,
            "sft_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
            "semantic_equivalence_scoring": False,
            "prediction_repair": False,
            "prediction_replacement": False,
            "prompt_change": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "strict_slot_f1_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_recovery_claim": False,
            "held_out_generalization_recovered": False,
            "model_quality_claim": False,
            "model_recovery_claim": False,
            "safety_improvement_claim": False,
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
            "merge_json": "blocked_payment_safety_repair_public_sample_merge.json",
            "merge_markdown": "blocked_payment_safety_repair_public_sample_merge.md",
            "merge_manifest": "manifest.json",
        },
        "recommended_next_step": "run_prediction_only_eval_against_the_new_manifest_in_a_later_phase",
    }


def current_retry_confirmation_preservation_public_sample_merge_evidence(
    *,
    manifest: DatasetManifest,
    candidate_seed_path: Path,
    pre_merge_manifest: dict[str, Any],
) -> dict[str, Any]:
    from voice2task.validation import validate_dataset_artifacts

    source_summary = manifest.source_summary
    candidate_seed_rows = int(
        source_summary.get("current_retry_confirmation_preservation_candidate_seed_rows", 0)
    )
    candidate_sft_rows = int(source_summary.get("current_retry_confirmation_preservation_candidate_sft_rows", 0))
    pre_counts = dict(pre_merge_manifest.get("counts") or {})
    pre_rejections = dict(pre_merge_manifest.get("dpo_rejection_counts") or {})
    post_rejections = manifest.dpo_rejection_counts
    rejection_deltas = {
        key: int(post_rejections.get(key, 0)) - int(pre_rejections.get(key, 0))
        for key in sorted(set(pre_rejections) | set(post_rejections))
        if int(post_rejections.get(key, 0)) - int(pre_rejections.get(key, 0)) != 0
    }
    validation = validate_dataset_artifacts(
        sft_path=Path(manifest.files["sft"]),
        dpo_path=Path(manifest.files["dpo"]),
        manifest_path=Path(manifest.files["manifest"]),
        public=True,
    )
    return {
        "evidence_kind": "current_retry_confirmation_preservation_public_sample_merge",
        "merge_status": "formal_public_sample_rebuilt" if validation.ok else "formal_public_sample_validation_failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pre_merge_public_sample_counts": pre_counts,
        "pre_merge_public_sample_dpo_rejection_counts": pre_rejections,
        "formal_public_sample_counts": manifest.counts,
        "formal_public_sample_split_counts": manifest.split_counts,
        "formal_public_sample_dpo_rejection_counts": manifest.dpo_rejection_counts,
        "source_summary": source_summary,
        "candidate_source": {
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "candidate_seed_rows": candidate_seed_rows,
            "candidate_sft_rows": candidate_sft_rows,
            "candidate_dpo_pairs": manifest.counts["dpo_pairs"] - int(pre_counts.get("dpo_pairs", 0)),
            "candidate_source_mode": "current_retry_confirmation_preservation_candidate_seed",
            "formal_source_mode": "current_retry_confirmation_preservation_formal_public_seed",
            "candidate_families": source_summary.get("current_retry_confirmation_preservation_families", []),
            "seed_split_counts": source_summary.get(
                "current_retry_confirmation_preservation_seed_split_counts",
                {"train": candidate_seed_rows, "dev": 0, "test": 0},
            ),
            "dpo_rejection_deltas": rejection_deltas,
        },
        "validation": {
            "ok": validation.ok,
            "failures": validation.failures,
            "counts": validation.counts,
        },
        "metric_authority": {
            "contract_evaluation_ladder": "authoritative",
            "contract_exact_match": "authoritative_strict_metric",
            "slot_f1": "authoritative_strict_metric",
            "slot_f1_soft": "diagnostic_only_not_primary",
        },
        "execution_scope": {
            "formal_public_sample_modified": True,
            "seed_traces_modified": True,
            "sft_artifacts_rebuilt": True,
            "dpo_artifacts_rebuilt": True,
            "training_run": False,
            "sft_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
            "semantic_equivalence_scoring": False,
            "prediction_repair": False,
            "prediction_replacement": False,
            "prompt_change": False,
            "slot_normalization": False,
            "adapter_release": False,
            "checkpoint_release": False,
            "private_corpus_publication": False,
            "live_browser_benchmark": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "strict_slot_f1_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_recovery_claim": False,
            "held_out_generalization_recovered": False,
            "model_quality_claim": False,
            "model_recovery_claim": False,
            "safety_improvement_claim": False,
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
            "merge_json": "current_retry_confirmation_preservation_public_sample_merge.json",
            "merge_markdown": "current_retry_confirmation_preservation_public_sample_merge.md",
            "merge_manifest": "manifest.json",
        },
        "recommended_next_step": "run_prediction_only_eval_against_the_new_manifest_in_a_later_phase",
    }


def form_fill_remediation_public_sample_merge_evidence(
    *,
    manifest: DatasetManifest,
    candidate_seed_path: Path,
) -> dict[str, Any]:
    source_summary = manifest.source_summary
    candidate_seed_rows = int(source_summary.get("form_fill_remediation_candidate_seed_rows", 0))
    candidate_sft_rows = int(source_summary.get("form_fill_remediation_candidate_sft_rows", 0))
    candidate_dpo_pairs = candidate_sft_rows * len(FORM_FILL_REMEDIATION_DPO_REJECTION_CATEGORIES)
    return {
        "evidence_kind": "form_fill_remediation_public_sample_merge",
        "merge_status": "formal_public_sample_rebuilt",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "formal_public_sample_counts": manifest.counts,
        "formal_public_sample_split_counts": manifest.split_counts,
        "source_summary": source_summary,
        "candidate_source": {
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "candidate_seed_rows": candidate_seed_rows,
            "candidate_sft_rows": candidate_sft_rows,
            "candidate_dpo_pairs": candidate_dpo_pairs,
            "source_case_groups": source_summary.get("form_fill_remediation_source_case_groups", []),
            "seed_split_counts": {"train": candidate_seed_rows, "dev": 0, "test": 0},
            "dpo_rejection_deltas": {
                category: candidate_sft_rows for category in FORM_FILL_REMEDIATION_DPO_REJECTION_CATEGORIES
            },
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
            "merge_json": "form_fill_remediation_public_sample_merge.json",
            "merge_markdown": "form_fill_remediation_public_sample_merge.md",
            "merge_manifest": "manifest.json",
        },
        "recommended_next_step": "run_prediction_only_eval_against_the_new_manifest_in_a_later_phase",
    }


def form_fill_confirmation_marker_extension_public_sample_merge_evidence(
    *,
    manifest: DatasetManifest,
    candidate_seed_path: Path,
    pre_merge_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    from voice2task.validation import validate_dataset_artifacts

    source_summary = manifest.source_summary
    candidate_seed_rows = int(
        source_summary.get("form_fill_confirmation_marker_extension_candidate_seed_rows", 0)
    )
    candidate_sft_rows = int(source_summary.get("form_fill_confirmation_marker_extension_candidate_sft_rows", 0))
    candidate_dpo_pairs = candidate_sft_rows * len(FORM_FILL_REMEDIATION_DPO_REJECTION_CATEGORIES)
    if pre_merge_counts is None:
        pre_merge_counts = {
            "seed_rows": manifest.counts["seed_rows"] - candidate_seed_rows,
            "sft_rows": manifest.counts["sft_rows"] - candidate_sft_rows,
            "dpo_pairs": manifest.counts["dpo_pairs"] - candidate_dpo_pairs,
        }
    validation = validate_dataset_artifacts(
        sft_path=Path(manifest.files["sft"]),
        dpo_path=Path(manifest.files["dpo"]),
        manifest_path=Path(manifest.files["manifest"]),
        public=True,
    )
    return {
        "evidence_kind": "form_fill_confirmation_marker_extension_public_sample_merge",
        "merge_status": "formal_public_sample_rebuilt" if validation.ok else "formal_public_sample_validation_failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pre_merge_public_sample_counts": pre_merge_counts,
        "formal_public_sample_counts": manifest.counts,
        "formal_public_sample_split_counts": manifest.split_counts,
        "source_summary": source_summary,
        "candidate_source": {
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "candidate_seed_rows": candidate_seed_rows,
            "candidate_sft_rows": candidate_sft_rows,
            "candidate_dpo_pairs": candidate_dpo_pairs,
            "candidate_source_mode": "form_fill_confirmation_marker_extension_candidate_seed",
            "formal_source_mode": "form_fill_confirmation_marker_extension_formal_public_seed",
            "source_family_ids": source_summary.get(
                "form_fill_confirmation_marker_extension_source_family_ids",
                [],
            ),
            "seed_split_counts": source_summary.get(
                "form_fill_confirmation_marker_extension_seed_split_counts",
                {"train": candidate_seed_rows, "dev": 0, "test": 0},
            ),
            "dpo_rejection_deltas": {
                category: candidate_sft_rows for category in FORM_FILL_REMEDIATION_DPO_REJECTION_CATEGORIES
            },
        },
        "validation": {
            "ok": validation.ok,
            "failures": validation.failures,
            "counts": validation.counts,
        },
        "metric_authority": {
            "contract_evaluation_ladder": "authoritative",
            "contract_exact_match": "authoritative_strict_metric",
            "slot_f1": "authoritative_strict_metric",
            "slot_f1_soft": "diagnostic_only_not_primary",
        },
        "execution_scope": {
            "formal_public_sample_modified": True,
            "sft_artifacts_rebuilt": True,
            "dpo_artifacts_rebuilt": True,
            "training_run": False,
            "prediction_run": False,
            "dpo_training_run": False,
            "a100_execution": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "strict_slot_f1_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_recovery_claim": False,
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
            "seed": _safe_artifact_ref(Path(manifest.files["seed"])),
            "sft": _safe_artifact_ref(Path(manifest.files["sft"])),
            "dpo": _safe_artifact_ref(Path(manifest.files["dpo"])),
            "manifest": _safe_artifact_ref(Path(manifest.files["manifest"])),
            "merge_json": "form_fill_confirmation_marker_extension_public_sample_merge.json",
            "merge_markdown": "form_fill_confirmation_marker_extension_public_sample_merge.md",
            "merge_manifest": "manifest.json",
        },
        "recommended_next_step": "run_prediction_only_eval_against_the_new_manifest_in_a_later_phase",
    }


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
    form_fill_remediation_seed_count = _form_fill_remediation_formal_seed_count(seed_rows)
    confirmation_marker_extension_seed_count = (
        _form_fill_confirmation_marker_extension_formal_seed_count(seed_rows)
    )
    blocked_payment_repair_seed_count = _blocked_payment_safety_repair_formal_seed_count(seed_rows)
    current_retry_confirmation_preservation_seed_count = (
        _current_retry_confirmation_preservation_formal_seed_count(seed_rows)
    )
    scaled_public_sample_seed_count = _scaled_public_sample_formal_seed_count(seed_rows)
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
    if form_fill_remediation_seed_count:
        source_summary.update(
            {
                "form_fill_remediation_candidate_seed_rows": form_fill_remediation_seed_count,
                "form_fill_remediation_candidate_sft_rows": _form_fill_remediation_formal_sft_count(rows),
                "form_fill_remediation_candidates_formal_public_sample": True,
                "form_fill_remediation_source_case_groups": _form_fill_remediation_formal_source_case_groups(
                    seed_rows
                ),
            }
        )
    if confirmation_marker_extension_seed_count:
        source_summary.update(
            {
                "form_fill_confirmation_marker_extension_candidate_seed_rows": (
                    confirmation_marker_extension_seed_count
                ),
                "form_fill_confirmation_marker_extension_candidate_sft_rows": (
                    _form_fill_confirmation_marker_extension_formal_sft_count(rows)
                ),
                "form_fill_confirmation_marker_extension_candidates_formal_public_sample": True,
                "form_fill_confirmation_marker_extension_source_family_ids": (
                    _form_fill_confirmation_marker_extension_formal_source_family_ids(seed_rows)
                ),
                "form_fill_confirmation_marker_extension_seed_split_counts": (
                    _form_fill_confirmation_marker_extension_formal_seed_split_counts(seed_rows)
                ),
            }
        )
    if blocked_payment_repair_seed_count:
        source_summary.update(
            {
                "blocked_payment_safety_repair_candidate_seed_rows": blocked_payment_repair_seed_count,
                "blocked_payment_safety_repair_candidate_sft_rows": (
                    _blocked_payment_safety_repair_formal_sft_count(rows)
                ),
                "blocked_payment_safety_repair_candidates_formal_public_sample": True,
                "blocked_payment_safety_repair_families": (
                    _blocked_payment_safety_repair_formal_families(seed_rows)
                ),
                "blocked_payment_safety_repair_seed_split_counts": (
                    _blocked_payment_safety_repair_formal_seed_split_counts(seed_rows)
                ),
            }
        )
    if current_retry_confirmation_preservation_seed_count:
        source_summary.update(
            {
                "current_retry_confirmation_preservation_candidate_seed_rows": (
                    current_retry_confirmation_preservation_seed_count
                ),
                "current_retry_confirmation_preservation_candidate_sft_rows": (
                    _current_retry_confirmation_preservation_formal_sft_count(rows)
                ),
                "current_retry_confirmation_preservation_candidates_formal_public_sample": True,
                "current_retry_confirmation_preservation_families": (
                    _current_retry_confirmation_preservation_formal_families(seed_rows)
                ),
                "current_retry_confirmation_preservation_seed_split_counts": (
                    _current_retry_confirmation_preservation_formal_seed_split_counts(seed_rows)
                ),
            }
        )
    if scaled_public_sample_seed_count:
        source_summary.update(
            {
                "scaled_public_sample_candidate_seed_rows": scaled_public_sample_seed_count,
                "scaled_public_sample_candidate_sft_rows": _scaled_public_sample_formal_sft_count(rows),
                "scaled_public_sample_candidates_formal_public_sample": True,
                "scaled_public_sample_seed_split_counts": _scaled_public_sample_formal_seed_split_counts(
                    seed_rows
                ),
                "scaled_public_sample_candidate_group_counts": (
                    _scaled_public_sample_formal_candidate_group_counts(seed_rows)
                ),
                "scaled_public_sample_family_counts": _scaled_public_sample_formal_family_counts(seed_rows),
                "comparison_boundary_changed": True,
                "comparison_boundary_warning": (
                    "formal public sample boundary changed; old metrics are not directly comparable"
                ),
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


def merge_scaled_public_sample_candidates_into_public_sample(
    *,
    candidate_seed_path: Path,
    seed_path: Path,
    output_dir: Path,
) -> DatasetManifest:
    """Merge reviewed scaled public-sample candidates into the formal public sample."""

    seed_rows = _read_seed_rows(seed_path)
    candidate_seed_rows = read_jsonl(candidate_seed_path)
    _validate_reviewed_scaled_public_sample_candidate_seed_rows(candidate_seed_rows)
    existing_ids = {str(row["id"]) for row in seed_rows}
    duplicate_ids = sorted(str(row["id"]) for row in candidate_seed_rows if str(row["id"]) in existing_ids)
    if duplicate_ids:
        raise ValueError(
            "scaled public-sample candidate seed IDs already exist in public sample: "
            f"{', '.join(duplicate_ids)}"
        )

    merged_candidates = [
        _formal_scaled_public_sample_candidate_seed(row, candidate_seed_path=candidate_seed_path)
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


def scaled_public_sample_public_sample_merge_evidence(
    *,
    manifest: DatasetManifest,
    candidate_seed_path: Path,
    pre_merge_manifest: dict[str, Any],
) -> dict[str, Any]:
    from voice2task.validation import validate_dataset_artifacts

    source_summary = manifest.source_summary
    candidate_seed_rows = int(source_summary.get("scaled_public_sample_candidate_seed_rows", 0))
    candidate_sft_rows = int(source_summary.get("scaled_public_sample_candidate_sft_rows", 0))
    pre_counts = dict(pre_merge_manifest.get("counts") or {})
    pre_rejections = dict(pre_merge_manifest.get("dpo_rejection_counts") or {})
    post_rejections = manifest.dpo_rejection_counts
    rejection_deltas = {
        key: int(post_rejections.get(key, 0)) - int(pre_rejections.get(key, 0))
        for key in HARD_NEGATIVE_CATEGORIES
    }
    validation = validate_dataset_artifacts(
        sft_path=Path(manifest.files["sft"]),
        dpo_path=Path(manifest.files["dpo"]),
        manifest_path=Path(manifest.files["manifest"]),
        public=True,
    )
    return {
        "evidence_kind": "scaled_public_sample_public_sample_merge",
        "merge_status": "formal_public_sample_rebuilt" if validation.ok else "formal_public_sample_validation_failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pre_merge_public_sample_counts": pre_counts,
        "pre_merge_public_sample_split_counts": dict(pre_merge_manifest.get("split_counts") or {}),
        "pre_merge_public_sample_dpo_rejection_counts": pre_rejections,
        "formal_public_sample_counts": manifest.counts,
        "formal_public_sample_split_counts": manifest.split_counts,
        "formal_public_sample_dpo_rejection_counts": manifest.dpo_rejection_counts,
        "source_summary": source_summary,
        "candidate_source": {
            "candidate_seed": _safe_artifact_ref(candidate_seed_path),
            "candidate_seed_rows": candidate_seed_rows,
            "candidate_sft_rows": candidate_sft_rows,
            "candidate_dpo_pairs": manifest.counts["dpo_pairs"] - int(pre_counts.get("dpo_pairs", 0)),
            "candidate_source_mode": "scaled_public_sample_candidate_seed",
            "formal_source_mode": "scaled_public_sample_formal_public_seed",
            "seed_split_counts": source_summary.get("scaled_public_sample_seed_split_counts", {}),
            "candidate_group_counts": source_summary.get("scaled_public_sample_candidate_group_counts", {}),
            "family_counts": source_summary.get("scaled_public_sample_family_counts", {}),
            "dpo_rejection_deltas": rejection_deltas,
        },
        "validation": {
            "ok": validation.ok,
            "failures": validation.failures,
            "counts": validation.counts,
        },
        "comparison_boundary": {
            "changed": True,
            "previous_manifest_id": pre_merge_manifest.get("manifest_id"),
            "new_manifest_id": manifest.manifest_id,
            "warning": "formal public sample boundary changed; old metrics are not directly comparable",
            "old_metrics_directly_comparable": False,
        },
        "metric_authority": {
            "contract_evaluation_ladder": "authoritative",
            "contract_exact_match": "authoritative_strict_metric",
            "slot_f1": "authoritative_strict_metric",
            "slot_f1_soft": "diagnostic_only_not_primary",
        },
        "execution_scope": {
            "formal_public_sample_modified": True,
            "seed_traces_modified": True,
            "sft_artifacts_rebuilt": True,
            "dpo_artifacts_rebuilt": True,
            "manifest_rebuilt": True,
            "training_run": False,
            "sft_run": False,
            "dpo_run": False,
            "grpo_run": False,
            "prediction_run": False,
            "a100_execution": False,
            "prompt_change": False,
            "evaluator_metric_change": False,
            "evaluator_relaxation": False,
            "semantic_equivalence_scoring": False,
            "prediction_repair": False,
            "prediction_replacement": False,
            "slot_normalization": False,
            "adapter_release": False,
            "checkpoint_release": False,
            "private_corpus_publication": False,
            "live_browser_benchmark": False,
        },
        "claims": {
            "strict_contract_exact_match_primary_metric": True,
            "strict_slot_f1_primary_metric": True,
            "soft_slot_f1_primary_metric": False,
            "semantic_equivalence_primary_metric": False,
            "held_out_recovery_claim": False,
            "held_out_generalization_recovered": False,
            "model_quality_claim": False,
            "model_recovery_claim": False,
            "safety_improvement_claim": False,
            "checkpoint_release": False,
            "adapter_release": False,
            "production_readiness_claim": False,
            "private_corpus_generalization_claim": False,
            "public_full_corpus_release_claim": False,
            "live_browser_benchmark_claim": False,
        },
        "artifact_files": {
            "seed": _safe_artifact_ref(Path(manifest.files["seed"])),
            "sft": _safe_artifact_ref(Path(manifest.files["sft"])),
            "dpo": _safe_artifact_ref(Path(manifest.files["dpo"])),
            "manifest": _safe_artifact_ref(Path(manifest.files["manifest"])),
            "merge_json": "scaled_public_sample_public_sample_merge.json",
            "merge_markdown": "scaled_public_sample_public_sample_merge.md",
            "merge_manifest": "manifest.json",
        },
        "recommended_next_step": "open_a_separate_prediction_only_eval_phase_on_the_new_manifest_boundary",
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
