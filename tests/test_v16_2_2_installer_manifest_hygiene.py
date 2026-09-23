import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import version
from tools import deployment_contract as dc

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "tools" / "install_zendure_controller.sh"


class TestV1622InstallerManifestHygiene(unittest.TestCase):
    def test_release_identity_and_supported_update_source(self):
        self.assertEqual("17.0.1", version.APP_VERSION)
        self.assertEqual("V17.0.1", version.APP_VERSION_LABEL)
        self.assertEqual("v17.0.1-20260922", version.APP_BUILD_ID)
        text = INSTALLER.read_text(encoding="utf-8")
        for token in (
            'EXPECTED_VERSION_ARG="v17_0_1"',
            'EXPECTED_SOURCE_VERSION="16.2.5"',
            'EXPECTED_SOURCE_BUILD_ID="v16.2.5-20260922"',
            'EXPECTED_TARGET_VERSION="17.0.1"',
            'EXPECTED_TARGET_BUILD_ID="v17.0.1-20260922"',
            'SOURCE_MANIFEST="V17_0_1_SOURCE_MANIFEST.sha256"',
        ):
            self.assertIn(token, text)

    def test_release_hygiene_rejects_volatile_tree_and_manifest_entries(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            cache = root / ".pytest_cache" / "v" / "cache"
            cache.mkdir(parents=True)
            (cache / "nodeids").write_text("[]\n", encoding="utf-8")
            result = dc.release_tree_hygiene(root=root)
            self.assertFalse(result["ok"], result)
            self.assertTrue(any("VOLATILE_DIR:.pytest_cache" == item["reason"] for item in result["errors"]))

            manifest = root / "CURRENT.sha256"
            manifest.write_text("0" * 64 + "  ./.pytest_cache/v/cache/nodeids\n", encoding="utf-8")
            verify = dc.verify_source_manifest(root=root, manifest_name=manifest.name)
            self.assertFalse(verify["ok"], verify)
            self.assertTrue(any("FORBIDDEN_MANIFEST_ENTRY:VOLATILE_DIR:.pytest_cache" in item["reason"] for item in verify["errors"]))

    def test_manifest_build_fails_closed_until_volatile_artifact_is_removed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            cache = root / "pkg" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "module.cpython-311.pyc").write_bytes(b"cache")
            failed = dc.build_source_manifest(root=root, manifest_name="CURRENT.sha256")
            self.assertFalse(failed["ok"], failed)
            shutil.rmtree(cache)
            passed = dc.build_source_manifest(root=root, manifest_name="CURRENT.sha256")
            self.assertTrue(passed["ok"], passed)
            self.assertEqual(1, passed["entry_count"])

    @unittest.skipUnless(shutil.which("rsync"), "rsync required for deployment-contract regression")
    def test_real_rsync_update_and_fresh_targets_match_manifest_contract(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            staged = base / "staged"
            staged.mkdir()
            (staged / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
            (staged / "static").mkdir()
            (staged / "static" / "app.js").write_text("console.log('ok');\n", encoding="utf-8")
            manifest_name = "CURRENT.sha256"
            built = dc.build_source_manifest(root=staged, manifest_name=manifest_name)
            self.assertTrue(built["ok"], built)

            update = base / "update"
            update.mkdir()
            (update / "config.json").write_text('{"user": true}\n', encoding="utf-8")
            (update / "logs").mkdir()
            (update / "logs" / "runtime.log").write_text("keep\n", encoding="utf-8")
            subprocess.run([
                "rsync", "-a", "--delete",
                "--exclude", "config.json", "--exclude", "config.json.last-good*", "--exclude", "logs/",
                "--exclude", "config-states/", "--exclude", "*.sqlite3", "--exclude", "zec_config_snapshots.json",
                "--exclude", "zec_runtime_events.jsonl*", "--exclude", ".zec_first_install_bootstrap.json",
                "--exclude", "zendure_controller.lock", "--exclude", "zendure_controller.instance.lock",
                "--exclude", "__pycache__/", "--exclude", ".pytest_cache/",
                str(staged) + "/", str(update) + "/",
            ], check=True)
            self.assertTrue((update / "config.json").is_file())
            self.assertTrue((update / "logs" / "runtime.log").is_file())
            update_verify = dc.verify_source_manifest(root=update, manifest_name=manifest_name)
            self.assertTrue(update_verify["ok"], update_verify)

            fresh = base / "fresh"
            fresh.mkdir()
            subprocess.run([
                "rsync", "-a", "--exclude", "__pycache__/", "--exclude", ".pytest_cache/",
                str(staged) + "/", str(fresh) + "/",
            ], check=True)
            fresh_verify = dc.verify_source_manifest(root=fresh, manifest_name=manifest_name)
            self.assertTrue(fresh_verify["ok"], fresh_verify)

    def test_installer_preflight_checks_release_hygiene_before_manifest_and_mutation(self):
        text = INSTALLER.read_text(encoding="utf-8")
        package = text[text.index("package_preflight()") : text.index("system_dependency_preflight()")]
        self.assertLess(package.index('verify_release_tree_hygiene_at "$STAGED_ROOT"'), package.index('verify_manifest_at "$STAGED_ROOT"'))
        self.assertLess(text.index("package_preflight"), text.index("INSTALLATION_STARTED=1"))
        self.assertIn('release-hygiene', text)
        self.assertIn('verify-manifest', text)

    def test_only_main_shell_may_run_support_capture_and_rollback(self):
        text = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('MAIN_BASHPID="$BASHPID"', text)
        error = text[text.index("on_error()") : text.index("trap 'on_error")]
        guard = 'if [ "$BASHPID" != "$MAIN_BASHPID" ]'
        self.assertIn(guard, error)
        self.assertLess(error.index(guard), error.index('start_support_capture "pre_rollback"'))
        self.assertLess(error.index(guard), error.index("rollback_update"))


if __name__ == "__main__":
    unittest.main()
