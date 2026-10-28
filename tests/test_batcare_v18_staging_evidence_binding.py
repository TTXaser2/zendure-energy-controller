"""Release pre-freeze QA provenance, no release approval and no Pi interactions."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_v18_staging_tree import prepare, verify_staging, OUTPUT_ROOT
from verify_release_identity_readiness import python_identity
from verify_v18_staging_qa_evidence import check


class V18StagingEvidenceBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='zec_cp39_evidence_')
        cls.base = Path(cls.temp.name)
        cls.stage = cls.base / 'stage'
        cls.stage.mkdir()
        try:
            if ROOT.name == OUTPUT_ROOT:
                # V18 is already staged. Preserve the original V17-only builder
                # contract in the opposite branch and verify copied V18 bytes.
                cls.staging_root = cls.stage / OUTPUT_ROOT
                shutil.copytree(ROOT, cls.staging_root,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc',
                                                               'logs', '*.sqlite3', '*.db', '*.log'))
                stage_gate = verify_staging(cls.staging_root)
                if stage_gate['gate'] != 'PASS':
                    raise AssertionError('V18_TEST_FIXTURE_STAGE_INVALID:' + repr(stage_gate['errors']))
            else:
                if python_identity(ROOT).get('APP_VERSION') != '17.1.3':
                    raise AssertionError('V17_TEST_FIXTURE_SOURCE_VERSION_MISMATCH')
                cls.staging_root = Path(prepare(ROOT, cls.stage)['output_root'])
        except BaseException:
            cls.temp.cleanup()
            raise
        cls.expected_manifest_sha = __import__('hashlib').sha256((cls.staging_root / 'V18_0_0_SOURCE_MANIFEST.sha256').read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.dir = self.base / 'reports'
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir()
        self.record = {
            'schema': 'ZEC_V18_STAGING_REGRESSION_READINESS_V1',
            'gate': 'PASS', 'release_approved': False, 'build_evidence_generated': False,
            'errors': [], 'staging_provenance_gate': 'PASS', 'test_compatibility_gate': 'PASS',
            'staging_root': str(self.staging_root), 'source_manifest_sha256': self.expected_manifest_sha,
            'suites': [
                {'status': 'PASS', 'exit_code': 0, 'timed_out': False, 'complete': True,
                 'errors': 0, 'failures': 0, 'tests': 1200, 'subtests': 400,
                 'warnings_mode': mode, 'log': '/malicious/external/path.log'}
                for mode in ('default', 'error::ResourceWarning')
            ],
        }
        for label, mode in (('regular', 'default'), ('strict', 'error::ResourceWarning')):
            (self.dir / (label+'.log')).write_text('......\n----------------------------------------------------------------------\nRan 1200 tests in 4.212s\n\nOK\n')
            (self.dir / (label+'.worker.json')).write_text(json.dumps({
                'completed': True, 'tests': 1200, 'subtests': 400, 'errors': 0,
                'failures': 0, 'warnings_mode': mode,
            }))
        self.report = self.dir / 'dual.json'
        self.write_report()

    def write_report(self):
        self.report.write_text(json.dumps(self.record))

    def verify(self):
        return check(self.staging_root, self.report, self.dir)

    def test_dual_root_contract_has_correct_runtime_and_hold(self):
        self.assertEqual('18.0.0', python_identity(self.staging_root)['APP_VERSION'])
        self.assertEqual('PASS', verify_staging(self.staging_root)['gate'])
        if ROOT.name == OUTPUT_ROOT:
            self.assertEqual('18.0.0', python_identity(ROOT)['APP_VERSION'])
        else:
            self.assertEqual('17.1.3', python_identity(ROOT)['APP_VERSION'])

    def test_positive_is_only_pre_freeze_and_does_not_mutate_evidence(self):
        before = (self.staging_root / 'validation/V18_0_0_BUILD_EVIDENCE.json').read_bytes()
        out = self.verify()
        self.assertEqual('PASS', out['gate'], out)
        self.assertEqual(2, len(out['suites']))
        self.assertEqual('PRE_FREEZE_STAGING_QA_ONLY', out['scope'])
        self.assertFalse(out['build_evidence_generated'])
        self.assertFalse(out['installable'])
        self.assertEqual(before, (self.staging_root / 'validation/V18_0_0_BUILD_EVIDENCE.json').read_bytes())

    def test_replay_report_wrong_manifest(self):
        self.record['source_manifest_sha256'] = '0'*64
        self.write_report()
        self.assertIn('DUAL_REPORT_SOURCE_MANIFEST_MISMATCH', self.verify()['errors'])

    def test_blocked_or_faked_release_report(self):
        self.record['release_approved'] = True
        self.write_report()
        self.assertEqual('FAIL', self.verify()['gate'])

    def test_missing_second_result(self):
        self.record['suites'].pop()
        self.write_report()
        self.assertIn('DUAL_REPORT_SUITE_SET_INVALID', self.verify()['errors'])

    def test_tampered_worker_subtests(self):
        p = self.dir/'strict.worker.json'
        obj = json.loads(p.read_text()); obj['subtests'] = 399; p.write_text(json.dumps(obj))
        self.assertIn('SUITE_WORKER_COUNTER_MISMATCH:strict:subtests', self.verify()['errors'])

    def test_failed_or_truncated_log(self):
        (self.dir/'regular.log').write_text('Ran 1200 tests in 4.212s\n\nFAILED (errors=1)\n')
        self.assertEqual('FAIL', self.verify()['gate'])

    def test_absent_worker(self):
        (self.dir/'regular.worker.json').unlink()
        self.assertIn('SUITE_LOG_OR_WORKER_UNREADABLE:regular', self.verify()['errors'])

    def test_symlinked_logs_are_not_followed(self):
        target = self.dir / 'regular.log'
        target.unlink()
        target.symlink_to(self.dir / 'strict.log')
        self.assertEqual('FAIL', self.verify()['gate'])

    def test_strict_warning_flag_was_not_actually_used(self):
        p=self.dir/'strict.worker.json'
        obj=json.loads(p.read_text()); obj['warnings_mode']='default';p.write_text(json.dumps(obj))
        self.assertIn('SUITE_WORKER_COMPLETION_INVALID:strict', self.verify()['errors'])

    def test_dual_count_divergence(self):
        self.record['suites'][1]['subtests'] = 401
        self.write_report()
        self.assertEqual('FAIL', self.verify()['gate'])


if __name__ == '__main__':
    unittest.main()
