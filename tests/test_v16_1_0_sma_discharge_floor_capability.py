from unittest.mock import patch
import sys
import types

import pytest

# The controller test environment intentionally does not require the external
# paho-mqtt package.  Install the same narrow import stub used by legacy tests.
if "paho.mqtt.client" not in sys.modules:
    paho = types.ModuleType("paho")
    paho_mqtt = types.ModuleType("paho.mqtt")
    paho_client = types.ModuleType("paho.mqtt.client")
    paho_client.Client = object
    paho_client.CallbackAPIVersion = types.SimpleNamespace(VERSION1=1)
    paho.mqtt = paho_mqtt
    paho_mqtt.client = paho_client
    sys.modules["paho"] = paho
    sys.modules["paho.mqtt"] = paho_mqtt
    sys.modules["paho.mqtt.client"] = paho_client

from measurement_v4 import build_v4_row
from primary_storage_modbus import (
    FC_READ_HOLDING_REGISTERS,
    ModbusReadError,
    PrimaryStorageModbusWorker,
    PrimaryStorageTemplate,
    RegisterDefinition,
    get_primary_storage_template,
    probe_primary_storage_modbus,
    read_current_discharge_floor_soc,
)
from state import ControllerState, primary_usable_soc_percent
from web_ui import build_ready_payload, build_status_view_payload


class FakeClock:
    def __init__(self, value): self.value = float(value)
    def __call__(self): return self.value
    def advance(self, seconds): self.value += float(seconds)


class CapabilityClient:
    def __init__(self, host, port, unit_id, timeout_s=1.0, *, fail_floor=False):
        self.host, self.port, self.unit_id = host, port, unit_id
        self.timeout_s = timeout_s
        self.connect_count = 1
        self.request_count = 0
        self.error_count = 0
        self.closed = False
        self.fail_floor = fail_floor

    def read_registers(self, fc, address, count):
        self.request_count += 1
        if address == 30775:
            return (0, 260)
        if address == 30845:
            return (0, 38)
        if address == 31009:
            if self.fail_floor:
                self.error_count += 1
                raise ModbusReadError("OPTIONAL_FLOOR_FAIL")
            return (0, 19)
        raise AssertionError((fc, address, count))

    def close(self): self.closed = True


CFG = {
    "SECOND_BATTERY_INTEGRATION_ENABLED": True,
    "SECOND_BATTERY_SOURCE_PROFILE": "modbus_template",
    "SECOND_BATTERY_MODBUS_TEMPLATE": "sma_sunny_island",
    "SECOND_BATTERY_MODBUS_HOST": "192.0.2.10",
    "SECOND_BATTERY_MODBUS_PORT": 502,
    "SECOND_BATTERY_MODBUS_UNIT_ID": 3,
    "SECOND_BATTERY_STALE_TIMEOUT_SECONDS": 30,
}


def test_sma_capability_is_register_31009_fc03_and_is_device_specific():
    t = get_primary_storage_template("sma_sunny_island")
    d = t.current_discharge_floor_soc
    assert d is not None
    assert (d.address, d.function_code, d.count, d.data_type) == (31009, FC_READ_HOLDING_REGISTERS, 2, "u32")
    assert t.capability_poll_interval_s == 10.0

    generic = PrimaryStorageTemplate(
        template_id="generic_test",
        display_name_default="Generic",
        protocol="modbus_tcp",
        read_only=True,
        poll_interval_s=1.0,
        port_default=502,
        unit_id_default=1,
        power=RegisterDefinition(1, 4, 2, "s32"),
        soc=RegisterDefinition(3, 3, 2, "u32"),
    )
    client = CapabilityClient("host", 502, 1)
    result = read_current_discharge_floor_soc(client, generic)
    assert result.supported is False
    assert result.ok is None
    assert client.request_count == 0


