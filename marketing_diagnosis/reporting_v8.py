from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v6
from marketing_diagnosis.visual_diagnosis import build_visual_diagnosis


TEMPLATE_PATH = Path(__file__).with_name("templates") / "customer_report_v24.html"

DESCRIPTIONS = {
    1: "展示本期与去年同期月度经营数据，并计算房费同比 YOY。",
    2: "展示各房型 RevPAR、出租率及低效房型占比。",
    3: "展示整体曝光、非广告曝光、广告曝光及每日广告曝光占比。",
    4: "展示流量、转化、同行均值及各项同行排名。",
    5: "展示本地/异地、新客/老客用户结构，本项只展示不计分。",
    6: "展示数据库可用日期范围内、最多近30天的 HOS 得分趋势与排名。",
    7: "展示近一个月扫码订单数量与统计口径。",
    8: "展示当日信息分；有值满分，无值计0分。",
    9: "展示近30天推广投入、本月美团EBK订单金额及 ROI。",
    10: "展示门店标题、后缀及热门商圈词命中结果。",
    11: "展示房型名称、字符数及卖点词命中结果。",
    12: "按流失酒店展示订单数、金额、流失房型和关注状态。",
    13: "分别展示美团与大众点评评分、点评数及未回复数。",
    14: "展示已报名权益数量、权益名称和有效房型范围。",
    15: "展示优美会开通、报名与生效状态。",
    16: "展示商旅专享价开通、报名与生效状态。",
    17: "展示公益流量开通、报名与生效状态。",
    18: "展示钟点房开通、报名与生效状态。",
    19: "展示酒店亮点配置与生效状态。",
    20: "展示预约开票开关与生效状态。",
    21: "展示房型视频、酒店预览视频和房型预览视频的上传数量与要求数量。",
    22: "展示人工录入的酒店挂冠等级。",
    23: "展示自动接单开关与生效状态。",
}

PERIODS = {
    1: "本月与去年同期", 2: "近30天", 3: "近30天", 4: "近30天",
    5: "最新月份", 6: "最多近30天", 7: "近一个月", 8: "当日",
    9: "近30天/本月", 10: "最新快照", 11: "最新快照", 12: "最新月份",
    13: "最新快照", 14: "最新快照", 15: "最新快照", 16: "最新快照",
    17: "最新快照", 18: "最新快照", 19: "最新快照", 20: "最新快照",
    21: "最新快照", 22: "人工录入", 23: "最新快照",
}

STATUS = {
    "success": ("已形成结果", "ok"), "zero": ("真实为0", "disabled"),
    "missing": ("数据未取到", "pending"), "error": ("查询失败", "pending"),
    "pending_rule": ("规则待确认", "pending"), "manual_pending": ("待人工录入", "manual"),
}


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


def _value(label: str, value: Any) -> str:
    if value in (None, ""):
        return "暂无数据"
    if isinstance(value, float):
        if any(key in label for key in ("占比", "率", "YOY", "同比")):
            return f"{value:.2%}"
        if any(key in label for key in ("金额", "房费", "投入", "收入")):
            return f"¥{value:,.2f}"
        return f"{value:,.2f}"
    return str(value)


def _score_text(item: dict[str, Any]) -> str:
    if not item.get("participates_in_score"):
        return "仅展示"
    score = item.get("item_score")
    return "待计算" if score is None else f"{float(score):g}分"


def _base_text(item: dict[str, Any]) -> str:
    return "仅展示" if not item.get("participates_in_score") else f"{float(item.get('base_score') or 0):g}分"


def _field(item: dict[str, Any], label: str) -> dict[str, Any]:
    return next((field for field in item.get("fields") or [] if field.get("label") == label), {})


def _source_box(item: dict[str, Any]) -> str:
    fields = "、".join(str(value) for value in item.get("source_fields") or []) or "待补充"
    return (
        "<div class='field-standard-note'><b>数据库来源：</b>"
        f"<code>{_e(item.get('source_table') or '待确认')}</code><br>"
        f"<b>对应字段：</b>{_e(fields)}</div>"
    )


