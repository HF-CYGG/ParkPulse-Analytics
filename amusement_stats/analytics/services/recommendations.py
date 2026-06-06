from __future__ import annotations

import math

from analytics.services.heat import compute_project_heat_scores
from projects.models import Project
from visitor.explore_charts import project_map_latlng


def build_recommendations(profile: dict | None = None) -> dict:
    profile = profile or {}
    heat_rows = {row["project_id"]: row for row in compute_project_heat_scores(days=7)}
    projects = list(Project.objects.exclude(status=Project.STATUS_CLOSED).order_by("name"))
    scored = []
    for project in projects:
        heat = heat_rows.get(project.id, _empty_heat(project))
        preference = _preference_score(project, profile)
        queue_score = max(0.0, 100 - min(100, project.queue_count / max(project.capacity, 1) * 100))
        heat_score = max(0.0, 100 - heat["score"])
        budget_score = _budget_score(project, profile)
        total = preference * 0.35 + queue_score * 0.25 + heat_score * 0.2 + budget_score * 0.1 + 10
        scored.append(
            {
                "project": project,
                "heat": heat,
                "score": round(total, 1),
                "queue_score": round(queue_score, 1),
                "reason": _reason_for(project, profile, heat, queue_score),
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    route_items = _route_items(scored, profile)
    avoid_peak = [_public_item(item) for item in sorted(scored, key=lambda item: (-item["queue_score"], -item["score"]))[:5]]
    combos = _combo_items(scored, profile)
    return {
        "avoid_peak": avoid_peak,
        "route": {
            "title": "基于实时热度的推荐路线",
            "estimated_minutes": min(int(profile.get("available_minutes") or 180), max(45, len(route_items) * 35)),
            "items": route_items,
        },
        "combos": combos,
    }


def _route_items(scored: list[dict], profile: dict) -> list[dict]:
    limit = max(2, min(6, int((profile.get("available_minutes") or 180) / 35)))
    selected = scored[:limit]
    if not selected:
        return []
    ordered = [selected.pop(0)]
    while selected:
        last_project = ordered[-1]["project"]
        last_lat, last_lng = project_map_latlng(last_project)
        next_idx, _ = min(
            enumerate(selected),
            key=lambda pair: _distance(last_lat, last_lng, *project_map_latlng(pair[1]["project"])),
        )
        ordered.append(selected.pop(next_idx))
    return [_public_item(item, seq=i + 1) for i, item in enumerate(ordered)]


def _combo_items(scored: list[dict], profile: dict) -> list[dict]:
    family = [_public_item(item) for item in scored if item["project"].project_type == Project.TYPE_FAMILY][:3]
    thrill = [_public_item(item) for item in scored if item["project"].project_type == Project.TYPE_THRILL][:3]
    view = [_public_item(item) for item in scored if item["project"].project_type == Project.TYPE_VIEW][:3]
    combos = []
    if profile.get("with_children") and family:
        combos.append({"name": "亲子轻松组合", "items": family, "reason": "优先低刺激、低排队和亲子项目。"})
    if thrill:
        combos.append({"name": "热门刺激组合", "items": thrill, "reason": "适合偏好刺激项目的游客，建议避开高峰时段。"})
    if view:
        combos.append({"name": "休闲观光组合", "items": view, "reason": "适合拍照、休息和长辈同行。"})
    if not combos and scored:
        combos.append({"name": "综合推荐组合", "items": [_public_item(item) for item in scored[:3]], "reason": "按偏好和当前排队压力综合排序。"})
    return combos


def _public_item(item: dict, *, seq: int | None = None) -> dict:
    project = item["project"]
    lat, lng = project_map_latlng(project)
    payload = {
        "project_id": project.id,
        "project_name": project.name,
        "project_type": project.project_type,
        "queue_count": project.queue_count,
        "heat_score": item["heat"]["score"],
        "recommend_score": item["score"],
        "reason": item["reason"],
        "lat": lat,
        "lng": lng,
    }
    if seq is not None:
        payload["seq"] = seq
    return payload


def _preference_score(project: Project, profile: dict) -> float:
    tags = str(profile.get("preference_tags") or "").lower()
    score = 45.0
    if profile.get("with_children") and project.project_type == Project.TYPE_FAMILY:
        score += 35
    if profile.get("with_elderly") and project.project_type in {Project.TYPE_VIEW, Project.TYPE_FAMILY}:
        score += 25
    if "thrill" in tags or "刺激" in tags:
        score += 25 if project.project_type == Project.TYPE_THRILL else -10
    if "family" in tags or "亲子" in tags:
        score += 25 if project.project_type == Project.TYPE_FAMILY else -5
    if "view" in tags or "观光" in tags:
        score += 25 if project.project_type == Project.TYPE_VIEW else -5
    if "low_queue" in tags or "低排队" in tags:
        score += max(0, 20 - project.queue_count)
    return max(0.0, min(100.0, score))


def _budget_score(project: Project, profile: dict) -> float:
    level = str(profile.get("budget_level") or "medium")
    if level == "low" and project.project_type == Project.TYPE_THRILL:
        return 60
    if level == "high":
        return 90
    return 80


def _reason_for(project: Project, profile: dict, heat: dict, queue_score: float) -> str:
    parts = []
    if profile.get("with_children") and project.project_type == Project.TYPE_FAMILY:
        parts.append("适合亲子同行")
    if profile.get("with_elderly") and project.project_type in {Project.TYPE_VIEW, Project.TYPE_FAMILY}:
        parts.append("步行和刺激强度更友好")
    if queue_score >= 75:
        parts.append("当前排队压力较低")
    if heat["score"] >= 70:
        parts.append("热度较高，建议按推荐时段体验")
    return "；".join(parts) or "与当前画像和实时热度匹配"


def _empty_heat(project: Project) -> dict:
    return {"score": 0, "dimensions": {}, "metrics": {"queue_count": project.queue_count, "region": project.effective_region()}}


def _distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return math.hypot(lat1 - lat2, lng1 - lng2)
