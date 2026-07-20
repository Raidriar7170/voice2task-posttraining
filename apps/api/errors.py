from __future__ import annotations

from dataclasses import dataclass

from voice2task.runtime.models import sanitize_public_text


@dataclass
class APIError(RuntimeError):
    code: str
    message: str
    status_code: int
    retryable: bool = False

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, f"{self.code}: {self.message}")

    def payload(self) -> dict[str, dict[str, object]]:
        return {
            "error": {
                "code": self.code,
                "message": sanitize_public_text(self.message),
                "retryable": self.retryable,
            }
        }
