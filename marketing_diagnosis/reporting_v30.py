from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v29


ROOM_TYPE_STYLE = """
<style>
.room-summary-v30{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.room-summary-v30>div{padding:14px 16px;border:1px solid #dfe8e5;border-radius:12px;background:#f8fbfa;min-height:76px}
.room-summary-v30 small{display:block;color:var(--muted);font-size:12px;font-weight:800}
.room-summary-v30 strong{display:block;margin-top:7px;color:#26343d;font-size:20px;line-height:1.2}
.room-table-v30{width:100%;min-width:1080px;border-collapse:collapse;border:1px solid #e1e8e5;background:#fff}
.room-table-v30 th,.room-table-v30 td{padding:9px 12px;border-right:1px solid #e7ecea;border-bottom:1px solid #e7ecea;text-align:right;vertical-align:middle;line-height:1.35;height:auto}
.room-table-v30 th{background:#f4f6f5;color:#596773;font-size:12px;font-weight:800;text-align:center}
.room-table-v30 td{color:#34424b;font-size:13px;white-space:nowrap}
.room-table-v30 th:first-child,.room-table-v30 td:first-child{text-align:left;position:sticky;left:0;z-index:1;background:#fff;min-width:220px}
.room-table-v30 th:first-child{z-index:2;background:#f4f6f5}
.room-table-v30 tbody tr:nth-child(odd){background:#f8fbfa}
.room-table-v30 tbody tr:nth-child(odd) td:first-child{background:#f8fbfa}
.room-table-v30 tbody tr.is-low{background:#fff3ef}
.room-table-v30 tbody tr.is-low td:first-child{background:#fff3ef}
.room-name-v30{font-weight:800;color:#26343d}
.room-source-caption-v30{margin:11px 0 0;color:var(--muted);font-size:11px;line-height:1.6}
@media(max-width:900px){.room-summary-v30{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.room-summary-v30{grid-template-columns:1fr}}
</style>
"""


_ITEM_TWO_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-2'>.*?</article>",
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


def _field_value(item: dict[str, Any], label: str) -> Any:
    for field in item.get("fields") or []:
        if str(field.get("label") or "") == label:
            return field.get("value")
    return None


def _plain(value: Any) -> str:
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


def _summary(item: dict[str, Any]) -> str:
    cards = [
        ("房型数", _plain(_field_value(item, "房型数"))),
        ("房间总数", _plain(_field_value(item, "房间总数"))),
        ("低效房型数", _plain(_field_value(item, "低效房型数"))),
        ("低效房型占比", _percentage(_field_value(item, "低效房型占比"))),
    ]
    return "<div class='room-summary-v30'>" + "".join(
        "<div>"
        f"<small>{reporting_v8._e(label)}</small>"
        f"<strong>{reporting_v8._e(value)}</strong>"
        "</div>"
        for label, value in cards
    ) + "</div>"


def _table(item: dict[str, Any]) -> str:
    headers = [
        "房型",
        "房间总数",
        "间夜数",
        "出租率",
        "房费",
        "平均房费",
        "RevPAR",
        "判定",
    ]
    rows: list[str] = []
    for record in item.get("records") or []:
        room_name = str(record.get("room_type_name") or "未命名房型")
        occupancy = _number(record.get("occupancy_points"))
        if occupancy is None:
            raw_occupancy = _number(record.get("occupancy_rate"))
            occupancy = (
                raw_occupancy * 100
                if raw_occupancy is not None and abs(raw_occupancy) <= 1
                else raw_occupancy
            )
        is_low = bool(record.get("is_low"))
        status = (
            "<span class='status-badge disabled'>低效</span>"
            if is_low
            else "<span class='status-badge ok'>正常</span>"
        )
        cells = [
            f"<span class='room-name-v30'>{reporting_v8._e(room_name)}</span>",
            reporting_v8._e(_plain(record.get("room_count"))),
            reporting_v8._e(_plain(record.get("room_nights"))),
            reporting_v8._e(_percentage(occupancy)),
            reporting_v8._e(_plain(record.get("room_revenue"))),
            reporting_v8._e(_plain(record.get("average_room_price"))),
            reporting_v8._e(_plain(record.get("revpar"))),
            status,
        ]
        rows.append(
            f"<tr class='{'is-low' if is_low else ''}'>"
            + "".join(f"<td>{cell}</td>" for cell in cells)
            + "</tr>"
        )

    if not rows:
        rows.append(
            "<tr><td>暂无房型汇总数据</td>"
            + "<td>—</td>" * (len(headers) - 1)
            + "</tr>"
        )

    return (
        "<div class='table-scroll'><table class='room-table-v30'><thead><tr>"
        + "".join(f"<th>{reporting_v8._e(header)}</th>" for header in headers)
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _room_type_card(item: dict[str, Any]) -> str:
    status_key = str(item.get("data_status") or "missing")
    status_text, status_class = reporting_v8.STATUS.get(status_key, (status_key, "neutral"))
    score_class = "ok" if item.get("item_score") is not None else "pending"
    return (
        f"<article class='diagnosis-card room-type-card-v30' data-status='{reporting_v8._e(status_key)}' "
        f"data-title='{reporting_v8._e(item.get('item_name'))}' id='rule-2'>"
        "<div class='card-top'><div class='rule-no'>02</div>"
        "<div class='card-title'><h3>房型 RevPAR 与低效房型</h3>"
        "<p>按房型展示近30天房间数、间夜数、出租率、房费、平均房费和RevPAR。</p></div>"
        "<div class='card-tags'>"
        "<div class='title-meta-item title-period'><small>统计周期</small><strong>近30天</strong></div>"
        f"<div class='title-meta-item title-score {score_class}'><small>当前得分</small>"
        f"<div class='title-score-value'><strong>{reporting_v8._e(reporting_v8._score_text(item))}</strong>"
        f"<span>满分 {reporting_v8._e(reporting_v8._base_text(item))}</span></div></div>"
        f"<span class='status-badge {status_class}'>{reporting_v8._e(status_text)}</span></div></div>"
        "<div class='result-area'>"
        + _summary(item)
        + _table(item)
        + "<p class='room-source-caption-v30'>数据仅取jl11_room_type_classification中section=summary；表内字段均为近30天汇总值。</p>"
        + reporting_v8._source_box(item)
        + f"<div class='notice'>{reporting_v8._e(item.get('note') or '')}</div>"
        + "</div></article>"
    )


def _item_two(result: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == 2
        ),
        None,
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v29.build_html(result)
    item = _item_two(result)
    if item:
        html_text = _ITEM_TWO_PATTERN.sub(lambda _: _room_type_card(item), html_text, count=1)
    return html_text.replace("</head>", ROOM_TYPE_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v29.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v29.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "ROOM_TYPE_STYLE",
    "_room_type_card",
    "_table",
    "build_html",
    "build_markdown",
    "write_reports",
]
