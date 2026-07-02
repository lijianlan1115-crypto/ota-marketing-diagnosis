from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

TRIGGER_PHRASES = [
    "S14诊断", "S14 诊断", "S14执行", "S14 执行",
    "运营诊断", "OTA诊断", "OTA全面诊断", "生成诊断报告", "查看诊断报告",
    "美团诊断", "携程诊断", "多渠道诊断",
]

PLATFORM_ALIASES = {
    "meituan": ["美团", "meituan"],
    "ctrip": ["携程", "ctrip"],
    "multi": ["多渠道", "全渠道", "multi"],
}


def should_route_to_s14(message: str) -> bool:
    normalized = str(message or "").lower()
    return any(phrase.lower() in normalized for phrase in TRIGGER_PHRASES)


def platform_from_text(message: str, default: str = "multi") -> str:
    normalized = str(message or "").lower()
    for platform, aliases in PLATFORM_ALIASES.items():
        if any(alias.lower() in normalized for alias in aliases):
            return platform
    return default


def build_control_inputs(message: str, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = defaults or {}
    today = date.today()
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", str(message or ""))
    period_start = dates[0] if dates else str(today - timedelta(days=int(defaults.get("default_period_days", 10)) - 1))
    period_end = dates[1] if len(dates) > 1 else str(today)
    return {
        "hotel_id": defaults.get("hotel_id", "puyue"),
        "hotel_name": defaults.get("hotel_name"),
        "platform": platform_from_text(message, defaults.get("platform", "multi")),
        "period_start": period_start,
        "period_end": period_end,
        "data_source_mode": defaults.get("data_source_mode", "database"),
        "output_dir": defaults.get("output_dir"),
        "public_base_url": defaults.get("public_base_url"),
        "dry_run": True,
    }
