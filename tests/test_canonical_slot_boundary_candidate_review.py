import json
import subprocess
from pathlib import Path

from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPORT_DIR = REPO_ROOT / "reports" / "public-sample" / "canonical-slot-boundary-candidates"
REVIEW_DIR = REPO_ROOT / "reports" / "public-sample" / "canonical-slot-boundary-candidate-review"
HUMAN_BRIEF = (
    REPO_ROOT
    / "docs"
    / "human-briefs"
    / "2026-06-18-review-canonical-slot-boundary-candidates-before-merge.html"
)

SOURCE_SUMMARY_JSON = SOURCE_REPORT_DIR / "summary.json"
SUMMARY_JSON = REVIEW_DIR / "summary.json"
SUMMARY_MD = REVIEW_DIR / "summary.md"
LEAK_SCAN_RESULT = REVIEW_DIR / "leak_scan_result.json"

EXPECTED_CLASSIFICATIONS = {
    "slot_key_aliases": "eligible_for_later_formal_merge_proposal",
    "slot_value_boundaries": "eligible_for_later_formal_merge_proposal",
    "normalized_command_display_diagnostic": "diagnostic_display_only",
    "excluded_non_equivalence_cases": "blocked_or_deferred_non_equivalence",
}

REQUIRED_BLOCKED_OPERATIONS = {
    "formal_public_sample_merge_now",
    "jsonl_seed_candidate_generation",
    "sft_or_dpo_row_generation",
    "manifest_rebuild",
    "split_change",
    "evaluator_definition_change",
    "prediction_run",
    "training_run",
    "a100_job",
    "postprocessor_implementation",
    "strict_exact_relaxation",
    "llm_judge",
    "semantic_equivalence_scoring",
    "prediction_repair",
    "model_quality_claim",
}

REQUIRED_EXCLUDED_CASES = {
    "date_today_vs_tomorrow",
    "city_origin_vs_destination",
    "product_name_change",
    "url_host_change",
    "price_amount_change",
    "product_name_vs_query",
    "location_vs_destination",
    "action_vs_reason",
}

PROTECTED_PATHS = [
    "data/public-samples/seed_traces.jsonl",
    "data/public-samples/sft_public_sample.jsonl",
    "data/public-samples/dpo_public_sample.jsonl",
    "data/public-samples/manifest_public_sample.json",
    "reports/public-sample/canonical-slot-boundary-candidates",
    "openspec/changes/merge-scaled-clarify-slot-boundary-candidates",
]
STILL_PROTECTED_AFTER_FORMAL_MERGE_PATHS = [
    "reports/public-sample/canonical-slot-boundary-candidates",
]


def _review_summary() -> dict:
    return json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))


def test_review_artifacts_exist_and_trace_to_source_materialization() -> None:
    assert SUMMARY_JSON.exists()
    assert SUMMARY_MD.exists()
    assert LEAK_SCAN_RESULT.exists()
    assert HUMAN_BRIEF.exists()

    review = _review_summary()
    source = json.loads(SOURCE_SUMMARY_JSON.read_text(encoding="utf-8"))
    assert review["evidence_kind"] == "canonical_slot_boundary_candidate_review"
    assert review["review_mode"] == "public_safe_review_only_no_data_or_training"
    assert review["source_candidate_materialization"] == {
        "artifact": "reports/public-sample/canonical-slot-boundary-candidates/summary.json",
        "evidence_kind": source["evidence_kind"],
        "accepted_candidate_count": source["summary"]["accepted_candidate_count"],
        "excluded_non_equivalence_count": source["summary"]["excluded_non_equivalence_count"],
        "formal_public_sample_status": source["summary"]["formal_public_sample_status"],
    }

    report = SUMMARY_MD.read_text(encoding="utf-8")
    assert "review-only" in report
    assert "not formal merge approval" in report
    assert "propose-canonical-slot-boundary-formal-merge-after-review" in report


