from __future__ import annotations

import math
from typing import Any

from marketing_diagnosis import ctrip_reputation_report as report
from marketing_diagnosis import ctrip_report_v54 as upstream

RADAR_STYLE = """
<style id='CTRIP_REPUTATION_RADAR_V2'>
.rep-radar{margin-top:12px;padding:10px 12px 8px;border:1px solid #edf2f0;border-radius:12px;background:#fbfdfc}
.rep-radar svg{display:block;width:100%;max-width:260px;height:auto;margin:0 auto;overflow:visible}
.rep-radar .radar-grid{fill:none;stroke:#dfe9e5;stroke-width:1}
.rep-radar .radar-grid.inner{stroke:#eaf0ed}
.rep-radar .radar-axis{stroke:#e3ebe8;stroke-width:1}
.rep-radar .radar-area{stroke-width:2;stroke-linejoin:round}
.rep-radar .radar-point{stroke:#fff;stroke-width:2}
.rep-radar .radar-label{fill:#687780;font-size:10px;font-weight:700}
.rep-radar .radar-value{font-size:11px;font-weight:850}
.rep-radar .radar-average-label{fill:#8a969e;font-size:9px}
.rep-radar .radar-average-value{fill:#26343d;font-size:18px;font-weight:900}
.rep-radar .radar-empty-title{fill:#64717b;font-size:12px;font-weight:850}
.rep-radar .radar-empty-note{fill:#96a1a8;font-size:10px}
@media(max-width:680px){.rep-radar svg{max-width:235px}}
</style>
"""

PALETTE = {
    "携程": ("#2fa66a", "rgba(47,166,106,.16)"),
    "去哪儿": ("#3f8fe8", "rgba(63,143,232,.16)"),
    "同程旅行": ("#f2a521", "rgba(242,165,33,.16)"),
    "智行": ("#9368d8", "rgba(147,104,216,.16)"),
}


def _number(value: Any) -> float | None:
    return upstream.number(value)


def _display(value: float | None) -> str:
    return "—" if value is None else f"{value:g}"


def _dimensions(entry: dict[str, Any]) -> tuple[tuple[str, str, int], ...]:
    platform_key = str(entry.get("platform_key") or "").lower()
    platform_name = str(entry.get("platform_name") or "")
    if platform_key == "qunar" or platform_name == "去哪儿":
        return (
            ("风格", "style_score", -90),
            ("服务", "service_score", 0),
            ("卫生", "hygiene_score", 90),
            ("安全", "safety_score", 180),
        )
    return (
        ("环境", "environment_score", -90),
        ("服务", "service_score", 0),
        ("卫生", "hygiene_score", 90),
        ("设施", "facility_score", 180),
    )


def _point(cx: float, cy: float, radius: float, angle: float, score: float) -> tuple[float, float]:
    radian = math.radians(angle)
    distance = radius * min(5.0, max(0.0, score)) / 5.0
    return cx + math.cos(radian) * distance, cy + math.sin(radian) * distance


def _rounded_ring(cx: float, cy: float, radius: float) -> str:
    return (
        f"M {cx:.1f},{cy-radius:.1f} "
        f"Q {cx+radius:.1f},{cy-radius:.1f} {cx+radius:.1f},{cy:.1f} "
        f"Q {cx+radius:.1f},{cy+radius:.1f} {cx:.1f},{cy+radius:.1f} "
        f"Q {cx-radius:.1f},{cy+radius:.1f} {cx-radius:.1f},{cy:.1f} "
        f"Q {cx-radius:.1f},{cy-radius:.1f} {cx:.1f},{cy-radius:.1f} Z"
    )


def _smooth_path(points: list[tuple[float, float]]) -> str:
    midpoints = [
        (
            (points[index][0] + points[(index + 1) % len(points)][0]) / 2,
            (points[index][1] + points[(index + 1) % len(points)][1]) / 2,
        )
        for index in range(len(points))
    ]
    parts = [f"M {midpoints[-1][0]:.1f},{midpoints[-1][1]:.1f}"]
    for index, point in enumerate(points):
        parts.append(
            f"Q {point[0]:.1f},{point[1]:.1f} "
            f"{midpoints[index][0]:.1f},{midpoints[index][1]:.1f}"
        )
    parts.append("Z")
    return " ".join(parts)


