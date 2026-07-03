from __future__ import annotations

from copy import deepcopy
from typing import Any

from marketing_diagnosis.data import normalize_dataset as _base_normalize_dataset


EXPOSURE_KEYS = ("曝光", "曝光量", "exposure")
EXPOSURE_PEOPLE_KEYS = ("曝光人数", "exposure_people", "exposure_users", "exposure_uv")


def _first(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None


def normalize_dataset(raw: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Normalize data while preserving exposure people as a separate field.

    The legacy normalizer mapped Chinese ``曝光人数`` to ``exposure``. That made
    reports unable to show both exposure volume and exposure people, and it also
    made the one-step conversion denominator ambiguous. This compatibility layer
    keeps ``exposure_people`` before running the legacy field mapping; if true
    exposure volume is missing, the later metrics enrichment layer may use
    exposure people as a clearly marked fallback denominator.
    """
    copied = deepcopy(raw or {})
    rows = copied.get("ota_funnel") or []
    for row in rows:
        if not isinstance(row, dict):
            continue
        exposure = _first(row, EXPOSURE_KEYS)
        people = _first(row, EXPOSURE_PEOPLE_KEYS)
        if people not in (None, ""):
            row.setdefault("exposure_people", people)
        if exposure in (None, "") and people not in (None, ""):
            row.setdefault("exposure_people", people)
            row.setdefault("exposure_from_people_fallback", True)
    return _base_normalize_dataset(copied)
