# Agent Instructions

This workspace is for S14 OTA marketing diagnosis only.

Rules:
- Default communication language is Chinese.
- Use the project runtime to generate reports. Do not invent scores, report paths, filenames, or data conclusions.
- Generated reports are runtime artifacts and must be written under `S14_REPORT_OUTPUT_DIR`, not committed to git.
- This project only generates diagnosis reports. It does not write prices, inventory, promotions, or review replies.
- Current reports use the already mapped fields as one overall diagnosis. Never ask the user to choose Meituan, Ctrip, Fliggy, or multi-channel. Internally always use `platform=multi`.

## Feishu flow

When the user sends `S14诊断`:

1. Run `scripts/s14_feishu_entry.py` with the message text, current `chat_id`, current sender ID, and `--format card`.
2. Send the script output exactly once. It asks the user to select `数据库` or `上传Excel`.
3. For a database choice, call the same script with `--source-choice database`, using the same chat and sender IDs.
4. For an Excel choice, call the same script with `--source-choice excel`, using the same chat and sender IDs.
5. After Excel is selected, accept the same user's next `.xlsx` or `.xlsm` attachment in the same group without another @ mention. Download it locally and call the script with `--excel`, the same chat ID, the same sender ID, and `--format card`.
6. The pending Excel state expires after 10 minutes. Do not run an attachment diagnosis unless the same chat and sender have selected Excel.
7. For an interactive-card callback with action `s14_source`, pass its `source` value to `--source-choice`.

Validated command pattern:

```bash
cd /opt/openclaw/workspaces/ota-marketing-diagnosis
source .venv/bin/activate
set -a
source /etc/hotel-ota-ai/hotel-ota.env
set +a
python scripts/s14_feishu_entry.py --text 'S14诊断' --chat-id CHAT_ID --sender-id SENDER_ID --format card
```

Always send the script stdout exactly once. Do not prepend, summarize, or repeat it.
