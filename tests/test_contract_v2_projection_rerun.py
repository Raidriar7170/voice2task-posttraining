from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from voice2task.contract_v2_projection import (
    CONTRIBUTION_CATEGORIES,
    REQUIRED_RERUN_ARTIFACTS,
    SUPPORTED_METRIC_REPRODUCTION_STATUSES,
    build_v2_envelope,
    canonical_v2_core_json,
    classify_failure_contribution,
    deterministic_normalized_command_renderer,
    generate_contract_v2_projection_rerun,
    paired_bootstrap_projection_deltas,
    project_v1_to_v2_core,
    v1_without_normalized_command_exact,
    v2_core_executable_pass,
    validate_recovered_source_boundary,
    validate_v2_core,
)
from voice2task.layered_evaluation import evaluate_layered_predictions
from voice2task.leak_scan import scan_paths
from voice2task.schemas import SFTDatasetRow, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_INPUTS = REPO_ROOT / "reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs"


def _contract(
    *,
    task_type: str = "search",
    route: str = "search_web",
    slots: dict[str, object] | None = None,
    normalized_command: str = "搜索北京明天天气",
    allow: bool = True,
    reason: str = "public_readonly",
    confirmation_required: bool = False,
    language: str = "zh-CN",
    contract_version: str = "v1",
) -> dict[str, object]:
    return {
        "task_type": task_type,
        "route": route,
        "safety": {"allow": allow, "reason": reason},
        "confirmation_required": confirmation_required,
        "slots": slots or {"query": "北京明天天气"},
        "normalized_command": normalized_command,
        "language": language,
        "contract_version": contract_version,
    }


def _rewrite_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_v2_core_projection_validation_canonical_json_and_envelope_are_deterministic() -> None:
    contract = _contract(slots={"query": "北京明天天气"})

    core = project_v1_to_v2_core(contract)

    assert set(core) == {"task_type", "route", "safety", "confirmation_required", "slots"}
    assert core["slots"] == {"query": "北京明天天气"}
    assert "normalized_command" not in core
    assert "language" not in core
    assert "contract_version" not in core
    assert validate_v2_core(core) == core
    assert canonical_v2_core_json(core) == canonical_v2_core_json(dict(reversed(list(core.items()))))
    assert build_v2_envelope(core) == build_v2_envelope(core)

    envelope = build_v2_envelope(core)
    assert envelope["language"] == "zh-CN"
    assert envelope["contract_version"] == "v2"
    assert envelope["normalized_command"] == "搜索北京明天天气"

    invalid_core = {**core, "allowed_actions": ["click"]}
    with pytest.raises(ValidationError):
        validate_v2_core(invalid_core)


def test_renderer_reads_only_core_fields_fails_closed_and_preserves_values() -> None:
    first = project_v1_to_v2_core(_contract(slots={"query": "北京明天天气"}, normalized_command="旧命令一"))
    second = project_v1_to_v2_core(_contract(slots={"query": "北京明天天气"}, normalized_command="旧命令二"))
    assert deterministic_normalized_command_renderer(first) == deterministic_normalized_command_renderer(second)

    search_core = project_v1_to_v2_core(_contract(slots={"query": "上海后天机票 300 元"}))
    assert deterministic_normalized_command_renderer(search_core)["normalized_command"] == "搜索上海后天机票 300 元"

    form_core = project_v1_to_v2_core(
        _contract(
            task_type="form_fill",
            route="fill_form",
            slots={"field": "邮箱", "value": "qa@example.com"},
            normalized_command="填写邮箱并确认",
            reason="requires_confirmation",
            confirmation_required=True,
        )
    )
    rendered = deterministic_normalized_command_renderer(form_core)
    assert rendered["supported"] is True
    assert "邮箱" in rendered["normalized_command"]
    assert "qa@example.com" in rendered["normalized_command"]

    unsupported = deterministic_normalized_command_renderer(
        {
            "task_type": "search",
            "route": "search_web",
            "safety": {"allow": True, "reason": "x"},
            "confirmation_required": False,
            "slots": {},
        }
    )
    assert unsupported == {"supported": False, "reason": "missing_query_slot", "normalized_command": None}


