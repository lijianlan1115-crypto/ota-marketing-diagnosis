from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v8, reporting_v30
from marketing_diagnosis.room_name_manual_v43 import SELLING_POINT_TERMS


MANUAL_ROOM_STYLE = """
<style>
.manual-room-panel-v31{display:grid;grid-template-columns:minmax(420px,1.05fr) minmax(560px,1.7fr);gap:16px;align-items:start}
.manual-room-input-v31,.manual-room-result-v31{padding:16px;border:1px solid #dfe8e5;border-radius:12px;background:#f8fbfa;position:relative}
.manual-room-input-v31 h4,.manual-room-result-v31 h4{margin:0 0 8px;color:#26343d;font-size:16px}
.manual-room-input-v31 p{margin:0 0 12px;color:var(--muted);font-size:12px;line-height:1.6}
.manual-room-count-row-v53{display:flex;gap:8px;align-items:center;margin:0 0 12px;padding:10px;border:1px solid #dfe8e5;border-radius:9px;background:#fff;position:relative;z-index:6}
.manual-room-count-row-v53 label{color:#596773;font-size:12px;font-weight:800;white-space:nowrap}
.manual-room-count-input-v53{box-sizing:border-box;width:90px;height:38px;padding:0 10px;border:1px solid #cfdad6;border-radius:7px;background:#fff;color:#26343d;font:inherit;outline:none}
.manual-room-count-input-v53:focus{border-color:#16845b;box-shadow:0 0 0 3px rgba(22,132,91,.10)}
.manual-room-set-count-v53{height:38px;padding:0 14px;border:1px solid #c8e2d6;border-radius:7px;background:#e8f4ef;color:#176747;font-weight:800;cursor:pointer;position:relative;z-index:7;pointer-events:auto;touch-action:manipulation}
.manual-room-fields-v52{display:flex;flex-direction:column;gap:9px}
.manual-room-field-v52{display:grid;grid-template-columns:62px minmax(0,1fr) 54px;gap:8px;align-items:center}
.manual-room-field-v52 label{color:#596773;font-size:12px;font-weight:800;white-space:nowrap}
.manual-room-name-input-v52{box-sizing:border-box;width:100%;height:42px;padding:0 11px;border:1px solid #cfdad6;border-radius:8px;background:#fff;color:#26343d;font:inherit;line-height:42px;white-space:nowrap;overflow-x:auto;outline:none}
.manual-room-name-input-v52:focus{border-color:#16845b;box-shadow:0 0 0 3px rgba(22,132,91,.10)}
.manual-room-remove-v52{height:34px;padding:0 8px;border:1px solid #e3c8c2;border-radius:7px;background:#fff5f2;color:#a04e3d;font-size:11px;font-weight:800;cursor:pointer;position:relative;z-index:4;pointer-events:auto}
.manual-room-actions-v31{display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap;position:relative;z-index:5}
.manual-room-button-v31,.manual-room-add-v52{min-height:42px;padding:9px 16px;border:0;border-radius:8px;font-weight:800;cursor:pointer;position:relative;z-index:6;pointer-events:auto;touch-action:manipulation}
.manual-room-button-v31{background:#16845b;color:#fff}
.manual-room-add-v52{background:#e8f4ef;color:#176747;border:1px solid #c8e2d6}
.manual-room-button-v31:hover{background:#116f4c}
.manual-room-add-v52:hover,.manual-room-set-count-v53:hover{background:#dcefe7}
.manual-room-hint-v31{display:block;margin-top:10px;color:var(--muted);font-size:11px;line-height:1.5}
.manual-room-table-v31{width:100%;border-collapse:collapse;background:#fff}
.manual-room-table-v31 th,.manual-room-table-v31 td{padding:9px 11px;border-bottom:1px solid #e3ebe8;text-align:left;line-height:1.35;height:auto}
.manual-room-table-v31 th{background:#f3f6f5;color:#596773;font-size:12px}
.manual-room-table-v31 td{font-size:13px}
.manual-room-table-v31 .room-name{font-weight:800;color:#26343d}
.manual-room-score-note-v31{margin:10px 0 0;padding:10px 12px;border-radius:8px;background:#eef7f3;color:#315c4d;font-size:12px;line-height:1.55}
.manual-room-score-note-v31.is-zero{background:#fff2ef;color:#8c4939}
.room-type-card-v30 .room-summary-v30>div:first-child small{font-size:0}
.room-type-card-v30 .room-summary-v30>div:first-child small::after{content:'全部在售房型数';font-size:12px}
@media(max-width:1050px){.manual-room-panel-v31{grid-template-columns:1fr}}
@media(max-width:560px){.manual-room-count-row-v53{align-items:flex-start;flex-wrap:wrap}.manual-room-field-v52{grid-template-columns:52px minmax(0,1fr)}.manual-room-remove-v52{grid-column:2;justify-self:end}}
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


def _input_rows_html(records: list[dict[str, Any]], minimum: int = 1) -> str:
    names = [str(record.get("room_type_name") or "").strip() for record in records]
    total = max(minimum, len(names), 1)
    rows: list[str] = []
    for index in range(total):
        value = names[index] if index < len(names) else ""
        rows.append(
            "<div class='manual-room-field-v52'>"
            f"<label>房型{index + 1}</label>"
            f"<input type='text' class='manual-room-name-input-v52' value='{reporting_v8._e(value)}' "
            f"placeholder='请输入第{index + 1}个房型名称' autocomplete='off' spellcheck='false'>"
            "<button type='button' class='manual-room-remove-v52' "
            "onclick='return window.S14ManualRoomRemove ? window.S14ManualRoomRemove(this) : false;'>删除</button>"
            "</div>"
        )
    return "".join(rows)


def _manual_room_card(item: dict[str, Any]) -> str:
    records = _records(item)
    score = float(item.get("item_score") or 0)
    base_score = float(item.get("base_score") or 4)
    passed = score >= base_score and bool(records)
    status_text = "已形成结果" if passed else "真实为0"
    status_class = "ok" if passed else "disabled"
    note_class = "" if passed else " is-zero"
    initial_count = max(1, len(records))

    return (
        f"<article class='diagnosis-card manual-room-card-v31' data-status='{'success' if passed else 'zero'}' "
        f"data-title='{reporting_v8._e(item.get('item_name'))}' id='rule-11'>"
        "<div class='card-top'><div class='rule-no'>11</div>"
        "<div class='card-title'><h3>房型名称卖点优化</h3>"
        "<p>每个输入框填写一个房型名称；输入框数量可自定义，全部填写后统一即时计算。</p></div>"
        "<div class='card-tags'>"
        "<div class='title-meta-item title-period'><small>统计口径</small><strong>人工输入</strong></div>"
        f"<div class='title-meta-item title-score {'ok' if passed else 'zero'}'><small>当前得分</small>"
        f"<div class='title-score-value'><strong class='manual-room-score-v31'>{score:g}分</strong>"
        f"<span>满分 {base_score:g}分</span></div></div>"
        f"<span class='status-badge {status_class} manual-room-status-v31'>{status_text}</span>"
        "</div></div>"
        "<div class='result-area'><div class='manual-room-panel-v31'>"
        "<div class='manual-room-input-v31'><h4>手动输入房型名称</h4>"
        "<p>先设置需要的输入框数量，每个框只填一个完整房型名称；也可以随时新增或删除。</p>"
        "<div class='manual-room-count-row-v53'>"
        "<label>输入框数量</label>"
        f"<input type='number' min='1' max='100' value='{initial_count}' class='manual-room-count-input-v53' inputmode='numeric'>"
        "<button type='button' class='manual-room-set-count-v53' "
        "onclick='return window.S14ManualRoomSetCount ? window.S14ManualRoomSetCount(this) : false;'>设置数量</button>"
        "</div>"
        f"<div class='manual-room-fields-v52'>{_input_rows_html(records)}</div>"
        "<div class='manual-room-actions-v31'>"
        "<button type='button' class='manual-room-add-v52' "
        "onclick='return window.S14ManualRoomAdd ? window.S14ManualRoomAdd(this) : false;'>+ 新增房型</button>"
        "<button type='button' class='manual-room-button-v31' "
        "onclick='return window.S14ManualRoomCalculate ? window.S14ManualRoomCalculate(this) : false;'>即时计算</button>"
        "</div>"
        "<span class='manual-room-hint-v31'>数量可设置为1至100；填写完成后点击“即时计算”，统一计算字符数、卖点表达及本项得分。网页试算不写回正式总分。</span>"
        "</div>"
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
    script = r"""
