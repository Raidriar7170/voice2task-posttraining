from __future__ import annotations

import asyncio
import time
from concurrent.futures import CancelledError as FutureCancelledError
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.api.config import DemoConfig
from apps.api.main import create_app
from apps.api.task_registry import SessionTaskRegistry
from tests.runtime.test_api import FakeExecutor
from voice2task.runtime.asr import ASRProviderError
from voice2task.runtime.inference import (
    FixtureVoice2TaskProvider,
    LocalPeftVoice2TaskProvider,
    ProviderError,
)
from voice2task.runtime.models import ASRResult, AudioInput, InferenceResult
from voice2task.runtime.storage import SQLiteSessionStore


class DelayedInferenceProvider:
    def __init__(
        self,
        *,
        delay_seconds: float = 0.25,
        error: Exception | None = None,
    ) -> None:
        self.delay_seconds = delay_seconds
        self.error = error

    async def infer(self, transcript: str) -> InferenceResult:
        await asyncio.sleep(self.delay_seconds)
        if self.error is not None:
            raise self.error
        return await FixtureVoice2TaskProvider().infer(transcript)


class DelayedASRProvider:
    def __init__(
        self,
        *,
        delay_seconds: float = 0.25,
        error: ASRProviderError | None = None,
    ) -> None:
        self.delay_seconds = delay_seconds
        self.error = error

    async def transcribe(self, audio: AudioInput) -> ASRResult:
        assert audio.content == b"wave"
        await asyncio.sleep(self.delay_seconds)
        if self.error is not None:
            raise self.error
        return ASRResult(
            text="帮我搜索北京明天的天气",
            language="zh",
            provider="delayed-fixture",
        )


class ThreadBlockingInferenceProvider:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()

    async def infer(self, transcript: str) -> InferenceResult:
        self.started.set()
        await asyncio.to_thread(self.release.wait)
        return await FixtureVoice2TaskProvider().infer(transcript)


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
        heartbeat_seconds=0.03,
    )


def _app(
    tmp_path: Path,
    *,
    inference_provider: DelayedInferenceProvider | None = None,
    asr_provider: DelayedASRProvider | None = None,
    asr_mode: str = "disabled",
    executor_factory: Any = None,
):
    config = _config(tmp_path, asr_mode=asr_mode)

    def default_executor_factory(event_sink, artifact_sink):
        return FakeExecutor(event_sink, artifact_sink, config.artifact_dir)

    return create_app(
        config=config,
        executor_factory=executor_factory or default_executor_factory,
        inference_provider=inference_provider,
        asr_provider=asr_provider,
    )


def _create_text(client: TestClient, text: str) -> dict[str, Any]:
    response = client.post(
        "/api/sessions",
        json={"input_kind": "text", "text": text, "profile": {"email": "demo@example.com"}},
    )
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["session"]["status"] == "INPUT_RECEIVED"
    assert "confirmation_token" not in payload
    return payload


