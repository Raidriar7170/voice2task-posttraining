from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.evaluation import (
    diagnose_alignment_mismatches,
    diagnose_constrained_contract_decoding,
    diagnose_schema_mismatches,
    diagnose_source_alignment,
    evaluate_predictions,
    load_predictions,
    load_sft_rows,
    prompt_fixture_predictions,
    rule_baseline_predictions,
    run_execution_smoke,
    write_predictions,
)
from voice2task.io import read_json, read_jsonl
from voice2task.reports import (
    write_alignment_diagnostics_report,
    write_constrained_decoding_diagnosis_report,
    write_metrics_report,
    write_schema_diagnostics_report,
    write_source_diagnostics_report,
)


def _existing_artifact_paths(predictions_path: Path, prediction_metadata: dict[str, object]) -> dict[str, str]:
    artifact_dir = predictions_path.parent
    candidates = {
        "predictions": predictions_path,
        "metrics": artifact_dir / "metrics.json",
        "metrics_markdown": artifact_dir / "metrics.md",
        "report": artifact_dir / "report.md",
        "manifest": artifact_dir / "manifest.json",
    }
    for section_name in ("diagnostic_artifacts", "sidecars"):
        section = prediction_metadata.get(section_name)
        if isinstance(section, dict):
            for key, value in section.items():
                if isinstance(value, str) and value:
                    candidates[str(key)] = Path(value)
    return {key: path.as_posix() for key, path in candidates.items() if path.exists()}


def _load_objective_inspection(
    predictions_path: Path,
    prediction_metadata: dict[str, object],
) -> dict[str, object] | None:
    diagnostic_artifacts = prediction_metadata.get("diagnostic_artifacts")
    candidate: Path | None = None
    if isinstance(diagnostic_artifacts, dict):
        objective_path = diagnostic_artifacts.get("objective_inspection")
        if isinstance(objective_path, str) and objective_path:
            candidate = Path(objective_path)
    if candidate is None:
        candidate = predictions_path.parent / "objective_inspection.json"
    if not candidate.exists():
        return None
    payload = read_json(candidate)
    return payload if isinstance(payload, dict) else None


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

    diagnose_schema = subcommands.add_parser("diagnose-schema")
    diagnose_schema.add_argument("--gold", type=Path, required=True)
    diagnose_schema.add_argument("--predictions", type=Path, required=True)
    diagnose_schema.add_argument("--output", type=Path, required=True)
    diagnose_schema.add_argument("--title", default="Voice2Task schema diagnostics")

    diagnose_constrained = subcommands.add_parser("diagnose-constrained-decoding")
    diagnose_constrained.add_argument("--predictions", type=Path, required=True)
    diagnose_constrained.add_argument("--raw-decoded-summary", type=Path, required=True)
    diagnose_constrained.add_argument("--output", type=Path, required=True)
    diagnose_constrained.add_argument("--title", default="Voice2Task constrained decoding diagnosis")

    diagnose_alignment = subcommands.add_parser("diagnose-alignment")
    diagnose_alignment.add_argument("--gold", type=Path, required=True)
    diagnose_alignment.add_argument("--predictions", type=Path, required=True)
    diagnose_alignment.add_argument("--output", type=Path, required=True)
    diagnose_alignment.add_argument("--title", default="Voice2Task alignment diagnostics")

    diagnose_source = subcommands.add_parser("diagnose-source")
    diagnose_source.add_argument("--gold", type=Path, required=True)
    diagnose_source.add_argument("--predictions", type=Path, required=True)
    diagnose_source.add_argument("--training-config", type=Path, required=True)
    diagnose_source.add_argument("--prediction-metadata", type=Path, required=True)
    diagnose_source.add_argument("--output", type=Path, required=True)
    diagnose_source.add_argument("--title", default="Voice2Task source diagnostics")

    smoke = subcommands.add_parser("smoke")
    smoke.add_argument("--gold", type=Path, required=True)
    smoke.add_argument("--predictions", type=Path, required=True)
    smoke.add_argument("--target", type=Path, required=True)
    smoke.add_argument("--output", type=Path)
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
    if args.command == "diagnose-schema":
        rows = load_sft_rows(args.gold)
        predictions = load_predictions(args.predictions)
        diagnostics = diagnose_schema_mismatches(rows, predictions)
        paths = write_schema_diagnostics_report(diagnostics, output_dir=args.output, title=args.title)
        print(json.dumps({"ok": True, "paths": {key: value.as_posix() for key, value in paths.items()}}, indent=2))
        return 0
    if args.command == "diagnose-constrained-decoding":
        predictions = load_predictions(args.predictions)
        diagnostics = diagnose_constrained_contract_decoding(predictions, read_jsonl(args.raw_decoded_summary))
        paths = write_constrained_decoding_diagnosis_report(diagnostics, output_dir=args.output, title=args.title)
        print(json.dumps({"ok": True, "paths": {key: value.as_posix() for key, value in paths.items()}}, indent=2))
        return 0
    if args.command == "diagnose-alignment":
        rows = load_sft_rows(args.gold)
        predictions = load_predictions(args.predictions)
        diagnostics = diagnose_alignment_mismatches(rows, predictions)
        paths = write_alignment_diagnostics_report(diagnostics, output_dir=args.output, title=args.title)
        print(json.dumps({"ok": True, "paths": {key: value.as_posix() for key, value in paths.items()}}, indent=2))
        return 0
    if args.command == "diagnose-source":
        rows = load_sft_rows(args.gold)
        predictions = load_predictions(args.predictions)
        prediction_metadata = read_json(args.prediction_metadata)
        diagnostics = diagnose_source_alignment(
            rows,
            predictions,
            training_config=read_json(args.training_config),
            prediction_metadata=prediction_metadata,
            prior_artifact_paths=_existing_artifact_paths(args.predictions, prediction_metadata),
            objective_inspection=_load_objective_inspection(args.predictions, prediction_metadata),
        )
        paths = write_source_diagnostics_report(diagnostics, output_dir=args.output, title=args.title)
        print(json.dumps({"ok": True, "paths": {key: value.as_posix() for key, value in paths.items()}}, indent=2))
        return 0
    if args.command == "smoke":
        rows = load_sft_rows(args.gold)
        predictions = load_predictions(args.predictions)
        smoke_result = run_execution_smoke(rows, predictions, enabled=True, target_path=args.target)
        output = json.dumps(smoke_result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0 if smoke_result.failed == 0 else 1
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