def radar_chart(entry: dict[str, Any]) -> str:
    dimensions = _dimensions(entry)
    values = {key: _number(entry.get(key)) for _, key, _ in dimensions}
    valid = [value for value in values.values() if value is not None]
    name = str(entry.get("platform_name") or "平台")
    stroke, fill = PALETTE.get(name, ("#2fa66a", "rgba(47,166,106,.16)"))

    cx, cy, radius = 130.0, 82.0, 48.0
    label_positions = (
        (130, 13, "middle"),
        (252, 86, "end"),
        (130, 166, "middle"),
        (8, 86, "start"),
    )
    labels = "".join(
        f"<text x='{x}' y='{y}' text-anchor='{anchor}' class='radar-label'>{upstream.e(label)} "
        f"<tspan class='radar-value' fill='{stroke}'>{upstream.e(_display(values[key]))}</tspan></text>"
        for (label, key, _), (x, y, anchor) in zip(dimensions, label_positions)
    )

    grid = (
        f"<path d='{_rounded_ring(cx, cy, radius)}' class='radar-grid'/>"
        f"<path d='{_rounded_ring(cx, cy, radius * .67)}' class='radar-grid inner'/>"
        f"<path d='{_rounded_ring(cx, cy, radius * .34)}' class='radar-grid inner'/>"
        f"<line x1='{cx}' y1='{cy}' x2='{cx}' y2='{cy-radius}' class='radar-axis'/>"
        f"<line x1='{cx}' y1='{cy}' x2='{cx+radius}' y2='{cy}' class='radar-axis'/>"
        f"<line x1='{cx}' y1='{cy}' x2='{cx}' y2='{cy+radius}' class='radar-axis'/>"
        f"<line x1='{cx}' y1='{cy}' x2='{cx-radius}' y2='{cy}' class='radar-axis'/>"
    )

    if len(valid) < 4:
        content = (
            grid
            + labels
            + f"<circle cx='{cx}' cy='{cy}' r='27' fill='#fff' stroke='#e2ebe7'/>"
            + f"<text x='{cx}' y='{cy-2}' text-anchor='middle' class='radar-empty-title'>数据待补</text>"
            + f"<text x='{cx}' y='{cy+13}' text-anchor='middle' class='radar-empty-note'>{len(valid)}/4 维已接入</text>"
        )
    else:
        points = [
            _point(cx, cy, radius, angle, float(values[key] or 0))
            for _, key, angle in dimensions
        ]
        average = sum(valid) / len(valid)
        dots = "".join(
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='{stroke}' class='radar-point'/>"
            for x, y in points
        )
        content = (
            grid
            + labels
            + f"<path d='{_smooth_path(points)}' fill='{fill}' stroke='{stroke}' class='radar-area'/>"
            + dots
            + f"<circle cx='{cx}' cy='{cy}' r='24' fill='#fff' stroke='{stroke}' stroke-opacity='.25'/>"
            + f"<text x='{cx}' y='{cy-4}' text-anchor='middle' class='radar-average-value'>{average:.2f}</text>"
            + f"<text x='{cx}' y='{cy+11}' text-anchor='middle' class='radar-average-label'>维度均分</text>"
        )

    aria_dimensions = "、".join(label for label, _, _ in dimensions)
    return (
        "<div class='rep-radar'>"
        f"<svg viewBox='0 0 260 174' role='img' aria-label='{upstream.e(aria_dimensions)}雷达图'>"
        + content
        + "</svg></div>"
    )


report._radar_chart = radar_chart
report.STYLE = report.STYLE + RADAR_STYLE

__all__ = ["RADAR_STYLE", "radar_chart"]
