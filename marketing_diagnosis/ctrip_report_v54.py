from __future__ import annotations

import copy
import html
import math
import re
from datetime import datetime
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v30, reporting_v35, reporting_v37
from marketing_diagnosis.ctrip_psi_v53 import STYLE as PSI_STYLE
from marketing_diagnosis.ctrip_psi_v53 import card as psi_card
from marketing_diagnosis.visual_diagnosis import build_visual_diagnosis


# no, title, full score (None = display only), period, description, source, field labels
SPECS = (
    (1, "月度经营趋势 YOY", 10, "近三个月", "展示房费、ADR、出租率、RevPAR及去年同期同比。", "PMS经营数据（与美团页面当前取数口径一致）", ()),
    (2, "房型 RevPAR 与低效房型", 8, "近30天", "按房型展示出租率、RevPAR及低效房型判定。", "PMS房型经营数据（与美团页面当前取数口径一致）", ()),
    (3, "平台流量漏斗分析", 15, "近30天", "展示曝光、访客、订单页和成交漏斗。", "携程 eBooking / 流量与转化", ("列表曝光", "APP访客", "订单页访客", "成交订单", "竞争圈排名")),
    (4, "用户来源画像", None, "近30天", "展示性别、年龄、本地异地、出行目的和预订习惯。", "携程 eBooking / 用户画像", ("性别", "年龄段", "本地 / 异地", "主要客源城市")),
    (5, "竞争圈分析", None, "近30天", "展示竞争圈排名、均值、流失订单和主要流失竞对。", "携程 eBooking / 竞争圈分析", ("竞争圈排名", "平均订单量", "流失订单量", "流失订单金额")),
    (6, "PSI 服务质量分", 8, "当前值", "展示基础分、九项分指标、项目权重和昨日变化。", "携程 eBooking / 服务质量分 / 基础分", ()),
    (7, "YOYO 卡 / 扫码住", 5, "近30天", "按近30天扫码订单换算日均扫码订单。", "携程 eBooking / YOYO卡或扫码住", ("近30天扫码订单", "日均扫码订单", "扫码新增会员", "促销状态")),
    (8, "信息完整度", 4, "当前值", "展示携程信息首页完整度及缺失项。", "携程 eBooking / 信息维护", ("信息完整度", "基础信息缺失", "政策缺失", "设施缺失")),
    (9, "推广数据：金字塔", 8, "近30天", "展示投入、曝光、点击、订单、成交金额和ROI。", "携程 eBooking / 金字塔推广", ("推广产品", "投入金额", "曝光量", "推广订单", "ROI")),
    (10, "页面展示和入口基础", 3, "最新快照", "检查门店后缀、地标商圈词、入口词及推荐词标签卖点。", "ctrip_ota_promotion_performance_30d.hotel_name", ("酒店展示名称", "门店后缀 / 地标商圈词", "命中入口词", "列表页推荐词 / 标签 / 卖点")),
    (11, "房型名称与售卖房型", 4, "最新快照", "展示售卖商品、房型名称合格数和合格占比。", "ctrip_ota_goods_price_mapping", ("售卖商品数", "售卖房型数", "合格房型", "合格房型占比")),
    (12, "口碑分析", 10, "当前值", "按携程、去哪儿、同程旅行和智行分别展示点评质量与回复情况。", "携程 eBooking / 点评问答 / 订单点评", ("携程", "去哪儿", "同程旅行", "智行")),
    (13, "权益中心", 4, "当前值", "展示已报名权益数量和权益清单。", "携程 eBooking / 权益中心", ("已报名权益", "权益清单")),
    (14, "积分联盟", 3, "近30天", "展示报名状态、近30天订单、成交金额和平台覆盖。", "携程 eBooking / 积分联盟", ("报名状态", "近30天订单", "成交金额", "覆盖平台")),
    (15, "优享会", 3, "当前值", "展示参加状态和标签状态。", "携程 eBooking / 优享会", ("参加状态", "标签状态")),
    (16, "商旅专享价", 2, "当前值", "展示开通状态和参与房型数。", "携程 eBooking / 商旅专享价", ("开通状态", "参与房型")),
    (17, "闪住", 2, "当前值", "展示闪住开通状态和参与房型数。", "携程 eBooking / 闪住", ("开通状态", "参与房型", "后台入口")),
    (18, "钟点房", 2, "近30天", "展示核心房型配置、促销状态和钟点房订单。", "携程 eBooking / 钟点房", ("钟点房配置", "核心房型", "促销状态", "近30天订单")),
    (19, "旅拍", 2, "当前值", "展示旅拍上传、认领状态和数量。", "携程 eBooking / 旅拍", ("旅拍上传", "认领状态", "旅拍数量")),
    (20, "首页视频", 1, "当前值", "展示酒店预览视频或首页视频上传状态。", "携程 eBooking / 视频管理", ("酒店预览视频", "首页视频", "口径状态")),
    (21, "挂牌 / 委托分销", 6, "当前值", "展示挂牌状态、挂牌等级、委托分销和权益等级。", "携程 eBooking / 挂牌与委托分销", ("挂牌状态", "挂牌等级", "委托分销", "权益等级")),
    (22, "多平台口径核验", None, "本次报告", "展示实际取数平台、是否混合、是否可拆分和人工确认状态。", "携程、去哪儿、同程旅行、智行口径核验", ("流量漏斗", "口碑分析", "积分联盟", "金字塔")),
)

