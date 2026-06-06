"""Plotly / Folium：游客端数据洞察与简易园区地图。"""

from __future__ import annotations

import hashlib
from datetime import date, datetime

import folium
import plotly.graph_objects as go
from django.db.models import Count
from django.db.models.functions import Extract, TruncDate
from django.utils import timezone

from projects.location_defaults import DEFAULT_CENTER, REGION_CENTER
from projects.models import Project
from records.models import PlayRecord

# Plotly 图表内文字与悬停统一中文；字体栈避免中文变方块
_PLOT_FONT = dict(family="'Microsoft YaHei','PingFang SC','Noto Sans SC',SimHei,sans-serif", size=13)
_PLOT_TITLE_FONT = dict(family="'Microsoft YaHei','PingFang SC','Noto Sans SC',SimHei,sans-serif", size=15)


def _fmt_cn_date(d: date | datetime | None) -> str:
    if d is None:
        return ""
    if isinstance(d, datetime):
        d = d.date()
    return f"{d.year}年{d.month}月{d.day}日"

def _stable_offset(project_id: int) -> tuple[float, float]:
    h = hashlib.md5(str(project_id).encode()).hexdigest()
    a = int(h[:8], 16)
    b = int(h[8:16], 16)
    return ((a % 200) - 100) / 8000.0, ((b % 200) - 100) / 8000.0


def project_map_latlng(project: Project) -> tuple[float, float]:
    if project.latitude is not None and project.longitude is not None:
        return float(project.latitude), float(project.longitude)
    base = REGION_CENTER.get(project.effective_region(), DEFAULT_CENTER)
    dx, dy = _stable_offset(project.id)
    return base[0] + dx, base[1] + dy


def build_play_analytics_html() -> str:
    """基于游玩记录表 PlayRecord 的真实入库数据：近 14 日按日、近 7 日按小时聚合统计，单页 Plotly。"""
    now = timezone.now()
    from datetime import timedelta

    start_day = now - timedelta(days=14)
    start_hour = now - timedelta(days=7)

    daily = (
        PlayRecord.objects.filter(play_time__gte=start_day)
        .annotate(d=TruncDate("play_time"))
        .values("d")
        .annotate(c=Count("id"))
        .order_by("d")
    )
    days = [row["d"] for row in daily]
    day_counts = [row["c"] for row in daily]
    day_labels_cn = [_fmt_cn_date(d) for d in days]
    day_tick_short: list[str] = []
    for d in days:
        if isinstance(d, datetime):
            d = d.date()
        if isinstance(d, date):
            day_tick_short.append(f"{d.month}月{d.day}日")
        else:
            day_tick_short.append(str(d) if d is not None else "")

    hourly_rows = (
        PlayRecord.objects.filter(play_time__gte=start_hour)
        .annotate(hour=Extract("play_time", "hour"))
        .values("hour")
        .annotate(c=Count("id"))
        .order_by("hour")
    )
    hour_to_count = {int(r["hour"]): r["c"] for r in hourly_rows}
    hours = list(range(24))
    hour_counts = [hour_to_count.get(h, 0) for h in hours]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=day_tick_short if day_tick_short else day_labels_cn,
            y=day_counts,
            name="每日记录条数",
            marker_color="#0d6efd",
            customdata=day_labels_cn,
            hovertemplate="<b>%{customdata}</b><br>游玩记录：<b>%{y}</b> 条<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="近 14 日游玩记录条数（真实数据）", font=_PLOT_TITLE_FONT),
        xaxis_title="日期",
        yaxis_title="条数",
        font=_PLOT_FONT,
        margin=dict(l=48, r=20, t=56, b=48),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,0.9)",
        hoverlabel=dict(font=_PLOT_FONT),
    )
    daily_html = fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"locale": "zh-CN", "displaylogo": False, "responsive": True},
    )

    hour_labels = [f"{h} 时" for h in hours]
    fig2 = go.Figure(
        data=[
            go.Scatter(
                x=hour_labels,
                y=hour_counts,
                mode="lines+markers",
                line=dict(color="#198754", width=2),
                fill="tozeroy",
                name="记录条数",
                hovertemplate="时段：<b>%{x}</b><br>合计记录：<b>%{y}</b> 条<extra></extra>",
            )
        ]
    )
    fig2.update_layout(
        title=dict(text="近 7 日按小时分布（0–23 时，真实数据）", font=_PLOT_TITLE_FONT),
        xaxis_title="时段（小时）",
        yaxis_title="条数",
        font=_PLOT_FONT,
        margin=dict(l=48, r=20, t=56, b=48),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,0.9)",
        hoverlabel=dict(font=_PLOT_FONT),
    )
    hourly_html = fig2.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"locale": "zh-CN", "displaylogo": False, "responsive": True},
    )

    # Plotly.js + 中文 locale（模式栏等尽量显示中文）
    return (
        '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>\n'
        '<script src="https://cdn.plot.ly/plotly-locale-zh-cn-2.35.2.js"></script>\n'
        f'<div class="mb-4">{daily_html}</div>\n'
        f"<div>{hourly_html}</div>"
    )


def build_folium_map_html() -> str:
    """简易园区地图：项目点位（有坐标用真实值，否则按区域示意）。默认高德中文路网底图。"""
    projects = list(Project.objects.all().order_by("name"))
    if not projects:
        return '<p class="text-muted">暂无项目数据，无法生成地图。</p>'

    center = project_map_latlng(projects[0])
    # 先建空白底图，再叠中文路网；避免 OSM 默认英文地名占主导
    m = folium.Map(location=[center[0], center[1]], zoom_start=15, tiles=None)
    gaode_tiles = (
        "https://webrd0{s}.is.autonavi.com/appmaptile?"
        "lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
    )
    folium.TileLayer(
        tiles=gaode_tiles,
        attr='© <a href="https://ditu.amap.com/" target="_blank">高德地图</a>',
        name="高德路网（中文标注）",
        subdomains="1234",
        overlay=False,
        control=True,
    ).add_to(m)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap（英文标注）",
        overlay=False,
        control=True,
    ).add_to(m)

    bounds: list[list[float]] = []
    for p in projects:
        lat, lng = project_map_latlng(p)
        bounds.append([lat, lng])
        tip = f"{p.name} · {p.get_project_type_display()}"
        popup_html = (
            f"<div style='min-width:200px;font-family:Microsoft YaHei,PingFang SC,sans-serif'>"
            f"<strong>{p.name}</strong><br>"
            f"类型：{p.get_project_type_display()}<br>"
            f"状态：{p.get_status_display()}<br>"
            f"<span style='color:#666;font-size:12px'>坐标为示意或录入值，请以现场为准</span>"
            f"</div>"
        )
        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=folium.Tooltip(tip, sticky=False),
        ).add_to(m)

    if len(bounds) >= 2:
        lats = [b[0] for b in bounds]
        lngs = [b[1] for b in bounds]
        pad = 0.002
        m.fit_bounds([[min(lats) - pad, min(lngs) - pad], [max(lats) + pad, max(lngs) + pad]])

    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    return m.get_root().render()
