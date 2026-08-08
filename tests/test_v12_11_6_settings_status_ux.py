import json
import os
import tempfile
import unittest
from pathlib import Path

from config_manager import ConfigManager, DEFAULT_CONFIG
from settings_model import build_settings_model
from settings_registry import SETTINGS_BY_KEY
from state import ControllerState

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_JS = (ROOT / "static/settings_v2.js").read_text(encoding="utf-8")
SETTINGS_CSS = (ROOT / "static/settings_v2.css").read_text(encoding="utf-8")
STATUS_JS = (ROOT / "static/status_v2.js").read_text(encoding="utf-8")
STATUS_CSS = (ROOT / "static/status_v2.css").read_text(encoding="utf-8")


class V12116SettingsStatusUxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({"DEVICE_ID": "TESTDEVICE", "HEADLESS_MODE": False})
        path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
        self.manager = ConfigManager(str(path))
        self.manager.load()
        self.model = build_settings_model(self.manager, ControllerState().snapshot(), csrf_token="abc")

    def _category(self, name):
        return next(c for c in self.model["categories"] if c["name"] == name)

    def _setting(self, key):
        return next(
            s
            for category in self.model["categories"]
            for section in category["sections"]
            for s in section["settings"]
            if s["key"] == key
        )

    def test_new_install_fixed_power_profiles_are_safe_zero_but_migration_values_remain(self):
        self.assertEqual(0, DEFAULT_CONFIG["NIGHT_DISCHARGE_POWER_W"])
        self.assertEqual(0, DEFAULT_CONFIG["MANUAL_FIXED_DISCHARGE_POWER_W"])
        self.assertEqual(0, DEFAULT_CONFIG["MANUAL_FIXED_CHARGE_POWER_W"])
        self.assertEqual(0, SETTINGS_BY_KEY["NIGHT_DISCHARGE_POWER_W"].default_new_install)
        self.assertEqual(400, SETTINGS_BY_KEY["NIGHT_DISCHARGE_POWER_W"].default_rc19)
        self.assertEqual(0, SETTINGS_BY_KEY["MANUAL_FIXED_DISCHARGE_POWER_W"].default_new_install)
        self.assertEqual(400, SETTINGS_BY_KEY["MANUAL_FIXED_DISCHARGE_POWER_W"].default_rc19)
        self.assertEqual(0, SETTINGS_BY_KEY["MANUAL_FIXED_CHARGE_POWER_W"].default_new_install)
        self.assertEqual(800, SETTINGS_BY_KEY["MANUAL_FIXED_CHARGE_POWER_W"].default_rc19)

    def test_default_ui_policy_distinguishes_default_clear_derived_and_installation_values(self):
        night = self._setting("NIGHT_DISCHARGE_POWER_W")
        self.assertEqual("sentinel", night["default_ui"]["kind"])
        self.assertIn("Sicherer Ausgangszustand", night["default_ui"]["meta"])
        self.assertEqual("Auf sicheren Ausgangszustand setzen", night["default_ui"]["action"])

        reserve = self._setting("NIGHT_DISCHARGE_STOP_SOC_PERCENT")
        self.assertEqual("clear", reserve["default_ui"]["kind"])
        self.assertEqual("Reserve-SOC entfernen", reserve["default_ui"]["action"])
        self.assertIsNone(reserve["default_ui"]["value"])

        derived = self._setting("HARVEST_PRIMARY_CHARGE_FLOOR_W")
        self.assertEqual("auto", derived["default_ui"]["kind"])
        self.assertEqual("Automatische Berechnung verwenden", derived["default_ui"]["action"])

        capacity = self._setting("ZENDURE_BATTERY_CAPACITY_WH")
        self.assertEqual("installation", capacity["default_ui"]["kind"])
        self.assertIn("kein allgemeiner Standardwert", capacity["default_ui"]["meta"])

        broker = self._setting("MQTT_BROKER")
        self.assertEqual("installation", broker["default_ui"]["kind"])
        self.assertIsNone(broker["default_ui"]["action"])

        ui = self._setting("UI_DARK_MODE")
        self.assertEqual("default", ui["default_ui"]["kind"])
        self.assertEqual("Auf Default setzen", ui["default_ui"]["action"])

    def test_logical_ordering_is_user_oriented(self):
        manual = self._category("Betriebsart & manuelle Steuerung")
        discharge = next(s for s in manual["sections"] if s["name"] == "Profil Feste Entladung")
        self.assertEqual(
            ["MANUAL_FIXED_DISCHARGE_POWER_W", "MANUAL_FIXED_DISCHARGE_TARGET_SOC", "MANUAL_DISCHARGE_AFTER_TARGET"],
            [x["key"] for x in discharge["settings"]],
        )
        night = self._category("Nachtbetrieb")
        self.assertLess(
            [s["name"] for s in night["sections"]].index("Zeitfenster"),
            [s["name"] for s in night["sections"]].index("Feste Basisentladung"),
        )
        time_section = next(s for s in night["sections"] if s["name"] == "Zeitfenster")
        self.assertEqual(
            ["NIGHT_START_HOUR", "NIGHT_START_MINUTE", "NIGHT_END_HOUR", "NIGHT_END_MINUTE"],
            [x["key"] for x in time_section["settings"]],
        )
        soc = next(s for s in self._category("Leistungsgrenzen & SOC-Schutz")["sections"] if s["name"] == "SOC-Schutzfenster")
        self.assertEqual(["MIN_SOC_PERCENT", "MAX_SOC_PERCENT"], [x["key"] for x in soc["settings"]])
        harvest = self._category("Harvest / Restüberschuss")
        self.assertEqual("Master & Zielbild", harvest["sections"][0]["name"])
        profile = next(s for s in harvest["sections"] if s["name"] == "Tageszeitprofil")
        self.assertEqual(
            ["HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING", "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY", "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON"],
            [x["key"] for x in profile["settings"]],
        )
        mqtt = next(s for s in self._category("Schnittstellen & Datenquellen")["sections"] if s["name"] == "MQTT-Verbindung")
        self.assertEqual(["MQTT_BROKER", "MQTT_PORT", "MQTT_USER", "MQTT_PASSWORD"], [x["key"] for x in mqtt["settings"]])

    def test_harvest_raw_key_labels_have_human_labels(self):
        for key in (
            "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS",
            "HARVEST_HIGH_SMA_SOC_HOLD_SECONDS",
            "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO",
            "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING",
        ):
            self.assertNotEqual(key, self._setting(key)["label"])

    def test_client_validation_is_immediate_on_field_change_and_inline(self):
        self.assertIn("clearValidationIssuesForKeys", SETTINGS_JS)
        self.assertIn("validateSingleSetting(s, value, el.value).forEach(addValidationIssue)", SETTINGS_JS)
        self.assertIn("TIME_FORMAT_INVALID", SETTINGS_JS)
        self.assertIn("field-issues", SETTINGS_JS)
        self.assertIn(".field-issue.error", SETTINGS_CSS)
        self.assertIn("aria-invalid", SETTINGS_JS)

    def test_blocked_preview_has_visibly_disabled_save_button(self):
        self.assertIn("Speichern nicht möglich", SETTINGS_JS)
        self.assertIn(".modal-actions button:disabled", SETTINGS_CSS)
        self.assertIn("cursor:not-allowed", SETTINGS_CSS)

    def test_admin_actions_use_zec_modal_and_no_native_confirm(self):
        self.assertNotIn("confirm(", SETTINGS_JS)
        self.assertIn("openAdminModal", SETTINGS_JS)
        self.assertIn("Controller-Dienst neu starten", SETTINGS_JS)
        self.assertIn("Last-Good-Pointer reparieren", SETTINGS_JS)
        self.assertIn("Version · Build-ID · Ready-Status", SETTINGS_JS)
        self.assertIn("Config-Hash", SETTINGS_JS)
        self.assertIn("Manifest-Hash", SETTINGS_JS)
        self.assertIn("admin-confirm-grid", SETTINGS_CSS)

    def test_controller_interfaces_info_popover_is_structured(self):
        self.assertIn("infoStructured", STATUS_JS)
        self.assertIn("Aktueller Regelzyklus", STATUS_JS)
        self.assertIn("Statistik · jüngste Durchläufe", STATUS_JS)
        self.assertIn("Lokale Zendure-API", STATUS_JS)
        self.assertIn("Einordnung", STATUS_JS)
        self.assertIn("zec-info-grid", STATUS_JS)
        self.assertIn("width:min(560px", STATUS_CSS)
        self.assertIn(".zec-info-section", STATUS_CSS)
        self.assertIn(".zec-info-note", STATUS_CSS)


if __name__ == "__main__":
    unittest.main()
