from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SKILL_ID = "s14-operation-diagnosis"
SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]
DEFAULT_REPORT_ROOT = Path("/var/lib/ota-marketing-diagnosis/reports")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from marketing_diagnosis.data_v2 import normalize_dataset
from marketing_diagnosis.db_loader_v4 import load_mysql_dsn_dataset
from marketing_diagnosis.excel_loader import load_excel_dataset
from marketing_diagnosis.reporting_v2 import write_reports
from marketing_diagnosis.rules_v3 import process

from .feishu_adapter import build_feishu_card_reply, build_feishu_reply


def _safe_segment(value: Any, fallback: str) -> str:
    text = str(value or fallback).strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    return text.strip("-._") or fallback


class S14OperationDiagnosis:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        prepared = self._prepare_inputs(inputs or {})
        mode = prepared["data_source_mode"]
        if mode == "excel_upload":
            excel_path = prepared.get("input_excel_path")
            if not excel_path:
                raise ValueError("S14 excel_upload mode requires input_excel_path")
            raw_dataset = load_excel_dataset(excel_path)
            data_source = "excel_upload"
        elif mode == "database":
            dsn = self._resolve_dsn()
            if not dsn:
                raise ValueError("S14 database mode requires S14_DB_DSN or config db_dsn")
            raw_dataset = load_mysql_dsn_dataset(
                dsn,
                limit=int(self.config.get("limit") or prepared.get("limit") or 5000),
                hotel_id=prepared.get("hotel_id"),
                platform=prepared.get("platform"),
                period_start=prepared.get("period_start"),
                period_end=prepared.get("period_end"),
            )
            data_source = "hotel_puyue_mysql"
        else:
            raise ValueError(f"unsupported S14 data_source_mode: {mode}")

        normalized = normalize_dataset(raw_dataset)
        result = process(normalized)
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_dir = self._report_dir(prepared, run_id)
        skill_result = {
            **result,
            "skill_id": SKILL_ID,
            "run_id": run_id,
            "hotel_id": prepared.get("hotel_id"),
            "hotel_name": prepared.get("hotel_name"),
            "platform": prepared.get("platform"),
            "period_start": prepared.get("period_start"),
            "period_end": prepared.get("period_end"),
            "period_days": prepared.get("period_days"),
            "data_source": data_source,
            "report_dir": str(report_dir),
            "approval_required": False,
            "dry_run": True,
        }
        paths = write_reports(skill_result, report_dir)
        report_file_path = paths["report_html"]
        report_url = self._public_url(report_file_path, prepared["output_root"])
        skill_result.update({
            "report_file_path": report_file_path,
            "report_url": report_url,
            "report_json": paths["report_json"],
            "report_markdown": paths["report_markdown"],
        })
        skill_result["feishu_message"] = build_feishu_reply(skill_result)
        skill_result["feishu_card"] = build_feishu_card_reply(skill_result)
        return skill_result

    def _resolve_dsn(self) -> str | None:
        env_name = self.config.get("db_dsn_env") or "S14_DB_DSN"
        return self.config.get("db_dsn") or os.environ.get(env_name) or os.environ.get("S14_DB_DSN")

    def _prepare_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        today = datetime.now().date()
        period_days = int(inputs.get("period_days") or 30)
        start = today - timedelta(days=max(1, period_days) - 1)
        output_root = (
            inputs.get("output_root")
            or inputs.get("output_dir")
            or self.config.get("report_output_dir")
            or os.environ.get("S14_REPORT_OUTPUT_DIR")
            or str(DEFAULT_REPORT_ROOT)
        )
        return {
            "data_source_mode": inputs.get("data_source_mode") or "database",
            "input_excel_path": inputs.get("input_excel_path"),
            "hotel_id": inputs.get("hotel_id") or "puyue",
            "hotel_name": inputs.get("hotel_name"),
            "platform": inputs.get("platform") or "multi",
            "period_start": inputs.get("period_start") or str(start),
            "period_end": inputs.get("period_end") or str(today),
            "period_days": period_days,
            "output_root": output_root,
            "public_base_url": inputs.get("public_base_url") or self.config.get("public_base_url") or os.environ.get("S14_PUBLIC_BASE_URL"),
            "dry_run": True,
            "limit": inputs.get("limit"),
        }

    def _report_dir(self, prepared: dict[str, Any], run_id: str) -> Path:
        root = Path(prepared["output_root"])
        hotel = _safe_segment(prepared.get("hotel_id"), "hotel")
        platform = _safe_segment(prepared.get("platform"), "multi")
        period = f"{_safe_segment(prepared.get('period_start'), 'start')}_{_safe_segment(prepared.get('period_end'), 'end')}"
        return root / hotel / platform / period / run_id

    def _public_url(self, report_file_path: str, output_root: str) -> str:
        base = self.config.get("public_base_url") or os.environ.get("S14_PUBLIC_BASE_URL")
        if base:
            try:
                rel = Path(report_file_path).resolve().relative_to(Path(output_root).resolve())
                return base.rstrip("/") + "/" + rel.as_posix()
            except ValueError:
                return base.rstrip("/") + "/" + Path(report_file_path).name
        return Path(report_file_path).resolve().as_uri()
