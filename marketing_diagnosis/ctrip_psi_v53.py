from __future__ import annotations

import html
import math
import re
from typing import Any

METRICS = (
    ("A", "经营产能", "历史间夜量", 20),
    ("B", "经营产能", "历史营业额", 20),
    ("C", "经营产能", "历史成交率", 10),
    ("D", "房源保障", "即时确认订单占比", 10),
    ("E", "房源保障", "消费者实惠分", 10),
    ("F", "房源保障", "房态良好度", 10),
    ("G", "客户服务", "点评竞争指数", 10),
    ("H", "客户服务", "信息完整度", 5),
    ("I", "客户服务", "可取消率", 5),
)

STYLE = """
<style id='CTRIP_PSI_V53'>
.psi-v53{border:1px solid #dfe6f2;border-radius:12px;background:#fff;overflow:hidden}.psi-title-v53{padding:16px 18px 8px;font-size:18px;font-weight:900;color:#102a56}.psi-title-v53 span{margin-left:8px;font-size:14px;font-weight:500;color:#53698c}.psi-summary-v53{display:flex;align-items:center;gap:24px;margin:0 18px 14px;padding:13px 14px;border-radius:8px;background:#f0f4ff;color:#17396d}.psi-summary-v53 strong{font-size:15px;color:#0d2c5a}.psi-summary-v53 b{margin-left:8px;font-size:20px;font-weight:500;color:#24538d}.psi-summary-v53 em{margin-left:8px;font-style:normal;color:#00a679}.psi-summary-v53 i{width:1px;height:19px;background:#cbd5e6}.psi-grid-v53{display:grid;grid-template-columns:minmax(300px,.82fr) minmax(580px,1.45fr);gap:18px;padding:0 18px 18px}.psi-radar-box-v53{display:flex;align-items:center;justify-content:center;min-height:410px;border:1px solid #e4e9f2;border-radius:10px}.psi-radar-v53{width:min(100%,390px);height:auto}.psi-radar-grid-v53{fill:none;stroke:#d3d8df}.psi-radar-axis-v53{stroke:#c7cdd6}.psi-radar-shape-v53{fill:rgba(223,64,58,.08);stroke:#df403a;stroke-width:2.3}.psi-radar-dot-v53{fill:#fff;stroke:#df403a;stroke-width:2}.psi-radar-label-v53{font-size:14px;fill:#253245;font-family:inherit}.psi-table-box-v53{overflow:auto;border:1px solid #dfe5ee;border-radius:10px}.psi-table-v53{width:100%;border-collapse:collapse;min-width:720px}.psi-table-v53 th,.psi-table-v53 td{padding:12px 11px;border-bottom:1px solid #e5e9f0;text-align:left;vertical-align:middle}.psi-table-v53 th{color:#102a56;font-size:13px;font-weight:900;white-space:nowrap}.psi-table-v53 td{font-size:13px;color:#18345f}.psi-type-v53{width:76px;font-size:15px!important;font-weight:900}.psi-index-v53{font-weight:800}.psi-score-v53 strong{font-size:15px;font-weight:500}.psi-delta-v53{display:block;margin-top:4px;font-size:11px;color:#8090aa}.psi-delta-v53.up{color:#00a679}.psi-delta-v53.down{color:#ef5a57}.psi-source-v53{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 18px 18px}.psi-source-v53 div{padding:12px 14px;border:1px solid #dfe7e4;border-radius:9px;background:#f8fbfa}.psi-source-v53 b{display:block}.psi-source-v53 span{display:block;margin-top:5px;color:#66756e;font-size:12px}.psi-pending-v53{color:#8491a6}@media(max-width:1050px){.psi-grid-v53{grid-template-columns:1fr}.psi-radar-box-v53{min-height:340px}}@media(max-width:680px){.psi-summary-v53{gap:10px;flex-wrap:wrap}.psi-summary-v53 i{display:none}.psi-source-v53{grid-template-columns:1fr}.psi-grid-v53{padding:0 12px 12px}}
</style>
"""

CARD_RE = re.compile(r"<article\b(?=[^>]*\bid=['\"](?P<anchor>(?:rule|module)-6)['\"])[^>]*>.*?</article>", re.S | re.I)
NAV_RE = re.compile(r"<a\b(?=[^>]*href=['\"]#(?:rule|module)-6['\"])[^>]*>.*?</a>", re.S | re.I)
SUMMARY_RE = re.compile(r"<tr\b[^>]*>\s*<td>\s*06\s*</td>.*?</tr>", re.S | re.I)


