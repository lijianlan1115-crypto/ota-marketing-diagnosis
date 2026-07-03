from __future__ import annotations

from collections import defaultdict
from typing import Any


def _num(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> str:
    return str(value or "")[:10]


def _month(value: Any) -> str:
    day = _date(value)
    return day[:7] if len(day) >= 7 else "unknown"


def operating_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "hotel_daily_missing"}
    ordered = sorted(rows, key=lambda item: _date(item.get("business_date")))
    latest = ordered[-1]
    total_room_count = 0.0
    total_room_nights = 0.0
    total_revenue = 0.0
    revenue_seen = False
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"room_count": 0.0, "room_nights": 0.0, "room_revenue": 0.0})
    daily_series = []
    for row in ordered:
        room_count = _num(row.get("room_count")) or 0.0
        room_nights = _num(row.get("room_nights")) or 0.0
        revenue = _num(row.get("room_revenue"))
        adr_row = _num(row.get("adr"))
        revpar_row = _num(row.get("revpar"))
        if revenue is None and adr_row is not None and room_nights:
            revenue = adr_row * room_nights
        if revenue is None and revpar_row is not None and room_count:
            revenue = revpar_row * room_count
        if revenue is None:
            revenue = 0.0
        else:
            revenue_seen = True
        total_room_count += room_count
        total_room_nights += room_nights
        total_revenue += revenue
        key = _month(row.get("business_date"))
        monthly[key]["room_count"] += room_count
        monthly[key]["room_nights"] += room_nights
        monthly[key]["room_revenue"] += revenue
        occ = _num(row.get("occupancy_rate"))
        if occ is None and room_count:
            occ = room_nights / room_count
        adr = adr_row if adr_row is not None else (revenue / room_nights if room_nights else None)
        revpar = revpar_row if revpar_row is not None else (revenue / room_count if room_count else None)
        daily_series.append({
            "business_date": _date(row.get("business_date")),
            "room_count": room_count or None,
            "room_nights": room_nights or None,
            "room_revenue": round(revenue, 2) if revenue_seen else None,
            "occupancy_rate": round(occ, 4) if occ is not None else None,
            "adr": round(adr, 2) if adr is not None else None,
            "revpar": round(revpar, 2) if revpar is not None else None,
        })
    occupancy = total_room_nights / total_room_count if total_room_count else None
    adr = total_revenue / total_room_nights if revenue_seen and total_room_nights else None
    revpar = total_revenue / total_room_count if revenue_seen and total_room_count else None
    monthly_trend = []
    for month in sorted(monthly):
        item = monthly[month]
        rc = item["room_count"]
        rn = item["room_nights"]
        rr = item["room_revenue"]
        monthly_trend.append({
            "month": month,
            "adr": round(rr / rn, 2) if rn else None,
            "occupancy_rate": round(rn / rc, 4) if rc else None,
            "revpar": round(rr / rc, 2) if rc else None,
            "room_revenue": round(rr, 2),
        })
    return {
        "status": "ok",
        "latest_business_date": latest.get("business_date"),
        "period_start": _date(ordered[0].get("business_date")),
        "period_end": _date(ordered[-1].get("business_date")),
        "room_count": round(total_room_count, 2) if total_room_count else None,
        "room_nights": round(total_room_nights, 2) if total_room_nights else None,
        "room_revenue": round(total_revenue, 2) if revenue_seen else None,
        "occupancy_rate": round(occupancy, 4) if occupancy is not None else None,
        "adr": round(adr, 2) if adr is not None else None,
        "revpar": round(revpar, 2) if revpar is not None else None,
        "history_days": len(ordered),
        "daily_series": daily_series[-62:],
        "monthly_trend": monthly_trend,
    }


