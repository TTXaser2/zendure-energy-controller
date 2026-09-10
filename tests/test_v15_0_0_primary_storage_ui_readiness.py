from unittest.mock import patch

from state import ControllerState
from status_page_v2 import render_status_page_v2
from web_ui import build_ready_payload, build_status_view_payload


def _healthy_ready_snapshot():
    return {
        "mqtt_connected": True,
        "last_shelly_update_age_seconds": 1,
        "grid_power_valid": True,
        "last_soc_update_age_seconds": 1,
        "soc_valid": True,
        "battery_soc": 80,
        "zendure_telemetry_source": "MQTT",
        "zendure_local_api_fallback_active": False,
        "mqtt_command_path_available": True,
        "mqtt_command_path_fresh": True,
        "mqtt_command_path_valid": True,
        "actual_zendure_power_valid": True,
        "zendure_command_state_complete": True,
        "zendure_command_smart_mode": 1,
        "zendure_command_ac_mode": "Input mode",
        "zendure_command_input_limit_w": 500,
        "zendure_command_output_limit_w": 0,
        "command_desired_sequence_id": 0,
        "command_uncertain_mqtt_active": False,
        "command_not_effective_active": False,
        "command_late_effect_guard_active": False,
        "command_lifecycle_state": "ACTIVE_EFFECTIVE",
        "current_mode": "HOLD",
        "consecutive_errors": 0,
        "last_error": "none",
        "last_error_time": "-",
        "uptime_seconds": 123,
    }


def test_readiness_snapshot_uses_monotonic_primary_storage_age():
    state = ControllerState()
    state.last_sma_battery_update_epoch = 1.0
    state.last_sma_battery_update_monotonic = 493.0
    state.primary_storage_data_available = True
    state.primary_storage_source_profile = "modbus_template"
    state.primary_storage_source_type = "modbus_tcp"
    state.primary_storage_source_health = "DEGRADED"
    state.primary_storage_last_poll_ok = False
    with patch("state.time.time", return_value=1000.0), patch("state.time.monotonic", return_value=500.0):
        snap = state.readiness_snapshot()
        full = state.snapshot()
    assert snap["last_sma_battery_update_age_seconds"] == 7
    assert full["last_sma_battery_update_age_seconds"] == 7
    assert snap["primary_storage_source_profile"] == "modbus_template"
    assert snap["primary_storage_source_health"] == "DEGRADED"
    assert snap["primary_storage_last_poll_ok"] is False


def test_observer_mode_primary_storage_is_a_readiness_source():
    cfg = {
        "SHELLY_STALE_TIMEOUT_SECONDS": 15,
        "SOC_STALE_TIMEOUT_SECONDS": 90,
        "SECOND_BATTERY_INTEGRATION_ENABLED": True,
        "CROSS_CHARGE_ENABLED": False,
        "SECOND_BATTERY_SOURCE_PROFILE": "modbus_template",
        "SECOND_BATTERY_STALE_TIMEOUT_SECONDS": 30,
    }
    snap = _healthy_ready_snapshot()
    snap.update({
        "last_sma_battery_update_age_seconds": 2,
        "second_battery_valid": True,
        "second_battery_validity_reason": "OK",
        "primary_storage_source_profile": "modbus_template",
        "primary_storage_source_type": "modbus_tcp",
        "primary_storage_source_health": "DEGRADED",
        "primary_storage_last_poll_ok": False,
        "primary_storage_endpoint": "192.168.0.76:502",
        "primary_storage_unit_id": 3,
    })
    ready = build_ready_payload(cfg, snap)
    assert ready["ready"] is True
    assert "primary_storage_source" in ready["checks"]
    check = ready["checks"]["primary_storage_source"]
    assert check["ok"] is True
    assert check["source_health"] == "DEGRADED"
    assert check["last_poll_ok"] is False

    stale = dict(snap, last_sma_battery_update_age_seconds=31, second_battery_valid=False)
    not_ready = build_ready_payload(cfg, stale)
    assert not_ready["ready"] is False
    assert "primary_storage_source" in not_ready["failed_checks"]


def test_cross_charge_keeps_historical_readiness_check_id():
    cfg = {
        "SHELLY_STALE_TIMEOUT_SECONDS": 15,
        "SOC_STALE_TIMEOUT_SECONDS": 90,
        "SECOND_BATTERY_INTEGRATION_ENABLED": True,
        "CROSS_CHARGE_ENABLED": True,
        "SECOND_BATTERY_SOURCE_PROFILE": "evcc_standard",
        "SECOND_BATTERY_STALE_TIMEOUT_SECONDS": 30,
    }
    snap = _healthy_ready_snapshot()
    snap.update({
        "last_sma_battery_update_age_seconds": 1,
        "second_battery_valid": True,
        "primary_storage_source_profile": "evcc_standard",
        "primary_storage_source_type": "mqtt",
        "primary_storage_source_health": "OK",
        "primary_storage_last_poll_ok": True,
    })
    ready = build_ready_payload(cfg, snap)
    assert ready["ready"] is True
    assert "cross_charge_second_battery" in ready["checks"]
    assert "primary_storage_source" not in ready["checks"]


def test_status_payload_and_page_use_configured_display_name_and_source_health():
    cfg = {
        "SECOND_BATTERY_INTEGRATION_ENABLED": True,
        "SECOND_BATTERY_SOURCE_PROFILE": "modbus_template",
        "SECOND_BATTERY_MODBUS_TEMPLATE": "sma_sunny_island",
        "SECOND_BATTERY_DISPLAY_NAME": "Haus-SMA",
        "MIN_SOC_PERCENT": 10,
        "MAX_SOC_PERCENT": 90,
        "NIGHT_DISCHARGE_RESERVE_SOC": 20,
    }
    snap = {
        "primary_storage_data_available": True,
        "second_battery_data_available": True,
        "second_battery_data_valid": True,
        "second_battery_data_fresh": True,
        "sma_battery_display_power": 500,
        "sma_battery_soc": 75,
        "primary_storage_source_health": "OK",
        "primary_storage_last_poll_ok": True,
        "primary_storage_endpoint": "192.168.0.76:502",
        "primary_storage_unit_id": 3,
        "current_mode": "HOLD",
    }
    payload = build_status_view_payload(cfg, snap)
    assert payload["primary"]["name"] == "Haus-SMA"
    assert payload["primary"]["source"] == "Direkt per Modbus"
    assert payload["primary"]["source_profile"] == "modbus_template"
    assert payload["primary"]["source_health"] == "OK"
    assert payload["primary"]["endpoint"] == "192.168.0.76:502"
    assert payload["primary"]["unit_id"] == 3

    page = render_status_page_v2(cfg, payload, analysis_available=False, analysis_port=8090)
    assert '<h2 data-zec="primary.name">Haus-SMA</h2>' in page
    assert "Quellenstatus" in page
    assert "Direkt per Modbus" in page
