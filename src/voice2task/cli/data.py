from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.dataset import (
    build_local_private_corpus,
    build_public_sample_dataset,
    family_stratified_public_sample_merge_evidence,
    materialize_family_stratified_generalization_candidates,
    materialize_slot_value_generalization_candidates,
    merge_family_stratified_candidates_into_public_sample,
    merge_slot_value_candidates_into_public_sample,
)
from voice2task.dpo import summarize_dpo_slices, validate_dpo_pairs_file
from voice2task.reports import write_family_stratified_public_sample_merge_report
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

    slot_value_parser = subcommands.add_parser("materialize-slot-value-candidates")
    slot_value_parser.add_argument("--case-design", type=Path, required=True)
    slot_value_parser.add_argument("--seed-output", type=Path, required=True)
    slot_value_parser.add_argument("--output", type=Path, required=True)

    family_parser = subcommands.add_parser("materialize-family-stratified-candidates")
    family_parser.add_argument("--seed-output", type=Path, required=True)
    family_parser.add_argument("--output", type=Path, required=True)

    merge_slot_value_parser = subcommands.add_parser("merge-slot-value-candidates")
    merge_slot_value_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_slot_value_parser.add_argument("--seed", type=Path, required=True)
    merge_slot_value_parser.add_argument("--output", type=Path, required=True)

    merge_family_parser = subcommands.add_parser("merge-family-stratified-candidates")
    merge_family_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_family_parser.add_argument("--seed", type=Path, required=True)
    merge_family_parser.add_argument("--output", type=Path, required=True)
    merge_family_parser.add_argument("--evidence-output", type=Path, required=True)
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
    if args.command == "materialize-slot-value-candidates":
        paths = materialize_slot_value_generalization_candidates(
            case_design_path=args.case_design,
            seed_output_path=args.seed_output,
            output_dir=args.output,
        )
        materialization_manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        payload = {
            "ok": True,
            "paths": {name: path.as_posix() for name, path in paths.items()},
            "summary": materialization_manifest["summary"],
            "execution_scope": materialization_manifest["execution_scope"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "materialize-family-stratified-candidates":
        paths = materialize_family_stratified_generalization_candidates(
            seed_output_path=args.seed_output,
            output_dir=args.output,
        )
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        payload = {
            "ok": True,
            "paths": {name: path.as_posix() for name, path in paths.items()},
            "summary": manifest["summary"],
            "execution_scope": manifest["execution_scope"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "merge-slot-value-candidates":
        manifest = merge_slot_value_candidates_into_public_sample(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        payload = {
            "ok": True,
            "counts": manifest.counts,
            "split_counts": manifest.split_counts,
            "source_summary": manifest.source_summary,
            "paths": manifest.files,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "merge-family-stratified-candidates":
        manifest = merge_family_stratified_candidates_into_public_sample(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        evidence = family_stratified_public_sample_merge_evidence(
            manifest=manifest,
            candidate_seed_path=args.candidate_seed,
        )
        evidence_paths = write_family_stratified_public_sample_merge_report(
            evidence,
            output_dir=args.evidence_output,
        )
        payload = {
            "ok": True,
            "counts": manifest.counts,
            "split_counts": manifest.split_counts,
            "source_summary": manifest.source_summary,
            "paths": manifest.files,
            "evidence_paths": {name: path.as_posix() for name, path in evidence_paths.items()},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
