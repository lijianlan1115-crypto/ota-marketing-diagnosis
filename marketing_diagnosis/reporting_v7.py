from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v6


CLIENT_STYLE = r"""
:root{--bg:#f3f6f5;--paper:#fff;--ink:#1f2933;--muted:#68747f;--line:#dfe7e4;--soft:#f7faf9;--mint:#e8f5ef;--mint2:#f2faf6;--green:#16845b;--teal:#0f9b82;--blue:#2563eb;--amber:#a96810;--red:#c43e38;--purple:#7654c4;--shadow:0 10px 28px rgba(29,56,47,.08)}
body{background:var(--bg);color:var(--ink);font-family:Inter,Arial,'PingFang SC','Microsoft YaHei',sans-serif;font-size:14px;line-height:1.55}
.top{background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}
.top-inner{max-width:1600px;padding:13px 24px}.top h1{font-size:21px}.meta{font-size:12px}.actions{gap:8px}.btn{height:36px;border-radius:8px;background:var(--ink);border-color:var(--ink)}
.selectbox{height:36px;border-color:var(--line);border-radius:8px;background:#fff;padding:0 10px}.selectbox select{height:32px;border:0}
.layout{max-width:1600px;grid-template-columns:250px minmax(0,1fr);gap:20px;padding:20px 24px 60px}
.side{top:82px;max-height:calc(100vh - 100px);overflow:auto;border-color:var(--line);border-radius:12px;box-shadow:var(--shadow)}
.side:before{content:'报告目录';display:block;padding:14px 14px 9px;font-size:12px;color:var(--muted);font-weight:800;text-transform:uppercase;letter-spacing:.08em}
.side a{display:flex;gap:9px;align-items:center;padding:9px 13px;border-bottom:0;border-top:1px solid #eef2f1;font-size:12px;color:#3f4b55}
.side a:before{content:attr(data-no);width:26px;height:22px;border-radius:6px;background:#edf4f1;display:grid;place-items:center;font-size:11px;color:var(--green);flex:0 0 auto}
.side a:hover{background:var(--mint2);color:var(--green)}
main{gap:18px;width:100%;max-width:100%;min-width:0;overflow:hidden}.card{border-color:var(--line);border-radius:12px;box-shadow:var(--shadow);scroll-margin-top:90px}.head{padding:17px 19px;border-bottom-color:#edf2f0;background:#fff}.head h2{font-size:18px}.head p{font-size:13px}.body{padding:18px}
.badge.good{background:#e5f5ed;color:#15734e}.badge.warn{background:#fff4d9;color:#92610f}.badge.bad{background:#fdebea;color:#aa302c}.badge.info{background:#e8f5ef;color:#15734e}.badge.neutral{background:#edf2f7;color:#475569}
.kpi,.tile,.panel{border-color:var(--line);border-radius:10px}.kpi,.tile{background:#f8fbfa}.kpi strong{font-size:25px}.panel h3{background:#f7faf9}
.table th{background:#f7faf9;color:#53616b}.table th,.table td{border-bottom-color:#eaf0ed}.table tbody tr:nth-child(even){background:#fbfdfc}.table tbody tr:hover{background:#f1faf6}
.callout{border-color:#cfe5dc;background:#f4fbf7;color:#275949}.period .badge.info{background:#e8f5ef;color:#15734e}
.client-hero{padding:24px;background:linear-gradient(135deg,#173d34,#245e50 55%,#358b72);color:#fff;border-radius:12px;position:relative;overflow:hidden;box-shadow:var(--shadow)}
.client-hero:after{content:'';position:absolute;width:320px;height:320px;border-radius:50%;right:-90px;top:-140px;background:rgba(255,255,255,.08)}
.client-hero-grid{display:grid;grid-template-columns:1.25fr 1fr;gap:22px;position:relative;z-index:1}.client-hero h2{margin:0;font-size:28px}.client-hero p{margin:8px 0 0;color:rgba(255,255,255,.78)}
.client-source{margin-top:18px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.client-source div{padding:11px 12px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);border-radius:9px}.client-source small{display:block;color:rgba(255,255,255,.68)}.client-source b{display:block;margin-top:3px}
.client-summary{display:grid;grid-template-columns:1fr 1fr;gap:10px}.client-summary>div{padding:14px;background:#fff;color:var(--ink);border-radius:10px}.client-summary small{display:block;color:var(--muted);font-weight:700}.client-summary strong{display:block;font-size:25px;margin-top:8px}.client-summary span{display:block;color:var(--muted);font-size:12px;margin-top:5px}
.client-result-summary{background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);overflow:hidden}.client-result-summary .summary-head{padding:17px 19px;border-bottom:1px solid #edf2f0}.client-result-summary h2{margin:0;font-size:18px}.client-result-summary p{margin:4px 0 0;color:var(--muted);font-size:13px}.summary-table-wrap{overflow:auto}.summary-table{width:100%;border-collapse:collapse;min-width:760px}.summary-table th,.summary-table td{padding:10px;border-bottom:1px solid #eaf0ed;text-align:left}.summary-table th{font-size:12px;color:#53616b;background:#f7faf9}.summary-table a{font-weight:800;color:var(--green);text-decoration:none}
details.metric-details{margin-top:14px;border:1px solid #cbd8e8;border-radius:10px;overflow:hidden;background:#fff}
details.metric-details>summary{list-style:none;cursor:pointer;padding:13px 14px;background:#f4f8fd;color:#1f3e64;font-weight:800;display:flex;justify-content:space-between;gap:12px;align-items:center}details.metric-details>summary::-webkit-details-marker{display:none}details.metric-details[open]>summary{background:#eef5fd;border-bottom:1px solid #dce6f2}
.metric-details-title small{display:block;margin-top:4px;color:#667085;font-weight:400}.metric-details-action{display:inline-flex;align-items:center;min-height:28px;padding:0 9px;border:1px solid #cbd8e8;border-radius:999px;background:#fff;color:#315b88;font-size:12px;white-space:nowrap}.metric-details-content{padding:0}.metric-details-arrow{display:inline-block;margin-left:6px;transition:transform .2s ease}details.metric-details[open] .metric-details-arrow{transform:rotate(180deg)}
.s14-scorebar{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}.s14-scorebar>div{padding:16px 18px;border:1px solid var(--line);border-radius:11px;background:#fff;box-shadow:var(--shadow)}.s14-scorebar small{display:block;color:var(--muted);font-weight:700}.s14-scorebar strong{display:block;margin-top:6px;font-size:25px;color:var(--green)}
.s14-summary,.s14-items{width:100%;max-width:100%;min-width:0}.s14-summary{margin-bottom:18px}.s14-items{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.s14-item{min-width:0;border:1px solid var(--line);border-radius:12px;background:#fff;box-shadow:var(--shadow);overflow:hidden;scroll-margin-top:90px}.s14-item-head{display:grid;grid-template-columns:42px minmax(0,1fr) auto;gap:12px;align-items:center;padding:15px 16px;border-bottom:1px solid #edf2f0}.s14-no{height:34px;border-radius:8px;background:#173d34;color:#fff;display:grid;place-items:center;font-weight:900}.s14-item h3{margin:0;font-size:16px}.s14-item-meta{display:flex;gap:7px;align-items:center;flex-wrap:wrap}.s14-item-body{padding:14px 16px}.s14-source{margin-bottom:10px;padding:9px 11px;border:1px solid #dce6f2;border-radius:8px;background:#f4f8fd;color:#315b88;font-size:11px;word-break:break-word}.s14-source b{font-size:12px}.s14-source span{display:block;margin-top:3px;color:#667085}.s14-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.s14-field{min-width:0;padding:10px 11px;border:1px solid #e7eeeb;border-radius:8px;background:#f8fbfa}.s14-field small,.s14-field span{display:block}.s14-field small{color:var(--muted);font-weight:700}.s14-field b{display:block;margin-top:4px;word-break:break-word}.s14-field span{margin-top:3px;color:var(--muted);font-size:11px}.s14-note{margin-top:10px;padding:9px 11px;border-left:3px solid #cfe5dc;background:#f4fbf7;color:#4d625a;font-size:12px}.s14-status{display:inline-flex;padding:4px 8px;border-radius:999px;font-size:11px;font-weight:800}.s14-status.success{background:#e5f5ed;color:#15734e}.s14-status.zero{background:#fdebea;color:#aa302c}.s14-status.pending_rule,.s14-status.manual_pending{background:#fff4d9;color:#92610f}.s14-status.missing,.s14-status.error{background:#edf2f7;color:#475569}
@media(max-width:1100px){.layout{grid-template-columns:minmax(0,1fr)}.side{position:static;max-height:none;display:none}.client-hero-grid{grid-template-columns:minmax(0,1fr)}.client-source{grid-template-columns:1fr 1fr}.s14-items{grid-template-columns:minmax(0,1fr)}}@media(max-width:980px){.client-summary{grid-template-columns:1fr 1fr}}@media(max-width:640px){.layout{padding:13px}.client-summary,.client-source,.s14-scorebar,.s14-fields{grid-template-columns:minmax(0,1fr)}.client-hero h2{font-size:23px}.s14-item-head{grid-template-columns:38px minmax(0,1fr)}.s14-item-meta{grid-column:1/-1}}
@media print{details.metric-details>summary{display:none!important}details.metric-details>.metric-details-content{display:block!important}.client-result-summary{box-shadow:none}}
"""

