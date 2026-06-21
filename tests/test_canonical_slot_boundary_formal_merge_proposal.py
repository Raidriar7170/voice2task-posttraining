import json
import subprocess
from pathlib import Path

from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVIEW_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "canonical-slot-boundary-candidate-review"
)
SOURCE_MATERIALIZATION_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "canonical-slot-boundary-candidates"
)
REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "canonical-slot-boundary-formal-merge-proposal"
)
HUMAN_BRIEF = (
    REPO_ROOT
    / "docs"
    / "human-briefs"
    / "2026-06-19-propose-canonical-slot-boundary-formal-merge-after-review.html"
)

SOURCE_REVIEW_JSON = SOURCE_REVIEW_DIR / "summary.json"
SUMMARY_JSON = REPORT_DIR / "summary.json"
SUMMARY_MD = REPORT_DIR / "summary.md"
LEAK_SCAN_RESULT = REPORT_DIR / "leak_scan_result.json"
REQUIRED_FUTURE_SOURCE_ARTIFACT = (
    REPO_ROOT / "data" / "public-samples" / "canonical_slot_boundary_seed_candidates.jsonl"
)

ELIGIBLE_FUTURE_CLASSES = ["slot_key_aliases", "slot_value_boundaries"]
EXCLUDED_FUTURE_CLASSES = [
    "normalized_command_display_diagnostic",
    "excluded_non_equivalence_cases",
]
REQUIRED_ACCEPTANCE_CRITERIA = {
    "exact_reviewed_row_level_candidate_source",
    "public_safe_validation",
    "duplicate_source_id_validation",
    "derived_sft_dpo_manifest_synchronization",
    "split_boundary_accounting",
    "comparison_boundary_warning",
    "strict_exact_and_strict_slot_f1_authoritative",
    "slot_f1_soft_diagnostic_only",
}
REQUIRED_BLOCKED_OPERATIONS = {
    "formal_public_sample_data_mutation",
    "jsonl_seed_candidate_generation",
    "sft_or_dpo_row_generation",
    "manifest_rebuild",
    "split_change",
    "evaluator_definition_change",
    "prediction_run",
    "training_run",
    "a100_job",
    "deterministic_postprocessor_implementation",
    "strict_exact_relaxation",
    "llm_judge",
    "semantic_equivalence_scoring",
    "prediction_repair",
    "checkpoint_or_adapter_release",
    "model_quality_claim",
}
PROTECTED_PATHS = [
    "data/public-samples/seed_traces.jsonl",
    "data/public-samples/sft_public_sample.jsonl",
    "data/public-samples/dpo_public_sample.jsonl",
    "data/public-samples/manifest_public_sample.json",
    "reports/public-sample/canonical-slot-boundary-candidate-review",
    "reports/public-sample/canonical-slot-boundary-candidates",
    "openspec/changes/merge-scaled-clarify-slot-boundary-candidates",
    "src/voice2task",
]
STILL_PROTECTED_AFTER_FORMAL_MERGE_PATHS = [
    "reports/public-sample/canonical-slot-boundary-candidate-review",
    "reports/public-sample/canonical-slot-boundary-candidates",
]


def _proposal_summary() -> dict:
    assert SUMMARY_JSON.exists()
    return json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))


def test_formal_merge_proposal_artifacts_exist_and_fail_closed_without_rows() -> None:
    assert SOURCE_REVIEW_JSON.exists()
    assert SUMMARY_JSON.exists()
    assert SUMMARY_MD.exists()
    assert LEAK_SCAN_RESULT.exists()
    assert HUMAN_BRIEF.exists()

    proposal = _proposal_summary()
    source = json.loads(SOURCE_REVIEW_JSON.read_text(encoding="utf-8"))
    assert proposal["evidence_kind"] == "canonical_slot_boundary_formal_merge_proposal"
    assert proposal["source_review"] == {
        "artifact": "reports/public-sample/canonical-slot-boundary-candidate-review/summary.json",
        "evidence_kind": source["evidence_kind"],
        "review_status": source["review_status"],
        "eligible_for_later_formal_merge_proposal_count": source["summary"][
            "eligible_for_later_formal_merge_proposal_count"
        ],
    }
    assert proposal["formal_merge_ready_now"] is False
    assert (
        proposal["formal_merge_readiness"]
        == "not_ready_missing_row_level_candidate_source"
    )
    assert proposal["implemented_now"] is False
    assert proposal["formal_public_sample_modified"] is False
    assert (
        proposal["required_future_source_artifact"]
        == "data/public-samples/canonical_slot_boundary_seed_candidates.jsonl"
    )
    # A later bounded materialization phase may create this source; the proposal
    # itself remains readiness-only and non-implementing.
    if REQUIRED_FUTURE_SOURCE_ARTIFACT.exists():
        source_text = REQUIRED_FUTURE_SOURCE_ARTIFACT.read_text(encoding="utf-8")
        assert "standalone_not_formal_public_sample" in source_text


