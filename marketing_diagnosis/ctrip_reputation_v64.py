from __future__ import annotations

from typing import Any


PLATFORMS = (
    ("ctrip", "携程", 5.0),
    ("qunar", "去哪儿", 3.0),
    ("tongcheng", "同程旅行", 1.0),
    ("zhixing", "智行", 1.0),
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return None if number is None else int(number)


def platform_key(row: dict[str, Any]) -> str | None:
    value = _text(row.get("platform_scope") or row.get("channel_source")).lower()
    aliases = {
        "ctrip": "ctrip", "携程": "ctrip", "xiecheng": "ctrip",
        "qunar": "qunar", "去哪儿": "qunar", "去哪兒": "qunar",
        "tongcheng": "tongcheng", "同程": "tongcheng", "同程旅行": "tongcheng",
        "zhixing": "zhixing", "智行": "zhixing",
    }
    return aliases.get(value)


def _latest(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = platform_key(row)
        if not key:
            continue
        current = selected.get(key)
        if current is None or _text(row.get("snapshot_time")) >= _text(current.get("snapshot_time")):
            selected[key] = dict(row)
    return selected


def _score(rating: float | None, weight: float) -> float | None:
    if rating is None:
        return None
    if rating >= 4.7:
        return weight
    if rating >= 4.5:
        return weight * 0.8
    return 0.0


def _reply_rate(total: int | None, unreplied: int | None) -> float | None:
    if total is None or total <= 0 or unreplied is None:
        return None
    return max(0.0, min(1.0, (total - unreplied) / total))


def build_reputation_item(sections: dict[str, Any]) -> dict[str, Any]:
    overview_rows = [
        dict(row)
        for row in sections.get("ctrip_review_overview") or []
        if isinstance(row, dict)
    ]
    if not overview_rows:
        overview_rows = [
            dict(row)
            for row in sections.get("review_overviews") or []
            if isinstance(row, dict) and platform_key(row)
        ]
    yesterday_rows = [
        dict(row)
        for row in sections.get("ctrip_review_yesterday") or []
        if isinstance(row, dict)
    ]
    yesterday = _latest(yesterday_rows)
    overview = _latest(overview_rows)

    platforms: list[dict[str, Any]] = []
    scores: list[float] = []
    for key, name, weight in PLATFORMS:
        row = overview.get(key)
        if row is None:
            platforms.append(
                {
                    "platform_key": key,
                    "platform_name": name,
                    "full_score": weight,
                    "data_status": "missing",
                }
            )
            continue
        rating = _number(row.get("review_score"))
        review_count = _integer(row.get("total_review_count"))
        unreplied = _integer(row.get("unreplied_review_count"))
        score = _score(rating, weight)
        if score is not None:
            scores.append(score)
        platforms.append(
            {
                "platform_key": key,
                "platform_name": name,
                "full_score": weight,
                "data_status": "success",
                "rating": rating,
                "score": score,
                "review_count": review_count,
                "yesterday_new_review_count": yesterday.get(key, {}).get("yesterday_new_review_count"),
                "unreplied_review_count": unreplied,
                "reply_rate": _reply_rate(review_count, unreplied),
                "negative_review_count": _integer(row.get("negative_review_count")),
                "environment_score": _number(row.get("environment_score")),
                "facility_score": _number(row.get("facility_score")),
                "service_score": _number(row.get("service_score")),
                "hygiene_score": _number(row.get("hygiene_score")),
                "style_score": _number(row.get("style_score")),
                "safety_score": _number(row.get("safety_score")),
            }
        )

    return {
        "standard_item_id": 12,
        "participates_in_score": True,
        "item_score": round(sum(scores), 2) if scores else None,
        "data_status": "success" if overview else "missing",
        "source": "携程 eBooking / 点评问答 / 订单点评",
        "fields_complete": True,
        "platforms": platforms,
        "note": "平台满分：携程5分、去哪儿3分、同程旅行1分、智行1分；点评分>=4.7得满分，4.5-4.7得80%，低于4.5得0分。",
    }


__all__ = ["PLATFORMS", "build_reputation_item", "platform_key"]
