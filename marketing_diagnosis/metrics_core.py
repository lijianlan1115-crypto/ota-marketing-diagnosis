from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        number = float(value)
        return None if number != number else number
    except (TypeError, ValueError):
        return None


def _ratio(value: Any) -> float | None:
    number = _num(value)
    if number is None:
        return None
    return number / 100 if number > 1 else number


def _date(value: Any) -> str:
    return str(value or "")[:10]


def _month(value: Any) -> str:
    day = _date(value)
    return day[:7] if len(day) >= 7 else "unknown"


def _monthly_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trend = []
    for row in sorted(rows, key=lambda item: str(item.get("period_month") or "")):
        month = row.get("period_month")
        if not month:
            continue
        rc = _num(row.get("room_count"))
        rn = _num(row.get("room_nights"))
        rr = _num(row.get("room_revenue"))
        occ = _ratio(row.get("occupancy_rate"))
        adr = _num(row.get("adr")) or (rr / rn if rr is not None and rn else None)
        revpar = _num(row.get("revpar")) or (rr / rc if rr is not None and rc else None)
        trend.append({
            "month": str(month),
            "adr": round(adr, 2) if adr is not None else None,
            "occupancy_rate": round(occ if occ is not None else (rn / rc if rn is not None and rc else 0), 4) if (occ is not None or (rn is not None and rc)) else None,
            "revpar": round(revpar, 2) if revpar is not None else None,
            "room_revenue": round(rr, 2) if rr is not None else None,
        })
    return trend


def operating_metrics(rows: list[dict[str, Any]], monthly_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
        room_nights = _num(row.get("room_nights")) or _num(row.get("sold_rooms")) or 0.0
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
        occ = _ratio(row.get("occupancy_rate"))
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
    monthly_trend = _monthly_from_rows(monthly_rows or [])
    if not monthly_trend:
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
        "monthly_trend": monthly_trend[-12:],
    }


