from __future__ import annotations

from typing import Any

from marketing_diagnosis import ctrip_flow as upstream


_COUNT_FIELD = "competition_circle_hotel_count"


def _strict_rank_count_sections(sections: dict[str, Any]) -> dict[str, Any]:
    """Make rank scoring use only competition_circle_hotel_count.

    Older payloads may contain several similarly named hotel-count fields or a
    combined ``rank/count`` string. Those values must not participate in item 03
    because the confirmed competition-circle hotel total is stored in
    ``competition_circle_hotel_count``.
    """

    normalized = dict(sections or {})
    rows: list[dict[str, Any]] = []
    for source in sections.get("ctrip_business_metrics_funnel") or []:
        if not isinstance(source, dict):
            continue
        row = dict(source)

        for alias in upstream._COUNT_ALIASES:
            if alias != _COUNT_FIELD:
                row.pop(alias, None)

        # Prevent the legacy rank/count text fallback. The denominator must
        # come from competition_circle_hotel_count only.
        for _, rank_key in upstream._RANK_METRICS:
            raw_rank = row.get(rank_key)
            if isinstance(raw_rank, str) and "/" in raw_rank:
                row[rank_key] = raw_rank.split("/", 1)[0].strip()

        rows.append(row)

    normalized["ctrip_business_metrics_funnel"] = rows
    return normalized


def build_flow_item(
    sections: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = upstream.build_flow_item(
        _strict_rank_count_sections(sections),
        existing,
    )
    scoring_rule = item.setdefault("scoring_rule", {})
    scoring_rule["rank_count_field"] = _COUNT_FIELD
    scoring_rule["rank"] = (
        "rank_percentile = 1-(排名-1)/competition_circle_hotel_count；"
        ">=80%得100%，>=60%得80%，>=40%得60%，<40%得0%"
    )
    return item


__all__ = ["build_flow_item"]
