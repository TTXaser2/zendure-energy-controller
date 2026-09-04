#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reproducible REAL-vs-scaled-INTEGER benchmark for Graph-Core V3."""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Sequence

SCALE = 10
SERIES = (
    "grid", "raw_grid", "control_grid", "control_grid_smoothed", "pv", "house", "zendure", "zendure_soc",
    "primary_power", "primary_soc", "target_raw", "target_limited", "target_filtered", "target_step", "target_final",
)


def _create(path: Path, integer: bool) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    typ = "INTEGER" if integer else "REAL"
    cols = ",".join(f"{name} {typ}" for name in SERIES)
    conn.execute(f"CREATE TABLE measurement_raw(ts_ms INTEGER PRIMARY KEY, quality_flags INTEGER NOT NULL, {cols})")
    return conn


def _value(row: int, idx: int) -> float:
    # Deterministic mixed household/commercial-scale signal. Peaks comfortably
    # cover a 30 kWp installation and include larger values to verify range.
    base = math.sin((row + idx * 17) / 137.0) * (28000.0 + idx * 1500.0)
    return round(base + ((row * (idx + 3)) % 1800) - 900.0, 1)


def _rows(count: int, integer: bool):
    start = 1_780_000_000_000
    for row in range(count):
        vals = [_value(row, idx) for idx, _ in enumerate(SERIES)]
        # SOC columns use a realistic bounded value instead of power-shaped data.
        vals[7] = round(50.0 + 45.0 * math.sin(row / 5000.0), 1)
        vals[9] = round(55.0 + 40.0 * math.sin(row / 7000.0), 1)
        if integer:
            vals = [int(round(value * SCALE)) for value in vals]
        yield (start + row * 3000, 255, *vals)


def _timed_query(conn: sqlite3.Connection, start_ms: int, end_ms: int, repetitions: int) -> float:
    durations: List[float] = []
    sql = "SELECT ts_ms,grid,target_final,zendure,zendure_soc FROM measurement_raw WHERE ts_ms BETWEEN ? AND ? ORDER BY ts_ms"
    # Warm the SQLite/page-cache path once before measuring.  This benchmark is
    # used for an engineering comparison, not as a cold-start latency test.
    # Without a warm-up, a tiny 10k-row unit-test invocation can be dominated by
    # unrelated scheduler/filesystem jitter and yield a false regression.
    list(conn.execute(sql, (start_ms, end_ms)))
    for _ in range(max(1, repetitions)):
        t0 = time.perf_counter_ns()
        list(conn.execute(sql, (start_ms, end_ms)))
        durations.append((time.perf_counter_ns() - t0) / 1_000_000.0)
    return round(statistics.median(durations), 3)


def run_one(path: Path, *, integer: bool, rows: int, repetitions: int) -> Dict[str, float]:
    conn = _create(path, integer)
    columns = "ts_ms,quality_flags," + ",".join(SERIES)
    placeholders = ",".join("?" for _ in range(2 + len(SERIES)))
    t0 = time.perf_counter()
    conn.executemany(f"INSERT INTO measurement_raw({columns}) VALUES({placeholders})", _rows(rows, integer))
    conn.commit()
    write_s = time.perf_counter() - t0
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db_bytes = path.stat().st_size
    start = 1_780_000_000_000
    # At 3 s/sample: 24 h = 28,800 rows; 48 h = 57,600 rows.
    q24 = _timed_query(conn, start, start + min(rows - 1, 28_799) * 3000, repetitions)
    q48 = _timed_query(conn, start, start + min(rows - 1, 57_599) * 3000, repetitions)
    plan = conn.execute(
        "EXPLAIN QUERY PLAN SELECT ts_ms,grid FROM measurement_raw WHERE ts_ms BETWEEN ? AND ? ORDER BY ts_ms",
        (start, start + 86_400_000),
    ).fetchall()
    conn.close()
    return {
        "db_bytes": db_bytes,
        "bytes_per_row": round(db_bytes / max(rows, 1), 3),
        "write_seconds": round(write_s, 3),
        "query_24h_median_ms": q24,
        "query_48h_median_ms": q48,
        "query_uses_integer_primary_key": 1 if any("INTEGER PRIMARY KEY" in str(item) for item in plan) else 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100000)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--dir", default="")
    args = parser.parse_args(argv)
    if args.dir:
        work = Path(args.dir).resolve()
        work.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        temp = tempfile.TemporaryDirectory(prefix="zec-v14-v3-bench-")
        work = Path(temp.name)
        cleanup = True
    real = run_one(work / "real.sqlite3", integer=False, rows=args.rows, repetitions=args.repetitions)
    integer = run_one(work / "integer.sqlite3", integer=True, rows=args.rows, repetitions=args.repetitions)
    result = {
        "rows": args.rows,
        "scale": SCALE,
        "real": real,
        "scaled_integer": integer,
        "integer_db_reduction_percent": round((1.0 - integer["db_bytes"] / real["db_bytes"]) * 100.0, 2),
        "integer_selected_if_no_regression": bool(
            integer["db_bytes"] < real["db_bytes"]
            and integer["query_24h_median_ms"] <= real["query_24h_median_ms"] * 1.25
            and integer["query_48h_median_ms"] <= real["query_48h_median_ms"] * 1.25
        ),
        "workdir": str(work) if not cleanup else "temporary",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if cleanup:
        temp.cleanup()
    return 0 if result["integer_selected_if_no_regression"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
