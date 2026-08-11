#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Idempotent V4-only backfill of graph_config_timeline.

Reads historical V4 CSV/CSV.GZ and zec_config_snapshots.json read-only. It never
modifies config.json, Last-Good metadata, controller/device state or V3 archives.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_config_timeline import backfill_entries, ensure_graph_config_schema, load_snapshot_map
from measurement_db import resolve_measurement_db_path


def _open_text(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def _iter_v4_rows(path: Path) -> Iterator[Tuple[int, str]]:
    try:
        with _open_text(path) as handle:
            sample = handle.read(8192)
            handle.seek(0)
            delimiter = ";" if sample.count(";") >= sample.count(",") else ","
            reader = csv.DictReader(handle, delimiter=delimiter)
            fields = set(reader.fieldnames or ())
            # V4 identity: both fields are part of the V4 contract. Historical V3
            # files do not acquire a runtime path merely by being scanned here.
            if "config_control_hash" not in fields or "measurement_epoch_ms" not in fields:
                return
            for row in reader:
                digest = str(row.get("config_control_hash") or "").strip()
                raw_ts = str(row.get("measurement_epoch_ms") or "").strip()
                if not digest or not raw_ts:
                    continue
                try:
                    yield int(float(raw_ts)), digest
                except Exception:
                    continue
    except (OSError, UnicodeError, csv.Error):
        return


def _candidate_dirs(config: Dict[str, Any], explicit: Iterable[str]) -> List[Path]:
    result = []
    for value in explicit:
        if value:
            result.append(Path(value).resolve())
    for key in ("MEASUREMENT_LOG_DIR", "MEASUREMENT_LOG_FALLBACK_DIR"):
        value = str(config.get(key) or "").strip()
        if value:
            result.append(Path(value).resolve())
    try:
        db_dir = Path(resolve_measurement_db_path(config)).resolve().parent
        result.append(db_dir)
    except Exception:
        pass
    unique = []
    seen = set()
    for path in result:
        text = str(path)
        if text not in seen and path.exists() and path.is_dir():
            seen.add(text)
            unique.append(path)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill ZEC V13 historical graph config timeline from Measurement V4")
    parser.add_argument("--config", default="/opt/zendure-controller/config.json")
    parser.add_argument("--db", default="")
    parser.add_argument("--measurement-dir", action="append", default=[])
    args = parser.parse_args()

    try:
        with open(args.config, "r", encoding="utf-8") as handle:
            config = json.load(handle)
        if not isinstance(config, dict):
            raise ValueError("CONFIG_ROOT_NOT_OBJECT")
    except FileNotFoundError:
        print(json.dumps({"status": "skipped", "reason": "CONFIG_NOT_FOUND", "config": args.config}, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": "CONFIG_READ_FAILED", "error": str(exc)}, sort_keys=True))
        return 2

    db_path = os.path.abspath(args.db or resolve_measurement_db_path(config))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    dirs = _candidate_dirs(config, args.measurement_dir)
    snapshots: Dict[str, Dict[str, Any]] = {}
    files_scanned = 0
    v4_files = 0
    v4_rows_seen = 0
    staged_transitions = 0

    # Use a TEMP SQLite stage instead of retaining historical measurement rows in
    # RAM. Only per-file hash transitions are staged; the final ORDER BY gives a
    # globally chronological stream to the idempotent timeline writer.
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        ensure_graph_config_schema(conn)
        conn.execute("CREATE TEMP TABLE graph_config_backfill_stage(effective_from_ms INTEGER NOT NULL, config_control_hash TEXT NOT NULL)")
        for directory in dirs:
            snapshots.update(load_snapshot_map(str(directory / "zec_config_snapshots.json")))
            for pattern in ("*.csv", "*.csv.gz"):
                for path in sorted(directory.glob(pattern)):
                    files_scanned += 1
                    file_had_row = False
                    last_file_hash = None
                    for ts_ms, digest in _iter_v4_rows(path):
                        file_had_row = True
                        v4_rows_seen += 1
                        if digest == last_file_hash:
                            continue
                        conn.execute(
                            "INSERT INTO graph_config_backfill_stage(effective_from_ms,config_control_hash) VALUES(?,?)",
                            (int(ts_ms), str(digest)),
                        )
                        staged_transitions += 1
                        last_file_hash = digest
                    if file_had_row:
                        v4_files += 1

        ordered_rows = conn.execute(
            "SELECT effective_from_ms,config_control_hash FROM graph_config_backfill_stage ORDER BY effective_from_ms ASC,rowid ASC"
        )
        result = backfill_entries(conn, ordered_rows, snapshots, presorted=True)
        conn.execute(
            "INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('graph_config_backfill_completed_at',?)",
            (datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('graph_config_backfill_source','measurement_v4')"
        )
        conn.commit()
    finally:
        conn.close()

    output = {
        "status": "ok",
        "db_path": db_path,
        "directories": [str(path) for path in dirs],
        "files_scanned": files_scanned,
        "v4_files_with_rows": v4_files,
        "v4_rows_seen": v4_rows_seen,
        "staged_hash_transitions": staged_transitions,
        "snapshot_count": len(snapshots),
        **result,
    }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
