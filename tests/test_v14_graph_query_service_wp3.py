import json
import os
import sqlite3
from pathlib import Path

import pytest

from graph_core_v3 import connect_graph_core
from graph_core_v3_live import GraphCoreV3LiveSession
from graph_query_service import (
    GRAPH_QUERY_SERVICE,
    GraphQueryError,
    GraphQueryService,
    canonical_series_catalog,
    plan_query,
)
from measurement_db import ensure_schema, query_graph_points


def _row(ts_ms: int, *, seq: int = 1, pub: int = 1, target: float = 100.0, grid: float = 120.0, raw_grid: float = 121.0):
    return {
        "epoch_s": ts_ms / 1000.0,
        "cycle_id": seq,
        "measurement_monotonic_ns": 10_000_000_000 + seq * 3_000_000_000,
        "grid_power_w": grid,
        "raw_grid_power_w": raw_grid,
        "grid_power_valid": True,
        "zendure_actual_power_w": target - 5,
        "actual_zendure_power_valid": True,
        "zendure_soc_percent": 55.0,
        "soc_valid": True,
        "second_battery_power_w": 200.0,
        "second_battery_soc_percent": 70.0,
        "second_battery_data_valid": True,
        "target_raw_w": target + 40,
        "target_after_power_limit_w": target + 30,
        "target_after_smoothing_w": target + 20,
        "target_after_ramp_w": target + 10,
        "target_final_w": target,
        "target_final_reason": "AUTO_GRID_EXPORT",
        "operating_mode": "AUTO",
        "control_intent": "CHARGE",
        "command_lifecycle_state": "TRACKING",
        "command_effect_category": "COMMAND_TARGET_TRACKING_EFFECTIVE",
        "command_desired_sequence_id": seq,
        "command_desired_intent": "CHARGE",
        "command_desired_smart_mode": 1,
        "command_desired_ac_mode": "input",
        "command_desired_input_limit_w": target,
        "command_desired_output_limit_w": 0,
        "command_desired_signed_target_w": target,
        "command_publish_event_id": pub,
        "command_publish_epoch_s": ts_ms / 1000.0,
        "command_publish_monotonic_ns": 10_000_000_000 + seq * 3_000_000_000 - 500_000_000,
        "zendure_command_smart_mode": 1,
        "zendure_command_ac_mode": "input",
        "zendure_command_input_limit_w": target,
        "zendure_command_output_limit_w": 0,
        "command_readback_matches_desired": 1,
        "command_readback_mismatch_fields": "",
        "command_resync_count": 0,
        "command_neutralization_episode_id": 0,
        "zendure_unit_count": 1,
    }


def _v3(tmp_path: Path, rows):
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        session = GraphCoreV3LiveSession(run_id=(1 << 62) + 303)
        session.write_batch(conn, str(db), rows)
    finally:
        conn.close()
    return db


def test_catalog_has_stable_ids_presentation_keys_and_temporal_semantics():
    items = canonical_series_catalog()
    assert len(items) == 17
    by_id = {item["series_id"]: item for item in items}
    assert by_id["grid_power_w"]["label_key"] == "graph.series.grid_power_w"
    assert by_id["grid_power_w"]["temporal_type"] == "continuous"
    assert by_id["target_final_w"]["temporal_type"] == "target"
    assert by_id["grid_power_w"]["entity_scope"] == "system"
    assert by_id["grid_power_w"]["storage_scale"] == 10


def test_query_planner_uses_highres_for_short_window_and_minute_for_wide_window():
    assert plan_query(0, 30 * 60_000).source == "raw"
    assert plan_query(0, 24 * 60 * 60_000).source == "1min"
    assert plan_query(0, 24 * 60 * 60_000, purpose="inspector").source == "raw"
    assert plan_query(0, 24 * 60 * 60_000, resolution="highres").source == "raw"


