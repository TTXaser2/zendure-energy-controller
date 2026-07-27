# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# ZEC-MEASUREMENT-V4 contract constants.

import hashlib
from typing import Dict, List

STANDARD_HEADER: List[str] = [
    "schema_version",
    "cycle_index",
    "measurement_time_utc",
    "measurement_epoch_ms",
    "cycle_duration_ms",
    "config_control_hash",
    "operating_mode",
    "operating_mode_duration_s",
    "control_intent",
    "control_input_valid",
    "control_missing_required_source_mask",
    "control_missing_required_source_count",
    "safe_state_active",
    "safe_state_reason",
    "night_window_active",
    "control_night_reserve_active",
    "control_night_exit_neutralized",
    "fixed_mode_active",
    "manual_stop_active",
    "grid_power_raw_w",
    "grid_power_w",
    "grid_power_valid",
    "grid_power_fresh",
    "grid_power_age_s",
    "grid_power_source",
    "pv_power_w",
    "pv_power_valid",
    "pv_power_fresh",
    "pv_power_age_s",
    "pv_power_source",
    "house_power_w",
    "house_power_valid",
    "house_power_fresh",
    "house_power_age_s",
    "house_power_source",
    "zendure_unit_count",
    "zendure_power_raw_w",
    "zendure_actual_power_w",
    "zendure_actual_power_valid",
    "zendure_actual_power_fresh",
    "zendure_actual_power_age_s",
    "zendure_actual_power_source",
    "zendure_raw_pack_input_w",
    "zendure_raw_grid_input_w",
    "zendure_raw_output_home_w",
    "zendure_raw_output_pack_w",
    "zendure_raw_grid_off_w",
    "zendure_raw_solar_input_w",
    "zendure_grid_signed_power_w",
    "zendure_battery_signed_power_w",
    "zendure_battery_charge_power_w",
    "zendure_battery_discharge_power_w",
    "zendure_offgrid_power_w",
    "zendure_offgrid_active",
    "zendure_power_balance_residual_w",
    "zendure_soc_raw_percent",
    "zendure_soc_percent",
    "control_soc_percent",
    "zendure_soc_valid",
    "zendure_soc_fresh",
    "zendure_soc_age_s",
    "zendure_soc_source",
    "zendure_headunit_temp_c",
    "zendure_headunit_temp_valid",
    "zendure_headunit_temp_age_s",
    "zendure_headunit_temp_source",
    "zendure_battery_temp_max_c",
    "zendure_battery_temp_min_c",
    "zendure_battery_temp_pack_count",
    "zendure_battery_temp_max_pack_id",
    "zendure_battery_temp_valid",
    "zendure_battery_temp_age_s",
    "zendure_battery_temp_source",
    "zendure_mqtt_status",
    "zendure_mqtt_live_confirmed",
    "zendure_mqtt_critical_data_age_s",
    "zendure_mqtt_missing_group_mask",
    "zendure_mqtt_missing_group_count",
    "zendure_mqtt_stale_group_mask",
    "zendure_mqtt_stale_group_count",
    "zendure_mqtt_retained_only",
    "zendure_mqtt_after_broker_restart",
    "second_battery_power_raw_w",
    "second_battery_power_w",
    "second_battery_power_valid",
    "second_battery_power_fresh",
    "second_battery_power_age_s",
    "second_battery_soc_percent",
    "second_battery_soc_valid",
    "second_battery_soc_fresh",
    "second_battery_soc_age_s",
    "second_battery_source",
    "scenario_grid_without_zendure_w",
    "scenario_grid_without_zendure_valid",
    "scenario_grid_without_zendure_source",
    "scenario_effective_surplus_w",
    "scenario_effective_surplus_valid",
    "control_grid_power_w",
    "control_grid_power_smoothed_w",
    "control_grid_power_smoothed_valid",
    "control_effective_export_w",
    "control_effective_export_valid",
    "rest_surplus_harvest_active",
    "rest_surplus_harvest_eligible",
    "rest_surplus_harvest_reason",
    "rest_surplus_harvest_block_reason",
    "rest_surplus_harvest_profile",
    "rest_surplus_entry_progress_s",
    "rest_surplus_hold_remaining_s",
    "rest_surplus_exit_reason",
    "second_battery_charge_pressure_w",
    "second_battery_charge_saturation_threshold_w",
    "rest_surplus_export_w",
    "harvest_primary_floor_w",
    "harvest_primary_restart_w",
    "harvest_primary_near_limit_w",
    "harvest_primary_target_share",
    "harvest_primary_required_w",
    "harvest_primary_share_reserve_w",
    "harvest_candidate_raw_w",
    "harvest_candidate_after_primary_w",
    "harvest_limiter_reason",
    "harvest_capacity_mode",
    "primary_remaining_capacity_kwh",
    "zendure_remaining_capacity_kwh",
    "control_deadband_active",
    "control_cross_charge_detected",
    "control_cross_charge_limited",
    "control_mode_change_lock_active",
    "target_raw_w",
    "target_filtered_w",
    "target_step_limited_w",
    "target_limited_w",
    "target_final_w",
    "target_final_reason",
    "target_changed_by_deadband",
    "target_changed_by_smoothing",
    "target_changed_by_step_limit",
    "target_changed_by_soc_limit",
    "target_changed_by_power_limit",
    "target_changed_by_cross_charge",
    "target_changed_by_mode",
    "target_changed_by_safe_state",
    "command_action",
    "command_requested_w",
    "command_sent_w",
    "command_effective_w",
    "command_sent_flag",
    "command_suppressed_reason",
    "command_mqtt_connected",
    "command_mqtt_success",
    "command_delta_w",
    "command_lifecycle_state",
    "command_desired_sequence_id",
    "command_desired_intent",
    "command_desired_smart_mode",
    "command_desired_ac_mode",
    "command_desired_input_limit_w",
    "command_desired_output_limit_w",
    "command_desired_signed_target_w",
    "command_desired_reason",
    "command_desired_safety_relevant",
    "command_publish_event",
    "command_publish_fields",
    "command_effect_category",
    "command_effect_reason",
    "command_effect_confirmed",
    "command_effect_confirmed_time",
    "command_neutralization_active",
    "command_neutralization_reason",
    "command_mismatch_resolution",
    "zendure_command_smart_mode",
    "zendure_command_ac_mode",
    "zendure_command_input_limit_w",
    "zendure_command_output_limit_w",
    "zendure_device_inverse_max_power_w",
    "zendure_device_charge_max_limit_w",
    "zendure_grid_off_mode",
    "zendure_flash_protection_active",
    "zendure_flash_protection_reason",
    "zendure_command_state_complete",
    "zendure_command_state_reason",
    "zendure_command_state_source",
    "zendure_power_observation_direction",
    "zendure_power_observation_confidence",
    "zendure_power_observation_signed_w",
    "zendure_power_observation_magnitude_w",
    "zendure_power_observation_age_s",
    "zendure_power_observation_reason",
    "command_uncertain_mqtt_active",
    "command_uncertain_mqtt_status",
    "command_not_effective_active",
    "command_not_effective_duration_s",
    "command_resync_count",
    "command_resync_reason",
]

