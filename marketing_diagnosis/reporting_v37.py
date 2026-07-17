from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v36


PERFORMANCE_TREND_STYLE = """
<style>
.performance-trend-layout-v54{display:grid;grid-template-columns:minmax(520px,1.08fr) minmax(590px,.92fr);gap:24px;align-items:start}
.performance-chart-v54,.performance-detail-v54{min-width:0}
.performance-chart-head-v54,.performance-detail-head-v54{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin:0 0 14px}
.performance-chart-head-v54 h4,.performance-detail-head-v54 h4{margin:0;color:#26343d;font-size:18px}
.performance-chart-head-v54 p{margin:5px 0 0;color:var(--muted);font-size:12px;line-height:1.5}
.performance-selector-v54{min-width:245px}
.performance-selector-v54 label{display:block;margin:0 0 6px;color:#596773;font-size:11px;font-weight:800}
.performance-select-v54{box-sizing:border-box;width:100%;height:44px;padding:0 42px 0 14px;border:1px solid #cfd9d5;border-radius:13px;background:#fff;color:#26343d;font:inherit;font-weight:800;cursor:pointer}
.performance-selected-v54{font-weight:900;color:#26343d}
.performance-legend-v54{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin:0 0 10px;color:#34424b;font-size:12px;font-weight:800}
.performance-legend-v54 span{display:inline-flex;align-items:center;gap:7px}
.performance-legend-line-v54{display:inline-block;width:28px;height:0;border-top:3px solid #258cf4;border-radius:999px}
.performance-legend-line-v54.previous{border-top-color:#f28b2d;border-top-style:dashed}
.performance-legend-line-v54.yoy{border-top-color:#52b96f}
.performance-svg-wrap-v54{width:100%;overflow:hidden}
.performance-svg-v54{display:block;width:100%;height:auto;min-height:340px;overflow:visible}
.performance-grid-v54{stroke:#e4e9e7;stroke-width:1}
.performance-zero-v54{stroke:#9ba6a2;stroke-width:1;stroke-dasharray:4 5}
.performance-axis-label-v54{fill:#7a8681;font-size:11px}
.performance-value-label-v54{fill:#2e3940;font-size:11px;font-weight:800}
.performance-current-line-v54{fill:none;stroke:#258cf4;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.performance-previous-line-v54{fill:none;stroke:#f28b2d;stroke-width:2.5;stroke-dasharray:8 7;stroke-linecap:round;stroke-linejoin:round}
.performance-yoy-line-v54{fill:none;stroke:#52b96f;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.performance-current-point-v54{fill:#258cf4}.performance-previous-point-v54{fill:#fff;stroke:#f28b2d;stroke-width:2}.performance-yoy-point-v54{fill:#52b96f}
.performance-detail-table-v54{width:100%;border-collapse:collapse;table-layout:fixed;background:#fff}
.performance-detail-table-v54 th,.performance-detail-table-v54 td{padding:16px 9px;border-bottom:1px solid #e2e7e5;text-align:center;vertical-align:middle}
.performance-detail-table-v54 th{color:#7a817e;font-size:12px;font-weight:800;line-height:1.35;background:#fff}
.performance-detail-table-v54 th:first-child,.performance-detail-table-v54 td:first-child{width:155px;text-align:left;padding-left:12px}
.performance-detail-table-v54 th strong{display:block;color:#747b78;font-size:15px;line-height:1.25}
.performance-detail-table-v54 th span{display:block;margin-top:5px;color:#8a918e;font-size:11px;font-weight:700}
.performance-detail-table-v54 th em{display:block;margin-top:3px;color:#8a918e;font-size:11px;font-style:normal;font-weight:700}
.performance-date-v54{color:#27333b;font-size:13px;font-weight:800;line-height:1.55;overflow-wrap:anywhere}
.performance-pair-v54{display:flex;align-items:center;justify-content:center;gap:5px;color:#202b31;white-space:nowrap}
.performance-pair-v54 strong{font-size:15px;line-height:1.25}.performance-pair-v54 span{color:#8a9490;font-size:14px}
.performance-yoy-value-v54{display:block;margin-top:7px;color:#27333b;font-size:13px;font-weight:800;white-space:nowrap}
.performance-yoy-value-v54.up{color:#18865d}.performance-yoy-value-v54.down{color:#b65343}
.performance-empty-v54{padding:50px 20px;border:1px dashed #d8e1de;border-radius:12px;background:#fafcfb;color:var(--muted);text-align:center}
@media(max-width:1180px){.performance-trend-layout-v54{grid-template-columns:1fr}.performance-detail-table-v54 th:first-child,.performance-detail-table-v54 td:first-child{width:170px}}
@media(max-width:680px){.performance-chart-head-v54{display:block}.performance-selector-v54{width:100%;margin-top:12px}.performance-detail-v54{overflow-x:auto}.performance-detail-table-v54{min-width:760px}}
</style>
"""

