from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.config import DemoConfig
from apps.api.main import _session_payload, create_app
from voice2task.runtime.models import (
    ArtifactRecord,
    BrowserTaskContractPayload,
    EventType,
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
        values: dict[str, str]
        path: str
        if plan.capability_id == "demo_search":
            query = str(contract.slots["query"])
            values = {"query_input": query, "results": f"受控结果：{query}"}
            path = "/sandbox/search"
        elif plan.capability_id == "demo_help":
            values = {"heading": "Voice2Task 帮助中心"}
            path = "/sandbox/help"
        elif plan.capability_id == "demo_product":
            values = {"product_price": "¥199.00", "product_price_dom": "¥199.00"}
            path = "/sandbox/product"
        elif plan.capability_id == "demo_profile_form":
            values = {"email_input": context.profile.email}
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
            values=values,
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
    assert response.status_code == 201, response.text
    return response.json()


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
    assert created["confirmation_token"] is None

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


def test_form_requires_bound_confirmation_then_executes_once(api_client: TestClient) -> None:
    created = _create(api_client, "把邮箱填进表单里，提交前先问我")
    session_id = str(created["session_id"])
    token = created["confirmation_token"]
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
    assert approved.json()["session"]["status"] == "CONFIRMED"

    executed = api_client.post(f"/api/sessions/{session_id}/execute")
    assert executed.status_code == 200
    assert executed.json()["session"]["execution"]["values"]["email_input"] == "demo@example.com"
    duplicate = api_client.post(f"/api/sessions/{session_id}/execute")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EXECUTION_ALREADY_STARTED"


def test_confirmation_reject_cancels_without_execution(api_client: TestClient) -> None:
    created = _create(api_client, "把邮箱填进表单里，提交前先问我")
    session_id = str(created["session_id"])
    rejected = api_client.post(
        f"/api/sessions/{session_id}/confirm",
        json={
            "decision": "reject",
            "plan_version": 1,
            "confirmation_token": created["confirmation_token"],
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
        "values": {},
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
        assert response.status_code == 503
        assert response.json()["error"] == {
            "code": "ASR_PROVIDER_UNAVAILABLE",
            "message": "ASR is disabled. Switch to text input or configure a provider.",
            "retryable": False,
        }

    fixture_config = _config(tmp_path / "fixture", asr_mode="fixture")

    def factory(event_sink: EventSink, artifact_sink: ArtifactSink) -> FakeExecutor:
        return FakeExecutor(event_sink, artifact_sink, fixture_config.artifact_dir)

    with TestClient(create_app(config=fixture_config, executor_factory=factory)) as fixture:
        response = fixture.post(
            "/api/sessions",
            data={"input_kind": "audio", "fixture_id": "fixture-search"},
            files={"audio": ("../../recording.wav", b"wave", "audio/wav")},
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        session_id = payload["session_id"]
        assert payload["session"]["status"] == "TRANSCRIPT_READY"
        assert payload["transcript_confirmation_required"] is True

        confirmed = fixture.post(
            f"/api/sessions/{session_id}/transcript",
            json={"transcript": "帮我搜索北京明天的天气", "plan_version": 1},
        )
        assert confirmed.status_code == 200, confirmed.text
        session = confirmed.json()["session"]
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
    assert unknown_fixture.status_code == 422
    assert unknown_fixture.json()["error"]["code"] == "FIXTURE_INPUT_UNSUPPORTED"
    for response in (invalid, unsupported_media, missing, unknown_fixture):
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
