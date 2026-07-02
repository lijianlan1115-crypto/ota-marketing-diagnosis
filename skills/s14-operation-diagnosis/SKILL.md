# S14 OTA 营销诊断 Skill

这是独立的 OpenClaw Skill 包装层，负责把飞书/OpenClaw 请求挂到 `marketing_diagnosis` 运行时。

## 定位

- 只做 OTA 营销诊断报告。
- 只读 MySQL 或 Excel 上传。
- 输出 `report.html`、`report.json`、`report.md`。
- 不写调价、不走审批、不执行 live、不写 price_task。

## OpenClaw 入口

OpenClaw 应调用：

```python
from runtime import S14OperationDiagnosis

result = S14OperationDiagnosis({
    "db_dsn_env": "S14_DB_DSN",
    "report_output_dir": "/opt/openclaw/workspaces/ota-marketing-diagnosis/public/s14-reports",
    "public_base_url": "http://47.108.200.194:8088/s14-reports",
}).execute({
    "hotel_id": "puyue",
    "platform": "multi",
    "data_source_mode": "database",
    "dry_run": True,
})
```

Excel 上传模式：

```python
result = S14OperationDiagnosis({
    "report_output_dir": "/opt/openclaw/workspaces/ota-marketing-diagnosis/public/s14-reports",
    "public_base_url": "http://47.108.200.194:8088/s14-reports",
}).execute({
    "hotel_id": "puyue",
    "platform": "multi",
    "data_source_mode": "excel_upload",
    "input_excel_path": "/path/to/uploaded.xlsx",
    "dry_run": True,
})
```

## 环境变量

```bash
export S14_DB_DSN='mysql+pymysql://openclaw_user:URL_ENCODED_PASSWORD@127.0.0.1:3306/hotel_puyue?charset=utf8mb4'
export S14_REPORT_OUTPUT_DIR='/opt/openclaw/workspaces/ota-marketing-diagnosis/public/s14-reports'
export S14_PUBLIC_BASE_URL='http://47.108.200.194:8088/s14-reports'
```

## 飞书回复

Skill 返回：

- `feishu_card`：优先发送的交互卡片。
- `feishu_message`：卡片不可用时的文本兜底。
- `report_url`：HTML 报告链接。

机器人层不要重新总结业务结果，直接发送 `feishu_card`，失败时发送 `feishu_message`。
