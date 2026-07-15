from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v7 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _field_value(item: dict[str, Any], label: str) -> Any:
    for field in item.get("fields") or []:
        if str(field.get("label") or "") == label:
            return field.get("value")
    return None


def _review_score_ratio(score: Any) -> float | None:
    """Apply the documented reputation-score thresholds exactly."""
    value = _n(score)
    if value is None:
        return None
    if value > 4.9:
        return 1.0
    if value >= 4.7:
        return 0.8
    return 0.0


def _patch_review_score(result: dict[str, Any]) -> None:
    item = _item(result, 13)
    if not item:
        return

    meituan_score = _n(_field_value(item, "美团评分"))
    dianping_score = _n(_field_value(item, "大众点评评分"))

    # The handbook explicitly treats Dianping as a sub-field but does not define
    # any averaging/weighting rule. Use the Meituan score as the primary scoring
    # value and only fall back to Dianping when Meituan is absent. This avoids
    # inventing an undocumented cross-platform aggregation formula.
    if meituan_score is not None:
        scoring_score = meituan_score
        scoring_source = "美团评分"
    elif dianping_score is not None:
        scoring_score = dianping_score
        scoring_source = "大众点评评分（美团评分缺失时备用）"
    else:
        scoring_score = None
        scoring_source = "无可用点评分"

    ratio = _review_score_ratio(scoring_score)
    item["score_ratio"] = ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 10) * ratio, 2)
        if ratio is not None
        else None
    )
    item["data_status"] = "success" if ratio is not None else "missing"
    item["note"] = (
        f"本项按{scoring_source}计分；大众点评评分作为口碑分析子字段展示。"
        "严格采用手册阈值：点评分>4.9得10分；4.7≤点评分≤4.9得8分；"
        "点评分<4.7得0分。未定义两平台平均或加权规则，因此不自行合并。"
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_review_score(result)
    result["rule_version"] = "2026-07-15-v9-review-score-handbook"
    return result


__all__ = ["_review_score_ratio", "build_visual_diagnosis"]
