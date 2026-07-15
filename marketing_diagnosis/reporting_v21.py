from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v20


def _crown_storage_key(result: dict[str, Any]) -> str:
    hotel = str(result.get("hotel_name") or result.get("hotel_id") or "hotel")
    start = str(result.get("period_start") or "")
    end = str(result.get("period_end") or "")
    return "s14:crown:" + hotel + ":" + start + ":" + end


def _excel_crown_script(result: dict[str, Any]) -> str:
    crown = (result.get("visual_diagnosis") or {}).get("manual_crown") or {}
    if not crown.get("crown_type"):
        return ""
    storage_key = _crown_storage_key(result)
    data = {
        "crown_type": crown.get("crown_type"),
        "operator": crown.get("operator") or "",
        "recorded_at": str(crown.get("recorded_at") or "").replace(" ", "T", 1),
    }
    return (
        "<script>(function(){try{localStorage.setItem("
        + json.dumps(storage_key, ensure_ascii=False)
        + ","
        + json.dumps(json.dumps(data, ensure_ascii=False), ensure_ascii=False)
        + ");}catch(e){}})();</script>"
    )


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v20.build_html(result)
    script = _excel_crown_script(result)
    return html_text.replace("</body>", script + "</body>", 1) if script else html_text


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v20.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v20.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = ["build_html", "build_markdown", "write_reports"]
