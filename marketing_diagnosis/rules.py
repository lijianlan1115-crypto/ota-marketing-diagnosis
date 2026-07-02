from marketing_diagnosis.metrics_core import competitor_metrics, funnel_metrics, operating_metrics, price_ladder_metrics, reputation_metrics


def process(data):
    sections = data.get("sections") or {}
    operating = operating_metrics(sections.get("hotel_daily", []))
    funnel = funnel_metrics(sections.get("ota_funnel", []))
    price = price_ladder_metrics(sections.get("products", []))
    reputation = reputation_metrics(sections.get("reviews", []))
    competitors = competitor_metrics(sections.get("competitors", []), own_min_price=price.get("min_price") if price.get("status") == "ok" else None)
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
    if not notes:
        notes.append({"level": "low", "title": "no major risk found", "evidence": "No high-risk rule triggered.", "suggestion": "Add more continuous data for trend analysis."})
        actions.append("Add more data before making major decisions.")
    return {"status": "ok" if data.get("status") == "ok" else "partial", "type": "ota_marketing", "boundary": "report_only", "data_quality": {"status": data.get("status"), "missing_fields": data.get("missing_fields") or {}, "diagnostics": data.get("diagnostics") or {}}, "metrics": {"operating": operating, "ota_funnel": funnel, "price_ladder": price, "reputation": reputation, "competitors": competitors}, "notes": notes, "actions": actions}