def funnel_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "ota_funnel_missing"}
    exposure = sum(_num(row.get("exposure")) or 0 for row in rows)
    views = sum(_num(row.get("views")) or _num(row.get("visitors")) or 0 for row in rows)
    paid_orders = sum(_num(row.get("paid_orders")) or 0 for row in rows)
    sales_revenue = sum(_num(row.get("sales_revenue")) or 0 for row in rows)
    sold_room_nights = sum(_num(row.get("sold_room_nights")) or 0 for row in rows)
    derived_conversion = paid_orders / views if views > 0 and paid_orders > 0 else None
    rates = [_ratio(row.get("payment_conversion_rate")) for row in rows if _ratio(row.get("payment_conversion_rate")) is not None]
    conversion = derived_conversion if derived_conversion is not None else (sum(rates) / len(rates) if rates else None)
    exposure_view_rates = [_ratio(row.get("exposure_to_view_rate")) for row in rows if _ratio(row.get("exposure_to_view_rate")) is not None]
    exposure_to_view_rate = views / exposure if exposure and views else (sum(exposure_view_rates) / len(exposure_view_rates) if exposure_view_rates else None)
    peer_rates = [_ratio(row.get("peer_avg_conversion_rate")) for row in rows if _ratio(row.get("peer_avg_conversion_rate")) is not None]
    peer_avg = sum(peer_rates) / len(peer_rates) if peer_rates else None
    ranks = [_num(row.get("peer_rank")) for row in rows if _num(row.get("peer_rank")) is not None]
    by_platform: dict[str, dict[str, float]] = defaultdict(lambda: {"exposure": 0.0, "views": 0.0, "paid_orders": 0.0, "sales_revenue": 0.0})
    for row in rows:
        platform = str(row.get("platform") or "unknown")
        by_platform[platform]["exposure"] += _num(row.get("exposure")) or 0.0
        by_platform[platform]["views"] += _num(row.get("views")) or _num(row.get("visitors")) or 0.0
        by_platform[platform]["paid_orders"] += _num(row.get("paid_orders")) or 0.0
        by_platform[platform]["sales_revenue"] += _num(row.get("sales_revenue")) or 0.0
    platform_rows = []
    for platform, item in sorted(by_platform.items()):
        pv = item["views"]
        po = item["paid_orders"]
        platform_rows.append({
            "platform": platform,
            "exposure": round(item["exposure"], 2) or None,
            "views": round(pv, 2) or None,
            "paid_orders": round(po, 2) or None,
            "sales_revenue": round(item["sales_revenue"], 2) or None,
            "payment_conversion_rate": round(po / pv, 4) if pv and po else None,
        })
    return {
        "status": "ok",
        "exposure": exposure or None,
        "views": views or None,
        "paid_orders": paid_orders or None,
        "sales_revenue": round(sales_revenue, 2) if sales_revenue else None,
        "sold_room_nights": sold_room_nights or None,
        "exposure_to_view_rate": round(exposure_to_view_rate, 4) if exposure_to_view_rate is not None else None,
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
    room_types = set()
    for row in rows:
        listed = _num(row.get("listed_price"))
        final = _num(row.get("final_price")) or _num(row.get("activity_price")) or listed
        if final:
            prices.append(final)
        if listed and final and final / listed < 0.65:
            jump_risks.append({"product_name": row.get("product_name"), "listed_price": listed, "final_price": final, "ratio": round(final / listed, 4)})
        platforms[str(row.get("platform") or "unknown")] += 1
        if row.get("room_type_name"):
            room_types.add(str(row.get("room_type_name")))
    group_buy_count = sum(1 for row in rows if row.get("is_group_buy") or str(row.get("product_type") or "").lower() in {"super_deal", "group_buy", "团购"})
    hour_room_count = sum(1 for row in rows if row.get("is_hour_room") or "钟点" in str(row.get("product_name") or ""))
    return {
        "status": "ok",
        "product_count": len(rows),
        "room_type_count": len(room_types),
        "min_price": min(prices) if prices else None,
        "max_price": max(prices) if prices else None,
        "price_span": max(prices) - min(prices) if len(prices) >= 2 else None,
        "group_buy_count": group_buy_count,
        "hour_room_count": hour_room_count,
        "price_jump_risks": jump_risks,
        "by_platform": dict(platforms),
    }


def promotion_metrics(rows: list[dict[str, Any]], product_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows and not product_rows:
        return {"status": "data_gap", "reason": "promotion_tables_empty"}
    active_rows = [row for row in rows if str(row.get("activity_status") or "") in {"进行中", "active", "ACTIVE", "有效"}]
    names = [str(row.get("activity_name")) for row in rows if row.get("activity_name")]
    room_type_total = sum(_num(row.get("activity_room_type_count")) or 0 for row in rows)
    activity_products = len(product_rows)
    platforms = Counter(str(row.get("platform") or "unknown") for row in rows + product_rows)
    has_discount_rule = any("折" in str(row.get("activity_rule_labels") or "") or "减" in str(row.get("activity_rule_labels") or "") for row in rows)
    return {
        "status": "partial",  # Current exports include activity coverage but not spend/click/order ROI.
        "activity_count": len(rows),
        "active_activity_count": len(active_rows),
        "activity_product_count": activity_products,
        "activity_room_type_count_total": int(room_type_total) if room_type_total else None,
        "activity_names": names[:20],
        "has_discount_rule": has_discount_rule,
        "has_cost_roi_fields": False,
        "missing_roi_fields": ["promo_cost", "promo_clicks", "promo_orders", "promo_revenue", "promo_roi"],
        "by_platform": dict(platforms),
    }


def reputation_metrics(rows: list[dict[str, Any]], overview_rows: list[dict[str, Any]] | None = None, ranking_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    overview_rows = overview_rows or []
    ranking_rows = ranking_rows or []
    if not rows and not overview_rows:
        return {"status": "data_gap", "reason": "reviews_missing"}
    detail_ratings = [_num(row.get("rating")) for row in rows if _num(row.get("rating")) is not None]
    detail_negative = [row for row in rows if row.get("is_negative") is True or (_num(row.get("rating")) is not None and (_num(row.get("rating")) or 0) < 4)]
    if overview_rows:
        total_reviews = sum(int(_num(row.get("review_count")) or 0) for row in overview_rows)
        negative_count = sum(int(_num(row.get("negative_review_count")) or 0) for row in overview_rows)
        weighted_rating_sum = sum((_num(row.get("rating_avg")) or 0) * int(_num(row.get("review_count")) or 0) for row in overview_rows)
        rating_count = sum(int(_num(row.get("review_count")) or 0) for row in overview_rows if _num(row.get("rating_avg")) is not None)
        rating_avg = weighted_rating_sum / rating_count if rating_count else (sum(detail_ratings) / len(detail_ratings) if detail_ratings else None)
        unreplied = sum(int(_num(row.get("unreplied_review_count")) or 0) for row in overview_rows)
    else:
        total_reviews = len(rows)
        negative_count = len(detail_negative)
        rating_avg = sum(detail_ratings) / len(detail_ratings) if detail_ratings else None
        unreplied = sum(1 for row in rows if row.get("is_replied") is False)
    keywords = []
    for row in rows:
        raw = row.get("keywords")
        if raw:
            keywords.extend([item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()])
    ranking_keywords = [row.get("rank_item_name") for row in ranking_rows if row.get("rank_item_name")]
    by_platform: dict[str, dict[str, Any]] = defaultdict(lambda: {"review_count": 0, "rating_sum": 0.0, "rating_weight": 0, "negative_count": 0, "unreplied_count": 0})
    for row in overview_rows:
        platform = str(row.get("platform") or "unknown")
        count = int(_num(row.get("review_count")) or 0)
        by_platform[platform]["review_count"] += count
        rating = _num(row.get("rating_avg"))
        if rating is not None and count:
            by_platform[platform]["rating_sum"] += rating * count
            by_platform[platform]["rating_weight"] += count
        by_platform[platform]["negative_count"] += int(_num(row.get("negative_review_count")) or 0)
        by_platform[platform]["unreplied_count"] += int(_num(row.get("unreplied_review_count")) or 0)
    if not overview_rows:
        for row in rows:
            platform = str(row.get("platform") or "unknown")
            by_platform[platform]["review_count"] += 1
            rating = _num(row.get("rating"))
            if rating is not None:
                by_platform[platform]["rating_sum"] += rating
                by_platform[platform]["rating_weight"] += 1
            if row in detail_negative:
                by_platform[platform]["negative_count"] += 1
            if row.get("is_replied") is False:
                by_platform[platform]["unreplied_count"] += 1
    platform_rows = []
    for platform, item in sorted(by_platform.items()):
        count = item["review_count"]
        weight = item["rating_weight"]
        platform_rows.append({
            "platform": platform,
            "review_count": count,
            "rating_avg": round(item["rating_sum"] / weight, 2) if weight else None,
            "negative_review_rate": round(item["negative_count"] / count, 4) if count else None,
            "unreplied_review_count": item["unreplied_count"],
        })
    return {
        "status": "ok",
        "review_count": total_reviews or len(rows),
        "rating_avg": round(rating_avg, 2) if rating_avg is not None else None,
        "negative_review_count": negative_count,
        "negative_review_rate": round(negative_count / total_reviews, 4) if total_reviews else None,
        "unreplied_review_count": unreplied,
        "keywords": sorted(set(keywords + [str(x) for x in ranking_keywords]))[:30],
        "sample_negative_reviews": [row.get("review_text") for row in detail_negative[:3] if row.get("review_text")],
        "by_platform": platform_rows,
    }


def nearby_event_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "data_gap", "reason": "nearby_events_missing"}
    ordered = sorted(rows, key=lambda row: _num(row.get("countdown_days")) if _num(row.get("countdown_days")) is not None else 9999)
    return {
        "status": "ok",
        "event_count": len(rows),
        "upcoming_60d_count": sum(1 for row in rows if (_num(row.get("countdown_days")) or 9999) <= 60),
        "nearest_event": ordered[0].get("event_name") if ordered else None,
        "nearest_countdown_days": _num(ordered[0].get("countdown_days")) if ordered else None,
        "events": [{"event_name": row.get("event_name"), "event_start_date": row.get("event_start_date"), "distance_km": row.get("distance_km"), "countdown_days": row.get("countdown_days")} for row in ordered[:10]],
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
