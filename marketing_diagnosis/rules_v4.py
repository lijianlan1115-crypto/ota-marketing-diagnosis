from __future__ import annotations

from typing import Any

from marketing_diagnosis.rules_v3 import process as _base_process
from marketing_diagnosis.visual_diagnosis_v17 import build_visual_diagnosis


def process(data: dict[str, Any]) -> dict[str, Any]:
    """Preserve the established rule pipeline and replace only item-02 visuals."""

    result = _base_process(data)
    sections = data.get("sections") or {}
    result["visual_diagnosis"] = build_visual_diagnosis(
        sections,
        str(data.get("hotel_name") or ""),
    )
    return result


__all__ = ["process"]
