from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_runtime_v51 as upstream
from marketing_diagnosis.ctrip_report_v54 import build_html as build_ctrip_page


CHANNEL_STYLE = """
<style id='OTA_CHANNEL_SWITCH_V52'>
.ota-channel-switch-v52{display:inline-flex;align-items:center;padding:3px;border:1px solid var(--line,#dfe7e4);border-radius:9px;background:#f5f8f7}
.ota-channel-switch-v52 a{height:30px;display:inline-flex;align-items:center;justify-content:center;min-width:58px;padding:0 14px;border-radius:6px;color:var(--muted,#68747f);font-size:13px;font-weight:800;text-decoration:none}
.ota-channel-switch-v52 a:hover{color:var(--green,#16845b)}
.ota-channel-switch-v52 a.active{background:#fff;color:var(--green,#16845b);box-shadow:0 2px 8px rgba(31,41,51,.12)}
@media print{.ota-channel-switch-v52{display:none!important}}
</style>
"""

_PRINT_BUTTON_RE = re.compile(
    r"(<button\b[^>]*onclick=['\"]window\.print\(\)['\"][^>]*>.*?</button>)",
    re.DOTALL | re.IGNORECASE,
)
_TOP_ACTIONS_RE = re.compile(
    r"(<div\b[^>]*class=['\"][^'\"]*\btop-actions\b[^'\"]*['\"][^>]*>)",
    re.DOTALL | re.IGNORECASE,
)
_SWITCH_RE = re.compile(
    r"<div\b[^>]*class=['\"][^'\"]*\bota-channel-switch-v52\b[^'\"]*['\"][^>]*>.*?</div>",
    re.DOTALL | re.IGNORECASE,
)


def _switch_html(active: str) -> str:
    return (
        "<div class='ota-channel-switch-v52' aria-label='报告渠道'>"
        f"<a class='{'active' if active == 'meituan' else ''}' href='report.html'>美团</a>"
        f"<a class='{'active' if active == 'ctrip' else ''}' href='ctrip_report.html'>携程</a>"
        "</div>"
    )


def inject_channel_switch(html_text: str, active: str = "meituan") -> str:
    """Add links between the two independently generated report pages."""

    if "OTA_CHANNEL_SWITCH_V52" not in html_text:
        html_text = html_text.replace("</head>", CHANNEL_STYLE + "</head>", 1)
    if "ota-channel-switch-v52" in html_text.split("</head>", 1)[-1]:
        return _SWITCH_RE.sub(_switch_html(active), html_text, count=1)

    switch = _switch_html(active)
    html_text, count = _PRINT_BUTTON_RE.subn(
        lambda match: match.group(1) + switch,
        html_text,
        count=1,
    )
    if count == 0:
        html_text, count = _TOP_ACTIONS_RE.subn(
            lambda match: match.group(1) + switch,
            html_text,
            count=1,
        )
    if count == 0:
        html_text = html_text.replace("<body>", "<body>" + switch, 1)
    return html_text


def build_ctrip_html(result: dict[str, Any]) -> str:
    """Generate the Ctrip report directly from result data."""

    return inject_channel_switch(build_ctrip_page(result), "ctrip")


def build_html(result: dict[str, Any]) -> str:
    """Keep the existing Meituan report body and scoring logic unchanged."""

    return inject_channel_switch(upstream.build_html(result), "meituan")


def build_markdown(result: dict[str, Any]) -> str:
    return upstream.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = upstream.write_reports(result, output_dir)
    report_path = Path(paths["report_html"])
    report_path.write_text(
        inject_channel_switch(report_path.read_text(encoding="utf-8"), "meituan"),
        encoding="utf-8",
    )
    ctrip_path = report_path.with_name("ctrip_report.html")
    ctrip_path.write_text(build_ctrip_html(result), encoding="utf-8")
    paths["ctrip_report_html"] = str(ctrip_path)
    return paths


__all__ = [
    "build_ctrip_html",
    "build_html",
    "build_markdown",
    "inject_channel_switch",
    "write_reports",
]
