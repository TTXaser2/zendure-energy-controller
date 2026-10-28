"""CP35: hard gate on release regression evidence, no V17-only test exclusions."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.v18_staging_regression_gate import (find_fixture_blockers, suite_result,
                                                check, V17_ONLY_FIXTURES, _guarded_dual_root_staging_fixture)
ROOT = Path(__file__).resolve().parents[1]

class V18StagingRegressionGateTests(unittest.TestCase):
    def test_three_known_v17_development_fixtures_are_detected(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            for rel, signatures in V17_ONLY_FIXTURES.items():
                dest=root/rel; dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text('\n'.join(signatures) + '\n')
            self.assertEqual(len(find_fixture_blockers(root)),len(V17_ONLY_FIXTURES))


    def test_cp36_real_multiline_guard_is_accepted(self):
        source=(ROOT/'tests/test_batcare_v18_staging_freeze.py').read_text()
        self.assertTrue(_guarded_dual_root_staging_fixture(source))
        self.assertFalse(any('V17_SOURCE_ONLY_FIXTURE_ON_V18_STAGE:tests/test_batcare_v18_staging_freeze.py' == x
                             for x in find_fixture_blockers(ROOT)))

    def test_unguarded_prepare_is_not_falsely_accepted(self):
        source='''''''''class Stub:
    def setUpClass(cls):
        cls.created = prepare(ROOT, cls.parent)
        # if cls.from_staging: shutil.copytree(ROOT, cls.stage)
''''''''' 
        self.assertFalse(_guarded_dual_root_staging_fixture(source))

    def test_dual_branch_without_runtime_hygiene_is_rejected(self):
        source='''''''''class Stub:
    def setUpClass(cls):
        if cls.from_staging:
            shutil.copytree(ROOT, cls.stage)
            cls.created = verify_staging(cls.stage)
        else:
            cls.created = prepare(ROOT, cls.parent)
''''''''' 
        self.assertFalse(_guarded_dual_root_staging_fixture(source))

    def test_missing_test_source_is_failure(self):
        with TemporaryDirectory() as d:
            self.assertTrue(any('TEST_SOURCE_MISSING' in x for x in find_fixture_blockers(Path(d))))

    def test_clean_fixture_detection(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            for rel in V17_ONLY_FIXTURES:
                dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text('def test_release_neutral(): pass\n')
            self.assertEqual(find_fixture_blockers(root),[])

    def test_forged_success_without_worker_record_rejected(self):
        self.assertEqual(suite_result(process_exit=0, worker=None,timed_out=False,strict=True)['status'],'FAIL')

    def test_timeout_with_forged_worker_pass_rejected(self):
        fake=dict(completed=True,tests=1158,subtests=10,errors=0,failures=0,
                  warnings_mode='error::ResourceWarning')
        self.assertEqual(suite_result(process_exit=0,worker=fake,timed_out=True,strict=True)['status'],'FAIL')

    def test_strict_requires_warning_mode(self):
        fake=dict(completed=True,tests=1158,subtests=10,errors=0,failures=0,
                  warnings_mode='default')
        self.assertEqual(suite_result(process_exit=0,worker=fake,timed_out=False,strict=True)['status'],'FAIL')

    def test_boolean_or_invalid_count_not_accepted(self):
        fake=dict(completed=True,tests=True,subtests=0,errors=0,failures=0,
                  warnings_mode='error::ResourceWarning')
        self.assertEqual(suite_result(process_exit=0,worker=fake,timed_out=False,strict=True)['status'],'FAIL')

    def test_valid_completed_suite_result_only(self):
        fake=dict(completed=True,tests=3,subtests=2,errors=0,failures=0,
                  warnings_mode='error::ResourceWarning')
        self.assertEqual(suite_result(process_exit=0,worker=fake,timed_out=False,strict=True)['status'],'PASS')
        self.assertEqual(suite_result(process_exit=1,worker=fake,timed_out=False,strict=True)['status'],'FAIL')

    def test_isolated_worker_imports_its_own_sibling_test_fixtures(self):
        import json
        import os
        import subprocess
        import sys
        with TemporaryDirectory() as d:
            root=Path(d)/'source'; (root/'tests').mkdir(parents=True)
            (root/'tests'/'__init__.py').write_text('')
            (root/'tests'/'sma_packet_fixtures.py').write_text('VALUE=42\n')
            (root/'tests'/'test_sibling_fixture.py').write_text(
                'import unittest\nfrom sma_packet_fixtures import VALUE\n'
                'class FixtureContract(unittest.TestCase):\n'
                '    def test_sibling(self): self.assertEqual(VALUE,42)\n')
            report=Path(d)/'worker.json'
            script=ROOT/'tools/v18_staging_regression_gate.py'
            result=subprocess.run([sys.executable,str(script),'--worker-root',str(root),
                 '--worker-result',str(report),'--worker-strict'],capture_output=True,
                 text=True,timeout=15,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            payload=json.loads(report.read_text())
            self.assertEqual((payload['tests'],payload['errors'],payload['failures']), (1,0,0))
            self.assertEqual(payload['warnings_mode'],'error::ResourceWarning')

    def test_invalid_root_never_approves_release(self):
        with TemporaryDirectory() as d:
            data=check(Path(d))
            self.assertEqual(data['gate'],'FAIL')
            self.assertFalse(data['release_approved'])
            self.assertFalse(data['build_evidence_generated'])

if __name__=='__main__': unittest.main()
