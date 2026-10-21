#!/usr/bin/env python3
"""Fail-closed release-bound architecture/history documentation checks."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

REQUIRED=(
    'docs/INDEX.md',
    'docs/releases/v17.1.2/RELEASE_INFO_V17_1_2.md',
    'docs/releases/v17.1.2/TECHNICAL_NOTES_V17_1_2.md',
    'docs/releases/v17.1.2/BUILD_VALIDATION_V17_1_2.md',
    'docs/architecture/ZEC_V17_1_2_As_Built.md',
    'docs/specifications/ZEC_S3_PRODUKTIONSSPEZIFIKATION_20261019.md',
    'docs/ZEC_Master_Backlog.md',
    'docs/history/README.md',
    'docs/decisions/ADR-0002-S3-Legacy-Opt-in-20261019.md',
    'docs/ZEC_Technisches_Datenblatt.docx',
    'docs/ZEC_Technisches_Datenblatt.pdf',
)
ID_PATTERN=re.compile(r'\bZEC-(?:BL|EV)-[A-Z0-9-]+\b')
LINK_PATTERN=re.compile(r'(?<!!)\[[^\]]+\]\(([^)]+)\)')

def validate(root:Path)->dict:
    root=root.resolve();docs=root/'docs';errors=[]
    for rel in REQUIRED:
        f=root/rel
        if not f.is_file() or f.stat().st_size==0:errors.append(f'MISSING_OR_EMPTY:{rel}')
    # The generic entrypoints must not silently send users to an older installer.
    readme=root/'README.md'
    installation=root/'README_INSTALLATION.md'
    versioned=root/'README_INSTALLATION_V17_1_2.md'
    if not readme.is_file() or 'Zendure Energy Controller V17.1.2' not in readme.read_text(encoding='utf-8'):
        errors.append('README_CURRENT_RELEASE_MISMATCH')
    if not installation.is_file() or not versioned.is_file() or installation.read_bytes()!=versioned.read_bytes():
        errors.append('INSTALLATION_GUIDE_ENTRYPOINT_MISMATCH')
    index=docs/'INDEX.md'
    if index.is_file():
        txt=index.read_text(encoding='utf-8')
        if 'V17.1.2' not in txt or 'v17.1.2-20261021' not in txt:errors.append('WRONG_INDEX_RELEASE')
        for link in LINK_PATTERN.findall(txt):
            link=link.split('#',1)[0].strip()
            if not link or re.match(r'^[a-z]+:',link,re.I):continue
            target=(docs/link).resolve()
            if not target.is_relative_to(docs.resolve()) or not target.is_file():
                errors.append(f'BROKEN_DOC_INDEX_LINK:{link}')
    asbuilt=docs/'architecture/ZEC_V17_1_2_As_Built.md'
    if asbuilt.is_file():
        txt=asbuilt.read_text(encoding='utf-8')
        for token in ('S3','1000-ms','MIN_SOC','OBIS','V17.1.2'):
            if token not in txt:errors.append(f'AS_BUILT_MISSING:{token}')
    original=docs/'history/README.md'
    if original.is_file() and 'MISSING_ORIGINAL' not in original.read_text(encoding='utf-8'):
        errors.append('HISTORY_MISSING_ORIGINAL_NOT_DISCLOSED')
    master=root/'05_ZEC_BACKLOG_AND_ROADMAP.md';snapshot=docs/'ZEC_Master_Backlog.md'
    if master.is_file() and snapshot.is_file():
        ids=ID_PATTERN.findall(master.read_text(encoding='utf-8'))
        snap_ids=set(ID_PATTERN.findall(snapshot.read_text(encoding='utf-8')))
        missing=sorted(set(ids)-snap_ids)
        if missing:errors.append('LEDGER_IDS_DROPPED:'+','.join(missing))
        if 'ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001' not in snap_ids or 'ZEC-BL-GRID-SMA-OBIS-001' not in snap_ids:
            errors.append('RELEASE_FIX_LEDGER_IDS_MISSING')
    else:errors.append('LEDGER_MISSING')
    return {'ok':not errors,'gate':'PASS' if not errors else 'FAIL','release':'V17.1.2','errors':errors}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='.');ap.add_argument('--json',action='store_true');a=ap.parse_args()
    result=validate(Path(a.root))
    print(json.dumps(result,indent=2,ensure_ascii=False) if a.json else 'DOC_ARCH_HISTORY_GATE='+result['gate']+' '+repr(result['errors']))
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
