# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from config_manager import CONFIG_SCHEMA
from settings_registry import SETTINGS, SETTINGS_BY_KEY, Visibility, ApplyClass, Editability, DefaultClass, ResetPolicy
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

# UI-only ordering and reset/default semantics. These rules never change runtime
# defaults or effective values; they only control presentation and safe reset actions.
SECTION_ORDER_OVERRIDES = {
    "Betriebsart & manuelle Steuerung": ("Betriebsart", "Profil Feste Entladung", "Profil Feste Ladung"),
    "Nachtbetrieb": ("Aktivierung", "Zeitfenster", "Feste Basisentladung", "Reserve & Folgeverhalten"),
    "Harvest / Restüberschuss": ("Master & Zielbild", "High-SOC & Vollspeicher", "Entry & Hysterese", "Near-Limit-Entry", "Primärspeicher-Schwellen", "Tageszeitprofil"),
    "Messdaten & Speicherung": ("Measurement-V4", "Speicherziel", "CSV-Messdaten & Rotation", "Schreibstrategie", "Speicherschutz", "Fallback", "SQLite-Graphstore", "SQLite-Graphspeicher", "SQLite-Retention", "Tageskurve & RAM-Historie", "V4-Archivpflege", "V4-Manifest & I/O", "Legacy-Kompatibilität"),
    "Schnittstellen & Datenquellen": ("MQTT-Verbindung", "Netzleistung · aktive Quelle", "Netzleistung · Shelly-kompatibel", "Netzleistung · SMA Direkt", "Netzleistung · SMA Diagnose", "MQTT-Diagnose", "Zendure Local API", "Zendure Local API · Timeouts"),
    "System & Diagnose": ("Darstellung", "Runtime-Logging", "Runtime-Logging · Detailkanäle", "Safe-State & Datenqualität", "Zendure MQTT-Datenqualität", "Analyse-/Replay-Service", "Webserver & Zugriff", "Administrative Aktionen"),
}

SETTING_ORDER_OVERRIDES = {
    "MANUAL_FIXED_DISCHARGE_POWER_W": 10, "MANUAL_FIXED_DISCHARGE_TARGET_SOC": 20, "MANUAL_DISCHARGE_AFTER_TARGET": 30,
    "MANUAL_FIXED_CHARGE_POWER_W": 10, "MANUAL_FIXED_CHARGE_TARGET_SOC": 20, "MANUAL_CHARGE_AFTER_TARGET": 30,
    "MIN_SOC_PERCENT": 10, "MAX_SOC_PERCENT": 20,
    "NIGHT_START_HOUR": 10, "NIGHT_START_MINUTE": 11, "NIGHT_END_HOUR": 20, "NIGHT_END_MINUTE": 21,
    "REST_SURPLUS_HARVEST_ENABLED": 1,
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO": 10, "HARVEST_PRIMARY_CHARGE_FLOOR_W": 11,
    "HARVEST_PRIMARY_CHARGE_RESTART_RATIO": 20, "HARVEST_PRIMARY_CHARGE_RESTART_W": 21,
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO": 30, "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W": 31,
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING": 10, "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY": 20, "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON": 30,
    "MEASUREMENT_LOG_MODE": 1, "MEASUREMENT_LOG_FILE": 2,
    "MEASUREMENT_LOG_STORAGE_TARGET": 1, "MEASUREMENT_LOG_DIR": 2, "MEASUREMENT_LOG_MOUNTPOINT": 3,
    "MQTT_BROKER": 10, "MQTT_PORT": 20, "MQTT_USER": 30, "MQTT_PASSWORD": 40,
    "GRID_METER_SOURCE": 1,
    "ZENDURE_LOCAL_API_ENABLED": 10, "ZENDURE_LOCAL_IP": 20, "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": 30,
    "ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY": 40, "ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS": 50,
    "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": 60, "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": 70,
    "ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS": 80, "ZENDURE_LOCAL_API_SOC_PRIORITY": 90,
    "FILE_LOG_ENABLED": 10, "FILE_LOG_DIR": 20, "FILE_LOG_FILE": 30, "FILE_LOG_MAX_BYTES": 40, "FILE_LOG_BACKUP_COUNT": 50,
}

