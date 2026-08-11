import csv
import gzip
import json
import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config_manager import ConfigManager, DEFAULT_CONFIG
from settings_runtime import StableReadResult, sha256_bytes, stable_read as real_stable_read


class V13AtomicCommitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG); cfg["DEVICE_ID"] = "TESTDEVICE"
        self.path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        os.chmod(self.path, 0o600)
        self.manager = ConfigManager(str(self.path)); self.manager.load()

    def test_post_write_verify_failure_restores_exact_old_bytes_and_runtime(self):
        old_bytes = self.path.read_bytes()
        old_configured = self.manager.get_configured()
        candidate = self.manager.candidate_base_config(); candidate["DEADBAND_W"] = 91
        calls = {"n": 0}

        def fake_stable(path):
            calls["n"] += 1
            if calls["n"] == 2:
                bad = b"post-write-readback-mismatch"
                return StableReadResult("ok", bad, None, sha256_bytes(bad), None)
            return real_stable_read(path)

        with patch("settings_runtime.stable_read", side_effect=fake_stable):
            with self.assertRaisesRegex(RuntimeError, "CONFIG_POST_WRITE_VERIFY_FAILED"):
                self.manager.commit_candidate(candidate, self.manager.configured_revision())
        self.assertEqual(old_bytes, self.path.read_bytes())
        self.assertEqual(old_configured, self.manager.get_configured())
        self.assertTrue(self.manager.status()["primary_config_valid"])

    def test_rollback_verification_failure_fails_closed(self):
        candidate = self.manager.candidate_base_config(); candidate["DEADBAND_W"] = 92
        calls = {"n": 0}

        def fake_stable(path):
            calls["n"] += 1
            if calls["n"] in (2, 3):
                bad = ("bad-%d" % calls["n"]).encode()
                return StableReadResult("ok", bad, None, sha256_bytes(bad), None)
            return real_stable_read(path)

        with patch("settings_runtime.stable_read", side_effect=fake_stable):
            with self.assertRaisesRegex(RuntimeError, "CONFIG_COMMIT_ROLLBACK_FAILED"):
                self.manager.commit_candidate(candidate, self.manager.configured_revision())
        status = self.manager.status()
        self.assertFalse(status["primary_config_valid"])
        self.assertEqual("invalid_runtime", status["config_health"])


class V13BackfillToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "measurements.sqlite3"
        self.cfg = dict(DEFAULT_CONFIG)
        self.cfg.update({
            "DEVICE_ID": "TESTDEVICE",
            "MEASUREMENT_DB_ENABLED": True,
            "MEASUREMENT_DB_PATH": str(self.db),
            "MEASUREMENT_LOG_DIR": str(self.root),
            "MEASUREMENT_LOG_FALLBACK_DIR": str(self.root),
        })
        self.config_path = self.root / "config.json"
        self.config_path.write_text(json.dumps(self.cfg), encoding="utf-8")
        self.script = Path(__file__).resolve().parents[1] / "tools" / "backfill_graph_config_timeline.py"

    def _write_v4(self, path, rows, gz=False):
        opener = gzip.open if gz else open
        kwargs = {"mode": "wt", "encoding": "utf-8", "newline": ""} if gz else {"mode": "w", "encoding": "utf-8", "newline": ""}
        with opener(path, **kwargs) as handle:
            writer = csv.DictWriter(handle, fieldnames=["measurement_epoch_ms", "config_control_hash"], delimiter=";")
            writer.writeheader(); writer.writerows(rows)

    def test_backfill_is_v4_only_idempotent_and_unknown_snapshot_safe(self):
        self._write_v4(self.root / "zec_measurements_v4.csv", [
            {"measurement_epoch_ms": 1000, "config_control_hash": "a"},
            {"measurement_epoch_ms": 2000, "config_control_hash": "a"},
            {"measurement_epoch_ms": 3000, "config_control_hash": "missing"},
        ])
        # V3-like file lacks config_control_hash and must be ignored.
        (self.root / "historical_v3.csv").write_text("measurement_epoch_ms;value\n1500;1\n", encoding="utf-8")
        snapshots = {"snapshots": [{"config_control_hash": "a", "control_parameters": {
            "MIN_SOC_PERCENT": 10, "MAX_SOC_PERCENT": 99, "NIGHT_DISCHARGE_STOP_SOC_PERCENT": 20,
            "NIGHT_START_HOUR": 21, "NIGHT_START_MINUTE": 30, "NIGHT_END_HOUR": 5, "NIGHT_END_MINUTE": 30,
        }}]}
        (self.root / "zec_config_snapshots.json").write_text(json.dumps(snapshots), encoding="utf-8")

        cmd = ["python3", str(self.script), "--config", str(self.config_path), "--db", str(self.db), "--measurement-dir", str(self.root)]
        first = subprocess.run(cmd, check=True, capture_output=True, text=True)
        second = subprocess.run(cmd, check=True, capture_output=True, text=True)
        f = json.loads(first.stdout); s = json.loads(second.stdout)
        self.assertEqual("ok", f["status"]); self.assertEqual("ok", s["status"])
        self.assertEqual(2, f["hash_transitions_seen"])
        self.assertEqual(1, f["unknown_snapshots"])
        self.assertEqual(0, s["entries_inserted"])
        conn = sqlite3.connect(self.db)
        rows = conn.execute("SELECT config_control_hash,known FROM graph_config_timeline ORDER BY effective_from_ms").fetchall()
        conn.close()
        self.assertEqual([("a", 1), ("missing", 0)], rows)

    def test_missing_config_is_safe_skip(self):
        result = subprocess.run(
            ["python3", str(self.script), "--config", str(self.root / "missing.json"), "--db", str(self.db)],
            check=True, capture_output=True, text=True,
        )
        self.assertEqual("skipped", json.loads(result.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
