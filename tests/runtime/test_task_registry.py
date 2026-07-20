from __future__ import annotations

import asyncio
import importlib
import importlib.util
from typing import Any

import pytest

from voice2task.runtime.storage import SessionConflict


def _registry_type() -> type[Any]:
    spec = importlib.util.find_spec("apps.api.task_registry")
    assert spec is not None, "apps.api.task_registry must define SessionTaskRegistry"
    module = importlib.import_module("apps.api.task_registry")
    registry_type = getattr(module, "SessionTaskRegistry", None)
    assert registry_type is not None, "SessionTaskRegistry must be public"
    return registry_type


@pytest.mark.asyncio
async def test_registry_keeps_one_strong_active_task_and_rejects_duplicate_start() -> None:
    registry = _registry_type()()
    started = asyncio.Event()
    release = asyncio.Event()

    async def work() -> None:
        started.set()
        await release.wait()

    await registry.start("session-one", work)
    await started.wait()

    assert registry.is_active("session-one") is True
    with pytest.raises(SessionConflict, match="SESSION_TASK_ACTIVE"):
        await registry.start("session-one", work)

    release.set()
    await registry.wait_idle("session-one")
    assert registry.is_active("session-one") is False


@pytest.mark.asyncio
async def test_registry_consumes_task_exceptions_and_invokes_controlled_handler() -> None:
    registry = _registry_type()()
    handled: list[str] = []
    loop_errors: list[dict[str, object]] = []
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: loop_errors.append(context))

    async def fail() -> None:
        raise RuntimeError("private task failure")

    async def handle(exc: BaseException) -> None:
        handled.append(type(exc).__name__)

    try:
        await registry.start("session-failure", fail, on_error=handle)
        await registry.wait_idle("session-failure")
        await asyncio.sleep(0)
    finally:
        loop.set_exception_handler(previous_handler)

    assert handled == ["RuntimeError"]
    assert loop_errors == []


@pytest.mark.asyncio
async def test_registry_shutdown_stops_accepting_cancels_and_awaits_all_tasks() -> None:
    registry = _registry_type()()
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def work() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    await registry.start("session-shutdown", work)
    await started.wait()

    cancelled_session_ids = await registry.shutdown()

    assert cancelled_session_ids == {"session-shutdown"}
    assert cancelled.is_set()
    assert registry.is_active("session-shutdown") is False
    with pytest.raises(SessionConflict, match="SESSION_TASK_REGISTRY_CLOSED"):
        await registry.start("session-late", work)


@pytest.mark.asyncio
async def test_registry_runs_done_cleanup_when_cancelled_before_work_starts() -> None:
    registry = _registry_type()()
    work_started = False
    cleanup_calls = 0

    async def work() -> None:
        nonlocal work_started
        work_started = True

    def cleanup() -> None:
        nonlocal cleanup_calls
        cleanup_calls += 1

    await registry.start("session-prestart-cancel", work, on_done=cleanup)
    assert await registry.cancel("session-prestart-cancel") is True

    assert work_started is False
    assert cleanup_calls == 1


@pytest.mark.asyncio
async def test_registry_transfers_resource_ownership_before_work_can_run() -> None:
    registry = _registry_type()()
    ownership_transferred = False
    observed_ownership: list[bool] = []

    def on_registered() -> None:
        nonlocal ownership_transferred
        ownership_transferred = True

    async def work() -> None:
        observed_ownership.append(ownership_transferred)

    await registry.start("session-owned-resource", work, on_registered=on_registered)
    await registry.wait_idle("session-owned-resource")

    assert observed_ownership == [True]
