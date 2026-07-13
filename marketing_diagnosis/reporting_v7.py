from __future__ import annotations

import re
from pathlib import Path

from marketing_diagnosis import reporting_v6


CLIENT_STYLE = r"""
:root{--bg:#f3f6f5;--paper:#fff;--ink:#1f2933;--muted:#68747f;--line:#dfe7e4;--soft:#f7faf9;--mint:#e8f5ef;--mint2:#f2faf6;--green:#16845b;--teal:#0f9b82;--amber:#a96810;--red:#c43e38;--shadow:0 10px 28px rgba(29,56,47,.08)}
body{background:var(--bg);color:var(--ink);font-family:Inter,Arial,'PingFang SC','Microsoft YaHei',sans-serif}
.top{background:rgba(255,255,255,.96);border-bottom:1px solid var(--line)}
.top-inner{max-width:1600px;padding:13px 24px}.top h1{font-size:21px}.meta{font-size:12px}
.btn{border-radius:8px;background:var(--ink);border-color:var(--ink)}
.selectbox{border-color:var(--line);border-radius:8px;background:#fff}
.layout{max-width:1600px;grid-template-columns:250px minmax(0,1fr);gap:20px;padding:20px 24px 60px}
.side{top:82px;max-height:calc(100vh - 100px);overflow:auto;border-color:var(--line);border-radius:12px;box-shadow:var(--shadow)}
.side a{padding:9px 13px;border-bottom:0;border-top:1px solid #eef2f1;font-size:12px;color:#3f4b55}
.side a:hover{background:var(--mint2);color:var(--green)}
.card{border-color:var(--line);border-radius:12px;box-shadow:var(--shadow)}
.head{padding:17px 19px;border-bottom-color:#edf2f0;background:#fff}.head h2{font-size:18px}.body{padding:18px}
.badge.good{background:#e5f5ed;color:#15734e}.badge.warn{background:#fff4d9;color:#92610f}.badge.bad{background:#fdebea;color:#aa302c}.badge.info{background:#e8f5ef;color:#15734e}
.kpi,.tile,.panel{border-color:var(--line);border-radius:10px}.kpi,.tile{background:#f8fbfa}.kpi strong{font-size:25px}
.table th{background:#f7faf9;color:#53616b}.table th,.table td{border-bottom-color:#eaf0ed}.table tbody tr:nth-child(even){background:#fbfdfc}.table tbody tr:hover{background:#f1faf6}
.callout{border-color:#cfe5dc;background:#f4fbf7;color:#275949}
.period .badge.info{background:#e8f5ef;color:#15734e}
.client-hero{padding:24px;background:linear-gradient(135deg,#173d34,#245e50 55%,#358b72);color:#fff;border-radius:12px;position:relative;overflow:hidden}
.client-hero:after{content:'';position:absolute;width:320px;height:320px;border-radius:50%;right:-90px;top:-140px;background:rgba(255,255,255,.08)}
.client-hero h2{margin:0;font-size:28px}.client-hero p{margin:8px 0 0;color:rgba(255,255,255,.78)}
.client-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:18px;position:relative;z-index:1}
.client-summary>div{padding:14px;background:#fff;color:var(--ink);border-radius:10px}.client-summary small{display:block;color:var(--muted);font-weight:700}.client-summary strong{display:block;font-size:25px;margin-top:8px}.client-summary span{display:block;color:var(--muted);font-size:12px;margin-top:5px}
details.metric-details{margin-top:14px;border:1px solid #cbd8e8;border-radius:10px;overflow:hidden;background:#fff}
details.metric-details>summary{list-style:none;cursor:pointer;padding:13px 14px;background:#f4f8fd;color:#1f3e64;font-weight:800;display:flex;justify-content:space-between;gap:12px;align-items:center}
details.metric-details>summary::-webkit-details-marker{display:none}details.metric-details[open]>summary{background:#eef5fd;border-bottom:1px solid #dce6f2}
.metric-details-title small{display:block;margin-top:4px;color:#667085;font-weight:400}.metric-details-action{display:inline-flex;align-items:center;min-height:28px;padding:0 9px;border:1px solid #cbd8e8;border-radius:999px;background:#fff;color:#315b88;font-size:12px;white-space:nowrap}
.metric-details-content{padding:0}.metric-details-arrow{display:inline-block;margin-left:6px;transition:transform .2s ease}details.metric-details[open] .metric-details-arrow{transform:rotate(180deg)}
@media(max-width:980px){.client-summary{grid-template-columns:1fr 1fr}}@media(max-width:640px){.client-summary{grid-template-columns:1fr}.client-hero h2{font-size:23px}}
@media print{details.metric-details>summary{display:none!important}details.metric-details>.metric-details-content{display:block!important}}
"""


_ANALYSIS_RE = re.compile(
    r"<details class='analysis'[^>]*>.*?</details>",
    flags=re.IGNORECASE | re.DOTALL,
)


def _remove_ai_blocks(html_text: str) -> str:
    html_text = _ANALYSIS_RE.sub("", html_text)
    html_text = html_text.replace("AI整改动作建议", "整改动作建议")
    html_text = html_text.replace("优先使用AI基于当前报告生成的动作；无AI配置时用规则兜底。", "根据当前经营指标、规则命中和数据缺口形成整改动作。")
    html_text = html_text.replace("AI分析", "")
    return html_text


def _inject_client_style(html_text: str) -> str:
    return html_text.replace("</style>", CLIENT_STYLE + "</style>", 1)


def _inject_client_hero(html_text: str, result: dict) -> str:
    score = result.get("final_score")
    score_text = "待计算" if score in (None, "") else f"{float(score):.1f}"
    risk = result.get("risk_level") or "待判断"
    modules = len(result.get("module_scores") or [])
    missing = sum(len(v or []) for v in ((result.get("data_quality") or {}).get("missing_fields") or {}).values())
    hero = f"""
<section class='client-hero' id='client-overview'>
  <h2>酒店经营与线上运营综合诊断</h2>
  <p>报告覆盖经营趋势、房型收益、曝光转化、价格、口碑及数据完整度，帮助快速识别问题并形成改进方向。</p>
  <div class='client-summary'>
    <div><small>综合得分</small><strong>{score_text}</strong><span>风险等级：{risk}</span></div>
    <div><small>诊断模块</small><strong>{modules or '待统计'}项</strong><span>按当前规则结果展示</span></div>
    <div><small>数据缺失</small><strong>{missing}项</strong><span>缺失值不使用0替代</span></div>
    <div><small>报告类型</small><strong>客户展示版</strong><span>不展示AI诊断分析</span></div>
  </div>
</section>
"""
    return html_text.replace("<main>", "<main>" + hero, 1)


def _wrap_detail_section(html_text: str, section_id: str) -> str:
    pattern = re.compile(
        rf"(<section class='card' id='{re.escape(section_id)}'[^>]*>.*?<div class='body'>)(.*?)(</div></section>)",
        flags=re.IGNORECASE | re.DOTALL,
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
    html_text = _inject_client_hero(html_text, result)
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
