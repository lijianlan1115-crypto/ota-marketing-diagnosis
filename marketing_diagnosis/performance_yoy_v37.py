from __future__ import annotations

from datetime import date
from typing import Any

from marketing_diagnosis.visual_diagnosis import _n


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


def _metric_key(row: dict[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("category") or "").strip(),
        str(row.get("metric_name") or "").strip(),
    )


def _latest_rows_for_day(
    rows: list[dict[str, Any]],
    business_day: str,
) -> list[dict[str, Any]]:
    """Keep the latest snapshot for each category + metric on one business day."""
    selected: dict[tuple[str, str], tuple[tuple[str, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        if _business_date(row) != business_day:
            continue
        if row.get("room_type_id") not in (None, ""):
            continue
        key = _metric_key(row)
        if not key[1]:
            continue
        order_key = (str(row.get("snapshot_time") or ""), index)
        current = selected.get(key)
        if current is None or order_key >= current[0]:
            selected[key] = (order_key, row)
    return [selected[key][1] for key in selected]


def _revenue_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Use only 门店收入 / 房费 when category is present.

    Compact customer Excel historically omitted category. It is accepted only when
    every candidate row has an empty category, preserving Excel compatibility
    without allowing a categorized database row such as 总营业指标 / 房费 to win.
    """
    strict = next(
        (
            row
            for row in rows
            if str(row.get("category") or "").strip() == "门店收入"
            and str(row.get("metric_name") or "").strip() == "房费"
        ),
        None,
    )
    if strict is not None:
        return strict
    if all(not str(row.get("category") or "").strip() for row in rows):
        return next(
            (
                row
                for row in rows
                if str(row.get("metric_name") or "").strip() == "房费"
            ),
            {},
        )
    return {}


def _ratio(previous: Any, current: Any) -> float | None:
    """Confirmed display formula: previous-year value divided by current value."""
    previous_number = _n(previous)
    current_number = _n(current)
    if previous_number is None or current_number in (None, 0):
        return None
    return previous_number / current_number


def _score_from_month_ratio(
    current_month: float | None,
    previous_month: float | None,
    month_ratio: float | None,
) -> tuple[str, float | None]:
    """Retain item 01's established score bands with the confirmed YOY ratio.

    A previous-year value of zero remains pending instead of being silently treated
    as a normal ratio, matching the existing business exception handling.
    """
    if current_month is None or previous_month is None:
        return "missing", None
    if current_month == 0 or previous_month == 0 or month_ratio is None:
        return "pending_rule", None
    if month_ratio > 0.2:
        return "success", 1.0
    if month_ratio < -0.2:
        return "success", 0.0
    if month_ratio < 0:
        return "success", 0.6
    return "pending_rule", None


def patch_performance_yoy(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    """Correct item 01 comparison selection and expose day/month/year YOY values.

    Selection rules:
    - current period is the latest ``business_date`` in JL02;
    - previous period is the exact same calendar day one year earlier;
    - rows match by ``category + metric_name``;
    - headline revenue uses only ``门店收入 / 房费`` when category exists;
    - YOY display formula is ``previous-year value / current value``.
    """
    item = _item(result, 1)
    if item is None:
        return

    all_rows = [
        row
        for row in sections.get("hotel_performance_daily") or []
        if row.get("room_type_id") in (None, "") and _business_date(row)
    ]
    current_day = max((_business_date(row) for row in all_rows), default="")
    previous_day = _previous_year_day(current_day) if current_day else ""
    current_rows = _latest_rows_for_day(all_rows, current_day) if current_day else []
    previous_rows = _latest_rows_for_day(all_rows, previous_day) if previous_day else []

    current_by_key = {_metric_key(row): row for row in current_rows}
    previous_by_key = {_metric_key(row): row for row in previous_rows}

    records: list[dict[str, Any]] = []
    for key, row in current_by_key.items():
        previous = previous_by_key.get(key, {})
        current_value_day = _n(row.get("value_day"))
        current_value_month = _n(row.get("value_month"))
        current_value_year = _n(row.get("value_year"))
        previous_value_day = _n(previous.get("value_day"))
        previous_value_month = _n(previous.get("value_month"))
        previous_value_year = _n(previous.get("value_year"))
        records.append(
            {
                "category": key[0],
                "metric_name": key[1],
                "value_day": current_value_day,
                "value_month": current_value_month,
                "value_year": current_value_year,
                "previous_value_day": previous_value_day,
                "previous_value_month": previous_value_month,
                "previous_value_year": previous_value_year,
                "yoy_day": _ratio(previous_value_day, current_value_day),
                "yoy_month": _ratio(previous_value_month, current_value_month),
                "yoy_year": _ratio(previous_value_year, current_value_year),
                # Backward-compatible aliases for older report layers.
                "previous_value": previous_value_month,
                "yoy": _ratio(previous_value_month, current_value_month),
            }
        )

    current_revenue = _revenue_row(current_rows)
    previous_revenue = _revenue_row(previous_rows)
    current_day_revenue = _n(current_revenue.get("value_day"))
    current_month_revenue = _n(current_revenue.get("value_month"))
    current_year_revenue = _n(current_revenue.get("value_year"))
    previous_day_revenue = _n(previous_revenue.get("value_day"))
    previous_month_revenue = _n(previous_revenue.get("value_month"))
    previous_year_revenue = _n(previous_revenue.get("value_year"))
    yoy_day = _ratio(previous_day_revenue, current_day_revenue)
    yoy_month = _ratio(previous_month_revenue, current_month_revenue)
    yoy_year = _ratio(previous_year_revenue, current_year_revenue)
    status, score_ratio = _score_from_month_ratio(
        current_month_revenue,
        previous_month_revenue,
        yoy_month,
    )

    item["data_status"] = status
    item["score_ratio"] = score_ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 0) * score_ratio, 2)
        if score_ratio is not None
        else None
    )
    item["records"] = records
    item["fields"] = [
        {"label": "本期本日值", "value": current_day_revenue, "origin": "门店收入/房费", "note": f"business_date={current_day} 的 value_day"},
        {"label": "去年本日值", "value": previous_day_revenue, "origin": "门店收入/房费", "note": f"business_date={previous_day} 的 value_day"},
        {"label": "本日YOY", "value": yoy_day, "origin": "公式计算", "note": "去年本日÷今年本日"},
        {"label": "本期本月值", "value": current_month_revenue, "origin": "门店收入/房费", "note": f"business_date={current_day} 的 value_month"},
        {"label": "去年本月值", "value": previous_month_revenue, "origin": "门店收入/房费", "note": f"business_date={previous_day} 的 value_month"},
        {"label": "本月YOY", "value": yoy_month, "origin": "公式计算", "note": "去年本月÷今年本月"},
        {"label": "本期本年值", "value": current_year_revenue, "origin": "门店收入/房费", "note": f"business_date={current_day} 的 value_year"},
        {"label": "去年本年值", "value": previous_year_revenue, "origin": "门店收入/房费", "note": f"business_date={previous_day} 的 value_year"},
        {"label": "本年YOY", "value": yoy_year, "origin": "公式计算", "note": "去年本年÷今年本年"},
        {"label": "本项原始得分", "value": item.get("item_score"), "origin": "规则计算", "note": "未折算得分"},
        {"label": "取数状态", "value": "已取到" if current_revenue and previous_revenue else "未完整取到", "origin": "条件判断", "note": "必须精确匹配本期与去年同日的门店收入/房费"},
    ]
    item["note"] = (
        f"本期按 business_date={current_day} 取值；去年同期按 business_date={previous_day} 精确取值；"
        "相同指标必须同时匹配 category 与 metric_name。顶部房费仅使用 category=门店收入、"
        "metric_name=房费。页面分别展示本日、本月、本年的去年同期值和 YOY；"
        "YOY=去年同期÷今年同期。"
    )


__all__ = ["patch_performance_yoy"]
