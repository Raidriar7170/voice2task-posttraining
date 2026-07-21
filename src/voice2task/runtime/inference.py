from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Protocol, cast

from voice2task.formatting import (
    PredictionInput,
    format_schema_retry_prompt_text,
    format_sft_prediction_prompt,
)
from voice2task.runtime.models import BrowserTaskContractPayload, InferenceResult
from voice2task.schemas import validate_contract_status


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.public_message = message
        self.retryable = retryable


class Voice2TaskInferenceProvider(Protocol):
    async def infer(self, transcript: str) -> InferenceResult: ...


FIXTURE_CONTRACTS: dict[str, dict[str, Any]] = {
    "帮我搜索北京明天的天气": {
        "task_type": "search",
        "route": "search_web",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"query": "北京明天天气"},
        "normalized_command": "搜索北京明天天气",
        "language": "zh-CN",
        "contract_version": "v1",
    },
    "打开帮助中心": {
        "task_type": "navigate",
        "route": "open_url",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"url": "https://help.example.com"},
        "normalized_command": "打开帮助中心",
        "language": "zh-CN",
        "contract_version": "v1",
    },
    "帮我提取这个页面上的商品价格": {
        "task_type": "extract",
        "route": "extract_page",
        "safety": {"allow": True, "reason": "public_readonly"},
        "confirmation_required": False,
        "slots": {"target": "商品价格"},
        "normalized_command": "提取页面商品价格",
        "language": "zh-CN",
        "contract_version": "v1",
    },
    "把邮箱填进表单里，提交前先问我": {
        "task_type": "form_fill",
        "route": "fill_form",
        "safety": {"allow": True, "reason": "requires_confirmation"},
        "confirmation_required": True,
        "slots": {"field": "邮箱"},
        "normalized_command": "填写邮箱并确认",
        "language": "zh-CN",
        "contract_version": "v1",
    },
    "帮我打开那个页面": {
        "task_type": "clarify",
        "route": "clarify",
        "safety": {"allow": True, "reason": "ambiguous_request"},
        "confirmation_required": True,
        "slots": {"ambiguity": "目标不明确，未指定具体网站或页面"},
        "normalized_command": "澄清要打开的页面",
        "language": "zh-CN",
        "contract_version": "v1",
    },
    "替我完成付款": {
        "task_type": "blocked",
        "route": "deny",
        "safety": {"allow": False, "reason": "unsafe_payment"},
        "confirmation_required": True,
        "slots": {"reason": "payment_requires_user_control"},
        "normalized_command": "拒绝代替用户付款",
        "language": "zh-CN",
        "contract_version": "v1",
    },
}


def _strict_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        value = json.loads(stripped)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProviderError(
            "MODEL_OUTPUT_SCHEMA_INVALID", "Model output was not one complete JSON object."
        ) from exc
    if not isinstance(value, dict):
        raise ProviderError(
            "MODEL_OUTPUT_SCHEMA_INVALID", "Model output was not one complete JSON object."
        )
    return value


def parse_strict_contract_json(text: str) -> BrowserTaskContractPayload:
    value = _strict_json_object(text)
    status = validate_contract_status(value)
    if not status["strict_schema_valid"]:
        raise ProviderError("MODEL_OUTPUT_SCHEMA_INVALID", "Model output failed the V1 schema.")
    if not status["semantic_valid"]:
        raise ProviderError("MODEL_OUTPUT_SEMANTIC_INVALID", "Model output failed V1 semantics.")
    return BrowserTaskContractPayload.model_validate(value)


class FixtureVoice2TaskProvider:
    async def infer(self, transcript: str) -> InferenceResult:
        fixture = FIXTURE_CONTRACTS.get(transcript)
        if fixture is None:
            raise ProviderError(
                "FIXTURE_INPUT_UNSUPPORTED",
                "Fixture inference supports only the six displayed demo utterances.",
            )
        contract = BrowserTaskContractPayload.model_validate(fixture)
        return InferenceResult(contract=contract, inference_mode="fixture")


Decoder = Callable[[str], Awaitable[str]]