_ITEM_ONE_PATTERN = re.compile(
    r"<article\b[^>]*\bid=['\"]rule-1['\"][^>]*>.*?</article>",
    re.DOTALL | re.IGNORECASE,
)

_TABLE_METRICS = (
    ("adr", "ADR"),
    ("occupancy", "出租率"),
    ("revpar", "RevPAR"),
    ("revenue", "房费（元）"),
)
_CHART_METRICS = (
    ("revenue", "房费"),
    ("adr", "ADR"),
    ("occupancy", "出租率"),
    ("revpar", "RevPAR"),
)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _metric(period: dict[str, Any], key: str) -> dict[str, Any]:
    return next(
        (
            metric
            for metric in period.get("metrics") or []
            if str(metric.get("key") or "") == key
        ),
        {},
    )


def _format_metric(key: str, value: Any) -> str:
    number = _number(value)
    if number is None:
        return "—"
    if key == "occupancy":
        if abs(number) <= 1:
            number *= 100
        return f"{number:.2f}%"
    return f"{number:,.2f}"


def _format_yoy(value: Any) -> tuple[str, str]:
    number = _number(value)
    if number is None:
        return "—", ""
    percent = number * 100
    if percent > 0:
        return f"↑ +{percent:.2f}%", "up"
    if percent < 0:
        return f"↓ {percent:.2f}%", "down"
    return "→ 0.00%", ""


def _header_cell(label: str) -> str:
    return (
        "<th>"
        f"<strong>{reporting_v8._e(label)}</strong>"
        "<span>本期 / 去年同期</span>"
        "<em>YOY</em>"
        "</th>"
    )