def test_overview_is_columnar_and_highres_keeps_quality_flags(tmp_path):
    start = 1_780_000_000_000
    db = _v3(tmp_path, [_row(start), _row(start + 3000, seq=2, target=110)])
    service = GraphQueryService(cache_max_entries=0)
    payload = service.overview(str(db), start, start + 10_000, series_ids=["grid_power_w", "target_final_w"])
    assert payload["format"] == "columnar_v1"
    assert payload["resolution"] == "highres"
    assert payload["timestamps_ms"] == [start, start + 3000]
    assert payload["series"]["grid_power_w"] == [120.0, 120.0]
    assert payload["series"]["target_final_w"] == [100.0, 110.0]
    assert len(payload["quality_flags"]) == 2
    assert all(isinstance(x, int) for x in payload["quality_flags"])


def test_minute_reaggregation_uses_sum_and_valid_count_for_continuous_grid_series(tmp_path):
    start = 1_780_000_020_000
    db = _v3(tmp_path, [
        _row(start, grid=100, raw_grid=200),
        _row(start + 3000, seq=2, grid=300, raw_grid=400),
    ])
    service = GraphQueryService(cache_max_entries=0)
    payload = service.overview(
        str(db), start - 1, start + 3 * 60 * 60_000,
        series_ids=["grid_power_w", "raw_grid_power_w", "control_grid_power_w"], resolution="1min", include_context=False,
    )
    assert payload["series"]["grid_power_w"][0] == 200.0
    assert payload["series"]["raw_grid_power_w"][0] == 300.0
    assert payload["series"]["control_grid_power_w"][0] == 200.0


def test_sparse_context_and_event_truncation_are_explicit(tmp_path):
    start = 1_780_001_000_000
    rows = [_row(start + i * 3000, seq=i + 1, pub=i + 1, target=100 + i) for i in range(5)]
    db = _v3(tmp_path, rows)
    service = GraphQueryService(cache_max_entries=0)
    payload = service.overview(str(db), start, start + 20_000, event_limit=2)
    assert payload["intervals"]["items"]
    assert payload["command_events"]["truncated"] is True
    assert payload["command_events"]["limit"] == 2
    assert len(payload["command_events"]["items"]) == 2


def test_topology_window_returns_only_latest_prior_state_per_subject(tmp_path):
    start = 1_780_002_000_000
    db = _v3(tmp_path, [_row(start)])
    conn = sqlite3.connect(db)
    try:
        cur = conn.execute("INSERT INTO graph_entities(stable_id,entity_type) VALUES('z1','ZENDURE')")
        test_entity_id = int(cur.lastrowid)
        conn.executemany(
            "INSERT INTO graph_topology_timeline(effective_from_ms,entity_id,entity_type,state,unit_count,source) VALUES(?,?,?,?,?,?)",
            [
                (start - 30_000, test_entity_id, "ZENDURE", "PRESENT", 1, "TEST"),
                (start - 20_000, test_entity_id, "ZENDURE", "ABSENT", 0, "TEST"),
                (start - 10_000, test_entity_id, "ZENDURE", "PRESENT", 1, "TEST"),
            ],
        )
        conn.commit()
    finally:
        conn.close()
    service = GraphQueryService(cache_max_entries=0)
    payload = service.overview(str(db), start, start + 10_000, series_ids=["grid_power_w"])
    entity_rows = [x for x in payload["topology_timeline"] if x.get("entity_id") == test_entity_id]
    assert len(entity_rows) == 1
    assert entity_rows[0]["state"] == "PRESENT"


