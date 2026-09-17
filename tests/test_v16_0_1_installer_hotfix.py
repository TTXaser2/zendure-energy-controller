import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import version
from tools import deployment_contract as dc


ROOT = Path(__file__).resolve().parents[1]


class TestV1601InstallerHotfix(unittest.TestCase):
    def test_release_identity_is_v16_0_1(self):
        self.assertEqual("16.0.1", version.APP_VERSION)
        self.assertEqual("V16.0.1", version.APP_VERSION_LABEL)
        self.assertEqual("v16.0.1-20260915", version.APP_BUILD_ID)

    def test_shared_identity_verifier_accepts_exact_release_and_rejects_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            version_file = Path(td) / "version.py"
            version_file.write_text(
                'APP_VERSION = "16.0.1"\n'
                'APP_VERSION_LABEL = "V16.0.1"\n'
                'APP_BUILD_ID = "v16.0.1-20260915"\n',
                encoding="utf-8",
            )
            exact = dc.verify_release_identity(
                version_file,
                expected_version="16.0.1",
                expected_build="v16.0.1-20260915",
            )
            self.assertTrue(exact["ok"], exact)
            mismatch = dc.verify_release_identity(
                version_file,
                expected_version="16.0.0",
                expected_build="v16.0.0-20260913",
            )
            self.assertFalse(mismatch["ok"], mismatch)

    def test_identity_cli_executes_the_same_parser_used_by_installer(self):
        command = [
            sys.executable,
            str(ROOT / "tools" / "deployment_contract.py"),
            "identity",
            "--version-file",
            str(ROOT / "version.py"),
            "--expected-version",
            "16.0.1",
            "--expected-build",
            "v16.0.1-20260915",
            "--json",
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual("16.0.1", payload["identity"]["version"])

        command[command.index("16.0.1")] = "16.0.0"
        rejected = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(1, rejected.returncode, rejected.stdout)
        self.assertFalse(json.loads(rejected.stdout)["ok"])

    def test_installer_uses_shared_identity_gate_without_embedded_regex(self):
        installer = (ROOT / "tools" / "install_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION_ARG="v16_0_1"', installer)
        self.assertIn('EXPECTED_TARGET_VERSION="16.0.1"', installer)
        self.assertIn('EXPECTED_TARGET_BUILD_ID="v16.0.1-20260915"', installer)
        self.assertIn('deployment_contract.py" identity', installer)
        self.assertNotIn("m=re.search(rf", installer)


if __name__ == "__main__":
    unittest.main()
