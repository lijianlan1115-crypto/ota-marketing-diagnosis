from __future__ import annotations

from datetime import date
from typing import Any

from marketing_diagnosis import db_loader_v3 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
}

_BASE = previous.previous.base
_DAILY_PERIODS = {"日", "daily", "day", "当日"}
_FLOW_CODE_MAP = {
    "FLOW_EXPOSURE_UV": "exposure",
    "FLOW_INTENTION_UV": "views",
    "FLOW_PAY_ORDER_CNT": "paid_orders",
    "FLOW_INTENTION_PER_EXPOSURE": "exposure_to_view_rate",
    "FLOW_PAY_ORDER_PER_INTENTION": "payment_conversion_rate",
}
_METRIC_NAME_MAP = {
    "曝光人数": "exposure",
    "曝光量": "exposure",
    "浏览人数": "views",
    "浏览量": "views",
    "支付订单数": "paid_orders",
    "订单数": "paid_orders",
    "支付转化率": "payment_conversion_rate",
    "浏览-支付转化率": "payment_conversion_rate",
    "曝光-浏览转化率": "exposure_to_view_rate",
    "HOS分": "hos_score",
    "信息分": "content_score",
}
_RATE_TARGETS = {
    "payment_conversion_rate",
    "exposure_to_view_rate",
}


def _previous_year_date(value: str | None) -> str | None:
    """Return the same calendar day in the previous year.

    February 29 falls back to February 28 when the previous year is not a leap
    year. Empty or invalid values are returned as ``None``.
    """
    text = str(value or "")[:10]
    if not text:
        return None
    try:
        current = date.fromisoformat(text)
    except ValueError:
        return None
    try:
        return current.replace(year=current.year - 1).isoformat()
    except ValueError:
        return current.replace(year=current.year - 1, day=28).isoformat()


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _period(value: Any) -> str:
    text = str(value or "").strip()
    return "日" if text.lower() in _DAILY_PERIODS else text


def _metric_target(row: dict[str, Any]) -> tuple[str | None, int]:
    """Return the normalized target and source priority.

    FLOW_* rows are the canonical source for the traffic funnel. The same
    Chinese metric names also appear in ordinary business metrics, but their
    peer averages and even values may differ. They are therefore only used as
    a fallback when the corresponding FLOW_* row is absent.
    """
    metric_code = str(row.get("metric_code") or "").strip().upper()
    if metric_code in _FLOW_CODE_MAP:
        return _FLOW_CODE_MAP[metric_code], 1000

    metric_name = str(row.get("metric_name") or "").strip()
    target = _METRIC_NAME_MAP.get(metric_name)
    if not target:
        return None, 0

    # HOS and information score do not have a FLOW_* replacement. For traffic
    # targets this lower priority deliberately allows FLOW_* rows to win.
    return target, 500 if target in {"hos_score", "content_score"} else 100


