"""园区分区参考坐标（WGS84），用于后台地图选点初始位置与游客端示意偏移。"""

from __future__ import annotations

import math

from .models import Project

REGION_CENTER: dict[str, tuple[float, float]] = {
    Project.REGION_ENTRANCE: (31.240, 121.495),
    Project.REGION_FAMILY: (31.236, 121.488),
    Project.REGION_THRILL: (31.232, 121.502),
    Project.REGION_VIEW: (31.238, 121.505),
    Project.REGION_REST: (31.234, 121.492),
    Project.REGION_CATERING: (31.231, 121.498),
}
DEFAULT_CENTER: tuple[float, float] = (31.235, 121.495)


def center_for_region(region: str | None) -> tuple[float, float]:
    if not region:
        return DEFAULT_CENTER
    return REGION_CENTER.get(region, DEFAULT_CENTER)


def safe_latlng(lat_value, lng_value) -> tuple[float, float] | None:
    """将任意来源的经纬度规整为可用浮点数，非法值统一返回 None。"""

    try:
        lat = float(lat_value)
        lng = float(lng_value)
    except (TypeError, ValueError):
        return None

    # 统一拦截 NaN、无穷大以及越界坐标，避免前端把异常值继续传给 Leaflet。
    if not math.isfinite(lat) or not math.isfinite(lng):
        return None
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return None
    return lat, lng


def project_or_region_latlng(project: Project) -> tuple[tuple[float, float], bool]:
    """优先返回项目自身有效坐标；若坐标缺失或非法，则回退到所属区域默认中心。"""

    coords = safe_latlng(project.latitude, project.longitude)
    if coords is not None:
        return coords, False
    return center_for_region(project.effective_region()), True


def initial_marker_latlng(project: Project) -> tuple[float, float]:
    """编辑页地图：已保存坐标则用之，否则用所属区域参考中心。"""

    coords, _ = project_or_region_latlng(project)
    return coords
