from __future__ import annotations

import re
from typing import Any

from marketing_diagnosis import reporting_runtime_v51 as meituan_report
from marketing_diagnosis.ctrip_report_v54 import build_html as build_ctrip_page


HEAD_RE = re.compile(r"<head\b[^>]*>(?P<content>.*?)</head>", re.DOTALL | re.IGNORECASE)
BODY_RE = re.compile(r"<body\b[^>]*>(?P<content>.*?)</body>", re.DOTALL | re.IGNORECASE)
TITLE_RE = re.compile(r"<title>.*?</title>", re.DOTALL | re.IGNORECASE)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
PRINT_BUTTON_RE = re.compile(
    r"(<button\b[^>]*onclick=['\"]window\.print\(\)['\"][^>]*>.*?</button>)",
    re.DOTALL | re.IGNORECASE,
)
TOP_ACTIONS_RE = re.compile(
    r"(<div\b[^>]*class=['\"][^'\"]*\btop-actions\b[^'\"]*['\"][^>]*>)",
    re.DOTALL | re.IGNORECASE,
)
RULE_ID_RE = re.compile(r"\bid=(['\"])(?:rule|module)-(?P<no>\d+)\1", re.IGNORECASE)
RULE_HREF_RE = re.compile(r"\bhref=(['\"])#(?:rule|module)-(?P<no>\d+)\1", re.IGNORECASE)
SECTION_ID_RE = re.compile(r"\bid=(['\"])(?P<name>overview|summary)\1", re.IGNORECASE)
SEARCH_ID_REPLACEMENTS = {
    "ruleSearch": "{channel}RuleSearch",
    "statusFilter": "{channel}StatusFilter",
}

DUAL_STYLE = """
<style id='DUAL_CHANNEL_REPORT_V57'>
.channel-view-v57{display:none}
.channel-view-v57.is-active{display:block}
.ota-channel-switch-v57{
  display:inline-flex;align-items:center;padding:3px;
  border:1px solid var(--line,#dfe7e4);border-radius:9px;background:#f5f8f7
}
.ota-channel-switch-v57 button{
  height:30px;display:inline-flex;align-items:center;justify-content:center;
  min-width:58px;padding:0 14px;border:0;border-radius:6px;background:transparent;
  color:var(--muted,#68747f);font:inherit;font-size:13px;font-weight:800;cursor:pointer
}
.ota-channel-switch-v57 button:hover{color:var(--green,#16845b)}
.ota-channel-switch-v57 button.is-active{
  background:#fff;color:var(--green,#16845b);
  box-shadow:0 2px 8px rgba(31,41,51,.12)
}
@media print{
  .channel-view-v57{display:none!important}
  .channel-view-v57.is-active{display:block!important}
  .ota-channel-switch-v57{display:none!important}
}
</style>
"""

DUAL_SCRIPT = r"""
<script id='DUAL_CHANNEL_REPORT_SCRIPT_V57'>
(function(){
  const valid=new Set(['meituan','ctrip']);
  const views=Array.from(document.querySelectorAll('[data-channel-view]'));

  function selectedChannel(){
    const value=new URLSearchParams(window.location.search).get('channel');
    return valid.has(value)?value:'meituan';
  }

  function activeView(){
    return document.querySelector('[data-channel-view].is-active');
  }

  function updateScope(channel){
    const select=document.querySelector('.topbar .scope-select');
    if(!select) return;
    select.innerHTML=channel==='ctrip'
      ? '<option>携程综合诊断</option><option>PMS经营数据</option><option>携程 eBooking 数据</option>'
      : '<option>综合诊断</option><option>PMS经营数据</option><option>美团EB数据</option>';
  }

  function scrollToHash(){
    const hash=decodeURIComponent((window.location.hash||'').replace(/^#/,''));
    if(!hash) return;
    const view=activeView();
    if(!view) return;
    const target=view.querySelector('[data-channel-anchor="'+CSS.escape(hash)+'"]');
    if(target) requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));
  }

  function apply(channel,updateUrl){
    const value=valid.has(channel)?channel:'meituan';
    views.forEach(view=>{
      const active=view.dataset.channelView===value;
      view.classList.toggle('is-active',active);
      view.setAttribute('aria-hidden',active?'false':'true');
    });
    document.querySelectorAll('[data-channel-target]').forEach(button=>{
      const active=button.dataset.channelTarget===value;
      button.classList.toggle('is-active',active);
      button.setAttribute('aria-pressed',active?'true':'false');
    });
    updateScope(value);
    document.documentElement.dataset.channel=value;
    document.title=(value==='ctrip'?'携程':'美团')+'｜酒店 OTA 全面诊断报告';
    if(updateUrl){
      const url=new URL(window.location.href);
      url.searchParams.set('channel',value);
      history.pushState({channel:value},'',url);
    }
    scrollToHash();
  }

  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-channel-target]');
    if(button){
      event.preventDefault();
      apply(button.dataset.channelTarget,true);
      return;
    }
    const anchor=event.target.closest('a[href^="#"]');
    if(!anchor) return;
    const value=decodeURIComponent(anchor.getAttribute('href').slice(1));
    const view=activeView();
    const target=view&&view.querySelector('[data-channel-anchor="'+CSS.escape(value)+'"]');
    if(!target) return;
    event.preventDefault();
    const url=new URL(window.location.href);
    url.hash=value;
    history.pushState({channel:selectedChannel()},'',url);
    target.scrollIntoView({behavior:'smooth',block:'start'});
  });

  window.addEventListener('popstate',()=>apply(selectedChannel(),false));
  window.addEventListener('hashchange',scrollToHash);
  apply(selectedChannel(),false);
})();
</script>
"""


