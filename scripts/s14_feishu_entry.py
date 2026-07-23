#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "s14-operation-diagnosis"
ENV_FILE = Path("/etc/hotel-ota-ai/hotel-ota.env")
STATE_DIR = Path(os.environ.get("S14_STATE_DIR", "/tmp/s14_state"))
STATE_TTL_SECONDS = int(os.environ.get("S14_SOURCE_STATE_TTL_SECONDS", "600"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from marketing_diagnosis.runtime_env import load_local_s14_env
from marketing_diagnosis.room_name_manual_v43 import (
    parse_room_type_names_from_text,
)

load_local_s14_env()

TRIGGERS = (
    "S14诊断",
    "S14 诊断",
    "运营诊断",
    "OTA诊断",
    "OTA全面诊断",
    "生成诊断报告",
    "美团诊断",
    "携程诊断",
    "多渠道诊断",
)
TEMPLATE_TRIGGERS = (
    "Excel模板",
    "excel模板",
    "表格模板",
    "诊断模板",
    "数据模板",
    "模板",
    "可以发模板",
    "发个模板",
)
DATABASE_CHOICES = {"数据库", "使用数据库", "从数据库拉取", "database", "db"}
EXCEL_CHOICES = {"上传excel", "excel", "上传表格", "上传excel表格", "表格"}
HOTEL_ALIASES = {
    "puyue": ("puyue", "璞悦"),
    "璞悦": ("puyue", "璞悦"),
    "璞悦酒店": ("puyue", "璞悦"),
}
TRUE_VALUES = {"1", "true", "yes", "on"}


def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _card_callback_enabled() -> bool:
    return (
        str(os.environ.get("S14_FEISHU_CARD_CALLBACK_ENABLED") or "")
        .strip()
        .lower()
        in TRUE_VALUES
    )


def _safe_id(value: str | None) -> str:
    raw = str(value or "default").strip() or "default"
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in raw)


def _flow_state_file(chat_id: str | None, sender_id: str | None) -> Path:
    return STATE_DIR / f"s14_flow_{_safe_id(chat_id)}_{_safe_id(sender_id)}.json"


def _last_excel_file(chat_id: str | None) -> Path:
    return STATE_DIR / f"s14_last_excel_{_safe_id(chat_id)}.json"


def _set_flow_state(
    state: str,
    *,
    chat_id: str | None,
    sender_id: str | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "state": state,
        "updated_at": time.time(),
        **(extra or {}),
    }
    _flow_state_file(chat_id, sender_id).write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record


def _get_flow_state(chat_id: str | None, sender_id: str | None) -> dict[str, Any] | None:
    path = _flow_state_file(chat_id, sender_id)
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            path.unlink(missing_ok=True)
            return None
        updated_at = float(record.get("updated_at") or 0)
        if time.time() - updated_at > STATE_TTL_SECONDS:
            path.unlink(missing_ok=True)
            return None
        return record
    except (OSError, ValueError, TypeError):
        path.unlink(missing_ok=True)
        return None


def _clear_flow_state(chat_id: str | None, sender_id: str | None) -> None:
    _flow_state_file(chat_id, sender_id).unlink(missing_ok=True)


def _save_excel_state(chat_id: str | None, excel_path: str) -> None:
    _last_excel_file(chat_id).write_text(
        json.dumps(
            {"excel_path": excel_path, "saved_at": datetime.now().isoformat()},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _load_excel_state(chat_id: str | None) -> str | None:
    path = _last_excel_file(chat_id)
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
    if os.environ.get("S14_CTRIP_HOTEL_ID"):
        cfg["ctrip_hotel_id"] = os.environ["S14_CTRIP_HOTEL_ID"]
    return cfg


def _output_root() -> str:
    return os.environ.get("S14_REPORT_OUTPUT_DIR") or "/var/lib/ota-marketing-diagnosis/reports"


def _hotel(text: str) -> tuple[str, str | None]:
    lower = text.lower()
    for alias, value in HOTEL_ALIASES.items():
        if alias.lower() in lower or alias in text:
            return value
    return "puyue", "璞悦"


def _manual_names(text: str, state: dict[str, Any] | None = None) -> list[str]:
    names = parse_room_type_names_from_text(text)
    if names:
        return names
    stored = (state or {}).get("manual_room_type_names")
    return [str(value).strip() for value in stored or [] if str(value).strip()]


def _state_extra(
    state: dict[str, Any] | None,
    names: list[str],
    sender_id: str | None,
) -> dict[str, Any]:
    return {
        "manual_room_type_names": names or list((state or {}).get("manual_room_type_names") or []),
        "manual_input_operator": sender_id or (state or {}).get("manual_input_operator"),
        "manual_input_recorded_at": (
            datetime.now().isoformat(timespec="seconds")
            if names
            else (state or {}).get("manual_input_recorded_at")
        ),
    }


def _request_context(
    text: str,
    *,
    manual_room_type_names: list[str] | None = None,
    sender_id: str | None = None,
) -> dict[str, Any]:
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
        "platform": "multi",
        "period_start": str(start),
        "period_end": str(today),
        "period_days": days,
        "request_text": text,
        "manual_room_type_names": manual_room_type_names or [],
        "manual_input_source": "飞书文本或语音转写人工输入",
        "manual_input_operator": sender_id,
    }


def _run_database(
    text: str = "",
    *,
    manual_room_type_names: list[str] | None = None,
    sender_id: str | None = None,
) -> dict[str, Any]:
    S14OperationDiagnosis = _load_skill_class()
    context = _request_context(
        text,
        manual_room_type_names=manual_room_type_names,
        sender_id=sender_id,
    )
    return S14OperationDiagnosis(_config()).execute(
        {**context, "data_source_mode": "database", "dry_run": True}
    )


def _run_excel(
    excel_path: str,
    text: str = "",
    *,
    manual_room_type_names: list[str] | None = None,
    sender_id: str | None = None,
) -> dict[str, Any]:
    S14OperationDiagnosis = _load_skill_class()
    context = _request_context(
        text,
        manual_room_type_names=manual_room_type_names,
        sender_id=sender_id,
    )
    return S14OperationDiagnosis(_config()).execute(
        {
            **context,
            "data_source_mode": "excel_upload",
            "input_excel_path": excel_path,
            "dry_run": True,
        }
    )


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
        "填写后先发送“S14诊断”并选择“上传Excel”，再直接发送 Excel 附件。\n"
        "注意：sheet 名和第一行字段名不要改；没有的数据可以留空。"
    )


def _is_template_request(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(token in text or token.lower() in lower for token in TEMPLATE_TRIGGERS) and (
        "excel" in lower or "表" in text or "模板" in text
    )


def _source_selection_card(manual_names: list[str] | None = None) -> dict[str, Any]:
    manual_note = (
        f"\n\n已记录人工房型名称：**{'、'.join(manual_names)}**"
        if manual_names
        else "\n\n第11项为人工输入项；可发送：`房型名称：五人战队套房、电竞双床房`。"
    )
    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    "本次按已经映射好的字段执行**整体诊断**。\n\n"
                    "请选择从服务器数据库读取，或随后上传 Excel。"
                    + manual_note
                ),
            },
        }
    ]
    if _card_callback_enabled():
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "type": "primary",
                        "text": {"tag": "plain_text", "content": "数据库"},
                        "value": {"action": "s14_source", "source": "database"},
                    },
                    {
                        "tag": "button",
                        "type": "default",
                        "text": {"tag": "plain_text", "content": "上传Excel"},
                        "value": {"action": "s14_source", "source": "excel"},
                    },
                ],
            }
        )
    else:
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "请直接回复 **数据库** 或 **上传Excel**。",
                },
            }
        )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": "S14诊断｜请选择数据来源"},
            },
            "elements": elements,
        },
    }


