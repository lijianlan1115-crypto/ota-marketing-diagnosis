from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v6 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
}


def _normalized_transaction_type(value: Any) -> str:
    """Normalize invisible/extra whitespace without changing Chinese content."""
    return "".join(str(value or "").split())


def _detail_fallback_spend(rows: list[dict[str, Any]], amount_column: str) -> tuple[float, int]:
    values: list[float] = []
    for row in rows:
        if _normalized_transaction_type(row.get("transaction_type")) != "推广通支出":
            continue
        value = base._float(row.get(amount_column))
        if value is None:
            continue
        values.append(abs(float(value)))
    return sum(values), len(values)


def _promotion_spend_summary_resilient(
    cursor,
    table: str,
    hotel_id: str | None,
    period_start: str | None,
    period_end: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Aggregate promotion spend while tolerating whitespace in transaction_type.

    First use a database-side SUM with TRIM. If it returns no matching rows, fetch
    the already date/hotel-filtered details and apply the same whitespace-cleaning
    behavior that produced the previously verified ¥500 result.
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

    common_filters: list[str] = []
    common_params: list[Any] = []
    if hotel_id and "hotel_id" in columns:
        common_filters.append(f"{base._safe_identifier('hotel_id')} = %s")
        common_params.append(hotel_id)
    if date_column:
        date_filter = base._date_range(
            date_column,
            period_start,
            period_end,
            common_params,
        )
        if date_filter:
            common_filters.append(date_filter)

    amount_identifier = base._safe_identifier(amount_column)
    type_identifier = base._safe_identifier("transaction_type")
    aggregate_filters = [f"TRIM({type_identifier}) = %s", *common_filters]
    aggregate_params = ["推广通支出", *common_params]
    aggregate_where = base._where(aggregate_filters)
    aggregate_sql = (
        "SELECT "
        f"COALESCE(SUM(ABS(CAST({amount_identifier} AS DECIMAL(20,4)))), 0) AS promotion_spend, "
        "COUNT(*) AS transaction_count "
        f"FROM {base._safe_identifier(table)} WHERE {aggregate_where}"
    )

    try:
        cursor.execute(aggregate_sql, aggregate_params)
        aggregate = dict(cursor.fetchone() or {})
        spend = float(aggregate.get("promotion_spend") or 0)
        count = int(aggregate.get("transaction_count") or 0)
        mode = "sql_trim"

        if count == 0:
            detail_where = base._where(common_filters)
            detail_sql = (
                f"SELECT {type_identifier} AS transaction_type, "
                f"{amount_identifier} AS amount_value "
                f"FROM {base._safe_identifier(table)}"
            )
            if detail_where:
                detail_sql += f" WHERE {detail_where}"
            cursor.execute(detail_sql, common_params)
            detail_rows = [dict(row) for row in cursor.fetchall()]
            normalized_rows = [
                {
                    "transaction_type": row.get("transaction_type"),
                    amount_column: row.get("amount_value"),
                }
                for row in detail_rows
            ]
            spend, count = _detail_fallback_spend(normalized_rows, amount_column)
            mode = "python_whitespace_fallback"

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
            "rows": count,
            "status": "ok",
            "aggregation": f"SUM(ABS({amount_column}))",
            "match_mode": mode,
            "amount_column": amount_column,
            "date_column": date_column,
            "hotel_filter_applied": "hotel_id" in columns,
            "table_columns": sorted(columns),
        }
    except Exception as exc:
        return None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": str(exc),
            "amount_column": amount_column,
            "date_column": date_column,
            "table_columns": sorted(columns),
        }


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


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
            summary, diag = _promotion_spend_summary_resilient(
                cursor,
                table,
                hotel_id,
                period_start,
                period_end,
            )

    if summary is not None:
        dataset["promotion_finance"] = [summary]

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["meituan_promotion_spend_v7"] = {
            **diag,
            "summary_applied": summary is not None,
        }
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "promotion_finance",
                "rows": 1 if summary is not None else len(dataset.get("promotion_finance") or []),
                "rule": "trimmed SQL match with verified detail fallback for 推广通支出",
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
    "_detail_fallback_spend",
    "_normalized_transaction_type",
    "_promotion_spend_summary_resilient",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