_ANALYSIS_RE = re.compile(r"<details class='analysis'[^>]*>.*?</details>", re.IGNORECASE | re.DOTALL)
_SIDE_RE = re.compile(r"(<nav class='side'>)(.*?)(</nav>)", re.IGNORECASE | re.DOTALL)
_LINK_RE = re.compile(r"<a href='([^']+)'>(.*?)</a>", re.IGNORECASE | re.DOTALL)


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _remove_ai_blocks(html_text: str) -> str:
    html_text = _ANALYSIS_RE.sub("", html_text)
    html_text = html_text.replace("AI整改动作建议", "整改动作建议")
    html_text = html_text.replace("优先使用AI基于当前报告生成的动作；无AI配置时用规则兜底。", "根据当前经营指标、规则命中和数据缺口形成整改动作。")
    html_text = html_text.replace("周边活动AI分析", "周边活动分析")
    html_text = html_text.replace("AI分析", "")
    return html_text


def _inject_client_style(html_text: str) -> str:
    return html_text.replace("</style>", CLIENT_STYLE + "</style>", 1)


def _number_side_links(html_text: str) -> str:
    def nav_repl(match: re.Match[str]) -> str:
        start, body, end = match.groups()
        counter = 0

        def link_repl(link: re.Match[str]) -> str:
            nonlocal counter
            counter += 1
            href, label = link.groups()
            number = "表" if "模块" in label or "规则" in label else f"{counter:02d}"
            return f"<a href='{href}' data-no='{number}'>{label}</a>"

        return start + _LINK_RE.sub(link_repl, body) + end

    return _SIDE_RE.sub(nav_repl, html_text, count=1)


