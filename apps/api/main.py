from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import ValidationError as PydanticValidationError
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.api.config import DemoConfig
from apps.api.errors import APIError
from apps.api.event_hub import BoundedEventHub, SlowSubscriberDropped
from apps.api.models import ConfirmationRequest, TextSessionRequest, TranscriptRequest
from apps.api.sandbox import router as sandbox_router
from voice2task.runtime.asr import (
    MAX_AUDIO_BYTES,
    ASRProvider,
    ASRProviderError,
    DisabledASRProvider,
    FixtureASRProvider,
    HTTPASRProvider,
)
from voice2task.runtime.executor import BrowserManager, ExecutorError, SandboxExecutor
from voice2task.runtime.inference import (
    FixtureVoice2TaskProvider,
    LocalPeftVoice2TaskProvider,
    ProviderError,
    Voice2TaskInferenceProvider,
)
from voice2task.runtime.models import (
    BrowserTaskContractPayload,
    ExecutionAction,
    ExecutionEvent,
    ExecutionPlan,
    PolicyResult,
    Profile,
    SessionContext,
    SessionRecord,
    SessionStatus,
    VerificationCheck,
    VerificationResult,
    sanitize_public_payload,
    sanitize_public_text,
)
from voice2task.runtime.orchestrator import (
    ArtifactSink,
    DemoOrchestrator,
    EventSink,
    ExecutorFactory,
)
from voice2task.runtime.storage import (
    ArtifactNotFound,
    SessionConflict,
    SessionNotFound,
    SQLiteSessionStore,
)

TERMINAL_STATUSES = {
    SessionStatus.COMPLETED,
    SessionStatus.BLOCKED,
    SessionStatus.CLARIFICATION_REQUIRED,
    SessionStatus.FAILED,
    SessionStatus.CANCELLED,
}


@dataclass
class DemoServices:
    config: DemoConfig
    store: SQLiteSessionStore
    hub: BoundedEventHub
    orchestrator: DemoOrchestrator
    browser_manager: BrowserManager | None


def _session_payload(session: SessionRecord) -> dict[str, Any]:
    return cast(dict[str, Any], sanitize_public_payload(session.model_dump(mode="json")))


def _error_status(code: str, default: int) -> int:
    if code == "AUDIO_TOO_LARGE":
        return 413
    if code == "AUDIO_MIME_UNSUPPORTED":
        return 415
    if code in {"ASR_PROVIDER_UNAVAILABLE", "ASR_ENDPOINT_MISSING"}:
        return 503
    if code.startswith("ASR_HTTP"):
        return 502
    return default


def _inference_provider(config: DemoConfig) -> Voice2TaskInferenceProvider:
    if config.inference_mode == "fixture":
        return FixtureVoice2TaskProvider()
    return LocalPeftVoice2TaskProvider.from_environment()


def _asr_provider(config: DemoConfig) -> ASRProvider:
    if config.asr_mode == "disabled":
        return DisabledASRProvider()
    if config.asr_mode == "fixture":
        return FixtureASRProvider()
    return HTTPASRProvider.from_environment()


