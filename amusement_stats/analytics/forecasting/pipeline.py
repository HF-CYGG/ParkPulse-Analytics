from __future__ import annotations

from datetime import datetime, time, timedelta

from django.db.models import Avg, Count
from django.utils import timezone

from analytics.forecasting.base import OptionalDependencyUnavailable, clamp
from analytics.forecasting.linear_regression import LinearRegressionModel
from analytics.forecasting.moving_average import MovingAverageModel
from analytics.forecasting.prophet_model import ProphetForecastModel
from analytics.forecasting.lstm_model import LSTMForecastModel
from analytics.models import ForecastEvaluation, HolidayCalendar, ProjectForecast, PromotionEvent
from analytics.services.metrics import mean_absolute_error, mean_squared_error, r2_score
from projects.models import Project
from records.models import PlayRecord


def run_forecast_pipeline(*, model: str = "all", days: int = 90, horizon: int = 7, persist: bool = True) -> dict:
    today = timezone.localdate()
    start_date = today - timedelta(days=max(days - 1, horizon + 1))
    items = []
    modes = []
    for project in Project.objects.all().order_by("name"):
        visits = _daily_visits(project, start_date, today)
        queues = _daily_queues(project, start_date, today)
        selected = _select_model(model, len(visits))
        selected.fit(visits, queues)
        predictions = selected.predict(horizon)
        modes.append(selected.name)
        forecast = []
        avg_queue = sum(queues) / len(queues) if queues else 0.0
        for idx, (visits_value, queue_value) in enumerate(predictions):
            target_date = today + timedelta(days=idx + 1)
            day_factor, external_reason = _external_factor(target_date)
            adjusted_visits = max(0.0, visits_value * day_factor)
            adjusted_queue = max(0.0, queue_value * day_factor)
            score = _score_from_prediction(project, adjusted_visits, adjusted_queue)
            alert_level, warning = _warning_for(project, target_date, score, adjusted_visits, adjusted_queue, avg_queue, external_reason)
            target_dt = timezone.make_aware(datetime.combine(target_date, time(hour=10)))
            factors = {
                "model": selected.name,
                "confidence": _confidence_for(len(visits), selected.name),
                "day_factor": round(day_factor, 2),
                "external_reason": external_reason,
                "avg_queue": round(avg_queue, 1),
                "parameters": selected.parameters(),
            }
            forecast_item = {
                "date": target_date.isoformat(),
                "label": _date_label(target_date),
                "predicted_score": round(score, 1),
                "predicted_visits": round(adjusted_visits, 1),
                "predicted_queue": round(adjusted_queue, 1),
                "alert_level": alert_level,
                "warning": warning,
                "confidence": factors["confidence"],
            }
            forecast.append(forecast_item)
            if persist:
                ProjectForecast.objects.update_or_create(
                    project=project,
                    model_name=selected.name,
                    target_time=target_dt,
                    defaults={
                        "predicted_score": forecast_item["predicted_score"],
                        "predicted_visits": forecast_item["predicted_visits"],
                        "predicted_queue": forecast_item["predicted_queue"],
                        "confidence": factors["confidence"],
                        "is_peak_alert": alert_level == ProjectForecast.ALERT_HIGH,
                        "alert_level": alert_level,
                        "warning": warning,
                        "factors": factors,
                    },
                )
        if persist:
            _persist_evaluation(project, selected.name, visits, start_date, today, horizon, selected.parameters())
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
    mode = _mode_for_result(modes)
    return {"mode": mode, "model": model, "generated_at": timezone.now().isoformat(), "items": items}


def evaluate_forecasts(*, days: int = 30, horizon: int = 7, model: str = "moving_average") -> list[dict]:
    today = timezone.localdate()
    start_date = today - timedelta(days=max(days - 1, horizon + 1))
    rows = []
    for project in Project.objects.all().order_by("name"):
        visits = _daily_visits(project, start_date, today)
        selected = _select_model(model, len(visits))
        row = _persist_evaluation(project, selected.name, visits, start_date, today, horizon, selected.parameters())
        rows.append(row)
    return rows


def _select_model(model: str, sample_size: int):
    requested = model.lower()
    if requested in {"prophet", "all"} and sample_size >= 30:
        try:
            return ProphetForecastModel()
        except OptionalDependencyUnavailable:
            pass
    if requested in {"lstm", "all"} and sample_size >= 30:
        try:
            return LSTMForecastModel()
        except OptionalDependencyUnavailable:
            pass
    if requested in {"linear", "linear_regression", "all"} and sample_size >= 14:
        return LinearRegressionModel()
    return MovingAverageModel()


def _daily_visits(project: Project, start_date, end_date) -> list[float]:
    rows = (
        PlayRecord.objects.filter(project=project, play_time__date__gte=start_date, play_time__date__lte=end_date)
        .values("play_time__date")
        .annotate(total=Count("id"))
    )
    by_day = {row["play_time__date"]: float(row["total"]) for row in rows}
    return [by_day.get(start_date + timedelta(days=i), 0.0) for i in range((end_date - start_date).days + 1)]


