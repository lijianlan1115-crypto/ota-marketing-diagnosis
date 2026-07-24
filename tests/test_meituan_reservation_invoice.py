from marketing_diagnosis.meituan_reservation_invoice import patch_reservation_invoice
from marketing_diagnosis.meituan_reservation_invoice_report import rewrite_reservation_invoice


def _result() -> dict:
    return {
        "visual_diagnosis": {
            "items": [
                {
                    "standard_item_id": 20,
                    "item_name": "预约开票",
                    "base_score": 2,
                    "participates_in_score": True,
                    "item_score": None,
                    "data_status": "missing",
                    "fields": [],
                }
            ]
        }
    }


def test_item_20_uses_reservation_invoice_code_and_name() -> None:
    result = _result()
    sections = {
        "promotion_status": [
            {
                "promotion_code": "reservation_invoice",
                "promotion_name": "预约发票",
                "status": "OPEN",
                "enroll_status": "OPEN",
                "effective_status": "OPEN",
                "snapshot_time": "2026-07-24 10:00:00",
            },
            {
                "promotion_code": "legacy_invoice",
                "promotion_name": "预约开票",
                "status": "CLOSED",
                "snapshot_time": "2026-07-24 11:00:00",
            },
        ]
    }

    patch_reservation_invoice(result, sections)

    item = result["visual_diagnosis"]["items"][0]
    assert item["item_name"] == "预约发票"
    assert item["data_status"] == "success"
    assert item["item_score"] == 2
    assert item["source_fields"][:2] == [
        "promotion_code=reservation_invoice",
        "promotion_name=预约发票",
    ]
    values = {field["label"]: field["value"] for field in item["fields"]}
    assert values["活动编码"] == "reservation_invoice"
    assert values["活动名称"] == "预约发票"
    assert values["开通状态"] == "OPEN"


def test_item_20_is_missing_when_only_legacy_name_exists() -> None:
    result = _result()
    sections = {
        "promotion_status": [
            {
                "promotion_code": "legacy_invoice",
                "promotion_name": "预约开票",
                "status": "OPEN",
            }
        ]
    }

    patch_reservation_invoice(result, sections)

    item = result["visual_diagnosis"]["items"][0]
    assert item["item_name"] == "预约发票"
    assert item["data_status"] == "missing"
    assert item["item_score"] is None


def test_report_uses_reservation_invoice_wording() -> None:
    html = "<h3>预约开票</h3><p>展示预约开票开关与生效状态。</p>"
    rewritten = rewrite_reservation_invoice(html)
    assert "预约开票" not in rewritten
    assert rewritten.count("预约发票") == 2
