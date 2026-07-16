from __future__ import annotations

import unittest

from marketing_diagnosis.db_loader_v11 import (
    DEFAULT_MYSQL_TABLES,
    _load_latest_promotion_performance,
)
from marketing_diagnosis.promotion_performance_v46 import (
    _score_ratio,
    patch_promotion_performance,
)
from marketing_diagnosis.reporting_v34 import _promotion_card


class _Cursor:
    def __init__(self):
        self.sql = ""
        self.params = []

    def execute(self, sql, params=None):
        self.sql = str(sql)
        self.params = list(params or [])

    def fetchall(self):
        if self.sql.startswith("SHOW COLUMNS"):
            return [
                {"Field": "hotel_id"},
                {"Field": "promotion_status"},
                {"Field": "spend_amount"},
                {"Field": "booking_order_amount"},
                {"Field": "snapshot_time"},
            ]
        return [
            {
                "hotel_id": "puyue",
                "promotion_status": "RUNNING",
                "spend_amount": 2000,
                "booking_order_amount": 24000,
                "snapshot_time": "2026-07-16 12:00:00",
            }
        ]


class PromotionPerformanceTests(unittest.TestCase):
    def _visual(self):
        return {
            "items": [
                {
                    "standard_item_id": 9,
                    "item_name": "推广数据",
                    "base_score": 8,
                    "participates_in_score": True,
                    "fields": [],
                }
            ]
        }

    def _sections(self, status="RUNNING", spend=2000, booking=24000):
        return {
            "promotion_finance": [
                {
                    "source_table": "meituan_ota_promotion_performance_30d",
                    "promotion_status": status,
                    "spend_amount": spend,
                    "booking_order_amount": booking,
                    "snapshot_time": "2026-07-16 12:00:00",
                }
            ]
        }

    def test_table_and_loader_mapping(self):
        self.assertEqual(
            DEFAULT_MYSQL_TABLES["meituan_promotion_performance_30d"],
            "meituan_ota_promotion_performance_30d",
        )
        row, diag = _load_latest_promotion_performance(
            _Cursor(),
            "meituan_ota_promotion_performance_30d",
            5000,
            "puyue",
        )
        self.assertEqual(row["promotion_status"], "RUNNING")
        self.assertEqual(row["spend_amount"], 2000)
        self.assertEqual(row["booking_order_amount"], 24000)
        self.assertEqual(diag["rows_used"], 1)

    def test_score_boundaries(self):
        self.assertEqual(_score_ratio("RUNNING", 1000, 20), 0)
        self.assertEqual(_score_ratio("STOPPED", 2000, 20), 0)
        self.assertEqual(_score_ratio("RUNNING", 2000, 4.99), 0)
        self.assertEqual(_score_ratio("RUNNING", 2000, 5), 0.60)
        self.assertEqual(_score_ratio("RUNNING", 2000, 10), 0.60)
        self.assertEqual(_score_ratio("RUNNING", 2000, 10.01), 1.0)

    def test_running_roi_above_ten_gets_full_score(self):
        visual = self._visual()
        patch_promotion_performance(visual, self._sections())
        item = visual["items"][0]
        self.assertEqual(item["item_score"], 8)
        self.assertAlmostEqual(item["promotion_performance"]["roi"], 12)
        labels = [field["label"] for field in item["fields"]]
        self.assertEqual(
            labels,
            ["推广状态", "近30天推广投入", "预订订单金额（元）", "ROI"],
        )

    def test_missing_or_inactive_is_mandatory_zero(self):
        visual = self._visual()
        patch_promotion_performance(visual, {})
        item = visual["items"][0]
        self.assertEqual(item["item_score"], 0)
        self.assertEqual(item["data_status"], "zero")

        visual = self._visual()
        patch_promotion_performance(
            visual,
            self._sections(status="PAUSED", spend=5000, booking=100000),
        )
        self.assertEqual(visual["items"][0]["item_score"], 0)

    def test_report_uses_near_30_day_labels(self):
        visual = self._visual()
        patch_promotion_performance(visual, self._sections())
        html = _promotion_card(visual["items"][0])
        for text in (
            "近30天",
            "推广状态",
            "近30天推广投入",
            "预订订单金额（元）",
            "ROI",
            "RUNNING",
        ):
            self.assertIn(text, html)
        self.assertNotIn("本月美团EBK订单金额", html)
        self.assertNotIn("待计算", html)


if __name__ == "__main__":
    unittest.main()
