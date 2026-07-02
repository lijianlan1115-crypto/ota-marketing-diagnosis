from __future__ import annotations

PUYUE_MYSQL_TABLE_PROFILE = {
    "profile_name": "puyue_mysql_reference",
    "description": "Reference profile derived from real database exports. It describes tables and roles; it is not a CSV input loader.",
    "sections": {
        "operating_daily": {
            "primary_table": "jy01_hotel_statistics_daily",
            "fallback_table": "rs01_room_revenue_daily",
            "grain": "business_date",
            "rules": [
                "Use jy01 total operating rows for historical day-level occupancy, room nights, ADR, RevPAR and revenue.",
                "Use rs01 only as room-fee detail and reconciliation; filter charge_subject=房费 before aggregating room_nights and room_fee.",
            ],
        },
        "realtime_occupancy_reference": {
            "tables": ["jd01_booking_detail", "jd04_inhouse_extension", "kf11_room_status_snapshot"],
            "grain": "as_of_time",
            "rules": [
                "This is a future real-time module reference, not used by the marketing report MVP.",
                "Use booking and in-house state for numerator and room status / maintenance rooms for denominator.",
            ],
        },
        "ota_funnel": {
            "tables": ["meituan_ota_business_metrics", "ctrip_ota_business_metrics"],
            "grain": "business_date, platform, stats_period_type, metric_name",
            "rules": [
                "Metrics are stored in tall format and should be pivoted by metric_name.",
                "Core canonical metrics: exposure, views, paid_orders, payment_conversion_rate, peer_avg_conversion_rate, peer_rank.",
            ],
        },
        "products": {
            "tables": ["meituan_ota_goods_price_mapping", "ctrip_ota_goods_price_mapping"],
            "grain": "platform, source_product_id",
            "rules": [
                "Use this for product ladder and price consistency diagnosis only.",
                "Do not write prices or price task rows from this project.",
            ],
        },
        "reputation": {
            "tables": ["meituan_ota_review_overview", "ctrip_ota_review_overview", "meituan_ota_review_detail", "ctrip_ota_review_detail", "meituan_ota_review_ranking"],
            "grain": "platform, review_id or business_date",
            "rules": [
                "Public review text may be shown in marketing diagnosis evidence.",
                "Private identifiers such as order, room, phone and guest names must remain masked if present.",
            ],
        },
        "promotion": {
            "tables": ["meituan_ota_promotion_activity", "ctrip_ota_promotion_activity", "meituan_ota_activity_product_detail", "ctrip_ota_activity_product_detail"],
            "grain": "platform, activity_id, product_id",
            "rules": [
                "Use for future promotion efficiency and activity-product diagnosis modules.",
                "The MVP scoring currently uses a conservative placeholder until this module is implemented.",
            ],
        },
        "nearby_event": {
            "tables": ["meituan_ota_nearby_event"],
            "grain": "event_id or event_date",
            "rules": [
                "Use for future local event opportunity diagnosis.",
            ],
        },
    },
}
