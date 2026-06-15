import json
from pathlib import Path

import pytest

from voice2task.cli import data as data_cli
from voice2task.cli import report as report_cli
from voice2task.dataset import build_public_sample_dataset, merge_slot_value_candidates_into_public_sample
from voice2task.io import read_json, read_jsonl, write_jsonl
from voice2task.leak_scan import scan_paths
from voice2task.validation import validate_dataset_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_DIR = REPO_ROOT / "data" / "public-samples"
CANDIDATE_SEED = PUBLIC_SAMPLE_DIR / "slot_value_generalization_seed_candidates.jsonl"

EXPECTED_COUNTS = {"dpo_pairs": 125, "seed_rows": 14, "sft_rows": 42}
EXPECTED_SPLITS = {"dev": 6, "test": 6, "train": 30}
EXPECTED_CANDIDATE_IDS = {
    "candidate-blocked-payment-canonical-command",
    "candidate-clarify-ambiguous-canonical-scope",
    "candidate-form-email-canonical-field",
    "candidate-navigate-open-url-canonical-command",
}
MERGED_EVIDENCE_DIR = REPO_ROOT / "reports" / "public-sample" / "a100-merged-slot-value-heldout-eval"
MERGED_A100_CONFIGS = {
    "sft": REPO_ROOT / "configs" / "sft-a100-merged-slot-value-heldout-rerun.json",
    "train": REPO_ROOT / "configs" / "sft-a100-merged-slot-value-heldout-train-prediction.json",
    "dev": REPO_ROOT / "configs" / "sft-a100-merged-slot-value-heldout-dev-prediction.json",
    "test": REPO_ROOT / "configs" / "sft-a100-merged-slot-value-heldout-test-prediction.json",
}


def _copy_current_public_sample(tmp_path: Path) -> Path:
    public_dir = tmp_path / "public-samples"
    public_dir.mkdir()
    seed_rows = [
        row for row in read_jsonl(PUBLIC_SAMPLE_DIR / "seed_traces.jsonl") if row["id"] not in EXPECTED_CANDIDATE_IDS
    ]
    write_jsonl(public_dir / "seed_traces.jsonl", seed_rows)
    build_public_sample_dataset(seed_path=public_dir / "seed_traces.jsonl", output_dir=public_dir)
    return public_dir


