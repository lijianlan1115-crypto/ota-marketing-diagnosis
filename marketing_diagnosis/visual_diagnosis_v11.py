from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis_v10 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


_DAILY_PERIODS = {"日", "daily", "day", "当日"}
_RANK_FIELDS = {
    "曝光人数同行排名": "exposure_rank",
    "浏览人数同行排名": "views_rank",
    "支付订单数同行排名": "paid_orders_rank",
    "支付转化率同行排名": "payment_conversion_rate_rank",
    "曝光-浏览转化率同行排名": "exposure_to_view_rate_rank",
    "浏览-支付转化率同行排名": "payment_conversion_rate_rank",
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


def _daily_meituan_rows(sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in sections.get("ota_funnel") or []
        if str(row.get("platform") or "").strip().lower() == "meituan"
        and str(row.get("period_type") or "").strip().lower() in _DAILY_PERIODS
    ]
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("business_date") or "")[:10],
            str(row.get("snapshot_time") or ""),
        ),
    )


def _latest_rank_with_date(
    rows: list[dict[str, Any]],
    key: str,
) -> tuple[Any, str] | tuple[None, None]:
    """Return the latest non-empty raw rank and the business date it came from."""
    for row in reversed(rows):
        raw_value = row.get(f"{key}_raw")
        value = raw_value if raw_value not in (None, "") else row.get(key)
        if value in (None, ""):
            continue
        business_date = str(row.get("business_date") or "")[:10]
        return value, business_date or None
    return None, None


def _base_label(label: str) -> str:
    return label.split("（取值日：", 1)[0]


def _patch_flow_rank_dates(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 4)
    if not item:
        return

    rows = _daily_meituan_rows(sections)
    for field in item.get("fields") or []:
        original_label = _base_label(str(field.get("label") or ""))
        key = _RANK_FIELDS.get(original_label)
        if not key:
            continue

        rank_value, rank_date = _latest_rank_with_date(rows, key)
        if rank_value in (None, ""):
            continue

        field["value"] = rank_value
        field["rank_value"] = rank_value
        field["rank_date"] = rank_date
        field["origin"] = "统计区间内最新非空 competitor_rank"
        if rank_date:
            field["label"] = f"{original_label}（取值日：{rank_date}）"
            field["note"] = (
                f"按 business_date 倒序取得最近一条非空 competitor_rank；"
                f"本值取自 {rank_date}，排名不参与评分。"
            )
        else:
            field["label"] = original_label
            field["note"] = "取得最近一条非空 competitor_rank；排名不参与评分。"

    item["note"] = (
        "近30天人数和订单指标按 business_date 的日口径求和；"
        "同行排名不求和、不平均，取统计区间内最近一条非空 competitor_rank，"
        "并展示该排名对应的 business_date；排名仅展示，不参与评分。"
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_flow_rank_dates(result, sections)
    result["rule_version"] = "2026-07-15-v12-flow-rank-date"
    return result


__all__ = [
    "_latest_rank_with_date",
    "_patch_flow_rank_dates",
    "build_visual_diagnosis",
]
