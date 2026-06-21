import json
import subprocess
from pathlib import Path

from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports" / "public-sample" / "canonical-slot-boundary-candidates"
SOURCE_POLICY_DIR = REPO_ROOT / "reports" / "public-sample" / "slot-canonicalization-policy"
HUMAN_BRIEF = (
    REPO_ROOT
    / "docs"
    / "human-briefs"
    / "2026-06-18-materialize-canonical-slot-boundary-candidates.html"
)

SUMMARY_JSON = REPORT_DIR / "summary.json"
SUMMARY_MD = REPORT_DIR / "summary.md"
LEAK_SCAN_RESULT = REPORT_DIR / "leak_scan_result.json"

REQUIRED_CANDIDATE_FIELDS = {
    "candidate_id",
    "candidate_group",
    "source_policy_file",
    "source_policy_section",
    "task_type",
    "input_slot_sketch",
    "canonical_slot_sketch",
    "rationale",
    "review_status",
    "later_allowed_operation",
    "strict_exact_impact",
    "formal_public_sample_status",
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
    "reports/public-sample/slot-canonicalization-policy",
]


def _summary() -> dict:
    return json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))


def test_candidate_materialization_summary_has_required_boundary_metadata() -> None:
    assert SUMMARY_JSON.exists()
    assert SUMMARY_MD.exists()
    assert LEAK_SCAN_RESULT.exists()
    assert HUMAN_BRIEF.exists()

    summary = _summary()
    assert summary["evidence_kind"] == "canonical_slot_boundary_candidate_materialization"
    assert summary["materialization_status"] == "standalone_candidate_examples_materialized"
    assert summary["source_policy_dir"] == "reports/public-sample/slot-canonicalization-policy"
    assert SOURCE_POLICY_DIR.exists()
    assert summary["source_manifest_id"] == "public-sample-20260617T152259Z"

    scope = summary["execution_scope"]
    assert scope["hard_boundary"] is True
    for flag in (
        "formal_public_sample_data_mutation",
        "sft_or_dpo_rows_added",
        "manifest_rebuilt",
        "split_change",
        "evaluator_definition_change",
        "evaluator_metric_change",
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

    claims = summary["claims"]
    assert claims["model_improvement_claim"] is False
    assert claims["held_out_recovery_claim"] is False
    assert claims["production_readiness_claim"] is False
    assert claims["safety_readiness_claim"] is False
    assert claims["live_browser_benchmark_improvement_claim"] is False


def test_accepted_candidates_cover_required_groups_and_schema() -> None:
    candidates = _summary()["accepted_candidates"]
    assert candidates
    groups = {candidate["candidate_group"] for candidate in candidates}
    assert {
        "slot_key_aliases",
        "slot_value_boundaries",
        "normalized_command_display_diagnostic",
    }.issubset(groups)

    for candidate in candidates:
        assert REQUIRED_CANDIDATE_FIELDS.issubset(candidate)
        assert candidate["review_status"] == "report_local_candidate_only"
        assert candidate["formal_public_sample_status"] == "not_added"

    key_alias_ids = {candidate["candidate_id"] for candidate in candidates}
    assert {
        "slot-key-alias-search-text-query",
        "slot-key-alias-site-url",
        "slot-key-alias-field-value",
    }.issubset(key_alias_ids)


def test_excluded_non_equivalence_cases_are_not_accepted_candidates() -> None:
    summary = _summary()
    excluded = summary["excluded_non_equivalence_examples"]
    excluded_ids = {example["case_id"] for example in excluded}
    assert REQUIRED_EXCLUDED_CASES.issubset(excluded_ids)
    assert all(example["merge_allowed"] is False for example in excluded)
    assert all(example["formal_public_sample_status"] == "not_added" for example in excluded)

    accepted_ids = {candidate["candidate_id"] for candidate in summary["accepted_candidates"]}
    assert accepted_ids.isdisjoint(REQUIRED_EXCLUDED_CASES)
    accepted_rationales = json.dumps(summary["accepted_candidates"], ensure_ascii=False)
    for case_id in REQUIRED_EXCLUDED_CASES:
        assert case_id not in accepted_rationales


def test_normalized_command_candidates_are_diagnostic_display_only() -> None:
    normalized = [
        candidate
        for candidate in _summary()["accepted_candidates"]
        if candidate["candidate_group"] == "normalized_command_display_diagnostic"
    ]
    assert normalized
    for candidate in normalized:
        assert candidate["task_type"] == "diagnostic_display"
        assert candidate["strict_exact_impact"] == "none"
        assert candidate["later_allowed_operation"] == "display_template_review_only"
        assert candidate["declares_equivalence"] is False
        assert candidate["rescore_prior_residuals"] is False
        assert candidate["repair_prediction"] is False


def test_protected_formal_data_are_not_modified() -> None:
    result = subprocess.run(
        ["git", "status", "--short", "--", *PROTECTED_PATHS],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stdout == ""


def test_materialized_report_and_human_brief_are_leak_scan_clean() -> None:
    result = scan_paths([REPORT_DIR, HUMAN_BRIEF])
    assert result.ok is True
    assert result.findings == []

    recorded = json.loads(LEAK_SCAN_RESULT.read_text(encoding="utf-8"))
    assert recorded["ok"] is True
    assert recorded["findings"] == []
