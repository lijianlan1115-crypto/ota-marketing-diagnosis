from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v5 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
}


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _promotion_spend_summary(
    cursor,
    table: str,
    hotel_id: str | None,
    period_start: str | None,
    period_end: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Aggregate Promotion Express expense directly from the live table.

    The source stores expenses as negative values. The report must show a
    positive investment amount, so SQL sums ABS(amount) only for rows whose
    transaction_type is exactly ``推广通支出`` within the diagnosis period.
    """
    columns, schema_error = base._table_columns(cursor, table)
    if schema_error:
        return None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": schema_error,
            "stage": "SHOW COLUMNS",
        }

    amount_column = next(
        (name for name in ("transaction_amount", "amount") if name in columns),
        None,
    )
    if "transaction_type" not in columns or amount_column is None:
        return None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "required transaction_type/amount column missing",
            "table_columns": sorted(columns),
        }

    date_column = next(
        (
            name
            for name in (
                "transaction_time",
                "business_date",
                "transaction_date",
                "created_at",
                "snapshot_time",
            )
            if name in columns
        ),
        None,
    )

    filters: list[str] = [f"{base._safe_identifier('transaction_type')} = %s"]
    params: list[Any] = ["推广通支出"]

    if hotel_id and "hotel_id" in columns:
        filters.append(f"{base._safe_identifier('hotel_id')} = %s")
        params.append(hotel_id)

    if date_column:
        date_filter = base._date_range(date_column, period_start, period_end, params)
        if date_filter:
            filters.append(date_filter)

    where = base._where(filters)
    amount_identifier = base._safe_identifier(amount_column)
    sql = (
        "SELECT "
        f"COALESCE(SUM(ABS(CAST({amount_identifier} AS DECIMAL(20,4)))), 0) "
        "AS promotion_spend, COUNT(*) AS transaction_count "
        f"FROM {base._safe_identifier(table)}"
    )
    if where:
        sql += f" WHERE {where}"

    try:
        cursor.execute(sql, params)
        row = dict(cursor.fetchone() or {})
        spend = float(row.get("promotion_spend") or 0)
        count = int(row.get("transaction_count") or 0)
        summary = {
            "transaction_type": "推广通支出",
            "transaction_amount": spend,
            "promotion_spend_summary": True,
            "transaction_count": count,
            "period_start": period_start,
            "period_end": period_end,
            "date_column": date_column,
            "source_table": table,
        }
        return summary, {
            "table": table,
            "where": where,
            "rows": count,
            "status": "ok",
            "aggregation": f"SUM(ABS({amount_column}))",
            "amount_column": amount_column,
            "date_column": date_column,
            "hotel_filter_applied": "hotel_id" in columns,
            "table_columns": sorted(columns),
        }
    except Exception as exc:
        return None, {
            "table": table,
            "where": where,
            "rows": 0,
            "status": "error",
            "aggregation": f"SUM(ABS({amount_column}))",
            "amount_column": amount_column,
            "date_column": date_column,
            "error": str(exc),
            "table_columns": sorted(columns),
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

    table = table_map["meituan_promotion_finance"]
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            summary, diag = _promotion_spend_summary(
                cursor,
                table,
                hotel_id,
                period_start,
                period_end,
            )

    # On a successful query, replace raw detail rows with one authoritative
    # database-side aggregate so later transformations cannot lose or double-count
    # the spend. On query failure, keep the earlier loader result for diagnostics.
    if summary is not None:
        dataset["promotion_finance"] = [summary]

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["meituan_promotion_spend_v6"] = {
            **diag,
            "summary_applied": summary is not None,
        }
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "promotion_finance",
                "rows": 1 if summary is not None else len(dataset.get("promotion_finance") or []),
                "rule": (
                    "database-side SUM(ABS(amount)) for transaction_type=推广通支出 "
                    "within diagnosis period"
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
    "_promotion_spend_summary",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
