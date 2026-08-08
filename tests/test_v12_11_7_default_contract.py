import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from config_manager import ConfigManager, DEFAULT_CONFIG
from settings_model import build_settings_model
from settings_registry import DefaultClass, ResetPolicy, SETTINGS, SETTINGS_BY_KEY
from settings_service import SettingsService

ROOT = Path(__file__).resolve().parents[1]


class V12117DefaultContractTests(unittest.TestCase):
    def _missing_manager(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "config.json"
        manager = ConfigManager(str(path))
        manager.load()
        return path, manager

    def test_all_212_settings_have_explicit_default_provenance(self):
        self.assertEqual(212, len(SETTINGS))
        counts = Counter(spec.default_class.value for spec in SETTINGS)
        self.assertEqual(212, sum(counts.values()))
        self.assertEqual({
            "product_default", "profile_preset", "safe_sentinel",
            "legacy_internal", "installation", "auto_or_unset",
        }, set(counts))
        for spec in SETTINGS:
            self.assertIsInstance(spec.default_class, DefaultClass)
            self.assertIsInstance(spec.reset_policy, ResetPolicy)

    def test_installation_values_have_no_generic_reset_and_safe_bootstrap(self):
        expected = {
            "DEVICE_ID": "", "MQTT_BROKER": "", "MQTT_USER": "",
            "GRID_METER_SOURCE": None, "SHELLY_IP": "",
            "MAX_CHARGE_POWER_W": None, "MAX_DISCHARGE_POWER_W": None,
            "MIN_SOC_PERCENT": None, "MAX_SOC_PERCENT": None,
        }
        for key, bootstrap in expected.items():
            spec = SETTINGS_BY_KEY[key]
            self.assertEqual(DefaultClass.INSTALLATION, spec.default_class, key)
            self.assertEqual(ResetPolicy.NONE, spec.reset_policy, key)
            self.assertEqual(bootstrap, spec.bootstrap_value, key)
            self.assertIsNone(spec.product_default, key)

    def test_measurement_first_install_is_safe_off_not_productive_standard(self):
        spec = SETTINGS_BY_KEY["MEASUREMENT_LOG_MODE"]
        self.assertEqual("off", spec.bootstrap_value)
        self.assertEqual("standard", spec.default_new_install)  # historical field, no longer first-install authority
        self.assertEqual("off", spec.default_rc19)
        self.assertEqual(DefaultClass.SAFE_SENTINEL, spec.default_class)

    def test_backend_rejects_reset_for_installation_value(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = Path(td.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG); cfg.update({"DEVICE_ID":"TESTDEVICE","MQTT_BROKER":"127.0.0.1"})
        path.write_text(json.dumps(cfg) + "\n", encoding="utf-8")
        manager = ConfigManager(str(path)); manager.load(); service = SettingsService(manager)
        result = service.preview({
            "base_revision": manager.cas_revision(),
            "changes": {"MAX_CHARGE_POWER_W": {"op":"reset_default"}}, "secrets": {}
        }, "s", {})
        self.assertEqual("blocked", result["status"])
        self.assertTrue(any(i["code"] == "RESET_NOT_ALLOWED" for i in result["issues"]))

    def test_backend_allows_real_product_default_reset(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = Path(td.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG); cfg.update({"DEVICE_ID":"TESTDEVICE","MQTT_BROKER":"127.0.0.1","DEADBAND_W":120})
        path.write_text(json.dumps(cfg) + "\n", encoding="utf-8")
        manager = ConfigManager(str(path)); manager.load(); service = SettingsService(manager)
        result = service.preview({
            "base_revision": manager.cas_revision(),
            "changes": {"DEADBAND_W": {"op":"reset_default"}}, "secrets": {}
        }, "s", {})
        self.assertEqual("ready", result["status"])
        self.assertTrue(any(d["key"] == "DEADBAND_W" and d["new"] == 80 for d in result["diff"]))

    def test_first_install_requires_explicit_site_and_safety_values_then_commits_canonically(self):
        path, manager = self._missing_manager()
        self.assertEqual("FIRST_INSTALL_SETUP", manager.status()["startup_mode"])
        self.assertFalse(manager.status()["control_allowed"])
        configured = manager.get_configured()
        self.assertEqual("", configured["MQTT_BROKER"])
        self.assertIsNone(configured["MAX_CHARGE_POWER_W"])
        self.assertEqual("off", configured["MEASUREMENT_LOG_MODE"])

        service = SettingsService(manager)
        changes = {
            "DEVICE_ID": {"op":"set","value":"TESTDEVICE"},
            "MQTT_BROKER": {"op":"set","value":"127.0.0.1"},
            "GRID_METER_SOURCE": {"op":"set","value":"shelly_http"},
            "SHELLY_IP": {"op":"set","value":"127.0.0.1"},
            "MAX_CHARGE_POWER_W": {"op":"set","value":1800},
            "MAX_DISCHARGE_POWER_W": {"op":"set","value":1700},
            "MIN_SOC_PERCENT": {"op":"set","value":15},
            "MAX_SOC_PERCENT": {"op":"set","value":95},
        }
        preview = service.preview({"base_revision":manager.cas_revision(),"changes":changes,"secrets":{}}, "s", {})
        self.assertEqual("ready", preview["status"], preview["issues"])
        result = service.commit({"preview_id":preview["preview_id"],"confirmations":preview["confirmations_required"]}, "s")
        self.assertEqual("committed", result["status"])
        self.assertEqual("NORMAL", manager.status()["startup_mode"])
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("off", saved["MEASUREMENT_LOG_MODE"])
        self.assertEqual(0, saved["NIGHT_DISCHARGE_POWER_W"])
        self.assertEqual(1800, saved["MAX_CHARGE_POWER_W"])
        self.assertEqual("/var/lib/zendure-controller/zec_measurements.sqlite3", saved["MEASUREMENT_DB_PATH"])
        manager2 = ConfigManager(str(path)); manager2.load()
        self.assertEqual("NORMAL", manager2.status()["startup_mode"])
        self.assertEqual("off", manager2.get()["MEASUREMENT_LOG_MODE"])
        self.assertEqual(0, manager2.get()["NIGHT_DISCHARGE_POWER_W"])

    def test_first_install_without_required_values_is_blocked(self):
        _path, manager = self._missing_manager()
        service = SettingsService(manager)
        result = service.preview({"base_revision":manager.cas_revision(),"changes":{},"secrets":{}}, "s", {})
        self.assertEqual("blocked", result["status"])
        keys = {k for issue in result["issues"] for k in issue.get("keys", [])}
        self.assertIn("MAX_CHARGE_POWER_W", keys)
        self.assertIn("GRID_METER_SOURCE", keys)

    def test_night_enabled_requires_explicit_positive_power(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = Path(td.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG); cfg.update({"DEVICE_ID":"TESTDEVICE","MQTT_BROKER":"127.0.0.1","NIGHT_DISCHARGE_ENABLED":False})
        path.write_text(json.dumps(cfg) + "\n", encoding="utf-8")
        manager = ConfigManager(str(path)); manager.load(); service = SettingsService(manager)
        result = service.preview({"base_revision":manager.cas_revision(),"changes":{"NIGHT_DISCHARGE_ENABLED":{"op":"set","value":True}},"secrets":{}}, "s", {})
        self.assertEqual("blocked", result["status"])
        self.assertTrue(any(i["code"] == "VAL-025" for i in result["issues"]))

    def test_model_uses_registry_reset_contract_not_ui_hardcoded_lists(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = Path(td.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG); cfg.update({"DEVICE_ID":"TESTDEVICE","MQTT_BROKER":"127.0.0.1"})
        path.write_text(json.dumps(cfg) + "\n", encoding="utf-8")
        manager = ConfigManager(str(path)); manager.load()
        model = build_settings_model(manager, {}, csrf_token="x")
        settings = {s["key"]:s for c in model["categories"] for sec in c["sections"] for s in sec["settings"]}
        self.assertIsNone(settings["MAX_CHARGE_POWER_W"]["default_ui"]["action"])
        self.assertEqual("Auf Default setzen", settings["DEADBAND_W"]["default_ui"]["action"])
        self.assertEqual("Automatische Berechnung verwenden", settings["HARVEST_PRIMARY_CHARGE_FLOOR_W"]["default_ui"]["action"])

    def test_existing_productive_values_are_never_rewritten_by_new_bootstrap_contract(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = Path(td.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({
            "DEVICE_ID": "EXISTINGDEVICE",
            "MQTT_BROKER": "192.0.2.10",
            "NIGHT_DISCHARGE_POWER_W": 400,
            "MAX_CHARGE_POWER_W": 2100,
            "MAX_DISCHARGE_POWER_W": 2050,
            "MIN_SOC_PERCENT": 17,
            "MAX_SOC_PERCENT": 98,
            "MEASUREMENT_LOG_MODE": "standard",
        })
        path.write_text(json.dumps(cfg, sort_keys=True) + "\n", encoding="utf-8")
        before = path.read_bytes()
        manager = ConfigManager(str(path)); manager.load()
        self.assertEqual("NORMAL", manager.status()["startup_mode"])
        self.assertEqual(400, manager.get()["NIGHT_DISCHARGE_POWER_W"])
        self.assertEqual(2100, manager.get()["MAX_CHARGE_POWER_W"])
        self.assertEqual("standard", manager.get()["MEASUREMENT_LOG_MODE"])
        self.assertEqual(before, path.read_bytes())

    def test_first_install_required_fields_are_forced_visible_in_standard_ui(self):
        js = (ROOT / "static" / "settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("firstInstallRequired", js)
        self.assertIn("FIRST_INSTALL_SETUP", js)
        self.assertIn("Erstinbetriebnahme: erforderlich", js)
        self.assertTrue(SETTINGS_BY_KEY["DEVICE_ID"].required_first_install)

    def test_example_config_is_neutral_first_install_template(self):
        cfg = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
        self.assertEqual("", cfg["DEVICE_ID"])
        self.assertEqual("", cfg["MQTT_BROKER"])
        self.assertIsNone(cfg["GRID_METER_SOURCE"])
        self.assertIsNone(cfg["MAX_CHARGE_POWER_W"])
        self.assertIsNone(cfg["MIN_SOC_PERCENT"])
        self.assertEqual("off", cfg["MEASUREMENT_LOG_MODE"])


if __name__ == "__main__":
    unittest.main()
