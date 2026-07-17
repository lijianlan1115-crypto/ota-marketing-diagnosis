from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v30
from marketing_diagnosis.room_name_manual_v43 import SELLING_POINT_TERMS


MANUAL_ROOM_STYLE = """
<style>
.manual-room-panel-v31{display:grid;grid-template-columns:minmax(300px,.9fr) minmax(520px,1.7fr);gap:16px;align-items:start}
.manual-room-input-v31,.manual-room-result-v31{padding:16px;border:1px solid #dfe8e5;border-radius:12px;background:#f8fbfa}
.manual-room-input-v31 h4,.manual-room-result-v31 h4{margin:0 0 8px;color:#26343d;font-size:16px}
.manual-room-input-v31 p{margin:0 0 10px;color:var(--muted);font-size:12px;line-height:1.6}
.manual-room-textarea-v31{box-sizing:border-box;width:100%;min-height:150px;padding:12px;border:1px solid #cfdad6;border-radius:9px;background:#fff;color:#26343d;font:inherit;line-height:1.55;resize:vertical;white-space:pre;overflow-x:auto;overflow-y:auto;word-break:normal}
.manual-room-actions-v31{display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap}
.manual-room-button-v31{padding:9px 16px;border:0;border-radius:8px;background:#16845b;color:#fff;font-weight:800;cursor:pointer}
.manual-room-hint-v31{color:var(--muted);font-size:11px;line-height:1.5}
.manual-room-table-v31{width:100%;border-collapse:collapse;background:#fff}
.manual-room-table-v31 th,.manual-room-table-v31 td{padding:9px 11px;border-bottom:1px solid #e3ebe8;text-align:left;line-height:1.35;height:auto}
.manual-room-table-v31 th{background:#f3f6f5;color:#596773;font-size:12px}
.manual-room-table-v31 td{font-size:13px}
.manual-room-table-v31 .room-name{font-weight:800;color:#26343d}
.manual-room-score-note-v31{margin:10px 0 0;padding:10px 12px;border-radius:8px;background:#eef7f3;color:#315c4d;font-size:12px;line-height:1.55}
.manual-room-score-note-v31.is-zero{background:#fff2ef;color:#8c4939}
.room-type-card-v30 .room-summary-v30>div:first-child small{font-size:0}
.room-type-card-v30 .room-summary-v30>div:first-child small::after{content:'全部在售房型数';font-size:12px}
@media(max-width:900px){.manual-room-panel-v31{grid-template-columns:1fr}}
</style>
"""

_ITEM_ELEVEN_PATTERN = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-11'>.*?</article>",
    re.DOTALL,
)
_ITEM_TWO_FIRST_VALUE_PATTERN = re.compile(
    r"(<article class='diagnosis-card room-type-card-v30'.*?<div class='room-summary-v30'><div><small>房型数</small><strong>).*?(</strong>)",
    re.DOTALL,
)


def _item(result: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in (result.get("visual_diagnosis") or {}).get("items") or []
            if int(item.get("standard_item_id") or 0) == number
        ),
        None,
    )


def _records(item: dict[str, Any]) -> list[dict[str, Any]]:
    records = list(item.get("records") or [])
    if records:
        return records
    fallback: list[dict[str, Any]] = []
    for field in item.get("fields") or []:
        label = str(field.get("label") or "").strip()
        if not label or label == "人工输入状态":
            continue
        try:
            count = int(float(field.get("value")))
        except (TypeError, ValueError):
            count = len("".join(label.split()))
        note = str(field.get("note") or "")
        selling_point = None
        for term in SELLING_POINT_TERMS:
            if term in label:
                selling_point = term
                break
        fallback.append(
            {
                "room_type_name": label,
                "character_count": count,
                "selling_point": selling_point,
                "passed": count > 5 and selling_point is not None and "不通过" not in note,
            }
        )
    return fallback


