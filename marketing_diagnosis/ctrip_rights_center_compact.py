from __future__ import annotations

import re
from typing import Any

from marketing_diagnosis import ctrip_report as stable_report
from marketing_diagnosis import ctrip_report_v54 as report


_ORIGINAL_GENERIC_CARD = report.generic_card
_RESULT_AREA_RE = re.compile(
    r"(<div class='result-area'>).*?(<div class='ctrip-source-v55'>)",
    re.S,
)

RIGHTS_STYLE = """
<style id='CTRIP_RIGHTS_CENTER_COMPACT'>
.ctrip-rights-layout-v66{display:grid;grid-template-columns:minmax(210px,.38fr) minmax(0,1.62fr);gap:14px;align-items:stretch}
.ctrip-rights-count-v66{display:flex;min-height:156px;flex-direction:column;justify-content:center;padding:22px;border:1px solid #d6e8df;border-radius:12px;background:linear-gradient(145deg,#edf8f3,#f8fbfa)}
.ctrip-rights-count-v66 small{color:#587067;font-size:12px;font-weight:800}
.ctrip-rights-count-v66 strong{display:block;margin-top:9px;color:#16845b;font-size:38px;line-height:1;font-variant-numeric:tabular-nums}
.ctrip-rights-count-v66 span{display:block;margin-top:10px;color:#7a8982;font-size:12px}
.ctrip-rights-panel-v66{min-width:0;padding:16px;border:1px solid #dfe7e4;border-radius:12px;background:#fff}
.ctrip-rights-panel-head-v66{display:flex;align-items:center;justify-content:space-between;gap:14px}
.ctrip-rights-panel-head-v66 small{display:block;color:#65746d;font-size:12px;font-weight:800}
.ctrip-rights-panel-head-v66 strong{display:block;margin-top:4px;color:#26343d;font-size:15px}
.ctrip-rights-panel-head-v66>span{flex:0 0 auto;padding:5px 10px;border-radius:999px;background:#e8f5ef;color:#16845b;font-size:11px;font-weight:850}
.ctrip-rights-grid-v66{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-top:14px}
.ctrip-rights-item-v66{min-height:92px;padding:12px 13px;border:1px solid #deebe5;border-radius:9px;background:#f7fbf9;overflow-wrap:anywhere}
.ctrip-rights-item-v66.inactive{border-color:#e5e8e7;background:#fafafa}
.ctrip-rights-item-head-v66{display:flex;align-items:center;gap:9px}
.ctrip-rights-item-head-v66 strong{min-width:0;flex:1;color:#2c4037;font-size:13px;line-height:1.35}
.ctrip-rights-check-v66{display:grid;width:24px;height:24px;flex:0 0 24px;place-items:center;border-radius:50%;background:#dff3e9;color:#16845b;font-size:13px;font-weight:900}
.ctrip-rights-item-v66.inactive .ctrip-rights-check-v66{background:#ecefee;color:#77827d}
.ctrip-rights-item-v66.pending .ctrip-rights-check-v66{background:#fff1d8;color:#a56a12}
.ctrip-rights-status-v66{flex:0 0 auto;padding:3px 7px;border-radius:999px;background:#e1f4ea;color:#16845b;font-size:10px;font-style:normal;font-weight:850;white-space:nowrap}
.ctrip-rights-status-v66.inactive{background:#ecefee;color:#6f7974}
.ctrip-rights-status-v66.pending{background:#fff1d8;color:#9b6517}
.ctrip-rights-rule-v66{display:grid;gap:3px;margin:10px 0 0;padding-top:9px;border-top:1px solid #e7efeb}
.ctrip-rights-rule-v66 small{color:#8a9690;font-size:10px;font-weight:700}
.ctrip-rights-rule-v66 span{color:#53645c;font-size:12px;line-height:1.45}
.ctrip-rights-item-v66.inactive .ctrip-rights-rule-v66 span{color:#84908a}
.ctrip-rights-empty-v66{grid-column:1/-1;min-height:72px;display:flex;align-items:center;justify-content:center;padding:12px;border:1px dashed #d8e4df;border-radius:9px;background:#fafcfb;color:#8a9791;font-size:12px}
@media(max-width:900px){.ctrip-rights-layout-v66{grid-template-columns:1fr}.ctrip-rights-count-v66{min-height:auto}.ctrip-rights-grid-v66{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.ctrip-rights-grid-v66{grid-template-columns:1fr}.ctrip-rights-panel-head-v66{align-items:flex-start;flex-direction:column}}
</style>
"""


def _format_count(value: Any, fallback: int | None = None) -> str:
    if value not in (None, ""):
        text = str(value).strip()
        if text.endswith("项"):
            return text
        try:
            number = float(text)
            return f"{int(number) if number.is_integer() else number:g}项"
        except (TypeError, ValueError):
            return text
    return f"{fallback}项" if fallback is not None else "待接入"