class LocalPeftVoice2TaskProvider:
    """Fail-closed local PEFT inference with an injectable decoder for hermetic tests."""

    def __init__(
        self,
        *,
        decoder: Decoder | None = None,
        base_model_path: Path | None = None,
        adapter_path: Path | None = None,
        max_new_tokens: int = 256,
    ) -> None:
        self._decoder = decoder
        self._base_model_path = base_model_path
        self._adapter_path = adapter_path
        self._max_new_tokens = max_new_tokens
        self._load_lock = asyncio.Lock()
        self._model: Any | None = None
        self._tokenizer: Any | None = None

    @classmethod
    def from_environment(cls) -> LocalPeftVoice2TaskProvider:
        base_model = os.environ.get("VOICE2TASK_BASE_MODEL_PATH")
        adapter = os.environ.get("VOICE2TASK_ADAPTER_PATH")
        if not base_model or not adapter:
            raise ProviderError(
                "PRIVATE_MODEL_CONFIG_MISSING",
                "Private model mode requires local base-model and adapter configuration.",
            )
        return cls(base_model_path=Path(base_model), adapter_path=Path(adapter))

    async def load(self) -> None:
        if self._decoder is not None or self._model is not None:
            return
        async with self._load_lock:
            if self._model is not None:
                return
            if self._base_model_path is None or self._adapter_path is None:
                raise ProviderError(
                    "PRIVATE_MODEL_CONFIG_MISSING",
                    "Private model mode requires local base-model and adapter configuration.",
                )
            if not self._base_model_path.is_dir() or not self._adapter_path.is_dir():
                raise ProviderError(
                    "PRIVATE_MODEL_NOT_AVAILABLE",
                    "Configured private model files are not available locally.",
                )
            try:
                await asyncio.to_thread(self._load_sync)
            except ProviderError:
                raise
            except Exception as exc:
                raise ProviderError(
                    "PRIVATE_MODEL_LOAD_FAILED", "Private model could not be loaded locally."
                ) from exc

    def _load_sync(self) -> None:
        import torch
        from peft import PeftModel  # type: ignore[import-not-found, unused-ignore]
        from transformers import AutoModelForCausalLM, AutoTokenizer

        assert self._base_model_path is not None
        assert self._adapter_path is not None
        tokenizer = AutoTokenizer.from_pretrained(
            self._base_model_path.as_posix(),
            local_files_only=True,
            trust_remote_code=True,
        )
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model: Any = AutoModelForCausalLM.from_pretrained(
            self._base_model_path.as_posix(),
            local_files_only=True,
            trust_remote_code=True,
            torch_dtype=dtype,
            device_map="auto" if torch.cuda.is_available() else None,
        )
        model = cast(Any, PeftModel).from_pretrained(
            model,
            self._adapter_path.as_posix(),
            local_files_only=True,
        )
        if not torch.cuda.is_available():
            model = model.to("cpu")
        model.eval()
        self._tokenizer = tokenizer
        self._model = model

    async def _decode(self, prompt: str) -> str:
        if self._decoder is not None:
            return await self._decoder(prompt)
        await self.load()
        try:
            return await asyncio.to_thread(self._decode_sync, prompt)
        except Exception as exc:
            raise ProviderError("PRIVATE_MODEL_INFERENCE_FAILED", "Private inference failed.") from exc

    def _decode_sync(self, prompt: str) -> str:
        import torch

        if self._model is None or self._tokenizer is None:
            raise RuntimeError("private model is not loaded")
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        with torch.no_grad():
            generated = self._model.generate(
                **inputs,
                max_new_tokens=self._max_new_tokens,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        new_tokens = generated[0][inputs["input_ids"].shape[-1] :]
        value = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        return value if isinstance(value, str) else str(value)

    async def infer(self, transcript: str) -> InferenceResult:
        await self.load()
        prediction_input = PredictionInput(id="runtime", input_text=transcript)
        prompt = format_sft_prediction_prompt(prediction_input, tokenizer=self._tokenizer)
        decoded = await self._decode(prompt)
        retry_attempted = False
        candidate: dict[str, Any] | str
        status: dict[str, Any]
        try:
            candidate = _strict_json_object(decoded)
        except ProviderError:
            candidate = decoded
            status = {"strict_schema_valid": False, "semantic_valid": False}
        else:
            status = validate_contract_status(candidate)

        if not status["strict_schema_valid"]:
            retry_attempted = True
            from voice2task.training import _schema_retry_prompt

            retry_instruction = _schema_retry_prompt(prediction_input, candidate, status)
            retry_prompt = format_schema_retry_prompt_text(
                retry_instruction,
                tokenizer=self._tokenizer,
            )
            retry_decoded = await self._decode(retry_prompt)
            contract = parse_strict_contract_json(retry_decoded)
        elif not status["semantic_valid"]:
            raise ProviderError(
                "MODEL_OUTPUT_SEMANTIC_INVALID", "Model output failed V1 semantics."
            )
        else:
            if not isinstance(candidate, dict):
                raise ProviderError(
                    "MODEL_OUTPUT_SCHEMA_INVALID", "Model output failed the V1 schema."
                )
            contract = BrowserTaskContractPayload.model_validate(candidate)

        return InferenceResult(
            contract=contract,
            inference_mode="private_model",
            retry_attempted=retry_attempted,
        )
