from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v33


PROMOTION_STYLE = """
<style>
.promotion-grid-v34{display:grid;grid-template-columns:repeat(3,minmax(180px,1fr));gap:12px}
.promotion-metric-v34{padding:16px;border:1px solid #dfe8e5;border-radius:12px;background:#f8fbfa;min-height:86px}
.promotion-metric-v34.is-roi{background:#eef6ff;border-color:#c8ddf7}
.promotion-metric-v34 small{display:block;color:var(--muted);font-size:12px;font-weight:800;line-height:1.35}
.promotion-metric-v34 strong{display:block;margin-top:9px;color:#26343d;font-size:22px;line-height:1.2}
.promotion-metric-v34 span{display:block;margin-top:6px;color:var(--muted);font-size:10px;line-height:1.45}
@media(max-width:900px){.promotion-grid-v34{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.promotion-grid-v34{grid-template-columns:1fr}}
</style>
"""


_ITEM_NINE_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-9'>.*?</article>",
    re.DOTALL,
)


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _cards(item: dict[str, Any]) -> str:
    # promotion_status is an internal database filter only. Even when an older
    # result still contains that field, do not expose it in customer HTML.
    fields = [
        field
        for field in list(item.get("fields") or [])
        if str(field.get("label") or "") != "推广状态"
    ]
    cards: list[str] = []
    for field in fields:
        label = str(field.get("label") or "")
        extra_class = " is-roi" if label == "ROI" else ""
        cards.append(
            f"<div class='promotion-metric-v34{extra_class}'>"
            f"<small>{reporting_v8._e(label)}</small>"
            f"<strong>{reporting_v8._e(reporting_v8._value(label, field.get('value')))}</strong>"
            f"<span>{reporting_v8._e(field.get('note') or '')}</span>"
            "</div>"
        )
    return "<div class='promotion-grid-v34'>" + "".join(cards) + "</div>"


def _promotion_card(item: dict[str, Any]) -> str:
    status_key = str(item.get("data_status") or "zero")
    status_text, status_class = reporting_v8.STATUS.get(
        status_key,
        (status_key, "neutral"),
    )
    score = float(item.get("item_score") or 0)
    return (
        f"<article class='diagnosis-card promotion-card-v34' data-status='{reporting_v8._e(status_key)}' "
        f"data-title='{reporting_v8._e(item.get('item_name'))}' id='rule-9'>"
        "<div class='card-top'><div class='rule-no'>09</div>"
        "<div class='card-title'><h3>推广数据</h3>"
        "<p>使用近30天推广投入与预订订单金额计算ROI，本项必须评分。</p></div>"
        "<div class='card-tags'>"
        "<div class='title-meta-item title-period'><small>统计周期</small><strong>近30天</strong></div>"
        f"<div class='title-meta-item title-score {'ok' if score > 0 else 'zero'}'><small>当前得分</small>"
        f"<div class='title-score-value'><strong>{reporting_v8._e(reporting_v8._score_text(item))}</strong>"
        f"<span>满分 {reporting_v8._e(reporting_v8._base_text(item))}</span></div></div>"
        f"<span class='status-badge {status_class}'>{reporting_v8._e(status_text)}</span>"
        "</div></div>"
        "<div class='result-area'>"
        + _cards(item)
        + reporting_v8._source_box(item)
        + f"<div class='notice'>{reporting_v8._e(item.get('note') or '')}</div>"
        + "</div>"
        + reporting_v8._detail_panel(item)
        + "</article>"
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v33.build_html(result)
    item = _item(result, 9)
    if item:
        html_text = _ITEM_NINE_PATTERN.sub(
            lambda _: _promotion_card(item),
            html_text,
            count=1,
        )
    return html_text.replace("</head>", PROMOTION_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v33.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v33.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "PROMOTION_STYLE",
    "_promotion_card",
    "build_html",
    "build_markdown",
    "write_reports",
]
