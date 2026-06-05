# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""Generic Cross-Charge MQTT mapping helpers.

The rule algorithm should not know whether a second battery value originates
from EVCC, Home Assistant, Victron, SMA, or another MQTT source. This module
turns a user configuration into explicit MQTT topics and normalizes payloads.
"""

import json
from typing import Any, Dict, Optional, Set


PROFILE_EVCC_STANDARD = "evcc_standard"
PROFILE_CUSTOM = "custom"
PAYLOAD_NUMBER = "number"
PAYLOAD_JSON = "json"
UNIT_W = "W"
UNIT_KW = "kW"
UNIT_WH = "Wh"
UNIT_KWH = "kWh"


def cross_charge_enabled(cfg: Dict[str, Any]) -> bool:
    return bool(cfg.get("CROSS_CHARGE_ENABLED", cfg.get("EVCC_ENABLED", False)))


def _clean_topic(topic: Any) -> str:
    return "" if topic is None else str(topic).strip().strip("/")


def second_battery_topics(cfg: Dict[str, Any]) -> Dict[str, str]:
    """Return explicit MQTT topics for the optional second battery.

    Keys are power, soc and capacity. Optional values may be empty strings.
    In EVCC standard profile the base topic is expanded to /power, /soc and
    /capacity. In custom profile the configured single-value topics are used.
    """
    profile = str(cfg.get("SECOND_BATTERY_SOURCE_PROFILE", PROFILE_EVCC_STANDARD) or PROFILE_EVCC_STANDARD)
    if profile == PROFILE_EVCC_STANDARD:
        base = _clean_topic(cfg.get("SECOND_BATTERY_EVCC_BASE_TOPIC") or cfg.get("EVCC_SMA_BATTERY_TOPIC") or "evcc/site/battery/devices/1")
        if not base:
            return {"power": "", "soc": "", "capacity": ""}
        return {
            "power": f"{base}/power",
            "soc": f"{base}/soc",
            "capacity": f"{base}/capacity",
        }
    return {
        "power": _clean_topic(cfg.get("SECOND_BATTERY_POWER_TOPIC")),
        "soc": _clean_topic(cfg.get("SECOND_BATTERY_SOC_TOPIC")),
        "capacity": _clean_topic(cfg.get("SECOND_BATTERY_CAPACITY_TOPIC")),
    }


def second_battery_subscription_topics(cfg: Dict[str, Any]) -> Set[str]:
    return {topic for topic in second_battery_topics(cfg).values() if topic}


def _get_json_path(data: Any, path: str) -> Any:
    if path is None or str(path).strip() == "":
        return data
    current = data
    for raw_part in str(path).strip().split("."):
        part = raw_part.strip()
        if not part:
            continue
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise KeyError(path)
    return current


def extract_numeric(payload: str, payload_type: str = PAYLOAD_NUMBER, json_path: str = "") -> Optional[float]:
    """Extract a numeric value from a plain-number or JSON payload."""
    try:
        if str(payload_type or PAYLOAD_NUMBER) == PAYLOAD_JSON:
            data = json.loads(payload)
            value = _get_json_path(data, json_path)
        else:
            value = payload
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def normalize_power_w(value: Optional[float], unit: str = UNIT_W) -> Optional[float]:
    if value is None:
        return None
    return float(value) * 1000.0 if unit == UNIT_KW else float(value)


def normalize_capacity_kwh(value: Optional[float], unit: str = UNIT_KWH) -> Optional[float]:
    if value is None:
        return None
    return float(value) / 1000.0 if unit == UNIT_WH else float(value)


def parse_second_battery_value(kind: str, payload: str, cfg: Dict[str, Any]) -> Optional[float]:
    """Parse and normalize one second-battery value.

    kind: power -> W, soc -> %, capacity -> kWh
    """
    profile = str(cfg.get("SECOND_BATTERY_SOURCE_PROFILE", PROFILE_EVCC_STANDARD) or PROFILE_EVCC_STANDARD)
    if profile == PROFILE_EVCC_STANDARD:
        payload_type = PAYLOAD_NUMBER
        json_path = ""
    else:
        payload_type = str(cfg.get(f"SECOND_BATTERY_{kind.upper()}_PAYLOAD_TYPE", PAYLOAD_NUMBER) or PAYLOAD_NUMBER)
        json_path = str(cfg.get(f"SECOND_BATTERY_{kind.upper()}_JSON_PATH", "") or "")

    value = extract_numeric(payload, payload_type, json_path)
    if kind == "power":
        return normalize_power_w(value, str(cfg.get("SECOND_BATTERY_POWER_UNIT", UNIT_W) or UNIT_W))
    if kind == "capacity":
        return normalize_capacity_kwh(value, str(cfg.get("SECOND_BATTERY_CAPACITY_UNIT", UNIT_KWH) or UNIT_KWH))
    return value


def normalize_discharge_power_w(raw_power_w: Any, discharge_sign: Any = 1) -> float:
    """Return positive W when the second battery discharges, otherwise 0."""
    try:
        sign = int(float(discharge_sign))
    except Exception:
        sign = 1
    if sign not in (-1, 1):
        sign = 1
    try:
        return max(0.0, float(raw_power_w) * float(sign))
    except Exception:
        return 0.0


def display_power_w(raw_power_w: Any, discharge_sign: Any = 1) -> float:
    """Return UI convention: positive = charging, negative = discharging."""
    return -1.0 * normalize_signed_power_w(raw_power_w, discharge_sign)


def normalize_signed_power_w(raw_power_w: Any, discharge_sign: Any = 1) -> float:
    """Return signed W where positive = discharging, negative = charging."""
    try:
        sign = int(float(discharge_sign))
    except Exception:
        sign = 1
    if sign not in (-1, 1):
        sign = 1
    try:
        return float(raw_power_w) * float(sign)
    except Exception:
        return 0.0
