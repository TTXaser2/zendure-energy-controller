#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reproducible WP9 episode-trigger / comparison benchmark."""
from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_core_v3 import connect_graph_core
from graph_core_v3_live import GraphCoreV3LiveSession
from graph_query_service import GraphQueryService
from tools.benchmark_graph_query_v3 import row


def median_ms(fn, repetitions: int):
    values = []
    result = None
    for _ in range(repetitions):
        t0 = time.perf_counter_ns()
        result = fn()
        values.append((time.perf_counter_ns() - t0) / 1e6)
    return round(statistics.median(values), 3), result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=57_600)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    start = 1_780_000_000_000
    with tempfile.TemporaryDirectory(prefix="zec-v14-wp9-compare-") as td:
        db = Path(td) / "graph.sqlite3"
        conn = connect_graph_core(db)
        session = GraphCoreV3LiveSession(run_id=(1 << 62) + 1009)
        batch = []
        for i in range(args.samples):
            batch.append(row(start + i * 3000, i))
            if len(batch) >= 500:
                session.write_batch(conn, str(db), batch)
                batch = []
        if batch:
            session.write_batch(conn, str(db), batch)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()

        service = GraphQueryService(cache_max_entries=0)
        all_ids = [item["series_id"] for item in service.catalog()["series"]]
        a_ms = start + 12 * 60 * 60_000
        b_ms = start + 36 * 60 * 60_000
        a_inspector = service.inspector(str(db), a_ms, series_ids=all_ids, tolerance_ms=10_000)
        b_inspector = service.inspector(str(db), b_ms, series_ids=all_ids, tolerance_ms=10_000)
        trigger_a = f"event:{int(a_inspector['correlation']['linked_event_id'])}"
        trigger_b = f"event:{int(b_inspector['correlation']['linked_event_id'])}"

        trigger_ms, trigger_payload = median_ms(
            lambda: service.episode_triggers(str(db), start + 11 * 60 * 60_000, start + 13 * 60 * 60_000, limit=500),
            args.repetitions,
        )
        compare_ms, compare_payload = median_ms(
            lambda: service.episode_comparison(
                str(db), trigger_a, trigger_b, before_ms=15 * 60_000, after_ms=45 * 60_000,
                series_ids=all_ids, resolution="highres",
            ),
            args.repetitions,
        )
        ep_a = compare_payload["episodes"]["a"]
        ep_b = compare_payload["episodes"]["b"]
        result = {
            "samples": args.samples,
            "sample_interval_s": 3,
            "span_hours": round(args.samples * 3 / 3600, 3),
            "series_count": len(all_ids),
            "repetitions": args.repetitions,
            "trigger_query_2h_median_ms": trigger_ms,
            "trigger_query_item_count": len(trigger_payload["items"]),
            "comparison_60min_pair_median_ms": compare_ms,
            "episode_a_rows": len(ep_a["overview"]["timestamps_ms"]),
            "episode_b_rows": len(ep_b["overview"]["timestamps_ms"]),
            "relative_t0_present_a": 0 in ep_a["overview"]["relative_timestamps_ms"],
            "relative_t0_present_b": 0 in ep_b["overview"]["relative_timestamps_ms"],
            "absolute_time_retained": compare_payload["alignment"]["absolute_time_retained"],
            "visual_similarity_is_causality_proof": compare_payload["alignment"]["visual_similarity_is_causality_proof"],
            "missing_series_are_not_imputed": compare_payload["meta"]["missing_series_are_not_imputed"],
        }
        text = json.dumps(result, indent=2, sort_keys=True)
        print(text)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
