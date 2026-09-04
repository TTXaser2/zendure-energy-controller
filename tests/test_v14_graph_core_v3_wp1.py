import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from graph_core_v3 import (
    INT64_MAX,
    POWER_SCALE,
    SparseStateBuilder,
    V4SourceError,
    connect_graph_core,
    decode_scaled,
    encode_scaled,
    extract_system_sample,
    iter_v4_rows,
    series_catalog,
)
from tools.rebuild_graph_core_v3 import rebuild


def _write_v4(path: Path, rows, *, trailing_nuls: int = 0):
    header = [
        "schema_version", "cycle_index", "measurement_epoch_ms", "config_control_hash",
        "operating_mode", "control_intent", "grid_power_w", "grid_power_raw_w", "grid_power_valid",
        "pv_power_w", "pv_power_valid", "house_power_w", "house_power_valid",
        "zendure_actual_power_w", "zendure_actual_power_valid", "zendure_soc_percent", "zendure_soc_valid",
        "second_battery_power_w", "second_battery_power_valid", "second_battery_soc_percent", "second_battery_soc_valid",
        "control_grid_power_w", "control_grid_power_smoothed_w", "control_grid_power_smoothed_valid",
        "target_raw_w", "target_limited_w", "target_filtered_w", "target_step_limited_w", "target_final_w", "target_final_reason",
        "target_changed_by_deadband", "target_changed_by_smoothing", "target_changed_by_step_limit", "target_changed_by_soc_limit",
        "target_changed_by_power_limit", "target_changed_by_cross_charge", "target_changed_by_mode", "target_changed_by_safe_state",
        "zendure_power_observation_direction", "zendure_power_observation_confidence",
        "command_lifecycle_state", "command_desired_sequence_id", "command_desired_smart_mode", "command_desired_ac_mode",
        "command_desired_input_limit_w", "command_desired_output_limit_w", "command_desired_signed_target_w",
        "command_publish_event_id", "command_publish_epoch_s", "command_readback_matches_desired", "command_readback_mismatch_fields",
        "zendure_command_smart_mode", "zendure_command_ac_mode", "zendure_command_input_limit_w", "zendure_command_output_limit_w",
        "command_effect_category", "command_effect_reference_w", "command_effect_reason", "command_resync_count",
        "command_neutralization_episode_id", "zendure_unit_count",
    ]
    with path.open("wb") as fh:
        fh.write((";".join(header) + "\r\n").encode())
        for row in rows:
            fh.write((";".join(str(row.get(key, "")) for key in header) + "\r\n").encode())
        if trailing_nuls:
            fh.write(b"\x00" * trailing_nuls)


def _row(ts, cycle, **extra):
    data = {
        "schema_version": 4,
        "cycle_index": cycle,
        "measurement_epoch_ms": ts,
        "config_control_hash": "hash-a",
        "operating_mode": "AUTO",
        "control_intent": "CHARGE",
        "grid_power_w": 100.0,
        "grid_power_raw_w": 101.0,
        "grid_power_valid": 1,
        "zendure_actual_power_w": 90.0,
        "zendure_actual_power_valid": 1,
        "zendure_soc_percent": 50.0,
        "zendure_soc_valid": 1,
        "target_raw_w": 120.0,
        "target_limited_w": 115.0,
        "target_filtered_w": 110.0,
        "target_step_limited_w": 105.0,
        "target_final_w": 100.0,
        "target_final_reason": "AUTO_GRID_EXPORT",
        "zendure_power_observation_direction": "CHARGE",
        "zendure_power_observation_confidence": "HIGH",
        "command_lifecycle_state": "TRACKING",
        "command_desired_sequence_id": 1,
        "command_desired_smart_mode": 1,
        "command_desired_ac_mode": "input",
        "command_desired_input_limit_w": 100,
        "command_desired_output_limit_w": 0,
        "command_desired_signed_target_w": 100,
        "command_publish_event_id": 1,
        "command_publish_epoch_s": ts / 1000.0,
        "command_readback_matches_desired": 1,
        "zendure_command_smart_mode": 1,
        "zendure_command_ac_mode": "input",
        "zendure_command_input_limit_w": 100,
        "zendure_command_output_limit_w": 0,
        "command_effect_category": "COMMAND_TARGET_TRACKING_EFFECTIVE",
        "command_effect_reference_w": 90,
        "command_resync_count": 0,
        "command_neutralization_episode_id": 0,
        "zendure_unit_count": 1,
    }
    data.update(extra)
    return data


