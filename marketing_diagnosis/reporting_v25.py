from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v24


PERFORMANCE_STYLE = """
<style>
.performance-v25-summary{display:grid;grid-template-columns:repeat(5,minmax(160px,1fr));gap:12px;margin-bottom:16px}
.performance-v25-summary>div{padding:16px 18px;border:1px solid #dfe8e5;border-radius:12px;background:linear-gradient(145deg,#fbfdfc,#f7faf9);min-height:96px}
.performance-v25-summary small{display:block;color:var(--muted);font-size:12px;font-weight:800}.performance-v25-summary strong{display:block;margin-top:8px;color:#26343d;font-size:22px;line-height:1.25}
.performance-table-v25{width:100%;min-width:1580px;border-collapse:collapse;border:1px solid #e1e8e5;background:#fff}
.performance-table-v25 th,.performance-table-v25 td{padding:12px 13px;border-right:1px solid #e7ecea;border-bottom:1px solid #e7ecea;text-align:right;vertical-align:middle;white-space:nowrap}
.performance-table-v25 th{background:#f4f6f5;color:#596773;font-size:12px;line-height:1.45;font-weight:800;text-align:center}
.performance-table-v25 td{font-size:13px;color:#34424b}.performance-table-v25 th:first-child,.performance-table-v25 td:first-child{text-align:left;position:sticky;left:0;z-index:1;background:#fff;min-width:190px}
.performance-table-v25 th:first-child{z-index:2;background:#f4f6f5}.performance-table-v25 tbody tr:nth-child(odd){background:#f8fbfa}.performance-table-v25 tbody tr:nth-child(odd) td:first-child{background:#f8fbfa}
.performance-metric-v25{font-weight:800;color:#26343d}.performance-category-v25{display:block;margin-top:4px;color:var(--muted);font-size:10px;font-weight:600}
.performance-yoy-v25{font-weight:800;color:#355f9d}.performance-v25-caption{margin:12px 0 0;color:var(--muted);font-size:11px;line-height:1.6}
@media(max-width:1100px){.performance-v25-summary{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.performance-v25-summary{grid-template-columns:1fr}}
</style>
"""


_ITEM_ONE_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-1'>.*?</article>",
    re.DOTALL,
)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").rstrip("%"))
        return None if number != number else number
    except (TypeError, ValueError):
        return None


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


