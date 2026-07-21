from __future__ import annotations

from typing import Any

from marketing_diagnosis import dual_channel_report_v56 as upstream
from marketing_diagnosis.ctrip_report_v59 import build_html as build_ctrip_page


def build_html(result: dict[str, Any]) -> str:
    """Generate the existing dual-channel report with the revised Ctrip item 04."""

    meituan_html = upstream._scope_search_queries(upstream.meituan_report.build_html(result))
    ctrip_html = upstream._scope_search_queries(build_ctrip_page(result))
    meituan_head, meituan_body = upstream._document_parts(meituan_html)
    ctrip_head, ctrip_body = upstream._document_parts(ctrip_html)

    meituan_page = upstream._balanced_element(meituan_body, "div", "page")
    ctrip_page = upstream._balanced_element(ctrip_body, "div", "page")
    rendered_meituan_page = upstream._annotate_meituan(meituan_page)
    rendered_ctrip_page = upstream._scope_ctrip(ctrip_page)

    output = meituan_html.replace(meituan_page, rendered_meituan_page + rendered_ctrip_page, 1)
    output = upstream._inject_switch(output)

    extra_styles = upstream._extra_blocks(upstream.STYLE_RE, meituan_head, ctrip_head)
    output = output.replace("</head>", extra_styles + upstream.DUAL_STYLE + "</head>", 1)

    extra_scripts = upstream._extra_blocks(
        upstream.SCRIPT_RE,
        meituan_body,
        upstream._scope_ctrip(ctrip_body),
    )
    output = output.replace("</body>", extra_scripts + upstream.DUAL_SCRIPT + "</body>", 1)
    return output


__all__ = ["build_html"]
