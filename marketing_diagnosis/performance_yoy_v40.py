from __future__ import annotations

from datetime import date
from typing import Any

from marketing_diagnosis.performance_yoy_v37 import _score_from_month_ratio
from marketing_diagnosis.visual_diagnosis import _n


CATEGORY = "总营业指标"
METRIC_ORDER = (
    "客房数",
    "维修房",
    "过夜房",
    "过夜房出租率",
    "过夜房出租率(扣自用房)",
    "间夜数",
    "房费",
    "平均房价",
    "出租率",
    "RevPar",
    "现付账房费",
)

_METRIC_ALIASES = {
    "revpar": "RevPar",
    "revpar值": "RevPar",
    "过夜房出租率（扣自用房）": "过夜房出租率(扣自用房)",
}


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _business_date(row: dict[str, Any]) -> str:
    return str(row.get("business_date") or "")[:10]


def _previous_year_day(value: str) -> str:
    try:
        current = date.fromisoformat(value)
    except ValueError:
        return ""
    try:
        return current.replace(year=current.year - 1).isoformat()
    except ValueError:
        return current.replace(year=current.year - 1, day=28).isoformat()


def _metric_name(value: Any) -> str:
    text = str(value or "").strip()
    compact = text.replace(" ", "")
    return _METRIC_ALIASES.get(compact.lower(), _METRIC_ALIASES.get(compact, compact))


def _ratio(previous: Any, current: Any) -> float | None:
    previous_number = _n(previous)
    current_number = _n(current)
    if previous_number is None or current_number in (None, 0):
        return None
    return previous_number / current_number


def _latest_rows_for_day(
    rows: list[dict[str, Any]],
    business_day: str,
) -> dict[str, dict[str, Any]]:
    selected: dict[str, tuple[tuple[str, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        if _business_date(row) != business_day:
            continue
        metric = _metric_name(row.get("metric_name"))
        if metric not in METRIC_ORDER:
            continue
        order_key = (str(row.get("snapshot_time") or ""), index)
        current = selected.get(metric)
        if current is None or order_key >= current[0]:
            selected[metric] = (order_key, row)
    return {metric: value[1] for metric, value in selected.items()}


def patch_performance_yoy(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    """Render item 01 from exact current/prior business dates and total metrics only.

    Rules confirmed for the customer page:
    - current period is the latest ``business_date`` available for ``总营业指标``;
    - comparison period is the exact same calendar day one year earlier;
    - only the eleven metrics in ``METRIC_ORDER`` are retained, in that order;
    - daily/monthly/yearly YOY is previous-period value divided by current value.
    """

    item = _item(result, 1)
    if item is None:
        return

    rows = [
        row
        for row in sections.get("hotel_performance_daily") or []
        if str(row.get("category") or "").strip() == CATEGORY
        and row.get("room_type_id") in (None, "")
        and _metric_name(row.get("metric_name")) in METRIC_ORDER
        and _business_date(row)
    ]

    current_day = max((_business_date(row) for row in rows), default="")
    previous_day = _previous_year_day(current_day) if current_day else ""
    current_rows = _latest_rows_for_day(rows, current_day) if current_day else {}
    previous_rows = _latest_rows_for_day(rows, previous_day) if previous_day else {}

    records: list[dict[str, Any]] = []
    for metric in METRIC_ORDER:
        current = current_rows.get(metric, {})
        previous = previous_rows.get(metric, {})
        current_day_value = _n(current.get("value_day"))
        current_month_value = _n(current.get("value_month"))
        current_year_value = _n(current.get("value_year"))
        previous_day_value = _n(previous.get("value_day"))
        previous_month_value = _n(previous.get("value_month"))
        previous_year_value = _n(previous.get("value_year"))
        records.append(
            {
                "category": CATEGORY,
                "metric_name": metric,
                "value_day": current_day_value,
                "previous_value_day": previous_day_value,
                "yoy_day": _ratio(previous_day_value, current_day_value),
                "value_month": current_month_value,
                "previous_value_month": previous_month_value,
                "yoy_month": _ratio(previous_month_value, current_month_value),
                "value_year": current_year_value,
                "previous_value_year": previous_year_value,
                "yoy_year": _ratio(previous_year_value, current_year_value),
            }
        )

    current_revenue = current_rows.get("房费", {})
    previous_revenue = previous_rows.get("房费", {})
    current_month_revenue = _n(current_revenue.get("value_month"))
    previous_month_revenue = _n(previous_revenue.get("value_month"))
    month_ratio = _ratio(previous_month_revenue, current_month_revenue)
    status, score_ratio = _score_from_month_ratio(
        current_month_revenue,
        previous_month_revenue,
        month_ratio,
    )
    item["data_status"] = status
    item["score_ratio"] = score_ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 0) * score_ratio, 2)
        if score_ratio is not None
        else None
    )

    current_count = sum(
        1
        for record in records
        if any(record.get(key) is not None for key in ("value_day", "value_month", "value_year"))
    )
    comparison_count = sum(
        1
        for record in records
        if any(
            record.get(key) is not None
            for key in ("previous_value_day", "previous_value_month", "previous_value_year")
        )
    )

    item["records"] = records
    item["fields"] = [
        {
            "label": "本期业务日期",
            "value": current_day or None,
            "origin": "business_date",
            "note": "总营业指标中的最新业务日期",
        },
        {
            "label": "同期业务日期",
            "value": previous_day or None,
            "origin": "business_date",
            "note": "本期业务日期的上一年同月同日",
        },
        {
            "label": "本期已取指标数",
            "value": current_count,
            "origin": "固定指标检查",
            "note": f"应取 {len(METRIC_ORDER)} 项",
        },
        {
            "label": "同期已取指标数",
            "value": comparison_count,
            "origin": "固定指标检查",
            "note": f"应取 {len(METRIC_ORDER)} 项",
        },
        {
            "label": "取数状态",
            "value": (
                "完整"
                if current_count == len(METRIC_ORDER) and comparison_count == len(METRIC_ORDER)
                else f"本期{current_count}/{len(METRIC_ORDER)}，同期{comparison_count}/{len(METRIC_ORDER)}"
            ),
            "origin": "固定指标检查",
            "note": "只检查总营业指标下的固定11项",
        },
    ]
    item["note"] = (
        f"本期仅取 business_date={current_day or '未取到'}，同期仅取 business_date={previous_day or '未取到'}；"
        "category 必须为总营业指标。页面固定展示客房数、维修房、过夜房、过夜房出租率、"
        "过夜房出租率(扣自用房)、间夜数、房费、平均房价、出租率、RevPar、现付账房费；"
        "分别展示日度、月度、年度及对应同期值，YOY=同期÷本期。"
    )


__all__ = ["CATEGORY", "METRIC_ORDER", "patch_performance_yoy"]
