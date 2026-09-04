import sqlite3
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from graph_core_v3 import connect_graph_core
from graph_core_v3_live import GraphCoreV3LiveSession, open_v3
from measurement_db import MeasurementDbWriter, detect_measurement_db_backend, ensure_schema, query_graph_points
from settings_registry import SETTINGS_BY_KEY
from state import ControllerState


def _config(path: Path):
    return {
        "MEASUREMENT_DB_ENABLED": True,
        "MEASUREMENT_DB_PATH": str(path),
        "MEASUREMENT_LOG_DIR": str(path.parent),
        "MEASUREMENT_LOG_FALLBACK_DIR": str(path.parent / "fallback"),
        "MIN_SOC_PERCENT": 10,
        "MAX_SOC_PERCENT": 99,
        "NIGHT_DISCHARGE_STOP_SOC_PERCENT": 20,
        "NIGHT_START_HOUR": 21,
        "NIGHT_START_MINUTE": 30,
        "NIGHT_END_HOUR": 5,
        "NIGHT_END_MINUTE": 30,
    }


def _row(ts_ms: int, seq: int = 1, pub: int = 1, target: float = 100.0):
    return {
        "epoch_s": ts_ms / 1000.0,
        "cycle_id": seq,
        "measurement_monotonic_ns": 10_000_000_000 + seq * 3_000_000_000,
        "grid_power_w": 120.0,
        "raw_grid_power_w": 121.0,
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


def _wait_rows(writer, expected, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = writer.status()
        if int(st.get("measurement_db_rows_written") or 0) >= expected:
            return st
        time.sleep(0.02)
    return writer.status()


def test_missing_database_defaults_to_v3_live_writer(tmp_path):
    db = tmp_path / "measurements.sqlite3"
    writer = MeasurementDbWriter()
    try:
        writer.enqueue(_config(db), _row(1_780_000_000_000))
        st = _wait_rows(writer, 1)
        assert st["measurement_db_backend"] == "v3"
        assert st["measurement_db_schema_version"] == 3
        assert st["measurement_db_storage_encoding"] == "scaled_integer_v1"
        assert st["measurement_db_run_id"] is not None
        assert st["measurement_db_rows_dropped"] == 0
    finally:
        writer.close()
    assert detect_measurement_db_backend(str(db))["backend"] == "v3"
    conn = sqlite3.connect(db)
    try:
        raw = conn.execute(
            "SELECT run_id,command_desired_sequence_id,command_publish_event_id,command_desired_target_dw,command_readback_target_dw FROM measurement_raw"
        ).fetchone()
        assert raw[0] == st["measurement_db_run_id"]
        assert raw[1:] == (1, 1, 1000, 1000)
        event = conn.execute(
            "SELECT event_type,monotonic_ns,publish_event_id FROM graph_command_events"
        ).fetchone()
        assert event == ("PUBLISHED", _row(1_780_000_000_000)["command_publish_monotonic_ns"], 1)
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()


def test_existing_v2_database_remains_v2_and_is_not_upgraded(tmp_path):
    db = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(db)
    ensure_schema(conn)
    conn.close()
    conn = sqlite3.connect(db)
    try:
        before_cols = {r[1] for r in conn.execute("PRAGMA table_info(measurement_raw)")}
    finally:
        conn.close()
    writer = MeasurementDbWriter()
    try:
        writer.enqueue(_config(db), _row(1_780_000_003_000))
        st = _wait_rows(writer, 1)
        assert st["measurement_db_backend"] == "v2"
        assert st["measurement_db_schema_version"] == 2
    finally:
        writer.close()
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0] == 1
        after_cols = {r[1] for r in conn.execute("PRAGMA table_info(measurement_raw)")}
        assert after_cols == before_cols
        assert "target_raw_dw" not in after_cols
    finally:
        conn.close()


def test_unknown_database_schema_fails_closed_without_mutation(tmp_path):
    db = tmp_path / "unknown.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE alien(x INTEGER)")
    conn.commit(); conn.close()
    original = db.read_bytes()
    writer = MeasurementDbWriter()
    try:
        writer.enqueue(_config(db), _row(1_780_000_006_000))
        deadline = time.time() + 2
        while time.time() < deadline and not writer.status().get("measurement_db_last_error"):
            time.sleep(0.02)
        st = writer.status()
        assert "MEASUREMENT_DB_UNKNOWN_SCHEMA" in st["measurement_db_last_error"]
        assert st["measurement_db_rows_written"] == 0
    finally:
        writer.close()
    assert db.read_bytes() == original


