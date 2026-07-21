from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from voice2task.runtime.models import Profile


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TextSessionRequest(APIModel):
    input_kind: Literal["text"]
    text: str = Field(min_length=1, max_length=500)
    profile: Profile = Field(default_factory=Profile)


class TranscriptRequest(APIModel):
    transcript: str = Field(min_length=1, max_length=500)
    plan_version: int = Field(ge=1)


class ConfirmationRequest(APIModel):
    decision: Literal["approve", "reject"]
    plan_version: int = Field(ge=1)
    confirmation_token: str = Field(min_length=1, max_length=256)
