from pathlib import Path
import unittest

import version
from tools.evaluate_installation_readiness import EXPECTED_BUILD_ID, EXPECTED_VERSION, classify


ROOT = Path(__file__).resolve().parents[1]


class V1302InstallerIdentityHotfixTests(unittest.TestCase):
    def _fully_ready_payload(self):
        return {
            "status": "ok",
            "ready": True,
            "version": version.APP_VERSION,
            "build_id": version.APP_BUILD_ID,
            "checks": {},
            "failed_checks": [],
        }

    def test_evaluator_identity_is_single_sourced_from_release_version(self):
        self.assertEqual("16.1.0", version.APP_VERSION)
        self.assertEqual("v16.1.0-20260919", version.APP_BUILD_ID)
        self.assertEqual(version.APP_VERSION, EXPECTED_VERSION)
        self.assertEqual(version.APP_BUILD_ID, EXPECTED_BUILD_ID)

    def test_fully_ready_current_release_cannot_be_rejected_as_identity(self):
        self.assertEqual(("READY", "FULL_READY"), classify(self._fully_ready_payload()))

    def test_previous_v13_0_1_identity_is_rejected(self):
        payload = self._fully_ready_payload()
        payload["version"] = "13.0.1"
        payload["build_id"] = "v13.0.1-20260811"
        self.assertEqual(("REJECT", "IDENTITY"), classify(payload))

    def test_installer_targets_v14_1_and_keeps_v14_0_0_r2_as_only_source(self):
        script = (ROOT / "tools" / "install_zendure_controller.sh").read_text(encoding="utf-8")
        for marker in (
            'EXPECTED_VERSION_ARG="v16_1_0"',
            'EXPECTED_SOURCE_VERSION="16.0.2"',
            'EXPECTED_SOURCE_BUILD_ID="v16.0.2-20260917"',
            'EXPECTED_TARGET_VERSION="16.1.0"',
            'EXPECTED_TARGET_BUILD_ID="v16.1.0-20260919"',
            'SOURCE_MANIFEST="V16_1_0_SOURCE_MANIFEST.sha256"',
        ):
            self.assertIn(marker, script)
    def test_existing_v3_is_verified_before_start_and_runtime_graph_gate_follows_readiness(self):
        script = (ROOT / "tools" / "install_zendure_controller.sh").read_text(encoding="utf-8")
        verify_idx = script.index('graph_verify_prestart.json')
        start_idx = script.index('sudo systemctl start zendure-controller.service', verify_idx)
        ready_idx = script.index('if [ "$READY_OK" -eq 1 ]', start_idx)
        graph_gate_idx = script.index('$BASE_URL/api/graph/v1/runtime', ready_idx)
        self.assertLess(verify_idx, start_idx)
        self.assertLess(ready_idx, graph_gate_idx)
        self.assertNotIn('tools/v14_cutover.py rebuild', script)
        self.assertIn('control_readiness_impact', script)

if __name__ == "__main__":
    unittest.main()
