from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import (
    _latest_distinct_days,
    _pct_value,
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


def _patch_daily_exposure_ratios(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Use the database percentage for each exposure day when it is available.

    ``ad_exposure_ratio_pct`` may be stored either as ``8.95`` or ``0.0895``.
    ``_pct_value`` normalizes both forms to the decimal value used by the
    report renderer. The original formula remains the fallback when the
    database percentage is missing or invalid.
    """
    exposure_rows = _latest_distinct_days(sections.get("exposure_daily") or [])
    rows_by_date = {
        str(row.get("business_date") or "")[:10]: row
        for row in exposure_rows
        if str(row.get("business_date") or "")[:10]
    }

    exposure_item = next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == 3
        ),
        None,
    )
    if not exposure_item:
        return result

    for field in exposure_item.get("fields") or []:
        label = str(field.get("label") or "")
        if not label.endswith(" 广告曝光占比"):
            continue

        business_date = label[:10]
        row = rows_by_date.get(business_date)
        if not row:
            continue

        database_ratio = _pct_value(row.get("ad_exposure_ratio_pct"))
        if database_ratio is None:
            field["note"] = "ad_exposure_ratio_pct 缺失，回退使用 ad_exposure ÷ total_exposure"
            continue

        field["value"] = database_ratio
        field["note"] = "ad_exposure_ratio_pct（数据库原值，已统一换算为小数）"
        field["origin"] = "数据库原值"

    exposure_item["note"] = (
        "近30天总占比按广告曝光合计 ÷ 整体曝光合计计算；"
        "每日占比优先使用数据库 ad_exposure_ratio_pct，缺失时回退公式。"
    )
    result["rule_version"] = "2026-07-14"
    return result


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    return _patch_daily_exposure_ratios(result, sections)
