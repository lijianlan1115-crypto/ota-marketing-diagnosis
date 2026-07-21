from __future__ import annotations

from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_runtime_v51 as upstream
from marketing_diagnosis.ctrip_report_v54 import build_html as build_ctrip_page
from marketing_diagnosis.dual_channel_report_v56 import build_html as build_dual_channel_page


def build_meituan_html(result: dict[str, Any]) -> str:
    """Generate the existing Meituan channel view directly from result data."""

    return upstream.build_html(result)


def build_ctrip_html(result: dict[str, Any]) -> str:
    """Generate the Ctrip channel view directly from result data."""

    return build_ctrip_page(result)


def build_dual_channel_html(result: dict[str, Any]) -> str:
    """Generate the production single-file report selected by ?channel=..."""

    return build_dual_channel_page(result)


def build_html(result: dict[str, Any]) -> str:
    """Generate the final report.html containing Meituan and Ctrip views."""

    return build_dual_channel_html(result)


def build_markdown(result: dict[str, Any]) -> str:
    return upstream.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    """Write one final report.html while preserving existing JSON/Markdown outputs."""

    paths = upstream.write_reports(result, output_dir)
    report_path = Path(paths["report_html"])
    report_path.write_text(build_html(result), encoding="utf-8")

    # Older development versions created extra HTML files. Do not create them
    # anymore, and remove stale copies when the same output directory is reused.
    for stale_name in ("ctrip_report.html", "双渠道诊断报告预览.html"):
        stale_path = report_path.with_name(stale_name)
        if stale_path.exists():
            stale_path.unlink()

    paths["report_html"] = str(report_path)
    paths.pop("ctrip_report_html", None)
    paths.pop("dual_channel_report_html", None)
    paths.pop("meituan_report_html", None)
    return paths


__all__ = [
    "build_ctrip_html",
    "build_dual_channel_html",
    "build_html",
    "build_markdown",
    "build_meituan_html",
    "write_reports",
]
