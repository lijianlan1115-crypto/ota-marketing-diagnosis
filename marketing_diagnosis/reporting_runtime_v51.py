from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v40 as upstream


CARD_RE = re.compile(
    r"<article\b[^>]*\bid=['\"]rule-4['\"][^>]*>.*?</article>",
    re.DOTALL | re.IGNORECASE,
)
CELL_RE = re.compile(
    r"(<table\b[^>]*flow-table-v23[^>]*>.*?<tbody\b[^>]*>\s*<tr\b[^>]*>\s*<td\b[^>]*>).*?(</td>)",
    re.DOTALL | re.IGNORECASE,
)
VALUE_RE = re.compile(
    r"<table\b[^>]*flow-table-v23[^>]*>.*?<tbody\b[^>]*>\s*<tr\b[^>]*>\s*<td\b[^>]*>\s*([^<]+?)\s*</td>",
    re.DOTALL | re.IGNORECASE,
)
HEADER_RE = re.compile(r"<th\b[^>]*>\s*日期\s*</th>", re.IGNORECASE)
CAPTION_RE = re.compile(
    r"<p\b[^>]*flow-table-caption-v23[^>]*>.*?</p>",
    re.DOTALL | re.IGNORECASE,
)


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()[:10]
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _period_label(card: str) -> str:
    match = VALUE_RE.search(card)
    if match is None:
        return "近30天"
    raw = match.group(1).strip()
    if "至" in raw:
        return raw
    end = _parse_date(raw)
    if end is None:
        return "近30天"
    start = end - timedelta(days=29)
    return f"{start.isoformat()} 至 {end.isoformat()}"


def rewrite_flow_period(html_text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        card = match.group(0)
        label = _period_label(card)
        card = HEADER_RE.sub("<th>统计周期</th>", card, count=1)
        card = CELL_RE.sub(
            lambda cell: cell.group(1) + label + cell.group(2),
            card,
            count=1,
        )
        return CAPTION_RE.sub("", card)

    return CARD_RE.sub(replace, html_text, count=1)


def build_html(result: dict[str, Any]) -> str:
    return rewrite_flow_period(upstream.build_html(result))


def build_markdown(result: dict[str, Any]) -> str:
    return upstream.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = upstream.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(
        rewrite_flow_period(html_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    return paths


__all__ = [
    "build_html",
    "build_markdown",
    "rewrite_flow_period",
    "write_reports",
]
