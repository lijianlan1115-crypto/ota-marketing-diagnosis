from __future__ import annotations

import re
from typing import Any, Iterable


SELLING_POINT_TERMS = (
    "电竞",
    "亲子",
    "麻将",
    "棋牌",
    "上下铺",
    "套房",
    "影音",
    "投影",
    "浴缸",
    "景观",
    "家庭",
    "商务",
    "榻榻米",
    "单人",
    "双床",
    "大床",
    "三人",
    "四人",
    "五人",
    "战队",
    "开黑",
    "情侣",
    "豪华",
    "智能",
)

_MANUAL_SOURCE = "用户手动输入（网页/飞书文本或语音转写）"
_STRONG_SPLIT_PATTERN = re.compile(r"[,，、;；|]+")
_LIST_MARKER_PATTERN = re.compile(
    r"^\s*(?:[-*•·●▪◦]+|\d{1,3}\s*[.、)）:：])\s*"
)
_COMPLETE_ROOM_NAME_PATTERN = re.compile(
    r"(?:房|房间|客房|套房|大床|双床|单人间|双人间|三人间|四人间|五人间|多人间|榻榻米)"
    r"(?:\s*[（(【\[].*?[）)】\]])?\s*$"
)
_PREFIX_PATTERN = re.compile(
    r"(?:房型名称|房型名|人工房型|在售房型)\s*(?:是|为|有|包括|如下|[:：])\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)


def _clean_input_line(value: Any) -> str:
    text = str(value or "").replace("\u200b", "").replace("\ufeff", "")
    text = _LIST_MARKER_PATTERN.sub("", text, count=1).strip()
    text = text.strip(" \t。.!！?？：:,，、;；|\"'“”‘’")
    if not re.search(r"[0-9A-Za-z\u3400-\u9fff]", text):
        return ""
    return text


def _looks_complete_room_name(value: str) -> bool:
    return bool(_COMPLETE_ROOM_NAME_PATTERN.search(str(value or "").strip()))


def _merge_wrapped_lines(value: str) -> list[str]:
    """Merge hard line wraps while preserving intentional one-room-per-line input.

    A newline is treated as a real room boundary only when the previous buffer
    already looks like a complete room name (for example ending in 房/间/床/套房)
    or the new line starts with an explicit list marker. Otherwise the line is
    considered a wrapped continuation and is joined back without spaces.
    """

    lines = str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    names: list[str] = []
    buffer = ""

    for raw_line in lines:
        has_list_marker = bool(_LIST_MARKER_PATTERN.match(raw_line))
        line = _clean_input_line(raw_line)
        if not line:
            continue

        if not buffer:
            buffer = line
            continue

        if has_list_marker or _looks_complete_room_name(buffer):
            names.append(buffer)
            buffer = line
        else:
            buffer += line

    if buffer:
        names.append(buffer)
    return names


def _split_manual_text(value: str) -> list[str]:
    names: list[str] = []
    for segment in _STRONG_SPLIT_PATTERN.split(str(value or "")):
        names.extend(_merge_wrapped_lines(segment))
    return names


def normalize_room_type_names(value: Any) -> list[str]:
    """Normalize manually supplied names without splitting wrapped long names."""

    if value in (None, ""):
        return []

    raw_values: list[Any]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        match = _PREFIX_PATTERN.search(text)
        if match:
            text = match.group(1).strip()
        raw_values = _split_manual_text(text)
    elif isinstance(value, (list, tuple, set)):
        raw_values = []
        for item in value:
            if isinstance(item, str):
                raw_values.extend(normalize_room_type_names(item))
            else:
                raw_values.append(item)
    else:
        raw_values = [value]

    names: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        name = _clean_input_line(raw)
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def parse_room_type_names_from_text(text: Any) -> list[str]:
    """Extract room type names from Feishu text or voice-transcribed text."""

    raw = str(text or "").strip()
    if not raw:
        return []
    match = _PREFIX_PATTERN.search(raw)
    if not match:
        return []
    return normalize_room_type_names(match.group(1))


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in result.get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _manual_rows(sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        row
        for row in list(sections.get("manual_inputs") or [])
        if isinstance(row, dict)
    ]


def _latest_manual_names(
    sections: dict[str, list[dict[str, Any]]],
) -> tuple[list[str], str, str, str]:
    rows = _manual_rows(sections)
    if not rows:
        return [], _MANUAL_SOURCE, "", ""

    row = max(
        enumerate(rows),
        key=lambda pair: (
            str(pair[1].get("recorded_at") or pair[1].get("updated_at") or ""),
            pair[0],
        ),
    )[1]
    names = normalize_room_type_names(
        row.get("room_type_names")
        or row.get("manual_room_type_names")
        or row.get("room_type_name")
    )
    source = str(row.get("source_table") or row.get("input_source") or _MANUAL_SOURCE)
    operator = str(row.get("operator") or "")
    recorded_at = str(row.get("recorded_at") or "")
    return names, source, operator, recorded_at


def _character_count(name: str) -> int:
    return len("".join(str(name or "").split()))


def _selling_point(name: str) -> str | None:
    return next((term for term in SELLING_POINT_TERMS if term in name), None)


def patch_manual_room_name_score(
    result: dict[str, Any],
    sections: dict[str, list[dict[str, Any]]],
) -> None:
    """Make item 11 an always-scored manual-input item."""

    item = _item(result, 11)
    if item is None:
        return

    names, source, operator, recorded_at = _latest_manual_names(sections)
    records: list[dict[str, Any]] = []
    failures: list[str] = []

    for name in names:
        count = _character_count(name)
        selling_point = _selling_point(name)
        passed = count > 5 and selling_point is not None
        if not passed:
            failures.append(name)
        records.append(
            {
                "room_type_name": name,
                "character_count": count,
                "selling_point": selling_point,
                "passed": passed,
            }
        )

    passed_all = bool(records) and not failures
    score_ratio = 1.0 if passed_all else 0.0
    base_score = float(item.get("base_score") or 4)

    item["participates_in_score"] = True
    item["score_ratio"] = score_ratio
    item["item_score"] = round(base_score * score_ratio, 2)
    item["data_status"] = "success" if passed_all else "zero"
    item["records"] = records
    item["fields"] = [
        {
            "label": record["room_type_name"],
            "value": record["character_count"],
            "origin": "人工输入评分",
            "note": (
                f"卖点表达：{record['selling_point'] or '未命中'}；"
                f"判定：{'通过' if record['passed'] else '不通过'}"
            ),
        }
        for record in records
    ]
    if not records:
        item["fields"] = [
            {
                "label": "人工输入状态",
                "value": "未输入",
                "origin": "人工输入评分",
                "note": "未提供房型名称，按0分计入总分",
            }
        ]

    item["source_table"] = source
    item["source_fields"] = [
        "manual_room_type_names",
        "字符数>5",
        "卖点表达命中",
    ]
    item["manual_input"] = {
        "room_type_names": names,
        "operator": operator,
        "recorded_at": recorded_at,
        "source": source,
    }

    if not records:
        item["note"] = (
            "本项必须评分：未收到人工输入的房型名称，按0分计入总分。"
            "可在网页输入，或在飞书发送“房型名称：五人战队套房、电竞双床房”。"
        )
    elif failures:
        item["note"] = (
            "本项必须评分且采用全有或全无规则：每个房型名称必须严格大于5个字，"
            "并命中至少一个卖点表达；以下房型未通过，整项得0分："
            + "、".join(failures)
        )
    else:
        item["note"] = (
            "所有人工输入房型名称均严格大于5个字且包含卖点表达，评分比例100%，"
            f"本项得满分{base_score:g}分。"
        )


__all__ = [
    "SELLING_POINT_TERMS",
    "normalize_room_type_names",
    "parse_room_type_names_from_text",
    "patch_manual_room_name_score",
]
