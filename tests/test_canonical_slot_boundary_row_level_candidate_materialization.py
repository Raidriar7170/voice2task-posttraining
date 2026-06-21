import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from voice2task.leak_scan import scan_paths
from voice2task.schemas import SFTDatasetRow

REPO_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_SOURCE = (
    REPO_ROOT / "data" / "public-samples" / "canonical_slot_boundary_seed_candidates.jsonl"
)
REPORT_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "canonical-slot-boundary-row-level-candidates"
)
SFT_PREVIEW = REPORT_DIR / "sft_candidate_rows.jsonl"
EVIDENCE_JSON = REPORT_DIR / "canonical_slot_boundary_row_level_candidate_materialization.json"
EVIDENCE_MD = REPORT_DIR / "canonical_slot_boundary_row_level_candidate_materialization.md"
MANIFEST = REPORT_DIR / "manifest.json"
LEAK_SCAN_RESULT = REPORT_DIR / "leak_scan_result.json"
HUMAN_BRIEF = (
    REPO_ROOT
    / "docs"
    / "human-briefs"
    / "2026-06-19-materialize-canonical-slot-boundary-row-level-candidates.html"
)

EXPECTED_SOURCE_CANDIDATE_IDS = {
    "slot-key-alias-search-text-query",
    "slot-key-alias-site-url",
    "slot-key-alias-field-value",
    "slot-value-boundary-whitespace-trim",
    "slot-value-boundary-fullwidth-punctuation",
    "slot-value-boundary-filler-removal",
    "slot-value-boundary-url-email-casing",
}
EXPECTED_CLASS_COUNTS = {
    "slot_key_aliases": 3,
    "slot_value_boundaries": 4,
}
EXCLUDED_SOURCE_CANDIDATE_IDS = {
    "normalized-command-display-search-template",
    "normalized-command-display-safety-template",
    "date_today_vs_tomorrow",
    "city_origin_vs_destination",
    "product_name_change",
    "url_host_change",
    "price_amount_change",
    "product_name_vs_query",
    "location_vs_destination",
    "action_vs_reason",
}
REQUIRED_TOP_LEVEL_FIELDS = {
    "id",
    "input_text",
    "target_contract",
    "split",
    "augmentations",
    "provenance",
}
REQUIRED_CONTRACT_FIELDS = {
    "contract_version",
    "language",
    "task_type",
    "route",
    "safety",
    "confirmation_required",
    "slots",
    "normalized_command",
}
REQUIRED_PROVENANCE_FIELDS = {
    "candidate_status",
    "public_safe",
    "source_mode",
    "source_candidate_id",
    "eligible_source_class",
    "source_materialization_artifact",
    "source_review_artifact",
    "source_policy_file",
    "source_policy_section",
    "source_manifest_id",
    "formal_public_sample_status",
    "strict_exact_impact",
}
PROTECTED_PATHS = [
    "data/public-samples/seed_traces.jsonl",
    "data/public-samples/sft_public_sample.jsonl",
    "data/public-samples/dpo_public_sample.jsonl",
    "data/public-samples/manifest_public_sample.json",
    "reports/public-sample/canonical-slot-boundary-candidates",
    "reports/public-sample/canonical-slot-boundary-candidate-review",
    "reports/public-sample/canonical-slot-boundary-formal-merge-proposal",
    "reports/public-sample/slot-canonicalization-policy",
    "openspec/changes/merge-scaled-clarify-slot-boundary-candidates",
    "src/voice2task",
]
STILL_PROTECTED_AFTER_FORMAL_MERGE_PATHS = [
    "reports/public-sample/canonical-slot-boundary-candidates",
    "reports/public-sample/canonical-slot-boundary-candidate-review",
    "reports/public-sample/canonical-slot-boundary-formal-merge-proposal",
    "reports/public-sample/slot-canonicalization-policy",
]


def _read_json(path: Path) -> dict[str, Any]:
    assert path.exists()
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    assert path.exists()
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _candidate_rows() -> list[dict[str, Any]]:
    return _read_jsonl(CANDIDATE_SOURCE)


def test_candidate_source_has_exact_reviewed_train_only_rows_and_schema() -> None:
    rows = _candidate_rows()
    assert len(rows) == 7
    assert {row["id"] for row in rows} == EXPECTED_SOURCE_CANDIDATE_IDS
    assert {row["provenance"]["source_candidate_id"] for row in rows} == (
        EXPECTED_SOURCE_CANDIDATE_IDS
    )
    assert Counter(row["split"] for row in rows) == {"train": 7}
    assert Counter(row["provenance"]["eligible_source_class"] for row in rows) == (
        EXPECTED_CLASS_COUNTS
    )

    for row in rows:
        assert set(row) == REQUIRED_TOP_LEVEL_FIELDS
        assert isinstance(row["input_text"], str)
        assert row["input_text"].strip()
        assert isinstance(row["augmentations"], list)
        assert len(row["augmentations"]) == 2
        assert row["input_text"] not in row["augmentations"]
        assert all(isinstance(item, str) and item.strip() for item in row["augmentations"])

        contract = row["target_contract"]
        assert set(contract) == REQUIRED_CONTRACT_FIELDS
        assert contract["contract_version"] == "v1"
        assert contract["language"] == "zh-CN"
        assert contract["normalized_command"].strip()
        assert isinstance(contract["slots"], dict)
        assert contract["slots"]
        assert isinstance(contract["confirmation_required"], bool)
        assert contract["safety"]["allow"] in {True, False}
        assert isinstance(contract["safety"]["reason"], str)
        assert contract["safety"]["reason"].strip()

        provenance = row["provenance"]
        assert set(provenance) == REQUIRED_PROVENANCE_FIELDS
        assert provenance["candidate_status"] == "standalone_not_formal_public_sample"
        assert provenance["public_safe"] is True
        assert provenance["source_mode"] == "canonical_slot_boundary_candidate_seed"
        assert provenance["source_candidate_id"] == row["id"]
        assert provenance["source_materialization_artifact"] == (
            "reports/public-sample/canonical-slot-boundary-candidates/summary.json"
        )
        assert provenance["source_review_artifact"] == (
            "reports/public-sample/canonical-slot-boundary-candidate-review/summary.json"
        )
        assert provenance["source_policy_file"] in {
            "slot-key-policy.md",
            "slot-value-policy.md",
        }
        assert provenance["source_policy_section"]
        assert provenance["source_manifest_id"] == "public-sample-20260617T152259Z"
        assert provenance["formal_public_sample_status"] == "not_added"
        assert provenance["strict_exact_impact"] == "none"


