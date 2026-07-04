#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "s14-operation-diagnosis"
ENV_FILE = Path("/etc/hotel-ota-ai/hotel-ota.env")
STATE_DIR = Path(os.environ.get("S14_STATE_DIR", "/tmp/s14_state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

TRIGGERS = ("S14诊断", "S14 诊断", "运营诊断", "OTA诊断", "OTA全面诊断", "生成诊断报告", "美团诊断", "携程诊断", "多渠道诊断")
TEMPLATE_TRIGGERS = ("Excel模板", "excel模板", "表格模板", "诊断模板", "数据模板", "模板", "可以发模板", "发个模板")
HOTEL_ALIASES = {
    "puyue": ("puyue", "璞悦"),
    "璞悦": ("puyue", "璞悦"),
    "璞悦酒店": ("puyue", "璞悦"),
}


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
    from runtime import S14OperationDiagnosis
    return S14OperationDiagnosis


def _config() -> dict[str, Any]:
    cfg: dict[str, Any] = {"db_dsn_env": "S14_DB_DSN"}
    if os.environ.get("S14_REPORT_OUTPUT_DIR"):
        cfg["report_output_dir"] = os.environ["S14_REPORT_OUTPUT_DIR"]
    if os.environ.get("S14_PUBLIC_BASE_URL"):
        cfg["public_base_url"] = os.environ["S14_PUBLIC_BASE_URL"]
    if os.environ.get("S14_DB_DSN"):
        cfg["db_dsn"] = os.environ["S14_DB_DSN"]
    return cfg


def _output_root() -> str:
    return os.environ.get("S14_REPORT_OUTPUT_DIR") or "/var/lib/ota-marketing-diagnosis/reports"


def _platform(text: str) -> str:
    lower = text.lower()
    if "美团" in text or "meituan" in lower:
        return "meituan"
    if "携程" in text or "ctrip" in lower:
        return "ctrip"
    if "飞猪" in text or "fliggy" in lower:
        return "fliggy"
    if "多渠道" in text or "全渠道" in text or "multi" in lower:
        return "multi"
    return "multi"


def _hotel(text: str) -> tuple[str, str | None]:
    lower = text.lower()
    for alias, value in HOTEL_ALIASES.items():
        if alias.lower() in lower or alias in text:
            return value
    return "puyue", "璞悦"


def _request_context(text: str) -> dict[str, Any]:
    today = datetime.now().date()
    days = 30
    match = re.search(r"最近\s*(\d+)\s*天", text)
    if match:
        days = max(1, min(366, int(match.group(1))))
    start = today - timedelta(days=days - 1)
    hotel_id, hotel_name = _hotel(text)
    return {
        "hotel_id": hotel_id,
        "hotel_name": hotel_name,
        "platform": _platform(text),
        "period_start": str(start),
        "period_end": str(today),
        "period_days": days,
    }


def _run_database(text: str = "") -> dict[str, Any]:
    S14OperationDiagnosis = _load_skill_class()
    context = _request_context(text)
    return S14OperationDiagnosis(_config()).execute({**context, "data_source_mode": "database", "dry_run": True})


def _run_excel(excel_path: str, text: str = "") -> dict[str, Any]:
    S14OperationDiagnosis = _load_skill_class()
    context = _request_context(text)
    return S14OperationDiagnosis(_config()).execute({**context, "data_source_mode": "excel_upload", "input_excel_path": excel_path, "dry_run": True})


def _template_url(template_path: Path) -> str:
    base = os.environ.get("S14_PUBLIC_BASE_URL")
    if not base:
        return str(template_path)
    root = Path(_output_root()).resolve()
    try:
        rel = template_path.resolve().relative_to(root)
        return base.rstrip("/") + "/" + rel.as_posix()
    except ValueError:
        return base.rstrip("/") + "/" + template_path.name


def _template_reply() -> str:
    sys.path.insert(0, str(ROOT))
    from marketing_diagnosis.excel_template import ensure_excel_template

    template_path = ensure_excel_template(_output_root())
    url = _template_url(template_path)
    return (
        "可以发送 Excel 分析。\n"
        f"请先下载并填写 S14 数据模板：{url}\n"
        "填写后把 Excel 文件发回来，我会按同一套 S14 流程读取数据并生成 HTML 诊断报告。\n"
        "注意：sheet 名和第一行字段名不要改；没有的数据可以留空。"
    )


def _is_template_request(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(token in text or token.lower() in lower for token in TEMPLATE_TRIGGERS) and ("excel" in lower or "表" in text or "模板" in text)


def main() -> int:
    parser = argparse.ArgumentParser(description="S14 Feishu/OpenClaw entry wrapper")
    parser.add_argument("--text", default="")
    parser.add_argument("--excel", default="")
    parser.add_argument("--chat-id", default="")
    parser.add_argument("--make-template", action="store_true")
    parser.add_argument("--format", choices=("text", "card"), default=os.environ.get("S14_FEISHU_REPLY_FORMAT", "card"))
    args = parser.parse_args()
    _load_env_file()
    chat_id = args.chat_id or None
    try:
        if args.make_template or _is_template_request(args.text):
            return _print(_template_reply())
        if args.excel:
            _save_excel_state(chat_id, args.excel)
            result = _run_excel(args.excel, args.text)
        elif args.text and any(token in args.text for token in TRIGGERS):
            result = _run_database(args.text)
        elif args.text and "复用Excel" in args.text:
            excel = _load_excel_state(chat_id)
            if not excel:
                return _print("没有可复用的 Excel，请重新上传。")
            result = _run_excel(excel, args.text)
        else:
            return _print("收到。需要生成 S14 OTA 诊断报告时，请发送「S14诊断」；需要 Excel 填报模板时，请发送「Excel模板」。")
        return _print(result.get("feishu_card") if args.format == "card" else result.get("feishu_message"))
    except Exception as exc:
        return _print(f"S14诊断失败：{exc}")


if __name__ == "__main__":
    raise SystemExit(main())
