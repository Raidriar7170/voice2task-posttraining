from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.config import DemoConfig
from apps.api.main import _session_payload, create_app
from voice2task.runtime.models import (
    ArtifactRecord,
    BrowserTaskContractPayload,
    EventType,
    ExecutionEvidence,
    ExecutionOutcome,
    ExecutionPlan,
    SessionContext,
    SessionRecord,
)

EventSink = Callable[[EventType, dict[str, object]], Awaitable[None]]
ArtifactSink = Callable[[ArtifactRecord], Awaitable[None]]


class FakeExecutor:
    def __init__(self, event_sink: EventSink, artifact_sink: ArtifactSink, artifact_dir: Path) -> None:
        self.event_sink = event_sink
        self.artifact_sink = artifact_sink
        self.artifact_dir = artifact_dir

    async def execute(
        self,
        plan: ExecutionPlan,
        *,
        contract: BrowserTaskContractPayload,
        context: SessionContext,
        confirmation_consumed: bool = False,
    ) -> ExecutionOutcome:
        if plan.requires_confirmation and not confirmation_consumed:
            raise AssertionError("orchestrator bypassed confirmation")
        action_outputs: dict[str, str] = {}
        dom_snapshot: dict[str, str]
        path: str
        if plan.capability_id == "demo_search":
            query = str(contract.slots["query"])
            dom_snapshot = {"query_input": query, "results": f"受控结果：{query}"}
            path = "/sandbox/search"
        elif plan.capability_id == "demo_help":
            dom_snapshot = {"heading": "Voice2Task 帮助中心"}
            path = "/sandbox/help"
        elif plan.capability_id == "demo_product":
            action_outputs = {"product_price": "¥199.00"}
            dom_snapshot = {"product_price": "¥199.00"}
            path = "/sandbox/product"
        elif plan.capability_id == "demo_profile_form":
            dom_snapshot = {"email_input": context.profile.email}
            path = "/sandbox/profile"
        else:
            raise AssertionError("fake executor received a non-executable plan")

        artifact_id = uuid4().hex
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = self.artifact_dir / f"{artifact_id}.png"
        artifact_path.write_bytes(b"public-fixture-png")
        await self.artifact_sink(
            ArtifactRecord(
                id=artifact_id,
                session_id=plan.session_id,
                kind="action_screenshot",
                relative_path=artifact_path.name,
                sha256="fixture-sha256",
                created_at=datetime.now(timezone.utc),
            )
        )
        for action in plan.actions:
            await self.event_sink(
                EventType.ACTION_STARTED,
                {
                    "action_id": action.action_id,
                    "kind": action.kind.value,
                    "capability_id": action.capability_id,
                    "locator_id": action.locator_id,
                },
            )
            await self.event_sink(
                EventType.ACTION_COMPLETED,
                {
                    "action_id": action.action_id,
                    "kind": action.kind.value,
                    "capability_id": action.capability_id,
                    "locator_id": action.locator_id,
                    "screenshot_id": artifact_id,
                    "elapsed_ms": 1,
                },
            )
        return ExecutionOutcome(
            browser_context_created=True,
            action_count=len(plan.actions),
            final_url_path=path,
            evidence=ExecutionEvidence(
                action_outputs=action_outputs,
                dom_snapshot=dom_snapshot,
            ),
            screenshots=[artifact_id],
            elapsed_ms=4,
        )


class CrashingExecutor:
    async def execute(
        self,
        plan: ExecutionPlan,
        *,
        contract: BrowserTaskContractPayload,
        context: SessionContext,
        confirmation_consumed: bool = False,
    ) -> ExecutionOutcome:
        del plan, contract, context, confirmation_consumed
        raise RuntimeError("private /Users/example/model hostname=secret pid=1234")


def _config(tmp_path: Path, *, asr_mode: str = "disabled") -> DemoConfig:
    return DemoConfig(
        database_path=tmp_path / "demo.sqlite3",
        artifact_dir=tmp_path / "artifacts",
        audio_temp_dir=tmp_path / "audio-tmp",
        web_dist=tmp_path / "missing-dist",
        inference_mode="fixture",
        asr_mode=asr_mode,
        execution_mode="sandbox",
        sandbox_origin="http://127.0.0.1:8000",
        heartbeat_seconds=0.05,
    )