def _status_kind(value: Any) -> str:
    text = str(value or "").strip().lower()
    if any(word in text for word in ("已取消", "未生效", "已失效", "取消", "失效", "inactive", "disabled", "closed", "cancelled", "canceled")):
        return "inactive"
    if any(word in text for word in ("已生效", "已报名", "生效中", "active", "enabled", "joined", "open")):
        return "active"
    return "pending"


def _rights_data(
    item_spec: tuple[Any, ...],
    payload: dict[str, Any],
) -> tuple[list[dict[str, str]], str, str]:
    rows = report.fields(item_spec, payload)
    raw_details = payload.get("rights_details")
    details: list[dict[str, str]] = []

    if isinstance(raw_details, list):
        for index, value in enumerate(raw_details):
            if not isinstance(value, dict):
                continue
            name = str(value.get("right_name") or value.get("name") or f"权益{index + 1}").strip()
            status = str(value.get("right_status") or value.get("status") or "状态待确认").strip()
            details.append(
                {
                    "name": name,
                    "rules": str(value.get("rights_rules") or value.get("rules") or "规则待补充").strip(),
                    "status": status,
                    "kind": str(value.get("status_kind") or _status_kind(status)).strip(),
                }
            )

    if not details:
        rights = payload.get("rights_list")
        if not isinstance(rights, list):
            raw = next(
                (row.get("value") for row in rows if row.get("label") == "权益清单"),
                "",
            )
            rights = [value.strip() for value in str(raw or "").split("、") if value.strip()]
        details = [
            {
                "name": str(value).strip(),
                "rules": "规则待补充",
                "status": "状态待确认",
                "kind": "pending",
            }
            for value in rights
            if str(value).strip()
        ]

    count_field = next(
        (row.get("value") for row in rows if row.get("label") == "已报名权益"),
        None,
    )
    active_value = payload.get("active_rights_count")
    active_count = _format_count(
        active_value if active_value not in (None, "") else count_field,
        sum(detail["kind"] == "active" for detail in details) if details else None,
    )
    total_count = _format_count(payload.get("total_rights_count"), len(details))
    return details, active_count, total_count


def _rights_content(item_spec: tuple[Any, ...], payload: dict[str, Any]) -> str:
    details, active_count, total_count = _rights_data(item_spec, payload)
    items: list[str] = []
    for detail in details:
        kind = detail["kind"] if detail["kind"] in {"active", "inactive", "pending"} else "pending"
        symbol = "✓" if kind == "active" else "×" if kind == "inactive" else "?"
        items.append(
            f"<div class='ctrip-rights-item-v66 {kind}'>"
            "<div class='ctrip-rights-item-head-v66'>"
            f"<span class='ctrip-rights-check-v66'>{symbol}</span>"
            f"<strong>{report.e(detail['name'])}</strong>"
            f"<em class='ctrip-rights-status-v66 {kind}'>{report.e(detail['status'])}</em>"
            "</div>"
            "<p class='ctrip-rights-rule-v66'><small>权益规则</small>"
            f"<span>{report.e(detail['rules'])}</span></p></div>"
        )

    item_html = "".join(items)
    if not item_html:
        empty_text = "待接入权益清单" if payload.get("data_status") == "missing" else "暂无已报名权益"
        item_html = f"<div class='ctrip-rights-empty-v66'>{report.e(empty_text)}</div>"

    return (
        "<div class='ctrip-rights-layout-v66'>"
        "<div class='ctrip-rights-count-v66'>"
        f"<small>已生效权益</small><strong>{report.e(active_count)}</strong>"
        "<span>已取消权益不计入当前得分</span></div>"
        "<div class='ctrip-rights-panel-v66'>"
        "<div class='ctrip-rights-panel-head-v66'><div>"
        "<small>权益清单</small><strong>权益规则与当前状态</strong></div>"
        f"<span>{report.e(active_count)}生效 / 共{report.e(total_count)}</span></div>"
        f"<div class='ctrip-rights-grid-v66'>{item_html}</div>"
        "</div></div>"
    )


def generic_card(result: dict[str, Any], item_spec: tuple[Any, ...]) -> str:
    html_text = _ORIGINAL_GENERIC_CARD(result, item_spec)
    if item_spec[0] != 13:
        return html_text

    payload = report.item_payload(result, item_spec)
    content = _rights_content(item_spec, payload)
    return _RESULT_AREA_RE.sub(
        lambda match: match.group(1) + content + match.group(2),
        html_text,
        count=1,
    )


report.generic_card = generic_card
stable_report.generic_card = generic_card
report.CTRIP_STYLE += RIGHTS_STYLE


__all__ = ["RIGHTS_STYLE", "generic_card"]
