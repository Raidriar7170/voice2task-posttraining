from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/run_copy_backed_verification_shadow_mode.py"
COPY_SLICE_DIR = REPO_ROOT / "reports/public-sample/copy-backed-slot-verification-slice"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_copy_backed_verification_shadow_mode", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_shadow_mode_input_boundary_requires_ready_copy_slice() -> None:
    module = _load_script_module()

    boundary = module.validate_shadow_mode_inputs(REPO_ROOT)

    assert boundary["decision_label"] == "SHADOW_MODE_INPUT_BOUNDARY_PASSED"
    assert boundary["copy_slice_decision_label"] == "COPY_SLICE_READY_FOR_SHADOW_INTEGRATION"
    assert boundary["enabled_task_scoped_triples"] == [
        "extract:extract_page:target",
        "form_fill:fill_form:field",
        "search:search_web:query",
    ]
    assert boundary["action_enabled"] is False
    assert boundary["v1_evaluator_metric_delta_zero"] is True
    assert boundary["blocking_reasons"] == []


def test_shadow_mode_writes_one_sidecar_per_prediction_contract(tmp_path: Path) -> None:
    module = _load_script_module()

    result = module.write_copy_backed_verification_shadow_mode_reports(
        REPO_ROOT,
        tmp_path / "shadow",
        tmp_path / "shadow-doc.md",
    )
    summary = result["summary"]
    sidecars = _read_jsonl(tmp_path / "shadow/shadow-sidecars.jsonl")
    compatibility = json.loads((tmp_path / "shadow/shadow-compatibility.json").read_text(encoding="utf-8"))

    assert summary["decision_label"] == "SHADOW_MODE_READY_FOR_REVIEW"
    assert summary["sidecar_attachment"]["prediction_contract_count"] == 828
    assert summary["sidecar_attachment"]["shadow_sidecar_count"] == 828
    assert summary["sidecar_attachment"]["sidecar_attachment_rate"] == 1.0
    assert len(sidecars) == 828
    assert compatibility["prediction_contract_count"] == 828
    assert compatibility["raw_input_hashes_preserved"] is True
    assert compatibility["v1_evaluator_metric_delta"]["zero_delta"] is True

    first = sidecars[0]
    assert first["shadow_mode_enabled"] is True
    assert first["enforcement_enabled"] is False
    assert first["prediction_contract_hash"]
    assert first["input_hash"]
    assert isinstance(first["slot_diagnostics"], list)
    assert all("status" in diagnostic for diagnostic in first["slot_diagnostics"])


def test_shadow_mode_keeps_action_disabled_and_separates_correctness(tmp_path: Path) -> None:
    module = _load_script_module()

    result = module.write_copy_backed_verification_shadow_mode_reports(
        REPO_ROOT,
        tmp_path / "shadow",
        tmp_path / "shadow-doc.md",
    )
    summary = result["summary"]
    sidecars = _read_jsonl(tmp_path / "shadow/shadow-sidecars.jsonl")
    action_diagnostics = [
        diagnostic
        for sidecar in sidecars
        for diagnostic in sidecar["slot_diagnostics"]
        if diagnostic["slot_path"] == "action"
    ]

    assert summary["enabled_scope"]["slot_paths"] == ["field", "query", "target"]
    assert summary["action_shadow"]["enabled"] is False
    assert summary["action_shadow"]["source_verified_count"] == 0
    assert summary["shadow_metrics"]["source_verified_prediction_count"] == 376
    assert summary["shadow_metrics"]["source_verified_and_gold_correct_count"] == 347
    assert summary["shadow_metrics"]["source_verified_gold_mismatch_count"] == 29
    assert summary["gates"]["enforcement_enabled_count"] == 0
    assert summary["gates"]["provenance_false_accept_count"] == 0
    assert summary["gates"]["silent_fallback_count"] == 0
    assert action_diagnostics
    assert all(diagnostic["verification_enabled"] is False for diagnostic in action_diagnostics)
    assert all(diagnostic["provenance"] == "unresolved" for diagnostic in action_diagnostics)


def test_shadow_mode_blocks_invalid_copy_slice_boundary(tmp_path: Path) -> None:
    module = _load_script_module()
    invalid_copy_slice = tmp_path / "copy-slice"
    shutil.copytree(COPY_SLICE_DIR, invalid_copy_slice)
    summary_path = invalid_copy_slice / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["decision_label"] = "COPY_SLICE_PARTIAL_NEEDS_SCOPE_REFINEMENT"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = module.write_copy_backed_verification_shadow_mode_reports(
        REPO_ROOT,
        tmp_path / "blocked-shadow",
        tmp_path / "blocked-doc.md",
        copy_slice_dir=invalid_copy_slice,
    )

    assert result["blocked"]["decision"] == "SHADOW_MODE_BLOCKED_INVALID_INPUT"
    assert (tmp_path / "blocked-shadow/blocked.json").exists()
    assert not (tmp_path / "blocked-shadow/summary.json").exists()
    assert not (tmp_path / "blocked-shadow/shadow-sidecars.jsonl").exists()


def test_generated_shadow_report_surface_is_public_safe(tmp_path: Path) -> None:
    module = _load_script_module()

    result = module.write_copy_backed_verification_shadow_mode_reports(
        REPO_ROOT,
        tmp_path / "shadow",
        tmp_path / "shadow-doc.md",
    )
    summary = result["summary"]
    summary_md = (tmp_path / "shadow/summary.md").read_text(encoding="utf-8")
    next_change = (tmp_path / "shadow/recommended-next-change.md").read_text(encoding="utf-8")
    doc = (tmp_path / "shadow-doc.md").read_text(encoding="utf-8")

    assert summary["recommended_next_change"]["change_id"] == "review-copy-backed-shadow-mode-before-runtime-wiring"
    assert "Shadow mode is not enforcement" in summary_md
    assert "source-backed provenance is not correctness" in next_change
    assert "Action remains disabled" in doc
    assert scan_paths([tmp_path / "shadow", tmp_path / "shadow-doc.md"]).ok
