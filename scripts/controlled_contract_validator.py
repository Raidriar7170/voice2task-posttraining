from __future__ import annotations

import json
import sys


def main() -> int:
    payload = json.load(sys.stdin)
    contract = payload.get("contract", {})
    required = {
        "task_type",
        "route",
        "safety",
        "confirmation_required",
        "slots",
        "normalized_command",
        "language",
        "contract_version",
    }
    missing = sorted(required - set(contract))
    ok = not missing and contract.get("contract_version") == "v1" and contract.get("language") == "zh-CN"
    print(json.dumps({"ok": ok, "missing": missing}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