def _wait_for_status(
    client: TestClient,
    session_id: str,
    expected: set[str],
    *,
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200, response.text
        last = response.json()["session"]
        if last["status"] in expected:
            return last
        time.sleep(0.01)
    raise AssertionError(f"session did not reach {expected}; last={last}")


def test_text_create_returns_before_delayed_inference_and_persists_real_events(
    tmp_path: Path,
) -> None:
    provider = DelayedInferenceProvider(delay_seconds=0.25)
    with TestClient(_app(tmp_path, inference_provider=provider)) as client:
        started = time.monotonic()
        created = _create_text(client, "打开帮助中心")
        elapsed = time.monotonic() - started

        assert elapsed < 0.15
        session_id = str(created["session_id"])
        terminal = _wait_for_status(client, session_id, {"PLAN_READY"})
        assert terminal["plan"]["capability_id"] == "demo_help"
        events = client.get(f"/api/sessions/{session_id}/events").json()["events"]
        event_types = [event["event_type"] for event in events]
        assert event_types[:4] == [
            "SESSION_CREATED",
            "INPUT_RECEIVED",
            "TRANSCRIPT_CONFIRMED",
            "INFERENCE_STARTED",
        ]
        assert "PLAN_COMPILED" in event_types


def test_private_provider_is_not_eagerly_loaded_during_app_startup(tmp_path: Path) -> None:
    provider = LocalPeftVoice2TaskProvider()

    with TestClient(_app(tmp_path, inference_provider=provider)) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_cancel_discards_late_result_from_blocking_inference_thread(tmp_path: Path) -> None:
    provider = ThreadBlockingInferenceProvider()
    with TestClient(_app(tmp_path, inference_provider=provider)) as client:
        created = _create_text(client, "打开帮助中心")
        session_id = str(created["session_id"])
        assert provider.started.wait(timeout=1.0)

        cancelled = client.post(f"/api/sessions/{session_id}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["session"]["status"] == "CANCELLED"

        provider.release.set()
        time.sleep(0.05)
        session = client.get(f"/api/sessions/{session_id}").json()["session"]
        events = client.get(f"/api/sessions/{session_id}/events").json()["events"]
        assert session["status"] == "CANCELLED"
        assert "PLAN_COMPILED" not in {event["event_type"] for event in events}


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (ProviderError("PRIVATE_PROVIDER_FAILED", "Provider failed safely."), "PRIVATE_PROVIDER_FAILED"),
        (RuntimeError("private /Users/example/model hostname=secret"), "BACKGROUND_INFERENCE_FAILED"),
    ],
)
def test_background_inference_failure_is_consumed_persisted_and_sanitized(
    tmp_path: Path,
    error: Exception,
    expected_code: str,
) -> None:
    provider = DelayedInferenceProvider(delay_seconds=0.01, error=error)
    with TestClient(_app(tmp_path, inference_provider=provider)) as client:
        created = _create_text(client, "打开帮助中心")
        session_id = str(created["session_id"])
        failed = _wait_for_status(client, session_id, {"FAILED"})
        events = client.get(f"/api/sessions/{session_id}/events").json()["events"]

    assert failed["error_code"] == expected_code
    rendered = repr([failed, events])
    assert "/Users/" not in rendered
    assert "hostname=" not in rendered
    assert "RuntimeError" not in rendered


def test_provider_public_message_is_sanitized_before_rest_event_persistence(
    tmp_path: Path,
) -> None:
    private_message = "leak /Users/private/model hostname=secret pid=1234"
    provider = DelayedInferenceProvider(
        delay_seconds=0.01,
        error=ProviderError("PRIVATE_PROVIDER_FAILED", private_message),
    )
    config = _config(tmp_path)

    with TestClient(_app(tmp_path, inference_provider=provider)) as client:
        created = _create_text(client, "打开帮助中心")
        session_id = str(created["session_id"])
        _wait_for_status(client, session_id, {"FAILED"})
        response = client.get(f"/api/sessions/{session_id}/events")

    assert response.status_code == 200
    assert private_message not in response.text
    assert "/Users/private/model" not in response.text
    assert "hostname=secret" not in response.text
    assert "pid=1234" not in response.text
    database_bytes = config.database_path.read_bytes()
    assert private_message.encode() not in database_bytes
    assert b"/Users/private/model" not in database_bytes


def test_audio_create_returns_after_safe_staging_then_background_cleans_temp_file(
    tmp_path: Path,
) -> None:
    provider = DelayedASRProvider(delay_seconds=0.25)
    config = _config(tmp_path, asr_mode="fixture")
    with TestClient(
        _app(tmp_path, asr_provider=provider, asr_mode="fixture")
    ) as client:
        started = time.monotonic()
        response = client.post(
            "/api/sessions",
            data={"input_kind": "audio"},
            files={"audio": ("../../recording.wav", b"wave", "audio/wav")},
        )
        elapsed = time.monotonic() - started

        assert response.status_code == 202, response.text
        assert elapsed < 0.15
        payload = response.json()
        assert payload["session"]["status"] == "INPUT_RECEIVED"
        assert len(list(config.audio_temp_dir.iterdir())) == 1
        ready = _wait_for_status(client, str(payload["session_id"]), {"TRANSCRIPT_READY"})
        assert ready["transcript"] == "帮我搜索北京明天的天气"
        assert list(config.audio_temp_dir.iterdir()) == []


def test_transcript_confirmation_is_accepted_once_and_schedules_inference(
    tmp_path: Path,
) -> None:
    inference = DelayedInferenceProvider(delay_seconds=0.25)
    asr = DelayedASRProvider(delay_seconds=0.01)
    with TestClient(
        _app(
            tmp_path,
            inference_provider=inference,
            asr_provider=asr,
            asr_mode="fixture",
        )
    ) as client:
        created = client.post(
            "/api/sessions",
            data={"input_kind": "audio"},
            files={"audio": ("recording.wav", b"wave", "audio/wav")},
        ).json()
        session_id = str(created["session_id"])
        _wait_for_status(client, session_id, {"TRANSCRIPT_READY"})

        first = client.post(
            f"/api/sessions/{session_id}/transcript",
            json={"transcript": "打开帮助中心", "plan_version": 1},
        )
        duplicate = client.post(
            f"/api/sessions/{session_id}/transcript",
            json={"transcript": "打开帮助中心", "plan_version": 1},
        )

        assert first.status_code == 202, first.text
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "SESSION_TASK_ACTIVE"
        planned = _wait_for_status(client, session_id, {"PLAN_READY"})
        assert planned["transcript"] == "打开帮助中心"
        assert planned["transcript_edited"] is True


