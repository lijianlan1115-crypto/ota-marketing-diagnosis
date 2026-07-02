# Yangli CSV Export Profile

This document records the database export shape used to build the first CSV bundle loader.

Supported CSV inputs:

- `jy01_hotel_statistics_daily_*`: mapped to `hotel_daily`; only rows where `dimension_type` and `dimension_name` are total operating metrics are used first.
- `rs01_room_revenue_daily_*`: fallback daily operating source; only `charge_subject=房费` rows are aggregated by `business_date`.
- `meituan_ota_business_metrics_*` and `ctrip_ota_business_metrics_*`: tall metric rows are pivoted into `ota_funnel` rows.
- `meituan_ota_goods_price_mapping_*` and `ctrip_ota_goods_price_mapping_*`: mapped to `products`.
- `meituan_ota_review_detail_*` and `ctrip_ota_review_detail_*`: mapped to `reviews`.

Ignored for now:

- price task tables
- mapping sync queue
- activity product detail
- promotion activity
- nearby event
- review ranking

They are kept out of the MVP report until dedicated promotion and event modules are added.

Run:

```bash
ota-marketing-diagnosis diagnose-csv --path yanglidata.zip --output reports
```
