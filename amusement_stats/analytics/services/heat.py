from __future__ import annotations

import math
from datetime import datetime, time, timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone

from analytics.models import HolidayCalendar, ProjectIncident, ProjectReview, PromotionEvent
from projects.models import Project
from records.models import PlayRecord
from visitor.models import VisitorFavorite, VisitorFeedback


HEAT_WEIGHTS = {
    "base": 0.25,
    "time": 0.15,
    "user": 0.15,
    "operations": 0.15,
    "external": 0.15,
    "subjective": 0.15,
}


def date_window(*, days: int = 7, start_date=None, end_date=None) -> tuple[datetime, datetime]:
    today = timezone.localdate()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = end_date - timedelta(days=max(days - 1, 0))
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min))
    return start_dt, end_dt


def compute_project_heat_scores(*, days: int = 7, start_date=None, end_date=None) -> list[dict]:
    start_dt, end_dt = date_window(days=days, start_date=start_date, end_date=end_date)
    projects = list(Project.objects.all().order_by("name"))
    if not projects:
        return []

    project_ids = [p.id for p in projects]
    records = PlayRecord.objects.filter(project_id__in=project_ids, play_time__gte=start_dt, play_time__lt=end_dt)
    record_stats = {
        row["project_id"]: row
        for row in records.values("project_id").annotate(
            visits=Count("id"),
            avg_queue=Avg("queue_time"),
            repeat_sum=Sum("repeat_count"),
            maintenance_records=Count("id", filter=Q(status_snapshot=Project.STATUS_MAINTENANCE)),
            closed_records=Count("id", filter=Q(status_snapshot=Project.STATUS_CLOSED)),
        )
    }
    hour_stats: dict[int, dict[int, int]] = {}
    for row in records.annotate(hour=ExtractHour("play_time")).values("project_id", "hour").annotate(total=Count("id")):
        if row["hour"] is None:
            continue
        hour_stats.setdefault(row["project_id"], {})[int(row["hour"])] = int(row["total"])
    day_stats: dict[int, list[int]] = {pid: [] for pid in project_ids}
    day_rows = records.annotate(day=TruncDate("play_time")).values("project_id", "day").annotate(total=Count("id"))
    day_map = {(row["project_id"], row["day"]): int(row["total"]) for row in day_rows}
    days_count = max((end_dt.date() - start_dt.date()).days, 1)
    for pid in project_ids:
        day_stats[pid] = [day_map.get((pid, start_dt.date() + timedelta(days=i)), 0) for i in range(days_count)]

    favorites = dict(
        VisitorFavorite.objects.filter(project_id__in=project_ids)
        .values("project_id")
        .annotate(total=Count("id"))
        .values_list("project_id", "total")
    )
    review_stats = {
        row["project_id"]: row
        for row in ProjectReview.objects.filter(project_id__in=project_ids).values("project_id").annotate(
            avg_rating=Avg("rating"),
            review_count=Count("id"),
        )
    }
    incidents = {
        row["project_id"]: row
        for row in ProjectIncident.objects.filter(project_id__in=project_ids, started_at__lt=end_dt)
        .filter(Q(ended_at__isnull=True) | Q(ended_at__gte=start_dt))
        .values("project_id")
        .annotate(total=Count("id"), downtime=Sum("downtime_minutes"))
    }
    complaint_count = VisitorFeedback.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt).count()

    max_visits = max((record_stats.get(p.id, {}).get("visits") or 0 for p in projects), default=0) or 1
    max_queue = max((float(record_stats.get(p.id, {}).get("avg_queue") or 0) for p in projects), default=0) or 1
    max_favorites = max((favorites.get(p.id, 0) for p in projects), default=0) or 1

    rows = []
    external_score = _external_score_for_window(start_dt.date(), end_dt.date())
    for project in projects:
        stats = record_stats.get(project.id, {})
        visits = int(stats.get("visits") or 0)
        avg_queue = float(stats.get("avg_queue") or 0)
        repeat_sum = int(stats.get("repeat_sum") or 0)
        repeat_rate = repeat_sum / visits if visits else 0.0
        turnover = visits / project.capacity if project.capacity else 0.0
        peak_share = _peak_share(hour_stats.get(project.id, {}))
        volatility = _coefficient_of_variation(day_stats.get(project.id, []))
        favorite_score = favorites.get(project.id, 0) / max_favorites
        review = review_stats.get(project.id, {})
        avg_rating = float(review.get("avg_rating") or 4.0)
        incident = incidents.get(project.id, {})
        incident_count = int(incident.get("total") or 0)
        downtime = int(incident.get("downtime") or 0)
        downtime_records = int(stats.get("maintenance_records") or 0) + int(stats.get("closed_records") or 0)
        downtime_ratio = min(1.0, (downtime_records / visits) if visits else 0.0)
        complaint_penalty = min(0.4, complaint_count / max(sum(s.get("visits") or 0 for s in record_stats.values()), 1))

        base_score = _clamp100(70 * (visits / max_visits) + 30 * (1 - min(avg_queue / max_queue, 1)))
        time_score = _clamp100(55 * peak_share + 45 * min(volatility, 1.0))
        user_score = _clamp100(55 * min(repeat_rate, 1.0) + 25 * favorite_score + 20 * min(turnover, 1.0))
        operations_score = _clamp100(100 - incident_count * 18 - downtime / 10 - downtime_ratio * 40)
        subjective_score = _clamp100((avg_rating / 5) * 100 - complaint_penalty * 100)
        dimensions = {
            "base": round(base_score, 1),
            "time": round(time_score, 1),
            "user": round(user_score, 1),
            "operations": round(operations_score, 1),
            "external": round(external_score, 1),
            "subjective": round(subjective_score, 1),
        }
        score = round(sum(dimensions[k] * HEAT_WEIGHTS[k] for k in HEAT_WEIGHTS), 1)
        rows.append(
            {
                "project_id": project.id,
                "name": project.name,
                "project_name": project.name,
                "score": score,
                "dimensions": dimensions,
                "metrics": {
                    "visits": visits,
                    "avg_queue": round(avg_queue, 1),
                    "peak_share": round(peak_share * 100, 1),
                    "volatility": round(volatility, 3),
                    "repeat_rate": round(repeat_rate * 100, 1),
                    "turnover": round(turnover * 100, 1),
                    "incident_count": incident_count,
                    "downtime_minutes": downtime,
                    "avg_rating": round(avg_rating, 1),
                    "complaint_rate": round(complaint_penalty * 100, 1),
                    "queue_count": project.queue_count,
                    "status": project.status,
                    "region": project.effective_region(),
                },
            }
        )
    rows.sort(key=lambda item: item["score"], reverse=True)
    return rows


def _peak_share(hour_map: dict[int, int]) -> float:
    total = sum(hour_map.values())
    if total <= 0:
        return 0.0
    peak_total = sum(v for h, v in hour_map.items() if 10 <= h <= 12 or 17 <= h <= 19)
    return peak_total / total


def _coefficient_of_variation(values: list[int]) -> float:
    values = [float(v) for v in values]
    if not values:
        return 0.0
    avg = sum(values) / len(values)
    if avg <= 0:
        return 0.0
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    return math.sqrt(variance) / avg


def _external_score_for_window(start_date, end_date) -> float:
    holidays = HolidayCalendar.objects.filter(date__gte=start_date, date__lt=end_date)
    holiday_boost = sum(max(0.0, h.heat_multiplier - 1.0) for h in holidays)
    promos = PromotionEvent.objects.filter(is_active=True, start_date__lt=end_date, end_date__gte=start_date)
    promo_boost = sum(max(0.0, p.heat_multiplier - 1.0) for p in promos)
    return _clamp100(70 + min(30, (holiday_boost + promo_boost) * 20))


def _clamp100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))
