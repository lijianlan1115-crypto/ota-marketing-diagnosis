from __future__ import annotations

from pathlib import Path

from marketing_diagnosis import reporting_v38 as upstream


PERFORMANCE_CHART_TOOLTIP_STYLE = """
<style>/* PERFORMANCE_CHART_TOOLTIP_V60 */
.performance-chart-v54{
  position:relative;
}
.performance-svg-v54{
  cursor:crosshair;
}
.performance-hover-line-v60{
  stroke:#7f8b86;
  stroke-width:1.2;
  stroke-dasharray:5 5;
  pointer-events:none;
}
.performance-hover-tooltip-v60{
  position:absolute;
  z-index:30;
  display:none;
  min-width:245px;
  max-width:320px;
  box-sizing:border-box;
  padding:13px 14px;
  border:1px solid rgba(38,52,61,.16);
  border-radius:12px;
  background:rgba(31,42,49,.96);
  color:#fff;
  box-shadow:0 12px 30px rgba(22,34,30,.24);
  pointer-events:none;
  font-size:12px;
  line-height:1.55;
}
.performance-hover-tooltip-v60 strong{
  display:block;
  margin-bottom:7px;
  font-size:14px;
}
.performance-hover-tooltip-v60 .performance-hover-date-v60{
  margin-bottom:8px;
  color:rgba(255,255,255,.72);
  font-size:11px;
}
.performance-hover-tooltip-v60 .performance-hover-row-v60{
  display:grid;
  grid-template-columns:78px minmax(0,1fr);
  gap:10px;
  align-items:center;
  padding:3px 0;
}
.performance-hover-tooltip-v60 .performance-hover-row-v60 span{
  color:rgba(255,255,255,.68);
}
.performance-hover-tooltip-v60 .performance-hover-row-v60 b{
  text-align:right;
  font-size:13px;
  overflow-wrap:anywhere;
}
</style>
"""


