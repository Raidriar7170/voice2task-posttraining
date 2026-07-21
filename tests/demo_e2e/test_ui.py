from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
import uvicorn
from playwright.async_api import Page, async_playwright

from apps.api.config import DemoConfig
from apps.api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest_asyncio.fixture
async def production_demo(tmp_path: Path) -> AsyncIterator[str]:
    dist = REPO_ROOT / "apps/web/dist"
    assert (dist / "index.html").is_file(), "run npm build before production UI tests"
    port = _free_port()
    origin = f"http://127.0.0.1:{port}"
    config = DemoConfig(
        database_path=tmp_path / "demo.sqlite3",
        artifact_dir=tmp_path / "artifacts",
        audio_temp_dir=tmp_path / "audio-tmp",
        web_dist=dist,
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
        sandbox_origin=origin,
        heartbeat_seconds=0.05,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(config=config),
            host="127.0.0.1",
            port=port,
            log_level="critical",
        )
    )
    task = asyncio.create_task(server.serve())
    for _ in range(200):
        if server.started:
            break
        await asyncio.sleep(0.02)
    if not server.started:
        server.should_exit = True
        await task
        raise RuntimeError("production demo server did not start")
    try:
        yield origin
    finally:
        server.should_exit = True
        await task


async def _assert_no_horizontal_overflow(page: Page) -> None:
    dimensions = await page.locator("html").evaluate(
        "element => ({ scrollWidth: element.scrollWidth, clientWidth: element.clientWidth })"
    )
    assert dimensions["scrollWidth"] <= dimensions["clientWidth"] + 1


async def _latest_session(origin: str) -> dict[str, object]:
    async with httpx.AsyncClient(base_url=origin) as client:
        response = await client.get("/api/sessions")
        response.raise_for_status()
        return response.json()["sessions"][0]


async def _session_events(origin: str, session_id: str) -> list[dict[str, object]]:
    async with httpx.AsyncClient(base_url=origin) as client:
        response = await client.get(f"/api/sessions/{session_id}/events")
        response.raise_for_status()
        return response.json()["events"]


def _assert_inference_and_compiler_precede_execution(
    events: list[dict[str, object]],
) -> None:
    event_types = [str(event["event_type"]) for event in events]
    assert event_types.index("INFERENCE_STARTED") < event_types.index("PLAN_COMPILED")
    if "EXECUTION_STARTED" in event_types:
        assert event_types.index("PLAN_COMPILED") < event_types.index("EXECUTION_STARTED")


