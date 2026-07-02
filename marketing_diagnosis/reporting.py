from pathlib import Path
import html
import json


def _text(value):
    if value is None:
        return "missing"
    if isinstance(value, float):
        return f"{value:.4f}" if abs(value) < 1 else f"{value:.2f}"
    return str(value)


def _esc(value):
    return html.escape(_text(value))


def _pct(value):
    try:
        if value is None:
            return "missing"
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return _text(value)


def _money(value):
    try:
        if value is None:
            return "missing"
        return f"¥{float(value):.2f}"
    except (TypeError, ValueError):
        return _text(value)


def build_markdown(result):
    lines = ["# OTA Marketing Report", ""]
    lines.append(f"- final_score: {result.get('final_score', 'missing')}")
    lines.append(f"- risk_level: {result.get('risk_level', 'missing')}")
    lines.append(f"- status: {result.get('status', 'missing')}")
    lines.append("")
    lines.append("## Module Scores")
    for item in result.get("module_scores") or []:
        lines.append(f"- {item.get('module_id')} {item.get('module_name')}: {item.get('score')}/{item.get('weight')} ({item.get('rate')})")
    lines.append("")
    lines.append("## Metrics")
    for name, payload in (result.get("metrics") or {}).items():
        lines.append(f"### {name}")
        if isinstance(payload, dict):
            for key, value in payload.items():
                lines.append(f"- {key}: {value}")
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


def _kpi_card(label, value, hint=""):
    return f"<div class='kpi'><label>{_esc(label)}</label><strong>{_esc(value)}</strong><span>{_esc(hint)}</span></div>"


