import json
import sys
import types
from pathlib import Path
from typing import Any

from voice2task import training
from voice2task.cli import report as report_cli
from voice2task.cli import train as train_cli
from voice2task.evaluation import evaluate_predictions, load_predictions
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_prediction_evidence_pack
from voice2task.schemas import ROUTES, TASK_TYPES, SFTDatasetRow
from voice2task.training import run_sft_prediction_export

A100_PROJECT_ROOT = "/mnt/data/" + "minghongsun/voice2task-post-training"


def _contract(query: str) -> dict[str, Any]:
    return {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": query},
        "normalized_command": f"搜索{query}",
        "language": "zh-CN",
        "contract_version": "v1",
    }


def _write_manifest(tmp_path: Path) -> Path:
    rows = tmp_path / "sft_public_sample.jsonl"
    rows.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": row_id,
                    "split": split,
                    "input_text": f"帮我搜索{query}",
                    "target_contract": _contract(query),
                    "provenance": {"source_id": row_id, "public_safe": True},
                },
                ensure_ascii=False,
            )
            for row_id, split, query in (
                ("sft-train-1", "train", "天气"),
                ("sft-test-1", "test", "机票"),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_id": "public-sample-test",
                "files": {"sft": rows.name},
                "counts": {"sft_rows": 2},
            }
        ),
        encoding="utf-8",
    )
    return manifest


def _write_prediction_config(
    tmp_path: Path,
    *,
    allow_private_prediction: bool = True,
    adapter_path: str | None = "<a100_project_root>/runs/a100-sft-public-smoke/adapter",
    output_root: str = A100_PROJECT_ROOT,
) -> Path:
    config = {
        "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_source": "modelscope",
        "allow_private_prediction": allow_private_prediction,
        "adapter_path": adapter_path,
        "output_root": output_root,
        "prediction_split": "all",
    }
    if adapter_path is None:
        config.pop("adapter_path")
    config_path = tmp_path / "prediction-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def test_sft_prediction_export_requires_explicit_opt_in_and_adapter_config(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    output = tmp_path / "predictions.jsonl"
    config = _write_prediction_config(tmp_path)

    dry_run = run_sft_prediction_export(config, manifest, output, dry_run=True, fixture_mode=False)

    assert output.exists() is False
    assert dry_run["prediction_status"] == "prediction_skipped_no_opt_in"
    assert dry_run["release_status"] == "not_released"
    assert dry_run["formatting_policy"]["prediction_prompt"] == "shared_contract_chat_template"
    assert dry_run["prompt_constraints"]["task_type_enum_visible"] is True
    assert dry_run["prompt_constraints"]["route_enum_visible"] is True
    assert dry_run["prompt_constraints"]["route_not_url_or_path_visible"] is True
    assert dry_run["prompt_constraints"]["slots_object_not_array_visible"] is True
    assert dry_run["prompt_constraints"]["canonical_json_one_shot_visible"] is True
    assert dry_run["prompt_constraints"]["whole_object_boundary_visible"] is True
    assert dry_run["prompt_constraints"]["route_execution_channel_visible"] is True
    assert dry_run["prompt_constraints"]["route_domain_values_not_route_visible"] is True
    assert dry_run["prompt_constraints"]["weather_to_search_route_example_visible"] is True
    assert dry_run["prediction_output_boundary"]["exact_json_only_output_visible"] is True
    assert dry_run["prediction_output_boundary"]["no_text_outside_root_json_object_visible"] is True
    assert dry_run["prediction_output_boundary"]["strict_whole_object_parser_boundary_visible"] is True
    assert dry_run["prediction_output_boundary"]["no_prefix_suffix_text_visible"] is True
    assert dry_run["prediction_output_boundary"]["no_trailing_analysis_visible"] is True
    assert dry_run["prediction_output_boundary"]["no_second_json_object_visible"] is True
    assert dry_run["decoding_policy"] == {
        "strategy": "greedy",
        "do_sample": False,
        "max_new_tokens": 256,
        "raw_decoded_sidecar_written": False,
        "schema_repair_applied": False,
        "schema_guard_enabled": True,
        "schema_retry_enabled": True,
        "schema_retry_max_attempts": 1,
    }

    missing_adapter_config = _write_prediction_config(tmp_path, adapter_path=None)
    blocked = run_sft_prediction_export(missing_adapter_config, manifest, output, dry_run=False, fixture_mode=False)

    assert output.exists() is False
    assert blocked["prediction_status"] == "prediction_blocked_missing_adapter"
    assert blocked["prediction_gate"]["will_run_private_prediction"] is False
    assert blocked["decoding_policy"]["schema_repair_applied"] is False


def test_route_task_ontology_output_repair_evidence_is_public_safe_and_bounded() -> None:
    evidence_dir = Path("reports/public-sample/route-task-ontology-output-repair")
    summary = json.loads((evidence_dir / "repair_summary.json").read_text(encoding="utf-8"))
    markdown = (evidence_dir / "repair_summary.md").read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    serialized = json.dumps(summary, ensure_ascii=False, sort_keys=True) + markdown

    assert summary["evidence_kind"] == "route_task_ontology_output_repair_local"
    assert summary["a100_execution"] is False
    assert summary["private_prediction_run"] is False
    assert summary["training_run"] is False
    assert summary["schema_repair_applied"] is False
    assert summary["source_prior_phase"] == "reports/public-sample/a100-constrained-output-train-split-rerun"
    assert summary["prior_failure_context"]["row_id"] == "seed-search-weather"
    assert summary["prior_failure_context"]["invalid_route"] == "weather"
    assert summary["prompt_constraints"]["route_execution_channel_visible"] is True
    assert summary["prompt_constraints"]["route_domain_values_not_route_visible"] is True
    assert summary["prompt_constraints"]["weather_to_search_route_example_visible"] is True
    assert summary["claims"]["a100_model_recovery_claim"] is False
    assert summary["claims"]["held_out_generalization_claim"] is False
    assert summary["claims"]["production_readiness_claim"] is False
    assert summary["claims"]["live_browser_benchmark_claim"] is False
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert "did not train" in serialized
    assert "did not run private prediction or A100 execution" in serialized
    assert "did not repair or coerce model outputs" in serialized
    assert "does not prove model recovery" in serialized
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized


def test_confirmation_required_emission_repair_evidence_is_public_safe_and_bounded() -> None:
    evidence_dir = Path("reports/public-sample/confirmation-required-emission-repair")
    summary = json.loads((evidence_dir / "repair_summary.json").read_text(encoding="utf-8"))
    markdown = (evidence_dir / "repair_summary.md").read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    serialized = json.dumps(summary, ensure_ascii=False, sort_keys=True) + markdown

    assert summary["evidence_kind"] == "confirmation_required_emission_repair_local"
    assert summary["a100_execution"] is False
    assert summary["private_prediction_run"] is False
    assert summary["training_run"] is False
    assert summary["schema_repair_applied"] is False
    assert summary["output_coercion_applied"] is False
    assert summary["source_prior_phase"] == "reports/public-sample/a100-route-ontology-train-split-rerun"
    assert summary["prior_failure_context"]["missing_confirmation_required_count"] == 3
    assert summary["prompt_constraints"]["confirmation_required_boolean_visible"] is True
    assert summary["prompt_constraints"]["weather_to_search_confirmation_false_visible"] is True
    assert summary["diagnostic_changes"]["missing_confirmation_required_count_visible"] is True
    assert summary["claims"]["a100_model_recovery_claim"] is False
    assert summary["claims"]["held_out_generalization_claim"] is False
    assert summary["claims"]["production_readiness_claim"] is False
    assert summary["claims"]["live_browser_benchmark_claim"] is False
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert "did not train" in serialized
    assert "did not run private prediction or A100 execution" in serialized
    assert "does not fill missing confirmation_required" in serialized
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized


