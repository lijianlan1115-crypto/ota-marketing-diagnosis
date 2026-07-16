from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import re

from marketing_diagnosis import reporting_v8, reporting_v23, reporting_v28


COMPACT_LAYOUT_STYLE = """
<style>
/* The customer report must show item 04 as one aggregate row only. */
.flow-table-v23 tbody tr:not(:first-child){display:none!important}

/* Item 01 rows follow their content height; category captions are not shown. */
.performance-table-v28 th,
.performance-table-v28 td{
  padding:8px 12px!important;
  line-height:1.35!important;
  height:auto!important;
  min-height:0!important;
}
.performance-table-v28 tbody tr{height:auto!important}
.performance-category-v25,
.performance-category-v28{
  display:none!important;
}
</style>
"""

_FLOW_CARD_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-4'>.*?</article>",
    re.DOTALL,
)
_FIRST_TABLE_CELL_PATTERN = re.compile(
    r"(<table class='flow-table-v23'>.*?<tbody><tr><td>).*?(</td>)",
    re.DOTALL,
)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _sum(records: list[dict[str, Any]], *keys: str) -> float | None:
    values: list[float] = []
    for record in records:
        value = next(
            (
                _number(record.get(key))
                for key in keys
                if _number(record.get(key)) is not None
            ),
            None,
        )
        if value is not None:
            values.append(value)
    return sum(values) if values else None


def _divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _set_field(item: dict[str, Any], label: str, value: Any, note: str) -> None:
    for field in item.get("fields") or []:
        if reporting_v23._base_label(field.get("label")) == label:
            field["value"] = value
            field["origin"] = "近30天汇总计算"
            field["note"] = note
            return
    item.setdefault("fields", []).append(
        {
            "label": label,
            "value": value,
            "origin": "近30天汇总计算",
            "note": note,
        }
    )


def _flow_summary_item(item: dict[str, Any]) -> dict[str, Any]:
    """Collapse daily traffic records into one calculated near-30-day row.

    This is a report-only transformation. The original diagnosis result, scoring,
    database selection and rank fields remain unchanged.
    """

    display_item = deepcopy(item)
    records = list(display_item.get("daily_records") or display_item.get("records") or [])
    records = sorted(
        records,
        key=lambda row: str(row.get("business_date") or row.get("date") or ""),
    )[-30:]

    if records:
        exposure = _sum(records, "exposure", "hotel_exposure")
        peer_exposure = _sum(records, "peer_exposure", "competitor_exposure")
        views = _sum(records, "views", "hotel_views")
        peer_views = _sum(records, "peer_views", "competitor_views")
        paid_orders = _sum(records, "paid_orders", "hotel_paid_orders")
        peer_paid_orders = _sum(records, "peer_paid_orders", "competitor_paid_orders")

        exposure_to_view = _divide(views, exposure)
        peer_exposure_to_view = _divide(peer_views, peer_exposure)
        view_to_pay = _divide(paid_orders, views)
        peer_view_to_pay = _divide(peer_paid_orders, peer_views)

        _set_field(display_item, "曝光人数", exposure, "最近30天每日酒店曝光人数合计")
        _set_field(display_item, "曝光人数同行均值", peer_exposure, "最近30天每日竞争圈平均曝光人数合计")
        _set_field(display_item, "浏览人数", views, "最近30天每日酒店浏览人数合计")
        _set_field(display_item, "浏览人数同行均值", peer_views, "最近30天每日竞争圈平均浏览人数合计")
        _set_field(display_item, "曝光-浏览转化率", exposure_to_view, "最近30天浏览人数合计÷曝光人数合计")
        _set_field(display_item, "曝光-浏览转化率同行均值", peer_exposure_to_view, "最近30天竞争圈浏览人数合计÷竞争圈曝光人数合计")
        _set_field(display_item, "支付订单数", paid_orders, "最近30天每日酒店支付订单数合计")
        _set_field(display_item, "支付订单数同行均值", peer_paid_orders, "最近30天每日竞争圈平均支付订单数合计")
        _set_field(display_item, "浏览-支付转化率", view_to_pay, "最近30天支付订单数合计÷浏览人数合计")
        _set_field(display_item, "浏览-支付转化率同行均值", peer_view_to_pay, "最近30天竞争圈支付订单数合计÷竞争圈浏览人数合计")

    display_item["daily_records"] = []
    display_item["records"] = []
    display_item["note"] = (
        "页面只展示一条近30天汇总记录；曝光、浏览和支付订单按日数据求和，"
        "一转与二转使用汇总后的分子÷分母重新计算。同行排名仍展示最近业务日期的非空排名。"
    )
    return display_item


def _flow_summary_card(item: dict[str, Any]) -> str:
    card = reporting_v23._flow_card(_flow_summary_item(item))
    return _FIRST_TABLE_CELL_PATTERN.sub(
        lambda match: match.group(1) + "近30天" + match.group(2),
        card,
        count=1,
    )


def _item_four(result: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == 4
        ),
        None,
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v28.build_html(result)
    item = _item_four(result)
    if item:
        html_text = _FLOW_CARD_PATTERN.sub(
            lambda _: _flow_summary_card(item),
            html_text,
            count=1,
        )
    return html_text.replace("</head>", COMPACT_LAYOUT_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v28.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v28.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "COMPACT_LAYOUT_STYLE",
    "_flow_summary_card",
    "_flow_summary_item",
    "build_html",
    "build_markdown",
    "write_reports",
]
