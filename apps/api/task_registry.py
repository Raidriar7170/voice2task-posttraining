from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from voice2task.runtime.storage import SessionConflict

WorkFactory = Callable[[], Awaitable[None]]
ErrorHandler = Callable[[BaseException], Awaitable[None]]
DoneHandler = Callable[[], None]
RegisteredHandler = Callable[[], None]


class SessionTaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._accepting = True
        self._lock = asyncio.Lock()

    async def _run(
        self,
        work: WorkFactory,
        on_error: ErrorHandler | None,
    ) -> None:
        try:
            await work()
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            if on_error is not None:
                await on_error(exc)

    def _task_done(
        self,
        session_id: str,
        task: asyncio.Task[None],
        on_done: DoneHandler | None,
    ) -> None:
        try:
            task.exception()
        except asyncio.CancelledError:
            pass
        if on_done is not None:
            try:
                on_done()
            except BaseException:
                pass
        if self._tasks.get(session_id) is task:
            self._tasks.pop(session_id, None)

    async def start(
        self,
        session_id: str,
        work: WorkFactory,
        *,
        on_error: ErrorHandler | None = None,
        on_done: DoneHandler | None = None,
        on_registered: RegisteredHandler | None = None,
    ) -> None:
        async with self._lock:
            if not self._accepting:
                raise SessionConflict("SESSION_TASK_REGISTRY_CLOSED")
            current = self._tasks.get(session_id)
            if current is not None and not current.done():
                raise SessionConflict("SESSION_TASK_ACTIVE")
            task = asyncio.create_task(
                self._run(work, on_error),
                name=f"voice2task-session-{session_id}",
            )
            self._tasks[session_id] = task
            task.add_done_callback(
                lambda completed: self._task_done(session_id, completed, on_done)
            )
            if on_registered is not None:
                on_registered()

    def is_active(self, session_id: str) -> bool:
        task = self._tasks.get(session_id)
        return task is not None and not task.done()

    async def wait_idle(self, session_id: str) -> None:
        task = self._tasks.get(session_id)
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)

    async def cancel(self, session_id: str) -> bool:
        task = self._tasks.get(session_id)
        if task is None or task.done():
            return False
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        return True

    async def shutdown(self) -> set[str]:
        async with self._lock:
            self._accepting = False
            active = {
                session_id: task
                for session_id, task in self._tasks.items()
                if not task.done()
            }
            for task in active.values():
                task.cancel()
        if active:
            await asyncio.gather(*active.values(), return_exceptions=True)
        return set(active)
