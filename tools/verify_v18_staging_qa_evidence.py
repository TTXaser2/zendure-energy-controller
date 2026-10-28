#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only, fail-closed binding of V18 staging regression *logs* to source bytes.

This does NOT issue ZEC_BUILD_EVIDENCE_V1, approve a release or enable the installer.
The two unittest runs are only pre-freeze regression evidence. The final release
must be frozen and re-tested separately, then pass manual/host/hardware gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from prepare_v18_staging_tree import OUTPUT_ROOT, verify_staging

SCHEMA = 'ZEC_V18_STAGING_QA_EVIDENCE_BINDING_V1'
DUAL_SCHEMA = 'ZEC_V18_STAGING_REGRESSION_READINESS_V1'
LOG_LIMIT = 4 * 1024 * 1024
JSON_LIMIT = 128 * 1024


def _bytes(path: Path, limit: int) -> bytes:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
        raise ValueError('FILE_MISSING_SYMLINK_OR_OVERSIZE')
    return path.read_bytes()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(path: Path) -> tuple[dict, bytes]:
    raw = _bytes(path, JSON_LIMIT)
    obj = json.loads(raw)
    if type(obj) is not dict:
        raise ValueError('JSON_NOT_OBJECT')
    return obj, raw


def check(staging_root: Path, dual_report: Path, report_dir: Path) -> dict:
    """Cross-check independent completion sidecars and logs; never trust path hints.

    Explicit caller-supplied files avoid following paths embedded in untrusted JSON.
    No staging files, build-evidence files, or log files are written or modified.
    """
    root = Path(staging_root).resolve()
    output = {'schema': SCHEMA, 'gate': 'FAIL', 'scope': 'PRE_FREEZE_STAGING_QA_ONLY',
              'release_approved': False, 'installable': False,
              'build_evidence_generated': False, 'errors': [], 'suites': []}
    errors = output['errors']
    if root.name != OUTPUT_ROOT or not root.is_dir():
        errors.append('STAGING_ROOT_INVALID')
        return output
    stage = verify_staging(root)
    output['staging_provenance_gate'] = stage['gate']
    if stage['gate'] != 'PASS':
        errors.append('STAGING_PROVENANCE_INVALID')
        return output
    manifest = root / 'V18_0_0_SOURCE_MANIFEST.sha256'
    source_sha = _sha(_bytes(manifest, LOG_LIMIT))
    output['source_manifest_sha256'] = source_sha
    try:
        report, report_raw = _json(Path(dual_report))
        output['dual_report_sha256'] = _sha(report_raw)
    except (OSError, ValueError, TypeError):
        errors.append('DUAL_REPORT_UNREADABLE')
        return output
    if (report.get('schema') != DUAL_SCHEMA or report.get('gate') != 'PASS'
            or report.get('release_approved') is not False
            or report.get('build_evidence_generated') is not False
            or report.get('errors') != []
            or report.get('staging_provenance_gate') != 'PASS'
            or report.get('test_compatibility_gate') != 'PASS'):
        errors.append('DUAL_REPORT_NOT_VALID_STAGING_PASS')
    if report.get('source_manifest_sha256') != source_sha:
        errors.append('DUAL_REPORT_SOURCE_MANIFEST_MISMATCH')
    if Path(str(report.get('staging_root', ''))).name != root.name:
        errors.append('DUAL_REPORT_ROOT_IDENTITY_MISMATCH')
    suites = report.get('suites')
    if type(suites) is not list or len(suites) != 2:
        errors.append('DUAL_REPORT_SUITE_SET_INVALID')
        return output
    for index, label in enumerate(('regular', 'strict')):
        expected_mode = 'default' if index == 0 else 'error::ResourceWarning'
        suite = suites[index]
        if type(suite) is not dict:
            errors.append('SUITE_NOT_OBJECT:' + label)
            continue
        exact = (suite.get('status') == 'PASS' and suite.get('exit_code') == 0
                 and suite.get('timed_out') is False and suite.get('complete') is True
                 and suite.get('errors') == 0 and suite.get('failures') == 0
                 and suite.get('warnings_mode') == expected_mode
                 and type(suite.get('tests')) is int and suite['tests'] > 0
                 and type(suite.get('subtests')) is int and suite['subtests'] >= 0)
        if not exact:
            errors.append('SUITE_COMPLETION_INVALID:' + label)
            continue
        try:
            # Deliberately reject symlinks and never use suite['log'] as a path.
            raw_log = _bytes(Path(report_dir) / (label + '.log'), LOG_LIMIT)
            worker, raw_worker = _json(Path(report_dir) / (label + '.worker.json'))
            decoded = raw_log.decode('utf-8', errors='replace')
        except (OSError, ValueError, TypeError):
            errors.append('SUITE_LOG_OR_WORKER_UNREADABLE:' + label)
            continue
        for name, value in (('tests', suite['tests']), ('subtests', suite['subtests']),
                            ('errors', 0), ('failures', 0)):
            if type(worker.get(name)) is not int or worker[name] != value:
                errors.append('SUITE_WORKER_COUNTER_MISMATCH:' + label + ':' + name)
        if worker.get('completed') is not True or worker.get('warnings_mode') != expected_mode:
            errors.append('SUITE_WORKER_COMPLETION_INVALID:' + label)
        # unittest output may contain diagnostic text AFTER its OK summary.
        # Require exactly one completed-run summary with the claimed count.
        matches = re.findall(r'^Ran (\d+) tests in [0-9]+(?:\.[0-9]+)?s$', decoded, re.MULTILINE)
        if matches != [str(suite['tests'])] or not re.search(r'^OK\s*$', decoded, re.MULTILINE):
            errors.append('SUITE_RAW_LOG_COMPLETION_MISMATCH:' + label)
        if re.search(r'^FAILED\s*\(', decoded, re.MULTILINE):
            errors.append('SUITE_RAW_LOG_FAILURE:' + label)
        output['suites'].append({'label': label, 'tests': suite['tests'],
                                 'subtests': suite['subtests'],
                                 'warnings_mode': expected_mode,
                                 'log_sha256': _sha(raw_log),
                                 'worker_sha256': _sha(raw_worker)})
    if len(output['suites']) != 2:
        errors.append('SUITE_EVIDENCE_INCOMPLETE')
    elif ((output['suites'][0]['tests'], output['suites'][0]['subtests']) !=
          (output['suites'][1]['tests'], output['suites'][1]['subtests'])):
        errors.append('DUAL_SUITE_COUNTER_MISMATCH')
    output['gate'] = 'PASS' if not errors else 'FAIL'
    return output


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--staging-root', required=True)
    ap.add_argument('--dual-report', required=True)
    ap.add_argument('--report-dir', required=True)
    ap.add_argument('--output-json')
    args = ap.parse_args()
    result = check(Path(args.staging_root), Path(args.dual_report), Path(args.report_dir))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output_json:
        Path(args.output_json).write_text(rendered, encoding='utf-8')
    print(rendered)
    return 0 if result['gate'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
