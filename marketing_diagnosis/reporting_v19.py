from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from marketing_diagnosis import reporting_v18


CROWN_STYLE = """
<style>
.manual-crown-form-v19{display:grid;grid-template-columns:repeat(3,minmax(180px,1fr));gap:14px;align-items:end}
.manual-crown-field-v19 label{display:block;margin-bottom:7px;color:var(--muted);font-size:12px;font-weight:800}
.manual-crown-field-v19 input,.manual-crown-field-v19 select{width:100%;height:42px;border:1px solid #d8e3df;border-radius:9px;background:#fff;padding:0 12px;color:var(--ink);font:inherit;outline:none}
.manual-crown-field-v19 input:focus,.manual-crown-field-v19 select:focus{border-color:#78bda5;box-shadow:0 0 0 3px rgba(22,132,91,.10)}
.manual-crown-actions-v19{display:flex;gap:9px;margin-top:14px;align-items:center;flex-wrap:wrap}
.manual-crown-actions-v19 button{height:38px;border-radius:8px;padding:0 15px;font-weight:800;cursor:pointer}
.manual-crown-save-v19{border:1px solid #16845b;background:#16845b;color:#fff}
.manual-crown-clear-v19{border:1px solid #d7e0dd;background:#fff;color:#52606b}
.manual-crown-message-v19{font-size:12px;color:var(--muted)}
.manual-crown-summary-v19{margin-top:16px;padding:14px;border:1px solid #dfe9e5;border-radius:10px;background:#f8fbfa;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.manual-crown-summary-v19 small{display:block;color:var(--muted);font-weight:800}.manual-crown-summary-v19 strong{display:block;margin-top:5px;font-size:17px}
@media(max-width:760px){.manual-crown-form-v19,.manual-crown-summary-v19{grid-template-columns:1fr}}
</style>
"""


_OLD_CROWN_SCRIPT = re.compile(
    r"<script>\s*\(function\(\)\{.*?crown-save-button.*?</script>",
    re.DOTALL,
)
_CROWN_CARD = re.compile(
    r"<article class='diagnosis-card'[^>]*id='rule-22'>.*?</article>",
    re.DOTALL,
)


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _score_base(result: dict[str, Any]) -> float:
    """Sum scored Meituan items before the manual crown item.

    Display-only items and the crown item itself are excluded. Missing scores are
    ignored rather than converted to zero; the browser adds the crown score only
    after a valid manual selection is saved.
    """

    visual = result.get("visual_diagnosis") or {}
    items = list(visual.get("items") or [])
    raw = 0.0
    for item in items:
        if int(item.get("standard_item_id") or 0) == 22:
            continue
        if item.get("participates_in_score") is False:
            continue
        score = item.get("item_score")
        if score is None:
            continue
        raw += float(score)
    return round(raw, 4)