# Fields added by RC11 for the command lifecycle and independent power
# observation.
RC11_COMMAND_LIFECYCLE_FIELDS = {
    "command_lifecycle_state",
    "command_desired_sequence_id",
    "command_desired_intent",
    "command_desired_ac_mode",
    "command_desired_input_limit_w",
    "command_desired_output_limit_w",
    "command_desired_signed_target_w",
    "command_desired_reason",
    "command_desired_safety_relevant",
    "command_publish_event",
    "command_publish_fields",
    "command_effect_confirmed",
    "command_effect_confirmed_time",
    "command_neutralization_active",
    "command_neutralization_reason",
    "zendure_power_observation_direction",
    "zendure_power_observation_confidence",
    "zendure_power_observation_signed_w",
    "zendure_power_observation_magnitude_w",
    "zendure_power_observation_age_s",
    "zendure_power_observation_reason",
    "zendure_raw_pack_input_w",
    "zendure_raw_grid_input_w",
    "zendure_raw_output_home_w",
    "zendure_raw_output_pack_w",
}

# RC12 adds the verified smartMode/command read-back contract and separates
# grid-side, battery-side and off-grid power boundaries.
RC12_COMMAND_CONTRACT_FIELDS = {
    "command_desired_smart_mode",
    "command_mismatch_resolution",
    "zendure_command_smart_mode",
    "zendure_command_ac_mode",
    "zendure_command_input_limit_w",
    "zendure_command_output_limit_w",
    "zendure_device_inverse_max_power_w",
    "zendure_device_charge_max_limit_w",
    "zendure_grid_off_mode",
    "zendure_flash_protection_active",
    "zendure_flash_protection_reason",
    "zendure_command_state_complete",
    "zendure_command_state_reason",
    "zendure_command_state_source",
    "zendure_raw_grid_off_w",
    "zendure_raw_solar_input_w",
    "zendure_grid_signed_power_w",
    "zendure_battery_signed_power_w",
    "zendure_battery_charge_power_w",
    "zendure_battery_discharge_power_w",
    "zendure_offgrid_power_w",
    "zendure_offgrid_active",
    "zendure_power_balance_residual_w",
}

