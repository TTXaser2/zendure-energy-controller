#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Idempotent V4-only backfill of graph_config_timeline.

Historical V4 files and config snapshots are scanned read-only into a temporary
SQLite staging DB. Only the short final merge into the productive measurement DB
holds the shared cross-process maintenance lock.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, MutableMapping, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_config_timeline import backfill_entries, ensure_graph_config_schema, load_snapshot_map
from measurement_db import resolve_measurement_db_path
from measurement_db_maintenance import measurement_db_maintenance_lock


def _open_text(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="strict", newline="")
    return path.open("r", encoding="utf-8", errors="strict", newline="")


def _iter_clean_lines(path: Path, stats: MutableMapping[str, Any]) -> Iterator[str]:
    with _open_text(path) as handle:
        for line in handle:
            if "\x00" in line:
                count = line.count("\x00")
                stats["nul_characters_removed"] = int(stats.get("nul_characters_removed") or 0) + count
                line = line.replace("\x00", "")
            yield line


def _iter_v4_rows(path: Path, stats: MutableMapping[str, Any]) -> Iterator[Tuple[int, str]]:
    """Yield V4 hash/timestamp rows while reporting damaged sources explicitly."""
    try:
        with _open_text(path) as handle:
            sample = handle.read(8192).replace("\x00", "")
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","
        reader = csv.DictReader(_iter_clean_lines(path, stats), delimiter=delimiter)
        fields = set(reader.fieldnames or ())
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
                stats["invalid_v4_rows"] = int(stats.get("invalid_v4_rows") or 0) + 1
    except (OSError, UnicodeError, csv.Error) as exc:
        stats["read_error_files"] = int(stats.get("read_error_files") or 0) + 1
        problems = stats.setdefault("problem_files", [])
        if len(problems) < 100:
            problems.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
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
        result.append(Path(resolve_measurement_db_path(config)).resolve().parent)
    except Exception:
        pass
    unique: List[Path] = []
    seen = set()
    for path in result:
        text = str(path)
        if text not in seen and path.exists() and path.is_dir():
            seen.add(text)
            unique.append(path)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill ZEC historical graph config timeline from Measurement V4")
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
    scan_stats: Dict[str, Any] = {
        "nul_characters_removed": 0,
        "read_error_files": 0,
        "invalid_v4_rows": 0,
        "problem_files": [],
    }

    stage_fd, stage_path = tempfile.mkstemp(prefix="zec-graph-config-backfill-", suffix=".sqlite3")
    os.close(stage_fd)
    stage = sqlite3.connect(stage_path)
    result: Dict[str, int] = {"hash_transitions_seen": 0, "entries_inserted": 0, "unknown_snapshots": 0}
    try:
        stage.execute("CREATE TABLE stage(effective_from_ms INTEGER NOT NULL, config_control_hash TEXT NOT NULL)")
        for directory in dirs:
            snapshots.update(load_snapshot_map(str(directory / "zec_config_snapshots.json")))
            for pattern in ("*.csv", "*.csv.gz"):
                for path in sorted(directory.glob(pattern)):
                    files_scanned += 1
                    file_had_row = False
                    last_file_hash = None
                    for ts_ms, digest in _iter_v4_rows(path, scan_stats):
                        file_had_row = True
                        v4_rows_seen += 1
                        if digest == last_file_hash:
                            continue
                        stage.execute("INSERT INTO stage(effective_from_ms,config_control_hash) VALUES(?,?)", (int(ts_ms), str(digest)))
                        staged_transitions += 1
                        last_file_hash = digest
                    if file_had_row:
                        v4_files += 1
        stage.commit()

        # The main DB is touched only during this short, explicit merge window.
        with measurement_db_maintenance_lock(db_path, timeout_s=30.0):
            main = sqlite3.connect(db_path, timeout=5.0)
            try:
                ensure_graph_config_schema(main)
                ordered_rows = stage.execute(
                    "SELECT effective_from_ms,config_control_hash FROM stage ORDER BY effective_from_ms ASC,rowid ASC"
                )
                result = backfill_entries(main, ordered_rows, snapshots, presorted=True, commit=False)
                main.execute(
                    "INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('graph_config_backfill_completed_at',?)",
                    (datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),),
                )
                main.execute("INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('graph_config_backfill_source','measurement_v4')")
                main.commit()
            except Exception:
                try:
                    main.rollback()
                except Exception:
                    pass
                raise
            finally:
                main.close()
    finally:
        stage.close()
        try:
            os.unlink(stage_path)
        except FileNotFoundError:
            pass

    output = {
        "status": "ok",
        "db_path": db_path,
        "directories": [str(path) for path in dirs],
        "files_scanned": files_scanned,
        "v4_files_with_rows": v4_files,
        "v4_rows_seen": v4_rows_seen,
        "staged_hash_transitions": staged_transitions,
        "snapshot_count": len(snapshots),
        **scan_stats,
        **result,
    }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
