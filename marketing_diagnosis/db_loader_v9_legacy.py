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


def _yesterday_review_count(
    cursor,
    table: str,
    hotel_id: str | None = None,
) -> tuple[int | None, str | None, dict[str, Any]]:
    """Count rows whose datetime ``review_time`` falls on MySQL server yesterday."""

    columns, schema_error = base._table_columns(cursor, table)
    if schema_error:
        return None, None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "stage": "SHOW COLUMNS",
            "error": schema_error,
        }
    if "review_time" not in columns:
        return None, None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "review_time column not found",
            "table_columns": sorted(columns),
        }

    filters = [
        f"DATE({base._safe_identifier('review_time')}) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)"
    ]
    params: list[Any] = []
    if hotel_id and "hotel_id" in columns:
        filters.append(f"{base._safe_identifier('hotel_id')} = %s")
        params.append(hotel_id)

    sql = (
        "SELECT DATE_SUB(CURDATE(), INTERVAL 1 DAY) AS target_date, "
        "COUNT(*) AS review_count "
        f"FROM {base._safe_identifier(table)} WHERE {' AND '.join(filters)}"
    )
    try:
        cursor.execute(sql, params)
        row = dict(cursor.fetchone() or {})
        count = int(row.get("review_count") or 0)
        target_date = str(row.get("target_date") or "")[:10] or None
        return count, target_date, {
            "table": table,
            "rows": count,
            "status": "ok",
            "where": "DATE(review_time)=DATE_SUB(CURDATE(), INTERVAL 1 DAY)",
            "target_date": target_date,
            "hotel_filter_applied": "hotel_id" in columns and bool(hotel_id),
            "aggregation": "COUNT(*)",
        }
    except Exception as exc:
        return None, None, {
            "table": table,
            "rows": 0,
            "status": "error",
            "where": "DATE(review_time)=DATE_SUB(CURDATE(), INTERVAL 1 DAY)",
            "error": str(exc),
        }


def _attach_yesterday_review_count(
    dataset: dict[str, list[dict[str, Any]]],
    count: int | None,
    target_date: str | None,
    table: str,
) -> None:
    """Attach the exact count to the newest Meituan overview row."""

    overviews = dataset.setdefault("review_overviews", [])
    candidates = [
        row
        for row in overviews
        if str(row.get("platform") or row.get("review_platform") or "").lower()
        in {"meituan", "美团"}
    ]
    if candidates:
        target = max(
            candidates,
            key=lambda row: str(row.get("snapshot_time") or row.get("updated_at") or ""),
        )
    else:
        target = {
            "platform": "meituan",
            "review_platform": "美团",
            "source_table": table,
        }
        overviews.append(target)

    target["yesterday_new_review_count"] = count
    target["yesterday_review_date"] = target_date
    target["yesterday_review_time_rule"] = (
        "DATE(review_time)=DATE_SUB(CURDATE(), INTERVAL 1 DAY)"
    )


def load_mysql_dsn_dataset(
    dsn: str,
    limit: int = 5000,
    tables: dict[str, str] | None = None,
    hotel_id: str | None = "puyue",
    platform: str | None = "multi",
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Load established sources, JL11 summaries and exact yesterday review count."""

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
    review_table = table_map["meituan_reviews"]
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
            review_count, review_date, review_diag = _yesterday_review_count(
                cursor,
                review_table,
                hotel_id=hotel_id,
            )

    summary_rows = _latest_summary_rows(rows)
    dataset["room_type_performance_daily"] = base._tag_rows(summary_rows, jl11_table)
    _attach_yesterday_review_count(
        dataset,
        review_count,
        review_date,
        review_table,
    )

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
        diagnostics.setdefault("tables", {})[
            "meituan_reviews_yesterday"
        ] = review_diag
        diagnostics.setdefault("transformations", []).extend(
            [
                {
                    "section": "room_type_performance_daily",
                    "rows": len(summary_rows),
                    "rule": (
                        "item 02 uses jl11 room_count, room_nights, occupancy_rate, "
                        "room_revenue, average_room_price and revpar"
                    ),
                },
                {
                    "section": "review_overviews",
                    "rows": review_count,
                    "rule": (
                        "item 13 yesterday new reviews = COUNT(*) from "
                        "meituan_ota_review_detail where DATE(review_time) is MySQL yesterday"
                    ),
                },
            ]
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
    "_attach_yesterday_review_count",
    "_latest_summary_rows",
    "_yesterday_review_count",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
