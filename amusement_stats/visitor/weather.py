"""Open-Meteo 免 Key 天气，用于游客端温馨提示。"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


def fetch_park_weather(latitude: float = 31.23, longitude: float = 121.47) -> dict | None:
    """
    返回当前天气摘要；失败时返回 None，页面可降级不显示。
    默认坐标可按园区所在地调整。
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,precipitation,rain,weather_code,relative_humidity_2m",
        "timezone": "Asia/Shanghai",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            payload = json.loads(resp.read().decode())
    except (OSError, ValueError):
        return None
    cur = (payload or {}).get("current") or {}
    return {
        "temp_c": cur.get("temperature_2m"),
        "precip_mm": cur.get("precipitation"),
        "rain_mm": cur.get("rain"),
        "code": cur.get("weather_code"),
        "humidity": cur.get("relative_humidity_2m"),
    }


def build_weather_tip(data: dict | None) -> tuple[str, str]:
    """
    返回 (一行摘要, 温馨提示正文)。
    无数据时摘要与提示均为空字符串。
    """
    if not data or data.get("temp_c") is None:
        return "", ""

    temp = float(data["temp_c"])
    rain = float(data.get("rain_mm") or 0)
    precip = float(data.get("precip_mm") or 0)
    code = int(data.get("code") or 0)

    parts = [f"约 {temp:.0f}°C"]
    if rain > 0.2 or precip > 0.3 or code in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}:
        parts.append("有降水")
    line = " · ".join(parts)

    tips: list[str] = []
    if rain > 0.2 or precip > 0.5:
        tips.append("目前可能有降雨，建议优先选择室内或半室内项目，并备好雨具。")
    elif code in {45, 48}:
        tips.append("能见度一般，请注意慢行与脚下安全。")
    if temp >= 33:
        tips.append("气温较高，请注意补水防晒，尽量避免长时间暴晒排队。")
    elif temp <= 5:
        tips.append("气温偏低，请注意保暖。")
    if data.get("humidity") is not None and float(data["humidity"]) >= 85 and temp >= 28:
        tips.append("闷热感较强，可到阴凉或休息区稍作休整。")

    if not tips:
        tips.append("天气适宜游园，仍请以现场广播与工作人员指引为准。")

    return line, " ".join(tips)
