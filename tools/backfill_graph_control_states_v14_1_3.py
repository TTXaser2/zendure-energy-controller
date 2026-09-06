#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Targeted V14.1.3 repair for missing live Graph-Core controller states.

V14.1.2 queued the raw controller row into Graph Core before Measurement V4
projected ``operating_mode`` and ``control_intent``.  Historical V4 files keep
those normalized values, so this maintenance-window tool repairs only the
missing *suffix* of the two affected graph interval kinds:

- OPERATING_MODE
- CONTROL_INTENT

It never rebuilds Graph Core, never touches numeric samples, command events,
coverage/evidence or CONTROL_REASON, and never interpolates across a real V4
gap.  Existing intervals are preserved.  Re-running the tool is idempotent:
only V4 rows later than the last already-persisted interval of each kind are
eligible.
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_core_v3 import V4SourceError, iter_v4_rows, safe_int  # noqa: E402
from measurement_db import detect_measurement_db_backend, resolve_measurement_db_path  # noqa: E402
from tools.rebuild_graph_core_v3 import _load_json, candidate_dirs, find_v4_files, first_timestamp  # noqa: E402

KINDS: Tuple[Tuple[str, str], ...] = (
    ("OPERATING_MODE", "operating_mode"),
    ("CONTROL_INTENT", "control_intent"),
)
SOURCE = "MEASUREMENT_V4_STATE_REPAIR_V14_1_3"
DEFAULT_MAX_GAP_MS = 30_000


@contextmanager
def _runtime_root_context(runtime_root: Optional[Path]):
    if runtime_root is None:
        yield None
        return
    root = runtime_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"RUNTIME_ROOT_MISSING:{root}")
    previous = Path.cwd()
    os.chdir(root)
    try:
        yield root
    finally:
        os.chdir(previous)


