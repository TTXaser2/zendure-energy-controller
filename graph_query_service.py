# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only Graph Core V3 query service and canonical series catalog.

WP3 contract:
- never creates or mutates a database while serving graph reads;
- uses raw high resolution for short inspector/zoom windows and 1-minute
  aggregates for wider overview windows;
- exposes stable technical series ids and presentation/i18n keys separately;
- keeps sparse intervals/events/config/topology/retention as temporal evidence;
- uses a small WAL-sensitive cache so live writes cannot leave stale graph
  results hidden behind an unchanged main SQLite file.
"""
from __future__ import annotations

import copy
import json
import heapq
import os
import sqlite3
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from graph_core_v3 import (
    ENTITY_BINDING_ENTITY_TABLE,
    ENTITY_BINDING_SYSTEM_PRIMARY,
    ENTITY_BINDING_SYSTEM_ZENDURE,
    ENTITY_SERIES,
    ENTITY_SERIES_BY_ID,
    SYSTEM_ENTITY_BINDINGS,
    SYSTEM_SERIES,
    SYSTEM_SERIES_BY_ID,
    EntitySeriesSpec,
    SeriesSpec,
    decode_scaled,
)
from graph_evidence import (
    EVIDENCE_AVAILABLE, EVIDENCE_GAP, EVIDENCE_NO_SOURCE,
    EVIDENCE_NOT_APPLICABLE, EVIDENCE_NOT_INSTRUMENTED, EVIDENCE_PURGED,
    EVIDENCE_UNKNOWN, evidence_rows,
)

FORMAT_COLUMNAR_V1 = "columnar_v1"
DEFAULT_MAX_WINDOW_MS = 48 * 60 * 60 * 1000
DEFAULT_HIGHRES_THRESHOLD_MS = 2 * 60 * 60 * 1000
DEFAULT_EVENT_LIMIT = 5000
CACHE_MAX_ENTRIES = 4
CACHE_TTL_S = 15.0


_TEMPORAL_TYPES: Dict[str, str] = {
    "grid_power_w": "continuous",
    "raw_grid_power_w": "continuous",
    "control_grid_power_w": "continuous",
    "control_grid_power_smoothed_w": "continuous",
    "pv_power_w": "continuous",
    "house_power_w": "continuous",
    "zendure_actual_power_w": "continuous",
    "zendure_soc_percent": "continuous",
    "primary_power_w": "continuous",
    "primary_soc_percent": "continuous",
    "target_raw_w": "target",
    "target_limited_w": "target",
    "target_filtered_w": "target",
    "target_step_limited_w": "target",
    "target_final_w": "target",
    "command_desired_target_w": "target",
    "command_readback_target_w": "target",
}

_LABEL_KEYS: Dict[str, str] = {
    series_id: f"graph.series.{series_id}" for series_id in _TEMPORAL_TYPES
}

_ENTITY_TEMPORAL_TYPES: Dict[str, str] = {
    "power_w": "continuous",
    "soc_percent": "continuous",
    "target_w": "target",
    "readback_target_w": "target",
}
_ENTITY_LABEL_KEYS: Dict[str, str] = {
    series_id: f"graph.entity_series.{series_id}" for series_id in _ENTITY_TEMPORAL_TYPES
}


class GraphQueryError(RuntimeError):
    pass


@dataclass(frozen=True)
class QueryPlan:
    source: str  # raw | 1min
    resolution_ms: int
    reason: str


def canonical_series_catalog() -> List[Dict[str, Any]]:
    """Return stable machine ids plus presentation metadata.

    label_key is deliberately not the German/English label itself. UI text can
    change or be translated without changing the persisted/query series id.
    """
    result: List[Dict[str, Any]] = []
    for spec in SYSTEM_SERIES:
        result.append({
            "series_id": spec.series_id,
            "label_key": _LABEL_KEYS[spec.series_id],
            "unit": spec.unit,
            "temporal_type": _TEMPORAL_TYPES[spec.series_id],
            "entity_scope": "system",
            "storage_encoding": "scaled_integer_v1",
            "storage_scale": int(spec.scale),
            "aggregation": spec.aggregation,
            "resolutions": ["highres", "1min"],
        })
    return result


def canonical_entity_series_catalog() -> List[Dict[str, Any]]:
    return [
        {
            "series_id": spec.series_id,
            "label_key": _ENTITY_LABEL_KEYS[spec.series_id],
            "unit": spec.unit,
            "temporal_type": _ENTITY_TEMPORAL_TYPES[spec.series_id],
            "entity_scope": "entity",
            "storage_encoding": "scaled_integer_v1",
            "storage_scale": int(spec.scale),
            "aggregation": spec.aggregation,
            "resolutions": ["highres", "1min"],
        }
        for spec in ENTITY_SERIES
    ]


def _db_fingerprint(path: str) -> Tuple[Any, ...]:
    """Fingerprint main DB plus WAL without opening SQLite.

    In WAL mode recent commits can exist only in `<db>-wal`; therefore main DB
    mtime/size alone is not a sufficient cache invalidation signal.
    """
    parts: List[Any] = [os.path.abspath(path)]
    for candidate in (path, path + "-wal"):
        try:
            st = os.stat(candidate)
            size = int(st.st_size)
            # SQLite may create/touch an empty WAL during a read-only open.
            # Its mtime carries no committed data and must not defeat caching.
            mtime_ns = int(st.st_mtime_ns) if size > 0 or candidate == path else 0
            parts.extend((candidate, size, mtime_ns))
        except FileNotFoundError:
            parts.extend((candidate, 0, 0))
    return tuple(parts)


def _readonly_connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    return conn


def _schema_version(conn: sqlite3.Connection) -> Optional[int]:
    try:
        row = conn.execute("SELECT value FROM measurement_meta WHERE key='schema_version'").fetchone()
        return int(row[0]) if row is not None else None
    except Exception:
        return None


def plan_query(start_ms: int, end_ms: int, *, resolution: str = "auto", purpose: str = "overview") -> QueryPlan:
    start_ms, end_ms = int(start_ms), int(end_ms)
    if end_ms <= start_ms:
        raise GraphQueryError("INVALID_TIME_RANGE")
    span = end_ms - start_ms
    requested = str(resolution or "auto").strip().lower()
    if requested in {"raw", "highres", "high_res"}:
        return QueryPlan("raw", 0, "explicit_highres")
    if requested in {"1min", "minute", "60s"}:
        return QueryPlan("1min", 60_000, "explicit_1min")
    if requested != "auto":
        raise GraphQueryError("INVALID_RESOLUTION")
    if str(purpose or "overview").lower() == "inspector":
        return QueryPlan("raw", 0, "inspector_requires_highres")
    if span <= DEFAULT_HIGHRES_THRESHOLD_MS:
        return QueryPlan("raw", 0, "short_window_highres")
    return QueryPlan("1min", 60_000, "wide_window_1min")


def _validate_series(series_ids: Optional[Sequence[str]]) -> Tuple[str, ...]:
    if not series_ids:
        return tuple(spec.series_id for spec in SYSTEM_SERIES)
    result: List[str] = []
    for item in series_ids:
        sid = str(item or "").strip()
        if not sid:
            continue
        if sid not in SYSTEM_SERIES_BY_ID:
            raise GraphQueryError(f"UNKNOWN_SERIES:{sid}")
        if sid not in result:
            result.append(sid)
    return tuple(result)


def _minute_value(row: sqlite3.Row, spec: SeriesSpec) -> Optional[float]:
    base = spec.column
    if spec.aggregation == "power":
        count = int(row[f"{base}_count"] or 0)
        total = row[f"{base}_sum"]
        if count <= 0 or total is None:
            return None
        return float(total) / float(count) / float(spec.scale)
    return decode_scaled(row[f"{base}_last"], scale=spec.scale)


def _query_numeric(
    conn: sqlite3.Connection,
    start_ms: int,
    end_ms: int,
    series_ids: Sequence[str],
    plan: QueryPlan,
) -> Dict[str, Any]:
    specs = [SYSTEM_SERIES_BY_ID[sid] for sid in series_ids]
    data: Dict[str, List[Optional[float]]] = {spec.series_id: [] for spec in specs}
    timestamps: List[int] = []
    sample_timestamps: List[int] = []
    sample_counts: List[int] = []
    quality: List[int] = []

    if plan.source == "raw":
        columns = ["ts_ms", "quality_flags"] + [spec.column for spec in specs]
        rows = conn.execute(
            f"SELECT {','.join(columns)} FROM measurement_raw "
            "WHERE ts_ms>=? AND ts_ms<=? ORDER BY ts_ms",
            (int(start_ms), int(end_ms)),
        ).fetchall()
        for row in rows:
            timestamps.append(int(row["ts_ms"]))
            sample_timestamps.append(int(row["ts_ms"]))
            sample_counts.append(1)
            quality.append(int(row["quality_flags"] or 0))
            for spec in specs:
                data[spec.series_id].append(decode_scaled(row[spec.column], scale=spec.scale))
    else:
        query_start = (int(start_ms) // 60_000) * 60_000
        needed: List[str] = ["bucket_start_ms", "last_ts_ms", "sample_count", "quality_or"]
        for spec in specs:
            for suffix in (("_sum", "_count") if spec.aggregation == "power" else ("_last",)):
                name = spec.column + suffix
                if name not in needed:
                    needed.append(name)
        rows = conn.execute(
            f"SELECT {','.join(needed)} FROM measurement_1min "
            "WHERE bucket_start_ms>=? AND bucket_start_ms<=? ORDER BY bucket_start_ms",
            (query_start, int(end_ms)),
        ).fetchall()
        for row in rows:
            timestamps.append(int(row["bucket_start_ms"]))
            sample_timestamps.append(int(row["last_ts_ms"] or row["bucket_start_ms"]))
            sample_counts.append(int(row["sample_count"] or 0))
            quality.append(int(row["quality_or"] or 0))
            for spec in specs:
                data[spec.series_id].append(_minute_value(row, spec))

    return {
        "format": FORMAT_COLUMNAR_V1,
        "timestamps_ms": timestamps,
        "sample_timestamps_ms": sample_timestamps,
        "sample_counts": sample_counts,
        "quality_flags": quality,
        "series": data,
    }


def _query_intervals(conn: sqlite3.Connection, start_ms: int, end_ms: int, *, limit: int) -> Dict[str, Any]:
    # Include the interval already active at the left edge by overlap semantics.
    rows = conn.execute(
        """
        SELECT interval_id,kind,run_id,entity_id,start_ms,end_ms,value_code,source,quality
          FROM graph_intervals
         WHERE start_ms<=? AND (end_ms IS NULL OR end_ms>?)
         ORDER BY start_ms,interval_id
         LIMIT ?
        """,
        (int(end_ms), int(start_ms), int(limit) + 1),
    ).fetchall()
    truncated = len(rows) > limit
    if truncated:
        rows = rows[:limit]
    return {
        "items": [dict(row) for row in rows],
        "truncated": truncated,
        "limit": int(limit),
    }


def _command_event_to_dict(row: Mapping[str, Any]) -> Dict[str, Any]:
    item = dict(row)
    for key in ("requested_target_dw", "desired_target_dw", "input_limit_dw", "output_limit_dw", "effect_reference_dw"):
        if key in item:
            item[key.replace("_dw", "_w")] = decode_scaled(item.pop(key), scale=10)
    return item


def _query_events(conn: sqlite3.Connection, start_ms: int, end_ms: int, *, limit: int) -> Dict[str, Any]:
    rows = conn.execute(
        """
        SELECT * FROM graph_command_events
         WHERE ts_ms>=? AND ts_ms<=?
         ORDER BY ts_ms,event_id
         LIMIT ?
        """,
        (int(start_ms), int(end_ms), int(limit) + 1),
    ).fetchall()
    truncated = len(rows) > limit
    if truncated:
        rows = rows[:limit]
    return {"items": [_command_event_to_dict(row) for row in rows], "truncated": truncated, "limit": int(limit)}


def _query_config(conn: sqlite3.Connection, start_ms: int, end_ms: int) -> List[Dict[str, Any]]:
    table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_config_timeline'").fetchone()
    if table is None:
        return []
    prior = conn.execute(
        "SELECT * FROM graph_config_timeline WHERE effective_from_ms<=? ORDER BY effective_from_ms DESC LIMIT 1",
        (int(start_ms),),
    ).fetchall()
    inside = conn.execute(
        "SELECT * FROM graph_config_timeline WHERE effective_from_ms>? AND effective_from_ms<=? ORDER BY effective_from_ms",
        (int(start_ms), int(end_ms)),
    ).fetchall()
    return [dict(row) for row in prior + inside]


def _query_topology(conn: sqlite3.Connection, start_ms: int, end_ms: int) -> List[Dict[str, Any]]:
    # State at the window start is the latest known state *per topology subject*,
    # not every historical topology row before start. This avoids duplicating
    # stale PRESENT/ABSENT transitions at the left edge.
    prior = conn.execute(
        """
        SELECT t.*
          FROM graph_topology_timeline AS t
          JOIN (
                SELECT COALESCE(entity_id,-1) AS eid, entity_type, COALESCE(role,'') AS topology_role, MAX(effective_from_ms) AS max_ts
                  FROM graph_topology_timeline
                 WHERE effective_from_ms<=?
                 GROUP BY COALESCE(entity_id,-1),entity_type,COALESCE(role,'')
               ) AS p
            ON COALESCE(t.entity_id,-1)=p.eid
           AND t.entity_type=p.entity_type
           AND COALESCE(t.role,'')=p.topology_role
           AND t.effective_from_ms=p.max_ts
         ORDER BY t.effective_from_ms,t.topology_id
        """,
        (int(start_ms),),
    ).fetchall()
    inside = conn.execute(
        "SELECT * FROM graph_topology_timeline WHERE effective_from_ms>? AND effective_from_ms<=? ORDER BY effective_from_ms,topology_id",
        (int(start_ms), int(end_ms)),
    ).fetchall()
    return [dict(row) for row in prior + inside]


def _query_runs(conn: sqlite3.Connection, start_ms: int, end_ms: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM graph_runs WHERE start_ms<=? AND (end_ms IS NULL OR end_ms>=?) ORDER BY start_ms,run_id",
        (int(end_ms), int(start_ms)),
    ).fetchall()
    return [dict(row) for row in rows]


def _query_retention(conn: sqlite3.Connection, start_ms: int, end_ms: int) -> List[Dict[str, Any]]:
    # WP5 retention evidence is optional for older V3 stores. History remains
    # readable; absence means simply that no retention evidence can enrich it.
    if not _table_exists(conn, "graph_retention_ledger"):
        return []
    rows = conn.execute(
        "SELECT * FROM graph_retention_ledger WHERE from_ms<=? AND to_ms>=? ORDER BY from_ms,ledger_id",
        (int(end_ms), int(start_ms)),
    ).fetchall()
    return [dict(row) for row in rows]


def _series_spans_one_scan(conn: sqlite3.Connection, ids: Sequence[str]) -> Dict[str, Tuple[Optional[int], Optional[int]]]:
    if not ids:
        return {}
    expressions: List[str] = []
    for index, sid in enumerate(ids):
        col = SYSTEM_SERIES_BY_ID[sid].column
        expressions.append(f"MIN(CASE WHEN {col} IS NOT NULL THEN ts_ms END) AS min_{index}")
        expressions.append(f"MAX(CASE WHEN {col} IS NOT NULL THEN ts_ms END) AS max_{index}")
    row = conn.execute("SELECT " + ",".join(expressions) + " FROM measurement_raw").fetchone()
    result: Dict[str, Tuple[Optional[int], Optional[int]]] = {}
    for index, sid in enumerate(ids):
        lo = row[f"min_{index}"] if row is not None else None
        hi = row[f"max_{index}"] if row is not None else None
        result[sid] = (None if lo is None else int(lo), None if hi is None else int(hi))
    return result


_EVIDENCE_PRIORITY = {
    EVIDENCE_PURGED: 70,
    EVIDENCE_NOT_APPLICABLE: 60,
    EVIDENCE_NOT_INSTRUMENTED: 50,
    EVIDENCE_GAP: 40,
    EVIDENCE_AVAILABLE: 30,
    EVIDENCE_NO_SOURCE: 20,
    EVIDENCE_UNKNOWN: 10,
}


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (str(name),)
    ).fetchone() is not None


def _instrumented_since(conn: sqlite3.Connection, series_id: str, entity_id: Optional[int]) -> Optional[int]:
    if not _table_exists(conn, "graph_instrumentation_timeline"):
        return None
    row = conn.execute(
        "SELECT effective_from_ms FROM graph_instrumentation_timeline "
        "WHERE series_id=? AND entity_id IS ? AND state='INSTRUMENTED' ORDER BY effective_from_ms LIMIT 1",
        (str(series_id), entity_id),
    ).fetchone()
    return None if row is None else int(row[0])


def _resolve_evidence_rows(
    rows: Sequence[Mapping[str, Any]], *, start_ms: int, end_ms: int,
    instrumented: Optional[int], forced_status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    start, end = int(start_ms), int(end_ms)
    if end < start:
        return []
    if forced_status:
        return [{"from_ms": start, "to_ms": end, "status": str(forced_status),
                 "source": "APPLICABILITY_CONTRACT", "quality": "AUTHORITATIVE"}]
    cuts = {start, end + 1}
    filtered: List[Dict[str, Any]] = []
    for original in rows:
        a = max(start, int(original["from_ms"])); b = min(end, int(original["to_ms"]))
        if a > b:
            continue
        item = dict(original); item["from_ms"] = a; item["to_ms"] = b
        filtered.append(item); cuts.add(a); cuts.add(b + 1)
    if instrumented is not None and start < int(instrumented) <= end:
        cuts.add(int(instrumented))
    ordered = sorted(cuts)
    out: List[Dict[str, Any]] = []
    for a, next_cut in zip(ordered, ordered[1:]):
        b = next_cut - 1
        covering = [x for x in filtered if int(x["from_ms"]) <= a and int(x["to_ms"]) >= b]
        if covering:
            winner = max(covering, key=lambda x: _EVIDENCE_PRIORITY.get(str(x.get("status")), 0))
            status = str(winner.get("status") or EVIDENCE_UNKNOWN)
            source = str(winner.get("source") or "GRAPH_CORE_V3")
            quality = str(winner.get("quality") or "OBSERVED")
            operation_id = winner.get("operation_id")
        elif instrumented is None:
            status, source, quality, operation_id = EVIDENCE_NO_SOURCE, "EVIDENCE_CONTRACT", "UNKNOWN", None
        elif b < int(instrumented):
            status, source, quality, operation_id = EVIDENCE_NOT_INSTRUMENTED, "INSTRUMENTATION_TIMELINE", "AUTHORITATIVE", None
        else:
            status, source, quality, operation_id = EVIDENCE_GAP, "EVIDENCE_CONTRACT", "DERIVED_GAP", None
        item = {"from_ms": int(a), "to_ms": int(b), "status": status, "source": source, "quality": quality}
        if operation_id:
            item["operation_id"] = operation_id
        if (out and out[-1]["status"] == item["status"] and out[-1]["source"] == item["source"]
                and out[-1].get("quality") == item.get("quality")
                and out[-1].get("operation_id") == item.get("operation_id")
                and int(out[-1]["to_ms"]) + 1 == int(item["from_ms"])):
            out[-1]["to_ms"] = item["to_ms"]
        else:
            out.append(item)
    return out


def _resolve_evidence_window(
    conn: sqlite3.Connection, *, series_id: str, resolution: str, entity_id: Optional[int],
    start_ms: int, end_ms: int, forced_status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    start, end = int(start_ms), int(end_ms)
    if end < start:
        return []
    if forced_status:
        return _resolve_evidence_rows([], start_ms=start, end_ms=end, instrumented=None, forced_status=forced_status)
    rows: List[Dict[str, Any]] = []
    if _table_exists(conn, "graph_availability_segments"):
        rows = evidence_rows(conn, series_id=series_id, entity_id=entity_id, resolution=resolution,
                             start_ms=start, end_ms=end)
    # Compatibility fallback for pre-WP5 V3 DBs only.
    if not rows:
        if entity_id is None and series_id in SYSTEM_SERIES_BY_ID:
            spec = SYSTEM_SERIES_BY_ID[series_id]
            if resolution == "1min":
                count_col = f"{spec.column}_count"
                q = conn.execute(
                    f"SELECT MIN(bucket_start_ms),MAX(bucket_start_ms) FROM measurement_1min "
                    f"WHERE bucket_start_ms>=? AND bucket_start_ms<=? AND {count_col}>0",
                    ((start // 60000) * 60000, end),
                ).fetchone()
                if q and q[0] is not None:
                    rows = [{"from_ms": int(q[0]), "to_ms": int(q[1]) + 59_999, "status": EVIDENCE_AVAILABLE,
                             "source": "GRAPH_CORE_V3_FALLBACK", "quality": "MINUTE_BUCKET"}]
            else:
                q = conn.execute(
                    f"SELECT MIN(ts_ms),MAX(ts_ms) FROM measurement_raw WHERE ts_ms>=? AND ts_ms<=? AND {spec.column} IS NOT NULL",
                    (start, end),
                ).fetchone()
                if q and q[0] is not None:
                    rows = [{"from_ms": int(q[0]), "to_ms": int(q[1]), "status": EVIDENCE_AVAILABLE,
                             "source": "GRAPH_CORE_V3_FALLBACK", "quality": "OBSERVED_NON_NULL_SPAN"}]
        elif entity_id is not None and series_id in ENTITY_SERIES_BY_ID:
            spec = ENTITY_SERIES_BY_ID[series_id]
            if resolution == "1min":
                count_col = f"{spec.column}_count"
                q = conn.execute(
                    f"SELECT MIN(bucket_start_ms),MAX(bucket_start_ms) FROM measurement_entity_1min "
                    f"WHERE entity_id=? AND bucket_start_ms>=? AND bucket_start_ms<=? AND {count_col}>0",
                    (int(entity_id), (start // 60000) * 60000, end),
                ).fetchone()
                if q and q[0] is not None:
                    rows = [{"from_ms": int(q[0]), "to_ms": int(q[1]) + 59_999, "status": EVIDENCE_AVAILABLE,
                             "source": "GRAPH_CORE_V3_ENTITY_FALLBACK", "quality": "MINUTE_BUCKET"}]
            else:
                q = conn.execute(
                    f"SELECT MIN(ts_ms),MAX(ts_ms) FROM measurement_entity_raw WHERE entity_id=? AND ts_ms>=? AND ts_ms<=? AND {spec.column} IS NOT NULL",
                    (int(entity_id), start, end),
                ).fetchone()
                if q and q[0] is not None:
                    rows = [{"from_ms": int(q[0]), "to_ms": int(q[1]), "status": EVIDENCE_AVAILABLE,
                             "source": "GRAPH_CORE_V3_ENTITY_FALLBACK", "quality": "OBSERVED_NON_NULL_SPAN"}]
    instrumented = _instrumented_since(conn, series_id, entity_id)
    if instrumented is None:
        starts = [int(x["from_ms"]) for x in rows if x.get("status") == EVIDENCE_AVAILABLE]
        instrumented = min(starts) if starts else None
    return _resolve_evidence_rows(rows, start_ms=start, end_ms=end, instrumented=instrumented)


def query_evidence_context(conn: sqlite3.Connection, series_ids: Sequence[str], *, resolution: str,
                           start_ms: int, end_ms: int) -> Dict[str, Any]:
    return {sid: _resolve_evidence_window(conn, series_id=sid, resolution=resolution, entity_id=None,
                                          start_ms=start_ms, end_ms=end_ms) for sid in series_ids}


def _coverage_evidence(conn: sqlite3.Connection, series_id: str, *, resolution: str = "highres") -> List[Dict[str, Any]]:
    rows = evidence_rows(conn, series_id=series_id, entity_id=None, resolution=resolution) if _table_exists(conn, "graph_availability_segments") else []
    if rows:
        start = min(int(x["from_ms"]) for x in rows); end = max(int(x["to_ms"]) for x in rows)
        instrumented = _instrumented_since(conn, series_id, None)
        if instrumented is None:
            starts = [int(x["from_ms"]) for x in rows if x.get("status") == EVIDENCE_AVAILABLE]
            instrumented = min(starts) if starts else None
        return _resolve_evidence_rows(rows, start_ms=start, end_ms=end, instrumented=instrumented)
    spec = SYSTEM_SERIES_BY_ID.get(series_id)
    if spec is None:
        return []
    if resolution == "1min":
        count_col = f"{spec.column}_count"
        span = conn.execute(f"SELECT MIN(bucket_start_ms),MAX(bucket_start_ms) FROM measurement_1min WHERE {count_col}>0").fetchone()
        if not span or span[0] is None: return []
        start, end = int(span[0]), int(span[1]) + 59_999
    else:
        span = conn.execute(f"SELECT MIN(ts_ms),MAX(ts_ms) FROM measurement_raw WHERE {spec.column} IS NOT NULL").fetchone()
        if not span or span[0] is None: return []
        start, end = int(span[0]), int(span[1])
    return _resolve_evidence_window(conn, series_id=series_id, resolution=resolution, entity_id=None,
                                    start_ms=start, end_ms=end)


def _coverage_evidence_bulk(conn: sqlite3.Connection, series_ids: Sequence[str], *, resolution: str = "highres") -> Dict[str, List[Dict[str, Any]]]:
    ids = tuple(series_ids)
    result: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in ids}
    if not ids:
        return result
    grouped: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in ids}
    instrumented: Dict[str, Optional[int]] = {sid: None for sid in ids}
    if _table_exists(conn, "graph_availability_segments"):
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT series_id,from_ms,to_ms,status,source,quality,operation_id FROM graph_availability_segments "
            f"WHERE entity_id IS NULL AND resolution=? AND series_id IN ({placeholders}) ORDER BY series_id,from_ms,segment_id",
            (resolution, *ids),
        ).fetchall()
        for row in rows:
            grouped[str(row[0])].append({"from_ms": int(row[1]), "to_ms": int(row[2]), "status": str(row[3]),
                                         "source": str(row[4]), "quality": str(row[5]), "operation_id": row[6]})
    if _table_exists(conn, "graph_instrumentation_timeline"):
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT series_id,MIN(effective_from_ms) FROM graph_instrumentation_timeline "
            f"WHERE entity_id IS NULL AND state='INSTRUMENTED' AND series_id IN ({placeholders}) GROUP BY series_id",
            ids,
        ).fetchall()
        for row in rows:
            instrumented[str(row[0])] = int(row[1])
    for sid in ids:
        rows = grouped[sid]
        if not rows:
            result[sid] = _coverage_evidence(conn, sid, resolution=resolution)
            continue
        inst = instrumented[sid]
        if inst is None:
            starts = [int(x["from_ms"]) for x in rows if x.get("status") == EVIDENCE_AVAILABLE]
            inst = min(starts) if starts else None
        result[sid] = _resolve_evidence_rows(rows, start_ms=min(int(x["from_ms"]) for x in rows),
                                             end_ms=max(int(x["to_ms"]) for x in rows), instrumented=inst)
    return result


def _resolved_coverage_segments(persisted: Sequence[Mapping[str, Any]], evidence: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for item in persisted:
        candidates.append({"from_ms": int(item["from_ms"]), "to_ms": int(item["to_ms"]),
                           "status": EVIDENCE_AVAILABLE, "source": str(item.get("source") or "GRAPH_SERIES_COVERAGE"),
                           "quality": str(item.get("quality") or "OBSERVED_NON_NULL_SPAN"), "origin_rank": 2})
    for item in evidence:
        candidates.append({"from_ms": int(item["from_ms"]), "to_ms": int(item["to_ms"]),
                           "status": str(item.get("status") or EVIDENCE_UNKNOWN),
                           "source": str(item.get("source") or "GRAPH_CORE_V3"),
                           "quality": str(item.get("quality") or "OBSERVED"), "origin_rank": 1})
    if not candidates: return []
    cuts = set()
    for item in candidates:
        cuts.add(int(item["from_ms"])); cuts.add(int(item["to_ms"]) + 1)
    out: List[Dict[str, Any]] = []
    ordered = sorted(cuts)
    for a, nc in zip(ordered, ordered[1:]):
        b = nc - 1
        covering = [x for x in candidates if int(x["from_ms"]) <= a and int(x["to_ms"]) >= b]
        if not covering: continue
        winner = max(covering, key=lambda x: (_EVIDENCE_PRIORITY.get(str(x.get("status")), 0), int(x.get("origin_rank",0))))
        if str(winner.get("status")) != EVIDENCE_AVAILABLE: continue
        seg = {"from_ms": a, "to_ms": b, "source": str(winner["source"]), "quality": str(winner["quality"])}
        if out and out[-1]["source"] == seg["source"] and out[-1]["quality"] == seg["quality"] and int(out[-1]["to_ms"])+1 == a:
            out[-1]["to_ms"] = b
        else: out.append(seg)
    return out


def query_series_coverage(conn: sqlite3.Connection, series_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    ids = _validate_series(series_ids)
    persisted: Dict[str,List[Dict[str,Any]]] = {sid: [] for sid in ids}
    availability: Dict[str,List[Dict[str,Any]]] = {sid: [] for sid in ids}
    if ids:
        placeholders = ",".join("?" for _ in ids)
        for row in conn.execute(
            f"SELECT series_id,from_ms,to_ms,source,quality FROM graph_series_coverage WHERE series_id IN ({placeholders}) ORDER BY series_id,from_ms", ids
        ).fetchall():
            persisted[str(row["series_id"])].append({"from_ms":int(row["from_ms"]),"to_ms":int(row["to_ms"]),"source":str(row["source"]),"quality":str(row["quality"])})
        if _table_exists(conn,"graph_availability_segments"):
            for row in conn.execute(
                f"SELECT series_id,from_ms,to_ms,status,source,quality FROM graph_availability_segments "
                f"WHERE entity_id IS NULL AND resolution='highres' AND series_id IN ({placeholders}) ORDER BY series_id,from_ms,segment_id", ids
            ).fetchall():
                availability[str(row["series_id"])].append({"from_ms":int(row["from_ms"]),"to_ms":int(row["to_ms"]),"status":str(row["status"]),"source":str(row["source"]),"quality":str(row["quality"])})
    missing=[sid for sid in ids if not availability[sid] and not persisted[sid]]
    full_spans=_series_spans_one_scan(conn,missing)
    result={}
    for sid in ids:
        if availability[sid]:
            segments=_resolved_coverage_segments(persisted[sid],availability[sid])
        elif persisted[sid]:
            segments=list(persisted[sid]); last=max(int(x["to_ms"]) for x in segments); spec=SYSTEM_SERIES_BY_ID[sid]
            tail=conn.execute(f"SELECT MIN(ts_ms),MAX(ts_ms) FROM measurement_raw WHERE ts_ms>? AND {spec.column} IS NOT NULL",(last,)).fetchone()
            if tail and tail[0] is not None:
                segments.append({"from_ms":int(tail[0]),"to_ms":int(tail[1]),"source":"GRAPH_CORE_V3_LIVE_TAIL","quality":"OBSERVED_NON_NULL_SPAN"})
        else:
            segments=[]; lo,hi=full_spans.get(sid,(None,None))
            if lo is not None: segments.append({"from_ms":lo,"to_ms":hi,"source":"GRAPH_CORE_V3","quality":"OBSERVED_NON_NULL_SPAN"})
        segments.sort(key=lambda x:(int(x["from_ms"]),int(x["to_ms"])))
        first=min((int(x["from_ms"]) for x in segments),default=None); last=max((int(x["to_ms"]) for x in segments),default=None)
        result[sid]={"available":first is not None,"from_ms":first,"to_ms":last,"segments":segments}
    return result


def _validate_entity_series(series_ids: Optional[Sequence[str]]) -> Tuple[str, ...]:
    if not series_ids:
        return tuple(spec.series_id for spec in ENTITY_SERIES)
    result: List[str] = []
    for item in series_ids:
        sid = str(item or "").strip()
        if not sid:
            continue
        if sid not in ENTITY_SERIES_BY_ID:
            raise GraphQueryError(f"UNKNOWN_ENTITY_SERIES:{sid}")
        if sid not in result:
            result.append(sid)
    return tuple(result)


def _json_object(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    try:
        decoded = json.loads(str(value))
    except Exception:
        return {}
    return dict(decoded) if isinstance(decoded, Mapping) else {}


def _query_entity_rows(conn: sqlite3.Connection, stable_ids: Optional[Sequence[str]] = None) -> List[sqlite3.Row]:
    if stable_ids:
        ids = tuple(dict.fromkeys(str(item).strip() for item in stable_ids if str(item).strip()))
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT * FROM graph_entities WHERE stable_id IN ({placeholders}) ORDER BY entity_id",
            ids,
        ).fetchall()
        found = {str(row["stable_id"]) for row in rows}
        missing = [sid for sid in ids if sid not in found]
        if missing:
            raise GraphQueryError(f"UNKNOWN_ENTITY:{','.join(missing)}")
        order = {sid: i for i, sid in enumerate(ids)}
        return sorted(rows, key=lambda row: order[str(row["stable_id"])])
    return conn.execute("SELECT * FROM graph_entities ORDER BY entity_id").fetchall()


def _latest_entity_topology(conn: sqlite3.Connection, entity_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT t.*
          FROM graph_topology_timeline AS t
          JOIN (
                SELECT COALESCE(role,'') AS role_key, MAX(effective_from_ms) AS max_ts
                  FROM graph_topology_timeline
                 WHERE entity_id=?
                 GROUP BY COALESCE(role,'')
          ) AS latest
            ON COALESCE(t.role,'')=latest.role_key AND t.effective_from_ms=latest.max_ts
         WHERE t.entity_id=?
         ORDER BY COALESCE(t.role,''),t.topology_id DESC
        """,
        (int(entity_id), int(entity_id)),
    ).fetchall()
    result: List[Dict[str, Any]] = []
    seen_roles: set[str] = set()
    for row in rows:
        role = str(row["role"] or "")
        if role in seen_roles:
            continue
        seen_roles.add(role)
        result.append({
            "role": role,
            "state": str(row["state"] or ""),
            "effective_from_ms": int(row["effective_from_ms"]),
            "confidence": str(row["confidence"] or "OBSERVED"),
            "unit_count": row["unit_count"],
            "source": str(row["source"] or ""),
        })
    return result


