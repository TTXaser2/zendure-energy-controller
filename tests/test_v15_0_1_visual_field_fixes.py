from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_state_detail_view_is_global_cursor_driven_and_no_longer_called_zeitlupe():
    js = _read("static/graph_v14_1.js")
    page = _read("graph_ui/page.py")
    assert "Zeitlupe" not in js
    assert "Zeitlupe" not in page
    assert "Detailausschnitt" in js
    assert "10-Minuten-Zoom um den Cursor" in js
    update = js.split("function updateCursorCards", 1)[1].split("function setSelectionMode", 1)[0]
    assert "renderStateMagnifier(actual)" in update
    hover = js.split("function bindStateHover", 1)[1].split("function setHoverMs", 1)[0]
    assert "renderStateMagnifier" not in hover
    assert "panel.hidden=true" not in hover


def test_state_parent_timeline_has_time_axis_and_synchronized_detail_window():
    js = _read("static/graph_v14_1.js")
    css = _read("static/graph_v14_1.css")
    assert "function stateAxisHtml(range)" in js
    assert "stateRows+commandRow+stateAxisHtml(range)" in js
    assert "data-gf-state-detail-window" in js
    assert ".gf-state-detail-window" in css
    assert ".gf-state-axis" in css


def test_state_reason_card_wraps_long_diagnostic_text():
    css = _read("static/graph_v14_1.css")
    assert ".gf-state-card .gf-cursor-row" in css
    assert "white-space:normal" in css
    assert "overflow-wrap:anywhere" in css


def test_comparison_value_panel_is_persistent_and_overlay_series_can_be_focused():
    js = _read("static/graph_v14_1.js")
    page = _read("graph_ui/page.py")
    css = _read("static/graph_v14_1.css")
    assert 'id="gfCompareHoverCard" class="gf-compare-hover-card"' in page
    assert 'id="gfCompareHoverCard" class="gf-compare-hover-card" hidden' not in page
    assert "function applyComparisonFocus()" in js
    assert "data-gf-compare-series" in js
    assert "dataset.borderWidth=focus?(match?2.6:.65)" in js
    assert "card.hidden=true" not in js.split("function renderCompareHoverCard", 1)[1].split("function bindComparisonCanvas", 1)[0]
    assert "display:block!important" in css


def test_command_follow_uses_fixed_values_panel_outside_mini_chart():
    js = _read("static/graph_v14_1.js")
    page = _read("graph_ui/page.py")
    assert 'id="gfCommandCursorCard" class="gf-command-values"' in page
    chart_fragment = page.split('class="gf-chart-wrap gf-chart-context"', 1)[1].split("</div>", 1)[0]
    assert "gfCommandCursorCard" not in chart_fragment
    command = js.split("function renderCommand", 1)[1].split("function triggerText", 1)[0]
    assert "renderCommandValues(ts)" in command
    assert "placeChartCard(card,current,ts" not in command


def test_calendar_navigation_steps_local_windows_without_duplicate_label():
    js = _read("static/graph_v14_1.js")
    page = _read("graph_ui/page.py")
    workspace = _read("graph_workspace.py")
    assert 'id="gfCalendarPrev"' in page
    assert 'id="gfCalendarNext"' in page
    assert "function shiftCalendarWindow(days)" in js
    assert "calendarOffsetDays" in js
    assert "nextOffset>0" in js
    assert "Vorgestern &amp; Gestern" in page
    assert '"label": "Vorgestern & Gestern"' in workspace
    assert "Letzte 2 Kalendertage" not in page


def test_toolbar_reserves_status_width_to_prevent_loading_layout_shift():
    css = _read("static/graph_v14_1.css")
    assert ".gf-toolbar-status{width:278px;min-width:278px;max-width:278px" in css
    assert "text-overflow:ellipsis" in css


def test_target_pipeline_uses_distinct_colors_dash_patterns_and_final_emphasis():
    js = _read("static/graph_v14_1.js")
    css = _read("static/graph_v14_1.css")
    for token in (
        "--gf-series-target-raw",
        "--gf-series-target-limited",
        "--gf-series-target-filtered",
        "--gf-series-target-step",
        "--gf-series-target-final",
    ):
        assert token in css
        assert token in js
    assert "target_raw_w:[2,3]" in js
    assert "target_limited_w:[9,4]" in js
    assert "target_filtered_w:[8,3,2,3]" in js
    assert "target_step_limited_w:[4,3]" in js
    assert "target_final_w:2.2" in js
    assert "stroke-dasharray" in js