def test_websocket_disconnect_does_not_cancel_background_pipeline(tmp_path: Path) -> None:
    provider = DelayedInferenceProvider(delay_seconds=0.15)
    with TestClient(_app(tmp_path, inference_provider=provider)) as client:
        created = _create_text(client, "打开帮助中心")
        session_id = str(created["session_id"])
        with client.websocket_connect(f"/ws/sessions/{session_id}?after_seq=0") as websocket:
            first = websocket.receive_json()
            assert first["event_type"] == "SESSION_CREATED"

        planned = _wait_for_status(client, session_id, {"PLAN_READY"})
        assert planned["error_code"] is None


def test_blocking_inference_streams_started_then_completed_over_websocket(
    tmp_path: Path,
) -> None:
    provider = ThreadBlockingInferenceProvider()
    with TestClient(_app(tmp_path, inference_provider=provider)) as client:
        created = _create_text(client, "打开帮助中心")
        session_id = str(created["session_id"])
        assert provider.started.wait(timeout=1.0)

        try:
            with client.websocket_connect(
                f"/ws/sessions/{session_id}?after_seq=0"
            ) as websocket:
                replayed = [websocket.receive_json() for _ in range(4)]
                assert [event["event_type"] for event in replayed] == [
                    "SESSION_CREATED",
                    "INPUT_RECEIVED",
                    "TRANSCRIPT_CONFIRMED",
                    "INFERENCE_STARTED",
                ]

                provider.release.set()
                completed = websocket.receive_json()
                assert completed["event_type"] == "INFERENCE_COMPLETED"
        finally:
            provider.release.set()

        planned = _wait_for_status(client, session_id, {"PLAN_READY"})
        assert planned["plan"]["capability_id"] == "demo_help"


