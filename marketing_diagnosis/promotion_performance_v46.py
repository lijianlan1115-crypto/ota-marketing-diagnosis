from __future__ import annotations

from typing import Any


SOURCE_TABLE = "hotel_puyue.meituan_ota_promotion_performance_30d"
SOURCE_FIELDS = [
    "promotion_status",
    "spend_amount",
    "booking_order_amount",
]


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _latest_performance_row(
    sections: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    rows = [
        row
        for row in list(sections.get("promotion_finance") or [])
        if isinstance(row, dict)
        and (
            "spend_amount" in row
            or "booking_order_amount" in row
            or "promotion_status" in row
            or "promotion_performance_30d"
            in str(row.get("source_table") or row.get("__source_table") or "")
        )
    ]
    if not rows:
        return {}
    return max(
        enumerate(rows),
        key=lambda pair: (
            str(pair[1].get("snapshot_time") or ""),
            str(pair[1].get("updated_at") or ""),
            str(pair[1].get("created_at") or ""),
            str(pair[1].get("business_date") or ""),
            pair[0],
        ),
    )[1]


def _score_ratio(
    promotion_status: str,
    spend_amount: float | None,
    roi: float | None,
) -> float:
    if promotion_status != "RUNNING":
        return 0.0
    if spend_amount is None or spend_amount <= 1000:
        return 0.0
    if roi is None:
        return 0.0
    if roi > 10:
        return 1.0
    if roi >= 5:
        return 0.60
    return 0.0


def patch_promotion_performance(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    """Replace item 09 with the mandatory 30-day promotion performance rule."""

    item = _item(result, 9)
    if item is None:
        return

    row = _latest_performance_row(sections)
    status = str(row.get("promotion_status") or "").strip().upper()
    spend = _number(row.get("spend_amount"))
    booking_amount = _number(row.get("booking_order_amount"))
    roi = (
        booking_amount / spend
        if booking_amount is not None and spend not in (None, 0)
        else None
    )
    ratio = _score_ratio(status, spend, roi)
    base_score = float(item.get("base_score") or 8)

    item["participates_in_score"] = True
    item["score_ratio"] = ratio
    item["item_score"] = round(base_score * ratio, 2)
    item["data_status"] = "success" if ratio > 0 else "zero"
    item["source_table"] = SOURCE_TABLE
    item["source_fields"] = SOURCE_FIELDS + [
        "ROI=booking_order_amount/spend_amount",
        "promotion_status=RUNNING",
    ]
    item["promotion_performance"] = {
        "promotion_status": status or None,
        "spend_amount": spend,
        "booking_order_amount": booking_amount,
        "roi": roi,
    }
    item["fields"] = [
        {
            "label": "推广状态",
            "value": status or None,
            "origin": "数据库原值",
            "note": "仅promotion_status=RUNNING时视为生效",
        },
        {
            "label": "近30天推广投入",
            "value": spend,
            "origin": "数据库原值",
            "note": "spend_amount；投入金额必须大于1000元才进入ROI评分",
        },
        {
            "label": "预订订单金额（元）",
            "value": booking_amount,
            "origin": "数据库原值",
            "note": "booking_order_amount",
        },
        {
            "label": "ROI",
            "value": roi,
            "origin": "公式计算",
            "note": "booking_order_amount ÷ spend_amount",
        },
    ]

    if not row:
        item["note"] = (
            "本项必须评分：未取得meituan_ota_promotion_performance_30d记录，"
            "按0分计入总分。"
        )
    elif status != "RUNNING":
        item["note"] = (
            f"本项必须评分：promotion_status={status or '空'}，未处于RUNNING状态，"
            "按0分计入总分。"
        )
    elif spend is None:
        item["note"] = "本项必须评分：spend_amount缺失，按0分计入总分。"
    elif spend <= 1000:
        item["note"] = (
            f"本项必须评分：近30天推广投入为{spend:g}元，未超过1000元，"
            "按0分计入总分。"
        )
    elif booking_amount is None:
        item["note"] = (
            "本项必须评分：booking_order_amount缺失，无法计算ROI，按0分计入总分。"
        )
    elif roi > 10:
        item["note"] = f"ROI={roi:.2f}>10，评分比例100%，本项得{base_score:g}分。"
    elif roi >= 5:
        item["note"] = (
            f"5≤ROI={roi:.2f}≤10，评分比例60%，本项得{base_score * 0.6:g}分。"
        )
    else:
        item["note"] = f"ROI={roi:.2f}<5，评分比例0%，本项得0分。"


__all__ = [
    "SOURCE_FIELDS",
    "SOURCE_TABLE",
    "_latest_performance_row",
    "_score_ratio",
    "patch_promotion_performance",
]
