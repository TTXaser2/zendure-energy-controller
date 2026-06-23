# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import time
from typing import Any, Dict, Optional

import requests


class ZendureLocalApiClient:
    """Small client for the local Zendure /properties/report API.

    The client is intentionally read-only. It never writes MQTT or device
    configuration; it only retrieves the locally reported device state so it
    can be used as a telemetry fallback when Zendure MQTT sensor topics are
    missing after a broker/Raspberry restart.
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        self.last_poll_epoch: Optional[float] = None

    def should_poll(self, config: Dict[str, Any]) -> bool:
        if not config.get("ZENDURE_LOCAL_API_USE_FOR_TELEMETRY", False):
            return False
        if not str(config.get("ZENDURE_LOCAL_IP", "")).strip():
            return False
        interval = max(1, int(config.get("ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS", 5)))
        if self.last_poll_epoch is None:
            return True
        return (time.time() - self.last_poll_epoch) >= interval

    def fetch_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        ip = str(config.get("ZENDURE_LOCAL_IP", "")).strip()
        if not ip:
            raise RuntimeError("ZENDURE_LOCAL_IP ist leer")
        configured_timeout = float(config.get("ZENDURE_LOCAL_API_TIMEOUT_SECONDS", 5))
        # The local API is optional/read-only telemetry. It must never block the
        # live regulator for several seconds when the device or Wi-Fi path stalls.
        # Existing configs may still contain 5 s from older releases; RC3 caps the
        # effective control-loop timeout unless the user explicitly raises the cap.
        timeout_cap = float(config.get("ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS", 1.5))
        timeout = max(0.2, min(configured_timeout, timeout_cap))
        url = f"http://{ip}/properties/report"
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        self.last_poll_epoch = time.time()
        try:
            return response.json()
        except Exception as exc:
            raise RuntimeError(f"Ungültige JSON-Antwort von {url}: {exc}")


def zendure_temp_to_celsius(value: Any) -> Optional[float]:
    """Normalize Zendure temperature values to Celsius.

    Zendure MQTT and the local /properties/report endpoint do not always expose
    temperatures in the same unit. MQTT often already publishes Celsius values
    such as 35.0 or 44.0. The local API commonly reports raw values in
    deci-Kelvin, e.g. 3091 means 309.1 K = 35.9 °C. Some integrations may also
    expose Kelvin directly. This function accepts all known forms and rejects
    implausible values rather than inventing misleading temperatures.
    """
    if value is None:
        return None
    try:
        raw = float(value)
    except Exception:
        return None

    # Already Celsius, as used by many MQTT entities.
    if -40.0 <= raw <= 120.0:
        return round(raw, 1)

    # Kelvin, rarely seen but easy to normalize.
    if 250.0 <= raw <= 400.0:
        return round(raw - 273.15, 1)

    # Deci-Kelvin, e.g. 3170 = 317.0 K = 43.9 °C.
    if 2500.0 <= raw <= 4000.0:
        return round((raw / 10.0) - 273.15, 1)

    return None
