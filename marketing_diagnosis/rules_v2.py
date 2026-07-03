from __future__ import annotations

from copy import deepcopy
from typing import Any

from marketing_diagnosis.ai_analysis import build_ai_analysis
from marketing_diagnosis.metrics_enrichment import enrich_metrics
from marketing_diagnosis.rules import process as base_process


def process(data: dict[str, Any]) -> dict[str, Any]:
    """Run the base diagnosis, then add time-grain and AI-ready enrichment.

    The base rule engine remains the scoring source of truth. This wrapper makes the
    report clearer by adding data-period metadata, latest-vs-previous funnel views,
    recent-90-day reputation context, and nearby-event AI context before the final
    AI analysis is generated.
    """
    result = base_process(data)
    sections = data.get("sections") or {}
    metrics = deepcopy(result.get("metrics") or {})
    result["metrics"] = metrics
    result["data_time_context"] = enrich_metrics(metrics, sections)
    result["ai_analysis"] = build_ai_analysis(result)
    return result
