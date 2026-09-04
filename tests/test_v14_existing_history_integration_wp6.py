import inspect
import json
import sqlite3
from datetime import datetime, timedelta

from graph_config_timeline import build_segments_from_rows, overlay_legend_transitions, upsert_timeline_entry
from graph_core_v3 import connect_graph_core
from graph_core_v3_live import GraphCoreV3LiveSession
from graph_history_runtime import graph_history_runtime_status, query_storage_day_history
from graph_query_service import GraphQueryService
from measurement_db import ensure_schema
import web_ui


def _config(db):
    return {"MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_DB_PATH": str(db)}


def _row(ts_ms, seq=1, *, config_hash="cfg-a", overlay=None, units=None):
    if overlay is None:
        overlay = {"min_soc": 10, "max_soc": 99, "reserve_soc": 20, "night_start": "21:30", "night_end": "05:30"}
    if units is None:
        units = [
            {"device_id": "UNIT-A", "display_name": "Zendure A", "actual_power_w": 60.0, "power_valid": 1,
             "soc_percent": 51.0, "soc_valid": 1, "target_w": 70.0, "target_valid": 1,
             "readback_target_w": 68.0, "readback_valid": 1},
            {"device_id": "UNIT-B", "display_name": "Zendure B", "actual_power_w": 35.0, "power_valid": 1,
             "soc_percent": 58.0, "soc_valid": 1, "target_w": 30.0, "target_valid": 1,
             "readback_target_w": 29.0, "readback_valid": 1},
        ]
    return {
        "epoch_s": ts_ms / 1000.0,
        "cycle_id": seq,
        "measurement_monotonic_ns": 10_000_000_000 + seq * 3_000_000_000,
        "grid_power_w": 100.0,
        "raw_grid_power_w": 101.0,
        "grid_power_valid": True,
        "zendure_actual_power_w": 95.0,
        "actual_zendure_power_valid": True,
        "zendure_soc_percent": 55.0,
        "soc_valid": True,
        "second_battery_power_w": 200.0,
        "second_battery_soc_percent": 70.0,
        "second_battery_data_valid": True,
        "second_battery_valid": True,
        "target_raw_w": 140.0,
        "target_after_power_limit_w": 130.0,
        "target_after_smoothing_w": 120.0,
        "target_after_ramp_w": 110.0,
        "target_final_w": 100.0,
        "target_final_reason": "AUTO_GRID_EXPORT",
        "operating_mode": "AUTO",
        "control_intent": "CHARGE",
        "command_lifecycle_state": "TRACKING",
        "command_effect_category": "COMMAND_TARGET_TRACKING_EFFECTIVE",
        "command_desired_sequence_id": seq,
        "command_desired_intent": "CHARGE",
        "command_desired_smart_mode": 1,
        "command_desired_ac_mode": "input",
        "command_desired_input_limit_w": 100.0,
        "command_desired_output_limit_w": 0.0,
        "command_desired_signed_target_w": 100.0,
        "command_publish_event_id": seq,
        "command_publish_epoch_s": ts_ms / 1000.0,
        "command_publish_monotonic_ns": 9_500_000_000 + seq * 3_000_000_000,
        "zendure_command_smart_mode": 1,
        "zendure_command_ac_mode": "input",
        "zendure_command_input_limit_w": 100.0,
        "zendure_command_output_limit_w": 0.0,
        "command_readback_matches_desired": 1,
        "command_readback_mismatch_fields": "",
        "command_resync_count": 0,
        "command_neutralization_episode_id": 0,
        "zendure_unit_count": 2,
        "zendure_units_json": json.dumps(units, separators=(",", ":")),
        "config_control_hash": config_hash,
        "_graph_config_overlay": overlay,
        "_graph_entity_config": {
            "zendure_device_id": "ZE-AGGREGATE-1",
            "controlled_display_name": "Zweitspeicher",
            "primary_display_name": "Hausspeicher",
            "primary_source_profile": "evcc_standard",
            "primary_integration_enabled": True,
        },
    }


