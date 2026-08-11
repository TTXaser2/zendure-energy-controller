# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import csv
import hashlib
import io
import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from version import APP_VERSION, APP_VERSION_LABEL

# Schema-neutraler RAM-/Graph-Exportvertrag. Diese Spaltenliste ist kein
# produktives Measurement-Schema. Persistente Controller-Messdaten werden
# ausschliesslich durch MeasurementV4Logger nach dem V4-Vertrag geschrieben.
GRAPH_EXPORT_SCHEMA = "ZEC-GRAPH-EXPORT-V1"
GRAPH_EXPORT_SCHEMA_VERSION = "1.0"
GRAPH_EXPORT_FIELDS: List[str] = [
    "schema",
    "schema_version",
    "controller_version",
    "date",
    "timestamp",
    "datetime_local",
    "epoch",
    "dt_s",
    "grid_power_w",
    "zendure_target_power_w",
    "zendure_actual_power_w",
    "second_battery_power_w",
    "second_battery_soc_percent",
    "norm_zendure_soc_percent",
    "battery_temperature_c",
    "mode",
    "control_reason",
    "target_final_reason",
    "measurement_log_status",
    "measurement_log_status_reason",
]

# Compatibility alias for code/tests that historically imported CSV_FIELDS.
# It now denotes only the schema-neutral graph export columns.
CSV_FIELDS = GRAPH_EXPORT_FIELDS

CSV_HEADER_MAP = {field: field for field in GRAPH_EXPORT_FIELDS}

CONTROL_HASH_KEYS = [
    "INTERVAL_SECONDS", "DEADBAND_W", "MOVING_AVERAGE_SAMPLES", "SMOOTHING_FACTOR",
    "MAX_POWER_STEP_W", "MAX_DISCHARGE_POWER_W", "MAX_CHARGE_POWER_W",
    "MIN_SOC_PERCENT", "MAX_SOC_PERCENT", "CONTROL_GAIN", "MIN_COMMAND_CHANGE_W",
    "MODE_CHANGE_LOCK_SECONDS", "MANUAL_MODE", "MANUAL_FIXED_DISCHARGE_POWER_W",
    "MANUAL_FIXED_DISCHARGE_TARGET_SOC", "MANUAL_DISCHARGE_AFTER_TARGET",
    "MANUAL_FIXED_CHARGE_POWER_W", "MANUAL_FIXED_CHARGE_TARGET_SOC",
    "MANUAL_CHARGE_AFTER_TARGET", "CROSS_CHARGE_ENABLED", "SMA_DISCHARGE_BLOCK_W",
    "CROSS_CHARGE_RESERVE_W", "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W",
    "SMA_GUARD_RAMP_DOWN_W", "SECOND_BATTERY_STALE_TIMEOUT_SECONDS",
    "SECOND_BATTERY_STALE_BLOCK_CHARGE", "NIGHT_DISCHARGE_ENABLED",
    "NIGHT_START_HOUR", "NIGHT_START_MINUTE", "NIGHT_END_HOUR", "NIGHT_END_MINUTE",
    "NIGHT_DISCHARGE_POWER_W", "NIGHT_DISCHARGE_STOP_SOC_PERCENT",
    "SHELLY_STALE_TIMEOUT_SECONDS", "SOC_STALE_TIMEOUT_SECONDS",
    "MQTT_DISCONNECTED_SAFE_STATE", "ZENDURE_POWER_STALE_TIMEOUT_SECONDS",
    "SAFE_STATE_ON_SHELLY_ERROR",
    "COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS", "COMMAND_RESYNC_STALE_MIN_SECONDS",
    "COMMAND_RESYNC_STALE_MIN_CYCLES", "COMMAND_RESYNC_COOLDOWN_SECONDS",
    "COMMAND_EFFECT_MIN_TARGET_W", "COMMAND_EFFECT_MIN_W", "COMMAND_EFFECT_TOLERANCE_W",
    "COMMAND_EFFECT_TOLERANCE_PERCENT",
    "COMMAND_EFFECT_TIMEOUT_SECONDS", "COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS",
    "COMMAND_EFFECT_FORCE_RESEND_SECONDS",
    "REST_SURPLUS_HARVEST_ENABLED", "SECOND_BATTERY_MAX_CHARGE_POWER_W",
    "REST_SURPLUS_MIN_EXPORT_W", "REST_SURPLUS_ENTRY_CONFIRM_SECONDS",
    "SECOND_BATTERY_CHARGE_SATURATION_MARGIN_W",
    "GRID_METER_SOURCE", "SMA_ENERGY_METER_GROUP", "SMA_ENERGY_METER_PORT",
    "SMA_ENERGY_METER_INTERFACE", "SMA_ENERGY_METER_SUSY_ID",
    "SMA_ENERGY_METER_SERIAL", "SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS",
]


