# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bounded, read-only Shelly HTTP telemetry independent of the ZEC control loop.

Used exclusively by the live status and event observer, never by control. The
existing ShellyClient/read_grid_power remains the control-loop authority.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Optional

import requests


@dataclass(frozen=True)
class LiveShellyReading:
    last_power_w: Optional[float] = None
    last_received_epoch: Optional[float] = None
    endpoint: str = ""
    last_error: str = ""


class LiveShellySampler:
    def __init__(self, config_getter: Callable[[], Mapping[str, object]], session=None) -> None:
        self.config_getter = config_getter
        self._session = session or requests.Session()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._reading = LiveShellyReading()

    def snapshot(self) -> LiveShellyReading:
        with self._lock:
            return self._reading

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name='zec-live-shelly')
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        # This worker is never allowed to initiate control actions.
        while not self._stop.is_set():
            tick = time.monotonic()
            cfg = self.config_getter()
            source = str(cfg.get('GRID_METER_SOURCE') or 'shelly_http')
            address = str(cfg.get('SHELLY_IP') or '').strip() if source == 'shelly_http' else ''
            endpoint = f'http://{address}/rpc/Shelly.GetStatus' if address else ''
            with self._lock:
                if self._reading.endpoint != endpoint:
                    self._reading = LiveShellyReading(endpoint=endpoint)
            if endpoint:
                try:
                    response = self._session.get(endpoint, timeout=0.8)
                    response.raise_for_status()
                    raw = float(response.json()['em:0']['total_act_power'])
                    with self._lock:
                        self._reading = LiveShellyReading(
                            last_power_w=raw, last_received_epoch=time.time(), endpoint=endpoint,
                        )
                except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
                    with self._lock:
                        prev = self._reading
                        self._reading = LiveShellyReading(
                            last_power_w=prev.last_power_w,
                            last_received_epoch=prev.last_received_epoch,
                            endpoint=endpoint,
                            last_error=type(exc).__name__,
                        )
            self._stop.wait(max(0.0, 1.0 - (time.monotonic() - tick)))
