from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v10 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
    "meituan_promotion_performance_30d": "meituan_ota_promotion_performance_30d",
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


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _load_latest_promotion_performance(
    cursor,
    table: str,
    limit: int,
    hotel_id: str | None,
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

    required = {"promotion_status", "spend_amount", "booking_order_amount"}
    missing = sorted(required - columns)
    if missing:
        return None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": f"required columns missing: {', '.join(missing)}",
            "table_columns": sorted(columns),
        }

    order_candidates = tuple(
        f"{name} DESC"
        for name in (*_DATE_COLUMNS, "id")
        if name in columns
    )
    rows, diag = base._profiled_fetch(
        cursor,
        table,
        max(20, min(limit, 1000)),
        hotel_id=hotel_id,
        extra_filters=[("promotion_status", "=", "RUNNING")],
        order_candidates=order_candidates,
    )
    if not rows:
        return None, {
            **diag,
            "required_columns": sorted(required),
            "rows_used": 0,
            "status_filter": "promotion_status=RUNNING",
        }

    source = rows[0]
    mapped = {
        "platform": "meituan",
        "source_table": table,
        "promotion_status": source.get("promotion_status"),
        "spend_amount": base._float(source.get("spend_amount")),
        "booking_order_amount": base._float(source.get("booking_order_amount")),
        "business_date": next(
            (
                str(source.get(name) or "")[:10]
                for name in _DATE_COLUMNS
                if source.get(name) not in (None, "")
            ),
            None,
        ),
        "snapshot_time": source.get("snapshot_time")
        or source.get("updated_at")
        or source.get("created_at"),
    }
    return mapped, {
        **diag,
        "required_columns": sorted(required),
        "rows_used": 1,
        "status_filter": "promotion_status=RUNNING",
        "selected_promotion_status": mapped.get("promotion_status"),
        "aggregation_rule": (
            "filter promotion_status=RUNNING first, then use the latest row from "
            "meituan_ota_promotion_performance_30d; spend_amount and "
            "booking_order_amount map directly"
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

    table = table_map["meituan_promotion_performance_30d"]
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            summary, diag = _load_latest_promotion_performance(
                cursor,
                table,
                limit,
                hotel_id,
            )

    finance_rows = [
        row
        for row in list(dataset.get("promotion_finance") or [])
        if "promotion_performance_30d"
        not in str(row.get("source_table") or row.get("__source_table") or "")
    ]
    if summary is not None:
        finance_rows.append(summary)
    dataset["promotion_finance"] = finance_rows

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})[
            "meituan_promotion_performance_30d"
        ] = diag
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "promotion_finance",
                "rows": 1 if summary is not None else 0,
                "rule": (
                    "item 09 uses hotel_puyue.meituan_ota_promotion_performance_30d; "
                    "only promotion_status=RUNNING rows are eligible; spend_amount "
                    "and booking_order_amount map directly"
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
    "_load_latest_promotion_performance",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
