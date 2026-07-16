from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v23


INFORMATION_STYLE = """
<style>
.info-v24-point{fill:#5b6fd8;stroke:#fff;stroke-width:3;cursor:pointer;transition:r .16s ease,filter .16s ease}
.info-v24-point:hover{r:7;filter:drop-shadow(0 3px 6px rgba(60,77,170,.35))}
.info-v24-tooltip{position:fixed;z-index:9999;display:none;pointer-events:none;min-width:160px;padding:10px 12px;border-radius:9px;background:rgba(31,41,51,.94);color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.18);font-size:12px;line-height:1.55}
.info-v24-tooltip strong{display:block;font-size:14px;margin-bottom:2px}.info-v24-tooltip span{display:block;color:rgba(255,255,255,.76)}
</style>
"""


_INFORMATION_CARD_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-8'>.*?</article>",
    re.DOTALL,
)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").rstrip("%"))
        return None if number != number else number
    except (TypeError, ValueError):
        return None


def _field(item: dict[str, Any], label: str) -> Any:
    for field in item.get("fields") or []:
        if str(field.get("label") or "") == label:
            return field.get("value")
    return None


def _date_parts(value: Any, points: list[dict[str, Any]]) -> tuple[str, str]:
    text = str(value or "")
    if " 至 " in text:
        start, end = text.split(" 至 ", 1)
        return start.strip() or "—", end.strip() or "—"
    if points:
        return str(points[0]["date"]), str(points[-1]["date"])
    fallback = str(_field({}, "") or "—")
    return fallback, fallback


def _information_points(item: dict[str, Any]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for record in item.get("daily_records") or []:
        day = str(record.get("business_date") or record.get("date") or "")[:10]
        value = _number(record.get("content_score") or record.get("information_score"))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) or value is None:
            continue
        rank = record.get("content_score_rank")
        points.append(
            {
                "date": day,
                "value": value,
                "note": f"同行排名 {rank}" if rank not in (None, "") else "暂无同行排名",
            }
        )

    if not points:
        for field in item.get("fields") or []:
            label = str(field.get("label") or "")
            value = _number(field.get("value"))
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", label) and value is not None:
                points.append(
                    {
                        "date": label,
                        "value": value,
                        "note": str(field.get("note") or ""),
                    }
                )

    if not points:
        day = str(_field(item, "统计日期") or "")[:10]
        value = _number(_field(item, "信息分"))
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) and value is not None:
            points.append({"date": day, "value": value, "note": "最新信息分"})

    by_day = {point["date"]: point for point in points}
    return [by_day[day] for day in sorted(by_day)[-30:]]