def _rows_html(records: list[dict[str, Any]]) -> str:
    if not records:
        return "<tr><td colspan='4'>尚未输入房型名称，本项已按0分计入总分。</td></tr>"
    rows: list[str] = []
    for record in records:
        passed = bool(record.get("passed"))
        badge = (
            "<span class='status-badge ok'>通过</span>"
            if passed
            else "<span class='status-badge disabled'>不通过</span>"
        )
        rows.append(
            "<tr>"
            f"<td><span class='room-name'>{reporting_v8._e(record.get('room_type_name'))}</span></td>"
            f"<td>{reporting_v8._e(record.get('character_count'))}</td>"
            f"<td>{reporting_v8._e(record.get('selling_point') or '未命中')}</td>"
            f"<td>{badge}</td>"
            "</tr>"
        )
    return "".join(rows)


def _manual_room_card(item: dict[str, Any]) -> str:
    records = _records(item)
    names = "\n".join(str(record.get("room_type_name") or "") for record in records)
    score = float(item.get("item_score") or 0)
    base_score = float(item.get("base_score") or 4)
    passed = score >= base_score and bool(records)
    status_text = "已形成结果" if passed else "真实为0"
    status_class = "ok" if passed else "disabled"
    note_class = "" if passed else " is-zero"

    return (
        f"<article class='diagnosis-card manual-room-card-v31' data-status='{'success' if passed else 'zero'}' "
        f"data-title='{reporting_v8._e(item.get('item_name'))}' id='rule-11'>"
        "<div class='card-top'><div class='rule-no'>11</div>"
        "<div class='card-title'><h3>房型名称卖点优化</h3>"
        "<p>房型名称由用户手动输入；支持网页即时试算，也支持飞书文本或语音转写后生成正式评分。</p></div>"
        "<div class='card-tags'>"
        "<div class='title-meta-item title-period'><small>统计口径</small><strong>人工输入</strong></div>"
        f"<div class='title-meta-item title-score {'ok' if passed else 'zero'}'><small>当前得分</small>"
        f"<div class='title-score-value'><strong class='manual-room-score-v31'>{score:g}分</strong>"
        f"<span>满分 {base_score:g}分</span></div></div>"
        f"<span class='status-badge {status_class} manual-room-status-v31'>{status_text}</span>"
        "</div></div>"
        "<div class='result-area'><div class='manual-room-panel-v31'>"
        "<div class='manual-room-input-v31'><h4>手动输入房型名称</h4>"
        "<p>建议使用逗号、顿号或分号分隔房型。粘贴长名称产生的断行会自动拼回；完整以房、间、床或套房结尾的行仍可作为独立房型。</p>"
        f"<textarea class='manual-room-textarea-v31' wrap='off' spellcheck='false' placeholder='例如：五人战队套房、电竞双床房'>{reporting_v8._e(names)}</textarea>"
        "<div class='manual-room-actions-v31'>"
        "<button type='button' class='manual-room-button-v31'>即时计算</button>"
        "<span class='manual-room-hint-v31'>点击后会先自动合并误换行，再计算字符数和卖点。网页试算不写回正式总分。</span>"
        "</div></div>"
        "<div class='manual-room-result-v31'><h4>评分明细</h4>"
        "<div class='table-scroll'><table class='manual-room-table-v31'><thead><tr>"
        "<th>房型名称</th><th>字符数</th><th>卖点表达</th><th>判定</th>"
        f"</tr></thead><tbody class='manual-room-body-v31'>{_rows_html(records)}</tbody></table></div>"
        f"<div class='manual-room-score-note-v31{note_class}'>{reporting_v8._e(item.get('note') or '')}</div>"
        "</div></div>"
        + reporting_v8._source_box(item)
        + "</div></article>"
    )


