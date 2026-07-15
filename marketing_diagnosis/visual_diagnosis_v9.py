from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v8 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


# Conservative, explicit room-selling-point vocabulary used by the current hotel
# products. The handbook requires a selling-point expression but does not provide
# a central dictionary, so only clear product features are accepted here.
_ROOM_SELLING_POINT_TERMS = (
    "电竞",
    "亲子",
    "麻将",
    "上下铺",
    "套房",
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


def _field(item: dict[str, Any], label: str) -> dict[str, Any] | None:
    return next(
        (
            field
            for field in item.get("fields") or []
            if str(field.get("label") or "") == label
        ),
        None,
    )


def _set_score(
    item: dict[str, Any],
    ratio: float | None,
    status: str,
) -> None:
    item["score_ratio"] = ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 0) * ratio, 2)
        if ratio is not None
        else None
    )
    item["data_status"] = status


def _patch_scan_order_score(result: dict[str, Any]) -> None:
    item = _item(result, 7)
    if not item:
        return

    count_field = _field(item, "月扫码订单")
    count = _n(count_field.get("value") if count_field else None)
    if count is None:
        _set_score(item, None, "missing")
        return

    if count > 120:
        _set_score(item, 1.0, "success")
        conclusion = "月扫码订单大于120单，得满分8分。"
    elif count == 60:
        _set_score(item, 0.5, "success")
        conclusion = "月扫码订单等于60单，得4分。"
    elif count == 0:
        _set_score(item, 0.0, "zero")
        conclusion = "月扫码订单为0，得0分。"
    else:
        # The handbook leaves 1–59, 61–120 and exactly 120 undefined.
        _set_score(item, None, "pending_rule")
        conclusion = "当前订单量位于手册未定义区间，保持待确认。"

    item["note"] = (
        "严格采用手册阈值：月扫码订单>120得8分；=60得4分；=0得0分。"
        "1–59、61–120及恰好120单的评分未定义。" + conclusion
    )


def _room_has_selling_point(name: str) -> bool:
    return any(term in name for term in _ROOM_SELLING_POINT_TERMS)


def _patch_room_name_score(result: dict[str, Any]) -> None:
    item = _item(result, 11)
    if not item:
        return

    fields = list(item.get("fields") or [])
    if not fields:
        _set_score(item, None, "missing")
        return

    checks: list[tuple[str, int, bool]] = []
    for field in fields:
        name = str(field.get("label") or "").strip()
        length_value = _n(field.get("value"))
        length = int(length_value) if length_value is not None else len(name)
        hit = _room_has_selling_point(name)
        checks.append((name, length, hit))
        field["note"] = (
            f"字符数：{length}；卖点表达："
            + ("已命中" if hit else "未命中")
        )
        field["origin"] = "名称长度与卖点词检查"

    if any(length < 5 for _, length, _ in checks):
        _set_score(item, 0.0, "zero")
        conclusion = "存在少于5个字的房型名称，得0分。"
    elif any(length == 5 for _, length, _ in checks):
        _set_score(item, None, "pending_rule")
        conclusion = "存在恰好5个字的房型名称，手册未定义该边界。"
    elif all(hit for _, _, hit in checks):
        _set_score(item, 1.0, "success")
        conclusion = "全部房型名称均大于5个字且具有明确卖点表达，得满分4分。"
    else:
        _set_score(item, 0.0, "zero")
        conclusion = "存在未体现明确卖点表达的房型名称，未满足满分条件，得0分。"

    item["note"] = (
        "严格采用手册二值条件：房型名称>5个字且满足卖点表达得4分；"
        "房型名称<5个字得0分；恰好5个字保持待确认。"
        + conclusion
    )


def _patch_review_score(result: dict[str, Any]) -> None:
    item = _item(result, 13)
    if not item:
        return

    meituan = _n((_field(item, "美团评分") or {}).get("value"))
    dianping = _n((_field(item, "大众点评评分") or {}).get("value"))

    # The handbook states that Dianping is a sub-field and does not define a
    # cross-platform average. Therefore Meituan is the primary score; Dianping is
    # used only when the Meituan score is missing.
    score = meituan if meituan is not None else dianping
    source = "美团评分" if meituan is not None else "大众点评评分（美团缺失时备用）"
    if score is None:
        _set_score(item, None, "missing")
        item["note"] = "美团和大众点评均未取得评分，不能评分。"
        return

    ratio = 1.0 if score > 4.9 else 0.8 if score >= 4.7 else 0.0
    _set_score(item, ratio, "success" if ratio > 0 else "zero")
    item["note"] = (
        f"按{source}计分。严格采用手册阈值：点评分>4.9得10分；"
        "4.7≤点评分≤4.9得8分；点评分<4.7得0分。"
        "大众点评作为子字段展示，不采用未定义的平均或加权公式。"
    )


def _patch_joined_rights_score(result: dict[str, Any]) -> None:
    item = _item(result, 14)
    if not item:
        return

    count = _n((_field(item, "已报名权益数量") or {}).get("value"))
    if count is None:
        _set_score(item, None, "missing")
        return

    # Apply the handbook's three-tier total-table rule. It is the only complete
    # rule that defines the 3–5 range.
    if count > 5:
        _set_score(item, 1.0, "success")
        conclusion = "已报名权益大于5项，得4分。"
    elif count >= 3:
        _set_score(item, 0.6, "success")
        conclusion = "已报名权益为3–5项，得2.4分。"
    else:
        _set_score(item, 0.0, "zero")
        conclusion = "已报名权益少于3项，得0分。"

    item["note"] = (
        "采用规则手册总表三档：已报名权益>5项得4分；3–5项得2.4分；"
        "<3项得0分。" + conclusion
    )


def _recalculate_totals(result: dict[str, Any]) -> None:
    items = list(result.get("items") or [])
    raw_score = round(
        sum(float(item.get("item_score")) for item in items if item.get("item_score") is not None),
        2,
    )
    connected_base = round(
        sum(
            float(item.get("base_score") or 0)
            for item in items
            if item.get("participates_in_score") and item.get("item_score") is not None
        ),
        2,
    )
    result["raw_score"] = raw_score
    result["connected_base_score"] = connected_base
    result["normalized_score"] = (
        round(raw_score / connected_base * 100, 2)
        if connected_base
        else None
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_scan_order_score(result)
    _patch_room_name_score(result)
    _patch_review_score(result)
    _patch_joined_rights_score(result)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-15-v10-handbook-scores-7-11-13-14"
    return result


__all__ = [
    "_patch_joined_rights_score",
    "_patch_review_score",
    "_patch_room_name_score",
    "_patch_scan_order_score",
    "_recalculate_totals",
    "build_visual_diagnosis",
]