LABEL_OVERRIDES = {
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS": "High-SOC Eintritt bestätigen",
    "HARVEST_HIGH_SMA_SOC_HOLD_SECONDS": "High-SOC Haltezeit",
    "HARVEST_HIGH_SMA_SOC_ENABLED": "High-SOC Parallel-Harvest aktiv",
    "HARVEST_HIGH_SMA_SOC_ENTER_PERCENT": "High-SOC Eintritt",
    "HARVEST_HIGH_SMA_SOC_EXIT_PERCENT": "High-SOC Austritt",
    "HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W": "Mindestexport für High-SOC Eintritt",
    "HARVEST_SMA_FULL_SOC_PERCENT": "SMA Voll-SOC Schwelle",
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": "Near-Limit Eintritt bestätigen",
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO": "Primärspeicher Mindestladeanteil",
    "HARVEST_PRIMARY_CHARGE_FLOOR_W": "Primärspeicher Mindestladeleistung (Override)",
    "HARVEST_PRIMARY_CHARGE_RESTART_RATIO": "Primärspeicher Wiederanlaufanteil",
    "HARVEST_PRIMARY_CHARGE_RESTART_W": "Primärspeicher Wiederanlaufleistung (Override)",
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO": "Primärspeicher Near-Limit Anteil",
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W": "Primärspeicher Near-Limit Leistung (Override)",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING": "SMA-Zielanteil morgens",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY": "SMA-Zielanteil mittags",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON": "SMA-Zielanteil nachmittags",
    "SOC_DAY_GRAPH_BOOTSTRAP_CACHE_SECONDS": "SOC-Tagesgraph Bootstrap-Cache",
    "WEB_HOST": "Webserver Bind-Adresse",
}

def _format_default_value(value: Any, unit: Optional[str]) -> str:
    if value is None:
        return "nicht gesetzt"
    if isinstance(value, bool):
        text = "Ein" if value else "Aus"
    else:
        text = str(value)
    return f"{text}{f' {unit}' if unit else ''}"


def _default_ui_policy(spec: Any) -> Dict[str, Any]:
    if spec.is_secret or spec.editability is not Editability.EDITABLE:
        return {"kind": "none", "meta": spec.default_help if not spec.is_secret else "", "action": None}
    kind = spec.default_class
    if kind is DefaultClass.INSTALLATION:
        return {"kind": "installation", "meta": spec.default_help, "action": None}
    if kind is DefaultClass.LEGACY_INTERNAL:
        return {"kind": "none", "meta": spec.default_help, "action": None}
    if kind is DefaultClass.AUTO_OR_UNSET:
        return {"kind": "auto" if spec.reset_policy is ResetPolicy.AUTO else "clear", "meta": spec.default_help, "action": spec.reset_label, "value": spec.reset_value}
    if kind is DefaultClass.PROFILE_PRESET:
        profile = {"EVCC_STANDARD":"EVCC Standard", "HARVEST_ZEC_STANDARD":"ZEC Standardstrategie", "MANUAL_PROFILE":"Manuelles Profil", "NIGHT_PROFILE":"ZEC Nachtprofil"}.get(spec.profile_id, spec.profile_id or "Profil")
        return {"kind": "profile", "meta": f"Profilwert ({profile}): {_format_default_value(spec.reset_value, spec.unit)} · kein universeller Einzeldefault", "action": spec.reset_label, "value": spec.reset_value}
    if kind is DefaultClass.SAFE_SENTINEL:
        return {"kind": "sentinel", "meta": f"Sicherer Ausgangszustand: {_format_default_value(spec.bootstrap_value, spec.unit)} · kein empfohlener Betriebswert", "action": spec.reset_label, "value": spec.reset_value}
    return {"kind": "default", "meta": f"Produktdefault: {_format_default_value(spec.product_default, spec.unit)}", "action": spec.reset_label, "value": spec.reset_value}


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
            "label": LABEL_OVERRIDES.get(spec.key, spec.label),
            "description": _description(spec.key, spec),
            "value_type": spec.value_type.value,
            "codec_id": spec.codec_id,
            "configured": _safe_value(spec.key, configured_value),
            "effective": _safe_value(spec.key, effective_value),
            "configured_state": "secret_set" if spec.is_secret and bool(configured_value) else ("secret_not_set" if spec.is_secret else "configured"),
            "secret_set": bool(configured_value) if spec.is_secret else False,
            "default": None if spec.is_secret or spec.reset_policy is ResetPolicy.NONE else spec.reset_value,
            "bootstrap_value": None if spec.is_secret else spec.bootstrap_value,
            "product_default": None if spec.is_secret else spec.product_default,
            "default_class": spec.default_class.value,
            "reset_policy": spec.reset_policy.value,
            "required_first_install": spec.required_first_install,
            "profile_id": spec.profile_id,
            "default_ui": _default_ui_policy(spec),
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
            "ui_order": SETTING_ORDER_OVERRIDES.get(spec.key, 10000 + spec.order),
            "lifecycle": spec.lifecycle,
        }
        section["settings"].append(entry)
        category["setting_count"] += 1

    category_list = []
    for category in categories.values():
        section_order = {name: idx for idx, name in enumerate(SECTION_ORDER_OVERRIDES.get(category["name"], ()), start=1)}
        sections = list(category["sections"].values())
        for section in sections:
            section["settings"].sort(key=lambda item: (item.get("ui_order", 10000), item.get("key", "")))
        sections.sort(key=lambda section: (section_order.get(section["name"], 10000), section["name"]))
        for section in sections:
            for item in section["settings"]:
                item.pop("ui_order", None)
        category["sections"] = sections
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
