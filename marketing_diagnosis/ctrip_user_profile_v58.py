from __future__ import annotations

from typing import Any


# canonical code, page label, accepted aliases
DIMENSIONS = (
    ("gender", "性别", ()),
    ("age_group", "年龄段", ()),
    ("city_origin", "本地 / 异地", ()),
    ("travel_type", "出行目的", ()),
    ("travel_time", "工作日 / 周末偏好", ()),
    ("consumption_price", "消费价格带", ()),
    ("booking_advance_days", "提前预订天数", ()),
    ("stay_days", "平均入住晚数", ()),
    (
        "orider_peak_time",
        "主要预订时段",
        ("order_peak_time", "order_hourly_distribution"),
    ),
    ("city_origin_top5", "主要客源城市", ()),
)

CHART_DIMENSIONS = (
    ("gender", "性别"),
    ("age_group", "年龄段"),
    ("city_origin", "本地 / 异地"),
    ("travel_type", "出行目的"),
    ("travel_time", "工作日 / 周末偏好"),
    ("consumption_price", "消费价格带"),
    ("booking_advance_days", "提前预订天数"),
    ("stay_days", "入住晚数"),
)

_RATIO_KEYS = (
    "rate_pct",
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
_VALUE_KEYS = (
    "metric_value",
    "bucket_value",
    "dimension_value",
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

_LABEL_MAP = {
    "age_group": {
        "<25": "25岁以下",
        "25-34": "25–34岁",
        "35-44": "35–44岁",
        "45-54": "45–54岁",
        ">=55": "55岁及以上",
    },
    "consumption_price": {
        "<=200": "200元及以下",
        "201-500": "201–500元",
        "501-1000": "501–1000元",
        "1001-2000": "1001–2000元",
        ">2000": "2000元以上",
    },
    "stay_days": {
        "1天": "1晚",
        "2天": "2晚",
        "3-5天": "3–5晚",
        "6天以上": "6晚以上",
    },
}


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


def _first_value(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _dimension_code(row: dict[str, Any]) -> str:
    return _text(row.get("dimension_code"))


def _bucket_label(row: dict[str, Any]) -> str:
    for key in (
        "bucket_label",
        "bucket_name",
        "dimension_label",
        "item_label",
        "label",
        "name",
    ):
        value = _text(row.get(key))
        if value:
            return value
    return ""


def _display_label(code: str, label: str) -> str:
    return _LABEL_MAP.get(code, {}).get(label, label)


def _metric_value(row: dict[str, Any]) -> float | None:
    return _number(_first_value(row, _VALUE_KEYS))


def _rate_pct(row: dict[str, Any]) -> float | None:
    for key in _RATIO_KEYS:
        value = row.get(key)
        if value in (None, ""):
            continue
        number = _number(value)
        if number is None:
            continue

        # Explicit percentage fields already use a 0–100 scale. Therefore
        # rate_pct=0.14 means 0.14%, not 14%.
        if key in {"rate_pct", "percentage", "percent", "value_pct"}:
            return number
        return number * 100 if abs(number) <= 1 else number

    # Compatibility with older fixtures where bucket_value stored a ratio.
    fallback = _number(row.get("bucket_value"))
    if fallback is not None and 0 <= fallback <= 1 and not _text(row.get("metric_unit")):
        return fallback * 100
    return None


def _rank(row: dict[str, Any]) -> float:
    value = _number(
        row.get("rank_position")
        or row.get("ranking_position")
        or row.get("rank")
        or row.get("sort_order")
    )
    return value if value is not None else 999999.0


def _entry(row: dict[str, Any], code: str) -> dict[str, Any]:
    return {
        "label": _display_label(code, _bucket_label(row)),
        "rate_pct": _rate_pct(row),
        "metric_value": _metric_value(row),
        "metric_unit": _text(row.get("metric_unit")),
        "rank_position": _rank(row),
        "count": _number(_first_value(row, _COUNT_KEYS)),
        "dimension_code": _dimension_code(row),
    }


def _rows_for(rows: list[dict[str, Any]], codes: set[str]) -> list[dict[str, Any]]:
    return [row for row in rows if _dimension_code(row) in codes]


def _is_average_row(code: str, row: dict[str, Any]) -> bool:
    label = _bucket_label(row)
    if code == "stay_days":
        return label in {"平均入住晚数", "avg_stay_days", "average_stay_days"}
    if code == "booking_advance_days":
        return label in {
            "avg_advance_booking_days",
            "平均提前预订天数",
            "平均提前预订天数（天）",
        }
    return False


def _distribution_entries(rows: list[dict[str, Any]], code: str) -> list[dict[str, Any]]:
    entries = [
        _entry(row, code)
        for row in _rows_for(rows, {code})
        if not _is_average_row(code, row)
    ]
    # Hide true 0% categories while preserving every positive category,
    # including tiny values such as 0.14%.
    entries = [entry for entry in entries if (entry.get("rate_pct") or 0) > 0]
    entries.sort(
        key=lambda entry: (
            -(entry.get("rate_pct") or 0),
            entry.get("rank_position", 999999),
        )
    )
    return entries


def _average_metric(rows: list[dict[str, Any]], code: str) -> float | None:
    for row in _rows_for(rows, {code}):
        if _is_average_row(code, row):
            value = _metric_value(row)
            if value is not None:
                return value
    return None


def _city_entries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries = [
        _entry(row, "city_origin_top5")
        for row in _rows_for(rows, {"city_origin_top5"})
    ]
    entries = [
        entry
        for entry in entries
        if (entry.get("rate_pct") or 0) > 0 or (entry.get("count") or 0) > 0
    ]
    entries.sort(
        key=lambda entry: (
            entry.get("rank_position", 999999),
            -(entry.get("rate_pct") or 0),
        )
    )
    return entries[:5]


def _peak_entry(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = _rows_for(rows, {"orider_peak_time", "order_peak_time"})
    entries = [_entry(row, "orider_peak_time") for row in candidates]
    entries = [
        entry
        for entry in entries
        if entry.get("label") or entry.get("rate_pct") is not None
    ]
    if not entries:
        return None
    entries.sort(
        key=lambda entry: (
            -(entry.get("rate_pct") or 0),
            entry.get("rank_position", 999999),
        )
    )
    return entries[0]


def _hour_value(label: str) -> float:
    text = label.strip()
    try:
        hour, minute = text.split(":", 1)
        return float(hour) + float(minute) / 60
    except (ValueError, TypeError):
        number = _number(text)
        return number if number is not None else 999999.0


def _hourly_entries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries = [
        _entry(row, "order_hourly_distribution")
        for row in _rows_for(rows, {"order_hourly_distribution"})
    ]
    entries = [
        entry
        for entry in entries
        if entry.get("label") and (entry.get("rate_pct") or 0) > 0
    ]
    entries.sort(key=lambda entry: _hour_value(str(entry.get("label") or "")))
    return entries


def _format_pct(value: Any) -> str:
    number = _number(value)
    return "" if number is None else f"{number:.2f}%"


def _field_value(entries: list[dict[str, Any]]) -> str | None:
    values: list[str] = []
    for entry in entries:
        label = _text(entry.get("label"))
        percentage = _format_pct(entry.get("rate_pct"))
        count = entry.get("count")
        if label and percentage:
            values.append(f"{label}：{percentage}")
        elif label and count is not None:
            values.append(f"{label}：{count:g}")
        elif label:
            values.append(label)
    return "；".join(values) or None


def row_text(row: dict[str, Any]) -> str:
    code = _dimension_code(row)
    entry = _entry(row, code)
    label = _text(entry.get("label"))
    percentage = _format_pct(entry.get("rate_pct"))
    metric = entry.get("metric_value")
    unit = _text(entry.get("metric_unit"))
    count = entry.get("count")

    details: list[str] = []
    if percentage:
        details.append(percentage)
    if metric is not None and not percentage:
        details.append(f"{metric:g}{unit}")
    if count is not None and not percentage:
        details.append(f"数量 {count:g}")
    return f"{label}：{' / '.join(details)}" if label and details else label or "已采集（无可展示值）"


def build_user_profile_item(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    clean_rows = [dict(row) for row in rows or [] if isinstance(row, dict)]
    charts = {
        code: {"title": title, "entries": _distribution_entries(clean_rows, code)}
        for code, title in CHART_DIMENSIONS
    }
    average_advance_days = _average_metric(clean_rows, "booking_advance_days")
    average_stay_nights = _average_metric(clean_rows, "stay_days")
    city_top5 = _city_entries(clean_rows)
    peak_time = _peak_entry(clean_rows)
    hourly_distribution = _hourly_entries(clean_rows)

    fields: list[dict[str, Any]] = []
    for code, label, aliases in DIMENSIONS:
        if code == "stay_days":
            value = (
                f"平均入住晚数：{average_stay_nights:g}晚"
                if average_stay_nights is not None
                else None
            )
            record_count = len(charts["stay_days"]["entries"]) + int(
                average_stay_nights is not None
            )
        elif code == "orider_peak_time":
            values: list[dict[str, Any]] = []
            if peak_time:
                values.append(peak_time)
            values.extend(hourly_distribution)
            value = _field_value(values)
            record_count = len(values)
        elif code == "city_origin_top5":
            value = _field_value(city_top5)
            record_count = len(city_top5)
        else:
            entries = charts[code]["entries"]
            value = _field_value(entries)
            record_count = len(entries)

        note = f"dimension_code={code}"
        if code == "stay_days":
            note += "，bucket_label=平均入住晚数"
        if code == "orider_peak_time":
            note += "，实时字段=order_hourly_distribution"
        fields.append(
            {
                "label": label,
                "value": value,
                "note": note,
                "dimension_code": code,
                "record_count": record_count,
                "aliases": list(aliases),
            }
        )

    connected = sum(1 for field in fields if field.get("record_count"))
    return {
        "standard_item_id": 4,
        "item_name": "用户来源画像",
        "participates_in_score": False,
        "full_score": 0,
        "item_score": 0,
        "data_status": "success" if connected else "missing",
        "source": "ctrip_ota_userprofile_distribution",
        "source_path": "携程 eBooking -> 数据中心 -> 用户行为",
        "fields": fields,
        "records": clean_rows,
        "charts": charts,
        "average_advance_days": average_advance_days,
        "average_stay_nights": average_stay_nights,
        "city_top5": city_top5,
        "peak_time": peak_time,
        "hourly_distribution": hourly_distribution,
        "connected_dimensions": connected,
        "expected_dimensions": len(DIMENSIONS),
    }


__all__ = [
    "CHART_DIMENSIONS",
    "DIMENSIONS",
    "build_user_profile_item",
    "row_text",
]
