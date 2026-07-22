from __future__ import annotations

from typing import Any


_ACTIVITY_CODES = {
    8: "information_completeness",
    14: "points_alliance",
    15: "preferred_club",
    16: "business_travel_price",
    18: "hourly_room",
    19: "travel_photo",
    20: "homepage_video",
    21: "listing_pass",
}
_INACTIVE = {"0", "false", "no", "not_joined", "not_jioned", "not_uploaded", "disabled", "closed", "inactive"}
_ACTIVE = {"1", "true", "yes", "joined", "enabled", "active", "uploaded", "open"}


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _words(row: dict[str, Any]) -> str:
    return " ".join(
        _text(row.get(key)).lower()
        for key in ("status", "status_detail", "metric_value", "metric_unit")
    )


def _state(row: dict[str, Any] | None) -> bool | None:
    if not row:
        return None
    words = " ".join(_text(row.get(key)).lower() for key in ("status", "status_detail"))
    inactive_words = _INACTIVE - {"0", "false", "no"}
    active_words = _ACTIVE - {"1", "true", "yes"}
    if any(value in words for value in inactive_words):
        return False
    enabled = row.get("enabled")
    if enabled not in (None, "") and _text(enabled).lower() in _INACTIVE:
        return False
    if any(value in words for value in active_words):
        return True
    if enabled not in (None, "") and _text(enabled).lower() in _ACTIVE:
        return True
    return None


def _field(label: str, value: Any, note: str = "") -> dict[str, Any]:
    return {"label": label, "value": value, "note": note}


def _item(
    no: int,
    score: float | None,
    status: str,
    source: str,
    fields: list[dict[str, Any]],
    note: str,
) -> dict[str, Any]:
    return {
        "standard_item_id": no,
        "participates_in_score": no != 17,
        "item_score": score,
        "data_status": status,
        "source": source,
        "fields": fields,
        "fields_complete": True,
        "note": note,
    }


def _activity(rows: list[dict[str, Any]], no: int) -> dict[str, Any] | None:
    code = _ACTIVITY_CODES[no]
    return next(
        (
            row
            for row in rows
            if _text(row.get("activity_code")).lower() == code
        ),
        None,
    )


def _activity_fields(
    row: dict[str, Any],
    *,
    status_label: str = "开通状态",
    include_coverage: bool = False,
) -> list[dict[str, Any]]:
    fields = [
        _decision(status_label, _state(row), positive="已开通", negative="未开通"),
        _field("参与房型", row.get("room_type_count")),
        _field("近30天订单", row.get("orders_30d")),
    ]
    if include_coverage:
        fields.append(_field("覆盖平台", row.get("platform_scope")))
    return fields


def _decision(label: str, state: bool | None, *, positive: str, negative: str) -> dict[str, Any]:
    value = positive if state is True else negative if state is False else "待核验"
    return _field(label, value)


def _rights_item(rows: list[dict[str, Any]]) -> dict[str, Any]:
    names = [_text(row.get("right_name")) for row in rows if _text(row.get("right_name"))]
    if not rows:
        return _item(13, None, "missing", "携程 eBooking / 促销推广 / 权益中心", [], "等待权益中心快照数据。")
    count = len(rows)
    score = 4.0 if count >= 5 else 2.4 if count >= 3 else 0.0
    item = _item(
        13,
        score,
        "success",
        "携程 eBooking / 促销推广 / 权益中心",
        [
            _field("已报名权益", f"{count}项"),
            _field("权益清单", "、".join(names) or None),
        ],
        "权益数量>=5项得4分，3-4项得2.4分，少于3项得0分。",
    )
    item["rights_list"] = names
    return item


def _information_item(row: dict[str, Any] | None) -> dict[str, Any]:
    source = "携程 eBooking / 信息维护 / 信息完整度"
    if not row:
        return _item(8, None, "missing", source, [], "等待信息完整度状态快照。")
    completeness = _number(row.get("metric_value"))
    fields = [
        _field(
            "信息完整度",
            None if completeness is None else f"{completeness:g}%",
        ),
        _field(
            "完整度结果",
            "已达标" if completeness is not None and completeness >= 100 else "未达标"
            if completeness is not None
            else "待核验",
        ),
    ]
    if completeness is None:
        return _item(8, None, "pending_rule", source, fields, "信息完整度数值无法由现有字段确认。")
    return _item(
        8,
        4.0 if completeness >= 100 else 0.0,
        "success",
        source,
        fields,
        "信息完整度达到100得4分，低于100得0分。",
    )



