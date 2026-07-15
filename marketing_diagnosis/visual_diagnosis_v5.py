from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v4 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


_DAILY_PERIODS = {"日", "daily", "day", "当日"}


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _meituan_rows(sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        row
        for row in sections.get("ota_funnel") or []
        if str(row.get("platform") or "").strip().lower() == "meituan"
    ]


def _latest_hos_row_per_day(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = [row for row in rows if _n(row.get("hos_score")) is not None]
    daily = [
        row
        for row in scored
        if str(row.get("period_type") or "").strip().lower() in _DAILY_PERIODS
    ]
    candidates = daily or scored

    latest: dict[str, tuple[tuple[str, str, str, int], dict[str, Any]]] = {}
    for index, row in enumerate(candidates):
        day = str(row.get("business_date") or "")[:10]
        if not day:
            continue
        sort_key = (
            str(row.get("snapshot_time") or ""),
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            index,
        )
        current = latest.get(day)
        if current is None or sort_key >= current[0]:
            latest[day] = (sort_key, row)

    return [latest[day][1] for day in sorted(latest)[-30:]]


def _rank_value(row: dict[str, Any]) -> Any:
    for key in ("hos_score_rank_raw", "hos_score_rank"):
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _patch_hos_presence_score(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 6)
    if not item:
        return

    all_meituan = _meituan_rows(sections)
    rows = _latest_hos_row_per_day(all_meituan)
    has_score = bool(rows)
    latest = rows[-1] if rows else {}
    values = [_n(row.get("hos_score")) for row in rows]
    clean_values = [value for value in values if value is not None]
    average = sum(clean_values) / len(clean_values) if clean_values else None

    if has_score:
        item["data_status"] = "success"
        item["score_ratio"] = 1.0
        item["item_score"] = float(item.get("base_score") or 3)
    elif all_meituan:
        item["data_status"] = "zero"
        item["score_ratio"] = 0.0
        item["item_score"] = 0.0
    else:
        item["data_status"] = "missing"
        item["score_ratio"] = None
        item["item_score"] = None

    display_range = (
        f"{str(rows[0].get('business_date') or '')[:10]} 至 "
        f"{str(rows[-1].get('business_date') or '')[:10]}"
        if rows
        else None
    )
    fields: list[dict[str, Any]] = [
        {
            "label": "展示范围",
            "value": display_range,
            "note": "数据库可用的最近30个HOS评分日期",
            "origin": "区间统计",
        },
        {
            "label": "是否有HOS评分",
            "value": "有" if has_score else ("无" if all_meituan else None),
            "note": "存在至少一条有效 hos_score 即判定为有评分",
            "origin": "存在性判断",
        },
        {
            "label": "有效评分天数",
            "value": len(rows) if rows else (0 if all_meituan else None),
            "note": "按 business_date 去重后的有效 HOS 评分天数",
            "origin": "区间统计",
        },
        {
            "label": "最新HOS分",
            "value": _n(latest.get("hos_score")),
            "note": "最近一个有评分日期的 HOS 分数",
            "origin": "数据库最新值",
        },
        {
            "label": "近30天平均分",
            "value": average,
            "note": "仅用于趋势展示，不参与本项评分",
            "origin": "公式计算",
        },
        {
            "label": "最新同行排名",
            "value": _rank_value(latest),
            "note": "最近一个有评分日期的同行排名",
            "origin": "数据库最新值",
        },
    ]
    for row in rows:
        rank = _rank_value(row)
        fields.append(
            {
                "label": str(row.get("business_date") or "")[:10],
                "value": _n(row.get("hos_score")),
                "note": f"同行排名：{rank if rank not in (None, '') else '暂无'}",
                "origin": "数据库日值",
            }
        )

    item["fields"] = fields
    item["note"] = (
        "客户确认口径：HOS只判断是否存在有效评分记录；有评分即得满分3分，"
        "明确无评分记0分。HOS分数、平均分和同行排名仅用于趋势展示，不再参与评分阈值判断。"
    )


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_hos_presence_score(result, sections)
    result["rule_version"] = "2026-07-15-v6-hos-presence"
    return result


__all__ = ["build_visual_diagnosis"]
