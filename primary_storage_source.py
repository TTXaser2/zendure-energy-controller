# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

"""Source-neutral helpers for the configured ZEC primary storage."""

from typing import Any, Mapping

from primary_storage_modbus import get_primary_storage_template

PROFILE_EVCC_STANDARD = "evcc_standard"
PROFILE_CUSTOM = "custom"
PROFILE_MODBUS_TEMPLATE = "modbus_template"


def primary_storage_integration_enabled(cfg: Mapping[str, Any]) -> bool:
    if "SECOND_BATTERY_INTEGRATION_ENABLED" in cfg:
        return bool(cfg.get("SECOND_BATTERY_INTEGRATION_ENABLED"))
    return bool(cfg.get("CROSS_CHARGE_ENABLED", cfg.get("EVCC_ENABLED", False)))


def primary_storage_source_profile(cfg: Mapping[str, Any]) -> str:
    return str(cfg.get("SECOND_BATTERY_SOURCE_PROFILE", PROFILE_EVCC_STANDARD) or PROFILE_EVCC_STANDARD).strip()


def primary_storage_uses_mqtt(cfg: Mapping[str, Any]) -> bool:
    return primary_storage_integration_enabled(cfg) and primary_storage_source_profile(cfg) in {PROFILE_EVCC_STANDARD, PROFILE_CUSTOM}


def primary_storage_uses_modbus(cfg: Mapping[str, Any]) -> bool:
    return primary_storage_integration_enabled(cfg) and primary_storage_source_profile(cfg) == PROFILE_MODBUS_TEMPLATE


def resolved_primary_storage_display_name(cfg: Mapping[str, Any]) -> str:
    configured = str(cfg.get("SECOND_BATTERY_DISPLAY_NAME", "") or "").strip()
    if configured:
        return configured
    if primary_storage_source_profile(cfg) == PROFILE_MODBUS_TEMPLATE:
        try:
            template = get_primary_storage_template(cfg.get("SECOND_BATTERY_MODBUS_TEMPLATE", "sma_sunny_island"))
            if template.display_name_default.strip():
                return template.display_name_default.strip()
        except Exception:
            pass
    return "Primärspeicher"


def primary_storage_source_label(cfg: Mapping[str, Any]) -> str:
    profile = primary_storage_source_profile(cfg)
    if profile == PROFILE_EVCC_STANDARD:
        return "EVCC"
    if profile == PROFILE_CUSTOM:
        return "Benutzerdefiniertes MQTT"
    if profile == PROFILE_MODBUS_TEMPLATE:
        return "Direkt per Modbus"
    return profile or "Unbekannt"