def test_coverage_is_series_specific_and_prefers_persisted_segments(tmp_path):
    start = 1_780_003_000_000
    db = _v3(tmp_path, [_row(start), _row(start + 3000, seq=2)])
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO graph_series_coverage(series_id,from_ms,to_ms,source,quality) VALUES(?,?,?,?,?)",
            ("grid_power_w", start - 1000, start + 4000, "MEASUREMENT_V4", "OBSERVED_NON_NULL_SPAN"),
        )
        conn.commit()
    finally:
        conn.close()
    service = GraphQueryService(cache_max_entries=0)
    payload = service.coverage(str(db), series_ids=["grid_power_w", "target_final_w"])
    assert payload["series"]["grid_power_w"]["from_ms"] == start - 1000
    assert payload["series"]["grid_power_w"]["segments"][0]["source"] == "MEASUREMENT_V4"
    assert payload["series"]["target_final_w"]["from_ms"] == start


def test_inspector_uses_nearest_raw_sample_and_exposes_command_correlation(tmp_path):
    start = 1_780_004_000_000
    db = _v3(tmp_path, [_row(start, seq=7, pub=4, target=123)])
    service = GraphQueryService(cache_max_entries=0)
    payload = service.inspector(str(db), start + 1000, series_ids=["target_final_w"], tolerance_ms=2000)
    assert payload["actual_ms"] == start
    assert payload["values"]["target_final_w"] == 123.0
    assert payload["correlation"]["desired_sequence_id"] == 7
    assert payload["correlation"]["publish_event_id"] == 4


def test_cache_hit_is_invalidated_when_wal_changes(tmp_path):
    start = 1_780_005_000_000
    db = _v3(tmp_path, [_row(start)])
    service = GraphQueryService(cache_max_entries=4, cache_ttl_s=60)
    first = service.overview(str(db), start, start + 20_000, series_ids=["grid_power_w"], include_context=False)
    second = service.overview(str(db), start, start + 20_000, series_ids=["grid_power_w"], include_context=False)
    assert first["meta"]["cache"] == "miss"
    assert second["meta"]["cache"] == "hit"
    conn = connect_graph_core(db)
    try:
        GraphCoreV3LiveSession(run_id=(1 << 62) + 304).write_batch(conn, str(db), [_row(start + 3000, seq=2)])
        # Keep connection open so the WAL remains the visible change carrier.
        third = service.overview(str(db), start, start + 20_000, series_ids=["grid_power_w"], include_context=False)
    finally:
        conn.close()
    assert third["meta"]["cache"] == "miss"
    assert len(third["timestamps_ms"]) == 2


def test_v2_database_is_rejected_by_new_service_without_mutation(tmp_path):
    db = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(db)
    ensure_schema(conn)
    conn.close()
    before = db.read_bytes()
    service = GraphQueryService(cache_max_entries=0)
    with pytest.raises(GraphQueryError, match="GRAPH_DB_NOT_V3"):
        service.coverage(str(db))
    assert db.read_bytes() == before


def test_overview_rejects_more_than_48_hours(tmp_path):
    start = 1_780_006_000_000
    db = _v3(tmp_path, [_row(start)])
    with pytest.raises(GraphQueryError, match="WINDOW_EXCEEDS_48H"):
        GraphQueryService(cache_max_entries=0).overview(str(db), start, start + 49 * 60 * 60_000)


def test_unknown_series_is_fail_closed(tmp_path):
    start = 1_780_007_000_000
    db = _v3(tmp_path, [_row(start)])
    with pytest.raises(GraphQueryError, match="UNKNOWN_SERIES"):
        GraphQueryService(cache_max_entries=0).overview(str(db), start, start + 10_000, series_ids=["made_up_series"])


def test_existing_graph_points_v3_adapter_uses_central_query_service(tmp_path):
    start = 1_780_008_000_000
    db = _v3(tmp_path, [_row(start, target=150)])
    cfg = {"MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_DB_PATH": str(db)}
    from datetime import datetime
    points, meta = query_graph_points(
        cfg,
        datetime.fromtimestamp((start - 1000) / 1000),
        datetime.fromtimestamp((start + 60_000) / 1000),
    )
    assert meta["query_service"] == "graph_query_service_v1"
    assert points[0]["zendure_target_power_w"] == 150.0
    assert points[0]["mode"] == "AUTO"
