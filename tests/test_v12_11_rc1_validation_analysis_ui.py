import sys
import types
import unittest
from pathlib import Path

if "paho" not in sys.modules:
    paho = types.ModuleType("paho")
    paho_mqtt = types.ModuleType("paho.mqtt")
    paho_client = types.ModuleType("paho.mqtt.client")
    paho_client.CallbackAPIVersion = types.SimpleNamespace(VERSION2=object())
    paho_client.Client = lambda *args, **kwargs: types.SimpleNamespace(
        on_message=None, on_connect=None, on_disconnect=None,
        username_pw_set=lambda *a, **k: None,
        connect=lambda *a, **k: None,
        loop_start=lambda *a, **k: None,
        subscribe=lambda *a, **k: None,
        publish=lambda *a, **k: types.SimpleNamespace(rc=0),
    )
    sys.modules["paho"] = paho
    sys.modules["paho.mqtt"] = paho_mqtt
    sys.modules["paho.mqtt.client"] = paho_client

from config_manager import DEFAULT_CONFIG
from config_validator import validate_config_semantics
from tools.replay_core import _v4_harvest_analysis, _v4_timing_analysis
from web_ui import build_settings_page, night_mode_projection_text


def issue_codes(issues):
    return {i.code for i in issues}


class Rc11PhaseAValidationAnalysisUiTests(unittest.TestCase):
    def test_harvest_validator_uses_actionable_german_messages(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({
            "REST_SURPLUS_HARVEST_ENABLED": True,
            "SECOND_BATTERY_MAX_CHARGE_POWER_W": "",
            "CROSS_CHARGE_ENABLED": True,
        })
        issues = validate_config_semantics(cfg)
        codes = issue_codes(issues)
        self.assertIn("HARVEST_MAX_CHARGE_MISSING", codes)
        text = "\n".join(i.message for i in issues)
        self.assertIn("Settings → Zweitbatterie → Restüberschuss-Ernte", text)
        self.assertNotIn("frische", text)

    def test_night_projection_distinguishes_mqtt_soc_from_settings_problem(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({
            "NIGHT_DISCHARGE_ENABLED": True,
            "NIGHT_START_HOUR": 0,
            "NIGHT_START_MINUTE": 0,
            "NIGHT_END_HOUR": 23,
            "NIGHT_END_MINUTE": 59,
            "NIGHT_DISCHARGE_POWER_W": 400,
            "ZENDURE_BATTERY_CAPACITY_WH": 5280,
        })
        text = night_mode_projection_text(cfg, {"battery_soc": None}, "NIGHT_DISCHARGE")
        self.assertIn("Zendure-MQTT-Werte", text)
        self.assertIn("nicht aktuell", text)

    def test_settings_page_has_no_hidden_legacy_contract_and_uses_live_model(self):
        cfg = dict(DEFAULT_CONFIG)
        html = build_settings_page(cfg)
        script = (Path(__file__).resolve().parents[1] / "static" / "settings_v2.js").read_text(encoding="utf-8")
        self.assertNotIn("Entlade-Blockgrenze (Legacy)", html)
        self.assertNotIn("legacy-settings-contract", html)
        self.assertIn("app.model.categories", script)
        self.assertIn("dependencyVisible", script)

    def test_harvest_analysis_separates_measured_and_modelled_effect(self):
        rows = []
        for i in range(3):
            rows.append({
                "dt_s": "3",
                "measurement_time_utc": f"2026-06-29T08:00:0{i}Z",
                "rest_surplus_harvest_active": "1",
                "target_final_reason": "REST_SURPLUS_HARVEST",
                "zendure_actual_power_w": "1000",
                "second_battery_power_w": "2300",
                "grid_power_w": "-200",
                "control_soc_percent": "50",
                "second_battery_charge_saturation_threshold_w": "2200",
            })
        analysis = _v4_harvest_analysis(rows)
        self.assertGreater(analysis["active"]["zendure_charge_kwh"], 0)
        self.assertGreater(analysis["active"]["estimated_avoided_immediate_export_kwh"], 0)
        self.assertIn("Ohne Harvest", analysis["assumption"])
        self.assertEqual("wahrscheinlich zusätzliche Speicherung", analysis["value_classification"])

    def test_timing_analysis_detects_local_api_slowest_phase(self):
        rows = [
            {"cycle_duration_ms": "2500", "cycle_timing_json": '{"zendure_local_api_ms":2200,"measurement_logging_ms":20}'},
            {"cycle_duration_ms": "800", "cycle_timing_json": '{"zendure_local_api_ms":100,"measurement_logging_ms":30}'},
        ]
        timing = _v4_timing_analysis(rows)
        self.assertEqual(1, timing["cycles_gt_2000_ms"])
        self.assertGreaterEqual(timing["local_api_ms_max"], 2200)
        self.assertEqual("zendure_local_api_ms", timing["slowest_step_top"][0]["name"])


if __name__ == "__main__":
    unittest.main()
