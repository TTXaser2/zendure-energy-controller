import json
import unittest
from pathlib import Path

from config_manager import DEFAULT_CONFIG, CONFIG_SCHEMA
from config_validator import validate_config_semantics
from sma_energy_meter import normalize_socket_mode, SmaEnergyMeterSnapshot
from state import ControllerState


class Rc6GroupBindDefaultTests(unittest.TestCase):
    def test_defaults_are_group_bind(self):
        cfg = json.loads(Path("config.example.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["SMA_ENERGY_METER_SOCKET_MODE"], "group_bind")
        self.assertEqual(DEFAULT_CONFIG["SMA_ENERGY_METER_SOCKET_MODE"], "group_bind")
        self.assertEqual(normalize_socket_mode(None), "group_bind")
        self.assertEqual(normalize_socket_mode("auto"), "group_bind")
        self.assertEqual(normalize_socket_mode("invalid"), "group_bind")
        self.assertEqual(SmaEnergyMeterSnapshot().configured_socket_mode, "group_bind")
        self.assertEqual(ControllerState().sma_energy_meter_socket_mode, "group_bind")

    def test_schema_marks_group_bind_as_recommended(self):
        setting = CONFIG_SCHEMA["SMA_ENERGY_METER_SOCKET_MODE"]
        self.assertIn("group_bind", setting["options"])
        self.assertIn("Empfohlen", setting["options"]["group_bind"])
        self.assertIn("EVCC", setting["description"])
        self.assertIn("Wildcard", setting["description"])

    def test_validator_warns_about_group_bind_and_wildcard_risk(self):
        cfg = {
            "GRID_METER_SOURCE": "sma_energy_meter_udp",
            "SMA_ENERGY_METER_GROUP": "239.12.255.254",
            "SMA_ENERGY_METER_PORT": 9522,
            "SMA_ENERGY_METER_SERIAL": "3011954105",
            "SMA_ENERGY_METER_SOCKET_MODE": "group_bind",
            "MQTT_BROKER": "127.0.0.1",
            "DEVICE_ID": "dev",
        }
        texts = "\n".join(i.message for i in validate_config_semantics(cfg))
        self.assertIn("group_bind", texts)
        self.assertIn("Wildcard", texts)


class Rc6DiagnosticPackageTests(unittest.TestCase):
    def test_export_summary_contains_socket_assessment(self):
        text = Path("tools/create_zec_analysis_package.sh").read_text(encoding="utf-8")
        self.assertIn("socket_assessment=OK_GROUP_BIND", text)
        self.assertIn("WILDCARD_BIND_RISK", text)
        self.assertIn("EVCC", text)


if __name__ == "__main__":
    unittest.main()
