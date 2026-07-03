from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.request
from typing import Any

AI_FIELDS = [
    "overview", "metrics", "funnel", "modules", "channels", "price",
    "promotion", "page", "reputation", "revpar", "contribution",
    "quadrant", "opportunity", "cap", "rules", "optimization",
    "missing", "actions",
]

REFERENCE_FRAMEWORK = {
    "source": "Xhotel门店数字运营首月诊断方案抽象框架",
    "report_structure": ["门店运营管理数据分析", "门店运营管理现状反馈", "门店运营管理提升实施方案"],
    "diagnosis_chain": [
        "PMS经营底盘：出租率、营收、ADR、RevPAR，判断收益问题来自入住率、房价还是结构。",
        "评分规则：8个主模块、41类评分规则、总分封顶和整改效果校验要分层输出。",
        "封顶规则：RevPAR低、收入下滑、订单和转化双弱、推广ROI缺失、关键字段缺失时，总分不能虚高。",
        "渠道贡献矩阵：按曝光占比、浏览占比、订单占比、销售额占比、客单价、二转和评分判断主力渠道与短板渠道。",
        "渠道效率四象限：高流量高转化放大，低流量高转化加曝光，高流量低转化修页面/价格/口碑，低流量低转化先补基础。",
        "OTA漏斗：曝光、浏览、一转、二转、支付订单、销售额；优先定位是曝光不足、一转弱还是二转低。",
        "推广效率：推广订单金额、推广花费、ROI、活动覆盖和明细完整度要分开，不得用活动覆盖替代ROI。",
        "页面入口：图片、视频、房型卖点、入口标签会影响一转和二转；没有字段时必须标记待采集。",
        "口碑信任：分平台看评分、评论量、差评率、未回复，评价量小不能只因评分高就判断稳定。",
        "价格房型：看最低价、最高价、价格跨度、团购、钟点房、远期价格铺设和竞对价差。",
        "机会点测算：只能作为流量×转化×客单价的试算，不得表述为承诺结果或已发生结果。",
        "整改校验：分数提升必须结合订单、RevPAR和收入变化判断，不能只看报告分数。",
    ],
}

