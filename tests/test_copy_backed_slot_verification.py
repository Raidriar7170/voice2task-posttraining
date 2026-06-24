from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from voice2task.copy_backed_slot_verification import (
    AMBIGUOUS_NORMALIZATION_COLLISION,
    NORMALIZATION_COLLISION_RULE,
    CopyBackedScope,
    audit_normalized_equivalent_collision,
    verify_copy_backed_value,
)
from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/run_copy_backed_slot_verification_slice.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_copy_backed_slot_verification_slice", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enabled_scope(slot_path: str = "query") -> CopyBackedScope:
    return CopyBackedScope(task_type="search", route="search_web", slot_path=slot_path, enabled=True)


def test_exact_unique_source_span_uses_unicode_half_open_offsets() -> None:
    result = verify_copy_backed_value("北京", "搜索北京天气", _enabled_scope())

    assert result.status == "VERIFIED_EXACT_UNIQUE"
    assert result.match_kind == "exact"
    assert result.provenance == "system_verified_source"
    assert result.source_span is not None
    assert result.source_span.start == 2
    assert result.source_span.end == 4
    assert result.source_span.text == "北京"
    assert "搜索北京天气"[result.source_span.start : result.source_span.end] == "北京"


def test_duplicate_spans_and_disabled_action_fail_closed() -> None:
    duplicate = verify_copy_backed_value("北京", "北京天气和北京新闻", _enabled_scope())
    disabled_action = verify_copy_backed_value(
        "deny",
        "deny the unsafe request",
        CopyBackedScope(task_type="blocked", route="deny", slot_path="action", enabled=False),
    )

    assert duplicate.status == "AMBIGUOUS_MULTIPLE_MATCHES"
    assert duplicate.provenance == "unresolved"
    assert duplicate.source_span is None
    assert disabled_action.status == "OUT_OF_SCOPE"
    assert disabled_action.provenance == "unresolved"
    assert disabled_action.source_span is None


def test_bounded_normalized_match_maps_back_to_original_source_span() -> None:
    result = verify_copy_backed_value("ABC-123", "请查询ａｂｃ １２３的状态", _enabled_scope())
    date_alias = verify_copy_backed_value("2026-06-22", "安排在2026年6月22日", _enabled_scope("target"))
    semantic_alias = verify_copy_backed_value("NYC", "搜索 New York 天气", _enabled_scope())

    assert result.status == "VERIFIED_NORMALIZED_UNIQUE"
    assert result.match_kind == "normalized"
    assert result.provenance == "system_verified_source"
    assert result.source_span is not None
    assert result.source_span.text == "ａｂｃ １２３"
    assert "请查询ａｂｃ １２３的状态"[result.source_span.start : result.source_span.end] == "ａｂｃ １２３"
    assert date_alias.status == "NOT_FOUND"
    assert semantic_alias.status == "NOT_FOUND"


def test_raw_exact_unique_can_be_downgraded_by_normalized_equivalent_collision() -> None:
    audit = audit_normalized_equivalent_collision("A/B", "主片段 A/B，归一等价候选 AB。")

    assert audit.status == AMBIGUOUS_NORMALIZATION_COLLISION
    assert audit.raw_exact_span_count == 1
    assert audit.normalized_equivalent_span_count == 2
    assert audit.source_attested_exact is False
    assert audit.fail_closed is True
    assert audit.normalization_rule == NORMALIZATION_COLLISION_RULE


def test_normalized_equivalent_collision_detector_covers_punctuation_cases() -> None:
    examples = [
        ("1.2", "版本 1.2 旁边还有 12。"),
        ("C++", "语言 C++ 旁边还有 C。"),
        ("v1.2", "版本 v1.2 旁边还有 v12。"),
        ("example.com/a", "链接 example.com/a 旁边还有 examplecoma。"),
        ("a.b@example.com", "邮箱 a.b@example.com 旁边还有 abexamplecom。"),
    ]

    for value, source_text in examples:
        audit = audit_normalized_equivalent_collision(value, source_text)

        assert audit.status == AMBIGUOUS_NORMALIZATION_COLLISION
        assert audit.raw_exact_span_count == 1
        assert audit.normalized_equivalent_span_count >= 2
        assert audit.source_attested_exact is False
        assert audit.fail_closed is True
        assert audit.ambiguous_mapping is True


