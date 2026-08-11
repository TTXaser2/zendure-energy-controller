import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from config_manager import DEFAULT_CONFIG
from csv_logger import compute_config_control_hash
from graph_config_timeline import (
    backfill_entries, build_day_segments, ensure_graph_config_schema, record_runtime_config, query_timeline_rows,
)
from measurement_db import ensure_schema, write_points
import web_ui


class V13GraphConfigTimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "measurements.sqlite3"
        self.cfg = {"MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_DB_PATH": str(self.db)}
        conn = sqlite3.connect(self.db); ensure_graph_config_schema(conn); conn.commit(); conn.close()
        self.day = datetime(2026, 8, 10, 0, 0, 0)

    @staticmethod
    def params(max_soc=99, start="21:30"):
        h, m = [int(x) for x in start.split(":")]
        return {"MIN_SOC_PERCENT": 10, "MAX_SOC_PERCENT": max_soc, "NIGHT_DISCHARGE_STOP_SOC_PERCENT": 20,
                "NIGHT_START_HOUR": h, "NIGHT_START_MINUTE": m, "NIGHT_END_HOUR": 5, "NIGHT_END_MINUTE": 30}

    def test_historical_changes_are_segmented_and_idempotent(self):
        t0 = int(self.day.timestamp() * 1000)
        t1 = int((self.day + timedelta(hours=17)).timestamp() * 1000)
        snapshots = {"a": self.params(99, "21:30"), "b": self.params(80, "23:00")}
        conn = sqlite3.connect(self.db)
        first = backfill_entries(conn, [(t0, "a"), (t0 + 1000, "a"), (t1, "b")], snapshots)
        second = backfill_entries(conn, [(t0, "a"), (t0 + 1000, "a"), (t1, "b")], snapshots)
        conn.close()
        self.assertEqual(2, first["hash_transitions_seen"])
        self.assertEqual(0, second["entries_inserted"])
        segments, meta = build_day_segments(self.cfg, self.day, self.day + timedelta(days=1))
        self.assertEqual(2, len(segments))
        self.assertEqual(99, segments[0]["max_soc"])
        self.assertEqual(80, segments[1]["max_soc"])
        self.assertEqual("21:30", segments[0]["night_start"])
        self.assertEqual("23:00", segments[1]["night_start"])
        self.assertEqual(17 * 60, segments[1]["start_minute"])
        self.assertEqual(0, meta["unknown_segments"])

    def test_missing_snapshot_is_unknown_never_current_config_fallback(self):
        t0 = int(self.day.timestamp() * 1000)
        conn = sqlite3.connect(self.db); backfill_entries(conn, [(t0, "missing")], {}); conn.close()
        current = self.params(77, "22:00")
        segments, _ = build_day_segments(self.cfg, self.day, self.day + timedelta(days=1), current_effective_config=None)
        self.assertFalse(segments[0]["known"])
        self.assertIsNone(segments[0]["max_soc"])
        self.assertNotEqual(77, segments[0]["max_soc"])

    def test_runtime_writer_creates_timeline_only_on_hash_change(self):
        conn = sqlite3.connect(self.db)
        ensure_schema(conn)
        base = int(self.day.timestamp() * 1000)
        p1 = {"ts_ms": base, "config_control_hash": "a", "_graph_config_overlay": {"min_soc": 10, "max_soc": 99, "reserve_soc": 20, "night_start": "21:30", "night_end": "05:30"}}
        p2 = dict(p1, ts_ms=base + 1000)
        p3 = dict(p1, ts_ms=base + 2000, config_control_hash="b", _graph_config_overlay={"min_soc": 10, "max_soc": 80, "reserve_soc": 20, "night_start": "23:00", "night_end": "05:30"})
        self.assertEqual(3, write_points(conn, [p1, p2, p3]))
        rows = conn.execute("SELECT effective_from_ms,config_control_hash FROM graph_config_timeline ORDER BY effective_from_ms").fetchall()
        conn.close()
        self.assertEqual([(base, "a"), (base + 2000, "b")], rows)

    def test_soc_graph_cache_reuses_points_but_refreshes_current_config_overlay(self):
        cfg_a = dict(DEFAULT_CONFIG)
        cfg_a.update({"MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_DB_PATH": str(self.db), "MAX_SOC_PERCENT": 99})
        cfg_b = dict(cfg_a); cfg_b["MAX_SOC_PERCENT"] = 80
        now = datetime.now()
        start = datetime.combine(now.date(), datetime.min.time())
        conn = sqlite3.connect(self.db)
        record_runtime_config(conn, int(start.timestamp() * 1000), cfg_a, compute_config_control_hash(cfg_a))
        conn.close()
        point = {"epoch_ms": int((start + timedelta(hours=1)).timestamp() * 1000), "soc": 50}
        snap = {"battery_soc": 50, "zendure_system_signed_power": 0, "current_mode": "AUTO"}
        with web_ui._storage_day_lock:
            web_ui._storage_day_cache.clear()
        with patch("web_ui.query_graph_points", return_value=([point], {"db_status": "ok"})) as qp, \
             patch("web_ui.query_measurement_date_range", return_value={"available_from": start.date().isoformat()}):
            first = web_ui.build_storage_soc_day_payload(cfg_a, snap, start.date().isoformat())
            second = web_ui.build_storage_soc_day_payload(cfg_b, snap, start.date().isoformat())
        self.assertEqual("rebuilt", first["cache_status"])
        self.assertEqual("hit", second["cache_status"])
        self.assertEqual(1, qp.call_count, "historical measurement points must stay cached")
        self.assertEqual(99, first["config_segments"][0]["max_soc"])
        self.assertEqual(80, second["config_segments"][-1]["max_soc"], "live current-day overlay must refresh on cache hit")

    def test_historical_soc_graph_cache_never_relabels_old_day_with_current_config(self):
        historical_day = datetime.now() - timedelta(days=2)
        historical_day = datetime.combine(historical_day.date(), datetime.min.time())
        cfg_a = dict(DEFAULT_CONFIG)
        cfg_a.update({"MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_DB_PATH": str(self.db), "MAX_SOC_PERCENT": 99})
        cfg_b = dict(cfg_a); cfg_b["MAX_SOC_PERCENT"] = 80
        conn = sqlite3.connect(self.db)
        record_runtime_config(conn, int(historical_day.timestamp() * 1000), cfg_a, compute_config_control_hash(cfg_a))
        conn.close()
        point = {"epoch_ms": int((historical_day + timedelta(hours=1)).timestamp() * 1000), "soc": 50}
        snap = {"battery_soc": 50, "zendure_system_signed_power": 0, "current_mode": "AUTO"}
        with web_ui._storage_day_lock:
            web_ui._storage_day_cache.clear()
        with patch("web_ui.query_graph_points", return_value=([point], {"db_status": "ok"})) as qp, \
             patch("web_ui.query_measurement_date_range", return_value={"available_from": historical_day.date().isoformat()}):
            first = web_ui.build_storage_soc_day_payload(cfg_a, snap, historical_day.date().isoformat())
            second = web_ui.build_storage_soc_day_payload(cfg_b, snap, historical_day.date().isoformat())
        self.assertEqual("hit", second["cache_status"])
        self.assertEqual(1, qp.call_count)
        self.assertEqual(99, first["config_segments"][0]["max_soc"])
        self.assertEqual(99, second["config_segments"][0]["max_soc"])
        self.assertNotIn(80, [seg.get("max_soc") for seg in second["config_segments"]])



if __name__ == "__main__":
    unittest.main()
