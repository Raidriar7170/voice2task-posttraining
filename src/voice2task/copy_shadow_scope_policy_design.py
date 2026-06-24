from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from voice2task.copy_backed_shadow_interface import (
    compute_policy_hash,
    load_scope_policy,
    policy_by_scope_key,
    stable_hash,
    validate_scope_policy,
)
from voice2task.copy_backed_slot_verification import VERIFIED_EXACT_UNIQUE, normalize_copy_text
from voice2task.copy_shadow_false_trust_diagnosis import (
    EXPECTED_CHALLENGE_HASH,
    EXPECTED_POLICY_HASH,
    run_copy_shadow_false_trust_diagnosis,
)
from voice2task.io import read_json, read_jsonl, write_json

CHANGE_ID = "design-copy-shadow-scope-policy-v2"
EVIDENCE_KIND = "copy_shadow_scope_policy_v2_design"
SOURCE_EVALUATION_DIR = Path("reports/public-sample/copy-shadow-template-disjoint-challenge-v1/adapter-evaluation")
DIAGNOSIS_DIR = Path("reports/public-sample/copy-shadow-false-trust-diagnosis")
POLICY_V1_PATH = Path("configs/copy-backed-scope-policy-v1.json")
DEFAULT_OUTPUT_DIR = Path("reports/public-sample/copy-shadow-scope-policy-v2-design")
DEFAULT_PROPOSED_POLICY_PATH = Path("configs/copy-backed-scope-policy-v2.proposed.json")

DECISION_SCOPE_REDUCTION_READY = "POLICY_V2_SCOPE_REDUCTION_READY_FOR_REVIEW"
DECISION_DESIGN_READY = "POLICY_V2_DESIGN_READY_FOR_REVIEW"
DECISION_INSUFFICIENT_EVIDENCE = "POLICY_V2_DESIGN_INSUFFICIENT_EVIDENCE"
DECISION_BLOCKED = "POLICY_V2_DESIGN_BLOCKED_INVALID_INPUT"
RECOMMENDED_SCOPE_REDUCTION_NEXT_CHANGE = "review-and-freeze-copy-shadow-policy-v2-before-naturalistic-challenge"
RECOMMENDED_EVIDENCE_NEXT_CHANGE = "collect-independent-observe-only-evidence-for-copy-scopes"

GATE_VERSION = "copy-shadow-scope-policy-v2-gates-2026-06-24"
ALLOWED_REPORT_FILENAMES = {
    "summary.md",
    "summary.json",
    "post-hardening-scope-metrics.json",
    "gate-config.json",
    "scope-decisions.json",
    "taxonomy-migration.json",
    "recommended-next-change.md",
    "blocked.json",
}

HIGH_RISK_MECHANISMS = {
    "WRONG_ENTITY_FROM_SOURCE",
    "SOURCE_ABSENT_SUBSTITUTION",
    "OVERLONG_SOURCE_SPAN",
    "UNDERSPECIFIED_PARTIAL_SPAN",
    "WRONG_SLOT_OR_SCOPE_SELECTION",
    "DUPLICATE_CONTEXT_DISAMBIGUATION_FAILURE",
    "GENERATED_VALUE_MISMATCH",
}

GATE_CONFIG = {
    "version": GATE_VERSION,
    "wilson_z": 1.96,
    "observe_enabled": {
        "min_attested": 30,
        "min_control": 10,
        "min_treatment": 10,
        "min_correct_rate": 0.90,
        "min_wilson_lower": 0.75,
        "max_high_risk_mismatch_rate": 0.05,
        "max_adapter_gap": 0.10,
    },
    "observe_limited": {
        "min_attested": 20,
        "min_adapter_role": 5,
        "min_correct_rate": 0.80,
        "min_wilson_lower": 0.60,
        "max_high_risk_mismatch_rate": 0.20,
        "max_adapter_gap": 0.25,
    },
    "disable": {
        "max_correct_rate_exclusive": 0.70,
        "min_high_risk_mismatch_rate": 0.25,
    },
    "insufficient_evidence": {
        "min_attested": 20,
        "min_adapter_role": 5,
        "max_adapter_role_share": 0.75,
        "max_condition_share": 0.90,
        "max_wilson_width": 0.35,
    },
}

STATUS_CONSERVATISM_RANK = {
    "OBSERVE_ENABLED": 0,
    "OBSERVE_LIMITED": 1,
    "CANDIDATE_ONLY": 2,
    "INSUFFICIENT_EVIDENCE": 3,
    "PROPOSE_DISABLE": 4,
}


def wilson_interval(successes: int, total: int, *, z: float = 1.96) -> dict[str, float | None]:
    if total <= 0:
        return {"lower": None, "upper": None, "width": None}
    if successes < 0 or successes > total:
        raise ValueError("successes must be between 0 and total")

    phat = successes / total
    denominator = 1 + z**2 / total
    center = (phat + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * total)) / total) / denominator
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return {"lower": lower, "upper": upper, "width": upper - lower}


