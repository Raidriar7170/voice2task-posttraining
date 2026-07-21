from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import httpx
import pytest

from apps.api.sandbox import router as sandbox_router
from voice2task.runtime.capabilities import CAPABILITY_REGISTRY
from voice2task.runtime.compiler import compile_contract_to_plan
from voice2task.runtime.inference import FIXTURE_CONTRACTS
from voice2task.runtime.models import (
    BrowserTaskContractPayload,
    ExecutionEvidence,
    ExecutionOutcome,
    SessionContext,
)
from voice2task.runtime.verifier import verify_execution


def _context(session_id: str = "verify-session") -> SessionContext:
    return SessionContext(
        session_id=session_id,
        profile={"email": "demo@example.com"},
        plan_version=1,
        plan_issued_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )


def _compiled(utterance: str):
    contract = BrowserTaskContractPayload.model_validate(FIXTURE_CONTRACTS[utterance])
    result = compile_contract_to_plan(contract, _context())
    assert result.plan is not None
    return contract, result.plan


@pytest.mark.asyncio
async def test_four_sandbox_pages_are_deterministic_and_same_origin() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(sandbox_router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        search = await client.get("/sandbox/search", params={"q": "北京明天天气"})
        help_page = await client.get("/sandbox/help")
        product = await client.get("/sandbox/product")
        profile = await client.get("/sandbox/profile")

    assert 'data-testid="query-input"' in search.text
    assert "北京明天天气" in search.text
    assert 'action="/sandbox/search"' in search.text
    assert "Voice2Task 帮助中心" in help_page.text
    assert 'data-testid="product-price">¥199.00<' in product.text
    assert 'data-testid="email-input"' in profile.text
    for response in (search, help_page, product, profile):
        assert response.status_code == 200
        assert "https://" not in response.text
        assert "<script" not in response.text


@pytest.mark.parametrize(
    ("utterance", "outcome"),
    [
        (
            "帮我搜索北京明天的天气",
            ExecutionOutcome(
                browser_context_created=True,
                action_count=3,
                final_url_path="/sandbox/search",
                evidence=ExecutionEvidence(
                    dom_snapshot={
                        "query_input": "北京明天天气",
                        "results": "受控结果：北京明天天气",
                    }
                ),
            ),
        ),
        (
            "打开帮助中心",
            ExecutionOutcome(
                browser_context_created=True,
                action_count=1,
                final_url_path="/sandbox/help",
                evidence=ExecutionEvidence(
                    dom_snapshot={"heading": "Voice2Task 帮助中心"}
                ),
            ),
        ),
        (
            "帮我提取这个页面上的商品价格",
            ExecutionOutcome(
                browser_context_created=True,
                action_count=2,
                final_url_path="/sandbox/product",
                evidence=ExecutionEvidence(
                    action_outputs={"product_price": "¥199.00"},
                    dom_snapshot={"product_price": "¥199.00"},
                ),
            ),
        ),
        (
            "把邮箱填进表单里，提交前先问我",
            ExecutionOutcome(
                browser_context_created=True,
                action_count=2,
                final_url_path="/sandbox/profile",
                evidence=ExecutionEvidence(
                    dom_snapshot={"email_input": "demo@example.com"}
                ),
            ),
        ),
    ],
)
def test_verifier_passes_four_deterministic_executable_scenarios(
    utterance: str, outcome: ExecutionOutcome
) -> None:
    contract, plan = _compiled(utterance)

    result = verify_execution(plan, contract, _context(), outcome)

    assert result.passed is True
    assert result.checks
    assert all(check.passed for check in result.checks)


@pytest.mark.parametrize("utterance", ["帮我打开那个页面", "替我完成付款"])
def test_verifier_proves_blocked_and_clarify_never_created_browser(utterance: str) -> None:
    contract, plan = _compiled(utterance)

    result = verify_execution(
        plan,
        contract,
        _context(),
        ExecutionOutcome(browser_context_created=False, action_count=0),
    )

    assert result.passed is True
    assert result.checks[0].check_type.value == "no_execution"
    assert "browser_context_created=false" in result.checks[0].observed


def test_verifier_failure_is_not_repaired() -> None:
    contract, plan = _compiled("帮我搜索北京明天的天气")
    outcome = ExecutionOutcome(
        browser_context_created=True,
        action_count=3,
        final_url_path="/sandbox/search",
        evidence=ExecutionEvidence(
            dom_snapshot={"query_input": "错误值", "results": "错误结果"}
        ),
    )

    first = verify_execution(plan, contract, _context(), outcome)
    second = verify_execution(plan, contract, _context(), outcome)

    assert first == second
    assert first.passed is False
    assert first.failure_code == "VERIFICATION_FAILED"
    assert any(not check.passed for check in first.checks)


def test_extract_verifier_fails_when_action_output_differs_from_fresh_dom_snapshot() -> None:
    contract, plan = _compiled("帮我提取这个页面上的商品价格")
    outcome = ExecutionOutcome.model_validate(
        {
            "browser_context_created": True,
            "action_count": 2,
            "final_url_path": "/sandbox/product",
            "evidence": {
                "action_outputs": {"product_price": "¥198.00"},
                "dom_snapshot": {"product_price": "¥199.00"},
            },
        }
    )

    result = verify_execution(plan, contract, _context(), outcome)

    assert result.passed is False
    assert result.failure_code == "EXTRACT_EVIDENCE_MISMATCH"
    extract_check = result.checks[-2]
    assert extract_check.passed is False
    assert extract_check.expected == "¥199.00"
    assert extract_check.observed == "¥198.00"


@pytest.mark.parametrize(
    ("action_output", "dom_snapshot", "expected_failure_code"),
    [
        ("", "¥199.00", "EXTRACT_ACTION_OUTPUT_MISSING"),
        ("¥199.00", "", "EXTRACT_DOM_SNAPSHOT_MISSING"),
        ("¥199.00", "¥198.00", "EXTRACT_EVIDENCE_MISMATCH"),
        ("¥198.00", "¥198.00", "EXTRACT_EXPECTED_VALUE_MISMATCH"),
    ],
)
def test_extract_verifier_uses_deterministic_failure_code_precedence(
    action_output: str,
    dom_snapshot: str,
    expected_failure_code: str,
) -> None:
    contract, plan = _compiled("帮我提取这个页面上的商品价格")
    outcome = ExecutionOutcome(
        browser_context_created=True,
        action_count=2,
        final_url_path="/sandbox/product",
        evidence=ExecutionEvidence(
            action_outputs={"product_price": action_output} if action_output else {},
            dom_snapshot={"product_price": dom_snapshot} if dom_snapshot else {},
        ),
    )

    result = verify_execution(plan, contract, _context(), outcome)

    assert result.passed is False
    assert result.failure_code == expected_failure_code


def test_extract_verifier_uses_registry_expected_value_after_evidence_matches() -> None:
    contract, plan = _compiled("帮我提取这个页面上的商品价格")
    outcome = ExecutionOutcome(
        browser_context_created=True,
        action_count=2,
        final_url_path="/sandbox/product",
        evidence=ExecutionEvidence(
            action_outputs={"product_price": "¥199.00"},
            dom_snapshot={"product_price": "¥199.00"},
        ),
    )
    product = CAPABILITY_REGISTRY["demo_product"]

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setitem(
            CAPABILITY_REGISTRY,
            "demo_product",
            replace(product, expected_values={"product_price": "¥200.00"}),
        )
        result = verify_execution(plan, contract, _context(), outcome)

    assert result.passed is False
    assert result.failure_code == "EXTRACT_EXPECTED_VALUE_MISMATCH"
    assert result.checks[-1].expected == "¥200.00"
    assert result.checks[-1].observed == "¥199.00"


def test_extract_verifier_keeps_generic_code_for_non_evidence_failure() -> None:
    contract, plan = _compiled("帮我提取这个页面上的商品价格")
    outcome = ExecutionOutcome(
        browser_context_created=True,
        action_count=2,
        final_url_path="/sandbox/wrong-product",
        evidence=ExecutionEvidence(
            action_outputs={"product_price": "¥199.00"},
            dom_snapshot={"product_price": "¥199.00"},
        ),
    )

    result = verify_execution(plan, contract, _context(), outcome)

    assert result.passed is False
    assert result.failure_code == "VERIFICATION_FAILED"
