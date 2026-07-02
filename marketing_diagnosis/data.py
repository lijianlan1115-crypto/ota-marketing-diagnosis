from __future__ import annotations

import datetime as dt
from typing import Any

SECTIONS = ["hotel_daily", "ota_funnel", "products", "reviews", "competitors"]

SHEET_NAMES = {
    "hotel_daily": {"hotel_daily", "daily", "酒店日报", "每日经营", "经营日报", "jy01", "rs01"},
    "ota_funnel": {"ota_funnel", "funnel", "OTA漏斗", "流量漏斗", "ota_business_metrics"},
    "products": {"products", "商品", "商品价格", "goods_price_mapping"},
    "reviews": {"reviews", "review", "评论", "口碑", "review_detail"},
    "competitors": {"competitors", "competition", "竞品", "竞品数据"},
}

FIELD_MAP = {
    "hotel_daily": {
        "日期": "business_date", "营业日期": "business_date", "date": "business_date", "data_date": "business_date",
        "总房量": "room_count", "房间数": "room_count", "available_room_nights": "room_count",
        "间夜": "room_nights", "售出间夜": "room_nights", "sold_room_nights": "room_nights", "sold_rooms": "room_nights",
        "收入": "room_revenue", "房费收入": "room_revenue", "room_fee": "room_revenue", "revenue": "room_revenue",
        "出租率": "occupancy_rate", "入住率": "occupancy_rate", "occupancy": "occupancy_rate",
        "平均房价": "adr", "room_daily_price": "adr", "rack_rate": "adr",
    },
    "ota_funnel": {
        "日期": "business_date", "平台": "platform", "渠道": "platform", "channel_source": "platform", "source_platform": "platform",
        "曝光": "exposure", "曝光人数": "exposure", "曝光量": "exposure", "peer_exposure": "peer_exposure",
        "浏览": "views", "浏览人数": "views", "访客": "visitors", "UV": "visitors", "peer_views": "peer_views",
        "支付订单": "paid_orders", "订单数": "paid_orders", "支付订单数": "paid_orders", "orders": "paid_orders",
        "支付转化率": "payment_conversion_rate", "转化率": "payment_conversion_rate", "浏览-支付转化率": "payment_conversion_rate",
        "同行平均转化率": "peer_avg_conversion_rate", "商圈平均转化率": "peer_avg_conversion_rate", "peer_payment_conversion_rate": "peer_avg_conversion_rate",
        "排名": "peer_rank", "商圈排名": "peer_rank", "competitor_rank": "peer_rank",
    },
    "products": {
        "平台": "platform", "渠道": "platform", "channel_source": "platform", "source_platform": "platform",
        "房型": "room_type_name", "source_room_type_name": "room_type_name",
        "商品名": "product_name", "商品名称": "product_name", "ota_product_name": "product_name", "source_product_name": "product_name",
        "商品类型": "product_type", "rate_plan_name": "product_type",
        "挂牌价": "listed_price", "门市价": "listed_price", "ota_sale_price": "listed_price", "current_sale_price": "listed_price",
        "活动价": "activity_price", "团购价": "activity_price",
        "到手价": "final_price", "售卖价": "final_price", "target_sale_price": "final_price",
        "是否钟点房": "is_hour_room", "钟点房": "is_hour_room",
        "是否团购": "is_group_buy", "团购": "is_group_buy", "is_super_deal": "is_group_buy",
    },
    "reviews": {
        "平台": "platform", "渠道": "platform", "channel_source": "platform",
        "评论日期": "review_date", "日期": "review_date", "review_time": "review_date", "stay_date": "review_date",
        "评分": "rating", "星级": "rating", "review_score": "rating", "review_score_max": "rating",
        "评论": "review_text", "评论内容": "review_text", "评价内容": "review_text", "review_content": "review_text",
        "是否差评": "is_negative", "差评": "is_negative", "is_negative_review": "is_negative",
        "关键词": "keywords", "rank_item_name": "keywords",
    },
    "competitors": {
        "日期": "business_date", "竞品": "competitor_name", "竞品名称": "competitor_name",
        "房型": "room_type_name", "价格": "price", "售卖价": "price", "peer_average": "price",
        "排名": "rank", "competitor_rank": "rank", "距离": "distance", "活动标签": "promotion_tag",
    },
}

REQUIRED = {
    "hotel_daily": {"business_date", "room_count", "room_nights"},
    "ota_funnel": {"platform", "views", "paid_orders"},
    "products": {"product_name", "listed_price"},
    "reviews": {"review_text"},
    "competitors": {"competitor_name", "price"},
}

NUMBER_FIELDS = {
    "room_count", "room_nights", "room_revenue", "adr", "revpar", "occupancy_rate",
    "exposure", "peer_exposure", "views", "peer_views", "visitors", "paid_orders", "payment_conversion_rate", "peer_avg_conversion_rate",
    "peer_rank", "listed_price", "activity_price", "final_price", "rating", "price", "rank",
}

BOOL_FIELDS = {"is_hour_room", "is_group_buy", "is_negative"}
DATE_FIELDS = {"business_date", "review_date"}
MASK_FIELDS = {"contact", "order_id", "room_no", "guest_name"}


def section_for_sheet(name: str) -> str | None:
    value = str(name or "").strip()
    lower = value.lower()
    for section, aliases in SHEET_NAMES.items():
        if value in aliases or lower in {x.lower() for x in aliases}:
            return section
    return None


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        percent = "%" in text
        text = text.replace("%", "")
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        return number / 100 if percent else number
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _boolean(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "是", "有", "团购", "钟点"}:
        return True
    if text in {"0", "false", "no", "n", "否", "无"}:
        return False
    return None


def _date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else text


def _canonical_key(section: str, key: str) -> str:
    raw = str(key or "").strip()
    return FIELD_MAP.get(section, {}).get(raw, raw)


def normalize_section(section: str, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows or []:
        item: dict[str, Any] = {}
        for raw_key, value in row.items():
            key = _canonical_key(section, str(raw_key))
            if not key:
                continue
            seen.add(key)
            if key in MASK_FIELDS:
                item[key] = "***" if value not in (None, "") else ""
            elif key in NUMBER_FIELDS:
                item[key] = _number(value)
            elif key in BOOL_FIELDS:
                item[key] = _boolean(value)
            elif key in DATE_FIELDS:
                item[key] = _date(value)
            else:
                item[key] = value
        if any(v not in (None, "") for v in item.values()):
            out.append(item)
    missing = sorted(REQUIRED.get(section, set()) - seen)
    return out, {"section": section, "row_count": len(out), "missing_fields": missing, "status": "ok" if not missing else "data_gap"}


def normalize_dataset(raw: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    sections: dict[str, list[dict[str, Any]]] = {}
    diagnostics: dict[str, Any] = {}
    for section in SECTIONS:
        rows, diag = normalize_section(section, raw.get(section, []))
        sections[section] = rows
        diagnostics[section] = diag
    missing = {k: v["missing_fields"] for k, v in diagnostics.items() if v["missing_fields"]}
    return {"status": "ok" if not missing else "partial", "sections": sections, "diagnostics": diagnostics, "missing_fields": missing}