@pytest.fixture
def api_client(tmp_path: Path) -> AsyncIterator[TestClient]:
    config = _config(tmp_path)

    def factory(event_sink: EventSink, artifact_sink: ArtifactSink) -> FakeExecutor:
        return FakeExecutor(event_sink, artifact_sink, config.artifact_dir)

    with TestClient(create_app(config=config, executor_factory=factory)) as client:
        yield client


def _create(client: TestClient, text: str, email: str = "demo@example.com") -> dict[str, object]:
    response = client.post(
        "/api/sessions",
        json={"input_kind": "text", "text": text, "profile": {"email": email}},
    )
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["session"]["status"] == "INPUT_RECEIVED"
    assert "confirmation_token" not in payload
    payload["session"] = _wait_for_session(
        client,
        str(payload["session_id"]),
        {
            "PLAN_READY",
            "AWAITING_CONFIRMATION",
            "CLARIFICATION_REQUIRED",
            "BLOCKED",
            "FAILED",
        },
    )
    return payload


def _wait_for_session(
    client: TestClient,
    session_id: str,
    statuses: set[str],
    *,
    timeout: float = 2.0,
) -> dict[str, object]:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200, response.text
        session = response.json()["session"]
        plan = session.get("plan")
        if (
            session["status"] == "PLAN_READY"
            and isinstance(plan, dict)
            and plan.get("requires_confirmation") is True
        ):
            sleep(0.01)
            continue
        if session["status"] in statuses:
            if client.app.state.services.task_registry.is_active(session_id):
                sleep(0.01)
                continue
            return session
        sleep(0.01)
    pytest.fail(f"session {session_id} did not reach one of {sorted(statuses)}")


def _challenge(client: TestClient, session_id: str) -> str:
    response = client.post(f"/api/sessions/{session_id}/confirmation-challenge")
    assert response.status_code == 200, response.text
    return str(response.json()["confirmation_token"])


def test_health_public_config_runtime_schemas_and_openapi_are_public_safe(
    api_client: TestClient,
) -> None:
    health = api_client.get("/api/health")
    config = api_client.get("/api/config/public")
    schemas = api_client.get("/api/schemas/runtime")
    openapi = api_client.get("/openapi.json")

    assert health.json() == {"status": "ok"}
    assert config.json() == {
        "inference_mode": "fixture",
        "asr_mode": "disabled",
        "execution_mode": "sandbox",
        "benchmark_kind": "controlled_fixture_e2e_demo",
    }
    assert "BrowserTaskContractPayload" in schemas.json()["schemas"]
    assert "ExecutionPlan" in schemas.json()["schemas"]
    assert "ExecutionEvidence" in schemas.json()["schemas"]
    assert "ExecutionOutcome" in schemas.json()["schemas"]
    combined = repr([config.json(), schemas.json(), openapi.json()])
    assert "/Users/" not in combined
    assert "confirmation_token_hash" not in combined


def test_session_payload_sanitizes_user_and_provider_controlled_text(api_client: TestClient) -> None:
    created = _create(api_client, "打开帮助中心")
    record = SessionRecord.model_validate(created["session"])
    private_record = record.model_copy(
        update={
            "transcript": "open /Users/example/private token=abcdefgh12345678",
            "error_code": "hostname=secret pid=1234",
        }
    )

    payload = _session_payload(private_record)
    rendered = repr(payload)

    assert "/Users/" not in rendered
    assert "abcdefgh12345678" not in rendered
    assert "hostname=secret" not in rendered
    assert "pid=1234" not in rendered


