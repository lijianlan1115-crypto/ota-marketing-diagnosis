from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _status_score


PROMOTION_CODE = "reservation_invoice"
PROMOTION_NAME = "预约发票"
SOURCE_TABLE = "hotel_puyue.meituan_ota_promotion_status"


def _text(value: Any) -> str:
    return "" if value in (None, "") else str(value).strip()


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return max(
        enumerate(rows),
        key=lambda pair: (
            str(pair[1].get("snapshot_time") or ""),
            str(pair[1].get("updated_at") or ""),
            str(pair[1].get("created_at") or ""),
            pair[0],
        ),
    )[1]


def _source_row(sections: dict[str, Any]) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in sections.get("promotion_status") or []
        if isinstance(row, dict)
    ]
    code_matches = [
        row
        for row in rows
        if _text(row.get("promotion_code")).lower() == PROMOTION_CODE
    ]
    exact_matches = [
        row for row in code_matches if _text(row.get("promotion_name")) == PROMOTION_NAME
    ]
    name_matches = [
        row for row in rows if _text(row.get("promotion_name")) == PROMOTION_NAME
    ]
    return _latest(exact_matches or code_matches or name_matches)


def _item(result: dict[str, Any]) -> dict[str, Any] | None:
    visual = result.get("visual_diagnosis")
    if not isinstance(visual, dict):
        return None
    return next(
        (
            item
            for item in visual.get("items") or []
            if isinstance(item, dict)
            and int(item.get("standard_item_id") or 0) == 20
        ),
        None,
    )


def patch_reservation_invoice(
    result: dict[str, Any],
    sections: dict[str, Any],
) -> None:
    """Use the confirmed reservation-invoice code and name for Meituan item 20."""

    item = _item(result)
    if item is None:
        return

    item["item_name"] = PROMOTION_NAME
    item["source_table"] = SOURCE_TABLE
    item["source_fields"] = [
        "promotion_code=reservation_invoice",
        "promotion_name=预约发票",
        "status",
        "enroll_status/registration_status",
        "effective_status",
    ]

    row = _source_row(sections)
    if not row:
        item["data_status"] = "missing"
        item["score_ratio"] = None
        item["item_score"] = None
        item["fields"] = [
            {
                "label": "开通状态",
                "value": None,
                "note": "未匹配 promotion_code=reservation_invoice、promotion_name=预约发票",
                "origin": "数据库筛选",
            }
        ]
        item["note"] = (
            "第20项为预约发票；当前未取得 promotion_code=reservation_invoice "
            "或 promotion_name=预约发票 的状态记录。"
        )
        return

    status, ratio, meaning = _status_score(row)
    item["data_status"] = status
    item["score_ratio"] = ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 2) * ratio, 2)
        if ratio is not None
        else None
    )
    item["fields"] = [
        {
            "label": "活动编码",
            "value": row.get("promotion_code"),
            "note": "应为 reservation_invoice",
            "origin": "数据库原值",
        },
        {
            "label": "活动名称",
            "value": row.get("promotion_name"),
            "note": "应为预约发票",
            "origin": "数据库原值",
        },
        {
            "label": "开通状态",
            "value": row.get("status") or row.get("open_status"),
            "note": "预约发票当前开通状态",
            "origin": "数据库原值",
        },
        {
            "label": "报名状态",
            "value": row.get("enroll_status") or row.get("registration_status"),
            "note": "预约发票报名状态",
            "origin": "数据库原值",
        },
        {
            "label": "生效状态",
            "value": row.get("effective_status"),
            "note": "预约发票生效状态",
            "origin": "数据库原值",
        },
        {
            "label": "状态含义",
            "value": meaning,
            "note": "沿用配置状态评分规则",
            "origin": "规则计算",
        },
    ]
    item["note"] = (
        "第20项为预约发票；优先按 promotion_code=reservation_invoice 匹配，"
        "promotion_name=预约发票用于名称核验。OPEN得2分，CLOSED得0分，"
        "PENDING或状态缺失保持待计算。"
    )


__all__ = [
    "PROMOTION_CODE",
    "PROMOTION_NAME",
    "patch_reservation_invoice",
]
