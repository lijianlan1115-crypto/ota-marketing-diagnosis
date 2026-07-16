from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import re

from marketing_diagnosis import reporting_v23, reporting_v25


_FLOW_CARD_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-4'>.*?</article>",
    re.DOTALL,
)
_FIRST_TABLE_CELL_PATTERN = re.compile(
    r"(<table class='flow-table-v23'>.*?<tbody><tr><td>).*?(</td>)",
    re.DOTALL,
)


def _flow_summary_card(item: dict[str, Any]) -> str:
    """Render item 04 as exactly one near-30-day aggregate row.

    The underlying daily records remain available in the diagnosis result for audit.
    Only the customer-facing table is collapsed to the already calculated aggregate
    fields, so scoring and database selection are unchanged.
    """

    display_item = deepcopy(item)
    display_item["daily_records"] = []
    display_item["records"] = []
    card = reporting_v23._flow_card(display_item)
    return _FIRST_TABLE_CELL_PATTERN.sub(
        lambda match: match.group(1) + "近30天" + match.group(2),
        card,
        count=1,
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


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v25.build_html(result)
    item = _item_four(result)
    if item:
        html_text = _FLOW_CARD_PATTERN.sub(
            lambda _: _flow_summary_card(item),
            html_text,
            count=1,
        )
    return html_text


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v25.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v25.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "_flow_summary_card",
    "build_html",
    "build_markdown",
    "write_reports",
]
