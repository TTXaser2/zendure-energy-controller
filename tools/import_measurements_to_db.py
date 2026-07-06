#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# Offline import tool for existing ZEC measurement CSV logs into the optional
# SQLite graph store. The tool is intentionally independent from the live
# controller loop and writes in small batches so it can be used on a Raspberry
# Pi without loading large logs into memory.

import argparse
import csv
import glob
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from measurement_db import (  # noqa: E402
    _connect,
    extract_measurement_point,
    resolve_measurement_db_path,
    write_points,
)

DEFAULT_PATTERNS = (
    "zendure_measurements*.csv",
    "zendure_measurements_v*.csv",
    "measurement*.csv",
    "*.csv",
)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        raise SystemExit(f"Konfiguration konnte nicht gelesen werden: {path}: {exc}")


def load_config(config_path: Optional[str]) -> Tuple[Dict[str, Any], Path]:
    if config_path:
        path = Path(config_path).expanduser().resolve()
        return _load_json(path), path
    for candidate in (ROOT_DIR / "config.json", ROOT_DIR / "config.example.json"):
        if candidate.exists():
            return _load_json(candidate), candidate
    return {}, ROOT_DIR / "config.json"


def _candidate_log_dirs(config: Dict[str, Any], explicit_log_dir: Optional[str]) -> List[Path]:
    dirs: List[Path] = []
    if explicit_log_dir:
        dirs.append(Path(explicit_log_dir).expanduser())
    try:
        from csv_logger import resolve_log_target  # local import avoids startup side effects

        target = resolve_log_target(config, allow_fallback=True)
        active_path = str(target.get("path") or "")
        if active_path:
            dirs.append(Path(active_path).expanduser().parent)
        fallback_path = str(target.get("fallback_path") or "")
        if fallback_path:
            dirs.append(Path(fallback_path).expanduser().parent)
    except Exception:
        pass
    if config.get("MEASUREMENT_LOG_DIR"):
        dirs.append(Path(str(config.get("MEASUREMENT_LOG_DIR"))).expanduser())
    dirs.append(ROOT_DIR / "logs")
    seen = set()
    result: List[Path] = []
    for d in dirs:
        d_abs = d if d.is_absolute() else (ROOT_DIR / d)
        try:
            key = str(d_abs.resolve())
        except Exception:
            key = str(d_abs)
        if key not in seen:
            seen.add(key)
            result.append(Path(key))
    return result


def find_csv_files(config: Dict[str, Any], log_dir: Optional[str], files: Sequence[str], patterns: Sequence[str]) -> List[Path]:
    found: List[Path] = []
    for item in files:
        p = Path(item).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        if p.is_dir():
            for pat in patterns:
                found.extend(Path(x) for x in glob.glob(str(p / pat)))
        else:
            for x in glob.glob(str(p)):
                found.append(Path(x))
    if not found:
        for d in _candidate_log_dirs(config, log_dir):
            if not d.exists() or not d.is_dir():
                continue
            for pat in patterns:
                found.extend(Path(x) for x in glob.glob(str(d / pat)))
    unique = []
    seen = set()
    for p in found:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if rp.name.startswith(".") or rp.suffix.lower() != ".csv":
            continue
        key = str(rp)
        if key in seen:
            continue
        seen.add(key)
        unique.append(rp)
    unique.sort(key=lambda p: (str(p.parent), p.name))
    return unique


def sniff_dialect(path: Path) -> csv.Dialect:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(8192)
        if not sample:
            return csv.excel
        try:
            return csv.Sniffer().sniff(sample, delimiters=";,\t,")
        except Exception:
            class Semi(csv.excel):
                delimiter = ";"
            if sample.count(";") >= sample.count(","):
                return Semi
            return csv.excel
    except Exception:
        return csv.excel


def _row_schema_supported(row: Dict[str, Any]) -> bool:
    schema = str(row.get("schema") or row.get("measurement_schema") or "").strip().upper()
    version = str(row.get("schema_version") or row.get("measurement_schema_version") or "").strip()
    if schema.startswith("ZEC-MEASUREMENT-V2"):
        return False
    if schema.startswith("ZEC-MEASUREMENT-V3") or schema.startswith("ZEC-MEASUREMENT-V4"):
        return True
    if version in {"3", "4"}:
        return True
    # RC17 extractor can also read reduced/legacy CSV rows if they contain a time basis.
    return True


def iter_points(path: Path, *, max_rows: Optional[int] = None) -> Tuple[int, int, int, Iterable[Dict[str, Any]]]:
    # Kept as generator factory return via nested generator so counters can be
    # updated by caller without storing rows in memory.
    dialect = sniff_dialect(path)

    def gen():
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh, dialect=dialect)
            for idx, row in enumerate(reader, start=1):
                if max_rows is not None and idx > max_rows:
                    break
                if not _row_schema_supported(row):
                    yield {"__skip_reason": "unsupported_schema"}
                    continue
                point = extract_measurement_point(row)
                if point is None:
                    yield {"__skip_reason": "no_timebasis_or_mapping"}
                else:
                    yield point

    return 0, 0, 0, gen()


def _count_rows(conn: sqlite3.Connection) -> Tuple[int, int]:
    raw = conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0]
    agg = conn.execute("SELECT COUNT(*) FROM measurement_1min").fetchone()[0]
    return int(raw), int(agg)