def e(v: Any) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def num(v: Any) -> float | None:
    try:
        x = float(v)
        return None if math.isnan(x) or math.isinf(x) else x
    except (TypeError, ValueError):
        return None


def payload(result: dict[str, Any]) -> dict[str, Any]:
    sections = result.get("sections") if isinstance(result.get("sections"), dict) else {}
    value = result.get("ctrip_psi") or result.get("psi_service_quality") or sections.get("ctrip_psi") or sections.get("psi_service_quality") or {}
    return dict(value) if isinstance(value, dict) else {}


def metric(data: dict[str, Any], code: str) -> dict[str, Any]:
    values = data.get("metrics")
    if isinstance(values, dict):
        value = values.get(code) or values.get(code.lower())
        return dict(value) if isinstance(value, dict) else ({"score": value} if value not in (None, "") else {})
    if isinstance(values, list):
        for value in values:
            if isinstance(value, dict) and str(value.get("code") or "").upper() == code:
                return dict(value)
    return {}


def score(v: Any) -> str:
    x = num(v)
    return "待接入" if x is None else f"{x:.2f}"


def delta(v: Any) -> tuple[str, str]:
    x = num(v)
    if x is None:
        return "较昨日 —", ""
    return f"{'↑' if x > 0 else '↓' if x < 0 else '—'} 较昨日 {'+' if x > 0 else ''}{x:.2f}", "up" if x > 0 else "down" if x < 0 else ""