def _points_item(row: dict[str, Any] | None) -> dict[str, Any]:
    source = "携程 eBooking / 促销推广 / 积分联盟"
    if not row:
        return _item(14, None, "missing", source, [], "等待积分联盟状态快照。")
    active = _state(row)
    orders = _number(row.get("orders_30d"))
    amount = row.get("metric_value") if _text(row.get("metric_unit")).lower() in {"amount", "元", "cny"} else None
    fields = [
        _decision("报名状态", active, positive="已报名", negative="未报名"),
        _field("近30天订单", row.get("orders_30d")),
        _field("成交金额", amount),
        _field("覆盖平台", row.get("platform_scope")),
    ]
    if active is None:
        return _item(14, None, "pending_rule", source, fields, "报名状态无法由现有字段确认。")
    score = 0.0 if not active else 3.0 if (orders or 0) > 0 else 1.8
    return _item(14, score, "success", source, fields, "已报名且近30天有成交订单得3分；无成交订单得1.8分。")


def _preferred_item(row: dict[str, Any] | None) -> dict[str, Any]:
    source = "携程 eBooking / 促销推广 / 优享会"
    if not row:
        return _item(15, None, "missing", source, [], "等待优享会状态快照。")
    active = _state(row)
    detail = _words(row)
    restricted = any(word in detail for word in ("restricted", "limited", "psi", "review", "受限", "限制"))
    fields = [
        _decision("参加状态", active, positive="已参加", negative="未参加"),
        _field("标签状态", "受限" if restricted else "正常展示" if active else "未参加"),
    ]
    if active is None:
        return _item(15, None, "pending_rule", source, fields, "参加状态无法由现有字段确认。")
    score = 0.0 if not active else 1.8 if restricted else 3.0
    return _item(15, score, "success", source, fields, "已参加且标签正常得3分；标签受限得1.8分；未参加得0分。")


def _business_item(row: dict[str, Any] | None) -> dict[str, Any]:
    source = "携程 eBooking / 促销推广 / 商旅专享价"
    if not row:
        return _item(16, None, "missing", source, [], "等待商旅专享价状态快照。")
    active = _state(row)
    rooms = _number(row.get("room_type_count"))
    fields = [_decision("开通状态", active, positive="已开通", negative="未开通")]
    if active is False:
        fields.append(_field("参与房型", 0))
    elif active is True:
        fields.extend(
            [
                _field("参与房型", row.get("room_type_count")),
                _field("近30天订单", row.get("orders_30d")),
                _field("成交金额", row.get("metric_value")),
            ]
        )
    if active is None:
        return _item(16, None, "pending_rule", source, fields, "开通状态无法由现有字段确认。")
    score = 0.0 if not active else 2.0 if (rooms or 0) > 0 else 1.0
    return _item(16, score, "success", source, fields, "已开通且有参与房型得2分；已开通但无有效房型得1分。")


def _hourly_item(row: dict[str, Any] | None, order_count: Any = None) -> dict[str, Any]:
    source = "携程 eBooking / 促销推广 / 钟点房促销 + 订单明细"
    if not row:
        return _item(18, None, "missing", source, [], "等待钟点房状态快照。")
    active = _state(row)
    configured = active and "enabled" in _words(row)
    orders = _number(order_count)
    fields = [
        _decision("钟点房配置", configured, positive="已配置", negative="未配置"),
        _field("核心房型", row.get("room_type_count")),
        _decision("促销状态", active, positive="已开通", negative="未开通"),
        _field("近30天订单", orders),
    ]
    if active is None:
        return _item(18, None, "pending_rule", source, fields, "钟点房配置状态无法由现有字段确认。")
    if orders is None:
        return _item(18, None, "pending_rule", source, fields, "近30天钟点房订单明细暂未取得。")
    score = (1.0 if configured else 0.0) + (1.0 if orders > 0 else 0.0)
    return _item(18, score, "success", source, fields, "核心房型已配置钟点房得1分；订单明细中近30天有有效钟点房订单再得1分。")


