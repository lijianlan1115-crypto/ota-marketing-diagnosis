from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_runtime_v51 as upstream


CHANNEL_STYLE = """
<style id='OTA_CHANNEL_SWITCH_V52'>
.ota-channel-switch-v52{display:inline-flex;align-items:center;padding:3px;border:1px solid var(--line,#dfe7e4);border-radius:9px;background:#f5f8f7}
.ota-channel-switch-v52 a{height:30px;display:inline-flex;align-items:center;justify-content:center;min-width:58px;padding:0 14px;border-radius:6px;color:var(--muted,#68747f);font-size:13px;font-weight:800;text-decoration:none}
.ota-channel-switch-v52 a:hover{color:var(--green,#16845b)}
.ota-channel-switch-v52 a.active{background:#fff;color:var(--green,#16845b);box-shadow:0 2px 8px rgba(31,41,51,.12)}
@media print{.ota-channel-switch-v52{display:none!important}}
</style>
"""

_PRINT_BUTTON_RE = re.compile(
    r"(<button\b[^>]*onclick=['\"]window\.print\(\)['\"][^>]*>.*?</button>)",
    re.DOTALL | re.IGNORECASE,
)
_TOP_ACTIONS_RE = re.compile(
    r"(<div\b[^>]*class=['\"][^'\"]*\btop-actions\b[^'\"]*['\"][^>]*>)",
    re.DOTALL | re.IGNORECASE,
)


def _switch_html(active: str) -> str:
    return (
        "<div class='ota-channel-switch-v52' aria-label='报告渠道'>"
        f"<a class='{'active' if active == 'meituan' else ''}' href='report.html'>美团</a>"
        f"<a class='{'active' if active == 'ctrip' else ''}' href='ctrip_report.html'>携程</a>"
        "</div>"
    )


def inject_channel_switch(html_text: str, active: str = "meituan") -> str:
    """Add two relative report links without changing the existing Meituan body."""
    if "OTA_CHANNEL_SWITCH_V52" not in html_text:
        html_text = html_text.replace("</head>", CHANNEL_STYLE + "</head>", 1)
    if "ota-channel-switch-v52" in html_text.split("</head>", 1)[-1]:
        return html_text

    switch = _switch_html(active)
    html_text, count = _PRINT_BUTTON_RE.subn(
        lambda match: match.group(1) + switch,
        html_text,
        count=1,
    )
    if count == 0:
        html_text, count = _TOP_ACTIONS_RE.subn(
            lambda match: match.group(1) + switch,
            html_text,
            count=1,
        )
    if count == 0:
        html_text = html_text.replace("<body>", "<body>" + switch, 1)
    return html_text