def test_future_merge_scope_keeps_only_reviewed_equivalence_like_classes() -> None:
    proposal = _proposal_summary()
    assert proposal["eligible_future_merge_classes"] == ELIGIBLE_FUTURE_CLASSES
    assert proposal["excluded_from_future_formal_merge"] == EXCLUDED_FUTURE_CLASSES

    normalized = proposal["excluded_class_rationales"][
        "normalized_command_display_diagnostic"
    ]
    assert normalized["future_formal_merge_allowed"] is False
    assert normalized["classification"] == "diagnostic_display_only"
    assert normalized["alters_strict_exact"] is False
    assert normalized["repairs_predictions"] is False

    non_equivalence = proposal["excluded_class_rationales"][
        "excluded_non_equivalence_cases"
    ]
    assert non_equivalence["future_formal_merge_allowed"] is False
    assert non_equivalence["classification"] == "blocked_or_deferred_non_equivalence"
    assert non_equivalence["loosen_slot_value_policy"] is False


def test_future_acceptance_criteria_and_metric_boundaries_are_explicit() -> None:
    proposal = _proposal_summary()
    criteria_ids = {item["id"] for item in proposal["future_acceptance_criteria"]}
    assert REQUIRED_ACCEPTANCE_CRITERIA.issubset(criteria_ids)
    assert proposal["comparison_boundary"] == {
        "required_for_future_merge": True,
        "warning": "old_metrics_cannot_be_compared_directly_after_formal_sample_boundary_change",
    }
    assert proposal["metric_boundary"] == {
        "contract_exact_match": "authoritative_strict_metric",
        "slot_f1": "authoritative_strict_metric",
        "slot_f1_soft": "diagnostic_only_not_recovery_or_equivalence_evidence",
    }

    next_step = proposal["recommended_next_bounded_step"]
    assert next_step["operation"] == "materialize_exact_row_level_candidate_source"
    assert next_step["target_artifact"] == (
        "data/public-samples/canonical_slot_boundary_seed_candidates.jsonl"
    )
    assert next_step["direct_formal_merge"] is False


def test_execution_scope_blocks_data_training_evaluator_and_claim_changes() -> None:
    proposal = _proposal_summary()
    scope = proposal["execution_scope"]
    assert scope["proposal_readiness_only"] is True
    assert set(scope["blocked_operations"]) == REQUIRED_BLOCKED_OPERATIONS
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

    claims = proposal["claims"]
    assert claims["proposal_readiness_evidence_only"] is True
    assert claims["formal_merge_approval_claim"] is False
    assert claims["model_improvement_claim"] is False
    assert claims["held_out_recovery_claim"] is False
    assert claims["production_readiness_claim"] is False
    assert claims["safety_readiness_claim"] is False
    assert claims["live_browser_benchmark_improvement_claim"] is False


def test_protected_sources_and_formal_data_are_not_modified() -> None:
    result = subprocess.run(
        ["git", "status", "--short", "--", *STILL_PROTECTED_AFTER_FORMAL_MERGE_PATHS],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stdout == ""


def test_proposal_artifacts_markdown_human_brief_and_leak_scan_are_public_safe() -> None:
    proposal = _proposal_summary()
    proposal_protected_paths = set(proposal["protected_paths_not_modified"])
    assert set(PROTECTED_PATHS).issubset(proposal_protected_paths)
    assert "data/public-samples/canonical_slot_boundary_seed_candidates.jsonl" in proposal_protected_paths

    report = SUMMARY_MD.read_text(encoding="utf-8")
    assert "not_ready_missing_row_level_candidate_source" in report
    assert "data/public-samples/canonical_slot_boundary_seed_candidates.jsonl" in report
    assert "not a direct formal merge" in report
    assert "slot_f1_soft" in report
    assert "diagnostic only" in report

    result = scan_paths([REPORT_DIR, HUMAN_BRIEF])
    assert result.ok is True
    assert result.findings == []

    recorded = json.loads(LEAK_SCAN_RESULT.read_text(encoding="utf-8"))
    assert recorded["ok"] is True
    assert recorded["findings"] == []
