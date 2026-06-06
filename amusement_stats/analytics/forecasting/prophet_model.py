from __future__ import annotations

from datetime import date, timedelta

from .base import OptionalDependencyUnavailable
from analytics.services.metrics import mean_absolute_error, mean_squared_error, r2_score


class ProphetForecastModel:
    name = "prophet"

    def __init__(self):
        try:
            from prophet import Prophet
            import pandas as pd
        except Exception as exc:  # pragma: no cover - depends on optional packages.
            raise OptionalDependencyUnavailable("prophet is not installed") from exc
        self.Prophet = Prophet
        self.pd = pd
        self.visit_model = None
        self.queue_model = None
        self.start_date: date | None = None

    def fit(self, visits: list[float], queues: list[float]) -> None:
        self.start_date = date.today() - timedelta(days=len(visits) - 1)
        visit_df = self._frame(visits)
        queue_df = self._frame(queues)
        self.visit_model = self.Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
        self.queue_model = self.Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
        self.visit_model.fit(visit_df)
        self.queue_model.fit(queue_df)

    def predict(self, horizon: int) -> list[tuple[float, float]]:
        future = self.visit_model.make_future_dataframe(periods=horizon, freq="D").tail(horizon)
        visit_pred = self.visit_model.predict(future)["yhat"].tolist()
        queue_pred = self.queue_model.predict(future)["yhat"].tolist()
        return [(max(0.0, visit_pred[idx]), max(0.0, queue_pred[idx])) for idx in range(horizon)]

    def parameters(self) -> dict:
        return {"weekly_seasonality": True}

    def evaluate(self, actual: list[float], predicted: list[float]) -> dict:
        return {
            "mae": mean_absolute_error(actual, predicted),
            "mse": mean_squared_error(actual, predicted),
            "r2": r2_score(actual, predicted),
        }

    def _frame(self, values: list[float]):
        days = [self.start_date + timedelta(days=idx) for idx in range(len(values))]
        return self.pd.DataFrame({"ds": days, "y": values})
