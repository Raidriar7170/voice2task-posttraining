import json
from pathlib import Path

from voice2task import evaluation, reports
from voice2task.cli import eval as eval_cli
from voice2task.evaluation import (
    evaluate_predictions,
    prompt_fixture_predictions,
    rule_baseline_predictions,
    run_execution_smoke,
)
from voice2task.io import write_jsonl
from voice2task.reports import write_metrics_report
from voice2task.schemas import BrowserTaskContract, SFTDatasetRow


def _row(row_id: str, route: str, query: str) -> SFTDatasetRow:
    return SFTDatasetRow(
        id=row_id,
        split="test",
        input_text=f"帮我搜索{query}",
        target_contract=BrowserTaskContract(
            task_type="search",
            route=route,
            safety={"allow": True, "reason": "public_readonly"},
            confirmation_required=False,
            slots={"query": query},
            normalized_command=f"搜索{query}",
        ),
        provenance={"source_id": row_id, "public_safe": True},
    )


def _row_with_split(row_id: str, split: str, task_type: str, route: str, slots: dict[str, object]) -> SFTDatasetRow:
    return SFTDatasetRow(
        id=row_id,
        split=split,
        input_text=f"帮我处理{row_id}",
        target_contract=BrowserTaskContract(
            task_type=task_type,
            route=route,
            safety={"allow": True, "reason": "public_readonly"},
            confirmation_required=False,
            slots=slots,
            normalized_command=f"处理{row_id}",
        ),
        provenance={"source_id": row_id, "public_safe": True},
    )


def test_evaluator_computes_contract_metrics_and_failure_slices() -> None:
    rows = [_row("gold-1", "search_web", "机票"), _row("gold-2", "search_web", "酒店")]
    predictions = {
        "gold-1": rows[0].target_contract.to_dict(),
        "gold-2": {
            **rows[1].target_contract.to_dict(),
            "route": "open_url",
            "slots": {"query": "民宿"},
        },
    }

    result = evaluate_predictions(rows, predictions)

    assert result.metrics["json_valid_rate"] == 1.0
    assert result.metrics["task_type_accuracy"] == 1.0
    assert result.metrics["route_accuracy"] == 0.5
    assert result.metrics["slot_f1"] < 1.0
    assert result.metrics["contract_exact_match"] == 0.5
    assert result.failure_slices["route"]["count"] == 1
    assert result.failure_slices["slot"]["examples"] == ["gold-2"]


def test_evaluator_rejects_predictions_missing_required_contract_fields() -> None:
    rows = [_row("gold-1", "search_web", "天气")]
    incomplete_prediction = {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "normalized_command": "搜索天气",
    }

    result = evaluate_predictions(rows, {"gold-1": incomplete_prediction})

    assert result.metrics["json_valid_rate"] == 0.0
    assert result.failure_slices["schema"]["count"] == 1


def test_schema_diagnostics_explain_contract_like_mismatches(tmp_path: Path) -> None:
    rows = [
        _row("missing-slots", "search_web", "天气"),
        _row("bad-task-type", "search_web", "机票"),
        _row("bad-route", "search_web", "酒店"),
        _row("slots-list", "search_web", "新闻"),
        _row("empty-safety-reason", "search_web", "地图"),
        _row("non-bool-safety-allow", "search_web", "日历"),
        _row("non-bool-confirmation", "search_web", "航班"),
        _row("bad-language", "search_web", "新闻"),
        _row("bad-contract-version", "search_web", "汇率"),
        _row("empty-normalized-command", "search_web", "翻译"),
        _row("non-string-normalized-command", "search_web", "汇率"),
    ]
    base = rows[0].target_contract.to_dict()
    predictions = {
        "missing-slots": {key: value for key, value in base.items() if key != "slots"},
        "bad-task-type": {**base, "task_type": "browser_task"},
        "bad-route": {**base, "route": "search"},
        "slots-list": {**base, "slots": ["query", "新闻"]},
        "empty-safety-reason": {**base, "safety": {"allow": True, "reason": ""}},
        "non-bool-safety-allow": {**base, "safety": {"allow": "yes", "reason": "public_readonly"}},
        "non-bool-confirmation": {**base, "confirmation_required": "false"},
        "bad-language": {**base, "language": "en-US"},
        "bad-contract-version": {**base, "contract_version": "v2"},
        "empty-normalized-command": {**base, "normalized_command": " "},
        "non-string-normalized-command": {**base, "normalized_command": {"text": "搜索汇率"}},
    }

    diagnostics = evaluation.diagnose_schema_mismatches(rows, predictions)

    assert diagnostics["summary"]["invalid_prediction_count"] == 11
    issues = {
        (issue["row_id"], issue["field_path"], issue["issue_category"])
        for row in diagnostics["rows"]
        for issue in row["issues"]
    }
    assert ("missing-slots", "slots", "missing_required_field") in issues
    assert ("bad-task-type", "task_type", "invalid_enum") in issues
    assert ("bad-route", "route", "invalid_enum") in issues
    assert ("slots-list", "slots", "invalid_type") in issues
    assert ("empty-safety-reason", "safety.reason", "empty_required_string") in issues
    assert ("non-bool-safety-allow", "safety.allow", "invalid_type") in issues
    assert ("non-bool-confirmation", "confirmation_required", "invalid_type") in issues
    assert ("bad-language", "language", "invalid_literal") in issues
    assert ("bad-contract-version", "contract_version", "invalid_literal") in issues
    assert ("empty-normalized-command", "normalized_command", "empty_required_string") in issues
    assert ("non-string-normalized-command", "normalized_command", "invalid_type") in issues
    assert all("observed_value_summary" in issue for row in diagnostics["rows"] for issue in row["issues"])
    assert all("expected_constraint" in issue for row in diagnostics["rows"] for issue in row["issues"])

    paths = reports.write_schema_diagnostics_report(
        diagnostics,
        output_dir=tmp_path,
        title="Post-recovery schema diagnostics",
    )
    report = paths["markdown"].read_text(encoding="utf-8")
    assert "invalid predictions remain invalid" in report
    assert "not a checkpoint release" in report
    assert "not an adapter release" in report
    assert "no production-readiness claim" in report
    assert "no full-private-corpus claim" in report
    assert "not a live-browser benchmark" in report


def test_diagnose_schema_cli_writes_public_safe_json_and_markdown(tmp_path: Path) -> None:
    row = _row("gold-1", "search_web", "天气")
    gold = tmp_path / "gold.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    output = tmp_path / "diagnostics"
    write_jsonl(gold, [row.to_dict()])
    write_jsonl(
        predictions,
        [
            {
                "id": "gold-1",
                "prediction": {
                    "task_type": "browser_task",
                    "route": "search_web",
                    "safety": {"allow": True, "reason": "public_readonly"},
                    "confirmation_required": False,
                    "slots": {"query": "天气"},
                    "normalized_command": "搜索天气",
                    "language": "zh-CN",
                    "contract_version": "v1",
                },
            }
        ],
    )

    assert (
        eval_cli.main(
            [
                "diagnose-schema",
                "--gold",
                gold.as_posix(),
                "--predictions",
                predictions.as_posix(),
                "--output",
                output.as_posix(),
            ]
        )
        == 0
    )

    diagnostics = json.loads((output / "schema_diagnostics.json").read_text(encoding="utf-8"))
    markdown = (output / "schema_diagnostics.md").read_text(encoding="utf-8")
    assert diagnostics["rows"][0]["issues"][0]["field_path"] == "task_type"
    assert diagnostics["rows"][0]["issues"][0]["issue_category"] == "invalid_enum"
    assert "invalid predictions remain invalid" in markdown


