from __future__ import annotations

from pathlib import Path
from datetime import datetime
import html
import json
from typing import Any


HTML_STYLE = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#1d2430;--muted:#667085;--line:#d9dee8;--line-soft:#edf0f5;--blue:#2563eb;--green:#168a4a;--amber:#b7791f;--red:#c2413a;--shadow:0 8px 24px rgba(22,34,51,.08)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif;font-size:14px;line-height:1.45}.app-header{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}.header-inner{max-width:1440px;margin:0 auto;padding:14px 24px;display:grid;grid-template-columns:1fr auto;gap:16px;align-items:center}.title-block h1{margin:0;font-size:22px;font-weight:700}.title-block p{margin:4px 0 0;color:var(--muted);font-size:13px}.actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;align-items:center}.btn{border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:8px;min-height:36px;padding:0 12px;font-weight:600;cursor:pointer}.btn.primary{background:var(--ink);border-color:var(--ink);color:#fff}.channel-selector{display:flex;align-items:center;gap:8px;padding:6px 12px;background:#f6f7f9;border-radius:8px;border:1px solid var(--line)}.channel-selector label{font-size:13px;color:var(--muted);font-weight:500}.channel-selector select{height:28px;padding:0 24px 0 8px;font-size:13px;border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--ink);cursor:pointer}.layout{max-width:1440px;margin:0 auto;padding:20px 24px 48px;display:grid;grid-template-columns:220px minmax(0,1fr);gap:20px}.sidebar{position:sticky;top:84px;align-self:start;border:1px solid var(--line);background:var(--panel);border-radius:8px;box-shadow:var(--shadow);overflow:hidden}.sidebar a{display:block;padding:11px 14px;color:#344054;text-decoration:none;border-bottom:1px solid var(--line-soft);font-weight:600;font-size:13px}.sidebar a:last-child{border-bottom:0}.sidebar a:hover{background:#f2f6fb;color:var(--blue)}main{display:grid;gap:18px}section{background:var(--panel);border:1px solid var(--line);border-radius:8px;box-shadow:var(--shadow);overflow:hidden}.section-head{padding:16px 18px;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line-soft)}.section-head h2{margin:0;font-size:17px;line-height:1.2}.section-head p{margin:5px 0 0;color:var(--muted);font-size:13px}.section-body{padding:18px}.status{display:inline-flex;align-items:center;justify-content:center;min-height:24px;padding:0 8px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap}.status.good{color:var(--green);background:#e8f5ee}.status.warn{color:var(--amber);background:#fff4dc}.status.bad{color:var(--red);background:#fdebea}.status.info{color:var(--blue);background:#eaf1ff}.status.neutral{color:#475467;background:#eef1f5}.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.kpi{border:1px solid var(--line);border-radius:8px;padding:14px;min-height:116px;display:grid;align-content:space-between;background:#fff}.kpi label{color:var(--muted);font-size:13px;font-weight:700}.kpi strong{display:block;margin-top:8px;font-size:28px;line-height:1}.kpi span{margin-top:9px;color:#475467;font-size:13px}.cap-alert{margin-top:12px;border:1px solid #f0cd7a;background:#fff8e6;border-radius:8px;padding:12px 14px;display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center}.cap-alert b{color:#7a4d08}.data-table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid var(--line-soft);text-align:left;vertical-align:middle}th{color:#475467;font-size:12px;font-weight:700;background:#f8fafc}tr:last-child td{border-bottom:0}.two-col{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px}.subpanel{border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#fff}.subpanel h3{margin:0;padding:12px 14px;border-bottom:1px solid var(--line-soft);font-size:15px;background:#fafbfc}.subpanel-content{padding:14px}.funnel{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:14px}.funnel-step{border:1px solid var(--line);border-radius:8px;padding:13px;background:#fbfcfe}.funnel-step label{color:var(--muted);font-size:12px;font-weight:700}.funnel-step strong{display:block;margin-top:6px;font-size:24px}.funnel-step span{display:block;margin-top:4px;color:var(--muted);font-size:12px}.legend{display:flex;flex-wrap:wrap;gap:10px 14px;margin-top:12px;color:var(--muted);font-size:12px}.legend i{display:inline-block;width:10px;height:10px;border-radius:999px;margin-right:5px;vertical-align:-1px}.analysis-card{margin-top:16px;border:1px solid #c7d2fe;border-left:4px solid #6366f1;border-radius:8px;background:#eef2ff;overflow:hidden}.analysis-card[open] summary{border-bottom:1px solid #c7d2fe}.analysis-card summary{cursor:pointer;padding:10px 16px;font-weight:700;font-size:14px;color:#4338ca;background:linear-gradient(135deg,#e0e7ff,#eef2ff);display:flex;align-items:center;gap:8px;list-style:none}.analysis-card summary::-webkit-details-marker{display:none}.ai-badge{display:inline-flex;align-items:center;gap:4px;font-size:11px;padding:2px 10px;border-radius:999px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-weight:700;letter-spacing:.5px}.analysis-body{padding:14px 18px;font-size:13px;line-height:1.75;color:#312e81;background:#eef2ff}.analysis-body p{margin:0 0 10px}.module-cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.module-card{border:1px solid var(--line);border-radius:10px;background:#fff;overflow:hidden}.module-card-header{padding:16px 18px 12px;display:grid;grid-template-columns:1fr auto;gap:10px;align-items:start}.mod-id{font-size:12px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}.mod-name{margin:2px 0 0;font-size:16px;font-weight:700;line-height:1.3}.module-card-score{text-align:right}.big-score{font-size:30px;font-weight:800;line-height:1}.of{font-size:13px;color:var(--muted)}.module-card-bar{padding:0 18px 6px}.bar-track{height:8px;background:#e9edf3;border-radius:999px;overflow:hidden}.bar-fill{height:100%;border-radius:999px;background:var(--blue)}.bar-fill.good{background:var(--green)}.bar-fill.warn{background:var(--amber)}.bar-fill.bad{background:var(--red)}.module-card-body{padding:0 18px 14px;font-size:13px;color:#475467;line-height:1.6;display:flex;flex-wrap:wrap;align-items:flex-start;gap:6px}.reason{display:inline-block;margin:0;padding:2px 8px;background:#f2f5f9;border-radius:4px;font-size:12px;color:#475467;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis}.module-card-analysis{margin:0 18px 14px;padding:12px 14px;background:#eef2ff;border-radius:8px;border:1px solid #c7d2fe;border-left:3px solid #818cf8;font-size:13px;line-height:1.65;color:#312e81}.channel-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-bottom:16px}.channel-card{border:1px solid var(--line);border-radius:10px;background:#fff;padding:14px}.channel-card h3{margin:0 0 10px;font-size:16px}.mini-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.mini{background:#f8fafc;border:1px solid var(--line-soft);border-radius:8px;padding:9px}.mini label{display:block;color:var(--muted);font-size:12px;font-weight:700}.mini strong{display:block;margin-top:4px;font-size:18px}.channel-card .suggest{margin-top:10px;color:#475467;font-size:13px}.hidden-by-channel{display:none!important}@media(max-width:980px){.layout{grid-template-columns:1fr;padding:14px}.sidebar{position:static;display:grid;grid-template-columns:repeat(2,1fr)}.kpi-grid,.two-col,.module-cards,.funnel,.channel-grid,.mini-grid{grid-template-columns:1fr}.header-inner{grid-template-columns:1fr;padding:12px 14px}.actions{justify-content:flex-start}}@media print{body{background:#fff}.app-header,.sidebar,.dashboard-only{display:none!important}.layout{display:block;padding:0;max-width:none}main{display:block}section{box-shadow:none;border:0;border-radius:0;page-break-inside:avoid}}
"""

MODULE_LABELS = {"M01": ("经营收益", "PMS jy01/jy03"), "M02": ("流量竞争", "美团/携程 OTA"), "M03": ("转化断点", "美团/携程 OTA"), "M04": ("价格房态", "PMS + OTA 商品"), "M05": ("推广ROI", "美团/携程推广"), "M06": ("页面基础", "页面采集/商品映射"), "M07": ("口碑信任", "美团/携程评价"), "M08": ("执行复盘", "系统计算")}


def _text(value: Any) -> str:
    if value is None:
        return "未获取"
    if isinstance(value, float):
        return f"{value:.4f}" if abs(value) < 1 else f"{value:.2f}"
    return str(value)


def _esc(value: Any) -> str:
    return html.escape(_text(value), quote=True)


def _num(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        return None if number != number else number
    except (TypeError, ValueError):
        return None


def _pct(value: Any) -> str:
    number = _num(value)
    return "未获取" if number is None else f"{number:.1%}"


def _money(value: Any) -> str:
    number = _num(value)
    return "未获取" if number is None else f"¥{number:,.1f}"


def _plain_num(value: Any, digits: int = 0) -> str:
    number = _num(value)
    return "未获取" if number is None else f"{number:,.{digits}f}"


def _risk_zh(risk: Any) -> str:
    return {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(str(risk or "").lower(), _text(risk))


def _platform_zh(platform: Any) -> str:
    return {"multi": "多渠道", "meituan": "美团", "ctrip": "携程", "fliggy": "飞猪", "unknown": "未知渠道"}.get(str(platform or "multi").lower(), _text(platform))


def _status_class(value: Any) -> str:
    if isinstance(value, str):
        return {"high": "bad", "medium": "warn", "low": "good", "data_gap": "neutral", "partial": "warn", "ok": "good"}.get(value.lower(), "neutral")
    number = _num(value)
    if number is None:
        return "neutral"
    if number >= 0.8:
        return "good"
    if number >= 0.6:
        return "warn"
    return "bad"


def _status_text(rate: Any, status: str = "ok") -> str:
    if status == "data_gap":
        return "数据缺口"
    value = _num(rate)
    if value is None:
        return "缺失"
    if value >= 0.8:
        return "正常/轻微可优化"
    if value >= 0.6:
        return "需要优化"
    return "严重短板"


def _ai_lines(result: dict[str, Any], key: str, fallback: list[str]) -> list[str]:
    ai = result.get("ai_analysis") or {}
    value = ai.get(key)
    if isinstance(value, list):
        clean = [str(x).strip() for x in value if str(x).strip()]
        return clean or fallback
    if isinstance(value, str) and value.strip():
        return [line.strip() for line in value.splitlines() if line.strip()] or fallback
    return fallback


def _ai_source(result: dict[str, Any]) -> str:
    source = str((result.get("ai_analysis") or {}).get("source") or "rule_based_fallback")
    if source == "ai":
        return "AI 接口"
    if source.startswith("rule_based"):
        return "规则兜底"
    return source


def build_markdown(result: dict[str, Any]) -> str:
    lines = ["# 酒店 OTA 全面诊断报告", "", f"- final_score: {result.get('final_score', 'missing')}", f"- risk_level: {result.get('risk_level', 'missing')}", f"- status: {result.get('status', 'missing')}", f"- report_url: {result.get('report_url', 'missing')}", "", "## Module Scores"]
    for item in result.get("module_scores") or []:
        lines.append(f"- {item.get('module_id')} {item.get('module_name')}: {item.get('score')}/{item.get('weight')} ({item.get('rate')}) status={item.get('status')}")
    return "\n".join(lines)


def _kpi(label: str, value: Any, hint: str = "", class_name: str = "") -> str:
    cls = f" class='{_esc(class_name)}'" if class_name else ""
    return f"<div class='kpi'><label>{_esc(label)}</label><strong{cls}>{_esc(value)}</strong><span>{_esc(hint)}</span></div>"


def _analysis(title: str, paragraphs: list[str], open_: bool = True, source: str = "AI 分析") -> str:
    body = "".join(f"<p>{_esc(p)}</p>" for p in paragraphs if str(p).strip())
    flag = " open" if open_ else ""
    return f"<details class='analysis-card'{flag}><summary><span class='ai-badge'>{_esc(source)}</span>{_esc(title)}</summary><div class='analysis-body'>{body}</div></details>"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell if str(cell).startswith('<') else _esc(cell)}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table class='data-table'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _missing_count(data_quality: dict[str, Any]) -> int:
    return sum(len(v or []) for v in (data_quality.get("missing_fields") or {}).values())


def _source_summary(data_quality: dict[str, Any]) -> str:
    total_rows = 0
    ok_tables = 0
    for source in data_quality.get("source_diagnostics") or []:
        for diag in (source.get("tables") or {}).values():
            if diag.get("status") == "ok":
                ok_tables += 1
                total_rows += int(diag.get("rows") or 0)
    return f"直连MySQL · {total_rows}行 · {ok_tables}表" if ok_tables else "数据源待核验"


def _trend_svg(monthly: list[dict[str, Any]]) -> str:
    if not monthly:
        return "<div>暂无月度趋势数据。</div>"
    values = [x.get("revpar") for x in monthly if _num(x.get("revpar")) is not None] + [x.get("adr") for x in monthly if _num(x.get("adr")) is not None]
    if not values:
        return "<div>趋势字段未获取。</div>"
    width, height = 700, 260
    left, right, top, bottom = 60, 680, 18, 220
    max_v = max(values) * 1.1
    min_v = min(0, min(values) * 0.9)
    span = max(max_v - min_v, 1)
    def x_at(i: int) -> float:
        return left + (right - left) * (i / max(1, len(monthly) - 1))
    def y_at(v: Any) -> float:
        return bottom - (float(v or 0) - min_v) / span * (bottom - top)
    grid = []
    for idx in range(5):
        y = top + (bottom - top) * idx / 4
        val = max_v - span * idx / 4
        grid.append(f"<line x1='{left}' y1='{y:.1f}' x2='{right}' y2='{y:.1f}' stroke='#e5e7eb' stroke-width='1' stroke-dasharray='4,3'/><text x='{left-8}' y='{y:.1f}' text-anchor='end' dominant-baseline='middle' style='font-size:10px;fill:#6b7280'>{val:.0f}</text>")
    labels = [f"<text x='{x_at(i):.1f}' y='238' text-anchor='middle' style='font-size:10px;fill:#6b7280'>{_esc(item.get('month'))}</text>" for i, item in enumerate(monthly)]
    def line_for(key: str, color: str) -> str:
        pts, circles = [], []
        for i, item in enumerate(monthly):
            v = _num(item.get(key))
            if v is None:
                continue
            x, y = x_at(i), y_at(v)
            pts.append(f"{x:.1f},{y:.1f}")
            circles.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='{color}' opacity='0.9'/><circle cx='{x:.1f}' cy='{y:.1f}' r='2' fill='white'/>")
        return "" if not pts else f"<polyline points='{' '.join(pts)}' fill='none' stroke='{color}' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/>" + "".join(circles)
    return f"<svg viewBox='0 0 {width} {height}' style='width:100%;display:block;height:auto' aria-label='月度经营趋势'>{''.join(grid)}{''.join(labels)}{line_for('revpar', '#2563eb')}{line_for('adr', '#16a34a')}</svg><div class='legend'><span><i style='background:#2563eb'></i>RevPAR</span><span><i style='background:#16a34a'></i>ADR</span></div>"


def _trend_rows(monthly: list[dict[str, Any]]) -> list[list[Any]]:
    return [[item.get("month"), _money(item.get("adr")), _pct(item.get("occupancy_rate")), _money(item.get("revpar")), _money(item.get("room_revenue"))] for item in monthly or []] or [["无", "未获取", "未获取", "未获取", "未获取"]]


def _channel_items(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    funnel_by = {x.get("platform"): x for x in (metrics.get("ota_funnel") or {}).get("by_platform") or []}
    rep_by = {x.get("platform"): x for x in (metrics.get("reputation") or {}).get("by_platform") or []}
    price_by = (metrics.get("price_ladder") or {}).get("by_platform") or {}
    promo_by = (metrics.get("promotion") or {}).get("by_platform") or {}
    platforms = sorted(set(funnel_by) | set(rep_by) | set(price_by) | set(promo_by))
    items = []
    for platform in platforms:
        f = funnel_by.get(platform) or {}
        r = rep_by.get(platform) or {}
        conversion = _num(f.get("payment_conversion_rate"))
        rating = _num(r.get("rating_avg"))
        negative = _num(r.get("negative_review_rate"))
        score = 45
        if conversion is not None:
            score += 25 if conversion >= 0.08 else 16 if conversion >= 0.04 else 6
        if rating is not None:
            score += 20 if rating >= 4.7 else 12 if rating >= 4.4 else 4
        if negative is not None:
            score += 10 if negative <= 0.03 else 4 if negative <= 0.06 else 0
        if price_by.get(platform):
            score += 5
        score = min(100, score)
        if conversion is None:
            suggestion = "补齐该渠道浏览与支付订单，先确认转化口径。"
        elif conversion < 0.04:
            suggestion = "转化偏弱，优先检查价格梯度、首图卖点、评价露出和取消政策。"
        elif rating is not None and rating < 4.5:
            suggestion = "评分偏弱，先处理差评关键词和未回复评论。"
        else:
            suggestion = "渠道基础较稳，继续扩大高转化房型和活动覆盖。"
        items.append({"platform": platform, "score": score, "funnel": f, "reputation": r, "product_count": price_by.get(platform), "promotion_rows": promo_by.get(platform), "suggestion": suggestion})
    return items


def _channel_cards(metrics: dict[str, Any]) -> str:
    items = _channel_items(metrics)
    if not items:
        return "<div>暂无分渠道数据。</div>"
    cards = []
    for item in items:
        p = item["platform"]
        f = item["funnel"]
        r = item["reputation"]
        score = item["score"]
        cards.append(f"""<div class='channel-card' data-channel-section='{_esc(p)}'>