def _script() -> str:
    terms_json = json.dumps(list(SELLING_POINT_TERMS), ensure_ascii=False)
    return f"""
<script>
(function(){{
  const terms={terms_json};
  const strongSplit=/[,，、;；|]+/;
  const listMarker=/^\s*(?:[-*•·●▪◦]+|\d{{1,3}}\s*[.、)）:：])\s*/;
  const completeRoom=/(?:房|房间|客房|套房|大床|双床|单人间|双人间|三人间|四人间|五人间|多人间|榻榻米)(?:\s*[（(【\[].*?[）)】\]])?\s*$/;
  const cleanLine=(raw)=>{{
    const text=String(raw||'')
      .replace(/[\u200b\ufeff]/g,'')
      .replace(listMarker,'')
      .trim()
      .replace(/^[\s。.!！?？：:,，、;；|"'“”‘’]+|[\s。.!！?？：:,，、;；|"'“”‘’]+$/g,'');
    return /[0-9A-Za-z\u3400-\u9fff]/.test(text)?text:'';
  }};
  const splitNames=(text)=>{{
    const collected=[];
    String(text||'').replace(/\r\n?/g,'\n').split(strongSplit).forEach(segment=>{{
      let buffer='';
      segment.split('\n').forEach(raw=>{{
        const marked=listMarker.test(raw);
        const line=cleanLine(raw);
        if(!line) return;
        if(!buffer){{buffer=line;return;}}
        if(marked||completeRoom.test(buffer)){{collected.push(buffer);buffer=line;}}
        else{{buffer+=line;}}
      }});
      if(buffer) collected.push(buffer);
    }});
    const seen=new Set();
    return collected.map(cleanLine).filter(name=>{{
      if(!name||seen.has(name)) return false;
      seen.add(name);
      return true;
    }});
  }};
  document.querySelectorAll('.manual-room-card-v31').forEach(card=>{{
    const button=card.querySelector('.manual-room-button-v31');
    const textarea=card.querySelector('.manual-room-textarea-v31');
    const body=card.querySelector('.manual-room-body-v31');
    const scoreNode=card.querySelector('.manual-room-score-v31');
    const statusNode=card.querySelector('.manual-room-status-v31');
    const noteNode=card.querySelector('.manual-room-score-note-v31');
    if(!button||!textarea||!body) return;
    button.addEventListener('click',()=>{{
      const names=splitNames(textarea.value);
      textarea.value=names.join('\n');
      const records=names.map(name=>{{
        const count=name.replace(/\s+/g,'').length;
        const sellingPoint=terms.find(term=>name.includes(term))||'';
        return {{name,count,sellingPoint,passed:count>5&&!!sellingPoint}};
      }});
      const passed=records.length>0&&records.every(x=>x.passed);
      body.innerHTML=records.length?records.map(x=>`<tr><td><span class="room-name">${{x.name.replace(/[&<>"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]))}}</span></td><td>${{x.count}}</td><td>${{x.sellingPoint||'未命中'}}</td><td><span class="status-badge ${{x.passed?'ok':'disabled'}}">${{x.passed?'通过':'不通过'}}</span></td></tr>`):'<tr><td colspan="4">尚未输入房型名称，本项按0分。</td></tr>';
      if(scoreNode) scoreNode.textContent=passed?'4分':'0分';
      if(statusNode){{statusNode.textContent=passed?'已形成结果':'真实为0';statusNode.className='status-badge manual-room-status-v31 '+(passed?'ok':'disabled');}}
      if(noteNode){{
        noteNode.classList.toggle('is-zero',!passed);
        noteNode.textContent=passed?'全部房型名称严格大于5个字且命中卖点表达，网页即时评分为4分。':'存在未通过房型或未输入，网页即时评分为0分。正式总分需重新生成报告。';
      }}
    }});
  }});
}})();
</script>
"""


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v30.build_html(result)
    item11 = _item(result, 11)
    if item11:
        html_text = _ITEM_ELEVEN_PATTERN.sub(
            lambda _: _manual_room_card(item11), html_text, count=1
        )

    item2 = _item(result, 2)
    if item2:
        total = len(item2.get("records") or [])
        html_text = _ITEM_TWO_FIRST_VALUE_PATTERN.sub(
            lambda match: match.group(1) + f"{total:,}" + match.group(2),
            html_text,
            count=1,
        )

    html_text = html_text.replace("</head>", MANUAL_ROOM_STYLE + "</head>", 1)
    return html_text.replace("</body>", _script() + "</body>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v30.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v30.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = [
    "MANUAL_ROOM_STYLE",
    "_manual_room_card",
    "build_html",
    "build_markdown",
    "write_reports",
]
