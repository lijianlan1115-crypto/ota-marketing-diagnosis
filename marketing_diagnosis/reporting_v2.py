from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

CSS = """
body{margin:0;background:#f6f7f9;color:#1d2430;font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif;font-size:14px}.top{position:sticky;top:0;background:#fff;border-bottom:1px solid #d9dee8;z-index:10}.top-inner{max-width:1440px;margin:0 auto;padding:14px 24px;display:flex;justify-content:space-between;gap:16px;align-items:center}.top h1{margin:0;font-size:22px}.meta{color:#667085;font-size:13px;margin-top:4px}.actions{display:flex;gap:8px;align-items:center}.selectbox{display:flex;gap:8px;align-items:center;border:1px solid #d9dee8;border-radius:8px;background:#f8fafc;padding:6px 10px}.selectbox select{height:30px;border:1px solid #d9dee8;border-radius:6px;background:#fff}.btn{height:34px;border:1px solid #1d2430;background:#1d2430;color:#fff;border-radius:8px;padding:0 12px;font-weight:700}.layout{max-width:1440px;margin:0 auto;padding:20px 24px 48px;display:grid;grid-template-columns:220px 1fr;gap:20px}.side{position:sticky;top:84px;align-self:start;background:#fff;border:1px solid #d9dee8;border-radius:8px;box-shadow:0 8px 24px rgba(22,34,51,.08);overflow:hidden}.side a{display:block;padding:11px 14px;border-bottom:1px solid #edf0f5;text-decoration:none;color:#344054;font-weight:700}.side a:hover{background:#f2f6fb;color:#2563eb}main{display:grid;gap:18px}.card{background:#fff;border:1px solid #d9dee8;border-radius:8px;box-shadow:0 8px 24px rgba(22,34,51,.08);overflow:hidden}.head{padding:16px 18px;border-bottom:1px solid #edf0f5;display:flex;justify-content:space-between;gap:12px}.head h2{margin:0;font-size:17px}.head p{margin:5px 0 0;color:#667085;font-size:13px}.body{padding:18px}.badge{display:inline-flex;align-items:center;min-height:24px;padding:0 8px;border-radius:999px;font-size:12px;font-weight:800}.good{color:#168a4a;background:#e8f5ee}.warn{color:#b7791f;background:#fff4dc}.bad{color:#c2413a;background:#fdebea}.info{color:#2563eb;background:#eaf1ff}.neutral{color:#475467;background:#eef1f5}.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.kpi,.mini{border:1px solid #d9dee8;border-radius:8px;padding:14px;background:#fff}.kpi label,.mini label{display:block;color:#667085;font-size:12px;font-weight:800}.kpi strong{display:block;margin-top:8px;font-size:28px}.kpi span{display:block;margin-top:8px;color:#667085;font-size:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #edf0f5;text-align:left;vertical-align:top}th{background:#f8fafc;color:#475467;font-size:12px}.analysis{margin-top:16px;border:1px solid #c7d2fe;border-left:4px solid #6366f1;border-radius:8px;background:#eef2ff}.analysis summary{cursor:pointer;padding:10px 14px;font-weight:800;color:#4338ca}.analysis .txt{padding:0 16px 14px;color:#312e81}.source-block{margin:0 0 18px}.source-title{display:flex;align-items:center;gap:8px;margin:0 0 10px;font-size:16px;font-weight:900}.source-grid,.channel-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.module,.chan{border:1px solid #d9dee8;border-radius:10px;background:#fff;overflow:hidden}.module-top{padding:14px 16px 8px;display:flex;justify-content:space-between;gap:10px}.mid{font-size:12px;font-weight:900;color:#667085}.mname{font-size:16px;font-weight:900;margin-top:2px}.score{font-size:26px;font-weight:900}.bar{height:8px;background:#e9edf3;border-radius:999px;overflow:hidden;margin:0 16px 10px}.fill{height:100%;background:#2563eb}.fill.good{background:#168a4a}.fill.warn{background:#b7791f}.fill.bad{background:#c2413a}.module-body{padding:0 16px 14px;color:#475467}.tag{display:inline-block;margin:3px 4px 0 0;padding:2px 8px;background:#f2f5f9;border-radius:4px;font-size:12px}.chan{padding:14px}.chan h3{margin:0 0 10px}.mini-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.mini strong{display:block;margin-top:4px;font-size:18px}.hidden{display:none!important}@media(max-width:980px){.layout{grid-template-columns:1fr;padding:14px}.side{position:static;display:grid;grid-template-columns:repeat(2,1fr)}.grid4,.two,.source-grid,.channel-grid,.mini-grid{grid-template-columns:1fr}.top-inner{display:block}.actions{margin-top:10px}}@media print{.top,.side{display:none}.layout{display:block;padding:0}.card{box-shadow:none;border:0}}
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
    return {"all":"全部","multi":"多渠道","pms":"PMS","meituan":"美团","ctrip":"携程","shared":"系统/数据","high":"高风险","medium":"中风险","low":"低风险"}.get(str(v or "").lower(), str(v or "未获取"))


def _cls(v: Any) -> str:
    if isinstance(v, str):
        return {"high":"bad","medium":"warn","low":"good","ok":"good","partial":"warn","data_gap":"neutral"}.get(v.lower(), "neutral")
    x = _n(v)
    if x is None:
        return "neutral"
    return "good" if x >= 0.8 else "warn" if x >= 0.6 else "bad"


def _ai_source(result: dict[str, Any]) -> str:
    s = str((result.get("ai_analysis") or {}).get("source") or "rule_based")
    return "AI接口" if s == "ai" else "规则兜底" if s.startswith("rule") else s


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
    return f"<details class='analysis' open><summary><span class='badge info'>{_e(_ai_source(result))}</span> {_e(title)}</summary><div class='txt'>{ps}</div></details>"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    h = "".join(f"<th>{_e(x)}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{x if str(x).startswith('<') else _e(x)}</td>" for x in r) + "</tr>" for r in rows)
    return f"<table class='table'><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


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
    return [[x.get("month"), _money(x.get("adr")), _pct(x.get("occupancy_rate")), _money(x.get("revpar")), _money(x.get("room_revenue"))] for x in monthly or []] or [["无", "未获取", "未获取", "未获取", "未获取"]]


def _trend(monthly: list[dict[str, Any]]) -> str:
    if not monthly:
        return "暂无月度趋势数据。"
    return _table(["月份","ADR","出租率","RevPAR","门店收入"], _trend_rows(monthly))


def _channel_items(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    funnel_by={x.get("platform"):x for x in (metrics.get("ota_funnel") or {}).get("by_platform") or []}
    rep_by={x.get("platform"):x for x in (metrics.get("reputation") or {}).get("by_platform") or []}
    price_by=(metrics.get("price_ladder") or {}).get("by_platform") or {}
    promo_by=(metrics.get("promotion") or {}).get("by_platform") or {}
    items=[]
    for p in sorted(set(funnel_by)|set(rep_by)|set(price_by)|set(promo_by)):
        f=funnel_by.get(p) or {}; r=rep_by.get(p) or {}; conv=_n(f.get("payment_conversion_rate")); rating=_n(r.get("rating_avg")); neg=_n(r.get("negative_review_rate")); score=45
        if conv is not None: score += 25 if conv>=0.08 else 16 if conv>=0.04 else 6
        if rating is not None: score += 20 if rating>=4.7 else 12 if rating>=4.4 else 4
        if neg is not None: score += 10 if neg<=0.03 else 4 if neg<=0.06 else 0
        if price_by.get(p): score += 5
        score=min(100,score)
        sug="补齐该渠道浏览与支付订单，先确认转化口径。" if conv is None else "转化偏弱，优先检查价格梯度、首图卖点、评价露出和取消政策。" if conv<0.04 else "评分偏弱，先处理差评关键词和未回复评论。" if rating is not None and rating<4.5 else "渠道基础较稳，继续扩大高转化房型和活动覆盖。"
        items.append({"platform":p,"score":score,"funnel":f,"reputation":r,"product_count":price_by.get(p),"promotion_rows":promo_by.get(p),"suggestion":sug})
    return items


def _channel_cards(metrics: dict[str, Any]) -> str:
    cards=[]
    for item in _channel_items(metrics):
        p=item["platform"]; f=item["funnel"]; r=item["reputation"]; score=item["score"]
        cards.append(f"<div class='chan' data-source='{_e(p)}'><h3>{_e(_zh(p))} <span class='badge {_cls(score/100)}'>渠道健康度 {score}/100</span></h3><div class='mini-grid'><div class='mini'><label>曝光</label><strong>{_e(_num(f.get('exposure')))}</strong></div><div class='mini'><label>浏览</label><strong>{_e(_num(f.get('views')))}</strong></div><div class='mini'><label>支付订单</label><strong>{_e(_num(f.get('paid_orders')))}</strong></div><div class='mini'><label>转化率</label><strong>{_e(_pct(f.get('payment_conversion_rate')))}</strong></div><div class='mini'><label>销售额</label><strong>{_e(_money(f.get('sales_revenue')))}</strong></div><div class='mini'><label>评分/差评率</label><strong>{_e(_num(r.get('rating_avg'),2))} / {_e(_pct(r.get('negative_review_rate')))}</strong></div></div><div class='meta'>建议：{_e(item['suggestion'])}</div></div>")
    return "<div class='channel-grid'>"+"".join(cards)+"</div>" if cards else "暂无分渠道数据。"


def _channel_table(metrics: dict[str, Any]) -> str:
    rows=[]
    for item in _channel_items(metrics):
        p=item["platform"]; f=item["funnel"]; r=item["reputation"]
        rows.append(f"<tr data-source-row='{_e(p)}'><td>{_e(_zh(p))}</td><td>{item['score']}/100</td><td>{_e(_num(f.get('exposure')))}</td><td>{_e(_num(f.get('views')))}</td><td>{_e(_num(f.get('paid_orders')))}</td><td>{_e(_money(f.get('sales_revenue')))}</td><td>{_e(_pct(f.get('payment_conversion_rate')))}</td><td>{_e(_num(r.get('review_count')))}</td><td>{_e(_num(r.get('rating_avg'),2))}</td><td>{_e(_pct(r.get('negative_review_rate')))}</td><td>{_e(item['suggestion'])}</td></tr>")
    if not rows: rows.append("<tr><td colspan='11'>暂无分渠道数据</td></tr>")
    return "<table class='table'><thead><tr>"+"".join(f"<th>{_e(h)}</th>" for h in ["渠道","健康度","曝光","浏览","支付订单","销售额","转化率","评价数","评分","差评率","建议"])+"</tr></thead><tbody>"+"".join(rows)+"</tbody></table>"


def _src_module(source: str, mid: str, metrics: dict[str, Any], ms: list[dict[str, Any]]) -> dict[str, Any]:
    base={x.get("module_id"):x for x in ms or []}.get(mid,{})
    weight=_n(base.get("weight")) or 10; status=base.get("status") or "ok"; reasons=[]; rate=None
    if source=="pms":
        op=metrics.get("operating") or {}; occ=_n(op.get("occupancy_rate")); revpar=_n(op.get("revpar"))
        if mid=="M01":
            rate=0.9 if occ and occ>=0.8 else 0.7 if occ and occ>=0.65 else 0.45 if occ is not None else None
            if revpar is not None: rate=min(0.98,(rate or 0.5)+(0.08 if revpar>=120 else 0.03 if revpar>=90 else -0.04))
            reasons=[f"出租率 {_pct(occ)}",f"RevPAR {_money(revpar)}",f"ADR {_money(op.get('adr'))}"]
        else: status="data_gap"; reasons=["该模块不是 PMS 主口径"]
    elif source in {"meituan","ctrip"}:
        item=next((x for x in _channel_items(metrics) if x.get("platform")==source),None) or {}; f=item.get("funnel") or {}; r=item.get("reputation") or {}; conv=_n(f.get("payment_conversion_rate")); rating=_n(r.get("rating_avg")); neg=_n(r.get("negative_review_rate"))
        if mid=="M02": rate=0.9 if (_n(f.get("exposure")) or 0)>=2000 or (_n(f.get("views")) or 0)>=300 else 0.65 if (_n(f.get("views")) or 0)>=100 else 0.45; reasons=[f"曝光 {_num(f.get('exposure'))}",f"浏览 {_num(f.get('views'))}"]
        elif mid=="M03": rate=0.9 if conv and conv>=0.08 else 0.65 if conv and conv>=0.04 else 0.35 if conv is not None else None; reasons=[f"支付订单 {_num(f.get('paid_orders'))}",f"转化率 {_pct(conv)}",f"销售额 {_money(f.get('sales_revenue'))}"]
        elif mid=="M04": count=item.get("product_count") or 0; rate=0.85 if count>=10 else 0.65 if count else None; reasons=[f"商品映射 {count or '未获取'} 条"]
        elif mid=="M05": rows=item.get("promotion_rows") or 0; rate=0.72 if rows else 0.45; status="partial"; reasons=[f"活动/活动商品记录 {rows} 条","ROI 成本字段仍需补齐"]
        elif mid=="M06": rate=0.7 if item.get("product_count") else 0.5; status="partial"; reasons=["基于商品名、评价关键词和活动标签推断","图片/视频字段仍需接入"]
        elif mid=="M07": rate=0.9 if rating and rating>=4.7 and (neg is None or neg<=0.03) else 0.7 if rating and rating>=4.4 else 0.45 if rating is not None else None; reasons=[f"评分 {_num(r.get('rating_avg'),2)}",f"评价数 {_num(r.get('review_count'))}",f"差评率 {_pct(r.get('negative_review_rate'))}"]
        else: status="data_gap"; reasons=["该模块不是渠道主口径"]
    else:
        rate=_n(base.get("rate")); status=base.get("status") or "ok"; reasons=base.get("reasons") or ["系统综合模块"]
    if rate is not None: rate=max(0,min(1,rate)); score=round(weight*rate,2)
    else: score=0.0
    name={"M01":"经营收益","M02":"流量竞争","M03":"转化断点","M04":"价格房态","M05":"推广ROI","M06":"页面基础","M07":"口碑信任","M08":"执行复盘"}.get(mid,mid)
    return {"module_id":mid,"module_name":name,"weight":weight,"score":score,"rate":rate,"status":status,"reasons":reasons}


def _module_card(item: dict[str, Any]) -> str:
    rate=_n(item.get("rate")); pct=int(round(max(0,min(1,rate or 0))*100)) if rate is not None else 0; status=item.get("status") or "ok"; klass=_cls(status if status=="data_gap" else (rate or 0)); title="数据缺口" if status=="data_gap" else f"{pct}%"; reasons="".join(f"<span class='tag'>{_e(x)}</span>" for x in (item.get("reasons") or [])[:5])
    return f"<div class='module'><div class='module-top'><div><div class='mid'>{_e(item.get('module_id'))}</div><div class='mname'>{_e(item.get('module_name'))}</div></div><div><span class='score'>{_e(title)}</span><span class='meta'> / {_num(item.get('score'),1)}/{_num(item.get('weight'),0)}</span></div></div><div class='bar'><div class='fill {klass}' style='width:{pct}%'></div></div><div class='module-body'><span class='badge {klass}'>{_e(status)}</span>{reasons}</div></div>"


def _module_blocks(metrics: dict[str, Any], ms: list[dict[str, Any]]) -> str:
    groups=[("pms","PMS 经营底盘",["M01"])]
    for item in _channel_items(metrics): groups.append((item["platform"],f"{_zh(item['platform'])} 渠道诊断",["M02","M03","M04","M05","M06","M07"]))
    groups.append(("shared","系统与数据质量",["M08"]))
    return "".join(f"<div class='source-block' data-module-source='{_e(src)}'><div class='source-title'>{_e(title)} <span class='badge neutral'>{_e(src)}</span></div><div class='source-grid'>{''.join(_module_card(_src_module(src,mid,metrics,ms)) for mid in mids)}</div></div>" for src,title,mids in groups)


def _metric_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    op=metrics.get("operating") or {}; funnel=metrics.get("ota_funnel") or {}; rep=metrics.get("reputation") or {}; price=metrics.get("price_ladder") or {}; promo=metrics.get("promotion") or {}; events=metrics.get("nearby_events") or {}
    items=[("RevPAR",_money(op.get("revpar")),"收益锚点"),("ADR",_money(op.get("adr")),"价格水平"),("出租率",_pct(op.get("occupancy_rate")),"经营效率"),("门店收入",_money(op.get("room_revenue")),"经营结果"),("曝光量",_num(funnel.get("exposure")),"流量入口"),("浏览量",_num(funnel.get("views")),"详情页访问"),("支付订单",_num(funnel.get("paid_orders")),"转化结果"),("浏览→支付转化率",_pct(funnel.get("payment_conversion_rate")),"转化结果"),("商品最低价",_money(price.get("min_price")),"价格梯度"),("活动数",_num(promo.get("activity_count")),"推广覆盖"),("近期周边活动",_num(events.get("upcoming_60d_count")),"需求事件"),("平台评分",_num(rep.get("rating_avg"),2),"信任锚点"),("差评率",_pct(rep.get("negative_review_rate")),"口碑风险")]
    rows=[]
    for a,b,c in items:
        cls="neutral" if b=="未获取" else "info"; text="缺失" if b=="未获取" else "已获取"; rows.append([a,b,c,f"<span class='badge {cls}'>{text}</span>"])
    return rows


def _missing_rows(dq: dict[str, Any]) -> list[list[Any]]:
    rows=[]
    for sec,fields in (dq.get("missing_fields") or {}).items():
        for f in fields or []: rows.append([f,"<span class='badge warn'>missing</span>","补采或检查字段映射",sec])
    return rows or [["无关键缺失字段","<span class='badge good'>ok</span>","继续保持字段采集稳定","系统计算"]]


def build_markdown(result: dict[str, Any]) -> str:
    lines=["# 酒店 OTA 全面诊断报告", "", f"- final_score: {result.get('final_score')}", f"- risk_level: {result.get('risk_level')}", f"- status: {result.get('status')}"]
    for m in result.get("module_scores") or []:
        lines.append(f"- {m.get('module_id')} {m.get('module_name')}: {m.get('score')}/{m.get('weight')} status={m.get('status')}")
    return "\n".join(lines)


def build_html(result: dict[str, Any]) -> str:
    metrics=result.get("metrics") or {}; op=metrics.get("operating") or {}; funnel=metrics.get("ota_funnel") or {}; price=metrics.get("price_ladder") or {}; comp=metrics.get("competitors") or {}; dq=result.get("data_quality") or {}; missing=_missing_count(dq); credibility=max(0,100-missing*10); score=_n(result.get("final_score")) or 0; risk=str(result.get("risk_level") or "medium").lower(); hotel=result.get("hotel_name") or result.get("hotel_id") or "酒店"; platform=result.get("platform") or "multi"; meta=f"{hotel}｜{_zh(platform)}｜{result.get('period_start')} 至 {result.get('period_end')}｜生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    cap=[]
    if missing>3: cap.append("C06 数据可信度封顶：关键字段缺失较多，部分判断按保守规则估计。")
    if result.get("status")!="ok": cap.append("当前报告为 partial，建议补齐缺失字段后复算。")
    if not cap: cap.append("未触发明显封顶规则；仍建议结合真实运营经验复核。")
    cap_html="".join(f"<li>{_e(x)}</li>" for x in cap)
    notes=result.get("notes") or []; note_rows=[[f"<span class='badge {_cls(n.get('level'))}'>{_e(n.get('level'))}</span>",n.get("title"),n.get("evidence"),n.get("suggestion")] for n in notes] or [["<span class='badge neutral'>info</span>","暂无结论","暂无","补充数据后重新诊断"]]
    actions="".join(f"<li>{_e(x)}</li>" for x in result.get("actions") or []) or "<li>补齐数据后重新生成诊断。</li>"
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>酒店 OTA 全面诊断报告</title><style>{CSS}</style></head><body>
<header class='top'><div class='top-inner'><div><h1>酒店 OTA 全面诊断报告</h1><div class='meta'>{_e(meta)}</div></div><div class='actions'><div class='selectbox'><label>选择板块</label><select id='channelSelector' onchange='switchBlock(this.value)'><option value='all'>全部</option><option value='pms'>PMS</option><option value='meituan'>美团</option><option value='ctrip'>携程</option><option value='shared'>系统/数据</option></select></div><button class='btn' onclick='window.print()'>导出报告</button></div></div></header>
<div class='layout'><nav class='side'><a href='#overview'>顶部总览</a><a href='#trend'>月度趋势</a><a href='#modules'>模块诊断</a><a href='#metrics'>经营指标</a><a href='#funnel'>流量漏斗</a><a href='#channels'>分渠道指标</a><a href='#missing'>补采提示</a><a href='#actions'>诊断结论</a></nav><main>
<section class='card' id='overview'><div class='head'><div><h2>顶部总览</h2><p>诊断结果概览</p></div><span class='badge {_cls(risk)}'>风险：{_e(_zh(risk))}</span></div><div class='body'><div class='grid4'>{_kpi('总分',f'{round(score):.0f}/100',f'原始分 {score:.1f}')}{_kpi('数据可信度',f'{credibility}%','字段完整度')}{_kpi('风险等级',_zh(risk),'基于模块得分判定',_cls(risk))}{_kpi('数据来源',_zh(platform),_source_summary(dq))}</div><div class='cap-alert'><b>封顶/校准规则</b><span><ul>{cap_html}</ul></span><span class='badge warn'>按规则校准</span></div>{_analysis(result,'综合诊断分析','overview',[f'综合诊断结论：酒店当前处于{_zh(risk)}状态，综合得分 {round(score):.0f}/100。',f'数据可信度 {credibility}%，当前缺失字段 {missing} 个。','核心短板请优先查看 PMS、各 OTA 渠道和系统数据质量三个分组。'])}</div></section>
<section class='card' id='trend' data-module-source='pms'><div class='head'><div><h2>月度经营趋势</h2><p>PMS 经营趋势</p></div></div><div class='body'>{_trend(op.get('monthly_trend') or [])}</div></section>
<section class='card' id='modules'><div class='head'><div><h2>模块诊断详情</h2><p>按 PMS、各 OTA 渠道、系统/数据质量拆分；右上角选择板块会同步过滤。</p></div></div><div class='body'>{_module_blocks(metrics,result.get('module_scores') or [])}{_analysis(result,'模块联动分析','modules',['模块诊断已按 PMS、OTA 渠道和系统数据质量拆开；先处理低分渠道，再补齐 partial/data_gap 的数据字段。'])}</div></section>
<section class='card' id='metrics' data-module-source='pms'><div class='head'><div><h2>经营指标</h2><p>PMS 经营数据</p></div></div><div class='body'>{_table(['指标','当前值','口径','状态'],_metric_rows(metrics))}{_analysis(result,'指标解读','metrics',[f"RevPAR {_money(op.get('revpar'))} = ADR {_money(op.get('adr'))} × 出租率 {_pct(op.get('occupancy_rate'))}。",'出租率使用所选周期内总售出间夜 / 总可售房晚；如果日表缺少出租率字段，会用 room_nights 或 sold_rooms 除以 room_count 计算。'])}</div></section>
<section class='card' id='funnel'><div class='head'><div><h2>流量漏斗</h2><p>曝光 → 浏览 → 支付转化路径</p></div></div><div class='body'><div class='grid4'>{_kpi('曝光量',_num(funnel.get('exposure')),'列表页展示')}{_kpi('浏览量',_num(funnel.get('views')),'详情页访问')}{_kpi('支付订单',_num(funnel.get('paid_orders')),'支付结果')}{_kpi('支付转化率',_pct(funnel.get('payment_conversion_rate')),'浏览→支付')}</div>{_analysis(result,'流量漏斗诊断','funnel',[f"曝光→浏览：{_pct(funnel.get('exposure_to_view_rate'))}。",f"浏览→支付：{_pct(funnel.get('payment_conversion_rate'))}。",'若曝光充足但支付不足，优先检查价格梯度、评论信任和退改政策。'])}</div></section>
<section class='card' id='channels'><div class='head'><div><h2>分渠道得分与指标</h2><p>按渠道展开曝光、浏览、支付、销售额、评分、差评率和建议。</p></div></div><div class='body'>{_channel_cards(metrics)}{_channel_table(metrics)}{_analysis(result,'分渠道诊断','channels',['分渠道指标按平台拆开，重点比较曝光、浏览、支付订单、销售额、评分和差评率。'])}</div></section>
<section class='card' id='price'><div class='head'><div><h2>价格与竞品</h2><p>商品价格梯度、竞品价格和价格跳水风险。</p></div></div><div class='body'><div class='grid4'>{_kpi('商品数',(price.get('product_count')),'OTA 商品映射')}{_kpi('最低价',_money(price.get('min_price')),'引流价')}{_kpi('最高价',_money(price.get('max_price')),'价格上沿')}{_kpi('竞品均价',_money(comp.get('competitor_avg_price')),'竞品参考')}</div>{_analysis(result,'价格诊断解读','price',['价格不是单点判断，需要同时看引流价、全日价、团购价、钟点房价和竞品均价，避免价格体系混乱。'])}</div></section>
<section class='card' id='missing' data-module-source='shared'><div class='head'><div><h2>补采提示</h2><p>缺失字段、影响、采集方式。</p></div></div><div class='body'>{_table(['缺失字段','当前状态','处理建议','责任来源'],_missing_rows(dq))}{_analysis(result,'数据完整度分析','missing',[f'当前缺失字段数为 {missing}。缺失字段不等于经营差，但会降低评分可信度。'])}</div></section>
<section class='card' id='actions'><div class='head'><div><h2>诊断结论与动作建议</h2><p>只输出营销建议，不执行调价和审批。</p></div></div><div class='body'><h3>问题结论</h3>{_table(['等级','标题','证据','建议'],note_rows)}<h3>动作建议</h3><ol>{actions}</ol>{_analysis(result,'动作优先级分析','actions',['先处理影响转化和信任的动作，再处理推广 ROI 数据补采。'])}</div></section>
</main></div><script>function switchBlock(v){{document.querySelectorAll('[data-source]').forEach(function(e){{e.classList.toggle('hidden',v!=='all'&&e.getAttribute('data-source')!==v);}});document.querySelectorAll('[data-source-row]').forEach(function(e){{e.classList.toggle('hidden',v!=='all'&&e.getAttribute('data-source-row')!==v);}});document.querySelectorAll('[data-module-source]').forEach(function(e){{e.classList.toggle('hidden',v!=='all'&&e.getAttribute('data-module-source')!==v);}});}}document.addEventListener('DOMContentLoaded',function(){{switchBlock(document.getElementById('channelSelector').value||'all');}});</script></body></html>"""


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    path=Path(output_dir); path.mkdir(parents=True, exist_ok=True)
    json_path=path/"report.json"; md_path=path/"report.md"; html_path=path/"report.html"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(result), encoding="utf-8")
    html_path.write_text(build_html(result), encoding="utf-8")
    return {"report_json":str(json_path),"report_markdown":str(md_path),"report_html":str(html_path)}
