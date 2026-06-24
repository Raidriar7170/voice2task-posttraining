from __future__ import annotations

import json
from pathlib import Path

import pytest

from voice2task.copy_backed_shadow_interface import compute_policy_hash
from voice2task.copy_shadow_scope_policy_design import (
    DECISION_SCOPE_REDUCTION_READY,
    EXPECTED_CHALLENGE_HASH,
    EXPECTED_POLICY_HASH,
    HIGH_RISK_MECHANISMS,
    apply_downward_override,
    compute_gate_status,
    compute_scope_metrics,
    migrate_case_ledger_taxonomy,
    run_copy_shadow_scope_policy_design,
    wilson_interval,
    write_copy_shadow_scope_policy_design_report,
)
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSIS_DIR = REPO_ROOT / "reports/public-sample/copy-shadow-false-trust-diagnosis"
DESIGN_DIR = REPO_ROOT / "reports/public-sample/copy-shadow-scope-policy-v2-design"
POLICY_V1_PATH = REPO_ROOT / "configs/copy-backed-scope-policy-v1.json"
POLICY_V2_PROPOSED_PATH = REPO_ROOT / "configs/copy-backed-scope-policy-v2.proposed.json"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _metric(
    *,
    total: int,
    correct: int,
    high_risk: int = 0,
    control: int | None = None,
    treatment: int | None = None,
    adapter_rates: dict[str, float] | None = None,
    technical_false_accept_count: int = 0,
    scope_policy_violation_count: int = 0,
    action_attested_count: int = 0,
    normalized_attested_count: int = 0,
    unresolved_semantic_boundary: bool = False,
    mixed_incompatible_slot_semantics: bool = False,
    no_engineering_value: bool = False,
    high_downstream_misuse_risk: bool = False,
    condition_max_share: float = 0.5,
    fixture_evidence_sufficient_for_gate: bool = True,
) -> dict:
    control_count = total // 2 if control is None else control
    treatment_count = total - control_count if treatment is None else treatment
    rates = adapter_rates or {"control": correct / total, "treatment": correct / total}
    return {
        "scope_key": "synthetic:route:slot",
        "total_attested_count": total,
        "gold_correct_count": correct,
        "correct_rate": correct / total if total else None,
        "wilson_95": wilson_interval(correct, total),
        "high_risk_mismatch_count": high_risk,
        "high_risk_mismatch_rate": high_risk / total if total else None,
        "adapter_role_counts": {"control": control_count, "treatment": treatment_count},
        "adapter_role_correct_rates": rates,
        "adapter_gap": max(rates.values()) - min(rates.values()) if rates else None,
        "technical_false_accept_count": technical_false_accept_count,
        "scope_policy_violation_count": scope_policy_violation_count,
        "action_attested_count": action_attested_count,
        "normalized_attested_count": normalized_attested_count,
        "execution_eligible_count": 0,
        "unresolved_semantic_boundary": unresolved_semantic_boundary,
        "mixed_incompatible_slot_semantics": mixed_incompatible_slot_semantics,
        "no_engineering_value": no_engineering_value,
        "high_downstream_misuse_risk": high_downstream_misuse_risk,
        "condition_max_share": condition_max_share,
        "fixture_evidence_sufficient_for_gate": fixture_evidence_sufficient_for_gate,
        "available_adapter_roles": ["control", "treatment"],
        "policy_v1_enabled": True,
    }


def test_wilson_interval_known_values_and_zero_sample() -> None:
    assert wilson_interval(0, 0) == {"lower": None, "upper": None, "width": None}

    interval = wilson_interval(27, 30)

    assert interval["lower"] == pytest.approx(0.7439, abs=0.0002)
    assert interval["upper"] == pytest.approx(0.9654, abs=0.0002)
    assert interval["width"] == pytest.approx(0.2215, abs=0.0002)
    assert interval["lower"] < 0.75


