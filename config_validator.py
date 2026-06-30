# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""Central semantic validation for Zendure Energy Controller configuration.

The generic config_manager module coerces types and clamps basic numeric ranges.
This module performs cross-field and environment checks that decide whether a
configuration is safe and operationally plausible.

Severity model:
- ERROR:   saving must be blocked in the web UI.
- WARNING: saving is allowed after explicit acknowledgement.
- INFO:    informational note only.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

import requests

from cross_charge import PROFILE_CUSTOM, PROFILE_EVCC_STANDARD, cross_charge_enabled, second_battery_topics


@dataclass
class ValidationIssue:
    severity: str
    message: str
    keys: Set[str] = field(default_factory=set)
    group: str = ""
    code: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "message": self.message,
            "keys": sorted(self.keys),
            "group": self.group,
            "code": self.code,
        }


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "checked"}
    return bool(value)


def _int_value(cfg: Dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(float(cfg.get(key, default)))
    except Exception:
        return default


def _optional_int_value(cfg: Dict[str, Any], key: str) -> Optional[int]:
    value = cfg.get(key)
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _float_value(cfg: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(cfg.get(key, default))
    except Exception:
        return default


def _str_value(cfg: Dict[str, Any], key: str) -> str:
    return "" if cfg.get(key) is None else str(cfg.get(key)).strip()


def _issue(severity: str, message: str, keys: Iterable[str], group: str, code: str) -> ValidationIssue:
    return ValidationIssue(severity=severity, message=message, keys=set(keys), group=group, code=code)


def _path_is_writable(path: str, base_dir: Optional[str] = None) -> bool:
    if not path:
        return False
    check_path = path if os.path.isabs(path) else os.path.abspath(os.path.join(base_dir or os.getcwd(), path))
    try:
        os.makedirs(check_path, exist_ok=True)
        probe = os.path.join(check_path, ".zendure_write_test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def _detected_writable_external_mountpoint() -> str:
    try:
        from csv_logger import detected_log_mounts
        chosen = next((m for m in detected_log_mounts() if m.get("writable")), None)
        return str(chosen.get("mountpoint") or "") if chosen else ""
    except Exception:
        return ""


def _measurement_external_target_dir(cfg: Dict[str, Any]) -> str:
    mountpoint = _str_value(cfg, "MEASUREMENT_LOG_MOUNTPOINT")
    if not (mountpoint and os.path.ismount(mountpoint) and os.access(mountpoint, os.W_OK)):
        mountpoint = _detected_writable_external_mountpoint()
    if not mountpoint:
        return ""
    subdir = _str_value(cfg, "MEASUREMENT_LOG_DIR") or "logs"
    subdir = subdir.lstrip(os.sep)
    return os.path.join(mountpoint, subdir)


RESTART_RELEVANT_KEYS = {
    "MQTT_BROKER",
    "MQTT_PORT",
    "MQTT_USER",
    "MQTT_PASSWORD",
    "DEVICE_ID",
    "WEB_HOST",
    "WEB_PORT",
    "MQTT_TOPIC_DIAGNOSTIC_ENABLED",
    "MQTT_TOPIC_DIAGNOSTIC_FILTER",
    "MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE",
    "MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT",
    "ZENDURE_LOCAL_IP",
    "ZENDURE_LOCAL_API_TIMEOUT_SECONDS",
    "CROSS_CHARGE_ENABLED",
    "SECOND_BATTERY_SOURCE_PROFILE",
    "SECOND_BATTERY_EVCC_BASE_TOPIC",
    "SECOND_BATTERY_POWER_TOPIC",
    "SECOND_BATTERY_SOC_TOPIC",
    "SECOND_BATTERY_CAPACITY_TOPIC",
    "SECOND_BATTERY_POWER_PAYLOAD_TYPE",
    "SECOND_BATTERY_SOC_PAYLOAD_TYPE",
    "SECOND_BATTERY_CAPACITY_PAYLOAD_TYPE",
    "SECOND_BATTERY_POWER_JSON_PATH",
    "SECOND_BATTERY_SOC_JSON_PATH",
    "SECOND_BATTERY_CAPACITY_JSON_PATH",
    "SECOND_BATTERY_POWER_UNIT",
    "SECOND_BATTERY_CAPACITY_UNIT",
}


def restart_relevant_changes(candidate: Dict[str, Any], current: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return keys whose changed value should trigger a service restart notice."""
    if not current:
        return []
    changed: List[str] = []
    for key in sorted(RESTART_RELEVANT_KEYS):
        if key in current and str(current.get(key)) != str(candidate.get(key)):
            changed.append(key)
    return changed


def validate_config_semantics(
    candidate: Dict[str, Any],
    current: Optional[Dict[str, Any]] = None,
    perform_live_checks: bool = False,
    base_dir: Optional[str] = None,
) -> List[ValidationIssue]:
    """Validate cross-field semantics for a candidate config.

    The function intentionally accepts raw form values as well as already coerced
    values. It returns issues with field keys so the web UI can highlight affected
    cards.
    """
    cfg = candidate or {}
    current = current or {}
    issues: List[ValidationIssue] = []

    # Network and local Zendure API.
    use_local_api = _bool_value(cfg.get("ZENDURE_LOCAL_API_USE_FOR_TELEMETRY", False))
    fallback_only = _bool_value(cfg.get("ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY", True))
    local_ip = _str_value(cfg, "ZENDURE_LOCAL_IP")

    if use_local_api and not fallback_only:
        if not local_ip:
            issues.append(_issue(
                "ERROR",
                "Die lokale Zendure-API ist als aktive Telemetriequelle konfiguriert, aber 'Zendure lokale IP' ist leer. Trage eine erreichbare IP der Zendure-Headunit ein oder aktiviere 'Zendure lokale API nur als Fallback'.",
                ["ZENDURE_LOCAL_API_USE_FOR_TELEMETRY", "ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY", "ZENDURE_LOCAL_IP"],
                "Netzwerk",
                "ZENDURE_LOCAL_API_IP_MISSING",
            ))
        elif perform_live_checks:
            timeout = max(1, min(_int_value(cfg, "ZENDURE_LOCAL_API_TIMEOUT_SECONDS", 5), 10))
            url = "http://{}/properties/report".format(local_ip)
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or ("properties" not in data and "packData" not in data):
                    issues.append(_issue(
                        "ERROR",
                        "Die lokale Zendure-API unter {} ist erreichbar, liefert aber keine erwartete properties/report-Antwort. Speichern wurde verhindert, weil diese Datenquelle als aktive Telemetriequelle verwendet würde.".format(url),
                        ["ZENDURE_LOCAL_IP", "ZENDURE_LOCAL_API_TIMEOUT_SECONDS"],
                        "Netzwerk",
                        "ZENDURE_LOCAL_API_INVALID_RESPONSE",
                    ))
            except Exception as exc:
                issues.append(_issue(
                    "ERROR",
                    "Die lokale Zendure-API unter {} konnte nicht erfolgreich abgefragt werden: {}. Speichern wurde verhindert, weil diese Datenquelle als aktive Telemetriequelle verwendet würde.".format(url, exc),
                    ["ZENDURE_LOCAL_IP", "ZENDURE_LOCAL_API_TIMEOUT_SECONDS"],
                    "Netzwerk",
                    "ZENDURE_LOCAL_API_UNREACHABLE",
                ))
    elif use_local_api and fallback_only and not local_ip:
        issues.append(_issue(
            "WARNING",
            "Die lokale Zendure-API ist als Telemetrie-Fallback aktiviert, aber 'Zendure lokale IP' ist leer. Der Controller kann weiter mit MQTT arbeiten, im Fehlerfall steht der API-Fallback jedoch nicht zur Verfügung.",
            ["ZENDURE_LOCAL_API_USE_FOR_TELEMETRY", "ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY", "ZENDURE_LOCAL_IP"],
            "Netzwerk",
            "ZENDURE_LOCAL_API_FALLBACK_WITHOUT_IP",
        ))

    control_timeout_cap = _float_value(cfg, "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS", 1.5)
    interval_for_timeout = _int_value(cfg, "INTERVAL_SECONDS", 3)
    if use_local_api and control_timeout_cap >= max(1.0, interval_for_timeout * 0.75):
        issues.append(_issue("WARNING", "Der Timeout-Cap der lokalen Zendure-API liegt nahe am Regelintervall. Langsame API-Antworten können einzelne Regelzyklen spürbar verlängern. Das ist eine Laufzeit-/Datenquellenwarnung; bitte Timeout und Regelintervall bewusst aufeinander abstimmen.", ["ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS", "INTERVAL_SECONDS"], "Netzwerk", "LOCAL_API_TIMEOUT_NEAR_INTERVAL"))


    local_api_timeout = _float_value(cfg, "ZENDURE_LOCAL_API_TIMEOUT_SECONDS", 5.0)
    if use_local_api and local_api_timeout >= max(1.0, float(interval_for_timeout)):
        issues.append(_issue("WARNING", "Der vollständige Timeout der lokalen Zendure-API ist größer oder gleich dem Regelintervall. Wenn die API im Regelpfad genutzt wird oder der Fallback anspringt, können einzelne Zyklen deutlich länger dauern.", ["ZENDURE_LOCAL_API_TIMEOUT_SECONDS", "INTERVAL_SECONDS"], "Netzwerk", "LOCAL_API_FULL_TIMEOUT_ABOVE_INTERVAL"))

    grid_source = str(cfg.get("GRID_METER_SOURCE", "shelly_http") or "shelly_http")
    if grid_source not in {"shelly_http", "sma_energy_meter_udp"}:
        issues.append(_issue("ERROR", "Die Netzleistungsquelle ist unbekannt. Bitte Shelly/UniMeter HTTP oder SMA Home Manager direkt auswählen.", ["GRID_METER_SOURCE"], "Netzwerk", "GRID_SOURCE_INVALID"))
    if grid_source == "shelly_http" and not _str_value(cfg, "SHELLY_IP"):
        issues.append(_issue("ERROR", "Die Shelly-/Uni-Meter-IP darf nicht leer sein, solange Shelly/UniMeter HTTP als Netzleistungsquelle verwendet wird.", ["SHELLY_IP", "GRID_METER_SOURCE"], "Netzwerk", "SHELLY_IP_MISSING"))
    if grid_source == "sma_energy_meter_udp":
        if not _str_value(cfg, "SMA_ENERGY_METER_GROUP"):
            issues.append(_issue("ERROR", "Für die direkte SMA-Netzleistungsquelle muss die Multicast-Gruppe konfiguriert sein, typischerweise 239.12.255.254.", ["SMA_ENERGY_METER_GROUP"], "Netzwerk", "SMA_ENERGY_METER_GROUP_MISSING"))
        if _int_value(cfg, "SMA_ENERGY_METER_PORT", 0) <= 0:
            issues.append(_issue("ERROR", "Für die direkte SMA-Netzleistungsquelle muss ein gültiger UDP-Port konfiguriert sein, typischerweise 9522.", ["SMA_ENERGY_METER_PORT"], "Netzwerk", "SMA_ENERGY_METER_PORT_INVALID"))
        issues.append(_issue("WARNING", "SMA Home Manager direkt ist als produktive Netzleistungsquelle ausgewählt. Bitte erst mehrere Stunden/Tage parallel gegen Shelly/UniMeter prüfen: Vorzeichen, Paketalter, Aussetzer und Regelverhalten.", ["GRID_METER_SOURCE"], "Netzwerk", "SMA_DIRECT_AS_CONTROL_SOURCE"))
    elif bool(cfg.get("SMA_ENERGY_METER_PASSIVE_ENABLED", False)):
        issues.append(_issue("INFO", "SMA Home Manager Direktdiagnose ist passiv aktiv. Die Regelung verwendet weiterhin die gewählte Netzleistungsquelle; die direkten SMA-Werte dienen zum Vergleich von Zuverlässigkeit, Vorzeichen und Paketalter.", ["SMA_ENERGY_METER_PASSIVE_ENABLED"], "Netzwerk", "SMA_DIRECT_PASSIVE_ENABLED"))
    if not _str_value(cfg, "MQTT_BROKER"):
        issues.append(_issue("ERROR", "Der MQTT-Broker darf nicht leer sein, weil Zendure-Steuerbefehle per MQTT gesendet werden.", ["MQTT_BROKER"], "Netzwerk", "MQTT_BROKER_MISSING"))
    if not _str_value(cfg, "DEVICE_ID"):
        issues.append(_issue("ERROR", "Die Zendure Device ID darf nicht leer sein, weil daraus die MQTT-Topics gebildet werden.", ["DEVICE_ID"], "Netzwerk", "DEVICE_ID_MISSING"))

    # Restart-relevant changes.
    changed_restart_keys = restart_relevant_changes(cfg, current)
    if changed_restart_keys:
        issues.append(_issue(
            "INFO",
            "Einige Änderungen betreffen MQTT-, Topic-, Webserver- oder lokale Infrastrukturparameter. Sie werden gespeichert; ein Neustart des Dienstes ist danach erforderlich oder dringend empfohlen, damit alle Verbindungen, Abonnements und Serverparameter sicher neu aufgebaut werden.",
            changed_restart_keys,
            "Netzwerk",
            "RESTART_REQUIRED_OR_RECOMMENDED",
        ))

    # SOC and rule limits.
    min_soc = _int_value(cfg, "MIN_SOC_PERCENT", 15)
    max_soc = _int_value(cfg, "MAX_SOC_PERCENT", 100)
    if min_soc >= max_soc:
        issues.append(_issue(
            "ERROR",
            "Der minimale Zendure-SOC muss kleiner als der maximale Zendure-SOC sein. Andernfalls kann der Regler Lade- und Entladegrenzen nicht eindeutig bewerten.",
            ["MIN_SOC_PERCENT", "MAX_SOC_PERCENT"],
            "Regelung",
            "SOC_LIMITS_INVALID",
        ))

    max_discharge = _int_value(cfg, "MAX_DISCHARGE_POWER_W", 0)
    max_charge = _int_value(cfg, "MAX_CHARGE_POWER_W", 0)
    if max_discharge <= 0:
        issues.append(_issue("ERROR", "Die maximale Entladeleistung muss größer als 0 Watt sein.", ["MAX_DISCHARGE_POWER_W"], "Regelung", "MAX_DISCHARGE_ZERO"))
    if max_charge <= 0:
        issues.append(_issue("ERROR", "Die maximale Ladeleistung muss größer als 0 Watt sein.", ["MAX_CHARGE_POWER_W"], "Regelung", "MAX_CHARGE_ZERO"))

    deadband = _int_value(cfg, "DEADBAND_W", 25)
    control_gain = _float_value(cfg, "CONTROL_GAIN", 0.30)
    max_step = _int_value(cfg, "MAX_POWER_STEP_W", 150)
    moving_avg = _int_value(cfg, "MOVING_AVERAGE_SAMPLES", 5)
    interval = _int_value(cfg, "INTERVAL_SECONDS", 2)
    smoothing = _float_value(cfg, "SMOOTHING_FACTOR", 0.25)

    if deadband < 20 and control_gain > 0.5 and max_step > 300:
        issues.append(_issue(
            "WARNING",
            "Die Regelparameter sind sehr aggressiv gewählt: kleine Totzone, hoher Control Gain und großer Power Step können zu nervösem Verhalten oder häufigen Moduswechseln führen.",
            ["DEADBAND_W", "CONTROL_GAIN", "MAX_POWER_STEP_W"],
            "Regelung",
            "AGGRESSIVE_CONTROL_PARAMS",
        ))
    if moving_avg > 30:
        issues.append(_issue(
            "WARNING",
            "Die Mittelwertbildung ist sehr hoch. Der Regler wird dadurch stark geglättet, reagiert aber deutlich träger auf Lastsprünge.",
            ["MOVING_AVERAGE_SAMPLES"],
            "Regelung",
            "MOVING_AVERAGE_HIGH",
        ))
    if interval <= 1 and moving_avg <= 2 and smoothing >= 0.8:
        issues.append(_issue(
            "WARNING",
            "Sehr kurzes Regelintervall, kaum Mittelwertbildung und hoher Smoothing Factor führen zu sehr schnellen Stellbefehlen. Bitte nur bewusst verwenden.",
            ["INTERVAL_SECONDS", "MOVING_AVERAGE_SAMPLES", "SMOOTHING_FACTOR"],
            "Regelung",
            "FAST_CONTROL_PARAMS",
        ))

    min_command_change = _int_value(cfg, "MIN_COMMAND_CHANGE_W", 50)
    if max_step > 0 and min_command_change > max_step:
        issues.append(_issue(
            "WARNING",
            "Die MQTT-Mindeständerung ist größer als die maximale Zielwertänderung pro Zyklus. Der Regler kann dadurch berechnete kleine Schritte häufig unterdrücken und deutlich träger wirken als erwartet.",
            ["MIN_COMMAND_CHANGE_W", "MAX_POWER_STEP_W"],
            "Regelung",
            "MIN_COMMAND_ABOVE_STEP",
        ))
    if deadband > 0 and min_command_change > deadband * 2:
        issues.append(_issue(
            "INFO",
            "Die MQTT-Mindeständerung ist deutlich größer als die normale Totzone. Das reduziert Kommandohäufigkeit, kann aber kleine Zielwertkorrekturen sichtbar verzögern.",
            ["MIN_COMMAND_CHANGE_W", "DEADBAND_W"],
            "Regelung",
            "MIN_COMMAND_HIGH_VS_DEADBAND",
        ))

    # Manual modes.
    manual_mode = _str_value(cfg, "MANUAL_MODE") or "AUTO"
    fixed_discharge_power = _int_value(cfg, "MANUAL_FIXED_DISCHARGE_POWER_W", 0)
    fixed_discharge_soc = _int_value(cfg, "MANUAL_FIXED_DISCHARGE_TARGET_SOC", min_soc)
    fixed_charge_power = _int_value(cfg, "MANUAL_FIXED_CHARGE_POWER_W", 0)
    fixed_charge_soc = _int_value(cfg, "MANUAL_FIXED_CHARGE_TARGET_SOC", max_soc)
    if fixed_discharge_power > max_discharge:
        issues.append(_issue("ERROR", "Die feste Entladeleistung darf nicht größer sein als die maximale Zendure-Entladeleistung.", ["MANUAL_FIXED_DISCHARGE_POWER_W", "MAX_DISCHARGE_POWER_W"], "Manueller Modus", "MANUAL_DISCHARGE_POWER_TOO_HIGH"))
    if fixed_charge_power > max_charge:
        issues.append(_issue("ERROR", "Die feste Ladeleistung darf nicht größer sein als die maximale Zendure-Ladeleistung.", ["MANUAL_FIXED_CHARGE_POWER_W", "MAX_CHARGE_POWER_W"], "Manueller Modus", "MANUAL_CHARGE_POWER_TOO_HIGH"))
    if fixed_discharge_soc < min_soc:
        issues.append(_issue("ERROR", "Der Ziel-SOC der festen Entladung darf nicht unter dem konfigurierten Min-SOC liegen.", ["MANUAL_FIXED_DISCHARGE_TARGET_SOC", "MIN_SOC_PERCENT"], "Manueller Modus", "MANUAL_DISCHARGE_SOC_TOO_LOW"))
    if fixed_charge_soc > max_soc:
        issues.append(_issue("ERROR", "Der Ziel-SOC der festen Beladung darf nicht über dem konfigurierten Max-SOC liegen.", ["MANUAL_FIXED_CHARGE_TARGET_SOC", "MAX_SOC_PERCENT"], "Manueller Modus", "MANUAL_CHARGE_SOC_TOO_HIGH"))
    if manual_mode == "STOP_HOLD":
        issues.append(_issue("WARNING", "Der manuelle Modus STOP/HOLD stoppt die automatische Regelung nach dem Speichern vollständig, bis wieder AUTO gewählt wird.", ["MANUAL_MODE"], "Manueller Modus", "MANUAL_STOP_HOLD_ACTIVE"))
    elif manual_mode in {"FIXED_DISCHARGE", "FIXED_CHARGE"}:
        issues.append(_issue("WARNING", "Ein fester manueller Lade-/Entlademodus übersteuert die automatische Netzleistungsregelung bis zum konfigurierten Ziel-SOC.", ["MANUAL_MODE"], "Manueller Modus", "MANUAL_FIXED_MODE_ACTIVE"))

    # Cross-Charge protection / external battery data source.
    if cross_charge_enabled(cfg):
        profile = _str_value(cfg, "SECOND_BATTERY_SOURCE_PROFILE") or PROFILE_EVCC_STANDARD
        if profile not in {PROFILE_EVCC_STANDARD, PROFILE_CUSTOM}:
            issues.append(_issue("ERROR", "Das Datenquellen-Profil der Zweitbatterie ist ungültig.", ["SECOND_BATTERY_SOURCE_PROFILE"], "Zweitbatterie", "SECOND_BATTERY_PROFILE_INVALID"))

        if not _str_value(cfg, "SECOND_BATTERY_DISPLAY_NAME"):
            issues.append(_issue("WARNING", "Der Anzeigename der Zusatzbatterie ist leer. Die Oberfläche verwendet dann technische Fallback-Bezeichnungen.", ["SECOND_BATTERY_DISPLAY_NAME"], "Zweitbatterie", "SECOND_BATTERY_NAME_EMPTY"))

        topics = second_battery_topics(cfg)
        if profile == PROFILE_EVCC_STANDARD:
            if not _str_value(cfg, "SECOND_BATTERY_EVCC_BASE_TOPIC"):
                issues.append(_issue("ERROR", "Die Zweitbatterie nutzt das Profil EVCC Standard, aber das EVCC Batterie-Basis-Topic ist leer.", ["CROSS_CHARGE_ENABLED", "SECOND_BATTERY_SOURCE_PROFILE", "SECOND_BATTERY_EVCC_BASE_TOPIC"], "Zweitbatterie", "SECOND_BATTERY_EVCC_BASE_TOPIC_MISSING"))
        else:
            if not topics.get("power"):
                issues.append(_issue("ERROR", "Die Zweitbatterie ist aktiv, aber im benutzerdefinierten Profil fehlt das Leistungs-Topic der Zusatzbatterie.", ["CROSS_CHARGE_ENABLED", "SECOND_BATTERY_SOURCE_PROFILE", "SECOND_BATTERY_POWER_TOPIC"], "Zweitbatterie", "SECOND_BATTERY_POWER_TOPIC_MISSING"))

            for kind, topic_key, payload_key, json_key, label in (
                ("power", "SECOND_BATTERY_POWER_TOPIC", "SECOND_BATTERY_POWER_PAYLOAD_TYPE", "SECOND_BATTERY_POWER_JSON_PATH", "Leistung"),
                ("soc", "SECOND_BATTERY_SOC_TOPIC", "SECOND_BATTERY_SOC_PAYLOAD_TYPE", "SECOND_BATTERY_SOC_JSON_PATH", "SOC"),
                ("capacity", "SECOND_BATTERY_CAPACITY_TOPIC", "SECOND_BATTERY_CAPACITY_PAYLOAD_TYPE", "SECOND_BATTERY_CAPACITY_JSON_PATH", "Kapazität"),
            ):
                topic_value = _str_value(cfg, topic_key)
                payload_type = _str_value(cfg, payload_key) or "number"
                json_path = _str_value(cfg, json_key)
                if payload_type not in {"number", "json"}:
                    issues.append(_issue("ERROR", f"Der Payload-Typ für {label} muss 'Zahl direkt' oder 'JSON mit Feldpfad' sein.", [payload_key], "Zweitbatterie", f"SECOND_BATTERY_{kind.upper()}_PAYLOAD_TYPE_INVALID"))
                if topic_value and payload_type == "json" and not json_path:
                    issues.append(_issue("ERROR", f"Für {label} ist JSON-Payload gewählt, aber der JSON-Feldpfad ist leer.", [topic_key, payload_key, json_key], "Zweitbatterie", f"SECOND_BATTERY_{kind.upper()}_JSON_PATH_MISSING"))

        power_unit = _str_value(cfg, "SECOND_BATTERY_POWER_UNIT") or "W"
        capacity_unit = _str_value(cfg, "SECOND_BATTERY_CAPACITY_UNIT") or "kWh"
        if power_unit not in {"W", "kW"}:
            issues.append(_issue("ERROR", "Die Leistungseinheit der Zusatzbatterie muss W oder kW sein.", ["SECOND_BATTERY_POWER_UNIT"], "Zweitbatterie", "SECOND_BATTERY_POWER_UNIT_INVALID"))
        if capacity_unit not in {"Wh", "kWh"}:
            issues.append(_issue("ERROR", "Die Kapazitätseinheit der Zusatzbatterie muss Wh oder kWh sein.", ["SECOND_BATTERY_CAPACITY_UNIT"], "Zweitbatterie", "SECOND_BATTERY_CAPACITY_UNIT_INVALID"))

        sign = _int_value(cfg, "SECOND_BATTERY_DISCHARGE_SIGN", 1)
        if sign not in (-1, 1):
            issues.append(_issue("ERROR", "Das Entlade-Vorzeichen der Zusatzbatterie muss entweder 1 oder -1 sein.", ["SECOND_BATTERY_DISCHARGE_SIGN"], "Zweitbatterie", "SECOND_BATTERY_SIGN_INVALID"))
        if _int_value(cfg, "SMA_DISCHARGE_BLOCK_W", 80) <= 0:
            issues.append(_issue("ERROR", "Die Entlade-Blockgrenze der Zusatzbatterie muss größer als 0 Watt sein.", ["SMA_DISCHARGE_BLOCK_W"], "Zweitbatterie", "SMA_BLOCK_ZERO"))
        if _int_value(cfg, "SECOND_BATTERY_STALE_TIMEOUT_SECONDS", 30) < 5:
            issues.append(_issue("WARNING", "Ein sehr kurzer Daten-Timeout kann bei kurzen MQTT-Pausen unnötig schnell zur Blockierung der Zendure-Ladung führen.", ["SECOND_BATTERY_STALE_TIMEOUT_SECONDS"], "Zweitbatterie", "SECOND_BATTERY_TIMEOUT_LOW"))
        if profile == PROFILE_CUSTOM and topics.get("soc") == "" and topics.get("capacity") == "":
            issues.append(_issue("INFO", "SOC- und Kapazitäts-Topic sind nicht konfiguriert. Die Zweitbatterie-Diagnose funktioniert weiterhin über die Leistungsmessung; Status- und Diagnoseanzeige bleiben für diese Zusatzwerte leer.", ["SECOND_BATTERY_SOC_TOPIC", "SECOND_BATTERY_CAPACITY_TOPIC"], "Zweitbatterie", "SECOND_BATTERY_OPTIONAL_VALUES_EMPTY"))

    # Restüberschuss-Ernte: harte Abhängigkeiten und verständliche Querhinweise.
    harvest_enabled = _bool_value(cfg.get("REST_SURPLUS_HARVEST_ENABLED", False))
    if harvest_enabled:
        max_primary_charge = _optional_int_value(cfg, "SECOND_BATTERY_MAX_CHARGE_POWER_W")
        min_export = _int_value(cfg, "REST_SURPLUS_MIN_EXPORT_W", 80)
        entry_confirm = _int_value(cfg, "REST_SURPLUS_ENTRY_CONFIRM_SECONDS", 30)
        margin = _int_value(cfg, "SECOND_BATTERY_CHARGE_SATURATION_MARGIN_W", 100)
        if max_primary_charge is None or max_primary_charge <= 0:
            issues.append(_issue("ERROR", "Restüberschuss-Ernte ist aktiv, aber die maximale Ladeleistung des Primärspeichers ist nicht konfiguriert oder nicht plausibel. Bitte in Settings → Zweitbatterie → Restüberschuss-Ernte die maximale Ladeleistung in Watt eintragen; ohne diesen Wert kann der Controller nicht erkennen, wann der Primärspeicher nahe seiner Ladegrenze arbeitet.", ["REST_SURPLUS_HARVEST_ENABLED", "SECOND_BATTERY_MAX_CHARGE_POWER_W"], "Zweitbatterie", "HARVEST_MAX_CHARGE_MISSING"))
        elif max_primary_charge < 300:
            issues.append(_issue("ERROR", "Die maximale Ladeleistung des Primärspeichers ist für die Restüberschuss-Ernte unplausibel niedrig. Trage den technischen Maximalwert des Primärspeichers in Watt ein.", ["SECOND_BATTERY_MAX_CHARGE_POWER_W"], "Zweitbatterie", "HARVEST_MAX_CHARGE_TOO_LOW"))
        elif max_primary_charge > 10000:
            issues.append(_issue("WARNING", "Die maximale Ladeleistung des Primärspeichers wirkt ungewöhnlich hoch. Bitte prüfen, ob der Wert in Watt und nicht versehentlich in einer anderen Einheit eingetragen wurde.", ["SECOND_BATTERY_MAX_CHARGE_POWER_W"], "Zweitbatterie", "HARVEST_MAX_CHARGE_HIGH"))
        if not cross_charge_enabled(cfg):
            issues.append(_issue("ERROR", "Restüberschuss-Ernte benötigt den Cross-Charge-Schutz. Wenn der Primärspeicher während einer Erntephase in Entladung kippt, muss Zendure-Ladung sicher reduziert oder blockiert werden können.", ["REST_SURPLUS_HARVEST_ENABLED", "CROSS_CHARGE_ENABLED"], "Zweitbatterie", "HARVEST_NEEDS_CROSS_CHARGE"))
        profile = _str_value(cfg, "SECOND_BATTERY_SOURCE_PROFILE") or PROFILE_EVCC_STANDARD
        topics = second_battery_topics(cfg)
        if profile == PROFILE_EVCC_STANDARD and not _str_value(cfg, "SECOND_BATTERY_EVCC_BASE_TOPIC"):
            issues.append(_issue("ERROR", "Restüberschuss-Ernte benötigt aktuelle Leistungsdaten der Zweitbatterie, aber das EVCC Batterie-Basis-Topic ist nicht konfiguriert. Bitte in Settings → Zweitbatterie → Zweitbatterie-Messwerte das EVCC-Basis-Topic eintragen.", ["REST_SURPLUS_HARVEST_ENABLED", "SECOND_BATTERY_EVCC_BASE_TOPIC"], "Zweitbatterie", "HARVEST_SECOND_BATTERY_TOPIC_MISSING"))
        if profile == PROFILE_CUSTOM and not topics.get("power"):
            issues.append(_issue("ERROR", "Restüberschuss-Ernte benötigt aktuelle Leistungsdaten der Zweitbatterie, aber im benutzerdefinierten Profil ist kein Leistungs-Topic konfiguriert. Bitte in Settings → Zweitbatterie → Zweitbatterie-Messwerte das Leistungs-Topic eintragen.", ["REST_SURPLUS_HARVEST_ENABLED", "SECOND_BATTERY_POWER_TOPIC"], "Zweitbatterie", "HARVEST_SECOND_BATTERY_POWER_TOPIC_MISSING"))
        if min_export <= 0:
            issues.append(_issue("ERROR", "Der Mindest-Netzexport für die Restüberschuss-Ernte muss größer als 0 W sein.", ["REST_SURPLUS_MIN_EXPORT_W"], "Zweitbatterie", "HARVEST_MIN_EXPORT_ZERO"))
        if entry_confirm < interval * 2:
            issues.append(_issue("WARNING", "Die Entry-Bestätigungszeit der Restüberschuss-Ernte ist sehr kurz. Kurze Wolkenlücken oder Lastspitzen könnten den Modus unnötig starten.", ["REST_SURPLUS_ENTRY_CONFIRM_SECONDS", "INTERVAL_SECONDS"], "Zweitbatterie", "HARVEST_ENTRY_CONFIRM_SHORT"))
        if entry_confirm > 180:
            issues.append(_issue("WARNING", "Die Entry-Bestätigungszeit der Restüberschuss-Ernte ist sehr lang. Kurze, wertvolle Überschussfenster können dadurch verpasst werden.", ["REST_SURPLUS_ENTRY_CONFIRM_SECONDS"], "Zweitbatterie", "HARVEST_ENTRY_CONFIRM_LONG"))
        if margin <= 0 or (max_primary_charge and margin >= max_primary_charge):
            issues.append(_issue("ERROR", "Die interne Marge zur Erkennung der Primärspeicher-Ladegrenze ist nicht plausibel. Sie muss größer als 0 W und kleiner als die maximale Ladeleistung des Primärspeichers sein.", ["SECOND_BATTERY_CHARGE_SATURATION_MARGIN_W", "SECOND_BATTERY_MAX_CHARGE_POWER_W"], "Zweitbatterie", "HARVEST_MARGIN_INVALID"))
        if min_command_change > min_export:
            issues.append(_issue("WARNING", "Die MQTT-Mindeständerung ist größer als der Mindest-Netzexport der Restüberschuss-Ernte. Die Funktion kann zwar aktiv werden, kleine Korrekturen werden aber möglicherweise durch die Mindeständerung unterdrückt.", ["MIN_COMMAND_CHANGE_W", "REST_SURPLUS_MIN_EXPORT_W"], "Zweitbatterie", "HARVEST_MIN_COMMAND_ABOVE_MIN_EXPORT"))
        if min_export < deadband:
            issues.append(_issue("INFO", "Der Mindest-Netzexport der Restüberschuss-Ernte liegt innerhalb der normalen Totzone. Das ist für diese Speziallage zulässig: Der Modus startet nur bei bestätigtem Primärspeicher-Ladelimit und darf dann bewusst feineren Restexport ernten.", ["REST_SURPLUS_MIN_EXPORT_W", "DEADBAND_W"], "Zweitbatterie", "HARVEST_EXPORT_BELOW_DEADBAND"))
        if max_step < min_export:
            issues.append(_issue("WARNING", "Die maximale Zielwertänderung pro Zyklus ist kleiner als der Mindest-Netzexport der Restüberschuss-Ernte. Zendure wird den Restüberschuss bewusst sehr langsam aufnehmen.", ["MAX_POWER_STEP_W", "REST_SURPLUS_MIN_EXPORT_W"], "Zweitbatterie", "HARVEST_STEP_SMALL"))
        if smoothing < 0.10 or interval >= 10:
            issues.append(_issue("INFO", "Die Restüberschuss-Ernte nutzt weiterhin Step-/Smoothing-Limits. Sehr kleine Glättungsfaktoren oder lange Regelintervalle machen Zendure bewusst träge und können kurze Überschussfenster teilweise verpassen.", ["SMOOTHING_FACTOR", "INTERVAL_SECONDS"], "Zweitbatterie", "HARVEST_SLOW_RESPONSE"))

    # Night mode.
    if _bool_value(cfg.get("NIGHT_DISCHARGE_ENABLED", False)):
        night_power = _int_value(cfg, "NIGHT_DISCHARGE_POWER_W", 0)
        if night_power <= 0:
            issues.append(_issue("ERROR", "Die Nachtentladeleistung ist in Settings → Nachtmodus nicht plausibel. Bitte bei aktivem Nachtmodus einen Wert größer als 0 W eintragen.", ["NIGHT_DISCHARGE_POWER_W", "NIGHT_DISCHARGE_ENABLED"], "Nachtmodus", "NIGHT_POWER_ZERO"))
        if night_power > max_discharge:
            issues.append(_issue("ERROR", "Die Nachtentladeleistung ist höher als die maximale Zendure-Entladeleistung. Bitte in Settings → Nachtmodus oder Settings → Regelung prüfen.", ["NIGHT_DISCHARGE_POWER_W", "MAX_DISCHARGE_POWER_W"], "Nachtmodus", "NIGHT_POWER_TOO_HIGH"))

        capacity_wh = _optional_int_value(cfg, "ZENDURE_BATTERY_CAPACITY_WH")
        if capacity_wh is None:
            issues.append(_issue("INFO", "Die Nachtmodus-Prognose ist nicht verfügbar, weil die Zendure-Batteriekapazität für die Prognose nicht konfiguriert ist. Bitte in Settings → Nachtmodus eintragen, wenn die Statusseite ein voraussichtliches Nachtmodus-Ende berechnen soll.", ["ZENDURE_BATTERY_CAPACITY_WH"], "Nachtmodus", "NIGHT_PROJECTION_CAPACITY_MISSING"))
        elif capacity_wh <= 0 or capacity_wh > 50000:
            issues.append(_issue("WARNING", "Die Zendure-Batteriekapazität für die Nachtmodus-Prognose ist nicht plausibel. Bitte in Settings → Nachtmodus einen realistischen Wh-Wert prüfen.", ["ZENDURE_BATTERY_CAPACITY_WH"], "Nachtmodus", "NIGHT_PROJECTION_CAPACITY_IMPLAUSIBLE"))

        night_stop_soc = _optional_int_value(cfg, "NIGHT_DISCHARGE_STOP_SOC_PERCENT")
        if night_stop_soc is not None and night_stop_soc < min_soc:
            issues.append(_issue("ERROR", "Der Nachtmodus Reserve-SOC darf nicht unter dem globalen Mindest-SOC liegen.", ["NIGHT_DISCHARGE_STOP_SOC_PERCENT", "MIN_SOC_PERCENT"], "Nachtmodus", "NIGHT_STOP_SOC_BELOW_MIN_SOC"))
        if night_stop_soc is not None and night_stop_soc > max_soc:
            issues.append(_issue("WARNING", "Der Nachtmodus Reserve-SOC liegt oberhalb des maximalen Lade-SOC. Das ist technisch möglich, führt aber dazu, dass die Nachtentladung sehr früh oder gar nicht startet.", ["NIGHT_DISCHARGE_STOP_SOC_PERCENT", "MAX_SOC_PERCENT"], "Nachtmodus", "NIGHT_STOP_SOC_ABOVE_MAX_SOC"))

    # Safety / fallback.
    if _int_value(cfg, "MAX_CONSECUTIVE_ERRORS", 5) <= 0:
        issues.append(_issue("ERROR", "Max Fehler in Folge muss größer als 0 sein.", ["MAX_CONSECUTIVE_ERRORS"], "Sicherheit / Fallback", "MAX_ERRORS_ZERO"))
    if _int_value(cfg, "SOC_STALE_TIMEOUT_SECONDS", 90) < _int_value(cfg, "INTERVAL_SECONDS", 2) * 2:
        issues.append(_issue("WARNING", "Der SOC Timeout ist sehr kurz im Verhältnis zum Regelintervall. Kurze MQTT-Pausen können dadurch schneller Safe-State auslösen.", ["SOC_STALE_TIMEOUT_SECONDS", "INTERVAL_SECONDS"], "Sicherheit / Fallback", "SOC_TIMEOUT_LOW"))

    # File system checks. Messdaten-Logging ist nachgelagert; Validierung soll
    # Fehlkonfigurationen sichtbar machen, aber die Regelung selbst hängt nie am Logging.
    measurement_mode = _str_value(cfg, "MEASUREMENT_LOG_MODE") or "off"
    if measurement_mode not in {"off", "standard", "extended"}:
        issues.append(_issue("ERROR", "Der Messdaten-Logging-Modus muss Aus, Standard oder Erweitert sein.", ["MEASUREMENT_LOG_MODE"], "Messdaten / Historie", "MEASUREMENT_LOG_MODE_INVALID"))
    if measurement_mode != "off":
        storage_target = _str_value(cfg, "MEASUREMENT_LOG_STORAGE_TARGET") or "internal_sd"
        allow_fallback = _bool_value(cfg.get("MEASUREMENT_LOG_ALLOW_SD_FALLBACK", True))
        if storage_target == "external_mount":
            target_dir = _measurement_external_target_dir(cfg)
            mount_ok = bool(target_dir) and _path_is_writable(target_dir, base_dir=base_dir)
            fallback_ok = allow_fallback and _path_is_writable(_str_value(cfg, "MEASUREMENT_LOG_FALLBACK_DIR"), base_dir=base_dir)
            if not mount_ok and not fallback_ok:
                issues.append(_issue("ERROR", "Externes Messdatenziel ist nicht verfügbar und der SD-Fallback ist nicht beschreibbar.", ["MEASUREMENT_LOG_STORAGE_TARGET", "MEASUREMENT_LOG_MOUNTPOINT", "MEASUREMENT_LOG_FALLBACK_DIR"], "Messdaten / Historie", "MEASUREMENT_LOG_TARGET_UNAVAILABLE"))
            elif not mount_ok and fallback_ok:
                issues.append(_issue("WARNING", "Externes Messdatenziel ist aktuell nicht als beschreibbarer Mountpoint verfügbar. Nach dem Speichern würde der begrenzte SD-Fallback verwendet.", ["MEASUREMENT_LOG_STORAGE_TARGET", "MEASUREMENT_LOG_MOUNTPOINT"], "Messdaten / Historie", "MEASUREMENT_LOG_EXTERNAL_FALLBACK"))
        else:
            if not _path_is_writable(_str_value(cfg, "MEASUREMENT_LOG_DIR"), base_dir=base_dir):
                issues.append(_issue("ERROR", "Messdaten-Logging ist aktiv, aber das Messdaten-Verzeichnis ist nicht beschreibbar.", ["MEASUREMENT_LOG_MODE", "MEASUREMENT_LOG_DIR"], "Messdaten / Historie", "MEASUREMENT_LOG_DIR_NOT_WRITABLE"))
        if measurement_mode == "extended":
            issues.append(_issue("INFO", "Erweitertes Messdaten-Logging erzeugt größere Dateien. Es ist für gezielte Simulation, What-if und tiefe MQTT-/Freshness-Analyse gedacht, nicht zwingend für Dauerbetrieb.", ["MEASUREMENT_LOG_MODE"], "Messdaten / Historie", "MEASUREMENT_LOG_EXTENDED_VOLUME"))
    if _bool_value(cfg.get("FILE_LOG_ENABLED", False)):
        if not _path_is_writable(_str_value(cfg, "FILE_LOG_DIR"), base_dir=base_dir):
            issues.append(_issue("ERROR", "Datei-Logging ist aktiv, aber das Runtime-Log-Verzeichnis ist nicht beschreibbar.", ["FILE_LOG_ENABLED", "FILE_LOG_DIR"], "Logging", "FILE_LOG_DIR_NOT_WRITABLE"))

    if _bool_value(cfg.get("HEADLESS_MODE", False)):
        issues.append(_issue("WARNING", "Headless Mode ist aktiv. Nach dem Speichern werden die Weboberflächen durch eine Hinweisseite ersetzt; Änderungen erfolgen dann über config.json oder durch Deaktivierung des Headless Mode in der Datei.", ["HEADLESS_MODE"], "Netzwerk", "HEADLESS_ACTIVE"))

    return issues


def split_issues(issues: Iterable[ValidationIssue]) -> Dict[str, List[ValidationIssue]]:
    buckets = {"ERROR": [], "WARNING": [], "INFO": []}
    for issue in issues:
        severity = issue.severity.upper()
        buckets.setdefault(severity, []).append(issue)
    return buckets
