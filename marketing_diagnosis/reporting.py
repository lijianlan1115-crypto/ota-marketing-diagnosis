from pathlib import Path
import html
import json
from datetime import datetime


HTML_STYLE = """
:root {
  --bg:#f6f7f9; --panel:#ffffff; --ink:#1d2430; --muted:#667085;
  --line:#d9dee8; --line-soft:#edf0f5; --blue:#2563eb; --cyan:#0891b2;
  --green:#168a4a; --amber:#b7791f; --red:#c2413a; --purple:#6d5bd0;
  --shadow:0 8px 24px rgba(22,34,51,.08);
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif; font-size:14px; line-height:1.45; }
.app-header { position:sticky; top:0; z-index:10; background:rgba(255,255,255,.96); border-bottom:1px solid var(--line); backdrop-filter:blur(10px); }
.header-inner { max-width:1440px; margin:0 auto; padding:14px 24px; display:grid; grid-template-columns:1fr auto; gap:16px; align-items:center; }
.title-block h1 { margin:0; font-size:22px; font-weight:700; }
.title-block p { margin:4px 0 0; color:var(--muted); font-size:13px; }
.actions { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.btn { border:1px solid var(--line); background:var(--panel); color:var(--ink); border-radius:8px; min-height:36px; padding:0 12px; font-weight:600; cursor:pointer; }
.btn.primary { background:var(--ink); border-color:var(--ink); color:#fff; }
.layout { max-width:1440px; margin:0 auto; padding:20px 24px 48px; display:grid; grid-template-columns:220px minmax(0,1fr); gap:20px; }
.sidebar { position:sticky; top:84px; align-self:start; border:1px solid var(--line); background:var(--panel); border-radius:8px; box-shadow:var(--shadow); overflow:hidden; }
.sidebar a { display:block; padding:11px 14px; color:#344054; text-decoration:none; border-bottom:1px solid var(--line-soft); font-weight:600; font-size:13px; }
.sidebar a:last-child { border-bottom:0; }
.sidebar a:hover { background:#f2f6fb; color:var(--blue); }
main { display:grid; gap:18px; }
section { background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); overflow:hidden; }
.section-head { padding:16px 18px; display:flex; align-items:flex-start; justify-content:space-between; gap:12px; border-bottom:1px solid var(--line-soft); }
.section-head h2 { margin:0; font-size:17px; line-height:1.2; }
.section-head p { margin:5px 0 0; color:var(--muted); font-size:13px; }
.section-body { padding:18px; }
.status { display:inline-flex; align-items:center; justify-content:center; min-height:24px; padding:0 8px; border-radius:999px; font-size:12px; font-weight:700; white-space:nowrap; }
.status.good { color:var(--green); background:#e8f5ee; }
.status.warn { color:var(--amber); background:#fff4dc; }
.status.bad { color:var(--red); background:#fdebea; }
.status.info { color:var(--blue); background:#eaf1ff; }
.status.neutral { color:#475467; background:#eef1f5; }
.kpi-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }
.kpi { border:1px solid var(--line); border-radius:8px; padding:14px; min-height:116px; display:grid; align-content:space-between; background:#fff; }
.kpi label { color:var(--muted); font-size:13px; font-weight:700; }
.kpi strong { display:block; margin-top:8px; font-size:28px; line-height:1; }
.kpi span { margin-top:9px; color:#475467; font-size:13px; }
.cap-alert { margin-top:12px; border:1px solid #f0cd7a; background:#fff8e6; border-radius:8px; padding:12px 14px; display:grid; grid-template-columns:auto 1fr auto; gap:12px; align-items:center; }
.cap-alert b { color:#7a4d08; }
.score-table,.data-table { width:100%; border-collapse:collapse; }
th,td { padding:10px 10px; border-bottom:1px solid var(--line-soft); text-align:left; vertical-align:middle; }
th { color:#475467; font-size:12px; font-weight:700; background:#f8fafc; }
tr:last-child td { border-bottom:0; }
.two-col { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:16px; }
.subpanel { border:1px solid var(--line); border-radius:8px; overflow:hidden; background:#fff; }
.subpanel h3 { margin:0; padding:12px 14px; border-bottom:1px solid var(--line-soft); font-size:15px; background:#fafbfc; }
.subpanel-content { padding:14px; }
.funnel { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin-bottom:14px; }
.funnel-step { border:1px solid var(--line); border-radius:8px; padding:13px; background:#fbfcfe; }
.funnel-step label { color:var(--muted); font-size:12px; font-weight:700; }
.funnel-step strong { display:block; margin-top:6px; font-size:24px; }
.funnel-step span { display:block; margin-top:4px; color:var(--muted); font-size:12px; }
.analysis-card { margin-top:16px; border:1px solid #c7d2fe; border-left:4px solid #6366f1; border-radius:8px; background:#eef2ff; overflow:hidden; }
.analysis-card[open] summary { border-bottom:1px solid #c7d2fe; }
.analysis-card summary { cursor:pointer; padding:10px 16px; font-weight:700; font-size:14px; color:#4338ca; background:linear-gradient(135deg,#e0e7ff,#eef2ff); display:flex; align-items:center; gap:8px; list-style:none; }
.analysis-card summary::-webkit-details-marker { display:none; }
.analysis-card summary .ai-badge { display:inline-flex; align-items:center; gap:4px; font-size:11px; padding:2px 10px; border-radius:999px; background:linear-gradient(135deg,#6366f1,#8b5cf6); color:#fff; font-weight:700; letter-spacing:.5px; }
.analysis-card .analysis-body { padding:14px 18px; font-size:13px; line-height:1.75; color:#312e81; background:#eef2ff; }
.analysis-card .analysis-body p { margin:0 0 10px; }
.module-cards { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }
.module-card { border:1px solid var(--line); border-radius:10px; background:#fff; overflow:hidden; }
.module-card-header { padding:16px 18px 12px; display:grid; grid-template-columns:1fr auto; gap:10px; align-items:start; }
.module-card-header .mod-id { font-size:12px; font-weight:800; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }
.module-card-header .mod-name { margin:2px 0 0; font-size:16px; font-weight:700; line-height:1.3; }
.module-card-score { text-align:right; }
.module-card-score .big-score { font-size:30px; font-weight:800; line-height:1; }
.module-card-score .of { font-size:13px; color:var(--muted); }
.module-card-bar { padding:0 18px 6px; }
.bar-track { height:8px; background:#e9edf3; border-radius:999px; overflow:hidden; }
.bar-fill { height:100%; border-radius:999px; background:var(--blue); }
.bar-fill.good { background:var(--green); } .bar-fill.warn { background:var(--amber); } .bar-fill.bad { background:var(--red); }
.module-card-body { padding:0 18px 14px; font-size:13px; color:#475467; line-height:1.6; display:flex; flex-wrap:wrap; align-items:flex-start; gap:6px; }
.module-card-body .reason { display:inline-block; margin:0; padding:2px 8px; background:#f2f5f9; border-radius:4px; font-size:12px; color:#475467; white-space:nowrap; max-width:100%; overflow:hidden; text-overflow:ellipsis; }
.module-card-analysis { margin:0 18px 14px; padding:12px 14px; background:#eef2ff; border-radius:8px; border:1px solid #c7d2fe; border-left:3px solid #818cf8; font-size:13px; line-height:1.65; color:#312e81; }
.module-card-analysis strong { color:#1e1b4b; }
pre { white-space:pre-wrap; word-break:break-word; background:#0f172a; color:#e5e7eb; border-radius:8px; padding:14px; overflow:auto; }
@media (max-width:980px) { .layout { grid-template-columns:1fr; padding:14px; } .sidebar { position:static; display:grid; grid-template-columns:repeat(2,1fr); } .kpi-grid,.two-col,.module-cards,.funnel { grid-template-columns:1fr; } .header-inner { grid-template-columns:1fr; padding:12px 14px; } .actions { justify-content:flex-start; } }
@media print { body { background:#fff; } .app-header,.sidebar,.dashboard-only { display:none!important; } .layout { display:block; padding:0; max-width:none; } main { display:block; } section { box-shadow:none; border:0; border-radius:0; page-break-inside:avoid; } }
"""