RC11_STANDARD_HEADER: List[str] = [
    field for field in STANDARD_HEADER if field not in RC12_COMMAND_CONTRACT_FIELDS
]
RC10_STANDARD_HEADER: List[str] = [
    field for field in RC11_STANDARD_HEADER if field not in RC11_COMMAND_LIFECYCLE_FIELDS
]

EXTENDED_FIELDS: List[str] = [
    "zendure_pack_temperatures_json",
    "zendure_headunit_temperatures_json",
    "zendure_mqtt_group_status_json",
]

EXTENDED_HEADER: List[str] = STANDARD_HEADER + EXTENDED_FIELDS
RC11_EXTENDED_HEADER: List[str] = RC11_STANDARD_HEADER + EXTENDED_FIELDS
RC10_EXTENDED_HEADER: List[str] = RC10_STANDARD_HEADER + EXTENDED_FIELDS

OPERATING_MODE_VALUES = {
    "AUTO", "HOLD", "HOLD_DEADBAND", "NIGHT_DISCHARGE", "FIXED_CHARGE",
    "FIXED_DISCHARGE", "STOP_HOLD", "SAFE_STATE", "UNKNOWN",
}

CONTROL_INTENT_VALUES = {"CHARGE", "DISCHARGE", "NEUTRAL", "HOLD", "SAFE", "UNKNOWN"}

TARGET_FINAL_REASON_VALUES = {
    "AUTO_GRID_IMPORT", "AUTO_GRID_EXPORT", "DEADBAND", "NIGHT_BASE_DISCHARGE",
    "NIGHT_RESERVE_STOP", "NIGHT_WINDOW_ENDED_NEUTRALIZED", "FIXED_CHARGE",
    "FIXED_DISCHARGE", "MANUAL_STOP", "MIN_SOC_LIMIT", "MAX_SOC_LIMIT",
    "MAX_CHARGE_POWER_LIMIT", "MAX_DISCHARGE_POWER_LIMIT", "STEP_LIMIT", "SMOOTHING",
    "CROSS_CHARGE_REDUCED", "CROSS_CHARGE_BLOCKED", "REST_SURPLUS_HARVEST", "MISSING_REQUIRED_SOURCE",
    "GRID_STALE", "SOC_STALE", "ZENDURE_MQTT_STALE", "MQTT_DISCONNECTED",
    "SAFE_STATE", "UNKNOWN",
}

