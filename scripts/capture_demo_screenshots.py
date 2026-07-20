from __future__ import annotations

import argparse
import asyncio
import socket
import tempfile
from pathlib import Path

import httpx
import uvicorn
from playwright.async_api import Page, async_playwright

from apps.api.config import DemoConfig
from apps.api.main import create_app


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _new_page(browser, origin: str, viewport: dict[str, int]) -> Page:
    page = await browser.new_page(viewport=viewport)
    await page.goto(origin, wait_until="networkidle")
    await page.get_by_text("Fixture Inference", exact=True).wait_for()
    return page


async def _complete_search(page: Page) -> None:
    await page.get_by_role("button", name="帮我搜索北京明天的天气").click()
    await page.get_by_role("button", name="生成受控计划").click()
    await page.get_by_role("button", name="执行计划").click()
    await page.get_by_text("通过", exact=True).wait_for()


async def _clear_sessions(origin: str) -> None:
    async with httpx.AsyncClient(base_url=origin) as client:
        sessions = (await client.get("/api/sessions")).json()["sessions"]
        for session in sessions:
            response = await client.delete(f"/api/sessions/{session['id']}")
            response.raise_for_status()


async def capture(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    origin = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="voice2task-demo-screenshots-") as temp_name:
        temp = Path(temp_name)
        config = DemoConfig(
            database_path=temp / "demo.sqlite3",
            artifact_dir=temp / "artifacts",
            audio_temp_dir=temp / "audio-tmp",
            web_dist=Path("apps/web/dist"),
            inference_mode="fixture",
            asr_mode="disabled",
            execution_mode="sandbox",
            sandbox_origin=origin,
            heartbeat_seconds=0.1,
        )
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(config=config),
                host="127.0.0.1",
                port=port,
                log_level="critical",
            )
        )
        server_task = asyncio.create_task(server.serve())
        for _ in range(250):
            if server.started:
                break
            await asyncio.sleep(0.02)
        if not server.started:
            server.should_exit = True
            await server_task
            raise RuntimeError("screenshot demo server failed to start")
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    desktop_search = await _new_page(browser, origin, {"width": 1440, "height": 900})
                    await _complete_search(desktop_search)
                    await desktop_search.screenshot(
                        path=(output_dir / "desktop-search-complete.png").as_posix(),
                        full_page=True,
                    )
                    await desktop_search.close()
                    await _clear_sessions(origin)

                    desktop_form = await _new_page(browser, origin, {"width": 1440, "height": 900})
                    await desktop_form.get_by_role(
                        "button", name="把邮箱填进表单里，提交前先问我"
                    ).click()
                    await desktop_form.get_by_role("button", name="生成受控计划").click()
                    await desktop_form.get_by_role("dialog", name="写操作确认").wait_for()
                    await desktop_form.screenshot(
                        path=(output_dir / "desktop-form-confirmation.png").as_posix(),
                        full_page=False,
                    )
                    await desktop_form.close()
                    await _clear_sessions(origin)

                    mobile_search = await _new_page(browser, origin, {"width": 390, "height": 844})
                    await _complete_search(mobile_search)
                    await mobile_search.screenshot(
                        path=(output_dir / "mobile-search-complete.png").as_posix(),
                        full_page=True,
                    )
                    await mobile_search.close()
                    await _clear_sessions(origin)

                    mobile_blocked = await _new_page(browser, origin, {"width": 390, "height": 844})
                    await mobile_blocked.get_by_role("button", name="替我完成付款").click()
                    await mobile_blocked.get_by_role("button", name="生成受控计划").click()
                    await mobile_blocked.get_by_text("已阻止", exact=True).first.wait_for()
                    await mobile_blocked.screenshot(
                        path=(output_dir / "mobile-blocked.png").as_posix(),
                        full_page=True,
                    )
                    await mobile_blocked.close()
                finally:
                    await browser.close()
        finally:
            server.should_exit = True
            await server_task


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture public-safe controlled demo screenshots.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/demo/screenshots"))
    args = parser.parse_args()
    asyncio.run(capture(args.output_dir))


if __name__ == "__main__":
    main()
