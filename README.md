# OTA Marketing Diagnosis

独立的第三方 OTA 营销诊断工具。

它不属于 `hotel--ota-ai` 主项目。第一版聚焦：

- 读取 Excel
- 读取数据库导出的 CSV 文件夹或 zip
- 读取临时 SQLite / MySQL 配置
- 标准化字段
- 用代码计算指标
- 生成 `report.json` 和 `report.md`

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

## 数据库 CSV 导出诊断

```bash
ota-marketing-diagnosis diagnose-csv --path yanglidata.zip --output reports
```

`--path` 可以是 CSV 文件夹，也可以是数据库导出的 zip。当前已支持这些导出表的自动识别：

- `jy01_hotel_statistics_daily`
- `rs01_room_revenue_daily`
- `meituan_ota_business_metrics` / `ctrip_ota_business_metrics`
- `meituan_ota_goods_price_mapping` / `ctrip_ota_goods_price_mapping`
- `meituan_ota_review_detail` / `ctrip_ota_review_detail`

其中 `jy01` 用作历史日经营主表；没有 `jy01` 时，会用 `rs01` 里 `charge_subject=房费` 的行按日聚合补经营数据。

## 临时数据库诊断

```bash
ota-marketing-diagnosis diagnose-config --config examples/sqlite_config.json --output reports
```

配置文件指定临时库类型、表名映射和读取行数。第一版支持 SQLite，也预留 MySQL 读取能力。

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
