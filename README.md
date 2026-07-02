# OTA Marketing Diagnosis

独立的第三方 OTA 营销诊断工具。

它不属于 `hotel--ota-ai` 主项目。第一版聚焦：

- 读取 Excel
- 标准化字段
- 用代码计算指标
- 生成 `report.json` 和 `report.md`

## 快速开始

```bash
python -m venv .venv
pip install -e .
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

## 项目边界

本项目只生成营销诊断报告，不做权限体系、调价写入、审批或线上执行。

公开 OTA 评论正文默认不脱敏，因为营销审核需要上下文。联系方式、订单号、房号、客人姓名等敏感字段会脱敏。

## 报告输出

```text
report.json
report.md
```

## 测试

```bash
python -m unittest discover tests
```

## 后续计划

- 补充临时数据库输入命令。
- 补充样例 Excel。
- 从旧原型 `D:\hotel\s14-feishu-test\s14-feishu-test` 迁移更完整的数据库读取和报告模板。