def test_candidate_classes_are_reviewed_without_immediate_merge_approval() -> None:
    reviews = {
        item["candidate_group"]: item
        for item in _review_summary()["candidate_class_reviews"]
    }
    assert reviews.keys() == EXPECTED_CLASSIFICATIONS.keys()

    for group, expected_classification in EXPECTED_CLASSIFICATIONS.items():
        decision = reviews[group]
        assert decision["review_classification"] == expected_classification
        assert decision["approved_for_formal_merge_now"] is False
        assert decision["requires_separate_openspec_change"] is True
        assert decision["allowed_later_operation"] == "bounded_openspec_proposal_only"
        assert REQUIRED_BLOCKED_OPERATIONS.issubset(set(decision["blocked_operations"]))

    assert reviews["slot_key_aliases"]["representative_candidate_ids"] == [
        "slot-key-alias-search-text-query",
        "slot-key-alias-site-url",
        "slot-key-alias-field-value",
    ]
    assert reviews["slot_value_boundaries"]["representative_candidate_ids"] == [
        "slot-value-boundary-whitespace-trim",
        "slot-value-boundary-fullwidth-punctuation",
        "slot-value-boundary-filler-removal",
        "slot-value-boundary-url-email-casing",
    ]


def test_normalized_command_and_non_equivalence_boundaries_stay_blocked() -> None:
    reviews = {
        item["candidate_group"]: item
        for item in _review_summary()["candidate_class_reviews"]
    }

    normalized = reviews["normalized_command_display_diagnostic"]
    assert normalized["declares_equivalence"] is False
    assert normalized["alters_strict_exact"] is False
    assert normalized["alters_executable_contract_pass_conditions"] is False
    assert normalized["rescores_prior_residuals"] is False
    assert normalized["repairs_predictions"] is False
    assert normalized["representative_candidate_ids"] == [
        "normalized-command-display-search-template",
        "normalized-command-display-safety-template",
    ]

    excluded = reviews["excluded_non_equivalence_cases"]
    assert set(excluded["representative_case_ids"]) == REQUIRED_EXCLUDED_CASES
    assert set(excluded["preserved_non_equivalence_boundaries"]) == {
        "date",
        "city_or_location",
        "product",
        "url_host",
        "price_or_amount",
        "query_or_product",
        "location_or_destination",
        "action_or_reason",
    }
    assert excluded["loosen_slot_value_policy"] is False


def test_review_execution_scope_records_no_data_training_or_evaluator_changes() -> None:
    review = _review_summary()
    scope = review["execution_scope"]
    assert scope["review_only"] is True
    for flag in (
        "formal_public_sample_data_mutation",
        "jsonl_seed_candidates_generated",
        "sft_or_dpo_rows_generated",
        "manifest_rebuilt",
        "split_change",
        "evaluator_definition_change",
        "prediction_run",
        "training_run",
        "a100_job",
        "deterministic_postprocessor_implemented",
        "strict_exact_relaxation",
        "llm_judge",
        "semantic_equivalence_scoring",
        "prediction_repair",
        "checkpoint_or_adapter_release",
    ):
        assert scope[flag] is False

    claims = review["claims"]
    assert claims["review_evidence_only"] is True
    assert claims["formal_merge_approval_claim"] is False
    assert claims["model_improvement_claim"] is False
    assert claims["held_out_recovery_claim"] is False
    assert claims["production_readiness_claim"] is False
    assert claims["safety_readiness_claim"] is False
    assert claims["live_browser_benchmark_improvement_claim"] is False

    assert review["recommended_next_step"] == {
        "proposed_change_id": "propose-canonical-slot-boundary-formal-merge-after-review",
        "operation": "later_bounded_openspec_proposal_only",
        "implemented_now": False,
    }


def test_protected_formal_data_are_not_modified() -> None:
    result = subprocess.run(
        ["git", "status", "--short", "--", *STILL_PROTECTED_AFTER_FORMAL_MERGE_PATHS],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stdout == ""


def test_review_artifacts_and_human_brief_are_leak_scan_clean() -> None:
    result = scan_paths([REVIEW_DIR, HUMAN_BRIEF])
    assert result.ok is True
    assert result.findings == []

    recorded = json.loads(LEAK_SCAN_RESULT.read_text(encoding="utf-8"))
    assert recorded["ok"] is True
    assert recorded["findings"] == []
