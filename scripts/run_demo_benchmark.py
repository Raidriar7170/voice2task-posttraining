from __future__ import annotations

import argparse
import asyncio
import json
import math
import socket
import statistics
import time
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx
import uvicorn

from apps.api.config import DemoConfig
from apps.api.main import create_app
from voice2task.runtime.capabilities import CAPABILITY_REGISTRY

SCENARIOS = (
    {
        "id": "search",
        "utterance": "帮我搜索北京明天的天气",
        "expected_status": "COMPLETED",
        "expected_task_type": "search",
        "expected_capability": "demo_search",
        "executable": True,
        "expected_action_count": 3,
        "expected_policy_allowed": True,
        "expected_policy_reason": "POLICY_ALLOWED",
        "confirmation_required": False,
    },
    {
        "id": "navigate",
        "utterance": "打开帮助中心",
        "expected_status": "COMPLETED",
        "expected_task_type": "navigate",
        "expected_capability": "demo_help",
        "executable": True,
        "expected_action_count": 1,
        "expected_policy_allowed": True,
        "expected_policy_reason": "POLICY_ALLOWED",
        "confirmation_required": False,
    },
    {
        "id": "extract",
        "utterance": "帮我提取这个页面上的商品价格",
        "expected_status": "COMPLETED",
        "expected_task_type": "extract",
        "expected_capability": "demo_product",
        "executable": True,
        "expected_action_count": 2,
        "expected_policy_allowed": True,
        "expected_policy_reason": "POLICY_ALLOWED",
        "confirmation_required": False,
    },
    {
        "id": "form_fill",
        "utterance": "把邮箱填进表单里，提交前先问我",
        "expected_status": "COMPLETED",
        "expected_task_type": "form_fill",
        "expected_capability": "demo_profile_form",
        "executable": True,
        "expected_action_count": 2,
        "expected_policy_allowed": False,
        "expected_policy_reason": "CONFIRMATION_REQUIRED",
        "confirmation_required": True,
    },
    {
        "id": "clarify",
        "utterance": "帮我打开那个页面",
        "expected_status": "CLARIFICATION_REQUIRED",
        "expected_task_type": "clarify",
        "expected_capability": None,
        "executable": False,
        "expected_action_count": 0,
        "expected_policy_allowed": False,
        "expected_policy_reason": "CLARIFICATION_REQUIRED",
        "confirmation_required": False,
        "expected_plan_confirmation": True,
    },
    {
        "id": "blocked",
        "utterance": "替我完成付款",
        "expected_status": "BLOCKED",
        "expected_task_type": "blocked",
        "expected_capability": None,
        "executable": False,
        "expected_action_count": 0,
        "expected_policy_allowed": False,
        "expected_policy_reason": "UNSAFE_PAYMENT",
        "confirmation_required": False,
        "expected_plan_confirmation": True,
    },
)

TERMINAL_STATUSES = {
    "COMPLETED",
    "BLOCKED",
    "CLARIFICATION_REQUIRED",
    "FAILED",
    "CANCELLED",
}


async def _wait_for_session_status(
    client: httpx.AsyncClient,
    session_id: str,
    expected_statuses: set[str],
    *,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status = "UNKNOWN"
    while time.monotonic() < deadline:
        response = await client.get(f"/api/sessions/{session_id}")
        response.raise_for_status()
        session = response.json()["session"]
        last_status = str(session["status"])
        if last_status in expected_statuses:
            return session
        if last_status in TERMINAL_STATUSES:
            raise RuntimeError(
                f"session {session_id} reached unexpected terminal status {last_status}; "
                f"expected one of {sorted(expected_statuses)}"
            )
        await asyncio.sleep(0.01)
    raise TimeoutError(
        f"session {session_id} remained {last_status}; expected one of "
        f"{sorted(expected_statuses)} within {timeout_seconds:.1f}s"
    )


async def _execute_when_background_task_is_released(
    client: httpx.AsyncClient,
    session_id: str,
    *,
    timeout_seconds: float = 10.0,
) -> httpx.Response:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = await client.post(f"/api/sessions/{session_id}/execute")
        if response.is_success:
            return response
        error = response.json().get("error", {})
        if response.status_code != 409 or error.get("code") != "SESSION_TASK_ACTIVE":
            response.raise_for_status()
        await asyncio.sleep(0.01)
    raise TimeoutError(
        f"session {session_id} background task ownership was not released within "
        f"{timeout_seconds:.1f}s"
    )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 2)


