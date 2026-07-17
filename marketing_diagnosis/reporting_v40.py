from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v39 as upstream


SCORE_AXIS_TITLE_STYLE = """
<style>/* SCORE_AXIS_TITLE_V62 */
.score-axis-title-v62{
  fill:#66756e!important;
  font-size:11px!important;
  font-weight:800!important;
  pointer-events:none;
}
</style>
"""

_SCORE_AXIS_TITLE_PATTERN = re.compile(
    r"<text\b(?P<attrs>[^>]*)>(?P<label>\s*(?:HOS\s*分|信息分)\s*)</text>",
    re.IGNORECASE,
)


def _set_attr(attrs: str, name: str, value: str) -> str:
    pattern = re.compile(
        rf"\s+{re.escape(name)}\s*=\s*(['\"]).*?\1",
        re.IGNORECASE | re.DOTALL,
    )
    cleaned = pattern.sub("", attrs)
    return cleaned.rstrip() + f" {name}='{value}'"


def _add_class(attrs: str, class_name: str) -> str:
    pattern = re.compile(r"\bclass\s*=\s*(['\"])(?P<value>.*?)\1", re.IGNORECASE)
    match = pattern.search(attrs)
    if match is None:
        return attrs.rstrip() + f" class='{class_name}'"

    classes = str(match.group("value") or "").split()
    if class_name not in classes:
        classes.append(class_name)
    quote = match.group(1)
    replacement = f"class={quote}{' '.join(classes)}{quote}"
    return attrs[: match.start()] + replacement + attrs[match.end() :]


def fix_score_axis_titles(html_text: str) -> str:
    """Move HOS/information-score titles above the top tick label.

    Both score charts place their vertical-axis title near the first Y-axis tick.
    The customer page therefore renders text such as ``HOS分6.10``.  Keep the
    tick positions unchanged and move only the axis title to the plot's upper
    left, above the highest grid line.
    """

    def replace(match: re.Match[str]) -> str:
        attrs = match.group("attrs") or ""
        attrs = _add_class(attrs, "score-axis-title-v62")
        attrs = _set_attr(attrs, "x", "68")
        attrs = _set_attr(attrs, "y", "6")
        attrs = _set_attr(attrs, "text-anchor", "start")
        attrs = _set_attr(attrs, "dominant-baseline", "hanging")
        return f"<text{attrs}>{match.group('label').strip()}</text>"

    html_text = _SCORE_AXIS_TITLE_PATTERN.sub(replace, html_text)
    if "SCORE_AXIS_TITLE_V62" not in html_text:
        html_text = html_text.replace(
            "</head>",
            SCORE_AXIS_TITLE_STYLE + "</head>",
            1,
        )
    return html_text


def build_html(result: dict[str, Any]) -> str:
    return fix_score_axis_titles(upstream.build_html(result))


def build_markdown(result: dict[str, Any]) -> str:
    return upstream.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = upstream.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(
        fix_score_axis_titles(html_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    return paths


__all__ = [
    "SCORE_AXIS_TITLE_STYLE",
    "build_html",
    "build_markdown",
    "fix_score_axis_titles",
    "write_reports",
]