def test_report_builds_task_scoped_policy_and_preserves_historical_metric_names(tmp_path: Path) -> None:
    module = _load_script_module()

    result = module.write_copy_backed_slot_verification_reports(
        REPO_ROOT,
        tmp_path / "copy-slice",
        tmp_path / "copy-doc.md",
    )
    summary = result["summary"]
    policy = json.loads((tmp_path / "copy-slice/task-scoped-policy.json").read_text(encoding="utf-8"))

    enabled_paths = {row["slot_path"] for row in policy["policy_rows"] if row["enabled"]}
    action_rows = [row for row in policy["policy_rows"] if row["slot_path"] == "action"]

    assert summary["decision_label"] in {
        "COPY_SLICE_READY_FOR_SHADOW_INTEGRATION",
        "COPY_SLICE_PARTIAL_NEEDS_SCOPE_REFINEMENT",
        "COPY_SLICE_NOT_JUSTIFIED",
    }
    assert enabled_paths <= {"query", "field", "target"}
    assert {"query", "field", "target"}.issubset(enabled_paths)
    assert action_rows
    assert all(row["enabled"] is False for row in action_rows)
    assert all(row["verification_enabled"] is False for row in action_rows)
    assert summary["historical_design_metrics"]["strategy_assignment_rate"] == 1.0
    assert summary["historical_design_metrics"]["copy_strategy_candidate_coverage"] > 0.57
    assert "overall_representation_coverage" not in summary["historical_design_metrics"]
    assert "copy_backed_coverage" not in summary["historical_design_metrics"]
    assert summary["gates"]["provenance_false_accept_count"] == 0
    assert summary["gates"]["silent_fallback_count"] == 0
    assert summary["gates"]["v1_evaluator_metric_delta_zero"] is True


def test_generated_public_safe_report_answers_required_questions(tmp_path: Path) -> None:
    module = _load_script_module()

    result = module.write_copy_backed_slot_verification_reports(
        REPO_ROOT,
        tmp_path / "copy-slice",
        tmp_path / "copy-doc.md",
    )
    summary = result["summary"]
    sidecars = (tmp_path / "copy-slice/verification-sidecars.jsonl").read_text(encoding="utf-8").splitlines()
    summary_md = (tmp_path / "copy-slice/summary.md").read_text(encoding="utf-8")
    next_change = (tmp_path / "copy-slice/recommended-next-change.md").read_text(encoding="utf-8")
    doc = (tmp_path / "copy-doc.md").read_text(encoding="utf-8")

    assert summary["enabled_scope"]["slot_paths"] == ["field", "query", "target"]
    assert summary["gold_verification"]["eligible_copy_event_count"] > 0
    assert summary["gold_verification"]["unique_verified_span_rate"] >= 0.70
    assert summary["prediction_verification"]["source_verified_prediction_count"] > 0
    assert summary["prediction_verification"]["source_verified_gold_mismatch_count"] >= 0
    assert summary["claims"]["prediction_rerun_performed"] is False
    assert summary["claims"]["runtime_integration_performed"] is False
    assert summary["claims"]["slot_performance_improvement_claim"] is False
    assert summary["v1_evaluator_metric_delta"]["zero_delta"] is True
    assert summary["recommended_next_change"]["change_id"] == "integrate-copy-backed-slot-verification-shadow-mode"
    assert sidecars
    assert "17-question closeout" in summary_md
    assert "source-backed provenance is not correctness" in next_change
    assert "Action stays disabled" in doc
    assert scan_paths([tmp_path / "copy-slice", tmp_path / "copy-doc.md"]).ok
