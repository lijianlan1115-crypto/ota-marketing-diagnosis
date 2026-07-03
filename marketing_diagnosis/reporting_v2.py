from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

CSS = """
:root{--bg:#f5f7fb;--panel:#fff;--ink:#182230;--muted:#667085;--line:#d9dee8;--soft:#eef2f7;--blue:#2563eb;--green:#168a4a;--amber:#b7791f;--red:#c2413a;--shadow:0 12px 34px rgba(16,24,40,.08);--radius:14px}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at top left,#eaf1ff 0,#f5f7fb 34%,#f7f8fb 100%);color:var(--ink);font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif;font-size:14px;line-height:1.52}.top{position:sticky;top:0;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(12px);z-index:20}.top-inner{max-width:1480px;margin:0 auto;padding:16px 24px;display:flex;justify-content:space-between;gap:16px;align-items:center}.top h1{margin:0;font-size:24px}.meta{color:var(--muted);font-size:13px;margin-top:4px}.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.selectbox{display:flex;gap:8px;align-items:center;border:1px solid var(--line);border-radius:10px;background:#f8fafc;padding:7px 11px}.selectbox label{font-weight:800;color:#475467}.selectbox select{height:30px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}.btn{height:36px;border:1px solid #182230;background:#182230;color:#fff;border-radius:10px;padding:0 14px;font-weight:800;cursor:pointer}.layout{max-width:1480px;margin:0 auto;padding:22px 24px 56px;display:grid;grid-template-columns:230px minmax(0,1fr);gap:22px}.side{position:sticky;top:88px;align-self:start;background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden}.side a{display:block;padding:11px 15px;border-bottom:1px solid var(--soft);text-decoration:none;color:#344054;font-weight:800;font-size:13px}.side a:hover{background:#eef4ff;color:var(--blue)}main{display:grid;gap:20px}.card{background:rgba(255,255,255,.98);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden}.head{padding:17px 20px;border-bottom:1px solid var(--soft);display:flex;justify-content:space-between;gap:12px;background:linear-gradient(180deg,#fff,#fbfcff)}.head h2{margin:0;font-size:18px}.head p{margin:6px 0 0;color:var(--muted);font-size:13px}.body{padding:20px}.badge{display:inline-flex;align-items:center;min-height:24px;padding:0 9px;border-radius:999px;font-size:12px;font-weight:900;white-space:nowrap}.good{color:var(--green);background:#e8f5ee}.warn{color:var(--amber);background:#fff4dc}.bad{color:var(--red);background:#fdebea}.info{color:var(--blue);background:#eaf1ff}.neutral{color:#475467;background:#eef1f5}.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px}.kpi,.mini{border:1px solid var(--line);border-radius:12px;padding:14px;background:linear-gradient(180deg,#fff,#fbfcfe)}.kpi label,.mini label{display:block;color:var(--muted);font-size:12px;font-weight:900}.kpi strong{display:block;margin-top:8px;font-size:29px;line-height:1}.kpi span{display:block;margin-top:8px;color:var(--muted);font-size:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.panel{border:1px solid var(--line);border-radius:12px;background:#fff;overflow:hidden;margin-bottom:14px}.panel h3{margin:0;padding:12px 14px;border-bottom:1px solid var(--soft);background:#fafbfc;font-size:15px}.panel .pbody{padding:14px}.table-wrap{overflow:auto}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:10px 11px;border-bottom:1px solid var(--soft);text-align:left;vertical-align:top}.table th{background:#f8fafc;color:#475467;font-size:12px;font-weight:900}.analysis{margin-top:16px;border:1px solid #c7d2fe;border-left:4px solid #6366f1;border-radius:12px;background:#eef2ff;overflow:hidden}.analysis summary{cursor:pointer;padding:11px 14px;font-weight:900;color:#4338ca;display:flex;gap:8px;align-items:center}.analysis .txt{padding:0 16px 14px;color:#312e81}.analysis p{margin:8px 0}.source-block{margin:0 0 18px}.source-title{display:flex;align-items:center;gap:8px;margin:0 0 10px;font-size:16px;font-weight:900}.source-grid,.channel-grid,.quad-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.module,.chan,.quad{border:1px solid var(--line);border-radius:13px;background:#fff;overflow:hidden}.module-top{padding:14px 16px 8px;display:flex;justify-content:space-between;gap:10px}.mid{font-size:12px;font-weight:900;color:var(--muted)}.mname{font-size:16px;font-weight:900;margin-top:2px}.score{font-size:26px;font-weight:900}.bar{height:8px;background:#e9edf3;border-radius:999px;overflow:hidden;margin:0 16px 10px}.fill{height:100%;background:var(--blue)}.fill.good{background:var(--green)}.fill.warn{background:var(--amber)}.fill.bad{background:var(--red)}.module-body{padding:0 16px 14px;color:#475467}.tag{display:inline-block;margin:3px 4px 0 0;padding:2px 8px;background:#f2f5f9;border-radius:6px;font-size:12px}.chan,.quad{padding:14px}.chan h3,.quad h3{margin:0 0 10px;font-size:16px}.mini-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.mini strong{display:block;margin-top:4px;font-size:18px}.flow{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;align-items:stretch}.flow-step{border:1px solid var(--line);border-radius:10px;background:#fbfcfe;padding:12px}.flow-step label{display:block;color:var(--muted);font-size:12px;font-weight:900}.flow-step strong{display:block;margin-top:6px;font-size:22px}.flow-step span{display:block;margin-top:4px;color:var(--muted);font-size:12px}.callout{border:1px solid #f0cd7a;background:#fff8e6;border-radius:12px;padding:12px 14px;margin-top:12px;color:#7a4d08}.pill-list{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.matrix-note{font-size:12px;color:var(--muted);margin-top:8px}.hidden{display:none!important}@media(max-width:980px){.layout{grid-template-columns:1fr;padding:14px}.side{position:static;display:grid;grid-template-columns:repeat(2,1fr)}.grid4,.two,.source-grid,.channel-grid,.mini-grid,.flow,.quad-grid{grid-template-columns:1fr}.top-inner{display:block}.actions{margin-top:10px}}@media print{.top,.side{display:none}.layout{display:block;padding:0}.card{box-shadow:none;border:0;background:#fff}.analysis{break-inside:avoid}}
"""


def _n(v: Any) -> float | None:
    try:
        if v in (None, ""):
            return None
        x = float(v)
        return None if x != x else x
    except Exception:
        return None


def _e(v: Any) -> str:
    return html.escape("未获取" if v is None else str(v), quote=True)


def _pct(v: Any) -> str:
    x = _n(v)
    return "未获取" if x is None else f"{x:.1%}"


def _money(v: Any) -> str:
    x = _n(v)
    return "未获取" if x is None else f"¥{x:,.1f}"


def _num(v: Any, d: int = 0) -> str:
    x = _n(v)
    return "未获取" if x is None else f"{x:,.{d}f}"