def _manual_crown_card(result: dict[str, Any]) -> str:
    hotel = str(result.get("hotel_name") or result.get("hotel_id") or "hotel")
    start = str(result.get("period_start") or "")
    end = str(result.get("period_end") or "")
    storage_key = "s14:crown:" + hotel + ":" + start + ":" + end
    base_raw = _score_base(result)

    return f"""
<article class='diagnosis-card' data-status='manual_pending' data-title='酒店挂冠' id='rule-22'>
  <div class='card-top'>
    <div class='rule-no'>23</div>
    <div class='card-title'><h3>酒店挂冠</h3><p>选择当前挂冠类型，保存后立即计算本项及总得分。</p></div>
    <div class='card-tags'>
      <div class='title-meta-item title-period'><small>统计周期</small><strong>人工录入</strong></div>
      <div class='title-meta-item title-score pending' id='crown-score-box'><small>当前得分</small><div class='title-score-value'><strong id='crown-score'>待计算</strong><span>满分 1分</span></div></div>
      <span class='status-badge manual' id='crown-status'>待人工录入</span>
    </div>
  </div>
  <div class='result-area'>
    <div class='viz-card'>
      <div class='manual-crown-form-v19'>
        <div class='manual-crown-field-v19'>
          <label for='crown-type-input'>挂冠类型</label>
          <select id='crown-type-input'>
            <option value=''>请选择</option>
            <option value='黑金挂冠'>黑金挂冠（1分）</option>
            <option value='普通挂冠'>普通挂冠（0.5分）</option>
            <option value='无挂冠'>无挂冠（0分）</option>
          </select>
        </div>
        <div class='manual-crown-field-v19'><label for='crown-operator-input'>录入人</label><input id='crown-operator-input' type='text' maxlength='50' placeholder='请输入录入人'></div>
        <div class='manual-crown-field-v19'><label for='crown-time-input'>录入时间</label><input id='crown-time-input' type='datetime-local'></div>
      </div>
      <div class='manual-crown-actions-v19'>
        <button class='manual-crown-save-v19' type='button' id='crown-save-button'>保存录入</button>
        <button class='manual-crown-clear-v19' type='button' id='crown-clear-button'>清空</button>
        <span class='manual-crown-message-v19' id='crown-message'>选择挂冠类型并保存后自动评分。</span>
      </div>
      <div class='manual-crown-summary-v19'>
        <div><small>挂冠类型</small><strong id='crown-type-display'>尚未录入</strong></div>
        <div><small>本项得分</small><strong id='crown-score-display'>待计算</strong></div>
        <div><small>录入人</small><strong id='crown-operator-display'>—</strong></div>
        <div><small>录入时间</small><strong id='crown-time-display'>—</strong></div>
      </div>
    </div>
  </div>
</article>
<script>
(function(){{
  const STORAGE_KEY={json.dumps(storage_key, ensure_ascii=False)};
  const BASE_RAW={base_raw};
  function el(id){{return document.getElementById(id);}}
  function nowLocal(){{
    const d=new Date(),pad=n=>String(n).padStart(2,'0');
    return `${{d.getFullYear()}}-${{pad(d.getMonth()+1)}}-${{pad(d.getDate())}}T${{pad(d.getHours())}}:${{pad(d.getMinutes())}}`;
  }}
  function scoreFor(type){{
    if(type==='黑金挂冠')return 1;
    if(type==='普通挂冠')return 0.5;
    if(type==='无挂冠')return 0;
    return null;
  }}
  function scoreText(score){{return score===null?'待计算':`${{score}}分`;}}
  function summaryRow(){{
    const link=document.querySelector("#summary a[href='#rule-22']");
    return link?link.closest('tr'):null;
  }}
  function updateTotal(score){{
    const node=document.querySelector('.total-score-v17 strong');
    if(!node)return;
    const raw=BASE_RAW+(score===null?0:score);
    node.textContent=String(Math.round(raw*100)/100);
  }}
  function apply(data){{
    const type=data.crown_type||'';
    const score=scoreFor(type);
    const filled=score!==null;
    el('crown-type-input').value=filled?type:'';
    el('crown-operator-input').value=data.operator||'';
    el('crown-time-input').value=data.recorded_at||nowLocal();
    el('crown-type-display').textContent=filled?type:'尚未录入';
    el('crown-score').textContent=scoreText(score);
    el('crown-score-display').textContent=scoreText(score);
    el('crown-operator-display').textContent=data.operator||'—';
    el('crown-time-display').textContent=data.recorded_at?data.recorded_at.replace('T',' '):'—';
    el('crown-status').textContent=filled?'已人工录入':'待人工录入';
    el('crown-status').className='status-badge '+(filled?'ok':'manual');
    el('crown-score-box').className='title-meta-item title-score '+(filled?'ok':'pending');
    const row=summaryRow();
    if(row){{
      const cells=row.querySelectorAll('td');
      if(cells.length>=5){{
        cells[3].textContent=scoreText(score);
        cells[4].innerHTML=filled?"<span class='status-badge ok'>已人工录入</span>":"<span class='status-badge manual'>待人工录入</span>";
      }}
    }}
    updateTotal(score);
  }}
  document.addEventListener('DOMContentLoaded',function(){{
    let data={{}};
    try{{data=JSON.parse(localStorage.getItem(STORAGE_KEY)||'{{}}');}}catch(e){{data={{}};}}
    apply(data);
    el('crown-save-button').addEventListener('click',function(){{
      const crown_type=el('crown-type-input').value;
      if(scoreFor(crown_type)===null){{el('crown-message').textContent='请先选择挂冠类型。';return;}}
      const saved={{crown_type,operator:el('crown-operator-input').value.trim(),recorded_at:el('crown-time-input').value||nowLocal()}};
      localStorage.setItem(STORAGE_KEY,JSON.stringify(saved));
      apply(saved);
      el('crown-message').textContent='已保存并完成评分。';
    }});
    el('crown-clear-button').addEventListener('click',function(){{
      localStorage.removeItem(STORAGE_KEY);
      apply({{recorded_at:nowLocal()}});
      el('crown-message').textContent='已清空本地录入。';
    }});
  }});
}})();
</script>
"""


def _replace_crown(html_text: str, result: dict[str, Any]) -> str:
    html_text = _OLD_CROWN_SCRIPT.sub("", html_text, count=1)
    return _CROWN_CARD.sub(lambda _: _manual_crown_card(result), html_text, count=1)


def build_html(result: dict[str, Any]) -> str:
    html_text = reporting_v18.build_html(result)
    html_text = _replace_crown(html_text, result)
    return html_text.replace("</head>", CROWN_STYLE + "</head>", 1)


def build_markdown(result: dict[str, Any]) -> str:
    return reporting_v18.build_markdown(result)


def write_reports(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    paths = reporting_v18.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(build_html(result), encoding="utf-8")
    return paths


__all__ = ["build_html", "build_markdown", "write_reports"]