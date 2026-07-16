from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v22


FLOW_TABLE_STYLE = """
<style>
.flow-table-card-v23 .result-area{display:grid;gap:16px}
.flow-table-v23{width:100%;min-width:1420px;border-collapse:collapse;border:1px solid #e1e8e5;background:#fff}
.flow-table-v23 th,.flow-table-v23 td{padding:13px 12px;border-right:1px solid #e7ecea;border-bottom:1px solid #e7ecea;text-align:center;vertical-align:middle}
.flow-table-v23 th{background:#f4f6f5;color:#596773;font-size:12px;line-height:1.55;font-weight:800;white-space:normal}
.flow-table-v23 td{color:#44515a;font-size:13px;white-space:nowrap}
.flow-table-v23 tbody tr:nth-child(odd){background:#f1f8ed}
.flow-table-v23 tbody tr:hover{background:#e8f4e3}
.flow-table-v23 th:first-child,.flow-table-v23 td:first-child{position:sticky;left:0;z-index:1;min-width:108px;font-weight:800}
.flow-table-v23 th:first-child{z-index:2;background:#f4f6f5}
.flow-table-v23 tbody tr:nth-child(odd) td:first-child{background:#f1f8ed}
.flow-table-v23 tbody tr:nth-child(even) td:first-child{background:#fff}
.flow-ranks-v23{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:10px}
.flow-rank-v23{padding:12px 14px;border:1px solid #e0e8e5;border-radius:10px;background:#f8fbfa}
.flow-rank-v23 small{display:block;color:var(--muted);font-size:11px;font-weight:800;line-height:1.4}
.flow-rank-v23 strong{display:block;margin-top:6px;color:#26343d;font-size:18px}
.flow-table-caption-v23{margin:0;color:var(--muted);font-size:11px;line-height:1.6}
@media(max-width:900px){.flow-ranks-v23{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.flow-ranks-v23{grid-template-columns:1fr}}
</style>
"""


_FLOW_CARD_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-4'>.*?</article>",
    re.DOTALL,
)
_RANK_DATE_PATTERN = re.compile(r"取值日[：:]\s*(\d{4}-\d{2}-\d{2})")


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").rstrip("%"))
        return None if number != number else number
    except (TypeError, ValueError):
        return None


def _base_label(value: Any) -> str:
    return str(value or "").split("（取值日：", 1)[0].strip()


def _field_value(item: dict[str, Any], label: str) -> Any:
    for field in item.get("fields") or []:
        if _base_label(field.get("label")) == label:
            return field.get("value")
    return None


def _latest_field_date(item: dict[str, Any]) -> str | None:
    dates: list[str] = []
    for field in item.get("fields") or []:
        match = _RANK_DATE_PATTERN.search(str(field.get("label") or ""))
        if match:
            dates.append(match.group(1))
    return max(dates) if dates else None


