from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from marketing_diagnosis.data import SECTIONS


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


def _mysql_dataset(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("MySQL support requires pymysql") from exc
    dsn = config.get("dsn")
    if not dsn:
        raise ValueError("MySQL config requires dsn")
    tables = config.get("tables") or {}
    limit = int(config.get("limit") or 5000)
    params = _mysql_params(str(dsn))
    dataset: dict[str, list[dict[str, Any]]] = {}
    with pymysql.connect(
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
    ) as conn:
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
