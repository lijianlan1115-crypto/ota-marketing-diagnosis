from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v9 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


# Conservative location / landmark vocabulary for validating an existing hotel-name
# suffix. The business rule requires an effective business-district or landmark
# suffix; generic trailing words such as “店” alone are not enough.
_LOCATION_TERMS = (
    "花溪公园",
    "贵州大学",
    "花溪大学城",
    "青岩古镇",
    "十里河滩",
    "贵阳北站",
    "贵阳站",
    "龙洞堡机场",
    "会展城",
    "喷水池",
    "大十字",
    "小十字",
    "花果园",
    "公园",
    "大学",
    "学院",
    "机场",
    "高铁站",
    "火车站",
    "地铁",
    "广场",
    "商圈",
    "景区",
    "古镇",
    "会展",
    "步行街",
)

_ROOM_SELLING_POINT_TERMS = (
    "电竞",
    "亲子",
    "麻将",
    "棋牌",
    "上下铺",
    "套房",
    "影音",
    "投影",
    "浴缸",
    "景观",
    "家庭",
    "商务",
    "榻榻米",
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


def _set_score(item: dict[str, Any], ratio: float | None, status: str) -> None:
    item["score_ratio"] = ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 0) * ratio, 2)
        if ratio is not None
        else None
    )
    item["data_status"] = status


def _fraction(value: Any) -> float | None:
    number = _n(value)
    if number is None:
        return None
    return number / 100 if abs(number) > 1 else number


def _patch_room_efficiency_score(result: dict[str, Any]) -> None:
    item = _item(result, 2)
    if not item:
        return

    low_ratio = _fraction((_field(item, "低效房型占比") or {}).get("value"))
    if low_ratio is None:
        _set_score(item, None, "missing")
        item["note"] = "未取得低效房型占比，无法按手册评分。"
        return

    if low_ratio < 0.10:
        ratio, conclusion = 1.0, "低效房型占比低于10%，得满分8分。"
    elif low_ratio <= 0.30:
        ratio, conclusion = 0.6, "低效房型占比为10%–30%，得4.8分。"
    else:
        ratio, conclusion = 0.0, "低效房型占比高于30%，得0分。"

    _set_score(item, ratio, "success" if ratio > 0 else "zero")
    item["note"] = (
        "严格采用手册阈值：低效房型为近30天出租率低于60%的房型；"
        "低效房型占比<10%得8分，10%–30%得4.8分，>30%得0分。"
        + conclusion
    )


def _rate_value(label: str, value: Any) -> float | None:
    number = _n(value)
    if number is None:
        return None
    if "转化率" in label and abs(number) > 1:
        return number / 100
    return number


def _ratio_score(value: float) -> float:
    if value > 2:
        return 1.0
    if value >= 1.5:
        return 0.8
    if value >= 1:
        return 0.6
    return 0.0


def _flow_pair(item: dict[str, Any], label: str, peer_label: str) -> tuple[float, float] | None:
    actual = _rate_value(label, (_field(item, label) or {}).get("value"))
    peer = _rate_value(peer_label, (_field(item, peer_label) or {}).get("value"))
    if actual is None or peer in (None, 0):
        return None
    return actual, peer


def _patch_flow_score(result: dict[str, Any]) -> None:
    item = _item(result, 4)
    if not item:
        return

    definitions = (
        ("曝光人数", "曝光人数同行均值"),
        ("浏览人数", "浏览人数同行均值"),
        ("曝光-浏览转化率", "曝光-浏览转化率同行均值"),
        ("浏览-支付转化率", "浏览-支付转化率同行均值"),
    )

    sub_scores: list[float] = []
    details: list[str] = []
    for label, peer_label in definitions:
        pair = _flow_pair(item, label, peer_label)
        if pair is None and label == "浏览-支付转化率":
            # Some source versions expose the same second-conversion metric as
            # “支付转化率”. Use it only as an explicit field alias.
            pair = _flow_pair(item, "支付转化率", "支付转化率同行均值")
        if pair is None:
            _set_score(item, None, "missing")
            item["note"] = f"{label}或其同行均值缺失/为0，四项等权评分无法完成。"
            return
        actual, peer = pair
        comparison = actual / peer
        score = _ratio_score(comparison)
        sub_scores.append(score)
        details.append(f"{label}÷同行均值={comparison:.2f}，子项比例{score:.0%}")

    overall_ratio = sum(sub_scores) / 4
    _set_score(item, overall_ratio, "success" if overall_ratio > 0 else "zero")
    item["note"] = (
        "严格采用手册四项等权规则：曝光人数、浏览人数、曝光-浏览转化率、"
        "浏览-支付转化率分别与同行均值相除；比例>2得100%，1.5–2得80%，"
        "1–1.5得60%，<1得0%；四项各占25%。"
        + "；".join(details)
    )


