import unittest

from marketing_diagnosis.reporting_v3 import build_html
from marketing_diagnosis.visual_diagnosis import build_visual_diagnosis


class VisualDiagnosisTests(unittest.TestCase):
    def test_exposure_uses_real_zero_and_daily_ratio(self):
        result = build_visual_diagnosis({"exposure_daily": [{
            "business_date": "2026-07-13", "total_exposure": 100,
            "non_ad_exposure": 70, "ad_exposure": 30,
            "ad_exposure_ratio_pct": 30,
        }]})
        item = result["items"][2]
        self.assertEqual(item["data_status"], "success")
        self.assertEqual(item["item_score"], 4)
        self.assertEqual(item["fields"][-1]["value"], .3)

    def test_missing_is_not_scored_as_zero(self):
        result = build_visual_diagnosis({})
        self.assertEqual(result["items"][2]["data_status"], "missing")
        self.assertIsNone(result["items"][2]["item_score"])
        self.assertEqual(result["items"][7]["data_status"], "zero")
        self.assertEqual(result["items"][7]["item_score"], 0)
        self.assertEqual(result["connected_base_score"], 5)

    def test_report_renders_23_item_database_section(self):
        visual = build_visual_diagnosis({})
        html = build_html({
            "hotel_name": "测试酒店", "platform": "meituan",
            "period_start": "2026-06-14", "period_end": "2026-07-13",
            "visual_diagnosis": visual, "metrics": {}, "data_quality": {},
            "module_scores": [], "rule_hits": [],
        })
        self.assertIn("23项可视化诊断结果", html)
        self.assertIn("id='rule-21'", html)
        self.assertIn("首页视频", html)
        self.assertIn("规则待确认", html)
        self.assertIn("数据库表：hotel_puyue.meituan_ota_video_upload_status", html)
        self.assertIn("对应字段：video_type、uploaded_count、required_count", html)


if __name__ == "__main__":
    unittest.main()
