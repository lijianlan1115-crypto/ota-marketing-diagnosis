from __future__ import annotations

import re
from typing import Any


_LANDMARK_ENDINGS = tuple(
    sorted(
        (
            "妇幼保健院",
            "购物中心",
            "商业广场",
            "火车站",
            "高铁站",
            "地铁站",
            "客运站",
            "公交站",
            "医学院",
            "风景区",
            "步行街",
            "保健院",
            "医院",
            "机场",
            "车站",
            "公园",
            "景区",
            "古镇",
            "大学",
            "学院",
            "学校",
            "中学",
            "小学",
            "商圈",
            "广场",
            "万达",
            "吾悦",
            "站",
        ),
        key=len,
        reverse=True,
    )
)
_LANDMARK_PATTERN = re.compile("|".join(re.escape(value) for value in _LANDMARK_ENDINGS))


def _text(value: Any) -> str:
    return str(value or "").strip()


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=lambda row: str(row.get("snapshot_time") or row.get("period_end_date") or ""))


def _store_suffix(name: str) -> str:
    """Return the final non-empty Chinese or ASCII parenthesized name suffix."""

    matches = re.findall(r"[（(]([^（）()]*)[）)]", name)
    for value in reversed(matches):
        suffix = value.strip()
        if suffix:
            return suffix
    return ""


def _landmark_hits(name: str, store_suffix: str) -> list[str]:
    """Extract complete location phrases instead of isolated keyword fragments."""

    source = (store_suffix or name).strip()
    source = re.sub(r"(?:旗舰店|分店|直营店|中心店|酒店|店)$", "", source)
    hits: list[str] = []
    start = 0
    for match in _LANDMARK_PATTERN.finditer(source):
        phrase = source[start : match.end()]
        phrase = re.sub(r"^[\s·•,，、/|丨\-—_]+", "", phrase).strip()
        if len(phrase) >= 2:
            hits.append(phrase)
        start = match.end()
    return list(dict.fromkeys(hits))


def build_page_entry_item(sections: dict[str, Any]) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in sections.get("ctrip_promotion_performance_30d") or []
        if isinstance(row, dict)
    ]
    row = _latest(rows)
    name = _text(row.get("hotel_name")) if row else ""
    if not name:
        return {
            "standard_item_id": 10,
            "participates_in_score": True,
            "item_score": None,
            "data_status": "missing",
            "source": "ctrip_ota_promotion_performance_30d.hotel_name",
            "fields_complete": True,
            "fields": [],
            "note": "等待携程酒店名称快照接入。",
        }

    store_suffix = _store_suffix(name)
    landmark_hits = _landmark_hits(name, store_suffix)
    score = float(bool(store_suffix)) + float(bool(landmark_hits))
    fields = [
        {"label": "酒店展示名称", "value": name},
        {
            "label": "门店后缀",
            "value": store_suffix or "未识别",
            "note": "直接取酒店名称括号内的完整内容",
        },
        {
            "label": "热门商圈词命中",
            "value": "、".join(landmark_hits) or "未命中",
            "note": "从门店后缀中识别完整商圈、交通、医院、景区、学校词组",
        },
        {
            "label": "列表页推荐词 / 标签 / 卖点",
            "value": "待接入",
            "note": "当前数据源仅提供酒店名称，暂无法判断",
        },
    ]
    return {
        "standard_item_id": 10,
        "participates_in_score": True,
        "item_score": score,
        "data_status": "partial",
        "source": "ctrip_ota_promotion_performance_30d.hotel_name",
        "fields_complete": True,
        "fields": fields,
        "note": "酒店展示名称保持原值；门店后缀取名称括号内容；热门商圈词按完整地点词组识别。",
    }


__all__ = ["build_page_entry_item"]