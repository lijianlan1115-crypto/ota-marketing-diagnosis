from __future__ import annotations

from typing import Any


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def refresh_meituan_summary(result: dict[str, Any]) -> None:
    """Make the Meituan channel total the direct sum of scoring items.

    Display-only items are excluded. A scoring item with missing data remains
    unscored and is not silently converted to zero.
    """

    visual = result.get("visual_diagnosis")
    if not isinstance(visual, dict):
        return

    items = [item for item in visual.get("items") or [] if isinstance(item, dict)]
    scoring_items = [item for item in items if item.get("participates_in_score") is not False]

    total_score = 0.0
    scored_items = 0
    for item in scoring_items:
        score = _number(item.get("item_score"))
        if score is None:
            continue
        total_score += score
        scored_items += 1

    full_score = sum(_number(item.get("base_score")) or 0.0 for item in scoring_items)
    total_score = round(total_score, 2)
    full_score = round(full_score, 2)
    scoring_count = len(scoring_items)
    pending_count = scoring_count - scored_items

    summary = {
        "total_score": total_score,
        "full_score": full_score,
        "scoring_items": scoring_count,
        "scored_items": scored_items,
        "pending_items": pending_count,
        "calculation_rule": "sum each participates_in_score item's item_score once",
    }

    visual.update(summary)
    # Keep legacy keys available to older renderers, but no longer perform a
    # connected-base normalization. normalized_score is now an alias of total.
    visual["raw_score"] = total_score
    visual["normalized_score"] = total_score
    visual["connected_base_score"] = full_score

    result["meituan_summary"] = summary
    channel_scores = result.setdefault("channel_scores", {})
    if isinstance(channel_scores, dict):
        current = channel_scores.get("meituan")
        channel_scores["meituan"] = {
            **(current if isinstance(current, dict) else {}),
            **summary,
            "items": items,
        }


__all__ = ["refresh_meituan_summary"]
