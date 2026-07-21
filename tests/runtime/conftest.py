from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator

import pytest_asyncio
import uvicorn
from fastapi import FastAPI

from apps.api.sandbox import router as sandbox_router


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest_asyncio.fixture
async def sandbox_origin() -> AsyncIterator[str]:
    app = FastAPI()
    app.include_router(sandbox_router)
    port = _free_port()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="critical",
        lifespan="off",
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.01)
    if not server.started:
        server.should_exit = True
        await task
        raise RuntimeError("test sandbox server did not start")
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await task
