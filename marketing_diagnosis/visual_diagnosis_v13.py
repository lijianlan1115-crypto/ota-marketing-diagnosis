from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis_v12 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


CROWN_SCORES = {
    "黑金挂冠": 1.0,
    "普通挂冠": 0.5,
    "无挂冠": 0.0,
}


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _latest_manual(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return max(
        enumerate(rows),
        key=lambda pair: (str(pair[1].get("recorded_at") or ""), pair[0]),
    )[1]


def _recalculate_totals(result: dict[str, Any]) -> None:
    items = list(result.get("items") or [])
    raw_score = round(
        sum(float(item.get("item_score")) for item in items if item.get("item_score") is not None),
        2,
    )
    connected_base = round(
        sum(
            float(item.get("base_score") or 0)
            for item in items
            if item.get("participates_in_score") and item.get("item_score") is not None
        ),
        2,
    )
    result["raw_score"] = raw_score
    result["connected_base_score"] = connected_base
    result["normalized_score"] = (
        round(raw_score / connected_base * 100, 2) if connected_base else None
    )


def _patch_manual_crown(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 22)
    if not item:
        return

    row = _latest_manual(list(sections.get("manual_inputs") or []))
    crown_type = str(row.get("crown_type") or "").strip()
    if crown_type not in CROWN_SCORES:
        item["data_status"] = "manual_pending"
        item["score_ratio"] = None
        item["item_score"] = None
        item["fields"] = [
            {"label": "挂冠类型", "value": None, "origin": "人工录入", "note": "待录入"}
        ]
        item["note"] = "可在Excel的15_人工录入工作表或页面中录入挂冠类型。"
        return

    score = CROWN_SCORES[crown_type]
    item["score_ratio"] = score
    item["item_score"] = score
    item["data_status"] = "success" if score > 0 else "zero"
    item["fields"] = [
        {"label": "挂冠类型", "value": crown_type, "origin": "Excel人工录入", "note": "固定选项评分"},
        {"label": "录入人", "value": row.get("operator"), "origin": "Excel人工录入", "note": "人工记录"},
        {"label": "录入时间", "value": row.get("recorded_at"), "origin": "Excel人工录入", "note": "取最新一条录入"},
    ]
    item["source_table"] = str(row.get("source_table") or "Excel：15_人工录入")
    item["note"] = (
        "Excel挂冠评分：黑金挂冠1分，普通挂冠0.5分，无挂冠0分；"
        "采用录入时间最新的一条记录。"
    )
    result["manual_crown"] = {
        "crown_type": crown_type,
        "operator": row.get("operator") or "",
        "recorded_at": row.get("recorded_at") or "",
        "score": score,
    }


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_manual_crown(result, sections)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-15-v14-excel-manual-crown"
    return result


__all__ = ["CROWN_SCORES", "_patch_manual_crown", "build_visual_diagnosis"]