STATUS = {
    "success": ("已形成结果", "ok"),
    "partial": ("部分接入", "pending"),
    "zero": ("真实为0", "disabled"),
    "missing": ("数据待接入", "pending"),
    "error": ("查询失败", "pending"),
    "pending_rule": ("规则待确认", "pending"),
    "manual_pending": ("待人工录入", "manual"),
}

CTRIP_STYLE = """
<style id='CTRIP_CODE_GENERATED_V55'>
.ctrip-note-v55{margin-top:14px;padding:11px 13px;border:1px solid rgba(255,255,255,.18);border-radius:9px;background:rgba(255,255,255,.09);color:rgba(255,255,255,.84);font-size:12px}
.ctrip-grid-v55{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.ctrip-metric-v55{min-height:92px;padding:13px;border:1px solid #dfe7e4;border-radius:9px;background:#fff}
.ctrip-metric-v55 small{display:block;color:#68747f;font-size:12px;font-weight:700}
.ctrip-metric-v55 strong{display:block;margin-top:9px;color:#26343d;font-size:20px;line-height:1.25;overflow-wrap:anywhere}
.ctrip-metric-v55 span{display:block;margin-top:6px;color:#84909a;font-size:11px}
.ctrip-source-v55{margin-top:12px;padding:11px 13px;border:1px solid #d9e6e1;border-radius:9px;background:#f4faf7;color:#315b4c;font-size:12px}
.ctrip-rights-table-v63{width:100%;border-collapse:collapse;border:1px solid #dfe7e4;border-radius:9px;overflow:hidden;background:#fff}
.ctrip-rights-table-v63 th,.ctrip-rights-table-v63 td{padding:11px 13px;border-bottom:1px solid #eaf0ed;text-align:left}
.ctrip-rights-table-v63 th{background:#f5faf7;color:#53616b;font-size:12px;font-weight:700}
.ctrip-rights-table-v63 td{color:#26343d;font-size:14px;font-weight:700}
.ctrip-rights-table-v63 tr:last-child td{border-bottom:0}
.ctrip-reputation-summary-v64{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:12px}
.ctrip-reputation-summary-card-v64{padding:14px;border:1px solid #dfe7e4;border-radius:9px;background:#f7fbf9}
.ctrip-reputation-summary-card-v64 small{display:block;color:#68747f;font-size:12px;font-weight:700}
.ctrip-reputation-summary-card-v64 strong{display:block;margin-top:7px;color:#26343d;font-size:22px;line-height:1.2}
.ctrip-reputation-summary-card-v64 span{display:block;margin-top:5px;color:#84909a;font-size:11px}
.ctrip-reputation-grid-v64{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.ctrip-reputation-card-v64{overflow:hidden;border:1px solid #dfe7e4;border-radius:9px;background:#fff}
.ctrip-reputation-head-v64{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 15px;border-bottom:1px solid #eaf0ed;background:#f7faf9}
.ctrip-reputation-name-v64{display:flex;align-items:center;gap:9px;color:#26343d;font-size:16px;font-weight:900}
.ctrip-reputation-dot-v64{width:8px;height:8px;border-radius:50%;background:#2f9d72}
.ctrip-reputation-weight-v64{display:block;margin-top:4px;color:#84909a;font-size:11px;font-weight:500}
.ctrip-reputation-score-v64{text-align:right;color:#16845b;font-weight:900}
.ctrip-reputation-score-v64 strong{display:block;font-size:18px;line-height:1.1}
.ctrip-reputation-score-v64 span{display:block;margin-top:4px;color:#84909a;font-size:11px;font-weight:600}
.ctrip-reputation-rating-v64{display:flex;align-items:end;justify-content:space-between;gap:14px;padding:14px 15px 10px}
.ctrip-reputation-rating-v64 small{display:block;color:#68747f;font-size:12px;font-weight:700}
.ctrip-reputation-rating-v64 strong{display:block;margin-top:5px;color:#26343d;font-size:28px;line-height:1}
.ctrip-reputation-rating-v64 em{font-style:normal;font-size:12px;font-weight:800}
.ctrip-reputation-rating-v64.good em{color:#16845b}.ctrip-reputation-rating-v64.fair em{color:#b6791f}.ctrip-reputation-rating-v64.low em{color:#c44c43}.ctrip-reputation-rating-v64.pending em{color:#84909a}
.ctrip-reputation-metrics-v64{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;padding:0 15px 13px}
.ctrip-reputation-metric-v64{padding:9px 10px;border:1px solid #edf1ef;border-radius:7px;background:#fbfcfc}
.ctrip-reputation-metric-v64 small{display:block;color:#84909a;font-size:11px;font-weight:600}
.ctrip-reputation-metric-v64 strong{display:block;margin-top:5px;color:#34424b;font-size:14px;line-height:1.2;overflow-wrap:anywhere}
.ctrip-reputation-dimensions-v64{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:0 15px 15px;padding-top:12px;border-top:1px solid #edf1ef}
.ctrip-reputation-dimension-v64 small{display:block;color:#84909a;font-size:11px}.ctrip-reputation-dimension-v64 strong{display:block;margin-top:4px;color:#53616b;font-size:13px}
.ctrip-reputation-muted-v64{color:#9aa5ad!important;font-weight:600!important}
.ctrip-room-name-summary-v65{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:12px}
.ctrip-room-name-table-v65{width:100%;border-collapse:collapse;border:1px solid #dfe7e4;background:#fff}
.ctrip-room-name-table-v65 th,.ctrip-room-name-table-v65 td{padding:11px 12px;border-bottom:1px solid #eaf0ed;text-align:left}
.ctrip-room-name-table-v65 th{background:#f5faf7;color:#53616b;font-size:12px;font-weight:700}
.ctrip-room-name-table-v65 td{color:#34424b;font-size:13px}
.ctrip-room-name-table-v65 tr:last-child td{border-bottom:0}
.ctrip-room-name-table-v65 .qualified{color:#16845b;font-weight:800}
.ctrip-room-name-table-v65 .unqualified{color:#b65c35;font-weight:800}
.ctrip-pending-v55{color:#788497!important}
@media(max-width:980px){.ctrip-grid-v55{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:980px){.ctrip-reputation-grid-v64{grid-template-columns:1fr}}
@media(max-width:680px){.ctrip-reputation-summary-v64{grid-template-columns:1fr}.ctrip-reputation-metrics-v64{grid-template-columns:repeat(2,minmax(0,1fr))}.ctrip-reputation-dimensions-v64{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:680px){.ctrip-room-name-summary-v65{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:640px){.ctrip-grid-v55{grid-template-columns:1fr}}
</style>
"""


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(str(value).replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None
    return None if math.isnan(parsed) or math.isinf(parsed) else parsed


def sections(result: dict[str, Any]) -> dict[str, Any]:
    value = result.get("sections")
    return value if isinstance(value, dict) else {}


def spec(no: int) -> tuple[Any, ...]:
    return next(item for item in SPECS if item[0] == no)


def item_source(result: dict[str, Any]) -> Any:
    nested = sections(result)
    return (
        result.get("ctrip_items")
        or result.get("ctrip_diagnosis_items")
        or nested.get("ctrip_items")
        or nested.get("ctrip_diagnosis_items")
        or {}
    )


def item_payload(result: dict[str, Any], item_spec: tuple[Any, ...]) -> dict[str, Any]:
    no, title = item_spec[0], item_spec[1]
    source = item_source(result)
    found: dict[str, Any] = {}

    if isinstance(source, dict):
        value = source.get(no) or source.get(str(no)) or source.get(title)
        if isinstance(value, dict):
            found = dict(value)
    elif isinstance(source, list):
        for value in source:
            if not isinstance(value, dict):
                continue
            value_no = value.get("no") or value.get("standard_item_id") or value.get("item_no")
            value_title = value.get("title") or value.get("item_name")
            if str(value_no or "") == str(no) or str(value_title or "") == title:
                found = dict(value)
                break

    channel = result.get("channel_scores")
    if isinstance(channel, dict) and isinstance(channel.get("ctrip"), dict):
        values = channel["ctrip"].get("items") or channel["ctrip"].get("item_scores")
        if isinstance(values, dict):
            value = values.get(no) or values.get(str(no)) or values.get(title)
            if isinstance(value, dict):
                found = {**value, **found}
            elif value not in (None, "") and "item_score" not in found:
                found["item_score"] = value

    if no == 6:
        nested = sections(result)
        psi = (
            result.get("ctrip_psi")
            or result.get("psi_service_quality")
            or nested.get("ctrip_psi")
            or nested.get("psi_service_quality")
        )
        if isinstance(psi, dict):
            found = {**psi, **found}
    return found


def summary_payload(result: dict[str, Any]) -> dict[str, Any]:
    nested = sections(result)
    for value in (
        result.get("ctrip_summary"),
        result.get("ctrip_score_summary"),
        nested.get("ctrip_summary"),
        nested.get("ctrip_score_summary"),
    ):
        if isinstance(value, dict):
            return dict(value)
    channel = result.get("channel_scores")
    if isinstance(channel, dict) and isinstance(channel.get("ctrip"), dict):
        return dict(channel["ctrip"])
    return {}


def score_value(payload: dict[str, Any]) -> float | None:
    for key in ("item_score", "diagnosis_score", "score", "current_score"):
        value = number(payload.get(key))
        if value is not None:
            return value
    return None


def configured_full_score(item_spec: tuple[Any, ...], payload: dict[str, Any]) -> float | None:
    if item_spec[2] is None:
        return None
    for key in ("full_score", "item_full_score", "weight"):
        value = number(payload.get(key))
        if value is not None:
            return value
    return float(item_spec[2])


def full_text(item_spec: tuple[Any, ...], payload: dict[str, Any]) -> str:
    value = configured_full_score(item_spec, payload)
    return "仅展示" if value is None else f"{value:g}分"


def score_text(item_spec: tuple[Any, ...], payload: dict[str, Any]) -> str:
    if item_spec[2] is None:
        return "仅展示"
    value = score_value(payload)
    return "待计算" if value is None else f"{value:g}分"


def status(payload: dict[str, Any]) -> tuple[str, str, str]:
    key = str(payload.get("data_status") or payload.get("status_key") or "")
    if not key:
        key = "success" if payload.get("fields") or payload.get("records") or score_value(payload) is not None else "missing"
    text, css = STATUS.get(key, (str(payload.get("status") or key), "neutral"))
    return key, text, css


def fields(item_spec: tuple[Any, ...], payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("fields")
    rows: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for label, value in raw.items():
            rows.append({"label": label, **value} if isinstance(value, dict) else {"label": label, "value": value})
    elif isinstance(raw, list):
        for value in raw:
            if isinstance(value, dict):
                rows.append(dict(value))
            elif isinstance(value, (list, tuple)) and len(value) > 1:
                rows.append({"label": value[0], "value": value[1]})

    known = {str(row.get("label") or "") for row in rows}
    if payload.get("fields_complete"):
        return rows
    for label in item_spec[6]:
        if label not in known:
            rows.append({"label": label, "value": payload.get(label)})
    return rows


def visual_items(result: dict[str, Any]) -> dict[int, dict[str, Any]]:
    visual = result.get("visual_diagnosis")
    if not isinstance(visual, dict):
        visual = build_visual_diagnosis({}, str(result.get("hotel_name") or ""))
    return {
        int(item.get("standard_item_id") or 0): item
        for item in (visual.get("items") or [])
        if isinstance(item, dict)
    }


def pms_item(result: dict[str, Any], no: int) -> dict[str, Any]:
    """Create a Ctrip-owned 01/02 item from the shared PMS diagnosis result.

    The records/fields/trend data come from the same PMS result used by Meituan.
    Only the Ctrip score configuration is overlaid, so the two HTML nodes remain
    independent while their current data and visual renderer stay identical.
    """

    item_spec = spec(no)
    base = copy.deepcopy(visual_items(result).get(no) or {})
    payload = item_payload(result, item_spec)
    item = base
    item["standard_item_id"] = no
    item["item_name"] = item_spec[1]
    item["participates_in_score"] = item_spec[2] is not None
    item["base_score"] = configured_full_score(item_spec, payload) or 0
    item["item_score"] = score_value(payload)
    if not item.get("data_status"):
        item["data_status"] = "success" if item.get("fields") or item.get("records") or item.get("trend_periods") else "missing"
    return item


def _reputation_value(entry: dict[str, Any], key: str, *, suffix: str = "") -> str:
    value = entry.get(key)
    if entry.get("data_status") == "missing":
        return "待接入"
    if value in (None, ""):
        return "暂无数据"
    parsed = number(value)
    if parsed is not None and parsed.is_integer():
        return f"{int(parsed)}{suffix}"
    return f"{parsed:.2f}{suffix}" if parsed is not None else f"{value}{suffix}"


def _reputation_percent(entry: dict[str, Any]) -> str:
    value = entry.get("reply_rate")
    if entry.get("data_status") == "missing":
        return "待接入"
    if value in (None, ""):
        return "暂无数据"
    parsed = number(value)
    return "暂无数据" if parsed is None else f"{parsed * 100:.1f}%"


def _reputation_card_content(payload: dict[str, Any]) -> str:
    platforms = payload.get("platforms")
    if not isinstance(platforms, list):
        platforms = []
    score = score_value(payload)
    available = sum(
        1
        for entry in platforms
        if isinstance(entry, dict) and entry.get("data_status") != "missing"
    )
    summary = (
        "<div class='ctrip-reputation-summary-v64'>"
        f"<div class='ctrip-reputation-summary-card-v64'><small>平台评分合计</small><strong>{e('待计算' if score is None else f'{score:g}分')}</strong><span>满分 10 分</span></div>"
        f"<div class='ctrip-reputation-summary-card-v64'><small>已接入平台</small><strong>{available}/4</strong><span>携程、去哪儿、同程旅行、智行</span></div>"
        "<div class='ctrip-reputation-summary-card-v64'><small>评分规则</small><strong>4.7分</strong><span>达标平台按对应权重计满分</span></div>"
        "</div>"
    )
    cards: list[str] = []
    for entry in platforms:
        if not isinstance(entry, dict):
            continue
        rating = number(entry.get("rating"))
        rating_class = (
            "pending"
            if rating is None
            else "good"
            if rating >= 4.7
            else "fair"
            if rating >= 4.5
            else "low"
        )
        rating_note = (
            "待接入"
            if rating is None
            else "达标"
            if rating >= 4.7
            else "80%计分"
            if rating >= 4.5
            else "未达标"
        )
        dimensions: list[str] = []
        for label, key in (
            ("环境", "environment_score"),
            ("设施", "facility_score"),
            ("服务", "service_score"),
            ("卫生", "hygiene_score"),
        ):
            muted = "ctrip-reputation-muted-v64" if entry.get(key) in (None, "") else ""
            dimensions.append(
                f"<div class='ctrip-reputation-dimension-v64'><small>{e(label)}</small>"
                f"<strong class='{muted}'>{e(_reputation_value(entry, key))}</strong></div>"
            )
        cards.append(
            "<section class='ctrip-reputation-card-v64'>"
            "<div class='ctrip-reputation-head-v64'><div>"
            f"<div class='ctrip-reputation-name-v64'><i class='ctrip-reputation-dot-v64'></i>{e(entry.get('platform_name') or '平台')}</div>"
            f"<span class='ctrip-reputation-weight-v64'>平台权重 {_reputation_value(entry, 'full_score', suffix='分')}</span>"
            "</div><div class='ctrip-reputation-score-v64'>"
            f"<strong>{e(_reputation_value(entry, 'score', suffix='分'))}</strong><span>本平台得分</span></div></div>"
            f"<div class='ctrip-reputation-rating-v64 {rating_class}'><div><small>点评分</small><strong>{e(_reputation_value(entry, 'rating'))}</strong></div><em>{e(rating_note)}</em></div>"
            "<div class='ctrip-reputation-metrics-v64'>"
            f"<div class='ctrip-reputation-metric-v64'><small>点评条数</small><strong>{e(_reputation_value(entry, 'review_count', suffix='条'))}</strong></div>"
            f"<div class='ctrip-reputation-metric-v64'><small>昨日新增点评数</small><strong>{e(_reputation_value(entry, 'yesterday_new_review_count', suffix='条'))}</strong></div>"
            f"<div class='ctrip-reputation-metric-v64'><small>未回复点评</small><strong>{e(_reputation_value(entry, 'unreplied_review_count', suffix='条'))}</strong></div>"
            f"<div class='ctrip-reputation-metric-v64'><small>点评回复率</small><strong>{e(_reputation_percent(entry))}</strong></div>"
            f"<div class='ctrip-reputation-metric-v64'><small>差评数</small><strong>{e(_reputation_value(entry, 'negative_review_count', suffix='条'))}</strong></div>"
            "</div>"
            f"<div class='ctrip-reputation-dimensions-v64'>{''.join(dimensions)}</div>"
            "</section>"
        )
    return summary + "<div class='ctrip-reputation-grid-v64'>" + "".join(cards) + "</div>"


def _room_name_card_content(payload: dict[str, Any]) -> str:
    fields_by_label = {
        str(row.get("label") or ""): row.get("value")
        for row in payload.get("fields") or []
        if isinstance(row, dict)
    }
    summary = "".join(
        "<div class='ctrip-metric-v55'>"
        f"<small>{e(label)}</small>"
        f"<strong>{e(value if value not in (None, '') else '待接入')}</strong>"
        "</div>"
        for label, value in fields_by_label.items()
    )
    records = payload.get("records")
    records = records if isinstance(records, list) else []
    table_rows: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        qualified = bool(record.get("qualified"))
        result_class = "qualified" if qualified else "unqualified"
        result_text = "合格" if qualified else "待优化"
        table_rows.append(
            "<tr>"
            f"<td>{e(record.get('name') or '未命名售卖房型')}</td>"
            f"<td>{e(record.get('length'))}</td>"
            f"<td>{e(record.get('reason') or '待核验')}</td>"
            f"<td class='{result_class}'>{result_text}</td>"
            "</tr>"
        )
    if not table_rows:
        table_rows.append(
            "<tr><td colspan='4' class='ctrip-pending-v55'>"
            "待接入携程售卖房型快照</td></tr>"
        )
    return (
        f"<div class='ctrip-room-name-summary-v65'>{summary}</div>"
        "<div class='table-scroll'><table class='ctrip-room-name-table-v65'>"
        "<thead><tr><th>售卖房型名称</th><th>名称字数</th>"
        "<th>识别信息</th><th>判定</th></tr></thead>"
        f"<tbody>{''.join(table_rows)}</tbody></table></div>"
    )


def generic_card(result: dict[str, Any], item_spec: tuple[Any, ...]) -> str:
    no, title, _, period, description, source, _ = item_spec
    payload = item_payload(result, item_spec)
    key, text, css = status(payload)
    rows = fields(item_spec, payload) or [
        {"label": "数据状态", "value": None, "note": "等待携程数据接入"}
    ]
    metrics = "".join(
        "<div class='ctrip-metric-v55'>"
        f"<small>{e(row.get('label') or '指标')}</small>"
        f"<strong class='{'ctrip-pending-v55' if row.get('value') in (None, '') else ''}'>"
        f"{e('待接入' if row.get('value') in (None, '') else row.get('value'))}</strong>"
        f"<span>{e(row.get('note') or '')}</span></div>"
        for row in rows
    )
    if no == 11:
        result_content = _room_name_card_content(payload)
    elif no == 12:
        result_content = _reputation_card_content(payload)
    elif no == 13:
        rights = payload.get("rights_list")
        if not isinstance(rights, list):
            rights = [
                value.strip()
                for value in str(next((row.get("value") for row in rows if row.get("label") == "权益清单"), "") or "").split("、")
                if value.strip()
            ]
        count = next((row.get("value") for row in rows if row.get("label") == "已报名权益"), None)
        table_rows = "".join(f"<tr><td>{e(value)}</td></tr>" for value in rights)
        if not table_rows:
            empty_text = "待接入" if key == "missing" else "暂无已报名权益"
            table_rows = f"<tr><td class='ctrip-pending-v55'>{e(empty_text)}</td></tr>"
        result_content = (
            "<div class='ctrip-grid-v55'>"
            f"<div class='ctrip-metric-v55'><small>已报名权益</small><strong>{e(count if count not in (None, '') else '待接入')}</strong></div>"
            "</div>"
            "<div class='table-scroll'><table class='ctrip-rights-table-v63'>"
            "<thead><tr><th>权益清单</th></tr></thead>"
            f"<tbody>{table_rows}</tbody></table></div>"
        )
    else:
        result_content = f"<div class='ctrip-grid-v55'>{metrics}</div>"
    score_class = "display-only" if item_spec[2] is None else "ok" if score_value(payload) is not None else "pending"
    return (
        f"<article class='diagnosis-card' data-status='{e(key)}' data-title='{e(title)}' id='rule-{no}'>"
        "<div class='card-top'>"
        f"<div class='rule-no'>{no:02d}</div>"
        f"<div class='card-title'><h3>{e(title)}</h3><p>{e(description)}</p></div>"
        "<div class='card-tags'>"
        f"<div class='title-meta-item title-period'><small>统计周期</small><strong>{e(period)}</strong></div>"
        f"<div class='title-meta-item title-score {score_class}'><small>当前得分</small>"
        f"<div class='title-score-value'><strong>{e(score_text(item_spec, payload))}</strong>"
        f"<span>满分 {e(full_text(item_spec, payload))}</span></div></div>"
        f"<span class='status-badge {css}'>{e(text)}</span></div></div>"
        "<div class='result-area'>"
        f"{result_content}"
        f"<div class='ctrip-source-v55'><b>携程数据来源：</b>{e(payload.get('source') or source)}</div>"
        "<div class='notice'>未接入字段统一显示“待接入”，不会使用美团数据或示例值替代。</div>"
        "</div></article>"
    )


def patch_psi_score(card_html: str, result: dict[str, Any]) -> str:
    item_spec = spec(6)
    payload = item_payload(result, item_spec)
    current = score_text(item_spec, payload)
    full = full_text(item_spec, payload)
    marker = "<div class='title-score-value'><strong>待计算</strong><span>满分 8分</span></div>"
    replacement = (
        "<div class='title-score-value'>"
        f"<strong>{e(current)}</strong><span>满分 {e(full)}</span></div>"
    )
    output = card_html.replace(marker, replacement, 1)
    if score_value(payload) is not None:
        output = output.replace("title-meta-item title-score pending", "title-meta-item title-score ok", 1)
    return output


def nav_html() -> str:
    links = "".join(
        f"<a href='#rule-{item[0]}'><span>{item[0]:02d}</span>{e(item[1])}</a>"
        for item in SPECS
    )
    return (
        "<nav class='side'><div class='side-title'>携程诊断目录</div>"
        "<a href='#overview'><span>00</span>诊断概览</a>"
        "<a href='#summary'><span>表</span>诊断结果总览</a>"
        f"{links}</nav>"
    )


def overview_html(result: dict[str, Any]) -> str:
    payload = summary_payload(result)
    total = number(payload.get("total_score") or payload.get("score"))
    total_text = "待计算" if total is None else f"{total:g}"
    scoring = sum(1 for item in SPECS if item[2] is not None)
    connected = payload.get("connected_items")
    connected_text = "待接入" if connected in (None, "") else f"{connected}项"
    start = result.get("period_start") or "未标注"
    end = result.get("period_end") or "未标注"
    return (
        "<section id='overview'><div class='hero'><div class='hero-grid'><div>"
        "<h2>携程渠道经营与服务质量诊断</h2>"
        "<p>携程页面由Python直接生成；目录、得分和渠道模块均独立于美团页面。</p>"
        "<div class='source-standard'>"
        f"<div><small>诊断周期</small><b>{e(start)} 至 {e(end)}</b></div>"
        "<div><small>01、02数据</small><b>PMS独立输出，当前与美团一致</b></div>"
        "<div><small>03以后数据</small><b>仅使用携程渠道数据</b></div>"
        "</div>"
        "<div class='ctrip-note-v55'>两个页面中的01、02分别由代码生成，读取同一份PMS结果；页面节点、满分和得分互不影响。</div>"
        "</div><div class='hero-stats'>"
        f"<div class='hero-stat'><small>携程综合得分</small><strong>{e(total_text)}</strong><em>不沿用美团得分</em></div>"
        f"<div class='hero-stat'><small>计分模块</small><strong>{scoring}项</strong><em>携程规则独立计算</em></div>"
        f"<div class='hero-stat'><small>展示模块</small><strong>{len(SPECS)-scoring}项</strong><em>不参与总分</em></div>"
        f"<div class='hero-stat'><small>已接入模块</small><strong>{e(connected_text)}</strong><em>未接入保持待计算</em></div>"
        "</div></div></div>"
        "<div class='section-body'><div class='notice'>携程页面不会从美团成品HTML复制目录或诊断卡片。</div></div>"
        "</section>"
    )


def summary_row(result: dict[str, Any], item_spec: tuple[Any, ...]) -> str:
    no = item_spec[0]
    if no in (1, 2):
        item = pms_item(result, no)
        key = str(item.get("data_status") or "missing")
        text, css = STATUS.get(key, (key, "neutral"))
        payload = item_payload(result, item_spec)
    else:
        payload = item_payload(result, item_spec)
        key, text, css = status(payload)
    return (
        f"<tr data-status='{e(key)}' data-title='{e(item_spec[1])}'>"
        f"<td>{no:02d}</td><td><a href='#rule-{no}'>{e(item_spec[1])}</a></td>"
        f"<td>{e(full_text(item_spec, payload))}</td><td>{e(score_text(item_spec, payload))}</td>"
        f"<td><span class='status-badge {css}'>{e(text)}</span></td>"
        f"<td>{e(payload.get('source') or item_spec[5])}<br>{e(item_spec[4])}</td></tr>"
    )


def summary_html(result: dict[str, Any]) -> str:
    rows = "".join(summary_row(result, item_spec) for item_spec in SPECS)
    return (
        "<section id='summary'><div class='section-head'><div>"
        "<h2>携程诊断结果总览</h2>"
        "<p>携程目录、满分、得分和数据状态独立于美团页面。</p></div>"
        "<div class='toolbar'><input class='search' id='ruleSearch' placeholder='搜索诊断项'/>"
        "<select class='filter' id='statusFilter'><option value='all'>全部状态</option>"
        "<option value='success'>已形成结果</option><option value='missing'>数据待接入</option>"
        "<option value='pending_rule'>规则待确认</option></select></div></div>"
        "<div class='section-body'><div class='table-scroll'><table class='summary-table'>"
        "<thead><tr><th>编号</th><th>携程诊断项目</th><th>满分</th><th>当前得分</th>"
        "<th>当前状态</th><th>数据来源/诊断内容</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div></div></section>"
    )


def cards_html(result: dict[str, Any]) -> str:
    item_one = pms_item(result, 1)
    item_two = pms_item(result, 2)
    cards = [
        reporting_v37._performance_card(item_one),
        reporting_v35._clean_customer_html(reporting_v30._room_type_card(item_two)),
    ]
    for item_spec in SPECS[2:]:
        no = item_spec[0]
        if no == 6:
            cards.append(patch_psi_score(psi_card(result, "rule-6"), result))
        else:
            cards.append(generic_card(result, item_spec))
    return "".join(cards)


def search_script() -> str:
    return """
<script>
document.addEventListener('DOMContentLoaded',function(){
  const search=document.getElementById('ruleSearch');
  const filter=document.getElementById('statusFilter');
  if(!search||!filter) return;
  function apply(){
    const q=(search.value||'').trim().toLowerCase();
    const state=filter.value;
    document.querySelectorAll('.diagnosis-card').forEach(function(card){
      const matchText=!q||(card.dataset.title||'').toLowerCase().includes(q);
      const matchState=state==='all'||card.dataset.status===state;
      card.classList.toggle('hidden-card',!(matchText&&matchState));
    });
  }
  search.addEventListener('input',apply);
  filter.addEventListener('change',apply);
});
</script>
"""


def build_head() -> str:
    """Use the same base report template and direct-render styles as Meituan."""

    template = reporting_v8.TEMPLATE_PATH.read_text(encoding="utf-8")
    base = template.split("</head>", 1)[0]
    base = re.sub(
        r"<title>.*?</title>",
        "<title>携程｜酒店 OTA 全面诊断报告</title>",
        base,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return (
        base
        + reporting_v8.EXTRA_STYLE
        + reporting_v30.ROOM_TYPE_STYLE
        + reporting_v37.PERFORMANCE_TREND_STYLE
        + PSI_STYLE
        + CTRIP_STYLE
        + "</head>"
    )


def build_html(result: dict[str, Any]) -> str:
    """Generate the complete Ctrip report directly from result data.

    No Meituan HTML is passed in, searched, copied or replaced. The two reports
    share the same base style system and PMS data model for items 01 and 02, but
    each page receives its own independently generated DOM and score settings.
    """

    hotel = result.get("hotel_name") or result.get("hotel_id") or "酒店"
    start = result.get("period_start") or "未标注"
    end = result.get("period_end") or "未标注"
    body = (
        "<body><header class='topbar'><div class='topbar-inner'>"
        "<div class='brand'><h1>酒店 OTA 全面诊断报告</h1>"
        f"<p>{e(hotel)}｜诊断周期：{e(start)} 至 {e(end)}｜生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        "</div><div class='top-actions'>"
        "<select class='scope-select'><option>携程综合诊断</option><option>PMS经营数据</option>"
        "<option>携程 eBooking 数据</option></select>"
        "<button class='btn primary' onclick='window.print()'>导出报告</button>"
        "</div></div></header>"
        f"<div class='page'>{nav_html()}<main>{overview_html(result)}{summary_html(result)}"
        f"{cards_html(result)}</main></div>{search_script()}{reporting_v37._script()}</body></html>"
    )
    return build_head() + body


__all__ = ["SPECS", "build_html", "pms_item"]
