from __future__ import annotations

from typing import Any


def _num(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def operating_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "hotel_daily_missing"}
    ordered = sorted(rows, key=lambda item: str(item.get("business_date") or ""))
    latest = ordered[-1]
    room_count = _num(latest.get("room_count"))
    room_nights = _num(latest.get("room_nights"))
    revenue = _num(latest.get("room_revenue"))
    occupancy = _num(latest.get("occupancy_rate"))
    if occupancy is None and room_count and room_nights is not None:
        occupancy = room_nights / room_count
    adr = _num(latest.get("adr"))
    if adr is None and revenue is not None and room_nights:
        adr = revenue / room_nights
    revpar = _num(latest.get("revpar"))
    if revpar is None and revenue is not None and room_count:
        revpar = revenue / room_count
    return {
        "status": "ok",
        "latest_business_date": latest.get("business_date"),
        "room_count": room_count,
        "room_nights": room_nights,
        "room_revenue": revenue,
        "occupancy_rate": round(occupancy, 4) if occupancy is not None else None,
        "adr": round(adr, 2) if adr is not None else None,
        "revpar": round(revpar, 2) if revpar is not None else None,
        "history_days": len(ordered),
    }


def funnel_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "ota_funnel_missing"}
    exposure = sum(_num(row.get("exposure")) or 0 for row in rows)
    views = sum(_num(row.get("views")) or _num(row.get("visitors")) or 0 for row in rows)
    paid_orders = sum(_num(row.get("paid_orders")) or 0 for row in rows)
    conversion = paid_orders / views if views > 0 else None
    rates = [_num(row.get("payment_conversion_rate")) for row in rows if _num(row.get("payment_conversion_rate")) is not None]
    if rates:
        conversion = sum(rates) / len(rates)
    peer_rates = [_num(row.get("peer_avg_conversion_rate")) for row in rows if _num(row.get("peer_avg_conversion_rate")) is not None]
    peer_avg = sum(peer_rates) / len(peer_rates) if peer_rates else None
    ranks = [_num(row.get("peer_rank")) for row in rows if _num(row.get("peer_rank")) is not None]
    return {
        "status": "ok",
        "exposure": exposure or None,
        "views": views or None,
        "paid_orders": paid_orders or None,
        "payment_conversion_rate": round(conversion, 4) if conversion is not None else None,
        "peer_avg_conversion_rate": round(peer_avg, 4) if peer_avg is not None else None,
        "best_peer_rank": min(ranks) if ranks else None,
    }


def price_ladder_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "products_missing"}
    prices = []
    jump_risks = []
    for row in rows:
        listed = _num(row.get("listed_price"))
        final = _num(row.get("final_price")) or _num(row.get("activity_price")) or listed
        if final:
            prices.append(final)
        if listed and final and final / listed < 0.65:
            jump_risks.append({
                "product_name": row.get("product_name"),
                "listed_price": listed,
                "final_price": final,
                "ratio": round(final / listed, 4),
            })
    group_buy_count = sum(1 for row in rows if row.get("is_group_buy") or str(row.get("product_type") or "").lower() in {"super_deal", "group_buy", "团购"})
    hour_room_count = sum(1 for row in rows if row.get("is_hour_room") or "钟点" in str(row.get("product_name") or ""))
    return {
        "status": "ok",
        "product_count": len(rows),
        "min_price": min(prices) if prices else None,
        "max_price": max(prices) if prices else None,
        "price_span": max(prices) - min(prices) if len(prices) >= 2 else None,
        "group_buy_count": group_buy_count,
        "hour_room_count": hour_room_count,
        "price_jump_risks": jump_risks,
    }


def reputation_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "reviews_missing"}
    ratings = [_num(row.get("rating")) for row in rows if _num(row.get("rating")) is not None]
    negative = [row for row in rows if row.get("is_negative") is True or (_num(row.get("rating")) is not None and (_num(row.get("rating")) or 0) < 4)]
    keywords = []
    for row in rows:
        raw = row.get("keywords")
        if raw:
            keywords.extend([item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()])
    return {
        "status": "ok",
        "review_count": len(rows),
        "rating_avg": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "negative_review_count": len(negative),
        "negative_review_rate": round(len(negative) / len(rows), 4) if rows else None,
        "keywords": sorted(set(keywords))[:20],
        "sample_negative_reviews": [row.get("review_text") for row in negative[:3] if row.get("review_text")],
    }


def competitor_metrics(rows: list[dict[str, Any]], own_min_price: float | None = None) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "competitors_missing"}
    prices = [_num(row.get("price")) for row in rows if _num(row.get("price")) is not None]
    ranks = [_num(row.get("rank")) for row in rows if _num(row.get("rank")) is not None]
    avg_price = sum(prices) / len(prices) if prices else None
    gap = own_min_price - avg_price if own_min_price is not None and avg_price else None
    return {
        "status": "ok",
        "competitor_count": len({str(row.get("competitor_name") or "") for row in rows if row.get("competitor_name")}),
        "competitor_avg_price": round(avg_price, 2) if avg_price is not None else None,
        "best_competitor_rank": min(ranks) if ranks else None,
        "own_min_price_vs_competitor_avg_gap": round(gap, 2) if gap is not None else None,
    }