PERFORMANCE_CHART_TOOLTIP_SCRIPT = r"""
<script>/* PERFORMANCE_CHART_TOOLTIP_V60 */
(function(){
  const bind=()=>{
    document.querySelectorAll('.performance-card-v54').forEach((card)=>{
      if(card.dataset.performanceHoverTooltipBound==='1') return;
      const chart=card.querySelector('.performance-chart-v54');
      const svg=card.querySelector('.performance-svg-v54');
      const dataNode=card.querySelector('.performance-data-v54');
      const select=card.querySelector('.performance-select-v54');
      if(!chart||!svg||!dataNode||!select) return;

      card.dataset.performanceHoverTooltipBound='1';
      const tooltip=document.createElement('div');
      tooltip.className='performance-hover-tooltip-v60';
      chart.appendChild(tooltip);

      const labels={revenue:'房费',adr:'ADR',occupancy:'出租率',revpar:'RevPAR'};
      const number=(value)=>{
        if(value===null||value===undefined||value==='') return null;
        const parsed=Number(String(value).replace(/,/g,'').replace(/%$/,''));
        return Number.isFinite(parsed)?parsed:null;
      };
      const normalized=(key,value)=>{
        const parsed=number(value);
        if(parsed===null) return null;
        return key==='occupancy'&&Math.abs(parsed)<=1?parsed*100:parsed;
      };
      const metricText=(key,value)=>{
        const parsed=normalized(key,value);
        if(parsed===null) return '—';
        if(key==='occupancy') return parsed.toFixed(2)+'%';
        return parsed.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});
      };
      const yoyText=(value)=>{
        const parsed=number(value);
        if(parsed===null) return '—';
        const percent=parsed*100;
        if(percent>0) return '↑ +'+percent.toFixed(2)+'%';
        if(percent<0) return '↓ '+percent.toFixed(2)+'%';
        return '→ 0.00%';
      };
      const escapeHtml=(value)=>String(value??'').replace(/[&<>"']/g,(char)=>({
        '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
      }[char]));
      const periods=()=>{
        try{return JSON.parse(dataNode.textContent||'[]');}catch(_){return [];}
      };
      const hide=()=>{
        tooltip.style.display='none';
        svg.querySelectorAll('.performance-hover-line-v60').forEach((node)=>node.remove());
      };
      const show=(event)=>{
        const rows=periods();
        if(!rows.length) return hide();
        const rect=svg.getBoundingClientRect();
        if(!rect.width||!rect.height) return hide();

        const viewX=(event.clientX-rect.left)/rect.width*720;
        const left=72;
        const right=650;
        if(viewX<left-28||viewX>right+28) return hide();
        const ratio=Math.max(0,Math.min(1,(viewX-left)/(right-left)));
        const index=Math.max(0,Math.min(rows.length-1,Math.round(ratio*Math.max(1,rows.length-1))));
        const period=rows[index]||{};
        const key=select.value||'revenue';
        const metric=(period.metrics||[]).find((item)=>String(item.key||'')===key)||{};
        const x=left+(right-left)*index/Math.max(1,rows.length-1);

        let line=svg.querySelector('.performance-hover-line-v60');
        if(!line){
          line=document.createElementNS('http://www.w3.org/2000/svg','line');
          line.setAttribute('class','performance-hover-line-v60');
          svg.appendChild(line);
        }
        line.setAttribute('x1',x.toFixed(1));
        line.setAttribute('x2',x.toFixed(1));
        line.setAttribute('y1','42');
        line.setAttribute('y2','278');

        tooltip.innerHTML=
          '<strong>'+escapeHtml(labels[key]||key)+'</strong>'+
          '<div class="performance-hover-date-v60">本期：'+escapeHtml(period.current_range||'—')+
          '<br>去年同期：'+escapeHtml(period.previous_range||'—')+'</div>'+
          '<div class="performance-hover-row-v60"><span>本期数值</span><b>'+escapeHtml(metricText(key,metric.current))+'</b></div>'+
          '<div class="performance-hover-row-v60"><span>去年同期</span><b>'+escapeHtml(metricText(key,metric.previous))+'</b></div>'+
          '<div class="performance-hover-row-v60"><span>YOY</span><b>'+escapeHtml(yoyText(metric.yoy))+'</b></div>';
        tooltip.style.display='block';

        const chartRect=chart.getBoundingClientRect();
        let tooltipX=event.clientX-chartRect.left+14;
        let tooltipY=event.clientY-chartRect.top+14;
        const maxX=Math.max(8,chart.clientWidth-tooltip.offsetWidth-8);
        const maxY=Math.max(8,chart.clientHeight-tooltip.offsetHeight-8);
        tooltipX=Math.max(8,Math.min(maxX,tooltipX));
        tooltipY=Math.max(8,Math.min(maxY,tooltipY));
        tooltip.style.left=tooltipX+'px';
        tooltip.style.top=tooltipY+'px';
      };

      svg.addEventListener('mousemove',show);
      svg.addEventListener('mouseleave',hide);
      select.addEventListener('change',hide);
    });
  };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',bind,{once:true});
  else bind();
})();
</script>
"""


def enable_performance_chart_tooltip(html_text: str) -> str:
    if "PERFORMANCE_CHART_TOOLTIP_V60" not in html_text:
        html_text = html_text.replace(
            "</head>",
            PERFORMANCE_CHART_TOOLTIP_STYLE + "</head>",
            1,
        )
        html_text = html_text.replace(
            "</body>",
            PERFORMANCE_CHART_TOOLTIP_SCRIPT + "</body>",
            1,
        )
    return html_text


def build_html(result: dict) -> str:
    return enable_performance_chart_tooltip(upstream.build_html(result))


def build_markdown(result: dict) -> str:
    return upstream.build_markdown(result)


def write_reports(result: dict, output_dir: str | Path) -> dict[str, str]:
    paths = upstream.write_reports(result, output_dir)
    html_path = Path(paths["report_html"])
    html_path.write_text(
        enable_performance_chart_tooltip(html_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    return paths


__all__ = [
    "PERFORMANCE_CHART_TOOLTIP_SCRIPT",
    "PERFORMANCE_CHART_TOOLTIP_STYLE",
    "build_html",
    "build_markdown",
    "enable_performance_chart_tooltip",
    "write_reports",
]
