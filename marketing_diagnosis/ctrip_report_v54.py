from __future__ import annotations

import html
import math
import re
from typing import Any

from marketing_diagnosis.ctrip_psi_v53 import STYLE as PSI_STYLE
from marketing_diagnosis.ctrip_psi_v53 import card as psi_card

# no, title, full score (None = display only), period, description, source, field labels
SPECS = (
    (1, "月度经营趋势 YOY", 10, "本日 / 本月 / 本年", "展示房费、ADR、出租率、RevPAR及去年同期同比。", "PMS经营数据（当前与美团页面取数口径一致）", ()),
    (2, "房型 RevPAR 与低效房型", 8, "本日 / 本月", "按房型展示出租率、RevPAR及低效房型判定。", "PMS房型经营数据（当前与美团页面取数口径一致）", ()),
    (3, "平台流量漏斗分析", 15, "近30天", "展示曝光、访客、订单页和成交漏斗。", "携程 eBooking / 流量与转化", ("列表曝光", "APP访客", "订单页访客", "成交订单", "竞争圈排名")),
    (4, "用户来源画像", None, "近30天", "展示性别、年龄、本地异地、出行目的和预订习惯。", "携程 eBooking / 用户画像", ("性别", "年龄段", "本地 / 异地", "主要客源城市")),
    (5, "竞争圈分析", None, "近30天", "展示竞争圈排名、均值、流失订单和主要流失竞对。", "携程 eBooking / 竞争圈分析", ("竞争圈排名", "平均订单量", "流失订单量", "流失订单金额")),
    (6, "PSI 服务质量分", 8, "当前值", "展示基础分、九项分指标、项目权重和昨日变化。", "携程 eBooking / 服务质量分 / 基础分", ()),
    (7, "YOYO 卡 / 扫码住", 5, "近30天", "按近30天扫码订单换算日均扫码订单。", "携程 eBooking / YOYO卡或扫码住", ("近30天扫码订单", "日均扫码订单", "扫码新增会员", "促销状态")),
    (8, "信息完整度", 4, "当前值", "展示携程信息首页完整度及缺失项。", "携程 eBooking / 信息维护", ("信息完整度", "基础信息缺失", "政策缺失", "设施缺失")),
    (9, "推广数据：金字塔", 8, "近30天", "展示投入、曝光、点击、订单、成交金额和ROI。", "携程 eBooking / 金字塔推广", ("推广产品", "投入金额", "曝光量", "推广订单", "ROI")),
    (10, "页面展示和入口基础", 3, "最新快照", "检查门店后缀、地标商圈词、推荐词、标签和卖点。", "携程酒店详情页 / eBooking信息维护", ("门店后缀", "地标 / 商圈词", "推荐词 / 标签")),
    (11, "房型名称与售卖房型", 4, "最新快照", "展示房型名称长度、卖点命中、合格占比和售卖渠道。", "携程 eBooking / 房型与售卖", ("房型总数", "合格房型", "合格占比", "售卖渠道")),
    (12, "口碑分析", 10, "当前值", "分别展示携程、去哪儿、同程旅行和智行评分。", "携程系平台点评数据", ("携程", "去哪儿", "同程旅行", "智行")),
    (13, "权益中心", 4, "当前值", "展示免费取消、提前入住、延迟退房和早餐等权益。", "携程 eBooking / 权益中心", ("已报名权益", "免费取消", "延迟退房", "早餐")),
    (14, "积分联盟", 3, "近30天", "展示报名状态、近30天订单、成交金额和平台覆盖。", "携程 eBooking / 积分联盟", ("报名状态", "近30天订单", "成交金额", "覆盖平台")),
    (15, "优享会", 3, "当前值", "展示参加状态、标签状态、参与房型和订单。", "携程 eBooking / 优享会", ("参加状态", "标签状态", "参与房型", "近30天订单")),
    (16, "商旅专享价", 2, "当前值", "展示开通状态、参与房型数和近30天订单。", "携程 eBooking / 商旅专享价", ("开通状态", "参与房型", "近30天订单", "成交金额")),
    (17, "闪住", 2, "当前值", "展示闪住开通状态和参与房型数。", "携程 eBooking / 闪住", ("开通状态", "参与房型", "后台入口")),
    (18, "钟点房", 2, "近30天", "展示核心房型配置、促销状态和钟点房订单。", "携程 eBooking / 钟点房", ("钟点房配置", "核心房型", "促销状态", "近30天订单")),
    (19, "旅拍", 2, "当前值", "展示旅拍上传、认领状态和数量。", "携程 eBooking / 旅拍", ("旅拍上传", "认领状态", "旅拍数量")),
    (20, "首页视频", 1, "当前值", "展示酒店预览视频或首页视频上传状态。", "携程 eBooking / 视频管理", ("酒店预览视频", "首页视频", "口径状态")),
    (21, "挂牌 / 委托分销", 6, "当前值", "展示挂牌状态、挂牌等级、委托分销和权益等级。", "携程 eBooking / 挂牌与委托分销", ("挂牌状态", "挂牌等级", "委托分销", "权益等级")),
    (22, "多平台口径核验", None, "本次报告", "展示实际取数平台、是否混合、是否可拆分和人工确认状态。", "携程、去哪儿、同程旅行、智行口径核验", ("流量漏斗", "口碑分析", "积分联盟", "金字塔")),
)

