from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from voice2task.copy_backed_shadow_interface import stable_hash
from voice2task.copy_backed_slot_verification import source_text_hash
from voice2task.schemas import as_contract, canonical_contract_json

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "configs/copy-backed-scope-policy-v1.json"
SCRIPT_PATH = REPO_ROOT / "scripts/generate_copy_shadow_template_disjoint_challenge.py"


def _load_script() -> Any:
    spec = importlib.util.spec_from_file_location("copy_shadow_template_disjoint_challenge", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _jsonl_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_template_disjoint_challenge_materialization_writes_required_rows_and_reports(tmp_path: Path) -> None:
    module = _load_script()
    challenge_path = tmp_path / "copy-shadow-template-disjoint-challenge-v1.jsonl"
    report_dir = tmp_path / "reports"

    summary = module.write_challenge_bundle(
        repo_root=REPO_ROOT,
        challenge_path=challenge_path,
        report_dir=report_dir,
        policy_path=POLICY_PATH,
    )

    rows = _jsonl_rows(challenge_path)
    assert summary["challenge_id"] == "copy-shadow-template-disjoint-challenge-v1"
    assert summary["row_count"] == 120
    assert len(rows) == 120
    assert len({row["challenge_id"] for row in rows}) == 120
    assert {row["challenge_version"] for row in rows} == {"copy-shadow-template-disjoint-challenge-v1"}
    required_fields = {
        "challenge_id",
        "challenge_version",
        "input_text",
        "task_type",
        "route",
        "slot_path",
        "gold_slot_value",
        "gold_contract",
        "scope_expected_enabled",
        "expected_gold_verification_class",
        "condition_tags",
        "public_safe",
        "template_signature",
        "input_hash",
        "gold_hash",
    }
    assert all(required_fields <= set(row) for row in rows)
    assert all(row["public_safe"] is True for row in rows)
    assert all(row["input_hash"] == source_text_hash(row["input_text"]) for row in rows)
    assert all(row["gold_hash"] == stable_hash(canonical_contract_json(row["gold_contract"])) for row in rows)
    for row in rows:
        contract = as_contract(row["gold_contract"]).to_dict()
        assert contract["task_type"] == row["task_type"]
        assert contract["route"] == row["route"]
        assert row["slot_path"] in contract["slots"]
        assert contract["slots"][row["slot_path"]] == row["gold_slot_value"]

    enabled_counts = summary["scope_counts"]["enabled"]
    assert enabled_counts == {
        "extract:extract_page:target": 30,
        "form_fill:fill_form:field": 30,
        "search:search_web:query": 30,
    }
    assert summary["scope_counts"]["disabled"] == {"blocked:deny:action": 30}

    condition_tags = {tag for row in rows for tag in row["condition_tags"]}
    assert {
        "exact_unique",
        "duplicate_exact",
        "source_absent",
        "multiple_entity_distractor",
        "partial_span_trap",
        "normalization_candidate",
        "normalization_collision",
        "long_input",
        "asr_style_noise",
        "synthetic_pii",
        "out_of_scope_action",
        "invalid_unparseable_output_fault_injection",
    } <= condition_tags

    expected_reports = {
        "challenge-manifest.json",
        "template-disjoint-audit.json",
        "challenge-summary.md",
        "challenge-summary.json",
        "per-scope-metrics.json",
        "per-condition-metrics.json",
        "latency-benchmark.json",
        "policy-freeze-audit.json",
        "privacy-audit.json",
        "recommended-next-change.md",
        "blocked.json",
    }
    assert expected_reports == {path.name for path in report_dir.iterdir() if path.is_file()}


def test_template_disjoint_challenge_reports_block_observed_inference_without_verified_adapters(
    tmp_path: Path,
) -> None:
    module = _load_script()
    challenge_path = tmp_path / "copy-shadow-template-disjoint-challenge-v1.jsonl"
    report_dir = tmp_path / "reports"

    summary = module.write_challenge_bundle(
        repo_root=REPO_ROOT,
        challenge_path=challenge_path,
        report_dir=report_dir,
        policy_path=POLICY_PATH,
    )

    blocked = json.loads((report_dir / "blocked.json").read_text(encoding="utf-8"))
    challenge_summary = json.loads((report_dir / "challenge-summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((report_dir / "challenge-manifest.json").read_text(encoding="utf-8"))
    disjoint = json.loads((report_dir / "template-disjoint-audit.json").read_text(encoding="utf-8"))
    freeze = json.loads((report_dir / "policy-freeze-audit.json").read_text(encoding="utf-8"))
    privacy = json.loads((report_dir / "privacy-audit.json").read_text(encoding="utf-8"))

    assert summary["decision_label"] == "CHALLENGE_EVALUATION_BLOCKED"
    assert challenge_summary["decision_label"] == "CHALLENGE_EVALUATION_BLOCKED"
    assert challenge_summary["observed_challenge_inference_blocked"] is True
    assert challenge_summary["canonical_prediction_hook_evaluated"] is False
    assert blocked["decision"] == "CHALLENGE_EVALUATION_BLOCKED"
    assert blocked["reason"] == "missing_loadable_frozen_adapters"
    assert blocked["fabricated_predictions"] is False
    assert blocked["training_run"] is False
    assert blocked["policy_modified"] is False
    assert manifest["challenge_hash"] == stable_hash(_jsonl_rows(challenge_path))
    assert disjoint["accepted"] is True
    assert disjoint["row_count"] == 120
    assert disjoint["overlap_counts"] == {
        "sample_id": 0,
        "exact_input_text": 0,
        "template_signature": 0,
        "slot_value_stripped_signature": 0,
    }
    assert disjoint["thresholds"] == {"char_3gram_jaccard_max": 0.8, "normalized_edit_similarity_max": 0.85}
    assert freeze["policy_loaded_once"] is True
    assert freeze["policy_start_hash"] == "5dc14efb8ded13dc048ddb067c7c63a1a62b6c03896950e861303973d505cbc7"
    assert freeze["policy_end_hash"] == freeze["policy_start_hash"]
    assert freeze["policy_drift_detected"] is False
    assert privacy["public_safe"] is True
    assert privacy["leak_scan"]["ok"] is True
    assert privacy["retains_full_input_text_in_sidecars"] is False
    assert privacy["retains_raw_model_output_in_sidecars"] is False


def test_template_disjoint_audit_detects_existing_slot_stripped_template_overlap(tmp_path: Path) -> None:
    module = _load_script()
    repo_root = tmp_path / "repo"
    public_dir = repo_root / "data/public-samples"
    public_dir.mkdir(parents=True)
    existing_contract = {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "fixture"},
        "confirmation_required": False,
        "slots": {"query": "旧值"},
        "normalized_command": "fixture",
        "language": "zh-CN",
        "contract_version": "v1",
    }
    (public_dir / "sft_public_sample.jsonl").write_text(
        json.dumps(
            {
                "id": "existing-row",
                "split": "test",
                "input_text": "模板分离挑战：请只复制唯一片段：旧值。",
                "target_contract": existing_contract,
                "provenance": {"public_safe": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    challenge_row = module._row(
        row_number=1,
        task_type="search",
        route="search_web",
        slot_path="query",
        input_text="模板分离挑战：请只复制唯一片段：新值。",
        slot_value="新值",
        expected_class="VERIFIED_EXACT_UNIQUE",
        condition_tags=["exact_unique", "scope:search:search_web:query"],
        scope_expected_enabled=True,
    )

    audit = module._template_disjoint_audit(repo_root, [challenge_row])

    assert audit["overlap_counts"]["template_signature"] == 1
    assert audit["overlap_counts"]["slot_value_stripped_signature"] == 1
    assert audit["accepted"] is False


def test_template_disjoint_challenge_refuses_to_freeze_when_audit_fails(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    module = _load_script()
    challenge_path = tmp_path / "copy-shadow-template-disjoint-challenge-v1.jsonl"
    report_dir = tmp_path / "reports"

    def failing_audit(repo_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "accepted": False,
            "overlap_counts": {
                "sample_id": 0,
                "exact_input_text": 1,
                "template_signature": 0,
                "slot_value_stripped_signature": 0,
            },
            "max_observed": {"char_3gram_jaccard": 0.0, "normalized_edit_similarity": 0.0},
        }

    monkeypatch.setattr(module, "_template_disjoint_audit", failing_audit)

    try:
        module.write_challenge_bundle(
            repo_root=REPO_ROOT,
            challenge_path=challenge_path,
            report_dir=report_dir,
            policy_path=POLICY_PATH,
        )
    except ValueError as exc:
        assert "template-disjoint audit failed" in str(exc)
    else:  # pragma: no cover - failure path assertion
        raise AssertionError("write_challenge_bundle must reject audit-failing rows")

    assert not challenge_path.exists()
    assert not report_dir.exists()