def _table(headers, rows):
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def build_html(result):
    metrics = result.get("metrics") or {}
    operating = metrics.get("operating") or {}
    funnel = metrics.get("ota_funnel") or {}
    price = metrics.get("price_ladder") or {}
    reputation = metrics.get("reputation") or {}
    competitors = metrics.get("competitors") or {}
    module_rows = [[m.get("module_id"), m.get("module_name"), m.get("score"), m.get("weight"), m.get("rate"), "; ".join(m.get("reasons") or [])] for m in result.get("module_scores") or []]
    note_rows = [[n.get("level"), n.get("title"), n.get("evidence"), n.get("suggestion")] for n in result.get("notes") or []]
    action_items = "".join(f"<li>{_esc(item)}</li>" for item in result.get("actions") or [])
    data_quality = json.dumps(result.get("data_quality") or {}, ensure_ascii=False, indent=2)
    raw_json = json.dumps(result, ensure_ascii=False, indent=2)
    return f"""<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>酒店 OTA 营销诊断报告</title>
  <style>
    :root {{ --bg:#f6f7fb; --panel:#fff; --ink:#1f2937; --muted:#667085; --line:#e5e7eb; --blue:#2563eb; --green:#168a4a; --amber:#b7791f; --red:#c2413a; --shadow:0 8px 24px rgba(15,23,42,.08); }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif; font-size:14px; line-height:1.5; }}
    header {{ position:sticky; top:0; z-index:10; background:rgba(255,255,255,.96); border-bottom:1px solid var(--line); }}
    .header-inner {{ max-width:1280px; margin:0 auto; padding:16px 24px; display:flex; justify-content:space-between; gap:16px; align-items:center; }}
    h1 {{ margin:0; font-size:22px; }}
    .sub {{ margin-top:4px; color:var(--muted); }}
    .layout {{ max-width:1280px; margin:0 auto; padding:22px 24px 48px; display:grid; grid-template-columns:220px minmax(0,1fr); gap:20px; }}
    nav {{ position:sticky; top:82px; align-self:start; background:var(--panel); border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow); overflow:hidden; }}
    nav a {{ display:block; padding:12px 14px; color:var(--ink); text-decoration:none; border-bottom:1px solid var(--line); font-weight:600; }}
    nav a:last-child {{ border-bottom:0; }}
    nav a:hover {{ background:#eff6ff; color:var(--blue); }}
    main {{ display:grid; gap:18px; }}
    section {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; box-shadow:var(--shadow); overflow:hidden; }}
    .section-head {{ padding:16px 18px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:12px; }}
    .section-head h2 {{ margin:0; font-size:18px; }}
    .section-head p {{ margin:5px 0 0; color:var(--muted); }}
    .body {{ padding:18px; }}
    .badge {{ display:inline-block; padding:5px 10px; border-radius:999px; font-weight:700; background:#eef2ff; color:var(--blue); }}
    .badge.high {{ background:#fee2e2; color:var(--red); }} .badge.medium {{ background:#fff7ed; color:var(--amber); }} .badge.low {{ background:#eaf7ef; color:var(--green); }}
    .kpis {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .kpi {{ border:1px solid var(--line); border-radius:10px; padding:14px; background:#fff; min-height:112px; }}
    .kpi label {{ color:var(--muted); font-weight:700; display:block; }} .kpi strong {{ font-size:26px; display:block; margin-top:8px; }} .kpi span {{ color:var(--muted); display:block; margin-top:8px; }}
    table {{ width:100%; border-collapse:collapse; }} th,td {{ border:1px solid var(--line); padding:9px 10px; text-align:left; vertical-align:top; }} th {{ background:#f8fafc; }}
    pre {{ white-space:pre-wrap; word-break:break-word; background:#0f172a; color:#e5e7eb; border-radius:10px; padding:14px; overflow:auto; }}
    .grid2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
    @media (max-width:900px) {{ .layout {{ grid-template-columns:1fr; }} nav {{ position:static; }} .kpis,.grid2 {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header><div class='header-inner'><div><h1>酒店 OTA 营销诊断报告</h1><div class='sub'>独立第三方营销诊断 · 只读分析 · 不写调价/审批/live</div></div><span class='badge {_esc(result.get('risk_level'))}'>{_esc(result.get('risk_level'))}</span></div></header>
  <div class='layout'>
    <nav><a href='#summary'>总览</a><a href='#modules'>M01-M08评分</a><a href='#operating'>经营</a><a href='#funnel'>OTA漏斗</a><a href='#price'>商品价格</a><a href='#reputation'>口碑</a><a href='#competitors'>竞品</a><a href='#actions'>建议</a><a href='#quality'>数据质量</a></nav>
    <main>
      <section id='summary'><div class='section-head'><div><h2>总览</h2><p>综合评分、风险等级和报告状态。</p></div></div><div class='body'><div class='kpis'>
        {_kpi_card('综合分', result.get('final_score'), '满分 100')}
        {_kpi_card('风险等级', result.get('risk_level'), 'high / medium / low')}
        {_kpi_card('报告状态', result.get('status'), 'ok / partial')}
        {_kpi_card('边界', result.get('boundary'), 'report only')}
      </div></div></section>
      <section id='modules'><div class='section-head'><div><h2>M01-M08 模块评分</h2><p>来自旧 S14 诊断框架的模块化评分结构。</p></div></div><div class='body'>{_table(['模块','名称','得分','权重','达成率','依据'], module_rows)}</div></section>
      <section id='operating'><div class='section-head'><div><h2>经营结果</h2><p>历史日经营、出租率、ADR、RevPAR。</p></div></div><div class='body'><div class='kpis'>
        {_kpi_card('营业日期', operating.get('latest_business_date'))}
        {_kpi_card('出租率', _pct(operating.get('occupancy_rate')))}
        {_kpi_card('ADR', _money(operating.get('adr')))}
        {_kpi_card('RevPAR', _money(operating.get('revpar')))}
      </div></div></section>
      <section id='funnel'><div class='section-head'><div><h2>OTA 流量漏斗</h2><p>曝光、浏览、支付订单、支付转化率。</p></div></div><div class='body'><div class='kpis'>
        {_kpi_card('曝光', funnel.get('exposure'))}
        {_kpi_card('浏览', funnel.get('views'))}
        {_kpi_card('支付订单', funnel.get('paid_orders'))}
        {_kpi_card('支付转化率', _pct(funnel.get('payment_conversion_rate')))}
      </div></div></section>
      <section id='price'><div class='section-head'><div><h2>商品价格梯度</h2><p>商品数量、最低价、最高价、价格跳水风险。</p></div></div><div class='body'><div class='kpis'>
        {_kpi_card('商品数', price.get('product_count'))}
        {_kpi_card('最低价', _money(price.get('min_price')))}
        {_kpi_card('最高价', _money(price.get('max_price')))}
        {_kpi_card('跳水风险数', len(price.get('price_jump_risks') or []))}
      </div></div></section>
      <section id='reputation'><div class='section-head'><div><h2>口碑评论</h2><p>评分、差评率、公开评论证据。</p></div></div><div class='body'><div class='kpis'>
        {_kpi_card('评论数', reputation.get('review_count'))}
        {_kpi_card('平均评分', reputation.get('rating_avg'))}
        {_kpi_card('差评率', _pct(reputation.get('negative_review_rate')))}
        {_kpi_card('差评数', reputation.get('negative_review_count'))}
      </div></div></section>
      <section id='competitors'><div class='section-head'><div><h2>竞品对比</h2><p>竞品均价和本店引流价差。</p></div></div><div class='body'><div class='kpis'>
        {_kpi_card('竞品数', competitors.get('competitor_count'))}
        {_kpi_card('竞品均价', _money(competitors.get('competitor_avg_price')))}
        {_kpi_card('最佳竞品排名', competitors.get('best_competitor_rank'))}
        {_kpi_card('价差', _money(competitors.get('own_min_price_vs_competitor_avg_gap')))}
      </div></div></section>
      <section id='actions'><div class='section-head'><div><h2>诊断结论与动作建议</h2><p>只输出营销建议，不执行调价和审批。</p></div></div><div class='body'><h3>问题结论</h3>{_table(['等级','标题','证据','建议'], note_rows)}<h3>动作建议</h3><ol>{action_items}</ol></div></section>
      <section id='quality'><div class='section-head'><div><h2>数据质量</h2><p>缺字段、数据状态和完整原始 JSON。</p></div></div><div class='body'><h3>Data Quality</h3><pre>{_esc(data_quality)}</pre><h3>Raw Result JSON</h3><pre>{_esc(raw_json)}</pre></div></section>
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