def test_gate_status_thresholds_are_ordered_and_deterministic() -> None:
    assert compute_gate_status(_metric(total=40, correct=38, high_risk=0)) == "OBSERVE_ENABLED"
    assert compute_gate_status(_metric(total=30, correct=27, high_risk=1)) == "OBSERVE_LIMITED"
    assert compute_gate_status(_metric(total=25, correct=19, high_risk=2)) == "CANDIDATE_ONLY"
    assert compute_gate_status(_metric(total=19, correct=19, high_risk=0)) == "INSUFFICIENT_EVIDENCE"
    assert compute_gate_status(_metric(total=40, correct=39, high_risk=0, control=35, treatment=5)) == (
        "INSUFFICIENT_EVIDENCE"
    )
    assert compute_gate_status(_metric(total=40, correct=39, high_risk=0, condition_max_share=0.95)) == (
        "INSUFFICIENT_EVIDENCE"
    )
    assert compute_gate_status(
        _metric(total=40, correct=39, high_risk=0, fixture_evidence_sufficient_for_gate=False)
    ) == "INSUFFICIENT_EVIDENCE"


def test_gate_status_disables_on_policy_technical_and_semantic_failures() -> None:
    assert compute_gate_status(_metric(total=40, correct=20, high_risk=0)) == "PROPOSE_DISABLE"
    assert compute_gate_status(_metric(total=40, correct=38, high_risk=10)) == "PROPOSE_DISABLE"
    assert compute_gate_status(_metric(total=40, correct=38, technical_false_accept_count=1)) == "PROPOSE_DISABLE"
    assert compute_gate_status(_metric(total=40, correct=38, scope_policy_violation_count=1)) == "PROPOSE_DISABLE"
    assert compute_gate_status(_metric(total=40, correct=38, mixed_incompatible_slot_semantics=True)) == (
        "PROPOSE_DISABLE"
    )
    assert compute_gate_status(_metric(total=40, correct=38, no_engineering_value=True)) == "PROPOSE_DISABLE"
    assert compute_gate_status(_metric(total=40, correct=38, high_downstream_misuse_risk=True)) == "PROPOSE_DISABLE"


def test_small_or_imbalanced_samples_cannot_enable_scope() -> None:
    perfect_three = _metric(total=3, correct=3, high_risk=0, control=0, treatment=3)
    wide_interval = _metric(total=20, correct=15, high_risk=0, control=10, treatment=10)

    assert compute_gate_status(perfect_three) == "INSUFFICIENT_EVIDENCE"
    assert perfect_three["wilson_95"]["lower"] < 0.75
    assert wide_interval["wilson_95"]["width"] > 0.35
    assert compute_gate_status(wide_interval) == "INSUFFICIENT_EVIDENCE"
    assert compute_gate_status(
        _metric(
            total=40,
            correct=38,
            high_risk=0,
            adapter_rates={"control": 1.0, "treatment": 0.70},
        )
    ) == "CANDIDATE_ONLY"


def test_gate_status_is_not_hardcoded_by_scope_key() -> None:
    enabled_metrics = _metric(total=40, correct=38, high_risk=0)
    enabled_metrics["scope_key"] = "unknown_task:unknown_route:unknown_slot"
    disable_metrics = _metric(total=40, correct=20, high_risk=0)
    disable_metrics["scope_key"] = "search:search_web:query"

    assert compute_gate_status(enabled_metrics) == "OBSERVE_ENABLED"
    assert compute_gate_status(disable_metrics) == "PROPOSE_DISABLE"


