# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from config_manager import CONFIG_SCHEMA
from settings_registry import SETTINGS, SETTINGS_BY_KEY, Visibility, ApplyClass, Editability
from settings_runtime import SettingsRuntimeManager
from settings_service import ISSUE_MESSAGES

CATEGORY_GROUPS = {
    "Betriebsart & manuelle Steuerung": "A. Betrieb",
    "Nachtbetrieb": "A. Betrieb",
    "Leistungsgrenzen & SOC-Schutz": "A. Betrieb",
    "AUTO-Regelung": "B. Regelung & Speicherstrategie",
    "Harvest / Restüberschuss": "B. Regelung & Speicherstrategie",
    "Primärspeicher & SMA": "B. Regelung & Speicherstrategie",
    "Cross-Charge-Schutz": "B. Regelung & Speicherstrategie",
    "Kommandowirkung & Resync": "B. Regelung & Speicherstrategie",
    "Zendure-Geräte": "C. Geräte & Schnittstellen",
    "Schnittstellen & Datenquellen": "C. Geräte & Schnittstellen",
    "Messdaten & Speicherung": "D. Daten, System & Diagnose",
    "System & Diagnose": "D. Daten, System & Diagnose",
}

CATEGORY_DESCRIPTIONS = {
    "Betriebsart & manuelle Steuerung": "Grundlegende Betriebsart und zeitweise feste Lade- oder Entladevorgaben.",
    "Nachtbetrieb": "Feste Nachtentladung, Zeitfenster und Reserve-SOC.",
    "Leistungsgrenzen & SOC-Schutz": "Globale Lade-, Entlade- und SOC-Schutzgrenzen.",
    "AUTO-Regelung": "Dynamik, Totzone, Glättung und Schrittweite der Netzregelung.",
    "Harvest / Restüberschuss": "Parallel-Harvest und Restexportaufnahme unter Erhalt des 0-W-Netzziels.",
    "Primärspeicher & SMA": "Integration, Datenmodell und Ladeleistungsgrenzen des Primärspeichers.",
    "Cross-Charge-Schutz": "Verhindert unerwünschtes Umladen zwischen den Speichern.",
    "Kommandowirkung & Resync": "Command-State, Wirksamkeitsprüfung, Neutralisierung und Recovery.",
    "Zendure-Geräte": "Zendure-Gerät, lokale API und gerätespezifische Telemetrie.",
    "Schnittstellen & Datenquellen": "MQTT, Netzleistungsquelle und externe Datenpfade.",
    "Messdaten & Speicherung": "Measurement V4, SQLite-Graphstore, Export und Speicherstatus.",
    "System & Diagnose": "Webserver, Darstellung, Logging, Analyse und Sicherheitsfallbacks.",
}

