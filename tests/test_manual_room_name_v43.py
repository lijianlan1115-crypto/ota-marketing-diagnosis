from __future__ import annotations

import unittest

from marketing_diagnosis.reporting_v31 import _manual_room_card
from marketing_diagnosis.room_name_manual_v43 import (
    parse_room_type_names_from_text,
    patch_manual_room_name_score,
)


class ManualRoomNameTests(unittest.TestCase):
    def _result(self):
        return {
            "items": [
                {
                    "standard_item_id": 11,
                    "item_name": "房型名称卖点优化",
                    "base_score": 4,
                    "participates_in_score": True,
                    "fields": [],
                }
            ]
        }

    def test_parses_feishu_text_or_voice_transcript(self):
        names = parse_room_type_names_from_text(
            "请诊断，房型名称：五人战队套房、电竞双床房"
        )
        self.assertEqual(names, ["五人战队套房", "电竞双床房"])

    def test_missing_manual_input_is_mandatory_zero(self):
        result = self._result()
        patch_manual_room_name_score(result, {})
        item = result["items"][0]
        self.assertEqual(item["item_score"], 0)
        self.assertEqual(item["score_ratio"], 0)
        self.assertEqual(item["data_status"], "zero")
        self.assertIn("按0分计入总分", item["note"])

    def test_all_names_must_be_longer_than_five_and_have_selling_point(self):
        result = self._result()
        patch_manual_room_name_score(
            result,
            {
                "manual_inputs": [
                    {
                        "room_type_names": ["五人战队套房", "电竞双床房"],
                        "source_table": "飞书语音转写人工输入",
                    }
                ]
            },
        )
        item = result["items"][0]
        self.assertEqual(item["item_score"], 4)
        self.assertTrue(all(record["passed"] for record in item["records"]))

        result = self._result()
        patch_manual_room_name_score(
            result,
            {"manual_inputs": [{"room_type_names": ["璞悦双床房"]}]},
        )
        item = result["items"][0]
        self.assertEqual(item["item_score"], 0)
        self.assertEqual(item["records"][0]["character_count"], 5)
        self.assertFalse(item["records"][0]["passed"])

    def test_report_contains_page_input_and_scoring_details(self):
        result = self._result()
        patch_manual_room_name_score(
            result,
            {"manual_inputs": [{"room_type_names": ["五人战队套房"]}]},
        )
        html = _manual_room_card(result["items"][0])
        self.assertIn("manual-room-textarea-v31", html)
        self.assertIn("即时计算", html)
        self.assertIn("卖点表达", html)
        self.assertIn("五人战队套房", html)
        self.assertIn("4分", html)


if __name__ == "__main__":
    unittest.main()
