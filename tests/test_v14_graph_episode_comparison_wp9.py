import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from config_manager import ConfigManager, DEFAULT_CONFIG
from graph_query_service import GraphQueryError, GraphQueryService
from graph_workspace import workspace_manifest
from state import ControllerState
from web_ui import build_graph_page, create_app
from tests.test_v14_graph_query_service_wp3 import _row, _v3

EXPECTED_CONTROLLER_SHA256 = "56f854bbe5bbecc9a7ce305af3915bd461615cc425e444b0c3e427c38e4184b1"


def _route_endpoint(app, path):
    for route in app.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint
    raise AssertionError(path)


def _published_triggers(service, db, start, end):
    payload = service.episode_triggers(str(db), start, end)
    return [x for x in payload["items"] if x["trigger_type"] == "PUBLISHED_EVENT"]


def test_wp9_manifest_exposes_pair_only_comparison_and_keeps_causality_guard():
    manifest = workspace_manifest(GraphQueryService(cache_max_entries=0).catalog())
    cfg = manifest["episode_comparison"]
    assert manifest["workspace_contract_version"] == 2
    assert manifest["capabilities"]["episode_comparison"] == "available_wp9"
    assert manifest["capabilities"]["side_by_side"] is True
    assert manifest["capabilities"]["overlay_pair_only"] is True
    assert manifest["capabilities"]["synchronized_cursor"] is True
    assert cfg["contract_version"] == 1
    assert cfg["max_episode_count"] == 2
    assert cfg["allowed_trigger_sources"] == ["PUBLISHED_EVENT", "INTERVAL_START"]
    assert cfg["allowed_interval_kinds"] == ["OPERATING_MODE", "CONTROL_INTENT", "CONTROL_REASON"]
    assert cfg["visual_similarity_is_causality_proof"] is False


def test_episode_triggers_are_only_persisted_publish_or_allowed_interval_starts(tmp_path):
    start = 1_785_000_000_000
    db = _v3(tmp_path, [
        _row(start, seq=1, pub=101, target=200),
        {**_row(start + 3000, seq=2, pub=102, target=300), "target_final_reason": "SMA_FULL_OR_IDLE"},
    ])
    service = GraphQueryService(cache_max_entries=0)
    payload = service.episode_triggers(str(db), start - 1, start + 10_000)
    assert payload["contract_version"] == 1
    assert payload["items"]
    assert {x["trigger_type"] for x in payload["items"]} <= {"PUBLISHED_EVENT", "INTERVAL_START"}
    assert all(x["trigger_id"].startswith(("event:", "interval:")) for x in payload["items"])
    interval_kinds = {x.get("interval_kind") for x in payload["items"] if x["trigger_type"] == "INTERVAL_START"}
    assert interval_kinds <= {"OPERATING_MODE", "CONTROL_INTENT", "CONTROL_REASON"}
    published = [x for x in payload["items"] if x["trigger_type"] == "PUBLISHED_EVENT"]
    assert [x["publish_event_id"] for x in published] == [101, 102]


def test_episode_comparison_aligns_two_persisted_triggers_to_relative_t0_and_retains_absolute_time(tmp_path):
    start = 1_785_010_000_000
    second = start + 60 * 60_000
    db = _v3(tmp_path, [
        _row(start - 3000, seq=1, pub=201, target=100, grid=300),
        _row(start, seq=2, pub=202, target=200, grid=200),
        _row(start + 3000, seq=3, pub=202, target=250, grid=100),
        _row(second - 3000, seq=4, pub=301, target=400, grid=500),
        _row(second, seq=5, pub=302, target=500, grid=400),
        _row(second + 3000, seq=6, pub=302, target=550, grid=300),
    ])
    service = GraphQueryService(cache_max_entries=0)
    triggers = _published_triggers(service, db, start - 5000, second + 5000)
    a = next(x for x in triggers if x["trigger_ms"] == start)
    b = next(x for x in triggers if x["trigger_ms"] == second)
    payload = service.episode_comparison(
        str(db), a["trigger_id"], b["trigger_id"], before_ms=3000, after_ms=3000,
        series_ids=["grid_power_w", "target_final_w"], resolution="highres",
    )
    assert payload["contract_version"] == 1
    assert payload["alignment"]["axis"] == "RELATIVE_T0_MS"
    assert payload["alignment"]["absolute_time_retained"] is True
    assert payload["alignment"]["visual_similarity_is_causality_proof"] is False
    ep_a, ep_b = payload["episodes"]["a"], payload["episodes"]["b"]
    assert ep_a["window"]["t0_ms"] == start
    assert ep_b["window"]["t0_ms"] == second
    assert 0 in ep_a["overview"]["relative_timestamps_ms"]
    assert 0 in ep_b["overview"]["relative_timestamps_ms"]
    assert ep_a["overview"]["timestamps_ms"] != ep_b["overview"]["timestamps_ms"]
    assert ep_a["overview"]["relative_timestamps_ms"] == ep_b["overview"]["relative_timestamps_ms"]
    assert ep_a["overview"]["series"]["target_final_w"] != ep_b["overview"]["series"]["target_final_w"]