def test_probe_returns_real_floor_and_normalized_usable_soc_without_writes():
    created = []
    def factory(*args, **kwargs):
        c = CapabilityClient(*args, **kwargs); created.append(c); return c
    result = probe_primary_storage_modbus(CFG, client_factory=factory)
    assert result["status"] == "ok"
    assert result["read_only"] is True
    assert result["soc_percent"] == 38
    assert result["current_discharge_floor_supported"] is True
    assert result["current_discharge_floor_read_ok"] is True
    assert result["current_discharge_floor_soc_percent"] == 19
    assert result["usable_soc_percent"] == pytest.approx(23.457, abs=0.001)
    assert created[0].request_count == 3
    assert created[0].closed is True


def test_optional_capability_failure_does_not_degrade_mandatory_primary_source():
    state = ControllerState()
    mono = FakeClock(100.0); wall = FakeClock(1_700_000_000.0)
    def factory(*args, **kwargs): return CapabilityClient(*args, **kwargs, fail_floor=True)
    worker = PrimaryStorageModbusWorker(state, CFG, client_factory=factory, monotonic_fn=mono, wall_time_fn=wall)
    poll = worker.poll_once()
    assert poll.soc_percent == 38
    assert state.sma_battery_soc == 38
    assert state.primary_storage_source_health == "OK"
    assert state.primary_storage_last_poll_ok is True
    assert state.primary_storage_current_discharge_floor_supported is True
    assert state.primary_storage_current_discharge_floor_last_poll_ok is False
    assert state.primary_storage_current_discharge_floor_last_error_code == "OPTIONAL_FLOOR_FAIL"
    assert state.primary_storage_current_discharge_floor_soc_percent is None


def test_state_normalizes_38_over_19_and_invalidates_stale_floor():
    state = ControllerState()
    state.sma_battery_soc = 38
    state.sma_battery_power = 260
    state.primary_storage_data_available = True
    state.primary_storage_source_profile = "modbus_template"
    state.primary_storage_current_discharge_floor_supported = True
    state.primary_storage_current_discharge_floor_soc_percent = 19
    state.last_sma_battery_update_monotonic = 100.0
    state.primary_storage_current_discharge_floor_last_update_monotonic = 100.0
    with patch("state.time.time", return_value=1_700_000_000.0), patch("state.time.monotonic", return_value=101.0):
        state.update_data_validity_model(CFG)
    assert state.primary_storage_current_discharge_floor_valid is True
    assert state.primary_storage_usable_soc_valid is True
    assert state.primary_storage_usable_soc_percent == pytest.approx(23.45679, rel=1e-5)

    # Refresh only the mandatory primary sample.  The optional device capability
    # must become stale independently and may no longer produce a usable SOC.
    state.last_sma_battery_update_monotonic = 131.0
    with patch("state.time.time", return_value=1_700_000_030.0), patch("state.time.monotonic", return_value=131.0):
        state.update_data_validity_model(CFG)
    assert state.second_battery_data_valid is True
    assert state.primary_storage_current_discharge_floor_valid is False
    assert state.primary_storage_usable_soc_valid is False
    assert state.primary_storage_usable_soc_percent is None


def test_usable_soc_helper_clamps_below_floor_but_rejects_bad_inputs():
    assert primary_usable_soc_percent(38, 19) == pytest.approx(23.45679, rel=1e-5)
    assert primary_usable_soc_percent(10, 19) == 0
    assert primary_usable_soc_percent(100, 19) == 100
    assert primary_usable_soc_percent(50, 100) is None


