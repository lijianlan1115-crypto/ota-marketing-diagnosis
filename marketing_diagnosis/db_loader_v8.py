from __future__ import annotations

import os
import unicodedata
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v5 as source_loader


DEFAULT_MYSQL_TABLES = {
    **source_loader.DEFAULT_MYSQL_TABLES,
}


def _normalized_transaction_type(value: Any) -> str:
    """Normalize compatibility ideographs, invisible characters and whitespace.

    Excel/database text can visually show ``推广通支出`` while actually containing
    Kangxi/compatibility characters such as ``推⼴通⽀出``. NFKC converts those
    characters to their normal Chinese equivalents before matching.
    """
    text = unicodedata.normalize("NFKC", str(value or ""))
    return "".join(
        char
        for char in text
        if not char.isspace() and unicodedata.category(char) != "Cf"
    )


def _date_text(value: Any) -> str:
    return str(value or "").strip()[:10]


def _in_period(value: Any, period_start: str | None, period_end: str | None) -> bool:
    day = _date_text(value)
    if not day:
        return not period_start and not period_end
    if period_start and day < period_start:
        return False
    if period_end and day > period_end:
        return False
    return True


def _detail_spend(
    rows: list[dict[str, Any]],
    amount_column: str,
    date_column: str | None,
    period_start: str | None,
    period_end: str | None,
) -> tuple[float, int]:
    values: list[float] = []
    for row in rows:
        if date_column and not _in_period(row.get(date_column), period_start, period_end):
            continue
        if _normalized_transaction_type(row.get("transaction_type")) != "推广通支出":
            continue
        value = base._float(row.get(amount_column))
        if value is None:
            continue
        values.append(abs(float(value)))
    return sum(values), len(values)


def _query_details(
    cursor,
    table: str,
    columns: set[str],
    amount_column: str,
    date_column: str | None,
    hotel_id: str | None,
    period_start: str | None,
    period_end: str | None,
    *,
    apply_hotel_filter: bool,
) -> tuple[list[dict[str, Any]], str | None, list[Any]]:
    filters: list[str] = []
    params: list[Any] = []

    if apply_hotel_filter and hotel_id and "hotel_id" in columns:
        filters.append(f"{base._safe_identifier('hotel_id')} = %s")
        params.append(hotel_id)

    if date_column:
        date_identifier = base._safe_identifier(date_column)
        # transaction_time may be DATETIME or a text range such as
        # ``2026-07-08 00:00:00-23:59:59``. LEFT(CAST(...), 10) handles both.
        date_expression = f"LEFT(CAST({date_identifier} AS CHAR), 10)"
        if period_start:
            filters.append(f"{date_expression} >= %s")
            params.append(period_start)
        if period_end:
            filters.append(f"{date_expression} <= %s")
            params.append(period_end)

    selected = [
        f"{base._safe_identifier('transaction_type')} AS transaction_type",
        f"{base._safe_identifier(amount_column)} AS amount_value",
    ]
    if date_column:
        selected.append(f"{base._safe_identifier(date_column)} AS transaction_date_value")
    if "hotel_id" in columns:
        selected.append(f"{base._safe_identifier('hotel_id')} AS source_hotel_id")

    where = base._where(filters)
    sql = f"SELECT {', '.join(selected)} FROM {base._safe_identifier(table)}"
    if where:
        sql += f" WHERE {where}"

    cursor.execute(sql, params)
    rows = [dict(row) for row in cursor.fetchall()]
    normalized = []
    for row in rows:
        normalized_row = {
            "transaction_type": row.get("transaction_type"),
            amount_column: row.get("amount_value"),
        }
        if date_column:
            normalized_row[date_column] = row.get("transaction_date_value")
        if "hotel_id" in columns:
            normalized_row["hotel_id"] = row.get("source_hotel_id")
        normalized.append(normalized_row)
    return normalized, where, params