def measurement_log_mode(config: Dict[str, Any]) -> str:
    mode = str(config.get("MEASUREMENT_LOG_MODE", "")).strip().lower()
    if mode in {"off", "standard", "extended"}:
        return mode
    return "standard" if bool(config.get("CSV_LOG_ENABLED", False)) else "off"


def measurement_profile(config: Dict[str, Any]) -> str:
    mode = measurement_log_mode(config)
    return "extended" if mode == "extended" else "standard"


def measurement_schema_version(config: Dict[str, Any]) -> str:
    """Return the fixed productive Measurement schema version.

    V12.13.0 removes runtime schema selection. The configuration marker is
    retained only for migration/rollback compatibility and is normalized to 4.
    """
    return "4"


def compute_config_control_hash(config: Dict[str, Any]) -> str:
    relevant = {key: config.get(key) for key in CONTROL_HASH_KEYS if key in config}
    payload = json.dumps(relevant, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _bool_text(value: Any) -> Any:
    if isinstance(value, bool):
        return "1" if value else "0"
    return value


def _json_compact(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return str(value)


def _serialized_row_length(row: Dict[str, Any]) -> int:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=GRAPH_EXPORT_FIELDS, extrasaction="ignore", delimiter=";")
    writer.writerow({field: row.get(field, "") for field in GRAPH_EXPORT_FIELDS})
    return len(buffer.getvalue().encode("utf-8"))


def estimate_retention_hours(config: Dict[str, Any], row_size_bytes: Optional[int] = None) -> Optional[float]:
    row_size = max(1, int(row_size_bytes or config.get("MEASUREMENT_LOG_ESTIMATED_ROW_BYTES", 4096)))
    max_bytes = int(config.get("MEASUREMENT_LOG_MAX_BYTES", config.get("CSV_LOG_MAX_BYTES", 2_000_000)))
    backup_count = int(config.get("MEASUREMENT_LOG_BACKUP_COUNT", config.get("CSV_LOG_BACKUP_COUNT", 5)))
    interval_s = max(1.0, float(config.get("INTERVAL_SECONDS", 3)))
    total_bytes = max_bytes * max(1, backup_count)
    rows = total_bytes / row_size
    return round(rows * interval_s / 3600.0, 2)


def _is_mountpoint(path: str) -> bool:
    try:
        return os.path.ismount(path)
    except Exception:
        return False


def _check_writable_dir(path: str) -> Dict[str, Any]:
    """Return an operational filesystem diagnosis for a log directory.

    This is intentionally runtime/operational metadata, not measurement data.
    Callers may expose it on the status page or write it to zendure_runtime.log,
    but it must not expand the persistent Measurement-V4 row contract.
    """
    result: Dict[str, Any] = {
        "path": path,
        "exists": False,
        "writable": False,
        "free_mb": None,
        "exception": "",
    }
    try:
        result["exists"] = os.path.exists(path)
        os.makedirs(path, exist_ok=True)
        result["exists"] = os.path.exists(path)
        try:
            usage = shutil.disk_usage(path)
            result["free_mb"] = int(usage.free / 1024 / 1024)
        except Exception:
            result["free_mb"] = None
        test_path = os.path.join(path, ".zec_write_test")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_path)
        result["writable"] = True
        return result
    except Exception as exc:
        result["exception"] = str(exc)
        return result


def _is_writable_dir(path: str) -> bool:
    return bool(_check_writable_dir(path).get("writable"))


def detected_log_mounts() -> List[Dict[str, Any]]:
    """Return mountpoints that are plausible user-selectable log targets."""
    mounts: List[Dict[str, Any]] = []
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return mounts
    seen = set()
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mountpoint, fstype = parts[:3]
        if mountpoint in seen:
            continue
        if fstype in {"proc", "sysfs", "tmpfs", "devtmpfs", "devpts", "overlay", "squashfs", "cgroup", "cgroup2", "securityfs", "pstore", "debugfs", "tracefs", "fusectl"}:
            continue
        plausible = (
            device.startswith("/dev/sd")
            or device.startswith("/dev/disk/")
            or mountpoint.startswith("/media/")
            or mountpoint.startswith("/mnt/")
        )
        if not plausible:
            continue
        try:
            usage = shutil.disk_usage(mountpoint)
            free_mb = int(usage.free / 1024 / 1024)
            total_mb = int(usage.total / 1024 / 1024)
        except Exception:
            free_mb = total_mb = None
        mounts.append({
            "device": device,
            "mountpoint": mountpoint,
            "fstype": fstype,
            "free_mb": free_mb,
            "total_mb": total_mb,
            "writable": os.access(mountpoint, os.W_OK),
        })
        seen.add(mountpoint)
    return mounts


def _external_subdir(config: Dict[str, Any]) -> str:
    """Return the configured sub-directory used below an external mountpoint.

    For external_mount, MEASUREMENT_LOG_DIR is intentionally interpreted as a
    sub-directory on the selected mountpoint. Leading slashes are stripped so a
    mistaken absolute-looking value cannot escape the selected USB target.
    """
    raw = str(config.get("MEASUREMENT_LOG_DIR", config.get("CSV_LOG_DIR", "logs")) or "logs").strip()
    if not raw:
        raw = "logs"
    return raw.lstrip(os.sep)


def _select_external_mountpoint(config: Dict[str, Any]) -> Tuple[str, str]:
    """Return (mountpoint, reason) for external_mount logging.

    A manually configured writable mountpoint wins. If it is empty or invalid,
    the first detected writable external mount is used. This matches the UI
    wording "erkannter USB-/Mountpoint" and avoids requiring the user to copy
    an auto-detected path into a second field.
    """
    manual = str(config.get("MEASUREMENT_LOG_MOUNTPOINT", "") or "").strip()
    if manual and _is_mountpoint(manual) and os.access(manual, os.W_OK):
        return manual, f"external_mount:{manual}"
    chosen = next((m for m in detected_log_mounts() if m.get("writable")), None)
    if chosen:
        mountpoint = str(chosen["mountpoint"])
        return mountpoint, f"external_auto:{mountpoint}"
    return "", "external_unavailable"


def resolve_log_target(config: Dict[str, Any], *, allow_fallback: bool = True) -> Dict[str, Any]:
    """Resolve the active measurement log target with runtime diagnostics.

    The detailed target diagnosis is operational state for status/runtime logging.
    The measurement CSV schema remains unchanged; callers should not add these
    details as per-row measurement fields.
    """
    target = str(config.get("MEASUREMENT_LOG_STORAGE_TARGET", "internal_sd") or "internal_sd").strip().lower()
    log_file = str(config.get("MEASUREMENT_LOG_FILE", config.get("CSV_LOG_FILE", "zendure_measurements.csv")) or "zendure_measurements.csv")

    def absolute_join(directory: str) -> str:
        return os.path.abspath(os.path.join(str(directory or "logs"), log_file))

    primary_reason = "primary"
    primary_dir = str(config.get("MEASUREMENT_LOG_DIR", config.get("CSV_LOG_DIR", "logs")) or "logs")
    selected_mountpoint = ""
    selected_mount_is_mount = False
    selected_mount_writable = False

    if target == "external_mount":
        manual = str(config.get("MEASUREMENT_LOG_MOUNTPOINT", "") or "").strip()
        mountpoint, primary_reason = _select_external_mountpoint(config)
        selected_mountpoint = mountpoint or manual
        selected_mount_is_mount = bool(selected_mountpoint and _is_mountpoint(selected_mountpoint))
        selected_mount_writable = bool(selected_mountpoint and os.access(selected_mountpoint, os.W_OK))
        if mountpoint:
            # Variante A: final path = mountpoint + configured measurement directory + file.
            primary_dir = os.path.join(mountpoint, _external_subdir(config))
        else:
            primary_dir = ""
    elif target == "custom_path":
        primary_reason = "custom_path"
    else:
        primary_dir = str(config.get("MEASUREMENT_LOG_DIR", "logs") or "logs")
        primary_reason = "internal_sd"

    primary_path = absolute_join(primary_dir) if primary_dir else ""
    primary_directory = os.path.dirname(primary_path) if primary_path else ""
    primary_check = _check_writable_dir(primary_directory) if primary_directory else {
        "path": primary_directory, "exists": False, "writable": False, "free_mb": None, "exception": ""
    }

    failure_reason = ""
    if target == "external_mount" and not primary_dir:
        failure_reason = "external_mount_unavailable"
    elif primary_path and not primary_check.get("writable"):
        failure_reason = "primary_not_writable"
    elif not primary_path:
        failure_reason = "primary_unavailable"

    result: Dict[str, Any] = {
        "path": primary_path,
        "fallback_active": False,
        "status_reason": primary_reason if not failure_reason else f"unavailable:{primary_reason}",
        "target_type": target,
        "active_target_type": target,
        "primary_path": primary_path,
        "primary_directory": primary_directory,
        "primary_mountpoint": selected_mountpoint,
        "primary_exists": bool(primary_check.get("exists")),
        "primary_is_mount": selected_mount_is_mount if target == "external_mount" else _is_mountpoint(primary_directory),
        "primary_writable": bool(primary_check.get("writable")),
        "primary_free_mb": primary_check.get("free_mb"),
        "primary_failure_reason": failure_reason,
        "primary_exception": primary_check.get("exception", ""),
        "fallback_path": "",
        "fallback_writable": False,
        "fallback_exception": "",
    }

    if primary_path and primary_check.get("writable"):
        result["status_reason"] = primary_reason
        return result

    if allow_fallback and bool(config.get("MEASUREMENT_LOG_ALLOW_SD_FALLBACK", True)) and target in {"external_mount", "custom_path"}:
        fallback_dir = str(config.get("MEASUREMENT_LOG_FALLBACK_DIR", "logs/fallback") or "logs/fallback")
        fallback_path = absolute_join(fallback_dir)
        fallback_directory = os.path.dirname(fallback_path)
        fallback_check = _check_writable_dir(fallback_directory)
        result["fallback_path"] = fallback_path
        result["fallback_writable"] = bool(fallback_check.get("writable"))
        result["fallback_exception"] = fallback_check.get("exception", "")
        if fallback_check.get("writable"):
            result["path"] = fallback_path
            result["fallback_active"] = True
            result["active_target_type"] = "fallback_sd"
            result["status_reason"] = f"fallback_sd_active:{primary_reason}:{failure_reason or 'primary_unavailable'}"
            return result

    # Return primary path if available so status messages point to the intended target.
    result["path"] = primary_path or absolute_join(str(config.get("MEASUREMENT_LOG_FALLBACK_DIR", "logs/fallback")))
    result["active_target_type"] = "unavailable"
    result["status_reason"] = f"unavailable:{primary_reason}:{failure_reason or 'primary_unavailable'}"
    return result


