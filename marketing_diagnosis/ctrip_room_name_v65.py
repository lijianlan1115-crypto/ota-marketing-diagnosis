from __future__ import annotations

import re
from typing import Any


_NAME_KEYWORDS = (
    "大床", "双床", "单床", "家庭床", "上下铺", "榻榻米", "圆床", "套房",
    "商务", "亲子", "情侣", "电竞", "棋牌", "观景", "景观", "影院", "光影",
    "浴缸", "零压", "洗衣", "早餐", "含早", "无早", "智能", "投影", "阳台", "落地窗",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _qualified(name: str) -> tuple[bool, int, str]:
    chinese_text = "".join(re.findall(r"[\u4e00-\u9fff]", name))
    length = len(chinese_text)
    hits = [keyword for keyword in _NAME_KEYWORDS if keyword in chinese_text]
    if length <= 5:
        return False, length, "中文字符数不足6个"
    if not hits:
        return False, length, "未识别床型、场景、卖点或人群信息"
    return True, length, f"包含{hits[0]}信息"


def build_room_name_item(sections: dict[str, Any]) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in sections.get("ctrip_goods_price_mapping") or []
        if isinstance(row, dict)
    ]
    if not rows:
        return {
            "standard_item_id": 11,
            "participates_in_score": True,
            "item_score": None,
            "data_status": "missing",
            "source": "ctrip_ota_goods_price_mapping",
            "fields_complete": True,
            "fields": [],
            "records": [],
            "note": "等待携程售卖房型快照。",
        }

    records: list[dict[str, Any]] = []
    for row in rows:
        name = _text(row.get("ota_product_name"))
        qualified, length, reason = _qualified(name)
        records.append(
            {
                "name": name or "未命名售卖房型",
                "length": length,
                "qualified": qualified,
                "reason": reason,
                "ota_room_type_id": row.get("ota_room_type_id"),
                "ota_product_id": row.get("ota_product_id"),
                "is_hour_room": row.get("is_hour_room"),
            }
        )
    qualified_count = sum(1 for record in records if record["qualified"])
    total = len(records)
    ratio = qualified_count / total if total else 0.0
    score = 4.0 if ratio >= 0.8 else 2.4 if ratio >= 0.5 else 0.0
    room_ids = {str(row.get("ota_room_type_id") or "") for row in rows if row.get("ota_room_type_id")}
    fields = [
        {"label": "售卖商品数", "value": total},
        {"label": "售卖房型数", "value": len(room_ids) or total},
        {"label": "合格房型", "value": qualified_count},
        {"label": "合格房型占比", "value": f"{ratio:.1%}"},
    ]
    return {
        "standard_item_id": 11,
        "participates_in_score": True,
        "item_score": score,
        "data_status": "success",
        "source": "ctrip_ota_goods_price_mapping",
        "fields_complete": True,
        "fields": fields,
        "records": records,
        "note": "合格名称需大于5个字，并包含床型、场景、卖点或人群信息；占比>=80%得4分，50%-80%得2.4分，低于50%得0分。",
    }


__all__ = ["build_room_name_item"]