CTRIP_ITEMS: tuple[dict[str, Any], ...] = (
    {"no": 1, "title": "月度经营趋势 YOY", "weight": "10", "period": "本月累计", "score": "8.0", "status": "已形成结果", "desc": "展示收入、平均房价、RevPAR、出租率及去年同期同比。", "fields": (("本月累计房费", "¥328,650"), ("去年同期房费", "¥301,880"), ("收入 YOY", "+8.87%"), ("本月出租率", "72.36%"))},
    {"no": 2, "title": "房型 RevPAR 与低效房型", "weight": "8", "period": "近30天", "score": "4.8", "status": "存在低效房型", "desc": "按近30天出租率识别低效房型并展示房型经营结果。", "fields": (("有售房型", "10"), ("低效房型", "2"), ("低效房型占比", "20.00%"), ("当前得分", "4.8 / 8"))},
    {"no": 3, "title": "平台流量漏斗分析", "weight": "15", "period": "近30天", "score": "9.0", "status": "部分低于竞争圈", "desc": "携程、去哪儿分别展示曝光、访客、订单页和成交漏斗。", "fields": (("列表曝光", "48,620"), ("APP访客", "8,420"), ("订单页访客", "1,420"), ("成交订单", "386"), ("竞争圈排名", "6 / 24"))},
    {"no": 4, "title": "用户来源画像", "weight": "展示", "period": "近30天", "score": "仅展示", "status": "已形成结果", "desc": "展示性别、年龄、本地异地、出行目的和预订习惯。", "fields": (("性别", "男性68% / 女性32%"), ("年龄段", "25–34岁占46%"), ("本地 / 异地", "36% / 64%"), ("主要客源城市", "贵阳、安顺、遵义"))},
    {"no": 5, "title": "竞争圈分析", "weight": "展示", "period": "近30天", "score": "仅展示", "status": "已形成结果", "desc": "展示竞争圈排名、均值、流失订单和主要流失竞对。", "fields": (("竞争圈排名", "8 / 24"), ("平均订单量", "412"), ("流失订单量", "36"), ("流失订单金额", "¥9,860"))},
    {"no": 6, "title": "PSI 服务质量分", "weight": "8", "period": "当前值", "score": "6.4", "status": "需继续提升", "desc": "展示 PSI 总分、基础分、奖励分、扣分和竞争圈排名。", "fields": (("PSI总分", "5.18"), ("基础分", "4.76"), ("奖励分", "+0.62"), ("扣分", "-0.20"), ("竞争圈排名", "9 / 24"))},
    {"no": 7, "title": "YOYO 卡 / 扫码住", "weight": "5", "period": "近30天", "score": "2.5", "status": "日均2–4单", "desc": "按近30天扫码订单换算日均扫码订单。", "fields": (("近30天扫码订单", "86单"), ("日均扫码订单", "2.87单"), ("扫码新增会员", "64人"), ("促销状态", "已开启"))},
    {"no": 8, "title": "信息完整度", "weight": "4", "period": "当前值", "score": "4.0", "status": "完整", "desc": "展示携程信息首页完整度及缺失项。", "fields": (("信息完整度", "100分"), ("基础信息缺失", "0"), ("政策缺失", "0"), ("设施缺失", "0"))},
    {"no": 9, "title": "推广数据：金字塔", "weight": "8", "period": "近30天", "score": "4.8", "status": "ROI中等", "desc": "展示投入、曝光、点击、订单、成交金额和 ROI。", "fields": (("推广产品", "金字塔"), ("投入金额", "¥3,260"), ("曝光量", "92,600"), ("推广订单", "128"), ("ROI", "7.62"))},
    {"no": 10, "title": "页面展示和入口基础", "weight": "3", "period": "最新快照", "score": "2.0", "status": "部分缺失", "desc": "检查门店后缀、地标商圈词、推荐词、标签和卖点。", "fields": (("门店后缀", "已配置"), ("地标 / 商圈词", "已命中"), ("推荐词 / 标签", "待补充"))},
    {"no": 11, "title": "房型名称与售卖房型", "weight": "4", "period": "最新快照", "score": "2.4", "status": "合格率不足80%", "desc": "展示房型名称长度、卖点命中、合格占比和售卖渠道。", "fields": (("房型总数", "10"), ("合格房型", "6"), ("合格占比", "60%"), ("售卖渠道", "携程 / Trip.com / 去哪儿"))},
    {"no": 12, "title": "口碑分析", "weight": "10", "period": "当前值", "score": "8.8", "status": "总体良好", "desc": "分别展示携程、去哪儿、同程旅行、智行评分。", "fields": (("携程", "4.72"), ("去哪儿", "4.61"), ("同程旅行", "4.68"), ("智行", "4.75"))},
    {"no": 13, "title": "权益中心", "weight": "4", "period": "当前值", "score": "2.4", "status": "已启用4项", "desc": "展示免费取消、提前入住、延迟退房、早餐等权益。", "fields": (("已报名权益", "4项"), ("免费取消", "已启用"), ("延迟退房", "已启用"), ("早餐", "未启用"))},
    {"no": 14, "title": "积分联盟", "weight": "3", "period": "近30天", "score": "1.8", "status": "已报名暂无成交", "desc": "展示报名状态、近30天订单、成交金额和平台覆盖。", "fields": (("报名状态", "已报名"), ("近30天订单", "0单"), ("成交金额", "¥0"), ("覆盖平台", "携程 / Trip.com / 去哪儿"))},
    {"no": 15, "title": "优享会", "weight": "3", "period": "当前值", "score": "3.0", "status": "正常", "desc": "展示参加状态、标签状态、参与房型和订单。", "fields": (("参加状态", "已参加"), ("标签状态", "正常展示"), ("参与房型", "8个"), ("近30天订单", "46单"))},
    {"no": 16, "title": "商旅专享价", "weight": "2", "period": "当前值", "score": "2.0", "status": "已开通", "desc": "展示开通状态、参与房型数和近30天订单。", "fields": (("开通状态", "已开通"), ("参与房型", "6个"), ("近30天订单", "32单"), ("字段状态", "成交金额待核验"))},
    {"no": 17, "title": "闪住", "weight": "2", "period": "当前值", "score": "0.0", "status": "待核验", "desc": "展示闪住开通状态和参与房型数。", "fields": (("开通状态", "待核验"), ("参与房型", "暂无数据"), ("后台入口", "待确认"))},
    {"no": 18, "title": "钟点房", "weight": "2", "period": "近30天", "score": "1.0", "status": "已配置暂无订单", "desc": "展示核心房型配置、促销状态和钟点房订单。", "fields": (("钟点房配置", "已配置"), ("核心房型", "2个"), ("促销状态", "已开启"), ("近30天订单", "0单"))},
    {"no": 19, "title": "旅拍", "weight": "2", "period": "当前值", "score": "2.0", "status": "已上传并认领", "desc": "展示旅拍上传、认领状态和数量。", "fields": (("旅拍上传", "已上传"), ("认领状态", "已认领"), ("旅拍数量", "18条"))},
    {"no": 20, "title": "首页视频", "weight": "1", "period": "当前值", "score": "1.0", "status": "已上传", "desc": "展示酒店预览视频或首页视频上传状态。", "fields": (("酒店预览视频", "1条"), ("首页视频", "已上传"), ("口径状态", "待确认是否重复"))},
    {"no": 21, "title": "挂牌 / 委托分销", "weight": "6", "period": "当前值", "score": "3.0", "status": "普通挂牌", "desc": "展示挂牌状态、挂牌等级、委托分销和权益等级。", "fields": (("挂牌状态", "已挂牌"), ("挂牌等级", "普通挂牌"), ("委托分销", "已启用"), ("权益等级", "基础"))},
    {"no": 22, "title": "多平台口径核验", "weight": "展示", "period": "本次报告", "score": "仅展示", "status": "存在待核验项", "desc": "展示实际取数平台、是否混合、是否可拆分和人工确认状态。", "fields": (("流量漏斗", "ctrip / qunar，可拆分"), ("口碑分析", "四平台，可拆分"), ("积分联盟", "multi，待核验"), ("金字塔", "multi，待核验"))},
)


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _ctrip_card(item: dict[str, Any]) -> str:
    fields = "".join(
        f"<div class='ctrip-metric-v52'><small>{_e(label)}</small><strong>{_e(value)}</strong></div>"
        for label, value in item["fields"]
    )
    score = item["score"] if item["weight"] == "展示" else f"{item['score']} / {item['weight']}"
    status_class = "warn" if any(token in item["status"] for token in ("待", "不足", "低于", "需", "存在", "暂无")) else "ok"
    return (
        f"<article class='ctrip-card-v52' id='ctrip-rule-{item['no']}'>"
        "<div class='ctrip-card-head-v52'>"
        f"<div class='ctrip-rule-no-v52'>{item['no']:02d}</div>"
        f"<div><h3>{_e(item['title'])}</h3><p>{_e(item['desc'])}</p></div>"
        "<div class='ctrip-card-meta-v52'>"
        f"<span><small>统计周期</small><b>{_e(item['period'])}</b></span>"
        f"<span><small>当前得分</small><b>{_e(score)}</b></span>"
        f"<em class='{status_class}'>{_e(item['status'])}</em>"
        "</div></div>"
        f"<div class='ctrip-metric-grid-v52'>{fields}</div>"
        "<details><summary>评分口径与数据来源</summary>"
        "<div class='ctrip-detail-v52'><div><b>主数据源</b><span>携程 eBooking / PMS</span></div>"
        "<div><b>页面状态</b><span>当前为携程页面模板，数据接入后替换为真实值</span></div></div></details>"
        "</article>"
    )