def _daily_queues(project: Project, start_date, end_date) -> list[float]:
    rows = (
        PlayRecord.objects.filter(project=project, play_time__date__gte=start_date, play_time__date__lte=end_date)
        .values("play_time__date")
        .annotate(avg_queue=Avg("queue_time"))
    )
    by_day = {row["play_time__date"]: float(row["avg_queue"] or 0) for row in rows}
    return [by_day.get(start_date + timedelta(days=i), float(project.queue_count or 0)) for i in range((end_date - start_date).days + 1)]


def _score_from_prediction(project: Project, visits: float, queue: float) -> float:
    demand_score = min(100.0, visits / max(project.daily_warn_threshold, 1) * 100)
    queue_score = min(100.0, queue / 30 * 100)
    realtime_score = min(100.0, project.queue_count / max(project.capacity, 1) * 100)
    return clamp(demand_score * 0.55 + queue_score * 0.25 + realtime_score * 0.2)


def _warning_for(project: Project, target_date, score: float, visits: float, queue: float, avg_queue: float, external_reason: str) -> tuple[str, str]:
    queue_spike = avg_queue > 0 and queue > avg_queue * 1.3
    visit_spike = visits >= project.daily_warn_threshold
    external_peak = bool(external_reason) and score >= 75
    if score >= 85 or visit_spike or queue_spike or external_peak:
        return (
            ProjectForecast.ALERT_HIGH,
            f"{target_date:%m月%d日} 10:00-12:00 {project.name}热度预计 {score:.0f} 分，排队压力较高，建议增加 1-2 名运维/疏导人员。",
        )
    if score >= 70:
        return (
            ProjectForecast.ALERT_WATCH,
            f"{target_date:%m月%d日} {project.name}热度预计 {score:.0f} 分，建议关注排队与设备状态。",
        )
    return ProjectForecast.ALERT_NONE, ""


def _external_factor(target_date) -> tuple[float, str]:
    factor = 1.18 if target_date.weekday() >= 5 else 1.0
    reason = "周末" if target_date.weekday() >= 5 else ""
    holiday = HolidayCalendar.objects.filter(date=target_date).order_by("-heat_multiplier").first()
    if holiday:
        factor *= holiday.heat_multiplier
        reason = holiday.name
    promo = (
        PromotionEvent.objects.filter(is_active=True, start_date__lte=target_date, end_date__gte=target_date)
        .order_by("-heat_multiplier")
        .first()
    )
    if promo:
        factor *= promo.heat_multiplier
        reason = f"{reason}+{promo.name}" if reason else promo.name
    return factor, reason


def _persist_evaluation(project: Project, model_name: str, visits: list[float], start_date, today, horizon: int, parameters: dict) -> dict:
    if len(visits) <= horizon + 2:
        actual = visits[-horizon:] if visits else []
        predicted = actual[:]
    else:
        train = visits[:-horizon]
        actual = visits[-horizon:]
        evaluator = LinearRegressionModel() if model_name != "moving_average" else MovingAverageModel()
        evaluator.fit(train, train)
        predicted = [value[0] for value in evaluator.predict(horizon)]
    mae = mean_absolute_error(actual, predicted)
    mse = mean_squared_error(actual, predicted)
    r2 = r2_score(actual, predicted)
    validation_start = today - timedelta(days=max(horizon - 1, 0))
    evaluation = ForecastEvaluation.objects.create(
        project=project,
        model_name=model_name,
        train_start=start_date,
        train_end=validation_start - timedelta(days=1),
        validation_start=validation_start,
        validation_end=today,
        horizon_days=horizon,
        mae=mae,
        mse=mse,
        r2=r2,
        sample_size=len(visits),
        parameters=parameters,
    )
    return {
        "project_id": project.id,
        "project_name": project.name,
        "model_name": model_name,
        "mae": evaluation.mae,
        "mse": evaluation.mse,
        "r2": evaluation.r2,
        "sample_size": evaluation.sample_size,
        "evaluated_at": timezone.localtime(evaluation.evaluated_at).strftime("%Y-%m-%d %H:%M"),
    }


def _confidence_for(sample_size: int, model_name: str) -> str:
    if sample_size >= 30 and model_name in {"prophet", "lstm"}:
        return "历史样本充足，已启用可选模型"
    if sample_size >= 14:
        return "历史样本适中，使用趋势模型"
    return "历史样本不足，已自动降级为移动平均"


def _date_label(target_date) -> str:
    if target_date.weekday() >= 5:
        return f"{target_date:%m-%d} 周末"
    return f"{target_date:%m-%d} 工作日"


def _mode_for_result(modes: list[str]) -> str:
    if not modes:
        return "moving_average"
    if len(set(modes)) == 1:
        return modes[0]
    return "mixed"
