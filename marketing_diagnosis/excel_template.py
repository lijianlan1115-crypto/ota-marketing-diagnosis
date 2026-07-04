from __future__ import annotations

from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

TEMPLATE_FILE_NAME = "s14_ota_diagnosis_template.xlsx"

SHEETS: dict[str, list[str]] = {
    "hotel_daily": ["business_date", "hotel_id", "room_count", "room_nights", "room_revenue", "adr", "occupancy_rate"],
    "hotel_monthly": ["month", "hotel_id", "room_revenue", "room_nights", "adr", "occupancy_rate", "revpar"],
    "ota_funnel": ["business_date", "platform", "room_type_name", "exposure", "exposure_people", "views", "paid_orders", "sales_revenue", "sold_room_nights", "payment_conversion_rate", "period_type"],
    "products": ["snapshot_time", "platform", "product_name", "room_type_name", "listed_price", "final_price", "group_buy", "hour_room"],
    "promotions": ["snapshot_time", "platform", "activity_name", "activity_status", "start_date", "end_date"],
    "promotion_products": ["snapshot_time", "platform", "activity_name", "product_name", "room_type_name", "activity_price", "activity_status"],
    "reviews": ["review_date", "platform", "rating", "is_negative", "is_replied", "review_content", "reply_content"],
    "review_overviews": ["snapshot_time", "platform", "review_count", "rating_avg", "negative_review_count", "negative_review_rate", "unreplied_review_count"],
    "review_rankings": ["snapshot_time", "platform", "rank_item_name", "rank_item_count", "sentiment"],
    "nearby_events": ["event_name", "event_start_date", "event_end_date", "distance_km", "countdown_days", "event_type", "expected_demand"],
    "competitors": ["business_date", "platform", "competitor_name", "room_type_name", "price", "rank", "rating", "sold_rooms", "activity_tag"],
}

INSTRUCTIONS = [
    ["使用说明", "说明"],
    ["1", "每个业务模块对应一个 sheet，sheet 名不要修改。"],
    ["2", "第一行是字段名，不要删除；从第二行开始填写真实数据。"],
    ["3", "日期建议使用 YYYY-MM-DD；月份建议使用 YYYY-MM。"],
    ["4", "ota_funnel 建议填写 room_type_name，这样可以做具体房型销售、二转、单价和收入贡献分析。"],
    ["5", "曝光量缺失但有曝光人数时，可以填写 exposure_people，系统会明确标记为临时替代口径。"],
    ["6", "review_overviews 是平台累计/概览快照；reviews 是评论明细，二者不要混填。"],
    ["7", "没有的数据可以留空，报告会显示数据缺口，不会把缺字段当经营差。"],
]


def _style_sheet(ws) -> None:
    header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    for col_idx in range(1, ws.max_column + 1):
        letter = get_column_letter(col_idx)
        width = max(14, min(28, len(str(ws.cell(1, col_idx).value or "")) + 4))
        ws.column_dimensions[letter].width = width
    ws.row_dimensions[1].height = 24


def _write_sheet(wb: Workbook, name: str, headers: Iterable[str]) -> None:
    ws = wb.create_sheet(title=name)
    ws.append(list(headers))
    _style_sheet(ws)


def build_excel_template(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "填写说明"
    for row in INSTRUCTIONS:
        ws.append(row)
    _style_sheet(ws)
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 90
    for name, headers in SHEETS.items():
        _write_sheet(wb, name, headers)
    wb.save(output_path)
    return output_path


def ensure_excel_template(output_root: str | Path) -> Path:
    template_path = Path(output_root) / "_templates" / TEMPLATE_FILE_NAME
    build_excel_template(template_path)
    return template_path
