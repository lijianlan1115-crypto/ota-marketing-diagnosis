from __future__ import annotations

from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v14, reporting_v15


EXPOSURE_COMPACT_STYLE = """
<style>
.exposure-layout-v16{display:grid;grid-template-columns:minmax(0,1fr) minmax(360px,.82fr);gap:18px;align-items:stretch}
.exposure-metrics-v16{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.exposure-metric-v16{display:flex;flex-direction:column;justify-content:center;min-height:132px;padding:18px 20px;border:1px solid #dfe8e5;border-radius:13px;background:linear-gradient(145deg,#fbfdfc,#f7faf9)}
.exposure-metric-v16 small{display:block;color:var(--muted);font-size:12px;font-weight:800;line-height:1.4}
.exposure-metric-v16 strong{display:block;margin-top:10px;color:#26343d;font-size:28px;line-height:1.15}
.exposure-donut-v16{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:276px;padding:20px;border:1px solid #dfe8e5;border-radius:14px;background:linear-gradient(145deg,#fff,#f7faf9)}
.exposure-donut-ring-v16{width:184px;height:184px;border-radius:50%;display:grid;place-items:center;position:relative}
.exposure-donut-ring-v16:after{content:'';position:absolute;inset:30px;border-radius:50%;background:#fff;box-shadow:inset 0 0 0 1px #eef2f0}
.exposure-donut-value-v16{position:relative;z-index:1;text-align:center}.exposure-donut-value-v16 strong{display:block;font-size:39px;color:#26343d}.exposure-donut-value-v16 span{display:block;margin-top:5px;color:var(--muted);font-size:13px}
@media(max-width:900px){.exposure-layout-v16{grid-template-columns:1fr}.exposure-donut-v16{min-height:240px}}
@media(max-width:560px){.exposure-metrics-v16{grid-template-columns:1fr}.exposure-metric-v16{min-height:106px}}
</style>
"""


def _metric(label: str, value: str) -> str:
    return (
        "<div class='exposure-metric-v16'>"
        f"<small>{reporting_v14._e(label)}</small>"
        f"<strong>{reporting_v14._e(value)}</strong>"
        "</div>"
    )


def _exposure_content(item: dict[str, Any]) -> str:
    total = reporting_v14._field(item, "整体曝光（近30天）")
    non_ad = reporting_v14._field(item, "非广告曝光")
    ad = reporting_v14._field(item, "广告曝光")
    ratio_raw = reporting_v14._field(item, "广告曝光占比")
    ratio = reporting_v14._fraction(ratio_raw)
    ratio_pct = 0.0 if ratio is None else ratio * 100
    ratio_text = "—" if ratio is None else f"{ratio_pct:.2f}%"
    donut_background = (
        "#edf2f0"
        if ratio is None
        else f"conic-gradient(#7189cf 0 {ratio_pct:.4f}%,#e8efec {ratio_pct:.4f}% 100%)"
    )

    return (
        "<div class='exposure-layout-v16'>"
        "<div class='exposure-metrics-v16'>"
        + _metric("整体曝光（近30天）", reporting_v14._plain(total))
        + _metric("非广告曝光", reporting_v14._plain(non_ad))
        + _metric("广告曝光", reporting_v14._plain(ad))
        + _metric("广告曝光占比", ratio_text)
        + "</div>"
        + "<div class='exposure-donut-v16'>"
        + f"<div class='exposure-donut-ring-v16' style='background:{donut_background}'>"
        + f"<div class='exposure-donut-value-v16'><strong>{reporting_v14._e(ratio_text)}</strong><span>广告曝光占比</span></div></div>"
        + "</div></div>"
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v15.build_html(result)
    items = reporting_v14._visual_items(result)
    if 3 in items:
        html_text = reporting_v14._replace_result_area(
            html_text,
            3,
            _exposure_content(items[3]),
        )
    return html_text.replace("</head>", EXPOSURE_COMPACT_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v15.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v15.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "EXPOSURE_COMPACT_STYLE",
    "_exposure_content",
    "build_html",
    "build_markdown",
    "write_reports",
]