def funnel_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "ota_funnel_missing"}
    exposure = sum(_num(row.get("exposure")) or 0 for row in rows)
    views = sum(_num(row.get("views")) or _num(row.get("visitors")) or 0 for row in rows)
    paid_orders = sum(_num(row.get("paid_orders")) or 0 for row in rows)
    derived_conversion = paid_orders / views if views > 0 and paid_orders > 0 else None
    rates = [_num(row.get("payment_conversion_rate")) for row in rows if _num(row.get("payment_conversion_rate")) is not None]
    conversion = derived_conversion if derived_conversion is not None else (sum(rates) / len(rates) if rates else None)
    peer_rates = [_num(row.get("peer_avg_conversion_rate")) for row in rows if _num(row.get("peer_avg_conversion_rate")) is not None]
    peer_avg = sum(peer_rates) / len(peer_rates) if peer_rates else None
    ranks = [_num(row.get("peer_rank")) for row in rows if _num(row.get("peer_rank")) is not None]
    by_platform: dict[str, dict[str, float]] = defaultdict(lambda: {"exposure": 0.0, "views": 0.0, "paid_orders": 0.0})
    for row in rows:
        platform = str(row.get("platform") or "unknown")
        by_platform[platform]["exposure"] += _num(row.get("exposure")) or 0.0
        by_platform[platform]["views"] += _num(row.get("views")) or _num(row.get("visitors")) or 0.0
        by_platform[platform]["paid_orders"] += _num(row.get("paid_orders")) or 0.0
    platform_rows = []
    for platform, item in sorted(by_platform.items()):
        pv = item["views"]
        po = item["paid_orders"]
        platform_rows.append({
            "platform": platform,
            "exposure": round(item["exposure"], 2) or None,
            "views": round(pv, 2) or None,
            "paid_orders": round(po, 2) or None,
            "payment_conversion_rate": round(po / pv, 4) if pv and po else None,
        })
    return {
        "status": "ok",
        "exposure": exposure or None,
        "views": views or None,
        "paid_orders": paid_orders or None,
        "exposure_to_view_rate": round(views / exposure, 4) if exposure and views else None,
        "payment_conversion_rate": round(conversion, 4) if conversion is not None else None,
        "peer_avg_conversion_rate": round(peer_avg, 4) if peer_avg is not None else None,
        "best_peer_rank": min(ranks) if ranks else None,
        "by_platform": platform_rows,
    }


def price_ladder_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "products_missing"}
    prices = []
    jump_risks = []
    platforms = defaultdict(int)
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
        platforms[str(row.get("platform") or "unknown")] += 1
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
        "by_platform": dict(platforms),
    }


def reputation_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "reviews_missing"}
    ratings = [_num(row.get("rating")) for row in rows if _num(row.get("rating")) is not None]
    negative = [row for row in rows if row.get("is_negative") is True or (_num(row.get("rating")) is not None and (_num(row.get("rating")) or 0) < 4)]
    keywords = []
    by_platform: dict[str, dict[str, Any]] = defaultdict(lambda: {"review_count": 0, "rating_sum": 0.0, "rating_count": 0, "negative_count": 0})
    for row in rows:
        raw = row.get("keywords")
        if raw:
            keywords.extend([item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()])
        platform = str(row.get("platform") or "unknown")
        by_platform[platform]["review_count"] += 1
        rating = _num(row.get("rating"))
        if rating is not None:
            by_platform[platform]["rating_sum"] += rating
            by_platform[platform]["rating_count"] += 1
        if row in negative:
            by_platform[platform]["negative_count"] += 1
    platform_rows = []
    for platform, item in sorted(by_platform.items()):
        count = item["review_count"]
        rating_count = item["rating_count"]
        platform_rows.append({
            "platform": platform,
            "review_count": count,
            "rating_avg": round(item["rating_sum"] / rating_count, 2) if rating_count else None,
            "negative_review_rate": round(item["negative_count"] / count, 4) if count else None,
        })
    return {
        "status": "ok",
        "review_count": len(rows),
        "rating_avg": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "negative_review_count": len(negative),
        "negative_review_rate": round(len(negative) / len(rows), 4) if rows else None,
        "keywords": sorted(set(keywords))[:20],
        "sample_negative_reviews": [row.get("review_text") for row in negative[:3] if row.get("review_text")],
        "by_platform": platform_rows,
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
