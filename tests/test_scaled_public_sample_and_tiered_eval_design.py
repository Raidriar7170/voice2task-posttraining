import json
from pathlib import Path
from typing import Any

import pytest

from voice2task.cli import report as report_cli
from voice2task.io import read_json, read_jsonl
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_scaled_public_sample_and_tiered_eval_design_report

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_DIR = REPO_ROOT / "data" / "public-samples"
PUBLIC_SAMPLE_MANIFEST = PUBLIC_SAMPLE_DIR / "manifest_public_sample.json"
CURRENT_123_RETRY_DIR = REPO_ROOT / "reports" / "public-sample" / "a100-current-123-train-split-sft-retry"


def test_scaled_public_sample_and_tiered_eval_design_cli_is_public_safe_and_non_claiming(
    tmp_path: Path,
    capsys: Any,
) -> None:
    output_dir = tmp_path / "scaled-public-sample-and-tiered-eval-design"

    assert (
        report_cli.main(
            [
                "scaled-public-sample-and-tiered-eval-design",
                "--public-manifest",
                PUBLIC_SAMPLE_MANIFEST.as_posix(),
                "--seed",
                (PUBLIC_SAMPLE_DIR / "seed_traces.jsonl").as_posix(),
                "--sft",
                (PUBLIC_SAMPLE_DIR / "sft_public_sample.jsonl").as_posix(),
                "--dpo",
                (PUBLIC_SAMPLE_DIR / "dpo_public_sample.jsonl").as_posix(),
                "--current-retry-evidence",
                (CURRENT_123_RETRY_DIR / "current_train_split_sft_retry.json").as_posix(),
                "--dev-metrics",
                (CURRENT_123_RETRY_DIR / "dev" / "metrics.json").as_posix(),
                "--test-metrics",
                (CURRENT_123_RETRY_DIR / "test" / "metrics.json").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    design = read_json(output_dir / "scaled_public_sample_and_tiered_eval_design.json")
    manifest = read_json(output_dir / "manifest.json")
    markdown = (output_dir / "scaled_public_sample_and_tiered_eval_design.md").read_text(encoding="utf-8")

    assert payload["ok"] is True
    assert design["evidence_kind"] == "scaled_public_sample_and_tiered_eval_design"
    assert design["dataset_manifest_id"] == "public-sample-20260617T045941Z"
    assert design["summary"]["current_seed_rows"] == 102
    assert design["summary"]["current_sft_rows"] == 261
    assert design["summary"]["current_dpo_pairs"] == 881
    assert design["summary"]["current_train_rows"] == 123
    assert design["summary"]["current_sft_split_counts"] == {"dev": 69, "test": 69, "train": 123}
    assert design["summary"]["current_seed_split_counts"] == {"dev": 23, "test": 23, "train": 56}
    assert design["summary"]["target_seed_milestone"] == 240
    assert design["summary"]["target_core_bucket_seed_rows_total"] == 220
    assert design["summary"]["target_overlay_seed_rows_total"] == 20
    assert design["current_coverage"]["task_type_counts"]["form_fill"] == 42
    assert design["current_coverage"]["task_type_counts"]["clarify"] == 12
    assert design["latest_model_evidence"]["split_metrics"]["dev"]["contract_exact_match"] == (
        0.43478260869565216
    )
    assert design["latest_model_evidence"]["split_metrics"]["test"]["slot_f1"] == 0.5458937198067634
    assert design["tiered_evaluation_design"]["metric_authority"] == {
        "contract_exact_match_primary_metric": True,
        "semantic_equivalence_primary_metric": False,
        "slot_f1_soft_primary_metric": False,
        "strict_slot_f1_primary_metric": True,
        "tiered_eval_is_diagnostic": True,
    }
    assert design["execution_scope"]["design_only"] is True
    assert design["execution_scope"]["formal_public_sample_modified"] is False
    assert design["execution_scope"]["training_run"] is False
    assert design["execution_scope"]["prediction_run"] is False
    assert design["execution_scope"]["evaluator_metric_change"] is False
    assert design["claims"]["model_recovery_claim"] is False
    assert design["claims"]["soft_slot_f1_primary_metric"] is False
    confirmation_bucket = [
        bucket
        for bucket in design["scaled_public_sample_design"]["target_buckets"]
        if bucket["bucket"] == "confirmation_boundary"
    ][0]
    assert confirmation_bucket["counts_toward_target_seed_milestone"] is False
    assert manifest["artifact_policy"]["design_only"] is True
    assert manifest["artifact_policy"]["seed_traces_modified"] is False
    assert "design-only public evidence report" in markdown
    assert "strict `contract_exact_match` and strict `slot_f1` remain public headline metrics" in markdown
    assert "Current SFT split counts: `{'dev': 69, 'test': 69, 'train': 123}`" in markdown
    assert "Current seed split counts: `{'train': 56, 'dev': 23, 'test': 23}`" in markdown
    assert "Target seed milestone: `240`" in markdown
    assert "Target core bucket total: `220`" in markdown
    assert "Target overlay bucket total: `20`" in markdown
    assert scan_paths([output_dir]).ok is True


def test_scaled_public_sample_design_rejects_mismatched_model_evidence_manifest(tmp_path: Path) -> None:
    current_retry = read_json(CURRENT_123_RETRY_DIR / "current_train_split_sft_retry.json")
    current_retry["dataset_manifest_id"] = "public-sample-stale"

    with pytest.raises(ValueError, match="current retry evidence manifest mismatch"):
        write_scaled_public_sample_and_tiered_eval_design_report(
            public_manifest=read_json(PUBLIC_SAMPLE_MANIFEST),
            seed_rows=read_jsonl(PUBLIC_SAMPLE_DIR / "seed_traces.jsonl"),
            sft_rows=read_jsonl(PUBLIC_SAMPLE_DIR / "sft_public_sample.jsonl"),
            dpo_rows=read_jsonl(PUBLIC_SAMPLE_DIR / "dpo_public_sample.jsonl"),
            current_retry_evidence=current_retry,
            dev_metrics=read_json(CURRENT_123_RETRY_DIR / "dev" / "metrics.json"),
            test_metrics=read_json(CURRENT_123_RETRY_DIR / "test" / "metrics.json"),
            output_dir=tmp_path / "design",
        )
