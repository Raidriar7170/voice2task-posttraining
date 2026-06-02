from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voice2task.io import read_json, read_jsonl, write_jsonl
from voice2task.schemas import BrowserTaskContract, SFTDatasetRow, ValidationError, as_contract


@dataclass(frozen=True)
class EvaluationResult:
    metrics: dict[str, float]
    failure_slices: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"metrics": dict(self.metrics), "failure_slices": self.failure_slices}


@dataclass(frozen=True)
class ExecutionSmokeResult:
    enabled: bool
    passed: int
    failed: int
    target: str | None
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "passed": self.passed,
            "failed": self.failed,
            "target": self.target,
            "notes": self.notes,
        }


def _sanitize_id(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]", "_", value)
    return sanitized[:80]


def _prediction_to_contract(value: Any) -> BrowserTaskContract | None:
    try:
        if isinstance(value, str):
            parsed = json.loads(value)
        else:
            parsed = value
        if not isinstance(parsed, dict):
            return None
        return as_contract(parsed)
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None


def _slot_f1(gold: dict[str, Any], predicted: dict[str, Any]) -> float:
    gold_items = {(str(key), str(value)) for key, value in gold.items()}
    predicted_items = {(str(key), str(value)) for key, value in predicted.items()}
    if not gold_items and not predicted_items:
        return 1.0
    if not gold_items or not predicted_items:
        return 0.0
    true_positive = len(gold_items & predicted_items)
    precision = true_positive / len(predicted_items)
    recall = true_positive / len(gold_items)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _add_failure(failure_slices: dict[str, dict[str, Any]], category: str, row_id: str) -> None:
    entry = failure_slices.setdefault(category, {"count": 0, "examples": []})
    entry["count"] += 1
    if len(entry["examples"]) < 5:
        entry["examples"].append(_sanitize_id(row_id))


def evaluate_predictions(rows: list[SFTDatasetRow], predictions: dict[str, Any]) -> EvaluationResult:
    total = max(len(rows), 1)
    valid = 0
    task_type_matches = 0
    route_matches = 0
    confirmation_matches = 0
    exact_matches = 0
    slot_scores: list[float] = []
    safety_tp = safety_fp = safety_fn = 0
    failure_slices: dict[str, dict[str, Any]] = {
        category: {"count": 0, "examples": []}
        for category in ("schema", "task_type", "route", "safety", "confirmation", "slot", "unknown")
    }

    for row in rows:
        gold = as_contract(row.target_contract)
        predicted = _prediction_to_contract(predictions.get(row.id))
        if predicted is None:
            _add_failure(failure_slices, "schema", row.id)
            slot_scores.append(0.0)
            continue
        valid += 1
        if predicted.task_type == gold.task_type:
            task_type_matches += 1
        else:
            _add_failure(failure_slices, "task_type", row.id)
        if predicted.route == gold.route:
            route_matches += 1
        else:
            _add_failure(failure_slices, "route", row.id)
        if predicted.confirmation_required == gold.confirmation_required:
            confirmation_matches += 1
        else:
            _add_failure(failure_slices, "confirmation", row.id)

        predicted_safe_stop = not bool(predicted.safety["allow"])
        gold_safe_stop = not bool(gold.safety["allow"])
        if predicted_safe_stop and gold_safe_stop:
            safety_tp += 1
        elif predicted_safe_stop and not gold_safe_stop:
            safety_fp += 1
            _add_failure(failure_slices, "safety", row.id)
        elif not predicted_safe_stop and gold_safe_stop:
            safety_fn += 1
            _add_failure(failure_slices, "safety", row.id)

        slot_score = _slot_f1(gold.slots, predicted.slots)
        slot_scores.append(slot_score)
        if slot_score < 1.0:
            _add_failure(failure_slices, "slot", row.id)
        if predicted.to_dict() == gold.to_dict():
            exact_matches += 1

    safety_precision = 1.0 if safety_tp + safety_fp == 0 else safety_tp / (safety_tp + safety_fp)
    safety_recall = 1.0 if safety_tp + safety_fn == 0 else safety_tp / (safety_tp + safety_fn)
    metrics = {
        "json_valid_rate": valid / total,
        "task_type_accuracy": task_type_matches / total,
        "route_accuracy": route_matches / total,
        "safety_precision": safety_precision,
        "safety_recall": safety_recall,
        "safety_predicted_stop_support": float(safety_tp + safety_fp),
        "safety_gold_stop_support": float(safety_tp + safety_fn),
        "confirmation_accuracy": confirmation_matches / total,
        "slot_f1": sum(slot_scores) / total,
        "contract_exact_match": exact_matches / total,
    }
    return EvaluationResult(metrics=metrics, failure_slices=failure_slices)


