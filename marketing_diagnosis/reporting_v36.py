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
    r"<article\b[^>]*\bid=['\"]rule-4['\"][^>]*>.*?</article>",
    re.DOTALL | re.IGNORECASE,
)
_FIRST_CELL_PATTERN = re.compile(
    r"(<table\b[^>]*class=['\"][^'\"]*flow-table-v23[^'\"]*['\"][^>]*>.*?"
    r"<tbody\b[^>]*>\s*<tr\b[^>]*>\s*<td\b[^>]*>).*?(</td>)",
    re.DOTALL | re.IGNORECASE,
)
_FIRST_CELL_VALUE_PATTERN = re.compile(
    r"<table\b[^>]*class=['\"][^'\"]*flow-table-v23[^'\"]*['\"][^>]*>.*?"
    r"<tbody\b[^>]*>\s*<tr\b[^>]*>\s*<td\b[^>]*>\s*([^<]+?)\s*</td>",
    re.DOTALL | re.IGNORECASE,
)
_HEADER_PATTERN = re.compile(r"<th\b[^>]*>\s*日期\s*</th>", re.IGNORECASE)
_CAPTION_PATTERN = re.compile(
    r"<p\b[^>]*class=['\"][^'\"]*flow-table-caption-v23[^'\"]*['\"][^>]*>.*?</p>",
    re.DOTALL | re.IGNORECASE,
)


def _date_text(value: Any) -> str | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _range_from_end(value: Any, period_days: int = 30) -> str | None:
    end = _date_text(value)
    if not end:
        return None
    start = (
        date.fromisoformat(end) - timedelta(days=max(int(period_days or 30), 1) - 1)
    ).isoformat()
    return f"{start} 至 {end}"


def _period_label(item: dict[str, Any]) -> str:
    records = list(item.get("daily_records") or item.get("records") or [])
    for record in records:
        label = str(record.get("flow_period_label") or "").strip()
        if label:
            return label

    for record in records:
        start = _date_text(
            record.get("flow_period_start")
            or record.get("period_start")
            or record.get("start_date")
            or record.get("stats_start_date")
        )
        end = _date_text(
            record.get("flow_period_end")
            or record.get("period_end")
            or record.get("end_date")
            or record.get("stats_end_date")
        )
        if start and end:
            return f"{start} 至 {end}"

    for record in records:
        label = _range_from_end(
            record.get("business_date")
            or record.get("data_date")
            or record.get("stats_date")
            or record.get("snapshot_time"),
            int(record.get("period_days") or 30),
        )
        if label:
            return label
    return "近30天"


def _period_label_from_card(card: str) -> str:
    match = _FIRST_CELL_VALUE_PATTERN.search(card)
    if not match:
        return "近30天"
    return _range_from_end(match.group(1), 30) or "近30天"


def _patch_flow_card(card: str, label: str) -> str:
    card = _HEADER_PATTERN.sub("<th>统计周期</th>", card, count=1)
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

    def replace_card(match: re.Match[str]) -> str:
        card = match.group(0)
        label = _period_label(item) if item else _period_label_from_card(card)
        if label == "近30天":
            label = _period_label_from_card(card)
        return _patch_flow_card(card, label)

    html_text = _ITEM_FOUR_PATTERN.sub(replace_card, html_text, count=1)
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
    "_period_label_from_card",
    "build_html",
    "build_markdown",
    "write_reports",
]
