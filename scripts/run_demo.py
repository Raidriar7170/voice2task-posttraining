from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence


def _terminate(processes: Sequence[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def run_development() -> int:
    environment = os.environ.copy()
    environment.setdefault("VOICE2TASK_SANDBOX_ORIGIN", "http://127.0.0.1:8000")
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
        ],
        env=environment,
        start_new_session=True,
    )
    web = subprocess.Popen(
        ["node_modules/.bin/vite"],
        cwd="apps/web",
        env=environment,
        start_new_session=True,
    )
    processes = [api, web]
    stop_requested = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        _terminate(processes)
    if stop_requested:
        return 0
    return next((process.returncode for process in processes if process.returncode), 0)


def run_production() -> int:
    environment = os.environ.copy()
    environment.setdefault("VOICE2TASK_SANDBOX_ORIGIN", "http://127.0.0.1:8000")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--workers",
            "1",
        ],
        env=environment,
        start_new_session=True,
    )
    stop_requested = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        if server.poll() is None:
            server.terminate()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        return_code = server.wait()
        return 0 if stop_requested else return_code
    except KeyboardInterrupt:
        return 130
    finally:
        _terminate([server])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Voice2Task controlled browser demo.")
    parser.add_argument("--dev", action="store_true", help="Run FastAPI reload and the Vite development server.")
    args = parser.parse_args()
    if args.dev:
        raise SystemExit(run_development())
    raise SystemExit(run_production())


if __name__ == "__main__":
    main()
