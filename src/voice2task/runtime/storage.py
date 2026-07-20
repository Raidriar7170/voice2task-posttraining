from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from voice2task.runtime.models import (
    RESTART_INTERRUPTED_STATUSES,
    ArtifactRecord,
    EventType,
    ExecutionEvent,
    SessionContext,
    SessionRecord,
    SessionStatus,
    sanitize_public_payload,
    sanitize_public_text,
)
from voice2task.runtime.session import assert_transition


class SessionNotFound(LookupError):
    pass


class SessionConflict(RuntimeError):
    pass


class ArtifactNotFound(LookupError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load(value: str | None) -> Any:
    return None if value is None else json.loads(value)


class SQLiteSessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._write_lock = asyncio.Lock()

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        connection = await aiosqlite.connect(self.path)
        connection.row_factory = aiosqlite.Row
        await connection.execute("PRAGMA foreign_keys = ON")
        await connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        finally:
            await connection.close()

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self._connect() as connection:
            await connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_kind TEXT NOT NULL,
                    context_json TEXT NOT NULL,
                    transcript_original TEXT,
                    transcript TEXT,
                    transcript_edited INTEGER NOT NULL DEFAULT 0,
                    inference_mode TEXT NOT NULL,
                    asr_mode TEXT NOT NULL,
                    execution_mode TEXT NOT NULL,
                    contract_json TEXT,
                    contract_validation_json TEXT,
                    plan_json TEXT,
                    policy_json TEXT,
                    execution_json TEXT,
                    verification_json TEXT,
                    error_code TEXT,
                    plan_version INTEGER NOT NULL DEFAULT 1,
                    confirmation_status TEXT NOT NULL DEFAULT 'not_required',
                    confirmation_token_hash TEXT,
                    confirmation_plan_id TEXT,
                    confirmation_expires_at TEXT,
                    confirmation_consumed_at TEXT,
                    execution_claimed INTEGER NOT NULL DEFAULT 0,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    last_event_seq INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    UNIQUE (session_id, seq)
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                """
            )
            await connection.commit()

    async def create_session(
        self,
        *,
        session_id: str,
        input_kind: str,
        context: SessionContext,
        inference_mode: str,
        asr_mode: str,
        execution_mode: str,
    ) -> SessionRecord:
        now = _now()
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            try:
                await connection.execute(
                    """
                    INSERT INTO sessions (
                        id, created_at, updated_at, status, input_kind, context_json,
                        inference_mode, asr_mode, execution_mode, plan_version, last_event_seq
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        session_id,
                        now.isoformat(),
                        now.isoformat(),
                        SessionStatus.CREATED.value,
                        input_kind,
                        _dump(context),
                        inference_mode,
                        asr_mode,
                        execution_mode,
                        context.plan_version,
                    ),
                )
                await self._insert_event(
                    connection,
                    session_id=session_id,
                    seq=1,
                    event_type=EventType.SESSION_CREATED,
                    stage="session",
                    status="ok",
                    message="Session created",
                    payload={},
                    created_at=now,
                )
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
        return await self.get_session(session_id)

    async def _insert_event(
        self,
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
        await connection.execute(
            """
            INSERT INTO events (
                session_id, seq, event_type, stage, status, message, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                seq,
                event_type.value,
                sanitize_public_text(stage),
                sanitize_public_text(status),
                sanitize_public_text(message),
                _dump(sanitize_public_payload(payload)) or "{}",
                created_at.isoformat(),
            ),
        )

    async def append_event(
        self,
        session_id: str,
        *,
        event_type: EventType,
        stage: str,
        status: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> ExecutionEvent:
        now = _now()
        public_stage = sanitize_public_text(stage)
        public_status = sanitize_public_text(status)
        public_message = sanitize_public_text(message)
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            row = await self._session_row(connection, session_id)
            seq = int(row["last_event_seq"]) + 1
            await connection.execute(
                "UPDATE sessions SET updated_at = ?, last_event_seq = ? WHERE id = ?",
                (now.isoformat(), seq, session_id),
            )
            await self._insert_event(
                connection,
                session_id=session_id,
                seq=seq,
                event_type=event_type,
                stage=public_stage,
                status=public_status,
                message=public_message,
                payload=payload or {},
                created_at=now,
            )
            await connection.commit()
        return ExecutionEvent(
            session_id=session_id,
            seq=seq,
            event_type=event_type,
            stage=public_stage,
            status=public_status,
            message=public_message,
            payload=sanitize_public_payload(payload or {}),
            created_at=now,
        )

    async def transition(
        self,
        session_id: str,
        target: SessionStatus,
        *,
        event_type: EventType,
        stage: str,
        status: str,
        message: str,
        payload: dict[str, Any] | None = None,
        error_code: str | None = None,
        updates: dict[str, Any] | None = None,
    ) -> SessionRecord:
        now = _now()
        public_error_code = sanitize_public_text(error_code) if error_code is not None else None
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            row = await self._session_row(connection, session_id)
            current = SessionStatus(str(row["status"]))
            assert_transition(current, target)
            seq = int(row["last_event_seq"]) + 1
            columns: dict[str, Any] = {
                "status": target.value,
                "updated_at": now.isoformat(),
                "last_event_seq": seq,
                "error_code": public_error_code,
            }
            columns.update(self._encoded_updates(updates or {}))
            assignments = ", ".join(f"{column} = ?" for column in columns)
            await connection.execute(
                f"UPDATE sessions SET {assignments} WHERE id = ?",  # noqa: S608 - columns are allowlisted.
                (*columns.values(), session_id),
            )
            await self._insert_event(
                connection,
                session_id=session_id,
                seq=seq,
                event_type=event_type,
                stage=stage,
                status=status,
                message=message,
                payload=payload or {},
                created_at=now,
            )
            await connection.commit()
        return await self.get_session(session_id)

    def _encoded_updates(self, updates: dict[str, Any]) -> dict[str, Any]:
        json_fields = {
            "context": "context_json",
            "contract": "contract_json",
            "contract_validation": "contract_validation_json",
            "plan": "plan_json",
            "policy": "policy_json",
            "execution": "execution_json",
            "verification": "verification_json",
        }
        scalar_fields = {
            "transcript_original",
            "transcript",
            "transcript_edited",
            "plan_version",
            "confirmation_status",
            "confirmation_token_hash",
            "confirmation_plan_id",
            "confirmation_expires_at",
            "confirmation_consumed_at",
            "execution_claimed",
            "cancel_requested",
        }
        encoded: dict[str, Any] = {}
        for key, value in updates.items():
            if key in json_fields:
                encoded[json_fields[key]] = _dump(value)
            elif key in scalar_fields:
                if isinstance(value, datetime):
                    value = value.isoformat()
                if isinstance(value, bool):
                    value = int(value)
                encoded[key] = value
            else:
                raise ValueError(f"unsupported session update field: {key}")
        return encoded

    async def update_fields(self, session_id: str, **updates: Any) -> SessionRecord:
        encoded = self._encoded_updates(updates)
        if not encoded:
            return await self.get_session(session_id)
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            await self._session_row(connection, session_id)
            encoded["updated_at"] = _now().isoformat()
            assignments = ", ".join(f"{column} = ?" for column in encoded)
            await connection.execute(
                f"UPDATE sessions SET {assignments} WHERE id = ?",  # noqa: S608 - columns are allowlisted.
                (*encoded.values(), session_id),
            )
            await connection.commit()
        return await self.get_session(session_id)

    async def claim_execution(self, session_id: str) -> bool:
        now = _now()
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            row = await self._session_row(connection, session_id)
            current = SessionStatus(str(row["status"]))
            if bool(row["execution_claimed"]) or current not in {
                SessionStatus.PLAN_READY,
                SessionStatus.CONFIRMED,
            }:
                await connection.rollback()
                raise SessionConflict("EXECUTION_ALREADY_STARTED")
            assert_transition(current, SessionStatus.EXECUTING)
            seq = int(row["last_event_seq"]) + 1
            await connection.execute(
                """
                UPDATE sessions
                SET status = ?, execution_claimed = 1, updated_at = ?, last_event_seq = ?
                WHERE id = ?
                """,
                (SessionStatus.EXECUTING.value, now.isoformat(), seq, session_id),
            )
            await self._insert_event(
                connection,
                session_id=session_id,
                seq=seq,
                event_type=EventType.EXECUTION_STARTED,
                stage="execution",
                status="running",
                message="Execution started",
                payload={},
                created_at=now,
            )
            await connection.commit()
        return True

    async def require_confirmation(
        self,
        session_id: str,
        *,
        plan_id: str,
        plan_version: int,
        plan_expires_at: datetime,
        now: datetime | None = None,
    ) -> SessionRecord:
        required_at = now or _now()
        if required_at > plan_expires_at:
            raise SessionConflict("PLAN_EXPIRED")
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            row = await self._session_row(connection, session_id)
            current = SessionStatus(str(row["status"]))
            if current is not SessionStatus.PLAN_READY:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_NOT_AVAILABLE")
            if int(row["plan_version"]) != plan_version:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_BINDING_MISMATCH")
            assert_transition(current, SessionStatus.AWAITING_CONFIRMATION)
            seq = int(row["last_event_seq"]) + 1
            await connection.execute(
                """
                UPDATE sessions
                SET status = ?, updated_at = ?, last_event_seq = ?, confirmation_status = ?,
                    confirmation_token_hash = NULL, confirmation_plan_id = ?,
                    confirmation_expires_at = ?, confirmation_consumed_at = NULL
                WHERE id = ?
                """,
                (
                    SessionStatus.AWAITING_CONFIRMATION.value,
                    required_at.isoformat(),
                    seq,
                    "required",
                    plan_id,
                    plan_expires_at.isoformat(),
                    session_id,
                ),
            )
            await self._insert_event(
                connection,
                session_id=session_id,
                seq=seq,
                event_type=EventType.CONFIRMATION_REQUIRED,
                stage="confirmation",
                status="required",
                message="Explicit confirmation required",
                payload={
                    "plan_id": plan_id,
                    "plan_version": plan_version,
                    "plan_expires_at": plan_expires_at.isoformat(),
                },
                created_at=required_at,
            )
            await connection.commit()
        return await self.get_session(session_id)

    async def rotate_confirmation_challenge(
        self,
        session_id: str,
        *,
        plan_id: str,
        plan_version: int,
        plan_expires_at: datetime,
        now: datetime | None = None,
    ) -> tuple[str, datetime]:
        issued_at = now or _now()
        if issued_at > plan_expires_at:
            raise SessionConflict("CONFIRMATION_EXPIRED")
        expires_at = min(issued_at + timedelta(minutes=5), plan_expires_at)
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            row = await self._session_row(connection, session_id)
            current = SessionStatus(str(row["status"]))
            if row["confirmation_consumed_at"] is not None:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_ALREADY_CONSUMED")
            if current is not SessionStatus.AWAITING_CONFIRMATION:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_NOT_AVAILABLE")
            if row["confirmation_plan_id"] != plan_id or int(row["plan_version"]) != plan_version:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_BINDING_MISMATCH")
            seq = int(row["last_event_seq"]) + 1
            await connection.execute(
                """
                UPDATE sessions
                SET updated_at = ?, last_event_seq = ?, confirmation_status = ?,
                    confirmation_token_hash = ?, confirmation_expires_at = ?
                WHERE id = ?
                """,
                (
                    issued_at.isoformat(),
                    seq,
                    "pending",
                    token_hash,
                    expires_at.isoformat(),
                    session_id,
                ),
            )
            await self._insert_event(
                connection,
                session_id=session_id,
                seq=seq,
                event_type=EventType.CONFIRMATION_REQUIRED,
                stage="confirmation",
                status="pending",
                message="Confirmation challenge issued",
                payload={
                    "plan_id": plan_id,
                    "plan_version": plan_version,
                    "expires_at": expires_at.isoformat(),
                },
                created_at=issued_at,
            )
            await connection.commit()
        return token, expires_at

    async def consume_confirmation(
        self,
        session_id: str,
        *,
        token: str,
        plan_id: str,
        plan_version: int,
        now: datetime | None = None,
    ) -> SessionRecord:
        consumed_at = now or _now()
        supplied_hash = hashlib.sha256(token.encode()).hexdigest()
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            row = await self._session_row(connection, session_id)
            if row["confirmation_consumed_at"] is not None:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_ALREADY_CONSUMED")
            current = SessionStatus(str(row["status"]))
            if current is not SessionStatus.AWAITING_CONFIRMATION:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_NOT_AVAILABLE")
            if row["confirmation_plan_id"] != plan_id or int(row["plan_version"]) != plan_version:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_BINDING_MISMATCH")
            expires_at = datetime.fromisoformat(str(row["confirmation_expires_at"]))
            if consumed_at > expires_at:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_EXPIRED")
            expected_hash = str(row["confirmation_token_hash"] or "")
            if not hmac.compare_digest(expected_hash, supplied_hash):
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_TOKEN_INVALID")
            assert_transition(current, SessionStatus.CONFIRMED)
            seq = int(row["last_event_seq"]) + 1
            await connection.execute(
                """
                UPDATE sessions
                SET status = ?, updated_at = ?, last_event_seq = ?, confirmation_status = ?,
                    confirmation_consumed_at = ?, confirmation_token_hash = NULL
                WHERE id = ?
                """,
                (
                    SessionStatus.CONFIRMED.value,
                    consumed_at.isoformat(),
                    seq,
                    "approved",
                    consumed_at.isoformat(),
                    session_id,
                ),
            )
            await self._insert_event(
                connection,
                session_id=session_id,
                seq=seq,
                event_type=EventType.CONFIRMATION_ACCEPTED,
                stage="confirmation",
                status="ok",
                message="Confirmation accepted",
                payload={"plan_id": plan_id, "plan_version": plan_version},
                created_at=consumed_at,
            )
            await connection.commit()
        return await self.get_session(session_id)

    async def reject_confirmation(
        self,
        session_id: str,
        *,
        token: str,
        plan_id: str,
        plan_version: int,
        now: datetime | None = None,
    ) -> SessionRecord:
        rejected_at = now or _now()
        supplied_hash = hashlib.sha256(token.encode()).hexdigest()
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            row = await self._session_row(connection, session_id)
            current = SessionStatus(str(row["status"]))
            if current is not SessionStatus.AWAITING_CONFIRMATION:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_NOT_AVAILABLE")
            if row["confirmation_plan_id"] != plan_id or int(row["plan_version"]) != plan_version:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_BINDING_MISMATCH")
            expires_at = datetime.fromisoformat(str(row["confirmation_expires_at"]))
            if rejected_at > expires_at:
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_EXPIRED")
            expected_hash = str(row["confirmation_token_hash"] or "")
            if not hmac.compare_digest(expected_hash, supplied_hash):
                await connection.rollback()
                raise SessionConflict("CONFIRMATION_TOKEN_INVALID")
            assert_transition(current, SessionStatus.CANCELLED)
            seq = int(row["last_event_seq"]) + 1
            await connection.execute(
                """
                UPDATE sessions
                SET status = ?, updated_at = ?, last_event_seq = ?, confirmation_status = ?,
                    confirmation_consumed_at = ?, confirmation_token_hash = NULL
                WHERE id = ?
                """,
                (
                    SessionStatus.CANCELLED.value,
                    rejected_at.isoformat(),
                    seq,
                    "rejected",
                    rejected_at.isoformat(),
                    session_id,
                ),
            )
            await self._insert_event(
                connection,
                session_id=session_id,
                seq=seq,
                event_type=EventType.CONFIRMATION_REJECTED,
                stage="confirmation",
                status="cancelled",
                message="Confirmation rejected; no action executed",
                payload={"plan_id": plan_id, "plan_version": plan_version},
                created_at=rejected_at,
            )
            await connection.commit()
        return await self.get_session(session_id)

    async def add_artifact(self, artifact: ArtifactRecord) -> None:
        relative = Path(artifact.relative_path)
        if relative.is_absolute() or relative.name != artifact.relative_path:
            raise ValueError("artifact path must be one relative filename")
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            await self._session_row(connection, artifact.session_id)
            await connection.execute(
                """
                INSERT INTO artifacts (id, session_id, kind, relative_path, sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.id,
                    artifact.session_id,
                    artifact.kind,
                    artifact.relative_path,
                    artifact.sha256,
                    artifact.created_at.isoformat(),
                ),
            )
            await connection.commit()

    async def get_artifact(self, session_id: str, artifact_id: str) -> ArtifactRecord:
        async with self._connect() as connection:
            await self._session_row(connection, session_id)
            cursor = await connection.execute(
                "SELECT * FROM artifacts WHERE session_id = ? AND id = ?",
                (session_id, artifact_id),
            )
            row = await cursor.fetchone()
        if row is None:
            raise ArtifactNotFound(artifact_id)
        return ArtifactRecord(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            kind=str(row["kind"]),
            relative_path=str(row["relative_path"]),
            sha256=str(row["sha256"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )

    async def list_artifacts(self, session_id: str) -> list[ArtifactRecord]:
        async with self._connect() as connection:
            await self._session_row(connection, session_id)
            cursor = await connection.execute(
                "SELECT * FROM artifacts WHERE session_id = ? ORDER BY created_at, id",
                (session_id,),
            )
            rows = await cursor.fetchall()
        return [
            ArtifactRecord(
                id=str(row["id"]),
                session_id=str(row["session_id"]),
                kind=str(row["kind"]),
                relative_path=str(row["relative_path"]),
                sha256=str(row["sha256"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )
            for row in rows
        ]

    async def recover_interrupted_sessions(self) -> int:
        transient = RESTART_INTERRUPTED_STATUSES
        async with self._connect() as connection:
            placeholders = ",".join("?" for _ in transient)
            cursor = await connection.execute(
                f"""SELECT id FROM sessions
                    WHERE status IN ({placeholders})
                       OR (status = ? AND input_kind = 'text')""",  # noqa: S608
                (
                    *(status.value for status in transient),
                    SessionStatus.TRANSCRIPT_READY.value,
                ),
            )
            session_ids = [str(row[0]) for row in await cursor.fetchall()]
        for session_id in session_ids:
            await self.transition(
                session_id,
                SessionStatus.FAILED,
                event_type=EventType.SESSION_FAILED,
                stage="session",
                status="failed",
                message="Session interrupted by server restart",
                error_code="SERVER_RESTART_INTERRUPTED",
            )
        return len(session_ids)

    async def _session_row(
        self, connection: aiosqlite.Connection, session_id: str
    ) -> aiosqlite.Row:
        cursor = await connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if row is None:
            raise SessionNotFound(session_id)
        return row

    async def get_session(self, session_id: str) -> SessionRecord:
        async with self._connect() as connection:
            row = await self._session_row(connection, session_id)
        return self._record_from_row(row)

    async def list_sessions(self, limit: int = 20) -> list[SessionRecord]:
        bounded_limit = min(max(limit, 1), 20)
        async with self._connect() as connection:
            cursor = await connection.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (bounded_limit,)
            )
            rows = await cursor.fetchall()
        return [self._record_from_row(row) for row in rows]

    def _record_from_row(self, row: aiosqlite.Row) -> SessionRecord:
        return SessionRecord(
            id=str(row["id"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            status=SessionStatus(str(row["status"])),
            input_kind=str(row["input_kind"]),
            context=SessionContext.model_validate(_load(row["context_json"])),
            transcript_original=row["transcript_original"],
            transcript=row["transcript"],
            transcript_edited=bool(row["transcript_edited"]),
            inference_mode=str(row["inference_mode"]),
            asr_mode=str(row["asr_mode"]),
            execution_mode=str(row["execution_mode"]),
            contract=_load(row["contract_json"]),
            contract_validation=_load(row["contract_validation_json"]),
            plan=_load(row["plan_json"]),
            policy=_load(row["policy_json"]),
            execution=_load(row["execution_json"]),
            verification=_load(row["verification_json"]),
            error_code=row["error_code"],
            plan_version=int(row["plan_version"]),
            confirmation_status=str(row["confirmation_status"]),
            confirmation_token_hash=row["confirmation_token_hash"],
            confirmation_plan_id=row["confirmation_plan_id"],
            confirmation_expires_at=(
                datetime.fromisoformat(str(row["confirmation_expires_at"]))
                if row["confirmation_expires_at"]
                else None
            ),
            confirmation_consumed_at=(
                datetime.fromisoformat(str(row["confirmation_consumed_at"]))
                if row["confirmation_consumed_at"]
                else None
            ),
            execution_claimed=bool(row["execution_claimed"]),
            cancel_requested=bool(row["cancel_requested"]),
            last_event_seq=int(row["last_event_seq"]),
        )

    async def events_after(self, session_id: str, after_seq: int) -> list[ExecutionEvent]:
        async with self._connect() as connection:
            await self._session_row(connection, session_id)
            cursor = await connection.execute(
                "SELECT * FROM events WHERE session_id = ? AND seq > ? ORDER BY seq",
                (session_id, max(after_seq, 0)),
            )
            rows = await cursor.fetchall()
        return [
            ExecutionEvent(
                session_id=str(row["session_id"]),
                seq=int(row["seq"]),
                event_type=EventType(str(row["event_type"])),
                stage=sanitize_public_text(str(row["stage"])),
                status=sanitize_public_text(str(row["status"])),
                message=sanitize_public_text(str(row["message"])),
                payload=sanitize_public_payload(_load(row["payload_json"])),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )
            for row in rows
        ]

    async def delete_session(self, session_id: str) -> None:
        async with self._write_lock, self._connect() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            await self._session_row(connection, session_id)
            await connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await connection.commit()
