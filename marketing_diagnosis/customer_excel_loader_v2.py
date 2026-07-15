from __future__ import annotations

import re
from typing import Any

from marketing_diagnosis.customer_excel_loader import (
    IMPORT_HEADER,
    MODULE_FIELD_MAP,
    MODULE_HEADER,
    _is_imported,
    _iso_date,
    _normalize_value,
    _text,
    is_customer_excel_template,
)


MODULE_TITLE_PATTERN = re.compile(r"〔\s*系统模块\s*[：:]\s*([^〕]+)〕")


def load_customer_excel_workbook(workbook: Any) -> dict[str, list[dict[str, Any]]]:
    """Parse the compact customer template and infer blank module cells.

    The yellow extension rows in the workbook intentionally keep the visible
    module column unobtrusive. Their module is inferred from the nearest block
    title, while an explicitly supplied module value still takes precedence.
    """
    dataset: dict[str, list[dict[str, Any]]] = {}
    context: dict[str, Any] = {}
    imported_rows = 0
    skipped_rows = 0
    unsupported_modules: set[str] = set()

    for sheet in workbook.worksheets:
        headers: list[str] | None = None
        active_module = ""

        for raw in sheet.iter_rows(values_only=True):
            values = list(raw)
            text_values = [_text(value) for value in values]

            for text in text_values:
                match = MODULE_TITLE_PATTERN.search(text)
                if match:
                    active_module = _text(match.group(1))
                    break

            if IMPORT_HEADER in text_values and MODULE_HEADER in text_values:
                headers = text_values
                continue
            if not headers:
                continue

            record = {
                headers[index]: value
                for index, value in enumerate(values)
                if index < len(headers) and headers[index]
            }
            if not _is_imported(record.get(IMPORT_HEADER)):
                if any(value not in (None, "") for value in record.values()):
                    skipped_rows += 1
                continue

            module = _text(record.get(MODULE_HEADER)) or active_module
            field_map = MODULE_FIELD_MAP.get(module)
            if not module or not field_map:
                if module:
                    unsupported_modules.add(module)
                continue

            converted: dict[str, Any] = {}
            for source_name, target_name in field_map.items():
                value = record.get(source_name)
                if value in (None, ""):
                    continue
                converted[target_name] = _normalize_value(module, target_name, value, record)

            if module == "basic_info":
                if converted.get("hotel_id"):
                    context["hotel_id"] = converted["hotel_id"]
                if converted.get("hotel_name"):
                    context["hotel_name"] = converted["hotel_name"]
                if converted.get("period_start"):
                    context["period_start"] = _iso_date(converted["period_start"])
                if converted.get("period_end"):
                    context["period_end"] = _iso_date(converted["period_end"])
                imported_rows += 1
                continue

            if module == "hotel_performance_daily":
                converted.setdefault("room_type_id", "")
            converted.setdefault("source_table", f"Excel：{sheet.title}/{module}")
            if any(value not in (None, "") for key, value in converted.items() if key != "source_table"):
                dataset.setdefault(module, []).append(converted)
                imported_rows += 1

    dataset["__excel_context__"] = context
    dataset["__source_diagnostics__"] = [{
        "loader": "customer_excel_v2",
        "status": "ok",
        "imported_rows": imported_rows,
        "skipped_rows": skipped_rows,
        "unsupported_modules": sorted(unsupported_modules),
    }]
    return dataset


__all__ = ["is_customer_excel_template", "load_customer_excel_workbook"]
