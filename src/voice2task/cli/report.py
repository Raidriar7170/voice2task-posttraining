from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from voice2task.io import read_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import (
    write_merged_slot_value_heldout_eval_report,
    write_runtime_label_provenance_check_evidence_pack,
    write_runtime_label_provenance_prep_evidence_pack,
    write_sft_label_provenance_evidence_pack,
    write_slot_value_candidate_sft_probe_report,
)

PRIVATE_SCAN_PREFIXES = (
    "/mnt/data/",
    "/Users/",
    "/root/",
    "/tmp/",
    "/private/",
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
    provenance = subcommands.add_parser("sft-label-provenance")
    provenance.add_argument("--objective-inspection", type=Path, required=True)
    provenance.add_argument("--output-dir", type=Path, required=True)
    provenance.add_argument("--prior-artifact", action="append", default=[])
    runtime_prep = subcommands.add_parser("runtime-label-provenance-prep")
    runtime_prep.add_argument("--prep-metadata", type=Path, required=True)
    runtime_prep.add_argument("--output-dir", type=Path, required=True)
    runtime_prep.add_argument("--prior-artifact", action="append", default=[])
    runtime_check = subcommands.add_parser("runtime-label-provenance-check")
    runtime_check.add_argument("--runtime-metadata", type=Path, required=True)
    runtime_check.add_argument("--output-dir", type=Path, required=True)
    runtime_check.add_argument("--leak-scan-result", type=Path)
    runtime_check.add_argument("--expected-manifest-id")
    runtime_check.add_argument("--prior-artifact", action="append", default=[])
    candidate_probe = subcommands.add_parser("slot-value-candidate-sft-probe")
    candidate_probe.add_argument("--dry-run-metadata", type=Path)
    candidate_probe.add_argument("--training-metadata", type=Path)
    candidate_probe.add_argument("--prediction-metadata", type=Path)
    candidate_probe.add_argument("--metrics", type=Path)
    candidate_probe.add_argument("--candidate-manifest", type=Path, required=True)
    candidate_probe.add_argument("--materialization-manifest", type=Path, required=True)
    candidate_probe.add_argument("--sft-config", type=Path, required=True)
    candidate_probe.add_argument("--prediction-config", type=Path, required=True)
    candidate_probe.add_argument("--a100-ssh-status", required=True)
    candidate_probe.add_argument("--a100-output-root-status", required=True)
    candidate_probe.add_argument("--a100-idle-gpu-status", required=True)
    candidate_probe.add_argument("--a100-selected-gpu-index", required=True)
    candidate_probe.add_argument("--a100-train-dependencies", default="")
    candidate_probe.add_argument("--a100-missing-dependencies", default="")
    candidate_probe.add_argument("--a100-training-status")
    candidate_probe.add_argument("--a100-prediction-status")
    candidate_probe.add_argument("--remote-workspace-status", default="not_recorded")
    candidate_probe.add_argument("--dependency-env-status", default="not_recorded")
    candidate_probe.add_argument("--sync-status", default="not_recorded")
    candidate_probe.add_argument("--output", type=Path, required=True)

    merged_eval = subcommands.add_parser("merged-slot-value-heldout-eval")
    merged_eval.add_argument("--public-manifest", type=Path, required=True)
    merged_eval.add_argument("--training-metadata", type=Path)
    merged_eval.add_argument("--train-metrics", type=Path, required=True)
    merged_eval.add_argument("--dev-metrics", type=Path, required=True)
    merged_eval.add_argument("--test-metrics", type=Path, required=True)
    merged_eval.add_argument("--train-prediction-metadata", type=Path)
    merged_eval.add_argument("--dev-prediction-metadata", type=Path)
    merged_eval.add_argument("--test-prediction-metadata", type=Path)
    merged_eval.add_argument("--prior-targeted-manifest", type=Path)
    merged_eval.add_argument("--output", type=Path, required=True)
    return parser


def _comma_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _prior_artifacts(values: list[str]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit("--prior-artifact values must use name=path")
        name, path = value.split("=", 1)
        if not name.strip() or not path.strip():
            raise SystemExit("--prior-artifact values must use non-empty name=path")
        artifacts[name.strip()] = path.strip()
    return artifacts


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
        findings = payload.get("findings")
        if isinstance(findings, list):
            for finding in findings:
                if isinstance(finding, dict):
                    finding["path"] = _display_scan_path(Path(str(finding.get("path", ""))))
        payload["max_public_jsonl_rows"] = args.max_public_jsonl_rows
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        output = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0 if result.ok else 1
    if args.command == "sft-label-provenance":
        report_paths = write_sft_label_provenance_evidence_pack(
            objective_inspection=read_json(args.objective_inspection),
            output_dir=args.output_dir,
            prior_artifacts=_prior_artifacts(args.prior_artifact),
        )
        print(
            json.dumps(
                {"ok": True, "paths": {key: value.as_posix() for key, value in report_paths.items()}},
                indent=2,
            )
        )
        return 0
    if args.command == "runtime-label-provenance-prep":
        report_paths = write_runtime_label_provenance_prep_evidence_pack(
            prep_metadata=read_json(args.prep_metadata),
            output_dir=args.output_dir,
            prior_artifacts=_prior_artifacts(args.prior_artifact),
        )
        print(
            json.dumps(
                {"ok": True, "paths": {key: value.as_posix() for key, value in report_paths.items()}},
                indent=2,
            )
        )
        return 0
    if args.command == "runtime-label-provenance-check":
        report_paths = write_runtime_label_provenance_check_evidence_pack(
            runtime_metadata=read_json(args.runtime_metadata),
            output_dir=args.output_dir,
            leak_scan_result=read_json(args.leak_scan_result) if args.leak_scan_result else None,
            prior_artifacts=_prior_artifacts(args.prior_artifact),
            expected_manifest_id=args.expected_manifest_id,
        )
        print(
            json.dumps(
                {"ok": True, "paths": {key: value.as_posix() for key, value in report_paths.items()}},
                indent=2,
            )
        )
        return 0
    if args.command == "slot-value-candidate-sft-probe":
        report_paths = write_slot_value_candidate_sft_probe_report(
            candidate_manifest=read_json(args.candidate_manifest),
            materialization_manifest=read_json(args.materialization_manifest),
            sft_config=read_json(args.sft_config),
            prediction_config=read_json(args.prediction_config),
            output_dir=args.output,
            candidate_manifest_path=args.candidate_manifest,
            materialization_manifest_path=args.materialization_manifest,
            sft_config_path=args.sft_config,
            prediction_config_path=args.prediction_config,
            a100_ssh_status=args.a100_ssh_status,
            a100_output_root_status=args.a100_output_root_status,
            a100_idle_gpu_status=args.a100_idle_gpu_status,
            a100_selected_gpu_index=args.a100_selected_gpu_index,
            a100_train_dependencies=_comma_list(args.a100_train_dependencies),
            a100_missing_dependencies=_comma_list(args.a100_missing_dependencies),
            dry_run_metadata=read_json(args.dry_run_metadata) if args.dry_run_metadata else None,
            training_metadata=read_json(args.training_metadata) if args.training_metadata else None,
            prediction_metadata=read_json(args.prediction_metadata) if args.prediction_metadata else None,
            metrics=read_json(args.metrics) if args.metrics else None,
            dry_run_metadata_path=args.dry_run_metadata,
            training_metadata_path=args.training_metadata,
            prediction_metadata_path=args.prediction_metadata,
            metrics_path=args.metrics,
            a100_training_status=args.a100_training_status,
            a100_prediction_status=args.a100_prediction_status,
            remote_workspace_status=args.remote_workspace_status,
            dependency_env_status=args.dependency_env_status,
            sync_status=args.sync_status,
        )
        evidence = read_json(report_paths["json"])
        print(
            json.dumps(
                {
                    "ok": True,
                    "paths": {key: value.as_posix() for key, value in report_paths.items()},
                    "summary": evidence.get("summary", {}),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "merged-slot-value-heldout-eval":
        metrics_paths = {
            "train": args.train_metrics,
            "dev": args.dev_metrics,
            "test": args.test_metrics,
        }
        prediction_metadata_paths = {
            "train": args.train_prediction_metadata,
            "dev": args.dev_prediction_metadata,
            "test": args.test_prediction_metadata,
        }
        report_paths = write_merged_slot_value_heldout_eval_report(
            public_manifest=read_json(args.public_manifest),
            training_metadata=read_json(args.training_metadata) if args.training_metadata else None,
            metrics_by_split={split: read_json(path) for split, path in metrics_paths.items()},
            prediction_metadata_by_split={
                split: read_json(path) if path else None for split, path in prediction_metadata_paths.items()
            },
            output_dir=args.output,
            metrics_paths=metrics_paths,
            prediction_metadata_paths=prediction_metadata_paths,
            prior_targeted_manifest=read_json(args.prior_targeted_manifest) if args.prior_targeted_manifest else None,
        )
        evidence = read_json(report_paths["json"])
        print(
            json.dumps(
                {
                    "ok": True,
                    "paths": {key: value.as_posix() for key, value in report_paths.items()},
                    "summary": {
                        "overall_interpretation": evidence.get("overall_interpretation"),
                        "split_results": evidence.get("split_results", {}),
                    },
                },
                indent=2,
            )
        )
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
