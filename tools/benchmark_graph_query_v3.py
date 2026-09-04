#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reproducible WP3 Graph Query Service benchmark."""
from __future__ import annotations

import argparse
import json
import math
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


def row(ts_ms: int, i: int):
    grid = round(math.sin(i / 137.0) * 2500.0 + math.sin(i / 17.0) * 120.0, 1)
    target = round(max(-2100.0, min(2100.0, -grid * 0.75)), 1)
    return {
        "epoch_s": ts_ms / 1000.0,
        "cycle_id": i + 1,
        "measurement_monotonic_ns": 10_000_000_000 + i * 3_000_000_000,
        "grid_power_w": grid,
        "raw_grid_power_w": grid + 12.3,
        "grid_power_valid": True,
        "zendure_actual_power_w": target * 0.96,
        "actual_zendure_power_valid": True,
        "zendure_soc_percent": round(55 + 20 * math.sin(i / 7000.0), 1),
        "soc_valid": True,
        "second_battery_power_w": round(-grid * 0.2, 1),
        "second_battery_soc_percent": round(70 + 15 * math.sin(i / 9000.0), 1),
        "second_battery_data_valid": True,
        "target_raw_w": target + 80,
        "target_after_power_limit_w": target + 50,
        "target_after_smoothing_w": target + 25,
        "target_after_ramp_w": target + 10,
        "target_final_w": target,
        "target_final_reason": "AUTO_GRID_EXPORT" if target > 0 else "AUTO_GRID_IMPORT",
        "operating_mode": "AUTO",
        "control_intent": "CHARGE" if target > 0 else "DISCHARGE",
        "command_lifecycle_state": "TRACKING",
        "command_effect_category": "COMMAND_TARGET_TRACKING_EFFECTIVE",
        "command_desired_sequence_id": i + 1,
        "command_desired_intent": "CHARGE" if target > 0 else "DISCHARGE",
        "command_desired_smart_mode": 1,
        "command_desired_ac_mode": "input" if target >= 0 else "output",
        "command_desired_input_limit_w": max(target, 0),
        "command_desired_output_limit_w": max(-target, 0),
        "command_desired_signed_target_w": target,
        "command_publish_event_id": i // 120 + 1,
        "command_publish_epoch_s": (ts_ms - (i % 120) * 3000) / 1000.0,
        "command_publish_monotonic_ns": 10_000_000_000 + (i - i % 120) * 3_000_000_000,
        "zendure_command_smart_mode": 1,
        "zendure_command_ac_mode": "input" if target >= 0 else "output",
        "zendure_command_input_limit_w": max(target, 0),
        "zendure_command_output_limit_w": max(-target, 0),
        "command_readback_matches_desired": 1,
        "command_readback_mismatch_fields": "",
        "command_resync_count": 0,
        "command_neutralization_episode_id": 0,
        "zendure_unit_count": 1,
    }


def median_ms(fn, repetitions=5):
    values=[]
    result=None
    for _ in range(repetitions):
        t0=time.perf_counter_ns(); result=fn(); values.append((time.perf_counter_ns()-t0)/1e6)
    return round(statistics.median(values),3), result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=57600)
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--output', default='')
    args=parser.parse_args()
    start=1_780_000_000_000
    with tempfile.TemporaryDirectory(prefix='zec-v14-wp3-query-') as td:
        db=Path(td)/'graph.sqlite3'
        conn=connect_graph_core(db)
        session=GraphCoreV3LiveSession(run_id=(1<<62)+909)
        t0=time.perf_counter()
        batch=[]
        for i in range(args.samples):
            batch.append(row(start+i*3000,i))
            if len(batch)>=500:
                session.write_batch(conn,str(db),batch); batch=[]
        if batch: session.write_batch(conn,str(db),batch)
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        conn.close()
        build_s=time.perf_counter()-t0

        service=GraphQueryService(cache_max_entries=0)
        all_ids=[x['series_id'] for x in service.catalog()['series']]
        q30,_=median_ms(lambda: service.overview(str(db),start,start+30*60_000,series_ids=all_ids,include_context=True),args.repetitions)
        q24,_=median_ms(lambda: service.overview(str(db),start,start+24*60*60_000,series_ids=all_ids,include_context=True),args.repetitions)

        tracemalloc.start()
        q48,p48=median_ms(lambda: service.overview(str(db),start,start+48*60*60_000-1,series_ids=all_ids,include_context=True),args.repetitions)
        _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
        insp,_=median_ms(lambda: service.inspector(str(db),start+12*60*60_000,series_ids=all_ids),args.repetitions)
        cov,_=median_ms(lambda: service.coverage(str(db),series_ids=all_ids),args.repetitions)

        cached=GraphQueryService(cache_max_entries=4,cache_ttl_s=15)
        cached.overview(str(db),start,start+24*60*60_000,series_ids=all_ids,include_context=True)
        cache_ms,cache_payload=median_ms(lambda: cached.overview(str(db),start,start+24*60*60_000,series_ids=all_ids,include_context=True),args.repetitions)
        serialized=len(json.dumps(p48,separators=(',',':'),ensure_ascii=False).encode('utf-8'))
        result={
            'samples':args.samples,
            'sample_interval_s':3,
            'span_hours':round(args.samples*3/3600,3),
            'db_bytes':db.stat().st_size,
            'build_seconds':round(build_s,3),
            'series_count':len(all_ids),
            'query_30min_median_ms':q30,
            'query_24h_median_ms':q24,
            'query_48h_median_ms':q48,
            'inspector_median_ms':insp,
            'coverage_median_ms':cov,
            'cache_hit_24h_median_ms':cache_ms,
            'query_48h_tracemalloc_peak_bytes':peak,
            'query_48h_serialized_bytes':serialized,
            'query_48h_rows':len(p48['timestamps_ms']),
            'format':p48['format'],
            'resolution_48h':p48['resolution'],
            'cache_contract':{'max_entries':4,'ttl_s':15,'fingerprint':'db+wal'},
        }
        text=json.dumps(result,indent=2,sort_keys=True)
        print(text)
        if args.output: Path(args.output).write_text(text+'\n',encoding='utf-8')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
