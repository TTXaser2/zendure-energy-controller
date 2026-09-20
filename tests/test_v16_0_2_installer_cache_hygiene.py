import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import deployment_contract as dc

ROOT = Path(__file__).resolve().parents[1]


class TestV1602InstallerCacheHygiene(unittest.TestCase):
    def test_obsolete_cache_cleanup_removes_only_absent_source_parent(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            target = base / "target"
            staged = base / "staged"
            (target / "zendure_controller_v12" / "__pycache__").mkdir(parents=True)
            legacy_cache = target / "zendure_controller_v12" / "__pycache__" / "legacy.cpython-311.pyc"
            legacy_cache.write_bytes(b"cache")
            (target / "current_module" / "__pycache__").mkdir(parents=True)
            current_cache = target / "current_module" / "__pycache__" / "current.cpython-311.pyc"
            current_cache.write_bytes(b"cache")
            (staged / "current_module").mkdir(parents=True)
            (staged / "current_module" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

            result = dc.cleanup_obsolete_python_caches(
                target=target, staged_root=staged, apply=True,
            )
            self.assertTrue(result["ok"], result)
            self.assertFalse(legacy_cache.parent.exists())
            self.assertTrue(current_cache.is_file())
            self.assertIn(str(legacy_cache.parent), result["removed"])
            self.assertIn(str(current_cache.parent), result["skipped_active"])

    def test_non_cache_content_blocks_cleanup_without_partial_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            target = base / "target"
            staged = base / "staged"
            staged.mkdir()
            safe_cache = target / "obsolete_safe" / "__pycache__"
            blocked_cache = target / "obsolete_blocked" / "__pycache__"
            safe_cache.mkdir(parents=True)
            blocked_cache.mkdir(parents=True)
            (safe_cache / "safe.cpython-311.pyc").write_bytes(b"cache")
            note = blocked_cache / "operator-note.txt"
            note.write_text("preserve me\n", encoding="utf-8")

            result = dc.cleanup_obsolete_python_caches(
                target=target, staged_root=staged, apply=True,
            )
            self.assertFalse(result["ok"], result)
            self.assertEqual("OBSOLETE_CACHE_CLEANUP_BLOCKED", result["error"])
            self.assertTrue(safe_cache.is_dir(), "operation must be all-or-nothing")
            self.assertTrue(note.is_file())
            self.assertEqual([], result["removed"])

    @unittest.skipUnless(shutil.which("rsync"), "rsync required for installer regression")
    def test_real_rsync_update_has_no_orphan_warning_and_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            target = base / "target"
            staged = base / "staged"
            (target / "zendure_controller_v12" / "__pycache__").mkdir(parents=True)
            (target / "zendure_controller_v12" / "__pycache__" / "old.cpython-311.pyc").write_bytes(b"cache")
            (target / "current_module" / "__pycache__").mkdir(parents=True)
            (target / "current_module" / "__pycache__" / "live.cpython-311.pyc").write_bytes(b"cache")
            (target / "config.json").write_text('{"keep": true}\n', encoding="utf-8")
            (target / "logs").mkdir()
            note = target / "logs" / "operator-note.txt"
            note.write_text("keep this user file\n", encoding="utf-8")
            (staged / "current_module").mkdir(parents=True)
            (staged / "current_module" / "module.py").write_text("VALUE = 2\n", encoding="utf-8")

            cleanup = dc.cleanup_obsolete_python_caches(
                target=target, staged_root=staged, apply=True,
            )
            self.assertTrue(cleanup["ok"], cleanup)
            completed = subprocess.run(
                [
                    "rsync", "-a", "--delete",
                    "--exclude", "config.json",
                    "--exclude", "logs/",
                    "--exclude", "__pycache__/",
                    str(staged) + "/", str(target) + "/",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertNotIn("cannot delete non-empty directory", completed.stderr)
            self.assertFalse((target / "zendure_controller_v12").exists())
            self.assertTrue((target / "current_module" / "__pycache__" / "live.cpython-311.pyc").is_file())
            self.assertEqual('{"keep": true}\n', (target / "config.json").read_text(encoding="utf-8"))
            self.assertEqual("keep this user file\n", note.read_text(encoding="utf-8"))

    def test_cli_matches_library_and_installer_invokes_it_before_rsync(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            target = base / "target"
            staged = base / "staged"
            cache = target / "zendure_controller_v12" / "__pycache__"
            cache.mkdir(parents=True)
            staged.mkdir()
            (cache / "legacy.cpython-311.pyc").write_bytes(b"cache")
            command = [
                sys.executable, str(ROOT / "tools" / "deployment_contract.py"),
                "cleanup-obsolete-caches", "--target", str(target),
                "--staged-root", str(staged), "--apply", "--json",
            ]
            completed = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(0, completed.returncode, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"], payload)
            self.assertFalse(cache.exists())

        installer = (ROOT / "tools" / "install_zendure_controller.sh").read_text(encoding="utf-8")
        cleanup_pos = installer.index("cleanup-obsolete-caches")
        rsync_pos = installer.index("rsync -a --delete")
        self.assertLess(cleanup_pos, rsync_pos)
        self.assertIn('--target "$TARGET" --staged-root "$STAGED_ROOT" --apply --json', installer)


if __name__ == "__main__":
    unittest.main()
