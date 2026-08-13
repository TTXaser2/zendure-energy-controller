# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import hashlib
import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from measurement import derive_zendure_actual_power, signed_zendure_target_w
from zendure_power_observation import derive_zendure_power_observation
from freshness import boolean_status, timestamp_status
from translations import limiter_text, mode_label, path_label, technical_limiter_text
from version import APP_VERSION


def power_flow_meaning(value: float, positive_label: str = "Netzbezug", negative_label: str = "Einspeisung", deadband: float = 1.0) -> str:
    if value > deadband:
        return positive_label
    if value < -deadband:
        return negative_label
    return "nahe 0 W"


def sma_power_meaning(value: float, deadband: float = 1.0) -> str:
    # Darstellungslogik: positive Werte bedeuten Ladung, negative Werte bedeuten Entladung.
    if value > deadband:
        return "zweite Batterie lädt"
    if value < -deadband:
        return "zweite Batterie entlädt"
    return "nahe 0 W"


@dataclass
class ControllerState:
    startup_epoch: float = field(default_factory=time.time)
    startup_time: datetime = field(default_factory=datetime.now)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    # Leistung / Regelung
    raw_grid_power: float = 0.0
    grid_power: float = 0.0
    current_rule_deviation: float = 0.0
    effective_export_power: int = 0
    effective_export_power_valid: bool = False
    effective_export_power_used_for_control: bool = False
    grid_power_available: bool = False
    grid_power_fresh: bool = False
    grid_power_valid: bool = False
    grid_power_used_for_control: bool = False
    grid_power_age_seconds: Optional[int] = None
    grid_power_validity_reason: str = "GRID_MISSING"
    grid_meter_source: str = "shelly_http"
    raw_grid_source: str = "Shelly-kompatible HTTP-Quelle"
    grid_rejected_count_since_start: int = 0
    grid_last_rejected_time: str = "-"
    grid_last_rejected_reason: str = ""
    grid_last_rejected_value_w: Optional[float] = None
    last_input_power: int = 0
    last_output_power: int = 0
    # Zendure Headunit/System-Istleistung. Historisch wurden packInputPower
    # und outputHomePower direkt als "Laden/Entladen" dargestellt. In der
    # Praxis ist für die tatsächlich an der Headunit erreichte Ladeleistung
    # insbesondere gridInputPower relevant; daher führen wir die Rohsensoren
    # separat und berechnen daraus eine konsistente Systemleistung:
    # positiv = Ladung, negativ = Entladung.
    actual_zendure_charge_power: int = 0
    actual_zendure_discharge_power: int = 0
    actual_zendure_grid_input_power: int = 0
    actual_zendure_output_pack_power: int = 0
    actual_zendure_grid_off_power: int = 0
    actual_zendure_solar_input_power: int = 0
    actual_zendure_pack_input_update_epoch: Optional[float] = None
    actual_zendure_output_home_update_epoch: Optional[float] = None
    actual_zendure_grid_input_update_epoch: Optional[float] = None
    actual_zendure_output_pack_update_epoch: Optional[float] = None
    actual_zendure_grid_off_update_epoch: Optional[float] = None
    actual_zendure_solar_input_update_epoch: Optional[float] = None
    # Grid-connected AC effect used by control/scenario reconstruction.
    actual_zendure_system_charge_power: int = 0
    actual_zendure_system_discharge_power: int = 0
    actual_zendure_system_signed_power: int = 0
    # Orthogonal electrical boundaries introduced by RC12.
    zendure_grid_signed_power_w: int = 0
    zendure_grid_import_power_w: int = 0
    zendure_grid_output_power_w: int = 0
    zendure_battery_signed_power_w: int = 0
    zendure_battery_charge_power_w: int = 0
    zendure_battery_discharge_power_w: int = 0
    zendure_offgrid_power_w: int = 0
    zendure_offgrid_active: bool = False
    zendure_power_balance_residual_w: int = 0
    # Independent physical-direction observation.  Unlike the legacy signed
    # value above, this model never uses the requested limit as sole direction
    # evidence.  Ambiguous packInputPower remains directionally unknown while
    # its magnitude can still prove that a 0-W neutralisation has not worked.
    zendure_power_observation_direction: str = "UNKNOWN"
    zendure_power_observation_confidence: str = "NONE"
    zendure_power_observation_signed_w: Optional[int] = None
    zendure_power_observation_magnitude_w: int = 0
    zendure_power_observation_reason: str = "Noch keine unabhängige Leistungsbeobachtung."
    zendure_power_observation_updated_epoch: Optional[float] = None
    current_target_power: int = 0
    zendure_target_signed_power: int = 0
    last_target_before_smoothing: int = 0
    last_target_after_power_limit: int = 0
    target_power_limit_reason: str = "NONE"
    last_target_after_smoothing: int = 0
    last_target_after_ramp: int = 0
    cross_charge_guard_latched: bool = False
    cross_charge_last_direction: str = ""

    # Restüberschuss-Ernte: zustandsbehaftete Diagnosefelder.
    # Der Modus darf nur in AUTO laden, startet erst nach bestätigtem
    # SMA-Ladelimit+Export-Zustand und bleibt danach bewusst großzügig aktiv,
    # solange er dem System nicht schadet.
    rest_surplus_harvest_active: bool = False
    rest_surplus_harvest_eligible: bool = False
    rest_surplus_entry_progress_s: float = 0.0
    rest_surplus_exit_reason: str = ""
    rest_surplus_harvest_reason: str = "NONE"
    rest_surplus_harvest_block_reason: str = ""
    rest_surplus_harvest_profile: str = "default"
    rest_surplus_hold_remaining_s: float = 0.0
    rest_surplus_export_w: float = 0.0
    second_battery_charge_pressure_w: float = 0.0
    second_battery_charge_saturation_threshold_w: float = 0.0
    harvest_primary_floor_w: float = 0.0
    harvest_primary_restart_w: float = 0.0
    harvest_primary_near_limit_w: float = 0.0
    harvest_primary_target_share: float = 0.0
    harvest_primary_required_w: float = 0.0
    harvest_primary_share_reserve_w: float = 0.0
    harvest_candidate_raw_w: float = 0.0
    harvest_candidate_after_primary_w: float = 0.0
    # RC16 / RC-B: make the SMA_FULL_OR_IDLE absolute-target calculation
    # reproducible without conflating a delta, a physical observation and an
    # absolute controller target.
    harvest_target_semantics: str = "NOT_APPLICABLE"
    harvest_reference_charge_w: float = 0.0
    harvest_reference_charge_source: str = "NONE"
    harvest_reference_charge_confidence: str = "NONE"
    harvest_reference_charge_age_s: Optional[float] = None
    harvest_reference_charge_valid: bool = False
    harvest_reference_fallback_reason: str = ""
    harvest_profile_reserve_w: float = 0.0
    harvest_candidate_delta_w: float = 0.0
    harvest_candidate_absolute_w: float = 0.0
    harvest_input_time_skew_s: Optional[float] = None
    # RC17: explicit 0-W network target and separated strategic/capture paths.
    harvest_network_target_w: float = 0.0
    harvest_total_available_charge_w: float = 0.0
    harvest_primary_share_target_w: float = 0.0
    harvest_zendure_share_target_w: float = 0.0
    harvest_export_capture_target_w: float = 0.0
    harvest_target_selected_by: str = "NOT_APPLICABLE"
    harvest_calculation_branch: str = "NOT_APPLICABLE"
    harvest_entry_min_export_w: float = 0.0
    harvest_command_path_eligible: bool = False
    harvest_command_path_block_reason: str = ""
    harvest_limiter_reason: str = ""
    harvest_capacity_mode: str = "off"
    primary_remaining_capacity_kwh: Optional[float] = None
    zendure_remaining_capacity_kwh: Optional[float] = None

    # Modus / Diagnose
    current_mode: str = "STARTUP"
    previous_mode: str = "STARTUP"
    mode_change_epoch: float = field(default_factory=time.time)
    last_mode_change_time: str = "-"
    last_mode_duration_seconds: int = 0
    control_reason: str = "Systemstart"
    technical_control_path: str = "-"
    active_limiters: List[str] = field(default_factory=list)
    last_control_action: str = "-"
    last_limit_reason: str = "-"
    charge_acceptance_state: str = "ok"
    charge_acceptance_reason: str = "Keine relevante Ladeanforderung."

    # Kommunikation
    mqtt_connected: bool = False
    last_mqtt_command: str = "-"
    last_mqtt_command_skipped: str = "-"
    mqtt_commands_sent: int = 0
    # RC3: Command-Lifecycle-Diagnose.  Ein erfolgreicher MQTT-Publish belegt
    # nur, dass der Broker die Nachricht angenommen hat; er belegt nicht, dass
    # die Zendure-Headunit den Befehl wirksam übernommen hat.  Diese Felder
    # machen unsichere Sends nach Restore/Broker-Neustart und ausbleibende
    # Gerätewirkung für UI/V4/Analyse sichtbar.
    command_uncertain_mqtt_active: bool = False
    command_uncertain_mqtt_since_epoch: Optional[float] = None
    command_uncertain_mqtt_since_time: str = "-"
    command_uncertain_mqtt_status: str = ""
    command_uncertain_mqtt_target_w: int = 0
    command_uncertain_mqtt_reason: str = ""
    command_resync_count: int = 0
    command_resync_last_time: str = "-"
    command_resync_reason: str = ""
    command_resync_suppressed_count: int = 0
    command_resync_suppressed_last_time: str = "-"
    command_resync_suppressed_reason: str = ""
    command_effect_category: str = "COMMAND_IDLE"
    command_effect_reason: str = "Kein aktiver Command-Effect-Watch."
    command_effect_reference_w: int = 0
    command_lifecycle_state: str = "IDLE"
    command_desired_sequence_id: int = 0
    command_desired_intent: str = "IDLE"
    command_desired_smart_mode: int = 1
    command_desired_ac_mode: str = ""
    command_desired_input_limit_w: int = 0
    command_desired_output_limit_w: int = 0
    command_desired_signed_target_w: int = 0
    command_desired_reason: str = ""
    command_desired_safety_relevant: bool = False
    command_publish_event: str = ""
    command_publish_last_time: str = "-"
    command_publish_fields: str = ""
    # RC13: Last-event snapshot fields above are made unambiguous by a
    # monotonically increasing event id and the epoch of the actual logical
    # publish batch. Follow-up measurement rows keep the same id/epoch.
    command_publish_event_id: int = 0
    command_publish_epoch_s: Optional[float] = None
    command_state_gate_state: str = "UNPROTECTED"
    command_state_retry_remaining_s: float = 0.0
    command_neutralization_episode_id: int = 0
    # RC15: read-back is evaluated independently from local publish history.
    command_readback_matches_desired: bool = False
    command_readback_mismatch_fields: str = "NOT_EVALUABLE"
    command_late_effect_guard_active: bool = False
    command_late_effect_guard_previous_intent: str = ""
    command_late_effect_guard_pending_intent: str = ""
    command_late_effect_guard_pending_target_w: int = 0
    command_late_effect_guard_duration_s: float = 0.0
    command_late_effect_guard_reason: str = ""
    command_late_effect_guard_activation_count: int = 0
    command_late_effect_guard_blocked_command_count: int = 0
    command_ac_mode_change_count: int = 0
    physical_power_direction_change_count: int = 0
    # Read-back of the complete Zendure command state.  Dynamic limit writes are
    # allowed only while smartMode=1 is fresh and the static command invariants
    # (AC mode and inactive limit) are confirmed.
    zendure_command_smart_mode: Optional[int] = None
    zendure_command_ac_mode: str = ""
    zendure_command_input_limit_w: Optional[int] = None
    zendure_command_output_limit_w: Optional[int] = None
    zendure_device_inverse_max_power_w: Optional[int] = None
    zendure_device_inverse_max_power_source: str = ""
    zendure_device_charge_max_limit_w: Optional[int] = None
    zendure_grid_off_mode: Optional[int] = None
    zendure_command_state_updated_epoch: Optional[float] = None
    zendure_command_smart_mode_updated_epoch: Optional[float] = None
    zendure_command_ac_mode_updated_epoch: Optional[float] = None
    zendure_command_input_limit_updated_epoch: Optional[float] = None
    zendure_command_output_limit_updated_epoch: Optional[float] = None
    zendure_device_inverse_max_power_updated_epoch: Optional[float] = None
    zendure_device_charge_max_limit_updated_epoch: Optional[float] = None
    zendure_grid_off_mode_updated_epoch: Optional[float] = None
    zendure_command_state_source: str = ""
    zendure_flash_protection_active: bool = False
    zendure_flash_protection_reason: str = "smartMode noch nicht bestätigt."
    zendure_command_state_complete: bool = False
    zendure_command_state_reason: str = "Command-State noch nicht vollständig rückgelesen."
    command_effect_confirmed: bool = False
    command_effect_confirmed_time: str = "-"
    command_effect_confirmed_reason: str = ""
    command_neutralization_active: bool = False
    command_neutralization_since_epoch: Optional[float] = None
    command_neutralization_since_time: str = "-"
    command_neutralization_reason: str = ""
    command_not_effective_active: bool = False
    command_not_effective_since_epoch: Optional[float] = None
    command_not_effective_since_time: str = "-"
    command_not_effective_duration_s: int = 0
    command_not_effective_reason: str = ""
    command_mismatch_resolution: str = ""
    consecutive_errors: int = 0
    last_error: str = "none"
    last_error_time: str = "-"
    safe_state_counter: int = 0
    controller_started_epoch: float = field(default_factory=time.time)
    last_cycle_completed_epoch: Optional[float] = None
    last_loop_duration_ms: float = 0.0
    last_cycle_total_ms: float = 0.0
    last_cycle_slowest_step: str = "none"
    last_cycle_slowest_step_ms: float = 0.0
    last_cycle_timing_json: str = "{}"
    last_cycle_timing_stats_json: str = "{}"
    cycle_timing_history: Deque[Dict[str, float]] = field(default_factory=lambda: deque(maxlen=60), repr=False)
    loop_counter: int = 0
    last_record_epoch: Optional[float] = None
    last_record_mqtt_commands_sent: int = 0

    # Zeitstempel / Staleness
    last_shelly_update_epoch: Optional[float] = None
    grid_power_sample_epoch: Optional[float] = None
    last_shelly_update_time: str = "-"
    last_soc_update_epoch: Optional[float] = None
    last_soc_update_time: str = "-"
    last_mqtt_soc_update_epoch: Optional[float] = None
    last_mqtt_soc_update_time: str = "-"
    last_mqtt_zendure_sensor_update_epoch: Optional[float] = None
    last_mqtt_zendure_sensor_update_time: str = "-"
    last_local_api_update_epoch: Optional[float] = None
    last_local_api_update_time: str = "-"
    last_local_api_error: str = "none"
    last_local_api_error_time: str = "-"
    last_sma_battery_update_epoch: Optional[float] = None
    last_sma_battery_update_time: str = "-"
    last_zendure_power_update_epoch: Optional[float] = None
    last_zendure_power_update_time: str = "-"

    # V12.12.2 productive single-owner diagnostics. The authoritative ownership
    # is the kernel flock; these fields only expose the active owner to health/UI.
    instance_owner_active: bool = False
    instance_owner_pid: Optional[int] = None
    instance_owner_build_id: str = ""
    instance_owner_since_utc: str = ""
    instance_owner_lock_path: str = ""

    # Batterie-Werte
    battery_soc: Optional[int] = None
    mqtt_battery_soc: Optional[int] = None
    local_api_soc: Optional[int] = None
    local_api_electric_level: Optional[int] = None
    local_api_pack_soc_level: Optional[int] = None
    zendure_telemetry_source: str = "none"
    zendure_local_api_fallback_active: bool = False
    # RC18 asynchronous local-API worker diagnostics. Monotonic timestamps are
    # retained only in memory; wall-clock values are used for display/logging.
    zendure_local_api_worker_state: str = "DISABLED"
    zendure_local_api_worker_config_generation: int = 0
    zendure_local_api_snapshot_sequence: int = 0
    zendure_local_api_success_sequence: int = 0
    zendure_local_api_new_success_applied: bool = False
    zendure_local_api_latest_attempt_ok: Optional[bool] = None
    zendure_local_api_last_attempt_epoch: Optional[float] = None
    zendure_local_api_last_attempt_monotonic: Optional[float] = None
    zendure_local_api_last_success_epoch: Optional[float] = None
    zendure_local_api_last_success_monotonic: Optional[float] = None
    zendure_local_api_snapshot_valid: bool = False
    zendure_local_api_snapshot_stale: bool = True
    zendure_local_api_snapshot_stale_after_s: float = 30.0
    zendure_local_api_request_duration_ms: Optional[float] = None
    zendure_local_api_last_request_duration_ms: Optional[float] = None
    zendure_local_api_snapshot_apply_ms: Optional[float] = None
    zendure_local_api_consecutive_errors: int = 0
    zendure_local_api_backoff_remaining_s: float = 0.0
    zendure_local_api_latest_error_code: str = "NONE"
    zendure_local_api_parse_warning_count: int = 0
    sma_battery_power: float = 0.0
    # Normierte Darstellungsleistung: positiv = Laden, negativ = Entladen.
    sma_battery_display_power: float = 0.0
    sma_battery_soc: Optional[float] = None
    sma_battery_capacity_kwh: Optional[float] = None
    sma_battery_discharge_power: float = 0.0
    second_battery_data_available: bool = False
    second_battery_data_fresh: bool = False
    second_battery_data_valid: bool = False
    second_battery_data_used_for_control: bool = False
    second_battery_data_age_seconds: Optional[int] = None
    second_battery_validity_reason: str = "SECOND_BATTERY_MISSING"
    evcc_data_available: bool = False

    # Direkte SMA Energy Meter / Sunny Home Manager Netzleistungsquelle
    sma_energy_meter_enabled: bool = False
    sma_energy_meter_running: bool = False
    sma_energy_meter_power_w: Optional[float] = None
    sma_energy_meter_consumption_power_w: Optional[float] = None
    sma_energy_meter_feedin_power_w: Optional[float] = None
    sma_energy_meter_last_epoch: Optional[float] = None
    sma_energy_meter_susy_id: Optional[int] = None
    sma_energy_meter_serial_number: Optional[int] = None
    sma_energy_meter_packet_count: int = 0
    sma_energy_meter_decode_count: int = 0
    sma_energy_meter_ignored_count: int = 0
    sma_energy_meter_error_count: int = 0
    sma_energy_meter_last_error: str = "none"
    sma_energy_meter_group: str = "239.12.255.254"
    sma_energy_meter_port: int = 9522
    sma_energy_meter_interface: str = ""
    sma_energy_meter_resolved_interface_ip: str = ""
    sma_energy_meter_configured_susy_id: str = ""
    sma_energy_meter_configured_serial: str = ""
    sma_energy_meter_selected_device_key: str = ""
    sma_energy_meter_selected_device_matched: bool = False
    sma_energy_meter_detected_device_count: int = 0
    sma_energy_meter_devices_json: str = "{}"
    sma_energy_meter_socket_mode: str = "group_bind"
    sma_energy_meter_effective_socket_mode: str = "group_bind"
    sma_energy_meter_bind_address: str = ""
    sma_energy_meter_bind_mode: str = ""
    sma_energy_meter_reuseaddr_enabled: bool = False
    sma_energy_meter_reuseport_requested: bool = False
    sma_energy_meter_reuseport_supported: bool = False
    sma_energy_meter_reuseport_enabled: bool = False
    sma_energy_meter_reuseport_error: str = ""
    sma_energy_meter_multicast_if_set: bool = False
    sma_energy_meter_packet_rate_per_min: float = 0.0
    sma_energy_meter_packet_gap_warn_s: float = 5.0
    sma_energy_meter_last_packet_gap_s: Optional[float] = None
    sma_energy_meter_max_packet_gap_s: Optional[float] = None
    sma_energy_meter_last_large_gap_s: Optional[float] = None
    sma_energy_meter_last_large_gap_age_seconds: Optional[int] = None

    # Einheitliches Freshness-/Validitätsmodell pro Regelzyklus.
    # Diese Felder ändern nicht die Regellogik selbst, sondern machen sichtbar,
    # welche externen Daten vorhanden, frisch, gültig und tatsächlich für die
    # Regelentscheidung genutzt wurden.
    soc_available: bool = False
    soc_fresh: bool = False
    soc_valid: bool = False
    soc_used_for_control: bool = False
    soc_age_seconds: Optional[int] = None
    soc_validity_reason: str = "SOC_MISSING"
    mqtt_command_path_available: bool = True
    mqtt_command_path_fresh: bool = False
    mqtt_command_path_valid: bool = False
    mqtt_command_path_used_for_control: bool = False
    mqtt_command_path_age_seconds: Optional[int] = None
    mqtt_command_path_validity_reason: str = "MQTT_DISCONNECTED"
    control_required_sources: List[str] = field(default_factory=list)
    control_missing_required_sources: List[str] = field(default_factory=list)
    control_data_quality: str = "not_evaluated"

    # Nachtmodus Reserve-/Stop-SOC. Der Stop-SOC ist eine laufende Untergrenze:
    # bei SOC <= Stop-SOC wird gestoppt, bei SOC > Stop-SOC darf im gleichen
    # Nachtfenster wieder entladen werden. Kein Latch, keine Hysterese.
    night_discharge_stop_soc_percent: Optional[int] = None
    night_discharge_stop_reason: str = "none"

    # Zendure Akkutemperaturen
    current_battery_temperature_c: Optional[float] = None
    highest_battery_temperature_c: Optional[float] = None
    highest_battery_temperature_time: str = "-"
    lowest_battery_temperature_c: Optional[float] = None
    lowest_battery_temperature_time: str = "-"
    zendure_pack_temperatures: List[Dict[str, Any]] = field(default_factory=list)
    zendure_battery_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Historien
    power_history: Deque[float] = field(default_factory=lambda: deque(maxlen=5))
    graph_history: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=300))
    event_history: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=50))
    mqtt_topic_diagnostics: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=200))

    # Interner Controller-Snapshot: Zendure MQTT Live-/Retained-/Partial-Stale-Diagnose.
    zendure_mqtt_connect_epoch: Optional[float] = None
    zendure_mqtt_disconnect_epoch: Optional[float] = None
    zendure_mqtt_topics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    zendure_mqtt_overall_status: str = "ZENDURE_MQTT_STALE"
    zendure_mqtt_status_reason: str = "Noch keine Zendure-MQTT-Daten empfangen."
    zendure_mqtt_live_confirmed: bool = False
    zendure_mqtt_retained_only: bool = False
    zendure_mqtt_partial_stale: bool = False
    zendure_mqtt_after_broker_restart_no_live_updates: bool = False
    zendure_mqtt_critical_data_age_s: Optional[int] = None
    zendure_mqtt_last_live_epoch_s: Optional[float] = None
    zendure_mqtt_last_received_epoch_s: Optional[float] = None
    zendure_mqtt_missing_critical_groups: str = ""
    zendure_mqtt_stale_critical_groups: str = ""

    # Interner Controller-Snapshot: Logging darf die Regelung nie blockieren.
    measurement_log_status: str = "disabled"
    measurement_log_status_reason: str = "Messdaten-Logging aus."
    measurement_estimated_retention_hours: Optional[float] = None
    measurement_current_file_size_bytes: int = 0
    measurement_free_disk_mb: Optional[int] = None
    measurement_log_path: str = ""
    measurement_log_target_type: str = ""
    measurement_log_active_target_type: str = ""
    measurement_fallback_active: bool = False
    measurement_fallback_count_since_start: int = 0
    measurement_last_fallback_time: str = ""
    measurement_last_fallback_reason: str = ""

    # RC17: SQLite Graph-/Measurement-Store, parallel zu CSV/V4.
    measurement_db_status: str = "idle"
    measurement_db_reason: str = "Noch kein DB-Schreibversuch."
    measurement_db_path: str = ""
    measurement_db_queue_depth: int = 0
    measurement_db_last_write_epoch_s: Any = ""
    measurement_db_last_write_duration_ms: Any = None
    measurement_db_error: str = ""
    measurement_db_last_error: str = ""
    measurement_db_last_error_epoch_s: Any = ""
    measurement_db_consecutive_failures: int = 0
    measurement_db_last_success_epoch_s: Any = ""
    measurement_db_write_stale: bool = False
    measurement_db_rows_written: int = 0
    measurement_db_rows_dropped: int = 0
    measurement_db_size_bytes: int = 0

    # Interner Controller-Snapshot: Istleistungs-Freshness.
    actual_zendure_power_valid: bool = False
    actual_zendure_power_age_s: Optional[int] = None
    actual_zendure_power_validity_reason: str = "ZENDURE_POWER_MISSING"

    def set_mode(self, new_mode: str) -> None:
        with self.lock:
            if new_mode != self.current_mode:
                self.previous_mode = self.current_mode
                self.current_mode = new_mode
                self.mode_change_epoch = time.time()
                self.last_mode_change_time = datetime.now().strftime("%H:%M:%S")
                self.add_event(f"Moduswechsel: {self.previous_mode} -> {new_mode}")
            self.last_mode_duration_seconds = int(time.time() - self.mode_change_epoch)

    def update_mode_duration(self) -> None:
        with self.lock:
            self.last_mode_duration_seconds = int(time.time() - self.mode_change_epoch)

    def add_event(self, text: str) -> None:
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            if self.event_history and self.event_history[-1].get("text") == text:
                self.event_history[-1]["time"] = timestamp
                self.event_history[-1]["count"] = int(self.event_history[-1].get("count", 1)) + 1
                return
            self.event_history.append({"time": timestamp, "text": text, "count": 1})

    def add_mqtt_diagnostic(
        self,
        topic: str,
        payload: str,
        limit: int = 200,
        *,
        diagnostic_filter: str = "",
        diagnostic_view_mode: str = "filtered",
        diagnostic_filter_matched: bool = False,
    ) -> None:
        with self.lock:
            if self.mqtt_topic_diagnostics.maxlen != limit:
                self.mqtt_topic_diagnostics = deque(self.mqtt_topic_diagnostics, maxlen=limit)
            self.mqtt_topic_diagnostics.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "topic": topic,
                "payload": payload[:500],
                "diagnostic_filter": diagnostic_filter,
                "diagnostic_view_mode": diagnostic_view_mode,
                "diagnostic_filter_matched": bool(diagnostic_filter_matched),
            })

    def clear_mqtt_diagnostics(self) -> int:
        """Clear buffered MQTT diagnostic rows and return the removed row count."""
        with self.lock:
            removed = len(self.mqtt_topic_diagnostics)
            self.mqtt_topic_diagnostics.clear()
            return removed

    def mark_zendure_mqtt_connect(self, now: Optional[float] = None) -> None:
        """Mark MQTT reconnect and reset per-connection live confirmation."""
        with self.lock:
            ts = now if now is not None else time.time()
            self.mqtt_connected = True
            self.zendure_mqtt_connect_epoch = ts
            self.zendure_mqtt_disconnect_epoch = None
            for info in self.zendure_mqtt_topics.values():
                info["message_count_since_connect"] = 0
                info["non_retained_seen_count_since_connect"] = 0
                info["retain_seen_count_since_connect"] = 0
                info["live_confirmed"] = False
            self.zendure_mqtt_live_confirmed = False
            self.zendure_mqtt_retained_only = False
            self.zendure_mqtt_partial_stale = False
            self.zendure_mqtt_after_broker_restart_no_live_updates = False
            self.invalidate_zendure_command_state("MQTT-Verbindung neu aufgebaut")

    def mark_zendure_mqtt_disconnect(self, now: Optional[float] = None) -> None:
        with self.lock:
            self.mqtt_connected = False
            self.zendure_mqtt_disconnect_epoch = now if now is not None else time.time()
            self.zendure_mqtt_live_confirmed = False
            self.invalidate_zendure_command_state("MQTT-Verbindung getrennt")

    def track_zendure_mqtt_topic(self, topic: str, payload: str, retain: bool, group: str, now: Optional[float] = None) -> None:
        """Track topic freshness and retained/live evidence for controller diagnostics."""
        if not topic.startswith("Zendure/"):
            return
        now_epoch = now if now is not None else time.time()
        digest = hashlib.sha256(str(payload).encode("utf-8", errors="replace")).hexdigest()[:16]
        with self.lock:
            info = self.zendure_mqtt_topics.get(topic, {
                "topic": topic,
                "topic_group": group,
                "first_received_at": None,
                "last_received_at": None,
                "age_s": None,
                "message_count": 0,
                "message_count_since_connect": 0,
                "last_payload_hash": None,
                "last_payload_changed_at": None,
                "payload_changed_age_s": None,
                "retain_flag": False,
                "retain_seen_count": 0,
                "retain_seen_count_since_connect": 0,
                "non_retained_seen_count": 0,
                "non_retained_seen_count_since_connect": 0,
                "live_confirmed": False,
            })
            if info.get("first_received_at") is None:
                info["first_received_at"] = round(now_epoch, 3)
            info["topic_group"] = group
            info["last_received_at"] = round(now_epoch, 3)
            info["message_count"] = int(info.get("message_count") or 0) + 1
            info["message_count_since_connect"] = int(info.get("message_count_since_connect") or 0) + 1
            info["retain_flag"] = bool(retain)
            if retain:
                info["retain_seen_count"] = int(info.get("retain_seen_count") or 0) + 1
                info["retain_seen_count_since_connect"] = int(info.get("retain_seen_count_since_connect") or 0) + 1
            else:
                info["non_retained_seen_count"] = int(info.get("non_retained_seen_count") or 0) + 1
                info["non_retained_seen_count_since_connect"] = int(info.get("non_retained_seen_count_since_connect") or 0) + 1
                info["live_confirmed"] = True
                self.zendure_mqtt_last_live_epoch_s = round(now_epoch, 3)
            if info.get("last_payload_hash") != digest:
                info["last_payload_hash"] = digest
                info["last_payload_changed_at"] = round(now_epoch, 3)
            self.zendure_mqtt_topics[topic] = info
            self.zendure_mqtt_last_received_epoch_s = round(now_epoch, 3)

    def _zendure_mqtt_group_summary_locked(self, now_epoch: float, timeout_s: int) -> Dict[str, Dict[str, Any]]:
        groups: Dict[str, Dict[str, Any]] = {}
        for topic, raw_info in self.zendure_mqtt_topics.items():
            info = dict(raw_info)
            group = str(info.get("topic_group") or "other")
            last_received = info.get("last_received_at")
            try:
                age_s = max(0, int(now_epoch - float(last_received))) if last_received is not None else None
            except Exception:
                age_s = None
            info["age_s"] = age_s
            last_changed = info.get("last_payload_changed_at")
            try:
                info["payload_changed_age_s"] = max(0, int(now_epoch - float(last_changed))) if last_changed is not None else None
            except Exception:
                info["payload_changed_age_s"] = None
            self.zendure_mqtt_topics[topic] = info
            g = groups.setdefault(group, {
                "topic_group": group,
                "topic_count": 0,
                "fresh_topic_count": 0,
                "live_confirmed": False,
                "retained_only": False,
                "last_received_at": None,
                "age_s": None,
                "topics": [],
            })
            g["topic_count"] += 1
            if age_s is not None and age_s <= timeout_s:
                g["fresh_topic_count"] += 1
            if bool(info.get("live_confirmed")):
                g["live_confirmed"] = True
            if int(info.get("message_count_since_connect") or 0) > 0 and int(info.get("non_retained_seen_count_since_connect") or 0) == 0:
                g["retained_only"] = True
            if last_received is not None and (g["last_received_at"] is None or float(last_received) > float(g["last_received_at"])):
                g["last_received_at"] = last_received
                g["age_s"] = age_s
            g["topics"].append(topic)
        return groups

    def update_zendure_mqtt_status(self, cfg: Dict[str, Any], now: Optional[float] = None) -> None:
        now_epoch = now if now is not None else time.time()
        timeout_s = int(cfg.get("ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS", cfg.get("ZENDURE_POWER_STALE_TIMEOUT_SECONDS", 90)))
        grace_s = int(cfg.get("ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS", min(timeout_s, 90)))
        required_groups = {"soc", "headunit_power"}
        with self.lock:
            groups = self._zendure_mqtt_group_summary_locked(now_epoch, timeout_s)
            missing = sorted(g for g in required_groups if g not in groups)
            stale = sorted(
                group for group, info in groups.items()
                if group in required_groups and (info.get("age_s") is None or int(info.get("age_s")) > timeout_s)
            )
            live_groups = {group for group, info in groups.items() if group in required_groups and bool(info.get("live_confirmed"))}
            retained_only_groups = {group for group, info in groups.items() if group in required_groups and bool(info.get("retained_only"))}
            last_critical_ages = [int(info.get("age_s")) for group, info in groups.items() if group in required_groups and info.get("age_s") is not None]
            self.zendure_mqtt_critical_data_age_s = max(last_critical_ages) if last_critical_ages else None
            self.zendure_mqtt_missing_critical_groups = ",".join(missing)
            self.zendure_mqtt_stale_critical_groups = ",".join(stale)
            self.zendure_mqtt_live_confirmed = required_groups.issubset(live_groups)
            self.zendure_mqtt_retained_only = bool(retained_only_groups) and not self.zendure_mqtt_live_confirmed
            self.zendure_mqtt_partial_stale = bool(stale) and bool(groups) and not set(stale).issuperset(required_groups)

            connect_age = None
            if self.zendure_mqtt_connect_epoch is not None:
                connect_age = max(0, int(now_epoch - float(self.zendure_mqtt_connect_epoch)))
            self.zendure_mqtt_after_broker_restart_no_live_updates = (
                bool(self.mqtt_connected)
                and connect_age is not None
                and connect_age > grace_s
                and not self.zendure_mqtt_live_confirmed
            )

            if not self.mqtt_connected:
                status = "ZENDURE_MQTT_STALE"
                reason = "MQTT nicht verbunden."
            elif self.zendure_mqtt_after_broker_restart_no_live_updates:
                status = "ZENDURE_MQTT_AFTER_BROKER_RESTART_NO_LIVE_UPDATES"
                reason = "Nach MQTT-Reconnect/Broker-Neustart keine nicht-retained Live-Werte aus kritischen Zendure-Gruppen."
            elif self.zendure_mqtt_retained_only:
                status = "ZENDURE_MQTT_RETAINED_ONLY"
                reason = "Kritische Zendure-Daten seit Reconnect nur als retained empfangen."
            elif missing or stale:
                status = "ZENDURE_MQTT_PARTIAL_STALE" if groups and not set(stale + missing).issuperset(required_groups) else "ZENDURE_MQTT_STALE"
                reason = "Fehlende/stale kritische Gruppen: " + ",".join(sorted(set(missing + stale)))
            else:
                status = "ZENDURE_MQTT_OK"
                reason = "Kritische Zendure-MQTT-Gruppen frisch und Live-Empfang bestätigt."
            self.zendure_mqtt_overall_status = status
            self.zendure_mqtt_status_reason = reason

    def zendure_mqtt_topic_groups_json(self) -> str:
        with self.lock:
            groups = self._zendure_mqtt_group_summary_locked(time.time(), 90)
            compact = {k: {kk: vv for kk, vv in v.items() if kk != "topics"} for k, v in groups.items()}
            return json.dumps(compact, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def zendure_mqtt_topics_json(self) -> str:
        with self.lock:
            return json.dumps(self.zendure_mqtt_topics, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def set_cycle_timing(self, timing_parts: Dict[str, Any], slowest_step: str, slowest_step_ms: float, total_ms: float) -> None:
        with self.lock:
            clean: Dict[str, float] = {}
            for key, value in (timing_parts or {}).items():
                try:
                    clean[str(key)] = round(float(value), 3)
                except Exception:
                    continue
            self.last_cycle_total_ms = round(float(total_ms or 0), 3)
            self.last_cycle_slowest_step = str(slowest_step or "none")
            self.last_cycle_slowest_step_ms = round(float(slowest_step_ms or 0), 3)
            self.last_cycle_completed_epoch = time.time()
            self.last_cycle_timing_json = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            self.cycle_timing_history.append(dict(clean))
            stats: Dict[str, Dict[str, float]] = {}
            all_keys = sorted({key for item in self.cycle_timing_history for key in item})
            for key in all_keys:
                values = sorted(float(item[key]) for item in self.cycle_timing_history if key in item)
                if not values:
                    continue
                count = len(values)
                p95_index = max(0, min(count - 1, int((count * 0.95) + 0.999999) - 1))
                stats[key] = {
                    "samples": count,
                    "mean_ms": round(sum(values) / count, 3),
                    "p95_ms": round(values[p95_index], 3),
                    "max_ms": round(values[-1], 3),
                }
            self.last_cycle_timing_stats_json = json.dumps(stats, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def set_measurement_log_status(self, status: Dict[str, Any]) -> None:
        with self.lock:
            self.measurement_log_status = str(status.get("measurement_log_status", self.measurement_log_status))
            self.measurement_log_status_reason = str(status.get("measurement_log_status_reason", self.measurement_log_status_reason))
            self.measurement_estimated_retention_hours = status.get("measurement_estimated_retention_hours", self.measurement_estimated_retention_hours)
            try:
                self.measurement_current_file_size_bytes = int(status.get("measurement_current_file_size_bytes", self.measurement_current_file_size_bytes) or 0)
            except Exception:
                pass
            self.measurement_free_disk_mb = status.get("measurement_free_disk_mb", self.measurement_free_disk_mb)
            self.measurement_log_path = str(status.get("measurement_log_path", self.measurement_log_path) or "")
            self.measurement_log_target_type = str(status.get("measurement_log_target_type", self.measurement_log_target_type) or "")
            self.measurement_log_active_target_type = str(status.get("measurement_log_active_target_type", self.measurement_log_active_target_type) or "")
            self.measurement_fallback_active = bool(status.get("measurement_fallback_active", self.measurement_fallback_active))
            try:
                self.measurement_fallback_count_since_start = int(status.get("measurement_fallback_count_since_start", self.measurement_fallback_count_since_start) or 0)
            except Exception:
                pass
            self.measurement_last_fallback_time = str(status.get("measurement_last_fallback_time", self.measurement_last_fallback_time) or "")
            self.measurement_last_fallback_reason = str(status.get("measurement_last_fallback_reason", self.measurement_last_fallback_reason) or "")
            self.measurement_db_status = str(status.get("measurement_db_status", self.measurement_db_status) or "")
            self.measurement_db_reason = str(status.get("measurement_db_reason", self.measurement_db_reason) or "")
            self.measurement_db_path = str(status.get("measurement_db_path", self.measurement_db_path) or "")
            try:
                self.measurement_db_queue_depth = int(status.get("measurement_db_queue_depth", self.measurement_db_queue_depth) or 0)
            except Exception:
                pass
            self.measurement_db_last_write_epoch_s = status.get("measurement_db_last_write_epoch_s", self.measurement_db_last_write_epoch_s)
            self.measurement_db_last_write_duration_ms = status.get("measurement_db_last_write_duration_ms", self.measurement_db_last_write_duration_ms)
            self.measurement_db_error = str(status.get("measurement_db_error", self.measurement_db_error) or "")
            self.measurement_db_last_error = str(status.get("measurement_db_last_error", self.measurement_db_last_error) or "")
            self.measurement_db_last_error_epoch_s = status.get("measurement_db_last_error_epoch_s", self.measurement_db_last_error_epoch_s)
            self.measurement_db_last_success_epoch_s = status.get("measurement_db_last_success_epoch_s", self.measurement_db_last_success_epoch_s)
            self.measurement_db_write_stale = bool(status.get("measurement_db_write_stale", self.measurement_db_write_stale))
            try:
                self.measurement_db_consecutive_failures = int(status.get("measurement_db_consecutive_failures", self.measurement_db_consecutive_failures) or 0)
            except Exception:
                pass
            try:
                self.measurement_db_rows_written = int(status.get("measurement_db_rows_written", self.measurement_db_rows_written) or 0)
            except Exception:
                pass
            try:
                self.measurement_db_rows_dropped = int(status.get("measurement_db_rows_dropped", self.measurement_db_rows_dropped) or 0)
            except Exception:
                pass
            try:
                self.measurement_db_size_bytes = int(status.get("measurement_db_size_bytes", self.measurement_db_size_bytes) or 0)
            except Exception:
                pass

    def set_error(self, message: str) -> None:
        with self.lock:
            self.last_error = message
            self.last_error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def mark_zendure_mqtt_sensor(self, now: float, now_text: str) -> None:
        with self.lock:
            self.last_mqtt_zendure_sensor_update_epoch = now
            self.last_mqtt_zendure_sensor_update_time = now_text

    def update_zendure_battery_metrics(self, source: str, battery_metrics: List[Dict[str, Any]], update_epoch: Optional[float] = None) -> None:
        """Merge Zendure battery/headunit metrics by serial number.

        MQTT and the local API are stored separately for temperature values. This
        avoids source ping-pong: a fresh MQTT temperature is not overwritten by a
        local-API diagnostic poll. The local API remains visible as diagnostic
        source, but the displayed temperature prefers MQTT while MQTT is fresh.
        """
        with self.lock:
            now_epoch = time.time() if update_epoch is None else float(update_epoch)
            now_text = datetime.fromtimestamp(now_epoch).strftime("%Y-%m-%d %H:%M:%S")
            updated = False

            def source_is_fresh(src_info: Dict[str, Any], timeout_seconds: int = 120) -> bool:
                epoch = src_info.get("update_epoch")
                if epoch is None:
                    return False
                try:
                    return (now_epoch - float(epoch)) <= timeout_seconds
                except Exception:
                    return False

            def select_temperature_source(entry: Dict[str, Any]) -> None:
                sources = entry.get("temperature_sources") or {}
                selected_name = None
                selected_info = None

                mqtt_info = sources.get("MQTT")
                if mqtt_info and source_is_fresh(mqtt_info):
                    selected_name = "MQTT"
                    selected_info = mqtt_info
                elif sources:
                    # Fallback: choose the newest source available.
                    selected_name, selected_info = max(
                        sources.items(),
                        key=lambda kv: float(kv[1].get("update_epoch") or 0.0),
                    )

                if selected_info:
                    entry["temperature_c"] = selected_info.get("temperature_c")
                    entry["temperature_source"] = selected_name
                    entry["temperature_raw"] = selected_info.get("raw_value")
                    entry["temperature_update_time"] = selected_info.get("update_time")

            for item in battery_metrics:
                pack_sn = str(item.get("pack_sn") or item.get("sn") or "unknown")
                if not pack_sn:
                    continue
                entry = self.zendure_battery_details.get(pack_sn, {
                    "pack_sn": pack_sn,
                    "temperature_c": None,
                    "temperature_source": "-",
                    "temperature_raw": None,
                    "temperature_update_time": "-",
                    "temperature_sources": {},
                    "power_w": None,
                    "power_source": "-",
                    "soc_percent": None,
                    "state": None,
                    "data_source": source,
                    "last_update_time": "-",
                    "highest_temperature_c": None,
                    "highest_temperature_time": "-",
                    "lowest_temperature_c": None,
                    "lowest_temperature_time": "-",
                })

                if "temperature_c" in item and item.get("temperature_c") is not None:
                    try:
                        temp_f = round(float(item.get("temperature_c")), 1)
                        raw_value = item.get("temperature_raw", item.get("raw_value", item.get("temperature_c")))
                        sources = entry.get("temperature_sources") or {}
                        sources[source] = {
                            "temperature_c": temp_f,
                            "raw_value": raw_value,
                            "update_time": now_text,
                            "update_epoch": now_epoch,
                        }
                        entry["temperature_sources"] = sources
                        select_temperature_source(entry)
                        selected_temp = entry.get("temperature_c")
                        if selected_temp is not None:
                            selected_temp = float(selected_temp)
                            if entry.get("highest_temperature_c") is None or selected_temp > float(entry.get("highest_temperature_c")):
                                entry["highest_temperature_c"] = selected_temp
                                entry["highest_temperature_time"] = now_text
                            if entry.get("lowest_temperature_c") is None or selected_temp < float(entry.get("lowest_temperature_c")):
                                entry["lowest_temperature_c"] = selected_temp
                                entry["lowest_temperature_time"] = now_text
                    except Exception:
                        pass

                if "power_w" in item and item.get("power_w") is not None:
                    try:
                        entry["power_w"] = int(float(item.get("power_w")))
                        entry["power_source"] = source
                    except Exception:
                        pass

                if "soc_percent" in item and item.get("soc_percent") is not None:
                    try:
                        entry["soc_percent"] = int(float(item.get("soc_percent")))
                    except Exception:
                        pass

                if "state" in item and item.get("state") is not None:
                    entry["state"] = str(item.get("state"))

                entry["data_source"] = source
                entry["last_update_time"] = now_text
                self.zendure_battery_details[pack_sn] = entry
                updated = True

            if updated:
                # Re-select displayed temperature for all batteries on every update,
                # so MQTT can expire and local API can take over without restart.
                for entry in self.zendure_battery_details.values():
                    select_temperature_source(entry)

                def sort_key(e: Dict[str, Any]) -> str:
                    sn = str(e.get("pack_sn", ""))
                    if sn == "headunit" or sn == str(getattr(self, "device_id", "")) or sn.startswith("HEC"):
                        return "0" + sn
                    return "1" + sn

                details = sorted(self.zendure_battery_details.values(), key=sort_key)
                self.zendure_pack_temperatures = [
                    {
                        "pack_sn": e.get("pack_sn"),
                        "temperature_c": e.get("temperature_c"),
                        "source": e.get("temperature_source") or e.get("data_source") or "-",
                        "temperature_raw": e.get("temperature_raw"),
                        "temperature_sources": e.get("temperature_sources", {}),
                        "highest_temperature_c": e.get("highest_temperature_c"),
                        "highest_temperature_time": e.get("highest_temperature_time"),
                        "lowest_temperature_c": e.get("lowest_temperature_c"),
                        "lowest_temperature_time": e.get("lowest_temperature_time"),
                    }
                    for e in details
                    if e.get("temperature_c") is not None
                ]
                current_values = [float(e["temperature_c"]) for e in details if e.get("temperature_c") is not None]
                if current_values:
                    self.current_battery_temperature_c = max(current_values)
                    if self.highest_battery_temperature_c is None or max(current_values) > self.highest_battery_temperature_c:
                        self.highest_battery_temperature_c = max(current_values)
                        self.highest_battery_temperature_time = now_text
                    if self.lowest_battery_temperature_c is None or min(current_values) < self.lowest_battery_temperature_c:
                        self.lowest_battery_temperature_c = min(current_values)
                        self.lowest_battery_temperature_time = now_text

    def update_zendure_temperature(self, source: str, pack_temperatures: List[Dict[str, Any]]) -> None:
        self.update_zendure_battery_metrics(source, pack_temperatures)

    @staticmethod
    def _normalize_zendure_command_property(name: str, value: Any) -> Any:
        key = str(name or "")
        if key == "smartMode":
            if isinstance(value, str):
                text = value.strip().upper()
                if text == "ON":
                    return 1
                if text == "OFF":
                    return 0
            try:
                return 1 if int(float(value)) == 1 else 0
            except Exception:
                return None
        if key == "acMode":
            if isinstance(value, str):
                text = value.strip()
                if text in {"Input mode", "Output mode"}:
                    return text
                try:
                    value = int(float(text))
                except Exception:
                    return ""
            try:
                numeric = int(value)
            except Exception:
                return ""
            return "Input mode" if numeric == 1 else "Output mode" if numeric == 2 else ""
        if key in {"inputLimit", "outputLimit", "inverseMaxPower", "chargeMaxLimit", "gridOffMode"}:
            try:
                return int(round(float(value)))
            except Exception:
                return None
        return value

    def update_zendure_command_property(self, name: str, value: Any, source: str, now: Optional[float] = None) -> None:
        """Update read-back state for a Zendure command/configuration property."""
        key = str(name or "")
        normalized = self._normalize_zendure_command_property(key, value)
        if normalized is None or (key == "acMode" and not normalized):
            return
        epoch = time.time() if now is None else float(now)
        mapping = {
            "smartMode": ("zendure_command_smart_mode", "zendure_command_smart_mode_updated_epoch"),
            "acMode": ("zendure_command_ac_mode", "zendure_command_ac_mode_updated_epoch"),
            "inputLimit": ("zendure_command_input_limit_w", "zendure_command_input_limit_updated_epoch"),
            "outputLimit": ("zendure_command_output_limit_w", "zendure_command_output_limit_updated_epoch"),
            "inverseMaxPower": ("zendure_device_inverse_max_power_w", "zendure_device_inverse_max_power_updated_epoch"),
            "chargeMaxLimit": ("zendure_device_charge_max_limit_w", "zendure_device_charge_max_limit_updated_epoch"),
            "gridOffMode": ("zendure_grid_off_mode", "zendure_grid_off_mode_updated_epoch"),
        }
        target = mapping.get(key)
        if target is None:
            return
        with self.lock:
            setattr(self, target[0], normalized)
            setattr(self, target[1], epoch)
            if key == "inverseMaxPower":
                self.zendure_device_inverse_max_power_source = str(source or "UNKNOWN")
            self.zendure_command_state_updated_epoch = epoch
            self.zendure_command_state_source = str(source or "UNKNOWN")
            self._refresh_zendure_command_state_locked(epoch)

    def _refresh_zendure_command_state_locked(self, now: Optional[float] = None, max_age_s: float = 30.0) -> None:
        epoch = time.time() if now is None else float(now)
        max_age = max(1.0, float(max_age_s))

        def fresh(value: Any, updated: Optional[float]) -> bool:
            return value is not None and updated is not None and (epoch - float(updated)) <= max_age

        smart_fresh = fresh(self.zendure_command_smart_mode, self.zendure_command_smart_mode_updated_epoch)
        ac_fresh = bool(self.zendure_command_ac_mode) and fresh(self.zendure_command_ac_mode, self.zendure_command_ac_mode_updated_epoch)
        input_fresh = fresh(self.zendure_command_input_limit_w, self.zendure_command_input_limit_updated_epoch)
        output_fresh = fresh(self.zendure_command_output_limit_w, self.zendure_command_output_limit_updated_epoch)
        self.zendure_flash_protection_active = bool(smart_fresh and self.zendure_command_smart_mode == 1)
        if self.zendure_flash_protection_active:
            self.zendure_flash_protection_reason = "smartMode=1 frisch rückgelesen; dynamische Änderungen werden nicht in Flash geschrieben."
        elif smart_fresh:
            self.zendure_flash_protection_reason = "smartMode=0 rückgelesen; dynamische Leistungsbefehle sind bis zur Aktivierung gesperrt."
        else:
            self.zendure_flash_protection_reason = "smartMode nicht frisch bestätigt; dynamische Leistungsbefehle sind bis zur Rücklesung gesperrt."
        self.zendure_command_state_complete = bool(smart_fresh and ac_fresh and input_fresh and output_fresh)
        if self.zendure_command_state_complete:
            self.zendure_command_state_reason = "smartMode, acMode, inputLimit und outputLimit frisch rückgelesen."
        else:
            missing = []
            if not smart_fresh:
                missing.append("smartMode")
            if not ac_fresh:
                missing.append("acMode")
            if not input_fresh:
                missing.append("inputLimit")
            if not output_fresh:
                missing.append("outputLimit")
            self.zendure_command_state_reason = "Nicht frisch bestätigt: " + ", ".join(missing)

    def zendure_command_state_snapshot(self, max_age_s: float = 30.0, now: Optional[float] = None) -> Dict[str, Any]:
        with self.lock:
            epoch = time.time() if now is None else float(now)
            self._refresh_zendure_command_state_locked(epoch, max_age_s=max_age_s)
            return {
                "smart_mode": self.zendure_command_smart_mode,
                "ac_mode": self.zendure_command_ac_mode,
                "input_limit_w": self.zendure_command_input_limit_w,
                "output_limit_w": self.zendure_command_output_limit_w,
                "inverse_max_power_w": self.zendure_device_inverse_max_power_w,
                "inverse_max_power_source": self.zendure_device_inverse_max_power_source,
                "inverse_max_power_updated_epoch": self.zendure_device_inverse_max_power_updated_epoch,
                "charge_max_limit_w": self.zendure_device_charge_max_limit_w,
                "grid_off_mode": self.zendure_grid_off_mode,
                "flash_protection_active": self.zendure_flash_protection_active,
                "complete": self.zendure_command_state_complete,
                "reason": self.zendure_command_state_reason,
                "source": self.zendure_command_state_source,
            }

    def invalidate_zendure_command_state(self, reason: str = "MQTT reconnect") -> None:
        """Require fresh read-back before incremental dynamic control resumes."""
        with self.lock:
            self.zendure_command_smart_mode_updated_epoch = None
            self.zendure_command_ac_mode_updated_epoch = None
            self.zendure_command_input_limit_updated_epoch = None
            self.zendure_command_output_limit_updated_epoch = None
            self.zendure_command_state_updated_epoch = None
            self.zendure_flash_protection_active = False
            self.zendure_flash_protection_reason = f"{reason}: smartMode muss neu bestätigt werden."
            self.zendure_command_state_complete = False
            self.zendure_command_state_reason = f"{reason}: vollständiger Command-State muss neu rückgelesen werden."

    def update_zendure_headunit_power(self, source: str, pack_input: Any = None, output_home: Any = None, grid_input: Any = None, output_pack: Any = None, grid_off: Any = None, solar_input: Any = None, update_epoch: Optional[float] = None) -> None:
        """Update and separate Zendure grid, battery and off-grid power flows.

        The compatibility field ``actual_zendure_system_signed_power`` now
        describes only the grid-connected AC port: positive means AC import via
        ``gridInputPower`` and negative means export via ``outputHomePower``.
        Battery charge/discharge (``outputPackPower``/``packInputPower``) and
        ``gridOffPower`` remain orthogonal so an off-grid load cannot masquerade
        as house export or failed grid-side neutralisation.
        """
        with self.lock:
            def to_int(value: Any) -> Optional[int]:
                if value is None:
                    return None
                try:
                    return int(float(value))
                except Exception:
                    return None

            pi = to_int(pack_input)
            oh = to_int(output_home)
            gi = to_int(grid_input)
            op = to_int(output_pack)
            go = to_int(grid_off)
            si = to_int(solar_input)
            now = time.time() if update_epoch is None else float(update_epoch)
            if pi is not None:
                self.actual_zendure_charge_power = pi
                self.actual_zendure_pack_input_update_epoch = now
            if oh is not None:
                self.actual_zendure_discharge_power = oh
                self.actual_zendure_output_home_update_epoch = now
            if gi is not None:
                self.actual_zendure_grid_input_power = gi
                self.actual_zendure_grid_input_update_epoch = now
            if op is not None:
                self.actual_zendure_output_pack_power = op
                self.actual_zendure_output_pack_update_epoch = now
            if go is not None:
                self.actual_zendure_grid_off_power = go
                self.actual_zendure_grid_off_update_epoch = now
            if si is not None:
                self.actual_zendure_solar_input_power = si
                self.actual_zendure_solar_input_update_epoch = now

            self._refresh_zendure_headunit_power_locked(now=now)

            self.last_zendure_power_update_epoch = now
            self.last_zendure_power_update_time = datetime.fromtimestamp(now).strftime("%H:%M:%S")

    def _refresh_zendure_headunit_power_locked(self, now: Optional[float] = None) -> None:
        now = time.time() if now is None else float(now)
        derived = derive_zendure_actual_power(
            pack_input=self.actual_zendure_charge_power,
            output_home=self.actual_zendure_discharge_power,
            grid_input=self.actual_zendure_grid_input_power,
            output_pack=self.actual_zendure_output_pack_power,
            requested_input_limit=self.last_input_power,
            requested_output_limit=self.last_output_power,
        )
        self.actual_zendure_system_charge_power = derived["charge_power_w"]
        self.actual_zendure_system_discharge_power = derived["discharge_power_w"]
        self.actual_zendure_system_signed_power = derived["signed_power_w"]
        self.zendure_grid_import_power_w = derived["charge_power_w"]
        self.zendure_grid_output_power_w = derived["discharge_power_w"]
        self.zendure_grid_signed_power_w = derived["signed_power_w"]
        self.zendure_battery_charge_power_w = derived["battery_charge_power_w"]
        self.zendure_battery_discharge_power_w = derived["battery_discharge_power_w"]
        self.zendure_battery_signed_power_w = derived["battery_signed_power_w"]
        self.zendure_offgrid_power_w = max(0, int(self.actual_zendure_grid_off_power or 0))

        # Raw Zendure topics do not necessarily arrive in the same MQTT packet.
        # Never let an old non-zero explicit sensor determine the direction of a
        # fresh packInputPower sample.  Fifteen seconds is deliberately shorter
        # than the general power-stale timeout; ambiguous data stays ambiguous
        # instead of being made certain by a stale companion topic.
        evidence_max_age_s = 15.0

        def fresh_value(value: int, epoch: Optional[float]) -> Optional[int]:
            if epoch is None or (now - float(epoch)) > evidence_max_age_s:
                return None
            return value

        observation_inputs = {
            "pack_input": fresh_value(self.actual_zendure_charge_power, self.actual_zendure_pack_input_update_epoch),
            "output_home": fresh_value(self.actual_zendure_discharge_power, self.actual_zendure_output_home_update_epoch),
            "grid_input": fresh_value(self.actual_zendure_grid_input_power, self.actual_zendure_grid_input_update_epoch),
            "output_pack": fresh_value(self.actual_zendure_output_pack_power, self.actual_zendure_output_pack_update_epoch),
            "grid_off": fresh_value(self.actual_zendure_grid_off_power, self.actual_zendure_grid_off_update_epoch),
            "solar_input": fresh_value(self.actual_zendure_solar_input_power, self.actual_zendure_solar_input_update_epoch),
        }
        observation = derive_zendure_power_observation(**observation_inputs)
        source_epochs = [
            epoch for value, epoch in (
                (observation_inputs["pack_input"], self.actual_zendure_pack_input_update_epoch),
                (observation_inputs["output_home"], self.actual_zendure_output_home_update_epoch),
                (observation_inputs["grid_input"], self.actual_zendure_grid_input_update_epoch),
                (observation_inputs["output_pack"], self.actual_zendure_output_pack_update_epoch),
                (observation_inputs["grid_off"], self.actual_zendure_grid_off_update_epoch),
                (observation_inputs["solar_input"], self.actual_zendure_solar_input_update_epoch),
            ) if value is not None and epoch is not None
        ]
        direction = str(observation["direction"])
        # Command-effect direction belongs to the grid-connected AC boundary.
        # Battery/off-grid flows are orthogonal and therefore cannot make a
        # neutral grid command look ineffective.
        if direction == "CHARGE":
            observation_epoch = self.actual_zendure_grid_input_update_epoch
        elif direction == "DISCHARGE":
            observation_epoch = self.actual_zendure_output_home_update_epoch
        elif direction == "CONFLICT":
            epochs = [
                epoch for value, epoch in (
                    (observation_inputs["grid_input"], self.actual_zendure_grid_input_update_epoch),
                    (observation_inputs["output_home"], self.actual_zendure_output_home_update_epoch),
                ) if value is not None and abs(int(value)) >= 20 and epoch is not None
            ]
            observation_epoch = min(epochs) if epochs else None
        else:
            grid_epochs = [
                epoch for value, epoch in (
                    (observation_inputs["grid_input"], self.actual_zendure_grid_input_update_epoch),
                    (observation_inputs["output_home"], self.actual_zendure_output_home_update_epoch),
                ) if value is not None and epoch is not None
            ]
            observation_epoch = max(grid_epochs) if grid_epochs else (max(source_epochs) if source_epochs else None)
        self.zendure_power_observation_direction = direction
        self.zendure_power_observation_confidence = str(observation["confidence"])
        self.zendure_power_observation_signed_w = observation["signed_power_w"]
        self.zendure_power_observation_magnitude_w = int(observation["magnitude_w"] or 0)
        self.zendure_power_observation_reason = str(observation["reason"])
        self.zendure_power_observation_updated_epoch = observation_epoch
        self.zendure_battery_signed_power_w = int(observation.get("battery_signed_power_w") or 0)
        self.zendure_battery_charge_power_w = int(observation.get("battery_charge_power_w") or 0)
        self.zendure_battery_discharge_power_w = int(observation.get("battery_discharge_power_w") or 0)
        self.zendure_offgrid_power_w = int(observation.get("offgrid_power_w") or 0)
        self.zendure_offgrid_active = bool(observation.get("offgrid_active"))
        self.zendure_power_balance_residual_w = int(observation.get("power_balance_residual_w") or 0)

    def refresh_zendure_headunit_power(self) -> None:
        """Recalculate Zendure actual power from the latest raw sensors and limits.

        MQTT/API raw sensors can arrive before a later control decision changes
        requested input/output limits. Recalculate once per control cycle so UI,
        graph and CSV do not show a stale sign after mode changes.
        """
        with self.lock:
            self._refresh_zendure_headunit_power_locked()

    def reset_active_limiters(self) -> None:
        with self.lock:
            self.active_limiters = []
            self.last_limit_reason = "none"

    def reset_night_discharge_stop_reason(self) -> None:
        with self.lock:
            if self.night_discharge_stop_reason != "none":
                self.night_discharge_stop_reason = "none"

    def add_limiter(self, limiter: str) -> None:
        with self.lock:
            if limiter not in self.active_limiters:
                self.active_limiters.append(limiter)
            self.last_limit_reason = ", ".join(self.active_limiters) if self.active_limiters else "none"

    def set_control_source_requirements(self, required_sources: List[str]) -> None:
        """Store the data sources required by the selected mode/path."""
        with self.lock:
            ordered: List[str] = []
            for source in required_sources:
                source_name = str(source).strip()
                if source_name and source_name not in ordered:
                    ordered.append(source_name)
            self.control_required_sources = ordered

    def update_data_validity_model(self, cfg: Dict[str, Any]) -> None:
        """Refresh per-cycle freshness/validity fields for external data.

        This is intentionally diagnostic/contract logic: existing mode handlers
        still decide whether to Safe-State, hold, charge or discharge. The model
        makes those decisions auditable for UI, graph, CSV and tests.
        """
        now_epoch = time.time()
        with self.lock:
            grid_status = timestamp_status(
                "grid",
                self.last_shelly_update_epoch,
                cfg.get("SHELLY_STALE_TIMEOUT_SECONDS", 15),
                has_value=self.last_shelly_update_epoch is not None,
                used_for_control=self.grid_power_used_for_control,
                now_epoch=now_epoch,
                missing_reason="GRID_MISSING",
                stale_reason="GRID_STALE",
            )
            soc_status = timestamp_status(
                "soc",
                self.last_soc_update_epoch,
                cfg.get("SOC_STALE_TIMEOUT_SECONDS", 90),
                has_value=self.battery_soc is not None,
                used_for_control=self.soc_used_for_control,
                now_epoch=now_epoch,
                missing_reason="SOC_MISSING",
                stale_reason="SOC_STALE",
            )
            mqtt_status = boolean_status(
                "mqtt_command_path",
                self.mqtt_connected,
                used_for_control=self.mqtt_command_path_used_for_control,
                false_reason="MQTT_DISCONNECTED",
            )
            second_status = timestamp_status(
                "second_battery",
                self.last_sma_battery_update_epoch,
                cfg.get("SECOND_BATTERY_STALE_TIMEOUT_SECONDS", cfg.get("EVCC_STALE_TIMEOUT_SECONDS", 30)),
                has_value=self.evcc_data_available and self.last_sma_battery_update_epoch is not None,
                used_for_control=self.second_battery_data_used_for_control,
                now_epoch=now_epoch,
                missing_reason="SECOND_BATTERY_MISSING",
                stale_reason="SECOND_BATTERY_STALE",
            )
            zendure_power_status = timestamp_status(
                "zendure_power",
                self.last_zendure_power_update_epoch,
                cfg.get("ZENDURE_POWER_STALE_TIMEOUT_SECONDS", 90),
                has_value=self.last_zendure_power_update_epoch is not None,
                used_for_control=False,
                now_epoch=now_epoch,
                missing_reason="ZENDURE_POWER_MISSING",
                stale_reason="ZENDURE_POWER_STALE",
            )

            self.grid_power_available = grid_status.available
            self.grid_power_fresh = grid_status.fresh
            self.grid_power_valid = grid_status.valid
            self.grid_power_age_seconds = grid_status.age_s
            self.grid_power_validity_reason = grid_status.reason

            self.soc_available = soc_status.available
            self.soc_fresh = soc_status.fresh
            self.soc_valid = soc_status.valid
            self.soc_age_seconds = soc_status.age_s
            self.soc_validity_reason = soc_status.reason

            self.mqtt_command_path_available = mqtt_status.available
            self.mqtt_command_path_fresh = mqtt_status.fresh
            self.mqtt_command_path_valid = mqtt_status.valid
            self.mqtt_command_path_age_seconds = mqtt_status.age_s
            self.mqtt_command_path_validity_reason = mqtt_status.reason

            self.second_battery_data_available = second_status.available
            self.second_battery_data_fresh = second_status.fresh
            self.second_battery_data_valid = second_status.valid
            self.second_battery_data_age_seconds = second_status.age_s
            self.second_battery_validity_reason = second_status.reason
            self.actual_zendure_power_valid = zendure_power_status.valid
            self.actual_zendure_power_age_s = zendure_power_status.age_s
            self.actual_zendure_power_validity_reason = zendure_power_status.reason

            source_status = {
                "grid": grid_status,
                "soc": soc_status,
                "mqtt_command_path": mqtt_status,
                "second_battery": second_status,
            }
            self.control_missing_required_sources = [
                source for source in self.control_required_sources
                if source_status.get(source) is not None and not source_status[source].valid
            ]
            self.control_data_quality = "ok" if not self.control_missing_required_sources else "missing_required_data"

        self.update_zendure_mqtt_status(cfg)

    def update_power_history(self, value: float, samples: int) -> float:
        with self.lock:
            if self.power_history.maxlen != samples:
                self.power_history = deque(self.power_history, maxlen=samples)
            self.power_history.append(value)
            return sum(self.power_history) / len(self.power_history)

    def ensure_graph_limit(self, limit: int) -> None:
        with self.lock:
            if self.graph_history.maxlen != limit:
                self.graph_history = deque(self.graph_history, maxlen=limit)

    def record_graph_point(self, graph_limit: int) -> None:
        with self.lock:
            self.ensure_graph_limit(graph_limit)
            now_dt = datetime.now()
            now_epoch = time.time()
            if self.last_record_epoch is None:
                dt_s = 0.0
            else:
                dt_s = max(0.0, now_epoch - self.last_record_epoch)
            self.last_record_epoch = now_epoch
            active_limiters = list(self.active_limiters)
            target_signed = signed_zendure_target_w(self.last_input_power, self.last_output_power)
            self.zendure_target_signed_power = target_signed
            mqtt_commands_in_cycle = max(0, int(self.mqtt_commands_sent) - int(self.last_record_mqtt_commands_sent))
            self.last_record_mqtt_commands_sent = int(self.mqtt_commands_sent)

            def signed_stage(value: Any) -> int:
                try:
                    magnitude = int(float(value or 0))
                except Exception:
                    magnitude = 0
                if self.last_output_power > 0 and self.last_input_power <= 0:
                    return -abs(magnitude)
                return abs(magnitude) if self.last_input_power > 0 else magnitude

            scenario_valid = bool(self.grid_power_valid and self.actual_zendure_power_valid)
            scenario_without_zendure = round(float(self.grid_power) - float(self.actual_zendure_system_signed_power), 1)
            scenario_reason = "OK" if scenario_valid else "GRID_OR_ZENDURE_ACTUAL_INVALID"
            target_error = target_signed - int(self.actual_zendure_system_signed_power or 0)
            command_sent = mqtt_commands_in_cycle > 0
            command_required = bool(self.mqtt_command_path_used_for_control)
            # Publish activity and physical effect are independent dimensions.
            # A cycle without a new publish must not erase an open mismatch, and
            # a resync cycle must not replace MISMATCH/RECOVERY_VERIFYING with
            # "no_command" or "not_evaluable".
            effect_category = str(self.command_effect_category or "")
            effect_reason = str(self.command_effect_reason or "")
            if not effect_category:
                if command_sent:
                    effect_category = "COMMAND_PENDING"
                    effect_reason = "Kommando gesendet; physische Wirkung wird über Folgezyklen bewertet."
                elif command_required:
                    effect_category = "COMMAND_IDLE"
                    effect_reason = self.last_mqtt_command_skipped or "Kein neues MQTT-Kommando erforderlich; bestehender Sollzustand bleibt aktiv."
                else:
                    effect_category = "COMMAND_IDLE"
                    effect_reason = "Kein aktiver Command-Effect-Watch."
            if self.command_uncertain_mqtt_active and effect_category not in {
                "COMMAND_MISMATCH_CONFIRMED",
                "COMMAND_NEUTRALIZATION_MISMATCH",
                "COMMAND_RECOVERY_VERIFYING",
            }:
                effect_category = "COMMAND_TELEMETRY_UNCERTAIN"
                effect_reason = self.command_uncertain_mqtt_reason or "Aktiver Sollwert wurde bei unsicherem Zendure-MQTT-Zustand gesendet."
            if self.command_not_effective_active and effect_category not in {
                "COMMAND_RECOVERY_VERIFYING",
                "COMMAND_NEUTRALIZATION_MISMATCH",
            }:
                effect_category = "COMMAND_MISMATCH_CONFIRMED"
                effect_reason = self.command_not_effective_reason or "Aktiver Sollwert zeigt keine erkennbare Gerätewirkung."

            effect_valid = effect_category in {
                "COMMAND_TARGET_TRACKING_EFFECTIVE",
                "COMMAND_NEUTRALIZATION_CONFIRMED",
            }

            unit = {
                "unit_id": "primary",
                "target_w": target_signed,
                "actual_power_w": self.actual_zendure_system_signed_power,
                "soc_percent": self.battery_soc,
                "freshness": self.zendure_mqtt_overall_status,
                "command_path_valid": self.mqtt_command_path_valid,
            }

            row = {
                # Schema / Zeitbasis
                "controller_version": APP_VERSION,
                "date": now_dt.strftime("%Y-%m-%d"),
                "timestamp": now_dt.strftime("%H:%M:%S"),
                "datetime_local": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "epoch": round(now_epoch, 3),
                "dt_s": round(dt_s, 3),
                "measurement_profile": "standard",
                "controller_version_label": f"V{APP_VERSION}",
                "cycle_id": self.loop_counter,
                "epoch_s": round(now_epoch, 3),

                # Messwerte / signierte Hauptwerte
                "raw_grid_power_w": round(self.raw_grid_power, 1),
                "raw_grid_power_meaning": power_flow_meaning(self.raw_grid_power, "Netzbezug", "Einspeisung"),
                "grid_power_w": round(self.grid_power, 1),
                "grid_power_meaning": power_flow_meaning(self.grid_power, "Netzbezug", "Einspeisung"),
                "grid_power_available": self.grid_power_available,
                "grid_power_fresh": self.grid_power_fresh,
                "grid_power_valid": self.grid_power_valid,
                "grid_power_used_for_control": self.grid_power_used_for_control,
                "grid_power_age_s": self.grid_power_age_seconds,
                "grid_power_validity_reason": self.grid_power_validity_reason,
                "raw_grid_source": self.raw_grid_source,
                "raw_grid_age_s": self.grid_power_age_seconds,
                "raw_zendure_soc_percent": self.battery_soc,
                "raw_zendure_soc_source": self.zendure_telemetry_source,
                "raw_zendure_soc_age_s": self.soc_age_seconds,
                "raw_zendure_battery_temperature_c": self.current_battery_temperature_c,
                "raw_second_battery_power_w": round(self.sma_battery_power, 1),
                "raw_second_battery_soc_percent": self.sma_battery_soc,
                "raw_second_battery_capacity_kwh": self.sma_battery_capacity_kwh,
                "raw_second_battery_source": "EVCC/SMA" if self.evcc_data_available else "none",
                "raw_second_battery_age_s": self.second_battery_data_age_seconds,
                "norm_grid_power_w": round(self.grid_power, 1),
                "norm_grid_power_smoothed_w": round(self.grid_power, 1),
                "norm_zendure_soc_percent": self.battery_soc,
                "norm_zendure_actual_power_w": self.actual_zendure_system_signed_power,
                "norm_zendure_actual_charge_power_w": self.actual_zendure_system_charge_power,
                "norm_zendure_actual_discharge_power_w": self.actual_zendure_system_discharge_power,
                "norm_second_battery_power_w": round(self.sma_battery_display_power, 1),
                "norm_second_battery_discharge_power_w": round(self.sma_battery_discharge_power, 1),
                "norm_effective_export_power_w": self.effective_export_power,
                "input_grid_power_used_w": round(self.grid_power, 1) if self.grid_power_used_for_control else "",
                "input_grid_power_used_for_control": self.grid_power_used_for_control,
                "input_soc_used_percent": self.battery_soc if self.soc_used_for_control else "",
                "input_soc_used_for_control": self.soc_used_for_control,
                "input_effective_export_used_w": self.effective_export_power if self.effective_export_power_used_for_control else "",
                "input_effective_export_used_for_control": self.effective_export_power_used_for_control,
                "input_second_battery_power_used_w": round(self.sma_battery_display_power, 1) if self.second_battery_data_used_for_control else "",
                "input_second_battery_used_for_control": self.second_battery_data_used_for_control,
                "input_mqtt_command_path_used_for_control": self.mqtt_command_path_used_for_control,
                "zendure_target_power_w": target_signed,
                "zendure_actual_power_w": self.actual_zendure_system_signed_power,
                "second_battery_power_w": round(self.sma_battery_display_power, 1),
                "second_battery_power_meaning": sma_power_meaning(self.sma_battery_display_power),

                # Kompatibilitäts-/UI-Aliasse im RAM-Graphen
                "raw_grid_power": round(self.raw_grid_power, 1),
                "grid_power": round(self.grid_power, 1),
                "charge_power": self.last_input_power,
                "discharge_power": self.last_output_power,
                "zendure_system_signed_power": self.actual_zendure_system_signed_power,
                "sma_battery_display_power": round(self.sma_battery_display_power, 1),
                "sma_battery_power": round(self.sma_battery_power, 1),

                # Zendure Rohsensoren / Diagnose
                "zendure_raw_grid_input_power_w": self.actual_zendure_grid_input_power,
                "zendure_raw_pack_input_power_w": self.actual_zendure_charge_power,
                "zendure_raw_output_home_power_w": self.actual_zendure_discharge_power,
                "zendure_raw_output_pack_power_w": self.actual_zendure_output_pack_power,
                "zendure_raw_grid_off_power_w": self.actual_zendure_grid_off_power,
                "zendure_raw_solar_input_power_w": self.actual_zendure_solar_input_power,
                "zendure_grid_signed_power_w": self.zendure_grid_signed_power_w,
                "zendure_grid_import_power_w": self.zendure_grid_import_power_w,
                "zendure_grid_output_power_w": self.zendure_grid_output_power_w,
                "zendure_battery_signed_power_w": self.zendure_battery_signed_power_w,
                "zendure_battery_charge_power_w": self.zendure_battery_charge_power_w,
                "zendure_battery_discharge_power_w": self.zendure_battery_discharge_power_w,
                "zendure_offgrid_power_w": self.zendure_offgrid_power_w,
                "zendure_offgrid_active": self.zendure_offgrid_active,
                "zendure_power_balance_residual_w": self.zendure_power_balance_residual_w,
                "zendure_actual_charge_power_w": self.actual_zendure_system_charge_power,
                "zendure_actual_discharge_power_w": self.actual_zendure_system_discharge_power,
                "actual_zendure_charge_power": self.actual_zendure_charge_power,
                "actual_zendure_discharge_power": self.actual_zendure_discharge_power,
                "actual_zendure_grid_input_power": self.actual_zendure_grid_input_power,
                "actual_zendure_output_pack_power": self.actual_zendure_output_pack_power,
                "zendure_pack_power": self.actual_zendure_charge_power,
                "zendure_ac_home_power": self.actual_zendure_discharge_power,
                "zendure_telemetry_source": self.zendure_telemetry_source,
                "zendure_api_fallback_active": self.zendure_local_api_fallback_active,
                "zendure_local_api_snapshot_sequence": self.zendure_local_api_snapshot_sequence,
                "zendure_local_api_success_sequence": self.zendure_local_api_success_sequence,
                "zendure_local_api_new_success_applied": self.zendure_local_api_new_success_applied,
                "zendure_local_api_last_success_age_s": (
                    round(max(0.0, time.monotonic() - self.zendure_local_api_last_success_monotonic), 3)
                    if self.zendure_local_api_last_success_monotonic is not None else None
                ),
                "zendure_local_api_snapshot_valid": self.zendure_local_api_snapshot_valid,
                "zendure_local_api_snapshot_stale": self.zendure_local_api_snapshot_stale,
                "zendure_local_api_request_duration_ms": self.zendure_local_api_request_duration_ms,
                "zendure_local_api_snapshot_apply_ms": self.zendure_local_api_snapshot_apply_ms,
                "battery_temperature_c": self.current_battery_temperature_c,

                # Zweitbatterie / Cross-Charge
                "second_battery_raw_power_w": round(self.sma_battery_power, 1),
                "second_battery_discharge_power_w": round(self.sma_battery_discharge_power, 1),
                "second_battery_data_available": self.second_battery_data_available,
                "second_battery_data_fresh": self.second_battery_data_fresh,
                "second_battery_data_valid": self.second_battery_data_valid,
                "second_battery_used_for_control": self.second_battery_data_used_for_control,
                "second_battery_age_s": self.second_battery_data_age_seconds,
                "second_battery_validity_reason": self.second_battery_validity_reason,
                "second_battery_available": self.second_battery_data_available,
                "second_battery_fresh": self.second_battery_data_fresh,
                "second_battery_valid": self.second_battery_data_valid,
                "scenario_grid_without_zendure_w": scenario_without_zendure,
                "scenario_removed_zendure_power_w": self.actual_zendure_system_signed_power,
                "scenario_reconstruction_valid": scenario_valid,
                "scenario_reconstruction_reason": scenario_reason,
                "scenario_includes_sma_effect": True,
                "scenario_includes_evcc_effect": True,
                "second_battery_soc_percent": self.sma_battery_soc,
                "second_battery_capacity_kwh": self.sma_battery_capacity_kwh,
                "sma_battery_power_meaning": sma_power_meaning(self.sma_battery_display_power),
                "sma_battery_discharge_power": round(self.sma_battery_discharge_power, 1),
                "effective_export_power_w": self.effective_export_power,
                "effective_export_power": self.effective_export_power,
                "effective_export_power_valid": self.effective_export_power_valid,
                "effective_export_power_used_for_control": self.effective_export_power_used_for_control,
                "effective_export_meaning": "Für Zendure-Ladung verfügbarer Überschuss nach Zusatzbatterie-Abzug und Sicherheitsreserve",
                "rest_surplus_harvest_active": self.rest_surplus_harvest_active,
                "rest_surplus_harvest_eligible": self.rest_surplus_harvest_eligible,
                "rest_surplus_harvest_reason": self.rest_surplus_harvest_reason,
                "rest_surplus_harvest_block_reason": self.rest_surplus_harvest_block_reason,
                "rest_surplus_harvest_profile": self.rest_surplus_harvest_profile,
                "rest_surplus_entry_progress_s": round(float(self.rest_surplus_entry_progress_s or 0.0), 1),
                "rest_surplus_hold_remaining_s": round(float(self.rest_surplus_hold_remaining_s or 0.0), 1),
                "rest_surplus_exit_reason": self.rest_surplus_exit_reason,
                "second_battery_charge_pressure_w": round(float(self.second_battery_charge_pressure_w or 0.0), 1),
                "second_battery_charge_saturation_threshold_w": round(float(self.second_battery_charge_saturation_threshold_w or 0.0), 1),
                "rest_surplus_export_w": round(float(self.rest_surplus_export_w or 0.0), 1),
                "harvest_primary_floor_w": round(float(self.harvest_primary_floor_w or 0.0), 1),
                "harvest_primary_restart_w": round(float(self.harvest_primary_restart_w or 0.0), 1),
                "harvest_primary_near_limit_w": round(float(self.harvest_primary_near_limit_w or 0.0), 1),
                "harvest_primary_target_share": round(float(self.harvest_primary_target_share or 0.0), 3),
                "harvest_primary_required_w": round(float(self.harvest_primary_required_w or 0.0), 1),
                "harvest_primary_share_reserve_w": round(float(self.harvest_primary_share_reserve_w or 0.0), 1),
                "harvest_candidate_raw_w": round(float(self.harvest_candidate_raw_w or 0.0), 1),
                "harvest_candidate_after_primary_w": round(float(self.harvest_candidate_after_primary_w or 0.0), 1),
                "harvest_target_semantics": self.harvest_target_semantics,
                "harvest_reference_charge_w": round(float(self.harvest_reference_charge_w or 0.0), 1),
                "harvest_reference_charge_source": self.harvest_reference_charge_source,
                "harvest_reference_charge_confidence": self.harvest_reference_charge_confidence,
                "harvest_reference_charge_age_s": (
                    None if self.harvest_reference_charge_age_s is None
                    else round(float(self.harvest_reference_charge_age_s), 1)
                ),
                "harvest_reference_charge_valid": self.harvest_reference_charge_valid,
                "harvest_reference_fallback_reason": self.harvest_reference_fallback_reason,
                "harvest_profile_reserve_w": round(float(self.harvest_profile_reserve_w or 0.0), 1),
                "harvest_candidate_delta_w": round(float(self.harvest_candidate_delta_w or 0.0), 1),
                "harvest_candidate_absolute_w": round(float(self.harvest_candidate_absolute_w or 0.0), 1),
                "harvest_input_time_skew_s": (
                    None if self.harvest_input_time_skew_s is None
                    else round(float(self.harvest_input_time_skew_s), 1)
                ),
                "harvest_network_target_w": round(float(self.harvest_network_target_w or 0.0), 1),
                "harvest_total_available_charge_w": round(float(self.harvest_total_available_charge_w or 0.0), 1),
                "harvest_primary_share_target_w": round(float(self.harvest_primary_share_target_w or 0.0), 1),
                "harvest_zendure_share_target_w": round(float(self.harvest_zendure_share_target_w or 0.0), 1),
                "harvest_export_capture_target_w": round(float(self.harvest_export_capture_target_w or 0.0), 1),
                "harvest_target_selected_by": self.harvest_target_selected_by,
                "harvest_calculation_branch": self.harvest_calculation_branch,
                "harvest_entry_min_export_w": round(float(self.harvest_entry_min_export_w or 0.0), 1),
                "harvest_command_path_eligible": self.harvest_command_path_eligible,
                "harvest_command_path_block_reason": self.harvest_command_path_block_reason,
                "harvest_limiter_reason": self.harvest_limiter_reason,
                "harvest_capacity_mode": self.harvest_capacity_mode,
                "primary_remaining_capacity_kwh": None if self.primary_remaining_capacity_kwh is None else round(float(self.primary_remaining_capacity_kwh), 3),
                "zendure_remaining_capacity_kwh": None if self.zendure_remaining_capacity_kwh is None else round(float(self.zendure_remaining_capacity_kwh), 3),

                # SOC / Modus / Reglerpfad
                "zendure_soc_percent": self.battery_soc,
                "soc_available": self.soc_available,
                "soc_fresh": self.soc_fresh,
                "soc_valid": self.soc_valid,
                "soc_used_for_control": self.soc_used_for_control,
                "soc_age_s": self.soc_age_seconds,
                "soc_validity_reason": self.soc_validity_reason,
                "mqtt_command_path_valid": self.mqtt_command_path_valid,
                "mqtt_command_path_used_for_control": self.mqtt_command_path_used_for_control,
                "mqtt_command_path_validity_reason": self.mqtt_command_path_validity_reason,
                "mqtt_command_path_available": self.mqtt_command_path_available,
                "mqtt_command_path_fresh": self.mqtt_command_path_fresh,
                "mqtt_command_path_age_s": self.mqtt_command_path_age_seconds,
                "control_required_sources": ",".join(self.control_required_sources),
                "control_missing_required_sources": ",".join(self.control_missing_required_sources),
                "control_data_quality": self.control_data_quality,
                "soc": self.battery_soc,
                "sma_soc": self.sma_battery_soc,
                "mode": self.current_mode,
                "mode_label": mode_label(self.current_mode),
                "previous_mode": self.previous_mode,
                "mode_duration_s": self.last_mode_duration_seconds,
                "control_path": self.technical_control_path,
                "control_path_label": path_label(self.technical_control_path),
                "deadband_active": self.current_mode in {"HOLD", "HOLD_DEADBAND"} or "DEADBAND" in self.technical_control_path,
                "cross_charge_guard_active": "CROSS_CHARGE" in self.technical_control_path or any(x in active_limiters for x in ("CROSS_CHARGE", "SMA_DISCHARGE")),
                "cross_charge_guard_limited": "CROSS_CHARGE" in self.technical_control_path or any(x in active_limiters for x in ("CROSS_CHARGE", "SMA_DISCHARGE")),
                "night_discharge_window_active": self.current_mode == "NIGHT_DISCHARGE" or self.night_discharge_stop_reason != "none",
                "night_discharge_base_active": self.current_mode == "NIGHT_DISCHARGE",
                "night_discharge_reserve_active": "NIGHT_RESERVE_SOC" in active_limiters or self.night_discharge_stop_reason != "none",
                "min_soc_limiter_active": "MIN_SOC" in active_limiters,
                "max_soc_limiter_active": "MAX_SOC" in active_limiters,
                "safe_state_active": self.current_mode == "SAFE_STATE",
                "target_limiters_summary": technical_limiter_text(active_limiters),
                "target_raw_w": signed_stage(self.last_target_before_smoothing),
                "target_after_deadband_w": signed_stage(self.last_target_before_smoothing),
                "target_after_cross_charge_w": target_signed,
                "target_after_power_limit_w": signed_stage(self.last_target_after_power_limit),
                "target_after_soc_limits_w": signed_stage(self.last_target_after_power_limit),
                "target_power_limit_reason": self.target_power_limit_reason,
                "target_after_smoothing_w": signed_stage(self.last_target_after_smoothing),
                "target_after_ramp_w": signed_stage(self.last_target_after_ramp),
                "target_final_w": target_signed,
                "target_final_reason": self.control_reason,
                "target_before_smoothing_w": self.last_target_before_smoothing,
                "target_after_smoothing_w": self.last_target_after_smoothing,
                "target_after_ramp_w": self.last_target_after_ramp,
                "target_before_smoothing": self.last_target_before_smoothing,
                "target_after_smoothing": self.last_target_after_smoothing,
                "target_after_ramp": self.last_target_after_ramp,
                "control_action": self.last_control_action,
                "limit_reason": self.last_limit_reason,
                "limit_label": limiter_text(active_limiters),
                "technical_limiters": technical_limiter_text(active_limiters),
                "technical_path": self.technical_control_path,
                "technical_path_label": path_label(self.technical_control_path),
                "control_reason": self.control_reason,
                "night_discharge_stop_soc_percent": self.night_discharge_stop_soc_percent,
                "night_discharge_stop_reason": self.night_discharge_stop_reason,

                # MQTT-Kommandodynamik / Diagnose
                "mqtt_command_required": command_required,
                "mqtt_command_sent": command_sent,
                "mqtt_command_skipped": (not command_sent) and bool(self.last_mqtt_command_skipped and self.last_mqtt_command_skipped != "-"),
                "mqtt_command_skip_reason": self.last_mqtt_command_skipped,
                "mqtt_command_signed_target_w": target_signed,
                "mqtt_command_input_limit_w": self.last_input_power,
                "mqtt_command_output_limit_w": self.last_output_power,
                "mqtt_command_result": "sent" if command_sent else "skipped_or_not_required",
                "mqtt_command_sequence": self.mqtt_commands_sent,
                "zendure_mqtt_overall_status": self.zendure_mqtt_overall_status,
                "zendure_mqtt_status_reason": self.zendure_mqtt_status_reason,
                "zendure_mqtt_connected": self.mqtt_connected,
                "zendure_mqtt_live_confirmed": self.zendure_mqtt_live_confirmed,
                "zendure_mqtt_retained_only": self.zendure_mqtt_retained_only,
                "zendure_mqtt_partial_stale": self.zendure_mqtt_partial_stale,
                "zendure_mqtt_after_broker_restart_no_live_updates": self.zendure_mqtt_after_broker_restart_no_live_updates,
                "zendure_mqtt_critical_data_age_s": self.zendure_mqtt_critical_data_age_s,
                "zendure_mqtt_last_live_epoch_s": self.zendure_mqtt_last_live_epoch_s,
                "zendure_mqtt_last_received_epoch_s": self.zendure_mqtt_last_received_epoch_s,
                "zendure_mqtt_missing_critical_groups": self.zendure_mqtt_missing_critical_groups,
                "zendure_mqtt_stale_critical_groups": self.zendure_mqtt_stale_critical_groups,
                "mqtt_commands_sent_total": self.mqtt_commands_sent,
                "mqtt_commands_sent_in_cycle": mqtt_commands_in_cycle,
                "mqtt_last_command": self.last_mqtt_command,
                "mqtt_last_command_skipped": self.last_mqtt_command_skipped,
                "last_mqtt_command": self.last_mqtt_command,
                "last_mqtt_command_skipped": self.last_mqtt_command_skipped,
                "command_uncertain_mqtt_active": self.command_uncertain_mqtt_active,
                "command_uncertain_mqtt_since_time": self.command_uncertain_mqtt_since_time,
                "command_uncertain_mqtt_status": self.command_uncertain_mqtt_status,
                "command_uncertain_mqtt_target_w": self.command_uncertain_mqtt_target_w,
                "command_uncertain_mqtt_reason": self.command_uncertain_mqtt_reason,
                "command_resync_count": self.command_resync_count,
                "command_resync_last_time": self.command_resync_last_time,
                "command_resync_reason": self.command_resync_reason,
                "command_resync_suppressed_count": self.command_resync_suppressed_count,
                "command_resync_suppressed_last_time": self.command_resync_suppressed_last_time,
                "command_resync_suppressed_reason": self.command_resync_suppressed_reason,
                "command_effect_state_category": self.command_effect_category,
                "command_effect_state_reason": self.command_effect_reason,
                "command_effect_reference_w": self.command_effect_reference_w,
                "command_lifecycle_state": self.command_lifecycle_state,
                "command_desired_sequence_id": self.command_desired_sequence_id,
                "command_desired_intent": self.command_desired_intent,
                "command_desired_smart_mode": self.command_desired_smart_mode,
                "command_desired_ac_mode": self.command_desired_ac_mode,
                "command_desired_input_limit_w": self.command_desired_input_limit_w,
                "command_desired_output_limit_w": self.command_desired_output_limit_w,
                "command_desired_signed_target_w": self.command_desired_signed_target_w,
                "command_desired_reason": self.command_desired_reason,
                "command_desired_safety_relevant": self.command_desired_safety_relevant,
                "command_publish_event": self.command_publish_event,
                "command_publish_last_time": self.command_publish_last_time,
                "command_publish_fields": self.command_publish_fields,
                "command_publish_event_id": self.command_publish_event_id,
                "command_publish_epoch_s": self.command_publish_epoch_s,
                "command_state_gate_state": self.command_state_gate_state,
                "command_state_retry_remaining_s": self.command_state_retry_remaining_s,
                "command_neutralization_episode_id": self.command_neutralization_episode_id,
                "command_readback_matches_desired": self.command_readback_matches_desired,
                "command_readback_mismatch_fields": self.command_readback_mismatch_fields,
                "command_late_effect_guard_active": self.command_late_effect_guard_active,
                "command_late_effect_guard_previous_intent": self.command_late_effect_guard_previous_intent,
                "command_late_effect_guard_pending_intent": self.command_late_effect_guard_pending_intent,
                "command_late_effect_guard_pending_target_w": self.command_late_effect_guard_pending_target_w,
                "command_late_effect_guard_duration_s": self.command_late_effect_guard_duration_s,
                "command_late_effect_guard_reason": self.command_late_effect_guard_reason,
                "command_late_effect_guard_activation_count": self.command_late_effect_guard_activation_count,
                "command_late_effect_guard_blocked_command_count": self.command_late_effect_guard_blocked_command_count,
                "command_ac_mode_change_count": self.command_ac_mode_change_count,
                "physical_power_direction_change_count": self.physical_power_direction_change_count,
                "command_effect_confirmed": self.command_effect_confirmed,
                "command_effect_confirmed_time": self.command_effect_confirmed_time,
                "command_effect_confirmed_reason": self.command_effect_confirmed_reason,
                "command_neutralization_active": self.command_neutralization_active,
                "command_neutralization_since_time": self.command_neutralization_since_time,
                "command_neutralization_reason": self.command_neutralization_reason,
                "command_mismatch_resolution": self.command_mismatch_resolution,
                "zendure_command_smart_mode": self.zendure_command_smart_mode,
                "zendure_command_ac_mode": self.zendure_command_ac_mode,
                "zendure_command_input_limit_w": self.zendure_command_input_limit_w,
                "zendure_command_output_limit_w": self.zendure_command_output_limit_w,
                "zendure_device_inverse_max_power_w": self.zendure_device_inverse_max_power_w,
                "zendure_device_inverse_max_power_source": self.zendure_device_inverse_max_power_source,
                "zendure_device_inverse_max_power_age_s": (
                    round(max(0.0, now_epoch - float(self.zendure_device_inverse_max_power_updated_epoch)), 1)
                    if self.zendure_device_inverse_max_power_updated_epoch is not None else ""
                ),
                "zendure_device_charge_max_limit_w": self.zendure_device_charge_max_limit_w,
                "zendure_grid_off_mode": self.zendure_grid_off_mode,
                "zendure_flash_protection_active": self.zendure_flash_protection_active,
                "zendure_flash_protection_reason": self.zendure_flash_protection_reason,
                "zendure_command_state_complete": self.zendure_command_state_complete,
                "zendure_command_state_reason": self.zendure_command_state_reason,
                "zendure_command_state_source": self.zendure_command_state_source,
                "zendure_power_observation_direction": self.zendure_power_observation_direction,
                "zendure_power_observation_confidence": self.zendure_power_observation_confidence,
                "zendure_power_observation_signed_w": self.zendure_power_observation_signed_w,
                "zendure_power_observation_magnitude_w": self.zendure_power_observation_magnitude_w,
                "zendure_power_observation_age_s": (
                    round(max(0.0, now_epoch - float(self.zendure_power_observation_updated_epoch)), 1)
                    if self.zendure_power_observation_updated_epoch is not None else ""
                ),
                "zendure_power_observation_reason": self.zendure_power_observation_reason,
                "controller_started_epoch": self.controller_started_epoch,
                "last_cycle_completed_epoch": self.last_cycle_completed_epoch,
                "loop_duration_ms": self.last_loop_duration_ms,
                "cycle_total_without_sleep_ms": self.last_cycle_total_ms,
                "cycle_slowest_step": self.last_cycle_slowest_step,
                "cycle_slowest_step_ms": self.last_cycle_slowest_step_ms,
                "cycle_timing_json": self.last_cycle_timing_json,
                "cycle_timing_stats_json": self.last_cycle_timing_stats_json,
                "loop_counter": self.loop_counter,
                "last_error": self.last_error,
                "last_error_time": self.last_error_time,

                # High-SOC-Ladeannahme-Diagnose
                "charge_acceptance_state": self.charge_acceptance_state,
                "charge_acceptance_reason": self.charge_acceptance_reason,
                "actual_zendure_power_w": self.actual_zendure_system_signed_power,
                "actual_zendure_power_valid": self.actual_zendure_power_valid,
                "actual_zendure_power_age_s": self.actual_zendure_power_age_s,
                "actual_target_error_w": target_error,
                "actual_target_error_abs_w": abs(target_error),
                "command_effect_valid": effect_valid,
                "command_effect_category": effect_category,
                "command_effect_reason": effect_reason,
                "command_not_effective_active": self.command_not_effective_active,
                "command_not_effective_since_time": self.command_not_effective_since_time,
                "command_not_effective_duration_s": self.command_not_effective_duration_s,
                "command_not_effective_reason": self.command_not_effective_reason,
                "measurement_log_status": self.measurement_log_status,
                "measurement_log_status_reason": self.measurement_log_status_reason,
                "measurement_estimated_retention_hours": self.measurement_estimated_retention_hours,
                "measurement_current_file_size_bytes": self.measurement_current_file_size_bytes,
                "measurement_free_disk_mb": self.measurement_free_disk_mb,
                "measurement_log_path": self.measurement_log_path,
                "measurement_log_target_type": self.measurement_log_target_type,
                "measurement_log_active_target_type": self.measurement_log_active_target_type,
                "measurement_fallback_active": self.measurement_fallback_active,
                "measurement_fallback_count_since_start": self.measurement_fallback_count_since_start,
                "measurement_last_fallback_time": self.measurement_last_fallback_time,
                "measurement_last_fallback_reason": self.measurement_last_fallback_reason,
                "measurement_db_status": self.measurement_db_status,
                "measurement_db_reason": self.measurement_db_reason,
                "measurement_db_path": self.measurement_db_path,
                "measurement_db_queue_depth": self.measurement_db_queue_depth,
                "measurement_db_last_write_epoch_s": self.measurement_db_last_write_epoch_s,
                "measurement_db_last_write_duration_ms": self.measurement_db_last_write_duration_ms,
                "measurement_db_error": self.measurement_db_error,
                "measurement_db_last_error": self.measurement_db_last_error,
                "measurement_db_last_error_epoch_s": self.measurement_db_last_error_epoch_s,
                "measurement_db_consecutive_failures": self.measurement_db_consecutive_failures,
                "measurement_db_last_success_epoch_s": self.measurement_db_last_success_epoch_s,
                "measurement_db_write_stale": self.measurement_db_write_stale,
                "measurement_db_rows_written": self.measurement_db_rows_written,
                "measurement_db_rows_dropped": self.measurement_db_rows_dropped,
                "measurement_db_size_bytes": self.measurement_db_size_bytes,
                "zendure_unit_count": 1,
                "zendure_aggregate_target_w": target_signed,
                "zendure_aggregate_actual_power_w": self.actual_zendure_system_signed_power,
                "zendure_aggregate_soc_percent": self.battery_soc,
                "zendure_aggregate_capacity_kwh": "",
                "zendure_aggregate_freshness": self.zendure_mqtt_overall_status,
                "zendure_units_json": json.dumps([unit], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                "target_limiters_json": json.dumps(active_limiters, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                "control_decision_json": json.dumps({"mode": self.current_mode, "path": self.technical_control_path, "action": self.last_control_action, "reason": self.control_reason}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                "freshness_details_json": json.dumps({"grid": self.grid_power_validity_reason, "soc": self.soc_validity_reason, "mqtt_command_path": self.mqtt_command_path_validity_reason, "second_battery": self.second_battery_validity_reason, "zendure_power": self.actual_zendure_power_validity_reason}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                "zendure_pack_data_json": json.dumps(list(self.zendure_battery_details.values()), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                "zendure_mqtt_topic_groups_json": self.zendure_mqtt_topic_groups_json(),
                "zendure_mqtt_topics_json": self.zendure_mqtt_topics_json(),
            }
            self.graph_history.append(row)

    def readiness_snapshot(self, command_state_max_age_s: float = 30.0) -> Dict[str, Any]:
        """Return the bounded subset required by /ready and config recovery.

        The control loop calls this every cycle for Stable-Ready observation;
        unlike ``snapshot()`` it never copies graph/event histories or builds
        large diagnostic JSON structures.
        """
        with self.lock:
            now_epoch = time.time()

            def age_seconds(epoch_value: Optional[float]) -> Optional[int]:
                if epoch_value is None:
                    return None
                return max(0, int(now_epoch - epoch_value))

            # Refresh the command-state freshness against the same wall clock
            # used for all other bounded readiness ages. No history or I/O is
            # touched here.
            self._refresh_zendure_command_state_locked(now_epoch, max_age_s=command_state_max_age_s)
            return {
                "uptime_seconds": int(now_epoch - self.startup_epoch),
                "instance_owner_active": self.instance_owner_active,
                "instance_owner_pid": self.instance_owner_pid,
                "instance_owner_build_id": self.instance_owner_build_id,
                "instance_owner_since_utc": self.instance_owner_since_utc,
                "instance_owner_lock_path": self.instance_owner_lock_path,
                "mqtt_connected": self.mqtt_connected,
                "last_shelly_update_age_seconds": age_seconds(self.last_shelly_update_epoch),
                "grid_power_valid": self.grid_power_valid,
                "grid_power_validity_reason": self.grid_power_validity_reason,
                "battery_soc": self.battery_soc,
                "last_soc_update_age_seconds": age_seconds(self.last_soc_update_epoch),
                "soc_valid": self.soc_valid,
                "soc_validity_reason": self.soc_validity_reason,
                "zendure_telemetry_source": self.zendure_telemetry_source,
                "zendure_local_api_fallback_active": self.zendure_local_api_fallback_active,
                "last_sma_battery_update_age_seconds": age_seconds(self.last_sma_battery_update_epoch),
                "second_battery_valid": self.second_battery_data_valid,
                "second_battery_validity_reason": self.second_battery_validity_reason,
                "mqtt_command_path_available": self.mqtt_command_path_available,
                "mqtt_command_path_fresh": self.mqtt_command_path_fresh,
                "mqtt_command_path_valid": self.mqtt_command_path_valid,
                "mqtt_command_path_age_seconds": self.mqtt_command_path_age_seconds,
                "mqtt_command_path_validity_reason": self.mqtt_command_path_validity_reason,
                "actual_zendure_power_valid": self.actual_zendure_power_valid,
                "actual_zendure_power_age_s": self.actual_zendure_power_age_s,
                "actual_zendure_power_validity_reason": self.actual_zendure_power_validity_reason,
                "zendure_command_state_complete": self.zendure_command_state_complete,
                "zendure_command_state_reason": self.zendure_command_state_reason,
                "zendure_command_state_source": self.zendure_command_state_source,
                "zendure_command_smart_mode": self.zendure_command_smart_mode,
                "zendure_command_ac_mode": self.zendure_command_ac_mode,
                "zendure_command_input_limit_w": self.zendure_command_input_limit_w,
                "zendure_command_output_limit_w": self.zendure_command_output_limit_w,
                "command_desired_sequence_id": self.command_desired_sequence_id,
                "command_desired_ac_mode": self.command_desired_ac_mode,
                "command_desired_input_limit_w": self.command_desired_input_limit_w,
                "command_desired_output_limit_w": self.command_desired_output_limit_w,
                "command_readback_matches_desired": self.command_readback_matches_desired,
                "command_readback_mismatch_fields": self.command_readback_mismatch_fields,
                "command_uncertain_mqtt_active": self.command_uncertain_mqtt_active,
                "command_not_effective_active": self.command_not_effective_active,
                "command_late_effect_guard_active": self.command_late_effect_guard_active,
                "command_lifecycle_state": self.command_lifecycle_state,
                "command_effect_category": self.command_effect_category,
                "command_resync_count": self.command_resync_count,
                "command_late_effect_guard_activation_count": self.command_late_effect_guard_activation_count,
                "safe_state_counter": self.safe_state_counter,
                "current_mode": self.current_mode,
                "consecutive_errors": self.consecutive_errors,
                "last_error": self.last_error,
                "last_error_time": self.last_error_time,
            }

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            now_epoch = time.time()

            def age_seconds(epoch_value: Optional[float]) -> Optional[int]:
                if epoch_value is None:
                    return None
                return max(0, int(now_epoch - epoch_value))

            def signed_target_stage(value: Any) -> int:
                try:
                    magnitude = abs(int(float(value or 0)))
                except Exception:
                    magnitude = 0
                if self.last_output_power > 0 and self.last_input_power <= 0:
                    return -magnitude
                if self.last_input_power > 0 and self.last_output_power <= 0:
                    return magnitude
                return 0 if magnitude == 0 else int(value or 0)

            current_signed_target = signed_zendure_target_w(
                self.last_input_power,
                self.last_output_power,
            )

            return {
                "uptime_seconds": int(now_epoch - self.startup_epoch),
                "raw_grid_power": self.raw_grid_power,
                "grid_power": self.grid_power,
                "current_rule_deviation": self.current_rule_deviation,
                "effective_export_power": self.effective_export_power,
                "effective_export_power_valid": self.effective_export_power_valid,
                "effective_export_power_used_for_control": self.effective_export_power_used_for_control,
                "grid_power_available": self.grid_power_available,
                "grid_power_fresh": self.grid_power_fresh,
                "grid_power_valid": self.grid_power_valid,
                "grid_power_used_for_control": self.grid_power_used_for_control,
                "grid_power_age_seconds": self.grid_power_age_seconds,
                "grid_power_validity_reason": self.grid_power_validity_reason,
                "grid_meter_source": self.grid_meter_source,
                "raw_grid_source": self.raw_grid_source,
                "grid_rejected_count_since_start": self.grid_rejected_count_since_start,
                "grid_last_rejected_time": self.grid_last_rejected_time,
                "grid_last_rejected_reason": self.grid_last_rejected_reason,
                "grid_last_rejected_value_w": self.grid_last_rejected_value_w,
                "last_input_power": self.last_input_power,
                "last_output_power": self.last_output_power,
                "actual_zendure_charge_power": self.actual_zendure_charge_power,
                "actual_zendure_discharge_power": self.actual_zendure_discharge_power,
                "actual_zendure_grid_input_power": self.actual_zendure_grid_input_power,
                "actual_zendure_output_pack_power": self.actual_zendure_output_pack_power,
                "actual_zendure_grid_off_power": self.actual_zendure_grid_off_power,
                "actual_zendure_solar_input_power": self.actual_zendure_solar_input_power,
                "zendure_grid_signed_power_w": self.zendure_grid_signed_power_w,
                "zendure_grid_import_power_w": self.zendure_grid_import_power_w,
                "zendure_grid_output_power_w": self.zendure_grid_output_power_w,
                "zendure_battery_signed_power_w": self.zendure_battery_signed_power_w,
                "zendure_battery_charge_power_w": self.zendure_battery_charge_power_w,
                "zendure_battery_discharge_power_w": self.zendure_battery_discharge_power_w,
                "zendure_offgrid_power_w": self.zendure_offgrid_power_w,
                "zendure_offgrid_active": self.zendure_offgrid_active,
                "zendure_power_balance_residual_w": self.zendure_power_balance_residual_w,
                "zendure_system_charge_power": self.actual_zendure_system_charge_power,
                "zendure_system_discharge_power": self.actual_zendure_system_discharge_power,
                "zendure_system_signed_power": self.actual_zendure_system_signed_power,
                "actual_zendure_power_valid": self.actual_zendure_power_valid,
                "actual_zendure_power_age_s": self.actual_zendure_power_age_s,
                "actual_zendure_power_validity_reason": self.actual_zendure_power_validity_reason,
                "current_target_power": self.current_target_power,
                "zendure_target_signed_power": current_signed_target,
                "target_raw_w": signed_target_stage(self.last_target_before_smoothing),
                "target_after_power_limit_w": signed_target_stage(self.last_target_after_power_limit),
                "target_after_smoothing_w": signed_target_stage(self.last_target_after_smoothing),
                "target_after_ramp_w": signed_target_stage(self.last_target_after_ramp),
                "target_final_w": current_signed_target,
                "last_target_before_smoothing": self.last_target_before_smoothing,
                "last_target_after_power_limit": self.last_target_after_power_limit,
                "target_power_limit_reason": self.target_power_limit_reason,
                "last_target_after_smoothing": self.last_target_after_smoothing,
                "last_target_after_ramp": self.last_target_after_ramp,
                "current_mode": self.current_mode,
                "previous_mode": self.previous_mode,
                "last_mode_change_time": self.last_mode_change_time,
                "last_mode_duration_seconds": self.last_mode_duration_seconds,
                "control_reason": self.control_reason,
                "technical_control_path": self.technical_control_path,
                "active_limiters": list(self.active_limiters),
                "last_control_action": self.last_control_action,
                "last_limit_reason": self.last_limit_reason,
                "charge_acceptance_state": self.charge_acceptance_state,
                "charge_acceptance_reason": self.charge_acceptance_reason,
                "mqtt_connected": self.mqtt_connected,
                "zendure_mqtt_overall_status": self.zendure_mqtt_overall_status,
                "zendure_mqtt_status_reason": self.zendure_mqtt_status_reason,
                "zendure_mqtt_live_confirmed": self.zendure_mqtt_live_confirmed,
                "zendure_mqtt_retained_only": self.zendure_mqtt_retained_only,
                "zendure_mqtt_partial_stale": self.zendure_mqtt_partial_stale,
                "zendure_mqtt_after_broker_restart_no_live_updates": self.zendure_mqtt_after_broker_restart_no_live_updates,
                "zendure_mqtt_critical_data_age_s": self.zendure_mqtt_critical_data_age_s,
                "zendure_mqtt_missing_critical_groups": self.zendure_mqtt_missing_critical_groups,
                "zendure_mqtt_stale_critical_groups": self.zendure_mqtt_stale_critical_groups,
                "last_mqtt_command": self.last_mqtt_command,
                "last_mqtt_command_skipped": self.last_mqtt_command_skipped,
                "mqtt_commands_sent": self.mqtt_commands_sent,
                "command_uncertain_mqtt_active": self.command_uncertain_mqtt_active,
                "command_uncertain_mqtt_since_time": self.command_uncertain_mqtt_since_time,
                "command_uncertain_mqtt_status": self.command_uncertain_mqtt_status,
                "command_uncertain_mqtt_target_w": self.command_uncertain_mqtt_target_w,
                "command_uncertain_mqtt_reason": self.command_uncertain_mqtt_reason,
                "command_resync_count": self.command_resync_count,
                "command_resync_last_time": self.command_resync_last_time,
                "command_resync_reason": self.command_resync_reason,
                "command_resync_suppressed_count": self.command_resync_suppressed_count,
                "command_resync_suppressed_last_time": self.command_resync_suppressed_last_time,
                "command_resync_suppressed_reason": self.command_resync_suppressed_reason,
                "command_effect_state_category": self.command_effect_category,
                "command_effect_state_reason": self.command_effect_reason,
                "command_effect_reference_w": self.command_effect_reference_w,
                "command_lifecycle_state": self.command_lifecycle_state,
                "command_desired_sequence_id": self.command_desired_sequence_id,
                "command_desired_intent": self.command_desired_intent,
                "command_desired_smart_mode": self.command_desired_smart_mode,
                "command_desired_ac_mode": self.command_desired_ac_mode,
                "command_desired_input_limit_w": self.command_desired_input_limit_w,
                "command_desired_output_limit_w": self.command_desired_output_limit_w,
                "command_desired_signed_target_w": self.command_desired_signed_target_w,
                "command_desired_reason": self.command_desired_reason,
                "command_desired_safety_relevant": self.command_desired_safety_relevant,
                "command_publish_event": self.command_publish_event,
                "command_publish_last_time": self.command_publish_last_time,
                "command_publish_fields": self.command_publish_fields,
                "command_publish_event_id": self.command_publish_event_id,
                "command_publish_epoch_s": self.command_publish_epoch_s,
                "command_state_gate_state": self.command_state_gate_state,
                "command_state_retry_remaining_s": self.command_state_retry_remaining_s,
                "command_neutralization_episode_id": self.command_neutralization_episode_id,
                "command_readback_matches_desired": self.command_readback_matches_desired,
                "command_readback_mismatch_fields": self.command_readback_mismatch_fields,
                "command_late_effect_guard_active": self.command_late_effect_guard_active,
                "command_late_effect_guard_previous_intent": self.command_late_effect_guard_previous_intent,
                "command_late_effect_guard_pending_intent": self.command_late_effect_guard_pending_intent,
                "command_late_effect_guard_pending_target_w": self.command_late_effect_guard_pending_target_w,
                "command_late_effect_guard_duration_s": self.command_late_effect_guard_duration_s,
                "command_late_effect_guard_reason": self.command_late_effect_guard_reason,
                "command_late_effect_guard_activation_count": self.command_late_effect_guard_activation_count,
                "command_late_effect_guard_blocked_command_count": self.command_late_effect_guard_blocked_command_count,
                "command_ac_mode_change_count": self.command_ac_mode_change_count,
                "physical_power_direction_change_count": self.physical_power_direction_change_count,
                "command_effect_confirmed": self.command_effect_confirmed,
                "command_effect_confirmed_time": self.command_effect_confirmed_time,
                "command_effect_confirmed_reason": self.command_effect_confirmed_reason,
                "command_neutralization_active": self.command_neutralization_active,
                "command_neutralization_since_time": self.command_neutralization_since_time,
                "command_neutralization_reason": self.command_neutralization_reason,
                "command_mismatch_resolution": self.command_mismatch_resolution,
                "zendure_command_smart_mode": self.zendure_command_smart_mode,
                "zendure_command_ac_mode": self.zendure_command_ac_mode,
                "zendure_command_input_limit_w": self.zendure_command_input_limit_w,
                "zendure_command_output_limit_w": self.zendure_command_output_limit_w,
                "zendure_device_inverse_max_power_w": self.zendure_device_inverse_max_power_w,
                "zendure_device_inverse_max_power_source": self.zendure_device_inverse_max_power_source,
                "zendure_device_inverse_max_power_age_s": age_seconds(self.zendure_device_inverse_max_power_updated_epoch),
                "zendure_device_charge_max_limit_w": self.zendure_device_charge_max_limit_w,
                "zendure_grid_off_mode": self.zendure_grid_off_mode,
                "zendure_flash_protection_active": self.zendure_flash_protection_active,
                "zendure_flash_protection_reason": self.zendure_flash_protection_reason,
                "zendure_command_state_complete": self.zendure_command_state_complete,
                "zendure_command_state_reason": self.zendure_command_state_reason,
                "zendure_command_state_source": self.zendure_command_state_source,
                "zendure_power_observation_direction": self.zendure_power_observation_direction,
                "zendure_power_observation_confidence": self.zendure_power_observation_confidence,
                "zendure_power_observation_signed_w": self.zendure_power_observation_signed_w,
                "zendure_power_observation_magnitude_w": self.zendure_power_observation_magnitude_w,
                "zendure_power_observation_age_s": age_seconds(self.zendure_power_observation_updated_epoch),
                "zendure_power_observation_reason": self.zendure_power_observation_reason,
                "command_not_effective_active": self.command_not_effective_active,
                "command_not_effective_since_time": self.command_not_effective_since_time,
                "command_not_effective_duration_s": self.command_not_effective_duration_s,
                "command_not_effective_reason": self.command_not_effective_reason,
                "consecutive_errors": self.consecutive_errors,
                "last_error": self.last_error,
                "last_error_time": self.last_error_time,
                "measurement_log_status": self.measurement_log_status,
                "measurement_log_status_reason": self.measurement_log_status_reason,
                "measurement_estimated_retention_hours": self.measurement_estimated_retention_hours,
                "measurement_current_file_size_bytes": self.measurement_current_file_size_bytes,
                "measurement_free_disk_mb": self.measurement_free_disk_mb,
                "measurement_log_path": self.measurement_log_path,
                "measurement_log_target_type": self.measurement_log_target_type,
                "measurement_log_active_target_type": self.measurement_log_active_target_type,
                "measurement_fallback_active": self.measurement_fallback_active,
                "measurement_fallback_count_since_start": self.measurement_fallback_count_since_start,
                "measurement_last_fallback_time": self.measurement_last_fallback_time,
                "measurement_last_fallback_reason": self.measurement_last_fallback_reason,
                "measurement_db_status": self.measurement_db_status,
                "measurement_db_reason": self.measurement_db_reason,
                "measurement_db_path": self.measurement_db_path,
                "measurement_db_queue_depth": self.measurement_db_queue_depth,
                "measurement_db_last_write_epoch_s": self.measurement_db_last_write_epoch_s,
                "measurement_db_last_write_duration_ms": self.measurement_db_last_write_duration_ms,
                "measurement_db_error": self.measurement_db_error,
                "measurement_db_last_error": self.measurement_db_last_error,
                "measurement_db_last_error_epoch_s": self.measurement_db_last_error_epoch_s,
                "measurement_db_consecutive_failures": self.measurement_db_consecutive_failures,
                "measurement_db_last_success_epoch_s": self.measurement_db_last_success_epoch_s,
                "measurement_db_write_stale": self.measurement_db_write_stale,
                "measurement_db_rows_written": self.measurement_db_rows_written,
                "measurement_db_rows_dropped": self.measurement_db_rows_dropped,
                "measurement_db_size_bytes": self.measurement_db_size_bytes,
                "safe_state_counter": self.safe_state_counter,
                "controller_started_epoch": self.controller_started_epoch,
                "last_cycle_completed_epoch": self.last_cycle_completed_epoch,
                "last_loop_duration_ms": self.last_loop_duration_ms,
                "last_cycle_total_ms": self.last_cycle_total_ms,
                "last_cycle_slowest_step": self.last_cycle_slowest_step,
                "last_cycle_slowest_step_ms": self.last_cycle_slowest_step_ms,
                "last_cycle_timing_json": self.last_cycle_timing_json,
                "last_cycle_timing_stats_json": self.last_cycle_timing_stats_json,
                "loop_counter": self.loop_counter,
                "last_shelly_update_time": self.last_shelly_update_time,
                "last_shelly_update_age_seconds": age_seconds(self.last_shelly_update_epoch),
                "last_soc_update_time": self.last_soc_update_time,
                "last_soc_update_age_seconds": age_seconds(self.last_soc_update_epoch),
                "last_mqtt_soc_update_time": self.last_mqtt_soc_update_time,
                "last_mqtt_soc_update_age_seconds": age_seconds(self.last_mqtt_soc_update_epoch),
                "last_mqtt_zendure_sensor_update_time": self.last_mqtt_zendure_sensor_update_time,
                "last_mqtt_zendure_sensor_update_age_seconds": age_seconds(self.last_mqtt_zendure_sensor_update_epoch),
                "last_local_api_update_time": self.last_local_api_update_time,
                "last_local_api_update_age_seconds": age_seconds(self.last_local_api_update_epoch),
                "last_local_api_error": self.last_local_api_error,
                "last_local_api_error_time": self.last_local_api_error_time,
                "zendure_local_api_worker_state": self.zendure_local_api_worker_state,
                "zendure_local_api_worker_config_generation": self.zendure_local_api_worker_config_generation,
                "zendure_local_api_snapshot_sequence": self.zendure_local_api_snapshot_sequence,
                "zendure_local_api_success_sequence": self.zendure_local_api_success_sequence,
                "zendure_local_api_new_success_applied": self.zendure_local_api_new_success_applied,
                "zendure_local_api_latest_attempt_ok": self.zendure_local_api_latest_attempt_ok,
                "zendure_local_api_last_attempt_time": (
                    datetime.fromtimestamp(self.zendure_local_api_last_attempt_epoch).strftime("%Y-%m-%d %H:%M:%S")
                    if self.zendure_local_api_last_attempt_epoch is not None else "-"
                ),
                "zendure_local_api_last_attempt_age_s": (
                    round(max(0.0, time.monotonic() - self.zendure_local_api_last_attempt_monotonic), 3)
                    if self.zendure_local_api_last_attempt_monotonic is not None else None
                ),
                "zendure_local_api_last_success_time": (
                    datetime.fromtimestamp(self.zendure_local_api_last_success_epoch).strftime("%Y-%m-%d %H:%M:%S")
                    if self.zendure_local_api_last_success_epoch is not None else "-"
                ),
                "zendure_local_api_last_success_age_s": (
                    round(max(0.0, time.monotonic() - self.zendure_local_api_last_success_monotonic), 3)
                    if self.zendure_local_api_last_success_monotonic is not None else None
                ),
                "zendure_local_api_snapshot_valid": self.zendure_local_api_snapshot_valid,
                "zendure_local_api_snapshot_stale": self.zendure_local_api_snapshot_stale,
                "zendure_local_api_snapshot_stale_after_s": self.zendure_local_api_snapshot_stale_after_s,
                "zendure_local_api_request_duration_ms": self.zendure_local_api_last_request_duration_ms,
                "zendure_local_api_snapshot_apply_ms": self.zendure_local_api_snapshot_apply_ms,
                "zendure_local_api_consecutive_errors": self.zendure_local_api_consecutive_errors,
                "zendure_local_api_backoff_remaining_s": self.zendure_local_api_backoff_remaining_s,
                "zendure_local_api_latest_error_code": self.zendure_local_api_latest_error_code,
                "zendure_local_api_parse_warning_count": self.zendure_local_api_parse_warning_count,
                "last_sma_battery_update_time": self.last_sma_battery_update_time,
                "last_sma_battery_update_age_seconds": age_seconds(self.last_sma_battery_update_epoch),
                "last_zendure_power_update_time": self.last_zendure_power_update_time,
                "last_zendure_power_update_age_seconds": age_seconds(self.last_zendure_power_update_epoch),
                "battery_soc": self.battery_soc,
                "soc_available": self.soc_available,
                "soc_fresh": self.soc_fresh,
                "soc_valid": self.soc_valid,
                "soc_used_for_control": self.soc_used_for_control,
                "soc_age_seconds": self.soc_age_seconds,
                "soc_validity_reason": self.soc_validity_reason,
                "mqtt_command_path_available": self.mqtt_command_path_available,
                "mqtt_command_path_fresh": self.mqtt_command_path_fresh,
                "mqtt_command_path_valid": self.mqtt_command_path_valid,
                "mqtt_command_path_used_for_control": self.mqtt_command_path_used_for_control,
                "mqtt_command_path_age_seconds": self.mqtt_command_path_age_seconds,
                "mqtt_command_path_validity_reason": self.mqtt_command_path_validity_reason,
                "control_required_sources": list(self.control_required_sources),
                "control_missing_required_sources": list(self.control_missing_required_sources),
                "control_data_quality": self.control_data_quality,
                "night_discharge_stop_soc_percent": self.night_discharge_stop_soc_percent,
                "night_discharge_stop_reason": self.night_discharge_stop_reason,
                "mqtt_battery_soc": self.mqtt_battery_soc,
                "local_api_soc": self.local_api_soc,
                "local_api_electric_level": self.local_api_electric_level,
                "local_api_pack_soc_level": self.local_api_pack_soc_level,
                "zendure_telemetry_source": self.zendure_telemetry_source,
                "zendure_local_api_fallback_active": self.zendure_local_api_fallback_active,
                "current_battery_temperature_c": self.current_battery_temperature_c,
                "highest_battery_temperature_c": self.highest_battery_temperature_c,
                "highest_battery_temperature_time": self.highest_battery_temperature_time,
                "lowest_battery_temperature_c": self.lowest_battery_temperature_c,
                "lowest_battery_temperature_time": self.lowest_battery_temperature_time,
                "zendure_pack_temperatures": list(self.zendure_pack_temperatures),
                "zendure_battery_details": list(self.zendure_battery_details.values()),
                "sma_battery_power": self.sma_battery_power,
                "sma_battery_display_power": self.sma_battery_display_power,
                "sma_battery_soc": self.sma_battery_soc,
                "sma_battery_capacity_kwh": self.sma_battery_capacity_kwh,
                "sma_battery_discharge_power": self.sma_battery_discharge_power,
                "second_battery_data_available": self.second_battery_data_available,
                "second_battery_data_fresh": self.second_battery_data_fresh,
                "second_battery_data_valid": self.second_battery_data_valid,
                "second_battery_data_used_for_control": self.second_battery_data_used_for_control,
                "second_battery_data_age_seconds": self.second_battery_data_age_seconds,
                "second_battery_validity_reason": self.second_battery_validity_reason,
                "evcc_data_available": self.evcc_data_available,
                "sma_energy_meter_enabled": self.sma_energy_meter_enabled,
                "sma_energy_meter_running": self.sma_energy_meter_running,
                "sma_energy_meter_power_w": self.sma_energy_meter_power_w,
                "sma_energy_meter_consumption_power_w": self.sma_energy_meter_consumption_power_w,
                "sma_energy_meter_feedin_power_w": self.sma_energy_meter_feedin_power_w,
                "sma_energy_meter_last_update_age_seconds": age_seconds(self.sma_energy_meter_last_epoch),
                "sma_energy_meter_susy_id": self.sma_energy_meter_susy_id,
                "sma_energy_meter_serial_number": self.sma_energy_meter_serial_number,
                "sma_energy_meter_packet_count": self.sma_energy_meter_packet_count,
                "sma_energy_meter_decode_count": self.sma_energy_meter_decode_count,
                "sma_energy_meter_ignored_count": self.sma_energy_meter_ignored_count,
                "sma_energy_meter_error_count": self.sma_energy_meter_error_count,
                "sma_energy_meter_last_error": self.sma_energy_meter_last_error,
                "sma_energy_meter_group": self.sma_energy_meter_group,
                "sma_energy_meter_port": self.sma_energy_meter_port,
                "sma_energy_meter_interface": self.sma_energy_meter_interface,
                "sma_energy_meter_resolved_interface_ip": self.sma_energy_meter_resolved_interface_ip,
                "sma_energy_meter_configured_susy_id": self.sma_energy_meter_configured_susy_id,
                "sma_energy_meter_configured_serial": self.sma_energy_meter_configured_serial,
                "sma_energy_meter_selected_device_key": self.sma_energy_meter_selected_device_key,
                "sma_energy_meter_selected_device_matched": self.sma_energy_meter_selected_device_matched,
                "sma_energy_meter_detected_device_count": self.sma_energy_meter_detected_device_count,
                "sma_energy_meter_devices_json": self.sma_energy_meter_devices_json,
                "sma_energy_meter_socket_mode": self.sma_energy_meter_socket_mode,
                "sma_energy_meter_effective_socket_mode": self.sma_energy_meter_effective_socket_mode,
                "sma_energy_meter_bind_address": self.sma_energy_meter_bind_address,
                "sma_energy_meter_bind_mode": self.sma_energy_meter_bind_mode,
                "sma_energy_meter_reuseaddr_enabled": self.sma_energy_meter_reuseaddr_enabled,
                "sma_energy_meter_reuseport_requested": self.sma_energy_meter_reuseport_requested,
                "sma_energy_meter_reuseport_supported": self.sma_energy_meter_reuseport_supported,
                "sma_energy_meter_reuseport_enabled": self.sma_energy_meter_reuseport_enabled,
                "sma_energy_meter_reuseport_error": self.sma_energy_meter_reuseport_error,
                "sma_energy_meter_multicast_if_set": self.sma_energy_meter_multicast_if_set,
                "sma_energy_meter_packet_rate_per_min": self.sma_energy_meter_packet_rate_per_min,
                "sma_energy_meter_packet_gap_warn_s": self.sma_energy_meter_packet_gap_warn_s,
                "sma_energy_meter_last_packet_gap_s": self.sma_energy_meter_last_packet_gap_s,
                "sma_energy_meter_max_packet_gap_s": self.sma_energy_meter_max_packet_gap_s,
                "sma_energy_meter_last_large_gap_s": self.sma_energy_meter_last_large_gap_s,
                "sma_energy_meter_last_large_gap_age_seconds": self.sma_energy_meter_last_large_gap_age_seconds,
                "rest_surplus_harvest_active": self.rest_surplus_harvest_active,
                "rest_surplus_harvest_eligible": self.rest_surplus_harvest_eligible,
                "rest_surplus_harvest_reason": self.rest_surplus_harvest_reason,
                "rest_surplus_harvest_block_reason": self.rest_surplus_harvest_block_reason,
                "rest_surplus_harvest_profile": self.rest_surplus_harvest_profile,
                "rest_surplus_entry_progress_s": round(float(self.rest_surplus_entry_progress_s or 0.0), 1),
                "rest_surplus_hold_remaining_s": round(float(self.rest_surplus_hold_remaining_s or 0.0), 1),
                "rest_surplus_exit_reason": self.rest_surplus_exit_reason,
                "second_battery_charge_pressure_w": round(float(self.second_battery_charge_pressure_w or 0.0), 1),
                "second_battery_charge_saturation_threshold_w": round(float(self.second_battery_charge_saturation_threshold_w or 0.0), 1),
                "rest_surplus_export_w": round(float(self.rest_surplus_export_w or 0.0), 1),
                "harvest_primary_floor_w": round(float(self.harvest_primary_floor_w or 0.0), 1),
                "harvest_primary_restart_w": round(float(self.harvest_primary_restart_w or 0.0), 1),
                "harvest_primary_near_limit_w": round(float(self.harvest_primary_near_limit_w or 0.0), 1),
                "harvest_primary_target_share": round(float(self.harvest_primary_target_share or 0.0), 3),
                "harvest_primary_required_w": round(float(self.harvest_primary_required_w or 0.0), 1),
                "harvest_primary_share_reserve_w": round(float(self.harvest_primary_share_reserve_w or 0.0), 1),
                "harvest_candidate_raw_w": round(float(self.harvest_candidate_raw_w or 0.0), 1),
                "harvest_candidate_after_primary_w": round(float(self.harvest_candidate_after_primary_w or 0.0), 1),
                "harvest_target_semantics": self.harvest_target_semantics,
                "harvest_reference_charge_w": round(float(self.harvest_reference_charge_w or 0.0), 1),
                "harvest_reference_charge_source": self.harvest_reference_charge_source,
                "harvest_reference_charge_confidence": self.harvest_reference_charge_confidence,
                "harvest_reference_charge_age_s": (
                    None if self.harvest_reference_charge_age_s is None
                    else round(float(self.harvest_reference_charge_age_s), 1)
                ),
                "harvest_reference_charge_valid": self.harvest_reference_charge_valid,
                "harvest_reference_fallback_reason": self.harvest_reference_fallback_reason,
                "harvest_profile_reserve_w": round(float(self.harvest_profile_reserve_w or 0.0), 1),
                "harvest_candidate_delta_w": round(float(self.harvest_candidate_delta_w or 0.0), 1),
                "harvest_candidate_absolute_w": round(float(self.harvest_candidate_absolute_w or 0.0), 1),
                "harvest_input_time_skew_s": (
                    None if self.harvest_input_time_skew_s is None
                    else round(float(self.harvest_input_time_skew_s), 1)
                ),
                "harvest_network_target_w": round(float(self.harvest_network_target_w or 0.0), 1),
                "harvest_total_available_charge_w": round(float(self.harvest_total_available_charge_w or 0.0), 1),
                "harvest_primary_share_target_w": round(float(self.harvest_primary_share_target_w or 0.0), 1),
                "harvest_zendure_share_target_w": round(float(self.harvest_zendure_share_target_w or 0.0), 1),
                "harvest_export_capture_target_w": round(float(self.harvest_export_capture_target_w or 0.0), 1),
                "harvest_target_selected_by": self.harvest_target_selected_by,
                "harvest_calculation_branch": self.harvest_calculation_branch,
                "harvest_entry_min_export_w": round(float(self.harvest_entry_min_export_w or 0.0), 1),
                "harvest_command_path_eligible": self.harvest_command_path_eligible,
                "harvest_command_path_block_reason": self.harvest_command_path_block_reason,
                "harvest_limiter_reason": self.harvest_limiter_reason,
                "harvest_capacity_mode": self.harvest_capacity_mode,
                "primary_remaining_capacity_kwh": None if self.primary_remaining_capacity_kwh is None else round(float(self.primary_remaining_capacity_kwh), 3),
                "zendure_remaining_capacity_kwh": None if self.zendure_remaining_capacity_kwh is None else round(float(self.zendure_remaining_capacity_kwh), 3),
                "graph_history": list(self.graph_history),
                "event_history": list(self.event_history),
                "mqtt_topic_diagnostics": list(self.mqtt_topic_diagnostics),
            }
