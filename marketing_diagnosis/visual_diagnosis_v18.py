from __future__ import annotations

from typing import Any

from marketing_diagnosis.room_name_manual_v43 import patch_manual_room_name_score
from marketing_diagnosis.visual_diagnosis_v14 import _recalculate_totals
from marketing_diagnosis.visual_diagnosis_v17 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    patch_manual_room_name_score(result, sections)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-16-v21-manual-room-name-always-score"
    return result


__all__ = ["build_visual_diagnosis"]
