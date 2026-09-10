import hashlib
import json
from pathlib import Path

import pytest

from config_manager import ConfigManager, DEFAULT_CONFIG
from graph_config_timeline import upsert_timeline_entry
from graph_query_service import GraphQueryError, GraphQueryService
from graph_workspace import workspace_manifest
from state import ControllerState
from web_ui import build_graph_page, create_app
from tests.test_v14_graph_query_service_wp3 import _row, _v3


EXPECTED_CONTROLLER_SHA256 = "d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff"


def _route_endpoint(app, path):
    for route in app.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint
    raise AssertionError(path)


def _event_id(service: GraphQueryService, db: Path, ts_ms: int) -> int:
    payload = service.inspector(str(db), ts_ms, tolerance_ms=2_000)
    return int(payload["correlation"]["linked_event_id"])


def test_wp8_manifest_exposes_inspector_and_command_follow_without_claiming_effectiveness():
    manifest = workspace_manifest(GraphQueryService(cache_max_entries=0).catalog())
    assert manifest["workspace_contract_version"] == 2
    assert manifest["capabilities"]["inspector"] == "available_wp8"
    assert manifest["capabilities"]["command_follow"] == "available_wp8"
    assert manifest["capabilities"]["episode_comparison"] == "available_wp9"
    assert manifest["inspector"]["contract_version"] == 2
    assert manifest["command_follow"]["contract_version"] == 1
    assert manifest["command_follow"]["publish_is_effectiveness_proof"] is False
    assert manifest["command_follow"]["direction_is_effectiveness_proof"] is False
    assert manifest["command_follow"]["system_effect_without_branch_target"] == "NOT_EVALUABLE"


def test_inspector_projects_raw_target_pipeline_states_config_and_command_link(tmp_path):
    start = 1_784_000_000_000
    db = _v3(tmp_path, [_row(start, seq=7, pub=4, target=123)])
    import sqlite3
    conn = sqlite3.connect(db)
    try:
        upsert_timeline_entry(
            conn,
            start - 10_000,
            "cfg-wp8",
            overlay={"min_soc": 10, "max_soc": 80, "reserve_soc": 20, "night_start": "21:30", "night_end": "05:30"},
            source="TEST",
            commit=False,
        )
        conn.commit()
    finally:
        conn.close()

    payload = GraphQueryService(cache_max_entries=0).inspector(str(db), start + 1000, tolerance_ms=2_000)
    assert payload["contract_version"] == 2
    assert payload["actual_ms"] == start
    assert payload["delta_ms"] == -1000
    assert payload["groups"]["measurement"]["grid_power_w"] == 120.0
    assert payload["groups"]["target_pipeline"] == {
        "target_raw_w": 163.0,
        "target_limited_w": 153.0,
        "target_filtered_w": 143.0,
        "target_step_limited_w": 133.0,
        "target_final_w": 123.0,
    }
    assert payload["groups"]["command"]["command_desired_target_w"] == 123.0
    assert payload["active_states"]["OPERATING_MODE"][0]["value_code"] == "AUTO"
    assert payload["active_states"]["CONTROL_REASON"][0]["value_code"] == "AUTO_GRID_EXPORT"
    assert payload["correlation"]["desired_sequence_id"] == 7
    assert payload["correlation"]["publish_event_id"] == 4
    assert payload["linked_command_event"]["event_type"] == "PUBLISHED"
    assert payload["config"]["max_soc"] == 80
    assert payload["meta"]["read_only"] is True


def test_inspector_keeps_historical_entity_and_topology_context_without_inventing_units(tmp_path):
    from tests.test_v14_graph_entities_wp4 import _physical_units, _row as entity_row, _v3 as entity_v3

    start = 1_784_001_000_000
    db = entity_v3(tmp_path, [
        entity_row(start, unit_count=2, units=_physical_units(start, include_b=True), primary=True),
        entity_row(start + 3000, seq=2, unit_count=2, units=_physical_units(start + 3000, include_b=True), primary=True),
    ])
    payload = GraphQueryService(cache_max_entries=0).inspector(str(db), start + 1000, tolerance_ms=2_000)
    entities = payload["entities"]
    physical = [x for x in entities if x["entity_type"] == "ZENDURE_UNIT"]
    assert len(physical) == 2
    assert all(x["source_identity"] for x in physical)
    assert all(x["actual_ms"] == start for x in physical)
    assert all(x["values"]["power_w"] is not None for x in physical)
    primary = next(x for x in entities if x["stable_id"] == "storage:primary")
    assert primary["display_name"] == "Hausspeicher"
    assert not [x for x in entities if x["entity_type"] == "ZENDURE_UNIT" and not x["source_identity"]]


