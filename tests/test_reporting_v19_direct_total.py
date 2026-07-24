from marketing_diagnosis.reporting_v19 import _manual_crown_card, _score_base


def _result() -> dict:
    return {
        "hotel_name": "测试酒店",
        "period_start": "2026-07-01",
        "period_end": "2026-07-24",
        "visual_diagnosis": {
            "items": [
                {
                    "standard_item_id": 1,
                    "participates_in_score": True,
                    "base_score": 10,
                    "item_score": 8,
                },
                {
                    "standard_item_id": 5,
                    "participates_in_score": False,
                    "base_score": 5,
                    "item_score": 5,
                },
                {
                    "standard_item_id": 22,
                    "participates_in_score": True,
                    "base_score": 1,
                    "item_score": None,
                },
            ]
        },
    }


def test_crown_base_sums_only_scored_participating_items() -> None:
    assert _score_base(_result()) == 8


def test_crown_script_adds_manual_score_without_percentage_normalization() -> None:
    card = _manual_crown_card(_result())

    assert "const BASE_RAW=8.0;" in card
    assert "const raw=BASE_RAW+(score===null?0:score);" in card
    assert "node.textContent=String(Math.round(raw*100)/100);" in card
    assert "BASE_CONNECTED" not in card
    assert "raw/connected*100" not in card
