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

from version import APP_VERSION, APP_VERSION_LABEL, CSV_SCHEMA

# ZEC-MEASUREMENT-V3: bewusst maschinenlesbare Spaltennamen.
# Trennzeichen: Semikolon. Dezimalzeichen: Punkt.
# Eine Zeile = ein Controller-Zyklus. Standard und Extended verwenden denselben
# Header; im Standard bleiben detaillierte JSON-Felder leer.
CSV_FIELDS: List[str] = [
    # Schema / Zeitbasis
    "schema",
    "schema_version",
    "measurement_profile",
    "measurement_capabilities_json",
    "controller_version",
    "controller_version_label",
    "config_control_hash",
    "cycle_id",
    "loop_counter",
    "date",
    "timestamp",
    "datetime_local",
    "epoch_s",
    "epoch",
    "dt_s",
    "loop_duration_ms",

    # Rohmesswerte Kern
    "raw_grid_power_w",
    "raw_grid_source",
    "raw_grid_age_s",
    "raw_zendure_soc_percent",
    "raw_zendure_soc_source",
    "raw_zendure_soc_age_s",
    "raw_zendure_grid_input_power_w",
    "raw_zendure_pack_input_power_w",
    "raw_zendure_output_home_power_w",
    "raw_zendure_output_pack_power_w",
    "raw_zendure_battery_temperature_c",
    "raw_second_battery_power_w",
    "raw_second_battery_soc_percent",
    "raw_second_battery_capacity_kwh",
    "raw_second_battery_source",
    "raw_second_battery_age_s",

    # Analyse-/UI-Aliasse, damit V3-Dateien mit vorhandener Auswertung lesbar bleiben.
    "raw_grid_power_meaning",
    "grid_power_w",
    "grid_power_meaning",
    "grid_power_available",
    "grid_power_fresh",
    "grid_power_valid",
    "grid_power_used_for_control",
    "grid_power_age_s",
    "grid_power_validity_reason",
    "zendure_target_power_w",
    "zendure_actual_power_w",
    "second_battery_power_w",
    "second_battery_power_meaning",
    "zendure_actual_charge_power_w",
    "zendure_actual_discharge_power_w",
    "zendure_telemetry_source",
    "zendure_api_fallback_active",
    "battery_temperature_c",
    "second_battery_raw_power_w",
    "second_battery_discharge_power_w",
    "second_battery_soc_percent",
    "second_battery_capacity_kwh",
    "second_battery_data_available",
    "second_battery_data_fresh",
    "second_battery_data_valid",
    "effective_export_power_w",

    # Normalisierte Werte / Regler-Eingänge
    "norm_grid_power_w",
    "norm_grid_power_smoothed_w",
    "norm_zendure_soc_percent",
    "norm_zendure_actual_power_w",
    "norm_zendure_actual_charge_power_w",
    "norm_zendure_actual_discharge_power_w",
    "norm_second_battery_power_w",
    "norm_second_battery_discharge_power_w",
    "norm_effective_export_power_w",
    "input_grid_power_used_w",
    "input_grid_power_used_for_control",
    "input_soc_used_percent",
    "input_soc_used_for_control",
    "input_effective_export_used_w",
    "input_effective_export_used_for_control",
    "input_second_battery_power_used_w",
    "input_second_battery_used_for_control",
    "input_mqtt_command_path_used_for_control",

    # Freshness / Validity Kern
    "grid_available",
    "grid_fresh",
    "grid_valid",
    "grid_used_for_control",
    "grid_age_s",
    "grid_validity_reason",
    "soc_available",
    "soc_fresh",
    "soc_valid",
    "soc_used_for_control",
    "soc_age_s",
    "soc_validity_reason",
    "mqtt_command_path_available",
    "mqtt_command_path_fresh",
    "mqtt_command_path_valid",
    "mqtt_command_path_used_for_control",
    "mqtt_command_path_age_s",
    "mqtt_command_path_validity_reason",
    "second_battery_available",
    "second_battery_fresh",
    "second_battery_valid",
    "second_battery_used_for_control",
    "second_battery_age_s",
    "second_battery_validity_reason",

    # Szenario-Basis ohne Zendure-Wirkung
    "scenario_grid_without_zendure_w",
    "scenario_removed_zendure_power_w",
    "scenario_reconstruction_valid",
    "scenario_reconstruction_reason",
    "scenario_includes_sma_effect",
    "scenario_includes_evcc_effect",

    # Reglerentscheidung
    "mode",
    "mode_label",
    "previous_mode",
    "mode_duration_s",
    "control_path",
    "control_path_label",
    "control_action",
    "control_reason",
    "control_data_quality",
    "control_required_sources",
    "control_missing_required_sources",
    "deadband_active",
    "cross_charge_guard_active",
    "night_discharge_window_active",
    "night_discharge_base_active",
    "night_discharge_reserve_active",
    "min_soc_limiter_active",
    "max_soc_limiter_active",
    "safe_state_active",
    "target_limiters_summary",
    "night_discharge_stop_soc_percent",
    "night_discharge_stop_reason",

    # Sollwert-Kaskade
    "target_raw_w",
    "target_after_deadband_w",
    "target_after_cross_charge_w",
    "target_after_soc_limits_w",
    "target_after_smoothing_w",
    "target_after_ramp_w",
    "target_final_w",
    "target_final_reason",

    # Tatsächlich gesendetes MQTT-Kommando
    "mqtt_command_required",
    "mqtt_command_sent",
    "mqtt_command_skipped",
    "mqtt_command_skip_reason",
    "mqtt_command_signed_target_w",
    "mqtt_command_input_limit_w",
    "mqtt_command_output_limit_w",
    "mqtt_commands_sent_total",
    "mqtt_commands_sent_in_cycle",
    "mqtt_command_result",
    "mqtt_command_sequence",
    "mqtt_last_command",
    "mqtt_last_command_skipped",

    # Zendure-MQTT Live/Retained/Stale Aggregatdiagnose (Standard)
    "zendure_mqtt_overall_status",
    "zendure_mqtt_status_reason",
    "zendure_mqtt_connected",
    "zendure_mqtt_live_confirmed",
    "zendure_mqtt_retained_only",
    "zendure_mqtt_partial_stale",
    "zendure_mqtt_after_broker_restart_no_live_updates",
    "zendure_mqtt_critical_data_age_s",
    "zendure_mqtt_last_live_epoch_s",
    "zendure_mqtt_last_received_epoch_s",
    "zendure_mqtt_missing_critical_groups",
    "zendure_mqtt_stale_critical_groups",

    # Istwirkung Kern
    "actual_zendure_power_w",
    "actual_zendure_power_valid",
    "actual_zendure_power_age_s",
    "actual_target_error_w",
    "actual_target_error_abs_w",
    "command_effect_valid",
    "command_effect_category",
    "command_effect_reason",
    "charge_acceptance_state",
    "charge_acceptance_reason",

    # Logging-/Systemstatus
    "measurement_log_status",
    "measurement_log_status_reason",
    "measurement_estimated_retention_hours",
    "measurement_current_file_size_bytes",
    "measurement_free_disk_mb",
    "last_error",
    "last_error_time",

    # Extended-Detailfelder
    "zendure_mqtt_topic_groups_json",
    "zendure_mqtt_topics_json",
    "zendure_unit_count",
    "zendure_aggregate_target_w",
    "zendure_aggregate_actual_power_w",
    "zendure_aggregate_soc_percent",
    "zendure_aggregate_capacity_kwh",
    "zendure_aggregate_freshness",
    "zendure_units_json",
    "target_limiters_json",
    "control_decision_json",
    "freshness_details_json",
    "zendure_pack_data_json",
    "zendure_raw_topics_snapshot_json",
]