def test_measurement_v4_contains_additive_diagnostic_fields():
    row = {
        "primary_discharge_floor_supported": True,
        "primary_discharge_floor_soc_percent": 19.0,
        "primary_discharge_floor_valid": True,
        "primary_discharge_floor_fresh": True,
        "primary_discharge_floor_age_s": 3,
        "primary_discharge_floor_source": "sma_sunny_island:modbus_register_31009",
        "primary_usable_soc_percent": 23.4567,
        "primary_usable_soc_valid": True,
    }
    out = build_v4_row(CFG, row)
    assert out["primary_discharge_floor_supported"] == "1"
    assert out["primary_discharge_floor_soc_percent"] == 19.0
    assert out["primary_discharge_floor_valid"] == "1"
    assert out["primary_discharge_floor_fresh"] == "1"
    assert out["primary_discharge_floor_age_s"] == 3.0
    assert out["primary_discharge_floor_source"] == "sma_sunny_island:modbus_register_31009"
    assert out["primary_usable_soc_percent"] == 23.5
    assert out["primary_usable_soc_valid"] == "1"


def test_readiness_exposes_capability_but_does_not_gate_ready():
    cfg = dict(CFG, SHELLY_STALE_TIMEOUT_SECONDS=15, SOC_STALE_TIMEOUT_SECONDS=90, CROSS_CHARGE_ENABLED=False)
    snap = {
        "mqtt_connected": True,
        "last_shelly_update_age_seconds": 1, "grid_power_valid": True,
        "last_soc_update_age_seconds": 1, "soc_valid": True, "battery_soc": 80,
        "last_sma_battery_update_age_seconds": 1, "second_battery_valid": True,
        "actual_zendure_power_valid": True,
        "mqtt_command_path_available": True, "mqtt_command_path_fresh": True, "mqtt_command_path_valid": True,
        "zendure_command_state_complete": True, "zendure_command_smart_mode": 1,
        "zendure_command_ac_mode": "Input mode", "zendure_command_input_limit_w": 0, "zendure_command_output_limit_w": 0,
        "command_desired_sequence_id": 0, "command_uncertain_mqtt_active": False,
        "command_not_effective_active": False, "command_late_effect_guard_active": False,
        "command_lifecycle_state": "ACTIVE_EFFECTIVE",
        "primary_storage_current_discharge_floor_supported": True,
        "primary_storage_current_discharge_floor_soc_percent": 19,
        "primary_storage_current_discharge_floor_fresh": False,
        "primary_storage_current_discharge_floor_valid": False,
        "primary_storage_current_discharge_floor_last_poll_ok": False,
        "primary_storage_current_discharge_floor_last_error_code": "OPTIONAL_FLOOR_FAIL",
    }
    ready = build_ready_payload(cfg, snap)
    assert ready["ready"] is True
    check = ready["checks"]["primary_storage_source"]
    assert check["current_discharge_floor_supported"] is True
    assert check["current_discharge_floor_valid"] is False
    assert check["ok"] is True


def test_status_payload_labels_capability_as_diagnostic_only():
    cfg = dict(CFG, SECOND_BATTERY_DISPLAY_NAME="Haus-SMA", MIN_SOC_PERCENT=10, MAX_SOC_PERCENT=90)
    snap = {
        "primary_storage_data_available": True,
        "second_battery_data_available": True,
        "second_battery_data_valid": True,
        "second_battery_data_fresh": True,
        "sma_battery_display_power": 260,
        "sma_battery_soc": 38,
        "primary_storage_source_health": "OK",
        "primary_storage_current_discharge_floor_supported": True,
        "primary_storage_current_discharge_floor_soc_percent": 19,
        "primary_storage_current_discharge_floor_valid": True,
        "primary_storage_current_discharge_floor_fresh": True,
        "primary_storage_current_discharge_floor_age_seconds": 2,
        "primary_storage_current_discharge_floor_source": "sma_sunny_island:modbus_register_31009",
        "primary_storage_usable_soc_percent": 23.4567,
        "primary_storage_usable_soc_valid": True,
        "current_mode": "HOLD",
    }
    payload = build_status_view_payload(cfg, snap)
    assert payload["primary"]["discharge_floor_text"] == "19 %"
    assert "23" in payload["primary"]["usable_soc_text"]
    assert payload["primary"]["discharge_floor_supported"] is True
