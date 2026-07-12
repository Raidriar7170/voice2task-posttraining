from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

import voice2task.clean_evaluation_review_pack as clean_review
from voice2task.clean_evaluation_boundary import (
    CANONICAL_PRIVATE_ROOT,
    PUBLIC_REPORT_ROOT,
    BoundaryViolation,
    blocked_summary_for,
    materialize_boundary,
    validate_named_inputs,
    verify_generation,
    write_public_evidence,
)
from voice2task.dataset import (
    blocked_payment_safety_repair_public_sample_merge_evidence,
    build_local_private_corpus,
    build_public_sample_dataset,
    canonical_slot_boundary_public_sample_merge_evidence,
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
    materialize_scaled_clarify_slot_boundary_candidates,
    materialize_scaled_public_sample_candidates,
    materialize_slot_value_generalization_candidates,
    merge_blocked_payment_safety_repair_candidates_into_public_sample,
    merge_canonical_slot_boundary_candidates_into_public_sample,
    merge_current_retry_confirmation_preservation_candidates_into_public_sample,
    merge_family_stratified_candidates_into_public_sample,
    merge_form_fill_confirmation_marker_extension_candidates_into_public_sample,
    merge_form_fill_remediation_candidates_into_public_sample,
    merge_scaled_public_sample_candidates_into_public_sample,
    merge_slot_value_candidates_into_public_sample,
    scaled_public_sample_public_sample_merge_evidence,
)
from voice2task.dpo import summarize_dpo_slices, validate_dpo_pairs_file
from voice2task.lockbox import validate_lockbox
from voice2task.reports import (
    write_blocked_payment_safety_repair_public_sample_merge_report,
    write_canonical_slot_boundary_public_sample_merge_report,
    write_current_retry_confirmation_preservation_public_sample_merge_report,
    write_family_stratified_public_sample_merge_report,
    write_form_fill_confirmation_marker_extension_public_sample_merge_report,
    write_form_fill_remediation_public_sample_merge_report,
    write_scaled_public_sample_public_sample_merge_report,
)
from voice2task.split_integrity import audit_split_integrity, write_split_integrity_report
from voice2task.validation import validate_dataset_artifacts

REPO_ROOT = Path(__file__).resolve().parents[3]


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

    validate_lockbox_parser = subcommands.add_parser("validate-lockbox")
    validate_lockbox_parser.add_argument("--lockbox", type=Path, required=True)
    validate_lockbox_parser.add_argument("--manifest", type=Path, required=True)
    validate_lockbox_parser.add_argument("--train", type=Path, action="append", default=[])
    validate_lockbox_parser.add_argument("--analysis", type=Path, action="append", default=[])
    validate_lockbox_parser.add_argument("--require-family-disjointness", action="store_true")

    dpo_parser = subcommands.add_parser("dpo-check")
    dpo_parser.add_argument("--dpo", type=Path, required=True)

    audit_splits_parser = subcommands.add_parser("audit-splits")
    audit_splits_parser.add_argument("--seed", type=Path, required=True)
    audit_splits_parser.add_argument("--sft", type=Path, required=True)
    audit_splits_parser.add_argument("--dpo", type=Path, required=True)
    audit_splits_parser.add_argument("--manifest", type=Path, required=True)
    audit_splits_parser.add_argument("--output", type=Path, required=True)
    audit_splits_parser.add_argument("--require-clean", action="store_true")

    clean_boundary_validate_parser = subcommands.add_parser("clean-boundary-validate")
    clean_boundary_validate_parser.add_argument("--bindings", required=True)
    clean_boundary_validate_parser.add_argument("--source-contract", required=True)
    clean_boundary_validate_parser.add_argument("--compiler-card", required=True)
    clean_boundary_validate_parser.add_argument("--model-card", required=True)

    clean_boundary_materialize_parser = subcommands.add_parser("clean-boundary-materialize")
    clean_boundary_materialize_parser.add_argument("--protocol-sha256", required=True)
    clean_boundary_materialize_parser.add_argument("--source-frame", required=True)
    clean_boundary_materialize_parser.add_argument("--lockbox-attestation", required=True)
    clean_boundary_materialize_parser.add_argument("--generation-id", required=True)

    clean_boundary_verify_parser = subcommands.add_parser("clean-boundary-verify")
    clean_boundary_verify_parser.add_argument("--generation-id", required=True)
    clean_boundary_verify_parser.add_argument("--population-seal-sha256", required=True)

    subcommands.add_parser("clean-boundary-review-pack")
    clean_boundary_review_lint_parser = subcommands.add_parser(
        "clean-boundary-review-lint"
    )
    clean_boundary_review_lint_parser.add_argument("--review-pack", required=True)

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

    scaled_clarify_parser = subcommands.add_parser(
        "materialize-scaled-clarify-slot-boundary-candidates"
    )
    scaled_clarify_parser.add_argument("--candidate-design", type=Path, required=True)
    scaled_clarify_parser.add_argument("--seed-output", type=Path, required=True)
    scaled_clarify_parser.add_argument("--output", type=Path, required=True)

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

    merge_canonical_slot_boundary_parser = subcommands.add_parser(
        "merge-canonical-slot-boundary-row-level-candidates"
    )
    merge_canonical_slot_boundary_parser.add_argument("--candidate-seed", type=Path, required=True)
    merge_canonical_slot_boundary_parser.add_argument("--seed", type=Path, required=True)
    merge_canonical_slot_boundary_parser.add_argument("--output", type=Path, required=True)
    merge_canonical_slot_boundary_parser.add_argument("--evidence-output", type=Path, required=True)
    return parser


