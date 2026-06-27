# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# ZEC-MEASUREMENT-V4 runtime writer. The writer is intentionally separate from
# the legacy V3 csv_logger field list so V3 can remain available during the V12.10 release-candidate phase.

import csv
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from csv_logger import compute_config_control_hash, estimate_retention_hours, measurement_log_mode, resolve_log_target
from measurement_v4_contract import (
    EXTENDED_FIELDS,
    MISSING_REQUIRED_SOURCE_BITS,
    ROTATION_REASON_VALUES,
    STANDARD_HEADER,
    ZENDURE_MQTT_GROUP_BITS,
    header_for_profile,
    header_hash,
)
from version import APP_VERSION

CONTROL_SNAPSHOT_KEYS = [
    "MAX_CHARGE_POWER_W", "MAX_DISCHARGE_POWER_W", "MIN_SOC_PERCENT", "MAX_SOC_PERCENT",
    "MIN_COMMAND_CHANGE_W", "NIGHT_DISCHARGE_ENABLED", "NIGHT_DISCHARGE_POWER_W",
    "NIGHT_DISCHARGE_START", "NIGHT_DISCHARGE_END", "NIGHT_DISCHARGE_STOP_SOC_PERCENT",
    "NIGHT_START_HOUR", "NIGHT_START_MINUTE", "NIGHT_END_HOUR", "NIGHT_END_MINUTE",
    "CROSS_CHARGE_SIGNIFICANT_W", "SMA_DISCHARGE_BLOCK_W", "CROSS_CHARGE_ENABLED",
    "CROSS_CHARGE_RESERVE_W", "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W", "SECOND_BATTERY_ENABLED",
    "SECOND_BATTERY_SOURCE_PROFILE", "SECOND_BATTERY_DISCHARGE_SIGN", "SECOND_BATTERY_STALE_BLOCK_CHARGE",
    "REST_SURPLUS_HARVEST_ENABLED", "SECOND_BATTERY_MAX_CHARGE_POWER_W",
    "REST_SURPLUS_MIN_EXPORT_W", "REST_SURPLUS_ENTRY_CONFIRM_SECONDS",
    "SECOND_BATTERY_CHARGE_SATURATION_MARGIN_W",
]

MQTT_GROUP_ALIASES = {
    "soc": "ZENDURE_SOC",
    "headunit_power": "ZENDURE_HEADUNIT_POWER",
    "pack_data": "ZENDURE_PACK_DATA",
    "packdata": "ZENDURE_PACK_DATA",
    "limit_state": "ZENDURE_LIMIT_STATE",
    "device_state": "ZENDURE_DEVICE_STATE",
    "command_feedback": "ZENDURE_COMMAND_FEEDBACK",
    "temperature": "ZENDURE_TEMPERATURES",
    "temperatures": "ZENDURE_TEMPERATURES",
}

