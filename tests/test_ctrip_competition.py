from marketing_diagnosis.ctrip_competition import build_competition_item
from marketing_diagnosis.ctrip_report import competition_card


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
        "ctrip_competition_metrics_30d": [
            {
                "metric_code": "booking_order_count",
                "metric_name": "订单量",
                "metric_value": 9,
                "competitor_avg": 78,
                "competitor_rank": 22,
                "competitor_count": 48,
            },
            {
                "metric_code": "sales_amount",
                "metric_name": "销售额",
                "metric_value": 2380,
                "competitor_avg": 16300,
                "competitor_rank": 20,
                "competitor_count": 48,
            },
            {
                "metric_code": "occupancy_rate",
                "metric_name": "出租率",
                "metric_value": 56.2,
                "competitor_avg": 72.4,
                "competitor_rank": 18,
                "competitor_count": 48,
            },
            {
                "metric_code": "conversion_rate",
                "metric_name": "转化率",
                "metric_value": 4.76,
                "competitor_avg": 6.55,
                "competitor_rank": 23,
                "competitor_count": 48,
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


def test_competition_item_keeps_all_rankings_and_top5_per_platform():
    item = build_competition_item(sections(), {"item_score": 11.4})

    assert item["item_score"] == 11.4
    assert [entry["label"] for entry in item["competition_metrics"]] == [
        "订单量",
        "销售额",
        "出租率",
        "转化率",
    ]
    assert item["loss_summary"]["order_count"] == 13
    assert item["loss_summary"]["order_amount"] == 4567.89
    assert len(item["loss_competitors"]["ctrip"]) == 5
    assert len(item["loss_competitors"]["qunar"]) == 5
    assert len(item["funnel_stages"]) == 3


def test_competition_card_removes_old_summary_cards_and_score_details():
    item = build_competition_item(sections(), {"item_score": 11.4})
    output = competition_card({"ctrip_items": {"3": item}})

    assert "竞争圈全部指标与排名" in output
    assert "昨日流失与主要流失竞对" in output
    assert "携程竞对酒店5" in output
    assert "去哪儿竞对酒店5" in output
    assert "11.4分" in output
    assert "流量规模" not in output
    assert "转化表现" not in output
    assert "评分明细" not in output