def radar(data: dict[str, Any]) -> str:
    cx = cy = 190.0
    radius = 126.0
    n = len(METRICS)
    def pt(i: int, s: float) -> tuple[float, float]:
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + radius * s * math.cos(a), cy + radius * s * math.sin(a)
    grids = []
    for level in range(1, 6):
        grids.append("<polygon class='psi-radar-grid-v53' points='" + " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, level / 5) for i in range(n))) + "'/>")
    axes, labels, values = [], [], []
    for i, (code, _, _, _) in enumerate(METRICS):
        x, y = pt(i, 1)
        axes.append(f"<line class='psi-radar-axis-v53' x1='{cx}' y1='{cy}' x2='{x:.1f}' y2='{y:.1f}'/>")
        lx, ly = pt(i, 1.18)
        anchor = "end" if lx < cx - 16 else "start" if lx > cx + 16 else "middle"
        labels.append(f"<text class='psi-radar-label-v53' x='{lx:.1f}' y='{ly:.1f}' text-anchor='{anchor}' dominant-baseline='middle'>{code}</text>")
        values.append(num(metric(data, code).get("score")))
    shape = ""
    if any(v is not None for v in values):
        points = [pt(i, max(0.0, min(5.0, v or 0.0)) / 5) for i, v in enumerate(values)]
        shape = "<polygon class='psi-radar-shape-v53' points='" + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + "'/>" + "".join(f"<circle class='psi-radar-dot-v53' cx='{x:.1f}' cy='{y:.1f}' r='3.3'/>" for x, y in points)
    return "<svg class='psi-radar-v53' viewBox='0 0 380 380' role='img' aria-label='PSI基础分雷达图'>" + "".join(grids + axes) + shape + "".join(labels) + "</svg>"


def rows(data: dict[str, Any]) -> str:
    counts = {group: sum(1 for _, g, _, _ in METRICS if g == group) for _, group, _, _ in METRICS}
    seen, output = set(), []
    for code, group, label, weight in METRICS:
        value = metric(data, code)
        dtext, dclass = delta(value.get("yesterday_change"))
        group_cell = ""
        if group not in seen:
            seen.add(group)
            group_cell = f"<td class='psi-type-v53' rowspan='{counts[group]}'>{e(group)}</td>"
        detail = f"<a href='{e(value.get('detail_url'))}'>查看</a>" if value.get("detail_url") else "<span class='psi-pending-v53'>待接入</span>"
        output.append(f"<tr>{group_cell}<td class='psi-index-v53'>{code}.{e(value.get('label') or label)}</td><td>{weight}%</td><td class='psi-score-v53'><strong>{e(score(value.get('score')))}</strong><span class='psi-delta-v53 {dclass}'>{e(dtext)}</span></td><td>{detail}</td></tr>")
    return "".join(output)


def card(result: dict[str, Any], anchor: str) -> str:
    data = payload(result)
    overall = num(data.get("yesterday_change"))
    overall_text = "较昨日 —" if overall is None else f"较昨日 {'+' if overall > 0 else ''}{overall:.2f}"
    weak = "—" if data.get("weak_item_count") in (None, "") else data.get("weak_item_count")
    status, css = ("已接入", "ok") if data else ("数据待接入", "pending")
    return f"""<article class='diagnosis-card' data-status='{'success' if data else 'missing'}' data-title='PSI 服务质量分' id='{e(anchor)}'><div class='card-top'><div class='rule-no'>06</div><div class='card-title'><h3>PSI 服务质量分</h3><p>展示携程基础分、九项分指标、项目权重、昨日变化及计算详情。</p></div><div class='card-tags'><div class='title-meta-item title-period'><small>统计周期</small><strong>当前值</strong></div><div class='title-meta-item title-score pending'><small>当前得分</small><div class='title-score-value'><strong>待计算</strong><span>满分 8分</span></div></div><span class='status-badge {css}'>{status}</span></div></div><div class='result-area'><div class='psi-v53'><div class='psi-title-v53'>基础分<span>把握经营大方向</span></div><div class='psi-summary-v53'><div><strong>我的基础分</strong><b>{e(score(data.get('base_score')))}</b><em>{e(overall_text)}</em></div><i></i><div><strong>得分较差</strong><b>{e(weak)} 项</b></div></div><div class='psi-grid-v53'><div class='psi-radar-box-v53'>{radar(data)}</div><div class='psi-table-box-v53'><table class='psi-table-v53'><thead><tr><th>指标类型</th><th>指标</th><th>项目权重</th><th>得分</th><th>计算详情</th></tr></thead><tbody>{rows(data)}</tbody></table></div></div><div class='psi-source-v53'><div><b>页面数据来源</b><span>携程 eBooking → 服务质量分 → 基础分</span></div><div><b>数据库映射状态</b><span>数据表和字段待后续接入；页面已预留 ctrip_psi / psi_service_quality 数据节点。</span></div></div></div><div class='notice'>未接入数据统一显示“待接入”，不会使用示例值或美团数据替代。</div></div><details class='output-fields-panel metric-details'><summary class='output-fields-head metric-details-summary'><div><h4>查看全部诊断指标</h4><p>包含携程页面来源、预留字段及后续计算口径</p></div><span class='field-count simple-count'>9项核心指标</span></summary><div class='metric-details-content'><div class='detail-group data-group'><div class='detail-group-title'><div>数据来源与字段</div><span>待数据库接入后补全</span></div><div class='field-standard-note'><b>携程后台来源：</b>eBooking / 服务质量分 / 基础分<br><b>建议数据节点：</b><code>ctrip_psi</code> 或 <code>sections.psi_service_quality</code><br><b>核心字段：</b>base_score、yesterday_change、weak_item_count、metrics[A-I].score、metrics[A-I].yesterday_change</div></div></div></details></article>"""


def transform(html_text: str, result: dict[str, Any]) -> str:
    html_text = html_text.replace("</head>", STYLE + "</head>", 1)
    html_text = re.sub(r"<title>.*?</title>", "<title>携程｜酒店 OTA 全面诊断报告</title>", html_text, count=1, flags=re.S | re.I)
    html_text = html_text.replace("美团EB数据", "携程 eBooking 数据").replace("HOS 历史得分", "PSI 服务质量分")
    html_text = html_text.replace("酒店经营与线上运营综合诊断", "携程渠道经营与服务质量诊断", 1)
    html_text = html_text.replace("严格使用数据库真实数据生成，覆盖经营趋势、流量、客群、推广、口碑及平台配置等23项内容。", "沿用正式报告页面结构；携程模块按接入进度逐项替换，未接入数据明确标记。", 1)
    def nav(m: re.Match[str]) -> str:
        found = re.search(r"href=['\"]#([^'\"]+)", m.group(0), re.I)
        return f"<a href='#{e(found.group(1) if found else 'rule-6')}'><span>06</span>PSI 服务质量分</a>"
    html_text = NAV_RE.sub(nav, html_text, count=1)
    summary = "<tr data-status='missing' data-title='PSI 服务质量分'><td>06</td><td><a href='#rule-6'>PSI 服务质量分</a></td><td>8分</td><td>待计算</td><td><span class='status-badge pending'>数据待接入</span></td><td>携程 eBooking / 服务质量分 / 基础分<br>展示基础分及 A-I 九项指标</td></tr>"
    html_text = SUMMARY_RE.sub(summary, html_text, count=1)
    html_text, count = CARD_RE.subn(lambda m: card(result, m.group("anchor")), html_text, count=1)
    return html_text if count else html_text.replace("</main>", card(result, "rule-6") + "</main>", 1)


__all__ = ["transform"]
