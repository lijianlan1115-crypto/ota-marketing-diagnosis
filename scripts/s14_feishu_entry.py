#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "s14-operation-diagnosis"
ENV_FILE = Path("/etc/hotel-ota-ai/hotel-ota.env")
STATE_DIR = Path(os.environ.get("S14_STATE_DIR", "/tmp/s14_state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

TRIGGERS = ("S14诊断", "S14 诊断", "运营诊断", "OTA诊断", "OTA全面诊断", "生成诊断报告", "美团诊断", "携程诊断", "多渠道诊断")


def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _state_file(chat_id: str | None) -> Path:
    safe = "default" if not chat_id else "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in chat_id)
    return STATE_DIR / f"s14_last_excel_{safe}.json"


def _save_excel_state(chat_id: str | None, excel_path: str) -> None:
    _state_file(chat_id).write_text(json.dumps({"excel_path": excel_path, "saved_at": datetime.now().isoformat()}, ensure_ascii=False), encoding="utf-8")


def _load_excel_state(chat_id: str | None) -> str | None:
    path = _state_file(chat_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        excel_path = data.get("excel_path")
        return excel_path if excel_path and Path(excel_path).exists() else None
    except Exception:
        return None


def _print(payload: Any) -> int:
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(str(payload or ""))
    return 0


def _load_skill_class():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(SKILL_ROOT))
    spec = importlib.util.spec_from_file_location("s14_skill_runtime", SKILL_ROOT / "runtime" / "__init__.py", submodule_search_locations=[str(SKILL_ROOT / "runtime")])
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.S14OperationDiagnosis


def _config() -> dict[str, Any]:
    cfg: dict[str, Any] = {"db_dsn_env": "S14_DB_DSN"}
    if os.environ.get("S14_REPORT_OUTPUT_DIR"):
        cfg["report_output_dir"] = os.environ["S14_REPORT_OUTPUT_DIR"]
    if os.environ.get("S14_PUBLIC_BASE_URL"):
        cfg["public_base_url"] = os.environ["S14_PUBLIC_BASE_URL"]
    if os.environ.get("S14_DB_DSN"):
        cfg["db_dsn"] = os.environ["S14_DB_DSN"]
    return cfg


def _run_database(platform: str = "multi") -> dict[str, Any]:
    S14OperationDiagnosis = _load_skill_class()
    return S14OperationDiagnosis(_config()).execute({"hotel_id": "puyue", "platform": platform, "data_source_mode": "database", "dry_run": True})


def _run_excel(excel_path: str, platform: str = "multi") -> dict[str, Any]:
    S14OperationDiagnosis = _load_skill_class()
    return S14OperationDiagnosis(_config()).execute({"hotel_id": "puyue", "platform": platform, "data_source_mode": "excel_upload", "input_excel_path": excel_path, "dry_run": True})


def _platform(text: str) -> str:
    lower = text.lower()
    if "美团" in text or "meituan" in lower:
        return "meituan"
    if "携程" in text or "ctrip" in lower:
        return "ctrip"
    return "multi"


def main() -> int:
    parser = argparse.ArgumentParser(description="S14 Feishu/OpenClaw entry wrapper")
    parser.add_argument("--text", default="")
    parser.add_argument("--excel", default="")
    parser.add_argument("--chat-id", default="")
    parser.add_argument("--format", choices=("text", "card"), default=os.environ.get("S14_FEISHU_REPLY_FORMAT", "card"))
    args = parser.parse_args()
    _load_env_file()
    chat_id = args.chat_id or None
    try:
        if args.excel:
            _save_excel_state(chat_id, args.excel)
            result = _run_excel(args.excel, platform="multi")
        elif args.text and any(token in args.text for token in TRIGGERS):
            result = _run_database(platform=_platform(args.text))
        elif args.text and "复用Excel" in args.text:
            excel = _load_excel_state(chat_id)
            if not excel:
                return _print("没有可复用的 Excel，请重新上传。")
            result = _run_excel(excel, platform="multi")
        else:
            return _print("收到。需要生成 S14 OTA 营销诊断报告时，请发送「S14诊断」或上传诊断 Excel。")
        return _print(result.get("feishu_card") if args.format == "card" else result.get("feishu_message"))
    except Exception as exc:
        return _print(f"S14诊断失败：{exc}")


if __name__ == "__main__":
    raise SystemExit(main())
