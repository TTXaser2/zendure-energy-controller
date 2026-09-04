#!/usr/bin/env python3
"""WP4 entity/topology persistence + query benchmark.

Synthetic workload only. It intentionally compares the same 48 h system data
with and without two authoritative physical Zendure-unit streams so the
incremental storage cost of instance awareness is visible.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import tempfile
import time
import tracemalloc
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_core_v3 import connect_graph_core
from graph_core_v3_live import GraphCoreV3LiveSession
from graph_query_service import GraphQueryService


def row(ts_ms: int, cycle: int, *, physical: bool) -> dict:
    base = {
        "epoch_s": ts_ms / 1000.0,
        "cycle_id": cycle,
        "measurement_monotonic_ns": 10_000_000_000 + cycle * 3_000_000_000,
        "grid_power_w": 120.0 + (cycle % 17),
        "raw_grid_power_w": 121.0 + (cycle % 17),
        "grid_power_valid": True,
        "zendure_actual_power_w": 95.0,
        "actual_zendure_power_valid": True,
        "zendure_soc_percent": 55.0 + (cycle % 20) / 10.0,
        "soc_valid": True,
        "second_battery_power_w": 200.0,
        "second_battery_soc_percent": 70.0,
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
        "command_desired_sequence_id": cycle,
        "command_desired_intent": "CHARGE",
        "command_desired_smart_mode": 1,
        "command_desired_ac_mode": "input",
        "command_desired_input_limit_w": 100.0,
        "command_desired_output_limit_w": 0.0,
        "command_desired_signed_target_w": 100.0,
        "command_publish_event_id": 1,
        "command_publish_epoch_s": 1_781_100_000.0,
        "command_publish_monotonic_ns": 9_500_000_000,
        "zendure_command_smart_mode": 1,
        "zendure_command_ac_mode": "input",
        "zendure_command_input_limit_w": 100.0,
        "zendure_command_output_limit_w": 0.0,
        "command_readback_matches_desired": 1,
        "command_resync_count": 0,
        "command_neutralization_episode_id": 0,
        "_graph_entity_config": {
            "zendure_device_id": "BENCH-CONTROLLED",
            "primary_display_name": "Bench Primary",
            "primary_source_profile": "evcc_standard",
            "primary_integration_enabled": True,
        },
    }
    if physical:
        base["zendure_unit_count"] = 2
        base["zendure_units_json"] = json.dumps([
            {
                "device_id": "BENCH-A",
                "display_name": "Bench A",
                "actual_power_w": 60.0,
                "power_valid": 1,
                "soc_percent": 52.0,
                "soc_valid": 1,
                "target_w": 65.0,
                "target_valid": 1,
                "readback_target_w": 64.0,
                "readback_valid": 1,
            },
            {
                "device_id": "BENCH-B",
                "display_name": "Bench B",
                "actual_power_w": 35.0,
                "power_valid": 1,
                "soc_percent": 58.0,
                "soc_valid": 1,
                "target_w": 35.0,
                "target_valid": 1,
                "readback_target_w": 34.0,
                "readback_valid": 1,
            },
        ], separators=(",", ":"))
    else:
        base["zendure_unit_count"] = 1
        base["zendure_units_json"] = '[{"unit_id":"primary","actual_power_w":95.0,"soc_percent":55.0,"target_w":100.0}]'
    return base


def build(path: Path, samples: int, *, physical: bool, batch_size: int) -> dict:
    start_ms = 1_781_100_000_000
    conn = connect_graph_core(path)
    session = GraphCoreV3LiveSession(run_id=(1 << 62) + (501 if physical else 500))
    started = time.perf_counter()
    try:
        for begin in range(0, samples, batch_size):
            stop = min(samples, begin + batch_size)
            rows = [row(start_ms + i * 3000, i + 1, physical=physical) for i in range(begin, stop)]
            session.write_batch(conn, str(path), rows)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {
            "system_raw": conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0],
            "system_1min": conn.execute("SELECT COUNT(*) FROM measurement_1min").fetchone()[0],
            "entities": conn.execute("SELECT COUNT(*) FROM graph_entities").fetchone()[0],
            "entity_raw": conn.execute("SELECT COUNT(*) FROM measurement_entity_raw").fetchone()[0],
            "entity_1min": conn.execute("SELECT COUNT(*) FROM measurement_entity_1min").fetchone()[0],
            "topology": conn.execute("SELECT COUNT(*) FROM graph_topology_timeline").fetchone()[0],
            "command_events": conn.execute("SELECT COUNT(*) FROM graph_command_events").fetchone()[0],
        }
    finally:
        conn.close()
    return {
        "duration_s": round(time.perf_counter() - started, 3),
        "db_bytes": path.stat().st_size,
        "integrity": integrity,
        "counts": counts,
        "start_ms": start_ms,
        "end_ms": start_ms + (samples - 1) * 3000,
    }


def median_ms(fn, repeats=15):
    values = []
    result = None
    for _ in range(repeats):
        started = time.perf_counter()
        result = fn()
        values.append((time.perf_counter() - started) * 1000.0)
    return round(statistics.median(values), 3), result


def query_stats(path: Path, start_ms: int, end_ms: int, *, physical: bool) -> dict:
    service = GraphQueryService(cache_max_entries=0)
    entities_ms, entities = median_ms(lambda: service.entities(str(path)))
    coverage_ms, coverage = median_ms(lambda: service.entity_coverage(str(path)))
    controlled_ms, controlled = median_ms(lambda: service.entity_overview(
        str(path), start_ms, end_ms, stable_ids=["storage:controlled"], resolution="1min"
    ))
    primary_ms, primary = median_ms(lambda: service.entity_overview(
        str(path), start_ms, end_ms, stable_ids=["storage:primary"], resolution="1min"
    ))
    physical_ms = None
    physical_json_bytes = None
    tracemalloc_peak = None
    if physical:
        unit = next(x for x in entities["entities"] if x.get("source_identity") == "BENCH-A")
        tracemalloc.start()
        physical_ms, payload = median_ms(lambda: service.entity_overview(
            str(path), start_ms, end_ms, stable_ids=[unit["stable_id"]], resolution="1min"
        ))
        _current, tracemalloc_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        physical_json_bytes = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return {
        "entities_median_ms": entities_ms,
        "coverage_median_ms": coverage_ms,
        "controlled_48h_1min_median_ms": controlled_ms,
        "primary_48h_1min_median_ms": primary_ms,
        "physical_unit_48h_1min_median_ms": physical_ms,
        "physical_unit_48h_json_bytes": physical_json_bytes,
        "physical_unit_query_tracemalloc_peak_bytes": tracemalloc_peak,
        "entity_count": len(entities["entities"]),
        "coverage_entity_count": len(coverage["entities"]),
        "controlled_points": len(controlled["entities"]["storage:controlled"]["timestamps_ms"]),
        "primary_points": len(primary["entities"]["storage:primary"]["timestamps_ms"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=57_600)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="zec_wp4_entity_bench_") as td:
        td_path = Path(td)
        logical_db = td_path / "logical.sqlite3"
        physical_db = td_path / "physical2.sqlite3"
        logical = build(logical_db, args.samples, physical=False, batch_size=args.batch_size)
        physical = build(physical_db, args.samples, physical=True, batch_size=args.batch_size)
        logical["queries"] = query_stats(logical_db, logical["start_ms"], logical["end_ms"], physical=False)
        physical["queries"] = query_stats(physical_db, physical["start_ms"], physical["end_ms"], physical=True)
        extra = physical["db_bytes"] - logical["db_bytes"]
        report = {
            "samples": args.samples,
            "sample_interval_s": 3,
            "hours": round(args.samples * 3 / 3600.0, 3),
            "logical_only": logical,
            "two_physical_units": physical,
            "incremental_physical_storage_bytes": extra,
            "incremental_bytes_per_entity_raw_sample": round(extra / max(1, 2 * args.samples), 3),
            "note": "Synthetic benchmark; incremental bytes include entity raw, 1min aggregates, coverage and topology metadata.",
        }
        text = json.dumps(report, indent=2, sort_keys=True)
        print(text)
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
