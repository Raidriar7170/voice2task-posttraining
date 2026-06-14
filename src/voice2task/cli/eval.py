from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.evaluation import (
    diagnose_alignment_mismatches,
    diagnose_constrained_contract_decoding,
    diagnose_heldout_family_strategy,
    diagnose_runtime_label_tiny_overfit_readiness,
    diagnose_schema_mismatches,
    diagnose_sft_contract_learning_signal,
    diagnose_source_alignment,
    diagnose_targeted_slot_value_residuals,
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
    write_heldout_family_strategy_report,
    write_metrics_report,
    write_runtime_label_tiny_overfit_diagnostic_report,
    write_schema_diagnostics_report,
    write_sft_contract_learning_signal_report,
    write_source_diagnostics_report,
    write_targeted_slot_value_residual_report,
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
    diagnose_constrained.add_argument(
        "--evidence-context",
        choices=("local_decoder_output_shape_hardening", "a100_prediction_rerun"),
        default="local_decoder_output_shape_hardening",
    )

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

    diagnose_learning = subcommands.add_parser("diagnose-sft-learning-signal")
    diagnose_learning.add_argument("--sft", type=Path, required=True)
    diagnose_learning.add_argument("--manifest", type=Path, required=True)
    diagnose_learning.add_argument("--prior-repair-diagnosis", type=Path)
    diagnose_learning.add_argument("--output", type=Path, required=True)
    diagnose_learning.add_argument("--title", default="Voice2Task SFT contract learning-signal evidence")

    diagnose_runtime_tiny = subcommands.add_parser("diagnose-runtime-label-tiny-overfit")
    diagnose_runtime_tiny.add_argument("--manifest", type=Path, required=True)
    diagnose_runtime_tiny.add_argument("--learning-signal", type=Path)
    diagnose_runtime_tiny.add_argument("--prior-repair-diagnosis", type=Path)
    diagnose_runtime_tiny.add_argument("--runtime-label-evidence", type=Path)
    diagnose_runtime_tiny.add_argument("--tiny-overfit-evidence", type=Path)
    diagnose_runtime_tiny.add_argument("--output", type=Path, required=True)
    diagnose_runtime_tiny.add_argument(
        "--title",
        default="Voice2Task runtime-label and tiny-overfit diagnostic",
    )

    diagnose_heldout_strategy = subcommands.add_parser("diagnose-heldout-family-strategy")
    diagnose_heldout_strategy.add_argument("--sft", type=Path, required=True)
    diagnose_heldout_strategy.add_argument("--manifest", type=Path, required=True)
    diagnose_heldout_strategy.add_argument("--tiny-overfit-manifest", type=Path, required=True)
    diagnose_heldout_strategy.add_argument("--heldout-manifest", type=Path, required=True)
    diagnose_heldout_strategy.add_argument("--dev-alignment", type=Path, required=True)
    diagnose_heldout_strategy.add_argument("--test-alignment", type=Path, required=True)
    diagnose_heldout_strategy.add_argument("--dev-schema", type=Path, required=True)
    diagnose_heldout_strategy.add_argument("--test-schema", type=Path, required=True)
    diagnose_heldout_strategy.add_argument("--output", type=Path, required=True)
    diagnose_heldout_strategy.add_argument(
        "--title",
        default="Voice2Task held-out family strategy diagnosis",
    )

    diagnose_targeted_residuals = subcommands.add_parser("diagnose-targeted-slot-value-residuals")
    diagnose_targeted_residuals.add_argument("--targeted-manifest", type=Path, required=True)
    diagnose_targeted_residuals.add_argument("--dev-gold", type=Path, required=True)
    diagnose_targeted_residuals.add_argument("--dev-predictions", type=Path, required=True)
    diagnose_targeted_residuals.add_argument("--dev-alignment", type=Path, required=True)
    diagnose_targeted_residuals.add_argument("--test-gold", type=Path, required=True)
    diagnose_targeted_residuals.add_argument("--test-predictions", type=Path, required=True)
    diagnose_targeted_residuals.add_argument("--test-alignment", type=Path, required=True)
    diagnose_targeted_residuals.add_argument("--output", type=Path, required=True)
    diagnose_targeted_residuals.add_argument(
        "--title",
        default="Voice2Task targeted slot value residual diagnosis",
    )

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
        diagnostics = diagnose_constrained_contract_decoding(
            predictions,
            read_jsonl(args.raw_decoded_summary),
            evidence_context=args.evidence_context,
        )
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
    if args.command == "diagnose-sft-learning-signal":
        diagnostics = diagnose_sft_contract_learning_signal(
            load_rows_path=args.sft,
            manifest_path=args.manifest,
            prior_repair_diagnosis=read_json(args.prior_repair_diagnosis)
            if args.prior_repair_diagnosis
            else None,
        )
        paths = write_sft_contract_learning_signal_report(diagnostics, output_dir=args.output, title=args.title)
        print(json.dumps({"ok": True, "paths": {key: value.as_posix() for key, value in paths.items()}}, indent=2))
        return 0
    if args.command == "diagnose-runtime-label-tiny-overfit":
        diagnostics = diagnose_runtime_label_tiny_overfit_readiness(
            manifest_path=args.manifest,
            learning_signal=read_json(args.learning_signal) if args.learning_signal else None,
            prior_repair_diagnosis=read_json(args.prior_repair_diagnosis)
            if args.prior_repair_diagnosis
            else None,
            runtime_label_evidence=read_json(args.runtime_label_evidence)
            if args.runtime_label_evidence
            else None,
            tiny_overfit_evidence=read_json(args.tiny_overfit_evidence) if args.tiny_overfit_evidence else None,
        )
        paths = write_runtime_label_tiny_overfit_diagnostic_report(
            diagnostics,
            output_dir=args.output,
            title=args.title,
        )
        print(json.dumps({"ok": True, "paths": {key: value.as_posix() for key, value in paths.items()}}, indent=2))
        return 0
    if args.command == "diagnose-heldout-family-strategy":
        diagnostics = diagnose_heldout_family_strategy(
            load_rows_path=args.sft,
            manifest_path=args.manifest,
            tiny_overfit_manifest=read_json(args.tiny_overfit_manifest),
            heldout_manifest=read_json(args.heldout_manifest),
            heldout_alignment_by_split={
                "dev": read_json(args.dev_alignment),
                "test": read_json(args.test_alignment),
            },
            heldout_schema_by_split={
                "dev": read_json(args.dev_schema),
                "test": read_json(args.test_schema),
            },
        )
        paths = write_heldout_family_strategy_report(
            diagnostics,
            output_dir=args.output,
            title=args.title,
        )
        print(json.dumps({"ok": True, "paths": {key: value.as_posix() for key, value in paths.items()}}, indent=2))
        return 0
    if args.command == "diagnose-targeted-slot-value-residuals":
        diagnostics = diagnose_targeted_slot_value_residuals(
            targeted_manifest=read_json(args.targeted_manifest),
            rows_by_split={
                "dev": load_sft_rows(args.dev_gold),
                "test": load_sft_rows(args.test_gold),
            },
            predictions_by_split={
                "dev": load_predictions(args.dev_predictions),
                "test": load_predictions(args.test_predictions),
            },
            alignment_by_split={
                "dev": read_json(args.dev_alignment),
                "test": read_json(args.test_alignment),
            },
        )
        paths = write_targeted_slot_value_residual_report(
            diagnostics,
            output_dir=args.output,
            title=args.title,
        )
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