def test_safety_confirmation_and_v2_executable_policy_are_retained() -> None:
    gold = project_v1_to_v2_core(
        _contract(
            task_type="blocked",
            route="deny",
            slots={"reason": "payment_requires_user_control"},
            normalized_command="拒绝代替用户转账",
            allow=False,
            reason="unsafe_payment",
            confirmation_required=True,
        )
    )
    safe_downgrade = {
        **gold,
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
    }

    assert gold["safety"] == {"allow": False, "reason": "unsafe_payment"}
    assert gold["confirmation_required"] is True
    assert v2_core_executable_pass(gold, safe_downgrade) is False


def test_v1_evaluator_semantics_stay_unchanged_for_normalized_command_mismatch() -> None:
    gold = _contract(normalized_command="搜索北京明天天气")
    pred = _contract(normalized_command="搜索北京明天的天气")
    rows = [SFTDatasetRow(id="row-1", split="dev", input_text="搜天气", target_contract=gold)]

    layered = evaluate_layered_predictions(rows, {"row-1": pred})

    assert layered["metrics"]["contract_exact_match_strict"] == 0.0
    assert layered["metrics"]["executable_contract_pass_rate"] == 1.0
    assert v1_without_normalized_command_exact(gold, pred) is True


@pytest.mark.parametrize(
    ("gold", "pred", "expected"),
    [
        (
            _contract(normalized_command="搜索北京明天天气"),
            _contract(normalized_command="搜索北京天气"),
            "NORMALIZED_COMMAND_ONLY",
        ),
        (_contract(), _contract(language="en-US"), "METADATA_ONLY"),
        (_contract(), _contract(normalized_command="搜索北京天气", contract_version="v0"), "DERIVED_FIELD_ONLY"),
        (_contract(slots={"query": "北京天气"}), _contract(slots={"query": "上海天气"}), "CORE_SLOT_FAILURE"),
        (
            _contract(),
            _contract(task_type="navigate", route="open_url", slots={"url": "https://example.com"}),
            "CORE_ROUTE_TASK_FAILURE",
        ),
        (
            _contract(confirmation_required=True, reason="requires_confirmation"),
            _contract(),
            "CORE_SAFETY_CONFIRMATION_FAILURE",
        ),
        (_contract(), _contract(route="open_url", slots={"query": "上海天气"}), "MIXED_CORE_FAILURE"),
        (_contract(), {"not": "a contract"}, "INVALID_OR_UNPARSEABLE"),
    ],
)
def test_failure_contribution_categories_are_complete(
    gold: dict[str, object],
    pred: dict[str, object],
    expected: str,
) -> None:
    assert expected in CONTRIBUTION_CATEGORIES
    assert classify_failure_contribution(gold, pred)["category"] == expected


def test_fixed_seed_bootstrap_is_deterministic() -> None:
    rows = [
        {"family": "search", "l0_exact": False, "l2_exact": True, "v1_executable": True, "v2_executable": True},
        {"family": "navigate", "l0_exact": False, "l2_exact": False, "v1_executable": False, "v2_executable": False},
        {"family": "blocked", "l0_exact": True, "l2_exact": True, "v1_executable": True, "v2_executable": True},
    ]

    first = paired_bootstrap_projection_deltas(rows, seed=20260621, iterations=200)
    second = paired_bootstrap_projection_deltas(rows, seed=20260621, iterations=200)

    assert first == second
    assert first["seed"] == 20260621
    assert first["iterations"] == 200
    assert "exact_pass_delta_ci95" in first
    assert "executable_pass_delta_ci95" in first


def test_recovered_source_boundary_accepts_current_ready_inputs() -> None:
    boundary = validate_recovered_source_boundary(RAW_INPUTS)

    assert boundary["decision_label"] == "SOURCE_BOUNDARY_PASSED"
    assert boundary["projection_inputs_ready"] is True
    assert boundary["metric_reproduction_status"] in SUPPORTED_METRIC_REPRODUCTION_STATUSES
    assert boundary["metric_reproduction_status"] == "reproduced"
    assert boundary["raw_model_output_used_for_projection"] is False
    assert boundary["prediction_contract_used_for_projection"] is True
    assert boundary["splits"]["dev"]["row_count"] == 207
    assert boundary["splits"]["test"]["row_count"] == 207
    assert boundary["dev_test_sample_ids_disjoint"] is True


