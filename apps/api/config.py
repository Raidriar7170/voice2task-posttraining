from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DemoConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    database_path: Path = Path("var/demo/demo.sqlite3")
    artifact_dir: Path = Path("var/demo/artifacts")
    audio_temp_dir: Path = Path("var/demo/audio-tmp")
    web_dist: Path = Path("apps/web/dist")
    inference_mode: Literal["fixture", "private_model"] = "fixture"
    asr_mode: Literal["disabled", "fixture", "http"] = "disabled"
    execution_mode: Literal["sandbox"] = "sandbox"
    sandbox_origin: str = "http://127.0.0.1:8000"
    heartbeat_seconds: float = Field(default=15.0, gt=0, le=60)
    websocket_queue_size: int = Field(default=64, ge=2, le=1024)

    @classmethod
    def from_environment(cls) -> DemoConfig:
        return cls.model_validate(
            {
                "database_path": Path(
                    os.environ.get("VOICE2TASK_DEMO_DB", "var/demo/demo.sqlite3")
                ),
                "artifact_dir": Path(
                    os.environ.get("VOICE2TASK_DEMO_ARTIFACTS", "var/demo/artifacts")
                ),
                "audio_temp_dir": Path(
                    os.environ.get("VOICE2TASK_DEMO_AUDIO_TMP", "var/demo/audio-tmp")
                ),
                "web_dist": Path(os.environ.get("VOICE2TASK_WEB_DIST", "apps/web/dist")),
                "inference_mode": os.environ.get("VOICE2TASK_INFERENCE_MODE", "fixture"),
                "asr_mode": os.environ.get("VOICE2TASK_ASR_MODE", "disabled"),
                "execution_mode": os.environ.get("VOICE2TASK_EXECUTION_MODE", "sandbox"),
                "sandbox_origin": os.environ.get(
                    "VOICE2TASK_SANDBOX_ORIGIN", "http://127.0.0.1:8000"
                ),
            }
        )

    def public_payload(self) -> dict[str, str]:
        return {
            "inference_mode": self.inference_mode,
            "asr_mode": self.asr_mode,
            "execution_mode": self.execution_mode,
            "benchmark_kind": "controlled_fixture_e2e_demo",
        }