def _waiting_excel_card(manual_names: list[str] | None = None) -> dict[str, Any]:
    manual_note = (
        f"\n\n已记录人工房型名称：**{'、'.join(manual_names)}**"
        if manual_names
        else "\n\n尚未提供人工房型名称时，第11项将按0分计入总分。"
    )
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "turquoise",
                "title": {"tag": "plain_text", "content": "S14诊断｜等待Excel附件"},
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "**数据来源：Excel**\n\n"
                            "请在当前群聊中直接发送 `.xlsx` 或 `.xlsm` 文件，"
                            "**无需再次@机器人**。\n\n"
                            "系统按当前群聊和当前用户关联，等待状态10分钟内有效。"
                            + manual_note
                        ),
                    },
                }
            ],
        },
    }


def _result_payload(result: dict[str, Any], output_format: str) -> Any:
    """Select one already-complete outbound representation.

    The adapter includes the source label in both representations. Prepending a
    second label produced the duplicated “数据来源/来源” lines seen in Feishu.
    """
    return (
        result.get("feishu_card")
        if output_format == "card"
        else result.get("feishu_message")
    )


def _resolved_output_format(requested: str, raw_card_json: bool) -> str:
    """Keep native card JSON out of ordinary OpenClaw stdout replies.

    OpenClaw renders channel UI through its message/presentation layer. A shell
    command's stdout is plain text, so printing provider-native card JSON there
    makes the JSON visible to the user. Raw JSON remains available only for a
    dedicated adapter that opts in explicitly.
    """
    if requested == "card" and not raw_card_json:
        return "text"
    return requested


