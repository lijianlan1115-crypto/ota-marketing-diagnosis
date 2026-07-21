from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v15 as previous


DEFAULT_MYSQL_TABLES = {
    **previous.DEFAULT_MYSQL_TABLES,
    "ctrip_joined_rights": "ctrip_ota_joined_rights",
    "ctrip_promotion_status": "ctrip_ota_promotion_status",
    "ctrip_userprofile_distribution": "ctrip_ota_userprofile_distribution",
}

_ORDER_COLUMNS = (
    "snapshot_time",
    "updated_at",
    "created_at",
    "business_date",
    "data_date",
    "id",
)


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _row_key(row: dict[str, Any]) -> tuple[str, str, str]:
    dimension = str(row.get("dimension_code") or "").strip()
    bucket = str(
        row.get("bucket_code")
        or row.get("bucket_label")
        or row.get("bucket_name")
        or row.get("dimension_label")
        or ""
    ).strip()
    hotel = str(row.get("hotel_id") or "").strip()
    return hotel, dimension, bucket


def _order_key(row: dict[str, Any], index: int) -> tuple[str, str, str, str, str, int, int]:
    try:
        row_id = int(row.get("id") or 0)
    except (TypeError, ValueError):
        row_id = 0
    return (
        str(row.get("snapshot_time") or ""),
        str(row.get("updated_at") or ""),
        str(row.get("created_at") or ""),
        str(row.get("business_date") or ""),
        str(row.get("data_date") or ""),
        row_id,
        index,
    )


def _sort_number(value: Any) -> float:
    if value in (None, ""):
        return 999999.0
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 999999.0


