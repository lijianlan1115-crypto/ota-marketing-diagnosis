from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v11 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


_DAILY_PERIODS = {"日", "daily", "day", "当日"}
_ROOM_SELLING_POINT_TERMS = (
    "电竞", "亲子", "麻将", "棋牌", "上下铺", "套房", "影音", "投影",
    "浴缸", "景观", "家庭", "商务", "榻榻米", "单人", "双床", "大床",
    "三人", "四人", "五人",
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
            if str(field.get("label") or "").split("（取值日：", 1)[0] == label
        ),
        None,
    )


def _set_field(item: dict[str, Any], label: str, value: Any, note: str) -> None:
    field = _field(item, label)
    if field is None:
        item.setdefault("fields", []).append(
            {"label": label, "value": value, "note": note, "origin": "规则计算"}
        )
        return
    field["value"] = value
    field["note"] = note
    field["origin"] = "规则计算"


def _set_score(item: dict[str, Any], ratio: float | None, status: str) -> None:
    item["score_ratio"] = ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 0) * ratio, 2)
        if ratio is not None
        else None
    )
    item["data_status"] = status


def _score_ratio(comparison: float | None) -> float:
    if comparison is None:
        return 0.0
    if comparison > 2:
        return 1.0
    if comparison >= 1.5:
        return 0.8
    if comparison >= 1:
        return 0.6
    return 0.0