def test_scaled_integer_range_and_round_trip_supports_large_installations():
    for watts in (-1_000_000_000.0, -30_000.0, 0.0, 30_000.0, 1_000_000_000.0):
        encoded = encode_scaled(watts, scale=POWER_SCALE)
        assert encoded is not None
        assert decode_scaled(encoded, scale=POWER_SCALE) == watts
    assert encode_scaled(INT64_MAX / POWER_SCALE * 2, scale=POWER_SCALE) is None
    assert encode_scaled(float("inf"), scale=POWER_SCALE) is None


def test_catalog_declares_integer_storage_contract():
    catalog = {item["series_id"]: item for item in series_catalog()}
    assert catalog["grid_power_w"]["storage_encoding"] == "INTEGER"
    assert catalog["grid_power_w"]["storage_scale"] == 10
    assert catalog["zendure_soc_percent"]["storage_scale"] == 10
    assert catalog["target_final_w"]["aggregation"] == "state_numeric"


def test_schema_uses_primary_key_without_redundant_timestamp_indexes(tmp_path):
    db = tmp_path / "v3.sqlite3"
    conn = connect_graph_core(db)
    try:
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(measurement_raw)")}
        assert "idx_measurement_raw_ts" not in indexes
        indexes_1m = {row[1] for row in conn.execute("PRAGMA index_list(measurement_1min)")}
        assert "idx_measurement_1min_bucket" not in indexes_1m
        config_indexes = {row[1] for row in conn.execute("PRAGMA index_list(graph_config_timeline)")}
        assert "idx_graph_config_timeline_hash" not in config_indexes
        assert conn.execute("SELECT value FROM measurement_meta WHERE key='schema_version'").fetchone()[0] == "3"
    finally:
        conn.close()


def test_trailing_nul_padding_is_accepted_and_reported(tmp_path):
    source = tmp_path / "v4.csv"
    _write_v4(source, [_row(1_780_000_000_000, 1)], trailing_nuls=307)
    anomalies, iterator = iter_v4_rows(source)
    rows = list(iterator)
    assert len(rows) == 1
    assert [(a.kind, a.detail) for a in anomalies] == [("TRAILING_NUL_PADDING", "307")]


def test_embedded_nul_is_rejected(tmp_path):
    source = tmp_path / "v4.csv"
    _write_v4(source, [_row(1_780_000_000_000, 1)])
    data = source.read_bytes().replace(b"AUTO", b"AU\x00TO", 1)
    source.write_bytes(data)
    anomalies, iterator = iter_v4_rows(source)
    with pytest.raises(V4SourceError, match="embedded NUL"):
        list(iterator)
    assert anomalies == []


def test_rebuild_creates_correct_minute_valid_counts_and_sparse_states(tmp_path):
    source = tmp_path / "v4.csv"
    start = 1_780_000_000_000
    rows = [
        _row(start, 1, pv_power_w="", pv_power_valid=0, target_changed_by_step_limit=0),
        _row(start + 3_000, 2, grid_power_w=200.0, pv_power_w=1000.0, pv_power_valid=1, target_changed_by_step_limit=1),
        _row(start + 6_000, 3, grid_power_w=300.0, pv_power_w=1200.0, pv_power_valid=1, target_changed_by_step_limit=1),
        _row(start + 65_000, 4, operating_mode="HOLD", target_changed_by_step_limit=0, command_desired_sequence_id=2, command_publish_event_id=2),
    ]
    _write_v4(source, rows, trailing_nuls=8)
    db = tmp_path / "v3.sqlite3"
    result = rebuild([source], db, reset=True, batch_size=2, progress_every=0)
    assert result["status"] == "ok"
    assert result["validation"]["raw_rows"] == 4
    assert result["validation"]["trailing_nul_bytes"] == 8
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        minute = conn.execute("SELECT * FROM measurement_1min ORDER BY bucket_start_ms LIMIT 1").fetchone()
        assert minute["sample_count"] == 3
        assert minute["grid_power_dw_count"] == 3
        assert minute["grid_power_dw_sum"] == 6000
        assert minute["pv_power_dw_count"] == 2
        assert minute["pv_power_dw_sum"] == 22000
        intervals = conn.execute("SELECT kind,value_code,start_ms,end_ms FROM graph_intervals ORDER BY start_ms,kind").fetchall()
        modes = [r for r in intervals if r["kind"] == "OPERATING_MODE"]
        assert [(r["value_code"], r["start_ms"]) for r in modes] == [("AUTO", start), ("HOLD", start + 65_000)]
        limiters = [r for r in intervals if r["kind"] == "LIMITER" and r["value_code"] == "STEP_LIMIT"]
        assert len(limiters) == 1
        assert limiters[0]["start_ms"] == start + 3_000
        assert limiters[0]["end_ms"] == start + 65_000
        events = conn.execute("SELECT event_type,publish_event_id,desired_sequence_id FROM graph_command_events ORDER BY ts_ms,event_id").fetchall()
        assert any(r["event_type"] == "PUBLISHED" and r["publish_event_id"] == 1 for r in events)
        assert any(r["event_type"] == "PUBLISHED" and r["publish_event_id"] == 2 for r in events)
        assert not any(r["event_type"] == "DESIRED_CHANGED" for r in events)
        dense = conn.execute("SELECT command_desired_sequence_id FROM measurement_raw ORDER BY ts_ms").fetchall()
        assert [r[0] for r in dense] == [1, 1, 1, 2]
        assert conn.execute("SELECT trailing_nul_bytes FROM graph_source_files").fetchone()[0] == 8
    finally:
        conn.close()


