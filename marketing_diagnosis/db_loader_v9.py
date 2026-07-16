from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v8 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
    "jl11": "jl11_room_type_classification",
}


def _latest_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one newest ``section=summary`` row for each room type."""

    selected: dict[str, tuple[tuple[str, str, str, int, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        if str(row.get("section") or "").strip().lower() != "summary":
            continue
        room_name = str(row.get("room_type_name") or "").strip()
        if not room_name:
            continue
        try:
            row_id = int(row.get("id") or 0)
        except (TypeError, ValueError):
            row_id = 0
        order_key = (
            str(row.get("snapshot_time") or ""),
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            row_id,
            index,
        )
        current = selected.get(room_name)
        if current is None or order_key >= current[0]:
            item = dict(row)
            item["period_type"] = "近30天"
            selected[room_name] = (order_key, item)

    return [selected[name][1] for name in sorted(selected)]


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
    """Load all established sources and replace item-02 data with JL11 summaries."""

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

    jl11_table = table_map["jl11"]
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            rows, diag = base._profiled_fetch(
                cursor,
                jl11_table,
                max(limit, 50000),
                hotel_id=hotel_id,
                extra_filters=[("section", "=", "summary")],
                order_candidates=(
                    "room_type_name ASC",
                    "snapshot_time ASC",
                    "updated_at ASC",
                    "id ASC",
                ),
            )

    summary_rows = _latest_summary_rows(rows)
    dataset["room_type_performance_daily"] = base._tag_rows(summary_rows, jl11_table)

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["jl11_room_type_summary"] = {
            **diag,
            "rows_used": len(summary_rows),
            "section_filter": "summary",
            "aggregation_rule": (
                "只取 section=summary；按 room_type_name 保留最新记录；"
                "直接使用近30天汇总字段"
            ),
        }
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "room_type_performance_daily",
                "rows": len(summary_rows),
                "rule": (
                    "item 02 uses jl11 room_count, room_nights, occupancy_rate, "
                    "room_revenue, average_room_price and revpar"
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
    "_latest_summary_rows",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
