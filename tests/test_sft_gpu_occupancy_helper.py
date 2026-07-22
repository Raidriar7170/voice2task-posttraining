from __future__ import annotations

import json
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from voice2task import _sft_gpu_probe_helper as helper
from voice2task import training


def _ready_helper_facts(*, free_memory_gib: float = 80.0) -> dict[str, Any]:
    return {
        "cuda_available": True,
        "visible_device_count": 1,
        "name": "NVIDIA A100-SXM4-80GB",
        "compute_capability": "8.0",
        "total_memory_gib": 80.0,
        "free_memory_gib": free_memory_gib,
        "cuda_version": "12.4",
        "bf16_supported": True,
    }


def _helper_result(status: str = "OK", **overrides: Any) -> dict[str, Any]:
    return {"status": status, **_ready_helper_facts(), **overrides}


def _fake_torch(
    *,
    available: bool = True,
    visible_count: int = 1,
    api_failure: Exception | None = None,
) -> Any:
    def availability() -> bool:
        if api_failure is not None:
            raise api_failure
        return available

    cuda = types.SimpleNamespace(
        is_available=availability,
        device_count=lambda: visible_count,
        get_device_properties=lambda index: types.SimpleNamespace(total_memory=80 * 1024**3),
        get_device_capability=lambda index: (8, 0),
        mem_get_info=lambda index: (79 * 1024**3, 80 * 1024**3),
        get_device_name=lambda index: "NVIDIA A100-SXM4-80GB",
        is_bf16_supported=lambda: True,
    )
    return types.SimpleNamespace(cuda=cuda, version=types.SimpleNamespace(cuda="12.4"))


def test_helper_collect_reports_typed_cuda_unavailable_without_raw_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        helper.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError("secret /workspace/torch")),
    )

    result = helper.collect_gpu_result()

    assert result["status"] == "CUDA_UNAVAILABLE"
    assert result["cuda_available"] is False
    assert "secret" not in json.dumps(result, sort_keys=True)
    assert "/workspace" not in json.dumps(result, sort_keys=True)


def test_helper_collect_reports_typed_cuda_unavailable_for_false_cuda() -> None:
    result = helper.collect_gpu_result(_fake_torch(available=False))

    assert result["status"] == "CUDA_UNAVAILABLE"
    assert result["cuda_available"] is False
    assert result["visible_device_count"] == 0


def test_helper_collect_reports_typed_single_selection_failure() -> None:
    result = helper.collect_gpu_result(_fake_torch(visible_count=2))

    assert result["status"] == "GPU_SELECTION_NOT_SINGLE"
    assert result["cuda_available"] is True
    assert result["visible_device_count"] == 2


def test_helper_collect_reports_valid_a100_facts() -> None:
    result = helper.collect_gpu_result(_fake_torch())

    assert result == {
        "schema_version": "voice2task-sft-gpu-helper-v2",
        "status": "OK",
        **_ready_helper_facts(free_memory_gib=79.0),
    }


def test_helper_collect_reports_typed_cuda_probe_failure_without_raw_error() -> None:
    result = helper.collect_gpu_result(
        _fake_torch(api_failure=RuntimeError("driver secret /data/private"))
    )

    assert result["status"] == "CUDA_PROBE_FAILED"
    assert "driver secret" not in json.dumps(result, sort_keys=True)
    assert "/data/private" not in json.dumps(result, sort_keys=True)


@pytest.mark.parametrize(
    "event",
    [
        "socket.__new__",
        "socket.connect",
        "socket.bind",
        "socket.getaddrinfo",
    ],
)
def test_helper_network_audit_hook_blocks_network_events(event: str) -> None:
    with pytest.raises(PermissionError, match="^NETWORK_ACCESS_BLOCKED$"):
        helper._network_audit_hook(event, ())  # noqa: SLF001


