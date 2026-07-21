from __future__ import annotations

import html
import math
from typing import Any

from marketing_diagnosis import ctrip_report_v54 as upstream


COLORS = ("#2fa66a", "#3f8fe8", "#f2a521", "#9368d8", "#ef6a4c", "#2aa8b8")

STYLE = """
<style id='CTRIP_USER_PROFILE_STABLE'>
.ctrip-profile-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:12px}
.ctrip-profile-card{container-type:inline-size;min-width:0;overflow:hidden;padding:14px;border:1px solid #dfe7e4;border-radius:10px;background:#fff}
.ctrip-profile-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:8px}
.ctrip-profile-head h4{margin:0;color:#27343d;font-size:14px;line-height:1.35}
.ctrip-profile-average{flex:0 0 auto;white-space:nowrap;color:#16845b;font-size:11px;font-weight:800}
.ctrip-profile-chart-scroll{max-width:100%;overflow-x:auto;overscroll-behavior-inline:contain;padding-bottom:2px}
.ctrip-profile-chart{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:10px;min-width:0;min-height:174px}
.ctrip-profile-svg{display:block;flex:1 1 180px;width:100%;min-width:170px;max-width:230px;height:auto;overflow:visible}
.ctrip-profile-legend{display:flex;flex:1 1 145px;min-width:130px;flex-direction:column;gap:7px}
.ctrip-profile-legend-row{display:grid;grid-template-columns:8px minmax(0,1fr) auto;align-items:start;gap:6px;color:#53606b;font-size:11px;line-height:1.35}
.ctrip-profile-dot{width:7px;height:7px;margin-top:4px;border-radius:50%;background:var(--profile-color)}
.ctrip-profile-legend-row b{min-width:0;color:#3a4650;font-weight:650;white-space:normal;overflow-wrap:anywhere;word-break:break-word}
.ctrip-profile-legend-row span{color:#495762;font-variant-numeric:tabular-nums;white-space:nowrap}
.ctrip-profile-empty{height:174px;display:flex;align-items:center;justify-content:center;border:1px dashed #dce5e1;border-radius:8px;background:#fafcfb;color:#83909b;font-size:13px}
.ctrip-profile-bottom{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,380px),1fr));gap:12px;margin-top:12px}
.ctrip-profile-city,.ctrip-profile-peak{min-width:0;padding:14px;border:1px solid #dfe7e4;border-radius:10px;background:#fff}
.ctrip-profile-city h4,.ctrip-profile-peak h4{margin:0 0 12px;color:#27343d;font-size:14px}
.ctrip-profile-city-row{display:grid;grid-template-columns:22px minmax(52px,84px) minmax(90px,1fr) 58px;align-items:center;gap:8px;margin:8px 0;font-size:11px}
.ctrip-profile-city-rank{width:18px;height:18px;display:flex;align-items:center;justify-content:center;border-radius:50%;background:var(--profile-color);color:#fff;font-size:10px;font-weight:800}
.ctrip-profile-city-name{min-width:0;color:#3d4a54;white-space:normal;overflow-wrap:anywhere}
.ctrip-profile-city-track{height:7px;overflow:hidden;border-radius:99px;background:#edf2f0}
.ctrip-profile-city-bar{display:block;height:100%;border-radius:inherit;background:var(--profile-color)}
.ctrip-profile-city-value{text-align:right;color:#4e5c66;font-variant-numeric:tabular-nums;white-space:nowrap}
.ctrip-profile-peak-layout{display:grid;grid-template-columns:minmax(105px,118px) minmax(0,1fr);align-items:stretch;gap:12px;min-width:0}
.ctrip-profile-peak-summary{display:flex;min-height:152px;flex-direction:column;align-items:center;justify-content:center;border-radius:9px;background:#f4faf7;text-align:center}
.ctrip-profile-peak-summary small{color:#687780;font-size:11px}
.ctrip-profile-peak-summary strong{margin:7px 0 3px;color:#16845b;font-size:28px;line-height:1}
.ctrip-profile-peak-summary b{color:#16845b;font-size:17px}
.ctrip-profile-hourly-scroll{max-width:100%;overflow-x:auto;overscroll-behavior-inline:contain}
.ctrip-profile-hourly-scroll .ctrip-profile-hourly-svg{display:block;width:100%;min-width:560px;height:auto}
.ctrip-profile-hourly-empty{min-height:152px;display:flex;align-items:center;justify-content:center;border:1px dashed #dce5e1;border-radius:8px;color:#89959e;font-size:12px}
.ctrip-profile-source{margin-top:12px;padding:10px 12px;border:1px solid #d9e6e1;border-radius:9px;background:#f4faf7;color:#315b4c;font-size:12px;overflow-wrap:anywhere}
.ctrip-profile-source b{margin-right:6px}
@container(max-width:430px){
  .ctrip-profile-chart{display:grid;grid-template-columns:1fr;justify-items:center}
  .ctrip-profile-svg{max-width:220px}
  .ctrip-profile-legend{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));width:100%;min-width:0}
  .ctrip-profile-legend-row{grid-template-columns:8px minmax(0,1fr)}
  .ctrip-profile-legend-row span{grid-column:2}
}
@media(max-width:760px){
  .ctrip-profile-grid,.ctrip-profile-bottom{grid-template-columns:1fr}
  .ctrip-profile-peak-layout{grid-template-columns:1fr}
  .ctrip-profile-peak-summary{min-height:92px}
}
@media(max-width:480px){
  .ctrip-profile-legend{display:grid;grid-template-columns:1fr}
  .ctrip-profile-city-row{grid-template-columns:22px minmax(50px,72px) minmax(72px,1fr) 54px}
}
</style>
"""


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(str(value).replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None
    return None if math.isnan(parsed) or math.isinf(parsed) else parsed


def pct(value: Any) -> str:
    parsed = number(value)
    return "—" if parsed is None else f"{parsed:.2f}%"


def _point(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    radians = math.radians(angle)
    return cx + radius * math.cos(radians), cy + radius * math.sin(radians)


def _donut_path(cx: float, cy: float, outer: float, inner: float, start: float, end: float) -> str:
    outer_start = _point(cx, cy, outer, start)
    outer_end = _point(cx, cy, outer, end)
    inner_end = _point(cx, cy, inner, end)
    inner_start = _point(cx, cy, inner, start)
    large = 1 if end - start > 180 else 0
    return (
        f"M {outer_start[0]:.2f} {outer_start[1]:.2f} "
        f"A {outer:.2f} {outer:.2f} 0 {large} 1 {outer_end[0]:.2f} {outer_end[1]:.2f} "
        f"L {inner_end[0]:.2f} {inner_end[1]:.2f} "
        f"A {inner:.2f} {inner:.2f} 0 {large} 0 {inner_start[0]:.2f} {inner_start[1]:.2f} Z"
    )


def donut_svg(entries: list[dict[str, Any]], title: str) -> str:
    visible = [entry for entry in entries if (number(entry.get("rate_pct")) or 0) > 0]
    total = sum(number(entry.get("rate_pct")) or 0 for entry in visible)
    if not visible or total <= 0:
        return ""

    cx, cy, outer, inner = 92.0, 86.0, 61.0, 28.0
    paths: list[str] = []
    labels: list[str] = []
    start = -90.0
    for index, entry in enumerate(visible):
        value = number(entry.get("rate_pct")) or 0
        sweep = value / total * 360.0
        end = start + sweep
        color = COLORS[index % len(COLORS)]
        if len(visible) == 1:
            paths.append(
                f"<circle cx='{cx:g}' cy='{cy:g}' r='{(outer+inner)/2:g}' fill='none' "
                f"stroke='{color}' stroke-width='{outer-inner:g}'/>"
            )
        else:
            paths.append(
                f"<path d='{_donut_path(cx, cy, outer, inner, start, end)}' "
                f"fill='{color}' stroke='#fff' stroke-width='1'/>"
            )

        mid = start + sweep / 2
        if value >= 6:
            tx, ty = _point(cx, cy, (outer + inner) / 2, mid)
            labels.append(
                f"<text x='{tx:.2f}' y='{ty:.2f}' dominant-baseline='middle' text-anchor='middle' "
                f"fill='#fff' font-size='10.5' font-weight='750'>{e(pct(value))}</text>"
            )
        elif 0 < value < 3:
            x1, y1 = _point(cx, cy, outer + 1, mid)
            x2, y2 = _point(cx, cy, outer + 12, mid)
            right = x2 >= cx
            x3 = 184 if right else 3
            anchor = "start" if right else "end"
            text_x = x3 + 3 if right else x3 - 3
            labels.append(
                f"<polyline points='{x1:.2f},{y1:.2f} {x2:.2f},{y2:.2f} {x3:.2f},{y2:.2f}' "
                "fill='none' stroke='#7c888f' stroke-width='1'/>"
                f"<text x='{text_x:.2f}' y='{y2:.2f}' dominant-baseline='middle' text-anchor='{anchor}' "
                f"fill='#495762' font-size='9.5' font-weight='700'>{e(pct(value))}</text>"
            )
        start = end

    return (
        f"<svg class='ctrip-profile-svg' viewBox='0 0 190 172' role='img' aria-label='{e(title)}占比分布'>"
        + "".join(paths)
        + "".join(labels)
        + "</svg>"
    )


def legend(entries: list[dict[str, Any]]) -> str:
    visible = [entry for entry in entries if (number(entry.get("rate_pct")) or 0) > 0]
    return "".join(
        "<div class='ctrip-profile-legend-row' style='--profile-color:"
        + COLORS[index % len(COLORS)]
        + "'><i class='ctrip-profile-dot'></i>"
        + f"<b>{e(entry.get('label'))}</b>"
        + f"<span>{e(pct(entry.get('rate_pct')))}</span></div>"
        for index, entry in enumerate(visible)
    )


def chart_card(title: str, chart: dict[str, Any], average: str | None = None) -> str:
    entries = list(chart.get("entries") or []) if isinstance(chart, dict) else []
    svg = donut_svg(entries, title)
    average_html = f"<span class='ctrip-profile-average'>{e(average)}</span>" if average else ""
    if not svg:
        body = "<div class='ctrip-profile-empty'>待接入</div>"
    else:
        body = (
            "<div class='ctrip-profile-chart-scroll'><div class='ctrip-profile-chart'>"
            f"{svg}<div class='ctrip-profile-legend'>{legend(entries)}</div>"
            "</div></div>"
        )
    return (
        "<section class='ctrip-profile-card'>"
        f"<div class='ctrip-profile-head'><h4>{e(title)}</h4>{average_html}</div>{body}</section>"
    )


def city_card(entries: list[dict[str, Any]]) -> str:
    visible = [
        entry
        for entry in entries
        if (number(entry.get("rate_pct")) or 0) > 0 or (number(entry.get("count")) or 0) > 0
    ][:5]
    if not visible:
        rows = "<div class='ctrip-profile-empty'>待接入</div>"
    else:
        maximum = max(number(entry.get("rate_pct")) or number(entry.get("count")) or 0 for entry in visible) or 1
        rendered = []
        for index, entry in enumerate(visible):
            value = number(entry.get("rate_pct"))
            raw = value if value is not None else number(entry.get("count")) or 0
            width = max(2.0, raw / maximum * 100)
            display = pct(value) if value is not None else f"{raw:g}"
            color = COLORS[index % len(COLORS)]
            rendered.append(
                f"<div class='ctrip-profile-city-row' style='--profile-color:{color}'>"
                f"<span class='ctrip-profile-city-rank'>{index+1}</span>"
                f"<span class='ctrip-profile-city-name'>{e(entry.get('label'))}</span>"
                f"<span class='ctrip-profile-city-track'><i class='ctrip-profile-city-bar' style='width:{width:.2f}%'></i></span>"
                f"<span class='ctrip-profile-city-value'>{e(display)}</span></div>"
            )
        rows = "".join(rendered)
    return f"<section class='ctrip-profile-city'><h4>主要客源城市（Top5）</h4>{rows}</section>"


def _hour(label: Any) -> float:
    text = str(label or "").strip()
    try:
        hour, minute = text.split(":", 1)
        return float(hour) + float(minute) / 60
    except (ValueError, TypeError):
        parsed = number(text)
        return parsed if parsed is not None else 0.0


def hourly_chart(entries: list[dict[str, Any]], peak: dict[str, Any] | None) -> str:
    visible = [entry for entry in entries if (number(entry.get("rate_pct")) or 0) > 0]
    if not visible:
        return "<div class='ctrip-profile-hourly-empty'>小时分布实时字段待接入</div>"

    width, height = 620.0, 168.0
    left, right, top, bottom = 36.0, 12.0, 18.0, 28.0
    chart_w, chart_h = width - left - right, height - top - bottom
    maximum = (max(number(entry.get("rate_pct")) or 0 for entry in visible) or 1) * 1.15
    points: list[tuple[float, float, dict[str, Any]]] = []
    for entry in visible:
        x = left + min(24.0, max(0.0, _hour(entry.get("label")))) / 24.0 * chart_w
        y = top + (1 - (number(entry.get("rate_pct")) or 0) / maximum) * chart_h
        points.append((x, y, entry))
    points.sort(key=lambda item: item[0])
    polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points)
    area = f"{left:.2f},{top+chart_h:.2f} {polyline} {points[-1][0]:.2f},{top+chart_h:.2f}"

    grid = []
    for fraction in (0, .5, 1):
        y = top + (1 - fraction) * chart_h
        grid.append(f"<line x1='{left:g}' y1='{y:.2f}' x2='{left+chart_w:.2f}' y2='{y:.2f}' stroke='#e8eeeb' stroke-width='1'/>")
        grid.append(f"<text x='{left-5:g}' y='{y:.2f}' text-anchor='end' dominant-baseline='middle' fill='#7d8991' font-size='9'>{maximum*fraction:.0f}%</text>")
    x_labels = []
    for hour in (0, 6, 12, 18, 24):
        x = left + hour / 24 * chart_w
        x_labels.append(f"<text x='{x:.2f}' y='{height-7:g}' text-anchor='middle' fill='#7d8991' font-size='9'>{hour:02d}:00</text>")

    peak_label = str((peak or {}).get("label") or "")
    peak_point = (
        min(points, key=lambda item: abs(_hour(item[2].get("label")) - _hour(peak_label)))
        if peak_label
        else max(points, key=lambda item: number(item[2].get("rate_pct")) or 0)
    )
    px, py, pentry = peak_point
    marker = (
        f"<line x1='{px:.2f}' y1='{py:.2f}' x2='{px:.2f}' y2='{top+chart_h:.2f}' stroke='#16845b' stroke-width='1' stroke-dasharray='3 3'/>"
        f"<circle cx='{px:.2f}' cy='{py:.2f}' r='4' fill='#16845b' stroke='#fff' stroke-width='2'/>"
        f"<rect x='{px-22:.2f}' y='{max(1,py-29):.2f}' width='44' height='20' rx='5' fill='#16845b'/>"
        f"<text x='{px:.2f}' y='{max(11,py-19):.2f}' text-anchor='middle' dominant-baseline='middle' fill='#fff' font-size='9.5' font-weight='750'>{e(pentry.get('label'))}</text>"
    )
    svg = (
        f"<svg class='ctrip-profile-hourly-svg' viewBox='0 0 {width:g} {height:g}' role='img' aria-label='主要预订时段小时分布'>"
        + "".join(grid)
        + f"<polygon points='{area}' fill='#dff3e8' opacity='.72'/>"
        + f"<polyline points='{polyline}' fill='none' stroke='#16845b' stroke-width='2.2' stroke-linejoin='round' stroke-linecap='round'/>"
        + "".join(f"<circle cx='{x:.2f}' cy='{y:.2f}' r='2.2' fill='#16845b'/>" for x, y, _ in points)
        + marker
        + "".join(x_labels)
        + "</svg>"
    )
    return f"<div class='ctrip-profile-hourly-scroll'>{svg}</div>"


def peak_card(peak: dict[str, Any] | None, hourly: list[dict[str, Any]]) -> str:
    peak_label = (peak or {}).get("label") or "待接入"
    peak_rate = pct((peak or {}).get("rate_pct"))
    summary = (
        "<div class='ctrip-profile-peak-summary'><small>高峰时段</small>"
        f"<strong>{e(peak_label)}</strong><small>该时段订单占比</small><b>{e(peak_rate)}</b></div>"
    )
    return (
        "<section class='ctrip-profile-peak'><h4>主要预订时段</h4>"
        f"<div class='ctrip-profile-peak-layout'>{summary}{hourly_chart(hourly, peak)}</div></section>"
    )


def card(result: dict[str, Any]) -> str:
    item_spec = upstream.spec(4)
    no, title, _, period, description, source, _ = item_spec
    payload = upstream.item_payload(result, item_spec)
    key, text, css = upstream.status(payload)
    charts = payload.get("charts") if isinstance(payload.get("charts"), dict) else {}
    average_advance = number(payload.get("average_advance_days"))
    average_stay = number(payload.get("average_stay_nights"))

    chart_order = (
        ("gender", "性别", None),
        ("age_group", "年龄段", None),
        ("city_origin", "本地 / 异地", None),
        ("travel_type", "出行目的", None),
        ("travel_time", "工作日 / 周末偏好", None),
        ("consumption_price", "消费价格带", None),
        ("booking_advance_days", "提前预订天数", f"平均提前 {average_advance:g} 天" if average_advance is not None else None),
        ("stay_days", "入住晚数", f"平均入住 {average_stay:g} 晚" if average_stay is not None else None),
    )
    chart_html = "".join(chart_card(label, charts.get(code) or {}, average) for code, label, average in chart_order)
    source_text = payload.get("source") or source
    source_path = payload.get("source_path") or "携程 eBooking -> 数据中心 -> 用户行为"

    return (
        f"<article class='diagnosis-card' data-status='{e(key)}' data-title='{e(title)}' id='rule-{no}'>"
        "<div class='card-top'>"
        f"<div class='rule-no'>{no:02d}</div>"
        f"<div class='card-title'><h3>{e(title)}</h3><p>{e(description)}</p></div>"
        "<div class='card-tags'>"
        f"<div class='title-meta-item title-period'><small>统计周期</small><strong>{e(period)}</strong></div>"
        "<div class='title-meta-item title-score display-only'><small>当前得分</small>"
        f"<div class='title-score-value'><strong>{e(upstream.score_text(item_spec, payload))}</strong>"
        f"<span>满分 {e(upstream.full_text(item_spec, payload))}</span></div></div>"
        f"<span class='status-badge {css}'>{e(text)}</span></div></div>"
        "<div class='result-area'>"
        f"<div class='ctrip-profile-grid'>{chart_html}</div>"
        f"<div class='ctrip-profile-bottom'>{city_card(list(payload.get('city_top5') or []))}"
        f"{peak_card(payload.get('peak_time') if isinstance(payload.get('peak_time'), dict) else None, list(payload.get('hourly_distribution') or []))}</div>"
        f"<div class='ctrip-profile-source'><b>携程数据来源：</b>{e(source_path)}（{e(source_text)}）</div>"
        "</div></article>"
    )


__all__ = ["STYLE", "card", "donut_svg"]
