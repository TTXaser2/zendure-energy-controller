#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline V14 Graph-Core V3 rebuild from Measurement V4.

The tool is intentionally maintenance-window oriented: it creates a brand-new
SQLite database and never mutates the legacy V2 database. Measurement V4 is the
primary historical source. The legacy DB is optional and is used only to copy
validated graph_config_timeline rows for comparison/rollback continuity.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_config_timeline import backfill_entries, load_snapshot_map  # noqa: E402
from graph_core_v3 import (  # noqa: E402
    SYSTEM_SERIES,
    CommandEventBuilder,
    EntityPersistenceBuilder,
    RunBuilder,
    SparseStateBuilder,
    V4SourceError,
    _aggregate_update,
    connect_graph_core,
    database_footprint,
    extract_system_sample,
    iter_v4_rows,
    register_source_file,
    safe_int,
    series_catalog,
    validate_graph_core,
)

from graph_evidence import (  # noqa: E402
    copy_retention_ledger,
    reapply_retention_ledger,
    replace_availability_from_1min,
)

DEFAULT_PATTERNS = ("zendure_measurements*.csv", "zendure_measurements*.csv.gz")


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("CONFIG_ROOT_NOT_OBJECT")
    return data


def _resolve_path(value: str, *, base: Path) -> Path:
    p = Path(str(value or "")).expanduser()
    return p if p.is_absolute() else (base / p)


def candidate_dirs(config: Mapping[str, Any], config_path: Path, explicit: Sequence[str]) -> List[Path]:
    result: List[Path] = []
    for value in explicit:
        if value:
            result.append(Path(value).expanduser())
    for key, default in (("MEASUREMENT_LOG_DIR", "logs"), ("MEASUREMENT_LOG_FALLBACK_DIR", "logs/fallback")):
        value = str(config.get(key) or default)
        result.append(_resolve_path(value, base=config_path.parent))
    unique: List[Path] = []
    seen = set()
    for path in result:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        key = str(resolved)
        if key not in seen and resolved.exists() and resolved.is_dir():
            seen.add(key)
            unique.append(resolved)
    return unique


def find_v4_files(dirs: Sequence[Path], explicit: Sequence[str]) -> List[Path]:
    found: List[Path] = []
    for item in explicit:
        p = Path(item).expanduser()
        matches = glob.glob(str(p))
        if matches:
            for match in matches:
                candidate = Path(match)
                if candidate.is_dir():
                    for pattern in DEFAULT_PATTERNS:
                        found.extend(candidate.glob(pattern))
                else:
                    found.append(candidate)
        elif p.exists():
            found.append(p)
    if not found:
        for directory in dirs:
            for pattern in DEFAULT_PATTERNS:
                found.extend(directory.glob(pattern))
    unique: Dict[str, Path] = {}
    for path in found:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved.is_file():
            unique[str(resolved)] = resolved
    return list(unique.values())


def first_timestamp(path: Path) -> int:
    anomalies, rows = iter_v4_rows(path)
    try:
        for _line_no, row in rows:
            ts = safe_int(row.get("measurement_epoch_ms"))
            if ts is not None:
                return int(ts)
    finally:
        close = getattr(rows, "close", None)
        if callable(close):
            close()
    return 2**63 - 1