def test_command_follow_separates_publish_direction_readback_tracking_and_system_effect(tmp_path):
    start = 1_784_002_000_000
    db = _v3(tmp_path, [
        _row(start, seq=1, pub=8, target=600, grid=220),
        _row(start + 3000, seq=2, pub=8, target=600, grid=80),
    ])
    service = GraphQueryService(cache_max_entries=0)
    payload = service.command_follow(str(db), event_id=_event_id(service, db, start), before_ms=1000, after_ms=10_000)
    stages = payload["stages"]
    assert stages["publish"]["status"] == "OBSERVED"
    assert stages["direction_reaction"]["status"] == "OBSERVED_AFTER_PUBLISH"
    assert stages["direction_reaction"]["causal_attribution"] == "NOT_PROVEN"
    assert stages["readback"]["status"] == "MATCH_OBSERVED"
    assert stages["tracking"]["status"] == "OBSERVATION_ONLY"
    assert stages["tracking"]["reason"] == "NO_HISTORICAL_TOLERANCE_ASSUMED"
    assert stages["system_effect"]["status"] == "NOT_EVALUABLE"
    assert stages["system_effect"]["reason"] == "NO_BRANCH_SPECIFIC_HISTORICAL_SYSTEM_TARGET_CONTRACT"
    assert payload["meta"]["effectiveness_from_publish_alone"] is False
    assert payload["meta"]["effectiveness_from_direction_alone"] is False
    assert payload["meta"]["causal_attribution"] == "NOT_PROVEN_BY_TEMPORAL_ORDER_ALONE"


def test_command_follow_preserves_controller_effect_as_labelled_non_independent_evidence(tmp_path):
    start = 1_784_003_000_000
    db = _v3(tmp_path, [_row(start, pub=9, target=500)])
    service = GraphQueryService(cache_max_entries=0)
    payload = service.command_follow(str(db), event_id=_event_id(service, db, start), before_ms=0, after_ms=5000)
    stage = payload["stages"]["controller_assessment"]
    assert stage["status"] == "TARGET_TRACKING_RECORDED"
    assert stage["categories"] == ["COMMAND_TARGET_TRACKING_EFFECTIVE"]
    assert stage["source"] == "PERSISTED_COMMAND_EFFECT_INTERVALS"
    assert stage["independent_wp8_verdict"] is False


def test_command_follow_maps_below_diagnostic_threshold_to_not_evaluable(tmp_path):
    start = 1_784_004_000_000
    row = _row(start, pub=10, target=20)
    row["command_effect_category"] = "COMMAND_BELOW_DIAGNOSTIC_THRESHOLD"
    db = _v3(tmp_path, [row])
    service = GraphQueryService(cache_max_entries=0)
    payload = service.command_follow(str(db), event_id=_event_id(service, db, start), before_ms=0, after_ms=5000)
    stage = payload["stages"]["controller_assessment"]
    assert stage["status"] == "NOT_EVALUABLE"
    assert "COMMAND_BELOW_DIAGNOSTIC_THRESHOLD" in stage["categories"]
    assert payload["stages"]["system_effect"]["status"] == "NOT_EVALUABLE"


def test_command_follow_preserves_confirmed_mismatch_without_overriding_it_from_same_direction(tmp_path):
    start = 1_784_005_000_000
    row = _row(start, pub=11, target=1000)
    row["zendure_actual_power_w"] = 100.0  # same direction, far from target
    row["command_effect_category"] = "COMMAND_MISMATCH_CONFIRMED"
    db = _v3(tmp_path, [row])
    service = GraphQueryService(cache_max_entries=0)
    payload = service.command_follow(str(db), event_id=_event_id(service, db, start), before_ms=0, after_ms=5000)
    assert payload["stages"]["direction_reaction"]["status"] == "OBSERVED_AFTER_PUBLISH"
    assert payload["stages"]["controller_assessment"]["status"] == "MISMATCH_RECORDED"
    assert payload["stages"]["tracking"]["first_abs_error_w"] == 900.0
    assert payload["meta"]["effectiveness_from_direction_alone"] is False


def test_command_follow_zero_target_is_not_treated_as_direction_effective(tmp_path):
    start = 1_784_006_000_000
    row = _row(start, pub=12, target=0)
    row["zendure_actual_power_w"] = 0.0
    row["command_effect_category"] = "COMMAND_PENDING"
    db = _v3(tmp_path, [row])
    service = GraphQueryService(cache_max_entries=0)
    payload = service.command_follow(str(db), event_id=_event_id(service, db, start), before_ms=0, after_ms=5000)
    assert payload["stages"]["direction_reaction"]["status"] == "NOT_EVALUABLE"
    assert payload["stages"]["direction_reaction"]["reason"] == "NO_NONZERO_DIRECTION_TARGET"
    assert payload["stages"]["controller_assessment"]["status"] == "PENDING_RECORDED"


