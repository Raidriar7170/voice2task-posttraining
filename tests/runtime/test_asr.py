from __future__ import annotations

import json

import httpx
import pytest

from voice2task.runtime.asr import (
    ASRProviderError,
    DisabledASRProvider,
    FixtureASRProvider,
    HTTPASRProvider,
    transcribe_uploaded_audio,
    validate_audio_upload,
)
from voice2task.runtime.models import AudioInput


@pytest.mark.asyncio
async def test_disabled_asr_fails_closed() -> None:
    with pytest.raises(ASRProviderError, match="ASR_PROVIDER_UNAVAILABLE") as exc_info:
        await DisabledASRProvider().transcribe(AudioInput(content=b"wave", mime_type="audio/wav"))
    assert exc_info.value.code == "ASR_PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_fixture_asr_accepts_only_declared_fixture_id() -> None:
    provider = FixtureASRProvider()
    result = await provider.transcribe(
        AudioInput(content=b"fixture", mime_type="audio/wav", fixture_id="fixture-search")
    )
    assert result.text == "帮我搜索北京明天的天气"
    assert result.provider == "fixture"

    with pytest.raises(ASRProviderError, match="ASR_FIXTURE_UNSUPPORTED"):
        await provider.transcribe(
            AudioInput(content=b"fixture", mime_type="audio/wav", fixture_id="anything-else")
        )


def test_audio_validation_rejects_mime_size_and_ignores_client_filename() -> None:
    with pytest.raises(ASRProviderError, match="AUDIO_MIME_UNSUPPORTED"):
        validate_audio_upload(b"x", "application/octet-stream", "../../secret.bin")
    with pytest.raises(ASRProviderError, match="AUDIO_TOO_LARGE"):
        validate_audio_upload(b"12345", "audio/wav", "../../recording.wav", max_bytes=4)

    validated = validate_audio_upload(b"wave", "audio/wav", "../../recording.wav")
    assert validated.mime_type == "audio/wav"
    assert validated.content == b"wave"


@pytest.mark.parametrize(
    "endpoint",
    ["http://user:password@127.0.0.1:9001/transcribe", "http://:password@127.0.0.1:9001/transcribe"],
)
def test_http_asr_endpoint_rejects_embedded_credentials(endpoint: str) -> None:
    with pytest.raises(ASRProviderError, match="ASR_ENDPOINT_INVALID"):
        HTTPASRProvider(endpoint=endpoint)


@pytest.mark.asyncio
async def test_http_asr_uses_exact_endpoint_typed_response_and_no_redirect() -> None:
    seen_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "text": "帮我搜索北京明天的天气",
                "language": "zh",
                "segments": [],
                "duration_ms": 1234,
                "provider": "private-local-asr",
            },
        )

    provider = HTTPASRProvider(
        endpoint="http://127.0.0.1:9001/v1/transcribe",
        transport=httpx.MockTransport(handler),
    )
    result = await provider.transcribe(AudioInput(content=b"wave", mime_type="audio/wav"))

    assert seen_urls == ["http://127.0.0.1:9001/v1/transcribe"]
    assert result.text == "帮我搜索北京明天的天气"
    assert result.provider == "private-local-asr"


@pytest.mark.asyncio
async def test_http_asr_rejects_redirect_and_invalid_response() -> None:
    async def redirect(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(307, headers={"location": "https://third-party.example/transcribe"})

    provider = HTTPASRProvider(
        endpoint="http://127.0.0.1:9001/v1/transcribe",
        transport=httpx.MockTransport(redirect),
    )
    with pytest.raises(ASRProviderError, match="ASR_HTTP_ERROR"):
        await provider.transcribe(AudioInput(content=b"wave", mime_type="audio/wav"))

    async def invalid(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps({"text": ""}).encode())

    invalid_provider = HTTPASRProvider(
        endpoint="http://127.0.0.1:9001/v1/transcribe",
        transport=httpx.MockTransport(invalid),
    )
    with pytest.raises(ASRProviderError, match="ASR_RESPONSE_INVALID"):
        await invalid_provider.transcribe(AudioInput(content=b"wave", mime_type="audio/wav"))


@pytest.mark.asyncio
async def test_temporary_audio_is_deleted_after_success_and_failure(tmp_path) -> None:
    class InspectingProvider:
        async def transcribe(self, audio: AudioInput):
            assert audio.content == b"wave"
            assert not list(tmp_path.glob("recording.*"))
            return await FixtureASRProvider().transcribe(
                AudioInput(content=b"fixture", mime_type="audio/wav", fixture_id="fixture-search")
            )

    await transcribe_uploaded_audio(
        InspectingProvider(),
        content=b"wave",
        mime_type="audio/wav",
        client_filename="../../recording.wav",
        temp_dir=tmp_path,
    )
    assert list(tmp_path.iterdir()) == []

    class FailingProvider:
        async def transcribe(self, _audio: AudioInput):
            raise ASRProviderError("ASR_FAILED", "failed")

    with pytest.raises(ASRProviderError, match="ASR_FAILED"):
        await transcribe_uploaded_audio(
            FailingProvider(),
            content=b"wave",
            mime_type="audio/wav",
            client_filename="../../recording.wav",
            temp_dir=tmp_path,
        )
    assert list(tmp_path.iterdir()) == []
