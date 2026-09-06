from pathlib import Path

from config_manager import DEFAULT_CONFIG
from web_ui import build_graph_page

ROOT = Path(__file__).resolve().parents[1]
GRAPH_JS = (ROOT / "static" / "graph_v14_1.js").read_text(encoding="utf-8")
GRAPH_CSS = (ROOT / "static" / "graph_v14_1.css").read_text(encoding="utf-8")


def _html():
    return build_graph_page({**DEFAULT_CONFIG, "UI_DARK_MODE": False})


def test_v1412_header_is_compact_toolbar_with_on_demand_custom_range():
    html = _html()
    assert 'class="gf-analysis-toolbar"' in html
    assert 'id="gfCustomToggle"' in html
    assert 'id="gfCustomRange" hidden' in html
    assert 'id="gfRefresh"' in html
    assert '.gf-analysis-toolbar{display:grid' in GRAPH_CSS
    assert 'padding:11px 14px' in GRAPH_CSS
    assert 'gf-investigation-bar' not in html


def test_v1412_right_context_contains_only_inspector_command_and_data():
    html = _html()
    assert 'data-gf-context-tab="inspector"' in html
    assert 'data-gf-context-tab="command"' in html
    assert 'data-gf-context-tab="quality"' in html
    assert 'data-gf-context-tab="compare"' not in html
    assert 'grid-template-columns:repeat(3,1fr)' in GRAPH_CSS


def test_v1412_period_and_episode_comparisons_share_bottom_analysis_lane():
    html = _html()
    assert 'id="gfComparisonArea"' in html
    assert 'id="gfComparePeriodsMode"' in html
    assert 'id="gfCompareEpisodesMode"' in html
    assert 'id="gfPeriodAFrom"' in html and 'id="gfPeriodATo"' in html
    assert 'id="gfPeriodBFrom"' in html and 'id="gfPeriodBTo"' in html
    assert 'id="gfPeriodPreviousDay"' in html
    assert 'id="gfTriggerA"' in html and 'id="gfTriggerB"' in html
    assert 'id="gfLoadPeriodComparison"' in html
    assert 'id="gfLoadEpisodeComparison"' in html
    assert 'DAY_MS = 24 * 60 * 60 * 1000' in GRAPH_JS
    assert 'loadPeriodComparison' in GRAPH_JS
    assert 'loadEpisodeComparison' in GRAPH_JS


def test_v1412_period_comparison_supports_side_by_side_and_relative_overlay():
    html = _html()
    for canvas_id in (
        'gfComparePowerA', 'gfCompareSocA', 'gfComparePowerB', 'gfCompareSocB',
        'gfComparePowerOverlay', 'gfCompareSocOverlay',
    ):
        assert f'id="{canvas_id}"' in html
    assert "comparisonMode:'side'" in GRAPH_JS
    assert "setComparisonDisplay('overlay')" in GRAPH_JS
    assert "domain==='relative'?raw.map" in GRAPH_JS
    assert "timeline:'relative'" in GRAPH_JS
    assert "tag:'A'" in GRAPH_JS and "tag:'B'" in GRAPH_JS


def test_v1412_episode_frontend_consumes_wp9_overview_contract_not_old_timeline_shape():
    assert 'episodeA.overview.relative_timestamps_ms' in GRAPH_JS
    assert 'episodeB.overview.relative_timestamps_ms' in GRAPH_JS
    assert 'episodeA.overview,timestamps_ms' in GRAPH_JS
    assert 'ep.timeline?.relative_ms' not in GRAPH_JS
    assert 'ep.timeline?.series' not in GRAPH_JS


def test_v1412_range_selection_is_persistent_and_separate_from_zoom():
    html = _html()
    assert 'id="gfSelectMode"' in html
    assert 'id="gfSelectionBar" hidden' in html
    assert 'id="gfZoomSelection"' in html
    assert 'id="gfCompareSelection"' in html
    assert 'id="gfClearSelection"' in html
    assert 'selection:null,selectionDraft:null,selectionMode:false' in GRAPH_JS
    assert 'function zoomSelection()' in GRAPH_JS
    assert 'function compareSelection()' in GRAPH_JS
    assert 'state.selection={start:' in GRAPH_JS
    assert 'state.selection=null' in GRAPH_JS
    assert 'zoomSelection(){if(!state.selection)return;setCustomRange(state.selection.start,state.selection.end' in GRAPH_JS


def test_v1412_synchronized_hover_cursor_drives_all_main_lanes_and_uses_custom_cards():
    html = _html()
    assert 'id="gfPowerCursorCard"' in html
    assert 'id="gfSocCursorCard"' in html
    assert 'id="gfStateCursorCard"' in html
    assert 'hoverMs:null' in GRAPH_JS
    assert 'function activeCursorMs()' in GRAPH_JS
    assert 'function setHoverMs(ts)' in GRAPH_JS
    assert 'redrawSynchronizedOverlays' in GRAPH_JS
    assert 'updateCursorCards' in GRAPH_JS
    assert 'updateStateOverlays' in GRAPH_JS
    assert "tooltip:{enabled:false}" in GRAPH_JS
    assert '.gf-cursor-card' in GRAPH_CSS
    assert 'transition:opacity .12s ease,transform .12s ease,left .06s linear' in GRAPH_CSS


def test_v1412_selection_overlay_is_synchronized_across_power_soc_and_state():
    assert 'gfSyncOverlay' in GRAPH_JS
    assert 'state.selectionDraft||state.selection' in GRAPH_JS
    assert 'gf-state-selection' in GRAPH_JS
    assert '--gf-selection-fill' in GRAPH_CSS
    assert '.gf-state-selection' in GRAPH_CSS


def test_v1412_data_quality_consumes_evidence_segment_arrays_and_distinguishes_causes():
    assert 'Array.isArray(value)?value:[]' in GRAPH_JS
    for status in ('GAP', 'NOT_INSTRUMENTED', 'PURGED_BY_RETENTION', 'AVAILABLE'):
        assert status in GRAPH_JS
    assert 'kein Evidenznachweis' in GRAPH_JS
    assert 'Lücke ${fmtDuration' in GRAPH_JS
    assert 'nicht instrumentiert ${fmtDuration' in GRAPH_JS
    assert 'Retention ${fmtDuration' in GRAPH_JS


def test_v1412_info_circle_help_is_available_for_advanced_analysis_concepts():
    html = _html()
    assert html.count('class="gf-info"') >= 5
    assert 'id="gfInfoPopover"' in html
    for key in ('workspace', 'cursor', 'selection', 'states', 'comparison', 'evidence'):
        assert f"{key}:" in GRAPH_JS
    assert '.gf-info-popover' in GRAPH_CSS


def test_v1412_main_charts_keep_thin_lines_and_large_hit_target_without_native_tooltips():
    assert 'function lineWidth(){return matchMedia' in GRAPH_JS
    assert '?1.1:1.35' in GRAPH_JS
    assert 'pointHitRadius:14' in GRAPH_JS
    assert 'pointRadius:0' in GRAPH_JS
    assert 'tooltip:{enabled:false}' in GRAPH_JS
