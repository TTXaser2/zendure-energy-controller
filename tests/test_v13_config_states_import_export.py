import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from config_artifacts import ConfigArtifactCoordinator
from config_bundle import (
    BUNDLE_MAX_BYTES, BundleError, build_bundle, build_bundle_payload,
    encode_bundle, parse_bundle,
)
from config_manager import ConfigManager, DEFAULT_CONFIG
from config_states import ConfigStateStore
from settings_registry import PortabilityClass, managed_settings
from settings_service import SettingsService


class V13ConfigStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg["DEVICE_ID"] = "TESTDEVICE"
        cfg["MQTT_PASSWORD"] = "super-secret"
        cfg["CUSTOM_UNKNOWN"] = "keep-target"
        cfg.pop("DEADBAND_W", None)  # source state inherits registry default
        self.path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        self.manager = ConfigManager(str(self.path)); self.manager.load()
        self.service = SettingsService(self.manager)
        self.store = ConfigStateStore(str(self.path))
        self.coordinator = ConfigArtifactCoordinator(self.manager, self.service, self.store)
        self.session = "session-token"

    def test_every_managed_setting_has_explicit_portability(self):
        specs = managed_settings()
        self.assertEqual(191, len(specs))
        self.assertTrue(all(spec.portability_class is not None for spec in specs))
        self.assertTrue(all(spec.portability_class is not PortabilityClass.SECRET or spec.is_secret for spec in specs))

    def test_named_state_never_contains_secret_plaintext(self):
        item = self.store.create(self.manager, name="Gut", description="Test")
        data = self.store.export_bytes(item["state_id"], expected_revision=item["state_revision"])
        self.assertNotIn(b"super-secret", data)
        parsed = parse_bundle(data)
        self.assertFalse(parsed.secrets["included"])
        self.assertIn("MQTT_PASSWORD", parsed.secrets["items"])

    def test_portable_profile_contains_only_portable_keys_and_no_secret(self):
        data = build_bundle(self.manager, artifact_kind="portable_profile", scope_mode="portable_profile", name="Profil")
        parsed = parse_bundle(data)
        self.assertEqual("portable_profile", parsed.payload["artifact_kind"])
        self.assertNotIn(b"super-secret", data)
        self.assertEqual(55, len(parsed.scope["keys"]))
        for key in parsed.scope["keys"]:
            from settings_registry import SETTINGS_BY_KEY
            self.assertIs(SETTINGS_BY_KEY[key].portability_class, PortabilityClass.PORTABLE_PROFILE)

    def test_state_load_restores_inheritance_and_preserves_target_unknown_and_secret(self):
        state = self.store.create(self.manager, name="Inherited")
        preview = self.service.preview({
            "base_revision": self.manager.cas_revision(),
            "changes": {"DEADBAND_W": {"op": "set", "value": 90}},
            "secrets": {},
        }, self.session, {})
        self.service.commit({"preview_id": preview["preview_id"], "confirmations": preview["confirmations_required"]}, self.session)
        self.assertEqual(90, self.manager.get_configured()["DEADBAND_W"])

        loaded = self.coordinator.preview_state(
            state["state_id"], state_revision=state["state_revision"], base_revision=self.manager.cas_revision(),
            session_token=self.session, state_snapshot={}, expert=False,
        )
        self.assertEqual("ready", loaded["status"])
        change = next(row for row in loaded["diff"] if row["key"] == "DEADBAND_W")
        self.assertEqual("inherited", change["new_origin"])
        result = self.service.commit({"preview_id": loaded["preview_id"], "confirmations": loaded["confirmations_required"]}, self.session)
        self.assertEqual("committed", result["status"])
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertNotIn("DEADBAND_W", raw)
        self.assertEqual("keep-target", raw["CUSTOM_UNKNOWN"])
        self.assertEqual("super-secret", raw["MQTT_PASSWORD"])

    def test_state_revision_is_rechecked_at_commit(self):
        state = self.store.create(self.manager, name="Before")
        # Make the target differ so the state preview is commit-capable; a pure
        # no-op intentionally has no preview token in V13.0.2.
        changed = self.service.preview({
            "base_revision": self.manager.cas_revision(),
            "changes": {"DEADBAND_W": {"op": "set", "value": 91}},
            "secrets": {},
        }, self.session, {})
        self.service.commit({"preview_id": changed["preview_id"], "confirmations": changed["confirmations_required"]}, self.session)
        loaded = self.coordinator.preview_state(
            state["state_id"], state_revision=state["state_revision"], base_revision=self.manager.cas_revision(),
            session_token=self.session, state_snapshot={},
        )
        self.assertEqual("ready", loaded["status"])
        self.store.patch(state["state_id"], expected_revision=state["state_revision"], name="After")
        with self.assertRaisesRegex(RuntimeError, "CONFIG_STATE_REVISION_CONFLICT"):
            self.service.commit({"preview_id": loaded["preview_id"], "confirmations": loaded["confirmations_required"]}, self.session)

    def test_import_roundtrip_uses_preview_and_secret_keep_by_default(self):
        data = build_bundle(self.manager, artifact_kind="export", scope_mode="full_managed", name="Backup")
        inspected = self.coordinator.inspect_bundle(data, session_token=self.session)
        preview = self.coordinator.preview_import(
            inspected["import_token"], base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, expert=False,
        )
        self.assertEqual("no_changes", preview["status"])
        self.assertIsNone(preview["preview_id"])
        self.assertFalse(preview["commit_allowed"])
        self.assertNotIn("super-secret", json.dumps(preview))

    def test_bundle_integrity_and_duplicate_keys_fail_closed(self):
        data = build_bundle(self.manager, artifact_kind="export", scope_mode="full_managed")
        doc = json.loads(data)
        doc["payload"]["name"] = "tampered"
        with self.assertRaisesRegex(BundleError, "BUNDLE_INTEGRITY_MISMATCH"):
            parse_bundle((json.dumps(doc) + "\n").encode())
        with self.assertRaisesRegex(BundleError, "BUNDLE_DUPLICATE_KEY"):
            parse_bundle(b'{"format":"ZEC-CONFIG-BUNDLE","format":"x","format_version":1,"payload":{},"integrity":{}}')

    def test_bundle_parser_rejects_malformed_and_oversize_inputs(self):
        cases = [
            (b"\xff", "BUNDLE_UTF8_INVALID"),
            (b"{", "BUNDLE_JSON_INVALID"),
            (b"[]", "BUNDLE_ROOT_NOT_OBJECT"),
            (b'{"x":NaN}', "BUNDLE_NON_FINITE_NUMBER"),
        ]
        for data, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(BundleError, code):
                parse_bundle(data)
        with self.assertRaisesRegex(BundleError, "BUNDLE_TOO_LARGE"):
            parse_bundle(b" " * (BUNDLE_MAX_BYTES + 1))

    def test_unknown_registry_drift_fails_closed_without_explicit_bundle_migration(self):
        payload = build_bundle_payload(self.manager, artifact_kind="export", scope_mode="full_managed")
        payload["source"]["settings_registry_sha256"] = "0" * 64
        with self.assertRaisesRegex(BundleError, "SETTINGS_REGISTRY_COMPATIBILITY_UNSUPPORTED"):
            parse_bundle(encode_bundle(payload))

    def test_bundle_semantic_contract_rejects_missing_resolved_and_secret_mismatch(self):
        payload = build_bundle_payload(self.manager, artifact_kind="export", scope_mode="full_managed")
        payload["resolved_values"].pop("DEADBAND_W", None)
        with self.assertRaisesRegex(BundleError, "BUNDLE_RESOLVED_VALUE_MISSING"):
            parse_bundle(encode_bundle(payload))

        payload = build_bundle_payload(
            self.manager, artifact_kind="export", scope_mode="full_managed", include_secrets=True,
        )
        payload["secrets"]["included"] = False
        with self.assertRaisesRegex(BundleError, "BUNDLE_SECRET_INCLUDE_MISMATCH"):
            parse_bundle(encode_bundle(payload))

        payload = build_bundle_payload(
            self.manager, artifact_kind="export", scope_mode="full_managed", include_secrets=True,
        )
        payload["scope"]["keys"].remove("MQTT_PASSWORD")
        with self.assertRaisesRegex(BundleError, "BUNDLE_SECRET_OUTSIDE_SCOPE"):
            parse_bundle(encode_bundle(payload))

    def test_import_token_is_session_bound_and_expires(self):
        data = build_bundle(self.manager, artifact_kind="export", scope_mode="full_managed")
        with patch("config_artifacts.time.monotonic", return_value=100.0):
            inspected = self.coordinator.inspect_bundle(data, session_token=self.session)
        with patch("config_artifacts.time.monotonic", return_value=101.0):
            with self.assertRaisesRegex(PermissionError, "CONFIG_IMPORT_TOKEN_SESSION_MISMATCH"):
                self.coordinator.preview_import(
                    inspected["import_token"], base_revision=self.manager.cas_revision(),
                    session_token="different-session", state_snapshot={},
                )
        with patch("config_artifacts.time.monotonic", return_value=1000.0):
            with self.assertRaisesRegex(KeyError, "CONFIG_IMPORT_TOKEN_EXPIRED_OR_UNKNOWN"):
                self.coordinator.preview_import(
                    inspected["import_token"], base_revision=self.manager.cas_revision(),
                    session_token=self.session, state_snapshot={},
                )

    def test_secret_import_keep_replace_and_clear_confirmation(self):
        data = build_bundle(
            self.manager, artifact_kind="export", scope_mode="full_managed", include_secrets=True,
        )
        inspected = self.coordinator.inspect_bundle(data, session_token=self.session)

        keep = self.coordinator.preview_import(
            inspected["import_token"], base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, expert=True, secret_operations={"MQTT_PASSWORD": {"op": "keep"}},
        )
        self.assertNotIn("MQTT_PASSWORD", [row["key"] for row in keep["diff"]])

        # Change target secret first; importing with replace restores source secret.
        preview = self.service.preview({
            "base_revision": self.manager.cas_revision(), "changes": {},
            "secrets": {"MQTT_PASSWORD": {"op": "replace", "value": "target-secret"}},
        }, self.session, {})
        committed = self.service.commit({
            "preview_id": preview["preview_id"], "confirmations": preview["confirmations_required"],
        }, self.session)
        self.assertNotIn("target-secret", json.dumps(committed["audit"]))

        data2 = build_bundle(
            # source bundle was created before target change, so reuse original bytes
            self.manager, artifact_kind="export", scope_mode="full_managed", include_secrets=True,
        )
        # Recreate a source bundle with a distinct secret to prove replacement without exposing it in preview/audit.
        source_cfg = json.loads(self.path.read_text(encoding="utf-8")); source_cfg["MQTT_PASSWORD"] = "portable-secret"
        source_path = Path(self.tmp.name) / "source.json"; source_path.write_text(json.dumps(source_cfg), encoding="utf-8")
        source_manager = ConfigManager(str(source_path)); source_manager.load()
        source_data = build_bundle(source_manager, artifact_kind="export", scope_mode="full_managed", include_secrets=True)
        source_inspected = self.coordinator.inspect_bundle(source_data, session_token=self.session)
        repl = self.coordinator.preview_import(
            source_inspected["import_token"], base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, expert=True, secret_operations={"MQTT_PASSWORD": {"op": "replace"}},
        )
        self.assertNotIn("portable-secret", json.dumps(repl))
        result = self.service.commit({"preview_id": repl["preview_id"], "confirmations": repl["confirmations_required"]}, self.session)
        self.assertEqual("portable-secret", json.loads(self.path.read_text(encoding="utf-8"))["MQTT_PASSWORD"] )
        self.assertNotIn("portable-secret", json.dumps(result["audit"]))

        inspected3 = self.coordinator.inspect_bundle(source_data, session_token=self.session)
        clear = self.coordinator.preview_import(
            inspected3["import_token"], base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, expert=True, secret_operations={"MQTT_PASSWORD": {"op": "clear"}},
        )
        self.assertIn("IMPORT_SECRET_CLEAR_CONFIRMATION", clear["confirmations_required"])
        with self.assertRaisesRegex(PermissionError, "CONFIRMATIONS_MISSING"):
            self.service.commit({"preview_id": clear["preview_id"], "confirmations": []}, self.session)

        # Preview tokens are one-shot after a failed commit attempt; create a fresh clear preview and confirm it.
        inspected4 = self.coordinator.inspect_bundle(source_data, session_token=self.session)
        clear2 = self.coordinator.preview_import(
            inspected4["import_token"], base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, expert=True, secret_operations={"MQTT_PASSWORD": {"op": "clear"}},
        )
        result2 = self.service.commit({
            "preview_id": clear2["preview_id"], "confirmations": clear2["confirmations_required"],
        }, self.session)
        self.assertEqual("", json.loads(self.path.read_text(encoding="utf-8"))["MQTT_PASSWORD"])
        self.assertNotIn("portable-secret", json.dumps(result2["audit"]))

    def test_state_store_rejects_group_or_world_readable_state_file(self):
        state = self.store.create(self.manager, name="Secure")
        path = Path(self.store._path(state["state_id"]))
        os.chmod(path, 0o644)
        with self.assertRaisesRegex(Exception, "CONFIG_STATE_FILE_PERMISSIONS_UNSAFE"):
            self.store.get(state["state_id"])

    def test_legacy_raw_import_requires_expert_and_still_uses_preview(self):
        raw = json.dumps({"DEVICE_ID": "TESTDEVICE", "DEADBAND_W": 91}).encode("utf-8")
        with self.assertRaisesRegex(PermissionError, "EXPERT_MODE_REQUIRED"):
            self.coordinator.inspect_legacy_raw(raw, session_token=self.session, expert=False)
        inspected = self.coordinator.inspect_legacy_raw(raw, session_token=self.session, expert=True)
        preview = self.coordinator.preview_import(
            inspected["import_token"], base_revision=self.manager.cas_revision(), session_token=self.session,
            state_snapshot={}, expert=True, skip_unknown=True,
        )
        self.assertIn(preview["status"], ("ready", "blocked"))
        if preview["status"] == "ready":
            self.assertIn("DEADBAND_W", [row["key"] for row in preview["diff"]])



if __name__ == "__main__":
    unittest.main()
