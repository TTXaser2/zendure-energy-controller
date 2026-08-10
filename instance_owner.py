# SPDX-License-Identifier: AGPL-3.0-or-later
"""Host-global single-instance ownership for the productive ZEC controller.

The lock path is deliberately absolute and independent from cwd/source path.
The kernel-held flock is authoritative; the small JSON payload is diagnostics
only and is overwritten only after ownership has been acquired.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import json
import os
from typing import Any, Dict, Optional, TextIO

INSTANCE_LOCK_PATH = "/opt/zendure-controller/zendure_controller.instance.lock"
INSTANCE_LOCK_EXIT_CODE = 73


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_locked_file(fh: TextIO) -> Dict[str, Any]:
    try:
        fh.seek(0)
        raw = fh.read().strip()
        if not raw:
            return {}
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"raw": raw}
    except Exception:
        return {}


class InstanceLockHeldError(RuntimeError):
    def __init__(self, path: str, owner: Optional[Dict[str, Any]] = None) -> None:
        self.path = path
        self.owner = dict(owner or {})
        super().__init__(f"ZEC controller instance lock is already held: {path}")


@dataclass
class InstanceOwnership:
    fh: TextIO
    path: str
    pid: int
    started_time_utc: str
    build_id: str

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "started_time_utc": self.started_time_utc,
            "build_id": self.build_id,
            "lock_path": self.path,
        }

    def close(self) -> None:
        if not self.fh.closed:
            self.fh.close()


def acquire_instance_lock(lock_path: str = INSTANCE_LOCK_PATH, *, build_id: str = "") -> InstanceOwnership:
    """Acquire the single productive owner lock or fail without side effects.

    A persistent lock file is intentional: stale file contents are harmless
    because ownership is the kernel flock, which is released automatically on
    clean close and on hard process death. The file is never unlinked while an
    owner may still hold the inode.
    """
    path = os.path.abspath(lock_path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    os.fchmod(fd, 0o600)
    fh = os.fdopen(fd, "r+", encoding="utf-8")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        owner = _read_locked_file(fh)
        fh.close()
        raise InstanceLockHeldError(path, owner) from exc
    except Exception:
        fh.close()
        raise

    started = _utc_now()
    ownership = InstanceOwnership(fh=fh, path=path, pid=os.getpid(), started_time_utc=started, build_id=str(build_id or ""))
    fh.seek(0)
    fh.truncate(0)
    json.dump(ownership.metadata, fh, ensure_ascii=False, sort_keys=True)
    fh.write("\n")
    fh.flush()
    os.fsync(fh.fileno())
    return ownership
