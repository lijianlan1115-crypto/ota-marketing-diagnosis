# Agent Instructions

This workspace is for S14 OTA marketing diagnosis only.

Rules:
- Default communication language is Chinese.
- Use the project runtime to generate reports. Do not invent scores, report paths, filenames, or data conclusions.
- For S14 trigger phrases, call `scripts/s14_feishu_entry.py` or the `s14-operation-diagnosis` skill runtime.
- Generated reports are runtime artifacts and must be written under `S14_REPORT_OUTPUT_DIR`, not committed to git.
- This project only generates diagnosis reports. It does not write prices, inventory, promotions, or review replies.

Validated runtime entry:

```bash
cd /opt/openclaw/workspaces/ota-marketing-diagnosis
source .venv/bin/activate
set -a
source /etc/hotel-ota-ai/hotel-ota.env
set +a
python scripts/s14_feishu_entry.py --text 'S14诊断' --format card
```
