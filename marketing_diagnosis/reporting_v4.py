from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

CSS = """
:root{--ink:#182230;--muted:#667085;--line:#d9dee8;--soft:#eef2f7;--blue:#2563eb;--green:#168a4a;--amber:#b7791f;--red:#c2413a;--shadow:0 12px 34px rgba(16,24,40,.08);--radius:14px}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at top left,#eaf1ff 0,#f5f7fb 34%,#f8fafc 100%);color:var(--ink);font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif;font-size:14px;line-height:1.52}.top{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}.top-inner{max-width:1500px;margin:0 auto;padding:16px 24px;display:flex;justify-content:space-between;gap:16px;align-items:center}.top h1{margin:0;font-size:24px}.meta{color:var(--muted);font-size:13px;margin-top:4px}.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.selectbox{display:flex;gap:8px;align-items:center;border:1px solid var(--line);border-radius:10px;background:#f8fafc;padding:7px 11px}.selectbox label{font-weight:800;color:#475467}.selectbox select{height:30px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}.btn{height:36px;border:1px solid #182230;background:#182230;color:#fff;border-radius:10px;padding:0 14px;font-weight:800;cursor:pointer}.layout{max-width:1500px;margin:0 auto;padding:22px 24px 56px;display:grid;grid-template-columns:240px minmax(0,1fr);gap:22px}.side{position:sticky;top:88px;align-self:start;background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden}.side a{display:block;padding:10px 14px;border-bottom:1px solid var(--soft);text-decoration:none;color:#344054;font-weight:800;font-size:13px}.side a:hover{background:#eef4ff;color:var(--blue)}main{display:grid;gap:20px}.card{background:rgba(255,255,255,.98);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden}.head{padding:17px 20px;border-bottom:1px solid var(--soft);display:flex;justify-content:space-between;gap:12px;background:linear-gradient(180deg,#fff,#fbfcff)}.head h2{margin:0;font-size:18px}.head p{margin:6px 0 0;color:var(--muted);font-size:13px}.body{padding:20px}.badge{display:inline-flex;align-items:center;min-height:24px;padding:0 9px;border-radius:999px;font-size:12px;font-weight:900;white-space:nowrap}.good{color:var(--green);background:#e8f5ee}.warn{color:var(--amber);background:#fff4dc}.bad{color:var(--red);background:#fdebea}.info{color:var(--blue);background:#eaf1ff}.neutral{color:#475467;background:#eef1f5}.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px}.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.kpi,.tile{border:1px solid var(--line);border-radius:12px;padding:14px;background:linear-gradient(180deg,#fff,#fbfcfe)}.kpi label,.tile label{display:block;color:var(--muted);font-size:12px;font-weight:900}.kpi strong{display:block;margin-top:8px;font-size:28px;line-height:1}.tile strong{display:block;margin-top:6px;font-size:19px}.kpi span,.tile span{display:block;margin-top:8px;color:var(--muted);font-size:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.panel{border:1px solid var(--line);border-radius:12px;background:#fff;overflow:hidden;margin-bottom:14px}.panel h3{margin:0;padding:12px 14px;border-bottom:1px solid var(--soft);background:#fafbfc;font-size:15px}.panel .pbody{padding:14px}.table-wrap{overflow:auto}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:10px 11px;border-bottom:1px solid var(--soft);text-align:left;vertical-align:top}.table th{background:#f8fafc;color:#475467;font-size:12px;font-weight:900}.analysis{margin-top:16px;border:1px solid #c7d2fe;border-left:4px solid #6366f1;border-radius:12px;background:#eef2ff;overflow:hidden}.analysis summary{cursor:pointer;padding:11px 14px;font-weight:900;color:#4338ca;display:flex;gap:8px;align-items:center}.analysis .txt{padding:0 16px 14px;color:#312e81}.analysis p{margin:8px 0}.callout{border:1px solid #f0cd7a;background:#fff8e6;border-radius:12px;padding:12px 14px;margin-top:12px;color:#7a4d08}.period{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.hidden{display:none!important}@media(max-width:980px){.layout{grid-template-columns:1fr;padding:14px}.side{position:static;display:grid;grid-template-columns:repeat(2,1fr)}.grid4,.grid3,.two{grid-template-columns:1fr}.top-inner{display:block}.actions{margin-top:10px}}@media print{.top,.side{display:none}.layout{display:block;padding:0}.card{box-shadow:none;border:0;background:#fff}.analysis{break-inside:avoid}}
"""


