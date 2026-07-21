from marketing_diagnosis import dual_channel_report_v56 as report


MEITUAN_HTML = """<!doctype html><html><head><title>美团</title><style>.meituan-only{display:block}</style></head><body>
<header class='topbar'><div class='top-actions'><button onclick='window.print()'>导出</button></div></header>
<div class='page'><nav class='side'><a href='#rule-3'>美团03</a></nav><main>
<section id='overview'>美团概览</section><section id='summary'><input id='ruleSearch'><select id='statusFilter'></select></section>
<article id='rule-3'>美团模块03</article></main></div>
<script>getElementById('ruleSearch');getElementById('statusFilter')</script>
</body></html>"""

CTRIP_HTML = """<!doctype html><html><head><title>携程</title><style>.ctrip-only{display:block}</style></head><body>
<header class='topbar'><div class='top-actions'><button onclick='window.print()'>导出</button></div></header>
<div class='page'><nav class='side'><a href='#rule-3'>携程03</a></nav><main>
<section id='overview'>携程概览</section><section id='summary'><input id='ruleSearch'><select id='statusFilter'></select></section>
<article id='rule-3'>携程模块03</article></main></div>
<script>getElementById('ruleSearch');getElementById('statusFilter')</script>
</body></html>"""


def test_one_html_contains_two_code_generated_channels(monkeypatch):
    monkeypatch.setattr(report.meituan_report, "build_html", lambda result: MEITUAN_HTML)
    monkeypatch.setattr(report, "build_ctrip_page", lambda result: CTRIP_HTML)

    output = report.build_html({"hotel_name": "测试酒店"})

    assert output.count("<!doctype html>") == 1
    assert "data-channel-page='meituan'" in output
    assert "data-channel-page='ctrip'" in output
    assert "?channel=meituan" in output
    assert "?channel=ctrip" in output
    assert "report.html" not in output
    assert "ctrip_report.html" not in output


def test_module_hash_and_duplicate_ids_are_scoped(monkeypatch):
    monkeypatch.setattr(report.meituan_report, "build_html", lambda result: MEITUAN_HTML)
    monkeypatch.setattr(report, "build_ctrip_page", lambda result: CTRIP_HTML)

    output = report.build_html({})

    assert "href='#module-3'" in output
    assert "id='meituan-module-3' data-channel-anchor='module-3'" in output
    assert "id='ctrip-module-3' data-channel-anchor='module-3'" in output
    assert "meituanRuleSearch" in output
    assert "ctripRuleSearch" in output
    assert "new URLSearchParams(window.location.search).get('channel')" in output
