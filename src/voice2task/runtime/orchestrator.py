from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from voice2task.runtime.asr import (
    ASRProvider,
    ASRProviderError,
    StagedAudioUpload,
    transcribe_staged_audio,
)
from voice2task.runtime.compiler import compile_contract_to_plan
from voice2task.runtime.executor import ExecutorError
from voice2task.runtime.inference import ProviderError, Voice2TaskInferenceProvider
from voice2task.runtime.models import (
    RESTART_INTERRUPTED_STATUSES,
    ArtifactRecord,
    BrowserTaskContractPayload,
    EventType,
    ExecutionOutcome,
    ExecutionPlan,
    Profile,
    SessionContext,
    SessionRecord,
    SessionStatus,
)
from voice2task.runtime.policy import evaluate_policy
from voice2task.runtime.storage import SessionConflict, SQLiteSessionStore
from voice2task.runtime.verifier import verify_execution


class EventPublisher(Protocol):
    async def publish(self, session_id: str, event: dict[str, object]) -> None: ...


class Executor(Protocol):
    async def execute(
        self,
        plan: ExecutionPlan,
        *,
        contract: BrowserTaskContractPayload,
        context: SessionContext,
        confirmation_consumed: bool = False,
    ) -> ExecutionOutcome: ...


EventSink = Callable[[EventType, dict[str, object]], Awaitable[None]]
ArtifactSink = Callable[[ArtifactRecord], Awaitable[None]]
ExecutorFactory = Callable[[EventSink, ArtifactSink], Executor]


