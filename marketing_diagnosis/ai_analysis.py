from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.request
from typing import Any


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        number = float(value)
        return None if number != number else number
    except (TypeError, ValueError):
        return None


def _pct(value: Any) -> str:
    number = _num(value)
    return "未获取" if number is None else f"{number:.1%}"


def _money(value: Any) -> str:
    number = _num(value)
    return "未获取" if number is None else f"¥{number:,.1f}"


def _plain(value: Any) -> str:
    return "未获取" if value is None else str(value)


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    metrics = result.get("metrics") or {}
    return {
        "final_score": result.get("final_score"),
        "risk_level": result.get("risk_level"),
        "status": result.get("status"),
        "hotel_id": result.get("hotel_id"),
        "hotel_name": result.get("hotel_name"),
        "platform": result.get("platform"),
        "period_start": result.get("period_start"),
        "period_end": result.get("period_end"),
        "metrics": {
            "operating": metrics.get("operating"),
            "ota_funnel": metrics.get("ota_funnel"),
            "price_ladder": metrics.get("price_ladder"),
            "promotion": metrics.get("promotion"),
            "reputation": metrics.get("reputation"),
            "nearby_events": metrics.get("nearby_events"),
            "competitors": metrics.get("competitors"),
        },
        "module_scores": result.get("module_scores"),
        "notes": result.get("notes"),
        "actions": result.get("actions"),
        "data_quality_summary": {
            "status": (result.get("data_quality") or {}).get("status"),
            "missing_fields": (result.get("data_quality") or {}).get("missing_fields"),
            "empty_sections": (result.get("data_quality") or {}).get("empty_sections"),
        },
    }


def _schema_hint() -> str:
    return (
        "只返回 JSON，不要 Markdown。字段必须为："
        "overview, metrics, funnel, modules, channels, price, missing, actions。"
        "每个字段是中文字符串数组，每条 1-2 句话。"
        "要求基于输入数据，不允许编造不存在的字段、金额、订单或渠道。"
    )


def _from_command(payload: dict[str, Any], timeout: int) -> dict[str, Any] | None:
    command = os.environ.get("S14_AI_ANALYSIS_CMD")
    if not command:
        return None
    proc = subprocess.run(
        shlex.split(command),
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or f"command exited {proc.returncode}")[:1000])
    return json.loads(proc.stdout)


def _from_openai_compatible(payload: dict[str, Any], timeout: int) -> dict[str, Any] | None:
    api_key = os.environ.get("S14_AI_API_KEY")
    base_url = (os.environ.get("S14_AI_BASE_URL") or "").rstrip("/")
    model = os.environ.get("S14_AI_MODEL")
    if not (api_key and base_url and model):
        return None
    url = base_url
    if not url.endswith("/chat/completions"):
        url = url + "/chat/completions"
    body = {
        "model": model,
        "temperature": float(os.environ.get("S14_AI_TEMPERATURE", "0.2")),
        "messages": [
            {"role": "system", "content": "你是酒店 OTA 运营诊断分析师。" + _schema_hint()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    content = data["choices"][0]["message"]["content"]
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    return json.loads(content)


def _fallback(result: dict[str, Any]) -> dict[str, Any]:
    metrics = result.get("metrics") or {}
    op = metrics.get("operating") or {}
    funnel = metrics.get("ota_funnel") or {}
    price = metrics.get("price_ladder") or {}
    promo = metrics.get("promotion") or {}
    rep = metrics.get("reputation") or {}
    events = metrics.get("nearby_events") or {}
    channels = funnel.get("by_platform") or []
    channel_lines = []
    for item in channels:
        platform = item.get("platform")
        channel_lines.append(
            f"{platform}：曝光 {_plain(item.get('exposure'))}，浏览 {_plain(item.get('views'))}，支付订单 {_plain(item.get('paid_orders'))}，浏览支付转化率 {_pct(item.get('payment_conversion_rate'))}。"
        )
    if not channel_lines:
        channel_lines.append("当前分渠道漏斗数据不足，无法判断各渠道差异。")
    return {
        "source": "rule_based_fallback",
        "overview": [
            f"综合评分 {result.get('final_score')}/100，风险等级 {result.get('risk_level')}。先看经营收益、转化断点和口碑信任三个核心模块。",
            f"当前周期 RevPAR {_money(op.get('revpar'))}，ADR {_money(op.get('adr'))}，出租率 {_pct(op.get('occupancy_rate'))}。",
        ],
        "metrics": [
            f"经营指标按所选周期聚合，出租率为总售出间夜除以总可售房晚；当前出租率 {_pct(op.get('occupancy_rate'))}。",
            f"门店收入 {_money(op.get('room_revenue'))}，RevPAR {_money(op.get('revpar'))}。",
        ],
        "funnel": [
            f"曝光 {_plain(funnel.get('exposure'))}，浏览 {_plain(funnel.get('views'))}，支付订单 {_plain(funnel.get('paid_orders'))}。",
            f"曝光到浏览转化率 {_pct(funnel.get('exposure_to_view_rate'))}，浏览到支付转化率 {_pct(funnel.get('payment_conversion_rate'))}。",
        ],
        "modules": ["模块分数来自真实字段计算；data_gap 模块不使用默认值冒充真实结论。"],
        "channels": channel_lines,
        "price": [
            f"商品数 {_plain(price.get('product_count'))}，最低价 {_money(price.get('min_price'))}，最高价 {_money(price.get('max_price'))}。",
            f"活动数 {_plain(promo.get('activity_count'))}，但推广 ROI 字段当前状态为 {promo.get('status')}。",
        ],
        "missing": ["补采提示只展示影响结论可信度的关键字段；补齐后应重新生成报告。"],
        "actions": [
            f"平台评分 {_plain(rep.get('rating_avg'))}，差评率 {_pct(rep.get('negative_review_rate'))}，可结合评价关键词优化页面卖点。",
            f"未来 60 天周边活动数 {_plain(events.get('upcoming_60d_count'))}，可作为需求判断辅助信息。",
        ],
    }


def build_ai_analysis(result: dict[str, Any]) -> dict[str, Any]:
    timeout = int(os.environ.get("S14_AI_ANALYSIS_TIMEOUT", "20"))
    payload = {"instruction": _schema_hint(), "report": _compact_result(result)}
    try:
        generated = _from_command(payload, timeout) or _from_openai_compatible(payload, timeout)
        if generated:
            generated["source"] = generated.get("source") or "ai"
            return generated
    except Exception as exc:
        fallback = _fallback(result)
        fallback["source"] = "rule_based_fallback_after_ai_error"
        fallback["error"] = str(exc)[:500]
        return fallback
    fallback = _fallback(result)
    fallback["source"] = "rule_based_fallback_no_ai_config"
    return fallback
