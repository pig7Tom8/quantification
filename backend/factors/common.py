from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FactorResult:
    score: float
    reasons: list[str]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))

