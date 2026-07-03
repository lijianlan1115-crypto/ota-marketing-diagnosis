# S14 OTA Operation Diagnosis Skill

## Purpose

Generate a report-only hotel OTA operation diagnosis report for a selected hotel, channel, and period. The skill reads controlled PMS/OTA/reputation/promotion/competitor/nearby-event data, produces `report.html`, `report.json`, `report.md`, and returns a Feishu-friendly summary or card.

This skill is an OpenClaw wrapper. The business engine lives under `marketing_diagnosis/`.

## When to use

Use this skill when the user asks for any of the following:

- S14诊断
- OTA诊断
- OTA全面诊断
- 运营诊断
- 生成诊断报告
- 美团诊断
- 携程诊断
- 多渠道诊断
- 酒店 OTA 经营分析报告

## Inputs

Preferred input fields:

- `data_source_mode`: `database` or `excel_upload`
- `hotel_id`: default `puyue`
- `hotel_name`: optional display name
- `platform`: `multi`, `meituan`, `ctrip`, or `fliggy`
- `period_start`: optional `YYYY-MM-DD`
- `period_end`: optional `YYYY-MM-DD`
- `period_days`: default `30`
- `input_excel_path`: required only for `excel_upload`
- `limit`: optional row limit for database extraction

## Outputs

The skill returns:

- `report_url`
- `report_file_path`
- `report_json`
- `report_markdown`
- `feishu_message`
- `feishu_card`
- `final_score`
- `risk_level`
- `cap_rules_triggered`
- `data_time_context`

## Safety boundary

This is a report-only skill.

It must not:

- update OTA prices;
- update OTA inventory;
- publish promotions;
- reply to OTA reviews;
- write to production databases;
- submit approval or execution requests.

All outputs are recommendations, diagnostics, or generated report artifacts only.

## Current analysis scope

The report currently covers:

- PMS经营底盘：ADR、出租率、RevPAR、收入、月度趋势；
- OTA流量漏斗：曝光量、曝光人数、计算曝光、一转、浏览、支付订单、二转；
- 最新日 / 上一日漏斗对比；
- 分渠道周期汇总；
- 口碑分析：累计/概览快照、全部明细、近30天、近90天、分渠道；
- 价格房型；
- 推广效率入口；
- 周边活动与需求建议；
- 评分规则命中明细；
- 总分封顶规则；
- AI整改动作建议。

## Data grain rule

Do not mix time grains silently. Each module should display its own grain and period:

- PMS经营：日粒度周期汇总；
- 月度趋势：月粒度；
- OTA漏斗：日粒度或快照行，支持最新日/上一日；
- 口碑概览：累计/快照；
- 评论明细：按评论日期拆全部、近30天、近90天；
- 价格/推广：通常是快照；
- 周边活动：事件日期口径。

## Exposure fallback rule

If true exposure volume is missing but exposure people is available, the skill may use exposure people as a temporary denominator for one-step conversion. The report must show both fields and clearly mark the calculation source.

## AI behavior

If `S14_AI_BASE_URL`, `S14_AI_API_KEY`, and `S14_AI_MODEL` are configured, the skill may call an OpenAI-compatible AI endpoint for narrative analysis and dynamic action plans.

If no AI endpoint is configured, use rule-based fallback. Do not claim the analysis came from AI externally beyond the generic report label `AI分析`.
