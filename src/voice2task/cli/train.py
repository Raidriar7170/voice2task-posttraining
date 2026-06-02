from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.training import run_dpo, run_sft


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voice2task-train")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("sft", "dpo"):
        subparser = subcommands.add_parser(name)
        subparser.add_argument("--config", type=Path, required=True)
        subparser.add_argument("--manifest", type=Path, required=True)
        subparser.add_argument("--output-dir", type=Path, required=True)
        mode = subparser.add_mutually_exclusive_group()
        mode.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
        mode.add_argument("--run-training", dest="dry_run", action="store_false")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "sft":
        metadata = run_sft(args.config, args.manifest, args.output_dir, dry_run=args.dry_run)
    elif args.command == "dpo":
        metadata = run_dpo(args.config, args.manifest, args.output_dir, dry_run=args.dry_run)
    else:
        raise AssertionError(f"unhandled command: {args.command}")
    print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
