from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v34


CLEAN_REPORT_STYLE = """
<style>
/* Generic field notes are hidden; removed audit blocks are not referenced here. */
.metric-row>div>span,
.source-cards>div>span,
.promotion-metric-v34>span,
.reputation-metric-v32>span{
  display:none!important;
}
</style>
"""


_TAG_TOKEN = re.compile(r"<(?P<close>/)?(?P<tag>[a-zA-Z0-9]+)\b[^>]*>", re.DOTALL)
_DETAILS_PATTERN = re.compile(
    r"<details\b[^>]*class=['\"][^'\"]*output-fields-panel[^'\"]*['\"][^>]*>.*?</details>",
    re.DOTALL,
)
_CAPTION_PATTERN = re.compile(
    r"<p\b[^>]*class=['\"][^'\"]*(?:performance-v25-caption|performance-v28-caption|room-source-caption-v30)[^'\"]*['\"][^>]*>.*?</p>",
    re.DOTALL,
)
_PROMOTION_NOTE_PATTERN = re.compile(
    r"(<div class='promotion-metric-v34[^']*'>.*?<strong>.*?</strong>)\s*<span>.*?</span>",
    re.DOTALL,
)
_REPUTATION_NOTE_PATTERN = re.compile(
    r"(<div class='reputation-metric-v32[^']*'>.*?<strong>.*?</strong>)\s*<span>.*?</span>",
    re.DOTALL,
)


def _class_start_pattern(tag: str, class_name: str) -> re.Pattern[str]:
    return re.compile(
        rf"<{re.escape(tag)}\b[^>]*class=['\"][^'\"]*\b{re.escape(class_name)}\b[^'\"]*['\"][^>]*>",
        re.DOTALL,
    )


def _remove_balanced_elements(html_text: str, tag: str, class_name: str) -> str:
    """Remove every balanced element carrying ``class_name``.

    Regex alone is unsafe for nested ``div`` blocks. This lightweight scanner
    counts matching open/close tags so the complete UI block is removed without
    touching the following table or card.
    """

    start_pattern = _class_start_pattern(tag, class_name)
    while True:
        start_match = start_pattern.search(html_text)
        if start_match is None:
            return html_text

        depth = 0
        end_position: int | None = None
        for token in _TAG_TOKEN.finditer(html_text, start_match.start()):
            if token.group("tag").lower() != tag.lower():
                continue
            if token.group("close"):
                depth -= 1
                if depth == 0:
                    end_position = token.end()
                    break
            else:
                depth += 1

        if end_position is None:
            # Keep malformed HTML unchanged rather than deleting the rest of the page.
            return html_text
        html_text = html_text[: start_match.start()] + html_text[end_position:]


def _clean_customer_html(html_text: str) -> str:
    # Item 01: keep the daily/monthly/yearly table and remove the redundant top cards.
    for class_name in ("performance-v25-summary", "performance-v28-summary"):
        html_text = _remove_balanced_elements(html_text, "div", class_name)

    # Remove database table/field audit boxes and all expandable audit panels.
    html_text = _remove_balanced_elements(html_text, "div", "field-standard-note")
    html_text = _DETAILS_PATTERN.sub("", html_text)
    html_text = _CAPTION_PATTERN.sub("", html_text)

    # Item 09 and item 13 cards keep labels and values, but omit field/SQL notes.
    html_text = _PROMOTION_NOTE_PATTERN.sub(r"\1", html_text)
    html_text = _REPUTATION_NOTE_PATTERN.sub(r"\1", html_text)

    return html_text.replace("</head>", CLEAN_REPORT_STYLE + "</head>", 1)


def build_html(result: dict[str, Any]) -> str:
    return _clean_customer_html(reporting_v34.build_html(result))


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v34.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v34.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "CLEAN_REPORT_STYLE",
    "_clean_customer_html",
    "_remove_balanced_elements",
    "build_html",
    "build_markdown",
    "write_reports",
]
