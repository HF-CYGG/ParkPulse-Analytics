from __future__ import annotations

from analytics.services.heat import compute_project_heat_scores
from visitor.explore_charts import project_map_latlng


def build_spatial_heat_payload(*, days: int = 7) -> dict:
    rows = compute_project_heat_scores(days=days)
    markers = []
    for row in rows:
        project = _project_from_row(row)
        if project is None:
            continue
        lat, lng = project_map_latlng(project)
        score = float(row["score"])
        markers.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "lat": lat,
                "lng": lng,
                "score": score,
                "radius": round(40 + score * 2.6, 1),
                "linked_heat": _linked_heat(row),
                "dimensions": row["dimensions"],
                "metrics": row["metrics"],
            }
        )
    return {"items": markers, "max_score": max((item["score"] for item in markers), default=0)}


def _project_from_row(row):
    from projects.models import Project

    try:
        return Project.objects.get(id=row["project_id"])
    except Project.DoesNotExist:
        return None


def _linked_heat(row: dict) -> list[dict]:
    score = float(row["score"])
    region = row["metrics"].get("region", "")
    if score < 55:
        return []
    return [
        {"target": "周边餐饮", "region": region, "score": round(score * 0.35, 1)},
        {"target": "文创零售", "region": region, "score": round(score * 0.28, 1)},
    ]
