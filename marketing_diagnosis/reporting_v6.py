from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v5


def _n(v: Any) -> float | None:
    try:
        if v in (None, ""):
            return None
        x = float(str(v).replace(",", ""))
        return None if x != x else x
    except Exception:
        return None


def _e(v: Any) -> str:
    return html.escape("未获取" if v is None else str(v), quote=True)


def _num(v: Any, d: int = 0) -> str:
    x = _n(v)
    return "未获取" if x is None else f"{x:,.{d}f}"


def _money(v: Any) -> str:
    x = _n(v)
    return "未获取" if x is None else f"¥{x:,.1f}"


def _pct(v: Any) -> str:
    x = _n(v)
    return "未获取" if x is None else f"{x:.1%}"


def _zh_platform(v: Any) -> str:
    return {"meituan": "美团", "ctrip": "携程", "fliggy": "飞猪", "multi": "多渠道", "unknown": "未知"}.get(str(v or "").lower(), str(v or "未获取"))


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    h = "".join(f"<th>{_e(x)}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{x if str(x).startswith('<') else _e(x)}</td>" for x in r) + "</tr>" for r in rows)
    return f"<div class='table-wrap'><table class='table'><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>"


def _period_line(period: dict[str, Any] | None) -> str:
    p = period or {}
    grain = {"mixed": "混合口径", "snapshot": "快照口径", "daily": "日粒度"}.get(str(p.get("grain") or ""), str(p.get("grain") or "数据口径"))
    note = p.get("note") or "价格、销售和竞品按可用字段汇总。"
    return f"<div class='period'><span class='badge info'>{_e(grain)}</span><span class='badge neutral'>{_e(note)}</span></div>"


def _room_type_rows(room_types: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for item in (room_types.get("items") or [])[:30]:
        rows.append([
            _zh_platform(item.get("platform")),
            item.get("room_type_name"),
            item.get("role"),
            _num(item.get("product_count")),
            _money(item.get("min_price")),
            _money(item.get("max_price")),
            _money(item.get("price_span")),
            _num(item.get("views")),
            _num(item.get("paid_orders")),
            _money(item.get("sales_revenue")),
            _pct(item.get("payment_conversion_rate")),
            _money(item.get("avg_order_value")),
            _money(item.get("sales_adr")),
            _pct(item.get("revenue_share")),
            _money(item.get("competitor_avg_price")),
            _money(item.get("own_vs_competitor_gap")),
            item.get("suggestion"),
        ])
    return rows or [["无", "未获取", "待补数据", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "未获取", "需要补充房型级商品、价格或销售数据"]]


def _room_type_cards(room_types: dict[str, Any]) -> str:
    items = room_types.get("items") or []
    main = next((x for x in items if x.get("role") == "主力房型"), None)
    weak = next((x for x in items if x.get("role") in {"高浏览低转化", "有浏览无成交"}), None)
    wide = next((x for x in items if x.get("role") == "价格跨度大"), None)
    cards = [
        ("房型数", _num(room_types.get("room_type_count")), "已识别房型/商品组合"),
        ("销售数据", "已接入" if room_types.get("has_room_type_sales") else "待补", room_types.get("missing_note")),
        ("主力房型", main.get("room_type_name") if main else "未明确", main.get("suggestion") if main else "需要房型级订单或收入判断"),
        ("转化风险", weak.get("room_type_name") if weak else "未明显触发", weak.get("suggestion") if weak else "继续观察浏览、订单和价格承接"),
        ("价格风险", wide.get("room_type_name") if wide else "未明显触发", wide.get("suggestion") if wide else "继续观察价格跨度和活动价"),
        ("分析口径", "房型级", "综合商品价格、活动商品、房型级漏斗/订单和竞品价"),
    ]
    return "<div class='grid3'>" + "".join(f"<div class='tile'><label>{_e(a)}</label><strong>{_e(b)}</strong><span>{_e(c)}</span></div>" for a, b, c in cards) + "</div>"


def _room_type_section(result: dict[str, Any]) -> str:
    room_types = ((result.get("metrics") or {}).get("room_types") or {})
    notes = room_types.get("summary") or ["房型级数据不足，建议补齐房型订单、间夜、收入、价格和竞品价。"]
    note_html = "".join(f"<p>{_e(x)}</p>" for x in notes)
    return f"""
<section class='card' id='room-types'>
  <div class='head'><div><h2>房型销售与价格分析</h2>{_period_line(room_types.get('data_period'))}<p>按具体房型拆分销售表现、价格梯度、活动覆盖和竞品价差。</p></div></div>
  <div class='body'>
    {_room_type_cards(room_types)}
    <div class='callout'>{note_html}</div>
    {_table(['渠道','房型','定位','商品数','最低价','最高价','价格跨度','浏览','订单','销售额','二转','客单价','销售ADR','收入占比','竞品均价','价差','建议'], _room_type_rows(room_types))}
    <details class='analysis' open><summary><span class='badge info'>AI分析</span> 房型分析建议</summary><div class='txt'><p>房型分析优先看销售贡献、二转、价格跨度和竞品价差。主力房型要保库存和稳定价格；高浏览低转化房型优先查页面、价格和口碑；价格跨度大的房型要复核团购、钟点房、活动价和全日价。</p></div></details>
  </div>
</section>
"""


def _inject_room_type_section(html_text: str, result: dict[str, Any]) -> str:
    section = _room_type_section(result)
    html_text = html_text.replace("<a href='#price'>价格房型</a>", "<a href='#room-types'>房型分析</a><a href='#price'>价格房型</a>")
    marker = "<section class='card' id='price'>"
    if marker in html_text:
        return html_text.replace(marker, section + marker, 1)
    return html_text.replace("</main>", section + "</main>", 1)


def build_html(result: dict) -> str:
    return _inject_room_type_section(reporting_v5.build_html(result), result)


def build_markdown(result: dict) -> str:
    return reporting_v5.build_markdown(result)


def write_reports(result: dict, output_dir: str | Path) -> dict[str, str]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "report.json"
    md_path = path / "report.md"
    html_path = path / "report.html"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(result), encoding="utf-8")
    html_path.write_text(build_html(result), encoding="utf-8")
    return {"report_json": str(json_path), "report_markdown": str(md_path), "report_html": str(html_path)}
