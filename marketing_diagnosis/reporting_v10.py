from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v9


# Keep the original business item IDs. Automatic order remains source item 23,
# but is displayed as customer-facing item 21 in the compact configuration table.
_CONFIG_NUMBERS = (15, 16, 17, 18, 19, 20, 23)
_STATUS_META = {
    "success": ("已形成结果", "open"),
    "zero": ("真实为0", "closed"),
    "pending_rule": ("待确认", "pending"),
    "missing": ("未取到", "pending"),
    "error": ("查询失败", "pending"),
}
_POSITIVE = {"OPEN", "ACTIVE", "ENABLED", "SUCCESS", "TRUE", "YES", "1", "已开通"}
_NEGATIVE = {"CLOSED", "INACTIVE", "DISABLED", "FAILED", "FALSE", "NO", "0", "未开通"}
_PENDING = {"PENDING", "UNKNOWN", "UNCONFIRMED", "WAITING", "待确认", "未确定"}


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _field(item: dict[str, Any], label: str) -> Any:
    for field in item.get("fields") or []:
        if str(field.get("label") or "") == label:
            return field.get("value")
    return None


def _state(value: Any) -> str:
    if value in (None, ""):
        return "pending"
    text = str(value).strip().upper()
    if text in _POSITIVE:
        return "open"
    if text in _NEGATIVE:
        return "closed"
    if text in _PENDING:
        return "pending"
    return "pending"


def _state_text(value: Any) -> str:
    if value in (None, ""):
        return "待确认"
    return {
        "open": "已开通",
        "closed": "未开通",
        "pending": "待确认",
    }[_state(value)]


def _score_text(item: dict[str, Any]) -> str:
    score = item.get("item_score")
    return "待计算" if score is None else f"{float(score):g}分"


def _base_text(item: dict[str, Any]) -> str:
    return f"{float(item.get('base_score') or 0):g}分"


def _source_box(item: dict[str, Any]) -> str:
    fields = "、".join(str(value) for value in item.get("source_fields") or []) or "待补充"
    return (
        "<div class='field-standard-note'><b>数据库来源：</b>"
        f"<code>{_e(item.get('source_table') or '待确认')}</code><br>"
        f"<b>对应字段：</b>{_e(fields)}</div>"
    )


def _status_chip(value: Any) -> str:
    state = _state(value)
    return f"<span class='config-status-chip {state}'>{_e(_state_text(value))}</span>"


def _display_number(source_number: int) -> int:
    return 21 if source_number == 23 else source_number


def _config_group(items: dict[int, dict[str, Any]]) -> str:
    rows: list[str] = []
    total_score = 0.0
    total_base = 0.0

    for no in _CONFIG_NUMBERS:
        item = items.get(no) or {}
        status_key = str(item.get("data_status") or "missing")
        result_text, result_class = _STATUS_META.get(status_key, ("待确认", "pending"))
        score = item.get("item_score")
        total_base += float(item.get("base_score") or 0)
        if score is not None:
            total_score += float(score)

        open_status = _field(item, "开通状态")
        rows.append(
            f"<tr class='config-status-row' id='rule-{no}'>"
            f"<td class='config-rule-number'>{_display_number(no)}</td>"
            f"<td class='config-item-name'>{_e(item.get('item_name'))}</td>"
            f"<td>{_status_chip(open_status)}</td>"
            f"<td><span class='config-result-chip {result_class}'>{_e(result_text)}</span></td>"
            f"<td class='config-full-score'>{_e(_base_text(item))}</td>"
            f"<td><span class='config-score-chip {result_class}'>{_e(_score_text(item))}</span></td>"
            "</tr>"
        )

    source_item = items.get(15) or {}
    return (
        "<article class='diagnosis-card config-status-group' id='config-status-group'><div class='card-top'>"
        "<div class='rule-no config-group-no'>15–21</div>"
        "<div class='card-title'><h3>配置状态汇总</h3><p>按编号顺序展示各配置项的开通状态和得分。</p></div>"
        "<div class='card-tags'><div class='title-meta-item title-period'><small>统计周期</small><strong>当前配置快照</strong></div>"
        f"<div class='title-meta-item title-score'><small>当前得分</small><div class='title-score-value'><strong>{total_score:g}分</strong><span>合计{total_base:g}分</span></div></div></div></div>"
        "<div class='config-status-legend'>"
        "<div class='config-legend-item open'><strong>已开通</strong><span>当前功能已开启</span><small>按规则计分</small></div>"
        "<div class='config-legend-item closed'><strong>未开通</strong><span>当前功能未开启</span><small>0分</small></div>"
        "<div class='config-legend-item pending'><strong>待确认</strong><span>数据库为空或状态未确定</span><small>待计算</small></div>"
        "</div>"
        "<div class='result-area config-status-result'><div class='viz-card config-status-card'><div class='table-scroll'>"
        "<table class='config-status-table'><thead><tr>"
        "<th>编号</th><th>配置项</th><th>开通状态</th><th>判定结果</th><th>满分</th><th>当前得分</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        + _source_box(source_item)
        + "<div class='notice config-status-note'>状态字段为空时保持待确认，不自动判定为未开通。</div></div></div></article>"
    )


def _replace_config_group(html_text: str, result: dict[str, Any]) -> str:
    visual = result.get("visual_diagnosis") or {}
    items = {
        int(item.get("standard_item_id") or 0): item
        for item in visual.get("items") or []
    }
    if not all(number in items for number in _CONFIG_NUMBERS):
        return html_text

    pattern = re.compile(
        r"<article class='diagnosis-card config-status-group' id='config-status-group'>.*?</article>",
        re.DOTALL,
    )
    return pattern.sub(lambda _: _config_group(items), html_text, count=1)


def build_html(result: dict[str, Any]) -> str:
    return _replace_config_group(reporting_v9.build_html(result), result)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v9.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v9.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(
        _replace_config_group(html_path.read_text(encoding="utf-8"), result),
        encoding="utf-8",
    )
    return paths


__all__ = [
    "_CONFIG_NUMBERS",
    "_config_group",
    "_display_number",
    "build_html",
    "build_markdown",
    "write_reports",
]