def latest_distribution_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the newest row for every dimension/bucket pair.

    User-profile dimensions may be refreshed independently, so selecting one
    global snapshot timestamp can accidentally discard valid dimensions. This
    function keeps the latest row for each dimension_code + bucket pair.
    """

    selected: dict[tuple[str, str, str], tuple[tuple[Any, ...], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        key = _row_key(row)
        order = _order_key(row, index)
        current = selected.get(key)
        if current is None or order >= current[0]:
            selected[key] = (order, dict(row))

    output = [value[1] for value in selected.values()]
    output.sort(
        key=lambda row: (
            str(row.get("dimension_code") or ""),
            _sort_number(row.get("sort_order")),
            _sort_number(row.get("rank") or row.get("ranking_position")),
            str(row.get("bucket_label") or row.get("bucket_name") or ""),
        )
    )
    return output


def _load_user_profile(
    cursor,
    table: str,
    limit: int,
    hotel_id: str | None,
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
    if "dimension_code" not in columns:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "required column missing: dimension_code",
            "table_columns": sorted(columns),
        }

    order_candidates = tuple(
        [f"{name} DESC" for name in _ORDER_COLUMNS if name in columns]
        + [
            value
            for value in ("dimension_code ASC", "sort_order ASC", "rank ASC", "bucket_label ASC")
            if value.rsplit(" ", 1)[0] in columns
        ]
    )
    rows, diag = base._profiled_fetch(
        cursor,
        table,
        max(limit, 10000),
        hotel_id=hotel_id,
        order_candidates=order_candidates,
    )
    latest = latest_distribution_rows(rows)
    return latest, {
        **diag,
        "rows_read": len(rows),
        "rows_used": len(latest),
        "selection_rule": "latest row per hotel_id + dimension_code + bucket",
    }


def _latest_configuration_rows(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    selected: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        name = str(row.get(key) or "").strip()
        if not name:
            continue
        order = _order_key(row, index)
        current = selected.get(name)
        if current is None or order >= current[0]:
            selected[name] = (order, dict(row))
    return [selected[name][1] for name in sorted(selected)]


def _load_ctrip_configuration(
    cursor,
    table: str,
    limit: int,
    hotel_id: str | None,
    key: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    columns, schema_error = base._table_columns(cursor, table)
    if schema_error:
        return [], {"table": table, "rows": 0, "status": "error", "error": schema_error}
    if key not in columns:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": f"required column missing: {key}",
            "table_columns": sorted(columns),
        }
    order_candidates = tuple(
        [f"{name} DESC" for name in _ORDER_COLUMNS if name in columns]
        + [f"{key} ASC"]
    )
    rows, diag = base._profiled_fetch(
        cursor,
        table,
        limit,
        hotel_id=hotel_id,
        order_candidates=order_candidates,
    )
    latest = _latest_configuration_rows(rows, key)
    return latest, {
        **diag,
        "rows_read": len(rows),
        "rows_used": len(latest),
        "selection_rule": f"latest row per {key}",
    }


def _load_ctrip_yesterday_counts(
    cursor,
    table: str,
    hotel_id: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    columns, schema_error = base._table_columns(cursor, table)
    if schema_error:
        return [], {"table": table, "rows": 0, "status": "error", "error": schema_error}
    if "review_time" not in columns or "platform_scope" not in columns:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "required columns missing: review_time, platform_scope",
            "table_columns": sorted(columns),
        }

    group_columns = ["platform_scope"]
    select_columns = ", ".join(base._safe_identifier(column) for column in group_columns)
    group_by = ", ".join(base._safe_identifier(column) for column in group_columns)
    params: list[Any] = []
    filters: list[str] = [
        "DATE(`review_time`) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)"
    ]
    if hotel_id and "hotel_id" in columns:
        filters.insert(0, "`hotel_id` = %s")
        params.append(hotel_id)
    sql = (
        f"SELECT {select_columns + ', ' if select_columns else ''}"
        "COUNT(*) AS yesterday_new_review_count "
        f"FROM {base._safe_identifier(table)} WHERE {base._where(filters)}"
    )
    if group_by:
        sql += f" GROUP BY {group_by}"
    try:
        cursor.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        platform_aliases = {
            "携程": "ctrip",
            "去哪儿": "qunar",
            "去哪兒": "qunar",
            "同程": "tongcheng",
            "同程旅行": "tongcheng",
            "智行": "zhixing",
        }
        existing_platforms = {
            platform_aliases.get(
                str(row.get("platform_scope") or row.get("channel_source") or "").strip(),
                str(row.get("platform_scope") or row.get("channel_source") or "").strip().lower(),
            )
            for row in rows
        }
        rows.extend(
            {
                "platform_scope": platform,
                "channel_source": platform,
                "yesterday_new_review_count": 0,
                "__source_table": table,
            }
            for platform in ("ctrip", "qunar", "tongcheng", "zhixing")
            if platform not in existing_platforms
        )
        for row in rows:
            row["__source_table"] = table
            row["snapshot_time"] = row.get("snapshot_time") or ""
        return rows, {
            "table": table,
            "rows": len(rows),
            "status": "ok",
            "where": "DATE(review_time)=DATE_SUB(CURDATE(), INTERVAL 1 DAY)",
            "hotel_id": hotel_id,
            "source_rule": "按review_time统计数据库昨日新增点评数",
        }
    except Exception as exc:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": str(exc),
            "where": "DATE(review_time)=DATE_SUB(CURDATE(), INTERVAL 1 DAY)",
        }


def load_mysql_dsn_dataset(
    dsn: str,
    limit: int = 5000,
    tables: dict[str, str] | None = None,
    hotel_id: str | None = "puyue",
    ctrip_hotel_id: str | None = None,
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

    if "ctrip" not in base._enabled_platforms(platform):
        dataset.setdefault("ctrip_joined_rights", [])
        dataset.setdefault("ctrip_promotion_status", [])
        dataset.setdefault("ctrip_userprofile_distribution", [])
        return dataset

    ctrip_id = ctrip_hotel_id or hotel_id
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            rights, rights_diag = _load_ctrip_configuration(
                cursor, table_map["ctrip_joined_rights"], limit, ctrip_id, "right_name"
            )
            statuses, statuses_diag = _load_ctrip_configuration(
                cursor, table_map["ctrip_promotion_status"], limit, ctrip_id, "activity_code"
            )
            profiles, profiles_diag = _load_user_profile(
                cursor, table_map["ctrip_userprofile_distribution"], limit, ctrip_id
            )
            review_overview, review_overview_diag = _load_ctrip_configuration(
                cursor, table_map["ctrip_review_overview"], limit, ctrip_id, "channel_source"
            )
            review_yesterday, review_yesterday_diag = _load_ctrip_yesterday_counts(
                cursor, table_map["ctrip_reviews"], ctrip_id
            )

    dataset["ctrip_joined_rights"] = base._tag_rows(rights, table_map["ctrip_joined_rights"])
    dataset["ctrip_promotion_status"] = base._tag_rows(statuses, table_map["ctrip_promotion_status"])
    dataset["ctrip_userprofile_distribution"] = base._tag_rows(profiles, table_map["ctrip_userprofile_distribution"])
    dataset["ctrip_review_overview"] = base._tag_rows(review_overview, table_map["ctrip_review_overview"])
    dataset["ctrip_review_yesterday"] = review_yesterday
    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        tables_diag = diagnostics.setdefault("tables", {})
        tables_diag["ctrip_joined_rights"] = rights_diag
        tables_diag["ctrip_promotion_status"] = statuses_diag
        tables_diag["ctrip_userprofile_distribution"] = profiles_diag
        tables_diag["ctrip_review_overview"] = review_overview_diag
        tables_diag["ctrip_review_yesterday"] = review_yesterday_diag
        diagnostics.setdefault("transformations", []).append(
            {
                "section": "ctrip_userprofile_distribution",
                "rows": len(profiles),
                "rule": (
                    "read ctrip_ota_userprofile_distribution on every report generation; "
                    "keep latest row per dimension_code and bucket"
                ),
            }
        )
        diagnostics["transformations"].extend(
            [
                {
                    "section": "ctrip_joined_rights",
                    "rows": len(rights),
                    "rule": f"hotel_id={ctrip_id}; keep the latest row per right_name",
                },
                {
                    "section": "ctrip_promotion_status",
                    "rows": len(statuses),
                    "rule": f"hotel_id={ctrip_id}; keep the latest row per activity_code",
                },
                {
                    "section": "ctrip_review_overview",
                    "rows": len(review_overview),
                    "rule": f"hotel_id={ctrip_id}; keep the latest row per channel_source",
                },
                {
                    "section": "ctrip_review_yesterday",
                    "rows": len(review_yesterday),
                    "rule": f"hotel_id={ctrip_id}; COUNT(*) where DATE(review_time)=database yesterday",
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
        ctrip_hotel_id=config.get("ctrip_hotel_id"),
        platform=config.get("platform") or "multi",
        period_start=config.get("period_start"),
        period_end=config.get("period_end"),
    )


__all__ = [
    "DEFAULT_MYSQL_TABLES",
    "latest_distribution_rows",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
