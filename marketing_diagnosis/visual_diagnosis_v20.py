from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis_v19 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


FLOW_SOURCE_TABLE = "hotel_puyue.meituan_ota_flow_conversion_30d"
FLOW_SOURCE_FIELDS = [
    "exposure_uv",
    "peer_exposure_uv",
    "browse_uv",
    "peer_browse_uv",
    "exposure_to_browse_rate_pct",
    "peer_exposure_to_browse_rate_pct",
    "pay_order_count",
    "peer_pay_order_count",
    "browse_to_pay_rate_pct",
    "peer_browse_to_pay_rate_pct",
    "exposure_peer_rank",
    "browse_peer_rank",
    "pay_order_peer_rank",
    "exposure_to_browse_peer_rank",
    "browse_to_pay_peer_rank",
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


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    item = _item(result, 4)
    if item is not None:
        item["source_table"] = FLOW_SOURCE_TABLE
        item["source_tables"] = [FLOW_SOURCE_TABLE]
        item["source_fields"] = FLOW_SOURCE_FIELDS
        item["note"] = (
            "第04项只读取hotel_puyue.meituan_ota_flow_conversion_30d的最新近30天汇总记录；"
            "曝光、浏览、支付订单及竞争圈平均值直接读取对应字段；"
            "exposure_to_browse_rate_pct、peer_exposure_to_browse_rate_pct、"
            "browse_to_pay_rate_pct、peer_browse_to_pay_rate_pct按数据库百分比单位展示；"
            "5项同行排名分别读取exposure_peer_rank、browse_peer_rank、"
            "pay_order_peer_rank、exposure_to_browse_peer_rank和browse_to_pay_peer_rank，"
            "排名仅展示，不参与评分。"
        )
    result["rule_version"] = "2026-07-16-v24-exact-flow-rank-fields"
    return result


__all__ = [
    "FLOW_SOURCE_FIELDS",
    "FLOW_SOURCE_TABLE",
    "build_visual_diagnosis",
]
