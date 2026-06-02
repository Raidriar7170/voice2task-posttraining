from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.evaluation import (
    evaluate_predictions,
    load_predictions,
    load_sft_rows,
    prompt_fixture_predictions,
    rule_baseline_predictions,
    run_execution_smoke,
    write_predictions,
)
from voice2task.reports import write_metrics_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voice2task-eval")
    subcommands = parser.add_subparsers(dest="command", required=True)

    baseline = subcommands.add_parser("baseline")
    baseline.add_argument("--gold", type=Path, required=True)
    baseline.add_argument("--output", type=Path, required=True)

    prompt_baseline = subcommands.add_parser("prompt-baseline")
    prompt_baseline.add_argument("--gold", type=Path, required=True)
    prompt_baseline.add_argument("--fixture", type=Path, required=True)
    prompt_baseline.add_argument("--output", type=Path, required=True)

    metrics = subcommands.add_parser("metrics")
    metrics.add_argument("--gold", type=Path, required=True)
    metrics.add_argument("--predictions", type=Path, required=True)
    metrics.add_argument("--output", type=Path, required=True)
    metrics.add_argument("--title", default="Voice2Task public sample metrics")

    smoke = subcommands.add_parser("smoke")
    smoke.add_argument("--gold", type=Path, required=True)
    smoke.add_argument("--predictions", type=Path, required=True)
    smoke.add_argument("--target", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "baseline":
        rows = load_sft_rows(args.gold)
        predictions = rule_baseline_predictions(rows)
        write_predictions(args.output, predictions)
        print(json.dumps({"ok": True, "output": args.output.as_posix(), "count": len(predictions)}, indent=2))
        return 0
    if args.command == "prompt-baseline":
        rows = load_sft_rows(args.gold)
        predictions = prompt_fixture_predictions(rows, args.fixture)
        write_predictions(args.output, predictions)
        print(json.dumps({"ok": True, "output": args.output.as_posix(), "count": len(predictions)}, indent=2))
        return 0
    if args.command == "metrics":
        rows = load_sft_rows(args.gold)
        predictions = load_predictions(args.predictions)
        eval_result = evaluate_predictions(rows, predictions)
        paths = write_metrics_report(eval_result, output_dir=args.output, title=args.title)
        print(json.dumps({"ok": True, "paths": {key: value.as_posix() for key, value in paths.items()}}, indent=2))
        return 0
    if args.command == "smoke":
        rows = load_sft_rows(args.gold)
        predictions = load_predictions(args.predictions)
        smoke_result = run_execution_smoke(rows, predictions, enabled=True, target_path=args.target)
        print(json.dumps(smoke_result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if smoke_result.failed == 0 else 1
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
