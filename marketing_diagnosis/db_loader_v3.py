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

    if "meituan" not in previous.base._enabled_platforms(platform):
        return dataset

    table = table_map["meituan_review_overview"]
    with previous.base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            rows, diag = previous.base._profiled_fetch(
                cursor,
                table,
                max(200, min(limit, 5000)),
                hotel_id=hotel_id,
                order_candidates=(
                    "snapshot_time DESC",
                    "review_platform ASC",
                    "updated_at DESC",
                ),
            )

    latest = _latest_review_overview_per_platform(rows)
    preserved = [
        row
        for row in dataset.get("review_overviews") or []
        if str(row.get("source_table") or row.get("__source_table") or "") != table
    ]
    dataset["review_overviews"] = preserved + previous.base._copy_rows(latest, "meituan", table)

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["meituan_review_overview_per_platform"] = {
            **diag,
            "rows_used": len(latest),
            "aggregation_rule": "按 review_platform 分组，各自取得最新 snapshot_time 记录",
        }
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "review_overviews",
                "rows": len(latest),
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
