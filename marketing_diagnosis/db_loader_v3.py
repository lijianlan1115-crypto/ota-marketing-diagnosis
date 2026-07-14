from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader_v2 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
}


def _review_platform_key(row: dict[str, Any]) -> str:
    for key in ("review_platform", "channel_source", "platform", "source_platform"):
        value = str(row.get(key) or "").strip().lower()
        if value:
            return value
    return "unknown"


def _latest_review_overview_per_platform(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, tuple[tuple[str, str, str, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        platform = _review_platform_key(row)
        sort_key = (
            str(row.get("snapshot_time") or ""),
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            index,
        )
        current = latest.get(platform)
        if current is None or sort_key >= current[0]:
            latest[platform] = (sort_key, row)
    return [latest[key][1] for key in sorted(latest)]


def _room_identity(row: dict[str, Any]) -> str:
    for key in ("room_type_id", "pms_rate_room_type_id", "room_type_name"):
        value = str(row.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    return ""


def _latest_room_row_per_day(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the newest snapshot for each business date and room type.

    jl01_room_type_performance_daily is a wide daily table. A historical
    business date may be captured repeatedly by later collection snapshots, so
    each date/room pair must use the newest snapshot before 30-day aggregation.
    """
    latest: dict[tuple[str, str], tuple[tuple[str, str, str, int], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        day = str(row.get("business_date") or "")[:10]
        room_key = _room_identity(row)
        if not day or not room_key:
            continue
        sort_key = (
            str(row.get("snapshot_time") or ""),
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            index,
        )
        key = (day, room_key)
        current = latest.get(key)
        if current is None or sort_key >= current[0]:
            latest[key] = (sort_key, row)

    return [
        latest[key][1]
        for key in sorted(
            latest,
            key=lambda item: (
                item[0],
                str(latest[item][1].get("room_type_id") or ""),
                str(latest[item][1].get("pms_rate_room_type_id") or ""),
                str(latest[item][1].get("room_type_name") or ""),
            ),
        )
    ]


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

    room_table = table_map["jl01"]
    review_table = table_map["meituan_review_overview"]
    meituan_enabled = "meituan" in previous.base._enabled_platforms(platform)

    review_rows: list[dict[str, Any]] = []
    review_diag: dict[str, Any] = {}

    with previous.base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            room_rows, room_diag = previous.base._profiled_fetch(
                cursor,
                room_table,
                max(limit, 50000),
                hotel_id=hotel_id,
                date_column="business_date",
                period_start=period_start,
                period_end=period_end,
                order_candidates=(
                    "business_date ASC",
                    "room_type_id ASC",
                    "pms_rate_room_type_id ASC",
                    "snapshot_time ASC",
                ),
            )

            if meituan_enabled:
                review_rows, review_diag = previous.base._profiled_fetch(
                    cursor,
                    review_table,
                    max(200, min(limit, 5000)),
                    hotel_id=hotel_id,
                    order_candidates=(
                        "snapshot_time DESC",
                        "review_platform ASC",
                        "updated_at DESC",
                    ),
                )

    daily_room_rows = _latest_room_row_per_day(room_rows)
    dataset["room_type_performance_daily"] = previous.base._tag_rows(
        daily_room_rows,
        room_table,
    )

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["jl01"] = {
            **room_diag,
            "rows_used": len(daily_room_rows),
            "aggregation_rule": (
                "按 business_date + 房型去重，每组保留最新 snapshot_time；"
                "直接读取 occupancy_rate、revpar、room_nights、room_revenue"
            ),
        }
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "room_type_performance_daily",
                "rows": len(daily_room_rows),
                "rule": (
                    "wide jl01 daily rows filtered by requested business_date range "
                    "and deduplicated by day + room"
                ),
            }
        )

    if not meituan_enabled:
        return dataset

    latest_reviews = _latest_review_overview_per_platform(review_rows)
    preserved = [
        row
        for row in dataset.get("review_overviews") or []
        if str(row.get("source_table") or row.get("__source_table") or "") != review_table
    ]
    dataset["review_overviews"] = preserved + previous.base._copy_rows(
        latest_reviews,
        "meituan",
        review_table,
    )

    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["meituan_review_overview_per_platform"] = {
            **review_diag,
            "rows_used": len(latest_reviews),
            "aggregation_rule": "按 review_platform 分组，各自取得最新 snapshot_time 记录",
        }
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "review_overviews",
                "rows": len(latest_reviews),
                "rule": "latest review overview row per review_platform",
            }
        )

    return dataset


def load_database_dataset(config_path):
    config = previous.base._load_json(config_path)
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
