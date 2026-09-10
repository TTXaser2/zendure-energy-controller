import json
from pathlib import Path

from config_manager import ConfigManager, DEFAULT_CONFIG
from graph_query_service import GraphQueryService
from graph_workspace import (
    GUIDED_VIEWS,
    TERMS_DE,
    WORKSPACE_MAX_SELECTED_SERIES,
    WORKSPACE_MAX_WINDOW_MS,
    resolve_guided_views,
    workspace_manifest,
)
from state import ControllerState
from web_ui import build_graph_page, create_app


def _route_endpoint(app, path):
    for route in app.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint
    raise AssertionError(path)


def test_workspace_manifest_decorates_canonical_catalog_without_replacing_machine_ids():
    service = GraphQueryService(cache_max_entries=0)
    catalog = service.catalog()
    manifest = workspace_manifest(catalog)
    assert manifest["workspace_contract_version"] == 2
    assert manifest["query_contract"] == "graph_query_service_v1"
    assert manifest["max_window_ms"] == 48 * 60 * 60 * 1000
    assert manifest["max_selected_series"] == WORKSPACE_MAX_SELECTED_SERIES
    assert manifest["default_view_id"] == "energy_balance"
    assert len(manifest["catalog"]["series"]) == len(catalog["series"]) == 17
    assert len(manifest["catalog"]["entity_series"]) == len(catalog["entity_series"]) == 4
    original_ids = [x["series_id"] for x in catalog["series"]]
    decorated_ids = [x["series_id"] for x in manifest["catalog"]["series"]]
    assert decorated_ids == original_ids
    by_id = {x["series_id"]: x for x in manifest["catalog"]["series"]}
    assert by_id["grid_power_w"]["label"] == "Netzleistung"
    assert by_id["target_final_w"]["group"] == "control"


def test_guided_views_reference_only_canonical_series_and_keep_wp9_boundary():
    catalog = GraphQueryService(cache_max_entries=0).catalog()
    system_ids = {x["series_id"] for x in catalog["series"]}
    entity_ids = {x["series_id"] for x in catalog["entity_series"]}
    manifest = workspace_manifest(catalog)
    assert [x["view_id"] for x in GUIDED_VIEWS] == ["energy_balance", "storage", "control", "free"]
    for view in manifest["guided_views"]:
        assert set(view["system_series"]) <= system_ids
        assert set(view["entity_series"]) <= entity_ids
    storage = next(x for x in manifest["guided_views"] if x["view_id"] == "storage")
    assert storage["entity_policy"] == "physical_storage_units_if_present"
    assert storage["entity_series"] == ["power_w", "soc_percent"]
    # WP8/WP9 extend the same workspace without changing the canonical series IDs.
    assert manifest["capabilities"]["inspector"] == "available_wp8"
    assert manifest["capabilities"]["command_follow"] == "available_wp8"
    assert manifest["capabilities"]["episode_comparison"] == "available_wp9"


def test_terminology_is_central_and_machine_ids_are_not_used_as_german_labels():
    assert TERMS_DE["graph.view.free"] == "Freie Auswahl"
    assert TERMS_DE["graph.series.primary_soc_percent"] == "Primärspeicher SOC"
    assert TERMS_DE["graph.entity_series.power_w"] == "Leistung"
    assert all(key.startswith("graph.") for key in TERMS_DE)


def test_graph_page_is_v3_workspace_and_does_not_call_legacy_history_payload():
    root = Path(__file__).resolve().parents[1]
    html = build_graph_page({"UI_DARK_MODE": False})
    js = (root / "static" / "graph_v14_1.js").read_text(encoding="utf-8")
    for endpoint in (
        "/api/graph/v1/workspace",
        "/api/graph/v1/overview",
        "/api/graph/v1/coverage",
        "/api/graph/v1/evidence",
    ):
        assert endpoint in js
    assert "/graph-view-data" not in js
    assert "/graph-data.csv" not in js
    assert "/graph_old" not in html
    assert "/graph_old" not in js
    assert "Analyse-Workspace" in html
    assert "Freies Lagebild" in html
    assert 'data-greenfield-contract="v14.1.4"' in html
    assert "/static/graph_v14_1.css" in html
    assert "/static/graph_v14_1.js" in html


def test_graph_page_exposes_graceful_evidence_and_wp8_wp9_tools():
    html = build_graph_page({})
    assert "Datenqualität" in html
    assert "Measurement V4 ist keine Laufzeitvoraussetzung" in html
    assert "Regler-Inspector" in html
    assert "Command-Follow" in html
    assert "Episoden t=0" in html
    assert 'id="gfComparisonArea"' in html
    assert "physical_storage_units_if_present" in Path(__file__).resolve().parents[1].joinpath("graph_workspace.py").read_text(encoding="utf-8")
    assert "episode_comparison" in Path(__file__).resolve().parents[1].joinpath("graph_workspace.py").read_text(encoding="utf-8")


