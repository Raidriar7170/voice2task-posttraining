from __future__ import annotations

import importlib
import json
import sys
from typing import Any

SCHEMA_VERSION = "voice2task-sft-gpu-helper-v2"
_NETWORK_AUDIT_EVENTS = {
    "socket.__new__",
    "socket.bind",
    "socket.connect",
    "socket.getaddrinfo",
    "socket.gethostbyaddr",
    "socket.gethostbyname",
    "socket.gethostbyname_ex",
    "socket.sendto",
}


def _empty_gpu_facts(
    *,
    cuda_available: bool = False,
    visible_device_count: int = 0,
    cuda_version: str = "unknown",
) -> dict[str, Any]:
    return {
        "cuda_available": cuda_available,
        "visible_device_count": visible_device_count,
        "name": None,
        "compute_capability": None,
        "total_memory_gib": None,
        "free_memory_gib": None,
        "cuda_version": cuda_version,
        "bf16_supported": False,
    }


def _result(status: str, facts: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "status": status, **facts}


def _network_audit_hook(event: str, args: tuple[Any, ...]) -> None:
    del args
    if event in _NETWORK_AUDIT_EVENTS:
        raise PermissionError("NETWORK_ACCESS_BLOCKED")


def collect_gpu_result(torch_module: Any | None = None) -> dict[str, Any]:
    if torch_module is None:
        try:
            torch_module = importlib.import_module("torch")
        except PermissionError:
            return _result("CUDA_PROBE_FAILED", _empty_gpu_facts())
        except Exception:
            return _result("CUDA_UNAVAILABLE", _empty_gpu_facts())

    try:
        cuda = torch_module.cuda
        cuda_version = str(getattr(torch_module.version, "cuda", None) or "unknown")
        if not bool(cuda.is_available()):
            return _result(
                "CUDA_UNAVAILABLE",
                _empty_gpu_facts(cuda_version=cuda_version),
            )
        visible_device_count = int(cuda.device_count())
        if visible_device_count != 1:
            return _result(
                "GPU_SELECTION_NOT_SINGLE",
                _empty_gpu_facts(
                    cuda_available=True,
                    visible_device_count=visible_device_count,
                    cuda_version=cuda_version,
                ),
            )
        properties = cuda.get_device_properties(0)
        capability = tuple(int(value) for value in cuda.get_device_capability(0))
        free_memory_bytes, _ = cuda.mem_get_info(0)
        facts = {
            "cuda_available": True,
            "visible_device_count": 1,
            "name": str(cuda.get_device_name(0)),
            "compute_capability": f"{capability[0]}.{capability[1]}",
            "total_memory_gib": round(
                int(getattr(properties, "total_memory", 0)) / float(1024**3),
                3,
            ),
            "free_memory_gib": round(int(free_memory_bytes) / float(1024**3), 3),
            "cuda_version": cuda_version,
            "bf16_supported": bool(cuda.is_bf16_supported()),
        }
    except Exception:
        return _result("CUDA_PROBE_FAILED", _empty_gpu_facts())
    return _result("OK", facts)


def main_result() -> dict[str, Any]:
    try:
        sys.addaudithook(_network_audit_hook)
    except Exception:
        return _result("CUDA_PROBE_FAILED", _empty_gpu_facts())
    return collect_gpu_result()


def main() -> int:
    print(json.dumps(main_result(), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
