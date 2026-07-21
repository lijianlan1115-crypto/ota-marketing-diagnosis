from marketing_diagnosis.ctrip_report_v54 import transform


BASE_HTML = """<!doctype html><html><head><title>美团报告</title></head><body>
<header class='topbar'><div class='topbar-inner'><div class='brand'><h1>酒店 OTA 全面诊断报告</h1><p>测试酒店</p></div><div class='top-actions'><button onclick='window.print()'>导出报告</button></div></div></header>
<div class='page'><nav class='side'><div class='side-title'>美团目录</div><a href='#rule-1'><span>01</span>月度经营趋势 YOY</a><a href='#rule-3'><span>03</span>美团曝光</a></nav>
<main><section id='overview'>美团总分</section>
<article class='diagnosis-card' data-status='success' data-title='月度经营趋势 YOY' id='rule-1'><div class='card-top'><div class='rule-no'>01</div><div class='card-title'><h3>月度经营趋势 YOY</h3></div><div class='card-tags'><div class='title-meta-item title-score ok'><small>当前得分</small><div class='title-score-value'><strong>9分</strong><span>满分 10分</span></div></div></div></div><div class='result-area'><div id='shared-one-data'>月度经营真实数据</div></div></article>
<article class='diagnosis-card' data-status='success' data-title='房型 RevPAR 与低效房型' id='rule-2'><div class='card-top'><div class='rule-no'>02</div><div class='card-title'><h3>房型 RevPAR 与低效房型</h3></div><div class='card-tags'><div class='title-meta-item title-score ok'><small>当前得分</small><div class='title-score-value'><strong>6分</strong><span>满分 8分</span></div></div></div></div><div class='result-area'><div id='shared-two-data'>房型经营真实数据</div></div></article>
<article class='diagnosis-card' id='rule-3'>美团曝光内容</article></main></div></body></html>"""


def test_ctrip_page_is_independent_and_keeps_shared_pms_cards():
    result = {
        "hotel_name": "测试酒店",
        "period_start": "2026-07-01",
        "period_end": "2026-07-30",
        "ctrip_summary": {"total_score": 72.5, "connected_items": 3},
        "ctrip_items": {
            "1": {"item_score": 7, "full_score": 12},
            "2": {"item_score": 5, "full_score": 9},
            "3": {"fields": {"列表曝光": 1200}, "item_score": 8},
            "6": {"item_score": 6.5},
        },
        "ctrip_psi": {
            "base_score": 4.15,
            "yesterday_change": 0.01,
            "weak_item_count": 0,
            "metrics": {"A": {"score": 4.2}},
        },
    }

    output = transform(BASE_HTML, result)

    assert "携程诊断目录" in output
    assert "平台流量漏斗分析" in output
    assert "YOYO 卡 / 扫码住" in output
    assert "美团曝光内容" not in output
    assert "美团曝光</a>" not in output

    assert "月度经营真实数据" in output
    assert "房型经营真实数据" in output
    assert "7分</strong><span>满分 12分" in output
    assert "5分</strong><span>满分 9分" in output

    assert "携程综合得分" in output
    assert "72.5分" in output
    assert "PSI 服务质量分" in output
    assert "我的基础分" in output
    assert "6.5分</strong><span>满分 8分" in output


def test_missing_ctrip_data_never_reuses_meituan_demo_values():
    output = transform(BASE_HTML, {"hotel_name": "测试酒店"})

    assert "待接入" in output
    assert "¥328,650" not in output
    assert "73.9" not in output
    assert "<section id='overview'>美团总分</section>" not in output
