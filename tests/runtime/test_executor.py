from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from playwright.async_api import Error as PlaywrightError

from voice2task.runtime.capabilities import CAPABILITY_REGISTRY
from voice2task.runtime.compiler import compile_contract_to_plan
from voice2task.runtime.executor import BrowserManager, ExecutorError, SandboxExecutor
from voice2task.runtime.inference import FIXTURE_CONTRACTS
from voice2task.runtime.models import BrowserTaskContractPayload, EventType, SessionContext
from voice2task.runtime.verifier import verify_execution


def _context(session_id: str = "executor-session") -> SessionContext:
    return SessionContext(
        session_id=session_id,
        profile={"email": "demo@example.com"},
        plan_version=1,
        plan_issued_at=datetime.now(timezone.utc),
    )


def _compiled(utterance: str, context: SessionContext):
    contract = BrowserTaskContractPayload.model_validate(FIXTURE_CONTRACTS[utterance])
    result = compile_contract_to_plan(contract, context)
    assert result.plan is not None
    return contract, result.plan


@pytest.mark.asyncio
async def test_browser_manager_close_is_idempotent_when_driver_already_closed() -> None:
    class ClosedBrowser:
        async def close(self) -> None:
            raise RuntimeError("driver already closed")

    class StoppablePlaywright:
        def __init__(self) -> None:
            self.stop_count = 0

        async def stop(self) -> None:
            self.stop_count += 1

    manager = BrowserManager()
    playwright = StoppablePlaywright()
    manager._browser = ClosedBrowser()  # type: ignore[assignment]
    manager._playwright = playwright  # type: ignore[assignment]

    await manager.close()
    await manager.close()

    assert playwright.stop_count == 1
    assert manager._browser is None
    assert manager._playwright is None


@pytest.mark.parametrize(
    "origin",
    ["https://example.com", "http://10.0.0.1:8000", "file:///tmp/demo"],
)
def test_executor_rejects_non_localhost_sandbox_origins(tmp_path: Path, origin: str) -> None:
    with pytest.raises(ExecutorError, match="SANDBOX_ORIGIN_INVALID"):
        SandboxExecutor(BrowserManager(), sandbox_origin=origin, artifact_dir=tmp_path)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("utterance", "confirmed", "expected_actions"),
    [
        ("帮我搜索北京明天的天气", False, 3),
        ("打开帮助中心", False, 1),
        ("帮我提取这个页面上的商品价格", False, 2),
        ("把邮箱填进表单里，提交前先问我", True, 2),
    ],
)
async def test_executor_runs_four_scenarios_with_events_screenshots_and_cleanup(
    sandbox_origin: str,
    tmp_path: Path,
    utterance: str,
    confirmed: bool,
    expected_actions: int,
) -> None:
    context = _context(f"executor-{expected_actions}-{confirmed}")
    contract, plan = _compiled(utterance, context)
    manager = BrowserManager()
    await manager.start()
    events: list[tuple[EventType, dict[str, object]]] = []

    async def emit(event_type: EventType, payload: dict[str, object]) -> None:
        events.append((event_type, payload))

    try:
        executor = SandboxExecutor(
            manager,
            sandbox_origin=sandbox_origin,
            artifact_dir=tmp_path,
            event_sink=emit,
        )
        outcome = await executor.execute(
            plan,
            contract=contract,
            context=context,
            confirmation_consumed=confirmed,
        )
    finally:
        await manager.close()

    assert outcome.browser_context_created is True
    assert outcome.action_count == expected_actions
    assert len(outcome.screenshots) == expected_actions
    assert len(list(tmp_path.glob("*.png"))) == expected_actions
    assert sum(event_type is EventType.ACTION_STARTED for event_type, _ in events) == expected_actions
    assert sum(event_type is EventType.ACTION_COMPLETED for event_type, _ in events) == expected_actions
    assert manager.active_context_count == 0
    assert verify_execution(plan, contract, context, outcome).passed is True
    serialized_events = repr(events)
    assert "data-testid" not in serialized_events
    assert str(tmp_path) not in serialized_events