def _n(v: Any) -> float | None:
    try:
        if v in (None, ""):
            return None
        x = float(str(v).replace(",", ""))
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
    return {"all":"全部","multi":"多渠道","pms":"PMS","meituan":"美团","ctrip":"携程","shared":"系统/数据","high":"高风险","medium":"中风险","low":"低风险","daily":"日粒度","monthly":"月粒度","snapshot":"快照/累计","event":"事件日期","unknown":"未知"}.get(str(v or "").lower(), str(v or "未获取"))


def _cls(v: Any) -> str:
    if isinstance(v, str):
        return {"high":"bad","medium":"warn","low":"good","高":"bad","中":"warn","低":"good","ok":"good","partial":"warn","data_gap":"neutral"}.get(v.lower(), "neutral")
    x = _n(v)
    if x is None:
        return "neutral"
    return "good" if x >= 0.8 else "warn" if x >= 0.6 else "bad"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    h = "".join(f"<th>{_e(x)}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{x if str(x).startswith('<') else _e(x)}</td>" for x in r) + "</tr>" for r in rows)
    return f"<div class='table-wrap'><table class='table'><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>"


def _kpi(label: str, value: Any, hint: str = "", cls: str = "") -> str:
    c = f" class='{cls}'" if cls else ""
    return f"<div class='kpi'><label>{_e(label)}</label><strong{c}>{_e(value)}</strong><span>{_e(hint)}</span></div>"


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


def _period(metric: dict[str, Any] | None) -> dict[str, Any]:
    return (metric or {}).get("data_period") or {}


def _period_line(period: dict[str, Any] | None) -> str:
    p = period or {}
    start = p.get("start") or "未标注"
    end = p.get("end") or "未标注"
    return f"{_zh(p.get('grain'))}｜{start} 至 {end}｜{p.get('note') or '时间口径未标注'}"


def _period_badges(period: dict[str, Any] | None) -> str:
    p = period or {}
    return f"<div class='period'><span class='badge info'>{_e(_zh(p.get('grain')))}</span><span class='badge neutral'>{_e(p.get('start') or '未标注')} → {_e(p.get('end') or '未标注')}</span><span class='badge neutral'>{_e(p.get('note') or '时间口径未标注')}</span></div>"


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