def compute_gate_status(metric: dict[str, Any]) -> str:
    total = int(metric.get("total_attested_count") or 0)
    correct_rate = _number(metric.get("correct_rate"))
    high_risk_rate = _number(metric.get("high_risk_mismatch_rate")) or 0.0
    wilson_lower = _number(metric.get("wilson_95", {}).get("lower"))
    adapter_counts = {str(k): int(v) for k, v in metric.get("adapter_role_counts", {}).items()}
    adapter_gap = _number(metric.get("adapter_gap"))
    action_count = int(metric.get("action_attested_count") or 0)
    normalized_count = int(metric.get("normalized_attested_count") or 0)

    if (
        int(metric.get("technical_false_accept_count") or 0) > 0
        or int(metric.get("scope_policy_violation_count") or 0) > 0
        or bool(metric.get("mixed_incompatible_slot_semantics"))
        or bool(metric.get("no_engineering_value"))
        or bool(metric.get("high_downstream_misuse_risk"))
    ):
        return "PROPOSE_DISABLE"

    if _is_insufficient_evidence(metric, total, adapter_counts):
        return "INSUFFICIENT_EVIDENCE"

    if (
        correct_rate is not None
        and (
            correct_rate < GATE_CONFIG["disable"]["max_correct_rate_exclusive"]
            or high_risk_rate >= GATE_CONFIG["disable"]["min_high_risk_mismatch_rate"]
        )
    ):
        return "PROPOSE_DISABLE"

    enabled_cfg = GATE_CONFIG["observe_enabled"]
    if (
        total >= enabled_cfg["min_attested"]
        and adapter_counts.get("control", 0) >= enabled_cfg["min_control"]
        and adapter_counts.get("treatment", 0) >= enabled_cfg["min_treatment"]
        and correct_rate is not None
        and correct_rate >= enabled_cfg["min_correct_rate"]
        and wilson_lower is not None
        and wilson_lower >= enabled_cfg["min_wilson_lower"]
        and high_risk_rate <= enabled_cfg["max_high_risk_mismatch_rate"]
        and adapter_gap is not None
        and adapter_gap <= enabled_cfg["max_adapter_gap"]
        and not bool(metric.get("unresolved_semantic_boundary"))
    ):
        return "OBSERVE_ENABLED"

    limited_cfg = GATE_CONFIG["observe_limited"]
    if (
        total >= limited_cfg["min_attested"]
        and adapter_counts
        and min(adapter_counts.values()) >= limited_cfg["min_adapter_role"]
        and correct_rate is not None
        and correct_rate >= limited_cfg["min_correct_rate"]
        and wilson_lower is not None
        and wilson_lower >= limited_cfg["min_wilson_lower"]
        and high_risk_rate <= limited_cfg["max_high_risk_mismatch_rate"]
        and adapter_gap is not None
        and adapter_gap <= limited_cfg["max_adapter_gap"]
        and action_count == 0
        and normalized_count == 0
    ):
        return "OBSERVE_LIMITED"

    return "CANDIDATE_ONLY"


def apply_downward_override(
    original_gate_status: str,
    final_status: str,
    *,
    semantic_reason: str,
    evidence_reference: str,
    reviewer_required: bool,
) -> dict[str, Any]:
    if original_gate_status not in STATUS_CONSERVATISM_RANK:
        raise ValueError(f"unknown original gate status: {original_gate_status}")
    if final_status not in STATUS_CONSERVATISM_RANK:
        raise ValueError(f"unknown final status: {final_status}")
    if STATUS_CONSERVATISM_RANK[final_status] < STATUS_CONSERVATISM_RANK[original_gate_status]:
        raise ValueError("upward override is not allowed")
    if not semantic_reason.strip():
        raise ValueError("semantic_reason is required")
    if not evidence_reference.strip():
        raise ValueError("evidence_reference is required")
    return {
        "original_gate_status": original_gate_status,
        "final_status": final_status,
        "override_direction": "none" if final_status == original_gate_status else "downward",
        "semantic_reason": semantic_reason,
        "evidence_reference": evidence_reference,
        "reviewer_required": bool(reviewer_required),
    }


def migrate_case_ledger_taxonomy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    migrated: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        _add_derived_secondary_mechanisms(item)
        attribution = _fixture_guided_attribution(item)
        if item.get("primary_mechanism") == "CHALLENGE_FIXTURE_OR_GOLD_AMBIGUITY":
            item["primary_mechanism"] = attribution["primary_mechanism"]
            secondary = set(str(value) for value in item.get("secondary_mechanisms", []))
            secondary.discard("NORMALIZED_GOLD_EQUIVALENT_STRING_MISMATCH")
            item["secondary_mechanisms"] = sorted(secondary)
            item.update({key: value for key, value in attribution.items() if key != "primary_mechanism"})
        elif item.get("primary_mechanism") in {"CANONICAL_STRING_MISMATCH", "TRUE_GOLD_OR_FIXTURE_AMBIGUITY"}:
            item.update({key: value for key, value in attribution.items() if key != "primary_mechanism"})
        else:
            item.setdefault("attribution_mode", "fixture_guided")
            item.setdefault("attribution_source", _default_attribution_source(item))
            item.setdefault("condition_tags_used", [str(tag) for tag in item.get("condition_tags", [])])
            item.setdefault("deterministic_checks_used", _default_deterministic_checks(item))
            item.setdefault("manual_review_required", str(item.get("primary_mechanism")) in HIGH_RISK_MECHANISMS)
        migrated.append(item)
    return migrated