def test_downward_only_override_validation() -> None:
    override = apply_downward_override(
        "OBSERVE_LIMITED",
        "CANDIDATE_ONLY",
        semantic_reason="partial-span semantic boundary remains unresolved",
        evidence_reference="reports/public-sample/example.json#scope",
        reviewer_required=True,
    )

    assert override["override_direction"] == "downward"
    assert override["original_gate_status"] == "OBSERVE_LIMITED"
    assert override["final_status"] == "CANDIDATE_ONLY"
    assert override["reviewer_required"] is True

    with pytest.raises(ValueError, match="upward"):
        apply_downward_override(
            "CANDIDATE_ONLY",
            "OBSERVE_ENABLED",
            semantic_reason="not allowed",
            evidence_reference="reports/public-sample/example.json#scope",
            reviewer_required=True,
        )


def test_taxonomy_migration_splits_fixture_ambiguity_and_records_attribution() -> None:
    rows = [
        {
            "challenge_id": "canonical",
            "scope_key": "form_fill:fill_form:field",
            "primary_mechanism": "CHALLENGE_FIXTURE_OR_GOLD_AMBIGUITY",
            "condition_tags": ["gold_ambiguous", "normalization_candidate"],
            "predicted_value": "A B",
            "gold_value": "AB",
        },
        {
            "challenge_id": "true-ambiguity",
            "scope_key": "form_fill:fill_form:field",
            "primary_mechanism": "CHALLENGE_FIXTURE_OR_GOLD_AMBIGUITY",
            "condition_tags": ["gold_ambiguous"],
            "predicted_value": "字段甲",
            "gold_value": "字段乙",
        },
    ]

    migrated = migrate_case_ledger_taxonomy(rows)

    assert [row["primary_mechanism"] for row in migrated] == [
        "CANONICAL_STRING_MISMATCH",
        "TRUE_GOLD_OR_FIXTURE_AMBIGUITY",
    ]
    assert {row["attribution_mode"] for row in migrated} == {"fixture_guided"}
    assert migrated[0]["attribution_source"] == "fixture_tag_plus_deterministic_relation"
    assert migrated[0]["condition_tags_used"] == ["gold_ambiguous", "normalization_candidate"]
    assert migrated[0]["deterministic_checks_used"] == ["normalized_value_equivalence"]
    assert migrated[0]["manual_review_required"] is False
    assert migrated[1]["attribution_source"] == "reviewed_fixture_ambiguity"
    assert migrated[1]["manual_review_required"] is True


def test_high_risk_mechanism_set_excludes_downgraded_and_ambiguity_mechanisms() -> None:
    assert HIGH_RISK_MECHANISMS == {
        "WRONG_ENTITY_FROM_SOURCE",
        "SOURCE_ABSENT_SUBSTITUTION",
        "OVERLONG_SOURCE_SPAN",
        "UNDERSPECIFIED_PARTIAL_SPAN",
        "WRONG_SLOT_OR_SCOPE_SELECTION",
        "DUPLICATE_CONTEXT_DISAMBIGUATION_FAILURE",
        "GENERATED_VALUE_MISMATCH",
    }
    assert "NORMALIZATION_EQUIVALENCE_COLLISION" not in HIGH_RISK_MECHANISMS
    assert "CANONICAL_STRING_MISMATCH" not in HIGH_RISK_MECHANISMS
    assert "TRUE_GOLD_OR_FIXTURE_AMBIGUITY" not in HIGH_RISK_MECHANISMS


