from __future__ import annotations

from typing import Any

from marketing_diagnosis.ctrip_configuration_v63 import build_configuration_items
from marketing_diagnosis.ctrip_reputation_v64 import build_reputation_item
from marketing_diagnosis.ctrip_user_profile_v59 import build_user_profile_item
from marketing_diagnosis.promotion_performance_v46 import patch_promotion_performance
from marketing_diagnosis.review_yesterday_v45 import patch_yesterday_review_count
from marketing_diagnosis.rules_v4 import process as _base_process
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
    result["visual_diagnosis"] = visual

    ctrip_items = result.setdefault("ctrip_items", {})
    ctrip_items["4"] = build_user_profile_item(
        sections.get("ctrip_userprofile_distribution") or []
    )
    ctrip_items["12"] = build_reputation_item(sections)
    ctrip_items.update(build_configuration_items(sections))
    return result


__all__ = ["process"]
