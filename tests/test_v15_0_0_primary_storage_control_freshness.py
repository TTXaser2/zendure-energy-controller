import time
from unittest.mock import patch

from config_manager import DEFAULT_CONFIG
from measurement_v4 import _canonical_source
from state import ControllerState
from tests.test_operation_priority import make_controller


def _cfg(**overrides):
    cfg = dict(DEFAULT_CONFIG)
    cfg.update({
        "SECOND_BATTERY_INTEGRATION_ENABLED": True,
        "SECOND_BATTERY_SOURCE_PROFILE": "modbus_template",
        "SECOND_BATTERY_STALE_TIMEOUT_SECONDS": 30,
        "CROSS_CHARGE_ENABLED": False,
        "REST_SURPLUS_HARVEST_ENABLED": False,
    })
    cfg.update(overrides)
    return cfg


def _fresh_primary_state(raw_power_w=-1200.0, soc=80.0):
    state = ControllerState()
    with state.lock:
        state.sma_battery_power = float(raw_power_w)
        state.sma_battery_soc = float(soc)
        state.last_sma_battery_update_epoch = time.time()
        state.last_sma_battery_update_monotonic = time.monotonic()
        state.primary_storage_data_available = True
        state.primary_storage_source_profile = "modbus_template"
        state.primary_storage_source_type = "modbus_tcp"
        state.primary_storage_last_poll_ok = True
    return state


def test_modbus_native_sign_is_canonical_and_observer_mode_remains_visible():
    cfg = _cfg(CROSS_CHARGE_ENABLED=False)
    state = _fresh_primary_state(raw_power_w=-1200.0)
    controller, state, _, _ = make_controller(cfg, state=state)

    controller.update_second_battery_display_metrics(cfg)
    assert state.sma_battery_display_power == 1200.0  # UI: positive = charging
    assert state.sma_battery_discharge_power == 0.0
    assert state.second_battery_data_available is True
    assert state.second_battery_data_fresh is True
    assert state.second_battery_data_valid is True
    assert state.second_battery_data_used_for_control is False

    with state.lock:
        state.sma_battery_power = 700.0
    controller.update_second_battery_display_metrics(cfg)
    assert state.sma_battery_display_power == -700.0  # UI: negative = discharging
    assert state.sma_battery_discharge_power == 700.0


def test_existing_mqtt_sign_configuration_is_unchanged():
    cfg = _cfg(
        SECOND_BATTERY_SOURCE_PROFILE="custom",
        SECOND_BATTERY_DISCHARGE_SIGN=-1,
    )
    state = _fresh_primary_state(raw_power_w=-500.0)
    with state.lock:
        state.primary_storage_source_profile = "custom"
        state.primary_storage_source_type = "mqtt"
    controller, state, _, _ = make_controller(cfg, state=state)
    controller.update_second_battery_display_metrics(cfg)
    assert state.sma_battery_discharge_power == 500.0
    assert state.sma_battery_display_power == -500.0


def test_control_freshness_prefers_monotonic_time_over_wall_clock():
    cfg = _cfg(SECOND_BATTERY_STALE_TIMEOUT_SECONDS=30)
    state = _fresh_primary_state()
    with state.lock:
        state.last_sma_battery_update_monotonic = 100.0
        state.last_sma_battery_update_epoch = 1_000.0
    controller, _, _, _ = make_controller(cfg, state=state)

    with patch("controller_logic.time.monotonic", return_value=110.0), patch("controller_logic.time.time", return_value=9_999_999.0):
        assert controller.second_battery_data_is_fresh(cfg) is True
    with patch("controller_logic.time.monotonic", return_value=131.0), patch("controller_logic.time.time", return_value=1.0):
        assert controller.second_battery_data_is_fresh(cfg) is False


def test_degraded_last_poll_keeps_fresh_cached_snapshot_control_valid_until_timeout():
    cfg = _cfg(SECOND_BATTERY_STALE_TIMEOUT_SECONDS=30)
    state = _fresh_primary_state()
    with state.lock:
        state.last_sma_battery_update_monotonic = 100.0
        state.primary_storage_last_poll_ok = False
        state.primary_storage_source_health = "DEGRADED"
    with patch("state.time.monotonic", return_value=110.0):
        state.update_data_validity_model(cfg)
    assert state.second_battery_data_available is True
    assert state.second_battery_data_fresh is True
    assert state.second_battery_data_valid is True
    assert state.primary_storage_source_health == "DEGRADED"

    with patch("state.time.monotonic", return_value=131.0):
        state.update_data_validity_model(cfg)
    assert state.second_battery_data_fresh is False
    assert state.second_battery_data_valid is False
    assert state.primary_storage_source_health == "STALE"


def test_disabled_integration_does_not_reuse_lingering_snapshot():
    cfg = _cfg(SECOND_BATTERY_INTEGRATION_ENABLED=False)
    state = _fresh_primary_state(raw_power_w=900.0)
    controller, state, _, _ = make_controller(cfg, state=state)
    controller.update_second_battery_display_metrics(cfg)
    assert state.second_battery_data_available is False
    assert state.second_battery_data_fresh is False
    assert state.second_battery_data_valid is False
    assert state.second_battery_validity_reason == "SECOND_BATTERY_DISABLED"
    assert state.sma_battery_display_power == 0.0
    assert state.sma_battery_discharge_power == 0.0


def test_measurement_v4_maps_native_modbus_to_existing_sma_source_enum():
    assert _canonical_source("modbus_template", second_battery=True) == "SMA"
    assert _canonical_source("custom", second_battery=True) == "EVCC_CUSTOM"
