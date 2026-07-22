from __future__ import annotations

import re
from typing import Any


_STORE_SUFFIXES = (
    "旗舰店", "分店", "直营店", "中心店", "店", "馆", "公寓", "民宿", "客栈", "驿站",
)
_LANDMARK_KEYWORDS = (
    "商圈", "步行街", "广场", "大道", "地铁", "车站", "火车站", "高铁", "机场",
    "公园", "景区", "医院", "妇幼", "学校", "大学", "学院", "万达", "吾悦",
)
_ENTRY_KEYWORDS = (
    "地铁", "站", "机场", "高铁", "火车站", "客运站", "公交", "医院", "妇幼", "医学院", "诊所",
    "景区", "公园", "风景区", "古镇", "大学", "学院", "学校", "中学", "小学", "商圈", "步行街",
    "万达", "吾悦",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=lambda row: str(row.get("snapshot_time") or row.get("period_end_date") or ""))


def _clean_name(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+$", "", name)


def _store_suffix(name: str) -> str:
    """Return the final non-empty Chinese or ASCII parenthesized name suffix."""

    matches = re.findall(r"[（(]([^（）()]*)[）)]", name)
    for value in reversed(matches):
        suffix = value.strip()
        if suffix:
            return suffix
    return ""


def _first_name_hits(name: str) -> list[str]:
    clean = _clean_name(name)
    suffix_hits = [suffix for suffix in _STORE_SUFFIXES if clean.endswith(suffix)]
    if clean.endswith("酒店"):
        suffix_hits = [suffix for suffix in suffix_hits if suffix != "店"]
    landmark_hits = [keyword for keyword in _LANDMARK_KEYWORDS if keyword in name]
    return list(dict.fromkeys(suffix_hits + landmark_hits))


def _entry_hits(name: str) -> list[str]:
    return list(dict.fromkeys(keyword for keyword in _ENTRY_KEYWORDS if keyword in name))


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
    first_hits = _first_name_hits(name)
    entry_hits = _entry_hits(name)
    score = float(bool(store_suffix or first_hits)) + float(bool(entry_hits))
    fields = [
        {"label": "酒店展示名称", "value": name},
        {
            "label": "门店后缀",
            "value": store_suffix or "未识别",
            "note": "直接取酒店名称括号内的完整内容",
        },
        {
            "label": "命中入口词",
            "value": "、".join(entry_hits) or "未命中",
            "note": "热门商圈、交通、医院、景区、学校等入口词",
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
        "note": "酒店展示名称保持原值；门店后缀直接取名称括号内容；入口词按酒店名称识别。",
    }


__all__ = ["build_page_entry_item"]