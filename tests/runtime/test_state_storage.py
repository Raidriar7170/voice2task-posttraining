from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from voice2task.runtime.models import EventType, SessionContext, SessionStatus
from voice2task.runtime.session import InvalidTransition, assert_transition
from voice2task.runtime.storage import SessionConflict, SQLiteSessionStore


def _context(session_id: str) -> SessionContext:
    return SessionContext(
        session_id=session_id,
        profile={"email": "demo@example.com"},
        selected_capability="demo_profile_form",
        plan_version=1,
        plan_issued_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )


def test_state_machine_accepts_declared_edge_and_rejects_illegal_edge() -> None:
    assert_transition(SessionStatus.CREATED, SessionStatus.INPUT_RECEIVED)

    with pytest.raises(InvalidTransition, match="CREATED.*EXECUTING"):
        assert_transition(SessionStatus.CREATED, SessionStatus.EXECUTING)


@pytest.mark.asyncio
async def test_storage_appends_monotonic_events_under_concurrency(tmp_path) -> None:
    store = SQLiteSessionStore(tmp_path / "demo.sqlite3")
    await store.initialize()
    await store.create_session(
        session_id="session-events",
        input_kind="text",
        context=_context("session-events"),
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
    )

    await asyncio.gather(
        *[
            store.append_event(
                "session-events",
                event_type=EventType.INPUT_RECEIVED,
                stage="input",
                status="ok",
                message=f"event-{index}",
                payload={"index": index},
            )
            for index in range(5)
        ]
    )

    events = await store.events_after("session-events", 0)
    assert [event.seq for event in events] == list(range(1, 7))
    assert len({event.seq for event in events}) == 6


async def _advance_to_plan_ready(store: SQLiteSessionStore, session_id: str) -> None:
    transitions = [
        (SessionStatus.INPUT_RECEIVED, EventType.INPUT_RECEIVED),
        (SessionStatus.TRANSCRIPT_READY, EventType.INPUT_RECEIVED),
        (SessionStatus.INFERRING, EventType.INFERENCE_STARTED),
        (SessionStatus.CONTRACT_READY, EventType.CONTRACT_VALIDATED),
        (SessionStatus.PLAN_READY, EventType.PLAN_COMPILED),
    ]
    for target, event_type in transitions:
        await store.transition(
            session_id,
            target,
            event_type=event_type,
            stage="test",
            status="ok",
            message=target.value,
        )


@pytest.mark.asyncio
async def test_execution_claim_is_atomic_and_duplicate_safe(tmp_path) -> None:
    store = SQLiteSessionStore(tmp_path / "demo.sqlite3")
    await store.initialize()
    await store.create_session(
        session_id="session-claim",
        input_kind="text",
        context=_context("session-claim"),
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
    )
    await _advance_to_plan_ready(store, "session-claim")

    first, second = await asyncio.gather(
        store.claim_execution("session-claim"),
        store.claim_execution("session-claim"),
        return_exceptions=True,
    )

    results = [first, second]
    assert sum(result is True for result in results) == 1
    assert sum(isinstance(result, SessionConflict) for result in results) == 1


@pytest.mark.asyncio
async def test_restart_recovery_fails_transient_sessions_without_replay(tmp_path) -> None:
    store = SQLiteSessionStore(tmp_path / "demo.sqlite3")
    await store.initialize()
    await store.create_session(
        session_id="session-restart",
        input_kind="text",
        context=_context("session-restart"),
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
    )
    await store.transition(
        "session-restart",
        SessionStatus.INPUT_RECEIVED,
        event_type=EventType.INPUT_RECEIVED,
        stage="input",
        status="ok",
        message="received",
    )
    await store.transition(
        "session-restart",
        SessionStatus.TRANSCRIPT_READY,
        event_type=EventType.INPUT_RECEIVED,
        stage="input",
        status="ok",
        message="transcript ready",
    )
    await store.transition(
        "session-restart",
        SessionStatus.INFERRING,
        event_type=EventType.INFERENCE_STARTED,
        stage="inference",
        status="running",
        message="started",
    )

    recovered = await store.recover_interrupted_sessions()
    session = await store.get_session("session-restart")

    assert recovered == 1
    assert session.status is SessionStatus.FAILED
    assert session.error_code == "SERVER_RESTART_INTERRUPTED"
    assert session.execution_claimed is False


@pytest.mark.asyncio
async def test_confirmation_is_hashed_bound_expiring_and_consumed_once(tmp_path) -> None:
    store = SQLiteSessionStore(tmp_path / "demo.sqlite3")
    await store.initialize()
    await store.create_session(
        session_id="session-confirm",
        input_kind="text",
        context=_context("session-confirm"),
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
    )
    await _advance_to_plan_ready(store, "session-confirm")
    issued_at = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)

    token = await store.issue_confirmation(
        "session-confirm", plan_id="plan-v1", plan_version=1, now=issued_at
    )
    pending = await store.get_session("session-confirm")

    assert token not in pending.model_dump_json()
    assert pending.confirmation_token_hash is not None
    assert pending.confirmation_token_hash != token
    assert pending.confirmation_expires_at == issued_at + timedelta(minutes=5)

    await store.consume_confirmation(
        "session-confirm",
        token=token,
        plan_id="plan-v1",
        plan_version=1,
        now=issued_at,
    )
    confirmed = await store.get_session("session-confirm")
    assert confirmed.status is SessionStatus.CONFIRMED
    assert confirmed.confirmation_consumed_at == issued_at

    with pytest.raises(SessionConflict, match="CONFIRMATION_ALREADY_CONSUMED"):
        await store.consume_confirmation(
            "session-confirm",
            token=token,
            plan_id="plan-v1",
            plan_version=1,
            now=issued_at,
        )


@pytest.mark.asyncio
async def test_confirmation_rejects_wrong_binding_and_expiry(tmp_path) -> None:
    store = SQLiteSessionStore(tmp_path / "demo.sqlite3")
    await store.initialize()
    await store.create_session(
        session_id="session-expiry",
        input_kind="text",
        context=_context("session-expiry"),
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
    )
    await _advance_to_plan_ready(store, "session-expiry")
    issued_at = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    token = await store.issue_confirmation(
        "session-expiry", plan_id="plan-v1", plan_version=1, now=issued_at
    )

    with pytest.raises(SessionConflict, match="CONFIRMATION_BINDING_MISMATCH"):
        await store.consume_confirmation(
            "session-expiry",
            token=token,
            plan_id="other-plan",
            plan_version=1,
            now=issued_at,
        )
    with pytest.raises(SessionConflict, match="CONFIRMATION_EXPIRED"):
        await store.consume_confirmation(
            "session-expiry",
            token=token,
            plan_id="plan-v1",
            plan_version=1,
            now=issued_at + timedelta(minutes=6),
        )
