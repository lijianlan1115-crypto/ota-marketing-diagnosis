from __future__ import annotations

from copy import deepcopy
from typing import Any

from marketing_diagnosis.data import normalize_dataset as _base_normalize_dataset


EXPOSURE_KEYS = ("曝光", "曝光量", "exposure")
EXPOSURE_PEOPLE_KEYS = ("曝光人数", "exposure_people", "exposure_users", "exposure_uv")
ROOM_TYPE_KEYS = ("房型", "房型名称", "room_type", "room_type_name", "source_room_type_name")


def _first(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None


def normalize_dataset(raw: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Normalize data while preserving exposure people and room-type fields."""
    copied = deepcopy(raw or {})
    rows = copied.get("ota_funnel") or []
    for row in rows:
        if not isinstance(row, dict):
            continue
        exposure = _first(row, EXPOSURE_KEYS)
        people = _first(row, EXPOSURE_PEOPLE_KEYS)
        room_type = _first(row, ROOM_TYPE_KEYS)
        if room_type not in (None, ""):
            row.setdefault("room_type_name", room_type)
        if people not in (None, ""):
            row.setdefault("exposure_people", people)
        if exposure in (None, "") and people not in (None, ""):
            row.setdefault("exposure_people", people)
            row.setdefault("exposure_from_people_fallback", True)
            for key in EXPOSURE_PEOPLE_KEYS:
                if key != "exposure_people" and key in row:
                    row.pop(key, None)
    return _base_normalize_dataset(copied)
