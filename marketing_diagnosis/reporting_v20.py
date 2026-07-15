from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v18, reporting_v19


_SCRIPT_PATTERN = re.compile(
    r"<script\b[^>]*>.*?</script>",
    re.DOTALL | re.IGNORECASE,
)
_CROWN_CARD_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-22'>.*?</article>",
    re.DOTALL,
)


def _remove_old_crown_script(html_text: str) -> str:
    """Remove only the script tag that implements the old crown input.

    The previous expression started at any ``<script>(function(){`` block and
    searched across subsequent script tags until it encountered
    ``crown-save-button``. When the HOS chart had an earlier IIFE script, that
    expression deleted every diagnosis card between item 06 and the crown card.

    Matching complete script tags first prevents cleanup from crossing a
    ``</script>`` boundary.
    """

    def replace(match: re.Match[str]) -> str:
        script = match.group(0)
        markers = (
            "crown-save-button",
            "crown-type-input",
            "s14:crown:",
        )
        return "" if any(marker in script for marker in markers) else script

    return _SCRIPT_PATTERN.sub(replace, html_text)


def _replace_crown(html_text: str, result: dict[str, Any]) -> str:
    cleaned = _remove_old_crown_script(html_text)
    return _CROWN_CARD_PATTERN.sub(
        lambda _: reporting_v19._manual_crown_card(result),
        cleaned,
        count=1,
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v18.build_html(result)
    html_text = _replace_crown(html_text, result)
    return html_text.replace("</head>", reporting_v19.CROWN_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v18.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v18.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "_remove_old_crown_script",
    "_replace_crown",
    "build_html",
    "build_markdown",
    "write_reports",
]