def test_a100_route_ontology_train_split_rerun_evidence_is_public_safe_and_bounded() -> None:
    evidence_dir = Path("reports/public-sample/a100-route-ontology-train-split-rerun")
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "route_ontology_diagnosis.json",
        "route_ontology_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "route_ontology_diagnosis.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    metrics_markdown = (evidence_dir / "metrics.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "route_ontology_diagnosis.md").read_text(encoding="utf-8")
    serialized = (
        json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        + json.dumps(manifest, ensure_ascii=False, sort_keys=True)
        + json.dumps(metrics, ensure_ascii=False, sort_keys=True)
        + json.dumps(schema_guard, ensure_ascii=False, sort_keys=True)
        + json.dumps(diagnosis, ensure_ascii=False, sort_keys=True)
        + report
        + metrics_markdown
        + diagnosis_markdown
    )

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["prompt_constraints"]["route_execution_channel_visible"] is True
    assert metadata["prompt_constraints"]["route_domain_values_not_route_visible"] is True
    assert metadata["prompt_constraints"]["weather_to_search_route_example_visible"] is True
    assert metadata["decoding_policy"]["schema_repair_applied"] is False
    assert metadata["decoding_policy"]["schema_retry_enabled"] is True
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_quality_evidence"] is False
    assert metrics["metadata"]["prediction_split"] == "train"
    assert metrics["metadata"]["generalization_claim"] is False
    assert metrics["metadata"]["strict_final_contract_metrics"] is True
    assert metrics["metadata"]["strict_final_route_accuracy"] == 0.0
    assert metrics["route_ontology_counts"]["route_value_counts"] == {"search_web": 3}
    assert metrics["route_ontology_counts"]["route_enum_valid_count"] == 3
    assert metrics["route_ontology_counts"]["raw_gold_route_match_count"] == 3
    assert metrics["route_ontology_counts"]["missing_confirmation_required_count"] == 3
    assert metrics["route_ontology_counts"]["validated_output_schema_valid_count"] == 0
    assert metrics["route_ontology_counts"]["strict_final_route_accuracy_explanation"]
    assert schema_guard["summary"]["prediction_count"] == 3
    assert diagnosis["diagnostic_kind"] == "route_ontology_train_split_diagnosis"
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["route_value_counts"] == {"search_web": 3}
    assert diagnosis["summary"]["route_enum_valid_count"] == 3
    assert diagnosis["summary"]["raw_gold_route_match_count"] == 3
    assert diagnosis["summary"]["missing_confirmation_required_count"] == 3
    assert diagnosis["summary"]["validated_output_schema_valid_count"] == 0
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert "train-internal" in report
    assert "no held-out generalization claim" in report
    assert "route ontology" in report
    assert "strict final-contract route accuracy" in report
    assert "raw route ontology / gold-route match: `3/3`" in report
    assert "strict final-contract route accuracy" in metrics_markdown
    assert "raw route ontology / gold-route match: `3/3`" in metrics_markdown
    assert "Strict final route accuracy remains `0.0000`" in diagnosis_markdown
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized


def test_a100_confirmation_required_train_split_rerun_evidence_is_public_safe_and_bounded() -> None:
    evidence_dir = Path("reports/public-sample/a100-confirmation-required-train-split-rerun")
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "confirmation_required_diagnosis.json",
        "confirmation_required_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "confirmation_required_diagnosis.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    prediction_rows = [
        json.loads(line)
        for line in (evidence_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    raw_rows = [
        json.loads(line)
        for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    generation_trace_rows = [
        json.loads(line)
        for line in (evidence_dir / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train_gold_rows = [
        json.loads(line)
        for line in (evidence_dir / "train_split_gold.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    metrics_markdown = (evidence_dir / "metrics.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "confirmation_required_diagnosis.md").read_text(encoding="utf-8")
    serialized = (
        json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        + json.dumps(manifest, ensure_ascii=False, sort_keys=True)
        + json.dumps(metrics, ensure_ascii=False, sort_keys=True)
        + json.dumps(schema_guard, ensure_ascii=False, sort_keys=True)
        + json.dumps(diagnosis, ensure_ascii=False, sort_keys=True)
        + report
        + metrics_markdown
        + diagnosis_markdown
    )

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["prompt_constraints"]["confirmation_required_boolean_visible"] is True
    assert metadata["prompt_constraints"]["weather_to_search_confirmation_false_visible"] is True
    assert metadata["decoding_policy"]["schema_repair_applied"] is False
    assert metadata["decoding_policy"]["schema_retry_enabled"] is True
    assert manifest["evidence_kind"] == "a100_confirmation_required_train_split_rerun"
    assert manifest["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["prediction_split"] == "train"
    assert manifest["prediction_count"] == 3
    assert manifest["training_rows_used"] == 3
    assert manifest["training_row_ids"] == expected_row_ids
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_quality_evidence"] is False
    assert manifest["claims"]["schema_repair_or_coercion_applied"] is False
    assert manifest["observed_result"]["raw_attempt_schema_valid_count"] == 2
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 2
    assert manifest["observed_result"]["missing_confirmation_required_count"] == 1
    assert manifest["observed_result"]["confirmation_required_boolean_count"] == 2
    assert manifest["observed_result"]["train_internal_partial_recovery_observed"] is True
    assert manifest["observed_result"]["train_internal_full_recovery_observed"] is False
    assert manifest["diagnostic_artifacts"]["post_archive_leak_scan"].endswith("post_archive_leak_scan_result.json")
    assert manifest["diagnostic_artifacts"]["final_leak_scan"].endswith("final_leak_scan_result.json")
    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in generation_trace_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert metrics["metadata"]["prediction_split"] == "train"
    assert metrics["metadata"]["generalization_claim"] is False
    assert metrics["metadata"]["strict_final_contract_metrics"] is True
    assert metrics["metrics"]["json_valid_rate"] == 2 / 3
    assert metrics["metrics"]["contract_exact_match"] == 0.0
    assert metrics["confirmation_required_counts"]["missing_confirmation_required_count"] == 1
    assert metrics["confirmation_required_counts"]["confirmation_required_boolean_count"] == 2
    assert metrics["confirmation_required_counts"]["raw_attempt_schema_valid_count"] == 2
    assert metrics["confirmation_required_counts"]["validated_output_schema_valid_count"] == 2
    assert metrics["confirmation_required_counts"]["validated_output_source_counts"] == {"none": 1, "raw_attempt": 2}
    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["raw_attempt_schema_valid_count"] == 2
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == 2
    assert schema_guard["summary"]["retry_attempted_count"] == 1
    assert schema_guard["summary"]["strict_retry_parser_rejected_fragment_count"] == 1
    assert diagnosis["diagnostic_kind"] == "confirmation_required_train_split_diagnosis"
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["missing_confirmation_required_count"] == 1
    assert diagnosis["summary"]["confirmation_required_boolean_count"] == 2
    assert diagnosis["summary"]["confirmation_required_false_count"] == 2
    assert diagnosis["summary"]["validated_output_schema_valid_count"] == 2
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "train-internal" in report
    assert "no held-out generalization claim" in report
    assert "confirmation_required" in report
    assert "partial recovery" in report
    assert "final validated schema-valid `2/3`" in report
    assert "not be described as full model recovery" in report
    assert "confirmation_required boolean emission: `2/3`" in metrics_markdown
    assert "Missing `confirmation_required`: `1/3`" in diagnosis_markdown
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert scan_paths([evidence_dir]).ok is True
    assert "volcano" not in serialized


def test_a100_normalized_command_policy_train_split_rerun_evidence_is_public_safe_and_bounded() -> None:
    evidence_dir = Path("reports/public-sample/a100-normalized-command-policy-train-split-rerun")
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "normalized_command_diagnosis.json",
        "normalized_command_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "normalized_command_diagnosis.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    prediction_rows = [
        json.loads(line)
        for line in (evidence_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    raw_rows = [
        json.loads(line)
        for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    generation_trace_rows = [
        json.loads(line)
        for line in (evidence_dir / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train_gold_rows = [
        json.loads(line)
        for line in (evidence_dir / "train_split_gold.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    metrics_markdown = (evidence_dir / "metrics.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "normalized_command_diagnosis.md").read_text(encoding="utf-8")
    serialized = (
        json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        + json.dumps(manifest, ensure_ascii=False, sort_keys=True)
        + json.dumps(metrics, ensure_ascii=False, sort_keys=True)
        + json.dumps(schema_guard, ensure_ascii=False, sort_keys=True)
        + json.dumps(diagnosis, ensure_ascii=False, sort_keys=True)
        + report
        + metrics_markdown
        + diagnosis_markdown
    )

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["prompt_constraints"]["normalized_command_canonical_policy_visible"] is True
    assert metadata["prompt_constraints"]["normalized_command_public_examples_visible"] is True
    assert metadata["prompt_constraints"]["normalized_command_no_metric_relaxation_visible"] is True
    assert metadata["decoding_policy"]["schema_repair_applied"] is False
    assert metadata["decoding_policy"]["schema_retry_enabled"] is True
    assert manifest["evidence_kind"] == "a100_normalized_command_policy_train_split_rerun"
    assert manifest["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["prediction_split"] == "train"
    assert manifest["prediction_count"] == 3
    assert manifest["training_rows_used"] == 3
    assert manifest["training_row_ids"] == expected_row_ids
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_quality_evidence"] is False
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["normalized_command_normalization_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["evaluator_metric_change_performed"] is False
    assert manifest["diagnostic_artifacts"]["post_archive_leak_scan"].endswith(
        "post_archive_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["final_leak_scan"].endswith("final_leak_scan_result.json")
    assert manifest["observed_result"]["normalized_command_exact_match_count"] == 2
    assert manifest["observed_result"]["normalized_command_mismatch_count"] == 1
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 1
    assert manifest["observed_result"]["train_internal_full_contract_recovery_observed"] is False
    assert manifest["observed_result"]["train_internal_normalized_command_partial_improvement_observed"] is True
    assert manifest["prior_context"]["prior_normalized_command_exact_match_count"] == 0
    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in generation_trace_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert metrics["metadata"]["prediction_split"] == "train"
    assert metrics["metadata"]["generalization_claim"] is False
    assert metrics["metadata"]["strict_final_contract_metrics"] is True
    assert metrics["metadata"]["normalized_command_exact_match_count"] == 2
    assert metrics["metadata"]["normalized_command_mismatch_count"] == 1
    assert metrics["metrics"]["json_valid_rate"] == 1 / 3
    assert metrics["metrics"]["contract_exact_match"] == 0.0
    assert metrics["normalized_command_counts"]["exact_match_count"] == 2
    assert metrics["normalized_command_counts"]["mismatch_count"] == 1
    assert metrics["normalized_command_counts"]["context_counts"]["co_occurs_with_schema_failure"] == 1
    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["raw_attempt_schema_valid_count"] == 1
    assert schema_guard["summary"]["retry_attempted_count"] == 2
    assert schema_guard["summary"]["retry_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == 1
    assert schema_guard["summary"]["strict_retry_parser_rejected_fragment_count"] == 2
    assert schema_guard["summary"]["normalized_command_exact_match_count"] == 2
    assert diagnosis["diagnostic_kind"] == "normalized_command_policy_train_split_diagnosis"
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["normalized_command_exact_match_count"] == 2
    assert diagnosis["summary"]["normalized_command_mismatch_count"] == 1
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["strict_metrics_preserved"] is True
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["normalized_command_normalization_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "train-internal" in report
    assert "no held-out generalization claim" in report
    assert "normalized-command exact-string matches were `2/3`" in report
    assert "must not be described as full train-row recovery" in report
    assert "semantic-equivalence scoring performed: `False`" in metrics_markdown
    assert "no normalization, no semantic-equivalence scoring, no prediction repair" in diagnosis_markdown
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert scan_paths([evidence_dir]).ok is True


def test_a100_normalized_rerun_row_mismatch_diagnosis_pack_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-normalized-command-policy-train-split-rerun")
    evidence_dir = Path("reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis")
    human_brief_path = Path(
        "docs/human-briefs/2026-06-05-diagnose-a100-normalized-rerun-row-mismatches.html"
    )
    change_dirs = [
        Path("openspec/changes/diagnose-a100-normalized-rerun-row-mismatches"),
        Path("openspec/changes/archive/2026-06-05-diagnose-a100-normalized-rerun-row-mismatches"),
    ]
    required_files = {
        "row_mismatch_diagnosis.json",
        "row_mismatch_diagnosis.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    diagnosis = json.loads((evidence_dir / "row_mismatch_diagnosis.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    markdown = (evidence_dir / "row_mismatch_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    prior_metrics = json.loads((prior_dir / "metrics.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            markdown,
            human_brief,
        ]
    )

    assert diagnosis["diagnostic_kind"] == "a100_normalized_rerun_row_mismatch_diagnosis"
    assert diagnosis["summary"]["gold_row_count"] == 3
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["row_mismatch_count"] == 3
    assert diagnosis["summary"]["schema_invalid_prediction_count"] == 2
    assert diagnosis["summary"]["validated_output_schema_valid_count"] == 1
    assert diagnosis["summary"]["normalized_command_exact_match_count"] == 2
    assert diagnosis["summary"]["normalized_command_mismatch_count"] == 1
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == prior_metrics["metrics"]["json_valid_rate"] == 1 / 3
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == (
        prior_metrics["metrics"]["contract_exact_match"]
    ) == 0.0
    assert diagnosis["summary"]["strict_final_task_type_accuracy"] == prior_metrics["metrics"]["task_type_accuracy"]
    assert diagnosis["summary"]["strict_final_route_accuracy"] == prior_metrics["metrics"]["route_accuracy"]
    assert diagnosis["summary"]["strict_final_confirmation_accuracy"] == (
        prior_metrics["metrics"]["confirmation_accuracy"]
    )
    assert diagnosis["summary"]["strict_final_slot_f1"] == prior_metrics["metrics"]["slot_f1"]
    assert diagnosis["summary"]["field_mismatch_counts"] == {
        "confirmation_required": 1,
        "normalized_command": 1,
        "route": 1,
        "safety.reason": 2,
        "slots": 3,
        "task_type": 2,
    }
    assert diagnosis["summary"]["family_counts"] == {
        "schema_invalid_task_type_enum": 1,
        "schema_missing_confirmation_required": 1,
        "schema_valid_task_route_safety_slot_mismatch": 1,
    }
    assert [row["row_id"] for row in diagnosis["rows"]] == expected_row_ids
    row_families = {row["row_id"]: row["primary_failure_family"] for row in diagnosis["rows"]}
    assert row_families == {
        "seed-search-weather": "schema_missing_confirmation_required",
        "seed-search-weather-aug-1": "schema_valid_task_route_safety_slot_mismatch",
        "seed-search-weather-aug-2": "schema_invalid_task_type_enum",
    }
    assert diagnosis["source_artifact_policy"]["uses_prior_public_sample_artifacts_only"] is True
    assert diagnosis["source_artifact_policy"]["a100_execution_performed"] is False
    assert diagnosis["source_artifact_policy"]["prediction_rerun_performed"] is False
    assert diagnosis["source_artifact_policy"]["training_or_decoding_changed"] is False
    assert diagnosis["source_artifact_policy"]["evaluator_metrics_changed"] is False
    assert diagnosis["claims"]["local_evidence_only_analysis"] is True
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["normalized_command_normalization_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False

    assert manifest["evidence_kind"] == "a100_normalized_rerun_row_mismatch_diagnosis"
    assert manifest["source_prior_phase"] == prior_dir.as_posix()
    assert manifest["counts"] == {
        "rows": 3,
        "schema_invalid_predictions": 2,
        "schema_invalid_task_type_enum": 1,
        "schema_missing_confirmation_required": 1,
        "schema_valid_task_route_safety_slot_mismatch": 1,
        "validated_output_schema_valid": 1,
    }
    assert manifest["metrics_preserved"]["json_valid_rate"] == 1 / 3
    assert manifest["metrics_preserved"]["contract_exact_match"] == 0.0
    assert manifest["diagnostic_artifacts"]["row_mismatch_diagnosis"].endswith("row_mismatch_diagnosis.json")
    assert manifest["diagnostic_artifacts"]["row_mismatch_report"].endswith("row_mismatch_diagnosis.md")
    assert manifest["diagnostic_artifacts"]["phase_validation_leak_scan"].endswith(
        "phase_validation_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["post_archive_leak_scan"].endswith(
        "post_archive_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["final_leak_scan"].endswith("final_leak_scan_result.json")
    assert manifest["source_artifacts"]["predictions"].endswith("predictions.jsonl")
    assert manifest["source_artifacts"]["train_split_gold"].endswith("train_split_gold.jsonl")
    assert manifest["claims"]["local_evidence_only_analysis"] is True
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["normalized_command_normalization_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "local evidence-only analysis" in markdown
    assert "No A100 execution was performed in this phase" in markdown
    assert "本地 evidence-only" in human_brief
    assert "不使用 A100" in human_brief
    assert "不改 strict evaluator metrics" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_public_readonly_search_contract_policy_pack_is_public_safe_and_bounded() -> None:
    source_dir = Path("reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis")
    evidence_dir = Path("reports/public-sample/public-readonly-search-contract-policy")
    human_brief_path = Path("docs/human-briefs/2026-06-06-repair-public-readonly-search-contract-policy.html")
    change_dirs = [
        Path("openspec/changes/repair-public-readonly-search-contract-policy"),
        Path("openspec/changes/archive/2026-06-06-repair-public-readonly-search-contract-policy"),
    ]
    expected_artifacts = {
        "repair_summary.json",
        "repair_summary.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }

    assert evidence_dir.exists()
    assert expected_artifacts <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    summary = json.loads((evidence_dir / "repair_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "repair_summary.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    source_diagnosis = json.loads((source_dir / "row_mismatch_diagnosis.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(summary, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            human_brief,
        ]
    )

    assert summary["evidence_kind"] == "public_readonly_search_contract_policy_local"
    assert summary["source_prior_phase"] == source_dir.as_posix()
    assert summary["source_family_counts"] == source_diagnosis["summary"]["family_counts"]
    assert summary["prompt_constraints"]["public_readonly_search_policy_visible"] is True
    assert summary["prompt_constraints"]["public_readonly_safety_reason_visible"] is True
    assert summary["prompt_constraints"]["search_query_slot_guidance_visible"] is True
    assert summary["prompt_constraints"]["task_type_not_route_enum_visible"] is True
    assert summary["claims"]["local_prompt_policy_hardening_only"] is True
    assert summary["claims"]["a100_execution_performed"] is False
    assert summary["claims"]["training_or_prediction_rerun_performed"] is False
    assert summary["claims"]["semantic_equivalence_scoring_performed"] is False
    assert summary["claims"]["slot_normalization_performed"] is False
    assert summary["claims"]["prediction_repair_or_rescore_performed"] is False
    assert summary["claims"]["model_quality_improvement_claim"] is False

    assert manifest["evidence_kind"] == "public_readonly_search_contract_policy_local"
    assert manifest["source_artifacts"]["row_mismatch_diagnosis"].endswith("row_mismatch_diagnosis.json")
    assert manifest["source_artifacts"]["source_manifest"].endswith("manifest.json")
    assert manifest["diagnostic_artifacts"]["repair_summary"].endswith("repair_summary.json")
    assert manifest["diagnostic_artifacts"]["repair_report"].endswith("repair_summary.md")
    assert manifest["diagnostic_artifacts"]["phase_validation_leak_scan"].endswith(
        "phase_validation_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["post_archive_leak_scan"].endswith(
        "post_archive_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["final_leak_scan"].endswith("final_leak_scan_result.json")
    assert manifest["claims"]["local_prompt_policy_hardening_only"] is True
    assert manifest["claims"]["a100_execution_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "local prompt/policy hardening only" in report
    assert "No A100 execution was performed" in report
    assert "本地 prompt/policy hardening" in human_brief
    assert "不使用 A100" in human_brief
    assert "不改 evaluator metrics" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_a100_public_readonly_search_policy_train_split_rerun_evidence_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-normalized-command-policy-train-split-rerun")
    evidence_dir = Path("reports/public-sample/a100-public-readonly-search-policy-train-split-rerun")
    human_brief_path = Path(
        "docs/human-briefs/2026-06-06-run-a100-public-readonly-search-policy-train-split-rerun.html"
    )
    change_dirs = [
        Path("openspec/changes/run-a100-public-readonly-search-policy-train-split-rerun"),
        Path("openspec/changes/archive/2026-06-06-run-a100-public-readonly-search-policy-train-split-rerun"),
    ]
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "public_readonly_search_policy_diagnosis.json",
        "public_readonly_search_policy_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads(
        (evidence_dir / "public_readonly_search_policy_diagnosis.json").read_text(encoding="utf-8")
    )
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    prediction_rows = [json.loads(line) for line in (evidence_dir / "predictions.jsonl").read_text().splitlines()]
    raw_rows = [json.loads(line) for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text().splitlines()]
    generation_trace_rows = [
        json.loads(line) for line in (evidence_dir / "generation_trace.jsonl").read_text().splitlines()
    ]
    train_gold_rows = [json.loads(line) for line in (evidence_dir / "train_split_gold.jsonl").read_text().splitlines()]
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    metrics_markdown = (evidence_dir / "metrics.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "public_readonly_search_policy_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    prior_metrics = json.loads((prior_dir / "metrics.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(metrics, ensure_ascii=False, sort_keys=True),
            json.dumps(schema_guard, ensure_ascii=False, sort_keys=True),
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(prompt_snapshot, ensure_ascii=False, sort_keys=True),
            json.dumps(prediction_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(raw_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(generation_trace_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(train_gold_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            metrics_markdown,
            diagnosis_markdown,
            human_brief,
        ]
    )

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["prompt_constraints"]["public_readonly_search_policy_visible"] is True
    assert metadata["prompt_constraints"]["public_readonly_safety_reason_visible"] is True
    assert metadata["prompt_constraints"]["search_query_slot_guidance_visible"] is True
    assert metadata["prompt_constraints"]["task_type_not_route_enum_visible"] is True
    assert metadata["decoding_policy"]["schema_repair_applied"] is False
    assert metadata["decoding_policy"]["schema_retry_enabled"] is True

    assert manifest["evidence_kind"] == "a100_public_readonly_search_policy_train_split_rerun"
    assert manifest["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["prediction_split"] == "train"
    assert manifest["prediction_count"] == 3
    assert manifest["training_rows_used"] == 3
    assert manifest["training_row_ids"] == expected_row_ids
    assert manifest["prior_context"]["baseline_evidence"] == prior_dir.as_posix()
    assert manifest["prior_context"]["prior_json_valid_rate"] == prior_metrics["metrics"]["json_valid_rate"] == 1 / 3
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_quality_evidence"] is False
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["slot_normalization_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["evaluator_metric_change_performed"] is False
    assert manifest["observed_result"]["json_valid_rate"] == 0.0
    assert manifest["observed_result"]["contract_exact_match"] == 0.0
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 0
    assert manifest["observed_result"]["raw_route_search_web_count"] == 3
    assert manifest["observed_result"]["raw_safety_reason_public_readonly_count"] == 3
    assert manifest["observed_result"]["raw_confirmation_required_false_count"] == 3
    assert manifest["observed_result"]["raw_slots_query_present_count"] == 3
    assert manifest["observed_result"]["raw_task_type_search_exact_count"] == 0
    assert manifest["observed_result"]["raw_task_type_route_alias_count"] == 3
    assert manifest["observed_result"]["train_internal_full_contract_recovery_observed"] is False
    assert manifest["observed_result"]["train_internal_public_readonly_field_emission_observed"] is True
    assert manifest["observed_result"]["train_internal_schema_regression_observed"] is True

    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in generation_trace_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert prompt_snapshot["prompt_constraints"]["public_readonly_search_policy_visible"] is True
    assert prompt_snapshot["claims"]["contains_gold_contract"] is False

    assert metrics["metadata"]["prediction_split"] == "train"
    assert metrics["metadata"]["generalization_claim"] is False
    assert metrics["metadata"]["strict_final_contract_metrics"] is True
    assert metrics["metadata"]["raw_text_field_observation_not_metric_relaxation"] is True
    assert metrics["metrics"]["json_valid_rate"] == 0.0
    assert metrics["metrics"]["contract_exact_match"] == 0.0
    assert metrics["public_readonly_search_policy_counts"]["raw_text_value_counts"]["task_type"] == {
        "search_web": 3
    }
    assert metrics["public_readonly_search_policy_counts"]["raw_text_value_counts"]["route"] == {
        "search_web": 3
    }

    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["raw_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["retry_attempted_count"] == 3
    assert schema_guard["summary"]["retry_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == 0
    assert schema_guard["summary"]["strict_retry_parser_rejected_fragment_count"] == 3
    assert schema_guard["summary"]["task_type_route_alias_count"] == 3
    assert schema_guard["summary"]["public_readonly_raw_field_emission_count"] == 3

    assert diagnosis["diagnostic_kind"] == "public_readonly_search_policy_train_split_diagnosis"
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 0.0
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["field_match_counts_from_raw_text_observation_only"] == {
        "confirmation_required": 3,
        "normalized_command": 2,
        "route": 3,
        "safety.reason": 3,
        "slots": 0,
        "task_type": 0,
    }
    assert diagnosis["summary"]["family_counts"]["schema_invalid_malformed_json_with_task_type_route_alias"] == 3
    assert diagnosis["claims"]["raw_text_field_observation_not_metric_relaxation"] is True
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["slot_normalization_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "strict JSON validity regressed from `1/3` to `0/3`" in report
    assert "Raw field observations below are diagnostic only" in metrics_markdown
    assert "no slot normalization" in diagnosis_markdown
    assert "strict schema 仍然失败" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_public_readonly_output_boundary_retry_policy_pack_is_public_safe_and_bounded() -> None:
    source_dir = Path("reports/public-sample/a100-public-readonly-search-policy-train-split-rerun")
    evidence_dir = Path("reports/public-sample/public-readonly-output-boundary-retry-policy")
    human_brief_path = Path(
        "docs/human-briefs/2026-06-06-repair-public-readonly-output-boundary-retry-policy.html"
    )
    change_dirs = [
        Path("openspec/changes/repair-public-readonly-output-boundary-retry-policy"),
        Path("openspec/changes/archive/2026-06-06-repair-public-readonly-output-boundary-retry-policy"),
    ]
    expected_artifacts = {
        "repair_summary.json",
        "repair_summary.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }

    assert evidence_dir.exists()
    assert expected_artifacts <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    summary = json.loads((evidence_dir / "repair_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "repair_summary.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    source_diagnosis = json.loads(
        (source_dir / "public_readonly_search_policy_diagnosis.json").read_text(encoding="utf-8")
    )
    source_schema_guard = json.loads((source_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(summary, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            human_brief,
        ]
    )

    assert summary["evidence_kind"] == "public_readonly_output_boundary_retry_policy_local"
    assert summary["source_prior_phase"] == source_dir.as_posix()
    assert summary["source_observed_result"]["strict_final_json_valid_rate"] == (
        source_diagnosis["summary"]["strict_final_json_valid_rate"]
    ) == 0.0
    assert summary["source_observed_result"]["strict_final_contract_exact_match"] == 0.0
    assert summary["source_observed_result"]["raw_task_type_route_alias_count"] == 3
    assert summary["source_schema_guard_summary"]["strict_retry_parser_rejected_fragment_count"] == (
        source_schema_guard["summary"]["strict_retry_parser_rejected_fragment_count"]
    ) == 3
    assert summary["source_schema_guard_summary"]["public_readonly_raw_field_emission_count"] == 3
    assert summary["prompt_constraints"]["single_root_json_object_visible"] is True
    assert summary["prompt_constraints"]["no_premature_root_close_visible"] is True
    assert summary["prompt_constraints"]["public_readonly_task_type_search_not_search_web_visible"] is True
    assert summary["prompt_constraints"]["public_readonly_search_policy_visible"] is True
    assert summary["prompt_constraints"]["task_type_not_route_enum_visible"] is True
    assert summary["retry_prompt_constraints"]["minified_json_only_visible"] is True
    assert summary["retry_prompt_constraints"]["single_root_json_object_visible"] is True
    assert summary["retry_prompt_constraints"]["no_premature_root_close_visible"] is True
    assert summary["retry_prompt_constraints"]["task_type_search_not_search_web_visible"] is True
    assert summary["claims"]["local_prompt_retry_policy_hardening_only"] is True
    assert summary["claims"]["a100_execution_performed"] is False
    assert summary["claims"]["training_or_prediction_rerun_performed"] is False
    assert summary["claims"]["evaluator_metric_change_performed"] is False
    assert summary["claims"]["semantic_equivalence_scoring_performed"] is False
    assert summary["claims"]["slot_normalization_performed"] is False
    assert summary["claims"]["prediction_repair_or_rescore_performed"] is False
    assert summary["claims"]["model_recovery_claim"] is False
    assert summary["claims"]["model_quality_improvement_claim"] is False

    assert manifest["evidence_kind"] == "public_readonly_output_boundary_retry_policy_local"
    assert manifest["source_artifacts"]["public_readonly_search_policy_diagnosis"].endswith(
        "public_readonly_search_policy_diagnosis.json"
    )
    assert manifest["source_artifacts"]["schema_guard_summary"].endswith("schema_guard_summary.json")
    assert manifest["diagnostic_artifacts"]["repair_summary"].endswith("repair_summary.json")
    assert manifest["diagnostic_artifacts"]["repair_report"].endswith("repair_summary.md")
    assert manifest["diagnostic_artifacts"]["phase_validation_leak_scan"].endswith(
        "phase_validation_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["post_archive_leak_scan"].endswith(
        "post_archive_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["final_leak_scan"].endswith("final_leak_scan_result.json")
    assert manifest["claims"]["local_prompt_retry_policy_hardening_only"] is True
    assert manifest["claims"]["a100_execution_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "local prompt/retry hardening only" in report
    assert "No A100 execution was performed" in report
    assert "not model recovery evidence" in report
    assert "本地 prompt/retry hardening" in human_brief
    assert "不使用 A100" in human_brief
    assert "不改 evaluator metrics" in human_brief
    assert "不证明模型恢复" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_a100_output_boundary_retry_policy_train_split_rerun_evidence_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-public-readonly-search-policy-train-split-rerun")
    local_repair_dir = Path("reports/public-sample/public-readonly-output-boundary-retry-policy")
    evidence_dir = Path("reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun")
    human_brief_path = Path(
        "docs/human-briefs/2026-06-06-run-a100-output-boundary-retry-policy-train-split-rerun.html"
    )
    change_dirs = [
        Path("openspec/changes/run-a100-output-boundary-retry-policy-train-split-rerun"),
        Path("openspec/changes/archive/2026-06-06-run-a100-output-boundary-retry-policy-train-split-rerun"),
    ]
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "output_boundary_retry_policy_diagnosis.json",
        "output_boundary_retry_policy_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads(
        (evidence_dir / "output_boundary_retry_policy_diagnosis.json").read_text(encoding="utf-8")
    )
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    prediction_rows = [json.loads(line) for line in (evidence_dir / "predictions.jsonl").read_text().splitlines()]
    raw_rows = [json.loads(line) for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text().splitlines()]
    generation_trace_rows = [
        json.loads(line) for line in (evidence_dir / "generation_trace.jsonl").read_text().splitlines()
    ]
    train_gold_rows = [json.loads(line) for line in (evidence_dir / "train_split_gold.jsonl").read_text().splitlines()]
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    metrics_markdown = (evidence_dir / "metrics.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "output_boundary_retry_policy_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    prior_metrics = json.loads((prior_dir / "metrics.json").read_text(encoding="utf-8"))
    local_repair_manifest = json.loads((local_repair_dir / "manifest.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(metrics, ensure_ascii=False, sort_keys=True),
            json.dumps(schema_guard, ensure_ascii=False, sort_keys=True),
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            metrics_markdown,
            diagnosis_markdown,
            human_brief,
        ]
    )

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["command_summary"]["config"] == "<private_prediction_config>"
    assert metadata["decoding_policy"]["schema_retry_enabled"] is True
    assert metadata["decoding_policy"]["schema_repair_applied"] is False
    assert metadata["prompt_constraints"]["single_root_json_object_visible"] is True
    assert metadata["prompt_constraints"]["no_premature_root_close_visible"] is True
    assert metadata["prompt_constraints"]["whole_object_boundary_visible"] is True
    assert metadata["prompt_constraints"]["public_readonly_task_type_search_not_search_web_visible"] is True

    assert manifest["evidence_kind"] == "a100_output_boundary_retry_policy_train_split_rerun"
    assert manifest["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["prediction_split"] == "train"
    assert manifest["prediction_count"] == 3
    assert manifest["training_rows_used"] == 3
    assert manifest["training_row_ids"] == expected_row_ids
    assert manifest["prior_context"]["baseline_evidence"] == prior_dir.as_posix()
    assert manifest["prior_context"]["local_prompt_retry_policy_evidence"] == local_repair_dir.as_posix()
    assert manifest["prior_context"]["prior_json_valid_rate"] == prior_metrics["metrics"]["json_valid_rate"] == 0.0
    assert local_repair_manifest["claims"]["a100_execution_performed"] is False
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["artifact_policy"]["remote_paths_copied_to_git"] is False
    assert manifest["artifact_policy"]["host_details_copied_to_git"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["slot_normalization_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["evaluator_metric_change_performed"] is False
    assert manifest["observed_result"]["json_valid_rate"] == 0.0
    assert manifest["observed_result"]["contract_exact_match"] == 0.0
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 0
    assert manifest["observed_result"]["raw_json_object_count"] == 3
    assert manifest["observed_result"]["raw_missing_task_type_count"] == 3
    assert manifest["observed_result"]["retry_prose_markdown_wrapper_count"] == 3
    assert manifest["observed_result"]["retry_task_type_search_visible_count"] == 3
    assert manifest["observed_result"]["train_internal_shape_improvement_observed"] is True
    assert manifest["observed_result"]["train_internal_full_contract_recovery_observed"] is False

    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in generation_trace_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert prompt_snapshot["prompt_constraints"]["single_root_json_object_visible"] is True
    assert prompt_snapshot["prompt_constraints"]["no_premature_root_close_visible"] is True
    assert prompt_snapshot["prompt_constraints"]["public_readonly_task_type_search_not_search_web_visible"] is True
    assert prompt_snapshot["claims"]["contains_gold_contract"] is False

    assert metrics["metrics"]["json_valid_rate"] == 0.0
    assert metrics["metrics"]["contract_exact_match"] == 0.0
    assert metrics["metrics"]["task_type_accuracy"] == 0.0
    assert metrics["metrics"]["route_accuracy"] == 0.0
    assert metrics["failure_slices"]["schema"]["count"] == 3

    assert schema_guard["evidence_kind"] == "a100_output_boundary_retry_policy_schema_guard_summary"
    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["raw_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["retry_attempted_count"] == 3
    assert schema_guard["summary"]["retry_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == 0
    assert schema_guard["summary"]["strict_retry_parser_rejected_fragment_count"] == 3
    assert schema_guard["summary"]["raw_json_object_count"] == 3
    assert schema_guard["summary"]["raw_missing_task_type_count"] == 3
    assert schema_guard["summary"]["raw_task_type_search_exact_count"] == 0
    assert schema_guard["summary"]["raw_task_type_route_alias_count"] == 0
    assert schema_guard["summary"]["retry_prose_markdown_wrapper_count"] == 3
    assert schema_guard["summary"]["retry_task_type_search_visible_count"] == 3
    assert schema_guard["summary"]["public_readonly_raw_field_emission_count"] == 3
    assert schema_guard["parse_status_counts"]["raw_attempt"] == {"json_object": 3}
    assert schema_guard["parse_status_counts"]["retry_attempt"] == {"json_fragment_object": 3}

    assert diagnosis["diagnostic_kind"] == "output_boundary_retry_policy_train_split_diagnosis"
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 0.0
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["validated_output_schema_valid_count"] == 0
    assert diagnosis["summary"]["shape_improvements"]["prior_raw_non_json_count"] == 3
    assert diagnosis["summary"]["shape_improvements"]["current_raw_json_object_count"] == 3
    assert diagnosis["summary"]["shape_improvements"]["current_raw_missing_task_type_count"] == 3
    assert diagnosis["summary"]["shape_improvements"]["current_raw_task_type_search_exact_count"] == 0
    assert diagnosis["summary"]["shape_improvements"]["current_raw_task_type_route_alias_count"] == 0
    assert diagnosis["summary"]["shape_improvements"]["current_retry_json_fragment_wrapper_count"] == 3
    assert diagnosis["summary"]["shape_improvements"]["current_retry_task_type_search_visible_count"] == 3
    assert diagnosis["summary"]["family_counts"]["missing_task_type"] == 3
    assert diagnosis["summary"]["family_counts"]["retry_prose_markdown_wrapper"] == 3
    assert diagnosis["summary"]["field_match_counts_from_raw_json_observation_only"] == {
        "confirmation_required": 3,
        "normalized_command": 3,
        "route": 3,
        "safety.reason": 3,
    }
    assert diagnosis["summary"]["raw_slots_query_present_count"] == 1
    assert diagnosis["summary"]["raw_slots_city_date_present_count"] == 2
    assert diagnosis["claims"]["raw_json_field_observation_not_metric_relaxation"] is True
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["slot_normalization_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "raw outputs are now whole JSON objects for `3/3` rows" in report
    assert "Raw JSON field observations below are diagnostic only" in metrics_markdown
    assert "No semantic-equivalence scoring" in diagnosis_markdown
    assert "raw output 已变成完整 JSON object" in human_brief
    assert "retry 又被说明文字/Markdown 包住" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_schema_retry_wrapper_boundary_policy_pack_is_public_safe_and_bounded() -> None:
    source_dir = Path("reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun")
    evidence_dir = Path("reports/public-sample/schema-retry-wrapper-boundary-policy")
    human_brief_path = Path("docs/human-briefs/2026-06-06-repair-schema-retry-wrapper-boundary.html")
    change_dirs = [
        Path("openspec/changes/repair-schema-retry-wrapper-boundary"),
        Path("openspec/changes/archive/2026-06-06-repair-schema-retry-wrapper-boundary"),
    ]
    required_files = {
        "repair_summary.json",
        "repair_summary.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    summary = json.loads((evidence_dir / "repair_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "repair_summary.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    source_diagnosis = json.loads(
        (source_dir / "output_boundary_retry_policy_diagnosis.json").read_text(encoding="utf-8")
    )
    serialized = "\n".join(
        [
            json.dumps(summary, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            human_brief,
        ]
    )

    assert summary["evidence_kind"] == "schema_retry_wrapper_boundary_policy_local"
    assert summary["source_prior_phase"] == source_dir.as_posix()
    assert summary["source_observed_result"]["strict_final_json_valid_rate"] == (
        source_diagnosis["summary"]["strict_final_json_valid_rate"]
    ) == 0.0
    assert summary["source_observed_result"]["strict_final_contract_exact_match"] == 0.0
    assert summary["source_observed_result"]["raw_json_object_count"] == 3
    assert summary["source_observed_result"]["raw_missing_task_type_count"] == 3
    assert summary["source_observed_result"]["retry_json_fragment_wrapper_count"] == 3
    assert summary["source_observed_result"]["retry_task_type_search_visible_count"] == 3
    assert summary["source_observed_result"]["validated_output_schema_valid_count"] == 0
    assert summary["source_schema_guard_summary"]["retry_attempted_count"] == 3
    assert summary["source_schema_guard_summary"]["retry_attempt_schema_valid_count"] == 0
    assert summary["source_schema_guard_summary"]["strict_retry_parser_rejected_fragment_count"] == 3
    assert summary["source_schema_guard_summary"]["retry_prose_markdown_wrapper_count"] == 3

    constraints = summary["retry_prompt_constraints"]
    assert constraints["minified_json_only_visible"] is True
    assert constraints["single_root_json_object_visible"] is True
    assert constraints["first_last_brace_visible"] is True
    assert constraints["no_markdown_prose_visible"] is True
    assert constraints["no_prefix_suffix_text_visible"] is True
    assert constraints["no_zh_this_following_prefix_visible"] is True
    assert constraints["no_here_is_visible"] is True
    assert constraints["no_trailing_analysis_visible"] is True
    assert constraints["no_second_json_object_visible"] is True
    assert constraints["strict_parser_rejection_warning_visible"] is True
    assert constraints["task_type_search_not_search_web_visible"] is True
    assert manifest["retry_prompt_constraints"] == constraints
    assert manifest["diagnostic_artifacts"]["repair_summary"].endswith("repair_summary.json")
    assert manifest["diagnostic_artifacts"]["repair_report"].endswith("repair_summary.md")
    assert manifest["diagnostic_artifacts"]["human_brief"] == human_brief_path.as_posix()
    assert manifest["source_artifacts"]["a100_output_boundary_retry_diagnosis"].endswith(
        "output_boundary_retry_policy_diagnosis.json"
    )

    assert summary["claims"]["local_retry_prompt_boundary_hardening_only"] is True
    assert summary["claims"]["a100_execution_performed"] is False
    assert summary["claims"]["training_or_prediction_rerun_performed"] is False
    assert summary["claims"]["private_prediction_rerun_performed"] is False
    assert summary["claims"]["parser_semantics_changed"] is False
    assert summary["claims"]["evaluator_metric_change_performed"] is False
    assert summary["claims"]["schema_repair_or_coercion_applied"] is False
    assert summary["claims"]["prediction_repair_or_rescore_performed"] is False
    assert summary["claims"]["semantic_equivalence_scoring_performed"] is False
    assert summary["claims"]["slot_normalization_performed"] is False
    assert summary["claims"]["model_recovery_claim"] is False
    assert summary["claims"]["model_quality_improvement_claim"] is False
    assert manifest["claims"] == summary["claims"]

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "local retry prompt boundary hardening only" in report
    assert "strict parser will reject the retry attempt" in report
    assert "本地 retry prompt 已补强 wrapper boundary" in human_brief
    assert "这不证明模型恢复" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_tighten_retry_json_only_output_boundary_pack_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-generation-stop-reason-boundary-rerun")
    evidence_dir = Path("reports/public-sample/tighten-retry-json-only-output-boundary")
    human_brief_path = Path("docs/human-briefs/2026-06-06-tighten-retry-json-only-output-boundary.html")
    archive_dir = Path("openspec/changes/archive/2026-06-06-tighten-retry-json-only-output-boundary")
    change_dirs = [
        Path("openspec/changes/tighten-retry-json-only-output-boundary"),
        archive_dir,
    ]
    required_files = {
        "manifest.json",
        "retry_json_only_boundary_summary.json",
        "retry_json_only_boundary_summary.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    summary = json.loads((evidence_dir / "retry_json_only_boundary_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "retry_json_only_boundary_summary.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = None
    final_leak_scan = None
    if archive_dir.exists():
        post_archive_leak_scan = json.loads(
            (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
        )
        final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    prior_manifest = json.loads((prior_dir / "manifest.json").read_text(encoding="utf-8"))
    prior_metrics = json.loads((prior_dir / "metrics.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(summary, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            human_brief,
        ]
    )

    assert summary["evidence_kind"] == "tighten_retry_json_only_output_boundary_local"
    assert manifest["evidence_kind"] == summary["evidence_kind"]
    assert summary["source_prior_phase"] == prior_dir.as_posix()
    assert manifest["prior_a100_stop_boundary_rerun"]["evidence_dir"] == prior_dir.as_posix()
    assert manifest["prior_a100_stop_boundary_rerun"]["manifest"] == (prior_dir / "manifest.json").as_posix()
    assert manifest["prior_a100_stop_boundary_rerun"]["metrics"] == (prior_dir / "metrics.json").as_posix()
    assert summary["prior_a100_context"]["evidence_kind"] == prior_manifest["evidence_kind"]
    assert summary["prior_a100_context"]["strict_final_json_valid_rate"] == (
        prior_metrics["metrics"]["json_valid_rate"]
    ) == 0.0
    assert summary["prior_a100_context"]["strict_final_contract_exact_match"] == (
        prior_metrics["metrics"]["contract_exact_match"]
    ) == 0.0
    assert summary["prior_a100_context"]["row_count"] == 3

    constraints = summary["retry_prompt_constraints"]
    assert constraints["exact_json_only_output_visible"] is True
    assert constraints["no_text_outside_root_json_object_visible"] is True
    assert constraints["no_natural_language_wrapper_or_preamble_visible"] is True
    assert constraints["machine_readable_only_retry_response_visible"] is True
    assert constraints["no_markdown_prose_visible"] is True
    assert constraints["no_prefix_suffix_text_visible"] is True
    assert constraints["no_second_json_object_visible"] is True
    assert constraints["strict_parser_rejection_warning_visible"] is True
    assert manifest["retry_prompt_constraints"] == constraints

    assert summary["claims"]["local_retry_prompt_boundary_hardening_only"] is True
    assert summary["claims"]["a100_execution_performed"] is False
    assert summary["claims"]["training_performed"] is False
    assert summary["claims"]["parser_relaxation_performed"] is False
    assert summary["claims"]["evaluator_metric_change_performed"] is False
    assert summary["claims"]["prediction_repair_performed"] is False
    assert summary["claims"]["prediction_rescore_performed"] is False
    assert summary["claims"]["model_recovery_claim"] is False
    assert summary["claims"]["model_quality_claim"] is False
    assert summary["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"] == summary["claims"]
    assert manifest["diagnostic_artifacts"]["summary_json"].endswith("retry_json_only_boundary_summary.json")
    assert manifest["diagnostic_artifacts"]["summary_markdown"].endswith("retry_json_only_boundary_summary.md")
    assert manifest["diagnostic_artifacts"]["human_brief"] == human_brief_path.as_posix()

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "no A100 execution" in report
    assert "no parser relaxation" in report
    assert "no model recovery or quality claim" in report
    assert "A100 执行：没有" in human_brief
    assert "不证明模型恢复" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_retry_template_decoding_boundary_pack_is_public_safe_and_bounded() -> None:
    local_hardening_dir = Path("reports/public-sample/tighten-retry-json-only-output-boundary")
    prior_a100_dir = Path("reports/public-sample/a100-retry-json-only-boundary-rerun")
    evidence_dir = Path("reports/public-sample/retry-template-decoding-boundary")
    human_brief_path = Path("docs/human-briefs/2026-06-06-retry-template-decoding-boundary.html")
    archive_dir = Path("openspec/changes/archive/2026-06-06-retry-template-decoding-boundary")
    change_dirs = [
        Path("openspec/changes/retry-template-decoding-boundary"),
        archive_dir,
    ]
    required_files = {
        "manifest.json",
        "retry_template_boundary_summary.json",
        "retry_template_boundary_summary.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    summary = json.loads((evidence_dir / "retry_template_boundary_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "retry_template_boundary_summary.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = None
    final_leak_scan = None
    if archive_dir.exists():
        post_archive_leak_scan = json.loads(
            (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
        )
        final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    local_summary = json.loads(
        (local_hardening_dir / "retry_json_only_boundary_summary.json").read_text(encoding="utf-8")
    )
    prior_manifest = json.loads((prior_a100_dir / "manifest.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(summary, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True)
            if post_archive_leak_scan is not None
            else "",
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True) if final_leak_scan is not None else "",
            report,
            human_brief,
        ]
    )

    assert summary["evidence_kind"] == "retry_template_decoding_boundary_local"
    assert manifest["evidence_kind"] == summary["evidence_kind"]
    assert summary["source_artifacts"]["local_retry_json_only_hardening"] == local_hardening_dir.as_posix()
    assert summary["source_artifacts"]["a100_retry_json_only_rerun"] == prior_a100_dir.as_posix()
    assert local_summary["claims"]["local_retry_prompt_boundary_hardening_only"] is True
    assert prior_manifest["observed_result"]["retry_prose_markdown_wrapper_count"] == 3
    assert prior_manifest["observed_result"]["strict_final_json_valid_rate"] == 0.0

    boundary = summary["retry_template_boundary"]
    assert boundary["retry_prompt_uses_chat_template_boundary"] is True
    assert boundary["retry_template_mode_visible"] is True
    assert boundary["machine_only_contract_regeneration_visible"] is True
    assert boundary["no_conversational_answer_mode_visible"] is True
    assert boundary["assistant_json_payload_only_visible"] is True
    assert boundary["strict_whole_object_parser_boundary_visible"] is True
    assert manifest["retry_template_boundary"] == boundary
    assert summary["retry_prompt_constraints"]["strict_parser_rejection_warning_visible"] is True
    assert summary["tdd_evidence"]["red_test_observed"] is True
    assert summary["tdd_evidence"]["green_test_observed"] is True

    assert summary["claims"]["local_retry_template_boundary_hardening_only"] is True
    assert summary["claims"]["a100_execution_performed"] is False
    assert summary["claims"]["training_performed"] is False
    assert summary["claims"]["private_prediction_rerun_performed"] is False
    assert summary["claims"]["parser_relaxation_performed"] is False
    assert summary["claims"]["evaluator_metric_change_performed"] is False
    assert summary["claims"]["schema_repair_or_coercion_applied"] is False
    assert summary["claims"]["prediction_repair_or_rescore_performed"] is False
    assert summary["claims"]["semantic_equivalence_scoring_performed"] is False
    assert summary["claims"]["slot_normalization_performed"] is False
    assert summary["claims"]["model_recovery_claim"] is False
    assert summary["claims"]["model_quality_improvement_claim"] is False
    assert manifest["claims"] == summary["claims"]

    for artifact_path in manifest["diagnostic_artifacts"].values():
        assert Path(artifact_path).exists()
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    if archive_dir.exists():
        assert post_archive_leak_scan is not None
        assert post_archive_leak_scan["ok"] is True
        assert post_archive_leak_scan["findings"] == []
        assert final_leak_scan is not None
        assert final_leak_scan["ok"] is True
        assert final_leak_scan["findings"] == []
    assert "local retry template/decoding-boundary hardening only" in report
    assert "does not prove trained-adapter output behavior changed" in report
    assert "本地 retry template boundary 已接入" in human_brief
    assert "不证明 A100 行为改变" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_a100_schema_retry_wrapper_boundary_rerun_evidence_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun")
    local_repair_dir = Path("reports/public-sample/schema-retry-wrapper-boundary-policy")
    evidence_dir = Path("reports/public-sample/a100-schema-retry-wrapper-boundary-rerun")
    human_brief_path = Path("docs/human-briefs/2026-06-06-run-a100-schema-retry-wrapper-boundary-rerun.html")
    change_dirs = [
        Path("openspec/changes/run-a100-schema-retry-wrapper-boundary-rerun"),
        Path("openspec/changes/archive/2026-06-06-run-a100-schema-retry-wrapper-boundary-rerun"),
    ]
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "schema_retry_wrapper_boundary_diagnosis.json",
        "schema_retry_wrapper_boundary_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "schema_retry_wrapper_boundary_diagnosis.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    prediction_rows = [json.loads(line) for line in (evidence_dir / "predictions.jsonl").read_text().splitlines()]
    raw_rows = [json.loads(line) for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text().splitlines()]
    generation_trace_rows = [
        json.loads(line) for line in (evidence_dir / "generation_trace.jsonl").read_text().splitlines()
    ]
    train_gold_rows = [json.loads(line) for line in (evidence_dir / "train_split_gold.jsonl").read_text().splitlines()]
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    metrics_markdown = (evidence_dir / "metrics.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "schema_retry_wrapper_boundary_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    serialized = "\n".join(
        [
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(metrics, ensure_ascii=False, sort_keys=True),
            json.dumps(schema_guard, ensure_ascii=False, sort_keys=True),
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            metrics_markdown,
            diagnosis_markdown,
            human_brief,
        ]
    )

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["command_summary"]["config"] == "<private_prediction_config>"
    assert metadata["command_summary"]["output"] == "<a100_prediction_output>"
    assert metadata["retry_prompt_constraints"]["no_prefix_suffix_text_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_here_is_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_trailing_analysis_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_second_json_object_visible"] is True
    assert metadata["retry_prompt_constraints"]["strict_parser_rejection_warning_visible"] is True
    assert prompt_snapshot["retry_prompt_constraints"] == metadata["retry_prompt_constraints"]

    assert manifest["evidence_kind"] == "a100_schema_retry_wrapper_boundary_train_split_rerun"
    assert manifest["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["prediction_split"] == "train"
    assert manifest["prediction_count"] == 3
    assert manifest["training_rows_used"] == 3
    assert manifest["training_row_ids"] == expected_row_ids
    assert manifest["prior_context"]["baseline_evidence"] == prior_dir.as_posix()
    assert manifest["prior_context"]["local_retry_wrapper_boundary_evidence"] == local_repair_dir.as_posix()
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["parser_relaxation_performed"] is False
    assert manifest["claims"]["evaluator_metric_change_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["slot_normalization_performed"] is False
    assert manifest["observed_result"]["strict_final_json_valid_rate"] == 0.0
    assert manifest["observed_result"]["strict_final_contract_exact_match"] == 0.0
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 0
    assert manifest["observed_result"]["raw_json_object_count"] == 3
    assert manifest["observed_result"]["raw_missing_task_type_count"] == 3
    assert manifest["observed_result"]["retry_prose_markdown_wrapper_count"] == 3
    assert manifest["observed_result"]["retry_wrapper_reduction_observed"] is False
    assert manifest["observed_result"]["schema_recovery_observed"] is False

    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in generation_trace_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert metrics["metrics"]["json_valid_rate"] == 0.0
    assert metrics["metrics"]["contract_exact_match"] == 0.0
    assert metrics["failure_slices"]["schema"]["count"] == 3

    assert schema_guard["evidence_kind"] == "a100_schema_retry_wrapper_boundary_schema_guard_summary"
    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["raw_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["retry_attempted_count"] == 3
    assert schema_guard["summary"]["retry_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == 0
    assert schema_guard["summary"]["raw_json_object_count"] == 3
    assert schema_guard["summary"]["raw_missing_task_type_count"] == 3
    assert schema_guard["summary"]["retry_prose_markdown_wrapper_count"] == 3
    assert schema_guard["summary"]["retry_forbidden_preface_visible_count"] == 2
    assert schema_guard["summary"]["retry_trailing_analysis_visible_count"] == 3
    assert schema_guard["summary"]["retry_task_type_search_visible_count"] == 3
    assert schema_guard["parse_status_counts"]["raw_attempt"] == {"json_object": 3}
    assert schema_guard["parse_status_counts"]["retry_attempt"] == {"json_fragment_object": 3}

    assert diagnosis["diagnostic_kind"] == "schema_retry_wrapper_boundary_train_split_diagnosis"
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 0.0
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["retry_wrapper_reduction_observed"] is False
    assert diagnosis["summary"]["schema_recovery_observed"] is False
    assert diagnosis["summary"]["family_counts"]["retry_prose_markdown_wrapper_after_boundary_repair"] == 3
    assert diagnosis["claims"]["parser_relaxation_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "retry wrapper-boundary prompt constraints reached the A100 prediction metadata" in diagnosis_markdown
    assert "Raw and retry observations are diagnostic only" in metrics_markdown
    assert "Retry attempts still visibly include `task_type=search`" in report
    assert "strict schema 仍未恢复" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_a100_retry_generation_trace_rerun_evidence_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-schema-retry-wrapper-boundary-rerun")
    local_instrumentation_dir = Path("reports/public-sample/retry-generation-trace-instrumentation")
    evidence_dir = Path("reports/public-sample/a100-retry-generation-trace-rerun")
    human_brief_path = Path("docs/human-briefs/2026-06-06-run-a100-retry-generation-trace-rerun.html")
    archive_dir = Path("openspec/changes/archive/2026-06-06-run-a100-retry-generation-trace-rerun")
    change_dirs = [
        Path("openspec/changes/run-a100-retry-generation-trace-rerun"),
        archive_dir,
    ]
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "retry_trace_diagnosis.json",
        "retry_trace_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "retry_trace_diagnosis.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    prediction_rows = [json.loads(line) for line in (evidence_dir / "predictions.jsonl").read_text().splitlines()]
    raw_rows = [json.loads(line) for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text().splitlines()]
    generation_trace_rows = [
        json.loads(line) for line in (evidence_dir / "generation_trace.jsonl").read_text().splitlines()
    ]
    train_gold_rows = [json.loads(line) for line in (evidence_dir / "train_split_gold.jsonl").read_text().splitlines()]
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = (
        json.loads((evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "post_archive_leak_scan_result.json").exists()
        else {"ok": True, "findings": []}
    )
    final_leak_scan = (
        json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "final_leak_scan_result.json").exists()
        else {"ok": True, "findings": []}
    )
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    metrics_markdown = (evidence_dir / "metrics.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "retry_trace_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    prior_manifest = json.loads((prior_dir / "manifest.json").read_text(encoding="utf-8"))
    local_instrumentation_manifest = json.loads(
        (local_instrumentation_dir / "manifest.json").read_text(encoding="utf-8")
    )
    serialized = "\n".join(
        [
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(metrics, ensure_ascii=False, sort_keys=True),
            json.dumps(schema_guard, ensure_ascii=False, sort_keys=True),
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            metrics_markdown,
            diagnosis_markdown,
            human_brief,
        ]
    )

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["decoding_policy"]["schema_retry_enabled"] is True
    assert metadata["decoding_policy"]["schema_repair_applied"] is False
    assert metadata["decoding_policy"]["generation_trace_sidecar_written"] is True
    assert metadata["command_summary"]["config"] == "<private_prediction_config>"
    assert metadata["command_summary"]["output"] == "<a100_prediction_output>"
    assert prompt_snapshot["claims"]["contains_gold_contract"] is False

    assert manifest["evidence_kind"] == "a100_retry_generation_trace_train_split_rerun"
    assert manifest["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["prediction_split"] == "train"
    assert manifest["prediction_count"] == 3
    assert manifest["training_rows_used"] == 3
    assert manifest["training_row_ids"] == expected_row_ids
    assert manifest["prior_context"]["baseline_evidence"] == prior_dir.as_posix()
    assert manifest["prior_context"]["local_retry_generation_trace_instrumentation"] == (
        local_instrumentation_dir.as_posix()
    )
    assert manifest["prior_context"]["prior_generation_trace_rows"] == 3
    assert manifest["prior_context"]["prior_retry_attempt_trace_rows"] == 0
    assert prior_manifest["observed_result"]["strict_final_json_valid_rate"] == 0.0
    assert local_instrumentation_manifest["claims"]["a100_execution_performed"] is False
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["artifact_policy"]["remote_paths_copied_to_git"] is False
    assert manifest["artifact_policy"]["host_details_copied_to_git"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False
    assert manifest["claims"]["parser_relaxation_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["slot_normalization_performed"] is False
    assert manifest["claims"]["evaluator_metric_change_performed"] is False

    assert manifest["observed_result"]["strict_final_json_valid_rate"] == 0.0
    assert manifest["observed_result"]["strict_final_contract_exact_match"] == 0.0
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 0
    assert manifest["observed_result"]["raw_json_object_count"] == 3
    assert manifest["observed_result"]["raw_missing_task_type_count"] == 3
    assert manifest["observed_result"]["retry_json_fragment_object_count"] == 3
    assert manifest["observed_result"]["retry_prose_markdown_wrapper_count"] == 3
    assert manifest["observed_result"]["retry_trace_instrumentation_observed"] is True
    assert manifest["observed_result"]["schema_recovery_observed"] is False
    assert manifest["observed_result"]["model_recovery_observed"] is False
    assert manifest["observed_result"]["retry_stop_boundary_claim_proven"] is False

    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert [row["id"] for row in generation_trace_rows] == [
        "seed-search-weather",
        "seed-search-weather",
        "seed-search-weather-aug-1",
        "seed-search-weather-aug-1",
        "seed-search-weather-aug-2",
        "seed-search-weather-aug-2",
    ]
    assert [row["attempt"] for row in generation_trace_rows] == [
        "raw_attempt",
        "retry_attempt",
        "raw_attempt",
        "retry_attempt",
        "raw_attempt",
        "retry_attempt",
    ]
    assert all(row["prediction_source_kind"] == "private_a100_adapter" for row in generation_trace_rows)

    raw_trace_rows = [row for row in generation_trace_rows if row["attempt"] == "raw_attempt"]
    retry_trace_rows = [row for row in generation_trace_rows if row["attempt"] == "retry_attempt"]
    assert len(raw_trace_rows) == 3
    assert len(retry_trace_rows) == 3
    assert all(row["finish_state"] == "eos_observed" for row in raw_trace_rows)
    assert all(row["eos_token_seen"] is True for row in raw_trace_rows)
    assert all(row["finish_state"] == "no_eos_observed" for row in retry_trace_rows)
    assert all(row["eos_token_seen"] is False for row in retry_trace_rows)
    assert all(row["generated_token_count"] < row["max_new_tokens"] for row in generation_trace_rows)

    assert metrics["metrics"]["json_valid_rate"] == 0.0
    assert metrics["metrics"]["contract_exact_match"] == 0.0
    assert metrics["failure_slices"]["schema"]["count"] == 3

    assert schema_guard["evidence_kind"] == "a100_retry_generation_trace_schema_guard_summary"
    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["raw_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["retry_attempted_count"] == 3
    assert schema_guard["summary"]["retry_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == 0
    assert schema_guard["summary"]["raw_json_object_count"] == 3
    assert schema_guard["summary"]["raw_missing_task_type_count"] == 3
    assert schema_guard["summary"]["retry_attempt_trace_row_count"] == 3
    assert schema_guard["parse_status_counts"]["raw_attempt"] == {"json_object": 3}
    assert schema_guard["parse_status_counts"]["retry_attempt"] == {"json_fragment_object": 3}
    assert schema_guard["trace_summary"]["trace_row_count"] == 6
    assert schema_guard["trace_summary"]["prior_trace_row_count"] == 3
    assert schema_guard["trace_summary"]["attempt_counts"] == {"raw_attempt": 3, "retry_attempt": 3}
    assert schema_guard["trace_summary"]["finish_state_counts"]["raw_attempt"] == {"eos_observed": 3}
    assert schema_guard["trace_summary"]["finish_state_counts"]["retry_attempt"] == {"no_eos_observed": 3}
    assert schema_guard["trace_summary"]["retry_trace_instrumentation_observed"] is True

    assert diagnosis["diagnostic_kind"] == "retry_generation_trace_train_split_diagnosis"
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 0.0
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["retry_trace_instrumentation_observed"] is True
    assert diagnosis["summary"]["trace_summary"]["retry_attempt_no_eos_observed_count"] == 3
    assert diagnosis["summary"]["trace_summary"]["raw_attempt_eos_observed_count"] == 3
    assert diagnosis["summary"]["schema_recovery_observed"] is False
    assert diagnosis["summary"]["model_recovery_observed"] is False
    assert diagnosis["summary"]["retry_stop_boundary_claim_proven"] is False
    assert diagnosis["summary"]["family_counts"]["schema_invalid_retry_wrapper_persisted_with_retry_trace"] == 3
    assert diagnosis["evidence_gaps"]["retry_stop_boundary_claim_unproven"] is True
    assert all(row["trace"]["raw_attempt_max_new_tokens"] == 256 for row in diagnosis["rows"])
    assert all(row["trace"]["retry_attempt_max_new_tokens"] == 256 for row in diagnosis["rows"])
    assert all(row["trace"]["shared_max_new_tokens"] == 256 for row in diagnosis["rows"])
    assert all(row["trace"]["retry_stop_boundary_claim_proven"] is False for row in diagnosis["rows"])
    assert diagnosis["claims"]["generation_trace_sidecar_written"] is True
    assert diagnosis["claims"]["schema_trace_instrumentation_observed"] is True
    assert diagnosis["claims"]["model_recovery_claim"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "retry-attempt rows" in report
    assert "not model recovery" in report
    assert "decoding behavior change" in report
    assert "retry prompt change" in report
    assert "public full-corpus release" in report
    assert "Retry Trace Boundary" in metrics_markdown
    assert "retry attempts now have trace rows" in diagnosis_markdown
    assert "retry stop-boundary claim remains unproven" in diagnosis_markdown
    assert "retry attempt trace 已补齐" in human_brief
    assert "不是模型恢复" in human_brief
    assert "decoding behavior change" in human_brief
    assert "retry prompt change" in human_brief
    assert "public full-corpus release" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_retry_trace_finish_state_boundary_diagnosis_pack_is_public_safe_and_bounded() -> None:
    source_dir = Path("reports/public-sample/a100-retry-generation-trace-rerun")
    evidence_dir = Path("reports/public-sample/retry-trace-finish-state-boundary-diagnosis")
    human_brief_path = Path(
        "docs/human-briefs/2026-06-06-diagnose-retry-trace-finish-state-boundary.html"
    )
    archive_dir = Path("openspec/changes/archive/2026-06-06-diagnose-retry-trace-finish-state-boundary")
    change_dirs = [
        Path("openspec/changes/diagnose-retry-trace-finish-state-boundary"),
        archive_dir,
    ]
    required_files = {
        "finish_state_boundary_diagnosis.json",
        "finish_state_boundary_diagnosis.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    diagnosis = json.loads((evidence_dir / "finish_state_boundary_diagnosis.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "finish_state_boundary_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = (
        json.loads((evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "post_archive_leak_scan_result.json").exists()
        else {"ok": True, "findings": []}
    )
    final_leak_scan = (
        json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "final_leak_scan_result.json").exists()
        else {"ok": True, "findings": []}
    )
    source_diagnosis = json.loads((source_dir / "retry_trace_diagnosis.json").read_text(encoding="utf-8"))
    source_trace_rows = [
        json.loads(line) for line in (source_dir / "generation_trace.jsonl").read_text().splitlines()
    ]
    source_retry_trace_rows = [row for row in source_trace_rows if row["attempt"] == "retry_attempt"]
    serialized = "\n".join(
        [
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            human_brief,
        ]
    )

    assert diagnosis["evidence_kind"] == "retry_trace_finish_state_boundary_diagnosis_local"
    assert diagnosis["diagnostic_kind"] == "retry_trace_finish_state_boundary_diagnosis"
    assert diagnosis["source_artifacts"]["a100_generation_trace"].endswith("generation_trace.jsonl")
    assert diagnosis["source_artifacts"]["trace_writer_source"] == "src/voice2task/training.py"
    assert diagnosis["source_artifact_policy"]["uses_prior_public_sample_artifacts_only"] is True
    assert diagnosis["source_artifact_policy"]["a100_execution_performed"] is False
    assert diagnosis["source_artifact_policy"]["prediction_rerun_performed"] is False
    assert diagnosis["source_artifact_policy"]["private_raw_logs_or_adapters_read"] is False

    summary = diagnosis["summary"]
    assert summary["source_prior_phase"] == source_dir.as_posix()
    assert summary["prediction_count"] == 3
    assert summary["retry_trace_row_count"] == 3
    assert summary["raw_trace_row_count"] == 3
    assert summary["retry_finish_state_counts"] == {"no_eos_observed": 3}
    assert summary["retry_eos_seen_counts"] == {"False": 3}
    assert summary["retry_generated_token_count_min"] == 146
    assert summary["retry_generated_token_count_max"] == 165
    assert summary["retry_max_new_tokens"] == [256]
    assert summary["retry_max_new_tokens_hit_count"] == 0
    assert summary["retry_no_eos_below_max_count"] == 3
    assert summary["strict_final_json_valid_rate"] == (
        source_diagnosis["summary"]["strict_final_json_valid_rate"]
    ) == 0.0
    assert summary["finish_state_algorithm"] == "tokenizer_eos_membership_only"
    assert summary["model_generate_explicit_eos_token_id_passed"] is False
    assert summary["model_generate_pad_token_id_uses_tokenizer_eos"] is True
    assert summary["model_generation_config_stop_reason_recorded"] is False
    assert summary["actual_generation_stop_reason_recorded"] is False
    assert summary["retry_stop_reason_claim_proven"] is False
    assert summary["max_token_truncation_claim_proven"] is False

    assert [row["row_id"] for row in diagnosis["rows"]] == expected_row_ids
    assert all(row["retry_generation"]["trace_available"] is True for row in diagnosis["rows"])
    assert all(row["retry_generation"]["finish_state"] == "no_eos_observed" for row in diagnosis["rows"])
    assert all(row["retry_generation"]["tokenizer_eos_seen"] is False for row in diagnosis["rows"])
    assert all(row["retry_generation"]["max_new_tokens"] == 256 for row in diagnosis["rows"])
    assert all(row["retry_generation"]["max_new_tokens_hit"] is False for row in diagnosis["rows"])
    assert all(row["retry_generation"]["actual_stop_reason_recorded"] is False for row in diagnosis["rows"])
    assert all(row["retry_generation"]["stop_reason_claim_proven"] is False for row in diagnosis["rows"])
    assert all(row["interpretation"]["actual_stop_reason_unknown"] is True for row in diagnosis["rows"])
    assert all(row["generated_token_count"] < row["max_new_tokens"] for row in source_retry_trace_rows)

    assert diagnosis["evidence_gaps"]["actual_model_generate_stop_reason_missing"] is True
    assert diagnosis["evidence_gaps"]["model_generation_config_eos_id_not_recorded"] is True
    assert diagnosis["evidence_gaps"]["stopping_criteria_status_not_recorded"] is True
    assert diagnosis["evidence_gaps"]["tokenizer_eos_visibility_must_not_be_overstated_as_stop_reason"] is True
    assert diagnosis["recommended_next_step"]["requires_user_confirmation"] is True

    assert manifest["evidence_kind"] == "retry_trace_finish_state_boundary_diagnosis_local"
    assert manifest["source_prior_phase"] == source_dir.as_posix()
    assert manifest["counts"]["rows"] == 3
    assert manifest["counts"]["retry_trace_rows"] == 3
    assert manifest["counts"]["retry_no_eos_below_max_count"] == 3
    assert manifest["counts"]["retry_max_new_tokens_hit_count"] == 0
    for artifact_path in manifest["diagnostic_artifacts"].values():
        assert Path(artifact_path).exists()
    if archive_dir.exists():
        assert manifest["diagnostic_artifacts"]["post_archive_leak_scan"].endswith(
            "post_archive_leak_scan_result.json"
        )
        assert manifest["diagnostic_artifacts"]["final_leak_scan"].endswith("final_leak_scan_result.json")
    else:
        assert "post_archive_leak_scan" not in manifest["diagnostic_artifacts"]
        assert "final_leak_scan" not in manifest["diagnostic_artifacts"]
    assert manifest["claims"]["local_evidence_only_analysis"] is True
    assert manifest["claims"]["a100_execution_performed"] is False
    assert manifest["claims"]["prediction_rerun_performed"] is False
    assert manifest["claims"]["training_performed"] is False
    assert manifest["claims"]["decoding_behavior_change_performed"] is False
    assert manifest["claims"]["retry_prompt_change_performed"] is False
    assert manifest["claims"]["parser_relaxation_performed"] is False
    assert manifest["claims"]["evaluator_metric_change_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["slot_normalization_performed"] is False
    assert manifest["claims"]["stop_reason_instrumentation_change_performed"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False
    assert manifest["claims"]["public_full_corpus_release"] is False
    assert manifest["claims"]["live_browser_benchmark_improvement_claim"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "actual stop reason remains unknown" in report
    assert "No A100 execution or prediction rerun" in report
    assert "162 passed" in human_brief
    assert "OpenSpec strict validate" in human_brief
    assert "不能证明真实 stop reason" in human_brief
    assert "不使用 A100" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_generation_stop_reason_boundary_instrumentation_pack_is_public_safe_and_bounded() -> None:
    evidence_dir = Path("reports/public-sample/generation-stop-reason-boundary-instrumentation")
    human_brief_path = Path("docs/human-briefs/2026-06-06-instrument-generation-stop-reason-boundary.html")
    archive_dir = Path("openspec/changes/archive/2026-06-06-instrument-generation-stop-reason-boundary")
    change_dirs = [
        Path("openspec/changes/instrument-generation-stop-reason-boundary"),
        archive_dir,
    ]
    required_files = {
        "instrumentation_summary.json",
        "instrumentation_summary.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }
    new_trace_fields = {
        "max_new_tokens_hit",
        "finish_state_basis",
        "stop_reason_evidence",
        "actual_stop_reason_recorded",
        "actual_stop_reason",
    }

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    summary = json.loads((evidence_dir / "instrumentation_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "instrumentation_summary.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = (
        json.loads((evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "post_archive_leak_scan_result.json").exists()
        else {"ok": True, "findings": []}
    )
    final_leak_scan = (
        json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "final_leak_scan_result.json").exists()
        else {"ok": True, "findings": []}
    )
    serialized = "\n".join(
        [
            json.dumps(summary, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            human_brief,
        ]
    )

    assert summary["evidence_kind"] == "generation_stop_reason_boundary_instrumentation_local"
    assert summary["instrumentation_kind"] == "generation_trace_stop_boundary_evidence_fields"
    assert new_trace_fields <= set(summary["code_change"]["new_trace_row_fields"])
    assert "finish_state" in summary["code_change"]["trace_row_fields_preserved"]
    assert summary["stop_boundary_semantics"]["finish_state_basis"] == "tokenizer_eos_membership"
    assert summary["stop_boundary_semantics"]["actual_stop_reason_recorded_by_current_code"] is False
    assert summary["stop_boundary_semantics"]["max_token_hit_is_boundary_signal_not_full_stop_reason"] is True
    assert summary["tdd_evidence"]["red_test_observed"] is True
    assert "max_new_tokens_hit" in summary["tdd_evidence"]["red_failure_reason"]
    assert summary["tdd_evidence"]["green_test_observed"] is True
    assert len(summary["tdd_evidence"]["focused_tests"]) == 4
    assert any(command["result"] == "164 passed" for command in summary["validation_commands"])
    assert any(command["result"] == "5 passed, 0 failed" for command in summary["validation_commands"])

    assert manifest["evidence_kind"] == "generation_stop_reason_boundary_instrumentation_local"
    for artifact_path in manifest["diagnostic_artifacts"].values():
        assert Path(artifact_path).exists()
    assert manifest["counts"]["new_trace_row_fields"] == len(new_trace_fields)
    assert len(manifest["source_artifacts"]["focused_tests"]) == 4
    assert any(command["result"] == "164 passed" for command in manifest["validation_commands"])
    assert any(command["result"] == "5 passed, 0 failed" for command in manifest["validation_commands"])
    assert manifest["claims"]["local_instrumentation_only"] is True
    assert manifest["claims"]["a100_execution_performed"] is False
    assert manifest["claims"]["training_or_prediction_rerun_performed"] is False
    assert manifest["claims"]["decoding_change_performed"] is False
    assert manifest["claims"]["parser_relaxation_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False
    assert manifest["claims"]["live_browser_benchmark_improvement_claim"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "actual stop reason remains unrecorded" in report
    assert "不运行 A100" in human_brief
    assert "不改变 decoding" in human_brief
    assert "不能证明真实 stop reason" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_a100_generation_stop_reason_boundary_rerun_evidence_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-retry-generation-trace-rerun")
    local_instrumentation_dir = Path("reports/public-sample/generation-stop-reason-boundary-instrumentation")
    evidence_dir = Path("reports/public-sample/a100-generation-stop-reason-boundary-rerun")
    human_brief_path = Path("docs/human-briefs/2026-06-06-run-a100-generation-stop-reason-boundary-rerun.html")
    archive_dir = Path("openspec/changes/archive/2026-06-06-run-a100-generation-stop-reason-boundary-rerun")
    change_dirs = [
        Path("openspec/changes/run-a100-generation-stop-reason-boundary-rerun"),
        archive_dir,
    ]
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_diagnostics.json",
        "schema_diagnostics.md",
        "constrained_decoding_diagnosis.json",
        "constrained_decoding_diagnosis.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "generation_stop_boundary_diagnosis.json",
        "generation_stop_boundary_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }
    new_trace_fields = {
        "max_new_tokens_hit",
        "finish_state_basis",
        "stop_reason_evidence",
        "actual_stop_reason_recorded",
        "actual_stop_reason",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "generation_stop_boundary_diagnosis.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    prediction_rows = [
        json.loads(line)
        for line in (evidence_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    raw_rows = [
        json.loads(line)
        for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    generation_trace_rows = [
        json.loads(line)
        for line in (evidence_dir / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train_gold_rows = [
        json.loads(line)
        for line in (evidence_dir / "train_split_gold.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8"))
    post_archive_leak_scan = (
        json.loads((evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "post_archive_leak_scan_result.json").exists()
        else {"ok": True, "findings": []}
    )
    final_leak_scan = (
        json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "final_leak_scan_result.json").exists()
        else {"ok": True, "findings": []}
    )
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "generation_stop_boundary_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    prior_manifest = json.loads((prior_dir / "manifest.json").read_text(encoding="utf-8"))
    local_instrumentation_manifest = json.loads(
        (local_instrumentation_dir / "manifest.json").read_text(encoding="utf-8")
    )
    serialized = "\n".join(
        [
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(metrics, ensure_ascii=False, sort_keys=True),
            json.dumps(schema_guard, ensure_ascii=False, sort_keys=True),
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True)
            if post_archive_leak_scan is not None
            else "",
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True) if final_leak_scan is not None else "",
            report,
            diagnosis_markdown,
            human_brief,
        ]
    )
    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["decoding_policy"]["schema_retry_enabled"] is True
    assert metadata["decoding_policy"]["schema_repair_applied"] is False
    assert metadata["decoding_policy"]["generation_trace_sidecar_written"] is True

    assert manifest["evidence_kind"] == "a100_generation_stop_reason_boundary_train_split_rerun"
    assert manifest["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["prediction_split"] == "train"
    assert manifest["overfit_diagnostic"] is True
    assert manifest["generalization_claim"] is False
    assert manifest["prediction_count"] == 3
    assert manifest["training_rows_used"] == 3
    assert manifest["training_row_ids"] == expected_row_ids
    assert manifest["prior_context"]["prior_retry_phase"] == prior_dir.as_posix()
    assert manifest["prior_context"]["local_instrumentation_phase"] == local_instrumentation_dir.as_posix()
    assert prior_manifest["claims"]["generation_trace_sidecar_written"] is True
    assert local_instrumentation_manifest["claims"]["a100_execution_performed"] is False
    assert manifest["artifact_policy"]["a100_execution_performed"] is True
    assert manifest["artifact_policy"]["prediction_rerun_performed"] is True
    assert manifest["artifact_policy"]["training_performed"] is False
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["artifact_policy"]["remote_paths_copied_to_git"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False
    assert manifest["claims"]["decoding_behavior_change_performed"] is False
    assert manifest["claims"]["retry_prompt_change_performed"] is False
    assert manifest["claims"]["parser_relaxation_performed"] is False
    assert manifest["claims"]["evaluator_metric_change_performed"] is False
    assert manifest["prompt_constraints"] == metadata["prompt_constraints"]
    assert manifest["prompt_constraints"]["task_type_enum_visible"] is True
    assert manifest["prompt_constraints"]["single_root_json_object_visible"] is True
    assert manifest["retry_prompt_constraints"] == metadata["retry_prompt_constraints"]
    assert manifest["retry_prompt_constraints"]["no_markdown_prose_visible"] is True
    assert manifest["retry_prompt_constraints"]["strict_parser_rejection_warning_visible"] is True
    assert "3-row train-split rerun" in manifest["recommended_next_step"]["reason"]

    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert [row["id"] for row in generation_trace_rows] == [
        "seed-search-weather",
        "seed-search-weather",
        "seed-search-weather-aug-1",
        "seed-search-weather-aug-1",
        "seed-search-weather-aug-2",
        "seed-search-weather-aug-2",
    ]
    assert all(new_trace_fields <= set(row) for row in generation_trace_rows)
    assert all(row["prediction_source_kind"] == "private_a100_adapter" for row in generation_trace_rows)

    raw_trace_rows = [row for row in generation_trace_rows if row["attempt"] == "raw_attempt"]
    retry_trace_rows = [row for row in generation_trace_rows if row["attempt"] == "retry_attempt"]
    assert len(raw_trace_rows) == 3
    assert len(retry_trace_rows) == 3
    assert all(row["finish_state"] == "eos_observed" for row in raw_trace_rows)
    assert all(row["stop_reason_evidence"] == "tokenizer_eos_observed" for row in raw_trace_rows)
    assert all(row["finish_state"] == "no_eos_observed" for row in retry_trace_rows)
    assert all(
        row["stop_reason_evidence"] == "not_recorded_below_max_without_tokenizer_eos"
        for row in retry_trace_rows
    )
    assert all(row["finish_state_basis"] == "tokenizer_eos_membership" for row in generation_trace_rows)
    assert all(row["actual_stop_reason_recorded"] is False for row in generation_trace_rows)
    assert all(row["actual_stop_reason"] is None for row in generation_trace_rows)
    assert all(row["max_new_tokens_hit"] is False for row in generation_trace_rows)

    assert metrics["metrics"]["json_valid_rate"] == 0.0
    assert metrics["metrics"]["contract_exact_match"] == 0.0
    assert metrics["failure_slices"]["schema"]["count"] == 3

    assert schema_guard["evidence_kind"] == "a100_generation_stop_reason_boundary_schema_guard_summary"
    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["raw_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["retry_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == 0
    assert schema_guard["summary"]["new_trace_fields_present_on_all_rows"] is True
    assert schema_guard["summary"]["actual_stop_reason_recorded_count"] == 0
    assert schema_guard["summary"]["max_new_tokens_hit_count"] == 0
    assert schema_guard["summary"]["raw_tokenizer_eos_observed_count"] == 3
    assert schema_guard["summary"]["retry_no_eos_below_max_count"] == 3
    assert schema_guard["trace_summary"]["stop_reason_evidence_counts"]["raw_attempt"] == {
        "tokenizer_eos_observed": 3
    }
    assert schema_guard["trace_summary"]["stop_reason_evidence_counts"]["retry_attempt"] == {
        "not_recorded_below_max_without_tokenizer_eos": 3
    }

    assert diagnosis["diagnostic_kind"] == "generation_stop_reason_boundary_train_split_diagnosis"
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 0.0
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["new_stop_boundary_fields_observed"] is True
    assert diagnosis["summary"]["actual_generation_stop_reason_recorded"] is False
    assert diagnosis["summary"]["actual_generation_stop_reason_recorded_count"] == 0
    assert diagnosis["summary"]["retry_stop_reason_claim_proven"] is False
    assert diagnosis["summary"]["max_token_truncation_claim_proven"] is False
    assert diagnosis["summary"]["schema_recovery_observed"] is False
    assert diagnosis["summary"]["model_recovery_observed"] is False
    assert diagnosis["evidence_gaps"]["actual_model_generate_stop_reason_missing"] is True
    assert diagnosis["evidence_gaps"]["tokenizer_eos_visibility_must_not_be_overstated_as_stop_reason"] is True
    assert diagnosis["evidence_gaps"]["below_max_without_tokenizer_eos_must_not_be_overstated_as_stop_reason"] is True
    assert all(row["retry_attempt"]["parse_status"] == "json_fragment_object" for row in diagnosis["rows"])
    assert all(row["retry_attempt"]["wrapper_status"] == "prose_markdown_wrapper" for row in diagnosis["rows"])
    assert all(row["retry_attempt"]["prose_markdown_wrapper"] is True for row in diagnosis["rows"])
    assert all(row["retry_generation"]["actual_stop_reason_recorded"] is False for row in diagnosis["rows"])
    assert all(row["interpretation"]["actual_stop_reason_unknown"] is True for row in diagnosis["rows"])
    assert diagnosis["claims"]["a100_execution_performed"] is True
    assert diagnosis["claims"]["prediction_rerun_performed"] is True
    assert diagnosis["claims"]["training_performed"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "actual stop reason remains unrecorded and unknown" in report
    assert "not be described as schema recovery or model recovery" in report
    assert "actual stop reason 仍未被真实记录" in human_brief
    assert "不是模型质量改善" in human_brief
    assert "A100 prediction-only rerun" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_a100_retry_json_only_boundary_rerun_evidence_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-generation-stop-reason-boundary-rerun")
    local_hardening_dir = Path("reports/public-sample/tighten-retry-json-only-output-boundary")
    evidence_dir = Path("reports/public-sample/a100-retry-json-only-boundary-rerun")
    human_brief_path = Path("docs/human-briefs/2026-06-06-run-a100-retry-json-only-boundary-rerun.html")
    archive_dir = Path("openspec/changes/archive/2026-06-06-run-a100-retry-json-only-boundary-rerun")
    change_dirs = [
        Path("openspec/changes/run-a100-retry-json-only-boundary-rerun"),
        archive_dir,
    ]
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_diagnostics.json",
        "schema_diagnostics.md",
        "constrained_decoding_diagnosis.json",
        "constrained_decoding_diagnosis.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "retry_json_only_boundary_diagnosis.json",
        "retry_json_only_boundary_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "retry_json_only_boundary_diagnosis.json").read_text(encoding="utf-8"))
    constrained = json.loads((evidence_dir / "constrained_decoding_diagnosis.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    prediction_rows = [
        json.loads(line)
        for line in (evidence_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    raw_rows = [
        json.loads(line)
        for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    generation_trace_rows = [
        json.loads(line)
        for line in (evidence_dir / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train_gold_rows = [
        json.loads(line)
        for line in (evidence_dir / "train_split_gold.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = None
    final_leak_scan = None
    if archive_dir.exists():
        post_archive_leak_scan = json.loads(
            (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
        )
        final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "retry_json_only_boundary_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    prior_manifest = json.loads((prior_dir / "manifest.json").read_text(encoding="utf-8"))
    local_summary = json.loads(
        (local_hardening_dir / "retry_json_only_boundary_summary.json").read_text(encoding="utf-8")
    )
    serialized = "\n".join(
        [
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(metrics, ensure_ascii=False, sort_keys=True),
            json.dumps(schema_guard, ensure_ascii=False, sort_keys=True),
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(constrained, ensure_ascii=False, sort_keys=True),
            json.dumps(prompt_snapshot, ensure_ascii=False, sort_keys=True),
            json.dumps(prediction_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(raw_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(generation_trace_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True)
            if post_archive_leak_scan is not None
            else "",
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True) if final_leak_scan is not None else "",
            report,
            diagnosis_markdown,
            human_brief,
        ]
    )
    for artifact_path in manifest["artifacts"].values():
        assert Path(artifact_path).exists()
    for artifact_path in manifest["diagnostic_artifacts"].values():
        assert Path(artifact_path).exists()
    for artifact_path in diagnosis["artifacts"].values():
        assert Path(artifact_path).exists()

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["decoding_policy"]["schema_retry_enabled"] is True
    assert metadata["decoding_policy"]["schema_repair_applied"] is False
    assert metadata["retry_prompt_constraints"]["exact_json_only_output_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_text_outside_root_json_object_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_natural_language_wrapper_or_preamble_visible"] is True
    assert metadata["retry_prompt_constraints"]["machine_readable_only_retry_response_visible"] is True
    assert prompt_snapshot["retry_prompt_constraints"] == metadata["retry_prompt_constraints"]

    assert manifest["evidence_kind"] == "a100_retry_json_only_boundary_train_split_rerun"
    assert manifest["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["prediction_split"] == "train"
    assert manifest["prediction_count"] == 3
    assert manifest["training_rows_used"] == 3
    assert manifest["prior_context"]["prior_a100_stop_boundary_rerun"] == prior_dir.as_posix()
    assert manifest["prior_context"]["local_hardening_a100_execution_performed"] is False
    assert manifest["prior_context"]["local_hardening_private_prediction_rerun_performed"] is False
    assert prior_manifest["observed_result"]["retry_json_fragment_object_count"] == 3
    assert local_summary["claims"]["local_retry_prompt_boundary_hardening_only"] is True
    assert manifest["artifact_policy"]["a100_execution_performed"] is True
    assert manifest["artifact_policy"]["prediction_rerun_performed"] is True
    assert manifest["artifact_policy"]["training_performed"] is False
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["artifact_policy"]["remote_paths_copied_to_git"] is False
    assert manifest["claims"]["retry_prompt_change_performed"] is True
    assert manifest["claims"]["decoding_behavior_change_performed"] is False
    assert manifest["claims"]["parser_relaxation_performed"] is False
    assert manifest["claims"]["evaluator_metric_change_performed"] is False
    assert manifest["claims"]["schema_repair_or_coercion_applied"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_recovery_claim"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False

    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert {row["attempt"] for row in generation_trace_rows} == {"raw_attempt", "retry_attempt"}
    assert len(generation_trace_rows) == 6

    assert metrics["metrics"]["json_valid_rate"] == 0.0
    assert metrics["metrics"]["contract_exact_match"] == 0.0
    assert metrics["failure_slices"]["schema"]["count"] == 3
    assert constrained["summary"]["parse_status_counts"]["retry_attempt"] == {"json_fragment_object": 3}
    assert constrained["summary"]["prose_markdown_wrapper_count"] == 3
    assert constrained["summary"]["validated_output_schema_valid_count"] == 0

    assert schema_guard["evidence_kind"] == "a100_retry_json_only_boundary_schema_guard_summary"
    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["raw_json_object_count"] == 3
    assert schema_guard["summary"]["retry_json_fragment_object_count"] == 3
    assert schema_guard["summary"]["retry_prose_markdown_wrapper_count"] == 3
    assert schema_guard["summary"]["retry_attempt_schema_valid_count"] == 0
    assert schema_guard["summary"]["strict_retry_parser_rejected_fragment_count"] == 3
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == 0
    assert schema_guard["summary"]["retry_boundary_improvement_observed"] is False

    assert diagnosis["diagnostic_kind"] == "retry_json_only_boundary_train_split_diagnosis"
    assert diagnosis["summary"]["retry_prompt_constraints_visible_count"] == 15
    assert diagnosis["summary"]["new_retry_json_only_constraints_visible"] == {
        "exact_json_only_output_visible": True,
        "machine_readable_only_retry_response_visible": True,
        "no_natural_language_wrapper_or_preamble_visible": True,
        "no_text_outside_root_json_object_visible": True,
    }
    assert diagnosis["summary"]["retry_json_fragment_object_count"] == 3
    assert diagnosis["summary"]["retry_prose_markdown_wrapper_count"] == 3
    assert diagnosis["summary"]["strict_retry_parser_rejected_fragment_count"] == 3
    assert diagnosis["summary"]["validated_output_schema_valid_count"] == 0
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 0.0
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["prior_strict_final_json_valid_rate"] == 0.0
    assert diagnosis["summary"]["prior_strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["schema_recovery_observed"] is False
    assert diagnosis["summary"]["retry_boundary_improvement_observed"] is False
    assert diagnosis["interpretation"]["retry_prompt_policy_visible_in_metadata"] is True
    assert diagnosis["interpretation"]["retry_wrapper_still_observed"] is True
    assert diagnosis["interpretation"]["strict_retry_parser_rejected_wrapped_fragments"] is True
    assert diagnosis["interpretation"]["strict_metrics_unchanged_from_prior_stop_boundary"] is True
    assert diagnosis["interpretation"]["parser_relaxation_recommended"] is False
    assert diagnosis["interpretation"]["prediction_repair_recommended"] is False
    assert all(row["retry_attempt_parse_status"] == "json_fragment_object" for row in diagnosis["rows"])
    assert all(row["strict_retry_parser_rejected_fragment"] is True for row in diagnosis["rows"])
    assert all(row["retry_prose_markdown_wrapper_visible"] is True for row in diagnosis["rows"])
    assert all(row["trace_attempts"] == ["raw_attempt", "retry_attempt"] for row in diagnosis["rows"])
    assert all(row["raw_trace_available"] is True for row in diagnosis["rows"])
    assert all(row["retry_trace_available"] is True for row in diagnosis["rows"])
    assert all(row["trace_attempts"] == ["raw_attempt", "retry_attempt"] for row in schema_guard["rows"])
    assert all(row["raw_trace_available"] is True for row in schema_guard["rows"])
    assert all(row["retry_trace_available"] is True for row in schema_guard["rows"])

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    if archive_dir.exists():
        assert post_archive_leak_scan is not None
        assert post_archive_leak_scan["ok"] is True
        assert post_archive_leak_scan["findings"] == []
        assert final_leak_scan is not None
        assert final_leak_scan["ok"] is True
        assert final_leak_scan["findings"] == []
    assert "Retry prompt constraints are visible" in report
    assert "retry attempts remain prose/Markdown-wrapped JSON fragments" in report
    assert "not be described as schema recovery or model recovery" in report
    assert "strict final metrics remain the source of truth" in diagnosis_markdown
    assert "约束已进入 A100 prediction metadata" in human_brief
    assert "没有模型质量改善" in human_brief
    assert "不要把 embedded JSON fragment 描述成有效预测" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_a100_retry_template_boundary_rerun_evidence_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-retry-json-only-boundary-rerun")
    local_template_dir = Path("reports/public-sample/retry-template-decoding-boundary")
    evidence_dir = Path("reports/public-sample/a100-retry-template-boundary-rerun")
    human_brief_path = Path("docs/human-briefs/2026-06-06-run-a100-retry-template-boundary-rerun.html")
    archive_dir = Path("openspec/changes/archive/2026-06-06-run-a100-retry-template-boundary-rerun")
    change_dirs = [
        Path("openspec/changes/run-a100-retry-template-boundary-rerun"),
        archive_dir,
    ]
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_diagnostics.json",
        "schema_diagnostics.md",
        "constrained_decoding_diagnosis.json",
        "constrained_decoding_diagnosis.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "retry_template_boundary_diagnosis.json",
        "retry_template_boundary_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    constrained = json.loads((evidence_dir / "constrained_decoding_diagnosis.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "retry_template_boundary_diagnosis.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    constrained_markdown = (evidence_dir / "constrained_decoding_diagnosis.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "retry_template_boundary_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    prediction_rows = [
        json.loads(line)
        for line in (evidence_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    raw_rows = [
        json.loads(line)
        for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    generation_trace_rows = [
        json.loads(line)
        for line in (evidence_dir / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train_gold_rows = [
        json.loads(line)
        for line in (evidence_dir / "train_split_gold.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = None
    final_leak_scan = None
    if archive_dir.exists():
        post_archive_leak_scan = json.loads(
            (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
        )
        final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    prior_manifest = json.loads((prior_dir / "manifest.json").read_text(encoding="utf-8"))
    local_manifest = json.loads((local_template_dir / "manifest.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(prompt_snapshot, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(metrics, ensure_ascii=False, sort_keys=True),
            json.dumps(schema_guard, ensure_ascii=False, sort_keys=True),
            json.dumps(constrained, ensure_ascii=False, sort_keys=True),
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(prediction_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(raw_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(generation_trace_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True)
            if post_archive_leak_scan is not None
            else "",
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True) if final_leak_scan is not None else "",
            report,
            constrained_markdown,
            diagnosis_markdown,
            human_brief,
        ]
    )

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["decoding_policy"]["schema_retry_enabled"] is True
    assert metadata["decoding_policy"]["schema_repair_applied"] is False
    assert metadata["retry_template_boundary"] == prompt_snapshot["retry_template_boundary"]
    assert all(metadata["retry_template_boundary"].values())

    assert manifest["evidence_kind"] == "a100_retry_template_boundary_train_split_rerun"
    assert manifest["observed_result"]["prediction_count"] == 3
    assert manifest["observed_result"]["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["observed_result"]["prediction_split"] == "train"
    assert manifest["observed_result"]["strict_final_json_valid_rate"] == 1.0
    assert manifest["observed_result"]["strict_final_contract_exact_match"] == 0.0
    assert manifest["observed_result"]["raw_attempt_schema_valid_count"] == 1
    assert manifest["observed_result"]["retry_attempted_count"] == 2
    assert manifest["observed_result"]["retry_attempt_schema_valid_count"] == 2
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 3
    assert manifest["observed_result"]["retry_prose_markdown_wrapper_count"] == 0
    assert manifest["observed_result"]["schema_recovery_observed"] is True
    assert manifest["observed_result"]["exact_match_recovery_observed"] is False
    assert manifest["observed_result"]["model_quality_improvement_claim"] is False
    assert manifest["source_artifacts"]["prior_a100_retry_json_only_rerun"] == prior_dir.as_posix()
    assert manifest["source_artifacts"]["local_retry_template_boundary"] == local_template_dir.as_posix()
    assert prior_manifest["observed_result"]["strict_final_json_valid_rate"] == 0.0
    assert local_manifest["claims"]["local_retry_template_boundary_hardening_only"] is True
    assert manifest["artifact_policy"]["a100_execution_performed"] is True
    assert manifest["artifact_policy"]["prediction_rerun_performed"] is True
    assert manifest["artifact_policy"]["training_performed"] is False
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["checkpoints_or_adapters_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["artifact_policy"]["remote_paths_copied_to_git"] is False
    assert manifest["claims"]["training_performed"] is False
    assert manifest["claims"]["parser_relaxation_performed"] is False
    assert manifest["claims"]["evaluator_metric_change_performed"] is False
    assert manifest["claims"]["schema_repair_or_coercion_applied"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False

    for artifact_path in manifest["artifacts"].values():
        assert Path(artifact_path).exists()
    for artifact_path in manifest["diagnostic_artifacts"].values():
        assert Path(artifact_path).exists()

    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert len(generation_trace_rows) == 5
    assert {row["attempt"] for row in generation_trace_rows} == {"raw_attempt", "retry_attempt"}

    assert metrics["metrics"]["json_valid_rate"] == 1.0
    assert metrics["metrics"]["contract_exact_match"] == 0.0
    assert metrics["metrics"]["slot_f1"] == 0.0
    assert metrics["failure_slices"]["schema"]["count"] == 0
    assert metrics["failure_slices"]["slot"]["count"] == 3

    assert schema_guard["evidence_kind"] == "a100_retry_template_boundary_schema_guard_summary"
    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["raw_json_object_count"] == 3
    assert schema_guard["summary"]["raw_attempt_schema_valid_count"] == 1
    assert schema_guard["summary"]["retry_attempted_count"] == 2
    assert schema_guard["summary"]["retry_attempt_schema_valid_count"] == 2
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == 3
    assert schema_guard["summary"]["retry_prose_markdown_wrapper_count"] == 0
    assert schema_guard["summary"]["strict_retry_parser_rejected_fragment_count"] == 0
    assert schema_guard["summary"]["schema_recovery_observed"] is True
    assert schema_guard["summary"]["exact_match_recovery_observed"] is False
    assert schema_guard["parse_status_counts"]["raw_attempt"] == {"json_object": 3}
    assert schema_guard["parse_status_counts"]["retry_attempt"] == {"json_object": 2}
    assert schema_guard["retry_template_boundary"] == metadata["retry_template_boundary"]
    assert schema_guard["trace_summary"]["attempt_counts"] == {"raw_attempt": 3, "retry_attempt": 2}

    assert constrained["claims"]["evidence_context"] == "a100_prediction_rerun"
    assert constrained["claims"]["a100_prediction_rerun_evidence"] is True
    assert constrained["claims"]["local_decoder_output_shape_hardening_only"] is False
    assert constrained["summary"]["validated_output_schema_valid_count"] == 3
    assert "A100 prediction-rerun evidence" in constrained_markdown
    assert "local decoder/output-shape hardening evidence only" not in constrained_markdown

    assert diagnosis["diagnostic_kind"] == "retry_template_boundary_train_split_diagnosis"
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 1.0
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["prior_strict_final_json_valid_rate"] == 0.0
    assert diagnosis["summary"]["prior_strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["schema_recovery_observed"] is True
    assert diagnosis["summary"]["exact_match_recovery_observed"] is False
    assert diagnosis["summary"]["retry_template_boundary_visible"] is True
    assert diagnosis["interpretation"]["retry_template_boundary_visible_in_metadata"] is True
    assert diagnosis["interpretation"]["schema_recovery_observed"] is True
    assert diagnosis["interpretation"]["exact_match_recovery_observed"] is False
    assert diagnosis["interpretation"]["model_quality_improvement_claim"] is False
    assert all(row["raw_trace_available"] is True for row in diagnosis["rows"])
    assert sum(row["retry_trace_available"] for row in diagnosis["rows"]) == 2

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    if archive_dir.exists():
        assert post_archive_leak_scan is not None
        assert post_archive_leak_scan["ok"] is True
        assert post_archive_leak_scan["findings"] == []
        assert final_leak_scan is not None
        assert final_leak_scan["ok"] is True
        assert final_leak_scan["findings"] == []
    assert "schema-valid recovery observed" in report
    assert "exact match remains 0.0" in report
    assert "not a model-quality improvement claim" in diagnosis_markdown
    assert "schema-valid 已恢复到 3/3" in human_brief
    assert "exact match 仍为 0/3" in human_brief
    assert "retry attempt 产出 schema-valid 输出" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_retry_template_slot_exact_match_mismatch_diagnosis_pack_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-retry-template-boundary-rerun")
    evidence_dir = Path("reports/public-sample/retry-template-slot-exact-match-mismatch-diagnosis")
    human_brief_path = Path(
        "docs/human-briefs/2026-06-06-diagnose-retry-template-slot-exact-match-mismatch.html"
    )
    archive_dir = Path(
        "openspec/changes/archive/2026-06-06-diagnose-retry-template-slot-exact-match-mismatch"
    )
    change_dirs = [
        Path("openspec/changes/diagnose-retry-template-slot-exact-match-mismatch"),
        archive_dir,
    ]
    required_files = {
        "slot_exact_match_mismatch_diagnosis.json",
        "slot_exact_match_mismatch_diagnosis.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    diagnosis = json.loads((evidence_dir / "slot_exact_match_mismatch_diagnosis.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = None
    final_leak_scan = None
    if archive_dir.exists():
        post_archive_leak_scan = json.loads(
            (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
        )
        final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    markdown = (evidence_dir / "slot_exact_match_mismatch_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    prior_metrics = json.loads((prior_dir / "metrics.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True)
            if post_archive_leak_scan is not None
            else "",
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True) if final_leak_scan is not None else "",
            markdown,
            human_brief,
        ]
    )

    assert diagnosis["diagnostic_kind"] == "retry_template_slot_exact_match_mismatch_diagnosis"
    assert diagnosis["summary"]["gold_row_count"] == 3
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["row_mismatch_count"] == 3
    assert diagnosis["summary"]["schema_invalid_prediction_count"] == 0
    assert diagnosis["summary"]["validated_output_schema_valid_count"] == 3
    assert diagnosis["summary"]["field_mismatch_counts"] == {"normalized_command": 1, "slots": 3}
    assert diagnosis["summary"]["slot_family_counts"] == {
        "city_date_slots_instead_of_query": 2,
        "query_slot_strict_string_mismatch": 1,
    }
    assert diagnosis["summary"]["normalized_command_mismatch_count"] == 1
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == prior_metrics["metrics"]["json_valid_rate"] == 1.0
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == (
        prior_metrics["metrics"]["contract_exact_match"]
    ) == 0.0
    assert diagnosis["summary"]["strict_final_task_type_accuracy"] == prior_metrics["metrics"]["task_type_accuracy"]
    assert diagnosis["summary"]["strict_final_route_accuracy"] == prior_metrics["metrics"]["route_accuracy"]
    assert diagnosis["summary"]["strict_final_confirmation_accuracy"] == (
        prior_metrics["metrics"]["confirmation_accuracy"]
    )
    assert diagnosis["summary"]["strict_final_slot_f1"] == prior_metrics["metrics"]["slot_f1"] == 0.0
    assert [row["row_id"] for row in diagnosis["rows"]] == expected_row_ids
    row_families = {row["row_id"]: row["primary_slot_mismatch_family"] for row in diagnosis["rows"]}
    assert row_families == {
        "seed-search-weather": "city_date_slots_instead_of_query",
        "seed-search-weather-aug-1": "city_date_slots_instead_of_query",
        "seed-search-weather-aug-2": "query_slot_strict_string_mismatch",
    }
    row_statuses = {row["row_id"]: row["source_prediction_status"] for row in diagnosis["rows"]}
    assert row_statuses["seed-search-weather"]["validated_output_source"] == "retry_attempt"
    assert row_statuses["seed-search-weather-aug-1"]["validated_output_source"] == "raw_attempt"
    assert row_statuses["seed-search-weather-aug-2"]["validated_output_source"] == "retry_attempt"
    assert all(status["validated_output_schema_valid"] is True for status in row_statuses.values())
    assert diagnosis["source_artifact_policy"]["uses_prior_public_sample_artifacts_only"] is True
    assert diagnosis["source_artifact_policy"]["a100_execution_performed"] is False
    assert diagnosis["source_artifact_policy"]["prediction_rerun_performed"] is False
    assert diagnosis["source_artifact_policy"]["slot_normalization_performed"] is False
    assert diagnosis["claims"]["local_evidence_only_analysis"] is True
    assert diagnosis["claims"]["slot_normalization_performed"] is False
    assert diagnosis["claims"]["normalized_command_normalization_performed"] is False
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False

    assert manifest["evidence_kind"] == "retry_template_slot_exact_match_mismatch_diagnosis"
    assert manifest["source_prior_phase"] == prior_dir.as_posix()
    assert manifest["counts"] == {
        "rows": 3,
        "validated_output_schema_valid": 3,
        "city_date_slots_instead_of_query": 2,
        "query_slot_strict_string_mismatch": 1,
        "normalized_command_mismatch": 1,
    }
    assert manifest["metrics_preserved"]["json_valid_rate"] == 1.0
    assert manifest["metrics_preserved"]["contract_exact_match"] == 0.0
    assert manifest["metrics_preserved"]["slot_f1"] == 0.0
    assert manifest["diagnostic_artifacts"]["slot_exact_match_mismatch_diagnosis"].endswith(
        "slot_exact_match_mismatch_diagnosis.json"
    )
    assert manifest["diagnostic_artifacts"]["slot_exact_match_mismatch_report"].endswith(
        "slot_exact_match_mismatch_diagnosis.md"
    )
    assert manifest["source_artifacts"]["predictions"].endswith("predictions.jsonl")
    assert manifest["source_artifacts"]["train_split_gold"].endswith("train_split_gold.jsonl")
    assert manifest["claims"]["local_evidence_only_analysis"] is True
    assert manifest["claims"]["slot_normalization_performed"] is False
    assert manifest["claims"]["normalized_command_normalization_performed"] is False
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["prediction_repair_or_rescore_performed"] is False
    assert manifest["claims"]["model_quality_improvement_claim"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    if archive_dir.exists():
        assert post_archive_leak_scan is not None
        assert post_archive_leak_scan["ok"] is True
        assert post_archive_leak_scan["findings"] == []
        assert final_leak_scan is not None
        assert final_leak_scan["ok"] is True
        assert final_leak_scan["findings"] == []
    assert "local evidence-only analysis" in markdown
    assert "No A100 execution was performed in this phase" in markdown
    assert "city_date_slots_instead_of_query" in markdown
    assert "query_slot_strict_string_mismatch" in markdown
    assert "schema-valid 3/3 但 exact match 0/3" in human_brief
    assert "不使用 A100" in human_brief
    assert "不做 slot normalization" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_search_query_slot_target_policy_pack_is_public_safe_and_bounded() -> None:
    source_dir = Path("reports/public-sample/retry-template-slot-exact-match-mismatch-diagnosis")
    evidence_dir = Path("reports/public-sample/search-query-slot-target-policy")
    human_brief_path = Path("docs/human-briefs/2026-06-06-define-search-query-slot-target-policy.html")
    archive_dir = Path("openspec/changes/archive/2026-06-06-define-search-query-slot-target-policy")
    change_dirs = [
        Path("openspec/changes/define-search-query-slot-target-policy"),
        archive_dir,
    ]
    required_files = {
        "policy_summary.json",
        "policy_summary.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    summary = json.loads((evidence_dir / "policy_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "policy_summary.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = None
    final_leak_scan = None
    if archive_dir.exists():
        post_archive_leak_scan = json.loads(
            (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
        )
        final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(summary, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True)
            if post_archive_leak_scan is not None
            else "",
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True) if final_leak_scan is not None else "",
            report,
            human_brief,
        ]
    )

    assert summary["evidence_kind"] == "search_query_slot_target_policy"
    assert summary["source_prior_phase"] == source_dir.as_posix()
    assert summary["prompt_constraints"]["compact_search_query_slot_policy_visible"] is True
    assert summary["prompt_constraints"]["search_query_no_city_date_split_visible"] is True
    assert summary["public_sample_search_rows"]["count"] == 3
    assert summary["public_sample_search_rows"]["compact_query_count"] == 3
    assert summary["public_sample_search_rows"]["city_date_slot_count"] == 0
    assert summary["public_sample_search_rows"]["spaced_query_count"] == 0
    assert summary["public_sample_search_rows"]["query_values"] == ["北京明天天气"]
    assert summary["dpo_search_pairs"]["chosen_compact_query_count"] == summary["dpo_search_pairs"]["count"]
    assert summary["dpo_search_pairs"]["chosen_city_date_slot_count"] == 0
    assert summary["claims"]["a100_execution_performed"] is False
    assert summary["claims"]["training_or_prediction_rerun_performed"] is False
    assert summary["claims"]["slot_normalization_performed"] is False
    assert summary["claims"]["semantic_equivalence_scoring_performed"] is False
    assert summary["claims"]["prediction_repair_or_rescore_performed"] is False
    assert summary["claims"]["model_quality_improvement_claim"] is False

    assert manifest["evidence_kind"] == "search_query_slot_target_policy"
    assert manifest["diagnostic_artifacts"]["policy_summary"].endswith("policy_summary.json")
    assert manifest["diagnostic_artifacts"]["policy_report"].endswith("policy_summary.md")
    assert manifest["source_artifacts"]["prior_slot_diagnosis"].endswith(
        "slot_exact_match_mismatch_diagnosis.json"
    )
    assert manifest["claims"] == summary["claims"]
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    if archive_dir.exists():
        assert post_archive_leak_scan is not None
        assert post_archive_leak_scan["ok"] is True
        assert post_archive_leak_scan["findings"] == []
        assert final_leak_scan is not None
        assert final_leak_scan["ok"] is True
        assert final_leak_scan["findings"] == []
    assert "compact slots.query" in report
    assert "no city/date slot splitting" in report
    assert "不运行 A100" in human_brief
    assert "不做 slot normalization" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_a100_search_query_slot_policy_rerun_pack_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-retry-template-boundary-rerun")
    prior_slot_diagnosis_dir = Path("reports/public-sample/retry-template-slot-exact-match-mismatch-diagnosis")
    local_policy_dir = Path("reports/public-sample/search-query-slot-target-policy")
    evidence_dir = Path("reports/public-sample/a100-search-query-slot-policy-rerun")
    human_brief_path = Path("docs/human-briefs/2026-06-08-run-a100-search-query-slot-policy-rerun.html")
    archive_dir = Path("openspec/changes/archive/2026-06-08-run-a100-search-query-slot-policy-rerun")
    change_dirs = [
        Path("openspec/changes/run-a100-search-query-slot-policy-rerun"),
        archive_dir,
    ]
    required_files = {
        "predictions.jsonl",
        "prediction_metadata.json",
        "prompt_snapshot.json",
        "raw_decoded_summary.jsonl",
        "generation_trace.jsonl",
        "train_split_gold.jsonl",
        "metrics.json",
        "metrics.md",
        "schema_guard_summary.json",
        "schema_guard_summary.md",
        "slot_policy_rerun_diagnosis.json",
        "slot_policy_rerun_diagnosis.md",
        "manifest.json",
        "report.md",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    metadata = json.loads((evidence_dir / "prediction_metadata.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_guard = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    diagnosis = json.loads((evidence_dir / "slot_policy_rerun_diagnosis.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    prediction_rows = [
        json.loads(line)
        for line in (evidence_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train_gold_rows = [
        json.loads(line)
        for line in (evidence_dir / "train_split_gold.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    generation_trace_rows = [
        json.loads(line)
        for line in (evidence_dir / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    diagnosis_markdown = (evidence_dir / "slot_policy_rerun_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = None
    final_leak_scan = None
    if archive_dir.exists():
        post_archive_leak_scan = json.loads(
            (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
        )
        final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(prompt_snapshot, ensure_ascii=False, sort_keys=True),
            json.dumps(metrics, ensure_ascii=False, sort_keys=True),
            json.dumps(schema_guard, ensure_ascii=False, sort_keys=True),
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(prediction_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(train_gold_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(generation_trace_rows, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True)
            if post_archive_leak_scan is not None
            else "",
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True) if final_leak_scan is not None else "",
            report,
            diagnosis_markdown,
            human_brief,
        ]
    )

    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_count"] == 3
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["prompt_constraints"]["compact_search_query_slot_policy_visible"] is True
    assert metadata["prompt_constraints"]["search_query_no_city_date_split_visible"] is True
    assert prompt_snapshot["prompt_constraints"]["compact_search_query_slot_policy_visible"] is True
    assert prompt_snapshot["prompt_constraints"]["search_query_no_city_date_split_visible"] is True

    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert {row["attempt"] for row in generation_trace_rows} <= {"raw_attempt", "retry_attempt"}

    for row in train_gold_rows:
        contract = row["target_contract"]
        assert contract["slots"] == {"query": "北京明天天气"}
        assert contract["normalized_command"] == "搜索北京明天天气"
        assert not ({"city", "date", "topic"} & set(contract["slots"]))
    assert "北京 明天 天气" not in json.dumps(train_gold_rows, ensure_ascii=False)

    assert metrics["metrics"]["json_valid_rate"] == diagnosis["summary"]["strict_final_json_valid_rate"]
    assert metrics["metrics"]["contract_exact_match"] == diagnosis["summary"]["strict_final_contract_exact_match"]
    assert schema_guard["summary"]["prediction_count"] == 3
    assert schema_guard["summary"]["validated_output_schema_valid_count"] == diagnosis["summary"][
        "validated_output_schema_valid_count"
    ]

    assert diagnosis["diagnostic_kind"] == "a100_search_query_slot_policy_rerun"
    assert diagnosis["source_prior_phase"] == prior_dir.as_posix()
    assert diagnosis["source_artifacts"]["prior_slot_diagnosis"].startswith(prior_slot_diagnosis_dir.as_posix())
    assert diagnosis["source_artifacts"]["local_search_query_slot_policy"].startswith(local_policy_dir.as_posix())
    assert diagnosis["target_policy"]["compact_slots_query"] is True
    assert diagnosis["target_policy"]["no_city_date_slot_splitting"] is True
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["gold_compact_query_count"] == 3
    assert diagnosis["summary"]["gold_spaced_query_count"] == 0
    assert diagnosis["summary"]["gold_city_date_slot_count"] == 0
    assert diagnosis["summary"]["exact_match_count"] == int(metrics["metrics"]["contract_exact_match"] * 3)
    assert isinstance(diagnosis["summary"]["exact_match_recovery_vs_prior_observed"], bool)
    assert diagnosis["summary"]["strict_final_contract_exact_match"] >= 0.0
    assert diagnosis["summary"]["strict_final_contract_exact_match"] <= 1.0
    assert diagnosis["claims"]["a100_execution_performed"] is True
    assert diagnosis["claims"]["prediction_rerun_performed"] is True
    assert diagnosis["claims"]["training_performed"] is False
    assert diagnosis["claims"]["slot_normalization_performed"] is False
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False
    assert diagnosis["claims"]["held_out_generalization_claim"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False

    assert manifest["evidence_kind"] == "a100_search_query_slot_policy_train_split_rerun"
    assert manifest["observed_result"] == diagnosis["summary"]
    assert manifest["source_artifacts"]["prior_a100_retry_template_boundary_rerun"] == prior_dir.as_posix()
    assert manifest["source_artifacts"]["prior_slot_diagnosis"].startswith(prior_slot_diagnosis_dir.as_posix())
    assert manifest["source_artifacts"]["local_search_query_slot_policy"].startswith(local_policy_dir.as_posix())
    assert manifest["artifact_policy"]["a100_execution_performed"] is True
    assert manifest["artifact_policy"]["prediction_rerun_performed"] is True
    assert manifest["artifact_policy"]["training_performed"] is False
    assert manifest["artifact_policy"]["train_split_only"] is True
    assert manifest["artifact_policy"]["private_configs_copied_to_git"] is False
    assert manifest["artifact_policy"]["raw_logs_copied_to_git"] is False
    assert manifest["artifact_policy"]["remote_paths_copied_to_git"] is False
    assert manifest["claims"] == diagnosis["claims"]
    for artifact_path in manifest["artifacts"].values():
        assert Path(artifact_path).exists()

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    if archive_dir.exists():
        assert post_archive_leak_scan is not None
        assert post_archive_leak_scan["ok"] is True
        assert post_archive_leak_scan["findings"] == []
        assert final_leak_scan is not None
        assert final_leak_scan["ok"] is True
        assert final_leak_scan["findings"] == []
    assert "compact slots.query" in report
    assert "train-split-only prediction evidence" in diagnosis_markdown
    assert "A100 prediction-only" in human_brief
    assert "不做 slot normalization" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_a100_search_query_slot_wrapper_boundary_diagnosis_pack_is_public_safe_and_bounded() -> None:
    source_dir = Path("reports/public-sample/a100-search-query-slot-policy-rerun")
    evidence_dir = Path("reports/public-sample/a100-search-query-slot-wrapper-boundary-diagnosis")
    human_brief_path = Path(
        "docs/human-briefs/2026-06-08-diagnose-a100-search-query-slot-wrapper-boundary.html"
    )
    archive_dir = Path("openspec/changes/archive/2026-06-08-diagnose-a100-search-query-slot-wrapper-boundary")
    change_dirs = [
        Path("openspec/changes/diagnose-a100-search-query-slot-wrapper-boundary"),
        archive_dir,
    ]
    required_files = {
        "wrapper_boundary_diagnosis.json",
        "wrapper_boundary_diagnosis.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    if archive_dir.exists():
        assert {"post_archive_leak_scan_result.json", "final_leak_scan_result.json"} <= {
            path.name for path in evidence_dir.iterdir()
        }
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    diagnosis = json.loads((evidence_dir / "wrapper_boundary_diagnosis.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "wrapper_boundary_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = (
        json.loads((evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "post_archive_leak_scan_result.json").exists()
        else None
    )
    final_leak_scan = (
        json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
        if (evidence_dir / "final_leak_scan_result.json").exists()
        else None
    )
    source_diagnosis = json.loads((source_dir / "slot_policy_rerun_diagnosis.json").read_text(encoding="utf-8"))
    generation_trace_rows = [
        json.loads(line)
        for line in (source_dir / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    serialized = "\n".join(
        [
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True)
            if post_archive_leak_scan is not None
            else "",
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True) if final_leak_scan is not None else "",
            report,
            human_brief,
        ]
    )

    assert diagnosis["evidence_kind"] == "a100_search_query_slot_wrapper_boundary_diagnosis_local"
    assert diagnosis["diagnostic_kind"] == "a100_search_query_slot_wrapper_boundary_diagnosis"
    assert diagnosis["source_prior_phase"] == source_dir.as_posix()
    assert diagnosis["source_artifacts"]["source_diagnosis"].endswith("slot_policy_rerun_diagnosis.json")
    assert diagnosis["source_artifact_policy"]["uses_prior_public_sample_artifacts_only"] is True
    assert diagnosis["source_artifact_policy"]["source_predictions_preserved"] is True
    assert diagnosis["source_artifact_policy"]["source_metrics_preserved"] is True
    assert diagnosis["source_artifact_policy"]["source_generation_trace_preserved"] is True
    assert diagnosis["source_artifact_policy"]["no_private_raw_logs_or_adapters_read"] is True

    summary = diagnosis["summary"]
    assert summary["prediction_count"] == 3
    assert summary["row_ids"] == expected_row_ids
    assert summary["strict_final_json_valid_rate"] == source_diagnosis["summary"]["strict_final_json_valid_rate"] == 0
    assert summary["strict_final_contract_exact_match"] == 0
    assert summary["validated_output_schema_valid_count"] == 0
    assert summary["embedded_compact_query_fragment_count"] == 3
    assert summary["markdown_wrapped_prediction_count"] == 3
    assert summary["raw_attempt_schema_valid_count"] == 0
    assert summary["retry_attempt_schema_valid_count"] == 0
    assert summary["raw_parse_status_counts"] == {"json_fragment_object": 3}
    assert summary["retry_parse_status_counts"] == {"json_fragment_object": 3}
    assert summary["raw_generation_trace_available"] is True
    assert summary["retry_generation_trace_available"] is True
    assert summary["raw_generation_eos_seen_count"] == 3
    assert summary["retry_generation_eos_seen_count"] == 3
    assert summary["raw_generation_max_new_tokens_hit_count"] == 0
    assert summary["retry_generation_max_new_tokens_hit_count"] == 0
    assert summary["generation_trace_attempt_counts"] == {"raw_attempt": 3, "retry_attempt": 3}
    assert summary["wrapper_origin_proven"] is False
    assert summary["strict_parser_accepts_markdown_wrappers"] is False

    assert [row["row_id"] for row in diagnosis["rows"]] == expected_row_ids
    for row in diagnosis["rows"]:
        assert row["raw_attempt"]["parse_status"] == "json_fragment_object"
        assert row["retry_attempt"]["parse_status"] == "json_fragment_object"
        assert row["raw_generation"]["finish_state"] == "eos_observed"
        assert row["retry_generation"]["finish_state"] == "eos_observed"
        assert row["raw_generation"]["max_new_tokens_hit"] is False
        assert row["retry_generation"]["max_new_tokens_hit"] is False
        assert row["observed_wrapper"]["markdown_fence_visible"] is True
        assert row["observed_wrapper"]["compact_query_fragment_visible"] is True
        assert row["validated_output"]["schema_valid"] is False

    assert diagnosis["evidence_gaps"]["wrapper_origin_unproven"] is True
    assert diagnosis["evidence_gaps"]["prompt_template_decoder_or_training_cause_unproven"] is True
    assert diagnosis["interpretation"]["compact_query_content_is_not_strict_schema_recovery"] is True
    assert diagnosis["interpretation"]["eos_observed_does_not_mean_wrapper_boundary_fixed"] is True
    assert diagnosis["interpretation"]["next_recommended_phase"] == "user-confirmed-output-boundary-behavior-change"

    assert manifest["evidence_kind"] == "a100_search_query_slot_wrapper_boundary_diagnosis_local"
    assert manifest["source_prior_phase"] == source_dir.as_posix()
    assert manifest["counts"]["prediction_count"] == 3
    assert manifest["counts"]["markdown_wrapped_predictions"] == 3
    assert manifest["counts"]["validated_output_schema_valid"] == 0
    assert manifest["diagnostic_artifacts"]["diagnosis"].endswith("wrapper_boundary_diagnosis.json")
    assert manifest["diagnostic_artifacts"]["report"].endswith("wrapper_boundary_diagnosis.md")
    assert manifest["source_artifacts"]["source_diagnosis"].endswith("slot_policy_rerun_diagnosis.json")
    assert manifest["source_artifact_policy"] == diagnosis["source_artifact_policy"]
    assert manifest["claims"] == diagnosis["claims"]

    assert diagnosis["claims"]["local_diagnosis_only"] is True
    assert diagnosis["claims"]["a100_execution_performed"] is False
    assert diagnosis["claims"]["training_or_prediction_rerun_performed"] is False
    assert diagnosis["claims"]["decoding_change_performed"] is False
    assert diagnosis["claims"]["parser_relaxation_performed"] is False
    assert diagnosis["claims"]["slot_normalization_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    if archive_dir.exists():
        assert post_archive_leak_scan is not None
        assert post_archive_leak_scan["ok"] is True
        assert post_archive_leak_scan["findings"] == []
        assert final_leak_scan is not None
        assert final_leak_scan["ok"] is True
        assert final_leak_scan["findings"] == []
    assert len(generation_trace_rows) == 6
    assert "local evidence-only diagnosis" in report
    assert "wrapper origin remains unproven" in report
    assert "不启动新的 A100" in human_brief
    assert "不能声明模型质量改善" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert "private-configs" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_retry_decoding_stop_boundary_diagnosis_pack_is_public_safe_and_bounded() -> None:
    source_dir = Path("reports/public-sample/a100-schema-retry-wrapper-boundary-rerun")
    evidence_dir = Path("reports/public-sample/retry-decoding-stop-boundary-diagnosis")
    human_brief_path = Path("docs/human-briefs/2026-06-06-diagnose-retry-decoding-stop-boundary.html")
    change_dirs = [
        Path("openspec/changes/diagnose-retry-decoding-stop-boundary"),
        Path("openspec/changes/archive/2026-06-06-diagnose-retry-decoding-stop-boundary"),
    ]
    required_files = {
        "decoding_stop_boundary_diagnosis.json",
        "decoding_stop_boundary_diagnosis.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    diagnosis = json.loads((evidence_dir / "decoding_stop_boundary_diagnosis.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "decoding_stop_boundary_diagnosis.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    source_diagnosis = json.loads(
        (source_dir / "schema_retry_wrapper_boundary_diagnosis.json").read_text(encoding="utf-8")
    )
    generation_trace_rows = [
        json.loads(line)
        for line in (source_dir / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    serialized = "\n".join(
        [
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            human_brief,
        ]
    )

    assert diagnosis["evidence_kind"] == "retry_decoding_stop_boundary_diagnosis_local"
    assert diagnosis["diagnostic_kind"] == "retry_decoding_stop_boundary_diagnosis"
    assert diagnosis["source_prior_phase"] == source_dir.as_posix()
    assert diagnosis["source_artifacts"]["source_diagnosis"].endswith(
        "schema_retry_wrapper_boundary_diagnosis.json"
    )
    assert diagnosis["source_artifact_policy"]["uses_prior_public_sample_artifacts_only"] is True
    assert diagnosis["source_artifact_policy"]["source_predictions_preserved"] is True
    assert diagnosis["source_artifact_policy"]["source_metrics_preserved"] is True
    assert diagnosis["source_artifact_policy"]["no_private_raw_logs_or_adapters_read"] is True

    summary = diagnosis["summary"]
    assert summary["prediction_count"] == 3
    assert summary["row_ids"] == expected_row_ids
    assert summary["strict_final_json_valid_rate"] == source_diagnosis["summary"]["strict_final_json_valid_rate"] == 0
    assert summary["strict_final_contract_exact_match"] == 0
    assert summary["validated_output_schema_valid_count"] == 0
    assert summary["raw_json_object_count"] == 3
    assert summary["raw_missing_task_type_count"] == 3
    assert summary["retry_prose_markdown_wrapper_count"] == 3
    assert summary["retry_markdown_fence_visible_count"] == 3
    assert summary["retry_forbidden_preface_visible_count"] == 2
    assert summary["retry_trailing_analysis_visible_count"] == 3
    assert summary["retry_task_type_search_visible_count"] == 3
    assert summary["retry_parse_status_counts"] == {"json_fragment_object": 3}
    assert summary["raw_parse_status_counts"] == {"json_object": 3}
    assert summary["raw_generation_trace_available"] is True
    assert summary["retry_generation_trace_available"] is False
    assert summary["raw_generation_finish_state_counts"] == {"eos_observed": 3}
    assert summary["raw_generation_eos_seen_count"] == 3
    assert summary["raw_generation_generated_token_count_min"] == 52
    assert summary["raw_generation_generated_token_count_max"] == 54
    assert summary["raw_generation_max_new_tokens"] == 256
    assert summary["raw_generation_max_new_tokens_hit_count"] == 0
    assert summary["raw_generation_token_counts_below_max_count"] == 3
    assert all(row["finish_state"] == "eos_observed" for row in generation_trace_rows)
    assert all(row["generated_token_count"] < row["max_new_tokens"] for row in generation_trace_rows)

    assert [row["row_id"] for row in diagnosis["rows"]] == expected_row_ids
    assert all(row["raw_generation"]["trace_available"] is True for row in diagnosis["rows"])
    assert all(row["raw_generation"]["max_new_tokens_hit"] is False for row in diagnosis["rows"])
    assert all(row["retry_attempt"]["generation_trace_available"] is False for row in diagnosis["rows"])
    assert all(row["retry_attempt"]["parse_status"] == "json_fragment_object" for row in diagnosis["rows"])
    assert all(row["retry_attempt"]["markdown_fence_visible"] is True for row in diagnosis["rows"])

    assert diagnosis["evidence_gaps"]["retry_generation_trace_missing"] is True
    assert diagnosis["evidence_gaps"]["raw_trace_must_not_be_used_for_retry_stop_claim"] is True
    assert diagnosis["evidence_gaps"]["retry_eos_or_stop_token_behavior_unproven"] is True
    assert diagnosis["evidence_gaps"]["retry_generated_token_count_unproven"] is True
    assert diagnosis["evidence_gaps"]["retry_generation_trace_missing_fields"] == [
        "retry_generated_token_count",
        "retry_max_new_tokens",
        "retry_eos_token_seen",
        "retry_finish_state",
        "retry_stop_reason",
    ]
    assert diagnosis["interpretation"]["raw_generation_max_token_truncation_likely"] is False
    assert diagnosis["interpretation"]["raw_generation_stop_boundary_observed"] is True
    assert diagnosis["interpretation"]["retry_stop_boundary_cause_proven"] is False
    assert diagnosis["interpretation"]["retry_wrapper_is_observed_model_output_not_parser_behavior"] is True
    assert diagnosis["interpretation"]["instruction_following_explanatory_style_hypothesis"] is True
    assert diagnosis["interpretation"]["parser_relaxation_recommended"] is False
    assert diagnosis["interpretation"]["prediction_repair_recommended"] is False
    assert diagnosis["interpretation"]["next_recommended_phase"] == (
        "instrument-retry-generation-trace-before-changing-decoding-behavior"
    )

    assert manifest["evidence_kind"] == diagnosis["evidence_kind"]
    assert manifest["source_prior_phase"] == source_dir.as_posix()
    assert manifest["counts"]["raw_generation_trace_rows"] == 3
    assert manifest["counts"]["retry_generation_trace_rows"] == 0
    assert manifest["counts"]["raw_generation_eos_seen_count"] == 3
    assert manifest["counts"]["raw_generation_max_new_tokens_hit_count"] == 0
    assert manifest["counts"]["retry_prose_markdown_wrapper_count"] == 3
    assert manifest["diagnostic_artifacts"]["diagnosis"].endswith("decoding_stop_boundary_diagnosis.json")
    assert manifest["diagnostic_artifacts"]["report"].endswith("decoding_stop_boundary_diagnosis.md")
    assert manifest["diagnostic_artifacts"]["human_brief"] == human_brief_path.as_posix()
    assert manifest["evidence_gaps"] == diagnosis["evidence_gaps"]
    assert manifest["claims"] == diagnosis["claims"]

    assert diagnosis["claims"]["local_diagnosis_only"] is True
    assert diagnosis["claims"]["a100_execution_performed"] is False
    assert diagnosis["claims"]["private_prediction_rerun_performed"] is False
    assert diagnosis["claims"]["training_or_prediction_rerun_performed"] is False
    assert diagnosis["claims"]["decoding_change_performed"] is False
    assert diagnosis["claims"]["parser_relaxation_performed"] is False
    assert diagnosis["claims"]["evaluator_metric_change_performed"] is False
    assert diagnosis["claims"]["schema_repair_or_coercion_applied"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["slot_normalization_performed"] is False
    assert diagnosis["claims"]["checkpoint_release"] is False
    assert diagnosis["claims"]["adapter_release"] is False
    assert diagnosis["claims"]["model_recovery_claim"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False
    assert diagnosis["claims"]["live_browser_benchmark_improvement_claim"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "raw generation reached EOS before the 256 token limit" in report
    assert "Retry generation trace 缺失" in human_brief
    assert "不能把 raw EOS 证据外推成 retry stop-boundary 结论" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_retry_generation_trace_instrumentation_pack_is_public_safe_and_bounded() -> None:
    evidence_dir = Path("reports/public-sample/retry-generation-trace-instrumentation")
    human_brief_path = Path("docs/human-briefs/2026-06-06-instrument-retry-generation-trace.html")
    change_dirs = [
        Path("openspec/changes/instrument-retry-generation-trace"),
        Path("openspec/changes/archive/2026-06-06-instrument-retry-generation-trace"),
    ]
    required_files = {
        "instrumentation_summary.json",
        "instrumentation_summary.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    summary = json.loads((evidence_dir / "instrumentation_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "instrumentation_summary.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    serialized = "\n".join(
        [
            json.dumps(summary, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            human_brief,
        ]
    )

    assert summary["evidence_kind"] == "retry_generation_trace_instrumentation_local"
    assert summary["instrumentation_kind"] == "retry_attempt_generation_trace_sidecar"
    assert summary["project_stage_target"] == "first-phase speech-to-contract normalization"
    assert summary["source_artifacts"]["prior_retry_stop_boundary_diagnosis"].endswith(
        "decoding_stop_boundary_diagnosis.json"
    )
    assert summary["source_artifacts"]["prior_a100_generation_trace"].endswith("generation_trace.jsonl")
    assert summary["source_artifacts"]["training_code"] == "src/voice2task/training.py"
    assert summary["code_change"]["generation_trace_attempt_field_added"] is True
    assert summary["code_change"]["raw_attempt_trace_rows_labelled"] is True
    assert summary["code_change"]["retry_attempt_trace_rows_added_when_retry_attempted"] is True
    assert summary["code_change"]["trace_sidecar_path_unchanged"] == "generation_trace.jsonl"
    assert summary["code_change"]["new_trace_row_field"] == "attempt"
    assert summary["code_change"]["allowed_attempt_values"] == ["raw_attempt", "retry_attempt"]
    assert "generated_token_count" in summary["code_change"]["trace_row_fields_preserved"]
    assert "finish_state" in summary["code_change"]["trace_row_fields_preserved"]
    assert summary["tdd_evidence"]["red_test_observed"] is True
    assert summary["tdd_evidence"]["green_test_observed"] is True
    assert summary["tdd_evidence"]["adjacent_retry_sidecar_tests_passed"] is True
    assert summary["historical_boundary"]["prior_a100_trace_rewritten"] is False
    assert summary["historical_boundary"]["prior_a100_retry_trace_available_after_this_phase"] is False
    assert summary["historical_boundary"][
        "future_a100_or_private_adapter_rerun_required_to_observe_real_retry_stop_boundary"
    ] is True
    assert summary["historical_boundary"]["historical_a100_metrics_reinterpreted"] is False
    assert summary["preservation"]["retry_prompt_text_changed"] is False
    assert summary["preservation"]["decoding_parameters_changed"] is False
    assert summary["preservation"]["strict_parser_semantics_changed"] is False
    assert summary["preservation"]["schema_guard_source_selection_changed"] is False
    assert summary["preservation"]["final_prediction_selection_changed"] is False
    assert summary["preservation"]["evaluator_metrics_changed"] is False

    assert manifest["evidence_kind"] == summary["evidence_kind"]
    assert manifest["counts"] == {
        "allowed_attempt_values": 2,
        "focused_tests_added": 1,
        "new_trace_row_fields": 1,
    }
    assert manifest["historical_boundary"] == summary["historical_boundary"]
    assert manifest["claims"] == summary["claims"]
    assert summary["claims"]["local_instrumentation_only"] is True
    assert summary["claims"]["a100_execution_performed"] is False
    assert summary["claims"]["private_prediction_rerun_performed"] is False
    assert summary["claims"]["training_or_prediction_rerun_performed"] is False
    assert summary["claims"]["decoding_change_performed"] is False
    assert summary["claims"]["retry_prompt_changed"] is False
    assert summary["claims"]["parser_relaxation_performed"] is False
    assert summary["claims"]["evaluator_metric_change_performed"] is False
    assert summary["claims"]["prediction_repair_or_rescore_performed"] is False
    assert summary["claims"]["semantic_equivalence_scoring_performed"] is False
    assert summary["claims"]["slot_normalization_performed"] is False
    assert summary["claims"]["checkpoint_release"] is False
    assert summary["claims"]["adapter_release"] is False
    assert summary["claims"]["model_recovery_claim"] is False
    assert summary["claims"]["model_quality_improvement_claim"] is False
    assert summary["claims"]["live_browser_benchmark_improvement_claim"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "attempt-level `generation_trace.jsonl` rows" in report
    assert "历史 A100" in human_brief
    assert "不会被 retroactively 改写" in human_brief
    assert "first-phase speech-to-contract normalization" in human_brief
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert "private-overrides" not in serialized
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_confirmation_rerun_row_mismatch_diagnosis_pack_is_public_safe_and_bounded() -> None:
    prior_dir = Path("reports/public-sample/a100-confirmation-required-train-split-rerun")
    evidence_dir = Path("reports/public-sample/confirmation-rerun-row-mismatch-diagnosis")
    required_files = {
        "row_mismatch_diagnosis.json",
        "row_mismatch_diagnosis.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
    }
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}

    diagnosis = json.loads((evidence_dir / "row_mismatch_diagnosis.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    markdown = (evidence_dir / "row_mismatch_diagnosis.md").read_text(encoding="utf-8")
    prior_metrics = json.loads((prior_dir / "metrics.json").read_text(encoding="utf-8"))
    serialized = (
        json.dumps(diagnosis, ensure_ascii=False, sort_keys=True)
        + json.dumps(manifest, ensure_ascii=False, sort_keys=True)
        + json.dumps(leak_scan, ensure_ascii=False, sort_keys=True)
        + json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True)
        + json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True)
        + json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True)
        + markdown
    )

    assert diagnosis["diagnostic_kind"] == "confirmation_required_rerun_row_mismatch_diagnosis"
    assert diagnosis["summary"]["gold_row_count"] == 3
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["row_mismatch_count"] == 3
    assert diagnosis["summary"]["schema_invalid_prediction_count"] == 1
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == prior_metrics["metrics"]["json_valid_rate"] == 2 / 3
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == (
        prior_metrics["metrics"]["contract_exact_match"]
    ) == 0.0
    assert diagnosis["summary"]["strict_final_task_type_accuracy"] == prior_metrics["metrics"]["task_type_accuracy"]
    assert diagnosis["summary"]["strict_final_route_accuracy"] == prior_metrics["metrics"]["route_accuracy"]
    assert diagnosis["summary"]["strict_final_confirmation_accuracy"] == (
        prior_metrics["metrics"]["confirmation_accuracy"]
    )
    assert diagnosis["summary"]["strict_final_slot_f1"] == prior_metrics["metrics"]["slot_f1"]
    assert diagnosis["summary"]["field_mismatch_counts"] == {
        "confirmation_required": 1,
        "normalized_command": 3,
        "route": 1,
        "safety.reason": 1,
        "task_type": 1,
    }
    assert diagnosis["summary"]["mismatch_category_counts"] == {
        "missing_prediction_field": 1,
        "value_mismatch": 6,
    }
    assert diagnosis["summary"]["family_counts"] == {
        "missing_required_field_schema_failure": 1,
        "semantic_task_route_safety_mismatch": 1,
        "strict_string_field_exact_match_mismatch": 1,
    }
    row_families = {row["row_id"]: row["primary_failure_family"] for row in diagnosis["rows"]}
    assert row_families == {
        "seed-search-weather": "missing_required_field_schema_failure",
        "seed-search-weather-aug-1": "semantic_task_route_safety_mismatch",
        "seed-search-weather-aug-2": "strict_string_field_exact_match_mismatch",
    }
    assert [row["row_id"] for row in diagnosis["rows"]] == expected_row_ids
    assert diagnosis["claims"]["local_evidence_only_analysis"] is True
    assert diagnosis["claims"]["does_not_repair_normalize_coerce_replace_or_rescore"] is True
    assert diagnosis["claims"]["held_out_generalization_claim"] is False
    assert diagnosis["claims"]["checkpoint_release"] is False
    assert diagnosis["claims"]["adapter_release"] is False
    assert diagnosis["claims"]["production_readiness_claim"] is False
    assert diagnosis["claims"]["public_full_corpus_release_claim"] is False
    assert diagnosis["claims"]["live_browser_benchmark_improvement_claim"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False
    assert manifest["evidence_kind"] == "confirmation_rerun_row_mismatch_diagnosis"
    assert manifest["source_prior_phase"] == "reports/public-sample/a100-confirmation-required-train-split-rerun"
    assert manifest["source_artifact_policy"]["uses_prior_public_sample_artifacts_only"] is True
    assert manifest["source_artifact_policy"]["a100_execution_performed"] is False
    assert manifest["source_artifact_policy"]["prediction_rerun_performed"] is False
    assert manifest["source_artifact_policy"]["training_or_decoding_changed"] is False
    assert manifest["metrics_preserved"]["json_valid_rate"] == 2 / 3
    assert manifest["metrics_preserved"]["contract_exact_match"] == 0.0
    assert manifest["metrics_preserved"]["task_type_accuracy"] == prior_metrics["metrics"]["task_type_accuracy"]
    assert manifest["metrics_preserved"]["route_accuracy"] == prior_metrics["metrics"]["route_accuracy"]
    assert manifest["metrics_preserved"]["confirmation_accuracy"] == prior_metrics["metrics"]["confirmation_accuracy"]
    assert manifest["metrics_preserved"]["slot_f1"] == prior_metrics["metrics"]["slot_f1"]
    assert manifest["claims"]["local_evidence_only_analysis"] is True
    assert manifest["claims"]["model_quality_improvement_claim"] is False
    assert manifest["diagnostic_artifacts"]["phase_validation_leak_scan"].endswith(
        "phase_validation_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["post_archive_leak_scan"].endswith(
        "post_archive_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["final_leak_scan"].endswith("final_leak_scan_result.json")
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "local evidence-only analysis" in markdown
    assert "does not repair, normalize, coerce, replace, or re-score predictions" in markdown
    assert "contract_exact_match remains `0.0`" in markdown
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized
    assert "volcano" not in serialized
    assert scan_paths([evidence_dir]).ok is True


def test_sft_prediction_metadata_uses_configured_max_new_tokens(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_prediction_config(tmp_path)
    config_payload = json.loads(config.read_text(encoding="utf-8"))
    config_payload["max_new_tokens"] = 96
    config.write_text(json.dumps(config_payload), encoding="utf-8")

    metadata = run_sft_prediction_export(
        config,
        manifest,
        tmp_path / "predictions.jsonl",
        dry_run=True,
        fixture_mode=False,
    )

    assert metadata["decoding_policy"]["strategy"] == "greedy"
    assert metadata["decoding_policy"]["do_sample"] is False
    assert metadata["decoding_policy"]["max_new_tokens"] == 96
    assert metadata["decoding_policy"]["raw_decoded_sidecar_written"] is False
    assert metadata["decoding_policy"]["schema_repair_applied"] is False


def test_prediction_metadata_sanitizes_private_sidecar_paths(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    private_output = Path("/private/var/folders/voice2task/predictions.jsonl")
    config = _write_prediction_config(tmp_path, output_root="/private/var/folders/voice2task")

    metadata = run_sft_prediction_export(config, manifest, private_output, dry_run=True, fixture_mode=False)

    serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    assert "/private/" not in serialized
    assert metadata["prediction_output_path"] == "<a100_prediction_output>"
    assert metadata["sidecars"]["prompt_snapshot"] == "<a100_prompt_snapshot>"
    assert metadata["metadata_path"] == "<a100_prediction_metadata>"


def test_sft_prediction_fixture_mode_writes_public_safe_predictions(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_prediction_config(tmp_path)
    output = tmp_path / "trained_predictions.jsonl"

    metadata = run_sft_prediction_export(config, manifest, output, dry_run=False, fixture_mode=True)

    assert metadata["prediction_status"] == "fixture_predictions_written"
    assert metadata["prediction_source_kind"] == "public_sample_contract_fixture"
    assert metadata["prediction_count"] == 2
    assert metadata["dataset_manifest_id"] == "public-sample-test"
    assert metadata["release_status"] == "not_released"
    predictions = load_predictions(output)
    assert predictions["sft-test-1"]["route"] == "search_web"
    assert scan_paths([output]).ok is True
    output_text = output.read_text(encoding="utf-8")
    assert A100_PROJECT_ROOT not in output_text
    assert "/Users/" not in output_text


def test_train_split_overfit_diagnostic_config_is_public_safe_and_bounded() -> None:
    config_path = Path("configs/sft-a100-train-split-overfit-diagnostic.json")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    serialized = json.dumps(config, ensure_ascii=False, sort_keys=True)

    assert config["prediction_split"] == "train"
    assert config["overfit_diagnostic"] is True
    assert config["generalization_claim"] is False
    assert config["private_override_required"] is True
    assert "<a100_project_root>" in serialized
    assert "private override" in " ".join(config["private_override_requirements"]).lower()
    assert "/mnt/data/" not in serialized
    assert "/Users/" not in serialized


def test_sft_prediction_fixture_mode_writes_sidecars_and_metadata_links(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_prediction_config(tmp_path)
    config_payload = json.loads(config.read_text(encoding="utf-8"))
    config_payload["prediction_split"] = "train"
    config_payload["overfit_diagnostic"] = True
    config_payload["generalization_claim"] = False
    config.write_text(json.dumps(config_payload), encoding="utf-8")
    output = tmp_path / "trained_predictions.jsonl"

    metadata = run_sft_prediction_export(config, manifest, output, dry_run=False, fixture_mode=True)

    predictions_before = load_predictions(output)
    sidecars = metadata["sidecars"]
    prompt_snapshot = tmp_path / "prompt_snapshot.json"
    raw_summary = tmp_path / "raw_decoded_summary.jsonl"
    generation_trace = tmp_path / "generation_trace.jsonl"
    metadata_path = tmp_path / "prediction_metadata.json"
    assert sidecars == {
        "prompt_snapshot": "<a100_prompt_snapshot>",
        "raw_decoded_summary": "<a100_raw_decoded_summary>",
        "generation_trace": "<a100_generation_trace>",
    }
    assert metadata["metadata_path"] == "<a100_prediction_metadata>"
    assert json.loads(metadata_path.read_text(encoding="utf-8"))["sidecars"] == sidecars
    assert metadata["diagnostic_artifacts"] == {
        "objective_inspection": "<a100_objective_inspection>",
        "leak_scan": "<a100_leak_scan_result>",
    }
    assert metadata["prediction_split"] == "train"
    assert metadata["overfit_diagnostic"] is True
    assert metadata["generalization_claim"] is False
    assert metadata["decoding_policy"]["raw_decoded_sidecar_written"] is True
    assert metadata["decoding_policy"]["generation_trace_sidecar_written"] is True
    assert metadata["retry_prompt_constraints"]["no_prefix_suffix_text_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_here_is_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_trailing_analysis_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_second_json_object_visible"] is True
    assert metadata["retry_prompt_constraints"]["exact_json_only_output_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_text_outside_root_json_object_visible"] is True
    assert metadata["retry_prompt_constraints"]["no_natural_language_wrapper_or_preamble_visible"] is True
    assert metadata["retry_prompt_constraints"]["machine_readable_only_retry_response_visible"] is True
    assert metadata["retry_prompt_constraints"]["strict_parser_rejection_warning_visible"] is True
    assert metadata["prediction_output_boundary"]["exact_json_only_output_visible"] is True
    assert metadata["prediction_output_boundary"]["no_text_outside_root_json_object_visible"] is True
    assert metadata["prediction_output_boundary"]["strict_whole_object_parser_boundary_visible"] is True
    assert metadata["prediction_output_boundary"]["no_prefix_suffix_text_visible"] is True
    assert metadata["prediction_output_boundary"]["no_trailing_analysis_visible"] is True
    assert metadata["prediction_output_boundary"]["no_second_json_object_visible"] is True

    prompt_payload = json.loads(prompt_snapshot.read_text(encoding="utf-8"))
    raw_rows = [json.loads(line) for line in raw_summary.read_text(encoding="utf-8").splitlines()]
    trace_rows = [json.loads(line) for line in generation_trace.read_text(encoding="utf-8").splitlines()]
    assert prompt_payload["retry_prompt_constraints"] == metadata["retry_prompt_constraints"]
    assert prompt_payload["prediction_output_boundary"] == metadata["prediction_output_boundary"]
    assert [row["id"] for row in prompt_payload["rows"]] == ["sft-train-1"]
    assert [row["id"] for row in raw_rows] == ["sft-train-1"]
    assert [row["id"] for row in trace_rows] == ["sft-train-1"]
    assert raw_rows[0]["parse_status"] == "json_object"
    assert raw_rows[0]["schema_repair_applied"] is False
    assert trace_rows[0]["prediction_source_kind"] == "public_sample_contract_fixture"
    assert trace_rows[0]["generated_token_count"] == 0
    assert load_predictions(output) == predictions_before
    assert scan_paths([prompt_snapshot, raw_summary, generation_trace, metadata_path]).ok is True


def test_sft_prediction_metadata_sanitizes_private_a100_paths(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    private_config = tmp_path / "private-config.json"
    private_config.write_text(
        json.dumps(
            {
                "base_model": "/mnt/data/" + "minghongsun/voice2task-post-training/models/model",
                "base_model_public_id": "Qwen/Qwen2.5-0.5B-Instruct",
                "model_source": "modelscope",
                "allow_private_prediction": True,
                "adapter_path": "/mnt/data/" + "minghongsun/voice2task-post-training/runs/run/adapter",
                "prediction_split": "all",
            }
        ),
        encoding="utf-8",
    )
    private_output = Path("/mnt/data/" + "minghongsun/voice2task-post-training/evidence/predictions.jsonl")

    metadata = run_sft_prediction_export(private_config, manifest, private_output, dry_run=True, fixture_mode=False)
    metadata_text = json.dumps(metadata, ensure_ascii=False, sort_keys=True)

    assert "Qwen/Qwen2.5-0.5B-Instruct" in metadata_text
    assert "/mnt/data/" not in metadata_text
    assert metadata["prediction_output_path"] == "<a100_prediction_output>"
    assert metadata["command_summary"]["config"] == "<private_prediction_config>"


def test_sft_prediction_metadata_sanitizes_private_base_model_without_public_id(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    private_config = tmp_path / "private-config.json"
    private_config.write_text(
        json.dumps(
            {
                "base_model": "/mnt/data/" + "minghongsun/voice2task-post-training/models/model",
                "model_source": "modelscope",
                "allow_private_prediction": True,
                "adapter_path": "/mnt/data/" + "minghongsun/voice2task-post-training/runs/run/adapter",
                "prediction_split": "all",
            }
        ),
        encoding="utf-8",
    )

    metadata = run_sft_prediction_export(private_config, manifest, tmp_path / "predictions.jsonl", dry_run=True)
    metadata_text = json.dumps(metadata, ensure_ascii=False, sort_keys=True)

    assert metadata["base_model"] == "<private_base_model>"
    assert "/mnt/data/" not in metadata_text


class _FakeInputIds:
    shape = (1, 0)


class _FakeInputs(dict[str, Any]):
    def to(self, device: str) -> "_FakeInputs":
        return self


class _FakeTokenizer:
    eos_token_id = 0

    def __call__(self, prompt: str, *, return_tensors: str) -> _FakeInputs:
        return _FakeInputs({"input_ids": _FakeInputIds()})

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        return "<chat-prompt>"

    def decode(self, new_tokens: list[int], *, skip_special_tokens: bool) -> str:
        return "模型输出不是 JSON，但需要保留为失败证据 /mnt/data/minghongsun/private/model"


class _FakeJsonPathTokenizer(_FakeTokenizer):
    def decode(self, new_tokens: list[int], *, skip_special_tokens: bool) -> str:
        return json.dumps(
            {
                "task_type": "search",
                "route": "search_web",
                "safety": {"allow": True, "reason": "read from /mnt/data/minghongsun/private/run"},
                "confirmation_required": False,
                "slots": {"query": "机票"},
                "normalized_command": "搜索机票",
                "language": "zh-CN",
                "contract_version": "v1",
            },
            ensure_ascii=False,
        )


class _FakeRetryTokenizer(_FakeTokenizer):
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.decode_calls = 0

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        rendered = "\n".join(f"{message['role']}: {message['content']}" for message in messages)
        if add_generation_prompt:
            rendered += "\nassistant:"
        return rendered

    def __call__(self, prompt: str, *, return_tensors: str) -> _FakeInputs:
        self.prompts.append(prompt)
        return _FakeInputs({"input_ids": _FakeInputIds()})

    def decode(self, new_tokens: list[int], *, skip_special_tokens: bool) -> str:
        self.decode_calls += 1
        if self.decode_calls == 1:
            return json.dumps(
                {
                    "task_type": "search",
                    "route": "search_web",
                    "confirmation_required": False,
                    "slots": {"query": "机票"},
                    "language": "zh-CN",
                },
                ensure_ascii=False,
            )
        return json.dumps(_contract("机票"), ensure_ascii=False)


class _FakeRetryTemplateTokenizer(_FakeRetryTokenizer):
    def __init__(self) -> None:
        super().__init__()
        self.template_calls: list[dict[str, Any]] = []

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        self.template_calls.append(
            {
                "messages": messages,
                "tokenize": tokenize,
                "add_generation_prompt": add_generation_prompt,
            }
        )
        rendered = "\n".join(f"{message['role']}: {message['content']}" for message in messages)
        if add_generation_prompt:
            rendered += "\nassistant:"
        return rendered


class _FakeMarkdownRetryTokenizer(_FakeTokenizer):
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.decode_calls = 0

    def __call__(self, prompt: str, *, return_tensors: str) -> _FakeInputs:
        self.prompts.append(prompt)
        return _FakeInputs({"input_ids": _FakeInputIds()})

    def decode(self, new_tokens: list[int], *, skip_special_tokens: bool) -> str:
        self.decode_calls += 1
        if self.decode_calls == 1:
            return json.dumps(
                {
                    "task_type": "search",
                    "route": "search_web",
                    "confirmation_required": False,
                    "slots": {"query": "机票"},
                    "language": "zh-CN",
                },
                ensure_ascii=False,
            )
        return (
            "这是修复后的 JSON：\n\n```json\n"
            + json.dumps(_contract("机票"), ensure_ascii=False, sort_keys=True)
            + "\n```\n请检查。"
        )


class _FakeMarkdownRawTokenizer(_FakeTokenizer):
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.decode_calls = 0

    def __call__(self, prompt: str, *, return_tensors: str) -> _FakeInputs:
        self.prompts.append(prompt)
        return _FakeInputs({"input_ids": _FakeInputIds()})

    def decode(self, new_tokens: list[int], *, skip_special_tokens: bool) -> str:
        self.decode_calls += 1
        return (
            "这是 first-pass JSON：\n\n```json\n"
            + json.dumps(_contract("机票"), ensure_ascii=False, sort_keys=True)
            + "\n```\n请检查。"
        )


class _FakeValidTokenizer(_FakeTokenizer):
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.decode_calls = 0

    def __call__(self, prompt: str, *, return_tensors: str) -> _FakeInputs:
        self.prompts.append(prompt)
        return _FakeInputs({"input_ids": _FakeInputIds()})

    def decode(self, new_tokens: list[int], *, skip_special_tokens: bool) -> str:
        self.decode_calls += 1
        return json.dumps(_contract("机票"), ensure_ascii=False)


class _FakeModel:
    device = "cpu"

    def eval(self) -> None:
        return None

    def generate(self, **kwargs: Any) -> list[list[int]]:
        return [[101, 102]]


class _FakeNoGrad:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def test_generation_trace_row_records_stop_boundary_evidence_without_actual_stop_reason() -> None:
    eos_row = training._generation_trace_row(
        row_id="sft-test-1",
        attempt="raw_attempt",
        prediction_source_kind="private_a100_adapter",
        generated_tokens=[101, 0],
        max_new_tokens=256,
        eos_token_id=0,
    )
    below_max_row = training._generation_trace_row(
        row_id="sft-test-2",
        attempt="retry_attempt",
        prediction_source_kind="private_a100_adapter",
        generated_tokens=[101, 102],
        max_new_tokens=256,
        eos_token_id=0,
    )
    max_hit_row = training._generation_trace_row(
        row_id="sft-test-3",
        attempt="retry_attempt",
        prediction_source_kind="private_a100_adapter",
        generated_tokens=[101, 102],
        max_new_tokens=2,
        eos_token_id=0,
    )

    assert eos_row["finish_state"] == "eos_observed"
    assert eos_row["max_new_tokens_hit"] is False
    assert eos_row["finish_state_basis"] == "tokenizer_eos_membership"
    assert eos_row["stop_reason_evidence"] == "tokenizer_eos_observed"
    assert eos_row["actual_stop_reason_recorded"] is False
    assert eos_row["actual_stop_reason"] is None

    assert below_max_row["finish_state"] == "no_eos_observed"
    assert below_max_row["max_new_tokens_hit"] is False
    assert below_max_row["finish_state_basis"] == "tokenizer_eos_membership"
    assert below_max_row["stop_reason_evidence"] == "not_recorded_below_max_without_tokenizer_eos"
    assert below_max_row["actual_stop_reason_recorded"] is False
    assert below_max_row["actual_stop_reason"] is None

    assert max_hit_row["finish_state"] == "no_eos_observed"
    assert max_hit_row["max_new_tokens_hit"] is True
    assert max_hit_row["finish_state_basis"] == "tokenizer_eos_membership"
    assert max_hit_row["stop_reason_evidence"] == "max_new_tokens_reached_without_tokenizer_eos"
    assert max_hit_row["actual_stop_reason_recorded"] is False
    assert max_hit_row["actual_stop_reason"] is None


def test_real_sft_prediction_preserves_non_json_decoded_output(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "trained_predictions.jsonl"
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    torch_module = types.ModuleType("torch")
    torch_module.float16 = "float16"
    torch_module.float32 = "float32"
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.no_grad = lambda: _FakeNoGrad()
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(from_pretrained=lambda model, adapter_path: model)
    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: _FakeTokenizer())
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeModel()
    )
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    count = training._run_real_sft_prediction(
        {"base_model": "Qwen/Qwen2.5-0.5B-Instruct", "adapter_path": (tmp_path / "adapter").as_posix()},
        [row],
        output,
    )

    record = json.loads(output.read_text(encoding="utf-8"))
    result = evaluate_predictions([row], load_predictions(output))

    assert count == 1
    assert record["prediction"] == "模型输出不是 JSON，但需要保留为失败证据 <private_path>"
    assert "/mnt/data/" not in json.dumps(record, ensure_ascii=False)
    assert result.metrics["json_valid_rate"] == 0.0
    assert result.failure_slices["schema"]["count"] == 1


def test_real_sft_prediction_sidecars_summarize_sanitized_decoded_and_generation_trace(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "trained_predictions.jsonl"
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    torch_module = types.ModuleType("torch")
    torch_module.float16 = "float16"
    torch_module.float32 = "float32"
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.no_grad = lambda: _FakeNoGrad()
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(from_pretrained=lambda model, adapter_path: model)
    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: _FakeTokenizer())
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeModel()
    )
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    count = training._run_real_sft_prediction(
        {"base_model": "Qwen/Qwen2.5-0.5B-Instruct", "adapter_path": (tmp_path / "adapter").as_posix()},
        [row],
        output,
        sidecar_paths={
            "prompt_snapshot": tmp_path / "prompt_snapshot.json",
            "raw_decoded_summary": tmp_path / "raw_decoded_summary.jsonl",
            "generation_trace": tmp_path / "generation_trace.jsonl",
        },
    )

    raw_rows = [
        json.loads(line)
        for line in (tmp_path / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    prompt_payload = json.loads((tmp_path / "prompt_snapshot.json").read_text(encoding="utf-8"))

    assert count == 1
    assert raw_rows[0]["parse_status"] == "non_json"
    assert raw_rows[0]["decoded_prefix"].endswith("<private_path>")
    assert raw_rows[0]["decoded_suffix"].endswith("<private_path>")
    assert raw_rows[0]["private_values_sanitized"] is True
    assert trace_rows[0]["generated_token_count"] == 2
    assert trace_rows[0]["max_new_tokens"] == 256
    assert trace_rows[0]["max_new_tokens_hit"] is False
    assert trace_rows[0]["eos_token_seen"] is False
    assert trace_rows[0]["finish_state"] == "no_eos_observed"
    assert trace_rows[0]["finish_state_basis"] == "tokenizer_eos_membership"
    assert trace_rows[0]["stop_reason_evidence"] == "not_recorded_below_max_without_tokenizer_eos"
    assert trace_rows[0]["actual_stop_reason_recorded"] is False
    assert trace_rows[0]["actual_stop_reason"] is None
    assert prompt_payload["rows"][0]["id"] == "sft-test-1"
    assert "/mnt/data/" not in json.dumps(raw_rows + trace_rows + prompt_payload["rows"], ensure_ascii=False)


def test_real_sft_prediction_generation_trace_records_retry_attempt(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "trained_predictions.jsonl"
    tokenizer = _FakeRetryTokenizer()
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    torch_module = types.ModuleType("torch")
    torch_module.float16 = "float16"
    torch_module.float32 = "float32"
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.no_grad = lambda: _FakeNoGrad()
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(from_pretrained=lambda model, adapter_path: model)
    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer)
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeModel()
    )
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    count = training._run_real_sft_prediction(
        {
            "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
            "adapter_path": (tmp_path / "adapter").as_posix(),
            "schema_retry_enabled": True,
        },
        [row],
        output,
        sidecar_paths={
            "prompt_snapshot": tmp_path / "prompt_snapshot.json",
            "raw_decoded_summary": tmp_path / "raw_decoded_summary.jsonl",
            "generation_trace": tmp_path / "generation_trace.jsonl",
        },
    )

    record = json.loads(output.read_text(encoding="utf-8"))
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert count == 1
    assert record["schema_guard"]["retry_attempted"] is True
    assert record["schema_guard"]["validated_output_source"] == "retry_attempt"
    assert [row["attempt"] for row in trace_rows] == ["raw_attempt", "retry_attempt"]
    assert [row["id"] for row in trace_rows] == ["sft-test-1", "sft-test-1"]
    assert all(row["prediction_source_kind"] == "private_a100_adapter" for row in trace_rows)
    assert all(row["strategy"] == "greedy" for row in trace_rows)
    assert all(row["do_sample"] is False for row in trace_rows)
    assert all(row["max_new_tokens"] == 256 for row in trace_rows)
    assert all(row["generated_token_count"] == 2 for row in trace_rows)
    assert all(row["eos_token_id_available"] is True for row in trace_rows)
    assert all(row["eos_token_seen"] is False for row in trace_rows)
    assert all(row["finish_state"] == "no_eos_observed" for row in trace_rows)
    assert all(row["max_new_tokens_hit"] is False for row in trace_rows)
    assert all(row["finish_state_basis"] == "tokenizer_eos_membership" for row in trace_rows)
    assert all(row["stop_reason_evidence"] == "not_recorded_below_max_without_tokenizer_eos" for row in trace_rows)
    assert all(row["actual_stop_reason_recorded"] is False for row in trace_rows)
    assert all(row["actual_stop_reason"] is None for row in trace_rows)
    assert scan_paths([tmp_path / "generation_trace.jsonl"]).ok is True


def test_real_sft_prediction_sanitizes_private_paths_inside_json_output(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "trained_predictions.jsonl"
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    torch_module = types.ModuleType("torch")
    torch_module.float16 = "float16"
    torch_module.float32 = "float32"
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.no_grad = lambda: _FakeNoGrad()
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(from_pretrained=lambda model, adapter_path: model)
    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeJsonPathTokenizer()
    )
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeModel()
    )
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    count = training._run_real_sft_prediction(
        {"base_model": "Qwen/Qwen2.5-0.5B-Instruct", "adapter_path": (tmp_path / "adapter").as_posix()},
        [row],
        output,
    )

    record = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(record, ensure_ascii=False)

    assert count == 1
    assert record["prediction"]["safety"]["reason"] == "read from <private_path>"
    assert "/mnt/data/" not in serialized
    assert scan_paths([output]).ok is True


def test_real_sft_prediction_retries_schema_invalid_missing_required_fields(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "trained_predictions.jsonl"
    tokenizer = _FakeRetryTokenizer()
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    torch_module = types.ModuleType("torch")
    torch_module.float16 = "float16"
    torch_module.float32 = "float32"
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.no_grad = lambda: _FakeNoGrad()
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(from_pretrained=lambda model, adapter_path: model)
    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer)
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeModel()
    )
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    count = training._run_real_sft_prediction(
        {
            "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
            "adapter_path": (tmp_path / "adapter").as_posix(),
            "schema_retry_enabled": True,
        },
        [row],
        output,
        sidecar_paths={
            "prompt_snapshot": tmp_path / "prompt_snapshot.json",
            "raw_decoded_summary": tmp_path / "raw_decoded_summary.jsonl",
            "generation_trace": tmp_path / "generation_trace.jsonl",
        },
    )

    record = json.loads(output.read_text(encoding="utf-8"))
    raw_rows = [
        json.loads(line)
        for line in (tmp_path / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    result = evaluate_predictions([row], load_predictions(output))

    assert count == 1
    assert tokenizer.decode_calls == 2
    assert len(tokenizer.prompts) == 2
    assert "缺失字段" in tokenizer.prompts[1]
    assert "safety" in tokenizer.prompts[1]
    assert record["prediction"] == _contract("机票")
    assert record["schema_guard"]["raw_attempt_schema_valid"] is False
    assert record["schema_guard"]["retry_attempted"] is True
    assert record["schema_guard"]["retry_attempt_schema_valid"] is True
    assert record["schema_guard"]["validated_output_source"] == "retry_attempt"
    assert raw_rows[0]["schema_guard"]["raw_attempt_schema_valid"] is False
    assert raw_rows[0]["schema_guard"]["retry_attempted"] is True
    assert raw_rows[0]["schema_guard"]["validated_output_source"] == "retry_attempt"
    assert raw_rows[0]["raw_attempt"]["parse_status"] == "json_object"
    assert raw_rows[0]["retry_attempt"]["parse_status"] == "json_object"
    assert raw_rows[0]["retry_attempt"]["decoded_prefix"].startswith("{")
    assert result.metrics["json_valid_rate"] == 1.0
    assert scan_paths([output, tmp_path / "raw_decoded_summary.jsonl"]).ok is True


def test_schema_retry_prompt_declares_canonical_json_only_contract_shape() -> None:
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    raw_prediction = {
        "task_type": "search_web",
        "route": "/weather/query_weather_request",
        "safety": {"reason": "query_weather_request"},
    }

    prompt = training._schema_retry_prompt(row, raw_prediction, training._schema_guard_status(raw_prediction))

    assert all(task_type in prompt for task_type in sorted(TASK_TYPES))
    assert all(route in prompt for route in sorted(ROUTES))
    assert '"task_type": "search"' in prompt
    assert '"route": "search_web"' in prompt
    assert '"safety": {"allow": true, "reason": "public_readonly"}' in prompt
    assert '"confirmation_required": false' in prompt
    assert '"slots": {}' in prompt
    assert "第一个非空字符必须是 `{`" in prompt
    assert "最后一个非空字符必须是 `}`" in prompt
    assert "不要 Markdown/code fences/prose" in prompt
    assert "route 是 enum，不是 URL/path" in prompt
    assert "task_type 不能使用 search_web、open_url、query_weather_request" in prompt
    assert "只输出一个 minified JSON object" in prompt
    assert "全部 8 个顶层字段必须都在同一个 root object 内" in prompt
    assert "不要在 normalized_command 之前提前关闭 root object" in prompt
    assert "task_type 必须是 search，不能是 search_web" in prompt
    assert "不要输出任何前缀或后缀文本" in prompt
    assert "不要以“这是”或“以下”开头" in prompt
    assert "不要使用 Here is" in prompt
    assert "不要在 JSON 后添加解释、分析或用户输入复述" in prompt
    assert "不要输出第二个 JSON object" in prompt
    assert "Retry response must be exactly one JSON object and nothing else" in prompt
    assert "No text outside the root JSON object" in prompt
    assert "不要使用自然语言 wrapper/preamble" in prompt
    assert "machine-readable only retry response" in prompt
    assert "Retry template mode: machine_contract_regeneration" in prompt
    assert "not a conversational assistant answer" in prompt
    assert "assistant JSON payload only" in prompt
    assert "否则 strict parser 会拒绝 retry attempt" in prompt

    constraints = training.schema_retry_prompt_constraint_summary(prompt)
    assert constraints["exact_json_only_output_visible"] is True
    assert constraints["no_text_outside_root_json_object_visible"] is True
    assert constraints["no_natural_language_wrapper_or_preamble_visible"] is True
    assert constraints["machine_readable_only_retry_response_visible"] is True
    template_boundary = training.schema_retry_template_boundary_summary(prompt)
    assert template_boundary["retry_template_mode_visible"] is True
    assert template_boundary["machine_only_contract_regeneration_visible"] is True
    assert template_boundary["no_conversational_answer_mode_visible"] is True
    assert template_boundary["assistant_json_payload_only_visible"] is True
    assert template_boundary["strict_whole_object_parser_boundary_visible"] is True


def test_real_sft_prediction_uses_machine_only_chat_template_for_retry_prompt(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "trained_predictions.jsonl"
    tokenizer = _FakeRetryTemplateTokenizer()
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    torch_module = types.ModuleType("torch")
    torch_module.float16 = "float16"
    torch_module.float32 = "float32"
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.no_grad = lambda: _FakeNoGrad()
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(from_pretrained=lambda model, adapter_path: model)
    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer)
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeModel()
    )
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    count = training._run_real_sft_prediction(
        {
            "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
            "adapter_path": (tmp_path / "adapter").as_posix(),
            "schema_retry_enabled": True,
        },
        [row],
        output,
        sidecar_paths={
            "prompt_snapshot": tmp_path / "prompt_snapshot.json",
            "raw_decoded_summary": tmp_path / "raw_decoded_summary.jsonl",
            "generation_trace": tmp_path / "generation_trace.jsonl",
        },
    )

    metadata = training._prediction_metadata_common(
        config_path=_write_prediction_config(tmp_path),
        manifest_path=_write_manifest(tmp_path),
        output_path=tmp_path / "predictions.jsonl",
        dry_run=False,
        fixture_mode=False,
    )
    prompt_payload = json.loads((tmp_path / "prompt_snapshot.json").read_text(encoding="utf-8"))

    assert count == 1
    assert len(tokenizer.template_calls) == 2
    retry_template_call = tokenizer.template_calls[1]
    assert retry_template_call["add_generation_prompt"] is True
    assert [message["role"] for message in retry_template_call["messages"]] == ["system", "user"]
    assert "machine-only schema retry" in retry_template_call["messages"][0]["content"]
    assert "Retry template mode: machine_contract_regeneration" in retry_template_call["messages"][1]["content"]
    assert "assistant JSON payload only" in tokenizer.prompts[1]
    assert tokenizer.prompts[1].endswith("assistant:")
    assert metadata["retry_template_boundary"]["retry_prompt_uses_chat_template_boundary"] is True
    assert metadata["retry_template_boundary"]["retry_template_mode_visible"] is True
    assert prompt_payload["retry_template_boundary"] == metadata["retry_template_boundary"]


def test_real_sft_prediction_rejects_markdown_wrapped_retry_even_when_fragment_is_valid(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "trained_predictions.jsonl"
    tokenizer = _FakeMarkdownRetryTokenizer()
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    torch_module = types.ModuleType("torch")
    torch_module.float16 = "float16"
    torch_module.float32 = "float32"
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.no_grad = lambda: _FakeNoGrad()
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(from_pretrained=lambda model, adapter_path: model)
    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer)
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeModel()
    )
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    count = training._run_real_sft_prediction(
        {
            "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
            "adapter_path": (tmp_path / "adapter").as_posix(),
            "schema_retry_enabled": True,
        },
        [row],
        output,
        sidecar_paths={
            "prompt_snapshot": tmp_path / "prompt_snapshot.json",
            "raw_decoded_summary": tmp_path / "raw_decoded_summary.jsonl",
            "generation_trace": tmp_path / "generation_trace.jsonl",
        },
    )

    record = json.loads(output.read_text(encoding="utf-8"))
    raw_rows = [
        json.loads(line)
        for line in (tmp_path / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    result = evaluate_predictions([row], load_predictions(output))

    assert count == 1
    assert tokenizer.decode_calls == 2
    assert record["prediction"] != _contract("机票")
    assert record["schema_guard"]["raw_attempt_schema_valid"] is False
    assert record["schema_guard"]["retry_attempted"] is True
    assert record["schema_guard"]["retry_attempt_schema_valid"] is False
    assert record["schema_guard"]["validated_output_schema_valid"] is False
    assert record["schema_guard"]["validated_output_source"] == "none"
    assert raw_rows[0]["retry_attempt"]["parse_status"] == "json_fragment_object"
    assert raw_rows[0]["schema_guard"]["retry_attempt_schema_valid"] is False
    assert raw_rows[0]["schema_guard"]["validated_output_schema_valid"] is False
    assert result.metrics["json_valid_rate"] == 0.0


def test_real_sft_prediction_rejects_markdown_wrapped_raw_attempt_even_when_fragment_is_valid(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "trained_predictions.jsonl"
    tokenizer = _FakeMarkdownRawTokenizer()
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    torch_module = types.ModuleType("torch")
    torch_module.float16 = "float16"
    torch_module.float32 = "float32"
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.no_grad = lambda: _FakeNoGrad()
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(from_pretrained=lambda model, adapter_path: model)
    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer)
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeModel()
    )
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    count = training._run_real_sft_prediction(
        {
            "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
            "adapter_path": (tmp_path / "adapter").as_posix(),
            "schema_retry_enabled": False,
        },
        [row],
        output,
        sidecar_paths={
            "prompt_snapshot": tmp_path / "prompt_snapshot.json",
            "raw_decoded_summary": tmp_path / "raw_decoded_summary.jsonl",
            "generation_trace": tmp_path / "generation_trace.jsonl",
        },
    )

    record = json.loads(output.read_text(encoding="utf-8"))
    raw_rows = [
        json.loads(line)
        for line in (tmp_path / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    result = evaluate_predictions([row], load_predictions(output))

    assert count == 1
    assert tokenizer.decode_calls == 1
    assert record["prediction"] != _contract("机票")
    assert record["schema_guard"]["raw_attempt_schema_valid"] is False
    assert record["schema_guard"]["retry_attempted"] is False
    assert record["schema_guard"]["validated_output_schema_valid"] is False
    assert record["schema_guard"]["validated_output_source"] == "none"
    assert raw_rows[0]["raw_attempt"]["parse_status"] == "json_fragment_object"
    assert raw_rows[0]["schema_guard"]["raw_attempt_schema_valid"] is False
    assert result.metrics["json_valid_rate"] == 0.0
    assert scan_paths([output, tmp_path / "raw_decoded_summary.jsonl"]).ok is True


def test_real_sft_prediction_skips_retry_when_raw_attempt_is_valid(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "trained_predictions.jsonl"
    tokenizer = _FakeValidTokenizer()
    row = SFTDatasetRow(
        id="sft-test-1",
        split="test",
        input_text="帮我搜索机票",
        target_contract=_contract("机票"),
        provenance={"source_id": "sft-test-1", "public_safe": True},
    )
    torch_module = types.ModuleType("torch")
    torch_module.float16 = "float16"
    torch_module.float32 = "float32"
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.no_grad = lambda: _FakeNoGrad()
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(from_pretrained=lambda model, adapter_path: model)
    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer)
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda *args, **kwargs: _FakeModel()
    )
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    count = training._run_real_sft_prediction(
        {
            "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
            "adapter_path": (tmp_path / "adapter").as_posix(),
            "schema_retry_enabled": True,
        },
        [row],
        output,
    )

    record = json.loads(output.read_text(encoding="utf-8"))

    assert count == 1
    assert tokenizer.decode_calls == 1
    assert len(tokenizer.prompts) == 1
    assert record["prediction"] == _contract("机票")
    assert record["schema_guard"]["raw_attempt_schema_valid"] is True
    assert record["schema_guard"]["retry_attempted"] is False
    assert record["schema_guard"]["validated_output_schema_valid"] is True
    assert record["schema_guard"]["validated_output_source"] == "raw_attempt"


def test_extract_json_sanitizes_top_level_lists_strings_ips_and_secrets() -> None:
    private_path = "/" + "mnt/data/minghongsun/private/run"
    private_ip = "192." + "168.1.10"
    secret = "api_key=" + "abc12345secret"
    decoded_list = json.dumps([private_path, {"nested": f"http://{private_ip}"}], ensure_ascii=False)
    decoded_string = json.dumps(secret, ensure_ascii=False)

    parsed_list = training._extract_json_object(decoded_list)
    parsed_string = training._extract_json_object(decoded_string)

    assert parsed_list == ["<private_path>", {"nested": "http://<private_ip>"}]
    assert parsed_string == "<secret>"
    assert "/mnt/data/" not in json.dumps(parsed_list, ensure_ascii=False)
    assert private_ip not in json.dumps(parsed_list, ensure_ascii=False)
    assert "abc12345secret" not in str(parsed_string)


def test_sft_prediction_run_prediction_calls_private_adapter_export(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_prediction_config(tmp_path, adapter_path=(tmp_path / "adapter").as_posix())
    output = tmp_path / "trained_predictions.jsonl"
    calls: list[Path] = []

    monkeypatch.setattr(training, "_prediction_dependencies_available", lambda: True)

    def write_private_predictions(
        config: dict[str, Any],
        rows: list[Any],
        output_path: Path,
        *,
        sidecar_paths: dict[str, Path],
    ) -> int:
        calls.append(output_path)
        output_path.write_text(
            "\n".join(
                json.dumps(
                    {
                        "id": row.id,
                        "prediction": row.target_contract.to_dict(),
                        "prediction_source_kind": "private_a100_adapter",
                        "provenance": {"public_safe": True},
                    },
                    ensure_ascii=False,
                )
                for row in rows
            )
            + "\n",
            encoding="utf-8",
        )
        return len(rows)

    monkeypatch.setattr(training, "_run_real_sft_prediction", write_private_predictions)

    metadata = run_sft_prediction_export(config, manifest, output, dry_run=False, fixture_mode=False)

    assert calls == [output]
    assert metadata["prediction_status"] == "private_adapter_predictions_written"
    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert metadata["prediction_gate"]["will_run_private_prediction"] is True
    assert metadata["prediction_count"] == 2
    assert scan_paths([output]).ok is True


def test_invalid_private_adapter_predictions_remain_schema_failures(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_prediction_config(tmp_path, adapter_path=(tmp_path / "adapter").as_posix())
    output = tmp_path / "trained_predictions.jsonl"

    monkeypatch.setattr(training, "_prediction_dependencies_available", lambda: True)

    def write_invalid_private_predictions(
        config: dict[str, Any],
        rows: list[Any],
        output_path: Path,
        *,
        sidecar_paths: dict[str, Path],
    ) -> int:
        output_path.write_text(
            "\n".join(
                json.dumps(
                    {
                        "id": row.id,
                        "prediction": {"task": {"description": "generic normalization output"}},
                        "prediction_source_kind": "private_a100_adapter",
                        "provenance": {"public_safe": True},
                    },
                    ensure_ascii=False,
                )
                for row in rows
            )
            + "\n",
            encoding="utf-8",
        )
        return len(rows)

    monkeypatch.setattr(training, "_run_real_sft_prediction", write_invalid_private_predictions)

    metadata = run_sft_prediction_export(config, manifest, output, dry_run=False, fixture_mode=False)
    prediction_rows = load_predictions(output)
    gold_rows = [
        SFTDatasetRow(**json.loads(line))
        for line in (tmp_path / "sft_public_sample.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    result = evaluate_predictions(gold_rows, prediction_rows)

    assert metadata["prediction_source_kind"] == "private_a100_adapter"
    assert prediction_rows["sft-test-1"] == {"task": {"description": "generic normalization output"}}
    assert result.metrics["json_valid_rate"] == 0.0
    assert result.failure_slices["schema"]["count"] == 2


def test_private_prediction_export_does_not_backfill_fixture_sidecars_for_legacy_writer(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    config = _write_prediction_config(tmp_path, adapter_path=(tmp_path / "adapter").as_posix())
    output = tmp_path / "trained_predictions.jsonl"

    monkeypatch.setattr(training, "_prediction_dependencies_available", lambda: True)

    def legacy_private_prediction_writer(
        config_payload: dict[str, Any],
        rows: list[SFTDatasetRow],
        output_path: Path,
    ) -> int:
        output_path.write_text(
            "\n".join(
                json.dumps(
                    {
                        "id": row.id,
                        "prediction": {"task": {"description": "legacy private writer output"}},
                        "prediction_source_kind": "private_a100_adapter",
                        "provenance": {"public_safe": True},
                    },
                    ensure_ascii=False,
                )
                for row in rows
            )
            + "\n",
            encoding="utf-8",
        )
        return len(rows)

    monkeypatch.setattr(training, "_run_real_sft_prediction", legacy_private_prediction_writer)

    try:
        run_sft_prediction_export(config, manifest, output, dry_run=False, fixture_mode=False)
    except TypeError:
        pass

    assert not (tmp_path / "raw_decoded_summary.jsonl").exists()
    assert not (tmp_path / "generation_trace.jsonl").exists()
    assert not (tmp_path / "prompt_snapshot.json").exists()


class _OffsetOnlyTokenizer:
    def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
        tokens: list[int] = []
        offsets: list[tuple[int, int]] = []
        for index, char in enumerate(text):
            token_id = ord(char)
            tokens.append(token_id)
            offsets.append((index, index + 1))
        return {
            "input_ids": tokens,
            "offset_mapping": offsets,
        }


class _InspectableTokenizer:
    chat_template = "fixture-template"

    def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]:
        tokens = [ord(char) for char in text]
        offsets = [(index, index + 1) for index, _ in enumerate(text)]
        return {
            "input_ids": tokens,
            "attention_mask": [1 for _ in tokens],
            "offset_mapping": offsets,
        }


class _AssistantOnlyLossCollator:
    def __call__(self, features: list[dict[str, Any]]) -> dict[str, list[list[int]]]:
        feature = features[0]
        assistant_start = feature["label_provenance_assistant_start"]
        labels = [
            -100 if end <= assistant_start else token_id
            for token_id, (_, end) in zip(feature["input_ids"], feature["offset_mapping"], strict=True)
        ]
        return {"labels": [labels]}


def test_sft_objective_inspection_keeps_fixture_collator_labels_non_real() -> None:
    row = SFTDatasetRow(
        id="sft-train-1",
        split="train",
        input_text="帮我搜索天气",
        target_contract=_contract("天气"),
        provenance={"source_id": "sft-train-1", "public_safe": True},
    )

    result = training.inspect_sft_objective(
        row,
        tokenizer=_InspectableTokenizer(),
        collator=_AssistantOnlyLossCollator(),
        label_source="trl_collator_labels",
        label_provenance={"source_kind": "fixture", "real_training_path": False},
    )

    assert result["inspection_status"] == "inspectable"
    assert result["dependency_unavailable"] is False
    assert result["tokenizer_status"] == "available"
    assert result["tokenizer_template_status"] == "template_available"
    assert result["collator_status"] == "labels_inspected"
    assert result["label_source"] == "trl_collator_labels"
    assert result["label_provenance"]["source_kind"] == "fixture"
    assert result["label_provenance"]["real_training_path"] is False
    assert result["label_tensor_available"] is True
    assert result["prompt_token_count"] > 0
    assert result["assistant_token_count"] > 0
    assert result["prompt_tokens_masked"] is True
    assert result["assistant_tokens_carry_loss"] is True
    assert result["true_label_mask_status"] == "fixture_only"
    assert "fixture_labels_not_real_training_proof" in result["evidence_gaps"]
    assert "real_training_label_provenance_missing" in result["evidence_gaps"]
    assert result["loss_interpretation"]["loss_improvement_alone_proves_contract_learning"] is False
    assert "training_text" not in result
    assert "assistant_contract_target" not in result


def test_sft_objective_inspection_keeps_unspecified_collator_labels_non_real() -> None:
    row = SFTDatasetRow(
        id="sft-train-1",
        split="train",
        input_text="帮我搜索天气",
        target_contract=_contract("天气"),
        provenance={"source_id": "sft-train-1", "public_safe": True},
    )

    result = training.inspect_sft_objective(
        row,
        tokenizer=_InspectableTokenizer(),
        collator=_AssistantOnlyLossCollator(),
        label_source="trl_collator_labels",
    )

    assert result["inspection_status"] == "inspectable"
    assert result["label_tensor_available"] is True
    assert result["prompt_tokens_masked"] is True
    assert result["assistant_tokens_carry_loss"] is True
    assert result["label_provenance"]["source_kind"] == "unspecified"
    assert result["label_provenance"]["real_training_path"] is False
    assert result["true_label_mask_status"] == "unavailable"
    assert "label_provenance_unspecified" in result["evidence_gaps"]
    assert "real_training_label_provenance_missing" in result["evidence_gaps"]


def test_sft_objective_inspection_allows_gap_free_labels_only_with_explicit_real_provenance() -> None:
    row = SFTDatasetRow(
        id="sft-train-1",
        split="train",
        input_text="帮我搜索天气",
        target_contract=_contract("天气"),
        provenance={"source_id": "sft-train-1", "public_safe": True},
    )

    result = training.inspect_sft_objective(
        row,
        tokenizer=_InspectableTokenizer(),
        collator=_AssistantOnlyLossCollator(),
        label_source="trl_collator_labels",
        label_provenance={"source_kind": "private_training_runtime", "real_training_path": True},
    )

    assert result["inspection_status"] == "inspectable"
    assert result["label_source"] == "trl_collator_labels"
    assert result["label_provenance"]["source_kind"] == "private_training_runtime"
    assert result["label_provenance"]["real_training_path"] is True
    assert result["true_label_mask_status"] == "inspectable"
    assert result["prompt_tokens_masked"] is True
    assert result["assistant_tokens_carry_loss"] is True
    assert result["evidence_gaps"] == []


def test_sft_objective_inspection_does_not_claim_real_loss_mask_without_provenance() -> None:
    row = SFTDatasetRow(
        id="sft-train-1",
        split="train",
        input_text="帮我搜索天气",
        target_contract=_contract("天气"),
        provenance={"source_id": "sft-train-1", "public_safe": True},
    )

    result = training.inspect_sft_objective(row, tokenizer=_OffsetOnlyTokenizer())

    assert result["inspection_status"] == "inspectable"
    assert result["prompt_tokens_masked"] is True
    assert result["assistant_tokens_carry_loss"] is True
    assert result["loss_interpretation"]["loss_improvement_alone_proves_contract_learning"] is False
    assert result["dependency_unavailable"] is False
    assert result["tokenizer_status"] == "available"
    assert result["tokenizer_template_status"] == "fallback"
    assert result["collator_status"] == "assistant_only_labels_constructed"
    assert result["label_source"] == "assistant_only_constructed_labels"
    assert result["label_tensor_available"] is True
    assert result["true_label_mask_status"] == "unavailable"
    assert "label_provenance_unspecified" in result["evidence_gaps"]
    assert "real_training_label_provenance_missing" in result["evidence_gaps"]


def test_sft_objective_inspection_reports_dependency_unavailable_without_train_deps(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: False)

    result = training.inspect_sft_objective_from_manifest(manifest, split="train")

    assert result["inspection_status"] == "dependency_unavailable"
    assert result["dependency_unavailable"] is True
    assert result["prompt_tokens_masked"] is None
    assert result["assistant_tokens_carry_loss"] is None
    assert result["tokenizer_status"] == "unavailable"
    assert result["collator_status"] == "unavailable"
    assert result["label_source"] == "unavailable"
    assert result["label_tensor_available"] is False


def test_sft_objective_inspection_cli_writes_dependency_unavailable_result(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    manifest = _write_manifest(tmp_path)
    output = tmp_path / "objective_inspection.json"
    monkeypatch.setattr(training, "_train_dependencies_available", lambda: False)

    assert (
        train_cli.main(
            [
                "sft-inspect-objective",
                "--manifest",
                manifest.as_posix(),
                "--output",
                output.as_posix(),
            ]
        )
        == 0
    )

    assert capsys.readouterr().out == ""
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["inspection_status"] == "dependency_unavailable"
    assert payload["dependency_unavailable"] is True
    assert payload["tokenizer_status"] == "unavailable"
    assert payload["tokenizer_template_status"] == "unavailable"
    assert payload["collator_status"] == "unavailable"
    assert payload["label_source"] == "unavailable"
    assert payload["label_tensor_available"] is False


def test_sft_label_provenance_report_cli_writes_public_safe_output_shape(
    tmp_path: Path,
    capsys: Any,
) -> None:
    objective = tmp_path / "objective_inspection.json"
    objective.write_text(
        json.dumps(
            {
                "inspection_status": "labels_unavailable",
                "dependency_unavailable": False,
                "tokenizer_status": "available",
                "tokenizer_template_status": "fallback",
                "collator_status": "not_supplied",
                "label_source": "unavailable",
                "label_provenance": {
                    "source_kind": "unavailable",
                    "real_training_path": False,
                    "token=secret1234": "sk-1234567890123456",
                },
                "label_tensor_available": False,
                "true_label_mask_status": "unavailable",
                "prompt_token_count": None,
                "assistant_token_count": None,
                "prompt_tokens_masked": None,
                "assistant_tokens_carry_loss": None,
                "evidence_gaps": ["collator_not_supplied", "real_training_label_provenance_missing"],
                "loss_interpretation": {
                    "loss_improvement_alone_proves_contract_learning": False,
                    "requires_assistant_loss_evidence": True,
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "label-provenance"

    assert (
        report_cli.main(
            [
                "sft-label-provenance",
                "--objective-inspection",
                objective.as_posix(),
                "--output-dir",
                output.as_posix(),
                "--prior-artifact",
                "target_template=reports/public-sample/sft-target-template-alignment/sft_target_template_alignment.json",
                "--prior-artifact",
                "/Users/example/private/token=secret1234=reports/public-sample/prior.json",
            ]
        )
        == 0
    )

    cli_output = json.loads(capsys.readouterr().out)
    summary_path = output / "label_provenance_summary.json"
    markdown_path = output / "label_provenance_summary.md"
    assert cli_output["ok"] is True
    assert cli_output["paths"]["json"] == summary_path.as_posix()
    assert cli_output["paths"]["markdown"] == markdown_path.as_posix()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert summary["evidence_kind"] == "sft_label_provenance"
    assert summary["inspection_status"] == "labels_unavailable"
    assert summary["tokenizer_template_status"] == "fallback"
    assert summary["collator_status"] == "not_supplied"
    assert summary["label_source"] == "unavailable"
    assert summary["label_tensor_available"] is False
    assert summary["true_label_mask_status"] == "unavailable"
    assert summary["prior_artifacts"]["target_template"].endswith("sft_target_template_alignment.json")
    assert summary["claims"]["checkpoint_release"] is False
    assert summary["claims"]["live_browser_benchmark_claim"] is False
    serialized_summary = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    assert "token=secret1234" not in serialized_summary
    assert "sk-1234567890123456" not in serialized_summary
    assert "/Users/example/private" not in serialized_summary
    assert "<secret>" in serialized_summary
    assert "<private_path>" in serialized_summary
    assert "labels_unavailable" in markdown
    assert "True label-mask status" in markdown
    assert "not a checkpoint release" in markdown
    assert "not a live-browser benchmark" in markdown
    assert "training_text" not in markdown
    assert scan_paths([summary_path, markdown_path]).ok is True


def test_prediction_evidence_pack_is_honest_and_public_safe(tmp_path: Path) -> None:
    prediction_path = tmp_path / "predictions.jsonl"
    prediction_path.write_text(
        json.dumps(
            {
                "id": "sft-test-1",
                "prediction": _contract("机票"),
                "prediction_source_kind": "public_sample_contract_fixture",
                "provenance": {"public_safe": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    metadata = {
        "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_source": "modelscope",
        "dataset_manifest_id": "public-sample-test",
        "prediction_source_kind": "public_sample_contract_fixture",
        "prediction_status": "fixture_predictions_written",
        "release_status": "not_released",
    }

    paths = write_prediction_evidence_pack(
        output_dir=tmp_path / "evidence",
        prediction_path=Path("reports/public-sample/a100-sft-prediction-eval-smoke/predictions.jsonl"),
        prediction_metadata=metadata,
        metrics_path=Path("reports/public-sample/a100-sft-prediction-eval-smoke/metrics.json"),
        smoke_result={"enabled": True, "passed": 1, "failed": 0, "notes": "controlled_validation_command"},
        leak_scan_result={"ok": True, "findings": []},
    )

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    report = paths["report"].read_text(encoding="utf-8").lower()
    assert manifest["release_status"] == "not_released"
    assert manifest["claims"]["checkpoint_release"] is False
    assert manifest["claims"]["live_browser_benchmark_claim"] is False
    assert manifest["prediction_source_kind"] == "public_sample_contract_fixture"
    assert "not a checkpoint release" in report
    assert "not a live-browser benchmark" in report
    assert "not private adapter model outputs" in report
    assert "private a100 adapter path" in report
    assert "reported as failures" in report
    assert scan_paths([paths["manifest"], paths["report"]]).ok is True


def test_train_split_overfit_evidence_pack_records_bounded_claims_and_sidecars(tmp_path: Path) -> None:
    metadata = {
        "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_source": "modelscope",
        "dataset_manifest_id": "public-sample-test",
        "prediction_source_kind": "public_sample_contract_fixture",
        "prediction_status": "fixture_predictions_written",
        "prediction_split": "train",
        "overfit_diagnostic": True,
        "generalization_claim": False,
        "release_status": "not_released",
        "sidecars": {
            "prompt_snapshot": "reports/public-sample/a100-train-split-overfit-diagnostic/prompt_snapshot.json",
            "raw_decoded_summary": (
                "reports/public-sample/a100-train-split-overfit-diagnostic/raw_decoded_summary.jsonl"
            ),
            "generation_trace": "reports/public-sample/a100-train-split-overfit-diagnostic/generation_trace.jsonl",
        },
        "diagnostic_artifacts": {
            "objective_inspection": (
                "reports/public-sample/a100-train-split-overfit-diagnostic/objective_inspection.json"
            ),
            "leak_scan": "reports/public-sample/a100-train-split-overfit-diagnostic/leak_scan_result.json",
        },
    }

    paths = write_prediction_evidence_pack(
        output_dir=tmp_path / "evidence",
        prediction_path=Path("reports/public-sample/a100-train-split-overfit-diagnostic/predictions.jsonl"),
        prediction_metadata=metadata,
        metrics_path=Path("reports/public-sample/a100-train-split-overfit-diagnostic/metrics.json"),
        smoke_result={"enabled": False, "passed": 0, "failed": 0, "notes": "not_run_for_train_split_diagnostic"},
        leak_scan_result={"ok": True, "findings": []},
    )

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    report = paths["report"].read_text(encoding="utf-8").lower()
    assert manifest["evidence_kind"] == "a100_train_split_overfit_diagnostic"
    assert manifest["prediction_split"] == "train"
    assert manifest["overfit_diagnostic"] is True
    assert manifest["generalization_claim"] is False
    assert manifest["claims"]["generalization_claim"] is False
    assert manifest["claims"]["release_claim"] is False
    assert manifest["sidecars"]["prompt_snapshot"].endswith("prompt_snapshot.json")
    assert manifest["diagnostic_artifacts"]["objective_inspection"].endswith("objective_inspection.json")
    assert manifest["diagnostic_artifacts"]["leak_scan"].endswith("leak_scan_result.json")
    assert "train-internal" in report
    assert "does not prove dev/test generalization" in report
    assert "objective inspection" in report
    assert "no release claim" in report
    assert scan_paths([paths["manifest"], paths["report"]]).ok is True


def test_train_split_overfit_metrics_are_standalone_bounded() -> None:
    metrics_json = json.loads(
        Path("reports/public-sample/a100-train-split-overfit-diagnostic/metrics.json").read_text(encoding="utf-8")
    )
    metrics_md = Path("reports/public-sample/a100-train-split-overfit-diagnostic/metrics.md").read_text(
        encoding="utf-8"
    )
    manifest = json.loads(
        Path("reports/public-sample/a100-train-split-overfit-diagnostic/manifest.json").read_text(encoding="utf-8")
    )
    leak_scan_result = json.loads(
        Path("reports/public-sample/a100-train-split-overfit-diagnostic/leak_scan_result.json").read_text(
            encoding="utf-8"
        )
    )
    report = Path("reports/public-sample/a100-train-split-overfit-diagnostic/report.md").read_text(encoding="utf-8")
    prediction_count = sum(
        1
        for line in Path("reports/public-sample/a100-train-split-overfit-diagnostic/predictions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    )
    human_brief = Path("docs/human-briefs/2026-06-03-run-a100-train-split-overfit-diagnostic.html").read_text(
        encoding="utf-8"
    )

    assert metrics_json["evidence_context"]["prediction_source_kind"] == "private_a100_adapter"
    assert metrics_json["evidence_context"]["prediction_split"] == "train"
    assert metrics_json["evidence_context"]["overfit_diagnostic"] is True
    assert metrics_json["evidence_context"]["model_quality_evidence"] is False
    assert metrics_json["evidence_context"].get("generalization_claim") is False
    assert metrics_json["evidence_context"].get("train_internal_recovery_observed") is False
    assert "prediction_source_kind: `private_a100_adapter`" in metrics_md
    assert "generalization_claim: `False`" in metrics_md
    assert "model_quality_evidence: `False`" in metrics_md
    assert "train_internal_recovery_observed: `False`" in metrics_md
    assert "No held-out generalization, release, production-readiness, or live-browser improvement claim" in metrics_md
    assert manifest["prediction_count"] == prediction_count == 3
    assert manifest["leak_scan_result"] == leak_scan_result
    assert metrics_json["failure_slices"]["schema"]["count"] == prediction_count
    assert "Schema validity: failed" in report
    assert "Route correctness: failed" in report
    assert "Slot shape: failed" in report
    assert "Safety decision: partial" in report
    assert "Confirmation behavior: failed" in report
    assert "not recovered" in report
    assert "must not be described as schema recovery" in report
    assert "3 条 train prediction" in human_brief


def test_assistant_only_train_split_rerun_evidence_is_bounded_and_public_safe() -> None:
    evidence_dir = Path("reports/public-sample/a100-assistant-only-train-split-rerun")
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    adapter_metadata = json.loads((evidence_dir / "adapter_metadata.json").read_text(encoding="utf-8"))
    full_leak_scan = json.loads((evidence_dir / "full_public_leak_scan_result.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    objective = json.loads((evidence_dir / "objective_inspection.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    prediction_count = sum(
        1 for line in (evidence_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    )

    assert manifest["evidence_kind"] == "a100_assistant_only_train_split_rerun"
    assert manifest["prediction_split"] == "train"
    assert manifest["overfit_diagnostic"] is True
    assert manifest["generalization_claim"] is False
    assert manifest["prediction_count"] == prediction_count == 3
    assert manifest["training_row_ids"] == [
        "seed-search-weather",
        "seed-search-weather-aug-1",
        "seed-search-weather-aug-2",
    ]
    assert manifest["source_manifest_rows"]["sft_rows"] == 12
    assert manifest["training_split"] == "train"
    assert manifest["training_rows_used"] == 3
    assert (
        adapter_metadata["dataset_load"]["loaded_rows_scope"]
        == "public_sample_manifest_sft_rows_before_train_split_filter"
    )
    assert adapter_metadata["dataset_load"]["training_row_ids"] == manifest["training_row_ids"]
    assert adapter_metadata["dataset_load"]["training_split"] == "train"
    assert adapter_metadata["dataset_load"]["training_rows_used"] == 3
    assert adapter_metadata["training_row_ids"] == manifest["training_row_ids"]
    assert adapter_metadata["training_split"] == "train"
    assert adapter_metadata["training_rows_used"] == 3
    assert "private A100 runtime" in adapter_metadata["notes"]
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["model_quality_evidence"] is False
    assert objective["prompt_tokens_masked"] is True
    assert objective["assistant_tokens_carry_loss"] is True
    assert metrics["evidence_context"]["assistant_only_objective_inspected"] is True
    assert metrics["evidence_context"]["train_internal_recovery_observed"] is False
    assert metrics["failure_slices"]["schema"]["count"] == 3
    assert full_leak_scan["ok"] is True
    assert full_leak_scan["findings"] == []
    assert "pre-assistant-only-objective-repair context" in report
    assert "schema-valid Browser Task Contract `json_valid_rate=0.0000`" in report
    assert "not held-out generalization" in report
    assert scan_paths([evidence_dir]).ok is True


def test_assistant_only_schema_output_diagnosis_separates_parseability_from_contract_validity() -> None:
    evidence_dir = Path("reports/public-sample/a100-assistant-only-train-split-rerun")
    diagnosis = json.loads((evidence_dir / "schema_output_diagnosis.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "schema_output_diagnosis_leak_scan_result.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "schema_output_diagnosis.md").read_text(encoding="utf-8")

    assert diagnosis["diagnostic_kind"] == "assistant_only_schema_output_failure_diagnosis"
    assert diagnosis["prediction_split"] == "train"
    assert diagnosis["overfit_diagnostic"] is True
    assert diagnosis["generalization_claim"] is False
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["raw_json_parseable_count"] == 3
    assert diagnosis["summary"]["contract_schema_valid_count"] == 0
    assert diagnosis["summary"]["contract_schema_valid_rate"] == 0.0
    assert diagnosis["summary"]["truncation_or_decode_limit_count"] == 0
    assert diagnosis["summary"]["dominant_failure_family"] == (
        "parseable_json_contract_shape_missing_required_fields"
    )
    assert diagnosis["field_issue_counts"]["missing_required_fields"] == {
        "contract_version": 1,
        "normalized_command": 2,
        "safety": 3,
    }
    assert diagnosis["field_issue_counts"]["field_mismatches"]["slots"] == 3
    assert all(row["raw_json_parseable"] is True for row in diagnosis["rows"])
    assert all(row["contract_schema_valid"] is False for row in diagnosis["rows"])
    assert all(row["generation_finish_state"] == "eos_observed" for row in diagnosis["rows"])
    assert diagnosis["claims"]["raw_json_parseability_is_not_contract_schema_validity"] is True
    assert diagnosis["claims"]["does_not_repair_normalize_coerce_or_replace_predictions"] is True
    assert diagnosis["recommended_next_bounded_phase"]["needs_user_confirmation_before_behavior_change"] is True
    assert "parseable JSON is not the same as schema-valid Browser Task Contract output" in report
    expected_boundary = (
        "This phase does not modify decoding, prompt templates, schemas, data generation, "
        "or training objectives"
    )
    assert expected_boundary in report
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert scan_paths(
        [
            evidence_dir / "schema_output_diagnosis.json",
            evidence_dir / "schema_output_diagnosis.md",
        ]
    ).ok is True


def test_contract_output_recovery_template_is_public_safe_and_bounded() -> None:
    template = Path("reports/templates/a100-sft-contract-output-recovery.md")

    text = template.read_text(encoding="utf-8")

    assert "json_valid_rate=0.0000" in text
    assert "12 schema failures" in text
    assert "reports/public-sample/a100-sft-post-recovery-rerun/" in text
    assert "post-rerun result: `json_valid_rate=0.0000`" in text
    assert "post-rerun controlled smoke: `0 passed / 12 failed`" in text
    assert "did not recover schema-valid Browser Task Contract output" in text
    assert "not a checkpoint release" in text
    assert "not a live-browser benchmark" in text
    assert "no production-readiness claim" in text
    assert "private_a100_adapter" in text
    assert "<a100_project_root>" in text
    assert scan_paths([template]).ok is True


def test_required_field_repair_train_split_rerun_evidence_preserves_retry_attempts_and_bounds() -> None:
    evidence_dir = Path("reports/public-sample/a100-required-field-repair-train-split-rerun")
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_summary = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    full_leak_scan = json.loads((evidence_dir / "full_public_leak_scan_result.json").read_text(encoding="utf-8"))
    raw_rows = [
        json.loads(line)
        for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")

    assert manifest["evidence_kind"] == "a100_required_field_repair_train_split_rerun"
    assert manifest["prediction_split"] == "train"
    assert manifest["training_rows_used"] == 3
    assert manifest["prediction_count"] == 3
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["adapter_release"] is False
    assert manifest["observed_result"]["json_valid_rate"] == 0.0
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 0
    assert manifest["release_status"] == "not_released"
    assert manifest["diagnostic_artifacts"]["prediction_metadata"].endswith("prediction_metadata.json")
    assert manifest["loss_mask_policy"]["policy"] == "assistant_only_completion_only"
    assert manifest["loss_mask_policy"]["assistant_target"] == "browser_task_contract_json"
    assert manifest["schema_guard_policy"]["schema_guard_enabled"] is True
    assert manifest["schema_guard_policy"]["schema_retry_enabled"] is True
    assert manifest["schema_guard_policy"]["schema_retry_max_attempts"] == 1
    assert manifest["decoding_policy"]["strategy"] == "greedy"
    assert manifest["decoding_policy"]["raw_decoded_sidecar_written"] is True
    assert metrics["evidence_context"]["required_field_skeleton_visible"] is True
    assert metrics["evidence_context"]["schema_retry_enabled"] is True
    assert metrics["evidence_context"]["validated_output_schema_valid_count"] == 0
    assert metrics["failure_slices"]["schema"]["count"] == 3
    assert schema_summary["raw_attempt_schema_valid_count"] == 0
    assert schema_summary["retry_attempted_count"] == 3
    assert schema_summary["retry_attempt_schema_valid_count"] == 0
    assert schema_summary["validated_output_schema_valid_count"] == 0
    assert schema_summary["retry_attempt_summary_present"] is True
    assert all("raw_attempt" in row and "retry_attempt" in row for row in raw_rows)
    assert all(row["retry_attempt"] is not None for row in raw_rows)
    assert full_leak_scan["ok"] is True
    assert full_leak_scan["findings"] == []
    assert "Prediction metadata:" in report
    assert "Adapter metadata:" in report
    assert "Release status: `not_released`" in report
    assert "Loss-mask policy: `assistant_only_completion_only`" in report
    assert "Schema guard enabled: `True`" in report
    assert "Schema retry enabled: `True`" in report
    assert "Decoding strategy: `greedy`" in report
    assert "must not be described as schema recovery" in report
    assert scan_paths([evidence_dir]).ok is True


def test_strict_retry_train_split_rerun_evidence_preserves_rejected_retry_fragments() -> None:
    evidence_dir = Path("reports/public-sample/a100-strict-retry-train-split-rerun")
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_summary = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    constrained = json.loads((evidence_dir / "constrained_decoding_diagnosis.json").read_text(encoding="utf-8"))
    full_leak_scan = json.loads((evidence_dir / "full_public_leak_scan_result.json").read_text(encoding="utf-8"))
    raw_rows = [
        json.loads(line)
        for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")

    assert manifest["evidence_kind"] == "a100_strict_retry_train_split_rerun"
    assert manifest["prediction_split"] == "train"
    assert manifest["training_rows_used"] == 3
    assert manifest["prediction_count"] == 3
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["adapter_release"] is False
    assert manifest["release_status"] == "not_released"
    assert manifest["strict_retry_interpretation"] == "whole_string_json_only_retry_parser"
    assert manifest["prior_context"]["required_field_repair_rerun"] == (
        "a100-required-field-repair-train-split-rerun"
    )
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 0
    assert manifest["observed_result"]["retry_fragment_objects_rejected_count"] == 3
    assert metrics["evidence_context"]["strict_retry_interpretation"] == "whole_string_json_only_retry_parser"
    assert metrics["evidence_context"]["retry_fragment_objects_rejected_count"] == 3
    assert metrics["failure_slices"]["schema"]["count"] == 3
    assert schema_summary["retry_attempted_count"] == 3
    assert schema_summary["retry_attempt_schema_valid_count"] == 0
    assert schema_summary["validated_output_schema_valid_count"] == 0
    assert schema_summary["strict_retry_parser_rejected_fragment_count"] == 3
    assert all(row["retry_attempt"]["parse_status"] == "json_fragment_object" for row in raw_rows)
    assert constrained["summary"]["json_fragment_retry_attempt_count"] == 3
    assert constrained["summary"]["validated_output_schema_valid_count"] == 0
    assert full_leak_scan["ok"] is True
    assert full_leak_scan["findings"] == []
    assert "strict retry rejected JSON fragments wrapped in Markdown/prose" in report
    assert "must not be described as schema recovery" in report
    assert scan_paths([evidence_dir]).ok is True


def test_constrained_output_train_split_rerun_evidence_preserves_failure_boundary() -> None:
    evidence_dir = Path("reports/public-sample/a100-constrained-output-train-split-rerun")
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((evidence_dir / "metrics.json").read_text(encoding="utf-8"))
    schema_summary = json.loads((evidence_dir / "schema_guard_summary.json").read_text(encoding="utf-8"))
    constrained = json.loads((evidence_dir / "constrained_decoding_diagnosis.json").read_text(encoding="utf-8"))
    prompt_snapshot = json.loads((evidence_dir / "prompt_snapshot.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_leak_scan = json.loads((evidence_dir / "phase_leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads(
        (evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8")
    )
    prediction_rows = [
        json.loads(line)
        for line in (evidence_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    raw_rows = [
        json.loads(line)
        for line in (evidence_dir / "raw_decoded_summary.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    generation_trace_rows = [
        json.loads(line)
        for line in (evidence_dir / "generation_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train_gold_rows = [
        json.loads(line)
        for line in (evidence_dir / "train_split_gold.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = (evidence_dir / "report.md").read_text(encoding="utf-8")
    expected_row_ids = ["seed-search-weather", "seed-search-weather-aug-1", "seed-search-weather-aug-2"]

    assert manifest["evidence_kind"] == "a100_constrained_output_train_split_rerun"
    assert manifest["prediction_source_kind"] == "private_a100_adapter"
    assert manifest["prediction_split"] == "train"
    assert manifest["prediction_count"] == 3
    assert manifest["training_rows_used"] == 3
    assert manifest["training_row_ids"] == expected_row_ids
    assert [row["id"] for row in prediction_rows] == expected_row_ids
    assert [row["id"] for row in raw_rows] == expected_row_ids
    assert [row["id"] for row in generation_trace_rows] == expected_row_ids
    assert [row["id"] for row in train_gold_rows] == expected_row_ids
    assert [row["id"] for row in prompt_snapshot["rows"]] == expected_row_ids
    assert len(prompt_snapshot["rows"]) == 3
    assert manifest["claims"]["held_out_generalization_claim"] is False
    assert manifest["claims"]["adapter_release"] is False
    assert manifest["release_status"] == "not_released"
    assert manifest["diagnostic_artifacts"]["phase_validation_leak_scan"].endswith(
        "phase_validation_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["post_archive_leak_scan"].endswith(
        "post_archive_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["final_leak_scan"].endswith(
        "final_leak_scan_result.json"
    )
    assert manifest["observed_result"]["validated_output_schema_valid_count"] == 0
    assert manifest["observed_result"]["baseline_validated_output_schema_valid_count"] == 0
    assert manifest["observed_result"]["retry_fragment_objects_rejected_count"] == 3
    assert manifest["observed_result"]["train_internal_recovery_observed"] is False
    assert prompt_snapshot["prompt_constraints"]["canonical_json_one_shot_visible"] is True
    assert prompt_snapshot["prompt_constraints"]["whole_object_boundary_visible"] is True
    assert metrics["evidence_context"]["training_rows_used"] == 3
    assert metrics["evidence_context"]["canonical_json_one_shot_visible"] is True
    assert metrics["evidence_context"]["whole_object_boundary_visible"] is True
    assert metrics["evidence_context"]["validated_output_schema_valid_count"] == 0
    assert metrics["failure_slices"]["schema"]["count"] == 3
    assert schema_summary["comparison_to_pre_repair_strict_retry_baseline"]["schema_recovery_observed"] is False
    assert schema_summary["strict_retry_parser_rejected_fragment_count"] == 3
    assert schema_summary["validated_output_source_counts"] == {"none": 3}
    assert constrained["summary"]["prose_markdown_wrapper_count"] == 3
    assert constrained["summary"]["validated_output_schema_valid_count"] == 0
    assert any(row["raw_attempt"]["parse_status"] == "json_object" for row in raw_rows)
    assert all(row["retry_attempt"]["parse_status"] == "json_fragment_object" for row in raw_rows)
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_leak_scan["ok"] is True
    assert phase_leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert "final validated schema-valid `0/3`" in report
    assert "not be described as model recovery" in report
    assert scan_paths([evidence_dir]).ok is True


def test_normalized_command_string_mismatch_evidence_pack_is_public_safe_and_bounded() -> None:
    evidence_dir = Path("reports/public-sample/confirmation-rerun-normalized-command-string-mismatch-diagnosis")
    human_brief_path = Path("docs/human-briefs/2026-06-05-diagnose-normalized-command-string-mismatches.html")
    change_dirs = [
        Path("openspec/changes/diagnose-normalized-command-string-mismatches"),
        Path("openspec/changes/archive/2026-06-05-diagnose-normalized-command-string-mismatches"),
    ]
    expected_artifacts = {
        "normalized_command_mismatch_diagnosis.json",
        "normalized_command_mismatch_diagnosis.md",
        "manifest.json",
        "leak_scan_result.json",
        "phase_validation_leak_scan_result.json",
        "post_archive_leak_scan_result.json",
        "final_leak_scan_result.json",
        "strict_string_mismatch_policy.md",
        "strict_string_policy_leak_scan_result.json",
    }

    assert {path.name for path in evidence_dir.iterdir()} >= expected_artifacts
    assert human_brief_path.exists()
    existing_change_dirs = [path for path in change_dirs if path.exists()]
    assert existing_change_dirs

    diagnosis = json.loads((evidence_dir / "normalized_command_mismatch_diagnosis.json").read_text(encoding="utf-8"))
    report = (evidence_dir / "normalized_command_mismatch_diagnosis.md").read_text(encoding="utf-8")
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    phase_validation_leak_scan = json.loads(
        (evidence_dir / "phase_validation_leak_scan_result.json").read_text(encoding="utf-8")
    )
    post_archive_leak_scan = json.loads(
        (evidence_dir / "post_archive_leak_scan_result.json").read_text(encoding="utf-8")
    )
    final_leak_scan = json.loads((evidence_dir / "final_leak_scan_result.json").read_text(encoding="utf-8"))
    human_brief = human_brief_path.read_text(encoding="utf-8")
    strict_string_policy = (evidence_dir / "strict_string_mismatch_policy.md").read_text(encoding="utf-8")
    strict_string_policy_leak_scan = json.loads(
        (evidence_dir / "strict_string_policy_leak_scan_result.json").read_text(encoding="utf-8")
    )

    assert diagnosis["diagnostic_kind"] == "normalized_command_string_mismatch_diagnosis"
    assert diagnosis["summary"]["normalized_command_mismatch_count"] == 3
    assert diagnosis["summary"]["context_counts"] == {
        "co_occurs_with_schema_failure": 1,
        "co_occurs_with_semantic_task_route_safety": 1,
        "strict_string_only": 1,
    }
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 2 / 3
    assert diagnosis["summary"]["strict_final_task_type_accuracy"] == 1 / 3
    assert diagnosis["summary"]["strict_final_route_accuracy"] == 1 / 3
    assert diagnosis["summary"]["strict_final_confirmation_accuracy"] == 2 / 3
    assert diagnosis["summary"]["strict_final_slot_f1"] == 2 / 3
    assert diagnosis["summary"]["strict_metrics_preserved"] is True
    assert diagnosis["source_artifacts"]["row_mismatch_diagnosis"].endswith("row_mismatch_diagnosis.json")
    assert diagnosis["source_artifacts"]["row_mismatch_manifest"].endswith("manifest.json")
    assert set(diagnosis["source_artifacts"]) == {"row_mismatch_diagnosis", "row_mismatch_manifest"}
    assert diagnosis["transitive_source_artifacts"]["predictions"].endswith("predictions.jsonl")
    assert diagnosis["source_artifact_policy"]["primary_inputs_are_row_mismatch_artifacts"] is True
    assert diagnosis["source_artifact_policy"]["transitive_rerun_artifacts_are_linked_for_traceability_only"] is True
    assert diagnosis["claims"]["local_evidence_only_analysis"] is True
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["normalized_command_normalization_performed"] is False
    assert diagnosis["claims"]["normalized_command_semantic_equivalence_marked"] is False
    assert diagnosis["claims"]["search_query_terms_marked_equivalent"] is False
    assert diagnosis["claims"]["predictions_repaired_or_replaced"] is False
    assert diagnosis["claims"]["predictions_rescored"] is False
    assert diagnosis["claims"]["training_or_prediction_rerun_performed"] is False

    assert manifest["evidence_kind"] == "confirmation_rerun_normalized_command_string_mismatch_diagnosis"
    assert manifest["counts"] == {
        "co_occurs_with_schema_failure": 1,
        "co_occurs_with_semantic_task_route_safety": 1,
        "normalized_command_mismatch_rows": 3,
        "strict_string_only": 1,
    }
    assert manifest["diagnostic_artifacts"]["normalized_command_mismatch_diagnosis"].endswith(
        "normalized_command_mismatch_diagnosis.json"
    )
    assert manifest["diagnostic_artifacts"]["normalized_command_mismatch_report"].endswith(
        "normalized_command_mismatch_diagnosis.md"
    )
    assert manifest["diagnostic_artifacts"]["leak_scan"].endswith("leak_scan_result.json")
    assert manifest["diagnostic_artifacts"]["phase_validation_leak_scan"].endswith(
        "phase_validation_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["post_archive_leak_scan"].endswith(
        "post_archive_leak_scan_result.json"
    )
    assert manifest["diagnostic_artifacts"]["final_leak_scan"].endswith("final_leak_scan_result.json")
    assert manifest["diagnostic_artifacts"]["strict_string_mismatch_policy"].endswith(
        "strict_string_mismatch_policy.md"
    )
    assert manifest["diagnostic_artifacts"]["strict_string_policy_leak_scan"].endswith(
        "strict_string_policy_leak_scan_result.json"
    )
    assert manifest["source_artifacts"]["row_mismatch_diagnosis"].endswith("row_mismatch_diagnosis.json")
    assert manifest["source_artifacts"]["row_mismatch_manifest"].endswith("manifest.json")
    assert set(manifest["source_artifacts"]) == {"row_mismatch_diagnosis", "row_mismatch_manifest"}
    assert manifest["transitive_source_artifacts"]["predictions"].endswith("predictions.jsonl")
    assert manifest["transitive_source_artifacts"]["train_split_gold"].endswith("train_split_gold.jsonl")
    assert manifest["strict_string_policy_clarification"] == {
        "artifact": (
            "reports/public-sample/confirmation-rerun-normalized-command-string-mismatch-diagnosis/"
            "strict_string_mismatch_policy.md"
        ),
        "artifact_role": "later_reader_facing_interpretation_note",
        "change_name": "clarify-strict-string-mismatch-policy",
        "clarified_on": "2026-06-05",
        "not_rerun_or_metric_artifact": True,
    }
    assert manifest["source_artifact_policy"]["primary_inputs_are_row_mismatch_artifacts"] is True
    assert manifest["source_artifact_policy"]["transitive_rerun_artifacts_are_linked_for_traceability_only"] is True
    assert manifest["metrics_preserved"]["contract_exact_match"] == 0.0
    assert manifest["claims"]["local_evidence_only_analysis"] is True
    assert manifest["claims"]["semantic_equivalence_scoring_performed"] is False
    assert manifest["claims"]["normalized_command_normalization_performed"] is False
    assert manifest["claims"]["predictions_rescored"] is False

    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert phase_validation_leak_scan["ok"] is True
    assert phase_validation_leak_scan["findings"] == []
    assert post_archive_leak_scan["ok"] is True
    assert post_archive_leak_scan["findings"] == []
    assert final_leak_scan["ok"] is True
    assert final_leak_scan["findings"] == []
    assert strict_string_policy_leak_scan["ok"] is True
    assert strict_string_policy_leak_scan["findings"] == []
    assert "README.md" in strict_string_policy_leak_scan["scanned_paths"]
    archived_change_path = "openspec/changes/archive/2026-06-05-clarify-strict-string-mismatch-policy"
    assert archived_change_path in strict_string_policy_leak_scan["scanned_paths"]
    assert "local evidence-only analysis" in report
    assert "does not normalize or semantically score" in report
    assert "`contract_exact_match` remains a hard full-contract exact-match metric" in strict_string_policy
    assert "explanatory row-level evidence only" in strict_string_policy
    assert "not automatically marked equivalent" in strict_string_policy
    assert "No A100 execution was performed" in strict_string_policy
    assert "本地 evidence-only" in human_brief
    assert "不改 strict evaluator metrics" in human_brief

    combined_public_text = "\n".join(
        [
            json.dumps(diagnosis, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(phase_validation_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(post_archive_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(final_leak_scan, ensure_ascii=False, sort_keys=True),
            json.dumps(strict_string_policy_leak_scan, ensure_ascii=False, sort_keys=True),
            report,
            strict_string_policy,
            human_brief,
        ]
    )
    assert "/mnt/data/" not in combined_public_text
    assert "/Users/" not in combined_public_text
    assert "volcano" not in combined_public_text
    assert scan_paths([evidence_dir, human_brief_path, *existing_change_dirs]).ok is True


def test_output_boundary_template_decoding_instrumentation_pack_is_public_safe_and_bounded() -> None:
    evidence_dir = Path("reports/public-sample/repair-output-boundary-template-decoding-instrumentation")
    human_brief_path = Path(
        "docs/human-briefs/2026-06-08-repair-output-boundary-template-decoding-instrumentation.html"
    )
    change_dir = Path(
        "openspec/changes/archive/2026-06-08-repair-output-boundary-template-decoding-instrumentation"
    )
    required_files = {
        "first_pass_output_boundary_summary.json",
        "first_pass_output_boundary_summary.md",
        "manifest.json",
        "leak_scan_result.json",
    }

    assert evidence_dir.exists()
    assert required_files <= {path.name for path in evidence_dir.iterdir()}
    assert human_brief_path.exists()

    summary = json.loads((evidence_dir / "first_pass_output_boundary_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    leak_scan = json.loads((evidence_dir / "leak_scan_result.json").read_text(encoding="utf-8"))
    markdown = (evidence_dir / "first_pass_output_boundary_summary.md").read_text(encoding="utf-8")
    human_brief = human_brief_path.read_text(encoding="utf-8")

    assert summary["evidence_kind"] == "first_pass_output_boundary_template_decoding_instrumentation_local"
    assert summary["change_name"] == "repair-output-boundary-template-decoding-instrumentation"
    assert summary["prediction_output_boundary"]["exact_json_only_output_visible"] is True
    assert summary["prediction_output_boundary"]["no_text_outside_root_json_object_visible"] is True
    assert summary["prediction_output_boundary"]["strict_whole_object_parser_boundary_visible"] is True
    assert summary["strict_parser_behavior"]["wrapped_json_fragment_rejected"] is True
    assert summary["metadata_propagation"]["prediction_metadata_exposes_boundary"] is True
    assert summary["metadata_propagation"]["prompt_snapshot_exposes_boundary"] is True
    assert summary["prior_a100_context"]["strict_schema_valid_output"] == "0/3"
    assert summary["prior_a100_context"]["markdown_wrapped_predictions"] == "3/3"
    assert summary["claims"]["local_behavior_change_only"] is True
    assert summary["claims"]["a100_execution_performed"] is False
    assert summary["claims"]["training_performed"] is False
    assert summary["claims"]["parser_relaxation_performed"] is False
    assert summary["claims"]["prediction_repair_or_rescore_performed"] is False
    assert summary["claims"]["model_quality_improvement_claim"] is False
    assert manifest["diagnostic_artifacts"]["summary_json"].endswith("first_pass_output_boundary_summary.json")
    assert leak_scan["ok"] is True
    assert leak_scan["findings"] == []
    assert "local behavior change only" in markdown
    assert "does not prove trained-adapter output behavior changed" in markdown
    assert "不能声明模型质量改善" in human_brief

    combined_public_text = "\n".join(
        [
            json.dumps(summary, ensure_ascii=False, sort_keys=True),
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            json.dumps(leak_scan, ensure_ascii=False, sort_keys=True),
            markdown,
            human_brief,
        ]
    )
    assert "/mnt/data/" not in combined_public_text
    assert "/Users/" not in combined_public_text
    assert scan_paths([evidence_dir, human_brief_path, change_dir]).ok is True


def test_leak_scan_rejects_model_adapter_and_cache_artifacts(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    (evidence_dir / "adapter").mkdir(parents=True)
    (evidence_dir / "adapter" / "adapter_config.json").write_text("{}", encoding="utf-8")
    (evidence_dir / "model.safetensors").write_text("placeholder", encoding="utf-8")
    (evidence_dir / "cache").mkdir()
    (evidence_dir / "cache" / "index.json").write_text("{}", encoding="utf-8")

    result = scan_paths([evidence_dir])

    assert {
        "model_artifact",
        "private_artifact_dir",
    }.issubset({finding.category for finding in result.findings})
