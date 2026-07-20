from __future__ import annotations

from typing import Any

from marketing_diagnosis.promotion_performance_v46 import patch_promotion_performance
from marketing_diagnosis.review_yesterday_v45 import patch_yesterday_review_count
from marketing_diagnosis.rules_v4 import process as _base_process
from marketing_diagnosis.visual_diagnosis_v14 import _recalculate_totals
from marketing_diagnosis.visual_diagnosis_v20 import build_visual_diagnosis


def process(data: dict[str, Any]) -> dict[str, Any]:
    """Preserve established rules and replace only the visual diagnosis layer."""

    result = _base_process(data)
    sections = data.get("sections") or {}
    visual = build_visual_diagnosis(
        sections,
        str(data.get("hotel_name") or ""),
    )
    patch_promotion_performance(visual, sections)
    patch_yesterday_review_count(visual, sections)
    # Promotion performance is patched after the visual diagnosis builder has
    # already calculated its totals. Recalculate here so a mandatory zero-score
    # promotion item still contributes its 8-point base to the denominator.
    _recalculate_totals(visual)
    result["visual_diagnosis"] = visual
    return result


__all__ = ["process"]
