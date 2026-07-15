from __future__ import annotations

from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v14


RIGHTS_TABLE_STYLE = """
<style>
.rights-overview{display:grid;gap:14px}
.rights-summary{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 18px;border:1px solid #dce8e4;border-radius:13px;background:linear-gradient(135deg,#f7fbf9,#ffffff)}
.rights-summary div{display:flex;align-items:baseline;gap:12px}.rights-summary small{color:var(--muted);font-size:12px;font-weight:800}.rights-summary strong{font-size:30px;color:#26343d;line-height:1}.rights-summary span{color:var(--muted);font-size:12px}
.rights-table{width:100%;border-collapse:collapse;min-width:620px;border:1px solid #e1eae7;border-radius:12px;overflow:hidden}
.rights-table th,.rights-table td{padding:13px 16px;border-bottom:1px solid #e7eeeb;text-align:left;vertical-align:middle}.rights-table th{background:#f5f8f7;color:#596873;font-size:12px}.rights-table td{font-size:14px}.rights-table tbody tr:last-child td{border-bottom:0}.rights-table .rights-index{width:72px;color:#7b8a94;font-weight:800}.rights-table .rights-name{font-weight:800;color:#26343d}
.rights-scope{display:inline-flex;align-items:center;border-radius:999px;padding:6px 11px;font-size:12px;font-weight:800;background:#eef3f1;color:#5d6c75}.rights-scope.all{background:#e6f6ef;color:#11895c}.rights-scope.partial{background:#fff3df;color:#a66b12}.rights-scope.off{background:#fdebea;color:#c34339}
@media(max-width:620px){.rights-summary{align-items:flex-start}.rights-summary div{display:grid;gap:7px}.rights-table{min-width:520px}}
</style>
"""


def _display_value(value: Any) -> str:
    if value in (None, ""):
        return "暂无数据"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _scope_class(value: Any) -> str:
    text = _display_value(value)
    if "全部" in text or "全房型" in text:
        return "all"
    if "部分" in text:
        return "partial"
    if any(word in text for word in ("未", "无", "关闭", "失效")):
        return "off"
    return ""


def _rights_content(item: dict[str, Any]) -> str:
    fields = list(item.get("fields") or [])
    count_field = next(
        (field for field in fields if str(field.get("label") or "") == "已报名权益数量"),
        None,
    )
    rights = [
        field
        for field in fields
        if str(field.get("label") or "") != "已报名权益数量"
    ]
    count_value = count_field.get("value") if count_field else len(rights)

    rows: list[str] = []
    for index, field in enumerate(rights, start=1):
        label = reporting_v14._e(field.get("label") or f"权益{index}")
        raw_value = field.get("value")
        value = reporting_v14._e(_display_value(raw_value))
        scope_class = _scope_class(raw_value)
        rows.append(
            "<tr>"
            f"<td class='rights-index'>{index:02d}</td>"
            f"<td class='rights-name'>{label}</td>"
            f"<td><span class='rights-scope {scope_class}'>{value}</span></td>"
            "</tr>"
        )

    if not rows:
        rows.append(
            "<tr><td class='rights-index'>—</td>"
            "<td class='rights-name'>暂无已报名权益明细</td>"
            "<td><span class='rights-scope'>暂无数据</span></td></tr>"
        )

    count_text = reporting_v14._e(_display_value(count_value))
    return (
        "<div class='rights-overview'>"
        "<div class='rights-summary'>"
        f"<div><small>已报名权益数量</small><strong>{count_text}</strong></div>"
        f"<span>当前共展示 {len(rights)} 项权益明细</span>"
        "</div>"
        "<div class='table-scroll'><table class='rights-table'>"
        "<thead><tr><th>序号</th><th>权益名称</th><th>有效房型范围</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div></div>"
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v14.build_html(result)
    items = reporting_v14._visual_items(result)
    if 14 in items:
        html_text = reporting_v14._replace_result_area(
            html_text,
            14,
            _rights_content(items[14]),
        )
    return html_text.replace("</head>", RIGHTS_TABLE_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v14.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v14.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "RIGHTS_TABLE_STYLE",
    "_rights_content",
    "build_html",
    "build_markdown",
    "write_reports",
]
