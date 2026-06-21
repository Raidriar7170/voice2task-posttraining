from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from voice2task.leak_scan import scan_paths
from voice2task.schemas import as_contract

REPO_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_SCRIPT = REPO_ROOT / "scripts" / "recover_step_matched_projection_inputs.py"
RAW_INPUTS = REPO_ROOT / "reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs"
COMMITTED_BOUNDARY = REPO_ROOT / "reports/public-sample/step-matched-canonical-slot-ablation/boundary-verification.json"
COMMITTED_COMPARISON = REPO_ROOT / "reports/public-sample/step-matched-canonical-slot-ablation/comparison.json"

EXPECTED_PREDICTION_FILES = {
    ("control", "dev"): RAW_INPUTS / "control/dev_predictions.jsonl",
    ("control", "test"): RAW_INPUTS / "control/test_predictions.jsonl",
    ("treatment", "dev"): RAW_INPUTS / "treatment/dev_predictions.jsonl",
    ("treatment", "test"): RAW_INPUTS / "treatment/test_predictions.jsonl",
}
EXPECTED_GOLD_FILES = {
    "dev": RAW_INPUTS / "gold/dev_gold.jsonl",
    "test": RAW_INPUTS / "gold/test_gold.jsonl",
}
REQUIRED_METRICS = (
    "contract_exact_match_strict",
    "strict_slot_f1",
    "slot_value_exact_f1",
    "slot_value_normalized_f1",
    "executable_contract_pass_rate",
    "schema_validity",
    "json_valid_rate",
    "route_accuracy",
    "task_type_accuracy",
    "safety_recall",
    "unsafe_false_negative_rate",
    "unsafe_false_positive_rate",
    "requires_confirmation_accuracy",
    "refusal_or_clarify_accuracy",
)


