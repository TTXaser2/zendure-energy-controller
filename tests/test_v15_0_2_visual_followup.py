from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_detail_window_is_adaptive_and_shared_by_magnifier_and_parent_overlay():
    js = _read("static/graph_v14_1.js")
    page = _read("graph_ui/page.py")
    assert "function adaptiveDetailWindow(range,ts)" in js
    assert "const MAX_DETAIL_HALF_MS = 5*60000" in js
    assert "Math.min(MAX_DETAIL_HALF_MS*2,span*.5)" in js
    assert "const mini=adaptiveDetailWindow(currentRange(),ts)" in js
    assert "adaptiveDetailWindow(range,ts)" in js
    assert "Zoom um den Cursor" in js
    assert "Zoom um den Cursor" in page
    assert "10-Minuten-Zoom um den Cursor" not in js
    assert "10-Minuten-Zoom um den Cursor" not in page


def test_command_values_panel_is_below_chart_and_keeps_constant_geometry():
    js = _read("static/graph_v14_1.js")
    css = _read("static/graph_v14_1.css")
    page = _read("graph_ui/page.py")
    chart_pos = page.index('<div class="gf-chart-wrap gf-chart-context"><canvas id="gfCommandChart"></canvas></div>')
    values_pos = page.index('id="gfCommandCursorCard"')
    assert chart_pos < values_pos
    assert "commandIds=['command_desired_target_w','command_readback_target_w','zendure_actual_power_w','grid_power_w']" in js
    assert "point?fmtValue(point.y,'W'):'—'" in js
    assert ".gf-command-values-head" in css
    assert "min-height:112px" in css
    assert "contain:layout" in css


def test_large_chart_tooltip_preserves_horizontal_flip_and_adds_smooth_vertical_follow():
    js = _read("static/graph_v14_1.js")
    css = _read("static/graph_v14_1.css")
    assert "hoverYRatio:null" in js
    assert "function chartYRatioFromPointer(chart,event)" in js
    assert "setHoverMsAt(ts,chartYRatioFromPointer(chart,event))" in js
    assert "function setHoverMs(ts)" in js
    assert "Number.isFinite(state.hoverYRatio)" in js
    assert "center=chart.chartArea.top+state.hoverYRatio*(chart.chartArea.bottom-chart.chartArea.top)" in js
    # Preserve the established X-axis side flip contract.
    assert "let left=x+gap,side='right'" in js
    assert "left=x-gap-width;side='left'" in js
    assert "top .10s ease-out" in css


def test_controller_logic_is_not_part_of_visual_followup_scope():
    # The actual byte-identity gate is performed against V15.0.1 during release validation.
    js = _read("static/graph_v14_1.js")
    assert "V15.0.2 graph interaction follow-up layer" in js
