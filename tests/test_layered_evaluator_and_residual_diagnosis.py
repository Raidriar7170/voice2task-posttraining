import json
from pathlib import Path

from voice2task.evaluation import evaluate_predictions
from voice2task.io import write_jsonl
from voice2task.layered_evaluation import (
    REQUIRED_LAYERED_METRICS,
    diagnose_residuals,
    evaluate_layered_predictions,
    generate_layered_and_residual_reports,
    normalize_slot_key,
    normalize_slot_value,
)
from voice2task.leak_scan import scan_paths
from voice2task.schemas import BrowserTaskContract, SFTDatasetRow


def _contract(
    *,
    task_type: str = "search",
    route: str = "search_web",
    allow: bool = True,
    reason: str = "public_readonly",
    confirmation_required: bool = False,
    slots: dict[str, object] | None = None,
    normalized_command: str = "搜索公开信息",
) -> BrowserTaskContract:
    return BrowserTaskContract(
        task_type=task_type,
        route=route,
        safety={"allow": allow, "reason": reason},
        confirmation_required=confirmation_required,
        slots=slots if slots is not None else {"query": "公开信息"},
        normalized_command=normalized_command,
    )


def _row(row_id: str, contract: BrowserTaskContract, *, split: str = "dev") -> SFTDatasetRow:
    return SFTDatasetRow(
        id=row_id,
        split=split,
        input_text=f"公开测试指令 {row_id}",
        target_contract=contract,
        provenance={"source_id": row_id, "public_safe": True},
    )


def test_layered_metrics_preserve_strict_exact_and_add_diagnostic_normalization() -> None:
    rows = [
        _row("exact", _contract(slots={"query": "天气"}, normalized_command="搜索天气")),
        _row("normalized", _contract(slots={"query": "OpenAI docs"}, normalized_command="搜索 OpenAI docs")),
        _row(
            "unsafe-downgrade",
            _contract(
                task_type="blocked",
                route="deny",
                allow=False,
                reason="unsafe_payment",
                confirmation_required=True,
                slots={"reason": "payment"},
                normalized_command="拒绝支付请求",
            ),
        ),
        _row("invalid", _contract(slots={"query": "地图"}, normalized_command="搜索地图")),
    ]
    predictions = {
        "exact": rows[0].target_contract.to_dict(),
        "normalized": {
            **rows[1].target_contract.to_dict(),
            "slots": {"keyword": "openai docs!"},
        },
        "unsafe-downgrade": {
            **rows[2].target_contract.to_dict(),
            "safety": {"allow": True, "reason": "public_readonly"},
            "confirmation_required": False,
        },
        "invalid": "not json",
    }

    strict = evaluate_predictions(rows, predictions)
    layered = evaluate_layered_predictions(rows, predictions)

    assert set(REQUIRED_LAYERED_METRICS).issubset(layered["metrics"])
    assert layered["metrics"]["contract_exact_match_strict"] == strict.metrics["contract_exact_match"]
    assert "contract_exact_match" not in layered["metrics"]
    assert layered["summary"]["total"] == 4
    assert layered["summary"]["strict_pass"] == 1
    assert layered["summary"]["strict_fail"] == 3
    assert layered["metrics"]["schema_validity"] == 0.75
    assert layered["metrics"]["slot_key_f1"] > layered["metrics"]["slot_value_exact_f1"]
    assert layered["metrics"]["slot_value_normalized_f1"] > layered["metrics"]["slot_value_exact_f1"]
    assert layered["metrics"]["unsafe_false_negative_rate"] == 1.0
    assert layered["metrics"]["unsafe_false_positive_rate"] == 0.0
    assert layered["summary"]["unsafe_gold_support"] == 1
    assert layered["summary"]["unsafe_safe_gold_support"] == 2
    assert layered["summary"]["unsafe_false_negative_count"] == 1
    assert layered["summary"]["unsafe_false_positive_count"] == 0
    assert layered["metrics"]["executable_contract_pass_rate"] == 0.5
    assert layered["claims"]["strict_evaluator_semantics_preserved"] is True
    assert layered["claims"]["llm_judge_used"] is False
    assert layered["claims"]["prediction_repair_performed"] is False