def _source_summary(result: dict) -> tuple[int, int]:
    rows = tables = 0
    for source in ((result.get("data_quality") or {}).get("source_diagnostics") or []):
        for diag in (source.get("tables") or {}).values():
            if diag.get("status") == "ok":
                tables += 1
                rows += int(diag.get("rows") or 0)
    return rows, tables


def _inject_client_hero(html_text: str, result: dict) -> str:
    visual = result.get("visual_diagnosis") or {}
    score = visual.get("normalized_score") if visual else result.get("final_score")
    try:
        score_text = f"{float(score):.1f}"
    except (TypeError, ValueError):
        score_text = "待计算"
    risk = ("待判断" if score is None else "高" if float(score) < 60 else "中" if float(score) < 80 else "低") if visual else (result.get("risk_level") or "待判断")
    modules = len(visual.get("items") or []) if visual else len(result.get("module_scores") or [])
    missing = (sum(1 for item in visual.get("items") or [] if item.get("data_status") in {"missing", "error"})
               if visual else sum(len(v or []) for v in ((result.get("data_quality") or {}).get("missing_fields") or {}).values()))
    rows, tables = _source_summary(result)
    period_start = result.get("period_start") or "未标注"
    period_end = result.get("period_end") or "未标注"
    platform = result.get("platform") or "多渠道"
    hero = f"""
<section class='client-hero' id='client-overview'>
  <div class='client-hero-grid'>
    <div>
      <h2>酒店经营与线上运营综合诊断</h2>
      <p>报告覆盖经营趋势、房型收益、曝光转化、价格、口碑及数据完整度，帮助快速识别问题并形成改进方向。</p>
      <div class='client-source'>
        <div><small>诊断周期</small><b>{_e(period_start)} 至 {_e(period_end)}</b></div>
        <div><small>诊断渠道</small><b>{_e(platform)}</b></div>
        <div><small>数据来源</small><b>{tables}表 · {rows}行</b></div>
      </div>
    </div>
    <div class='client-summary'>
      <div><small>折算得分</small><strong>{score_text}</strong><span>风险等级：{_e(risk)}</span></div>
      <div><small>诊断模块</small><strong>{modules or '待统计'}项</strong><span>按当前规则结果展示</span></div>
      <div><small>数据缺失</small><strong>{missing}项</strong><span>缺失值不使用0替代</span></div>
      <div><small>报告类型</small><strong>规则诊断版</strong><span>仅展示规则计算和真实数据</span></div>
    </div>
  </div>
</section>
"""
    return html_text.replace("<main>", "<main>" + hero, 1)


