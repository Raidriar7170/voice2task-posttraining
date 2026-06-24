from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from voice2task.copy_backed_shadow_interface import (
    generate_online_shadow_sidecar,
    load_scope_policy,
    stable_hash,
    validate_scope_policy,
)
from voice2task.copy_backed_slot_verification import (
    AMBIGUOUS_NORMALIZATION_COLLISION,
    NORMALIZATION_COLLISION_RULE,
    VERIFIED_EXACT_UNIQUE,
    audit_normalized_equivalent_collision,
    normalize_copy_text,
)
from voice2task.io import read_json, read_jsonl, write_json, write_jsonl
from voice2task.schemas import canonical_contract_json
from voice2task.slot_error_analysis import flatten_slot_values

CHANGE_ID = "diagnose-copy-shadow-false-trust-before-naturalistic-v2"
EVIDENCE_KIND = "copy_shadow_false_trust_diagnosis"
SOURCE_EVALUATION_DIR = Path("reports/public-sample/copy-shadow-template-disjoint-challenge-v1/adapter-evaluation")
POLICY_PATH = Path("configs/copy-backed-scope-policy-v1.json")
EXPECTED_CHALLENGE_HASH = "12eccdd54b2c89f1127ec23f18d7179e1ebaacb1a644ae5ca1a14b3309f11324"
EXPECTED_POLICY_HASH = "5dc14efb8ded13dc048ddb067c7c63a1a62b6c03896950e861303973d505cbc7"
EXPECTED_SCOPES = (
    "search:search_web:query",
    "form_fill:fill_form:field",
    "extract:extract_page:target",
)

DECISION_POLICY_V2_REVIEW_READY = "SOURCE_ATTESTATION_SEMANTICS_HARDENED_POLICY_V2_REVIEW_READY"
DECISION_SCOPE_REDUCTION_REQUIRED = "SOURCE_ATTESTATION_HARDENED_SCOPE_REDUCTION_REQUIRED"
DECISION_NO_FURTHER_INTEGRATION = "COPY_SHADOW_OBSERVE_ONLY_NO_FURTHER_INTEGRATION"
DECISION_BLOCKED_INVALID_INPUT = "FALSE_TRUST_DIAGNOSIS_BLOCKED_INVALID_INPUT"
DECISION_INCONSISTENT_ARTIFACTS = "FALSE_TRUST_DIAGNOSIS_INCONSISTENT_ARTIFACTS"

NORMALIZATION_RULE = NORMALIZATION_COLLISION_RULE
POLICY_V2_STATUS_DEFERRED = "DEFER_TO_DESIGN_COPY_SHADOW_SCOPE_POLICY_V2"


