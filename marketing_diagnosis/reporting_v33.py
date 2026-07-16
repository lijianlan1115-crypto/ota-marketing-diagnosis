from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

from marketing_diagnosis import reporting_v23, reporting_v32


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

_FLOW_CARD_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-4'>.*?</article>",
    re.DOTALL,
)
_FIRST_TABLE_CELL_PATTERN = re.compile(
    r"(<table class='flow-table-v23'>.*?<tbody><tr><td>).*?(</td>)",
    re.DOTALL,
)


def _item_four(result: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == 4
        ),
        None,
    )


def _direct_flow_card(item: dict[str, Any]) -> str:
    """Render the mapped 30-day values without recalculating either conversion rate."""

    display_item = deepcopy(item)
    display_item["daily_records"] = []
    display_item["records"] = []
    card = reporting_v23._flow_card(display_item)
    return _FIRST_TABLE_CELL_PATTERN.sub(
        lambda match: match.group(1) + "近30天" + match.group(2),
        card,
        count=1,
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v32.build_html(result)
    item = _item_four(result)
    if item:
        html_text = _FLOW_CARD_PATTERN.sub(
            lambda _: _direct_flow_card(item),
            html_text,
            count=1,
        )
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
    "_direct_flow_card",
    "build_html",
    "build_markdown",
    "write_reports",
]