def _zh(v: Any) -> str:
    return {"all":"全部","multi":"多渠道","pms":"PMS","meituan":"美团","ctrip":"携程","shared":"系统/数据","high":"高风险","medium":"中风险","low":"低风险","高":"高","中":"中","低":"低"}.get(str(v or "").lower(), str(v or "未获取"))


def _cls(v: Any) -> str:
    if isinstance(v, str):
        return {"high":"bad","medium":"warn","low":"good","高":"bad","中":"warn","低":"good","ok":"good","partial":"warn","data_gap":"neutral"}.get(v.lower(), "neutral")
    x = _n(v)
    if x is None:
        return "neutral"
    return "good" if x >= 0.8 else "warn" if x >= 0.6 else "bad"


def _ai(result: dict[str, Any], key: str, fallback: list[str]) -> list[str]:
    v = (result.get("ai_analysis") or {}).get(key)
    if isinstance(v, list):
        out = [str(x).strip() for x in v if str(x).strip()]
        return out or fallback
    if isinstance(v, str) and v.strip():
        return [x.strip() for x in v.splitlines() if x.strip()] or fallback
    return fallback


def _analysis(result: dict[str, Any], title: str, key: str, fallback: list[str]) -> str:
    ps = "".join(f"<p>{_e(p)}</p>" for p in _ai(result, key, fallback))
    return f"<details class='analysis' open><summary><span class='badge info'>AI分析</span> {_e(title)}</summary><div class='txt'>{ps}</div></details>"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    h = "".join(f"<th>{_e(x)}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{x if str(x).startswith('<') else _e(x)}</td>" for x in r) + "</tr>" for r in rows)
    return f"<div class='table-wrap'><table class='table'><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>"


def _kpi(label: str, value: Any, hint: str = "", cls: str = "") -> str:
    c = f" class='{cls}'" if cls else ""
    return f"<div class='kpi'><label>{_e(label)}</label><strong{c}>{_e(value)}</strong><span>{_e(hint)}</span></div>"


def _missing_count(dq: dict[str, Any]) -> int:
    return sum(len(v or []) for v in (dq.get("missing_fields") or {}).values())


def _source_summary(dq: dict[str, Any]) -> str:
    rows = tables = 0
    for src in dq.get("source_diagnostics") or []:
        for diag in (src.get("tables") or {}).values():
            if diag.get("status") == "ok":
                tables += 1
                rows += int(diag.get("rows") or 0)
    return f"直连MySQL · {rows}行 · {tables}表" if tables else "数据源待核验"


def _trend_rows(monthly: list[dict[str, Any]]) -> list[list[Any]]:
    return [[x.get("month"), _money(x.get("adr")), _pct(x.get("occupancy_rate")), _money(x.get("revpar")), _money(x.get("room_revenue")), _pct(x.get("revpar_mom"))] for x in monthly or []] or [["无", "未获取", "未获取", "未获取", "未获取", "未获取"]]


def _trend_svg(monthly: list[dict[str, Any]]) -> str:
    if not monthly:
        return "暂无月度趋势数据。"
    values = [v for item in monthly for v in [_n(item.get("adr")), _n(item.get("revpar"))] if v is not None]
    if not values:
        return "趋势字段未获取。"
    w, h, left, right, top, bottom = 720, 260, 58, 690, 20, 218
    max_v = max(values) * 1.12
    min_v = min(0, min(values) * 0.9)
    span = max(max_v - min_v, 1)
    def x_at(i: int) -> float:
        return left + (right - left) * i / max(1, len(monthly) - 1)
    def y_at(v: float) -> float:
        return bottom - (v - min_v) / span * (bottom - top)
    grid = []
    for i in range(5):
        y = top + (bottom - top) * i / 4
        val = max_v - span * i / 4
        grid.append(f"<line x1='{left}' y1='{y:.1f}' x2='{right}' y2='{y:.1f}' stroke='#e5e7eb' stroke-dasharray='4,3'/><text x='{left-8}' y='{y:.1f}' text-anchor='end' dominant-baseline='middle' style='font-size:10px;fill:#667085'>{val:.0f}</text>")
    labels = "".join(f"<text x='{x_at(i):.1f}' y='238' text-anchor='middle' style='font-size:10px;fill:#667085'>{_e(item.get('month'))}</text>" for i, item in enumerate(monthly))
    def line(key: str, color: str) -> str:
        pts, dots = [], []
        for i, item in enumerate(monthly):
            v = _n(item.get(key))
            if v is None:
                continue
            x, y = x_at(i), y_at(v)
            pts.append(f"{x:.1f},{y:.1f}")
            dots.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='{color}'/><circle cx='{x:.1f}' cy='{y:.1f}' r='2' fill='white'/>")
        return "" if not pts else f"<polyline points='{' '.join(pts)}' fill='none' stroke='{color}' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/>" + "".join(dots)
    return f"<svg viewBox='0 0 {w} {h}' style='width:100%;height:auto'>{''.join(grid)}{labels}{line('revpar','#2563eb')}{line('adr','#168a4a')}</svg><div class='meta'>蓝线 RevPAR，绿线 ADR</div>"


def _trend(monthly: list[dict[str, Any]]) -> str:
    return f"<div class='two'><div class='panel'><h3>月度趋势线</h3><div class='pbody'>{_trend_svg(monthly)}</div></div><div class='panel'><h3>月度经营明细</h3><div class='pbody'>{_table(['月份','ADR','出租率','RevPAR','门店收入','RevPAR环比'], _trend_rows(monthly))}</div></div></div>"


def _platform_price(price: dict[str, Any], platform: str) -> dict[str, Any]:
    data = (price.get("by_platform") or {}).get(platform)
    if isinstance(data, dict):
        return data
    if data:
        return {"product_count": data}
    return {}


def _platform_promo(promo: dict[str, Any], platform: str) -> dict[str, Any]:
    data = (promo.get("by_platform") or {}).get(platform)
    if isinstance(data, dict):
        return data
    if data:
        return {"activity_count": data, "activity_product_count": data}
    return {}