def _metric_cards(item: dict[str, Any], limit: int = 5) -> str:
    fields = (item.get("fields") or [])[:limit]
    if not fields:
        fields = [{"label": "数据状态", "value": None, "note": "数据库未返回可展示记录"}]
    return "<div class='metric-row five'>" + "".join(
        f"<div><small>{_e(field.get('label'))}</small><b>{_e(_value(str(field.get('label') or ''), field.get('value')))}</b>"
        f"<span>{_e(field.get('note') or '')}</span></div>" for field in fields
    ) + "</div>"


def _trend_svg(item: dict[str, Any]) -> str:
    points = []
    for field in (item.get("fields") or [])[4:]:
        value = _n(field.get("value"))
        label = str(field.get("label") or "")
        if value is not None and len(label) >= 8:
            points.append((label[-5:], value))
    if not points:
        return "<div class='notice pending-note'>数据库未返回可绘制的 HOS 日数据。</div>"
    points = points[-30:]
    values = [value for _, value in points]
    low, high = min(values), max(values)
    span = max(high - low, 1)
    width, height = 760, 220
    coords = []
    dots = []
    labels = []
    for index, (label, value) in enumerate(points):
        x = 45 + index * 680 / max(1, len(points) - 1)
        y = 180 - (value - low) / span * 135
        coords.append(f"{x:.1f},{y:.1f}")
        dots.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3.5' fill='#5b6fd8'><title>{_e(label)}：{value:g}</title></circle>")
        if index in {0, len(points) - 1} or index % max(1, len(points) // 6) == 0:
            labels.append(f"<text class='axis-label' text-anchor='middle' x='{x:.1f}' y='204'>{_e(label)}</text>")
    return (
        f"<svg class='native-chart' viewBox='0 0 {width} {height}'><line class='grid-line' x1='45' y1='180' x2='725' y2='180'/>"
        f"<polyline fill='none' points='{' '.join(coords)}' stroke='#5b6fd8' stroke-width='3'/>"
        + "".join(dots + labels) + "</svg>"
    )


def _result_area(item: dict[str, Any]) -> str:
    no = int(item.get("standard_item_id") or 0)
    if no == 6:
        return f"<div class='visual-grid two'><div class='viz-card'><h4>近30天 HOS 趋势</h4>{_trend_svg(item)}</div><div class='viz-card'><h4>统计结果</h4>{_metric_cards(item, 4)}</div></div>"
    if no == 21:
        cards = []
        for field in item.get("fields") or []:
            value = _n(field.get("value"))
            state = "open" if value and value > 0 else "closed" if value == 0 else "pending"
            cards.append(
                f"<div class='video-summary-card {state}'><small>{_e(field.get('label'))}</small>"
                f"<strong>{_e(_value(str(field.get('label') or ''), field.get('value')))}</strong><span>{_e(field.get('note'))}</span></div>"
            )
        return "<div class='video-summary-grid'>" + "".join(cards) + "</div>"
    return _metric_cards(item)


def _detail_panel(item: dict[str, Any]) -> str:
    rows = []
    for field in item.get("fields") or []:
        rows.append(
            f"<tr><td class='field-name'>{_e(field.get('label'))}</td>"
            f"<td><span class='value-rule'>{_e(_value(str(field.get('label') or ''), field.get('value')))}</span></td>"
            f"<td><span class='status-badge neutral'>{_e(field.get('origin') or '数据库原值')}</span></td>"
            f"<td>{_e(field.get('note') or '数据库原值或规则计算值')}</td></tr>"
        )
    if not rows:
        rows.append("<tr><td class='field-name'>数据状态</td><td><span class='value-pending'>暂无数据</span></td><td><span class='status-badge pending'>未取到</span></td><td>请检查数据库查询诊断</td></tr>")
    return (
        "<details class='output-fields-panel metric-details'><summary class='output-fields-head metric-details-summary'>"
        "<div><h4>查看全部诊断指标</h4><p>包含数据库来源、字段、当前结果及详细口径</p></div>"
        f"<span class='field-count simple-count'>{len(rows)}项核心指标</span></summary>"
        "<div class='metric-details-content'><div class='detail-group data-group'>"
        "<div class='detail-group-title'><div>数据明细</div><span>本项全部输出指标</span></div>"
        "<div class='table-scroll'><table class='output-table'><thead><tr><th>指标</th><th>当前结果</th><th>取值方式</th><th>说明</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div></div></div></details>"
    )


def _card(item: dict[str, Any]) -> str:
    no = int(item.get("standard_item_id") or 0)
    status_key = str(item.get("data_status") or "missing")
    status_text, status_class = STATUS.get(status_key, (status_key, "neutral"))
    score_class = "ok" if item.get("item_score") is not None else "pending"
    return (
        f"<article class='diagnosis-card' data-status='{_e(status_key)}' data-title='{_e(item.get('item_name'))}' id='rule-{no}'>"
        "<div class='card-top'>"
        f"<div class='rule-no'>{no:02d}</div><div class='card-title'><h3>{_e(item.get('item_name'))}</h3>"
        f"<p>{_e(DESCRIPTIONS.get(no, '展示数据库结果和评分状态。'))}</p></div>"
        "<div class='card-tags'>"
        f"<div class='title-meta-item title-period'><small>统计周期</small><strong>{_e(PERIODS.get(no, '当前周期'))}</strong></div>"
        f"<div class='title-meta-item title-score {score_class}'><small>当前得分</small><div class='title-score-value'><strong>{_e(_score_text(item))}</strong><span>满分 {_e(_base_text(item))}</span></div></div>"
        f"<span class='status-badge {status_class}'>{_e(status_text)}</span></div></div>"
        f"<div class='result-area'>{_result_area(item)}{_source_box(item)}"
        f"<div class='notice'>{_e(item.get('note') or '数据直接来自上述数据库表；派生值按本项规则计算。')}</div></div>"
        f"{_detail_panel(item)}</article>"
    )


def _config_group(items: dict[int, dict[str, Any]]) -> str:
    rows = []
    total_score = 0.0
    total_base = 0.0
    for no in (15, 16, 17, 18, 19, 20, 23):
        item = items[no]
        status_key = str(item.get("data_status") or "missing")
        status_text, status_class = STATUS.get(status_key, (status_key, "neutral"))
        main_status = _value("开通状态", _field(item, "开通状态").get("value"))
        enroll = _value("报名状态", _field(item, "报名状态").get("value"))
        effective = _value("生效状态", _field(item, "生效状态").get("value"))
        score = _n(item.get("item_score"))
        total_base += float(item.get("base_score") or 0)
        if score is not None:
            total_score += score
        chip = "open" if status_key == "success" else "closed" if status_key == "zero" else "pending"
        rows.append(
            f"<tr class='config-status-row' id='rule-{no}'><td class='config-rule-number'>{no}</td>"
            f"<td class='config-item-name'>{_e(item.get('item_name'))}</td>"
            f"<td><div class='config-status-cell'><small>开通状态</small><span class='config-status-chip {chip}'>{_e(main_status)}</span></div></td>"
            f"<td><div class='config-status-cell'><small>报名 / 生效状态</small><span class='config-status-chip {chip}'>{_e(enroll)} / {_e(effective)}</span></div></td>"
            f"<td><span class='config-result-chip {chip}'>{_e(status_text)}</span></td>"
            f"<td class='config-full-score'>{_e(_base_text(item))}</td><td><span class='config-score-chip {chip}'>{_e(_score_text(item))}</span></td></tr>"
        )
    source = _source_box(items[15])
    return (
        "<article class='diagnosis-card config-status-group' id='config-status-group'><div class='card-top'>"
        "<div class='rule-no config-group-no'>15–20</div><div class='card-title'><h3>配置状态汇总</h3><p>统一展示各功能当前状态、数据库来源和得分。</p></div>"
        f"<div class='card-tags'><div class='title-meta-item title-period'><small>统计周期</small><strong>当前配置快照</strong></div>"
        f"<div class='title-meta-item title-score'><small>当前得分</small><div class='title-score-value'><strong>{total_score:g}分</strong><span>合计{total_base:g}分</span></div></div></div></div>"
        "<div class='config-status-legend'><div class='config-legend-item open'><strong>OPEN</strong><span>已开通 / 已参与</span><small>满分</small></div>"
        "<div class='config-legend-item closed'><strong>CLOSED</strong><span>未开通 / 未参与</span><small>0分</small></div>"
        "<div class='config-legend-item pending'><strong>PENDING</strong><span>未确定 / 未取到</span><small>待计算</small></div></div>"
        "<div class='result-area config-status-result'><div class='viz-card config-status-card'><div class='table-scroll'><table class='config-status-table'>"
        "<thead><tr><th>编号</th><th>配置项</th><th>主状态</th><th>补充状态</th><th>判定结果</th><th>满分</th><th>当前得分</th></tr></thead><tbody>"
        + "".join(rows) + f"</tbody></table></div>{source}<div class='notice config-status-note'>状态字段缺失时保持待确认，不默认为未开通。</div></div></div></article>"
    )


def _summary(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items:
        no = int(item.get("standard_item_id") or 0)
        status_key = str(item.get("data_status") or "missing")
        status_text, status_class = STATUS.get(status_key, (status_key, "neutral"))
        rows.append(
            f"<tr data-status='{_e(status_key)}' data-title='{_e(item.get('item_name'))}'><td>{no:02d}</td>"
            f"<td><a href='#rule-{no}'>{_e(item.get('item_name'))}</a></td><td>{_e(_base_text(item))}</td>"
            f"<td>{_e(_score_text(item))}</td><td><span class='status-badge {status_class}'>{_e(status_text)}</span></td>"
            f"<td>{_e(item.get('source_table'))}<br>{_e(DESCRIPTIONS.get(no))}</td></tr>"
        )
    return (
        "<section id='summary'><div class='section-head'><div><h2>23项诊断结果总览</h2>"
        "<p>数据库真实结果、评分状态和来源表；点击项目名称查看详细字段。</p></div>"
        "<div class='toolbar'><input class='search' id='ruleSearch' placeholder='搜索诊断项'/><select class='filter' id='statusFilter'><option value='all'>全部状态</option><option value='success'>已形成结果</option><option value='missing'>数据未取到</option><option value='pending_rule'>规则待确认</option></select></div></div>"
        "<div class='section-body'><div class='table-scroll'><table class='summary-table'><thead><tr><th>编号</th><th>诊断项目</th><th>满分</th><th>当前得分</th><th>当前状态</th><th>数据库来源/诊断内容</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div></div></section>"
    )


def _source_counts(result: dict[str, Any]) -> tuple[int, int]:
    rows = tables = 0
    for source in (result.get("data_quality") or {}).get("source_diagnostics") or []:
        for diag in (source.get("tables") or {}).values():
            if diag.get("status") == "ok":
                tables += 1
                rows += int(diag.get("rows") or 0)
    return tables, rows


def build_html(result: dict[str, Any]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    head = template.split("</head>", 1)[0] + "</head>"
    visual = result.get("visual_diagnosis") or build_visual_diagnosis({}, str(result.get("hotel_name") or ""))
    items = visual.get("items") or []
    item_map = {int(item.get("standard_item_id") or 0): item for item in items}
    hotel = result.get("hotel_name") or result.get("hotel_id") or "酒店"
    start, end = result.get("period_start") or "未标注", result.get("period_end") or "未标注"
    normalized = _n(visual.get("normalized_score"))
    normalized_text = "待计算" if normalized is None else f"{normalized:.1f}"
    tables, rows = _source_counts(result)
    missing = sum(1 for item in items if item.get("data_status") in {"missing", "error"})
    nav = ["<nav class='side'><div class='side-title'>报告目录</div><a href='#overview'><span>00</span>诊断概览</a><a href='#summary'><span>表</span>诊断结果总览</a>"]
    nav.extend(f"<a href='#rule-{no}'><span>{no:02d}</span>{_e(item_map[no].get('item_name'))}</a>" for no in range(1, 24))
    nav.append("</nav>")
    overview = (
        "<section id='overview'><div class='hero'><div class='hero-grid'><div><h2>酒店经营与线上运营综合诊断</h2>"
        "<p>严格使用数据库真实数据生成，覆盖经营趋势、流量、客群、推广、口碑及平台配置等23项内容。</p>"
        f"<div class='source-standard'><div><small>诊断周期</small><b>{_e(start)} 至 {_e(end)}</b></div>"
        f"<div><small>数据库核验</small><b>{tables}张表 · {rows}行</b></div><div><small>规则版本</small><b>{_e(visual.get('rule_version'))}</b></div></div></div>"
        f"<div class='hero-stats'><div class='hero-stat'><small>折算得分</small><strong>{_e(normalized_text)}</strong><em>按已成功评分项目折算</em></div>"
        f"<div class='hero-stat'><small>原始得分</small><strong>{_e(visual.get('raw_score'))}</strong><em>固定满分100分</em></div>"
        f"<div class='hero-stat'><small>已接入基础分</small><strong>{_e(visual.get('connected_base_score'))}</strong><em>进入折算分母</em></div>"
        f"<div class='hero-stat'><small>未取到数据</small><strong>{missing}项</strong><em>不会用随机值或0替代</em></div></div></div></div>"
        "<div class='section-body'><div class='notice'>报告中的每项数据均展示来源表和字段；查询失败、空结果和真实0分别处理。</div></div></section>"
    )
    cards = []
    for no in range(1, 15):
        cards.append(_card(item_map[no]))
    cards.append(_config_group(item_map))
    cards.append(_card(item_map[21]))
    cards.append(_card(item_map[22]))
    script = """
<script>
document.addEventListener('DOMContentLoaded',function(){
  const search=document.getElementById('ruleSearch'), filter=document.getElementById('statusFilter');
  function apply(){const q=(search.value||'').trim().toLowerCase(), s=filter.value;
    document.querySelectorAll('.diagnosis-card:not(.config-status-group)').forEach(card=>{const okQ=!q||(card.dataset.title||'').toLowerCase().includes(q);const okS=s==='all'||card.dataset.status===s;card.classList.toggle('hidden-card',!(okQ&&okS));});
  }
  search.addEventListener('input',apply);filter.addEventListener('change',apply);
});
</script>
"""
    body = (
        f"<body><header class='topbar'><div class='topbar-inner'><div class='brand'><h1>酒店 OTA 全面诊断报告</h1>"
        f"<p>{_e(hotel)}｜诊断周期：{_e(start)} 至 {_e(end)}｜生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p></div>"
        "<div class='top-actions'><select class='scope-select'><option>综合诊断</option><option>PMS经营数据</option><option>美团EB数据</option></select><button class='btn primary' onclick='window.print()'>导出报告</button></div></div></header>"
        "<div class='page'>" + "".join(nav) + "<main>" + overview + _summary(items) + "".join(cards) + "</main></div>" + script + "</body></html>"
    )
    return head + body


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v6.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v6.write_reports(result, output_dir)
    Path(paths["report_html"]).write_text(build_html(result), encoding="utf-8")
    return paths
