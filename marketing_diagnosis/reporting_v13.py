from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v12


CUSTOMER_CLEAN_STYLE = """
<style>
/* Customer-facing report keeps conclusions and values only. Technical source,
   formula and query-scope notes remain in report.json for audit, but are not
   displayed anywhere in the customer HTML report. */
.metric-row > div > span,
.video-summary-card > span,
.field-standard-note,
.result-area > .notice,
.config-status-note,
.metric-details .output-table th:nth-child(3),
.metric-details .output-table td:nth-child(3),
.metric-details .output-table th:nth-child(4),
.metric-details .output-table td:nth-child(4) {
  display: none !important;
}
</style>
"""

# Internal source IDs stay unchanged so database logic and manual-input scripts
# continue to work. Only customer-visible numbering/order is changed:
# source 23 automatic order -> display 21
# source 21 homepage video  -> display 22
# source 22 hotel crown     -> display 23
_TAIL_DISPLAY_ORDER = ((23, 21), (21, 22), (22, 23))


def _replace_first_number(text: str, source_number: int, display_number: int) -> str:
    return re.sub(
        rf"(<td>{source_number:02d}</td>)",
        f"<td>{display_number:02d}</td>",
        text,
        count=1,
    )


def _renumber_card(html_text: str, source_number: int, display_number: int) -> str:
    pattern = re.compile(
        rf"(<article class='diagnosis-card'[^>]*id='rule-{source_number}'>.*?<div class='rule-no'>)"
        rf"{source_number:02d}(</div>)",
        re.DOTALL,
    )
    return pattern.sub(
        lambda match: match.group(1) + f"{display_number:02d}" + match.group(2),
        html_text,
        count=1,
    )


def _reorder_nav(html_text: str) -> str:
    matches: dict[int, re.Match[str]] = {}
    for source_number, _ in _TAIL_DISPLAY_ORDER:
        match = re.search(
            rf"<a href='#rule-{source_number}'><span>{source_number:02d}</span>.*?</a>",
            html_text,
            re.DOTALL,
        )
        if match:
            matches[source_number] = match
    if len(matches) != 3:
        return html_text

    ordered: list[str] = []
    for source_number, display_number in _TAIL_DISPLAY_ORDER:
        entry = matches[source_number].group(0)
        entry = entry.replace(
            f"<span>{source_number:02d}</span>",
            f"<span>{display_number:02d}</span>",
            1,
        )
        ordered.append(entry)

    start = min(match.start() for match in matches.values())
    end = max(match.end() for match in matches.values())
    return html_text[:start] + "".join(ordered) + html_text[end:]


def _summary_row_pattern(source_number: int) -> re.Pattern[str]:
    # Tempered matching prevents one row search from consuming neighboring rows.
    return re.compile(
        rf"<tr data-status='[^']*' data-title='[^']*'>"
        rf"(?:(?!</tr>).)*?<a href='#rule-{source_number}'>"
        rf"(?:(?!</tr>).)*?</tr>",
        re.DOTALL,
    )


def _reorder_summary(html_text: str) -> str:
    matches: dict[int, re.Match[str]] = {}
    for source_number, _ in _TAIL_DISPLAY_ORDER:
        match = _summary_row_pattern(source_number).search(html_text)
        if match:
            matches[source_number] = match
    if len(matches) != 3:
        return html_text

    ordered: list[str] = []
    for source_number, display_number in _TAIL_DISPLAY_ORDER:
        row = matches[source_number].group(0)
        row = _replace_first_number(row, source_number, display_number)
        ordered.append(row)

    start = min(match.start() for match in matches.values())
    end = max(match.end() for match in matches.values())
    return html_text[:start] + "".join(ordered) + html_text[end:]


def _apply_customer_tail_order(html_text: str) -> str:
    # Automatic order is already shown as row 21 inside the configuration table.
    # The two standalone cards retain their original internal anchors while their
    # visible numbers become 22 (video) and 23 (hotel crown).
    html_text = _renumber_card(html_text, 21, 22)
    html_text = _renumber_card(html_text, 22, 23)
    html_text = _reorder_nav(html_text)
    return _reorder_summary(html_text)


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v12.build_html(result)
    html_text = _apply_customer_tail_order(html_text)
    return html_text.replace("</head>", CUSTOMER_CLEAN_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v12.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v12.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "CUSTOMER_CLEAN_STYLE",
    "_TAIL_DISPLAY_ORDER",
    "_apply_customer_tail_order",
    "build_html",
    "build_markdown",
    "write_reports",
]
