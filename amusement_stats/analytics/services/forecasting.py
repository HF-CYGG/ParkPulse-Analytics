from __future__ import annotations

from django.utils import timezone

from analytics.forecasting.pipeline import evaluate_forecasts, run_forecast_pipeline
from analytics.models import ForecastEvaluation


def build_forecast_rows(*, days: int = 30, horizon: int = 7, model_name: str = "all", persist: bool = False) -> dict:
    return run_forecast_pipeline(model=model_name, days=days, horizon=horizon, persist=persist)


def evaluate_baseline_forecasts(*, days: int = 30, horizon: int = 7) -> list[dict]:
    rows = evaluate_forecasts(days=days, horizon=horizon, model="moving_average")
    if rows:
        return rows
    return [
        {
            "project_id": item.project_id,
            "project_name": item.project.name,
            "model_name": item.model_name,
            "mae": item.mae,
            "mse": item.mse,
            "r2": item.r2,
            "sample_size": item.sample_size,
            "evaluated_at": timezone.localtime(item.evaluated_at).strftime("%Y-%m-%d %H:%M"),
        }
        for item in ForecastEvaluation.objects.select_related("project").order_by("-evaluated_at")[:30]
    ]
