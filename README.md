# OTA Marketing Diagnosis

独立的第三方 OTA 营销诊断工具。

它不属于 `hotel--ota-ai` 主项目。第一版聚焦：

- 读取 Excel
- 读取阿里服务器本机 MySQL 诊断库
- 标准化字段
- 用代码计算指标
- 生成 `report.json`、`report.md` 和完整 `report.html`
- 以 `skills/s14-operation-diagnosis` 形式挂载到 OpenClaw

数据库导出的 CSV/zip 只作为字段画像和开发参考，不作为正式产品入口，也不作为 CLI 运行入口。

## 快速开始

```bash
python -m venv .venv
pip install -e .
```

MySQL 读取需要安装：

```bash
pip install pymysql
```

## OpenClaw 挂载

推荐把本仓库作为独立 workspace 放到服务器：

```bash
cd /opt/openclaw/workspaces
git clone https://github.com/TAI-YE-1/ota-marketing-diagnosis.git
cd ota-marketing-diagnosis
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

配置环境变量：

```bash
export S14_DB_DSN='mysql+pymysql://openclaw_user:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:3306/hotel_puyue?charset=utf8mb4'
export S14_REPORT_OUTPUT_DIR='/opt/openclaw/workspaces/ota-marketing-diagnosis/public/s14-reports'
export S14_PUBLIC_BASE_URL='http://47.108.200.194:8088/s14-reports'
```

OpenClaw 应识别：

```text
skills/s14-operation-diagnosis/openclaw.skill.yaml
```

如果走飞书入口包装脚本，可调用：

```bash
python scripts/s14_feishu_entry.py --text 'S14诊断' --format card
```

返回值优先使用 `feishu_card`，失败时 fallback 到 `feishu_message`。

## 生成样例 Excel

```bash
python scripts/create_sample_excel.py
```

会生成：

```text
examples/sample_data.xlsx
```

## Excel 诊断

```bash
ota-marketing-diagnosis diagnose-excel --excel examples/sample_data.xlsx --output reports
```

也可以直接运行模块：

```bash
python -m marketing_diagnosis.main diagnose-excel --excel examples/sample_data.xlsx --output reports
```

Excel 支持以下 sheet：

| 标准 sheet | 说明 |
|---|---|
| `hotel_daily` | 每日经营数据 |
| `ota_funnel` | OTA 曝光、浏览、支付转化 |
| `products` | OTA 商品与价格梯度 |
| `reviews` | 公开评论与口碑 |
| `competitors` | 竞品价格、排名、活动标签 |

## 阿里服务器本机 MySQL 诊断

在服务器上设置 DSN：

```bash
export S14_DB_DSN='mysql+pymysql://openclaw_user:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:3306/hotel_puyue?charset=utf8mb4'
```

运行：

```bash
ota-marketing-diagnosis diagnose-db --dsn-env S14_DB_DSN --output reports
```

也可以直接传 DSN，但不建议把密码写进 shell 历史：

```bash
ota-marketing-diagnosis diagnose-db --dsn 'mysql+pymysql://user:password@127.0.0.1:3306/hotel_puyue?charset=utf8mb4' --output reports
```

`diagnose-db` 会按内置 `puyue_mysql_reference` profile 读取真实表并聚合成报告数据。

## 配置文件诊断

```bash
ota-marketing-diagnosis diagnose-config --config examples/sqlite_config.json --output reports
```

配置文件适合开发调试或替代数据库，不是主要生产入口。

## 数据库画像参考

`yanglidata.zip` 这类数据库导出文件只用于确认真实表结构、真实字段名、空值情况和字段口径。它的结论会沉淀到数据库 profile、字段映射和聚合规则里，不会要求最终用户上传数据库导出包。

当前参考表包括：

- `jy01_hotel_statistics_daily`
- `rs01_room_revenue_daily`
- `jd01_booking_detail`
- `jd04_inhouse_extension`
- `kf11_room_status_snapshot`
- `meituan_ota_business_metrics` / `ctrip_ota_business_metrics`
- `meituan_ota_goods_price_mapping` / `ctrip_ota_goods_price_mapping`
- `meituan_ota_review_detail` / `ctrip_ota_review_detail`
- `meituan_ota_promotion_activity` / `ctrip_ota_promotion_activity`
- `meituan_ota_nearby_event`

## 项目边界

本项目只生成营销诊断报告，不做权限体系、调价写入、审批或线上执行。

公开 OTA 评论正文默认不脱敏，因为营销审核需要上下文。联系方式、订单号、房号、客人姓名等敏感字段会脱敏。

## 报告输出

```text
report.json
report.md
report.html
```

`report.html` 是完整可打开报告，包含总览、M01-M08 评分、经营、OTA 漏斗、商品价格、口碑、竞品、动作建议和数据质量章节。

报告包含：

- final_score
- risk_level
- M01-M08 module_scores
- metrics
- notes
- actions
- data_quality

## 测试

```bash
python -m unittest discover tests
python scripts/s14_feishu_entry.py --text 'S14诊断' --format card
```

## 后续计划

- 继续吸收旧原型 HTML 报告的更细布局和图表样式。
