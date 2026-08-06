import json
import tempfile
import unittest
from pathlib import Path

from config_manager import ConfigManager, DEFAULT_CONFIG
from settings_service import SettingsService


class Rc20SettingsServiceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg["DEVICE_ID"] = "TESTDEVICE"
        cfg["MQTT_PASSWORD"] = "existing-secret"
        cfg["CUSTOM_UNKNOWN"] = "keep-me"
        self.path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        self.manager = ConfigManager(str(self.path))
        self.manager.load()
        self.service = SettingsService(self.manager)
        self.session = "session-token"

    def preview(self, changes=None, secrets=None):
        return self.service.preview({
            "base_revision": self.manager.cas_revision(),
            "changes": changes or {},
            "secrets": secrets or {},
        }, self.session, {})

    def test_preview_is_side_effect_free(self):
        before = self.path.read_bytes()
        result = self.preview({"DEADBAND_W": {"op": "set", "value": 90}})
        self.assertEqual("ready", result["status"])
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(80, self.manager.get()["DEADBAND_W"])

    def test_commit_is_one_time_and_preserves_unknown_and_secret_keep(self):
        preview = self.preview({"DEADBAND_W": {"op": "set", "value": 90}}, {"MQTT_PASSWORD": {"op": "keep"}})
        result = self.service.commit({"preview_id": preview["preview_id"], "confirmations": preview["confirmations_required"]}, self.session)
        self.assertEqual("committed", result["status"])
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual("keep-me", saved["CUSTOM_UNKNOWN"])
        self.assertEqual("existing-secret", saved["MQTT_PASSWORD"])
        with self.assertRaises(KeyError):
            self.service.commit({"preview_id": preview["preview_id"]}, self.session)

    def test_secret_replace_and_clear_are_explicit(self):
        preview = self.preview(secrets={"MQTT_PASSWORD": {"op": "replace", "value": "new-secret"}})
        self.service.commit({"preview_id": preview["preview_id"], "confirmations": preview["confirmations_required"]}, self.session)
        self.assertEqual("new-secret", json.loads(self.path.read_text(encoding="utf-8"))["MQTT_PASSWORD"])
        preview = self.preview(secrets={"MQTT_PASSWORD": {"op": "clear"}})
        self.service.commit({"preview_id": preview["preview_id"], "confirmations": preview["confirmations_required"]}, self.session)
        self.assertEqual("", json.loads(self.path.read_text(encoding="utf-8"))["MQTT_PASSWORD"])

    def test_secret_values_never_appear_in_preview_json(self):
        result = self.preview(secrets={"MQTT_PASSWORD": {"op": "replace", "value": "never-render-me"}})
        self.assertNotIn("never-render-me", json.dumps(result))
        self.assertTrue(any(item["key"] == "MQTT_PASSWORD" and item["secret"] for item in result["diff"]))

    def test_secret_cannot_bypass_explicit_secret_channel(self):
        result = self.preview({"MQTT_PASSWORD": {"op": "set", "value": "bypass"}})
        self.assertEqual("blocked", result["status"])
        self.assertTrue(any(issue["code"] == "SECRET_OPERATION_INVALID" for issue in result["issues"]))
        self.assertNotIn("bypass", json.dumps(result))

    def test_unknown_key_cannot_be_modified_through_patch(self):
        result = self.preview({"CUSTOM_UNKNOWN": {"op": "set", "value": "changed"}})
        self.assertEqual("blocked", result["status"])
        self.assertTrue(any(issue["code"] == "PATCH_UNKNOWN_KEY" for issue in result["issues"]))

    def test_migration_only_restart_command_cannot_be_set(self):
        result = self.preview({"SERVICE_RESTART_COMMAND": {"op": "set", "value": "rm -rf /"}})
        self.assertEqual("blocked", result["status"])
        self.assertTrue(any(issue["code"] == "PATCH_KEY_NOT_EDITABLE" for issue in result["issues"]))

    def test_old_preview_conflicts_after_external_format_only_change(self):
        preview = self.preview({"DEADBAND_W": {"op": "set", "value": 90}})
        cfg = json.loads(self.path.read_text(encoding="utf-8"))
        self.path.write_text(json.dumps(cfg, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "CONFIG_REVISION_CONFLICT"):
            self.service.commit({"preview_id": preview["preview_id"], "confirmations": preview["confirmations_required"]}, self.session)

    def test_restart_key_remains_pending_after_commit(self):
        result = self.preview({"WEB_PORT": {"op": "set", "value": 8081}})
        committed = self.service.commit({"preview_id": result["preview_id"], "confirmations": result["confirmations_required"]}, self.session)
        self.assertTrue(committed["pending_restart"])
        self.assertIn("WEB_PORT", committed["restart_required_keys"])
        self.assertEqual(8080, self.manager.get()["WEB_PORT"])


if __name__ == "__main__":
    unittest.main()
