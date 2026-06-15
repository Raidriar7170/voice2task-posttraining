import json
from pathlib import Path

import pytest

from voice2task.cli import eval as eval_cli
from voice2task.evaluation import diagnose_merged_slot_value_residuals
from voice2task.io import write_json
from voice2task.leak_scan import scan_paths
from voice2task.reports import write_merged_slot_value_residual_report
from voice2task.schemas import SFTDatasetRow


def _contract(
    *,
    task_type: str = "form_fill",
    route: str = "fill_form",
    slots: dict[str, str] | None = None,
    normalized_command: str = "填写邮箱并确认",
) -> dict[str, object]:
    return {
        "task_type": task_type,
        "route": route,
        "safety": {"allow": True, "reason": "requires_confirmation"},
        "confirmation_required": True,
        "slots": slots if slots is not None else {"field": "邮箱"},
        "normalized_command": normalized_command,
        "language": "zh-CN",
        "contract_version": "v1",
    }


def _row(row_id: str, split: str, target_contract: dict[str, object]) -> SFTDatasetRow:
    return SFTDatasetRow(
        id=row_id,
        split=split,
        input_text=f"public sample {row_id}",
        target_contract=target_contract,
        provenance={"source_id": row_id.rsplit("-", 1)[0], "public_safe": True},
    )


def _source_manifest() -> dict[str, object]:
    return {
        "evidence_kind": "a100_merged_slot_value_heldout_eval",
        "dataset_manifest_id": "public-sample-test",
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "split_results": {
            "dev": {
                "contract_exact_match": 0.5,
                "slot_f1": 0.5,
                "slot_f1_soft": 1.0,
                "json_valid_rate": 1.0,
                "task_type_accuracy": 1.0,
                "route_accuracy": 1.0,
                "confirmation_accuracy": 1.0,
                "safety_precision": 1.0,
                "safety_recall": 1.0,
                "residual_row_count": 1,
            },
            "test": {
                "contract_exact_match": 0.8333333333333334,
                "slot_f1": 1.0,
                "slot_f1_soft": 1.0,
                "json_valid_rate": 1.0,
                "task_type_accuracy": 1.0,
                "route_accuracy": 1.0,
                "confirmation_accuracy": 1.0,
                "safety_precision": 1.0,
                "safety_recall": 1.0,
                "residual_row_count": 1,
            },
        },
    }


def test_merged_slot_value_residual_diagnostic_classifies_strict_remaining_mismatches() -> None:
    form_gold = _contract()
    open_gold = _contract(
        task_type="navigate",
        route="open_url",
        slots={"url": "https://example.com"},
        normalized_command="打开示例网站",
    )
    rows_by_split = {
        "dev": [_row("seed-form-email-dev", "dev", form_gold)],
        "test": [_row("seed-open-example-test", "test", open_gold)],
    }
    predictions_by_split = {
        "dev": {"seed-form-email-dev": {**form_gold, "slots": {"field": "email"}}},
        "test": {"seed-open-example-test": {**open_gold, "normalized_command": "访问示例网站"}},
    }

    diagnosis = diagnose_merged_slot_value_residuals(
        merged_manifest=_source_manifest(),
        rows_by_split=rows_by_split,
        predictions_by_split=predictions_by_split,
    )

    assert diagnosis["evidence_kind"] == "merged_slot_value_residual_diagnosis"
    assert diagnosis["diagnostic_mode"] == "public_safe_no_training_no_prediction_no_metric_change"
    assert diagnosis["source_merged_eval"]["evidence_kind"] == "a100_merged_slot_value_heldout_eval"
    assert diagnosis["summary"]["strict_contract_exact_match"] == {
        "dev": 0.5,
        "test": 0.8333333333333334,
    }
    assert diagnosis["summary"]["strict_slot_f1"] == {"dev": 0.5, "test": 1.0}
    assert diagnosis["summary"]["soft_slot_f1"] == {"dev": 1.0, "test": 1.0}
    assert diagnosis["summary"]["soft_slot_f1_primary_metric"] is False
    assert diagnosis["summary"]["residual_row_count"] == 2
    assert diagnosis["summary"]["residual_field_counts"] == {"normalized_command": 1, "slots": 1}
    assert diagnosis["summary"]["source_count_consistency"]["ok"] is True
    assert diagnosis["summary"]["source_count_consistency"]["by_split"] == {
        "dev": {"computed": 1, "expected": 1, "ok": True},
        "test": {"computed": 1, "expected": 1, "ok": True},
    }
    assert diagnosis["summary"]["residual_category_counts"] == {
        "normalized_command_strict_string_mismatch": 1,
        "slot_value_strict_mismatch_soft_match": 1,
    }
    assert diagnosis["summary"]["recommended_next_step"] == "review_residual_buckets_before_data_or_training_change"

    residuals = {(entry["split"], entry["row_id"], entry["field_path"]): entry for entry in diagnosis["residuals"]}
    assert residuals[("dev", "seed-form-email-dev", "slots")]["category"] == (
        "slot_value_strict_mismatch_soft_match"
    )
    assert residuals[("test", "seed-open-example-test", "normalized_command")]["category"] == (
        "normalized_command_strict_string_mismatch"
    )
    assert diagnosis["execution_scope"]["training_run"] is False
    assert diagnosis["execution_scope"]["prediction_run"] is False
    assert diagnosis["execution_scope"]["evaluator_metric_change"] is False
    assert diagnosis["claims"]["held_out_recovery_claim"] is False
    assert diagnosis["claims"]["semantic_equivalence_primary_metric"] is False