STATUS = {
    "success": ("已形成结果", "ok"), "zero": ("真实为0", "disabled"),
    "missing": ("数据待接入", "pending"), "error": ("查询失败", "pending"),
    "pending_rule": ("规则待确认", "pending"), "manual_pending": ("待人工录入", "manual"),
}
NAV_RE = re.compile(r"<nav\b[^>]*class=['\"][^'\"]*\bside\b[^'\"]*['\"][^>]*>.*?</nav>", re.S | re.I)
MAIN_RE = re.compile(r"<main\b[^>]*>.*?</main>", re.S | re.I)
TITLE_RE = re.compile(r"<title>.*?</title>", re.S | re.I)
CARD_RE = {n: re.compile(rf"<article\b(?=[^>]*\bid=['\"](?:rule|module)-{n}['\"])[^>]*>.*?</article>", re.S | re.I) for n in (1, 2)}
SCORE_RE = re.compile(r"(<div\b[^>]*class=['\"][^'\"]*\btitle-score-value\b[^'\"]*['\"][^>]*>\s*<strong>).*?(</strong>\s*<span>\s*满分\s*).*?(</span>)", re.S | re.I)
SCORE_CLASS_RE = re.compile(r"class=(['\"])(?P<c>[^'\"]*\btitle-meta-item\b[^'\"]*\btitle-score\b[^'\"]*)\1", re.I)

STYLE = """
<style id='CTRIP_INDEPENDENT_V54'>
.ctrip-note-v54{margin-top:14px;padding:11px 13px;border:1px solid rgba(255,255,255,.18);border-radius:9px;background:rgba(255,255,255,.09);color:rgba(255,255,255,.84);font-size:12px}
.ctrip-grid-v54{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.ctrip-metric-v54{min-height:92px;padding:13px;border:1px solid #dfe7e4;border-radius:9px;background:#fff}.ctrip-metric-v54 small{display:block;color:#68747f;font-size:12px;font-weight:700}.ctrip-metric-v54 strong{display:block;margin-top:9px;color:#26343d;font-size:20px;line-height:1.25;overflow-wrap:anywhere}.ctrip-metric-v54 span{display:block;margin-top:6px;color:#84909a;font-size:11px}.ctrip-source-v54{margin-top:12px;padding:11px 13px;border:1px solid #d9e6e1;border-radius:9px;background:#f4faf7;color:#315b4c;font-size:12px}.ctrip-pending-v54{color:#788497!important}@media(max-width:980px){.ctrip-grid-v54{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:640px){.ctrip-grid-v54{grid-template-columns:1fr}}
</style>
"""


def e(v: Any) -> str: return html.escape("" if v is None else str(v), quote=True)
def number(v: Any) -> float | None:
    try:
        x = float(v); return None if math.isnan(x) or math.isinf(x) else x
    except (TypeError, ValueError): return None