def _normalize_choice(value: str) -> str | None:
    normalized = str(value or "").strip().lower().replace(" ", "")
    database_values = {item.lower().replace(" ", "") for item in DATABASE_CHOICES}
    excel_values = {item.lower().replace(" ", "") for item in EXCEL_CHOICES}
    if normalized in database_values or any(normalized.startswith(item) for item in database_values):
        return "database"
    if normalized in excel_values or any(normalized.startswith(item) for item in excel_values):
        return "excel"
    return None


def _handle_source_choice(
    source: str,
    *,
    chat_id: str | None,
    sender_id: str | None,
    text: str,
    output_format: str,
) -> Any:
    choice = _normalize_choice(source)
    old_state = _get_flow_state(chat_id, sender_id) or {}
    names = _manual_names(text, old_state)
    extra = _state_extra(old_state, names, sender_id)

    if choice == "database":
        _set_flow_state(
            "running_database",
            chat_id=chat_id,
            sender_id=sender_id,
            extra=extra,
        )
        try:
            result = _run_database(
                text,
                manual_room_type_names=extra.get("manual_room_type_names"),
                sender_id=sender_id,
            )
            _clear_flow_state(chat_id, sender_id)
            return _result_payload(result, output_format)
        except Exception:
            _set_flow_state(
                "awaiting_source",
                chat_id=chat_id,
                sender_id=sender_id,
                extra=extra,
            )
            raise

    if choice == "excel":
        _set_flow_state(
            "awaiting_excel",
            chat_id=chat_id,
            sender_id=sender_id,
            extra=extra,
        )
        return (
            _waiting_excel_card(extra.get("manual_room_type_names"))
            if output_format == "card"
            else "数据来源：Excel\n请直接发送Excel附件，无需再次@机器人。等待状态10分钟内有效。"
        )

    return (
        _source_selection_card(names)
        if output_format == "card"
        else "请选择本次数据来源：数据库 / 上传Excel。当前报告不再区分渠道。"
    )


def handle_card_source_choice(
    source: str,
    *,
    chat_id: str,
    sender_id: str,
) -> dict[str, Any] | str:
    """Run one trusted card source action and return a structured reply.

    This is the public bridge used by the Feishu callback service. The returned
    card remains an in-process object and must be sent through Feishu OpenAPI;
    callers must never print or forward its serialized JSON as assistant text.
    """
    return _handle_source_choice(
        source,
        chat_id=chat_id,
        sender_id=sender_id,
        text="数据库" if source == "database" else "上传Excel",
        output_format="card",
    )


def _manual_input_ack(names: list[str], state: dict[str, Any]) -> str:
    next_step = {
        "awaiting_source": "请继续选择“数据库”或“上传Excel”。",
        "awaiting_excel": "请继续发送Excel附件。",
        "manual_ready": "请发送“S14诊断”，再选择数据来源。",
    }.get(str(state.get("state") or ""), "请发送“S14诊断”继续。")
    return f"已记录人工房型名称：{'、'.join(names)}。{next_step}"