def test_episode_comparison_reports_window_coverage_and_evidence_separately_per_episode(tmp_path):
    start = 1_785_020_000_000
    second = start + 60_000
    row_a = _row(start, seq=1, pub=401, target=200)
    row_b = _row(second, seq=2, pub=402, target=300)
    row_b["pv_power_w"] = None
    row_b["pv_power_valid"] = False
    db = _v3(tmp_path, [row_a, row_b])
    service = GraphQueryService(cache_max_entries=0)
    triggers = _published_triggers(service, db, start - 1, second + 1)
    payload = service.episode_comparison(
        str(db), triggers[0]["trigger_id"], triggers[1]["trigger_id"], before_ms=0, after_ms=1000,
        series_ids=["grid_power_w", "pv_power_w"], resolution="highres",
    )
    a = payload["episodes"]["a"]
    b = payload["episodes"]["b"]
    assert a["window_coverage"]["system"]["grid_power_w"]["status"] == "AVAILABLE"
    assert a["window_coverage"]["system"]["pv_power_w"]["status"] in {"NO_DATA", "AVAILABLE", "PARTIAL"}
    assert b["window_coverage"]["system"]["pv_power_w"]["status"] == "NO_DATA"
    assert a["evidence"] is not b["evidence"]
    assert a["evidence"]["from_ms"] != b["evidence"]["from_ms"]
    assert payload["meta"]["missing_series_are_not_imputed"] is True


def test_episode_comparison_does_not_invent_entities_missing_from_one_episode(tmp_path):
    from tests.test_v14_graph_entities_wp4 import _physical_units, _row as entity_row, _v3 as entity_v3

    start = 1_785_030_000_000
    second = start + 60_000
    rows = [
        entity_row(start, unit_count=1, units=_physical_units(start, include_b=False), primary=True),
        entity_row(second, seq=2, unit_count=2, units=_physical_units(second, include_b=True), primary=True),
    ]
    # Ensure distinct publish ids so both timestamps are persisted trigger candidates.
    rows[0]["command_publish_event_id"] = 501
    rows[1]["command_publish_event_id"] = 502
    db = entity_v3(tmp_path, rows)
    service = GraphQueryService(cache_max_entries=0)
    triggers = _published_triggers(service, db, start - 1, second + 1)
    entities = service.entities(str(db))["entities"]
    units = [x for x in entities if x["entity_type"] == "ZENDURE_UNIT"]
    assert len(units) == 2
    stable_ids = [x["stable_id"] for x in units]
    payload = service.episode_comparison(
        str(db), triggers[0]["trigger_id"], triggers[1]["trigger_id"], before_ms=0, after_ms=1000,
        series_ids=["grid_power_w"], stable_ids=stable_ids, entity_series_ids=["power_w"], resolution="highres",
    )
    a_entities = payload["episodes"]["a"]["entities"]["entities"]
    b_entities = payload["episodes"]["b"]["entities"]["entities"]
    assert set(a_entities) == set(stable_ids) == set(b_entities)
    # The unit that did not yet have a point in episode A remains a real catalog entity but has no fabricated sample.
    no_data_a = [sid for sid in stable_ids if payload["episodes"]["a"]["window_coverage"]["entities"][sid]["power_w"]["status"] == "NO_DATA"]
    assert no_data_a
    assert all(not a_entities[sid]["timestamps_ms"] for sid in no_data_a)
    assert payload["meta"]["missing_entities_are_not_invented"] is True


