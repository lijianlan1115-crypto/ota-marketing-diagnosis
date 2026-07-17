from __future__ import annotations

import re
from pathlib import Path

from marketing_diagnosis import reporting_v37 as upstream


PERFORMANCE_TABLE_SCROLL_STYLE = """
<style>/* PERFORMANCE_TABLE_SCROLL_V59 */
.performance-trend-layout-v54{
  display:grid!important;
  grid-template-columns:minmax(0,1fr)!important;
  grid-auto-rows:auto!important;
  gap:16px!important;
  align-items:start!important;
}
.performance-chart-v54,
.performance-detail-v54{
  box-sizing:border-box;
  display:flex;
  flex-direction:column;
  width:100%;
  max-width:100%;
  min-width:0;
  height:auto!important;
  min-height:0!important;
  max-height:none!important;
  padding:18px;
  border:1px solid #dfe8e5;
  border-radius:14px;
  background:#fff;
  overflow:hidden;
}
.performance-chart-v54 .performance-chart-head-v54,
.performance-detail-v54 .performance-detail-head-v54{
  flex:0 0 auto;
}
.performance-chart-v54 .performance-svg-wrap-v54{
  flex:0 0 auto;
  display:flex;
  align-items:center;
  width:100%;
  height:360px!important;
  min-height:360px!important;
  overflow:hidden;
}
.performance-chart-v54 .performance-svg-v54{
  display:block;
  width:100%;
  height:100%!important;
  min-height:0!important;
}
.performance-detail-v54 .performance-detail-scroll-v55{
  flex:0 0 auto;
  height:auto!important;
  min-height:0!important;
}
.performance-detail-scroll-v55{
  display:block;
  width:100%;
  max-width:100%;
  overflow-x:auto;
  overflow-y:hidden;
  padding-bottom:8px;
  scrollbar-gutter:stable;
  overscroll-behavior-inline:contain;
  -webkit-overflow-scrolling:touch;
}
.performance-detail-scroll-v55 .performance-detail-table-v54{
  width:100%!important;
  min-width:940px!important;
  height:auto!important;
  min-height:0!important;
  table-layout:fixed!important;
}
.performance-detail-scroll-v55 .performance-detail-table-v54 thead tr{
  height:82px!important;
}
.performance-detail-scroll-v55 .performance-detail-table-v54 tbody tr{
  height:92px!important;
}
.performance-detail-scroll-v55 .performance-detail-table-v54 th,
.performance-detail-scroll-v55 .performance-detail-table-v54 td{
  box-sizing:border-box;
  height:auto!important;
  padding:12px 9px!important;
  vertical-align:middle!important;
}
.performance-detail-scroll-v55 .performance-detail-table-v54 th:first-child,
.performance-detail-scroll-v55 .performance-detail-table-v54 td:first-child{
  position:sticky;
  left:0;
  z-index:3;
  width:190px!important;
  min-width:190px!important;
  white-space:nowrap!important;
  background:#fff;
  box-shadow:8px 0 12px -12px rgba(30,45,40,.55);
}
.performance-detail-scroll-v55 .performance-detail-table-v54 thead th:first-child{
  z-index:4;
}
.performance-detail-scroll-v55 .performance-detail-table-v54 tbody tr:nth-child(odd) td:first-child{
  background:#f3fbf7;
}
.performance-detail-scroll-v55 .performance-detail-table-v54 th:not(:first-child),
.performance-detail-scroll-v55 .performance-detail-table-v54 td:not(:first-child){
  min-width:180px!important;
}
@media(max-width:680px){
  .performance-chart-v54 .performance-svg-wrap-v54{
    height:320px!important;
    min-height:320px!important;
  }
}
</style>
"""

_TABLE_PATTERN = re.compile(
    r"(<table\b[^>]*class=['\"][^'\"]*performance-detail-table-v54[^'\"]*['\"][^>]*>.*?</table>)",
    re.DOTALL | re.IGNORECASE,
)


def enable_performance_table_scroll(html_text: str) -> str:
    """Stack the operating chart above a complete horizontally scrollable table."""

    if "performance-detail-scroll-v55" not in html_text:
        html_text = _TABLE_PATTERN.sub(
            r"<div class='performance-detail-scroll-v55'>\1</div>",
            html_text,
            count=1,
        )
    if "PERFORMANCE_TABLE_SCROLL_V59" not in html_text:
        html_text = html_text.replace(
            "</head>",
            PERFORMANCE_TABLE_SCROLL_STYLE + "</head>",
            1,
        )
    return html_text


def build_html(result: dict) -> str:
    return enable_performance_table_scroll(upstream.build_html(result))


def build_markdown(result: dict) -> str:
    return upstream.build_markdown(result)


def write_reports(result: dict, output_dir: str | Path) -> dict[str, str]:
    paths = upstream.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(
        enable_performance_table_scroll(html_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    return paths


__all__ = [
    "PERFORMANCE_TABLE_SCROLL_STYLE",
    "build_html",
    "build_markdown",
    "enable_performance_table_scroll",
    "write_reports",
]
