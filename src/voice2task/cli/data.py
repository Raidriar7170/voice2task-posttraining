from __future__ import annotations

import argparse
import json
from pathlib import Path

from voice2task.dataset import (
    blocked_payment_safety_repair_public_sample_merge_evidence,
    build_local_private_corpus,
    build_public_sample_dataset,
    check_form_fill_confirmation_marker_extension_candidate_integration_preview,
    check_form_fill_remediation_candidate_integration_preview,
    current_retry_confirmation_preservation_public_sample_merge_evidence,
    family_stratified_public_sample_merge_evidence,
    form_fill_confirmation_marker_extension_public_sample_merge_evidence,
    form_fill_remediation_public_sample_merge_evidence,
    materialize_blocked_payment_safety_repair_candidates,
    materialize_current_retry_confirmation_preservation_candidates,
    materialize_family_stratified_generalization_candidates,
    materialize_form_fill_confirmation_marker_extension_candidates,
    materialize_form_fill_remediation_candidates,
    materialize_scaled_public_sample_candidates,
    materialize_slot_value_generalization_candidates,
    merge_blocked_payment_safety_repair_candidates_into_public_sample,
    merge_current_retry_confirmation_preservation_candidates_into_public_sample,
    merge_family_stratified_candidates_into_public_sample,
    merge_form_fill_confirmation_marker_extension_candidates_into_public_sample,
    merge_form_fill_remediation_candidates_into_public_sample,
    merge_scaled_public_sample_candidates_into_public_sample,
    merge_slot_value_candidates_into_public_sample,
    scaled_public_sample_public_sample_merge_evidence,
)
from voice2task.dpo import summarize_dpo_slices, validate_dpo_pairs_file
from voice2task.reports import (
    write_blocked_payment_safety_repair_public_sample_merge_report,
    write_current_retry_confirmation_preservation_public_sample_merge_report,
    write_family_stratified_public_sample_merge_report,
    write_form_fill_confirmation_marker_extension_public_sample_merge_report,
    write_form_fill_remediation_public_sample_merge_report,
    write_scaled_public_sample_public_sample_merge_report,
)
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

    form_fill_parser = subcommands.add_parser("materialize-form-fill-remediation-candidates")
    form_fill_parser.add_argument("--case-design", type=Path, required=True)
    form_fill_parser.add_argument("--seed-output", type=Path, required=True)
    form_fill_parser.add_argument("--output", type=Path, required=True)

    confirmation_marker_extension_parser = subcommands.add_parser(
        "materialize-form-fill-confirmation-marker-extension-candidates"
    )
    confirmation_marker_extension_parser.add_argument("--extension-design", type=Path, required=True)
    confirmation_marker_extension_parser.add_argument("--seed-output", type=Path, required=True)
    confirmation_marker_extension_parser.add_argument("--output", type=Path, required=True)

    blocked_payment_repair_parser = subcommands.add_parser(
        "materialize-blocked-payment-safety-repair-candidates"
    )
    blocked_payment_repair_parser.add_argument("--candidate-design", type=Path, required=True)
    blocked_payment_repair_parser.add_argument("--seed-output", type=Path, required=True)
    blocked_payment_repair_parser.add_argument("--output", type=Path, required=True)

    current_retry_confirmation_parser = subcommands.add_parser(
        "materialize-current-retry-confirmation-preservation-candidates"
    )
    current_retry_confirmation_parser.add_argument("--candidate-design", type=Path, required=True)
    current_retry_confirmation_parser.add_argument("--seed-output", type=Path, required=True)
    current_retry_confirmation_parser.add_argument("--output", type=Path, required=True)

    check_form_fill_parser = subcommands.add_parser(
        "check-form-fill-remediation-candidate-integration",
        help="Build a report-scoped preview dataset for standalone form-fill remediation candidates.",
    )
    check_form_fill_parser.add_argument("--candidate-seed", type=Path, required=True)
    check_form_fill_parser.add_argument("--seed", type=Path, required=True)
    check_form_fill_parser.add_argument("--output", type=Path, required=True)

    check_confirmation_marker_extension_parser = subcommands.add_parser(
        "check-form-fill-confirmation-marker-extension-candidate-integration",
        help="Build a report-scoped preview dataset for standalone form-fill confirmation-marker extension candidates.",
    )
    check_confirmation_marker_extension_parser.add_argument("--candidate-seed", type=Path, required=True)
    check_confirmation_marker_extension_parser.add_argument("--seed", type=Path, required=True)
    check_confirmation_marker_extension_parser.add_argument("--output", type=Path, required=True)

    family_parser = subcommands.add_parser("materialize-family-stratified-candidates")
    family_parser.add_argument("--seed-output", type=Path, required=True)
    family_parser.add_argument("--output", type=Path, required=True)

    scaled_public_sample_parser = subcommands.add_parser("materialize-scaled-public-sample-candidates")
    scaled_public_sample_parser.add_argument("--seed-output", type=Path, required=True)
    scaled_public_sample_parser.add_argument("--output", type=Path, required=True)

    merge_slot_value_parser = subcommands.add_parser("merge-slot-value-candidates")
    merge_slot_value_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_slot_value_parser.add_argument("--seed", type=Path, required=True)
    merge_slot_value_parser.add_argument("--output", type=Path, required=True)

    merge_family_parser = subcommands.add_parser("merge-family-stratified-candidates")
    merge_family_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_family_parser.add_argument("--seed", type=Path, required=True)
    merge_family_parser.add_argument("--output", type=Path, required=True)
    merge_family_parser.add_argument("--evidence-output", type=Path, required=True)

    merge_form_fill_parser = subcommands.add_parser("merge-form-fill-remediation-candidates")
    merge_form_fill_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_form_fill_parser.add_argument("--seed", type=Path, required=True)
    merge_form_fill_parser.add_argument("--output", type=Path, required=True)
    merge_form_fill_parser.add_argument("--evidence-output", type=Path, required=True)

    merge_confirmation_marker_extension_parser = subcommands.add_parser(
        "merge-form-fill-confirmation-marker-extension-candidates"
    )
    merge_confirmation_marker_extension_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_confirmation_marker_extension_parser.add_argument("--seed", type=Path, required=True)
    merge_confirmation_marker_extension_parser.add_argument("--output", type=Path, required=True)
    merge_confirmation_marker_extension_parser.add_argument("--evidence-output", type=Path, required=True)

    merge_blocked_payment_repair_parser = subcommands.add_parser(
        "merge-blocked-payment-safety-repair-candidates"
    )
    merge_blocked_payment_repair_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_blocked_payment_repair_parser.add_argument("--seed", type=Path, required=True)
    merge_blocked_payment_repair_parser.add_argument("--output", type=Path, required=True)
    merge_blocked_payment_repair_parser.add_argument("--evidence-output", type=Path, required=True)

    merge_current_retry_confirmation_parser = subcommands.add_parser(
        "merge-current-retry-confirmation-preservation-candidates"
    )
    merge_current_retry_confirmation_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_current_retry_confirmation_parser.add_argument("--seed", type=Path, required=True)
    merge_current_retry_confirmation_parser.add_argument("--output", type=Path, required=True)
    merge_current_retry_confirmation_parser.add_argument("--evidence-output", type=Path, required=True)

    merge_scaled_public_sample_parser = subcommands.add_parser("merge-scaled-public-sample-candidates")
    merge_scaled_public_sample_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_scaled_public_sample_parser.add_argument("--seed", type=Path, required=True)
    merge_scaled_public_sample_parser.add_argument("--output", type=Path, required=True)
    merge_scaled_public_sample_parser.add_argument("--evidence-output", type=Path, required=True)
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
    if args.command == "materialize-form-fill-remediation-candidates":
        paths = materialize_form_fill_remediation_candidates(
            case_design_path=args.case_design,
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
    if args.command == "materialize-form-fill-confirmation-marker-extension-candidates":
        paths = materialize_form_fill_confirmation_marker_extension_candidates(
            extension_design_path=args.extension_design,
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
    if args.command == "materialize-blocked-payment-safety-repair-candidates":
        paths = materialize_blocked_payment_safety_repair_candidates(
            candidate_design_path=args.candidate_design,
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
    if args.command == "materialize-current-retry-confirmation-preservation-candidates":
        paths = materialize_current_retry_confirmation_preservation_candidates(
            candidate_design_path=args.candidate_design,
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
    if args.command == "check-form-fill-remediation-candidate-integration":
        paths = check_form_fill_remediation_candidate_integration_preview(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        ok = bool(manifest["validation"]["ok"])
        payload = {
            "ok": ok,
            "paths": {name: path.as_posix() for name, path in paths.items()},
            "preview_counts": manifest["preview_counts"],
            "preview_split_counts": manifest["preview_split_counts"],
            "candidate_source": manifest["candidate_source"],
            "formal_public_sample_counts_before": manifest["formal_public_sample_counts_before"],
            "validation": manifest["validation"],
            "execution_scope": manifest["execution_scope"],
            "claims": manifest["claims"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if ok else 1
    if args.command == "check-form-fill-confirmation-marker-extension-candidate-integration":
        paths = check_form_fill_confirmation_marker_extension_candidate_integration_preview(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        ok = bool(manifest["validation"]["ok"])
        payload = {
            "ok": ok,
            "paths": {name: path.as_posix() for name, path in paths.items()},
            "preview_counts": manifest["preview_counts"],
            "preview_split_counts": manifest["preview_split_counts"],
            "candidate_source": manifest["candidate_source"],
            "formal_public_sample_counts_before": manifest["formal_public_sample_counts_before"],
            "validation": manifest["validation"],
            "execution_scope": manifest["execution_scope"],
            "claims": manifest["claims"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if ok else 1
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
    if args.command == "materialize-scaled-public-sample-candidates":
        paths = materialize_scaled_public_sample_candidates(
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
    if args.command == "merge-form-fill-remediation-candidates":
        manifest = merge_form_fill_remediation_candidates_into_public_sample(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        evidence = form_fill_remediation_public_sample_merge_evidence(
            manifest=manifest,
            candidate_seed_path=args.candidate_seed,
        )
        evidence_paths = write_form_fill_remediation_public_sample_merge_report(
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
    if args.command == "merge-form-fill-confirmation-marker-extension-candidates":
        manifest = merge_form_fill_confirmation_marker_extension_candidates_into_public_sample(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        evidence = form_fill_confirmation_marker_extension_public_sample_merge_evidence(
            manifest=manifest,
            candidate_seed_path=args.candidate_seed,
        )
        evidence_paths = write_form_fill_confirmation_marker_extension_public_sample_merge_report(
            evidence,
            output_dir=args.evidence_output,
        )
        ok = bool((evidence.get("validation") or {}).get("ok", False))
        payload = {
            "ok": ok,
            "counts": manifest.counts,
            "split_counts": manifest.split_counts,
            "source_summary": manifest.source_summary,
            "paths": manifest.files,
            "evidence_paths": {name: path.as_posix() for name, path in evidence_paths.items()},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if ok else 1
    if args.command == "merge-blocked-payment-safety-repair-candidates":
        pre_merge_manifest = json.loads((args.output / "manifest_public_sample.json").read_text(encoding="utf-8"))
        manifest = merge_blocked_payment_safety_repair_candidates_into_public_sample(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        evidence = blocked_payment_safety_repair_public_sample_merge_evidence(
            manifest=manifest,
            candidate_seed_path=args.candidate_seed,
            pre_merge_manifest=pre_merge_manifest,
        )
        evidence_paths = write_blocked_payment_safety_repair_public_sample_merge_report(
            evidence,
            output_dir=args.evidence_output,
        )
        ok = bool((evidence.get("validation") or {}).get("ok", False))
        payload = {
            "ok": ok,
            "counts": manifest.counts,
            "split_counts": manifest.split_counts,
            "source_summary": manifest.source_summary,
            "paths": manifest.files,
            "evidence_paths": {name: path.as_posix() for name, path in evidence_paths.items()},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if ok else 1
    if args.command == "merge-current-retry-confirmation-preservation-candidates":
        pre_merge_manifest = json.loads((args.output / "manifest_public_sample.json").read_text(encoding="utf-8"))
        manifest = merge_current_retry_confirmation_preservation_candidates_into_public_sample(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        evidence = current_retry_confirmation_preservation_public_sample_merge_evidence(
            manifest=manifest,
            candidate_seed_path=args.candidate_seed,
            pre_merge_manifest=pre_merge_manifest,
        )
        evidence_paths = write_current_retry_confirmation_preservation_public_sample_merge_report(
            evidence,
            output_dir=args.evidence_output,
        )
        ok = bool((evidence.get("validation") or {}).get("ok", False))
        payload = {
            "ok": ok,
            "counts": manifest.counts,
            "split_counts": manifest.split_counts,
            "source_summary": manifest.source_summary,
            "paths": manifest.files,
            "evidence_paths": {name: path.as_posix() for name, path in evidence_paths.items()},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if ok else 1
    if args.command == "merge-scaled-public-sample-candidates":
        pre_merge_manifest = json.loads((args.output / "manifest_public_sample.json").read_text(encoding="utf-8"))
        manifest = merge_scaled_public_sample_candidates_into_public_sample(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        evidence = scaled_public_sample_public_sample_merge_evidence(
            manifest=manifest,
            candidate_seed_path=args.candidate_seed,
            pre_merge_manifest=pre_merge_manifest,
        )
        evidence_paths = write_scaled_public_sample_public_sample_merge_report(
            evidence,
            output_dir=args.evidence_output,
        )
        ok = bool((evidence.get("validation") or {}).get("ok", False))
        payload = {
            "ok": ok,
            "counts": manifest.counts,
            "split_counts": manifest.split_counts,
            "source_summary": manifest.source_summary,
            "paths": manifest.files,
            "evidence_paths": {name: path.as_posix() for name, path in evidence_paths.items()},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if ok else 1
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