def test_episode_comparison_rejects_same_or_non_persisted_trigger(tmp_path):
    start = 1_785_040_000_000
    db = _v3(tmp_path, [_row(start, pub=601)])
    service = GraphQueryService(cache_max_entries=0)
    trigger = _published_triggers(service, db, start - 1, start + 1)[0]["trigger_id"]
    with pytest.raises(GraphQueryError, match="EPISODES_MUST_DIFFER"):
        service.episode_comparison(str(db), trigger, trigger, before_ms=0, after_ms=1000)
    with pytest.raises(GraphQueryError, match="EPISODE_TRIGGER_NOT_FOUND"):
        service.episode_comparison(str(db), trigger, "event:999999", before_ms=0, after_ms=1000)


def test_episode_trigger_rejects_non_allowed_interval_kind(tmp_path):
    start = 1_785_050_000_000
    db = _v3(tmp_path, [_row(start, pub=701)])
    conn = sqlite3.connect(db)
    try:
        cur = conn.execute(
            "INSERT INTO graph_intervals(kind,run_id,entity_id,start_ms,end_ms,value_code,source,quality) VALUES(?,?,?,?,?,?,?,?)",
            ("COMMAND_EFFECT", None, None, start, start + 1000, "COMMAND_PENDING", "TEST", "OBSERVED"),
        )
        bad_id = int(cur.lastrowid)
        conn.commit()
    finally:
        conn.close()
    service = GraphQueryService(cache_max_entries=0)
    good = _published_triggers(service, db, start - 1, start + 1)[0]["trigger_id"]
    with pytest.raises(GraphQueryError, match="EPISODE_TRIGGER_INTERVAL_KIND_NOT_ALLOWED"):
        service.episode_comparison(str(db), good, f"interval:{bad_id}", before_ms=0, after_ms=1000)


def test_wp9_routes_bind_to_v3_episode_contract(tmp_path):
    start = 1_785_060_000_000
    second = start + 3000
    db = _v3(tmp_path, [_row(start, seq=1, pub=801), _row(second, seq=2, pub=802)])
    cfg = dict(DEFAULT_CONFIG)
    cfg["MEASUREMENT_DB_ENABLED"] = True
    cfg["MEASUREMENT_DB_PATH"] = str(db)
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    manager = ConfigManager(str(cfg_path))
    manager.load()
    app = create_app(manager, ControllerState())
    trigger_payload = _route_endpoint(app, "/api/graph/v1/episode-triggers")(start_ms=start - 1, end_ms=second + 1, limit=100)
    pubs = [x for x in trigger_payload["items"] if x["trigger_type"] == "PUBLISHED_EVENT"]
    compare = _route_endpoint(app, "/api/graph/v1/episode-comparison")(
        trigger_a=pubs[0]["trigger_id"], trigger_b=pubs[1]["trigger_id"], before_ms=0, after_ms=1000,
        series="grid_power_w,target_final_w", entities="", entity_series="", resolution="highres",
    )
    assert compare["contract_version"] == 1
    assert compare["episodes"]["a"]["trigger"]["trigger_id"] == pubs[0]["trigger_id"]
    assert compare["episodes"]["b"]["trigger"]["trigger_id"] == pubs[1]["trigger_id"]


def test_graph_page_exposes_wp9_pair_side_by_side_overlay_and_synchronized_inspector():
    root = Path(__file__).resolve().parents[1]
    html = build_graph_page({})
    js = (root / "static" / "graph_v14_1.js").read_text(encoding="utf-8")
    assert "/api/graph/v1/episode-triggers" in js
    assert "/api/graph/v1/episode-comparison" in js
    assert "Episoden t=0" in html
    assert "Nebeneinander" in html
    assert "Überlagert" in html
    assert "t=0" in html
    assert "selectCursor" in js
    assert "gfComparePowerA" in html
    assert "gfComparePowerB" in html
    assert "gfComparePowerOverlay" in html
    assert "episodeA.overview.relative_timestamps_ms" in js
    assert "episodeB.overview.relative_timestamps_ms" in js
    assert "/graph-view-data" not in js


def test_wp9_does_not_modify_controller_logic():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256((root / "controller_logic.py").read_bytes()).hexdigest()
    assert digest == EXPECTED_CONTROLLER_SHA256
