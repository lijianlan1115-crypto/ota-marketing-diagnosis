from __future__ import annotations

from copy import deepcopy
from typing import Any

from marketing_diagnosis.performance_yoy_v37 import patch_performance_yoy
from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v13 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)
from marketing_diagnosis.visual_diagnosis_v14 import (
    _latest_rows_by_day,
    _patch_authoritative_flow,
    _recalculate_totals,
)


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _safe_div(numerator: Any, denominator: Any) -> float | None:
    top, bottom = _n(numerator), _n(denominator)
    if top is None or bottom in (None, 0):
        return None
    return top / bottom


def _flow_daily_records(
    sections: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build the original daily flow table rows without changing scoring.

    The authoritative FLOW selectors already enforce Meituan daily grain, canonical
    metric codes and latest snapshot per business date. This helper only merges
    those selected values into one display record per date.
    """

    all_rows = list(sections.get("ota_funnel") or [])
    by_day: dict[str, dict[str, Any]] = {}
    specifications = (
        ("exposure", ("exposure", "peer_exposure")),
        ("views", ("views", "peer_views")),
        ("paid_orders", ("paid_orders", "peer_paid_orders")),
        (
            "exposure_to_view_rate",
            ("exposure_to_view_rate", "peer_exposure_to_view_rate"),
        ),
        (
            "payment_conversion_rate",
            ("payment_conversion_rate", "peer_payment_conversion_rate"),
        ),
    )

    for target, keys in specifications:
        for row in _latest_rows_by_day(all_rows, target):
            day = str(row.get("business_date") or "")[:10]
            if not day:
                continue
            record = by_day.setdefault(day, {"business_date": day})
            for key in keys:
                value = row.get(key)
                if value not in (None, ""):
                    record[key] = value

    records: list[dict[str, Any]] = []
    for day in sorted(by_day):
        record = by_day[day]
        record.setdefault(
            "exposure_to_view_rate",
            _safe_div(record.get("views"), record.get("exposure")),
        )
        record.setdefault(
            "peer_exposure_to_view_rate",
            _safe_div(record.get("peer_views"), record.get("peer_exposure")),
        )
        record.setdefault(
            "payment_conversion_rate",
            _safe_div(record.get("paid_orders"), record.get("views")),
        )
        record.setdefault(
            "peer_payment_conversion_rate",
            _safe_div(record.get("peer_paid_orders"), record.get("peer_views")),
        )
        records.append(record)
    return records[-30:]


def _is_daily_meituan(row: dict[str, Any]) -> bool:
    platform = str(row.get("platform") or "").strip().lower()
    period = str(row.get("period_type") or row.get("stats_period_type") or "").strip().lower()
    platform_ok = platform in {"meituan", "美团", "美团酒店"}
    period_ok = not period or period in {"日", "daily", "day", "当日"}
    return platform_ok and period_ok


def _information_daily_records(
    sections: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Keep the latest information-score snapshot for each date, at most 30 days.

    This function only supplies report-display history. Item 08's existing score,
    status and rule calculation remain untouched.
    """

    selected: dict[str, tuple[tuple[str, int], dict[str, Any]]] = {}
    for index, row in enumerate(sections.get("ota_funnel") or []):
        if not _is_daily_meituan(row):
            continue
        value = _n(row.get("content_score"))
        day = str(row.get("business_date") or "")[:10]
        if value is None or not day:
            continue
        order_key = (str(row.get("snapshot_time") or ""), index)
        current = selected.get(day)
        if current is None or order_key >= current[0]:
            selected[day] = (
                order_key,
                {
                    "business_date": day,
                    "content_score": value,
                    "content_score_rank": row.get("content_score_rank"),
                },
            )
    return [selected[day][1] for day in sorted(selected)[-30:]]


def _attach_information_history(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 8)
    if item is None:
        return

    records = _information_daily_records(sections)
    item["daily_records"] = records
    if not records:
        return

    values = [float(record["content_score"]) for record in records]
    start = records[0]["business_date"]
    end = records[-1]["business_date"]
    latest = records[-1]
    latest_rank = latest.get("content_score_rank")
    average = sum(values) / len(values)

    item["fields"] = [
        {
            "label": "展示范围",
            "value": f"{start} 至 {end}",
            "note": "按业务日期去重后最多展示近30天",
            "origin": "区间统计",
        },
        {
            "label": "是否有信息分",
            "value": "有",
            "note": "统计周期内存在有效信息分记录",
            "origin": "条件判断",
        },
        {
            "label": "有效数据天数",
            "value": len(records),
            "note": "按业务日期去重后的信息分记录数",
            "origin": "区间统计",
        },
        {
            "label": "近30天平均分",
            "value": average,
            "note": "有效日信息分合计除以有效数据天数",
            "origin": "公式计算",
        },
        {
            "label": "最新信息分",
            "value": latest["content_score"],
            "note": "最近一个有信息分日期的数据",
            "origin": "最新记录",
        },
        {
            "label": "最新同行排名",
            "value": latest_rank,
            "note": "存在同行排名时展示，不参与本项评分",
            "origin": "最新记录",
        },
        {
            "label": "统计日期",
            "value": end,
            "note": "兼容原信息分展示字段",
            "origin": "最新记录",
        },
        {
            "label": "信息分",
            "value": latest["content_score"],
            "note": "兼容原信息分展示字段",
            "origin": "最新记录",
        },
        *[
            {
                "label": record["business_date"],
                "value": record["content_score"],
                "note": (
                    f"同行排名 {record['content_score_rank']}"
                    if record.get("content_score_rank") not in (None, "")
                    else "暂无同行排名"
                ),
                "origin": "日数据",
            }
            for record in records
        ],
    ]
    item["note"] = (
        "页面按业务日期展示最多近30天信息分趋势；同日多次快照仅保留最新一条。"
        "本项原有评分逻辑不变。"
    )


def _restore_flow_layout(
    result: dict[str, Any],
    original_fields: list[dict[str, Any]],
    original_note: str,
) -> None:
    """Keep the established item-04 metric layout when canonical FLOW rows are absent."""

    item = _item(result, 4)
    if not item:
        return

    fields = list(item.get("fields") or [])
    collapsed_fallback = (
        item.get("data_status") == "missing"
        and len(fields) <= 1
        and (not fields or str(fields[0].get("label") or "") == "曝光人数")
    )
    if not collapsed_fallback:
        return

    item["fields"] = deepcopy(original_fields)
    item["score_ratio"] = None
    item["item_score"] = None
    item["data_status"] = "missing"
    item["note"] = (
        "未匹配到美团日口径的权威 FLOW_* 指标，当前不参与评分；"
        "页面保留原有完整流量指标布局，便于核对曝光、浏览、订单、"
        "转化率、同行均值及同行排名。"
        + (f" 原口径说明：{original_note}" if original_note else "")
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    patch_performance_yoy(result, sections)

    original_item = _item(result, 4) or {}
    original_fields = deepcopy(list(original_item.get("fields") or []))
    original_note = str(original_item.get("note") or "")

    _patch_authoritative_flow(result, sections)
    flow_item = _item(result, 4)
    if flow_item is not None:
        flow_item["daily_records"] = _flow_daily_records(sections)
    _restore_flow_layout(result, original_fields, original_note)
    _attach_information_history(result, sections)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-16-v18-business-date-yoy"
    return result


__all__ = [
    "_flow_daily_records",
    "_information_daily_records",
    "build_visual_diagnosis",
]
