from __future__ import annotations

import re
from typing import Any

from marketing_diagnosis import reporting_runtime_v51 as meituan_report
from marketing_diagnosis.ctrip_report_v54 import build_html as build_ctrip_page


HEAD_RE = re.compile(r"<head\b[^>]*>(?P<content>.*?)</head>", re.DOTALL | re.IGNORECASE)
BODY_RE = re.compile(r"<body\b[^>]*>(?P<content>.*?)</body>", re.DOTALL | re.IGNORECASE)
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
    "ruleSearch": "ctripRuleSearch",
    "statusFilter": "ctripStatusFilter",
}


DUAL_STYLE = """
<style id='DUAL_CHANNEL_REPORT_V58'>
.page.channel-view-v58{display:none}
.page.channel-view-v58.is-active{display:grid}
.ota-channel-switch-v58{
  display:inline-flex;align-items:center;padding:3px;
  border:1px solid var(--line,#dfe7e4);border-radius:9px;background:#f5f8f7
}
.ota-channel-switch-v58 button{
  height:30px;display:inline-flex;align-items:center;justify-content:center;
  min-width:58px;padding:0 14px;border:0;border-radius:6px;background:transparent;
  color:var(--muted,#68747f);font:inherit;font-size:13px;font-weight:800;cursor:pointer
}
.ota-channel-switch-v58 button:hover{color:var(--green,#16845b)}
.ota-channel-switch-v58 button.is-active{
  background:#fff;color:var(--green,#16845b);
  box-shadow:0 2px 8px rgba(31,41,51,.12)
}
@media print{
  .page.channel-view-v58{display:none!important}
  .page.channel-view-v58.is-active{display:grid!important}
  .ota-channel-switch-v58{display:none!important}
}
</style>
"""


DUAL_SCRIPT = r"""
<script id='DUAL_CHANNEL_REPORT_SCRIPT_V58'>
(function(){
  const valid=new Set(['meituan','ctrip']);
  const views=Array.from(document.querySelectorAll('.page[data-channel-view]'));

  function selectedChannel(){
    const value=new URLSearchParams(window.location.search).get('channel');
    return valid.has(value)?value:'meituan';
  }

  function activeView(){
    return document.querySelector('.page[data-channel-view].is-active');
  }

  function updateScope(channel){
    const select=document.querySelector('.topbar .scope-select');
    if(!select) return;
    select.innerHTML=channel==='ctrip'
      ? '<option>携程综合诊断</option><option>PMS经营数据</option><option>携程 eBooking 数据</option>'
      : '<option>综合诊断</option><option>PMS经营数据</option><option>美团EB数据</option>';
  }

  function findTarget(hash){
    const view=activeView();
    if(!view||!hash) return null;
    return view.querySelector('[data-channel-anchor="'+CSS.escape(hash)+'"]')
      || view.querySelector('#'+CSS.escape(hash));
  }

  function scrollToHash(){
    const hash=decodeURIComponent((window.location.hash||'').replace(/^#/,''));
    const target=findTarget(hash);
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
    const hash=decodeURIComponent(anchor.getAttribute('href').slice(1));
    const target=findTarget(hash);
    if(!target) return;
    event.preventDefault();
    const url=new URL(window.location.href);
    url.hash=hash;
    history.pushState({channel:selectedChannel()},'',url);
    target.scrollIntoView({behavior:'smooth',block:'start'});
  });

  window.addEventListener('popstate',()=>apply(selectedChannel(),false));
  window.addEventListener('hashchange',scrollToHash);
  apply(selectedChannel(),false);
})();
</script>
"""


def _scope_search_queries(document: str) -> str:
    # Both channel generators use the same search/filter component. Restrict its
    # card query to the nearest .page so filtering one channel never hides cards
    # in the other hidden channel view.
    document = document.replace(
        "document.querySelectorAll('.diagnosis-card",
        "(search.closest('.page')||document).querySelectorAll('.diagnosis-card",
    )
    document = document.replace(
        'document.querySelectorAll(".diagnosis-card',
        '(search.closest(".page")||document).querySelectorAll(".diagnosis-card',
    )
    return document


def _document_parts(document: str) -> tuple[str, str]:
    head_match = HEAD_RE.search(document)
    body_match = BODY_RE.search(document)
    if head_match is None or body_match is None:
        raise ValueError("Generated report is missing a complete <head> or <body> element")
    return head_match.group("content"), body_match.group("content")


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


def _extra_blocks(pattern: re.Pattern[str], base: str, other: str) -> str:
    existing = set(pattern.findall(base))
    return "".join(block for block in pattern.findall(other) if block not in existing)


def _switch_html() -> str:
    return (
        "<div class='ota-channel-switch-v58' aria-label='报告渠道'>"
        "<button type='button' data-channel-target='meituan' aria-pressed='true'>美团</button>"
        "<button type='button' data-channel-target='ctrip' aria-pressed='false'>携程</button>"
        "</div>"
    )


