from __future__ import annotations

from analytics.services.metrics import mean_absolute_error, mean_squared_error, r2_score


class MovingAverageModel:
    name = "moving_average"

    def __init__(self, window: int = 7):
        self.window = window
        self.visits: list[float] = []
        self.queues: list[float] = []

    def fit(self, visits: list[float], queues: list[float]) -> None:
        self.visits = [float(value) for value in visits]
        self.queues = [float(value) for value in queues]

    def predict(self, horizon: int) -> list[tuple[float, float]]:
        return [
            (_window_average(self.visits, self.window), _window_average(self.queues, self.window))
            for _ in range(horizon)
        ]

    def parameters(self) -> dict:
        return {"window": self.window}

    def evaluate(self, actual: list[float], predicted: list[float]) -> dict:
        return {
            "mae": mean_absolute_error(actual, predicted),
            "mse": mean_squared_error(actual, predicted),
            "r2": r2_score(actual, predicted),
        }


def _window_average(values: list[float], window: int) -> float:
    if not values:
        return 0.0
    sample = values[-window:]
    return sum(sample) / len(sample)