def _promotion_spend_summary_unicode(
    cursor,
    table: str,
    hotel_id: str | None,
    period_start: str | None,
    period_end: str | None,
    *,
    preloaded_rows: list[dict[str, Any]] | None = None,
    schema_is_hotel_scoped: bool = False,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
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

    attempts: list[dict[str, Any]] = []
    try:
        apply_hotel = bool(hotel_id and "hotel_id" in columns)
        rows, where, params = _query_details(
            cursor,
            table,
            columns,
            amount_column,
            date_column,
            hotel_id,
            period_start,
            period_end,
            apply_hotel_filter=apply_hotel,
        )
        spend, count = _detail_spend(
            rows,
            amount_column,
            date_column,
            period_start,
            period_end,
        )
        mode = "unicode_detail_with_hotel" if apply_hotel else "unicode_detail"
        attempts.append({"mode": mode, "rows_read": len(rows), "matches": count, "where": where})

        # hotel_puyue is already a hotel-scoped schema. Some historical finance
        # rows have a blank or non-standard hotel_id even though they belong to this
        # schema. Retry without hotel_id only when the schema itself is hotel-scoped.
        if count == 0 and apply_hotel and schema_is_hotel_scoped:
            rows, where, params = _query_details(
                cursor,
                table,
                columns,
                amount_column,
                date_column,
                hotel_id,
                period_start,
                period_end,
                apply_hotel_filter=False,
            )
            spend, count = _detail_spend(
                rows,
                amount_column,
                date_column,
                period_start,
                period_end,
            )
            mode = "unicode_detail_schema_scoped"
            attempts.append({"mode": mode, "rows_read": len(rows), "matches": count, "where": where})

        if count == 0 and preloaded_rows:
            spend, count = _detail_spend(
                list(preloaded_rows),
                amount_column,
                date_column,
                period_start,
                period_end,
            )
            mode = "unicode_preloaded_fallback"
            attempts.append(
                {
                    "mode": mode,
                    "rows_read": len(preloaded_rows),
                    "matches": count,
                    "where": "preloaded rows",
                }
            )

        if count == 0:
            # Never replace source rows with a synthetic zero when no matching
            # transaction was actually found. This prevents false ¥0.00 reports.
            return None, {
                "table": table,
                "rows": 0,
                "status": "empty",
                "match_mode": mode,
                "attempts": attempts,
                "amount_column": amount_column,
                "date_column": date_column,
                "table_columns": sorted(columns),
                "summary_applied": False,
            }

        summary = {
            "transaction_type": "推广通支出",
            "transaction_amount": spend,
            "promotion_spend_summary": True,
            "transaction_count": count,
            "period_start": period_start,
            "period_end": period_end,
            "date_column": date_column,
            "source_table": table,
            "match_mode": mode,
        }
        return summary, {
            "table": table,
            "rows": count,
            "status": "ok",
            "aggregation": f"SUM(ABS({amount_column})) after Unicode NFKC normalization",
            "match_mode": mode,
            "attempts": attempts,
            "amount_column": amount_column,
            "date_column": date_column,
            "table_columns": sorted(columns),
            "summary_applied": True,
        }
    except Exception as exc:
        return None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": str(exc),
            "attempts": attempts,
            "amount_column": amount_column,
            "date_column": date_column,
            "table_columns": sorted(columns),
            "summary_applied": False,
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
    dataset = source_loader.load_mysql_dsn_dataset(
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
    database_name = str(base._mysql_params(dsn).get("database") or "").lower()
    schema_is_hotel_scoped = database_name.startswith("hotel_")
    preloaded_rows = list(dataset.get("promotion_finance") or [])

    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            summary, diag = _promotion_spend_summary_unicode(
                cursor,
                table,
                hotel_id,
                period_start,
                period_end,
                preloaded_rows=preloaded_rows,
                schema_is_hotel_scoped=schema_is_hotel_scoped,
            )

    if summary is not None:
        dataset["promotion_finance"] = [summary]

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["meituan_promotion_spend_v8"] = diag
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "promotion_finance",
                "rows": 1 if summary is not None else len(dataset.get("promotion_finance") or []),
                "rule": (
                    "transaction_time period filter + Unicode NFKC transaction_type match + "
                    "SUM(ABS(transaction_amount))"
                ),
            }
        )

    return dataset


def load_database_dataset(config_path):
    config = base._load_json(config_path)
    kind = str(config.get("kind") or config.get("type") or "sqlite").lower()
    if kind not in {"mysql", "mysql+pymysql"}:
        return source_loader.load_database_dataset(config_path)

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
    "_detail_spend",
    "_normalized_transaction_type",
    "_promotion_spend_summary_unicode",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