def test_projection_rerun_writes_complete_public_safe_artifacts_without_overwriting_history(tmp_path: Path) -> None:
    history_root = tmp_path / "contract-v2-projection"
    output_dir = history_root / "rerun-with-recovered-inputs"
    history_root.mkdir()
    historical_summary = history_root / "summary.md"
    historical_summary.write_text("historical blocked evidence\n", encoding="utf-8")

    result = generate_contract_v2_projection_rerun(raw_inputs_dir=RAW_INPUTS, output_dir=output_dir)

    assert result["decision_label"] in {
        "PROCEED_TO_CONTRACT_V2_IMPLEMENTATION",
        "PARTIAL_SCHEMA_BENEFIT",
        "SLOT_BOTTLENECK_PERSISTS",
        "PROJECTION_INVALID_OR_BLOCKED",
    }
    assert historical_summary.read_text(encoding="utf-8") == "historical blocked evidence\n"
    missing = [name for name in REQUIRED_RERUN_ARTIFACTS if not (output_dir / name).exists()]
    assert missing == []
    assert not (output_dir / "blocked.json").exists()

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["source_boundary"]["prediction_contract_used_for_projection"] is True
    assert summary["source_boundary"]["raw_model_output_used_for_projection"] is False
    assert summary["required_questions"]["used_recovered_metric_reproduced_step_matched_contracts"] is True
    assert summary["claims"]["training_performed"] is False
    assert summary["claims"]["prediction_repair_performed"] is False
    assert summary["claims"]["contract_v2_implemented"] is False
    assert scan_paths([output_dir]).ok


def test_invalid_boundary_writes_blocked_artifact_only(tmp_path: Path) -> None:
    bad_inputs = tmp_path / "raw-inputs"
    shutil.copytree(RAW_INPUTS, bad_inputs)
    manifest_path = bad_inputs / "artifact-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["projection_inputs_ready"] = False
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    output_dir = tmp_path / "rerun"

    result = generate_contract_v2_projection_rerun(raw_inputs_dir=bad_inputs, output_dir=output_dir)

    assert result["decision_label"] == "PROJECTION_INVALID_OR_BLOCKED"
    blocked = json.loads((output_dir / "blocked.json").read_text(encoding="utf-8"))
    assert blocked["boundary_decision_label"] == "PROJECTION_INVALID_INPUT_BOUNDARY"
    assert not (output_dir / "summary.json").exists()


def test_boundary_recomputes_sample_id_hash_from_jsonl_files(tmp_path: Path) -> None:
    bad_inputs = tmp_path / "raw-inputs"
    shutil.copytree(RAW_INPUTS, bad_inputs)
    for relative in [
        "gold/dev_gold.jsonl",
        "control/dev_predictions.jsonl",
        "treatment/dev_predictions.jsonl",
    ]:
        path = bad_inputs / relative
        rows = _read_jsonl(path)
        old_id = rows[0]["sample_id"]
        rows[0]["sample_id"] = f"{old_id}-tampered"
        _rewrite_jsonl(path, rows)

    boundary = validate_recovered_source_boundary(bad_inputs)

    assert boundary["decision_label"] == "PROJECTION_INVALID_INPUT_BOUNDARY"
    assert "dev: actual sample id hash does not match manifest" in boundary["failures"]


def test_boundary_recomputes_gold_contract_hash_from_jsonl_files(tmp_path: Path) -> None:
    bad_inputs = tmp_path / "raw-inputs"
    shutil.copytree(RAW_INPUTS, bad_inputs)
    for relative in [
        "gold/dev_gold.jsonl",
        "control/dev_predictions.jsonl",
        "treatment/dev_predictions.jsonl",
    ]:
        path = bad_inputs / relative
        rows = _read_jsonl(path)
        rows[0]["gold_contract"]["slots"] = {"url": "https://changed.example.com"}
        _rewrite_jsonl(path, rows)

    boundary = validate_recovered_source_boundary(bad_inputs)

    assert boundary["decision_label"] == "PROJECTION_INVALID_INPUT_BOUNDARY"
    assert "dev: actual gold contract hash does not match manifest" in boundary["failures"]
