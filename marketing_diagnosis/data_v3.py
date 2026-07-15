from __future__ import annotations

from copy import deepcopy
from typing import Any

from marketing_diagnosis.data_v2 import normalize_dataset as _base_normalize_dataset


def normalize_dataset(raw: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result = _base_normalize_dataset(raw)
    manual_rows = [dict(row) for row in deepcopy(raw or {}).get("manual_inputs") or [] if isinstance(row, dict)]
    result.setdefault("sections", {})["manual_inputs"] = manual_rows
    result.setdefault("diagnostics", {})["manual_inputs"] = {
        "section": "manual_inputs",
        "row_count": len(manual_rows),
        "missing_fields": [],
        "source_tables": sorted({str(row.get("source_table")) for row in manual_rows if row.get("source_table")}),
        "seen_fields": sorted({key for row in manual_rows for key in row}),
        "status": "ok",
    }
    return result


__all__ = ["normalize_dataset"]
