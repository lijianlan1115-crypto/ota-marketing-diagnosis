from __future__ import annotations

from pathlib import Path

from marketing_diagnosis import reporting_v4


TEXT_REPLACEMENTS = {
    "总分、封顶、数据可信度与核心指标。各模块时间口径已放在对应模块标题下。": "关键经营指标、风险等级与数据可信度。",
    "总分、封顶、数据可信度与核心指标。": "关键经营指标、风险等级与数据可信度。",
    "各模块时间口径已放在对应模块标题下。": "",
    "数据时间粒度与口径": "数据口径",
    "不再把概览累计数误标成近30天。": "",
    "拆分累计/概览快照、全部评论明细、近30天、近90天和分渠道；不再把概览累计数误标成近30天。": "区分累计概览、评论明细、近30天、近90天和分渠道表现。",
    "模块诊断依赖各自模块顶部口径，不再单独聚合展示时间粒度。": "模块诊断结合各模块数据口径查看。",
    "PMS经营总览为日粒度汇总，两者不要混算。": "PMS经营总览为日粒度汇总，月度趋势用于观察长期方向。",
    "系统/数据口径：": "",
    "解释每个模块为什么得分、为什么扣分。": "展示各评分项的判断依据。",
    "字段</th>": "评分依据</th>",
    "operating.occupancy_rate": "出租率水平",
    "operating.revpar": "RevPAR收益水平",
    "operating.monthly_trend.revenue_mom": "收入与RevPAR趋势",
    "ota_funnel.exposure": "流量曝光规模",
    "ota_funnel.exposure_to_view_rate": "曝光到浏览效率",
    "ota_funnel.peer_rank": "竞争圈对比位置",
    "ota_funnel.payment_conversion_rate": "浏览到支付转化",
    "ota_funnel.paid_orders": "支付订单结果",
    "ota_funnel.sales_revenue/avg_order_value": "销售额与客单价",
    "price_ladder.min/max/span": "价格梯度与价差",
    "price_ladder.group_buy/hour_room": "团购与钟点房结构",
    "competitors.own_min_price_vs_competitor_avg_gap": "本店与竞对入口价差",
    "promotion.activity_count": "活动覆盖情况",
    "promotion.promo_roi": "推广ROI完整度",
    "page.image/video/tags": "页面图片、视频和标签基础",
    "products.product_count/room_type_count": "商品和房型承接",
    "reputation.rating/review_count": "评分与评价规模",
    "reputation.negative_rate/unreplied": "差评与未回复情况",
    "data_quality.missing_fields": "关键字段完整度",
    "data_quality.empty_sections": "空模块情况",
}


def _clean_html(html: str) -> str:
    for old, new in TEXT_REPLACEMENTS.items():
        html = html.replace(old, new)
    return html


def build_html(result: dict) -> str:
    return _clean_html(reporting_v4.build_html(result))


def build_markdown(result: dict) -> str:
    return reporting_v4.build_markdown(result)


def write_reports(result: dict, output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v4.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(_clean_html(html_path.read_text(encoding="utf-8")), encoding="utf-8")
    return paths
