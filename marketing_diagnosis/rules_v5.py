from __future__ import annotations

from typing import Any

from marketing_diagnosis.ctrip_competition import build_competition_item
from marketing_diagnosis.ctrip_configuration_v63 import build_configuration_items
from marketing_diagnosis.ctrip_page_entry_v66 import build_page_entry_item
from marketing_diagnosis.ctrip_promotion_v67 import build_promotion_item
from marketing_diagnosis.ctrip_psi import build_psi_item
from marketing_diagnosis.ctrip_reputation_v64 import build_reputation_item
from marketing_diagnosis.ctrip_room_name_v65 import build_room_name_item
from marketing_diagnosis.ctrip_user_profile_v58 import build_user_profile_item
from marketing_diagnosis.promotion_performance_v46 import patch_promotion_performance
from marketing_diagnosis.review_yesterday_v45 import patch_yesterday_review_count
from marketing_diagnosis.rules_v4 import process as _base_process
from marketing_diagnosis.visual_diagnosis_v20 import build_visual_diagnosis


_COMPETITION_METRIC_SPECS = (
    {
        "metric_code": "booking_order_count",
        "aliases": ("booking_order_count",),
        "label": "竞争圈平均预订订单量",
        "unit": "单",
    },
    {
        "metric_code": "booking_sales_amount",
        "aliases": ("booking_sales_amount",),
        "label": "竞争圈平均预订销售额",
        "unit": "元",
    },
    {
        "metric_code": "occupancy_ratet",
        "aliases": ("occupancy_ratet", "occupancy_rate"),
        "label": "竞争圈平均出租率",
        "unit": "%",
    },
    {
        "metric_code": "ctrip_app_conversion_ratet",
        "aliases": ("ctrip_app_conversion_ratet", "ctrip_app_conversion_rate"),
        "label": "竞争圈平均携程APP转化率",
        "unit": "%",
    },
    {
        "metric_code": "inhouse_room_night",
        "aliases": ("inhouse_room_night", "inhouse_room_nights"),
        "label": "竞争圈平均在店间夜",
        "unit": "间夜",
    },
    {
        "metric_code": "ctrip_app_visitor_count",
        "aliases": ("ctrip_app_visitor_count", "ctrip_app_visitors"),
        "label": "竞争圈平均携程APP访客",
        "unit": "人",
    },
)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _text(value: Any) -> str:
    return "" if value in (None, "") else str(value).strip()


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _competition_metric_entries(sections: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        dict(row)
        for row in sections.get("ctrip_competition_metrics_30d") or []
        if isinstance(row, dict)
    ]
    rows_by_code: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        code = _text(row.get("metric_code")).lower()
        if code:
            rows_by_code.setdefault(code, []).append(row)

    entries: list[dict[str, Any]] = []
    for spec in _COMPETITION_METRIC_SPECS:
        candidates: list[dict[str, Any]] = []
        for alias in spec["aliases"]:
            candidates.extend(rows_by_code.get(str(alias).lower(), []))

        selected: dict[str, Any] | None = None
        best_completeness = -1
        for row in candidates:
            values = (
                _number(
                    _first(
                        row,
                        "hotel_value",
                        "metric_value",
                        "hotel_metric_value",
                        "current_value",
                        "my_value",
                    )
                ),
                _number(
                    _first(
                        row,
                        "competitor_avg",
                        "competitor_average",
                        "peer_average",
                        "avg_value",
                    )
                ),
                _number(
                    _first(
                        row,
                        "competitor_rank",
                        "ranking_position",
                        "rank_position",
                        "rank",
                    )
                ),
            )
            completeness = sum(value is not None for value in values)
            if selected is None or completeness > best_completeness:
                selected = row
                best_completeness = completeness

        selected = selected or {}
        raw_rank = _first(
            selected,
            "competitor_rank",
            "ranking_position",
            "rank_position",
            "rank",
        )
        competitor_count = _number(
            _first(
                selected,
                "competitor_count",
                "circle_hotel_count",
                "peer_hotel_count",
            )
        )
        if competitor_count is None and "/" in _text(raw_rank):
            competitor_count = _number(_text(raw_rank).split("/", 1)[1])

        hotel_value = _number(
            _first(
                selected,
                "hotel_value",
                "metric_value",
                "hotel_metric_value",
                "current_value",
                "my_value",
            )
        )
        competitor_avg = _number(
            _first(
                selected,
                "competitor_avg",
                "competitor_average",
                "peer_average",
                "avg_value",
            )
        )
        competitor_rank = _number(raw_rank)
        entries.append(
            {
                "label": spec["label"],
                "metric_code": spec["metric_code"],
                "hotel_value": hotel_value,
                "competitor_avg": competitor_avg,
                "competitor_rank": competitor_rank,
                "competitor_count": competitor_count,
                "unit": spec["unit"],
                "connected": any(
                    value is not None
                    for value in (hotel_value, competitor_avg, competitor_rank)
                ),
            }
        )
    return entries


def _has_funnel_data(stages: list[dict[str, Any]]) -> bool:
    return any(
        stage.get("hotel_value") is not None
        or stage.get("competitor_avg") is not None
        for stage in stages
        if isinstance(stage, dict)
    )


