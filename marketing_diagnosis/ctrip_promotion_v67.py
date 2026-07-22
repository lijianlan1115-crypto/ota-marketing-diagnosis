from __future__ import annotations

from typing import Any


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: str(row.get("snapshot_time") or row.get("period_end_date") or ""),
    )


def _money(value: float | None) -> str:
    return "待接入" if value is None else f"¥{value:,.2f}"


def _roi(row: dict[str, Any], spend: float | None) -> float | None:
    value = _number(row.get("return_on_ad_spend"))
    if value is not None:
        return value
    amount = _number(row.get("booking_order_amount"))
    return amount / spend if amount is not None and spend not in (None, 0) else None


def _score(spend: float | None, roi: float | None) -> float | None:
    if spend is None or roi is None:
        return None
    if spend < 1000 or roi < 5:
        return 0.0
    return 8.0 if roi >= 10 else 4.8


def build_promotion_item(sections: dict[str, Any]) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in sections.get("ctrip_promotion_performance_30d") or []
        if isinstance(row, dict)
    ]
    row = _latest(rows)
    source = "ctrip_ota_promotion_performance_30d"
    if row is None:
        return {
            "standard_item_id": 9,
            "participates_in_score": True,
            "item_score": None,
            "data_status": "missing",
            "source": source,
            "fields_complete": True,
            "fields": [],
            "note": "等待携程近30天金字塔推广快照。",
        }

    spend = _number(row.get("spend_amount"))
    roi = _roi(row, spend)
    score = _score(spend, roi)
    fields = [
        {"label": "推广投入", "value": _money(spend)},
        {"label": "推广曝光", "value": _number(row.get("exposure_count"))},
        {"label": "推广点击", "value": _number(row.get("click_count"))},
        {"label": "推广订单", "value": _number(row.get("booking_order_count"))},
        {"label": "推广订单金额", "value": _money(_number(row.get("booking_order_amount")))},
        {"label": "ROI", "value": None if roi is None else f"{roi:.2f}"},
    ]
    if score is None:
        status, note = "pending_rule", "推广投入或ROI缺失，暂无法计算得分。"
    elif spend is not None and spend < 1000:
        status, note = "success", "近30天推广投入低于1000元，本项得0分。"
    elif roi is not None and roi >= 10:
        status, note = "success", "ROI达到10及以上，本项得8分。"
    elif roi is not None and roi >= 5:
        status, note = "success", "ROI介于5至10之间，本项得4.8分。"
    else:
        status, note = "success", "ROI低于5，本项得0分。"
    return {
        "standard_item_id": 9,
        "participates_in_score": True,
        "item_score": score,
        "data_status": status,
        "source": source,
        "fields_complete": True,
        "fields": fields,
        "note": note,
    }


__all__ = ["build_promotion_item"]