def _document_parts(document: str) -> tuple[str, str]:
    head_match = HEAD_RE.search(document)
    body_match = BODY_RE.search(document)
    if head_match is None or body_match is None:
        raise ValueError("Generated report is missing a complete <head> or <body> element")
    return head_match.group("content"), body_match.group("content")


def _extra_styles(base_head: str, other_head: str) -> str:
    existing = set(STYLE_RE.findall(base_head))
    return "".join(block for block in STYLE_RE.findall(other_head) if block not in existing)


def _balanced_element(document: str, tag: str, class_name: str) -> str:
    start_re = re.compile(
        rf"<{re.escape(tag)}\b[^>]*class=['\"][^'\"]*\b{re.escape(class_name)}\b[^'\"]*['\"][^>]*>",
        re.DOTALL | re.IGNORECASE,
    )
    start = start_re.search(document)
    if start is None:
        raise ValueError(f"Generated report is missing <{tag} class='{class_name}'>")

    token_re = re.compile(rf"</?{re.escape(tag)}\b[^>]*>", re.DOTALL | re.IGNORECASE)
    depth = 0
    for token in token_re.finditer(document, start.start()):
        if token.group(0).lstrip().startswith("</"):
            depth -= 1
            if depth == 0:
                return document[start.start() : token.end()]
        else:
            depth += 1
    raise ValueError(f"Generated report has an unclosed <{tag} class='{class_name}'>")


def _switch_html() -> str:
    return (
        "<div class='ota-channel-switch-v57' aria-label='报告渠道'>"
        "<button type='button' data-channel-target='meituan' aria-pressed='true'>美团</button>"
        "<button type='button' data-channel-target='ctrip' aria-pressed='false'>携程</button>"
        "</div>"
    )


def _inject_switch(header: str) -> str:
    switch = _switch_html()
    header, count = PRINT_BUTTON_RE.subn(
        lambda match: match.group(1) + switch,
        header,
        count=1,
    )
    if count == 0:
        header, count = TOP_ACTIONS_RE.subn(
            lambda match: match.group(1) + switch,
            header,
            count=1,
        )
    return switch + header if count == 0 else header


def _scope_content(content: str, channel: str) -> str:
    for source, replacement in SEARCH_ID_REPLACEMENTS.items():
        value = replacement.format(channel=channel)
        content = content.replace(f"id='{source}'", f"id='{value}'")
        content = content.replace(f'id="{source}"', f'id="{value}"')
        content = content.replace(f"getElementById('{source}')", f"getElementById('{value}')")
        content = content.replace(f'getElementById("{source}")', f'getElementById("{value}")')

    content = RULE_ID_RE.sub(
        lambda match: (
            f"id={match.group(1)}{channel}-module-{match.group('no')}{match.group(1)} "
            f"data-channel-anchor={match.group(1)}module-{match.group('no')}{match.group(1)}"
        ),
        content,
    )
    content = RULE_HREF_RE.sub(
        lambda match: f"href={match.group(1)}#module-{match.group('no')}{match.group(1)}",
        content,
    )
    content = SECTION_ID_RE.sub(
        lambda match: (
            f"id={match.group(1)}{channel}-{match.group('name')}{match.group(1)} "
            f"data-channel-anchor={match.group(1)}{match.group('name')}{match.group(1)}"
        ),
        content,
    )
    return content


def _unique_scripts(*bodies: str) -> str:
    output: list[str] = []
    seen: set[str] = set()
    for body in bodies:
        for block in SCRIPT_RE.findall(body):
            if block not in seen:
                seen.add(block)
                output.append(block)
    return "".join(output)


def build_html(result: dict[str, Any]) -> str:
    """Generate the production report.html with two code-generated channel views.

    The file has one shared header and one shared page shell. Meituan and Ctrip
    each render their own directory, overview, summary and modules. The query
    string ``?channel=meituan`` or ``?channel=ctrip`` only controls which
    generated channel view is visible.
    """

    meituan_html = meituan_report.build_html(result)
    ctrip_html = build_ctrip_page(result)
    meituan_head, meituan_body = _document_parts(meituan_html)
    ctrip_head, ctrip_body = _document_parts(ctrip_html)

    scoped_meituan_body = _scope_content(meituan_body, "meituan")
    scoped_ctrip_body = _scope_content(ctrip_body, "ctrip")

    header = _inject_switch(_balanced_element(scoped_meituan_body, "header", "topbar"))
    meituan_page = _balanced_element(scoped_meituan_body, "div", "page")
    ctrip_page = _balanced_element(scoped_ctrip_body, "div", "page")

    head = TITLE_RE.sub(
        "<title>酒店 OTA 全面诊断报告</title>",
        meituan_head,
        count=1,
    )
    head += _extra_styles(head, ctrip_head)
    head += DUAL_STYLE

    scripts = _unique_scripts(scoped_meituan_body, scoped_ctrip_body)

    return (
        "<!doctype html><html lang='zh-CN'><head>"
        + head
        + "</head><body>"
        + header
        + "<section class='channel-view-v57 is-active' data-channel-view='meituan' aria-hidden='false'>"
        + meituan_page
        + "</section>"
        + "<section class='channel-view-v57' data-channel-view='ctrip' aria-hidden='true'>"
        + ctrip_page
        + "</section>"
        + scripts
        + DUAL_SCRIPT
        + "</body></html>"
    )


__all__ = ["build_html"]
