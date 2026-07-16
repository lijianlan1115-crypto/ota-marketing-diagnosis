from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v12 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
}

_ORDER_COLUMNS = (
    "snapshot_time",
    "updated_at",
    "created_at",
    "business_date",
    "id",
)


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _latest_configuration_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the newest live row for every configuration/promotion name.

    Configuration rows may be updated independently.  Selecting one global
    ``snapshot_time`` can therefore drop otherwise valid rows.  This helper
    keeps the latest row per ``promotion_name`` so each report generation shows
    the current state of every configuration item.
    """

    selected: dict[str, tuple[tuple[str, str, str, str, int, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        name = str(
            row.get("promotion_name")
            or row.get("config_name")
            or row.get("feature_name")
            or ""
        ).strip()
        if not name:
            continue
        try:
            row_id = int(row.get("id") or 0)
        except (TypeError, ValueError):
            row_id = 0
        order_key = (
            str(row.get("snapshot_time") or ""),
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            str(row.get("business_date") or ""),
            row_id,
            index,
        )
        current = selected.get(name)
        if current is None or order_key >= current[0]:
            selected[name] = (order_key, dict(row))

    return [selected[name][1] for name in sorted(selected)]


def _load_current_configuration_status(
    cursor,
    table: str,
    limit: int,
    hotel_id: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    columns, schema_error = base._table_columns(cursor, table)
    if schema_error:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "stage": "SHOW COLUMNS",
            "error": schema_error,
        }

    name_column = next(
        (
            name
            for name in ("promotion_name", "config_name", "feature_name")
            if name in columns
        ),
        None,
    )
    if not name_column:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "configuration name column not found",
            "table_columns": sorted(columns),
        }

    order_candidates = tuple(
        f"{name} DESC" for name in _ORDER_COLUMNS if name in columns
    )
    rows, diag = base._profiled_fetch(
        cursor,
        table,
        max(limit, 5000),
        hotel_id=hotel_id,
        order_candidates=order_candidates,
    )
    latest = _latest_configuration_rows(rows)
    return latest, {
        **diag,
        "rows_read": len(rows),
        "rows_used": len(latest),
        "name_column": name_column,
        "selection_rule": (
            "query the live table on every report generation and keep the newest "
            "row independently for each configuration name"
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
    dataset = previous.load_mysql_dsn_dataset(
        dsn,
        limit=limit,
        tables=tables,
        hotel_id=hotel_id,
        platform=platform,
        period_start=period_start,
        period_end=period_end,
    )

    if "meituan" not in base._enabled_platforms(platform):
        return dataset

    table_map = {**DEFAULT_MYSQL_TABLES, **(tables or {})}
    table = table_map["meituan_promotion_status"]
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            latest, diag = _load_current_configuration_status(
                cursor,
                table,
                limit,
                hotel_id,
            )

    # Replace the earlier snapshot with this fresh per-item selection.  Empty
    # and error results stay visible to the upper rule layer instead of reusing
    # stale rows from a previous query.
    dataset["promotion_status"] = base._tag_rows(latest, table)

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})[
            "meituan_promotion_status_live"
        ] = diag
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "promotion_status",
                "rows": len(latest),
                "rule": (
                    "live query per report; latest row per promotion_name/config_name/feature_name"
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
    "_latest_configuration_rows",
    "_load_current_configuration_status",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
