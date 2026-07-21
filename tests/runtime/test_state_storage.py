from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite
import pytest

from voice2task.runtime.models import (
    EventType,
    ExecutionEvidence,
    ExecutionOutcome,
    PolicyResult,
    SessionContext,
    SessionStatus,
)
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


def _allowed_policy() -> PolicyResult:
    return PolicyResult(
        allowed=True,
        requires_confirmation=True,
        reason_code="POLICY_ALLOWED",
        message="Plan is restricted to an allowlisted localhost capability.",
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
async def test_restart_recovery_fails_accepted_input_before_background_task_starts(
    tmp_path,
) -> None:
    store = SQLiteSessionStore(tmp_path / "demo.sqlite3")
    await store.initialize()
    await store.create_session(
        session_id="accepted-before-start",
        input_kind="text",
        context=_context("accepted-before-start"),
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
    )
    await store.transition(
        "accepted-before-start",
        SessionStatus.INPUT_RECEIVED,
        event_type=EventType.INPUT_RECEIVED,
        stage="input",
        status="ok",
        message="accepted",
    )

    assert await store.recover_interrupted_sessions() == 1
    recovered = await store.get_session("accepted-before-start")
    assert recovered.status is SessionStatus.FAILED
    assert recovered.error_code == "SERVER_RESTART_INTERRUPTED"


@pytest.mark.asyncio
async def test_execution_evidence_roundtrips_after_sqlite_store_reopens(tmp_path) -> None:
    database_path = tmp_path / "demo.sqlite3"
    store = SQLiteSessionStore(database_path)
    await store.initialize()
    await store.create_session(
        session_id="session-extract-evidence",
        input_kind="text",
        context=_context("session-extract-evidence"),
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
    )
    outcome = ExecutionOutcome(
        browser_context_created=True,
        action_count=2,
        final_url_path="/sandbox/product",
        evidence=ExecutionEvidence(
            action_outputs={"product_price": "¥199.00"},
            dom_snapshot={"product_price": "¥199.00"},
        ),
    )
    await store.update_fields("session-extract-evidence", execution=outcome)

    reopened = SQLiteSessionStore(database_path)
    session = await reopened.get_session("session-extract-evidence")

    assert session.execution == outcome.model_dump(mode="json")
    assert session.execution["evidence"]["action_outputs"] == {"product_price": "¥199.00"}
    assert session.execution["evidence"]["dom_snapshot"] == {"product_price": "¥199.00"}


@pytest.mark.asyncio
async def test_confirmation_challenge_rotates_hash_and_is_consumed_once(tmp_path) -> None:
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
    plan_expires_at = issued_at + timedelta(minutes=3)
    await store.require_confirmation(
        "session-confirm",
        plan_id="plan-v1",
        plan_version=1,
        plan_expires_at=plan_expires_at,
        now=issued_at,
    )

    first_token, first_expiry = await store.rotate_confirmation_challenge(
        "session-confirm",
        plan_id="plan-v1",
        plan_version=1,
        plan_expires_at=plan_expires_at,
        now=issued_at,
    )
    second_token, second_expiry = await store.rotate_confirmation_challenge(
        "session-confirm",
        plan_id="plan-v1",
        plan_version=1,
        plan_expires_at=plan_expires_at,
        now=issued_at + timedelta(seconds=1),
    )
    pending = await store.get_session("session-confirm")

    assert first_token != second_token
    assert first_expiry == plan_expires_at
    assert second_expiry == plan_expires_at
    assert first_token not in pending.model_dump_json()
    assert second_token not in pending.model_dump_json()
    assert pending.confirmation_token_hash is not None
    assert pending.confirmation_token_hash not in {first_token, second_token}
    assert pending.confirmation_expires_at == plan_expires_at

    with pytest.raises(SessionConflict, match="CONFIRMATION_TOKEN_INVALID"):
        await store.consume_confirmation(
            "session-confirm",
            token=first_token,
            plan_id="plan-v1",
            plan_version=1,
            effective_policy=_allowed_policy(),
            now=issued_at + timedelta(seconds=1),
        )

    await store.consume_confirmation(
        "session-confirm",
        token=second_token,
        plan_id="plan-v1",
        plan_version=1,
        effective_policy=_allowed_policy(),
        now=issued_at + timedelta(seconds=1),
    )
    confirmed = await store.get_session("session-confirm")
    assert confirmed.status is SessionStatus.CONFIRMED
    assert confirmed.confirmation_consumed_at == issued_at + timedelta(seconds=1)
    assert confirmed.confirmation_token_hash is None

    with pytest.raises(SessionConflict, match="CONFIRMATION_ALREADY_CONSUMED"):
        await store.consume_confirmation(
            "session-confirm",
            token=second_token,
            plan_id="plan-v1",
            plan_version=1,
            effective_policy=_allowed_policy(),
            now=issued_at + timedelta(seconds=1),
        )


@pytest.mark.asyncio
async def test_confirmation_and_effective_policy_commit_atomically(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SQLiteSessionStore(tmp_path / "demo.sqlite3")
    await store.initialize()
    await store.create_session(
        session_id="session-confirm-atomic",
        input_kind="text",
        context=_context("session-confirm-atomic"),
        inference_mode="fixture",
        asr_mode="disabled",
        execution_mode="sandbox",
    )
    await _advance_to_plan_ready(store, "session-confirm-atomic")
    await store.update_fields(
        "session-confirm-atomic",
        policy=PolicyResult(
            allowed=False,
            requires_confirmation=True,
            reason_code="CONFIRMATION_REQUIRED",
            message="Explicit confirmation is required before this local write.",
        ),
    )
    issued_at = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    plan_expires_at = issued_at + timedelta(minutes=3)
    await store.require_confirmation(
        "session-confirm-atomic",
        plan_id="plan-v1",
        plan_version=1,
        plan_expires_at=plan_expires_at,
        now=issued_at,
    )
    token, _ = await store.rotate_confirmation_challenge(
        "session-confirm-atomic",
        plan_id="plan-v1",
        plan_version=1,
        plan_expires_at=plan_expires_at,
        now=issued_at,
    )
    before = await store.get_session("session-confirm-atomic")
    before_events = await store.events_after("session-confirm-atomic", 0)
    original_insert = store._insert_event

    async def fail_policy_event(
        connection: aiosqlite.Connection,
        *,
        session_id: str,
        seq: int,
        event_type: EventType,
        stage: str,
        status: str,
        message: str,
        payload: dict[str, Any],
        created_at: datetime,
    ) -> None:
        if event_type is EventType.POLICY_ALLOWED:
            raise RuntimeError("injected policy event failure")
        await original_insert(
            connection,
            session_id=session_id,
            seq=seq,
            event_type=event_type,
            stage=stage,
            status=status,
            message=message,
            payload=payload,
            created_at=created_at,
        )

    monkeypatch.setattr(store, "_insert_event", fail_policy_event)

    with pytest.raises(RuntimeError, match="injected policy event failure"):
        await store.consume_confirmation(
            "session-confirm-atomic",
            token=token,
            plan_id="plan-v1",
            plan_version=1,
            effective_policy=_allowed_policy(),
            now=issued_at + timedelta(seconds=1),
        )

    after = await store.get_session("session-confirm-atomic")
    after_events = await store.events_after("session-confirm-atomic", 0)
    assert after.status is before.status is SessionStatus.AWAITING_CONFIRMATION
    assert after.confirmation_status == before.confirmation_status == "pending"
    assert after.confirmation_token_hash == before.confirmation_token_hash
    assert after.confirmation_consumed_at is None
    assert after.policy == before.policy
    assert after.last_event_seq == before.last_event_seq
    assert after_events == before_events


@pytest.mark.asyncio
async def test_confirmation_challenge_rejects_wrong_binding_expiry_and_clears_on_reject(
    tmp_path,
) -> None:
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
    plan_expires_at = issued_at + timedelta(minutes=5)
    await store.require_confirmation(
        "session-expiry",
        plan_id="plan-v1",
        plan_version=1,
        plan_expires_at=plan_expires_at,
        now=issued_at,
    )

    with pytest.raises(SessionConflict, match="CONFIRMATION_BINDING_MISMATCH"):
        await store.rotate_confirmation_challenge(
            "session-expiry",
            plan_id="other-plan",
            plan_version=1,
            plan_expires_at=plan_expires_at,
            now=issued_at,
        )

    token, _ = await store.rotate_confirmation_challenge(
        "session-expiry",
        plan_id="plan-v1",
        plan_version=1,
        plan_expires_at=plan_expires_at,
        now=issued_at,
    )

    with pytest.raises(SessionConflict, match="CONFIRMATION_BINDING_MISMATCH"):
        await store.consume_confirmation(
            "session-expiry",
            token=token,
            plan_id="other-plan",
            plan_version=1,
            effective_policy=_allowed_policy(),
            now=issued_at,
        )
    with pytest.raises(SessionConflict, match="CONFIRMATION_EXPIRED"):
        await store.consume_confirmation(
            "session-expiry",
            token=token,
            plan_id="plan-v1",
            plan_version=1,
            effective_policy=_allowed_policy(),
            now=issued_at + timedelta(minutes=6),
        )

    rejected = await store.reject_confirmation(
        "session-expiry",
        token=token,
        plan_id="plan-v1",
        plan_version=1,
        now=issued_at + timedelta(minutes=4),
    )
    assert rejected.status is SessionStatus.CANCELLED
    assert rejected.confirmation_token_hash is None
