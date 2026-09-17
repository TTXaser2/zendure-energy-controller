import json
import os
import socket
import tempfile
import unittest
from pathlib import Path

from config_manager import ConfigManager
from settings_service import SettingsService
from tools import deployment_contract as dc
from tools.zec_support_bundle import redact_mapping

ROOT = Path(__file__).resolve().parents[1]


class TestV1600DeploymentContract(unittest.TestCase):
    def _artifact(self, root: Path, absolute: str, content: str = "x") -> Path:
        p = root / absolute.lstrip("/")
        p.parent.mkdir(parents=True, exist_ok=True)
        if absolute.endswith("/zendure-controller"):
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.write_text(content, encoding="utf-8")
        return p

    def test_clean_supported_and_partial_states_share_one_classifier(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clean = dc.classify_installation(root=str(root), check_active_units=False)
            self.assertEqual(dc.STATE_CLEAN_FRESH_INSTALL, clean["state"])

            target = self._artifact(root, "/opt/zendure-controller")
            (target / "version.py").write_text(
                'APP_VERSION="15.0.3"\nAPP_BUILD_ID="v15.0.3-20260911"\n', encoding="utf-8"
            )
            (target / "config.json").write_text("{}\n", encoding="utf-8")
            self._artifact(root, "/etc/systemd/system/zendure-controller.service")
            self._artifact(root, "/usr/local/sbin/zendure-controller-restart")
            self._artifact(root, "/etc/sudoers.d/zendure-controller")
            supported = dc.classify_installation(
                root=str(root), expected_update_version="15.0.3",
                expected_update_build="v15.0.3-20260911", check_active_units=False,
            )
            self.assertEqual(dc.STATE_SUPPORTED_UPDATE, supported["state"])

            (target / "config.json").unlink()
            partial = dc.classify_installation(
                root=str(root), expected_update_version="15.0.3",
                expected_update_build="v15.0.3-20260911", check_active_units=False,
            )
            self.assertEqual(dc.STATE_AMBIGUOUS, partial["state"])

    def test_bootstrap_is_allowlisted_and_web_port_range_is_unprivileged(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / dc.BOOTSTRAP_NAME
            dc.write_bootstrap(path, 8123)
            self.assertEqual({"WEB_PORT": 8123}, dc.load_bootstrap(path))
            with self.assertRaises(ValueError):
                dc.validate_web_port(80)
            with self.assertRaises(ValueError):
                dc.validate_web_port(65536)
            path.write_text(json.dumps({"format": dc.BOOTSTRAP_FORMAT, "values": {"WEB_PORT": 8123, "X": 1}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                dc.load_bootstrap(path)

    def test_first_install_bootstrap_visible_and_control_stays_off_until_restart(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.json"
            dc.write_bootstrap(Path(td) / dc.BOOTSTRAP_NAME, 8123)
            manager = ConfigManager(str(path)); manager.load()
            self.assertEqual("FIRST_INSTALL_SETUP", manager.status()["startup_mode"])
            self.assertEqual(8123, manager.get()["WEB_PORT"])
            self.assertEqual(8123, manager.get_configured()["WEB_PORT"])
            self.assertFalse(manager.control_allowed())
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
            service.commit({"preview_id":preview["preview_id"],"confirmations":preview["confirmations_required"]}, "s")
            self.assertFalse((Path(td) / dc.BOOTSTRAP_NAME).exists())
            self.assertFalse(manager.control_allowed())
            self.assertTrue(manager.status()["first_install_restart_required"])
            saved=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(8123, saved["WEB_PORT"])
            manager2=ConfigManager(str(path)); manager2.load()
            self.assertEqual("NORMAL",manager2.status()["startup_mode"])
            self.assertTrue(manager2.control_allowed())
            self.assertEqual(8123, manager2.get()["WEB_PORT"])

    def test_changed_web_port_conflict_blocks_settings_preview(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"config.json"
            base={
                "DEVICE_ID":"TESTDEVICE", "MQTT_BROKER":"127.0.0.1", "GRID_METER_SOURCE":"shelly_http",
                "SHELLY_IP":"127.0.0.1", "MAX_CHARGE_POWER_W":1800, "MAX_DISCHARGE_POWER_W":1700,
                "MIN_SOC_PERCENT":15, "MAX_SOC_PERCENT":95, "WEB_PORT":8080,
            }
            # Use the normal parser to inherit remaining defaults without materializing them in the file.
            path.write_text(json.dumps(base)+"\n",encoding="utf-8")
            manager=ConfigManager(str(path)); manager.load(); service=SettingsService(manager)
            sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM); sock.bind(("127.0.0.1",0)); sock.listen(1)
            port=sock.getsockname()[1]
            try:
                preview=service.preview({"base_revision":manager.cas_revision(),"changes":{"WEB_PORT":{"op":"set","value":port}},"secrets":{}},"s",{})
                self.assertEqual("blocked",preview["status"])
                self.assertTrue(any(i["code"]=="VAL-027" for i in preview["issues"]),preview["issues"])
            finally:
                sock.close()

    def test_support_redaction_never_exposes_secret_value(self):
        redacted=redact_mapping({"MQTT_PASSWORD":"supersecret","MQTT_BROKER":"broker","ACCESS_TOKEN":"abc"})
        self.assertEqual({"secret_set":True},redacted["MQTT_PASSWORD"])
        self.assertEqual({"secret_set":True},redacted["ACCESS_TOKEN"])
        self.assertEqual("broker",redacted["MQTT_BROKER"])
        self.assertNotIn("supersecret",json.dumps(redacted))

    def test_installer_uninstaller_and_systemd_contracts(self):
        installer=(ROOT/"tools/install_zendure_controller.sh").read_text(encoding="utf-8")
        wrapper=(ROOT/"tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        uninstaller=(ROOT/"tools/uninstall_zendure_controller.sh").read_text(encoding="utf-8")
        unit=(ROOT/"systemd/zendure-controller.service").read_text(encoding="utf-8")
        self.assertIn("--preflight-only",installer)
        self.assertIn("--fresh-install",installer)
        self.assertIn("--web-port",installer)
        self.assertIn("CLEAN_FRESH_INSTALL",installer)
        self.assertIn("PRODUCTIVE_CHANGES=NONE",installer)
        self.assertIn("install_zendure_controller.sh",wrapper)
        self.assertIn("--fresh-install-reset",uninstaller)
        self.assertIn("--no-user-data-backup",uninstaller)
        self.assertIn("--include-measurement-data",uninstaller)
        self.assertIn("CLEAN_FRESH_INSTALL_STATE=yes",uninstaller)
        self.assertNotIn("mosquitto.service",unit)


if __name__ == "__main__":
    unittest.main()
