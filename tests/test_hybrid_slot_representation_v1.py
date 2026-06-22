from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/design_hybrid_slot_representation_v1.py"
OUTPUT_DIR = REPO_ROOT / "reports/public-sample/hybrid-slot-representation-v1"
DOC_PATH = REPO_ROOT / "docs/hybrid-slot-representation-v1.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("design_hybrid_slot_representation_v1", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_input_boundary_accepts_only_current_authoritative_evidence() -> None:
    module = _load_module()

    boundary = module.validate_hybrid_design_inputs(REPO_ROOT)

    assert boundary["decision_label"] == "HYBRID_DESIGN_INPUT_BOUNDARY_PASSED"
    assert boundary["recovered_prediction_inputs_available"] is True
    assert boundary["metric_reproduction_status"] == "reproduced"
    assert boundary["slot_analysis_decision_label"] == "MIXED_SLOT_REPRESENTATION_REQUIRED"
    assert boundary["external_schema"] == "BrowserTaskContract V1"
    assert boundary["training_target_changed"] is False
    assert boundary["contract_core_v2_changed"] is False
    assert boundary["blocking_reasons"] == []


def test_hybrid_slot_value_field_ownership_and_span_semantics_are_verifier_owned() -> None:
    module = _load_module()

    design = module.build_hybrid_slot_representation_design(REPO_ROOT)
    fields = {field["name"]: field for field in design["hybrid_slot_value"]["fields"]}

    assert list(fields) == [
        "value",
        "value_type",
        "representation_kind",
        "source_span",
        "normalization_rule",
        "verification_status",
        "provenance",
        "fallback_behavior",
    ]
    assert fields["value"]["owner"] == "model"
    for name in (
        "value_type",
        "representation_kind",
        "source_span",
        "normalization_rule",
        "verification_status",
        "provenance",
        "fallback_behavior",
    ):
        assert fields[name]["owner"] == "system"

    assert design["source_span_semantics"] == {
        "source_basis": "original_input_text_or_fixed_sanitized_transcript",
        "offset_unit": "unicode_character",
        "start": "inclusive",
        "end": "exclusive",
        "requires_source_text_hash": True,
        "requires_exact_back_slice": True,
        "allows_similarity_only": False,
        "allows_discontiguous_span": False,
    }
    assert module.verify_half_open_span("搜索北京天气", 2, 4, "北京") is True
    assert module.verify_half_open_span("搜索北京天气", 2, 3, "北京") is False


def test_representation_matrix_is_deterministic_and_covers_required_paths() -> None:
    module = _load_module()

    first = module.build_hybrid_slot_representation_design(REPO_ROOT)["representation_matrix"]
    second = module.build_hybrid_slot_representation_design(REPO_ROOT)["representation_matrix"]

    assert first == second
    assert len({(row["slot_path"], row["task_type_scope"]) for row in first}) == len(first)
    paths = {row["slot_path"] for row in first}
    assert {"query", "field", "target", "action", "url", "ambiguity", "reason"}.issubset(paths)
    assert all(isinstance(row["proposed_representation"], str) for row in first)
    assert all("," not in row["proposed_representation"] for row in first)

    by_path = {row["slot_path"]: row for row in first}
    assert by_path["query"]["proposed_representation"] == "copy"
    assert by_path["field"]["proposed_representation"] == "copy"
    assert by_path["target"]["proposed_representation"] == "copy"
    assert by_path["action"]["proposed_representation"] == "copy"
    assert by_path["ambiguity"]["proposed_representation"] == "bounded_structured"
    assert by_path["reason"]["proposed_representation"] == "bounded_structured"
    assert by_path["url"]["proposed_representation"] == "unresolved"
    assert by_path["city"]["proposed_representation"] == "task_schema_constrained"


