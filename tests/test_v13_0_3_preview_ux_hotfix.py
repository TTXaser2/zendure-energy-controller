import json
import os
import tempfile
import unittest
from pathlib import Path

import version
from config_artifacts import ConfigArtifactCoordinator
from config_bundle import build_bundle, encode_bundle, parse_bundle
from config_manager import ConfigManager, DEFAULT_CONFIG
from config_states import ConfigStateStore
from settings_service import SettingsService

ROOT = Path(__file__).resolve().parents[1]
OLD_REGISTRY_HASH = "c1e13a7a1fd2968545bcf49073dc7b1d9e9dd7c71e0d002a45f50610d0780440"
TECHNICAL_STEP = "REGISTRY_DISPLAY_METADATA_V13_0_2"


def as_v13_0_1_bundle(data: bytes) -> bytes:
    doc = json.loads(data)
    payload = dict(doc["payload"])
    source = dict(payload["source"])
    source.update({
        "app_version": "13.0.1",
        "app_build_id": "v13.0.1-20260811",
        "settings_registry_schema_version": "1.24-v13.0",
        "settings_registry_sha256": OLD_REGISTRY_HASH,
    })
    payload["source"] = source
    return encode_bundle(payload)


class V1303PreviewUxHotfixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg["DEVICE_ID"] = "TESTDEVICE"
        cfg["MQTT_PASSWORD"] = "secret"
        self.path.write_text(json.dumps(cfg) + "\n", encoding="utf-8")
        os.chmod(self.path, 0o600)
        self.manager = ConfigManager(str(self.path)); self.manager.load()
        self.service = SettingsService(self.manager)
        self.store = ConfigStateStore(str(self.path))
        self.coordinator = ConfigArtifactCoordinator(self.manager, self.service, self.store)
        self.session = "v1303-session"

    def test_release_identity_is_v13_0_3(self):
        self.assertEqual("13.0.3", version.APP_VERSION)
        self.assertEqual("V13.0.3", version.APP_VERSION_LABEL)
        self.assertEqual("v13.0.3-20260814", version.APP_BUILD_ID)

    def test_v13_0_1_portable_profile_display_transition_is_technical_only(self):
        data = as_v13_0_1_bundle(build_bundle(
            self.manager, artifact_kind="portable_profile", scope_mode="portable_profile", name="Altprofil",
        ))
        inspected = self.coordinator.inspect_bundle(data, session_token=self.session)
        self.assertEqual([TECHNICAL_STEP], inspected["migration_steps"])
        self.assertEqual([TECHNICAL_STEP], inspected["technical_transition_steps"])
        self.assertEqual([], inspected["user_migration_steps"])
        self.assertEqual(0, inspected["user_migration_count"])

        preview = self.coordinator.preview_import(
            inspected["import_token"], base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, expert=False,
        )
        self.assertEqual("no_changes", preview["status"])
        self.assertFalse(preview["commit_allowed"])
        self.assertIsNone(preview["preview_id"])
        self.assertEqual([], preview["confirmations_required"])
        self.assertEqual([TECHNICAL_STEP], preview["technical_transition_steps"])
        self.assertEqual([], preview["user_migration_steps"])
        codes = {issue.get("code") for issue in preview["issues"]}
        self.assertNotIn(TECHNICAL_STEP, codes)
        self.assertNotIn("CONFIG_IMPORT_MIGRATED", codes)

    def test_v13_0_1_named_state_display_transition_is_technical_only(self):
        state = self.store.create(self.manager, name="Altstand")
        state_path = Path(self.store._path(state["state_id"]))
        old_data = as_v13_0_1_bundle(state_path.read_bytes())
        state_path.write_bytes(old_data); os.chmod(state_path, 0o600)
        current = next(item for item in self.store.list()["items"] if item["state_id"] == state["state_id"])
        preview = self.coordinator.preview_state(
            state["state_id"], state_revision=current["state_revision"], base_revision=self.manager.cas_revision(),
            session_token=self.session, state_snapshot={}, expert=False,
        )
        self.assertEqual("config_state_load", preview["operation"])
        self.assertEqual("no_changes", preview["status"])
        self.assertEqual([], preview["confirmations_required"])
        self.assertEqual([TECHNICAL_STEP], preview["technical_transition_steps"])
        self.assertEqual([], preview["user_migration_steps"])

    def test_noop_preview_never_requires_confirmation_even_with_warning_issue(self):
        warning = {
            "code": "TEST_WARNING", "severity": "warning", "keys": [], "message_id": "TEST_WARNING",
            "message": "Testhinweis", "params": {}, "source": "test", "blocking": False,
        }
        preview = self.service.preview_candidate(
            self.manager.candidate_base_config(), base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, patch_issues=(warning,), metadata={"operation": "config_import"},
        )
        self.assertEqual("no_changes", preview["status"])
        self.assertEqual([], preview["confirmations_required"])
        self.assertFalse(preview["commit_allowed"])

    def test_real_diff_keeps_required_confirmation_and_commit_contract(self):
        warning = {
            "code": "TEST_WARNING", "severity": "warning", "keys": ["DEADBAND_W"], "message_id": "TEST_WARNING",
            "message": "Konkretes Risiko prüfen.", "params": {}, "source": "test", "blocking": False,
        }
        candidate = self.manager.candidate_base_config()
        candidate["DEADBAND_W"] = int(self.manager.get_configured()["DEADBAND_W"]) + 1
        preview = self.service.preview_candidate(
            candidate, base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, patch_issues=(warning,), metadata={"operation": "config_import"},
        )
        self.assertEqual("ready", preview["status"])
        self.assertTrue(preview["commit_allowed"])
        self.assertTrue(preview["preview_id"])
        self.assertIn("DEADBAND_W", [row["key"] for row in preview["diff"]])
        self.assertEqual(["TEST_WARNING"], preview["confirmations_required"])

    def test_real_legacy_migration_is_user_relevant(self):
        raw = json.dumps({
            "DEVICE_ID": "TESTDEVICE",
            "SMA_DISCHARGE_BLOCK_W": self.manager.get_configured()["CROSS_CHARGE_SIGNIFICANT_W"],
        }).encode("utf-8")
        inspected = self.coordinator.inspect_legacy_raw(raw, expert=True, session_token=self.session)
        self.assertTrue(inspected["user_migration_steps"])
        self.assertEqual([], inspected["technical_transition_steps"])
        self.assertEqual(len(inspected["user_migration_steps"]), inspected["user_migration_count"])
        preview = self.coordinator.preview_import(
            inspected["import_token"], base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, expert=True, secret_operations={},
        )
        self.assertEqual("ready", preview["status"])
        self.assertIn("CONFIG_IMPORT_MIGRATED", preview["confirmations_required"])
        migration_issue = next(i for i in preview["issues"] if i["code"] == "CONFIG_IMPORT_MIGRATED")
        self.assertIn("nutzerrelevante Konfigurationsmigration", migration_issue["message"])
        legacy_issue = next(i for i in preview["issues"] if i["code"] == "LEGACY_RAW_CONFIG_NO_BUNDLE_INTEGRITY")
        self.assertNotEqual(legacy_issue["code"], legacy_issue["message"])
        self.assertIn("ältere Konfigurationsdatei", legacy_issue["message"])

    def test_frontend_contains_context_titles_noop_copy_and_technical_details(self):
        js = (ROOT / "static/settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("Konfigurationsstand prüfen", js)
        self.assertIn("Import prüfen", js)
        self.assertIn("Keine Änderungen erforderlich", js)
        self.assertIn("Kompatibel eingelesen", js)
        self.assertIn("Technische Details", js)
        self.assertIn("commitButton.hidden = noChanges", js)
        self.assertIn("closeButton.hidden = noChanges", js)
        self.assertIn("user_migration_steps", js)
        self.assertNotIn("Speichern nicht möglich", js)
        self.assertNotIn("Hinweis <b>${esc(c)}</b> wurde geprüft und wird bewusst bestätigt.", js)


    def test_preview_modal_keeps_desktop_mobile_internal_scroll_and_single_noop_action_contract(self):
        js = (ROOT / "static/settings_v2.js").read_text(encoding="utf-8")
        css = (ROOT / "static/settings_v2.css").read_text(encoding="utf-8")
        self.assertIn("commitButton.hidden = noChanges", js)
        self.assertIn("closeButton.hidden = noChanges", js)
        self.assertIn("backButton.textContent = noChanges && !app.previewReturnToConfigStates ? 'Schließen' : 'Zurück'", js)
        self.assertIn(".modal{display:flex;flex-direction:column;overflow:hidden", css)
        self.assertIn(".modal-body{flex:1 1 auto;min-height:0;overflow-y:auto;overscroll-behavior:contain", css)
        self.assertIn(".modal-actions{padding:12px 16px calc(12px + env(safe-area-inset-bottom));position:sticky;bottom:0}", css)

    def test_installer_is_strict_v13_0_2_to_v13_0_3(self):
        script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION="v13_0_3"', script)
        self.assertIn('EXPECTED_SOURCE_VERSION="13.0.2"', script)
        self.assertIn('EXPECTED_SOURCE_BUILD_ID="v13.0.2-20260812"', script)
        self.assertIn('EXPECTED_TARGET_VERSION="13.0.3"', script)
        self.assertIn('EXPECTED_TARGET_BUILD_ID="v13.0.3-20260814"', script)


if __name__ == "__main__":
    unittest.main()
