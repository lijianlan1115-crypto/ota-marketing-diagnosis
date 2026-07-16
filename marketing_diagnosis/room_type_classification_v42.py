from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n

SOURCE_TABLE = "hotel_puyue.jl11_room_type_classification"
SOURCE_FIELDS = [
    "section=summary",
    "room_type_name",
    "room_count",
    "room_nights",
    "occupancy_rate",
    "room_revenue",
    "average_room_price",
    "revpar",
]


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _occupancy_points(value: Any) -> float | None:
    number = _n(value)
    if number is None:
        return None
    return number * 100 if abs(number) <= 1 else number


def _latest_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, tuple[tuple[str, str, str, int, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        if str(row.get("section") or "").strip().lower() != "summary":
            continue
        room_name = str(row.get("room_type_name") or "").strip()
        if not room_name:
            continue
        try:
            row_id = int(row.get("id") or 0)
        except (TypeError, ValueError):
            row_id = 0
        order_key = (
            str(row.get("snapshot_time") or ""),
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            row_id,
            index,
        )
        current = selected.get(room_name)
        if current is None or order_key >= current[0]:
            selected[room_name] = (order_key, row)
    return [selected[name][1] for name in sorted(selected)]


def _score_ratio(low_ratio: float | None) -> float | None:
    if low_ratio is None:
        return None
    if low_ratio < 0.10:
        return 1.0
    if low_ratio <= 0.30:
        return 0.60
    return 0.0


def patch_room_type_summary(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    """Replace item 02 with JL11 ``section=summary`` near-30-day values.

    Excel and legacy JL01 rows are left unchanged because they do not carry the
    JL11 ``section=summary`` marker.
    """

    item = _item(result, 2)
    if item is None:
        return

    rows = _latest_summary_rows(list(sections.get("room_type_performance_daily") or []))
    if not rows:
        return

    records: list[dict[str, Any]] = []
    for row in rows:
        occupancy = _n(row.get("occupancy_rate"))
        occupancy_points = _occupancy_points(occupancy)
        records.append(
            {
                "room_type_name": str(row.get("room_type_name") or "").strip(),
                "room_count": _n(row.get("room_count")),
                "room_nights": _n(row.get("room_nights")),
                "occupancy_rate": occupancy,
                "occupancy_points": occupancy_points,
                "room_revenue": _n(row.get("room_revenue")),
                "average_room_price": _n(row.get("average_room_price")),
                "revpar": _n(row.get("revpar")),
                "is_low": occupancy_points is not None and occupancy_points < 60,
            }
        )

    valid_records = [record for record in records if record["occupancy_points"] is not None]
    low_records = [record for record in valid_records if record["is_low"]]
    low_ratio = len(low_records) / len(valid_records) if valid_records else None
    score_ratio = _score_ratio(low_ratio)

    item["data_status"] = (
        "missing" if score_ratio is None else "success" if score_ratio > 0 else "zero"
    )
    item["score_ratio"] = score_ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 0) * score_ratio, 2)
        if score_ratio is not None
        else None
    )
    item["records"] = records
    item["fields"] = [
        {
            "label": "房型数",
            "value": len(records),
            "origin": "按room_type_name去重",
            "note": "section=summary中的不同房型数量",
        },
        {
            "label": "房间总数",
            "value": sum(record["room_count"] or 0 for record in records),
            "origin": "区间汇总",
            "note": "各房型room_count合计",
        },
        {
            "label": "低效房型数",
            "value": len(low_records) if valid_records else None,
            "origin": "条件统计",
            "note": "近30天occupancy_rate低于60%的房型数",
        },
        {
            "label": "低效房型占比",
            "value": low_ratio,
            "origin": "公式计算",
            "note": "低效房型数÷有出租率数据的房型数",
        },
        {
            "label": "低效房型清单",
            "value": "、".join(record["room_type_name"] for record in low_records) or None,
            "origin": "条件统计",
            "note": "occupancy_rate低于60%的房型",
        },
    ]
    item["source_table"] = SOURCE_TABLE
    item["source_fields"] = SOURCE_FIELDS
    item["note"] = (
        "全部数据直接取hotel_puyue.jl11_room_type_classification中section=summary的近30天汇总值；"
        "按room_type_name展示room_count、room_nights、occupancy_rate、room_revenue、"
        "average_room_price和revpar。低效房型为出租率低于60%；低效房型占比<10%得满分，"
        "10%至30%得60%，超过30%得0分。"
    )


__all__ = [
    "SOURCE_FIELDS",
    "SOURCE_TABLE",
    "_latest_summary_rows",
    "_occupancy_points",
    "patch_room_type_summary",
]
