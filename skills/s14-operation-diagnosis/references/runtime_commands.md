# S14 OpenClaw Runtime Commands

## 数据库模式

```bash
export S14_DB_DSN='mysql+pymysql://openclaw_user:URL_ENCODED_PASSWORD@127.0.0.1:3306/hotel_puyue?charset=utf8mb4'
export S14_REPORT_OUTPUT_DIR='/opt/openclaw/workspaces/ota-marketing-diagnosis/public/s14-reports'
export S14_PUBLIC_BASE_URL='http://47.108.200.194:8088/s14-reports'

python - <<'PY'
from skills.s14_operation_diagnosis.runtime import S14OperationDiagnosis
PY
```

如果直接从 skill 目录测试：

```bash
cd skills/s14-operation-diagnosis
python - <<'PY'
from runtime import S14OperationDiagnosis
result = S14OperationDiagnosis({
    'db_dsn_env': 'S14_DB_DSN',
    'report_output_dir': '../../public/s14-reports',
    'public_base_url': 'http://47.108.200.194:8088/s14-reports',
}).execute({
    'hotel_id': 'puyue',
    'platform': 'multi',
    'data_source_mode': 'database',
    'dry_run': True,
})
print(result['report_url'])
PY
```

## Excel 上传模式

```bash
cd skills/s14-operation-diagnosis
python - <<'PY'
from runtime import S14OperationDiagnosis
result = S14OperationDiagnosis({'report_output_dir': '../../public/s14-reports'}).execute({
    'hotel_id': 'puyue',
    'platform': 'multi',
    'data_source_mode': 'excel_upload',
    'input_excel_path': '/path/to/uploaded.xlsx',
    'dry_run': True,
})
print(result['report_file_path'])
PY
```

## 禁止

- 禁止 CSV/zip 作为正式运行入口。
- 禁止传入模型拼出来的 `metrics` 或 `business_fields`。
- 禁止将 S14 输出接到价格写入、审批或 live 执行。
