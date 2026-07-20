from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from apps.api.config import DemoConfig
from apps.api.event_hub import BoundedEventHub
from apps.api.main import create_app
from tests.runtime.test_api import FakeExecutor


def _app(tmp_path: Path):
    config = DemoConfig(
        database_path=tmp_path / "demo.sqlite3",
        artifact_dir=tmp_path / "artifacts",
        audio_temp_dir=tmp_path / "audio-tmp",
        web_dist=tmp_path / "missing-dist",
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
        sandbox_origin="http://127.0.0.1:8000",
        heartbeat_seconds=0.03,
        websocket_queue_size=64,
    )

    def factory(event_sink, artifact_sink):
        return FakeExecutor(event_sink, artifact_sink, config.artifact_dir)

    return create_app(config=config, executor_factory=factory)


def _create(client: TestClient, text: str) -> dict[str, object]:
    response = client.post(
        "/api/sessions",
        json={"input_kind": "text", "text": text, "profile": {"email": "demo@example.com"}},
    )
    assert response.status_code == 201
    return response.json()


def test_websocket_replays_after_seq_then_streams_ordered_live_events(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path)) as client:
        created = _create(client, "帮我搜索北京明天的天气")
        session_id = str(created["session_id"])
        last_before = int(created["session"]["last_event_seq"])
        with client.websocket_connect(f"/ws/sessions/{session_id}?after_seq=2") as websocket:
            replay = [websocket.receive_json() for _ in range(last_before - 2)]
            assert [event["seq"] for event in replay] == list(range(3, last_before + 1))

            executed = client.post(f"/api/sessions/{session_id}/execute")
            assert executed.status_code == 200
            terminal_seq = int(executed.json()["session"]["last_event_seq"])
            live = [websocket.receive_json() for _ in range(terminal_seq - last_before)]
            assert [event["seq"] for event in live] == list(
                range(last_before + 1, terminal_seq + 1)
            )
            assert live[-1]["event_type"] == "SESSION_COMPLETED"
            with pytest.raises(WebSocketDisconnect) as exc_info:
                websocket.receive_json()
            assert exc_info.value.code == 1000


def test_websocket_heartbeat_is_not_persisted(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path)) as client:
        created = _create(client, "打开帮助中心")
        session_id = str(created["session_id"])
        last_seq = int(created["session"]["last_event_seq"])
        with client.websocket_connect(
            f"/ws/sessions/{session_id}?after_seq={last_seq}"
        ) as websocket:
            heartbeat = websocket.receive_json()
            assert heartbeat == {"type": "heartbeat", "after_seq": last_seq}
        events = client.get(f"/api/sessions/{session_id}/events?after_seq={last_seq}")
        assert events.json()["events"] == []


def test_terminal_replay_closes_normally_and_unknown_session_is_rejected(tmp_path: Path) -> None:
    with TestClient(_app(tmp_path)) as client:
        created = _create(client, "替我完成付款")
        session_id = str(created["session_id"])
        terminal_seq = int(created["session"]["last_event_seq"])
        with client.websocket_connect(f"/ws/sessions/{session_id}?after_seq=0") as websocket:
            replay = [websocket.receive_json() for _ in range(terminal_seq)]
            assert replay[-1]["seq"] == terminal_seq
            assert replay[-1]["event_type"] == "POLICY_BLOCKED"
            with pytest.raises(WebSocketDisconnect) as terminal_close:
                websocket.receive_json()
            assert terminal_close.value.code == 1000

        with pytest.raises(WebSocketDisconnect) as unknown:
            with client.websocket_connect("/ws/sessions/not-found") as websocket:
                websocket.receive_json()
        assert unknown.value.code == 4404


@pytest.mark.asyncio
async def test_slow_websocket_subscriber_drops_only_itself() -> None:
    hub = BoundedEventHub(queue_size=2)
    slow = await hub.subscribe("session")
    fast = await hub.subscribe("session")

    await hub.publish("session", {"seq": 1})
    assert await fast.receive() == {"seq": 1}
    await hub.publish("session", {"seq": 2})
    assert await fast.receive() == {"seq": 2}
    await hub.publish("session", {"seq": 3})
    assert await fast.receive() == {"seq": 3}

    assert slow.dropped is True
    assert fast.dropped is False
    assert hub.subscriber_count("session") == 1
