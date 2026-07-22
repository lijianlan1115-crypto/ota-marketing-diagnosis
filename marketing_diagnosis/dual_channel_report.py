from __future__ import annotations

from typing import Any

from marketing_diagnosis import dual_channel_report_v56 as upstream
from marketing_diagnosis.ctrip_report import build_html as build_ctrip_page


SIDEBAR_STYLE = """
<style id='OTA_COLLAPSIBLE_SIDEBAR_STABLE'>
.page.channel-view-v58{transition:grid-template-columns .2s ease,gap .2s ease}
.side-collapse-button{width:calc(100% - 16px);min-height:34px;margin:8px;padding:6px 9px;display:flex;align-items:center;justify-content:center;gap:7px;border:1px solid var(--line,#dfe7e4);border-radius:8px;background:#f7faf9;color:var(--green,#16845b);font:inherit;font-size:12px;font-weight:800;cursor:pointer}
.side-collapse-button:hover{background:var(--mint2,#f2faf6)}
.side-collapse-button .side-collapse-arrow{font-size:17px;line-height:1}
.page.sidebar-collapsed{grid-template-columns:58px minmax(0,1fr);gap:12px}
.page.sidebar-collapsed .side{overflow-x:hidden}
.page.sidebar-collapsed .side-title,.page.sidebar-collapsed .side-collapse-label{display:none}
.page.sidebar-collapsed .side-collapse-button{width:42px;margin:8px;padding:4px}
.page.sidebar-collapsed .side>a{justify-content:center;gap:0;padding:9px 4px;font-size:0}
.page.sidebar-collapsed .side>a span{width:32px;height:26px;font-size:11px;flex:0 0 auto}
.page.sidebar-collapsed main{min-width:0}
@media(max-width:900px){
  .page.channel-view-v58,.page.channel-view-v58.sidebar-collapsed{grid-template-columns:1fr;gap:12px}
  .page.channel-view-v58 .side{position:relative;top:auto;max-height:260px}
  .page.channel-view-v58.sidebar-collapsed .side{max-height:52px;overflow:hidden}
  .page.channel-view-v58.sidebar-collapsed .side-collapse-button{width:calc(100% - 16px);margin:8px}
  .page.channel-view-v58.sidebar-collapsed .side-collapse-label{display:inline}
  .page.channel-view-v58.sidebar-collapsed .side>a,.page.channel-view-v58.sidebar-collapsed .side-title{display:none}
}
</style>
"""


SIDEBAR_SCRIPT = r"""
<script id='OTA_COLLAPSIBLE_SIDEBAR_SCRIPT_STABLE'>
(function(){
  function setup(){
    document.querySelectorAll('.page[data-channel-view]').forEach(function(view){
      const side=view.querySelector('.side');
      if(!side||side.querySelector('.side-collapse-button')) return;
      const channel=view.dataset.channelView||'report';
      const key='ota-sidebar-collapsed-'+channel;
      const button=document.createElement('button');
      button.type='button';
      button.className='side-collapse-button';
      side.insertBefore(button,side.firstChild);

      function apply(collapsed){
        view.classList.toggle('sidebar-collapsed',collapsed);
        button.setAttribute('aria-expanded',collapsed?'false':'true');
        button.setAttribute('title',collapsed?'展开左侧目录':'收起左侧目录');
        button.innerHTML='<span class="side-collapse-arrow">'+(collapsed?'›':'‹')+'</span><span class="side-collapse-label">'+(collapsed?'展开目录':'收起目录')+'</span>';
        try{localStorage.setItem(key,collapsed?'1':'0');}catch(error){}
        requestAnimationFrame(function(){window.dispatchEvent(new Event('resize'));});
      }

      let collapsed=false;
      try{collapsed=localStorage.getItem(key)==='1';}catch(error){}
      apply(collapsed);
      button.addEventListener('click',function(){apply(!view.classList.contains('sidebar-collapsed'));});
    });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',setup);
  else setup();
})();
</script>
"""


PROFILE_INTERACTION_FIX_SCRIPT = r"""
<script id='CTRIP_USER_PROFILE_INTERACTION_FIX_STABLE'>
(function(){
  function profileRoot(node){
    return node && node.closest ? node.closest('[data-ctrip-profile]') : null;
  }

  document.addEventListener('click',function(event){
    const toggle=event.target.closest('[data-profile-toggle]');
    if(toggle){
      const root=profileRoot(toggle);
      if(!root) return;
      event.preventDefault();
      event.stopImmediatePropagation();

      const code=toggle.getAttribute('data-profile-toggle');
      const expanded=toggle.getAttribute('aria-expanded')==='true';
      root.querySelectorAll('[data-profile-detail="'+CSS.escape(code)+'"]').forEach(function(row){
        row.hidden=expanded;
      });
      toggle.setAttribute('aria-expanded',expanded?'false':'true');
      toggle.textContent=expanded?'展开详情':'收起详情';
      return;
    }

    const tab=event.target.closest('[data-profile-tab]');
    if(tab){
      const root=profileRoot(tab);
      if(!root) return;
      event.preventDefault();
      event.stopImmediatePropagation();

      const name=tab.getAttribute('data-profile-tab');
      root.querySelectorAll('[data-profile-tab]').forEach(function(item){
        const active=item.getAttribute('data-profile-tab')===name;
        item.classList.toggle('active',active);
        item.setAttribute('aria-selected',active?'true':'false');
      });
      root.querySelectorAll('[data-profile-panel]').forEach(function(panel){
        panel.hidden=panel.getAttribute('data-profile-panel')!==name;
      });
    }
  },true);
})();
</script>
"""


def build_html(result: dict[str, Any]) -> str:
    """Build the existing dual report and add stable shared interactions in place."""

    # dual_channel_report_v56 resolves this global at call time. Replacing it keeps
    # the original dual-channel implementation while using the stable Ctrip page.
    upstream.build_ctrip_page = build_ctrip_page
    output = upstream.build_html(result)
    output = output.replace("</head>", SIDEBAR_STYLE + "</head>", 1)
    output = output.replace(
        "</body>",
        SIDEBAR_SCRIPT + PROFILE_INTERACTION_FIX_SCRIPT + "</body>",
        1,
    )
    return output


__all__ = ["build_html"]
