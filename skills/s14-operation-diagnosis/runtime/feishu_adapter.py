from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def build_feishu_reply(result: dict[str, Any]) -> str:
    score = result.get("final_score", "-")
    risk = result.get("risk_level", "-")
    report_url = result.get("report_url", "")
    notes = result.get("notes") or []
    lines = [
        f"S14 OTA营销诊断完成：{score}/100，风险等级 {risk}",
        f"HTML报告：{report_url}" if report_url else "HTML报告：未生成公开链接",
        "",
        "重点结论：",
    ]
    for item in notes[:5]:
        lines.append(f"- [{item.get('level')}] {item.get('title')}：{item.get('suggestion')}")
    return "\n".join(lines)


def build_feishu_card_reply(result: dict[str, Any]) -> dict[str, Any]:
    score = _text(result.get("final_score", "-"))
    risk = _text(result.get("risk_level", "-"))
    report_url = _text(result.get("report_url", ""))
    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**综合评分：** {score}/100\\n**风险等级：** {risk}"}},
    ]
    if report_url:
        elements.append({"tag": "action", "actions": [{"tag": "button", "text": {"tag": "plain_text", "content": "打开HTML报告"}, "type": "primary", "url": report_url}]})
    for item in (result.get("notes") or [])[:5]:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"- **{item.get('title')}**：{item.get('suggestion')}"}})
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"template": "blue", "title": {"tag": "plain_text", "content": "S14 OTA营销诊断报告"}},
            "elements": elements,
        },
    }
