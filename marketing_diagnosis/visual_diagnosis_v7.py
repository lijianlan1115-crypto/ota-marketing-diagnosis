from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v6 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
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


def _field_value(item: dict[str, Any], label: str) -> Any:
    for field in item.get("fields") or []:
        if str(field.get("label") or "") == label:
            return field.get("value")
    return None


def _promotion_spend(rows: list[dict[str, Any]]) -> float | None:
    """Sum real Promotion Express expenses as a positive amount.

    The source table stores expenses as negative transaction amounts. Only rows
    whose transaction_type is exactly ``推广通支出`` participate. The database
    loader has already restricted rows to the diagnosis period, so this function
    only performs the business-condition filter and numeric aggregation.
    """
    values: list[float] = []
    for row in rows:
        if str(row.get("transaction_type") or "").strip() != "推广通支出":
            continue
        value = _n(row.get("transaction_amount"))
        if value is None:
            value = _n(row.get("amount"))
        if value is None:
            continue
        values.append(abs(float(value)))
    return sum(values) if values else None


def _patch_promotion_finance(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 9)
    if not item:
        return

    spend = _promotion_spend(sections.get("promotion_finance") or [])
    revenue = _n(_field_value(item, "本月美团EBK订单金额"))
    roi = None if spend in (None, 0) or revenue is None else revenue / spend

    ratio: float | None = None
    if spend is None:
        status = "missing"
    elif spend == 0:
        status, ratio = "zero", 0.0
    elif spend <= 1000:
        status = "pending_rule"
    elif roi is None:
        status = "missing"
    else:
        status = "success"
        ratio = 1.0 if roi > 10 else 0.6 if roi >= 5 else 0.0

    item["fields"] = [
        {
            "label": "近30天推广投入",
            "value": spend,
            "note": "诊断周期内 transaction_type=推广通支出的 transaction_amount 绝对值合计",
            "origin": "数据库条件汇总",
        },
        {
            "label": "本月美团EBK订单金额",
            "value": revenue,
            "note": "本月美团EBK房费收入",
            "origin": "数据库原值",
        },
        {
            "label": "ROI",
            "value": roi,
            "note": "本月美团EBK订单金额 ÷ 近30天推广投入",
            "origin": "公式计算",
        },
    ]
    item["data_status"] = status
    item["score_ratio"] = ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 8) * ratio, 2)
        if ratio is not None
        else None
    )
    item["source_table"] = (
        "hotel_puyue.meituan_ota_promotion_finance_detail + "
        "hotel_puyue.jy03_hotel_statistics_month"
    )
    item["source_fields"] = [
        "transaction_time",
        "transaction_type=推广通支出",
        "transaction_amount",
        "period_month",
        "dimension_type=渠道",
        "dimension_name=美团EBK",
        "room_revenue",
    ]
    item["note"] = (
        "近30天推广投入按诊断周期内推广通支出明细求和；"
        "数据库支出金额为负数，展示时转换为正的投入金额。"
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_promotion_finance(result, sections)
    result["rule_version"] = "2026-07-15-v8-promotion-expense-sum"
    return result


__all__ = ["_promotion_spend", "build_visual_diagnosis"]
