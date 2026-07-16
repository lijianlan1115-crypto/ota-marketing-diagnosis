from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v9_legacy as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
    "meituan_flow_conversion_30d": "meituan_ota_flow_conversion_30d",
}

_DATE_COLUMNS = (
    "business_date",
    "data_date",
    "stats_date",
    "stat_date",
    "snapshot_date",
    "snapshot_time",
    "updated_at",
    "created_at",
)

_FLOW_KEYS = {
    "exposure",
    "peer_exposure",
    "views",
    "peer_views",
    "paid_orders",
    "peer_paid_orders",
    "exposure_to_view_rate",
    "peer_exposure_to_view_rate",
    "payment_conversion_rate",
    "peer_payment_conversion_rate",
    "peer_avg_conversion_rate",
}

_FLOW_TARGETS = (
    "exposure",
    "views",
    "paid_orders",
    "exposure_to_view_rate",
    "payment_conversion_rate",
)

_META_KEYS = {
    "platform",
    "business_date",
    "period_type",
    "stats_period_type",
    "period_days",
    "source_table",
    "__source_table",
    "snapshot_time",
    "updated_at",
    "created_at",
}


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _percent_ratio(value: Any) -> float | None:
    """Convert a database percentage value such as 10.44 into 0.1044."""

    number = base._float(value)
    return None if number is None else number / 100


def _display_number(value: Any) -> str:
    number = base._float(value)
    if number is None:
        return str(value or "")
    return str(int(number)) if float(number).is_integer() else str(number)


def _rank_value(row: dict[str, Any], *prefixes: str) -> Any:
    direct_keys: list[str] = []
    position_keys: list[str] = []
    for prefix in prefixes:
        direct_keys.extend(
            [
                f"{prefix}_rank",
                f"{prefix}_peer_rank",
                f"{prefix}_competitor_rank",
                f"{prefix}_ranking",
                f"{prefix}_rank_text",
            ]
        )
        position_keys.extend(
            [
                f"{prefix}_rank_position",
                f"{prefix}_ranking_position",
                f"{prefix}_rank_no",
            ]
        )

    direct = _first(row, *direct_keys)
    if direct not in (None, ""):
        return direct

    position = _first(row, *position_keys)
    if position in (None, ""):
        return None

    total = _first(
        row,
        "peer_hotel_count",
        "peer_count",
        "competitor_count",
        "competitor_hotel_count",
        "rank_total",
        "ranking_total",
        "hotel_count",
    )
    if total in (None, ""):
        return position
    return f"{_display_number(position)}/{_display_number(total)}"


def _attach_rank(item: dict[str, Any], target: str, raw_value: Any) -> None:
    if raw_value in (None, ""):
        return
    raw_text = str(raw_value).strip()
    item[f"{target}_rank_raw"] = raw_text
    rank = base._rank(raw_text)
    if rank is not None:
        item[f"{target}_rank"] = rank


def _source_date(row: dict[str, Any], fallback: str | None = None) -> str | None:
    value = _first(row, *_DATE_COLUMNS)
    text = str(value or fallback or "").strip()
    return text[:10] or None


def _map_flow_conversion_row(
    row: dict[str, Any],
    source_table: str,
    fallback_date: str | None = None,
) -> dict[str, Any]:
    """Map one 30-day summary row into the established OTA funnel schema."""

    item: dict[str, Any] = {
        "platform": "meituan",
        "business_date": _source_date(row, fallback_date),
        # Existing flow selectors use the daily marker. The values themselves are
        # already a single 30-day summary row and are not re-queried from daily data.
        "period_type": "日",
        "stats_period_type": "日",
        "period_days": 30,
        "source_table": source_table,
        "snapshot_time": _first(row, "snapshot_time", "updated_at", "created_at"),
        "exposure": base._float(row.get("exposure_uv")),
        "peer_exposure": base._float(row.get("peer_exposure_uv")),
        "views": base._float(row.get("browse_uv")),
        "peer_views": base._float(row.get("peer_browse_uv")),
        "exposure_to_view_rate": _percent_ratio(
            row.get("exposure_to_browse_rate_pct")
        ),
        "peer_exposure_to_view_rate": _percent_ratio(
            row.get("peer_exposure_to_browse_rate_pct")
        ),
        "paid_orders": base._float(row.get("pay_order_count")),
        "peer_paid_orders": base._float(row.get("peer_pay_order_count")),
        "payment_conversion_rate": _percent_ratio(
            row.get("browse_to_pay_rate_pct")
        ),
        "peer_payment_conversion_rate": _percent_ratio(
            row.get("peer_browse_to_pay_rate_pct")
        ),
        "peer_avg_conversion_rate": _percent_ratio(
            row.get("peer_browse_to_pay_rate_pct")
        ),
        "exposure_metric_code": "FLOW_EXPOSURE_UV",
        "views_metric_code": "FLOW_INTENTION_UV",
        "paid_orders_metric_code": "FLOW_PAY_ORDER_CNT",
        "exposure_to_view_rate_metric_code": "FLOW_INTENTION_PER_EXPOSURE",
        "payment_conversion_rate_metric_code": "FLOW_PAY_ORDER_PER_INTENTION",
    }

    _attach_rank(item, "exposure", _rank_value(row, "exposure_uv", "exposure"))
    _attach_rank(item, "views", _rank_value(row, "browse_uv", "browse"))
    _attach_rank(
        item,
        "exposure_to_view_rate",
        _rank_value(
            row,
            "exposure_to_browse_rate_pct",
            "exposure_to_browse_rate",
            "exposure_browse",
        ),
    )
    _attach_rank(
        item,
        "paid_orders",
        _rank_value(row, "pay_order_count", "pay_order", "paid_order"),
    )
    _attach_rank(
        item,
        "payment_conversion_rate",
        _rank_value(
            row,
            "browse_to_pay_rate_pct",
            "browse_to_pay_rate",
            "browse_pay",
        ),
    )
    return item


