from __future__ import annotations

from datetime import datetime

from django.http import JsonResponse
from django.utils import timezone

from analytics.models import ForecastEvaluation
from analytics.services.forecasting import build_forecast_rows, evaluate_baseline_forecasts
from analytics.services.heat import compute_project_heat_scores
from analytics.services.spatial import build_spatial_heat_payload
from core.auth_utils import staff_or_admin_required


def api_response(data, *, code: int = 0, message: str = "ok"):
    return JsonResponse({"code": code, "message": message, "data": data}, json_dumps_params={"ensure_ascii": False})


@staff_or_admin_required
def heat_score_api(request):
    start_date = _parse_date(request.GET.get("start_date") or request.GET.get("start"))
    end_date = _parse_date(request.GET.get("end_date") or request.GET.get("end"))
    days = _parse_int(request.GET.get("days"), default=7, min_value=1, max_value=180)
    rows = compute_project_heat_scores(days=days, start_date=start_date, end_date=end_date)
    project_id = _parse_int(request.GET.get("project_id"), default=0, min_value=0, max_value=10**9)
    if project_id:
        rows = [row for row in rows if row["project_id"] == project_id]
    return api_response({"items": rows, "weights": {"base": 25, "time": 15, "user": 15, "operations": 15, "external": 15, "subjective": 15}})


@staff_or_admin_required
def forecast_api(request):
    days = _parse_int(request.GET.get("days"), default=30, min_value=7, max_value=365)
    horizon = _parse_int(request.GET.get("horizon"), default=7, min_value=1, max_value=14)
    payload = build_forecast_rows(days=days, horizon=horizon, persist=False)
    project_id = _parse_int(request.GET.get("project_id"), default=0, min_value=0, max_value=10**9)
    if project_id:
        payload["items"] = [item for item in payload["items"] if item["project_id"] == project_id]
    return api_response(payload)


@staff_or_admin_required
def forecast_alerts_api(request):
    days = _parse_int(request.GET.get("days"), default=30, min_value=7, max_value=365)
    horizon = _parse_int(request.GET.get("horizon"), default=7, min_value=1, max_value=14)
    payload = build_forecast_rows(days=days, horizon=horizon, persist=False)
    alerts = []
    for item in payload["items"]:
        for forecast in item["forecast"]:
            if forecast["alert_level"] == "high":
                alerts.append(
                    {
                        "project_id": item["project_id"],
                        "project_name": item["project_name"],
                        **forecast,
                    }
                )
    return api_response({"items": alerts, "generated_at": payload["generated_at"], "mode": payload["mode"]})


@staff_or_admin_required
def forecast_evaluation_api(request):
    refresh = request.GET.get("refresh") == "1"
    if refresh or not ForecastEvaluation.objects.exists():
        rows = evaluate_baseline_forecasts(days=30, horizon=7)
    else:
        rows = [
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
    return api_response({"items": rows})


@staff_or_admin_required
def spatial_heat_api(request):
    days = _parse_int(request.GET.get("days"), default=7, min_value=1, max_value=180)
    return api_response(build_spatial_heat_payload(days=days))


@staff_or_admin_required
def heat_timeline_api(request):
    start_date = _parse_date(request.GET.get("start_date") or request.GET.get("start"))
    end_date = _parse_date(request.GET.get("end_date") or request.GET.get("end"))
    days = _parse_int(request.GET.get("days"), default=7, min_value=1, max_value=180)
    rows = compute_project_heat_scores(days=days, start_date=start_date, end_date=end_date)
    return api_response({"items": rows, "granularity": request.GET.get("granularity") or "day"})


@staff_or_admin_required
def project_detail_api(request, project_id: int):
    rows = compute_project_heat_scores(days=30)
    row = next((item for item in rows if item["project_id"] == project_id), None)
    if row is None:
        return api_response({}, code=1, message="项目不存在或暂无分析数据")
    forecast = build_forecast_rows(days=30, horizon=7)
    row["forecast"] = next((item for item in forecast["items"] if item["project_id"] == project_id), {})
    return api_response(row)


@staff_or_admin_required
def project_forecast_api(request, project_id: int):
    days = _parse_int(request.GET.get("days"), default=30, min_value=7, max_value=365)
    horizon = _parse_int(request.GET.get("horizon"), default=7, min_value=1, max_value=14)
    payload = build_forecast_rows(days=days, horizon=horizon, persist=False)
    item = next((row for row in payload["items"] if row["project_id"] == project_id), None)
    if item is None:
        return api_response({}, code=1, message="项目不存在或暂无预测数据")
    return api_response(item)


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_int(value: str | None, *, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(parsed, max_value))