CSV_HEADER_MAP = {field: field for field in CSV_FIELDS}

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
    raw = str(config.get("MEASUREMENT_SCHEMA_VERSION", config.get("MEASUREMENT_LOG_SCHEMA", "3")) or "3").strip().lower()
    if raw in {"4", "v4", "zec4", "zec-measurement-v4"}:
        return "4"
    return "3"


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
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, extrasaction="ignore", delimiter=";")
    writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
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
    but it must not expand the ZEC-MEASUREMENT-V3 row schema.
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
    """CSV-Rotator für ZEC-MEASUREMENT-V3.

    Logging ist optional und nachgelagert. Fehler beim Schreiben werden als
    Status zurückgemeldet und dürfen die Regellogik nicht blockieren.
    """

    def __init__(self) -> None:
        self._last_path = None
        self._validated_v3_paths = set()
        self._invalid_schema_paths: Dict[str, str] = {}
        self._fh = None
        self._writer = None
        self._open_path: Optional[str] = None
        self._rows_since_flush = 0
        self._last_flush_epoch = 0.0
        self._fallback_active_previous = False
        self._fallback_counter_since_start = 0
        self._last_fallback_time = ""
        self._last_fallback_reason = ""
        self._last_fallback_signature = ""
        self._v4_logger = None
        self._db_writer = None

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.flush()
            except Exception:
                pass
            try:
                self._fh.close()
            except Exception:
                pass
        self._fh = None
        self._writer = None
        self._open_path = None
        self._rows_since_flush = 0
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

    def _get_writer(self, path: str):
        write_header = not os.path.exists(path) or os.path.getsize(path) == 0
        if self._fh is None or self._open_path != path or self._fh.closed:
            self.close()
            self._fh = open(path, "a", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(self._fh, fieldnames=CSV_FIELDS, extrasaction="ignore", delimiter=";")
            self._open_path = path
            self._last_flush_epoch = __import__("time").time()
            if write_header:
                self._writer.writerow(CSV_HEADER_MAP)
        return self._writer

    def _flush_if_due(self, config: Dict[str, Any]) -> None:
        if self._fh is None:
            return
        import time
        max_rows = max(1, int(config.get("MEASUREMENT_LOG_FLUSH_EVERY_ROWS", 100)))
        max_seconds = max(1.0, float(config.get("MEASUREMENT_LOG_FLUSH_EVERY_SECONDS", 60)))
        now = time.time()
        if self._rows_since_flush >= max_rows or (now - self._last_flush_epoch) >= max_seconds:
            self._fh.flush()
            self._rows_since_flush = 0
            self._last_flush_epoch = now

    def _enqueue_measurement_db(self, config: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        """Queue one measurement row for the optional SQLite graph store.

        This path is intentionally independent of CSV/V4 logging mode so the
        status/graph UI can keep a lightweight local history even when the
        heavy measurement CSV logging is switched off.  The call is non-blocking
        by design; on queue/full errors the regulator cycle continues.
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

    def _merge_db_status(self, status: Dict[str, Any], db_status: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(status or {})
        merged.update(db_status or {})
        return merged

    def log(self, config: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        if measurement_schema_version(config) == "4":
            db_status = self._enqueue_measurement_db(config, row)
            if self._v4_logger is None:
                from measurement_v4 import MeasurementV4Logger
                self._v4_logger = MeasurementV4Logger()
            return self._merge_db_status(self._v4_logger.log(config, row), db_status)
        mode = measurement_log_mode(config)
        if mode == "off":
            db_status = self._enqueue_measurement_db(config, row)
            return self._merge_db_status(self.status(config, "disabled", "MEASUREMENT_LOG_MODE=off"), db_status)

        # Resolve path/fallback once per cycle and use that same decision for
        # directory checks, rotation, row contents and returned status. This
        # avoids one-cycle-delayed status values and mismatches between USB rows
        # and fallback status fields.
        target_info = resolve_log_target(config, allow_fallback=True)
        path = str(target_info.get("path") or "")
        fallback_active = bool(target_info.get("fallback_active"))
        target_reason = str(target_info.get("status_reason") or "")
        self._last_fallback_active = fallback_active
        self._last_target_reason = target_reason
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)

        free_mb = self._free_disk_mb(directory)
        min_free = int(config.get("MEASUREMENT_LOG_MIN_FREE_DISK_MB", 500))
        if free_mb is not None and free_mb < min_free:
            return self.status(config, "paused_disk_low", f"Freier Speicher unter {min_free} MB", path=path, free_mb=free_mb)

        schema_error = self._active_file_schema_error(path)
        if schema_error:
            return self.status(config, "paused_invalid_schema", schema_error, path=path, free_mb=free_mb)

        fallback_event = False
        if fallback_active:
            signature = f"{target_info.get('primary_path')}|{target_info.get('primary_failure_reason')}|{target_info.get('primary_exception')}"
            if (not self._fallback_active_previous) or signature != self._last_fallback_signature:
                fallback_event = True
                self._fallback_counter_since_start += 1
                self._last_fallback_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._last_fallback_reason = str(target_info.get("primary_failure_reason") or target_reason or "fallback_active")
                self._last_fallback_signature = signature
        self._fallback_active_previous = fallback_active

        status = "active_fallback_sd" if fallback_active else "active"
        if fallback_active:
            reason = f"SD-Fallback aktiv: {self._last_fallback_reason}; primäres Messdatenziel nicht verfügbar, begrenzte Rotation wird verwendet."
        else:
            reason = "OK"
        out_row = self.prepare_row(config, row, path=path, free_mb=free_mb, log_status=status, log_status_reason=reason)
        db_status = self._enqueue_measurement_db(config, out_row)
        row_size = _serialized_row_length(out_row)
        out_row["measurement_estimated_retention_hours"] = estimate_retention_hours(config, row_size)

        self._rotate_if_needed(config, path, fallback_active=fallback_active)
        writer = self._get_writer(path)
        writer.writerow({field: _bool_text(out_row.get(field, "")) for field in CSV_FIELDS})
        self._rows_since_flush += 1
        self._flush_if_due(config)

        return self._merge_db_status(self.status(config, status, reason, path=path, free_mb=free_mb, row_size_bytes=row_size, target_info=target_info, fallback_event=fallback_event), db_status)

    def prepare_row(self, config: Dict[str, Any], row: Dict[str, Any], *, path: Optional[str] = None, free_mb: Optional[int] = None, log_status: str = "active", log_status_reason: str = "OK") -> Dict[str, Any]:
        mode = measurement_log_mode(config)
        profile = "extended" if mode == "extended" else "standard"
        out = dict(row)
        out["schema"] = out.get("schema") or CSV_SCHEMA
        out["schema_version"] = out.get("schema_version") or "3.0"
        out["measurement_profile"] = profile
        out["controller_version"] = out.get("controller_version") or APP_VERSION
        out["controller_version_label"] = out.get("controller_version_label") or APP_VERSION_LABEL
        out["config_control_hash"] = out.get("config_control_hash") or compute_config_control_hash(config)
        out["measurement_capabilities_json"] = out.get("measurement_capabilities_json") or _json_compact({
            "regulator_diagnostics": True,
            "scenario_reconstruction": True,
            "mqtt_stale_aggregate": True,
            "mqtt_topic_details": profile == "extended",
            "packdata_raw": profile == "extended",
            "unit_details": "detailed" if profile == "extended" else "compact",
        })
        out["measurement_current_file_size_bytes"] = os.path.getsize(path) if path and os.path.exists(path) else 0
        out["measurement_free_disk_mb"] = free_mb if free_mb is not None else self._free_disk_mb(os.path.dirname(path) if path else self.get_current_dir(config))
        out["measurement_estimated_retention_hours"] = out.get("measurement_estimated_retention_hours") or estimate_retention_hours(config)
        # Always write the status of this logger decision. Do not preserve stale
        # status fields from the previous controller state row.
        out["measurement_log_status"] = log_status
        out["measurement_log_status_reason"] = log_status_reason

        if profile != "extended":
            for field in (
                "zendure_mqtt_topic_groups_json", "zendure_mqtt_topics_json", "target_limiters_json",
                "control_decision_json", "freshness_details_json", "zendure_pack_data_json",
                "zendure_raw_topics_snapshot_json",
            ):
                out[field] = ""
        return out

    def status(
        self,
        config: Dict[str, Any],
        status: str,
        reason: str,
        *,
        path: Optional[str] = None,
        free_mb: Optional[int] = None,
        row_size_bytes: Optional[int] = None,
        target_info: Optional[Dict[str, Any]] = None,
        fallback_event: bool = False,
    ) -> Dict[str, Any]:
        target_info = target_info or resolve_log_target(config, allow_fallback=True)
        path = path or str(target_info.get("path") or self.get_current_path(config))
        current_size = os.path.getsize(path) if os.path.exists(path) else 0
        return {
            "measurement_log_status": status,
            "measurement_log_status_reason": reason,
            "measurement_estimated_retention_hours": estimate_retention_hours(config, row_size_bytes),
            "measurement_current_file_size_bytes": current_size,
            "measurement_free_disk_mb": free_mb if free_mb is not None else self._free_disk_mb(os.path.dirname(path)),
            "measurement_log_path": path,
            "measurement_log_target_type": target_info.get("target_type", ""),
            "measurement_log_active_target_type": target_info.get("active_target_type", ""),
            "measurement_fallback_active": bool(target_info.get("fallback_active")),
            "measurement_fallback_event": bool(fallback_event),
            "measurement_fallback_count_since_start": self._fallback_counter_since_start,
            "measurement_last_fallback_time": self._last_fallback_time,
            "measurement_last_fallback_reason": self._last_fallback_reason,
            "measurement_primary_path": target_info.get("primary_path", ""),
            "measurement_primary_mountpoint": target_info.get("primary_mountpoint", ""),
            "measurement_primary_exists": target_info.get("primary_exists", ""),
            "measurement_primary_is_mount": target_info.get("primary_is_mount", ""),
            "measurement_primary_writable": target_info.get("primary_writable", ""),
            "measurement_primary_free_mb": target_info.get("primary_free_mb", ""),
            "measurement_primary_failure_reason": target_info.get("primary_failure_reason", ""),
            "measurement_primary_exception": target_info.get("primary_exception", ""),
        }

    def write_runtime_event(self, config: Dict[str, Any], event: Dict[str, Any]) -> None:
        """Best-effort V4 runtime event hook used by asynchronous diagnostics."""
        if measurement_schema_version(config) != "4":
            return
        if self._v4_logger is None:
            from measurement_v4 import MeasurementV4Logger
            self._v4_logger = MeasurementV4Logger()
        self._v4_logger.write_runtime_event(config, event)

    def get_current_path(self, config: Dict[str, Any]) -> str:
        if measurement_schema_version(config) == "4":
            if self._v4_logger is None:
                from measurement_v4 import MeasurementV4Logger
                self._v4_logger = MeasurementV4Logger()
            return self._v4_logger.get_current_path(config)
        path, fallback_active, reason = resolve_log_path(config, allow_fallback=True)
        self._last_fallback_active = fallback_active
        self._last_target_reason = reason
        return path

    def get_current_dir(self, config: Dict[str, Any]) -> str:
        return os.path.dirname(self.get_current_path(config))


    def _active_file_schema_error(self, path: str) -> str:
        """Validate the active file once before appending.

        This is a generic safety guard, not a V2 migration/cleanup path. It
        prevents mixing V3 rows into an existing file with an incompatible
        header while avoiding per-write header checks.
        """
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            self._invalid_schema_paths.pop(path, None)
            return ""
        if path in self._invalid_schema_paths:
            return self._invalid_schema_paths[path]
        if path in self._validated_v3_paths:
            return ""
        try:
            with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                first = f.readline().strip()
        except Exception as exc:
            reason = f"Aktive Messdatei konnte nicht geprüft werden: {exc}"
            self._invalid_schema_paths[path] = reason
            return reason
        fields = [part.strip() for part in first.split(";")]
        required = {"schema", "schema_version", "measurement_profile", "scenario_grid_without_zendure_w"}
        if fields and fields[0] == "schema" and required.issubset(set(fields)):
            self._validated_v3_paths.add(path)
            return ""
        reason = "Messdaten-Logging pausiert: vorhandene Datei entspricht nicht dem gültigen ZEC-MEASUREMENT-V3-Header. Datei prüfen/löschen oder neuen Dateinamen wählen."
        self._invalid_schema_paths[path] = reason
        return reason

    def _free_disk_mb(self, directory: str) -> Optional[int]:
        try:
            os.makedirs(directory, exist_ok=True)
            usage = shutil.disk_usage(directory)
            return int(usage.free / 1024 / 1024)
        except Exception:
            return None

    def _rotate_if_needed(self, config: Dict[str, Any], path: str, *, fallback_active: bool = False) -> None:
        if fallback_active:
            max_bytes = int(config.get("MEASUREMENT_LOG_FALLBACK_MAX_BYTES", 10_000_000))
            backup_count = int(config.get("MEASUREMENT_LOG_FALLBACK_BACKUP_COUNT", 2))
        else:
            max_bytes = int(config.get("MEASUREMENT_LOG_MAX_BYTES", config.get("CSV_LOG_MAX_BYTES", 2_000_000)))
            backup_count = int(config.get("MEASUREMENT_LOG_BACKUP_COUNT", config.get("CSV_LOG_BACKUP_COUNT", 5)))

        if not os.path.exists(path) or os.path.getsize(path) < max_bytes:
            return

        if self._open_path == path:
            self.close()

        for index in range(backup_count, 0, -1):
            src = self._backup_path(path, index)
            dst = self._backup_path(path, index + 1)
            if index == backup_count and os.path.exists(src):
                os.remove(src)
            elif os.path.exists(src):
                os.replace(src, dst)

        os.replace(path, self._backup_path(path, 1))

    def _backup_path(self, path: str, index: int) -> str:
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        stem, ext = os.path.splitext(filename)
        return os.path.join(directory, f"{stem}_{index}{ext}")


def rows_to_csv(rows: Iterable[Dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, extrasaction="ignore", delimiter=";")
    writer.writerow(CSV_HEADER_MAP)
    for row in rows:
        out_row = dict(row)
        out_row["schema"] = out_row.get("schema") or CSV_SCHEMA
        out_row["schema_version"] = out_row.get("schema_version") or "3.0"
        writer.writerow({field: _bool_text(out_row.get(field, "")) for field in CSV_FIELDS})
    return buffer.getvalue()
