from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v2 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


_DAILY_PERIODS = {"日", "daily", "day", "当日"}


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _daily_meituan_rows(sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in sections.get("ota_funnel") or []
        if str(row.get("platform") or "").lower() == "meituan"
        and str(row.get("period_type") or "").strip().lower() in _DAILY_PERIODS
    ]
    return sorted(rows, key=lambda row: str(row.get("business_date") or ""))


def _latest_rank(rows: list[dict[str, Any]], key: str) -> Any:
    for row in reversed(rows):
        raw_value = row.get(f"{key}_raw")
        if raw_value not in (None, ""):
            return raw_value
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _patch_flow_ranks(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    flow_item = _item(result, 4)
    if not flow_item:
        return

    rows = _daily_meituan_rows(sections)
    label_to_key = {
        "曝光人数同行排名": "exposure_rank",
        "浏览人数同行排名": "views_rank",
        "支付订单数同行排名": "paid_orders_rank",
        "支付转化率同行排名": "payment_conversion_rate_rank",
        "曝光-浏览转化率同行排名": "exposure_to_view_rate_rank",
        "浏览-支付转化率同行排名": "payment_conversion_rate_rank",
    }
    fields = {str(field.get("label") or ""): field for field in flow_item.get("fields") or []}
    for label, key in label_to_key.items():
        field = fields.get(label)
        if not field:
            continue
        value = _latest_rank(rows, key)
        if value in (None, ""):
            continue
        field["value"] = value
        field["origin"] = "数据库最新非空值"
        field["note"] = "按业务日期倒序取得最近一个非空 competitor_rank"

    flow_item["note"] = (
        "近30天人数和订单指标按 business_date 的日口径求和；"
        "同行排名取统计区间内最近一个非空 competitor_rank。"
    )


def _patch_scan_orders(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    scan_item = _item(result, 7)
    if not scan_item:
        return

    scan_item["source_table"] = "hotel_puyue.meituan_ota_scan_order_detail"
    scan_item["source_fields"] = ["COUNT(*)", "日期字段（存在时按诊断周期过滤）"]

    summary = next(
        (
            row
            for row in sections.get("ota_funnel") or []
            if str(row.get("period_type") or "") == "scan_order_summary"
        ),
        None,
    )
    if not summary:
        scan_item["note"] = (
            "已配置从 meituan_ota_scan_order_detail 统计总条数；"
            "当前未取得查询结果，请查看数据来源核验中的表查询状态。"
        )
        return

    count = _n(summary.get("scan_order_count"))
    date_column = summary.get("scan_order_date_column")
    period_start = summary.get("scan_order_period_start")
    period_end = summary.get("scan_order_period_end")
    scope = (
        f"DATE({date_column})：{period_start} 至 {period_end}"
        if date_column
        else "数据表全部记录"
    )
    scan_item["fields"] = [
        {
            "label": "月扫码订单",
            "value": int(count) if count is not None and float(count).is_integer() else count,
            "note": f"COUNT(*)；统计范围：{scope}",
            "origin": "数据库汇总",
        }
    ]
    scan_item["score_ratio"] = 0.0 if count == 0 else None
    scan_item["item_score"] = 0.0 if count == 0 else None
    scan_item["data_status"] = "zero" if count == 0 else "pending_rule"
    scan_item["note"] = (
        "月度扫码订单数直接统计 meituan_ota_scan_order_detail 的记录总条数；"
        "存在日期字段时按本次诊断周期过滤。正数对应的评分阈值尚未提供。"
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_flow_ranks(result, sections)
    _patch_scan_orders(result, sections)
    result["rule_version"] = "2026-07-14-v3"
    return result
