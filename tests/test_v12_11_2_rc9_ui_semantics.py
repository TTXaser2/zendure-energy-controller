import json
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import version
import web_ui
# Installs the paho-mqtt test stub before importing controller_logic.
from tests import test_operation_priority as op
from state import ControllerState
from web_ui import build_status_view_payload, replay_service_available


class V12112Rc9UiSemanticsTests(unittest.TestCase):
    def setUp(self):
        web_ui._replay_health_cache.update({"port": None, "available": False, "checked_epoch": 0.0})

    def test_version(self):
        self.assertEqual("12.11.2-rc12", version.APP_VERSION)
        self.assertEqual("V12.11.2-RC12", version.APP_VERSION_LABEL)

    def test_replay_probe_uses_lightweight_health_json(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"status": "ok", "version": "12.11.2-rc9"}
        with patch("web_ui.requests.get", return_value=response) as get:
            self.assertTrue(replay_service_available({"REPLAY_WEB_PORT": 8090}))
        get.assert_called_once_with("http://127.0.0.1:8090/health", timeout=1.5)

    def test_replay_probe_rejects_invalid_health_contract(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"status": "starting"}
        with patch("web_ui.requests.get", return_value=response):
            self.assertFalse(replay_service_available({"REPLAY_WEB_PORT": 8090}))

    def test_status_payload_marks_reachable_replay_active(self):
        snap = ControllerState().snapshot()
        snap.update({
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_cycle_total_ms": 10.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps({
                "cycle_total_without_sleep_ms": 10.0,
                "other_cycle_work_ms": 10.0,
            }),
        })
        with patch("web_ui.get_system_metrics", return_value={
            "disk_free_bytes": 80,
            "disk_total_bytes": 100,
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
        }), patch("web_ui.replay_service_available", return_value=True):
            payload = build_status_view_payload({
                "INTERVAL_SECONDS": 3,
                "MEASUREMENT_DB_ENABLED": False,
                "ZENDURE_LOCAL_API_ENABLED": False,
            }, snap, events=[])
        self.assertEqual("Aktiv", payload["diag"]["analysis"])
        self.assertEqual([], payload["events"]["technical_restrictions"])

    def test_optional_local_api_phase_is_visible_as_not_executed(self):
        snap = ControllerState().snapshot()
        snap.update({
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_cycle_total_ms": 20.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps({
                "cycle_total_without_sleep_ms": 20.0,
                "config_reload_ms": 1.0,
                "measurement_logging_ms": 5.0,
                "other_cycle_work_ms": 14.0,
            }),
        })
        with patch("web_ui.replay_service_available", return_value=True):
            payload = build_status_view_payload({
                "INTERVAL_SECONDS": 3,
                "MEASUREMENT_DB_ENABLED": False,
                "ZENDURE_LOCAL_API_ENABLED": False,
            }, snap, events=[])
        local = next(row for row in payload["diag"]["timing_phases"] if row["key"] == "local_api")
        self.assertFalse(local["executed"])
        self.assertIsNone(local["ms"])
        self.assertAlmostEqual(20.0, sum((row["ms"] or 0.0) for row in payload["diag"]["timing_phases"]), places=6)

    def test_local_api_timer_is_omitted_when_poll_is_skipped(self):
        cfg = op.base_cfg(MANUAL_MODE="STOP_HOLD")
        controller, _state, _mqtt, _shelly = op.make_controller(cfg)
        controller._cycle_timing_parts = {}
        controller._timed_local_api_phase(cfg)
        self.assertNotIn("zendure_local_api_ms", controller._cycle_timing_parts)

    def test_storage_payload_and_markup_use_occupied_perspective(self):
        snap = ControllerState().snapshot()
        snap.update({
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_cycle_total_ms": 10.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps({
                "cycle_total_without_sleep_ms": 10.0,
                "other_cycle_work_ms": 10.0,
            }),
        })
        with patch("web_ui.get_system_metrics", return_value={
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
        }), patch("web_ui.replay_service_available", return_value=True):
            payload = build_status_view_payload({
                "INTERVAL_SECONDS": 3,
                "MEASUREMENT_DB_ENABLED": False,
                "ZENDURE_LOCAL_API_ENABLED": False,
            }, snap, events=[])
        self.assertEqual(20.0, payload["logging"]["used_bytes"])
        self.assertEqual(20.0, payload["logging"]["disk_used_percent"])
        html = Path("status_page_v2.py").read_text(encoding="utf-8")
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        self.assertIn("Belegter Speicher", html)
        self.assertIn('data-zec="logging.used_text"', html)
        self.assertIn("p.logging?.used_bytes", js)
        self.assertNotIn('data-zec="logging.free_text"', html)

    def test_timing_order_matches_approved_after_image(self):
        html = Path("status_page_v2.py").read_text(encoding="utf-8")
        total = html.index("zec-timing-total")
        tree = html.index('id="diagTimingTree"')
        meta = html.index('data-zec="diag.cycle_meta"')
        distribution = html.index('id="diagTimingDistribution"')
        async_part = html.index("zec-async-timing")
        self.assertLess(total, tree)
        self.assertLess(tree, meta)
        self.assertLess(meta, distribution)
        self.assertLess(distribution, async_part)

    def test_mini_graph_uses_newest_buffer_point_wording(self):
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        self.assertIn("neuester: ${fmtPower(values.at(-1))}", js)
        self.assertNotIn("aktuell ${fmtPower(values.at(-1))}", js)

    def test_resync_empty_texts_are_compact(self):
        snap = ControllerState().snapshot()
        snap.update({
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_cycle_total_ms": 10.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps({
                "cycle_total_without_sleep_ms": 10.0,
                "other_cycle_work_ms": 10.0,
            }),
        })
        with patch("web_ui.replay_service_available", return_value=True):
            payload = build_status_view_payload({
                "INTERVAL_SECONDS": 3,
                "MEASUREMENT_DB_ENABLED": False,
                "ZENDURE_LOCAL_API_ENABLED": False,
            }, snap, events=[])
        self.assertEqual("Keiner seit Controllerstart", payload["diag"]["resync_text"])
        self.assertEqual("Keiner seit Controllerstart", payload["diag"]["resync_suppressed_text"])

    def test_event_footer_receives_optional_interface_restrictions(self):
        snap = ControllerState().snapshot()
        snap.update({
            "grid_power_valid": True,
            "raw_grid_power": 0,
            "last_local_api_error": "timeout",
            "last_cycle_total_ms": 10.0,
            "last_cycle_completed_epoch": time.time(),
            "last_cycle_timing_json": json.dumps({
                "cycle_total_without_sleep_ms": 10.0,
                "other_cycle_work_ms": 10.0,
            }),
        })
        with patch("web_ui.replay_service_available", return_value=True):
            payload = build_status_view_payload({
                "INTERVAL_SECONDS": 3,
                "MEASUREMENT_DB_ENABLED": False,
                "ZENDURE_LOCAL_API_ENABLED": True,
            }, snap, events=[])
        self.assertEqual(["lokale API nicht erreichbar"], payload["events"]["technical_restrictions"])
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        self.assertIn("Keine offene Störung · ${restrictions.length} technische Einschränkung", js)

    def test_popovers_keep_free_space_and_command_resync_explanations(self):
        js = Path("static/status_v2.js").read_text(encoding="utf-8")
        self.assertIn("`Frei: ${fmtBytes(free)}.`", js)
        self.assertIn("Beim Zendure-Kommandoabgleich sendet ZEC", js)
        self.assertIn("Ein unterdrückter Versuch bedeutet ausdrücklich", js)