MODULE_LABELS = {
    "M01": ("经营收益", "PMS jy01"),
    "M02": ("流量竞争", "美团/携程 OTA"),
    "M03": ("转化断点", "美团/携程 OTA"),
    "M04": ("价格房态", "PMS + OTA 商品"),
    "M05": ("推广ROI", "美团/携程推广"),
    "M06": ("页面基础", "页面采集/商品映射"),
    "M07": ("口碑信任", "美团/携程评价"),
    "M08": ("执行复盘", "系统计算"),
}


def _text(value):
    if value is None:
        return "未获取"
    if isinstance(value, float):
        return f"{value:.4f}" if abs(value) < 1 else f"{value:.2f}"
    return str(value)


def _esc(value):
    return html.escape(_text(value), quote=True)


def _pct(value):
    try:
        if value is None:
            return "未获取"
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return _text(value)


def _money(value):
    try:
        if value is None:
            return "未获取"
        return f"¥{float(value):.2f}"
    except (TypeError, ValueError):
        return _text(value)


def _num(value):
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _risk_zh(risk):
    return {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(str(risk or "").lower(), _text(risk))


def _status_class(rate_or_risk):
    if isinstance(rate_or_risk, str):
        return {"high": "bad", "medium": "warn", "low": "good", "data_gap": "neutral", "partial": "warn", "ok": "good"}.get(rate_or_risk.lower(), "neutral")
    value = _num(rate_or_risk)
    if value is None:
        return "neutral"
    if value >= 0.8:
        return "good"
    if value >= 0.6:
        return "warn"
    return "bad"


def _status_text(rate, status="ok"):
    if status == "data_gap":
        return "数据缺口"
    value = _num(rate)
    if value is None:
        return "缺失"
    if value >= 0.8:
        return "良好"
    if value >= 0.6:
        return "需要优化"
    return "严重短板"


def _fmt_metric(key, value):
    if key in {"occupancy_rate", "payment_conversion_rate", "peer_avg_conversion_rate", "negative_review_rate"}:
        return _pct(value)
    if key in {"adr", "revpar", "room_revenue", "min_price", "max_price", "competitor_avg_price", "own_min_price_vs_competitor_avg_gap"}:
        return _money(value)
    return _text(value)


def build_markdown(result):
    lines = ["# 酒店 OTA 全面诊断报告", ""]
    lines.append(f"- final_score: {result.get('final_score', 'missing')}")
    lines.append(f"- risk_level: {result.get('risk_level', 'missing')}")
    lines.append(f"- status: {result.get('status', 'missing')}")
    lines.append("")
    lines.append("## Module Scores")
    for item in result.get("module_scores") or []:
        lines.append(f"- {item.get('module_id')} {item.get('module_name')}: {item.get('score')}/{item.get('weight')} ({item.get('rate')}) status={item.get('status')}")
    lines.append("")
    lines.append("## Notes")
    for item in result.get("notes") or []:
        lines.append(f"- [{item.get('level')}] {item.get('title')}: {item.get('suggestion')}")
    lines.append("")
    lines.append("## Actions")
    for index, item in enumerate(result.get("actions") or [], 1):
        lines.append(f"{index}. {item}")
    lines.append("")
    lines.append("## Data Quality")
    lines.append(json.dumps(result.get("data_quality") or {}, ensure_ascii=False, indent=2))
    return "\n".join(lines)


def _kpi(label, value, hint="", class_name=""):
    cls = f" class='{_esc(class_name)}'" if class_name else ""
    return f"<div class='kpi'><label>{_esc(label)}</label><strong{cls}>{_esc(value)}</strong><span>{_esc(hint)}</span></div>"


def _analysis(title, paragraphs, open_=True):
    body = "".join(f"<p>{p}</p>" for p in paragraphs if p)
    flag = " open" if open_ else ""
    return f"<details class='analysis-card'{flag}><summary><span class='ai-badge'>AI 分析</span>{_esc(title)}</summary><div class='analysis-body'>{body}</div></details>"


def _module_card(module):
    module_id = module.get("module_id") or "M??"
    label, source = MODULE_LABELS.get(module_id, (module.get("module_name") or module_id, "系统计算"))
    score = _num(module.get("score")) or 0
    weight = _num(module.get("weight")) or 0
    rate = _num(module.get("rate"))
    status = module.get("status") or "ok"
    if rate is None and weight and status != "data_gap":
        rate = score / weight
    rate_for_bar = max(0, min(1, rate if rate is not None else 0))
    pct = int(round(rate_for_bar * 100))
    klass = _status_class(status if status == "data_gap" else rate_for_bar)
    reasons = module.get("reasons") or []
    reason_html = "".join(f"<span class='reason'>{_esc(reason)}</span>" for reason in reasons[:8])
    if not reason_html:
        reason_html = "<span class='reason'>系统评分</span>"
    source_fields = module.get("source_fields") or []
    if source_fields:
        reason_html += "".join(f"<span class='reason'>source: {_esc(field)}</span>" for field in source_fields[:5])
    analysis = _module_analysis(module_id, label, rate_for_bar, status)
    color = {"good": "var(--green)", "warn": "var(--amber)", "bad": "var(--red)", "neutral": "#475467"}.get(klass, "var(--blue)")
    score_text = "数据缺口" if status == "data_gap" else f"{pct}%"
    return f"""<div class='module-card'>
  <div class='module-card-header'>
    <div><div class='mod-id'>{_esc(module_id)} <span style='font-size:11px;color:var(--muted);font-weight:400'>数据: {_esc(source)}</span></div><div class='mod-name'>{_esc(label)}</div></div>
    <div class='module-card-score'><span class='big-score' style='color:{color}'>{_esc(score_text)}</span><span class='of'> / {_esc(score)}/{_esc(weight)}</span></div>
  </div>
  <div class='module-card-bar'><div class='bar-track'><div class='bar-fill {klass}' style='width:{pct}%'></div></div></div>
  <div class='module-card-body'><span class='status {klass}'>{_esc(_status_text(rate, status))}</span>{reason_html}</div>
  <div class='module-card-analysis'>{analysis}</div>
</div>"""


def _module_analysis(module_id, label, rate, status="ok"):
    if status == "data_gap":
        return f"⚪ <strong>{_esc(label)}</strong> 当前为数据缺口。系统没有使用默认值冒充真实结论；请先接入对应表或字段后再评分。"
    pct = int(round(rate * 100))
    if rate < 0.45:
        prefix = "🔴"
        tone = "严重短板"
    elif rate < 0.7:
        prefix = "🟡"
        tone = "需要优化"
    else:
        prefix = "🟢"
        tone = "相对健康"
    advice = {
        "M01": "用 RevPAR 而不是单纯 ADR 判断经营质量，关注价格与出租率平衡。",
        "M02": "继续拆解曝光来源、自然流量占比和竞争圈排名，避免只靠推广买流量。",
        "M03": "重点排查曝光到浏览、浏览到支付的断点，包括首图、卖点、价格和退改政策。",
        "M04": "梳理全日房、钟点房、团购和活动价，保持清晰价格梯度。",
        "M05": "补齐推广花费、点击、推广订单和 ROI，避免只看曝光不看产出。",
        "M06": "优化首图、视频、房型卖点、标签入口和权益配置。",
        "M07": "将好评关键词反哺页面卖点，差评关键词进入整改清单。",
        "M08": "建立诊断、整改、验证、复盘闭环，并记录动作完成率。",
    }.get(module_id, "继续补充数据并形成可验证的整改动作。")
    return f"{prefix} <strong>{_esc(label)}</strong> 得分率 {pct}%，状态：{_esc(tone)}。<br><br>{_esc(advice)}"


def _table(headers, rows, class_name="data-table"):
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{cell if str(cell).startswith('<') else _esc(cell)}</td>" for cell in row) + "</tr>")
    return f"<table class='{class_name}'><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _source_rows(data_quality):
    rows = []
    for source in data_quality.get("source_diagnostics") or []:
        for key, diag in (source.get("tables") or {}).items():
            rows.append([
                key,
                diag.get("table"),
                diag.get("rows"),
                f"<span class='status {_status_class(diag.get('status'))}'>{_esc(diag.get('status'))}</span>",
                diag.get("where") or "—",
                ", ".join((diag.get("fields_sample") or [])[:12]) or diag.get("aggregation") or "—",
            ])
    if not rows:
        rows.append(["无", "无 source_diagnostics", 0, "<span class='status bad'>missing</span>", "—", "当前报告无法证明数据来自哪张表"])
    return rows


def _metric_rows(metrics, data_quality=None):
    operating = metrics.get("operating") or {}
    funnel = metrics.get("ota_funnel") or {}
    reputation = metrics.get("reputation") or {}
    price = metrics.get("price_ladder") or {}
    items = [
        ("RevPAR（每间可售房收入）", operating.get("revpar"), "收益锚点", "PMS jy01", "revpar"),
        ("ADR（平均房价）", operating.get("adr"), "价格水平", "PMS jy01 / OTA", "adr"),
        ("出租率", operating.get("occupancy_rate"), "经营效率", "PMS jy01", "occupancy_rate"),
        ("门店收入", operating.get("room_revenue"), "经营结果", "PMS jy01", "room_revenue"),
        ("曝光量", funnel.get("exposure"), "流量入口", "美团/携程 OTA", "exposure"),
        ("浏览量（UV）", funnel.get("views"), "详情页访问", "美团/携程 OTA", "views"),
        ("浏览→支付转化率", funnel.get("payment_conversion_rate"), "转化结果", "美团/携程 OTA", "payment_conversion_rate"),
        ("商品最低价", price.get("min_price"), "价格梯度", "OTA 商品", "min_price"),
        ("平台评分", reputation.get("rating_avg"), "信任锚点", "美团/携程评价", "rating_avg"),
        ("差评率", reputation.get("negative_review_rate"), "口碑风险", "美团/携程评价", "negative_review_rate"),
    ]
    rows = []
    for label, value, scope, source, key in items:
        cls = "neutral" if value is None else "good"
        status = "缺失" if value is None else "已获取"
        rows.append([label, _fmt_metric(key, value), scope, f"<span style='font-size:11px;color:var(--muted)'>{_esc(source)}</span>", f"<span class='status {cls}'>{status}</span>"])
    return rows


def _missing_rows(data_quality):
    missing = data_quality.get("missing_fields") or {}
    rows = []
    for section, fields in missing.items():
        for field in fields or []:
            rows.append([field, "<span class='status warn'>missing</span>", "补采或检查字段映射", section])
    if not rows:
        rows.append(["无关键缺失字段", "<span class='status good'>ok</span>", "继续保持字段采集稳定", "系统计算"])
    return rows


def _missing_count(data_quality):
    missing = data_quality.get("missing_fields") or {}
    return sum(len(v or []) for v in missing.values())


def build_html(result):
    metrics = result.get("metrics") or {}
    operating = metrics.get("operating") or {}
    funnel = metrics.get("ota_funnel") or {}
    reputation = metrics.get("reputation") or {}
    price = metrics.get("price_ladder") or {}
    competitors = metrics.get("competitors") or {}
    data_quality = result.get("data_quality") or {}
    missing_count = _missing_count(data_quality)
    credibility = max(0, 100 - missing_count * 10)
    final_score = _num(result.get("final_score")) or 0
    risk = str(result.get("risk_level") or "medium").lower()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title_meta = f"{_text(result.get('hotel_name') or result.get('hotel_id') or '酒店')}｜{_text(result.get('platform') or 'multi')}｜{_text(result.get('period_start'))} 至 {_text(result.get('period_end'))}｜生成时间：{generated_at}"
    module_cards = "".join(_module_card(m) for m in result.get("module_scores") or [])
    if not module_cards:
        module_cards = "<div class='section-note'>暂无模块评分。</div>"
    notes = result.get("notes") or []
    note_rows = [[f"<span class='status {_status_class(n.get('level'))}'>{_esc(n.get('level'))}</span>", n.get("title"), n.get("evidence"), n.get("suggestion")] for n in notes]
    if not note_rows:
        note_rows = [["<span class='status neutral'>info</span>", "暂无结论", "暂无", "补充数据后重新诊断"]]
    action_items = "".join(f"<li>{_esc(item)}</li>" for item in result.get("actions") or []) or "<li>补齐数据后重新生成诊断。</li>"
    cap_items = []
    if missing_count > 3:
        cap_items.append("C06 数据可信度封顶：关键字段缺失较多，部分判断按保守规则估计。")
    if result.get("status") != "ok":
        cap_items.append("数据补采提示：当前报告为 partial，建议补齐缺失字段后复算。")
    if not cap_items:
        cap_items.append("未触发明显封顶规则；仍建议结合真实运营经验复核。")
    cap_html = "".join(f"<li>{_esc(item)}</li>" for item in cap_items)
    raw_json = json.dumps(result, ensure_ascii=False, indent=2)
    data_quality_json = json.dumps(data_quality, ensure_ascii=False, indent=2)
    metric_analysis = "当前关键指标已汇总展示。若部分指标为未获取，应优先检查字段映射和对应数据表是否存在有效记录。"
    missing_analysis = f"当前缺失字段数为 {missing_count}。缺失字段不等于经营差，但会降低评分可信度，相关模块采用保守估计。"
    source_analysis = "本节用于核验报告是否真的查到数据库。若表状态为 empty/error，相关报告值不能当作真实经营结论。"
    return f"""<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>酒店 OTA 全面诊断报告</title>
  <style>{HTML_STYLE}</style>
</head>
<body>
  <header class='app-header'>
    <div class='header-inner'>
      <div class='title-block'><h1>酒店 OTA 全面诊断报告</h1><p>{_esc(title_meta)}</p></div>
      <div class='actions'><button class='btn primary' onclick='window.print()'>导出报告</button></div>
    </div>
  </header>
  <div class='layout'>
    <nav class='sidebar dashboard-only'>
      <a href='#overview'>顶部总览卡片</a>
      <a href='#source'>数据来源核验</a>
      <a href='#trend'>月度趋势图</a>
      <a href='#modules'>模块诊断</a>
      <a href='#metrics'>经营指标</a>
      <a href='#funnel'>流量漏斗</a>
      <a href='#price'>价格与竞品</a>
      <a href='#missing'>补采提示</a>
      <a href='#raw'>原始结果</a>
    </nav>
    <main>
      <section id='overview'>
        <div class='section-head'><div><h2>顶部总览卡片</h2><p>诊断结果概览</p></div><span class='status {_status_class(risk)}'>风险：{_esc(_risk_zh(risk))}</span></div>
        <div class='section-body'>
          <div class='kpi-grid'>
            {_kpi('总分', f'{round(final_score):.0f} / 100', f'原始分 {final_score:.1f}')}
            {_kpi('数据可信度', f'{credibility}%', '字段完整度')}
            {_kpi('风险等级', _risk_zh(risk), '基于模块得分判定', _status_class(risk))}
            {_kpi('数据来源', result.get('platform') or 'multi', result.get('data_source') or 'database')}
          </div>
          <div class='cap-alert'><b>封顶/校准规则</b><span><ul>{cap_html}</ul></span><span class='status warn'>按规则校准</span></div>
          {_analysis('综合诊断分析', [f'<strong>综合诊断结论</strong>：酒店当前处于<strong>{_esc(_risk_zh(risk))}</strong>状态，综合得分 {round(final_score):.0f}/100。', f'数据可信度 {credibility}%，当前缺失字段 {missing_count} 个。', '核心短板请优先查看 M01-M08 模块卡片中的红色、黄色或数据缺口模块。'])}
        </div>
      </section>
      <section id='source'>
        <div class='section-head'><div><h2>数据来源核验</h2><p>展示实际查询的数据库表、行数、过滤条件和字段样本。</p></div></div>
        <div class='section-body'>{_table(['逻辑名','真实表','行数','状态','过滤条件','字段样本/聚合口径'], _source_rows(data_quality))}{_analysis('数据接口核验', [source_analysis])}</div>
      </section>
      <section id='trend'>
        <div class='section-head'><div><h2>月度趋势图</h2><p>趋势图区域；当前 MVP 先输出关键趋势占位，后续接入 jy03 月度数据。</p></div></div>
        <div class='section-body'><div class='two-col'><div class='subpanel'><h3>RevPAR / ADR 趋势</h3><div class='subpanel-content'>暂无 jy03 月度趋势数据；接入后在此绘制 SVG 趋势线。</div></div><div class='subpanel'><h3>趋势解读</h3><div class='subpanel-content'>当前报告先以历史日经营和 OTA 漏斗作为诊断依据。</div></div></div></div>
      </section>
      <section id='modules'>
        <div class='section-head'><div><h2>模块诊断详情</h2><p>8 个诊断模块独立评估；数据没接上的模块显示为数据缺口，不使用默认值冒充结论。</p></div></div>
        <div class='section-body'><div class='module-cards'>{module_cards}</div></div>
      </section>
      <section id='metrics'>
        <div class='section-head'><div><h2>经营指标</h2><p>关键经营数据一览</p></div></div>
        <div class='section-body'>{_table(['指标','当前值','口径','数据来源','状态'], _metric_rows(metrics, data_quality))}{_analysis('指标解读', [metric_analysis])}</div>
      </section>
      <section id='funnel'>
        <div class='section-head'><div><h2>流量与转化漏斗</h2><p>曝光、浏览、支付订单、支付转化。</p></div></div>
        <div class='section-body'><div class='funnel'>
          <div class='funnel-step'><label>曝光</label><strong>{_esc(funnel.get('exposure'))}</strong><span>OTA 入口流量</span></div>
          <div class='funnel-step'><label>浏览</label><strong>{_esc(funnel.get('views'))}</strong><span>详情页访问</span></div>
          <div class='funnel-step'><label>支付订单</label><strong>{_esc(funnel.get('paid_orders'))}</strong><span>最终订单</span></div>
        </div>{_analysis('流量漏斗解读', ['若曝光充足但浏览不足，优先优化首图和入口标签；若浏览充足但支付不足，优先检查价格梯度、评论信任和退改政策。'])}</div>
      </section>
      <section id='price'>
        <div class='section-head'><div><h2>价格与竞品</h2><p>商品价格梯度、竞品价格和价格跳水风险。</p></div></div>
        <div class='section-body'><div class='kpi-grid'>
          {_kpi('商品数', price.get('product_count'), 'OTA 商品映射')}
          {_kpi('最低价', _money(price.get('min_price')), '引流价')}
          {_kpi('最高价', _money(price.get('max_price')), '价格上沿')}
          {_kpi('竞品均价', _money(competitors.get('competitor_avg_price')), '竞品参考')}
        </div>{_analysis('价格诊断解读', ['价格不是单点判断，需要同时看引流价、全日价、团购价、钟点房价和竞品均价，避免价格体系混乱。'])}</div>
      </section>
      <section id='missing'>
        <div class='section-head'><div><h2>补采提示</h2><p>缺失字段、影响、采集方式；数据缺失不等于经营差，但影响可信度。</p></div></div>
        <div class='section-body'>{_table(['缺失字段','当前状态','处理建议','责任来源'], _missing_rows(data_quality))}{_analysis('数据完整度分析', [missing_analysis, '所有基于缺失字段的判断均采用保守估计，实际得分可能被低估或高估。'])}</div>
      </section>
      <section id='actions'>
        <div class='section-head'><div><h2>诊断结论与动作建议</h2><p>只输出营销建议，不执行调价和审批。</p></div></div>
        <div class='section-body'><h3>问题结论</h3>{_table(['等级','标题','证据','建议'], note_rows)}<h3>动作建议</h3><ol>{action_items}</ol></div>
      </section>
      <section id='raw'>
        <div class='section-head'><div><h2>原始结果与数据质量</h2><p>用于开发核对和字段映射复盘。</p></div></div>
        <div class='section-body'><h3>Data Quality</h3><pre>{_esc(data_quality_json)}</pre><h3>Raw Result JSON</h3><pre>{_esc(raw_json)}</pre></div>
      </section>
    </main>
  </div>
</body>
</html>"""


def write_reports(result, output_dir):
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "report.json"
    md_path = path / "report.md"
    html_path = path / "report.html"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(result), encoding="utf-8")
    html_path.write_text(build_html(result), encoding="utf-8")
    return {"report_json": str(json_path), "report_markdown": str(md_path), "report_html": str(html_path)}