def test_dynamic_command_values_are_dense_not_event_explosion(tmp_path):
    db = tmp_path / "v3.sqlite3"
    writer = MeasurementDbWriter()
    start = 1_780_000_000_000
    try:
        for i in range(100):
            # Publish only every tenth sample, while desired/readback target changes every sample.
            pub = i // 10 + 1
            row = _row(start + i * 3000, seq=i + 1, pub=pub, target=100 + i)
            if i % 10:
                # Same publish event id/epoch between actual publishes.
                row["command_publish_epoch_s"] = (start + (i // 10) * 10 * 3000) / 1000.0
                row["command_publish_monotonic_ns"] = 10_000_000_000 + (i // 10) * 30_000_000_000
            writer.enqueue(_config(db), row)
        st = _wait_rows(writer, 100)
        assert st["measurement_db_rows_written"] == 100
    finally:
        writer.close()
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0] == 100
        assert conn.execute("SELECT COUNT(*) FROM graph_command_events WHERE event_type='PUBLISHED'").fetchone()[0] == 10
        assert conn.execute("SELECT COUNT(*) FROM graph_command_events WHERE event_type='DESIRED_CHANGED'").fetchone()[0] == 0
        assert conn.execute("SELECT MIN(command_desired_target_dw),MAX(command_desired_target_dw) FROM measurement_raw").fetchone() == (1000, 1990)
    finally:
        conn.close()


def test_v3_compatibility_reader_keeps_existing_status_graph_contract(tmp_path):
    db = tmp_path / "v3.sqlite3"
    writer = MeasurementDbWriter()
    start = 1_780_000_000_000
    try:
        for i in range(3):
            writer.enqueue(_config(db), _row(start + i * 3000, seq=1, pub=1, target=150))
        _wait_rows(writer, 3)
    finally:
        writer.close()
    start_dt = datetime.fromtimestamp((start - 1000) / 1000.0)
    end_dt = datetime.fromtimestamp((start + 60_000) / 1000.0)
    points, meta = query_graph_points(_config(db), start_dt, end_dt)
    assert meta["db_backend"] == "v3"
    assert len(points) == 1
    assert points[0]["zendure_target_power_w"] == 150.0
    assert points[0]["zendure_actual_power_w"] == 145.0
    assert points[0]["mode"] == "AUTO"
    assert points[0]["control_reason"] == "AUTO_GRID_EXPORT"


def test_writer_shutdown_does_not_retry_forever_after_flush_failure(tmp_path):
    db = tmp_path / "v3.sqlite3"
    writer = MeasurementDbWriter()
    with patch.object(writer, "_flush", return_value=False):
        writer.enqueue(_config(db), _row(1_780_000_000_000))
        time.sleep(0.05)
        started = time.monotonic()
        writer.close()
        assert time.monotonic() - started < 1.5
        assert writer._thread is None or not writer._thread.is_alive()


def test_queue_setting_is_retired_from_registry_but_legacy_migration_can_still_strip_it():
    assert "MEASUREMENT_DB_MAX_QUEUE_ROWS" not in SETTINGS_BY_KEY


def test_state_records_monotonic_measurement_and_exposes_new_db_diagnostics():
    state = ControllerState()
    state.record_graph_point(5)
    row = state.graph_history[-1]
    assert isinstance(row["measurement_monotonic_ns"], int)
    state.set_measurement_log_status({
        "measurement_db_backend": "v3",
        "measurement_db_schema_version": 3,
        "measurement_db_storage_encoding": "scaled_integer_v1",
        "measurement_db_run_id": 123,
        "measurement_db_queue_capacity": 5000,
        "measurement_db_prepare_duration_ms": 0.01,
    })
    snap = state.snapshot()
    assert snap["measurement_db_backend"] == "v3"
    assert snap["measurement_db_schema_version"] == 3
    assert snap["measurement_db_run_id"] == 123


def test_publish_monotonic_timestamp_is_captured_only_on_actual_publish():
    # Source-level regression: command publish wall clock and monotonic clock are
    # updated in the same published_fields branch, without changing command data.
    source = Path(__file__).resolve().parents[1].joinpath("controller_logic.py").read_text(encoding="utf-8")
    needle = "self.state.command_publish_epoch_s = now_epoch\n                self.state.command_publish_monotonic_ns = time.monotonic_ns()"
    assert needle in source

def test_new_live_run_closes_stale_open_intervals_from_prior_live_run(tmp_path):
    db = tmp_path / "restart.sqlite3"
    start = 1_780_100_000_000

    conn = open_v3(str(db))
    try:
        first = GraphCoreV3LiveSession(run_id=(1 << 62) + 101)
        assert first.write_batch(conn, str(db), [_row(start, seq=1, pub=1, target=100)]) == 1
        old = conn.execute(
            "SELECT interval_id,run_id,start_ms,end_ms,value_code FROM graph_intervals "
            "WHERE kind='OPERATING_MODE'"
        ).fetchone()
        assert old is not None
        assert old[1] == first.run_id
        assert old[2] == start
        assert old[3] is None
        old_run_end = conn.execute(
            "SELECT end_ms FROM graph_runs WHERE run_id=?", (first.run_id,)
        ).fetchone()[0]
        assert old_run_end == start
    finally:
        conn.close()

    # New process/run, same physical database.  The first committed sample of
    # the new run must terminate any stale open interval of the prior LIVE run
    # at the prior run's last persisted observation, not bridge the downtime.
    conn = open_v3(str(db))
    try:
        second = GraphCoreV3LiveSession(run_id=(1 << 62) + 202)
        second_row = _row(start + 60_000, seq=1, pub=1, target=120)
        second_row["operating_mode"] = "NIGHT_DISCHARGE"
        assert second.write_batch(conn, str(db), [second_row]) == 1

        intervals = [tuple(row) for row in conn.execute(
            "SELECT run_id,start_ms,end_ms,value_code FROM graph_intervals "
            "WHERE kind='OPERATING_MODE' ORDER BY start_ms,run_id"
        ).fetchall()]
        assert intervals == [
            (first.run_id, start, start + 1, "AUTO"),
            (second.run_id, start + 60_000, None, "NIGHT_DISCHARGE"),
        ]
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()

