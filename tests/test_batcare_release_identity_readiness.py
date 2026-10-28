"""No I/O mutation and fail-closed CP27 release-identity gates."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.verify_release_identity_readiness import check, python_identity, shell_installer_identity

ROOT=Path(__file__).resolve().parents[1]
ARGS=dict(version='18.0.0', build_id='v18.0.0-20261027',
          source_version='17.1.3', source_build_id='v17.1.3-20261022')


class ReleaseIdentityReadiness(unittest.TestCase):
    def test_current_cp_is_fail_closed(self):
        result=check(ROOT,**ARGS)
        self.assertEqual('FAIL',result['gate'])
        self.assertFalse(result['installable'])
        if python_identity(ROOT)['APP_VERSION'] == '18.0.0':
            self.assertIn('BUILD_EVIDENCE_CONTRACT_FAIL:BUILD_EVIDENCE_STATUS_NOT_PASS',result['errors'])
        else:
            self.assertIn('RUNTIME_IDENTITY_MISMATCH:APP_VERSION',result['errors'])
            self.assertIn('INSTALLER_IDENTITY_MISMATCH:EXPECTED_SOURCE_VERSION',result['errors'])
        self.assertIn('DATASHEET_RELEASE_IDENTITY_MISMATCH',result['errors'])
        self.assertIn('UML_RELEASE_IDENTITY_MISMATCH',result['errors'])
        self.assertIn('UML_MANUAL_REVIEW_PENDING',result['errors'])

    def test_existing_production_original_not_labeled_new(self):
        staged = python_identity(ROOT)['APP_VERSION'] == '18.0.0'
        self.assertEqual('18.0.0' if staged else '17.1.3', python_identity(ROOT)['APP_VERSION'])
        self.assertEqual('17.1.3' if staged else '17.1.2',
                         shell_installer_identity(ROOT)['EXPECTED_SOURCE_VERSION'])

    def test_unrelated_identity_rejected(self):
        result=check(ROOT,**dict(ARGS,build_id='v17.1.3-20261022'))
        self.assertIn('CANDIDATE_BUILD_INVALID',result['errors'])
        self.assertIn('RELEASE_IDENTITY_NOT_NEW',result['errors'])

    def test_no_mutation(self):
        paths=[ROOT/'version.py',ROOT/'tools/install_zendure_controller.sh',
               ROOT/'docs/architecture/uml/manifest.json']
        before=[p.read_bytes() for p in paths]
        check(ROOT,**ARGS)
        self.assertEqual(before,[p.read_bytes() for p in paths])

    def test_missing_files_reported_not_inferred(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'version.py').write_text('APP_VERSION="18.0.0"\nAPP_VERSION_LABEL="V18.0.0"\nAPP_BUILD_ID="v18.0.0-20261027"\n')
            result=check(root,**ARGS)
            self.assertEqual(result['gate'],'FAIL')
            self.assertIn('INSTALLER_IDENTITY_UNREADABLE:FileNotFoundError',result['errors'])
            self.assertIn('SOURCE_MANIFEST_MISSING',result['errors'])
            self.assertIn('DATASHEET_RELEASE_METADATA_MISSING',result['errors'])
            self.assertIn('UML_MANIFEST_MISSING',result['errors'])

    def test_blocked_build_evidence_cannot_be_accepted_as_release_identity(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix='zec_v18_blocked_evidence_') as temporary:
            root=Path(temporary)
            (root/'version.py').write_text('APP_VERSION = "18.0.0"\nAPP_VERSION_LABEL = "V18.0.0"\nAPP_BUILD_ID = "v18.0.0-20261027"\n')
            evidence=root/'validation/V18_0_0_BUILD_EVIDENCE.json'
            evidence.parent.mkdir(parents=True)
            evidence.write_text(json.dumps({
                'format':'ZEC_BUILD_EVIDENCE_V1',
                'status':'BLOCKED',
                'release':{'version':'18.0.0','label':'V18.0.0','build_id':'v18.0.0-20261027'},
                'test_file_count':0,
                'full_regression':{'status':'NOT_RUN_ON_FINAL_TREE','tests':0,'subtests':0},
                'resourcewarning_regression':{'status':'NOT_RUN_ON_FINAL_TREE','tests':0,
                                              'subtests':0,'warnings_mode':'error::ResourceWarning'},
            }))
            result=check(root,**ARGS)
            self.assertEqual('FAIL',result['gate'])
            self.assertIn('BUILD_EVIDENCE_CONTRACT_FAIL:BUILD_EVIDENCE_STATUS_NOT_PASS',result['errors'])
            self.assertIn('BUILD_EVIDENCE_CONTRACT_FAIL:BUILD_EVIDENCE_TEST_FILE_COUNT_INVALID',result['errors'])

    def test_build_evidence_with_incorrect_full_and_resourcewarning_counts_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix='zec_v18_wrong_count_') as temporary:
            root=Path(temporary)
            (root/'version.py').write_text('APP_VERSION = "18.0.0"\nAPP_VERSION_LABEL = "V18.0.0"\nAPP_BUILD_ID = "v18.0.0-20261027"\n')
            evidence=root/'validation/V18_0_0_BUILD_EVIDENCE.json'
            evidence.parent.mkdir(parents=True)
            evidence.write_text(json.dumps({
                'format':'ZEC_BUILD_EVIDENCE_V1',
                'status':'PASS',
                'release':{'version':'18.0.0','label':'V18.0.0','build_id':'v18.0.0-20261027'},
                'test_file_count':172,
                'full_regression':{'status':'PASS','tests':1200,'subtests':22},
                'resourcewarning_regression':{'status':'PASS','tests':1201,'subtests':22,
                                              'warnings_mode':'error::ResourceWarning'},
            }))
            result=check(root,**ARGS)
            self.assertEqual('FAIL',result['gate'])
            self.assertIn('BUILD_EVIDENCE_CONTRACT_FAIL:BUILD_EVIDENCE_TEST_COUNT_MISMATCH',result['errors'])

    def test_read_only_cli_output_is_json(self):
        import subprocess,sys
        proc=subprocess.run([sys.executable,str(ROOT/'tools/verify_release_identity_readiness.py'),
             '--root',str(ROOT),'--candidate-version',ARGS['version'],
             '--candidate-build',ARGS['build_id'],'--source-version',ARGS['source_version'],
             '--source-build',ARGS['source_build_id'],'--json'],capture_output=True,text=True,check=False)
        self.assertEqual(1,proc.returncode)
        self.assertEqual('FAIL',json.loads(proc.stdout)['gate'])

if __name__=='__main__':unittest.main()
