from __future__ import annotations

from typing import Any

from marketing_diagnosis.ctrip_flow import build_flow_item
from marketing_diagnosis.rules_v5 import _refresh_ctrip_summary
from marketing_diagnosis.rules_v5 import process as upstream_process


def process(data: dict[str, Any]) -> dict[str, Any]:
    """Replace item 03 after the established rule pipeline has completed."""

    result = upstream_process(data)
    sections = data.get("sections") or {}
    items = result.setdefault("ctrip_items", {})
    existing = items.get("3") or items.get(3)
    items["3"] = build_flow_item(
        sections,
        existing if isinstance(existing, dict) else None,
    )
    _refresh_ctrip_summary(result)
    return result


__all__ = ["process"]
