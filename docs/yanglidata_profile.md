# Yangli Database Export Profile

This document records what the real database export looks like. The export is a schema and field reference only. It is not a product input and should not become a customer-facing workflow.

Use this profile to design:

- database table profiles
- field aliases
- aggregation rules
- missing-field diagnostics
- report evidence fields

Reference tables:

- `jy01_hotel_statistics_daily`: historical daily operating metrics. Use total operating rows as the primary day-level operating source.
- `rs01_room_revenue_daily`: room-fee detail. Use `charge_subject=房费` for day-level room-night and room-revenue reconciliation.
- `jd01_booking_detail`: booking and arrival detail. Useful for future real-time or hourly funnel modules.
- `jd04_inhouse_extension`: in-house / extension detail. Useful for future real-time occupancy modules.
- `kf11_room_status_snapshot`: room status snapshot. Useful for denominator and maintenance-room logic in real-time occupancy.
- `meituan_ota_business_metrics` and `ctrip_ota_business_metrics`: OTA funnel metrics in tall metric format.
- `meituan_ota_goods_price_mapping` and `ctrip_ota_goods_price_mapping`: OTA product and price mapping.
- `meituan_ota_review_overview` and `ctrip_ota_review_overview`: review summary.
- `meituan_ota_review_detail` and `ctrip_ota_review_detail`: public review detail.
- `meituan_ota_promotion_activity` and `ctrip_ota_promotion_activity`: promotion activity.
- `meituan_ota_activity_product_detail` and `ctrip_ota_activity_product_detail`: activity products.
- `meituan_ota_nearby_event`: nearby event opportunity reference.

Product boundary:

- Formal user input remains Excel upload or configured temporary database access.
- Database export CSV / zip files are not formal runtime input.
- The report tool must not write prices, approvals, live actions, or price-task rows.