def _v3(tmp_path):
    db = tmp_path / "graph.sqlite3"
    start = int(datetime(2026, 8, 10, 1, 0).timestamp() * 1000)
    conn = connect_graph_core(db)
    try:
        session = GraphCoreV3LiveSession(run_id=(1 << 62) + 606)
        session.write_batch(conn, str(db), [_row(start, 1), _row(start + 3000, 2), _row(start + 6000, 3)])
        # Explicit historical return sequence: 99 -> 80 -> 99.  The V13 bug
        # class was global legend de-duplication; WP6 must retain both returns.
        upsert_timeline_entry(conn, start, "cfg-a", overlay={"min_soc": 10, "max_soc": 99, "reserve_soc": 20, "night_start": "21:30", "night_end": "05:30"}, source="TEST", commit=False)
        upsert_timeline_entry(conn, start + 60 * 60_000, "cfg-b", overlay={"min_soc": 10, "max_soc": 80, "reserve_soc": 20, "night_start": "21:30", "night_end": "05:30"}, source="TEST", commit=False)
        upsert_timeline_entry(conn, start + 2 * 60 * 60_000, "cfg-c", overlay={"min_soc": 10, "max_soc": 99, "reserve_soc": 20, "night_start": "21:30", "night_end": "05:30"}, source="TEST", commit=False)
        conn.commit()
    finally:
        conn.close()
    return db, start


def test_cutover_status_classifies_missing_v2_and_v3_without_v4_requirement(tmp_path):
    missing = graph_history_runtime_status(_config(tmp_path / "missing.sqlite3"))
    assert missing["read_mode"] == "UNAVAILABLE"
    assert missing["control_readiness_impact"] == "NONE"
    assert missing["measurement_v4_required"] is False

    v2 = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(v2); ensure_schema(conn); conn.close()
    legacy = graph_history_runtime_status(_config(v2))
    assert legacy["read_mode"] == "LEGACY_V2_COMPAT"
    assert legacy["legacy_history_readable"] is True
    assert legacy["workspace_ready"] is False

    v3, _ = _v3(tmp_path)
    native = graph_history_runtime_status(_config(v3))
    assert native["read_mode"] == "V3_NATIVE"
    assert native["workspace_ready"] is True
    assert native["measurement_v4_required"] is False
    assert native["capabilities"]["evidence"] is True


def test_v3_runtime_api_is_separate_from_controller_ready_route(tmp_path):
    source = inspect.getsource(web_ui.create_app)
    assert '@app.get("/api/graph/v1/runtime")' in source
    assert '@app.get("/ready")' in source
    runtime_block = source[source.index('@app.get("/api/graph/v1/runtime")'):source.index('@app.get("/api/graph/v1/coverage")')]
    assert "graph_history_runtime_status" in runtime_block
    assert "build_ready_payload" not in runtime_block


def test_compatibility_points_delegate_numeric_history_to_overview(tmp_path):
    db, start = _v3(tmp_path)
    service = GraphQueryService(cache_max_entries=0)
    points, meta = service.compatibility_points(str(db), start - 1000, start + 60_000)
    assert points and points[0]["mode"] == "AUTO"
    assert points[0]["sample_count"] == 3
    assert meta["compatibility_source"] == "overview_columnar_v1"
    method_source = inspect.getsource(GraphQueryService.compatibility_points)
    assert "FROM measurement_1min" not in method_source
    assert "self.overview(" in method_source


def test_overview_exposes_representative_sample_timestamp_for_sparse_context(tmp_path):
    db, start = _v3(tmp_path)
    payload = GraphQueryService(cache_max_entries=0).overview(
        str(db), start - 1000, start + 60_000,
        series_ids=["zendure_soc_percent"], resolution="1min", include_context=True, include_sample_metadata=True,
    )
    assert len(payload["timestamps_ms"]) == 1
    assert payload["sample_timestamps_ms"][0] == start + 6000
    assert payload["sample_counts"] == [3]