def rule_baseline_predictions(rows: list[SFTDatasetRow]) -> dict[str, dict[str, Any]]:
    predictions: dict[str, dict[str, Any]] = {}
    for row in rows:
        text = row.input_text
        if any(marker in text for marker in ("搜", "搜索", "查")):
            query = text.replace("帮我", "").replace("搜索", "").replace("搜", "").replace("查一下", "").strip()
            contract = BrowserTaskContract(
                task_type="search",
                route="search_web",
                safety={"allow": True, "reason": "public_readonly"},
                confirmation_required=False,
                slots={"query": query or text},
                normalized_command=f"搜索{query or text}",
            )
        elif "打开" in text:
            contract = BrowserTaskContract(
                task_type="navigate",
                route="open_url",
                safety={"allow": True, "reason": "public_readonly"},
                confirmation_required=False,
                slots={"url": "about:blank"},
                normalized_command=text,
            )
        else:
            contract = BrowserTaskContract(
                task_type="clarify",
                route="clarify",
                safety={"allow": False, "reason": "underspecified_request"},
                confirmation_required=True,
                slots={},
                normalized_command=text,
            )
        predictions[row.id] = contract.to_dict()
    return predictions


def prompt_fixture_predictions(rows: list[SFTDatasetRow], fixture_path: Path) -> dict[str, Any]:
    expected_ids = {row.id for row in rows}
    predictions = load_predictions(fixture_path)
    missing = sorted(expected_ids - set(predictions))
    if missing:
        raise ValidationError(f"prompt_fixture_missing_predictions: {', '.join(missing)}")
    return {row_id: predictions[row_id] for row_id in sorted(expected_ids)}


def _run_validation_command(command: list[str], row: SFTDatasetRow, contract: BrowserTaskContract) -> bool:
    payload = json.dumps(
        {"id": row.id, "input_text": row.input_text, "contract": contract.to_dict()},
        ensure_ascii=False,
    )
    completed = subprocess.run(
        command,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return False
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False
    return bool(result.get("ok"))


def run_execution_smoke(
    rows: list[SFTDatasetRow],
    predictions: dict[str, Any],
    enabled: bool,
    target_path: Path | None = None,
) -> ExecutionSmokeResult:
    if not enabled:
        return ExecutionSmokeResult(enabled=False, passed=0, failed=0, target=None, notes="disabled")
    if target_path is None:
        return ExecutionSmokeResult(enabled=True, passed=0, failed=len(rows), target=None, notes="target_path_missing")
    target = read_json(target_path)
    command = target.get("command")
    if isinstance(command, list) and all(isinstance(item, str) for item in command):
        passed = 0
        failed = 0
        for row in rows:
            prediction = _prediction_to_contract(predictions.get(row.id))
            if prediction is not None and _run_validation_command(command, row, prediction):
                passed += 1
            else:
                failed += 1
        return ExecutionSmokeResult(
            enabled=True,
            passed=passed,
            failed=failed,
            target=target_path.as_posix(),
            notes="controlled_validation_command",
        )
    if target.get("accepts_contracts") is not True:
        return ExecutionSmokeResult(
            enabled=True,
            passed=0,
            failed=len(rows),
            target=target_path.as_posix(),
            notes="target_does_not_accept_contracts",
        )
    passed = sum(1 for row in rows if _prediction_to_contract(predictions.get(row.id)) is not None)
    return ExecutionSmokeResult(
        enabled=True,
        passed=passed,
        failed=len(rows) - passed,
        target=target_path.as_posix(),
        notes="controlled_contract_consumer_smoke",
    )


def load_sft_rows(path: Path) -> list[SFTDatasetRow]:
    return [SFTDatasetRow(**record) for record in read_jsonl(path)]


def load_predictions(path: Path) -> dict[str, Any]:
    predictions: dict[str, Any] = {}
    for record in read_jsonl(path):
        row_id = str(record.get("id", ""))
        if "prediction" in record:
            predictions[row_id] = record["prediction"]
        elif "contract" in record:
            predictions[row_id] = record["contract"]
        else:
            predictions[row_id] = {key: value for key, value in record.items() if key != "id"}
    return predictions


def write_predictions(path: Path, predictions: dict[str, dict[str, Any]]) -> None:
    write_jsonl(path, [{"id": row_id, "prediction": prediction} for row_id, prediction in predictions.items()])
