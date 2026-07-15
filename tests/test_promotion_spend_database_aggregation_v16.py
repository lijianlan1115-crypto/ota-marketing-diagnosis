from __future__ import annotations

import unittest

from marketing_diagnosis.db_loader_v6 import _promotion_spend_summary
from marketing_diagnosis.visual_diagnosis_v7 import build_visual_diagnosis


class FakeCursor:
    def __init__(self):
        self.sql = ""
        self.params = []
        self._result = []

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = list(params or [])
        if sql.startswith("SHOW COLUMNS"):
            self._result = [
                {"Field": "hotel_id"},
                {"Field": "transaction_time"},
                {"Field": "transaction_type"},
                {"Field": "transaction_amount"},
            ]
        else:
            self._result = [
                {"promotion_spend": 500, "transaction_count": 5}
            ]

    def fetchall(self):
        return list(self._result)

    def fetchone(self):
        return self._result[0] if self._result else None


class PromotionSpendDatabaseAggregationTest(unittest.TestCase):
    def test_database_query_filters_period_and_sums_absolute_expense(self):
        cursor = FakeCursor()
        summary, diag = _promotion_spend_summary(
            cursor,
            "meituan_ota_promotion_finance_detail",
            "puyue",
            "2026-06-16",
            "2026-07-15",
        )

        self.assertEqual(summary["transaction_amount"], 500)
        self.assertEqual(summary["transaction_count"], 5)
        self.assertTrue(summary["promotion_spend_summary"])
        self.assertEqual(diag["status"], "ok")
        self.assertIn("SUM(ABS(CAST(`transaction_amount`", cursor.sql)
        self.assertIn("DATE(transaction_time) >= %s", cursor.sql)
        self.assertIn("DATE(transaction_time) <= %s", cursor.sql)
        self.assertEqual(
            cursor.params,
            ["推广通支出", "puyue", "2026-06-16", "2026-07-15"],
        )

    def test_visual_item_uses_authoritative_summary(self):
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
        item = next(
            row
            for row in result["items"]
            if row["standard_item_id"] == 9
        )
        fields = {field["label"]: field["value"] for field in item["fields"]}

        self.assertEqual(fields["近30天推广投入"], 500)
        self.assertAlmostEqual(fields["ROI"], 53358.04 / 500)
        self.assertEqual(item["data_status"], "pending_rule")


if __name__ == "__main__":
    unittest.main()
