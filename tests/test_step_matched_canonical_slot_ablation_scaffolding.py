from __future__ import annotations

import json
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"
HELPER_PATH = REPO_ROOT / "scripts" / "step_matched_canonical_slot_ablation_report.py"


def _load_helper():
    assert HELPER_PATH.exists(), "step-matched report helper is missing"
    spec = importlib.util.spec_from_file_location("step_matched_canonical_slot_ablation_report", HELPER_PATH)
    assert spec is not None and spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def _read_config(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))


def test_step_matched_training_configs_hold_causal_invariants() -> None:
    helper = _load_helper()
    control = _read_config("sft-a100-step-matched-canonical-slot-control.json")
    treatment = _read_config("sft-a100-step-matched-canonical-slot-treatment.json")

    invariant_keys = [
        "base_model",
        "lora",
        "learning_rate",
        "max_steps",
        "scheduler_step_count",
        "per_device_train_batch_size",
        "gradient_accumulation_steps",
        "seed",
        "max_seq_length",
        "logging_steps",
        "save_strategy",
        "trainer",
        "prompt_template_id",
        "tokenizer_policy",
        "decoding_policy_id",
        "evaluator_id",
    ]
    for key in invariant_keys:
        assert control[key] == treatment[key]

    assert control["step_matched_canonical_slot_ablation"] is True
    assert treatment["step_matched_canonical_slot_ablation"] is True
    assert control["paired_control"] is True
    assert control["paired_treatment"] is False
    assert treatment["paired_control"] is False
    assert treatment["paired_treatment"] is True
    assert control["dataset_manifest_id"] == "public-sample-20260617T152259Z"
    assert treatment["dataset_manifest_id"] == "public-sample-20260619T090925Z"
    assert control["expected_train_sft_rows"] == 261
    assert treatment["expected_train_sft_rows"] == 282
    assert control["max_steps"] == 3132
    assert control["max_steps"] > 0
    assert control["max_steps"] == control["scheduler_step_count"]
    assert control["step_budget"]["source_type"] == "reconstructed_from_prior_control_config"
    assert control["step_budget"]["prior_control_expected_train_sft_rows"] == 261
    assert control["step_budget"]["prior_control_num_train_epochs"] == 12
    assert control["step_budget"]["reconstructed_optimizer_steps"] == 3132
    assert treatment["step_budget"] == control["step_budget"]
    assert control["target_token_exposure_policy"] == "record_only_not_matched"
    assert treatment["target_token_exposure_policy"] == "record_only_not_matched"
    assert control["dpo_or_grpo_allowed"] is False
    assert treatment["dpo_or_grpo_allowed"] is False
    assert "<a100_project_root>" in control["output_root"]
    assert "<a100_project_root>" in treatment["output_root"]

    serialized = json.dumps({"control": control, "treatment": treatment}, sort_keys=True)
    helper.assert_public_safe_text(serialized)


def test_step_matched_prediction_configs_share_frozen_eval_policy() -> None:
    helper = _load_helper()
    names = [
        "sft-a100-step-matched-canonical-slot-control-dev-prediction.json",
        "sft-a100-step-matched-canonical-slot-control-test-prediction.json",
        "sft-a100-step-matched-canonical-slot-treatment-dev-prediction.json",
        "sft-a100-step-matched-canonical-slot-treatment-test-prediction.json",
    ]
    configs = {name: _read_config(name) for name in names}

    first = configs[names[0]]
    for config in configs.values():
        for key in [
            "base_model",
            "max_new_tokens",
            "model_source",
            "schema_retry_enabled",
            "prompt_template_id",
            "tokenizer_policy",
            "decoding_policy_id",
            "evaluator_id",
            "target_dataset_manifest_id",
        ]:
            assert config[key] == first[key]
        assert config["step_matched_canonical_slot_ablation"] is True
        assert config["frozen_dev_test_boundary"] is True
        assert config["allow_private_prediction"] is True
        assert config["generalization_claim"] is False
        assert config["prediction_artifact_policy"].startswith("commit_only_sanitized")
        assert "<a100_project_root>" in config["adapter_path"]
        assert config["dpo_or_grpo_allowed"] is False

    assert configs[names[0]]["prediction_split"] == "dev"
    assert configs[names[1]]["prediction_split"] == "test"
    assert configs[names[2]]["prediction_split"] == "dev"
    assert configs[names[3]]["prediction_split"] == "test"
    assert configs[names[0]]["source_adapter_dataset_manifest_id"] == "public-sample-20260617T152259Z"
    assert configs[names[2]]["source_adapter_dataset_manifest_id"] == "public-sample-20260619T090925Z"

    serialized = json.dumps(configs, sort_keys=True)
    helper.assert_public_safe_text(serialized)


