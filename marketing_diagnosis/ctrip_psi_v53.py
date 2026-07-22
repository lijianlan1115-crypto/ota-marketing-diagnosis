from __future__ import annotations

import html
import math
import re
from typing import Any


METRICS = (
    ("historical_room_nights", "经营产能", "历史间夜量", "间夜", "夜量"),
    ("historical_gmv", "经营产能", "历史营业额", "元", "营业额"),
    ("historical_deal_rate", "经营产能", "历史成交率", "%", "成交率"),
    ("instant_confirm_order_rate", "房源保障", "即时确认订单占比", "%", "即时确认"),
    ("consumer_value", "房源保障", "消费者实惠分", "指数", "实惠分"),
    ("room_status_good_rate", "房源保障", "房态良好度", "%", "房态"),
    ("review_competitiveness", "客户服务", "点评竞争指数", "指数", "点评"),
    ("information_completeness", "客户服务", "信息完整度", "%", "信息"),
    ("cancellation_rate", "客户服务", "可取消率", "%", "可取消"),
)

STYLE = """
<style id='CTRIP_PSI_V53'>
.psi-v53{border:1px solid #dfe7e4;border-radius:12px;background:#fff;overflow:hidden}
.psi-overview-v53{display:grid;grid-template-columns:minmax(210px,.8fr) minmax(0,1.7fr);gap:14px;padding:16px 18px 14px}
.psi-total-v53{display:flex;flex-direction:column;justify-content:center;min-height:170px;padding:20px;border-radius:12px;background:linear-gradient(145deg,#edf7f2,#f8fbfa);border:1px solid #d9e9e1}
.psi-total-v53 small{color:#67766f;font-size:12px;font-weight:800}.psi-total-v53 strong{margin-top:7px;color:#14855c;font-size:48px;line-height:1}.psi-total-v53 em{margin-top:9px;color:#607068;font-size:12px;font-style:normal}.psi-total-v53 b{margin-top:13px;color:#273a32;font-size:14px}
.psi-summary-grid-v53{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.psi-summary-card-v53{padding:15px;border:1px solid #e1e9e6;border-radius:10px;background:#fbfcfc}.psi-summary-card-v53 small{display:block;color:#76847d;font-size:11px;font-weight:700}.psi-summary-card-v53 strong{display:block;margin-top:8px;color:#263a32;font-size:22px}.psi-summary-card-v53 span{display:block;margin-top:5px;color:#91a099;font-size:11px}
.psi-grid-v53{display:grid;grid-template-columns:minmax(300px,.78fr) minmax(620px,1.55fr);gap:14px;padding:0 18px 16px}
.psi-radar-box-v53{display:flex;align-items:center;justify-content:center;min-height:395px;border:1px solid #e4ebe7;border-radius:10px;background:#fbfdfc}.psi-radar-v53{width:min(100%,390px);height:auto}.psi-radar-grid-v53{fill:none;stroke:#d9e2de}.psi-radar-axis-v53{stroke:#cfdad5}.psi-radar-shape-v53{fill:rgba(31,157,108,.12);stroke:#1f9d6c;stroke-width:2.3}.psi-radar-dot-v53{fill:#fff;stroke:#1f9d6c;stroke-width:2}.psi-radar-label-v53{font-size:12px;fill:#354840;font-family:inherit}
.psi-table-box-v53{overflow:auto;border:1px solid #dfe7e4;border-radius:10px}.psi-table-v53{width:100%;border-collapse:collapse;min-width:560px}.psi-table-v53 th,.psi-table-v53 td{padding:10px 9px;border-bottom:1px solid #e7eeeb;text-align:left;vertical-align:middle}.psi-table-v53 th{background:#f6faf8;color:#53645c;font-size:12px;font-weight:850;white-space:nowrap}.psi-table-v53 td{font-size:12px;color:#30433b}.psi-type-v53{width:68px;font-weight:900}.psi-index-v53{font-weight:800}.psi-muted-v53{color:#93a099}.psi-period-v53{white-space:nowrap}
.psi-deduction-v53{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 18px 14px}.psi-deduction-v53 div{padding:12px 14px;border:1px solid #eadfdd;border-radius:9px;background:#fffafa}.psi-deduction-v53 small{display:block;color:#8b7772;font-size:11px}.psi-deduction-v53 strong{display:block;margin-top:6px;color:#b74d43;font-size:18px}
.psi-history-v53{margin:0 18px 14px;padding:12px 14px;border:1px solid #e2eae6;border-radius:9px;background:#fafcfb}.psi-history-v53 b{display:block;margin-bottom:8px;color:#34483f}.psi-history-list-v53{display:flex;gap:8px;overflow-x:auto}.psi-history-item-v53{flex:0 0 auto;padding:8px 11px;border-radius:8px;background:#edf6f1;color:#31594a;font-size:11px}.psi-history-item-v53 strong{display:block;margin-top:3px;font-size:15px}
.psi-source-v53{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 18px 18px}.psi-source-v53 div{padding:12px 14px;border:1px solid #dfe7e4;border-radius:9px;background:#f8fbfa}.psi-source-v53 b{display:block}.psi-source-v53 span{display:block;margin-top:5px;color:#66756e;font-size:12px;line-height:1.55}.psi-pending-v53{color:#8e9b95}
@media(max-width:1100px){.psi-overview-v53,.psi-grid-v53{grid-template-columns:1fr}.psi-summary-grid-v53{grid-template-columns:repeat(2,minmax(0,1fr))}.psi-radar-box-v53{min-height:330px}}
@media(max-width:680px){.psi-overview-v53{padding:12px}.psi-summary-grid-v53,.psi-deduction-v53,.psi-source-v53{grid-template-columns:1fr}.psi-grid-v53{padding:0 12px 12px}.psi-deduction-v53,.psi-source-v53,.psi-history-v53{margin-left:12px;margin-right:12px}}
</style>
"""