def test_workspace_route_is_available_even_when_history_is_missing_and_does_not_gate_control(tmp_path):
    cfg = dict(DEFAULT_CONFIG)
    cfg["MEASUREMENT_DB_ENABLED"] = True
    cfg["MEASUREMENT_DB_PATH"] = str(tmp_path / "missing.sqlite3")
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    manager = ConfigManager(str(cfg_path))
    manager.load()
    app = create_app(manager, ControllerState())
    endpoint = _route_endpoint(app, "/api/graph/v1/workspace")
    payload = endpoint()
    assert payload["workspace_contract_version"] == 2
    assert payload["runtime"]["read_mode"] == "UNAVAILABLE"
    assert payload["runtime"]["control_readiness_impact"] == "NONE"
    assert payload["runtime"]["measurement_v4_required"] is False
    assert payload["runtime"]["workspace_ready"] is False


def test_workspace_hard_limit_matches_query_service_limit():
    assert WORKSPACE_MAX_WINDOW_MS == 48 * 60 * 60 * 1000
    assert WORKSPACE_MAX_WINDOW_MS > 24 * 60 * 60 * 1000


def test_topology_resolution_uses_only_real_physical_units_and_caps_guided_view_at_two():
    base = workspace_manifest(GraphQueryService(cache_max_entries=0).catalog())["guided_views"]
    entities = [
        {"stable_id": "storage:controlled", "entity_type": "ZENDURE_STORAGE", "last_seen_ms": 5000, "available_series": ["power_w", "soc_percent"]},
        {"stable_id": "storage:primary", "entity_type": "PRIMARY_STORAGE", "last_seen_ms": 5000, "available_series": ["power_w", "soc_percent"]},
        {"stable_id": "unit:a", "entity_type": "ZENDURE_UNIT", "last_seen_ms": 3000, "source_identity": "A", "available_series": ["power_w", "soc_percent", "target_w"]},
        {"stable_id": "unit:b", "entity_type": "ZENDURE_UNIT", "last_seen_ms": 5000, "source_identity": "B", "available_series": ["power_w", "soc_percent"]},
        {"stable_id": "unit:c", "entity_type": "ZENDURE_UNIT", "last_seen_ms": 4000, "source_identity": "C", "available_series": ["power_w", "soc_percent"]},
    ]
    resolved = resolve_guided_views(base, entities)
    storage = next(x for x in resolved if x["view_id"] == "storage")
    assert storage["resolved_entity_series"] == [
        {"stable_id": "unit:b", "series_id": "power_w"},
        {"stable_id": "unit:b", "series_id": "soc_percent"},
        {"stable_id": "unit:c", "series_id": "power_w"},
        {"stable_id": "unit:c", "series_id": "soc_percent"},
    ]
    assert all(not x["stable_id"].startswith("storage:") for x in storage["resolved_entity_series"])


def test_topology_resolution_gracefully_handles_zendure_only_without_physical_unit_rows():
    base = workspace_manifest(GraphQueryService(cache_max_entries=0).catalog())["guided_views"]
    resolved = resolve_guided_views(base, [{
        "stable_id": "storage:controlled",
        "entity_type": "ZENDURE_STORAGE",
        "available_series": ["power_w", "soc_percent"],
    }])
    storage = next(x for x in resolved if x["view_id"] == "storage")
    assert storage["resolved_entity_series"] == []


def test_workspace_route_resolves_two_real_physical_units_from_v3(tmp_path):
    from tests.test_v14_graph_entities_wp4 import _physical_units, _row, _v3

    start = 1_783_100_000_000
    db = _v3(tmp_path, [
        _row(start, unit_count=2, units=_physical_units(start, include_b=True), primary=True),
        _row(start + 3000, seq=2, unit_count=2, units=_physical_units(start + 3000, include_b=True), primary=True),
    ])
    cfg = dict(DEFAULT_CONFIG)
    cfg["MEASUREMENT_DB_ENABLED"] = True
    cfg["MEASUREMENT_DB_PATH"] = str(db)
    cfg_path = tmp_path / "config-v3.json"
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    manager = ConfigManager(str(cfg_path))
    manager.load()
    app = create_app(manager, ControllerState())
    payload = _route_endpoint(app, "/api/graph/v1/workspace")()
    assert payload["runtime"]["read_mode"] == "V3_NATIVE"
    assert payload["runtime"]["workspace_ready"] is True
    by_type = {}
    for entity in payload["entities"]:
        by_type.setdefault(entity["entity_type"], []).append(entity)
    assert len(by_type.get("ZENDURE_UNIT", [])) == 2
    storage = next(x for x in payload["guided_views"] if x["view_id"] == "storage")
    resolved = storage["resolved_entity_series"]
    assert len(resolved) == 4
    assert {x["series_id"] for x in resolved} == {"power_w", "soc_percent"}
    assert all(x["stable_id"] not in {"storage:controlled", "storage:primary"} for x in resolved)
    primary = next(x for x in payload["entities"] if x["stable_id"] == "storage:primary")
    assert primary["display_name"] == "Hausspeicher"