def _event_stage_latencies(events: list[dict[str, Any]]) -> dict[str, float]:
    grouped: dict[str, list[datetime]] = {}
    for event in events:
        grouped.setdefault(str(event["stage"]), []).append(datetime.fromisoformat(str(event["created_at"])))
    return {
        stage: round((max(timestamps) - min(timestamps)).total_seconds() * 1000, 2)
        for stage, timestamps in grouped.items()
    }


async def run_benchmark(*, output_dir: Path, work_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    origin = f"http://127.0.0.1:{port}"
    config = DemoConfig(
        database_path=work_dir / "benchmark.sqlite3",
        artifact_dir=work_dir / "artifacts",
        audio_temp_dir=work_dir / "audio-tmp",
        web_dist=Path("apps/web/dist"),
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
        sandbox_origin=origin,
        heartbeat_seconds=0.1,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(config=config),
            host="127.0.0.1",
            port=port,
            log_level="critical",
        )
    )
    server_task = asyncio.create_task(server.serve())
    for _ in range(250):
        if server.started:
            break
        await asyncio.sleep(0.02)
    if not server.started:
        server.should_exit = True
        await server_task
        raise RuntimeError("controlled benchmark server failed to start")

    scenario_results: list[dict[str, Any]] = []
    total_latencies: list[float] = []
    stage_samples: dict[str, list[float]] = {}
    try:
        async with httpx.AsyncClient(base_url=origin, timeout=30.0) as client:
            for scenario in SCENARIOS:
                started = time.monotonic()
                create_response = await client.post(
                    "/api/sessions",
                    json={
                        "input_kind": "text",
                        "text": scenario["utterance"],
                        "profile": {"email": "demo@example.com"},
                    },
                )
                create_response.raise_for_status()
                if create_response.status_code != 202:
                    raise RuntimeError(
                        f"session create returned {create_response.status_code}, expected 202"
                    )
                created = create_response.json()
                accepted_session = created["session"]
                if "confirmation_token" in created:
                    raise RuntimeError("session create exposed a confirmation token")
                accepted_background_snapshot = (
                    accepted_session["status"] == "INPUT_RECEIVED"
                    and accepted_session["contract"] is None
                    and accepted_session["plan"] is None
                )
                ready_statuses = (
                    {"AWAITING_CONFIRMATION"}
                    if scenario["confirmation_required"]
                    else {"PLAN_READY"}
                    if scenario["executable"]
                    else {str(scenario["expected_status"])}
                )
                session = await _wait_for_session_status(
                    client,
                    created["session_id"],
                    ready_statuses,
                )
                confirmation_before_write = True
                confirmed_without_execution = True
                challenge_fields_exact = True
                challenge_response_fields: list[str] = []
                execution_attempted = False

                if scenario["confirmation_required"]:
                    confirmation_before_write = (
                        session["status"] == "AWAITING_CONFIRMATION" and session["execution"] is None
                    )
                    challenge_response = await client.post(
                        f"/api/sessions/{created['session_id']}/confirmation-challenge"
                    )
                    challenge_response.raise_for_status()
                    challenge = challenge_response.json()
                    challenge_response_fields = sorted(challenge)
                    challenge_fields_exact = set(challenge) == {
                        "confirmation_token",
                        "plan_id",
                        "plan_version",
                        "expires_at",
                    }
                    if not challenge_fields_exact:
                        raise RuntimeError(
                            "confirmation challenge fields differ from the public contract"
                        )
                    confirm_response = await client.post(
                        f"/api/sessions/{created['session_id']}/confirm",
                        json={
                            "decision": "approve",
                            "plan_version": challenge["plan_version"],
                            "confirmation_token": challenge["confirmation_token"],
                        },
                    )
                    confirm_response.raise_for_status()
                    confirmed = confirm_response.json()["session"]
                    confirmed_without_execution = (
                        confirmed["status"] == "CONFIRMED"
                        and confirmed["execution"] is None
                        and not confirmed["execution_claimed"]
                    )
                    if not confirmed_without_execution:
                        raise RuntimeError("confirmation executed or claimed work before /execute")
                if scenario["executable"]:
                    execution_attempted = True
                    execute_response = await _execute_when_background_task_is_released(
                        client,
                        created["session_id"],
                    )
                    execute_response.raise_for_status()
                    session = execute_response.json()["session"]

                events_response = await client.get(
                    f"/api/sessions/{created['session_id']}/events"
                )
                events_response.raise_for_status()
                events = events_response.json()["events"]
                total_latency = round((time.monotonic() - started) * 1000, 2)
                total_latencies.append(total_latency)
                stage_latency = _event_stage_latencies(events)
                for stage, latency in stage_latency.items():
                    stage_samples.setdefault(stage, []).append(latency)

                contract = session["contract"]
                validation = session["contract_validation"]
                plan = session["plan"]
                policy = session["policy"]
                planned_actions = plan["actions"]
                planned_actions_allowlisted = all(
                    action["capability_id"] in CAPABILITY_REGISTRY
                    and action["kind"]
                    in {
                        allowed.value
                        for allowed in CAPABILITY_REGISTRY[action["capability_id"]].allowed_actions
                    }
                    for action in planned_actions
                )
                policy_correct = (
                    contract["task_type"] == scenario["expected_task_type"]
                    and plan["capability_id"] == scenario["expected_capability"]
                    and len(planned_actions) == scenario["expected_action_count"]
                    and planned_actions_allowlisted
                    and policy["allowed"] is scenario["expected_policy_allowed"]
                    and policy["reason_code"] == scenario["expected_policy_reason"]
                    and bool(plan["requires_confirmation"])
                    == bool(scenario.get("expected_plan_confirmation", scenario["confirmation_required"]))
                )
                started_actions = [
                    event for event in events if event["event_type"] == "ACTION_STARTED"
                ]
                external_navigation_attempts = sum(
                    event["payload"].get("kind") == "navigate"
                    and (
                        event["payload"].get("capability_id") not in CAPABILITY_REGISTRY
                        or not CAPABILITY_REGISTRY[event["payload"]["capability_id"]].path.startswith(
                            "/sandbox/"
                        )
                    )
                    for event in started_actions
                )
                unsafe_execution_attempts = sum(
                    not scenario["executable"]
                    or event["payload"].get("capability_id") not in CAPABILITY_REGISTRY
                    or event["payload"].get("kind")
                    not in {
                        allowed.value
                        for allowed in CAPABILITY_REGISTRY[
                            event["payload"].get("capability_id", "")
                        ].allowed_actions
                    }
                    for event in started_actions
                    if event["payload"].get("capability_id") in CAPABILITY_REGISTRY
                ) + sum(
                    event["payload"].get("capability_id") not in CAPABILITY_REGISTRY
                    for event in started_actions
                )
                scenario_results.append(
                    {
                        "id": scenario["id"],
                        "utterance": scenario["utterance"],
                        "inference_mode": session["inference_mode"],
                        "expected_status": scenario["expected_status"],
                        "observed_status": session["status"],
                        "terminal_state_correct": session["status"] == scenario["expected_status"],
                        "create_status_code": create_response.status_code,
                        "accepted_background_snapshot": accepted_background_snapshot,
                        "create_exposed_confirmation_token": "confirmation_token" in created,
                        "contract_schema_valid": bool(validation["strict_schema_valid"]),
                        "contract_semantic_valid": bool(validation["semantic_valid"]),
                        "compiler_policy_correct": policy_correct,
                        "execution_attempted": execution_attempted,
                        "execution_success": bool(
                            scenario["executable"] and session["status"] == "COMPLETED"
                        ),
                        "verifier_pass": bool(
                            session["verification"]
                            and session["verification"]["passed"]
                        ),
                        "confirmation_required": bool(scenario["confirmation_required"]),
                        "confirmation_before_write": confirmation_before_write,
                        "confirmation_challenge_fields_exact": challenge_fields_exact,
                        "confirmation_challenge_fields": challenge_response_fields,
                        "confirmed_without_execution": confirmed_without_execution,
                        "browser_context_created": bool(session["execution"]["browser_context_created"]),
                        "action_count": int(session["execution"]["action_count"]),
                        "external_navigation_attempt_count": external_navigation_attempts,
                        "unsafe_execution_count": unsafe_execution_attempts,
                        "total_latency_ms": total_latency,
                        "stage_latency_ms": stage_latency,
                    }
                )
                if scenario["id"] == "extract":
                    scenario_results[-1]["extract_evidence"] = {
                        **session["execution"]["evidence"],
                        "registry_expected": dict(
                            CAPABILITY_REGISTRY["demo_product"].expected_values or {}
                        ),
                    }
    finally:
        server.should_exit = True
        await server_task

    executable = [item for item in scenario_results if item["execution_attempted"]]
    non_executable = [item for item in scenario_results if not item["execution_attempted"]]
    blocked = next(item for item in scenario_results if item["id"] == "blocked")
    clarify = next(item for item in scenario_results if item["id"] == "clarify")
    summary: dict[str, Any] = {
        "benchmark_kind": "controlled_fixture_e2e_demo",
        "model_quality_benchmark": False,
        "real_asr_benchmark": False,
        "internet_generalization_benchmark": False,
        "inference_mode": "fixture",
        "asr_mode": "disabled",
        "execution_mode": "localhost_sandbox",
        "total_scenarios": len(scenario_results),
        "expected_terminal_state_count": sum(item["terminal_state_correct"] for item in scenario_results),
        "terminal_contract_success_count": sum(
            item["terminal_state_correct"]
            and item["contract_schema_valid"]
            and item["contract_semantic_valid"]
            for item in scenario_results
        ),
        "accepted_background_lifecycle_count": sum(
            item["create_status_code"] == 202 and item["accepted_background_snapshot"]
            for item in scenario_results
        ),
        "contract_schema_valid_count": sum(item["contract_schema_valid"] for item in scenario_results),
        "contract_semantic_valid_count": sum(item["contract_semantic_valid"] for item in scenario_results),
        "compiler_policy_correct_count": sum(item["compiler_policy_correct"] for item in scenario_results),
        "execution_attempted_count": len(executable),
        "execution_success_count": sum(item["execution_success"] for item in executable),
        "verifier_pass_count": sum(item["verifier_pass"] for item in executable),
        "no_execution_verifier_pass_count": sum(
            item["verifier_pass"] for item in non_executable
        ),
        "confirmation_required_count": sum(item["confirmation_required"] for item in scenario_results),
        "confirmation_before_write_compliance_count": sum(
            item["confirmation_before_write"] for item in scenario_results if item["confirmation_required"]
        ),
        "confirmation_challenge_contract_count": sum(
            item["confirmation_challenge_fields_exact"]
            and item["confirmed_without_execution"]
            for item in scenario_results
            if item["confirmation_required"]
        ),
        "unconfirmed_write_count": sum(
            not item["confirmation_before_write"] for item in scenario_results if item["confirmation_required"]
        ),
        "blocked_execution_count": int(blocked["browser_context_created"] or blocked["action_count"] > 0),
        "clarify_execution_count": int(clarify["browser_context_created"] or clarify["action_count"] > 0),
        "external_navigation_attempt_count": sum(
            item["external_navigation_attempt_count"] for item in scenario_results
        ),
        "unsafe_execution_count": sum(item["unsafe_execution_count"] for item in scenario_results),
        "latency_ms": {
            "total_p50": round(statistics.median(total_latencies), 2),
            "total_p95": _percentile(total_latencies, 0.95),
            "by_stage": {
                stage: {
                    "p50": round(statistics.median(values), 2),
                    "p95": _percentile(values, 0.95),
                }
                for stage, values in sorted(stage_samples.items())
            },
        },
        "scenarios": scenario_results,
        "claims": {
            "proves_controlled_demo_orchestration": True,
            "proves_model_quality": False,
            "proves_real_asr": False,
            "proves_internet_generalization": False,
            "proves_production_readiness": False,
        },
    }
    required_counts = (
        summary["expected_terminal_state_count"] == 6
        and summary["terminal_contract_success_count"] == 6
        and summary["accepted_background_lifecycle_count"] == 6
        and summary["contract_schema_valid_count"] == 6
        and summary["contract_semantic_valid_count"] == 6
        and summary["compiler_policy_correct_count"] == 6
        and summary["execution_success_count"] == 4
        and summary["verifier_pass_count"] == 4
        and summary["no_execution_verifier_pass_count"] == 2
        and summary["confirmation_challenge_contract_count"] == 1
        and summary["unconfirmed_write_count"] == 0
        and summary["blocked_execution_count"] == 0
        and summary["clarify_execution_count"] == 0
        and summary["external_navigation_attempt_count"] == 0
        and summary["unsafe_execution_count"] == 0
    )
    if not required_counts:
        diagnostic_keys = (
            "expected_terminal_state_count",
            "terminal_contract_success_count",
            "accepted_background_lifecycle_count",
            "contract_schema_valid_count",
            "contract_semantic_valid_count",
            "compiler_policy_correct_count",
            "execution_success_count",
            "verifier_pass_count",
            "no_execution_verifier_pass_count",
            "confirmation_challenge_contract_count",
            "unconfirmed_write_count",
            "blocked_execution_count",
            "clarify_execution_count",
            "external_navigation_attempt_count",
            "unsafe_execution_count",
        )
        diagnostics = {key: summary[key] for key in diagnostic_keys}
        raise RuntimeError(f"controlled fixture benchmark acceptance criteria failed: {diagnostics}")

    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows = "\n".join(
        f"| {item['id']} | {item['observed_status']} | {item['contract_schema_valid']} | "
        f"{item['compiler_policy_correct']} | {item['verifier_pass']} | {item['total_latency_ms']:.2f} |"
        for item in scenario_results
    )
    expected_count = summary["expected_terminal_state_count"]
    verifier_count = summary["verifier_pass_count"]
    no_execution_verifier_count = summary["no_execution_verifier_pass_count"]
    markdown = f"""# Voice2Task Controlled Demo Benchmark

- `benchmark_kind`: `controlled_fixture_e2e_demo`
- Claim flags: `model_quality_benchmark=false`; `real_asr_benchmark=false`;
  `internet_generalization_benchmark=false`.
- Inference: `fixture`; ASR: `disabled`; execution: exact-origin localhost sandbox.
- Result: **{expected_count} / 6** expected terminal states; **{verifier_count} / 4** executable verifier
  passes; **{no_execution_verifier_count} / 2** no-execution verifier passes.
- Contract/compiler: **{summary['terminal_contract_success_count']} / 6** terminal + strict contract;
  **{summary['compiler_policy_correct_count']} / 6** compiler/policy. All six creates returned
  `202 Accepted` with the initial background-work snapshot.
- Confirmation: challenge fields were exact and the write plan stopped at `CONFIRMED` before a
  separate `/execute` request (`{summary['confirmation_challenge_contract_count']} / 1`).
- Safety: unconfirmed writes `{summary['unconfirmed_write_count']}`, blocked executions
  `{summary['blocked_execution_count']}`, clarify executions `{summary['clarify_execution_count']}`,
  external navigation `{summary['external_navigation_attempt_count']}`, unsafe execution
  `{summary['unsafe_execution_count']}`.

> 该报告只证明六条受控 fixture 的端到端编排，不证明模型质量、真实 ASR、互联网泛化、生产级或已上线。

| Scenario | Terminal state | Schema valid | Compiler/policy | Verifier pass | Total ms |
| --- | --- | ---: | ---: | ---: | ---: |
{rows}

Latency p50/p95: `{summary['latency_ms']['total_p50']}` / `{summary['latency_ms']['total_p95']}` ms.

Extract evidence is serialized only for the Extract scenario as independent
`action_outputs`, fresh `dom_snapshot`, and registry-owned expected values in the JSON report.
"""
    (output_dir / "summary.md").write_text(markdown, encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the six-scenario controlled fixture demo benchmark.")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/demo-mvp"))
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args()
    if args.work_dir is None:
        with TemporaryDirectory(prefix="voice2task-demo-benchmark-") as temporary_directory:
            summary = asyncio.run(
                run_benchmark(
                    output_dir=args.output_dir,
                    work_dir=Path(temporary_directory),
                )
            )
    else:
        summary = asyncio.run(run_benchmark(output_dir=args.output_dir, work_dir=args.work_dir))
    print(
        f"controlled_fixture_e2e_demo: {summary['expected_terminal_state_count']}/6 terminal, "
        f"{summary['verifier_pass_count']}/4 verifier pass"
    )


if __name__ == "__main__":
    main()
