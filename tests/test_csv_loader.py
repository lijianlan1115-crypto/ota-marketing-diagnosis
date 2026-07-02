import unittest

from marketing_diagnosis.csv_loader import _pivot_business_metrics


class CsvLoaderTests(unittest.TestCase):
    def test_pivot_business_metrics(self):
        rows = [
            {"stats_period_type": "today", "business_date": "2026-07-02 00:00:00", "metric_name": "浏览人数", "metric_value": "100", "peer_average": "80", "competitor_rank": "3/21"},
            {"stats_period_type": "today", "business_date": "2026-07-02 00:00:00", "metric_name": "支付订单数", "metric_value": "8", "peer_average": "5", "competitor_rank": "2/21"},
            {"stats_period_type": "today", "business_date": "2026-07-02 00:00:00", "metric_name": "浏览-支付转化率", "metric_value": "0.08", "peer_average": "10.00", "competitor_rank": "2/21"},
        ]
        result = _pivot_business_metrics(rows, "meituan")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["views"], 100.0)
        self.assertEqual(result[0]["paid_orders"], 8.0)
        self.assertEqual(result[0]["payment_conversion_rate"], 0.08)
        self.assertEqual(result[0]["peer_avg_conversion_rate"], 0.1)


if __name__ == "__main__":
    unittest.main()
