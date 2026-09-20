import argparse
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

from tools.backup_zec_user_data import main as backup_main
from tools.v16_deployment_test_harness import run_harness
from tools import zec_support_bundle as support

ROOT = Path(__file__).resolve().parents[1]


class TestV1600DeploymentHardening(unittest.TestCase):
    def test_engineering_harness_passes_all_non_destructive_scenarios(self):
        report = run_harness()
        self.assertEqual("PASS", report["status"], report)
        self.assertEqual(0, report["failure_count"], report)
        names = {c["name"] for c in report["checks"]}
        self.assertTrue({
            "clean_fresh_install", "classifier_read_only", "supported_update",
            "partial_fail_closed", "privileged_port_blocked", "port_conflict_detected",
            "missing_dependency_has_install_hint", "broker_neutral_dependencies",
            "failure_capture_before_rollback",
        }.issubset(names))

    def test_local_user_data_backup_contains_restore_data_but_measurement_is_opt_in(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            target = base / "target"; target.mkdir()
            out = base / "out"; out.mkdir()
            (target / "config.json").write_text('{"MQTT_PASSWORD":"real-secret"}\n', encoding="utf-8")
            (target / "config.json.last-good").write_text('{"ok":true}\n', encoding="utf-8")
            (target / "graph.sqlite3").write_bytes(b"sqlite-data")
            (target / "config-states").mkdir()
            (target / "config-states" / "a.zec-config.json").write_text('{}\n', encoding="utf-8")
            (target / "logs").mkdir()
            (target / "logs" / "zendure_measurements_v4.csv").write_text('secret-measurement\n', encoding="utf-8")
            argv = ["backup_zec_user_data.py", "--target", str(target), "--output-dir", str(out), "--label", "test"]
            with mock.patch("sys.argv", argv), mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(0, backup_main())
                report = json.loads(stdout.getvalue())
            archive = Path(report["archive"])
            self.assertTrue(archive.is_file())
            self.assertEqual(0o600, archive.stat().st_mode & 0o777)
            self.assertEqual(report["archive_sha256"], support.sha256_file(archive))
            with tarfile.open(archive, "r:gz") as tf:
                names = set(tf.getnames())
                self.assertIn("install-root/config.json", names)
                self.assertIn("install-root/graph.sqlite3", names)
                self.assertIn("install-root/config-states/a.zec-config.json", names)
                self.assertNotIn("install-root/logs/zendure_measurements_v4.csv", names)
                config = tf.extractfile("install-root/config.json").read().decode("utf-8")
                self.assertIn("real-secret", config)  # restore backup is intentionally not redacted

    def test_support_bundle_redacts_config_and_appends_rollback_result_to_same_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            target = base / "target"; target.mkdir()
            (target / "version.py").write_text('APP_VERSION="16.0.2"\nAPP_BUILD_ID="v16.0.2-20260917"\n', encoding="utf-8")
            cfg = target / "config.json"
            cfg.write_text(json.dumps({"MQTT_PASSWORD":"do-not-share", "MQTT_BROKER":"broker.local"}), encoding="utf-8")
            log = base / "installer.log"; log.write_text("failure\n", encoding="utf-8")
            args = argparse.Namespace(
                output_dir=str(base), work_dir="", label="fault-test", target=str(target),
                config=str(cfg), install_log=str(log), since_epoch="", stage="pre_rollback",
                error_code="SIMULATED", package_sha256="abc", source_version="15.0.3",
                source_build_id="v15.0.3-20260911", target_version="16.0.2",
                target_build_id="v16.0.2-20260917", defer_finalize=True,
            )
            def fake_run(work, name, command, timeout=15):
                (work / f"{name}.txt").write_text("simulated\n", encoding="utf-8")
            def fake_http(work, name, url):
                (work / f"{name}.json").write_text(json.dumps({"url":url})+"\n", encoding="utf-8")
            with mock.patch.object(support, "run_capture", side_effect=fake_run), \
                 mock.patch.object(support, "http_snapshot", side_effect=fake_http), \
                 mock.patch.object(support, "dependency_matrix", return_value={"ok":True}):
                work = support.collect(args)
            redacted = json.loads((work / "config.redacted.json").read_text(encoding="utf-8"))
            self.assertEqual({"secret_set": True}, redacted["MQTT_PASSWORD"])
            self.assertEqual("broker.local", redacted["MQTT_BROKER"])
            archive = support.finalize(work, base, "update_rollback_completed", 42)
            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
                self.assertTrue(any(n.endswith("rollback_result.json") for n in names))
                self.assertFalse(any(n.endswith("/config.json") for n in names))
                payload = b"".join(zf.read(n) for n in names if not n.endswith('/'))
                self.assertNotIn(b"do-not-share", payload)
                rb_name = next(n for n in names if n.endswith("rollback_result.json"))
                rb = json.loads(zf.read(rb_name))
                self.assertEqual("update_rollback_completed", rb["result"])
                self.assertEqual(42, rb["exit_code"])

    def test_operational_diagnostics_use_dynamic_endpoint_contract(self):
        files = [
            "tools/collect_zec_trace.sh", "tools/collect_resync_diagnostics.sh",
            "tools/collect_zec_crash_package.sh", "tools/collect_zec_install_diagnostics.sh",
            "tools/create_zec_analysis_package.sh", "tools/collect_zec_support_bundle.sh",
        ]
        combined = "\n".join((ROOT / f).read_text(encoding="utf-8") for f in files)
        self.assertNotIn("http://127.0.0.1:8080", combined)
        self.assertIn("deployment_contract.py", combined)
        crash = (ROOT / "tools/collect_zec_crash_package.sh").read_text(encoding="utf-8")
        self.assertNotIn("cp \"$TARGET/config.json\"", crash)
        self.assertIn("zec_support_bundle.py", crash)

    def test_uninstaller_backup_opt_out_requires_explicit_second_acknowledgement(self):
        text = (ROOT / "tools/uninstall_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn("--confirm-no-user-data-backup", text)
        self.assertIn("DELETE WITHOUT BACKUP", text)
        self.assertIn("--include-measurement-data", text)
        self.assertIn("backup_zec_user_data.py", text)

    def test_first_install_mqtt_guard_and_field_acceptance_contract(self):
        controller = (ROOT / "ZendureController.py").read_text(encoding="utf-8")
        self.assertIn('first_install_setup = config_manager.startup_mode() == "FIRST_INSTALL_SETUP"', controller)
        guard = controller[controller.index("first_install_setup ="):controller.index("primary_storage_worker = None")]
        self.assertIn("if first_install_setup:", guard)
        self.assertIn("else:\n        mqtt_bridge.start()", guard)
        self.assertNotIn("mqtt_bridge.start()\n    if first_install_setup", guard)
        field = (ROOT / "tools/v16_field_acceptance.py").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION = "16.1.0"', field)
        self.assertIn('"FIRST_INSTALL_SETUP"', field)
        self.assertIn('"CLEAN_FRESH_INSTALL"', field)
        self.assertIn("effective_local_web_endpoint", field)
        self.assertNotIn('default="http://127.0.0.1:8080"', field)

    def test_canonical_release_process_contains_deployment_exit_contract(self):
        text = (ROOT / "06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md").read_text(encoding="utf-8")
        for marker in (
            "install_zendure_controller.sh", "uninstall_zendure_controller.sh", "--preflight-only",
            "CLEAN_FRESH_INSTALL", "AMBIGUOUS_OR_PARTIAL_INSTALL", "FIRST_INSTALL_SETUP",
            "secretsicheren Diagnosekern", "Clean-Fresh-Install-Feldtest",
        ):
            self.assertIn(marker, text)

    def test_installer_preflight_is_before_productive_mutation_and_has_no_fault_injection_cli(self):
        text = (ROOT / "tools/install_zendure_controller.sh").read_text(encoding="utf-8")
        preflight_exit = text.index('if [ "$PREFLIGHT_ONLY" -eq 1 ]')
        mutation = text.index("INSTALLATION_STARTED=1")
        self.assertLess(preflight_exit, mutation)
        self.assertIn("PRODUCTIVE_CHANGES=NONE", text[:mutation])
        self.assertNotIn("--fault-inject", text)
        self.assertNotIn("--fail-phase", text)
        error = text[text.index("on_error()"):text.index("trap 'on_error")]
        self.assertLess(error.index('start_support_capture "pre_rollback"'), error.index("rollback_update"))
        self.assertLess(error.index("rollback_update"), error.index("finalize_support_capture"))


if __name__ == "__main__":
    unittest.main()
