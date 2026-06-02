from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.dataset import build_local_private_corpus, build_public_sample_dataset
from voice2task.dpo import summarize_dpo_slices, validate_dpo_pairs_file
from voice2task.validation import validate_dataset_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voice2task-data")
    subcommands = parser.add_subparsers(dest="command", required=True)

    public_parser = subcommands.add_parser("build-public")
    public_parser.add_argument("--seed", type=Path, required=True)
    public_parser.add_argument("--output", type=Path, required=True)

    local_parser = subcommands.add_parser("build-local")
    local_parser.add_argument("--seed-trace", type=Path, required=True)
    local_parser.add_argument("--output", type=Path, required=True)

    validate_parser = subcommands.add_parser("validate")
    validate_parser.add_argument("--sft", type=Path, required=True)
    validate_parser.add_argument("--dpo", type=Path, required=True)
    validate_parser.add_argument("--manifest", type=Path, required=True)
    validate_parser.add_argument("--public", action="store_true")

    dpo_parser = subcommands.add_parser("dpo-check")
    dpo_parser.add_argument("--dpo", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build-public":
        manifest = build_public_sample_dataset(seed_path=args.seed, output_dir=args.output)
        print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "build-local":
        manifest = build_local_private_corpus(seed_trace_path=args.seed_trace, output_dir=args.output)
        print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "validate":
        result = validate_dataset_artifacts(
            sft_path=args.sft,
            dpo_path=args.dpo,
            manifest_path=args.manifest,
            public=args.public,
        )
        payload = {"ok": result.ok, "failures": result.failures, "counts": result.counts}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if result.ok else 1
    if args.command == "dpo-check":
        pairs = validate_dpo_pairs_file(args.dpo)
        print(json.dumps(summarize_dpo_slices(pairs), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