def test_compute_scope_metrics_from_committed_artifacts_post_hardening() -> None:
    audits = _read_jsonl(
        REPO_ROOT
        / "reports/public-sample/copy-shadow-template-disjoint-challenge-v1/adapter-evaluation/evaluation-audits.jsonl"
    )
    ledger = migrate_case_ledger_taxonomy(_read_jsonl(DIAGNOSIS_DIR / "false-trust-case-ledger.jsonl"))
    policy = read_json(POLICY_V1_PATH)

    metrics = compute_scope_metrics(
        audits=audits,
        migrated_ledger=ledger,
        policy=policy,
        technical_gate_counts={
            "action_trusted_count": 0,
            "normalized_trusted_count": 0,
            "provenance_false_accept_count": 0,
            "scope_policy_violation_count": 0,
        },
    )

    search = metrics["search:search_web:query"]
    form = metrics["form_fill:fill_form:field"]
    extract = metrics["extract:extract_page:target"]
    assert search["total_attested_count"] == 30
    assert search["correct_rate"] == pytest.approx(0.9)
    assert search["wilson_95"]["lower"] < 0.75
    assert search["high_risk_mismatch_count"] == 3
    assert search["condition_max_share"] == pytest.approx(1.0)
    assert search["evidence_condition_tag_distribution"] == {"partial_span_trap": 3}
    assert form["total_attested_count"] == 31
    assert form["high_risk_mismatch_count"] == 5
    assert form["canonical_string_mismatch_count"] == 3
    assert form["condition_max_share"] == pytest.approx(6 / 13)
    assert form["evidence_condition_tag_distribution"] == {
        "multiple_entity_distractor": 1,
        "normalization_candidate": 3,
        "normalization_collision": 6,
        "source_absent": 3,
    }
    assert extract["total_attested_count"] == 3
    assert extract["adapter_role_counts"] == {"treatment": 3}
    assert extract["evidence_sufficiency"]["only_one_adapter_role"] is True
    assert all(row["policy_v1_enabled"] is True for row in metrics.values())
    assert all(row["policy_gate_deterministic"] is True for row in metrics.values())
    assert all(row["attribution_mode"] == "fixture_guided" for row in metrics.values())
    assert all(row["fixture_independent_evidence"] is False for row in metrics.values())
    assert all("fixture_evidence_independent" not in row for row in metrics.values())


def test_run_design_recomputes_committed_policy_v2_scope_decisions_without_mutating_v1() -> None:
    before_policy = POLICY_V1_PATH.read_text(encoding="utf-8")
    result = run_copy_shadow_scope_policy_design(REPO_ROOT)
    after_policy = POLICY_V1_PATH.read_text(encoding="utf-8")

    assert before_policy == after_policy
    assert result["summary"]["decision_label"] == DECISION_SCOPE_REDUCTION_READY
    assert result["summary"]["recommended_next_change"] == (
        "review-and-freeze-copy-shadow-policy-v2-before-naturalistic-challenge"
    )
    assert result["summary"]["challenge_hash"] == EXPECTED_CHALLENGE_HASH
    assert result["summary"]["source_policy_v1_hash"] == EXPECTED_POLICY_HASH
    assert result["summary"]["technical_false_accept_count"] == 0
    assert result["summary"]["action_attested_count"] == 0
    assert result["summary"]["normalized_attested_count"] == 0
    assert result["summary"]["execution_eligible_count"] == 0
    assert result["scope_decisions"]["form_fill:fill_form:field"]["final_status"] == "PROPOSE_DISABLE"
    assert result["scope_decisions"]["search:search_web:query"]["final_status"] == "INSUFFICIENT_EVIDENCE"
    assert result["scope_decisions"]["extract:extract_page:target"]["final_status"] == "INSUFFICIENT_EVIDENCE"
    assert result["scope_decisions"]["extract:extract_page:target"]["original_gate_status"] == (
        "INSUFFICIENT_EVIDENCE"
    )
    assert all(decision["reviewer_required"] is True for decision in result["scope_decisions"].values())


