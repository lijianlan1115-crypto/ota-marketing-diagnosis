from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v17


_DETAIL_PANEL_PATTERN = re.compile(
    r"<details\b[^>]*class=(['\"])"
    r"[^'\"]*\bmetric-details\b[^'\"]*\1[^>]*>.*?</details>",
    re.DOTALL | re.IGNORECASE,
)


def _remove_metric_detail_panels(html_text: str) -> str:
    """Remove every per-item '查看全部诊断指标' expander from customer HTML.

    The underlying fields remain in report.json and the diagnosis result object;
    this changes only the rendered customer page.
    """
    return _DETAIL_PANEL_PATTERN.sub("", html_text)


def build_html(result: dict[str, Any]) -> str:
    return _remove_metric_detail_panels(reporting_v17.build_html(result))


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v17.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v17.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "_remove_metric_detail_panels",
    "build_html",
    "build_markdown",
    "write_reports",
]
