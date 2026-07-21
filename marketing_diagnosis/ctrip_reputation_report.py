from __future__ import annotations

import math
from typing import Any

from marketing_diagnosis import ctrip_report_v54 as upstream
from marketing_diagnosis.ctrip_reputation_style import STYLE

TARGET = 4.7


def _number(value: Any) -> float | None:
    return upstream.number(value)


def _value(entry: dict[str, Any], key: str, suffix: str = "") -> str:
    if entry.get("data_status") == "missing":
        return "待接入"
    value = entry.get(key)
    if value in (None, ""):
        return "—"
    parsed = _number(value)
    if parsed is None:
        return f"{value}{suffix}"
    return f"{parsed:g}{suffix}"


def _percent(entry: dict[str, Any]) -> str:
    value = _number(entry.get("reply_rate"))
    if value is None:
        return "待接入" if entry.get("data_status") == "missing" else "—"
    return f"{(value * 100 if abs(value) <= 1 else value):.1f}%"


def _tone(rating: float | None) -> tuple[str, str]:
    if rating is None:
        return "pending", "待接入"
    if rating >= TARGET:
        return "good", "达标"
    if rating >= 4.5:
        return "fair", "接近达标"
    return "low", "未达标"


def _radar_chart(entry: dict[str, Any]) -> str:
    dimensions = (
        ("环境", "environment_score", -90),
        ("服务", "service_score", 0),
        ("卫生", "hygiene_score", 90),
        ("设施", "facility_score", 180),
    )
    cx, cy, radius = 72.0, 72.0, 43.0

    def point(angle: float, score: float) -> tuple[float, float]:
        radian = math.radians(angle)
        distance = radius * min(5.0, max(0.0, score)) / 5.0
        return cx + math.cos(radian) * distance, cy + math.sin(radian) * distance

    values = {key: _number(entry.get(key)) for _, key, _ in dimensions}
    polygon = " ".join(
        f"{x:.1f},{y:.1f}"
        for label, key, angle in dimensions
        for x, y in [point(angle, values[key] or 0.0)]
    )

    def ring(scale: float) -> str:
        points = (
            (cx, cy - radius * scale),
            (cx + radius * scale, cy),
            (cx, cy + radius * scale),
            (cx - radius * scale, cy),
        )
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    value_grid = "".join(
        "<div class='rep-dim'>"
        f"<small>{upstream.e(label)}</small>"
        f"<strong>{upstream.e(_value(entry, key))}</strong>"
        "</div>"
        for label, key, _ in dimensions
    )

    return (
        "<div class='rep-dims' style='grid-template-columns:150px minmax(0,1fr);align-items:center'>"
        "<svg viewBox='0 0 144 144' width='144' height='144' role='img' aria-label='口碑维度雷达图'>"
        f"<polygon points='{ring(1)}' fill='none' stroke='#dce6e2' stroke-width='1'/>"
        f"<polygon points='{ring(.75)}' fill='none' stroke='#e7eeeb' stroke-width='1'/>"
        f"<polygon points='{ring(.5)}' fill='none' stroke='#edf3f0' stroke-width='1'/>"
        f"<polygon points='{ring(.25)}' fill='none' stroke='#f3f6f5' stroke-width='1'/>"
        f"<line x1='{cx}' y1='{cy}' x2='{cx}' y2='{cy-radius}' stroke='#e1e9e6'/>"
        f"<line x1='{cx}' y1='{cy}' x2='{cx+radius}' y2='{cy}' stroke='#e1e9e6'/>"
        f"<line x1='{cx}' y1='{cy}' x2='{cx}' y2='{cy+radius}' stroke='#e1e9e6'/>"
        f"<line x1='{cx}' y1='{cy}' x2='{cx-radius}' y2='{cy}' stroke='#e1e9e6'/>"
        f"<polygon points='{polygon}' fill='rgba(22,132,91,.18)' stroke='#16845b' stroke-width='2'/>"
        "<text x='72' y='12' text-anchor='middle' fill='#68747f' font-size='10'>环境</text>"
        "<text x='132' y='76' text-anchor='middle' fill='#68747f' font-size='10'>服务</text>"
        "<text x='72' y='141' text-anchor='middle' fill='#68747f' font-size='10'>卫生</text>"
        "<text x='12' y='76' text-anchor='middle' fill='#68747f' font-size='10'>设施</text>"
        "</svg>"
        f"<div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px'>{value_grid}</div>"
        "</div>"
    )


