from marketing_diagnosis.metrics_core import competitor_metrics, funnel_metrics, operating_metrics, price_ladder_metrics, reputation_metrics


MODULES = [
    ("M01", "operating_result", 16),
    ("M02", "traffic_exposure", 12),
    ("M03", "conversion_path", 14),
    ("M04", "price_inventory", 12),
    ("M05", "promotion_efficiency", 10),
    ("M06", "content_entry", 10),
    ("M07", "reputation_trust", 16),
    ("M08", "execution_data_quality", 10),
]


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def _module_score(module_id, module_name, weight, rate, reasons, status="ok", source_fields=None):
    if rate is None:
        score = 0.0
        clean_rate = None
    else:
        clean_rate = _clamp(rate)
        score = round(weight * clean_rate, 2)
    return {
        "module_id": module_id,
        "module_name": module_name,
        "weight": weight,
        "score": score,
        "rate": round(clean_rate, 4) if clean_rate is not None else None,
        "status": status,
        "reasons": reasons,
        "source_fields": source_fields or [],
    }


def _risk(score):
    if score < 60:
        return "high"
    if score < 80:
        return "medium"
    return "low"


def _has_value(payload, key):
    return isinstance(payload, dict) and payload.get(key) is not None


def score_modules(metrics, data_quality):
    op = metrics["operating"]
    funnel = metrics["ota_funnel"]
    price = metrics["price_ladder"]
    rep = metrics["reputation"]
    missing_count = sum(len(v or []) for v in (data_quality.get("missing_fields") or {}).values())
    empty_sections = data_quality.get("empty_sections") or {}

    occ = op.get("occupancy_rate")
    conv = funnel.get("payment_conversion_rate")
    peer_conv = funnel.get("peer_avg_conversion_rate")
    neg = rep.get("negative_review_rate")
    rating = rep.get("rating_avg")
    jump_count = len(price.get("price_jump_risks") or [])
    product_count = price.get("product_count") or 0
    review_count = rep.get("review_count") or 0
    exposure = funnel.get("exposure")
    views = funnel.get("views")

    scores = []
    if occ is None:
        scores.append(_module_score("M01", "operating_result", 16, None, ["data_gap: occupancy_rate missing"], "data_gap", ["jy01.occupancy_rate or room_count+room_nights"]))
    else:
        scores.append(_module_score("M01", "operating_result", 16, 0.95 if occ >= 0.85 else 0.75 if occ >= 0.7 else 0.45, ["occupancy_rate from normalized hotel_daily"], "ok", ["hotel_daily.occupancy_rate", "hotel_daily.room_count", "hotel_daily.room_nights"]))

    if views is None and exposure is None:
        scores.append(_module_score("M02", "traffic_exposure", 12, None, ["data_gap: exposure/views missing"], "data_gap", ["ota_business_metrics.曝光量", "ota_business_metrics.浏览人数"]))
    else:
        scores.append(_module_score("M02", "traffic_exposure", 12, 0.9 if (exposure or 0) >= 800 or (views or 0) >= 100 else 0.65, ["exposure and views from OTA business metrics"], "ok", ["ota_funnel.exposure", "ota_funnel.views"]))

    if conv is None:
        scores.append(_module_score("M03", "conversion_path", 14, None, ["data_gap: payment_conversion_rate missing"], "data_gap", ["ota_business_metrics.支付转化率", "ota_business_metrics.浏览-支付转化率"]))
    else:
        if peer_conv:
            conversion_rate = 0.9 if conv >= peer_conv else 0.55 if conv >= peer_conv * 0.7 else 0.3
        else:
            conversion_rate = 0.85 if conv >= 0.08 else 0.6 if conv >= 0.04 else 0.35
        scores.append(_module_score("M03", "conversion_path", 14, conversion_rate, ["payment conversion from OTA business metrics"], "ok", ["ota_funnel.payment_conversion_rate", "ota_funnel.peer_avg_conversion_rate"]))

    if not product_count:
        scores.append(_module_score("M04", "price_inventory", 12, None, ["data_gap: products missing"], "data_gap", ["ota_goods_price_mapping"] ))
    else:
        price_rate = 0.8 if not jump_count else 0.55
        scores.append(_module_score("M04", "price_inventory", 12, price_rate, ["product ladder from OTA goods price mapping"], "ok", ["products.listed_price", "products.final_price"]))

    scores.append(_module_score("M05", "promotion_efficiency", 10, None, ["data_gap: promotion tables not wired into MVP metrics yet"], "data_gap", ["ota_promotion_activity", "ota_activity_product_detail", "promo_cost", "promo_roi"]))

    if not product_count:
        scores.append(_module_score("M06", "content_entry", 10, None, ["data_gap: page/content fields not wired"], "data_gap", ["page_collection", "product tags", "image/video status"]))
    else:
        scores.append(_module_score("M06", "content_entry", 10, None, ["data_gap: product presence is real, but page content score requires page collection fields"], "data_gap", ["page_collection", "image/video status", "entry tags"]))

    if rating is None and not review_count:
        scores.append(_module_score("M07", "reputation_trust", 16, None, ["data_gap: review score/detail missing"], "data_gap", ["ota_review_detail.review_score", "ota_review_overview"] ))
    else:
        if rating is None:
            rep_rate = 0.45
        else:
            rep_rate = 0.9 if rating >= 4.7 and (neg is None or neg <= 0.03) else 0.65 if rating >= 4.4 else 0.4
        if review_count < 10:
            rep_rate = min(rep_rate, 0.7)
        scores.append(_module_score("M07", "reputation_trust", 16, rep_rate, ["rating and negative reviews from OTA review data"], "ok", ["reviews.rating", "reviews.is_negative", "reviews.review_text"]))

    quality_rate = 0.9 if missing_count == 0 and not empty_sections else 0.65 if missing_count <= 5 else 0.4
    scores.append(_module_score("M08", "execution_data_quality", 10, quality_rate, [f"missing_fields={missing_count}", f"empty_sections={list(empty_sections.keys())}"], "ok" if missing_count == 0 and not empty_sections else "partial", ["normalization diagnostics", "source diagnostics"]))
    return scores


