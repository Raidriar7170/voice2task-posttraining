from __future__ import annotations

from voice2task.runtime.models import SessionStatus


class InvalidTransition(RuntimeError):
    """Raised when a session attempts an undeclared state edge."""


ALLOWED_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.CREATED: frozenset(
        {SessionStatus.INPUT_RECEIVED, SessionStatus.CANCELLED, SessionStatus.FAILED}
    ),
    SessionStatus.INPUT_RECEIVED: frozenset(
        {
            SessionStatus.TRANSCRIBING,
            SessionStatus.TRANSCRIPT_READY,
            SessionStatus.CANCELLED,
            SessionStatus.FAILED,
        }
    ),
    SessionStatus.TRANSCRIBING: frozenset(
        {SessionStatus.TRANSCRIPT_READY, SessionStatus.CANCELLED, SessionStatus.FAILED}
    ),
    SessionStatus.TRANSCRIPT_READY: frozenset(
        {SessionStatus.INFERRING, SessionStatus.CANCELLED, SessionStatus.FAILED}
    ),
    SessionStatus.INFERRING: frozenset(
        {
            SessionStatus.CONTRACT_READY,
            SessionStatus.CONTRACT_REJECTED,
            SessionStatus.CANCELLED,
            SessionStatus.FAILED,
        }
    ),
    SessionStatus.CONTRACT_REJECTED: frozenset({SessionStatus.FAILED}),
    SessionStatus.CONTRACT_READY: frozenset(
        {
            SessionStatus.PLAN_READY,
            SessionStatus.BLOCKED,
            SessionStatus.CLARIFICATION_REQUIRED,
            SessionStatus.CANCELLED,
            SessionStatus.FAILED,
        }
    ),
    SessionStatus.PLAN_READY: frozenset(
        {
            SessionStatus.POLICY_BLOCKED,
            SessionStatus.AWAITING_CONFIRMATION,
            SessionStatus.EXECUTING,
            SessionStatus.BLOCKED,
            SessionStatus.CLARIFICATION_REQUIRED,
            SessionStatus.CANCELLED,
            SessionStatus.FAILED,
        }
    ),
    SessionStatus.POLICY_BLOCKED: frozenset({SessionStatus.BLOCKED, SessionStatus.FAILED}),
    SessionStatus.AWAITING_CONFIRMATION: frozenset(
        {SessionStatus.CONFIRMED, SessionStatus.CANCELLED, SessionStatus.BLOCKED, SessionStatus.FAILED}
    ),
    SessionStatus.CONFIRMED: frozenset(
        {SessionStatus.EXECUTING, SessionStatus.CANCELLED, SessionStatus.FAILED}
    ),
    SessionStatus.EXECUTING: frozenset(
        {SessionStatus.VERIFYING, SessionStatus.CANCELLED, SessionStatus.FAILED}
    ),
    SessionStatus.VERIFYING: frozenset(
        {SessionStatus.COMPLETED, SessionStatus.CANCELLED, SessionStatus.FAILED}
    ),
    SessionStatus.COMPLETED: frozenset(),
    SessionStatus.BLOCKED: frozenset(),
    SessionStatus.CLARIFICATION_REQUIRED: frozenset(),
    SessionStatus.FAILED: frozenset(),
    SessionStatus.CANCELLED: frozenset(),
}


def assert_transition(current: SessionStatus, target: SessionStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransition(f"illegal session transition: {current.value} -> {target.value}")
