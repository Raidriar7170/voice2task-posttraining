import json
from pathlib import Path

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


def test_write_metrics_report_outputs_json_and_markdown(tmp_path: Path) -> None:
    rows = [_row("gold-1", "search_web", "天气")]
    result = evaluate_predictions(rows, {"gold-1": rows[0].target_contract.to_dict()})

    paths = write_metrics_report(result, output_dir=tmp_path, title="Public sample metrics")

    metrics = json.loads(paths["json"].read_text(encoding="utf-8"))
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert metrics["metrics"]["contract_exact_match"] == 1.0
    assert "Public sample metrics" in markdown
    assert "live-browser improvement" in markdown
