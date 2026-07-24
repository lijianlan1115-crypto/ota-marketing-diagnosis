from marketing_diagnosis.meituan_score_summary import refresh_meituan_summary


def test_meituan_total_sums_only_scoring_items() -> None:
    result = {
        "visual_diagnosis": {
            "items": [
                {
                    "standard_item_id": 1,
                    "participates_in_score": True,
                    "base_score": 10,
                    "item_score": 8,
                },
                {
                    "standard_item_id": 2,
                    "participates_in_score": False,
                    "base_score": 5,
                    "item_score": 5,
                },
                {
                    "standard_item_id": 3,
                    "participates_in_score": True,
                    "base_score": 7,
                    "item_score": None,
                },
                {
                    "standard_item_id": 4,
                    "participates_in_score": True,
                    "base_score": 3,
                    "item_score": 0,
                },
            ]
        }
    }

    refresh_meituan_summary(result)

    summary = result["meituan_summary"]
    assert summary["total_score"] == 8
    assert summary["full_score"] == 20
    assert summary["scoring_items"] == 3
    assert summary["scored_items"] == 2
    assert summary["pending_items"] == 1

    visual = result["visual_diagnosis"]
    assert visual["raw_score"] == 8
    assert visual["normalized_score"] == 8
    assert visual["connected_base_score"] == 20
