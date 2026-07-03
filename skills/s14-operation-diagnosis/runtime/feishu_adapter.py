from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _num(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _fmt_num(value: Any, digits: int = 1) -> str:
    number = _num(value)
    if number is None:
        return "未获取"
    return f"{number:,.{digits}f}"


def _money(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "未获取"
    return f"¥{number:,.1f}"


def _pct(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "未获取"
    return f"{number:.1%}"


def _risk_zh(value: Any) -> str:
    return {"high": "高风险", "medium": "中等风险", "low": "低风险"}.get(str(value or "").lower(), _text(value) or "未知风险")


def _risk_icon(value: Any) -> str:
    return {"high": "🔴", "medium": "⚠️", "low": "🟢"}.get(str(value or "").lower(), "⚪")


def _platform_zh(value: Any) -> str:
    text = str(value or "multi").lower()
    return {"multi": "多渠道", "meituan": "美团", "ctrip": "携程", "fliggy": "飞猪"}.get(text, _text(value) or "多渠道")


def _hotel_label(result: dict[str, Any]) -> str:
    hotel_id = result.get("hotel_id") or "puyue"
    hotel_name = result.get("hotel_name") or ("璞悦" if hotel_id == "puyue" else hotel_id)
    return f"{hotel_name}（{hotel_id}）"


def _period_label(result: dict[str, Any]) -> str:
    start = result.get("period_start") or "未获取"
    end = result.get("period_end") or "未获取"
    return f"最近 30 天（{start} ~ {end}）"


def _module_lines(result: dict[str, Any], limit: int = 4) -> list[str]:
    modules = result.get("module_scores") or []
    ranked = sorted(modules, key=lambda item: (_num(item.get("rate")) if _num(item.get("rate")) is not None else -1))
    lines: list[str] = []
    for item in ranked[:limit]:
        mid = item.get("module_id") or "M??"
        name = item.get("module_name") or mid
        score = _fmt_num(item.get("score"), 1)
        weight = _fmt_num(item.get("weight"), 0)
        status = item.get("status") or "ok"
        label = "数据缺口" if status == "data_gap" else f"{score}/{weight}"
        lines.append(f"- {mid} {name}：{label}")
    return lines


def _source_summary(result: dict[str, Any]) -> str:
    dq = result.get("data_quality") or {}
    tables = []
    for source in dq.get("source_diagnostics") or []:
        for key, diag in (source.get("tables") or {}).items():
            if diag.get("status") == "ok":
                tables.append(f"{key}:{diag.get('rows', 0)}行")
    if not tables:
        return "数据来源：未核验到有效表"
    return "数据来源：" + "，".join(tables[:6])


def _data_gap_summary(result: dict[str, Any]) -> str:
    modules = [item.get("module_id") for item in result.get("module_scores") or [] if item.get("status") == "data_gap"]
    if not modules:
        return "数据完整度：关键模块已接入"
    return "数据缺口：" + "、".join(str(x) for x in modules if x)


def _metric_lines(result: dict[str, Any]) -> list[str]:
    metrics = result.get("metrics") or {}
    op = metrics.get("operating") or {}
    funnel = metrics.get("ota_funnel") or {}
    rep = metrics.get("reputation") or {}
    return [
        f"- RevPAR：{_money(op.get('revpar'))}｜ADR：{_money(op.get('adr'))}｜出租率：{_pct(op.get('occupancy_rate'))}",
        f"- 曝光：{_fmt_num(funnel.get('exposure'), 0)}｜浏览：{_fmt_num(funnel.get('views'), 0)}｜支付订单：{_fmt_num(funnel.get('paid_orders'), 0)}｜转化率：{_pct(funnel.get('payment_conversion_rate'))}",
        f"- 评价数：{_fmt_num(rep.get('review_count'), 0)}｜评分：{_fmt_num(rep.get('rating_avg'), 2)}｜差评率：{_pct(rep.get('negative_review_rate'))}",
    ]


def build_feishu_reply(result: dict[str, Any]) -> str:
    score = _fmt_num(result.get("final_score"), 1)
    risk = result.get("risk_level") or "-"
    report_url = result.get("report_url", "")
    notes = result.get("notes") or []
    lines = [
        "🎯 S14 诊断报告已生成",
        f"酒店：{_hotel_label(result)}｜渠道：{_platform_zh(result.get('platform'))}｜周期：{_period_label(result)}",
        f"📊 综合评分：{score}/100 {_risk_icon(risk)} {_risk_zh(risk)}",
        "",
        "📌 经营概况：",
        *_metric_lines(result),
        f"- {_source_summary(result)}",
        f"- {_data_gap_summary(result)}",
        "",
        "⚠️ 重点关注：",
    ]
    for item in notes[:5]:
        lines.append(f"- {item.get('title')}：{item.get('suggestion')}")
    if not notes:
        lines.append("- 暂无高优先级风险。")
    lines.extend([
        "",
        f"📄 HTML 报告链接：{report_url}" if report_url else "📄 HTML 报告链接：未生成公开链接",
        "点击「打开 HTML 报告」按钮可查看完整诊断详情。",
    ])
    return "\n".join(lines)


def build_feishu_card_reply(result: dict[str, Any]) -> dict[str, Any]:
    score = _fmt_num(result.get("final_score"), 1)
    risk = result.get("risk_level") or "-"
    report_url = _text(result.get("report_url", ""))
    summary = "\n".join(_metric_lines(result))
    attention = "\n".join(_module_lines(result))
    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**酒店：** {_hotel_label(result)}\n**渠道：** {_platform_zh(result.get('platform'))}\n**周期：** {_period_label(result)}"}},
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**综合评分：** {score}/100 {_risk_icon(risk)} {_risk_zh(risk)}"}},
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**经营概况**\n{summary}"}},
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**数据核验**\n- {_source_summary(result)}\n- {_data_gap_summary(result)}"}},
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**重点关注**\n{attention or '- 暂无'}"}},
    ]
    if report_url:
        elements.append({"tag": "action", "actions": [{"tag": "button", "text": {"tag": "plain_text", "content": "打开 HTML 报告"}, "type": "primary", "url": report_url}]})
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"template": "blue", "title": {"tag": "plain_text", "content": "S14 OTA营销诊断报告"}},
            "elements": elements,
        },
    }