def run_copy_shadow_false_trust_diagnosis(
    repo_root: Path,
    *,
    expected_challenge_hash: str = EXPECTED_CHALLENGE_HASH,
    expected_policy_hash: str = EXPECTED_POLICY_HASH,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    inputs = _load_inputs(repo_root)
    boundary = _validate_input_boundary(
        repo_root,
        inputs,
        expected_challenge_hash=expected_challenge_hash,
        expected_policy_hash=expected_policy_hash,
    )
    if not boundary["ok"]:
        decision = _blocked_decision(boundary.get("blocking_reasons", []))
        return {
            "summary": _blocked_summary(decision, boundary),
            "input_boundary": boundary,
            "case_ledger": [],
            "normalization_collision_audit": _empty_collision_audit(),
            "per_scope_risk_review": _empty_scope_review(),
        }

    source_attested_events = _build_source_attested_events(inputs)
    case_ledger = _build_case_ledger(inputs, source_attested_events)
    per_scope = _build_per_scope_review(inputs["audits"], case_ledger)
    collision_audit = _build_collision_audit(source_attested_events)
    summary = _build_summary(inputs, boundary, case_ledger, per_scope, collision_audit)
    return {
        "summary": summary,
        "input_boundary": boundary,
        "case_ledger": case_ledger,
        "normalization_collision_audit": collision_audit,
        "per_scope_risk_review": per_scope,
    }


def write_copy_shadow_false_trust_diagnosis_report(
    repo_root: Path,
    output_dir: Path,
    *,
    expected_challenge_hash: str = EXPECTED_CHALLENGE_HASH,
    expected_policy_hash: str = EXPECTED_POLICY_HASH,
) -> dict[str, Any]:
    diagnosis = run_copy_shadow_false_trust_diagnosis(
        repo_root,
        expected_challenge_hash=expected_challenge_hash,
        expected_policy_hash=expected_policy_hash,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    if diagnosis["summary"]["decision_label"] in {DECISION_BLOCKED_INVALID_INPUT, DECISION_INCONSISTENT_ARTIFACTS}:
        write_json(output_dir / "blocked.json", _blocked_artifact(diagnosis))
        return diagnosis

    write_json(output_dir / "summary.json", diagnosis["summary"])
    write_jsonl(output_dir / "false-trust-case-ledger.jsonl", diagnosis["case_ledger"])
    write_json(output_dir / "per-scope-risk-review.json", diagnosis["per_scope_risk_review"])
    write_json(output_dir / "normalization-collision-audit.json", diagnosis["normalization_collision_audit"])
    (output_dir / "summary.md").write_text(_summary_markdown(diagnosis), encoding="utf-8")
    (output_dir / "sidecar-v2-semantics.md").write_text(_sidecar_v2_semantics_markdown(diagnosis), encoding="utf-8")
    (output_dir / "recommended-next-change.md").write_text(
        _recommended_next_change_markdown(diagnosis),
        encoding="utf-8",
    )
    return diagnosis


def classify_mismatch_mechanism(
    *,
    condition_tags: list[str],
    predicted_value: Any,
    gold_value: Any,
    source_text: str,
    slot_path: str,
    normalized_collision: bool,
    span_attested: bool,
) -> dict[str, Any]:
    tag_set = {str(tag) for tag in condition_tags}
    secondary: list[str] = []
    fixture_guided_attribution: dict[str, Any] | None = None
    normalized_value_equivalent = isinstance(predicted_value, str) and isinstance(gold_value, str) and (
        normalize_copy_text(predicted_value) == normalize_copy_text(gold_value)
    )

    if not span_attested or "span_attestation_failure" in tag_set:
        primary = "TECHNICAL_SPAN_ATTESTATION_FAILURE"
    elif "wrong_scope" in tag_set or slot_path == "action":
        primary = "WRONG_SLOT_OR_SCOPE_SELECTION"
    elif "source_absent" in tag_set:
        primary = "SOURCE_ABSENT_SUBSTITUTION"
    elif normalized_collision or "normalization_collision" in tag_set:
        primary = "NORMALIZATION_EQUIVALENCE_COLLISION"
    elif "duplicate_exact" in tag_set:
        primary = "DUPLICATE_CONTEXT_DISAMBIGUATION_FAILURE"
    elif "multiple_entity_distractor" in tag_set:
        primary = "WRONG_ENTITY_FROM_SOURCE"
    elif "gold_ambiguous" in tag_set or normalized_value_equivalent:
        fixture_guided_attribution = _fixture_guided_attribution(
            condition_tags=tag_set,
            predicted_value=predicted_value,
            gold_value=gold_value,
            source_text=source_text,
            primary_mechanism=None,
            normalized_collision=normalized_collision,
            span_attested=span_attested,
        )
        primary = str(fixture_guided_attribution["primary_mechanism"])
    elif not isinstance(predicted_value, str) or not isinstance(gold_value, str):
        primary = "UNCLASSIFIED_SEMANTIC_MISMATCH"
    elif "partial_span_trap" in tag_set and predicted_value.startswith(gold_value):
        primary = "OVERLONG_SOURCE_SPAN"
    elif "partial_span_trap" in tag_set or gold_value.startswith(predicted_value):
        primary = "UNDERSPECIFIED_PARTIAL_SPAN"
    elif predicted_value in source_text:
        primary = "GENERATED_VALUE_MISMATCH"
    else:
        primary = "UNCLASSIFIED_SEMANTIC_MISMATCH"

    if isinstance(predicted_value, str) and isinstance(gold_value, str):
        if (
            predicted_value.startswith(gold_value)
            and predicted_value != gold_value
            and primary != "OVERLONG_SOURCE_SPAN"
        ):
            secondary.append("OVERLONG_SOURCE_SPAN")
        if predicted_value in gold_value and predicted_value != gold_value and primary != "UNDERSPECIFIED_PARTIAL_SPAN":
            secondary.append("UNDERSPECIFIED_PARTIAL_SPAN")

    result = {
        "primary_mechanism": primary,
        "secondary_mechanisms": sorted(set(secondary)),
    }
    if fixture_guided_attribution is None:
        fixture_guided_attribution = _fixture_guided_attribution(
            condition_tags=tag_set,
            predicted_value=predicted_value,
            gold_value=gold_value,
            source_text=source_text,
            primary_mechanism=primary,
            normalized_collision=normalized_collision,
            span_attested=span_attested,
        )
    result.update({key: value for key, value in fixture_guided_attribution.items() if key != "primary_mechanism"})
    return result


def _fixture_guided_attribution(
    *,
    condition_tags: set[str],
    predicted_value: Any,
    gold_value: Any,
    source_text: str,
    primary_mechanism: str | None,
    normalized_collision: bool,
    span_attested: bool,
) -> dict[str, Any]:
    deterministic_checks: list[str] = []
    normalized_value_equivalent = isinstance(predicted_value, str) and isinstance(gold_value, str) and (
        normalize_copy_text(predicted_value) == normalize_copy_text(gold_value)
    )
    if normalized_value_equivalent:
        deterministic_checks.append("normalized_value_equivalence")
    if normalized_collision:
        deterministic_checks.append("normalized_collision_audit")
    if not span_attested:
        deterministic_checks.append("span_attestation_failure")
    if isinstance(predicted_value, str) and isinstance(gold_value, str):
        has_prefix_relation = predicted_value.startswith(gold_value) or gold_value.startswith(predicted_value)
        if predicted_value != gold_value and has_prefix_relation:
            deterministic_checks.append("span_prefix_relation")
        if predicted_value and predicted_value in source_text:
            deterministic_checks.append("predicted_value_source_membership")

    if primary_mechanism is None and normalized_value_equivalent:
        source = "fixture_tag_plus_deterministic_relation" if condition_tags else "deterministic_relation"
        primary = "CANONICAL_STRING_MISMATCH"
        manual_review_required = False
    elif primary_mechanism is None:
        source = "reviewed_fixture_ambiguity"
        primary = "TRUE_GOLD_OR_FIXTURE_AMBIGUITY"
        manual_review_required = True
    else:
        primary = primary_mechanism
        if primary == "TRUE_GOLD_OR_FIXTURE_AMBIGUITY":
            source = "reviewed_fixture_ambiguity"
        elif condition_tags and deterministic_checks:
            source = "fixture_tag_plus_deterministic_relation"
        elif condition_tags:
            source = "fixture_tag"
        else:
            source = "deterministic_relation"
        manual_review_required = primary in {
            "TRUE_GOLD_OR_FIXTURE_AMBIGUITY",
            "WRONG_ENTITY_FROM_SOURCE",
            "SOURCE_ABSENT_SUBSTITUTION",
            "WRONG_SLOT_OR_SCOPE_SELECTION",
            "GENERATED_VALUE_MISMATCH",
            "UNCLASSIFIED_SEMANTIC_MISMATCH",
        }

    return {
        "primary_mechanism": primary,
        "attribution_mode": "fixture_guided",
        "attribution_source": source,
        "condition_tags_used": sorted(condition_tags),
        "deterministic_checks_used": sorted(set(deterministic_checks)),
        "manual_review_required": manual_review_required,
    }


def _load_inputs(repo_root: Path) -> dict[str, Any]:
    eval_dir = repo_root / SOURCE_EVALUATION_DIR
    roles = ("control", "treatment")
    rows = read_jsonl(eval_dir / "challenge-sft/sft_public_sample.jsonl")
    predictions = {
        role: read_jsonl(eval_dir / role / "jsonl_sink/predictions.jsonl")
        for role in roles
    }
    sidecars = {
        role: read_jsonl(eval_dir / role / "jsonl_sink/online-copy-shadow-sidecars.jsonl")
        for role in roles
    }
    return {
        "eval_dir": eval_dir,
        "rows": rows,
        "row_by_id": {str(row["id"]): row for row in rows},
        "predictions": predictions,
        "prediction_by_id": {
            role: {str(row["id"]): row for row in role_rows}
            for role, role_rows in predictions.items()
        },
        "sidecars": sidecars,
        "sidecar_by_id": {
            role: {
                str(prediction["id"]): sidecar
                for prediction, sidecar in zip(predictions[role], sidecars[role], strict=True)
            }
            for role in roles
        },
        "summary": read_json(eval_dir / "challenge-evaluation-summary.json"),
        "manifest": read_json(eval_dir / "challenge-sft/manifest.json"),
        "hook_safety": read_json(eval_dir / "hook-safety-audit.json"),
        "prediction_audit": read_json(eval_dir / "prediction-run-audit.json"),
        "per_scope_metrics": read_json(eval_dir / "per-scope-metrics.json"),
        "per_condition_metrics": read_json(eval_dir / "per-condition-metrics.json"),
        "adapter_identity": read_json(eval_dir / "adapter-identity-audit.json"),
        "audits": read_jsonl(eval_dir / "evaluation-audits.jsonl"),
        "policy": load_scope_policy(repo_root / POLICY_PATH),
    }


def _validate_input_boundary(
    repo_root: Path,
    inputs: dict[str, Any],
    *,
    expected_challenge_hash: str,
    expected_policy_hash: str,
) -> dict[str, Any]:
    rows = inputs["rows"]
    summary = inputs["summary"]
    manifest = inputs["manifest"]
    hook_safety = inputs["hook_safety"]
    policy_validation = validate_scope_policy(inputs["policy"])
    blocking: list[str] = []

    challenge_hash = manifest.get("challenge_hash")
    if challenge_hash != expected_challenge_hash:
        blocking.append("challenge_hash_mismatch")
    if summary.get("challenge_hash") != expected_challenge_hash:
        blocking.append("summary_challenge_hash_mismatch")
    if manifest.get("counts", {}).get("sft_rows") != len(rows):
        blocking.append("challenge_sft_row_count_mismatch")

    policy_hash = policy_validation.get("computed_policy_hash")
    if policy_hash != expected_policy_hash or summary.get("policy_hash") != expected_policy_hash:
        blocking.append("policy_hash_mismatch")
    if policy_validation.get("ok") is not True:
        blocking.append("policy_validation_failed")

    if inputs["adapter_identity"].get("overall_status") != "verified":
        blocking.append("adapter_identity_not_verified")
    if summary.get("adapter_identity_status") != "verified":
        blocking.append("summary_adapter_identity_not_verified")

    prediction_alignment = _prediction_alignment(inputs)
    sidecar_alignment = _sidecar_alignment(inputs)
    audit_alignment = _audit_alignment(inputs)
    deterministic_sidecar = _sidecar_deterministic_equivalence(inputs)
    prediction_hashes = _prediction_artifact_hashes(inputs)

    if not prediction_alignment["ok"]:
        blocking.extend(f"prediction_alignment:{reason}" for reason in prediction_alignment["blocking_reasons"])
    if not sidecar_alignment["ok"]:
        blocking.extend(f"sidecar_alignment:{reason}" for reason in sidecar_alignment["blocking_reasons"])
    if not audit_alignment["ok"]:
        blocking.extend(f"audit_alignment:{reason}" for reason in audit_alignment["blocking_reasons"])
    if not deterministic_sidecar["ok"]:
        blocking.extend(
            f"sidecar_deterministic_equivalence:{reason}" for reason in deterministic_sidecar["blocking_reasons"]
        )
    if not prediction_hashes["ok"]:
        blocking.extend(f"prediction_artifact_hashes:{reason}" for reason in prediction_hashes["blocking_reasons"])

    pipeline = summary.get("pipeline_integrity", {})
    if pipeline.get("prediction_output_invariance_proven") is not True:
        blocking.append("prediction_output_invariance_not_proven")
    if pipeline.get("v1_metric_delta_zero") is not True:
        blocking.append("v1_metric_delta_not_zero")
    technical_gates = summary.get("technical_gate_counts", {})
    if hook_safety.get("action_trusted_count") != 0 or technical_gates.get("action_trusted_count") != 0:
        blocking.append("action_trusted_count_nonzero")
    if hook_safety.get("normalized_trusted_count") != 0 or technical_gates.get("normalized_trusted_count") != 0:
        blocking.append("normalized_trusted_count_nonzero")
    if hook_safety.get("main_prediction_unchanged_all") is not True:
        blocking.append("main_prediction_not_unchanged")

    return {
        "audit_kind": "copy_shadow_false_trust_diagnosis_input_boundary",
        "ok": not blocking,
        "blocking_reasons": blocking,
        "artifact_consistency_checked": True,
        "challenge_hash": challenge_hash,
        "expected_challenge_hash": expected_challenge_hash,
        "row_count": len(rows),
        "policy_hash": policy_hash,
        "expected_policy_hash": expected_policy_hash,
        "adapter_identity_status": inputs["adapter_identity"].get("overall_status"),
        "prediction_output_invariance_proven": pipeline.get("prediction_output_invariance_proven") is True,
        "v1_metric_delta_zero": pipeline.get("v1_metric_delta_zero") is True,
        "action_trusted_count": hook_safety.get("action_trusted_count"),
        "normalized_trusted_count": hook_safety.get("normalized_trusted_count"),
        "prediction_alignment": prediction_alignment,
        "sidecar_alignment": sidecar_alignment,
        "audit_alignment": audit_alignment,
        "sidecar_deterministic_equivalence": deterministic_sidecar,
        "prediction_artifact_hashes": prediction_hashes,
    }


def _prediction_alignment(inputs: dict[str, Any]) -> dict[str, Any]:
    expected_ids = [str(row["id"]) for row in inputs["rows"]]
    blocking: list[str] = []
    by_role: dict[str, Any] = {}
    for role, predictions in inputs["predictions"].items():
        prediction_ids = [str(row.get("id")) for row in predictions]
        if prediction_ids != expected_ids:
            blocking.append(f"{role}_prediction_ids_mismatch")
        by_role[role] = {
            "prediction_count": len(predictions),
            "challenge_id_alignment": prediction_ids == expected_ids,
        }
    return {"ok": not blocking, "blocking_reasons": blocking, "roles": by_role}


def _sidecar_alignment(inputs: dict[str, Any]) -> dict[str, Any]:
    blocking: list[str] = []
    by_role: dict[str, Any] = {}
    for role, predictions in inputs["predictions"].items():
        sidecars = inputs["sidecars"][role]
        if len(sidecars) != len(predictions):
            blocking.append(f"{role}_sidecar_count_mismatch")
        unchanged = sum(1 for row in sidecars if row.get("main_prediction_unchanged") is True)
        unmutated = sum(1 for row in sidecars if row.get("contract_mutated") is False)
        if unchanged != len(sidecars):
            blocking.append(f"{role}_main_prediction_changed")
        if unmutated != len(sidecars):
            blocking.append(f"{role}_contract_mutated")
        by_role[role] = {
            "prediction_count": len(predictions),
            "sidecar_count": len(sidecars),
            "main_prediction_unchanged_count": unchanged,
            "contract_unmutated_count": unmutated,
        }
    return {"ok": not blocking, "blocking_reasons": blocking, "roles": by_role}


def _audit_alignment(inputs: dict[str, Any]) -> dict[str, Any]:
    blocking: list[str] = []
    row_ids = set(inputs["row_by_id"])
    roles = set(inputs["predictions"])
    trusted_gold_checks = 0
    trusted_gold_mismatches = 0
    for audit in inputs["audits"]:
        sample_id = str(audit.get("sample_id"))
        role = str(audit.get("run_role"))
        if sample_id not in row_ids:
            blocking.append(f"unknown_audit_sample:{sample_id}")
            continue
        if role not in roles:
            blocking.append(f"unknown_audit_role:{role}")
            continue
        if audit.get("trusted_provenance") is True:
            recomputed = _gold_correct_exact(inputs, role, sample_id, str(audit.get("slot_path")))
            if recomputed != audit.get("gold_correct_exact"):
                blocking.append(f"gold_correct_mismatch:{role}:{sample_id}:{audit.get('slot_path')}")
            trusted_gold_checks += 1
            if recomputed is False:
                trusted_gold_mismatches += 1
    return {
        "ok": not blocking,
        "blocking_reasons": sorted(set(blocking)),
        "evaluation_audit_count": len(inputs["audits"]),
        "trusted_gold_checks": trusted_gold_checks,
        "trusted_gold_mismatches": trusted_gold_mismatches,
    }


def _sidecar_deterministic_equivalence(inputs: dict[str, Any]) -> dict[str, Any]:
    blocking: list[str] = []
    checked = 0
    for role, predictions in inputs["predictions"].items():
        for prediction in predictions:
            sample_id = str(prediction["id"])
            row = inputs["row_by_id"][sample_id]
            expected = generate_online_shadow_sidecar(
                str(row["input_text"]),
                prediction["prediction"],
                request_id=sample_id,
                scope_policy=inputs["policy"],
                sample_id=sample_id,
                split=row.get("split"),
                run_role=role,
            )
            actual = inputs["sidecar_by_id"][role][sample_id]
            expected_slots = _diagnostic_subset_by_key(expected.get("slot_diagnostics", []))
            actual_slots = _diagnostic_subset_by_key(actual.get("slot_diagnostics", []))
            if expected_slots != actual_slots:
                blocking.append(f"{role}:{sample_id}")
                if len(blocking) >= 5:
                    break
            checked += 1
        if len(blocking) >= 5:
            break
    return {
        "ok": not blocking,
        "blocking_reasons": blocking,
        "checked_sidecars": checked,
        "method": "regenerate_slot_diagnostic_subset_from_committed_prediction_and_policy",
    }


def _prediction_artifact_hashes(inputs: dict[str, Any]) -> dict[str, Any]:
    audit_by_path = {
        str(row.get("prediction_output_path")): str(row.get("prediction_output_hash"))
        for row in inputs["prediction_audit"].get("prediction_runs", [])
        if row.get("prediction_output_path")
    }
    blocking: list[str] = []
    observed: dict[str, str] = {}
    for path, expected_hash in audit_by_path.items():
        full_path = inputs["eval_dir"] / path
        if not full_path.exists():
            blocking.append(f"missing:{path}")
            continue
        actual_hash = _sha256_file(full_path)
        observed[path] = actual_hash
        if actual_hash != expected_hash:
            blocking.append(f"hash_mismatch:{path}")
    return {"ok": not blocking, "blocking_reasons": blocking, "hashes": observed}


def _diagnostic_subset_by_key(diagnostics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    subset: dict[str, dict[str, Any]] = {}
    for diagnostic in diagnostics:
        key = f"{diagnostic.get('scope_key')}:{diagnostic.get('slot_path')}"
        span = diagnostic.get("source_span")
        subset[key] = {
            "candidate_provenance": bool(diagnostic.get("candidate_provenance")),
            "candidate_span_count": diagnostic.get("candidate_span_count"),
            "match_kind": diagnostic.get("match_kind"),
            "normalization_rule": diagnostic.get("normalization_rule"),
            "predicted_value_hash": diagnostic.get("predicted_value_hash"),
            "source_span": _span_subset(span),
            "trusted_provenance": bool(diagnostic.get("trusted_provenance")),
            "verification_status": diagnostic.get("verification_status") or diagnostic.get("status"),
        }
    return subset


def _span_subset(span: Any) -> dict[str, Any] | None:
    if not isinstance(span, dict):
        return None
    return {
        "start": span.get("start"),
        "end": span.get("end"),
        "source_text_hash": span.get("source_text_hash"),
        "span_hash": span.get("span_hash"),
    }


def _build_source_attested_events(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for audit in inputs["audits"]:
        if audit.get("trusted_provenance") is not True or audit.get("status") != VERIFIED_EXACT_UNIQUE:
            continue
        role = str(audit["run_role"])
        sample_id = str(audit["sample_id"])
        slot_path = str(audit["slot_path"])
        row = inputs["row_by_id"][sample_id]
        prediction = inputs["prediction_by_id"][role][sample_id]
        sidecar = inputs["sidecar_by_id"][role][sample_id]
        diagnostic = _find_diagnostic(sidecar, slot_path, str(audit["scope_key"]))
        predicted_value = flatten_slot_values(prediction["prediction"].get("slots", {})).get(slot_path)
        gold_value = flatten_slot_values(row["target_contract"].get("slots", {})).get(slot_path)
        source_text = str(row["input_text"])
        collision = audit_normalized_equivalent_collision(predicted_value, source_text)
        normalized_collision = collision.status == AMBIGUOUS_NORMALIZATION_COLLISION
        source_attested_input = _is_source_attested_exact_input(audit, diagnostic)
        source_attested_exact = source_attested_input and not normalized_collision
        events.append(
            {
                "audit": audit,
                "role": role,
                "sample_id": sample_id,
                "slot_path": slot_path,
                "scope_key": str(audit.get("scope_key")),
                "row": row,
                "prediction": prediction,
                "sidecar": sidecar,
                "diagnostic": diagnostic,
                "predicted_value": predicted_value,
                "gold_value": gold_value,
                "source_text": source_text,
                "collision": collision,
                "normalized_collision": normalized_collision,
                "source_attested_exact_input": source_attested_input,
                "source_attested_exact": source_attested_exact,
                "gold_correct_exact": audit.get("gold_correct_exact"),
            }
        )
    return sorted(events, key=lambda row: (row["role"], row["sample_id"], row["slot_path"]))


def _build_case_ledger(inputs: dict[str, Any], source_attested_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = []
    for event in source_attested_events:
        if event["gold_correct_exact"] is not False:
            continue
        audit = event["audit"]
        role = event["role"]
        sample_id = event["sample_id"]
        slot_path = event["slot_path"]
        row = event["row"]
        prediction = event["prediction"]
        diagnostic = event["diagnostic"]
        predicted_value = event["predicted_value"]
        gold_value = event["gold_value"]
        source_text = event["source_text"]
        collision = event["collision"]
        normalized_collision = event["normalized_collision"]
        source_attested_input = event["source_attested_exact_input"]
        source_attested_exact = source_attested_input and not normalized_collision
        mechanism = classify_mismatch_mechanism(
            condition_tags=[str(tag) for tag in row.get("provenance", {}).get("condition_tags", [])],
            predicted_value=predicted_value,
            gold_value=gold_value,
            source_text=source_text,
            slot_path=slot_path,
            normalized_collision=normalized_collision,
            span_attested=source_attested_input,
        )
        span = diagnostic.get("source_span") if isinstance(diagnostic, dict) else None
        ledger_row = {
            "challenge_id": sample_id,
            "adapter_role": role,
            "task_type": prediction["prediction"].get("task_type"),
            "route": prediction["prediction"].get("route"),
            "slot_path": slot_path,
            "scope_key": audit.get("scope_key"),
            "condition_tags": row.get("provenance", {}).get("condition_tags", []),
            "predicted_value": predicted_value,
            "gold_value": gold_value,
            "predicted_value_hash": stable_hash(predicted_value),
            "gold_value_hash": stable_hash(gold_value),
            "source_span_offsets": _span_offsets(span),
            "source_span_hash": span.get("span_hash") if isinstance(span, dict) else None,
            "historical_trusted_provenance": True,
            "source_attested_exact_input": source_attested_input,
            "source_attested_exact": source_attested_exact,
            "semantic_correctness": "offline_gold_mismatch",
            "execution_eligible": False,
            "primary_mechanism": mechanism["primary_mechanism"],
            "secondary_mechanisms": mechanism["secondary_mechanisms"],
            "online_detectability": _online_detectability(mechanism["primary_mechanism"]),
            "offline_gold_required": True,
            "deterministic_mitigation_possible": _deterministic_mitigation_possible(mechanism["primary_mechanism"]),
            "task_level_semantic_check_required": mechanism["primary_mechanism"]
            in {"WRONG_ENTITY_FROM_SOURCE", "GENERATED_VALUE_MISMATCH", "UNCLASSIFIED_SEMANTIC_MISMATCH"},
            "scope_policy_implication": _scope_policy_implication(str(audit.get("scope_key"))),
            "normalized_collision_status": collision.status,
            "normalization_rule": collision.normalization_rule,
            "sanitized_example": _sanitized_example(source_text, predicted_value, gold_value),
        }
        for key in (
            "attribution_mode",
            "attribution_source",
            "condition_tags_used",
            "deterministic_checks_used",
            "manual_review_required",
        ):
            if key in mechanism:
                ledger_row[key] = mechanism[key]
        ledger.append(ledger_row)
    return sorted(ledger, key=lambda row: (row["adapter_role"], row["challenge_id"], row["slot_path"]))


def _build_per_scope_review(
    audits: list[dict[str, Any]],
    case_ledger: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    review: dict[str, dict[str, Any]] = {}
    trusted_by_scope: dict[str, Counter[str]] = defaultdict(Counter)
    role_by_scope: dict[str, Counter[str]] = defaultdict(Counter)
    for audit in audits:
        scope = str(audit.get("scope_key"))
        if scope not in EXPECTED_SCOPES or audit.get("trusted_provenance") is not True:
            continue
        trusted_by_scope[scope]["source_attested_count"] += 1
        role_by_scope[scope][str(audit.get("run_role"))] += 1
        if audit.get("gold_correct_exact") is True:
            trusted_by_scope[scope]["gold_correct_count"] += 1
        elif audit.get("gold_correct_exact") is False:
            trusted_by_scope[scope]["gold_mismatch_count"] += 1

    ledger_by_scope: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case_ledger:
        ledger_by_scope[str(row["scope_key"])].append(row)

    for scope in EXPECTED_SCOPES:
        counts = trusted_by_scope[scope]
        cases = ledger_by_scope[scope]
        mechanism_counts = Counter(str(row["primary_mechanism"]) for row in cases)
        source_attested_count = counts["source_attested_count"]
        mismatch_count = counts["gold_mismatch_count"]
        review[scope] = {
            "scope_key": scope,
            "source_attested_count": source_attested_count,
            "gold_correct_count": counts["gold_correct_count"],
            "gold_correct_rate": _rate(counts["gold_correct_count"], source_attested_count),
            "gold_mismatch_count": mismatch_count,
            "gold_mismatch_rate": _rate(mismatch_count, source_attested_count),
            "source_absent_substitution_count": mechanism_counts["SOURCE_ABSENT_SUBSTITUTION"],
            "normalization_collision_count": mechanism_counts["NORMALIZATION_EQUIVALENCE_COLLISION"],
            "partial_or_overlong_count": mechanism_counts["OVERLONG_SOURCE_SPAN"]
            + mechanism_counts["UNDERSPECIFIED_PARTIAL_SPAN"],
            "wrong_entity_count": mechanism_counts["WRONG_ENTITY_FROM_SOURCE"],
            "adapter_role_distribution": dict(sorted(role_by_scope[scope].items())),
            "condition_tag_distribution": _condition_counts(cases),
            "mechanism_counts": dict(sorted(mechanism_counts.items())),
            "policy_v2_proposal_status": POLICY_V2_STATUS_DEFERRED,
            "policy_v2_proposal_deferred_to": "design-copy-shadow-scope-policy-v2",
            "review_note": _scope_review_note(scope),
        }
    return review


def _build_collision_audit(source_attested_events: list[dict[str, Any]]) -> dict[str, Any]:
    checked_rows = _collision_event_rows(source_attested_events)
    events = [row for row in checked_rows if row["status"] == AMBIGUOUS_NORMALIZATION_COLLISION]
    return {
        "audit_kind": "normalized_equivalent_collision_audit",
        "normalization_rule": NORMALIZATION_RULE,
        "raw_exact_source_attested_events_checked": len(checked_rows),
        "downgrade_count": len(events),
        "events": events,
        "normalized_trusted_provenance_enabled": False,
        "execution_eligible_count": 0,
    }


def _collision_event_rows(source_attested_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in source_attested_events:
        collision = event["collision"]
        rows.append(
            {
                "challenge_id": event["sample_id"],
                "adapter_role": event["role"],
                "scope_key": event["scope_key"],
                "slot_path": event["slot_path"],
                "status": collision.status,
                "source_attested_exact": event["source_attested_exact"],
                "execution_eligible": False,
                "normalization_rule": collision.normalization_rule,
            }
        )
    return rows


def _build_summary(
    inputs: dict[str, Any],
    boundary: dict[str, Any],
    case_ledger: list[dict[str, Any]],
    per_scope: dict[str, dict[str, Any]],
    collision_audit: dict[str, Any],
) -> dict[str, Any]:
    observed = _recomputed_observed_counts(inputs["audits"])
    downgrade_count = collision_audit["downgrade_count"]
    decision = DECISION_SCOPE_REDUCTION_REQUIRED
    next_change = "design-copy-shadow-scope-policy-v2"

    return {
        "change_id": CHANGE_ID,
        "evidence_kind": EVIDENCE_KIND,
        "source_evaluation_change": "recover-and-run-frozen-adapter-challenge-evaluation",
        "source_evaluation_decision": inputs["summary"].get("decision_label"),
        "decision_label": decision,
        "recommended_next_change": next_change,
        "input_boundary_ok": boundary["ok"],
        "challenge_hash": boundary["challenge_hash"],
        "policy_hash": boundary["policy_hash"],
        "adapter_identity_status": boundary["adapter_identity_status"],
        "row_count": boundary["row_count"],
        "evaluation_audit_count": len(inputs["audits"]),
        "historical_trusted_provenance_alias": "deprecated_compatibility_input_only",
        "sidecar_v2_source_field": "source_attested_exact",
        "online_semantic_correctness": "unknown",
        "execution_eligible_count": 0,
        "source_attested_exact_input_count": observed["source_attested_exact_input_count"],
        "source_attested_gold_correct_count": observed["source_attested_gold_correct_count"],
        "source_attested_gold_mismatch_count": observed["source_attested_gold_mismatch_count"],
        "normalization_collision_downgrade_count": downgrade_count,
        "post_diagnosis_source_attested_exact_count": observed["source_attested_exact_input_count"] - downgrade_count,
        "post_diagnosis_gold_mismatch_still_requires_offline_review": len(
            [row for row in case_ledger if row["source_attested_exact"]]
        ),
        "case_ledger_count": len(case_ledger),
        "mechanism_counts": dict(sorted(Counter(row["primary_mechanism"] for row in case_ledger).items())),
        "per_scope_policy_v2_proposal": {
            scope: item["policy_v2_proposal_status"] for scope, item in per_scope.items()
        },
        "per_scope_policy_v2_proposal_deferred_to": "design-copy-shadow-scope-policy-v2",
        "technical_gate_counts": {
            "action_trusted_count": boundary["action_trusted_count"],
            "normalized_trusted_count": boundary["normalized_trusted_count"],
            "provenance_false_accept_count": inputs["hook_safety"].get("provenance_false_accept_count"),
            "runtime_decision_delta_count": inputs["hook_safety"].get("runtime_decision_delta_count"),
        },
        "claims": {
            "training_run": False,
            "prediction_rerun": False,
            "challenge_modified": False,
            "policy_v1_modified": False,
            "historical_sidecars_modified": False,
            "runtime_enforcement_enabled": False,
            "normalized_trusted_provenance_enabled": False,
            "model_improvement_claim": False,
            "production_readiness_claim": False,
        },
    }


def _recomputed_observed_counts(audits: list[dict[str, Any]]) -> dict[str, int]:
    source_attested = [
        row
        for row in audits
        if row.get("trusted_provenance") is True and row.get("status") == VERIFIED_EXACT_UNIQUE
    ]
    return {
        "source_attested_exact_input_count": len(source_attested),
        "source_attested_gold_correct_count": sum(
            1 for row in source_attested if row.get("gold_correct_exact") is True
        ),
        "source_attested_gold_mismatch_count": sum(
            1 for row in source_attested if row.get("gold_correct_exact") is False
        ),
    }


def _gold_correct_exact(inputs: dict[str, Any], role: str, sample_id: str, slot_path: str) -> bool:
    row = inputs["row_by_id"][sample_id]
    prediction = inputs["prediction_by_id"][role][sample_id]["prediction"]
    gold = row["target_contract"]
    if prediction.get("task_type") != gold.get("task_type") or prediction.get("route") != gold.get("route"):
        return False
    return flatten_slot_values(gold.get("slots", {})).get(slot_path) == flatten_slot_values(
        prediction.get("slots", {})
    ).get(slot_path)


def _find_diagnostic(sidecar: dict[str, Any], slot_path: str, scope_key: str) -> dict[str, Any]:
    for diagnostic in sidecar.get("slot_diagnostics", []):
        if diagnostic.get("slot_path") == slot_path and diagnostic.get("scope_key") == scope_key:
            return diagnostic
    raise ValueError(f"missing diagnostic for {scope_key}:{slot_path}")


def _is_source_attested_exact_input(audit: dict[str, Any], diagnostic: dict[str, Any]) -> bool:
    return (
        audit.get("trusted_provenance") is True
        and diagnostic.get("trusted_provenance") is True
        and audit.get("status") == VERIFIED_EXACT_UNIQUE
        and diagnostic.get("verification_status") == VERIFIED_EXACT_UNIQUE
        and diagnostic.get("match_kind") == "exact"
        and diagnostic.get("candidate_span_count") == 1
    )


def _span_offsets(span: Any) -> dict[str, int] | None:
    if not isinstance(span, dict):
        return None
    return {"start": int(span["start"]), "end": int(span["end"])}


def _online_detectability(primary_mechanism: str) -> str:
    if primary_mechanism == "NORMALIZATION_EQUIVALENCE_COLLISION":
        return "deterministic_source_only_collision_audit"
    if primary_mechanism == "TECHNICAL_SPAN_ATTESTATION_FAILURE":
        return "deterministic_source_span_validation"
    if primary_mechanism == "CANONICAL_STRING_MISMATCH":
        return "fixture_guided_deterministic_relation_only"
    if primary_mechanism == "TRUE_GOLD_OR_FIXTURE_AMBIGUITY":
        return "requires_fixture_or_gold_review"
    return "requires_offline_gold_or_task_semantic_check"


def _deterministic_mitigation_possible(primary_mechanism: str) -> bool:
    return primary_mechanism in {
        "NORMALIZATION_EQUIVALENCE_COLLISION",
        "CANONICAL_STRING_MISMATCH",
        "OVERLONG_SOURCE_SPAN",
        "UNDERSPECIFIED_PARTIAL_SPAN",
        "TECHNICAL_SPAN_ATTESTATION_FAILURE",
    }


def _scope_policy_implication(scope_key: str) -> str:
    if scope_key == "form_fill:fill_form:field":
        return "propose_disable_before_policy_v2"
    if scope_key == "search:search_web:query":
        return "observe_limited_requires_partial_span_guard"
    return "observe_enabled_with_low_sample_caveat"


def _sanitized_example(source_text: str, predicted_value: Any, gold_value: Any) -> dict[str, Any]:
    return {
        "source_excerpt": source_text[:120],
        "predicted_value": predicted_value,
        "gold_value": gold_value,
        "public_safe": True,
    }


def _condition_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in cases:
        counts.update(str(tag) for tag in row.get("condition_tags", []))
    return dict(sorted(counts.items()))


def _scope_review_note(scope: str) -> str:
    if scope == "form_fill:fill_form:field":
        return (
            "Field slots mix field names, values, and DOM/schema resolution risk; exact text copy alone is too weak "
            "for further integration without policy-v2 scope reduction."
        )
    if scope == "search:search_web:query":
        return "Search query scope has partial-span mismatch risk; observe-only can continue only with explicit guards."
    return "Extract target had no gold mismatch in this fixture, but sample support is small and remains observe-only."


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _empty_collision_audit() -> dict[str, Any]:
    return {
        "audit_kind": "normalized_equivalent_collision_audit",
        "normalization_rule": NORMALIZATION_RULE,
        "raw_exact_source_attested_events_checked": 0,
        "downgrade_count": 0,
        "events": [],
        "normalized_trusted_provenance_enabled": False,
        "execution_eligible_count": 0,
    }


def _empty_scope_review() -> dict[str, dict[str, Any]]:
    return {
        scope: {
            "scope_key": scope,
            "source_attested_count": 0,
            "gold_correct_count": 0,
            "gold_mismatch_count": 0,
            "policy_v2_proposal_status": POLICY_V2_STATUS_DEFERRED,
            "policy_v2_proposal_deferred_to": "design-copy-shadow-scope-policy-v2",
        }
        for scope in EXPECTED_SCOPES
    }


def _blocked_summary(decision: str, boundary: dict[str, Any]) -> dict[str, Any]:
    return {
        "change_id": CHANGE_ID,
        "evidence_kind": EVIDENCE_KIND,
        "decision_label": decision,
        "input_boundary_ok": False,
        "blocking_reasons": boundary.get("blocking_reasons", []),
        "execution_eligible_count": 0,
        "claims": {
            "training_run": False,
            "prediction_rerun": False,
            "challenge_modified": False,
            "policy_v1_modified": False,
            "historical_sidecars_modified": False,
            "runtime_enforcement_enabled": False,
            "model_improvement_claim": False,
        },
    }


def _blocked_decision(blocking_reasons: list[str]) -> str:
    invalid_input_reasons = {
        "challenge_hash_mismatch",
        "summary_challenge_hash_mismatch",
        "challenge_sft_row_count_mismatch",
        "policy_hash_mismatch",
        "policy_validation_failed",
        "adapter_identity_not_verified",
        "summary_adapter_identity_not_verified",
    }
    if any(reason in invalid_input_reasons for reason in blocking_reasons):
        return DECISION_BLOCKED_INVALID_INPUT
    return DECISION_INCONSISTENT_ARTIFACTS


def _blocked_artifact(diagnosis: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": diagnosis["summary"]["decision_label"],
        "blocking_reasons": diagnosis["input_boundary"].get("blocking_reasons", []),
        "training_run": False,
        "prediction_rerun": False,
        "challenge_modified": False,
        "policy_modified": False,
        "historical_artifacts_modified": False,
        "execution_eligible": False,
    }


def _summary_markdown(diagnosis: dict[str, Any]) -> str:
    summary = diagnosis["summary"]
    return "\n".join(
        [
            "# Copy-shadow false-trust diagnosis",
            "",
            f"Decision: `{summary['decision_label']}`.",
            "",
            "This is an offline, public-safe re-audit of committed challenge artifacts. It does not rerun "
            "predictions, train, modify policy v1, repair predictions, or enable runtime enforcement.",
            "",
            "## Counts",
            "",
            f"- Historical source-attested exact input count: `{summary['source_attested_exact_input_count']}`",
            f"- Gold-correct among source-attested exact: `{summary['source_attested_gold_correct_count']}`",
            f"- Source-attested but gold-mismatch cases: `{summary['source_attested_gold_mismatch_count']}`",
            f"- Normalized-equivalent collision downgrades: `{summary['normalization_collision_downgrade_count']}`",
            f"- Post-diagnosis source_attested_exact count: `{summary['post_diagnosis_source_attested_exact_count']}`",
            "- Execution eligible count: `0`",
            "",
            "## Policy-v2 proposal",
            "",
            *[
                f"- `{scope}`: `{status}`"
                for scope, status in summary["per_scope_policy_v2_proposal"].items()
            ],
            "",
            "Legacy diagnosis policy-v2 statuses are deferred to the deterministic "
            "`design-copy-shadow-scope-policy-v2` gate.",
            "",
            f"Recommended next change: `{summary['recommended_next_change']}`.",
            "",
        ]
    )


def _sidecar_v2_semantics_markdown(diagnosis: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Sidecar v2 source-attestation semantics",
            "",
            "`source_attested_exact` means only that the predicted slot value has a unique raw exact span in the "
            "public source input after deterministic validation. It is not semantic correctness.",
            "",
            "Historical `trusted_provenance` remains a deprecated compatibility alias for committed v1 artifacts. "
            "New diagnosis artifacts use `source_attested_exact` and keep `execution_eligible=false`.",
            "",
            "Online-style semantics keep `semantic_correctness=unknown`. Gold correctness appears only in offline "
            "diagnosis outputs that explicitly read committed gold contracts.",
            "",
            "Normalized-equivalent matches remain candidate-only. If one raw exact span has multiple normalized "
            "equivalent source candidates, the diagnosis emits `AMBIGUOUS_NORMALIZATION_COLLISION`, sets "
            "`source_attested_exact=false`, and leaves `execution_eligible=false`.",
            "",
            f"Current diagnosis decision: `{diagnosis['summary']['decision_label']}`.",
            "",
        ]
    )


def _recommended_next_change_markdown(diagnosis: dict[str, Any]) -> str:
    summary = diagnosis["summary"]
    return "\n".join(
        [
            "# Recommended next change",
            "",
            f"`{summary['recommended_next_change']}`",
            "",
            "Scope: design a policy-v2 reduction/review from this diagnosis only. Do not create naturalistic v2, "
            "do not train, do not rerun predictions, do not enable actions, and do not treat normalized provenance "
            "as trusted.",
            "",
            "Required starting facts:",
            "",
            f"- Decision label: `{summary['decision_label']}`",
            f"- Source-attested but gold-mismatch cases: `{summary['source_attested_gold_mismatch_count']}`",
            f"- Normalized-equivalent collision downgrades: `{summary['normalization_collision_downgrade_count']}`",
            "- Execution eligible count: `0`",
            "",
        ]
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_contract_hash(contract: dict[str, Any]) -> str:
    return stable_hash(canonical_contract_json(contract))
