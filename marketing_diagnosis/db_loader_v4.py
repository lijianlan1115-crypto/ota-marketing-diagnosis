from __future__ import annotations

from datetime import date
from typing import Any

from marketing_diagnosis import db_loader_v3 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
}


def _previous_year_date(value: str | None) -> str | None:
    """Return the same calendar day in the previous year.

    February 29 falls back to February 28 when the previous year is not a leap
    year. Empty or invalid values are returned as ``None``.
    """
    text = str(value or "")[:10]
    if not text:
        return None
    try:
        current = date.fromisoformat(text)
    except ValueError:
        return None
    try:
        return current.replace(year=current.year - 1).isoformat()
    except ValueError:
        return current.replace(year=current.year - 1, day=28).isoformat()


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

    jl02_table = table_map["jl02"]
    history_start = _previous_year_date(period_start or period_end)

    # JL02 stores current and previous-year values in the same table. Query the
    # requested period plus the matching prior-year period so the diagnosis can
    # compare rows by business_date rather than by collection snapshot time.
    with previous.previous.base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            rows, diag = previous.previous.base._profiled_fetch(
                cursor,
                jl02_table,
                max(limit, 100000),
                hotel_id=hotel_id,
                date_column="business_date",
                period_start=history_start,
                period_end=period_end,
                order_candidates=(
                    "business_date ASC",
                    "metric_name ASC",
                    "snapshot_time ASC",
                ),
            )

    dataset["hotel_performance_daily"] = previous.previous.base._tag_rows(
        rows,
        jl02_table,
    )

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["jl02_business_date_yoy"] = {
            **diag,
            "rows_used": len(rows),
            "history_start": history_start,
            "period_end": period_end,
            "aggregation_rule": (
                "JL02按business_date读取本期与去年同期；"
                "去年同期为当前业务日期的上一年同月同日"
            ),
        }
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "hotel_performance_daily",
                "rows": len(rows),
                "rule": (
                    "jl02 current-period and prior-year rows loaded from the "
                    "same table for exact business_date YOY matching"
                ),
            }
        )

    return dataset


def load_database_dataset(config_path):
    config = previous.previous.base._load_json(config_path)
    kind = str(config.get("kind") or config.get("type") or "sqlite").lower()
    if kind not in {"mysql", "mysql+pymysql"}:
        return previous.load_database_dataset(config_path)

    dsn = config.get("dsn") or __import__("os").environ.get(str(config.get("dsn_env") or ""))
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
    "_previous_year_date",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