def compute_scope_metrics(
    *,
    audits: list[dict[str, Any]],
    migrated_ledger: list[dict[str, Any]],
    policy: dict[str, Any],
    technical_gate_counts: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    policy_rows = policy_by_scope_key(policy)
    scopes = sorted(policy_rows)
    audits_by_scope: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for audit in audits:
        scope = str(audit.get("scope_key"))
        if scope in policy_rows and _is_attested_audit(audit):
            audits_by_scope[scope].append(audit)

    ledger_by_scope: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in migrated_ledger:
        ledger_by_scope[str(row.get("scope_key"))].append(row)

    metrics: dict[str, dict[str, Any]] = {}
    for scope in scopes:
        if scope not in policy.get("enabled_triples", []):
            continue
        scope_audits = audits_by_scope[scope]
        cases = ledger_by_scope[scope]
        total = len(scope_audits)
        correct = sum(1 for audit in scope_audits if audit.get("gold_correct_exact") is True)
        role_counts = Counter(str(audit.get("run_role")) for audit in scope_audits)
        role_correct = Counter(
            str(audit.get("run_role")) for audit in scope_audits if audit.get("gold_correct_exact") is True
        )
        role_rates = {
            role: role_correct[role] / count
            for role, count in sorted(role_counts.items())
            if count
        }
        high_risk_count = _high_risk_mismatch_count(cases)
        mechanism_counts = Counter(str(row.get("primary_mechanism")) for row in cases)
        condition_counts = _condition_counts(cases)
        max_condition_share = _max_share(condition_counts.values())
        adapter_gap = max(role_rates.values()) - min(role_rates.values()) if len(role_rates) >= 2 else None
        execution_eligible_count = sum(1 for row in cases if row.get("execution_eligible") is True)
        metrics[scope] = {
            "scope_key": scope,
            "total_attested_count": total,
            "gold_correct_count": correct,
            "correct_rate": _rate(correct, total),
            "wilson_95": wilson_interval(correct, total),
            "high_risk_mismatch_count": high_risk_count,
            "high_risk_mismatch_rate": _rate(high_risk_count, total),
            "adapter_role_counts": dict(sorted(role_counts.items())),
            "adapter_role_correct_rates": role_rates,
            "adapter_gap": adapter_gap,
            "available_adapter_roles": sorted(role_counts),
            "mechanism_counts": dict(sorted(mechanism_counts.items())),
            "canonical_string_mismatch_count": mechanism_counts["CANONICAL_STRING_MISMATCH"],
            "true_gold_or_fixture_ambiguity_count": mechanism_counts["TRUE_GOLD_OR_FIXTURE_AMBIGUITY"],
            "normalization_collision_count": mechanism_counts["NORMALIZATION_EQUIVALENCE_COLLISION"],
            "condition_tag_distribution": dict(sorted(condition_counts.items())),
            "condition_max_share": max_condition_share,
            "fixture_evidence_independent": True,
            "technical_false_accept_count": int(
                technical_gate_counts.get("provenance_false_accept_count")
                or technical_gate_counts.get("technical_false_accept_count")
                or 0
            ),
            "scope_policy_violation_count": int(technical_gate_counts.get("scope_policy_violation_count") or 0),
            "action_attested_count": int(
                technical_gate_counts.get("action_attested_count")
                or technical_gate_counts.get("action_trusted_count")
                or 0
            ),
            "normalized_attested_count": int(
                technical_gate_counts.get("normalized_attested_count")
                or technical_gate_counts.get("normalized_trusted_count")
                or 0
            ),
            "execution_eligible_count": execution_eligible_count,
            "policy_v1_enabled": bool(policy_rows[scope].get("enabled")),
            "unresolved_semantic_boundary": False,
            "mixed_incompatible_slot_semantics": False,
            "no_engineering_value": False,
            "high_downstream_misuse_risk": False,
            "evidence_sufficiency": _evidence_sufficiency(total, role_counts, max_condition_share),
        }
    return metrics


def run_copy_shadow_scope_policy_design(
    repo_root: Path,
    *,
    expected_challenge_hash: str = EXPECTED_CHALLENGE_HASH,
    expected_policy_hash: str = EXPECTED_POLICY_HASH,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    boundary = _validate_design_input_boundary(
        repo_root,
        expected_challenge_hash=expected_challenge_hash,
        expected_policy_hash=expected_policy_hash,
    )
    if not boundary["ok"]:
        return {
            "summary": _blocked_summary(boundary),
            "input_boundary": boundary,
            "scope_metrics": {},
            "scope_decisions": {},
            "taxonomy_migration": {},
            "proposed_policy": {},
            "gate_config": GATE_CONFIG,
        }

    diagnosis_dir = repo_root / DIAGNOSIS_DIR
    evaluation_dir = repo_root / SOURCE_EVALUATION_DIR
    policy = load_scope_policy(repo_root / POLICY_V1_PATH)
    audits = read_jsonl(evaluation_dir / "evaluation-audits.jsonl")
    ledger = read_jsonl(diagnosis_dir / "false-trust-case-ledger.jsonl")
    migrated_ledger = migrate_case_ledger_taxonomy(ledger)
    diagnosis_summary = read_json(diagnosis_dir / "summary.json")
    metrics = compute_scope_metrics(
        audits=audits,
        migrated_ledger=migrated_ledger,
        policy=policy,
        technical_gate_counts=diagnosis_summary.get("technical_gate_counts", {}),
    )
    decisions = _scope_decisions(metrics)
    taxonomy_migration = _taxonomy_migration_report(ledger, migrated_ledger)
    summary = _summary(repo_root, boundary, metrics, decisions, taxonomy_migration)
    proposed_policy = _proposed_policy(boundary, summary, metrics, decisions)
    return {
        "summary": summary,
        "input_boundary": boundary,
        "scope_metrics": metrics,
        "scope_decisions": decisions,
        "taxonomy_migration": taxonomy_migration,
        "proposed_policy": proposed_policy,
        "gate_config": GATE_CONFIG,
    }


def write_copy_shadow_scope_policy_design_report(
    repo_root: Path,
    *,
    output_dir: Path | None = None,
    proposed_policy_path: Path | None = None,
    expected_challenge_hash: str = EXPECTED_CHALLENGE_HASH,
    expected_policy_hash: str = EXPECTED_POLICY_HASH,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = _resolve_repo_path(repo_root, output_dir or DEFAULT_OUTPUT_DIR)
    proposed_policy_path = _resolve_repo_path(repo_root, proposed_policy_path or DEFAULT_PROPOSED_POLICY_PATH)
    result = run_copy_shadow_scope_policy_design(
        repo_root,
        expected_challenge_hash=expected_challenge_hash,
        expected_policy_hash=expected_policy_hash,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    _remove_stale_report_files(output_dir)

    if result["summary"]["decision_label"] == DECISION_BLOCKED:
        if proposed_policy_path.exists():
            proposed_policy_path.unlink()
        write_json(output_dir / "blocked.json", _blocked_artifact(result))
        return result

    write_json(output_dir / "summary.json", result["summary"])
    write_json(output_dir / "post-hardening-scope-metrics.json", result["scope_metrics"])
    write_json(output_dir / "gate-config.json", result["gate_config"])
    write_json(output_dir / "scope-decisions.json", result["scope_decisions"])
    write_json(output_dir / "taxonomy-migration.json", result["taxonomy_migration"])
    write_json(proposed_policy_path, result["proposed_policy"])
    (output_dir / "summary.md").write_text(_summary_markdown(result), encoding="utf-8")
    (output_dir / "recommended-next-change.md").write_text(_recommended_next_change_markdown(result), encoding="utf-8")
    return result


def _is_insufficient_evidence(metric: dict[str, Any], total: int, adapter_counts: dict[str, int]) -> bool:
    if total < GATE_CONFIG["insufficient_evidence"]["min_attested"]:
        return True
    if len(adapter_counts) < 2:
        return True
    if min(adapter_counts.values()) < GATE_CONFIG["insufficient_evidence"]["min_adapter_role"]:
        return True
    if max(adapter_counts.values()) / total > GATE_CONFIG["insufficient_evidence"]["max_adapter_role_share"]:
        return True
    condition_max_share = _number(metric.get("condition_max_share")) or 0.0
    if condition_max_share > GATE_CONFIG["insufficient_evidence"]["max_condition_share"]:
        return True
    wilson_width = _number(metric.get("wilson_95", {}).get("width"))
    if wilson_width is not None and wilson_width > GATE_CONFIG["insufficient_evidence"]["max_wilson_width"]:
        return True
    if metric.get("fixture_evidence_independent") is False:
        return True
    return False


def _resolve_repo_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _fixture_guided_attribution(row: dict[str, Any]) -> dict[str, Any]:
    tags = {str(tag) for tag in row.get("condition_tags", [])}
    predicted = row.get("predicted_value")
    gold = row.get("gold_value")
    deterministic_checks: list[str] = []
    normalized_equivalent = isinstance(predicted, str) and isinstance(gold, str) and (
        normalize_copy_text(predicted) == normalize_copy_text(gold)
    )
    if normalized_equivalent:
        deterministic_checks.append("normalized_value_equivalence")
    if normalized_equivalent:
        source = "fixture_tag_plus_deterministic_relation" if tags else "deterministic_relation"
        primary = "CANONICAL_STRING_MISMATCH"
        manual_review = False
    else:
        source = "reviewed_fixture_ambiguity"
        primary = "TRUE_GOLD_OR_FIXTURE_AMBIGUITY"
        manual_review = True
    return {
        "primary_mechanism": primary,
        "attribution_mode": "fixture_guided",
        "attribution_source": source,
        "condition_tags_used": sorted(tags),
        "deterministic_checks_used": deterministic_checks,
        "manual_review_required": manual_review,
    }


def _default_attribution_source(row: dict[str, Any]) -> str:
    tags = row.get("condition_tags", [])
    checks = _default_deterministic_checks(row)
    if tags and checks:
        return "fixture_tag_plus_deterministic_relation"
    if tags:
        return "fixture_tag"
    return "deterministic_relation"


def _default_deterministic_checks(row: dict[str, Any]) -> list[str]:
    checks: list[str] = []
    primary = str(row.get("primary_mechanism"))
    if primary == "NORMALIZATION_EQUIVALENCE_COLLISION":
        checks.append("normalized_collision_audit")
    predicted = row.get("predicted_value")
    gold = row.get("gold_value")
    if isinstance(predicted, str) and isinstance(gold, str) and predicted != gold:
        if predicted.startswith(gold) or gold.startswith(predicted):
            checks.append("span_prefix_relation")
        if normalize_copy_text(predicted) == normalize_copy_text(gold):
            checks.append("normalized_value_equivalence")
    if row.get("source_attested_exact_input") is True:
        checks.append("source_attested_exact_input")
    if row.get("source_attested_exact") is False:
        checks.append("source_attestation_downgraded")
    return sorted(set(checks))


def _add_derived_secondary_mechanisms(row: dict[str, Any]) -> None:
    predicted = row.get("predicted_value")
    gold = row.get("gold_value")
    if not isinstance(predicted, str) or not isinstance(gold, str) or predicted == gold:
        return
    secondary = set(str(value) for value in row.get("secondary_mechanisms", []))
    if predicted in gold and row.get("primary_mechanism") != "UNDERSPECIFIED_PARTIAL_SPAN":
        secondary.add("UNDERSPECIFIED_PARTIAL_SPAN")
    if gold in predicted and row.get("primary_mechanism") != "OVERLONG_SOURCE_SPAN":
        secondary.add("OVERLONG_SOURCE_SPAN")
    row["secondary_mechanisms"] = sorted(secondary)


def _is_attested_audit(audit: dict[str, Any]) -> bool:
    return audit.get("trusted_provenance") is True and audit.get("status") == VERIFIED_EXACT_UNIQUE


def _high_risk_mismatch_count(cases: list[dict[str, Any]]) -> int:
    count = 0
    for row in cases:
        if str(row.get("primary_mechanism")) in HIGH_RISK_MECHANISMS:
            count += 1
        count += sum(1 for value in row.get("secondary_mechanisms", []) if str(value) in HIGH_RISK_MECHANISMS)
    return count


def _condition_counts(cases: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in cases:
        counts.update(str(tag) for tag in row.get("condition_tags", []))
    return counts


def _evidence_sufficiency(total: int, role_counts: Counter[str], condition_max_share: float) -> dict[str, Any]:
    min_adapter = min(role_counts.values()) if role_counts else 0
    max_adapter_share = max(role_counts.values()) / total if total and role_counts else None
    return {
        "sample_count_below_20": total < GATE_CONFIG["insufficient_evidence"]["min_attested"],
        "only_one_adapter_role": len(role_counts) < 2,
        "min_available_adapter_count": min_adapter,
        "adapter_max_share": max_adapter_share,
        "adapter_overdependence": bool(
            max_adapter_share is not None
            and max_adapter_share > GATE_CONFIG["insufficient_evidence"]["max_adapter_role_share"]
        ),
        "condition_max_share": condition_max_share,
        "condition_overdependence": condition_max_share > GATE_CONFIG["insufficient_evidence"]["max_condition_share"],
    }


def _scope_decisions(metrics: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for scope, metric in sorted(metrics.items()):
        original = compute_gate_status(metric)
        override = None
        final_status = original
        decisions[scope] = {
            "scope_key": scope,
            "original_gate_status": original,
            "final_status": final_status,
            "override": override,
            "gate_version": GATE_VERSION,
            "evidence_reference": (
                "reports/public-sample/copy-shadow-scope-policy-v2-design/"
                f"post-hardening-scope-metrics.json#{scope}"
            ),
            "reviewer_required": final_status in {"OBSERVE_ENABLED", "OBSERVE_LIMITED", "CANDIDATE_ONLY"},
            "execution_eligible": False,
        }
    return decisions


def _taxonomy_migration_report(original: list[dict[str, Any]], migrated: list[dict[str, Any]]) -> dict[str, Any]:
    original_counts = Counter(str(row.get("primary_mechanism")) for row in original)
    migrated_counts = Counter(str(row.get("primary_mechanism")) for row in migrated)
    migrated_rows = [
        {
            "challenge_id": row.get("challenge_id"),
            "adapter_role": row.get("adapter_role"),
            "scope_key": row.get("scope_key"),
            "primary_mechanism": row.get("primary_mechanism"),
            "attribution_mode": row.get("attribution_mode"),
            "attribution_source": row.get("attribution_source"),
            "condition_tags_used": row.get("condition_tags_used", []),
            "deterministic_checks_used": row.get("deterministic_checks_used", []),
            "manual_review_required": row.get("manual_review_required"),
        }
        for row in migrated
        if row.get("attribution_mode") == "fixture_guided"
    ]
    return {
        "migration_kind": "copy_shadow_false_trust_taxonomy_policy_v2",
        "source_mechanism": "CHALLENGE_FIXTURE_OR_GOLD_AMBIGUITY",
        "target_mechanisms": ["CANONICAL_STRING_MISMATCH", "TRUE_GOLD_OR_FIXTURE_AMBIGUITY"],
        "original_mechanism_counts": dict(sorted(original_counts.items())),
        "migrated_mechanism_counts": dict(sorted(migrated_counts.items())),
        "fixture_guided_row_count": len(migrated_rows),
        "migrated_rows": migrated_rows,
    }


def _summary(
    repo_root: Path,
    boundary: dict[str, Any],
    metrics: dict[str, dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    taxonomy_migration: dict[str, Any],
) -> dict[str, Any]:
    status_counts = Counter(row["final_status"] for row in decisions.values())
    reduction_ready = (
        any(status in status_counts for status in ("OBSERVE_LIMITED", "PROPOSE_DISABLE"))
        and status_counts.get("OBSERVE_ENABLED", 0) == 0
        and all(row["execution_eligible_count"] == 0 for row in metrics.values())
        and sum(row["technical_false_accept_count"] for row in metrics.values()) == 0
    )
    insufficient_only = bool(status_counts) and all(
        status == "INSUFFICIENT_EVIDENCE" for status in status_counts
    )
    if reduction_ready:
        decision = DECISION_SCOPE_REDUCTION_READY
        next_change = RECOMMENDED_SCOPE_REDUCTION_NEXT_CHANGE
    elif insufficient_only:
        decision = DECISION_INSUFFICIENT_EVIDENCE
        next_change = RECOMMENDED_EVIDENCE_NEXT_CHANGE
    else:
        decision = DECISION_DESIGN_READY
        next_change = RECOMMENDED_SCOPE_REDUCTION_NEXT_CHANGE

    return {
        "change_id": CHANGE_ID,
        "evidence_kind": EVIDENCE_KIND,
        "decision_label": decision,
        "recommended_next_change": next_change,
        "input_boundary_ok": boundary["ok"],
        "challenge_hash": boundary["challenge_hash"],
        "source_policy_v1_id": boundary["source_policy_v1_id"],
        "source_policy_v1_hash": boundary["source_policy_v1_hash"],
        "diagnosis_artifact_hash": boundary["diagnosis_artifact_hash"],
        "decision_gate_version": GATE_VERSION,
        "scope_status_counts": dict(sorted(status_counts.items())),
        "technical_false_accept_count": max(
            (row["technical_false_accept_count"] for row in metrics.values()), default=0
        ),
        "action_attested_count": max((row["action_attested_count"] for row in metrics.values()), default=0),
        "normalized_attested_count": max((row["normalized_attested_count"] for row in metrics.values()), default=0),
        "execution_eligible_count": sum(row["execution_eligible_count"] for row in metrics.values()),
        "taxonomy_fixture_guided_row_count": taxonomy_migration["fixture_guided_row_count"],
        "report_dir": str((repo_root / DEFAULT_OUTPUT_DIR).relative_to(repo_root)),
        "proposed_policy_path": str(DEFAULT_PROPOSED_POLICY_PATH),
        "claims": _claims(),
    }


def _proposed_policy(
    boundary: dict[str, Any],
    summary: dict[str, Any],
    metrics: dict[str, dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "policy_id": "copy-backed-scope-policy-v2-proposed",
        "policy_version": "2.0.0-proposed",
        "status": "proposal",
        "active": False,
        "runtime_loaded": False,
        "enforcement_enabled": False,
        "action_enabled": False,
        "normalized_trusted": False,
        "source_policy_v1_id": boundary["source_policy_v1_id"],
        "source_policy_v1_hash": boundary["source_policy_v1_hash"],
        "challenge_v1_hash": boundary["challenge_hash"],
        "diagnosis_artifact_hash": boundary["diagnosis_artifact_hash"],
        "decision_gate_version": GATE_VERSION,
        "decision_label": summary["decision_label"],
        "recommended_next_change": summary["recommended_next_change"],
        "scopes": {
            scope: {
                "metrics": metrics[scope],
                "original_gate_status": decisions[scope]["original_gate_status"],
                "final_status": decisions[scope]["final_status"],
                "override": decisions[scope]["override"],
                "evidence_reference": decisions[scope]["evidence_reference"],
                "execution_eligible": False,
            }
            for scope in sorted(decisions)
        },
        "claims": _claims(),
    }


def _validate_design_input_boundary(
    repo_root: Path,
    *,
    expected_challenge_hash: str,
    expected_policy_hash: str,
) -> dict[str, Any]:
    blocking: list[str] = []
    evaluation_dir = repo_root / SOURCE_EVALUATION_DIR
    diagnosis_dir = repo_root / DIAGNOSIS_DIR
    required_files = [
        evaluation_dir / "challenge-sft/manifest.json",
        evaluation_dir / "challenge-evaluation-summary.json",
        evaluation_dir / "adapter-identity-audit.json",
        evaluation_dir / "prediction-run-audit.json",
        evaluation_dir / "hook-safety-audit.json",
        evaluation_dir / "evaluation-audits.jsonl",
        diagnosis_dir / "summary.json",
        diagnosis_dir / "false-trust-case-ledger.jsonl",
        diagnosis_dir / "per-scope-risk-review.json",
        diagnosis_dir / "normalization-collision-audit.json",
        repo_root / POLICY_V1_PATH,
    ]
    for path in required_files:
        if not path.exists():
            blocking.append(f"missing:{path.relative_to(repo_root)}")

    if blocking:
        return _boundary_from_blocking(blocking)

    policy = load_scope_policy(repo_root / POLICY_V1_PATH)
    policy_validation = validate_scope_policy(policy)
    manifest = read_json(evaluation_dir / "challenge-sft/manifest.json")
    evaluation_summary = read_json(evaluation_dir / "challenge-evaluation-summary.json")
    diagnosis_summary = read_json(diagnosis_dir / "summary.json")
    diagnosis_ledger = read_jsonl(diagnosis_dir / "false-trust-case-ledger.jsonl")
    diagnosis_per_scope = read_json(diagnosis_dir / "per-scope-risk-review.json")
    collision_audit = read_json(diagnosis_dir / "normalization-collision-audit.json")
    hook_safety = read_json(evaluation_dir / "hook-safety-audit.json")
    recomputed_diagnosis = run_copy_shadow_false_trust_diagnosis(repo_root)

    challenge_hash = str(manifest.get("challenge_hash"))
    source_policy_hash = compute_policy_hash(policy)
    if challenge_hash != expected_challenge_hash:
        blocking.append("challenge_hash_mismatch")
    if evaluation_summary.get("challenge_hash") != expected_challenge_hash:
        blocking.append("evaluation_summary_challenge_hash_mismatch")
    if diagnosis_summary.get("challenge_hash") != expected_challenge_hash:
        blocking.append("diagnosis_summary_challenge_hash_mismatch")
    if source_policy_hash != expected_policy_hash or policy_validation.get("ok") is not True:
        blocking.append("policy_v1_hash_or_validation_mismatch")
    if diagnosis_summary.get("policy_hash") != expected_policy_hash:
        blocking.append("diagnosis_policy_hash_mismatch")
    if evaluation_summary.get("adapter_identity_status") != "verified":
        blocking.append("adapter_identity_not_verified")
    if evaluation_summary.get("pipeline_integrity", {}).get("v1_metric_delta_zero") is not True:
        blocking.append("v1_metric_delta_not_zero")
    if hook_safety.get("action_trusted_count") != 0:
        blocking.append("action_trusted_count_nonzero")
    if hook_safety.get("normalized_trusted_count") != 0:
        blocking.append("normalized_trusted_count_nonzero")
    if hook_safety.get("provenance_false_accept_count") != 0:
        blocking.append("provenance_false_accept_count_nonzero")
    if diagnosis_summary.get("execution_eligible_count") != 0:
        blocking.append("execution_eligible_count_nonzero")
    if diagnosis_summary.get("online_semantic_correctness") != "unknown":
        blocking.append("source_only_sidecar_semantics_missing")
    if collision_audit.get("downgrade_count") != diagnosis_summary.get("normalization_collision_downgrade_count"):
        blocking.append("normalization_collision_downgrade_count_mismatch")
    for event in collision_audit.get("events", []):
        if event.get("source_attested_exact") is not False or event.get("execution_eligible") is not False:
            blocking.append("normalization_collision_event_not_downgraded")
            break
    if recomputed_diagnosis["input_boundary"].get("ok") is not True:
        blocking.extend(
            f"recomputed_diagnosis:{reason}"
            for reason in recomputed_diagnosis["input_boundary"].get("blocking_reasons", [])
        )
    if stable_hash(diagnosis_ledger) != stable_hash(recomputed_diagnosis["case_ledger"]):
        blocking.append("diagnosis_case_ledger_drift")
    if stable_hash(diagnosis_per_scope) != stable_hash(recomputed_diagnosis["per_scope_risk_review"]):
        blocking.append("diagnosis_per_scope_risk_review_drift")
    if stable_hash(collision_audit) != stable_hash(recomputed_diagnosis["normalization_collision_audit"]):
        blocking.append("diagnosis_collision_audit_drift")
    for key in (
        "decision_label",
        "mechanism_counts",
        "source_attested_exact_input_count",
        "source_attested_gold_correct_count",
        "source_attested_gold_mismatch_count",
        "normalization_collision_downgrade_count",
        "post_diagnosis_source_attested_exact_count",
        "per_scope_policy_v2_proposal",
    ):
        if diagnosis_summary.get(key) != recomputed_diagnosis["summary"].get(key):
            blocking.append(f"diagnosis_summary_drift:{key}")

    return {
        "audit_kind": "copy_shadow_scope_policy_v2_design_input_boundary",
        "ok": not blocking,
        "blocking_reasons": blocking,
        "challenge_hash": challenge_hash,
        "expected_challenge_hash": expected_challenge_hash,
        "source_policy_v1_id": str(policy.get("policy_id")),
        "source_policy_v1_hash": source_policy_hash,
        "expected_policy_hash": expected_policy_hash,
        "policy_v1_validation": policy_validation,
        "adapter_identity_status": evaluation_summary.get("adapter_identity_status"),
        "v1_metric_delta_zero": evaluation_summary.get("pipeline_integrity", {}).get("v1_metric_delta_zero") is True,
        "action_attested_count": hook_safety.get("action_trusted_count"),
        "normalized_attested_count": hook_safety.get("normalized_trusted_count"),
        "technical_false_accept_count": hook_safety.get("provenance_false_accept_count"),
        "execution_eligible_count": diagnosis_summary.get("execution_eligible_count"),
        "diagnosis_artifact_hash": _sha256_file(diagnosis_dir / "false-trust-case-ledger.jsonl"),
        "source_only_sidecar_semantics": diagnosis_summary.get("online_semantic_correctness") == "unknown",
    }


def _boundary_from_blocking(blocking: list[str]) -> dict[str, Any]:
    return {
        "audit_kind": "copy_shadow_scope_policy_v2_design_input_boundary",
        "ok": False,
        "blocking_reasons": blocking,
        "challenge_hash": None,
        "expected_challenge_hash": EXPECTED_CHALLENGE_HASH,
        "source_policy_v1_id": None,
        "source_policy_v1_hash": None,
        "expected_policy_hash": EXPECTED_POLICY_HASH,
        "diagnosis_artifact_hash": None,
    }


def _blocked_summary(boundary: dict[str, Any]) -> dict[str, Any]:
    return {
        "change_id": CHANGE_ID,
        "evidence_kind": EVIDENCE_KIND,
        "decision_label": DECISION_BLOCKED,
        "recommended_next_change": None,
        "input_boundary_ok": False,
        "blocking_reasons": boundary.get("blocking_reasons", []),
        "claims": _claims(),
    }


def _blocked_artifact(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result["summary"]["decision_label"],
        "blocking_reasons": result["input_boundary"].get("blocking_reasons", []),
        "proposed_policy_emitted": False,
        "policy_v1_modified": False,
        "challenge_modified": False,
        "prediction_rerun": False,
        "runtime_enforcement_enabled": False,
    }


def _summary_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    decisions = result["scope_decisions"]
    lines = [
        "# Copy-shadow scope policy v2 design",
        "",
        f"Decision: `{summary['decision_label']}`.",
        "",
        "Policy V2 is proposal-only. It is inactive, not runtime loaded, not enforcement, not action eligibility, "
        "not normalized trust, not training, not model improvement, and not a production or safety readiness claim.",
        "",
        "## Scope decisions",
        "",
    ]
    lines.extend(
        f"- `{scope}`: original `{row['original_gate_status']}`, final `{row['final_status']}`"
        for scope, row in sorted(decisions.items())
    )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- Challenge hash: `{summary['challenge_hash']}`",
            f"- Policy V1 hash: `{summary['source_policy_v1_hash']}`",
            f"- Technical false accepts: `{summary['technical_false_accept_count']}`",
            f"- Execution eligible count: `{summary['execution_eligible_count']}`",
            "",
            f"Recommended next change: `{summary['recommended_next_change']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def _recommended_next_change_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    return "\n".join(
        [
            "# Recommended next change",
            "",
            f"`{summary['recommended_next_change']}`",
            "",
            "Review and freeze the inactive Policy V2 proposal before any naturalistic challenge, runtime loading, "
            "training, action enablement, normalized trust, or public readiness claim.",
            "",
        ]
    )


def _remove_stale_report_files(output_dir: Path) -> None:
    for child in output_dir.iterdir():
        if child.is_file():
            child.unlink()
        else:
            raise ValueError(f"unexpected report bundle entry: {child}")


def _claims() -> dict[str, bool]:
    return {
        "training_run": False,
        "prediction_rerun": False,
        "challenge_modified": False,
        "policy_v1_modified": False,
        "historical_sidecars_modified": False,
        "runtime_enforcement_enabled": False,
        "normalized_trusted_provenance_enabled": False,
        "model_improvement_claim": False,
        "production_readiness_claim": False,
        "safety_readiness_claim": False,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _max_share(values: Any) -> float:
    values = [int(value) for value in values]
    total = sum(values)
    if total == 0:
        return 0.0
    return max(values) / total


def _number(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def proposed_policy_hash(policy: dict[str, Any]) -> str:
    return stable_hash(policy)