async def _execute_with_background_release_retry(page: Page, button_name: str) -> None:
    completed_status = page.locator(
        'section[aria-labelledby="plan-heading"] .state-chip',
        has_text="已完成",
    )
    for _ in range(20):
        await page.get_by_role("button", name=button_name).click()
        await page.wait_for_timeout(50)
        if await completed_status.is_visible():
            return
        active_task_error = page.get_by_role("alert").filter(has_text="SESSION_TASK_ACTIVE")
        if await active_task_error.count() and await active_task_error.is_visible():
            continue
        await completed_status.wait_for(timeout=10_000)
        return
    raise AssertionError("execute remained blocked by background task ownership")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "viewport",
    [{"width": 1440, "height": 900}, {"width": 390, "height": 844}],
)
async def test_production_ui_search_extract_recoverable_form_blocked_and_delete(
    production_demo: str,
    viewport: dict[str, int],
) -> None:
    console_errors: list[str] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport=viewport)
        page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        try:
            await page.goto(production_demo, wait_until="networkidle")
            await page.get_by_role("button", name="生成受控计划").click()
            await page.locator(".capability-line strong", has_text="demo_search").wait_for()
            await page.get_by_text("INFERENCE_STARTED", exact=True).wait_for()
            await page.get_by_text("PLAN_COMPILED", exact=True).wait_for()
            search = await _latest_session(production_demo)
            search_events_before = await _session_events(production_demo, str(search["id"]))
            _assert_inference_and_compiler_precede_execution(search_events_before)
            assert all(
                event["event_type"] != "EXECUTION_STARTED" for event in search_events_before
            )
            await _execute_with_background_release_retry(page, "执行计划")
            await page.get_by_text("通过", exact=True).wait_for()
            await page.get_by_text("已完成", exact=True).first.wait_for()
            search_events_after = await _session_events(production_demo, str(search["id"]))
            _assert_inference_and_compiler_precede_execution(search_events_after)
            await _assert_no_horizontal_overflow(page)

            await page.reload(wait_until="networkidle")
            await page.get_by_role(
                "button", name="帮我提取这个页面上的商品价格"
            ).click()
            await page.get_by_role("button", name="生成受控计划").click()
            await page.locator(".capability-line strong", has_text="demo_product").wait_for()
            extract = await _latest_session(production_demo)
            extract_events_before = await _session_events(
                production_demo, str(extract["id"])
            )
            _assert_inference_and_compiler_precede_execution(extract_events_before)
            assert all(
                event["event_type"] != "EXECUTION_STARTED"
                for event in extract_events_before
            )
            await _execute_with_background_release_retry(page, "执行计划")
            await page.get_by_text("已完成", exact=True).first.wait_for()
            extract = await _latest_session(production_demo)
            extract_evidence = extract["execution"]["evidence"]
            assert extract_evidence["action_outputs"] == {"product_price": "¥199.00"}
            assert extract_evidence["dom_snapshot"] == {"product_price": "¥199.00"}
            assert extract["verification"]["passed"] is True
            assert len(extract["verification"]["checks"]) == 5
            assert all(check["passed"] for check in extract["verification"]["checks"])
            await _assert_no_horizontal_overflow(page)

            await page.reload(wait_until="networkidle")
            await page.get_by_role("button", name="把邮箱填进表单里，提交前先问我").click()
            await page.get_by_role("button", name="生成受控计划").click()
            dialog = page.get_by_role("dialog", name="写操作确认")
            await dialog.wait_for()
            async with httpx.AsyncClient(base_url=production_demo) as client:
                pending = (await client.get("/api/sessions")).json()["sessions"][0]
            assert pending["status"] == "AWAITING_CONFIRMATION"
            assert pending["execution"] is None
            pending_events = await _session_events(production_demo, pending["id"])
            _assert_inference_and_compiler_precede_execution(pending_events)
            assert all(event["event_type"] != "EXECUTION_STARTED" for event in pending_events)

            await page.reload(wait_until="networkidle")
            dialog = page.get_by_role("dialog", name="写操作确认")
            await dialog.wait_for()
            recovered_pending = await _latest_session(production_demo)
            assert recovered_pending["id"] == pending["id"]
            assert recovered_pending["status"] == "AWAITING_CONFIRMATION"
            assert recovered_pending["execution"] is None

            await dialog.get_by_role("button", name="确认计划").click()
            await page.get_by_text("已确认待执行", exact=True).first.wait_for()
            confirmed = await _latest_session(production_demo)
            assert confirmed["status"] == "CONFIRMED"
            assert confirmed["execution"] is None
            assert confirmed["execution_claimed"] is False
            confirmed_events = await _session_events(production_demo, pending["id"])
            assert all(event["event_type"] != "EXECUTION_STARTED" for event in confirmed_events)
            await _execute_with_background_release_retry(page, "执行已确认计划")
            await page.get_by_text("通过", exact=True).wait_for()
            await page.get_by_text("已完成", exact=True).first.wait_for()
            form_events = await _session_events(production_demo, pending["id"])
            _assert_inference_and_compiler_precede_execution(form_events)
            await _assert_no_horizontal_overflow(page)

            await page.reload(wait_until="networkidle")
            await page.get_by_role("button", name="替我完成付款").click()
            await page.get_by_role("button", name="生成受控计划").click()
            await page.get_by_text("已阻止", exact=True).first.wait_for()
            await page.get_by_text("零动作：浏览器不会启动", exact=True).wait_for()
            async with httpx.AsyncClient(base_url=production_demo) as client:
                blocked = (await client.get("/api/sessions")).json()["sessions"][0]
            assert blocked["status"] == "BLOCKED"
            assert blocked["execution"]["browser_context_created"] is False
            assert blocked["execution"]["action_count"] == 0
            blocked_events = await _session_events(production_demo, blocked["id"])
            _assert_inference_and_compiler_precede_execution(blocked_events)
            assert all(event["event_type"] != "EXECUTION_STARTED" for event in blocked_events)
            await _assert_no_horizontal_overflow(page)

            blocked_id = str(blocked["id"])
            await page.get_by_role("button", name="删除 Session").click()
            await page.get_by_text("创建 session 后显示 transcript。", exact=True).wait_for()
            async with httpx.AsyncClient(base_url=production_demo) as client:
                deleted = await client.get(f"/api/sessions/{blocked_id}")
                remaining = (await client.get("/api/sessions")).json()["sessions"]
            assert deleted.status_code == 404
            assert all(session["id"] != blocked_id for session in remaining)
            await _assert_no_horizontal_overflow(page)
        finally:
            await browser.close()

    assert console_errors == []


@pytest.mark.asyncio
@pytest.mark.parametrize("viewport", [{"width": 390, "height": 844}, {"width": 1440, "height": 900}])
async def test_production_ui_has_no_horizontal_overflow(
    production_demo: str,
    viewport: dict[str, int],
) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport=viewport)
        try:
            await page.goto(production_demo, wait_until="networkidle")
            await page.get_by_text("Fixture Inference", exact=True).wait_for()
            await _assert_no_horizontal_overflow(page)
        finally:
            await browser.close()
