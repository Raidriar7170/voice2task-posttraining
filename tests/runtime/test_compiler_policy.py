from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from voice2task.runtime.capabilities import CAPABILITY_REGISTRY
from voice2task.runtime.compiler import compile_contract_to_plan
from voice2task.runtime.models import (
    BrowserTaskContractPayload,
    ExecutionAction,
    ExecutionPlan,
    SessionContext,
)
from voice2task.runtime.policy import evaluate_policy

ISSUED_AT = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)


def _context(capability: str | None = None) -> SessionContext:
    return SessionContext(
        session_id="session-compiler",
        profile={"email": "demo@example.com"},
        selected_capability=capability,
        plan_version=3,
        plan_issued_at=ISSUED_AT,
    )


def _contract(task_type: str, route: str, slots: dict[str, str]) -> BrowserTaskContractPayload:
    semantics = {
        "search": (True, "public_readonly", False),
        "navigate": (True, "public_readonly", False),
        "extract": (True, "public_readonly", False),
        "form_fill": (True, "requires_confirmation", True),
        "clarify": (True, "ambiguous_request", True),
        "blocked": (False, "unsafe_payment", True),
    }
    allow, reason, confirmation = semantics[task_type]
    return BrowserTaskContractPayload(
        task_type=task_type,
        route=route,
        safety={"allow": allow, "reason": reason},
        confirmation_required=confirmation,
        slots=slots,
        normalized_command=f"demo-{task_type}",
    )


def test_registry_contains_only_reviewed_capabilities_and_trusted_selectors() -> None:
    assert set(CAPABILITY_REGISTRY) == {
        "demo_search",
        "demo_help",
        "demo_product",
        "demo_profile_form",
    }
    assert CAPABILITY_REGISTRY["demo_search"].path == "/sandbox/search"
    assert CAPABILITY_REGISTRY["demo_profile_form"].requires_confirmation is True


@pytest.mark.parametrize(
    ("contract", "capability", "action_count", "outcome"),
    [
        (_contract("search", "search_web", {"query": "北京明天天气"}), "demo_search", 3, "ready"),
        (
            _contract("navigate", "open_url", {"url": "https://help.example.com"}),
            "demo_help",
            1,
            "ready",
        ),
        (_contract("extract", "extract_page", {"target": "商品价格"}), "demo_product", 2, "ready"),
        (
            _contract("form_fill", "fill_form", {"field": "邮箱"}),
            "demo_profile_form",
            2,
            "ready",
        ),
        (
            _contract(
                "clarify",
                "clarify",
                {"ambiguity": "目标不明确，未指定具体网站或页面"},
            ),
            None,
            0,
            "clarification_required",
        ),
        (
            _contract("blocked", "deny", {"reason": "payment_requires_user_control"}),
            None,
            0,
            "blocked",
        ),
    ],
)
def test_compiler_handles_six_contract_outcomes(
    contract: BrowserTaskContractPayload,
    capability: str | None,
    action_count: int,
    outcome: str,
) -> None:
    result = compile_contract_to_plan(contract, _context(capability))

    assert result.outcome == outcome
    assert result.plan is not None
    assert result.plan.capability_id == capability
    assert len(result.plan.actions) == action_count
    assert result.plan.expires_at == ISSUED_AT + timedelta(minutes=5)
    for action in result.plan.actions:
        assert not hasattr(action, "selector")
        assert not hasattr(action, "url")


def test_compiler_is_deterministic_and_discards_model_url_from_actions() -> None:
    contract = _contract("navigate", "open_url", {"url": "https://help.example.com"})

    first = compile_contract_to_plan(contract, _context("demo_help"))
    second = compile_contract_to_plan(contract, _context("demo_help"))

    assert first == second
    assert first.plan is not None
    assert first.plan.plan_id == second.plan.plan_id
    assert "help.example.com" not in first.plan.model_dump_json()


@pytest.mark.parametrize(
    "contract",
    [
        _contract("search", "search_web", {"query": ""}),
        _contract("search", "search_web", {"query": "北京明天天气", "city": "北京"}),
        _contract("navigate", "open_url", {"url": "https://evil.example"}),
        _contract("navigate", "open_url", {"url": "http://127.0.0.1/private"}),
        _contract("navigate", "open_url", {"url": "file:///private/demo"}),
        _contract("navigate", "open_url", {"url": "data:text/html,unsafe"}),
        _contract("navigate", "open_url", {"url": "javascript:alert(1)"}),
        _contract("extract", "extract_page", {"target": "任意内容"}),
        _contract("form_fill", "fill_form", {"field": "password"}),
    ],
)
def test_compiler_rejects_unknown_empty_or_extra_slots(contract: BrowserTaskContractPayload) -> None:
    result = compile_contract_to_plan(contract, _context())

    assert result.outcome == "rejected"
    assert result.plan is None
    assert result.reason_code in {
        "INVALID_SLOT_VALUE",
        "UNKNOWN_SLOT",
        "CAPABILITY_NOT_ALLOWLISTED",
    }


def test_policy_allows_read_only_requires_form_confirmation_and_blocks_no_execution() -> None:
    search = compile_contract_to_plan(
        _contract("search", "search_web", {"query": "北京明天天气"}), _context("demo_search")
    ).plan
    form = compile_contract_to_plan(
        _contract("form_fill", "fill_form", {"field": "邮箱"}), _context("demo_profile_form")
    ).plan
    blocked = compile_contract_to_plan(
        _contract("blocked", "deny", {"reason": "payment_requires_user_control"}), _context()
    ).plan
    assert search is not None and form is not None and blocked is not None

    search_policy = evaluate_policy(search, now=ISSUED_AT)
    form_policy = evaluate_policy(form, now=ISSUED_AT)
    confirmed_form_policy = evaluate_policy(form, now=ISSUED_AT, confirmation_consumed=True)
    blocked_policy = evaluate_policy(blocked, now=ISSUED_AT)

    assert (search_policy.allowed, search_policy.requires_confirmation) == (True, False)
    assert form_policy.allowed is False
    assert form_policy.reason_code == "CONFIRMATION_REQUIRED"
    assert confirmed_form_policy.allowed is True
    assert blocked_policy.allowed is False
    assert blocked_policy.reason_code == "UNSAFE_PAYMENT"


def test_policy_fails_closed_for_expired_unknown_or_unsafe_plan() -> None:
    valid_action = ExecutionAction(
        action_id="action-1",
        kind="navigate",
        capability_id="demo_search",
        timeout_ms=5000,
    )
    expired = ExecutionPlan(
        plan_id="expired-plan",
        session_id="session-policy",
        plan_version=1,
        route="search_web",
        capability_id="demo_search",
        requires_confirmation=False,
        actions=[valid_action],
        postconditions=[],
        expires_at=ISSUED_AT,
    )
    unknown = expired.model_copy(
        update={
            "plan_id": "unknown-plan",
            "capability_id": "unknown",
            "expires_at": ISSUED_AT + timedelta(minutes=5),
        }
    )
    unsafe = expired.model_copy(
        update={
            "plan_id": "unsafe-plan",
            "route": "javascript:alert(1)",
            "expires_at": ISSUED_AT + timedelta(minutes=5),
        }
    )

    assert evaluate_policy(expired, now=ISSUED_AT + timedelta(seconds=1)).reason_code == "PLAN_EXPIRED"
    assert evaluate_policy(unknown, now=ISSUED_AT).reason_code == "CAPABILITY_NOT_ALLOWLISTED"
    assert evaluate_policy(unsafe, now=ISSUED_AT).reason_code == "UNSAFE_ROUTE"
