from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v31


REPUTATION_STYLE = """
<style>
.reputation-grid-v32{display:grid;grid-template-columns:repeat(3,minmax(180px,1fr));gap:12px}
.reputation-metric-v32{padding:16px;border:1px solid #dfe8e5;border-radius:12px;background:#f8fbfa;min-height:86px}
.reputation-metric-v32.is-yesterday{background:#eef6ff;border-color:#c8ddf7}
.reputation-metric-v32 small{display:block;color:var(--muted);font-size:12px;font-weight:800;line-height:1.35}
.reputation-metric-v32 strong{display:block;margin-top:9px;color:#26343d;font-size:22px;line-height:1.2}
.reputation-metric-v32 span{display:block;margin-top:6px;color:var(--muted);font-size:10px;line-height:1.45}
.reputation-date-v32{display:inline-block;margin-left:4px;color:#34679d;font-weight:800;white-space:nowrap}
@media(max-width:900px){.reputation-grid-v32{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.reputation-grid-v32{grid-template-columns:1fr}}
</style>
"""


_ITEM_THIRTEEN_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-13'>.*?</article>",
    re.DOTALL,
)
_DATE_PATTERN = re.compile(r"\b(20\d{2})[-/]?(\d{2})[-/]?(\d{2})\b")


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _normalize_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = _DATE_PATTERN.search(text)
    if not match:
        return ""
    candidate = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return ""


def _yesterday_date(item: dict[str, Any]) -> str:
    """Return the concrete date used for yesterday's review count."""

    direct = _normalize_date(item.get("yesterday_review_date"))
    if direct:
        return direct

    for field in item.get("fields") or []:
        if str(field.get("label") or "") != "昨日新增点评数":
            continue
        for candidate in (field.get("review_date"), field.get("note")):
            parsed = _normalize_date(candidate)
            if parsed:
                return parsed
    return ""


def _all_metric_cards(item: dict[str, Any]) -> str:
    fields = list(item.get("fields") or [])
    if not fields:
        fields = [
            {
                "label": "数据状态",
                "value": None,
                "note": "数据库未返回可展示记录",
            }
        ]
    review_date = _yesterday_date(item)
    cards: list[str] = []
    for field in fields:
        label = str(field.get("label") or "")
        is_yesterday = label == "昨日新增点评数"
        extra_class = " is-yesterday" if is_yesterday else ""
        display_label = label
        if is_yesterday and review_date:
            display_label = (
                "昨日新增点评数"
                f"<span class='reputation-date-v32'>（{reporting_v8._e(review_date)}）</span>"
            )
        else:
            display_label = reporting_v8._e(display_label)
        value = reporting_v8._value(label, field.get("value"))
        cards.append(
            f"<div class='reputation-metric-v32{extra_class}'>"
            f"<small>{display_label}</small>"
            f"<strong>{reporting_v8._e(value)}</strong>"
            f"<span>{reporting_v8._e(field.get('note') or '')}</span>"
            "</div>"
        )
    return "<div class='reputation-grid-v32'>" + "".join(cards) + "</div>"


def _reputation_card(item: dict[str, Any]) -> str:
    status_key = str(item.get("data_status") or "missing")
    status_text, status_class = reporting_v8.STATUS.get(
        status_key,
        (status_key, "neutral"),
    )
    score_class = "ok" if item.get("item_score") is not None else "pending"
    review_date = _yesterday_date(item)
    period_text = f"最新快照 / {review_date}" if review_date else "最新快照 / 昨日"
    return (
        f"<article class='diagnosis-card reputation-card-v32' data-status='{reporting_v8._e(status_key)}' "
        f"data-title='{reporting_v8._e(item.get('item_name'))}' id='rule-13'>"
        "<div class='card-top'><div class='rule-no'>13</div>"
        "<div class='card-title'><h3>口碑分析</h3>"
        "<p>展示美团与大众点评评分、点评数、未回复数，以及按review_time统计的昨日新增点评数。</p></div>"
        "<div class='card-tags'>"
        f"<div class='title-meta-item title-period'><small>统计周期</small><strong>{reporting_v8._e(period_text)}</strong></div>"
        f"<div class='title-meta-item title-score {score_class}'><small>当前得分</small>"
        f"<div class='title-score-value'><strong>{reporting_v8._e(reporting_v8._score_text(item))}</strong>"
        f"<span>满分 {reporting_v8._e(reporting_v8._base_text(item))}</span></div></div>"
        f"<span class='status-badge {status_class}'>{reporting_v8._e(status_text)}</span>"
        "</div></div>"
        "<div class='result-area'>"
        + _all_metric_cards(item)
        + reporting_v8._source_box(item)
        + f"<div class='notice'>{reporting_v8._e(item.get('note') or '')}</div>"
        + "</div>"
        + reporting_v8._detail_panel(item)
        + "</article>"
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v31.build_html(result)
    item = _item(result, 13)
    if item:
        html_text = _ITEM_THIRTEEN_PATTERN.sub(
            lambda _: _reputation_card(item),
            html_text,
            count=1,
        )
    return html_text.replace("</head>", REPUTATION_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v31.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v31.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "REPUTATION_STYLE",
    "_reputation_card",
    "_yesterday_date",
    "build_html",
    "build_markdown",
    "write_reports",
]
