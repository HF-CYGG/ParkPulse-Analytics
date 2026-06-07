from __future__ import annotations

import math
from datetime import datetime, time, timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone

from accounts.models import VisitorProfile
from analytics.models import HolidayCalendar, ProjectIncident, ProjectReview, PromotionEvent, WeatherObservation
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
    external = _external_score_for_window(start_dt.date(), end_dt.date())
    profile_summary = _profile_summary()
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
        profile_score, profile_breakdown = _profile_preference(project, profile_summary)
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
        user_score = _clamp100(40 * min(repeat_rate, 1.0) + 20 * favorite_score + 20 * min(turnover, 1.0) + 20 * (profile_score / 100))
        operations_score = _clamp100(100 - incident_count * 18 - downtime / 10 - downtime_ratio * 40)
        subjective_score = _clamp100((avg_rating / 5) * 100 - complaint_penalty * 100)
        dimensions = {
            "base": round(base_score, 1),
            "time": round(time_score, 1),
            "user": round(user_score, 1),
            "operations": round(operations_score, 1),
            "external": round(external["score"], 1),
            "subjective": round(subjective_score, 1),
        }
        score = round(sum(dimensions[k] * HEAT_WEIGHTS[k] for k in HEAT_WEIGHTS), 1)
        dimension_reasons = {
            "base": _base_reason(visits, avg_queue),
            "time": f"高峰时段占比 {peak_share * 100:.1f}%，日波动系数 {volatility:.2f}",
            "user": f"重复游玩率 {repeat_rate * 100:.1f}%，画像匹配 {profile_score:.1f} 分，收藏热度 {favorite_score * 100:.1f} 分",
            "operations": f"故障/维护 {incident_count} 次，维护影响 {downtime} 分钟",
            "external": external["reason"],
            "subjective": f"平均评分 {avg_rating:.1f}，投诉率 {complaint_penalty * 100:.1f}%",
        }
        reasons = _top_reasons(dimensions, dimension_reasons)
        rows.append(
            {
                "project_id": project.id,
                "name": project.name,
                "project_name": project.name,
                "score": score,
                "dimensions": dimensions,
                "reasons": reasons,
                "dimension_reasons": dimension_reasons,
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
                    "external": external,
                    "user_profile_breakdown": profile_breakdown,
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


def _external_score_for_window(start_date, end_date) -> dict:
    holidays = HolidayCalendar.objects.filter(date__gte=start_date, date__lt=end_date)
    holiday_boost = sum(max(0.0, h.heat_multiplier - 1.0) for h in holidays)
    promos = PromotionEvent.objects.filter(is_active=True, start_date__lt=end_date, end_date__gte=start_date)
    promo_boost = sum(max(0.0, p.heat_multiplier - 1.0) for p in promos)
    weather_rows = list(WeatherObservation.objects.filter(date__gte=start_date, date__lt=end_date))
    weather_factor = sum(row.heat_multiplier for row in weather_rows) / len(weather_rows) if weather_rows else 1.0
    weather_delta = (weather_factor - 1.0) * 60
    score = _clamp100(70 + min(30, (holiday_boost + promo_boost) * 20) + weather_delta)
    weather_label = "无天气样本，按常规天气处理"
    if weather_rows:
        first = weather_rows[0]
        weather_label = f"{first.get_weather_type_display()}，系数 {weather_factor:.2f}"
    parts = [weather_label]
    if holidays.exists():
        parts.append("节假日/周末提升")
    if promos.exists():
        parts.append("促销活动提升")
    return {
        "score": score,
        "weather": {
            "sample_count": len(weather_rows),
            "factor": round(weather_factor, 2),
            "description": weather_label,
        },
        "holiday_boost": round(holiday_boost, 2),
        "promotion_boost": round(promo_boost, 2),
        "reason": "；".join(parts),
    }


def _profile_summary() -> dict:
    profiles = list(VisitorProfile.objects.all())
    total = len(profiles)
    if not profiles:
        return {"total": 0, "age": {}, "consumption": {}, "children": 0, "elderly": 0}
    age = {}
    consumption = {}
    children = 0
    elderly = 0
    for profile in profiles:
        age[profile.age_group] = age.get(profile.age_group, 0) + 1
        consumption[profile.consumption_level] = consumption.get(profile.consumption_level, 0) + 1
        children += 1 if profile.with_children else 0
        elderly += 1 if profile.with_elderly else 0
    return {"total": total, "age": age, "consumption": consumption, "children": children, "elderly": elderly}


def _profile_preference(project: Project, summary: dict) -> tuple[float, dict]:
    total = max(summary.get("total") or 0, 1)
    age = summary.get("age", {})
    consumption = summary.get("consumption", {})
    score = 55.0
    if project.project_type == Project.TYPE_FAMILY:
        score += (age.get(VisitorProfile.AGE_FAMILY, 0) + summary.get("children", 0)) / total * 35
    elif project.project_type == Project.TYPE_THRILL:
        score += (age.get(VisitorProfile.AGE_TEEN, 0) + age.get(VisitorProfile.AGE_ADULT, 0)) / total * 30
        score += consumption.get(VisitorProfile.CONSUMPTION_HIGH, 0) / total * 10
    elif project.project_type == Project.TYPE_VIEW:
        score += (age.get(VisitorProfile.AGE_SENIOR, 0) + summary.get("elderly", 0)) / total * 30
        score += consumption.get(VisitorProfile.CONSUMPTION_LOW, 0) / total * 8
    breakdown = {
        "sample_size": summary.get("total", 0),
        "age_group_score": round(score, 1),
        "children_share": round(summary.get("children", 0) / total * 100, 1),
        "elderly_share": round(summary.get("elderly", 0) / total * 100, 1),
        "consumption": consumption,
    }
    return _clamp100(score), breakdown


def _base_reason(visits: int, avg_queue: float) -> str:
    if visits <= 0:
        return "暂无游玩记录，按低热度处理"
    return f"游玩人次 {visits}，平均排队 {avg_queue:.1f} 分钟"


def _top_reasons(dimensions: dict, dimension_reasons: dict) -> list[str]:
    ordered = sorted(dimensions.items(), key=lambda item: item[1], reverse=True)
    reasons = [dimension_reasons[key] for key, _ in ordered[:3]]
    low = [dimension_reasons[key] for key, value in ordered if value < 55]
    if low:
        reasons.append(f"短板：{low[0]}")
    return reasons


def _clamp100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))
