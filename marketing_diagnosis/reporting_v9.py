from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8


_LABEL_PREFIXES = {
    "meituan": "美团",
    "dianping": "大众点评",
}


def _localized_label(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    lower = text.lower()
    for prefix, display in _LABEL_PREFIXES.items():
        if lower.startswith(prefix):
            return display + text[len(prefix):]
    return value


def _localize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Translate legacy English review-platform prefixes before rendering.

    New diagnosis results already emit Chinese labels, while existing report.json
    files may still contain labels such as ``meituan评分`` and
    ``dianping点评条数``.  Rendering through this compatibility layer makes both
    old and new results display consistent Chinese platform names.
    """
    localized = deepcopy(result or {})
    visual = localized.get("visual_diagnosis") or {}
    for item in visual.get("items") or []:
        if int(item.get("standard_item_id") or 0) != 13:
            continue
        for field in item.get("fields") or []:
            field["label"] = _localized_label(field.get("label"))
    return localized


def build_html(result: dict[str, Any]) -> str:
    return reporting_v8.build_html(_localize_result(result))


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v8.build_markdown(_localize_result(result))


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    return reporting_v8.write_reports(_localize_result(result), output_dir)


__all__ = ["build_html", "build_markdown", "write_reports"]
