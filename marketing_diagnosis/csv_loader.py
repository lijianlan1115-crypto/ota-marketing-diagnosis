from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "gbk", "utf-8"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _read_csv_text(text: str) -> list[dict[str, Any]]:
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def _iter_csv_files(path: str | Path):
    root = Path(path)
    if root.is_file() and root.suffix.lower() == ".zip":
        with zipfile.ZipFile(root) as archive:
            for name in archive.namelist():
                if name.lower().endswith(".csv"):
                    yield Path(name).name, _read_csv_text(_decode(archive.read(name)))
        return
    if root.is_dir():
        for item in sorted(root.glob("*.csv")):
            yield item.name, _read_csv_text(_decode(item.read_bytes()))
        return
    raise FileNotFoundError(f"CSV export path not found: {root}")


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    percent = text.endswith("%")
    text = text.rstrip("%")
    try:
        number = float(text)
    except ValueError:
        return None
    return number / 100 if percent else number


def _rank(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    head = text.split("/")[0]
    return _float(head)


def _ratio_metric(value: Any) -> float | None:
    number = _float(value)
    if number is None:
        return None
    return number / 100 if number > 1 else number


def _pivot_business_metrics(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    metric_map = {
        "曝光量": "exposure",
        "曝光人数": "exposure",
        "浏览人数": "views",
        "支付订单数": "paid_orders",
        "支付转化率": "payment_conversion_rate",
        "浏览-支付转化率": "payment_conversion_rate",
    }
    for row in rows:
        key = (str(row.get("stats_period_type") or ""), str(row.get("business_date") or "")[:10])
        item = grouped.setdefault(key, {"platform": platform, "business_date": key[1], "period_type": key[0]})
        name = str(row.get("metric_name") or "").strip()
        target = metric_map.get(name)
        if not target:
            continue
        if target == "payment_conversion_rate":
            item[target] = _ratio_metric(row.get("metric_value"))
            peer = _ratio_metric(row.get("peer_average"))
            if peer is not None:
                item["peer_avg_conversion_rate"] = peer
        else:
            item[target] = _float(row.get("metric_value"))
        rank = _rank(row.get("competitor_rank"))
        if rank is not None:
            item["peer_rank"] = rank
    return list(grouped.values())


def _total_daily(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if row.get("dimension_type") == "总营业指标" and row.get("dimension_name") == "总营业指标":
            out.append(row)
    return out or rows


def _rs01_daily(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, float]] = defaultdict(lambda: {"room_nights": 0.0, "room_revenue": 0.0})
    for row in rows:
        if str(row.get("charge_subject") or "") != "房费":
            continue
        day = str(row.get("business_date") or "")[:10]
        if not day:
            continue
        grouped[day]["room_nights"] += _float(row.get("room_nights")) or 0
        grouped[day]["room_revenue"] += _float(row.get("room_fee")) or 0
    return [{"business_date": day, "room_nights": values["room_nights"], "room_revenue": values["room_revenue"], "source_table": "rs01_room_revenue_daily"} for day, values in sorted(grouped.items())]


def _products(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        out.append({
            "platform": platform,
            "room_type_name": row.get("room_type_name"),
            "product_name": row.get("ota_product_name") or row.get("source_product_name"),
            "product_type": "group_buy" if str(row.get("is_super_deal") or "").lower() in {"1", "true", "yes"} else row.get("rate_plan_name"),
            "listed_price": row.get("ota_sale_price") or row.get("current_sale_price"),
            "final_price": row.get("ota_sale_price") or row.get("current_sale_price"),
            "is_group_buy": str(row.get("is_super_deal") or "").lower() in {"1", "true", "yes"},
            "is_hour_room": row.get("is_hour_room"),
        })
    return out


def _reviews(rows: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        out.append({
            "platform": platform,
            "review_date": str(row.get("review_time") or row.get("stay_date") or "")[:10],
            "rating": row.get("review_score"),
            "review_text": row.get("review_content"),
            "is_negative": row.get("is_negative_review"),
            "room_type_name": row.get("room_type_name"),
        })
    return out


def load_csv_export_dataset(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    dataset: dict[str, list[dict[str, Any]]] = {"hotel_daily": [], "ota_funnel": [], "products": [], "reviews": [], "competitors": []}
    rs01_rows: list[dict[str, Any]] = []
    has_jy01 = False
    for name, rows in _iter_csv_files(path):
        if not rows:
            continue
        lower = name.lower()
        if "jy01_hotel_statistics_daily" in lower:
            dataset["hotel_daily"].extend(_total_daily(rows))
            has_jy01 = True
        elif "rs01_room_revenue_daily" in lower:
            rs01_rows.extend(rows)
        elif "meituan_ota_business_metrics" in lower:
            dataset["ota_funnel"].extend(_pivot_business_metrics(rows, "meituan"))
        elif "ctrip_ota_business_metrics" in lower:
            dataset["ota_funnel"].extend(_pivot_business_metrics(rows, "ctrip"))
        elif "meituan_ota_goods_price_mapping" in lower:
            dataset["products"].extend(_products(rows, "meituan"))
        elif "ctrip_ota_goods_price_mapping" in lower:
            dataset["products"].extend(_products(rows, "ctrip"))
        elif "meituan_ota_review_detail" in lower:
            dataset["reviews"].extend(_reviews(rows, "meituan"))
        elif "ctrip_ota_review_detail" in lower:
            dataset["reviews"].extend(_reviews(rows, "ctrip"))
    if not has_jy01 and rs01_rows:
        dataset["hotel_daily"].extend(_rs01_daily(rs01_rows))
    return dataset