def _detected_location_term(suffix: str) -> str | None:
    return next((term for term in _LOCATION_TERMS if term in suffix), None)


def _patch_page_entry_score(result: dict[str, Any]) -> None:
    item = _item(result, 10)
    if not item:
        return

    name = str((_field(item, "酒店展示名称") or {}).get("value") or "").strip()
    suffix_field = _field(item, "检测到的后缀")
    hotword_field = _field(item, "热门商圈词命中")
    suffix = str((suffix_field or {}).get("value") or "").strip()
    existing_hotword = str((hotword_field or {}).get("value") or "").strip()

    if not name:
        _set_score(item, None, "missing")
        item["note"] = "未取得酒店展示名称，无法判断页面后缀。"
        return

    if not suffix:
        _set_score(item, 0.0, "zero")
        item["note"] = "酒店展示名称未添加后缀，按手册得0分。"
        return

    matched = existing_hotword or _detected_location_term(suffix)
    if matched:
        if hotword_field is not None:
            hotword_field["value"] = matched
            hotword_field["origin"] = "后缀商圈/地标词检查"
            hotword_field["note"] = f"在后缀“{suffix}”中命中“{matched}”"
        _set_score(item, 1.0, "success")
        item["note"] = (
            f"酒店名称已添加后缀“{suffix}”，并命中商圈/地标词“{matched}”，"
            "严格按手册得满分3分。"
        )
        return

    _set_score(item, 0.0, "zero")
    item["note"] = (
        f"酒店名称虽有后缀“{suffix}”，但未命中已配置的商圈/地标词，"
        "未满足满分条件，得0分。"
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

    failed_short: list[str] = []
    failed_selling_point: list[str] = []
    boundary_names: list[str] = []
    for field in fields:
        name = str(field.get("label") or "").strip()
        length_value = _n(field.get("value"))
        length = int(length_value) if length_value is not None else len(name)
        matched = next((term for term in _ROOM_SELLING_POINT_TERMS if term in name), None)
        field["note"] = f"字符数：{length}；卖点词：{matched or '未命中'}"
        field["origin"] = "名称长度与卖点词检查"
        if length < 5:
            failed_short.append(name)
        elif length == 5:
            boundary_names.append(name)
        elif not matched:
            failed_selling_point.append(name)

    if failed_short:
        _set_score(item, 0.0, "zero")
        conclusion = "少于5字：" + "、".join(failed_short)
    elif boundary_names:
        _set_score(item, None, "pending_rule")
        conclusion = "恰好5字边界待确认：" + "、".join(boundary_names)
    elif failed_selling_point:
        _set_score(item, 0.0, "zero")
        conclusion = "未命中卖点词：" + "、".join(failed_selling_point)
    else:
        _set_score(item, 1.0, "success")
        conclusion = "全部在售房型名称均大于5字并命中明确卖点词，得满分4分。"

    item["note"] = (
        "严格采用手册规则：房型名称>5个字且有卖点表达得4分；"
        "<5个字得0分；恰好5个字保持待确认。" + conclusion
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
    _patch_room_efficiency_score(result)
    _patch_flow_score(result)
    _patch_page_entry_score(result)
    _patch_room_name_score(result)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-15-v11-handbook-scores-2-4-10-11"
    return result


__all__ = [
    "_patch_flow_score",
    "_patch_page_entry_score",
    "_patch_room_efficiency_score",
    "_patch_room_name_score",
    "_ratio_score",
    "build_visual_diagnosis",
]
