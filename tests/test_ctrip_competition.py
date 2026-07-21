from marketing_diagnosis.ctrip_competition import build_competition_item
from marketing_diagnosis.ctrip_report import competition_analysis_card, funnel_card
from marketing_diagnosis.rules_v5 import _split_competition_payload


def sections():
    return {
        "ota_funnel": [
            {
                "platform": "ctrip",
                "business_date": "2026-07-20",
                "period_type": "近30天",
                "exposure": 5160,
                "peer_exposure": 22347,
                "views": 736,
                "peer_views": 4793,
                "paid_orders": 9,
                "peer_paid_orders": 78,
            }
        ],
        "ctrip_business_metrics_funnel": [],
        "ctrip_competition_metrics_30d": [
            {
                "metric_code": "booking_order_count",
                "metric_name": "订单量",
                "metric_value": 9,
                "competitor_avg": 78,
                "competitor_rank": 22,
                "competitor_count": 48,
                "metric_unit": "order",
            },
            {
                "metric_code": "booking_order_count",
                "metric_name": "销售额",
                "metric_value": 2380,
                "competitor_avg": 16300,
                "competitor_rank": 20,
                "competitor_count": 48,
                "metric_unit": "CNY",
            },
            {
                "metric_code": "booking_order_count",
                "metric_name": "出租率",
                "metric_value": 56.2,
                "competitor_avg": 72.4,
                "competitor_rank": 18,
                "competitor_count": 48,
                "metric_unit": "%",
            },
            {
                "metric_code": "booking_order_count",
                "metric_name": "转化率",
                "metric_value": 4.76,
                "competitor_avg": 6.55,
                "competitor_rank": 23,
                "competitor_count": 48,
                "metric_unit": "%",
            },
            {
                "metric_code": "visitor_count",
                "metric_name": "访客量",
                "metric_value": 916,
                "competitor_avg": 5576.3,
                "competitor_rank": 22,
                "metric_unit": "person",
            },
        ],
        "ctrip_business_metrics_loss": [
            {
                "business_date": "2026-07-20 00:00:00",
                "metric_group": "流失诊断",
                "metric_name": "流失订单量",
                "metric_value": 13,
            },
            {
                "business_date": "2026-07-20 00:00:00",
                "metric_group": "流失诊断",
                "metric_name": "流失订单金额",
                "metric_value": 4567.89,
            },
        ],
        "ctrip_order_loss_monthly": [
            {
                "platform_scope": "ctrip",
                "period_month": "2026-07",
                "ranking_position": index,
                "competitor_hotel_name": f"携程竞对酒店{index}",
            }
            for index in range(1, 7)
        ]
        + [
            {
                "platform_scope": "qunar",
                "period_month": "2026-07",
                "ranking_position": index,
                "competitor_hotel_name": f"去哪儿竞对酒店{index}",
            }
            for index in range(1, 7)
        ],
    }


def split_items():
    combined = build_competition_item(sections(), {"item_score": 11.4})
    return _split_competition_payload(combined, {"item_score": 11.4})


def test_item_03_keeps_only_funnel_and_score():
    item_three, item_five = split_items()

    assert item_three["standard_item_id"] == 3
    assert item_three["item_score"] == 11.4
    assert len(item_three["funnel_stages"]) == 5
    assert "competition_metrics" not in item_three
    assert "loss_competitors" not in item_three

    output = funnel_card({"ctrip_items": {"3": item_three}})
    assert "我的酒店" in output
    assert "竞争圈平均" in output
    assert "列表页曝光量" in output
    assert "成交订单数" in output
    assert "竞争圈核心指标与排名" not in output
    assert "昨日流失与主要流失竞对" not in output


def test_item_05_keeps_core_rankings_loss_and_channel_tabs():
    item_three, item_five = split_items()

    assert item_five["standard_item_id"] == 5
    assert item_five["participates_in_score"] is False
    assert [entry["label"] for entry in item_five["competition_metrics"]] == [
        "订单量",
        "销售额",
        "出租率",
        "转化率",
    ]
    assert item_five["loss_summary"]["order_count"] == 13
    assert item_five["loss_summary"]["order_amount"] == 4567.89
    assert len(item_five["loss_competitors"]["ctrip"]) == 5
    assert len(item_five["loss_competitors"]["qunar"]) == 5

    output = competition_analysis_card({"ctrip_items": {"5": item_five}})
    assert "竞争圈核心指标与排名" in output
    assert "昨日流失与主要流失竞对" in output
    assert "data-loss-tab='ctrip'" in output
    assert "data-loss-tab='qunar'" in output
    assert "携程竞对酒店5" in output
    assert "去哪儿竞对酒店5" in output
    assert "订单量（单）" in output
    assert "销售额（元）" in output
    assert "CNY" not in output
    assert "person" not in output
    assert "9单" not in output
    assert "流量漏斗" not in output


def test_unknown_competition_metrics_are_not_rendered():
    _, item_five = split_items()
    output = competition_analysis_card({"ctrip_items": {"5": item_five}})

    assert "访客量" not in output
    assert "room_night" not in output
    assert "评分明细" not in output