<script>
(function(){
  if(window.__s14ManualRoomV53Bound) return;
  window.__s14ManualRoomV53Bound=true;
  const terms=__TERMS__;
  const splitPattern=/[\n\r,，、;；|]+/;
  const cleanName=(value)=>String(value||'')
    .replace(/[\u200b\ufeff]/g,'')
    .trim()
    .replace(/^[\s。.!！?？：:,，、;；|"'“”‘’]+|[\s。.!！?？：:,，、;；|"'“”‘’]+$/g,'');
  const escapeHtml=(value)=>String(value||'').replace(/[&<>"']/g,(char)=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[char]));
  const clampCount=(value)=>{
    const number=parseInt(value,10);
    if(!Number.isFinite(number)) return 1;
    return Math.min(100,Math.max(1,number));
  };
  const splitNames=(value)=>{
    const seen=new Set();
    return String(value||'').split(splitPattern).map(cleanName).filter((name)=>{
      if(!name||seen.has(name)) return false;
      seen.add(name);
      return true;
    });
  };
  const renumber=(container)=>{
    Array.from(container.querySelectorAll('.manual-room-field-v52')).forEach((row,index)=>{
      const label=row.querySelector('label');
      const input=row.querySelector('.manual-room-name-input-v52');
      if(label) label.textContent='房型'+(index+1);
      if(input) input.placeholder='请输入第'+(index+1)+'个房型名称';
    });
    const card=container.closest('.manual-room-card-v31');
    const countInput=card&&card.querySelector('.manual-room-count-input-v53');
    if(countInput) countInput.value=Math.max(1,container.querySelectorAll('.manual-room-field-v52').length);
  };
  const appendRow=(container,value='',focus=true)=>{
    const row=document.createElement('div');
    row.className='manual-room-field-v52';
    row.innerHTML='<label></label><input type="text" class="manual-room-name-input-v52" autocomplete="off" spellcheck="false"><button type="button" class="manual-room-remove-v52">删除</button>';
    const input=row.querySelector('.manual-room-name-input-v52');
    if(input) input.value=value;
    container.appendChild(row);
    renumber(container);
    if(input&&focus) input.focus();
    return row;
  };
  const collectNames=(card)=>{
    const names=[];
    const seen=new Set();
    card.querySelectorAll('.manual-room-name-input-v52').forEach((input)=>{
      splitNames(input.value).forEach((name)=>{
        if(!seen.has(name)){seen.add(name);names.push(name);}
      });
    });
    return names;
  };
  const rebuildInputs=(card,names,requestedCount)=>{
    const container=card.querySelector('.manual-room-fields-v52');
    if(!container) return;
    const currentCount=container.querySelectorAll('.manual-room-field-v52').length;
    const total=Math.max(1,clampCount(requestedCount||currentCount),names.length);
    container.innerHTML='';
    for(let index=0;index<total;index++) appendRow(container,names[index]||'',false);
    renumber(container);
  };
  const setCount=(button)=>{
    const card=button.closest('.manual-room-card-v31');
    if(!card) return false;
    const countInput=card.querySelector('.manual-room-count-input-v53');
    const requested=clampCount(countInput&&countInput.value);
    const names=collectNames(card);
    rebuildInputs(card,names,requested);
    return false;
  };
  const calculate=(button)=>{
    const card=button.closest('.manual-room-card-v31');
    if(!card) return false;
    const body=card.querySelector('.manual-room-body-v31');
    const scoreNode=card.querySelector('.manual-room-score-v31');
    const statusNode=card.querySelector('.manual-room-status-v31');
    const noteNode=card.querySelector('.manual-room-score-note-v31');
    const countInput=card.querySelector('.manual-room-count-input-v53');
    if(!body) return false;
    const names=collectNames(card);
    rebuildInputs(card,names,clampCount(countInput&&countInput.value));
    const records=names.map((name)=>{
      const count=name.replace(/\s+/g,'').length;
      const sellingPoint=terms.find((term)=>name.includes(term))||'';
      return {name,count,sellingPoint,passed:count>5&&!!sellingPoint};
    });
    const passed=records.length>0&&records.every((record)=>record.passed);
    body.innerHTML=records.length?records.map((record)=>
      '<tr><td><span class="room-name">'+escapeHtml(record.name)+'</span></td><td>'+record.count+'</td><td>'+escapeHtml(record.sellingPoint||'未命中')+'</td><td><span class="status-badge '+(record.passed?'ok':'disabled')+'">'+(record.passed?'通过':'不通过')+'</span></td></tr>'
    ).join(''):'<tr><td colspan="4">尚未输入房型名称，本项按0分。</td></tr>';
    if(scoreNode) scoreNode.textContent=passed?'4分':'0分';
    if(statusNode){
      statusNode.textContent=passed?'已形成结果':'真实为0';
      statusNode.className='status-badge manual-room-status-v31 '+(passed?'ok':'disabled');
    }
    if(noteNode){
      noteNode.classList.toggle('is-zero',!passed);
      noteNode.textContent=passed?'全部房型名称严格大于5个字且命中卖点表达，网页即时评分为4分。':'存在未通过房型或未输入，网页即时评分为0分。正式总分需重新生成报告。';
    }
    return false;
  };
  window.S14ManualRoomCalculate=calculate;
  window.S14ManualRoomSetCount=setCount;
  window.S14ManualRoomAdd=(button)=>{
    const card=button.closest('.manual-room-card-v31');
    const container=card&&card.querySelector('.manual-room-fields-v52');
    if(container) appendRow(container,'',true);
    return false;
  };
  window.S14ManualRoomRemove=(button)=>{
    const card=button.closest('.manual-room-card-v31');
    const container=card&&card.querySelector('.manual-room-fields-v52');
    const row=button.closest('.manual-room-field-v52');
    if(container&&row){
      const rows=container.querySelectorAll('.manual-room-field-v52');
      if(rows.length>1) row.remove();
      else{
        const input=row.querySelector('.manual-room-name-input-v52');
        if(input) input.value='';
      }
      renumber(container);
    }
    return false;
  };
  document.addEventListener('click',(event)=>{
    const calculateButton=event.target.closest('.manual-room-button-v31');
    if(calculateButton){event.preventDefault();calculate(calculateButton);return;}
    const setCountButton=event.target.closest('.manual-room-set-count-v53');
    if(setCountButton){event.preventDefault();setCount(setCountButton);return;}
    const addButton=event.target.closest('.manual-room-add-v52');
    if(addButton){event.preventDefault();window.S14ManualRoomAdd(addButton);return;}
    const removeButton=event.target.closest('.manual-room-remove-v52');
    if(removeButton){event.preventDefault();window.S14ManualRoomRemove(removeButton);}
  });
  document.addEventListener('keydown',(event)=>{
    if(event.key!=='Enter'||!event.target.matches('.manual-room-count-input-v53')) return;
    event.preventDefault();
    const card=event.target.closest('.manual-room-card-v31');
    const button=card&&card.querySelector('.manual-room-set-count-v53');
    if(button) setCount(button);
  });
})();
</script>
"""
    return script.replace("__TERMS__", terms_json)


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
    "_input_rows_html",
    "_manual_room_card",
    "_script",
    "build_html",
    "build_markdown",
    "write_reports",
]