def _inject_result_summary(html_text: str, result: dict) -> str:
    rows = []
    for index, item in enumerate(result.get("module_scores") or [], start=1):
        score = item.get("score")
        weight = item.get("weight")
        score_text = "待计算" if score in (None, "") else f"{score}/{weight}"
        status = item.get("status") or "待确认"
        reasons = "；".join(item.get("reasons") or []) or "暂无诊断说明"
        module_id = item.get("module_id") or f"M{index:02d}"
        rows.append(
            "<tr>"
            f"<td>{index:02d}</td>"
            f"<td><a href='#modules'>{_e(item.get('module_name') or module_id)}</a></td>"
            f"<td>{_e(weight)}</td>"
            f"<td>{_e(score_text)}</td>"
            f"<td><span class='badge neutral'>{_e(status)}</span></td>"
            f"<td>{_e(reasons)}</td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='6'>暂无模块评分数据</td></tr>")
    block = (
        "<section class='client-result-summary' id='client-summary'>"
        "<div class='summary-head'><h2>诊断结果总览</h2><p>快速查看各模块当前得分、状态和判断依据。</p></div>"
        "<div class='summary-table-wrap'><table class='summary-table'><thead><tr>"
        "<th>编号</th><th>诊断项目</th><th>满分</th><th>当前得分</th><th>状态</th><th>诊断依据</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div></section>"
    )
    marker = "</section>\n<section class='card' id='overview'"
    if marker in html_text:
        return html_text.replace(marker, "</section>" + block + "\n<section class='card' id='overview'", 1)
    return html_text.replace("</section>", "</section>" + block, 1)


def _visual_value(label: str, value: Any) -> str:
    if value in (None, ""):
        return "暂无数据"
    if isinstance(value, float):
        if any(key in label for key in ("占比", "转化率", "YOY", "同比", "出租率")):
            return f"{value:.2%}"
        if any(key in label for key in ("金额", "房费", "投入", "收入")):
            return f"¥{value:,.2f}"
        return f"{value:,.2f}"
    return str(value)


