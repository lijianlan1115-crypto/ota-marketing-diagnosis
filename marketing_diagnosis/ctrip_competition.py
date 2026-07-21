from __future__ import annotations

import os
from typing import Any

from marketing_diagnosis import db_loader as base
from marketing_diagnosis import db_loader_v16 as upstream


DEFAULT_MYSQL_TABLES = {
    **upstream.DEFAULT_MYSQL_TABLES,
    "ctrip_competition_metrics_30d": "ctrip_ota_competition_metrics_30d",
    "ctrip_order_loss_monthly": "ctrip_ota_order_loss_monthly",
}

_ORDER_COLUMNS = (
    "snapshot_time",
    "updated_at",
    "created_at",
    "business_date",
    "data_date",
    "period_month",
    "stat_month",
    "id",
)


def _diagnostics(dataset: dict[str, Any]) -> dict[str, Any] | None:
    records = dataset.get("__source_diagnostics__") or []
    return records[0] if records and isinstance(records[0], dict) else None


def _text(value: Any) -> str:
    return "" if value in (None, "") else str(value).strip()


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).strip().replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _order_key(row: dict[str, Any], index: int) -> tuple[str, ...]:
    values = [str(row.get(column) or "") for column in _ORDER_COLUMNS[:-1]]
    try:
        row_id = int(row.get("id") or 0)
    except (TypeError, ValueError):
        row_id = 0
    values.extend((f"{row_id:020d}", f"{index:020d}"))
    return tuple(values)