class V12112Rc9ManualNightRegressionTests(unittest.TestCase):
    def _finish_manual_discharge(self, *, after="AUTO", soc=40, target=40, reserve=35, night=True, shelly=None):
        cfg = op.base_cfg(
            MANUAL_MODE="FIXED_DISCHARGE",
            MANUAL_FIXED_DISCHARGE_TARGET_SOC=target,
            MANUAL_DISCHARGE_AFTER_TARGET=after,
            NIGHT_DISCHARGE_ENABLED=True,
            NIGHT_DISCHARGE_STOP_SOC_PERCENT=reserve,
            MIN_SOC_PERCENT=15,
        )
        controller, state, mqtt, _ = op.make_controller(cfg, state=op.fresh_state(soc), shelly=shelly or op.OkShelly(0))
        controller.is_night_discharge_active = lambda _cfg: night
        controller.run_once(cfg)
        return controller, state, mqtt

    def test_manual_discharge_target_auto_then_night_discharge_next_cycle(self):
        controller, state, mqtt = self._finish_manual_discharge(soc=40, target=40, reserve=35, night=True)
        self.assertEqual("STOP_HOLD", state.current_mode)
        self.assertEqual("AUTO", controller.config_manager.get()["MANUAL_MODE"])
        mqtt.commands.clear()
        controller.run_once(controller.config_manager.get())
        self.assertEqual("NIGHT_DISCHARGE", state.current_mode)
        self.assertIn(("output", 400, False), mqtt.commands)

    def test_manual_discharge_target_at_night_reserve_uses_auto_branch(self):
        controller, state, mqtt = self._finish_manual_discharge(soc=35, target=35, reserve=35, night=True)
        mqtt.commands.clear()
        controller.run_once(controller.config_manager.get())
        self.assertNotEqual("NIGHT_DISCHARGE", state.current_mode)
        self.assertIn("NIGHT_RESERVE_SOC", state.active_limiters)
        self.assertNotIn(("output", 400, False), mqtt.commands)

    def test_manual_discharge_target_outside_night_window_returns_to_auto(self):
        controller, state, mqtt = self._finish_manual_discharge(soc=40, target=40, reserve=35, night=False)
        mqtt.commands.clear()
        controller.run_once(controller.config_manager.get())
        self.assertNotEqual("NIGHT_DISCHARGE", state.current_mode)
        self.assertNotIn(("output", 400, False), mqtt.commands)

    def test_manual_discharge_stop_hold_does_not_enter_night(self):
        controller, state, mqtt = self._finish_manual_discharge(after="STOP_HOLD", soc=40, target=40, reserve=35, night=True)
        self.assertEqual("STOP_HOLD", controller.config_manager.get()["MANUAL_MODE"])
        mqtt.commands.clear()
        controller.run_once(controller.config_manager.get())
        self.assertEqual("STOP_HOLD", state.current_mode)
        self.assertNotIn(("output", 400, False), mqtt.commands)


if __name__ == "__main__":
    unittest.main()
