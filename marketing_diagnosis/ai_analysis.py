from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.request
from typing import Any

SECTION_PROMPTS = {
    "overview": "总览分析：先给一句经营判断，再说明最高风险来源。必须引用综合分、风险等级、核心经营指标，不要空泛表扬。",
    "metrics": "经营指标分析：围绕 RevPAR、ADR、出租率、收入拆解。判断是价格问题、入住问题还是收益结构问题。",
    "funnel": "流量漏斗分析：按曝光→浏览→支付订单→销售额分析路径断点。必须指出是流量不足、点击不足还是下单转化不足。",
    "modules": "模块联动分析：把 M01-M08 按 PMS、渠道、价格、推广、口碑、数据质量分组解释，不要只复述分数。",
    "channels": "分渠道分析：分别评价 PMS、每个 OTA 渠道。比较曝光、浏览、支付、销售额、评分、差评率，给每个渠道一条动作建议。",
    "price": "价格分析：看最低价、最高价、价格跨度、团购/钟点房/活动价。说明是否价格梯度混乱或引流价不足。",
    "missing": "数据完整度分析：说明缺失字段会影响哪些结论，按优先级给补采建议。不要把缺字段说成经营差。",
    "actions": "动作优先级分析：输出 3-5 条可执行动作，按先数据、再页面/价格、再推广/口碑排序。",
}


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
        "你必须只返回 JSON，不要 Markdown。字段必须为：overview, metrics, funnel, modules, channels, price, missing, actions。"
        "每个字段是中文字符串数组，每条 1-2 句话。必须基于输入数据，不允许编造不存在的字段、金额、订单、渠道、活动或结论。"
        "优先使用具体数字和对比关系，避免空话，例如不要写‘持续优化’，要写‘优先补齐推广 ROI 字段后再判断投放效率’。"
    )


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "instruction": _schema_hint(),
        "section_prompts": SECTION_PROMPTS,
        "report": _compact_result(result),
    }


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
    url = base_url if base_url.endswith("/chat/completions") else base_url + "/chat/completions"
    body = {
        "model": model,
        "temperature": float(os.environ.get("S14_AI_TEMPERATURE", "0.2")),
        "messages": [
            {"role": "system", "content": "你是酒店 OTA 经营诊断专家，擅长 PMS、OTA 漏斗、价格、活动推广、口碑和数据质量诊断。" + _schema_hint()},
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
    content = data["choices"][0]["message"]["content"].strip()
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
            f"{platform}：曝光 {_plain(item.get('exposure'))}，浏览 {_plain(item.get('views'))}，支付订单 {_plain(item.get('paid_orders'))}，销售额 {_money(item.get('sales_revenue'))}，浏览支付转化率 {_pct(item.get('payment_conversion_rate'))}。"
        )
    if not channel_lines:
        channel_lines.append("当前分渠道漏斗数据不足，无法判断各 OTA 渠道差异；需要补齐平台维度的曝光、浏览、支付订单和销售额。")
    return {
        "source": "rule_based_fallback_no_ai_config",
        "overview": [
            f"综合评分 {result.get('final_score')}/100，风险等级 {result.get('risk_level')}。先看 PMS 经营收益、OTA 转化断点和口碑信任三个核心层。",
            f"当前周期 RevPAR {_money(op.get('revpar'))}，ADR {_money(op.get('adr'))}，出租率 {_pct(op.get('occupancy_rate'))}；如果 RevPAR 弱，应拆成价格和入住两条线排查。",
        ],
        "metrics": [
            f"经营指标按所选周期聚合，出租率为总售出间夜除以总可售房晚；当前出租率 {_pct(op.get('occupancy_rate'))}。",
            f"门店收入 {_money(op.get('room_revenue'))}，RevPAR {_money(op.get('revpar'))}，ADR {_money(op.get('adr'))}；三者要一起看，不能只看房价。",
        ],
        "funnel": [
            f"曝光 {_plain(funnel.get('exposure'))}，浏览 {_plain(funnel.get('views'))}，支付订单 {_plain(funnel.get('paid_orders'))}，销售额 {_money(funnel.get('sales_revenue'))}。",
            f"曝光到浏览转化率 {_pct(funnel.get('exposure_to_view_rate'))}，浏览到支付转化率 {_pct(funnel.get('payment_conversion_rate'))}；如果浏览充足但支付弱，优先检查价格梯度、评价和取消政策。",
        ],
        "modules": [
            "模块诊断已拆为 PMS、各 OTA 渠道和系统/数据质量层：PMS 看经营收益，渠道看流量/转化/口碑/商品，系统层看数据完整度和执行闭环。",
            "data_gap 或 partial 模块不能当作真实经营差，只能说明当前数据不足或字段口径不完整。",
        ],
        "channels": channel_lines,
        "price": [
            f"商品数 {_plain(price.get('product_count'))}，最低价 {_money(price.get('min_price'))}，最高价 {_money(price.get('max_price'))}；需要检查引流价、全日价、团购价和钟点房价是否混乱。",
            f"活动数 {_plain(promo.get('activity_count'))}，活动覆盖已接入，但推广成本、点击、推广订单、推广收入和 ROI 仍未完整接入。",
        ],
        "missing": ["补采提示只展示影响结论可信度的关键字段；缺字段不是经营差，但会让模块分数偏保守。"],
        "actions": [
            f"平台评分 {_plain(rep.get('rating_avg'))}，差评率 {_pct(rep.get('negative_review_rate'))}；先把高频差评关键词转成页面卖点和服务整改清单。",
            f"未来 60 天周边活动数 {_plain(events.get('upcoming_60d_count'))}，可作为需求判断辅助，但不能替代订单和价格数据。",
            "优先级建议：先补齐推广 ROI 和页面内容字段，再处理渠道低转化，再做活动/价格策略。",
        ],
    }


def build_ai_analysis(result: dict[str, Any]) -> dict[str, Any]:
    timeout = int(os.environ.get("S14_AI_ANALYSIS_TIMEOUT", "20"))
    payload = _payload(result)
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
    return _fallback(result)
