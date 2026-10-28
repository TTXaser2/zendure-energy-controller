"""CP28: no premature production execution, correct V17.1.3->V18 staging identity."""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import v18_field_acceptance as field
from tools.verify_release_identity_readiness import check, python_identity, shell_installer_identity

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'tools/install_zendure_controller_v18_candidate.sh'
CANONICAL = ROOT / 'tools/install_zendure_controller.sh'
BUILD_ID = 'v18.0.0-20261027'


class TestCandidateV18(unittest.TestCase):
    def test_candidate_identity_exact_but_canonical_v17_remains_unchanged(self):
        staged = python_identity(ROOT)['APP_VERSION'] == '18.0.0'
        self.assertEqual('18.0.0' if staged else '17.1.3', python_identity(ROOT)['APP_VERSION'])
        self.assertEqual('17.1.3' if staged else '17.1.2',
                         shell_installer_identity(ROOT)['EXPECTED_SOURCE_VERSION'])
        if staged:
            self.assertIn('exit 78', CANONICAL.read_text().split('SCRIPT_DIR=', 1)[0])
            self.assertFalse(CANONICAL.stat().st_mode & 0o111)
        s = CANDIDATE.read_text()
        expected = {
            'EXPECTED_VERSION_ARG': 'v18_0_0',
            'EXPECTED_SOURCE_VERSION': '17.1.3',
            'EXPECTED_SOURCE_BUILD_ID': 'v17.1.3-20261022',
            'EXPECTED_TARGET_VERSION': '18.0.0',
            'EXPECTED_TARGET_BUILD_ID': BUILD_ID,
            'SOURCE_MANIFEST': 'V18_0_0_SOURCE_MANIFEST.sha256',
        }
        for name, value in expected.items():
            self.assertRegex(s, re.compile(r'^' + name + r'="' + re.escape(value) + r'"$', re.M))
        self.assertIn('validation/V18_0_0_BUILD_EVIDENCE.json', s)
        self.assertIn('verify_build_evidence_at "$STAGED_ROOT"', s)
        self.assertIn('--expected-version "$EXPECTED_SOURCE_VERSION"', s)
        self.assertIn('--expected-build "$EXPECTED_SOURCE_BUILD_ID"', s)
        self.assertIn('zec_backup_root_artifacts', s)
        self.assertIn('rollback_update()', s)
        self.assertIn('rollback_fresh()', s)
        self.assertIn('PRODUCTIVE_CHANGES=NONE', s)
        self.assertIn('ROOT_ARTIFACT_BACKUP=', s)
        self.assertNotIn('v17.1.2-installer-failure', s)
        self.assertNotIn('V17_1_3_SOURCE_MANIFEST.sha256', s)

    def test_unconditional_hold_precedes_even_script_dir_resolution(self):
        s = CANDIDATE.read_text()
        self.assertLess(s.index('exit 78'), s.index('SCRIPT_DIR='))
        self.assertLess(s.index('exit 78'), s.index('source "$SCRIPT_DIR/root_artifact_transaction.sh"'))
        self.assertNotIn('ZEC_V18_INSTALLER_RELEASE_APPROVED', s)
        self.assertFalse(CANDIDATE.stat().st_mode & 0o111)

    def test_execution_with_any_options_is_nonmutating_blocked(self):
        before = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            for args in ([], ['v18_0_0'], ['v18_0_0', '--preflight-only'],
                         ['v18_0_0', '--fresh-install'], ['v18_0_0', '--web-port', '8888'],
                         ['v17_1_3']):
                result = subprocess.run(['bash', str(CANDIDATE), *args], cwd=td,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(78, result.returncode, args)
                self.assertIn('RELEASE_HOLD', result.stderr)
                self.assertEqual([], list(Path(td).iterdir()))
        self.assertEqual(before, hashlib.sha256(CANDIDATE.read_bytes()).hexdigest())

    def test_shell_syntax_still_valid(self):
        self.assertEqual(0, subprocess.run(['bash', '-n', str(CANDIDATE)], capture_output=True).returncode)

    def test_candidate_field_contract_source_and_persistent_report(self):
        self.assertEqual('18.0.0', field.EXPECTED_VERSION)
        self.assertEqual('V18.0.0', field.EXPECTED_LABEL)
        self.assertEqual(BUILD_ID, field.EXPECTED_BUILD_ID)
        self.assertEqual({'version':'17.1.3', 'build_id':'v17.1.3-20261022'},
                         field._expected_update_source())
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            old = p/'zec_v17_1_3_install_report_foo.json'
            new = p/'zec_v18_0_0_install_report_foo.json'
            old.write_text('{}')
            new.write_text('{}')
            result, kind = field._resolve_install_report(persistent_dir=p)
            self.assertEqual(new, result)
            self.assertEqual('persistent_latest', kind)

    def test_candidate_field_does_not_inherit_v17_pass_or_simulate_care_effect(self):
        expected_runtime = ('18.0.0', BUILD_ID) if python_identity(ROOT)['APP_VERSION'] == '18.0.0' else ('17.1.3', 'v17.1.3-20261022')
        self.assertEqual(expected_runtime, (field.APP_VERSION, field.APP_BUILD_ID))
        s=(ROOT/'tools/v18_field_acceptance.py').read_text()
        self.assertIn('"battery_care_physical_effect", False', s)
        self.assertIn('RELEASE_BLOCKER_NOT_EVALUABLE', s)
        self.assertIn('configuration_mutations_by_this_tool', s)
        self.assertIn('commands_published_by_this_tool', s)
        self.assertNotIn('install_zendure_controller.sh")', s)

    def test_identity_gate_still_blocks_unready_release(self):
        r = check(ROOT, version='18.0.0', build_id=BUILD_ID,
                  source_version='17.1.3',source_build_id='v17.1.3-20261022')
        self.assertEqual('FAIL',r['gate'])
        self.assertFalse(r['installable'])
        if python_identity(ROOT)['APP_VERSION'] == '18.0.0':
            self.assertIn('BUILD_EVIDENCE_CONTRACT_FAIL:BUILD_EVIDENCE_STATUS_NOT_PASS',r['errors'])
            self.assertIn('UML_MANUAL_REVIEW_PENDING',r['errors'])
        else:
            self.assertIn('RUNTIME_IDENTITY_MISMATCH:APP_VERSION',r['errors'])
            self.assertIn('INSTALLER_IDENTITY_MISMATCH:EXPECTED_SOURCE_VERSION',r['errors'])

if __name__ == '__main__':
    unittest.main()
