import json
import time
import unittest
from pathlib import Path

import version
# Installs the paho-mqtt test stub before importing controller_logic.
from tests import test_operation_priority as _operation_priority_stub  # noqa: F401
from controller_logic import ZendureController
from state import ControllerState
from web_ui import build_status_view_payload


class V12112Rc8BacklogCompletionTests(unittest.TestCase):
    def _controller_for_effect_monitor(self, *, target_input=0, target_output=0, actual=0, age=1.0, status="ZENDURE_MQTT_OK", live=True):
        controller = ZendureController.__new__(ZendureController)
        controller.state = ControllerState()
        controller._last_zendure_mqtt_status = status
        controller._mqtt_uncertain_since_epoch = None
        controller._mqtt_uncertain_cycles = 0
        controller._mqtt_uncertain_had_hard_loss = False
        controller._last_resync_signature = ""
        controller._last_resync_epoch = 0.0
        controller._command_effect_watch_target = 0
        controller._command_effect_watch_start_epoch = None
        controller._command_effect_last_resend_epoch = 0.0
        controller._last_command_effect_log_epoch = 0.0
        with controller.state.lock:
            controller.state.last_input_power = target_input
            controller.state.last_output_power = target_output
            controller.state.zendure_mqtt_overall_status = status
            controller.state.zendure_mqtt_live_confirmed = live
            controller.state.actual_zendure_system_signed_power = actual
            controller.state.actual_zendure_power_valid = True
            controller.state.last_zendure_power_update_epoch = time.time() - float(age)
            controller.state.actual_zendure_power_age_s = age
            controller.state.command_uncertain_mqtt_active = True
            controller.state.command_uncertain_mqtt_target_w = -29
            controller.state.command_uncertain_mqtt_reason = "alte Warnung"
            controller.state.command_uncertain_mqtt_status = "ZENDURE_MQTT_STALE"
            controller.state.command_uncertain_mqtt_since_epoch = time.time() - 60
            controller.state.command_uncertain_mqtt_since_time = "10:00:00"
        return controller

    def test_version(self):
        self.assertEqual("12.11.2-rc17", version.APP_VERSION)
        self.assertEqual("V12.11.2-RC17", version.APP_VERSION_LABEL)

    def test_neutral_fresh_actual_clears_only_stale_diagnostic_uncertainty(self):
        controller = self._controller_for_effect_monitor(actual=0, age=1.0)
        controller.update_command_effect_monitor({
            "COMMAND_EFFECT_TOLERANCE_W": 80,
            "ZENDURE_POWER_STALE_TIMEOUT_SECONDS": 90,
        })
        with controller.state.lock:
            self.assertFalse(controller.state.command_uncertain_mqtt_active)
            self.assertEqual("", controller.state.command_uncertain_mqtt_reason)
            self.assertEqual("COMMAND_NEUTRALIZATION_CONFIRMED", controller.state.command_effect_category)
            self.assertIn("Neutraler Gerätezustand", controller.state.command_effect_reason)
            self.assertEqual(0, controller.state.last_input_power)
            self.assertEqual(0, controller.state.last_output_power)

    def test_uncertainty_is_not_cleared_without_confirmed_neutral_device_state(self):
        controller = self._controller_for_effect_monitor(actual=-400, age=1.0)
        controller.update_command_effect_monitor({
            "COMMAND_EFFECT_TOLERANCE_W": 80,
            "ZENDURE_POWER_STALE_TIMEOUT_SECONDS": 90,
        })
        with controller.state.lock:
            self.assertTrue(controller.state.command_uncertain_mqtt_active)

        controller = self._controller_for_effect_monitor(actual=0, age=120.0)
        controller.update_command_effect_monitor({
            "COMMAND_EFFECT_TOLERANCE_W": 80,
            "ZENDURE_POWER_STALE_TIMEOUT_SECONDS": 90,
        })
        with controller.state.lock:
            self.assertTrue(controller.state.command_uncertain_mqtt_active)

    def test_timing_payload_exposes_cycle_context_and_complete_distribution(self):
        timing = {
            "cycle_total_without_sleep_ms": 50.0,
            "config_reload_ms": 1.0,
            "zendure_local_api_ms": 25.0,
            "sma_energy_meter_ms": 1.0,
            "control_decision_ms": 1.0,
            "mqtt_command_path_ms": 8.0,
            "command_effect_monitor_ms": 1.0,
            "measurement_logging_ms": 8.0,
            "other_cycle_work_ms": 5.0,
        }
        snap = ControllerState().snapshot()
        snap.update({
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_cycle_total_ms": 50.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps(timing),
            "last_cycle_slowest_step": "zendure_local_api_ms",
            "last_cycle_slowest_step_ms": 25.0,
        })
        payload = build_status_view_payload({
            "INTERVAL_SECONDS": 2,
            "SLOW_CYCLE_WARN_MS": 5000,
            "MEASUREMENT_DB_ENABLED": False,
        }, snap, events=[])
        diag = payload["diag"]
        self.assertEqual("Zyklusabstand ca. 2,05 s · aktive Arbeit 2,4 %", diag["cycle_meta_text"])
        self.assertFalse(diag["cycle_slow_warning"])
        self.assertEqual(5000.0, diag["slow_cycle_warn_ms"])
        self.assertAlmostEqual(50.0, sum(row["ms"] for row in diag["timing_phases"]), places=6)
        self.assertAlmostEqual(100.0, sum(row["percent"] for row in diag["timing_phases"]), places=6)
        self.assertEqual(
            ["config", "local_api", "energy_data", "control", "mqtt", "effect", "logging", "other"],
            [row["key"] for row in diag["timing_phases"]],
        )

    def test_slow_cycle_warning_uses_named_config_threshold(self):
        snap = ControllerState().snapshot()
        snap.update({
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_cycle_total_ms": 5100.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps({
                "cycle_total_without_sleep_ms": 5100.0,
                "other_cycle_work_ms": 5100.0,
            }),
        })
        payload = build_status_view_payload({
            "INTERVAL_SECONDS": 2,
            "SLOW_CYCLE_WARN_MS": 5000,
            "MEASUREMENT_DB_ENABLED": False,
        }, snap, events=[])
        self.assertTrue(payload["diag"]["cycle_slow_warning"])

    def test_frontend_links_timing_colors_to_rows_and_distribution(self):
        html = Path("status_page_v2.py").read_text(encoding="utf-8")
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        css = Path("static/status_v2.css").read_text(encoding="utf-8")
        self.assertIn('id="diagTimingDistribution"', html)
        self.assertIn('data-zec="diag.cycle_meta"', html)
        self.assertIn("zec-timing-key", js)
        self.assertIn("zec-timing-segment", js)
        self.assertIn("phaseClass(row.key)", js)
        self.assertIn(".zec-phase-local_api", css)
        self.assertIn(".zec-phase-mqtt", css)
        self.assertNotIn("meter('diag.cycle'", js)
        self.assertIn("Slow-Cycle-Warnschwelle", js)

    def test_soc_chart_uses_quantization_aware_display_reconstruction(self):
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        self.assertIn("reconstructQuantizedSoc", js)
        self.assertIn("drawQuantizedSocLine", js)
        self.assertIn("duration>=20", js)
        self.assertIn("protectedLevels", js)
        self.assertNotIn("drawMonotoneLine", js)
        self.assertNotIn("bezierCurveTo", js)

    def test_update_script_waits_for_valid_ready_json(self):
        script = Path("tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn("READY_DEADLINE=$((SECONDS + 20))", script)
        self.assertIn('while [ "$SECONDS" -lt "$READY_DEADLINE" ]', script)
        self.assertIn("python3 -m json.tool", script)
        self.assertIn("Update abgeschlossen und Ready-Check erfolgreich", script)
        self.assertIn("innerhalb von 20 Sekunden kein gültiges JSON", script)
        self.assertNotIn('curl -s "http://127.0.0.1:8080/ready" | python3 -m json.tool || true', script)

    def test_fastapi_uses_lifespan_and_ui_test_closes_file(self):
        web = Path("web_ui.py").read_text(encoding="utf-8")
        old_test = Path("tests/test_v12_11_2_rc5_operations_dashboard.py").read_text(encoding="utf-8")
        self.assertIn("@asynccontextmanager", web)
        self.assertIn("lifespan=lifespan", web)
        self.assertNotIn('@app.on_event("startup")', web)
        self.assertNotIn('@app.on_event("shutdown")', web)
        self.assertIn("Path(\"static/status_v2.js\").read_text", old_test)
        self.assertNotIn('open("static/status_v2.js"', old_test)


if __name__ == "__main__":
    unittest.main()
