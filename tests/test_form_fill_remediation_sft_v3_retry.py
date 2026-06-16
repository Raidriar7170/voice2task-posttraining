from pathlib import Path

import pytest

from voice2task.io import read_json
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = (
    REPO_ROOT
    / "reports"
    / "public-sample"
    / "a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery"
)


def test_form_fill_sft_v3_retry_evidence_records_partial_improvement_without_recovery_claim() -> None:
    evidence = read_json(EVIDENCE_DIR / "form_fill_remediation_sft_v3_retry.json")
    manifest = read_json(EVIDENCE_DIR / "manifest.json")
    leak_scan = read_json(EVIDENCE_DIR / "leak_scan_result.json")
    report = (EVIDENCE_DIR / "report.md").read_text(encoding="utf-8")

    assert evidence["evidence_kind"] == "a100_form_fill_remediation_sft_v3_retry_after_ssh_recovery"
    assert evidence["run_status"] == "observed"
    assert evidence["dataset_manifest_id"] == "public-sample-20260616T074315Z"
    assert evidence["overall_interpretation"] == "form_fill_sft_v3_partial_improvement_with_safety_regression_risk"

    training = evidence["training_metadata"]
    assert training["training_status"] == "training_completed"
    assert training["training_rows_used"] == 114
    assert training["form_fill_remediation_train_rows"] == 21
    assert training["adapter_copied_to_git"] is False
    assert training["checkpoint_copied_to_git"] is False
    assert training["private_override_copied_to_git"] is False

    dev = evidence["split_results"]["dev"]
    test = evidence["split_results"]["test"]
    assert dev["prediction_count"] == 69
    assert test["prediction_count"] == 69
    assert dev["json_valid_rate"] == 1.0
    assert test["json_valid_rate"] == 1.0
    assert dev["contract_exact_match"] == pytest.approx(0.463768115942029)
    assert dev["slot_f1"] == pytest.approx(0.5652173913043478)
    assert dev["safety_recall"] == pytest.approx(0.5555555555555556)
    assert test["contract_exact_match"] == pytest.approx(0.34782608695652173)
    assert test["slot_f1"] == pytest.approx(0.49758454106280187)
    assert test["safety_recall"] == pytest.approx(1.0)

    comparison = evidence["comparison"]
    assert comparison["dev"]["contract_exact_match"]["delta"] == pytest.approx(0.15942028985507245)
    assert comparison["dev"]["slot_f1"]["delta"] == pytest.approx(0.1739130434782608)
    assert comparison["dev"]["safety_recall"]["delta"] == pytest.approx(-0.11111111111111105)
    assert comparison["test"]["contract_exact_match"]["delta"] == pytest.approx(0.0579710144927536)

    claims = evidence["claims"]
    assert claims["training_performed"] is True
    assert claims["held_out_generalization_recovered"] is False
    assert claims["model_recovery_claim"] is False
    assert claims["production_readiness_claim"] is False
    assert claims["adapter_release"] is False
    assert claims["checkpoint_release"] is False
    assert claims["soft_slot_f1_primary_metric"] is False
    assert claims["safety_regression_risk_observed"] is True

    assert manifest["overall_interpretation"] == evidence["overall_interpretation"]
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert "not a model recovery or production-readiness result" in report
    assert scan_paths([EVIDENCE_DIR]).ok is True