def _channel_items(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    funnel_by = {x.get("platform"): x for x in (metrics.get("ota_funnel") or {}).get("by_platform") or []}
    rep_by = {x.get("platform"): x for x in (metrics.get("reputation") or {}).get("by_platform") or []}
    price = metrics.get("price_ladder") or {}
    promo = metrics.get("promotion") or {}
    platforms = sorted(set(funnel_by) | set(rep_by) | set((price.get("by_platform") or {}).keys()) | set((promo.get("by_platform") or {}).keys()))
    items = []
    for p in platforms:
        f = funnel_by.get(p) or {}
        r = rep_by.get(p) or {}
        pp = _platform_price(price, p)
        pr = _platform_promo(promo, p)
        conv = _n(f.get("payment_conversion_rate"))
        rating = _n(r.get("rating_avg"))
        neg = _n(r.get("negative_review_rate"))
        score = 45
        if conv is not None:
            score += 25 if conv >= 0.08 else 16 if conv >= 0.04 else 6
        if rating is not None:
            score += 20 if rating >= 4.7 else 12 if rating >= 4.4 else 4
        if neg is not None:
            score += 10 if neg <= 0.03 else 4 if neg <= 0.06 else 0
        if pp.get("product_count"):
            score += 5
        score = min(100, score)
        sug = "补齐该渠道浏览与支付订单，先确认转化口径。" if conv is None else "二转偏弱，优先检查价格梯度、首图卖点、评价露出和取消政策。" if conv < 0.04 else "评分偏弱，先处理差评关键词和未回复评论。" if rating is not None and rating < 4.5 else "渠道基础较稳，继续扩大高转化房型和活动覆盖。"
        items.append({"platform": p, "score": score, "funnel": f, "reputation": r, "price": pp, "promotion": pr, "product_count": pp.get("product_count"), "promotion_rows": (pr.get("activity_count") or 0) + (pr.get("activity_product_count") or 0), "suggestion": sug})
    return items


def _overview_blocks(metrics: dict[str, Any], dq: dict[str, Any]) -> str:
    op = metrics.get("operating") or {}
    cards = [f"<div class='chan' data-source='pms'><h3>PMS经营底盘 <span class='badge {_cls(op.get('occupancy_rate') or 0)}'>出租率 {_pct(op.get('occupancy_rate'))}</span></h3><div class='mini-grid'><div class='mini'><label>RevPAR</label><strong>{_e(_money(op.get('revpar')))}</strong></div><div class='mini'><label>ADR</label><strong>{_e(_money(op.get('adr')))}</strong></div><div class='mini'><label>日均收入</label><strong>{_e(_money(op.get('avg_daily_revenue')))}</strong></div></div><div class='meta'>PMS口径用于判断经营底盘，不和OTA渠道混算。</div></div>"]
    for item in _channel_items(metrics):
        p, f = item["platform"], item["funnel"]
        cards.append(f"<div class='chan' data-source='{_e(p)}'><h3>{_e(_zh(p))}概览 <span class='badge {_cls(item['score']/100)}'>{item['score']}/100</span></h3><div class='mini-grid'><div class='mini'><label>订单占比</label><strong>{_e(_pct(f.get('order_share')))}</strong></div><div class='mini'><label>销售额占比</label><strong>{_e(_pct(f.get('revenue_share')))}</strong></div><div class='mini'><label>客单价</label><strong>{_e(_money(f.get('avg_order_value')))}</strong></div></div><div class='meta'>{_e(item['suggestion'])}</div></div>")
    cards.append(f"<div class='chan' data-source='shared'><h3>系统/数据 <span class='badge neutral'>字段核验</span></h3><div class='mini-grid'><div class='mini'><label>数据状态</label><strong>{_e(dq.get('status'))}</strong></div><div class='mini'><label>缺字段数</label><strong>{_missing_count(dq)}</strong></div><div class='mini'><label>空模块</label><strong>{len(dq.get('empty_sections') or {})}</strong></div></div><div class='meta'>数据缺口只影响可信度，不直接等于经营差。</div></div>")
    return "<div class='channel-grid'>" + "".join(cards) + "</div>"


def _flow_blocks(metrics: dict[str, Any]) -> str:
    cards = []
    for item in _channel_items(metrics):
        p, f = item["platform"], item["funnel"]
        status = "完整" if f.get("exposure") is not None and f.get("views") is not None and f.get("paid_orders") is not None else "部分"
        cards.append(f"<div class='panel' data-source='{_e(p)}'><h3>渠道：{_e(_zh(p))} <span class='badge {_cls(item['score']/100)}'>{_e(status)}</span></h3><div class='pbody'><div class='flow'><div class='flow-step'><label>入口</label><strong>{_e(_num(f.get('exposure')))}</strong><span>曝光量 / 列表页展示次数</span></div><div class='flow-step'><label>访问</label><strong>{_e(_num(f.get('views')))}</strong><span>浏览量 / 详情页访问人数</span></div><div class='flow-step'><label>点击效率</label><strong>{_e(_pct(f.get('exposure_to_view_rate')))}</strong><span>曝光→浏览</span></div><div class='flow-step'><label>转化</label><strong>{_e(_pct(f.get('payment_conversion_rate')))}</strong><span>浏览→支付，订单 {_e(_num(f.get('paid_orders')))}</span></div></div></div></div>")
    return "".join(cards) if cards else "暂无分渠道漏斗数据。"


def _channel_cards(metrics: dict[str, Any]) -> str:
    cards = []
    for item in _channel_items(metrics):
        p, f, r, score = item["platform"], item["funnel"], item["reputation"], item["score"]
        cards.append(f"<div class='chan' data-source='{_e(p)}'><h3>{_e(_zh(p))} <span class='badge {_cls(score/100)}'>渠道健康度 {score}/100</span></h3><div class='mini-grid'><div class='mini'><label>曝光</label><strong>{_e(_num(f.get('exposure')))}</strong></div><div class='mini'><label>浏览</label><strong>{_e(_num(f.get('views')))}</strong></div><div class='mini'><label>支付订单</label><strong>{_e(_num(f.get('paid_orders')))}</strong></div><div class='mini'><label>转化率</label><strong>{_e(_pct(f.get('payment_conversion_rate')))}</strong></div><div class='mini'><label>客单价</label><strong>{_e(_money(f.get('avg_order_value')))}</strong></div><div class='mini'><label>评分/差评率</label><strong>{_e(_num(r.get('rating_avg'),2))} / {_e(_pct(r.get('negative_review_rate')))}</strong></div></div><div class='meta'>建议：{_e(item['suggestion'])}</div></div>")
    return "<div class='channel-grid'>" + "".join(cards) + "</div>" if cards else "暂无分渠道数据。"


def _channel_table(metrics: dict[str, Any]) -> str:
    rows = []
    for item in _channel_items(metrics):
        p, f, r = item["platform"], item["funnel"], item["reputation"]
        rows.append(f"<tr data-source-row='{_e(p)}'><td>{_e(_zh(p))}</td><td>{item['score']}/100</td><td>{_e(_num(f.get('exposure')))}</td><td>{_e(_num(f.get('views')))}</td><td>{_e(_num(f.get('paid_orders')))}</td><td>{_e(_money(f.get('sales_revenue')))}</td><td>{_e(_pct(f.get('payment_conversion_rate')))}</td><td>{_e(_pct(f.get('revenue_share')))}</td><td>{_e(_money(f.get('avg_order_value')))}</td><td>{_e(_num(r.get('rating_avg'),2))}</td><td>{_e(_pct(r.get('negative_review_rate')))}</td><td>{_e(item['suggestion'])}</td></tr>")
    if not rows:
        rows.append("<tr><td colspan='12'>暂无分渠道数据</td></tr>")
    return "<table class='table'><thead><tr>" + "".join(f"<th>{_e(h)}</th>" for h in ["渠道","健康度","曝光","浏览","支付订单","销售额","转化率","销售额占比","客单价","评分","差评率","建议"]) + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _contribution_matrix(metrics: dict[str, Any]) -> str:
    rows = []
    for item in _channel_items(metrics):
        p, f, r = item["platform"], item["funnel"], item["reputation"]
        role = "主力渠道" if (_n(f.get("order_share")) or 0) >= 0.5 or (_n(f.get("revenue_share")) or 0) >= 0.5 else "补充渠道"
        if (_n(f.get("payment_conversion_rate")) is None) and not f.get("paid_orders"):
            role = "待补数据"
        rows.append([_zh(p), _pct(f.get("exposure_share")), _pct(f.get("view_share")), _pct(f.get("order_share")), _pct(f.get("revenue_share")), _money(f.get("avg_order_value")), _pct(f.get("payment_conversion_rate")), _num(r.get("rating_avg"), 2), role])
    return _table(["渠道","曝光占比","浏览占比","订单占比","销售额占比","客单价","二转","评分","判断"], rows or [["无","未获取","未获取","未获取","未获取","未获取","未获取","未获取","待补数据"]])


def _quadrant_blocks(metrics: dict[str, Any]) -> str:
    items = _channel_items(metrics)
    views = [_n(x["funnel"].get("views")) or 0 for x in items]
    convs = [_n(x["funnel"].get("payment_conversion_rate")) for x in items if _n(x["funnel"].get("payment_conversion_rate")) is not None]
    traffic_bar = (sum(views) / len(views)) if views else 0
    conv_bar = (sum(convs) / len(convs)) if convs else 0.04
    buckets = {"主力放大": [], "加曝光": [], "修转化": [], "暂缓投放": []}
    for item in items:
        f = item["funnel"]
        high_traffic = (_n(f.get("views")) or 0) >= traffic_bar
        high_conv = (_n(f.get("payment_conversion_rate")) or 0) >= conv_bar
        label = "主力放大" if high_traffic and high_conv else "加曝光" if (not high_traffic and high_conv) else "修转化" if high_traffic and not high_conv else "暂缓投放"
        buckets[label].append(_zh(item["platform"]))
    explain = {"主力放大":"高流量高转化，适合扩大活动和预算。", "加曝光":"低流量高转化，优先补自然流量或广告曝光。", "修转化":"高流量低转化，优先查页面、价格、口碑。", "暂缓投放":"低流量低转化，先补基础再投放。"}
    cards = []
    for label, names in buckets.items():
        pills = "".join(f"<span class='badge info'>{_e(n)}</span>" for n in names) if names else "<span class='badge neutral'>暂无渠道</span>"
        cards.append(f"<div class='quad'><h3>{_e(label)}</h3><div class='pill-list'>{pills}</div><div class='matrix-note'>{_e(explain[label])}</div></div>")
    return f"<div class='quad-grid'>{''.join(cards)}</div><div class='matrix-note'>分界线：浏览量均值 {_num(traffic_bar)}，二转均值 {_pct(conv_bar)}。样本少时仅作运营排查线索。</div>"


def _revpar_decomposition(metrics: dict[str, Any]) -> str:
    op = metrics.get("operating") or {}
    adr, occ, revpar = _n(op.get("adr")), _n(op.get("occupancy_rate")), _n(op.get("revpar"))
    if adr is None or occ is None:
        diagnosis, level = "ADR 或出租率缺失，无法拆解 RevPAR。", "neutral"
    elif adr >= 180 and occ < 0.65:
        diagnosis, level = "房价不低但出租率偏弱，优先排查流量、转化、价格承接和口碑。", "warn"
    elif adr < 160 and occ >= 0.75:
        diagnosis, level = "出租率尚可但 ADR 偏低，可能存在提价或产品升级空间。", "good"
    elif adr < 160 and occ < 0.65:
        diagnosis, level = "ADR 和出租率同时偏弱，应从渠道曝光、页面包装、价格体系和口碑一起排查。", "bad"
    else:
        diagnosis, level = "ADR 与出租率处于相对均衡区间，继续看渠道结构和远期价格。", "info"
    rows = [["ADR", _money(adr), "平均房价", "价格水平"], ["出租率", _pct(occ), "售出间夜 ÷ 可售房晚", "入住效率"], ["RevPAR", _money(revpar), "ADR × 出租率", "收益结果"], ["拆解判断", f"<span class='badge {level}'>{_e(diagnosis)}</span>", "规则诊断", "优先级线索"]]
    return _table(["项目","值","口径","判断"], rows)


def _opportunity_estimates(metrics: dict[str, Any]) -> str:
    rows = []
    for item in _channel_items(metrics):
        p, f = item["platform"], item["funnel"]
        views, exposure, conv, evr, aov = _n(f.get("views")), _n(f.get("exposure")), _n(f.get("payment_conversion_rate")), _n(f.get("exposure_to_view_rate")), _n(f.get("avg_order_value"))
        new_orders_from_conv = views * conv * 0.10 if views is not None and conv is not None else None
        new_rev_from_conv = new_orders_from_conv * aov if new_orders_from_conv is not None and aov is not None else None
        new_orders_from_exp = exposure * 0.20 * evr * conv if exposure is not None and evr is not None and conv is not None else None
        new_rev_from_exp = new_orders_from_exp * aov if new_orders_from_exp is not None and aov is not None else None
        rows.append([_zh(p), "二转提升10%", _num(new_orders_from_conv, 1), _money(new_rev_from_conv), "测算：浏览量不变，二转提升10%"])
        rows.append([_zh(p), "曝光提升20%", _num(new_orders_from_exp, 1), _money(new_rev_from_exp), "测算：一转和二转不变"])
    return _table(["渠道","机会假设","预计新增订单","预计新增销售额","说明"], rows or [["无","待补数据","未获取","未获取","需要曝光、浏览、转化和客单价"]])


def _price_ladder_table(metrics: dict[str, Any]) -> str:
    rows = []
    price = metrics.get("price_ladder") or {}
    competitors = metrics.get("competitors") or {}
    rows.append(["全渠道", _num(price.get("product_count")), _money(price.get("min_price")), _money(price.get("max_price")), _money(price.get("price_span")), _num(price.get("group_buy_count")), _num(price.get("hour_room_count")), "看整体价格跨度和引流入口"])
    for item in _channel_items(metrics):
        p = item["platform"]
        pp = item.get("price") or {}
        comp = (competitors.get("by_platform") or {}).get(p) or {}
        span = _n(pp.get("price_span"))
        judgement = "价格跨度偏大，复核团购/钟点房/全日价" if span is not None and span > 150 else "价格梯度待结合竞对和远期价复核"
        if not pp.get("min_price"):
            judgement = "缺少渠道价格字段，无法判断引流价"
        rows.append([_zh(p), _num(pp.get("product_count")), _money(pp.get("min_price")), _money(pp.get("max_price")), _money(pp.get("price_span")), _num(pp.get("group_buy_count")), _num(pp.get("hour_room_count")), f"{judgement}；竞品均价 {_money(comp.get('competitor_avg_price'))}"])
    return _table(["渠道","商品数","最低价","最高价","价格跨度","团购数","钟点房数","判断"], rows)


def _price_blocks(metrics: dict[str, Any]) -> str:
    price = metrics.get("price_ladder") or {}
    competitors = metrics.get("competitors") or {}
    cards = [f"<div class='chan' data-source='shared'><h3>全渠道价格 <span class='badge info'>汇总</span></h3><div class='mini-grid'><div class='mini'><label>商品数</label><strong>{_e(_num(price.get('product_count')))}</strong></div><div class='mini'><label>最低价</label><strong>{_e(_money(price.get('min_price')))}</strong></div><div class='mini'><label>最高价</label><strong>{_e(_money(price.get('max_price')))}</strong></div><div class='mini'><label>价格跨度</label><strong>{_e(_money(price.get('price_span')))}</strong></div><div class='mini'><label>团购商品</label><strong>{_e(_num(price.get('group_buy_count')))}</strong></div><div class='mini'><label>钟点房</label><strong>{_e(_num(price.get('hour_room_count')))}</strong></div></div></div>"]
    for item in _channel_items(metrics):
        p = item["platform"]
        pp = item.get("price") or {}
        comp = (competitors.get("by_platform") or {}).get(p) or {}
        cards.append(f"<div class='chan' data-source='{_e(p)}'><h3>{_e(_zh(p))}价格房型 <span class='badge neutral'>渠道</span></h3><div class='mini-grid'><div class='mini'><label>商品数</label><strong>{_e(_num(pp.get('product_count')))}</strong></div><div class='mini'><label>最低价</label><strong>{_e(_money(pp.get('min_price')))}</strong></div><div class='mini'><label>最高价</label><strong>{_e(_money(pp.get('max_price')))}</strong></div><div class='mini'><label>房型数</label><strong>{_e(_num(pp.get('room_type_count')))}</strong></div><div class='mini'><label>竞品均价</label><strong>{_e(_money(comp.get('competitor_avg_price')))}</strong></div><div class='mini'><label>价差</label><strong>{_e(_money(comp.get('own_min_price_vs_competitor_avg_gap')))}</strong></div></div><div class='meta'>渠道价格要和外网展示、低价日历、团购/钟点房/远期价一起复核。</div></div>")
    return "<div class='channel-grid'>" + "".join(cards) + "</div>"


def _promotion_blocks(metrics: dict[str, Any]) -> str:
    promo = metrics.get("promotion") or {}
    panels = []
    for item in _channel_items(metrics):
        p = item["platform"]
        pr = item.get("promotion") or {}
        detail = "已接入活动覆盖，ROI明细未补齐" if pr else "未补齐"
        rows = [["推广订单金额", "未获取", "推广订单金额", "推广产出"], ["推广花费", "未获取", "推广花费", "推广成本"], ["ROI", "未获取", "订单金额 ÷ 推广花费", "推广效率"], ["活动数", _num(pr.get("activity_count")), "活动覆盖", "活动基础"], ["活动商品明细", _num(pr.get("activity_product_count")), "活动商品数", "商品覆盖"], ["推广明细", detail, "推广明细完整度", "影响封顶规则"]]
        panels.append(f"<div class='panel' data-source='{_e(p)}'><h3>{_e(_zh(p))} 推广效率</h3><div class='pbody'>{_table(['指标','值','口径','判断'], rows)}</div></div>")
    if not panels:
        rows = [["推广订单金额", "未获取", "推广订单金额", "推广产出"], ["推广花费", "未获取", "推广花费", "推广成本"], ["ROI", "未获取", "订单金额 ÷ 推广花费", "推广效率"], ["推广明细", "未补齐", "推广明细完整度", "影响封顶规则"]]
        panels.append(f"<div class='panel'><h3>推广效率</h3><div class='pbody'>{_table(['指标','值','口径','判断'], rows)}</div></div>")
    missing = ", ".join(promo.get("missing_roi_fields") or ["promo_cost", "promo_clicks", "promo_orders", "promo_revenue", "promo_roi"])
    return "".join(panels) + f"<div class='callout'>当前预留推广效率口径：{_e(missing)}。字段未接入时，只能判断活动覆盖，不能判断投放 ROI。</div>"


def _page_blocks(metrics: dict[str, Any]) -> str:
    panels = []
    for item in _channel_items(metrics):
        p = item["platform"]
        pp = item.get("price") or {}
        product_status = "已接入商品/房型基础" if pp.get("product_count") else "未知"
        rows = [["图片质量", "未知", "页面基础", "页面基础"], ["视频状态", "未知", "内容完整度", "内容完整度"], ["房型卖点", product_status, "商品名/房型映射", "转化支撑"], ["入口标签", "未知", "搜索和入口质量", "搜索入口"]]
        panels.append(f"<div class='panel' data-source='{_e(p)}'><h3>{_e(_zh(p))} 页面展示</h3><div class='pbody'>{_table(['项目','状态','来源','判断'], rows)}</div></div>")
    return "".join(panels) if panels else "暂无渠道页面数据。"


def _reputation_blocks(metrics: dict[str, Any]) -> str:
    panels = []
    rep_by = {x.get("platform"): x for x in (metrics.get("reputation") or {}).get("by_platform") or []}
    for item in _channel_items(metrics):
        p = item["platform"]
        r = rep_by.get(p) or item.get("reputation") or {}
        total = _n(r.get("review_count")) or 0
        negative = _n(r.get("negative_review_count"))
        if negative is None and r.get("negative_review_rate") is not None:
            negative = total * (_n(r.get("negative_review_rate")) or 0)
        positive = max(0, total - (negative or 0)) if total else None
        rows = [["平台评分", _num(r.get("rating_avg"), 2), "平台评分", "信任锚点"], ["总评价数", _num(total), "点评数量", "评价规模"], ["好评数", _num(positive), "总评 - 差评", "正向反馈"], ["差评数", _num(negative), "差评数", "口碑风险"], ["差评率", _pct(r.get("negative_review_rate")), "差评数 ÷ 总评", "口碑风险"], ["未回复评价", _num(r.get("unreplied_review_count")), "未回复评价数", "服务响应"]]
        panels.append(f"<div class='panel' data-source='{_e(p)}'><h3>{_e(_zh(p))} 口碑</h3><div class='pbody'>{_table(['指标','值','口径','判断'], rows)}</div></div>")
    return "".join(panels) if panels else "暂无口碑数据。"


def _module_map(ms: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {x.get("module_id"): x for x in ms or []}


def _src_module(source: str, mid: str, metrics: dict[str, Any], ms: list[dict[str, Any]]) -> dict[str, Any]:
    base = _module_map(ms).get(mid, {})
    weight = _n(base.get("weight")) or 10
    status = base.get("status") or "ok"
    reasons, rate = [], None
    if source == "pms":
        op = metrics.get("operating") or {}
        occ, revpar = _n(op.get("occupancy_rate")), _n(op.get("revpar"))
        if mid == "M01":
            rate = 0.9 if occ and occ >= 0.8 else 0.7 if occ and occ >= 0.65 else 0.45 if occ is not None else None
            if revpar is not None:
                rate = min(0.98, (rate or 0.5) + (0.08 if revpar >= 120 else 0.03 if revpar >= 90 else -0.04))
            reasons = [f"出租率 {_pct(occ)}", f"RevPAR {_money(revpar)}", f"ADR {_money(op.get('adr'))}"]
        else:
            status, reasons = "data_gap", ["该模块不是 PMS 主口径"]
    elif source in {"meituan", "ctrip"}:
        item = next((x for x in _channel_items(metrics) if x.get("platform") == source), None) or {}
        f, r = item.get("funnel") or {}, item.get("reputation") or {}
        conv, rating, neg = _n(f.get("payment_conversion_rate")), _n(r.get("rating_avg")), _n(r.get("negative_review_rate"))
        if mid == "M02":
            rate = 0.9 if (_n(f.get("exposure")) or 0) >= 2000 or (_n(f.get("views")) or 0) >= 300 else 0.65 if (_n(f.get("views")) or 0) >= 100 else 0.45
            reasons = [f"曝光 {_num(f.get('exposure'))}", f"浏览 {_num(f.get('views'))}", f"一转 {_pct(f.get('exposure_to_view_rate'))}"]
        elif mid == "M03":
            rate = 0.9 if conv and conv >= 0.08 else 0.65 if conv and conv >= 0.04 else 0.35 if conv is not None else None
            reasons = [f"支付订单 {_num(f.get('paid_orders'))}", f"二转 {_pct(conv)}", f"销售额 {_money(f.get('sales_revenue'))}"]
        elif mid == "M04":
            count = _n(item.get("product_count")) or 0
            rate = 0.85 if count >= 10 else 0.65 if count else None
            reasons = [f"商品映射 {_num(count)} 条", f"最低价 {_money((item.get('price') or {}).get('min_price'))}"]
        elif mid == "M05":
            rows = _n(item.get("promotion_rows")) or 0
            rate, status = (0.72 if rows else 0.45), "partial"
            reasons = [f"活动/活动商品记录 {_num(rows)} 条", "ROI 成本字段仍需补齐"]
        elif mid == "M06":
            rate, status = (0.7 if item.get("product_count") else 0.5), "partial"
            reasons = ["基于商品名、评价关键词和活动标签推断", "图片/视频字段仍需接入"]
        elif mid == "M07":
            rate = 0.9 if rating and rating >= 4.7 and (neg is None or neg <= 0.03) else 0.7 if rating and rating >= 4.4 else 0.45 if rating is not None else None
            reasons = [f"评分 {_num(r.get('rating_avg'),2)}", f"评价数 {_num(r.get('review_count'))}", f"差评率 {_pct(r.get('negative_review_rate'))}"]
        else:
            status, reasons = "data_gap", ["该模块不是渠道主口径"]
    else:
        rate = _n(base.get("rate"))
        status = base.get("status") or "ok"
        reasons = base.get("reasons") or ["系统综合模块"]
    score = round(weight * max(0, min(1, rate)), 2) if rate is not None else 0.0
    name = {"M01":"经营收益","M02":"流量竞争","M03":"转化断点","M04":"价格房态","M05":"推广ROI","M06":"页面基础","M07":"口碑信任","M08":"执行复盘"}.get(mid, mid)
    return {"module_id": mid, "module_name": name, "weight": weight, "score": score, "rate": rate, "status": status, "reasons": reasons}


def _module_card(item: dict[str, Any]) -> str:
    rate = _n(item.get("rate"))
    pct = int(round(max(0, min(1, rate or 0)) * 100)) if rate is not None else 0
    status = item.get("status") or "ok"
    klass = _cls(status if status == "data_gap" else (rate or 0))
    title = "数据缺口" if status == "data_gap" else f"{pct}%"
    reasons = "".join(f"<span class='tag'>{_e(x)}</span>" for x in (item.get("reasons") or [])[:5])
    return f"<div class='module'><div class='module-top'><div><div class='mid'>{_e(item.get('module_id'))}</div><div class='mname'>{_e(item.get('module_name'))}</div></div><div><span class='score'>{_e(title)}</span><span class='meta'> / {_num(item.get('score'),1)}/{_num(item.get('weight'),0)}</span></div></div><div class='bar'><div class='fill {klass}' style='width:{pct}%'></div></div><div class='module-body'><span class='badge {klass}'>{_e(status)}</span>{reasons}</div></div>"


def _module_blocks(metrics: dict[str, Any], ms: list[dict[str, Any]]) -> str:
    groups = [("pms", "PMS 经营底盘", ["M01"])]
    for item in _channel_items(metrics):
        groups.append((item["platform"], f"{_zh(item['platform'])} 渠道诊断", ["M02", "M03", "M04", "M05", "M06", "M07"]))
    groups.append(("shared", "系统与数据质量", ["M08"]))
    return "".join(f"<div class='source-block' data-module-source='{_e(src)}'><div class='source-title'>{_e(title)} <span class='badge neutral'>{_e(src)}</span></div><div class='source-grid'>{''.join(_module_card(_src_module(src, mid, metrics, ms)) for mid in mids)}</div></div>" for src, title, mids in groups)


def _metric_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    op, funnel, rep, price, promo, events = (metrics.get("operating") or {}), (metrics.get("ota_funnel") or {}), (metrics.get("reputation") or {}), (metrics.get("price_ladder") or {}), (metrics.get("promotion") or {}), (metrics.get("nearby_events") or {})
    items = [("RevPAR", _money(op.get("revpar")), "收益锚点"), ("ADR", _money(op.get("adr")), "价格水平"), ("出租率", _pct(op.get("occupancy_rate")), "经营效率"), ("门店收入", _money(op.get("room_revenue")), "经营结果"), ("日均收入", _money(op.get("avg_daily_revenue")), "派生指标"), ("日均售出间夜", _num(op.get("avg_daily_room_nights"), 1), "派生指标"), ("曝光量", _num(funnel.get("exposure")), "流量入口"), ("浏览量", _num(funnel.get("views")), "详情页访问"), ("支付订单", _num(funnel.get("paid_orders")), "转化结果"), ("浏览→支付转化率", _pct(funnel.get("payment_conversion_rate")), "二转"), ("客单价", _money(funnel.get("avg_order_value")), "派生指标"), ("每浏览销售额", _money(funnel.get("revenue_per_view")), "派生指标"), ("商品最低价", _money(price.get("min_price")), "价格梯度"), ("活动数", _num(promo.get("activity_count")), "推广覆盖"), ("近期周边活动", _num(events.get("upcoming_60d_count")), "需求事件"), ("平台评分", _num(rep.get("rating_avg"), 2), "信任锚点"), ("差评率", _pct(rep.get("negative_review_rate")), "口碑风险")]
    rows = []
    for a, b, c in items:
        cls = "neutral" if b == "未获取" else "info"
        rows.append([a, b, c, f"<span class='badge {cls}'>{'缺失' if b == '未获取' else '已获取'}</span>"])
    return rows


def _missing_rows(dq: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for sec, fields in (dq.get("missing_fields") or {}).items():
        for f in fields or []:
            rows.append([f, "<span class='badge warn'>missing</span>", "补采或检查字段映射", sec])
    return rows or [["无关键缺失字段", "<span class='badge good'>ok</span>", "继续保持字段采集稳定", "系统计算"]]


def _task_rows(dq: dict[str, Any]) -> list[list[Any]]:
    missing = _missing_count(dq)
    return [
        ["P0", "OTA运营", "补齐 S14 数据库关键经营字段，确保报告不是基于缺失口径判断", f"字段完整度、数据新鲜度、缺字段数={missing}", "3天"],
        ["P1", "收益经理", "复盘 RevPAR、ADR、出租率和核心房型库存健康度", "RevPAR、ADR、出租率、房型可售", "7天"],
        ["P1", "运营负责人", "检查曝光、浏览、支付转化和推广 ROI 的断点", "曝光、浏览、支付转化率、ROI", "7天"],
        ["P2", "门店店长", "完善图片、视频、房型卖点和入口标签", "页面质量、转化率、点评关键词", "14天"],
    ]


def build_markdown(result: dict[str, Any]) -> str:
    lines = ["# 酒店 OTA 全面诊断报告", "", f"- final_score: {result.get('final_score')}", f"- risk_level: {result.get('risk_level')}", f"- status: {result.get('status')}"]
    for m in result.get("module_scores") or []:
        lines.append(f"- {m.get('module_id')} {m.get('module_name')}: {m.get('score')}/{m.get('weight')} status={m.get('status')}")
    return "\n".join(lines)


def build_html(result: dict[str, Any]) -> str:
    metrics = result.get("metrics") or {}
    op, funnel, dq = (metrics.get("operating") or {}), (metrics.get("ota_funnel") or {}), (result.get("data_quality") or {})
    missing = _missing_count(dq)
    credibility = max(0, 100 - missing * 10)
    score = _n(result.get("final_score")) or 0
    risk = str(result.get("risk_level") or "medium").lower()
    hotel = result.get("hotel_name") or result.get("hotel_id") or "酒店"
    platform = result.get("platform") or "multi"
    meta = f"{hotel}｜{_zh(platform)}｜{result.get('period_start')} 至 {result.get('period_end')}｜生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    cap = []
    if missing > 3:
        cap.append("C06 数据可信度封顶：关键字段缺失较多，部分判断按保守规则估计。")
    if result.get("status") != "ok":
        cap.append("当前报告为 partial，建议补齐缺失字段后复算。")
    if not cap:
        cap.append("未触发明显封顶规则；仍建议结合真实运营经验复核。")
    cap_html = "".join(f"<li>{_e(x)}</li>" for x in cap)
    notes = result.get("notes") or []
    note_rows = [[f"<span class='badge {_cls(n.get('level'))}'>{_e(n.get('level'))}</span>", n.get("title"), n.get("evidence"), n.get("suggestion")] for n in notes] or [["<span class='badge neutral'>info</span>", "暂无结论", "暂无", "补充数据后重新诊断"]]
    actions = "".join(f"<li>{_e(x)}</li>" for x in result.get("actions") or []) or "<li>补齐数据后重新生成诊断。</li>"
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>酒店 OTA 全面诊断报告</title><style>{CSS}</style></head><body>
<header class='top'><div class='top-inner'><div><h1>酒店 OTA 全面诊断报告</h1><div class='meta'>{_e(meta)}</div></div><div class='actions'><div class='selectbox'><label>选择板块</label><select id='channelSelector' onchange='switchBlock(this.value)'><option value='all'>全部</option><option value='pms'>PMS</option><option value='meituan'>美团</option><option value='ctrip'>携程</option><option value='shared'>系统/数据</option></select></div><button class='btn' onclick='window.print()'>导出报告</button></div></div></header>
<div class='layout'><nav class='side'><a href='#overview'>顶部总览</a><a href='#trend'>月度趋势</a><a href='#revpar'>RevPAR拆解</a><a href='#contribution'>贡献矩阵</a><a href='#quadrant'>效率四象限</a><a href='#opportunity'>机会点测算</a><a href='#modules'>模块诊断</a><a href='#metrics'>经营指标</a><a href='#funnel'>流量漏斗</a><a href='#promotion'>推广效率</a><a href='#page'>页面入口</a><a href='#reputation'>口碑分析</a><a href='#channels'>分渠道指标</a><a href='#price'>价格竞品</a><a href='#missing'>补采提示</a><a href='#actions'>整改任务</a></nav><main>
<section class='card' id='overview'><div class='head'><div><h2>诊断结果概览</h2><p>汇总 + PMS/渠道/系统分板块概览。</p></div><span class='badge {_cls(risk)}'>风险：{_e(_zh(risk))}</span></div><div class='body'><div class='grid4'>{_kpi('总分', f'{round(score):.0f}/100', f'原始分 {score:.1f}')}{_kpi('数据可信度', f'{credibility}%', '字段完整度')}{_kpi('风险等级', _zh(risk), '基于模块得分判定', _cls(risk))}{_kpi('数据来源', _zh(platform), _source_summary(dq))}</div><div class='callout'><b>封顶/校准规则</b><ul>{cap_html}</ul></div><h3>分板块概览</h3>{_overview_blocks(metrics, dq)}{_analysis(result, '综合诊断分析', 'overview', [f'综合诊断结论：酒店当前处于{_zh(risk)}状态，综合得分 {round(score):.0f}/100。', f'数据可信度 {credibility}%，当前缺失字段 {missing} 个。', '核心短板请优先查看 PMS、各 OTA 渠道和系统数据质量三个分组。'])}</div></section>
<section class='card' id='trend' data-module-source='pms'><div class='head'><div><h2>月度经营趋势</h2><p>PMS 经营趋势线 + 月度经营表。</p></div></div><div class='body'>{_trend(op.get('monthly_trend') or [])}</div></section>
<section class='card' id='revpar' data-module-source='pms'><div class='head'><div><h2>RevPAR 拆解</h2><p>判断收益问题来自 ADR、出租率还是两者叠加。</p></div></div><div class='body'>{_revpar_decomposition(metrics)}{_analysis(result, 'RevPAR拆解分析', 'revpar', ['RevPAR = ADR × 出租率。先判断是价格问题、入住问题还是二者叠加，再回到渠道和产品结构排查。'])}</div></section>
<section class='card' id='contribution'><div class='head'><div><h2>渠道贡献矩阵</h2><p>比较曝光、浏览、订单、销售额、客单价、转化率和评分。</p></div></div><div class='body'>{_contribution_matrix(metrics)}{_analysis(result, '渠道贡献分析', 'contribution', ['贡献矩阵用于判断主力渠道、弱渠道和高潜渠道；不要只按曝光量判断渠道价值。'])}</div></section>
<section class='card' id='quadrant'><div class='head'><div><h2>渠道效率四象限</h2><p>按流量与转化拆成主力放大、加曝光、修转化、暂缓投放。</p></div></div><div class='body'>{_quadrant_blocks(metrics)}{_analysis(result, '四象限分析', 'quadrant', ['高流量低转化先修页面/价格/口碑；低流量高转化优先加曝光。'])}</div></section>
<section class='card' id='opportunity'><div class='head'><div><h2>机会点测算</h2><p>基于流量 × 转化 × 客单价的保守测算，不作为承诺结果。</p></div></div><div class='body'>{_opportunity_estimates(metrics)}<div class='callout'>以上为运营测算：只用于判断先提曝光、先提一转、先提二转还是先提客单价，不代表已发生结果。</div>{_analysis(result, '机会点分析', 'opportunity', ['机会点测算必须标记为假设：以当前浏览、转化和客单价为基准，测算小幅提升空间。'])}</div></section>
<section class='card' id='modules'><div class='head'><div><h2>模块诊断详情</h2><p>按 PMS、各 OTA 渠道、系统/数据质量拆分；右上角选择板块会同步过滤。</p></div></div><div class='body'>{_module_blocks(metrics, result.get('module_scores') or [])}{_analysis(result, '模块联动分析', 'modules', ['模块诊断已按 PMS、OTA 渠道和系统数据质量拆开；先处理低分渠道，再补齐 partial/data_gap 的数据字段。'])}</div></section>
<section class='card' id='metrics' data-module-source='pms'><div class='head'><div><h2>经营指标</h2><p>PMS经营数据与派生指标。</p></div></div><div class='body'>{_table(['指标','当前值','口径','状态'], _metric_rows(metrics))}{_analysis(result, '指标解读', 'metrics', [f"RevPAR {_money(op.get('revpar'))} = ADR {_money(op.get('adr'))} × 出租率 {_pct(op.get('occupancy_rate'))}。", '出租率使用所选周期内总售出间夜 / 总可售房晚；如果日表缺少出租率字段，会用 room_nights 或 sold_rooms 除以 room_count 计算。'])}</div></section>
<section class='card' id='funnel'><div class='head'><div><h2>流量漏斗</h2><p>曝光 → 浏览 → 支付转化路径，按渠道展开。</p></div></div><div class='body'><div class='grid4'>{_kpi('曝光量', _num(funnel.get('exposure')), '列表页展示')}{_kpi('浏览量', _num(funnel.get('views')), '详情页访问')}{_kpi('支付订单', _num(funnel.get('paid_orders')), '支付结果')}{_kpi('支付转化率', _pct(funnel.get('payment_conversion_rate')), '浏览→支付')}</div><h3>分渠道路径</h3>{_flow_blocks(metrics)}{_analysis(result, '流量漏斗诊断', 'funnel', [f"曝光→浏览：{_pct(funnel.get('exposure_to_view_rate'))}。", f"浏览→支付：{_pct(funnel.get('payment_conversion_rate'))}。", '若曝光充足但支付不足，优先检查价格梯度、评论信任和退改政策。'])}</div></section>
<section class='card' id='promotion'><div class='head'><div><h2>推广效率表</h2><p>推广金额、花费、ROI 和明细完整度；当前未接入成本/ROI字段时保留口径入口。</p></div></div><div class='body'>{_promotion_blocks(metrics)}{_analysis(result, '推广效率分析', 'promotion', ['当前只能判断活动覆盖，推广订单金额、推广花费和 ROI 仍未接入；因此不应得出投放效率好坏的结论。'])}</div></section>
<section class='card' id='page'><div class='head'><div><h2>页面展示与入口基础</h2><p>图片、视频、卖点、入口标签。</p></div></div><div class='body'>{_page_blocks(metrics)}{_analysis(result, '页面入口分析', 'page', ['页面图片、视频、房型卖点和入口标签仍需结构化采集；当前只可依据商品/房型映射做弱判断。'])}</div></section>
<section class='card' id='reputation'><div class='head'><div><h2>口碑分析</h2><p>平台评分、评价数量、差评和未回复评价。</p></div></div><div class='body'>{_reputation_blocks(metrics)}{_analysis(result, '口碑分析', 'reputation', ['口碑模块应按渠道分别看评分、评价规模、差评率和未回复数；评价规模过小时不能过度乐观。'])}</div></section>
<section class='card' id='channels'><div class='head'><div><h2>分渠道得分与指标</h2><p>按渠道展开曝光、浏览、支付、销售额、占比、客单价、评分、差评率和建议。</p></div></div><div class='body'>{_channel_cards(metrics)}{_channel_table(metrics)}{_analysis(result, '分渠道诊断', 'channels', ['分渠道指标按平台拆开，重点比较曝光、浏览、支付订单、销售额、评分和差评率。'])}</div></section>
<section class='card' id='price'><div class='head'><div><h2>价格与竞品</h2><p>全渠道汇总 + 按渠道拆分价格房型和竞品价差。</p></div></div><div class='body'>{_price_blocks(metrics)}<h3>价格梯度诊断表</h3>{_price_ladder_table(metrics)}{_analysis(result, '价格诊断解读', 'price', ['价格不是单点判断，需要同时看引流价、全日价、团购价、钟点房价、远期价和竞品均价，避免价格体系混乱。'])}</div></section>
<section class='card' id='missing' data-module-source='shared'><div class='head'><div><h2>补采提示</h2><p>缺失字段、影响、采集方式。</p></div></div><div class='body'>{_table(['缺失字段','当前状态','处理建议','责任来源'], _missing_rows(dq))}{_analysis(result, '数据完整度分析', 'missing', [f'当前缺失字段数为 {missing}。缺失字段不等于经营差，但会降低评分可信度。'])}</div></section>
<section class='card' id='actions'><div class='head'><div><h2>诊断结论与整改任务</h2><p>问题结论 + P0/P1/P2 整改任务表；只输出建议，不执行调价和审批。</p></div></div><div class='body'><h3>问题结论</h3>{_table(['等级','标题','证据','建议'], note_rows)}<h3>动作建议</h3><ol>{actions}</ol><h3>整改任务表</h3>{_table(['优先级','负责人','整改动作','复盘指标','周期'], _task_rows(dq))}{_analysis(result, '动作优先级分析', 'actions', ['先补数据和页面包装，再做主渠道流量曝光与二转优化，最后补推广 ROI 并复盘订单、营收和 RevPAR。'])}</div></section>
</main></div><script>function switchBlock(v){{document.querySelectorAll('[data-source]').forEach(function(e){{e.classList.toggle('hidden',v!=='all'&&e.getAttribute('data-source')!==v);}});document.querySelectorAll('[data-source-row]').forEach(function(e){{e.classList.toggle('hidden',v!=='all'&&e.getAttribute('data-source-row')!==v);}});document.querySelectorAll('[data-module-source]').forEach(function(e){{e.classList.toggle('hidden',v!=='all'&&e.getAttribute('data-module-source')!==v);}});}}document.addEventListener('DOMContentLoaded',function(){{switchBlock(document.getElementById('channelSelector').value||'all');}});</script></body></html>"""


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
