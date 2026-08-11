# SPDX-License-Identifier: AGPL-3.0-or-later
"""Historical effective-config overlay timeline for the SOC day graph."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from csv_logger import compute_config_control_hash
from measurement_db import resolve_measurement_db_path

TIMELINE_VERSION = "1"


def _hhmm(params: Mapping[str, Any], prefix: str, derived: str, default: str) -> str:
    direct = str(params.get(derived) or "").strip()
    if len(direct) == 5 and direct[2] == ":":
        return direct
    try:
        return f"{int(params.get(prefix + '_HOUR')):02d}:{int(params.get(prefix + '_MINUTE')):02d}"
    except Exception:
        return default


def overlay_from_parameters(params: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "min_soc": params.get("MIN_SOC_PERCENT"),
        "max_soc": params.get("MAX_SOC_PERCENT"),
        "reserve_soc": params.get("NIGHT_DISCHARGE_STOP_SOC_PERCENT"),
        "night_start": _hhmm(params, "NIGHT_START", "NIGHT_DISCHARGE_START", ""),
        "night_end": _hhmm(params, "NIGHT_END", "NIGHT_DISCHARGE_END", ""),
    }


def overlay_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    return overlay_from_parameters(config)


def ensure_graph_config_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_config_timeline (
            effective_from_ms INTEGER PRIMARY KEY,
            config_control_hash TEXT NOT NULL,
            known INTEGER NOT NULL,
            min_soc REAL,
            max_soc REAL,
            reserve_soc REAL,
            night_start TEXT,
            night_end TEXT,
            source TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_config_timeline_hash ON graph_config_timeline(config_control_hash)")
    conn.execute("CREATE TABLE IF NOT EXISTS measurement_meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('graph_config_timeline_version',?)", (TIMELINE_VERSION,))


def _semantic_tuple(config_hash: str, known: bool, overlay: Mapping[str, Any]) -> Tuple[Any, ...]:
    return (
        str(config_hash), int(bool(known)), overlay.get("min_soc"), overlay.get("max_soc"),
        overlay.get("reserve_soc"), str(overlay.get("night_start") or ""), str(overlay.get("night_end") or ""),
    )


def upsert_timeline_entry(
    conn: sqlite3.Connection,
    effective_from_ms: int,
    config_hash: str,
    *,
    overlay: Optional[Mapping[str, Any]],
    source: str,
    known: bool = True,
    ensure_schema: bool = True,
) -> bool:
    if ensure_schema:
        ensure_graph_config_schema(conn)
    ts = int(effective_from_ms)
    digest = str(config_hash or "").strip()
    if not digest:
        return False
    ov = dict(overlay or {}) if known else {"min_soc": None, "max_soc": None, "reserve_soc": None, "night_start": "", "night_end": ""}
    desired = _semantic_tuple(digest, known, ov)
    exact = conn.execute(
        """SELECT config_control_hash,known,min_soc,max_soc,reserve_soc,night_start,night_end
           FROM graph_config_timeline WHERE effective_from_ms=?""", (ts,)
    ).fetchone()
    if exact is not None:
        exact_tuple = (str(exact[0]), int(exact[1]), exact[2], exact[3], exact[4], str(exact[5] or ""), str(exact[6] or ""))
        if exact_tuple == desired:
            return False
    previous = conn.execute(
        """SELECT config_control_hash,known,min_soc,max_soc,reserve_soc,night_start,night_end
           FROM graph_config_timeline WHERE effective_from_ms < ? ORDER BY effective_from_ms DESC LIMIT 1""",
        (ts,),
    ).fetchone()
    if previous is not None:
        prev_tuple = (str(previous[0]), int(previous[1]), previous[2], previous[3], previous[4], str(previous[5] or ""), str(previous[6] or ""))
        existing_same_ts = conn.execute("SELECT 1 FROM graph_config_timeline WHERE effective_from_ms=?", (ts,)).fetchone()
        if prev_tuple == desired and existing_same_ts is None:
            return False
    conn.execute(
        """INSERT OR REPLACE INTO graph_config_timeline(
            effective_from_ms,config_control_hash,known,min_soc,max_soc,reserve_soc,night_start,night_end,source
        ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (ts, digest, 1 if known else 0, ov.get("min_soc"), ov.get("max_soc"), ov.get("reserve_soc"),
         str(ov.get("night_start") or ""), str(ov.get("night_end") or ""), str(source or "runtime")),
    )
    # If the following entry is semantically identical, the newly inserted boundary
    # already represents it and the duplicate can be removed.
    following = conn.execute(
        """SELECT effective_from_ms,config_control_hash,known,min_soc,max_soc,reserve_soc,night_start,night_end
           FROM graph_config_timeline WHERE effective_from_ms > ? ORDER BY effective_from_ms ASC LIMIT 1""",
        (ts,),
    ).fetchone()
    if following is not None:
        foll_tuple = (str(following[1]), int(following[2]), following[3], following[4], following[5], str(following[6] or ""), str(following[7] or ""))
        if foll_tuple == desired:
            conn.execute("DELETE FROM graph_config_timeline WHERE effective_from_ms=?", (int(following[0]),))
    conn.commit()
    return True