def _daily_meituan_rows(sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    selected: dict[str, tuple[tuple[str, int], dict[str, Any]]] = {}
    for index, row in enumerate(sections.get("ota_funnel") or []):
        if str(row.get("platform") or "").strip().lower() != "meituan":
            continue
        period = str(row.get("period_type") or "").strip().lower()
        if period not in _DAILY_PERIODS:
            continue
        day = str(row.get("business_date") or "")[:10]
        if not day:
            continue
        key = (str(row.get("snapshot_time") or ""), index)
        current = selected.get(day)
        if current is None or key >= current[0]:
            selected[day] = (key, row)
    return [selected[day][1] for day in sorted(selected)]


def _sum(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [_n(row.get(key)) for row in rows]
    clean = [value for value in values if value is not None]
    return sum(clean) if clean else None


def _average(rows: list[dict[str, Any]], *keys: str) -> float | None:
    values: list[float] = []
    for row in rows:
        value = next((_n(row.get(key)) for key in keys if _n(row.get(key)) is not None), None)
        if value is not None:
            values.append(value)
    return sum(values) / len(values) if values else None


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _patch_flow_score(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 4)
    if not item:
        return

    rows = _daily_meituan_rows(sections)
    if not rows:
        _set_score(item, None, "missing")
        item["note"] = "统计周期内未取得美团日流量数据，无法计算本项得分。"
        return

    exposure = _sum(rows, "exposure")
    peer_exposure = _sum(rows, "peer_exposure")
    views = _sum(rows, "views")
    peer_views = _sum(rows, "peer_views")
    paid_orders = _sum(rows, "paid_orders")
    peer_paid_orders = _sum(rows, "peer_paid_orders")

    exposure_to_view = _safe_div(views, exposure)
    if exposure_to_view is None:
        exposure_to_view = _average(rows, "exposure_to_view_rate")
    peer_exposure_to_view = _safe_div(peer_views, peer_exposure)
    if peer_exposure_to_view is None:
        peer_exposure_to_view = _average(rows, "peer_exposure_to_view_rate")

    payment_conversion = _safe_div(paid_orders, views)
    if payment_conversion is None:
        payment_conversion = _average(rows, "payment_conversion_rate")
    peer_payment_conversion = _safe_div(peer_paid_orders, peer_views)
    if peer_payment_conversion is None:
        peer_payment_conversion = _average(
            rows,
            "peer_payment_conversion_rate",
            "peer_avg_conversion_rate",
        )

    values = (
        ("曝光人数", exposure, peer_exposure),
        ("浏览人数", views, peer_views),
        ("曝光-浏览转化率", exposure_to_view, peer_exposure_to_view),
        ("浏览-支付转化率", payment_conversion, peer_payment_conversion),
    )

    ratios: list[float] = []
    details: list[str] = []
    for label, actual, peer in values:
        comparison = _safe_div(actual, peer)
        sub_ratio = _score_ratio(comparison)
        ratios.append(sub_ratio)
        if comparison is None:
            details.append(f"{label}缺少酒店值或同行均值，该子项按0%计")
        else:
            details.append(f"{label}÷同行均值={comparison:.2f}，子项评分比例{sub_ratio:.0%}")

    overall_ratio = sum(ratios) / 4
    _set_score(item, overall_ratio, "success" if overall_ratio > 0 else "zero")

    _set_field(item, "曝光人数", exposure, "统计周期内日曝光人数求和")
    _set_field(item, "曝光人数同行均值", peer_exposure, "统计周期内日同行均值求和")
    _set_field(item, "浏览人数", views, "统计周期内日浏览人数求和")
    _set_field(item, "浏览人数同行均值", peer_views, "统计周期内日同行均值求和")
    _set_field(item, "曝光-浏览转化率", exposure_to_view, "浏览人数÷曝光人数")
    _set_field(item, "曝光-浏览转化率同行均值", peer_exposure_to_view, "同行浏览人数÷同行曝光人数")
    _set_field(item, "浏览-支付转化率", payment_conversion, "支付订单数÷浏览人数")
    _set_field(item, "浏览-支付转化率同行均值", peer_payment_conversion, "同行支付订单数÷同行浏览人数")

    item["note"] = (
        "严格按四项各25%计算。单项酒店值÷同行均值：>2得100%，1.5–2得80%，"
        "1–1.5得60%，<1得0%；已有流量数据但某个子项缺失时，该子项按0%计，"
        "不再使整项停留在待计算。" + "；".join(details)
    )


def _patch_promotion_score(result: dict[str, Any]) -> None:
    item = _item(result, 9)
    if not item:
        return

    spend = _n((_field(item, "近30天推广投入") or {}).get("value"))
    revenue = _n((_field(item, "本月美团EBK订单金额") or {}).get("value"))
    if spend is not None:
        spend = abs(spend)
    roi = _safe_div(revenue, spend)
    _set_field(item, "近30天推广投入", spend, "推广通支出绝对值合计")
    _set_field(item, "ROI", roi, "本月美团EBK订单金额÷近30天推广投入")

    if spend is None:
        _set_score(item, None, "missing")
        item["note"] = "未取得推广投入，无法评分。"
    elif spend <= 1000:
        _set_score(item, 0.0, "zero")
        item["note"] = "月推广投入不超过1000元，严格按手册记0分，不再显示待计算。"
    elif roi is None:
        _set_score(item, None, "missing")
        item["note"] = "推广投入超过1000元，但未取得订单金额，无法计算ROI。"
    else:
        ratio = 1.0 if roi > 10 else 0.6 if roi >= 5 else 0.0
        _set_score(item, ratio, "success" if ratio > 0 else "zero")
        item["note"] = (
            "投入超过1000元后按ROI评分：ROI>10得100%，5≤ROI≤10得60%，ROI<5得0%。"
        )


def _patch_room_name_score(result: dict[str, Any]) -> None:
    item = _item(result, 11)
    if not item:
        return
    fields = list(item.get("fields") or [])
    if not fields:
        _set_score(item, None, "missing")
        item["note"] = "未取得在售房型名称，无法评分。"
        return

    failures: list[str] = []
    for field in fields:
        name = str(field.get("label") or "").strip()
        length_value = _n(field.get("value"))
        length = int(length_value) if length_value is not None else len(name)
        selling_point = next((term for term in _ROOM_SELLING_POINT_TERMS if term in name), None)
        field["note"] = f"字符数：{length}；卖点词：{selling_point or '未命中'}"
        field["origin"] = "名称长度与卖点词检查"
        if length <= 5 or not selling_point:
            failures.append(name)

    if failures:
        _set_score(item, 0.0, "zero")
        item["note"] = (
            "严格按手册：房型名称必须大于5个字并满足卖点表达；"
            "以下房型未满足，得0分：" + "、".join(failures)
        )
    else:
        _set_score(item, 1.0, "success")
        item["note"] = "全部在售房型名称均大于5个字且包含明确卖点，得满分4分。"


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
    result["normalized_score"] = round(raw_score / connected_base * 100, 2) if connected_base else None


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_flow_score(result, sections)
    _patch_promotion_score(result)
    _patch_room_name_score(result)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-15-v13-final-score-4-9-11"
    return result


__all__ = [
    "_patch_flow_score",
    "_patch_promotion_score",
    "_patch_room_name_score",
    "build_visual_diagnosis",
]