def test_write_design_report_bundle_and_inactive_policy(tmp_path: Path) -> None:
    output_dir = tmp_path / "policy-v2-design"
    proposed_policy_path = tmp_path / "copy-backed-scope-policy-v2.proposed.json"
    output_dir.mkdir()
    (output_dir / "unexpected-stale.json").write_text("{}\n", encoding="utf-8")

    result = write_copy_shadow_scope_policy_design_report(
        REPO_ROOT,
        output_dir=output_dir,
        proposed_policy_path=proposed_policy_path,
    )

    assert result["summary"]["decision_label"] == DECISION_SCOPE_REDUCTION_READY
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "gate-config.json",
        "post-hardening-scope-metrics.json",
        "recommended-next-change.md",
        "scope-decisions.json",
        "summary.json",
        "summary.md",
        "taxonomy-migration.json",
    ]
    proposed = json.loads(proposed_policy_path.read_text(encoding="utf-8"))
    assert proposed["status"] == "proposal"
    assert proposed["active"] is False
    assert proposed["runtime_loaded"] is False
    assert proposed["enforcement_enabled"] is False
    assert proposed["source_policy_v1_id"] == "copy-backed-scope-policy-v1"
    assert proposed["source_policy_v1_hash"] == EXPECTED_POLICY_HASH
    assert proposed["challenge_v1_hash"] == EXPECTED_CHALLENGE_HASH
    assert proposed["decision_gate_version"] == "copy-shadow-scope-policy-v2-gates-2026-06-24"
    assert proposed["scopes"]["form_fill:fill_form:field"]["final_status"] == "PROPOSE_DISABLE"
    assert all(scope["reviewer_required"] is True for scope in proposed["scopes"].values())
    assert scan_paths([output_dir, proposed_policy_path]).ok


def test_blocked_report_removes_stale_proposed_policy(tmp_path: Path) -> None:
    output_dir = tmp_path / "policy-v2-design"
    proposed_policy_path = tmp_path / "copy-backed-scope-policy-v2.proposed.json"
    proposed_policy_path.write_text('{"stale": true}\n', encoding="utf-8")

    result = write_copy_shadow_scope_policy_design_report(
        REPO_ROOT,
        output_dir=output_dir,
        proposed_policy_path=proposed_policy_path,
        expected_challenge_hash="bad-hash",
    )

    assert result["summary"]["decision_label"] == "POLICY_V2_DESIGN_BLOCKED_INVALID_INPUT"
    assert sorted(path.name for path in output_dir.iterdir()) == ["blocked.json"]
    assert not proposed_policy_path.exists()


def test_committed_policy_v2_design_artifacts_are_current_and_review_only() -> None:
    summary = read_json(DESIGN_DIR / "summary.json")
    proposed = read_json(POLICY_V2_PROPOSED_PATH)
    policy_v1 = read_json(POLICY_V1_PATH)

    assert summary["decision_label"] == DECISION_SCOPE_REDUCTION_READY
    assert summary["scope_status_counts"]["PROPOSE_DISABLE"] >= 1
    assert proposed["status"] == "proposal"
    assert proposed["active"] is False
    assert proposed["runtime_loaded"] is False
    assert proposed["enforcement_enabled"] is False
    assert proposed["source_policy_v1_hash"] == compute_policy_hash(policy_v1)
    assert all(scope["reviewer_required"] is True for scope in proposed["scopes"].values())
    assert proposed["scopes"]["search:search_web:query"]["final_status"] == "INSUFFICIENT_EVIDENCE"
    assert proposed["scopes"]["search:search_web:query"]["metrics"]["condition_max_share"] == pytest.approx(1.0)
    assert "fixture_evidence_independent" not in proposed["scopes"]["search:search_web:query"]["metrics"]
    assert summary["claims"] == {
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
    assert scan_paths([DESIGN_DIR, POLICY_V2_PROPOSED_PATH, REPO_ROOT / "docs/copy-shadow-scope-policy-v2.md"]).ok


def test_policy_v2_review_doc_explains_gate_and_scope_decisions() -> None:
    text = (REPO_ROOT / "docs/copy-shadow-scope-policy-v2.md").read_text(encoding="utf-8")

    for required in (
        "Gate order",
        "Wilson interval",
        "Sample support",
        "Adapter consistency",
        "Fixture-guided attribution",
        "Downward-only override",
        "Why these scope statuses",
        "Runtime boundary",
        "form_fill:fill_form:field",
        "search:search_web:query",
        "extract:extract_page:target",
        "runtime_loaded=false",
    ):
        assert required in text
