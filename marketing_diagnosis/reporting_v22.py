from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v21


_SCOPE_SELECT_PATTERN = re.compile(
    r"<select\b[^>]*class=(['\"])[^'\"]*\bscope-select\b[^'\"]*\1[^>]*>.*?</select>",
    re.DOTALL | re.IGNORECASE,
)
_RULE_ONE_PATTERN = re.compile(
    r"(<article\b[^>]*id=(['\"])rule-1\2[^>]*>)(.*?)(</article>)",
    re.DOTALL | re.IGNORECASE,
)
_SUBTOTAL_ROW_PATTERN = re.compile(
    r"<tr\b[^>]*>.*?<span\b[^>]*class=(['\"])[^'\"]*\bfield-name\b[^'\"]*\1[^>]*>\s*小计\s*</span>.*?</tr>",
    re.DOTALL | re.IGNORECASE,
)


def _remove_scope_selector(html_text: str) -> str:
    """Remove the customer-facing report scope selector and keep export actions."""
    return _SCOPE_SELECT_PATTERN.sub("", html_text, count=1)


def _remove_item_one_subtotal(html_text: str) -> str:
    """Hide only the '小计' record from item 01's operating-metric table."""

    def replace_article(match: re.Match[str]) -> str:
        opening, quote, content, closing = match.groups()
        cleaned = _SUBTOTAL_ROW_PATTERN.sub("", content, count=1)
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