SECTION_PROMPTS = {
    "overview": "总览分析：判断是经营底盘、渠道流量、转化、价格房型还是数据缺口问题，必须引用综合分、风险等级、RevPAR/ADR/出租率/核心渠道结果。",
    "metrics": "经营指标分析：拆 RevPAR、ADR、出租率、收入，判断收益短板来自入住率不足、房价不足、房型结构还是渠道结构。",
    "revpar": "RevPAR拆解分析：围绕 RevPAR=ADR×出租率，判断是价格问题、入住问题还是两者叠加，并给优先排查方向。",
    "contribution": "渠道贡献矩阵分析：比较曝光占比、浏览占比、订单占比、销售额占比、客单价、二转、评分，指出主渠道、补充渠道和待补数据渠道。",
    "quadrant": "渠道效率四象限分析：按流量和转化把渠道分成主力放大、加曝光、修转化、暂缓投放，并说明动作优先级。",
    "opportunity": "机会点测算分析：基于当前曝光、浏览、转化、客单价做保守测算，必须声明是测算，不是承诺。",
    "funnel": "流量漏斗分析：按曝光→浏览→一转→二转/支付订单→销售额定位断点，明确是曝光不足、一转弱、二转低还是订单金额弱。",
    "modules": "模块联动分析：按 PMS、OTA渠道、价格房型、推广、页面、口碑、系统数据质量分组解释，不要只复述分数。",
    "channels": "分渠道分析：分别评价每个 OTA 渠道，比较曝光、浏览、支付、销售额、评分、差评率、商品/活动覆盖。",
    "price": "价格分析：看最低价、最高价、价格跨度、团购/钟点房/活动价、远期价格铺设和竞对价格承受力。",
    "promotion": "推广效率分析：必须区分活动覆盖和投放效率。没有推广订单金额、推广花费、ROI时，只能说ROI无法判断，不能说推广效果好或差。",
    "page": "页面展示与入口分析：围绕图片质量、视频状态、房型卖点、入口标签判断页面基础。字段未知时必须明确待采集。",
    "reputation": "口碑分析：按渠道看评分、总评价、好评、差评、未回复。评价数量过少时，不能只因评分高就判定口碑稳。",
    "cap": "封顶校准分析：解释原始分、封顶线、最终分和触发规则。封顶是防失真校准，不是普通扣分。",
    "rules": "评分规则分析：说明哪些规则命中、哪些模块低分、证据字段是什么，避免只展示一个总分。",
    "optimization": "整改复盘分析：说明后续要如何用动作日志、整改前后订单/收入/RevPAR校验是否真正有效。",
    "missing": "数据完整度分析：说明缺失字段会影响哪些结论，按优先级给补采建议，不要把缺字段说成经营差。",
    "actions": "动作优先级分析：输出3-5条可执行动作，按先补数据/页面包装→主渠道流量曝光→二转优化→远期价格铺设→推广复盘排序。",
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
        "score_before_cap": result.get("score_before_cap"),
        "cap_score": result.get("cap_score"),
        "cap_applied": result.get("cap_applied"),
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
        "rule_hits": result.get("rule_hits"),
        "cap_rules_triggered": result.get("cap_rules_triggered"),
        "optimization_checks": result.get("optimization_checks"),
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
        "输出要像酒店运营顾问，不像通用AI；必须围绕订单量=流量×转化、PMS经营底盘、OTA漏斗、渠道贡献、四象限、封顶校准、推广ROI、页面包装、口碑、价格房型。"
    )


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    return {"instruction": _schema_hint(), "reference_framework": REFERENCE_FRAMEWORK, "section_prompts": SECTION_PROMPTS, "report": _compact_result(result)}


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
    cap_lines = []
    for item in result.get("cap_rules_triggered") or []:
        cap_lines.append(f"触发{item.get('cap_id')}：{item.get('name')}，封顶{item.get('cap_score')}分，证据：{item.get('evidence')}。")
    if not cap_lines:
        cap_lines.append("当前未触发强封顶规则，但仍需要人工复核经营指标和字段完整度。")
    return {
        "source": "rule_based_fallback_no_ai_config",
        "overview": [f"原始分 {result.get('score_before_cap')}/100，最终分 {result.get('final_score')}/100，风险等级 {result.get('risk_level')}。先看 PMS 经营底盘，再看主渠道流量、二转、价格房型和口碑。", f"当前周期 RevPAR {_money(op.get('revpar'))}，ADR {_money(op.get('adr'))}，出租率 {_pct(op.get('occupancy_rate'))}。"],
        "metrics": [f"经营指标按所选周期聚合，出租率为总售出间夜除以总可售房晚；当前出租率 {_pct(op.get('occupancy_rate'))}。"],
        "revpar": [f"RevPAR {_money(op.get('revpar'))} = ADR {_money(op.get('adr'))} × 出租率 {_pct(op.get('occupancy_rate'))}；先判断是价格问题还是入住问题。"],
        "contribution": ["渠道贡献矩阵用于比较曝光占比、订单占比、销售额占比和客单价；不要只按曝光量判断渠道价值。"],
        "quadrant": ["四象限用于决定渠道动作：高流量低转化先修转化，低流量高转化先加曝光。"],
        "opportunity": ["机会点为测算，不是承诺；用于判断优先提升曝光、一转、二转还是客单价。"],
        "cap": cap_lines,
        "rules": [f"当前命中规则数 {len(result.get('rule_hits') or [])}，应优先解释低分模块和data_gap/partial模块，而不是只看总分。"],
        "optimization": ["整改复盘需要动作日志和前后指标；分数提升但订单、收入或RevPAR不提升，不能算有效优化。"],
        "funnel": [f"订单量=流量×转化。当前曝光 {_plain(funnel.get('exposure'))}，浏览 {_plain(funnel.get('views'))}，支付订单 {_plain(funnel.get('paid_orders'))}。"],
        "modules": ["模块诊断已拆为 PMS、各 OTA 渠道和系统/数据质量层。"],
        "channels": channel_lines,
        "price": [f"商品数 {_plain(price.get('product_count'))}，最低价 {_money(price.get('min_price'))}，最高价 {_money(price.get('max_price'))}；需检查引流价、团购价、钟点房和远期价。"],
        "promotion": [f"活动数 {_plain(promo.get('activity_count'))}，活动商品数 {_plain(promo.get('activity_product_count'))}；推广成本、点击、推广订单、推广收入和 ROI 未完整接入时，不能判断投放效率。"],
        "page": ["图片质量、视频状态、房型卖点和入口标签需要结构化采集；字段未知时只能标记待补齐。"],
        "reputation": [f"平台评分 {_plain(rep.get('rating_avg'))}，评价数 {_plain(rep.get('review_count'))}，差评率 {_pct(rep.get('negative_review_rate'))}；评价量太小时不能只因评分高就判断口碑稳定。"],
        "missing": ["缺字段不是经营差，但会降低结论可信度，尤其影响推广ROI、页面包装、竞对和远期价判断。"],
        "actions": [f"未来60天周边活动数 {_plain(events.get('upcoming_60d_count'))} 可辅助需求判断；优先补数据和页面，再做渠道曝光、二转和推广复盘。"],
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
