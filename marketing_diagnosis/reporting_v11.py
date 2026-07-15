from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v10


EXTRA_STYLE = """
<style>
.manual-crown-form{display:grid;grid-template-columns:repeat(3,minmax(180px,1fr));gap:14px;align-items:end}
.manual-crown-field label{display:block;margin-bottom:7px;color:var(--muted);font-size:12px;font-weight:800}
.manual-crown-field input{width:100%;height:42px;border:1px solid #d8e3df;border-radius:9px;background:#fff;padding:0 12px;color:var(--ink);font:inherit;outline:none}
.manual-crown-field input:focus{border-color:#78bda5;box-shadow:0 0 0 3px rgba(22,132,91,.10)}
.manual-crown-actions{display:flex;gap:9px;margin-top:14px;align-items:center;flex-wrap:wrap}
.manual-crown-actions button{height:38px;border-radius:8px;padding:0 15px;font-weight:800;cursor:pointer}
.manual-crown-save{border:1px solid #16845b;background:#16845b;color:#fff}
.manual-crown-clear{border:1px solid #d7e0dd;background:#fff;color:#52606b}
.manual-crown-message{font-size:12px;color:var(--muted)}
.manual-crown-summary{margin-top:16px;padding:14px;border:1px solid #dfe9e5;border-radius:10px;background:#f8fbfa;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.manual-crown-summary small{display:block;color:var(--muted);font-weight:800}.manual-crown-summary strong{display:block;margin-top:5px;font-size:17px}
@media(max-width:760px){.manual-crown-form,.manual-crown-summary{grid-template-columns:1fr}}
</style>
"""


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _manual_card(result: dict[str, Any]) -> str:
    hotel = str(result.get("hotel_name") or result.get("hotel_id") or "hotel")
    start = str(result.get("period_start") or "")
    end = str(result.get("period_end") or "")
    storage_key = "s14:crown:" + hotel + ":" + start + ":" + end
    storage_key_js = json.dumps(storage_key, ensure_ascii=False)

    return f"""
<article class='diagnosis-card' data-status='manual_pending' data-title='酒店挂冠' id='rule-22'>
  <div class='card-top'>
    <div class='rule-no'>22</div>
    <div class='card-title'><h3>酒店挂冠</h3><p>由用户填写挂冠类型、录入人和录入时间。</p></div>
    <div class='card-tags'>
      <div class='title-meta-item title-period'><small>统计周期</small><strong>人工录入</strong></div>
      <div class='title-meta-item title-score pending' id='crown-score-box'><small>当前得分</small><div class='title-score-value'><strong id='crown-score'>待计算</strong><span>满分 1分</span></div></div>
      <span class='status-badge manual' id='crown-status'>待人工录入</span>
    </div>
  </div>
  <div class='result-area'>
    <div class='viz-card'>
      <div class='manual-crown-form'>
        <div class='manual-crown-field'><label for='crown-type-input'>挂冠类型</label><input id='crown-type-input' type='text' maxlength='100' placeholder='请输入酒店挂冠类型'></div>
        <div class='manual-crown-field'><label for='crown-operator-input'>录入人</label><input id='crown-operator-input' type='text' maxlength='50' placeholder='请输入录入人'></div>
        <div class='manual-crown-field'><label for='crown-time-input'>录入时间</label><input id='crown-time-input' type='datetime-local'></div>
      </div>
      <div class='manual-crown-actions'>
        <button class='manual-crown-save' type='button' id='crown-save-button'>保存录入</button>
        <button class='manual-crown-clear' type='button' id='crown-clear-button'>清空</button>
        <span class='manual-crown-message' id='crown-message'>填写挂冠类型后保存，本项记1分。</span>
      </div>
      <div class='manual-crown-summary'>
        <div><small>挂冠类型</small><strong id='crown-type-display'>尚未录入</strong></div>
        <div><small>录入人</small><strong id='crown-operator-display'>—</strong></div>
        <div><small>录入时间</small><strong id='crown-time-display'>—</strong></div>
      </div>
    </div>
    <div class='field-standard-note'><b>数据来源：</b>用户输入（当前浏览器本地保存）<br><b>对应字段：</b>crown_type、operator、recorded_at</div>
    <div class='notice'>人工录入项；未录入不等于无挂冠。当前版本保存在浏览器本地，不写入数据库。</div>
  </div>
</article>
<script>
(function(){{
  const STORAGE_KEY={storage_key_js};
  function el(id){{return document.getElementById(id);}}
  function nowLocal(){{
    const d=new Date(), pad=n=>String(n).padStart(2,'0');
    return `${{d.getFullYear()}}-${{pad(d.getMonth()+1)}}-${{pad(d.getDate())}}T${{pad(d.getHours())}}:${{pad(d.getMinutes())}}`;
  }}
  function summaryRow(){{
    const link=document.querySelector("#summary a[href='#rule-22']");
    return link ? link.closest('tr') : null;
  }}
  function apply(data){{
    const filled=Boolean((data.crown_type||'').trim());
    el('crown-type-input').value=data.crown_type||'';
    el('crown-operator-input').value=data.operator||'';
    el('crown-time-input').value=data.recorded_at||nowLocal();
    el('crown-type-display').textContent=filled ? data.crown_type : '尚未录入';
    el('crown-operator-display').textContent=data.operator||'—';
    el('crown-time-display').textContent=data.recorded_at ? data.recorded_at.replace('T',' ') : '—';
    el('crown-score').textContent=filled ? '1分' : '待计算';
    el('crown-status').textContent=filled ? '已人工录入' : '待人工录入';
    el('crown-status').className='status-badge '+(filled?'ok':'manual');
    const row=summaryRow();
    if(row){{
      const cells=row.querySelectorAll('td');
      if(cells.length>=5){{
        cells[3].textContent=filled?'1分':'待计算';
        cells[4].innerHTML=filled?"<span class='status-badge ok'>已人工录入</span>":"<span class='status-badge manual'>待人工录入</span>";
      }}
    }}
  }}
  document.addEventListener('DOMContentLoaded',function(){{
    let data={{}};
    try{{data=JSON.parse(localStorage.getItem(STORAGE_KEY)||'{{}}');}}catch(e){{data={{}};}}
    apply(data);
    el('crown-save-button').addEventListener('click',function(){{
      const crown_type=el('crown-type-input').value.trim();
      if(!crown_type){{el('crown-message').textContent='请先填写挂冠类型。';return;}}
      const saved={{crown_type,operator:el('crown-operator-input').value.trim(),recorded_at:el('crown-time-input').value||nowLocal()}};
      localStorage.setItem(STORAGE_KEY,JSON.stringify(saved));
      apply(saved);el('crown-message').textContent='已保存到当前浏览器。';
    }});
    el('crown-clear-button').addEventListener('click',function(){{
      localStorage.removeItem(STORAGE_KEY);apply({{recorded_at:nowLocal()}});el('crown-message').textContent='已清空本地录入。';
    }});
  }});
}})();
</script>
"""


def _replace_manual_card(html_text: str, result: dict[str, Any]) -> str:
    pattern = re.compile(
        r"<article class='diagnosis-card'[^>]*id='rule-22'>.*?</article>",
        re.DOTALL,
    )
    return pattern.sub(lambda _: _manual_card(result), html_text, count=1)


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v10.build_html(result)
    html_text = html_text.replace("</head>", EXTRA_STYLE + "</head>", 1)
    return _replace_manual_card(html_text, result)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v10.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v10.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = ["build_html", "build_markdown", "write_reports"]