def _entity_available_series(binding: str) -> Tuple[str, ...]:
    mapping = SYSTEM_ENTITY_BINDINGS.get(str(binding or "").upper())
    if mapping is not None:
        return tuple(mapping.keys())
    return tuple(spec.series_id for spec in ENTITY_SERIES)


def _entity_row_to_catalog(conn: sqlite3.Connection, row: sqlite3.Row) -> Dict[str, Any]:
    binding = str(row["storage_binding"] or ENTITY_BINDING_ENTITY_TABLE).upper()
    topology = _latest_entity_topology(conn, int(row["entity_id"]))
    return {
        "entity_id": int(row["entity_id"]),
        "stable_id": str(row["stable_id"]),
        "entity_type": str(row["entity_type"]),
        "identity_kind": str(row["identity_kind"] or "LOGICAL_ROLE"),
        "source_identity": row["source_identity"],
        "storage_binding": binding,
        "label_key": str(row["label_key"] or ""),
        "display_name": str(row["display_name"] or ""),
        "first_seen_ms": row["first_seen_ms"],
        "last_seen_ms": row["last_seen_ms"],
        "metadata": _json_object(row["metadata_json"]),
        "available_series": list(_entity_available_series(binding)),
        "topology": topology,
    }


def _entity_minute_value(row: sqlite3.Row, spec: EntitySeriesSpec) -> Optional[float]:
    base = spec.column
    if spec.aggregation == "power":
        count = int(row[f"{base}_count"] or 0)
        total = row[f"{base}_sum"]
        if count <= 0 or total is None:
            return None
        return float(total) / float(count) / float(spec.scale)
    return decode_scaled(row[f"{base}_last"], scale=spec.scale)