def _travel_photo_item(row: dict[str, Any] | None) -> dict[str, Any]:
    source = "携程 eBooking / 信息维护 / 酒店亮点 / 旅拍"
    if not row:
        return _item(19, None, "missing", source, [], "等待旅拍状态快照。")
    active = _state(row)
    detail = _words(row)
    claimed = "claim" in detail or "认领" in detail
    count = 0 if active is False else row.get("metric_value")
    fields = [
        _decision("旅拍上传", active, positive="已上传", negative="未上传"),
        _field("认领状态", "已认领" if claimed else "未认领" if active else "未上传"),
        _field("旅拍数量", count),
    ]
    if active is None:
        return _item(19, None, "pending_rule", source, fields, "旅拍上传状态无法由现有字段确认。")
    score = 0.0 if not active else 2.0 if claimed else 1.0
    return _item(19, score, "success", source, fields, "有上传且已认领得2分；有上传未认领得1分。")


def _video_item(row: dict[str, Any] | None) -> dict[str, Any]:
    source = "携程 eBooking / 信息维护 / 视频管理"
    if not row:
        return _item(20, None, "missing", source, [], "等待首页视频状态快照。")
    uploaded = _state(row) is True and "uploaded" in _words(row)
    fields = [
        _field("酒店预览视频", "已上传" if uploaded else "未上传"),
        _field("首页视频", "已上传" if uploaded else "未上传"),
        _field("口径状态", "已按酒店预览视频判断"),
    ]
    return _item(20, 1.0 if uploaded else 0.0, "success", source, fields, "已上传首页或酒店预览视频得1分。")


def _listing_item(row: dict[str, Any] | None) -> dict[str, Any]:
    source = "携程 eBooking / 挂牌管理 / 委托分销"
    if not row:
        return _item(21, None, "missing", source, [], "等待挂牌或委托分销状态快照。")
    active = _state(row)
    detail = _words(row)
    fields = [
        _decision("挂牌状态", active, positive="已挂牌", negative="未挂牌"),
        _field("挂牌等级", "待核验"),
        _field("委托分销", "已参加" if active else "未参加" if active is False else "待核验"),
        _field("权益等级", "待核验"),
    ]
    if active is None:
        return _item(21, None, "pending_rule", source, fields, "挂牌状态无法由现有字段确认。")
    if not active:
        return _item(21, 0.0, "success", source, fields, "未挂牌或未参加委托分销。")
    if any(word in detail for word in ("gold", "premium", "高级", "金牌")):
        score = 6.0
        level = "高级/金牌"
    elif any(word in detail for word in ("standard", "basic", "普通", "基础")):
        score = 3.0
        level = "普通/基础"
    else:
        return _item(21, None, "pending_rule", source, fields, "已挂牌，但未提供挂牌或委托分销等级。")
    fields[1] = _field("挂牌等级", level)
    fields[3] = _field("权益等级", level)
    return _item(21, score, "success", source, fields, "高级挂牌/金牌/高级委托分销得6分；普通或基础权益得3分。")


def build_configuration_items(sections: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rights = [dict(row) for row in sections.get("ctrip_joined_rights") or [] if isinstance(row, dict)]
    statuses = [dict(row) for row in sections.get("ctrip_promotion_status") or [] if isinstance(row, dict)]
    hourly_rows = [dict(row) for row in sections.get("ctrip_hourly_orders") or [] if isinstance(row, dict)]
    hourly_status = _activity(statuses, 18)
    hourly_order_count = (
        hourly_rows[0].get("orders_30d")
        if hourly_rows
        else hourly_status.get("orders_30d")
        if hourly_status is not None and "ctrip_hourly_orders" not in sections
        else None
    )
    items = {
        "8": _information_item(_activity(statuses, 8)),
        "13": _rights_item(rights),
        "14": _points_item(_activity(statuses, 14)),
        "15": _preferred_item(_activity(statuses, 15)),
        "16": _business_item(_activity(statuses, 16)),
        "17": _item(17, None, "pending_rule", "携程 eBooking / 闪住服务入口", [_field("入口状态", None)], "暂无数据库表；待按实际后台菜单补充入口字段后计分。"),
        "18": _hourly_item(hourly_status, hourly_order_count),
        "19": _travel_photo_item(_activity(statuses, 19)),
        "20": _video_item(_activity(statuses, 20)),
        "21": _listing_item(_activity(statuses, 21)),
    }
    return items


__all__ = ["build_configuration_items"]
