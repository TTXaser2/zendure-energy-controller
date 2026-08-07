import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import status_page_v2
import version
import web_ui
from tests.test_operation_priority import (
    DummyConfigManager,
    NoopCsv,
    NoopLogger,
    NoopZendureApi,
    OkShelly,
    base_cfg,
    fresh_state,
)
# Importing test_operation_priority installs the paho-mqtt test stub before
# controller_logic is imported.
from controller_logic import ZendureController
from state import ControllerState
from tests.test_v12_11_2_rc12_command_contract import SmartRecordingMqtt


_METRICS = {
    "disk_free_bytes": 80.0,
    "disk_total_bytes": 100.0,
    "cpu_percent": 1.0,
    "ram_used_percent": 20.0,
    "ram_available_bytes": 80,
    "ram_total_bytes": 100,
    "swap_used_bytes": 0,
    "swap_total_bytes": 0,
    "swap_in_bytes_per_s": 0,
    "swap_out_bytes_per_s": 0,
    "temperature_c": 40.0,
    "load": [0.0, 0.0, 0.0],
    "system_uptime_s": 100,
    "throttling": {"available": True, "current": [], "historic": []},
}


def set_command_state(
    state: ControllerState,
    *,
    smart=1,
    ac="Output mode",
    input_limit=0,
    output_limit=0,
    charge_max=2400,
    inverse_max=2400,
):
    now = time.time()
    state.update_zendure_command_property("smartMode", smart, "test", now)
    state.update_zendure_command_property("acMode", ac, "test", now)
    state.update_zendure_command_property("inputLimit", input_limit, "test", now)
    state.update_zendure_command_property("outputLimit", output_limit, "test", now)
    state.update_zendure_command_property("chargeMaxLimit", charge_max, "test", now)
    state.update_zendure_command_property("inverseMaxPower", inverse_max, "test", now)
    state.update_zendure_command_property("gridOffMode", 2, "test", now)
    with state.lock:
        state.zendure_mqtt_overall_status = "ZENDURE_MQTT_OK"
        state.zendure_mqtt_live_confirmed = True
        state.actual_zendure_power_valid = True
        state.last_zendure_power_update_epoch = now


def payload(cfg, snap):
    with patch("web_ui.get_system_metrics", return_value=_METRICS), patch("web_ui.replay_service_available", return_value=True):
        return web_ui.build_status_view_payload(cfg, snap, events=[])


class Rc19StatusTextTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual("12.11.5", version.APP_VERSION)
        self.assertEqual("V12.11.5", version.APP_VERSION_LABEL)

    def test_discharge_path_is_not_misclassified_as_charge(self):
        snap = {
            "current_mode": "DISCHARGE",
            "control_reason": "Netzbezug erkannt -> Zendure entlädt",
            "technical_control_path": "GRID -> DISCHARGE_CONTROL -> OUTPUT",
            "command_desired_intent": "DISCHARGE",
        }
        self.assertEqual("Netzbezug wird reduziert", web_ui._reason_public_text(snap))

    def test_stop_hold_is_not_misclassified_as_deadband_hold(self):
        snap = {
            "current_mode": "STOP_HOLD",
            "control_reason": "Manueller Stop/Hold-Modus",
            "technical_control_path": "MANUAL -> STOP_HOLD",
            "command_desired_intent": "NEUTRALIZE",
        }
        self.assertEqual("Manueller Stopp – Zendure bleibt neutral", web_ui._reason_public_text(snap))

    def test_charge_path_remains_correct(self):
        snap = {
            "current_mode": "CHARGE",
            "control_reason": "PV-Überschuss erkannt -> Zendure lädt",
            "technical_control_path": "GRID -> CHARGE_CONTROL -> INPUT",
            "command_desired_intent": "CHARGE",
        }
        self.assertEqual("Einspeisung wird reduziert", web_ui._reason_public_text(snap))

    def test_discharge_cycle_does_not_claim_export_input_was_used(self):
        cfg = base_cfg(
            MANUAL_MODE="AUTO",
            NIGHT_DISCHARGE_ENABLED=False,
            MIN_SOC_PERCENT=15,
            MAX_SOC_PERCENT=99,
            DEADBAND_W=80,
        )
        state = fresh_state(80)
        mqtt = SmartRecordingMqtt()
        set_command_state(state, ac="Output mode", inverse_max=2400)
        controller = ZendureController(
            DummyConfigManager(cfg), state, mqtt, OkShelly(800),
            NoopCsv(), NoopZendureApi(), NoopLogger(),
        )
        controller.run_once(cfg)
        controller.csv_logger.log = lambda _cfg, _row: {}
        controller.finish_cycle(cfg, time.time())
        self.assertEqual("DISCHARGE", state.current_mode)
        self.assertFalse(state.effective_export_power_used_for_control)


