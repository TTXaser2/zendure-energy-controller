import csv
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from csv_logger import CsvRotatingLogger, compute_config_control_hash
from measurement_v4 import ConfigSnapshotStore, MeasurementV4Logger, build_config_snapshot
from measurement_v4_contract import STANDARD_HEADER
from tests.test_measurement_v4_writer import base_config, base_row
from zendure_local_api import ZendureLocalApiClient


class MeasurementV4Rc3Tests(unittest.TestCase):
    def test_logging_off_hard_bypasses_v4_path_resolution(self):
        logger = MeasurementV4Logger()
        with patch("measurement_v4.resolve_log_target", side_effect=AssertionError("must not resolve target when logging is off")):
            status = logger.log({"MEASUREMENT_LOG_MODE": "off", "MEASUREMENT_SCHEMA_VERSION": "4"}, {})
        self.assertEqual("disabled", status["measurement_log_status"])
        self.assertEqual("MEASUREMENT_LOG_MODE=off", status["measurement_log_status_reason"])

    def test_existing_default_v4_file_gets_new_session_file_not_second_manifest_entry_same_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_path = os.path.join(tmp, "zendure_measurements_v4.csv")
            with open(base_path, "w", encoding="utf-8", newline="") as f:
                f.write(";".join(STANDARD_HEADER) + "\n")
                f.write(";".join(["4"] + [""] * (len(STANDARD_HEADER) - 1)) + "\n")
            logger = CsvRotatingLogger()
            logger.log(base_config(tmp), base_row())
            logger.close()
            files = sorted(name for name in os.listdir(tmp) if name.startswith("zendure_measurements_v4") and name.endswith(".csv"))
            self.assertEqual(2, len(files))
            self.assertIn("zendure_measurements_v4.csv", files)
            new_files = [name for name in files if name != "zendure_measurements_v4.csv"]
            self.assertEqual(1, len(new_files))
            with open(os.path.join(tmp, new_files[0]), newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(1, len(rows))
            with open(os.path.join(tmp, "zec_measurement_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual([new_files[0]], [entry["relative_path"] for entry in manifest["files"]])
            self.assertEqual(1, manifest["files"][0]["row_count"])

    def test_existing_snapshot_is_backfilled_with_cross_charge_significant_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = base_config(tmp)
            cfg.pop("CROSS_CHARGE_SIGNIFICANT_W", None)
            cfg["SMA_DISCHARGE_BLOCK_W"] = 80
            old_snapshot = build_config_snapshot(cfg)
            old_snapshot["control_parameters"].pop("CROSS_CHARGE_SIGNIFICANT_W", None)
            path = os.path.join(tmp, "zec_config_snapshots.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"schema_version": 4, "snapshots": [old_snapshot]}, f)
            store = ConfigSnapshotStore()
            self.assertEqual(compute_config_control_hash(cfg), store.ensure_snapshot(tmp, cfg))
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            params = data["snapshots"][0]["control_parameters"]
            self.assertEqual(80, params["CROSS_CHARGE_SIGNIFICANT_W"])

    def test_local_api_timeout_is_capped_for_control_loop(self):
        client = ZendureLocalApiClient()
        captured = {}

        class Response:
            def raise_for_status(self):
                return None
            def json(self):
                return {"properties": {}, "packData": []}

        def fake_get(url, timeout):
            captured["timeout"] = timeout
            return Response()

        client.session.get = fake_get
        client.fetch_report({
            "ZENDURE_LOCAL_IP": "192.0.2.10",
            "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": 5,
            "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": 1.5,
        })
        self.assertEqual(1.5, captured["timeout"])


if __name__ == "__main__":
    unittest.main()
