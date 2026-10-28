#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mutation-free integrity verification of the NON-RELEASE V18 datasheet draft.

Successful result proves only byte-level source/doc traceability, never suitability
for deployment or independent Battery-Care physical effectiveness.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

METADATA = 'docs/releases/v18.0.0/ZEC_Technisches_Datenblatt_V18_0_0_ENTWURF.provenance.json'

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def check(root: Path) -> dict:
    root=root.resolve()
    errors=[]
    try:
        record=json.loads((root/METADATA).read_text(encoding='utf8'))
    except (OSError,ValueError,TypeError) as e:
        return {'gate':'FAIL','release_approved':False,'errors':['DRAFT_METADATA_INVALID:'+type(e).__name__]}
    expected={'schema':'ZEC_V18_DATASHEET_DRAFT_PROVENANCE_V1','target_version':'18.0.0',
              'status':'DEVELOPMENT_NOT_INSTALLABLE','release_gate':'FAIL',
              'hardware_effect':'NOT_VERIFIED','manual_uml':'PENDING',
              'build_identity_status':'PROVISIONAL_NOT_FROZEN'}
    for k,v in expected.items():
        if record.get(k)!=v: errors.append('DRAFT_GUARD_MISMATCH:'+k)
    if not re.fullmatch(r'v18\.0\.0-\d{8}',str(record.get('target_build_id',''))):
        errors.append('DRAFT_BUILD_ID_INVALID')
    names={}
    for k in ('docx','pdf'):
        item=record.get('files',{}).get(k,{})
        name=item.get('path','')
        if not isinstance(name,str) or not name.startswith('docs/releases/v18.0.0/') or not name.endswith('.'+k):
            errors.append('DRAFT_ASSET_PATH_INVALID:'+k);continue
        names[k]=name
    for name,sha in list(record.get('source_sha256',{}).items())+list(record.get('canonical_previous_datasheet_sha256',{}).items())+[(x.get('path',''),x.get('sha256')) for x in record.get('files',{}).values()]:
        if not isinstance(name,str) or name.startswith('/') or '..' in Path(name).parts or not isinstance(sha,str) or not re.fullmatch(r'[0-9a-f]{64}',sha):
            errors.append('DRAFT_PROVENANCE_INVALID_PATH_OR_DIGEST');continue
        path=root/name
        if not path.is_file() or digest(path)!=sha:
            errors.append('DRAFT_PROVENANCE_MISMATCH:'+name)
    required_sources={'controller_logic.py','battery_care_policy.py','battery_care_pv_allocation.py',
                      'battery_care_grid_observation.py','battery_care_episode_store.py',
                      'battery_care_graph_history.py','battery_care_stage_events.py',
                      'operational_events.py','version.py','static/status_v2.js',
                      'tools/install_zendure_controller.sh'}
    if not required_sources.issubset(set(record.get('source_sha256',{}))):
        errors.append('DRAFT_SOURCE_COVERAGE_INSUFFICIENT')
    previous={'docs/ZEC_Technisches_Datenblatt.docx','docs/ZEC_Technisches_Datenblatt.pdf',
              'docs/ZEC_Technisches_Datenblatt.release.json'}
    if set(record.get('canonical_previous_datasheet_sha256',{}))!=previous:
        errors.append('DRAFT_LEGACY_DATASHEET_COVERAGE_MISSING')
    if 'docx' in names:
        try:
            with ZipFile(root/names['docx']) as z:
                xml=' '.join(z.read(n).decode('utf8','replace') for n in z.namelist() if n.startswith('word/') and n.endswith('.xml'))
            text=re.sub(r'<[^>]+>',' ',xml).replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')
            for phrase in record.get('required_phrases',[]):
                if phrase not in text:
                    errors.append('DRAFT_REQUIRED_TEXT_MISSING:'+str(phrase))
        except (OSError,ValueError,KeyError):
            errors.append('DRAFT_DOCX_INVALID')
    if 'pdf' in names:
        p=root/names['pdf']
        if not p.is_file() or p.stat().st_size<20000 or p.read_bytes()[:5]!=b'%PDF-':
            errors.append('DRAFT_PDF_INVALID')
    return {'gate':'PASS' if not errors else 'FAIL','release_approved':False,
            'scope':'V18_DATASHEET_DRAFT_INTEGRITY_ONLY','source_hashes':len(record.get('source_sha256',{})),
            'errors':errors}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--json',action='store_true');a=p.parse_args()
    result=check(Path(a.root));print(json.dumps(result,indent=2,ensure_ascii=False) if a.json else repr(result))
    return 0 if result['gate']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
