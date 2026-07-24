from __future__ import annotations

import html
import re
from typing import Any, Callable

from marketing_diagnosis import reporting_runtime_v51 as runtime


_CARD_PATTERN = re.compile(
    r"<div class=(?P<q>['\"])hero-stat(?P=q)>"
    r"<small>(?P<label>折算得分|原始得分|已接入基础分|未取到数据)</small>"
    r"<strong>.*?</strong><em>.*?</em></div>",
    re.DOTALL,
)
_NOTICE = "报告中的每项数据均展示来源表和字段；查询失败、空结果和真实0分别处理。"
_NEW_NOTICE = "美团诊断总分等于所有参与计分模块当前得分之和；展示项不计分，待接入计分项不按0分代入。"


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _format_number(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "待计算"
    return f"{number:g}"


def rewrite_meituan_total(document: str, result: dict[str, Any]) -> str:
    visual = result.get("visual_diagnosis")
    if not isinstance(visual, dict):
        return document

    cards = {
        "折算得分": (
            "诊断总分",
            _format_number(visual.get("total_score", visual.get("raw_score"))),
            "所有参与计分模块得分加和",
        ),
        "原始得分": (
            "已计分模块",
            f"{int(visual.get('scored_items') or 0)}/{int(visual.get('scoring_items') or 0)}项",
            "仅统计已形成得分的计分模块",
        ),
        "已接入基础分": (
            "总满分",
            _format_number(visual.get("full_score", visual.get("connected_base_score"))),
            "所有参与计分模块满分合计",
        ),
        "未取到数据": (
            "待接入计分项",
            f"{int(visual.get('pending_items') or 0)}项",
            "保持待计算，不按0分代入",
        ),
    }

    def replace(match: re.Match[str]) -> str:
        label, value, note = cards[match.group("label")]
        quote = match.group("q")
        return (
            f"<div class={quote}hero-stat{quote}>"
            f"<small>{html.escape(label)}</small>"
            f"<strong>{html.escape(value)}</strong>"
            f"<em>{html.escape(note)}</em></div>"
        )

    document = _CARD_PATTERN.sub(replace, document, count=4)
    return document.replace(_NOTICE, _NEW_NOTICE, 1)


def _install() -> None:
    if hasattr(runtime, "_meituan_direct_total_original_build_html"):
        return

    original: Callable[[dict[str, Any]], str] = runtime.build_html
    runtime._meituan_direct_total_original_build_html = original

    def build_html(result: dict[str, Any]) -> str:
        return rewrite_meituan_total(original(result), result)

    runtime.build_html = build_html


_install()


__all__ = ["rewrite_meituan_total"]
