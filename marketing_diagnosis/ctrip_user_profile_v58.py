from __future__ import annotations

from typing import Any


# dimension_code, page label, accepted aliases
DIMENSIONS = (
    ("gender", "性别", ()),
    ("age_group", "年龄段", ()),
    ("city_origin", "本地 / 异地", ()),
    ("travel_type", "出行目的", ()),
    ("travel_time", "工作日 / 周末偏好", ()),
    ("consumption_price", "消费价格带", ()),
    ("booking_advance_days", "提前预订天数", ()),
    ("stay_days", "平均入住晚数", ()),
    ("orider_peak_time", "主要预订时段", ("order_peak_time",)),
    ("city_origin_top5", "主要客源城市", ()),
)

_LABEL_KEYS = (
    "bucket_label",
    "bucket_name",
    "dimension_label",
    "item_label",
    "label",
    "name",
)
_VALUE_KEYS = (
    "bucket_value",
    "dimension_value",
    "metric_value",
    "display_value",
    "value",
    "avg_value",
)
_COUNT_KEYS = (
    "user_count",
    "people_count",
    "order_count",
    "sample_count",
    "count",
)
_RATIO_KEYS = (
    "bucket_ratio",
    "distribution_ratio",
    "user_ratio",
    "proportion",
    "percentage",
    "percent",
    "ratio",
    "rate",
    "value_pct",
)
_SKIP_FALLBACK_KEYS = {
    "id",
    "hotel_id",
    "hotel_name",
    "source_platform",
    "platform",
    "dimension_code",
    "dimension_name",
    "bucket_code",
    "bucket_label",
    "bucket_name",
    "dimension_label",
    "item_label",
    "label",
    "name",
    "snapshot_time",
    "created_at",
    "updated_at",
    "business_date",
    "data_date",
    "sort_order",
    "rank",
    "source_table",
    "__source_table",
}


def _first(row: dict[str, Any], keys: tuple[str, ...]) -> tuple[str | None, Any]:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return key, value
    return None, None


def _text(value: Any) -> str:
    if value in (None, ""):
        return ""
    return str(value).strip()


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip().replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None


def _format_number(value: Any) -> str:
    number = _number(value)
    if number is None:
        return _text(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def _format_ratio(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if "%" in text:
        return text
    number = _number(value)
    if number is None:
        return text
    percentage = number * 100 if abs(number) <= 1 else number
    return f"{percentage:.2f}%".replace(".00%", "%").replace(".0%", "%")


def _row_order(row: dict[str, Any], index: int) -> tuple[float, float, int]:
    sort_order = _number(row.get("sort_order"))
    rank = _number(row.get("rank") or row.get("ranking_position"))
    return (
        sort_order if sort_order is not None else 999999,
        rank if rank is not None else 999999,
        index,
    )


def _fallback_values(row: dict[str, Any], used: set[str]) -> list[str]:
    values: list[str] = []
    for key, value in row.items():
        if key in used or key in _SKIP_FALLBACK_KEYS or value in (None, ""):
            continue
        values.append(f"{key}={_text(value)}")
    return values[:3]


def row_text(row: dict[str, Any]) -> str:
    label_key, label_value = _first(row, _LABEL_KEYS)
    value_key, value = _first(row, _VALUE_KEYS)
    count_key, count = _first(row, _COUNT_KEYS)
    ratio_key, ratio = _first(row, _RATIO_KEYS)

    used = {key for key in (label_key, value_key, count_key, ratio_key) if key}
    details: list[str] = []
    if value not in (None, ""):
        details.append(_format_number(value))
    if count not in (None, "") and count_key != value_key:
        details.append(f"数量 {_format_number(count)}")
    if ratio not in (None, "") and ratio_key not in {value_key, count_key}:
        details.append(_format_ratio(ratio))
    if not details:
        details.extend(_fallback_values(row, used))

    label = _text(label_value)
    detail = " / ".join(value for value in details if value)
    if label and detail:
        return f"{label}：{detail}"
    return label or detail or "已采集（无可展示值）"


def _dimension_rows(rows: list[dict[str, Any]], code: str, aliases: tuple[str, ...]) -> list[dict[str, Any]]:
    accepted = {code, *aliases}
    selected = [row for row in rows if str(row.get("dimension_code") or "").strip() in accepted]
    if code == "stay_days":
        average = [
            row for row in selected
            if str(row.get("bucket_label") or "").strip() == "平均入住晚数"
        ]
        if average:
            selected = average
    return [row for _, row in sorted(enumerate(selected), key=lambda pair: _row_order(pair[1], pair[0]))]


def build_user_profile_item(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    clean_rows = [dict(row) for row in rows or [] if isinstance(row, dict)]
    fields: list[dict[str, Any]] = []
    connected = 0

    for code, label, aliases in DIMENSIONS:
        selected = _dimension_rows(clean_rows, code, aliases)
        if selected:
            connected += 1
        fields.append(
            {
                "label": label,
                "value": "；".join(row_text(row) for row in selected) if selected else None,
                "note": (
                    f"dimension_code={code}"
                    + ("，bucket_label=平均入住晚数" if code == "stay_days" else "")
                ),
                "dimension_code": code,
                "record_count": len(selected),
            }
        )

    return {
        "standard_item_id": 4,
        "item_name": "用户来源画像",
        "participates_in_score": False,
        "full_score": 0,
        "item_score": 0,
        "data_status": "success" if connected else "missing",
        "source": "ctrip_ota_userprofile_distribution",
        "fields": fields,
        "records": clean_rows,
        "connected_dimensions": connected,
        "expected_dimensions": len(DIMENSIONS),
    }


__all__ = ["DIMENSIONS", "build_user_profile_item", "row_text"]