def test_text_search_create_execute_history_artifact_and_delete(api_client: TestClient) -> None:
    created = _create(api_client, "帮我搜索北京明天的天气")
    session_id = str(created["session_id"])
    session = created["session"]
    assert isinstance(session, dict)
    assert session["status"] == "PLAN_READY"
    assert session["inference_mode"] == "fixture"
    assert "confirmation_token" not in created

    execute = api_client.post(f"/api/sessions/{session_id}/execute")
    assert execute.status_code == 200, execute.text
    completed = execute.json()["session"]
    assert completed["status"] == "COMPLETED"
    assert completed["verification"]["passed"] is True
    artifact_id = completed["execution"]["screenshots"][0]

    events = api_client.get(f"/api/sessions/{session_id}/events", params={"after_seq": 2})
    assert events.status_code == 200
    assert all(event["seq"] > 2 for event in events.json()["events"])
    assert [event["seq"] for event in events.json()["events"]] == sorted(
        event["seq"] for event in events.json()["events"]
    )

    history = api_client.get("/api/sessions")
    assert history.status_code == 200
    assert history.json()["sessions"][0]["id"] == session_id
    artifact = api_client.get(f"/api/sessions/{session_id}/artifacts/{artifact_id}")
    assert artifact.status_code == 200
    assert artifact.content == b"public-fixture-png"
    assert "/Users/" not in repr(completed)

    deleted = api_client.delete(f"/api/sessions/{session_id}")
    assert deleted.status_code == 204
    assert api_client.get(f"/api/sessions/{session_id}").status_code == 404
    assert api_client.get(f"/api/sessions/{session_id}/artifacts/{artifact_id}").status_code == 404


def test_artifact_unlink_failure_keeps_session_retryable(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _create(api_client, "帮我搜索北京明天的天气")
    session_id = str(created["session_id"])
    completed = api_client.post(f"/api/sessions/{session_id}/execute").json()["session"]
    artifact_id = str(completed["execution"]["screenshots"][0])
    artifact_path = api_client.app.state.services.config.artifact_dir / f"{artifact_id}.png"
    original_unlink = Path.unlink

    def fail_target_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path == artifact_path:
            raise OSError("private filesystem failure /Users/example")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_target_unlink)
    failed = api_client.delete(f"/api/sessions/{session_id}")

    assert failed.status_code == 500
    assert failed.json() == {
        "error": {
            "code": "ARTIFACT_DELETE_FAILED",
            "message": "Local session artifacts could not be removed.",
            "retryable": True,
        }
    }
    assert api_client.get(f"/api/sessions/{session_id}").status_code == 200
    assert api_client.get(
        f"/api/sessions/{session_id}/artifacts/{artifact_id}"
    ).status_code == 200

    monkeypatch.setattr(Path, "unlink", original_unlink)
    assert api_client.delete(f"/api/sessions/{session_id}").status_code == 204
    assert api_client.get(f"/api/sessions/{session_id}").status_code == 404


def test_extract_evidence_is_preserved_across_create_execute_get_and_list(
    api_client: TestClient,
) -> None:
    created = _create(api_client, "帮我提取这个页面上的商品价格")
    session_id = str(created["session_id"])
    assert created["session"]["execution"] is None

    executed = api_client.post(f"/api/sessions/{session_id}/execute")
    assert executed.status_code == 200
    expected_evidence = {
        "action_outputs": {"product_price": "¥199.00"},
        "dom_snapshot": {"product_price": "¥199.00"},
    }
    assert executed.json()["session"]["execution"]["evidence"] == expected_evidence

    fetched = api_client.get(f"/api/sessions/{session_id}")
    listed = api_client.get("/api/sessions")
    assert fetched.status_code == 200
    assert listed.status_code == 200
    assert fetched.json()["session"]["execution"]["evidence"] == expected_evidence
    listed_session = next(
        item for item in listed.json()["sessions"] if item["id"] == session_id
    )
    assert listed_session["execution"]["evidence"] == expected_evidence