def _detail_table(periods: list[dict[str, Any]]) -> str:
    headers = "<th><strong>日期范围</strong></th>" + "".join(
        _header_cell(label) for _, label in _TABLE_METRICS
    )
    rows: list[str] = []
    for period in periods:
        cells = [
            "<td>"
            f"<div class='performance-date-v54' title='去年同期：{reporting_v8._e(period.get('previous_range') or '')}'>"
            f"{reporting_v8._e(period.get('current_range') or '—')}"
            "</div></td>"
        ]
        for key, _ in _TABLE_METRICS:
            metric = _metric(period, key)
            yoy_text, yoy_class = _format_yoy(metric.get("yoy"))
            cells.append(
                "<td>"
                "<div class='performance-pair-v54'>"
                f"<strong>{reporting_v8._e(_format_metric(key, metric.get('current')))}</strong>"
                "<span>/</span>"
                f"<strong>{reporting_v8._e(_format_metric(key, metric.get('previous')))}</strong>"
                "</div>"
                f"<span class='performance-yoy-value-v54 {yoy_class}'>{reporting_v8._e(yoy_text)}</span>"
                "</td>"
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    if not rows:
        rows.append("<tr><td colspan='5'><div class='performance-empty-v54'>当前没有可展示的总营业指标趋势数据。</div></td></tr>")

    return (
        "<table class='performance-detail-table-v54'><thead><tr>"
        + headers
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _performance_card(item: dict[str, Any]) -> str:
    periods = list(item.get("trend_periods") or [])
    status_key = str(item.get("data_status") or "missing")
    status_text, status_class = reporting_v8.STATUS.get(status_key, (status_key, "neutral"))
    score_class = "ok" if item.get("item_score") is not None else "pending"
    options = "".join(
        f"<option value='{reporting_v8._e(key)}'>{reporting_v8._e(label)}</option>"
        for key, label in _CHART_METRICS
    )

    return (
        f"<article class='diagnosis-card performance-card-v54' data-status='{reporting_v8._e(status_key)}' "
        f"data-title='{reporting_v8._e(item.get('item_name'))}' id='rule-1'>"
        "<div class='card-top'><div class='rule-no'>01</div>"
        "<div class='card-title'><h3>月度经营趋势 YOY</h3>"
        "<p>指标直接读取总营业指标；左侧下拉框只切换折线图，右侧固定展示全部经营数据。</p></div>"
        "<div class='card-tags'>"
        "<div class='title-meta-item title-period'><small>统计周期</small><strong>近三个月</strong></div>"
        f"<div class='title-meta-item title-score {score_class}'><small>当前得分</small>"
        f"<div class='title-score-value'><strong>{reporting_v8._e(reporting_v8._score_text(item))}</strong>"
        f"<span>满分 {reporting_v8._e(reporting_v8._base_text(item))}</span></div></div>"
        f"<span class='status-badge {status_class}'>{reporting_v8._e(status_text)}</span></div></div>"
        "<div class='result-area'>"
        "<div class='performance-trend-layout-v54'>"
        "<section class='performance-chart-v54'>"
        "<div class='performance-chart-head-v54'><div>"
        "<h4>指标：<span class='performance-selected-v54'>房费</span></h4>"
        "<p>蓝线为本期，橙色虚线为去年同期，绿色为 YOY；YOY 使用右侧百分比轴。</p>"
        "</div><div class='performance-selector-v54'><label>经营指标</label>"
        f"<select class='performance-select-v54'>{options}</select></div></div>"
        "<div class='performance-legend-v54'>"
        "<span><i class='performance-legend-line-v54'></i>本期</span>"
        "<span><i class='performance-legend-line-v54 previous'></i>去年同期</span>"
        "<span><i class='performance-legend-line-v54 yoy'></i>YOY</span>"
        "</div>"
        "<div class='performance-svg-wrap-v54'><svg class='performance-svg-v54' viewBox='0 0 720 370' role='img' aria-label='经营指标同比趋势图'></svg></div>"
        f"<script type='application/json' class='performance-data-v54'>{_safe_json(periods)}</script>"
        "</section>"
        "<section class='performance-detail-v54'>"
        "<div class='performance-detail-head-v54'><h4>经营数据明细</h4></div>"
        + _detail_table(periods)
        + "</section></div></div></article>"
    )


def _script() -> str:
    return r"""
<script>
(function(){
  if(window.__s14PerformanceTrendV54Bound) return;
  window.__s14PerformanceTrendV54Bound=true;
  const NS='http://www.w3.org/2000/svg';
  const labels={revenue:'房费',adr:'ADR',occupancy:'出租率',revpar:'RevPAR'};
  const number=(value)=>{
    if(value===null||value===undefined||value==='') return null;
    const parsed=Number(String(value).replace(/,/g,'').replace(/%$/,''));
    return Number.isFinite(parsed)?parsed:null;
  };
  const normalized=(key,value)=>{
    const parsed=number(value);
    if(parsed===null) return null;
    return key==='occupancy'&&Math.abs(parsed)<=1?parsed*100:parsed;
  };
  const compact=(value)=>{
    if(value===null||!Number.isFinite(value)) return '—';
    const absolute=Math.abs(value);
    if(absolute>=100000000) return (value/100000000).toFixed(1)+'亿';
    if(absolute>=10000) return (value/10000).toFixed(1)+'万';
    if(absolute>=1000) return (value/1000).toFixed(1)+'k';
    return value.toFixed(2).replace(/\.00$/,'');
  };
  const metricText=(key,value)=>{
    const parsed=normalized(key,value);
    if(parsed===null) return '—';
    if(key==='occupancy') return parsed.toFixed(2)+'%';
    return parsed.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});
  };
  const yoyText=(value)=>{
    const parsed=number(value);
    if(parsed===null) return '—';
    const percent=parsed*100;
    return (percent>0?'+':'')+percent.toFixed(2)+'%';
  };
  const pathFor=(values,xAt,yAt)=>{
    let path='';
    let active=false;
    values.forEach((value,index)=>{
      if(value===null){active=false;return;}
      const command=active?'L':'M';
      path+=command+xAt(index).toFixed(1)+' '+yAt(value).toFixed(1)+' ';
      active=true;
    });
    return path.trim();
  };
  const escapeXml=(value)=>String(value||'').replace(/[&<>"']/g,(char)=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[char]));
  const render=(card)=>{
    const select=card.querySelector('.performance-select-v54');
    const selected=card.querySelector('.performance-selected-v54');
    const svg=card.querySelector('.performance-svg-v54');
    const dataNode=card.querySelector('.performance-data-v54');
    if(!select||!svg||!dataNode) return;
    let periods=[];
    try{periods=JSON.parse(dataNode.textContent||'[]');}catch(_){periods=[];}
    const key=select.value||'revenue';
    if(selected) selected.textContent=labels[key]||key;
    if(!periods.length){svg.innerHTML='<text x="360" y="185" text-anchor="middle" class="performance-axis-label-v54">当前没有可展示的总营业指标趋势数据</text>';return;}
    const valuesFor=(name)=>periods.map((period)=>{
      const metric=(period.metrics||[]).find((item)=>String(item.key||'')===key)||{};
      return name==='yoy'?number(metric.yoy):normalized(key,metric[name]);
    });
    const current=valuesFor('current');
    const previous=valuesFor('previous');
    const yoy=valuesFor('yoy');
    const leftValues=current.concat(previous).filter((value)=>value!==null);
    let leftMin=leftValues.length?Math.min(...leftValues):0;
    let leftMax=leftValues.length?Math.max(...leftValues):1;
    if(leftMin===leftMax){const pad=Math.max(Math.abs(leftMin)*.08,1);leftMin-=pad;leftMax+=pad;}
    else{const pad=(leftMax-leftMin)*.14;leftMin-=pad;leftMax+=pad;}
    if(key!=='revenue') leftMin=Math.max(0,leftMin);
    const yoyValues=yoy.filter((value)=>value!==null);
    const yoySpan=Math.max(.05,...yoyValues.map((value)=>Math.abs(value)))*1.25;
    const left=72,right=650,top=42,bottom=278;
    const xAt=(index)=>left+(right-left)*index/Math.max(1,periods.length-1);
    const yLeft=(value)=>bottom-(value-leftMin)/(leftMax-leftMin)*(bottom-top);
    const yYoy=(value)=>bottom-(value+yoySpan)/(2*yoySpan)*(bottom-top);
    let html='';
    for(let index=0;index<5;index++){
      const ratio=index/4;
      const y=bottom-ratio*(bottom-top);
      const leftValue=leftMin+ratio*(leftMax-leftMin);
      const rightValue=-yoySpan+ratio*(2*yoySpan);
      html+='<line class="performance-grid-v54" x1="'+left+'" y1="'+y.toFixed(1)+'" x2="'+right+'" y2="'+y.toFixed(1)+'"></line>';
      html+='<text class="performance-axis-label-v54" x="'+(left-10)+'" y="'+(y+4).toFixed(1)+'" text-anchor="end">'+escapeXml(key==='occupancy'?leftValue.toFixed(1)+'%':compact(leftValue))+'</text>';
      html+='<text class="performance-axis-label-v54" x="'+(right+10)+'" y="'+(y+4).toFixed(1)+'" text-anchor="start">'+escapeXml((rightValue*100).toFixed(0)+'%')+'</text>';
    }
    const zeroY=yYoy(0);
    html+='<line class="performance-zero-v54" x1="'+left+'" y1="'+zeroY.toFixed(1)+'" x2="'+right+'" y2="'+zeroY.toFixed(1)+'"></line>';
    const currentPath=pathFor(current,xAt,yLeft);
    const previousPath=pathFor(previous,xAt,yLeft);
    const yoyPath=pathFor(yoy,xAt,yYoy);
    if(currentPath) html+='<path class="performance-current-line-v54" d="'+currentPath+'"></path>';
    if(previousPath) html+='<path class="performance-previous-line-v54" d="'+previousPath+'"></path>';
    if(yoyPath) html+='<path class="performance-yoy-line-v54" d="'+yoyPath+'"></path>';
    periods.forEach((period,index)=>{
      const x=xAt(index);
      const ranges=String(period.current_range||'—').split('—');
      html+='<text class="performance-axis-label-v54" x="'+x.toFixed(1)+'" y="307" text-anchor="middle"><tspan x="'+x.toFixed(1)+'">'+escapeXml(ranges[0]||'—')+'</tspan><tspan x="'+x.toFixed(1)+'" dy="17">—'+escapeXml(ranges[1]||'')+'</tspan></text>';
      if(current[index]!==null){const y=yLeft(current[index]);html+='<circle class="performance-current-point-v54" cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="5"></circle>';}
      if(previous[index]!==null){const y=yLeft(previous[index]);html+='<circle class="performance-previous-point-v54" cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="5"></circle>';}
      if(yoy[index]!==null){const y=yYoy(yoy[index]);html+='<circle class="performance-yoy-point-v54" cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="5"></circle><text class="performance-value-label-v54" x="'+x.toFixed(1)+'" y="'+(y-12).toFixed(1)+'" text-anchor="middle">'+escapeXml(yoyText(yoy[index]))+'</text>';}
    });
    html+='<text class="performance-axis-label-v54" x="12" y="26">'+escapeXml(labels[key]||key)+'</text>';
    html+='<text class="performance-axis-label-v54" x="704" y="26" text-anchor="end">YOY</text>';
    svg.innerHTML=html;
  };
  document.querySelectorAll('.performance-card-v54').forEach((card)=>{
    const select=card.querySelector('.performance-select-v54');
    if(select) select.addEventListener('change',()=>render(card));
    render(card);
  });
})();
</script>
"""


def _item_one(result: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == 1
        ),
        None,
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v36.build_html(result)
    item = _item_one(result)
    if item:
        html_text = _ITEM_ONE_PATTERN.sub(
            lambda _: _performance_card(item),
            html_text,
            count=1,
        )
    html_text = html_text.replace("</head>", PERFORMANCE_TREND_STYLE + "</head>", 1)
    return html_text.replace("</body>", _script() + "</body>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v36.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v36.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "PERFORMANCE_TREND_STYLE",
    "_detail_table",
    "_performance_card",
    "build_html",
    "build_markdown",
    "write_reports",
]
