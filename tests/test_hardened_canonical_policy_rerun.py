import json
from pathlib import Path

import pytest

from voice2task.cli import report as report_cli
from voice2task.io import read_json
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SAMPLE_DIR = REPO_ROOT / "data" / "public-samples"
PRIOR_MERGED_MANIFEST = (
    REPO_ROOT / "reports" / "public-sample" / "a100-merged-slot-value-heldout-eval" / "manifest.json"
)
HARDENED_EVIDENCE_DIR = REPO_ROOT / "reports" / "public-sample" / "a100-hardened-canonical-policy-rerun"
HARDENED_OBSERVED_EVIDENCE_DIR = (
    REPO_ROOT / "reports" / "public-sample" / "a100-hardened-canonical-policy-rerun-observed"
)
HARDENED_CONFIGS = {
    split: REPO_ROOT / "configs" / f"sft-a100-hardened-canonical-policy-{split}-prediction.json"
    for split in ("train", "dev", "test")
}


def _current_public_manifest() -> dict:
    return read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")


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


def _prediction_metadata(split: str, count: int, private_root: str) -> dict:
    return {
        "adapter_path": f"{private_root}/runs/a100-merged-slot-value-heldout-eval/adapter",
        "dataset_manifest_id": _current_public_manifest()["manifest_id"],
        "prediction_count": count,
        "prediction_source_kind": "private_a100_adapter",
        "prediction_split": split,
        "prediction_status": "private_adapter_predictions_written",
        "prompt_constraints": {
            "clarify_ambiguity_canonical_phrase_visible": True,
            "unsafe_payment_canonical_command_visible": True,
        },
    }


def _observed_cli_args(
    tmp_path: Path,
    *,
    prior_manifest: Path = PRIOR_MERGED_MANIFEST,
    output_dir: Path | None = None,
) -> list[str]:
    private_root = "/mnt" + "/data/minghongsun/private"
    metrics_paths = {
        "train": _write_json(tmp_path / "train_metrics.json", _metrics_payload(1.0, 1.0)),
        "dev": _write_json(tmp_path / "dev_metrics.json", _metrics_payload(1.0, 1.0)),
        "test": _write_json(tmp_path / "test_metrics.json", _metrics_payload(1.0, 1.0)),
    }
    metadata_paths = {
        split: _write_json(tmp_path / f"{split}_metadata.raw.json", _prediction_metadata(split, count, private_root))
        for split, count in _current_public_manifest()["split_counts"].items()
    }
    return [
        "hardened-canonical-policy-rerun",
        "--public-manifest",
        (PUBLIC_SAMPLE_DIR / "manifest_public_sample.json").as_posix(),
        "--prior-merged-manifest",
        prior_manifest.as_posix(),
        "--train-metrics",
        metrics_paths["train"].as_posix(),
        "--dev-metrics",
        metrics_paths["dev"].as_posix(),
        "--test-metrics",
        metrics_paths["test"].as_posix(),
        "--train-prediction-metadata",
        metadata_paths["train"].as_posix(),
        "--dev-prediction-metadata",
        metadata_paths["dev"].as_posix(),
        "--test-prediction-metadata",
        metadata_paths["test"].as_posix(),
        "--output",
        (output_dir or (tmp_path / "hardened-report")).as_posix(),
    ]


def test_hardened_canonical_policy_configs_are_prediction_only_and_public_safe() -> None:
    manifest = read_json(PUBLIC_SAMPLE_DIR / "manifest_public_sample.json")
    manifest_id = manifest["manifest_id"]
    legacy_manifest_id = read_json(HARDENED_OBSERVED_EVIDENCE_DIR / "manifest.json")["dataset_manifest_id"]

    for split, path in HARDENED_CONFIGS.items():
        config = read_json(path)
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

        assert config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
        assert config["dataset_manifest_id"] == legacy_manifest_id
        assert legacy_manifest_id != manifest_id
        assert config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["prediction_only"] is True
        assert config["hardened_canonical_policy"] is True
        assert config["source_adapter_runtime"] == "a100-merged-slot-value-heldout-eval"
        assert config["adapter_path"] == "<a100_project_root>/runs/a100-merged-slot-value-heldout-eval/adapter"
        assert config["evidence_output_dir"] == (
            f"<a100_project_root>/evidence/a100-hardened-canonical-policy-rerun/{split}"
        )
        assert "allow_heavy_training" not in config
        assert "adapter_output_dir" not in config
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized

    assert scan_paths(list(HARDENED_CONFIGS.values())).ok is True


