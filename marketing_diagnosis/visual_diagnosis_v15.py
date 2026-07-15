from __future__ import annotations

from copy import deepcopy
from typing import Any

from marketing_diagnosis.visual_diagnosis_v13 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)
from marketing_diagnosis.visual_diagnosis_v14 import (
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

    original_item = _item(result, 4) or {}
    original_fields = deepcopy(list(original_item.get("fields") or []))
    original_note = str(original_item.get("note") or "")

    _patch_authoritative_flow(result, sections)
    _restore_flow_layout(result, original_fields, original_note)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-15-v15-flow-layout-fallback"
    return result


__all__ = ["build_visual_diagnosis"]