def create_app(
    *,
    config: DemoConfig | None = None,
    executor_factory: ExecutorFactory | None = None,
) -> FastAPI:
    resolved_config = config or DemoConfig.from_environment()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        store = SQLiteSessionStore(resolved_config.database_path)
        await store.initialize()
        await store.recover_interrupted_sessions()
        hub = BoundedEventHub(queue_size=resolved_config.websocket_queue_size)
        inference = _inference_provider(resolved_config)
        if isinstance(inference, LocalPeftVoice2TaskProvider):
            await inference.load()
        asr = _asr_provider(resolved_config)
        browser_manager: BrowserManager | None = None
        if executor_factory is None:
            browser_manager = BrowserManager()
            await browser_manager.start()

            def sandbox_executor_factory(
                event_sink: EventSink, artifact_sink: ArtifactSink
            ) -> SandboxExecutor:
                assert browser_manager is not None
                return SandboxExecutor(
                    browser_manager,
                    sandbox_origin=resolved_config.sandbox_origin,
                    artifact_dir=resolved_config.artifact_dir,
                    event_sink=event_sink,
                    artifact_sink=artifact_sink,
                )
            selected_factory: ExecutorFactory = sandbox_executor_factory
        else:
            selected_factory = executor_factory
        orchestrator = DemoOrchestrator(
            store=store,
            publisher=hub,
            inference_provider=inference,
            asr_provider=asr,
            executor_factory=selected_factory,
            audio_temp_dir=resolved_config.audio_temp_dir,
            inference_mode=resolved_config.inference_mode,
            asr_mode=resolved_config.asr_mode,
            execution_mode=resolved_config.execution_mode,
        )
        app.state.services = DemoServices(
            config=resolved_config,
            store=store,
            hub=hub,
            orchestrator=orchestrator,
            browser_manager=browser_manager,
        )
        try:
            yield
        finally:
            if browser_manager is not None:
                await browser_manager.close()

    app = FastAPI(
        title="Voice2Task Controlled Browser Demo",
        version="1.0.0-demo",
        lifespan=lifespan,
    )
    app.include_router(sandbox_router)

    def services(request: Request) -> DemoServices:
        return cast(DemoServices, request.app.state.services)

    @app.exception_handler(APIError)
    async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.payload())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        error = APIError("VALIDATION_ERROR", "Request validation failed.", 422)
        return JSONResponse(status_code=422, content=error.payload())

    @app.exception_handler(SessionNotFound)
    async def session_not_found_handler(_request: Request, _exc: SessionNotFound) -> JSONResponse:
        error = APIError("SESSION_NOT_FOUND", "Session was not found.", 404)
        return JSONResponse(status_code=404, content=error.payload())

    @app.exception_handler(ArtifactNotFound)
    async def artifact_not_found_handler(_request: Request, _exc: ArtifactNotFound) -> JSONResponse:
        error = APIError("ARTIFACT_NOT_FOUND", "Artifact was not found for this session.", 404)
        return JSONResponse(status_code=404, content=error.payload())

    @app.exception_handler(SessionConflict)
    async def session_conflict_handler(_request: Request, exc: SessionConflict) -> JSONResponse:
        code = sanitize_public_text(str(exc)) or "SESSION_CONFLICT"
        error = APIError(code, code.replace("_", " ").title(), 409)
        return JSONResponse(status_code=409, content=error.payload())

    @app.exception_handler(ProviderError)
    async def provider_error_handler(_request: Request, exc: ProviderError) -> JSONResponse:
        error = APIError(exc.code, exc.public_message, 422, exc.retryable)
        return JSONResponse(status_code=error.status_code, content=error.payload())

    @app.exception_handler(ASRProviderError)
    async def asr_error_handler(_request: Request, exc: ASRProviderError) -> JSONResponse:
        status_code = _error_status(exc.code, 422)
        error = APIError(exc.code, exc.public_message, status_code, exc.retryable)
        return JSONResponse(status_code=status_code, content=error.payload())

    @app.exception_handler(ExecutorError)
    async def executor_error_handler(_request: Request, exc: ExecutorError) -> JSONResponse:
        status_code = 409 if exc.code in {"CONFIRMATION_REQUIRED", "PLAN_EXPIRED"} else 500
        error = APIError(exc.code, exc.public_message, status_code)
        return JSONResponse(status_code=status_code, content=error.payload())

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else f"HTTP_{exc.status_code}"
        message = "Resource was not found." if exc.status_code == 404 else "Request failed."
        error = APIError(code, message, exc.status_code)
        return JSONResponse(status_code=exc.status_code, content=error.payload())

    @app.exception_handler(Exception)
    async def internal_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
        error = APIError("INTERNAL_ERROR", "The demo request failed safely.", 500)
        return JSONResponse(status_code=500, content=error.payload())

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/config/public")
    async def public_config(request: Request) -> dict[str, str]:
        return services(request).config.public_payload()

    @app.get("/api/schemas/runtime")
    async def runtime_schemas() -> dict[str, dict[str, Any]]:
        models = (
            BrowserTaskContractPayload,
            SessionContext,
            ExecutionAction,
            ExecutionPlan,
            PolicyResult,
            VerificationCheck,
            VerificationResult,
            ExecutionEvent,
        )
        return {"schemas": {model.__name__: model.model_json_schema() for model in models}}

    @app.post("/api/sessions", status_code=201)
    async def create_session(request: Request) -> dict[str, Any]:
        service = services(request)
        content_type = request.headers.get("content-type", "").lower()
        if content_type.startswith("application/json"):
            try:
                request_model = TextSessionRequest.model_validate(await request.json())
            except (PydanticValidationError, ValueError) as exc:
                raise APIError("VALIDATION_ERROR", "Request validation failed.", 422) from exc
            session, token = await service.orchestrator.create_text_session(
                text=request_model.text,
                profile=request_model.profile,
            )
            return {
                "session_id": session.id,
                "session": _session_payload(session),
                "confirmation_token": token,
                "transcript_confirmation_required": False,
            }
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            if str(form.get("input_kind", "audio")) != "audio":
                raise APIError("VALIDATION_ERROR", "Audio multipart input_kind must be audio.", 422)
            upload = form.get("audio")
            if not isinstance(upload, UploadFile):
                raise APIError("VALIDATION_ERROR", "Audio multipart request requires an audio file.", 422)
            content = await upload.read(MAX_AUDIO_BYTES + 1)
            await upload.close()
            if len(content) > MAX_AUDIO_BYTES:
                raise APIError("AUDIO_TOO_LARGE", "Audio upload exceeds the 20 MB limit.", 413)
            try:
                profile = Profile(email=str(form.get("profile_email", "demo@example.com")))
            except PydanticValidationError as exc:
                raise APIError("VALIDATION_ERROR", "Profile validation failed.", 422) from exc
            session = await service.orchestrator.create_audio_session(
                content=content,
                mime_type=upload.content_type or "application/octet-stream",
                client_filename=upload.filename,
                profile=profile,
                fixture_id=str(form["fixture_id"]) if form.get("fixture_id") else None,
            )
            return {
                "session_id": session.id,
                "session": _session_payload(session),
                "confirmation_token": None,
                "transcript_confirmation_required": True,
            }
        raise APIError("UNSUPPORTED_MEDIA_TYPE", "Use application/json or multipart/form-data.", 415)

    @app.get("/api/sessions")
    async def list_sessions(request: Request, limit: int = 20) -> dict[str, Any]:
        records = await services(request).store.list_sessions(limit=limit)
        return {"sessions": [_session_payload(record) for record in records]}

    @app.get("/api/sessions/{session_id}")
    async def get_session(session_id: str, request: Request) -> dict[str, Any]:
        record = await services(request).store.get_session(session_id)
        return {"session": _session_payload(record)}

    @app.get("/api/sessions/{session_id}/events")
    async def get_events(session_id: str, request: Request, after_seq: int = 0) -> dict[str, Any]:
        events = await services(request).store.events_after(session_id, max(after_seq, 0))
        return {"events": [event.model_dump(mode="json") for event in events]}

    @app.post("/api/sessions/{session_id}/transcript")
    async def confirm_transcript(
        session_id: str,
        payload: TranscriptRequest,
        request: Request,
    ) -> dict[str, Any]:
        session, token = await services(request).orchestrator.confirm_transcript(
            session_id,
            transcript=payload.transcript,
            plan_version=payload.plan_version,
        )
        return {"session": _session_payload(session), "confirmation_token": token}

    @app.post("/api/sessions/{session_id}/confirm")
    async def confirm_session(
        session_id: str,
        payload: ConfirmationRequest,
        request: Request,
    ) -> dict[str, Any]:
        session = await services(request).orchestrator.confirm(
            session_id,
            decision=payload.decision,
            plan_version=payload.plan_version,
            token=payload.confirmation_token,
        )
        return {"session": _session_payload(session)}

    @app.post("/api/sessions/{session_id}/execute")
    async def execute_session(session_id: str, request: Request) -> dict[str, Any]:
        session = await services(request).orchestrator.execute(session_id)
        return {"session": _session_payload(session)}

    @app.post("/api/sessions/{session_id}/cancel")
    async def cancel_session(session_id: str, request: Request) -> dict[str, Any]:
        session = await services(request).orchestrator.cancel(session_id)
        return {"session": _session_payload(session)}

    @app.get("/api/sessions/{session_id}/artifacts/{artifact_id}")
    async def get_artifact(session_id: str, artifact_id: str, request: Request) -> FileResponse:
        service = services(request)
        artifact = await service.store.get_artifact(session_id, artifact_id)
        candidate = service.config.artifact_dir / artifact.relative_path
        if candidate.parent.resolve() != service.config.artifact_dir.resolve() or not candidate.is_file():
            raise ArtifactNotFound(artifact_id)
        return FileResponse(candidate, media_type="image/png", filename=f"{artifact.id}.png")

    @app.delete("/api/sessions/{session_id}", status_code=204)
    async def delete_session(session_id: str, request: Request) -> Response:
        service = services(request)
        session = await service.store.get_session(session_id)
        if session.status in {SessionStatus.EXECUTING, SessionStatus.VERIFYING}:
            raise SessionConflict("EXECUTION_IN_PROGRESS")
        artifacts = await service.store.list_artifacts(session_id)
        await service.store.delete_session(session_id)
        for artifact in artifacts:
            candidate = service.config.artifact_dir / artifact.relative_path
            if candidate.parent.resolve() == service.config.artifact_dir.resolve():
                candidate.unlink(missing_ok=True)
        return Response(status_code=204)

    @app.websocket("/ws/sessions/{session_id}")
    async def session_websocket(websocket: WebSocket, session_id: str, after_seq: int = 0) -> None:
        service: DemoServices = websocket.app.state.services
        try:
            await service.store.get_session(session_id)
        except SessionNotFound:
            await websocket.accept()
            await websocket.close(code=4404, reason="session not found")
            return
        await websocket.accept()
        subscription = await service.hub.subscribe(session_id)
        last_sent = max(after_seq, 0)
        try:
            replay = await service.store.events_after(session_id, last_sent)
            for replay_event in replay:
                if replay_event.seq <= last_sent:
                    continue
                await websocket.send_json(replay_event.model_dump(mode="json"))
                last_sent = replay_event.seq
            current = await service.store.get_session(session_id)
            if current.status in TERMINAL_STATUSES and last_sent >= current.last_event_seq:
                await websocket.close(code=1000)
                return
            while True:
                try:
                    live_event = await asyncio.wait_for(
                        subscription.receive(),
                        timeout=service.config.heartbeat_seconds,
                    )
                except TimeoutError:
                    await websocket.send_json({"type": "heartbeat", "after_seq": last_sent})
                    continue
                except SlowSubscriberDropped:
                    await websocket.close(code=4408, reason="slow client queue overflow")
                    return
                seq = int(live_event.get("seq", 0))
                if seq <= last_sent:
                    continue
                await websocket.send_json(live_event)
                last_sent = seq
                current = await service.store.get_session(session_id)
                if current.status in TERMINAL_STATUSES and last_sent >= current.last_event_seq:
                    await websocket.close(code=1000)
                    return
        except WebSocketDisconnect:
            return
        finally:
            await service.hub.unsubscribe(subscription)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_web(full_path: str) -> Response:
        if full_path.startswith(("api/", "ws/", "sandbox/")):
            raise HTTPException(status_code=404)
        dist = resolved_config.web_dist
        requested = dist / full_path if full_path else dist / "index.html"
        if requested.is_file() and requested.resolve().is_relative_to(dist.resolve()):
            return FileResponse(requested)
        index = dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404)

    return app


app = create_app()