def _latest_by_metric(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[tuple[str, str], tuple[tuple[str, ...], dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        key = (
            _text(row.get("metric_code")),
            _text(row.get("metric_name") or row.get("metric_label")),
        )
        if not any(key):
            key = ("row", str(index))
        order = _order_key(row, index)
        current = selected.get(key)
        if current is None or order >= current[0]:
            selected[key] = (order, dict(row))
    return [value[1] for value in selected.values()]


def _load_competition_metrics(
    cursor,
    table: str,
    limit: int,
    hotel_id: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    columns, schema_error = base._table_columns(cursor, table)
    if schema_error:
        return [], {"table": table, "rows": 0, "status": "error", "error": schema_error}
    if not ({"metric_code", "metric_name"} & columns):
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "required column missing: metric_code or metric_name",
            "table_columns": sorted(columns),
        }
    order_candidates = tuple(
        [f"{name} DESC" for name in _ORDER_COLUMNS if name in columns]
        + [value for value in ("metric_code ASC", "metric_name ASC") if value.rsplit(" ", 1)[0] in columns]
    )
    rows, diag = base._profiled_fetch(
        cursor,
        table,
        max(limit, 10000),
        hotel_id=hotel_id,
        order_candidates=order_candidates,
    )
    latest = _latest_by_metric(rows)
    return latest, {
        **diag,
        "rows_read": len(rows),
        "rows_used": len(latest),
        "selection_rule": "latest row per metric_code + metric_name",
    }


def _load_yesterday_loss_metrics(
    cursor,
    table: str,
    hotel_id: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    columns, schema_error = base._table_columns(cursor, table)
    if schema_error:
        return [], {"table": table, "rows": 0, "status": "error", "error": schema_error}
    required = {"business_date", "metric_group", "metric_name"}
    missing = required - columns
    if missing:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "required columns missing: " + ", ".join(sorted(missing)),
            "table_columns": sorted(columns),
        }

    filters = [
        "DATE(`business_date`) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)",
        "`metric_group` = %s",
        "`metric_name` IN (%s, %s)",
    ]
    params: list[Any] = ["流失诊断", "流失订单量", "流失订单金额"]
    if hotel_id and "hotel_id" in columns:
        filters.insert(0, "`hotel_id` = %s")
        params.insert(0, hotel_id)
    sql = (
        f"SELECT * FROM {base._safe_identifier(table)} "
        f"WHERE {base._where(filters)} ORDER BY `business_date` DESC, `metric_name` ASC"
    )
    try:
        cursor.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        return rows, {
            "table": table,
            "rows": len(rows),
            "status": "ok" if rows else "empty",
            "where": "database yesterday + metric_group=流失诊断 + two loss metrics",
            "hotel_filter_applied": bool(hotel_id and "hotel_id" in columns),
        }
    except Exception as exc:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": str(exc),
            "where": "database yesterday + loss metrics",
        }


def _load_order_loss(
    cursor,
    table: str,
    limit: int,
    hotel_id: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    columns, schema_error = base._table_columns(cursor, table)
    if schema_error:
        return [], {"table": table, "rows": 0, "status": "error", "error": schema_error}
    required = {"platform_scope", "competitor_hotel_name"}
    missing = required - columns
    if missing:
        return [], {
            "table": table,
            "rows": 0,
            "status": "error",
            "error": "required columns missing: " + ", ".join(sorted(missing)),
            "table_columns": sorted(columns),
        }
    order_candidates = tuple(
        [f"{name} DESC" for name in _ORDER_COLUMNS if name in columns]
        + [value for value in ("platform_scope ASC", "ranking_position ASC") if value.rsplit(" ", 1)[0] in columns]
    )
    rows, diag = base._profiled_fetch(
        cursor,
        table,
        max(limit, 10000),
        hotel_id=hotel_id,
        order_candidates=order_candidates,
    )
    rows = [row for row in rows if _text(row.get("platform_scope")).lower() in {"ctrip", "qunar"}]
    return rows, {
        **diag,
        "rows_used": len(rows),
        "row_filter": "platform_scope in (ctrip, qunar)",
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
    dataset = upstream.load_mysql_dsn_dataset(
        dsn,
        limit=limit,
        tables=table_map,
        hotel_id=hotel_id,
        ctrip_hotel_id=ctrip_hotel_id,
        platform=platform,
        period_start=period_start,
        period_end=period_end,
    )

    if "ctrip" not in base._enabled_platforms(platform):
        dataset.setdefault("ctrip_competition_metrics_30d", [])
        dataset.setdefault("ctrip_business_metrics_loss", [])
        dataset.setdefault("ctrip_order_loss_monthly", [])
        return dataset

    ctrip_id = ctrip_hotel_id or hotel_id
    with base._connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            competition, competition_diag = _load_competition_metrics(
                cursor,
                table_map["ctrip_competition_metrics_30d"],
                limit,
                ctrip_id,
            )
            loss_metrics, loss_metrics_diag = _load_yesterday_loss_metrics(
                cursor,
                table_map["ctrip_funnel"],
                ctrip_id,
            )
            loss_competitors, loss_competitors_diag = _load_order_loss(
                cursor,
                table_map["ctrip_order_loss_monthly"],
                limit,
                ctrip_id,
            )

    dataset["ctrip_competition_metrics_30d"] = base._tag_rows(
        competition,
        table_map["ctrip_competition_metrics_30d"],
    )
    dataset["ctrip_business_metrics_loss"] = base._tag_rows(
        loss_metrics,
        table_map["ctrip_funnel"],
    )
    dataset["ctrip_order_loss_monthly"] = base._tag_rows(
        loss_competitors,
        table_map["ctrip_order_loss_monthly"],
    )

    diagnostics = _diagnostics(dataset)
    if diagnostics is not None:
        diagnostics.setdefault("tables", {}).update(
            {
                "ctrip_competition_metrics_30d": competition_diag,
                "ctrip_business_metrics_loss": loss_metrics_diag,
                "ctrip_order_loss_monthly": loss_competitors_diag,
            }
        )
        diagnostics.setdefault("transformations", []).extend(
            [
                {
                    "section": "ctrip_competition_metrics_30d",
                    "rows": len(competition),
                    "rule": "latest row per metric_code + metric_name",
                },
                {
                    "section": "ctrip_business_metrics_loss",
                    "rows": len(loss_metrics),
                    "rule": "database yesterday; metric_group=流失诊断",
                },
                {
                    "section": "ctrip_order_loss_monthly",
                    "rows": len(loss_competitors),
                    "rule": "ctrip/qunar rows retained; renderer selects latest Top5",
                },
            ]
        )
    return dataset


def load_database_dataset(config_path):
    config = base._load_json(config_path)
    kind = str(config.get("kind") or config.get("type") or "sqlite").lower()
    if kind not in {"mysql", "mysql+pymysql"}:
        return upstream.load_database_dataset(config_path)
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


def _metric_label(row: dict[str, Any]) -> str:
    name = _text(row.get("metric_name") or row.get("metric_label"))
    code = _text(row.get("metric_code"))
    combined = f"{name} {code}".lower()
    if "订单" in name or "booking_order" in combined:
        return "订单量"
    if "销售额" in name or "销售金额" in name or any(key in combined for key in ("sales_amount", "sale_amount", "sales_revenue", "revenue", "gmv")):
        return "销售额"
    if "出租率" in name or "occupancy" in combined:
        return "出租率"
    if "转化" in name or "conversion" in combined:
        return "转化率"
    return name or code or "竞争圈指标"


def _metric_unit(row: dict[str, Any], label: str) -> str:
    explicit = _text(row.get("metric_unit") or row.get("unit"))
    if explicit:
        return explicit
    if "率" in label:
        return "%"
    if "销售" in label or "金额" in label:
        return "元"
    if "订单" in label:
        return "单"
    return ""


def _competition_entries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {"订单量": 0, "销售额": 1, "出租率": 2, "转化率": 3}
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        label = _metric_label(row)
        code = _text(row.get("metric_code"))
        key = (label, code)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "label": label,
                "metric_code": code,
                "hotel_value": _number(_first(row, "metric_value", "hotel_value", "current_value", "my_value")),
                "competitor_avg": _number(_first(row, "competitor_avg", "competitor_average", "peer_average", "avg_value")),
                "competitor_rank": _number(_first(row, "competitor_rank", "ranking_position", "rank_position", "rank")),
                "competitor_count": _number(_first(row, "competitor_count", "circle_hotel_count", "peer_hotel_count")),
                "unit": _metric_unit(row, label),
            }
        )
    entries.sort(key=lambda entry: (priority.get(str(entry.get("label")), 99), str(entry.get("label"))))
    return entries


def _latest_funnel(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    ctrip_rows = [row for row in rows if _text(row.get("platform")).lower() == "ctrip"]
    if not ctrip_rows:
        return None
    ctrip_rows.sort(
        key=lambda row: (
            _text(row.get("business_date")),
            "30" in _text(row.get("period_type")),
        ),
        reverse=True,
    )
    return dict(ctrip_rows[0])


def _funnel_stages(rows: list[dict[str, Any]], existing: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    existing_stages = (existing or {}).get("funnel_stages")
    if isinstance(existing_stages, list) and existing_stages:
        return [dict(stage) for stage in existing_stages if isinstance(stage, dict)]
    row = _latest_funnel(rows)
    if not row:
        return []
    definitions = (
        ("列表页曝光量", ("exposure", "list_exposure", "list_page_exposure"), ("peer_exposure", "competitor_exposure")),
        ("详情页访客量", ("views", "detail_visitors", "detail_page_visitors"), ("peer_views", "competitor_views")),
        ("订单页访客量", ("order_page_visitors", "order_visitors"), ("peer_order_page_visitors", "competitor_order_page_visitors")),
        ("订单提交人数", ("submitted_orders", "order_submit_users", "submit_order_count"), ("peer_submitted_orders", "competitor_submitted_orders")),
        ("成交订单数", ("paid_orders", "booking_order_count", "completed_orders"), ("peer_paid_orders", "competitor_paid_orders")),
    )
    stages: list[dict[str, Any]] = []
    for label, hotel_keys, peer_keys in definitions:
        hotel_value = _number(_first(row, *hotel_keys))
        peer_value = _number(_first(row, *peer_keys))
        if hotel_value is None and peer_value is None:
            continue
        stages.append({"label": label, "hotel_value": hotel_value, "competitor_avg": peer_value})
    return stages


def _loss_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"order_count": None, "order_amount": None, "business_date": None}
    for row in rows:
        name = _text(row.get("metric_name"))
        value = _number(_first(row, "metric_value", "value", "current_value"))
        if name == "流失订单量":
            result["order_count"] = value
        elif name == "流失订单金额":
            result["order_amount"] = value
        day = _text(row.get("business_date"))[:10]
        if day:
            result["business_date"] = max(_text(result.get("business_date")), day)
    return result


def _platform(value: Any) -> str:
    text = _text(value).lower()
    aliases = {"携程": "ctrip", "去哪儿": "qunar", "去哪兒": "qunar"}
    return aliases.get(_text(value), text)


def _period_key(row: dict[str, Any]) -> str:
    return _text(
        _first(
            row,
            "period_month",
            "business_month",
            "stat_month",
            "data_month",
            "business_date",
            "snapshot_time",
            "updated_at",
            "created_at",
        )
    )[:19]


def _loss_competitors(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {"ctrip": [], "qunar": []}
    for platform in output:
        platform_rows = [row for row in rows if _platform(row.get("platform_scope")) == platform]
        if not platform_rows:
            continue
        periods = [_period_key(row) for row in platform_rows if _period_key(row)]
        latest = max(periods) if periods else ""
        if latest:
            platform_rows = [row for row in platform_rows if _period_key(row) == latest]
        normalized: list[dict[str, Any]] = []
        for row in platform_rows:
            name = _text(row.get("competitor_hotel_name"))
            if not name:
                continue
            rank = _number(_first(row, "ranking_position", "rank_position", "competitor_rank", "rank"))
            normalized.append(
                {
                    "ranking_position": rank,
                    "competitor_hotel_name": name,
                    "loss_order_count": _number(_first(row, "loss_order_count", "order_count", "lost_order_count")),
                    "loss_order_amount": _number(_first(row, "loss_order_amount", "loss_amount", "order_amount")),
                    "period": latest,
                }
            )
        normalized.sort(key=lambda row: (row.get("ranking_position") if row.get("ranking_position") is not None else 999999, row.get("competitor_hotel_name")))
        output[platform] = normalized[:5]
    return output


def build_competition_item(
    sections: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    competition_rows = [dict(row) for row in sections.get("ctrip_competition_metrics_30d") or [] if isinstance(row, dict)]
    loss_rows = [dict(row) for row in sections.get("ctrip_business_metrics_loss") or [] if isinstance(row, dict)]
    competitor_rows = [dict(row) for row in sections.get("ctrip_order_loss_monthly") or [] if isinstance(row, dict)]
    funnel_rows = [dict(row) for row in sections.get("ota_funnel") or [] if isinstance(row, dict)]

    competition_metrics = _competition_entries(competition_rows)
    loss_summary = _loss_summary(loss_rows)
    loss_competitors = _loss_competitors(competitor_rows)
    funnel_stages = _funnel_stages(funnel_rows, existing)
    has_data = bool(
        competition_metrics
        or funnel_stages
        or loss_summary.get("order_count") is not None
        or loss_summary.get("order_amount") is not None
        or loss_competitors["ctrip"]
        or loss_competitors["qunar"]
    )

    fields = [
        {
            "label": entry.get("label"),
            "value": entry.get("competitor_avg"),
            "note": "竞争圈平均 / 排名",
        }
        for entry in competition_metrics
    ]
    item = {
        "standard_item_id": 3,
        "item_name": "平台流量漏斗分析",
        "participates_in_score": True,
        "full_score": 15,
        "data_status": "success" if has_data else "missing",
        "source": "ctrip_ota_competition_metrics_30d、ctrip_ota_business_metrics、ctrip_ota_order_loss_monthly",
        "source_path": "携程 eBooking -> 数据中心 -> 竞争圈动态",
        "fields": fields,
        "fields_complete": True,
        "funnel_stages": funnel_stages,
        "competition_metrics": competition_metrics,
        "loss_summary": loss_summary,
        "loss_competitors": loss_competitors,
        "records": competition_rows + loss_rows + competitor_rows,
    }
    for key in ("item_score", "diagnosis_score", "score", "current_score"):
        if isinstance(existing, dict) and existing.get(key) not in (None, ""):
            item[key] = existing[key]
            break
    return item


__all__ = [
    "DEFAULT_MYSQL_TABLES",
    "build_competition_item",
    "load_database_dataset",
    "load_mysql_dsn_dataset",
]