def test_only_eligible_classes_are_materialized_and_excluded_cases_stay_out() -> None:
    rows = _candidate_rows()
    source_ids = {row["provenance"]["source_candidate_id"] for row in rows}
    source_classes = {row["provenance"]["eligible_source_class"] for row in rows}
    serialized = json.dumps(rows, ensure_ascii=False)

    assert source_classes == set(EXPECTED_CLASS_COUNTS)
    assert source_ids.isdisjoint(EXCLUDED_SOURCE_CANDIDATE_IDS)
    assert "normalized_command_display_diagnostic" not in source_classes
    assert "excluded_non_equivalence_cases" not in source_classes
    assert "display_normalized_command" not in serialized
    for excluded_id in EXCLUDED_SOURCE_CANDIDATE_IDS:
        assert excluded_id not in serialized


def test_report_local_preview_and_evidence_record_standalone_boundary() -> None:
    seed_rows = _candidate_rows()
    sft_rows = _read_jsonl(SFT_PREVIEW)
    evidence = _read_json(EVIDENCE_JSON)
    manifest = _read_json(MANIFEST)
    report = EVIDENCE_MD.read_text(encoding="utf-8")

    assert len(sft_rows) == 21
    assert Counter(row["split"] for row in sft_rows) == {"train": 21}
    assert set(Counter(row["provenance"]["source_id"] for row in sft_rows).values()) == {3}
    assert {row["provenance"]["source_id"] for row in sft_rows} == {
        row["id"] for row in seed_rows
    }
    for row in sft_rows:
        SFTDatasetRow(**row)
        assert row["provenance"]["candidate_status"] == (
            "standalone_not_formal_public_sample"
        )
        assert row["provenance"]["public_safe"] is True
        assert row["provenance"]["source_mode"] in {
            "canonical_slot_boundary_candidate",
            "schema_preserving_augmentation",
        }

    assert evidence["evidence_kind"] == (
        "canonical_slot_boundary_row_level_candidate_materialization"
    )
    assert evidence["materialization_status"] == (
        "standalone_row_level_candidate_source_materialized"
    )
    assert evidence["summary"]["candidate_seed_rows"] == 7
    assert evidence["summary"]["candidate_sft_preview_rows"] == 21
    assert evidence["summary"]["seed_split_counts"] == {"train": 7}
    assert evidence["summary"]["sft_preview_split_counts"] == {"train": 21}
    assert evidence["summary"]["eligible_source_class_counts"] == EXPECTED_CLASS_COUNTS
    assert evidence["summary"]["formal_public_sample_modified"] is False
    assert evidence["comparison_boundary"]["formal_sample_boundary_changed"] is False
    assert evidence["comparison_boundary"]["old_metrics_directly_comparable"] is True
    assert evidence["recommended_next_bounded_step"] == {
        "operation": "formal_merge_review_or_apply_phase_can_inspect_this_source",
        "direct_formal_merge_implemented_now": False,
    }

    for flag in (
        "formal_public_sample_data_mutation",
        "formal_sft_or_dpo_generation",
        "formal_manifest_rebuild",
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
        assert evidence["execution_scope"][flag] is False
        assert manifest["execution_scope"][flag] is False

    assert manifest["artifact_policy"]["standalone_only"] is True
    assert manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert manifest["artifact_policy"]["report_local_sft_preview_only"] is True
    assert "standalone row-level candidate source" in report
    assert "does not merge the formal public sample" in report
    assert "No model-quality improvement can be inferred" in report


def test_protected_formal_sources_and_source_evidence_are_not_modified() -> None:
    result = subprocess.run(
        ["git", "status", "--short", "--", *STILL_PROTECTED_AFTER_FORMAL_MERGE_PATHS],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stdout == ""


def test_candidate_reports_and_human_brief_are_public_safe() -> None:
    assert HUMAN_BRIEF.exists()
    leak_scan = _read_json(LEAK_SCAN_RESULT)
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []

    result = scan_paths([CANDIDATE_SOURCE, REPORT_DIR, HUMAN_BRIEF])
    assert result.ok is True
    assert result.findings == []

    brief = HUMAN_BRIEF.read_text(encoding="utf-8")
    assert "standalone_not_formal_public_sample" in brief
    assert "formal public sample" in brief
    assert "model-quality" in brief
