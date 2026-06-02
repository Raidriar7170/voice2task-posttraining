from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from voice2task.leak_scan import scan_paths

PRIVATE_SCAN_PREFIXES = (
    "/mnt/data/",
    "/Users/",
    "/root/",
    "/tmp/",
)


def _display_scan_path(path: Path) -> str:
    value = path.as_posix()
    if any(value.startswith(prefix) for prefix in PRIVATE_SCAN_PREFIXES):
        return "<private_path>"
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voice2task-report")
    subcommands = parser.add_subparsers(dest="command", required=True)
    leak = subcommands.add_parser("leak-scan")
    leak.add_argument("positional_paths", nargs="*", type=Path)
    leak.add_argument("--paths", nargs="+", type=Path)
    leak.add_argument("--output", type=Path)
    leak.add_argument("--max-public-jsonl-rows", type=int, default=5000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "leak-scan":
        paths = list(args.positional_paths)
        if args.paths:
            paths.extend(args.paths)
        if not paths:
            raise SystemExit("leak-scan requires at least one path")
        result = scan_paths(paths, max_public_jsonl_rows=args.max_public_jsonl_rows)
        payload = result.to_dict()
        payload["scanned_paths"] = [_display_scan_path(path) for path in paths]
        payload["max_public_jsonl_rows"] = args.max_public_jsonl_rows
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        output = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0 if result.ok else 1
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
