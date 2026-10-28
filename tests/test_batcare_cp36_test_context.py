"""CP36: provenance-safe dual runtime tests, never release approval."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tests.v18_staging_test_contract import is_v18_stage, assert_stage_runtime, assert_stage_installer
from tools.verify_release_identity_readiness import python_identity

ROOT = Path(__file__).resolve().parents[1]


class CP36TestContextSafety(unittest.TestCase):
    def test_actual_context_is_exactly_known_v17_or_blocked_v18(self):
        ident = python_identity(ROOT)
        self.assertIn(ident['APP_VERSION'], ('17.1.3', '18.0.0'))
        staged = is_v18_stage(ROOT)
        self.assertEqual(staged, ident['APP_VERSION'] == '18.0.0')
        if staged:
            assert_stage_runtime(self, ROOT)
            assert_stage_installer(self, ROOT)
        else:
            self.assertEqual('v17.1.3-20261022', ident['APP_BUILD_ID'])

    def test_forged_v18_identity_outside_staging_root_rejected(self):
        with TemporaryDirectory() as temp:
            bad = Path(temp)
            (bad/'version.py').write_text('APP_VERSION = "18.0.0"\nAPP_VERSION_LABEL = "V18.0.0"\nAPP_BUILD_ID = "v18.0.0-20261027"\n')
            with self.assertRaises(AssertionError):
                is_v18_stage(bad)

    def test_unknown_candidate_version_rejected(self):
        with TemporaryDirectory() as temp:
            unknown = Path(temp)
            (unknown/'version.py').write_text('APP_VERSION = "19.0.0"\nAPP_VERSION_LABEL = "V19.0.0"\nAPP_BUILD_ID = "v19.0.0-test"\n')
            with self.assertRaises(AssertionError):
                is_v18_stage(unknown)

    def test_historical_v17_assertion_bodies_still_present(self):
        for rel in ('test_batcare_v18_candidate_contract.py',
                    'test_batcare_release_identity_readiness.py',
                    'test_batcare_v18_staging_freeze.py'):
            content = (ROOT/'tests'/rel).read_text(encoding='utf-8')
            self.assertTrue(any(x in content for x in ('if is_v18_stage(', 'if cls.from_staging:', 'if staged:', "if python_identity(ROOT)['APP_VERSION']")))
            if rel != 'test_batcare_v18_staging_freeze.py':
                self.assertIn('17.1.3', content)
            else:
                self.assertIn('cls.created = prepare(ROOT, cls.parent)', content)


if __name__ == '__main__':
    unittest.main()
