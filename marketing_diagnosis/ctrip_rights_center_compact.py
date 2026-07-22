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
.ctrip-rights-count-v66{display:flex;min-height:138px;flex-direction:column;justify-content:center;padding:22px;border:1px solid #d6e8df;border-radius:12px;background:linear-gradient(145deg,#edf8f3,#f8fbfa)}
.ctrip-rights-count-v66 small{color:#587067;font-size:12px;font-weight:800}
.ctrip-rights-count-v66 strong{display:block;margin-top:9px;color:#16845b;font-size:38px;line-height:1;font-variant-numeric:tabular-nums}
.ctrip-rights-count-v66 span{display:block;margin-top:10px;color:#7a8982;font-size:12px}
.ctrip-rights-panel-v66{min-width:0;padding:16px;border:1px solid #dfe7e4;border-radius:12px;background:#fff}
.ctrip-rights-panel-head-v66{display:flex;align-items:center;justify-content:space-between;gap:14px}
.ctrip-rights-panel-head-v66 small{display:block;color:#65746d;font-size:12px;font-weight:800}
.ctrip-rights-panel-head-v66 strong{display:block;margin-top:4px;color:#26343d;font-size:15px}
.ctrip-rights-panel-head-v66 span{flex:0 0 auto;padding:5px 10px;border-radius:999px;background:#e8f5ef;color:#16845b;font-size:11px;font-weight:850}
.ctrip-rights-grid-v66{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin-top:14px}
.ctrip-rights-item-v66{display:flex;min-height:58px;align-items:center;gap:10px;padding:11px 13px;border:1px solid #deebe5;border-radius:9px;background:#f7fbf9;color:#2c4037;font-size:13px;font-weight:800;overflow-wrap:anywhere}
.ctrip-rights-check-v66{display:grid;width:24px;height:24px;flex:0 0 24px;place-items:center;border-radius:50%;background:#dff3e9;color:#16845b;font-size:13px;font-weight:900}
.ctrip-rights-empty-v66{grid-column:1/-1;min-height:58px;display:flex;align-items:center;justify-content:center;padding:12px;border:1px dashed #d8e4df;border-radius:9px;background:#fafcfb;color:#8a9791;font-size:12px}
@media(max-width:900px){.ctrip-rights-layout-v66{grid-template-columns:1fr}.ctrip-rights-count-v66{min-height:auto}.ctrip-rights-grid-v66{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.ctrip-rights-grid-v66{grid-template-columns:1fr}.ctrip-rights-panel-head-v66{align-items:flex-start;flex-direction:column}}
</style>
"""


def _rights_data(item_spec: tuple[Any, ...], payload: dict[str, Any]) -> tuple[list[str], str]:
    rows = report.fields(item_spec, payload)
    rights = payload.get("rights_list")
    if not isinstance(rights, list):
        raw = next(
            (row.get("value") for row in rows if row.get("label") == "权益清单"),
            "",
        )
        rights = [value.strip() for value in str(raw or "").split("、") if value.strip()]

    normalized = [str(value).strip() for value in rights if str(value).strip()]
    count = next(
        (row.get("value") for row in rows if row.get("label") == "已报名权益"),
        None,
    )
    if count in (None, ""):
        count_text = f"{len(normalized)}项" if normalized else "待接入"
    else:
        count_text = str(count).strip()
        if count_text.replace(".", "", 1).isdigit() and not count_text.endswith("项"):
            count_text = f"{count_text}项"
    return normalized, count_text


def _rights_content(item_spec: tuple[Any, ...], payload: dict[str, Any]) -> str:
    rights, count_text = _rights_data(item_spec, payload)
    item_html = "".join(
        "<div class='ctrip-rights-item-v66'>"
        "<span class='ctrip-rights-check-v66'>✓</span>"
        f"<span>{report.e(value)}</span></div>"
        for value in rights
    )
    if not item_html:
        empty_text = "待接入权益清单" if payload.get("data_status") == "missing" else "暂无已报名权益"
        item_html = f"<div class='ctrip-rights-empty-v66'>{report.e(empty_text)}</div>"

    return (
        "<div class='ctrip-rights-layout-v66'>"
        "<div class='ctrip-rights-count-v66'>"
        f"<small>已报名权益</small><strong>{report.e(count_text)}</strong>"
        "<span>当前生效权益数量</span></div>"
        "<div class='ctrip-rights-panel-v66'>"
        "<div class='ctrip-rights-panel-head-v66'><div>"
        "<small>权益清单</small><strong>当前已报名权益明细</strong></div>"
        f"<span>共 {report.e(count_text)}</span></div>"
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
