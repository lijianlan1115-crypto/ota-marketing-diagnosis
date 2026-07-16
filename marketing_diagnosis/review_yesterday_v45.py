from __future__ import annotations

from typing import Any


SOURCE_TABLE = "hotel_puyue.meituan_ota_review_detail"
SOURCE_RULE = "DATE(review_time)=DATE_SUB(CURDATE(), INTERVAL 1 DAY)"


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _meituan_overview(
    sections: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    rows = [
        row
        for row in list(sections.get("review_overviews") or [])
        if isinstance(row, dict)
        and str(row.get("platform") or row.get("review_platform") or "").lower()
        in {"meituan", "美团"}
    ]
    if not rows:
        return {}
    return max(
        rows,
        key=lambda row: str(row.get("snapshot_time") or row.get("updated_at") or ""),
    )


def patch_yesterday_review_count(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    """Add the exact MySQL-yesterday review count to visual item 13."""

    item = _item(result, 13)
    if item is None:
        return

    row = _meituan_overview(sections)
    count = row.get("yesterday_new_review_count")
    target_date = str(row.get("yesterday_review_date") or "")[:10]

    fields = [
        field
        for field in list(item.get("fields") or [])
        if str(field.get("label") or "") != "昨日新增点评数"
    ]
    yesterday_field = {
        "label": "昨日新增点评数",
        "value": count,
        "origin": "数据库条件计数",
        "note": (
            f"统计日期：{target_date}；{SOURCE_RULE}"
            if target_date
            else SOURCE_RULE
        ),
    }

    insert_at = next(
        (
            index + 1
            for index, field in enumerate(fields)
            if "美团" in str(field.get("label") or "")
            and "点评" in str(field.get("label") or "")
            and ("条数" in str(field.get("label") or "") or "数量" in str(field.get("label") or ""))
        ),
        min(2, len(fields)),
    )
    fields.insert(insert_at, yesterday_field)
    item["fields"] = fields
    item["source_table"] = (
        "hotel_puyue.meituan_ota_review_overview + " + SOURCE_TABLE
    )
    source_fields = list(item.get("source_fields") or [])
    for value in ("review_time", "COUNT(*)", SOURCE_RULE):
        if value not in source_fields:
            source_fields.append(value)
    item["source_fields"] = source_fields
    item["yesterday_review_date"] = target_date or None
    item["yesterday_new_review_count"] = count

    existing_note = str(item.get("note") or "").strip()
    count_note = (
        f"昨日新增点评数按{target_date}的review_time记录统计，共{int(count)}条。"
        if count is not None and target_date
        else "昨日新增点评数按review_time的日期部分统计；当前未取得计数结果。"
    )
    item["note"] = (existing_note + " " + count_note).strip()


__all__ = [
    "SOURCE_RULE",
    "SOURCE_TABLE",
    "patch_yesterday_review_count",
]