class Rc19CapacityAndFixedModeTests(unittest.TestCase):
    def test_remaining_capacity_updates_in_stop_hold(self):
        cfg = base_cfg(
            MANUAL_MODE="STOP_HOLD",
            ZENDURE_BATTERY_CAPACITY_WH=5280,
            ZENDURE_BATTERY_CAPACITY_KWH=5.28,
            MAX_SOC_PERCENT=99,
        )
        state = fresh_state(80)
        controller = ZendureController(
            DummyConfigManager(cfg), state, SmartRecordingMqtt(), OkShelly(0),
            NoopCsv(), NoopZendureApi(), NoopLogger(),
        )
        controller.run_once(cfg)
        self.assertAlmostEqual(1.0032, state.zendure_remaining_capacity_kwh, places=4)

    def test_view_payload_recomputes_stale_remaining_capacity(self):
        cfg = base_cfg(
            ZENDURE_BATTERY_CAPACITY_WH=5280,
            ZENDURE_BATTERY_CAPACITY_KWH=5.28,
            MAX_SOC_PERCENT=99,
            ZENDURE_LOCAL_API_ENABLED=False,
        )
        snap = ControllerState().snapshot()
        snap.update({
            "battery_soc": 80,
            "zendure_remaining_capacity_kwh": 0.05,
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_cycle_total_ms": 10.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps({"cycle_total_without_sleep_ms": 10.0, "other_cycle_work_ms": 10.0}),
        })
        result = payload(cfg, snap)
        self.assertAlmostEqual(1.0032, result["zendure"]["remaining"], places=4)
        self.assertEqual("1,00 kWh", result["zendure"]["remaining_text"])

    def test_fixed_discharge_preserves_requested_and_applied_targets(self):
        cfg = base_cfg(
            MANUAL_MODE="FIXED_DISCHARGE",
            MANUAL_FIXED_DISCHARGE_POWER_W=2400,
            MAX_DISCHARGE_POWER_W=2400,
            MANUAL_FIXED_DISCHARGE_TARGET_SOC=78,
        )
        state = fresh_state(83)
        mqtt = SmartRecordingMqtt()
        set_command_state(state, ac="Output mode", inverse_max=2000)
        controller = ZendureController(
            DummyConfigManager(cfg), state, mqtt, OkShelly(0),
            NoopCsv(), NoopZendureApi(), NoopLogger(),
        )
        controller.handle_manual_fixed_discharge(cfg)
        snap = state.snapshot()
        self.assertEqual(-2400, snap["target_raw_w"])
        self.assertEqual(-2000, snap["target_after_power_limit_w"])
        self.assertEqual(-2000, snap["target_final_w"])
        self.assertEqual("ZENDURE_DEVICE_INVERSE_MAX_POWER", snap["target_power_limit_reason"])
        self.assertIn("ZENDURE_DEVICE_INVERSE_MAX_POWER", state.active_limiters)

    def test_fixed_projection_uses_applied_target(self):
        cfg = base_cfg(
            MANUAL_FIXED_DISCHARGE_POWER_W=2400,
            MAX_DISCHARGE_POWER_W=2400,
            MANUAL_FIXED_DISCHARGE_TARGET_SOC=78,
            ZENDURE_BATTERY_CAPACITY_WH=5280,
        )
        snap = {
            "battery_soc": 83,
            "target_final_w": -2000,
            "last_output_power": 2000,
            "zendure_device_inverse_max_power_w": 2000,
        }
        self.assertEqual(2000, web_ui._fixed_mode_effective_power_w(cfg, snap, "MANUAL_FIXED_DISCHARGE"))

    def test_fixed_mode_payload_explains_device_cap(self):
        cfg = base_cfg(
            MANUAL_FIXED_DISCHARGE_POWER_W=2400,
            MAX_DISCHARGE_POWER_W=2400,
            MANUAL_FIXED_DISCHARGE_TARGET_SOC=78,
            ZENDURE_BATTERY_CAPACITY_WH=5280,
            ZENDURE_LOCAL_API_ENABLED=False,
        )
        snap = ControllerState().snapshot()
        snap.update({
            "current_mode": "MANUAL_FIXED_DISCHARGE",
            "battery_soc": 83,
            "zendure_target_signed_power": -2000,
            "target_raw_w": -2400,
            "target_final_w": -2000,
            "target_power_limit_reason": "ZENDURE_DEVICE_INVERSE_MAX_POWER",
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_cycle_total_ms": 10.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps({"cycle_total_without_sleep_ms": 10.0, "other_cycle_work_ms": 10.0}),
        })
        result = payload(cfg, snap)
        self.assertEqual("Wirksames Ziel", result["mode"]["target_label"])
        self.assertEqual("−2,40 kW Entladen", result["mode"]["requested_target"])
        self.assertEqual("Zendure-Gerätecap inverseMaxPower", result["mode"]["limit_text"])