def _is_validate_lockbox_argv(argv: list[str] | None) -> bool:
    args = list(sys.argv[1:] if argv is None else argv)
    return bool(args and args[0] == "validate-lockbox")


def _is_clean_boundary_review_argv(argv: list[str] | None) -> bool:
    args = list(sys.argv[1:] if argv is None else argv)
    return bool(
        args
        and args[0]
        in {"clean-boundary-review-pack", "clean-boundary-review-lint"}
    )


def _review_lint_exit_zero(payload: dict[str, object]) -> bool:
    return payload == clean_review.review_lint_success_truth()


def _parser_error_payload(message: str, manifest_path: str | None = None) -> dict[str, object]:
    return {
        "ok": False,
        "failures": [
            {
                "category": "ArgumentParserError",
                "row_id": "input",
                "message": message.strip(),
            }
        ],
        "counts": {},
        "manifest": {"path": manifest_path},
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    is_validate_lockbox = _is_validate_lockbox_argv(argv)
    is_clean_boundary_review = _is_clean_boundary_review_argv(argv)
    if is_validate_lockbox or is_clean_boundary_review:
        argparse_stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(argparse_stderr):
                args = parser.parse_args(argv)
        except SystemExit as exc:
            if exc.code == 0 and is_clean_boundary_review:
                return 0
            payload = (
                clean_review.review_command_failure_truth()
                if is_clean_boundary_review
                else _parser_error_payload(argparse_stderr.getvalue())
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            return exc.code if isinstance(exc.code, int) else 2
    else:
        args = parser.parse_args(argv)
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
    if args.command == "validate-lockbox":
        try:
            lockbox_result = validate_lockbox(
                lockbox_path=args.lockbox,
                manifest_path=args.manifest,
                train_paths=args.train,
                analysis_paths=args.analysis,
                require_family_disjointness=args.require_family_disjointness,
            )
            payload = lockbox_result.to_dict()
        except Exception as exc:  # noqa: BLE001 - CLI validation failures must stay machine-readable.
            payload = {
                "ok": False,
                "failures": [
                    {
                        "category": type(exc).__name__,
                        "row_id": "input",
                        "message": str(exc),
                    }
                ],
                "counts": {},
                "manifest": {"path": args.manifest.as_posix()},
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if args.command == "dpo-check":
        pairs = validate_dpo_pairs_file(args.dpo)
        print(json.dumps(summarize_dpo_slices(pairs), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "audit-splits":
        audit = audit_split_integrity(
            seed_path=args.seed,
            sft_path=args.sft,
            dpo_path=args.dpo,
            manifest_path=args.manifest,
            repo_root=REPO_ROOT,
        )
        paths = write_split_integrity_report(audit, args.output)
        payload = {
            "ok": audit["input_validation"]["valid"]
            and (audit["clean_gate"]["passed"] or not args.require_clean),
            "require_clean": args.require_clean,
            "input_validation": audit["input_validation"],
            "clean_gate": audit["clean_gate"],
            "outputs": {name: path.as_posix() for name, path in paths.items()},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if args.command == "clean-boundary-review-pack":
        try:
            clean_review.write_review_pack_bundle(REPO_ROOT)
            payload = clean_review.build_review_pack_summary()
            return_code = 0
        except Exception:
            payload = clean_review.review_command_failure_truth()
            return_code = 1
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return return_code
    if args.command == "clean-boundary-review-lint":
        review_input_root = REPO_ROOT / CANONICAL_PRIVATE_ROOT / "review-inputs"
        try:
            payload = clean_review.lint_review_envelope_file(
                review_input_root,
                args.review_pack,
            )
        except Exception:
            payload = clean_review.review_command_failure_truth()
        exit_zero = _review_lint_exit_zero(payload)
        if not exit_zero and payload.get("lint_conforms") is True:
            payload = clean_review.review_command_failure_truth()
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if exit_zero else 1
    if args.command == "clean-boundary-validate":
        private_root = REPO_ROOT / CANONICAL_PRIVATE_ROOT
        try:
            protocol = validate_named_inputs(
                private_root,
                bindings=args.bindings,
                source_contract=args.source_contract,
                compiler_card=args.compiler_card,
                model_card=args.model_card,
            )
            payload = {
                "ok": True,
                "current_readiness_state": "PROTOCOL_FROZEN",
                "protocol_sha256": protocol["protocol_sha256"],
                "execution_readiness": False,
            }
        except BoundaryViolation as exc:
            summary = blocked_summary_for(exc)
            payload = {
                "ok": False,
                "evidence_status": summary["evidence_status"],
                "decision": summary["decision"],
                "current_readiness_state": summary["current_readiness_state"],
                "blockers": summary["blockers"],
                "execution_readiness": False,
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if args.command == "clean-boundary-materialize":
        private_root = REPO_ROOT / CANONICAL_PRIVATE_ROOT
        try:
            summary = materialize_boundary(
                private_root,
                protocol_sha256=args.protocol_sha256,
                source_frame=args.source_frame,
                lockbox_attestation=args.lockbox_attestation,
                generation_id=args.generation_id,
            )
            write_public_evidence(summary, REPO_ROOT, PUBLIC_REPORT_ROOT)
            payload = {"ok": True, **summary}
        except BoundaryViolation as exc:
            summary = blocked_summary_for(exc, last_state=exc.last_verified_state)
            write_public_evidence(summary, REPO_ROOT, PUBLIC_REPORT_ROOT)
            payload = {"ok": False, **summary}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if args.command == "clean-boundary-verify":
        private_root = REPO_ROOT / CANONICAL_PRIVATE_ROOT
        try:
            payload = verify_generation(
                private_root,
                args.generation_id,
                expected_population_seal_sha256=args.population_seal_sha256,
            )
        except BoundaryViolation as exc:
            payload = {
                "ok": False,
                "boundary_integrity_status": (
                    "NOT_CREATED" if exc.code == "GENERATION_NOT_FOUND" else "COMPROMISED"
                ),
                "blockers": [exc.code],
                "execution_readiness": False,
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
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
    if args.command == "materialize-scaled-clarify-slot-boundary-candidates":
        paths = materialize_scaled_clarify_slot_boundary_candidates(
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
    if args.command == "merge-canonical-slot-boundary-row-level-candidates":
        pre_merge_manifest = json.loads((args.output / "manifest_public_sample.json").read_text(encoding="utf-8"))
        manifest = merge_canonical_slot_boundary_candidates_into_public_sample(
            candidate_seed_path=args.candidate_seed,
            seed_path=args.seed,
            output_dir=args.output,
        )
        evidence = canonical_slot_boundary_public_sample_merge_evidence(
            manifest=manifest,
            candidate_seed_path=args.candidate_seed,
            pre_merge_manifest=pre_merge_manifest,
        )
        evidence_paths = write_canonical_slot_boundary_public_sample_merge_report(
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