@pytest.mark.asyncio
async def test_form_fill_cannot_create_context_before_confirmation(
    sandbox_origin: str, tmp_path: Path
) -> None:
    context = _context("unconfirmed-form")
    contract, plan = _compiled("把邮箱填进表单里，提交前先问我", context)
    manager = BrowserManager()
    await manager.start()
    executor = SandboxExecutor(manager, sandbox_origin=sandbox_origin, artifact_dir=tmp_path)

    try:
        with pytest.raises(ExecutorError, match="CONFIRMATION_REQUIRED") as exc_info:
            await executor.execute(
                plan,
                contract=contract,
                context=context,
                confirmation_consumed=False,
            )
    finally:
        await manager.close()

    assert exc_info.value.code == "CONFIRMATION_REQUIRED"
    assert manager.active_context_count == 0
    assert list(tmp_path.glob("*.png")) == []


@pytest.mark.asyncio
async def test_executor_aborts_external_request_before_egress_and_closes_context(
    sandbox_origin: str, tmp_path: Path
) -> None:
    context = _context("external-egress")
    contract, plan = _compiled("打开帮助中心", context)
    malicious_registry = dict(CAPABILITY_REGISTRY)
    malicious_registry["demo_help"] = replace(
        malicious_registry["demo_help"],
        path="https://example.com/should-never-leave",
    )
    manager = BrowserManager()
    await manager.start()
    executor = SandboxExecutor(
        manager,
        sandbox_origin=sandbox_origin,
        artifact_dir=tmp_path,
        capabilities=malicious_registry,
    )

    try:
        with pytest.raises(ExecutorError, match="EXTERNAL_REQUEST_BLOCKED") as exc_info:
            await executor.execute(
                plan,
                contract=contract,
                context=context,
                confirmation_consumed=False,
            )
    finally:
        await manager.close()

    assert exc_info.value.code == "EXTERNAL_REQUEST_BLOCKED"
    assert manager.active_context_count == 0


@pytest.mark.asyncio
async def test_executor_failure_stops_remaining_actions_and_closes_context(
    sandbox_origin: str, tmp_path: Path
) -> None:
    context = _context("missing-locator")
    contract, plan = _compiled("帮我搜索北京明天的天气", context)
    broken_registry = dict(CAPABILITY_REGISTRY)
    broken_registry["demo_search"] = replace(
        broken_registry["demo_search"],
        locators={**broken_registry["demo_search"].locators, "query_input": '[data-testid="missing"]'},
    )
    manager = BrowserManager()
    await manager.start()
    executor = SandboxExecutor(
        manager,
        sandbox_origin=sandbox_origin,
        artifact_dir=tmp_path,
        capabilities=broken_registry,
        overall_timeout_ms=7000,
    )

    try:
        with pytest.raises(ExecutorError) as exc_info:
            await executor.execute(plan, contract=contract, context=context)
    finally:
        await manager.close()

    assert exc_info.value.code in {"ACTION_TIMEOUT", "ACTION_FAILED"}
    assert manager.active_context_count == 0


@pytest.mark.asyncio
async def test_executor_overall_timeout_fails_closed_and_closes_context(
    sandbox_origin: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context("overall-timeout")
    contract, plan = _compiled("打开帮助中心", context)
    manager = BrowserManager()
    await manager.start()
    executor = SandboxExecutor(
        manager,
        sandbox_origin=sandbox_origin,
        artifact_dir=tmp_path,
        overall_timeout_ms=250,
    )

    async def never_finishes(*_args: object, **_kwargs: object) -> None:
        await asyncio.sleep(1)

    monkeypatch.setattr(executor, "_perform_action", never_finishes)
    try:
        with pytest.raises(ExecutorError, match="EXECUTION_TIMEOUT") as exc_info:
            await executor.execute(plan, contract=contract, context=context)
    finally:
        await manager.close()

    assert exc_info.value.code == "EXECUTION_TIMEOUT"
    assert manager.active_context_count == 0


@pytest.mark.asyncio
async def test_executor_setup_failure_still_closes_new_context(tmp_path: Path) -> None:
    context = _context("setup-failure")
    contract, plan = _compiled("打开帮助中心", context)
    browser_context = AsyncMock()
    browser_context.route.side_effect = PlaywrightError("route setup failed")
    manager = BrowserManager()
    manager.new_context = AsyncMock(return_value=browser_context)  # type: ignore[method-assign]
    manager.close_context = AsyncMock()  # type: ignore[method-assign]
    executor = SandboxExecutor(
        manager,
        sandbox_origin="http://127.0.0.1:8000",
        artifact_dir=tmp_path,
    )

    with pytest.raises(ExecutorError, match="BROWSER_SETUP_FAILED") as exc_info:
        await executor.execute(plan, contract=contract, context=context)

    assert exc_info.value.code == "BROWSER_SETUP_FAILED"
    manager.close_context.assert_awaited_once_with(browser_context)