def test_constrained_decoding_diagnosis_counts_retry_failure_families(tmp_path: Path) -> None:
    valid_contract = _row("strict-valid", "search_web", "机票").target_contract.to_dict()
    invalid_contract = {
        "task_type": "search_web",
        "route": "open_url",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": "天气"},
        "normalized_command": "搜索天气",
        "language": "zh-CN",
        "contract_version": "v1",
    }
    wrapped_retry = (
        "这是修复后的 Browser Task Contract:\n```json\n"
        + json.dumps(
            {
                "task_type": "query_weather_request",
                "route": "/weather/query_weather_request",
                "safety": {"allow": True, "reason": "public_readonly"},
                "confirmation_required": False,
                "slots": {"city": "北京"},
                "normalized_command": "查询北京天气",
                "language": "zh-CN",
                "contract_version": "v1",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n```\n"
    )
    raw_summary_rows = [
        {
            "id": "wrapped-invalid",
            "raw_attempt": {
                "parse_status": "json_object",
                "decoded_prefix": json.dumps(invalid_contract, ensure_ascii=False, sort_keys=True),
                "decoded_suffix": json.dumps(invalid_contract, ensure_ascii=False, sort_keys=True),
            },
            "retry_attempt": {
                "parse_status": "json_fragment_object",
                "decoded_prefix": wrapped_retry,
                "decoded_suffix": wrapped_retry,
            },
            "schema_guard": {
                "raw_attempt_schema_valid": False,
                "retry_attempt_schema_valid": False,
                "validated_output_schema_valid": False,
            },
        },
        {
            "id": "strict-valid",
            "raw_attempt": {
                "parse_status": "json_object",
                "decoded_prefix": json.dumps({"task_type": "search"}, ensure_ascii=False),
                "decoded_suffix": json.dumps({"task_type": "search"}, ensure_ascii=False),
            },
            "retry_attempt": {
                "parse_status": "json_object",
                "decoded_prefix": json.dumps(valid_contract, ensure_ascii=False, sort_keys=True),
                "decoded_suffix": json.dumps(valid_contract, ensure_ascii=False, sort_keys=True),
            },
            "schema_guard": {
                "raw_attempt_schema_valid": False,
                "retry_attempt_schema_valid": True,
                "validated_output_schema_valid": True,
            },
        },
    ]

    diagnostics = evaluation.diagnose_constrained_contract_decoding(
        {"wrapped-invalid": invalid_contract, "strict-valid": valid_contract},
        raw_summary_rows,
    )

    summary = diagnostics["summary"]
    assert diagnostics["diagnostic_kind"] == "constrained_contract_decoding_diagnosis"
    assert summary["prediction_count"] == 2
    assert summary["raw_attempt_schema_valid_count"] == 0
    assert summary["retry_attempt_schema_valid_count"] == 1
    assert summary["validated_output_schema_valid_count"] == 1
    assert summary["parse_status_counts"]["raw_attempt"]["json_object"] == 2
    assert summary["parse_status_counts"]["retry_attempt"]["json_fragment_object"] == 1
    assert summary["legacy_task_type_alias_count"] == 2
    assert summary["path_like_route_count"] == 1
    assert summary["prose_markdown_wrapper_count"] == 1
    assert diagnostics["claims"]["local_decoder_output_shape_hardening_only"] is True
    assert diagnostics["claims"]["does_not_coerce_or_replace_invalid_predictions"] is True
    assert diagnostics["claims"]["held_out_generalization_claim"] is False

    paths = reports.write_constrained_decoding_diagnosis_report(
        diagnostics,
        output_dir=tmp_path,
        title="Constrained decoding diagnosis",
    )
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "Constrained decoding diagnosis" in markdown
    assert "local decoder/output-shape hardening" in markdown
    assert "invalid predictions remain invalid" in markdown
    assert "not a model recovery claim" in markdown


def test_diagnose_constrained_decoding_cli_writes_public_safe_json_and_markdown(tmp_path: Path) -> None:
    prediction = {
        "task_type": "search_web",
        "route": "open_url",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": "天气"},
        "normalized_command": "搜索天气",
        "language": "zh-CN",
        "contract_version": "v1",
    }
    predictions = tmp_path / "predictions.jsonl"
    raw_decoded_summary = tmp_path / "raw_decoded_summary.jsonl"
    output = tmp_path / "constrained"
    write_jsonl(predictions, [{"id": "row-1", "prediction": prediction}])
    write_jsonl(
        raw_decoded_summary,
        [
            {
                "id": "row-1",
                "raw_attempt": {
                    "parse_status": "json_object",
                    "decoded_prefix": json.dumps(prediction, ensure_ascii=False, sort_keys=True),
                    "decoded_suffix": json.dumps(prediction, ensure_ascii=False, sort_keys=True),
                },
                "retry_attempt": {
                    "parse_status": "json_fragment_object",
                    "decoded_prefix": "```json\n{\"task_type\":\"search_web\",\"route\":\"/weather\"}\n```",
                    "decoded_suffix": "```json\n{\"task_type\":\"search_web\",\"route\":\"/weather\"}\n```",
                },
                "schema_guard": {
                    "raw_attempt_schema_valid": False,
                    "retry_attempt_schema_valid": False,
                    "validated_output_schema_valid": False,
                },
            }
        ],
    )

    assert (
        eval_cli.main(
            [
                "diagnose-constrained-decoding",
                "--predictions",
                predictions.as_posix(),
                "--raw-decoded-summary",
                raw_decoded_summary.as_posix(),
                "--output",
                output.as_posix(),
            ]
        )
        == 0
    )

    diagnostics = json.loads((output / "constrained_decoding_diagnosis.json").read_text(encoding="utf-8"))
    markdown = (output / "constrained_decoding_diagnosis.md").read_text(encoding="utf-8")
    assert diagnostics["summary"]["prediction_count"] == 1
    assert diagnostics["summary"]["validated_output_schema_valid_count"] == 0
    assert diagnostics["summary"]["prose_markdown_wrapper_count"] == 1
    assert "invalid predictions remain invalid" in markdown
    assert "not a checkpoint release" in markdown


def test_diagnose_constrained_decoding_cli_can_label_a100_prediction_rerun_evidence(
    tmp_path: Path,
) -> None:
    prediction = {
        "task_type": "search_web",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": "天气"},
        "normalized_command": "搜索天气",
        "language": "zh-CN",
        "contract_version": "v1",
    }
    predictions = tmp_path / "predictions.jsonl"
    raw_decoded_summary = tmp_path / "raw_decoded_summary.jsonl"
    output = tmp_path / "constrained"
    decoded = json.dumps(prediction, ensure_ascii=False, sort_keys=True)
    write_jsonl(predictions, [{"id": "row-1", "prediction": prediction}])
    write_jsonl(
        raw_decoded_summary,
        [
            {
                "id": "row-1",
                "raw_attempt": {
                    "parse_status": "json_object",
                    "decoded_prefix": decoded,
                    "decoded_suffix": decoded,
                },
                "retry_attempt": None,
                "schema_guard": {
                    "raw_attempt_schema_valid": True,
                    "retry_attempt_schema_valid": None,
                    "validated_output_schema_valid": True,
                },
            }
        ],
    )

    assert (
        eval_cli.main(
            [
                "diagnose-constrained-decoding",
                "--predictions",
                predictions.as_posix(),
                "--raw-decoded-summary",
                raw_decoded_summary.as_posix(),
                "--output",
                output.as_posix(),
                "--evidence-context",
                "a100_prediction_rerun",
            ]
        )
        == 0
    )

    diagnostics = json.loads((output / "constrained_decoding_diagnosis.json").read_text(encoding="utf-8"))
    markdown = (output / "constrained_decoding_diagnosis.md").read_text(encoding="utf-8")
    assert diagnostics["claims"]["evidence_context"] == "a100_prediction_rerun"
    assert diagnostics["claims"]["a100_prediction_rerun_evidence"] is True
    assert diagnostics["claims"]["local_decoder_output_shape_hardening_only"] is False
    assert "A100 prediction-rerun evidence" in markdown
    assert "local decoder/output-shape hardening evidence only" not in markdown