CARD_RE = re.compile(r"<article\b(?=[^>]*\bid=['\"](?P<anchor>(?:rule|module)-6)['\"])[^>]*>.*?</article>", re.S | re.I)
NAV_RE = re.compile(r"<a\b(?=[^>]*href=['\"]#(?:rule|module)-6['\"])[^>]*>.*?</a>", re.S | re.I)
SUMMARY_RE = re.compile(r"<tr\b[^>]*>\s*<td>\s*06\s*</td>.*?</tr>", re.S | re.I)


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) or math.isinf(number) else number


def payload(result: dict[str, Any]) -> dict[str, Any]:
    items = result.get("ctrip_items") if isinstance(result.get("ctrip_items"), dict) else {}
    value = items.get("6") or items.get(6) or result.get("ctrip_psi")
    if isinstance(value, dict):
        return dict(value)
    sections = result.get("sections") if isinstance(result.get("sections"), dict) else {}
    if sections.get("ctrip_psi_score") or sections.get("ctrip_psi_metric"):
        from marketing_diagnosis.ctrip_psi import build_psi_item

        return build_psi_item(sections)
    return {}


def _metric_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = data.get("metrics")
    if isinstance(values, list):
        return {
            str(row.get("metric_code") or ""): dict(row)
            for row in values
            if isinstance(row, dict) and row.get("metric_code")
        }
    if isinstance(values, dict):
        return {
            str(code): (dict(row) if isinstance(row, dict) else {"psi_score": row})
            for code, row in values.items()
        }
    return {}


def _plain(value: Any, decimals: int = 2) -> str:
    number = num(value)
    if number is None:
        return "待接入"
    if number.is_integer():
        return f"{number:,.0f}"
    return f"{number:,.{decimals}f}"


def _metric_value(value: Any, unit: str) -> str:
    number = num(value)
    if number is None:
        return "待接入"
    if unit == "%":
        percent = number * 100 if abs(number) <= 1 else number
        return f"{percent:.2f}%"
    if unit == "元":
        return f"{number:,.2f}"
    return f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"


def _rank(data: dict[str, Any]) -> str:
    rank = num(data.get("psi_rank"))
    count = num(data.get("psi_competition_circle_count"))
    if rank is None:
        return "待接入"
    return f"第 {rank:g} 名" + (f" / {count:g}家" if count is not None else "")


def _score_pair(value: Any, maximum: Any) -> str:
    current = _plain(value)
    max_value = num(maximum)
    return current if max_value is None else f"{current} / {max_value:g}"