def _funnel_day_rows(funnel: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for item in funnel.get("latest_previous_comparison") or []:
        rows.append([item.get("label"), item.get("business_date"), _num(item.get("exposure")), _num(item.get("exposure_people")), _num(item.get("effective_exposure")), item.get("exposure_used_source"), _num(item.get("views")), _pct(item.get("exposure_to_view_rate")), _num(item.get("paid_orders")), _pct(item.get("payment_conversion_rate")), _money(item.get("sales_revenue"))])
    return rows or [["最新日", funnel.get("latest_business_date"), "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取"]]


def _funnel_platform_rows(funnel: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for item in funnel.get("by_platform") or []:
        rows.append([_zh(item.get("platform")), _num(item.get("exposure")), _num(item.get("exposure_people")), _num(item.get("effective_exposure")), item.get("exposure_used_source"), _num(item.get("views")), _pct(item.get("exposure_to_view_rate")), _num(item.get("paid_orders")), _pct(item.get("payment_conversion_rate")), _money(item.get("avg_order_value"))])
    return rows or [["无", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取"]]


def _rep_value_row(label: str, scope: dict[str, Any], source_note: str = "") -> list[Any]:
    return [label, scope.get("start"), scope.get("end"), _num(scope.get("review_count")), _num(scope.get("rating_avg"), 2), _num(scope.get("negative_review_count")), _pct(scope.get("negative_review_rate")), _num(scope.get("unreplied_review_count")), source_note or scope.get("source_note")]


def _reputation_rows(rep: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    overview = rep.get("overview_snapshot") or {}
    rows.append(_rep_value_row("累计/概览快照", overview))
    for item in overview.get("by_platform") or []:
        rows.append(_rep_value_row(f"{_zh(item.get('platform'))}累计/概览", {**overview, **item}, overview.get("source_note")))
    detail_all = rep.get("detail_all") or {}
    rows.append(_rep_value_row("全部评论明细", detail_all))
    for item in detail_all.get("by_platform") or []:
        rows.append(_rep_value_row(f"{_zh(item.get('platform'))}全部明细", {**detail_all, **item}, detail_all.get("source_note")))
    recent30 = rep.get("recent_30d") or {}
    rows.append(_rep_value_row("近30天评论明细", recent30))
    for item in recent30.get("by_platform") or []:
        rows.append(_rep_value_row(f"{_zh(item.get('platform'))}近30天", {**recent30, **item}, recent30.get("source_note")))
    recent90 = rep.get("recent_90d") or {}
    rows.append(_rep_value_row("近90天评论明细", recent90))
    for item in recent90.get("by_platform") or []:
        rows.append(_rep_value_row(f"{_zh(item.get('platform'))}近90天", {**recent90, **item}, recent90.get("source_note")))
    return rows


def _event_rows(events: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for item in events.get("events") or []:
        rows.append([item.get("event_name"), item.get("event_start_date"), item.get("countdown_days"), item.get("distance_km"), "需求辅助信号"])
    return rows or [["无", "未获取", "未获取", "未获取", "暂无事件数据"]]


def _event_suggestion_html(events: dict[str, Any]) -> str:
    suggestions = ((events.get("ai_context") or {}).get("suggestions") or [])
    return "".join(f"<p>{_e(x)}</p>" for x in suggestions) or "<p>暂无周边活动建议。</p>"


def _module_rows(result: dict[str, Any]) -> list[list[Any]]:
    return [[item.get("module_id"), item.get("module_name"), f"{_num(item.get('score'),1)}/{_num(item.get('weight'),0)}", item.get("status"), "；".join(item.get("reasons") or [])] for item in result.get("module_scores") or []]


def _rule_rows(result: dict[str, Any]) -> list[list[Any]]:
    return [[item.get("rule_id"), item.get("module_id"), item.get("rule_name"), item.get("field"), f"{_num(item.get('score'),1)}/{_num(item.get('weight'),0)}", "；".join(item.get("reasons") or [])] for item in result.get("rule_hits") or []] or [["无", "无", "暂无规则命中", "无", "无", "无"]]


def _cap_rows(result: dict[str, Any]) -> list[list[Any]]:
    return [[item.get("cap_id"), item.get("name"), item.get("cap_score"), item.get("severity"), item.get("evidence"), item.get("description")] for item in result.get("cap_rules_triggered") or []] or [["无", "未触发封顶", result.get("cap_score", 100), "低", "当前未命中封顶条件", "仍建议人工复核经营数据。"]]


def _ai_action_rows(result: dict[str, Any]) -> list[list[Any]]:
    lines = _ai(result, "action_plan", []) or _ai(result, "actions", []) or result.get("actions") or []
    rows = []
    for text in lines[:8]:
        raw = str(text)
        parts = [p.strip() for p in raw.split("｜")]
        if len(parts) >= 5:
            rows.append(parts[:5])
            continue
        if any(x in raw for x in ["补", "字段", "数据", "ROI"]):
            pri, owner, cycle = "P0", "OTA运营", "3天"
        elif any(x in raw for x in ["曝光", "转化", "价格", "RevPAR", "ADR"]):
            pri, owner, cycle = "P1", "运营负责人/收益经理", "7天"
        else:
            pri, owner, cycle = "P2", "门店店长", "14天"
        rows.append([pri, owner, raw, "订单、转化、RevPAR、字段完整度", cycle])
    return rows or [["P0", "OTA运营", "补齐关键字段后重新生成报告", "字段完整度、数据新鲜度", "3天"]]


def _missing_rows(dq: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for sec, fields in (dq.get("missing_fields") or {}).items():
        for f in fields or []:
            rows.append([sec, f, "<span class='badge warn'>missing</span>", "补采或检查字段映射"])
    return rows or [["无", "无关键缺失字段", "<span class='badge good'>ok</span>", "继续保持字段采集稳定"]]


def _price_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    price = metrics.get("price_ladder") or {}
    rows = [["全渠道", _num(price.get("product_count")), _money(price.get("min_price")), _money(price.get("max_price")), _money(price.get("price_span")), _num(price.get("group_buy_count")), _num(price.get("hour_room_count"))]]
    for platform, item in sorted((price.get("by_platform") or {}).items()):
        rows.append([_zh(platform), _num(item.get("product_count")), _money(item.get("min_price")), _money(item.get("max_price")), _money(item.get("price_span")), _num(item.get("group_buy_count")), _num(item.get("hour_room_count"))])
    return rows


def _metric_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    op, funnel, rep, price, promo, events = (metrics.get("operating") or {}), (metrics.get("ota_funnel") or {}), (metrics.get("reputation") or {}), (metrics.get("price_ladder") or {}), (metrics.get("promotion") or {}), (metrics.get("nearby_events") or {})
    items = [("RevPAR", _money(op.get("revpar")), "PMS日粒度/周期汇总"), ("ADR", _money(op.get("adr")), "PMS平均房价"), ("出租率", _pct(op.get("occupancy_rate")), "售出间夜÷可售房晚"), ("有效曝光", _num(funnel.get("effective_exposure")), "曝光量缺失时用曝光人数替代"), ("曝光人数", _num(funnel.get("exposure_people")), "辅助字段"), ("浏览量", _num(funnel.get("views")), "详情页访问"), ("支付订单", _num(funnel.get("paid_orders")), "支付结果"), ("支付转化率", _pct(funnel.get("payment_conversion_rate")), "浏览→支付"), ("商品最低价", _money(price.get("min_price")), "价格快照"), ("活动数", _num(promo.get("activity_count")), "活动快照"), ("平台评分", _num(rep.get("rating_avg"), 2), "口碑概览/明细"), ("60天周边活动", _num(events.get("upcoming_60d_count")), "事件日期口径")]
    return [[a, b, c, f"<span class='badge {'neutral' if b == '未获取' else 'info'}'>{'缺失' if b == '未获取' else '已获取'}</span>"] for a, b, c in items]


def build_markdown(result: dict[str, Any]) -> str:
    lines = ["# 酒店 OTA 全面诊断报告", "", f"- score_before_cap: {result.get('score_before_cap')}", f"- final_score: {result.get('final_score')}", f"- cap_applied: {result.get('cap_applied')}", f"- risk_level: {result.get('risk_level')}", f"- status: {result.get('status')}"]
    return "\n".join(lines)


def build_html(result: dict[str, Any]) -> str:
    metrics = result.get("metrics") or {}
    op, funnel, rep, events, price, dq = (metrics.get("operating") or {}), (metrics.get("ota_funnel") or {}), (metrics.get("reputation") or {}), (metrics.get("nearby_events") or {}), (metrics.get("price_ladder") or {}), (result.get("data_quality") or {})
    missing = _missing_count(dq)
    credibility = max(0, 100 - missing * 10)
    score = _n(result.get("final_score")) or 0
    raw_score = _n(result.get("score_before_cap")) or score
    cap_score = _n(result.get("cap_score")) or 100
    risk = str(result.get("risk_level") or "medium").lower()
    hotel = result.get("hotel_name") or result.get("hotel_id") or "酒店"
    platform = result.get("platform") or "multi"
    meta = f"{hotel}｜{_zh(platform)}｜报告请求周期：{result.get('period_start')} 至 {result.get('period_end')}｜生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    cap_state = "已封顶" if result.get("cap_applied") else "未封顶"
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>酒店 OTA 全面诊断报告</title><style>{CSS}</style></head><body>
<header class='top'><div class='top-inner'><div><h1>酒店 OTA 全面诊断报告</h1><div class='meta'>{_e(meta)}</div></div><div class='actions'><div class='selectbox'><label>选择板块</label><select id='channelSelector' onchange='switchBlock(this.value)'><option value='all'>全部</option><option value='pms'>PMS</option><option value='meituan'>美团</option><option value='ctrip'>携程</option><option value='shared'>系统/数据</option></select></div><button class='btn' onclick='window.print()'>导出报告</button></div></div></header>
<div class='layout'><nav class='side'><a href='#overview'>顶部总览</a><a href='#score-cap'>评分封顶</a><a href='#trend'>月度趋势</a><a href='#funnel'>流量漏斗</a><a href='#reputation'>口碑分析</a><a href='#events'>周边活动</a><a href='#modules'>模块诊断</a><a href='#rules'>规则明细</a><a href='#metrics'>经营指标</a><a href='#price'>价格房型</a><a href='#missing'>补采提示</a><a href='#actions'>AI整改动作</a></nav><main>
<section class='card' id='overview'><div class='head'><div><h2>诊断结果概览</h2><p>总分、封顶、数据可信度与核心指标。各模块时间口径已放在对应模块标题下。</p></div><span class='badge {_cls(risk)}'>风险：{_e(_zh(risk))}</span></div><div class='body'><div class='grid4'>{_kpi('最终总分', f'{score:.1f}/100', f'原始分 {raw_score:.1f}')}{_kpi('封顶状态', cap_state, f'封顶线 {cap_score:.1f}', 'warn' if result.get('cap_applied') else 'good')}{_kpi('数据可信度', f'{credibility}%', f'缺失字段 {missing} 个')}{_kpi('数据来源', _zh(platform), _source_summary(dq))}</div><div class='grid4' style='margin-top:13px'>{_kpi('RevPAR', _money(op.get('revpar')), _period_line(_period(op)))}{_kpi('出租率', _pct(op.get('occupancy_rate')), 'PMS周期汇总')}{_kpi('有效曝光', _num(funnel.get('effective_exposure')), funnel.get('exposure_note'))}{_kpi('近60天活动', _num(events.get('upcoming_60d_count')), _period_line(_period(events)))}</div>{_analysis(result, '综合诊断分析', 'overview', [f'最终分 {score:.1f}/100，原始分 {raw_score:.1f}，封顶线 {cap_score:.1f}。'])}</div></section>
<section class='card' id='score-cap' data-module-source='shared'><div class='head'><div><h2>总分封顶说明</h2><p>系统/数据口径：防止基础项、口碑项或缺字段导致经营结论失真。</p></div><span class='badge {'warn' if result.get('cap_applied') else 'good'}'>{_e(cap_state)}</span></div><div class='body'>{_table(['规则ID','规则','封顶分','等级','证据','说明'], _cap_rows(result))}{_analysis(result, '封顶校准分析', 'cap', ['封顶规则用于防止报告失真。'])}</div></section>
<section class='card' id='trend' data-module-source='pms'><div class='head'><div><h2>月度经营趋势</h2>{_period_badges(_period(op))}<p>月度趋势表本身为月粒度；PMS经营总览为日粒度汇总，两者不要混算。</p></div></div><div class='body'><div class='two'><div class='panel'><h3>月度趋势线</h3><div class='pbody'>{_trend_svg(op.get('monthly_trend') or [])}</div></div><div class='panel'><h3>月度经营明细</h3><div class='pbody'>{_table(['月份','ADR','出租率','RevPAR','门店收入','RevPAR环比'], _trend_rows(op.get('monthly_trend') or []))}</div></div></div></div></section>
<section class='card' id='funnel'><div class='head'><div><h2>流量漏斗</h2>{_period_badges(_period(funnel))}<p>周期汇总 + 最新日/上一日对比。曝光量缺失时可临时用曝光人数作为计算曝光。</p></div></div><div class='body'><div class='grid4'>{_kpi('曝光量', _num(funnel.get('exposure')), '原始曝光量')}{_kpi('曝光人数', _num(funnel.get('exposure_people')), '辅助口径')}{_kpi('计算曝光', _num(funnel.get('effective_exposure')), funnel.get('exposure_used_source'))}{_kpi('一转', _pct(funnel.get('exposure_to_view_rate')), '浏览 ÷ 计算曝光')}</div><div class='grid4' style='margin-top:13px'>{_kpi('浏览量', _num(funnel.get('views')), '详情页访问')}{_kpi('支付订单', _num(funnel.get('paid_orders')), '支付结果')}{_kpi('二转', _pct(funnel.get('payment_conversion_rate')), '订单 ÷ 浏览')}{_kpi('客单价', _money(funnel.get('avg_order_value')), '销售额 ÷ 订单')}</div><div class='callout'>{_e(funnel.get('exposure_note'))}</div><h3>最新日 / 上一日对比</h3>{_table(['口径','日期','曝光量','曝光人数','计算曝光','使用口径','浏览','一转','订单','二转','销售额'], _funnel_day_rows(funnel))}<h3>分渠道周期汇总</h3>{_table(['渠道','曝光量','曝光人数','计算曝光','使用口径','浏览','一转','订单','二转','客单价'], _funnel_platform_rows(funnel))}{_analysis(result, '流量漏斗诊断', 'funnel', ['漏斗必须同时看周期汇总和最新日/上一日，避免把单日波动当长期结论。'])}</div></section>
<section class='card' id='reputation'><div class='head'><div><h2>口碑分析</h2>{_period_badges(_period(rep))}<p>拆分累计/概览快照、全部评论明细、近30天、近90天和分渠道；不再把概览累计数误标成近30天。</p></div></div><div class='body'><div class='callout'>{_e(rep.get('coverage_note'))}</div>{_table(['口径','开始','结束','评价数','评分','差评数','差评率','未回复','来源说明'], _reputation_rows(rep))}{_analysis(result, '口碑分析', 'reputation', ['口碑要区分累计概览和近90天评论明细；评价量太小时不能只因评分高就判定稳定。'])}</div></section>
<section class='card' id='events'><div class='head'><div><h2>周边活动与需求建议</h2>{_period_badges(_period(events))}<p>周边活动是事件日期口径，用于辅助远期价、库存、套餐和页面卖点。</p></div></div><div class='body'>{_table(['活动','开始日期','倒计时','距离km','判断'], _event_rows(events))}<div class='callout'>{_event_suggestion_html(events)}</div>{_analysis(result, '周边活动AI分析', 'nearby_events', (events.get('ai_context') or {}).get('suggestions') or ['周边活动只能作为需求辅助信号。'])}</div></section>
<section class='card' id='modules'><div class='head'><div><h2>模块诊断详情</h2><p>模块诊断依赖各自模块顶部口径，不再单独聚合展示时间粒度。</p></div></div><div class='body'>{_table(['模块','名称','得分','状态','证据'], _module_rows(result))}{_analysis(result, '模块联动分析', 'modules', ['模块诊断要和时间口径、数据缺口、封顶规则一起看。'])}</div></section>
<section class='card' id='rules' data-module-source='shared'><div class='head'><div><h2>评分规则命中明细</h2><p>系统/数据口径：解释每个模块为什么得分、为什么扣分。</p></div></div><div class='body'>{_table(['规则ID','模块','规则名称','字段','得分','证据'], _rule_rows(result))}{_analysis(result, '评分规则分析', 'rules', ['规则明细用于解释分数来源。'])}</div></section>
<section class='card' id='metrics' data-module-source='pms'><div class='head'><div><h2>经营指标</h2>{_period_badges(_period(op))}<p>PMS经营数据与核心派生指标。</p></div></div><div class='body'>{_table(['指标','当前值','口径','状态'], _metric_rows(metrics))}{_analysis(result, '指标解读', 'metrics', [f"RevPAR {_money(op.get('revpar'))} = ADR {_money(op.get('adr'))} × 出租率 {_pct(op.get('occupancy_rate'))}。"] )}</div></section>
<section class='card' id='price'><div class='head'><div><h2>价格房型</h2>{_period_badges(_period(price))}<p>价格快照口径，分渠道看最低价、最高价、团购和钟点房。</p></div></div><div class='body'>{_table(['渠道','商品数','最低价','最高价','价格跨度','团购数','钟点房数'], _price_rows(metrics))}{_analysis(result, '价格诊断解读', 'price', ['价格不是单点判断，需要同时看引流价、全日价、团购价、钟点房价、远期价和竞品均价。'])}</div></section>
<section class='card' id='missing' data-module-source='shared'><div class='head'><div><h2>补采提示</h2><p>系统/数据口径：缺失字段、影响、采集方式。</p></div></div><div class='body'>{_table(['模块','缺失字段','状态','处理建议'], _missing_rows(dq))}{_analysis(result, '数据完整度分析', 'missing', [f'当前缺失字段数为 {missing}。'])}</div></section>
<section class='card' id='actions'><div class='head'><div><h2>AI整改动作建议</h2><p>优先使用AI基于当前报告生成的动作；无AI配置时用规则兜底。</p></div></div><div class='body'>{_table(['优先级','负责人','整改动作','复盘指标','周期'], _ai_action_rows(result))}{_analysis(result, '动作优先级分析', 'action_plan', ['先补数据和页面包装，再做主渠道流量曝光与二转优化，最后补推广ROI并复盘订单、营收和RevPAR。'])}</div></section>
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
