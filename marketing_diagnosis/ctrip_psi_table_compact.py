from __future__ import annotations

import re
from typing import Any

from marketing_diagnosis import ctrip_psi_v53 as psi
from marketing_diagnosis import ctrip_report as stable_report
from marketing_diagnosis import ctrip_report_v54 as report


_ORIGINAL_CARD = report.psi_card
_OLD_HEADER = (
    "<th>指标类型</th><th>诊断指标</th><th>实际值</th>"
    "<th>权重</th><th>PSI得分</th>"
)
_NEW_HEADER = (
    "<th class='psi-col-type-v53'>指标类型</th>"
    "<th class='psi-col-index-v53'>诊断指标</th>"
    "<th class='psi-col-unit-v53'>单位</th>"
    "<th class='psi-col-value-v53'>实际值</th>"
    "<th class='psi-col-weight-v53'>权重</th>"
    "<th class='psi-col-score-v53'>PSI得分</th>"
)
_COMPETITION_CARD_RE = re.compile(
    r"<div class='psi-summary-card-v53'><small>竞争圈排名</small>.*?</div>",
    re.S,
)


def rows(data: dict[str, Any]) -> str:
    metric_values = psi._metric_map(data)
    groups = {metric[1] for metric in psi.METRICS}
    counts = {
        group: sum(
            1
            for _, metric_group, _, _, _ in psi.METRICS
            if metric_group == group
        )
        for group in groups
    }
    seen: set[str] = set()
    output: list[str] = []

    for code, group, label, default_unit, _ in psi.METRICS:
        value = metric_values.get(code) or {}
        unit = str(value.get("unit") or default_unit)
        group_cell = ""
        if group not in seen:
            seen.add(group)
            group_cell = (
                f"<td class='psi-type-v53' rowspan='{counts[group]}'>"
                f"{psi.e(group)}</td>"
            )

        weight = psi.num(value.get("weight_pct"))
        weight_text = "待接入" if weight is None else f"{weight:g}%"
        score_text = psi._plain(value.get("psi_score"))
        actual_value = psi._metric_value(value.get("metric_value"), unit)

        output.append(
            f"<tr>{group_cell}"
            f"<td class='psi-index-v53'>{psi.e(value.get('metric_name') or label)}</td>"
            f"<td class='psi-unit-v53'>{psi.e(unit)}</td>"
            f"<td class='psi-value-v53'>{psi.e(actual_value)}</td>"
            f"<td class='psi-weight-v53'>{psi.e(weight_text)}</td>"
            f"<td class='psi-score-v53'><strong>{psi.e(score_text)}</strong></td></tr>"
        )

    return "".join(output)


def card(result: dict[str, Any], anchor: str) -> str:
    html_text = _ORIGINAL_CARD(result, anchor).replace(_OLD_HEADER, _NEW_HEADER, 1)
    return _COMPETITION_CARD_RE.sub("", html_text, count=1)


psi.rows = rows
psi.card = card
report.psi_card = card
stable_report.psi_card = card
report.PSI_STYLE += """
<style id='CTRIP_PSI_COMPACT_TABLE'>
.psi-summary-grid-v53{grid-template-columns:repeat(3,minmax(0,1fr))}
.psi-table-v53{min-width:680px;table-layout:fixed}
.psi-table-v53 th,.psi-table-v53 td{padding:12px 14px}
.psi-table-v53 .psi-col-type-v53{width:16%}
.psi-table-v53 .psi-col-index-v53{width:27%}
.psi-table-v53 .psi-col-unit-v53{width:11%}
.psi-table-v53 .psi-col-value-v53{width:18%}
.psi-table-v53 .psi-col-weight-v53{width:13%}
.psi-table-v53 .psi-col-score-v53{width:15%}
.psi-table-v53 .psi-col-unit-v53,
.psi-table-v53 .psi-col-value-v53,
.psi-table-v53 .psi-col-weight-v53,
.psi-table-v53 .psi-col-score-v53,
.psi-table-v53 .psi-unit-v53,
.psi-table-v53 .psi-value-v53,
.psi-table-v53 .psi-weight-v53,
.psi-table-v53 .psi-score-v53{text-align:center}
.psi-table-v53 .psi-unit-v53{color:#718078}
</style>
"""


__all__ = ["card", "rows"]