def _inject_visual_diagnosis(html_text: str, result: dict) -> str:
    visual = result.get("visual_diagnosis") or {}
    items = visual.get("items") or []
    if not items:
        return html_text
    status_text = {
        "success": "已计算", "zero": "真实为0", "missing": "数据缺失",
        "error": "采集失败", "pending_rule": "规则待确认", "manual_pending": "待人工录入",
    }
    summary_rows = []
    cards = []
    for item in items:
        no = int(item.get("standard_item_id") or 0)
        status = str(item.get("data_status") or "missing")
        score = item.get("item_score")
        participates = bool(item.get("participates_in_score"))
        score_text = "仅展示" if not participates else ("待计算" if score is None else f"{float(score):g}分")
        base_text = "仅展示" if not participates else f"{float(item.get('base_score') or 0):g}分"
        summary_rows.append(
            f"<tr><td>{no:02d}</td><td><a href='#rule-{no}'>{_e(item.get('item_name'))}</a></td>"
            f"<td>{base_text}</td><td>{score_text}</td><td><span class='s14-status {status}'>{_e(status_text.get(status, status))}</span></td>"
            f"<td>数据表：{_e(item.get('source_table'))}<br>{_e(item.get('note') or '按数据库字段与规则手册计算')}</td></tr>"
        )
        fields = []
        for field in item.get("fields") or []:
            fields.append(
                "<div class='s14-field'>"
                f"<small>{_e(field.get('label'))}</small><b>{_e(_visual_value(str(field.get('label') or ''), field.get('value')))}</b>"
                f"<span>{_e(field.get('note') or '')}</span></div>"
            )
        if not fields:
            fields.append("<div class='s14-field'><small>数据状态</small><b>暂无数据</b><span>缺失值不会按0处理</span></div>")
        note = f"<div class='s14-note'>{_e(item.get('note'))}</div>" if item.get("note") else ""
        source_fields = "、".join(str(value) for value in (item.get("source_fields") or [])) or "待补充"
        source = (
            "<div class='s14-source'><b>数据库表：" + _e(item.get("source_table")) + "</b>"
            "<span>对应字段：" + _e(source_fields) + "</span></div>"
        )
        cards.append(
            f"<article class='s14-item' id='rule-{no}'><div class='s14-item-head'><div class='s14-no'>{no:02d}</div>"
            f"<h3>{_e(item.get('item_name'))}</h3><div class='s14-item-meta'><span class='s14-status {status}'>{_e(status_text.get(status, status))}</span>"
            f"<span class='badge neutral'>{score_text} / {base_text}</span></div></div>"
            f"<div class='s14-item-body'>{source}<div class='s14-fields'>{''.join(fields)}</div>{note}</div></article>"
        )
    normalized = visual.get("normalized_score")
    block = (
        "<section class='s14-summary' id='s14-summary'><div class='s14-scorebar'>"
        f"<div><small>原始得分</small><strong>{_e(visual.get('raw_score'))}/100</strong></div>"
        f"<div><small>已接入基础分</small><strong>{_e(visual.get('connected_base_score'))}/100</strong></div>"
        f"<div><small>按已接入项折算得分</small><strong>{'待计算' if normalized is None else f'{float(normalized):.2f}'}</strong></div>"
        "</div><div class='client-result-summary'><div class='summary-head'><h2>23项可视化诊断结果</h2>"
        "<p>严格区分真实为0、数据缺失、采集失败、规则待确认和人工待录入。</p></div>"
        "<div class='summary-table-wrap'><table class='summary-table'><thead><tr><th>编号</th><th>诊断项目</th><th>满分</th><th>当前得分</th><th>状态</th><th>口径说明</th></tr></thead><tbody>"
        + "".join(summary_rows) + "</tbody></table></div></div></section>"
        + "<section class='s14-items'>" + "".join(cards) + "</section>"
    )
    nav = "<nav class='side'><a href='#client-overview' data-no='00'>诊断概览</a><a href='#s14-summary' data-no='表'>诊断结果总览</a>"
    nav += "".join(f"<a href='#rule-{int(item.get('standard_item_id') or 0)}' data-no='{int(item.get('standard_item_id') or 0):02d}'>{_e(item.get('item_name'))}</a>" for item in items)
    nav += "</nav>"
    html_text = _SIDE_RE.sub(nav, html_text, count=1)
    # v24 页面以 23 项规则为主体；移除旧版八模块明细，避免同一报告出现
    # 两套评分口径。原始 JSON/Markdown 仍保留旧模块结果供兼容调用方使用。
    html_text = re.sub(r"<section class='card' id='overview'.*?</main>", "</main>", html_text, count=1, flags=re.DOTALL)
    return html_text.replace("</main>", block + "</main>", 1)


def _wrap_detail_section(html_text: str, section_id: str) -> str:
    pattern = re.compile(
        rf"(<section class='card' id='{re.escape(section_id)}'[^>]*>.*?<div class='body'>)(.*?)(</div></section>)",
        re.IGNORECASE | re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        start, body, end = match.groups()
        return (
            start
            + "<details class='metric-details'><summary>"
            + "<span class='metric-details-title'>诊断指标明细<small>展示本项核心指标、当前结果及必要说明。</small></span>"
            + "<span class='metric-details-action'>点击展开<span class='metric-details-arrow'>⌄</span></span>"
            + "</summary><div class='metric-details-content'>"
            + body
            + "</div></details>"
            + end
        )

    return pattern.sub(repl, html_text, count=1)


def build_html(result: dict) -> str:
    html_text = reporting_v6.build_html(result)
    html_text = _remove_ai_blocks(html_text)
    html_text = _inject_client_style(html_text)
    html_text = _number_side_links(html_text)
    html_text = _inject_client_hero(html_text, result)
    if not result.get("visual_diagnosis"):
        html_text = _inject_result_summary(html_text, result)
    html_text = _inject_visual_diagnosis(html_text, result)
    if not result.get("visual_diagnosis"):
        for section_id in ("rules", "metrics", "missing"):
            html_text = _wrap_detail_section(html_text, section_id)
    return html_text


def build_markdown(result: dict) -> str:
    return reporting_v6.build_markdown(result)


def write_reports(result: dict, output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v6.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths
