# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# ZEC Graph Core V3 foundation.
#
# This module deliberately contains no controller/command side effects. It is
# used by the offline V14 rebuild/backfill path and by tests/benchmarks. The
# existing V2 live writer remains untouched until the later writer cutover WP.

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Sequence, Tuple

GRAPH_CORE_SCHEMA_VERSION = 3
INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1
POWER_SCALE = 10
PERCENT_SCALE = 10

QUALITY_GRID_VALID = 1 << 0
QUALITY_ZENDURE_POWER_VALID = 1 << 1
QUALITY_ZENDURE_SOC_VALID = 1 << 2
QUALITY_PRIMARY_POWER_VALID = 1 << 3
QUALITY_PRIMARY_SOC_VALID = 1 << 4
QUALITY_PV_VALID = 1 << 5
QUALITY_HOUSE_VALID = 1 << 6
QUALITY_CONTROL_GRID_SMOOTHED_VALID = 1 << 7


@dataclass(frozen=True)
class SeriesSpec:
    series_id: str
    source_field: str
    column: str
    unit: str
    scale: int
    aggregation: str  # power | state_numeric | last


SYSTEM_SERIES: Tuple[SeriesSpec, ...] = (
    SeriesSpec("grid_power_w", "grid_power_w", "grid_power_dw", "W", POWER_SCALE, "power"),
    SeriesSpec("raw_grid_power_w", "grid_power_raw_w", "raw_grid_power_dw", "W", POWER_SCALE, "power"),
    SeriesSpec("control_grid_power_w", "control_grid_power_w", "control_grid_power_dw", "W", POWER_SCALE, "power"),
    SeriesSpec("control_grid_power_smoothed_w", "control_grid_power_smoothed_w", "control_grid_power_smoothed_dw", "W", POWER_SCALE, "power"),
    SeriesSpec("pv_power_w", "pv_power_w", "pv_power_dw", "W", POWER_SCALE, "power"),
    SeriesSpec("house_power_w", "house_power_w", "house_power_dw", "W", POWER_SCALE, "power"),
    SeriesSpec("zendure_actual_power_w", "zendure_actual_power_w", "zendure_actual_power_dw", "W", POWER_SCALE, "power"),
    SeriesSpec("zendure_soc_percent", "zendure_soc_percent", "zendure_soc_tenths_percent", "%", PERCENT_SCALE, "state_numeric"),
    SeriesSpec("primary_power_w", "second_battery_power_w", "primary_power_dw", "W", POWER_SCALE, "power"),
    SeriesSpec("primary_soc_percent", "second_battery_soc_percent", "primary_soc_tenths_percent", "%", PERCENT_SCALE, "state_numeric"),
    SeriesSpec("target_raw_w", "target_raw_w", "target_raw_dw", "W", POWER_SCALE, "state_numeric"),
    SeriesSpec("target_limited_w", "target_limited_w", "target_limited_dw", "W", POWER_SCALE, "state_numeric"),
    SeriesSpec("target_filtered_w", "target_filtered_w", "target_filtered_dw", "W", POWER_SCALE, "state_numeric"),
    SeriesSpec("target_step_limited_w", "target_step_limited_w", "target_step_limited_dw", "W", POWER_SCALE, "state_numeric"),
    SeriesSpec("target_final_w", "target_final_w", "target_final_dw", "W", POWER_SCALE, "state_numeric"),
    SeriesSpec("command_desired_target_w", "command_desired_signed_target_w", "command_desired_target_dw", "W", POWER_SCALE, "state_numeric"),
    SeriesSpec("command_readback_target_w", "command_readback_target_w", "command_readback_target_dw", "W", POWER_SCALE, "state_numeric"),
)

SYSTEM_SERIES_BY_ID = {spec.series_id: spec for spec in SYSTEM_SERIES}
SYSTEM_SERIES_BY_COLUMN = {spec.column: spec for spec in SYSTEM_SERIES}


@dataclass(frozen=True)
class EntitySeriesSpec:
    series_id: str
    column: str
    unit: str
    scale: int
    aggregation: str


ENTITY_SERIES: Tuple[EntitySeriesSpec, ...] = (
    EntitySeriesSpec("power_w", "power_dw", "W", POWER_SCALE, "power"),
    EntitySeriesSpec("soc_percent", "soc_tenths_percent", "%", PERCENT_SCALE, "state_numeric"),
    EntitySeriesSpec("target_w", "target_dw", "W", POWER_SCALE, "state_numeric"),
    EntitySeriesSpec("readback_target_w", "readback_target_dw", "W", POWER_SCALE, "state_numeric"),
)
ENTITY_SERIES_BY_ID = {spec.series_id: spec for spec in ENTITY_SERIES}

ENTITY_QUALITY_POWER_VALID = 1 << 0
ENTITY_QUALITY_SOC_VALID = 1 << 1
ENTITY_QUALITY_TARGET_VALID = 1 << 2
ENTITY_QUALITY_READBACK_VALID = 1 << 3

ENTITY_STABLE_CONTROLLED_STORAGE = "storage:controlled"
ENTITY_STABLE_PRIMARY_STORAGE = "storage:primary"
ENTITY_BINDING_SYSTEM_ZENDURE = "SYSTEM_ZENDURE"
ENTITY_BINDING_SYSTEM_PRIMARY = "SYSTEM_PRIMARY"
ENTITY_BINDING_ENTITY_TABLE = "ENTITY_TABLE"

# Entity-facing metrics can be projected from the wide system table when the
# entity is intrinsically singular. This avoids duplicating the same values on
# every sample merely to satisfy a presentation abstraction. Only genuinely
# instance-specific telemetry belongs in measurement_entity_* tables.
SYSTEM_ENTITY_BINDINGS: Dict[str, Dict[str, str]] = {
    ENTITY_BINDING_SYSTEM_ZENDURE: {
        "power_w": "zendure_actual_power_w",
        "soc_percent": "zendure_soc_percent",
        "target_w": "command_desired_target_w",
        "readback_target_w": "command_readback_target_w",
    },
    ENTITY_BINDING_SYSTEM_PRIMARY: {
        "power_w": "primary_power_w",
        "soc_percent": "primary_soc_percent",
    },
}

# Long-term columns are generated from the canonical series contract. Physical
# power keeps sum/count so wider zoom levels can be recomputed without
# averaging averages; step/state-like numeric series intentionally do not keep
# a mean.

def aggregate_columns(spec: SeriesSpec) -> Tuple[str, ...]:
    base = spec.column
    if spec.aggregation == "power":
        return (
            f"{base}_min",
            f"{base}_max",
            f"{base}_sum",
            f"{base}_last",
            f"{base}_count",
        )
    if spec.aggregation == "state_numeric":
        return (
            f"{base}_min",
            f"{base}_max",
            f"{base}_last",
            f"{base}_count",
        )
    return (f"{base}_last", f"{base}_count")


def safe_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except Exception:
        return None
    return result if math.isfinite(result) else None


def safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def bool01(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float)):
        return 1 if value != 0 else 0
    return 1 if str(value).strip().lower() in {"1", "true", "yes", "ja", "on", "valid", "gültig"} else 0


def encode_scaled(value: Any, *, scale: int) -> Optional[int]:
    numeric = safe_float(value)
    if numeric is None:
        return None
    scaled = int(round(numeric * int(scale)))
    if scaled < INT64_MIN or scaled > INT64_MAX:
        return None
    return scaled


def decode_scaled(value: Any, *, scale: int) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(int(value)) / float(scale)
    except Exception:
        return None


