from __future__ import annotations

import unittest

from marketing_diagnosis.reporting_v31 import _manual_room_card, _script
from marketing_diagnosis.room_name_manual_v43 import (
    normalize_room_type_names,
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

    def test_merges_wrapped_long_names_but_keeps_complete_lines(self):
        names = normalize_room_type_names(
            "璞悦双床房(无电脑)免费停车+近贵\n"
            "州大学、璞悦双床房(无电脑)免费停车+近十字\n"
            "街；荣耀战场大床房电竞停车+不接待未\n"
            "成年+RTX4060/5"
        )
        self.assertEqual(
            names,
            [
                "璞悦双床房(无电脑)免费停车+近贵州大学",
                "璞悦双床房(无电脑)免费停车+近十字街",
                "荣耀战场大床房电竞停车+不接待未成年+RTX4060/5",
            ],
        )

        self.assertEqual(
            normalize_room_type_names("五人战队套房\n电竞双床房"),
            ["五人战队套房", "电竞双床房"],
        )

    def test_list_markers_force_a_new_room_boundary(self):
        self.assertEqual(
            normalize_room_type_names(
                "1. 荣耀战场大床房电竞停车+近地铁\n"
                "2. 璞悦双床房免费停车+近大学"
            ),
            ["荣耀战场大床房电竞停车+近地铁", "璞悦双床房免费停车+近大学"],
        )

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

    def test_report_contains_no_wrap_input_and_scoring_details(self):
        result = self._result()
        patch_manual_room_name_score(
            result,
            {"manual_inputs": [{"room_type_names": ["五人战队套房"]}]},
        )
        html = _manual_room_card(result["items"][0])
        self.assertIn("manual-room-textarea-v31", html)
        self.assertIn("wrap='off'", html)
        self.assertIn("即时计算", html)
        self.assertIn("卖点表达", html)
        self.assertIn("五人战队套房", html)
        self.assertIn("4分", html)

        script = _script()
        self.assertIn("completeRoom", script)
        self.assertIn("textarea.value=names.join", script)
        self.assertNotIn("split(/[\\n\\r,，、;；|]+/)", script)


if __name__ == "__main__":
    unittest.main()
