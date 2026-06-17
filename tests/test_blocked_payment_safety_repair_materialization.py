from __future__ import annotations

from pathlib import Path

from public_sample_fixtures import SCALED_PUBLIC_SAMPLE_COUNTS

from voice2task.dataset import materialize_blocked_payment_safety_repair_candidates
from voice2task.io import read_json, read_jsonl

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_DIR = REPO_ROOT / "data" / "public-samples"
DESIGN_PATH = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "blocked-payment-safety-repair-candidate-design"
    / "blocked_payment_safety_repair_candidate_design.json"
)
MATERIALIZATION_DIR = REPO_ROOT / "reports" / "public-sample" / "blocked-payment-safety-repair-materialization"
MERGE_DIR = REPO_ROOT / "reports" / "public-sample" / "blocked-payment-safety-repair-public-sample-merge"
EXPECTED_IDS = {
    "candidate-blocked-payment-repair-refund-confirmation-or-processing",
    "candidate-blocked-payment-repair-subscription-charge-confirmation",
}


def _assert_blocked_payment_repair_contract(row: dict) -> None:
    contract = row["target_contract"]
    assert row["split"] == "train"
    assert contract["task_type"] == "blocked"
    assert contract["route"] == "deny"
    assert contract["safety"] == {"allow": False, "reason": "unsafe_payment"}
    assert contract["confirmation_required"] is False
    assert contract["slots"]["reason"] in {"refund_control", "subscription_charge_control"}
    provenance = row["provenance"]
    assert provenance["public_safe"] is True
    assert provenance["candidate_status"] == "formal_public_sample"
    assert provenance["source_mode"] == "blocked_payment_safety_repair_formal_public_seed"
    assert provenance["repair_family"] in {
        "refund_confirmation_or_processing",
        "subscription_charge_confirmation",
    }
    assert provenance["source_design_evidence_kind"] == "blocked_payment_safety_repair_candidate_design"
    assert provenance["source_row_ids"]


def test_committed_public_sample_contains_blocked_payment_repair_seeds() -> None:
    seed_rows = read_jsonl(PUBLIC_SAMPLE_DIR / "seed_traces.jsonl")
    materialized = [row for row in seed_rows if row["id"] in EXPECTED_IDS]
    assert {row["id"] for row in materialized} == EXPECTED_IDS
    for row in materialized:
        _assert_blocked_payment_repair_contract(row)

    manifest = read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")
    assert manifest["counts"] == SCALED_PUBLIC_SAMPLE_COUNTS
    source_summary = manifest["source_summary"]
    assert source_summary["blocked_payment_safety_repair_candidate_seed_rows"] == 2
    assert source_summary["blocked_payment_safety_repair_candidate_sft_rows"] == 4
    assert source_summary["blocked_payment_safety_repair_candidates_formal_public_sample"] is True
    assert source_summary["blocked_payment_safety_repair_seed_split_counts"] == {
        "train": 2,
        "dev": 0,
        "test": 0,
    }


def test_blocked_payment_repair_materialization_report_is_bounded() -> None:
    materialization_manifest = read_json(MATERIALIZATION_DIR / "manifest.json")
    assert materialization_manifest["summary"]["candidate_seed_rows"] == 2
    assert materialization_manifest["summary"]["candidate_sft_rows"] == 4
    assert materialization_manifest["artifact_policy"]["formal_public_sample_files_modified"] is False
    assert materialization_manifest["artifact_policy"]["training_run"] is False
    assert materialization_manifest["artifact_policy"]["prediction_run"] is False

    merge_manifest = read_json(MERGE_DIR / "manifest.json")
    assert merge_manifest["formal_public_sample_counts"] == {
        "seed_rows": 100,
        "sft_rows": 256,
        "dpo_pairs": 864,
    }
    assert merge_manifest["candidate_source"]["candidate_seed_rows"] == 2
    assert merge_manifest["candidate_source"]["candidate_sft_rows"] == 4
    assert merge_manifest["candidate_source"]["candidate_dpo_pairs"] == 14
    assert merge_manifest["candidate_source"]["dpo_rejection_deltas"] == {
        "malformed_schema": 2,
        "missing_slot": 2,
        "underspecified_request": 2,
        "unsafe_allowance": 2,
        "wrong_route": 2,
        "wrong_slot": 2,
        "wrong_task_type": 2,
    }
    assert merge_manifest["validation"]["ok"] is True
    assert merge_manifest["claims"]["model_quality_claim"] is False
    assert merge_manifest["claims"]["safety_improvement_claim"] is False
    assert merge_manifest["claims"]["production_readiness_claim"] is False
    assert merge_manifest["claims"]["live_browser_benchmark_claim"] is False


def test_blocked_payment_repair_materialization_is_reproducible(tmp_path: Path) -> None:
    seed_output = tmp_path / "candidate_seed_traces.jsonl"
    output_dir = tmp_path / "materialization"
    paths = materialize_blocked_payment_safety_repair_candidates(
        candidate_design_path=DESIGN_PATH,
        seed_output_path=seed_output,
        output_dir=output_dir,
    )

    candidate_rows = read_jsonl(paths["seed"])
    assert {row["id"] for row in candidate_rows} == EXPECTED_IDS
    assert sum(1 for _ in (output_dir / "sft_candidate_rows.jsonl").read_text().splitlines()) == 4
    manifest = read_json(paths["manifest"])
    assert manifest["summary"]["formal_public_sample_modified"] is False
    assert manifest["summary"]["seed_traces_modified"] is False
    assert manifest["artifact_policy"]["public_sample_modified"] is False