def test_normalization_is_conservative_and_does_not_equate_materially_different_values() -> None:
    assert normalize_slot_key("keyword") == "query"
    assert normalize_slot_key("SEARCH_TERM") == "query"
    assert normalize_slot_value("  OPENAI docs!  ") == normalize_slot_value("openai docs")
    assert normalize_slot_value("打开　Example.com。") == normalize_slot_value("open example.com")
    assert normalize_slot_value("北京") != normalize_slot_value("上海")
    assert normalize_slot_value("2026-06-18") != normalize_slot_value("2026-06-19")
    assert normalize_slot_value("100 元") != normalize_slot_value("200 元")


def test_residual_diagnosis_attributes_field_families_and_sanitizes_examples() -> None:
    rows = [
        _row("route", _contract(slots={"query": "天气"})),
        _row("missing-slot", _contract(slots={"query": "机票", "date": "明天"})),
        _row("extra-slot", _contract(slots={"query": "新闻"})),
        _row(
            "confirmation",
            _contract(
                task_type="blocked",
                route="deny",
                allow=False,
                reason="unsafe_payment",
                confirmation_required=True,
                slots={"reason": "payment"},
            ),
        ),
        _row("invalid-output", _contract(slots={"query": "汇率"})),
    ]
    predictions = {
        "route": {**rows[0].target_contract.to_dict(), "route": "open_url"},
        "missing-slot": {**rows[1].target_contract.to_dict(), "slots": {"query": "机票"}},
        "extra-slot": {**rows[2].target_contract.to_dict(), "slots": {"query": "新闻", "city": "北京"}},
        "confirmation": {
            **rows[3].target_contract.to_dict(),
            "safety": {"allow": True, "reason": "public_readonly"},
            "confirmation_required": False,
        },
        "invalid-output": {"task_type": "search"},
    }

    diagnosis = diagnose_residuals(rows, predictions, split="dev")

    assert diagnosis["summary"]["total"] == 5
    assert diagnosis["summary"]["strict_pass"] == 0
    assert diagnosis["summary"]["strict_fail"] == 5
    family_counts = diagnosis["summary"]["family_counts"]
    assert family_counts["route"] == 1
    assert family_counts["missing_slot"] == 1
    assert family_counts["extra_slot"] == 1
    assert family_counts["risk_level"] == 2
    assert family_counts["confirmation"] == 1
    assert family_counts["invalid_output"] == 1
    assert diagnosis["summary"]["family_proportions"]["route"] == 0.2
    assert diagnosis["summary"]["top_field_paths"][0]["path"] in {"slots.query", "route", "safety.allow"}
    assert {item["field_path"] for item in diagnosis["residuals"] if item["family"] == "risk_level"} >= {
        "safety.allow",
        "safety.reason",
    }
    assert all(
        len(family["examples"]) <= 3
        for family in diagnosis["families"].values()
    )
    assert diagnosis["claims"]["recommendations_are_diagnostic_only"] is True
    assert diagnosis["claims"]["model_improvement_claim"] is False


def test_residual_examples_redact_private_paths_tokens_and_ips(tmp_path: Path) -> None:
    private_path = "/Users/example/private/raw.log"
    token = "api_key=abc123456789"
    private_ip = "192.168.1.10"
    rows = [
        _row(
            "private-summary",
            _contract(slots={"query": "public query"}, normalized_command="搜索公开信息"),
        )
    ]
    predictions = {
        "private-summary": {
            **rows[0].target_contract.to_dict(),
            "normalized_command": f"读取 {private_path} {token} {private_ip}",
            "slots": {"query": f"public query {private_path} {token} {private_ip}"},
        }
    }

    diagnosis = diagnose_residuals(rows, predictions, split="dev")
    output_dir = tmp_path / "source"
    for split in ("dev", "test"):
        split_dir = output_dir / split
        write_jsonl(split_dir / f"{split}_gold.jsonl", [rows[0].to_dict()])
        write_jsonl(
            split_dir / "predictions.jsonl",
            [{"id": "private-summary", "prediction": predictions["private-summary"]}],
        )

    generate_layered_and_residual_reports(
        source_dir=output_dir,
        layered_output_dir=tmp_path / "layered-eval",
        residual_output_dir=tmp_path / "residual-diagnosis",
        manifest_id="public-sample-20260617T152259Z",
    )
    serialized = json.dumps(diagnosis, ensure_ascii=False) + "\n"
    serialized += (tmp_path / "residual-diagnosis" / "dev" / "residual_diagnosis.md").read_text(
        encoding="utf-8"
    )

    assert private_path not in serialized
    assert token not in serialized
    assert private_ip not in serialized
    assert "<private_path>" in serialized
    assert "<secret>" in serialized
    assert "<private_ip>" in serialized
    assert scan_paths([tmp_path / "residual-diagnosis"]).ok


