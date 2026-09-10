from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_greenfield_contract_and_lane_layout_controls():
    page = text("graph_ui/page.py")
    js = text("static/graph_v14_1.js")
    assert 'data-greenfield-contract="v14.1.4"' in page
    for lane in ("power", "soc", "state", "comparison"):
        assert f'data-gf-lane="{lane}"' in page
    assert "data-gf-lane-toggle" in page
    assert "data-gf-lane-move" in page
    assert "zec:graph:v14.1.3:layout:" in js
    assert "localStorage.setItem" in js
    assert "applyLaneLayout" in js
    assert "moveLane" in js
    assert "toggleLane" in js


def test_workspace_presets_have_distinct_titles_and_default_orders():
    js = text("static/graph_v14_1.js")
    assert "Speicher-SOC & historische Grenzen" in js
    assert "Speicherleistungen" in js
    assert "Zielwertpipeline & Netzreaktion" in js
    assert "Regelzustände & Ereignisse" in js
    assert "order:['soc','power','state','comparison']" in js
    assert "order:['power','state','soc','comparison']" in js
    assert "resetInspectorContext()" in js


def test_busy_feedback_and_free_series_debounce_are_explicit():
    page = text("graph_ui/page.py")
    js = text("static/graph_v14_1.js")
    css = text("static/graph_v14_1.css")
    assert "gfBusyBadge" in page
    assert "gf-lane-busy" in page
    assert "Datenreihen werden geladen" in js
    assert "scheduleFreeReload" in js
    # V14.1.4 keeps the explicit debounce/busy contract but upgrades the old
    # full-workspace reload to an incremental series reload.
    assert "state.freeReloadTimer=setTimeout(()=>{state.freeReloadTimer=null;reloadFreeSelection();},250)" in js
    assert "async function reloadFreeSelection" in js
    assert ".gf-spinner" in css
    assert ".gf-lane.is-loading" in css


def test_state_lane_has_command_row_and_hover_magnifier_outside_tracks():
    page = text("graph_ui/page.py")
    js = text("static/graph_v14_1.js")
    css = text("static/graph_v14_1.css")
    assert "gfStateMagnifier" in page
    assert "gfStateHoverPanel" in page
    assert ">Commands</div>" in js
    assert "renderStateMagnifier" in js
    assert "5*60000" in js
    assert ".gf-state-hover-panel" in css
    assert ".gf-state-card{position:relative!important" in css


def test_command_follow_has_info_legend_hover_and_publish_marker():
    page = text("graph_ui/page.py")
    js = text("static/graph_v14_1.js")
    assert 'data-gf-info="command"' in page
    assert "gfCommandLegend" in page
    assert "gfCommandCursorCard" in page
    assert "renderLegend('#gfCommandLegend',datasets)" in js
    assert "$gfPublishMs" in js
    assert "gfLocalCursor" in js
    assert "gfCommandHoverBound" in js


def test_quality_groups_common_evidence_gaps_once():
    page = text("graph_ui/page.py")
    js = text("static/graph_v14_1.js")
    assert "gfQualitySummary" in page
    assert "function evidenceGroups" in js
    assert "1 gemeinsame Datenlücke" in js
    assert "betrifft ${group.series.length}/${ids.length} Reihen" in js
    assert "data-gf-open-quality" in js


def test_period_and_episode_comparison_share_hover_and_episode_zero_axis():
    page = text("graph_ui/page.py")
    js = text("static/graph_v14_1.js")
    assert "gfCompareHoverCard" in page
    assert "gfCompareCursor" in js
    assert "compareHoverRelMs" in js
    assert "renderCompareHoverCard" in js
    assert "Δ A−B" in js
    assert "t=0" in js
    assert "timeline:'relative'" in js
    # Episodes remain on their real -before ... 0 ... +after relative axis.
    assert "episodes?{start:Math.min(a.range.start,b.range.start),end:Math.max(a.range.end,b.range.end)}" in js
    assert "Number(value)===0?'t=0'" in js


def test_episode_trigger_selection_is_guided_and_filterable():
    page = text("graph_ui/page.py")
    js = text("static/graph_v14_1.js")
    assert "gfTriggerSearch" in page
    assert "gfTriggerKindFilter" in page
    assert "gfSimilarTriggerB" in page
    assert "Ereignisreaktionen vergleichen" in page
    assert "chooseSimilarTriggerB" in js
    assert "triggerSignature" in js
    assert "filteredTriggers" in js


def test_inspector_density_and_wider_workspace_are_css_contracts():
    css = text("static/graph_v14_1.css")
    assert "max-width:2020px" in css
    assert ".gf-chart-large{height:292px}" in css
    assert ".gf-chart-medium{height:190px}" in css
    assert ".gf-kv-list{display:grid;gap:1px}" in css
    assert "#gfInspectorCommandLink{position:sticky" in css


def test_settings_dark_mode_normalizes_legacy_controls_to_semantic_tokens():
    css = text("static/settings_v2.css")
    assert "V14.1.3: complete Settings-V2 dark-theme normalization" in css
    assert 'html[data-theme="dark"] body.zec-settings-v2' in css
    assert "--panel:var(--zec-card-bg,#0d1929)" in css
    assert ".config-state-grid input" in css
    assert ".modal," in css
    assert ".search-drawer" in css
    assert "color-scheme:dark" in css
