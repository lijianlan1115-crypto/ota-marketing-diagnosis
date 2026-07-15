from __future__ import annotations

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


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v12.build_html(result)
    return html_text.replace("</head>", CUSTOMER_CLEAN_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v12.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v12.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = ["build_html", "build_markdown", "write_reports"]
