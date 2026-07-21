from __future__ import annotations

from typing import Any

from marketing_diagnosis.ctrip_competition import build_competition_item
from marketing_diagnosis.ctrip_configuration_v63 import build_configuration_items
from marketing_diagnosis.ctrip_page_entry_v66 import build_page_entry_item
from marketing_diagnosis.ctrip_reputation_v64 import build_reputation_item
from marketing_diagnosis.ctrip_room_name_v65 import build_room_name_item
from marketing_diagnosis.ctrip_user_profile_v58 import build_user_profile_item
from marketing_diagnosis.promotion_performance_v46 import patch_promotion_performance
from marketing_diagnosis.review_yesterday_v45 import patch_yesterday_review_count
from marketing_diagnosis.rules_v4 import process as _base_process
from marketing_diagnosis.visual_diagnosis_v20 import build_visual_diagnosis


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
        competition_metrics
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
        "source": "待确认",
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
    item_three, item_five = _split_competition_payload(
        combined,
        existing_item_three if isinstance(existing_item_three, dict) else None,
    )
    ctrip_items["3"] = item_three
    ctrip_items["5"] = item_five
    ctrip_items["4"] = build_user_profile_item(
        sections.get("ctrip_userprofile_distribution") or []
    )
    ctrip_items["10"] = build_page_entry_item(sections)
    ctrip_items["12"] = build_reputation_item(sections)
    ctrip_items["11"] = build_room_name_item(sections)
    ctrip_items.update(build_configuration_items(sections))
    return result


__all__ = ["process"]
