from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v13


CUSTOMER_PAGE_STYLE = """
<style>
/* Presentation-only improvements. No database, metric or score logic lives here. */
.summary-collapsible{margin:0 0 22px;border:1px solid #dce7e3;border-radius:16px;background:#fff;overflow:hidden;box-shadow:0 8px 24px rgba(38,52,61,.05)}
.summary-collapsible>summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:18px;padding:21px 24px;background:linear-gradient(135deg,#fbfdfc,#f4f9f7)}
.summary-collapsible>summary::-webkit-details-marker{display:none}
.summary-collapsible>summary h2{margin:0;font-size:21px;color:#26343d}.summary-collapsible>summary p{margin:6px 0 0;color:var(--muted);font-size:12px}
.summary-toggle{display:inline-flex;align-items:center;gap:8px;border:1px solid #cfe0da;border-radius:999px;padding:8px 13px;background:#fff;color:#356b59;font-size:12px;font-weight:800;white-space:nowrap}
.summary-toggle:after{content:'⌄';font-size:17px;line-height:1;transition:transform .18s ease}.summary-collapsible[open] .summary-toggle:after{transform:rotate(180deg)}
.summary-collapsible[open] .summary-toggle-label{font-size:0}.summary-collapsible[open] .summary-toggle-label:after{content:'收起总览';font-size:12px}
.summary-collapsible .section-body{border-top:1px solid #e5ece9;padding:0 22px 22px}.summary-collapsible .summary-table{margin-top:18px}
.summary-collapsible .summary-table th:last-child,.summary-collapsible .summary-table td:last-child{min-width:300px}

.customer-visual-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(320px,.75fr);gap:18px;align-items:stretch}
.customer-metric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.customer-metric{padding:16px;border:1px solid #e0e9e6;border-radius:12px;background:#fbfdfc;min-height:94px}
.customer-metric small{display:block;color:var(--muted);font-size:12px;font-weight:800}.customer-metric strong{display:block;margin-top:9px;color:#26343d;font-size:24px;line-height:1.2}
.ratio-donut-card{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:270px;border:1px solid #e0e9e6;border-radius:14px;background:linear-gradient(145deg,#fff,#f7faf9);padding:20px}
.ratio-donut{width:184px;height:184px;border-radius:50%;display:grid;place-items:center;position:relative}.ratio-donut:after{content:'';position:absolute;inset:30px;border-radius:50%;background:#fff;box-shadow:inset 0 0 0 1px #eef2f0}
.ratio-donut-value{position:relative;z-index:1;text-align:center}.ratio-donut-value strong{display:block;font-size:39px;color:#26343d}.ratio-donut-value span{display:block;margin-top:5px;color:var(--muted);font-size:13px}
.ratio-donut-card p{margin:14px 0 0;color:var(--muted);font-size:12px;text-align:center}

.user-source-v2{display:grid;gap:16px}.user-source-month{display:flex;align-items:center;justify-content:space-between;padding:14px 17px;border:1px solid #dfe9e5;border-radius:12px;background:#f8fbfa}
.user-source-month span{color:var(--muted);font-size:12px;font-weight:800}.user-source-month strong{font-size:19px;color:#26343d}
.user-share-card{padding:18px;border:1px solid #dfe8e5;border-radius:14px;background:#fff}.user-share-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:13px}
.user-share-head h4{margin:0;color:#26343d;font-size:16px}.user-share-head span{color:var(--muted);font-size:11px}
.user-share-values{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}.user-share-value{padding:12px 14px;border:1px solid #e5ece9;border-radius:10px;background:#fafcfb}
.user-share-value small{display:block;color:var(--muted);font-size:11px;font-weight:800}.user-share-value strong{display:block;margin-top:5px;font-size:21px;color:#26343d}
.user-share-bar{display:flex;min-height:48px;border-radius:11px;overflow:hidden;background:#edf2f0}.user-share-segment{display:flex;align-items:center;justify-content:center;padding:0 10px;color:#fff;font-size:12px;font-weight:900;white-space:nowrap;overflow:hidden}
.user-share-segment.primary{background:#22a77a}.user-share-segment.secondary{background:#7189cf}.user-share-segment.new{background:#d28b50}.user-share-segment.returning{background:#8c72bd}
.user-share-empty{display:flex;align-items:center;justify-content:center;min-height:48px;border:1px dashed #d5dfdb;border-radius:11px;background:#fafcfb;color:var(--muted);font-size:12px}

.metric-details-summary p{font-size:0}.metric-details-summary p:after{content:'包含当前结果与指标明细';font-size:12px}
@media(max-width:980px){.customer-visual-grid{grid-template-columns:1fr}.customer-metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.summary-collapsible>summary{align-items:flex-start;padding:18px}.customer-metric-grid,.user-share-values{grid-template-columns:1fr}.user-share-segment{font-size:10px;padding:0 5px}.summary-toggle{padding:7px 10px}}
</style>
"""


