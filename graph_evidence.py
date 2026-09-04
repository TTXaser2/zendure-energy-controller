# SPDX-License-Identifier: AGPL-3.0-or-later
"""Graph-Core V3 coverage, retention and evidence helpers.

Storage/query only: no controller decisions and no command side effects.
WP5 distinguishes observed data from deliberate retention, missing historical
instrumentation, topology inapplicability and actual source gaps.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

EVIDENCE_AVAILABLE = "AVAILABLE"
EVIDENCE_PURGED = "PURGED_BY_RETENTION"
EVIDENCE_NOT_INSTRUMENTED = "NOT_INSTRUMENTED"
EVIDENCE_GAP = "GAP"
EVIDENCE_NOT_APPLICABLE = "NOT_APPLICABLE"
EVIDENCE_NO_SOURCE = "NO_SOURCE_EVIDENCE"
EVIDENCE_UNKNOWN = "UNKNOWN_EVIDENCE"
EVIDENCE_STATES = {
    EVIDENCE_AVAILABLE, EVIDENCE_PURGED, EVIDENCE_NOT_INSTRUMENTED,
    EVIDENCE_GAP, EVIDENCE_NOT_APPLICABLE, EVIDENCE_NO_SOURCE,
    EVIDENCE_UNKNOWN,
}

RESOLUTION_HIGHRES = "highres"
RESOLUTION_1MIN = "1min"
DATA_CLASS_SYSTEM_HIGHRES = "SYSTEM_HIGHRES"
DATA_CLASS_ENTITY_HIGHRES = "ENTITY_HIGHRES"


class RetentionError(RuntimeError):
    pass


def ensure_evidence_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_availability_segments (
            segment_id INTEGER PRIMARY KEY,
            series_id TEXT NOT NULL,
            entity_id INTEGER,
            resolution TEXT NOT NULL,
            from_ms INTEGER NOT NULL,
            to_ms INTEGER NOT NULL,
            status TEXT NOT NULL,
            source TEXT NOT NULL,
            quality TEXT NOT NULL DEFAULT 'OBSERVED',
            operation_id TEXT,
            details_json TEXT,
            FOREIGN KEY(entity_id) REFERENCES graph_entities(entity_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_graph_availability_lookup "
        "ON graph_availability_segments(series_id,entity_id,resolution,from_ms,to_ms)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_instrumentation_timeline (
            instrumentation_id INTEGER PRIMARY KEY,
            series_id TEXT NOT NULL,
            entity_id INTEGER,
            effective_from_ms INTEGER NOT NULL,
            state TEXT NOT NULL,
            source TEXT NOT NULL,
            details_json TEXT,
            FOREIGN KEY(entity_id) REFERENCES graph_entities(entity_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_graph_instrumentation_lookup "
        "ON graph_instrumentation_timeline(series_id,entity_id,effective_from_ms)"
    )
    existing = {str(r[1]) for r in conn.execute("PRAGMA table_info(graph_retention_ledger)")}
    for name, decl in {
        "operation_id": "TEXT",
        "stable_entity_id": "TEXT",
        "details_json": "TEXT",
    }.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE graph_retention_ledger ADD COLUMN {name} {decl}")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_graph_retention_operation "
        "ON graph_retention_ledger(operation_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_graph_retention_range "
        "ON graph_retention_ledger(data_class,entity_id,from_ms,to_ms)"
    )


def _compact_json(value: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not value:
        return None
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _merge_ranges(ranges: Iterable[Tuple[int, int]], *, join_gap_ms: int = 1) -> List[Tuple[int, int]]:
    ordered = sorted((int(a), int(b)) for a, b in ranges if int(b) >= int(a))
    if not ordered:
        return []
    out: List[Tuple[int, int]] = []
    start, end = ordered[0]
    for a, b in ordered[1:]:
        if a <= end + int(join_gap_ms):
            end = max(end, b)
        else:
            out.append((start, end))
            start, end = a, b
    out.append((start, end))
    return out


def record_instrumentation(
    conn: sqlite3.Connection, *, series_id: str, effective_from_ms: int,
    state: str = "INSTRUMENTED", source: str = "GRAPH_CORE_V3",
    entity_id: Optional[int] = None, details: Optional[Mapping[str, Any]] = None,
) -> None:
    row = conn.execute(
        "SELECT state,effective_from_ms FROM graph_instrumentation_timeline "
        "WHERE series_id=? AND entity_id IS ? ORDER BY effective_from_ms DESC LIMIT 1",
        (str(series_id), entity_id),
    ).fetchone()
    if row is not None and str(row[0]) == str(state):
        return
    conn.execute(
        "INSERT INTO graph_instrumentation_timeline(series_id,entity_id,effective_from_ms,state,source,details_json) "
        "VALUES(?,?,?,?,?,?)",
        (str(series_id), entity_id, int(effective_from_ms), str(state), str(source), _compact_json(details)),
    )


def _insert_segment(
    conn: sqlite3.Connection, *, series_id: str, entity_id: Optional[int],
    resolution: str, from_ms: int, to_ms: int, status: str, source: str,
    quality: str = "OBSERVED", operation_id: Optional[str] = None,
    details: Optional[Mapping[str, Any]] = None,
) -> None:
    if status not in EVIDENCE_STATES:
        raise ValueError(f"UNKNOWN_EVIDENCE_STATUS:{status}")
    if int(to_ms) < int(from_ms):
        raise ValueError("INVALID_EVIDENCE_RANGE")
    conn.execute(
        "INSERT INTO graph_availability_segments(series_id,entity_id,resolution,from_ms,to_ms,status,source,quality,operation_id,details_json) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (str(series_id), entity_id, str(resolution), int(from_ms), int(to_ms), str(status),
         str(source), str(quality), operation_id, _compact_json(details)),
    )


def replace_availability_from_1min(conn: sqlite3.Connection) -> None:
    """Rebuild compact durable availability from permanent 1-minute tables."""
    from graph_core_v3 import ENTITY_SERIES, SYSTEM_SERIES
    conn.execute("DELETE FROM graph_availability_segments WHERE source IN ('DERIVED_1MIN','DERIVED_ENTITY_1MIN')")
    for spec in SYSTEM_SERIES:
        count_col = f"{spec.column}_count"
        buckets = [int(r[0]) for r in conn.execute(
            f"SELECT bucket_start_ms FROM measurement_1min WHERE {count_col}>0 ORDER BY bucket_start_ms"
        )]
        if not buckets:
            continue
        ranges = _merge_ranges(((b, b + 59_999) for b in buckets), join_gap_ms=1)
        for a, b in ranges:
            record_instrumentation(conn, series_id=spec.series_id, effective_from_ms=a, source="DERIVED_1MIN")
            _insert_segment(conn, series_id=spec.series_id, entity_id=None, resolution=RESOLUTION_1MIN,
                            from_ms=a, to_ms=b, status=EVIDENCE_AVAILABLE, source="DERIVED_1MIN")
            _insert_segment(conn, series_id=spec.series_id, entity_id=None, resolution=RESOLUTION_HIGHRES,
                            from_ms=a, to_ms=b, status=EVIDENCE_AVAILABLE, source="DERIVED_1MIN",
                            quality="MINUTE_GRANULAR_HIGHRES_EVIDENCE")

    for entity_row in conn.execute("SELECT entity_id FROM graph_entities WHERE storage_binding='ENTITY_TABLE'").fetchall():
        entity_id = int(entity_row[0])
        for spec in ENTITY_SERIES:
            count_col = f"{spec.column}_count"
            buckets = [int(r[0]) for r in conn.execute(
                f"SELECT bucket_start_ms FROM measurement_entity_1min WHERE entity_id=? AND {count_col}>0 ORDER BY bucket_start_ms",
                (entity_id,),
            )]
            if not buckets:
                continue
            for a, b in _merge_ranges(((x, x + 59_999) for x in buckets), join_gap_ms=1):
                record_instrumentation(conn, series_id=spec.series_id, entity_id=entity_id,
                                       effective_from_ms=a, source="DERIVED_ENTITY_1MIN")
                _insert_segment(conn, series_id=spec.series_id, entity_id=entity_id, resolution=RESOLUTION_1MIN,
                                from_ms=a, to_ms=b, status=EVIDENCE_AVAILABLE, source="DERIVED_ENTITY_1MIN")
                _insert_segment(conn, series_id=spec.series_id, entity_id=entity_id, resolution=RESOLUTION_HIGHRES,
                                from_ms=a, to_ms=b, status=EVIDENCE_AVAILABLE, source="DERIVED_ENTITY_1MIN",
                                quality="MINUTE_GRANULAR_HIGHRES_EVIDENCE")


def _coverage_missing_system(conn: sqlite3.Connection, from_ms: int, to_ms: int) -> List[Dict[str, Any]]:
    from graph_core_v3 import SYSTEM_SERIES
    missing: List[Dict[str, Any]] = []
    for spec in SYSTEM_SERIES:
        raw_buckets = [int(r[0]) for r in conn.execute(
            f"SELECT DISTINCT (ts_ms/60000)*60000 FROM measurement_raw "
            f"WHERE ts_ms>=? AND ts_ms<=? AND {spec.column} IS NOT NULL ORDER BY 1",
            (int(from_ms), int(to_ms)),
        )]
        if not raw_buckets:
            continue
        count_col = f"{spec.column}_count"
        longterm = {int(r[0]) for r in conn.execute(
            f"SELECT bucket_start_ms FROM measurement_1min WHERE bucket_start_ms>=? AND bucket_start_ms<=? AND {count_col}>0",
            ((int(from_ms)//60000)*60000, (int(to_ms)//60000)*60000),
        )}
        for bucket in raw_buckets:
            if bucket not in longterm:
                missing.append({"series_id": spec.series_id, "bucket_start_ms": bucket})
    return missing


def _coverage_missing_entity(conn: sqlite3.Connection, entity_id: int, from_ms: int, to_ms: int) -> List[Dict[str, Any]]:
    from graph_core_v3 import ENTITY_SERIES
    missing: List[Dict[str, Any]] = []
    for spec in ENTITY_SERIES:
        raw_buckets = [int(r[0]) for r in conn.execute(
            f"SELECT DISTINCT (ts_ms/60000)*60000 FROM measurement_entity_raw "
            f"WHERE entity_id=? AND ts_ms>=? AND ts_ms<=? AND {spec.column} IS NOT NULL ORDER BY 1",
            (int(entity_id), int(from_ms), int(to_ms)),
        )]
        if not raw_buckets:
            continue
        count_col = f"{spec.column}_count"
        longterm = {int(r[0]) for r in conn.execute(
            f"SELECT bucket_start_ms FROM measurement_entity_1min WHERE entity_id=? AND bucket_start_ms>=? AND bucket_start_ms<=? AND {count_col}>0",
            (int(entity_id), (int(from_ms)//60000)*60000, (int(to_ms)//60000)*60000),
        )}
        for bucket in raw_buckets:
            if bucket not in longterm:
                missing.append({"series_id": spec.series_id, "entity_id": int(entity_id), "bucket_start_ms": bucket})
    return missing


def _operation_signature(*, from_ms: int, to_ms: int, reason: str,
                         source_generation: Optional[str], entity_ids: Sequence[int]) -> str:
    payload = {
        "from_ms": int(from_ms), "to_ms": int(to_ms), "reason": str(reason),
        "source_generation": source_generation, "entity_ids": [int(x) for x in entity_ids],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _existing_operation(conn: sqlite3.Connection, operation_id: str) -> Optional[str]:
    rows = conn.execute(
        "SELECT details_json FROM graph_retention_ledger WHERE operation_id=? ORDER BY ledger_id",
        (str(operation_id),),
    ).fetchall()
    if not rows:
        return None
    found = set()
    for row in rows:
        try:
            details = json.loads(row[0] or "{}")
        except Exception:
            details = {}
        sig = str(details.get("operation_signature") or "")
        if sig:
            found.add(sig)
    if len(found) == 1:
        return next(iter(found))
    if not found:
        return "LEGACY_OPERATION_WITHOUT_SIGNATURE"
    return "CONFLICTING_STORED_OPERATION"


def purge_highres(
    conn: sqlite3.Connection, *, from_ms: int, to_ms: int, operation_id: str,
    reason: str, source_generation: Optional[str] = None,
    entity_ids: Optional[Sequence[int]] = None, performed_at_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """Atomically purge high-res only after proving durable per-series 1min coverage."""
    ensure_evidence_schema(conn)
    start, end = int(from_ms), int(to_ms)
    if end < start:
        raise RetentionError("RETENTION_INVALID_RANGE")
    op = str(operation_id or "").strip()
    if not op:
        raise RetentionError("RETENTION_OPERATION_ID_REQUIRED")
    why = str(reason or "").strip()
    if not why:
        raise RetentionError("RETENTION_REASON_REQUIRED")
    ids = sorted(set(int(x) for x in (entity_ids or [])))
    signature = _operation_signature(from_ms=start, to_ms=end, reason=why,
                                     source_generation=source_generation, entity_ids=ids)
    existing = _existing_operation(conn, op)
    if existing is not None:
        if existing == signature:
            return {"status": "already_applied", "operation_id": op, "operation_signature": signature}
        raise RetentionError("RETENTION_OPERATION_ID_CONFLICT")

    system_missing = _coverage_missing_system(conn, start, end)
    entity_missing: Dict[int, List[Dict[str, Any]]] = {}
    for entity_id in ids:
        miss = _coverage_missing_entity(conn, entity_id, start, end)
        if miss:
            entity_missing[entity_id] = miss
    if system_missing or entity_missing:
        raise RetentionError("RETENTION_LONGTERM_COVERAGE_INCOMPLETE")

    now_ms = int(performed_at_ms if performed_at_ms is not None else time.time() * 1000)
    details = {"operation_signature": signature, "range_semantics": "inclusive", "longterm_guard": "series_bucket_exact"}
    try:
        conn.execute("BEGIN IMMEDIATE")
        system_before = int(conn.execute(
            "SELECT COUNT(*) FROM measurement_raw WHERE ts_ms>=? AND ts_ms<=?", (start, end)
        ).fetchone()[0])
        conn.execute("DELETE FROM measurement_raw WHERE ts_ms>=? AND ts_ms<=?", (start, end))
        conn.execute(
            "INSERT INTO graph_retention_ledger(from_ms,to_ms,data_class,entity_id,action,reason,performed_at_ms,source_generation,operation_id,stable_entity_id,details_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (start, end, DATA_CLASS_SYSTEM_HIGHRES, None, "PURGE", why, now_ms,
             source_generation, op, None, _compact_json(details)),
        )
        from graph_core_v3 import ENTITY_SERIES, SYSTEM_SERIES
        for spec in SYSTEM_SERIES:
            _insert_segment(conn, series_id=spec.series_id, entity_id=None, resolution=RESOLUTION_HIGHRES,
                            from_ms=start, to_ms=end, status=EVIDENCE_PURGED, source="RETENTION_LEDGER",
                            operation_id=op, details=details)

        entity_deleted: Dict[int, int] = {}
        for entity_id in ids:
            stable = conn.execute("SELECT stable_id FROM graph_entities WHERE entity_id=?", (entity_id,)).fetchone()
            if stable is None:
                raise RetentionError(f"RETENTION_UNKNOWN_ENTITY:{entity_id}")
            count = int(conn.execute(
                "SELECT COUNT(*) FROM measurement_entity_raw WHERE entity_id=? AND ts_ms>=? AND ts_ms<=?",
                (entity_id, start, end),
            ).fetchone()[0])
            conn.execute("DELETE FROM measurement_entity_raw WHERE entity_id=? AND ts_ms>=? AND ts_ms<=?",
                         (entity_id, start, end))
            entity_deleted[entity_id] = count
            conn.execute(
                "INSERT INTO graph_retention_ledger(from_ms,to_ms,data_class,entity_id,action,reason,performed_at_ms,source_generation,operation_id,stable_entity_id,details_json) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (start, end, DATA_CLASS_ENTITY_HIGHRES, entity_id, "PURGE", why, now_ms,
                 source_generation, op, str(stable[0]), _compact_json(details)),
            )
            for spec in ENTITY_SERIES:
                _insert_segment(conn, series_id=spec.series_id, entity_id=entity_id, resolution=RESOLUTION_HIGHRES,
                                from_ms=start, to_ms=end, status=EVIDENCE_PURGED, source="RETENTION_LEDGER",
                                operation_id=op, details=details)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"status": "ok", "operation_id": op, "operation_signature": signature,
            "system_rows_deleted": system_before, "entity_rows_deleted": entity_deleted}


def copy_retention_ledger(source_path: str, dest: sqlite3.Connection) -> int:
    if not source_path:
        return 0
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True, timeout=30.0)
    source.row_factory = sqlite3.Row
    try:
        if source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_retention_ledger'").fetchone() is None:
            return 0
        cols = {str(r[1]) for r in source.execute("PRAGMA table_info(graph_retention_ledger)")}
        rows = source.execute("SELECT * FROM graph_retention_ledger ORDER BY ledger_id").fetchall()
        copied = 0
        for row in rows:
            stable = row["stable_entity_id"] if "stable_entity_id" in cols else None
            if not stable and row["entity_id"] is not None:
                ent = source.execute("SELECT stable_id FROM graph_entities WHERE entity_id=?", (row["entity_id"],)).fetchone()
                stable = ent[0] if ent else None
            entity_id = None
            if stable:
                dest_row = dest.execute("SELECT entity_id FROM graph_entities WHERE stable_id=?", (stable,)).fetchone()
                entity_id = int(dest_row[0]) if dest_row else None
            operation_id = row["operation_id"] if "operation_id" in cols else None
            details_json = row["details_json"] if "details_json" in cols else None
            dest.execute(
                "INSERT INTO graph_retention_ledger(from_ms,to_ms,data_class,entity_id,action,reason,performed_at_ms,source_generation,operation_id,stable_entity_id,details_json) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (int(row["from_ms"]), int(row["to_ms"]), str(row["data_class"]), entity_id,
                 str(row["action"]), str(row["reason"]), int(row["performed_at_ms"]), row["source_generation"],
                 operation_id, stable, details_json),
            )
            copied += 1
        return copied
    finally:
        source.close()


def reapply_retention_ledger(conn: sqlite3.Connection) -> Dict[str, int]:
    """Re-delete copied high-res retention ranges; permanent 1min stays untouched."""
    from graph_core_v3 import ENTITY_SERIES, SYSTEM_SERIES
    system_deleted = 0
    entity_deleted = 0
    rows = conn.execute(
        "SELECT ledger_id,from_ms,to_ms,data_class,entity_id,stable_entity_id,operation_id FROM graph_retention_ledger "
        "WHERE action='PURGE' ORDER BY ledger_id"
    ).fetchall()
    for row in rows:
        start, end, data_class = int(row[1]), int(row[2]), str(row[3])
        operation_id = row[6]
        if data_class == DATA_CLASS_SYSTEM_HIGHRES:
            count = int(conn.execute("SELECT COUNT(*) FROM measurement_raw WHERE ts_ms>=? AND ts_ms<=?", (start, end)).fetchone()[0])
            conn.execute("DELETE FROM measurement_raw WHERE ts_ms>=? AND ts_ms<=?", (start, end))
            system_deleted += count
            for spec in SYSTEM_SERIES:
                _insert_segment(conn, series_id=spec.series_id, entity_id=None, resolution=RESOLUTION_HIGHRES,
                                from_ms=start, to_ms=end, status=EVIDENCE_PURGED,
                                source="RETENTION_LEDGER_REAPPLIED", operation_id=operation_id)
        elif data_class == DATA_CLASS_ENTITY_HIGHRES:
            stable = row[5]
            target_id = None
            if stable:
                found = conn.execute("SELECT entity_id FROM graph_entities WHERE stable_id=?", (stable,)).fetchone()
                target_id = int(found[0]) if found else None
            elif row[4] is not None:
                target_id = int(row[4])
            if target_id is None:
                continue
            conn.execute("UPDATE graph_retention_ledger SET entity_id=? WHERE ledger_id=?", (target_id, int(row[0])))
            count = int(conn.execute(
                "SELECT COUNT(*) FROM measurement_entity_raw WHERE entity_id=? AND ts_ms>=? AND ts_ms<=?",
                (target_id, start, end),
            ).fetchone()[0])
            conn.execute("DELETE FROM measurement_entity_raw WHERE entity_id=? AND ts_ms>=? AND ts_ms<=?",
                         (target_id, start, end))
            entity_deleted += count
            for spec in ENTITY_SERIES:
                _insert_segment(conn, series_id=spec.series_id, entity_id=target_id, resolution=RESOLUTION_HIGHRES,
                                from_ms=start, to_ms=end, status=EVIDENCE_PURGED,
                                source="RETENTION_LEDGER_REAPPLIED", operation_id=operation_id)
    return {"system_rows_deleted": int(system_deleted), "entity_rows_deleted": int(entity_deleted)}


def evidence_rows(
    conn: sqlite3.Connection, *, series_id: str, resolution: str,
    entity_id: Optional[int] = None, start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> List[Dict[str, Any]]:
    clauses = ["series_id=?", "resolution=?", "entity_id IS ?"]
    params: List[Any] = [str(series_id), str(resolution), entity_id]
    if start_ms is not None:
        clauses.append("to_ms>=?"); params.append(int(start_ms))
    if end_ms is not None:
        clauses.append("from_ms<=?"); params.append(int(end_ms))
    rows = conn.execute(
        "SELECT from_ms,to_ms,status,source,quality,operation_id,details_json FROM graph_availability_segments WHERE "
        + " AND ".join(clauses) + " ORDER BY from_ms,segment_id", tuple(params),
    ).fetchall()
    return [{"from_ms": int(r[0]), "to_ms": int(r[1]), "status": str(r[2]), "source": str(r[3]),
             "quality": str(r[4]), "operation_id": r[5]} for r in rows]


def _extend_available_segment(
    conn: sqlite3.Connection, *, series_id: str, entity_id: Optional[int], resolution: str,
    from_ms: int, to_ms: int, source: str, quality: str, max_join_gap_ms: int,
) -> None:
    row = conn.execute(
        "SELECT segment_id,from_ms,to_ms FROM graph_availability_segments "
        "WHERE series_id=? AND entity_id IS ? AND resolution=? AND status=? AND source=? "
        "ORDER BY to_ms DESC LIMIT 1",
        (str(series_id), entity_id, str(resolution), EVIDENCE_AVAILABLE, str(source)),
    ).fetchone()
    if row is not None and int(from_ms) <= int(row[2]) + int(max_join_gap_ms):
        conn.execute("UPDATE graph_availability_segments SET from_ms=MIN(from_ms,?),to_ms=MAX(to_ms,?) WHERE segment_id=?",
                     (int(from_ms), int(to_ms), int(row[0])))
        return
    _insert_segment(conn, series_id=series_id, entity_id=entity_id, resolution=resolution,
                    from_ms=from_ms, to_ms=to_ms, status=EVIDENCE_AVAILABLE, source=source, quality=quality)


def record_live_batch_evidence(conn: sqlite3.Connection, rows: Sequence[Mapping[str, Any]], *, run_id: int) -> None:
    """Persist compact, gap-aware evidence in the same transaction as measurements."""
    if not rows:
        return
    from graph_core_v3 import ENTITY_SERIES, SYSTEM_SERIES, extract_system_sample
    series_times: Dict[str, List[int]] = {}
    for row in rows:
        sample = extract_system_sample(row)
        if sample is None:
            continue
        ts = int(sample["ts_ms"])
        for spec in SYSTEM_SERIES:
            if sample.get(spec.column) is not None:
                series_times.setdefault(spec.series_id, []).append(ts)
    for sid, timestamps in series_times.items():
        ordered = sorted(set(int(ts) for ts in timestamps))
        if not ordered:
            continue
        record_instrumentation(conn, series_id=sid, effective_from_ms=ordered[0], source="LIVE_NON_NULL")
        for a, b in _merge_ranges(((ts, ts) for ts in ordered), join_gap_ms=10_000):
            _extend_available_segment(conn, series_id=sid, entity_id=None, resolution=RESOLUTION_HIGHRES,
                                      from_ms=a, to_ms=b, source="LIVE", quality="OBSERVED", max_join_gap_ms=10_000)
        buckets = sorted({(ts // 60_000) * 60_000 for ts in ordered})
        for a, b in _merge_ranges(((bucket, bucket + 59_999) for bucket in buckets), join_gap_ms=1):
            _extend_available_segment(conn, series_id=sid, entity_id=None, resolution=RESOLUTION_1MIN,
                                      from_ms=a, to_ms=b, source="LIVE", quality="MINUTE_BUCKET", max_join_gap_ms=1)
    if not series_times:
        return
    start = min(min(times) for times in series_times.values() if times)
    end = max(max(times) for times in series_times.values() if times)
    entity_ids = [int(r[0]) for r in conn.execute(
        "SELECT entity_id FROM graph_entities WHERE storage_binding='ENTITY_TABLE' "
        "AND last_seen_ms>=? AND last_seen_ms<=? ORDER BY entity_id", (start, end)
    ).fetchall()]
    if not entity_ids:
        return
    columns = ",".join(spec.column for spec in ENTITY_SERIES)
    for entity_id in entity_ids:
        observed = conn.execute(
            f"SELECT ts_ms,{columns} FROM measurement_entity_raw WHERE entity_id=? AND ts_ms>=? AND ts_ms<=? ORDER BY ts_ms",
            (entity_id, start, end),
        ).fetchall()
        if not observed:
            continue
        for offset, spec in enumerate(ENTITY_SERIES, start=1):
            timestamps = [int(row[0]) for row in observed if row[offset] is not None]
            if not timestamps:
                continue
            record_instrumentation(conn, series_id=spec.series_id, entity_id=entity_id,
                                   effective_from_ms=timestamps[0], source="LIVE_ENTITY_NON_NULL")
            for a, b in _merge_ranges(((ts, ts) for ts in timestamps), join_gap_ms=10_000):
                _extend_available_segment(conn, series_id=spec.series_id, entity_id=entity_id, resolution=RESOLUTION_HIGHRES,
                                          from_ms=a, to_ms=b, source="LIVE_ENTITY", quality="OBSERVED", max_join_gap_ms=10_000)
            buckets = sorted({(ts // 60_000) * 60_000 for ts in timestamps})
            for a, b in _merge_ranges(((bucket, bucket + 59_999) for bucket in buckets), join_gap_ms=1):
                _extend_available_segment(conn, series_id=spec.series_id, entity_id=entity_id, resolution=RESOLUTION_1MIN,
                                          from_ms=a, to_ms=b, source="LIVE_ENTITY", quality="MINUTE_BUCKET", max_join_gap_ms=1)