def test_task_specific_key_policy_uses_gold_contract_presence_not_profile_cooccurrence() -> None:
    module = _load_module()

    policies = {
        policy["task_type_scope"]: policy
        for policy in module.build_hybrid_slot_representation_design(REPO_ROOT)["task_specific_key_policy"]
    }

    assert policies["search:search_web"]["required_slot_keys"] == ["query"]
    assert policies["navigate:open_url"]["required_slot_keys"] == ["url"]
    assert policies["form_fill:fill_form"]["required_slot_keys"] == ["field"]
    assert policies["extract:extract_page"]["required_slot_keys"] == ["target"]
    assert policies["clarify:clarify"]["required_slot_keys"] == ["ambiguity"]
    assert policies["blocked:deny"]["required_slot_keys"] == ["reason"]
    assert policies["blocked:deny"]["optional_slot_keys"] == ["action"]
    assert policies["clarify:clarify"]["optional_slot_keys"] == []


def test_feasibility_projection_quantifies_coverage_without_success_metric_recalculation(tmp_path: Path) -> None:
    module = _load_module()

    result = module.write_hybrid_slot_representation_reports(REPO_ROOT, tmp_path / "reports", tmp_path / "design.md")
    projection = result["feasibility_projection"]
    summary = result["summary"]

    assert summary["decision_label"] == "HYBRID_DESIGN_READY_COPY_SLICE_FIRST"
    assert summary["claims"]["training_performed"] is False
    assert summary["claims"]["prediction_rerun_performed"] is False
    assert summary["claims"]["schema_migration_performed"] is False
    assert summary["claims"]["model_improvement_claim"] is False
    assert summary["claims"]["slot_performance_improvement_claim"] is False
    assert projection["gold_slot_event_count"] == 471
    assert projection["prediction_slot_event_count"] == 942
    assert projection["coverage"]["overall_representation_coverage"] == 1.0
    assert projection["coverage"]["copy_backed_rate"] > 0.45
    assert projection["coverage"]["bounded_structured_rate"] > 0.30
    assert projection["coverage"]["limited_free_generation_rate"] == 0.0
    assert projection["coverage"]["unresolved_rate"] > 0.0
    assert projection["prediction_verification"]["currently_verifiable_prediction_rate"] > 0.5
    assert projection["prediction_verification"]["currently_fail_closed_prediction_rate"] > 0.3
    assert projection["does_not_recalculate_model_success_metrics"] is True

    assert (tmp_path / "reports/summary.json").exists()
    assert (tmp_path / "reports/representation-matrix.json").exists()
    assert (tmp_path / "reports/feasibility-projection.json").exists()
    assert (tmp_path / "reports/recommended-next-change.md").exists()
    assert (tmp_path / "design.md").exists()
    assert not (tmp_path / "reports/blocked.json").exists()


def test_generated_report_surface_is_public_safe_and_has_required_answers() -> None:
    module = _load_module()

    summary = module.write_hybrid_slot_representation_reports(REPO_ROOT, OUTPUT_DIR, DOC_PATH)["summary"]
    matrix = json.loads((OUTPUT_DIR / "representation-matrix.json").read_text(encoding="utf-8"))
    projection = json.loads((OUTPUT_DIR / "feasibility-projection.json").read_text(encoding="utf-8"))
    doc = DOC_PATH.read_text(encoding="utf-8")

    assert summary["recommended_next_change"]["change_id"] == "implement-copy-backed-slot-verification-slice"
    assert summary["fallback_next_change"]["change_id"] == "implement-task-specific-slot-schema-validator"
    assert summary["why_not_full_hybrid_system_now"]
    assert projection["does_not_mutate_predictions"] is True
    assert projection["does_not_recalculate_model_success_metrics"] is True
    assert len(matrix) >= 8
    assert "Model-authored vs system-derived fields" in doc
    assert "模型不需要直接输出 offsets" in doc
    assert "Current claims that remain unsupported" in doc
    assert scan_paths([OUTPUT_DIR, DOC_PATH]).ok
