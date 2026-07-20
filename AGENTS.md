# Agent Instructions

This workspace is for S14 OTA marketing diagnosis only.

Rules:
- Default communication language is Chinese.
- Use the project runtime to generate reports. Do not invent scores, report paths, filenames, cards, buttons, or data conclusions.
- Generated reports are runtime artifacts and must be written under `S14_REPORT_OUTPUT_DIR`, not committed to git.
- This project only generates diagnosis reports. It does not write prices, inventory, promotions, or review replies.
- Current reports use the already mapped fields as one overall diagnosis. Never ask the user to choose Meituan, Ctrip, Fliggy, or multi-channel. Internally always use `platform=multi`.
- Never send internal development summaries such as “修复已就绪”, source-code change descriptions, test summaries, or root-cause tables to a normal Feishu user.
- Never say “点击上面卡片” unless an interactive card was actually included in the same outbound message.
- Never claim a report was generated unless the runtime returned a real non-empty `report_url`.

## Feishu flow

When the user sends `S14诊断`:

1. Prefer the Skill runtime's `source_selection` result. For an ordinary OpenClaw reply, send only its `feishu_message` field. Never send the complete result object or provider-native `feishu_card` JSON as assistant text.
2. OpenClaw must render rich UI through its own message/presentation layer. When executing the CLI wrapper through a shell/exec tool, always use `--format text` and send that stdout exactly once. It asks the user to type `数据库` or `上传Excel`.
3. For a database choice, invoke the Skill with `data_source_mode=database`, `platform=multi`, or call the same script with `--source-choice database`, using the same chat and sender IDs.
4. For an Excel choice, invoke the Skill with `data_source_mode=excel_pending`, or call the same script with `--source-choice excel`, using the same chat and sender IDs.
5. After Excel is selected, accept the same user's next `.xlsx` or `.xlsm` attachment in the same group without another @ mention. Download it locally and call the script with `--excel`, the same chat ID, the same sender ID, and `--format text`.
6. The pending Excel state expires after 10 minutes. Do not run an attachment diagnosis unless the same chat and sender have selected Excel.
7. For an interactive-card callback with action `s14_source`, pass its `source` value to `--source-choice`.
8. After database or Excel diagnosis completes, send `feishu_message` exactly once when using exec/CLI. A dedicated structured adapter may request `--format card --raw-card-json`, parse the JSON, and send it through the channel API; its stdout must never be copied into chat. The result must contain the actual HTML report URL.

Validated command pattern:

```bash
cd /opt/openclaw/workspaces/ota-marketing-diagnosis
source .venv/bin/activate
set -a
source /etc/hotel-ota-ai/hotel-ota.env
set +a
python scripts/s14_feishu_entry.py --text 'S14诊断' --chat-id CHAT_ID --sender-id SENDER_ID --format text
```

Always send the runtime output exactly once. Do not prepend, summarize, repeat, or replace it with an explanation of code changes.