def radar(data: dict[str, Any]) -> str:
    metric_values = _metric_map(data)
    cx = cy = 190.0
    radius = 122.0
    total = len(METRICS)

    def point(index: int, scale: float) -> tuple[float, float]:
        angle = -math.pi / 2 + 2 * math.pi * index / total
        return cx + radius * scale * math.cos(angle), cy + radius * scale * math.sin(angle)

    grids = [
        "<polygon class='psi-radar-grid-v53' points='"
        + " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(index, level / 5) for index in range(total)))
        + "'/>"
        for level in range(1, 6)
    ]
    axes: list[str] = []
    labels: list[str] = []
    values: list[float | None] = []
    for index, (code, _, _, _, short_label) in enumerate(METRICS):
        x, y = point(index, 1)
        axes.append(f"<line class='psi-radar-axis-v53' x1='{cx}' y1='{cy}' x2='{x:.1f}' y2='{y:.1f}'/>")
        label_x, label_y = point(index, 1.18)
        anchor = "end" if label_x < cx - 16 else "start" if label_x > cx + 16 else "middle"
        labels.append(f"<text class='psi-radar-label-v53' x='{label_x:.1f}' y='{label_y:.1f}' text-anchor='{anchor}' dominant-baseline='middle'>{e(short_label)}</text>")
        values.append(num((metric_values.get(code) or {}).get("psi_score")))

    shape = ""
    if any(value is not None for value in values):
        points = [point(index, max(0.0, min(5.0, value or 0.0)) / 5) for index, value in enumerate(values)]
        shape = (
            "<polygon class='psi-radar-shape-v53' points='"
            + " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
            + "'/>"
            + "".join(f"<circle class='psi-radar-dot-v53' cx='{x:.1f}' cy='{y:.1f}' r='3.3'/>" for x, y in points)
        )
    return "<svg class='psi-radar-v53' viewBox='0 0 380 380' role='img' aria-label='PSI九项诊断指标雷达图'>" + "".join(grids + axes) + shape + "".join(labels) + "</svg>"


def rows(data: dict[str, Any]) -> str:
    metric_values = _metric_map(data)
    counts = {group: sum(1 for _, metric_group, _, _, _ in METRICS if metric_group == group) for group in {metric[1] for metric in METRICS}}
    seen: set[str] = set()
    output: list[str] = []
    for code, group, label, default_unit, _ in METRICS:
        value = metric_values.get(code) or {}
        unit = str(value.get("unit") or default_unit)
        group_cell = ""
        if group not in seen:
            seen.add(group)
            group_cell = f"<td class='psi-type-v53' rowspan='{counts[group]}'>{e(group)}</td>"
        weight = num(value.get("weight_pct"))
        weight_text = "待接入" if weight is None else f"{weight:g}%"
        score_text = _plain(value.get("psi_score"))
        output.append(
            f"<tr>{group_cell}<td class='psi-index-v53'>{e(value.get('metric_name') or label)}</td>"
            f"<td>{e(_metric_value(value.get('metric_value'), unit))}</td>"
            f"<td>{e(weight_text)}</td><td><strong>{e(score_text)}</strong></td></tr>"
        )
    return "".join(output)


def _history(data: dict[str, Any]) -> str:
    history = [row for row in data.get("psi_history") or [] if isinstance(row, dict)]
    if not history:
        return ""
    items: list[str] = []
    for row in history[-8:]:
        date = row.get("business_date") or row.get("date") or row.get("snapshot_time") or "历史"
        value = row.get("psi_total_score")
        if value in (None, ""):
            value = row.get("score_psi") if row.get("score_psi") not in (None, "") else row.get("value")
        items.append(f"<div class='psi-history-item-v53'>{e(str(date)[:10])}<strong>{e(_plain(value))}</strong></div>")
    return f"<div class='psi-history-v53'><b>PSI 历史趋势</b><div class='psi-history-list-v53'>{''.join(items)}</div></div>"


