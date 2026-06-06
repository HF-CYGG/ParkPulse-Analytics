from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


class OptionalDependencyUnavailable(RuntimeError):
    pass


@dataclass
class ForecastPoint:
    target_date: date
    predicted_visits: float
    predicted_queue: float
    confidence: str
    factors: dict


class ForecastModel(Protocol):
    name: str

    def fit(self, visits: list[float], queues: list[float]) -> None:
        ...

    def predict(self, horizon: int) -> list[tuple[float, float]]:
        ...

    def evaluate(self, actual: list[float], predicted: list[float]) -> dict:
        ...

    def parameters(self) -> dict:
        ...


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))