def _load_recovery_module():
    assert RECOVERY_SCRIPT.exists(), "recovery script must be committed"
    spec = importlib.util.spec_from_file_location("recover_step_matched_projection_inputs", RECOVERY_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _adapter_metadata(*, arm: str) -> dict[str, Any]:
    return {
        "adapter_release_status": "not_released",
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "dataset_load": {
            "manifest_id": (
                "public-sample-20260617T152259Z"
                if arm == "control"
                else "public-sample-20260619T090925Z"
            )
        },
        "training_budget": {"effective_batch_size": 1, "observed_optimizer_steps": 3132},
        "training_rows_used": 261 if arm == "control" else 282,
        "training_status": "training_completed",
    }


def test_recovery_helper_fail_closes_duplicate_missing_boundary_and_metric_mismatch() -> None:
    recovery = _load_recovery_module()

    rows = [
        {"sample_id": "a", "split": "dev", "input_hash": "ih-a", "gold_contract": {"x": 1}},
        {"sample_id": "a", "split": "dev", "input_hash": "ih-a", "gold_contract": {"x": 1}},
    ]
    assert "duplicate_sample_ids" in recovery.boundary_blocking_reasons(
        control_rows=rows,
        treatment_rows=rows[:1],
        gold_rows=rows[:1],
        expected_count=2,
        expected_gold_hash="not-used-after-duplicate",
    )

    assert recovery.metric_matches({"x": 1.0}, {"x": 1.0000000000000004}, tolerance=1e-12) is True
    assert recovery.metric_matches({"x": 1.0}, {"x": 1.001}, tolerance=1e-12) is False

    blocked = recovery.build_blocked_payload(
        decision_label="RECOVERY_INVALID_METRIC_MISMATCH",
        blocking_reasons=["metric_mismatch"],
    )
    assert blocked["projection_inputs_ready"] is False
    assert blocked["claims"]["contract_v2_projection_run"] is False
    assert blocked["claims"]["prediction_repair_performed"] is False


def test_source_artifact_validation_and_blocked_cleanup_are_fail_closed(tmp_path: Path) -> None:
    recovery = _load_recovery_module()
    bundle, load_reason = recovery.load_source_bundle_or_blocker(tmp_path / "missing", "control", "dev")

    assert bundle is None
    assert load_reason == "control_dev_source_bundle_unavailable"
    assert recovery.decision_for_blocking_reasons([load_reason]) == "RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE"
    assert (
        recovery.decision_for_blocking_reasons(["dev_gold_hash_mismatch"])
        == "RECOVERY_INVALID_BOUNDARY_MISMATCH"
    )

    malformed_reasons = recovery.source_artifact_blocking_reasons(
        expected_ids=["a"],
        prediction_rows=[{"id": "a"}],
        raw_summary_rows=[{"id": "a"}],
    )
    assert "invalid_prediction_rows" in malformed_reasons
    assert "invalid_raw_summary_rows" in malformed_reasons
    assert recovery.decision_for_blocking_reasons(malformed_reasons) == "RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE"

    non_object_reasons = recovery.source_artifact_blocking_reasons(
        expected_ids=[""],
        prediction_rows=[[]],
        raw_summary_rows=[None],
    )
    assert "invalid_prediction_rows" in non_object_reasons
    assert "invalid_raw_summary_rows" in non_object_reasons

    reasons = recovery.source_artifact_blocking_reasons(
        expected_ids=["a", "b"],
        prediction_rows=[{"id": "a", "prediction": {"task_type": "search"}}],
        raw_summary_rows=[{"id": "a", "decoded_sha256": "abc"}],
    )

    assert "missing_prediction_rows" in reasons
    assert "missing_raw_summary_rows" in reasons

    output_dir = tmp_path / "raw-inputs"
    stale_files = [
        output_dir / "boundary-verification.json",
        output_dir / "metric-reproduction.json",
        output_dir / "recovery-summary.md",
        output_dir / "control/dev_predictions.jsonl",
        output_dir / "gold/dev_gold.jsonl",
    ]
    for path in stale_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale", encoding="utf-8")

    recovery._write_blocked(
        output_dir,
        decision_label="RECOVERY_INVALID_BOUNDARY_MISMATCH",
        blocking_reasons=["missing_prediction_rows"],
    )

    assert _read_json(output_dir / "blocked.json")["projection_inputs_ready"] is False
    assert _read_json(output_dir / "artifact-manifest.json")["decision_label"] == "RECOVERY_INVALID_BOUNDARY_MISMATCH"
    for path in stale_files:
        assert not path.exists()


def test_recover_writes_blocked_when_source_bundle_is_unavailable(tmp_path: Path) -> None:
    recovery = _load_recovery_module()
    control_metadata = tmp_path / "control_metadata.json"
    treatment_metadata = tmp_path / "treatment_metadata.json"
    control_adapter_config = tmp_path / "control_adapter_config.json"
    treatment_adapter_config = tmp_path / "treatment_adapter_config.json"
    _write_json(control_metadata, _adapter_metadata(arm="control"))
    _write_json(treatment_metadata, _adapter_metadata(arm="treatment"))
    _write_json(control_adapter_config, {"peft_type": "LORA"})
    _write_json(treatment_adapter_config, {"peft_type": "LORA"})

    result = recovery.recover(
        SimpleNamespace(
            source_root=tmp_path / "missing-source",
            output_dir=tmp_path / "raw-inputs",
            run_id="step-matched-canonical-slot-ablation-20260620T000000Z",
            control_adapter_metadata=control_metadata,
            treatment_adapter_metadata=treatment_metadata,
            control_adapter_config=control_adapter_config,
            treatment_adapter_config=treatment_adapter_config,
            control_adapter_model_sha256=recovery.EXPECTED_CONTROL_ADAPTER_HASH,
            treatment_adapter_model_sha256=recovery.EXPECTED_TREATMENT_ADAPTER_HASH,
        )
    )

    assert result["ok"] is False
    assert result["decision_label"] == "RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE"
    assert _read_json(tmp_path / "raw-inputs/blocked.json")["decision_label"] == "RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE"
    assert not (tmp_path / "raw-inputs/control").exists()
    assert not (tmp_path / "raw-inputs/metric-reproduction.json").exists()


def test_recover_writes_blocked_when_adapter_evidence_is_unavailable(tmp_path: Path) -> None:
    recovery = _load_recovery_module()
    result = recovery.recover(
        SimpleNamespace(
            source_root=tmp_path / "missing-source",
            output_dir=tmp_path / "raw-inputs",
            run_id="step-matched-canonical-slot-ablation-20260620T000000Z",
            control_adapter_metadata=tmp_path / "missing-control-metadata.json",
            treatment_adapter_metadata=tmp_path / "missing-treatment-metadata.json",
            control_adapter_config=tmp_path / "missing-control-config.json",
            treatment_adapter_config=tmp_path / "missing-treatment-config.json",
            control_adapter_model_sha256=recovery.EXPECTED_CONTROL_ADAPTER_HASH,
            treatment_adapter_model_sha256=recovery.EXPECTED_TREATMENT_ADAPTER_HASH,
        )
    )

    assert result["ok"] is False
    assert result["decision_label"] == "RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE"
    blocked = _read_json(tmp_path / "raw-inputs/blocked.json")
    assert "control_adapter_identity_unverified" in blocked["blocking_reasons"]
    assert "treatment_adapter_identity_unverified" in blocked["blocking_reasons"]


def test_recovered_raw_inputs_artifact_contract_is_complete_public_safe_and_projection_ready() -> None:
    recovery = _load_recovery_module()
    manifest = _read_json(RAW_INPUTS / "artifact-manifest.json")
    boundary = _read_json(RAW_INPUTS / "boundary-verification.json")
    metric_reproduction = _read_json(RAW_INPUTS / "metric-reproduction.json")
    committed_boundary = _read_json(COMMITTED_BOUNDARY)

    assert not (RAW_INPUTS / "blocked.json").exists()
    assert manifest["change_id"] == "recover-step-matched-projection-inputs"
    assert manifest["decision_label"] == "RECOVERED_FROM_EXISTING_ARTIFACTS"
    assert manifest["recovery_method"] == "recovered_from_existing_artifacts"
    assert manifest["projection_inputs_ready"] is True
    assert manifest["claims"]["training_performed"] is False
    assert manifest["claims"]["prediction_only_reproduction_performed"] is False
    assert manifest["claims"]["contract_v2_projection_run"] is False
    assert manifest["claims"]["prediction_repair_performed"] is False
    assert manifest["control_adapter_identity_hash"] == (
        "27aaffc10f39d497af08bfa35d4f914bd198dafc514798449e0e5292b56a6359"
    )
    assert manifest["treatment_adapter_identity_hash"] == (
        "a23c54e7c157de2dd80c88777ac752272803096f7e9a19aa69669d13c8eb9238"
    )
    assert manifest["dev_row_count"] == 207
    assert manifest["test_row_count"] == 207
    assert manifest["dev_gold_hash"] == committed_boundary["splits"]["dev"]["gold_contract_hash"]["control"]
    assert manifest["test_gold_hash"] == committed_boundary["splits"]["test"]["gold_contract_hash"]["control"]
    assert manifest["retention_hook"]["status"] == "verified_existing_prediction_sidecars"

    assert boundary["comparison_allowed"] is True
    assert boundary["blocking_reasons"] == []
    assert boundary["control_treatment_ids_match"] is True
    assert boundary["control_gold_ids_match"] is True
    assert boundary["treatment_gold_ids_match"] is True
    assert boundary["dev_gold_hash_match"] is True
    assert boundary["test_gold_hash_match"] is True
    assert boundary["input_hash_match"] is True
    assert boundary["control_adapter_verified"] is True
    assert boundary["treatment_adapter_verified"] is True
    assert boundary["config_match"] is True
    assert boundary["prompt_match"] is True
    assert boundary["evaluator_match"] is True

    assert metric_reproduction["status"] == "reproduced"
    assert metric_reproduction["decision_label"] == "RECOVERED_FROM_EXISTING_ARTIFACTS"
    for split in ("dev", "test"):
        for arm in ("control", "treatment"):
            payload = metric_reproduction["splits"][split][arm]
            assert payload["matches_committed"] is True
            assert set(REQUIRED_METRICS).issubset(payload["metrics"])

    all_paths = [
        RAW_INPUTS / "artifact-manifest.json",
        RAW_INPUTS / "boundary-verification.json",
        RAW_INPUTS / "metric-reproduction.json",
        RAW_INPUTS / "recovery-summary.md",
        *EXPECTED_GOLD_FILES.values(),
        *EXPECTED_PREDICTION_FILES.values(),
    ]
    assert scan_paths(all_paths, max_public_jsonl_rows=500).ok is True
    serialized = json.dumps(
        {
            "manifest": manifest,
            "boundary": boundary,
            "metric_reproduction": metric_reproduction,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized

    for split, path in EXPECTED_GOLD_FILES.items():
        rows = _read_jsonl(path)
        assert len(rows) == 207
        assert len({row["sample_id"] for row in rows}) == 207
        assert {row["split"] for row in rows} == {split}
        for row in rows:
            assert {
                "sample_id",
                "split",
                "input_text",
                "input_hash",
                "gold_contract",
                "gold_hash",
                "manifest_id",
            } <= set(row)
            as_contract(row["gold_contract"])
            assert row["gold_hash"] == recovery.sha256_text(recovery.canonical_json(row["gold_contract"]))

    dev_ids = {row["sample_id"] for row in _read_jsonl(EXPECTED_GOLD_FILES["dev"])}
    test_ids = {row["sample_id"] for row in _read_jsonl(EXPECTED_GOLD_FILES["test"])}
    assert dev_ids.isdisjoint(test_ids)

    for (arm, split), path in EXPECTED_PREDICTION_FILES.items():
        rows = _read_jsonl(path)
        assert len(rows) == 207
        assert len({row["sample_id"] for row in rows}) == 207
        assert {row["run_role"] for row in rows} == {arm}
        assert {row["split"] for row in rows} == {split}
        for row in rows:
            assert {
                "sample_id",
                "split",
                "input_text",
                "input_hash",
                "gold_contract",
                "prediction_contract",
                "raw_model_output",
                "parse_status",
                "run_role",
                "run_id",
                "manifest_id",
                "config_hash",
                "prompt_hash",
                "model_output_hash",
            } <= set(row)
            as_contract(row["gold_contract"])
            as_contract(row["prediction_contract"])
            assert row["parse_status"] == "valid"
            assert row["model_output_hash"] == recovery.sha256_text(row["raw_model_output"])