def _first_present_value(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row.get(name) not in (None, ""):
            return row.get(name)
    return None


def _quality_flags(row: Mapping[str, Any]) -> int:
    # Measurement V4 and the live in-memory graph row use a few different
    # validity field names.  Normalize them here so the V3 quality mask has
    # identical semantics on both ingestion paths.
    flags = 0
    if bool01(_first_present_value(row, "grid_power_valid")):
        flags |= QUALITY_GRID_VALID
    if bool01(_first_present_value(row, "zendure_actual_power_valid", "actual_zendure_power_valid")):
        flags |= QUALITY_ZENDURE_POWER_VALID
    if bool01(_first_present_value(row, "zendure_soc_valid", "soc_valid")):
        flags |= QUALITY_ZENDURE_SOC_VALID
    primary_valid = _first_present_value(row, "second_battery_valid", "second_battery_data_valid")
    if bool01(_first_present_value(row, "second_battery_power_valid") if "second_battery_power_valid" in row else primary_valid):
        flags |= QUALITY_PRIMARY_POWER_VALID
    if bool01(_first_present_value(row, "second_battery_soc_valid") if "second_battery_soc_valid" in row else primary_valid):
        flags |= QUALITY_PRIMARY_SOC_VALID
    if bool01(_first_present_value(row, "pv_power_valid")):
        flags |= QUALITY_PV_VALID
    if bool01(_first_present_value(row, "house_power_valid")):
        flags |= QUALITY_HOUSE_VALID
    if bool01(_first_present_value(row, "control_grid_power_smoothed_valid", "grid_power_valid")):
        flags |= QUALITY_CONTROL_GRID_SMOOTHED_VALID
    return flags


def _first_value(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row.get(name) not in (None, ""):
            return row.get(name)
    return ""


def _readback_signed_target_value(row: Mapping[str, Any]) -> Optional[float]:
    ac_mode = str(row.get("zendure_command_ac_mode") or "").strip().lower()
    input_limit = safe_float(row.get("zendure_command_input_limit_w"))
    output_limit = safe_float(row.get("zendure_command_output_limit_w"))
    if ac_mode == "input" and input_limit is not None:
        return abs(input_limit)
    if ac_mode == "output" and output_limit is not None:
        return -abs(output_limit)
    if input_limit == 0 and output_limit == 0:
        return 0.0
    return None


def extract_system_sample(row: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    # Measurement V4 and the live in-memory graph row intentionally have a
    # slightly different naming surface. Normalize only the fields needed by
    # Graph Core; the V4 contract itself remains unchanged.
    ts_ms = safe_int(_first_value(row, "measurement_epoch_ms", "epoch_ms"))
    if ts_ms is None:
        epoch_s = safe_float(_first_value(row, "epoch_s", "epoch"))
        if epoch_s is not None:
            ts_ms = int(round(epoch_s * 1000.0))
    if ts_ms is None:
        return None

    is_v4 = "measurement_epoch_ms" in row
    source_aliases: Dict[str, Tuple[str, ...]] = {
        "grid_power_raw_w": ("grid_power_raw_w",) if is_v4 else ("raw_grid_power_w", "raw_grid_power"),
        "control_grid_power_w": ("control_grid_power_w",) if is_v4 else ("grid_power_w", "grid_power"),
        "control_grid_power_smoothed_w": ("control_grid_power_smoothed_w",) if is_v4 else ("grid_power_w", "grid_power"),
        "second_battery_power_w": ("second_battery_power_w",) if is_v4 else ("second_battery_power_w", "sma_battery_display_power", "sma_battery_power"),
        "second_battery_soc_percent": ("second_battery_soc_percent",) if is_v4 else ("second_battery_soc_percent", "sma_battery_soc", "primary_soc_percent"),
        "target_limited_w": ("target_limited_w",) if is_v4 else ("target_after_power_limit_w", "target_after_soc_limits_w"),
        "target_filtered_w": ("target_filtered_w",) if is_v4 else ("target_after_smoothing_w",),
        "target_step_limited_w": ("target_step_limited_w",) if is_v4 else ("target_after_ramp_w",),
        "command_desired_signed_target_w": ("command_desired_signed_target_w",),
    }

    sample: Dict[str, Any] = {
        "ts_ms": ts_ms,
        "cycle_index": safe_int(_first_value(row, "cycle_index", "cycle_id")),
        "quality_flags": _quality_flags(row),
        "sample_monotonic_ns": safe_int(row.get("measurement_monotonic_ns")),
        "run_id": safe_int(row.get("graph_run_id")),
        "command_desired_sequence_id": safe_int(row.get("command_desired_sequence_id")),
        "command_publish_event_id": safe_int(row.get("command_publish_event_id")),
    }
    invalid_fields: List[str] = []
    for spec in SYSTEM_SERIES:
        if spec.series_id == "command_readback_target_w":
            raw_value = _readback_signed_target_value(row)
        else:
            aliases = source_aliases.get(spec.source_field, (spec.source_field,))
            raw_value = _first_value(row, *aliases)
        encoded = encode_scaled(raw_value, scale=spec.scale)
        if raw_value not in (None, "") and encoded is None:
            invalid_fields.append(spec.source_field)
        sample[spec.column] = encoded
    sample["_invalid_numeric_fields"] = tuple(invalid_fields)
    return sample


def _column_sql(columns: Iterable[str]) -> str:
    return ",\n            ".join(f"{column} INTEGER" for column in columns)


def _aggregate_column_sql() -> str:
    cols: List[str] = []
    for spec in SYSTEM_SERIES:
        for column in aggregate_columns(spec):
            suffix = " NOT NULL DEFAULT 0" if column.endswith("_count") else ""
            cols.append(f"{column} INTEGER{suffix}")
    return ",\n            ".join(cols)


def connect_graph_core(path: os.PathLike[str] | str, *, create: bool = True) -> sqlite3.Connection:
    path_s = os.fspath(path)
    parent = os.path.dirname(os.path.abspath(path_s))
    if create:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path_s, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA busy_timeout=30000")
    ensure_graph_core_schema(conn)
    return conn


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: Mapping[str, str]) -> None:
    existing = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, declaration in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")


def ensure_graph_core_schema(conn: sqlite3.Connection) -> None:
    raw_columns = [spec.column for spec in SYSTEM_SERIES]
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS measurement_raw (
            ts_ms INTEGER PRIMARY KEY,
            cycle_index INTEGER,
            quality_flags INTEGER NOT NULL DEFAULT 0,
            sample_monotonic_ns INTEGER,
            run_id INTEGER,
            command_desired_sequence_id INTEGER,
            command_publish_event_id INTEGER,
            {_column_sql(raw_columns)}
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS measurement_1min (
            bucket_start_ms INTEGER PRIMARY KEY,
            sample_count INTEGER NOT NULL,
            first_ts_ms INTEGER NOT NULL,
            last_ts_ms INTEGER NOT NULL,
            quality_or INTEGER NOT NULL DEFAULT 0,
            {_aggregate_column_sql()}
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_entities (
            entity_id INTEGER PRIMARY KEY,
            stable_id TEXT NOT NULL UNIQUE,
            entity_type TEXT NOT NULL,
            identity_kind TEXT NOT NULL DEFAULT 'LOGICAL_ROLE',
            source_identity TEXT,
            storage_binding TEXT NOT NULL DEFAULT 'ENTITY_TABLE',
            label_key TEXT,
            display_name TEXT,
            first_seen_ms INTEGER,
            last_seen_ms INTEGER,
            metadata_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS measurement_entity_raw (
            entity_id INTEGER NOT NULL,
            ts_ms INTEGER NOT NULL,
            run_id INTEGER,
            source_cycle_index INTEGER,
            power_dw INTEGER,
            soc_tenths_percent INTEGER,
            target_dw INTEGER,
            readback_target_dw INTEGER,
            quality_flags INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(entity_id, ts_ms),
            FOREIGN KEY(entity_id) REFERENCES graph_entities(entity_id),
            FOREIGN KEY(run_id) REFERENCES graph_runs(run_id)
        ) WITHOUT ROWID
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS measurement_entity_1min (
            entity_id INTEGER NOT NULL,
            bucket_start_ms INTEGER NOT NULL,
            sample_count INTEGER NOT NULL,
            first_ts_ms INTEGER NOT NULL,
            last_ts_ms INTEGER NOT NULL,
            power_dw_min INTEGER,
            power_dw_max INTEGER,
            power_dw_sum INTEGER,
            power_dw_last INTEGER,
            power_dw_count INTEGER NOT NULL DEFAULT 0,
            soc_tenths_percent_min INTEGER,
            soc_tenths_percent_max INTEGER,
            soc_tenths_percent_last INTEGER,
            soc_tenths_percent_count INTEGER NOT NULL DEFAULT 0,
            target_dw_min INTEGER,
            target_dw_max INTEGER,
            target_dw_last INTEGER,
            target_dw_count INTEGER NOT NULL DEFAULT 0,
            readback_target_dw_min INTEGER,
            readback_target_dw_max INTEGER,
            readback_target_dw_last INTEGER,
            readback_target_dw_count INTEGER NOT NULL DEFAULT 0,
            quality_or INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(entity_id, bucket_start_ms),
            FOREIGN KEY(entity_id) REFERENCES graph_entities(entity_id)
        ) WITHOUT ROWID
        """
    )
    _ensure_columns(conn, "graph_entities", {
        "identity_kind": "TEXT NOT NULL DEFAULT 'LOGICAL_ROLE'",
        "source_identity": "TEXT",
        "storage_binding": "TEXT NOT NULL DEFAULT 'ENTITY_TABLE'",
        "display_name": "TEXT",
    })
    _ensure_columns(conn, "measurement_entity_raw", {
        "run_id": "INTEGER",
        "source_cycle_index": "INTEGER",
    })
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_runs (
            run_id INTEGER PRIMARY KEY,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER,
            start_monotonic_ns INTEGER,
            source TEXT NOT NULL,
            confidence TEXT NOT NULL,
            first_cycle_index INTEGER,
            last_cycle_index INTEGER,
            app_version TEXT,
            build_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_intervals (
            interval_id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL,
            run_id INTEGER,
            entity_id INTEGER,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER,
            value_code TEXT NOT NULL,
            source TEXT NOT NULL,
            quality TEXT NOT NULL DEFAULT 'OBSERVED',
            FOREIGN KEY(run_id) REFERENCES graph_runs(run_id),
            FOREIGN KEY(entity_id) REFERENCES graph_entities(entity_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_intervals_kind_entity_start ON graph_intervals(kind, entity_id, run_id, start_ms)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_command_events (
            event_id INTEGER PRIMARY KEY,
            ts_ms INTEGER NOT NULL,
            monotonic_ns INTEGER,
            run_id INTEGER,
            entity_id INTEGER,
            event_type TEXT NOT NULL,
            source_cycle_index INTEGER,
            desired_sequence_id INTEGER,
            publish_event_id INTEGER,
            requested_target_dw INTEGER,
            desired_target_dw INTEGER,
            smart_mode INTEGER,
            ac_mode TEXT,
            input_limit_dw INTEGER,
            output_limit_dw INTEGER,
            readback_matches_desired INTEGER,
            mismatch_fields TEXT,
            effect_category TEXT,
            effect_reference_dw INTEGER,
            reason TEXT,
            source_file_id INTEGER,
            FOREIGN KEY(run_id) REFERENCES graph_runs(run_id),
            FOREIGN KEY(entity_id) REFERENCES graph_entities(entity_id),
            FOREIGN KEY(source_file_id) REFERENCES graph_source_files(source_file_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_command_events_ts ON graph_command_events(ts_ms)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_command_events_run_publish ON graph_command_events(run_id, publish_event_id)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_topology_timeline (
            topology_id INTEGER PRIMARY KEY,
            effective_from_ms INTEGER NOT NULL,
            entity_id INTEGER,
            entity_type TEXT NOT NULL,
            role TEXT,
            state TEXT NOT NULL,
            unit_count INTEGER,
            source TEXT NOT NULL,
            confidence TEXT NOT NULL DEFAULT 'OBSERVED',
            metadata_json TEXT,
            FOREIGN KEY(entity_id) REFERENCES graph_entities(entity_id)
        )
        """
    )
    _ensure_columns(conn, "graph_topology_timeline", {
        "role": "TEXT",
        "confidence": "TEXT NOT NULL DEFAULT 'OBSERVED'",
    })
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_topology_effective ON graph_topology_timeline(effective_from_ms)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_topology_entity_effective ON graph_topology_timeline(entity_id,effective_from_ms)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_retention_ledger (
            ledger_id INTEGER PRIMARY KEY,
            from_ms INTEGER NOT NULL,
            to_ms INTEGER NOT NULL,
            data_class TEXT NOT NULL,
            entity_id INTEGER,
            action TEXT NOT NULL,
            reason TEXT NOT NULL,
            performed_at_ms INTEGER NOT NULL,
            source_generation TEXT,
            FOREIGN KEY(entity_id) REFERENCES graph_entities(entity_id)
        )
        """
    )
    from graph_evidence import ensure_evidence_schema
    ensure_evidence_schema(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_source_files (
            source_file_id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT,
            first_ms INTEGER,
            last_ms INTEGER,
            rows_seen INTEGER NOT NULL DEFAULT 0,
            rows_imported INTEGER NOT NULL DEFAULT 0,
            trailing_nul_bytes INTEGER NOT NULL DEFAULT 0,
            anomalies_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_series_coverage (
            series_id TEXT NOT NULL,
            from_ms INTEGER NOT NULL,
            to_ms INTEGER NOT NULL,
            source TEXT NOT NULL,
            quality TEXT NOT NULL,
            PRIMARY KEY(series_id, from_ms, to_ms, source)
        ) WITHOUT ROWID
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_entity_series_coverage (
            entity_id INTEGER NOT NULL,
            series_id TEXT NOT NULL,
            from_ms INTEGER NOT NULL,
            to_ms INTEGER NOT NULL,
            source TEXT NOT NULL,
            quality TEXT NOT NULL,
            PRIMARY KEY(entity_id, series_id, source),
            FOREIGN KEY(entity_id) REFERENCES graph_entities(entity_id)
        ) WITHOUT ROWID
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS measurement_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        ) WITHOUT ROWID
        """
    )
    # Reuse the existing V13 sparse config-history schema. This keeps one
    # canonical representation rather than inventing a V14 duplicate.
    from graph_config_timeline import ensure_graph_config_schema
    ensure_graph_config_schema(conn)
    # V13 created a hash index that has no productive query consumer. The V14
    # core keeps the time-ordered INTEGER PRIMARY KEY only; a hash index may be
    # reintroduced later only if a measured query requires it.
    conn.execute("DROP INDEX IF EXISTS idx_graph_config_timeline_hash")
    conn.execute(
        "INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('schema_version',?)",
        (str(GRAPH_CORE_SCHEMA_VERSION),),
    )
    conn.execute(
        "INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('storage_encoding','scaled_integer_v1')"
    )
    conn.commit()


def series_catalog() -> List[Dict[str, Any]]:
    return [
        {
            "series_id": spec.series_id,
            "source_field": spec.source_field,
            "storage_column": spec.column,
            "unit": spec.unit,
            "storage_encoding": "INTEGER",
            "storage_scale": spec.scale,
            "aggregation": spec.aggregation,
        }
        for spec in SYSTEM_SERIES
    ]


def entity_series_catalog() -> List[Dict[str, Any]]:
    return [
        {
            "series_id": spec.series_id,
            "unit": spec.unit,
            "storage_encoding": "INTEGER",
            "storage_scale": int(spec.scale),
            "aggregation": spec.aggregation,
        }
        for spec in ENTITY_SERIES
    ]


def _compact_json(value: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not value:
        return None
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def ensure_graph_entity(
    conn: sqlite3.Connection,
    *,
    stable_id: str,
    entity_type: str,
    ts_ms: int,
    identity_kind: str = "LOGICAL_ROLE",
    source_identity: Optional[str] = None,
    storage_binding: str = ENTITY_BINDING_ENTITY_TABLE,
    label_key: Optional[str] = None,
    display_name: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> int:
    """Resolve a stable external entity id to a compact integer entity_id.

    Identity-bearing fields are immutable once persisted. Presentation metadata
    such as display_name may evolve without changing identity.
    """
    sid = str(stable_id or "").strip()
    etype = str(entity_type or "").strip().upper()
    ikind = str(identity_kind or "LOGICAL_ROLE").strip().upper()
    binding = str(storage_binding or ENTITY_BINDING_ENTITY_TABLE).strip().upper()
    source_id = str(source_identity or "").strip() or None
    label = str(label_key or "").strip() or None
    display = str(display_name or "").strip() or None
    if not sid or not etype:
        raise ValueError("ENTITY_IDENTITY_INCOMPLETE")
    existing = conn.execute(
        "SELECT entity_id,entity_type,identity_kind,source_identity,storage_binding,first_seen_ms,last_seen_ms "
        "FROM graph_entities WHERE stable_id=?",
        (sid,),
    ).fetchone()
    if existing is None:
        cur = conn.execute(
            """
            INSERT INTO graph_entities(
                stable_id,entity_type,identity_kind,source_identity,storage_binding,
                label_key,display_name,first_seen_ms,last_seen_ms,metadata_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (sid, etype, ikind, source_id, binding, label, display, int(ts_ms), int(ts_ms), _compact_json(metadata)),
        )
        return int(cur.lastrowid)

    entity_id = int(existing[0])
    persisted = {
        "entity_type": str(existing[1] or "").upper(),
        "identity_kind": str(existing[2] or "LOGICAL_ROLE").upper(),
        "source_identity": str(existing[3] or "").strip() or None,
        "storage_binding": str(existing[4] or ENTITY_BINDING_ENTITY_TABLE).upper(),
    }
    desired = {
        "entity_type": etype,
        "identity_kind": ikind,
        "source_identity": source_id,
        "storage_binding": binding,
    }
    for key in ("entity_type", "identity_kind", "storage_binding"):
        if persisted[key] != desired[key]:
            raise RuntimeError(f"ENTITY_IDENTITY_CONFLICT:{sid}:{key}")
    if persisted["source_identity"] and source_id and persisted["source_identity"] != source_id:
        raise RuntimeError(f"ENTITY_IDENTITY_CONFLICT:{sid}:source_identity")
    first_seen = int(existing[5]) if existing[5] is not None else int(ts_ms)
    last_seen = int(existing[6]) if existing[6] is not None else int(ts_ms)
    conn.execute(
        """
        UPDATE graph_entities
           SET source_identity=COALESCE(source_identity,?),
               label_key=COALESCE(?,label_key),
               display_name=COALESCE(?,display_name),
               first_seen_ms=?,last_seen_ms=?,
               metadata_json=COALESCE(?,metadata_json)
         WHERE entity_id=?
        """,
        (
            source_id, label, display, min(first_seen, int(ts_ms)), max(last_seen, int(ts_ms)),
            _compact_json(metadata), entity_id,
        ),
    )
    return entity_id


def _entity_aggregate_update(current: MutableMapping[str, Any], spec: EntitySeriesSpec, value: Optional[int]) -> None:
    if value is None:
        return
    base = spec.column
    count_key = f"{base}_count"
    current[count_key] = int(current.get(count_key) or 0) + 1
    current[f"{base}_last"] = int(value)
    if spec.aggregation in {"power", "state_numeric"}:
        min_key = f"{base}_min"
        max_key = f"{base}_max"
        current[min_key] = int(value) if current.get(min_key) is None else min(int(current[min_key]), int(value))
        current[max_key] = int(value) if current.get(max_key) is None else max(int(current[max_key]), int(value))
    if spec.aggregation == "power":
        sum_key = f"{base}_sum"
        candidate = int(current.get(sum_key) or 0) + int(value)
        if candidate < INT64_MIN or candidate > INT64_MAX:
            raise OverflowError(f"INT64 overflow in entity minute aggregate {sum_key}")
        current[sum_key] = candidate


def _upsert_entity_minute(conn: sqlite3.Connection, entity_id: int, sample: Mapping[str, Any]) -> None:
    bucket = int(sample["ts_ms"] // 60000) * 60000
    conn.row_factory = sqlite3.Row
    old_row = conn.execute(
        "SELECT * FROM measurement_entity_1min WHERE entity_id=? AND bucket_start_ms=?",
        (int(entity_id), bucket),
    ).fetchone()
    data: Dict[str, Any] = dict(old_row) if old_row is not None else {
        "entity_id": int(entity_id),
        "bucket_start_ms": bucket,
        "sample_count": 0,
        "first_ts_ms": int(sample["ts_ms"]),
        "last_ts_ms": int(sample["ts_ms"]),
        "quality_or": 0,
    }
    data["sample_count"] = int(data.get("sample_count") or 0) + 1
    data["first_ts_ms"] = min(int(data.get("first_ts_ms") or sample["ts_ms"]), int(sample["ts_ms"]))
    data["last_ts_ms"] = max(int(data.get("last_ts_ms") or sample["ts_ms"]), int(sample["ts_ms"]))
    data["quality_or"] = int(data.get("quality_or") or 0) | int(sample.get("quality_flags") or 0)
    for spec in ENTITY_SERIES:
        _entity_aggregate_update(data, spec, sample.get(spec.column))
    columns = list(data.keys())
    update = ",".join(f"{column}=excluded.{column}" for column in columns if column not in {"entity_id", "bucket_start_ms"})
    conn.execute(
        f"INSERT INTO measurement_entity_1min({','.join(columns)}) VALUES({','.join('?' for _ in columns)}) "
        f"ON CONFLICT(entity_id,bucket_start_ms) DO UPDATE SET {update}",
        tuple(data[column] for column in columns),
    )


def _update_entity_series_coverage(conn: sqlite3.Connection, entity_id: int, sample: Mapping[str, Any], *, source: str) -> None:
    for spec in ENTITY_SERIES:
        if sample.get(spec.column) is None:
            continue
        ts_ms = int(sample["ts_ms"])
        conn.execute(
            """
            INSERT INTO graph_entity_series_coverage(entity_id,series_id,from_ms,to_ms,source,quality)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(entity_id,series_id,source) DO UPDATE SET
                from_ms=MIN(from_ms,excluded.from_ms),
                to_ms=MAX(to_ms,excluded.to_ms),
                quality=excluded.quality
            """,
            (int(entity_id), spec.series_id, ts_ms, ts_ms, str(source), "OBSERVED_NON_NULL_SPAN"),
        )


def insert_entity_sample(
    conn: sqlite3.Connection,
    entity_id: int,
    sample: Mapping[str, Any],
    *,
    source: str,
) -> bool:
    columns = [
        "entity_id", "ts_ms", "run_id", "source_cycle_index", "power_dw", "soc_tenths_percent",
        "target_dw", "readback_target_dw", "quality_flags",
    ]
    values = [int(entity_id)] + [sample.get(column) for column in columns[1:]]
    before = conn.total_changes
    conn.execute(
        f"INSERT OR IGNORE INTO measurement_entity_raw({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
        values,
    )
    inserted = conn.total_changes > before
    if inserted:
        _upsert_entity_minute(conn, int(entity_id), sample)
        _update_entity_series_coverage(conn, int(entity_id), sample, source=source)
    return inserted


def _parse_json_list_with_status(value: Any) -> Tuple[List[Mapping[str, Any]], bool]:
    """Return mapping items plus whether the source was an explicit valid list.

    The distinction matters for topology: an explicit authoritative empty list
    together with unit_count=0 can prove that formerly present physical units
    are now ABSENT. A missing or malformed field cannot prove absence.
    """
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)], all(isinstance(item, Mapping) for item in value)
    if not isinstance(value, str) or not value.strip():
        return [], False
    try:
        decoded = json.loads(value)
    except Exception:
        return [], False
    if not isinstance(decoded, list):
        return [], False
    return [item for item in decoded if isinstance(item, Mapping)], all(isinstance(item, Mapping) for item in decoded)


def _parse_json_list(value: Any) -> List[Mapping[str, Any]]:
    return _parse_json_list_with_status(value)[0]


def _unit_identity(unit: Mapping[str, Any]) -> Optional[Tuple[str, str]]:
    for key, kind in (("device_id", "DEVICE_ID"), ("serial", "SERIAL"), ("serial_number", "SERIAL"), ("unit_id", "UNIT_ID")):
        raw = str(unit.get(key) or "").strip()
        if not raw:
            continue
        if raw.lower() in {"primary", "aggregate", "system", "default"}:
            continue
        return kind, raw
    return None


def _stable_physical_unit_id(source_identity: str) -> str:
    digest = hashlib.sha256(str(source_identity).encode("utf-8")).hexdigest()[:16]
    return f"zendure-unit:{digest}"


def _entity_sample_from_unit(ts_ms: int, unit: Mapping[str, Any], *, run_id: Optional[int], cycle_index: Optional[int]) -> Dict[str, Any]:
    power_raw = _first_value(unit, "actual_power_w", "power_w", "signed_power_w")
    soc_raw = _first_value(unit, "soc_percent", "soc")
    target_raw = _first_value(unit, "target_w", "desired_target_w")
    readback_raw = _first_value(unit, "readback_target_w", "command_readback_target_w")
    quality = 0
    if bool01(unit.get("power_valid")):
        quality |= ENTITY_QUALITY_POWER_VALID
    if bool01(unit.get("soc_valid")):
        quality |= ENTITY_QUALITY_SOC_VALID
    if bool01(unit.get("target_valid")):
        quality |= ENTITY_QUALITY_TARGET_VALID
    if bool01(unit.get("readback_valid")):
        quality |= ENTITY_QUALITY_READBACK_VALID
    return {
        "ts_ms": int(ts_ms),
        "run_id": safe_int(run_id),
        "source_cycle_index": safe_int(cycle_index),
        "power_dw": encode_scaled(power_raw, scale=POWER_SCALE),
        "soc_tenths_percent": encode_scaled(soc_raw, scale=PERCENT_SCALE),
        "target_dw": encode_scaled(target_raw, scale=POWER_SCALE),
        "readback_target_dw": encode_scaled(readback_raw, scale=POWER_SCALE),
        "quality_flags": quality,
    }


class EntityPersistenceBuilder:
    """Instance-aware identity/topology persistence without inventing devices.

    The two singular logical storage roles are projected from measurement_raw
    and therefore cost no duplicate high-frequency rows. measurement_entity_*
    is used only when an authoritative per-unit list exposes real, separately
    identifiable telemetry.
    """

    def __init__(self, conn: sqlite3.Connection, *, source: str = "MEASUREMENT_V4") -> None:
        self.conn = conn
        self.source = str(source)
        self.entity_cache: Dict[str, int] = {}
        self.entity_identity_cache: Dict[str, Tuple[str, str, Optional[str], str]] = {}
        self.entity_presentation_cache: Dict[str, Tuple[Optional[str], Optional[str], Optional[str]]] = {}
        self.entity_last_seen_pending: Dict[int, int] = {}
        self.topology_cache: Dict[Tuple[int, str], Tuple[str, Optional[int], str, Optional[str]]] = {}
        self._known_physical_ids: Optional[set[int]] = None

    @staticmethod
    def _identity_signature(kwargs: Mapping[str, Any]) -> Tuple[str, str, Optional[str], str]:
        return (
            str(kwargs.get("entity_type") or "").strip().upper(),
            str(kwargs.get("identity_kind") or "LOGICAL_ROLE").strip().upper(),
            str(kwargs.get("source_identity") or "").strip() or None,
            str(kwargs.get("storage_binding") or ENTITY_BINDING_ENTITY_TABLE).strip().upper(),
        )

    @staticmethod
    def _presentation_signature(kwargs: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        label = str(kwargs.get("label_key") or "").strip() or None
        display = str(kwargs.get("display_name") or "").strip() or None
        metadata = _compact_json(kwargs.get("metadata"))
        return label, display, metadata

    def _ensure_cached(self, **kwargs: Any) -> int:
        sid = str(kwargs["stable_id"])
        ts_ms = int(kwargs["ts_ms"])
        identity = self._identity_signature(kwargs)
        presentation = self._presentation_signature(kwargs)
        entity_id = self.entity_cache.get(sid)
        if entity_id is None:
            entity_id = ensure_graph_entity(self.conn, **kwargs)
            self.entity_cache[sid] = int(entity_id)
            self.entity_identity_cache[sid] = identity
            self.entity_presentation_cache[sid] = presentation
        else:
            if self.entity_identity_cache.get(sid) != identity:
                # Let the canonical resolver produce the fail-closed conflict
                # and validate against the persisted row as well.
                ensure_graph_entity(self.conn, **kwargs)
                raise RuntimeError(f"ENTITY_IDENTITY_CONFLICT:{sid}")
            if self.entity_presentation_cache.get(sid) != presentation:
                ensure_graph_entity(self.conn, **kwargs)
                self.entity_presentation_cache[sid] = presentation
        self.entity_last_seen_pending[int(entity_id)] = max(
            ts_ms, int(self.entity_last_seen_pending.get(int(entity_id), ts_ms))
        )
        return int(entity_id)

    def flush_seen(self) -> None:
        """Persist exact last-seen timestamps once per transaction/batch.

        Avoiding one graph_entities UPDATE per sample materially reduces write
        amplification while retaining exact committed entity boundaries.
        """
        if not self.entity_last_seen_pending:
            return
        self.conn.executemany(
            "UPDATE graph_entities SET last_seen_ms=MAX(COALESCE(last_seen_ms,?),?) WHERE entity_id=?",
            [(ts_ms, ts_ms, entity_id) for entity_id, ts_ms in self.entity_last_seen_pending.items()],
        )
        self.entity_last_seen_pending.clear()

    def _last_topology_signature(self, entity_id: int, role: str) -> Optional[Tuple[str, Optional[int], str, Optional[str]]]:
        key = (int(entity_id), str(role))
        if key in self.topology_cache:
            return self.topology_cache[key]
        row = self.conn.execute(
            "SELECT state,unit_count,confidence,metadata_json FROM graph_topology_timeline "
            "WHERE entity_id=? AND COALESCE(role,'')=? "
            "ORDER BY effective_from_ms DESC,topology_id DESC LIMIT 1",
            (int(entity_id), str(role)),
        ).fetchone()
        signature = None if row is None else (
            str(row[0]), safe_int(row[1]), str(row[2] or "OBSERVED"), str(row[3]) if row[3] is not None else None,
        )
        if signature is not None:
            self.topology_cache[key] = signature
        return signature

    def _topology(self, ts_ms: int, entity_id: int, entity_type: str, role: str, state: str, *, unit_count: Optional[int] = None, confidence: str = "OBSERVED", metadata: Optional[Mapping[str, Any]] = None) -> None:
        normalized = str(state or "").strip().upper()
        if normalized not in {"PRESENT", "ABSENT", "NOT_APPLICABLE"}:
            raise ValueError(f"INVALID_TOPOLOGY_STATE:{normalized}")
        normalized_count = safe_int(unit_count)
        normalized_confidence = str(confidence or "OBSERVED")
        metadata_json = _compact_json(metadata)
        signature = (normalized, normalized_count, normalized_confidence, metadata_json)
        previous = self._last_topology_signature(entity_id, role)
        if previous == signature:
            return
        self.conn.execute(
            """
            INSERT INTO graph_topology_timeline(
                effective_from_ms,entity_id,entity_type,role,state,unit_count,source,confidence,metadata_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                int(ts_ms), int(entity_id), str(entity_type), str(role), normalized,
                normalized_count, self.source, normalized_confidence, metadata_json,
            ),
        )
        self.topology_cache[(int(entity_id), str(role))] = signature

    def _physical_present_ids(self) -> set[int]:
        if self._known_physical_ids is not None:
            return set(self._known_physical_ids)
        rows = self.conn.execute(
            """
            SELECT e.entity_id
              FROM graph_entities AS e
             WHERE e.entity_type='ZENDURE_UNIT'
               AND EXISTS(
                    SELECT 1 FROM graph_topology_timeline AS t
                     WHERE t.entity_id=e.entity_id AND t.role='CONTROLLED_STORAGE_MEMBER'
                       AND t.state='PRESENT'
                       AND t.topology_id=(
                           SELECT t2.topology_id FROM graph_topology_timeline AS t2
                            WHERE t2.entity_id=e.entity_id AND t2.role='CONTROLLED_STORAGE_MEMBER'
                            ORDER BY t2.effective_from_ms DESC,t2.topology_id DESC LIMIT 1
                       )
               )
            """
        ).fetchall()
        self._known_physical_ids = {int(row[0]) for row in rows}
        return set(self._known_physical_ids)

    def observe(self, ts_ms: int, row: Mapping[str, Any], *, run_id: Optional[int] = None) -> Dict[str, Any]:
        ts_ms = int(ts_ms)
        config_meta = row.get("_graph_entity_config") if isinstance(row.get("_graph_entity_config"), Mapping) else {}
        unit_count = safe_int(row.get("zendure_unit_count"))
        zendure_device_id = str(config_meta.get("zendure_device_id") or "").strip()
        controlled_metadata: Dict[str, Any] = {"source_kind": "SYSTEM_AGGREGATE"}
        if zendure_device_id:
            controlled_metadata["configured_device_id"] = zendure_device_id
        controlled = self._ensure_cached(
            stable_id=ENTITY_STABLE_CONTROLLED_STORAGE,
            entity_type="ZENDURE_STORAGE",
            ts_ms=ts_ms,
            identity_kind="LOGICAL_ROLE",
            source_identity=None,
            storage_binding=ENTITY_BINDING_SYSTEM_ZENDURE,
            label_key="graph.entity.controlled_storage",
            display_name="Zendure",
            metadata=controlled_metadata,
        )
        controlled_has_data = any(row.get(name) not in (None, "") for name in ("zendure_actual_power_w", "zendure_soc_percent"))
        controlled_state = "PRESENT" if (unit_count is not None and unit_count > 0) or controlled_has_data else "NOT_APPLICABLE"
        self._topology(ts_ms, controlled, "ZENDURE_STORAGE", "CONTROLLED_STORAGE", controlled_state, unit_count=unit_count)

        primary_display = str(config_meta.get("primary_display_name") or "").strip() or None
        primary_source_profile = str(config_meta.get("primary_source_profile") or row.get("second_battery_source") or "").strip()
        primary = self._ensure_cached(
            stable_id=ENTITY_STABLE_PRIMARY_STORAGE,
            entity_type="PRIMARY_STORAGE",
            ts_ms=ts_ms,
            identity_kind="LOGICAL_ROLE",
            source_identity=None,
            storage_binding=ENTITY_BINDING_SYSTEM_PRIMARY,
            label_key="graph.entity.primary_storage",
            display_name=primary_display,
            metadata={"source_profile": primary_source_profile} if primary_source_profile else None,
        )
        integration_flag = config_meta.get("primary_integration_enabled")
        primary_has_data = any(row.get(name) not in (None, "") for name in ("second_battery_power_w", "second_battery_soc_percent"))
        source_disabled = primary_source_profile.strip().upper() in {"", "NONE", "DISABLED"}
        if integration_flag is False:
            primary_state = "NOT_APPLICABLE"
        elif primary_has_data or not source_disabled:
            primary_state = "PRESENT"
        else:
            primary_state = "NOT_APPLICABLE"
        self._topology(
            ts_ms, primary, "PRIMARY_STORAGE", "PRIMARY_STORAGE", primary_state,
            confidence="OBSERVED" if primary_has_data else "CONFIGURED",
            metadata={"source_profile": primary_source_profile} if primary_source_profile else None,
        )

        units, explicit_valid_unit_list = _parse_json_list_with_status(row.get("zendure_units_json"))
        identities: List[Tuple[Mapping[str, Any], Tuple[str, str]]] = []
        for unit in units:
            identity = _unit_identity(unit)
            if identity is not None:
                identities.append((unit, identity))
        identity_keys = {(kind, source_identity) for _unit, (kind, source_identity) in identities}
        authoritative = (
            explicit_valid_unit_list
            and unit_count is not None
            and int(unit_count) == len(units) == len(identities) == len(identity_keys)
        )
        current_ids: set[int] = set()
        entity_rows_written = 0
        if authoritative:
            for unit, (identity_kind, source_identity) in identities:
                stable_id = _stable_physical_unit_id(source_identity)
                display = str(unit.get("display_name") or unit.get("name") or "").strip() or None
                entity_id = self._ensure_cached(
                    stable_id=stable_id,
                    entity_type="ZENDURE_UNIT",
                    ts_ms=ts_ms,
                    identity_kind=identity_kind,
                    source_identity=source_identity,
                    storage_binding=ENTITY_BINDING_ENTITY_TABLE,
                    label_key="graph.entity.zendure_unit",
                    display_name=display,
                    metadata={"parent": ENTITY_STABLE_CONTROLLED_STORAGE},
                )
                current_ids.add(entity_id)
                self._topology(
                    ts_ms, entity_id, "ZENDURE_UNIT", "CONTROLLED_STORAGE_MEMBER", "PRESENT",
                    unit_count=unit_count, metadata={"parent": ENTITY_STABLE_CONTROLLED_STORAGE},
                )
                entity_sample = _entity_sample_from_unit(
                    ts_ms, unit, run_id=run_id,
                    cycle_index=safe_int(_first_value(row, "cycle_index", "cycle_id")),
                )
                if any(entity_sample.get(spec.column) is not None for spec in ENTITY_SERIES):
                    if insert_entity_sample(self.conn, entity_id, entity_sample, source=self.source):
                        entity_rows_written += 1
            previous_ids = self._physical_present_ids()
            for entity_id in sorted(previous_ids - current_ids):
                row_meta = self.conn.execute("SELECT entity_type FROM graph_entities WHERE entity_id=?", (entity_id,)).fetchone()
                entity_type = str(row_meta[0]) if row_meta else "ZENDURE_UNIT"
                self._topology(ts_ms, entity_id, entity_type, "CONTROLLED_STORAGE_MEMBER", "ABSENT", unit_count=unit_count)
            self._known_physical_ids = set(current_ids)

        return {
            "controlled_entity_id": controlled,
            "primary_entity_id": primary,
            "physical_unit_count": len(current_ids) if authoritative else 0,
            "authoritative_unit_list": authoritative,
            "entity_rows_written": entity_rows_written,
        }


def _aggregate_update(current: MutableMapping[str, Any], spec: SeriesSpec, value: Optional[int]) -> None:
    if value is None:
        return
    base = spec.column
    count_key = f"{base}_count"
    current[count_key] = int(current.get(count_key) or 0) + 1
    current[f"{base}_last"] = int(value)
    if spec.aggregation in {"power", "state_numeric"}:
        min_key = f"{base}_min"
        max_key = f"{base}_max"
        current[min_key] = int(value) if current.get(min_key) is None else min(int(current[min_key]), int(value))
        current[max_key] = int(value) if current.get(max_key) is None else max(int(current[max_key]), int(value))
    if spec.aggregation == "power":
        sum_key = f"{base}_sum"
        candidate = int(current.get(sum_key) or 0) + int(value)
        if candidate < INT64_MIN or candidate > INT64_MAX:
            raise OverflowError(f"INT64 overflow in minute aggregate {sum_key}")
        current[sum_key] = candidate


def _upsert_minute(conn: sqlite3.Connection, sample: Mapping[str, Any]) -> None:
    bucket = int(sample["ts_ms"] // 60000) * 60000
    conn.row_factory = sqlite3.Row
    old_row = conn.execute("SELECT * FROM measurement_1min WHERE bucket_start_ms=?", (bucket,)).fetchone()
    data: Dict[str, Any] = dict(old_row) if old_row is not None else {
        "bucket_start_ms": bucket,
        "sample_count": 0,
        "first_ts_ms": int(sample["ts_ms"]),
        "last_ts_ms": int(sample["ts_ms"]),
        "quality_or": 0,
    }
    data["sample_count"] = int(data.get("sample_count") or 0) + 1
    data["first_ts_ms"] = min(int(data.get("first_ts_ms") or sample["ts_ms"]), int(sample["ts_ms"]))
    data["last_ts_ms"] = max(int(data.get("last_ts_ms") or sample["ts_ms"]), int(sample["ts_ms"]))
    data["quality_or"] = int(data.get("quality_or") or 0) | int(sample.get("quality_flags") or 0)
    for spec in SYSTEM_SERIES:
        _aggregate_update(data, spec, sample.get(spec.column))
    columns = list(data.keys())
    placeholders = ",".join("?" for _ in columns)
    update = ",".join(f"{column}=excluded.{column}" for column in columns if column != "bucket_start_ms")
    conn.execute(
        f"INSERT INTO measurement_1min({','.join(columns)}) VALUES({placeholders}) "
        f"ON CONFLICT(bucket_start_ms) DO UPDATE SET {update}",
        tuple(data[column] for column in columns),
    )


def insert_system_sample(conn: sqlite3.Connection, sample: Mapping[str, Any]) -> bool:
    columns = [
        "ts_ms", "cycle_index", "quality_flags", "sample_monotonic_ns", "run_id",
        "command_desired_sequence_id", "command_publish_event_id",
    ] + [spec.column for spec in SYSTEM_SERIES]
    values = [sample.get(column) for column in columns]
    before = conn.total_changes
    conn.execute(
        f"INSERT OR IGNORE INTO measurement_raw({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
        values,
    )
    inserted = conn.total_changes > before
    if inserted:
        _upsert_minute(conn, sample)
    return inserted


def _readback_signed_target(row: Mapping[str, Any]) -> Optional[int]:
    ac_mode = str(row.get("zendure_command_ac_mode") or "").strip().lower()
    input_limit = safe_float(row.get("zendure_command_input_limit_w"))
    output_limit = safe_float(row.get("zendure_command_output_limit_w"))
    if ac_mode == "input" and input_limit is not None:
        return encode_scaled(input_limit, scale=POWER_SCALE)
    if ac_mode == "output" and output_limit is not None:
        encoded = encode_scaled(output_limit, scale=POWER_SCALE)
        return -encoded if encoded is not None else None
    if input_limit == 0 and output_limit == 0:
        return 0
    return None


class SparseStateBuilder:
    MUTEX_FIELDS: Tuple[Tuple[str, str], ...] = (
        ("OPERATING_MODE", "operating_mode"),
        ("CONTROL_INTENT", "control_intent"),
        ("CONTROL_REASON", "target_final_reason"),
        ("POWER_OBSERVATION_DIRECTION", "zendure_power_observation_direction"),
        ("POWER_OBSERVATION_CONFIDENCE", "zendure_power_observation_confidence"),
        ("COMMAND_LIFECYCLE", "command_lifecycle_state"),
        ("COMMAND_EFFECT", "command_effect_category"),
        ("COMMAND_DESIRED_INTENT", "command_desired_intent"),
        ("COMMAND_READBACK_SMART_MODE", "zendure_command_smart_mode"),
        ("COMMAND_READBACK_AC_MODE", "zendure_command_ac_mode"),
        ("COMMAND_READBACK_MATCH", "command_readback_matches_desired"),
        ("COMMAND_READBACK_MISMATCH_FIELDS", "command_readback_mismatch_fields"),
        ("GRID_SOURCE", "grid_power_source"),
        ("ZENDURE_POWER_SOURCE", "zendure_actual_power_source"),
        ("ZENDURE_SOC_SOURCE", "zendure_soc_source"),
        ("PRIMARY_SOURCE", "second_battery_source"),
    )
    QUALITY_BOOL_FIELDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
        ("GRID_DATA", ("grid_power_valid",)),
        ("ZENDURE_POWER_DATA", ("zendure_actual_power_valid", "actual_zendure_power_valid")),
        ("ZENDURE_SOC_DATA", ("zendure_soc_valid", "soc_valid")),
        ("PRIMARY_POWER_DATA", ("second_battery_power_valid", "second_battery_valid", "second_battery_data_valid")),
        ("PRIMARY_SOC_DATA", ("second_battery_soc_valid", "second_battery_valid", "second_battery_data_valid")),
        ("PV_DATA", ("pv_power_valid",)),
        ("HOUSE_DATA", ("house_power_valid",)),
    )
    LIMITER_FIELDS: Tuple[Tuple[str, str], ...] = (
        ("DEADBAND", "target_changed_by_deadband"),
        ("SMOOTHING", "target_changed_by_smoothing"),
        ("STEP_LIMIT", "target_changed_by_step_limit"),
        ("SOC_LIMIT", "target_changed_by_soc_limit"),
        ("POWER_LIMIT", "target_changed_by_power_limit"),
        ("CROSS_CHARGE", "target_changed_by_cross_charge"),
        ("MODE", "target_changed_by_mode"),
        ("SAFE_STATE", "target_changed_by_safe_state"),
    )

    def __init__(self, conn: sqlite3.Connection, *, source: str = "MEASUREMENT_V4") -> None:
        self.conn = conn
        self.source = source
        self.open_mutex: Dict[Tuple[str, Optional[int]], Tuple[int, str, Optional[int], int]] = {}
        self.open_limiters: Dict[str, Tuple[int, Optional[int], int]] = {}
        self.last_ts: Optional[int] = None
        self.current_run_id: Optional[int] = None

    def _open_interval(
        self, kind: str, start_ms: int, value: str, run_id: Optional[int], entity_id: Optional[int] = None
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO graph_intervals(kind,run_id,entity_id,start_ms,end_ms,value_code,source,quality) VALUES(?,?,?,?,?,?,?,?)",
            (kind, run_id, entity_id, int(start_ms), None, value, self.source, "OBSERVED"),
        )
        return int(cur.lastrowid)

    def _finish_interval(self, interval_id: int, end_ms: Optional[int]) -> None:
        if end_ms is None:
            return
        self.conn.execute(
            "UPDATE graph_intervals SET end_ms=? WHERE interval_id=? AND (end_ms IS NULL OR end_ms>?)",
            (int(end_ms), int(interval_id), int(end_ms)),
        )

    def _close_open(self, end_ms: Optional[int]) -> None:
        if end_ms is not None:
            for _key, (_start, _value, _run_id, interval_id) in list(self.open_mutex.items()):
                self._finish_interval(interval_id, end_ms)
            for _limiter, (_start, _run_id, interval_id) in list(self.open_limiters.items()):
                self._finish_interval(interval_id, end_ms)
        self.open_mutex.clear()
        self.open_limiters.clear()

    @staticmethod
    def _entity_for_kind(kind: str, controlled_entity_id: Optional[int], primary_entity_id: Optional[int]) -> Optional[int]:
        if kind.startswith("COMMAND_") or kind.startswith("ZENDURE_") or kind.startswith("POWER_OBSERVATION_"):
            return controlled_entity_id
        if kind.startswith("PRIMARY_"):
            return primary_entity_id
        return None

    def observe(
        self,
        ts_ms: int,
        row: Mapping[str, Any],
        run_id: Optional[int] = None,
        *,
        controlled_entity_id: Optional[int] = None,
        primary_entity_id: Optional[int] = None,
    ) -> None:
        if self.last_ts is not None and ts_ms < self.last_ts:
            return
        if self.current_run_id is not None and run_id is not None and run_id != self.current_run_id:
            end = (self.last_ts + 1) if self.last_ts is not None else ts_ms
            self._close_open(end)
        self.current_run_id = run_id if run_id is not None else self.current_run_id
        self.last_ts = ts_ms
        active_run = self.current_run_id

        for kind, field in self.MUTEX_FIELDS:
            value = str(row.get(field) or "").strip()
            entity_id = self._entity_for_kind(kind, controlled_entity_id, primary_entity_id)
            key = (kind, entity_id)
            previous = self.open_mutex.get(key)
            if previous is None:
                if value:
                    iid = self._open_interval(kind, ts_ms, value, active_run, entity_id)
                    self.open_mutex[key] = (ts_ms, value, active_run, iid)
            elif previous[1] != value:
                self._finish_interval(previous[3], ts_ms)
                if value:
                    iid = self._open_interval(kind, ts_ms, value, active_run, entity_id)
                    self.open_mutex[key] = (ts_ms, value, active_run, iid)
                else:
                    self.open_mutex.pop(key, None)

        for kind, fields in self.QUALITY_BOOL_FIELDS:
            raw_value = _first_present_value(row, *fields)
            if raw_value is None:
                continue
            value = "VALID" if bool01(raw_value) else "INVALID"
            entity_id = self._entity_for_kind(kind, controlled_entity_id, primary_entity_id)
            key = (kind, entity_id)
            previous = self.open_mutex.get(key)
            if previous is None:
                iid = self._open_interval(kind, ts_ms, value, active_run, entity_id)
                self.open_mutex[key] = (ts_ms, value, active_run, iid)
            elif previous[1] != value:
                self._finish_interval(previous[3], ts_ms)
                iid = self._open_interval(kind, ts_ms, value, active_run, entity_id)
                self.open_mutex[key] = (ts_ms, value, active_run, iid)

        harvest_limiter = str(row.get("harvest_limiter_reason") or "").strip()
        active_limiters = {name for name, field in self.LIMITER_FIELDS if bool01(row.get(field))}
        if harvest_limiter:
            active_limiters.add(f"HARVEST:{harvest_limiter}")
        for limiter in sorted(set(self.open_limiters) - active_limiters):
            _start, _run, iid = self.open_limiters.pop(limiter)
            self._finish_interval(iid, ts_ms)
        for limiter in sorted(active_limiters - set(self.open_limiters)):
            iid = self._open_interval("LIMITER", ts_ms, limiter, active_run)
            self.open_limiters[limiter] = (ts_ms, active_run, iid)

    def close(self, end_ms: Optional[int]) -> None:
        end = int(end_ms) + 1 if end_ms is not None else None
        self._close_open(end)


class RunBuilder:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.run_id: Optional[int] = None
        self.run_start_ms: Optional[int] = None
        self.first_cycle: Optional[int] = None
        self.last_cycle: Optional[int] = None
        self.last_ts: Optional[int] = None

    def _finish_current(self) -> None:
        if self.run_id is None or self.last_ts is None:
            return
        self.conn.execute(
            "UPDATE graph_runs SET end_ms=?,last_cycle_index=? WHERE run_id=?",
            (self.last_ts, self.last_cycle, self.run_id),
        )

    def observe(self, ts_ms: int, cycle_index: Optional[int]) -> int:
        new_run = self.run_id is None
        if self.last_ts is not None and ts_ms < self.last_ts:
            return int(self.run_id or 1)
        if self.last_cycle is not None and cycle_index is not None and cycle_index < self.last_cycle:
            new_run = True
        if new_run:
            self._finish_current()
            cur = self.conn.execute(
                "INSERT INTO graph_runs(start_ms,source,confidence,first_cycle_index,last_cycle_index) VALUES(?,?,?,?,?)",
                (ts_ms, "MEASUREMENT_V4", "RECONSTRUCTED_FROM_CYCLE_INDEX", cycle_index, cycle_index),
            )
            self.run_id = int(cur.lastrowid)
            self.run_start_ms = ts_ms
            self.first_cycle = cycle_index
        self.last_cycle = cycle_index if cycle_index is not None else self.last_cycle
        self.last_ts = ts_ms
        return int(self.run_id)

    def close(self) -> None:
        self._finish_current()



class CommandEventBuilder:
    """Persist only genuinely sparse command events.

    Dynamic desired/readback targets and sequence ids live in measurement_raw;
    lifecycle/effect/readback state lives in sparse intervals. This avoids an
    event row for every ordinary AUTO target change.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.last_run_id: Optional[int] = None
        self.last_publish_event: Optional[int] = None
        self.last_resync_count: Optional[int] = None
        self.last_neutralization_episode: Optional[int] = None

    def _insert(
        self,
        ts_ms: int,
        run_id: int,
        event_type: str,
        row: Mapping[str, Any],
        source_file_id: Optional[int],
        *,
        monotonic_ns: Optional[int] = None,
        entity_id: Optional[int] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO graph_command_events(
                ts_ms,monotonic_ns,run_id,entity_id,event_type,source_cycle_index,desired_sequence_id,publish_event_id,
                requested_target_dw,desired_target_dw,smart_mode,ac_mode,input_limit_dw,output_limit_dw,
                readback_matches_desired,mismatch_fields,effect_category,effect_reference_dw,reason,source_file_id
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                ts_ms,
                monotonic_ns,
                run_id,
                entity_id,
                event_type,
                safe_int(_first_value(row, "cycle_index", "cycle_id")),
                safe_int(row.get("command_desired_sequence_id")),
                safe_int(row.get("command_publish_event_id")),
                encode_scaled(row.get("command_requested_w"), scale=POWER_SCALE),
                encode_scaled(row.get("command_desired_signed_target_w"), scale=POWER_SCALE),
                safe_int(row.get("command_desired_smart_mode")),
                str(row.get("command_desired_ac_mode") or "").strip() or None,
                encode_scaled(row.get("command_desired_input_limit_w"), scale=POWER_SCALE),
                encode_scaled(row.get("command_desired_output_limit_w"), scale=POWER_SCALE),
                safe_int(row.get("command_readback_matches_desired")),
                str(row.get("command_readback_mismatch_fields") or "").strip() or None,
                str(row.get("command_effect_category") or row.get("command_effect_state_category") or "").strip() or None,
                encode_scaled(row.get("command_effect_reference_w"), scale=POWER_SCALE),
                str(row.get("command_effect_reason") or row.get("command_desired_reason") or "").strip() or None,
                source_file_id,
            ),
        )

    def observe(
        self, ts_ms: int, run_id: int, row: Mapping[str, Any], source_file_id: Optional[int],
        *, entity_id: Optional[int] = None,
    ) -> None:
        if self.last_run_id != run_id:
            self.last_run_id = run_id
            self.last_publish_event = None
            self.last_resync_count = None
            self.last_neutralization_episode = None

        publish = safe_int(row.get("command_publish_event_id"))
        if publish is not None and publish > 0 and publish != self.last_publish_event:
            publish_ts = safe_float(row.get("command_publish_epoch_s"))
            event_ts = int(round(publish_ts * 1000)) if publish_ts is not None else ts_ms
            self._insert(
                event_ts, run_id, "PUBLISHED", row, source_file_id,
                monotonic_ns=safe_int(row.get("command_publish_monotonic_ns")), entity_id=entity_id,
            )
            self.last_publish_event = publish

        resync = safe_int(row.get("command_resync_count"))
        if resync is not None and self.last_resync_count is not None and resync > self.last_resync_count:
            self._insert(ts_ms, run_id, "RESYNC", row, source_file_id, entity_id=entity_id)
        if resync is not None:
            self.last_resync_count = resync

        neutral = safe_int(row.get("command_neutralization_episode_id"))
        if neutral is not None and neutral > 0 and neutral != self.last_neutralization_episode:
            self._insert(ts_ms, run_id, "NEUTRALIZATION_EPISODE", row, source_file_id, entity_id=entity_id)
            self.last_neutralization_episode = neutral


@dataclass
class SourceAnomaly:
    kind: str
    detail: str


class V4SourceError(RuntimeError):
    pass


def _detect_delimiter(header_line: str) -> str:
    return ";" if header_line.count(";") >= header_line.count(",") else ","


def _iter_checked_text_lines(path: Path, anomalies: List[SourceAnomaly]) -> Iterator[str]:
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rb") as fh:  # type: ignore[arg-type]
        trailing_mode = False
        trailing_count = 0
        for raw in fh:
            if b"\x00" not in raw:
                if trailing_mode:
                    raise V4SourceError(f"{path}: non-NUL data after NUL padding")
                try:
                    yield raw.decode("utf-8-sig")
                except UnicodeDecodeError as exc:
                    raise V4SourceError(f"{path}: UTF-8 error: {exc}") from exc
                continue
            # The only repair policy accepted by WP1: a suffix consisting only
            # of NUL bytes after a complete record terminator. No embedded NUL
            # or NUL followed by real data is silently repaired.
            non_nul = raw.replace(b"\x00", b"")
            if non_nul not in (b"", b"\r", b"\n", b"\r\n"):
                raise V4SourceError(f"{path}: embedded NUL inside a record")
            trailing_mode = True
            trailing_count += raw.count(b"\x00")
        if trailing_count:
            anomalies.append(SourceAnomaly("TRAILING_NUL_PADDING", str(trailing_count)))


def iter_v4_rows(path: os.PathLike[str] | str) -> Tuple[List[SourceAnomaly], Iterator[Tuple[int, Dict[str, str]]]]:
    p = Path(path)
    anomalies: List[SourceAnomaly] = []

    def generator() -> Iterator[Tuple[int, Dict[str, str]]]:
        lines = _iter_checked_text_lines(p, anomalies)
        try:
            header_line = next(lines)
        except StopIteration:
            return
        delimiter = _detect_delimiter(header_line)
        header = next(csv.reader([header_line], delimiter=delimiter))
        if "measurement_epoch_ms" not in header:
            raise V4SourceError(f"{p}: not a supported Measurement V4 file")
        reader = csv.DictReader(lines, fieldnames=header, delimiter=delimiter)
        for line_no, row in enumerate(reader, start=2):
            if None in row:
                raise V4SourceError(f"{p}:{line_no}: CSV column overflow")
            yield line_no, dict(row)

    return anomalies, generator()


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def register_source_file(
    conn: sqlite3.Connection,
    path: Path,
    *,
    first_ms: Optional[int],
    last_ms: Optional[int],
    rows_seen: int,
    rows_imported: int,
    anomalies: Sequence[SourceAnomaly],
    include_sha256: bool,
) -> int:
    trailing = sum(int(a.detail) for a in anomalies if a.kind == "TRAILING_NUL_PADDING")
    anomaly_json = json.dumps([a.__dict__ for a in anomalies], ensure_ascii=False, separators=(",", ":")) if anomalies else None
    digest = sha256_file(path) if include_sha256 else None
    conn.execute(
        """
        INSERT INTO graph_source_files(path,size_bytes,sha256,first_ms,last_ms,rows_seen,rows_imported,trailing_nul_bytes,anomalies_json)
        VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(path) DO UPDATE SET
            size_bytes=excluded.size_bytes,sha256=excluded.sha256,first_ms=excluded.first_ms,last_ms=excluded.last_ms,
            rows_seen=excluded.rows_seen,rows_imported=excluded.rows_imported,trailing_nul_bytes=excluded.trailing_nul_bytes,
            anomalies_json=excluded.anomalies_json
        """,
        (str(path), path.stat().st_size, digest, first_ms, last_ms, rows_seen, rows_imported, trailing, anomaly_json),
    )
    row = conn.execute("SELECT source_file_id FROM graph_source_files WHERE path=?", (str(path),)).fetchone()
    return int(row[0])


def validate_graph_core(conn: sqlite3.Connection) -> Dict[str, Any]:
    integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    raw = conn.execute("SELECT COUNT(*),MIN(ts_ms),MAX(ts_ms) FROM measurement_raw").fetchone()
    minute = conn.execute("SELECT COUNT(*),MIN(bucket_start_ms),MAX(bucket_start_ms) FROM measurement_1min").fetchone()
    events = conn.execute("SELECT COUNT(*) FROM graph_command_events").fetchone()[0]
    intervals = conn.execute("SELECT COUNT(*) FROM graph_intervals").fetchone()[0]
    runs = conn.execute("SELECT COUNT(*) FROM graph_runs").fetchone()[0]
    sources = conn.execute("SELECT COUNT(*),COALESCE(SUM(trailing_nul_bytes),0) FROM graph_source_files").fetchone()
    entities = conn.execute("SELECT COUNT(*) FROM graph_entities").fetchone()[0]
    entity_raw = conn.execute("SELECT COUNT(*) FROM measurement_entity_raw").fetchone()[0]
    entity_minute = conn.execute("SELECT COUNT(*) FROM measurement_entity_1min").fetchone()[0]
    topology = conn.execute("SELECT COUNT(*) FROM graph_topology_timeline").fetchone()[0]
    duplicate_raw = conn.execute("SELECT COUNT(*) FROM (SELECT ts_ms FROM measurement_raw GROUP BY ts_ms HAVING COUNT(*)>1)").fetchone()[0]
    duplicate_entity_raw = conn.execute(
        "SELECT COUNT(*) FROM (SELECT entity_id,ts_ms FROM measurement_entity_raw GROUP BY entity_id,ts_ms HAVING COUNT(*)>1)"
    ).fetchone()[0]
    return {
        "integrity_check": integrity,
        "raw_rows": int(raw[0] or 0),
        "raw_first_ms": raw[1],
        "raw_last_ms": raw[2],
        "minute_rows": int(minute[0] or 0),
        "minute_first_ms": minute[1],
        "minute_last_ms": minute[2],
        "command_events": int(events or 0),
        "intervals": int(intervals or 0),
        "runs": int(runs or 0),
        "source_files": int(sources[0] or 0),
        "trailing_nul_bytes": int(sources[1] or 0),
        "entities": int(entities or 0),
        "entity_raw_rows": int(entity_raw or 0),
        "entity_minute_rows": int(entity_minute or 0),
        "topology_rows": int(topology or 0),
        "duplicate_raw_timestamps": int(duplicate_raw or 0),
        "duplicate_entity_raw_timestamps": int(duplicate_entity_raw or 0),
    }


def database_footprint(path: os.PathLike[str] | str) -> Dict[str, int]:
    p = Path(path)
    return {
        "db_bytes": p.stat().st_size if p.exists() else 0,
        "wal_bytes": Path(str(p) + "-wal").stat().st_size if Path(str(p) + "-wal").exists() else 0,
        "shm_bytes": Path(str(p) + "-shm").stat().st_size if Path(str(p) + "-shm").exists() else 0,
    }