def _inject_switch(document: str) -> str:
    switch = _switch_html()
    document, count = PRINT_BUTTON_RE.subn(
        lambda match: match.group(1) + switch,
        document,
        count=1,
    )
    if count == 0:
        document, count = TOP_ACTIONS_RE.subn(
            lambda match: match.group(1) + switch,
            document,
            count=1,
        )
    if count == 0:
        raise ValueError("Meituan report is missing the top action area")
    return document


def _add_root_attributes(page: str, channel: str, active: bool) -> str:
    start = re.search(
        r"<div\b(?P<attrs>[^>]*\bclass=['\"][^'\"]*\bpage\b[^'\"]*['\"][^>]*)>",
        page,
        re.DOTALL | re.IGNORECASE,
    )
    if start is None:
        raise ValueError("Generated channel view is missing <div class='page'>")
    attrs = start.group("attrs")
    class_match = re.search(r"\bclass=(['\"])(?P<value>.*?)\1", attrs, re.DOTALL | re.IGNORECASE)
    if class_match is None:
        raise ValueError("Generated channel page has no class attribute")
    classes = class_match.group("value").split()
    if "channel-view-v58" not in classes:
        classes.append("channel-view-v58")
    if active and "is-active" not in classes:
        classes.append("is-active")
    quote = class_match.group(1)
    class_attr = f"class={quote}{' '.join(classes)}{quote}"
    attrs = attrs[: class_match.start()] + class_attr + attrs[class_match.end() :]
    attrs += (
        f" data-channel-view='{channel}'"
        f" aria-hidden='{'false' if active else 'true'}'"
    )
    return page[: start.start()] + f"<div{attrs}>" + page[start.end() :]


def _annotate_meituan(page: str) -> str:
    page = RULE_ID_RE.sub(
        lambda match: (
            f"id={match.group(1)}rule-{match.group('no')}{match.group(1)} "
            f"data-channel-anchor={match.group(1)}module-{match.group('no')}{match.group(1)}"
        ),
        page,
    )
    page = SECTION_ID_RE.sub(
        lambda match: (
            f"id={match.group(1)}{match.group('name')}{match.group(1)} "
            f"data-channel-anchor={match.group(1)}{match.group('name')}{match.group(1)}"
        ),
        page,
    )
    return _add_root_attributes(page, "meituan", True)


def _scope_ctrip(page: str) -> str:
    for source, replacement in SEARCH_ID_REPLACEMENTS.items():
        page = page.replace(f"id='{source}'", f"id='{replacement}'")
        page = page.replace(f'id="{source}"', f'id="{replacement}"')
        page = page.replace(f"getElementById('{source}')", f"getElementById('{replacement}')")
        page = page.replace(f'getElementById("{source}")', f'getElementById("{replacement}")')

    page = RULE_ID_RE.sub(
        lambda match: (
            f"id={match.group(1)}ctrip-rule-{match.group('no')}{match.group(1)} "
            f"data-channel-anchor={match.group(1)}module-{match.group('no')}{match.group(1)}"
        ),
        page,
    )
    page = RULE_HREF_RE.sub(
        lambda match: f"href={match.group(1)}#module-{match.group('no')}{match.group(1)}",
        page,
    )
    page = SECTION_ID_RE.sub(
        lambda match: (
            f"id={match.group(1)}ctrip-{match.group('name')}{match.group(1)} "
            f"data-channel-anchor={match.group(1)}{match.group('name')}{match.group(1)}"
        ),
        page,
    )
    return _add_root_attributes(page, "ctrip", False)


def build_html(result: dict[str, Any]) -> str:
    """Add a code-generated Ctrip channel to the existing Meituan report.html.

    The complete Meituan document remains the production base. Only a channel
    switch, Ctrip-specific styles/scripts and one independently generated Ctrip
    ``.page`` block are injected. This keeps the current Meituan UI and all 23
    Meituan items intact while adding a complete 22-item Ctrip view selected by
    ``?channel=ctrip``.
    """

    meituan_html = _scope_search_queries(meituan_report.build_html(result))
    ctrip_html = _scope_search_queries(build_ctrip_page(result))
    meituan_head, meituan_body = _document_parts(meituan_html)
    ctrip_head, ctrip_body = _document_parts(ctrip_html)

    meituan_page = _balanced_element(meituan_body, "div", "page")
    ctrip_page = _balanced_element(ctrip_body, "div", "page")
    rendered_meituan_page = _annotate_meituan(meituan_page)
    rendered_ctrip_page = _scope_ctrip(ctrip_page)

    output = meituan_html.replace(meituan_page, rendered_meituan_page + rendered_ctrip_page, 1)
    output = _inject_switch(output)

    extra_styles = _extra_blocks(STYLE_RE, meituan_head, ctrip_head)
    output = output.replace("</head>", extra_styles + DUAL_STYLE + "</head>", 1)

    extra_scripts = _extra_blocks(SCRIPT_RE, meituan_body, _scope_ctrip(ctrip_body))
    output = output.replace("</body>", extra_scripts + DUAL_SCRIPT + "</body>", 1)
    return output


__all__ = ["build_html"]
