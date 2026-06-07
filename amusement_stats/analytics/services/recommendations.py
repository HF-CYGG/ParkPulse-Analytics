from __future__ import annotations

import math

from django.db.models import Avg

from analytics.models import ProjectReview
from analytics.services.heat import compute_project_heat_scores
from projects.models import Project
from visitor.explore_charts import project_map_latlng


def build_recommendations(profile: dict | None = None) -> dict:
    profile = profile or {}
    heat_rows = {row["project_id"]: row for row in compute_project_heat_scores(days=7)}
    projects = list(Project.objects.exclude(status=Project.STATUS_CLOSED).order_by("name"))
    ratings = _project_ratings()
    origin = _route_origin(projects)
    scored = []
    for project in projects:
        heat = heat_rows.get(project.id, _empty_heat(project))
        profile_score = _profile_score(project, profile)
        queue_score = max(0.0, 100 - min(100, project.queue_count / max(project.capacity, 1) * 100))
        rating_score = ratings.get(project.id, 80.0)
        distance_score = _distance_score(project, origin)
        budget_score = _budget_score(project, profile)
        heat_penalty = max(0.0, float(heat.get("score") or 0) - 75) * 0.35
        total = (
            profile_score * 0.35
            + queue_score * 0.25
            + rating_score * 0.20
            + distance_score * 0.10
            + budget_score * 0.10
            - heat_penalty
        )
        scored.append(
            {
                "project": project,
                "heat": heat,
                "score": round(total, 1),
                "profile_score": round(profile_score, 1),
                "queue_score": round(queue_score, 1),
                "rating_score": round(rating_score, 1),
                "distance_score": round(distance_score, 1),
                "budget_score": round(budget_score, 1),
                "heat_penalty": round(heat_penalty, 1),
                "reason": _reason_for(project, profile, heat, queue_score, rating_score),
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    route_items = _route_items(scored, profile)
    avoid_peak = [_public_item(item) for item in sorted(scored, key=lambda item: (-item["queue_score"], -item["rating_score"], -item["score"]))[:5]]
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


def similar_low_queue_projects(project: Project, *, limit: int = 3) -> list[dict]:
    candidates = []
    ratings = _project_ratings()
    for candidate in (
        Project.objects.exclude(id=project.id)
        .exclude(status=Project.STATUS_CLOSED)
        .filter(project_type=project.project_type)
        .order_by("queue_count", "name")
    ):
        queue_score = max(0.0, 100 - min(100, candidate.queue_count / max(candidate.capacity, 1) * 100))
        rating_score = ratings.get(candidate.id, 80.0)
        total = queue_score * 0.65 + rating_score * 0.35
        candidates.append(
            {
                "project_id": candidate.id,
                "project_name": candidate.name,
                "queue_count": candidate.queue_count,
                "recommend_score": round(total, 1),
                "reason": "同类型项目，当前排队压力更低",
            }
        )
    candidates.sort(key=lambda item: item["recommend_score"], reverse=True)
    return candidates[:limit]


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
    low_budget = [_public_item(item) for item in scored if item["budget_score"] >= 85][:3]
    elderly = [
        _public_item(item)
        for item in scored
        if item["project"].project_type in {Project.TYPE_VIEW, Project.TYPE_FAMILY}
    ][:3]
    combos = []
    if profile.get("with_children") and family:
        combos.append({"name": "亲子轻松组合", "items": family, "reason": "优先低刺激、低排队和亲子项目。"})
    if profile.get("with_elderly") and elderly:
        combos.append({"name": "长者友好休闲组合", "items": elderly, "reason": "优先步行压力小、刺激强度低的项目。"})
    if (str(profile.get("budget_level") or "") == "low" or int(profile.get("budget_amount") or 0) <= 120) and low_budget:
        combos.append({"name": "低预算高性价比组合", "items": low_budget, "reason": "按预算匹配和低排队压力综合选择。"})
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
        "profile_score": item["profile_score"],
        "rating_score": item["rating_score"],
        "distance_score": item["distance_score"],
        "budget_score": item["budget_score"],
        "heat_penalty": item["heat_penalty"],
        "reason": item["reason"],
        "lat": lat,
        "lng": lng,
    }
    if seq is not None:
        payload["seq"] = seq
    return payload


def _profile_score(project: Project, profile: dict) -> float:
    tags = str(profile.get("preference_tags") or "").lower()
    age_group = str(profile.get("age_group") or "")
    score = 45.0
    if age_group == "child" and project.project_type == Project.TYPE_FAMILY:
        score += 25
    if age_group == "teen" and project.project_type == Project.TYPE_THRILL:
        score += 20
    if age_group == "senior" and project.project_type in {Project.TYPE_VIEW, Project.TYPE_FAMILY}:
        score += 25
    if age_group == "family" and project.project_type == Project.TYPE_FAMILY:
        score += 25
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
    if "popular" in tags or "hot" in tags or "热门" in tags:
        score += 15
    if "low_budget" in tags or "低预算" in tags:
        score += 18 if project.project_type in {Project.TYPE_FAMILY, Project.TYPE_VIEW} else -5
    if "night" in tags or "夜场" in tags:
        score += 18 if project.project_type == Project.TYPE_VIEW else 6
    if "photo" in tags or "拍照" in tags:
        score += 20 if project.project_type == Project.TYPE_VIEW else 4
    if "leisure" in tags or "休闲" in tags:
        score += 18 if project.project_type in {Project.TYPE_VIEW, Project.TYPE_FAMILY} else -8
    if "senior" in tags or "长者友好" in tags:
        score += 24 if project.project_type in {Project.TYPE_VIEW, Project.TYPE_FAMILY} else -12
    return max(0.0, min(100.0, score))


def _budget_score(project: Project, profile: dict) -> float:
    level = str(profile.get("budget_level") or "medium")
    budget_amount = int(profile.get("budget_amount") or 0)
    if level == "low":
        return 90 if project.project_type in {Project.TYPE_FAMILY, Project.TYPE_VIEW} else 65
    if level == "high" or budget_amount >= 300:
        return 95
    return 80


def _project_ratings() -> dict[int, float]:
    rows = (
        ProjectReview.objects.values("project_id")
        .annotate(
            avg_experience=Avg("experience_score"),
            avg_queue=Avg("queue_reasonableness_score"),
            avg_safety=Avg("safety_score"),
            avg_rating=Avg("rating"),
        )
    )
    ratings = {}
    for row in rows:
        scores = [row.get("avg_experience"), row.get("avg_queue"), row.get("avg_safety")]
        scores = [float(score) for score in scores if score]
        if scores:
            ratings[row["project_id"]] = sum(scores) / len(scores) / 5 * 100
        elif row.get("avg_rating"):
            ratings[row["project_id"]] = float(row["avg_rating"]) / 5 * 100
    return ratings


def _route_origin(projects: list[Project]) -> tuple[float, float]:
    if not projects:
        return 0.0, 0.0
    points = [project_map_latlng(project) for project in projects]
    return sum(point[0] for point in points) / len(points), sum(point[1] for point in points) / len(points)


def _distance_score(project: Project, origin: tuple[float, float]) -> float:
    lat, lng = project_map_latlng(project)
    distance = _distance(lat, lng, origin[0], origin[1])
    return max(35.0, 100 - distance * 9000)


def _reason_for(project: Project, profile: dict, heat: dict, queue_score: float, rating_score: float) -> str:
    parts = []
    if profile.get("with_children") and project.project_type == Project.TYPE_FAMILY:
        parts.append("适合亲子同行")
    if profile.get("with_elderly") and project.project_type in {Project.TYPE_VIEW, Project.TYPE_FAMILY}:
        parts.append("步行和刺激强度更友好")
    tags = str(profile.get("preference_tags") or "")
    if "夜场" in tags and project.project_type == Project.TYPE_VIEW:
        parts.append("适合夜场观光")
    if "拍照" in tags and project.project_type == Project.TYPE_VIEW:
        parts.append("适合拍照打卡")
    if queue_score >= 75:
        parts.append("当前排队压力较低")
    if rating_score >= 85:
        parts.append("近期评分较高")
    if heat["score"] >= 70:
        parts.append("热度较高，建议按推荐时段体验")
    return "；".join(parts) or "与当前画像和实时热度匹配"


def _empty_heat(project: Project) -> dict:
    return {"score": 0, "dimensions": {}, "metrics": {"queue_count": project.queue_count, "region": project.effective_region()}}


def _distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return math.hypot(lat1 - lat2, lng1 - lng2)
