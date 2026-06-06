from __future__ import annotations

import math

from analytics.models import ServiceFacility
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
                "facilities": _facility_heat(row, lat, lng),
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


def _facility_heat(row: dict, project_lat: float, project_lng: float) -> list[dict]:
    score = float(row["score"])
    if score < 35:
        return []
    items = []
    for facility in ServiceFacility.objects.filter(is_active=True):
        facility_lat, facility_lng = _facility_latlng(facility, project_lat, project_lng)
        distance = _distance_meters(project_lat, project_lng, facility_lat, facility_lng)
        if distance > 450:
            continue
        distance_factor = max(0.15, 1 - distance / 450)
        type_factor = 0.42
        if facility.facility_type == ServiceFacility.TYPE_RETAIL:
            type_factor = 0.34
        elif facility.facility_type == ServiceFacility.TYPE_REST:
            type_factor = 0.28
        linked_heat = round(score * distance_factor * type_factor, 1)
        items.append(
            {
                "id": facility.id,
                "name": facility.name,
                "facility_type": facility.facility_type,
                "region": facility.region,
                "lat": facility_lat,
                "lng": facility_lng,
                "distance_meters": round(distance, 1),
                "linked_heat": linked_heat,
            }
        )
    items.sort(key=lambda item: item["linked_heat"], reverse=True)
    return items[:8]


def _facility_latlng(facility: ServiceFacility, fallback_lat: float, fallback_lng: float) -> tuple[float, float]:
    if facility.latitude is not None and facility.longitude is not None:
        return float(facility.latitude), float(facility.longitude)
    return fallback_lat, fallback_lng


def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return math.hypot(lat1 - lat2, lng1 - lng2) * 111_000