def test_config_overlay_legend_preserves_non_adjacent_return_value():
    day = datetime(2026, 8, 10)
    rows = [
        {"effective_from_ms": int(day.timestamp()*1000), "known": 1, "config_control_hash": "a", "min_soc": 10, "max_soc": 99, "reserve_soc": 20, "night_start": "21:30", "night_end": "05:30", "source": "TEST"},
        {"effective_from_ms": int((day+timedelta(hours=8)).timestamp()*1000), "known": 1, "config_control_hash": "b", "min_soc": 10, "max_soc": 80, "reserve_soc": 20, "night_start": "21:30", "night_end": "05:30", "source": "TEST"},
        {"effective_from_ms": int((day+timedelta(hours=16)).timestamp()*1000), "known": 1, "config_control_hash": "c", "min_soc": 10, "max_soc": 99, "reserve_soc": 20, "night_start": "21:30", "night_end": "05:30", "source": "TEST"},
    ]
    segments, _ = build_segments_from_rows(rows, day, day + timedelta(days=1))
    assert [s["max_soc"] for s in segments] == [99, 80, 99]
    assert overlay_legend_transitions(segments)["max_soc"] == [99, 80, 99]


def test_v3_storage_day_uses_config_entity_coverage_and_evidence_contract(tmp_path):
    db, start = _v3(tmp_path)
    day_start = datetime.combine(datetime.fromtimestamp(start/1000).date(), datetime.min.time())
    history = query_storage_day_history(_config(db), day_start, day_start + timedelta(days=1))
    assert history["read_mode"] == "V3_NATIVE"
    assert history["source"] == "graph_core_v3_1min"
    assert history["config_legend"]["max_soc"] == [99, 80, 99]
    assert history["zendure_unit_count"] == 2
    assert history["unit_labels"] == ["Zendure A", "Zendure B"]
    assert history["primary_storage_present"] is True
    assert history["primary_display_name"] == "Hausspeicher"
    assert history["coverage"]["series"]
    assert history["evidence"]["series"]
    assert history["runtime"]["measurement_v4_required"] is False
    assert history["points"][0]["zendure_unit_1_soc"] == 51.0
    assert history["points"][0]["zendure_unit_2_soc"] == 58.0


def test_status_soc_day_endpoint_switches_to_v3_history_semantics(tmp_path):
    db, start = _v3(tmp_path)
    date = datetime.fromtimestamp(start/1000).date().isoformat()
    with web_ui._storage_day_lock:
        web_ui._storage_day_cache.clear()
    payload = web_ui.build_storage_soc_day_payload(
        _config(db),
        {"battery_soc": 55, "current_mode": "AUTO", "zendure_system_signed_power": 95},
        date,
    )
    assert payload["source"] == "graph_core_v3_1min"
    assert payload["history_runtime"]["read_mode"] == "V3_NATIVE"
    assert payload["history_runtime"]["control_readiness_impact"] == "NONE"
    assert payload["config_legend"]["max_soc"] == [99, 80, 99]
    assert payload["primary_storage_present"] is True
    assert payload["history_entities"]


def test_wp6_does_not_define_retention_horizon_scheduler_or_vacuum_policy():
    runtime_source = inspect.getsource(__import__("graph_history_runtime"))
    assert "RETENTION_DAYS" not in runtime_source
    assert "VACUUM" not in runtime_source.upper()
    assert "schedule" not in runtime_source.lower()


def test_pre_wp5_v3_without_evidence_tables_remains_history_readable(tmp_path):
    db, start = _v3(tmp_path)
    conn = sqlite3.connect(db)
    try:
        for table in ("graph_availability_segments", "graph_instrumentation_timeline", "graph_retention_ledger"):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
    finally:
        conn.close()
    status = graph_history_runtime_status(_config(db))
    assert status["read_mode"] == "V3_NATIVE"
    assert status["workspace_ready"] is True
    assert status["evidence_supported"] is True
    assert status["persisted_evidence_supported"] is False
    assert status["evidence_mode"] == "DERIVED_V3_FALLBACK"
    day_start = datetime.combine(datetime.fromtimestamp(start/1000).date(), datetime.min.time())
    history = query_storage_day_history(_config(db), day_start, day_start + timedelta(days=1))
    assert history["points"], "missing WP5 evidence tables must not make V3 history unusable"
    assert history["runtime"]["measurement_v4_required"] is False
    assert history["evidence"]["series"], "fallback evidence may be derived from persisted V3 data"
    assert history["evidence"]["retention"] == []
    statuses = {item["status"] for items in history["evidence"]["series"].values() for item in items}
    assert "AVAILABLE" in statuses