def main() -> int:
    parser = argparse.ArgumentParser(description="S14 Feishu/OpenClaw entry wrapper")
    parser.add_argument("--text", default="")
    parser.add_argument("--excel", default="")
    parser.add_argument("--chat-id", default=os.environ.get("FEISHU_CHAT_ID", ""))
    parser.add_argument("--sender-id", default=os.environ.get("FEISHU_SENDER_ID", ""))
    parser.add_argument("--source-choice", default="")
    parser.add_argument("--make-template", action="store_true")
    parser.add_argument(
        "--format",
        choices=("text", "card"),
        default=os.environ.get("S14_FEISHU_REPLY_FORMAT", "text"),
        help=(
            "stdout format; card requires --raw-card-json and is intended only "
            "for a structured Feishu/OpenClaw adapter"
        ),
    )
    parser.add_argument(
        "--raw-card-json",
        action="store_true",
        help="allow provider-native card JSON on stdout for a caller that parses it",
    )
    args = parser.parse_args()
    _load_env_file()
    chat_id = args.chat_id or None
    sender_id = args.sender_id or None
    output_format = _resolved_output_format(args.format, args.raw_card_json)
    if args.format == "card" and output_format == "text":
        print(
            "S14: --format card requires --raw-card-json; using safe text output.",
            file=sys.stderr,
        )

    try:
        if args.make_template or _is_template_request(args.text):
            return _print(_template_reply())

        if args.source_choice:
            return _print(
                _handle_source_choice(
                    args.source_choice,
                    chat_id=chat_id,
                    sender_id=sender_id,
                    text=args.text,
                    output_format=output_format,
                )
            )

        state = _get_flow_state(chat_id, sender_id) or {}
        parsed_names = parse_room_type_names_from_text(args.text)

        if args.excel:
            identity_supplied = bool(chat_id or sender_id)
            if identity_supplied and state.get("state") != "awaiting_excel":
                message = "请先发送“S14诊断”，选择“上传Excel”后再发送附件。"
                return _print(
                    {
                        "msg_type": "interactive",
                        "card": {
                            "header": {
                                "template": "orange",
                                "title": {"tag": "plain_text", "content": "S14诊断｜尚未选择Excel"},
                            },
                            "elements": [
                                {"tag": "div", "text": {"tag": "lark_md", "content": message}}
                            ],
                        },
                    }
                    if output_format == "card"
                    else message
                )

            path = Path(args.excel).expanduser().resolve()
            if path.suffix.lower() not in {".xlsx", ".xlsm"}:
                return _print("请上传 .xlsx 或 .xlsm 格式的 S14 Excel 文件。")
            _save_excel_state(chat_id, str(path))
            names = parsed_names or list(state.get("manual_room_type_names") or [])
            result = _run_excel(
                str(path),
                args.text,
                manual_room_type_names=names,
                sender_id=sender_id,
            )
            _clear_flow_state(chat_id, sender_id)
            return _print(_result_payload(result, output_format))

        if args.text and any(token in args.text for token in TRIGGERS):
            old_names = list(state.get("manual_room_type_names") or [])
            names = parsed_names or old_names
            new_state = _set_flow_state(
                "awaiting_source",
                chat_id=chat_id,
                sender_id=sender_id,
                extra=_state_extra(state, names, sender_id),
            )
            return _print(
                _source_selection_card(new_state.get("manual_room_type_names"))
                if output_format == "card"
                else "请选择本次数据来源：数据库 / 上传Excel。当前报告不再区分渠道。"
            )

        choice = _normalize_choice(args.text)
        if choice and state.get("state") == "awaiting_source":
            return _print(
                _handle_source_choice(
                    args.text,
                    chat_id=chat_id,
                    sender_id=sender_id,
                    text=args.text,
                    output_format=output_format,
                )
            )

        if parsed_names:
            next_state = str(state.get("state") or "manual_ready")
            if next_state not in {"awaiting_source", "awaiting_excel"}:
                next_state = "manual_ready"
            saved = _set_flow_state(
                next_state,
                chat_id=chat_id,
                sender_id=sender_id,
                extra=_state_extra(state, parsed_names, sender_id),
            )
            return _print(_manual_input_ack(parsed_names, saved))

        if args.text and "复用Excel" in args.text:
            excel = _load_excel_state(chat_id)
            if not excel:
                return _print("没有可复用的 Excel，请重新上传。")
            names = list(state.get("manual_room_type_names") or [])
            result = _run_excel(
                excel,
                args.text,
                manual_room_type_names=names,
                sender_id=sender_id,
            )
            return _print(_result_payload(result, output_format))

        return _print(
            "收到。需要生成 S14 OTA 诊断报告时，请发送「S14诊断」；"
            "人工房型名称可发送「房型名称：五人战队套房、电竞双床房」；"
            "需要 Excel 填报模板时，请发送「Excel模板」。"
        )
    except Exception as exc:
        return _print(f"S14诊断失败：{exc}")


if __name__ == "__main__":
    raise SystemExit(main())