class DemoOrchestrator:
    def __init__(
        self,
        *,
        store: SQLiteSessionStore,
        publisher: EventPublisher,
        inference_provider: Voice2TaskInferenceProvider,
        asr_provider: ASRProvider,
        executor_factory: ExecutorFactory,
        audio_temp_dir: Path,
        inference_mode: str,
        asr_mode: str,
        execution_mode: str,
    ) -> None:
        self.store = store
        self.publisher = publisher
        self.inference_provider = inference_provider
        self.asr_provider = asr_provider
        self.executor_factory = executor_factory
        self.audio_temp_dir = audio_temp_dir
        self.inference_mode = inference_mode
        self.asr_mode = asr_mode
        self.execution_mode = execution_mode

    async def _publish_after(self, session_id: str, after_seq: int) -> None:
        for event in await self.store.events_after(session_id, after_seq):
            await self.publisher.publish(session_id, event.model_dump(mode="json"))

    async def _transition(
        self,
        session_id: str,
        target: SessionStatus,
        *,
        event_type: EventType,
        stage: str,
        status: str,
        message: str,
        payload: dict[str, object] | None = None,
        error_code: str | None = None,
        updates: dict[str, object] | None = None,
    ) -> SessionRecord:
        before = await self.store.get_session(session_id)
        result = await self.store.transition(
            session_id,
            target,
            event_type=event_type,
            stage=stage,
            status=status,
            message=message,
            payload=payload,
            error_code=error_code,
            updates=updates,
        )
        await self._publish_after(session_id, before.last_event_seq)
        return result

    async def _append(
        self,
        session_id: str,
        *,
        event_type: EventType,
        stage: str,
        status: str,
        message: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        event = await self.store.append_event(
            session_id,
            event_type=event_type,
            stage=stage,
            status=status,
            message=message,
            payload=payload,
        )
        await self.publisher.publish(session_id, event.model_dump(mode="json"))

    async def _new_session(self, *, input_kind: str, profile: Profile) -> SessionRecord:
        session_id = f"session-{uuid4().hex}"
        context = SessionContext(
            session_id=session_id,
            profile=profile,
            selected_capability=None,
            plan_version=1,
            plan_issued_at=datetime.now(timezone.utc),
        )
        session = await self.store.create_session(
            session_id=session_id,
            input_kind=input_kind,
            context=context,
            inference_mode=self.inference_mode,
            asr_mode=self.asr_mode,
            execution_mode=self.execution_mode,
        )
        await self._publish_after(session_id, 0)
        return session

    async def create_text_session(self, *, text: str, profile: Profile) -> SessionRecord:
        session = await self._new_session(input_kind="text", profile=profile)
        return await self._transition(
            session.id,
            SessionStatus.INPUT_RECEIVED,
            event_type=EventType.INPUT_RECEIVED,
            stage="input",
            status="ok",
            message="Text input received",
            updates={"transcript_original": text, "transcript": text, "transcript_edited": False},
        )

    async def process_text_session(self, session_id: str) -> SessionRecord:
        await self._transition(
            session_id,
            SessionStatus.TRANSCRIPT_READY,
            event_type=EventType.TRANSCRIPT_CONFIRMED,
            stage="transcript",
            status="ok",
            message="Text transcript accepted",
        )
        return await self._process_transcript(session_id)

    async def create_audio_session(
        self,
        *,
        profile: Profile,
    ) -> SessionRecord:
        session = await self._new_session(input_kind="audio", profile=profile)
        return await self._transition(
            session.id,
            SessionStatus.INPUT_RECEIVED,
            event_type=EventType.AUDIO_ACCEPTED,
            stage="input",
            status="ok",
            message="Audio input accepted for configured ASR",
        )

    async def process_audio_session(
        self,
        session_id: str,
        staged: StagedAudioUpload,
    ) -> SessionRecord:
        try:
            await self._transition(
                session_id,
                SessionStatus.TRANSCRIBING,
                event_type=EventType.ASR_STARTED,
                stage="asr",
                status="running",
                message="ASR transcription started",
            )
            try:
                result = await transcribe_staged_audio(
                    self.asr_provider,
                    staged,
                )
            except ASRProviderError as exc:
                await self._transition(
                    session_id,
                    SessionStatus.FAILED,
                    event_type=EventType.ASR_FAILED,
                    stage="asr",
                    status="failed",
                    message=exc.public_message,
                    error_code=exc.code,
                )
                raise
            return await self._transition(
                session_id,
                SessionStatus.TRANSCRIPT_READY,
                event_type=EventType.ASR_COMPLETED,
                stage="asr",
                status="ok",
                message="ASR transcript ready for user confirmation",
                payload={"provider": result.provider, "duration_ms": result.duration_ms},
                updates={
                    "transcript_original": result.text,
                    "transcript": result.text,
                    "transcript_edited": False,
                },
            )
        finally:
            staged.path.unlink(missing_ok=True)

    async def confirm_transcript(
        self,
        session_id: str,
        *,
        transcript: str,
        plan_version: int,
    ) -> SessionRecord:
        session = await self.store.get_session(session_id)
        if session.status is not SessionStatus.TRANSCRIPT_READY or session.input_kind != "audio":
            raise SessionConflict("TRANSCRIPT_NOT_EDITABLE")
        if session.plan_version != plan_version:
            raise SessionConflict("PLAN_VERSION_MISMATCH")
        edited = transcript != session.transcript_original
        await self.store.update_fields(
            session_id,
            transcript=transcript,
            transcript_edited=edited,
        )
        await self._append(
            session_id,
            event_type=EventType.TRANSCRIPT_EDITED if edited else EventType.TRANSCRIPT_CONFIRMED,
            stage="transcript",
            status="ok",
            message="Transcript edited and confirmed" if edited else "Transcript confirmed",
            payload={"edited": edited},
        )
        return await self._process_transcript(session_id)

    async def _process_transcript(self, session_id: str) -> SessionRecord:
        session = await self._transition(
            session_id,
            SessionStatus.INFERRING,
            event_type=EventType.INFERENCE_STARTED,
            stage="inference",
            status="running",
            message=f"Voice2Task inference started in {self.inference_mode} mode",
            payload={"inference_mode": self.inference_mode},
        )
        assert session.transcript is not None
        try:
            inference = await self.inference_provider.infer(session.transcript)
        except ProviderError as exc:
            await self._transition(
                session_id,
                SessionStatus.CONTRACT_REJECTED,
                event_type=EventType.CONTRACT_REJECTED,
                stage="inference",
                status="failed",
                message=exc.public_message,
                error_code=exc.code,
            )
            await self._transition(
                session_id,
                SessionStatus.FAILED,
                event_type=EventType.SESSION_FAILED,
                stage="session",
                status="failed",
                message="Session failed closed after inference rejection",
                error_code=exc.code,
            )
            raise
        contract = inference.contract
        validation = contract.validation_status
        await self._transition(
            session_id,
            SessionStatus.CONTRACT_READY,
            event_type=EventType.INFERENCE_COMPLETED,
            stage="inference",
            status="ok",
            message=f"Contract produced by {inference.inference_mode} inference",
            payload={
                "inference_mode": inference.inference_mode,
                "schema_valid": inference.schema_valid,
                "semantic_valid": inference.semantic_valid,
                "retry_attempted": inference.retry_attempted,
            },
            updates={"contract": contract, "contract_validation": validation},
        )
        await self._append(
            session_id,
            event_type=EventType.CONTRACT_VALIDATED,
            stage="contract",
            status="ok",
            message="BrowserTaskContract V1 schema and semantics validated",
            payload={"schema_valid": True, "semantic_valid": True},
        )
        session = await self.store.get_session(session_id)
        compile_context = session.context.model_copy(
            update={"plan_issued_at": datetime.now(timezone.utc)}
        )
        initial_compile = compile_contract_to_plan(contract, compile_context)
        if initial_compile.plan is not None:
            context = compile_context.model_copy(
                update={"selected_capability": initial_compile.plan.capability_id}
            )
            compile_result = compile_contract_to_plan(contract, context)
        else:
            context = compile_context
            compile_result = initial_compile
        if compile_result.plan is None:
            await self._transition(
                session_id,
                SessionStatus.FAILED,
                event_type=EventType.SESSION_FAILED,
                stage="compiler",
                status="failed",
                message=compile_result.message,
                error_code=compile_result.reason_code,
                updates={"context": context},
            )
            raise ProviderError(
                compile_result.reason_code or "PLAN_COMPILE_FAILED",
                compile_result.message,
            )
        plan = compile_result.plan
        policy = evaluate_policy(plan, now=context.plan_issued_at)
        if compile_result.outcome in {"blocked", "clarification_required"}:
            outcome = ExecutionOutcome(browser_context_created=False, action_count=0)
            verification = verify_execution(plan, contract, context, outcome)
            await self.store.update_fields(
                session_id,
                context=context,
                plan=plan,
                policy=policy,
                execution=outcome,
                verification=verification,
            )
            await self._append(
                session_id,
                event_type=EventType.PLAN_COMPILED,
                stage="compiler",
                status="blocked" if compile_result.outcome == "blocked" else "clarify",
                message=compile_result.message,
                payload={"outcome": compile_result.outcome, "action_count": 0},
            )
            await self._append(
                session_id,
                event_type=EventType.VERIFICATION_COMPLETED,
                stage="verification",
                status="ok",
                message="No-execution postcondition verified",
                payload={"passed": True, "action_count": 0},
            )
            terminal = (
                SessionStatus.BLOCKED
                if compile_result.outcome == "blocked"
                else SessionStatus.CLARIFICATION_REQUIRED
            )
            event_type = (
                EventType.POLICY_BLOCKED
                if terminal is SessionStatus.BLOCKED
                else EventType.VERIFICATION_COMPLETED
            )
            await self._transition(
                session_id,
                terminal,
                event_type=event_type,
                stage="policy" if terminal is SessionStatus.BLOCKED else "clarification",
                status="blocked" if terminal is SessionStatus.BLOCKED else "required",
                message=policy.message,
                payload={"reason_code": policy.reason_code, "browser_context_created": False},
            )
            return await self.store.get_session(session_id)

        await self._transition(
            session_id,
            SessionStatus.PLAN_READY,
            event_type=EventType.PLAN_COMPILED,
            stage="compiler",
            status="ok",
            message="Controlled execution plan compiled",
            payload={
                "plan_id": plan.plan_id,
                "capability_id": plan.capability_id,
                "action_count": len(plan.actions),
                "requires_confirmation": plan.requires_confirmation,
            },
            updates={"context": context, "plan": plan, "policy": policy},
        )
        if plan.requires_confirmation:
            before = await self.store.get_session(session_id)
            await self.store.require_confirmation(
                session_id,
                plan_id=plan.plan_id,
                plan_version=plan.plan_version,
                plan_expires_at=plan.expires_at,
            )
            await self._publish_after(session_id, before.last_event_seq)
            return await self.store.get_session(session_id)
        await self._append(
            session_id,
            event_type=EventType.POLICY_ALLOWED,
            stage="policy",
            status="ok",
            message="Read-only localhost plan allowed; explicit Execute is still required",
            payload={"reason_code": policy.reason_code},
        )
        return await self.store.get_session(session_id)

    async def issue_confirmation_challenge(
        self,
        session_id: str,
    ) -> tuple[str, datetime, ExecutionPlan]:
        session = await self.store.get_session(session_id)
        if session.status is not SessionStatus.AWAITING_CONFIRMATION or session.plan is None:
            raise SessionConflict("CONFIRMATION_NOT_AVAILABLE")
        plan = ExecutionPlan.model_validate(session.plan)
        before = session.last_event_seq
        token, expires_at = await self.store.rotate_confirmation_challenge(
            session_id,
            plan_id=plan.plan_id,
            plan_version=plan.plan_version,
            plan_expires_at=plan.expires_at,
        )
        await self._publish_after(session_id, before)
        return token, expires_at, plan

    async def fail_background_task(
        self,
        session_id: str,
        *,
        stage: str,
        error_code: str,
        message: str,
        transient_only: bool = False,
    ) -> None:
        try:
            session = await self.store.get_session(session_id)
        except Exception:
            return
        if session.status in {
            SessionStatus.COMPLETED,
            SessionStatus.BLOCKED,
            SessionStatus.CLARIFICATION_REQUIRED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        }:
            return
        is_restart_transient = session.status in RESTART_INTERRUPTED_STATUSES or (
            session.status is SessionStatus.TRANSCRIPT_READY and session.input_kind == "text"
        )
        if transient_only and not is_restart_transient:
            return
        await self._transition(
            session_id,
            SessionStatus.FAILED,
            event_type=EventType.SESSION_FAILED,
            stage=stage,
            status="failed",
            message=message,
            error_code=error_code,
        )

    async def confirm(
        self,
        session_id: str,
        *,
        decision: str,
        plan_version: int,
        token: str,
    ) -> SessionRecord:
        session = await self.store.get_session(session_id)
        if session.plan is None:
            raise SessionConflict("CONFIRMATION_NOT_AVAILABLE")
        plan = ExecutionPlan.model_validate(session.plan)
        before = session.last_event_seq
        if decision == "approve":
            effective_policy = evaluate_policy(plan, confirmation_consumed=True)
            if not effective_policy.allowed:
                raise SessionConflict(effective_policy.reason_code)
            result = await self.store.consume_confirmation(
                session_id,
                token=token,
                plan_id=plan.plan_id,
                plan_version=plan_version,
                effective_policy=effective_policy,
            )
        else:
            result = await self.store.reject_confirmation(
                session_id,
                token=token,
                plan_id=plan.plan_id,
                plan_version=plan_version,
            )
        await self._publish_after(session_id, before)
        return result

    async def execute(self, session_id: str) -> SessionRecord:
        session = await self.store.get_session(session_id)
        if session.execution_claimed or session.status in {
            SessionStatus.COMPLETED,
            SessionStatus.EXECUTING,
            SessionStatus.VERIFYING,
        }:
            raise SessionConflict("EXECUTION_ALREADY_STARTED")
        if session.status is SessionStatus.AWAITING_CONFIRMATION:
            raise SessionConflict("CONFIRMATION_REQUIRED")
        if session.status not in {SessionStatus.PLAN_READY, SessionStatus.CONFIRMED}:
            raise SessionConflict("SESSION_NOT_EXECUTABLE")
        if session.plan is None or session.contract is None:
            raise SessionConflict("SESSION_NOT_EXECUTABLE")
        plan = ExecutionPlan.model_validate(session.plan)
        contract = BrowserTaskContractPayload.model_validate(session.contract)
        confirmation_consumed = session.status is SessionStatus.CONFIRMED
        policy = evaluate_policy(plan, confirmation_consumed=confirmation_consumed)
        if not policy.allowed:
            raise SessionConflict(policy.reason_code)
        async def event_sink(event_type: EventType, payload: dict[str, object]) -> None:
            status = "running" if event_type is EventType.ACTION_STARTED else "ok"
            if event_type is EventType.ACTION_FAILED:
                status = "failed"
            await self._append(
                session_id,
                event_type=event_type,
                stage="execution",
                status=status,
                message=event_type.value.replace("_", " ").title(),
                payload=payload,
            )

        async def artifact_sink(artifact: ArtifactRecord) -> None:
            await self.store.add_artifact(artifact)

        try:
            executor = self.executor_factory(event_sink, artifact_sink)
        except Exception as exc:
            raise ExecutorError(
                "EXECUTION_PREPARATION_FAILED",
                "The controlled browser executor could not be prepared safely.",
            ) from exc

        before = session.last_event_seq
        await self.store.claim_execution(session_id)
        await self._publish_after(session_id, before)
        try:
            outcome = await executor.execute(
                plan,
                contract=contract,
                context=session.context,
                confirmation_consumed=confirmation_consumed,
            )
        except ExecutorError as exc:
            await self._transition(
                session_id,
                SessionStatus.FAILED,
                event_type=EventType.SESSION_FAILED,
                stage="execution",
                status="failed",
                message=exc.public_message,
                error_code=exc.code,
            )
            raise
        except Exception as exc:
            error_code = "INTERNAL_EXECUTION_ERROR"
            public_message = "The controlled browser execution failed safely."
            await self._transition(
                session_id,
                SessionStatus.FAILED,
                event_type=EventType.SESSION_FAILED,
                stage="execution",
                status="failed",
                message=public_message,
                error_code=error_code,
            )
            raise ExecutorError(error_code, public_message) from exc
        await self._transition(
            session_id,
            SessionStatus.VERIFYING,
            event_type=EventType.VERIFICATION_STARTED,
            stage="verification",
            status="running",
            message="Deterministic verification started",
            updates={"execution": outcome},
        )
        verification = verify_execution(plan, contract, session.context, outcome)
        target = SessionStatus.COMPLETED if verification.passed else SessionStatus.FAILED
        await self._append(
            session_id,
            event_type=EventType.VERIFICATION_COMPLETED,
            stage="verification",
            status="ok" if verification.passed else "failed",
            message="Deterministic verification passed" if verification.passed else "Deterministic verification failed",
            payload={"passed": verification.passed, "check_count": len(verification.checks)},
        )
        return await self._transition(
            session_id,
            target,
            event_type=EventType.SESSION_COMPLETED if verification.passed else EventType.SESSION_FAILED,
            stage="session",
            status="completed" if verification.passed else "failed",
            message="Controlled demo session completed" if verification.passed else "Controlled demo session failed",
            payload={"verification_passed": verification.passed},
            error_code=verification.failure_code,
            updates={"verification": verification},
        )

    async def cancel(self, session_id: str) -> SessionRecord:
        session = await self.store.get_session(session_id)
        if session.status in {
            SessionStatus.COMPLETED,
            SessionStatus.BLOCKED,
            SessionStatus.CLARIFICATION_REQUIRED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        }:
            raise SessionConflict("SESSION_ALREADY_TERMINAL")
        if session.status in {SessionStatus.EXECUTING, SessionStatus.VERIFYING}:
            raise SessionConflict("EXECUTION_IN_PROGRESS")
        return await self._transition(
            session_id,
            SessionStatus.CANCELLED,
            event_type=EventType.SESSION_CANCELLED,
            stage="session",
            status="cancelled",
            message="Session cancelled; no further actions will run",
            updates={"cancel_requested": True},
        )
