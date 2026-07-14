import json
import tempfile
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from marketing_diagnosis.reporting_v6 import write_reports


class ReportSerializationTests(unittest.TestCase):
    def test_mysql_native_values_are_json_serializable(self):
        result = {
            "business_date": date(2026, 7, 14),
            "snapshot_time": datetime(2026, 7, 14, 15, 30),
            "amount": Decimal("123.45"),
            "metrics": {}, "data_quality": {}, "module_scores": [], "rule_hits": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            paths = write_reports(result, directory)
            payload = json.loads(Path(paths["report_json"]).read_text(encoding="utf-8"))
        self.assertEqual(payload["business_date"], "2026-07-14")
        self.assertEqual(payload["snapshot_time"], "2026-07-14T15:30:00")
        self.assertEqual(payload["amount"], 123.45)


if __name__ == "__main__":
    unittest.main()
