#!/usr/bin/env python3
"""Build and verify the canonical ZEC release ZIP with exactly one expected root directory."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

VOLATILE_PARTS={'.pytest_cache','__pycache__'}
VOLATILE_SUFFIXES={'.pyc','.pyo'}

def expected_root(version:str)->str:
    return f"zendure_controller_v{version.replace('.', '_')}"

def verify_zip(path:Path, version:str)->dict:
    root=expected_root(version)
    errors=[]
    with ZipFile(path) as zf:
        bad=zf.testzip()
        if bad: errors.append(f'ZIP_CRC_ERROR:{bad}')
        names=[n for n in zf.namelist() if n and not n.endswith('/')]
    if not names: errors.append('ZIP_EMPTY')
    prefix=root+'/'
    outside=[n for n in names if not n.startswith(prefix)]
    if outside: errors.append('ZIP_ROOT_MISMATCH:'+outside[0])
    if names and not any(n==prefix+'version.py' for n in names): errors.append('VERSION_FILE_UNDER_ROOT_MISSING')
    if names and not any(n==prefix+'tools/install_zendure_controller.sh' for n in names): errors.append('INSTALLER_UNDER_ROOT_MISSING')
    return {'ok':not errors,'root':root,'files':len(names),'errors':errors}

def build(root:Path,out:Path,version:str)->dict:
    root=root.resolve(); out=out.resolve(); arcroot=expected_root(version)
    with ZipFile(out,'w',ZIP_DEFLATED,compresslevel=6) as zf:
        for p in sorted(root.rglob('*')):
            if not p.is_file() or p.is_symlink() or p.resolve()==out: continue
            rel=p.relative_to(root)
            if any(part in VOLATILE_PARTS for part in rel.parts) or p.suffix in VOLATILE_SUFFIXES: continue
            zf.write(p,Path(arcroot)/rel)
    return verify_zip(out,version)

def main()->int:
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='cmd',required=True)
    b=sub.add_parser('build'); b.add_argument('--root',required=True); b.add_argument('--output',required=True); b.add_argument('--version',required=True)
    v=sub.add_parser('verify'); v.add_argument('--zip',required=True); v.add_argument('--version',required=True)
    a=ap.parse_args()
    result=build(Path(a.root),Path(a.output),a.version) if a.cmd=='build' else verify_zip(Path(a.zip),a.version)
    print('RELEASE_PACKAGE_GATE='+('PASS' if result['ok'] else 'FAIL'))
    print('EXPECTED_ZIP_ROOT='+result['root']); print('ZIP_FILE_COUNT='+str(result['files']))
    for e in result['errors']: print('ERROR='+e)
    return 0 if result['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