def test_alignment_diagnostics_compare_raw_invalid_prediction_fields(tmp_path: Path) -> None:
    row = _row("gold-1", "search_web", "天气")
    prediction = {
        "task_type": "normalization",
        "route": "/search",
        "safety": {"allow": "yes", "reason": "allowed"},
        "confirmation_required": "false",
        "slots": ["query", "天气"],
        "normalized_command": "查天气",
        "language": "en-US",
        "contract_version": "v2",
    }

    diagnostics = evaluation.diagnose_alignment_mismatches([row], {"gold-1": prediction})

    assert diagnostics["diagnostic_kind"] == "browser_task_contract_alignment_mismatch"
    assert diagnostics["summary"]["gold_row_count"] == 1
    assert diagnostics["summary"]["prediction_count"] == 1
    assert diagnostics["summary"]["row_mismatch_count"] == 1
    assert diagnostics["summary"]["schema_invalid_prediction_count"] == 1
    assert diagnostics["summary"]["field_mismatch_counts"]["slots"] == 1
    assert diagnostics["claims"]["invalid_predictions_remain_invalid"] is True

    mismatches = diagnostics["rows"][0]["mismatches"]
    mismatch_paths = {mismatch["field_path"] for mismatch in mismatches}
    assert mismatch_paths == {
        "task_type",
        "route",
        "safety.allow",
        "safety.reason",
        "confirmation_required",
        "slots",
        "normalized_command",
        "language",
        "contract_version",
    }
    assert all(mismatch["row_id"] == "gold-1" for mismatch in mismatches)
    assert all("mismatch_category" in mismatch for mismatch in mismatches)
    assert all("gold_value_summary" in mismatch for mismatch in mismatches)
    assert all("prediction_value_summary" in mismatch for mismatch in mismatches)

    paths = reports.write_alignment_diagnostics_report(
        diagnostics,
        output_dir=tmp_path,
        title="Post-recovery alignment diagnostics",
    )
    report = paths["markdown"].read_text(encoding="utf-8")
    assert "invalid predictions remain invalid" in report
    assert "field-level public-sample evidence only" in report
    assert "not a checkpoint release" in report
    assert "not an adapter release" in report
    assert "no production-readiness claim" in report
    assert "no full-private-corpus claim" in report
    assert "not a live-browser benchmark" in report


