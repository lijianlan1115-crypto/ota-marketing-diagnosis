from marketing_diagnosis.ctrip_page_entry_v66 import build_page_entry_item
from marketing_diagnosis.ctrip_report import build_html


def test_page_entry_uses_hotel_name_and_keeps_missing_page_fields_pending():
    item = build_page_entry_item(
        {
            "ctrip_promotion_performance_30d": [
                {
                    "hotel_name": "贵阳智町·栖筑优品酒店(紫林庵站妇幼保健院店)",
                    "snapshot_time": "2026-07-21 20:14:00",
                }
            ]
        }
    )

    assert item["item_score"] == 2.0
    assert item["data_status"] == "partial"
    assert item["fields"][1]["value"] == "已命中"
    assert "站" in item["fields"][2]["value"]
    assert item["fields"][3]["value"] == "待接入"


def test_page_entry_card_does_not_show_database_status_codes():
    item = build_page_entry_item(
        {"ctrip_promotion_performance_30d": [{"hotel_name": "测试酒店"}]}
    )
    output = build_html({"hotel_name": "测试酒店", "ctrip_items": {"10": item}})
    card = output.split("id='rule-10'", 1)[1].split("id='rule-11'", 1)[0]

    assert "测试酒店" in card
    assert "待接入" in card
    assert "ctrip_ota_promotion_performance_30d.hotel_name" in card
    assert "ENABLED" not in card and "NOT_JOINED" not in card