def _chart_svg(points: list[dict[str, Any]]) -> str:
    if not points:
        return "<div class='hos-v2-empty'>当前统计周期没有有效信息分记录。</div>"

    width, height = 820, 300
    left, right, top, bottom = 68.0, 790.0, 26.0, 245.0
    values = [float(point["value"]) for point in points]
    raw_min, raw_max = min(values), max(values)
    if raw_min == raw_max:
        padding = max(abs(raw_min) * 0.08, 1.0)
        low = max(0.0, raw_min - padding)
        high = raw_max + padding
    else:
        padding = max((raw_max - raw_min) * 0.18, 1.0)
        low = max(0.0, raw_min - padding)
        high = raw_max + padding
    if high <= low:
        high = low + 1.0
    span = high - low

    def x_at(index: int) -> float:
        return left + (right - left) * index / max(1, len(points) - 1)

    def y_at(value: float) -> float:
        return bottom - (value - low) / span * (bottom - top)

    grid: list[str] = []
    for index in range(5):
        ratio = index / 4
        y = bottom - ratio * (bottom - top)
        value = low + ratio * span
        grid.append(
            f"<line class='hos-v2-grid' x1='{left:.1f}' y1='{y:.1f}' x2='{right:.1f}' y2='{y:.1f}'/>"
            f"<text class='hos-v2-axis-label' text-anchor='end' dominant-baseline='middle' x='{left - 10:.1f}' y='{y:.1f}'>{value:.2f}</text>"
        )

    coords = [(x_at(index), y_at(float(point["value"]))) for index, point in enumerate(points)]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f"{left:.1f},{bottom:.1f} {polyline} {right:.1f},{bottom:.1f}"

    labels: list[str] = []
    label_step = max(1, len(points) // 6)
    for index, point in enumerate(points):
        if index in {0, len(points) - 1} or index % label_step == 0:
            x, _ = coords[index]
            labels.append(
                f"<text class='hos-v2-axis-label' text-anchor='middle' x='{x:.1f}' y='{bottom + 25:.1f}'>{reporting_v8._e(point['date'][5:])}</text>"
            )

    circles: list[str] = []
    for index, point in enumerate(points):
        x, y = coords[index]
        circles.append(
            f"<circle class='info-v24-point' cx='{x:.1f}' cy='{y:.1f}' r='5' "
            f"data-date='{reporting_v8._e(point['date'])}' data-value='{float(point['value']):.2f}' data-note='{reporting_v8._e(point['note'])}'>"
            f"<title>{reporting_v8._e(point['date'])}｜信息分 {float(point['value']):.2f}｜{reporting_v8._e(point['note'])}</title></circle>"
        )

    return (
        f"<svg class='hos-v2-svg' viewBox='0 0 {width} {height}' role='img' aria-label='信息分趋势图'>"
        "<defs><linearGradient id='infoAreaGradient' x1='0' y1='0' x2='0' y2='1'><stop offset='0%' stop-color='#7f91eb'/><stop offset='100%' stop-color='#dfe5ff'/></linearGradient></defs>"
        + "".join(grid)
        + f"<line class='hos-v2-axis' x1='{left:.1f}' y1='{top:.1f}' x2='{left:.1f}' y2='{bottom:.1f}'/>"
        + f"<line class='hos-v2-axis' x1='{left:.1f}' y1='{bottom:.1f}' x2='{right:.1f}' y2='{bottom:.1f}'/>"
        + f"<polygon class='hos-v2-area' style='fill:url(#infoAreaGradient)' points='{area}'/>"
        + f"<polyline class='hos-v2-line' points='{polyline}'/>"
        + "".join(circles)
        + "".join(labels)
        + f"<text class='hos-v2-axis-label' x='12' y='{top + 2:.1f}'>信息分</text>"
        + "</svg><div class='info-v24-tooltip' id='info-v24-tooltip'></div>"
    )


def _information_card(item: dict[str, Any]) -> str:
    points = _information_points(item)
    display_range = _field(item, "展示范围")
    start, end = _date_parts(display_range, points)
    valid_days = _field(item, "有效数据天数")
    if valid_days in (None, ""):
        valid_days = len(points) if points else None
    latest = _field(item, "最新信息分")
    if latest in (None, ""):
        latest = points[-1]["value"] if points else _field(item, "信息分")
    average = _field(item, "近30天平均分")
    if average in (None, "") and points:
        average = sum(float(point["value"]) for point in points) / len(points)
    presence = _field(item, "是否有信息分")
    has_score = bool(points) or str(presence or "") == "有" or _number(latest) is not None

    status_key = str(item.get("data_status") or "missing")
    status_text, status_class = reporting_v8.STATUS.get(status_key, (status_key, "neutral"))
    score_class = "ok" if item.get("item_score") is not None else "pending"
    average_text = "—" if _number(average) is None else f"{float(average):.2f}"
    latest_text = "—" if _number(latest) is None else f"{float(latest):.2f}"

    return f"""
<article class='diagnosis-card' data-status='{reporting_v8._e(status_key)}' data-title='信息分数据' id='rule-8'>
  <div class='card-top'>
    <div class='rule-no'>08</div>
    <div class='card-title'><h3>信息分数据</h3><p>判断统计周期内是否存在信息分，并展示最多近30天趋势。</p></div>
    <div class='card-tags'>
      <div class='title-meta-item title-period'><small>统计周期</small><strong>最多近30天</strong></div>
      <div class='title-meta-item title-score {score_class}'><small>当前得分</small><div class='title-score-value'><strong>{reporting_v8._e(reporting_v8._score_text(item))}</strong><span>满分 {reporting_v8._e(reporting_v8._base_text(item))}</span></div></div>
      <span class='status-badge {status_class}'>{reporting_v8._e(status_text)}</span>
    </div>
  </div>
  <div class='result-area'>
    <div class='hos-v2-layout'>
      <div class='hos-v2-chart-card'>
        <div class='hos-v2-chart-head'><div><h4>最多近30天 信息分趋势</h4><p>纵轴展示实际信息分；鼠标悬浮数据点可查看日期和分数。</p></div><span class='hos-v2-axis-note'>平均分：{reporting_v8._e(average_text)}</span></div>
        {_chart_svg(points)}
      </div>
      <div class='hos-v2-stats-card'>
        <h4>统计结果</h4>
        <div class='hos-v2-date-banner'><div class='hos-v2-date-block'><small>起始日期</small><strong>{reporting_v8._e(start)}</strong></div><span class='hos-v2-date-arrow'>→</span><div class='hos-v2-date-block'><small>截止日期</small><strong>{reporting_v8._e(end)}</strong></div></div>
        <div class='hos-v2-stat-grid'>
          <div class='hos-v2-stat hos-v2-presence {'yes' if has_score else 'no'}'><small>是否有信息分</small><strong>{reporting_v8._e('已有数据' if has_score else '暂无数据')}</strong><span>本项仍按原有信息分评分规则计分</span></div>
          <div class='hos-v2-stat'><small>有效数据天数</small><strong>{reporting_v8._e(valid_days if valid_days not in (None, '') else '—')}</strong><span>按业务日期去重后的信息分记录数</span></div>
          <div class='hos-v2-stat'><small>最新信息分</small><strong>{reporting_v8._e(latest_text)}</strong><span>最近一个有信息分日期的数据</span></div>
          <div class='hos-v2-stat'><small>近30天平均分</small><strong>{reporting_v8._e(average_text)}</strong><span>有效日信息分的算术平均值</span></div>
        </div>
      </div>
    </div>
    {reporting_v8._source_box(item)}
    <div class='notice'>{reporting_v8._e(item.get('note') or '信息分展示最多近30天趋势，评分逻辑保持不变。')}</div>
  </div>
</article>
<script>
(function(){{
  document.addEventListener('DOMContentLoaded',function(){{
    const tooltip=document.getElementById('info-v24-tooltip');
    if(!tooltip)return;
    document.querySelectorAll('.info-v24-point').forEach(function(point){{
      function move(event){{tooltip.style.left=(event.clientX+14)+'px';tooltip.style.top=(event.clientY+14)+'px';}}
      point.addEventListener('mouseenter',function(event){{
        tooltip.innerHTML='<strong>'+point.dataset.date+' · 信息分 '+point.dataset.value+'</strong><span>'+(point.dataset.note||'')+'</span>';
        tooltip.style.display='block';move(event);
      }});
      point.addEventListener('mousemove',move);
      point.addEventListener('mouseleave',function(){{tooltip.style.display='none';}});
    }});
  }});
}})();
</script>
"""


def _item_eight(result: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == 8
        ),
        None,
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v23.build_html(result)
    item = _item_eight(result)
    if item:
        html_text = _INFORMATION_CARD_PATTERN.sub(
            lambda _: _information_card(item),
            html_text,
            count=1,
        )
    return html_text.replace("</head>", INFORMATION_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v23.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v23.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "_information_card",
    "_information_points",
    "build_html",
    "build_markdown",
    "write_reports",
]