def test_helper_installs_network_audit_hook_before_importing_torch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed: list[Any] = []
    monkeypatch.setattr(helper.sys, "addaudithook", installed.append)

    def fake_import(name: str) -> Any:
        assert installed == [helper._network_audit_hook]  # noqa: SLF001
        installed[0]("socket.connect", ())
        return _fake_torch()

    monkeypatch.setattr(helper.importlib, "import_module", fake_import)

    result = helper.main_result()

    assert result["status"] == "CUDA_PROBE_FAILED"
    assert "NETWORK_ACCESS_BLOCKED" not in json.dumps(result, sort_keys=True)


def test_helper_network_audit_hook_blocks_real_socket_apis_in_isolated_child() -> None:
    helper_path = Path(helper.__file__).resolve(strict=True)
    script = """
import importlib.util
import json
import socket
import sys

spec = importlib.util.spec_from_file_location("isolated_gpu_helper", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.addaudithook(module._network_audit_hook)

def with_tcp(action):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        return action(sock)
    finally:
        sock.close()

def with_udp(action):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return action(sock)
    finally:
        sock.close()

operations = {
    "creation": lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM).close(),
    "listen": lambda: with_tcp(lambda sock: (sock.bind(("127.0.0.1", 0)), sock.listen())),
    "connect": lambda: with_tcp(lambda sock: sock.connect(("127.0.0.1", 9))),
    "connect_ex": lambda: with_tcp(lambda sock: sock.connect_ex(("127.0.0.1", 9))),
    "sendto": lambda: with_udp(lambda sock: sock.sendto(b"x", ("127.0.0.1", 9))),
    "sendmsg": lambda: with_udp(lambda sock: sock.sendmsg([b"x"], [], 0, ("127.0.0.1", 9))),
    "dns": lambda: socket.getaddrinfo("localhost", 80),
}
results = {}
for name, operation in operations.items():
    try:
        operation()
    except PermissionError as exc:
        results[name] = "BLOCKED" if str(exc) == "NETWORK_ACCESS_BLOCKED" else "WRONG_ERROR"
    except Exception:
        results[name] = "NOT_AUDIT_BLOCKED"
    else:
        results[name] = "NOT_BLOCKED"
print(json.dumps(results, sort_keys=True))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script, helper_path.as_posix()],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={"LC_ALL": "C", "LANG": "C"},
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "connect": "BLOCKED",
        "connect_ex": "BLOCKED",
        "creation": "BLOCKED",
        "dns": "BLOCKED",
        "listen": "BLOCKED",
        "sendmsg": "BLOCKED",
        "sendto": "BLOCKED",
    }


def test_helper_real_child_emits_exactly_one_strict_typed_json_document() -> None:
    helper_path = Path(helper.__file__).resolve(strict=True)
    completed = subprocess.run(
        [sys.executable, "-I", helper_path.as_posix()],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={
            "CUDA_VISIBLE_DEVICES": "-1",
            "PYTHONNOUSERSITE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "LC_ALL": "C",
            "LANG": "C",
        },
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout.count("\n") == 1
    payload = json.loads(completed.stdout)
    assert set(payload) == {
        "schema_version",
        "status",
        *training.SFT_GPU_HELPER_FACT_FIELDS,
    }
    assert payload["schema_version"] == "voice2task-sft-gpu-helper-v2"
    assert payload["status"] == "CUDA_UNAVAILABLE"
    assert payload["cuda_available"] is False


def test_gpu_probe_orders_pre_occupancy_helper_and_post_occupancy_with_exact_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "3")
    events: list[tuple[str, str]] = []
    monkeypatch.setattr(
        training,
        "_sample_sft_gpu_compute_process_count",
        lambda selector: events.append(("occupancy", selector)) or 0,
        raising=False,
    )
    monkeypatch.setattr(
        training,
        "_run_sft_gpu_fact_helper",
        lambda selector: events.append(("helper", selector)) or _helper_result(),
        raising=False,
    )

    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001

    assert blockers == []
    assert events == [("occupancy", "3"), ("helper", "3"), ("occupancy", "3")]
    assert facts["compute_process_count"] == 0
    assert facts["idle_verified"] is True


def test_gpu_probe_repeats_full_sequence_without_pid_inference_or_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "GPU-selector")
    events: list[str] = []
    monkeypatch.setattr(
        training,
        "_sample_sft_gpu_compute_process_count",
        lambda selector: events.append(f"occupancy:{selector}") or 0,
        raising=False,
    )
    monkeypatch.setattr(
        training,
        "_run_sft_gpu_fact_helper",
        lambda selector: events.append(f"helper:{selector}") or _helper_result(),
        raising=False,
    )

    first = training._probe_sft_gpu()  # noqa: SLF001
    second = training._probe_sft_gpu()  # noqa: SLF001

    assert first[1] == second[1] == []
    assert events == [
        "occupancy:GPU-selector",
        "helper:GPU-selector",
        "occupancy:GPU-selector",
        "occupancy:GPU-selector",
        "helper:GPU-selector",
        "occupancy:GPU-selector",
    ]
    serialized = json.dumps([first, second], sort_keys=True).lower()
    for forbidden in ("pid", "username", "uuid", "hostname", "command", "selector"):
        assert forbidden not in serialized


def test_gpu_probe_blocks_preexisting_occupancy_without_starting_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    helper_calls: list[str] = []
    monkeypatch.setattr(training, "_sample_sft_gpu_compute_process_count", lambda selector: 1, raising=False)
    monkeypatch.setattr(
        training,
        "_run_sft_gpu_fact_helper",
        lambda selector: helper_calls.append(selector),
        raising=False,
    )

    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001

    assert blockers == ["GPU_BUSY"]
    assert helper_calls == []
    assert facts["compute_process_count"] == 1
    assert facts["idle_verified"] is False


def test_gpu_probe_blocks_post_helper_occupancy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    samples = iter([0, 1])
    monkeypatch.setattr(
        training,
        "_sample_sft_gpu_compute_process_count",
        lambda selector: next(samples),
        raising=False,
    )
    monkeypatch.setattr(training, "_run_sft_gpu_fact_helper", lambda selector: _helper_result(), raising=False)

    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001

    assert blockers == ["GPU_BUSY"]
    assert facts["compute_process_count"] == 1
    assert facts["idle_verified"] is False


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError("private timeout detail"),
        RuntimeError("private helper detail /workspace/secret"),
    ],
)
def test_gpu_probe_converts_helper_failure_to_private_safe_blocker(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    sample_calls: list[str] = []
    monkeypatch.setattr(
        training,
        "_sample_sft_gpu_compute_process_count",
        lambda selector: sample_calls.append(selector) or 0,
        raising=False,
    )
    monkeypatch.setattr(
        training,
        "_run_sft_gpu_fact_helper",
        lambda selector: (_ for _ in ()).throw(failure),
        raising=False,
    )

    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001

    assert blockers == ["GPU_OCCUPANCY_PROBE_FAILED"]
    assert sample_calls == ["0", "0"]
    serialized = json.dumps(facts, sort_keys=True)
    assert "private" not in serialized
    assert "/workspace" not in serialized


@pytest.mark.parametrize(
    ("status", "expected_blocker"),
    [
        ("CUDA_UNAVAILABLE", "CUDA_UNAVAILABLE"),
        ("CUDA_PROBE_FAILED", "CUDA_PROBE_FAILED"),
    ],
)
def test_gpu_probe_preserves_typed_helper_failure(
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    expected_blocker: str,
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(training, "_sample_sft_gpu_compute_process_count", lambda selector: 0)
    monkeypatch.setattr(
        training,
        "_run_sft_gpu_fact_helper",
        lambda selector: _helper_result(
            status,
            cuda_available=False,
            visible_device_count=0,
            name=None,
            compute_capability=None,
            total_memory_gib=None,
            free_memory_gib=None,
            cuda_version="unknown",
            bf16_supported=False,
        ),
    )

    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001

    assert blockers == [expected_blocker]
    assert facts["idle_verified"] is True


@pytest.mark.parametrize(
    "malformed",
    [
        {},
        {"cuda_available": True},
        {**_helper_result(), "visible_device_count": "1"},
        {**_helper_result(), "private_path": "/workspace/secret"},
        _helper_result("UNKNOWN_STATUS"),
    ],
)
def test_gpu_probe_fails_closed_on_malformed_helper_result(
    monkeypatch: pytest.MonkeyPatch,
    malformed: dict[str, Any],
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(training, "_sample_sft_gpu_compute_process_count", lambda selector: 0, raising=False)
    monkeypatch.setattr(training, "_run_sft_gpu_fact_helper", lambda selector: malformed, raising=False)

    facts, blockers = training._probe_sft_gpu()  # noqa: SLF001

    assert blockers == ["GPU_OCCUPANCY_PROBE_FAILED"]
    assert "/workspace" not in json.dumps(facts, sort_keys=True)


@pytest.mark.parametrize(
    "malformed",
    [
        _helper_result("OK", cuda_available=False),
        _helper_result("OK", visible_device_count=2),
        _helper_result("OK", name=None),
        _helper_result("CUDA_UNAVAILABLE", cuda_available=True),
        _helper_result("CUDA_PROBE_FAILED", name="NVIDIA A100-SXM4-80GB"),
        _helper_result("GPU_SELECTION_NOT_SINGLE", visible_device_count=1),
        _helper_result("GPU_SELECTION_NOT_SINGLE", visible_device_count=2, bf16_supported=True),
    ],
)
def test_gpu_helper_protocol_rejects_cross_field_inconsistency(
    malformed: dict[str, Any],
) -> None:
    with pytest.raises(RuntimeError, match="^GPU_OCCUPANCY_PROBE_FAILED$"):
        training._validated_sft_gpu_helper_result(malformed)  # noqa: SLF001


def test_gpu_fact_helper_runner_uses_exact_selector_and_private_one_json_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    payload = {
        "schema_version": "voice2task-sft-gpu-helper-v2",
        **_helper_result(),
    }

    def fake_run(command: list[str], **kwargs: Any) -> Any:
        calls.append({"command": command, **kwargs})
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(training.subprocess, "run", fake_run)

    result = training._run_sft_gpu_fact_helper("7")  # noqa: SLF001

    assert result == _helper_result()
    assert calls[0]["command"] == [
        training.sys.executable,
        "-I",
        Path(helper.__file__).resolve(strict=True).as_posix(),
    ]
    assert calls[0]["env"] == {
        "CUDA_VISIBLE_DEVICES": "7",
        "PYTHONNOUSERSITE": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "LC_ALL": "C",
        "LANG": "C",
    }
    for forbidden in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "TOKEN",
        "PYTHONPATH",
        "PYTHONHOME",
        "LD_PRELOAD",
        "DYLD_INSERT_LIBRARIES",
    ):
        assert forbidden not in calls[0]["env"]
    assert os.path.isabs(calls[0]["command"][0])
    assert os.path.isabs(calls[0]["command"][2])
    assert calls[0]["capture_output"] is True
    assert calls[0]["text"] is True


@pytest.mark.parametrize(
    "result",
    [
        types.SimpleNamespace(returncode=1, stdout="", stderr="private error"),
        types.SimpleNamespace(returncode=0, stdout="not-json", stderr=""),
        types.SimpleNamespace(returncode=0, stdout="{}", stderr=""),
        types.SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "schema_version": "voice2task-sft-gpu-helper-v2",
                    **_helper_result("UNKNOWN_STATUS"),
                }
            ),
            stderr="",
        ),
    ],
)
def test_gpu_fact_helper_runner_rejects_nonzero_or_malformed_output(
    monkeypatch: pytest.MonkeyPatch,
    result: Any,
) -> None:
    monkeypatch.setattr(training.subprocess, "run", lambda *args, **kwargs: result)

    with pytest.raises(RuntimeError, match="GPU_OCCUPANCY_PROBE_FAILED"):
        training._run_sft_gpu_fact_helper("0")  # noqa: SLF001


def test_gpu_fact_helper_runner_converts_timeout_without_raw_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        training.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("/private/helper", 1)),
    )

    with pytest.raises(RuntimeError, match="^GPU_OCCUPANCY_PROBE_FAILED$"):
        training._run_sft_gpu_fact_helper("0")  # noqa: SLF001