_DISPLAY_NUMBER = {23: 21, 21: 22, 22: 23}


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").rstrip("%"))
        return None if number != number else number
    except (TypeError, ValueError):
        return None


def _fraction(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    if abs(number) > 1:
        number /= 100
    return max(0.0, min(1.0, number))


def _pct(value: Any) -> str:
    number = _fraction(value)
    return "—" if number is None else f"{number * 100:.2f}%"


def _plain(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "—"
    return f"{number:,.2f}"


def _field(item: dict[str, Any], label: str) -> Any:
    for field in item.get("fields") or []:
        if str(field.get("label") or "") == label:
            return field.get("value")
    return None


def _visual_items(result: dict[str, Any]) -> dict[int, dict[str, Any]]:
    visual = result.get("visual_diagnosis") or {}
    return {
        int(item.get("standard_item_id") or 0): item
        for item in visual.get("items") or []
    }


def _metric(label: str, value: str) -> str:
    return f"<div class='customer-metric'><small>{_e(label)}</small><strong>{_e(value)}</strong></div>"


def _exposure_content(item: dict[str, Any]) -> str:
    total = _field(item, "整体曝光（近30天）")
    non_ad = _field(item, "非广告曝光")
    ad = _field(item, "广告曝光")
    ratio = _fraction(_field(item, "广告曝光占比"))
    ratio_pct = 0.0 if ratio is None else ratio * 100
    ratio_text = "—" if ratio is None else f"{ratio_pct:.2f}%"
    donut_background = (
        "#edf2f0"
        if ratio is None
        else f"conic-gradient(#7189cf 0 {ratio_pct:.4f}%,#e8efec {ratio_pct:.4f}% 100%)"
    )
    return (
        "<div class='customer-visual-grid'>"
        "<div class='customer-metric-grid'>"
        + _metric("整体曝光（近30天）", _plain(total))
        + _metric("非广告曝光", _plain(non_ad))
        + _metric("广告曝光", _plain(ad))
        + "</div>"
        + "<div class='ratio-donut-card'>"
        + f"<div class='ratio-donut' style='background:{donut_background}'><div class='ratio-donut-value'><strong>{_e(ratio_text)}</strong><span>广告曝光占比</span></div></div>"
        + "<p>圆环仅展示已计算的广告曝光占比，不改变评分结果。</p></div></div>"
    )


def _share_block(
    title: str,
    subtitle: str,
    left_label: str,
    left_value: Any,
    right_label: str,
    right_value: Any,
    left_class: str,
    right_class: str,
) -> str:
    left = _fraction(left_value)
    right = _fraction(right_value)
    values = (
        "<div class='user-share-values'>"
        f"<div class='user-share-value'><small>{_e(left_label)}</small><strong>{_e(_pct(left_value))}</strong></div>"
        f"<div class='user-share-value'><small>{_e(right_label)}</small><strong>{_e(_pct(right_value))}</strong></div>"
        "</div>"
    )
    if left is None or right is None or left + right <= 0:
        bar = "<div class='user-share-empty'>当前月份该组占比数据尚未完整接入</div>"
    else:
        total = left + right
        left_width = left / total * 100
        right_width = right / total * 100
        bar = (
            "<div class='user-share-bar'>"
            f"<div class='user-share-segment {left_class}' style='width:{left_width:.4f}%'>{_e(left_label)} {_e(_pct(left_value))}</div>"
            f"<div class='user-share-segment {right_class}' style='width:{right_width:.4f}%'>{_e(right_label)} {_e(_pct(right_value))}</div>"
            "</div>"
        )
    return (
        "<div class='user-share-card'>"
        f"<div class='user-share-head'><h4>{_e(title)}</h4><span>{_e(subtitle)}</span></div>"
        + values
        + bar
        + "</div>"
    )


def _user_source_content(item: dict[str, Any]) -> str:
    month = _field(item, "统计月份") or "—"
    return (
        "<div class='user-source-v2'>"
        f"<div class='user-source-month'><span>统计月份</span><strong>{_e(month)}</strong></div>"
        + _share_block(
            "地域来源",
            "本地用户与异地用户结构",
            "本地",
            _field(item, "本地占比"),
            "异地",
            _field(item, "异地占比"),
            "primary",
            "secondary",
        )
        + _share_block(
            "新老客户结构",
            "新客与老客用户结构",
            "新客",
            _field(item, "新客占比"),
            "老客",
            _field(item, "老客占比"),
            "new",
            "returning",
        )
        + "</div>"
    )


def _replace_result_area(html_text: str, item_number: int, content: str) -> str:
    pattern = re.compile(
        rf"(<article class='diagnosis-card'[^>]*id='rule-{item_number}'>.*?<div class='result-area'>).*?(</div><details class='output-fields-panel)",
        re.DOTALL,
    )
    return pattern.sub(lambda match: match.group(1) + content + match.group(2), html_text, count=1)


def _base_text(item: dict[str, Any]) -> str:
    if not item.get("participates_in_score"):
        return "仅展示"
    return f"{float(item.get('base_score') or 0):g}分"


def _score_text(item: dict[str, Any]) -> str:
    if not item.get("participates_in_score"):
        return "仅展示"
    score = item.get("item_score")
    return "待计算" if score is None else f"{float(score):g}分"


def _summary_collapsible(result: dict[str, Any]) -> str:
    items = list(_visual_items(result).values())
    items.sort(key=lambda item: _DISPLAY_NUMBER.get(int(item.get("standard_item_id") or 0), int(item.get("standard_item_id") or 0)))
    rows: list[str] = []
    for item in items:
        source_number = int(item.get("standard_item_id") or 0)
        display_number = _DISPLAY_NUMBER.get(source_number, source_number)
        status_key = str(item.get("data_status") or "missing")
        status_text, status_class = reporting_v8.STATUS.get(status_key, (status_key, "neutral"))
        description = reporting_v8.DESCRIPTIONS.get(source_number, "展示当前诊断结果。")
        rows.append(
            f"<tr data-status='{_e(status_key)}' data-title='{_e(item.get('item_name'))}'>"
            f"<td>{display_number:02d}</td><td><a href='#rule-{source_number}'>{_e(item.get('item_name'))}</a></td>"
            f"<td>{_e(_base_text(item))}</td><td>{_e(_score_text(item))}</td>"
            f"<td><span class='status-badge {status_class}'>{_e(status_text)}</span></td>"
            f"<td>{_e(description)}</td></tr>"
        )
    return (
        "<details id='summary' class='summary-collapsible'>"
        "<summary><div><h2>23项诊断结果总览</h2><p>汇总各项得分与状态；展开后可点击项目名称定位到页面对应位置。</p></div>"
        "<span class='summary-toggle'><span class='summary-toggle-label'>展开总览</span></span></summary>"
        "<div class='section-body'><div class='table-scroll'><table class='summary-table'>"
        "<thead><tr><th>编号</th><th>诊断项目</th><th>满分</th><th>当前得分</th><th>当前状态</th><th>诊断内容</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div></div></details>"
    )


def _replace_summary(html_text: str, result: dict[str, Any]) -> str:
    return re.sub(
        r"<section id='summary'>.*?</section>",
        lambda _: _summary_collapsible(result),
        html_text,
        count=1,
        flags=re.DOTALL,
    )


def build_html(result: dict[str, Any]) -> str:
    # reporting_v13 already contains the established numbering, HOS chart,
    # manual crown input and customer-clean rules. This layer only changes layout.
    html_text = reporting_v13.build_html(result)
    items = _visual_items(result)
    if 3 in items:
        html_text = _replace_result_area(html_text, 3, _exposure_content(items[3]))
    if 5 in items:
        html_text = _replace_result_area(html_text, 5, _user_source_content(items[5]))
    html_text = _replace_summary(html_text, result)
    return html_text.replace("</head>", CUSTOMER_PAGE_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v13.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v13.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "CUSTOMER_PAGE_STYLE",
    "_exposure_content",
    "_summary_collapsible",
    "_user_source_content",
    "build_html",
    "build_markdown",
    "write_reports",
]
