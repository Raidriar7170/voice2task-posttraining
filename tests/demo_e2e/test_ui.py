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


@pytest.mark.asyncio
async def test_production_ui_search_form_confirmation_and_blocked(
    production_demo: str,
) -> None:
    console_errors: list[str] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        try:
            await page.goto(production_demo, wait_until="networkidle")
            await page.get_by_role("button", name="生成受控计划").click()
            await page.locator(".capability-line strong", has_text="demo_search").wait_for()
            await page.get_by_role("button", name="执行计划").click()
            await page.get_by_text("通过", exact=True).wait_for()
            await page.get_by_text("已完成", exact=True).first.wait_for()
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
            await dialog.get_by_role("button", name="确认并执行").click()
            await page.get_by_text("通过", exact=True).wait_for()
            await page.get_by_text("已完成", exact=True).first.wait_for()
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