def test_run_namespace_is_reconstructed_when_cycle_index_resets(tmp_path):
    source = tmp_path / "v4.csv"
    start = 1_780_000_000_000
    rows = [
        _row(start, 1, command_desired_sequence_id=1, command_publish_event_id=1),
        _row(start + 3_000, 2, command_desired_sequence_id=1, command_publish_event_id=1),
        _row(start + 6_000, 1, command_desired_sequence_id=1, command_publish_event_id=1),
    ]
    _write_v4(source, rows)
    db = tmp_path / "v3.sqlite3"
    rebuild([source], db, reset=True, progress_every=0)
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM graph_runs").fetchone()[0] == 2
        published = conn.execute("SELECT run_id,publish_event_id FROM graph_command_events WHERE event_type='PUBLISHED' ORDER BY event_id").fetchall()
        assert published == [(1, 1), (2, 1)]
    finally:
        conn.close()


def test_rebuild_refuses_existing_output_without_reset(tmp_path):
    source = tmp_path / "v4.csv"
    _write_v4(source, [_row(1_780_000_000_000, 1)])
    db = tmp_path / "v3.sqlite3"
    db.write_bytes(b"existing")
    with pytest.raises(SystemExit, match="--reset"):
        rebuild([source], db, reset=False, progress_every=0)


def test_benchmark_tool_reports_integer_candidate_metrics_without_timing_flake(tmp_path):
    tool = Path(__file__).resolve().parents[1] / "tools" / "benchmark_graph_core_v3.py"
    proc = subprocess.run(
        [sys.executable, str(tool), "--rows", "10000", "--repetitions", "2", "--dir", str(tmp_path / "bench")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    # Exit 2 intentionally means the *measured* timing gate asks for review.
    # A small unit-test benchmark must not become flaky merely because the host
    # scheduler injects one latency outlier; the reproducible 100k engineering
    # benchmark is the actual selection gate.  The unit test validates the
    # structural/storage contract and that a complete report is produced.
    assert proc.returncode in {0, 2}, proc.stderr + proc.stdout
    result = json.loads(proc.stdout)
    assert result["scaled_integer"]["db_bytes"] < result["real"]["db_bytes"]
    assert result["integer_db_reduction_percent"] > 40.0
    assert result["real"]["query_uses_integer_primary_key"] == 1
    assert result["scaled_integer"]["query_uses_integer_primary_key"] == 1
    assert isinstance(result["integer_selected_if_no_regression"], bool)


def test_invalid_numeric_is_not_saturated_and_is_reported(tmp_path):
    source = tmp_path / "v4.csv"
    _write_v4(source, [_row(1_780_000_000_000, 1, grid_power_w="inf")])
    db = tmp_path / "v3.sqlite3"
    result = rebuild([source], db, reset=True, progress_every=0)
    assert result["invalid_numeric_fields"] == {"grid_power_w": 1}
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT grid_power_dw FROM measurement_raw").fetchone()[0] is None
    finally:
        conn.close()


def test_quality_intervals_preserve_valid_invalid_transitions(tmp_path):
    source = tmp_path / "v4.csv"
    start = 1_780_000_000_000
    _write_v4(source, [
        _row(start, 1, grid_power_valid=1),
        _row(start + 3_000, 2, grid_power_valid=0),
        _row(start + 6_000, 3, grid_power_valid=1),
    ])
    db = tmp_path / "v3.sqlite3"
    rebuild([source], db, reset=True, progress_every=0)
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT start_ms,end_ms,value_code FROM graph_intervals WHERE kind='GRID_DATA' ORDER BY start_ms"
        ).fetchall()
        assert rows[0] == (start, start + 3_000, "VALID")
        assert rows[1] == (start + 3_000, start + 6_000, "INVALID")
        assert rows[2][0] == start + 6_000 and rows[2][2] == "VALID"
    finally:
        conn.close()