def _pct(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "—"
    if abs(number) <= 1:
        number *= 100
    return f"{number:.2f}%"


def _metric_value(metric_name: str, value: Any) -> str:
    number = _number(value)
    if number is None:
        return "—"
    normalized = metric_name.strip().lower()
    if "率" in metric_name or normalized in {"occupancy", "occupancy_rate"}:
        # JL02 stores rate metrics as percentage points in the established report.
        return f"{number:,.2f}"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _summary(item: dict[str, Any]) -> str:
    cards = [
        ("本月值", _plain(_field_value(item, "本期本月值"))),
        ("去年本月值", _plain(_field_value(item, "去年本月值"))),
        ("本月YOY", _pct(_field_value(item, "本月YOY"))),
        ("本年YOY", _pct(_field_value(item, "本年YOY"))),
        ("取数状态", str(_field_value(item, "取数状态") or "未取到")),
    ]
    return "<div class='performance-v25-summary'>" + "".join(
        "<div>"
        f"<small>{reporting_v8._e(label)}</small>"
        f"<strong>{reporting_v8._e(value)}</strong>"
        "</div>"
        for label, value in cards
    ) + "</div>"


def _records_table(item: dict[str, Any]) -> str:
    headers = [
        "经营指标",
        "本日",
        "去年本日",
        "本日YOY",
        "本月",
        "去年本月",
        "本月YOY",
        "本年",
        "去年本年",
        "本年YOY",
    ]
    rows: list[str] = []
    for record in item.get("records") or []:
        metric_name = str(record.get("metric_name") or "")
        category = str(record.get("category") or "")
        metric_cell = (
            f"<span class='performance-metric-v25'>{reporting_v8._e(metric_name or '未命名指标')}</span>"
            + (
                f"<span class='performance-category-v25'>{reporting_v8._e(category)}</span>"
                if category
                else ""
            )
        )
        values = [
            metric_cell,
            reporting_v8._e(_metric_value(metric_name, record.get("value_day"))),
            reporting_v8._e(_metric_value(metric_name, record.get("previous_value_day"))),
            f"<span class='performance-yoy-v25'>{reporting_v8._e(_pct(record.get('yoy_day')))}</span>",
            reporting_v8._e(_metric_value(metric_name, record.get("value_month"))),
            reporting_v8._e(_metric_value(metric_name, record.get("previous_value_month"))),
            f"<span class='performance-yoy-v25'>{reporting_v8._e(_pct(record.get('yoy_month')))}</span>",
            reporting_v8._e(_metric_value(metric_name, record.get("value_year"))),
            reporting_v8._e(_metric_value(metric_name, record.get("previous_value_year"))),
            f"<span class='performance-yoy-v25'>{reporting_v8._e(_pct(record.get('yoy_year')))}</span>",
        ]
        rows.append("<tr>" + "".join(f"<td>{value}</td>" for value in values) + "</tr>")

    if not rows:
        rows.append(
            "<tr><td><span class='performance-metric-v25'>暂无数据</span></td>"
            + "<td>—</td>" * (len(headers) - 1)
            + "</tr>"
        )

    return (
        "<div class='table-scroll'><table class='performance-table-v25'><thead><tr>"
        + "".join(f"<th>{reporting_v8._e(header)}</th>" for header in headers)
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _performance_card(item: dict[str, Any]) -> str:
    status_key = str(item.get("data_status") or "missing")
    status_text, status_class = reporting_v8.STATUS.get(status_key, (status_key, "neutral"))
    score_class = "ok" if item.get("item_score") is not None else "pending"
    return (
        f"<article class='diagnosis-card performance-card-v25' data-status='{reporting_v8._e(status_key)}' "
        f"data-title='{reporting_v8._e(item.get('item_name'))}' id='rule-1'>"
        "<div class='card-top'><div class='rule-no'>01</div>"
        "<div class='card-title'><h3>月度经营趋势 YOY</h3>"
        "<p>按业务日期精确匹配本期与去年同日，并分别展示本日、本月、本年的同期值及YOY。</p></div>"
        "<div class='card-tags'>"
        "<div class='title-meta-item title-period'><small>统计周期</small><strong>本日 / 本月 / 本年</strong></div>"
        f"<div class='title-meta-item title-score {score_class}'><small>当前得分</small>"
        f"<div class='title-score-value'><strong>{reporting_v8._e(reporting_v8._score_text(item))}</strong>"
        f"<span>满分 {reporting_v8._e(reporting_v8._base_text(item))}</span></div></div>"
        f"<span class='status-badge {status_class}'>{reporting_v8._e(status_text)}</span></div></div>"
        "<div class='result-area'>"
        + _summary(item)
        + _records_table(item)
        + "<p class='performance-v25-caption'>去年同期只取上一年同月同日、相同 category 与 metric_name 的 value_day / value_month / value_year；顶部房费只使用“门店收入 / 房费”。YOY＝去年同期÷今年同期。</p>"
        + reporting_v8._source_box(item)
        + f"<div class='notice'>{reporting_v8._e(item.get('note') or '')}</div>"
        + "</div></article>"
    )


def _item_one(result: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == 1
        ),
        None,
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v24.build_html(result)
    item = _item_one(result)
    if item:
        html_text = _ITEM_ONE_PATTERN.sub(lambda _: _performance_card(item), html_text, count=1)
    return html_text.replace("</head>", PERFORMANCE_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v24.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v24.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "_performance_card",
    "_records_table",
    "build_html",
    "build_markdown",
    "write_reports",
]
