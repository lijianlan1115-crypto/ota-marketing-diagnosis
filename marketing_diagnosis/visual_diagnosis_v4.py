from __future__ import annotations

from collections import defaultdict
from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v3 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


_SOURCE_FIELDS = [
    "business_date",
    "room_type_name",
    "room_type_id",
    "pms_rate_room_type_id",
    "room_nights",
    "occupancy_rate",
    "room_revenue",
    "adr",
    "revpar",
    "snapshot_time",
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


def _room_identity(row: dict[str, Any]) -> str:
    for key in ("room_type_id", "pms_rate_room_type_id", "room_type_name"):
        value = str(row.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    return ""


def _dedupe_daily_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], tuple[tuple[str, str, str, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        day = str(row.get("business_date") or "")[:10]
        room_key = _room_identity(row)
        if not day or not room_key:
            continue
        sort_key = (
            str(row.get("snapshot_time") or ""),
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            index,
        )
        key = (day, room_key)
        current = latest.get(key)
        if current is None or sort_key >= current[0]:
            latest[key] = (sort_key, row)
    return [latest[key][1] for key in sorted(latest)]


def _average(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [_n(row.get(key)) for row in rows]
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else None


def _patch_room_type_performance(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 2)
    if not item:
        return

    rows = _dedupe_daily_rows(sections.get("room_type_performance_daily") or [])
    latest_day = max(
        (str(row.get("business_date") or "")[:10] for row in rows),
        default="",
    )
    latest_rows = [
        row for row in rows
        if str(row.get("business_date") or "")[:10] == latest_day
    ]

    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        room_key = _room_identity(row)
        if room_key:
            history[room_key].append(row)

    records: list[dict[str, Any]] = []
    for row in sorted(
        latest_rows,
        key=lambda value: (
            str(value.get("room_type_id") or ""),
            str(value.get("pms_rate_room_type_id") or ""),
            str(value.get("room_type_name") or ""),
        ),
    ):
        room_key = _room_identity(row)
        room_history = history.get(room_key) or [row]
        occupancy_month = _average(room_history, "occupancy_rate")
        revpar_month = _average(room_history, "revpar")
        records.append(
            {
                "room_type_id": row.get("room_type_id"),
                "pms_rate_room_type_id": row.get("pms_rate_room_type_id"),
                "room_type_name": row.get("room_type_name"),
                "business_date": latest_day,
                "period_days_with_data": len(
                    {
                        str(value.get("business_date") or "")[:10]
                        for value in room_history
                        if str(value.get("business_date") or "")[:10]
                    }
                ),
                "occupancy_day": _n(row.get("occupancy_rate")),
                "revpar_day": _n(row.get("revpar")),
                "occupancy_month": occupancy_month,
                "revpar_month": revpar_month,
                "room_nights_day": _n(row.get("room_nights")),
                "room_revenue_day": _n(row.get("room_revenue")),
                "adr_day": _n(row.get("adr")),
            }
        )

    low_rooms = [
        record
        for record in records
        if record.get("occupancy_month") is not None
        and float(record["occupancy_month"]) < 60
    ]
    missing_rooms = [
        record
        for record in records
        if record.get("occupancy_month") is None
    ]
    room_count = len(records) or None
    low_count = len(low_rooms) if records else None
    low_ratio = None if not room_count else low_count / room_count

    item["fields"] = [
        {
            "label": "低效房型数",
            "value": low_count,
            "note": "统计区间日均出租率低于60%的房型数",
            "origin": "条件统计",
        },
        {
            "label": "在售房型数",
            "value": room_count,
            "note": f"最新营业日期 {latest_day or '暂无'} 的房型数",
            "origin": "按房型去重统计",
        },
        {
            "label": "低效房型占比",
            "value": low_ratio,
            "note": "低效房型数 ÷ 在售房型数",
            "origin": "公式计算",
        },
        {
            "label": "低效房型清单",
            "value": "、".join(
                str(record.get("room_type_name") or "")
                for record in low_rooms
                if str(record.get("room_type_name") or "")
            ) or None,
            "note": (
                f"{len(missing_rooms)}个房型缺少出租率"
                if missing_rooms else "按近30天日均出租率判定"
            ),
            "origin": "条件统计",
        },
    ]
    item["records"] = records
    item["source_table"] = "hotel_puyue.jl01_room_type_performance_daily"
    item["source_fields"] = list(_SOURCE_FIELDS)
    item["data_status"] = "success" if records else "missing"
    item["score_ratio"] = None
    item["item_score"] = None
    item["note"] = (
        "JL01按宽表读取：当日直接取最新 business_date 的 occupancy_rate 和 revpar；"
        "近30天指标按请求区间内 business_date + 房型去重后的日值求平均；"
        "同一天同一房型存在多次采集时保留最新 snapshot_time。"
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_room_type_performance(result, sections)
    result["rule_version"] = "2026-07-14-v5-jl01-wide"
    return result


__all__ = ["build_visual_diagnosis"]
