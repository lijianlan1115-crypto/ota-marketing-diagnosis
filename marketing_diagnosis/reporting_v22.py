from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v21


_SCOPE_SELECT_PATTERN = re.compile(
    r"<select\b[^>]*class=(['\"])[^'\"]*\bscope-select\b[^'\"]*\1[^>]*>.*?</select>",
    re.DOTALL | re.IGNORECASE,
)
_SCOPE_STYLE_PATTERN = re.compile(
    r"\.scope-select\s*\{[^{}]*\}",
    re.DOTALL | re.IGNORECASE,
)
_RULE_ONE_PATTERN = re.compile(
    r"(<article\b[^>]*id=(['\"])rule-1\2[^>]*>)(.*?)(</article>)",
    re.DOTALL | re.IGNORECASE,
)
_TABLE_ROW_PATTERN = re.compile(
    r"<tr\b[^>]*>.*?</tr>",
    re.DOTALL | re.IGNORECASE,
)
_SUBTOTAL_FIELD_PATTERN = re.compile(
    r"<span\b[^>]*class=(['\"])[^'\"]*\bfield-name\b[^'\"]*\1[^>]*>\s*小计\s*</span>",
    re.DOTALL | re.IGNORECASE,
)


def _remove_scope_selector(html_text: str) -> str:
    """Remove the report scope selector and its now-unused CSS rule.

    Removing the style rule as well keeps generated HTML free of the
    ``scope-select`` marker, so source-level validation does not confuse an
    unused CSS selector with a visible form control.
    """

    cleaned = _SCOPE_SELECT_PATTERN.sub("", html_text, count=1)
    return _SCOPE_STYLE_PATTERN.sub("", cleaned)


def _remove_item_one_subtotal(html_text: str) -> str:
    """Hide only the '小计' record from item 01's operating-metric table.

    Each ``<tr>...</tr>`` is inspected independently. This prevents the cleanup
    from starting at an earlier row such as ``房费`` and consuming multiple rows
    before it reaches the ``小计`` label.
    """

    def replace_article(match: re.Match[str]) -> str:
        opening, quote, content, closing = match.groups()

        def replace_row(row_match: re.Match[str]) -> str:
            row = row_match.group(0)
            return "" if _SUBTOTAL_FIELD_PATTERN.search(row) else row

        cleaned = _TABLE_ROW_PATTERN.sub(replace_row, content)
        return opening + cleaned + closing

    return _RULE_ONE_PATTERN.sub(replace_article, html_text, count=1)


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v21.build_html(result)
    html_text = _remove_item_one_subtotal(html_text)
    return _remove_scope_selector(html_text)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v21.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v21.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "_remove_item_one_subtotal",
    "_remove_scope_selector",
    "build_html",
    "build_markdown",
    "write_reports",
]
