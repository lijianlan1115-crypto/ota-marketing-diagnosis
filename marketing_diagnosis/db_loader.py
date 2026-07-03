from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from marketing_diagnosis.data import SECTIONS


DEFAULT_MYSQL_TABLES = {
    "jy01": "jy01_hotel_statistics_daily",
    "rs01": "rs01_room_revenue_daily",
    "meituan_funnel": "meituan_ota_business_metrics",
    "ctrip_funnel": "ctrip_ota_business_metrics",
    "meituan_products": "meituan_ota_goods_price_mapping",
    "ctrip_products": "ctrip_ota_goods_price_mapping",
    "meituan_reviews": "meituan_ota_review_detail",
    "ctrip_reviews": "ctrip_ota_review_detail",
}


def _safe_identifier(value: str) -> str:
    if not value.replace("_", "").isalnum():
        raise ValueError(f"unsafe identifier: {value}")
    return f"`{value}`"


def _load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _sqlite_dataset(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    db_path = config.get("path")
    if not db_path:
        raise ValueError("SQLite config requires path")
    tables = config.get("tables") or {}
    limit = int(config.get("limit") or 5000)
    dataset: dict[str, list[dict[str, Any]]] = {}
    source_diagnostics = {"kind": "sqlite", "path": str(db_path), "tables": {}}
    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.row_factory = sqlite3.Row
        for section in SECTIONS:
            table = tables.get(section)
            if not table:
                continue
            rows = conn.execute(f"SELECT * FROM {_safe_identifier(str(table))} LIMIT ?", (limit,)).fetchall()
            dataset[section] = [dict(row) for row in rows]
            source_diagnostics["tables"][section] = {"table": table, "rows": len(rows), "status": "ok" if rows else "empty"}
    dataset["__source_diagnostics__"] = [source_diagnostics]
    return dataset


def _mysql_params(dsn: str) -> dict[str, Any]:
    parsed = urlparse(dsn)
    query = parse_qs(parsed.query)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "/").lstrip("/"),
        "charset": query.get("charset", ["utf8mb4"])[0],
    }


def _masked_dsn(dsn: str) -> str:
    parsed = urlparse(dsn)
    user = unquote(parsed.username or "")
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    database = (parsed.path or "/").lstrip("/")
    return f"mysql+pymysql://{user}:***@{host}:{port}/{database}"


def _connect_mysql(dsn: str):
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("MySQL support requires pymysql") from exc
    params = _mysql_params(str(dsn))
    return pymysql.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        database=params["database"],
        charset=params["charset"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=10,
        read_timeout=20,
        write_timeout=20,
    )