def test_step_matched_required_artifact_contract_uses_public_evidence_root() -> None:
    helper = _load_helper()
    assert helper.EVIDENCE_ROOT == Path("reports/public-sample/step-matched-canonical-slot-ablation")
    assert helper.REQUIRED_ARTIFACTS == (
        "boundary-verification.json",
        "control/config.json",
        "control/training-summary.json",
        "control/dev-metrics.json",
        "control/test-metrics.json",
        "treatment/config.json",
        "treatment/training-summary.json",
        "treatment/dev-metrics.json",
        "treatment/test-metrics.json",
        "paired-row-analysis.json",
        "family-level-deltas.json",
        "bootstrap-analysis.json",
        "comparison.json",
        "comparison.md",
        "decision.md",
    )
    assert helper.REQUIRED_METRICS == (
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


def test_step_matched_pilot_gate_labels_are_exact_and_thresholded() -> None:
    helper = _load_helper()
    assert helper.DECISION_LABELS == (
        "PASS_STEP_MATCHED_PILOT",
        "POSITIVE_BUT_INCONCLUSIVE",
        "NO_CANONICAL_DATA_SIGNAL",
        "REGRESSION_OR_GUARDRAIL_FAILURE",
    )

    passing = {
        "dev": {
            "slot_value_exact_f1": 0.03,
            "executable_contract_pass_rate": 0.02,
            "safety_recall": 0.0,
            "unsafe_false_negative_rate": 0.0,
            "requires_confirmation_accuracy": -0.01,
            "schema_validity": 0.0,
            "json_valid_rate": 0.0,
        },
        "test": {
            "slot_value_exact_f1": 0.031,
            "executable_contract_pass_rate": 0.021,
            "safety_recall": 0.0,
            "unsafe_false_negative_rate": -0.01,
            "requires_confirmation_accuracy": 0.0,
            "schema_validity": 0.0,
            "json_valid_rate": 0.0,
        },
    }
    assert helper.decide_pilot_gate(passing)["decision_label"] == "PASS_STEP_MATCHED_PILOT"

    partial = json.loads(json.dumps(passing))
    partial["test"]["slot_value_exact_f1"] = 0.027
    assert helper.decide_pilot_gate(partial)["decision_label"] == "POSITIVE_BUT_INCONCLUSIVE"

    no_signal = json.loads(json.dumps(passing))
    no_signal["dev"]["slot_value_exact_f1"] = 0.0
    no_signal["test"]["slot_value_exact_f1"] = 0.0
    no_signal["dev"]["executable_contract_pass_rate"] = 0.0
    no_signal["test"]["executable_contract_pass_rate"] = 0.0
    assert helper.decide_pilot_gate(no_signal)["decision_label"] == "NO_CANONICAL_DATA_SIGNAL"

    regression = json.loads(json.dumps(passing))
    regression["dev"]["safety_recall"] = -0.001
    assert helper.decide_pilot_gate(regression)["decision_label"] == "REGRESSION_OR_GUARDRAIL_FAILURE"

    schema_drop = json.loads(json.dumps(passing))
    schema_drop["test"]["schema_validity"] = -0.001
    assert helper.decide_pilot_gate(schema_drop)["decision_label"] == "REGRESSION_OR_GUARDRAIL_FAILURE"


def test_blocked_artifact_is_public_safe_and_does_not_fabricate_metrics() -> None:
    helper = _load_helper()
    artifact = helper.build_blocked_artifact(
        blocker="previous control optimizer-step budget could not be verified",
        evidence_gaps=["trainer_state_missing", "training_summary_missing"],
    )

    assert artifact["phase"] == "run-step-matched-canonical-slot-ablation"
    assert artifact["status"] == "blocked"
    assert artifact["metrics_available"] is False
    assert "metrics" not in artifact
    assert "comparison" not in artifact
    assert artifact["decision_label"] is None
    assert artifact["claims"]["metrics_fabricated"] is False
    assert artifact["claims"]["training_performed"] is False
    assert artifact["claims"]["dpo_or_grpo_run_performed"] is False

    helper.assert_public_safe_text(json.dumps(artifact, sort_keys=True))
