from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v2 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


_DAILY_PERIODS = {"日", "daily", "day", "当日"}
_MEITUAN_ALIASES = {"meituan", "美团", "美团酒店"}
_DIANPING_ALIASES = {"dianping", "大众点评", "点评", "大众点评网"}


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


def _is_meituan_product(row: dict[str, Any]) -> bool:
    platform = str(row.get("platform") or row.get("channel_source") or "").strip().lower()
    source_table = str(row.get("source_table") or row.get("__source_table") or "").strip().lower()
    return platform in _MEITUAN_ALIASES or source_table.endswith("meituan_ota_goods_price_mapping")


def _latest_meituan_products(sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = [row for row in sections.get("products") or [] if _is_meituan_product(row)]
    dated = [
        (str(row.get("business_date") or row.get("snapshot_time") or "")[:19], row)
        for row in rows
        if str(row.get("business_date") or row.get("snapshot_time") or "")
    ]
    if not dated:
        return rows
    latest_stamp = max(stamp for stamp, _ in dated)
    latest_day = latest_stamp[:10]
    return [
        row
        for row in rows
        if str(row.get("business_date") or row.get("snapshot_time") or "")[:10] == latest_day
    ]


def _patch_room_names(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    room_item = _item(result, 11)
    if not room_item:
        return

    rows = _latest_meituan_products(sections)
    room_names = sorted(
        {
            str(row.get("room_type_name") or "").strip()
            for row in rows
            if str(row.get("room_type_name") or "").strip()
        }
    )
    room_item["fields"] = [
        {
            "label": name,
            "value": len(name),
            "note": "room_type_name 字符数",
            "origin": "美团商品表最新快照去重",
        }
        for name in room_names
    ]
    room_item["source_table"] = "hotel_puyue.meituan_ota_goods_price_mapping"
    room_item["source_fields"] = ["room_type_name"]

    if not room_names:
        room_item["data_status"] = "missing"
        room_item["score_ratio"] = None
        room_item["item_score"] = None
    elif any(len(name) < 5 for name in room_names):
        room_item["data_status"] = "success"
        room_item["score_ratio"] = 0.0
        room_item["item_score"] = 0.0
    else:
        room_item["data_status"] = "pending_rule"
        room_item["score_ratio"] = None
        room_item["item_score"] = None

    room_item["note"] = (
        "只读取 hotel_puyue.meituan_ota_goods_price_mapping 最新快照中的 "
        "room_type_name，并按房型名称去重；不混入携程或其他平台房型。"
    )


def _review_platform(row: dict[str, Any]) -> str:
    values = (
        row.get("review_platform"),
        row.get("platform"),
        row.get("channel_source"),
        row.get("source_platform"),
    )
    for value in values:
        text = str(value or "").strip().lower()
        if not text:
            continue
        if text in _DIANPING_ALIASES or "大众点评" in text or "dianping" in text:
            return "dianping"
        if text in _MEITUAN_ALIASES or "美团" in text or "meituan" in text:
            return "meituan"
    return ""


def _latest_review_row(rows: list[dict[str, Any]], platform: str) -> dict[str, Any]:
    matches = [row for row in rows if _review_platform(row) == platform]
    if not matches:
        return {}
    return max(
        enumerate(matches),
        key=lambda pair: (
            str(pair[1].get("snapshot_time") or ""),
            str(pair[1].get("business_date") or ""),
            str(pair[1].get("period_month") or ""),
            str(pair[1].get("updated_at") or ""),
            pair[0],
        ),
    )[1]


def _first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _patch_review_unreplied_counts(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    review_item = _item(result, 13)
    if not review_item:
        return

    rows = sections.get("review_overviews") or []
    meituan = _latest_review_row(rows, "meituan")
    dianping = _latest_review_row(rows, "dianping")

    review_item["fields"] = [
        {
            "label": "美团评分",
            "value": _first_present(meituan, "rating_avg", "review_score"),
            "note": "美团评价概览",
            "origin": "数据库原值",
        },
        {
            "label": "美团点评条数",
            "value": _first_present(meituan, "review_count", "total_review_count"),
            "note": "total_review_count",
            "origin": "数据库原值",
        },
        {
            "label": "美团未回复点评数",
            "value": meituan.get("unreplied_review_count"),
            "note": "unreplied_review_count",
            "origin": "数据库原值",
        },
        {
            "label": "大众点评评分",
            "value": _first_present(dianping, "rating_avg", "review_score"),
            "note": "大众点评评价概览",
            "origin": "数据库原值",
        },
        {
            "label": "大众点评未回复点评数",
            "value": dianping.get("unreplied_review_count"),
            "note": "unreplied_review_count",
            "origin": "数据库原值",
        },
        {
            "label": "大众点评点评条数",
            "value": _first_present(dianping, "review_count", "total_review_count"),
            "note": "total_review_count",
            "origin": "数据库原值",
        },
    ]
    review_item["source_table"] = "hotel_puyue.meituan_ota_review_overview"
    review_item["source_fields"] = [
        "review_platform",
        "review_score",
        "total_review_count",
        "unreplied_review_count",
    ]
    review_item["data_status"] = "pending_rule" if meituan or dianping else "missing"
    review_item["score_ratio"] = None
    review_item["item_score"] = None
    review_item["note"] = (
        "美团和大众点评分别按 review_platform 识别；两个平台的未回复点评数"
        "均只读取 unreplied_review_count，不使用其他评论数字段替代。"
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_flow_ranks(result, sections)
    _patch_scan_orders(result, sections)
    _patch_room_names(result, sections)
    _patch_review_unreplied_counts(result, sections)
    result["rule_version"] = "2026-07-14-v4"
    return result
