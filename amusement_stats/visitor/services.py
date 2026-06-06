from datetime import datetime, time, timedelta

from django.db.models import Count
from django.utils import timezone

from records.models import PlayRecord


def public_hot_ranking(*, days: int = 7, top_n: int = 10) -> list[dict]:
    """
    近 N 日全园聚合：仅返回对外展示所需字段（不含人次绝对值，按分位划档）。
    返回项：rank, project_id, project_name, heat_level（高/中/低）, heat_hint（简短文案）
    """
    today = timezone.localdate()
    start_date = today - timedelta(days=max(days - 1, 0))
    day_start = timezone.make_aware(datetime.combine(start_date, time.min))
    day_end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))

    rows = list(
        PlayRecord.objects.filter(play_time__gte=day_start, play_time__lt=day_end)
        .values("project_id", "project__name")
        .annotate(visits=Count("id"))
        .order_by("-visits")[:top_n]
    )
    if not rows:
        return []

    counts = [r["visits"] for r in rows]
    vmax = max(counts)

    def level_for(v: int) -> str:
        if vmax <= 0:
            return "低"
        ratio = v / vmax
        if ratio >= 0.66:
            return "高"
        if ratio >= 0.33:
            return "中"
        return "低"

    hint_map = {"高": "人气很旺，建议错峰体验", "中": "热度适中", "低": "相对宽松"}

    out = []
    for i, r in enumerate(rows, start=1):
        lvl = level_for(r["visits"])
        out.append(
            {
                "rank": i,
                "project_id": r["project_id"],
                "project_name": r["project__name"],
                "heat_level": lvl,
                "heat_hint": hint_map[lvl],
            }
        )
    return out
