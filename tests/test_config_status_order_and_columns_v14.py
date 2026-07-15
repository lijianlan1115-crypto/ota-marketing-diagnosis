from __future__ import annotations

import unittest

from marketing_diagnosis.reporting_v10 import _CONFIG_NUMBERS, _config_group


class ConfigStatusOrderAndColumnsTest(unittest.TestCase):
    def _items(self):
        return {
            number: {
                "standard_item_id": number,
                "item_name": f"配置{number}",
                "base_score": 1,
                "item_score": 1 if number != 20 else None,
                "data_status": "success" if number != 20 else "pending_rule",
                "fields": [
                    {"label": "开通状态", "value": "OPEN" if number != 20 else "PENDING"},
                    {"label": "报名状态", "value": "OPEN"},
                    {"label": "生效状态", "value": "OPEN"},
                ],
                "source_table": "hotel_puyue.meituan_ota_promotion_status",
                "source_fields": ["status"],
            }
            for number in reversed(_CONFIG_NUMBERS)
        }

    def test_rows_are_rendered_in_fixed_item_number_order(self):
        html = _config_group(self._items())
        positions = [html.index(f"id='rule-{number}'") for number in _CONFIG_NUMBERS]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("15–20 / 23", html)

    def test_registration_and_effective_columns_are_removed(self):
        html = _config_group(self._items())
        header = html.split("<thead><tr>", 1)[1].split("</tr></thead>", 1)[0]
        self.assertEqual(header.count("<th>"), 6)
        self.assertIn("<th>开通状态</th>", header)
        self.assertNotIn("报名状态", header)
        self.assertNotIn("生效状态", header)


if __name__ == "__main__":
    unittest.main()
