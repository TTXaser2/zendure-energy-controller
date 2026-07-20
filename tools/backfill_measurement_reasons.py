#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Backfill missing historical controller reasons in the SQLite graph store.

The tool is deliberately offline/idempotent:
- CSV files are only read and never modified.
- only empty reason columns are filled;
- no raw measurement rows are inserted;
- only affected one-minute reason aggregates are recalculated;
- dry-run operates on a temporary SQLite copy;
- apply creates a SQLite-consistent rollback backup first.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from measurement_db import DEFAULT_DB_FILENAME, ensure_schema, extract_measurement_point  # noqa: E402

CSV_PATTERNS = (
    "zendure_measurements_v4_*.csv",
    "zendure_measurements*.csv",
    "*.csv",
)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Füllt fehlende historische Regelgründe im SQLite-Graphspeicher aus V4-CSV-Dateien nach.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("paths", nargs="*", help="Zusätzliche CSV-Dateien, Verzeichnisse oder Globs.")
    parser.add_argument("--root", default=str(ROOT), help="Controller-Installationsverzeichnis.")
    parser.add_argument("--config", help="Pfad zur config.json.")
    parser.add_argument("--db-path", help="Expliziter Pfad zur SQLite-Datei.")
    parser.add_argument("--apply", action="store_true", help="Änderungen in die echte Datenbank schreiben.")
    parser.add_argument("--allow-running-controller", action="store_true", help="Apply trotz aktivem Controller zulassen (nicht empfohlen).")
    parser.add_argument("--progress-every", type=int, default=10000, help="Fortschrittsausgabe nach N CSV-Zeilen; 0 deaktiviert.")
    return parser.parse_args(argv)


def load_config(root: Path, explicit: Optional[str]) -> Tuple[Path, Dict[str, Any]]:
    candidates = [Path(explicit).expanduser()] if explicit else [root / "config.json", root / "config.example.json"]
    for path in candidates:
        if path.exists():
            return path.resolve(), json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("Keine config.json oder config.example.json gefunden.")


def _candidate_dirs(root: Path, config_path: Path, cfg: Dict[str, Any]) -> List[Path]:
    values: List[Path] = [root / "logs", config_path.parent / "logs"]
    for key in ("MEASUREMENT_LOG_DIR", "MEASUREMENT_LOG_PATH"):
        raw = str(cfg.get(key) or "").strip()
        if not raw:
            continue
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = config_path.parent / path
        values.append(path if path.suffix.lower() != ".csv" else path.parent)
    unique: List[Path] = []
    seen = set()
    for path in values:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique




def resolve_db_path(root: Path, config_path: Path, cfg: Dict[str, Any], explicit_arg: Optional[str]) -> Path:
    if explicit_arg:
        path = Path(explicit_arg).expanduser()
        return (path if path.is_absolute() else config_path.parent / path).resolve()
    explicit_cfg = str(cfg.get("MEASUREMENT_DB_PATH") or "").strip()
    if explicit_cfg:
        path = Path(explicit_cfg).expanduser()
        return (path if path.is_absolute() else config_path.parent / path).resolve()
    filename = str(cfg.get("MEASUREMENT_DB_FILE") or DEFAULT_DB_FILENAME).strip() or DEFAULT_DB_FILENAME
    candidates = [directory / filename for directory in _candidate_dirs(root, config_path, cfg)]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (root / "logs" / filename).resolve()

def discover_csv_files(root: Path, config_path: Path, cfg: Dict[str, Any], paths: Sequence[str]) -> List[Path]:
    found: List[Path] = []
    supplied = bool(paths)
    for item in paths:
        path = Path(item).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.is_dir():
            for pattern in CSV_PATTERNS:
                found.extend(Path(x) for x in glob.glob(str(path / pattern)))
        else:
            found.extend(Path(x) for x in glob.glob(str(path)))
    if not supplied:
        for directory in _candidate_dirs(root, config_path, cfg):
            if not directory.is_dir():
                continue
            for pattern in CSV_PATTERNS:
                found.extend(Path(x) for x in glob.glob(str(directory / pattern)))
    unique: List[Path] = []
    seen = set()
    for path in found:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved.suffix.lower() != ".csv" or resolved.name.startswith("."):
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        unique.append(resolved)
    unique.sort(key=lambda p: (str(p.parent), p.name))
    return unique


def sniff_dialect(path: Path) -> csv.Dialect:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
            sample = fh.read(8192).replace("\x00", "")
        if not sample:
            return csv.excel
        try:
            return csv.Sniffer().sniff(sample, delimiters=";,\t,")
        except Exception:
            class Semi(csv.excel):
                delimiter = ";"
            return Semi if sample.count(";") >= sample.count(",") else csv.excel
    except Exception:
        return csv.excel


def iter_csv_points(files: Sequence[Path]) -> Iterable[Tuple[Path, Dict[str, Any]]]:
    for file_no, path in enumerate(files, start=1):
        print(f"[{file_no}/{len(files)}] {path.name}")
        dialect = sniff_dialect(path)
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
            clean_lines = (line.replace("\x00", "") for line in fh)
            reader = csv.DictReader(clean_lines, dialect=dialect)
            for row in reader:
                point = extract_measurement_point(row)
                if point is not None:
                    yield path, point