def _new_minute(sample: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "bucket_start_ms": int(sample["ts_ms"] // 60000) * 60000,
        "sample_count": 0,
        "first_ts_ms": int(sample["ts_ms"]),
        "last_ts_ms": int(sample["ts_ms"]),
        "quality_or": 0,
    }


def _update_minute(data: Dict[str, Any], sample: Mapping[str, Any]) -> None:
    data["sample_count"] = int(data.get("sample_count") or 0) + 1
    data["first_ts_ms"] = min(int(data["first_ts_ms"]), int(sample["ts_ms"]))
    data["last_ts_ms"] = max(int(data["last_ts_ms"]), int(sample["ts_ms"]))
    data["quality_or"] = int(data.get("quality_or") or 0) | int(sample.get("quality_flags") or 0)
    for spec in SYSTEM_SERIES:
        _aggregate_update(data, spec, sample.get(spec.column))


def _insert_minute(conn: sqlite3.Connection, data: Optional[Dict[str, Any]]) -> None:
    if not data:
        return
    columns = list(data.keys())
    conn.execute(
        f"INSERT INTO measurement_1min({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
        tuple(data[column] for column in columns),
    )


def _copy_legacy_config_timeline(conn: sqlite3.Connection, legacy_path: Optional[Path]) -> int:
    if not legacy_path or not legacy_path.exists():
        return 0
    source = sqlite3.connect(f"file:{legacy_path}?mode=ro", uri=True, timeout=30.0)
    source.row_factory = sqlite3.Row
    try:
        table = source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_config_timeline'"
        ).fetchone()
        if table is None:
            return 0
        rows = source.execute("SELECT * FROM graph_config_timeline ORDER BY effective_from_ms").fetchall()
        for row in rows:
            conn.execute(
                """
                INSERT OR REPLACE INTO graph_config_timeline(
                    effective_from_ms,config_control_hash,known,min_soc,max_soc,reserve_soc,night_start,night_end,source
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    row["effective_from_ms"], row["config_control_hash"], row["known"], row["min_soc"], row["max_soc"],
                    row["reserve_soc"], row["night_start"], row["night_end"], "legacy_v2_verified_timeline",
                ),
            )
        return len(rows)
    finally:
        source.close()


def _write_series_coverage(conn: sqlite3.Connection, coverage: Mapping[str, Tuple[int, int]]) -> None:
    for series_id, (first_ms, last_ms) in coverage.items():
        conn.execute(
            "INSERT OR REPLACE INTO graph_series_coverage(series_id,from_ms,to_ms,source,quality) VALUES(?,?,?,?,?)",
            (series_id, first_ms, last_ms, "MEASUREMENT_V4", "OBSERVED_NON_NULL_SPAN"),
        )


def rebuild(
    files: Sequence[Path],
    output: Path,
    *,
    legacy_db: Optional[Path] = None,
    reset: bool = False,
    batch_size: int = 5000,
    progress_every: int = 100000,
    include_source_sha256: bool = False,
    entity_config: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    started = time.time()
    if output.exists() and not reset:
        raise SystemExit(f"Zieldatenbank existiert bereits: {output}; --reset erforderlich")
    if reset:
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(output) + suffix)
            if candidate.exists():
                candidate.unlink()
    output.parent.mkdir(parents=True, exist_ok=True)

    ordered = sorted(files, key=lambda path: (first_timestamp(path), str(path)))
    conn = connect_graph_core(output)
    sparse = SparseStateBuilder(conn)
    runs = RunBuilder(conn)
    commands = CommandEventBuilder(conn)
    entities = EntityPersistenceBuilder(conn, source="MEASUREMENT_V4")
    raw_columns = [
        "ts_ms", "cycle_index", "quality_flags", "sample_monotonic_ns", "run_id",
        "command_desired_sequence_id", "command_publish_event_id",
    ] + [spec.column for spec in SYSTEM_SERIES]
    raw_sql = f"INSERT OR IGNORE INTO measurement_raw({','.join(raw_columns)}) VALUES({','.join('?' for _ in raw_columns)})"

    minute: Optional[Dict[str, Any]] = None
    raw_batch: List[Tuple[Any, ...]] = []
    last_ts: Optional[int] = None
    rows_seen = 0
    rows_imported = 0
    duplicate_or_out_of_order = 0
    files_ok = 0
    source_errors: List[Dict[str, str]] = []
    config_transitions: List[Tuple[int, str]] = []
    last_config_hash = ""
    coverage: Dict[str, Tuple[int, int]] = {}
    invalid_numeric_fields: Dict[str, int] = {}
    snapshot_map: Dict[str, Dict[str, Any]] = {}
    for directory in sorted({path.parent for path in ordered}):
        snapshot_map.update(load_snapshot_map(str(directory / "zec_config_snapshots.json")))

    try:
        for file_no, path in enumerate(ordered, 1):
            # Each source file is an atomic rebuild unit. A structurally broken
            # file must never leave a partial file import behind.
            savepoint = f"v4_file_{file_no}"
            conn.execute(f"SAVEPOINT {savepoint}")
            # Pre-register the file so sparse command events can refer to it.
            source_file_id = register_source_file(
                conn, path, first_ms=None, last_ms=None, rows_seen=0, rows_imported=0,
                anomalies=(), include_sha256=False,
            )
            anomalies, iterator = iter_v4_rows(path)
            file_seen = 0
            file_imported = 0
            file_first: Optional[int] = None
            file_last: Optional[int] = None
            try:
                for _line_no, row in iterator:
                    rows_seen += 1
                    file_seen += 1
                    sample = extract_system_sample(row)
                    if sample is None:
                        raise V4SourceError(f"{path}: row without valid measurement_epoch_ms")
                    ts_ms = int(sample["ts_ms"])
                    for field in sample.get("_invalid_numeric_fields", ()):
                        invalid_numeric_fields[str(field)] = int(invalid_numeric_fields.get(str(field), 0)) + 1
                    if last_ts is not None and ts_ms <= last_ts:
                        # Raw timestamps are the canonical identity in V3. Overlap
                        # or out-of-order history is reported, never merged into
                        # sparse timelines where it could create false transitions.
                        duplicate_or_out_of_order += 1
                        continue
                    last_ts = ts_ms
                    file_first = ts_ms if file_first is None else min(file_first, ts_ms)
                    file_last = ts_ms if file_last is None else max(file_last, ts_ms)
                    file_imported += 1
                    rows_imported += 1

                    for spec in SYSTEM_SERIES:
                        if sample.get(spec.column) is not None:
                            prev = coverage.get(spec.series_id)
                            coverage[spec.series_id] = (ts_ms, ts_ms) if prev is None else (prev[0], ts_ms)

                    current_bucket = int(ts_ms // 60000) * 60000
                    if minute is None:
                        minute = _new_minute(sample)
                    elif int(minute["bucket_start_ms"]) != current_bucket:
                        _insert_minute(conn, minute)
                        minute = _new_minute(sample)
                    _update_minute(minute, sample)

                    run_id = runs.observe(ts_ms, sample.get("cycle_index"))
                    sample["run_id"] = run_id
                    raw_batch.append(tuple(sample.get(column) for column in raw_columns))
                    if len(raw_batch) >= batch_size:
                        conn.executemany(raw_sql, raw_batch)
                        raw_batch.clear()

                    entity_row: Mapping[str, Any] = row
                    if entity_config:
                        entity_row = dict(row)
                        entity_row["_graph_entity_config"] = {
                            "zendure_device_id": str(entity_config.get("DEVICE_ID") or "").strip(),
                            "primary_display_name": str(entity_config.get("SECOND_BATTERY_DISPLAY_NAME") or "").strip(),
                        }
                    entity_context = entities.observe(ts_ms, entity_row, run_id=run_id)
                    sparse.observe(
                        ts_ms, row, run_id,
                        controlled_entity_id=entity_context.get("controlled_entity_id"),
                        primary_entity_id=entity_context.get("primary_entity_id"),
                    )
                    commands.observe(
                        ts_ms, run_id, row, source_file_id,
                        entity_id=entity_context.get("controlled_entity_id"),
                    )

                    digest = str(row.get("config_control_hash") or "").strip()
                    if digest and digest != last_config_hash:
                        config_transitions.append((ts_ms, digest))
                        last_config_hash = digest

                    if progress_every and rows_imported % progress_every == 0:
                        print(f"progress rows={rows_imported} files={file_no}/{len(ordered)}", flush=True)
                # Flush current-file raw rows before releasing its savepoint.
                if raw_batch:
                    conn.executemany(raw_sql, raw_batch)
                    raw_batch.clear()
                # iter_v4_rows records trailing-NUL anomalies while exhausting
                # the iterator, so register final per-file evidence afterwards.
                register_source_file(
                    conn, path, first_ms=file_first, last_ms=file_last, rows_seen=file_seen,
                    rows_imported=file_imported, anomalies=anomalies, include_sha256=include_source_sha256,
                )
                entities.flush_seen()
                conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                conn.commit()
                files_ok += 1
            except Exception as exc:
                close = getattr(iterator, "close", None)
                if callable(close):
                    close()
                try:
                    conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                except Exception:
                    conn.rollback()
                raw_batch.clear()
                source_errors.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
                raise

        if raw_batch:
            conn.executemany(raw_sql, raw_batch)
            raw_batch.clear()
        _insert_minute(conn, minute)
        sparse.close(last_ts)
        runs.close()
        _write_series_coverage(conn, coverage)
        entities.flush_seen()

        # Build config history from V4 hashes/snapshots. The validated legacy
        # timeline is merged afterwards so known historical overlays are not lost
        # if a snapshot file is absent from the current log directories.
        config_result = backfill_entries(
            conn, config_transitions, snapshot_map, source="measurement_v4_rebuild",
            presorted=True, commit=False,
        )
        legacy_config_rows = _copy_legacy_config_timeline(conn, legacy_db)

        # WP5: derive compact availability from the permanent 1-minute layer,
        # then copy and reapply any deliberate high-res retention from a prior
        # V3 core so a rebuild never resurrects intentionally purged detail.
        replace_availability_from_1min(conn)
        retention_rows_copied = copy_retention_ledger(str(legacy_db), conn) if legacy_db else 0
        retention_reapplied = reapply_retention_ledger(conn)

        # graph_config_timeline's V13 helper recreates its historical hash index;
        # V14 deliberately removes it because no productive query uses it.
        conn.execute("DROP INDEX IF EXISTS idx_graph_config_timeline_hash")

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        meta = {
            "rebuild_completed_at": now,
            "rebuild_source": "measurement_v4",
            "rebuild_source_files": str(len(ordered)),
            "rebuild_rows_seen": str(rows_seen),
            "rebuild_rows_imported": str(rows_imported),
            "rebuild_duplicate_or_out_of_order": str(duplicate_or_out_of_order),
            "series_catalog_json": json.dumps(series_catalog(), ensure_ascii=False, separators=(",", ":")),
        }
        for key, value in meta.items():
            conn.execute("INSERT OR REPLACE INTO measurement_meta(key,value) VALUES(?,?)", (key, value))
        conn.commit()
        # Make file-size reporting deterministic and bounded at the end of an
        # offline rebuild; the DB remains WAL-capable when opened later.
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        validation = validate_graph_core(conn)
        footprint = database_footprint(output)
        return {
            "status": "ok" if validation["integrity_check"] == "ok" else "error",
            "output": str(output),
            "files": len(ordered),
            "files_ok": files_ok,
            "rows_seen": rows_seen,
            "rows_imported": rows_imported,
            "duplicate_or_out_of_order": duplicate_or_out_of_order,
            "series_coverage_count": len(coverage),
            "invalid_numeric_fields": dict(sorted(invalid_numeric_fields.items())),
            "snapshot_count": len(snapshot_map),
            "legacy_config_rows_copied": legacy_config_rows,
            "retention_rows_copied": retention_rows_copied,
            "retention_reapplied": retention_reapplied,
            "config_timeline": config_result,
            "source_errors": source_errors,
            "duration_s": round(time.time() - started, 3),
            "validation": validation,
            "footprint": footprint,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild ZEC V14 Graph-Core V3 from Measurement V4")
    parser.add_argument("sources", nargs="*", help="V4 files/globs/directories; otherwise discovered from config")
    parser.add_argument("--config", default=str(ROOT / "config.json"), help="ZEC config.json")
    parser.add_argument("--measurement-dir", action="append", default=[], help="Additional measurement directory")
    parser.add_argument("--output", required=True, help="New V3 SQLite output path")
    parser.add_argument("--legacy-db", default="", help="Optional read-only legacy DB used for validated config timeline and V3 retention evidence")
    parser.add_argument("--reset", action="store_true", help="Delete an existing output DB/WAL/SHM before rebuilding")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--progress-every", type=int, default=100000)
    parser.add_argument("--source-sha256", action="store_true", help="Hash every V4 source file for provenance (slower)")
    parser.add_argument("--report", default="", help="Optional JSON report path")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config).expanduser().resolve()
    config = _load_json(config_path) if config_path.exists() else {}
    dirs = candidate_dirs(config, config_path, args.measurement_dir)
    files = find_v4_files(dirs, args.sources)
    if not files:
        print(json.dumps({"status": "error", "reason": "NO_V4_FILES", "directories": [str(p) for p in dirs]}))
        return 2
    output = Path(args.output).expanduser().resolve()
    legacy = Path(args.legacy_db).expanduser().resolve() if args.legacy_db else None
    try:
        result = rebuild(
            files, output, legacy_db=legacy, reset=args.reset, batch_size=max(1, args.batch_size),
            progress_every=max(0, args.progress_every), include_source_sha256=bool(args.source_sha256),
            entity_config=config,
        )
    except Exception as exc:
        result = {"status": "error", "reason": type(exc).__name__, "error": str(exc), "output": str(output)}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.report:
        report = Path(args.report).expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(text + "\n", encoding="utf-8")
    return 0 if result.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
