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
        self.assertEqual("13.0.3", version.APP_VERSION)
        self.assertEqual("v13.0.3-20260814", version.APP_BUILD_ID)
        self.assertEqual(version.APP_VERSION, EXPECTED_VERSION)
        self.assertEqual(version.APP_BUILD_ID, EXPECTED_BUILD_ID)

    def test_fully_ready_current_release_cannot_be_rejected_as_identity(self):
        self.assertEqual(("READY", "FULL_READY"), classify(self._fully_ready_payload()))

    def test_previous_v13_0_1_identity_is_rejected(self):
        payload = self._fully_ready_payload()
        payload["version"] = "13.0.1"
        payload["build_id"] = "v13.0.1-20260811"
        self.assertEqual(("REJECT", "IDENTITY"), classify(payload))

    def test_installer_targets_hotfix_and_keeps_v13_0_1_as_only_source(self):
        script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_VERSION="v13_0_3"', script)
        self.assertIn('EXPECTED_SOURCE_VERSION="13.0.2"', script)
        self.assertIn('EXPECTED_SOURCE_BUILD_ID="v13.0.2-20260812"', script)
        self.assertIn('EXPECTED_TARGET_VERSION="13.0.3"', script)
        self.assertIn('EXPECTED_TARGET_BUILD_ID="v13.0.3-20260814"', script)
        self.assertIn('V13_0_3_SOURCE_MANIFEST.sha256', script)

    def test_backfill_remains_after_successful_readiness_acceptance(self):
        script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
        ready_idx = script.index('if [ "$READY_OK" -eq 1 ]')
        backfill_idx = script.index('python3 tools/backfill_graph_config_timeline.py')
        self.assertGreater(backfill_idx, ready_idx)
        self.assertIn('Historical graph enrichment is deliberately non-fatal', script)


if __name__ == "__main__":
    unittest.main()