# Client-side visibility conditions. The values remain preserved when hidden.
DEPENDENCY_RULES: Dict[str, Dict[str, Any]] = {
    "MANUAL_FIXED_DISCHARGE_POWER_W": {"key": "MANUAL_MODE", "equals": "FIXED_DISCHARGE"},
    "MANUAL_FIXED_DISCHARGE_TARGET_SOC": {"key": "MANUAL_MODE", "equals": "FIXED_DISCHARGE"},
    "MANUAL_DISCHARGE_AFTER_TARGET": {"key": "MANUAL_MODE", "equals": "FIXED_DISCHARGE"},
    "MANUAL_FIXED_CHARGE_POWER_W": {"key": "MANUAL_MODE", "equals": "FIXED_CHARGE"},
    "MANUAL_FIXED_CHARGE_TARGET_SOC": {"key": "MANUAL_MODE", "equals": "FIXED_CHARGE"},
    "MANUAL_CHARGE_AFTER_TARGET": {"key": "MANUAL_MODE", "equals": "FIXED_CHARGE"},
    "NIGHT_START_HOUR": {"key": "NIGHT_DISCHARGE_ENABLED", "equals": True},
    "NIGHT_START_MINUTE": {"key": "NIGHT_DISCHARGE_ENABLED", "equals": True},
    "NIGHT_END_HOUR": {"key": "NIGHT_DISCHARGE_ENABLED", "equals": True},
    "NIGHT_END_MINUTE": {"key": "NIGHT_DISCHARGE_ENABLED", "equals": True},
    "NIGHT_DISCHARGE_POWER_W": {"key": "NIGHT_DISCHARGE_ENABLED", "equals": True},
    "NIGHT_DISCHARGE_STOP_SOC_PERCENT": {"key": "NIGHT_DISCHARGE_ENABLED", "equals": True},
    "ZENDURE_LOCAL_IP": {"key": "ZENDURE_LOCAL_API_ENABLED", "equals": True},
    "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": {"key": "ZENDURE_LOCAL_API_ENABLED", "equals": True},
    "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": {"key": "ZENDURE_LOCAL_API_ENABLED", "equals": True},
    "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": {"key": "ZENDURE_LOCAL_API_ENABLED", "equals": True},
    "ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY": {"key": "ZENDURE_LOCAL_API_ENABLED", "equals": True},
    "ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS": {"key": "ZENDURE_LOCAL_API_ENABLED", "equals": True},
    "ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS": {"key": "ZENDURE_LOCAL_API_ENABLED", "equals": True},
    "ZENDURE_LOCAL_API_SOC_PRIORITY": {"key": "ZENDURE_LOCAL_API_ENABLED", "equals": True},
    "MQTT_TOPIC_DIAGNOSTIC_FILTER": {"key": "MQTT_TOPIC_DIAGNOSTIC_ENABLED", "equals": True},
    "MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE": {"key": "MQTT_TOPIC_DIAGNOSTIC_ENABLED", "equals": True},
    "MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT": {"key": "MQTT_TOPIC_DIAGNOSTIC_ENABLED", "equals": True},
    "MEASUREMENT_LOG_STORAGE_TARGET": {"key": "MEASUREMENT_LOG_MODE", "not_equals": "off"},
    "MEASUREMENT_LOG_DIR": {"key": "MEASUREMENT_LOG_MODE", "not_equals": "off"},
    "MEASUREMENT_LOG_MAX_BYTES": {"key": "MEASUREMENT_LOG_MODE", "not_equals": "off"},
    "MEASUREMENT_LOG_MIN_FREE_DISK_MB": {"key": "MEASUREMENT_LOG_MODE", "not_equals": "off"},
    "FILE_LOG_DIR": {"key": "FILE_LOG_ENABLED", "equals": True},
    "FILE_LOG_FILE": {"key": "FILE_LOG_ENABLED", "equals": True},
    "FILE_LOG_MAX_BYTES": {"key": "FILE_LOG_ENABLED", "equals": True},
    "FILE_LOG_BACKUP_COUNT": {"key": "FILE_LOG_ENABLED", "equals": True},
}


def _safe_value(key: str, value: Any) -> Any:
    spec = SETTINGS_BY_KEY.get(key)
    if spec is not None and spec.is_secret:
        return None
    return value


def _description(key: str, spec: Any) -> str:
    legacy = CONFIG_SCHEMA.get(key, {})
    return str(legacy.get("description") or spec.validation_text or spec.apply_text or "")


def build_settings_model(
    manager: SettingsRuntimeManager,
    state_snapshot: Optional[Mapping[str, Any]] = None,
    *,
    csrf_token: str = "",
) -> Dict[str, Any]:
    configured = manager.get_configured()
    effective = manager.get()
    status = manager.status()
    inherited = set(status.get("inherited_default_keys") or [])
    pending = set(status.get("pending_restart_keys") or [])
    issue_by_key: Dict[str, List[Dict[str, Any]]] = {}
    for issue in status.get("issues") or []:
        issue = dict(issue)
        issue["message"] = ISSUE_MESSAGES.get(issue.get("message_id") or issue.get("code"), issue.get("code"))
        for key in issue.get("keys") or ["__global__"]:
            issue_by_key.setdefault(key, []).append(issue)

    categories: Dict[str, Dict[str, Any]] = {}
    for spec in SETTINGS:
        # S1 shows the active RC19/S1 surface. Later-release target-only fields
        # remain in the registry but are not presented as operational settings.
        if spec.visibility in (
            Visibility.HIDDEN_MIGRATION,
            Visibility.HIDDEN_TRANSITION,
        ):
            continue
        if spec.release_stage != "S1" and spec.origin != "RC19":
            continue
        if spec.lifecycle.startswith("remove_") or spec.lifecycle in ("reserved_inactive", "deployment_constant_not_config"):
            continue

        category = categories.setdefault(spec.category, {
            "name": spec.category,
            "group": CATEGORY_GROUPS.get(spec.category, "D. Daten, System & Diagnose"),
            "description": CATEGORY_DESCRIPTIONS.get(spec.category, ""),
            "sections": {},
            "setting_count": 0,
        })
        section = category["sections"].setdefault(spec.section, {"name": spec.section, "settings": []})
        configured_value = configured.get(spec.key, spec.default_new_install)
        effective_value = effective.get(spec.key, spec.default_new_install)
        available = spec.release_stage == "S1" or spec.origin == "RC19"
        editable = bool(
            available
            and spec.editability is Editability.EDITABLE
            and spec.apply_class not in (ApplyClass.PROTECTED_ACTION, ApplyClass.READ_ONLY, ApplyClass.MIGRATION_ONLY)
        )
        entry = {
            "key": spec.key,
            "label": spec.label,
            "description": _description(spec.key, spec),
            "value_type": spec.value_type.value,
            "codec_id": spec.codec_id,
            "configured": _safe_value(spec.key, configured_value),
            "effective": _safe_value(spec.key, effective_value),
            "configured_state": "secret_set" if spec.is_secret and bool(configured_value) else ("secret_not_set" if spec.is_secret else "configured"),
            "secret_set": bool(configured_value) if spec.is_secret else False,
            "default": None if spec.is_secret else spec.default_new_install,
            "default_state": "set" if spec.is_secret and bool(spec.default_new_install) else ("not_set" if spec.is_secret else None),
            "minimum": spec.minimum,
            "maximum": spec.maximum,
            "unit": spec.unit,
            "options": [{"value": value, "label": label} for value, label in spec.options],
            "visibility": spec.visibility.value,
            "expert": spec.visibility is not Visibility.STANDARD,
            "protected": spec.visibility is Visibility.PROTECTED_EXPERT,
            "editable": editable,
            "available": available,
            "apply_class": spec.apply_class.value,
            "apply_text": spec.apply_text,
            "risk": spec.risk,
            "dependency_keys": list(spec.dependency_keys),
            "dependency_rule": DEPENDENCY_RULES.get(spec.key),
            "validation_text": spec.validation_text,
            "inherited_default": spec.key in inherited,
            "pending_restart": spec.key in pending,
            "configured_differs_effective": configured_value != effective_value,
            "issues": issue_by_key.get(spec.key, []),
            "config_key_visible": spec.visibility is not Visibility.STANDARD,
            "release_stage": spec.release_stage,
            "lifecycle": spec.lifecycle,
        }
        section["settings"].append(entry)
        category["setting_count"] += 1

    category_list = []
    for category in categories.values():
        category["sections"] = list(category["sections"].values())
        category_list.append(category)

    return {
        "schema": "ZEC-SETTINGS-MODEL-V1",
        "controller_version": manager.app_version,
        "csrf_token": csrf_token,
        "base_revision": getattr(manager, "cas_revision", manager.configured_revision)(),
        "configured_revision": manager.configured_revision(),
        "typed_revision": manager.typed_config_revision(),
        "effective_revision": manager.effective_revision(),
        "status": status,
        "categories": category_list,
        "global_issues": issue_by_key.get("__global__", []),
        "unknown_keys": sorted(key for key in configured if key not in SETTINGS_BY_KEY),
        "capabilities": {
            "preview_commit": True,
            "restart_action": bool(effective.get("WEB_SERVICE_RESTART_ENABLED", False)),
            "storage_probe": True,
            "last_good_pointer_repair": bool(status.get("last_good_store_repair_required")),
        },
        "runtime": {
            "current_mode": (state_snapshot or {}).get("current_mode"),
            "ready": (state_snapshot or {}).get("ready"),
            "battery_soc": (state_snapshot or {}).get("battery_soc"),
            "interval_seconds": effective.get("INTERVAL_SECONDS"),
        },
    }
