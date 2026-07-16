from __future__ import annotations

from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v26


STACKED_SCAN_INFO_STYLE = """
<style>
/* Item 07 and item 08 are intentionally stacked as two full-width rows. */
.diagnosis-pair-v17{
  grid-template-columns:minmax(0,1fr)!important;
  gap:22px!important;
}
.diagnosis-pair-v17>.diagnosis-card{
  width:100%;
  min-width:0;
}
</style>
"""


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v26.build_html(result)
    return html_text.replace("</head>", STACKED_SCAN_INFO_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v26.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v26.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "STACKED_SCAN_INFO_STYLE",
    "build_html",
    "build_markdown",
    "write_reports",
]
