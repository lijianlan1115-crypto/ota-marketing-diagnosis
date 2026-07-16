from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis_v14 import (
    _field,
    _latest_rank,
    _rank_field,
    _recalculate_totals,
    _safe_div,
    _score_ratio,
    _set_score,
)
from marketing_diagnosis.visual_diagnosis_v18 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


FLOW_SOURCE_TABLE = "meituan_ota_flow_conversion_30d"


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _source_row(sections: dict[str, list[dict[str, Any]]]) -> dict[str, Any] | None:
    rows = [
        row
        for row in sections.get("ota_funnel") or []
        if str(row.get("source_table") or row.get("__source_table") or "")
        == FLOW_SOURCE_TABLE
    ]
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            str(row.get("business_date") or ""),
            str(row.get("snapshot_time") or ""),
        ),
    )


def _patch_flow_conversion_30d(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 4)
    row = _source_row(sections)
    if item is None or row is None:
        return

    exposure = row.get("exposure")
    peer_exposure = row.get("peer_exposure")
    views = row.get("views")
    peer_views = row.get("peer_views")
    exposure_rate = row.get("exposure_to_view_rate")
    peer_exposure_rate = row.get("peer_exposure_to_view_rate")
    paid_orders = row.get("paid_orders")
    peer_paid_orders = row.get("peer_paid_orders")
    payment_rate = row.get("payment_conversion_rate")
    peer_payment_rate = row.get("peer_payment_conversion_rate")

    exposure_rank, exposure_rank_date = _latest_rank([row], "exposure")
    views_rank, views_rank_date = _latest_rank([row], "views")
    exposure_rate_rank, exposure_rate_rank_date = _latest_rank(
        [row], "exposure_to_view_rate"
    )
    order_rank, order_rank_date = _latest_rank([row], "paid_orders")
    payment_rate_rank, payment_rate_rank_date = _latest_rank(
        [row], "payment_conversion_rate"
    )

    item["fields"] = [
        _field("曝光人数", exposure, "直接读取 exposure_uv", FLOW_SOURCE_TABLE),
        _field("曝光人数同行均值", peer_exposure, "直接读取 peer_exposure_uv", FLOW_SOURCE_TABLE),
        _rank_field("曝光人数同行排名", exposure_rank, exposure_rank_date),
        _field("浏览人数", views, "直接读取 browse_uv", FLOW_SOURCE_TABLE),
        _field("浏览人数同行均值", peer_views, "直接读取 peer_browse_uv", FLOW_SOURCE_TABLE),
        _rank_field("浏览人数同行排名", views_rank, views_rank_date),
        _field(
            "曝光-浏览转化率",
            exposure_rate,
            "直接读取 exposure_to_browse_rate_pct（数据库百分比已转为比例）",
            FLOW_SOURCE_TABLE,
        ),
        _field(
            "曝光-浏览转化率同行均值",
            peer_exposure_rate,
            "直接读取 peer_exposure_to_browse_rate_pct（数据库百分比已转为比例）",
            FLOW_SOURCE_TABLE,
        ),
        _rank_field(
            "曝光-浏览转化率同行排名",
            exposure_rate_rank,
            exposure_rate_rank_date,
        ),
        _field("支付订单数", paid_orders, "直接读取 pay_order_count", FLOW_SOURCE_TABLE),
        _field(
            "支付订单数同行均值",
            peer_paid_orders,
            "直接读取 peer_pay_order_count",
            FLOW_SOURCE_TABLE,
        ),
        _rank_field("支付订单数同行排名", order_rank, order_rank_date),
        _field(
            "浏览-支付转化率",
            payment_rate,
            "直接读取 browse_to_pay_rate_pct（数据库百分比已转为比例）",
            FLOW_SOURCE_TABLE,
        ),
        _field(
            "浏览-支付转化率同行均值",
            peer_payment_rate,
            "直接读取 peer_browse_to_pay_rate_pct（数据库百分比已转为比例）",
            FLOW_SOURCE_TABLE,
        ),
        _rank_field(
            "浏览-支付转化率同行排名",
            payment_rate_rank,
            payment_rate_rank_date,
        ),
    ]

    scoring_values = (
        (exposure, peer_exposure),
        (views, peer_views),
        (exposure_rate, peer_exposure_rate),
        (payment_rate, peer_payment_rate),
    )
    ratios = [_score_ratio(_safe_div(actual, peer)) for actual, peer in scoring_values]
    overall_ratio = sum(ratios) / 4
    _set_score(item, overall_ratio, "success" if overall_ratio > 0 else "zero")

    item["daily_records"] = [dict(row)]
    item["records"] = []
    item["source_tables"] = [FLOW_SOURCE_TABLE]
    item["note"] = (
        "第04项统一读取 hotel_puyue.meituan_ota_flow_conversion_30d 的最新近30天汇总记录；"
        "曝光、浏览、订单及两项转化率均直接使用指定字段，不再从旧的 FLOW_* 日明细重新汇总。"
        "同行排名仅在该表存在对应排名字段时展示，不参与评分。"
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_flow_conversion_30d(result, sections)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-16-v22-flow-conversion-30d"
    return result


__all__ = [
    "FLOW_SOURCE_TABLE",
    "_patch_flow_conversion_30d",
    "build_visual_diagnosis",
]
