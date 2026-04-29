from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PipelineExecutionError(RuntimeError):
    message: str
    details: tuple[str, ...] = ()

    def __str__(self) -> str:
        if not self.details:
            return self.message
        return f"{self.message} | " + " | ".join(self.details)
