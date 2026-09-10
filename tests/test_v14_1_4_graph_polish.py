from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_calendar_day_presets_are_distinct_from_rolling_windows():
    page = (ROOT / "graph_ui/page.py").read_text(encoding="utf-8")
    js = (ROOT / "static/graph_v14_1.js").read_text(encoding="utf-8")
    workspace = (ROOT / "graph_workspace.py").read_text(encoding="utf-8")
    for token in ("Rollierend", "Kalendertage", 'data-gf-calendar-preset="today"', 'data-gf-calendar-preset="yesterday"', 'data-gf-calendar-preset="today_yesterday"', 'data-gf-calendar-preset="last_two_complete_days"'):
        assert token in page
    assert "function calendarRange(id)" in js
    assert "state.calendarPreset" in js
    assert '"calendar_presets"' in workspace
    assert "LOCAL_TWO_COMPLETE_DAYS_BEFORE_TODAY" in workspace


def test_cursor_cards_flip_to_left_instead_of_clamping_over_analysis_point():
    js = (ROOT / "static/graph_v14_1.js").read_text(encoding="utf-8")
    body = js.split("function placeChartCard", 1)[1].split("function updateCursorCards", 1)[0]
    assert "left=x-gap-width" in body
    assert "card.dataset.gfSide=side" in body
    assert "left=x+gap" in body
    command = js.split("function renderCommand", 1)[1].split("function triggerText", 1)[0]
    assert "placeChartCard(card,current,ts" in command
    assert "current.width-250" not in command


def test_inspector_pipeline_is_a_real_visual_chain_with_deltas_and_collapsible_details():
    page = (ROOT / "graph_ui/page.py").read_text(encoding="utf-8")
    js = (ROOT / "static/graph_v14_1.js").read_text(encoding="utf-8")
    css = (ROOT / "static/graph_v14_1.css").read_text(encoding="utf-8")
    assert 'id="gfInspectorPipeline" class="gf-pipeline"' in page
    assert '<details class="gf-inspector-section gf-inspector-details">' in page
    assert "function pipelineHtml(values)" in js
    assert "target_step_limited_w" in js
    assert "command_readback_target_w" in js
    assert "Δ ${fmtValue(delta,unit(id))}" in js
    assert ".gf-pipeline-step:not(:last-child)::after" in css


def test_free_selection_incrementally_loads_only_new_series_when_timeline_matches():
    js = (ROOT / "static/graph_v14_1.js").read_text(encoding="utf-8")
    body = js.split("async function reloadFreeSelection", 1)[1].split("function scheduleFreeReload", 1)[0]
    assert "added=ids.filter" in body
    assert "series:added.join(',')" in body
    assert "include_context:'false'" in body
    assert "sameTimeline" in body
    assert "inkrementell +${added.length}" in body


def test_comparison_hover_marks_points_and_whole_calendar_day_uses_clock_ticks():
    js = (ROOT / "static/graph_v14_1.js").read_text(encoding="utf-8")
    compare_plugin = js.split("const compareCursorPlugin", 1)[1].split("const localCursorPlugin", 1)[0]
    assert "nearestDatasetPoint(dataset,value)" in compare_plugin
    assert "ctx.arc(x,y,3" in compare_plugin
    assert "function isSingleWholeCalendarDay" in js
    assert "stepSize=6*3600000" in js
    assert "'24:00'" in js


def test_state_magnifier_keeps_exact_center_marker_and_quality_names_affected_series():
    js = (ROOT / "static/graph_v14_1.js").read_text(encoding="utf-8")
    css = (ROOT / "static/graph_v14_1.css").read_text(encoding="utf-8")
    assert "gf-mini-center" in js
    assert ".gf-mini-center" in css
    assert "betroffen: ${esc(group.series.map(label).join(', '))}" in js


def test_guided_view_switch_sets_busy_state_before_loading():
    js = (ROOT / "static/graph_v14_1.js").read_text(encoding="utf-8")
    listener = js.split("qa('[data-gf-investigation]')", 2)[-1]
    assert "setBusy(true,state.pendingLabel)" in listener
