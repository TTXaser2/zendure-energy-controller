# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cross-process maintenance lock for the ZEC measurement SQLite store.

The lock deliberately lives beside the DB and is acquired only by asynchronous
SQLite writer/maintenance code. The controller regulation loop never waits on it.
"""
from __future__ import annotations

import fcntl
import os
import time
from contextlib import contextmanager
from typing import Iterator


class MeasurementDbMaintenanceLockTimeout(TimeoutError):
    pass


def maintenance_lock_path(db_path: str) -> str:
    return os.path.abspath(str(db_path)) + ".maintenance.lock"


@contextmanager
def measurement_db_maintenance_lock(db_path: str, *, timeout_s: float = 5.0, poll_s: float = 0.05) -> Iterator[str]:
    path = maintenance_lock_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            os.fchmod(fd, 0o600)
        except Exception:
            pass
        deadline = time.monotonic() + max(0.0, float(timeout_s))
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise MeasurementDbMaintenanceLockTimeout("MEASUREMENT_DB_MAINTENANCE_LOCK_TIMEOUT")
                time.sleep(max(0.01, float(poll_s)))
        yield path
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(fd)
