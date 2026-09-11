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
        self.assertEqual("15.0.2", version.APP_VERSION)
        self.assertEqual("v15.0.2-20260911", version.APP_BUILD_ID)
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
        script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION="v15_0_2"', script)
        self.assertIn('EXPECTED_SOURCE_VERSION="15.0.1"', script)
        self.assertIn('EXPECTED_SOURCE_BUILD_ID="v15.0.1-20260911"', script)
        self.assertIn('EXPECTED_TARGET_VERSION="15.0.2"', script)
        self.assertIn('EXPECTED_TARGET_BUILD_ID="v15.0.2-20260911"', script)
        self.assertIn('V15_0_2_SOURCE_MANIFEST.sha256', script)

    def test_existing_v3_is_verified_before_start_and_runtime_graph_gate_follows_readiness(self):
        script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
        verify_idx = script.index('python3 tools/v14_cutover.py verify')
        normal_start_marker = script.index('echo "Starte Controller..."')
        start_idx = script.index('sudo systemctl start zendure-controller.service', normal_start_marker)
        ready_idx = script.index('if [ "$READY_OK" -eq 1 ]')
        graph_gate_idx = script.index('Prüfe getrennte Graph-History-Readiness')
        self.assertLess(verify_idx, start_idx)
        self.assertLess(ready_idx, graph_gate_idx)
        self.assertNotIn('python3 tools/v14_cutover.py rebuild', script)
        self.assertIn('control_readiness_impact', script)
        self.assertNotIn('Historical graph enrichment is deliberately non-fatal', script)


if __name__ == "__main__":
    unittest.main()
