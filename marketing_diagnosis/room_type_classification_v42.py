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


def _score_ratio(low_ratio: float) -> float:
    if low_ratio < 0.10:
        return 1.0
    if low_ratio <= 0.30:
        return 0.60
    return 0.0


def _apply_score(item: dict[str, Any], score_ratio: float) -> None:
    item["participates_in_score"] = True
    item["score_ratio"] = score_ratio
    item["item_score"] = round(float(item.get("base_score") or 8) * score_ratio, 2)
    item["data_status"] = "success" if score_ratio > 0 else "zero"


def patch_room_type_summary(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    """Replace item 02 with JL11 near-30-day values and always form a score.

    Low-efficiency rooms are room types whose near-30-day occupancy rate is below
    60%. The denominator is every distinct on-sale room type in ``section=summary``.
    Missing JL11 rows are scored zero instead of dropping item 02 from the total.
    """

    item = _item(result, 2)
    if item is None:
        return

    rows = _latest_summary_rows(list(sections.get("room_type_performance_daily") or []))
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

    total_room_types = len(records)
    low_records = [record for record in records if record["is_low"]]
    missing_occupancy = [
        record for record in records if record["occupancy_points"] is None
    ]
    low_ratio = len(low_records) / total_room_types if total_room_types else None

    if low_ratio is None:
        _apply_score(item, 0.0)
    else:
        _apply_score(item, _score_ratio(low_ratio))

    item["records"] = records
    item["fields"] = [
        {
            "label": "全部在售房型数",
            "value": total_room_types,
            "origin": "按room_type_name去重",
            "note": "section=summary中的全部不同房型数量",
        },
        {
            "label": "房间总数",
            "value": sum(record["room_count"] or 0 for record in records),
            "origin": "区间汇总",
            "note": "各房型room_count合计",
        },
        {
            "label": "低效房型数",
            "value": len(low_records),
            "origin": "条件统计",
            "note": "最近一个月occupancy_rate低于60%的房型数量",
        },
        {
            "label": "低效房型占比",
            "value": low_ratio,
            "origin": "公式计算",
            "note": "低效房型数÷全部在售房型数",
        },
        {
            "label": "低效房型清单",
            "value": "、".join(record["room_type_name"] for record in low_records) or None,
            "origin": "条件统计",
            "note": "最近一个月出租率低于60%的房型",
        },
        {
            "label": "出租率缺失房型数",
            "value": len(missing_occupancy),
            "origin": "数据质量检查",
            "note": "仍计入全部在售房型数，但不判定为低效房型",
        },
    ]
    item["source_table"] = SOURCE_TABLE
    item["source_fields"] = SOURCE_FIELDS

    if not records:
        item["note"] = (
            "本项必须评分：未取得jl11_room_type_classification中section=summary记录，"
            "按0分计入总分。低效房型定义为最近一个月出租率<60%；"
            "低效房型占比=低效房型数÷全部在售房型数。"
        )
    else:
        item["note"] = (
            "本项必须评分。全部数据取hotel_puyue.jl11_room_type_classification中"
            "section=summary的近30天汇总值；低效房型为最近一个月出租率<60%；"
            "低效房型占比=低效房型数÷全部在售房型数。占比<10%得满分，"
            "10%至30%得60%，超过30%得0分。"
        )


__all__ = [
    "SOURCE_FIELDS",
    "SOURCE_TABLE",
    "_latest_summary_rows",
    "_occupancy_points",
    "patch_room_type_summary",
]