def test_cancel_and_delete_coordinate_with_active_session_task(tmp_path: Path) -> None:
    provider = DelayedInferenceProvider(delay_seconds=0.5)
    with TestClient(_app(tmp_path, inference_provider=provider)) as client:
        created = _create_text(client, "打开帮助中心")
        session_id = str(created["session_id"])

        active_delete = client.delete(f"/api/sessions/{session_id}")
        assert active_delete.status_code == 409
        assert active_delete.json()["error"]["code"] == "SESSION_TASK_ACTIVE"

        cancelled = client.post(f"/api/sessions/{session_id}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["session"]["status"] == "CANCELLED"
        time.sleep(0.55)
        still_cancelled = client.get(f"/api/sessions/{session_id}").json()["session"]
        assert still_cancelled["status"] == "CANCELLED"

        deleted = client.delete(f"/api/sessions/{session_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/sessions/{session_id}").status_code == 404


def test_lifespan_shutdown_cancels_task_and_persists_stable_failure(tmp_path: Path) -> None:
    provider = DelayedInferenceProvider(delay_seconds=5.0)
    app = _app(tmp_path, inference_provider=provider)
    with TestClient(app) as client:
        created = _create_text(client, "打开帮助中心")
        session_id = str(created["session_id"])

    async def read_session() -> dict[str, Any]:
        record = await SQLiteSessionStore(_config(tmp_path).database_path).get_session(session_id)
        return record.model_dump(mode="json")

    persisted = asyncio.run(read_session())
    assert persisted["status"] == "FAILED"
    assert persisted["error_code"] == "SERVER_SHUTDOWN_CANCELLED"


def test_lifespan_shutdown_preserves_a_plan_already_at_a_recoverable_boundary(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    reached_plan_ready = Event()
    with TestClient(app) as client:
        services = client.app.state.services
        process_text_session = services.orchestrator.process_text_session

        async def hold_after_plan_ready(session_id: str) -> Any:
            result = await process_text_session(session_id)
            reached_plan_ready.set()
            await asyncio.Event().wait()
            return result

        services.orchestrator.process_text_session = hold_after_plan_ready
        created = _create_text(client, "打开帮助中心")
        session_id = str(created["session_id"])
        assert reached_plan_ready.wait(timeout=1.0)
        assert client.get(f"/api/sessions/{session_id}").json()["session"]["status"] == "PLAN_READY"

    async def read_session() -> dict[str, Any]:
        record = await SQLiteSessionStore(_config(tmp_path).database_path).get_session(session_id)
        return record.model_dump(mode="json")

    persisted = asyncio.run(read_session())
    assert persisted["status"] == "PLAN_READY"
    assert persisted["error_code"] is None


def test_confirmation_challenge_rotates_and_raw_value_stays_out_of_public_surfaces(
    tmp_path: Path,
) -> None:
    with TestClient(_app(tmp_path)) as client:
        created = _create_text(client, "把邮箱填进表单里，提交前先问我")
        session_id = str(created["session_id"])
        _wait_for_status(client, session_id, {"AWAITING_CONFIRMATION"})

        first = client.post(f"/api/sessions/{session_id}/confirmation-challenge")
        second = client.post(f"/api/sessions/{session_id}/confirmation-challenge")
        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert set(first.json()) == {
            "confirmation_token",
            "plan_id",
            "plan_version",
            "expires_at",
        }
        first_token = first.json()["confirmation_token"]
        second_token = second.json()["confirmation_token"]
        assert first_token != second_token

        for response in (
            client.get(f"/api/sessions/{session_id}"),
            client.get("/api/sessions"),
            client.get(f"/api/sessions/{session_id}/events"),
        ):
            assert first_token not in response.text
            assert second_token not in response.text
        database_bytes = _config(tmp_path).database_path.read_bytes()
        assert first_token.encode() not in database_bytes
        assert second_token.encode() not in database_bytes

        old = client.post(
            f"/api/sessions/{session_id}/confirm",
            json={"decision": "approve", "plan_version": 1, "confirmation_token": first_token},
        )
        assert old.status_code == 409
        assert old.json()["error"]["code"] == "CONFIRMATION_TOKEN_INVALID"

        approved = client.post(
            f"/api/sessions/{session_id}/confirm",
            json={"decision": "approve", "plan_version": 1, "confirmation_token": second_token},
        )
        assert approved.status_code == 200
        assert approved.json()["session"]["status"] == "CONFIRMED"
        assert approved.json()["session"]["execution"] is None
        assert client.post(f"/api/sessions/{session_id}/confirmation-challenge").status_code == 409


def test_known_asr_failure_is_persisted_and_temporary_audio_is_removed(tmp_path: Path) -> None:
    provider = DelayedASRProvider(
        delay_seconds=0.01,
        error=ASRProviderError("ASR_FIXTURE_FAILED", "ASR failed safely."),
    )
    config = _config(tmp_path, asr_mode="fixture")
    with TestClient(
        _app(tmp_path, asr_provider=provider, asr_mode="fixture")
    ) as client:
        response = client.post(
            "/api/sessions",
            data={"input_kind": "audio"},
            files={"audio": ("recording.wav", b"wave", "audio/wav")},
        )
        assert response.status_code == 202
        failed = _wait_for_status(client, response.json()["session_id"], {"FAILED"})

    assert failed["error_code"] == "ASR_FIXTURE_FAILED"
    assert list(config.audio_temp_dir.iterdir()) == []


def test_audio_cancellation_removes_staged_temporary_file(tmp_path: Path) -> None:
    provider = DelayedASRProvider(delay_seconds=5.0)
    config = _config(tmp_path, asr_mode="fixture")
    with TestClient(
        _app(tmp_path, asr_provider=provider, asr_mode="fixture")
    ) as client:
        response = client.post(
            "/api/sessions",
            data={"input_kind": "audio"},
            files={"audio": ("recording.wav", b"wave", "audio/wav")},
        )
        assert response.status_code == 202
        assert len(list(config.audio_temp_dir.iterdir())) == 1

        cancelled = client.post(f"/api/sessions/{response.json()['session_id']}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["session"]["status"] == "CANCELLED"
        assert list(config.audio_temp_dir.iterdir()) == []


def test_request_cancellation_before_task_registration_removes_staged_audio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path, asr_mode="fixture")

    async def cancel_before_registration(
        _registry: SessionTaskRegistry,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(SessionTaskRegistry, "start", cancel_before_registration)

    with TestClient(_app(tmp_path, asr_mode="fixture")) as client:
        with pytest.raises((asyncio.CancelledError, FutureCancelledError)):
            client.post(
                "/api/sessions",
                data={"input_kind": "audio"},
                files={"audio": ("recording.wav", b"wave", "audio/wav")},
            )

    assert list(config.audio_temp_dir.glob("*")) == []
