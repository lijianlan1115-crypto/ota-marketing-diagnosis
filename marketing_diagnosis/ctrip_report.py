from __future__ import annotations

from datetime import datetime
from typing import Any

from marketing_diagnosis import reporting_v30, reporting_v35, reporting_v37
from marketing_diagnosis import ctrip_report_v54 as upstream
from marketing_diagnosis.ctrip_psi_v53 import card as psi_card
from marketing_diagnosis.ctrip_user_profile_report import STYLE as PROFILE_STYLE
from marketing_diagnosis.ctrip_user_profile_report import card as profile_card


SPECS = upstream.SPECS


def cards_html(result: dict[str, Any]) -> str:
    item_one = upstream.pms_item(result, 1)
    item_two = upstream.pms_item(result, 2)
    cards = [
        reporting_v37._performance_card(item_one),
        reporting_v35._clean_customer_html(reporting_v30._room_type_card(item_two)),
    ]
    for item_spec in SPECS[2:]:
        no = item_spec[0]
        if no == 4:
            cards.append(profile_card(result))
        elif no == 6:
            cards.append(upstream.patch_psi_score(psi_card(result, "rule-6"), result))
        else:
            cards.append(upstream.generic_card(result, item_spec))
    return "".join(cards)


def build_head() -> str:
    head = upstream.build_head()
    return head.replace("</head>", PROFILE_STYLE + "</head>", 1)


def build_html(result: dict[str, Any]) -> str:
    """Generate the Ctrip report with the stable item-04 profile renderer."""

    hotel = result.get("hotel_name") or result.get("hotel_id") or "酒店"
    start = result.get("period_start") or "未标注"
    end = result.get("period_end") or "未标注"
    body = (
        "<body><header class='topbar'><div class='topbar-inner'>"
        "<div class='brand'><h1>酒店 OTA 全面诊断报告</h1>"
        f"<p>{upstream.e(hotel)}｜诊断周期：{upstream.e(start)} 至 {upstream.e(end)}｜生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        "</div><div class='top-actions'>"
        "<select class='scope-select'><option>携程综合诊断</option><option>PMS经营数据</option>"
        "<option>携程 eBooking 数据</option></select>"
        "<button class='btn primary' onclick='window.print()'>导出报告</button>"
        "</div></div></header>"
        f"<div class='page'>{upstream.nav_html()}<main>{upstream.overview_html(result)}{upstream.summary_html(result)}"
        f"{cards_html(result)}</main></div>{upstream.search_script()}{reporting_v37._script()}</body></html>"
    )
    return build_head() + body


__all__ = ["SPECS", "build_html", "cards_html"]
