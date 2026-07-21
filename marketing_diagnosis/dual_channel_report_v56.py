from __future__ import annotations

import re
from typing import Any

from marketing_diagnosis import reporting_runtime_v51 as meituan_report
from marketing_diagnosis.ctrip_report_v54 import build_html as build_ctrip_page


HEAD_RE = re.compile(r"<head\b[^>]*>(?P<content>.*?)</head>", re.DOTALL | re.IGNORECASE)
BODY_RE = re.compile(r"<body\b[^>]*>(?P<content>.*?)</body>", re.DOTALL | re.IGNORECASE)
TITLE_RE = re.compile(r"<title>.*?</title>", re.DOTALL | re.IGNORECASE)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
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
<style id='DUAL_CHANNEL_REPORT_V56'>
.channel-page-v56{display:none}
.channel-page-v56.is-active{display:block}
.ota-channel-switch-v56{
  display:inline-flex;align-items:center;padding:3px;
  border:1px solid var(--line,#dfe7e4);border-radius:9px;background:#f5f8f7
}
.ota-channel-switch-v56 a{
  height:30px;display:inline-flex;align-items:center;justify-content:center;
  min-width:58px;padding:0 14px;border-radius:6px;
  color:var(--muted,#68747f);font-size:13px;font-weight:800;text-decoration:none
}
.ota-channel-switch-v56 a:hover{color:var(--green,#16845b)}
.ota-channel-switch-v56 a.is-active{
  background:#fff;color:var(--green,#16845b);
  box-shadow:0 2px 8px rgba(31,41,51,.12)
}
@media print{
  .channel-page-v56{display:none!important}
  .channel-page-v56.is-active{display:block!important}
  .ota-channel-switch-v56{display:none!important}
}
</style>
"""


DUAL_SCRIPT = r"""
<script id='DUAL_CHANNEL_REPORT_SCRIPT_V56'>
(function(){
  const valid=new Set(['meituan','ctrip']);
  const pages=Array.from(document.querySelectorAll('[data-channel-page]'));

  function selectedChannel(){
    const value=new URLSearchParams(window.location.search).get('channel');
    return valid.has(value)?value:'meituan';
  }

  function activePage(){
    return document.querySelector('[data-channel-page].is-active');
  }

  function scrollToHash(){
    const hash=decodeURIComponent((window.location.hash||'').replace(/^#/,''));
    if(!hash) return;
    const page=activePage();
    if(!page) return;
    const target=page.querySelector('[data-channel-anchor="'+CSS.escape(hash)+'"]');
    if(target) requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));
  }

  function apply(channel, updateUrl){
    const value=valid.has(channel)?channel:'meituan';
    pages.forEach(page=>{
      const active=page.dataset.channelPage===value;
      page.classList.toggle('is-active',active);
      page.setAttribute('aria-hidden',active?'false':'true');
    });
    document.querySelectorAll('[data-channel-target]').forEach(link=>{
      link.classList.toggle('is-active',link.dataset.channelTarget===value);
      link.setAttribute('aria-current',link.dataset.channelTarget===value?'page':'false');
    });
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
    const switchLink=event.target.closest('[data-channel-target]');
    if(switchLink){
      event.preventDefault();
      apply(switchLink.dataset.channelTarget,true);
      return;
    }
    const anchor=event.target.closest('a[href^="#"]');
    if(!anchor) return;
    const value=decodeURIComponent(anchor.getAttribute('href').slice(1));
    const page=activePage();
    const target=page&&page.querySelector('[data-channel-anchor="'+CSS.escape(value)+'"]');
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


def _switch_html() -> str:
    return (
        "<div class='ota-channel-switch-v56' aria-label='报告渠道'>"
        "<a href='?channel=meituan' data-channel-target='meituan'>美团</a>"
        "<a href='?channel=ctrip' data-channel-target='ctrip'>携程</a>"
        "</div>"
    )


def _inject_switch(body: str) -> str:
    switch = _switch_html()
    body, count = PRINT_BUTTON_RE.subn(
        lambda match: match.group(1) + switch,
        body,
        count=1,
    )
    if count == 0:
        body, count = TOP_ACTIONS_RE.subn(
            lambda match: match.group(1) + switch,
            body,
            count=1,
        )
    return switch + body if count == 0 else body


def _scope_body(body: str, channel: str) -> str:
    for source, replacement in SEARCH_ID_REPLACEMENTS.items():
        value = replacement.format(channel=channel)
        body = body.replace(f"id='{source}'", f"id='{value}'")
        body = body.replace(f'id="{source}"', f'id="{value}"')
        body = body.replace(f"getElementById('{source}')", f"getElementById('{value}')")
        body = body.replace(f'getElementById("{source}")', f'getElementById("{value}")')

    body = RULE_ID_RE.sub(
        lambda match: (
            f"id={match.group(1)}{channel}-module-{match.group('no')}{match.group(1)} "
            f"data-channel-anchor={match.group(1)}module-{match.group('no')}{match.group(1)}"
        ),
        body,
    )
    body = RULE_HREF_RE.sub(
        lambda match: f"href={match.group(1)}#module-{match.group('no')}{match.group(1)}",
        body,
    )
    body = SECTION_ID_RE.sub(
        lambda match: (
            f"id={match.group(1)}{channel}-{match.group('name')}{match.group(1)} "
            f"data-channel-anchor={match.group(1)}{match.group('name')}{match.group(1)}"
        ),
        body,
    )
    return _inject_switch(body)


def build_html(result: dict[str, Any]) -> str:
    """Generate one HTML file containing both code-generated channel pages.

    The selected channel is controlled by ``?channel=meituan`` or
    ``?channel=ctrip``. Both channel DOM trees are generated by Python first;
    no iframe and no link to report.html/ctrip_report.html is used.
    """

    meituan_html = meituan_report.build_html(result)
    ctrip_html = build_ctrip_page(result)
    meituan_head, meituan_body = _document_parts(meituan_html)
    ctrip_head, ctrip_body = _document_parts(ctrip_html)

    head = TITLE_RE.sub(
        "<title>酒店 OTA 双渠道诊断报告</title>",
        meituan_head,
        count=1,
    )
    head += _extra_styles(head, ctrip_head)
    head += DUAL_STYLE

    meituan_body = _scope_body(meituan_body, "meituan")
    ctrip_body = _scope_body(ctrip_body, "ctrip")

    return (
        "<!doctype html><html lang='zh-CN'><head>"
        + head
        + "</head><body>"
        + "<div class='channel-page-v56 is-active' data-channel-page='meituan' aria-hidden='false'>"
        + meituan_body
        + "</div>"
        + "<div class='channel-page-v56' data-channel-page='ctrip' aria-hidden='true'>"
        + ctrip_body
        + "</div>"
        + DUAL_SCRIPT
        + "</body></html>"
    )


__all__ = ["build_html"]
