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
    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.row_factory = sqlite3.Row
        for section in SECTIONS:
            table = tables.get(section)
            if not table:
                continue
            rows = conn.execute(f"SELECT * FROM {_safe_identifier(str(table))} LIMIT ?", (limit,)).fetchall()
            dataset[section] = [dict(row) for row in rows]
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


def _fetch(cursor, table: str, limit: int, where: str | None = None) -> list[dict[str, Any]]:
    sql = f"SELECT * FROM {_safe_identifier(table)}"
    if where:
        sql += f" WHERE {where}"
    sql += " LIMIT %s"
    try:
        cursor.execute(sql, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []


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


def _pivot_funnel(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    metric_map = {
        "曝光量": "exposure",
        "曝光人数": "exposure",
        "浏览人数": "views",
        "支付订单数": "paid_orders",
        "支付转化率": "payment_conversion_rate",
        "浏览-支付转化率": "payment_conversion_rate",
    }
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        period = str(row.get("stats_period_type") or "")
        day = str(row.get("business_date") or "")[:10]
        item = grouped.setdefault((period, day), {"platform": platform, "business_date": day, "period_type": period})
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


def _rs01_daily(cursor, table: str) -> list[dict[str, Any]]:
    sql = (
        f"SELECT DATE(business_date) AS business_date, SUM(room_nights) AS room_nights, "
        f"SUM(room_fee) AS room_revenue, 'rs01_room_revenue_daily' AS source_table "
        f"FROM {_safe_identifier(table)} WHERE charge_subject='房费' GROUP BY DATE(business_date)"
    )
    try:
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []


def _products(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        is_group = str(row.get("is_super_deal") or "").lower() in {"1", "true", "yes"}
        out.append({
            "platform": platform,
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
        "review_date": str(row.get("review_time") or row.get("stay_date") or "")[:10],
        "rating": row.get("review_score"),
        "review_text": row.get("review_content"),
        "is_negative": row.get("is_negative_review"),
        "room_type_name": row.get("room_type_name"),
    } for row in rows]


def load_mysql_dsn_dataset(dsn: str, limit: int = 5000, tables: dict[str, str] | None = None) -> dict[str, list[dict[str, Any]]]:
    table_map = {**DEFAULT_MYSQL_TABLES, **(tables or {})}
    dataset: dict[str, list[dict[str, Any]]] = {section: [] for section in SECTIONS}
    with _connect_mysql(dsn) as conn:
        with conn.cursor() as cursor:
            jy01 = _fetch(cursor, table_map["jy01"], limit, "dimension_type='总营业指标' AND dimension_name='总营业指标'")
            if jy01:
                dataset["hotel_daily"].extend(jy01)
            else:
                dataset["hotel_daily"].extend(_rs01_daily(cursor, table_map["rs01"]))
            dataset["ota_funnel"].extend(_pivot_funnel(_fetch(cursor, table_map["meituan_funnel"], limit), "meituan"))
            dataset["ota_funnel"].extend(_pivot_funnel(_fetch(cursor, table_map["ctrip_funnel"], limit), "ctrip"))
            dataset["products"].extend(_products(_fetch(cursor, table_map["meituan_products"], limit), "meituan"))
            dataset["products"].extend(_products(_fetch(cursor, table_map["ctrip_products"], limit), "ctrip"))
            dataset["reviews"].extend(_reviews(_fetch(cursor, table_map["meituan_reviews"], limit), "meituan"))
            dataset["reviews"].extend(_reviews(_fetch(cursor, table_map["ctrip_reviews"], limit), "ctrip"))
    return dataset


def _mysql_dataset(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    dsn = config.get("dsn") or os.environ.get(str(config.get("dsn_env") or ""))
    if not dsn:
        raise ValueError("MySQL config requires dsn or dsn_env")
    tables = config.get("tables") or {}
    limit = int(config.get("limit") or 5000)
    if config.get("profile") in {"puyue_mysql_reference", "puyue_mysql"} or not tables:
        return load_mysql_dsn_dataset(str(dsn), limit=limit, tables=tables)
    dataset: dict[str, list[dict[str, Any]]] = {}
    with _connect_mysql(str(dsn)) as conn:
        with conn.cursor() as cursor:
            for section in SECTIONS:
                table = tables.get(section)
                if not table:
                    continue
                cursor.execute(f"SELECT * FROM {_safe_identifier(str(table))} LIMIT %s", (limit,))
                dataset[section] = [dict(row) for row in cursor.fetchall()]
    return dataset


def load_database_dataset(config_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    config = _load_json(config_path)
    kind = str(config.get("kind") or "sqlite").lower()
    if kind == "sqlite":
        return _sqlite_dataset(config)
    if kind in {"mysql", "mysql+pymysql"}:
        return _mysql_dataset(config)
    raise ValueError(f"Unsupported database kind: {kind}")