def test_confirmation_rerun_row_mismatch_diagnosis_buckets_three_residual_failures(
    tmp_path: Path,
) -> None:
    rows = [
        SFTDatasetRow(
            id=row_id,
            split="train",
            input_text=input_text,
            target_contract=BrowserTaskContract(
                task_type="search",
                route="search_web",
                safety={"allow": True, "reason": "public_readonly"},
                confirmation_required=False,
                slots={"query": "北京 明天 天气"},
                normalized_command="搜索北京明天天气",
            ),
            provenance={"source_id": "seed-search-weather", "public_safe": True},
        )
        for row_id, input_text in (
            ("seed-search-weather", "帮我搜索北京明天的天气"),
            ("seed-search-weather-aug-1", "查一下北京明天天气"),
            ("seed-search-weather-aug-2", "搜北京明天的天气"),
        )
    ]
    predictions = {
        "seed-search-weather": {
            "task_type": "search",
            "route": "search_web",
            "safety": {"allow": True, "reason": "public_readonly"},
            "slots": {"query": "北京 明天 天气"},
            "normalized_command": "搜索北京明天的天气",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        "seed-search-weather-aug-1": {
            "task_type": "form_fill",
            "route": "open_url",
            "safety": {"allow": True, "reason": "form_fill"},
            "confirmation_required": False,
            "slots": {"query": "北京 明天 天气"},
            "normalized_command": "查询北京明天天气",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        "seed-search-weather-aug-2": {
            "task_type": "search",
            "route": "search_web",
            "safety": {"allow": True, "reason": "public_readonly"},
            "confirmation_required": False,
            "slots": {"query": "北京 明天 天气"},
            "normalized_command": "搜索北京明天的天气",
            "language": "zh-CN",
            "contract_version": "v1",
        },
    }
    metrics = {
        "metrics": {
            "json_valid_rate": 2 / 3,
            "task_type_accuracy": 1 / 3,
            "route_accuracy": 1 / 3,
            "confirmation_accuracy": 2 / 3,
            "slot_f1": 2 / 3,
            "contract_exact_match": 0.0,
        }
    }
    schema_guard_summary = {
        "summary": {
            "validated_output_schema_valid_count": 2,
            "validated_output_source_counts": {"none": 1, "raw_attempt": 2},
        },
        "rows": [
            {
                "id": "seed-search-weather",
                "raw_attempt_missing_required_fields": ["confirmation_required"],
                "validated_output_schema_valid": False,
                "validated_output_source": "none",
            },
            {
                "id": "seed-search-weather-aug-1",
                "raw_attempt_missing_required_fields": [],
                "validated_output_schema_valid": True,
                "validated_output_source": "raw_attempt",
            },
            {
                "id": "seed-search-weather-aug-2",
                "raw_attempt_missing_required_fields": [],
                "validated_output_schema_valid": True,
                "validated_output_source": "raw_attempt",
            },
        ],
    }
    prior_dir = "reports/public-sample/a100-confirmation-required-train-split-rerun"

    diagnosis = evaluation.diagnose_confirmation_rerun_row_mismatches(
        rows,
        predictions,
        metrics=metrics,
        schema_guard_summary=schema_guard_summary,
        source_artifacts={
            "train_split_gold": f"{prior_dir}/train_split_gold.jsonl",
            "predictions": f"{prior_dir}/predictions.jsonl",
            "metrics": f"{prior_dir}/metrics.json",
            "schema_guard_summary": f"{prior_dir}/schema_guard_summary.json",
            "manifest": f"{prior_dir}/manifest.json",
        },
    )

    assert diagnosis["diagnostic_kind"] == "confirmation_required_rerun_row_mismatch_diagnosis"
    assert diagnosis["summary"]["gold_row_count"] == 3
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["row_mismatch_count"] == 3
    assert diagnosis["summary"]["schema_invalid_prediction_count"] == 1
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 2 / 3
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
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
    assert diagnosis["claims"]["local_evidence_only_analysis"] is True
    assert diagnosis["claims"]["does_not_repair_normalize_coerce_replace_or_rescore"] is True
    assert diagnosis["claims"]["held_out_generalization_claim"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False

    paths = reports.write_confirmation_rerun_row_mismatch_report(diagnosis, output_dir=tmp_path)
    report = paths["markdown"].read_text(encoding="utf-8")
    assert paths["json"].name == "row_mismatch_diagnosis.json"
    assert paths["markdown"].name == "row_mismatch_diagnosis.md"
    assert "local evidence-only analysis" in report
    assert "does not repair, normalize, coerce, replace, or re-score predictions" in report
    assert "missing_required_field_schema_failure" in report
    assert "strict_string_field_exact_match_mismatch" in report


def test_a100_normalized_rerun_row_mismatch_diagnosis_buckets_residual_schema_and_route_failures(
    tmp_path: Path,
) -> None:
    rows = [
        SFTDatasetRow(
            id=row_id,
            split="train",
            input_text=input_text,
            target_contract=BrowserTaskContract(
                task_type="search",
                route="search_web",
                safety={"allow": True, "reason": "public_readonly"},
                confirmation_required=False,
                slots={"query": "北京 明天 天气"},
                normalized_command="搜索北京明天天气",
            ),
            provenance={"source_id": "seed-search-weather", "public_safe": True},
        )
        for row_id, input_text in (
            ("seed-search-weather", "帮我搜索北京明天的天气"),
            ("seed-search-weather-aug-1", "查一下北京明天天气"),
            ("seed-search-weather-aug-2", "搜北京明天的天气"),
        )
    ]
    predictions = {
        "seed-search-weather": {
            "task_type": "search",
            "route": "search_web",
            "safety": {"allow": True, "reason": "public_readonly"},
            "slots": {"city": "北京", "date": "明天"},
            "normalized_command": "搜索北京明天的天气",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        "seed-search-weather-aug-1": {
            "task_type": "form_fill",
            "route": "open_url",
            "safety": {"allow": True, "reason": "form_fill"},
            "confirmation_required": False,
            "slots": {"query": "北京明天天气"},
            "normalized_command": "搜索北京明天天气",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        "seed-search-weather-aug-2": {
            "task_type": "search_web",
            "route": "search_web",
            "safety": {"allow": True, "reason": "open_url"},
            "confirmation_required": False,
            "slots": {"query": "北京明天天气"},
            "normalized_command": "搜索北京明天天气",
            "language": "zh-CN",
            "contract_version": "v1",
        },
    }
    metrics = {
        "metrics": {
            "json_valid_rate": 1 / 3,
            "task_type_accuracy": 0.0,
            "route_accuracy": 0.0,
            "confirmation_accuracy": 1 / 3,
            "slot_f1": 0.0,
            "contract_exact_match": 0.0,
        },
        "normalized_command_counts": {
            "exact_match_count": 2,
            "mismatch_count": 1,
        },
    }
    schema_guard_summary = {
        "summary": {
            "normalized_command_exact_match_count": 2,
            "normalized_command_mismatch_count": 1,
            "validated_output_schema_valid_count": 1,
        },
        "rows": [
            {
                "id": "seed-search-weather",
                "raw_attempt_missing_required_fields": ["confirmation_required"],
                "raw_attempt_validation_error": "missing required fields: confirmation_required",
                "validated_output_schema_valid": False,
                "validated_output_source": "none",
            },
            {
                "id": "seed-search-weather-aug-1",
                "raw_attempt_missing_required_fields": [],
                "raw_attempt_validation_error": None,
                "validated_output_schema_valid": True,
                "validated_output_source": "raw_attempt",
            },
            {
                "id": "seed-search-weather-aug-2",
                "raw_attempt_missing_required_fields": [],
                "raw_attempt_validation_error": (
                    "task_type must be one of "
                    "['blocked', 'clarify', 'extract', 'form_fill', 'navigate', 'search']"
                ),
                "validated_output_schema_valid": False,
                "validated_output_source": "none",
            },
        ],
    }
    prior_dir = "reports/public-sample/a100-normalized-command-policy-train-split-rerun"

    diagnosis = evaluation.diagnose_a100_normalized_rerun_row_mismatches(
        rows,
        predictions,
        metrics=metrics,
        schema_guard_summary=schema_guard_summary,
        source_artifacts={
            "train_split_gold": f"{prior_dir}/train_split_gold.jsonl",
            "predictions": f"{prior_dir}/predictions.jsonl",
            "metrics": f"{prior_dir}/metrics.json",
            "schema_guard_summary": f"{prior_dir}/schema_guard_summary.json",
            "normalized_command_diagnosis": f"{prior_dir}/normalized_command_diagnosis.json",
            "manifest": f"{prior_dir}/manifest.json",
        },
    )

    assert diagnosis["diagnostic_kind"] == "a100_normalized_rerun_row_mismatch_diagnosis"
    assert diagnosis["summary"]["gold_row_count"] == 3
    assert diagnosis["summary"]["prediction_count"] == 3
    assert diagnosis["summary"]["row_mismatch_count"] == 3
    assert diagnosis["summary"]["schema_invalid_prediction_count"] == 2
    assert diagnosis["summary"]["validated_output_schema_valid_count"] == 1
    assert diagnosis["summary"]["normalized_command_exact_match_count"] == 2
    assert diagnosis["summary"]["normalized_command_mismatch_count"] == 1
    assert diagnosis["summary"]["strict_final_json_valid_rate"] == 1 / 3
    assert diagnosis["summary"]["strict_final_contract_exact_match"] == 0.0
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
    row_families = {row["row_id"]: row["primary_failure_family"] for row in diagnosis["rows"]}
    assert row_families == {
        "seed-search-weather": "schema_missing_confirmation_required",
        "seed-search-weather-aug-1": "schema_valid_task_route_safety_slot_mismatch",
        "seed-search-weather-aug-2": "schema_invalid_task_type_enum",
    }
    assert diagnosis["source_artifact_policy"]["uses_prior_public_sample_artifacts_only"] is True
    assert diagnosis["source_artifact_policy"]["a100_execution_performed"] is False
    assert diagnosis["source_artifact_policy"]["prediction_rerun_performed"] is False
    assert diagnosis["claims"]["local_evidence_only_analysis"] is True
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["normalized_command_normalization_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False

    paths = reports.write_a100_normalized_rerun_row_mismatch_report(diagnosis, output_dir=tmp_path)
    report = paths["markdown"].read_text(encoding="utf-8")
    assert paths["json"].name == "row_mismatch_diagnosis.json"
    assert paths["markdown"].name == "row_mismatch_diagnosis.md"
    assert "local evidence-only analysis" in report
    assert "No A100 execution was performed in this phase" in report
    assert "schema_missing_confirmation_required" in report
    assert "schema_invalid_task_type_enum" in report
    assert "schema_valid_task_route_safety_slot_mismatch" in report


def test_normalized_command_string_mismatch_diagnosis_preserves_strict_boundaries(
    tmp_path: Path,
) -> None:
    source_dir = Path("reports/public-sample/confirmation-rerun-row-mismatch-diagnosis")
    row_mismatch_diagnosis = json.loads((source_dir / "row_mismatch_diagnosis.json").read_text(encoding="utf-8"))

    diagnosis = evaluation.diagnose_normalized_command_string_mismatches(
        row_mismatch_diagnosis,
        source_artifacts={
            "row_mismatch_diagnosis": (source_dir / "row_mismatch_diagnosis.json").as_posix(),
            "row_mismatch_manifest": (source_dir / "manifest.json").as_posix(),
        },
    )

    assert diagnosis["diagnostic_kind"] == "normalized_command_string_mismatch_diagnosis"
    summary = diagnosis["summary"]
    assert summary["normalized_command_mismatch_count"] == 3
    assert summary["string_only_count"] == 1
    assert summary["co_occurs_with_schema_failure_count"] == 1
    assert summary["co_occurs_with_semantic_task_route_safety_count"] == 1
    assert summary["context_counts"] == {
        "co_occurs_with_schema_failure": 1,
        "co_occurs_with_semantic_task_route_safety": 1,
        "strict_string_only": 1,
    }
    assert summary["strict_metrics_preserved"] is True
    assert summary["strict_final_json_valid_rate"] == row_mismatch_diagnosis["summary"][
        "strict_final_json_valid_rate"
    ]
    assert summary["strict_final_task_type_accuracy"] == row_mismatch_diagnosis["summary"][
        "strict_final_task_type_accuracy"
    ]
    assert summary["strict_final_route_accuracy"] == row_mismatch_diagnosis["summary"][
        "strict_final_route_accuracy"
    ]
    assert summary["strict_final_confirmation_accuracy"] == row_mismatch_diagnosis["summary"][
        "strict_final_confirmation_accuracy"
    ]
    assert summary["strict_final_slot_f1"] == row_mismatch_diagnosis["summary"]["strict_final_slot_f1"]
    assert summary["strict_final_contract_exact_match"] == row_mismatch_diagnosis["summary"][
        "strict_final_contract_exact_match"
    ]

    row_contexts = {row["row_id"]: row["context_kind"] for row in diagnosis["rows"]}
    assert row_contexts == {
        "seed-search-weather": "co_occurs_with_schema_failure",
        "seed-search-weather-aug-1": "co_occurs_with_semantic_task_route_safety",
        "seed-search-weather-aug-2": "strict_string_only",
    }
    assert all(row["mismatch"]["field_path"] == "normalized_command" for row in diagnosis["rows"])
    assert all(row["mismatch"]["mismatch_category"] == "value_mismatch" for row in diagnosis["rows"])
    assert diagnosis["claims"]["local_evidence_only_analysis"] is True
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["normalized_command_normalization_performed"] is False
    assert diagnosis["claims"]["normalized_command_semantic_equivalence_marked"] is False
    assert diagnosis["claims"]["search_query_terms_marked_equivalent"] is False
    assert diagnosis["claims"]["predictions_repaired_or_replaced"] is False
    assert diagnosis["claims"]["predictions_rescored"] is False
    assert diagnosis["claims"]["does_not_repair_normalize_coerce_replace_or_rescore"] is True
    assert diagnosis["source_artifact_policy"]["evaluator_metrics_changed"] is False
    assert diagnosis["source_artifact_policy"]["primary_inputs_are_row_mismatch_artifacts"] is True
    assert diagnosis["source_artifact_policy"]["transitive_rerun_artifacts_are_linked_for_traceability_only"] is True
    assert set(diagnosis["source_artifacts"]) == {"row_mismatch_diagnosis", "row_mismatch_manifest"}
    assert "predictions" in diagnosis["transitive_source_artifacts"]

    paths = reports.write_normalized_command_mismatch_report(diagnosis, output_dir=tmp_path)
    report = paths["markdown"].read_text(encoding="utf-8")
    assert paths["json"].name == "normalized_command_mismatch_diagnosis.json"
    assert paths["markdown"].name == "normalized_command_mismatch_diagnosis.md"
    assert "local evidence-only analysis" in report
    assert "does not normalize or semantically score" in report
    assert "does not mark `搜索/查询` or `明天的天气/明天天气` as equivalent" in report
    assert "does not repair, coerce, replace, or re-score predictions" in report
    assert "Transitive Source Artifacts" in report
    assert "traceability only" in report
    assert "Strict final contract_exact_match remains `0.0`" in report


def test_retry_template_slot_exact_match_mismatch_diagnosis_classifies_slot_shapes(
    tmp_path: Path,
) -> None:
    rows = [
        SFTDatasetRow(
            id=row_id,
            split="train",
            input_text=input_text,
            target_contract=BrowserTaskContract(
                task_type="search",
                route="search_web",
                safety={"allow": True, "reason": "public_readonly"},
                confirmation_required=False,
                slots={"query": "北京 明天 天气"},
                normalized_command="搜索北京明天天气",
            ),
            provenance={"source_id": "seed-search-weather", "public_safe": True},
        )
        for row_id, input_text in (
            ("seed-search-weather", "帮我搜索北京明天的天气"),
            ("seed-search-weather-aug-1", "查一下北京明天天气"),
            ("seed-search-weather-aug-2", "搜北京明天的天气"),
        )
    ]
    predictions = {
        "seed-search-weather": {
            **rows[0].target_contract.to_dict(),
            "normalized_command": "帮我搜索北京明天的天气",
            "slots": {"city": "北京", "date": "明天"},
        },
        "seed-search-weather-aug-1": {
            **rows[1].target_contract.to_dict(),
            "slots": {"city": "北京", "date": "明天"},
        },
        "seed-search-weather-aug-2": {
            **rows[2].target_contract.to_dict(),
            "slots": {"query": "北京明天天气"},
        },
    }
    schema_guard_summary = {
        "summary": {"validated_output_schema_valid_count": 3},
        "rows": [
            {
                "row_id": "seed-search-weather",
                "validated_output_schema_valid": True,
                "validated_output_source": "retry_attempt",
            },
            {
                "row_id": "seed-search-weather-aug-1",
                "validated_output_schema_valid": True,
                "validated_output_source": "raw_attempt",
            },
            {
                "row_id": "seed-search-weather-aug-2",
                "validated_output_schema_valid": True,
                "validated_output_source": "retry_attempt",
            },
        ],
    }
    metrics = {
        "metrics": {
            "json_valid_rate": 1.0,
            "task_type_accuracy": 1.0,
            "route_accuracy": 1.0,
            "confirmation_accuracy": 1.0,
            "slot_f1": 0.0,
            "contract_exact_match": 0.0,
        }
    }

    diagnosis = evaluation.diagnose_retry_template_slot_exact_match_mismatches(
        rows,
        predictions,
        metrics=metrics,
        schema_guard_summary=schema_guard_summary,
        source_artifacts={
            "predictions": "reports/public-sample/a100-retry-template-boundary-rerun/predictions.jsonl",
            "train_split_gold": "reports/public-sample/a100-retry-template-boundary-rerun/train_split_gold.jsonl",
        },
    )

    assert diagnosis["diagnostic_kind"] == "retry_template_slot_exact_match_mismatch_diagnosis"
    summary = diagnosis["summary"]
    assert summary["gold_row_count"] == 3
    assert summary["prediction_count"] == 3
    assert summary["row_mismatch_count"] == 3
    assert summary["schema_invalid_prediction_count"] == 0
    assert summary["validated_output_schema_valid_count"] == 3
    assert summary["field_mismatch_counts"] == {"normalized_command": 1, "slots": 3}
    assert summary["slot_family_counts"] == {
        "city_date_slots_instead_of_query": 2,
        "query_slot_strict_string_mismatch": 1,
    }
    assert summary["normalized_command_mismatch_count"] == 1
    assert summary["strict_final_json_valid_rate"] == 1.0
    assert summary["strict_final_slot_f1"] == 0.0
    assert summary["strict_final_contract_exact_match"] == 0.0

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
    assert diagnosis["claims"]["semantic_equivalence_scoring_performed"] is False
    assert diagnosis["claims"]["prediction_repair_or_rescore_performed"] is False
    assert diagnosis["claims"]["model_quality_improvement_claim"] is False

    paths = reports.write_retry_template_slot_exact_match_mismatch_report(diagnosis, output_dir=tmp_path)
    report = paths["markdown"].read_text(encoding="utf-8")
    assert paths["json"].name == "slot_exact_match_mismatch_diagnosis.json"
    assert paths["markdown"].name == "slot_exact_match_mismatch_diagnosis.md"
    assert "local evidence-only analysis" in report
    assert "No A100 execution was performed in this phase" in report
    assert "city_date_slots_instead_of_query" in report
    assert "query_slot_strict_string_mismatch" in report
    assert "slot normalization" in report


def test_diagnose_alignment_cli_writes_public_safe_json_and_markdown(tmp_path: Path) -> None:
    row = _row("gold-1", "search_web", "天气")
    gold = tmp_path / "gold.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    output = tmp_path / "diagnostics"
    write_jsonl(gold, [row.to_dict()])
    write_jsonl(
        predictions,
        [
            {
                "id": "gold-1",
                "prediction": {
                    "task_type": "normalization",
                    "route": "search_web",
                    "safety": {"allow": True, "reason": "public_readonly"},
                    "confirmation_required": False,
                    "slots": {"query": "天气"},
                    "normalized_command": "搜索天气",
                    "language": "zh-CN",
                    "contract_version": "v1",
                },
            }
        ],
    )

    assert (
        eval_cli.main(
            [
                "diagnose-alignment",
                "--gold",
                gold.as_posix(),
                "--predictions",
                predictions.as_posix(),
                "--output",
                output.as_posix(),
            ]
        )
        == 0
    )

    diagnostics = json.loads((output / "alignment_diagnostics.json").read_text(encoding="utf-8"))
    markdown = (output / "alignment_diagnostics.md").read_text(encoding="utf-8")
    assert diagnostics["rows"][0]["mismatches"][0]["field_path"] == "task_type"
    assert diagnostics["rows"][0]["mismatches"][0]["mismatch_category"] == "value_mismatch"
    assert "field-level public-sample evidence only" in markdown


def test_source_diagnostics_report_targets_prompt_split_prediction_and_decoding_evidence(
    tmp_path: Path,
) -> None:
    rows = [
        _row_with_split("train-search", "train", "search", "search_web", {"query": "天气"}),
        _row_with_split("dev-open", "dev", "navigate", "open_url", {"url": "https://example.com"}),
    ]
    predictions = {
        "train-search": {
            "task_type": "query_weather",
            "route": "/weather/query",
            "safety": {"allow": True, "reason": ""},
            "slots": ["city"],
            "normalized_command": "",
            "language": "zh-CN",
            "contract_version": "v1",
        },
        "dev-open": rows[1].target_contract.to_dict(),
    }

    diagnostics = evaluation.diagnose_source_alignment(
        rows,
        predictions,
        training_config={"dataset_split": "train"},
        prediction_metadata={"prediction_split": "all"},
    )

    assert diagnostics["diagnostic_kind"] == "browser_task_contract_source_alignment"
    assert diagnostics["target_shape"]["path_like_route_count"] == 0
    assert diagnostics["target_shape"]["list_slots_count"] == 0
    assert diagnostics["prediction_symptoms"]["path_like_route_count"] == 1
    assert diagnostics["prediction_symptoms"]["list_slots_count"] == 1
    assert diagnostics["prediction_symptoms"]["schema_invalid_prediction_count"] == 1
    assert diagnostics["prediction_symptoms"]["missing_confirmation_required_count"] == 1
    assert diagnostics["prediction_symptoms"]["invalid_predictions_remain_invalid"] is True
    assert diagnostics["split_coverage"]["configured_training_split"] == "train"
    assert diagnostics["split_coverage"]["configured_prediction_split"] == "all"
    assert diagnostics["split_coverage"]["gold_split_counts"] == {"dev": 1, "train": 1}
    assert diagnostics["split_coverage"]["training_row_count"] == 1
    assert diagnostics["training_coverage"]["task_type_counts"] == {"search": 1}
    assert diagnostics["training_coverage"]["route_counts"] == {"search_web": 1}
    assert diagnostics["current_prompt_constraints"]["task_type_enum_visible"] is True
    assert diagnostics["current_prompt_constraints"]["route_enum_visible"] is True
    assert diagnostics["current_prompt_constraints"]["route_not_url_or_path_visible"] is True
    assert diagnostics["current_prompt_constraints"]["route_execution_channel_visible"] is True
    assert diagnostics["current_prompt_constraints"]["route_domain_values_not_route_visible"] is True
    assert diagnostics["current_prompt_constraints"]["weather_to_search_route_example_visible"] is True
    assert diagnostics["current_prompt_constraints"]["confirmation_required_boolean_visible"] is True
    assert diagnostics["current_prompt_constraints"]["weather_to_search_confirmation_false_visible"] is True
    assert diagnostics["current_prompt_constraints"]["slots_object_not_array_visible"] is True
    assert diagnostics["prediction_run_prompt_evidence"]["prompt_constraints_present"] is False
    assert "prompt_constraints_at_prediction_time" in diagnostics["prediction_run_prompt_evidence"]["evidence_gaps"]
    assert (
        diagnostics["prediction_run_prompt_evidence"][
            "current_prompt_constraints_are_rerun_preparation_not_old_run_evidence"
        ]
        is True
    )
    assert diagnostics["decoding_evidence"]["decoding_policy_present"] is False
    assert "raw_decoded_sidecar" in diagnostics["decoding_evidence"]["evidence_gaps"]
    assert "generated_token_count" in diagnostics["decoding_evidence"]["evidence_gaps"]
    assert "eos_or_finish_state" in diagnostics["decoding_evidence"]["evidence_gaps"]
    assert diagnostics["claims"]["does_not_repair_normalize_coerce_or_replace_predictions"] is True

    paths = reports.write_source_diagnostics_report(
        diagnostics,
        output_dir=tmp_path,
        title="Source diagnostics",
    )
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "Source diagnostics" in markdown
    assert "invalid predictions remain invalid" in markdown
    assert "does not repair, normalize, coerce, or replace predictions" in markdown
    assert "route is not a URL/path" in markdown
    assert "route execution-channel ontology visible: `True`" in markdown
    assert "route domain/topic values excluded from route visible: `True`" in markdown
    assert "weather-to-search route example visible: `True`" in markdown
    assert "confirmation_required boolean visible: `True`" in markdown
    assert "weather-to-search confirmation false visible: `True`" in markdown
    assert "Missing `confirmation_required`: `1`" in markdown
    assert "Current Prompt Constraints" in markdown
    assert "Prediction-Run Prompt Evidence" in markdown
    assert "prompt_constraints_at_prediction_time" in markdown
    assert "raw_decoded_sidecar" in markdown
    assert "missing evidence, not inferred cause" in markdown
    assert "not a checkpoint release" in markdown


def test_source_diagnostics_include_sft_target_template_alignment_evidence(tmp_path: Path) -> None:
    rows = [
        _row_with_split("train-search", "train", "search", "search_web", {"query": "天气"}),
        _row_with_split("dev-open", "dev", "navigate", "open_url", {"url": "https://example.com"}),
    ]
    prediction_metadata = {
        "base_model": "<private_base_model>",
        "model_source": "modelscope",
        "stack": "transformers+peft+trl",
        "prediction_split": "train",
        "prediction_source_kind": "private_a100_adapter",
        "adapter_release_status": "not_released",
        "prediction_gate": {
            "adapter_configured": True,
            "cli_run_prediction": True,
            "config_allow_private_prediction": True,
            "fixture_mode": False,
            "will_run_private_prediction": True,
        },
        "formatting_policy": {
            "policy": "shared_contract_chat_template",
            "sft_training_text": "shared_contract_chat_template",
            "prediction_prompt": "shared_contract_chat_template",
            "tokenizer_chat_template": "used_when_available_with_tokenize_false",
            "fallback": {
                "mode": "deterministic_role_plain_text",
                "debug_path": "/" + "Users/example/private/tokenizer",
            },
            "prediction_target_policy": "generation_prompt_without_gold_contract",
            "private_debug_path": "/" + "Users/example/private/tokenizer",
        },
        "diagnostic_artifacts": {
            "objective_inspection": "reports/public-sample/prior/objective_inspection.json",
            "leak_scan": "reports/public-sample/prior/leak_scan_result.json",
        },
        "sidecars": {"prompt_snapshot": "reports/public-sample/prior/prompt_snapshot.json"},
    }

    diagnostics = evaluation.diagnose_source_alignment(
        rows,
        {"train-search": rows[0].target_contract.to_dict()},
        training_config={
            "base_model": "Qwen/Qwen2.5-0.5B-Instruct",
            "model_source": "modelscope",
            "dataset_split": "train",
            "prediction_split": "train",
            "adapter_path": "<a100_project_root>/runs/adapter",
        },
        prediction_metadata=prediction_metadata,
        prior_artifact_paths={
            "predictions": "reports/public-sample/prior/predictions.jsonl",
            "metrics": "reports/public-sample/prior/metrics.json",
            "report": "reports/public-sample/prior/report.md",
        },
        objective_inspection={
            "inspection_status": "tokenizer_unavailable",
            "prompt_tokens_masked": True,
            "assistant_tokens_carry_loss": True,
        },
    )

    alignment = diagnostics["sft_target_template_alignment"]
    assert alignment["summary"]["diagnostic_status"] == "public_safe_structural_evidence"
    assert alignment["summary"]["row_count"] == 1
    assert alignment["summary"]["all_rows_share_system_user_prefix"] is False
    assert alignment["summary"]["all_rows_share_core_system_user_prefix"] is True
    assert alignment["summary"]["all_prediction_prompts_include_prediction_output_boundary"] is True
    assert alignment["summary"]["all_training_text_contains_assistant_target"] is True
    assert alignment["summary"]["all_prediction_prompts_exclude_assistant_target"] is True
    assert alignment["summary"]["evidence_gaps"] == []
    assert diagnostics["prediction_symptoms"]["schema_invalid_prediction_count"] == 0
    assert diagnostics["prediction_symptoms"]["missing_prediction_count"] == 1
    assert alignment["label_mask_evidence"]["status"] == "labels_unavailable"
    assert alignment["label_mask_evidence"]["true_label_mask_status"] == "unavailable"
    assert "real_training_label_provenance_missing" in alignment["label_mask_evidence"]["evidence_gaps"]
    assert alignment["chat_template_evidence"]["rendering_source"] == "fallback"
    assert "tokenizer_chat_template_not_loaded" in alignment["chat_template_evidence"]["evidence_gaps"]
    assert alignment["metadata_alignment"]["base_model"]["prediction_metadata"] == "<private_base_model>"
    assert alignment["metadata_alignment"]["base_model"]["status"] == "prediction_metadata_private_placeholder"
    assert alignment["metadata_alignment"]["model_source"]["matches"] is True
    assert alignment["metadata_alignment"]["prediction_split"]["matches"] is True
    assert alignment["metadata_alignment"]["formatting_policy"]["matches"] is False
    fallback_policy = alignment["metadata_alignment"]["formatting_policy"]["prediction_metadata"]["fallback"]
    assert fallback_policy["mode"] == "deterministic_role_plain_text"
    assert fallback_policy["debug_path"] == "<private_value>"
    assert alignment["metadata_alignment"]["adapter_gate"]["adapter_configured"] is True
    assert alignment["metadata_alignment"]["adapter_release_status"] == "not_released"
    assert alignment["metadata_alignment"]["prediction_source_kind"] == "private_a100_adapter"
    assert "private_debug_path" not in alignment["metadata_alignment"]["formatting_policy"]["prediction_metadata"]
    assert alignment["prior_artifacts"]["predictions"] == "reports/public-sample/prior/predictions.jsonl"
    assert (
        alignment["prior_artifacts"]["objective_inspection"]
        == "reports/public-sample/prior/objective_inspection.json"
    )
    assert alignment["claims"]["does_not_run_private_prediction"] is True
    assert alignment["claims"]["does_not_prove_dev_test_generalization"] is True

    row = alignment["rows"][0]
    assert row["row_id"] == "train-search"
    assert row["same_system_user_prefix"] is False
    assert row["same_core_system_user_prefix"] is True
    assert row["prediction_only_boundary_suffix_visible"] is True
    assert row["assistant_contract_target_in_training_text"] is True
    assert row["assistant_contract_target_in_prediction_prompt"] is False
    assert row["assistant_target_span"]["status"] == "found"
    assert row["structural_proxy_status"] == "assistant_target_span_found"
    assert row["prediction_prompt_ends_with_generation_boundary"] is True
    assert row["training_text_sha256"]
    assert row["prediction_prompt_sha256"]
    assert row["assistant_contract_target_sha256"]
    assert row["training_text_char_count"] > 0
    assert row["prediction_prompt_char_count"] > 0
    assert row["training_text_char_count"] != row["prediction_prompt_char_count"]
    assert "training_text" not in row
    assert "prediction_prompt" not in row
    assert "assistant_contract_target" not in row

    paths = reports.write_source_diagnostics_report(diagnostics, output_dir=tmp_path, title="Source diagnostics")
    alignment_json = json.loads(paths["sft_target_template_alignment_json"].read_text(encoding="utf-8"))
    alignment_markdown = paths["sft_target_template_alignment_markdown"].read_text(encoding="utf-8")
    assert alignment_json["summary"]["row_count"] == 1
    assert "training_text" not in alignment_json["rows"][0]
    assert "SFT Target-Template Alignment" in alignment_markdown
    assert "Same core system/user prefix" in alignment_markdown
    assert "Prediction output boundary visible" in alignment_markdown
    assert "labels_unavailable" in alignment_markdown
    assert "tokenizer_chat_template_not_loaded" in alignment_markdown
    assert "does not run private prediction" in alignment_markdown
    assert "帮我处理train-search" not in alignment_markdown
    assert "private_debug_path" not in alignment_markdown


def test_label_provenance_fixture_trl_collator_labels_do_not_count_as_real_proof() -> None:
    rows = [_row_with_split("train-search", "train", "search", "search_web", {"query": "天气"})]

    diagnostics = evaluation.diagnose_source_alignment(
        rows,
        {"train-search": rows[0].target_contract.to_dict()},
        training_config={"dataset_split": "train", "prediction_split": "train"},
        prediction_metadata={"prediction_split": "train"},
        objective_inspection={
            "inspection_status": "inspectable",
            "label_source": "trl_collator_labels",
            "label_provenance": {"source_kind": "fixture", "real_training_path": False},
            "label_tensor_available": True,
            "prompt_token_count": 12,
            "assistant_token_count": 5,
            "prompt_tokens_masked": True,
            "assistant_tokens_carry_loss": True,
            "evidence_gaps": ["fixture_labels_not_real_training_proof"],
        },
    )

    label_mask = diagnostics["sft_target_template_alignment"]["label_mask_evidence"]
    assert label_mask["status"] == "labels_unavailable"
    assert label_mask["true_label_mask_status"] == "fixture_only"
    assert label_mask["label_source"] == "trl_collator_labels"
    assert label_mask["label_provenance"]["source_kind"] == "fixture"
    assert label_mask["label_tensor_available"] is True
    assert label_mask["prompt_tokens_masked"] is None
    assert label_mask["assistant_tokens_carry_loss"] is None
    assert "fixture_labels_not_real_training_proof" in label_mask["evidence_gaps"]
    assert "real_training_label_provenance_missing" in label_mask["evidence_gaps"]


def test_sft_target_template_alignment_reports_no_matching_rows_without_vacuous_success() -> None:
    rows = [_row_with_split("train-search", "train", "search", "search_web", {"query": "天气"})]

    diagnostics = evaluation.diagnose_source_alignment(
        rows,
        {"different-row": rows[0].target_contract.to_dict()},
        training_config={"dataset_split": "train", "prediction_split": "train"},
        prediction_metadata={"prediction_split": "train"},
    )

    alignment = diagnostics["sft_target_template_alignment"]
    assert alignment["summary"]["row_count"] == 0
    assert alignment["summary"]["all_rows_share_system_user_prefix"] is False
    assert alignment["summary"]["all_training_text_contains_assistant_target"] is False
    assert alignment["summary"]["all_prediction_prompts_exclude_assistant_target"] is False
    assert alignment["summary"]["structural_target_span_status"] == "unavailable"
    assert "no_matching_prediction_rows" in alignment["summary"]["evidence_gaps"]


def test_diagnose_source_cli_writes_public_safe_json_and_markdown(tmp_path: Path) -> None:
    rows = [
        _row_with_split("train-search", "train", "search", "search_web", {"query": "天气"}),
        _row_with_split("test-open", "test", "navigate", "open_url", {"url": "https://example.com"}),
    ]
    gold = tmp_path / "gold.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    training_config = tmp_path / "training-config.json"
    prediction_metadata = tmp_path / "prediction-metadata.json"
    output = tmp_path / "source"
    write_jsonl(gold, [row.to_dict() for row in rows])
    write_jsonl(
        predictions,
        [
            {
                "id": "train-search",
                "prediction": {
                    "task_type": "normalization",
                    "route": "/weather",
                    "safety": {"allow": True, "reason": ""},
                    "confirmation_required": False,
                    "slots": [],
                    "normalized_command": "",
                    "language": "zh-CN",
                    "contract_version": "v1",
                },
            },
            {"id": "test-open", "prediction": rows[1].target_contract.to_dict()},
        ],
    )
    training_config.write_text(json.dumps({"dataset_split": "train"}), encoding="utf-8")
    prediction_metadata.write_text(
        json.dumps(
            {
                "prediction_split": "all",
                "decoding_policy": {
                    "strategy": "greedy",
                    "do_sample": False,
                    "max_new_tokens": 128,
                    "raw_decoded_sidecar_written": False,
                    "schema_repair_applied": False,
                },
            }
        ),
        encoding="utf-8",
    )

    assert (
        eval_cli.main(
            [
                "diagnose-source",
                "--gold",
                gold.as_posix(),
                "--predictions",
                predictions.as_posix(),
                "--training-config",
                training_config.as_posix(),
                "--prediction-metadata",
                prediction_metadata.as_posix(),
                "--output",
                output.as_posix(),
                "--title",
                "Source diagnostics",
            ]
        )
        == 0
    )

    diagnostics = json.loads((output / "source_diagnostics.json").read_text(encoding="utf-8"))
    markdown = (output / "source_diagnostics.md").read_text(encoding="utf-8")
    alignment_diagnostics = json.loads((output / "sft_target_template_alignment.json").read_text(encoding="utf-8"))
    alignment_markdown = (output / "sft_target_template_alignment.md").read_text(encoding="utf-8")
    assert diagnostics["decoding_evidence"]["policy"]["max_new_tokens"] == 128
    assert diagnostics["decoding_evidence"]["policy"]["schema_repair_applied"] is False
    assert diagnostics["prediction_run_prompt_evidence"]["prompt_constraints_present"] is False
    assert diagnostics["prediction_symptoms"]["path_like_route_count"] == 1
    assert alignment_diagnostics["summary"]["diagnostic_status"] == "public_safe_structural_evidence"
    assert alignment_diagnostics["label_mask_evidence"]["status"] == "labels_unavailable"
    assert "training_text" not in alignment_diagnostics["rows"][0]
    assert "prediction_prompt" not in alignment_diagnostics["rows"][0]
    assert alignment_diagnostics["rows"][0]["prediction_prompt_ends_with_generation_boundary"] is True
    assert "SFT Target-Template Alignment" in alignment_markdown
    assert "not a checkpoint release" in alignment_markdown
    assert "帮我处理train-search" not in alignment_markdown
    assert "Source diagnostics" in markdown
    assert "schema_repair_applied" in markdown


def test_alignment_diagnostics_redact_private_row_ids_and_values(tmp_path: Path) -> None:
    private_row_id = "/" + "Users/example/private/" + "sk-" + "1234567890123456"
    row = _row(private_row_id, "search_web", "天气")
    prediction = {
        **row.target_contract.to_dict(),
        "task_type": "api_" + "key=" + "secret1234",
        "normalized_command": "/" + "Users/example/private/" + "sk-" + "1234567890123456",
    }

    diagnostics = evaluation.diagnose_alignment_mismatches([row], {private_row_id: prediction})
    paths = reports.write_alignment_diagnostics_report(diagnostics, output_dir=tmp_path)
    markdown = paths["markdown"].read_text(encoding="utf-8")
    serialized = json.dumps(diagnostics, ensure_ascii=False, sort_keys=True)

    assert "/" + "Users/example" not in serialized
    assert "sk-" + "1234567890123456" not in serialized
    assert "/" + "Users/example" not in markdown
    assert "sk-" + "1234567890123456" not in markdown
    assert "<private_path>" in serialized
    assert "<secret>" in serialized


def test_alignment_diagnostics_summarize_empty_objects_without_trailing_whitespace(tmp_path: Path) -> None:
    row = _row("gold-1", "search_web", "天气")
    prediction = {**row.target_contract.to_dict(), "slots": {}}

    diagnostics = evaluation.diagnose_alignment_mismatches([row], {"gold-1": prediction})
    paths = reports.write_alignment_diagnostics_report(diagnostics, output_dir=tmp_path)
    markdown = paths["markdown"].read_text(encoding="utf-8")
    slots_mismatch = diagnostics["rows"][0]["mismatches"][0]

    assert slots_mismatch["field_path"] == "slots"
    assert slots_mismatch["prediction_value_summary"] == "empty object"
    assert "prediction empty object" in markdown
    assert "prediction object with keys: " not in markdown


def test_rule_and_prompt_fixture_baselines_are_bounded(tmp_path: Path) -> None:
    rows = [_row("gold-1", "search_web", "天气")]
    predictions = rule_baseline_predictions(rows)

    assert predictions["gold-1"]["task_type"] == "search"

    fixture = tmp_path / "prompt_predictions.jsonl"
    write_jsonl(fixture, [{"id": "gold-1", "prediction": rows[0].target_contract.to_dict()}])
    prompt_predictions = prompt_fixture_predictions(rows, fixture)
    assert prompt_predictions["gold-1"]["route"] == "search_web"


def test_execution_smoke_calls_controlled_validation_command(tmp_path: Path) -> None:
    rows = [_row("gold-1", "search_web", "天气")]
    predictions = rule_baseline_predictions(rows)
    assert run_execution_smoke(rows, predictions, enabled=False).enabled is False

    validator = tmp_path / "validator.py"
    validator.write_text(
        "\n".join(
            [
                "import json, sys",
                "payload = json.load(sys.stdin)",
                "contract = payload['contract']",
                "ok = contract.get('route') == 'search_web'",
                "print(json.dumps({'ok': ok, 'reason': 'checked'}))",
            ]
        ),
        encoding="utf-8",
    )
    target = tmp_path / "validation-target.json"
    target.write_text(json.dumps({"command": ["python", str(validator)]}), encoding="utf-8")
    smoke = run_execution_smoke(rows, predictions, enabled=True, target_path=target)
    assert smoke.enabled is True
    assert smoke.passed == 1
    assert smoke.failed == 0


def test_smoke_cli_can_write_json_result(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    rows = [_row("gold-1", "search_web", "天气")]
    gold = tmp_path / "gold.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    write_jsonl(gold, [rows[0].to_dict()])
    write_jsonl(predictions, [{"id": "gold-1", "prediction": rows[0].target_contract.to_dict()}])
    target = tmp_path / "validation-target.json"
    target.write_text(json.dumps({"accepts_contracts": True}), encoding="utf-8")
    output = tmp_path / "smoke_result.json"

    assert (
        eval_cli.main(
            [
                "smoke",
                "--gold",
                gold.as_posix(),
                "--predictions",
                predictions.as_posix(),
                "--target",
                target.as_posix(),
                "--output",
                output.as_posix(),
            ]
        )
        == 0
    )

    assert capsys.readouterr().out == ""
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["passed"] == 1
    assert result["failed"] == 0


def test_write_metrics_report_outputs_json_and_markdown(tmp_path: Path) -> None:
    rows = [_row("gold-1", "search_web", "天气")]
    result = evaluate_predictions(rows, {"gold-1": rows[0].target_contract.to_dict()})

    paths = write_metrics_report(result, output_dir=tmp_path, title="Public sample metrics")

    metrics = json.loads(paths["json"].read_text(encoding="utf-8"))
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert metrics["metrics"]["contract_exact_match"] == 1.0
    assert "Public sample metrics" in markdown
    assert "live-browser improvement" in markdown
