from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.io import write_json
from voice2task.training import (
    inspect_sft_objective_from_manifest,
    prepare_sft_runtime_label_provenance,
    public_training_result,
    run_dpo,
    run_sft,
    run_sft_prediction_export,
    run_sft_preflight,
    run_sft_runtime_label_provenance_check,
)


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
    preflight = subcommands.add_parser("sft-preflight")
    preflight.add_argument("--config", type=Path, required=True)
    preflight.add_argument("--manifest", type=Path, required=True)
    preflight.add_argument("--output-dir", type=Path, required=True)
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
    runtime_prep = subcommands.add_parser("sft-prepare-runtime-label-provenance")
    runtime_prep.add_argument("--config", type=Path, required=True)
    runtime_prep.add_argument("--manifest", type=Path, required=True)
    runtime_prep.add_argument("--output", type=Path, required=True)
    runtime_check = subcommands.add_parser("sft-runtime-label-provenance-check")
    runtime_check.add_argument("--config", type=Path, required=True)
    runtime_check.add_argument("--manifest", type=Path, required=True)
    runtime_check.add_argument("--split", default="train")
    runtime_check.add_argument("--output", type=Path, required=True)
    runtime_check.add_argument("--run-runtime-check", action="store_true", default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "sft":
            metadata = run_sft(args.config, args.manifest, args.output_dir, dry_run=args.dry_run)
        elif args.command == "sft-preflight":
            metadata = run_sft_preflight(args.config, args.manifest, args.output_dir)
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
        elif args.command == "sft-prepare-runtime-label-provenance":
            metadata = prepare_sft_runtime_label_provenance(args.config, args.manifest, metadata_path=args.output)
        elif args.command == "sft-runtime-label-provenance-check":
            metadata = run_sft_runtime_label_provenance_check(
                args.config,
                args.manifest,
                split=args.split,
                output_path=args.output,
                run_runtime_check=args.run_runtime_check,
            )
        else:
            raise AssertionError(f"unhandled command: {args.command}")
    except Exception:
        metadata = {
            "schema_version": "voice2task-training-result-v1",
            "training_status": "training_failed",
            "blockers": ["TRAINING_RUNTIME_ERROR"],
        }
        print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    if args.command in {"sft", "dpo"}:
        metadata = public_training_result(metadata)
    if args.command == "sft-inspect-objective" and args.output:
        write_json(args.output, metadata)
    elif args.command == "sft-prepare-runtime-label-provenance":
        write_json(args.output, metadata)
    elif args.command == "sft-runtime-label-provenance-check":
        if not args.output.exists():
            print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))
    if args.command == "sft-preflight":
        return 0 if metadata.get("ready") is True else 1
    if args.command in {"sft", "dpo"}:
        return 0 if metadata.get("training_status") in {"dry_run", "training_completed"} else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
