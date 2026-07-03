from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.request
from typing import Any

AI_FIELDS = ["overview", "metrics", "funnel", "modules", "channels", "price", "promotion", "page", "reputation", "missing", "actions"]

REFERENCE_FRAMEWORK = {
    "source": "Xhotel门店数字运营首月诊断方案抽象框架",
    "report_structure": ["门店运营管理数据分析", "门店运营管理现状反馈", "门店运营管理提升实施方案"],
    "diagnosis_chain": [
        "PMS经营底盘：近6个月/近30天出租率、营收、ADR、RevPAR，判断收益问题来自入住率、房价还是结构。",
        "渠道结构：会员、协议、其他、OTA、散客占比，判断是否过度依赖OTA、是否需要补会员和私域。",
        "核心渠道订单：按渠道看订单数、订单金额、销售额，识别绝对贡献渠道和增长空间。",
        "OTA漏斗：曝光、浏览、一转、二转、支付订单、销售额；优先定位是曝光不足、一转弱还是二转低。",
        "竞对参照：和商圈竞对比较曝光、浏览、转化、订单、均价和总额，不只看自身环比。",
        "HOS/平台健康：关注HOS得分、预定间夜排名、营业额排名、完整订单占比、确认率、商品可订率等平台质量项。",
        "推广效率：推广通/全域通/广告曝光要看曝光、点击、点击率、转化、预订单、预定间夜、预定金额，不能只有活动覆盖。",
        "页面入口：图片、视频、房型卖点、入口标签会影响一转和二转；没有页面字段时必须标记为待采集。",
        "口碑信任：分平台看评分、评论量、差评率、未回复，差评关键词要转化为页面卖点和服务整改动作。",
        "价格房型：看主渠道外网展示、核心竞对价格日历、远期价格铺设、引流价、团购价、钟点房、活动价一致性。",
    ],
    "first_stage_problem_taxonomy": ["补充广告曝光", "二转转化低", "远期价格铺设不合理", "产品包装不足", "推广ROI缺失", "页面内容缺失"],
    "action_logic": [
        "订单量 = 流量 × 转化率；流量拆自然流量和广告流量，转化率重点看二转。",
        "第一阶段先聚焦主渠道，尤其是美团：后台活动优化 + 推广通/全域通 + 页面包装 + 二转优化。",
        "转化率提升目标可用10%-15%作为试跑期目标，但只能在报告中标记为运营目标，不当作已发生结果。",
        "先补数据和页面包装，再做渠道投放，再复盘订单/营收/RevPAR变化。",
    ],
}

SECTION_PROMPTS = {
    "overview": "总览分析：先判断门店处于经营底盘问题、渠道流量问题、转化问题、价格房型问题还是数据缺口问题。必须引用综合分、风险等级、RevPAR/ADR/出租率/核心渠道结果。",
    "metrics": "经营指标分析：按 PMS 经营底盘拆 RevPAR、ADR、出租率、收入。判断收益短板来自入住率不足、房价不足、房型结构还是渠道结构。",
    "funnel": "流量漏斗分析：按曝光→浏览→一转→二转/支付订单→销售额定位断点。必须明确是曝光不足、一转弱、二转低还是订单金额弱。",
    "modules": "模块联动分析：按 PMS、OTA渠道、价格房型、推广、页面、口碑、系统数据质量分组解释，不要只复述分数。",
    "channels": "分渠道分析：分别评价 PMS、每个 OTA 渠道。比较曝光、浏览、支付、销售额、评分、差评率、商品/活动覆盖。",
    "price": "价格分析：看最低价、最高价、价格跨度、团购/钟点房/活动价、远期价格铺设和竞对价格承受力。",
    "promotion": "推广效率分析：必须区分活动覆盖和投放效率。没有推广订单金额、推广花费、ROI时，只能说ROI无法判断，不能说推广效果好或差。",
    "page": "页面展示与入口分析：围绕图片质量、视频状态、房型卖点、入口标签判断页面基础。字段未知时必须明确待采集，不得凭空判断页面好坏。",
    "reputation": "口碑分析：按渠道看评分、总评价、好评、差评、未回复。评价数量过少时，不能只因评分高就判定口碑稳。",
    "missing": "数据完整度分析：说明缺失字段会影响哪些结论，按优先级给补采建议。不要把缺字段说成经营差。",
    "actions": "动作优先级分析：输出3-5条可执行动作。按先补数据/页面包装→主渠道流量曝光→二转优化→远期价格铺设→推广复盘排序，并给可验证指标。",
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
    fields = ", ".join(AI_FIELDS)
    return (
        f"你必须只返回 JSON，不要 Markdown。字段必须为：{fields}。"
        "每个字段是中文字符串数组，每条1-2句话。必须基于输入数据，不允许编造不存在的字段、金额、订单、渠道、活动或结论。"
        "输出要像酒店运营顾问，不像通用AI：必须围绕订单量=流量×转化、PMS经营底盘、OTA漏斗、竞对、HOS、推广ROI、页面包装、口碑、价格房型。"
        "如使用10%-15%转化提升目标，只能表述为试跑目标或建议，不得表述为已实现。"
    )


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "instruction": _schema_hint(),
        "reference_framework": REFERENCE_FRAMEWORK,
        "section_prompts": SECTION_PROMPTS,
        "report": _compact_result(result),
    }


