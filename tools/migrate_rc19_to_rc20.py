#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Exact, fail-closed RC19 -> RC20 configuration migration.

The tool is intentionally standalone and bounded.  It preserves unknown keys,
never clamps or repairs invalid values, writes atomically only after full RC20
validation and supports a check-only preflight for the updater.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from settings_runtime import (  # noqa: E402
    atomic_write,
    decode_json_object,
    migrate_rc19_to_rc20,
    parse_full_candidate,
    pretty_json_bytes,
    stable_read,
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="ZEC RC19 -> RC20 config migration")
    value.add_argument("--config", default="config.json", help="Path to config.json")
    value.add_argument("--check-only", action="store_true", help="Validate and print the plan without writing")
    value.add_argument("--backup", default="", help="Optional exact backup path written before migration")
    value.add_argument("--json", action="store_true", help="Machine-readable result")
    return value


def result_payload(*, path: Path, before_revision: str, after_revision: str, changed: bool, steps: tuple[str, ...]) -> Dict[str, Any]:
    return {
        "schema": "ZEC-RC19-RC20-MIGRATION-V1",
        "config_path": str(path.resolve()),
        "changed": changed,
        "steps": list(steps),
        "before_file_revision": before_revision,
        "after_file_revision": after_revision,
        "status": "ready" if changed else "no_op",
    }


def main() -> int:
    args = parser().parse_args()
    path = Path(args.config)
    read = stable_read(str(path))
    if read.status != "ok" or read.data is None:
        raise SystemExit(f"CONFIG_READ_FAILED:{read.status}")
    raw, issues = decode_json_object(read.data)
    if raw is None or issues:
        code = issues[0].code if issues else "CONFIG_JSON_INVALID"
        raise SystemExit(code)

    try:
        migrated, steps = migrate_rc19_to_rc20(raw)
    except ValueError as exc:
        raise SystemExit("CONFIG_MIGRATION_FAILED:" + str(exc)) from None
    candidate = parse_full_candidate(migrated, previous=raw)
    if not candidate.valid:
        details = ",".join(sorted({issue.code for issue in candidate.issues if issue.blocking}))
        raise SystemExit("CONFIG_VALIDATION_FAILED:" + details)

    output = pretty_json_bytes(candidate.persisted)
    changed = output != read.data
    after_revision = hashlib.sha256(output).hexdigest()
    payload = result_payload(
        path=path,
        before_revision=read.revision or "",
        after_revision=after_revision,
        changed=changed,
        steps=steps,
    )

    if not args.check_only and changed:
        if args.backup:
            backup = Path(args.backup)
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                raise SystemExit("BACKUP_ALREADY_EXISTS")
            shutil.copyfile(path, backup)
            os.chmod(backup, 0o600)
        atomic_write(str(path), output, mode=0o600)
        verified = stable_read(str(path))
        if verified.status != "ok" or verified.data != output:
            raise SystemExit("CONFIG_POST_WRITE_VERIFY_FAILED")
        payload["after_file_revision"] = verified.revision
        payload["status"] = "migrated"

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Status: {payload['status']}")
        print(f"Config: {payload['config_path']}")
        print(f"Changed: {str(payload['changed']).lower()}")
        print("Steps: " + (", ".join(payload["steps"]) if payload["steps"] else "none"))
        print(f"Before SHA256: {payload['before_file_revision']}")
        print(f"After SHA256:  {payload['after_file_revision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