def _pivot_meituan_metrics(
    rows: list[dict[str, Any]],
    source_table: str,
) -> list[dict[str, Any]]:
    """Pivot Meituan metric rows with metric_code-aware source priority."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    selected: dict[tuple[str, str], dict[str, tuple[int, str, str, int]]] = {}

    for index, row in enumerate(rows):
        target, priority = _metric_target(row)
        if not target:
            continue

        day = str(row.get("business_date") or row.get("snapshot_time") or "")[:10]
        if not day:
            continue
        period = _period(row.get("stats_period_type") or row.get("period_type"))
        group_key = (period, day)
        item = grouped.setdefault(
            group_key,
            {
                "platform": "meituan",
                "business_date": day,
                "period_type": period,
                "source_table": source_table,
            },
        )
        item["snapshot_time"] = max(
            str(item.get("snapshot_time") or ""),
            str(row.get("snapshot_time") or ""),
        )

        candidate = (
            priority,
            str(row.get("snapshot_time") or ""),
            str(row.get("updated_at") or row.get("created_at") or ""),
            index,
        )
        target_selected = selected.setdefault(group_key, {})
        current = target_selected.get(target)
        if current is not None and candidate < current:
            continue
        target_selected[target] = candidate

        if target in _RATE_TARGETS:
            value = _BASE._ratio(row.get("metric_value"))
            peer = _BASE._ratio(row.get("peer_average"))
        else:
            value = _BASE._float(row.get("metric_value"))
            peer = _BASE._float(row.get("peer_average"))

        item[target] = value
        if peer is not None:
            item[f"peer_{target}"] = peer
            if target == "payment_conversion_rate":
                item["peer_avg_conversion_rate"] = peer
        else:
            item.pop(f"peer_{target}", None)
            if target == "payment_conversion_rate":
                item.pop("peer_avg_conversion_rate", None)

        raw_rank = str(row.get("competitor_rank") or "").strip()
        rank = _BASE._rank(raw_rank)
        if raw_rank:
            item[f"{target}_rank_raw"] = raw_rank
        else:
            item.pop(f"{target}_rank_raw", None)
        if rank is not None:
            item[f"{target}_rank"] = rank
        else:
            item.pop(f"{target}_rank", None)

        item[f"{target}_metric_code"] = row.get("metric_code")
        item[f"{target}_metric_name"] = row.get("metric_name")

    return [grouped[key] for key in sorted(grouped, key=lambda value: (value[1], value[0]))]


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

    jl02_table = table_map["jl02"]
    history_start = _previous_year_date(period_start or period_end)
    meituan_enabled = "meituan" in _BASE._enabled_platforms(platform)
    meituan_table = table_map["meituan_funnel"]
    meituan_rows: list[dict[str, Any]] = []
    meituan_diag: dict[str, Any] = {}

    # JL02 stores current and previous-year values in the same table. Query the
    # requested period plus the matching prior-year period so the diagnosis can
    # compare rows by business_date rather than by collection snapshot time.
    with _BASE._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            rows, diag = _BASE._profiled_fetch(
                cursor,
                jl02_table,
                max(limit, 100000),
                hotel_id=hotel_id,
                date_column="business_date",
                period_start=history_start,
                period_end=period_end,
                order_candidates=(
                    "business_date ASC",
                    "metric_name ASC",
                    "snapshot_time ASC",
                ),
            )

            if meituan_enabled:
                meituan_rows, meituan_diag = _BASE._profiled_fetch(
                    cursor,
                    meituan_table,
                    max(limit, 100000),
                    hotel_id=hotel_id,
                    date_column="business_date",
                    period_start=period_start,
                    period_end=period_end,
                    order_candidates=(
                        "business_date ASC",
                        "stats_period_type ASC",
                        "metric_code ASC",
                        "snapshot_time ASC",
                    ),
                )

    dataset["hotel_performance_daily"] = _BASE._tag_rows(rows, jl02_table)

    precise_meituan_rows: list[dict[str, Any]] = []
    if meituan_enabled:
        precise_meituan_rows = _pivot_meituan_metrics(meituan_rows, meituan_table)
        other_platform_rows = [
            row
            for row in dataset.get("ota_funnel") or []
            if str(row.get("platform") or "").lower() != "meituan"
        ]
        dataset["ota_funnel"] = other_platform_rows + precise_meituan_rows

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["jl02_business_date_yoy"] = {
            **diag,
            "rows_used": len(rows),
            "history_start": history_start,
            "period_end": period_end,
            "aggregation_rule": (
                "JL02按business_date读取本期与去年同期；"
                "去年同期为当前业务日期的上一年同月同日"
            ),
        }
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "hotel_performance_daily",
                "rows": len(rows),
                "rule": (
                    "jl02 current-period and prior-year rows loaded from the "
                    "same table for exact business_date YOY matching"
                ),
            }
        )
        if meituan_enabled:
            diagnostics.setdefault("tables", {})["meituan_funnel_flow_priority"] = {
                **meituan_diag,
                "rows_used": len(precise_meituan_rows),
                "aggregation_rule": (
                    "按business_date+日口径透视；流量指标优先metric_code=FLOW_*；"
                    "同日期同指标保留最新snapshot_time"
                ),
            }
            diagnostics.setdefault("transformations", []).append(
                {
                    "section": "ota_funnel",
                    "rows": len(precise_meituan_rows),
                    "rule": "canonical FLOW_* metrics override ordinary same-name metrics",
                }
            )

    return dataset


def load_database_dataset(config_path):
    config = _BASE._load_json(config_path)
    kind = str(config.get("kind") or config.get("type") or "sqlite").lower()
    if kind not in {"mysql", "mysql+pymysql"}:
        return previous.load_database_dataset(config_path)

    dsn = config.get("dsn") or __import__("os").environ.get(str(config.get("dsn_env") or ""))
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
    "_pivot_meituan_metrics",
    "_previous_year_date",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
