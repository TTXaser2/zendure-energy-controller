"""Fail-closed, source-bound V18 datasheet DRAFT checks; never a release approval."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import shutil
import unittest

from tools.verify_v18_datasheet_draft import METADATA, check

ROOT=Path(__file__).resolve().parents[1]


class V18DatasheetDraftTests(unittest.TestCase):
    def setUp(self):
        self._temp=TemporaryDirectory(prefix='zec_v18_datasheet_test_')
        self.addCleanup(self._temp.cleanup)
        self.root=Path(self._temp.name)
        meta=json.loads((ROOT/METADATA).read_text(encoding='utf-8'))
        self.meta=meta
        names=[METADATA]+list(meta['source_sha256'])+list(meta['canonical_previous_datasheet_sha256'])
        names += [x['path'] for x in meta['files'].values()]
        for name in names:
            dest=self.root/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/name,dest)

    def save(self):
        (self.root/METADATA).write_text(json.dumps(self.meta,ensure_ascii=False),encoding='utf-8')

    def test_original_draft_verifies_but_never_approves_release(self):
        from tests.v18_staging_test_contract import is_v18_stage, assert_stage_drafts
        if is_v18_stage(Path(__file__).resolve().parents[1]):
            assert_stage_drafts(self, Path(__file__).resolve().parents[1])
            return
        result=check(self.root)
        self.assertEqual(result['gate'],'PASS',result)
        self.assertFalse(result['release_approved'])
        self.assertEqual(result['scope'],'V18_DATASHEET_DRAFT_INTEGRITY_ONLY')

    def test_pdf_byte_manipulation_rejected(self):
        p=self.root/self.meta['files']['pdf']['path'];p.write_bytes(p.read_bytes()+b'altered')
        self.assertEqual(check(self.root)['gate'],'FAIL')

    def test_docx_byte_manipulation_rejected(self):
        p=self.root/self.meta['files']['docx']['path'];p.write_bytes(p.read_bytes()+b'altered')
        self.assertEqual(check(self.root)['gate'],'FAIL')

    def test_controller_change_rejected(self):
        p=self.root/'controller_logic.py';p.write_bytes(p.read_bytes()+b'\n# modified')
        self.assertTrue(any('controller_logic.py' in x for x in check(self.root)['errors']))

    def test_published_datasheet_change_rejected(self):
        p=self.root/'docs/ZEC_Technisches_Datenblatt.pdf';p.write_bytes(p.read_bytes()+b'\n')
        self.assertTrue(any('docs/ZEC_Technisches_Datenblatt.pdf' in x for x in check(self.root)['errors']))

    def test_fake_release_approval_rejected(self):
        self.meta['status']='RELEASE_APPROVED';self.meta['release_gate']='PASS';self.save()
        res=check(self.root)
        self.assertEqual(res['gate'],'FAIL');self.assertFalse(res['release_approved'])

    def test_incomplete_source_coverage_rejected(self):
        self.meta['source_sha256'].pop('controller_logic.py');self.save()
        self.assertIn('DRAFT_SOURCE_COVERAGE_INSUFFICIENT',check(self.root)['errors'])

    def test_missing_legacy_assets_rejected(self):
        self.meta['canonical_previous_datasheet_sha256'].pop('docs/ZEC_Technisches_Datenblatt.pdf');self.save()
        self.assertIn('DRAFT_LEGACY_DATASHEET_COVERAGE_MISSING',check(self.root)['errors'])

    def test_bad_pdf_magic_rejected_even_matching_digest(self):
        from hashlib import sha256
        p=self.root/self.meta['files']['pdf']['path'];p.write_bytes(b'nopdf'+p.read_bytes()[5:]);
        self.meta['files']['pdf']['sha256']=sha256(p.read_bytes()).hexdigest();self.save()
        self.assertIn('DRAFT_PDF_INVALID',check(self.root)['errors'])

    def test_missing_metadata_fail_closed(self):
        (self.root/METADATA).unlink()
        self.assertEqual(check(self.root)['gate'],'FAIL')

if __name__=='__main__': unittest.main()
