import csv
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path

# The CI/container used for ZIP assembly does not need a real MQTT broker client.
# Provide a tiny import stub before importing controller_logic.
sys.modules.setdefault("paho", types.ModuleType("paho"))
sys.modules.setdefault("paho.mqtt", types.ModuleType("paho.mqtt"))
fake_mqtt_client = types.ModuleType("paho.mqtt.client")
fake_mqtt_client.Client = object
sys.modules.setdefault("paho.mqtt.client", fake_mqtt_client)

from controller_logic import ZendureController
from csv_logger import CsvRotatingLogger
from state import ControllerState
from tests.test_measurement_v4_writer import base_config, base_row


class FakeMqtt:
    def __init__(self):
        self.calls = []
    def set_ac_mode(self, mode):
        self.calls.append(("ac_mode", mode, False))
    def set_input_limit(self, watts, force=False):
        self.calls.append(("input", int(watts), bool(force)))
    def set_output_limit(self, watts, force=False):
        self.calls.append(("output", int(watts), bool(force)))


class V12100Rc8IsolatedFixTests(unittest.TestCase):
    def test_v4_logger_always_uses_physical_session_file_matching_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = base_config(tmp)
            logger = CsvRotatingLogger()
            try:
                logger.log(cfg, base_row())
                logger.log(cfg, {**base_row(), "cycle_id": 43, "epoch_s": 1780000003.0})
            finally:
                logger.close()

            csv_files = sorted(name for name in os.listdir(tmp) if name.startswith("zendure_measurements_v4") and name.endswith(".csv"))
            self.assertEqual(1, len(csv_files), csv_files)
            self.assertRegex(csv_files[0], r"^zendure_measurements_v4_\d{8}T\d{6}Z\.csv$")
            self.assertNotEqual("zendure_measurements_v4.csv", csv_files[0])
            with open(os.path.join(tmp, "zec_measurement_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(csv_files[0], manifest["files"][0]["relative_path"])
            self.assertTrue(os.path.exists(os.path.join(tmp, manifest["files"][0]["relative_path"])))
            with open(os.path.join(tmp, csv_files[0]), newline="", encoding="utf-8") as f:
                self.assertEqual(2, len(list(csv.DictReader(f, delimiter=";"))))

    def test_deadband_after_startup_sends_one_forced_neutral_command(self):
        state = ControllerState()
        fake_mqtt = FakeMqtt()
        controller = ZendureController(None, state, fake_mqtt, None, None, None)
        cfg = {"CROSS_CHARGE_ENABLED": False}

        controller.handle_deadband(cfg)
        self.assertIn(("input", 0, True), fake_mqtt.calls)
        self.assertIn(("output", 0, True), fake_mqtt.calls)
        self.assertEqual("GRID -> DEADBAND -> STARTUP_NEUTRALIZE -> HOLD_POWER", state.technical_control_path)

        fake_mqtt.calls.clear()
        controller.handle_deadband(cfg)
        self.assertEqual([], fake_mqtt.calls)
        self.assertEqual("GRID -> DEADBAND -> HOLD_POWER", state.technical_control_path)

    def test_package_tool_default_is_no_stop_and_can_create_fallback_only_package(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "tools" / "create_zec_analysis_package.sh"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            primary = base / "primary"
            fallback = base / "fallback"
            runtime = base / "runtime"
            out = base / "out"
            primary.mkdir(); fallback.mkdir(); runtime.mkdir(); out.mkdir()
            (primary / "zendure_measurements_v4.csv").write_text("", encoding="utf-8")
            csv_path = fallback / "zendure_measurements_v4_20260626T000000Z.csv"
            csv_path.write_text("schema_version\n4\n", encoding="utf-8")
            (fallback / "zec_measurement_manifest.json").write_text(json.dumps({
                "schema_version": 4,
                "files": [{"relative_path": csv_path.name, "row_count": 1}],
            }), encoding="utf-8")
            (fallback / "zec_config_snapshots.json").write_text(json.dumps({"schema_version": 4, "snapshots": []}), encoding="utf-8")
            (fallback / "zec_runtime_events.jsonl").write_text("{}\n", encoding="utf-8")
            (runtime / "zendure_runtime.log").write_text("runtime\n", encoding="utf-8")

            result = subprocess.run([
                "bash", str(script),
                "--measurement-dir", str(primary),
                "--fallback-dir", str(fallback),
                "--runtime-dir", str(runtime),
                "--install-dir", str(repo),
                "--output-dir", str(out),
                "--name", "pkg",
            ], text=True, capture_output=True, check=True)
            self.assertIn("without stopping services", result.stdout)
            self.assertIn("fallback-only", result.stderr)
            zip_path = out / "pkg.zip"
            self.assertTrue(zip_path.exists())
            with zipfile.ZipFile(zip_path) as zf:
                names = set(zf.namelist())
            self.assertIn("pkg/fallback_logs/" + csv_path.name, names)
            self.assertIn("pkg/PACKAGE_INFO.txt", names)


if __name__ == "__main__":
    unittest.main()
