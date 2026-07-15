from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader_v4 as previous
from marketing_diagnosis.db_loader_v2 import _scan_order_count


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
}


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _upsert_scan_order_summary(
    dataset: dict[str, list[dict[str, Any]]],
    summary: dict[str, Any] | None,
) -> None:
    """Keep exactly one scan-order summary row in ``ota_funnel``.

    ``db_loader_v4`` rebuilds Meituan funnel rows from FLOW_* metrics. That
    replacement must not discard the auxiliary scan-order COUNT(*) summary
    produced by the earlier loader layer.
    """
    rows = list(dataset.get("ota_funnel") or [])
    rows = [
        row
        for row in rows
        if str(row.get("period_type") or "") != "scan_order_summary"
        and row.get("scan_order_count") is None
    ]
    if summary is not None:
        rows.append(summary)
    dataset["ota_funnel"] = rows


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

    if "meituan" not in previous._BASE._enabled_platforms(platform):
        return dataset

    scan_table = table_map["meituan_scan_orders"]
    with previous._BASE._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            summary, scan_diag = _scan_order_count(
                cursor,
                scan_table,
                hotel_id,
                period_start,
                period_end,
            )

    _upsert_scan_order_summary(dataset, summary)

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {})["meituan_scan_orders_v5"] = {
            **scan_diag,
            "summary_preserved": summary is not None,
            "aggregation_rule": (
                "COUNT(*) from meituan_ota_scan_order_detail; "
                "preserved after FLOW_* funnel reconstruction"
            ),
        }
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "ota_funnel",
                "rows": 1 if summary is not None else 0,
                "rule": "preserve scan_order_summary after Meituan funnel rebuild",
            }
        )

    return dataset


def load_database_dataset(config_path):
    config = previous._BASE._load_json(config_path)
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
    "_upsert_scan_order_summary",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
