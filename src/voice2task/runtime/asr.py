from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from pydantic import ValidationError

from voice2task.runtime.models import ASRResult, AudioInput

MAX_AUDIO_BYTES = 20 * 1024 * 1024
ALLOWED_AUDIO_MIME_TYPES = frozenset({"audio/wav", "audio/x-wav", "audio/webm", "audio/mpeg"})
MIME_SUFFIXES = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/webm": ".webm",
    "audio/mpeg": ".mp3",
}


@dataclass(frozen=True)
class StagedAudioUpload:
    path: Path
    mime_type: str
    fixture_id: str | None = None


class ASRProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.public_message = message
        self.retryable = retryable


class ASRProvider(Protocol):
    async def transcribe(self, audio: AudioInput) -> ASRResult: ...


class DisabledASRProvider:
    async def transcribe(self, audio: AudioInput) -> ASRResult:
        del audio
        raise ASRProviderError(
            "ASR_PROVIDER_UNAVAILABLE",
            "ASR is disabled. Switch to text input or configure a provider.",
        )


FIXTURE_TRANSCRIPTS = {
    "fixture-search": "帮我搜索北京明天的天气",
    "fixture-navigate": "打开帮助中心",
    "fixture-extract": "帮我提取这个页面上的商品价格",
    "fixture-form": "把邮箱填进表单里，提交前先问我",
    "fixture-clarify": "帮我打开那个页面",
    "fixture-blocked": "替我完成付款",
}


class FixtureASRProvider:
    async def transcribe(self, audio: AudioInput) -> ASRResult:
        transcript = FIXTURE_TRANSCRIPTS.get(audio.fixture_id or "")
        if transcript is None:
            raise ASRProviderError(
                "ASR_FIXTURE_UNSUPPORTED",
                "Fixture ASR accepts only declared demo fixture IDs.",
            )
        return ASRResult(
            text=transcript,
            language="zh",
            segments=[],
            duration_ms=0,
            provider="fixture",
        )


def validate_audio_upload(
    content: bytes,
    mime_type: str,
    client_filename: str | None,
    *,
    max_bytes: int = MAX_AUDIO_BYTES,
) -> AudioInput:
    del client_filename
    normalized_mime = mime_type.split(";", 1)[0].strip().lower()
    if normalized_mime not in ALLOWED_AUDIO_MIME_TYPES:
        raise ASRProviderError("AUDIO_MIME_UNSUPPORTED", "Audio MIME type is not supported.")
    if not content:
        raise ASRProviderError("AUDIO_EMPTY", "Audio upload is empty.")
    if len(content) > max_bytes:
        raise ASRProviderError("AUDIO_TOO_LARGE", "Audio upload exceeds the 20 MB limit.")
    return AudioInput(content=content, mime_type=normalized_mime)


class HTTPASRProvider:
    def __init__(
        self,
        *,
        endpoint: str,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ASRProviderError("ASR_ENDPOINT_INVALID", "Configured ASR endpoint is invalid.")
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @classmethod
    def from_environment(cls) -> HTTPASRProvider:
        endpoint = os.environ.get("VOICE2TASK_ASR_ENDPOINT")
        if not endpoint:
            raise ASRProviderError(
                "ASR_ENDPOINT_MISSING", "HTTP ASR mode requires one explicitly configured endpoint."
            )
        return cls(endpoint=endpoint)

    async def transcribe(self, audio: AudioInput) -> ASRResult:
        suffix = MIME_SUFFIXES[audio.mime_type]
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    self.endpoint,
                    files={"audio": (f"audio{suffix}", audio.content, audio.mime_type)},
                )
        except httpx.HTTPError as exc:
            raise ASRProviderError("ASR_HTTP_ERROR", "Configured ASR service request failed.", retryable=True) from exc
        if response.is_redirect or response.status_code < 200 or response.status_code >= 300:
            raise ASRProviderError(
                "ASR_HTTP_ERROR", "Configured ASR service returned an unsuccessful response.", retryable=True
            )
        try:
            payload: Any = response.json()
            result = ASRResult.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise ASRProviderError("ASR_RESPONSE_INVALID", "Configured ASR response was invalid.") from exc
        return result


async def transcribe_uploaded_audio(
    provider: ASRProvider,
    *,
    content: bytes,
    mime_type: str,
    client_filename: str | None,
    temp_dir: Path,
    fixture_id: str | None = None,
) -> ASRResult:
    staged = stage_uploaded_audio(
        content=content,
        mime_type=mime_type,
        client_filename=client_filename,
        temp_dir=temp_dir,
        fixture_id=fixture_id,
    )
    return await transcribe_staged_audio(provider, staged)


def stage_uploaded_audio(
    *,
    content: bytes,
    mime_type: str,
    client_filename: str | None,
    temp_dir: Path,
    fixture_id: str | None = None,
) -> StagedAudioUpload:
    audio = validate_audio_upload(content, mime_type, client_filename)
    temp_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = temp_dir / f"{uuid4().hex}{MIME_SUFFIXES[audio.mime_type]}"
    temporary_path.write_bytes(audio.content)
    return StagedAudioUpload(
        path=temporary_path,
        mime_type=audio.mime_type,
        fixture_id=fixture_id,
    )


async def transcribe_staged_audio(
    provider: ASRProvider,
    staged: StagedAudioUpload,
) -> ASRResult:
    try:
        safe_audio = AudioInput(
            content=staged.path.read_bytes(),
            mime_type=staged.mime_type,
            fixture_id=staged.fixture_id,
        )
        return await provider.transcribe(safe_audio)
    finally:
        staged.path.unlink(missing_ok=True)