MISSING_SOURCE_ALIASES = {
    "grid": "GRID_POWER",
    "grid_power": "GRID_POWER",
    "soc": "ZENDURE_SOC",
    "zendure_soc": "ZENDURE_SOC",
    "mqtt_command_path": "ZENDURE_MQTT_COMMAND_PATH",
    "zendure_actual_power": "ZENDURE_ACTUAL_POWER",
    "second_battery": "SECOND_BATTERY_POWER",
    "second_battery_power": "SECOND_BATTERY_POWER",
    "pv": "PV_POWER",
    "pv_power": "PV_POWER",
    "house": "HOUSE_POWER",
    "house_power": "HOUSE_POWER",
    "config": "CONFIG_CONTROL",
    "config_control": "CONFIG_CONTROL",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


def _round1(value: Any) -> Any:
    number = _safe_float(value)
    if number is None:
        return ""
    return round(number, 1)


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return ""

def _bool01(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "ja", "on"}:
            return "1"
        if lowered in {"0", "false", "no", "nein", "off"}:
            return "0"
        return ""
    return "1" if bool(value) else "0"


def _json_compact(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _canonical_source(value: Any, *, second_battery: bool = False) -> str:
    raw = str(value or "").strip().upper()
    if second_battery:
        profile = str(value or "").strip().lower()
        if profile == "evcc_standard" or "EVCC" in raw:
            return "EVCC_STANDARD"
        if profile == "evcc_custom":
            return "EVCC_CUSTOM"
        if "SMA" in raw:
            return "SMA"
        if raw in {"NONE", "DISABLED", ""}:
            return "DISABLED"
        return "UNKNOWN"
    if "UNIMETER" in raw or "UNI-METER" in raw:
        return "UNIMETER"
    if "SHELLY" in raw:
        return "SHELLY"
    if "EVCC" in raw:
        return "EVCC"
    if "SMA" in raw:
        return "SMA"
    if "MQTT" in raw or "ZENDURE" in raw:
        return "ZENDURE_MQTT"
    if raw in {"CONFIG", "DERIVED", "DISABLED"}:
        return raw
    if raw in {"NONE", "", "-"}:
        return "DISABLED"
    return "UNKNOWN"


def _csv_list(value: Any) -> List[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _mask_from_names(names: Iterable[str], aliases: Dict[str, str], bits: Dict[str, int]) -> Tuple[int, int]:
    mask = 0
    count = 0
    seen = set()
    for name in names:
        key = aliases.get(str(name).strip().lower(), str(name).strip().upper())
        if key in bits and key not in seen:
            mask |= bits[key]
            count += 1
            seen.add(key)
    return mask, count


def _v4_filename(config: Dict[str, Any]) -> str:
    name = str(config.get("MEASUREMENT_LOG_FILE", "zendure_measurements.csv") or "zendure_measurements.csv")
    if name == "zendure_measurements.csv":
        return "zendure_measurements_v4.csv"
    return name


def _v4_target_config(config: Dict[str, Any]) -> Dict[str, Any]:
    cfg = dict(config)
    cfg["MEASUREMENT_LOG_FILE"] = _v4_filename(config)
    return cfg


def _line_epoch(row: Dict[str, Any]) -> Tuple[str, int]:
    epoch = _safe_float(row.get("epoch_s", row.get("epoch")))
    if epoch is None:
        now = datetime.now(timezone.utc)
        return now.isoformat(timespec="milliseconds").replace("+00:00", "Z"), int(now.timestamp() * 1000)
    dt = datetime.fromtimestamp(epoch, timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z"), int(round(epoch * 1000))


def build_config_snapshot(config: Dict[str, Any]) -> Dict[str, Any]:
    control_parameters: Dict[str, Any] = {}
    for key in CONTROL_SNAPSHOT_KEYS:
        if key in config:
            control_parameters[key] = config.get(key)
    # V4 uses the neutral cross-charge term. Existing installations still carry
    # the legacy SMA_* key; expose the new contract key without changing runtime
    # controller behavior in this RC.
    if "CROSS_CHARGE_SIGNIFICANT_W" not in control_parameters and "SMA_DISCHARGE_BLOCK_W" in control_parameters:
        control_parameters["CROSS_CHARGE_SIGNIFICANT_W"] = control_parameters.get("SMA_DISCHARGE_BLOCK_W")
    # Stable derived HH:MM values for easier later reconstruction.
    if "NIGHT_DISCHARGE_START" not in control_parameters:
        control_parameters["NIGHT_DISCHARGE_START"] = f"{int(config.get('NIGHT_START_HOUR', 0)):02d}:{int(config.get('NIGHT_START_MINUTE', 0)):02d}"
    if "NIGHT_DISCHARGE_END" not in control_parameters:
        control_parameters["NIGHT_DISCHARGE_END"] = f"{int(config.get('NIGHT_END_HOUR', 0)):02d}:{int(config.get('NIGHT_END_MINUTE', 0)):02d}"
    return {
        "config_control_hash": compute_config_control_hash(config),
        "schema_version": 4,
        "controller_version": APP_VERSION,
        "created_time_utc": _now_utc(),
        "source": "runtime_config",
        "control_parameters": control_parameters,
    }


def build_v4_row(config: Dict[str, Any], row: Dict[str, Any], previous_effective_command_w: Optional[float] = None) -> Dict[str, Any]:
    measurement_time_utc, epoch_ms = _line_epoch(row)
    mode_raw = str(row.get("mode", "UNKNOWN") or "UNKNOWN")
    target_final = _safe_float(row.get("target_final_w", row.get("zendure_target_power_w")))
    active_limiters = _csv_list(row.get("technical_limiters", row.get("target_limiters_summary")))
    control_reason = str(row.get("control_reason", row.get("target_final_reason", "UNKNOWN")) or "UNKNOWN")
    target_reason = _map_target_reason(control_reason, mode_raw, target_final, active_limiters, row)
    operating_mode = _map_operating_mode(mode_raw, target_reason=target_reason, row=row)
    control_intent = _control_intent(operating_mode, target_final)

    missing_names = _filter_missing_required_sources(_csv_list(row.get("control_missing_required_sources")), config, row)
    missing_mask, missing_count = _mask_from_names(missing_names, MISSING_SOURCE_ALIASES, MISSING_REQUIRED_SOURCE_BITS)

    mqtt_status = _map_mqtt_status(row.get("zendure_mqtt_overall_status"), row)
    missing_mqtt = _csv_list(row.get("zendure_mqtt_missing_critical_groups"))
    stale_mqtt = _csv_list(row.get("zendure_mqtt_stale_critical_groups"))
    missing_mqtt_mask, missing_mqtt_count = _mask_from_names(missing_mqtt, MQTT_GROUP_ALIASES, ZENDURE_MQTT_GROUP_BITS)
    stale_mqtt_mask, stale_mqtt_count = _mask_from_names(stale_mqtt, MQTT_GROUP_ALIASES, ZENDURE_MQTT_GROUP_BITS)

    command_sent = _bool01(row.get("mqtt_command_sent")) == "1"
    command_required = _bool01(row.get("mqtt_command_required")) == "1"
    mqtt_connected = _bool01(row.get("zendure_mqtt_connected"))
    requested_w = target_final if target_final is not None else ""
    command_action, suppressed_reason = _command_action(row, command_sent, command_required, mqtt_connected, target_final, previous_effective_command_w)
    command_sent_w = target_final if command_sent and target_final is not None else ""
    effective_w: Any = ""
    if command_sent and target_final is not None:
        effective_w = target_final
    elif previous_effective_command_w is not None:
        effective_w = previous_effective_command_w
    command_delta: Any = ""
    if target_final is not None and previous_effective_command_w is not None:
        command_delta = round(target_final - previous_effective_command_w, 1)

    scenario_without = _safe_float(row.get("scenario_grid_without_zendure_w"))
    effective_surplus = ""
    if scenario_without is not None:
        effective_surplus = max(0.0, -scenario_without)

    pack_info = _temperature_aggregates(row)
    cycle_duration_ms = _safe_int(row.get("loop_duration_ms"))
    if cycle_duration_ms is None:
        dt_s = _safe_float(row.get("dt_s"))
        cycle_duration_ms = int(round(dt_s * 1000)) if dt_s is not None else None

    v4 = {
        "schema_version": 4,
        "cycle_index": _safe_int(row.get("cycle_id", row.get("loop_counter"))) or "",
        "measurement_time_utc": measurement_time_utc,
        "measurement_epoch_ms": epoch_ms,
        "cycle_duration_ms": cycle_duration_ms if cycle_duration_ms is not None else "",
        "config_control_hash": compute_config_control_hash(config),
        "operating_mode": operating_mode,
        "operating_mode_duration_s": _safe_int(row.get("mode_duration_s")) or "",
        "control_intent": control_intent,
        "control_input_valid": "0" if missing_count else "1",
        "control_missing_required_source_mask": missing_mask,
        "control_missing_required_source_count": missing_count,
        "safe_state_active": "1" if operating_mode == "SAFE_STATE" else "0",
        "safe_state_reason": _safe_state_reason(row, mqtt_status, missing_names, operating_mode),
        "night_window_active": _bool01(row.get("night_discharge_window_active")),
        "control_night_reserve_active": _bool01(row.get("night_discharge_reserve_active")),
        "control_night_exit_neutralized": "1" if target_reason in {"NIGHT_RESERVE_STOP", "NIGHT_WINDOW_ENDED_NEUTRALIZED"} else "0",
        "fixed_mode_active": "1" if operating_mode in {"FIXED_CHARGE", "FIXED_DISCHARGE"} else "0",
        "manual_stop_active": "1" if operating_mode == "STOP_HOLD" else "0",
        "grid_power_raw_w": _round1(row.get("raw_grid_power_w", row.get("raw_grid_power"))),
        "grid_power_w": _round1(row.get("grid_power_w", row.get("grid_power"))),
        "grid_power_valid": _bool01(row.get("grid_power_valid", row.get("grid_valid"))),
        "grid_power_fresh": _bool01(row.get("grid_power_fresh", row.get("grid_fresh"))),
        "grid_power_age_s": _round1(row.get("grid_power_age_s", row.get("raw_grid_age_s"))),
        "grid_power_source": _canonical_source(row.get("raw_grid_source")),
        "pv_power_w": "",
        "pv_power_valid": "",
        "pv_power_fresh": "",
        "pv_power_age_s": "",
        "pv_power_source": "DISABLED",
        "house_power_w": "",
        "house_power_valid": "",
        "house_power_fresh": "",
        "house_power_age_s": "",
        "house_power_source": "DISABLED",
        "zendure_unit_count": _safe_int(row.get("zendure_unit_count")) or 1,
        "zendure_power_raw_w": _round1(row.get("actual_zendure_power_w", row.get("zendure_actual_power_w"))),
        "zendure_actual_power_w": _round1(row.get("actual_zendure_power_w", row.get("zendure_actual_power_w"))),
        "zendure_actual_power_valid": _bool01(row.get("actual_zendure_power_valid")),
        "zendure_actual_power_fresh": _bool01(row.get("actual_zendure_power_valid")),
        "zendure_actual_power_age_s": _round1(row.get("actual_zendure_power_age_s")),
        "zendure_actual_power_source": _canonical_source(row.get("zendure_telemetry_source")),
        "zendure_soc_raw_percent": _round1(row.get("raw_zendure_soc_percent", row.get("zendure_soc_percent"))),
        "zendure_soc_percent": _round1(row.get("norm_zendure_soc_percent", row.get("zendure_soc_percent"))),
        "control_soc_percent": _round1(row.get("input_soc_used_percent", row.get("zendure_soc_percent"))),
        "zendure_soc_valid": _bool01(row.get("soc_valid")),
        "zendure_soc_fresh": _bool01(row.get("soc_fresh")),
        "zendure_soc_age_s": _round1(row.get("soc_age_s", row.get("raw_zendure_soc_age_s"))),
        "zendure_soc_source": _canonical_source(row.get("raw_zendure_soc_source", row.get("zendure_telemetry_source"))),
        "zendure_headunit_temp_c": pack_info.get("headunit_temp_c", ""),
        "zendure_headunit_temp_valid": pack_info.get("headunit_valid", ""),
        "zendure_headunit_temp_age_s": pack_info.get("headunit_age_s", ""),
        "zendure_headunit_temp_source": pack_info.get("headunit_source", "ZENDURE_MQTT"),
        "zendure_battery_temp_max_c": pack_info.get("pack_max_temp_c", ""),
        "zendure_battery_temp_min_c": pack_info.get("pack_min_temp_c", ""),
        "zendure_battery_temp_pack_count": pack_info.get("pack_count", ""),
        "zendure_battery_temp_max_pack_id": pack_info.get("max_pack_id", ""),
        "zendure_battery_temp_valid": pack_info.get("pack_valid", ""),
        "zendure_battery_temp_age_s": pack_info.get("pack_age_s", ""),
        "zendure_battery_temp_source": pack_info.get("pack_source", "ZENDURE_MQTT"),
        "zendure_mqtt_status": mqtt_status,
        "zendure_mqtt_live_confirmed": _bool01(row.get("zendure_mqtt_live_confirmed")),
        "zendure_mqtt_critical_data_age_s": _round1(row.get("zendure_mqtt_critical_data_age_s")),
        "zendure_mqtt_missing_group_mask": missing_mqtt_mask,
        "zendure_mqtt_missing_group_count": missing_mqtt_count,
        "zendure_mqtt_stale_group_mask": stale_mqtt_mask,
        "zendure_mqtt_stale_group_count": stale_mqtt_count,
        "zendure_mqtt_retained_only": _bool01(row.get("zendure_mqtt_retained_only")),
        "zendure_mqtt_after_broker_restart": _bool01(row.get("zendure_mqtt_after_broker_restart_no_live_updates")),
        "second_battery_power_raw_w": _round1(row.get("raw_second_battery_power_w", row.get("second_battery_raw_power_w"))),
        "second_battery_power_w": _round1(row.get("second_battery_power_w", row.get("norm_second_battery_power_w"))),
        "second_battery_power_valid": _bool01(row.get("second_battery_valid", row.get("second_battery_data_valid"))),
        "second_battery_power_fresh": _bool01(row.get("second_battery_fresh", row.get("second_battery_data_fresh"))),
        "second_battery_power_age_s": _round1(row.get("second_battery_age_s")),
        "second_battery_soc_percent": _round1(row.get("second_battery_soc_percent")),
        "second_battery_soc_valid": _bool01(row.get("second_battery_valid", row.get("second_battery_data_valid"))),
        "second_battery_soc_fresh": _bool01(row.get("second_battery_fresh", row.get("second_battery_data_fresh"))),
        "second_battery_soc_age_s": _round1(row.get("second_battery_age_s")),
        "second_battery_source": _canonical_source(config.get("SECOND_BATTERY_SOURCE_PROFILE", row.get("raw_second_battery_source")), second_battery=True),
        "scenario_grid_without_zendure_w": _round1(scenario_without),
        "scenario_grid_without_zendure_valid": _bool01(row.get("scenario_reconstruction_valid")),
        "scenario_grid_without_zendure_source": "DERIVED",
        "scenario_effective_surplus_w": _round1(effective_surplus),
        "scenario_effective_surplus_valid": _bool01(row.get("scenario_reconstruction_valid")),
        "control_grid_power_w": _round1(_first_non_empty(row.get("input_grid_power_used_w"), row.get("grid_power_w"), row.get("grid_power"))),
        "control_grid_power_smoothed_w": _round1(_first_non_empty(row.get("norm_grid_power_smoothed_w"), row.get("grid_power_w"), row.get("grid_power"))),
        "control_grid_power_smoothed_valid": _bool01(_first_non_empty(row.get("grid_power_used_for_control"), row.get("input_grid_power_used_for_control"))),
        "control_effective_export_w": _round1(_first_non_empty(row.get("input_effective_export_used_w"), row.get("effective_export_power_w"), row.get("effective_export_power"), effective_surplus)),
        "control_effective_export_valid": _bool01(_first_non_empty(row.get("input_effective_export_used_for_control"), row.get("effective_export_power_used_for_control"), row.get("effective_export_power_valid"), row.get("scenario_reconstruction_valid"))),
        "rest_surplus_harvest_active": _bool01(row.get("rest_surplus_harvest_active")),
        "rest_surplus_harvest_eligible": _bool01(row.get("rest_surplus_harvest_eligible")),
        "rest_surplus_entry_progress_s": _round1(row.get("rest_surplus_entry_progress_s")),
        "rest_surplus_exit_reason": str(row.get("rest_surplus_exit_reason", "") or ""),
        "second_battery_charge_pressure_w": _round1(row.get("second_battery_charge_pressure_w")),
        "second_battery_charge_saturation_threshold_w": _round1(row.get("second_battery_charge_saturation_threshold_w")),
        "rest_surplus_export_w": _round1(row.get("rest_surplus_export_w", max(0.0, -(_safe_float(row.get("grid_power_w", row.get("grid_power"))) or 0.0)))),
        "control_deadband_active": _bool01(row.get("deadband_active")),
        "control_cross_charge_detected": "1" if target_reason in {"CROSS_CHARGE_REDUCED", "CROSS_CHARGE_BLOCKED"} else "0",
        "control_cross_charge_limited": "1" if target_reason in {"CROSS_CHARGE_REDUCED", "CROSS_CHARGE_BLOCKED"} else "0",
        "control_mode_change_lock_active": "1" if "MODE_CHANGE" in str(row.get("technical_path", row.get("control_path", ""))).upper() else "0",
        "target_raw_w": _round1(row.get("target_raw_w")),
        "target_filtered_w": _round1(row.get("target_after_smoothing_w", row.get("target_filtered_w"))),
        "target_step_limited_w": _round1(row.get("target_after_ramp_w", row.get("target_step_limited_w"))),
        "target_limited_w": _round1(row.get("target_after_soc_limits_w", row.get("target_limited_w"))),
        "target_final_w": _round1(target_final),
        "target_final_reason": target_reason,
        "target_changed_by_deadband": "1" if "DEADBAND" in control_reason.upper() or _bool01(row.get("deadband_active")) == "1" else "0",
        "target_changed_by_smoothing": "1" if "SMOOTH" in control_reason.upper() or "SMOOTH" in active_limiters else "0",
        "target_changed_by_step_limit": "1" if "RAMP" in control_reason.upper() or "STEP" in control_reason.upper() else "0",
        "target_changed_by_soc_limit": "1" if any(x in active_limiters for x in ("MIN_SOC", "MAX_SOC")) else "0",
        "target_changed_by_power_limit": "1" if any(x in active_limiters for x in ("MAX_CHARGE", "MAX_DISCHARGE", "POWER_LIMIT")) else "0",
        "target_changed_by_cross_charge": "1" if "CROSS_CHARGE" in target_reason else "0",
        "target_changed_by_mode": "1" if operating_mode in {"NIGHT_DISCHARGE", "FIXED_CHARGE", "FIXED_DISCHARGE", "STOP_HOLD"} else "0",
        "target_changed_by_safe_state": "1" if target_reason == "SAFE_STATE" else "0",
        "command_action": command_action,
        "command_requested_w": _round1(requested_w),
        "command_sent_w": _round1(command_sent_w),
        "command_effective_w": _round1(effective_w),
        "command_sent_flag": "1" if command_sent else "0",
        "command_suppressed_reason": suppressed_reason,
        "command_mqtt_connected": mqtt_connected,
        "command_mqtt_success": "1" if command_sent else ("0" if command_action == "FAILED" else ""),
        "command_delta_w": _round1(command_delta),
    }
    # Normalize None to empty strings.
    for key in list(v4.keys()):
        if v4[key] is None:
            v4[key] = ""
    return v4


def build_extended_values(row: Dict[str, Any], v4_row: Dict[str, Any]) -> Dict[str, str]:
    pack_json, headunit_json = _temperature_jsons(row, v4_row)
    mqtt_json = _mqtt_group_status_json(row, v4_row)
    return {
        "zendure_pack_temperatures_json": _json_compact(pack_json) if pack_json else "",
        "zendure_headunit_temperatures_json": _json_compact(headunit_json) if headunit_json else "",
        "zendure_mqtt_group_status_json": _json_compact(mqtt_json) if mqtt_json else "",
    }


def _filter_missing_required_sources(names: List[str], config: Dict[str, Any], row: Dict[str, Any]) -> List[str]:
    """Keep missing-required diagnostics aligned with the V4 contract.

    A stale/missing second battery is only a hard required-source problem when
    the current control path really depends on it. If the stale-block option is
    disabled and no cross-charge guard is active, AUTO must remain diagnosable
    without turning the whole input model invalid just because optional SMA/EVCC
    telemetry is stale.
    """
    filtered: List[str] = []
    stale_block = bool(config.get("SECOND_BATTERY_STALE_BLOCK_CHARGE", config.get("EVCC_STALE_BLOCK_CHARGE", True)))
    cross_charge_active = _bool01(row.get("cross_charge_guard_active")) == "1"
    for name in names:
        canonical = MISSING_SOURCE_ALIASES.get(str(name).strip().lower(), str(name).strip().upper())
        if canonical == "SECOND_BATTERY_POWER" and not stale_block and not cross_charge_active:
            continue
        filtered.append(name)
    return filtered


def _map_operating_mode(mode: str, *, target_reason: str = "", row: Optional[Dict[str, Any]] = None) -> str:
    raw = str(mode or "").upper()
    reason = str((row or {}).get("control_reason", (row or {}).get("target_final_reason", "")) or "").upper()
    # The legacy controller internally uses safe_state() also as a neutralizing
    # helper for SOC limits. In V4 these are target limiters, not fault modes.
    if raw == "SAFE_STATE" and target_reason in {"MAX_SOC_LIMIT", "MIN_SOC_LIMIT"}:
        return "AUTO"
    if raw == "SAFE_STATE" and ("SOC ZU HOCH" in reason or "SOC ZU NIEDRIG" in reason):
        return "AUTO"
    if raw in {"AUTO", "HOLD", "HOLD_DEADBAND", "NIGHT_DISCHARGE", "STOP_HOLD", "SAFE_STATE"}:
        return raw
    if raw in {"MANUAL_FIXED_CHARGE", "FIXED_CHARGE"}:
        return "FIXED_CHARGE"
    if raw in {"MANUAL_FIXED_DISCHARGE", "FIXED_DISCHARGE"}:
        return "FIXED_DISCHARGE"
    if raw in {"CHARGE", "DISCHARGE", "CHARGE_RAMP_DOWN", "DISCHARGE_RAMP_DOWN", "BLOCKED_BY_SMA"}:
        return "AUTO"
    return "UNKNOWN"


def _control_intent(operating_mode: str, target_final: Optional[float]) -> str:
    if operating_mode == "SAFE_STATE":
        return "SAFE"
    if operating_mode in {"HOLD", "HOLD_DEADBAND", "STOP_HOLD"}:
        return "HOLD"
    if target_final is None:
        return "UNKNOWN"
    if target_final > 0:
        return "CHARGE"
    if target_final < 0:
        return "DISCHARGE"
    return "NEUTRAL"


def _map_mqtt_status(value: Any, row: Dict[str, Any]) -> str:
    raw = str(value or "").upper()
    if "AFTER_BROKER_RESTART" in raw:
        return "ZENDURE_MQTT_NO_LIVE"
    if raw in {"ZENDURE_MQTT_OK", "ZENDURE_MQTT_STALE", "ZENDURE_MQTT_PARTIAL_STALE", "ZENDURE_MQTT_RETAINED_ONLY", "ZENDURE_MQTT_NO_LIVE", "ZENDURE_MQTT_UNKNOWN"}:
        return raw
    if raw == "OK":
        return "ZENDURE_MQTT_OK"
    if raw == "STALE":
        return "ZENDURE_MQTT_STALE"
    if bool(row.get("zendure_mqtt_after_broker_restart_no_live_updates")):
        return "ZENDURE_MQTT_NO_LIVE"
    if bool(row.get("zendure_mqtt_partial_stale")):
        return "ZENDURE_MQTT_PARTIAL_STALE"
    if bool(row.get("zendure_mqtt_retained_only")):
        return "ZENDURE_MQTT_RETAINED_ONLY"
    return "ZENDURE_MQTT_UNKNOWN"


def _map_target_reason(reason: str, operating_mode: str, target_final: Optional[float], active_limiters: List[str], row: Dict[str, Any]) -> str:
    raw = str(reason or "").upper()
    upper_limiters = {str(item).upper() for item in active_limiters}
    if operating_mode == "NIGHT_DISCHARGE":
        return "NIGHT_BASE_DISCHARGE"
    stop_reason = str(row.get("night_discharge_stop_reason", "") or "").upper()
    if "RESERVE" in stop_reason:
        return "NIGHT_RESERVE_STOP"
    if "WINDOW" in stop_reason or "ENDED" in stop_reason:
        return "NIGHT_WINDOW_ENDED_NEUTRALIZED"
    if operating_mode == "FIXED_CHARGE":
        return "FIXED_CHARGE"
    if operating_mode == "FIXED_DISCHARGE":
        return "FIXED_DISCHARGE"
    if operating_mode == "STOP_HOLD":
        return "MANUAL_STOP"
    if "MIN_SOC" in raw or "SOC ZU NIEDRIG" in raw or "MIN_SOC" in upper_limiters:
        return "MIN_SOC_LIMIT"
    if "MAX_SOC" in raw or "SOC ZU HOCH" in raw or "MAX_SOC" in upper_limiters:
        return "MAX_SOC_LIMIT"
    if str(operating_mode or "").upper() == "SAFE_STATE":
        return "SAFE_STATE"
    if "REST_SURPLUS" in raw or "HARVEST" in raw or "RESTÜBERSCHUSS" in raw or "RESTUEBERSCHUSS" in raw or "ERNTE" in raw:
        return "REST_SURPLUS_HARVEST"
    if "BLOCKED_BY_SMA" in raw or "SMA" in raw or "CROSS_CHARGE" in raw:
        return "CROSS_CHARGE_BLOCKED" if target_final == 0 else "CROSS_CHARGE_REDUCED"
    if "DEADBAND" in raw:
        return "DEADBAND"
    if "DISCONNECT" in raw or "MQTT" in raw:
        return "MQTT_DISCONNECTED" if "DISCONNECT" in raw else "ZENDURE_MQTT_STALE"
    if "GRID" in raw and "STALE" in raw:
        return "GRID_STALE"
    if "SOC" in raw and "STALE" in raw:
        return "SOC_STALE"
    if "RAMP" in raw or "STEP" in raw:
        return "STEP_LIMIT"
    if "SMOOTH" in raw:
        return "SMOOTHING"
    if target_final is not None:
        if target_final > 0:
            return "AUTO_GRID_EXPORT"
        if target_final < 0:
            return "AUTO_GRID_IMPORT"
        return "DEADBAND"
    return "UNKNOWN"


def _safe_state_reason(row: Dict[str, Any], mqtt_status: str, missing_names: List[str], operating_mode: str) -> str:
    if operating_mode != "SAFE_STATE":
        return ""
    lowered = {name.lower() for name in missing_names}
    if "soc" in lowered or "zendure_soc" in lowered:
        return "SOC_MISSING"
    if mqtt_status == "ZENDURE_MQTT_NO_LIVE":
        return "ZENDURE_MQTT_NO_LIVE"
    if mqtt_status in {"ZENDURE_MQTT_STALE", "ZENDURE_MQTT_PARTIAL_STALE"}:
        return "ZENDURE_MQTT_STALE"
    if _bool01(row.get("zendure_mqtt_connected")) == "0":
        return "MQTT_DISCONNECTED"
    return "UNKNOWN"


def _command_action(row: Dict[str, Any], sent: bool, required: bool, mqtt_connected: str, target_final: Optional[float] = None, previous_effective_command_w: Optional[float] = None) -> Tuple[str, str]:
    if sent:
        return "SENT", ""
    skip = str(row.get("mqtt_command_skip_reason", row.get("mqtt_last_command_skipped", "")) or "").upper()
    if required and mqtt_connected == "0":
        return "FAILED", ""
    if not required:
        return "NOT_REQUIRED", ""
    if "MIN" in skip and "COMMAND" in skip:
        return "SUPPRESSED", "MIN_COMMAND_CHANGE"
    if "NO_CHANGE" in skip or "KEIN" in skip or "NO CHANGE" in skip:
        return "SUPPRESSED", "NO_CHANGE"
    if "DEADBAND" in skip:
        return "SUPPRESSED", "DEADBAND"
    if "SAFE" in skip:
        return "SUPPRESSED", "SAFE_STATE"
    if "MISSING" in skip or "REQUIRED" in skip:
        return "SUPPRESSED", "MISSING_REQUIRED_SOURCE"
    if skip and skip != "-":
        # Legacy MQTT skip text often only contains the topic and target value
        # (e.g. "inputLimit -> 0") after publish() suppresses a repeated value.
        # That is a no-change suppression, not an unknown diagnostic reason.
        if "->" in skip:
            return "SUPPRESSED", "NO_CHANGE"
        if target_final is not None and previous_effective_command_w is not None and abs(float(target_final) - float(previous_effective_command_w)) < 0.0001:
            return "SUPPRESSED", "NO_CHANGE"
        return "SUPPRESSED", "UNKNOWN"
    return "SUPPRESSED", "NO_CHANGE"


def _parse_pack_details(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = row.get("zendure_pack_data_json")
    if not raw:
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _is_headunit_id(pack_id: str) -> bool:
    raw = str(pack_id or "").lower()
    return raw == "headunit" or raw.startswith("hec")


def _temperature_aggregates(row: Dict[str, Any]) -> Dict[str, Any]:
    details = _parse_pack_details(row)
    now_age = _round1(row.get("actual_zendure_power_age_s", 0))
    headunit = []
    packs = []
    for item in details:
        pack_id = str(item.get("pack_sn") or item.get("pack_id") or item.get("sn") or "")
        temp = _safe_float(item.get("temperature_c"))
        if temp is None:
            continue
        if _is_headunit_id(pack_id):
            headunit.append((pack_id or "headunit_main", round(temp, 1), item))
        else:
            packs.append((pack_id or f"pack_{len(packs)+1}", round(temp, 1), item))
    if not details and _safe_float(row.get("raw_zendure_battery_temperature_c")) is not None:
        # Legacy V3 only had one aggregate temperature. Treat it as headunit-like
        # and do not invent per-pack details.
        headunit.append(("headunit_main", round(float(row.get("raw_zendure_battery_temperature_c")), 1), {}))
    result: Dict[str, Any] = {
        "headunit_source": "ZENDURE_MQTT",
        "pack_source": "ZENDURE_MQTT",
    }
    if headunit:
        max_head = max(headunit, key=lambda x: x[1])
        result.update({"headunit_temp_c": max_head[1], "headunit_valid": "1", "headunit_age_s": now_age, "headunit_source": "ZENDURE_MQTT"})
    else:
        result.update({"headunit_valid": "0", "headunit_source": "ZENDURE_MQTT"})
    if packs:
        max_pack = max(packs, key=lambda x: x[1])
        min_pack = min(packs, key=lambda x: x[1])
        result.update({
            "pack_max_temp_c": max_pack[1],
            "pack_min_temp_c": min_pack[1],
            "pack_count": len(packs),
            "max_pack_id": max_pack[0],
            "pack_valid": "1",
            "pack_age_s": now_age,
            "pack_source": "ZENDURE_MQTT",
        })
    else:
        result.update({"pack_count": 0, "pack_valid": "0", "pack_source": "ZENDURE_MQTT"})
    return result


def _temperature_jsons(row: Dict[str, Any], v4: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    details = _parse_pack_details(row)
    packs = []
    sensors = []
    for item in details:
        pack_id = str(item.get("pack_sn") or item.get("pack_id") or item.get("sn") or "")
        temp = _safe_float(item.get("temperature_c"))
        if temp is None:
            continue
        entry = {
            "sensor_id" if _is_headunit_id(pack_id) else "pack_id": pack_id or ("headunit_main" if _is_headunit_id(pack_id) else f"pack_{len(packs)+1}"),
            "label": "Headunit main" if _is_headunit_id(pack_id) else pack_id,
            "temp_c": round(temp, 1),
            "valid": True,
            "age_s": _safe_float(v4.get("zendure_headunit_temp_age_s" if _is_headunit_id(pack_id) else "zendure_battery_temp_age_s")),
        }
        if _is_headunit_id(pack_id):
            sensors.append(entry)
        else:
            packs.append(entry)
    pack_json = None
    if packs:
        pack_json = {
            "source": "ZENDURE_MQTT",
            "age_s": _safe_float(v4.get("zendure_battery_temp_age_s")),
            "valid": True,
            "pack_count": len(packs),
            "max_temp_c": _safe_float(v4.get("zendure_battery_temp_max_c")),
            "min_temp_c": _safe_float(v4.get("zendure_battery_temp_min_c")),
            "max_pack_id": v4.get("zendure_battery_temp_max_pack_id"),
            "packs": packs,
        }
    headunit_json = None
    if sensors:
        headunit_json = {
            "source": "ZENDURE_MQTT",
            "age_s": _safe_float(v4.get("zendure_headunit_temp_age_s")),
            "valid": True,
            "max_temp_c": _safe_float(v4.get("zendure_headunit_temp_c")),
            "max_sensor_id": max(sensors, key=lambda x: x.get("temp_c") or -999).get("sensor_id"),
            "sensors": sensors,
        }
    return pack_json, headunit_json


def _mqtt_group_status_json(row: Dict[str, Any], v4: Dict[str, Any]) -> Dict[str, Any]:
    missing = set(_mask_names_from_mask(_safe_int(v4.get("zendure_mqtt_missing_group_mask")) or 0, ZENDURE_MQTT_GROUP_BITS))
    stale = set(_mask_names_from_mask(_safe_int(v4.get("zendure_mqtt_stale_group_mask")) or 0, ZENDURE_MQTT_GROUP_BITS))
    groups = []
    for group_id in ZENDURE_MQTT_GROUP_BITS.keys():
        status = "OK"
        if group_id in missing:
            status = "MISSING"
        elif group_id in stale:
            status = "STALE"
        groups.append({
            "group_id": group_id,
            "status": status,
            "age_s": None,
            "fresh": status == "OK",
            "valid": status != "MISSING",
            "missing": group_id in missing,
            "stale": group_id in stale,
            "retained": False,
            "live_confirmed": _bool01(v4.get("zendure_mqtt_live_confirmed")) == "1",
        })
    return {
        "overall_status": v4.get("zendure_mqtt_status"),
        "live_confirmed": _bool01(v4.get("zendure_mqtt_live_confirmed")) == "1",
        "critical_data_age_s": _safe_float(v4.get("zendure_mqtt_critical_data_age_s")),
        "missing_group_count": _safe_int(v4.get("zendure_mqtt_missing_group_count")) or 0,
        "stale_group_count": _safe_int(v4.get("zendure_mqtt_stale_group_count")) or 0,
        "retained_only": _bool01(v4.get("zendure_mqtt_retained_only")) == "1",
        "after_broker_restart": _bool01(v4.get("zendure_mqtt_after_broker_restart")) == "1",
        "groups": groups,
    }


def _mask_names_from_mask(mask: int, bits: Dict[str, int]) -> List[str]:
    return [name for name, bit in bits.items() if mask & bit]


class RuntimeEventWriter:
    def __init__(self) -> None:
        self._last_event_signature = ""

    def path_for(self, directory: str) -> str:
        return os.path.join(directory, "zec_runtime_events.jsonl")

    def write(self, directory: str, event: Dict[str, Any]) -> None:
        os.makedirs(directory, exist_ok=True)
        payload = dict(event)
        payload["event_time_utc"] = payload.get("event_time_utc") or _now_utc()
        payload["event_type"] = payload.get("event_type") or "unknown"
        with open(self.path_for(directory), "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


class ConfigSnapshotStore:
    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._known_hashes: Dict[str, set] = {}

    def path_for(self, directory: str) -> str:
        return os.path.join(directory, "zec_config_snapshots.json")

    def ensure_snapshot(self, directory: str, config: Dict[str, Any]) -> str:
        os.makedirs(directory, exist_ok=True)
        path = self.path_for(directory)
        snapshot = build_config_snapshot(config)
        config_hash = str(snapshot["config_control_hash"])
        data = self._load(path)
        snapshots = data.setdefault("snapshots", [])
        changed = False
        existing = next((item for item in snapshots if isinstance(item, dict) and str(item.get("config_control_hash")) == config_hash), None)
        if existing is None:
            snapshots.append(snapshot)
            changed = True
        else:
            changed = self._backfill_existing_snapshot(existing, snapshot) or changed
        if changed:
            self._atomic_write(path, data)
            self._cache[path] = data
            self._known_hashes[path] = {str(item.get("config_control_hash")) for item in data.get("snapshots", []) if isinstance(item, dict)}
        else:
            self._known_hashes.setdefault(path, {str(item.get("config_control_hash")) for item in snapshots if isinstance(item, dict)})
        return config_hash

    def _load(self, path: str) -> Dict[str, Any]:
        if path in self._cache:
            return self._cache[path]
        data: Dict[str, Any] = {"schema_version": 4, "snapshots": []}
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                loaded.setdefault("schema_version", 4)
                loaded.setdefault("snapshots", [])
                data = loaded
        self._cache[path] = data
        self._known_hashes[path] = {str(item.get("config_control_hash")) for item in data.get("snapshots", []) if isinstance(item, dict)}
        return data

    def _backfill_existing_snapshot(self, existing: Dict[str, Any], snapshot: Dict[str, Any]) -> bool:
        changed = False
        params = existing.setdefault("control_parameters", {})
        new_params = snapshot.get("control_parameters", {}) if isinstance(snapshot.get("control_parameters"), dict) else {}
        if "CROSS_CHARGE_SIGNIFICANT_W" not in params:
            if "CROSS_CHARGE_SIGNIFICANT_W" in new_params:
                params["CROSS_CHARGE_SIGNIFICANT_W"] = new_params["CROSS_CHARGE_SIGNIFICANT_W"]
                changed = True
            elif "SMA_DISCHARGE_BLOCK_W" in params:
                params["CROSS_CHARGE_SIGNIFICANT_W"] = params.get("SMA_DISCHARGE_BLOCK_W")
                changed = True
        # Preserve original created_time_utc, but keep runtime/controller version and
        # newly introduced rule parameters current for diagnostics. The config hash
        # deliberately remains the hash of rule-relevant config values.
        for key in ("schema_version", "source"):
            if key not in existing and key in snapshot:
                existing[key] = snapshot[key]
                changed = True
        if existing.get("controller_version") != snapshot.get("controller_version"):
            existing["controller_version"] = snapshot.get("controller_version")
            existing["updated_time_utc"] = _now_utc()
            changed = True
        for key, value in new_params.items():
            if key not in params:
                params[key] = value
                changed = True
        return changed

    def _atomic_write(self, path: str, data: Dict[str, Any]) -> None:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
        os.replace(tmp, path)


class ManifestStore:
    def path_for(self, directory: str) -> str:
        return os.path.join(directory, "zec_measurement_manifest.json")

    def load(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                loaded.setdefault("schema_version", 4)
                loaded.setdefault("files", [])
                return loaded
        return {"schema_version": 4, "files": []}

    def update_file(self, directory: str, entry_update: Dict[str, Any]) -> Dict[str, Any]:
        os.makedirs(directory, exist_ok=True)
        path = self.path_for(directory)
        data = self.load(path)
        files = data.setdefault("files", [])
        file_id = str(entry_update["measurement_file_id"])
        entry = next((item for item in files if isinstance(item, dict) and item.get("measurement_file_id") == file_id), None)
        if entry is None:
            entry = {}
            files.append(entry)
        elif entry.get("created_time_utc"):
            entry_update = dict(entry_update)
            entry_update["created_time_utc"] = entry.get("created_time_utc")
        entry.update(entry_update)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
        os.replace(tmp, path)
        return entry


class MeasurementV4Logger:
    def __init__(self) -> None:
        self._fh = None
        self._writer = None
        self._open_path: Optional[str] = None
        self._rows_since_flush = 0
        self._last_flush_epoch = 0.0
        self._file_ids: Dict[str, str] = {}
        self._logical_stream_id = f"ls_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
        self._row_counts: Dict[str, int] = {}
        self._first_epoch_ms: Dict[str, int] = {}
        self._last_epoch_ms: Dict[str, int] = {}
        self._last_effective_command_w: Optional[float] = None
        self._validated_paths: Dict[str, str] = {}
        self._manifest = ManifestStore()
        self._snapshots = ConfigSnapshotStore()
        self._runtime = RuntimeEventWriter()
        self._fallback_active_previous = False
        self._fallback_counter_since_start = 0
        self._last_fallback_time = ""
        self._last_fallback_reason = ""
        self._last_fallback_signature = ""
        self._session_suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._session_path_map: Dict[str, str] = {}
        self._manifest_registered_paths: set = set()
        self._manifest_last_write_epoch: Dict[str, float] = {}
        self._manifest_last_row_count: Dict[str, int] = {}
        self._manifest_meta: Dict[str, Dict[str, Any]] = {}

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.flush()
            except Exception:
                pass
        if self._open_path:
            try:
                self._update_manifest(self._open_path, force=True)
            except Exception:
                pass
        if self._fh is not None:
            try:
                self._fh.close()
            except Exception:
                pass
        self._fh = None
        self._writer = None
        self._open_path = None
        self._rows_since_flush = 0

    def log(self, config: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        mode = measurement_log_mode(config)
        if mode == "off":
            return self._disabled_status("MEASUREMENT_LOG_MODE=off")
        profile = "extended" if mode == "extended" else "standard"
        cfg = _v4_target_config(config)
        target_info = self._resolve_target_info(cfg)
        path = str(target_info.get("path") or "")
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        free_mb = self._free_disk_mb(directory)
        min_free = int(config.get("MEASUREMENT_LOG_MIN_FREE_DISK_MB", 500))
        if free_mb is not None and free_mb < min_free:
            return self.status(config, "paused_disk_low", f"Freier Speicher unter {min_free} MB", path=path, free_mb=free_mb, target_info=target_info)

        schema_error = self._active_file_schema_error(path, profile)
        if schema_error:
            return self.status(config, "paused_invalid_schema", schema_error, path=path, free_mb=free_mb, target_info=target_info)

        try:
            config_hash = self._snapshots.ensure_snapshot(directory, cfg)
        except Exception as exc:
            self._runtime_best_effort(directory, {"event_type": "config_snapshot_write_failed", "failure_reason": str(exc), "resolved_primary_file_path": target_info.get("primary_path", ""), "resolved_mountpoint": target_info.get("primary_mountpoint", ""), "fallback_path": target_info.get("fallback_path", "")})
            return self.status(config, "paused_config_snapshot_error", f"Config-Snapshot konnte nicht geschrieben werden: {exc}", path=path, free_mb=free_mb, target_info=target_info)

        v4_row = build_v4_row(cfg, row, previous_effective_command_w=self._last_effective_command_w)
        v4_row["config_control_hash"] = config_hash
        if profile == "extended":
            v4_row.update(build_extended_values(row, v4_row))
        fields = header_for_profile(profile)
        row_epoch = _safe_int(v4_row.get("measurement_epoch_ms")) or 0

        fallback_event = self._update_fallback_state(target_info)
        rotated_path = self._rotate_if_needed(cfg, path, fallback_active=bool(target_info.get("fallback_active")))
        if rotated_path != path:
            path = rotated_path
            directory = os.path.dirname(path)
            target_info = dict(target_info)
            target_info["path"] = path
            os.makedirs(directory, exist_ok=True)
            free_mb = self._free_disk_mb(directory)
        file_id = self._file_id_for_path(path)
        if path not in self._row_counts:
            self._row_counts[path] = 0
        if path not in self._first_epoch_ms:
            self._first_epoch_ms[path] = row_epoch
        self._last_epoch_ms[path] = row_epoch
        rotation_reason = "FALLBACK_ENTER" if fallback_event and target_info.get("fallback_active") else "SERVICE_START"

        try:
            self._register_manifest_file(directory, path, profile, fields, file_id, row_epoch, target_info, rotation_reason=rotation_reason)
        except Exception as exc:
            self._runtime_best_effort(directory, {"event_type": "manifest_write_failed", "failure_reason": str(exc), "measurement_file_id": file_id, "logical_stream_id": self._logical_stream_id, "resolved_primary_file_path": target_info.get("primary_path", ""), "resolved_mountpoint": target_info.get("primary_mountpoint", ""), "fallback_path": target_info.get("fallback_path", "")})
            return self.status(config, "paused_manifest_error", f"Manifest konnte nicht geschrieben werden: {exc}", path=path, free_mb=free_mb, target_info=target_info)

        writer = self._get_writer(path, fields)
        writer.writerow({field: self._serialize(v4_row.get(field, "")) for field in fields})
        self._rows_since_flush += 1
        flushed = self._flush_if_due(config)
        self._row_counts[path] = self._row_counts.get(path, 0) + 1
        if _safe_float(v4_row.get("command_effective_w")) is not None:
            self._last_effective_command_w = _safe_float(v4_row.get("command_effective_w"))

        try:
            self._update_manifest_if_due(config, path, row_epoch, force=(self._row_counts.get(path, 0) == 1 or flushed))
        except Exception as exc:
            # The row is already written; surface the problem immediately.
            self._runtime_best_effort(directory, {"event_type": "manifest_write_failed", "failure_reason": str(exc), "measurement_file_id": file_id, "logical_stream_id": self._logical_stream_id})

        if fallback_event:
            event_type = "fallback_enter" if target_info.get("fallback_active") else "fallback_recovered"
            self._runtime_best_effort(directory, {
                "event_type": event_type,
                "measurement_file_id": file_id,
                "logical_stream_id": self._logical_stream_id,
                "resolved_primary_file_path": target_info.get("primary_path", ""),
                "resolved_mountpoint": target_info.get("primary_mountpoint", ""),
                "failure_reason": target_info.get("primary_failure_reason", ""),
                "fallback_path": target_info.get("fallback_path", ""),
            })

        status = "active_fallback_sd" if target_info.get("fallback_active") else "active"
        reason = "SD-Fallback aktiv; V4-Measurement schreibt begrenzt auf SD." if target_info.get("fallback_active") else "OK"
        return self.status(config, status, reason, path=path, free_mb=free_mb, row_size_bytes=self._serialized_row_length(v4_row, fields), target_info=target_info, fallback_event=fallback_event)

    def status(self, config: Dict[str, Any], status: str, reason: str, *, path: Optional[str] = None, free_mb: Optional[int] = None, row_size_bytes: Optional[int] = None, target_info: Optional[Dict[str, Any]] = None, fallback_event: bool = False) -> Dict[str, Any]:
        cfg = _v4_target_config(config)
        target_info = target_info or self._resolve_target_info(cfg)
        path = path or str(target_info.get("path") or "")
        current_size = os.path.getsize(path) if path and os.path.exists(path) else 0
        return {
            "measurement_log_status": status,
            "measurement_log_status_reason": reason,
            "measurement_estimated_retention_hours": estimate_retention_hours(config, row_size_bytes),
            "measurement_current_file_size_bytes": current_size,
            "measurement_free_disk_mb": free_mb if free_mb is not None else self._free_disk_mb(os.path.dirname(path) if path else "."),
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

    def _disabled_status(self, reason: str) -> Dict[str, Any]:
        # Logging=off must be a hard bypass: no path resolution, disk stat, manifest,
        # snapshot or retention calculation in the regulator cycle.
        return {
            "measurement_log_status": "disabled",
            "measurement_log_status_reason": reason,
            "measurement_estimated_retention_hours": "",
            "measurement_current_file_size_bytes": 0,
            "measurement_free_disk_mb": "",
            "measurement_log_path": self._open_path or "",
            "measurement_log_target_type": "",
            "measurement_log_active_target_type": "",
            "measurement_fallback_active": False,
            "measurement_fallback_event": False,
            "measurement_fallback_count_since_start": self._fallback_counter_since_start,
            "measurement_last_fallback_time": self._last_fallback_time,
            "measurement_last_fallback_reason": self._last_fallback_reason,
        }

    def get_current_path(self, config: Dict[str, Any]) -> str:
        if measurement_log_mode(config) == "off":
            return self._open_path or ""
        return str(self._resolve_target_info(_v4_target_config(config)).get("path") or "")

    def _resolve_target_info(self, config: Dict[str, Any]) -> Dict[str, Any]:
        target_info = resolve_log_target(config, allow_fallback=True)
        base_path = str(target_info.get("path") or "")
        if not base_path:
            return target_info
        session_path = self._session_path_for(base_path)
        if session_path != base_path:
            target_info = dict(target_info)
            target_info["path"] = session_path
        return target_info

    def _session_path_for(self, base_path: str) -> str:
        if base_path in self._session_path_map:
            return self._session_path_map[base_path]
        path = base_path
        filename = os.path.basename(base_path)
        # RC8: never write a V4 runtime session into the unsuffixed base file.
        # The RC7 investigation showed a dangerous split-brain condition where
        # the manifest referenced a timestamped session file while the physical
        # data was no longer present after restart/package handling.  A fresh,
        # explicit session file for every service start keeps manifest entries
        # and physical files one-to-one and prevents accidental truncation or
        # reuse of zendure_measurements_v4.csv.
        if filename == "zendure_measurements_v4.csv":
            stem, ext = os.path.splitext(filename)
            path = os.path.join(os.path.dirname(base_path), f"{stem}_{self._session_suffix}{ext}")
            if os.path.exists(path):
                path = os.path.join(os.path.dirname(base_path), f"{stem}_{self._session_suffix}_{uuid.uuid4().hex[:6]}{ext}")
        self._session_path_map[base_path] = path
        return path

    def _register_manifest_file(self, directory: str, path: str, profile: str, fields: List[str], file_id: str, row_epoch: int, target_info: Dict[str, Any], rotation_reason: str) -> None:
        if path in self._manifest_registered_paths:
            return
        self._manifest_meta[path] = {
            "directory": directory,
            "profile": profile,
            "fields": fields,
            "file_id": file_id,
            "target_info": dict(target_info),
            "rotation_reason": rotation_reason,
        }
        self._ensure_manifest_entry(directory, path, profile, fields, file_id, row_epoch, target_info, rotation_reason)
        self._manifest_registered_paths.add(path)
        self._manifest_last_write_epoch[path] = __import__("time").time()
        self._manifest_last_row_count[path] = self._row_counts.get(path, 0)

    def _update_manifest_if_due(self, config: Dict[str, Any], path: str, row_epoch: int, *, force: bool = False) -> None:
        if path not in self._manifest_meta:
            return
        import time
        rows_every = max(1, int(config.get("MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_ROWS", 25)))
        seconds_every = max(5.0, float(config.get("MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_SECONDS", 30)))
        row_count = self._row_counts.get(path, 0)
        last_rows = self._manifest_last_row_count.get(path, 0)
        last_time = self._manifest_last_write_epoch.get(path, 0.0)
        now = time.time()
        if not force and (row_count - last_rows) < rows_every and (now - last_time) < seconds_every:
            return
        self._update_manifest(path, force=True, row_epoch=row_epoch)

    def _update_manifest(self, path: str, *, force: bool = False, row_epoch: Optional[int] = None) -> None:
        if path not in self._manifest_meta:
            return
        meta = self._manifest_meta[path]
        if row_epoch is None:
            row_epoch = self._last_epoch_ms.get(path, self._first_epoch_ms.get(path, 0))
        self._ensure_manifest_entry(
            meta["directory"],
            path,
            meta["profile"],
            meta["fields"],
            meta["file_id"],
            int(row_epoch or 0),
            meta["target_info"],
            meta["rotation_reason"],
        )
        self._manifest_last_write_epoch[path] = __import__("time").time()
        self._manifest_last_row_count[path] = self._row_counts.get(path, 0)

    def _file_id_for_path(self, path: str) -> str:
        if path not in self._file_ids:
            digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:8]
            self._file_ids[path] = f"mf_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{digest}"
            self._runtime_best_effort(os.path.dirname(path), {"event_type": "logging_file_opened", "measurement_file_id": self._file_ids[path], "logical_stream_id": self._logical_stream_id})
        return self._file_ids[path]

    def _ensure_manifest_entry(self, directory: str, path: str, profile: str, fields: List[str], file_id: str, row_epoch: int, target_info: Dict[str, Any], rotation_reason: str) -> None:
        relative = os.path.relpath(path, directory)
        count = self._row_counts.get(path, 0)
        first_epoch = self._first_epoch_ms.get(path, row_epoch)
        file_role = "fallback_measurement" if target_info.get("fallback_active") else "primary_measurement"
        reason = rotation_reason if rotation_reason in ROTATION_REASON_VALUES else "UNKNOWN"
        self._manifest.update_file(directory, {
            "measurement_file_id": file_id,
            "logical_stream_id": self._logical_stream_id,
            "file_role": file_role,
            "profile": profile,
            "schema_version": 4,
            "file_name": os.path.basename(path),
            "relative_path": relative,
            "header_hash": header_hash(fields),
            "first_measurement_epoch_ms": first_epoch,
            "last_measurement_epoch_ms": row_epoch,
            "row_count": count,
            "rotation_reason": reason,
            "created_time_utc": _now_utc(),
            "closed_time_utc": "",
        })

    def _get_writer(self, path: str, fields: List[str]):
        write_header = not os.path.exists(path) or os.path.getsize(path) == 0
        if self._fh is None or self._open_path != path or self._fh.closed:
            self.close()
            self._fh = open(path, "a", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(self._fh, fieldnames=fields, extrasaction="ignore", delimiter=";")
            self._open_path = path
            self._last_flush_epoch = __import__("time").time()
            if write_header:
                self._writer.writerow({field: field for field in fields})
        return self._writer

    def _flush_if_due(self, config: Dict[str, Any]) -> bool:
        if self._fh is None:
            return False
        import time
        max_rows = max(1, int(config.get("MEASUREMENT_LOG_FLUSH_EVERY_ROWS", 100)))
        max_seconds = max(1.0, float(config.get("MEASUREMENT_LOG_FLUSH_EVERY_SECONDS", 60)))
        now = time.time()
        if self._rows_since_flush >= max_rows or (now - self._last_flush_epoch) >= max_seconds:
            self._fh.flush()
            self._rows_since_flush = 0
            self._last_flush_epoch = now
            return True
        return False

    def _serialize(self, value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "1" if value else "0"
        return value

    def _serialized_row_length(self, row: Dict[str, Any], fields: List[str]) -> int:
        import io
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore", delimiter=";")
        writer.writerow({field: self._serialize(row.get(field, "")) for field in fields})
        return len(buffer.getvalue().encode("utf-8"))

    def _active_file_schema_error(self, path: str, profile: str) -> str:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            self._validated_paths.pop(path, None)
            return ""
        expected = header_for_profile(profile)
        if self._validated_paths.get(path) == profile:
            return ""
        try:
            with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                first = f.readline().strip()
        except Exception as exc:
            return f"Aktive V4-Messdatei konnte nicht geprüft werden: {exc}"
        fields = [part.strip() for part in first.split(";")]
        if fields == expected:
            self._validated_paths[path] = profile
            return ""
        return "Messdaten-Logging pausiert: vorhandene Datei entspricht nicht dem gültigen ZEC-MEASUREMENT-V4-Header. Datei prüfen/löschen oder neuen Dateinamen wählen."

    def _rotate_if_needed(self, config: Dict[str, Any], path: str, *, fallback_active: bool = False) -> str:
        if fallback_active:
            max_bytes = int(config.get("MEASUREMENT_LOG_FALLBACK_MAX_BYTES", 10_000_000))
        else:
            max_bytes = int(config.get("MEASUREMENT_LOG_MAX_BYTES", 25_000_000))
        if not os.path.exists(path) or os.path.getsize(path) < max_bytes:
            return path

        if self._open_path == path:
            self.close()

        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        _stem, ext = os.path.splitext(filename)
        # V4 rotation is manifest-led: never create hidden _1/_2 files that are
        # not registered as physical measurement files. Use a fresh short name
        # instead of appending timestamps to already rotated filenames.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stem = "zendure_measurements_v4" if filename.startswith("zendure_measurements_v4") else _stem
        new_path = os.path.join(directory, f"{stem}_{stamp}{ext}")
        if os.path.exists(new_path):
            new_path = os.path.join(directory, f"{stem}_{stamp}_{uuid.uuid4().hex[:6]}{ext}")
        for base, mapped in list(self._session_path_map.items()):
            if mapped == path:
                self._session_path_map[base] = new_path
        self._runtime_best_effort(directory, {
            "event_type": "logging_file_rotated",
            "logical_stream_id": self._logical_stream_id,
            "previous_path": path,
            "new_path": new_path,
            "rotation_reason": "SIZE_LIMIT",
        })
        return new_path

    def _backup_path(self, path: str, index: int) -> str:
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        stem, ext = os.path.splitext(filename)
        return os.path.join(directory, f"{stem}_{index}{ext}")

    def _free_disk_mb(self, directory: str) -> Optional[int]:
        try:
            os.makedirs(directory, exist_ok=True)
            usage = os.statvfs(directory)
            return int((usage.f_bavail * usage.f_frsize) / 1024 / 1024)
        except Exception:
            return None

    def _runtime_best_effort(self, directory: str, event: Dict[str, Any]) -> None:
        try:
            self._runtime.write(directory, event)
        except Exception:
            pass

    def _update_fallback_state(self, target_info: Dict[str, Any]) -> bool:
        fallback_active = bool(target_info.get("fallback_active"))
        signature = f"{target_info.get('primary_path')}|{target_info.get('primary_failure_reason')}|{target_info.get('primary_exception')}|{fallback_active}"
        event = False
        if fallback_active:
            if (not self._fallback_active_previous) or signature != self._last_fallback_signature:
                event = True
                self._fallback_counter_since_start += 1
                self._last_fallback_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._last_fallback_reason = str(target_info.get("primary_failure_reason") or "fallback_active")
                self._last_fallback_signature = signature
        elif self._fallback_active_previous:
            event = True
            self._last_fallback_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._last_fallback_reason = "fallback_recovered"
        self._fallback_active_previous = fallback_active
        return event