def _query_entity_table_numeric(
    conn: sqlite3.Connection,
    entity_id: int,
    start_ms: int,
    end_ms: int,
    series_ids: Sequence[str],
    plan: QueryPlan,
) -> Dict[str, Any]:
    specs = [ENTITY_SERIES_BY_ID[sid] for sid in series_ids]
    data: Dict[str, List[Optional[float]]] = {spec.series_id: [] for spec in specs}
    timestamps: List[int] = []
    quality: List[int] = []
    if plan.source == "raw":
        columns = ["ts_ms", "quality_flags"] + [spec.column for spec in specs]
        rows = conn.execute(
            f"SELECT {','.join(columns)} FROM measurement_entity_raw "
            "WHERE entity_id=? AND ts_ms>=? AND ts_ms<=? ORDER BY ts_ms",
            (int(entity_id), int(start_ms), int(end_ms)),
        ).fetchall()
        for row in rows:
            timestamps.append(int(row["ts_ms"]))
            quality.append(int(row["quality_flags"] or 0))
            for spec in specs:
                data[spec.series_id].append(decode_scaled(row[spec.column], scale=spec.scale))
    else:
        query_start = (int(start_ms) // 60_000) * 60_000
        needed = ["bucket_start_ms", "quality_or"]
        for spec in specs:
            suffixes = ("_sum", "_count") if spec.aggregation == "power" else ("_last",)
            for suffix in suffixes:
                name = spec.column + suffix
                if name not in needed:
                    needed.append(name)
        rows = conn.execute(
            f"SELECT {','.join(needed)} FROM measurement_entity_1min "
            "WHERE entity_id=? AND bucket_start_ms>=? AND bucket_start_ms<=? ORDER BY bucket_start_ms",
            (int(entity_id), query_start, int(end_ms)),
        ).fetchall()
        for row in rows:
            timestamps.append(int(row["bucket_start_ms"]))
            quality.append(int(row["quality_or"] or 0))
            for spec in specs:
                data[spec.series_id].append(_entity_minute_value(row, spec))
    return {
        "format": FORMAT_COLUMNAR_V1,
        "timestamps_ms": timestamps,
        "quality_flags": quality,
        "series": data,
    }


def _query_system_bound_entity(
    conn: sqlite3.Connection,
    binding: str,
    start_ms: int,
    end_ms: int,
    requested: Sequence[str],
    plan: QueryPlan,
) -> Dict[str, Any]:
    mapping = SYSTEM_ENTITY_BINDINGS.get(str(binding or "").upper(), {})
    applicable = [sid for sid in requested if sid in mapping]
    not_applicable = [sid for sid in requested if sid not in mapping]
    if not applicable:
        return {
            "format": FORMAT_COLUMNAR_V1,
            "timestamps_ms": [],
            "quality_flags": [],
            "series": {},
            "not_applicable_series": not_applicable,
        }
    system_ids = [mapping[sid] for sid in applicable]
    numeric = _query_numeric(conn, start_ms, end_ms, system_ids, plan)
    return {
        "format": FORMAT_COLUMNAR_V1,
        "timestamps_ms": numeric["timestamps_ms"],
        "quality_flags": numeric["quality_flags"],
        "series": {sid: numeric["series"][mapping[sid]] for sid in applicable},
        "not_applicable_series": not_applicable,
    }


def _entity_table_coverage(conn: sqlite3.Connection, entity_id: int, series_ids: Sequence[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    persisted_rows = conn.execute(
        "SELECT series_id,from_ms,to_ms,source,quality FROM graph_entity_series_coverage WHERE entity_id=?",
        (int(entity_id),),
    ).fetchall()
    persisted = {str(row["series_id"]): row for row in persisted_rows}
    for sid in series_ids:
        row = persisted.get(sid)
        segments: List[Dict[str, Any]] = []
        if row is not None:
            segments.append({
                "from_ms": int(row["from_ms"]), "to_ms": int(row["to_ms"]),
                "source": str(row["source"]), "quality": str(row["quality"]),
            })
        else:
            spec = ENTITY_SERIES_BY_ID[sid]
            span = conn.execute(
                f"SELECT MIN(ts_ms),MAX(ts_ms) FROM measurement_entity_raw WHERE entity_id=? AND {spec.column} IS NOT NULL",
                (int(entity_id),),
            ).fetchone()
            if span and span[0] is not None:
                segments.append({
                    "from_ms": int(span[0]), "to_ms": int(span[1]),
                    "source": "GRAPH_CORE_V3_ENTITY", "quality": "OBSERVED_NON_NULL_SPAN",
                })
        result[sid] = {
            "available": bool(segments),
            "applicability": "AVAILABLE" if segments else "NO_EVIDENCE",
            "from_ms": min((int(x["from_ms"]) for x in segments), default=None),
            "to_ms": max((int(x["to_ms"]) for x in segments), default=None),
            "segments": segments,
        }
    return result


def _system_bound_entity_coverage(conn: sqlite3.Connection, binding: str, series_ids: Sequence[str]) -> Dict[str, Any]:
    mapping = SYSTEM_ENTITY_BINDINGS.get(str(binding or "").upper(), {})
    mapped = [mapping[sid] for sid in series_ids if sid in mapping]
    system_cov = query_series_coverage(conn, mapped) if mapped else {}
    result: Dict[str, Any] = {}
    for sid in series_ids:
        system_sid = mapping.get(sid)
        if system_sid is None:
            result[sid] = {
                "available": False, "applicability": "NOT_APPLICABLE",
                "from_ms": None, "to_ms": None, "segments": [],
            }
        else:
            payload = dict(system_cov.get(system_sid) or {})
            payload["applicability"] = "AVAILABLE" if payload.get("available") else "NO_EVIDENCE"
            payload["source_series_id"] = system_sid
            result[sid] = payload
    return result


class GraphQueryService:
    def __init__(self, *, cache_max_entries: int = CACHE_MAX_ENTRIES, cache_ttl_s: float = CACHE_TTL_S) -> None:
        self.cache_max_entries = max(0, int(cache_max_entries))
        self.cache_ttl_s = max(0.0, float(cache_ttl_s))
        self._cache: "OrderedDict[Tuple[Any, ...], Tuple[float, Dict[str, Any]]]" = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def catalog() -> Dict[str, Any]:
        return {"catalog_version": 2, "series": canonical_series_catalog(), "entity_series": canonical_entity_series_catalog()}

    def runtime_status(self, path: str) -> Dict[str, Any]:
        """Return cheap, non-mutating readiness/capability metadata for V3 history.

        This status is intentionally independent from controller readiness.  It
        tells UI/cutover code whether the V14 history contract can be consumed,
        without making historical storage a prerequisite for safe regulation.
        """
        conn = self._open_v3(path)
        started = time.perf_counter()
        try:
            tables = {
                str(row[0]) for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            required = {
                "measurement_raw",
                "measurement_1min",
                "graph_intervals",
                "graph_command_events",
                "graph_entities",
                "graph_topology_timeline",
                "graph_config_timeline",
            }
            optional_evidence = {
                "graph_availability_segments",
                "graph_instrumentation_timeline",
                "graph_retention_ledger",
            }
            missing_required = sorted(required - tables)
            first_ms = last_ms = None
            if "measurement_1min" in tables:
                row = conn.execute(
                    "SELECT MIN(bucket_start_ms), MAX(bucket_start_ms) FROM measurement_1min"
                ).fetchone()
                if row:
                    first_ms, last_ms = row[0], row[1]
            return {
                "backend": "v3",
                "schema_version": 3,
                "query_contract": "graph_query_service_v1",
                "workspace_ready": not missing_required,
                "history_data_available": first_ms is not None and last_ms is not None,
                "available_from_ms": int(first_ms) if first_ms is not None else None,
                "available_to_ms": int(last_ms) if last_ms is not None else None,
                "measurement_v4_required": False,
                "missing_required_tables": missing_required,
                "capabilities": {
                    "overview": not missing_required,
                    "inspector": "measurement_raw" in tables,
                    "entities": "graph_entities" in tables and "graph_topology_timeline" in tables,
                    "config_timeline": "graph_config_timeline" in tables,
                    "coverage": "measurement_1min" in tables,
                    "evidence": optional_evidence.issubset(tables),
                    "retention_evidence": "graph_retention_ledger" in tables,
                },
                "meta": {
                    "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                },
            }
        finally:
            conn.close()

    def _open_v3(self, path: str) -> sqlite3.Connection:
        if not path or not os.path.exists(path):
            raise GraphQueryError("GRAPH_DB_MISSING")
        conn = _readonly_connect(path)
        if _schema_version(conn) != 3:
            conn.close()
            raise GraphQueryError("GRAPH_DB_NOT_V3")
        return conn

    def _cache_get(self, key: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
        if self.cache_max_entries <= 0 or self.cache_ttl_s <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                return None
            created, payload = item
            if now - created > self.cache_ttl_s:
                self._cache.pop(key, None)
                return None
            self._cache.move_to_end(key)
            result = copy.deepcopy(payload)
            result.setdefault("meta", {})["cache"] = "hit"
            return result

    def _cache_put(self, key: Tuple[Any, ...], payload: Dict[str, Any]) -> None:
        if self.cache_max_entries <= 0 or self.cache_ttl_s <= 0:
            return
        with self._lock:
            self._cache[key] = (time.monotonic(), copy.deepcopy(payload))
            self._cache.move_to_end(key)
            while len(self._cache) > self.cache_max_entries:
                self._cache.popitem(last=False)

    def entities(self, path: str, *, stable_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        key_ids = tuple(str(item).strip() for item in (stable_ids or ()) if str(item).strip())
        key = ("entities", _db_fingerprint(path), key_ids)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        conn = self._open_v3(path)
        started = time.perf_counter()
        try:
            rows = _query_entity_rows(conn, key_ids or None)
            payload = {
                "entities": [_entity_row_to_catalog(conn, row) for row in rows],
                "entity_series": canonical_entity_series_catalog(),
                "meta": {
                    "cache": "miss",
                    "entity_count": len(rows),
                    "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                },
            }
        finally:
            conn.close()
        self._cache_put(key, payload)
        return payload

    def entity_overview(
        self,
        path: str,
        start_ms: int,
        end_ms: int,
        *,
        stable_ids: Optional[Sequence[str]] = None,
        series_ids: Optional[Sequence[str]] = None,
        resolution: str = "auto",
    ) -> Dict[str, Any]:
        start_ms, end_ms = int(start_ms), int(end_ms)
        if end_ms <= start_ms:
            raise GraphQueryError("INVALID_TIME_RANGE")
        if end_ms - start_ms > DEFAULT_MAX_WINDOW_MS:
            raise GraphQueryError("WINDOW_EXCEEDS_48H")
        entity_series = _validate_entity_series(series_ids)
        entity_keys = tuple(str(item).strip() for item in (stable_ids or ()) if str(item).strip())
        plan = plan_query(start_ms, end_ms, resolution=resolution, purpose="overview")
        key = (
            "entity_overview", _db_fingerprint(path), start_ms, end_ms,
            entity_keys, entity_series, plan.source,
        )
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        conn = self._open_v3(path)
        started = time.perf_counter()
        try:
            rows = _query_entity_rows(conn, entity_keys or None)
            entity_ids = {int(row["entity_id"]) for row in rows}
            topology_by_entity: Dict[int, List[Dict[str, Any]]] = {entity_id: [] for entity_id in entity_ids}
            for item in _query_topology(conn, start_ms, end_ms):
                entity_id = item.get("entity_id")
                if entity_id is not None and int(entity_id) in topology_by_entity:
                    topology_by_entity[int(entity_id)].append(item)
            entities: Dict[str, Any] = {}
            total_rows = 0
            for row in rows:
                catalog = _entity_row_to_catalog(conn, row)
                binding = str(catalog["storage_binding"])
                if binding in SYSTEM_ENTITY_BINDINGS:
                    numeric = _query_system_bound_entity(
                        conn, binding, start_ms, end_ms, entity_series, plan,
                    )
                else:
                    numeric = _query_entity_table_numeric(
                        conn, int(row["entity_id"]), start_ms, end_ms, entity_series, plan,
                    )
                    numeric["not_applicable_series"] = []
                total_rows += len(numeric["timestamps_ms"])
                entities[str(row["stable_id"])] = {
                    "entity": catalog,
                    "topology_timeline": topology_by_entity.get(int(row["entity_id"]), []),
                    **numeric,
                }
            payload = {
                "format": FORMAT_COLUMNAR_V1,
                "from_ms": start_ms,
                "to_ms": end_ms,
                "resolution": "highres" if plan.source == "raw" else "1min",
                "entities": entities,
                "meta": {
                    "cache": "miss",
                    "query_source": plan.source,
                    "query_plan_reason": plan.reason,
                    "entity_count": len(rows),
                    "row_count_total": total_rows,
                    "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                },
            }
        finally:
            conn.close()
        self._cache_put(key, payload)
        return payload

    def entity_coverage(
        self,
        path: str,
        *,
        stable_ids: Optional[Sequence[str]] = None,
        series_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        entity_series = _validate_entity_series(series_ids)
        entity_keys = tuple(str(item).strip() for item in (stable_ids or ()) if str(item).strip())
        key = ("entity_coverage", _db_fingerprint(path), entity_keys, entity_series)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        conn = self._open_v3(path)
        started = time.perf_counter()
        try:
            rows = _query_entity_rows(conn, entity_keys or None)
            entities: Dict[str, Any] = {}
            for row in rows:
                binding = str(row["storage_binding"] or ENTITY_BINDING_ENTITY_TABLE).upper()
                coverage = (
                    _system_bound_entity_coverage(conn, binding, entity_series)
                    if binding in SYSTEM_ENTITY_BINDINGS
                    else _entity_table_coverage(conn, int(row["entity_id"]), entity_series)
                )
                for sid in entity_series:
                    if coverage[sid].get("applicability") == "NOT_APPLICABLE":
                        coverage[sid]["evidence_segments"] = []
                    elif binding in SYSTEM_ENTITY_BINDINGS:
                        source_sid = SYSTEM_ENTITY_BINDINGS.get(binding, {}).get(sid)
                        coverage[sid]["evidence_segments"] = (
                            _coverage_evidence(conn, source_sid, resolution="highres") if source_sid else []
                        )
                    else:
                        first = coverage[sid].get("from_ms")
                        last = coverage[sid].get("to_ms")
                        if first is not None and last is not None:
                            coverage[sid]["evidence_segments"] = _resolve_evidence_window(
                                conn, series_id=sid, resolution="highres", entity_id=int(row["entity_id"]),
                                start_ms=int(first), end_ms=int(last),
                            )
                        else:
                            coverage[sid]["evidence_segments"] = []
                entities[str(row["stable_id"])] = {
                    "entity_id": int(row["entity_id"]),
                    "storage_binding": binding,
                    "series": coverage,
                }
            payload = {
                "entities": entities,
                "meta": {
                    "cache": "miss",
                    "entity_count": len(rows),
                    "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                },
            }
        finally:
            conn.close()
        self._cache_put(key, payload)
        return payload

    def overview(
        self,
        path: str,
        start_ms: int,
        end_ms: int,
        *,
        series_ids: Optional[Sequence[str]] = None,
        resolution: str = "auto",
        include_context: bool = True,
        event_limit: int = DEFAULT_EVENT_LIMIT,
        include_sample_metadata: bool = False,
    ) -> Dict[str, Any]:
        start_ms, end_ms = int(start_ms), int(end_ms)
        ids = _validate_series(series_ids)
        if end_ms <= start_ms:
            raise GraphQueryError("INVALID_TIME_RANGE")
        if end_ms - start_ms > DEFAULT_MAX_WINDOW_MS:
            raise GraphQueryError("WINDOW_EXCEEDS_48H")
        plan = plan_query(start_ms, end_ms, resolution=resolution, purpose="overview")
        fingerprint = _db_fingerprint(path)
        key = ("overview", fingerprint, start_ms, end_ms, ids, plan.source, bool(include_context), int(event_limit), bool(include_sample_metadata))
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        started = time.perf_counter()
        conn = self._open_v3(path)
        try:
            numeric = _query_numeric(conn, start_ms, end_ms, ids, plan)
            payload: Dict[str, Any] = {
                "format": FORMAT_COLUMNAR_V1,
                "from_ms": start_ms,
                "to_ms": end_ms,
                "resolution": "highres" if plan.source == "raw" else "1min",
                "timestamps_ms": numeric["timestamps_ms"],
                "quality_flags": numeric["quality_flags"],
                "series": numeric["series"],
            }
            if include_sample_metadata:
                payload["sample_timestamps_ms"] = numeric["sample_timestamps_ms"]
                payload["sample_counts"] = numeric["sample_counts"]
            if include_context:
                payload.update({
                    "intervals": _query_intervals(conn, start_ms, end_ms, limit=event_limit),
                    "command_events": _query_events(conn, start_ms, end_ms, limit=event_limit),
                    "config_timeline": _query_config(conn, start_ms, end_ms),
                    "topology_timeline": _query_topology(conn, start_ms, end_ms),
                    "runs": _query_runs(conn, start_ms, end_ms),
                    "retention": _query_retention(conn, start_ms, end_ms),
                })
            payload["meta"] = {
                "cache": "miss",
                "query_source": plan.source,
                "query_plan_reason": plan.reason,
                "row_count": len(payload["timestamps_ms"]),
                "series_count": len(ids),
                "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
            }
        finally:
            conn.close()
        self._cache_put(key, payload)
        return payload

    def config_timeline(self, path: str, start_ms: int, end_ms: int) -> Dict[str, Any]:
        """Return sparse historical effective-config rows through the V3 service."""
        start_ms, end_ms = int(start_ms), int(end_ms)
        if end_ms <= start_ms:
            raise GraphQueryError("INVALID_TIME_RANGE")
        if end_ms - start_ms > DEFAULT_MAX_WINDOW_MS:
            raise GraphQueryError("WINDOW_EXCEEDS_48H")
        key = ("config_timeline", _db_fingerprint(path), start_ms, end_ms)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        started = time.perf_counter()
        conn = self._open_v3(path)
        try:
            rows = _query_config(conn, start_ms, end_ms)
            payload = {
                "items": rows,
                "meta": {
                    "cache": "miss",
                    "row_count": len(rows),
                    "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                },
            }
        finally:
            conn.close()
        self._cache_put(key, payload)
        return payload

    def compatibility_points(self, path: str, start_ms: int, end_ms: int, *, limit: int = 5000) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """V13 graph/status adapter backed by the canonical V3 overview contract.

        WP6 removes the second, hand-written ``measurement_1min`` reader from
        this compatibility path.  Existing consumers keep their point-shaped
        payload while numeric/history semantics come from ``overview()``.
        """
        start_ms, end_ms = int(start_ms), int(end_ms)
        ids = (
            "grid_power_w", "raw_grid_power_w", "target_final_w",
            "zendure_actual_power_w", "pv_power_w", "house_power_w",
            "zendure_soc_percent", "primary_soc_percent", "primary_power_w",
        )
        payload = self.overview(
            path,
            start_ms,
            end_ms,
            series_ids=ids,
            resolution="1min",
            include_context=True,
            event_limit=max(5000, int(limit) * 4),
            include_sample_metadata=True,
        )
        timestamps = list(payload.get("timestamps_ms") or [])[: max(0, int(limit))]
        sample_timestamps = list(payload.get("sample_timestamps_ms") or [])[: max(0, int(limit))]
        sample_counts = list(payload.get("sample_counts") or [])[: max(0, int(limit))]
        series = dict(payload.get("series") or {})
        quality_flags = list(payload.get("quality_flags") or [])
        intervals = list((payload.get("intervals") or {}).get("items") or [])
        by_kind: Dict[str, List[Dict[str, Any]]] = {}
        for item in intervals:
            by_kind.setdefault(str(item.get("kind") or ""), []).append(item)

        def value_at(kind: str, ts_ms: int) -> str:
            value = ""
            for item in by_kind.get(kind, []):
                if int(item["start_ms"]) > ts_ms:
                    break
                finish = item.get("end_ms")
                if finish is None or ts_ms < int(finish):
                    value = str(item.get("value_code") or "")
            return value

        def series_value(series_id: str, index: int) -> Optional[float]:
            values = list(series.get(series_id) or [])
            return values[index] if index < len(values) else None

        points: List[Dict[str, Any]] = []
        for index, ts_value in enumerate(timestamps):
            bucket_ms = int(ts_value)
            ts_ms = int(sample_timestamps[index]) if index < len(sample_timestamps) else bucket_ms
            mode = value_at("OPERATING_MODE", ts_ms)
            reason = value_at("CONTROL_REASON", ts_ms)
            active_limiters = {
                str(item.get("value_code") or "")
                for item in by_kind.get("LIMITER", [])
                if int(item["start_ms"]) <= ts_ms
                and (item.get("end_ms") is None or ts_ms < int(item["end_ms"]))
            }
            grid = series_value("grid_power_w", index)
            quality = int(quality_flags[index] or 0) if index < len(quality_flags) else 0
            points.append({
                "epoch_ms": ts_ms,
                "grid_power_w": grid,
                # The V13 UI never consumes minute min/max today. Keep the
                # compatibility keys without reintroducing a parallel SQL path.
                "grid_power_min_w": grid,
                "grid_power_max_w": grid,
                "grid_power_raw_w": series_value("raw_grid_power_w", index),
                "zendure_target_power_w": series_value("target_final_w", index),
                "zendure_actual_power_w": series_value("zendure_actual_power_w", index),
                "pv_power_w": series_value("pv_power_w", index),
                "house_power_w": series_value("house_power_w", index),
                "soc": series_value("zendure_soc_percent", index),
                "primary_soc": series_value("primary_soc_percent", index),
                "primary_power_w": series_value("primary_power_w", index),
                "mode": mode,
                "mode_label": mode,
                "control_reason": reason,
                "limit_reason": ", ".join(sorted(active_limiters)),
                "data_status": "gültig" if quality else "nicht bewertet",
                "cross_charge_limited": "CROSS_CHARGE" in active_limiters,
                "safe_state_active": mode == "SAFE_STATE" or "SAFE_STATE" in active_limiters,
                "night_window_active": mode == "NIGHT_DISCHARGE",
                "night_reserve_active": "NIGHT_RESERVE_SOC" in active_limiters,
                "sample_count": int(sample_counts[index]) if index < len(sample_counts) else 1,
            })
        return points, {
            "db_status": "hit",
            "db_path": path,
            "db_rows": len(points),
            "db_size_bytes": os.path.getsize(path) if os.path.exists(path) else 0,
            "db_backend": "v3",
            "db_schema_version": 3,
            "query_service": "graph_query_service_v1",
            "compatibility_source": "overview_columnar_v1",
            "overview_meta": dict(payload.get("meta") or {}),
        }

    def storage_day_status(
        self,
        path: str,
        start_ms: int,
        end_ms: int,
        *,
        limit: int = 2000,
    ) -> Dict[str, Any]:
        """Lean V3 day payload for the status-page SOC chart.

        Unlike ``compatibility_points()`` this path intentionally reads only
        the four storage series plus OPERATING_MODE/CONTROL_REASON and the
        effective config timeline. It does not load command events, topology,
        runs, retention, coverage or evidence. Those belong to the analysis
        workspace, not to the small status chart.
        """
        start_ms, end_ms = int(start_ms), int(end_ms)
        if end_ms <= start_ms:
            raise GraphQueryError("INVALID_TIME_RANGE")
        if end_ms - start_ms > DEFAULT_MAX_WINDOW_MS:
            raise GraphQueryError("WINDOW_EXCEEDS_48H")
        ids = (
            "zendure_actual_power_w",
            "zendure_soc_percent",
            "primary_soc_percent",
            "primary_power_w",
        )
        plan = plan_query(start_ms, end_ms, resolution="1min", purpose="overview")
        fingerprint = _db_fingerprint(path)
        key = ("storage_day_status", fingerprint, start_ms, end_ms, int(limit))
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        started = time.perf_counter()
        conn = self._open_v3(path)
        try:
            numeric = _query_numeric(conn, start_ms, end_ms, ids, plan)
            timestamps = list(numeric.get("timestamps_ms") or [])[: max(0, int(limit))]
            series = dict(numeric.get("series") or {})
            # Status SOC needs only two sparse contexts. Query them directly
            # instead of materializing every limiter/quality/command state in
            # the day and filtering in Python. This matters most near the end
            # of a busy day on the Pi 3B+.
            interval_rows = conn.execute(
                """
                SELECT interval_id,kind,run_id,entity_id,start_ms,end_ms,value_code,source,quality
                  FROM graph_intervals
                 WHERE kind IN ('OPERATING_MODE','CONTROL_REASON')
                   AND start_ms<=? AND (end_ms IS NULL OR end_ms>?)
                 ORDER BY start_ms,interval_id
                 LIMIT ?
                """,
                (int(end_ms), int(start_ms), max(5000, int(limit) * 4)),
            ).fetchall()
            intervals = [dict(row) for row in interval_rows]
            config_rows = _query_config(conn, start_ms, end_ms)
        finally:
            conn.close()

        by_kind: Dict[str, List[Dict[str, Any]]] = {}
        for item in intervals:
            by_kind.setdefault(str(item.get("kind") or ""), []).append(item)

        # Bind the four numeric arrays once.  V14.1.3 rebuilt ``list(...)`` for
        # every point/series access, which made a full day scale quadratically
        # in Python allocation/copy work.
        series_values: Dict[str, List[Optional[float]]] = {
            series_id: list(series.get(series_id) or []) for series_id in ids
        }
        timestamp_values = [int(value) for value in timestamps]

        def interval_values(kind: str) -> List[str]:
            """Map sparse intervals to sorted timestamps without rescanning.

            Intervals are ordered by start_ms/interval_id.  A max-priority heap
            preserves the old "latest active interval wins" semantics even if
            malformed/legacy data contains overlaps, while reducing the normal
            full-day path from O(points*intervals) to O((points+intervals) log n).
            """
            items = by_kind.get(kind, [])
            active: List[Tuple[int, int, Optional[int], str]] = []
            cursor = 0
            result: List[str] = []
            for ts_ms in timestamp_values:
                while cursor < len(items) and int(items[cursor]["start_ms"]) <= ts_ms:
                    item = items[cursor]
                    start_value = int(item["start_ms"])
                    interval_id = int(item.get("interval_id") or cursor)
                    finish_raw = item.get("end_ms")
                    finish = int(finish_raw) if finish_raw is not None else None
                    heapq.heappush(
                        active,
                        (-start_value, -interval_id, finish, str(item.get("value_code") or "")),
                    )
                    cursor += 1
                while active and active[0][2] is not None and ts_ms >= int(active[0][2]):
                    heapq.heappop(active)
                result.append(active[0][3] if active else "")
            return result

        mode_values = interval_values("OPERATING_MODE")
        reason_values = interval_values("CONTROL_REASON")

        def series_value(series_id: str, index: int) -> Optional[float]:
            values = series_values.get(series_id) or []
            return values[index] if index < len(values) else None

        points: List[Dict[str, Any]] = []
        for index, ts_ms in enumerate(timestamp_values):
            mode = mode_values[index] if index < len(mode_values) else ""
            points.append({
                "epoch_ms": ts_ms,
                "zendure_actual_power_w": series_value("zendure_actual_power_w", index),
                "soc": series_value("zendure_soc_percent", index),
                "primary_soc": series_value("primary_soc_percent", index),
                "primary_power_w": series_value("primary_power_w", index),
                "mode": mode,
                "control_reason": reason_values[index] if index < len(reason_values) else "",
                "safe_state_active": mode == "SAFE_STATE",
                "night_window_active": mode == "NIGHT_DISCHARGE",
            })

        payload = {
            "points": points,
            "config_timeline": config_rows,
            "meta": {
                "cache": "miss",
                "query_source": plan.source,
                "row_count": len(points),
                "series_count": len(ids),
                "interval_count": len(intervals),
                "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
            },
        }
        self._cache_put(key, payload)
        return payload

    def evidence(
        self,
        path: str,
        start_ms: int,
        end_ms: int,
        *,
        series_ids: Optional[Sequence[str]] = None,
        resolution: str = "highres",
    ) -> Dict[str, Any]:
        start_ms, end_ms = int(start_ms), int(end_ms)
        if end_ms < start_ms:
            raise GraphQueryError("INVALID_TIME_RANGE")
        if end_ms - start_ms > DEFAULT_MAX_WINDOW_MS:
            raise GraphQueryError("WINDOW_EXCEEDS_48H")
        res = str(resolution or "highres").lower()
        if res not in {"highres", "1min"}:
            raise GraphQueryError("INVALID_EVIDENCE_RESOLUTION")
        ids = _validate_series(series_ids)
        key = ("evidence", _db_fingerprint(path), start_ms, end_ms, ids, res)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        conn = self._open_v3(path)
        started = time.perf_counter()
        try:
            payload = {
                "from_ms": start_ms,
                "to_ms": end_ms,
                "resolution": res,
                "series": query_evidence_context(conn, ids, resolution=res, start_ms=start_ms, end_ms=end_ms),
                "retention": _query_retention(conn, start_ms, end_ms),
                "meta": {"cache": "miss", "query_ms": round((time.perf_counter() - started) * 1000.0, 3)},
            }
        finally:
            conn.close()
        self._cache_put(key, payload)
        return payload

    def inspector(
        self,
        path: str,
        ts_ms: int,
        *,
        series_ids: Optional[Sequence[str]] = None,
        tolerance_ms: int = 10_000,
    ) -> Dict[str, Any]:
        """Return one high-resolution cursor snapshot plus its historical context.

        WP8 deliberately treats this as a read-only evidence projection.  Values,
        sparse states, config and topology remain sourced from Graph Core V3; no
        new historical truth is synthesized in the inspector layer.
        """
        ids = _validate_series(series_ids)
        target = int(ts_ms)
        tolerance = max(0, min(int(tolerance_ms), 60_000))
        conn = self._open_v3(path)
        started = time.perf_counter()
        try:
            specs = [SYSTEM_SERIES_BY_ID[sid] for sid in ids]
            cols = ["ts_ms", "quality_flags", "run_id", "command_desired_sequence_id", "command_publish_event_id"] + [spec.column for spec in specs]
            row = conn.execute(
                f"SELECT {','.join(cols)} FROM measurement_raw "
                "WHERE ts_ms BETWEEN ? AND ? ORDER BY ABS(ts_ms-?),ts_ms LIMIT 1",
                (target - tolerance, target + tolerance, target),
            ).fetchone()
            if row is None:
                values = {sid: None for sid in ids}
                actual_ms = None
                quality = 0
                correlation: Dict[str, Any] = {}
            else:
                values = {spec.series_id: decode_scaled(row[spec.column], scale=spec.scale) for spec in specs}
                actual_ms = int(row["ts_ms"])
                quality = int(row["quality_flags"] or 0)
                correlation = {
                    "run_id": row["run_id"],
                    "desired_sequence_id": row["command_desired_sequence_id"],
                    "publish_event_id": row["command_publish_event_id"],
                }
            context_ms = actual_ms if actual_ms is not None else target
            interval_payload = _query_intervals(conn, context_ms, context_ms, limit=500)
            interval_items = list(interval_payload.get("items") or [])
            active_states: Dict[str, List[Dict[str, Any]]] = {}
            for item in interval_items:
                active_states.setdefault(str(item.get("kind") or ""), []).append(dict(item))
            events = _query_events(conn, context_ms - tolerance, context_ms + tolerance, limit=500)
            config = _query_config(conn, context_ms, context_ms)
            topology = _query_topology(conn, context_ms, context_ms)
            runs = _query_runs(conn, context_ms, context_ms)

            linked_event = None
            publish_id = correlation.get("publish_event_id") if correlation else None
            run_id = correlation.get("run_id") if correlation else None
            if publish_id is not None:
                if run_id is None:
                    event_row = conn.execute(
                        "SELECT * FROM graph_command_events WHERE publish_event_id=? AND event_type='PUBLISHED' "
                        "ORDER BY ABS(ts_ms-?),event_id LIMIT 1",
                        (int(publish_id), context_ms),
                    ).fetchone()
                else:
                    event_row = conn.execute(
                        "SELECT * FROM graph_command_events WHERE run_id=? AND publish_event_id=? AND event_type='PUBLISHED' "
                        "ORDER BY ABS(ts_ms-?),event_id LIMIT 1",
                        (int(run_id), int(publish_id), context_ms),
                    ).fetchone()
                if event_row is not None:
                    linked_event = _command_event_to_dict(event_row)
                    correlation["linked_event_id"] = int(event_row["event_id"])

            evidence_start = max(0, context_ms - tolerance)
            evidence_end = context_ms + tolerance
            evidence = query_evidence_context(
                conn, ids, resolution="highres", start_ms=evidence_start, end_ms=evidence_end
            )

            topology_by_entity: Dict[int, List[Dict[str, Any]]] = {}
            for item in topology:
                entity_id = item.get("entity_id")
                if entity_id is not None:
                    topology_by_entity.setdefault(int(entity_id), []).append(dict(item))
            entity_rows = _query_entity_rows(conn)
            historical_entities: List[Dict[str, Any]] = []
            for entity_row in entity_rows:
                entity_id = int(entity_row["entity_id"])
                first_seen = entity_row["first_seen_ms"]
                last_seen = entity_row["last_seen_ms"]
                seen_at_cursor = (
                    (first_seen is None or int(first_seen) <= context_ms)
                    and (last_seen is None or int(last_seen) >= context_ms)
                )
                topology_rows = topology_by_entity.get(entity_id, [])
                if not seen_at_cursor and not topology_rows:
                    continue
                binding = str(entity_row["storage_binding"] or ENTITY_BINDING_ENTITY_TABLE).upper()
                entity_values: Dict[str, Optional[float]] = {}
                entity_actual_ms: Optional[int] = None
                if binding in SYSTEM_ENTITY_BINDINGS:
                    mapping = SYSTEM_ENTITY_BINDINGS[binding]
                    for entity_sid, system_sid in mapping.items():
                        entity_values[entity_sid] = values.get(system_sid)
                    entity_actual_ms = actual_ms
                else:
                    e_specs = list(ENTITY_SERIES)
                    e_cols = ["ts_ms", "quality_flags"] + [spec.column for spec in e_specs]
                    e_row = conn.execute(
                        f"SELECT {','.join(e_cols)} FROM measurement_entity_raw WHERE entity_id=? "
                        "AND ts_ms BETWEEN ? AND ? ORDER BY ABS(ts_ms-?),ts_ms LIMIT 1",
                        (entity_id, context_ms - tolerance, context_ms + tolerance, context_ms),
                    ).fetchone()
                    if e_row is not None:
                        entity_actual_ms = int(e_row["ts_ms"])
                        entity_values = {
                            spec.series_id: decode_scaled(e_row[spec.column], scale=spec.scale) for spec in e_specs
                        }
                historical_entities.append({
                    "entity_id": entity_id,
                    "stable_id": str(entity_row["stable_id"]),
                    "entity_type": str(entity_row["entity_type"]),
                    "identity_kind": str(entity_row["identity_kind"] or "LOGICAL_ROLE"),
                    "source_identity": entity_row["source_identity"],
                    "storage_binding": binding,
                    "display_name": str(entity_row["display_name"] or ""),
                    "metadata": _json_object(entity_row["metadata_json"]),
                    "topology": topology_rows,
                    "actual_ms": entity_actual_ms,
                    "values": entity_values,
                })

            groups = {
                "measurement": {sid: values.get(sid) for sid in (
                    "grid_power_w", "raw_grid_power_w", "control_grid_power_w", "control_grid_power_smoothed_w",
                    "pv_power_w", "house_power_w", "zendure_actual_power_w", "zendure_soc_percent",
                    "primary_power_w", "primary_soc_percent",
                ) if sid in values},
                "target_pipeline": {sid: values.get(sid) for sid in (
                    "target_raw_w", "target_limited_w", "target_filtered_w", "target_step_limited_w", "target_final_w",
                ) if sid in values},
                "command": {sid: values.get(sid) for sid in (
                    "command_desired_target_w", "command_readback_target_w",
                ) if sid in values},
            }
            return {
                "contract_version": 2,
                "requested_ms": target,
                "actual_ms": actual_ms,
                "delta_ms": None if actual_ms is None else int(actual_ms - target),
                "quality_flags": quality,
                "values": values,
                "groups": groups,
                "correlation": correlation,
                "linked_command_event": linked_event,
                "intervals": interval_payload,
                "active_states": active_states,
                "command_events": events,
                "config": config[-1] if config else None,
                "entities": historical_entities,
                "topology": topology,
                "runs": runs,
                "evidence": evidence,
                "meta": {
                    "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "tolerance_ms": tolerance,
                    "entity_count": len(historical_entities),
                    "read_only": True,
                },
            }
        finally:
            conn.close()

    def command_follow(
        self,
        path: str,
        *,
        event_id: Optional[int] = None,
        ts_ms: Optional[int] = None,
        tolerance_ms: int = 60_000,
        before_ms: int = 15_000,
        after_ms: int = 180_000,
    ) -> Dict[str, Any]:
        """Correlate one persisted command event with subsequent observations.

        The method intentionally does *not* turn publication or same-direction
        power into an effectiveness verdict.  It reports those stages separately,
        carries the controller's already-persisted effect category as labelled
        evidence, and returns NOT_EVALUABLE where V3 lacks a branch-specific
        historical system target.
        """
        before = max(0, min(int(before_ms), 10 * 60_000))
        after = max(1_000, min(int(after_ms), 10 * 60_000))
        tolerance = max(0, min(int(tolerance_ms), 10 * 60_000))
        conn = self._open_v3(path)
        started = time.perf_counter()
        try:
            event_row = None
            if event_id is not None:
                event_row = conn.execute(
                    "SELECT * FROM graph_command_events WHERE event_id=?", (int(event_id),)
                ).fetchone()
                if event_row is None:
                    raise GraphQueryError("UNKNOWN_COMMAND_EVENT")
                if str(event_row["event_type"] or "").upper() != "PUBLISHED":
                    raise GraphQueryError("COMMAND_EVENT_NOT_PUBLISHED")
            else:
                target = int(ts_ms if ts_ms is not None else time.time() * 1000)
                event_row = conn.execute(
                    "SELECT * FROM graph_command_events WHERE event_type='PUBLISHED' AND ts_ms BETWEEN ? AND ? "
                    "ORDER BY ABS(ts_ms-?),ts_ms,event_id LIMIT 1",
                    (target - tolerance, target + tolerance, target),
                ).fetchone()
                if event_row is None:
                    raise GraphQueryError("COMMAND_EVENT_NOT_FOUND")
            event = _command_event_to_dict(event_row)
            event_ts = int(event["ts_ms"])
            start_ms = event_ts - before
            requested_end_ms = event_ts + after

            # A Command-Follow result belongs to exactly one persisted publish.
            # Later publishes may continue the same controller intent, but their
            # observations/effect intervals must not be retroactively attributed
            # to this event.  Censor the causal window at the next publish for
            # the same run/entity and expose that boundary explicitly.
            run_id = event.get("run_id")
            entity_id = event.get("entity_id")
            params: List[Any] = [int(run_id), event_ts, event_ts, int(event["event_id"])]
            entity_clause = "entity_id IS NULL"
            if entity_id is not None:
                entity_clause = "entity_id=?"
                params.append(int(entity_id))
            next_publish_row = conn.execute(
                "SELECT * FROM graph_command_events WHERE event_type='PUBLISHED' AND run_id=? "
                "AND (ts_ms>? OR (ts_ms=? AND event_id>?)) AND " + entity_clause +
                " ORDER BY ts_ms,event_id LIMIT 1",
                tuple(params),
            ).fetchone()
            next_publish = _command_event_to_dict(next_publish_row) if next_publish_row is not None else None
            next_publish_ms = int(next_publish["ts_ms"]) if next_publish is not None else None
            censored = next_publish_ms is not None and next_publish_ms <= requested_end_ms
            if censored and next_publish_ms > event_ts:
                end_ms = next_publish_ms - 1
            elif censored:
                # Same-ms publishes cannot be separated from raw samples by the
                # current millisecond storage key. Keep the event timestamp only
                # and flag the ambiguity instead of attributing later time.
                end_ms = event_ts
            else:
                end_ms = requested_end_ms
            follow_ids = (
                "grid_power_w", "control_grid_power_w", "zendure_actual_power_w",
                "target_final_w", "command_desired_target_w", "command_readback_target_w",
                "zendure_soc_percent", "primary_power_w", "primary_soc_percent",
            )
            numeric = _query_numeric(conn, start_ms, end_ms, follow_ids, QueryPlan("raw", 0, "command_follow_requires_highres"))
            timestamps = list(numeric.get("timestamps_ms") or [])
            series = dict(numeric.get("series") or {})

            desired_target = event.get("desired_target_w")
            if desired_target is None:
                desired_values = list(series.get("command_desired_target_w") or [])
                post_pairs = [(ts, desired_values[i]) for i, ts in enumerate(timestamps) if ts >= event_ts and i < len(desired_values) and desired_values[i] is not None]
                if post_pairs:
                    desired_target = post_pairs[0][1]
            desired_target = None if desired_target is None else float(desired_target)

            actual_values = list(series.get("zendure_actual_power_w") or [])
            readback_values = list(series.get("command_readback_target_w") or [])
            grid_values = list(series.get("grid_power_w") or [])

            def last_before(values: Sequence[Optional[float]]) -> Tuple[Optional[int], Optional[float]]:
                pairs = [(int(ts), values[i]) for i, ts in enumerate(timestamps) if int(ts) < event_ts and i < len(values) and values[i] is not None]
                return pairs[-1] if pairs else (None, None)

            def first_after(values: Sequence[Optional[float]]) -> Tuple[Optional[int], Optional[float]]:
                for i, ts in enumerate(timestamps):
                    if int(ts) >= event_ts and i < len(values) and values[i] is not None:
                        return int(ts), float(values[i])
                return None, None

            baseline_actual_ms, baseline_actual = last_before(actual_values)
            first_actual_ms, first_actual = first_after(actual_values)
            baseline_grid_ms, baseline_grid = last_before(grid_values)
            _first_grid_ms, first_grid = first_after(grid_values)

            direction_payload: Dict[str, Any]
            if desired_target is None or desired_target == 0:
                direction_payload = {
                    "status": "NOT_EVALUABLE",
                    "reason": "NO_NONZERO_DIRECTION_TARGET",
                    "latency_ms": None,
                    "first_observed_ms": first_actual_ms,
                    "first_observed_w": first_actual,
                    "causal_attribution": "NOT_PROVEN",
                }
            else:
                desired_sign = 1 if desired_target > 0 else -1
                baseline_same = baseline_actual is not None and ((baseline_actual > 0) - (baseline_actual < 0)) == desired_sign
                first_match = None
                for i, ts in enumerate(timestamps):
                    if int(ts) < event_ts or i >= len(actual_values):
                        continue
                    value = actual_values[i]
                    if value is None or float(value) == 0:
                        continue
                    if ((float(value) > 0) - (float(value) < 0)) == desired_sign:
                        first_match = (int(ts), float(value))
                        break
                if baseline_same:
                    direction_payload = {
                        "status": "PREEXISTING_DIRECTION",
                        "reason": "SAME_DIRECTION_ALREADY_OBSERVED_BEFORE_PUBLISH",
                        "latency_ms": None,
                        "first_observed_ms": first_match[0] if first_match else None,
                        "first_observed_w": first_match[1] if first_match else None,
                        "causal_attribution": "NOT_PROVEN",
                    }
                elif first_match is not None:
                    direction_payload = {
                        "status": "OBSERVED_AFTER_PUBLISH",
                        "reason": "SIGNED_ACTUAL_POWER_ENTERED_REQUESTED_DIRECTION",
                        "latency_ms": int(first_match[0] - event_ts),
                        "first_observed_ms": first_match[0],
                        "first_observed_w": first_match[1],
                        "causal_attribution": "NOT_PROVEN",
                    }
                else:
                    direction_payload = {
                        "status": "NO_OBSERVATION",
                        "reason": "NO_SAME_DIRECTION_ACTUAL_POWER_IN_WINDOW",
                        "latency_ms": None,
                        "first_observed_ms": None,
                        "first_observed_w": None,
                        "causal_attribution": "NOT_PROVEN",
                    }

            readback_payload: Dict[str, Any]
            if desired_target is None:
                readback_payload = {"status": "UNKNOWN", "reason": "DESIRED_TARGET_UNKNOWN", "latency_ms": None}
            else:
                baseline_rb_ms, baseline_rb = last_before(readback_values)
                preexisting = baseline_rb is not None and abs(float(baseline_rb) - desired_target) < 1e-9
                rb_match = None
                for i, ts in enumerate(timestamps):
                    if int(ts) < event_ts or i >= len(readback_values):
                        continue
                    value = readback_values[i]
                    if value is not None and abs(float(value) - desired_target) < 1e-9:
                        rb_match = (int(ts), float(value))
                        break
                if preexisting:
                    readback_payload = {
                        "status": "PREEXISTING_MATCH", "reason": "READBACK_ALREADY_MATCHED_BEFORE_PUBLISH",
                        "latency_ms": None, "matched_ms": baseline_rb_ms, "readback_w": baseline_rb,
                    }
                elif rb_match is not None:
                    readback_payload = {
                        "status": "MATCH_OBSERVED", "reason": "READBACK_TARGET_EQUALS_DESIRED_TARGET",
                        "latency_ms": int(rb_match[0] - event_ts), "matched_ms": rb_match[0], "readback_w": rb_match[1],
                    }
                else:
                    readback_payload = {
                        "status": "NO_MATCH_OBSERVED", "reason": "NO_EQUAL_READBACK_TARGET_IN_WINDOW",
                        "latency_ms": None, "matched_ms": None, "readback_w": None,
                    }

            tracking_errors: List[Tuple[int, float]] = []
            if desired_target is not None:
                for i, ts in enumerate(timestamps):
                    if int(ts) < event_ts or i >= len(actual_values):
                        continue
                    value = actual_values[i]
                    if value is not None:
                        tracking_errors.append((int(ts), abs(float(value) - desired_target)))
            tracking_payload: Dict[str, Any] = {
                "status": "OBSERVATION_ONLY" if tracking_errors else "UNKNOWN",
                "reason": "NO_HISTORICAL_TOLERANCE_ASSUMED" if tracking_errors else "NO_ACTUAL_POWER_OBSERVATION",
                "first_abs_error_w": tracking_errors[0][1] if tracking_errors else None,
                "best_abs_error_w": min((x[1] for x in tracking_errors), default=None),
                "last_abs_error_w": tracking_errors[-1][1] if tracking_errors else None,
                "sample_count": len(tracking_errors),
            }

            interval_payload = _query_intervals(conn, start_ms, end_ms, limit=2000)
            interval_items = list(interval_payload.get("items") or [])
            effect_history = [dict(item) for item in interval_items if str(item.get("kind") or "") == "COMMAND_EFFECT"]
            lifecycle_history = [dict(item) for item in interval_items if str(item.get("kind") or "") == "COMMAND_LIFECYCLE"]
            readback_state_history = [dict(item) for item in interval_items if str(item.get("kind") or "") == "COMMAND_READBACK_MATCH"]
            observation_direction_history = [dict(item) for item in interval_items if str(item.get("kind") or "") == "POWER_OBSERVATION_DIRECTION"]
            observation_confidence_history = [dict(item) for item in interval_items if str(item.get("kind") or "") == "POWER_OBSERVATION_CONFIDENCE"]

            effect_categories = []
            for item in effect_history:
                code = str(item.get("value_code") or "")
                if code and code not in effect_categories:
                    effect_categories.append(code)
            recorded_status = "UNKNOWN"
            if "COMMAND_BELOW_DIAGNOSTIC_THRESHOLD" in effect_categories:
                recorded_status = "NOT_EVALUABLE"
            elif "COMMAND_MISMATCH_CONFIRMED" in effect_categories or "COMMAND_NEUTRALIZATION_MISMATCH" in effect_categories:
                recorded_status = "MISMATCH_RECORDED"
            elif "COMMAND_TARGET_TRACKING_EFFECTIVE" in effect_categories:
                recorded_status = "TARGET_TRACKING_RECORDED"
            elif "COMMAND_PARTIALLY_EFFECTIVE" in effect_categories:
                recorded_status = "PARTIAL_EFFECT_RECORDED"
            elif "COMMAND_PENDING" in effect_categories:
                recorded_status = "PENDING_RECORDED"
            controller_assessment = {
                "status": recorded_status,
                "categories": effect_categories,
                "source": "PERSISTED_COMMAND_EFFECT_INTERVALS",
                "independent_wp8_verdict": False,
            }

            post_grid = [float(grid_values[i]) for i, ts in enumerate(timestamps) if int(ts) >= event_ts and i < len(grid_values) and grid_values[i] is not None]
            system_observation = {
                "status": "NOT_EVALUABLE",
                "reason": "NO_BRANCH_SPECIFIC_HISTORICAL_SYSTEM_TARGET_CONTRACT",
                "baseline_grid_w": baseline_grid,
                "first_grid_w": first_grid,
                "last_grid_w": post_grid[-1] if post_grid else None,
                "best_abs_grid_w": min((abs(x) for x in post_grid), default=None),
                "grid_sample_count": len(post_grid),
                "note": "Grid movement is observable, but WP8 does not infer goal attainment without the branch-specific historical target contract.",
            }

            evidence = query_evidence_context(conn, follow_ids, resolution="highres", start_ms=start_ms, end_ms=end_ms)
            events = _query_events(conn, start_ms, end_ms, limit=2000)
            config = _query_config(conn, event_ts, event_ts)
            topology = _query_topology(conn, event_ts, event_ts)
            critical = ("zendure_actual_power_w", "command_desired_target_w", "command_readback_target_w")
            evidence_states: Dict[str, List[str]] = {
                sid: sorted({str(seg.get("status") or EVIDENCE_UNKNOWN) for seg in evidence.get(sid, [])}) for sid in critical
            }
            if all(states and set(states) == {EVIDENCE_AVAILABLE} for states in evidence_states.values()):
                evidence_quality = "AVAILABLE"
            elif any(EVIDENCE_GAP in states or EVIDENCE_UNKNOWN in states for states in evidence_states.values()):
                evidence_quality = "PARTIAL_OR_GAPPED"
            else:
                evidence_quality = "UNKNOWN"

            return {
                "contract_version": 1,
                "event": event,
                "window": {
                    "from_ms": start_ms,
                    "event_ms": event_ts,
                    "to_ms": end_ms,
                    "requested_to_ms": requested_end_ms,
                    "before_ms": before,
                    "after_ms": after,
                    "censored_by_next_publish": bool(censored),
                    "next_publish_event_id": int(next_publish["event_id"]) if next_publish is not None else None,
                    "next_publish_ms": next_publish_ms,
                    "same_timestamp_publish_ambiguity": bool(censored and next_publish_ms == event_ts),
                },
                "timeline": {
                    "format": FORMAT_COLUMNAR_V1,
                    "timestamps_ms": timestamps,
                    "quality_flags": list(numeric.get("quality_flags") or []),
                    "series": series,
                },
                "stages": {
                    "publish": {"status": "OBSERVED", "event_id": int(event["event_id"]), "event_ms": event_ts},
                    "direction_reaction": direction_payload,
                    "readback": readback_payload,
                    "tracking": tracking_payload,
                    "controller_assessment": controller_assessment,
                    "system_effect": system_observation,
                },
                "context": {
                    "intervals": interval_payload,
                    "command_events": events,
                    "effect_history": effect_history,
                    "lifecycle_history": lifecycle_history,
                    "readback_state_history": readback_state_history,
                    "power_observation_direction_history": observation_direction_history,
                    "power_observation_confidence_history": observation_confidence_history,
                    "config": config[-1] if config else None,
                    "topology": topology,
                },
                "evidence": evidence,
                "evidence_quality": evidence_quality,
                "meta": {
                    "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "read_only": True,
                    "causal_attribution": "NOT_PROVEN_BY_TEMPORAL_ORDER_ALONE",
                    "effectiveness_from_publish_alone": False,
                    "effectiveness_from_direction_alone": False,
                },
            }
        finally:
            conn.close()

    @staticmethod
    def _episode_trigger_from_row(row: Mapping[str, Any], trigger_type: str) -> Dict[str, Any]:
        if trigger_type == "PUBLISHED_EVENT":
            event = _command_event_to_dict(row)
            return {
                "trigger_id": f"event:{int(event['event_id'])}",
                "trigger_type": "PUBLISHED_EVENT",
                "trigger_ms": int(event["ts_ms"]),
                "run_id": event.get("run_id"),
                "entity_id": event.get("entity_id"),
                "event_id": int(event["event_id"]),
                "event_type": "PUBLISHED",
                "value_code": str(event.get("reason") or "PUBLISHED"),
                "desired_sequence_id": event.get("desired_sequence_id"),
                "publish_event_id": event.get("publish_event_id"),
                "requested_target_w": event.get("requested_target_w"),
                "desired_target_w": event.get("desired_target_w"),
                "source": "graph_command_events",
            }
        return {
            "trigger_id": f"interval:{int(row['interval_id'])}",
            "trigger_type": "INTERVAL_START",
            "trigger_ms": int(row["start_ms"]),
            "run_id": row["run_id"],
            "entity_id": row["entity_id"],
            "interval_id": int(row["interval_id"]),
            "interval_kind": str(row["kind"]),
            "value_code": str(row["value_code"]),
            "quality": str(row["quality"] or "UNKNOWN"),
            "source": str(row["source"] or "graph_intervals"),
        }

    @staticmethod
    def _resolve_episode_trigger(conn: sqlite3.Connection, trigger_id: str) -> Dict[str, Any]:
        raw = str(trigger_id or "").strip()
        if raw.startswith("event:"):
            try:
                ident = int(raw.split(":", 1)[1])
            except Exception as exc:
                raise GraphQueryError("INVALID_EPISODE_TRIGGER") from exc
            row = conn.execute("SELECT * FROM graph_command_events WHERE event_id=?", (ident,)).fetchone()
            if row is None:
                raise GraphQueryError("EPISODE_TRIGGER_NOT_FOUND")
            if str(row["event_type"] or "").upper() != "PUBLISHED":
                raise GraphQueryError("EPISODE_TRIGGER_EVENT_NOT_PUBLISHED")
            return GraphQueryService._episode_trigger_from_row(row, "PUBLISHED_EVENT")
        if raw.startswith("interval:"):
            try:
                ident = int(raw.split(":", 1)[1])
            except Exception as exc:
                raise GraphQueryError("INVALID_EPISODE_TRIGGER") from exc
            row = conn.execute(
                "SELECT interval_id,kind,run_id,entity_id,start_ms,end_ms,value_code,source,quality "
                "FROM graph_intervals WHERE interval_id=?", (ident,),
            ).fetchone()
            if row is None:
                raise GraphQueryError("EPISODE_TRIGGER_NOT_FOUND")
            if str(row["kind"] or "") not in {"OPERATING_MODE", "CONTROL_INTENT", "CONTROL_REASON"}:
                raise GraphQueryError("EPISODE_TRIGGER_INTERVAL_KIND_NOT_ALLOWED")
            return GraphQueryService._episode_trigger_from_row(row, "INTERVAL_START")
        raise GraphQueryError("INVALID_EPISODE_TRIGGER")

    def episode_triggers(
        self,
        path: str,
        start_ms: int,
        end_ms: int,
        *,
        limit: int = 500,
    ) -> Dict[str, Any]:
        start_ms, end_ms = int(start_ms), int(end_ms)
        if end_ms <= start_ms:
            raise GraphQueryError("INVALID_TIME_RANGE")
        if end_ms - start_ms > DEFAULT_MAX_WINDOW_MS:
            raise GraphQueryError("WINDOW_EXCEEDS_48H")
        bounded_limit = max(1, min(int(limit), 2000))
        conn = self._open_v3(path)
        started = time.perf_counter()
        try:
            event_rows = conn.execute(
                "SELECT * FROM graph_command_events WHERE event_type='PUBLISHED' AND ts_ms>=? AND ts_ms<=? "
                "ORDER BY ts_ms,event_id LIMIT ?",
                (start_ms, end_ms, bounded_limit + 1),
            ).fetchall()
            interval_rows = conn.execute(
                "SELECT interval_id,kind,run_id,entity_id,start_ms,end_ms,value_code,source,quality "
                "FROM graph_intervals WHERE kind IN ('OPERATING_MODE','CONTROL_INTENT','CONTROL_REASON') "
                "AND start_ms>=? AND start_ms<=? ORDER BY start_ms,interval_id LIMIT ?",
                (start_ms, end_ms, bounded_limit + 1),
            ).fetchall()
            items = [self._episode_trigger_from_row(row, "PUBLISHED_EVENT") for row in event_rows]
            items += [self._episode_trigger_from_row(row, "INTERVAL_START") for row in interval_rows]
            items.sort(key=lambda item: (int(item["trigger_ms"]), str(item["trigger_type"]), str(item["trigger_id"])))
            truncated = len(event_rows) > bounded_limit or len(interval_rows) > bounded_limit or len(items) > bounded_limit
            if len(items) > bounded_limit:
                items = items[:bounded_limit]
            return {
                "contract_version": 1,
                "from_ms": start_ms,
                "to_ms": end_ms,
                "items": items,
                "truncated": bool(truncated),
                "limit": bounded_limit,
                "meta": {
                    "read_only": True,
                    "allowed_event_type": "PUBLISHED",
                    "allowed_interval_kinds": ["OPERATING_MODE", "CONTROL_INTENT", "CONTROL_REASON"],
                    "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                },
            }
        finally:
            conn.close()

    @staticmethod
    def _episode_window_coverage(numeric: Mapping[str, Any], series_ids: Sequence[str]) -> Dict[str, Any]:
        timestamps = list(numeric.get("timestamps_ms") or [])
        total = len(timestamps)
        result: Dict[str, Any] = {}
        series = numeric.get("series") or {}
        for sid in series_ids:
            values = list(series.get(sid) or [])
            non_null = sum(1 for value in values if value is not None)
            if total <= 0 or non_null <= 0:
                status = "NO_DATA"
            elif non_null >= total:
                status = "AVAILABLE"
            else:
                status = "PARTIAL"
            result[str(sid)] = {
                "status": status,
                "sample_slots": total,
                "non_null_samples": non_null,
                "fraction": (float(non_null) / float(total)) if total else 0.0,
            }
        return result

    def episode_comparison(
        self,
        path: str,
        trigger_a: str,
        trigger_b: str,
        *,
        before_ms: int,
        after_ms: int,
        series_ids: Optional[Sequence[str]] = None,
        stable_ids: Optional[Sequence[str]] = None,
        entity_series_ids: Optional[Sequence[str]] = None,
        resolution: str = "auto",
    ) -> Dict[str, Any]:
        before, after = max(0, int(before_ms)), max(1, int(after_ms))
        if before + after > DEFAULT_MAX_WINDOW_MS:
            raise GraphQueryError("EPISODE_WINDOW_EXCEEDS_48H")
        if str(trigger_a or "").strip() == str(trigger_b or "").strip():
            raise GraphQueryError("EPISODES_MUST_DIFFER")
        ids = _validate_series(series_ids)
        entity_ids = tuple(str(item).strip() for item in (stable_ids or ()) if str(item).strip())
        entity_series = _validate_entity_series(entity_series_ids) if entity_ids else tuple()
        conn = self._open_v3(path)
        try:
            a = self._resolve_episode_trigger(conn, trigger_a)
            b = self._resolve_episode_trigger(conn, trigger_b)
        finally:
            conn.close()

        started = time.perf_counter()

        def build_episode(trigger: Mapping[str, Any]) -> Dict[str, Any]:
            anchor = int(trigger["trigger_ms"])
            start = anchor - before
            end = anchor + after
            overview = self.overview(
                path, start, end, series_ids=ids, resolution=resolution, include_context=True,
            )
            overview["relative_timestamps_ms"] = [int(ts) - anchor for ts in overview.get("timestamps_ms") or []]
            evidence_resolution = "highres" if str(overview.get("resolution")) == "highres" else "1min"
            evidence = self.evidence(path, start, end, series_ids=ids, resolution=evidence_resolution)
            entities_payload: Dict[str, Any] = {
                "format": FORMAT_COLUMNAR_V1, "from_ms": start, "to_ms": end,
                "resolution": overview.get("resolution"), "entities": {}, "meta": {"entity_count": 0},
            }
            if entity_ids:
                entities_payload = self.entity_overview(
                    path, start, end, stable_ids=entity_ids, series_ids=entity_series, resolution=resolution,
                )
                for entity in (entities_payload.get("entities") or {}).values():
                    entity["relative_timestamps_ms"] = [int(ts) - anchor for ts in entity.get("timestamps_ms") or []]
            entity_window_coverage: Dict[str, Any] = {}
            for stable_id, entity in (entities_payload.get("entities") or {}).items():
                entity_window_coverage[str(stable_id)] = self._episode_window_coverage(entity, entity_series)
            return {
                "trigger": dict(trigger),
                "window": {
                    "t0_ms": anchor,
                    "absolute_from_ms": start,
                    "absolute_to_ms": end,
                    "relative_from_ms": -before,
                    "relative_to_ms": after,
                    "before_ms": before,
                    "after_ms": after,
                },
                "overview": overview,
                "entities": entities_payload,
                "window_coverage": {
                    "system": self._episode_window_coverage(overview, ids),
                    "entities": entity_window_coverage,
                },
                "evidence": evidence,
            }

        return {
            "contract_version": 1,
            "alignment": {
                "axis": "RELATIVE_T0_MS",
                "t0_definition": "PERSISTED_TRIGGER_TIMESTAMP",
                "absolute_time_retained": True,
                "visual_similarity_is_causality_proof": False,
                "episode_count": 2,
            },
            "series_ids": list(ids),
            "entity_ids": list(entity_ids),
            "entity_series_ids": list(entity_series),
            "episodes": {
                "a": build_episode(a),
                "b": build_episode(b),
            },
            "meta": {
                "read_only": True,
                "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                "missing_series_are_not_imputed": True,
                "missing_entities_are_not_invented": True,
                "comparison_is_descriptive_not_causal": True,
            },
        }

    def coverage(self, path: str, *, series_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        ids = _validate_series(series_ids)
        key = ("coverage", _db_fingerprint(path), ids)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        conn = self._open_v3(path)
        started = time.perf_counter()
        try:
            series_payload = query_series_coverage(conn, ids)
            evidence_payload = _coverage_evidence_bulk(conn, ids, resolution="highres")
            for sid in ids:
                series_payload[sid]["evidence_segments"] = evidence_payload[sid]
            payload = {
                "series": series_payload,
                "meta": {
                    "cache": "miss",
                    "query_ms": round((time.perf_counter() - started) * 1000.0, 3),
                },
            }
        finally:
            conn.close()
        self._cache_put(key, payload)
        return payload


GRAPH_QUERY_SERVICE = GraphQueryService()
