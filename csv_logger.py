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
from typing import Any, Dict, Iterable, List, Optional

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
]


def measurement_log_mode(config: Dict[str, Any]) -> str:
    mode = str(config.get("MEASUREMENT_LOG_MODE", "")).strip().lower()
    if mode in {"off", "standard", "extended"}:
        return mode
    return "standard" if bool(config.get("CSV_LOG_ENABLED", False)) else "off"


def measurement_profile(config: Dict[str, Any]) -> str:
    mode = measurement_log_mode(config)
    return "extended" if mode == "extended" else "standard"


def compute_config_control_hash(config: Dict[str, Any]) -> str:
    relevant = {key: config.get(key) for key in CONTROL_HASH_KEYS if key in config}
    payload = json.dumps(relevant, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _bool_text(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
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


class CsvRotatingLogger:
    """CSV-Rotator für ZEC-MEASUREMENT-V3.

    Logging ist optional und nachgelagert. Fehler beim Schreiben werden als
    Status zurückgemeldet und dürfen die Regellogik nicht blockieren.
    """

    def __init__(self) -> None:
        self._last_path = None

    def log(self, config: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        mode = measurement_log_mode(config)
        if mode == "off":
            return self.status(config, "disabled", "MEASUREMENT_LOG_MODE=off")

        path = self.get_current_path(config)
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)

        free_mb = self._free_disk_mb(directory)
        min_free = int(config.get("MEASUREMENT_LOG_MIN_FREE_DISK_MB", 500))
        if free_mb is not None and free_mb < min_free:
            return self.status(config, "paused_disk_low", f"Freier Speicher unter {min_free} MB", path=path, free_mb=free_mb)

        out_row = self.prepare_row(config, row, path=path, free_mb=free_mb)
        row_size = _serialized_row_length(out_row)
        out_row["measurement_estimated_retention_hours"] = estimate_retention_hours(config, row_size)

        self._rotate_if_needed(config, path)
        write_header = not os.path.exists(path) or os.path.getsize(path) == 0

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore", delimiter=";")
            if write_header:
                writer.writerow(CSV_HEADER_MAP)
            writer.writerow({field: _bool_text(out_row.get(field, "")) for field in CSV_FIELDS})

        return self.status(config, "active", "OK", path=path, free_mb=free_mb, row_size_bytes=row_size)

    def prepare_row(self, config: Dict[str, Any], row: Dict[str, Any], *, path: Optional[str] = None, free_mb: Optional[int] = None) -> Dict[str, Any]:
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
        out["measurement_log_status"] = out.get("measurement_log_status") or "active"
        out["measurement_log_status_reason"] = out.get("measurement_log_status_reason") or "OK"

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
    ) -> Dict[str, Any]:
        path = path or self.get_current_path(config)
        current_size = os.path.getsize(path) if os.path.exists(path) else 0
        return {
            "measurement_log_status": status,
            "measurement_log_status_reason": reason,
            "measurement_estimated_retention_hours": estimate_retention_hours(config, row_size_bytes),
            "measurement_current_file_size_bytes": current_size,
            "measurement_free_disk_mb": free_mb if free_mb is not None else self._free_disk_mb(os.path.dirname(path)),
            "measurement_log_path": path,
        }

    def get_current_path(self, config: Dict[str, Any]) -> str:
        log_dir = str(config.get("MEASUREMENT_LOG_DIR", config.get("CSV_LOG_DIR", "logs")))
        log_file = str(config.get("MEASUREMENT_LOG_FILE", config.get("CSV_LOG_FILE", "zendure_measurements.csv")))
        return os.path.abspath(os.path.join(log_dir, log_file))

    def get_current_dir(self, config: Dict[str, Any]) -> str:
        return os.path.dirname(self.get_current_path(config))

    def _free_disk_mb(self, directory: str) -> Optional[int]:
        try:
            os.makedirs(directory, exist_ok=True)
            usage = shutil.disk_usage(directory)
            return int(usage.free / 1024 / 1024)
        except Exception:
            return None

    def _rotate_if_needed(self, config: Dict[str, Any], path: str) -> None:
        max_bytes = int(config.get("MEASUREMENT_LOG_MAX_BYTES", config.get("CSV_LOG_MAX_BYTES", 2_000_000)))
        backup_count = int(config.get("MEASUREMENT_LOG_BACKUP_COUNT", config.get("CSV_LOG_BACKUP_COUNT", 5)))

        if not os.path.exists(path) or os.path.getsize(path) < max_bytes:
            return

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
