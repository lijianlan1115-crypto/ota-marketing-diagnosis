from __future__ import annotations

import unittest

from marketing_diagnosis.db_loader_v7 import _promotion_spend_summary_resilient
from marketing_diagnosis.visual_diagnosis_v7 import build_visual_diagnosis


class FakeCursor:
    def __init__(self):
        self.sql_calls: list[tuple[str, list[object]]] = []
        self._rows: list[dict] = []

    def execute(self, sql, params=None):
        self.sql_calls.append((sql, list(params or [])))
        if sql.startswith("SHOW COLUMNS"):
            self._rows = [
                {"Field": "transaction_time"},
                {"Field": "transaction_type"},
                {"Field": "transaction_amount"},
            ]
        elif "COUNT(*) AS transaction_count" in sql:
            self._rows = [{"promotion_spend": 0, "transaction_count": 0}]
        else:
            self._rows = [
                {"transaction_type": " 推广通支出 ", "amount_value": -100},
                {"transaction_type": "推广通支出\n", "amount_value": -100},
                {"transaction_type": "推广 通 支出", "amount_value": -100},
                {"transaction_type": "\t推广通支出", "amount_value": -100},
                {"transaction_type": "推广通支出", "amount_value": -100},
            ]

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class PromotionSpendWhitespaceFallbackTest(unittest.TestCase):
    def test_fallback_restores_verified_500_spend(self):
        cursor = FakeCursor()
        summary, diag = _promotion_spend_summary_resilient(
            cursor,
            "meituan_ota_promotion_finance_detail",
            "puyue",
            "2026-06-16",
            "2026-07-15",
        )

        self.assertEqual(summary["transaction_amount"], 500)
        self.assertEqual(summary["transaction_count"], 5)
        self.assertEqual(diag["match_mode"], "python_whitespace_fallback")
        self.assertIn("TRIM(`transaction_type`) = %s", cursor.sql_calls[1][0])

    def test_visual_item_receives_500_and_roi(self):
        result = build_visual_diagnosis(
            {
                "promotion_finance": [
                    {
                        "transaction_type": "推广通支出",
                        "transaction_amount": 500,
                        "promotion_spend_summary": True,
                    }
                ],
                "promotion_revenue": [
                    {"period_month": "2026-07", "room_revenue": 53358.04}
                ],
            }
        )
        item = next(row for row in result["items"] if row["standard_item_id"] == 9)
        fields = {field["label"]: field["value"] for field in item["fields"]}

        self.assertEqual(fields["近30天推广投入"], 500)
        self.assertAlmostEqual(fields["ROI"], 53358.04 / 500)
        self.assertEqual(item["data_status"], "pending_rule")


if __name__ == "__main__":
    unittest.main()