def card(result: dict[str, Any], anchor: str) -> str:
    data = payload(result)
    connected = str(data.get("data_status") or "missing") == "success"
    status, css = ("已形成结果", "ok") if connected else ("数据待接入", "pending")
    total = _plain(data.get("psi_total_score"))
    item_score = _plain(data.get("item_score"))
    return (
        f"<article class='diagnosis-card' data-status='{'success' if connected else 'missing'}' data-title='PSI 服务质量分' id='{e(anchor)}'>"
        "<div class='card-top'><div class='rule-no'>06</div>"
        "<div class='card-title'><h3>PSI 服务质量分</h3><p>按PSI总分计算本项得分，九项子指标仅用于诊断解释，不重复计分。</p></div>"
        "<div class='card-tags'><div class='title-meta-item title-period'><small>统计周期</small><strong>当前值</strong></div>"
        "<div class='title-meta-item title-score pending'><small>当前得分</small><div class='title-score-value'><strong>待计算</strong><span>满分 8分</span></div></div>"
        f"<span class='status-badge {css}'>{status}</span></div></div>"
        "<div class='result-area'><div class='psi-v53'>"
        "<div class='psi-overview-v53'>"
        f"<div class='psi-total-v53'><small>PSI 服务质量总分</small><strong>{e(total)}</strong><em>对应诊断得分 {e(item_score)} / 8分</em><b>{e(_rank(data))}</b></div>"
        "<div class='psi-summary-grid-v53'>"
        f"<div class='psi-summary-card-v53'><small>基础分</small><strong>{e(_score_pair(data.get('psi_basic_score'), data.get('psi_basic_score_max')))}</strong><span>当前值 / 满分</span></div>"
        f"<div class='psi-summary-card-v53'><small>奖励分</small><strong>{e(_score_pair(data.get('psi_reward_score'), data.get('psi_reward_score_max')))}</strong><span>当前值 / 满分</span></div>"
        f"<div class='psi-summary-card-v53'><small>总扣分</small><strong>{e(_plain(data.get('psi_deduction_score')))}</strong><span>服务、诚信、财务合计</span></div>"
        f"<div class='psi-summary-card-v53'><small>竞争圈排名</small><strong>{e(_rank(data))}</strong><span>PSI 综合表现</span></div>"
        "</div></div>"
        f"<div class='psi-grid-v53'><div class='psi-radar-box-v53'>{radar(data)}</div>"
        "<div class='psi-table-box-v53'><table class='psi-table-v53'><thead><tr>"
        "<th>指标类型</th><th>诊断指标</th><th>实际值</th><th>权重</th><th>PSI得分</th>"
        f"</tr></thead><tbody>{rows(data)}</tbody></table></div></div>"
        "<div class='psi-deduction-v53'>"
        f"<div><small>服务扣分</small><strong>{e(_plain(data.get('service_deduction_score')))}</strong></div>"
        f"<div><small>诚信扣分</small><strong>{e(_plain(data.get('integrity_deduction_score')))}</strong></div>"
        f"<div><small>财务扣分</small><strong>{e(_plain(data.get('financial_deduction_score')))}</strong></div>"
        "</div>"
        f"{_history(data)}"
        "<div class='psi-source-v53'>"
        "<div><b>页面数据来源</b><span>携程 eBooking → 工具中心 / PSI 服务质量分</span></div>"
        "<div><b>数据库来源与计分口径</b><span>汇总表：ctrip_ota_psi_score；明细表：ctrip_ota_psi_metric。PSI≥5.5得8分；5.0–5.49得6.4分；4.5–4.99得4.8分；低于4.5得0分。</span></div>"
        "</div></div>"
        "<div class='notice'>九项PSI子指标只用于解释酒店服务质量表现，不再拆成多个高权重计分项。</div>"
        "</div></article>"
    )


def transform(html_text: str, result: dict[str, Any]) -> str:
    html_text = html_text.replace("</head>", STYLE + "</head>", 1)
    html_text = re.sub(r"<title>.*?</title>", "<title>携程｜酒店 OTA 全面诊断报告</title>", html_text, count=1, flags=re.S | re.I)

    def nav(match: re.Match[str]) -> str:
        found = re.search(r"href=['\"]#([^'\"]+)", match.group(0), re.I)
        return f"<a href='#{e(found.group(1) if found else 'rule-6')}'><span>06</span>PSI 服务质量分</a>"

    html_text = NAV_RE.sub(nav, html_text, count=1)
    data = payload(result)
    current = _plain(data.get("item_score")) if data else "待计算"
    status = "已形成结果" if data.get("data_status") == "success" else "数据待接入"
    css = "ok" if data.get("data_status") == "success" else "pending"
    summary = (
        "<tr data-status='" + ("success" if css == "ok" else "missing") + "' data-title='PSI 服务质量分'>"
        "<td>06</td><td><a href='#rule-6'>PSI 服务质量分</a></td><td>8分</td>"
        f"<td>{e(current)}</td><td><span class='status-badge {css}'>{e(status)}</span></td>"
        "<td>ctrip_ota_psi_score、ctrip_ota_psi_metric<br>PSI总分计分，九项指标仅诊断解释</td></tr>"
    )
    html_text = SUMMARY_RE.sub(summary, html_text, count=1)
    html_text, count = CARD_RE.subn(lambda match: card(result, match.group("anchor")), html_text, count=1)
    return html_text if count else html_text.replace("</main>", card(result, "rule-6") + "</main>", 1)


__all__ = ["STYLE", "card", "transform"]