from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v35


FLOW_PERIOD_STYLE = """
<style>
.flow-table-v23 th:first-child,
.flow-table-v23 td:first-child{
  min-width:190px!important;
  white-space:nowrap!important;
}
</style>
"""

_ITEM_FOUR_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-4'>.*?</article>",
    re.DOTALL,
)
_FIRST_CELL_PATTERN = re.compile(
    r"(<table class='flow-table-v23'>.*?<tbody><tr><td>).*?(</td>)",
    re.DOTALL,
)
_CAPTION_PATTERN = re.compile(
    r"<p class='flow-table-caption-v23'>.*?</p>",
    re.DOTALL,
)


def _date_text(value: Any) -> str | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _period_label(item: dict[str, Any]) -> str:
    records = list(item.get("daily_records") or item.get("records") or [])
    for record in records:
        label = str(record.get("flow_period_label") or "").strip()
        if label:
            return label

    for record in records:
        end = _date_text(
            record.get("flow_period_end")
            or record.get("business_date")
            or record.get("snapshot_time")
        )
        if not end:
            continue
        period_days = int(record.get("period_days") or 30)
        start = (
            date.fromisoformat(end) - timedelta(days=max(period_days, 1) - 1)
        ).isoformat()
        return f"{start} 至 {end}"

    return "近30天"


def _patch_flow_card(card: str, label: str) -> str:
    card = card.replace("<th>日期</th>", "<th>统计周期</th>", 1)
    card = _FIRST_CELL_PATTERN.sub(
        lambda match: match.group(1) + label + match.group(2),
        card,
        count=1,
    )
    return _CAPTION_PATTERN.sub("", card)


def _item_four(result: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == 4
        ),
        None,
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v35.build_html(result)
    item = _item_four(result)
    if item:
        label = _period_label(item)
        html_text = _ITEM_FOUR_PATTERN.sub(
            lambda match: _patch_flow_card(match.group(0), label),
            html_text,
            count=1,
        )
    return html_text.replace("</head>", FLOW_PERIOD_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v35.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v35.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "FLOW_PERIOD_STYLE",
    "_patch_flow_card",
    "_period_label",
    "build_html",
    "build_markdown",
    "write_reports",
]
