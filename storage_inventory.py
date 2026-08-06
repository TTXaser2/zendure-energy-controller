# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bounded asynchronous storage inventory for the web/status path.

GET consumers only copy an in-memory snapshot. Potentially expensive directory
and CSV scans run in one daemon worker and never in an HTTP request or control
cycle.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


class StorageInventory:
    def __init__(self, builder: Callable[[], Dict[str, Any]]) -> None:
        self._builder = builder
        self._lock = threading.RLock()
        self._in_flight = False
        self._generation = 0
        self._thread: Optional[threading.Thread] = None
        self._snapshot: Dict[str, Any] = {
            "status": "pending",
            "ready": False,
            "refresh_in_flight": False,
            "generation": 0,
            "built_at": None,
            "duration_ms": None,
            "error": None,
        }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            value = dict(self._snapshot)
            value["refresh_in_flight"] = self._in_flight
            return value

    def _worker(self) -> None:
        started = time.monotonic()
        try:
            payload = dict(self._builder() or {})
            status = "ok"
            error = None
        except Exception as exc:  # diagnostic infrastructure must fail closed
            payload = {}
            status = "error"
            error = type(exc).__name__
        duration_ms = round((time.monotonic() - started) * 1000.0, 3)
        with self._lock:
            self._generation += 1
            self._snapshot = {
                **payload,
                "status": status,
                "ready": status == "ok",
                "refresh_in_flight": False,
                "generation": self._generation,
                "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "duration_ms": duration_ms,
                "error": error,
            }
            self._in_flight = False

    def refresh_async(self) -> Dict[str, Any]:
        with self._lock:
            if self._in_flight:
                return {"status": "already_running", "generation": self._generation}
            self._in_flight = True
            thread = threading.Thread(target=self._worker, name="zec-storage-inventory", daemon=True)
            self._thread = thread
            thread.start()
            return {"status": "scheduled", "generation": self._generation}

    def wait(self, timeout: float = 5.0) -> bool:
        with self._lock:
            thread = self._thread
        if thread is None:
            return True
        thread.join(max(0.0, float(timeout)))
        return not thread.is_alive()