def build_ctrip_html(result: dict[str, Any]) -> str:
    hotel = _e(result.get("hotel_name") or "璞悦·奢电竞酒店")
    start = _e(result.get("period_start") or "-")
    end = _e(result.get("period_end") or "-")
    sidebar = "".join(
        f"<a href='#ctrip-rule-{item['no']}'><span>{item['no']:02d}</span>{_e(item['title'])}</a>"
        for item in CTRIP_ITEMS
    )
    cards = "".join(_ctrip_card(item) for item in CTRIP_ITEMS)
    return f"""<!doctype html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>携程｜酒店 OTA 全面诊断报告</title>
<style>
:root{{--bg:#f3f6f5;--paper:#fff;--ink:#1f2933;--muted:#68747f;--line:#dfe7e4;--green:#16845b;--shadow:0 10px 28px rgba(29,56,47,.08)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 Inter,Arial,'PingFang SC','Microsoft YaHei',sans-serif}}a{{color:inherit;text-decoration:none}}button{{font:inherit}}
.ctrip-topbar-v52{{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}
.ctrip-topbar-inner-v52{{max-width:1600px;margin:auto;padding:12px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px}}.ctrip-brand-v52 h1{{margin:0;font-size:21px}}.ctrip-brand-v52 p{{margin:2px 0 0;color:var(--muted);font-size:12px}}.ctrip-actions-v52{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.ctrip-btn-v52{{height:36px;padding:0 13px;border:1px solid var(--line);border-radius:8px;background:#fff;font-weight:800;cursor:pointer}}.ctrip-btn-v52.primary{{background:var(--ink);border-color:var(--ink);color:#fff}}
.ota-channel-switch-v52{{display:inline-flex;align-items:center;padding:3px;border:1px solid var(--line);border-radius:9px;background:#f5f8f7}}.ota-channel-switch-v52 a{{height:30px;display:inline-flex;align-items:center;justify-content:center;min-width:58px;padding:0 14px;border-radius:6px;color:var(--muted);font-weight:800}}.ota-channel-switch-v52 a.active{{background:#fff;color:var(--green);box-shadow:0 2px 8px rgba(31,41,51,.12)}}
.ctrip-page-v52{{max-width:1600px;margin:auto;padding:20px 24px 60px;display:grid;grid-template-columns:260px minmax(0,1fr);gap:20px}}.ctrip-side-v52{{position:sticky;top:80px;align-self:start;max-height:calc(100vh - 96px);overflow:auto;background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}}.ctrip-side-v52 h2{{margin:0;padding:14px;font-size:12px;color:var(--muted)}}.ctrip-side-v52 a{{display:flex;gap:9px;padding:9px 13px;border-top:1px solid #eef2f1;font-size:12px}}.ctrip-side-v52 a span{{width:28px;color:var(--green);font-weight:900}}
.ctrip-main-v52{{display:grid;gap:18px;min-width:0}}.ctrip-hero-v52,.ctrip-card-v52{{background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);overflow:hidden}}.ctrip-hero-v52{{padding:24px;background:linear-gradient(135deg,#173d34,#245e50 55%,#358b72);color:#fff}}.ctrip-hero-grid-v52{{display:grid;grid-template-columns:1.2fr 1fr;gap:20px}}.ctrip-hero-v52 h2{{margin:0;font-size:28px}}.ctrip-hero-v52 p{{margin:8px 0 0;color:rgba(255,255,255,.8)}}.ctrip-hero-stats-v52{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}.ctrip-hero-stats-v52 div{{padding:13px;border-radius:10px;background:#fff;color:var(--ink)}}.ctrip-hero-stats-v52 small{{display:block;color:var(--muted)}}.ctrip-hero-stats-v52 strong{{display:block;margin-top:5px;font-size:23px}}
.ctrip-card-head-v52{{display:grid;grid-template-columns:48px minmax(0,1fr) auto;gap:13px;align-items:start;padding:17px 18px;border-bottom:1px solid #edf2f0}}.ctrip-rule-no-v52{{width:42px;height:42px;display:grid;place-items:center;border-radius:10px;background:#e8f5ef;color:var(--green);font-size:16px;font-weight:900}}.ctrip-card-head-v52 h3{{margin:0;font-size:18px}}.ctrip-card-head-v52 p{{margin:4px 0 0;color:var(--muted);font-size:13px}}.ctrip-card-meta-v52{{display:flex;gap:7px;align-items:center;flex-wrap:wrap;justify-content:flex-end}}.ctrip-card-meta-v52 span{{min-width:96px;padding:7px 10px;border:1px solid #e2ebe7;border-radius:8px;background:#f7faf9}}.ctrip-card-meta-v52 small{{display:block;color:var(--muted);font-size:10px}}.ctrip-card-meta-v52 b{{display:block;margin-top:2px}}.ctrip-card-meta-v52 em{{font-style:normal;padding:5px 9px;border-radius:999px;font-size:11px;font-weight:850}}.ctrip-card-meta-v52 em.ok{{background:#e5f5ed;color:#15734e}}.ctrip-card-meta-v52 em.warn{{background:#fff4d9;color:#92610f}}
.ctrip-metric-grid-v52{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;padding:17px 18px;background:#fbfdfc}}.ctrip-metric-v52{{padding:12px;border:1px solid #e3ebe8;border-radius:9px;background:#fff}}.ctrip-metric-v52 small{{display:block;color:var(--muted);font-weight:700}}.ctrip-metric-v52 strong{{display:block;margin-top:5px;font-size:19px;word-break:break-word}}details{{border-top:1px solid #edf2f0}}summary{{cursor:pointer;padding:12px 18px;font-weight:800;color:#315348}}.ctrip-detail-v52{{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:0 18px 18px}}.ctrip-detail-v52 div{{padding:12px;border:1px solid var(--line);border-radius:9px}}.ctrip-detail-v52 span{{display:block;margin-top:4px;color:var(--muted);font-size:12px}}
@media(max-width:1000px){{.ctrip-page-v52{{grid-template-columns:1fr}}.ctrip-side-v52{{display:none}}.ctrip-metric-grid-v52{{grid-template-columns:repeat(2,1fr)}}.ctrip-hero-grid-v52{{grid-template-columns:1fr}}}}@media(max-width:640px){{.ctrip-topbar-inner-v52{{align-items:flex-start;flex-direction:column}}.ctrip-card-head-v52{{grid-template-columns:42px 1fr}}.ctrip-card-meta-v52{{grid-column:1/-1;justify-content:flex-start}}.ctrip-metric-grid-v52,.ctrip-detail-v52{{grid-template-columns:1fr}}}}@media print{{.ctrip-topbar-v52,.ctrip-side-v52{{display:none!important}}.ctrip-page-v52{{display:block;padding:0}}.ctrip-card-v52{{break-inside:avoid;box-shadow:none}}}}
</style>
</head>
<body>
<header class='ctrip-topbar-v52'><div class='ctrip-topbar-inner-v52'><div class='ctrip-brand-v52'><h1>酒店 OTA 全面诊断报告</h1><p>当前渠道：携程</p></div><div class='ctrip-actions-v52'><button class='ctrip-btn-v52' onclick="document.querySelectorAll('details').forEach(x=>x.open=!x.open)">展开 / 收起规则</button><button class='ctrip-btn-v52 primary' onclick='window.print()'>导出报告</button>{_switch_html('ctrip')}</div></div></header>
<div class='ctrip-page-v52'><aside class='ctrip-side-v52'><h2>携程诊断目录 · 22项</h2>{sidebar}</aside><main class='ctrip-main-v52'><section class='ctrip-hero-v52'><div class='ctrip-hero-grid-v52'><div><h2>{hotel}｜携程渠道诊断</h2><p>统计周期：{start} 至 {end}</p></div><div class='ctrip-hero-stats-v52'><div><small>综合得分</small><strong>73.9</strong></div><div><small>计分模块</small><strong>19项</strong></div><div><small>展示模块</small><strong>3项</strong></div><div><small>当前状态</small><strong>模板预览</strong></div></div></div></section>{cards}</main></div>
</body></html>"""


def build_html(result: dict[str, Any]) -> str:
    return inject_channel_switch(upstream.build_html(result), "meituan")


def build_markdown(result: dict[str, Any]) -> str:
    return upstream.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = upstream.write_reports(result, output_dir)
    report_path = Path(paths["report_html"])
    report_path.write_text(
        inject_channel_switch(report_path.read_text(encoding="utf-8"), "meituan"),
        encoding="utf-8",
    )
    ctrip_path = report_path.with_name("ctrip_report.html")
    ctrip_path.write_text(build_ctrip_html(result), encoding="utf-8")
    paths["ctrip_report_html"] = str(ctrip_path)
    return paths


__all__ = [
    "build_ctrip_html",
    "build_html",
    "build_markdown",
    "inject_channel_switch",
    "write_reports",
]
