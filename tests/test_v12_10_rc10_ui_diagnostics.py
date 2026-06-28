import sys
import types
import unittest

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
from csv_logger import compute_config_control_hash
from web_ui import build_base_header, night_mode_projection_text, rest_surplus_status_lines


class Rc10UiDiagnosticsTests(unittest.TestCase):
    def test_control_hash_changes_when_harvest_settings_change(self):
        cfg_a = dict(DEFAULT_CONFIG)
        cfg_b = dict(DEFAULT_CONFIG)
        cfg_a.update({
            "REST_SURPLUS_HARVEST_ENABLED": False,
            "SECOND_BATTERY_MAX_CHARGE_POWER_W": "",
            "REST_SURPLUS_MIN_EXPORT_W": 80,
        })
        cfg_b.update({
            "REST_SURPLUS_HARVEST_ENABLED": True,
            "SECOND_BATTERY_MAX_CHARGE_POWER_W": 2300,
            "REST_SURPLUS_MIN_EXPORT_W": 80,
        })
        self.assertNotEqual(compute_config_control_hash(cfg_a), compute_config_control_hash(cfg_b))

    def test_night_projection_names_missing_settings_path_for_capacity(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({
            "NIGHT_DISCHARGE_ENABLED": True,
            "NIGHT_START_HOUR": 0,
            "NIGHT_START_MINUTE": 0,
            "NIGHT_END_HOUR": 23,
            "NIGHT_END_MINUTE": 59,
            "NIGHT_DISCHARGE_POWER_W": 400,
            "ZENDURE_BATTERY_CAPACITY_WH": "",
        })
        text = night_mode_projection_text(cfg, {"battery_soc": 60}, "NIGHT_DISCHARGE")
        self.assertIn("Settings → Nachtmodus", text)
        self.assertIn("Batteriekapazität", text)

    def test_dark_theme_contains_subgroup_and_info_box_contrast_rules(self):
        html = build_base_header("Test", cfg={"UI_DARK_MODE": True})
        self.assertIn(".subgroup-card", html)
        self.assertIn(".info-box { background:#0f2a3f", html)
        self.assertIn(".error-box", html)

    def test_rest_surplus_status_lines_separate_configuration_readiness_activity(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({
            "REST_SURPLUS_HARVEST_ENABLED": True,
            "SECOND_BATTERY_MAX_CHARGE_POWER_W": 2300,
            "REST_SURPLUS_MIN_EXPORT_W": 80,
            "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": 30,
            "SECOND_BATTERY_CHARGE_SATURATION_MARGIN_W": 100,
            "CROSS_CHARGE_ENABLED": True,
        })
        snap = {
            "second_battery_data_valid": True,
            "second_battery_data_fresh": True,
            "rest_surplus_harvest_active": False,
            "rest_surplus_harvest_eligible": True,
            "rest_surplus_entry_progress_s": 18,
            "second_battery_charge_saturation_threshold_w": 2200,
        }
        text = rest_surplus_status_lines(cfg, snap)
        self.assertIn("Konfiguration: aktiviert", text)
        self.assertIn("Bereitschaft: bereit", text)
        self.assertIn("Entry läuft", text)
        self.assertIn("18 / 30 s", text)


if __name__ == "__main__":
    unittest.main()