<h3>{_esc(_platform_zh(p))} <span class='status {_status_class(score/100)}'>渠道健康度 {score}/100</span></h3>
<div class='mini-grid'>
<div class='mini'><label>曝光</label><strong>{_esc(_plain_num(f.get('exposure')))}</strong></div>
<div class='mini'><label>浏览</label><strong>{_esc(_plain_num(f.get('views')))}</strong></div>
<div class='mini'><label>支付订单</label><strong>{_esc(_plain_num(f.get('paid_orders')))}</strong></div>
<div class='mini'><label>转化率</label><strong>{_esc(_pct(f.get('payment_conversion_rate')))}</strong></div>
<div class='mini'><label>销售额</label><strong>{_esc(_money(f.get('sales_revenue')))}</strong></div>
<div class='mini'><label>评分 / 差评率</label><strong>{_esc(_plain_num(r.get('rating_avg'), 2))} / {_esc(_pct(r.get('negative_review_rate')))}</strong></div>
</div><div class='suggest'>建议：{_esc(item['suggestion'])}</div></div>""")
    return "<div class='channel-grid'>" + "".join(cards) + "</div>"


def _channel_table(metrics: dict[str, Any]) -> str:
    rows = []
    for item in _channel_items(metrics):
        p = item["platform"]
        f = item["funnel"]
        r = item["reputation"]
        rows.append(f"<tr data-channel-row='{_esc(p)}'><td>{_esc(_platform_zh(p))}</td><td>{item['score']}/100</td><td>{_esc(_plain_num(f.get('exposure')))}</td><td>{_esc(_plain_num(f.get('views')))}</td><td>{_esc(_plain_num(f.get('paid_orders')))}</td><td>{_esc(_money(f.get('sales_revenue')))}</td><td>{_esc(_pct(f.get('payment_conversion_rate')))}</td><td>{_esc(_plain_num(r.get('review_count')))}</td><td>{_esc(_plain_num(r.get('rating_avg'), 2))}</td><td>{_esc(_pct(r.get('negative_review_rate')))}</td><td>{_esc(item['suggestion'])}</td></tr>")
    if not rows:
        rows.append("<tr><td colspan='11'>暂无分渠道数据</td></tr>")
    headers = ["渠道", "健康度", "曝光", "浏览", "支付订单", "销售额", "转化率", "评价数", "评分", "差评率", "诊断建议"]
    return "<table class='data-table'><thead><tr>" + "".join(f"<th>{_esc(h)}</th>" for h in headers) + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _metric_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    op = metrics.get("operating") or {}; funnel = metrics.get("ota_funnel") or {}; rep = metrics.get("reputation") or {}; price = metrics.get("price_ladder") or {}; promo = metrics.get("promotion") or {}; events = metrics.get("nearby_events") or {}
    items = [("RevPAR（每间可售房收入）", _money(op.get("revpar")), "收益锚点"), ("ADR（平均房价）", _money(op.get("adr")), "价格水平"), ("出租率", _pct(op.get("occupancy_rate")), "经营效率"), ("门店收入", _money(op.get("room_revenue")), "经营结果"), ("曝光量", _plain_num(funnel.get("exposure")), "流量入口"), ("浏览量（UV）", _plain_num(funnel.get("views")), "详情页访问"), ("支付订单", _plain_num(funnel.get("paid_orders")), "转化结果"), ("浏览→支付转化率", _pct(funnel.get("payment_conversion_rate")), "转化结果"), ("商品最低价", _money(price.get("min_price")), "价格梯度"), ("活动数", _plain_num(promo.get("activity_count")), "推广覆盖"), ("近期周边活动", _plain_num(events.get("upcoming_60d_count")), "需求事件"), ("平台评分", _plain_num(rep.get("rating_avg"), 2), "信任锚点"), ("差评率", _pct(rep.get("negative_review_rate")), "口碑风险")]
    rows = []
    for label, value, scope in items:
        status = "缺失" if value == "未获取" else "已获取"
        cls = "neutral" if status == "缺失" else "info"
        rows.append([label, value, scope, f"<span class='status {cls}'>{status}</span>"])
    return rows


def _missing_rows(data_quality: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for section, fields in (data_quality.get("missing_fields") or {}).items():
        for field in fields or []:
            rows.append([field, "<span class='status warn'>missing</span>", "补采或检查字段映射", section])
    return rows or [["无关键缺失字段", "<span class='status good'>ok</span>", "继续保持字段采集稳定", "系统计算"]]


def _module_analysis(module_id: str, label: str, rate: float, status: str, metrics: dict[str, Any]) -> str:
    if status == "data_gap":
        return f"{label} 当前为数据缺口。系统没有使用默认值冒充真实结论；请先接入对应表或字段后再评分。"
    pct = int(round(rate * 100)); op = metrics.get("operating") or {}; funnel = metrics.get("ota_funnel") or {}; rep = metrics.get("reputation") or {}
    advice = {"M01": f"当前 RevPAR {_money(op.get('revpar'))}，ADR {_money(op.get('adr'))}，出租率 {_pct(op.get('occupancy_rate'))}。出租率按所选周期聚合口径计算。", "M02": f"曝光 {_plain_num(funnel.get('exposure'))}，浏览 {_plain_num(funnel.get('views'))}。继续拆解曝光来源、自然流量占比和竞争圈排名。", "M03": f"浏览→支付转化率 {_pct(funnel.get('payment_conversion_rate'))}。重点排查曝光到浏览、浏览到支付的断点。", "M04": "梳理全日房、钟点房、团购和活动价，保持清晰价格梯度。", "M05": "当前已接入活动覆盖，但推广成本、点击、推广订单、推广收入、ROI 字段仍需补齐。", "M06": "优化首图、视频、房型卖点、标签入口和权益配置。", "M07": f"平台评分 {_plain_num(rep.get('rating_avg'), 2)}，差评率 {_pct(rep.get('negative_review_rate'))}。将好评关键词反哺页面卖点。", "M08": "建立诊断、整改、验证、复盘闭环，并记录动作完成率。"}.get(module_id, "继续补充数据并形成可验证的整改动作。")
    return f"{label} 得分率 {pct}%。{advice}"


def _module_card(module: dict[str, Any], metrics: dict[str, Any]) -> str:
    module_id = module.get("module_id") or "M??"; label, source = MODULE_LABELS.get(module_id, (module.get("module_name") or module_id, "系统计算")); score = _num(module.get("score")) or 0; weight = _num(module.get("weight")) or 0; rate = _num(module.get("rate")); status = module.get("status") or "ok"
    if rate is None and weight and status != "data_gap": rate = score / weight
    rate_for_bar = max(0, min(1, rate if rate is not None else 0)); pct = int(round(rate_for_bar * 100)); klass = _status_class(status if status == "data_gap" else rate_for_bar)
    reasons = module.get("reasons") or []; reason_html = "".join(f"<span class='reason'>{_esc(reason)}</span>" for reason in reasons[:8]) or "<span class='reason'>系统评分</span>"; color = {"good": "var(--green)", "warn": "var(--amber)", "bad": "var(--red)", "neutral": "#475467"}.get(klass, "var(--blue)"); score_text = "数据缺口" if status == "data_gap" else f"{pct}%"; analysis = _module_analysis(module_id, label, rate_for_bar, status, metrics)
    return f"""<div class='module-card'><div class='module-card-header'><div><div class='mod-id'>{_esc(module_id)} <span style='font-size:11px;color:var(--muted);font-weight:400'>数据: {_esc(source)}</span></div><div class='mod-name'>{_esc(label)}</div></div><div class='module-card-score'><span class='big-score' style='color:{color}'>{_esc(score_text)}</span><span class='of'> / {_esc(score)}/{_esc(weight)}</span></div></div><div class='module-card-bar'><div class='bar-track'><div class='bar-fill {klass}' style='width:{pct}%'></div></div></div><div class='module-card-body'><span class='status {klass}'>{_esc(_status_text(rate, status))}</span>{reason_html}</div><div class='module-card-analysis'>{_esc(analysis)}</div></div>"""


def build_html(result: dict[str, Any]) -> str:
    metrics = result.get("metrics") or {}; operating = metrics.get("operating") or {}; funnel = metrics.get("ota_funnel") or {}; price = metrics.get("price_ladder") or {}; competitors = metrics.get("competitors") or {}; data_quality = result.get("data_quality") or {}; missing_count = _missing_count(data_quality); credibility = max(0, 100 - missing_count * 10); final_score = _num(result.get("final_score")) or 0; risk = str(result.get("risk_level") or "medium").lower(); generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); hotel_name = result.get("hotel_name") or result.get("hotel_id") or "酒店"; platform = result.get("platform") or "multi"; ai_source = _ai_source(result)
    title_meta = f"{_text(hotel_name)}｜{_platform_zh(platform)}｜{_text(result.get('period_start'))} 至 {_text(result.get('period_end'))}｜生成时间：{generated_at}"
    module_cards = "".join(_module_card(m, metrics) for m in result.get("module_scores") or []) or "<div>暂无模块评分。</div>"
    notes = result.get("notes") or []; note_rows = [[f"<span class='status {_status_class(n.get('level'))}'>{_esc(n.get('level'))}</span>", n.get("title"), n.get("evidence"), n.get("suggestion")] for n in notes] or [["<span class='status neutral'>info</span>", "暂无结论", "暂无", "补充数据后重新诊断"]]
    action_items = "".join(f"<li>{_esc(item)}</li>" for item in result.get("actions") or []) or "<li>补齐数据后重新生成诊断。</li>"
    cap_items = []
    if missing_count > 3: cap_items.append("C06 数据可信度封顶：关键字段缺失较多，部分判断按保守规则估计。")
    if result.get("status") != "ok": cap_items.append("数据补采提示：当前报告为 partial，建议补齐缺失字段后复算。")
    if not cap_items: cap_items.append("未触发明显封顶规则；仍建议结合真实运营经验复核。")
    cap_html = "".join(f"<li>{_esc(item)}</li>" for item in cap_items)
    overview_fallback = [f"综合诊断结论：酒店当前处于{_risk_zh(risk)}状态，综合得分 {round(final_score):.0f}/100。", f"数据可信度 {credibility}%，当前缺失字段 {missing_count} 个。", "核心短板请优先查看 M01-M08 模块卡片中的红色、黄色或数据缺口模块。"]
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>酒店 OTA 全面诊断报告</title><style>{HTML_STYLE}</style></head><body>
<header class='app-header'><div class='header-inner'><div class='title-block'><h1>酒店 OTA 全面诊断报告</h1><p>{_esc(title_meta)}</p></div><div class='actions'><div class='channel-selector'><label>选择渠道：</label><select id='channelSelector' onchange='switchChannel(this.value)'><option value='all'>全部渠道</option><option value='meituan'>美团</option><option value='ctrip'>携程</option></select></div><button class='btn primary' onclick='window.print()'>导出报告</button></div></div></header>
<div class='layout'><nav class='sidebar dashboard-only'><a href='#overview'>顶部总览卡片</a><a href='#trend'>月度趋势图</a><a href='#modules'>模块诊断</a><a href='#metrics'>经营指标</a><a href='#funnel'>流量漏斗</a><a href='#channels'>分渠道指标</a><a href='#missing'>补采提示</a><a href='#actions'>诊断结论</a></nav><main>
<section id='overview'><div class='section-head'><div><h2>顶部总览卡片</h2><p>诊断结果概览</p></div><span class='status {_status_class(risk)}'>风险：{_esc(_risk_zh(risk))}</span></div><div class='section-body'><div class='kpi-grid'>{_kpi('总分', f'{round(final_score):.0f} / 100', f'原始分 {final_score:.1f}')}{_kpi('数据可信度', f'{credibility}%', '字段完整度')}{_kpi('风险等级', _risk_zh(risk), '基于模块得分判定', _status_class(risk))}{_kpi('数据来源', _platform_zh(platform), _source_summary(data_quality))}</div><div class='cap-alert'><b>封顶/校准规则</b><span><ul>{cap_html}</ul></span><span class='status warn'>按规则校准</span></div>{_analysis('综合诊断分析', _ai_lines(result, 'overview', overview_fallback), source=ai_source)}</div></section>
<section id='trend'><div class='section-head'><div><h2>月度经营趋势图</h2><p>RevPAR、ADR、出租率、门店收入月度变化</p></div></div><div class='section-body'><div class='two-col'><div class='subpanel'><h3>月度经营趋势</h3><div class='subpanel-content'>{_trend_svg(operating.get('monthly_trend') or [])}</div></div><div class='subpanel'><h3>月度经营数据</h3><div class='subpanel-content'>{_table(['月份','ADR','出租率','RevPAR','门店收入'], _trend_rows(operating.get('monthly_trend') or []))}</div></div></div></div></section>
<section id='modules'><div class='section-head'><div><h2>模块诊断详情</h2><p>8 个诊断模块独立评估；数据没接上的模块显示为数据缺口，不使用默认值冒充结论。</p></div></div><div class='section-body'><div class='module-cards'>{module_cards}</div>{_analysis('模块联动分析', _ai_lines(result, 'modules', ['模块得分来自真实字段计算，建议优先处理低分和 partial 模块。']), source=ai_source)}</div></section>
<section id='metrics'><div class='section-head'><div><h2>经营指标</h2><p>关键经营数据一览</p></div></div><div class='section-body'>{_table(['指标','当前值','口径','状态'], _metric_rows(metrics))}{_analysis('指标解读', _ai_lines(result, 'metrics', [f"RevPAR {_money(operating.get('revpar'))} = ADR {_money(operating.get('adr'))} × 出租率 {_pct(operating.get('occupancy_rate'))}。", "出租率使用所选周期内总售出间夜 / 总可售房晚；如果日表缺少出租率字段，会用 room_nights 或 sold_rooms 除以 room_count 计算。", f"曝光→浏览转化率 {_pct(funnel.get('exposure_to_view_rate'))}，浏览→支付转化率 {_pct(funnel.get('payment_conversion_rate'))}。"]), source=ai_source)}</div></section>
<section id='funnel'><div class='section-head'><div><h2>流量漏斗</h2><p>曝光 → 浏览 → 支付转化路径</p></div></div><div class='section-body'><div class='funnel'><div class='funnel-step'><label>曝光量</label><strong>{_esc(_plain_num(funnel.get('exposure')))}</strong><span>列表页展示次数</span></div><div class='funnel-step'><label>浏览量</label><strong>{_esc(_plain_num(funnel.get('views')))}</strong><span>详情页访问次数</span></div><div class='funnel-step'><label>支付转化率</label><strong>{_esc(_pct(funnel.get('payment_conversion_rate')))}</strong><span>浏览→支付转化</span></div></div>{_analysis('流量漏斗诊断', _ai_lines(result, 'funnel', [f"曝光→浏览：{_pct(funnel.get('exposure_to_view_rate'))}。", f"浏览→支付：{_pct(funnel.get('payment_conversion_rate'))}。", "若曝光充足但支付不足，优先检查价格梯度、评论信任和退改政策。"]), source=ai_source)}</div></section>
<section id='channels'><div class='section-head'><div><h2>分渠道得分与指标</h2><p>选择右上角渠道后，本节卡片和表格会按渠道切换。</p></div></div><div class='section-body'>{_channel_cards(metrics)}{_channel_table(metrics)}{_analysis('分渠道诊断', _ai_lines(result, 'channels', ['分渠道指标按平台拆开，重点比较曝光、浏览、支付订单、销售额、评分和差评率。']), source=ai_source)}</div></section>
<section id='price'><div class='section-head'><div><h2>价格与竞品</h2><p>商品价格梯度、竞品价格和价格跳水风险。</p></div></div><div class='section-body'><div class='kpi-grid'>{_kpi('商品数', price.get('product_count'), 'OTA 商品映射')}{_kpi('最低价', _money(price.get('min_price')), '引流价')}{_kpi('最高价', _money(price.get('max_price')), '价格上沿')}{_kpi('竞品均价', _money(competitors.get('competitor_avg_price')), '竞品参考')}</div>{_analysis('价格诊断解读', _ai_lines(result, 'price', ['价格不是单点判断，需要同时看引流价、全日价、团购价、钟点房价和竞品均价，避免价格体系混乱。']), source=ai_source)}</div></section>
<section id='missing'><div class='section-head'><div><h2>补采提示</h2><p>缺失字段、影响、采集方式；数据缺失不等于经营差，但影响可信度。</p></div></div><div class='section-body'>{_table(['缺失字段','当前状态','处理建议','责任来源'], _missing_rows(data_quality))}{_analysis('数据完整度分析', _ai_lines(result, 'missing', [f'当前缺失字段数为 {missing_count}。缺失字段不等于经营差，但会降低评分可信度。', '所有基于缺失字段的判断均采用保守估计，实际得分可能被低估或高估。']), source=ai_source)}</div></section>
<section id='actions'><div class='section-head'><div><h2>诊断结论与动作建议</h2><p>只输出营销建议，不执行调价和审批。</p></div></div><div class='section-body'><h3>问题结论</h3>{_table(['等级','标题','证据','建议'], note_rows)}<h3>动作建议</h3><ol>{action_items}</ol>{_analysis('动作优先级分析', _ai_lines(result, 'actions', ['先处理影响转化和信任的动作，再处理推广 ROI 数据补采。']), source=ai_source)}</div></section>
</main></div><script>function switchChannel(value){{document.querySelectorAll('[data-channel-section]').forEach(function(el){{el.classList.toggle('hidden-by-channel',value!=='all'&&el.getAttribute('data-channel-section')!==value);}});document.querySelectorAll('[data-channel-row]').forEach(function(el){{el.classList.toggle('hidden-by-channel',value!=='all'&&el.getAttribute('data-channel-row')!==value);}});}}document.addEventListener('DOMContentLoaded',function(){{var s=document.getElementById('channelSelector');if(s){{switchChannel(s.value||'all');}}}});</script></body></html>"""


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "report.json"
    md_path = path / "report.md"
    html_path = path / "report.html"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(result), encoding="utf-8")
    html_path.write_text(build_html(result), encoding="utf-8")
    return {"report_json": str(json_path), "report_markdown": str(md_path), "report_html": str(html_path)}
