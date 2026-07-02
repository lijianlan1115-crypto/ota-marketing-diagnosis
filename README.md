# OTA Marketing Diagnosis

独立的第三方 OTA 营销诊断工具。

它不属于 `hotel--ota-ai` 主项目，不接入飞书鉴权、调价、审批、live 执行或价格任务表。第一版聚焦：

- 读取 Excel
- 读取临时 SQLite / MySQL 数据库
- 标准化字段
- 用代码计算指标
- 生成 `report.json` 和 `report.md`

## 快速开始

```bash
python -m venv .venv
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
pip install -e .
```

### Excel 诊断

```bash
python -m marketing_diagnosis.cli diagnose-excel \
  --excel examples/sample_data.xlsx \
  --output reports
```

Excel 支持以下 sheet，英文名优先，也兼容常见中文 sheet 名：

| 标准 sheet | 说明 |
|---|---|
| `hotel_daily` | 每日经营数据 |
| `ota_funnel` | OTA 曝光、浏览、支付转化 |
| `products` | OTA 商品与价格梯度 |
| `reviews` | 公开评论与口碑 |
| `competitors` | 竞品价格、排名、活动标签 |

### 数据库诊断

```bash
python -m marketing_diagnosis.cli diagnose-db \
  --config examples/db_config.example.json \
  --output reports
```

第一版支持 SQLite，MySQL 为可选能力，需要安装 `pymysql`。

## 设计边界

本项目只做营销诊断：

- 不做飞书鉴权
- 不做 admin / owner / operator 权限
- 不做调价写入
- 不做审批
- 不做 live 执行
- 不读取主项目 SQLite 授权库
- 不复用主项目 OpenClaw 路由

公开 OTA 评论正文默认不脱敏，因为营销审核需要上下文。手机号、身份证、订单号、房号、客人姓名等敏感字段会脱敏。

## 报告输出

每次诊断输出：

```text
report.json
report.md
```

报告结构：

1. 酒店经营概览
2. OTA 流量漏斗诊断
3. 商品价格梯度诊断
4. 口碑评论诊断
5. 竞品对比诊断
6. 营销动作建议

## 测试

```bash
python -m unittest discover tests
```