def test_command_follow_is_censored_at_next_publish_and_does_not_mix_later_effect_state(tmp_path):
    start = 1_784_006_500_000
    first = _row(start, seq=1, pub=21, target=700)
    first["command_effect_category"] = "COMMAND_PENDING"
    second = _row(start + 6000, seq=2, pub=22, target=900)
    second["command_effect_category"] = "COMMAND_MISMATCH_CONFIRMED"
    db = _v3(tmp_path, [first, second])
    service = GraphQueryService(cache_max_entries=0)
    first_event_id = _event_id(service, db, start)
    payload = service.command_follow(str(db), event_id=first_event_id, before_ms=0, after_ms=180_000)
    assert payload["window"]["censored_by_next_publish"] is True
    assert payload["window"]["to_ms"] == start + 5999
    assert payload["window"]["next_publish_ms"] == start + 6000
    assert payload["window"]["next_publish_event_id"] != first_event_id
    assert payload["stages"]["controller_assessment"]["status"] == "PENDING_RECORDED"
    assert "COMMAND_MISMATCH_CONFIRMED" not in payload["stages"]["controller_assessment"]["categories"]
    assert max(payload["timeline"]["timestamps_ms"]) < start + 6000


def test_command_follow_rejects_non_publish_event_ids_instead_of_mislabelling_them_as_publish(tmp_path):
    import sqlite3

    start = 1_784_006_700_000
    db = _v3(tmp_path, [_row(start, pub=23, target=400)])
    conn = sqlite3.connect(db)
    try:
        cur = conn.execute(
            "INSERT INTO graph_command_events(ts_ms,run_id,event_type) "
            "SELECT ts_ms,run_id,'RESYNC' FROM graph_command_events WHERE event_type='PUBLISHED' LIMIT 1"
        )
        non_publish_event_id = int(cur.lastrowid)
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(GraphQueryError, match="COMMAND_EVENT_NOT_PUBLISHED"):
        GraphQueryService(cache_max_entries=0).command_follow(str(db), event_id=non_publish_event_id)


def test_command_follow_supports_nearest_publish_lookup_and_fails_closed_for_unknown_event(tmp_path):
    start = 1_784_007_000_000
    db = _v3(tmp_path, [_row(start, pub=13, target=300)])
    service = GraphQueryService(cache_max_entries=0)
    by_time = service.command_follow(str(db), ts_ms=start + 500, tolerance_ms=1000, before_ms=0, after_ms=5000)
    assert by_time["event"]["publish_event_id"] == 13
    with pytest.raises(GraphQueryError, match="UNKNOWN_COMMAND_EVENT"):
        service.command_follow(str(db), event_id=999_999)
    with pytest.raises(GraphQueryError, match="COMMAND_EVENT_NOT_FOUND"):
        service.command_follow(str(db), ts_ms=start + 100_000, tolerance_ms=100)


def test_wp8_api_and_browser_bind_inspector_and_command_follow_to_v3_without_legacy_history(tmp_path):
    start = 1_784_008_000_000
    db = _v3(tmp_path, [_row(start, pub=14, target=350)])
    cfg = dict(DEFAULT_CONFIG)
    cfg["MEASUREMENT_DB_ENABLED"] = True
    cfg["MEASUREMENT_DB_PATH"] = str(db)
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    manager = ConfigManager(str(cfg_path))
    manager.load()
    app = create_app(manager, ControllerState())

    inspector = _route_endpoint(app, "/api/graph/v1/inspector")(ts_ms=start, tolerance_ms=1000)
    event_id = int(inspector["correlation"]["linked_event_id"])
    follow = _route_endpoint(app, "/api/graph/v1/command-follow")(event_id=event_id, before_ms=0, after_ms=5000)
    assert inspector["contract_version"] == 2
    assert follow["contract_version"] == 1
    assert follow["event"]["event_id"] == event_id

    root = Path(__file__).resolve().parents[1]
    html = build_graph_page({})
    js = (root / "static" / "graph_v14_1.js").read_text(encoding="utf-8")
    assert "/api/graph/v1/inspector" in js
    assert "/api/graph/v1/command-follow" in js
    assert "Regler-Inspector" in html
    assert "Command-Follow" in html
    assert "/graph-view-data" not in js
    assert "Publish und gleiche Richtung allein gelten nicht als Wirksamkeitsnachweis" in js


def test_wp8_does_not_modify_controller_logic():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256((root / "controller_logic.py").read_bytes()).hexdigest()
    assert digest == EXPECTED_CONTROLLER_SHA256
