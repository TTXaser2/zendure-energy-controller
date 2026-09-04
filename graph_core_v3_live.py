# SPDX-License-Identifier: AGPL-3.0-or-later
"""Live Graph-Core V3 writer backend.

No controller decisions or MQTT side effects live here. The caller owns the
non-blocking queue; this backend only performs worker-thread SQLite work.
"""
from __future__ import annotations

import copy
import os
import secrets
import sqlite3
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

from graph_config_timeline import upsert_timeline_entry
from graph_core_v3 import (
    CommandEventBuilder,
    EntityPersistenceBuilder,
    INT64_MAX,
    SparseStateBuilder,
    connect_graph_core,
    extract_system_sample,
    insert_system_sample,
    safe_int,
)
from version import APP_BUILD_ID, APP_VERSION


def new_live_run_id() -> int:
    # Keep live ids in the upper positive half of INT64 so they do not collide
    # with the low, sequential ids reconstructed by the offline V4 backfill.
    return (1 << 62) | secrets.randbits(62)


class GraphCoreV3LiveSession:
    def __init__(self, run_id: Optional[int] = None) -> None:
        self.run_id = int(run_id if run_id is not None else new_live_run_id())
        if self.run_id <= 0 or self.run_id > INT64_MAX:
            raise ValueError("LIVE_RUN_ID_OUT_OF_RANGE")
        self._path = ""
        self._sparse: Optional[SparseStateBuilder] = None
        self._commands: Optional[CommandEventBuilder] = None
        self._entities: Optional[EntityPersistenceBuilder] = None
        self._last_ts_ms: Optional[int] = None
        self._last_config_hash = ""
        self._run_registered = False

    def reset_for_path(self, path: str, conn: sqlite3.Connection) -> None:
        self._path = os.path.abspath(path)
        self._sparse = SparseStateBuilder(conn, source="LIVE")
        self._commands = CommandEventBuilder(conn)
        self._entities = EntityPersistenceBuilder(conn, source="LIVE")
        self._last_ts_ms = None
        self._last_config_hash = ""
        self._run_registered = False

    def _bind(self, path: str, conn: sqlite3.Connection) -> None:
        if self._path != os.path.abspath(path) or self._sparse is None or self._commands is None or self._entities is None:
            self.reset_for_path(path, conn)
        else:
            self._sparse.conn = conn
            self._commands.conn = conn
            self._entities.conn = conn

    def _ensure_run(self, conn: sqlite3.Connection, sample: Mapping[str, Any]) -> None:
        if self._run_registered:
            return
        ts_ms = int(sample["ts_ms"])
        cycle = safe_int(sample.get("cycle_index"))
        monotonic_ns = safe_int(sample.get("sample_monotonic_ns"))

        # A process restart creates a new run and therefore a hard semantic
        # boundary for sparse state.  Open intervals from an older LIVE run
        # must never be allowed to look active indefinitely just because the
        # process ended before the in-memory SparseStateBuilder could close
        # them.  graph_runs.end_ms is advanced with every committed batch, so
        # its last value is the strongest persisted boundary we have for that
        # run.  Close only intervals whose owning LIVE run has a known end; do
        # not infer state through the downtime and do not touch reconstructed
        # V4 runs.
        conn.execute(
            """
            UPDATE graph_intervals
               SET end_ms = (
                   SELECT r.end_ms + 1
                     FROM graph_runs AS r
                    WHERE r.run_id = graph_intervals.run_id
               )
             WHERE end_ms IS NULL
               AND run_id IS NOT NULL
               AND run_id <> ?
               AND EXISTS (
                   SELECT 1
                     FROM graph_runs AS r
                    WHERE r.run_id = graph_intervals.run_id
                      AND r.source = 'LIVE'
                      AND r.end_ms IS NOT NULL
                      AND r.end_ms >= graph_intervals.start_ms
               )
            """,
            (self.run_id,),
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO graph_runs(
                run_id,start_ms,end_ms,start_monotonic_ns,source,confidence,
                first_cycle_index,last_cycle_index,app_version,build_id
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                self.run_id, ts_ms, None, monotonic_ns, "LIVE", "OBSERVED",
                cycle, cycle, APP_VERSION, APP_BUILD_ID,
            ),
        )
        existing = conn.execute(
            "SELECT source,start_ms FROM graph_runs WHERE run_id=?", (self.run_id,)
        ).fetchone()
        if existing is None or str(existing[0]) != "LIVE":
            raise RuntimeError("LIVE_RUN_ID_COLLISION")
        self._run_registered = True

    @staticmethod
    def _snapshot_builder(builder: Any) -> Dict[str, Any]:
        return {
            key: copy.deepcopy(value)
            for key, value in builder.__dict__.items()
            if key != "conn"
        }

    @staticmethod
    def _restore_builder(builder: Any, state: Mapping[str, Any], conn: sqlite3.Connection) -> None:
        for key in list(builder.__dict__):
            if key != "conn":
                builder.__dict__.pop(key, None)
        builder.__dict__.update(copy.deepcopy(dict(state)))
        builder.conn = conn

    def write_batch(self, conn: sqlite3.Connection, path: str, rows: Sequence[Mapping[str, Any]]) -> int:
        if not rows:
            return 0
        self._bind(path, conn)
        assert self._sparse is not None and self._commands is not None and self._entities is not None
        sparse_state = self._snapshot_builder(self._sparse)
        command_state = self._snapshot_builder(self._commands)
        entity_state = self._snapshot_builder(self._entities)
        session_state = (self._last_ts_ms, self._last_config_hash, self._run_registered)
        written = 0
        try:
            for row in rows:
                sample = extract_system_sample(row)
                if sample is None:
                    continue
                ts_ms = int(sample["ts_ms"])
                sample["run_id"] = self.run_id
                self._ensure_run(conn, sample)
                if insert_system_sample(conn, sample):
                    written += 1
                self._last_ts_ms = ts_ms
                entity_context = self._entities.observe(ts_ms, row, run_id=self.run_id)
                self._sparse.observe(
                    ts_ms, row, self.run_id,
                    controlled_entity_id=entity_context.get("controlled_entity_id"),
                    primary_entity_id=entity_context.get("primary_entity_id"),
                )
                self._commands.observe(
                    ts_ms, self.run_id, row, None,
                    entity_id=entity_context.get("controlled_entity_id"),
                )

                config_hash = str(row.get("_graph_config_hash") or row.get("config_control_hash") or "").strip()
                overlay = row.get("_graph_config_overlay")
                if config_hash and isinstance(overlay, dict) and config_hash != self._last_config_hash:
                    upsert_timeline_entry(
                        conn, ts_ms, config_hash, overlay=overlay,
                        source="runtime_effective", known=True,
                        ensure_schema=False, commit=False,
                    )
                    self._last_config_hash = config_hash

            self._entities.flush_seen()
            if self._last_ts_ms is not None:
                last_cycle = safe_int(rows[-1].get("cycle_id") if rows else None)
                if last_cycle is None and rows:
                    last_cycle = safe_int(rows[-1].get("cycle_index"))
                conn.execute(
                    "UPDATE graph_runs SET end_ms=?,last_cycle_index=COALESCE(?,last_cycle_index) WHERE run_id=?",
                    (self._last_ts_ms, last_cycle, self.run_id),
                )
            conn.execute(
                "INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('last_write_epoch_s',?)",
                (str(time.time()),),
            )
            # WP5 compact evidence belongs to the same transaction as the
            # measurements it describes, so evidence can never get ahead of
            # a rolled-back measurement batch.
            from graph_evidence import record_live_batch_evidence
            record_live_batch_evidence(conn, rows, run_id=self.run_id)
            conn.commit()
            return written
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            self._restore_builder(self._sparse, sparse_state, conn)
            self._restore_builder(self._commands, command_state, conn)
            self._restore_builder(self._entities, entity_state, conn)
            self._last_ts_ms, self._last_config_hash, self._run_registered = session_state
            raise


def open_v3(path: str) -> sqlite3.Connection:
    return connect_graph_core(path)
