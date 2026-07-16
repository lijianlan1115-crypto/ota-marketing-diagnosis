from __future__ import annotations

from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v32


FLOW_HEADER_STYLE = """
<style>
/* Item 04 has long business labels; keep every header on one line and scroll horizontally. */
.flow-table-v23{
  min-width:2100px!important;
}
.flow-table-v23 th{
  white-space:nowrap!important;
  line-height:1.35!important;
  font-size:11px!important;
  padding:13px 10px!important;
}
</style>
"""


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v32.build_html(result)
    return html_text.replace("</head>", FLOW_HEADER_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v32.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v32.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "FLOW_HEADER_STYLE",
    "build_html",
    "build_markdown",
    "write_reports",
]
