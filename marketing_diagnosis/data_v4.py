from __future__ import annotations

from copy import deepcopy
from typing import Any

from marketing_diagnosis.data_v3 import normalize_dataset as _base_normalize_dataset


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _scan_order_summary(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Build the item-07 summary from an independent ``scan_orders`` section.

    Some Feishu/Excel loaders provide scan orders as their own section instead of
    placing the COUNT summary in ``ota_funnel``. Older normalization discarded
    that section, which made item 07 show "数据未取到" even though source rows had
    been loaded. Each detail row counts as one order unless an explicit
    ``scan_order_count`` is present.
    """

    if not rows:
        return None

    total = 0.0
    matched = 0
    dates: list[str] = []
    source_tables: set[str] = set()
    for row in rows:
        explicit = _number(row.get("scan_order_count"))
        if explicit is not None:
            total += explicit
            matched += 1
        elif any(row.get(key) not in (None, "") for key in ("order_id", "scan_time", "business_date")):
            total += 1
            matched += 1
        else:
            fallback = next(
                (
                    _number(row.get(key))
                    for key in ("order_count", "count", "total_count")
                    if _number(row.get(key)) is not None
                ),
                None,
            )
            if fallback is not None:
                total += fallback
                matched += 1

        day = str(row.get("scan_time") or row.get("business_date") or "")[:10]
        if day:
            dates.append(day)
        source = str(row.get("source_table") or row.get("__source_table") or "").strip()
        if source:
            source_tables.add(source)

    if matched == 0:
        return None

    value: int | float = int(total) if float(total).is_integer() else total
    return {
        "platform": "meituan",
        "period_type": "scan_order_summary",
        "scan_order_count": value,
        "scan_order_date_column": "scan_time" if any(row.get("scan_time") not in (None, "") for row in rows) else None,
        "scan_order_period_start": min(dates) if dates else None,
        "scan_order_period_end": max(dates) if dates else None,
        "source_table": ", ".join(sorted(source_tables)) or "scan_orders",
        "summary_source": "normalized scan_orders section",
    }


def _raw_rows(raw: dict[str, Any], section: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in deepcopy(raw or {}).get(section) or []
        if isinstance(row, dict)
    ]


def normalize_dataset(raw: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result = _base_normalize_dataset(raw)
    raw_scan_rows = _raw_rows(raw, "scan_orders")
    raw_ctrip_rights_rows = _raw_rows(raw, "ctrip_joined_rights")
    raw_ctrip_status_rows = _raw_rows(raw, "ctrip_promotion_status")
    raw_ctrip_profile_rows = _raw_rows(raw, "ctrip_userprofile_distribution")
    raw_ctrip_review_rows = _raw_rows(raw, "ctrip_review_overview")
    raw_ctrip_yesterday_rows = _raw_rows(raw, "ctrip_review_yesterday")
    raw_ctrip_hourly_order_rows = _raw_rows(raw, "ctrip_hourly_orders")

    sections = result.setdefault("sections", {})
    sections["scan_orders"] = raw_scan_rows
    sections["ctrip_joined_rights"] = raw_ctrip_rights_rows
    sections["ctrip_promotion_status"] = raw_ctrip_status_rows
    sections["ctrip_userprofile_distribution"] = raw_ctrip_profile_rows
    sections["ctrip_review_overview"] = raw_ctrip_review_rows
    sections["ctrip_review_yesterday"] = raw_ctrip_yesterday_rows
    sections["ctrip_hourly_orders"] = raw_ctrip_hourly_order_rows

    funnel_rows = list(sections.get("ota_funnel") or [])
    has_summary = any(
        str(row.get("period_type") or "") == "scan_order_summary"
        or row.get("scan_order_count") is not None
        for row in funnel_rows
    )
    summary = None if has_summary else _scan_order_summary(raw_scan_rows)
    if summary is not None:
        funnel_rows.append(summary)
        sections["ota_funnel"] = funnel_rows

    result.setdefault("diagnostics", {})["scan_orders"] = {
        "section": "scan_orders",
        "row_count": len(raw_scan_rows),
        "summary_created": summary is not None,
        "summary_preserved": has_summary,
        "source_tables": sorted(
            {
                str(row.get("source_table") or row.get("__source_table"))
                for row in raw_scan_rows
                if row.get("source_table") or row.get("__source_table")
            }
        ),
        "status": "ok" if raw_scan_rows or has_summary else "empty",
    }
    result.setdefault("diagnostics", {})["ctrip_userprofile_distribution"] = {
        "section": "ctrip_userprofile_distribution",
        "row_count": len(raw_ctrip_profile_rows),
        "source_tables": sorted(
            {
                str(row.get("source_table") or row.get("__source_table"))
                for row in raw_ctrip_profile_rows
                if row.get("source_table") or row.get("__source_table")
            }
        ),
        "seen_dimension_codes": sorted(
            {
                str(row.get("dimension_code"))
                for row in raw_ctrip_profile_rows
                if row.get("dimension_code") not in (None, "")
            }
        ),
        "status": "ok" if raw_ctrip_profile_rows else "empty",
    }
    for section, rows in (
        ("ctrip_joined_rights", raw_ctrip_rights_rows),
        ("ctrip_promotion_status", raw_ctrip_status_rows),
        ("ctrip_review_overview", raw_ctrip_review_rows),
        ("ctrip_review_yesterday", raw_ctrip_yesterday_rows),
        ("ctrip_hourly_orders", raw_ctrip_hourly_order_rows),
    ):
        result["diagnostics"][section] = {
            "section": section,
            "row_count": len(rows),
            "source_tables": sorted(
                {
                    str(row.get("source_table") or row.get("__source_table"))
                    for row in rows
                    if row.get("source_table") or row.get("__source_table")
                }
            ),
            "status": "ok" if rows else "empty",
        }
    return result


__all__ = ["_scan_order_summary", "normalize_dataset"]