def test_merge_slot_value_candidates_rebuilds_formal_public_sample(tmp_path: Path) -> None:
    public_dir = _copy_current_public_sample(tmp_path)

    manifest = merge_slot_value_candidates_into_public_sample(
        candidate_seed_path=CANDIDATE_SEED,
        seed_path=public_dir / "seed_traces.jsonl",
        output_dir=public_dir,
    )

    seed_rows = read_jsonl(public_dir / "seed_traces.jsonl")
    sft_rows = read_jsonl(public_dir / "sft_public_sample.jsonl")
    dpo_rows = read_jsonl(public_dir / "dpo_public_sample.jsonl")
    manifest_payload = read_json(public_dir / "manifest_public_sample.json")

    assert manifest.counts == EXPECTED_COUNTS
    assert manifest.split_counts == EXPECTED_SPLITS
    assert manifest_payload["counts"] == EXPECTED_COUNTS
    assert manifest_payload["split_counts"] == EXPECTED_SPLITS
    assert manifest_payload["source_summary"]["slot_value_candidate_seed_rows"] == 4
    assert manifest_payload["source_summary"]["slot_value_candidates_formal_public_sample"] is True
    assert len(seed_rows) == 14
    assert len(sft_rows) == 42
    assert len(dpo_rows) == 125

    seed_by_id = {row["id"]: row for row in seed_rows}
    sft_by_id = {row["id"]: row for row in sft_rows}
    dpo_by_id = {row["id"]: row for row in dpo_rows}
    assert EXPECTED_CANDIDATE_IDS.issubset(seed_by_id)
    assert all(seed_by_id[row_id]["split"] == "train" for row_id in EXPECTED_CANDIDATE_IDS)
    assert all(
        seed_by_id[row_id]["provenance"]["candidate_status"] == "formal_public_sample"
        for row_id in EXPECTED_CANDIDATE_IDS
    )
    assert all(sft_by_id[f"{row_id}-aug-1"]["split"] == "train" for row_id in EXPECTED_CANDIDATE_IDS)
    assert (
        sft_by_id["candidate-form-email-canonical-field"]["provenance"]["source_case_group_id"]
        == "form-email-slot-value-language-variant"
    )
    assert sft_by_id["candidate-form-email-canonical-field"]["provenance"]["candidate_status"] == (
        "formal_public_sample"
    )
    assert dpo_by_id["candidate-form-email-canonical-field-wrong_task_type"]["rejection_reason"] == (
        "wrong_task_type"
    )
    assert dpo_by_id["candidate-clarify-ambiguous-canonical-scope-clarify_action_drift"][
        "rejection_reason"
    ] == "clarify_action_drift"
    assert dpo_by_id["candidate-blocked-payment-canonical-command-blocked_payment_action_drift"][
        "rejection_reason"
    ] == "blocked_payment_action_drift"
    assert dpo_by_id["candidate-navigate-open-url-canonical-command-navigate_canonical_url_drift"][
        "rejection_reason"
    ] == "navigate_canonical_url_drift"
    assert "candidate-form-email-canonical-field-aug-1-wrong_task_type" not in dpo_by_id

    validation = validate_dataset_artifacts(
        sft_path=public_dir / "sft_public_sample.jsonl",
        dpo_path=public_dir / "dpo_public_sample.jsonl",
        manifest_path=public_dir / "manifest_public_sample.json",
        public=True,
    )
    assert validation.ok is True
    assert scan_paths([public_dir]).ok is True