def test_hardened_canonical_policy_report_cli_writes_observed_public_safe_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    output_dir = tmp_path / "hardened-report"

    assert report_cli.main(_observed_cli_args(tmp_path)) == 0

    payload = json.loads(capsys.readouterr().out)
    evidence = read_json(output_dir / "hardened_canonical_policy_rerun.json")
    manifest = read_json(output_dir / "manifest.json")
    report = (output_dir / "report.md").read_text(encoding="utf-8")
    serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True)

    assert payload["ok"] is True
    assert payload["summary"]["rerun_status"] == "observed"
    assert evidence["evidence_kind"] == "a100_hardened_canonical_policy_rerun"
    assert evidence["rerun_status"] == "observed"
    assert evidence["source_adapter_runtime"] == "a100-merged-slot-value-heldout-eval"
    assert evidence["claims"]["training_performed"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["private_corpus_generalization_claim"] is False
    assert evidence["claims"]["soft_slot_f1_primary_metric"] is False
    assert evidence["prompt_policy_by_split"]["dev"]["hardened_canonical_policy_visible"] is True
    assert evidence["comparison"]["prior_merged_slot_value_exact"] == {"dev": 0.5, "test": 5 / 6, "train": 1.0}
    assert evidence["comparison"]["hardened_canonical_policy_exact"] == {"dev": 1.0, "test": 1.0, "train": 1.0}
    assert evidence["comparison"]["dev_test_exact_delta"]["dev"] == 0.5
    assert manifest["evidence_kind"] == "a100_hardened_canonical_policy_rerun"
    assert manifest["diagnostic_artifacts"]["evidence"] == "hardened-report/hardened_canonical_policy_rerun.json"
    assert "a100-merged-slot-value-heldout-eval/merged_slot_value_heldout_eval.json" not in json.dumps(
        manifest["diagnostic_artifacts"],
        ensure_ascii=False,
    )
    assert "prediction-only" in report
    assert "strict `contract_exact_match` remains primary" in report
    assert "/mnt/data/" not in serialized
    assert scan_paths([output_dir]).ok is True


def test_hardened_canonical_policy_report_diagnostic_artifacts_follow_output_dir(
    tmp_path: Path,
    capsys,
) -> None:
    output_dir = tmp_path / "custom-observed-report"

    assert report_cli.main(_observed_cli_args(tmp_path, output_dir=output_dir)) == 0

    json.loads(capsys.readouterr().out)
    manifest = read_json(output_dir / "manifest.json")

    assert manifest["diagnostic_artifacts"]["evidence"] == (
        "custom-observed-report/hardened_canonical_policy_rerun.json"
    )
    assert manifest["diagnostic_artifacts"]["manifest"] == "custom-observed-report/manifest.json"
    assert manifest["diagnostic_artifacts"]["report"] == "custom-observed-report/report.md"
    assert "a100-hardened-canonical-policy-rerun/hardened_canonical_policy_rerun.json" not in json.dumps(
        manifest["diagnostic_artifacts"],
        ensure_ascii=False,
    )
    assert scan_paths([output_dir]).ok is True


def test_hardened_canonical_policy_report_diagnostic_artifacts_keep_nested_relative_output_dir(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output_dir = Path("nested") / "observed-report"

    assert report_cli.main(_observed_cli_args(tmp_path, output_dir=output_dir)) == 0

    json.loads(capsys.readouterr().out)
    manifest = read_json(output_dir / "manifest.json")

    assert manifest["diagnostic_artifacts"]["evidence"] == (
        "nested/observed-report/hardened_canonical_policy_rerun.json"
    )
    assert manifest["diagnostic_artifacts"]["manifest"] == "nested/observed-report/manifest.json"
    assert manifest["diagnostic_artifacts"]["report"] == "nested/observed-report/report.md"
    assert scan_paths([output_dir]).ok is True


def test_hardened_canonical_policy_report_rejects_bad_prior_manifest(tmp_path: Path) -> None:
    bad_prior = _write_json(
        tmp_path / "bad_prior_manifest.json",
        {
            "evidence_kind": "a100_hardened_canonical_policy_rerun",
            "comparison": {"merged_slot_value_exact": {"dev": 0.5, "test": 5 / 6, "train": 1.0}},
        },
    )

    with pytest.raises(ValueError, match="prior merged manifest"):
        report_cli.main(_observed_cli_args(tmp_path, prior_manifest=bad_prior))


def test_hardened_canonical_policy_report_fails_closed_when_prompt_flags_missing(tmp_path: Path) -> None:
    private_root = "/mnt" + "/data/minghongsun/private"
    metrics_paths = {
        "train": _write_json(tmp_path / "train_metrics.json", _metrics_payload(1.0, 1.0)),
        "dev": _write_json(tmp_path / "dev_metrics.json", _metrics_payload(1.0, 1.0)),
        "test": _write_json(tmp_path / "test_metrics.json", _metrics_payload(1.0, 1.0)),
    }
    metadata_paths = {}
    for split, count in _current_public_manifest()["split_counts"].items():
        payload = _prediction_metadata(split, count, private_root)
        if split == "dev":
            payload["prompt_constraints"] = {}
        metadata_paths[split] = _write_json(tmp_path / f"{split}_metadata.raw.json", payload)

    assert (
        report_cli.main(
            [
                "hardened-canonical-policy-rerun",
                "--public-manifest",
                (PUBLIC_SAMPLE_DIR / "manifest_public_sample.json").as_posix(),
                "--prior-merged-manifest",
                PRIOR_MERGED_MANIFEST.as_posix(),
                "--train-metrics",
                metrics_paths["train"].as_posix(),
                "--dev-metrics",
                metrics_paths["dev"].as_posix(),
                "--test-metrics",
                metrics_paths["test"].as_posix(),
                "--train-prediction-metadata",
                metadata_paths["train"].as_posix(),
                "--dev-prediction-metadata",
                metadata_paths["dev"].as_posix(),
                "--test-prediction-metadata",
                metadata_paths["test"].as_posix(),
                "--output",
                (tmp_path / "hardened-report").as_posix(),
            ]
        )
        == 0
    )

    evidence = read_json(tmp_path / "hardened-report" / "hardened_canonical_policy_rerun.json")
    assert evidence["overall_interpretation"] == "hardened_canonical_policy_prompt_flags_missing"
    assert evidence["claims"]["hardened_prompt_policy_visible"] is False
    assert evidence["claims"]["public_sample_heldout_strict_exact_recovered"] is False
    assert evidence["claims"]["held_out_generalization_recovered"] is False


def test_hardened_canonical_policy_report_rejects_blocked_status_without_reason(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="blocked hardened-canonical-policy-rerun requires --blocked-reason"):
        report_cli.main(
            [
                "hardened-canonical-policy-rerun",
                "--public-manifest",
                (PUBLIC_SAMPLE_DIR / "manifest_public_sample.json").as_posix(),
                "--prior-merged-manifest",
                PRIOR_MERGED_MANIFEST.as_posix(),
                "--rerun-status",
                "blocked",
                "--output",
                (tmp_path / "blocked-report").as_posix(),
            ]
        )


def test_hardened_canonical_policy_report_rejects_wrong_split_metadata(tmp_path: Path) -> None:
    private_root = "/mnt" + "/data/minghongsun/private"
    metrics_paths = {
        "train": _write_json(tmp_path / "train_metrics.json", _metrics_payload(1.0, 1.0)),
        "dev": _write_json(tmp_path / "dev_metrics.json", _metrics_payload(1.0, 1.0)),
        "test": _write_json(tmp_path / "test_metrics.json", _metrics_payload(1.0, 1.0)),
    }
    metadata_paths = {}
    for split, count in _current_public_manifest()["split_counts"].items():
        payload = _prediction_metadata(split, count, private_root)
        if split == "dev":
            payload["prediction_split"] = "test"
        metadata_paths[split] = _write_json(tmp_path / f"{split}_metadata.raw.json", payload)

    with pytest.raises(ValueError, match="prediction metadata split mismatch"):
        report_cli.main(
            [
                "hardened-canonical-policy-rerun",
                "--public-manifest",
                (PUBLIC_SAMPLE_DIR / "manifest_public_sample.json").as_posix(),
                "--prior-merged-manifest",
                PRIOR_MERGED_MANIFEST.as_posix(),
                "--train-metrics",
                metrics_paths["train"].as_posix(),
                "--dev-metrics",
                metrics_paths["dev"].as_posix(),
                "--test-metrics",
                metrics_paths["test"].as_posix(),
                "--train-prediction-metadata",
                metadata_paths["train"].as_posix(),
                "--dev-prediction-metadata",
                metadata_paths["dev"].as_posix(),
                "--test-prediction-metadata",
                metadata_paths["test"].as_posix(),
                "--output",
                (tmp_path / "hardened-report").as_posix(),
            ]
        )


def test_hardened_canonical_policy_report_cli_writes_blocked_public_safe_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    output_dir = tmp_path / "blocked-report"

    assert (
        report_cli.main(
            [
                "hardened-canonical-policy-rerun",
                "--public-manifest",
                (PUBLIC_SAMPLE_DIR / "manifest_public_sample.json").as_posix(),
                "--prior-merged-manifest",
                PRIOR_MERGED_MANIFEST.as_posix(),
                "--rerun-status",
                "blocked",
                "--blocked-reason",
                "ssh_unavailable",
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    evidence = read_json(output_dir / "hardened_canonical_policy_rerun.json")
    report = (output_dir / "report.md").read_text(encoding="utf-8")
    serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True)

    assert payload["ok"] is True
    assert payload["summary"]["rerun_status"] == "blocked"
    assert evidence["rerun_status"] == "blocked"
    assert evidence["blocked_reason"] == "ssh_unavailable"
    assert evidence["claims"]["training_performed"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["comparison"]["hardened_canonical_policy_exact"] == {}
    assert "Blocked before private prediction" in report
    assert "/mnt/data/" not in serialized
    assert scan_paths([output_dir]).ok is True


def test_committed_hardened_canonical_policy_rerun_evidence_is_bounded_and_public_safe() -> None:
    evidence = read_json(HARDENED_EVIDENCE_DIR / "hardened_canonical_policy_rerun.json")
    manifest = read_json(HARDENED_EVIDENCE_DIR / "manifest.json")

    assert evidence["evidence_kind"] == "a100_hardened_canonical_policy_rerun"
    assert evidence["dataset_manifest_id"] == "public-sample-20260615T040231Z"
    assert evidence["source_adapter_runtime"] == "a100-merged-slot-value-heldout-eval"
    assert evidence["rerun_status"] in {"observed", "blocked"}
    if evidence["rerun_status"] == "blocked":
        assert evidence["blocked_reason"] == "source_adapter_missing_on_a100"
        assert evidence["split_results"] == {}
        assert evidence["comparison"]["hardened_canonical_policy_exact"] == {}
    assert evidence["claims"]["training_performed"] is False
    assert evidence["claims"]["model_recovery_claim"] is False
    assert evidence["claims"]["adapter_release"] is False
    assert evidence["claims"]["checkpoint_release"] is False
    assert evidence["claims"]["private_corpus_generalization_claim"] is False
    assert evidence["claims"]["soft_slot_f1_primary_metric"] is False
    assert manifest["evidence_kind"] == "a100_hardened_canonical_policy_rerun"
    assert scan_paths([HARDENED_EVIDENCE_DIR]).ok is True


def test_committed_observed_hardened_rerun_does_not_overwrite_blocked_evidence() -> None:
    blocked_evidence = read_json(HARDENED_EVIDENCE_DIR / "hardened_canonical_policy_rerun.json")
    observed_evidence = read_json(HARDENED_OBSERVED_EVIDENCE_DIR / "hardened_canonical_policy_rerun.json")
    observed_manifest = read_json(HARDENED_OBSERVED_EVIDENCE_DIR / "manifest.json")

    assert blocked_evidence["rerun_status"] == "blocked"
    assert blocked_evidence["blocked_reason"] == "source_adapter_missing_on_a100"
    assert observed_evidence["rerun_status"] == "observed"
    assert observed_evidence["overall_interpretation"] == "hardened_canonical_policy_heldout_unchanged"
    assert observed_manifest["diagnostic_artifacts"]["evidence"] == (
        "reports/public-sample/a100-hardened-canonical-policy-rerun-observed/"
        "hardened_canonical_policy_rerun.json"
    )
    assert "a100-hardened-canonical-policy-rerun/hardened_canonical_policy_rerun.json" not in json.dumps(
        observed_manifest["diagnostic_artifacts"],
        ensure_ascii=False,
    )
    assert scan_paths([HARDENED_OBSERVED_EVIDENCE_DIR]).ok is True