def _split_competition_payload(
    combined: dict[str, Any],
    existing_item_three: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    funnel_stages = [
        dict(stage)
        for stage in combined.get("funnel_stages") or []
        if isinstance(stage, dict)
    ]
    competition_metrics = [
        dict(entry)
        for entry in combined.get("competition_metrics") or []
        if isinstance(entry, dict)
    ]
    loss_summary = (
        dict(combined.get("loss_summary") or {})
        if isinstance(combined.get("loss_summary"), dict)
        else {}
    )
    loss_competitors = (
        dict(combined.get("loss_competitors") or {})
        if isinstance(combined.get("loss_competitors"), dict)
        else {"ctrip": [], "qunar": []}
    )

    item_three = {
        "standard_item_id": 3,
        "item_name": "平台流量漏斗分析",
        "participates_in_score": True,
        "full_score": 15,
        "data_status": "success" if _has_funnel_data(funnel_stages) else "missing",
        "source": "待确认",
        "source_path": "携程 eBooking -> 数据中心 -> 流量与转化",
        "fields": [
            {
                "label": stage.get("label"),
                "value": stage.get("hotel_value"),
                "note": "我的酒店 / 竞争圈平均",
            }
            for stage in funnel_stages
        ],
        "fields_complete": True,
        "funnel_stages": funnel_stages,
        "records": list(combined.get("records") or []),
    }
    for key in ("item_score", "diagnosis_score", "score", "current_score"):
        value = combined.get(key)
        if value in (None, "") and isinstance(existing_item_three, dict):
            value = existing_item_three.get(key)
        if value not in (None, ""):
            item_three[key] = value
            break

    has_competition_data = bool(
        any(entry.get("connected") for entry in competition_metrics)
        or loss_summary.get("order_count") is not None
        or loss_summary.get("order_amount") is not None
        or list(loss_competitors.get("ctrip") or [])
        or list(loss_competitors.get("qunar") or [])
    )
    item_five = {
        "standard_item_id": 5,
        "item_name": "竞争圈分析",
        "participates_in_score": False,
        "full_score": 0,
        "item_score": 0,
        "data_status": "success" if has_competition_data else "missing",
        "source": (
            "ctrip_ota_competition_metrics_30d、"
            "ctrip_ota_business_metrics、ctrip_ota_order_loss_monthly"
        ),
        "source_path": "携程 eBooking -> 数据中心 -> 竞争圈动态",
        "fields": [
            {
                "label": entry.get("label"),
                "value": entry.get("competitor_avg"),
                "note": "竞争圈平均 / 排名",
            }
            for entry in competition_metrics
        ],
        "fields_complete": True,
        "competition_metrics": competition_metrics,
        "loss_summary": loss_summary,
        "loss_competitors": loss_competitors,
        "records": list(combined.get("records") or []),
    }
    return item_three, item_five


def _refresh_ctrip_summary(result: dict[str, Any]) -> None:
    items = result.get("ctrip_items")
    if not isinstance(items, dict):
        return
    total_score = 0.0
    full_score = 0.0
    scored_items = 0
    connected_items = 0
    for item in items.values():
        if not isinstance(item, dict):
            continue
        if str(item.get("data_status") or "") == "success":
            connected_items += 1
        if item.get("participates_in_score") is False:
            continue
        maximum = _number(item.get("full_score") or item.get("item_full_score") or item.get("weight"))
        score = None
        for key in ("item_score", "diagnosis_score", "score", "current_score"):
            score = _number(item.get(key))
            if score is not None:
                break
        if maximum is not None:
            full_score += maximum
        if score is not None:
            total_score += score
            scored_items += 1
    summary = {
        "total_score": total_score,
        "full_score": full_score,
        "scored_items": scored_items,
        "connected_items": connected_items,
        "calculation_rule": "sum each scoring item's item_score once; PSI submetrics are diagnostic only",
    }
    result["ctrip_summary"] = summary
    channel_scores = result.setdefault("channel_scores", {})
    if isinstance(channel_scores, dict):
        current = channel_scores.get("ctrip")
        channel_scores["ctrip"] = {**(current if isinstance(current, dict) else {}), **summary, "items": items}


def process(data: dict[str, Any]) -> dict[str, Any]:
    """Preserve established rules and replace only the visual diagnosis layer."""

    result = _base_process(data)
    sections = data.get("sections") or {}
    visual = build_visual_diagnosis(
        sections,
        str(data.get("hotel_name") or ""),
    )
    patch_promotion_performance(visual, sections)
    patch_yesterday_review_count(visual, sections)
    result["visual_diagnosis"] = visual

    ctrip_items = result.setdefault("ctrip_items", {})
    existing_item_three = ctrip_items.get("3") or ctrip_items.get(3)
    combined = build_competition_item(
        sections,
        existing_item_three if isinstance(existing_item_three, dict) else None,
    )
    # Item 05 uses the six confirmed metric codes only. This deliberately
    # replaces the old fuzzy label matching that produced an extra generic
    # "竞争圈排名" row and omitted in-house nights / APP visitors.
    combined["competition_metrics"] = _competition_metric_entries(sections)
    item_three, item_five = _split_competition_payload(
        combined,
        existing_item_three if isinstance(existing_item_three, dict) else None,
    )
    ctrip_items["3"] = item_three
    ctrip_items["5"] = item_five
    ctrip_items["4"] = build_user_profile_item(
        sections.get("ctrip_userprofile_distribution") or []
    )
    ctrip_items["9"] = build_promotion_item(sections)
    ctrip_items["10"] = build_page_entry_item(sections)
    psi_item = build_psi_item(sections)
    ctrip_items["6"] = psi_item
    result["ctrip_psi"] = psi_item
    ctrip_items["12"] = build_reputation_item(sections)
    ctrip_items["11"] = build_room_name_item(sections)
    ctrip_items.update(build_configuration_items(sections))
    _refresh_ctrip_summary(result)
    return result


__all__ = ["process"]
