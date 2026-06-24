from __future__ import annotations

import json
from pathlib import Path

from voice2task.copy_shadow_false_trust_diagnosis import (
    DECISION_BLOCKED_INVALID_INPUT,
    DECISION_SCOPE_REDUCTION_REQUIRED,
    classify_mismatch_mechanism,
    run_copy_shadow_false_trust_diagnosis,
    write_copy_shadow_false_trust_diagnosis_report,
)
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_diagnosis_recomputes_committed_false_trust_boundary() -> None:
    diagnosis = run_copy_shadow_false_trust_diagnosis(REPO_ROOT)
    summary = diagnosis["summary"]
    boundary = diagnosis["input_boundary"]

    assert summary["decision_label"] == DECISION_SCOPE_REDUCTION_REQUIRED
    assert summary["execution_eligible_count"] == 0
    assert summary["historical_trusted_provenance_alias"] == "deprecated_compatibility_input_only"
    assert summary["online_semantic_correctness"] == "unknown"
    assert summary["source_attested_exact_input_count"] == 64
    assert summary["source_attested_gold_correct_count"] == 48
    assert summary["source_attested_gold_mismatch_count"] == 16
    assert summary["normalization_collision_downgrade_count"] == 6
    assert summary["post_diagnosis_source_attested_exact_count"] == 58
    assert summary["recommended_next_change"] == "design-copy-shadow-scope-policy-v2"
    assert diagnosis["normalization_collision_audit"]["raw_exact_source_attested_events_checked"] == 64
    assert diagnosis["normalization_collision_audit"]["downgrade_count"] == 6

    assert boundary["ok"] is True
    assert boundary["challenge_hash"] == "12eccdd54b2c89f1127ec23f18d7179e1ebaacb1a644ae5ca1a14b3309f11324"
    assert boundary["policy_hash"] == "5dc14efb8ded13dc048ddb067c7c63a1a62b6c03896950e861303973d505cbc7"
    assert boundary["adapter_identity_status"] == "verified"
    assert boundary["prediction_output_invariance_proven"] is True
    assert boundary["v1_metric_delta_zero"] is True
    assert boundary["action_trusted_count"] == 0
    assert boundary["normalized_trusted_count"] == 0

    assert len(diagnosis["case_ledger"]) == 16
    assert sum(1 for row in diagnosis["case_ledger"] if not row["source_attested_exact"]) == 6
    assert {row["primary_mechanism"] for row in diagnosis["case_ledger"]} >= {
        "SOURCE_ABSENT_SUBSTITUTION",
        "NORMALIZATION_EQUIVALENCE_COLLISION",
        "OVERLONG_SOURCE_SPAN",
    }
    assert diagnosis["per_scope_risk_review"]["form_fill:fill_form:field"]["gold_mismatch_count"] == 13
    assert diagnosis["per_scope_risk_review"]["search:search_web:query"]["gold_mismatch_count"] == 3
    assert diagnosis["per_scope_risk_review"]["extract:extract_page:target"]["gold_mismatch_count"] == 0


def test_invalid_input_boundary_writes_blocked_report(tmp_path: Path) -> None:
    result = write_copy_shadow_false_trust_diagnosis_report(
        REPO_ROOT,
        tmp_path / "diagnosis",
        expected_challenge_hash="bad-hash",
    )

    blocked = json.loads((tmp_path / "diagnosis" / "blocked.json").read_text(encoding="utf-8"))
    assert result["summary"]["decision_label"] == DECISION_BLOCKED_INVALID_INPUT
    assert blocked["decision"] == DECISION_BLOCKED_INVALID_INPUT
    assert blocked["training_run"] is False
    assert blocked["prediction_rerun"] is False
    assert blocked["historical_artifacts_modified"] is False
    assert sorted(path.name for path in (tmp_path / "diagnosis").iterdir()) == ["blocked.json"]


def test_diagnosis_report_writes_bounded_public_safe_bundle(tmp_path: Path) -> None:
    output_dir = tmp_path / "diagnosis"

    result = write_copy_shadow_false_trust_diagnosis_report(REPO_ROOT, output_dir)

    assert result["summary"]["decision_label"] == DECISION_SCOPE_REDUCTION_REQUIRED
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "false-trust-case-ledger.jsonl",
        "normalization-collision-audit.json",
        "per-scope-risk-review.json",
        "recommended-next-change.md",
        "sidecar-v2-semantics.md",
        "summary.json",
        "summary.md",
    ]
    assert "source_attested_exact" in (output_dir / "sidecar-v2-semantics.md").read_text(encoding="utf-8")
    assert "design-copy-shadow-scope-policy-v2" in (output_dir / "recommended-next-change.md").read_text(
        encoding="utf-8"
    )
    ledger_lines = (output_dir / "false-trust-case-ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(ledger_lines) == 16
    assert all(json.loads(line)["execution_eligible"] is False for line in ledger_lines)
    assert scan_paths([output_dir]).ok


def test_mechanism_classifier_covers_supported_taxonomy() -> None:
    cases = [
        (["source_absent"], "foo", "bar", "foo only", "field", "SOURCE_ABSENT_SUBSTITUTION"),
        (["normalization_collision"], "A-B", "AB", "A B and A-B", "field", "NORMALIZATION_EQUIVALENCE_COLLISION"),
        (["partial_span_trap"], "topic extended", "topic", "topic extended", "query", "OVERLONG_SOURCE_SPAN"),
        ([], "topic", "topic extended", "topic extended", "query", "UNDERSPECIFIED_PARTIAL_SPAN"),
        (["wrong_scope"], "foo", "bar", "foo", "action", "WRONG_SLOT_OR_SCOPE"),
        (["duplicate_exact"], "foo", "bar", "foo and foo", "field", "DUPLICATE_CONTEXT_DISAMBIGUATION_FAILURE"),
        ([], "foo", "bar", "foo", "field", "GENERATED_VALUE_MISMATCH"),
        (["gold_ambiguous"], "A B", "AB", "A B", "field", "CHALLENGE_FIXTURE_OR_GOLD_AMBIGUITY"),
        (["span_attestation_failure"], "foo", "bar", "foo", "field", "TECHNICAL_SPAN_ATTESTATION_FAILURE"),
        ([], None, "bar", "foo", "field", "UNCLASSIFIED_SEMANTIC_MISMATCH"),
    ]

    for tags, predicted, gold, source_text, slot_path, expected in cases:
        result = classify_mismatch_mechanism(
            condition_tags=tags,
            predicted_value=predicted,
            gold_value=gold,
            source_text=source_text,
            slot_path=slot_path,
            normalized_collision=False,
            span_attested=True,
        )

        assert result["primary_mechanism"] == expected
