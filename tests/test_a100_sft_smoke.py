import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from voice2task import training
from voice2task.cli import train as train_cli
from voice2task.leak_scan import scan_paths
from voice2task.schemas import SFTDatasetRow, canonical_contract_json
from voice2task.training import run_sft

REPO_ROOT = Path(__file__).resolve().parents[1]
A100_PROJECT_DIR = "/mnt/data/" + "minghongsun/voice2task-post-training"
A100_PROJECT_ROOT_POLICY = "must_resolve_to_approved_private_a100_project_root"
RUNTIME_SFT_MAX_SEQ_LENGTH = 2048
SHARED_PREFIX_RUNTIME_SFT_MAX_SEQ_LENGTH = 4096


def _write_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "manifest.json"
    rows = tmp_path / "sft_public_sample.jsonl"
    rows.write_text(
        json.dumps(
            {
                "id": "sft-1",
                "split": "train",
                "input_text": "搜索天气",
                "target_contract": {
                    "task_type": "search",
                    "route": "search_web",
                    "safety": {"allow": True, "reason": "public_readonly"},
                    "confirmation_required": False,
                    "slots": {"query": "天气"},
                    "normalized_command": "搜索天气",
                    "language": "zh-CN",
                    "contract_version": "v1",
                },
                "provenance": {"source_id": "seed-1", "public_safe": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest.write_text(
        json.dumps(
            {
                "manifest_id": "public-sample-test",
                "files": {"sft": rows.name},
                "counts": {"sft_rows": 1},
            }
        ),
        encoding="utf-8",
    )
    return manifest


def _write_multirow_manifest(tmp_path: Path, *, train_rows: int = 4) -> Path:
    manifest = tmp_path / "manifest.json"
    rows = tmp_path / "sft_public_sample.jsonl"
    lines = []
    for index in range(train_rows):
        lines.append(
            json.dumps(
                {
                    "id": f"sft-{index + 1}",
                    "split": "train",
                    "input_text": f"搜索天气 {index + 1}",
                    "target_contract": {
                        "task_type": "search",
                        "route": "search_web",
                        "safety": {"allow": True, "reason": "public_readonly"},
                        "confirmation_required": False,
                        "slots": {"query": f"天气 {index + 1}"},
                        "normalized_command": f"搜索天气 {index + 1}",
                        "language": "zh-CN",
                        "contract_version": "v1",
                    },
                    "provenance": {"source_id": f"seed-{index + 1}", "public_safe": True},
                },
                ensure_ascii=False,
            )
        )
    rows.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "manifest_id": "public-sample-test",
                "files": {"sft": rows.name},
                "counts": {"sft_rows": train_rows},
            }
        ),
        encoding="utf-8",
    )
    return manifest


def _write_config(tmp_path: Path, allow_heavy_training: bool, output_root: str = A100_PROJECT_DIR) -> Path:
    suffix = "allow" if allow_heavy_training else "block"
    config = tmp_path / f"sft-{suffix}.json"
    config.write_text(
        json.dumps(
            {
                "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
                "allow_heavy_training": allow_heavy_training,
                "dataset_split": "train",
                "gpu_selection_policy": "select_idle_gpu_only_no_process_interruption",
                "output_root": output_root,
                "lora": {"r": 8, "alpha": 16, "dropout": 0.05, "target_modules": ["q_proj", "v_proj"]},
            }
        ),
        encoding="utf-8",
    )
    return config


def _write_runtime_label_provenance_config(
    tmp_path: Path,
    *,
    allow_runtime_check: bool = False,
    output_root: str = "<a100_project_root>",
    adapter_path: str = "<a100_project_root>/runs/a100-train-split-overfit-diagnostic/adapter",
    evidence_output_dir: str | None = None,
    runtime_check_output_dir: str | None = None,
) -> Path:
    resolved_evidence_output_dir = evidence_output_dir or f"{output_root}/evidence/runtime-label-provenance-prep"
    resolved_runtime_check_output_dir = (
        runtime_check_output_dir or f"{output_root}/evidence/runtime-label-provenance-prep"
    )
    config = tmp_path / "runtime-label-provenance-prep.json"
    config.write_text(
        json.dumps(
            {
                "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
                "allow_runtime_label_provenance_check": allow_runtime_check,
                "private_override_required": True,
                "private_override_requirements": [
                    "Create a private override outside git before runtime execution.",
                    "Resolve <a100_project_root> to the approved private A100 project root.",
                ],
                "output_root": output_root,
                "evidence_output_dir": resolved_evidence_output_dir,
                "runtime_check_output_dir": resolved_runtime_check_output_dir,
                "adapter_path": adapter_path,
                "dependency_policy": "prep_only_no_train_dependency_import_no_model_download",
                "max_seq_length": SHARED_PREFIX_RUNTIME_SFT_MAX_SEQ_LENGTH,
                "label_provenance_intent": "inspect_real_tokenizer_collator_labels_later",
                "prior_artifacts": {
                    "sft_label_provenance": "reports/public-sample/sft-label-provenance/",
                    "sft_target_template_alignment": "reports/public-sample/sft-target-template-alignment/",
                    "a100_train_split_overfit_diagnostic": (
                        "reports/public-sample/a100-train-split-overfit-diagnostic/"
                    ),
                },
            }
        ),
        encoding="utf-8",
    )
    return config


class _RuntimeInspectableTokenizer:
    chat_template = "private-runtime-template"

    def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
        tokens = [ord(char) for char in text]
        offsets = [(index, index + 1) for index, _ in enumerate(text)]
        return {
            "input_ids": tokens,
            "attention_mask": [1 for _ in tokens],
            "offset_mapping": offsets,
        }


class _MissingOffsetTokenizer(_RuntimeInspectableTokenizer):
    def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
        encoded = super().__call__(text, **kwargs)
        encoded.pop("offset_mapping")
        return encoded


class _MismatchedOffsetTokenizer(_RuntimeInspectableTokenizer):
    def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
        encoded = super().__call__(text, **kwargs)
        encoded["offset_mapping"] = encoded["offset_mapping"][:-1]
        return encoded


class _BoundaryOverlapTokenizer(_RuntimeInspectableTokenizer):
    def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
        target = '{"contract_version"'
        boundary = text.find(target)
        if boundary < 0:
            boundary = max(1, len(text) // 2)
        return {
            "input_ids": [1, 2],
            "attention_mask": [1, 1],
            "offset_mapping": [(0, boundary + 1), (boundary + 1, len(text))],
        }


class _AssistantOnlyRuntimeLossCollator:
    def __call__(self, features: list[dict[str, Any]]) -> dict[str, list[list[int]]]:
        feature = features[0]
        assistant_start = feature["label_provenance_assistant_start"]
        labels = [
            -100 if end <= assistant_start else token_id
            for token_id, (_, end) in zip(feature["input_ids"], feature["offset_mapping"], strict=True)
        ]
        return {"labels": [labels]}


def test_public_sample_a100_sft_smoke_config_is_bounded_and_opt_in() -> None:
    config_path = REPO_ROOT / "configs" / "sft-a100-public-smoke.json"

    assert config_path.exists()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["allow_heavy_training"] is True
    assert config["base_model"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
    assert config["output_root"] == "<a100_project_root>"
    assert config["output_dir"] == "<a100_project_root>/runs/a100-sft-public-smoke"
    assert config["adapter_output_dir"] == "<a100_project_root>/runs/a100-sft-public-smoke/adapter"
    assert config["a100_project_root_policy"] == A100_PROJECT_ROOT_POLICY
    assert config["gpu_selection_policy"] == "select_idle_gpu_only_no_process_interruption"
    assert scan_paths([config_path]).ok is True


def test_compact_query_exact_match_a100_rerun_configs_use_7b_and_stay_public_safe() -> None:
    sft_config_path = REPO_ROOT / "configs" / "sft-a100-compact-query-exact-match-rerun.json"
    prediction_config_path = REPO_ROOT / "configs" / "sft-a100-compact-query-exact-match-prediction.json"

    assert sft_config_path.exists()
    assert prediction_config_path.exists()
    sft_config = json.loads(sft_config_path.read_text(encoding="utf-8"))
    prediction_config = json.loads(prediction_config_path.read_text(encoding="utf-8"))
    serialized = json.dumps({"sft": sft_config, "prediction": prediction_config}, ensure_ascii=False, sort_keys=True)

    assert sft_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert prediction_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert sft_config["allow_heavy_training"] is True
    assert prediction_config["allow_private_prediction"] is True
    assert sft_config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
    assert prediction_config["prediction_split"] == "train"
    assert prediction_config["overfit_diagnostic"] is True
    assert prediction_config["generalization_claim"] is False
    assert sft_config["output_root"] == "<a100_project_root>"
    assert prediction_config["output_root"] == "<a100_project_root>"
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([sft_config_path, prediction_config_path]).ok is True


def test_current_manifest_tiny_overfit_probe_configs_use_7b_and_stay_public_safe() -> None:
    sft_config_path = REPO_ROOT / "configs" / "sft-a100-current-manifest-tiny-overfit-rerun.json"
    prediction_config_path = REPO_ROOT / "configs" / "sft-a100-current-manifest-tiny-overfit-prediction.json"

    assert sft_config_path.exists()
    assert prediction_config_path.exists()
    sft_config = json.loads(sft_config_path.read_text(encoding="utf-8"))
    prediction_config = json.loads(prediction_config_path.read_text(encoding="utf-8"))
    serialized = json.dumps({"sft": sft_config, "prediction": prediction_config}, ensure_ascii=False, sort_keys=True)

    assert sft_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert prediction_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert sft_config["dataset_manifest_id"] == "public-sample-20260613T072200Z"
    assert prediction_config["dataset_manifest_id"] == "public-sample-20260613T072200Z"
    assert sft_config["dataset_split"] == "train"
    assert sft_config["max_train_rows"] == 3
    assert sft_config["allow_heavy_training"] is True
    assert prediction_config["allow_private_prediction"] is True
    assert prediction_config["max_prediction_rows"] == 3
    assert prediction_config["prediction_split"] == "train"
    assert prediction_config["overfit_diagnostic"] is True
    assert prediction_config["generalization_claim"] is False
    assert sft_config["output_root"] == "<a100_project_root>"
    assert prediction_config["output_root"] == "<a100_project_root>"
    assert sft_config["reference_runtime"] == "a100-current-manifest-tiny-overfit-probe"
    assert prediction_config["reference_runtime"] == "a100-current-manifest-tiny-overfit-probe-prediction"
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([sft_config_path, prediction_config_path]).ok is True


def test_current_tiny_adapter_heldout_prediction_configs_are_split_specific_and_public_safe() -> None:
    config_paths = {
        "dev": REPO_ROOT / "configs" / "sft-a100-current-tiny-adapter-heldout-dev-prediction.json",
        "test": REPO_ROOT / "configs" / "sft-a100-current-tiny-adapter-heldout-test-prediction.json",
    }

    for split, config_path in config_paths.items():
        assert config_path.exists()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

        assert config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
        assert config["dataset_manifest_id"] == "public-sample-20260613T072200Z"
        assert config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["current_tiny_adapter_heldout_diagnostic"] is True
        assert config["overfit_diagnostic"] is False
        assert config["generalization_claim"] is False
        assert config["output_root"] == "<a100_project_root>"
        assert config["adapter_path"] == "<a100_project_root>/runs/a100-current-manifest-tiny-overfit-probe/adapter"
        assert config["evidence_output_dir"] == (
            f"<a100_project_root>/evidence/current-tiny-adapter-heldout-prediction/{split}"
        )
        assert config["reference_runtime"] == f"a100-current-tiny-adapter-heldout-{split}-prediction"
        assert "allow_heavy_training" not in config
        assert "adapter_output_dir" not in config
        assert "max_prediction_rows" not in config
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized
        assert scan_paths([config_path]).ok is True


def test_extract_price_contract_residual_a100_rerun_configs_use_7b_and_stay_public_safe() -> None:
    sft_config_path = REPO_ROOT / "configs" / "sft-a100-extract-price-contract-residual-rerun.json"
    prediction_config_path = REPO_ROOT / "configs" / "sft-a100-extract-price-contract-residual-prediction.json"

    assert sft_config_path.exists()
    assert prediction_config_path.exists()
    sft_config = json.loads(sft_config_path.read_text(encoding="utf-8"))
    prediction_config = json.loads(prediction_config_path.read_text(encoding="utf-8"))
    serialized = json.dumps({"sft": sft_config, "prediction": prediction_config}, ensure_ascii=False, sort_keys=True)

    assert sft_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert prediction_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert sft_config["dataset_manifest_id"] == "public-sample-20260613T060441Z"
    assert prediction_config["dataset_manifest_id"] == "public-sample-20260613T060441Z"
    assert sft_config["allow_heavy_training"] is True
    assert prediction_config["allow_private_prediction"] is True
    assert sft_config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
    assert prediction_config["prediction_split"] == "train"
    assert prediction_config["overfit_diagnostic"] is True
    assert prediction_config["generalization_claim"] is False
    assert sft_config["output_root"] == "<a100_project_root>"
    assert prediction_config["output_root"] == "<a100_project_root>"
    assert sft_config["reference_runtime"] == "a100-extract-price-contract-residual-rerun"
    assert prediction_config["reference_runtime"] == "a100-extract-price-contract-residual-prediction"
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([sft_config_path, prediction_config_path]).ok is True


def test_extract_price_canonical_wording_a100_rerun_configs_use_7b_and_stay_public_safe() -> None:
    sft_config_path = REPO_ROOT / "configs" / "sft-a100-extract-price-canonical-wording-rerun.json"
    prediction_config_path = REPO_ROOT / "configs" / "sft-a100-extract-price-canonical-wording-prediction.json"

    assert sft_config_path.exists()
    assert prediction_config_path.exists()
    sft_config = json.loads(sft_config_path.read_text(encoding="utf-8"))
    prediction_config = json.loads(prediction_config_path.read_text(encoding="utf-8"))
    serialized = json.dumps({"sft": sft_config, "prediction": prediction_config}, ensure_ascii=False, sort_keys=True)

    assert sft_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert prediction_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert sft_config["dataset_manifest_id"] == "public-sample-20260613T063029Z"
    assert prediction_config["dataset_manifest_id"] == "public-sample-20260613T063029Z"
    assert sft_config["allow_heavy_training"] is True
    assert prediction_config["allow_private_prediction"] is True
    assert sft_config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
    assert prediction_config["prediction_split"] == "train"
    assert prediction_config["overfit_diagnostic"] is True
    assert prediction_config["generalization_claim"] is False
    assert sft_config["output_root"] == "<a100_project_root>"
    assert prediction_config["output_root"] == "<a100_project_root>"
    assert sft_config["reference_runtime"] == "a100-extract-price-canonical-wording-rerun"
    assert prediction_config["reference_runtime"] == "a100-extract-price-canonical-wording-prediction"
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([sft_config_path, prediction_config_path]).ok is True


def test_public_heldout_contract_generalization_prediction_configs_are_split_specific_and_public_safe() -> None:
    config_paths = {
        "dev": REPO_ROOT / "configs" / "sft-a100-public-heldout-dev-prediction.json",
        "test": REPO_ROOT / "configs" / "sft-a100-public-heldout-test-prediction.json",
    }

    for split, config_path in config_paths.items():
        assert config_path.exists()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

        assert config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
        assert config["dataset_manifest_id"] == "public-sample-20260613T063029Z"
        assert config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["public_heldout_diagnostic"] is True
        assert config["overfit_diagnostic"] is False
        assert config["generalization_claim"] is False
        assert config["output_root"] == "<a100_project_root>"
        assert config["adapter_path"] == "<a100_project_root>/runs/a100-extract-price-canonical-wording-rerun/adapter"
        assert config["evidence_output_dir"] == (
            f"<a100_project_root>/evidence/a100-public-heldout-contract-generalization/{split}"
        )
        assert config["reference_runtime"] == f"a100-public-heldout-contract-generalization-{split}-prediction"
        assert "allow_heavy_training" not in config
        assert "adapter_output_dir" not in config
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized
        assert scan_paths([config_path]).ok is True


def test_public_heldout_residual_repair_a100_configs_are_split_specific_and_public_safe() -> None:
    manifest_id = "public-sample-20260613T072200Z"
    sft_config_path = REPO_ROOT / "configs" / "sft-a100-public-heldout-residual-repair-rerun.json"
    prediction_config_paths = {
        "train": REPO_ROOT / "configs" / "sft-a100-public-heldout-residual-repair-train-prediction.json",
        "dev": REPO_ROOT / "configs" / "sft-a100-public-heldout-residual-repair-dev-prediction.json",
        "test": REPO_ROOT / "configs" / "sft-a100-public-heldout-residual-repair-test-prediction.json",
    }

    assert sft_config_path.exists()
    sft_config = json.loads(sft_config_path.read_text(encoding="utf-8"))
    serialized_sft = json.dumps(sft_config, ensure_ascii=False, sort_keys=True)
    assert sft_config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert sft_config["dataset_manifest_id"] == manifest_id
    assert sft_config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
    assert sft_config["dataset_split"] == "train"
    assert sft_config["dev_split"] == "dev"
    assert sft_config["allow_heavy_training"] is True
    assert sft_config["public_heldout_residual_repair"] is True
    assert sft_config["generalization_claim"] is False
    assert sft_config["output_root"] == "<a100_project_root>"
    assert sft_config["adapter_output_dir"] == (
        "<a100_project_root>/runs/a100-public-heldout-residual-repair-rerun/adapter"
    )
    assert "/mnt/data/" not in serialized_sft
    assert "/Users/" not in serialized_sft

    for split, config_path in prediction_config_paths.items():
        assert config_path.exists()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

        assert config["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
        assert config["dataset_manifest_id"] == manifest_id
        assert config["public_sample_manifest"] == "data/public-samples/manifest_public_sample.json"
        assert config["prediction_split"] == split
        assert config["allow_private_prediction"] is True
        assert config["public_heldout_residual_repair"] is True
        assert config["generalization_claim"] is False
        assert config["output_root"] == "<a100_project_root>"
        assert config["adapter_path"] == (
            "<a100_project_root>/runs/a100-public-heldout-residual-repair-rerun/adapter"
        )
        assert config["evidence_output_dir"] == (
            f"<a100_project_root>/evidence/a100-public-heldout-residual-repair/{split}"
        )
        assert config["reference_runtime"] == f"a100-public-heldout-residual-repair-{split}-prediction"
        assert "allow_heavy_training" not in config
        assert "adapter_output_dir" not in config
        assert "/mnt/data/" not in serialized
        assert "/Users/" not in serialized
        assert scan_paths([config_path]).ok is True

    assert scan_paths([sft_config_path, *prediction_config_paths.values()]).ok is True


def test_public_heldout_residual_repair_evidence_records_negative_result_without_release_claims() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "repair-public-heldout-contract-residuals"
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "heldout_residual_repair_diagnosis.json").read_text(encoding="utf-8"))
    train_metrics = json.loads((evidence_dir / "train" / "metrics.json").read_text(encoding="utf-8"))
    dev_metrics = json.loads((evidence_dir / "dev" / "metrics.json").read_text(encoding="utf-8"))
    test_metrics = json.loads((evidence_dir / "test" / "metrics.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8").lower()

    assert manifest["evidence_kind"] == "a100_public_heldout_residual_repair"
    assert manifest["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert manifest["dataset_manifest_id"] == "public-sample-20260613T072200Z"
    assert manifest["prediction_splits"] == ["train", "dev", "test"]
    assert manifest["primary_evidence_splits"] == ["dev", "test"]
    assert manifest["overall_interpretation"] == "public_heldout_residual_repair_failed"
    assert manifest["claims"]["public_heldout_residual_repair"] is True
    assert manifest["claims"]["held_out_generalization_recovered"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["adapter_release"] is False
    assert manifest["claims"]["checkpoint_release"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["private_paths_omitted"] is True
    assert manifest["split_results"]["train"]["contract_exact_match"] == pytest.approx(1 / 3)
    assert manifest["split_results"]["dev"]["contract_exact_match"] == 0.0
    assert manifest["split_results"]["test"]["contract_exact_match"] == 0.0
    assert manifest["split_results"]["dev"]["json_valid_rate"] == 1.0
    assert manifest["split_results"]["test"]["json_valid_rate"] == 1.0
    assert train_metrics["metrics"]["contract_exact_match"] == pytest.approx(1 / 3)
    assert dev_metrics["metrics"]["contract_exact_match"] == 0.0
    assert test_metrics["metrics"]["contract_exact_match"] == 0.0
    assert diagnosis["summary"]["overall_interpretation"] == "public_heldout_residual_repair_failed"
    assert diagnosis["summary"]["split_exact_match"]["train"] == pytest.approx(1 / 3)
    assert diagnosis["summary"]["split_exact_match"]["dev"] == 0.0
    assert diagnosis["summary"]["split_exact_match"]["test"] == 0.0
    assert leak_scan["ok"] is True
    assert "negative result" in report
    assert "not a release" in report
    assert "private-corpus" in report
    assert scan_paths([evidence_dir]).ok is True


def test_prompt_snapshot_row_records_actual_extract_prompt_constraints() -> None:
    row = SFTDatasetRow(
        id="seed-extract-price-aug-1",
        split="train",
        input_text="帮我看看这个东西现在卖多少钱",
        target_contract={
            "task_type": "extract",
            "route": "extract_page",
            "safety": {"allow": True, "reason": "public_readonly"},
            "confirmation_required": False,
            "slots": {"target": "商品价格"},
            "normalized_command": "提取页面商品价格",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        provenance={"source_id": "seed-extract-price", "public_safe": True},
    )

    prompt = training.format_sft_prediction_prompt(training.PredictionInput.from_sft_row(row), tokenizer=None)
    snapshot = training._prompt_snapshot_row(row, prompt)  # noqa: SLF001

    assert snapshot["prompt_constraints"]["public_readonly_extract_policy_visible"] is True
    assert snapshot["prompt_constraints"]["extract_target_slot_guidance_visible"] is True
    assert snapshot["prompt_constraints"]["extract_search_fallback_rejection_visible"] is True
    assert snapshot["prompt_constraints"]["extract_query_page_url_slot_rejection_visible"] is True


def test_extract_price_contract_residual_a100_rerun_evidence_is_bounded_and_public_safe() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-extract-price-contract-residual-rerun"
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    diagnosis = json.loads(
        (evidence_dir / "extract_price_contract_residual_rerun_diagnosis.json").read_text(encoding="utf-8")
    )
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8").lower()

    assert manifest["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert manifest["prediction_split"] == "train"
    assert manifest["overfit_diagnostic"] is True
    assert manifest["generalization_claim"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["observed_result"]["compact_query_exact_match_count"] == 3
    assert manifest["observed_result"]["extract_price_task_route_correct_count"] == 3
    assert manifest["observed_result"]["extract_price_exact_match_count"] == 0
    assert manifest["observed_result"]["extract_price_slot_target_exact_count"] == 1
    assert metrics["metrics"]["contract_exact_match"] == 0.5
    assert metrics["metrics"]["json_valid_rate"] == 1.0
    assert metrics["metrics"]["slot_f1"] == 2 / 3
    assert diagnosis["summary"]["overall_interpretation"] == (
        "extract_price_route_recovered_but_strict_exact_match_residual_remains"
    )
    assert diagnosis["summary"]["extract_price_search_fallback_count"] == 0
    assert diagnosis["summary"]["extract_price_query_or_page_url_slot_count"] == 0
    assert metadata["prompt_constraints"]["public_readonly_extract_policy_visible"] is True
    assert prompt_snapshot["prompt_constraints"]["public_readonly_extract_policy_visible"] is True
    assert leak_scan["ok"] is True
    assert "not a model-recovery claim" in report
    assert scan_paths([evidence_dir]).ok is True


def test_extract_price_canonical_wording_a100_rerun_evidence_is_bounded_and_public_safe() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-extract-price-canonical-wording-rerun"
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    diagnosis = json.loads(
        (evidence_dir / "extract_price_canonical_wording_rerun_diagnosis.json").read_text(encoding="utf-8")
    )
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8").lower()

    assert manifest["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert manifest["prediction_split"] == "train"
    assert manifest["overfit_diagnostic"] is True
    assert manifest["generalization_claim"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["observed_result"]["compact_query_exact_match_count"] == 3
    assert manifest["observed_result"]["extract_price_exact_match_count"] == 3
    assert manifest["observed_result"]["extract_price_slot_target_exact_count"] == 3
    assert manifest["observed_result"]["extract_price_normalized_command_exact_count"] == 3
    assert manifest["observed_result"]["extract_price_wrong_price_synonym_count"] == 0
    assert metrics["metrics"]["contract_exact_match"] == 1.0
    assert metrics["metrics"]["json_valid_rate"] == 1.0
    assert metrics["metrics"]["slot_f1"] == 1.0
    assert diagnosis["summary"]["overall_interpretation"] == (
        "extract_price_canonical_wording_recovered_on_train_split"
    )
    assert diagnosis["summary"]["extract_price_search_fallback_count"] == 0
    assert diagnosis["summary"]["extract_price_extra_particle_normalized_command_count"] == 0
    assert metadata["prompt_constraints"]["extract_canonical_price_target_visible"] is True
    assert metadata["prompt_constraints"]["extract_wrong_price_synonym_rejection_visible"] is True
    assert prompt_snapshot["prompt_constraints"]["extract_canonical_price_target_visible"] is True
    assert leak_scan["ok"] is True
    assert "not a model-recovery claim" in report
    assert scan_paths([evidence_dir]).ok is True


def test_public_heldout_contract_generalization_evidence_records_split_failures_without_release_claims() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-public-heldout-contract-generalization"
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    diagnosis = json.loads(
        (evidence_dir / "heldout_contract_generalization_diagnosis.json").read_text(encoding="utf-8")
    )
    dev_metrics = json.loads((evidence_dir / "dev" / "metrics.json").read_text(encoding="utf-8"))
    test_metrics = json.loads((evidence_dir / "test" / "metrics.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8").lower()

    assert manifest["evidence_kind"] == "a100_public_heldout_contract_generalization"
    assert manifest["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert manifest["prediction_splits"] == ["dev", "test"]
    assert manifest["claims"]["held_out_generalization_recovered"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["adapter_release"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["split_results"]["dev"]["contract_exact_match"] == 0.0
    assert manifest["split_results"]["test"]["contract_exact_match"] == 0.0
    assert manifest["split_results"]["dev"]["json_valid_rate"] == 1.0
    assert manifest["split_results"]["test"]["json_valid_rate"] == 1.0
    assert dev_metrics["metrics"]["contract_exact_match"] == 0.0
    assert test_metrics["metrics"]["contract_exact_match"] == 0.0
    assert diagnosis["summary"]["overall_interpretation"] == "public_heldout_strict_generalization_failed"
    assert diagnosis["summary"]["split_exact_match"] == {"dev": 0.0, "test": 0.0}
    assert leak_scan["ok"] is True
    assert "not a release" in report
    assert "public held-out diagnostic" in report
    assert scan_paths([evidence_dir]).ok is True


def test_current_tiny_adapter_heldout_prediction_evidence_records_failed_transfer() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "current-tiny-adapter-heldout-prediction"
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "current_tiny_adapter_heldout_diagnosis.json").read_text(encoding="utf-8"))
    dev_metrics = json.loads((evidence_dir / "dev" / "metrics.json").read_text(encoding="utf-8"))
    test_metrics = json.loads((evidence_dir / "test" / "metrics.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8").lower()

    assert manifest["evidence_kind"] == "current_tiny_adapter_heldout_prediction"
    assert manifest["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert manifest["dataset_manifest_id"] == "public-sample-20260613T072200Z"
    assert manifest["prediction_splits"] == ["dev", "test"]
    assert manifest["prior_train_internal_result"]["contract_exact_match"] == 1.0
    assert manifest["overall_interpretation"] == "current_tiny_adapter_heldout_strict_generalization_failed"
    assert manifest["claims"]["held_out_generalization_recovered"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["adapter_release"] is False
    assert manifest["claims"]["checkpoint_release"] is False
    assert manifest["claims"]["new_training"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["private_paths_omitted"] is True
    assert manifest["split_results"]["dev"]["contract_exact_match"] == 0.0
    assert manifest["split_results"]["test"]["contract_exact_match"] == 0.0
    assert manifest["split_results"]["dev"]["json_valid_rate"] == 1.0
    assert manifest["split_results"]["test"]["json_valid_rate"] == pytest.approx(2 / 3)
    assert dev_metrics["metrics"]["contract_exact_match"] == 0.0
    assert test_metrics["metrics"]["contract_exact_match"] == 0.0
    assert diagnosis["summary"]["overall_interpretation"] == (
        "current_tiny_adapter_heldout_strict_generalization_failed"
    )
    assert diagnosis["summary"]["split_exact_match"] == {"dev": 0.0, "test": 0.0}
    assert leak_scan["ok"] is True
    assert "prediction-only" in report
    assert "not a new training run" in report
    assert "did not carry" in report
    assert scan_paths([evidence_dir]).ok is True


def test_compact_query_exact_match_a100_rerun_evidence_is_bounded_and_public_safe() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-compact-query-exact-match-rerun"
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    diagnosis = json.loads(
        (evidence_dir / "compact_query_exact_match_rerun_diagnosis.json").read_text(encoding="utf-8")
    )
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8").lower()

    assert manifest["base_model"] == "Qwen/Qwen2.5-7B-Instruct"
    assert manifest["prediction_split"] == "train"
    assert manifest["overfit_diagnostic"] is True
    assert manifest["generalization_claim"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["observed_result"]["compact_query_exact_match_count"] == 3
    assert manifest["observed_result"]["compact_query_decomposed_slot_count"] == 0
    assert manifest["observed_result"]["non_compact_extract_residual_row_count"] == 3
    assert metrics["metrics"]["contract_exact_match"] == 0.5
    assert metrics["metrics"]["json_valid_rate"] == 1.0
    assert diagnosis["summary"]["overall_interpretation"] == (
        "compact_query_residual_improved_but_overall_train_split_not_fully_recovered"
    )
    assert all(row["uses_compact_query_slot"] for row in diagnosis["compact_query_rows"])
    assert all(not row["uses_decomposed_city_date_topic_slots"] for row in diagnosis["compact_query_rows"])
    assert leak_scan["ok"] is True
    assert "not a model-recovery claim" in report
    assert scan_paths([evidence_dir]).ok is True


def test_runtime_label_provenance_config_template_is_public_safe_and_requires_private_override() -> None:
    config_path = REPO_ROOT / "configs" / "sft-runtime-label-provenance-prep.json"

    assert config_path.exists()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

    assert config["private_override_required"] is True
    assert config["allow_runtime_label_provenance_check"] is False
    assert config["true_label_mask_status"] == "unavailable"
    assert config["label_tensor_available"] is False
    assert config["output_root"] == "<a100_project_root>"
    assert "<a100_project_root>" in serialized
    assert "private override" in " ".join(config["private_override_requirements"]).lower()
    assert "prep_only_no_train_dependency_import_no_model_download" == config["dependency_policy"]
    assert set(config["prior_artifacts"]) == {
        "sft_label_provenance",
        "sft_target_template_alignment",
        "a100_train_split_overfit_diagnostic",
    }
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([config_path]).ok is True


def test_runtime_label_provenance_prep_blocks_unresolved_private_override_and_keeps_true_labels_unavailable(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_runtime_label_provenance_config(tmp_path, allow_runtime_check=True)

    def fail_if_train_dependencies_checked() -> bool:
        raise AssertionError("runtime prep must not inspect train dependencies")

    monkeypatch.setattr(training, "_train_dependencies_available", fail_if_train_dependencies_checked)

    metadata = training.prepare_sft_runtime_label_provenance(config, manifest)
    serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)

    assert metadata["evidence_kind"] == "sft_runtime_label_provenance_prep"
    assert metadata["runtime_check_status"] == "blocked_unresolved_private_override"
    assert metadata["runtime_gate"] == {
        "cli_requested_runtime_check": False,
        "config_allow_runtime_label_provenance_check": True,
        "private_override_resolved": False,
        "will_run_runtime_label_provenance_check": False,
    }
    assert metadata["private_override"]["required"] is True
    assert metadata["private_override"]["status"] == "unresolved"
    assert set(metadata["private_override"]["unresolved_fields"]) == {
        "adapter_path",
        "evidence_output_dir",
        "output_root",
        "runtime_check_output_dir",
    }
    assert metadata["dependency_policy"]["train_dependencies_imported"] is False
    assert metadata["dependency_policy"]["model_download_allowed"] is False
    assert metadata["dependency_policy"]["private_adapter_load_allowed"] is False
    assert metadata["label_provenance_intent"]["private_labels_inspected"] is False
    assert metadata["label_tensor_available"] is False
    assert metadata["true_label_mask_status"] == "unavailable"
    assert "runtime_check_not_executed" in metadata["evidence_gaps"]
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized


def test_runtime_label_provenance_prep_defaults_to_non_heavy_skipped_status(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=False,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
    )

    metadata = training.prepare_sft_runtime_label_provenance(config, manifest)

    assert metadata["runtime_check_status"] == "skipped_no_runtime_opt_in"
    assert metadata["runtime_gate"] == {
        "cli_requested_runtime_check": False,
        "config_allow_runtime_label_provenance_check": False,
        "private_override_resolved": True,
        "will_run_runtime_label_provenance_check": False,
    }
    assert metadata["output_root_policy"]["status"] == "resolved_private_override_not_run"
    assert metadata["label_tensor_available"] is False
    assert metadata["true_label_mask_status"] == "unavailable"
    assert metadata["claims"]["runtime_readiness_proves_contract_learning"] is False


def test_runtime_label_provenance_prep_blocks_partial_override_with_unresolved_evidence_output_dir(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=(resolved_root / "evidence" / "runtime-label-provenance-prep").as_posix(),
        evidence_output_dir="<a100_project_root>/evidence/runtime-label-provenance-prep",
    )

    metadata = training.prepare_sft_runtime_label_provenance(config, manifest)

    assert metadata["runtime_check_status"] == "blocked_unresolved_private_override"
    assert metadata["runtime_gate"]["private_override_resolved"] is False
    assert metadata["private_override"]["status"] == "unresolved"
    assert metadata["private_override"]["unresolved_fields"] == ["evidence_output_dir"]


def test_runtime_label_provenance_train_cli_writes_prep_metadata_without_stdout(
    tmp_path: Path,
    capsys: Any,
) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_runtime_label_provenance_config(tmp_path, allow_runtime_check=True)
    output = tmp_path / "runtime_prep.json"

    assert (
        train_cli.main(
            [
                "sft-prepare-runtime-label-provenance",
                "--config",
                config.as_posix(),
                "--manifest",
                manifest.as_posix(),
                "--output",
                output.as_posix(),
            ]
        )
        == 0
    )

    assert capsys.readouterr().out == ""
    metadata = json.loads(output.read_text(encoding="utf-8"))
    assert metadata["runtime_check_status"] == "blocked_unresolved_private_override"
    assert metadata["metadata_path"] in {output.as_posix(), "<private_path>"}


def test_runtime_label_provenance_check_blocks_without_run_flag_unresolved_override_or_bad_output(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=(resolved_root / "evidence" / "runtime-label-provenance-check").as_posix(),
        evidence_output_dir=(resolved_root / "evidence" / "runtime-label-provenance-check").as_posix(),
    )
    calls: list[SFTDatasetRow] = []

    def inspector(row: SFTDatasetRow, config: dict[str, Any]) -> dict[str, Any]:
        calls.append(row)
        return {"inspection_status": "should_not_run"}

    skipped = training.run_sft_runtime_label_provenance_check(
        config,
        manifest,
        split="train",
        output_path=resolved_root / "evidence" / "runtime-label-provenance-check" / "skipped.json",
        run_runtime_check=False,
        objective_inspector=inspector,
    )
    assert skipped["evidence_kind"] == "sft_runtime_label_provenance_observed"
    assert skipped["evidence_status"] == "skipped_no_runtime_opt_in"
    assert skipped["runtime_gate"]["cli_requested_runtime_check"] is False
    assert skipped["runtime_gate"]["will_run_runtime_label_provenance_check"] is False

    unresolved_dir = tmp_path / "unresolved"
    unresolved_dir.mkdir()
    unresolved_config = _write_runtime_label_provenance_config(unresolved_dir, allow_runtime_check=True)
    unresolved = training.run_sft_runtime_label_provenance_check(
        unresolved_config,
        manifest,
        split="train",
        output_path=resolved_root / "evidence" / "runtime-label-provenance-check" / "unresolved.json",
        run_runtime_check=True,
        objective_inspector=inspector,
    )
    assert unresolved["evidence_status"] == "blocked_unresolved_private_override"
    assert unresolved["private_override"]["status"] == "unresolved"
    assert set(unresolved["private_override"]["unresolved_fields"]) == {
        "adapter_path",
        "evidence_output_dir",
        "output_root",
        "runtime_check_output_dir",
    }

    outside = training.run_sft_runtime_label_provenance_check(
        config,
        manifest,
        split="train",
        output_path=tmp_path / "outside-root" / "runtime.json",
        run_runtime_check=True,
        objective_inspector=inspector,
    )
    assert outside["evidence_status"] == "blocked_output_outside_approved_root"
    assert outside["output_root_policy"]["status"] == "blocked_output_outside_approved_root"
    assert "runtime_output_outside_approved_root" in outside["evidence_gaps"]
    assert calls == []


def test_runtime_label_provenance_check_blocks_traversal_outside_runtime_root(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=(resolved_root / "evidence").as_posix(),
        evidence_output_dir=(resolved_root / "evidence").as_posix(),
    )
    output = resolved_root / "evidence" / ".." / ".." / "escaped" / "runtime.json"

    metadata = training.run_sft_runtime_label_provenance_check(
        config,
        manifest,
        split="train",
        output_path=output,
        run_runtime_check=True,
        objective_inspector=lambda row, config: {"inspection_status": "should_not_run"},
    )

    assert metadata["evidence_status"] == "blocked_output_outside_approved_root"
    assert metadata["output_root_policy"]["status"] == "blocked_output_outside_approved_root"
    assert not output.exists()


def test_runtime_label_provenance_check_blocks_symlink_escape_outside_runtime_root(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    runtime_dir = resolved_root / "evidence"
    runtime_dir.mkdir(parents=True)
    outside_dir = tmp_path / "escaped"
    outside_dir.mkdir()
    symlink = runtime_dir / "escape-link"
    symlink.symlink_to(outside_dir, target_is_directory=True)
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=runtime_dir.as_posix(),
        evidence_output_dir=runtime_dir.as_posix(),
    )
    output = symlink / "runtime.json"

    metadata = training.run_sft_runtime_label_provenance_check(
        config,
        manifest,
        split="train",
        output_path=output,
        run_runtime_check=True,
        objective_inspector=lambda row, config: {"inspection_status": "should_not_run"},
    )

    assert metadata["evidence_status"] == "blocked_output_outside_approved_root"
    assert metadata["output_root_policy"]["status"] == "blocked_output_outside_approved_root"
    assert not output.exists()


def test_runtime_label_provenance_check_records_real_collator_labels_with_explicit_provenance(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    output = resolved_root / "evidence" / "runtime-label-provenance-check" / "runtime.json"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=output.parent.as_posix(),
        evidence_output_dir=output.parent.as_posix(),
    )
    def inspector(row: SFTDatasetRow, config: dict[str, Any]) -> dict[str, Any]:
        return training.inspect_sft_objective(
            row,
            tokenizer=_RuntimeInspectableTokenizer(),
            collator=_AssistantOnlyRuntimeLossCollator(),
            label_source="trl_collator_labels",
            label_provenance={"source_kind": "private_training_runtime", "real_training_path": True},
        )

    metadata = training.run_sft_runtime_label_provenance_check(
        config,
        manifest,
        split="train",
        output_path=output,
        run_runtime_check=True,
        objective_inspector=inspector,
    )
    serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)

    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == metadata
    assert metadata["evidence_kind"] == "sft_runtime_label_provenance_observed"
    assert metadata["evidence_status"] == "labels_inspected"
    assert metadata["runtime_source_kind"] == "private_a100_runtime"
    assert metadata["dataset_manifest_id"] == "public-sample-test"
    assert set(metadata["package_versions"]).issuperset({"python", "transformers"})
    assert metadata["label_tensor_available"] is True
    assert metadata["true_label_mask_status"] == "inspectable"
    assert metadata["label_source"] == "trl_collator_labels"
    assert metadata["label_source_kind"] == "private_training_runtime"
    assert metadata["label_provenance"]["source_kind"] == "private_training_runtime"
    assert metadata["label_provenance"]["real_training_path"] is True
    assert metadata["prompt_tokens_masked"] is True
    assert metadata["assistant_tokens_carry_loss"] is True
    assert metadata["evidence_gaps"] == []
    assert metadata["release_status"] == "not_released"
    assert metadata["claims"]["held_out_generalization_claim"] is False
    assert metadata["claims"]["production_readiness_claim"] is False
    assert metadata["claims"]["live_browser_benchmark_claim"] is False
    assert metadata["artifact_policy"]["private_paths_omitted"] is True
    assert "fixture" not in metadata["label_source_kind"]
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized


def test_runtime_label_provenance_check_uses_tokenizer_without_full_train_extras(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    output = resolved_root / "evidence" / "runtime-label-provenance-check" / "runtime.json"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=output.parent.as_posix(),
        evidence_output_dir=output.parent.as_posix(),
    )
    config_payload = json.loads(config.read_text(encoding="utf-8"))
    config_payload["base_model"] = (resolved_root / "models" / "qwen2.5-7b-instruct").as_posix()
    config.write_text(json.dumps(config_payload), encoding="utf-8")
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: False)
    monkeypatch.setitem(
        training.__dict__,
        "AutoTokenizer",
        types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: _RuntimeInspectableTokenizer()),
    )

    metadata = training.run_sft_runtime_label_provenance_check(
        config,
        manifest,
        split="train",
        output_path=output,
        run_runtime_check=True,
    )

    assert metadata["evidence_status"] == "labels_inspected"
    assert metadata["tokenizer_status"] == "available"
    assert metadata["collator_status"] == "labels_inspected"
    assert metadata["true_label_mask_status"] == "inspectable"
    assert metadata["prompt_tokens_masked"] is True
    assert metadata["assistant_tokens_carry_loss"] is True


def test_runtime_label_provenance_check_downgrades_fixture_labels_to_fixture_only(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    output = resolved_root / "evidence" / "runtime-label-provenance-check" / "runtime.json"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=output.parent.as_posix(),
        evidence_output_dir=output.parent.as_posix(),
    )

    def inspector(row: SFTDatasetRow, config: dict[str, Any]) -> dict[str, Any]:
        return training.inspect_sft_objective(
            row,
            tokenizer=_RuntimeInspectableTokenizer(),
            collator=_AssistantOnlyRuntimeLossCollator(),
            label_source="trl_collator_labels",
            label_provenance={"source_kind": "fixture", "real_training_path": False},
        )

    metadata = training.run_sft_runtime_label_provenance_check(
        config,
        manifest,
        split="train",
        output_path=output,
        run_runtime_check=True,
        objective_inspector=inspector,
    )

    assert metadata["evidence_status"] == "fixture_only"
    assert metadata["label_tensor_available"] is True
    assert metadata["true_label_mask_status"] == "fixture_only"
    assert metadata["label_source_kind"] == "fixture"
    assert "fixture_labels_not_real_training_proof" in metadata["evidence_gaps"]
    assert "real_training_label_provenance_missing" in metadata["evidence_gaps"]
    assert metadata["claims"]["checkpoint_release"] is False
    assert metadata["artifact_policy"]["raw_logs_copied_to_git"] is False


def test_runtime_label_provenance_check_downgrades_non_real_provenance_to_available_but_not_proof(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    output = resolved_root / "evidence" / "runtime-label-provenance-check" / "runtime.json"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=output.parent.as_posix(),
        evidence_output_dir=output.parent.as_posix(),
    )

    def inspector(row: SFTDatasetRow, config: dict[str, Any]) -> dict[str, Any]:
        result = training.inspect_sft_objective(
            row,
            tokenizer=_RuntimeInspectableTokenizer(),
            collator=_AssistantOnlyRuntimeLossCollator(),
            label_source="trl_collator_labels",
            label_provenance={"source_kind": "private_training_runtime", "real_training_path": True},
        )
        result["label_provenance"]["real_training_path"] = False
        return result

    metadata = training.run_sft_runtime_label_provenance_check(
        config,
        manifest,
        split="train",
        output_path=output,
        run_runtime_check=True,
        objective_inspector=inspector,
    )

    assert metadata["label_tensor_available"] is True
    assert metadata["true_label_mask_status"] == "inspectable"
    assert metadata["evidence_status"] == "labels_available_but_not_real_training_proof"


def test_runtime_label_provenance_default_inspector_masks_prompt_tokens_with_assistant_only_labels(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    rows = training._load_sft_training_rows(manifest, split="train")  # noqa: SLF001
    calls: list[str] = []
    local_model = (tmp_path / "runtime-model").as_posix()

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(base_model: str, **kwargs: Any) -> _RuntimeInspectableTokenizer:
            calls.append(base_model)
            assert kwargs["trust_remote_code"] is True
            assert kwargs["local_files_only"] is True
            return _RuntimeInspectableTokenizer()

    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(training, "AutoTokenizer", FakeAutoTokenizer, raising=False)

    result = training._inspect_runtime_sft_objective(  # noqa: SLF001
        rows[0],
        {"base_model": local_model, "max_seq_length": SHARED_PREFIX_RUNTIME_SFT_MAX_SEQ_LENGTH},
    )

    assert calls == [local_model]
    assert result["inspection_status"] == "inspectable"
    assert result["label_source"] == "actual_training_labels"
    assert result["label_provenance"] == {
        "source_kind": "private_training_runtime",
        "real_training_path": True,
    }
    assert result["label_tensor_available"] is True
    assert result["true_label_mask_status"] == "inspectable"
    assert result["prompt_tokens_masked"] is True
    assert result["assistant_tokens_carry_loss"] is True


def test_sft_objective_fails_closed_when_assistant_target_span_is_ambiguous(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    row = training._load_sft_training_rows(manifest, split="train")[0]  # noqa: SLF001
    target = canonical_contract_json(row.target_contract)
    ambiguous_row = SFTDatasetRow(
        id=row.id,
        split=row.split,
        input_text=f"用户贴了候选合同 JSON: {target}",
        target_contract=row.target_contract,
        provenance=row.provenance,
    )

    result = training.inspect_sft_objective(
        ambiguous_row,
        tokenizer=_RuntimeInspectableTokenizer(),
        collator=_AssistantOnlyRuntimeLossCollator(),
        label_source="trl_collator_labels",
        label_provenance={"source_kind": "private_training_runtime", "real_training_path": True},
    )

    assert result["inspection_status"] == "assistant_span_ambiguous"
    assert result["label_tensor_available"] is False
    assert result["prompt_tokens_masked"] is None
    assert result["assistant_tokens_carry_loss"] is None
    assert "assistant_span_ambiguous" in result["evidence_gaps"]


def test_sft_assistant_only_training_record_masks_prompt_and_keeps_contract_loss(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    row = training._load_sft_training_rows(manifest, split="train")[0]  # noqa: SLF001
    target = canonical_contract_json(row.target_contract)

    record = training._assistant_only_training_record(row, _RuntimeInspectableTokenizer())  # noqa: SLF001
    loss_text = "".join(
        chr(token_id)
        for token_id, label in zip(record["input_ids"], record["labels"], strict=True)
        if label != -100
    )
    masked_text = "".join(
        chr(token_id)
        for token_id, label in zip(record["input_ids"], record["labels"], strict=True)
        if label == -100
    )

    assert loss_text == target
    assert "system:" in masked_text
    assert "user:" in masked_text
    assert "assistant:" in masked_text


def test_sft_assistant_only_training_record_fails_closed_when_max_seq_length_exceeded(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    row = training._load_sft_training_rows(manifest, split="train")[0]  # noqa: SLF001

    with pytest.raises(ValueError, match="max_seq_length_exceeded"):
        training._assistant_only_training_record(row, _RuntimeInspectableTokenizer(), max_seq_length=5)  # noqa: SLF001


def test_sft_assistant_only_training_record_fails_closed_without_offsets(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    row = training._load_sft_training_rows(manifest, split="train")[0]  # noqa: SLF001

    with pytest.raises(ValueError, match="token_offsets_unavailable"):
        training._assistant_only_training_record(row, _MissingOffsetTokenizer())  # noqa: SLF001


def test_sft_assistant_only_training_record_fails_closed_on_offset_length_mismatch(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    row = training._load_sft_training_rows(manifest, split="train")[0]  # noqa: SLF001

    with pytest.raises(ValueError, match="label_token_offset_length_mismatch"):
        training._assistant_only_training_record(row, _MismatchedOffsetTokenizer())  # noqa: SLF001


def test_sft_assistant_only_training_record_fails_closed_on_assistant_boundary_overlap(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    row = training._load_sft_training_rows(manifest, split="train")[0]  # noqa: SLF001

    with pytest.raises(ValueError, match="assistant_span_token_boundary_unavailable"):
        training._assistant_only_training_record(row, _BoundaryOverlapTokenizer())  # noqa: SLF001


def test_runtime_label_provenance_default_inspector_uses_training_record_data_collator(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    rows = training._load_sft_training_rows(manifest, split="train")  # noqa: SLF001
    local_model = (tmp_path / "runtime-model").as_posix()
    collator_features: list[list[dict[str, Any]]] = []

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(base_model: str, **kwargs: Any) -> _RuntimeInspectableTokenizer:
            return _RuntimeInspectableTokenizer()

    class SpyTrainingCollator:
        def __init__(self, tokenizer: Any, *, tensorize: bool = True) -> None:
            assert tensorize is False

        def __call__(self, features: list[dict[str, Any]]) -> dict[str, list[list[int]]]:
            collator_features.append(features)
            return {"labels": [list(features[0]["labels"])]}

    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(training, "AutoTokenizer", FakeAutoTokenizer, raising=False)
    monkeypatch.setattr(training, "_AssistantOnlyCausalLmDataCollator", SpyTrainingCollator)

    result = training._inspect_runtime_sft_objective(  # noqa: SLF001
        rows[0],
        {"base_model": local_model, "max_seq_length": SHARED_PREFIX_RUNTIME_SFT_MAX_SEQ_LENGTH},
    )

    assert collator_features
    assert {"input_ids", "attention_mask", "labels"} <= set(collator_features[0][0])
    assert result["inspection_status"] == "inspectable"
    assert result["label_source"] == "actual_training_labels"
    assert result["collator_status"] == "labels_inspected"
    assert result["true_label_mask_status"] == "inspectable"
    assert result["prompt_tokens_masked"] is True
    assert result["assistant_tokens_carry_loss"] is True


def test_runtime_label_provenance_default_inspector_prefers_private_base_model_for_loading(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    rows = training._load_sft_training_rows(manifest, split="train")  # noqa: SLF001
    calls: list[str] = []
    private_base_model = (tmp_path / "models" / "qwen-local").as_posix()

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(base_model: str, **kwargs: Any) -> _RuntimeInspectableTokenizer:
            calls.append(base_model)
            return _RuntimeInspectableTokenizer()

    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(training, "AutoTokenizer", FakeAutoTokenizer, raising=False)

    result = training._inspect_runtime_sft_objective(  # noqa: SLF001
        rows[0],
        {
            "base_model": private_base_model,
            "base_model_public_id": "Qwen/Qwen2.5-0.5B-Instruct",
            "max_seq_length": SHARED_PREFIX_RUNTIME_SFT_MAX_SEQ_LENGTH,
        },
    )

    assert calls == [private_base_model]
    assert result["inspection_status"] == "inspectable"


def test_runtime_label_provenance_default_inspector_rejects_public_id_fallback(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    rows = training._load_sft_training_rows(manifest, split="train")  # noqa: SLF001
    calls: list[str] = []

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(base_model: str, **kwargs: Any) -> _RuntimeInspectableTokenizer:
            calls.append(base_model)
            return _RuntimeInspectableTokenizer()

    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(training, "AutoTokenizer", FakeAutoTokenizer, raising=False)

    result = training._inspect_runtime_sft_objective(  # noqa: SLF001
        rows[0],
        {
            "base_model_public_id": "Qwen/Qwen2.5-0.5B-Instruct",
            "max_seq_length": SHARED_PREFIX_RUNTIME_SFT_MAX_SEQ_LENGTH,
        },
    )

    assert calls == []
    assert result["inspection_status"] == "tokenizer_unavailable"
    assert "runtime_base_model_not_private_local_path" in result["evidence_gaps"]


def test_runtime_label_provenance_train_cli_writes_observed_metadata_with_explicit_run_flag(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    output = resolved_root / "evidence" / "runtime-label-provenance-check" / "runtime.json"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=output.parent.as_posix(),
        evidence_output_dir=output.parent.as_posix(),
    )

    def inspector(row: SFTDatasetRow, config: dict[str, Any]) -> dict[str, Any]:
        return training.inspect_sft_objective(
            row,
            tokenizer=_RuntimeInspectableTokenizer(),
            collator=_AssistantOnlyRuntimeLossCollator(),
            label_source="trl_collator_labels",
            label_provenance={"source_kind": "private_training_runtime", "real_training_path": True},
        )

    monkeypatch.setattr(training, "_inspect_runtime_sft_objective", inspector)

    assert (
        train_cli.main(
            [
                "sft-runtime-label-provenance-check",
                "--config",
                config.as_posix(),
                "--manifest",
                manifest.as_posix(),
                "--split",
                "train",
                "--output",
                output.as_posix(),
                "--run-runtime-check",
            ]
        )
        == 0
    )

    assert capsys.readouterr().out == ""
    metadata = json.loads(output.read_text(encoding="utf-8"))
    assert metadata["evidence_kind"] == "sft_runtime_label_provenance_observed"
    assert metadata["evidence_status"] == "labels_inspected"
    assert metadata["runtime_gate"]["cli_requested_runtime_check"] is True
    assert metadata["runtime_gate"]["config_allow_runtime_label_provenance_check"] is True
    assert metadata["runtime_gate"]["will_run_runtime_label_provenance_check"] is True


def test_runtime_label_provenance_train_cli_prints_blocked_status_for_outside_root_output(
    tmp_path: Path,
    capsys: Any,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    output = tmp_path / "outside-root" / "runtime.json"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=(resolved_root / "evidence" / "runtime-label-provenance-check").as_posix(),
        evidence_output_dir=(resolved_root / "evidence" / "runtime-label-provenance-check").as_posix(),
    )

    assert (
        train_cli.main(
            [
                "sft-runtime-label-provenance-check",
                "--config",
                config.as_posix(),
                "--manifest",
                manifest.as_posix(),
                "--split",
                "train",
                "--output",
                output.as_posix(),
                "--run-runtime-check",
            ]
        )
        == 0
    )

    assert not output.exists()
    stdout = capsys.readouterr().out
    metadata = json.loads(stdout)
    assert metadata["evidence_kind"] == "sft_runtime_label_provenance_observed"
    assert metadata["evidence_status"] == "blocked_output_outside_approved_root"
    assert metadata["runtime_check_status"] == "blocked_output_outside_approved_root"
    assert metadata["runtime_gate"]["will_run_runtime_label_provenance_check"] is False
    assert "runtime_output_outside_approved_root" in metadata["evidence_gaps"]
    assert tmp_path.as_posix() not in stdout
    assert output.as_posix() not in stdout


def test_runtime_label_provenance_train_cli_does_not_write_skipped_status_outside_root(
    tmp_path: Path,
    capsys: Any,
) -> None:
    manifest = _write_manifest(tmp_path)
    resolved_root = tmp_path / "private-a100-root"
    output = tmp_path / "outside-root" / "skipped.json"
    config = _write_runtime_label_provenance_config(
        tmp_path,
        allow_runtime_check=True,
        output_root=resolved_root.as_posix(),
        adapter_path=(resolved_root / "runs" / "adapter").as_posix(),
        runtime_check_output_dir=(resolved_root / "evidence" / "runtime-label-provenance-check").as_posix(),
        evidence_output_dir=(resolved_root / "evidence" / "runtime-label-provenance-check").as_posix(),
    )

    assert (
        train_cli.main(
            [
                "sft-runtime-label-provenance-check",
                "--config",
                config.as_posix(),
                "--manifest",
                manifest.as_posix(),
                "--output",
                output.as_posix(),
            ]
        )
        == 0
    )

    assert not output.exists()
    stdout = capsys.readouterr().out
    metadata = json.loads(stdout)
    assert metadata["evidence_status"] == "skipped_no_runtime_opt_in"
    assert metadata["output_root_policy"]["status"] == "blocked_output_outside_approved_root"
    assert metadata["runtime_gate"]["will_run_runtime_label_provenance_check"] is False
    assert tmp_path.as_posix() not in stdout
    assert output.as_posix() not in stdout


def test_runtime_label_provenance_train_cli_does_not_write_unresolved_status_outside_root(
    tmp_path: Path,
    capsys: Any,
) -> None:
    manifest = _write_manifest(tmp_path)
    output = tmp_path / "outside-root" / "unresolved.json"
    config = _write_runtime_label_provenance_config(tmp_path, allow_runtime_check=True)

    assert (
        train_cli.main(
            [
                "sft-runtime-label-provenance-check",
                "--config",
                config.as_posix(),
                "--manifest",
                manifest.as_posix(),
                "--output",
                output.as_posix(),
                "--run-runtime-check",
            ]
        )
        == 0
    )

    assert not output.exists()
    stdout = capsys.readouterr().out
    metadata = json.loads(stdout)
    assert metadata["evidence_status"] == "blocked_unresolved_private_override"
    assert metadata["output_root_policy"]["status"] == "blocked_unresolved_template"
    assert metadata["private_override"]["status"] == "unresolved"
    assert tmp_path.as_posix() not in stdout
    assert output.as_posix() not in stdout


def test_sft_heavy_training_requires_cli_and_config_opt_ins(monkeypatch: Any, tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    calls: list[Path] = []

    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(
        training,
        "_run_real_sft",
        lambda metadata, config, manifest_path, output_dir: calls.append(output_dir),
    )

    allowed_root = tmp_path / "remote-root"
    config_allows = _write_config(tmp_path, allow_heavy_training=True, output_root=allowed_root.as_posix())
    dry_run_meta = run_sft(
        config_path=config_allows,
        manifest_path=manifest,
        output_dir=tmp_path / "dry-run",
        dry_run=True,
    )
    assert calls == []
    assert dry_run_meta["heavy_training_gate"] == {
        "cli_run_training": False,
        "config_allow_heavy_training": True,
        "will_run_heavy_training": False,
    }
    assert dry_run_meta["command_summary"]["mode"] == "dry_run"

    config_blocks = _write_config(tmp_path, allow_heavy_training=False)
    blocked_meta = run_sft(
        config_path=config_blocks,
        manifest_path=manifest,
        output_dir=tmp_path / "blocked",
        dry_run=False,
    )
    assert calls == []
    assert blocked_meta["release_status"] == "not_released"
    assert blocked_meta["training_status"] == "training_skipped_by_config"
    assert blocked_meta["heavy_training_gate"] == {
        "cli_run_training": True,
        "config_allow_heavy_training": False,
        "will_run_heavy_training": False,
    }

    run_meta = run_sft(
        config_path=config_allows,
        manifest_path=manifest,
        output_dir=allowed_root / "runs" / "run",
        dry_run=False,
    )
    assert calls == [allowed_root / "runs" / "run"]
    assert run_meta["release_status"] == "not_released"
    assert run_meta["heavy_training_gate"]["will_run_heavy_training"] is True
    assert run_meta["command_summary"]["mode"] == "run_training"


def test_sft_a100_run_training_blocks_output_outside_configured_root(monkeypatch: Any, tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    allowed_root = tmp_path / "allowed-root"
    config = _write_config(tmp_path, allow_heavy_training=True, output_root=allowed_root.as_posix())
    calls: list[Path] = []
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(
        training,
        "_run_real_sft",
        lambda metadata, config, manifest_path, output_dir: calls.append(output_dir),
    )

    metadata = run_sft(
        config_path=config,
        manifest_path=manifest,
        output_dir=tmp_path / "outside-root",
        dry_run=False,
    )

    assert calls == []
    assert metadata["release_status"] == "not_released"
    assert metadata["training_status"] == "training_blocked_by_output_policy"
    assert metadata["heavy_training_gate"]["will_run_heavy_training"] is False
    assert "outside configured output_root" in metadata["notes"]


def test_sft_a100_run_training_blocks_unresolved_public_template_output_root(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_config(tmp_path, allow_heavy_training=True, output_root="<a100_project_root>")
    calls: list[Path] = []
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(
        training,
        "_run_real_sft",
        lambda metadata, config, manifest_path, output_dir: calls.append(output_dir),
    )

    metadata = run_sft(
        config_path=config,
        manifest_path=manifest,
        output_dir=Path("<a100_project_root>") / "runs" / "run",
        dry_run=False,
    )

    assert calls == []
    assert metadata["release_status"] == "not_released"
    assert metadata["training_status"] == "training_blocked_by_output_policy"
    assert metadata["heavy_training_gate"]["will_run_heavy_training"] is False
    assert "unresolved output_root template" in metadata["notes"]


def _install_fake_training_modules(
    monkeypatch: Any,
    *,
    sft_trainer_class: type[Any],
    dataset_records: list[list[dict[str, list[int]]]],
    trainer_calls: list[dict[str, Any]],
    saved_paths: list[str],
) -> None:
    class FakeDataset:
        @staticmethod
        def from_list(records: list[dict[str, list[int]]]) -> list[dict[str, list[int]]]:
            dataset_records.append(records)
            return records

    class FakeModel:
        def save_pretrained(self, path: str) -> None:
            saved_paths.append(path)

    class FakeAutoModelForCausalLM:
        @staticmethod
        def from_pretrained(base_model: str) -> FakeModel:
            assert base_model == "fake-qwen"
            return FakeModel()

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(base_model: str) -> _RuntimeInspectableTokenizer:
            assert base_model == "fake-qwen"
            return _RuntimeInspectableTokenizer()

    class FakeTrainingArguments:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class FakeTransformersTrainer:
        def __init__(self, **kwargs: Any) -> None:
            trainer_calls.append(kwargs)
            self.model = kwargs["model"]

        def train(self) -> None:
            return None

    fake_datasets = types.SimpleNamespace(Dataset=FakeDataset)
    fake_transformers = types.SimpleNamespace(
        AutoModelForCausalLM=FakeAutoModelForCausalLM,
        AutoTokenizer=FakeAutoTokenizer,
        Trainer=FakeTransformersTrainer,
        TrainingArguments=FakeTrainingArguments,
    )
    fake_peft = types.SimpleNamespace(
        LoraConfig=lambda **kwargs: {"lora": kwargs},
        get_peft_model=lambda model, peft_config: model,
    )
    fake_trl = types.SimpleNamespace(SFTTrainer=sft_trainer_class)
    monkeypatch.setitem(sys.modules, "datasets", fake_datasets)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setitem(sys.modules, "peft", fake_peft)
    monkeypatch.setitem(sys.modules, "trl", fake_trl)


def test_real_sft_heavy_path_keeps_new_trl_sfttrainer_with_assistant_only_labels(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    rows = training._load_sft_training_rows(manifest, split="train")  # noqa: SLF001
    target = canonical_contract_json(rows[0].target_contract)
    dataset_records: list[list[dict[str, list[int]]]] = []
    sft_trainer_calls: list[dict[str, Any]] = []
    trainer_calls: list[dict[str, Any]] = []
    saved_paths: list[str] = []

    class FakeSFTTrainer:
        def __init__(
            self,
            *,
            model: Any,
            processing_class: Any,
            train_dataset: list[dict[str, list[int]]],
            args: Any,
            peft_config: dict[str, Any],
            data_collator: Any,
        ) -> None:
            sft_trainer_calls.append(
                {
                    "model": model,
                    "processing_class": processing_class,
                    "train_dataset": train_dataset,
                    "args": args,
                    "peft_config": peft_config,
                    "data_collator": data_collator,
                }
            )
            self.model = model

        def train(self) -> None:
            return None

    _install_fake_training_modules(
        monkeypatch,
        sft_trainer_class=FakeSFTTrainer,
        dataset_records=dataset_records,
        trainer_calls=trainer_calls,
        saved_paths=saved_paths,
    )

    training._run_real_sft(  # noqa: SLF001
        {"adapter_path": (tmp_path / "adapter").as_posix()},
        {
            "base_model": "fake-qwen",
            "dataset_split": "train",
            "max_seq_length": SHARED_PREFIX_RUNTIME_SFT_MAX_SEQ_LENGTH,
            "lora": {"r": 8, "alpha": 16, "dropout": 0.05, "target_modules": ["q_proj"]},
        },
        manifest,
        tmp_path / "run",
    )

    assert trainer_calls == []
    assert len(sft_trainer_calls) == 1
    assert dataset_records
    record = dataset_records[0][0]
    loss_text = "".join(
        chr(token_id)
        for token_id, label in zip(record["input_ids"], record["labels"], strict=True)
        if label != -100
    )
    assert loss_text == target
    assert isinstance(sft_trainer_calls[0]["processing_class"], _RuntimeInspectableTokenizer)
    assert sft_trainer_calls[0]["data_collator"].__class__.__name__ == "_AssistantOnlyCausalLmDataCollator"
    assert "dataset_text_field" not in sft_trainer_calls[0]
    assert "tokenizer" not in sft_trainer_calls[0]
    assert saved_paths == [(tmp_path / "adapter").as_posix()]


def test_real_sft_heavy_path_supports_old_trl_sfttrainer_tokenizer_signature(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    dataset_records: list[list[dict[str, list[int]]]] = []
    sft_trainer_calls: list[dict[str, Any]] = []
    trainer_calls: list[dict[str, Any]] = []
    saved_paths: list[str] = []

    class FakeSFTTrainer:
        def __init__(
            self,
            *,
            model: Any,
            tokenizer: Any,
            train_dataset: list[dict[str, list[int]]],
            args: Any,
            peft_config: dict[str, Any],
            data_collator: Any,
        ) -> None:
            sft_trainer_calls.append(
                {
                    "model": model,
                    "tokenizer": tokenizer,
                    "train_dataset": train_dataset,
                    "args": args,
                    "peft_config": peft_config,
                    "data_collator": data_collator,
                }
            )
            self.model = model

        def train(self) -> None:
            return None

    _install_fake_training_modules(
        monkeypatch,
        sft_trainer_class=FakeSFTTrainer,
        dataset_records=dataset_records,
        trainer_calls=trainer_calls,
        saved_paths=saved_paths,
    )

    training._run_real_sft(  # noqa: SLF001
        {"adapter_path": (tmp_path / "adapter").as_posix()},
        {
            "base_model": "fake-qwen",
            "dataset_split": "train",
            "max_seq_length": SHARED_PREFIX_RUNTIME_SFT_MAX_SEQ_LENGTH,
            "lora": {"r": 8, "alpha": 16, "dropout": 0.05, "target_modules": ["q_proj"]},
        },
        manifest,
        tmp_path / "run",
    )

    assert trainer_calls == []
    assert len(sft_trainer_calls) == 1
    assert isinstance(sft_trainer_calls[0]["tokenizer"], _RuntimeInspectableTokenizer)
    assert "processing_class" not in sft_trainer_calls[0]
    assert saved_paths == [(tmp_path / "adapter").as_posix()]


def test_real_sft_heavy_path_limits_tiny_overfit_rows_and_records_metadata(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_multirow_manifest(tmp_path, train_rows=4)
    dataset_records: list[list[dict[str, list[int]]]] = []
    sft_trainer_calls: list[dict[str, Any]] = []
    trainer_calls: list[dict[str, Any]] = []
    saved_paths: list[str] = []

    class FakeSFTTrainer:
        def __init__(
            self,
            *,
            model: Any,
            processing_class: Any,
            train_dataset: list[dict[str, list[int]]],
            args: Any,
            peft_config: dict[str, Any],
            data_collator: Any,
        ) -> None:
            sft_trainer_calls.append(
                {
                    "model": model,
                    "processing_class": processing_class,
                    "train_dataset": train_dataset,
                    "args": args,
                    "peft_config": peft_config,
                    "data_collator": data_collator,
                }
            )
            self.model = model

        def train(self) -> None:
            return None

    _install_fake_training_modules(
        monkeypatch,
        sft_trainer_class=FakeSFTTrainer,
        dataset_records=dataset_records,
        trainer_calls=trainer_calls,
        saved_paths=saved_paths,
    )

    metadata = {"adapter_path": (tmp_path / "adapter").as_posix(), "dataset_load": {}}
    training._run_real_sft(  # noqa: SLF001
        metadata,
        {
            "base_model": "fake-qwen",
            "dataset_split": "train",
            "max_train_rows": 2,
            "max_seq_length": SHARED_PREFIX_RUNTIME_SFT_MAX_SEQ_LENGTH,
            "lora": {"r": 8, "alpha": 16, "dropout": 0.05, "target_modules": ["q_proj"]},
        },
        manifest,
        tmp_path / "run",
    )

    assert trainer_calls == []
    assert len(sft_trainer_calls) == 1
    assert len(dataset_records[0]) == 2
    assert metadata["training_split"] == "train"
    assert metadata["training_row_limit"] == 2
    assert metadata["training_rows_used"] == 2
    assert metadata["training_row_ids"] == ["sft-1", "sft-2"]
    assert metadata["dataset_load"]["training_rows_used"] == 2
    assert metadata["dataset_load"]["training_row_ids"] == ["sft-1", "sft-2"]
    assert metadata["dataset_load"]["loaded_rows_before_training_row_limit"] == 4


def test_sft_metadata_contains_public_safe_a100_smoke_fields(monkeypatch: Any, tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    allowed_root = tmp_path / "remote-root"
    config = _write_config(tmp_path, allow_heavy_training=True, output_root=allowed_root.as_posix())
    output_dir = allowed_root / "runs" / "run"
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)
    monkeypatch.setattr(training, "_run_real_sft", lambda metadata, config, manifest_path, output_dir: None)

    metadata = run_sft(config_path=config, manifest_path=manifest, output_dir=output_dir, dry_run=False)

    assert metadata["release_status"] == "not_released"
    assert metadata["dataset_manifest_id"] == "public-sample-test"
    assert metadata["gpu_selection_policy"]["policy"] == "select_idle_gpu_only_no_process_interruption"
    assert metadata["gpu_selection_policy"]["identifier_policy"] == "policy_only_no_host_ip_or_gpu_uuid"
    assert metadata["output_paths"]["run_output_dir"] == output_dir.as_posix()
    assert metadata["output_paths"]["adapter_path"] == (output_dir / "adapter").as_posix()
    assert metadata["output_paths"]["metadata_path"] == (output_dir / "adapter_metadata.json").as_posix()
    assert metadata["output_paths"]["configured_output_root"] == allowed_root.as_posix()
    assert metadata["command_summary"]["entrypoint"] == "voice2task-train sft"
    assert metadata["command_summary"]["requires_cli_run_training"] is True
    assert metadata["command_summary"]["requires_config_allow_heavy_training"] is True
    assert metadata["command_summary"]["mode"] == "run_training"
    assert set(metadata["package_versions"]).issuperset(
        {"python", "accelerate", "datasets", "peft", "transformers", "trl"}
    )
    assert all("/" not in str(version) for version in metadata["package_versions"].values())


def test_sft_training_failure_writes_sanitized_metadata(monkeypatch: Any, tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    allowed_root = tmp_path / "remote-root"
    config = _write_config(tmp_path, allow_heavy_training=True, output_root=allowed_root.as_posix())
    output_dir = allowed_root / "runs" / "run"
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: True)

    def fail_training(metadata: dict[str, Any], config: dict[str, Any], manifest_path: Path, output_dir: Path) -> None:
        raise RuntimeError("Network is unreachable while reading /" + "Users/person/token.txt")

    monkeypatch.setattr(training, "_run_real_sft", fail_training)

    with pytest.raises(RuntimeError):
        run_sft(config_path=config, manifest_path=manifest, output_dir=output_dir, dry_run=False)

    metadata = json.loads((output_dir / "adapter_metadata.json").read_text(encoding="utf-8"))
    assert metadata["release_status"] == "not_released"
    assert metadata["training_status"] == "training_failed"
    assert metadata["error_category"] == "model_download_unavailable"
    assert metadata["error_summary"] == "Training failed before completion; raw logs remain private."
    assert "Users" not in json.dumps(metadata)


def test_public_a100_smoke_evidence_sample_is_safe_and_honest() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-sft-smoke"
    manifest_path = evidence_dir / "manifest.json"
    report_path = evidence_dir / "report.md"

    assert manifest_path.exists()
    assert report_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8").lower()

    assert manifest["release_status"] == "not_released"
    assert manifest["claims"]["checkpoint_release"] is False
    assert manifest["claims"]["live_browser_benchmark_claim"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert "not a checkpoint release" in report
    assert "no live-browser benchmark improvement claim" in report
    assert scan_paths([evidence_dir]).ok is True


def test_public_a100_smoke_evidence_omits_exact_remote_run_paths() -> None:
    evidence_dir = REPO_ROOT / "reports" / "public-sample" / "a100-sft-smoke"
    human_brief = REPO_ROOT / "docs" / "human-briefs" / "2026-06-02-a100-sft-smoke-run.html"
    runbook = REPO_ROOT / "README.md"
    smoke_config = REPO_ROOT / "configs" / "sft-a100-public-smoke.json"
    exact_private_paths = [
        A100_PROJECT_DIR + "/runs/a100-sft-public-smoke",
        A100_PROJECT_DIR + "/runs/a100-sft-public-smoke-modelscope",
        A100_PROJECT_DIR + "/models/Qwen2.5-0.5B-Instruct-modelscope",
    ]

    public_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [*sorted(evidence_dir.glob("*")), human_brief, runbook, smoke_config]
        if path.is_file()
    )

    for private_path in exact_private_paths:
        assert private_path not in public_text


def test_evidence_leak_scan_rejects_ssh_details_private_rows_and_oversized_corpora(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    bad_report = evidence_dir / "report.md"
    bad_report.write_text(
        "\n".join(
            [
                "api_" + "key=abcd1234efgh",
                "ssh " + "operator@10" + ".1.2.3",
                "/" + "Users/person/private.jsonl",
            ]
        ),
        encoding="utf-8",
    )
    (evidence_dir / "raw-private.jsonl").write_text(
        '{"provenance":{"public_safe":false}}\n',
        encoding="utf-8",
    )
    (evidence_dir / "generated.jsonl").write_text("{}\n" * 6, encoding="utf-8")

    result = scan_paths([evidence_dir], max_public_jsonl_rows=5)

    assert {
        "private_path",
        "secret",
        "private_ip",
        "ssh_detail",
        "raw_private_row",
        "oversized_public_corpus",
    }.issubset({finding.category for finding in result.findings})
