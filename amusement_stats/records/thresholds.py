from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from django.utils import timezone

from projects.models import Project
from records.models import PlayRecord


def _ensure_aware(dt):
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


def check_project_capacity_and_daily_threshold(
    project: Project,
    candidate_play_time,
    *,
    exclude_record_id: int | None = None,
    pending_records: Iterable[PlayRecord] | None = None,
):
    """
    统一阈值判定：
    - 并发窗口：record.play_time <= t < record.play_time + cycle_minutes （左闭右开）
    - 日阈值：同自然日记录数（按 candidate_play_time 所在本地日期）
    """
    candidate = _ensure_aware(candidate_play_time)
    cycle_minutes = max(int(project.cycle_minutes or 1), 1)
    window_start = candidate - timedelta(minutes=cycle_minutes)

    active_qs = PlayRecord.objects.filter(
        project=project,
        play_time__lte=candidate,
        play_time__gt=window_start,
    )
    day_qs = PlayRecord.objects.filter(
        project=project,
        play_time__date=timezone.localtime(candidate).date(),
    )

    if exclude_record_id:
        active_qs = active_qs.exclude(id=exclude_record_id)
        day_qs = day_qs.exclude(id=exclude_record_id)

    active_count = active_qs.count()
    day_count = day_qs.count()

    pending_active = 0
    pending_day = 0
    for p in pending_records or []:
        if p.project_id != project.id:
            continue
        p_time = _ensure_aware(p.play_time)
        if p_time is None:
            continue
        if p_time <= candidate < p_time + timedelta(minutes=cycle_minutes):
            pending_active += 1
        if timezone.localtime(p_time).date() == timezone.localtime(candidate).date():
            pending_day += 1

    active_count += pending_active
    day_count += pending_day

    capacity_limit = int(project.capacity or 0)
    daily_limit = int(project.daily_warn_threshold or 0)

    capacity_blocked = capacity_limit > 0 and active_count >= capacity_limit
    daily_blocked = daily_limit > 0 and day_count >= daily_limit

    messages = []
    if capacity_blocked:
        messages.append(
            f"项目【{project.name}】在 {timezone.localtime(candidate):%Y-%m-%d %H:%M} 时段并发占用为 {active_count}，"
            f"已达到/超过最大承载量 {capacity_limit}，本次无法录入。"
        )
    if daily_blocked:
        messages.append(
            f"项目【{project.name}】在 {timezone.localtime(candidate):%Y-%m-%d} 当日记录数为 {day_count}，"
            f"已达到/超过日预警阈值 {daily_limit}，本次无法录入。"
        )

    return {
        "allow": not (capacity_blocked or daily_blocked),
        "reason_codes": [code for code, flag in [("capacity", capacity_blocked), ("daily", daily_blocked)] if flag],
        "messages": messages,
        "capacity_blocked": capacity_blocked,
        "daily_blocked": daily_blocked,
        "active_count": active_count,
        "capacity_limit": capacity_limit,
        "day_count": day_count,
        "daily_limit": daily_limit,
        "candidate_play_time": candidate,
    }
