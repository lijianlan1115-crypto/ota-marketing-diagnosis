from __future__ import annotations

from typing import Any

from marketing_diagnosis.visual_diagnosis import _n
from marketing_diagnosis.visual_diagnosis_v13 import (
    build_visual_diagnosis as _base_build_visual_diagnosis,
)


_DAILY_PERIODS = {"日", "daily", "day", "当日"}
_CANONICAL_CODES = {
    "exposure": "FLOW_EXPOSURE_UV",
    "views": "FLOW_INTENTION_UV",
    "paid_orders": "FLOW_PAY_ORDER_CNT",
    "exposure_to_view_rate": "FLOW_INTENTION_PER_EXPOSURE",
    "payment_conversion_rate": "FLOW_PAY_ORDER_PER_INTENTION",
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


def _base_label(value: Any) -> str:
    return str(value or "").split("（取值日：", 1)[0]


def _set_score(item: dict[str, Any], ratio: float | None, status: str) -> None:
    item["score_ratio"] = ratio
    item["item_score"] = (
        round(float(item.get("base_score") or 0) * ratio, 2)
        if ratio is not None
        else None
    )
    item["data_status"] = status


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _score_ratio(comparison: float | None) -> float:
    if comparison is None:
        return 0.0
    if comparison > 2:
        return 1.0
    if comparison >= 1.5:
        return 0.8
    if comparison >= 1:
        return 0.6
    return 0.0


def _is_daily_meituan(row: dict[str, Any]) -> bool:
    platform = str(row.get("platform") or "").strip().lower()
    period = str(row.get("period_type") or row.get("stats_period_type") or "").strip().lower()
    return platform in {"meituan", "美团", "美团酒店"} and period in _DAILY_PERIODS


def _is_excel_row(row: dict[str, Any]) -> bool:
    return str(row.get("source_table") or row.get("__source_table") or "").startswith("Excel：")


def _canonical_value_present(row: dict[str, Any], target: str) -> bool:
    """Accept only the canonical FLOW metric in DB mode.

    Database rows produced by ``db_loader_v4`` retain the selected source code as
    ``<target>_metric_code``. Excel rows are already created from the explicit
    Chinese FLOW sheet and may not carry this auxiliary key, so they are accepted
    when the target value exists.
    """

    if row.get(target) is None:
        return False
    code = str(row.get(f"{target}_metric_code") or "").strip().upper()
    if code:
        return code == _CANONICAL_CODES[target]
    return _is_excel_row(row)


def _latest_rows_by_day(
    rows: list[dict[str, Any]],
    target: str,
) -> list[dict[str, Any]]:
    selected: dict[str, tuple[tuple[str, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        if not _is_daily_meituan(row) or not _canonical_value_present(row, target):
            continue
        day = str(row.get("business_date") or "")[:10]
        if not day:
            continue
        candidate = (str(row.get("snapshot_time") or ""), index)
        current = selected.get(day)
        if current is None or candidate >= current[0]:
            selected[day] = (candidate, row)
    return [selected[day][1] for day in sorted(selected)]


def _sum(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [_n(row.get(key)) for row in rows]
    clean = [value for value in values if value is not None]
    return sum(clean) if clean else None


def _average(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [_n(row.get(key)) for row in rows]
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else None


def _latest_rank(rows: list[dict[str, Any]], target: str) -> tuple[Any, str | None]:
    key = f"{target}_rank"
    for row in reversed(rows):
        raw = row.get(f"{key}_raw")
        value = raw if raw not in (None, "") else row.get(key)
        if value in (None, ""):
            continue
        day = str(row.get("business_date") or "")[:10] or None
        return value, day
    return None, None


def _field(label: str, value: Any, note: str, origin: str = "规则计算") -> dict[str, Any]:
    return {"label": label, "value": value, "note": note, "origin": origin}


def _rank_field(label: str, value: Any, day: str | None) -> dict[str, Any]:
    display_label = f"{label}（取值日：{day}）" if day else label
    note = (
        f"按 business_date 倒序取最近一条非空 competitor_rank；取值日为 {day}；排名不参与评分。"
        if day
        else "统计周期内没有非空 competitor_rank；排名不参与评分。"
    )
    return _field(display_label, value, note, "最新非空 competitor_rank")


def _metric_values(
    all_rows: list[dict[str, Any]],
    target: str,
    peer_key: str,
) -> tuple[list[dict[str, Any]], float | None, float | None, Any, str | None]:
    rows = _latest_rows_by_day(all_rows, target)
    return rows, _sum(rows, target), _sum(rows, peer_key), *_latest_rank(rows, target)


def _patch_authoritative_flow(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    item = _item(result, 4)
    if not item:
        return

    all_rows = list(sections.get("ota_funnel") or [])

    exposure_rows, exposure, peer_exposure, exposure_rank, exposure_rank_date = _metric_values(
        all_rows, "exposure", "peer_exposure"
    )
    views_rows, views, peer_views, views_rank, views_rank_date = _metric_values(
        all_rows, "views", "peer_views"
    )
    order_rows, paid_orders, peer_paid_orders, order_rank, order_rank_date = _metric_values(
        all_rows, "paid_orders", "peer_paid_orders"
    )
    exposure_rate_rows = _latest_rows_by_day(all_rows, "exposure_to_view_rate")
    payment_rate_rows = _latest_rows_by_day(all_rows, "payment_conversion_rate")

    if not exposure_rows:
        _set_score(item, None, "missing")
        item["fields"] = [
            _field("曝光人数", None, "未取得 metric_code=FLOW_EXPOSURE_UV 的日数据", "数据库筛选")
        ]
        item["note"] = (
            "未取得美团日口径 FLOW_EXPOSURE_UV 数据，无法按确认后的流量口径计算。"
        )
        return

    exposure_to_view = _safe_div(views, exposure)
    if exposure_to_view is None:
        exposure_to_view = _average(exposure_rate_rows, "exposure_to_view_rate")
    peer_exposure_to_view = _safe_div(peer_views, peer_exposure)
    if peer_exposure_to_view is None:
        peer_exposure_to_view = _average(exposure_rate_rows, "peer_exposure_to_view_rate")

    payment_conversion = _safe_div(paid_orders, views)
    if payment_conversion is None:
        payment_conversion = _average(payment_rate_rows, "payment_conversion_rate")
    peer_payment_conversion = _safe_div(peer_paid_orders, peer_views)
    if peer_payment_conversion is None:
        peer_payment_conversion = _average(payment_rate_rows, "peer_payment_conversion_rate")

    exposure_rate_rank, exposure_rate_rank_date = _latest_rank(
        exposure_rate_rows, "exposure_to_view_rate"
    )
    payment_rate_rank, payment_rate_rank_date = _latest_rank(
        payment_rate_rows, "payment_conversion_rate"
    )

    item["fields"] = [
        _field("曝光人数", exposure, "metric_code=FLOW_EXPOSURE_UV；同日保留最新snapshot_time后按日求和", "数据库汇总"),
        _field("曝光人数同行均值", peer_exposure, "FLOW_EXPOSURE_UV同行均值按有效日求和", "数据库汇总"),
        _rank_field("曝光人数同行排名", exposure_rank, exposure_rank_date),
        _field("浏览人数", views, "metric_code=FLOW_INTENTION_UV；同日最新快照后按日求和", "数据库汇总"),
        _field("浏览人数同行均值", peer_views, "FLOW_INTENTION_UV同行均值按有效日求和", "数据库汇总"),
        _rank_field("浏览人数同行排名", views_rank, views_rank_date),
        _field("支付订单数", paid_orders, "metric_code=FLOW_PAY_ORDER_CNT；同日最新快照后按日求和", "数据库汇总"),
        _field("支付订单数同行均值", peer_paid_orders, "FLOW_PAY_ORDER_CNT同行均值按有效日求和", "数据库汇总"),
        _rank_field("支付订单数同行排名", order_rank, order_rank_date),
        _field("曝光-浏览转化率", exposure_to_view, "浏览人数÷曝光人数", "公式计算"),
        _field("曝光-浏览转化率同行均值", peer_exposure_to_view, "同行浏览人数÷同行曝光人数", "公式计算"),
        _rank_field("曝光-浏览转化率同行排名", exposure_rate_rank, exposure_rate_rank_date),
        _field("浏览-支付转化率", payment_conversion, "支付订单数÷浏览人数", "公式计算"),
        _field("浏览-支付转化率同行均值", peer_payment_conversion, "同行支付订单数÷同行浏览人数", "公式计算"),
        _rank_field("浏览-支付转化率同行排名", payment_rate_rank, payment_rate_rank_date),
    ]

    scoring_values = (
        ("曝光人数", exposure, peer_exposure),
        ("浏览人数", views, peer_views),
        ("曝光-浏览转化率", exposure_to_view, peer_exposure_to_view),
        ("浏览-支付转化率", payment_conversion, peer_payment_conversion),
    )
    ratios: list[float] = []
    details: list[str] = []
    for label, actual, peer in scoring_values:
        comparison = _safe_div(actual, peer)
        ratio = _score_ratio(comparison)
        ratios.append(ratio)
        details.append(
            f"{label}缺少酒店值或同行均值，子项按0%计"
            if comparison is None
            else f"{label}÷同行均值={comparison:.2f}，子项比例{ratio:.0%}"
        )

    overall_ratio = sum(ratios) / 4
    _set_score(item, overall_ratio, "success" if overall_ratio > 0 else "zero")
    item["note"] = (
        "确认口径：FLOW_EXPOSURE_UV等FLOW_*指标按business_date分组，同日只保留最新"
        "snapshot_time；人数与同行均值按日求和；同行排名按日期倒序取最近一条非空"
        "competitor_rank并标注取值日期，排名不参与评分。评分仍按四项酒店值÷同行均值、"
        "各占25%计算。" + "；".join(details)
    )


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


def build_visual_diagnosis(
    sections: dict[str, list[dict[str, Any]]],
    hotel_name: str = "",
) -> dict[str, Any]:
    result = _base_build_visual_diagnosis(sections, hotel_name)
    _patch_authoritative_flow(result, sections)
    _recalculate_totals(result)
    result["rule_version"] = "2026-07-15-v15-authoritative-flow-rank"
    return result


__all__ = [
    "_latest_rows_by_day",
    "_patch_authoritative_flow",
    "build_visual_diagnosis",
]
