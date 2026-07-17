from __future__ import annotations

import os
from datetime import date
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v14 as previous


DEFAULT_MYSQL_TABLES = dict(previous.DEFAULT_MYSQL_TABLES)
CATEGORY = "总营业指标"
METRIC_NAMES = (
    "客房数",
    "维修房",
    "过夜房",
    "过夜房出租率",
    "过夜房出租率(扣自用房)",
    "间夜数",
    "房费",
    "平均房价",
    "出租率",
    "RevPar",
    "现付账房费",
)


def _date(value: Any) -> date | None:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _shift_month_start(value: date, months: int) -> date:
    absolute = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(absolute, 12)
    return date(year, month_index + 1, 1)


def _jl02_history_start(latest_business_day: Any) -> str | None:
    """Return the earliest month required by the three-month YOY chart.

    A latest date of 2026-07-16 needs May-July 2026 and May-July 2025, so the
    database history query must start at 2025-05-01.
    """

    latest = _date(latest_business_day)
    if latest is None:
        return None
    return _shift_month_start(latest.replace(day=1), -14).isoformat()


def _jl02_filters(
    columns: set[str],
    hotel_id: str | None,
) -> tuple[list[str], list[Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if hotel_id and "hotel_id" in columns:
        filters.append("`hotel_id` = %s")
        params.append(hotel_id)
    if "category" in columns:
        filters.append("`category` = %s")
        params.append(CATEGORY)
    if "room_type_id" in columns:
        filters.append("(`room_type_id` IS NULL OR `room_type_id` = '')")
    if "metric_name" in columns:
        placeholders = ",".join(["%s"] * len(METRIC_NAMES))
        filters.append(f"`metric_name` IN ({placeholders})")
        params.extend(METRIC_NAMES)
    return filters, params


def _load_jl02_history(
    cursor,
    table: str,
    limit: int,
    hotel_id: str | None,
    period_end: str | None,
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
    if "business_date" not in columns:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "required column missing: business_date",
            "table_columns": sorted(columns),
        }

    filters, params = _jl02_filters(columns, hotel_id)
    latest_filters = list(filters)
    latest_params = list(params)
    if period_end:
        latest_filters.append("DATE(`business_date`) <= %s")
        latest_params.append(period_end)

    latest_sql = (
        f"SELECT MAX(DATE(`business_date`)) AS latest_business_date "
        f"FROM {base._safe_identifier(table)}"
    )
    latest_where = base._where(latest_filters)
    if latest_where:
        latest_sql += f" WHERE {latest_where}"
    try:
        cursor.execute(latest_sql, latest_params)
        latest_row = cursor.fetchone() or {}
    except Exception as exc:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "stage": "latest business_date",
            "error": str(exc),
        }

    latest = _date(latest_row.get("latest_business_date"))
    history_start = _jl02_history_start(latest)
    if latest is None or history_start is None:
        return [], {
            "table": table,
            "rows": 0,
            "status": "empty",
            "latest_business_date": None,
        }

    history_filters = list(filters)
    history_params = list(params)
    history_filters.append("DATE(`business_date`) >= %s")
    history_params.append(history_start)
    history_filters.append("DATE(`business_date`) <= %s")
    history_params.append(latest.isoformat())

    order_parts = ["`business_date` ASC"]
    if "snapshot_time" in columns:
        order_parts.append("`snapshot_time` ASC")
    if "metric_name" in columns:
        order_parts.append("`metric_name` ASC")

    rows, diag = base._fetch(
        cursor,
        table,
        max(limit, 100000),
        base._where(history_filters),
        history_params,
        ", ".join(order_parts),
    )
    return rows, {
        **diag,
        "latest_business_date": latest.isoformat(),
        "history_start": history_start,
        "history_end": latest.isoformat(),
        "rows_used": len(rows),
        "selection_rule": (
            "complete current three-month and prior-year comparison window; "
            "category=总营业指标; room_type_id empty; fixed operating metrics only"
        ),
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
    dataset = previous.load_mysql_dsn_dataset(
        dsn,
        limit=limit,
        tables=table_map,
        hotel_id=hotel_id,
        platform=platform,
        period_start=period_start,
        period_end=period_end,
    )

    table = table_map["jl02"]
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            rows, diag = _load_jl02_history(
                cursor,
                table,
                limit,
                hotel_id,
                period_end,
            )

    if rows:
        dataset["hotel_performance_daily"] = base._tag_rows(rows, table)

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["jl02_history_v61"] = diag
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "hotel_performance_daily",
                "rows": len(rows),
                "rule": (
                    "reload JL02 by the complete trend comparison date window so "
                    "older prior-year months are not truncated by a global row limit"
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
    "CATEGORY",
    "DEFAULT_MYSQL_TABLES",
    "METRIC_NAMES",
    "_jl02_history_start",
    "_load_jl02_history",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
