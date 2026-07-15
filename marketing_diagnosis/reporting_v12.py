from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v11


EXTRA_STYLE = """
<style>
.hos-v2-layout{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(360px,.75fr);gap:18px}
.hos-v2-chart-card,.hos-v2-stats-card{border:1px solid #dfe8e4;border-radius:14px;background:#fff;padding:20px;position:relative}
.hos-v2-chart-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:10px}
.hos-v2-chart-head h4,.hos-v2-stats-card h4{margin:0;font-size:17px;color:#26343d}
.hos-v2-chart-head p{margin:5px 0 0;color:var(--muted);font-size:12px}
.hos-v2-axis-note{padding:5px 9px;border-radius:999px;background:#eef4ff;color:#4560b2;font-size:11px;font-weight:800;white-space:nowrap}
.hos-v2-svg{display:block;width:100%;height:auto;min-height:280px;overflow:visible}
.hos-v2-grid{stroke:#e7ecea;stroke-width:1;stroke-dasharray:4 4}
.hos-v2-axis{stroke:#9ba8a3;stroke-width:1.2}
.hos-v2-axis-label{fill:#738078;font-size:11px;font-weight:700}
.hos-v2-line{fill:none;stroke:#5b6fd8;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.hos-v2-area{fill:url(#hosAreaGradient);opacity:.42}
.hos-v2-point{fill:#5b6fd8;stroke:#fff;stroke-width:3;cursor:pointer;transition:r .16s ease,filter .16s ease}
.hos-v2-point:hover{r:7;filter:drop-shadow(0 3px 6px rgba(60,77,170,.35))}
.hos-v2-tooltip{position:fixed;z-index:9999;display:none;pointer-events:none;min-width:160px;padding:10px 12px;border-radius:9px;background:rgba(31,41,51,.94);color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.18);font-size:12px;line-height:1.55}
.hos-v2-tooltip strong{display:block;font-size:14px;margin-bottom:2px}.hos-v2-tooltip span{display:block;color:rgba(255,255,255,.76)}
.hos-v2-date-banner{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:12px;padding:15px;border:1px solid #dce6f6;border-radius:12px;background:linear-gradient(135deg,#f7faff,#eef4ff);margin:12px 0 14px}
.hos-v2-date-block small{display:block;color:#718096;font-size:11px;font-weight:800}.hos-v2-date-block strong{display:block;margin-top:4px;color:#27456f;font-size:17px;white-space:nowrap}
.hos-v2-date-arrow{width:34px;height:34px;display:flex;align-items:center;justify-content:center;border-radius:50%;background:#fff;color:#5b6fd8;font-size:18px;font-weight:900;box-shadow:0 3px 10px rgba(91,111,216,.12)}
.hos-v2-stat-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.hos-v2-stat{padding:13px;border:1px solid #e2eae7;border-radius:11px;background:#f9fbfa;min-height:92px}
.hos-v2-stat small{display:block;color:var(--muted);font-size:11px;font-weight:800}.hos-v2-stat strong{display:block;margin-top:7px;font-size:21px;color:#26343d;line-height:1.25}.hos-v2-stat span{display:block;margin-top:5px;color:var(--muted);font-size:10px;line-height:1.4}
.hos-v2-presence.yes{background:#edf8f3;border-color:#cce9db}.hos-v2-presence.yes strong{color:#16845b}.hos-v2-presence.no{background:#fff4f2;border-color:#f0d4cf}.hos-v2-presence.no strong{color:#c43e38}
.hos-v2-empty{height:260px;display:flex;align-items:center;justify-content:center;border:1px dashed #d9e2df;border-radius:12px;background:#fafcfb;color:var(--muted)}
@media(max-width:1050px){.hos-v2-layout{grid-template-columns:1fr}}
@media(max-width:620px){.hos-v2-stat-grid{grid-template-columns:1fr}.hos-v2-date-block strong{font-size:14px}.hos-v2-chart-head{display:block}.hos-v2-axis-note{display:inline-flex;margin-top:8px}}
</style>
"""


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _n(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        number = float(value)
        return None if number != number else number
    except (TypeError, ValueError):
        return None


def _field(item: dict[str, Any], label: str) -> dict[str, Any]:
    return next(
        (field for field in item.get("fields") or [] if field.get("label") == label),
        {},
    )


def _score_text(item: dict[str, Any]) -> str:
    score = item.get("item_score")
    return "待计算" if score is None else f"{float(score):g}分"


def _source_box(item: dict[str, Any]) -> str:
    fields = "、".join(str(value) for value in item.get("source_fields") or []) or "待补充"
    return (
        "<div class='field-standard-note'><b>数据库来源：</b>"
        f"<code>{_e(item.get('source_table') or '待确认')}</code><br>"
        f"<b>对应字段：</b>{_e(fields)}</div>"
    )


def _date_parts(value: Any) -> tuple[str, str]:
    text = str(value or "")
    if " 至 " in text:
        start, end = text.split(" 至 ", 1)
        return start.strip() or "—", end.strip() or "—"
    return (text or "—", text or "—")


def _daily_points(item: dict[str, Any]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for field in item.get("fields") or []:
        label = str(field.get("label") or "")
        value = _n(field.get("value"))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", label) or value is None:
            continue
        points.append(
            {
                "date": label,
                "value": value,
                "note": str(field.get("note") or ""),
            }
        )
    return points[-30:]


def _chart_svg(points: list[dict[str, Any]]) -> str:
    if not points:
        return "<div class='hos-v2-empty'>当前统计周期没有有效 HOS 评分记录。</div>"

    width, height = 820, 300
    left, right, top, bottom = 68.0, 790.0, 26.0, 245.0
    values = [float(point["value"]) for point in points]
    raw_min, raw_max = min(values), max(values)
    if raw_min == raw_max:
        padding = max(abs(raw_min) * 0.08, 0.5)
        low = max(0.0, raw_min - padding)
        high = raw_max + padding
    else:
        padding = max((raw_max - raw_min) * 0.18, 0.25)
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
                f"<text class='hos-v2-axis-label' text-anchor='middle' x='{x:.1f}' y='{bottom + 25:.1f}'>{_e(point['date'][5:])}</text>"
            )

    circles: list[str] = []
    for index, point in enumerate(points):
        x, y = coords[index]
        circles.append(
            f"<circle class='hos-v2-point' cx='{x:.1f}' cy='{y:.1f}' r='5' "
            f"data-date='{_e(point['date'])}' data-value='{float(point['value']):.2f}' data-note='{_e(point['note'])}'>"
            f"<title>{_e(point['date'])}｜HOS {float(point['value']):.2f}｜{_e(point['note'])}</title></circle>"
        )

    return (
        f"<svg class='hos-v2-svg' viewBox='0 0 {width} {height}' role='img' aria-label='HOS得分趋势图'>"
        "<defs><linearGradient id='hosAreaGradient' x1='0' y1='0' x2='0' y2='1'><stop offset='0%' stop-color='#7f91eb'/><stop offset='100%' stop-color='#dfe5ff'/></linearGradient></defs>"
        + "".join(grid)
        + f"<line class='hos-v2-axis' x1='{left:.1f}' y1='{top:.1f}' x2='{left:.1f}' y2='{bottom:.1f}'/>"
        + f"<line class='hos-v2-axis' x1='{left:.1f}' y1='{bottom:.1f}' x2='{right:.1f}' y2='{bottom:.1f}'/>"
        + f"<polygon class='hos-v2-area' points='{area}'/>"
        + f"<polyline class='hos-v2-line' points='{polyline}'/>"
        + "".join(circles)
        + "".join(labels)
        + f"<text class='hos-v2-axis-label' x='12' y='{top + 2:.1f}'>HOS分</text>"
        + "</svg><div class='hos-v2-tooltip' id='hos-v2-tooltip'></div>"
    )


def _hos_card(item: dict[str, Any]) -> str:
    points = _daily_points(item)
    display_range = _field(item, "展示范围").get("value")
    start, end = _date_parts(display_range)
    presence = _field(item, "是否有HOS评分").get("value")
    valid_days = _field(item, "有效评分天数").get("value")
    latest_score = _field(item, "最新HOS分").get("value")
    average = _field(item, "近30天平均分").get("value")
    latest_rank = _field(item, "最新同行排名").get("value")
    has_score = str(presence or "") == "有"
    status_text = "已形成结果" if has_score else ("真实为0" if presence == "无" else "数据未取到")
    status_class = "ok" if has_score else ("disabled" if presence == "无" else "pending")
    score_class = "ok" if item.get("item_score") is not None else "pending"

    return f"""
<article class='diagnosis-card' data-status='{_e(item.get('data_status'))}' data-title='HOS 历史得分' id='rule-6'>
  <div class='card-top'>
    <div class='rule-no'>06</div>
    <div class='card-title'><h3>HOS 历史得分</h3><p>判断统计周期内是否存在 HOS 评分，并展示评分趋势与同行排名。</p></div>
    <div class='card-tags'>
      <div class='title-meta-item title-period'><small>统计周期</small><strong>最多近30天</strong></div>
      <div class='title-meta-item title-score {score_class}'><small>当前得分</small><div class='title-score-value'><strong>{_e(_score_text(item))}</strong><span>满分 3分</span></div></div>
      <span class='status-badge {status_class}'>{_e(status_text)}</span>
    </div>
  </div>
  <div class='result-area'>
    <div class='hos-v2-layout'>
      <div class='hos-v2-chart-card'>
        <div class='hos-v2-chart-head'><div><h4>最多近30天 HOS 趋势</h4><p>纵轴展示实际 HOS 分值；鼠标悬浮数据点可查看日期、分数和同行排名。</p></div><span class='hos-v2-axis-note'>平均分：{_e('—' if average in (None, '') else f'{float(average):.2f}')}</span></div>
        {_chart_svg(points)}
      </div>
      <div class='hos-v2-stats-card'>
        <h4>统计结果</h4>
        <div class='hos-v2-date-banner'><div class='hos-v2-date-block'><small>起始日期</small><strong>{_e(start)}</strong></div><span class='hos-v2-date-arrow'>→</span><div class='hos-v2-date-block'><small>截止日期</small><strong>{_e(end)}</strong></div></div>
        <div class='hos-v2-stat-grid'>
          <div class='hos-v2-stat hos-v2-presence {'yes' if has_score else 'no'}'><small>是否有 HOS 评分</small><strong>{_e('已有评分' if has_score else ('暂无评分' if presence == '无' else '未取到'))}</strong><span>本项仅按是否存在有效评分记录计分</span></div>
          <div class='hos-v2-stat'><small>有效评分天数</small><strong>{_e(valid_days if valid_days not in (None, '') else '—')}</strong><span>按业务日期去重后的评分记录数</span></div>
          <div class='hos-v2-stat'><small>最新 HOS 分</small><strong>{_e('—' if latest_score in (None, '') else f'{float(latest_score):.2f}')}</strong><span>最近一个有评分日期的数据</span></div>
          <div class='hos-v2-stat'><small>最新同行排名</small><strong>{_e(latest_rank if latest_rank not in (None, '') else '—')}</strong><span>仅展示，不参与本项评分</span></div>
        </div>
      </div>
    </div>
    {_source_box(item)}
    <div class='notice'>{_e(item.get('note') or '')}</div>
  </div>
</article>
<script>
(function(){{
  document.addEventListener('DOMContentLoaded',function(){{
    const tooltip=document.getElementById('hos-v2-tooltip');
    if(!tooltip)return;
    document.querySelectorAll('.hos-v2-point').forEach(function(point){{
      function move(event){{tooltip.style.left=(event.clientX+14)+'px';tooltip.style.top=(event.clientY+14)+'px';}}
      point.addEventListener('mouseenter',function(event){{
        tooltip.innerHTML='<strong>'+point.dataset.date+' · HOS '+point.dataset.value+'</strong><span>'+(point.dataset.note||'暂无同行排名')+'</span>';
        tooltip.style.display='block';move(event);
      }});
      point.addEventListener('mousemove',move);
      point.addEventListener('mouseleave',function(){{tooltip.style.display='none';}});
    }});
  }});
}})();
</script>
"""


def _replace_hos_card(html_text: str, result: dict[str, Any]) -> str:
    visual = result.get("visual_diagnosis") or {}
    item = next(
        (
            value
            for value in visual.get("items") or []
            if int(value.get("standard_item_id") or 0) == 6
        ),
        None,
    )
    if not item:
        return html_text
    pattern = re.compile(
        r"<article class='diagnosis-card'[^>]*id='rule-6'>.*?</article>",
        re.DOTALL,
    )
    return pattern.sub(lambda _: _hos_card(item), html_text, count=1)


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v11.build_html(result)
    html_text = html_text.replace("</head>", EXTRA_STYLE + "</head>", 1)
    return _replace_hos_card(html_text, result)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v11.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v11.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = ["build_html", "build_markdown", "write_reports"]
