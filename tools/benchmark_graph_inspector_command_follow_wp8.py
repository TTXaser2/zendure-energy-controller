#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reproducible WP8 inspector / command-follow benchmark."""
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
    with tempfile.TemporaryDirectory(prefix="zec-v14-wp8-inspector-") as td:
        db = Path(td) / "graph.sqlite3"
        conn = connect_graph_core(db)
        session = GraphCoreV3LiveSession(run_id=(1 << 62) + 1008)
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
        catalog_ids = [item["series_id"] for item in service.catalog()["series"]]
        # Use a command publication on a stable 120-cycle publication boundary near 12 h.
        target_index = min(max(120, (12 * 60 * 60 // 3) // 120 * 120), args.samples - 1)
        target_ms = start + target_index * 3000
        inspector_ms, inspector_payload = median_ms(
            lambda: service.inspector(str(db), target_ms, series_ids=catalog_ids, tolerance_ms=10_000),
            args.repetitions,
        )
        linked_event_id = int(inspector_payload["correlation"]["linked_event_id"])
        follow_ms, follow_payload = median_ms(
            lambda: service.command_follow(
                str(db), event_id=linked_event_id, before_ms=15_000, after_ms=180_000
            ),
            args.repetitions,
        )
        result = {
            "samples": args.samples,
            "sample_interval_s": 3,
            "span_hours": round(args.samples * 3 / 3600, 3),
            "series_count": len(catalog_ids),
            "repetitions": args.repetitions,
            "inspector_median_ms": inspector_ms,
            "inspector_contract_version": inspector_payload["contract_version"],
            "inspector_entity_count": len(inspector_payload.get("entities") or []),
            "command_follow_median_ms": follow_ms,
            "command_follow_contract_version": follow_payload["contract_version"],
            "command_follow_timeline_rows": len(follow_payload["timeline"]["timestamps_ms"]),
            "command_follow_evidence_quality": follow_payload["evidence_quality"],
            "system_effect_status": follow_payload["stages"]["system_effect"]["status"],
            "publish_is_effectiveness_proof": follow_payload["meta"]["effectiveness_from_publish_alone"],
            "direction_is_effectiveness_proof": follow_payload["meta"]["effectiveness_from_direction_alone"],
        }
        text = json.dumps(result, indent=2, sort_keys=True)
        print(text)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
