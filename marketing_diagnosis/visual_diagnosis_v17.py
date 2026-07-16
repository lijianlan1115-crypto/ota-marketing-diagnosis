from __future__ import annotations

from typing import Any

from marketing_diagnosis.room_type_classification_v42 import patch_room_type_summary
from marketing_diagnosis.visual_diagnosis_v14 import _recalculate_totals
from marketing_diagnosis.visual_diagnosis_v16 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    patch_room_type_summary(result, sections)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-16-v20-jl11-room-type-summary"
    return result


__all__ = ["build_visual_diagnosis"]
