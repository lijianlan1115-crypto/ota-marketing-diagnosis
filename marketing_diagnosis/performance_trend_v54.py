from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any


CATEGORY = "总营业指标"
DISPLAY_METRICS = (
    ("房费", "房费", "revenue"),
    ("平均房价", "ADR", "adr"),
    ("出租率", "出租率", "occupancy"),
    ("RevPar", "RevPAR", "revpar"),
)

_METRIC_ALIASES = {
    "revpar": "RevPar",
    "revpar值": "RevPar",
    "平均房价adr": "平均房价",
    "adr": "平均房价",
}


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _date(value: Any) -> date | None:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _metric_name(value: Any) -> str:
    text = str(value or "").strip().replace(" ", "")
    return _METRIC_ALIASES.get(text.lower(), _METRIC_ALIASES.get(text, text))


def _is_total_metric_row(row: dict[str, Any]) -> bool:
    return (
        str(row.get("category") or "").strip() == CATEGORY
        and row.get("room_type_id") in (None, "")
        and _metric_name(row.get("metric_name"))
        in {source_name for source_name, _, _ in DISPLAY_METRICS}
    )


def _shift_month(value: date, months: int) -> date:
    absolute = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(absolute, 12)
    month = month_index + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _previous_year(value: date) -> date:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _month_end(value: date) -> date:
    return value.replace(day=monthrange(value.year, value.month)[1])


def _format_range(start: date, end: date) -> str:
    return f"{start:%Y/%m/%d}—{end:%Y/%m/%d}"


def _growth(current: Any, previous: Any) -> float | None:
    current_number = _number(current)
    previous_number = _number(previous)
    if current_number is None or previous_number in (None, 0):
        return None
    return current_number / previous_number - 1


def _latest_rows_within(
    rows: list[dict[str, Any]],
    start: date,
    end: date,
) -> tuple[dict[str, dict[str, Any]], date | None]:
    selected: dict[str, tuple[tuple[date, str, int], dict[str, Any]]] = {}
    latest_day: date | None = None

    for index, row in enumerate(rows):
        if not _is_total_metric_row(row):
            continue
        business_day = _date(row.get("business_date"))
        if business_day is None or business_day < start or business_day > end:
            continue
        metric = _metric_name(row.get("metric_name"))
        latest_day = business_day if latest_day is None or business_day > latest_day else latest_day
        order_key = (business_day, str(row.get("snapshot_time") or ""), index)
        current = selected.get(metric)
        if current is None or order_key >= current[0]:
            selected[metric] = (order_key, row)

    return {metric: value[1] for metric, value in selected.items()}, latest_day


def build_performance_trend_periods(
    rows: list[dict[str, Any]],
    latest_business_day: str | date | None,
) -> list[dict[str, Any]]:
    """Build two complete natural months plus current month-to-date from JL02.

    Only rows where ``category=总营业指标`` and ``room_type_id`` is empty are
    accepted.  Every displayed current/prior value is read directly from the
    matching row's ``value_month`` field.  Display YOY uses the common growth
    formula ``current / previous - 1``; the existing diagnosis score remains
    untouched and continues to use its previously confirmed rule.
    """

    latest = latest_business_day if isinstance(latest_business_day, date) else _date(latest_business_day)
    if latest is None:
        return []

    periods: list[dict[str, Any]] = []
    for month_offset in (-2, -1, 0):
        anchor = _shift_month(latest, month_offset)
        expected_start = _month_start(anchor)
        expected_end = latest if month_offset == 0 else _month_end(anchor)

        current_rows, actual_current_end = _latest_rows_within(rows, expected_start, expected_end)
        current_end = actual_current_end or expected_end

        previous_start = _previous_year(expected_start)
        expected_previous_end = _previous_year(current_end)
        previous_rows, actual_previous_end = _latest_rows_within(
            rows,
            previous_start,
            expected_previous_end,
        )
        previous_end = actual_previous_end or expected_previous_end

        metrics: list[dict[str, Any]] = []
        for source_name, label, key in DISPLAY_METRICS:
            current_value = _number((current_rows.get(source_name) or {}).get("value_month"))
            previous_value = _number((previous_rows.get(source_name) or {}).get("value_month"))
            metrics.append(
                {
                    "key": key,
                    "label": label,
                    "source_metric": source_name,
                    "current": current_value,
                    "previous": previous_value,
                    "yoy": _growth(current_value, previous_value),
                }
            )

        periods.append(
            {
                "period_key": f"{expected_start:%Y-%m}",
                "current_start": expected_start.isoformat(),
                "current_end": current_end.isoformat(),
                "current_range": _format_range(expected_start, current_end),
                "previous_start": previous_start.isoformat(),
                "previous_end": previous_end.isoformat(),
                "previous_range": _format_range(previous_start, previous_end),
                "metrics": metrics,
            }
        )

    return periods


def attach_performance_trend(
    item: dict[str, Any],
    rows: list[dict[str, Any]],
    latest_business_day: str | date | None,
) -> None:
    periods = build_performance_trend_periods(rows, latest_business_day)
    item["trend_periods"] = periods
    item["trend_metric_order"] = [
        {"key": key, "label": label, "source_metric": source}
        for source, label, key in DISPLAY_METRICS
    ]


__all__ = [
    "CATEGORY",
    "DISPLAY_METRICS",
    "attach_performance_trend",
    "build_performance_trend_periods",
]