def sections(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("sections") if isinstance(result.get("sections"), dict) else {}

def spec(no: int) -> tuple[Any, ...]: return next(x for x in SPECS if x[0] == no)

def item_source(result: dict[str, Any]) -> Any:
    s = sections(result)
    return result.get("ctrip_items") or result.get("ctrip_diagnosis_items") or s.get("ctrip_items") or s.get("ctrip_diagnosis_items") or {}

def item_payload(result: dict[str, Any], sp: tuple[Any, ...]) -> dict[str, Any]:
    no, title = sp[0], sp[1]; source = item_source(result); found: dict[str, Any] = {}
    if isinstance(source, dict):
        value = source.get(no) or source.get(str(no)) or source.get(title)
        if isinstance(value, dict): found = dict(value)
    elif isinstance(source, list):
        for value in source:
            if isinstance(value, dict) and (str(value.get("no") or value.get("standard_item_id") or value.get("item_no") or "") == str(no) or str(value.get("title") or value.get("item_name") or "") == title):
                found = dict(value); break
    channel = result.get("channel_scores")
    if isinstance(channel, dict) and isinstance(channel.get("ctrip"), dict):
        values = channel["ctrip"].get("items") or channel["ctrip"].get("item_scores")
        if isinstance(values, dict):
            value = values.get(no) or values.get(str(no)) or values.get(title)
            if isinstance(value, dict): found = {**value, **found}
            elif value not in (None, "") and "item_score" not in found: found["item_score"] = value
    if no == 6:
        s = sections(result); psi = result.get("ctrip_psi") or result.get("psi_service_quality") or s.get("ctrip_psi") or s.get("psi_service_quality")
        if isinstance(psi, dict): found = {**psi, **found}
    return found

def summary_payload(result: dict[str, Any]) -> dict[str, Any]:
    s = sections(result)
    for value in (result.get("ctrip_summary"), result.get("ctrip_score_summary"), s.get("ctrip_summary"), s.get("ctrip_score_summary")):
        if isinstance(value, dict): return dict(value)
    channel = result.get("channel_scores")
    return dict(channel["ctrip"]) if isinstance(channel, dict) and isinstance(channel.get("ctrip"), dict) else {}

def score_value(p: dict[str, Any]) -> float | None:
    for key in ("item_score", "diagnosis_score", "score", "current_score"):
        value = number(p.get(key))
        if value is not None: return value
    return None

def full_text(sp: tuple[Any, ...], p: dict[str, Any]) -> str:
    if sp[2] is None: return "仅展示"
    for key in ("full_score", "item_full_score", "weight"):
        value = number(p.get(key))
        if value is not None: return f"{value:g}分"
    return f"{sp[2]:g}分"

def score_text(sp: tuple[Any, ...], p: dict[str, Any]) -> str:
    if sp[2] is None: return "仅展示"
    value = score_value(p); return "待计算" if value is None else f"{value:g}分"

def status(p: dict[str, Any]) -> tuple[str, str, str]:
    key = str(p.get("data_status") or p.get("status_key") or "")
    if not key: key = "success" if p.get("fields") or p.get("records") or score_value(p) is not None else "missing"
    text, css = STATUS.get(key, (str(p.get("status") or key), "neutral")); return key, text, css

def fields(sp: tuple[Any, ...], p: dict[str, Any]) -> list[dict[str, Any]]:
    raw = p.get("fields"); rows: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for label, value in raw.items(): rows.append({"label": label, **value} if isinstance(value, dict) else {"label": label, "value": value})
    elif isinstance(raw, list):
        for value in raw:
            if isinstance(value, dict): rows.append(dict(value))
            elif isinstance(value, (list, tuple)) and len(value) > 1: rows.append({"label": value[0], "value": value[1]})
    known = {str(x.get("label") or "") for x in rows}
    for label in sp[6]:
        if label not in known: rows.append({"label": label, "value": p.get(label)})
    return rows

def patch_score(card: str, result: dict[str, Any], sp: tuple[Any, ...]) -> str:
    p = item_payload(result, sp)
    card = SCORE_RE.sub(lambda m: m.group(1) + e(score_text(sp, p)) + m.group(2) + e(full_text(sp, p)) + m.group(3), card, count=1)
    cls = "display-only" if sp[2] is None else "ok" if score_value(p) is not None else "pending"
    def repl(m: re.Match[str]) -> str:
        values = [x for x in m.group("c").split() if x not in {"ok", "zero", "pending", "display-only"}] + [cls]
        return f"class={m.group(1)}{' '.join(values)}{m.group(1)}"
    return SCORE_CLASS_RE.sub(repl, card, count=1)

def generic_card(result: dict[str, Any], sp: tuple[Any, ...]) -> str:
    no, title, _, period, desc, source, _ = sp; p = item_payload(result, sp); key, text, css = status(p); rows = fields(sp, p) or [{"label": "数据状态", "value": None, "note": "等待携程数据接入"}]
    metrics = "".join(f"<div class='ctrip-metric-v54'><small>{e(x.get('label') or '指标')}</small><strong class='{'ctrip-pending-v54' if x.get('value') in (None, '') else ''}'>{e('待接入' if x.get('value') in (None, '') else x.get('value'))}</strong><span>{e(x.get('note') or '')}</span></div>" for x in rows)
    score_cls = "display-only" if sp[2] is None else "ok" if score_value(p) is not None else "pending"
    return f"<article class='diagnosis-card' data-status='{e(key)}' data-title='{e(title)}' id='rule-{no}'><div class='card-top'><div class='rule-no'>{no:02d}</div><div class='card-title'><h3>{e(title)}</h3><p>{e(desc)}</p></div><div class='card-tags'><div class='title-meta-item title-period'><small>统计周期</small><strong>{e(period)}</strong></div><div class='title-meta-item title-score {score_cls}'><small>当前得分</small><div class='title-score-value'><strong>{e(score_text(sp,p))}</strong><span>满分 {e(full_text(sp,p))}</span></div></div><span class='status-badge {css}'>{e(text)}</span></div></div><div class='result-area'><div class='ctrip-grid-v54'>{metrics}</div><div class='ctrip-source-v54'><b>携程数据来源：</b>{e(p.get('source') or source)}</div><div class='notice'>未接入字段统一显示“待接入”，不会使用美团数据或示例值替代。</div></div></article>"

def shared_card(meituan_html: str, result: dict[str, Any], no: int) -> str:
    match = CARD_RE[no].search(meituan_html); return patch_score(match.group(0), result, spec(no)) if match else generic_card(result, spec(no))

def nav_html() -> str:
    return "<nav class='side'><div class='side-title'>携程诊断目录</div><a href='#overview'><span>00</span>诊断概览</a><a href='#summary'><span>表</span>诊断结果总览</a>" + "".join(f"<a href='#rule-{x[0]}'><span>{x[0]:02d}</span>{e(x[1])}</a>" for x in SPECS) + "</nav>"

def overview_html(result: dict[str, Any]) -> str:
    p = summary_payload(result); total = number(p.get("total_score") or p.get("score")); total_text = "待计算" if total is None else f"{total:g}分"; scoring = sum(1 for x in SPECS if x[2] is not None); connected = p.get("connected_items"); connected_text = "待接入" if connected in (None, "") else f"{connected}项"
    return f"<section id='overview'><div class='hero'><div class='hero-grid'><div><h2>{e(result.get('hotel_name') or result.get('hotel_id') or '酒店')}｜携程渠道诊断</h2><p>诊断周期：{e(result.get('period_start') or '未标注')} 至 {e(result.get('period_end') or '未标注')}</p><div class='source-standard'><div><small>页面关系</small><b>携程页面独立生成</b></div><div><small>01、02数据</small><b>PMS独立输出，当前与美团一致</b></div><div><small>03以后数据</small><b>仅使用携程渠道数据</b></div></div><div class='ctrip-note-v54'>美团与携程是两个独立HTML页面；顶部按钮只负责页面切换。两个页面中的01、02分别存在，当前样式和PMS数据一致，但得分可独立配置。</div></div><div class='hero-stats'><div class='hero-stat'><small>携程综合得分</small><strong>{e(total_text)}</strong><em>不沿用美团得分</em></div><div class='hero-stat'><small>计分模块</small><strong>{scoring}项</strong><em>携程规则独立计算</em></div><div class='hero-stat'><small>展示模块</small><strong>{len(SPECS)-scoring}项</strong><em>不参与总分</em></div><div class='hero-stat'><small>已接入模块</small><strong>{e(connected_text)}</strong><em>未接入保持待计算</em></div></div></div></div></section>"

def summary_html(result: dict[str, Any]) -> str:
    rows = []
    for sp in SPECS:
        p = item_payload(result, sp); key, text, css = status(p)
        if sp[0] in (1,2): key, (text, css) = "success", STATUS["success"]
        rows.append(f"<tr data-status='{e(key)}' data-title='{e(sp[1])}'><td>{sp[0]:02d}</td><td><a href='#rule-{sp[0]}'>{e(sp[1])}</a></td><td>{e(full_text(sp,p))}</td><td>{e(score_text(sp,p))}</td><td><span class='status-badge {css}'>{e(text)}</span></td><td>{e(p.get('source') or sp[5])}<br>{e(sp[4])}</td></tr>")
    return "<section id='summary'><div class='section-head'><div><h2>携程诊断结果总览</h2><p>携程目录、满分、得分和数据状态独立于美团页面。</p></div></div><div class='section-body'><div class='table-scroll'><table class='summary-table'><thead><tr><th>编号</th><th>携程诊断项目</th><th>满分</th><th>当前得分</th><th>当前状态</th><th>数据来源/诊断内容</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div></div></section>"

def main_html(meituan_html: str, result: dict[str, Any]) -> str:
    cards = []
    for sp in SPECS:
        no = sp[0]
        if no in (1,2): cards.append(shared_card(meituan_html, result, no))
        elif no == 6: cards.append(patch_score(psi_card(result, "rule-6"), result, sp))
        else: cards.append(generic_card(result, sp))
    return "<main>" + overview_html(result) + summary_html(result) + "".join(cards) + "</main>"

def transform(meituan_html: str, result: dict[str, Any]) -> str:
    """Generate a separate Ctrip page while reusing only the current visual CSS and the 01/02 PMS output."""
    output = TITLE_RE.sub("<title>携程｜酒店 OTA 全面诊断报告</title>", meituan_html, count=1)
    if "CTRIP_INDEPENDENT_V54" not in output: output = output.replace("</head>", STYLE + PSI_STYLE + "</head>", 1)
    output = NAV_RE.sub(nav_html(), output, count=1)
    return MAIN_RE.sub(lambda _: main_html(meituan_html, result), output, count=1)

__all__ = ["SPECS", "transform"]