def resolve_log_path(config: Dict[str, Any], *, allow_fallback: bool = True) -> Tuple[str, bool, str]:
    """Resolve the active measurement log path.

    Returns (path, fallback_active, status_reason). The fallback is deliberately
    limited to SD and visible through status/runtime diagnostics; it is not silent.
    """
    target = resolve_log_target(config, allow_fallback=allow_fallback)
    return str(target.get("path") or ""), bool(target.get("fallback_active")), str(target.get("status_reason") or "")


class CsvRotatingLogger:
    """V4-only Measurement facade plus independent SQLite graph queue.

    Since V12.13.0 the productive controller has no Legacy-V3 writer or schema
    fallback. ``MEASUREMENT_LOG_MODE`` controls only off/standard/extended V4.
    Historical V3 reading remains isolated in offline tools.
    """

    def __init__(self) -> None:
        self._v4_logger = None
        self._db_writer = None

    def _ensure_v4_logger(self):
        if self._v4_logger is None:
            from measurement_v4 import MeasurementV4Logger
            self._v4_logger = MeasurementV4Logger()
        return self._v4_logger

    def close(self) -> None:
        if self._v4_logger is not None:
            try:
                self._v4_logger.close()
            except Exception:
                pass
        if self._db_writer is not None:
            try:
                self._db_writer.close()
            except Exception:
                pass

    def _enqueue_measurement_db(self, config: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        """Queue one row for the independent SQLite graph store.

        The queue remains non-blocking and independent of CSV logging mode.
        """
        try:
            if self._db_writer is None:
                from measurement_db import MeasurementDbWriter
                self._db_writer = MeasurementDbWriter()
            return self._db_writer.enqueue(config, row)
        except Exception as exc:
            return {
                "measurement_db_status": "error",
                "measurement_db_reason": str(exc),
                "measurement_db_error": str(exc),
            }

    @staticmethod
    def _merge_db_status(status: Dict[str, Any], db_status: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(status or {})
        merged.update(db_status or {})
        return merged

    def log(self, config: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        db_status = self._enqueue_measurement_db(config, row)
        v4_status = self._ensure_v4_logger().log(config, row)
        return self._merge_db_status(v4_status, db_status)

    def write_runtime_event(self, config: Dict[str, Any], event: Dict[str, Any]) -> None:
        """Best-effort V4 runtime event hook used by asynchronous diagnostics."""
        self._ensure_v4_logger().write_runtime_event(config, event)

    def get_current_path(self, config: Dict[str, Any]) -> str:
        return self._ensure_v4_logger().get_current_path(config)

    def get_current_dir(self, config: Dict[str, Any]) -> str:
        path = self.get_current_path(config)
        return os.path.dirname(path) if path else ""

def rows_to_csv(rows: Iterable[Dict[str, Any]]) -> str:
    """Serialize the in-memory graph history as a graph export, not Measurement.

    The endpoint intentionally keeps its historical filename for compatibility,
    but the content is explicitly identified as ZEC-GRAPH-EXPORT-V1.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=GRAPH_EXPORT_FIELDS, extrasaction="ignore", delimiter=";")
    writer.writerow(CSV_HEADER_MAP)
    for row in rows:
        out_row = dict(row)
        out_row["schema"] = GRAPH_EXPORT_SCHEMA
        out_row["schema_version"] = GRAPH_EXPORT_SCHEMA_VERSION
        writer.writerow({field: _bool_text(out_row.get(field, "")) for field in GRAPH_EXPORT_FIELDS})
    return buffer.getvalue()
