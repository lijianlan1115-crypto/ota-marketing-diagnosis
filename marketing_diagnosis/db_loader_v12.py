from __future__ import annotations

from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v11 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
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

_EXACT_RANK_FIELDS = {
    "exposure_peer_rank": "exposure",
    "browse_peer_rank": "views",
    "pay_order_peer_rank": "paid_orders",
    "exposure_to_browse_peer_rank": "exposure_to_view_rate",
    "browse_to_pay_peer_rank": "payment_conversion_rate",
}


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _apply_exact_rank_fields(
    mapped_row: dict[str, Any],
    source_row: dict[str, Any],
) -> dict[str, Any]:
    """Copy the five confirmed peer-rank columns into item-04 canonical keys."""

    for source_key, target in _EXACT_RANK_FIELDS.items():
        raw_value = source_row.get(source_key)
        if raw_value in (None, ""):
            continue
        raw_text = str(raw_value).strip()
        mapped_row[f"{target}_rank_raw"] = raw_text
        parsed = base._rank(raw_text)
        if parsed is not None:
            mapped_row[f"{target}_rank"] = parsed
    return mapped_row


def _load_latest_exact_rank_row(
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

    missing = sorted(set(_EXACT_RANK_FIELDS) - columns)
    date_column = next((name for name in _DATE_COLUMNS if name in columns), None)
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
        date_column=date_column,
        period_start=period_start if date_column else None,
        period_end=period_end if date_column else None,
        order_candidates=order_candidates,
    )
    return (rows[0] if rows else None), {
        **diag,
        "date_column": date_column,
        "exact_rank_fields": sorted(_EXACT_RANK_FIELDS),
        "missing_exact_rank_fields": missing,
        "rows_used": 1 if rows else 0,
    }


def _flow_summary_row(dataset: dict[str, Any], table: str) -> dict[str, Any] | None:
    rows = [
        row
        for row in list(dataset.get("ota_funnel") or [])
        if str(row.get("source_table") or row.get("__source_table") or "")
        .strip()
        .endswith(table)
    ]
    if not rows:
        return None
    return max(
        enumerate(rows),
        key=lambda pair: (
            str(pair[1].get("business_date") or ""),
            str(pair[1].get("snapshot_time") or ""),
            pair[0],
        ),
    )[1]


def load_mysql_dsn_dataset(
    dsn: str,
    limit: int = 5000,
    tables: dict[str, str] | None = None,
    hotel_id: str | None = "puyue",
    platform: str | None = "multi",
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Load all existing modules and enforce the five exact item-04 rank fields."""

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
            raw_row, diag = _load_latest_exact_rank_row(
                cursor,
                table,
                limit,
                hotel_id,
                period_start,
                period_end,
            )

    mapped_row = _flow_summary_row(dataset, table)
    if raw_row is not None and mapped_row is not None:
        _apply_exact_rank_fields(mapped_row, raw_row)

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})[
            "meituan_flow_conversion_30d_exact_ranks"
        ] = diag
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "ota_funnel",
                "rows": 1 if raw_row is not None and mapped_row is not None else 0,
                "rule": (
                    "item 04 exact rank mapping: exposure_peer_rank, browse_peer_rank, "
                    "pay_order_peer_rank, exposure_to_browse_peer_rank and "
                    "browse_to_pay_peer_rank"
                ),
            }
        )

    return dataset


def load_database_dataset(config_path):
    config = base._load_json(config_path)
    kind = str(config.get("kind") or config.get("type") or "sqlite").lower()
    if kind not in {"mysql", "mysql+pymysql"}:
        return previous.load_database_dataset(config_path)

    import os

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
    "_EXACT_RANK_FIELDS",
    "_apply_exact_rank_fields",
    "_load_latest_exact_rank_row",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
