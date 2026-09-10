from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import web_ui
from graph_query_service import GraphQueryService

ROOT = Path(__file__).resolve().parents[1]


def test_status_day_query_binds_series_once_and_uses_sweep_mapping_contract():
    source = (ROOT / "graph_query_service.py").read_text(encoding="utf-8")
    body = source.split("    def storage_day_status(", 1)[1].split("    def evidence(", 1)[0]
    assert "series_values" in body
    assert "interval_values" in body
    assert "heapq.heappush" in body
    assert "values = list(series.get(series_id) or [])" not in body
    assert "for item in by_kind.get(kind, [])" not in body


def test_status_day_interval_mapping_preserves_latest_active_overlap_semantics(tmp_path):
    # Unit-level contract for the optimized mapping is exercised through a
    # minimal fake numeric/config query surface so overlapping legacy intervals
    # still resolve exactly like the V14.1.3 scan: latest active interval wins.
    service = GraphQueryService(cache_max_entries=0, cache_ttl_s=0)
    path = tmp_path / "graph.sqlite3"
    path.write_bytes(b"x")
    timestamps = [1000, 2000, 3000, 4000]
    numeric = {
        "timestamps_ms": timestamps,
        "series": {
            "zendure_actual_power_w": [10, 20, 30, 40],
            "zendure_soc_percent": [50, 51, 52, 53],
            "primary_soc_percent": [60, 61, 62, 63],
            "primary_power_w": [1, 2, 3, 4],
        },
    }

    class FakeConn:
        def execute(self, _sql, _args):
            class Rows:
                def fetchall(self_nonlocal):
                    return [
                        {"interval_id": 1, "kind": "OPERATING_MODE", "run_id": None, "entity_id": None, "start_ms": 0, "end_ms": 5000, "value_code": "AUTO", "source": "T", "quality": "OBSERVED"},
                        {"interval_id": 2, "kind": "OPERATING_MODE", "run_id": None, "entity_id": None, "start_ms": 2500, "end_ms": 3500, "value_code": "HOLD", "source": "T", "quality": "OBSERVED"},
                        {"interval_id": 3, "kind": "CONTROL_REASON", "run_id": None, "entity_id": None, "start_ms": 0, "end_ms": None, "value_code": "R1", "source": "T", "quality": "OBSERVED"},
                    ]
            return Rows()
        def close(self):
            pass

    with patch("graph_query_service._db_fingerprint", return_value=("fake",)), \
         patch("graph_query_service._query_numeric", return_value=numeric), \
         patch("graph_query_service._query_config", return_value=[]), \
         patch.object(service, "_open_v3", return_value=FakeConn()):
        payload = service.storage_day_status(str(path), 0, 5000, limit=10)

    assert [p["mode"] for p in payload["points"]] == ["AUTO", "AUTO", "HOLD", "AUTO"]
    assert [p["control_reason"] for p in payload["points"]] == ["R1", "R1", "R1", "R1"]


def test_status_day_outer_cache_keeps_multiple_recent_days():
    cfg = {"MEASUREMENT_DB_ENABLED": True, "STATUS_PRIMARY_STORAGE_PRESENT": False}
    snap = {"battery_soc": 50, "zendure_system_signed_power": 0, "current_mode": "AUTO"}
    base = datetime.combine((datetime.now() - timedelta(days=4)).date(), datetime.min.time())

    def fake_history(_cfg, day_start, _day_end, **_kwargs):
        return {
            "points": [{"minute": 60, "time": "01:00", "zendure_soc": 50}],
            "source": "graph_core_v3_1min",
            "runtime": {"read_mode": "V3_NATIVE"},
            "zendure_unit_count": 1,
            "unit_labels": ["Zendure"],
            "primary_storage_present": False,
            "available_from": base.date().isoformat(),
            "available_to": datetime.now().date().isoformat(),
            "config_segments": [],
            "config_timeline": {},
        }

    with web_ui._storage_day_lock:
        web_ui._storage_day_cache.clear()
        web_ui._storage_day_cache_entries.clear()
    with patch("web_ui.graph_history_runtime_status", return_value={"read_mode": "V3_NATIVE"}), \
         patch("web_ui.query_storage_day_history", side_effect=fake_history) as history:
        first = web_ui.build_storage_soc_day_payload(cfg, snap, base.date().isoformat())
        second_day = web_ui.build_storage_soc_day_payload(cfg, snap, (base + timedelta(days=1)).date().isoformat())
        first_again = web_ui.build_storage_soc_day_payload(cfg, snap, base.date().isoformat())

    assert first["cache_status"] == "rebuilt"
    assert second_day["cache_status"] == "rebuilt"
    assert first_again["cache_status"] == "hit"
    assert history.call_count == 2
    assert first_again["cache_entries"] == 2