def process(data):
    sections = data.get("sections") or {}
    operating = operating_metrics(sections.get("hotel_daily", []))
    funnel = funnel_metrics(sections.get("ota_funnel", []))
    price = price_ladder_metrics(sections.get("products", []))
    reputation = reputation_metrics(sections.get("reviews", []))
    competitors = competitor_metrics(sections.get("competitors", []), own_min_price=price.get("min_price") if price.get("status") == "ok" else None)
    data_quality = {
        "status": data.get("status"),
        "missing_fields": data.get("missing_fields") or {},
        "empty_sections": data.get("empty_sections") or {},
        "diagnostics": data.get("diagnostics") or {},
        "source_diagnostics": data.get("source_diagnostics") or [],
    }
    metrics = {"operating": operating, "ota_funnel": funnel, "price_ladder": price, "reputation": reputation, "competitors": competitors}
    module_scores = score_modules(metrics, data_quality)
    final_score = round(sum(item["score"] for item in module_scores), 2)
    notes = []
    actions = []
    conv = funnel.get("payment_conversion_rate")
    peer = funnel.get("peer_avg_conversion_rate")
    if conv is not None and peer is not None and conv < peer * 0.7:
        notes.append({"level": "high", "title": "conversion below peers", "evidence": f"conversion={conv:.4f}, peer={peer:.4f}", "suggestion": "Improve content, tags, review placement, and product ladder."})
        actions.append("Improve OTA content page first.")
    jump_count = len(price.get("price_jump_risks") or [])
    if jump_count:
        notes.append({"level": "medium", "title": "product ladder jump risk", "evidence": f"risk_products={jump_count}", "suggestion": "Review group-buy, hourly, and full-day products together."})
        actions.append("Make the product price ladder clearer.")
    neg_rate = reputation.get("negative_review_rate")
    if neg_rate is not None and neg_rate > 0.05:
        notes.append({"level": "medium", "title": "negative review rate is high", "evidence": f"negative_rate={neg_rate:.4f}", "suggestion": "Fix repeated service and facility issues."})
    gap = competitors.get("own_min_price_vs_competitor_avg_gap")
    if gap is not None and gap > 30:
        notes.append({"level": "medium", "title": "entry price above competitor average", "evidence": f"gap={gap:.2f}", "suggestion": "Optimize entry product before broad discounting."})
    if operating.get("occupancy_rate") is not None and operating["occupancy_rate"] < 0.65:
        notes.append({"level": "medium", "title": "occupancy is low", "evidence": f"occupancy={operating['occupancy_rate']:.4f}", "suggestion": "Use funnel data to locate exposure or conversion issues."})
    data_gap_modules = [item["module_id"] for item in module_scores if item.get("status") == "data_gap"]
    if data_gap_modules:
        notes.append({"level": "medium", "title": "some modules are data gaps", "evidence": f"modules={','.join(data_gap_modules)}", "suggestion": "Do not treat data-gap module scores as real operating conclusions. Wire the corresponding tables or fields first."})
        actions.append("Check report data quality and source diagnostics before using the conclusion externally.")
    if not notes:
        notes.append({"level": "low", "title": "no major risk found", "evidence": "No high-risk rule was triggered from available real data.", "suggestion": "Add more continuous data for trend analysis."})
        actions.append("Add more data before making major decisions.")
    return {"status": "ok" if data.get("status") == "ok" and not data_gap_modules else "partial", "type": "ota_marketing", "boundary": "report_only", "final_score": final_score, "risk_level": _risk(final_score), "module_scores": module_scores, "data_quality": data_quality, "metrics": metrics, "notes": notes, "actions": actions}
