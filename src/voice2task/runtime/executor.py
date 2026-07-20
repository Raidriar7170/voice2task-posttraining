from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

from playwright.async_api import Browser, BrowserContext, Page, Playwright, Route, async_playwright
from playwright.async_api import Error as PlaywrightError

from voice2task.runtime.capabilities import CAPABILITY_REGISTRY, Capability
from voice2task.runtime.models import (
    ArtifactRecord,
    BrowserTaskContractPayload,
    EventType,
    ExecutionAction,
    ExecutionEvidence,
    ExecutionOutcome,
    ExecutionPlan,
    SessionContext,
)
from voice2task.runtime.policy import evaluate_policy


class ExecutorError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.public_message = message


EventSink = Callable[[EventType, dict[str, object]], Awaitable[None]]
ArtifactSink = Callable[[ArtifactRecord], Awaitable[None]]


class BrowserManager:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self.active_context_count = 0

    async def start(self) -> None:
        if self._browser is not None:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)

    async def new_context(self) -> BrowserContext:
        if self._browser is None:
            raise ExecutorError("BROWSER_NOT_READY", "The local browser runtime is not ready.")
        context = await self._browser.new_context(
            accept_downloads=False,
            service_workers="block",
        )
        self.active_context_count += 1
        return context

    async def close_context(self, context: BrowserContext) -> None:
        try:
            await context.close()
        finally:
            self.active_context_count = max(0, self.active_context_count - 1)

    async def close(self) -> None:
        browser = self._browser
        playwright = self._playwright
        self._browser = None
        self._playwright = None
        if browser is not None:
            with suppress(PlaywrightError, RuntimeError):
                await browser.close()
        if playwright is not None:
            with suppress(PlaywrightError, RuntimeError):
                await playwright.stop()


