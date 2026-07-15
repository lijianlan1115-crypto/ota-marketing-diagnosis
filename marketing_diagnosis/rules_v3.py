from __future__ import annotations

from copy import deepcopy
from typing import Any

from marketing_diagnosis.metrics_enrichment_v2 import enrich_metrics
from marketing_diagnosis.rules import process as base_process
from marketing_diagnosis.visual_diagnosis_v12 import build_visual_diagnosis


def process(data: dict[str, Any]) -> dict[str, Any]:
    """Run the base diagnosis with corrected database-backed visuals."""
    result = base_process(data)
    sections = data.get("sections") or {}
    metrics = deepcopy(result.get("metrics") or {})
    result["metrics"] = metrics
    result["data_time_context"] = enrich_metrics(metrics, sections)
    result["visual_diagnosis"] = build_visual_diagnosis(sections)
    return result
