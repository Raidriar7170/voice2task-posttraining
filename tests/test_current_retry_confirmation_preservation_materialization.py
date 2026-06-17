from __future__ import annotations

from pathlib import Path

from public_sample_fixtures import SCALED_PUBLIC_SAMPLE_COUNTS, SCALED_PUBLIC_SAMPLE_SPLITS

from voice2task.dataset import materialize_current_retry_confirmation_preservation_candidates
from voice2task.io import read_json, read_jsonl

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_DIR = REPO_ROOT / "data" / "public-samples"
DESIGN_PATH = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "current-retry-confirmation-preservation-candidate-design"
    / "current_retry_confirmation_preservation_candidate_design.json"
)
MATERIALIZATION_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "current-retry-confirmation-preservation-materialization"
)
MERGE_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "current-retry-confirmation-preservation-public-sample-merge"
)
EXPECTED_IDS = {
    "candidate-current-retry-public-navigation-non-confirmation-preservation",
    "candidate-current-retry-unsafe-payment-confirmation-preservation",
}


def _assert_confirmation_preservation_contract(row: dict) -> None:
    contract = row["target_contract"]
    provenance = row["provenance"]
    assert row["split"] == "train"
    assert provenance["public_safe"] is True
    assert provenance["candidate_status"] == "formal_public_sample"
    assert provenance["source_mode"] == "current_retry_confirmation_preservation_formal_public_seed"
    assert provenance["source_design_evidence_kind"] == "current_retry_confirmation_preservation_candidate_design"
    assert provenance["source_row_ids"]
    assert provenance["accepted_target_contract_sketch"]
    assert provenance["rejected_drift_sketches"]

    if provenance["candidate_family"] == "unsafe_payment_confirmation_preservation":
        assert contract["task_type"] == "blocked"
        assert contract["route"] == "deny"
        assert contract["safety"] == {"allow": False, "reason": "unsafe_payment"}
        assert contract["confirmation_required"] is True
        assert contract["slots"] == {"reason": "payment_requires_user_control"}
    elif provenance["candidate_family"] == "public_navigation_non_confirmation_preservation":
        assert contract["task_type"] == "navigate"
        assert contract["route"] == "open_url"
        assert contract["safety"] == {"allow": True, "reason": "public_readonly"}
        assert contract["confirmation_required"] is False
        assert contract["slots"] == {"url": "https://learn.example.com"}
    else:
        raise AssertionError(f"unexpected candidate family: {provenance['candidate_family']}")


def test_committed_public_sample_contains_current_retry_confirmation_preservation_seeds() -> None:
    seed_rows = read_jsonl(PUBLIC_SAMPLE_DIR / "seed_traces.jsonl")
    materialized = [row for row in seed_rows if row["id"] in EXPECTED_IDS]
    assert {row["id"] for row in materialized} == EXPECTED_IDS
    for row in materialized:
        _assert_confirmation_preservation_contract(row)

    manifest = read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")
    assert manifest["counts"] == SCALED_PUBLIC_SAMPLE_COUNTS
    assert manifest["split_counts"] == SCALED_PUBLIC_SAMPLE_SPLITS
    source_summary = manifest["source_summary"]
    assert source_summary["current_retry_confirmation_preservation_candidate_seed_rows"] == 2
    assert source_summary["current_retry_confirmation_preservation_candidate_sft_rows"] == 5
    assert source_summary["current_retry_confirmation_preservation_candidates_formal_public_sample"] is True
    assert source_summary["current_retry_confirmation_preservation_families"] == [
        "public_navigation_non_confirmation_preservation",
        "unsafe_payment_confirmation_preservation",
    ]
    assert source_summary["current_retry_confirmation_preservation_seed_split_counts"] == {
        "train": 2,
        "dev": 0,
        "test": 0,
    }


def test_current_retry_confirmation_preservation_materialization_report_is_bounded() -> None:
    materialization_manifest = read_json(MATERIALIZATION_DIR / "manifest.json")
    assert materialization_manifest["source_candidate_design"]["dataset_manifest_id"] == (
        "public-sample-20260616T165835Z"
    )
    assert materialization_manifest["summary"]["candidate_family_count"] == 2
    assert materialization_manifest["summary"]["candidate_seed_rows"] == 2
    assert materialization_manifest["summary"]["candidate_sft_rows"] == 5
    assert materialization_manifest["summary"]["formal_public_sample_seed_rows"] == 100
    assert materialization_manifest["summary"]["formal_public_sample_sft_rows"] == 256
    assert materialization_manifest["summary"]["formal_public_sample_dpo_pairs"] == 864
    assert (
        materialization_manifest["summary"][
            "formal_public_sample_has_current_retry_confirmation_preservation_candidates"
        ]
        is False
    )
    assert materialization_manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert materialization_manifest["artifact_policy"]["training_run"] is False
    assert materialization_manifest["artifact_policy"]["prediction_run"] is False
    assert materialization_manifest["artifact_policy"]["evaluator_metric_change"] is False

    merge_manifest = read_json(MERGE_DIR / "manifest.json")
    assert merge_manifest["pre_merge_public_sample_counts"] == {
        "seed_rows": 100,
        "sft_rows": 256,
        "dpo_pairs": 864,
    }
    assert merge_manifest["formal_public_sample_counts"] == {
        "seed_rows": 102,
        "sft_rows": 261,
        "dpo_pairs": 881,
    }
    assert merge_manifest["candidate_source"]["candidate_seed_rows"] == 2
    assert merge_manifest["candidate_source"]["candidate_sft_rows"] == 5
    assert merge_manifest["candidate_source"]["candidate_dpo_pairs"] == 17
    assert merge_manifest["candidate_source"]["dpo_rejection_deltas"] == {
        "blocked_payment_action_drift": 1,
        "malformed_schema": 2,
        "missing_confirmation": 1,
        "missing_slot": 2,
        "navigate_canonical_url_drift": 1,
        "underspecified_request": 2,
        "unsafe_allowance": 2,
        "wrong_route": 2,
        "wrong_slot": 2,
        "wrong_task_type": 2,
    }
    assert merge_manifest["validation"]["ok"] is True
    assert merge_manifest["claims"]["model_quality_claim"] is False
    assert merge_manifest["claims"]["model_recovery_claim"] is False
    assert merge_manifest["claims"]["safety_improvement_claim"] is False
    assert merge_manifest["claims"]["production_readiness_claim"] is False
    assert merge_manifest["claims"]["live_browser_benchmark_claim"] is False


def test_current_retry_confirmation_preservation_materialization_is_reproducible(tmp_path: Path) -> None:
    seed_output = tmp_path / "candidate_seed_traces.jsonl"
    output_dir = tmp_path / "materialization"
    paths = materialize_current_retry_confirmation_preservation_candidates(
        candidate_design_path=DESIGN_PATH,
        seed_output_path=seed_output,
        output_dir=output_dir,
    )

    candidate_rows = read_jsonl(paths["seed"])
    assert {row["id"] for row in candidate_rows} == EXPECTED_IDS
    assert sum(1 for _ in (output_dir / "sft_candidate_rows.jsonl").read_text().splitlines()) == 5
    manifest = read_json(paths["manifest"])
    assert manifest["summary"]["formal_public_sample_modified"] is False
    assert manifest["summary"]["seed_traces_modified"] is False
    assert manifest["artifact_policy"]["public_sample_modified"] is False
