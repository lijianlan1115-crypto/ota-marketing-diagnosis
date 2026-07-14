from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base


DEFAULT_MYSQL_TABLES = {
    **base.DEFAULT_MYSQL_TABLES,
    "meituan_scan_orders": "meituan_ota_scan_order_detail",
}

_DAILY_PERIODS = {"日", "daily", "day", "当日"}
_METRIC_MAP = {
    "曝光人数": "exposure",
    "曝光量": "exposure",
    "浏览人数": "views",
    "浏览量": "views",
    "支付订单数": "paid_orders",
    "订单数": "paid_orders",
    "销售间夜": "sold_room_nights",
    "销售均价": "sale_adr",
    "销售额": "sales_revenue",
    "入住间夜": "checkin_room_nights",
    "满房率": "full_occupancy_rate",
    "引流价": "entry_price",
    "评价分": "rating_score",
    "信息分": "content_score",
    "HOS分": "hos_score",
    "支付转化率": "payment_conversion_rate",
    "浏览-支付转化率": "payment_conversion_rate",
    "曝光-浏览转化率": "exposure_to_view_rate",
}

# 同一个日期可能同时存在“人数”和“量”等同类指标。报告口径明确使用
# 曝光人数、浏览人数、支付订单数，因此必须优先选择这些标准指标，不能
# 因 SQL 返回顺序而被别名行覆盖。
_METRIC_PRIORITY = {
    "曝光人数": 100,
    "曝光量": 50,
    "浏览人数": 100,
    "浏览量": 50,
    "支付订单数": 100,
    "订单数": 50,
    "浏览-支付转化率": 100,
    "支付转化率": 50,
}

_ALLOWED_MEITUAN_NAMES = {
    "浏览人数",
    "浏览量",
    "支付订单数",
    "订单数",
    "支付转化率",
    "曝光-浏览转化率",
    "浏览-支付转化率",
    "曝光人数",
    "曝光量",
    "HOS分",
    "信息分",
}


def _period(value: Any) -> str:
    text = str(value or "").strip()
    return "日" if text.lower() in _DAILY_PERIODS else text


def _candidate_key(row: dict[str, Any], metric_name: str, index: int) -> tuple[int, str, int]:
    return (
        _METRIC_PRIORITY.get(metric_name, 80),
        str(row.get("snapshot_time") or ""),
        index,
    )


def _pivot_funnel_precise(
    rows: list[dict[str, Any]],
    platform: str,
    source_table: str,
) -> list[dict[str, Any]]:
    """Pivot metric rows without allowing aliases to overwrite canonical metrics."""
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    selected: dict[tuple[str, str, str], dict[str, tuple[int, str, int]]] = {}

    for index, row in enumerate(rows):
        metric_name = str(row.get("metric_name") or "").strip()
        target = _METRIC_MAP.get(metric_name)
        if not target:
            continue

        period = _period(row.get("stats_period_type") or row.get("period_type"))
        day = str(row.get("business_date") or row.get("snapshot_time") or "")[:10]
        group_key = (platform, period, day)
        item = grouped.setdefault(
            group_key,
            {
                "platform": platform,
                "business_date": day,
                "period_type": period,
                "source_table": source_table,
            },
        )
        item["snapshot_time"] = max(
            str(item.get("snapshot_time") or ""),
            str(row.get("snapshot_time") or ""),
        )

        candidate = _candidate_key(row, metric_name, index)
        target_selected = selected.setdefault(group_key, {})
        if target in target_selected and candidate < target_selected[target]:
            continue
        target_selected[target] = candidate

        if target in {"payment_conversion_rate", "exposure_to_view_rate", "full_occupancy_rate"}:
            item[target] = base._ratio(row.get("metric_value"))
            peer = base._ratio(row.get("peer_average"))
        else:
            item[target] = base._float(row.get("metric_value"))
            peer = base._float(row.get("peer_average"))

        if peer is not None:
            item[f"peer_{target}"] = peer
            if target == "payment_conversion_rate":
                item["peer_avg_conversion_rate"] = peer

        raw_rank = str(row.get("competitor_rank") or "").strip()
        rank_position = base._rank(raw_rank)
        if raw_rank:
            item[f"{target}_rank_raw"] = raw_rank
        if rank_position is not None:
            item[f"{target}_rank"] = rank_position
            item.setdefault("peer_rank", rank_position)

        if row.get("metric_code") not in (None, ""):
            item[f"{target}_metric_code"] = row.get("metric_code")
        item[f"{target}_metric_name"] = metric_name

    return list(grouped.values())


