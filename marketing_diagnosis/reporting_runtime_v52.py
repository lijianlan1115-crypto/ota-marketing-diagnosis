from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_runtime_v51 as upstream
from marketing_diagnosis.ctrip_report_v54 import build_html as build_ctrip_page
from marketing_diagnosis.dual_channel_report_v56 import build_html as build_dual_channel_page


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
    """Legacy two-file switch kept for backward-compatible single-channel output."""

    return (
        "<div class='ota-channel-switch-v52' aria-label='报告渠道'>"
        f"<a class='{'active' if active == 'meituan' else ''}' href='report.html'>美团</a>"
        f"<a class='{'active' if active == 'ctrip' else ''}' href='ctrip_report.html'>携程</a>"
        "</div>"
    )


def inject_channel_switch(html_text: str, active: str = "meituan") -> str:
    """Add legacy links between separately generated channel files."""

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


def build_meituan_html(result: dict[str, Any]) -> str:
    """Generate the existing Meituan report directly from result data."""

    return upstream.build_html(result)


def build_ctrip_html(result: dict[str, Any]) -> str:
    """Generate the Ctrip report directly from result data."""

    return build_ctrip_page(result)


def build_dual_channel_html(result: dict[str, Any]) -> str:
    """Generate one HTML controlled by ?channel=meituan or ?channel=ctrip."""

    return build_dual_channel_page(result)


def build_html(result: dict[str, Any]) -> str:
    """Backward-compatible Meituan-only HTML builder."""

    return build_meituan_html(result)


def build_markdown(result: dict[str, Any]) -> str:
    return upstream.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    """Write legacy files plus the primary single-file dual-channel report."""

    paths = upstream.write_reports(result, output_dir)
    report_path = Path(paths["report_html"])

    # Keep existing single-channel artifacts for compatibility with old links.
    report_path.write_text(
        inject_channel_switch(report_path.read_text(encoding="utf-8"), "meituan"),
        encoding="utf-8",
    )
    ctrip_path = report_path.with_name("ctrip_report.html")
    ctrip_path.write_text(inject_channel_switch(build_ctrip_html(result), "ctrip"), encoding="utf-8")

    # Primary customer preview: one code-generated HTML, selected with ?channel=...
    dual_path = report_path.with_name("双渠道诊断报告预览.html")
    dual_path.write_text(build_dual_channel_html(result), encoding="utf-8")

    paths["meituan_report_html"] = str(report_path)
    paths["ctrip_report_html"] = str(ctrip_path)
    paths["dual_channel_report_html"] = str(dual_path)
    return paths


__all__ = [
    "build_ctrip_html",
    "build_dual_channel_html",
    "build_html",
    "build_markdown",
    "build_meituan_html",
    "inject_channel_switch",
    "write_reports",
]
