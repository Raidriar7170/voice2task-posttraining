from __future__ import annotations

import importlib.util
import inspect
import json
import shutil
from pathlib import Path
from typing import Any

from voice2task.leak_scan import scan_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/review_copy_backed_shadow_mode_before_runtime_wiring.py"
POLICY_PATH = REPO_ROOT / "configs/copy-backed-scope-policy-v1.json"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("review_copy_backed_shadow_mode_before_runtime_wiring", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _contract(task_type: str, route: str, slots: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_type": task_type,
        "route": route,
        "safety": {"allow": task_type != "blocked", "reason": "test fixture"},
        "confirmation_required": False,
        "slots": slots,
        "normalized_command": "test fixture",
        "language": "zh-CN",
        "contract_version": "v1",
    }


def _assert_no_gold_or_correctness_fields(value: Any) -> None:
    blocked_fragments = ("gold", "correct", "accuracy", "score", "evaluator")
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = key.lower()
            assert not any(fragment in lowered for fragment in blocked_fragments), key
            _assert_no_gold_or_correctness_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_gold_or_correctness_fields(nested)


def test_online_sidecar_generation_has_no_gold_dependency() -> None:
    from voice2task.copy_backed_shadow_interface import (
        generate_online_shadow_sidecar,
        load_scope_policy,
        validate_scope_policy,
    )

    signature = inspect.signature(generate_online_shadow_sidecar)
    assert all("gold" not in name.lower() for name in signature.parameters)
    assert all("evaluator" not in name.lower() for name in signature.parameters)

    policy = load_scope_policy(POLICY_PATH)
    assert validate_scope_policy(policy)["ok"] is True
    sidecar = generate_online_shadow_sidecar(
        "帮我搜索北京天气",
        _contract("search", "search_web", {"query": "北京天气"}),
        request_id="req-1",
        sample_id="sample-1",
        split="dev",
        run_role="control",
        scope_policy=policy,
    )

    _assert_no_gold_or_correctness_fields(sidecar)
    diagnostic = sidecar["slot_diagnostics"][0]
    assert diagnostic["policy_enabled"] is True
    assert diagnostic["status"] == "VERIFIED_EXACT_UNIQUE"
    assert diagnostic["trusted_provenance"] is True
    assert diagnostic["candidate_provenance"] is False
    assert diagnostic["source_span"]["text"] == "北京天气"


def test_normalized_candidate_and_disabled_action_are_not_trusted() -> None:
    from voice2task.copy_backed_shadow_interface import generate_online_shadow_sidecar, load_scope_policy

    policy = load_scope_policy(POLICY_PATH)

    normalized = generate_online_shadow_sidecar(
        "字段是 A B",
        _contract("form_fill", "fill_form", {"field": "AB"}),
        request_id="req-2",
        scope_policy=policy,
    )["slot_diagnostics"][0]
    assert normalized["status"] == "VERIFIED_NORMALIZED_UNIQUE"
    assert normalized["trusted_provenance"] is False
    assert normalized["candidate_provenance"] is True
    assert normalized["normalization_rule"] == "nfkc_casefold_strip_space_punct"

    action = generate_online_shadow_sidecar(
        "请取消订单",
        _contract("blocked", "deny", {"action": "取消订单"}),
        request_id="req-3",
        scope_policy=policy,
    )["slot_diagnostics"][0]
    assert action["policy_enabled"] is False
    assert action["trusted_provenance"] is False
    assert action["candidate_provenance"] is False
    assert action["status"] == "OUT_OF_SCOPE"


def test_tampered_trusted_span_is_counted_as_false_accept() -> None:
    from voice2task.copy_backed_shadow_interface import (
        count_provenance_false_accepts,
        generate_online_shadow_sidecar,
        load_scope_policy,
    )

    policy = load_scope_policy(POLICY_PATH)
    sidecar = generate_online_shadow_sidecar(
        "提取目标是价格",
        _contract("extract", "extract_page", {"target": "价格"}),
        request_id="req-4",
        scope_policy=policy,
    )
    assert count_provenance_false_accepts(sidecar, "提取目标是价格", policy) == 0

    sidecar["slot_diagnostics"][0]["source_span"]["text"] = "目标"
    assert count_provenance_false_accepts(sidecar, "提取目标是价格", policy) == 1

    status_tampered = generate_online_shadow_sidecar(
        "提取目标是价格",
        _contract("extract", "extract_page", {"target": "价格"}),
        request_id="req-4b",
        scope_policy=policy,
    )
    status_tampered["slot_diagnostics"][0]["match_kind"] = "normalized"
    assert count_provenance_false_accepts(status_tampered, "提取目标是价格", policy) == 1

    policy_tampered = generate_online_shadow_sidecar(
        "提取目标是价格",
        _contract("extract", "extract_page", {"target": "价格"}),
        request_id="req-4c",
        scope_policy=policy,
    )
    policy_tampered["policy_hash"] = "drifted"
    assert count_provenance_false_accepts(policy_tampered, "提取目标是价格", policy) == 1


def test_review_replay_writes_split_sidecar_and_audit_surfaces(tmp_path: Path) -> None:
    module = _load_script_module()

    result = module.write_copy_backed_shadow_review_reports(
        REPO_ROOT,
        tmp_path / "review",
        tmp_path / "shadow-interface.md",
        policy_path=POLICY_PATH,
    )
    summary = result["summary"]
    sidecars = _read_jsonl(tmp_path / "review/online-shadow-sidecars.jsonl")
    audits = _read_jsonl(tmp_path / "review/evaluation-audits.jsonl")
    interface_review = json.loads((tmp_path / "review/interface-review.json").read_text(encoding="utf-8"))
    per_scope = json.loads((tmp_path / "review/per-scope-metrics.json").read_text(encoding="utf-8"))
    latency = json.loads((tmp_path / "review/latency-benchmark.json").read_text(encoding="utf-8"))

    assert summary["decision_label"] == "SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK"
    assert summary["online_sidecar_count"] == 828
    assert len(sidecars) == 828
    assert summary["evaluation_audit_count"] == len(audits)
    assert summary["metrics"]["total_slot_event_count"] == 942
    assert summary["metrics"]["eligible_slot_event_count"] == 430
    assert summary["metrics"]["trusted_exact_count"] == 376
    assert summary["metrics"]["trusted_exact_rate"] == 376 / 430
    assert summary["metrics"]["eligible_verification_failure_count"] == 54
    assert summary["metrics"]["global_non_verified_count"] == 566
    assert summary["metrics"]["source_verified_gold_mismatch_rate"] == 29 / 376
    assert summary["gates"]["normalized_trusted_count"] == 0
    assert summary["gates"]["action_trusted_count"] == 0
    assert summary["gates"]["provenance_false_accept_count"] == 0
    assert summary["gates"]["silent_fallback_count"] == 0
    assert summary["gates"]["contract_mutation_count"] == 0
    assert summary["gates"]["runtime_decision_delta_count"] == 0
    assert summary["gates"]["v1_evaluator_metric_delta_zero"] is True
    assert summary["gates"]["deterministic_rerun_rate"] == 1.0
    assert interface_review["online_sidecar_has_no_gold_fields"] is True
    assert set(per_scope["enabled_scope_keys"]) == {
        "extract:extract_page:target",
        "form_fill:fill_form:field",
        "search:search_web:query",
    }
    assert latency["benchmark_kind"] == "local_cpu_microbenchmark_not_production_slo"
    assert latency["policy_lookup"]["p95_ms"] >= 0
    assert latency["long_chinese_input"]["input_char_count"] > 100

    _assert_no_gold_or_correctness_fields(sidecars[0])
    assert any("gold_correct_exact" in audit for audit in audits)
    assert scan_paths([tmp_path / "review", tmp_path / "shadow-interface.md"]).ok


def test_policy_drift_blocks_review(tmp_path: Path) -> None:
    module = _load_script_module()
    drifted_policy = tmp_path / "copy-backed-scope-policy-v1.json"
    shutil.copy2(POLICY_PATH, drifted_policy)
    policy = json.loads(drifted_policy.read_text(encoding="utf-8"))
    policy["enabled_triples"] = policy["enabled_triples"][:-1]
    drifted_policy.write_text(json.dumps(policy, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = module.write_copy_backed_shadow_review_reports(
        REPO_ROOT,
        tmp_path / "blocked",
        tmp_path / "blocked-doc.md",
        policy_path=drifted_policy,
    )

    assert result["blocked"]["decision"] == "SHADOW_REVIEW_BLOCKED_POLICY_DRIFT"
    assert (tmp_path / "blocked/blocked.json").exists()
    assert not (tmp_path / "blocked/summary.json").exists()
    assert not (tmp_path / "blocked/online-shadow-sidecars.jsonl").exists()
