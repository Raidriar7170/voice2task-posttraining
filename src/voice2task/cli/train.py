from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.io import write_json
from voice2task.training import inspect_sft_objective_from_manifest, run_dpo, run_sft, run_sft_prediction_export


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
    prediction = subcommands.add_parser("sft-predict")
    prediction.add_argument("--config", type=Path, required=True)
    prediction.add_argument("--manifest", type=Path, required=True)
    prediction.add_argument("--output", type=Path, required=True)
    prediction_mode = prediction.add_mutually_exclusive_group()
    prediction_mode.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    prediction_mode.add_argument("--run-prediction", dest="dry_run", action="store_false")
    prediction.add_argument("--fixture-mode", action="store_true")
    objective = subcommands.add_parser("sft-inspect-objective")
    objective.add_argument("--manifest", type=Path, required=True)
    objective.add_argument("--split", default="train")
    objective.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "sft":
        metadata = run_sft(args.config, args.manifest, args.output_dir, dry_run=args.dry_run)
    elif args.command == "dpo":
        metadata = run_dpo(args.config, args.manifest, args.output_dir, dry_run=args.dry_run)
    elif args.command == "sft-predict":
        metadata = run_sft_prediction_export(
            args.config,
            args.manifest,
            args.output,
            dry_run=args.dry_run,
            fixture_mode=args.fixture_mode,
        )
    elif args.command == "sft-inspect-objective":
        metadata = inspect_sft_objective_from_manifest(args.manifest, split=args.split)
    else:
        raise AssertionError(f"unhandled command: {args.command}")
    if args.command == "sft-inspect-objective" and args.output:
        write_json(args.output, metadata)
    else:
        print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