def _fetch(cursor, table: str, limit: int, where: str | None = None, params: list[Any] | None = None, order_by: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sql = f"SELECT * FROM {_safe_identifier(table)}"
    if where:
        sql += f" WHERE {where}"
    if order_by:
        sql += f" ORDER BY {order_by}"
    sql += " LIMIT %s"
    final_params = list(params or []) + [limit]
    try:
        cursor.execute(sql, final_params)
        rows = [dict(row) for row in cursor.fetchall()]
        fields = sorted({key for row in rows[:20] for key in row.keys()})
        return rows, {"table": table, "where": where, "rows": len(rows), "fields_sample": fields, "status": "ok" if rows else "empty"}
    except Exception as exc:
        return [], {"table": table, "where": where, "rows": 0, "fields_sample": [], "status": "error", "error": str(exc)}


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace(",", "").rstrip("%")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _ratio(value: Any) -> float | None:
    number = _float(value)
    if number is None:
        return None
    return number / 100 if number > 1 else number


def _rank(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _float(text.split("/")[0])


def _where(parts: list[str]) -> str | None:
    clean = [part for part in parts if part]
    return " AND ".join(clean) if clean else None


def _date_range(column: str, start: str | None, end: str | None, params: list[Any]) -> str | None:
    parts = []
    if start:
        parts.append(f"DATE({column}) >= %s")
        params.append(start)
    if end:
        parts.append(f"DATE({column}) <= %s")
        params.append(end)
    return " AND ".join(parts) if parts else None


def _hotel_filter(hotel_id: str | None, params: list[Any]) -> str | None:
    if not hotel_id:
        return None
    params.append(hotel_id)
    return "hotel_id = %s"


def _latest_snapshot(rows: list[dict[str, Any]], date_keys: tuple[str, ...] = ("business_date", "snapshot_time")) -> list[dict[str, Any]]:
    if not rows:
        return rows
    best = ""
    for row in rows:
        for key in date_keys:
            value = str(row.get(key) or "")[:19]
            if value > best:
                best = value
                break
    if not best:
        return rows
    return [row for row in rows if any(str(row.get(key) or "")[:19] == best for key in date_keys)]


def _pivot_funnel(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    metric_map = {
        "曝光量": "exposure",
        "曝光人数": "exposure",
        "浏览人数": "views",
        "浏览量": "views",
        "支付订单数": "paid_orders",
        "订单数": "paid_orders",
        "支付转化率": "payment_conversion_rate",
        "浏览-支付转化率": "payment_conversion_rate",
    }
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        period = str(row.get("stats_period_type") or row.get("period_type") or "")
        day = str(row.get("business_date") or row.get("snapshot_time") or "")[:10]
        item = grouped.setdefault((period, day), {"platform": platform, "business_date": day, "period_type": period, "source_table": row.get("__source_table")})
        target = metric_map.get(str(row.get("metric_name") or "").strip())
        if not target:
            continue
        if target == "payment_conversion_rate":
            item[target] = _ratio(row.get("metric_value"))
            peer = _ratio(row.get("peer_average"))
            if peer is not None:
                item["peer_avg_conversion_rate"] = peer
        else:
            item[target] = _float(row.get("metric_value"))
        rank = _rank(row.get("competitor_rank"))
        if rank is not None:
            item["peer_rank"] = rank
    return list(grouped.values())


def _rs01_daily(cursor, table: str, hotel_id: str | None = None, period_start: str | None = None, period_end: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params: list[Any] = []
    filters = ["charge_subject='房费'"]
    hotel = _hotel_filter(hotel_id, params)
    if hotel:
        filters.append(hotel)
    date = _date_range("business_date", period_start, period_end, params)
    if date:
        filters.append(date)
    where = _where(filters)
    sql = (
        f"SELECT DATE(business_date) AS business_date, SUM(room_nights) AS room_nights, "
        f"SUM(room_fee) AS room_revenue, 'rs01_room_revenue_daily' AS source_table "
        f"FROM {_safe_identifier(table)} WHERE {where} GROUP BY DATE(business_date) ORDER BY DATE(business_date) ASC"
    )
    try:
        cursor.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        return rows, {"table": table, "where": where, "rows": len(rows), "aggregation": "sum(room_nights), sum(room_fee) by business_date", "status": "ok" if rows else "empty"}
    except Exception as exc:
        return [], {"table": table, "where": where, "rows": 0, "aggregation": "sum by business_date", "status": "error", "error": str(exc)}


def _products(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        is_group = str(row.get("is_super_deal") or "").lower() in {"1", "true", "yes"}
        out.append({
            "platform": platform,
            "source_table": row.get("__source_table"),
            "business_date": str(row.get("business_date") or row.get("snapshot_time") or "")[:10],
            "room_type_name": row.get("room_type_name") or row.get("source_room_type_name"),
            "product_name": row.get("ota_product_name") or row.get("source_product_name"),
            "product_type": "group_buy" if is_group else row.get("rate_plan_name"),
            "listed_price": row.get("ota_sale_price") or row.get("current_sale_price"),
            "final_price": row.get("ota_sale_price") or row.get("current_sale_price"),
            "is_group_buy": is_group,
            "is_hour_room": row.get("is_hour_room"),
        })
    return out


def _reviews(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    return [{
        "platform": platform,
        "source_table": row.get("__source_table"),
        "review_date": str(row.get("review_time") or row.get("stay_date") or "")[:10],
        "rating": row.get("review_score"),
        "review_text": row.get("review_content"),
        "is_negative": row.get("is_negative_review"),
        "room_type_name": row.get("room_type_name"),
    } for row in rows]


def _tag_rows(rows: list[dict[str, Any]], table: str) -> list[dict[str, Any]]:
    for row in rows:
        row["__source_table"] = table
    return rows


def _enabled_platforms(platform: str | None) -> list[str]:
    value = str(platform or "multi").lower()
    if value in {"meituan", "美团"}:
        return ["meituan"]
    if value in {"ctrip", "携程"}:
        return ["ctrip"]
    return ["meituan", "ctrip"]


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
    dataset: dict[str, list[dict[str, Any]]] = {section: [] for section in SECTIONS}
    enabled = _enabled_platforms(platform)
    diagnostics: dict[str, Any] = {
        "kind": "mysql",
        "dsn": _masked_dsn(dsn),
        "profile": "puyue_mysql_reference",
        "hotel_id": hotel_id,
        "platform": platform,
        "period_start": period_start,
        "period_end": period_end,
        "tables": {},
        "transformations": [],
    }
    with _connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            params: list[Any] = []
            filters = ["dimension_type='总营业指标'", "dimension_name='总营业指标'"]
            hotel = _hotel_filter(hotel_id, params)
            if hotel:
                filters.append(hotel)
            date = _date_range("business_date", period_start, period_end, params)
            if date:
                filters.append(date)
            jy01, diag = _fetch(cursor, table_map["jy01"], limit, _where(filters), params, "business_date ASC")
            diagnostics["tables"]["jy01"] = diag
            if jy01:
                dataset["hotel_daily"].extend(_tag_rows(jy01, table_map["jy01"]))
                diagnostics["transformations"].append({"section": "hotel_daily", "source": table_map["jy01"], "rows": len(jy01), "rule": "total operating rows filtered by hotel_id and business_date"})
            else:
                rs01_rows, rs01_diag = _rs01_daily(cursor, table_map["rs01"], hotel_id, period_start, period_end)
                diagnostics["tables"]["rs01_fallback"] = rs01_diag
                dataset["hotel_daily"].extend(rs01_rows)
                diagnostics["transformations"].append({"section": "hotel_daily", "source": table_map["rs01"], "rows": len(rs01_rows), "rule": "fallback, charge_subject=房费 daily aggregation filtered by date"})

            if "meituan" in enabled:
                params = []
                filters = []
                hotel = _hotel_filter(hotel_id, params)
                if hotel:
                    filters.append(hotel)
                date = _date_range("business_date", period_start, period_end, params)
                if date:
                    filters.append(date)
                rows, diag = _fetch(cursor, table_map["meituan_funnel"], limit, _where(filters), params, "business_date ASC, metric_name ASC")
                diagnostics["tables"]["meituan_funnel"] = diag
                dataset["ota_funnel"].extend(_pivot_funnel(_tag_rows(rows, table_map["meituan_funnel"]), "meituan"))

                rows, diag = _fetch(cursor, table_map["meituan_products"], limit, _where(filters), params, "business_date DESC, snapshot_time DESC")
                diagnostics["tables"]["meituan_products"] = {**diag, "rows_used": len(_latest_snapshot(rows))}
                dataset["products"].extend(_products(_tag_rows(_latest_snapshot(rows), table_map["meituan_products"]), "meituan"))

                params_r = []
                filters_r = []
                hotel = _hotel_filter(hotel_id, params_r)
                if hotel:
                    filters_r.append(hotel)
                date = _date_range("review_time", period_start, period_end, params_r)
                if date:
                    filters_r.append(date)
                rows, diag = _fetch(cursor, table_map["meituan_reviews"], limit, _where(filters_r), params_r, "review_time DESC")
                diagnostics["tables"]["meituan_reviews"] = diag
                dataset["reviews"].extend(_reviews(_tag_rows(rows, table_map["meituan_reviews"]), "meituan"))

            if "ctrip" in enabled:
                params = []
                filters = []
                hotel = _hotel_filter(hotel_id, params)
                if hotel:
                    filters.append(hotel)
                date = _date_range("business_date", period_start, period_end, params)
                if date:
                    filters.append(date)
                rows, diag = _fetch(cursor, table_map["ctrip_funnel"], limit, _where(filters), params, "business_date ASC, metric_name ASC")
                diagnostics["tables"]["ctrip_funnel"] = diag
                dataset["ota_funnel"].extend(_pivot_funnel(_tag_rows(rows, table_map["ctrip_funnel"]), "ctrip"))

                rows, diag = _fetch(cursor, table_map["ctrip_products"], limit, _where(filters), params, "business_date DESC, snapshot_time DESC")
                diagnostics["tables"]["ctrip_products"] = {**diag, "rows_used": len(_latest_snapshot(rows))}
                dataset["products"].extend(_products(_tag_rows(_latest_snapshot(rows), table_map["ctrip_products"]), "ctrip"))

                params_r = []
                filters_r = []
                hotel = _hotel_filter(hotel_id, params_r)
                if hotel:
                    filters_r.append(hotel)
                # Some Ctrip review exports have stay_date but not review_time.
                date = _date_range("stay_date", period_start, period_end, params_r)
                if date:
                    filters_r.append(date)
                rows, diag = _fetch(cursor, table_map["ctrip_reviews"], limit, _where(filters_r), params_r, "stay_date DESC")
                diagnostics["tables"]["ctrip_reviews"] = diag
                dataset["reviews"].extend(_reviews(_tag_rows(rows, table_map["ctrip_reviews"]), "ctrip"))

            diagnostics["transformations"].append({"section": "ota_funnel", "source": [table_map.get(f"{p}_funnel") for p in enabled], "rows": len(dataset["ota_funnel"]), "rule": "pivot metric_name tall table filtered by platform and period"})
            diagnostics["transformations"].append({"section": "products", "source": [table_map.get(f"{p}_products") for p in enabled], "rows": len(dataset["products"]), "rule": "latest product snapshot within requested period"})
            diagnostics["transformations"].append({"section": "reviews", "source": [table_map.get(f"{p}_reviews") for p in enabled], "rows": len(dataset["reviews"]), "rule": "review detail filtered by requested period"})
    dataset["__source_diagnostics__"] = [diagnostics]
    return dataset


def _mysql_dataset(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    dsn = config.get("dsn") or os.environ.get(str(config.get("dsn_env") or ""))
    if not dsn:
        raise ValueError("MySQL config requires dsn or dsn_env")
    tables = config.get("tables") or {}
    limit = int(config.get("limit") or 5000)
    if config.get("profile") in {"puyue_mysql_reference", "puyue_mysql"} or not tables:
        return load_mysql_dsn_dataset(
            dsn,
            limit=limit,
            tables=tables,
            hotel_id=config.get("hotel_id") or "puyue",
            platform=config.get("platform") or "multi",
            period_start=config.get("period_start"),
            period_end=config.get("period_end"),
        )
    dataset: dict[str, list[dict[str, Any]]] = {}
    source_diagnostics = {"kind": "mysql", "dsn": _masked_dsn(dsn), "tables": {}}
    with _connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            for section in SECTIONS:
                table = tables.get(section)
                if not table:
                    continue
                rows, diag = _fetch(cursor, str(table), limit)
                dataset[section] = rows
                source_diagnostics["tables"][section] = diag
    dataset["__source_diagnostics__"] = [source_diagnostics]
    return dataset


def load_database_dataset(config_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    config = _load_json(config_path)
    kind = str(config.get("kind") or config.get("type") or "sqlite").lower()
    if kind == "sqlite":
        return _sqlite_dataset(config)
    if kind in {"mysql", "mysql+pymysql"}:
        return _mysql_dataset(config)
    raise ValueError(f"unsupported database kind: {kind}")
