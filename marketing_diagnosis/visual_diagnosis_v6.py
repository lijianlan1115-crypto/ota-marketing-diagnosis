from __future__ import annotations

from datetime import date
from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v5 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


_SOURCE_FIELDS = [
    "business_date",
    "metric_name",
    "value_day",
    "value_month",
    "value_year",
    "snapshot_time",
]


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _previous_year_date(value: str) -> str:
    current = date.fromisoformat(value[:10])
    try:
        return current.replace(year=current.year - 1).isoformat()
    except ValueError:
        return current.replace(year=current.year - 1, day=28).isoformat()


def _is_total_metric_row(row: dict[str, Any]) -> bool:
    return row.get("room_type_id") in (None, "")


def _latest_metric_rows_for_day(
    rows: list[dict[str, Any]],
    business_date: str,
) -> dict[str, dict[str, Any]]:
    latest: dict[str, tuple[tuple[str, str, str, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        if not _is_total_metric_row(row):
            continue
        if str(row.get("business_date") or "")[:10] != business_date:
            continue
        metric_name = str(row.get("metric_name") or "").strip()
        if not metric_name:
            continue
        sort_key = (
            str(row.get("snapshot_time") or ""),
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            index,
        )
        current = latest.get(metric_name)
        if current is None or sort_key >= current[0]:
            latest[metric_name] = (sort_key, row)
    return {name: value[1] for name, value in latest.items()}


def _yoy(current: Any, previous: Any) -> float | None:
    current_value = _n(current)
    previous_value = _n(previous)
    if current_value is None or previous_value in (None, 0):
        return None
    return (current_value - previous_value) / previous_value


def _score_ratio(yoy: float | None) -> float | None:
    if yoy is None:
        return None
    if yoy > 0.20:
        return 1.0
    if yoy >= 0:
        return 0.8
    if yoy >= -0.20:
        return 0.6
    return 0.0


def _patch_business_date_yoy(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 1)
    if not item:
        return

    rows = [
        row
        for row in sections.get("hotel_performance_daily") or []
        if _is_total_metric_row(row)
        and str(row.get("business_date") or "")[:10]
    ]
    current_day = max(
        (str(row.get("business_date") or "")[:10] for row in rows),
        default="",
    )
    if not current_day:
        item["data_status"] = "missing"
        item["score_ratio"] = None
        item["item_score"] = None
        item["fields"] = []
        item["records"] = []
        item["source_table"] = "hotel_puyue.jl02_hotel_performance_daily"
        item["source_fields"] = list(_SOURCE_FIELDS)
        item["note"] = "未取得JL02的business_date，无法计算去年同期。"
        return

    previous_day = _previous_year_date(current_day)
    current_by_metric = _latest_metric_rows_for_day(rows, current_day)
    previous_by_metric = _latest_metric_rows_for_day(rows, previous_day)

    current_revenue = _n((current_by_metric.get("房费") or {}).get("value_month"))
    previous_revenue = _n((previous_by_metric.get("房费") or {}).get("value_month"))
    revenue_yoy = _yoy(current_revenue, previous_revenue)
    ratio = _score_ratio(revenue_yoy)

    if not current_by_metric:
        status = "missing"
    elif not previous_by_metric:
        status = "missing"
    elif previous_revenue == 0:
        status = "pending_rule"
    else:
        status = "success" if ratio is not None else "missing"

    records: list[dict[str, Any]] = []
    for metric_name in sorted(current_by_metric):
        current_row = current_by_metric[metric_name]
        previous_row = previous_by_metric.get(metric_name) or {}
        current_month = _n(current_row.get("value_month"))
        previous_month = _n(previous_row.get("value_month"))
        records.append(
            {
                "metric_name": metric_name,
                "business_date": current_day,
                "previous_business_date": previous_day,
                "value_day": _n(current_row.get("value_day")),
                "value_month": current_month,
                "value_year": _n(current_row.get("value_year")),
                "previous_value": previous_month,
                "yoy": _yoy(current_month, previous_month),
            }
        )

    item["fields"] = [
        {
            "label": "本期值",
            "value": current_revenue,
            "note": f"{current_day} 房费 value_month",
            "origin": "数据库原值",
        },
        {
            "label": "去年同期值",
            "value": previous_revenue,
            "note": f"{previous_day} 房费 value_month",
            "origin": "同表去年同日",
        },
        {
            "label": "YOY",
            "value": revenue_yoy,
            "note": "（本期值－去年同期值）÷去年同期值",
            "origin": "公式计算",
        },
        {
            "label": "本项原始得分",
            "value": round(10 * ratio, 2) if ratio is not None else None,
            "note": "同比>20%满分；0%至20%得80%；下降20%以内得60%；下降超过20%得0分",
            "origin": "规则计算",
        },
        {
            "label": "取数状态",
            "value": "已取到" if current_by_metric and previous_by_metric else "去年同期未取到",
            "note": f"本期 {current_day}；去年同期 {previous_day}",
            "origin": "business_date精确匹配",
        },
    ]
    item["records"] = records
    item["data_status"] = status
    item["score_ratio"] = ratio
    item["item_score"] = round(float(item.get("base_score") or 10) * ratio, 2) if ratio is not None else None
    item["source_table"] = "hotel_puyue.jl02_hotel_performance_daily"
    item["source_fields"] = list(_SOURCE_FIELDS)
    item["note"] = (
        "本期取JL02最新business_date；去年同期在同一张表中精确匹配上一年同月同日。"
        "同一业务日期、同一指标存在多次采集时，保留最新snapshot_time。"
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_business_date_yoy(result, sections)
    result["rule_version"] = "2026-07-15-v7-jl02-business-date-yoy"
    return result


__all__ = [
    "_latest_metric_rows_for_day",
    "_previous_year_date",
    "build_visual_diagnosis",
]
