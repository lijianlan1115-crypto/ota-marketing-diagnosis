from __future__ import annotations

from copy import deepcopy
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


def _customer_display_result(result: dict[str, Any]) -> dict[str, Any]:
    """Swap only the customer-facing item numbers 21 and 23.

    Business data and report.json keep their original identifiers. In the HTML
    presentation, automatic order becomes item 21 and homepage video becomes
    item 23, while item 22 remains the manual crown entry.
    """
    display = deepcopy(result or {})
    visual = display.get("visual_diagnosis") or {}
    items = visual.get("items") or []

    for item in items:
        number = int(item.get("standard_item_id") or 0)
        if number == 21:
            item["standard_item_id"] = 23
        elif number == 23:
            item["standard_item_id"] = 21

    items.sort(key=lambda item: int(item.get("standard_item_id") or 0))
    return display


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v12.build_html(_customer_display_result(result))
    return html_text.replace("</head>", CUSTOMER_CLEAN_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v12.build_markdown(_customer_display_result(result))


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v12.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "CUSTOMER_CLEAN_STYLE",
    "_customer_display_result",
    "build_html",
    "build_markdown",
    "write_reports",
]
