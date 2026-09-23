import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import version
from tools import deployment_contract as dc

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "tools" / "install_zendure_controller.sh"


def good_payload():
    return {
        "format": "ZEC_BUILD_EVIDENCE_V1",
        "release": {
            "version": "17.0.1",
            "label": "V17.0.1",
            "build_id": "v17.0.1-20260922",
        },
        "status": "PASS",
        "test_file_count": 150,
        "full_regression": {"status": "PASS", "tests": 1123, "subtests": 698},
        "resourcewarning_regression": {
            "status": "PASS", "tests": 1123, "subtests": 698,
            "warnings_mode": "error::ResourceWarning",
        },
    }


class TestV1700BuildEvidenceContract(unittest.TestCase):
    def test_release_identity_and_update_source(self):
        self.assertEqual(("17.0.1", "V17.0.1", "v17.0.1-20260922"),
                         (version.APP_VERSION, version.APP_VERSION_LABEL, version.APP_BUILD_ID))
        text = INSTALLER.read_text(encoding="utf-8")
        for token in (
            'EXPECTED_VERSION_ARG="v17_0_1"',
            'EXPECTED_SOURCE_VERSION="16.2.5"',
            'EXPECTED_SOURCE_BUILD_ID="v16.2.5-20260922"',
            'EXPECTED_TARGET_VERSION="17.0.1"',
            'EXPECTED_TARGET_BUILD_ID="v17.0.1-20260922"',
            'SOURCE_MANIFEST="V17_0_1_SOURCE_MANIFEST.sha256"',
            'validation/V17_0_1_BUILD_EVIDENCE.json',
        ):
            self.assertIn(token, text)

    def test_machine_readable_evidence_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "validation" / "V17_0_1_BUILD_EVIDENCE.json"
            path.parent.mkdir()
            path.write_text(json.dumps(good_payload()), encoding="utf-8")
            result = dc.verify_build_evidence(
                root=root, evidence_name="validation/V17_0_1_BUILD_EVIDENCE.json",
                expected_version="17.0.1", expected_label="V17.0.1",
                expected_build="v17.0.1-20260922",
            )
            self.assertTrue(result["ok"], result)

    def test_machine_readable_evidence_fails_closed_on_wrong_release_or_mode(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "validation" / "V17_0_1_BUILD_EVIDENCE.json"
            path.parent.mkdir()
            payload = good_payload()
            payload["release"]["version"] = "16.2.2"
            payload["resourcewarning_regression"]["warnings_mode"] = "default"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = dc.verify_build_evidence(
                root=root, evidence_name="validation/V17_0_1_BUILD_EVIDENCE.json",
                expected_version="17.0.1", expected_label="V17.0.1",
                expected_build="v17.0.1-20260922",
            )
            self.assertFalse(result["ok"], result)
            reasons = {item["reason"] for item in result["errors"]}
            self.assertIn("BUILD_EVIDENCE_RELEASE_VERSION_MISMATCH", reasons)
            self.assertIn("BUILD_EVIDENCE_RESOURCEWARNING_MODE_MISMATCH", reasons)

    def test_cli_verifier_uses_same_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "validation" / "V17_0_1_BUILD_EVIDENCE.json"
            path.parent.mkdir()
            path.write_text(json.dumps(good_payload()), encoding="utf-8")
            proc = subprocess.run([
                "python3", str(ROOT / "tools" / "deployment_contract.py"),
                "verify-build-evidence", "--root", str(root),
                "--evidence", "validation/V17_0_1_BUILD_EVIDENCE.json",
                "--expected-version", "17.0.1", "--expected-label", "V17.0.1",
                "--expected-build", "v17.0.1-20260922", "--json",
            ], text=True, capture_output=True)
            self.assertEqual(0, proc.returncode, proc.stderr or proc.stdout)
            self.assertTrue(json.loads(proc.stdout)["ok"])

    def test_installer_no_longer_parses_human_text_markers(self):
        text = INSTALLER.read_text(encoding="utf-8")
        block = text[text.index("verify_build_evidence_at()") : text.index("verify_js_at()")]
        self.assertIn("verify-build-evidence", block)
        self.assertNotIn("FULL_TEST.txt", block)
        self.assertNotIn("RESOURCEWARNING_TEST.txt", block)
        self.assertNotIn("RELEASE:", block)
        self.assertNotIn("RESOURCEWARNING:", block)

    def test_package_preflight_invokes_canonical_build_evidence_verifier(self):
        text = INSTALLER.read_text(encoding="utf-8")
        start = text.index("package_preflight()")
        end = text.index("system_dependency_preflight()")
        package = text[start:end]
        self.assertIn('verify_build_evidence_at "$STAGED_ROOT"', package)
        self.assertIn('verify_manifest_at "$STAGED_ROOT"', package)
        self.assertLess(package.index('verify_manifest_at "$STAGED_ROOT"'),
                        package.index('verify_build_evidence_at "$STAGED_ROOT"'))



if __name__ == "__main__":
    unittest.main()