def test_merge_slot_value_candidates_cli(tmp_path: Path, capsys) -> None:
    public_dir = _copy_current_public_sample(tmp_path)

    assert (
        data_cli.main(
            [
                "merge-slot-value-candidates",
                "--candidate-seed",
                CANDIDATE_SEED.as_posix(),
                "--seed",
                (public_dir / "seed_traces.jsonl").as_posix(),
                "--output",
                public_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["counts"] == EXPECTED_COUNTS
    assert payload["split_counts"] == EXPECTED_SPLITS
    assert payload["source_summary"]["slot_value_candidate_seed_rows"] == 4


def test_merge_slot_value_candidates_rejects_unreviewed_candidate_rows(tmp_path: Path) -> None:
    public_dir = _copy_current_public_sample(tmp_path)
    candidate_rows = read_jsonl(CANDIDATE_SEED)
    unreviewed = dict(candidate_rows[0])
    unreviewed["id"] = "candidate-unreviewed-extra-row"
    write_jsonl(tmp_path / "candidate_seed_with_extra.jsonl", [*candidate_rows, unreviewed])

    with pytest.raises(ValueError, match="expected reviewed slot-value candidate seed IDs"):
        merge_slot_value_candidates_into_public_sample(
            candidate_seed_path=tmp_path / "candidate_seed_with_extra.jsonl",
            seed_path=public_dir / "seed_traces.jsonl",
            output_dir=public_dir,
        )


def test_committed_formal_public_sample_contains_merged_slot_value_candidates() -> None:
    manifest = read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")
    seed_rows = read_jsonl(PUBLIC_SAMPLE_DIR / "seed_traces.jsonl")
    sft_rows = read_jsonl(PUBLIC_SAMPLE_DIR / "sft_public_sample.jsonl")
    dpo_rows = read_jsonl(PUBLIC_SAMPLE_DIR / "dpo_public_sample.jsonl")

    assert manifest["counts"] == EXPECTED_COUNTS
    assert manifest["split_counts"] == EXPECTED_SPLITS
    assert {row["id"] for row in seed_rows}.issuperset(EXPECTED_CANDIDATE_IDS)
    assert {row["id"] for row in sft_rows}.issuperset(
        {row_id for seed_id in EXPECTED_CANDIDATE_IDS for row_id in (seed_id, f"{seed_id}-aug-1", f"{seed_id}-aug-2")}
    )
    assert {row["id"] for row in dpo_rows}.issuperset(
        {f"{seed_id}-wrong_task_type" for seed_id in EXPECTED_CANDIDATE_IDS}
    )
    assert scan_paths([PUBLIC_SAMPLE_DIR]).ok is True


def test_committed_merged_slot_value_a100_evidence_is_bounded_and_public_safe() -> None:
    evidence = read_json(MERGED_EVIDENCE_DIR / "merged_slot_value_heldout_eval.json")
    manifest = read_json(MERGED_EVIDENCE_DIR / "manifest.json")

    assert manifest["formal_public_sample_counts"] == EXPECTED_COUNTS
    assert manifest["comparison"]["merged_slot_value_exact"] == {
        "dev": 0.5,
        "test": 5 / 6,
        "train": 1.0,
    }
    assert manifest["claims"]["held_out_generalization_recovered"] is False
    assert manifest["claims"]["adapter_release"] is False
    assert manifest["claims"]["checkpoint_release"] is False
    assert manifest["claims"]["private_corpus_generalization_claim"] is False
    assert manifest["claims"]["soft_slot_f1_primary_metric"] is False
    assert evidence["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert "SFT training ran locally" not in json.dumps(evidence, ensure_ascii=False)
    assert scan_paths([MERGED_EVIDENCE_DIR]).ok is True


def test_merged_slot_value_a100_configs_are_split_specific_and_public_safe() -> None:
    manifest = read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")
    manifest_id = manifest["manifest_id"]
    sft_config = read_json(MERGED_A100_CONFIGS["sft"])
    serialized_sft = json.dumps(sft_config, ensure_ascii=False, sort_keys=True)

    assert sft_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert sft_config["dataset_manifest_id"] == manifest_id
    assert sft_config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
    assert sft_config["dataset_split"] == "train"
    assert sft_config["allow_heavy_training"] is True
    assert sft_config["merged_slot_value_candidates"] is True
    assert sft_config["generalization_claim"] is False
    assert sft_config["output_root"] == "<a100_project_root>"
    assert sft_config["adapter_output_dir"] == (
        "<a100_project_root>/runs/a100-merged-slot-value-heldout-eval/adapter"
    )
    assert "/mnt/data/" not in serialized_sft
    assert "/Users/" not in serialized_sft

    for split in ("train", "dev", "test"):
        config = read_json(MERGED_A100_CONFIGS[split])
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)
        assert config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
        assert config["dataset_manifest_id"] == manifest_id
        assert config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["merged_slot_value_candidates"] is True
        assert config["generalization_claim"] is False
        assert config["adapter_path"] == "<a100_project_root>/runs/a100-merged-slot-value-heldout-eval/adapter"
        assert config["evidence_output_dir"] == (
            f"<a100_project_root>/evidence/a100-merged-slot-value-heldout-eval/{split}"
        )
        assert "allow_heavy_training" not in config
        assert "adapter_output_dir" not in config
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized

    assert scan_paths(list(MERGED_A100_CONFIGS.values())).ok is True


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _metrics_payload(exact: float, slot_f1: float, *, slot_failures: int = 0) -> dict:
    return {
        "failure_slices": {
            "schema": {"count": 0, "examples": []},
            "task_type": {"count": 0, "examples": []},
            "route": {"count": 0, "examples": []},
            "safety": {"count": 0, "examples": []},
            "confirmation": {"count": 0, "examples": []},
            "slot": {"count": slot_failures, "examples": ["row-1"] if slot_failures else []},
            "unknown": {"count": 0, "examples": []},
        },
        "metrics": {
            "contract_exact_match": exact,
            "json_valid_rate": 1.0,
            "slot_f1": slot_f1,
            "slot_f1_soft": slot_f1,
            "task_type_accuracy": 1.0,
            "route_accuracy": 1.0,
            "safety_precision": 1.0,
            "safety_recall": 1.0,
            "confirmation_accuracy": 1.0,
        },
    }


def test_merged_slot_value_report_cli_writes_public_safe_evidence(tmp_path: Path, capsys) -> None:
    private_root = "/mnt" + "/data/minghongsun/private"
    manifest = read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")
    training_metadata = _write_json(
        tmp_path / "training_metadata.raw.json",
        {
            "base_model": f"{private_root}/models/qwen2.5-7b",
            "dataset_manifest_id": manifest["manifest_id"],
            "training_rows_used": 30,
            "training_status": "training_completed",
            "adapter_path": f"{private_root}/runs/adapter",
        },
    )
    train_metrics = _write_json(tmp_path / "train_metrics.json", _metrics_payload(1.0, 1.0))
    dev_metrics = _write_json(tmp_path / "dev_metrics.json", _metrics_payload(0.5, 0.75, slot_failures=3))
    test_metrics = _write_json(tmp_path / "test_metrics.json", _metrics_payload(1 / 3, 0.75, slot_failures=4))
    metadata_paths = {}
    for split, count in {"train": 30, "dev": 6, "test": 6}.items():
        metadata_paths[split] = _write_json(
            tmp_path / f"{split}_prediction_metadata.raw.json",
            {
                "adapter_path": f"{private_root}/runs/adapter",
                "dataset_manifest_id": manifest["manifest_id"],
                "prediction_count": count,
                "prediction_source_kind": "private_a100_adapter",
                "prediction_split": split,
                "prediction_status": "private_adapter_predictions_written",
            },
        )
    output_dir = tmp_path / "merged-report"

    assert (
        report_cli.main(
            [
                "merged-slot-value-heldout-eval",
                "--public-manifest",
                (PUBLIC_SAMPLE_DIR / "manifest_public_sample.json").as_posix(),
                "--training-metadata",
                training_metadata.as_posix(),
                "--train-metrics",
                train_metrics.as_posix(),
                "--dev-metrics",
                dev_metrics.as_posix(),
                "--test-metrics",
                test_metrics.as_posix(),
                "--train-prediction-metadata",
                metadata_paths["train"].as_posix(),
                "--dev-prediction-metadata",
                metadata_paths["dev"].as_posix(),
                "--test-prediction-metadata",
                metadata_paths["test"].as_posix(),
                "--prior-targeted-manifest",
                (
                    REPO_ROOT
                    / "reports"
                    / "public-sample"
                    / "a100-targeted-family-coverage-probe"
                    / "manifest.json"
                ).as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    evidence = read_json(output_dir / "merged_slot_value_heldout_eval.json")
    report = (output_dir / "report.md").read_text(encoding="utf-8")
    manifest_path = output_dir / "manifest.json"
    manifest_payload = read_json(manifest_path)
    serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True)

    assert payload["ok"] is True
    assert payload["summary"]["overall_interpretation"] == "merged_slot_value_heldout_improved_partial"
    assert evidence["dataset_manifest_id"] == manifest["manifest_id"]
    assert evidence["formal_public_sample_counts"] == EXPECTED_COUNTS
    assert evidence["split_results"]["train"]["prediction_count"] == 30
    assert evidence["split_results"]["dev"]["prediction_count"] == 6
    assert evidence["split_results"]["test"]["prediction_count"] == 6
    assert evidence["split_results"]["dev"]["contract_exact_match"] == 0.5
    assert evidence["comparison"]["prior_targeted_family_coverage_exact"] == {
        "dev": 1 / 6,
        "test": 1 / 6,
        "train": 1.0,
    }
    assert evidence["comparison"]["dev_test_improved_from_prior_targeted"] == {"dev": True, "test": True}
    assert evidence["claims"]["held_out_generalization_recovered"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert evidence["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest_payload["evidence_kind"] == "a100_merged_slot_value_heldout_eval"
    assert "strict `contract_exact_match` remains primary" in report
    assert "/mnt/data/" not in serialized
    assert scan_paths([output_dir]).ok is True