class Rc19LocalApiUiTests(unittest.TestCase):
    def _api_payload(self, **updates):
        cfg = base_cfg(
            ZENDURE_LOCAL_API_ENABLED=True,
            ZENDURE_LOCAL_API_USE_FOR_TELEMETRY=True,
            ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY=True,
            ZENDURE_LOCAL_IP="192.168.0.50",
        )
        snap = ControllerState().snapshot()
        snap.update({
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_cycle_total_ms": 10.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps({"cycle_total_without_sleep_ms": 10.0, "other_cycle_work_ms": 10.0}),
            "zendure_local_api_worker_state": "IDLE",
            "zendure_local_api_snapshot_valid": True,
            "zendure_local_api_snapshot_stale": False,
            "zendure_local_api_last_success_age_s": 2.9,
            "zendure_local_api_last_attempt_age_s": 2.8,
            "zendure_local_api_latest_attempt_ok": True,
            "zendure_local_api_request_duration_ms": 30.25,
            "zendure_local_api_snapshot_apply_ms": 1.288,
            "zendure_local_api_consecutive_errors": 0,
            "zendure_local_api_backoff_remaining_s": 0,
            "zendure_local_api_latest_error_code": "NONE",
            "zendure_telemetry_source": "MQTT",
            "zendure_local_api_fallback_active": False,
        })
        snap.update(updates)
        return cfg, payload(cfg, snap)

    def test_compact_worker_status_and_source_are_visible(self):
        cfg, result = self._api_payload()
        self.assertEqual("Snapshot aktuell · MQTT ist Primärquelle", result["diag"]["api"])
        self.assertIn("IDLE", result["diag"]["api_worker_text"])
        self.assertEqual("letzter Request 30.2 ms", result["diag"]["api_request_text"])
        self.assertEqual([], result["events"]["technical_restrictions"])
        rendered = status_page_v2.render_status_page_v2(cfg, result, analysis_available=True, analysis_port=8090)
        self.assertIn("API-Hintergrundworker", rendered)
        self.assertIn("Zendure Local API, asynchron", rendered)
        self.assertIn("API-Snapshotübernahme, synchron", rendered)

    def test_api_fallback_active_is_named(self):
        _, result = self._api_payload(zendure_telemetry_source="LOCAL_API", zendure_local_api_fallback_active=True)
        self.assertEqual("Snapshot aktuell · API liefert aktive Telemetrie", result["diag"]["api"])
        self.assertTrue(result["diag"]["api_fallback_active"])

    def test_backoff_is_reported_as_restriction(self):
        _, result = self._api_payload(
            zendure_local_api_worker_state="BACKOFF",
            zendure_local_api_snapshot_valid=False,
            zendure_local_api_snapshot_stale=True,
            zendure_local_api_consecutive_errors=3,
            zendure_local_api_backoff_remaining_s=20,
        )
        self.assertEqual("warn", result["diag"]["api_tone"])
        self.assertEqual(["lokale API eingeschränkt"], result["events"]["technical_restrictions"])

    def test_frontend_popover_contains_full_worker_diagnostics(self):
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        for token in (
            "api_worker_state", "api_last_attempt_age_s", "api_last_success_age_s",
            "api_last_request_duration_ms", "api_snapshot_apply_ms",
            "api_consecutive_errors", "api_backoff_remaining_s", "api_error_code",
        ):
            self.assertIn(token, js)


class Rc19InstallerTests(unittest.TestCase):
    def test_ready_check_requires_boolean_true_and_allows_real_startup_time(self):
        script = Path("tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('tools/evaluate_installation_readiness.py', script)
        self.assertIn("SECONDS + 90", script)
        self.assertIn("Bevorzugt wird ready=true", script)
        self.assertIn("TRANSITIONAL_STREAK", script)
        self.assertNotIn("Update abgeschlossen und Ready-Check erfolgreich.\n", "")


if __name__ == "__main__":
    unittest.main()