def _strip_existing_meituan_flow(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove only the old Meituan flow metrics while preserving other modules."""

    cleaned: list[dict[str, Any]] = []
    for row in rows:
        platform = str(row.get("platform") or "").strip().lower()
        if platform not in {"meituan", "美团", "美团酒店"}:
            cleaned.append(row)
            continue

        item = dict(row)
        for key in _FLOW_KEYS:
            item.pop(key, None)
        for target in _FLOW_TARGETS:
            for suffix in (
                "_rank",
                "_rank_raw",
                "_metric_code",
                "_metric_name",
            ):
                item.pop(f"{target}{suffix}", None)

        meaningful = any(
            value not in (None, "") and key not in _META_KEYS
            for key, value in item.items()
        )
        if meaningful:
            cleaned.append(item)
    return cleaned


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _load_latest_flow_conversion(
    cursor,
    table: str,
    limit: int,
    hotel_id: str | None,
    period_start: str | None,
    period_end: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    columns, schema_error = base._table_columns(cursor, table)
    if schema_error:
        return None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "stage": "SHOW COLUMNS",
            "error": schema_error,
        }

    required = {
        "exposure_uv",
        "peer_exposure_uv",
        "browse_uv",
        "peer_browse_uv",
        "exposure_to_browse_rate_pct",
        "peer_exposure_to_browse_rate_pct",
        "pay_order_count",
        "peer_pay_order_count",
        "browse_to_pay_rate_pct",
        "peer_browse_to_pay_rate_pct",
    }
    missing = sorted(required - columns)
    if missing:
        return None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": f"required columns missing: {', '.join(missing)}",
            "table_columns": sorted(columns),
        }

    date_column = next((name for name in _DATE_COLUMNS if name in columns), None)
    order_candidates = tuple(
        f"{name} DESC"
        for name in (*_DATE_COLUMNS, "id")
        if name in columns
    )
    rows, diag = base._profiled_fetch(
        cursor,
        table,
        max(50, min(limit, 5000)),
        hotel_id=hotel_id,
        date_column=date_column,
        period_start=period_start if date_column else None,
        period_end=period_end if date_column else None,
        order_candidates=order_candidates,
    )
    if not rows:
        return None, {
            **diag,
            "required_columns": sorted(required),
            "date_column": date_column,
            "rows_used": 0,
        }

    mapped = _map_flow_conversion_row(rows[0], table, period_end)
    return mapped, {
        **diag,
        "required_columns": sorted(required),
        "date_column": date_column,
        "rows_used": 1,
        "selected_business_date": mapped.get("business_date"),
        "aggregation_rule": (
            "use the latest row from meituan_ota_flow_conversion_30d; "
            "count fields map directly and *_rate_pct fields are divided by 100"
        ),
    }


def load_mysql_dsn_dataset(
    dsn: str,
    limit: int = 5000,
    tables: dict[str, str] | None = None,
    hotel_id: str | None = "puyue",
    platform: str | None = "multi",
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    table_map = {**DEFAULT_MYSQL_TABLES, **(tables or {})}
    dataset = previous.load_mysql_dsn_dataset(
        dsn,
        limit=limit,
        tables=table_map,
        hotel_id=hotel_id,
        platform=platform,
        period_start=period_start,
        period_end=period_end,
    )

    if "meituan" not in base._enabled_platforms(platform):
        return dataset

    table = table_map["meituan_flow_conversion_30d"]
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            summary, diag = _load_latest_flow_conversion(
                cursor,
                table,
                limit,
                hotel_id,
                period_start,
                period_end,
            )

    funnel_rows = _strip_existing_meituan_flow(
        list(dataset.get("ota_funnel") or [])
    )
    if summary is not None:
        funnel_rows.append(summary)
    dataset["ota_funnel"] = funnel_rows

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})[
            "meituan_flow_conversion_30d"
        ] = diag
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "ota_funnel",
                "rows": 1 if summary is not None else 0,
                "rule": (
                    "item 04 uses hotel_puyue.meituan_ota_flow_conversion_30d; "
                    "exposure_uv/browse_uv/pay_order_count map directly and "
                    "percentage columns are converted from percent units to ratios"
                ),
            }
        )

    return dataset


def load_database_dataset(config_path):
    config = base._load_json(config_path)
    kind = str(config.get("kind") or config.get("type") or "sqlite").lower()
    if kind not in {"mysql", "mysql+pymysql"}:
        return previous.load_database_dataset(config_path)

    dsn = config.get("dsn") or os.environ.get(str(config.get("dsn_env") or ""))
    if not dsn:
        raise ValueError("MySQL config requires dsn or dsn_env")
    return load_mysql_dsn_dataset(
        dsn,
        limit=int(config.get("limit") or 5000),
        tables=config.get("tables") or {},
        hotel_id=config.get("hotel_id") or "puyue",
        platform=config.get("platform") or "multi",
        period_start=config.get("period_start"),
        period_end=config.get("period_end"),
    )


__all__ = [
    "DEFAULT_MYSQL_TABLES",
    "_load_latest_flow_conversion",
    "_map_flow_conversion_row",
    "_percent_ratio",
    "_strip_existing_meituan_flow",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
