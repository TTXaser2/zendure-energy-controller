import csv
import json
import os
import tempfile
import time
import unittest

from csv_logger import CsvRotatingLogger
from measurement_v4_contract import STANDARD_HEADER
from tests.test_measurement_v4_writer import base_config, base_row
from tests.test_operation_priority import OkShelly, base_cfg, fresh_state, make_controller
from state import ControllerState
from web_ui import build_status_page


class MeasurementV4Rc5Tests(unittest.TestCase):
    def _run_full_cycle(self, controller, cfg):
        start = time.time()
        controller.run_once(cfg)
        controller.finish_cycle(cfg, start)

    def test_v4_size_rotation_creates_registered_physical_file_not_hidden_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = base_config(tmp)
            cfg["MEASUREMENT_LOG_MAX_BYTES"] = 1
            logger = CsvRotatingLogger()
            logger.log(cfg, base_row())
            logger.log(cfg, {**base_row(), "cycle_id": 43, "epoch_s": 1780000003.123})
            logger.close()
            csv_files = sorted(name for name in os.listdir(tmp) if name.startswith("zendure_measurements_v4") and name.endswith(".csv"))
            self.assertGreaterEqual(len(csv_files), 2)
            self.assertFalse(any(name.endswith("_1.csv") or name.endswith("_2.csv") for name in csv_files))
            with open(os.path.join(tmp, "zec_measurement_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            manifest_files = sorted(entry["file_name"] for entry in manifest["files"])
            self.assertEqual(sorted(csv_files), manifest_files)

    def test_night_window_exit_neutralizes_old_fixed_discharge_before_deadband_can_hold_it(self):
        cfg = base_cfg(NIGHT_DISCHARGE_ENABLED=True, DEADBAND_W=80)
        state = fresh_state(80)
        with state.lock:
            state.current_mode = "NIGHT_DISCHARGE"
            state.last_output_power = 400
            state.current_target_power = 400
            state.technical_control_path = "NIGHT_MODE -> OUTPUT"
        controller, state, mqtt, shelly = make_controller(cfg, state=state, shelly=OkShelly(0))
        controller.is_night_discharge_active = lambda _cfg: False

        self._run_full_cycle(controller, cfg)

        self.assertIn(("output", 0, True), mqtt.commands)
        self.assertEqual(0, state.last_output_power)
        self.assertEqual(0, state.current_target_power)
        self.assertNotEqual("NIGHT_DISCHARGE", state.current_mode)

    def test_status_ui_uses_active_cycle_time_as_primary_timing_value(self):
        cfg = base_config("/tmp")
        snapshot = ControllerState().snapshot()
        snapshot.update({
            "last_loop_duration_ms": 17,
            "last_cycle_total_ms": 143,
            "last_cycle_slowest_step": "measurement_logging_ms",
            "last_cycle_slowest_step_ms": 22,
            "loop_counter": 60,
            "uptime_seconds": 193,
            "mqtt_connected": True,
            "last_shelly_update_age_seconds": 1,
            "battery_soc": 80,
            "current_mode": "AUTO",
            "grid_power": 0,
            "raw_grid_power": 0,
            "grid_power_valid": True,
            "grid_power_fresh": True,
            "grid_power_used_for_control": True,
            "last_input_power": 0,
            "last_output_power": 0,
            "actual_zendure_power": 0,
            "actual_zendure_system_power": 0,
            "actual_zendure_system_charge_power": 0,
            "actual_zendure_system_discharge_power": 0,
            "zendure_pack_power_details": [],
            "zendure_temperature_details": [],
            "active_limiters": [],
            "last_control_action": "-",
            "technical_control_path": "GRID -> DEADBAND",
            "measurement_log_status": "active",
            "measurement_log_status_reason": "OK",
            "measurement_log_path": "/media/pi/4CD6-6466/ZEC/logs/zendure_measurements_v4.csv",
            "measurement_log_active_target_type": "external_mount",
            "measurement_fallback_count_since_start": 0,
            "measurement_estimated_retention_hours": 1,
            "measurement_free_disk_mb": 100,
        })
        html = build_status_page(cfg, snapshot)
        self.assertIn("Aktive Zykluszeit", html)
        self.assertIn("143 ms", html)
        self.assertIn("Messdaten-Logging 22 ms", html)
        self.assertNotIn("cycle_total_without_sleep_ms", html)



if __name__ == "__main__":
    unittest.main()