def record_runtime_config(conn: sqlite3.Connection, ts_ms: int, config: Mapping[str, Any], config_hash: str = "") -> bool:
    digest = str(config_hash or compute_config_control_hash(dict(config)))
    return upsert_timeline_entry(
        conn, ts_ms, digest, overlay=overlay_from_config(config), source="runtime_effective", known=True,
    )


def load_snapshot_map(path: str) -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except Exception:
        return {}
    result: Dict[str, Dict[str, Any]] = {}
    for item in doc.get("snapshots", []) if isinstance(doc, Mapping) else []:
        if not isinstance(item, Mapping):
            continue
        digest = str(item.get("config_control_hash") or "")
        params = item.get("control_parameters")
        if digest and isinstance(params, Mapping):
            result[digest] = dict(params)
    return result


def backfill_entries(
    conn: sqlite3.Connection,
    rows: Iterable[Tuple[int, str]],
    snapshots: Mapping[str, Mapping[str, Any]],
    *,
    source: str = "measurement_v4_backfill",
    presorted: bool = False,
) -> Dict[str, int]:
    ensure_graph_config_schema(conn)
    inserted = 0
    unknown = 0
    seen = 0
    last_hash = None
    normalized = ((int(ts), str(h)) for ts, h in rows if str(h))
    ordered = normalized if presorted else sorted(normalized, key=lambda x: x[0])
    for ts_ms, digest in ordered:
        if digest == last_hash:
            continue
        seen += 1
        params = snapshots.get(digest)
        known = isinstance(params, Mapping)
        if not known:
            unknown += 1
        if upsert_timeline_entry(
            conn, ts_ms, digest,
            overlay=overlay_from_parameters(params or {}), source=source, known=known, ensure_schema=False,
        ):
            inserted += 1
        last_hash = digest
    return {"hash_transitions_seen": seen, "entries_inserted": inserted, "unknown_snapshots": unknown}


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "effective_from_ms": int(row["effective_from_ms"]),
        "config_control_hash": str(row["config_control_hash"]),
        "known": bool(row["known"]),
        "min_soc": row["min_soc"],
        "max_soc": row["max_soc"],
        "reserve_soc": row["reserve_soc"],
        "night_start": row["night_start"] or "",
        "night_end": row["night_end"] or "",
        "source": row["source"] or "",
    }


