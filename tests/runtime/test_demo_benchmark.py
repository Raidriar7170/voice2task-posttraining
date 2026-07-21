from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import scripts.run_demo_benchmark as benchmark_module
from scripts.run_demo_benchmark import run_benchmark


@pytest.mark.asyncio
async def test_controlled_demo_benchmark_runs_exact_six_real_api_scenarios(tmp_path) -> None:
    output_dir = tmp_path / "report"
    summary = await run_benchmark(output_dir=output_dir, work_dir=tmp_path / "runtime")

    assert summary["benchmark_kind"] == "controlled_fixture_e2e_demo"
    assert summary["model_quality_benchmark"] is False
    assert summary["real_asr_benchmark"] is False
    assert summary["internet_generalization_benchmark"] is False
    assert summary["total_scenarios"] == 6
    assert summary["expected_terminal_state_count"] == 6
    assert summary["terminal_contract_success_count"] == 6
    assert summary["accepted_background_lifecycle_count"] == 6
    assert summary["contract_schema_valid_count"] == 6
    assert summary["contract_semantic_valid_count"] == 6
    assert summary["compiler_policy_correct_count"] == 6
    assert summary["execution_attempted_count"] == 4
    assert summary["execution_success_count"] == 4
    assert summary["verifier_pass_count"] == 4
    assert summary["no_execution_verifier_pass_count"] == 2
    assert summary["confirmation_required_count"] == 1
    assert summary["confirmation_challenge_contract_count"] == 1
    assert summary["confirmation_pre_policy_correct_count"] == 1
    assert summary["confirmation_effective_policy_persisted_count"] == 1
    assert summary["confirmation_policy_event_order_count"] == 1
    assert summary["unconfirmed_write_count"] == 0
    assert summary["blocked_execution_count"] == 0
    assert summary["clarify_execution_count"] == 0
    assert summary["external_navigation_attempt_count"] == 0
    assert summary["unsafe_execution_count"] == 0
    assert len(summary["scenarios"]) == 6
    assert all(item["create_status_code"] == 202 for item in summary["scenarios"])
    assert all(item["accepted_background_snapshot"] for item in summary["scenarios"])
    assert all(not item["create_exposed_confirmation_token"] for item in summary["scenarios"])
    assert all(item["confirmation_challenge_fields_exact"] for item in summary["scenarios"])
    assert all(item["confirmed_without_execution"] for item in summary["scenarios"])
    form = next(item for item in summary["scenarios"] if item["id"] == "form_fill")
    assert form["confirmation_challenge_fields"] == [
        "confirmation_token",
        "expires_at",
        "plan_id",
        "plan_version",
    ]
    assert form["pre_confirmation_policy_correct"] is True
    assert form["effective_confirmation_policy_persisted"] is True
    assert form["confirmation_policy_event_ordered"] is True
    confirmation_only_fields = {
        "pre_confirmation_policy_correct",
        "effective_confirmation_policy_persisted",
        "confirmation_policy_event_ordered",
    }
    assert all(
        confirmation_only_fields.isdisjoint(item)
        for item in summary["scenarios"]
        if not item["confirmation_required"]
    )
    extract = next(item for item in summary["scenarios"] if item["id"] == "extract")
    assert extract["extract_evidence"] == {
        "action_outputs": {"product_price": "¥199.00"},
        "dom_snapshot": {"product_price": "¥199.00"},
        "registry_expected": {"product_price": "¥199.00"},
    }
    assert all("extract_evidence" not in item for item in summary["scenarios"] if item != extract)
    assert {item["expected_status"] for item in summary["scenarios"]} == {
        "COMPLETED",
        "CLARIFICATION_REQUIRED",
        "BLOCKED",
    }
    assert summary["latency_ms"]["total_p50"] >= 0
    assert summary["latency_ms"]["total_p95"] >= summary["latency_ms"]["total_p50"]

    disk_summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert disk_summary == summary
    assert "controlled_fixture_e2e_demo" in markdown
    assert "不证明模型质量" in markdown
    assert "6 / 6" in markdown
    assert "202 Accepted" in markdown
    assert "stopped at `CONFIRMED`" in markdown
    assert "effective `POLICY_ALLOWED`" in markdown
    assert "independent" in markdown


def test_benchmark_cli_default_runtime_directory_is_disposable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed_work_dir: Path | None = None

    async def fake_run_benchmark(*, output_dir: Path, work_dir: Path) -> dict[str, object]:
        nonlocal observed_work_dir
        observed_work_dir = work_dir
        assert output_dir == tmp_path / "report"
        assert work_dir.is_dir()
        return {"expected_terminal_state_count": 6, "verifier_pass_count": 4}

    monkeypatch.setattr(benchmark_module, "run_benchmark", fake_run_benchmark)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_demo_benchmark.py", "--output-dir", str(tmp_path / "report")],
    )

    benchmark_module.main()

    assert observed_work_dir is not None
    assert not observed_work_dir.exists()