def build_content(payload: dict[str, Any]) -> str:
    platforms = [item for item in payload.get("platforms") or [] if isinstance(item, dict)]
    score = upstream.score_value(payload)
    ratings = [_number(item.get("rating")) for item in platforms]
    valid_ratings = [value for value in ratings if value is not None]
    available = sum(item.get("data_status") != "missing" for item in platforms)
    reached = sum(value >= TARGET for value in valid_ratings)
    average = sum(valid_ratings) / len(valid_ratings) if valid_ratings else None

    kpis = (
        "<div class='rep-kpis'>"
        f"<div class='rep-kpi'><small>模块得分</small><strong>{upstream.e('待计算' if score is None else f'{score:g}/10')}</strong><span>平台权重合计</span></div>"
        f"<div class='rep-kpi'><small>平台平均分</small><strong>{upstream.e('—' if average is None else f'{average:.2f}')}</strong><span>四个平台横向对比</span></div>"
        f"<div class='rep-kpi'><small>已接入平台</small><strong>{available}/4</strong><span>真实渠道数据</span></div>"
        f"<div class='rep-kpi'><small>达标平台</small><strong>{reached}/{len(valid_ratings) or 4}</strong><span>满分线 {TARGET:g}</span></div>"
        "</div>"
    )

    compare_rows: list[str] = []
    risk_entries: list[tuple[float, float, dict[str, Any]]] = []
    for entry in platforms:
        rating = _number(entry.get("rating"))
        tone, state = _tone(rating)
        width = 0 if rating is None else min(100.0, max(0.0, rating / 5 * 100))
        weight = _number(entry.get("full_score")) or 0
        if rating is not None and rating < TARGET:
            risk_entries.append((weight, TARGET - rating, entry))
        compare_rows.append(
            "<div class='rep-row'>"
            f"<span class='rep-name'>{upstream.e(entry.get('platform_name') or '平台')}</span>"
            f"<span class='rep-score'>{upstream.e('—' if rating is None else f'{rating:.2f}')}</span>"
            f"<span class='rep-track'><i class='rep-fill {tone}' style='display:block;width:{width:.1f}%'></i></span>"
            f"<span class='rep-state {tone}'>{upstream.e(state)}</span>"
            "</div>"
        )
    comparison = (
        "<div class='rep-compare'><div class='rep-compare-head'>"
        f"<b>平台评分对比</b><span>竖线为满分线 {TARGET:g}</span></div>"
        + "".join(compare_rows)
        + "</div>"
    )

    if risk_entries:
        _, gap, risk = max(risk_entries, key=lambda item: (item[0], item[1]))
        insight = (
            f"<b>重点结论：</b>{upstream.e(risk.get('platform_name') or '重点平台')}"
            f"当前低于满分线 {gap:.2f} 分，且权重较高，建议优先处理差评并改善最低分维度。"
        )
    else:
        insight = "<b>重点结论：</b>当前已接入平台均达到目标线，继续关注新增差评和回复时效。"

    cards: list[str] = []
    for entry in platforms:
        rating = _number(entry.get("rating"))
        tone, state = _tone(rating)
        gap = None if rating is None else rating - TARGET
        gap_text = "—" if gap is None else f"{gap:+.2f}"
        cards.append(
            "<section class='rep-card'>"
            "<div class='rep-head'><div>"
            f"<div class='rep-title'>{upstream.e(entry.get('platform_name') or '平台')}</div>"
            f"<span class='rep-weight'>权重 {_value(entry, 'full_score', '分')}</span></div>"
            f"<span class='rep-badge {tone}'>{upstream.e(state)}</span></div>"
            "<div class='rep-main'>"
            f"<div class='rep-rating'><small>平台点评分</small><strong>{upstream.e(_value(entry, 'rating'))}</strong></div>"
            f"<div><small>距达标</small><strong class='{'rep-pos' if gap is not None and gap >= 0 else 'rep-neg'}'>{upstream.e(gap_text)}</strong></div>"
            f"<div><small>贡献分</small><strong>{upstream.e(_value(entry, 'score'))} / {upstream.e(_value(entry, 'full_score'))}</strong></div>"
            "</div>"
            "<div class='rep-facts'>"
            f"<div class='rep-fact'><small>点评数</small><strong>{upstream.e(_value(entry, 'review_count', '条'))}</strong></div>"
            f"<div class='rep-fact'><small>回复率</small><strong>{upstream.e(_percent(entry))}</strong></div>"
            f"<div class='rep-fact'><small>差评数</small><strong>{upstream.e(_value(entry, 'negative_review_count', '条'))}</strong></div>"
            f"<div class='rep-fact'><small>昨日新增</small><strong>{upstream.e(_value(entry, 'yesterday_new_review_count', '条'))}</strong></div>"
            "</div>"
            f"{_radar_chart(entry)}</section>"
        )

    return (
        "<div class='rep-wrap'>"
        + kpis
        + comparison
        + f"<div class='rep-insight'>{insight}</div>"
        + "<div class='rep-cards'>"
        + "".join(cards)
        + "</div></div>"
    )


def install() -> None:
    if getattr(upstream, "_simple_reputation_installed", False):
        return
    original_build_head = upstream.build_head

    def build_head() -> str:
        head = original_build_head()
        return head.replace("</head>", STYLE + "</head>", 1)

    upstream._reputation_card_content = build_content
    upstream.build_head = build_head
    upstream._simple_reputation_installed = True


install()

__all__ = ["STYLE", "build_content", "install"]