def controller_is_active() -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "--quiet", "zendure-controller.service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def sqlite_backup(source: Path, target: Path) -> None:
    src = sqlite3.connect(str(source), timeout=5.0)
    dst = sqlite3.connect(str(target), timeout=5.0)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def recalc_bucket_reason(conn: sqlite3.Connection, bucket: int) -> None:
    row = conn.execute(
        """
        SELECT control_reason
        FROM measurement_raw
        WHERE ts_ms >= ? AND ts_ms < ?
          AND COALESCE(TRIM(control_reason),'') <> ''
        ORDER BY ts_ms DESC
        LIMIT 1
        """,
        (bucket, bucket + 60000),
    ).fetchone()
    reason = str(row[0] or "") if row else ""
    conn.execute(
        "UPDATE measurement_1min SET control_reason_last=? WHERE bucket_start_ms=?",
        (reason, bucket),
    )


def run_backfill(conn: sqlite3.Connection, files: Sequence[Path], progress_every: int) -> Dict[str, int]:
    rows_seen = raw_row_missing = already_complete = no_reason = updated = 0
    affected_buckets = set()
    conn.execute("BEGIN IMMEDIATE")
    try:
        for _path, point in iter_csv_points(files):
            rows_seen += 1
            reason = str(point.get("control_reason") or "").strip()
            if not reason:
                no_reason += 1
                continue
            row = conn.execute(
                "SELECT COALESCE(TRIM(control_reason),'') FROM measurement_raw WHERE ts_ms=?",
                (int(point["ts_ms"]),),
            ).fetchone()
            if row is None:
                raw_row_missing += 1
                continue
            if row[0]:
                already_complete += 1
                continue
            cursor = conn.execute(
                "UPDATE measurement_raw SET control_reason=? WHERE ts_ms=? AND COALESCE(TRIM(control_reason),'')=''",
                (reason, int(point["ts_ms"])),
            )
            if cursor.rowcount == 1:
                updated += 1
                affected_buckets.add(int(point["ts_ms"] // 60000) * 60000)
            if progress_every and rows_seen % progress_every == 0:
                print(
                    f"  ... {rows_seen} Zeilen, zu füllen={updated}, "
                    f"bereits vollständig={already_complete}, nicht in DB={raw_row_missing}"
                )
        for idx, bucket in enumerate(sorted(affected_buckets), start=1):
            recalc_bucket_reason(conn, bucket)
            if progress_every and idx % max(1, progress_every // 100) == 0:
                print(f"  ... {idx}/{len(affected_buckets)} Minutenaggregate aktualisiert")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {
        "rows_seen": rows_seen,
        "raw_row_missing": raw_row_missing,
        "already_complete": already_complete,
        "csv_rows_without_reason": no_reason,
        "updated": updated,
        "affected_minute_buckets": len(affected_buckets),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    config_path, cfg = load_config(root, args.config)
    db_path = resolve_db_path(root, config_path, cfg, args.db_path)
    files = discover_csv_files(root, config_path, cfg, args.paths)

    print("ZEC Regelgrund-Backfill")
    print(f"Modus:          {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Controller:     {root}")
    print(f"Konfiguration:  {config_path}")
    print(f"SQLite:         {db_path}")
    print(f"CSV-Dateien:    {len(files)}")

    if not db_path.exists():
        print("SQLite-Datei nicht gefunden.")
        return 2
    if not files:
        print("Keine passenden CSV-Dateien gefunden.")
        return 3
    if args.apply and controller_is_active() and not args.allow_running_controller:
        print("ABBRUCH: zendure-controller.service ist aktiv. Controller vor APPLY stoppen.")
        return 4

    start = time.time()
    rollback_backup: Optional[Path] = None
    temp_dir: Optional[tempfile.TemporaryDirectory[str]] = None
    work_db = db_path
    try:
        if args.apply:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rollback_backup = Path(str(db_path) + f".before_reason_backfill_{stamp}.bak")
            sqlite_backup(db_path, rollback_backup)
        else:
            temp_dir = tempfile.TemporaryDirectory(prefix="zec_reason_backfill_dry_")
            work_db = Path(temp_dir.name) / db_path.name
            sqlite_backup(db_path, work_db)
            print(f"DRY-RUN-Kopie:  {work_db}")

        conn = sqlite3.connect(str(work_db), timeout=10.0)
        try:
            conn.execute("PRAGMA busy_timeout=10000")
            ensure_schema(conn)
            stats = run_backfill(conn, files, max(0, int(args.progress_every)))
        finally:
            conn.close()
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()

    print("\n=== Ergebnis ===")
    for key in (
        "rows_seen",
        "csv_rows_without_reason",
        "raw_row_missing",
        "already_complete",
        "updated",
        "affected_minute_buckets",
    ):
        print(f"{key}: {stats[key]}")
    print(f"duration_s: {time.time() - start:.2f}")
    if args.apply:
        print("Änderungen wurden geschrieben.")
        print(f"Rollback-Backup: {rollback_backup}")
    else:
        print("DRY-RUN: Keine Änderung wurde gespeichert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