COMMAND_ACTION_VALUES = {"SENT", "SUPPRESSED", "FAILED", "NOT_REQUIRED", "UNKNOWN"}
COMMAND_SUPPRESSED_REASON_VALUES = {
    "NO_CHANGE", "MIN_COMMAND_CHANGE", "DEADBAND", "MODE_HOLD", "MQTT_DISCONNECTED",
    "INVALID_TARGET", "SAFE_STATE", "MISSING_REQUIRED_SOURCE", "UNKNOWN",
}

SOURCE_VALUES = {"SHELLY", "UNIMETER", "EVCC", "SMA", "ZENDURE_MQTT", "DERIVED", "CONFIG", "DISABLED", "UNKNOWN"}
SECOND_BATTERY_SOURCE_VALUES = {"EVCC_STANDARD", "EVCC_CUSTOM", "SMA", "DISABLED", "UNKNOWN"}

ZENDURE_MQTT_STATUS_VALUES = {
    "ZENDURE_MQTT_OK", "ZENDURE_MQTT_STALE", "ZENDURE_MQTT_PARTIAL_STALE",
    "ZENDURE_MQTT_RETAINED_ONLY", "ZENDURE_MQTT_NO_LIVE", "ZENDURE_MQTT_UNKNOWN",
}

SAFE_STATE_REASON_VALUES = {
    "MQTT_DISCONNECTED", "SOC_MISSING", "SOC_STALE", "GRID_REQUIRED_BUT_MISSING",
    "GRID_REQUIRED_BUT_STALE", "ZENDURE_MQTT_NO_LIVE", "ZENDURE_MQTT_STALE",
    "COMMAND_PATH_UNAVAILABLE", "CONFIG_INVALID", "COMMAND_FAILED", "UNKNOWN",
}

FILE_ROLE_VALUES = {"primary_measurement", "fallback_measurement", "rotated_measurement", "export_copy", "unknown"}
ROTATION_REASON_VALUES = {
    "SERVICE_START", "PROFILE_CHANGED", "HEADER_CHANGED", "SIZE_LIMIT", "TIME_ROTATION",
    "MANUAL_ROTATION", "FALLBACK_ENTER", "FALLBACK_RECOVERED", "UNKNOWN",
}

MISSING_REQUIRED_SOURCE_BITS: Dict[str, int] = {
    "GRID_POWER": 1,
    "ZENDURE_SOC": 2,
    "ZENDURE_MQTT_COMMAND_PATH": 4,
    "ZENDURE_ACTUAL_POWER": 8,
    "SECOND_BATTERY_POWER": 16,
    "PV_POWER": 32,
    "HOUSE_POWER": 64,
    "CONFIG_CONTROL": 128,
}

ZENDURE_MQTT_GROUP_BITS: Dict[str, int] = {
    "ZENDURE_SOC": 1,
    "ZENDURE_HEADUNIT_POWER": 2,
    "ZENDURE_PACK_DATA": 4,
    "ZENDURE_LIMIT_STATE": 8,
    "ZENDURE_DEVICE_STATE": 16,
    "ZENDURE_COMMAND_FEEDBACK": 32,
    "ZENDURE_TEMPERATURES": 64,
}

EXTENDED_GROUP_STATUS_VALUES = {"OK", "MISSING", "STALE", "RETAINED_ONLY", "NO_LIVE", "UNKNOWN"}


def header_for_profile(profile: str) -> List[str]:
    return EXTENDED_HEADER if str(profile).lower() == "extended" else STANDARD_HEADER


def rc11_header_for_profile(profile: str) -> List[str]:
    return RC11_EXTENDED_HEADER if str(profile).lower() == "extended" else RC11_STANDARD_HEADER


def rc10_header_for_profile(profile: str) -> List[str]:
    return RC10_EXTENDED_HEADER if str(profile).lower() == "extended" else RC10_STANDARD_HEADER


def header_hash(fields: List[str]) -> str:
    line = ";".join(fields)
    return hashlib.sha256(line.encode("utf-8")).hexdigest()[:16]
