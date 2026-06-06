from __future__ import annotations

from analytics.services.metrics import mean_absolute_error, mean_squared_error, r2_score


class LinearRegressionModel:
    name = "linear_regression"

    def __init__(self, window: int = 14):
        self.window = window
        self.visits: list[float] = []
        self.queues: list[float] = []

    def fit(self, visits: list[float], queues: list[float]) -> None:
        self.visits = [float(value) for value in visits]
        self.queues = [float(value) for value in queues]

    def predict(self, horizon: int) -> list[tuple[float, float]]:
        return [
            (_linear_next(self.visits[-self.window:], step), _linear_next(self.queues[-self.window:], step))
            for step in range(1, horizon + 1)
        ]

    def parameters(self) -> dict:
        return {"window": self.window}

    def evaluate(self, actual: list[float], predicted: list[float]) -> dict:
        return {
            "mae": mean_absolute_error(actual, predicted),
            "mse": mean_squared_error(actual, predicted),
            "r2": r2_score(actual, predicted),
        }


def _linear_next(series: list[float], step: int) -> float:
    if not series:
        return 0.0
    if len(series) == 1:
        return max(0.0, series[0])
    xs = list(range(len(series)))
    ys = [float(value) for value in series]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0:
        return max(0.0, ys[-1])
    slope = sum((xs[idx] - x_mean) * (ys[idx] - y_mean) for idx in range(len(xs))) / denom
    return max(0.0, y_mean + slope * (len(series) - 1 + step))