def _from_command(payload: dict[str, Any], timeout: int) -> dict[str, Any] | None:
    command = os.environ.get("S14_AI_ANALYSIS_CMD")
    if not command:
        return None
    proc = subprocess.run(shlex.split(command), input=json.dumps(payload, ensure_ascii=False), text=True, capture_output=True, timeout=timeout, check=False)
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
            {"role": "system", "content": "你是酒店 OTA 经营诊断专家，擅长 PMS、OTA 漏斗、竞对、HOS、价格房型、推广通/全域通、页面包装、口碑和数据质量诊断。" + _schema_hint()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
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
        channel_lines.append(f"{platform}：曝光 {_plain(item.get('exposure'))}，浏览 {_plain(item.get('views'))}，支付订单 {_plain(item.get('paid_orders'))}，销售额 {_money(item.get('sales_revenue'))}，浏览支付转化率 {_pct(item.get('payment_conversion_rate'))}。")
    if not channel_lines:
        channel_lines.append("当前分渠道漏斗数据不足，无法判断各 OTA 渠道差异；需要补齐平台维度的曝光、浏览、支付订单和销售额。")
    return {
        "source": "rule_based_fallback_no_ai_config",
        "overview": [f"综合评分 {result.get('final_score')}/100，风险等级 {result.get('risk_level')}。按首月诊断框架，先看 PMS 经营底盘，再看主渠道流量、二转、价格房型和口碑。", f"当前周期 RevPAR {_money(op.get('revpar'))}，ADR {_money(op.get('adr'))}，出租率 {_pct(op.get('occupancy_rate'))}；如果 RevPAR 弱，应拆成价格、入住率和渠道结构三条线排查。"],
        "metrics": [f"经营指标按所选周期聚合，出租率为总售出间夜除以总可售房晚；当前出租率 {_pct(op.get('occupancy_rate'))}。", f"门店收入 {_money(op.get('room_revenue'))}，RevPAR {_money(op.get('revpar'))}，ADR {_money(op.get('adr'))}；三者要一起看，不能只看房价。"],
        "funnel": [f"订单量=流量×转化。当前曝光 {_plain(funnel.get('exposure'))}，浏览 {_plain(funnel.get('views'))}，支付订单 {_plain(funnel.get('paid_orders'))}，销售额 {_money(funnel.get('sales_revenue'))}。", f"曝光到浏览转化率 {_pct(funnel.get('exposure_to_view_rate'))}，浏览到支付转化率 {_pct(funnel.get('payment_conversion_rate'))}；如果浏览充足但支付弱，优先处理二转、价格梯度、评价和取消政策。"],
        "modules": ["模块诊断已拆为 PMS、各 OTA 渠道和系统/数据质量层：PMS 看经营收益，渠道看流量/转化/口碑/商品，系统层看数据完整度和执行闭环。", "参考首月诊断框架，优先归类为补充广告曝光、二转转化低、远期价格铺设不合理、产品包装不足四类问题。"],
        "channels": channel_lines,
        "price": [f"商品数 {_plain(price.get('product_count'))}，最低价 {_money(price.get('min_price'))}，最高价 {_money(price.get('max_price'))}；需要检查引流价、全日价、团购价、钟点房价和远期价铺设是否混乱。"],
        "promotion": [f"活动数 {_plain(promo.get('activity_count'))}，活动商品数 {_plain(promo.get('activity_product_count'))}；推广成本、点击、推广订单、推广收入和 ROI 未完整接入时，不能判断推广通/全域通投放效率。"],
        "page": ["图片质量、视频状态、房型卖点和入口标签目前需要结构化采集；在字段未知时，只能标记为页面基础待补齐。"],
        "reputation": [f"平台评分 {_plain(rep.get('rating_avg'))}，评价数 {_plain(rep.get('review_count'))}，差评率 {_pct(rep.get('negative_review_rate'))}，未回复 {_plain(rep.get('unreplied_review_count'))}；评价量太小时不能只因评分高就判断口碑稳定。"],
        "missing": ["补采提示只展示影响结论可信度的关键字段；缺字段不是经营差，但会让模块分数偏保守，尤其影响推广ROI、竞对和页面包装判断。"],
        "actions": [f"未来 60 天周边活动数 {_plain(events.get('upcoming_60d_count'))}，可作为需求判断辅助，但不能替代订单和价格数据。", "优先级建议：先补齐推广 ROI 和页面内容字段，再做主渠道流量曝光和二转优化，最后复盘订单、营收和 RevPAR。"],
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