def _scan_order_count(
    cursor,
    table: str,
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
            "error": schema_error,
            "stage": "SHOW COLUMNS",
        }

    filters: list[str] = []
    params: list[Any] = []
    if hotel_id and "hotel_id" in columns:
        filters.append("hotel_id = %s")
        params.append(hotel_id)

    date_candidates = (
        "business_date",
        "order_date",
        "scan_date",
        "scan_time",
        "order_time",
        "order_create_time",
        "created_at",
        "create_time",
        "snapshot_time",
    )
    date_column = next((column for column in date_candidates if column in columns), None)
    if date_column:
        date_filter = base._date_range(date_column, period_start, period_end, params)
        if date_filter:
            filters.append(date_filter)

    where = base._where(filters)
    sql = f"SELECT COUNT(*) AS order_count FROM {base._safe_identifier(table)}"
    if where:
        sql += f" WHERE {where}"

    try:
        cursor.execute(sql, params)
        row = dict(cursor.fetchone() or {})
        count = int(row.get("order_count") or 0)
        summary = {
            "platform": "meituan",
            "period_type": "scan_order_summary",
            "business_date": period_end or "",
            "scan_order_count": count,
            "scan_order_date_column": date_column,
            "scan_order_period_start": period_start,
            "scan_order_period_end": period_end,
            "scan_order_source_table": table,
        }
        return summary, {
            "table": table,
            "where": where,
            "rows": count,
            "aggregation": "COUNT(*)",
            "date_column": date_column,
            "table_columns": sorted(columns),
            "hotel_filter_applied": "hotel_id" in columns,
            "status": "ok",
        }
    except Exception as exc:
        return None, {
            "table": table,
            "where": where,
            "rows": 0,
            "aggregation": "COUNT(*)",
            "date_column": date_column,
            "table_columns": sorted(columns),
            "status": "error",
            "error": str(exc),
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
    dataset = base.load_mysql_dsn_dataset(
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

    diagnostics = _diagnostics(dataset)
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            funnel_table = table_map["meituan_funnel"]
            rows, funnel_diag = base._profiled_fetch(
                cursor,
                funnel_table,
                limit,
                hotel_id=hotel_id,
                date_column="business_date",
                period_start=period_start,
                period_end=period_end,
                order_candidates=(
                    "business_date ASC",
                    "stats_period_type ASC",
                    "metric_name ASC",
                    "snapshot_time ASC",
                ),
            )
            rows = [
                row
                for row in rows
                if str(row.get("metric_code") or "").startswith("flow")
                or str(row.get("metric_name") or "").strip() in _ALLOWED_MEITUAN_NAMES
            ]
            precise_rows = _pivot_funnel_precise(rows, "meituan", funnel_table)
            other_platform_rows = [
                row
                for row in dataset.get("ota_funnel") or []
                if str(row.get("platform") or "").lower() != "meituan"
            ]
            dataset["ota_funnel"] = other_platform_rows + precise_rows

            scan_summary, scan_diag = _scan_order_count(
                cursor,
                table_map["meituan_scan_orders"],
                hotel_id,
                period_start,
                period_end,
            )
            if scan_summary is not None:
                dataset["ota_funnel"].append(scan_summary)

    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["meituan_funnel_precise"] = {
            **funnel_diag,
            "rows_used": len(precise_rows),
            "aggregation_rule": (
                "按 business_date + 日口径聚合；曝光人数/浏览人数/支付订单数优先于同义别名"
            ),
        }
        diagnostics.setdefault("tables", {})["meituan_scan_orders"] = scan_diag
        diagnostics.setdefault("transformations", []).extend(
            [
                {
                    "section": "ota_funnel",
                    "rows": len(precise_rows),
                    "rule": "canonical daily metric pivot with latest snapshot and alias priority",
                },
                {
                    "section": "scan_orders",
                    "rows": scan_diag.get("rows", 0),
                    "rule": "COUNT(*) from meituan_ota_scan_order_detail within requested period when a date column exists",
                },
            ]
        )

    return dataset


def load_database_dataset(config_path):
    config = base._load_json(config_path)
    kind = str(config.get("kind") or config.get("type") or "sqlite").lower()
    if kind not in {"mysql", "mysql+pymysql"}:
        return base.load_database_dataset(config_path)

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
