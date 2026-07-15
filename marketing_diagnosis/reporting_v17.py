from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v14, reporting_v16


COMPACT_OVERVIEW_STYLE = """
<style>
.hero-v17{padding:28px 32px}
.hero-layout-v17{display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,360px);gap:28px;align-items:center;position:relative;z-index:1}
.hero-copy-v17 h2{margin:0;font-size:32px}.hero-copy-v17 p{margin:10px 0 0;max-width:820px;color:rgba(255,255,255,.8);font-size:15px}
.hero-period-v17{display:inline-flex;align-items:center;gap:10px;margin-top:22px;padding:11px 15px;border:1px solid rgba(255,255,255,.18);border-radius:11px;background:rgba(255,255,255,.1)}
.hero-period-v17 small{color:rgba(255,255,255,.68);font-weight:800}.hero-period-v17 strong{font-size:16px;color:#fff}
.total-score-v17{padding:24px 26px;border-radius:16px;background:#fff;color:#26343d;box-shadow:0 12px 30px rgba(16,48,39,.18)}
.total-score-v17 small{display:block;color:var(--muted);font-size:13px;font-weight:800}.total-score-v17 strong{display:block;margin-top:10px;font-size:48px;line-height:1}.total-score-v17 span{display:block;margin-top:9px;color:var(--muted);font-size:13px}
.diagnosis-pair-v17{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;align-items:stretch}
.diagnosis-pair-v17>.diagnosis-card{height:100%;margin:0}
.diagnosis-pair-v17 .metric-row.five{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.diagnosis-pair-v17 .result-area{min-height:150px}
@media(max-width:1050px){.hero-layout-v17,.diagnosis-pair-v17{grid-template-columns:1fr}.total-score-v17{max-width:360px}.diagnosis-pair-v17 .result-area{min-height:0}}
@media(max-width:620px){.hero-v17{padding:22px}.hero-copy-v17 h2{font-size:25px}.total-score-v17 strong{font-size:40px}}
</style>
"""


def _score_text(value: Any) -> str:
    number = reporting_v14._number(value)
    return "待计算" if number is None else f"{number:.1f}"


def _compact_overview(result: dict[str, Any]) -> str:
    visual = result.get("visual_diagnosis") or {}
    start = result.get("period_start") or "未标注"
    end = result.get("period_end") or "未标注"
    score = _score_text(visual.get("normalized_score"))
    return (
        "<section id='overview'><div class='hero hero-v17'>"
        "<div class='hero-layout-v17'><div class='hero-copy-v17'>"
        "<h2>酒店经营与线上运营综合诊断</h2>"
        "<p>覆盖经营趋势、流量、客群、推广、口碑及平台配置等23项诊断内容。</p>"
        f"<div class='hero-period-v17'><small>诊断周期</small><strong>{reporting_v14._e(start)} 至 {reporting_v14._e(end)}</strong></div>"
        "</div>"
        "<div class='total-score-v17'><small>总得分</small>"
        f"<strong>{reporting_v14._e(score)}</strong><span>满分100分</span></div>"
        "</div></div></section>"
    )


def _replace_overview(html_text: str, result: dict[str, Any]) -> str:
    return re.sub(
        r"<section id='overview'>.*?</section>",
        lambda _: _compact_overview(result),
        html_text,
        count=1,
        flags=re.DOTALL,
    )


def _pair_cards(html_text: str, left_number: int = 7, right_number: int = 8) -> str:
    pattern = re.compile(
        rf"(<article class='diagnosis-card'[^>]*id='rule-{left_number}'>.*?</article>)\s*"
        rf"(<article class='diagnosis-card'[^>]*id='rule-{right_number}'>.*?</article>)",
        re.DOTALL,
    )
    return pattern.sub(
        lambda match: (
            "<div class='diagnosis-pair-v17'>"
            + match.group(1)
            + match.group(2)
            + "</div>"
        ),
        html_text,
        count=1,
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v16.build_html(result)
    html_text = _replace_overview(html_text, result)
    html_text = _pair_cards(html_text, 7, 8)
    return html_text.replace("</head>", COMPACT_OVERVIEW_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v16.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v16.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "COMPACT_OVERVIEW_STYLE",
    "_compact_overview",
    "_pair_cards",
    "build_html",
    "build_markdown",
    "write_reports",
]
