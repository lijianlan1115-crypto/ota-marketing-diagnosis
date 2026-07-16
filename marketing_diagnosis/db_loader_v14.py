from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from marketing_diagnosis import db_loader_v13 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
}

FLOW_TABLE = "meituan_ota_flow_conversion_30d"
_START_KEYS = (
    "flow_period_start",
    "period_start",
    "start_date",
    "stats_start_date",
    "stat_start_date",
    "data_start_date",
    "begin_date",
)
_END_KEYS = (
    "flow_period_end",
    "period_end",
    "end_date",
    "stats_end_date",
    "stat_end_date",
    "data_end_date",
    "business_date",
    "data_date",
    "stats_date",
    "stat_date",
    "snapshot_date",
    "snapshot_time",
    "updated_at",
    "created_at",
)


def _date_text(value: Any) -> str | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _first_date(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        parsed = _date_text(row.get(key))
        if parsed:
            return parsed
    return None


def _flow_period(row: dict[str, Any]) -> tuple[str | None, str | None, str]:
    """Return the real display range for a 30-day aggregate row.

    Explicit source start/end fields win. When the source only provides its
    latest business date, the period starts 29 calendar days earlier because
    the table itself is a rolling 30-day aggregate.
    """

    start = _first_date(row, _START_KEYS)
    end = _first_date(row, _END_KEYS)
    period_days = int(row.get("period_days") or 30)

    if end and not start:
        start = (date.fromisoformat(end) - timedelta(days=max(period_days, 1) - 1)).isoformat()
    if start and not end:
        end = (date.fromisoformat(start) + timedelta(days=max(period_days, 1) - 1)).isoformat()

    if start and end:
        return start, end, f"{start} 至 {end}"
    if end:
        return None, end, f"近30天（截至 {end}）"
    return None, None, "近30天"


def attach_flow_period_range(
    dataset: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    for row in dataset.get("ota_funnel") or []:
        source = str(row.get("source_table") or row.get("__source_table") or "")
        if not source.endswith(FLOW_TABLE):
            continue
        start, end, label = _flow_period(row)
        row["flow_period_start"] = start
        row["flow_period_end"] = end
        row["flow_period_label"] = label
    return dataset


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
    return attach_flow_period_range(dataset)


def load_database_dataset(config_path):
    config = previous.base._load_json(config_path)
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
    "FLOW_TABLE",
    "_flow_period",
    "attach_flow_period_range",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