def _count(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "—"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _percentage(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "—"
    if abs(number) <= 1:
        number *= 100
    return f"{number:.2f}%"


def _rank(value: Any) -> str:
    if value in (None, ""):
        return "—"
    return str(value)


def _record_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _rate(numerator: Any, denominator: Any, supplied: Any = None) -> Any:
    if supplied not in (None, ""):
        return supplied
    top, bottom = _number(numerator), _number(denominator)
    if top is None or bottom in (None, 0):
        return None
    return top / bottom


def _daily_rows(item: dict[str, Any]) -> list[list[str]]:
    records = list(item.get("daily_records") or item.get("records") or [])
    rows: list[list[str]] = []
    for record in sorted(records, key=lambda row: str(row.get("business_date") or row.get("date") or "")):
        day = str(record.get("business_date") or record.get("date") or "")[:10]
        exposure = _record_value(record, "exposure", "hotel_exposure")
        peer_exposure = _record_value(record, "peer_exposure", "competitor_exposure")
        views = _record_value(record, "views", "hotel_views")
        peer_views = _record_value(record, "peer_views", "competitor_views")
        orders = _record_value(record, "paid_orders", "hotel_paid_orders")
        peer_orders = _record_value(record, "peer_paid_orders", "competitor_paid_orders")
        exposure_rate = _rate(views, exposure, _record_value(record, "exposure_to_view_rate"))
        peer_exposure_rate = _rate(peer_views, peer_exposure, _record_value(record, "peer_exposure_to_view_rate"))
        payment_rate = _rate(orders, views, _record_value(record, "payment_conversion_rate", "view_to_pay_rate"))
        peer_payment_rate = _rate(peer_orders, peer_views, _record_value(record, "peer_payment_conversion_rate", "peer_view_to_pay_rate"))
        rows.append([
            day.replace("-", "") if day else "—",
            _count(exposure),
            _count(peer_exposure),
            _count(views),
            _count(peer_views),
            _percentage(exposure_rate),
            _percentage(peer_exposure_rate),
            _count(orders),
            _count(peer_orders),
            _percentage(payment_rate),
            _percentage(peer_payment_rate),
        ])
    return rows


def _summary_row(item: dict[str, Any]) -> list[str]:
    date_text = _latest_field_date(item)
    return [
        date_text.replace("-", "") if date_text else "近30天汇总",
        _count(_field_value(item, "曝光人数")),
        _count(_field_value(item, "曝光人数同行均值")),
        _count(_field_value(item, "浏览人数")),
        _count(_field_value(item, "浏览人数同行均值")),
        _percentage(_field_value(item, "曝光-浏览转化率")),
        _percentage(_field_value(item, "曝光-浏览转化率同行均值")),
        _count(_field_value(item, "支付订单数")),
        _count(_field_value(item, "支付订单数同行均值")),
        _percentage(_field_value(item, "浏览-支付转化率")),
        _percentage(_field_value(item, "浏览-支付转化率同行均值")),
    ]


def _flow_table(item: dict[str, Any]) -> str:
    headers = [
        "日期",
        "我的酒店曝光人数",
        "竞争圈平均曝光人数",
        "我的酒店浏览人数",
        "竞争圈平均浏览人数",
        "我的酒店曝光-浏览转化率",
        "竞争圈平均曝光-浏览转化率",
        "我的酒店支付订单数",
        "竞争圈平均支付订单数",
        "我的酒店浏览-支付转化率",
        "竞争圈平均浏览-支付转化率",
    ]
    rows = _daily_rows(item) or [_summary_row(item)]
    table_rows = "".join(
        "<tr>" + "".join(f"<td>{reporting_v8._e(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return (
        "<div class='table-scroll'><table class='flow-table-v23'><thead><tr>"
        + "".join(f"<th>{reporting_v8._e(header)}</th>" for header in headers)
        + "</tr></thead><tbody>"
        + table_rows
        + "</tbody></table></div>"
    )


def _rank_strip(item: dict[str, Any]) -> str:
    ranks = [
        ("曝光人数同行排名", _field_value(item, "曝光人数同行排名")),
        ("浏览人数同行排名", _field_value(item, "浏览人数同行排名")),
        ("曝光-浏览转化率同行排名", _field_value(item, "曝光-浏览转化率同行排名")),
        ("支付订单数同行排名", _field_value(item, "支付订单数同行排名")),
        ("浏览-支付转化率同行排名", _field_value(item, "浏览-支付转化率同行排名")),
    ]
    return "<div class='flow-ranks-v23'>" + "".join(
        "<div class='flow-rank-v23'>"
        f"<small>{reporting_v8._e(label)}</small><strong>{reporting_v8._e(_rank(value))}</strong></div>"
        for label, value in ranks
    ) + "</div>"


def _flow_card(item: dict[str, Any]) -> str:
    status_key = str(item.get("data_status") or "missing")
    status_text, status_class = reporting_v8.STATUS.get(status_key, (status_key, "neutral"))
    score_class = "ok" if item.get("item_score") is not None else "pending"
    records_present = bool(item.get("daily_records") or item.get("records"))
    caption = (
        "按业务日期逐日展示；同一天存在多个快照时使用数据层已确认的最新快照。"
        if records_present
        else "当前结果为近30天汇总口径；表头保持原流量明细格式，同行排名在表格下方单独展示。"
    )
    return (
        f"<article class='diagnosis-card flow-table-card-v23' data-status='{reporting_v8._e(status_key)}' "
        f"data-title='{reporting_v8._e(item.get('item_name'))}' id='rule-4'>"
        "<div class='card-top'>"
        "<div class='rule-no'>04</div>"
        f"<div class='card-title'><h3>{reporting_v8._e(item.get('item_name'))}</h3>"
        f"<p>{reporting_v8._e(reporting_v8.DESCRIPTIONS.get(4))}</p></div>"
        "<div class='card-tags'>"
        f"<div class='title-meta-item title-period'><small>统计周期</small><strong>{reporting_v8._e(reporting_v8.PERIODS.get(4))}</strong></div>"
        f"<div class='title-meta-item title-score {score_class}'><small>当前得分</small>"
        f"<div class='title-score-value'><strong>{reporting_v8._e(reporting_v8._score_text(item))}</strong>"
        f"<span>满分 {reporting_v8._e(reporting_v8._base_text(item))}</span></div></div>"
        f"<span class='status-badge {status_class}'>{reporting_v8._e(status_text)}</span></div></div>"
        "<div class='result-area'>"
        + _flow_table(item)
        + _rank_strip(item)
        + f"<p class='flow-table-caption-v23'>{reporting_v8._e(caption)}</p>"
        + reporting_v8._source_box(item)
        + f"<div class='notice'>{reporting_v8._e(item.get('note') or '流量指标按当前确认口径计算。')}</div>"
        + "</div></article>"
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
    html_text = reporting_v22.build_html(result)
    item = _item_four(result)
    if item:
        html_text = _FLOW_CARD_PATTERN.sub(lambda _: _flow_card(item), html_text, count=1)
    return html_text.replace("</head>", FLOW_TABLE_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v22.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v22.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "FLOW_TABLE_STYLE",
    "_flow_card",
    "_flow_table",
    "build_html",
    "build_markdown",
    "write_reports",
]
