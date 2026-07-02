# OTA Marketing Diagnosis

独立的第三方 OTA 营销诊断工具。

它不属于 `hotel--ota-ai` 主项目。第一版聚焦：

- 读取 Excel
- 读取临时 SQLite / MySQL 配置
- 标准化字段
- 用代码计算指标
- 生成 `report.json` 和 `report.md`

数据库导出的 CSV/zip 只作为字段画像和开发参考，不作为正式产品入口，也不作为 CLI 运行入口。

## 快速开始

```bash
python -m venv .venv
pip install -e .
```

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

## 临时数据库诊断

```bash
ota-marketing-diagnosis diagnose-config --config examples/sqlite_config.json --output reports
```

配置文件指定临时库类型、表名映射和读取行数。第一版支持 SQLite，也预留 MySQL 读取能力。

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
```

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
```

## 后续计划

- 从旧原型 `D:\hotel\s14-feishu-test\s14-feishu-test` 继续迁移更完整的 HTML 报告模板。
