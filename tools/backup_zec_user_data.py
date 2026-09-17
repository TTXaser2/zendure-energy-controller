#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create a local restore-oriented ZEC user-data archive.

Unlike a support bundle this archive is allowed to contain real configuration
secrets. It is created locally, mode 0600, and is never the default artifact for
third-party support sharing.
"""
from __future__ import annotations
import argparse, hashlib, json, os, tarfile, time
from pathlib import Path
from typing import Iterable

try:
    from tools.deployment_contract import read_identity
except Exception:
    read_identity = None

DEFAULT_TARGET = Path('/opt/zendure-controller')


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def candidates(target: Path, include_measurement: bool) -> list[Path]:
    result: list[Path] = []
    for name in ('config.json', '.zec_first_install_bootstrap.json', 'zec_config_snapshots.json'):
        p=target/name
        if p.is_file(): result.append(p)
    result.extend(sorted(p for p in target.glob('config.json.last-good*') if p.is_file()))
    result.extend(sorted(p for p in target.glob('zec_runtime_events.jsonl*') if p.is_file()))
    states=target/'config-states'
    if states.is_dir(): result.extend(sorted(p for p in states.rglob('*') if p.is_file()))
    # Runtime SQLite stores are restore-relevant and normally compact enough to include.
    result.extend(sorted(p for p in target.rglob('*.sqlite3') if p.is_file() and 'tests' not in p.parts))
    if include_measurement:
        logs=target/'logs'
        if logs.is_dir(): result.extend(sorted(p for p in logs.rglob('*') if p.is_file()))
        # If configured Measurement V4 points to an external location, include it only
        # when explicitly requested.
        cfg=target/'config.json'
        if cfg.is_file():
            try:
                data=json.loads(cfg.read_text(encoding='utf-8'))
                mdir=str(data.get('MEASUREMENT_LOG_DIR') or 'logs')
                mtarget=str(data.get('MEASUREMENT_LOG_STORAGE_TARGET') or 'internal_sd')
                if os.path.isabs(mdir): ext=Path(mdir)
                elif mtarget == 'external_mount': ext=Path(str(data.get('MEASUREMENT_LOG_MOUNTPOINT') or ''))/mdir
                else: ext=None
                if ext and ext.is_dir(): result.extend(sorted(p for p in ext.rglob('*') if p.is_file()))
            except Exception:
                pass
    seen=[]; keys=set()
    for p in result:
        rp=str(p.resolve())
        if rp not in keys:
            keys.add(rp); seen.append(p)
    return seen


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--target', default=str(DEFAULT_TARGET))
    ap.add_argument('--output-dir', default='/home/pi/Downloads')
    ap.add_argument('--include-measurement-data', action='store_true')
    ap.add_argument('--label', default='uninstall')
    args=ap.parse_args()
    target=Path(args.target).resolve()
    out=Path(args.output_dir).resolve()
    try:
        out.relative_to(target)
    except ValueError:
        pass
    else:
        raise SystemExit('FEHLER: --output-dir darf nicht innerhalb des zu entfernenden ZEC-Zielverzeichnisses liegen.')
    out.mkdir(parents=True, exist_ok=True)
    stamp=time.strftime('%Y%m%d_%H%M%S')
    base=f'zec_user_data_backup_{args.label}_{stamp}'
    archive=out/f'{base}.tar.gz'
    manifest_path=out/f'{base}.manifest.json'
    files=candidates(target,args.include_measurement_data) if target.exists() else []
    entries=[]
    with tarfile.open(archive,'w:gz') as tar:
        for path in files:
            try:
                rel=path.relative_to(target)
                arcname=Path('install-root')/rel
            except ValueError:
                arcname=Path('external')/str(path).lstrip('/')
            st=path.stat()
            entries.append({'source':str(path),'archive_path':str(arcname),'size':st.st_size,'sha256':sha256_file(path),'mode':oct(st.st_mode & 0o7777),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns})
            tar.add(path,arcname=str(arcname),recursive=False)
    os.chmod(archive,0o600)
    identity = read_identity(target/'version.py') if read_identity is not None else {'version':'','build_id':'','label':''}
    manifest={'format':'ZEC_USER_DATA_BACKUP_V1','target':str(target),'installed_identity':identity,'include_measurement_data':args.include_measurement_data,'files':entries,'archive':str(archive),'archive_sha256':sha256_file(archive),'archive_size':archive.stat().st_size}
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    os.chmod(manifest_path,0o600)
    print(json.dumps(manifest,indent=2,sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
