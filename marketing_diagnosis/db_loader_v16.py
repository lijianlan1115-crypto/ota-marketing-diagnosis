from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v15 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
    "ctrip_userprofile_distribution": "ctrip_ota_userprofile_distribution",
}

_ORDER_COLUMNS = (
    "snapshot_time",
    "updated_at",
    "created_at",
    "business_date",
    "data_date",
    "id",
)


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _row_key(row: dict[str, Any], index: int) -> tuple[str, str, str, int]:
    dimension = str(row.get("dimension_code") or "").strip()
    bucket = str(
        row.get("bucket_code")
        or row.get("bucket_label")
        or row.get("bucket_name")
        or row.get("dimension_label")
        or ""
    ).strip()
    hotel = str(row.get("hotel_id") or "").strip()
    return hotel, dimension, bucket, index


def _order_key(row: dict[str, Any], index: int) -> tuple[str, str, str, str, str, int, int]:
    try:
        row_id = int(row.get("id") or 0)
    except (TypeError, ValueError):
        row_id = 0
    return (
        str(row.get("snapshot_time") or ""),
        str(row.get("updated_at") or ""),
        str(row.get("created_at") or ""),
        str(row.get("business_date") or ""),
        str(row.get("data_date") or ""),
        row_id,
        index,
    )


def latest_distribution_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the newest row for every dimension/bucket pair.

    User-profile dimensions may be refreshed independently, so selecting one
    global snapshot timestamp can accidentally discard valid dimensions. This
    function keeps the latest row for each dimension_code + bucket pair.
    """

    selected: dict[tuple[str, str, str], tuple[tuple[Any, ...], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        hotel, dimension, bucket, _ = _row_key(row, index)
        key = (hotel, dimension, bucket)
        order = _order_key(row, index)
        current = selected.get(key)
        if current is None or order >= current[0]:
            selected[key] = (order, dict(row))

    output = [value[1] for value in selected.values()]
    output.sort(
        key=lambda row: (
            str(row.get("dimension_code") or ""),
            float(row.get("sort_order") or 999999),
            float(row.get("rank") or row.get("ranking_position") or 999999),
            str(row.get("bucket_label") or row.get("bucket_name") or ""),
        )
    )
    return output


def _load_user_profile(
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
    if "dimension_code" not in columns:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "required column missing: dimension_code",
            "table_columns": sorted(columns),
        }

    order_candidates = tuple(
        [f"{name} DESC" for name in _ORDER_COLUMNS if name in columns]
        + [
            value
            for value in ("dimension_code ASC", "sort_order ASC", "rank ASC", "bucket_label ASC")
            if value.rsplit(" ", 1)[0] in columns
        ]
    )
    rows, diag = base._profiled_fetch(
        cursor,
        table,
        max(limit, 10000),
        hotel_id=hotel_id,
        order_candidates=order_candidates,
    )
    latest = latest_distribution_rows(rows)
    return latest, {
        **diag,
        "rows_read": len(rows),
        "rows_used": len(latest),
        "selection_rule": "latest row per hotel_id + dimension_code + bucket",
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

    if "ctrip" not in base._enabled_platforms(platform):
        dataset.setdefault("ctrip_userprofile_distribution", [])
        return dataset

    table = table_map["ctrip_userprofile_distribution"]
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            rows, diag = _load_user_profile(cursor, table, limit, hotel_id)

    dataset["ctrip_userprofile_distribution"] = base._tag_rows(rows, table)
    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["ctrip_userprofile_distribution"] = diag
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "ctrip_userprofile_distribution",
                "rows": len(rows),
                "rule": (
                    "read ctrip_ota_userprofile_distribution on every report generation; "
                    "keep latest row per dimension_code and bucket"
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
    "latest_distribution_rows",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