def test_merged_slot_value_residual_diagnostic_fails_closed_on_source_count_mismatch() -> None:
    gold = _contract()
    with pytest.raises(ValueError, match="residual count mismatch"):
        diagnose_merged_slot_value_residuals(
            merged_manifest=_source_manifest(),
            rows_by_split={"dev": [_row("seed-form-email-dev", "dev", gold)], "test": []},
            predictions_by_split={"dev": {"seed-form-email-dev": gold}, "test": {}},
        )


def test_merged_slot_value_residual_report_is_public_safe_and_bounded(tmp_path: Path) -> None:
    dev_gold = _contract()
    test_gold = _contract(
        task_type="navigate",
        route="open_url",
        slots={"url": "https://example.com"},
        normalized_command="打开示例网站",
    )
    diagnosis = diagnose_merged_slot_value_residuals(
        merged_manifest=_source_manifest(),
        rows_by_split={
            "dev": [_row("seed-form-email-dev", "dev", dev_gold)],
            "test": [_row("seed-open-example-test", "test", test_gold)],
        },
        predictions_by_split={
            "dev": {"seed-form-email-dev": {**dev_gold, "slots": {"field": "email"}}},
            "test": {"seed-open-example-test": {**test_gold, "normalized_command": "访问示例网站"}},
        },
    )

    paths = write_merged_slot_value_residual_report(diagnosis, tmp_path)

    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert paths["manifest"].exists()

    saved = json.loads(paths["json"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    markdown = paths["markdown"].read_text(encoding="utf-8")

    assert saved["claims"]["prediction_repair_or_replacement"] is False
    assert manifest["artifact_policy"]["private_paths_omitted"] is True
    assert manifest["claims"]["soft_slot_f1_primary_metric"] is False
    assert "strict `contract_exact_match` remains primary" in markdown
    assert "Soft slot F1 is internal diagnostic-only" in markdown
    assert "not held-out recovery" in markdown
    assert scan_paths([tmp_path]).ok is True


def test_merged_slot_value_residual_cli_filters_gold_rows_by_requested_split(tmp_path: Path, capsys: object) -> None:
    dev_gold = _contract()
    test_gold = _contract(
        task_type="navigate",
        route="open_url",
        slots={"url": "https://example.com"},
        normalized_command="打开示例网站",
    )
    all_rows = [
        _row("seed-form-email-dev", "dev", dev_gold).to_dict(),
        _row("seed-open-example-test", "test", test_gold).to_dict(),
    ]
    predictions_by_path = {
        "dev_predictions.jsonl": [
            {"id": "seed-form-email-dev", "prediction": {**dev_gold, "slots": {"field": "email"}}}
        ],
        "test_predictions.jsonl": [
            {
                "id": "seed-open-example-test",
                "prediction": {**test_gold, "normalized_command": "访问示例网站"},
            }
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    gold_path = tmp_path / "all_sft_rows.jsonl"
    output_dir = tmp_path / "out"
    write_json(manifest_path, _source_manifest())
    gold_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in all_rows) + "\n",
        encoding="utf-8",
    )
    for name, rows in predictions_by_path.items():
        (tmp_path / name).write_text(
            "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
            encoding="utf-8",
        )

    assert (
        eval_cli.main(
            [
                "diagnose-merged-slot-value-residuals",
                "--merged-manifest",
                manifest_path.as_posix(),
                "--dev-gold",
                gold_path.as_posix(),
                "--dev-predictions",
                (tmp_path / "dev_predictions.jsonl").as_posix(),
                "--test-gold",
                gold_path.as_posix(),
                "--test-predictions",
                (tmp_path / "test_predictions.jsonl").as_posix(),
                "--output",
                output_dir.as_posix(),
            ]
        )
        == 0
    )
    cli_output = json.loads(capsys.readouterr().out)
    assert cli_output["ok"] is True
    diagnosis = json.loads((output_dir / "merged_slot_value_residual_diagnosis.json").read_text(encoding="utf-8"))
    assert diagnosis["summary"]["residual_row_count"] == 2
    assert diagnosis["aggregates"]["by_split_residual_rows"] == {"dev": 1, "test": 1}
    assert scan_paths([output_dir]).ok is True
