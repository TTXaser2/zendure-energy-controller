import contextlib
import json
import os
import re
import zipfile
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import version
from config_artifacts import ConfigArtifactCoordinator
from config_bundle import build_bundle, encode_bundle, parse_bundle
from config_manager import ConfigManager, DEFAULT_CONFIG
from config_states import ConfigStateStore
from measurement_db import MeasurementDbWriter, extract_measurement_point
from settings_registry import SCHEMA_VERSION, SETTINGS, registry_contract_sha256
from settings_service import SettingsService

ROOT = Path(__file__).resolve().parents[1]
OLD_REGISTRY_HASH = "c1e13a7a1fd2968545bcf49073dc7b1d9e9dd7c71e0d002a45f50610d0780440"


class V1302ConfigArtifactHotfixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.config_path = Path(self.tmp.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg["DEVICE_ID"] = "TESTDEVICE"
        cfg["MQTT_PASSWORD"] = "secret"
        cfg["CROSS_CHARGE_ENABLED"] = True
        cfg["REST_SURPLUS_HARVEST_ENABLED"] = False
        cfg.pop("SECOND_BATTERY_INTEGRATION_ENABLED", None)
        self.config_path.write_text(json.dumps(cfg) + "\n", encoding="utf-8")
        os.chmod(self.config_path, 0o600)
        self.manager = ConfigManager(str(self.config_path)); self.manager.load()
        self.service = SettingsService(self.manager)
        self.store = ConfigStateStore(str(self.config_path))
        self.coordinator = ConfigArtifactCoordinator(self.manager, self.service, self.store)
        self.session = "v1302-session"

    def test_release_and_registry_contract_are_v13_0_2(self):
        self.assertEqual("13.0.2", version.APP_VERSION)
        self.assertEqual("V13.0.2", version.APP_VERSION_LABEL)
        self.assertEqual("v13.0.2-20260812", version.APP_BUILD_ID)
        self.assertEqual("1.25-v13.0", SCHEMA_VERSION)
        self.assertNotEqual(OLD_REGISTRY_HASH, registry_contract_sha256())

    def test_v13_0_1_registry_bundle_has_exact_display_only_compatibility(self):
        data = build_bundle(self.manager, artifact_kind="portable_profile", scope_mode="portable_profile")
        doc = json.loads(data)
        payload = dict(doc["payload"])
        payload["source"] = dict(payload["source"])
        payload["source"]["settings_registry_schema_version"] = "1.24-v13.0"
        payload["source"]["settings_registry_sha256"] = OLD_REGISTRY_HASH
        parsed = parse_bundle(encode_bundle(payload))
        self.assertEqual("compatible", parsed.compatibility["status"])
        self.assertIn("REGISTRY_DISPLAY_METADATA_V13_0_2", parsed.migration_steps)

    def test_arbitrary_registry_hash_still_fails_closed(self):
        data = build_bundle(self.manager, artifact_kind="export", scope_mode="full_managed")
        doc = json.loads(data); payload = dict(doc["payload"]); payload["source"] = dict(payload["source"])
        payload["source"]["settings_registry_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SETTINGS_REGISTRY_COMPATIBILITY_UNSUPPORTED"):
            parse_bundle(encode_bundle(payload))

    def test_named_state_with_portable_scope_remains_named_state(self):
        state = self.store.create(self.manager, name="Portable local", scope_mode="portable_profile")
        self.assertEqual("valid", state["status"])
        self.assertEqual("portable_profile", state["scope_mode"])
        self.assertEqual(55, state["scope_key_count"])
        bundle = parse_bundle(self.store.export_bytes(state["state_id"], expected_revision=state["state_revision"]))
        self.assertEqual("named_state", bundle.payload["artifact_kind"])
        self.assertEqual("portable_profile", bundle.scope["mode"])

    def test_corrupt_semantic_state_is_safe_deletable_with_revision_cas(self):
        self.store.ensure_root()
        state_id = "a" * 32
        # A valid portable exchange artifact is invalid as a local named state.
        data = build_bundle(self.manager, artifact_kind="portable_profile", scope_mode="portable_profile", name="broken local")
        path = Path(self.store.root) / f"{state_id}.zec-config.json"
        path.write_bytes(data); os.chmod(path, 0o600)
        listed = self.store.list()["items"]
        item = next(x for x in listed if x["state_id"] == state_id)
        self.assertEqual("corrupt", item["status"])
        self.assertTrue(item["safe_deletable"])
        with self.assertRaisesRegex(RuntimeError, "CONFIG_STATE_REVISION_CONFLICT"):
            self.store.delete(state_id, expected_revision="0" * 64)
        result = self.store.delete(state_id, expected_revision=item["state_revision"])
        self.assertEqual("deleted", result["status"])
        self.assertFalse(path.exists())

    def test_identical_state_has_no_false_derived_default_drift_and_no_commit_token(self):
        # The runtime derives SECOND_BATTERY_INTEGRATION_ENABLED=True from the
        # existing cross-charge/harvest settings even though the key is absent.
        self.assertTrue(self.manager.get_configured()["SECOND_BATTERY_INTEGRATION_ENABLED"])
        state = self.store.create(self.manager, name="same")
        preview = self.coordinator.preview_state(
            state["state_id"], state_revision=state["state_revision"],
            base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, expert=False,
        )
        self.assertEqual("no_changes", preview["status"])
        self.assertFalse(preview["commit_allowed"])
        self.assertIsNone(preview["preview_id"])
        self.assertFalse(any(x.get("code") == "INHERITED_DEFAULT_CHANGED" for x in preview.get("issues", [])))
        self.assertFalse(preview["diff"])

    def test_identical_import_is_noop_and_server_rejects_commit_without_preview(self):
        data = build_bundle(self.manager, artifact_kind="portable_profile", scope_mode="portable_profile")
        inspected = self.coordinator.inspect_bundle(data, session_token=self.session)
        preview = self.coordinator.preview_import(
            inspected["import_token"], base_revision=self.manager.cas_revision(),
            session_token=self.session, state_snapshot={}, expert=False,
        )
        self.assertEqual("no_changes", preview["status"])
        self.assertIsNone(preview["preview_id"])
        with self.assertRaisesRegex(PermissionError, "PREVIEW_NOT_COMMITTABLE"):
            self.service.commit({"preview_id": None, "confirmations": []}, self.session)


class V1302MeasurementWriterTests(unittest.TestCase):
    def _config(self, path):
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({"MEASUREMENT_DB_ENABLED": True, "MEASUREMENT_DB_PATH": str(path), "DEVICE_ID": "TESTDEVICE"})
        return cfg

    def _row(self, ts=1786500000000):
        return {
            "measurement_epoch_ms": str(ts),
            "operating_mode": "AUTO",
            "zendure_soc_percent": "50",
            "grid_power_valid": "1",
            "config_control_hash": "hash-a",
        }

    def test_failed_flush_batch_is_retried_with_fresh_connection_and_not_lost(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "measurements.sqlite3"
            writer = MeasurementDbWriter()
            real_write = __import__("measurement_db").write_points
            calls = {"n": 0}

            def flaky(conn, points):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise sqlite3.OperationalError("database is locked")
                return real_write(conn, points)

            try:
                with patch("measurement_db.write_points", side_effect=flaky):
                    writer.enqueue(self._config(db), self._row())
                    deadline = time.time() + 5
                    saw_error = False
                    while time.time() < deadline:
                        st = writer.status()
                        saw_error = saw_error or st.get("measurement_db_consecutive_failures", 0) > 0 or bool(st.get("measurement_db_last_error"))
                        if st.get("measurement_db_rows_written") == 1:
                            break
                        time.sleep(0.05)
                    st = writer.status()
                self.assertGreaterEqual(calls["n"], 2)
                self.assertTrue(saw_error)
                self.assertEqual(1, st["measurement_db_rows_written"])
                self.assertEqual(0, st["measurement_db_rows_dropped"])
                self.assertEqual(0, st["measurement_db_consecutive_failures"])
                self.assertIn("database is locked", st["measurement_db_last_error"])
                conn = sqlite3.connect(db)
                count = conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0]
                conn.close()
                self.assertEqual(1, count)
            finally:
                writer.close()

    def test_enqueue_does_not_erase_active_error_and_stale_is_visible(self):
        writer = MeasurementDbWriter()
        try:
            with writer._lock:
                writer._last_status.update({
                    "measurement_db_status": "error",
                    "measurement_db_reason": "locked",
                    "measurement_db_error": "locked",
                    "measurement_db_last_error": "locked",
                    "measurement_db_last_error_epoch_s": 100.0,
                    "measurement_db_consecutive_failures": 1,
                    "measurement_db_first_enqueue_epoch_s": 100.0,
                    "measurement_db_last_enqueue_epoch_s": 230.0,
                    "measurement_db_last_success_epoch_s": "",
                })
            with patch("measurement_db.time.time", return_value=230.0):
                st = writer.status()
            self.assertEqual("error", st["measurement_db_status"])
            self.assertEqual("locked", st["measurement_db_error"])
            self.assertEqual("locked", st["measurement_db_last_error"])
            self.assertTrue(st["measurement_db_write_stale"])
        finally:
            writer.close()


class V1302BackfillAndUiContractTests(unittest.TestCase):
    def test_backfill_reports_and_strips_nul_instead_of_silently_skipping(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); db = root / "m.sqlite3"; cfg = dict(DEFAULT_CONFIG)
            cfg.update({
                "DEVICE_ID":"TESTDEVICE", "MEASUREMENT_DB_ENABLED":True,
                "MEASUREMENT_DB_PATH":str(db), "MEASUREMENT_LOG_DIR":str(root),
                "MEASUREMENT_LOG_FALLBACK_DIR":str(root),
            })
            (root/"config.json").write_text(json.dumps(cfg), encoding="utf-8")
            (root/"zec_config_snapshots.json").write_text(json.dumps({"snapshots":[{"config_control_hash":"a","control_parameters":{
                "MIN_SOC_PERCENT":10,"MAX_SOC_PERCENT":99,"NIGHT_DISCHARGE_STOP_SOC_PERCENT":20,
                "NIGHT_START_HOUR":21,"NIGHT_START_MINUTE":30,"NIGHT_END_HOUR":5,"NIGHT_END_MINUTE":30,
            }}]}), encoding="utf-8")
            (root/"zec_measurements_v4.csv").write_bytes(b"measurement_epoch_ms;config_control_hash\n1000;a\x00\n")
            script=ROOT/"tools"/"backfill_graph_config_timeline.py"
            result=subprocess.run(["python3",str(script),"--config",str(root/"config.json"),"--db",str(db),"--measurement-dir",str(root)],check=True,capture_output=True,text=True)
            doc=json.loads(result.stdout)
            self.assertEqual("ok",doc["status"])
            self.assertEqual(1,doc["nul_characters_removed"])
            self.assertEqual(0,doc["read_error_files"])
            self.assertEqual(1,doc["v4_rows_seen"])

    def test_graph_legend_uses_adjacent_not_global_deduplication(self):
        js=(ROOT/"static"/"status_v2.js").read_text(encoding="utf-8")
        self.assertIn("adjacentValues", js)
        self.assertNotIn("[...new Set(segments.map(s=>s[key])", js)
        self.assertNotIn("[...new Set(segments.map(s=>`${s.night_start}", js)

    def test_config_modal_csrf_and_modal_stack_contract_is_present(self):
        js=(ROOT/"static"/"settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("app.model?.csrf_token || $('meta[name=\"zec-csrf\"]')?.content", js)
        self.assertIn("refreshCsrfToken", js)
        self.assertIn("fetchWithCsrfRetry(url,opt,false)", js)
        self.assertIn("previewReturnToConfigStates", js)
        self.assertIn("modal-child", js)
        self.assertIn("setConfigStatesBanner('error'", js)
        self.assertIn("Verteilbares Regelprofil exportieren", js)
        self.assertNotIn("Teilbares Regelprofil", js)

    def test_user_visible_known_historical_release_phrases_are_removed(self):
        files=[ROOT/"config_manager.py",ROOT/"settings_help.py",ROOT/"web_ui.py",ROOT/"static"/"settings_v2.js",ROOT/"static"/"status_v2.js"]
        text="\n".join(p.read_text(encoding="utf-8") for p in files)
        for phrase in (
            "Standard in V12.11.2-RC1 ist",
            "Seit RC18 blockiert die lokale API",
            "Dient der RC3-Timingdiagnose",
            "In V12.13.0 ein fester",
            "Diagnose: RC3-kompatibel",
        ):
            self.assertNotIn(phrase,text)

    def test_registry_user_visible_metadata_has_no_historical_release_references(self):
        pattern = re.compile(r"\b(?:RC\d+|V(?:12|13)\.\d+(?:\.\d+)?)\b", re.I)
        offenders = []
        for spec in SETTINGS:
            visible = [
                spec.label, spec.apply_text, spec.validation_text, spec.default_help,
                spec.dependency_text, spec.release_text,
            ]
            visible.extend(label for _, label in spec.options)
            help_spec = spec.help
            visible.extend([
                help_spec.short_help, help_spec.extended_help, help_spec.when_help,
                help_spec.effect_increase, help_spec.effect_decrease,
                help_spec.effect_enable, help_spec.effect_disable,
                help_spec.dependency_help, help_spec.override_help,
                help_spec.risk_help, help_spec.formula_text,
            ])
            visible.extend(text for _, text in help_spec.option_help)
            visible.extend(help_spec.evidence_refs)
            for text in visible:
                if isinstance(text, str) and pattern.search(text):
                    offenders.append((spec.key, text))
        self.assertEqual([], offenders)

    def test_current_manual_is_v13_0_2_and_has_no_unnecessary_historical_release_copy(self):
        manual = ROOT / "docs" / "Zendure_Energy_Controller_Handbuch.docx"
        with zipfile.ZipFile(manual) as archive:
            parts = [archive.read("word/document.xml").decode("utf-8")]
            parts.extend(archive.read(name).decode("utf-8") for name in archive.namelist() if name.startswith("word/footer") and name.endswith(".xml"))
        xml = "\n".join(parts)
        self.assertIn("Benutzerhandbuch V13.0.2", xml)
        self.assertNotIn("V13.0.0", xml)
        self.assertNotIn("V12.6", xml)
        self.assertNotRegex(xml, r"\bRC\d+\b")
        self.assertIsNone(re.search(r"(?<!ver)\bteilbares Regelprofil\b", xml, re.I))
        self.assertIn("verteilbares Regelprofil", xml)

    def test_installer_is_strict_v13_0_1_to_v13_0_2(self):
        script=(ROOT/"tools"/"update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION="v13_0_2"',script)
        self.assertIn('EXPECTED_SOURCE_VERSION="13.0.1"',script)
        self.assertIn('EXPECTED_SOURCE_BUILD_ID="v13.0.1-20260811"',script)
        self.assertIn('EXPECTED_TARGET_VERSION="13.0.2"',script)
        self.assertIn('EXPECTED_TARGET_BUILD_ID="v13.0.2-20260812"',script)
        self.assertIn('V13_0_2_SOURCE_MANIFEST.sha256',script)


if __name__ == '__main__':
    unittest.main()
