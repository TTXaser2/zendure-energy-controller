#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared secretsafe support-bundle core for ZEC deployment and manual support.

The externally shareable ZIP never contains raw config.json. Installer failures
may collect a pre-rollback snapshot into a persistent work directory and finalize
that same bundle after rollback with the rollback result appended.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from typing import Any, Mapping, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_ROOT))
from tools.deployment_contract import dependency_matrix, effective_local_web_endpoint, read_identity  # noqa:E402

SECRET_TOKENS = ("PASSWORD", "SECRET", "TOKEN", "API_KEY", "PRIVATE_KEY", "CREDENTIAL")


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    try:
        from settings_registry import SETTINGS_BY_KEY
    except Exception:
        SETTINGS_BY_KEY={}
    out: dict[str, Any]={}
    for key,value in data.items():
        spec=SETTINGS_BY_KEY.get(key)
        secret=bool(spec is not None and getattr(spec,'is_secret',False)) or any(token in str(key).upper() for token in SECRET_TOKENS)
        out[key]={"secret_set":bool(value)} if secret else value
    return out


def _secret_values_from_config(config_path: Path) -> list[str]:
    if not config_path.is_file():
        return []
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, dict):
        return []
    try:
        from settings_registry import SETTINGS_BY_KEY
    except Exception:
        SETTINGS_BY_KEY = {}
    values: list[str] = []
    for key, value in raw.items():
        spec = SETTINGS_BY_KEY.get(key)
        secret = bool(spec is not None and getattr(spec, "is_secret", False)) or any(token in str(key).upper() for token in SECRET_TOKENS)
        if secret and value not in (None, ""):
            text = str(value)
            if len(text) >= 3:
                values.append(text)
    return sorted(set(values), key=len, reverse=True)


def redact_text(text: str, secret_values: Sequence[str]) -> str:
    out = text
    for value in secret_values:
        out = out.replace(value, "<redacted-secret>")
    return out


def sanitize_work_tree(work: Path, secret_values: Sequence[str]) -> None:
    if not secret_values:
        return
    for path in work.rglob("*"):
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        clean = redact_text(raw, secret_values)
        if clean != raw:
            path.write_text(clean, encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text if text.endswith('\n') else text+'\n', encoding='utf-8')


def run_capture(work: Path, name: str, command: Sequence[str], timeout: int=15) -> None:
    try:
        cp=subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, check=False)
        text=f"Command: {' '.join(command)}\nReturnCode: {cp.returncode}\n\n{cp.stdout or ''}"
    except Exception as exc:
        text=f"Command: {' '.join(command)}\nERROR: {type(exc).__name__}: {exc}\n"
    write_text(work/f'{name}.txt',text)


