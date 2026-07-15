from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "s14_feishu_entry.py"


class LiveS14SourceSelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="s14_live_flow_")
        self.previous_state_dir = os.environ.get("S14_STATE_DIR")
        os.environ["S14_STATE_DIR"] = self.tmp.name

        spec = importlib.util.spec_from_file_location(
            f"s14_feishu_entry_test_{id(self)}",
            SCRIPT,
        )
        assert spec and spec.loader
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.module.STATE_DIR = Path(self.tmp.name)
        self.module.STATE_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.previous_state_dir is None:
            os.environ.pop("S14_STATE_DIR", None)
        else:
            os.environ["S14_STATE_DIR"] = self.previous_state_dir
        self.tmp.cleanup()

    def test_trigger_card_only_asks_database_or_excel(self) -> None:
        card = self.module._source_selection_card()
        actions = card["card"]["elements"][1]["actions"]
        labels = [action["text"]["content"] for action in actions]
        sources = [action["value"]["source"] for action in actions]

        self.assertEqual(labels, ["数据库", "上传Excel"])
        self.assertEqual(sources, ["database", "excel"])
        rendered = str(card)
        self.assertNotIn("携程 / 美团", rendered)
        self.assertNotIn("选择渠道", rendered)

    def test_all_text_variants_use_unified_multi_platform(self) -> None:
        for text in ("S14诊断", "美团诊断", "携程诊断", "多渠道诊断"):
            with self.subTest(text=text):
                context = self.module._request_context(text)
                self.assertEqual(context["platform"], "multi")
                self.assertEqual(context["period_days"], 30)

    def test_excel_wait_state_is_scoped_to_chat_and_sender(self) -> None:
        self.module._set_flow_state(
            "awaiting_excel",
            chat_id="chat-a",
            sender_id="user-a",
        )

        same = self.module._get_flow_state("chat-a", "user-a")
        other_user = self.module._get_flow_state("chat-a", "user-b")
        other_chat = self.module._get_flow_state("chat-b", "user-a")

        self.assertEqual(same["state"], "awaiting_excel")
        self.assertIsNone(other_user)
        self.assertIsNone(other_chat)

    def test_excel_choice_enters_waiting_state_without_running_report(self) -> None:
        payload = self.module._handle_source_choice(
            "excel",
            chat_id="chat-a",
            sender_id="user-a",
            text="上传Excel",
            output_format="card",
        )

        state = self.module._get_flow_state("chat-a", "user-a")
        self.assertEqual(state["state"], "awaiting_excel")
        self.assertEqual(
            payload["card"]["header"]["title"]["content"],
            "S14诊断｜等待Excel附件",
        )

    def test_database_choice_runs_current_report_and_clears_state(self) -> None:
        self.module._set_flow_state(
            "awaiting_source",
            chat_id="chat-a",
            sender_id="user-a",
        )
        fake_result = {
            "feishu_card": {
                "msg_type": "interactive",
                "card": {
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": "报告完成",
                            },
                        }
                    ]
                },
            }
        }

        with patch.object(self.module, "_run_database", return_value=fake_result) as run:
            payload = self.module._handle_source_choice(
                "database",
                chat_id="chat-a",
                sender_id="user-a",
                text="数据库",
                output_format="card",
            )

        run.assert_called_once()
        self.assertIsNone(self.module._get_flow_state("chat-a", "user-a"))
        content = payload["card"]["elements"][0]["text"]["content"]
        self.assertTrue(content.startswith("**数据来源：** 数据库"))


if __name__ == "__main__":
    unittest.main()
