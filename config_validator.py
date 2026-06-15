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

    if not _str_value(cfg, "SHELLY_IP"):
        issues.append(_issue("ERROR", "Die Shelly-/Uni-Meter-IP darf nicht leer sein, weil die Netzleistung die zentrale Regelgröße ist.", ["SHELLY_IP"], "Netzwerk", "SHELLY_IP_MISSING"))
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
            issues.append(_issue("ERROR", "Das Datenquellen-Profil des Cross-Charge-Schutzes ist ungültig.", ["SECOND_BATTERY_SOURCE_PROFILE"], "Cross-Charge-Schutz", "SECOND_BATTERY_PROFILE_INVALID"))

        if not _str_value(cfg, "SECOND_BATTERY_DISPLAY_NAME"):
            issues.append(_issue("WARNING", "Der Anzeigename der Zusatzbatterie ist leer. Die Oberfläche verwendet dann technische Fallback-Bezeichnungen.", ["SECOND_BATTERY_DISPLAY_NAME"], "Cross-Charge-Schutz", "SECOND_BATTERY_NAME_EMPTY"))

        topics = second_battery_topics(cfg)
        if profile == PROFILE_EVCC_STANDARD:
            if not _str_value(cfg, "SECOND_BATTERY_EVCC_BASE_TOPIC"):
                issues.append(_issue("ERROR", "Der Cross-Charge-Schutz nutzt das Profil EVCC Standard, aber das EVCC Batterie-Basis-Topic ist leer.", ["CROSS_CHARGE_ENABLED", "SECOND_BATTERY_SOURCE_PROFILE", "SECOND_BATTERY_EVCC_BASE_TOPIC"], "Cross-Charge-Schutz", "SECOND_BATTERY_EVCC_BASE_TOPIC_MISSING"))
        else:
            if not topics.get("power"):
                issues.append(_issue("ERROR", "Der Cross-Charge-Schutz ist aktiv, aber im benutzerdefinierten Profil fehlt das Leistungs-Topic der Zusatzbatterie.", ["CROSS_CHARGE_ENABLED", "SECOND_BATTERY_SOURCE_PROFILE", "SECOND_BATTERY_POWER_TOPIC"], "Cross-Charge-Schutz", "SECOND_BATTERY_POWER_TOPIC_MISSING"))

            for kind, topic_key, payload_key, json_key, label in (
                ("power", "SECOND_BATTERY_POWER_TOPIC", "SECOND_BATTERY_POWER_PAYLOAD_TYPE", "SECOND_BATTERY_POWER_JSON_PATH", "Leistung"),
                ("soc", "SECOND_BATTERY_SOC_TOPIC", "SECOND_BATTERY_SOC_PAYLOAD_TYPE", "SECOND_BATTERY_SOC_JSON_PATH", "SOC"),
                ("capacity", "SECOND_BATTERY_CAPACITY_TOPIC", "SECOND_BATTERY_CAPACITY_PAYLOAD_TYPE", "SECOND_BATTERY_CAPACITY_JSON_PATH", "Kapazität"),
            ):
                topic_value = _str_value(cfg, topic_key)
                payload_type = _str_value(cfg, payload_key) or "number"
                json_path = _str_value(cfg, json_key)
                if payload_type not in {"number", "json"}:
                    issues.append(_issue("ERROR", f"Der Payload-Typ für {label} muss 'Zahl direkt' oder 'JSON mit Feldpfad' sein.", [payload_key], "Cross-Charge-Schutz", f"SECOND_BATTERY_{kind.upper()}_PAYLOAD_TYPE_INVALID"))
                if topic_value and payload_type == "json" and not json_path:
                    issues.append(_issue("ERROR", f"Für {label} ist JSON-Payload gewählt, aber der JSON-Feldpfad ist leer.", [topic_key, payload_key, json_key], "Cross-Charge-Schutz", f"SECOND_BATTERY_{kind.upper()}_JSON_PATH_MISSING"))

        power_unit = _str_value(cfg, "SECOND_BATTERY_POWER_UNIT") or "W"
        capacity_unit = _str_value(cfg, "SECOND_BATTERY_CAPACITY_UNIT") or "kWh"
        if power_unit not in {"W", "kW"}:
            issues.append(_issue("ERROR", "Die Leistungseinheit der Zusatzbatterie muss W oder kW sein.", ["SECOND_BATTERY_POWER_UNIT"], "Cross-Charge-Schutz", "SECOND_BATTERY_POWER_UNIT_INVALID"))
        if capacity_unit not in {"Wh", "kWh"}:
            issues.append(_issue("ERROR", "Die Kapazitätseinheit der Zusatzbatterie muss Wh oder kWh sein.", ["SECOND_BATTERY_CAPACITY_UNIT"], "Cross-Charge-Schutz", "SECOND_BATTERY_CAPACITY_UNIT_INVALID"))

        sign = _int_value(cfg, "SECOND_BATTERY_DISCHARGE_SIGN", 1)
        if sign not in (-1, 1):
            issues.append(_issue("ERROR", "Das Entlade-Vorzeichen der Zusatzbatterie muss entweder 1 oder -1 sein.", ["SECOND_BATTERY_DISCHARGE_SIGN"], "Cross-Charge-Schutz", "SECOND_BATTERY_SIGN_INVALID"))
        if _int_value(cfg, "SMA_DISCHARGE_BLOCK_W", 80) <= 0:
            issues.append(_issue("ERROR", "Die Entlade-Blockgrenze der Zusatzbatterie muss größer als 0 Watt sein.", ["SMA_DISCHARGE_BLOCK_W"], "Cross-Charge-Schutz", "SMA_BLOCK_ZERO"))
        if _int_value(cfg, "SECOND_BATTERY_STALE_TIMEOUT_SECONDS", 30) < 5:
            issues.append(_issue("WARNING", "Ein sehr kurzer Daten-Timeout kann bei kurzen MQTT-Pausen unnötig schnell zur Blockierung der Zendure-Ladung führen.", ["SECOND_BATTERY_STALE_TIMEOUT_SECONDS"], "Cross-Charge-Schutz", "SECOND_BATTERY_TIMEOUT_LOW"))
        if profile == PROFILE_CUSTOM and topics.get("soc") == "" and topics.get("capacity") == "":
            issues.append(_issue("INFO", "SOC- und Kapazitäts-Topic sind nicht konfiguriert. Der Cross-Charge-Schutz funktioniert weiterhin über die Leistungsmessung; Status- und Diagnoseanzeige bleiben für diese Zusatzwerte leer.", ["SECOND_BATTERY_SOC_TOPIC", "SECOND_BATTERY_CAPACITY_TOPIC"], "Cross-Charge-Schutz", "SECOND_BATTERY_OPTIONAL_VALUES_EMPTY"))

    # Night mode.
    if _bool_value(cfg.get("NIGHT_DISCHARGE_ENABLED", False)):
        night_power = _int_value(cfg, "NIGHT_DISCHARGE_POWER_W", 0)
        if night_power <= 0:
            issues.append(_issue("ERROR", "Die Nachtleistung muss bei aktivem Nachtmodus größer als 0 Watt sein.", ["NIGHT_DISCHARGE_POWER_W", "NIGHT_DISCHARGE_ENABLED"], "Nachtmodus", "NIGHT_POWER_ZERO"))
        if night_power > max_discharge:
            issues.append(_issue("ERROR", "Die Nachtleistung darf nicht größer sein als die maximale Zendure-Entladeleistung.", ["NIGHT_DISCHARGE_POWER_W", "MAX_DISCHARGE_POWER_W"], "Nachtmodus", "NIGHT_POWER_TOO_HIGH"))

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
