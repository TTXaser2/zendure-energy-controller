"""CP30 negative-safety and manifest tests for non-installable V18 staging."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from prepare_v18_staging_tree import OUTPUT_ROOT, MANIFEST, prepare, verify_staging  # noqa: E402
from deployment_contract import verify_build_evidence, verify_source_manifest, release_tree_hygiene  # noqa: E402


class V18StagingFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='zec_v18_stage_cp30_')
        cls.parent = Path(cls.temp.name)
        cls.original_version_sha = hashlib.sha256((ROOT/'version.py').read_bytes()).hexdigest()
        cls.original_installer_sha = hashlib.sha256((ROOT/'tools/install_zendure_controller.sh').read_bytes()).hexdigest()
        try:
            cls.stage = cls.parent/OUTPUT_ROOT
            # On a V18 final-tree test root, re-test the existing staged artifact in a
            # disposable copy. The staging *builder* contract still runs on V17 roots.
            from verify_release_identity_readiness import python_identity
            cls.from_staging = python_identity(ROOT)['APP_VERSION'] == '18.0.0'
            if cls.from_staging:
                # Preserve the packaged V18 source, never copy transient SQLite/log
                # side effects from tests that ran earlier in this same suite.
                shutil.copytree(ROOT, cls.stage,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc',
                                                               '.pytest_cache', 'logs',
                                                               '*.sqlite3', '*.sqlite3-*',
                                                               '*.sqlite', '*.db', '*.log'))
                cls.created = verify_staging(cls.stage)
            else:
                cls.created = prepare(ROOT, cls.parent)
        except BaseException:
            cls.temp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_ephemeral_sqlite_artifacts_do_not_enter_staging(self):
        if self.from_staging:
            # The V18 root is an output, not a permitted input to prepare().
            # Enforce its hygiene directly rather than weakening the V17 input test.
            self.assertTrue(release_tree_hygiene(root=self.stage, manifest_name=MANIFEST)['ok'])
            self.assertFalse((self.stage/'logs').exists())
            return
        with tempfile.TemporaryDirectory(prefix='zec_v18_dirty_source_') as temp:
            parent=Path(temp)
            source=parent/'source'
            shutil.copytree(ROOT,source,
                            ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            log=source/'logs'
            log.mkdir(exist_ok=True)
            (log/'zec_operational_events.sqlite3').write_bytes(b'volatile-test-runtime-database')
            (log/'runtime.log').write_text('volatile\n',encoding='utf-8')
            target=parent/'staging'
            target.mkdir()
            result=prepare(source,target)
            self.assertEqual(result['gate'],'PASS')
            self.assertFalse((target/OUTPUT_ROOT/'logs').exists())
            self.assertTrue(verify_source_manifest(
                root=target/OUTPUT_ROOT, manifest_name=MANIFEST)['ok'])

    def test_staging_is_explicitly_noninstallable(self):
        self.assertEqual(self.created['gate'], 'PASS')
        self.assertFalse(self.created['installable'])
        self.assertEqual(self.created['release_identity_gate'], 'FAIL')

    def test_stage_manifest_verifies(self):
        self.assertTrue(verify_source_manifest(root=self.stage,manifest_name=MANIFEST)['ok'])

    def test_staged_runtime_has_v18_identity(self):
        text=(self.stage/'version.py').read_text()
        self.assertIn('APP_VERSION = "18.0.0"',text)
        self.assertIn('APP_BUILD_ID = "v18.0.0-20261027"',text)

    def test_standard_installer_has_non_bypassable_hold(self):
        inst = self.stage/'tools/install_zendure_controller.sh'
        self.assertFalse(inst.stat().st_mode & 0o111)
        for arg in ([], ['v18_0_0'], ['v18_0_0','--preflight-only'],
                    ['v18_0_0','--fresh-install'], ['v18_0_0','--help']):
            p=subprocess.run(['bash',str(inst),*arg],capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,78, (arg,p.stdout,p.stderr))
            self.assertIn('RELEASE_HOLD',p.stderr)

    def test_build_evidence_never_claims_pass(self):
        check=verify_build_evidence(root=self.stage,evidence_name='validation/V18_0_0_BUILD_EVIDENCE.json',
                                    expected_version='18.0.0',expected_label='V18.0.0',
                                    expected_build='v18.0.0-20261027')
        self.assertFalse(check['ok'])
        self.assertTrue(any(e['reason']=='BUILD_EVIDENCE_STATUS_NOT_PASS' for e in check['errors']))

    def test_source_tree_was_not_mutated(self):
        self.assertEqual(hashlib.sha256((ROOT/'version.py').read_bytes()).hexdigest(),self.original_version_sha)
        self.assertEqual(hashlib.sha256((ROOT/'tools/install_zendure_controller.sh').read_bytes()).hexdigest(),self.original_installer_sha)

    def test_master_ledger_is_exact_canonical_snapshot(self):
        self.assertEqual((self.stage/'docs/ZEC_Master_Backlog.md').read_bytes(),
                         (self.stage/'05_ZEC_BACKLOG_AND_ROADMAP.md').read_bytes())

    def test_repeated_prepare_refuses_to_overwrite(self):
        with self.assertRaises(FileExistsError):
            prepare(ROOT,self.parent)

    def test_manifest_manipulation_is_detected(self):
        doc=self.stage/'README.md'
        before=doc.read_bytes()
        try:
            doc.write_bytes(before+b'\nUNAUTHORIZED CHANGE\n')
            self.assertEqual(verify_staging(self.stage)['gate'],'FAIL')
            self.assertIn('STAGING_SOURCE_MANIFEST_INVALID',verify_staging(self.stage)['errors'])
        finally:
            doc.write_bytes(before)

    def test_installer_bypass_attempt_is_detected(self):
        inst=self.stage/'tools/install_zendure_controller.sh'
        before=inst.read_bytes()
        try:
            inst.write_bytes(before.replace(b'exit 78', b'exit 0',1))
            check=verify_staging(self.stage)
            self.assertEqual(check['gate'],'FAIL')
            self.assertIn('STANDARD_INSTALLER_EARLY_HOLD_MISSING',check['errors'])
        finally:
            inst.write_bytes(before)

    def test_cp33_datasheet_is_bound_to_staging_without_release_promotion(self):
        import json
        from prepare_v18_staging_tree import DATASHEET_BINDING
        binding=json.loads((self.stage/DATASHEET_BINDING).read_text())
        self.assertEqual(binding['status'], 'DEVELOPMENT_NOT_INSTALLABLE')
        self.assertEqual(binding['datasheet_status'], 'DRAFT_ONLY')
        self.assertEqual(binding['release_gate'], 'FAIL')
        self.assertEqual(set(binding['intentional_source_replacements']),
                         {'version.py', 'tools/install_zendure_controller.sh'})
        self.assertNotEqual(binding['intentional_source_replacements']['version.py']['cp33_source_sha256'],
                            binding['intentional_source_replacements']['version.py']['staged_sha256'])

    def test_staged_datasheet_tampering_fails_even_with_original_metadata(self):
        from prepare_v18_staging_tree import _verify_staged_datasheet
        pdf=self.stage/'docs/releases/v18.0.0/ZEC_Technisches_Datenblatt_V18_0_0_ENTWURF.pdf'
        before=pdf.read_bytes()
        try:
            pdf.write_bytes(before+b'INVALID_TRAILING_BYTES')
            self.assertIn('STAGED_DATASHEET_ASSET_HASH_MISMATCH:pdf',_verify_staged_datasheet(self.stage))
            self.assertEqual(verify_staging(self.stage)['gate'],'FAIL')
        finally:
            pdf.write_bytes(before)

    def test_staged_datasheet_source_mutation_is_detected(self):
        from prepare_v18_staging_tree import _verify_staged_datasheet
        path=self.stage/'battery_care_policy.py'
        before=path.read_bytes()
        try:
            path.write_bytes(before+b'\n# unauthorized mutation')
            self.assertIn('STAGED_DATASHEET_UNAUTHORIZED_SOURCE_CHANGE:battery_care_policy.py',
                          _verify_staged_datasheet(self.stage))
        finally:
            path.write_bytes(before)

    def test_missing_staged_datasheet_binding_is_fail_closed(self):
        from prepare_v18_staging_tree import DATASHEET_BINDING, _verify_staged_datasheet
        p=self.stage/DATASHEET_BINDING
        before=p.read_bytes()
        try:
            p.unlink()
            self.assertIn('STAGED_DATASHEET_PROVENANCE_MISSING_OR_INVALID',
                          _verify_staged_datasheet(self.stage))
        finally:
            p.write_bytes(before)

    def test_forged_replacement_hash_is_detected(self):
        import json
        from prepare_v18_staging_tree import DATASHEET_BINDING, _verify_staged_datasheet
        p=self.stage/DATASHEET_BINDING
        before=p.read_bytes()
        try:
            obj=json.loads(before)
            obj['intentional_source_replacements']['version.py']['staged_sha256']='0'*64
            p.write_text(json.dumps(obj))
            self.assertIn('STAGED_DATASHEET_REPLACEMENT_HASH_MISMATCH:version.py',
                          _verify_staged_datasheet(self.stage))
        finally:
            p.write_bytes(before)

    def test_review_remains_manual_and_pending(self):
        check=verify_staging(self.stage)
        self.assertEqual(check['gate'],'PASS')
        self.assertIn('UML_MANUAL_REVIEW_PENDING',check['release_identity_errors'])
        self.assertIn('BUILD_EVIDENCE_CONTRACT_FAIL:BUILD_EVIDENCE_STATUS_NOT_PASS',
                      check['release_identity_errors'])


if __name__=='__main__':
    unittest.main()
