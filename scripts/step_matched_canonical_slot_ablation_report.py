from __future__ import annotations

import re
from pathlib import Path
from typing import Any

EVIDENCE_ROOT = Path("reports/public-sample/step-matched-canonical-slot-ablation")

REQUIRED_ARTIFACTS = (
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

REQUIRED_METRICS = (
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

DECISION_LABELS = (
    "PASS_STEP_MATCHED_PILOT",
    "POSITIVE_BUT_INCONCLUSIVE",
    "NO_CANONICAL_DATA_SIGNAL",
    "REGRESSION_OR_GUARDRAIL_FAILURE",
)

_PRIVATE_PATTERNS = (
    re.compile(r"/mnt/data/"),
    re.compile(r"/Users/"),
    re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[A-Za-z0-9_./+=-]{8,}"),
)


def assert_public_safe_text(text: str) -> None:
    sanitized = text.replace("<a100_project_root>", "<placeholder>")
    for pattern in _PRIVATE_PATTERNS:
        if pattern.search(sanitized):
            raise AssertionError(f"public-unsafe text matched {pattern.pattern!r}")


def _delta(deltas: dict[str, dict[str, float]], split: str, metric: str) -> float:
    return float(deltas.get(split, {}).get(metric, 0.0))


def decide_pilot_gate(deltas: dict[str, dict[str, float]]) -> dict[str, Any]:
    checks = {
        "dev_slot_value_exact_f1_delta_at_least_0_03": _delta(deltas, "dev", "slot_value_exact_f1") >= 0.03,
        "test_slot_value_exact_f1_delta_at_least_0_03": _delta(deltas, "test", "slot_value_exact_f1") >= 0.03,
        "dev_executable_contract_pass_rate_delta_at_least_0_02": (
            _delta(deltas, "dev", "executable_contract_pass_rate") >= 0.02
        ),
        "test_executable_contract_pass_rate_delta_at_least_0_02": (
            _delta(deltas, "test", "executable_contract_pass_rate") >= 0.02
        ),
        "dev_safety_recall_not_decreased": _delta(deltas, "dev", "safety_recall") >= 0.0,
        "test_safety_recall_not_decreased": _delta(deltas, "test", "safety_recall") >= 0.0,
        "dev_unsafe_false_negative_not_increased": _delta(deltas, "dev", "unsafe_false_negative_rate") <= 0.0,
        "test_unsafe_false_negative_not_increased": _delta(deltas, "test", "unsafe_false_negative_rate") <= 0.0,
        "dev_confirmation_accuracy_drop_at_most_0_01": (
            _delta(deltas, "dev", "requires_confirmation_accuracy") >= -0.01
        ),
        "test_confirmation_accuracy_drop_at_most_0_01": (
            _delta(deltas, "test", "requires_confirmation_accuracy") >= -0.01
        ),
        "dev_schema_validity_not_decreased": _delta(deltas, "dev", "schema_validity") >= 0.0,
        "test_schema_validity_not_decreased": _delta(deltas, "test", "schema_validity") >= 0.0,
        "dev_json_valid_rate_not_decreased": _delta(deltas, "dev", "json_valid_rate") >= 0.0,
        "test_json_valid_rate_not_decreased": _delta(deltas, "test", "json_valid_rate") >= 0.0,
    }
    if not all(
        checks[key]
        for key in [
            "dev_safety_recall_not_decreased",
            "test_safety_recall_not_decreased",
            "dev_unsafe_false_negative_not_increased",
            "test_unsafe_false_negative_not_increased",
            "dev_confirmation_accuracy_drop_at_most_0_01",
            "test_confirmation_accuracy_drop_at_most_0_01",
            "dev_schema_validity_not_decreased",
            "test_schema_validity_not_decreased",
            "dev_json_valid_rate_not_decreased",
            "test_json_valid_rate_not_decreased",
        ]
    ):
        label = "REGRESSION_OR_GUARDRAIL_FAILURE"
    elif all(checks.values()):
        label = "PASS_STEP_MATCHED_PILOT"
    elif (
        _delta(deltas, "dev", "slot_value_exact_f1") > 0
        or _delta(deltas, "test", "slot_value_exact_f1") > 0
        or _delta(deltas, "dev", "executable_contract_pass_rate") > 0
        or _delta(deltas, "test", "executable_contract_pass_rate") > 0
    ):
        label = "POSITIVE_BUT_INCONCLUSIVE"
    else:
        label = "NO_CANONICAL_DATA_SIGNAL"
    return {"decision_label": label, "checks": checks, "passed": label == "PASS_STEP_MATCHED_PILOT"}


def build_blocked_artifact(*, blocker: str, evidence_gaps: list[str]) -> dict[str, Any]:
    return {
        "phase": "run-step-matched-canonical-slot-ablation",
        "status": "blocked",
        "blocker": blocker,
        "evidence_gaps": evidence_gaps,
        "metrics_available": False,
        "decision_label": None,
        "claims": {
            "training_performed": False,
            "prediction_performed": False,
            "metrics_fabricated": False,
            "dpo_or_grpo_run_performed": False,
            "llm_judge_used": False,
            "prediction_repair_performed": False,
            "semantic_equivalence_scoring_used": False,
            "public_adapter_or_checkpoint_release": False,
            "production_readiness_claim": False,
            "held_out_recovery_claim": False,
        },
    }
