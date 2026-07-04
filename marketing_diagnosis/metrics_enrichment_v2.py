from __future__ import annotations

from typing import Any

from marketing_diagnosis.metrics_enrichment import enrich_metrics as base_enrich_metrics
from marketing_diagnosis.room_type_analysis import build_room_type_metrics


def enrich_metrics(metrics: dict[str, Any], sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    context = base_enrich_metrics(metrics, sections)
    room_types = build_room_type_metrics(sections)
    products = sections.get("products") or []
    funnel = sections.get("ota_funnel") or []
    room_types["data_period"] = {
        "label": "房型价格与销售",
        "grain": "mixed",
        "start": None,
        "end": None,
        "row_count": len(products) + len(funnel),
        "note": "价格为商品快照口径；销售表现来自房型级漏斗/订单字段，缺失时只展示价格与活动覆盖。",
    }
    metrics["room_types"] = room_types
    context.append({"module": "房型价格与销售", **room_types["data_period"]})
    return context
