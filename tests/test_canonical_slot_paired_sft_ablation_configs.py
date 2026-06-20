from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"
REPORT_DIR = REPO_ROOT / "reports" / "public-sample" / "canonical-slot-paired-sft-ablation"


def _read_config(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))


def test_canonical_slot_paired_sft_training_configs_hold_invariants():
    control = _read_config("sft-a100-canonical-slot-paired-control.json")
    treatment = _read_config("sft-a100-canonical-slot-paired-treatment.json")

    invariant_keys = [
        "base_model",
        "lora",
        "learning_rate",
        "num_train_epochs",
        "max_steps",
        "per_device_train_batch_size",
        "gradient_accumulation_steps",
        "seed",
        "max_seq_length",
        "logging_steps",
        "save_strategy",
        "trainer",
    ]
    for key in invariant_keys:
        assert control[key] == treatment[key]

    assert control["dataset_manifest_id"] == "public-sample-20260617T152259Z"
    assert treatment["dataset_manifest_id"] == "public-sample-20260619T090925Z"
    assert control["expected_train_sft_rows"] == 261
    assert treatment["expected_train_sft_rows"] == 282
    assert control["paired_control"] is True
    assert treatment["paired_treatment"] is True
    assert control["dpo_or_grpo_allowed"] is False
    assert treatment["dpo_or_grpo_allowed"] is False
    assert "<a100_project_root>" in control["output_root"]
    assert "<a100_project_root>" in treatment["output_root"]


def test_canonical_slot_paired_prediction_configs_share_decoding_policy():
    configs = {
        name: _read_config(name)
        for name in [
            "sft-a100-canonical-slot-paired-control-dev-prediction.json",
            "sft-a100-canonical-slot-paired-control-test-prediction.json",
            "sft-a100-canonical-slot-paired-treatment-dev-prediction.json",
            "sft-a100-canonical-slot-paired-treatment-test-prediction.json",
        ]
    }

    invariant_keys = ["base_model", "max_new_tokens", "model_source", "schema_retry_enabled"]
    first = next(iter(configs.values()))
    for config in configs.values():
        for key in invariant_keys:
            assert config[key] == first[key]
        assert config["allow_private_prediction"] is True
        assert config["generalization_claim"] is False
        assert config["prediction_artifact_policy"].startswith("commit_only_sanitized")
        assert "<a100_project_root>" in config["adapter_path"]

    assert configs["sft-a100-canonical-slot-paired-control-dev-prediction.json"]["prediction_split"] == "dev"
    assert configs["sft-a100-canonical-slot-paired-control-test-prediction.json"]["prediction_split"] == "test"
    assert configs["sft-a100-canonical-slot-paired-treatment-dev-prediction.json"]["prediction_split"] == "dev"
    assert configs["sft-a100-canonical-slot-paired-treatment-test-prediction.json"]["prediction_split"] == "test"
    assert configs["sft-a100-canonical-slot-paired-control-dev-prediction.json"][
        "source_adapter_dataset_manifest_id"
    ] == "public-sample-20260617T152259Z"
    assert configs["sft-a100-canonical-slot-paired-treatment-dev-prediction.json"][
        "source_adapter_dataset_manifest_id"
    ] == "public-sample-20260619T090925Z"


def test_canonical_slot_paired_public_artifacts_include_training_provenance():
    comparison = json.loads((REPORT_DIR / "comparison.json").read_text(encoding="utf-8"))
    assert comparison["dataset_manifest_id"] == "public-sample-20260619T090925Z"
    assert comparison["evaluation_manifest_id"] == "public-sample-20260619T090925Z"
    assert comparison["training_manifests"] == {
        "control": "public-sample-20260617T152259Z",
        "treatment": "public-sample-20260619T090925Z",
    }
    assert comparison["claims"]["prediction_repair_performed"] is False
    assert comparison["claims"]["schema_retry_boundary"] == (
        "generation_time_invalid_json_retry_only_no_posthoc_prediction_repair"
    )

    expected_rows = {"control": 261, "treatment": 282}
    for arm, manifest_id in comparison["training_manifests"].items():
        summary = json.loads((REPORT_DIR / arm / "training_summary.json").read_text(encoding="utf-8"))
        metrics = json.loads((REPORT_DIR / arm / "dev" / "metrics.json").read_text(encoding="utf-8"))
        assert summary["arm"] == arm
        assert summary["training_status"] == "training_completed"
        assert summary["training_manifest_id"] == manifest_id
        assert summary["evaluation_manifest_id"] == "public-sample-20260619T090925Z"
        assert summary["selected_train_sft_rows"] == expected_rows[arm]
        assert summary["expected_train_sft_rows"] == expected_rows[arm]
        assert summary["base_model_public_id"] == "Qwen/Qwen2.5-7B-Instruct"
        assert summary["seed"] == 7170
        assert summary["learning_rate"] == 0.00005
        assert summary["gradient_accumulation_steps"] == 1
        assert summary["adapter_release_status"] == "not_released"
        assert summary["checkpoint_release_status"] == "not_released"
        assert summary["raw_private_paths_copied_to_git"] is False
        assert summary["sanitized_for_public_evidence"] is True
        assert "raw adapter metadata" in summary["observed_training_status_basis"]
        assert metrics["training_summary_path"] == f"{arm}/training_summary.json"
        serialized = json.dumps(summary, sort_keys=True)
        assert "/mnt/data" not in serialized
        assert "<a100_project_root>" not in serialized