def http_snapshot(work: Path, name: str, url: str) -> None:
    target=work/f'{name}.json'
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body=response.read()
        try:
            parsed=json.loads(body.decode('utf-8'))
            target.write_text(json.dumps(parsed,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        except Exception:
            (work/f'{name}.txt').write_bytes(body)
    except Exception as exc:
        write_text(work/f'{name}.error.txt',f'{type(exc).__name__}: {exc}')


def collect(args: argparse.Namespace) -> Path:
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    if args.work_dir:
        work=Path(args.work_dir); work.mkdir(parents=True,exist_ok=True)
    else:
        stamp=time.strftime('%Y%m%d_%H%M%S')
        safe=''.join(ch if ch.isalnum() or ch in '._-' else '_' for ch in args.label)
        work=out/f'zec_{safe}_support_{stamp}.work'
        work.mkdir(parents=True,exist_ok=False)
    endpoint=effective_local_web_endpoint(target=args.target)
    metadata={
        'format':'ZEC_SUPPORT_BUNDLE_V1','label':args.label,'stage':args.stage,
        'error_code':args.error_code,'created_epoch_s':time.time(),
        'package_sha256':args.package_sha256,'source_version':args.source_version,
        'source_build_id':args.source_build_id,'target_version':args.target_version,
        'target_build_id':args.target_build_id,'local_web_endpoint':endpoint,
        'raw_config_included':False,
    }
    (work/'bundle_metadata.json').write_text(json.dumps(metadata,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (work/'dependency_matrix.json').write_text(json.dumps(dependency_matrix(),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    cfg=Path(args.config)
    secret_values=_secret_values_from_config(cfg)
    if cfg.is_file():
        try:
            raw=json.loads(cfg.read_text(encoding='utf-8'))
            if isinstance(raw,dict):
                (work/'config.redacted.json').write_text(json.dumps(redact_mapping(raw),indent=2,sort_keys=True)+'\n',encoding='utf-8')
        except Exception as exc:
            write_text(work/'config_redaction_error.txt',f'{type(exc).__name__}: {exc}')
        cutover=PACKAGE_ROOT/'tools'/'v14_cutover.py'
        if cutover.is_file():
            runtime_root=str(Path(args.target).resolve())
            run_capture(work,'v14_cutover_preflight',[sys.executable,str(cutover),'preflight','--config',str(cfg),'--runtime-root',runtime_root,'--json'],timeout=30)
            run_capture(work,'v14_cutover_verify',[sys.executable,str(cutover),'verify','--config',str(cfg),'--runtime-root',runtime_root,'--json'],timeout=30)
    if args.install_log and Path(args.install_log).is_file():
        try:
            log_text=Path(args.install_log).read_text(encoding='utf-8', errors='replace')
            write_text(work/'installer.log', redact_text(log_text, secret_values))
        except Exception as exc:
            write_text(work/'installer_log_copy_error.txt', f'{type(exc).__name__}: {exc}')
    version_path=Path(args.target)/'version.py'
    (work/'installed_identity.json').write_text(json.dumps(read_identity(version_path),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (work/'package_identity.json').write_text(json.dumps(read_identity(PACKAGE_ROOT/'version.py'),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    run_capture(work,'date',['date','-Is'])
    run_capture(work,'uname',['uname','-a'])
    run_capture(work,'uptime',['uptime'])
    run_capture(work,'free',['free','-h'])
    run_capture(work,'df',['df','-hT'])
    run_capture(work,'lsblk',['lsblk','-f'])
    run_capture(work,'findmnt',['findmnt'])
    for unit in ('zendure-controller.service','zendure-replay.service','zendure-status-preview.service','mosquitto.service','evcc.service'):
        run_capture(work,'systemctl_'+unit.replace('.','_'),['systemctl','status',unit,'--no-pager','-l'])
    if args.since_epoch:
        run_capture(work,'controller_journal',['journalctl','-u','zendure-controller.service','--since',f'@{args.since_epoch}','--no-pager','-l'],timeout=25)
    else:
        run_capture(work,'controller_journal',['journalctl','-u','zendure-controller.service','-b','-n','800','--no-pager','-l'],timeout=25)
    run_capture(work,'system_warnings',['journalctl','-p','warning..alert','-b','-n','600','--no-pager','-l'],timeout=25)
    run_capture(work,'kernel_current',['journalctl','-k','-b','-n','900','--no-pager','-l'],timeout=25)
    run_capture(work,'kernel_previous',['journalctl','-k','-b','-1','-n','900','--no-pager','-l'],timeout=25)
    run_capture(work,'system_warnings_previous',['journalctl','-p','warning..alert','-b','-1','-n','900','--no-pager','-l'],timeout=25)
    run_capture(work,'controller_journal_previous',['journalctl','-u','zendure-controller.service','-b','-1','-n','500','--no-pager','-l'],timeout=25)
    run_capture(work,'dmesg_storage_filtered',['bash','-lc',"dmesg -T | egrep -i 'mmc|blk|sda|usb|ext4|vfat|fat|i/o|timeout|blocked|hung|reset|under-voltage|voltage|error|fail|throttled' || true"],timeout=25)
    run_capture(work,'runtime_log_tail',['bash','-lc',f"tail -n 600 {str(Path(args.target)/'logs/zendure_runtime.log')} || true"],timeout=15)
    run_capture(work,'fstab',['bash','-lc','cat /etc/fstab || true'])
    run_capture(work,'boot_cmdline',['bash','-lc','cat /boot/cmdline.txt 2>/dev/null || cat /boot/firmware/cmdline.txt 2>/dev/null || true'])
    run_capture(work,'boot_config',['bash','-lc','cat /boot/config.txt 2>/dev/null || cat /boot/firmware/config.txt 2>/dev/null || true'])
    base=endpoint['base_url']
    for name,path in (('health','/health'),('ready','/ready'),('status','/status'),('graph_runtime','/api/graph/v1/runtime'),('graph_workspace','/api/graph/v1/workspace')):
        http_snapshot(work,name,base+path)
    sanitize_work_tree(work, secret_values)
    return work


def finalize(work: Path, output_dir: Path, rollback_result: str='', rollback_exit_code: Optional[int]=None) -> Path:
    if (work/'config.json').exists():
        raise RuntimeError('RAW_CONFIG_FORBIDDEN_IN_SUPPORT_BUNDLE')
    if rollback_result or rollback_exit_code is not None:
        payload={'result':rollback_result or 'not_applicable','exit_code':rollback_exit_code,'recorded_epoch_s':time.time()}
        (work/'rollback_result.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    output_dir.mkdir(parents=True,exist_ok=True)
    name=work.name[:-5] if work.name.endswith('.work') else work.name
    archive=output_dir/f'{name}.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zf:
        for path in sorted(work.rglob('*')):
            if path.is_file():
                zf.write(path,arcname=f'{name}/{path.relative_to(work)}')
    os.chmod(archive,0o600)
    write_text(work/'archive_sha256.txt',sha256_file(archive))
    return archive


def main(argv: Optional[Sequence[str]]=None) -> int:
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('collect')
    c.add_argument('--label',default='manual')
    c.add_argument('--output-dir',default='/home/pi/Downloads')
    c.add_argument('--work-dir',default='')
    c.add_argument('--target',default='/opt/zendure-controller')
    c.add_argument('--config',default='/opt/zendure-controller/config.json')
    c.add_argument('--install-log',default='')
    c.add_argument('--since-epoch',default='')
    c.add_argument('--stage',default='manual_support')
    c.add_argument('--error-code',default='')
    c.add_argument('--package-sha256',default='')
    c.add_argument('--source-version',default='')
    c.add_argument('--source-build-id',default='')
    c.add_argument('--target-version',default='')
    c.add_argument('--target-build-id',default='')
    c.add_argument('--defer-finalize',action='store_true')
    f=sub.add_parser('finalize')
    f.add_argument('--work-dir',required=True)
    f.add_argument('--output-dir',default='/home/pi/Downloads')
    f.add_argument('--rollback-result',default='')
    f.add_argument('--rollback-exit-code',type=int)
    args=ap.parse_args(argv)
    if args.cmd=='collect':
        work=collect(args)
        if args.defer_finalize:
            print(work)
        else:
            archive=finalize(work,Path(args.output_dir))
            print(archive)
    else:
        archive=finalize(Path(args.work_dir),Path(args.output_dir),args.rollback_result,args.rollback_exit_code)
        print(archive)
    return 0
if __name__=='__main__': raise SystemExit(main())
