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
main{gap:18px}.card{border-color:var(--line);border-radius:12px;box-shadow:var(--shadow);scroll-margin-top:90px}.head{padding:17px 19px;border-bottom-color:#edf2f0;background:#fff}.head h2{font-size:18px}.head p{font-size:13px}.body{padding:18px}
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
@media(max-width:1100px){.client-hero-grid{grid-template-columns:1fr}.client-source{grid-template-columns:1fr 1fr}}@media(max-width:980px){.client-summary{grid-template-columns:1fr 1fr}}@media(max-width:640px){.client-summary,.client-source{grid-template-columns:1fr}.client-hero h2{font-size:23px}}
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
    score = result.get("final_score")
    try:
        score_text = f"{float(score):.1f}"
    except (TypeError, ValueError):
        score_text = "待计算"
    risk = result.get("risk_level") or "待判断"
    modules = len(result.get("module_scores") or [])
    missing = sum(len(v or []) for v in ((result.get("data_quality") or {}).get("missing_fields") or {}).values())
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
      <div><small>综合得分</small><strong>{score_text}</strong><span>风险等级：{_e(risk)}</span></div>
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
    html_text = _inject_result_summary(html_text, result)
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