def test_form_requires_bound_confirmation_then_executes_once(api_client: TestClient) -> None:
    created = _create(api_client, "把邮箱填进表单里，提交前先问我")
    session_id = str(created["session_id"])
    token = _challenge(api_client, session_id)
    assert isinstance(token, str) and token
    assert created["session"]["status"] == "AWAITING_CONFIRMATION"
    assert token not in repr(created["session"])

    before_confirm = api_client.post(f"/api/sessions/{session_id}/execute")
    assert before_confirm.status_code == 409
    assert before_confirm.json()["error"]["code"] == "CONFIRMATION_REQUIRED"

    wrong = api_client.post(
        f"/api/sessions/{session_id}/confirm",
        json={"decision": "approve", "plan_version": 1, "confirmation_token": "wrong-token"},
    )
    assert wrong.status_code == 409
    assert wrong.json()["error"]["code"] == "CONFIRMATION_TOKEN_INVALID"

    approved = api_client.post(
        f"/api/sessions/{session_id}/confirm",
        json={"decision": "approve", "plan_version": 1, "confirmation_token": token},
    )
    assert approved.status_code == 200
    approved_session = approved.json()["session"]
    assert approved_session["status"] == "CONFIRMED"
    assert approved_session["policy"] == {
        "allowed": True,
        "requires_confirmation": True,
        "reason_code": "POLICY_ALLOWED",
        "message": "Plan is restricted to an allowlisted localhost capability.",
    }

    fetched = api_client.get(f"/api/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["session"]["policy"] == approved_session["policy"]
    event_types = [
        event["event_type"]
        for event in api_client.get(f"/api/sessions/{session_id}/events").json()["events"]
    ]
    accepted_index = event_types.index("CONFIRMATION_ACCEPTED")
    assert event_types[accepted_index : accepted_index + 2] == [
        "CONFIRMATION_ACCEPTED",
        "POLICY_ALLOWED",
    ]

    executed = api_client.post(f"/api/sessions/{session_id}/execute")
    assert executed.status_code == 200
    assert (
        executed.json()["session"]["execution"]["evidence"]["dom_snapshot"]["email_input"]
        == "demo@example.com"
    )
    duplicate = api_client.post(f"/api/sessions/{session_id}/execute")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EXECUTION_ALREADY_STARTED"


def test_confirmation_reject_cancels_without_execution(api_client: TestClient) -> None:
    created = _create(api_client, "把邮箱填进表单里，提交前先问我")
    session_id = str(created["session_id"])
    token = _challenge(api_client, session_id)
    rejected = api_client.post(
        f"/api/sessions/{session_id}/confirm",
        json={
            "decision": "reject",
            "plan_version": 1,
            "confirmation_token": token,
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["session"]["status"] == "CANCELLED"
    assert api_client.post(f"/api/sessions/{session_id}/execute").status_code == 409


@pytest.mark.parametrize(
    ("utterance", "expected_status"),
    [("帮我打开那个页面", "CLARIFICATION_REQUIRED"), ("替我完成付款", "BLOCKED")],
)
def test_no_execution_scenarios_end_terminal(
    api_client: TestClient, utterance: str, expected_status: str
) -> None:
    created = _create(api_client, utterance)
    session_id = str(created["session_id"])
    assert created["session"]["status"] == expected_status
    assert created["session"]["execution"] == {
        "browser_context_created": False,
        "action_count": 0,
        "final_url_path": None,
        "evidence": {"action_outputs": {}, "dom_snapshot": {}},
        "screenshots": [],
        "elapsed_ms": 0,
    }
    execute = api_client.post(f"/api/sessions/{session_id}/execute")
    assert execute.status_code == 409


def test_cancel_plan_ready_session(api_client: TestClient) -> None:
    created = _create(api_client, "打开帮助中心")
    session_id = str(created["session_id"])
    cancelled = api_client.post(f"/api/sessions/{session_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["session"]["status"] == "CANCELLED"


def test_audio_disabled_and_fixture_transcript_edit_flow(tmp_path: Path) -> None:
    disabled_config = _config(tmp_path / "disabled", asr_mode="disabled")
    with TestClient(create_app(config=disabled_config, executor_factory=lambda *_: None)) as disabled:
        response = disabled.post(
            "/api/sessions",
            data={"input_kind": "audio"},
            files={"audio": ("recording.wav", b"wave", "audio/wav")},
        )
        assert response.status_code == 202
        session_id = str(response.json()["session_id"])
        failed = _wait_for_session(disabled, session_id, {"FAILED"})
        assert failed["error_code"] == "ASR_PROVIDER_UNAVAILABLE"

    fixture_config = _config(tmp_path / "fixture", asr_mode="fixture")

    def factory(event_sink: EventSink, artifact_sink: ArtifactSink) -> FakeExecutor:
        return FakeExecutor(event_sink, artifact_sink, fixture_config.artifact_dir)

    with TestClient(create_app(config=fixture_config, executor_factory=factory)) as fixture:
        response = fixture.post(
            "/api/sessions",
            data={"input_kind": "audio", "fixture_id": "fixture-search"},
            files={"audio": ("../../recording.wav", b"wave", "audio/wav")},
        )
        assert response.status_code == 202, response.text
        payload = response.json()
        session_id = payload["session_id"]
        assert payload["session"]["status"] == "INPUT_RECEIVED"
        assert payload["transcript_confirmation_required"] is True
        transcript_ready = _wait_for_session(fixture, session_id, {"TRANSCRIPT_READY"})
        assert transcript_ready["status"] == "TRANSCRIPT_READY"

        confirmed = fixture.post(
            f"/api/sessions/{session_id}/transcript",
            json={"transcript": "帮我搜索北京明天的天气", "plan_version": 1},
        )
        assert confirmed.status_code == 202, confirmed.text
        assert confirmed.json()["session"]["status"] == "TRANSCRIPT_READY"
        session = _wait_for_session(fixture, session_id, {"PLAN_READY"})
        assert session["status"] == "PLAN_READY"
        assert session["transcript_original"] == "帮我搜索北京明天的天气"
        assert session["transcript"] == "帮我搜索北京明天的天气"
        assert session["transcript_edited"] is False


def test_uniform_errors_cover_validation_media_type_not_found_and_fixture_provider(
    api_client: TestClient,
) -> None:
    invalid = api_client.post("/api/sessions", json={"input_kind": "text", "unexpected": True})
    unsupported_media = api_client.post(
        "/api/sessions", content=b"plain", headers={"content-type": "text/plain"}
    )
    missing = api_client.get("/api/sessions/not-found")
    unknown_fixture = api_client.post(
        "/api/sessions",
        json={"input_kind": "text", "text": "任意未知输入", "profile": {"email": "demo@example.com"}},
    )

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert unsupported_media.status_code == 415
    assert unsupported_media.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "SESSION_NOT_FOUND"
    assert unknown_fixture.status_code == 202
    unknown_session = _wait_for_session(
        api_client,
        str(unknown_fixture.json()["session_id"]),
        {"FAILED"},
    )
    assert unknown_session["error_code"] == "FIXTURE_INPUT_UNSUPPORTED"
    for response in (invalid, unsupported_media, missing):
        error = response.json()["error"]
        assert set(error) == {"code", "message", "retryable"}
        assert "/Users/" not in repr(error)
        assert "Traceback" not in repr(error)


def test_unexpected_executor_error_marks_session_failed_without_leaking_metadata(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)

    def factory(_event_sink: EventSink, _artifact_sink: ArtifactSink) -> CrashingExecutor:
        return CrashingExecutor()

    with TestClient(create_app(config=config, executor_factory=factory)) as client:
        created = _create(client, "打开帮助中心")
        session_id = str(created["session_id"])
        response = client.post(f"/api/sessions/{session_id}/execute")

        assert response.status_code == 500
        assert response.json()["error"] == {
            "code": "INTERNAL_EXECUTION_ERROR",
            "message": "The controlled browser execution failed safely.",
            "retryable": False,
        }
        session = client.get(f"/api/sessions/{session_id}").json()["session"]
        assert session["status"] == "FAILED"
        assert session["error_code"] == "INTERNAL_EXECUTION_ERROR"
        events = client.get(f"/api/sessions/{session_id}/events").json()["events"]
        serialized = repr(events)
        assert "/Users/" not in serialized
        assert "hostname=" not in serialized
        assert "pid=" not in serialized


def test_executor_preparation_failure_is_retryable_before_atomic_execution_claim(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    attempts = 0

    def factory(event_sink: EventSink, artifact_sink: ArtifactSink) -> FakeExecutor:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("private executor preparation detail")
        return FakeExecutor(event_sink, artifact_sink, config.artifact_dir)

    with TestClient(create_app(config=config, executor_factory=factory)) as client:
        created = _create(client, "打开帮助中心")
        session_id = str(created["session_id"])

        failed_preparation = client.post(f"/api/sessions/{session_id}/execute")
        assert failed_preparation.status_code == 500
        assert failed_preparation.json()["error"] == {
            "code": "EXECUTION_PREPARATION_FAILED",
            "message": "The controlled browser executor could not be prepared safely.",
            "retryable": False,
        }
        retryable = client.get(f"/api/sessions/{session_id}").json()["session"]
        assert retryable["status"] == "PLAN_READY"
        assert retryable["execution_claimed"] is False

        executed = client.post(f"/api/sessions/{session_id}/execute")
        assert executed.status_code == 200
        assert executed.json()["session"]["status"] == "COMPLETED"
        duplicate = client.post(f"/api/sessions/{session_id}/execute")
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "EXECUTION_ALREADY_STARTED"