def test_raw_extra_field_is_strict_schema_invalid_and_diagnosed_as_extra_field() -> None:
    row = _row("extra-field", _contract(slots={"query": "天气"}))
    prediction = {
        **row.target_contract.to_dict(),
        "debug_trace": "public debug text",
    }

    strict = evaluate_predictions([row], {"extra-field": prediction})
    layered = evaluate_layered_predictions([row], {"extra-field": prediction})
    diagnosis = diagnose_residuals([row], {"extra-field": prediction}, split="dev")

    assert strict.metrics["strict_schema_valid_rate"] == 0.0
    assert strict.metrics["contract_exact_match"] == 0.0
    assert strict.failure_slices["schema"]["count"] == 1
    assert layered["metrics"]["schema_validity"] == 0.0
    assert layered["summary"]["strict_pass"] == 0
    assert layered["summary"]["strict_fail"] == 1
    assert diagnosis["summary"]["strict_pass"] == 0
    assert diagnosis["summary"]["strict_fail"] == 1
    assert diagnosis["summary"]["family_counts"]["extra_field"] == 1
    assert diagnosis["summary"]["top_field_paths"][0] == {"path": "debug_trace", "count": 1}
    assert diagnosis["families"]["extra_field"]["examples"][0]["field_path"] == "debug_trace"


def test_report_generation_writes_public_safe_dev_test_layered_and_residual_outputs(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    for split in ("dev", "test"):
        split_dir = source_dir / split
        rows = [
            _row(f"{split}-exact", _contract(slots={"query": "天气"}), split=split),
            _row(f"{split}-slot", _contract(slots={"query": "OpenAI docs"}), split=split),
        ]
        predictions = {
            rows[0].id: rows[0].target_contract.to_dict(),
            rows[1].id: {**rows[1].target_contract.to_dict(), "slots": {"keyword": "openai docs!"}},
        }
        write_jsonl(split_dir / f"{split}_gold.jsonl", [row.to_dict() for row in rows])
        write_jsonl(
            split_dir / "predictions.jsonl",
            [{"id": row_id, "prediction": prediction} for row_id, prediction in predictions.items()],
        )
        (split_dir / "metrics.json").write_text(
            json.dumps(evaluate_predictions(rows, predictions).to_dict(), ensure_ascii=False),
            encoding="utf-8",
        )

    outputs = generate_layered_and_residual_reports(
        source_dir=source_dir,
        layered_output_dir=tmp_path / "layered-eval",
        residual_output_dir=tmp_path / "residual-diagnosis",
        manifest_id="public-sample-20260617T152259Z",
    )

    assert (tmp_path / "layered-eval" / "dev" / "metrics.json").exists()
    assert (tmp_path / "layered-eval" / "test" / "metrics.json").exists()
    assert (tmp_path / "layered-eval" / "summary.md").exists()
    assert (tmp_path / "residual-diagnosis" / "dev" / "residual_diagnosis.json").exists()
    assert (tmp_path / "residual-diagnosis" / "test" / "residual_diagnosis.json").exists()
    assert (tmp_path / "residual-diagnosis" / "summary.json").exists()
    layered_dev = json.loads((tmp_path / "layered-eval" / "dev" / "metrics.json").read_text(encoding="utf-8"))
    residual_summary = json.loads((tmp_path / "residual-diagnosis" / "summary.json").read_text(encoding="utf-8"))
    assert layered_dev["manifest_id"] == "public-sample-20260617T152259Z"
    assert layered_dev["metrics"]["contract_exact_match_strict"] == 0.5
    assert residual_summary["splits"]["dev"]["strict_fail"] == 1
    assert outputs["claims"]["a100_training_performed"] is False
    assert outputs["claims"]["evaluator_relaxation_performed"] is False
    assert scan_paths([tmp_path / "layered-eval", tmp_path / "residual-diagnosis"]).ok