def import_files(
    csv_files: Sequence[Path],
    db_path: Path,
    *,
    batch_size: int = 500,
    dry_run: bool = False,
    reset: bool = False,
    max_rows_per_file: Optional[int] = None,
    progress_every: int = 5000,
) -> Dict[str, Any]:
    start = time.time()
    total_seen = total_imported = total_skipped = 0
    per_file: List[Dict[str, Any]] = []

    if dry_run:
        conn = None
    else:
        if reset and db_path.exists():
            for suffix in ("", "-wal", "-shm"):
                candidate = Path(str(db_path) + suffix)
                if candidate.exists():
                    candidate.unlink()
        conn = _connect(str(db_path))

    try:
        for file_no, path in enumerate(csv_files, start=1):
            seen = imported = skipped = 0
            batch: List[Dict[str, Any]] = []
            print(f"[{file_no}/{len(csv_files)}] {path}")
            _, _, _, points = iter_points(path, max_rows=max_rows_per_file)
            for point in points:
                seen += 1
                total_seen += 1
                if point.get("__skip_reason"):
                    skipped += 1
                    total_skipped += 1
                else:
                    imported += 1
                    total_imported += 1
                    if not dry_run:
                        batch.append(point)
                        if len(batch) >= batch_size:
                            write_points(conn, batch)  # type: ignore[arg-type]
                            batch = []
                if progress_every and seen % progress_every == 0:
                    print(f"  ... {seen} Zeilen gelesen, {imported} importierbar, {skipped} übersprungen")
            if batch and not dry_run:
                write_points(conn, batch)  # type: ignore[arg-type]
            per_file.append({"file": str(path), "rows_seen": seen, "rows_imported": imported, "rows_skipped": skipped})
            print(f"  fertig: gelesen={seen}, importiert={imported}, übersprungen={skipped}")
        raw = agg = 0
        if conn is not None:
            raw, agg = _count_rows(conn)
            conn.execute("INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('last_import_epoch_s',?)", (str(time.time()),))
            conn.execute("INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('last_import_source_files',?)", (str(len(csv_files)),))
            conn.commit()
        return {
            "db_path": str(db_path),
            "dry_run": dry_run,
            "reset": reset,
            "files": len(csv_files),
            "rows_seen": total_seen,
            "rows_imported": total_imported,
            "rows_skipped": total_skipped,
            "db_raw_rows": raw,
            "db_1min_rows": agg,
            "duration_s": round(time.time() - start, 3),
            "per_file": per_file,
        }
    finally:
        if conn is not None:
            conn.close()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importiert vorhandene ZEC Measurement-CSV-Dateien in den SQLite-Graphspeicher.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("files", nargs="*", help="CSV-Dateien, Globs oder Verzeichnisse. Ohne Angabe wird das Messdatenverzeichnis durchsucht.")
    parser.add_argument("--config", help="Pfad zur config.json. Ohne Angabe: config.json, fallback config.example.json im Installationsverzeichnis.")
    parser.add_argument("--log-dir", help="Messdatenverzeichnis, falls nicht aus der Konfiguration ermittelt werden soll.")
    parser.add_argument("--db-path", help="Zielpfad der SQLite-Datei. Ohne Angabe aus MEASUREMENT_DB_* und Messdatenziel abgeleitet.")
    parser.add_argument("--pattern", action="append", help="Zusätzliches Dateimuster, z. B. 'zendure_measurements*.csv'. Mehrfach möglich.")
    parser.add_argument("--batch-size", type=int, default=500, help="SQLite-Schreibbatchgröße.")
    parser.add_argument("--max-rows-per-file", type=int, default=None, help="Optionales Limit pro Datei für Tests/Probeimporte.")
    parser.add_argument("--progress-every", type=int, default=5000, help="Fortschritt alle N CSV-Zeilen ausgeben; 0 deaktiviert.")
    parser.add_argument("--reset", action="store_true", help="Vor Import vorhandene DB-Datei inklusive WAL/SHM löschen.")
    parser.add_argument("--dry-run", action="store_true", help="Nur lesen und auswerten, nichts schreiben.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config, config_path = load_config(args.config)
    patterns = tuple(args.pattern or DEFAULT_PATTERNS)
    if args.db_path:
        db_path = Path(args.db_path).expanduser()
        if not db_path.is_absolute():
            db_path = (Path.cwd() / db_path).resolve()
    else:
        db_path = Path(resolve_measurement_db_path(config)).expanduser().resolve()
    csv_files = find_csv_files(config, args.log_dir, args.files, patterns)
    print("ZEC Measurement SQLite Import")
    print(f"Konfiguration: {config_path}")
    print(f"SQLite-Ziel:   {db_path}")
    print(f"CSV-Dateien:   {len(csv_files)}")
    if not csv_files:
        print("Keine CSV-Dateien gefunden. Nutze --log-dir oder gib Dateien/Globs direkt an.", file=sys.stderr)
        return 2
    summary = import_files(
        csv_files,
        db_path,
        batch_size=max(1, int(args.batch_size)),
        dry_run=bool(args.dry_run),
        reset=bool(args.reset),
        max_rows_per_file=args.max_rows_per_file,
        progress_every=max(0, int(args.progress_every)),
    )
    print("\n=== Zusammenfassung ===")
    for key in ("files", "rows_seen", "rows_imported", "rows_skipped", "db_raw_rows", "db_1min_rows", "duration_s", "dry_run", "reset"):
        print(f"{key}: {summary[key]}")
    print(f"db_path: {summary['db_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
