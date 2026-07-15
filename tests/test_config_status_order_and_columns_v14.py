from __future__ import annotations

import unittest

from marketing_diagnosis.reporting_v10 import (
    _CONFIG_NUMBERS,
    _apply_numeric_tail_order,
    _config_group,
)


class ConfigStatusOrderAndColumnsTest(unittest.TestCase):
    def _items(self):
        numbers = (*_CONFIG_NUMBERS, 21, 22, 23)
        return {
            number: {
                "standard_item_id": number,
                "item_name": f"配置{number}",
                "base_score": 1,
                "item_score": 1 if number != 20 else None,
                "participates_in_score": True,
                "data_status": "success" if number != 20 else "pending_rule",
                "fields": [
                    {"label": "开通状态", "value": "OPEN" if number != 20 else "PENDING"},
                    {"label": "报名状态", "value": "OPEN"},
                    {"label": "生效状态", "value": "OPEN"},
                ],
                "source_table": "hotel_puyue.meituan_ota_promotion_status",
                "source_fields": ["status"],
            }
            for number in reversed(numbers)
        }

    def _result(self):
        return {"visual_diagnosis": {"items": list(self._items().values())}}

    def test_config_rows_only_contain_items_15_to_20_in_order(self):
        html = _config_group(self._items())
        positions = [html.index(f"id='rule-{number}'") for number in _CONFIG_NUMBERS]
        self.assertEqual(_CONFIG_NUMBERS, (15, 16, 17, 18, 19, 20))
        self.assertEqual(positions, sorted(positions))
        self.assertIn("15–20", html)
        self.assertNotIn("id='rule-23'", html)

    def test_registration_and_effective_columns_are_removed(self):
        html = _config_group(self._items())
        header = html.split("<thead><tr>", 1)[1].split("</tr></thead>", 1)[0]
        self.assertEqual(header.count("<th>"), 6)
        self.assertIn("<th>开通状态</th>", header)
        self.assertNotIn("报名状态", header)
        self.assertNotIn("生效状态", header)

    def test_item_23_is_inserted_after_item_22(self):
        source = (
            "<article class='diagnosis-card config-status-group' id='config-status-group'>旧汇总</article>"
            "<article class='diagnosis-card' id='rule-21'>项目21</article>"
            "<article class='diagnosis-card' id='rule-22'>项目22</article>"
        )
        html = _apply_numeric_tail_order(source, self._result())
        self.assertLess(html.index("id='rule-21'"), html.index("id='rule-22'"))
        self.assertLess(html.index("id='rule-22'"), html.index("id='rule-23'"))


if __name__ == "__main__":
    unittest.main()
