# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# Lightweight SQLite measurement/graph store for Zendure Energy Controller.
# The store is deliberately optional and parallel to CSV/V4 logging: controller
# regulation must never wait for SQLite writes.

import os
import queue
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB_FILENAME = "zec_measurements.sqlite3"


def _safe_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ja", "on", "valid", "gültig"}


def _first(row: Dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row.get(name) not in (None, ""):
            return row.get(name)
    return ""


def _parse_epoch_ms(row: Dict[str, Any]) -> Optional[int]:
    epoch = _safe_float(_first(row, "epoch_s", "epoch"))
    if epoch is not None:
        return int(round(epoch * 1000))
    epoch_ms = _safe_int(_first(row, "epoch_ms", "measurement_epoch_ms"))
    if epoch_ms is not None:
        return epoch_ms
    text = str(_first(row, "datetime_local", "local_time", "timestamp_local") or "").strip()
    if text:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y %H:%M:%S"):
            try:
                return int(datetime.strptime(text[:19], fmt).timestamp() * 1000)
            except Exception:
                pass
    date_part = str(row.get("date") or "").strip()
    time_part = str(row.get("timestamp") or "").strip()
    if date_part and time_part:
        try:
            return int(datetime.strptime(f"{date_part} {time_part[:8]}", "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
        except Exception:
            pass
    return None


def extract_measurement_point(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ts_ms = _parse_epoch_ms(row)
    if ts_ms is None:
        return None
    grid = _safe_float(_first(row, "grid_power_w", "norm_grid_power_w", "grid_power"))
    raw_grid = _safe_float(_first(row, "raw_grid_power_w", "raw_grid_power"))
    target = _safe_float(_first(row, "target_final_w", "zendure_target_power_w", "command_effective_w", "zendure_target_signed_power"))
    actual = _safe_float(_first(row, "zendure_actual_power_w", "actual_zendure_power_w", "norm_zendure_actual_power_w", "zendure_system_signed_power"))
    soc = _safe_float(_first(row, "zendure_soc_percent", "norm_zendure_soc_percent", "raw_zendure_soc_percent", "soc"))
    primary_soc = _safe_float(_first(row, "second_battery_soc_percent", "sma_battery_soc", "primary_soc_percent"))
    primary_power = _safe_float(_first(row, "second_battery_power_w", "sma_battery_power_w", "sma_battery_power"))
    pv = _safe_float(_first(row, "pv_power_w")) if _boolish(_first(row, "pv_power_valid", "pv_valid")) else None
    house = _safe_float(_first(row, "house_power_w")) if _boolish(_first(row, "house_power_valid", "house_valid")) else None
    soc_valid_raw = _first(row, "soc_valid", "zendure_soc_valid")
    soc_valid = _boolish(soc_valid_raw) if soc_valid_raw not in (None, "") else soc is not None
    mode = str(_first(row, "mode", "operating_mode") or "")
    control_reason = str(_first(
        row,
        "control_reason",
        "target_final_reason",
        "safe_state_reason",
        "rest_surplus_harvest_reason",
        "command_effect_reason",
    ) or "").strip()
    data_status = "gültig" if (soc_valid or soc is not None) else "nicht bewertet"
    return {
        "ts_ms": int(ts_ms),
        "grid_power_w": grid,
        "raw_grid_power_w": raw_grid,
        "zendure_target_power_w": target,
        "zendure_actual_power_w": actual,
        "pv_power_w": pv,
        "house_power_w": house,
        "soc_percent": soc,
        "primary_soc_percent": primary_soc,
        "primary_power_w": primary_power,
        "mode": mode,
        "control_reason": control_reason,
        "data_status": data_status,
        "source": str(_first(row, "raw_grid_source", "grid_meter_source") or ""),
        "soc_valid": 1 if soc_valid else 0,
        "grid_valid": 1 if _boolish(_first(row, "grid_power_valid", "grid_valid")) else 0,
        "safe_state_active": 1 if (_boolish(row.get("safe_state_active")) or mode == "SAFE_STATE") else 0,
        "cross_charge_limited": 1 if _boolish(_first(row, "cross_charge_guard_limited", "control_cross_charge_limited")) else 0,
        "night_window_active": 1 if (_boolish(_first(row, "night_discharge_window_active", "night_window_active")) or mode == "NIGHT_DISCHARGE") else 0,
        "night_reserve_active": 1 if _boolish(_first(row, "night_discharge_reserve_active", "control_night_reserve_active")) else 0,
        "config_control_hash": str(_first(row, "config_control_hash") or "").strip(),
    }


def resolve_measurement_db_path(config: Dict[str, Any]) -> str:
    explicit = str(config.get("MEASUREMENT_DB_PATH", "") or "").strip()
    if explicit:
        return os.path.abspath(explicit)
    filename = str(config.get("MEASUREMENT_DB_FILE", DEFAULT_DB_FILENAME) or DEFAULT_DB_FILENAME).strip() or DEFAULT_DB_FILENAME
    # Reuse the selected measurement target directory, but avoid importing
    # csv_logger at module import time to prevent circular imports.
    directory = "logs"
    try:
        from csv_logger import resolve_log_target  # local import by design
        target = resolve_log_target(config, allow_fallback=True)
        path = str(target.get("path") or "")
        if path:
            directory = os.path.dirname(os.path.abspath(path))
        else:
            directory = os.path.abspath(str(config.get("MEASUREMENT_LOG_DIR", "logs") or "logs"))
    except Exception:
        directory = os.path.abspath(str(config.get("MEASUREMENT_LOG_DIR", "logs") or "logs"))
    return os.path.abspath(os.path.join(directory, filename))


def _connect(path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=1.0)
    try:
        # WAL is fast on ext4/SSD. On vfat/fuse it may fail; fall back silently to DELETE.
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except Exception:
            try:
                conn.execute("PRAGMA journal_mode=DELETE")
            except Exception:
                pass
        try:
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA busy_timeout=1000")
        except Exception:
            pass
        ensure_schema(conn)
        return conn
    except Exception:
        conn.close()
        raise


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS measurement_raw (
            ts_ms INTEGER PRIMARY KEY,
            grid_power_w REAL,
            raw_grid_power_w REAL,
            zendure_target_power_w REAL,
            zendure_actual_power_w REAL,
            pv_power_w REAL,
            house_power_w REAL,
            soc_percent REAL,
            mode TEXT,
            control_reason TEXT,
            data_status TEXT,
            source TEXT,
            soc_valid INTEGER,
            grid_valid INTEGER,
            safe_state_active INTEGER,
            cross_charge_limited INTEGER,
            night_window_active INTEGER,
            night_reserve_active INTEGER
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_measurement_raw_ts ON measurement_raw(ts_ms)")
    for table, columns in {
        "measurement_raw": {
            "primary_soc_percent": "REAL",
            "primary_power_w": "REAL",
            "control_reason": "TEXT",
        },
    }.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col, typ in columns.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS measurement_1min (
            bucket_start_ms INTEGER PRIMARY KEY,
            sample_count INTEGER NOT NULL,
            first_ts_ms INTEGER,
            last_ts_ms INTEGER,
            grid_avg_w REAL,
            grid_min_w REAL,
            grid_max_w REAL,
            raw_grid_last_w REAL,
            zendure_target_last_w REAL,
            zendure_actual_last_w REAL,
            pv_avg_w REAL,
            house_avg_w REAL,
            soc_last_percent REAL,
            primary_soc_last_percent REAL,
            primary_power_last_w REAL,
            mode_last TEXT,
            control_reason_last TEXT,
            data_status_last TEXT,
            source_last TEXT,
            soc_valid_last INTEGER,
            grid_valid_last INTEGER,
            safe_state_active INTEGER,
            cross_charge_limited INTEGER,
            night_window_active INTEGER,
            night_reserve_active INTEGER
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_measurement_1min_bucket ON measurement_1min(bucket_start_ms)")
    existing_1min = {row[1] for row in conn.execute("PRAGMA table_info(measurement_1min)").fetchall()}
    for col, typ in {
        "primary_soc_last_percent": "REAL",
        "primary_power_last_w": "REAL",
        "control_reason_last": "TEXT",
    }.items():
        if col not in existing_1min:
            conn.execute(f"ALTER TABLE measurement_1min ADD COLUMN {col} {typ}")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS measurement_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    conn.execute("INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('schema_version','2')")
    # V13 graph overlay history is a separate, lightweight schema extension;
    # Measurement V4 and the 1-minute measurement schema remain unchanged.
    from graph_config_timeline import ensure_graph_config_schema
    ensure_graph_config_schema(conn)
    conn.commit()


def _avg_update(old_avg: Optional[float], old_count: int, value: Optional[float]) -> Optional[float]:
    if value is None:
        return old_avg
    if old_avg is None or old_count <= 0:
        return float(value)
    return ((float(old_avg) * old_count) + float(value)) / (old_count + 1)


def _min_update(old: Optional[float], value: Optional[float]) -> Optional[float]:
    if value is None:
        return old
    if old is None:
        return float(value)
    return min(float(old), float(value))


def _max_update(old: Optional[float], value: Optional[float]) -> Optional[float]:
    if value is None:
        return old
    if old is None:
        return float(value)
    return max(float(old), float(value))


def write_points(conn: sqlite3.Connection, points: List[Dict[str, Any]]) -> int:
    from graph_config_timeline import ensure_graph_config_schema, upsert_timeline_entry
    ensure_graph_config_schema(conn)
    latest_timeline = conn.execute(
        "SELECT config_control_hash FROM graph_config_timeline ORDER BY effective_from_ms DESC LIMIT 1"
    ).fetchone()
    last_timeline_hash = str(latest_timeline[0]) if latest_timeline and latest_timeline[0] else ""
    written = 0
    for p in points:
        conn.execute(
            """
            INSERT OR REPLACE INTO measurement_raw(
                ts_ms, grid_power_w, raw_grid_power_w, zendure_target_power_w,
                zendure_actual_power_w, pv_power_w, house_power_w, soc_percent,
                primary_soc_percent, primary_power_w, mode, control_reason, data_status, source, soc_valid, grid_valid, safe_state_active,
                cross_charge_limited, night_window_active, night_reserve_active
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                p["ts_ms"], p.get("grid_power_w"), p.get("raw_grid_power_w"), p.get("zendure_target_power_w"),
                p.get("zendure_actual_power_w"), p.get("pv_power_w"), p.get("house_power_w"), p.get("soc_percent"),
                p.get("primary_soc_percent"), p.get("primary_power_w"), p.get("mode"), p.get("control_reason"), p.get("data_status"), p.get("source"), p.get("soc_valid"), p.get("grid_valid"),
                p.get("safe_state_active"), p.get("cross_charge_limited"), p.get("night_window_active"), p.get("night_reserve_active"),
            ),
        )
        bucket = int(p["ts_ms"] // 60000) * 60000
        cur = conn.execute("SELECT * FROM measurement_1min WHERE bucket_start_ms=?", (bucket,))
        row = cur.fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO measurement_1min(
                    bucket_start_ms, sample_count, first_ts_ms, last_ts_ms, grid_avg_w,
                    grid_min_w, grid_max_w, raw_grid_last_w, zendure_target_last_w,
                    zendure_actual_last_w, pv_avg_w, house_avg_w, soc_last_percent,
                    primary_soc_last_percent, primary_power_last_w, mode_last, control_reason_last, data_status_last, source_last, soc_valid_last, grid_valid_last,
                    safe_state_active, cross_charge_limited, night_window_active, night_reserve_active
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    bucket, 1, p["ts_ms"], p["ts_ms"], p.get("grid_power_w"), p.get("grid_power_w"), p.get("grid_power_w"),
                    p.get("raw_grid_power_w"), p.get("zendure_target_power_w"), p.get("zendure_actual_power_w"),
                    p.get("pv_power_w"), p.get("house_power_w"), p.get("soc_percent"),
                    p.get("primary_soc_percent"), p.get("primary_power_w"), p.get("mode"), p.get("control_reason"), p.get("data_status"),
                    p.get("source"), p.get("soc_valid"), p.get("grid_valid"), p.get("safe_state_active"),
                    p.get("cross_charge_limited"), p.get("night_window_active"), p.get("night_reserve_active"),
                ),
            )
        else:
            cols = [d[0] for d in cur.description]
            old = dict(zip(cols, row))
            count = int(old.get("sample_count") or 0)
            conn.execute(
                """
                UPDATE measurement_1min SET
                    sample_count=?, first_ts_ms=?, last_ts_ms=?, grid_avg_w=?, grid_min_w=?, grid_max_w=?,
                    raw_grid_last_w=?, zendure_target_last_w=?, zendure_actual_last_w=?, pv_avg_w=?, house_avg_w=?,
                    soc_last_percent=?, primary_soc_last_percent=?, primary_power_last_w=?, mode_last=?, control_reason_last=?, data_status_last=?, source_last=?, soc_valid_last=?, grid_valid_last=?,
                    safe_state_active=?, cross_charge_limited=?, night_window_active=?, night_reserve_active=?
                WHERE bucket_start_ms=?
                """,
                (
                    count + 1,
                    min(int(old.get("first_ts_ms") or p["ts_ms"]), p["ts_ms"]),
                    max(int(old.get("last_ts_ms") or p["ts_ms"]), p["ts_ms"]),
                    _avg_update(old.get("grid_avg_w"), count, p.get("grid_power_w")),
                    _min_update(old.get("grid_min_w"), p.get("grid_power_w")),
                    _max_update(old.get("grid_max_w"), p.get("grid_power_w")),
                    p.get("raw_grid_power_w"), p.get("zendure_target_power_w"), p.get("zendure_actual_power_w"),
                    _avg_update(old.get("pv_avg_w"), count, p.get("pv_power_w")),
                    _avg_update(old.get("house_avg_w"), count, p.get("house_power_w")),
                    p.get("soc_percent"), p.get("primary_soc_percent"), p.get("primary_power_w"), p.get("mode"), p.get("control_reason"), p.get("data_status"), p.get("source"),
                    p.get("soc_valid"), p.get("grid_valid"),
                    1 if int(old.get("safe_state_active") or 0) or int(p.get("safe_state_active") or 0) else 0,
                    1 if int(old.get("cross_charge_limited") or 0) or int(p.get("cross_charge_limited") or 0) else 0,
                    1 if int(old.get("night_window_active") or 0) or int(p.get("night_window_active") or 0) else 0,
                    1 if int(old.get("night_reserve_active") or 0) or int(p.get("night_reserve_active") or 0) else 0,
                    bucket,
                ),
            )
        config_hash = str(p.get("config_control_hash") or "")
        overlay = p.get("_graph_config_overlay")
        if config_hash and isinstance(overlay, dict) and config_hash != last_timeline_hash:
            upsert_timeline_entry(
                conn, int(p["ts_ms"]), config_hash, overlay=overlay, source="runtime_effective", known=True, ensure_schema=False, commit=False
            )
            last_timeline_hash = config_hash
        written += 1
    if points:
        conn.execute("INSERT OR REPLACE INTO measurement_meta(key,value) VALUES('last_write_epoch_s',?)", (str(time.time()),))
    conn.commit()
    return written



def detect_measurement_db_backend(path: str) -> Dict[str, Any]:
    """Classify an existing SQLite store without mutating it."""
    absolute = os.path.abspath(path)
    if not os.path.exists(absolute) or os.path.getsize(absolute) == 0:
        return {"backend": "missing", "schema_version": None, "path": absolute}
    conn = None
    try:
        conn = sqlite3.connect(f"file:{absolute}?mode=ro", uri=True, timeout=1.0)
        version = None
        try:
            row = conn.execute("SELECT value FROM measurement_meta WHERE key='schema_version'").fetchone()
            version = str(row[0]) if row and row[0] not in (None, "") else None
        except Exception:
            version = None
        if version == "3":
            return {"backend": "v3", "schema_version": 3, "path": absolute}
        if version == "2":
            return {"backend": "v2", "schema_version": 2, "path": absolute}
        # Historical V2 stores are also recognizable by their legacy raw fields.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(measurement_raw)").fetchall()}
        if {"ts_ms", "zendure_target_power_w", "mode", "control_reason"}.issubset(cols):
            return {"backend": "v2", "schema_version": 2, "path": absolute}
        return {"backend": "unknown", "schema_version": version, "path": absolute}
    except Exception as exc:
        return {"backend": "unknown", "schema_version": None, "path": absolute, "error": str(exc)}
    finally:
        if conn is not None:
            conn.close()


class MeasurementDbWriter:
    WRITE_STALE_SECONDS = 120.0
    RETRY_DELAY_SECONDS = 0.5
    DEFAULT_MAX_QUEUE = 5000
    _STOP_SENTINEL = object()

    def __init__(self, max_queue: int = DEFAULT_MAX_QUEUE) -> None:
        self._max_queue = int(max_queue)
        self._queue: "queue.Queue[Any]" = queue.Queue(maxsize=self._max_queue)
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._conn_thread_id: Optional[int] = None
        self._path = ""
        self._backend = ""
        self._schema_version: Optional[int] = None
        self._v3_session = None
        self._last_status: Dict[str, Any] = {
            "measurement_db_status": "idle",
            "measurement_db_reason": "Noch kein DB-Schreibversuch.",
            "measurement_db_path": "",
            "measurement_db_queue_depth": 0,
            "measurement_db_queue_capacity": self._max_queue,
            "measurement_db_backend": "",
            "measurement_db_schema_version": None,
            "measurement_db_storage_encoding": "",
            "measurement_db_run_id": None,
            "measurement_db_last_write_epoch_s": "",
            "measurement_db_last_write_duration_ms": None,
            "measurement_db_prepare_duration_ms": None,
            "measurement_db_error": "",
            "measurement_db_last_error": "",
            "measurement_db_last_error_epoch_s": "",
            "measurement_db_consecutive_failures": 0,
            "measurement_db_last_success_epoch_s": "",
            "measurement_db_write_stale": False,
            "measurement_db_first_enqueue_epoch_s": "",
            "measurement_db_last_enqueue_epoch_s": "",
            "measurement_db_rows_written": 0,
            "measurement_db_rows_dropped": 0,
            "measurement_db_size_bytes": 0,
        }

    def _refresh_stale_locked(self, now: Optional[float] = None) -> None:
        now = float(now if now is not None else time.time())
        first = self._last_status.get("measurement_db_first_enqueue_epoch_s")
        last_enqueue = self._last_status.get("measurement_db_last_enqueue_epoch_s")
        last_success = self._last_status.get("measurement_db_last_success_epoch_s")
        try:
            first_f = float(first) if first not in (None, "") else 0.0
        except Exception:
            first_f = 0.0
        try:
            enqueue_f = float(last_enqueue) if last_enqueue not in (None, "") else 0.0
        except Exception:
            enqueue_f = 0.0
        try:
            success_f = float(last_success) if last_success not in (None, "") else 0.0
        except Exception:
            success_f = 0.0
        reference = success_f or first_f
        stale = bool(enqueue_f and reference and enqueue_f > success_f and (now - reference) >= self.WRITE_STALE_SECONDS)
        self._last_status["measurement_db_write_stale"] = stale
        failures = int(self._last_status.get("measurement_db_consecutive_failures") or 0)
        if stale and failures <= 0:
            self._last_status["measurement_db_status"] = "stale"
            self._last_status["measurement_db_reason"] = "Seit mindestens 120 s kein erfolgreicher DB-Schreibvorgang trotz neuer Messpunkte."

    def _snapshot_locked(self) -> Dict[str, Any]:
        self._refresh_stale_locked()
        data = dict(self._last_status)
        data["measurement_db_queue_depth"] = self._queue.qsize()
        return data

    def enqueue(self, config: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        if not bool(config.get("MEASUREMENT_DB_ENABLED", True)):
            return self._set_status("disabled", "MEASUREMENT_DB_ENABLED=false", config=config)
        started_ns = time.perf_counter_ns()
        if _parse_epoch_ms(row) is None:
            return self._set_status("skipped", "Row ohne auswertbare Zeitbasis", config=config)
        payload = dict(row)
        # Capture config evidence before the worker thread; no DB I/O occurs here.
        try:
            from csv_logger import compute_config_control_hash
            from graph_config_timeline import overlay_from_config
            payload["_graph_config_hash"] = compute_config_control_hash(config)
            payload["_graph_config_overlay"] = overlay_from_config(config)
            payload["_graph_entity_config"] = {
                "zendure_device_id": str(config.get("DEVICE_ID") or "").strip(),
                "primary_display_name": str(config.get("SECOND_BATTERY_DISPLAY_NAME") or "").strip(),
                "primary_source_profile": str(config.get("SECOND_BATTERY_SOURCE_PROFILE") or "").strip(),
                "primary_integration_enabled": bool(config.get("SECOND_BATTERY_INTEGRATION_ENABLED", False)),
            }
        except Exception:
            pass
        if payload.get("measurement_monotonic_ns") in (None, ""):
            payload["measurement_monotonic_ns"] = time.monotonic_ns()
        path = resolve_measurement_db_path(config)
        now = time.time()
        prepare_ms = round((time.perf_counter_ns() - started_ns) / 1_000_000.0, 3)
        try:
            self._ensure_thread()
            self._queue.put_nowait((path, payload))
            with self._lock:
                if not self._last_status.get("measurement_db_first_enqueue_epoch_s"):
                    self._last_status["measurement_db_first_enqueue_epoch_s"] = now
                self._last_status["measurement_db_last_enqueue_epoch_s"] = now
                self._last_status["measurement_db_path"] = path
                self._last_status["measurement_db_prepare_duration_ms"] = prepare_ms
                failures = int(self._last_status.get("measurement_db_consecutive_failures") or 0)
                if failures <= 0 and not self._last_status.get("measurement_db_write_stale"):
                    self._last_status["measurement_db_status"] = "queued"
                    self._last_status["measurement_db_reason"] = "DB-Schreibvorgang gepuffert"
                self._refresh_stale_locked(now)
                return self._snapshot_locked()
        except queue.Full:
            with self._lock:
                dropped = int(self._last_status.get("measurement_db_rows_dropped") or 0) + 1
                self._last_status["measurement_db_rows_dropped"] = dropped
                self._last_status["measurement_db_status"] = "queue_full"
                self._last_status["measurement_db_reason"] = "DB-Queue voll; Messpunkt verworfen"
                self._last_status["measurement_db_path"] = path
                return self._snapshot_locked()
        except Exception as exc:
            return self._set_status("error", str(exc), path=path, config=config, error=str(exc))

    def _ensure_thread(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, name="zec-measurement-db-writer", daemon=True)
        self._thread.start()

    def _worker(self) -> None:
        batch: List[Dict[str, Any]] = []
        current_path = ""
        deferred: Optional[Tuple[str, Dict[str, Any]]] = None
        retry_pending = False
        try:
            while True:
                if batch and retry_pending:
                    if self._flush(current_path, batch):
                        batch = []
                        retry_pending = False
                    elif self._stop.is_set():
                        break
                    else:
                        self._stop.wait(self.RETRY_DELAY_SECONDS)
                        continue

                if deferred is not None:
                    path, point = deferred
                    deferred = None
                else:
                    try:
                        item = self._queue.get(timeout=0.25)
                    except queue.Empty:
                        if batch and current_path:
                            if self._flush(current_path, batch):
                                batch = []
                            elif self._stop.is_set():
                                break
                            else:
                                retry_pending = True
                        if self._stop.is_set() and self._queue.empty() and not batch:
                            break
                        continue
                    if item is self._STOP_SENTINEL:
                        self._queue.task_done()
                        self._stop.set()
                        if not batch:
                            break
                        continue
                    path, point = item
                    self._queue.task_done()

                if current_path and path != current_path and batch:
                    deferred = (path, point)
                    if self._flush(current_path, batch):
                        batch = []
                        current_path = ""
                    elif self._stop.is_set():
                        break
                    else:
                        retry_pending = True
                    continue

                current_path = path
                batch.append(point)
                if len(batch) >= 50:
                    if self._flush(current_path, batch):
                        batch = []
                    elif self._stop.is_set():
                        break
                    else:
                        retry_pending = True

                if self._stop.is_set() and self._queue.empty() and batch:
                    if self._flush(current_path, batch):
                        batch = []
                    break
        finally:
            self._reset_connection(rollback=False)

    def _reset_connection(self, *, rollback: bool) -> None:
        conn = self._conn
        self._conn = None
        self._conn_thread_id = None
        self._path = ""
        self._backend = ""
        self._schema_version = None
        if conn is not None:
            if rollback:
                try:
                    conn.rollback()
                except Exception:
                    pass
            try:
                conn.close()
            except Exception:
                pass

    @staticmethod
    def _legacy_point(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if "ts_ms" in row and "grid_power_w" in row:
            return dict(row)
        return extract_measurement_point(row)

    def _open_backend(self, path: str) -> None:
        detection = detect_measurement_db_backend(path)
        backend = str(detection.get("backend") or "unknown")
        if backend == "missing":
            backend = "v3"
        if backend == "v2":
            self._conn = _connect(path)
            self._schema_version = 2
        elif backend == "v3":
            from graph_core_v3_live import GraphCoreV3LiveSession, open_v3
            self._conn = open_v3(path)
            self._schema_version = 3
            if self._v3_session is None:
                self._v3_session = GraphCoreV3LiveSession()
        else:
            detail = detection.get("error") or detection.get("schema_version") or "unbekanntes Schema"
            raise RuntimeError(f"MEASUREMENT_DB_UNKNOWN_SCHEMA:{detail}")
        self._conn_thread_id = threading.get_ident()
        self._path = path
        self._backend = backend

    def _flush(self, path: str, batch: List[Dict[str, Any]]) -> bool:
        if not batch:
            return True
        started_ns = time.perf_counter_ns()
        try:
            from measurement_db_maintenance import measurement_db_maintenance_lock
            with measurement_db_maintenance_lock(path, timeout_s=5.0):
                if self._conn is None or self._path != path:
                    self._reset_connection(rollback=False)
                    self._open_backend(path)
                assert self._conn is not None
                if self._backend == "v2":
                    points = [p for p in (self._legacy_point(row) for row in batch) if p is not None]
                    count = write_points(self._conn, points)
                elif self._backend == "v3":
                    count = self._v3_session.write_batch(self._conn, path, batch)
                else:
                    raise RuntimeError("MEASUREMENT_DB_BACKEND_NOT_READY")
            now = time.time()
            with self._lock:
                total = int(self._last_status.get("measurement_db_rows_written") or 0) + count
                self._last_status.update({
                    "measurement_db_status": "active",
                    "measurement_db_reason": "OK",
                    "measurement_db_path": path,
                    "measurement_db_queue_depth": self._queue.qsize(),
                    "measurement_db_queue_capacity": self._max_queue,
                    "measurement_db_backend": self._backend,
                    "measurement_db_schema_version": self._schema_version,
                    "measurement_db_storage_encoding": "scaled_integer_v1" if self._backend == "v3" else "legacy_real_v2",
                    "measurement_db_run_id": getattr(self._v3_session, "run_id", None) if self._backend == "v3" else None,
                    "measurement_db_last_write_epoch_s": now,
                    "measurement_db_last_success_epoch_s": now,
                    "measurement_db_last_write_duration_ms": round((time.perf_counter_ns() - started_ns) / 1_000_000.0, 3),
                    "measurement_db_error": "",
                    "measurement_db_consecutive_failures": 0,
                    "measurement_db_write_stale": False,
                    "measurement_db_rows_written": total,
                    "measurement_db_size_bytes": os.path.getsize(path) if os.path.exists(path) else 0,
                })
            return True
        except Exception as exc:
            self._reset_connection(rollback=True)
            now = time.time()
            message = str(exc)
            with self._lock:
                failures = int(self._last_status.get("measurement_db_consecutive_failures") or 0) + 1
                self._last_status.update({
                    "measurement_db_status": "error",
                    "measurement_db_reason": message,
                    "measurement_db_path": path,
                    "measurement_db_queue_depth": self._queue.qsize(),
                    "measurement_db_error": message,
                    "measurement_db_last_error": message,
                    "measurement_db_last_error_epoch_s": now,
                    "measurement_db_consecutive_failures": failures,
                })
                self._refresh_stale_locked(now)
            return False

    def _set_status(self, status: str, reason: str, *, path: str = "", config: Optional[Dict[str, Any]] = None, error: str = "") -> Dict[str, Any]:
        if config is not None and not path:
            try:
                path = resolve_measurement_db_path(config)
            except Exception:
                path = ""
        with self._lock:
            failures = int(self._last_status.get("measurement_db_consecutive_failures") or 0)
            if failures > 0 and status == "queued":
                status = "error"
                reason = str(self._last_status.get("measurement_db_reason") or reason)
            self._last_status.update({
                "measurement_db_status": status,
                "measurement_db_reason": reason,
                "measurement_db_path": path or self._last_status.get("measurement_db_path", ""),
                "measurement_db_queue_depth": self._queue.qsize(),
                "measurement_db_queue_capacity": self._max_queue,
            })
            if error:
                now = time.time()
                self._last_status["measurement_db_error"] = error
                self._last_status["measurement_db_last_error"] = error
                self._last_status["measurement_db_last_error_epoch_s"] = now
            if path and os.path.exists(path):
                try:
                    self._last_status["measurement_db_size_bytes"] = os.path.getsize(path)
                except Exception:
                    pass
            return self._snapshot_locked()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return self._snapshot_locked()

    def __del__(self):
        # Destructor must never block interpreter/test shutdown. Explicit owners
        # call close(); daemon-thread/process exit remains a final safety net.
        try:
            self._stop.set()
        except Exception:
            pass

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            try:
                self._queue.put_nowait(self._STOP_SENTINEL)
            except Exception:
                pass
            thread.join(timeout=6.0)
            if not thread.is_alive():
                self._thread = None
            else:
                with self._lock:
                    self._last_status["measurement_db_status"] = "shutdown_timeout"
                    self._last_status["measurement_db_reason"] = "DB-Writer konnte nicht innerhalb des Shutdown-Timeouts beendet werden"
        if self._conn is not None and self._conn_thread_id in (None, threading.get_ident()):
            self._reset_connection(rollback=False)

def db_status_for_config(config: Dict[str, Any]) -> Dict[str, Any]:
    path = resolve_measurement_db_path(config)
    detection = detect_measurement_db_backend(path)
    backend = str(detection.get("backend") or "unknown")
    status = "available" if backend in {"v2", "v3"} else ("missing" if backend == "missing" else "error")
    return {
        "measurement_db_status": status,
        "measurement_db_path": path,
        "measurement_db_size_bytes": os.path.getsize(path) if os.path.exists(path) else 0,
        "measurement_db_backend": backend,
        "measurement_db_schema_version": detection.get("schema_version"),
        "measurement_db_storage_encoding": "scaled_integer_v1" if backend == "v3" else ("legacy_real_v2" if backend == "v2" else ""),
        "measurement_db_error": detection.get("error", "") if backend == "unknown" else "",
    }


def query_measurement_date_range(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return the first and last local calendar dates available in the 1-minute store."""
    if not bool(config.get("MEASUREMENT_DB_ENABLED", True)):
        return {"available_from": "", "available_to": "", "db_status": "disabled"}
    path = resolve_measurement_db_path(config)
    if not os.path.exists(path):
        return {"available_from": "", "available_to": "", "db_status": "missing"}
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(path, timeout=1.0)
        row = conn.execute(
            "SELECT MIN(bucket_start_ms), MAX(bucket_start_ms) FROM measurement_1min"
        ).fetchone()
        first_ms, last_ms = row if row else (None, None)
        return {
            "available_from": datetime.fromtimestamp(first_ms / 1000.0).date().isoformat() if first_ms is not None else "",
            "available_to": datetime.fromtimestamp(last_ms / 1000.0).date().isoformat() if last_ms is not None else "",
            "db_status": "hit",
        }
    except Exception as exc:
        return {"available_from": "", "available_to": "", "db_status": "error", "db_error": str(exc)}
    finally:
        if conn is not None:
            conn.close()


def query_graph_points(config: Dict[str, Any], start_dt: datetime, end_dt: datetime, *, limit: int = 5000) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not bool(config.get("MEASUREMENT_DB_ENABLED", True)):
        return [], {"db_status": "disabled", "db_path": ""}
    path = resolve_measurement_db_path(config)
    detection = detect_measurement_db_backend(path)
    backend = str(detection.get("backend") or "unknown")
    if backend == "missing":
        return [], {"db_status": "missing", "db_path": path}
    if backend == "unknown":
        return [], {"db_status": "error", "db_path": path, "db_error": str(detection.get("error") or "UNKNOWN_DB_SCHEMA")}
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    if backend == "v3":
        # V3 history has one canonical SQL/query implementation.  This adapter
        # only restores the legacy V13 point shape for existing UI consumers.
        from graph_query_service import GRAPH_QUERY_SERVICE
        points, meta = GRAPH_QUERY_SERVICE.compatibility_points(path, start_ms, end_ms, limit=limit)
        for point in points:
            dt = datetime.fromtimestamp(int(point["epoch_ms"]) / 1000.0)
            point["time"] = dt.strftime("%H:%M:%S")
            point["datetime_local"] = dt.isoformat(sep=" ", timespec="seconds")
        return points, meta

    # Legacy V2 remains read-compatible and is never mutated by this path.
    query_start_ms = (start_ms // 60000) * 60000
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(path, timeout=1.0)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM measurement_1min
            WHERE bucket_start_ms >= ? AND bucket_start_ms <= ?
            ORDER BY bucket_start_ms ASC
            LIMIT ?
            """,
            (query_start_ms, end_ms, int(limit)),
        ).fetchall()
    except Exception as exc:
        return [], {"db_status": "error", "db_path": path, "db_error": str(exc), "db_backend": backend}
    finally:
        if conn is not None:
            conn.close()

    points: List[Dict[str, Any]] = []
    for row in rows:
        ts_ms = int(row["last_ts_ms"] or row["bucket_start_ms"])
        dt = datetime.fromtimestamp(ts_ms / 1000.0)
        mode = row["mode_last"] or ""
        points.append({
            "time": dt.strftime("%H:%M:%S"), "datetime_local": dt.isoformat(sep=" ", timespec="seconds"), "epoch_ms": ts_ms,
            "grid_power_w": row["grid_avg_w"], "grid_power_min_w": row["grid_min_w"], "grid_power_max_w": row["grid_max_w"],
            "grid_power_raw_w": row["raw_grid_last_w"], "zendure_target_power_w": row["zendure_target_last_w"],
            "zendure_actual_power_w": row["zendure_actual_last_w"], "pv_power_w": row["pv_avg_w"], "house_power_w": row["house_avg_w"],
            "soc": row["soc_last_percent"], "primary_soc": row["primary_soc_last_percent"] if "primary_soc_last_percent" in row.keys() else None,
            "primary_power_w": row["primary_power_last_w"] if "primary_power_last_w" in row.keys() else None,
            "mode": mode, "mode_label": mode,
            "control_reason": (row["control_reason_last"] if "control_reason_last" in row.keys() else "") or "", "limit_reason": "",
            "data_status": row["data_status_last"] or "gültig", "cross_charge_limited": bool(row["cross_charge_limited"]),
            "safe_state_active": bool(row["safe_state_active"]), "night_window_active": bool(row["night_window_active"]),
            "night_reserve_active": bool(row["night_reserve_active"]), "sample_count": row["sample_count"],
        })
    return points, {
        "db_status": "hit", "db_path": path, "db_rows": len(points),
        "db_size_bytes": os.path.getsize(path) if os.path.exists(path) else 0,
        "db_backend": "v2", "db_schema_version": detection.get("schema_version"),
    }