def _quick_check(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA quick_check").fetchone()
    return str(row[0]) if row else "no_result"


def _existing_cutoffs(conn: sqlite3.Connection) -> Dict[str, Optional[int]]:
    result: Dict[str, Optional[int]] = {}
    for kind, _field in KINDS:
        row = conn.execute(
            "SELECT MAX(COALESCE(end_ms,start_ms)) FROM graph_intervals WHERE kind=?",
            (kind,),
        ).fetchone()
        result[kind] = int(row[0]) if row and row[0] is not None else None
    return result


def _existing_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for kind, _field in KINDS:
        row = conn.execute("SELECT COUNT(*) FROM graph_intervals WHERE kind=?", (kind,)).fetchone()
        result[kind] = int(row[0] if row else 0)
    return result


def _run_spans(conn: sqlite3.Connection) -> Tuple[List[int], List[Tuple[int, Optional[int], int]]]:
    rows = conn.execute(
        "SELECT start_ms,end_ms,run_id FROM graph_runs ORDER BY start_ms,run_id"
    ).fetchall()
    spans = [(int(row[0]), int(row[1]) if row[1] is not None else None, int(row[2])) for row in rows]
    return [row[0] for row in spans], spans


def _resolve_run_id(
    ts_ms: int,
    starts: Sequence[int],
    spans: Sequence[Tuple[int, Optional[int], int]],
    *,
    tolerance_ms: int,
) -> Optional[int]:
    if not starts:
        return None
    idx = bisect.bisect_right(starts, int(ts_ms)) - 1
    if idx < 0:
        return None
    start_ms, end_ms, run_id = spans[idx]
    if ts_ms < start_ms:
        return None
    if end_ms is not None and ts_ms > end_ms + tolerance_ms:
        return None
    return run_id


def _ordered_files(config: Mapping[str, Any], config_path: Path, explicit_dirs: Sequence[str], explicit_files: Sequence[str]) -> List[Path]:
    dirs = candidate_dirs(config, config_path, explicit_dirs)
    files = find_v4_files(dirs, explicit_files)
    return sorted(files, key=lambda path: (first_timestamp(path), str(path)))


def collect_repair_intervals(
    conn: sqlite3.Connection,
    files: Sequence[Path],
    *,
    max_gap_ms: int = DEFAULT_MAX_GAP_MS,
) -> Dict[str, Any]:
    """Collect suffix-repair intervals from V4 without mutating the database."""
    cutoffs = _existing_cutoffs(conn)
    run_starts, run_spans = _run_spans(conn)
    intervals: Dict[str, List[Tuple[Optional[int], int, int, str]]] = {kind: [] for kind, _ in KINDS}
    open_state: Dict[str, Optional[Dict[str, Any]]] = {kind: None for kind, _ in KINDS}
    last_eligible_ts: Dict[str, Optional[int]] = {kind: None for kind, _ in KINDS}
    rows_seen = 0
    source_errors: List[Dict[str, str]] = []
    source_anomalies: List[Dict[str, Any]] = []

    def close_kind(kind: str, *, end_ms: Optional[int] = None) -> None:
        state = open_state[kind]
        if state is None:
            return
        last_ts = int(state["last_ts"])
        resolved_end = int(end_ms) if end_ms is not None else last_ts + 1
        if resolved_end <= int(state["start_ms"]):
            resolved_end = int(state["start_ms"]) + 1
        intervals[kind].append(
            (state.get("run_id"), int(state["start_ms"]), resolved_end, str(state["value"]))
        )
        open_state[kind] = None

    def break_all() -> None:
        for kind, _field in KINDS:
            close_kind(kind)
            last_eligible_ts[kind] = None

    last_global_ts: Optional[int] = None
    for path in files:
        anomalies, rows = iter_v4_rows(path)
        try:
            for _line_no, row in rows:
                rows_seen += 1
                ts_ms = safe_int(row.get("measurement_epoch_ms"))
                if ts_ms is None:
                    continue
                ts_ms = int(ts_ms)
                # File overlap/rotation duplicates are common and are not a
                # reason to fabricate backwards state transitions.
                if last_global_ts is not None and ts_ms < last_global_ts:
                    continue
                last_global_ts = ts_ms
                run_id = _resolve_run_id(ts_ms, run_starts, run_spans, tolerance_ms=max_gap_ms)

                for kind, field in KINDS:
                    cutoff = cutoffs.get(kind)
                    if cutoff is not None and ts_ms <= cutoff:
                        continue
                    previous_ts = last_eligible_ts[kind]
                    state = open_state[kind]
                    if previous_ts is not None and ts_ms - previous_ts > max_gap_ms:
                        close_kind(kind)
                        state = None
                    if state is not None and state.get("run_id") != run_id:
                        close_kind(kind, end_ms=ts_ms)
                        state = None

                    value = str(row.get(field) or "").strip()
                    if not value:
                        close_kind(kind, end_ms=ts_ms)
                        last_eligible_ts[kind] = ts_ms
                        continue
                    if state is None:
                        open_state[kind] = {
                            "start_ms": ts_ms,
                            "last_ts": ts_ms,
                            "value": value,
                            "run_id": run_id,
                        }
                    elif str(state["value"]) != value:
                        close_kind(kind, end_ms=ts_ms)
                        open_state[kind] = {
                            "start_ms": ts_ms,
                            "last_ts": ts_ms,
                            "value": value,
                            "run_id": run_id,
                        }
                    else:
                        state["last_ts"] = ts_ms
                    last_eligible_ts[kind] = ts_ms
        except V4SourceError as exc:
            # A damaged source file is evidence of a real discontinuity.  Keep
            # already collected observations, close the current state and
            # continue with the next file without bridging the gap.
            source_errors.append({"path": str(path), "error": str(exc)})
            break_all()
        finally:
            closer = getattr(rows, "close", None)
            if callable(closer):
                closer()
        if anomalies:
            source_anomalies.append({
                "path": str(path),
                "anomalies": [getattr(a, "__dict__", {"kind": str(a)}) for a in anomalies],
            })

    break_all()
    return {
        "cutoffs_before_ms": cutoffs,
        "intervals": intervals,
        "rows_seen": rows_seen,
        "source_errors": source_errors,
        "source_anomalies": source_anomalies,
    }


def apply_repair(
    conn: sqlite3.Connection,
    collected: Mapping[str, Any],
    *,
    apply: bool,
) -> Dict[str, int]:
    intervals = collected.get("intervals") or {}
    inserted: Dict[str, int] = {kind: 0 for kind, _ in KINDS}
    if not apply:
        for kind, _field in KINDS:
            inserted[kind] = len(intervals.get(kind) or [])
        return inserted

    conn.execute("BEGIN IMMEDIATE")
    try:
        for kind, _field in KINDS:
            for run_id, start_ms, end_ms, value in intervals.get(kind) or []:
                conn.execute(
                    """
                    INSERT INTO graph_intervals(
                        kind,run_id,entity_id,start_ms,end_ms,value_code,source,quality
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (kind, run_id, None, int(start_ms), int(end_ms), str(value), SOURCE, "OBSERVED"),
                )
                inserted[kind] += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return inserted


def repair(
    config_path: Path,
    *,
    runtime_root: Optional[Path] = None,
    explicit_dirs: Sequence[str] = (),
    explicit_files: Sequence[str] = (),
    max_gap_ms: int = DEFAULT_MAX_GAP_MS,
    apply: bool = False,
) -> Dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    if not config_path.is_file():
        return {"status": "error", "reason": "CONFIG_MISSING", "config": str(config_path)}
    with _runtime_root_context(runtime_root) as active_root:
        config = _load_json(config_path)
        db_path = Path(resolve_measurement_db_path(dict(config))).expanduser().resolve()
        detection = detect_measurement_db_backend(str(db_path))
        if detection.get("backend") != "v3":
            return {
                "status": "error",
                "reason": "GRAPH_DB_NOT_V3",
                "db_path": str(db_path),
                "backend": detection.get("backend"),
            }
        files = _ordered_files(config, config_path, explicit_dirs, explicit_files)
        if not files:
            return {"status": "error", "reason": "NO_V4_FILES", "db_path": str(db_path)}

        conn = sqlite3.connect(str(db_path), timeout=30.0)
        try:
            conn.execute("PRAGMA busy_timeout=30000")
            quick_before = _quick_check(conn)
            if quick_before != "ok":
                return {
                    "status": "error",
                    "reason": "GRAPH_DB_QUICK_CHECK_FAILED",
                    "quick_check": quick_before,
                    "db_path": str(db_path),
                }
            counts_before = _existing_counts(conn)
            collected = collect_repair_intervals(conn, files, max_gap_ms=max_gap_ms)
            planned = {kind: len((collected.get("intervals") or {}).get(kind) or []) for kind, _ in KINDS}
            inserted = apply_repair(conn, collected, apply=apply)
            counts_after = _existing_counts(conn) if apply else dict(counts_before)
            quick_after = _quick_check(conn)
        finally:
            conn.close()

        status = "ok" if quick_after == "ok" and not collected.get("source_errors") else "warning"
        reason = "REPAIRED" if apply else "DRY_RUN"
        if collected.get("source_errors"):
            reason = "REPAIRED_WITH_SOURCE_ERRORS" if apply else "DRY_RUN_WITH_SOURCE_ERRORS"
        return {
            "status": status,
            "reason": reason,
            "schema": "ZEC_V14_1_3_GRAPH_CONTROL_STATE_SUFFIX_REPAIR_V1",
            "runtime_root": str(active_root) if active_root is not None else str(Path.cwd()),
            "config": str(config_path),
            "db_path": str(db_path),
            "v4_files": len(files),
            "rows_seen": collected.get("rows_seen"),
            "max_gap_ms": int(max_gap_ms),
            "apply": bool(apply),
            "quick_check_before": quick_before,
            "quick_check_after": quick_after,
            "counts_before": counts_before,
            "cutoffs_before_ms": collected.get("cutoffs_before_ms"),
            "planned_intervals": planned,
            "inserted_intervals": inserted if apply else {kind: 0 for kind, _ in KINDS},
            "counts_after": counts_after,
            "source_errors": collected.get("source_errors") or [],
            "source_anomalies": collected.get("source_anomalies") or [],
            "control_readiness_impact": "NONE",
            "numeric_graph_data_mutated": False,
            "command_events_mutated": False,
            "control_reason_mutated": False,
        }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--source-dir", action="append", default=[])
    parser.add_argument("--source-file", action="append", default=[])
    parser.add_argument("--max-gap-ms", type=int, default=DEFAULT_MAX_GAP_MS)
    parser.add_argument("--apply", action="store_true", help="Actually insert the targeted repair intervals")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = repair(
        Path(args.config),
        runtime_root=Path(args.runtime_root) if args.runtime_root else None,
        explicit_dirs=args.source_dir,
        explicit_files=args.source_file,
        max_gap_ms=max(1, int(args.max_gap_ms)),
        apply=bool(args.apply),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(result)
    return 0 if result.get("status") in {"ok", "warning"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
