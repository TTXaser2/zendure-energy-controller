from pathlib import Path

from config_manager import DEFAULT_CONFIG
from web_ui import build_graph_page

ROOT = Path(__file__).resolve().parents[1]
GRAPH_JS = ROOT / "static" / "graph_v14_1.js"
GRAPH_CSS = ROOT / "static" / "graph_v14_1.css"
STATUS_JS = ROOT / "static" / "status_v2.js"


def test_greenfield_graph_page_is_separate_from_legacy_presentation():
    html = build_graph_page({**DEFAULT_CONFIG, "UI_DARK_MODE": False})
    source = (ROOT / "web_ui.py").read_text(encoding="utf-8")
    js = GRAPH_JS.read_text(encoding="utf-8")
    assert 'data-greenfield-contract="v14.1.2"' in html
    assert '/static/graph_v14_1.css' in html
    assert '/static/graph_v14_1.js' in html
    assert 'Analyse-Workspace' in html
    assert 'Graph / Live-Verlauf' not in html
    assert '/graph_old' not in html
    assert '@app.get("/graph_old"' not in source
    assert 'def build_graph_page_legacy' not in source
    assert '/graph-view-data' not in js
    assert '/graph_old' not in js


def test_graph_theme_follows_global_light_and_dark_modes_without_force_override():
    light = build_graph_page({**DEFAULT_CONFIG, "UI_DARK_MODE": False})
    dark = build_graph_page({**DEFAULT_CONFIG, "UI_DARK_MODE": True})
    source = (ROOT / "web_ui.py").read_text(encoding="utf-8")
    css = GRAPH_CSS.read_text(encoding="utf-8")
    assert 'data-theme="light"' in light
    assert 'data-theme="dark"' in dark
    assert 'force_dark=True' not in source[source.index('def build_graph_page'):source.index('def build_footer')]
    assert 'html[data-theme="dark"] .gf-page' in css
    assert '--gf-panel:' in css
    assert '--gf-text:' in css


def test_desktop_information_architecture_is_three_column_with_synchronized_lanes():
    html = build_graph_page(dict(DEFAULT_CONFIG))
    css = GRAPH_CSS.read_text(encoding="utf-8")
    js = GRAPH_JS.read_text(encoding="utf-8")
    assert 'class="gf-three-column"' in html
    assert 'grid-template-columns:280px minmax(640px,1fr) 360px' in css
    assert 'id="gfPowerChart"' in html
    assert 'id="gfSocChart"' in html
    assert 'id="gfStateTimeline"' in html
    assert 'Leistungsfluss &amp; Regelziel' in html
    assert 'SOC &amp; historische Grenzen' in html
    assert 'Zustände &amp; Ereignisse' in html
    assert 'selectCursor' in js
    assert 'syncPlugin' in js
    assert 'gfPowerCursorCard' in html
    assert 'gfSocCursorCard' in html
    assert 'gfStateCursorCard' in html


def test_graph_uses_only_v3_query_contracts_and_keeps_advanced_analysis_tools():
    js = GRAPH_JS.read_text(encoding="utf-8")
    for endpoint in (
        '/api/graph/v1/workspace',
        '/api/graph/v1/overview',
        '/api/graph/v1/coverage',
        '/api/graph/v1/evidence',
        '/api/graph/v1/inspector',
        '/api/graph/v1/command-follow',
        '/api/graph/v1/episode-triggers',
        '/api/graph/v1/episode-comparison',
    ):
        assert endpoint in js
    assert '/graph-view-data' not in js
    assert '/storage-soc-day-data' not in js


def test_graph_lines_are_thin_but_keep_generous_pointer_hit_target():
    js = GRAPH_JS.read_text(encoding="utf-8")
    assert "?1.1:1.35" in js
    assert 'pointHitRadius:14' in js
    assert 'pointRadius:0' in js


def test_mobile_context_is_a_bottom_sheet_not_a_permanent_side_column():
    css = GRAPH_CSS.read_text(encoding="utf-8")
    html = build_graph_page(dict(DEFAULT_CONFIG))
    assert '@media(max-width:760px)' in css
    assert '.gf-context-panel{display:none;position:fixed' in css
    assert '.gf-context-panel.is-open{display:block}' in css
    assert 'id="gfMobileContextButton"' in html


def test_graph_request_coalescing_prevents_parallel_workspace_reload_storms():
    js = GRAPH_JS.read_text(encoding="utf-8")
    assert 'loading:false,reloadPending:false' in js
    assert 'if(state.loading){state.reloadPending=true;return;}' in js
    assert 'if(state.reloadPending){state.reloadPending=false;queueMicrotask(()=>loadAll(true));}' in js
    assert 'timeoutMs=30000' in js


def test_historical_soc_day_request_clears_stale_chart_and_validates_returned_date():
    js = STATUS_JS.read_text(encoding="utf-8")
    assert 'let dayController=null; let dayRequestSequence=0;' in js
    assert 'if(dayController)dayController.abort();' in js
    assert 'controller.abort(),30000' in js
    assert 'socChart.clear(requestedDate);' in js
    assert 'SOC_DAY_DATE_MISMATCH' in js
    assert 'requestId!==dayRequestSequence' in js
    assert 'dayInFlight' not in js


def test_soc_day_chart_clear_hides_old_tooltip_and_old_points():
    js = STATUS_JS.read_text(encoding="utf-8")
    assert "clear(date='')" in js
    assert 'this.hoverX=null' in js
    assert 'this.tooltip.hidden=true' in js
    assert 'points:[]' in js