def query_timeline_rows(config: Mapping[str, Any], start_dt: datetime, end_dt: datetime) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    path = resolve_measurement_db_path(dict(config))
    if not os.path.exists(path):
        return [], {"timeline_status": "db_missing", "db_path": path}
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(path, timeout=1.0)
        conn.row_factory = sqlite3.Row
        # Do not mutate a historical DB just by reading the graph. Older DBs that
        # have not been backfilled simply report no timeline.
        table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_config_timeline'").fetchone()
        if table is None:
            return [], {"timeline_status": "not_backfilled", "db_path": path}
        prior = conn.execute(
            "SELECT * FROM graph_config_timeline WHERE effective_from_ms <= ? ORDER BY effective_from_ms DESC LIMIT 1",
            (start_ms,),
        ).fetchall()
        inside = conn.execute(
            "SELECT * FROM graph_config_timeline WHERE effective_from_ms > ? AND effective_from_ms < ? ORDER BY effective_from_ms ASC",
            (start_ms, end_ms),
        ).fetchall()
        rows = prior + inside
        return [_row_to_dict(row) for row in rows], {"timeline_status": "hit", "db_path": path}
    except Exception as exc:
        return [], {"timeline_status": "error", "db_path": path, "timeline_error": str(exc)}
    finally:
        if conn is not None:
            conn.close()


def build_day_segments(
    config: Mapping[str, Any], start_dt: datetime, end_dt: datetime,
    *, current_effective_config: Optional[Mapping[str, Any]] = None, now_dt: Optional[datetime] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows, meta = query_timeline_rows(config, start_dt, end_dt)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    normalized = list(rows)
    if not normalized or normalized[0]["effective_from_ms"] > start_ms:
        normalized.insert(0, {
            "effective_from_ms": start_ms, "config_control_hash": "", "known": False,
            "min_soc": None, "max_soc": None, "reserve_soc": None, "night_start": "", "night_end": "", "source": "unknown",
        })
    elif normalized[0]["effective_from_ms"] < start_ms:
        normalized[0] = dict(normalized[0], effective_from_ms=start_ms)

    # Current effective config may have changed after the latest measurement write.
    now = now_dt or datetime.now()
    if current_effective_config is not None and start_dt <= now < end_dt:
        now_ms = int(now.timestamp() * 1000)
        digest = compute_config_control_hash(dict(current_effective_config))
        ov = overlay_from_config(current_effective_config)
        last = normalized[-1] if normalized else None
        desired = _semantic_tuple(digest, True, ov)
        actual = None if last is None else _semantic_tuple(last.get("config_control_hash", ""), last.get("known", False), last)
        if desired != actual:
            normalized.append({
                "effective_from_ms": now_ms, "config_control_hash": digest, "known": True,
                **ov, "source": "runtime_effective_live",
            })

    normalized.sort(key=lambda x: int(x["effective_from_ms"]))
    # Merge identical overlay semantics for display while retaining a hash only as provenance.
    compact: List[Dict[str, Any]] = []
    for row in normalized:
        display_tuple = (bool(row.get("known")), row.get("min_soc"), row.get("max_soc"), row.get("reserve_soc"), row.get("night_start"), row.get("night_end"))
        if compact:
            prev = compact[-1]
            prev_tuple = (bool(prev.get("known")), prev.get("min_soc"), prev.get("max_soc"), prev.get("reserve_soc"), prev.get("night_start"), prev.get("night_end"))
            if display_tuple == prev_tuple:
                continue
        compact.append(dict(row))
    segments: List[Dict[str, Any]] = []
    for index, row in enumerate(compact):
        seg_start = max(start_ms, int(row["effective_from_ms"]))
        seg_end = end_ms if index + 1 >= len(compact) else min(end_ms, int(compact[index + 1]["effective_from_ms"]))
        if seg_end <= seg_start:
            continue
        item = dict(row)
        item["start_minute"] = max(0, int((seg_start - start_ms) // 60000))
        item["end_minute"] = min(1440, int((seg_end - start_ms + 59999) // 60000))
        segments.append(item)
    meta = dict(meta)
    meta["segments"] = len(segments)
    meta["unknown_segments"] = sum(1 for item in segments if not item.get("known"))
    return segments, meta
