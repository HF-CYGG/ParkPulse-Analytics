from __future__ import annotations

from datetime import datetime, time, timedelta

from django.db.models import Avg, Count
from django.utils import timezone

from analytics.models import ForecastEvaluation, ProjectForecast
from analytics.services.metrics import mean_absolute_error, mean_squared_error, r2_score
from projects.models import Project
from records.models import PlayRecord


def build_forecast_rows(*, days: int = 30, horizon: int = 7, model_name: str = "baseline", persist: bool = False) -> dict:
    today = timezone.localdate()
    start_date = today - timedelta(days=max(days - 1, 1))
    projects = list(Project.objects.all().order_by("name"))
    items = []
    for project in projects:
        series = _daily_series(project, start_date, today)
        queue_series = _daily_queue_series(project, start_date, today)
        predicted_visits = _predict_next_values(series, horizon)
        predicted_queue = _predict_next_values(queue_series, horizon)
        forecast = []
        for idx in range(horizon):
            target_date = today + timedelta(days=idx + 1)
            day_factor = _day_factor(target_date)
            visits = max(0.0, predicted_visits[idx] * day_factor)
            queue = max(0.0, predicted_queue[idx] * day_factor)
            score = _score_from_prediction(project, visits, queue)
            alert_level, warning = _warning_for(project, target_date, score, visits, queue)
            target_dt = timezone.make_aware(datetime.combine(target_date, time(hour=10)))
            forecast_item = {
                "date": target_date.isoformat(),
                "label": _date_label(target_date),
                "predicted_score": round(score, 1),
                "predicted_visits": round(visits, 1),
                "predicted_queue": round(queue, 1),
                "alert_level": alert_level,
                "warning": warning,
            }
            forecast.append(forecast_item)
            if persist:
                ProjectForecast.objects.update_or_create(
                    project=project,
                    model_name=model_name,
                    target_time=target_dt,
                    defaults={
                        "predicted_score": forecast_item["predicted_score"],
                        "predicted_visits": forecast_item["predicted_visits"],
                        "predicted_queue": forecast_item["predicted_queue"],
                        "alert_level": alert_level,
                        "warning": warning,
                        "factors": {"day_factor": day_factor, "mode": "baseline"},
                    },
                )
        peak = max(forecast, key=lambda item: item["predicted_score"]) if forecast else {}
        items.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "forecast": forecast,
                "alert": any(item["alert_level"] == ProjectForecast.ALERT_HIGH for item in forecast),
                "warning": peak.get("warning", ""),
                "peak": peak,
            }
        )
    items.sort(key=lambda item: item["peak"].get("predicted_score", 0), reverse=True)
    return {"mode": "baseline", "model": model_name, "generated_at": timezone.now().isoformat(), "items": items}


def evaluate_baseline_forecasts(*, days: int = 30, horizon: int = 7) -> list[dict]:
    today = timezone.localdate()
    start_date = today - timedelta(days=max(days - 1, horizon + 1))
    rows = []
    for project in Project.objects.all().order_by("name"):
        series = _daily_series(project, start_date, today)
        if len(series) <= horizon + 2:
            actual = series[-horizon:] if series else []
            predicted = actual[:]
        else:
            train = series[:-horizon]
            actual = series[-horizon:]
            predicted = _predict_next_values(train, horizon)
        mae = mean_absolute_error(actual, predicted)
        mse = mean_squared_error(actual, predicted)
        r2 = r2_score(actual, predicted)
        ForecastEvaluation.objects.create(
            project=project,
            model_name="baseline",
            train_start=start_date,
            train_end=today,
            horizon_days=horizon,
            mae=mae,
            mse=mse,
            r2=r2,
            sample_size=len(series),
        )
        rows.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "model_name": "baseline",
                "mae": mae,
                "mse": mse,
                "r2": r2,
                "sample_size": len(series),
            }
        )
    return rows


def _daily_series(project: Project, start_date, end_date) -> list[float]:
    rows = (
        PlayRecord.objects.filter(project=project, play_time__date__gte=start_date, play_time__date__lte=end_date)
        .values("play_time__date")
        .annotate(total=Count("id"))
    )
    by_day = {row["play_time__date"]: float(row["total"]) for row in rows}
    return [by_day.get(start_date + timedelta(days=i), 0.0) for i in range((end_date - start_date).days + 1)]


def _daily_queue_series(project: Project, start_date, end_date) -> list[float]:
    rows = (
        PlayRecord.objects.filter(project=project, play_time__date__gte=start_date, play_time__date__lte=end_date)
        .values("play_time__date")
        .annotate(avg_queue=Avg("queue_time"))
    )
    by_day = {row["play_time__date"]: float(row["avg_queue"] or 0) for row in rows}
    return [by_day.get(start_date + timedelta(days=i), float(project.queue_count or 0)) for i in range((end_date - start_date).days + 1)]


def _predict_next_values(series: list[float], horizon: int) -> list[float]:
    if not series:
        return [0.0 for _ in range(horizon)]
    last_window = series[-7:] if len(series) >= 7 else series
    ma = sum(last_window[-3:]) / min(3, len(last_window))
    trend = _linear_next(last_window) - last_window[-1] if len(last_window) >= 2 else 0.0
    values = []
    for step in range(1, horizon + 1):
        weekly = last_window[(step - 1) % len(last_window)]
        values.append(max(0.0, ma * 0.45 + weekly * 0.4 + (last_window[-1] + trend * step) * 0.15))
    return values


def _linear_next(series: list[float]) -> float:
    n = len(series)
    xs = list(range(n))
    ys = [float(v) for v in series]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0:
        return ys[-1]
    slope = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n)) / denom
    return max(0.0, y_mean + slope * n)


def _day_factor(target_date) -> float:
    if target_date.weekday() >= 5:
        return 1.18
    return 1.0


def _score_from_prediction(project: Project, visits: float, queue: float) -> float:
    demand_score = min(100.0, visits / max(project.daily_warn_threshold, 1) * 100)
    queue_score = min(100.0, queue / 30 * 100)
    realtime_score = min(100.0, project.queue_count / max(project.capacity, 1) * 100)
    return max(0.0, min(100.0, demand_score * 0.55 + queue_score * 0.25 + realtime_score * 0.2))


def _warning_for(project: Project, target_date, score: float, visits: float, queue: float) -> tuple[str, str]:
    if score >= 80 or visits >= project.daily_warn_threshold:
        return (
            ProjectForecast.ALERT_HIGH,
            f"{target_date:%m月%d日} 10:00-12:00 {project.name}热度预计达到{score:.0f}分，建议增加运维人员并准备分流。",
        )
    if score >= 65:
        return (
            ProjectForecast.ALERT_WATCH,
            f"{target_date:%m月%d日} {project.name}热度预计达到{score:.0f}分，建议关注排队与设备状态。",
        )
    return ProjectForecast.ALERT_NONE, ""


def _date_label(target_date) -> str:
    if target_date.weekday() >= 5:
        return f"{target_date:%m-%d} 周末"
    return f"{target_date:%m-%d} 工作日"