class SandboxExecutor:
    def __init__(
        self,
        manager: BrowserManager,
        *,
        sandbox_origin: str,
        artifact_dir: Path,
        event_sink: EventSink | None = None,
        artifact_sink: ArtifactSink | None = None,
        capabilities: Mapping[str, Capability] = CAPABILITY_REGISTRY,
        overall_timeout_ms: int = 20_000,
    ) -> None:
        parsed = urlsplit(sandbox_origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ExecutorError("SANDBOX_ORIGIN_INVALID", "Sandbox origin configuration is invalid.")
        self.manager = manager
        self.sandbox_origin = f"{parsed.scheme}://{parsed.netloc}"
        self.artifact_dir = artifact_dir
        self.event_sink = event_sink
        self.artifact_sink = artifact_sink
        self.capabilities = capabilities
        self.overall_timeout_ms = overall_timeout_ms

    async def _emit(self, event_type: EventType, payload: dict[str, object]) -> None:
        if self.event_sink is not None:
            await self.event_sink(event_type, payload)

    def _resolve_value(
        self,
        source: str | None,
        *,
        contract: BrowserTaskContractPayload,
        context: SessionContext,
        action_outputs: dict[str, str],
    ) -> str:
        if source is None:
            return ""
        if source == "contract.slots.query":
            return str(contract.slots["query"])
        if source == "session.profile.email":
            return context.profile.email
        if source == "execution.action_outputs.product_price":
            return action_outputs.get("product_price", "")
        raise ExecutorError("VALUE_SOURCE_NOT_ALLOWLISTED", "Action value source is not allowlisted.")

    async def _perform_action(
        self,
        page: Page,
        action: ExecutionAction,
        capability: Capability,
        *,
        contract: BrowserTaskContractPayload,
        context: SessionContext,
        action_outputs: dict[str, str],
    ) -> None:
        timeout = action.timeout_ms
        if action.kind.value == "navigate":
            target = urljoin(f"{self.sandbox_origin}/", capability.path.lstrip("/"))
            await page.goto(target, wait_until="domcontentloaded", timeout=timeout)
            return
        if action.locator_id is None:
            raise ExecutorError("LOCATOR_NOT_ALLOWLISTED", "Action requires a trusted locator ID.")
        selector = capability.locators.get(action.locator_id)
        if selector is None:
            raise ExecutorError("LOCATOR_NOT_ALLOWLISTED", "Action locator is not allowlisted.")
        locator = page.locator(selector)
        if action.kind.value == "fill":
            value = self._resolve_value(
                action.value_source,
                contract=contract,
                context=context,
                action_outputs=action_outputs,
            )
            await locator.fill(value, timeout=timeout)
        elif action.kind.value == "click":
            await locator.click(timeout=timeout)
        elif action.kind.value == "extract_text":
            text = await locator.text_content(timeout=timeout)
            action_outputs[action.locator_id] = (text or "").strip()
        else:
            raise ExecutorError("UNSAFE_ACTION", "Action kind is not supported by the sandbox executor.")

    async def _save_screenshot(
        self,
        page: Page,
        *,
        session_id: str,
    ) -> str:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_id = uuid4().hex
        filename = f"{artifact_id}.png"
        path = self.artifact_dir / filename
        await page.screenshot(path=path.as_posix(), full_page=True)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if self.artifact_sink is not None:
            from datetime import datetime, timezone

            await self.artifact_sink(
                ArtifactRecord(
                    id=artifact_id,
                    session_id=session_id,
                    kind="action_screenshot",
                    relative_path=filename,
                    sha256=digest,
                    created_at=datetime.now(timezone.utc),
                )
            )
        return artifact_id

    async def _collect_dom_snapshot(
        self,
        page: Page,
        capability: Capability,
    ) -> dict[str, str]:
        dom_snapshot: dict[str, str] = {}
        for locator_id in ("query_input", "email_input"):
            selector = capability.locators.get(locator_id)
            if selector and await page.locator(selector).count():
                dom_snapshot[locator_id] = await page.locator(selector).input_value()
        for locator_id in ("results", "heading", "product_price"):
            selector = capability.locators.get(locator_id)
            if selector and await page.locator(selector).count():
                text = await page.locator(selector).text_content()
                dom_snapshot[locator_id] = (text or "").strip()
        return dom_snapshot

    async def execute(
        self,
        plan: ExecutionPlan,
        *,
        contract: BrowserTaskContractPayload,
        context: SessionContext,
        confirmation_consumed: bool = False,
    ) -> ExecutionOutcome:
        policy = evaluate_policy(
            plan,
            confirmation_consumed=confirmation_consumed,
        )
        if not policy.allowed:
            raise ExecutorError(policy.reason_code, policy.message)
        if plan.capability_id is None or plan.capability_id not in self.capabilities:
            raise ExecutorError("CAPABILITY_NOT_ALLOWLISTED", "Capability is not available to the executor.")
        if len(plan.actions) > 5:
            raise ExecutorError("ACTION_LIMIT_EXCEEDED", "Execution plan exceeds the action limit.")
        capability = self.capabilities[plan.capability_id]
        try:
            return await asyncio.wait_for(
                self._execute_in_context(
                    plan,
                    contract=contract,
                    context=context,
                    capability=capability,
                ),
                timeout=self.overall_timeout_ms / 1000,
            )
        except TimeoutError as exc:
            raise ExecutorError(
                "EXECUTION_TIMEOUT", "The controlled browser execution timed out."
            ) from exc
        except PlaywrightError as exc:
            raise ExecutorError(
                "BROWSER_SETUP_FAILED", "The controlled browser context could not be prepared."
            ) from exc

    async def _execute_in_context(
        self,
        plan: ExecutionPlan,
        *,
        contract: BrowserTaskContractPayload,
        context: SessionContext,
        capability: Capability,
    ) -> ExecutionOutcome:
        started = time.monotonic()
        browser_context = await self.manager.new_context()
        external_request_blocked = False
        action_outputs: dict[str, str] = {}
        screenshots: list[str] = []
        completed_actions = 0

        async def guard_route(route: Route) -> None:
            nonlocal external_request_blocked
            parsed = urlsplit(route.request.url)
            request_origin = f"{parsed.scheme}://{parsed.netloc}"
            if request_origin != self.sandbox_origin or not parsed.path.startswith("/sandbox/"):
                external_request_blocked = True
                await route.abort("blockedbyclient")
                return
            await route.continue_()

        try:
            await browser_context.route("**/*", guard_route)
            route_web_socket = getattr(browser_context, "route_web_socket", None)
            if callable(route_web_socket):
                await route_web_socket("**/*", lambda socket: socket.close())
            page = await browser_context.new_page()
            page.on("popup", lambda popup: asyncio.create_task(popup.close()))
            page.on("download", lambda download: asyncio.create_task(download.cancel()))
            page.on("filechooser", lambda chooser: asyncio.create_task(chooser.set_files([])))
            for action in plan.actions:
                action_started = time.monotonic()
                await self._emit(
                    EventType.ACTION_STARTED,
                    {
                        "action_id": action.action_id,
                        "kind": action.kind.value,
                        "capability_id": action.capability_id,
                        "locator_id": action.locator_id,
                    },
                )
                try:
                    await self._perform_action(
                        page,
                        action,
                        capability,
                        contract=contract,
                        context=context,
                        action_outputs=action_outputs,
                    )
                    if external_request_blocked:
                        raise ExecutorError(
                            "EXTERNAL_REQUEST_BLOCKED", "A request outside the exact sandbox origin was blocked."
                        )
                    screenshot_id = await self._save_screenshot(page, session_id=plan.session_id)
                    screenshots.append(screenshot_id)
                    completed_actions += 1
                    await self._emit(
                        EventType.ACTION_COMPLETED,
                        {
                            "action_id": action.action_id,
                            "kind": action.kind.value,
                            "capability_id": action.capability_id,
                            "locator_id": action.locator_id,
                            "elapsed_ms": int((time.monotonic() - action_started) * 1000),
                            "screenshot_id": screenshot_id,
                        },
                    )
                except ExecutorError as exc:
                    await self._emit(
                        EventType.ACTION_FAILED,
                        {"action_id": action.action_id, "error_code": exc.code},
                    )
                    raise
                except PlaywrightError as exc:
                    code = "EXTERNAL_REQUEST_BLOCKED" if external_request_blocked else "ACTION_FAILED"
                    await self._emit(
                        EventType.ACTION_FAILED,
                        {"action_id": action.action_id, "error_code": code},
                    )
                    raise ExecutorError(code, "The controlled browser action failed.") from exc
            dom_snapshot = await self._collect_dom_snapshot(page, capability)
            return ExecutionOutcome(
                browser_context_created=True,
                action_count=completed_actions,
                final_url_path=urlsplit(page.url).path,
                evidence=ExecutionEvidence(
                    action_outputs=action_outputs,
                    dom_snapshot=dom_snapshot,
                ),
                screenshots=screenshots,
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        finally:
            await self.manager.close_context(browser_context)
