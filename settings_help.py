# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# V12.12.1 registry-native help/guidance metadata.  This module is deliberately
# static: opening help never performs I/O, network access or controller work.

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple
from settings_help_v1712 import WHEN as WHEN_V1712, FAST_CAPTURE_PLAIN


@dataclass(frozen=True)
class HandbookRef:
    section_id: str
    section_title: str
    page: int


@dataclass(frozen=True)
class HelpDependency:
    relation: str
    key: str
    text: Optional[str] = None


@dataclass(frozen=True)
class HelpExample:
    title: str
    inputs: Tuple[str, ...]
    calculation: str
    result: str
    interpretation: str


@dataclass(frozen=True)
class SettingHelpSpec:
    short_help: str
    extended_help: str
    when_help: Optional[str]
    help_level: str
    search_terms: Tuple[str, ...]
    handbook_ref: Optional[HandbookRef]
    effect_increase: Optional[str] = None
    effect_decrease: Optional[str] = None
    effect_enable: Optional[str] = None
    effect_disable: Optional[str] = None
    option_help: Tuple[Tuple[str, str], ...] = ()
    dependencies: Tuple[HelpDependency, ...] = ()
    dependency_help: Optional[str] = None
    override_help: Optional[str] = None
    risk_help: Optional[str] = None
    example: Optional[HelpExample] = None
    formula_text: Optional[str] = None
    guidance_rule_ids: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CategorySpec:
    name: str
    group: str
    description: str
    help_text: str
    handbook_ref: Optional[HandbookRef]


@dataclass(frozen=True)
class SectionSpec:
    category: str
    name: str
    help_text: str
    handbook_ref: Optional[HandbookRef]


RICH_CATEGORIES = frozenset({
    "Betriebsart & manuelle Steuerung",
    "Leistungsgrenzen & SOC-Schutz",
    "AUTO-Regelung",
    "Nachtbetrieb",
    "Harvest / Restüberschuss",
    "Cross-Charge-Schutz",
    "Kommandowirkung & Resync",
})

CATEGORY_GROUPS = {
    "Betriebsart & manuelle Steuerung": "A. Betrieb",
    "Nachtbetrieb": "A. Betrieb",
    "Leistungsgrenzen & SOC-Schutz": "A. Betrieb",
    "AUTO-Regelung": "B. Regelung & Speicherstrategie",
    "Harvest / Restüberschuss": "B. Regelung & Speicherstrategie",
    "Primärspeicher": "B. Regelung & Speicherstrategie",
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
    "Primärspeicher": "Integration, Datenmodell und Ladeleistungsgrenzen des Primärspeichers.",
    "Cross-Charge-Schutz": "Verhindert unerwünschtes Umladen zwischen den Speichern.",
    "Kommandowirkung & Resync": "Command-State, Wirksamkeitsprüfung, Neutralisierung und Recovery.",
    "Zendure-Geräte": "Zendure-Gerät und anlagenbezogene Geräteparameter.",
    "Schnittstellen & Datenquellen": "MQTT, Netzleistungsquelle und externe Datenpfade.",
    "Messdaten & Speicherung": "Measurement V4, SQLite-Graphstore und Speicherschutz.",
    "System & Diagnose": "Webserver, Darstellung, Logging, Analyse und Sicherheitsfallbacks.",
}

CATEGORY_HELP_TEXT = {
    "Betriebsart & manuelle Steuerung": "AUTO nutzt die normale Netzleistungsregelung. STOP/HOLD und feste manuelle Modi haben Vorrang vor AUTO; ein manueller Modus ungleich AUTO verhindert den Nachtmodus im betreffenden Zyklus. Feste Lade- und Entlademodi arbeiten mit festen Leistungszielen bis zum Ziel-SOC. Safe-State sowie harte SOC- und Gerätegrenzen behalten immer Vorrang.",
    "Leistungsgrenzen & SOC-Schutz": "Lade-/Entladegrenzen sowie MIN/MAX-SOC sind anlagen- und geräteabhängige Schutzwerte. Sie begrenzen auch manuelle, Nacht- und AUTO-Ziele. Diese Werte sind keine universellen Empfehlungen und müssen zur konkreten Hardware passen.",
    "AUTO-Regelung": "ZEC bildet aus dem Netzbezug beziehungsweise der Netzeinspeisung eine passende Lade- oder Entladeanforderung. Mittelwert und Totzone beruhigen Messschwankungen; Verstärkung und Glättung bestimmen die Reaktion, danach begrenzt die maximale Änderung je Regelzyklus gewöhnliche Zielwertsprünge. Die Mindeständerung für Gerätebefehle kommt erst beim Versand hinzu. Fast Capture darf nur in besonders bestätigten Fällen einen zusätzlich begrenzten Ladeanteil ergänzen. Mehr Tempo ist nicht automatisch sicherer oder besser.",
    "Nachtbetrieb": "Der Nachtmodus erzeugt eine feste Basisentladung und ist keine netzleistungsnachgeführte AUTO-Entladung. Start und Ende dürfen über Mitternacht laufen. Eine optionale Nachtreserve pausiert die feste Basisentladung; globale MIN-SOC-Grenzen und aktive 0-W-Neutralisierung beim Exit bleiben Schutzinvarianten.",
    "Primärspeicher": "Die Primärspeicher-Anbindung kann über EVCC, benutzerdefiniertes MQTT oder ein geprüftes read-only Modbus-Geräteprofil erfolgen. Nach Auswahl einer Quelle zeigt ZEC unmittelbar die dafür relevanten Verbindungsparameter. Vorzeichen-, Einheits- und Freshness-Semantik bleiben quellenneutral und sicherheitsrelevant.",
    "Harvest / Restüberschuss": "Der Primärspeicher hat grundsätzlich Vorrang. Wenn am Hausanschluss trotzdem tatsächlich nutzbarer PV-Überschuss eingespeist würde, darf Zendure diesen innerhalb seiner Grenzen aufnehmen. Einschalt-, Wiederanlauf- und Nahe-Maximum-Schwellen legen fest, wann bestimmte zusätzliche Ladewege überhaupt zugelassen sind; absolute Wattwerte ersetzen jeweils den passenden Prozentanteil. Die Saison-/Tagesstrategie verteilt nur geeignete Leistung, sie sperrt keine notwendige Restüberschussaufnahme. Netzwerte sind keine unveränderten festen Gerätezielwerte.",
    "Cross-Charge-Schutz": "Cross-Charge wird symmetrisch behandelt. Gegenläufiger Zendure-Sollwert wird proportional reduziert, aber der Schutz kehrt die Richtung nicht selbstständig um. Frische Zweitbatteriedaten sind erforderlich; Sollwertkonflikt und tatsächlich beobachteter Gegenfluss bleiben getrennte Sachverhalte.",
    "Kommandowirkung & Resync": "Das Senden (Publish) eines Gerätebefehls beweist noch keine tatsächliche Lade- oder Entladeleistung. ZEC prüft getrennt, ob das Gerät die Richtung übernimmt, wie genau die Leistung folgt und ob sich der Netzbezug verbessert. Auch das sichere Zurücknehmen auf null Watt muss bestätigt werden. Wiederabgleich-Zeiten betreffen Fehlerbehandlung und nicht die Geschwindigkeit der normalen AUTO-Regelung.",
    "Zendure-Geräte": "Geräte-ID und Batteriekapazität sind installationsabhängig. Unbekannte Hardwarewerte werden nicht erfunden; Kapazität dient vor allem Prognose und Diagnose.",
    "Schnittstellen & Datenquellen": "MQTT überträgt Zendure-Gerätedaten und zulässige Leistungsanforderungen. Für die Hausnetzleistung wird entweder SMA Energy Meter/Sunny Home Manager direkt oder ein Shelly-kompatibler HTTP-Zähler gewählt. Die jeweils passende Adresse, Gerätekennung und Aktualitätsgrenze sind Voraussetzung; ein passiv beobachteter Zähler ersetzt nicht die aktive Quelle. Lokale Zendure-Geräteabfragen können ergänzende Diagnose beziehungsweise ausdrücklich zugelassene Ersatzwerte liefern, aber keinen zweiten Regler.",
    "Messdaten & Speicherung": "Measurement V4 ist die produktive Messdatengrundlage. Logging ist nachgelagert und darf die Regelung nicht blockieren. off, standard und extended unterscheiden Umfang und Speichervolumen; Fallback- und Storagezustände müssen sichtbar bleiben.",
    "System & Diagnose": "Hier stellst du Webzugang, Protokolle, Messwert-Aktualitätsüberwachung und ressourcenbegrenzte Analysen ein. Mehr Logdaten und größere Analysen beanspruchen Speicher, CPU und Datenträger, steuern aber nicht selbst die Ladeleistung. Sicherheitsgrenzen können bei echten Daten- oder Kommunikationsproblemen eine unsichere Geräteanforderung stoppen; ein Webserver-Neustart benötigt eine gesonderte administrative Bestätigung.",
}

# Page numbers are build-verified against the V12.12.1 generic manual.
HANDBOOK_GLOSSARY = HandbookRef("glossary", "Begriffe und Abkürzungen", 15)
HANDBOOK_SECTIONS = {
    "Betriebsart & manuelle Steuerung": ("manual-modes", "Betriebsarten und manuelle Steuerung", 4),
    "Leistungsgrenzen & SOC-Schutz": ("limits-soc", "Leistungsgrenzen und SOC-Schutz", 5),
    "AUTO-Regelung": ("auto-control", "AUTO-Regelung", 6),
    "Nachtbetrieb": ("night", "Nachtbetrieb", 7),
    "Primärspeicher": ("primary-storage", "Primärspeicher", 8),
    "Harvest / Restüberschuss": ("harvest", "Harvest / Restüberschuss", 9),
    "Cross-Charge-Schutz": ("cross-charge", "Cross-Charge-Schutz", 10),
    "Kommandowirkung & Resync": ("command-effect", "Kommandowirkung und Resync", 11),
    "Zendure-Geräte": ("interfaces", "Geräte und Schnittstellen", 12),
    "Schnittstellen & Datenquellen": ("interfaces", "Geräte und Schnittstellen", 12),
    "Messdaten & Speicherung": ("measurement-v4", "Measurement V4 und Speicherung", 13),
    "System & Diagnose": ("system-diagnostics", "System und Diagnose", 14),
}

SECTION_ORDER_OVERRIDES = {
    "Primärspeicher": ("Integration & Status", "Integration & Identität", "Anbindung", "Gerät & Verbindung · Modbus", "MQTT-Datenquelle · EVCC Standard", "MQTT-Datenquelle · Benutzerdefiniert", "MQTT-Payload · Benutzerdefiniert", "Normalisierung", "Freshness & Verfügbarkeit", "Technische Leistungsdaten"),
    "Betriebsart & manuelle Steuerung": ("Betriebsart", "Profil Feste Entladung", "Profil Feste Ladung"),
    "Nachtbetrieb": ("Aktivierung", "Zeitfenster", "Feste Basisentladung", "Reserve & Folgeverhalten"),
    "Harvest / Restüberschuss": ("Master & Zielbild", "Fast Capture", "High-SOC & Vollspeicher", "Entry & Hysterese", "Near-Limit-Entry", "Primärspeicher-Schwellen", "Tageszeitprofil"),
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
    "HARVEST_FAST_CAPTURE_MODE": 1,
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
    "HARVEST_SEASON_MODE": "Saisonale Ladeverteilung",
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
    "SECOND_BATTERY_EVCC_BASE_TOPIC": {"key": "SECOND_BATTERY_SOURCE_PROFILE", "equals": "evcc_standard"},
    "SECOND_BATTERY_POWER_TOPIC": {"key": "SECOND_BATTERY_SOURCE_PROFILE", "equals": "custom"},
    "SECOND_BATTERY_SOC_TOPIC": {"key": "SECOND_BATTERY_SOURCE_PROFILE", "equals": "custom"},
    "SECOND_BATTERY_CAPACITY_TOPIC": {"key": "SECOND_BATTERY_SOURCE_PROFILE", "equals": "custom"},
    "SECOND_BATTERY_MODBUS_TEMPLATE": {"key": "SECOND_BATTERY_SOURCE_PROFILE", "equals": "modbus_template"},
    "SECOND_BATTERY_MODBUS_HOST": {"key": "SECOND_BATTERY_SOURCE_PROFILE", "equals": "modbus_template"},
    "SECOND_BATTERY_MODBUS_PORT": {"key": "SECOND_BATTERY_SOURCE_PROFILE", "equals": "modbus_template"},
    "SECOND_BATTERY_MODBUS_UNIT_ID": {"key": "SECOND_BATTERY_SOURCE_PROFILE", "equals": "modbus_template"},
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
    "REST_SURPLUS_MIN_EXPORT_W": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
    "HARVEST_FAST_CAPTURE_MODE": {"key": "SECOND_BATTERY_INTEGRATION_ENABLED", "equals": True},
    "HARVEST_HIGH_SMA_SOC_ENABLED": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
    "HARVEST_HIGH_SMA_SOC_ENTER_PERCENT": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
    "HARVEST_HIGH_SMA_SOC_EXIT_PERCENT": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
    "HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
    "HARVEST_SMA_FULL_SOC_PERCENT": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
    "HARVEST_HIGH_SMA_SOC_HOLD_SECONDS": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
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

SHORT_HELP = {
    'MANUAL_MODE': 'Automatik überlässt die Leistung der normalen Netz-/PV-Regelung. Stop/Hold setzt Lade- und Entladeleistung auf 0 W und hält diesen Zustand, bis hier wieder ein anderer Modus gespeichert wird. Feste Entladung oder Beladung übersteuern die Automatik bis zum eingestellten Ziel-SOC.',
    'MANUAL_DISCHARGE_AFTER_TARGET': 'Legt fest, was passiert, sobald der Ziel-SOC der festen Entladung erreicht ist. Automatik aktiviert wieder die normale Regelung; Stop/Hold setzt beide Leistungen auf 0 W und bleibt dort.',
    'MANUAL_FIXED_DISCHARGE_POWER_W': 'Leistung für den manuellen Modus Feste Entladung. Der Controller begrenzt diesen Wert zusätzlich auf die konfigurierte maximale Entladeleistung.',
    'MANUAL_FIXED_DISCHARGE_TARGET_SOC': 'Ziel-SOC für die feste Entladung. Zur Laufzeit wird dieser Wert mindestens auf den konfigurierten Min Zendure SOC angehoben, damit die allgemeine Akku-Schutzgrenze nicht unterschritten wird.',
    'MANUAL_CHARGE_AFTER_TARGET': 'Legt fest, was passiert, sobald der Ziel-SOC der festen Beladung erreicht ist. Automatik aktiviert wieder die normale Regelung; Stop/Hold setzt beide Leistungen auf 0 W und bleibt dort.',
    'MANUAL_FIXED_CHARGE_POWER_W': 'Leistung für den manuellen Modus Feste Beladung. Der Controller begrenzt diesen Wert zusätzlich auf die konfigurierte maximale Ladeleistung.',
    'MANUAL_FIXED_CHARGE_TARGET_SOC': 'Ziel-SOC für die feste Beladung. Zur Laufzeit wird dieser Wert höchstens auf den konfigurierten Max Zendure SOC abgesenkt, damit die allgemeine obere Akku-Grenze eingehalten wird.',
    'ZENDURE_BATTERY_CAPACITY_WH': 'Gesamtkapazität der Zendure-Batterien in Wh für die Nachtmodus-Prognose. Leer = Prognose nicht berechenbar. Beispiel: 5280 Wh bei 2,4 kWh Headunit plus 2,88 kWh Erweiterung.',
    'DEVICE_ID': 'Identifier der Zendure Headunit für die MQTT-Topics.',
    'MAX_CHARGE_POWER_W': 'Maximale Leistung, mit der Zendure bei PV-Überschuss geladen werden darf.',
    'MAX_DISCHARGE_POWER_W': 'Maximale Leistung, mit der Zendure das Haus versorgen darf.',
    'MAX_SOC_PERCENT': 'Ab diesem SOC wird Ladung verhindert.',
    'MIN_SOC_PERCENT': 'Unterhalb dieses SOC wird Entladung verhindert.',
    'MIN_COMMAND_CHANGE_W': 'MQTT-Leistungsbefehle werden nur gesendet, wenn sich der Wert mindestens um diesen Betrag ändert. 0 deaktiviert die Optimierung.',
    'MOVING_AVERAGE_SAMPLES': 'Anzahl der Messwerte im gleitenden Mittelwert. Höher = ruhiger, aber träger.',
    'DEADBAND_W': 'Bereich um 0 W Netzleistung, in dem die Leistung gehalten wird. Reduziert Pendeln und MQTT-Kommandos.',
    'MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W': 'Zendure lädt nur, wenn nach Zusatzbatterie-Abzug und Reserve mindestens dieser Überschuss übrig bleibt.',
    'MAX_POWER_STEP_W': 'Maximale Änderung der Lade-/Entladeleistung pro Zyklus.',
    'SMA_GUARD_RAMP_DOWN_W': 'Schrittweite, mit der Zendure-Ladung reduziert wird, wenn der Cross-Charge-Schutz blockiert.',
    'CONTROL_GAIN': 'Reglerverstärkung. 0.30 bedeutet, dass nur 30 % der Abweichung pro Zyklus aufaddiert werden.',
    'SMOOTHING_FACTOR': 'Zusätzliche Glättung der Zielwerte. 1.0 reagiert sofort, kleinere Werte sind weicher.',
    'INTERVAL_SECONDS': 'Zeit zwischen zwei Regelschritten. Kleinere Werte reagieren schneller, größere Werte laufen ruhiger.',
    'NIGHT_DISCHARGE_ENABLED': 'Aktiviert eine feste Entladeleistung im konfigurierten Zeitfenster.',
    'NIGHT_DISCHARGE_POWER_W': 'Feste Entladeleistung im Nachtmodus.',
    'NIGHT_DISCHARGE_STOP_SOC_PERCENT': 'Optionaler Reserve-/Stop-SOC für die Nachtentladung. Leer lassen für bisheriges Verhalten. Wenn gesetzt, stoppt die Nachtentladung bei SOC kleiner/gleich diesem Wert. Steigt der SOC später wieder über diesen Wert, darf die Nachtentladung im selben Nachtfenster wieder laufen. Der Wert muss mindestens dem globalen Mindest-SOC entsprechen.',
    'NIGHT_END_HOUR': 'Endstunde des Nachtmodus.',
    'NIGHT_END_MINUTE': 'Endminute des Nachtmodus. Wird in der Weboberfläche zusammen mit der Stunde als hh:mm-Feld dargestellt.',
    'NIGHT_START_HOUR': 'Startstunde des Nachtmodus.',
    'NIGHT_START_MINUTE': 'Startminute des Nachtmodus.',
    'SECOND_BATTERY_STALE_TIMEOUT_SECONDS': 'Nach dieser Zeit ohne vollständiges Primärspeicher-Update gelten die Daten für die Regelung als veraltet. Das gilt quellenneutral für MQTT und native Modbus-Templates; Source Health kann bereits vorher DEGRADED melden, solange der letzte vollständige Snapshot noch frisch ist.',
    'SECOND_BATTERY_DISPLAY_NAME': 'Freier Anzeigename des Primärspeichers. Dieser Name wird in Status, Graph, Inspector und Diagnose verwendet; interne IDs und Historienidentität bleiben stabil.',
    'SECOND_BATTERY_SOURCE_PROFILE': 'Wählt genau eine Primärspeicher-Anbindung: EVCC, benutzerdefiniertes MQTT oder direktes read-only Modbus über ein geprüftes Geräteprofil. Die jeweils benötigten Verbindungsparameter werden unmittelbar darunter geführt. Ein Quellenwechsel erfordert einen Dienstneustart.',
    'SECOND_BATTERY_MODBUS_TEMPLATE': 'Geprüftes read-only Geräteprofil für die direkte Modbus-Anbindung. Derzeit ist SMA Sunny Island verfügbar. Weitere Geräteprofile werden versioniert mit ZEC-Releases ausgeliefert; Register sind nicht frei editierbar.',
    'SECOND_BATTERY_MODBUS_HOST': 'Host oder IP-Adresse des Primärspeichers für Modbus TCP. Der Wert ist installationsspezifisch.',
    'SECOND_BATTERY_MODBUS_PORT': 'Modbus-TCP-Port. Das Geräteprofil SMA Sunny Island verwendet 502 als Default; der Wert kann installationsseitig überschrieben werden.',
    'SECOND_BATTERY_MODBUS_UNIT_ID': 'Modbus Unit-ID. Das Geräteprofil SMA Sunny Island verwendet 3 als Default; der Wert kann installationsseitig überschrieben werden.',
    'SECOND_BATTERY_CAPACITY_TOPIC': 'Optionales MQTT-Topic für die Primärspeicher-Kapazität im MQTT-Profil. Die Kapazität dient Anzeige und Diagnose, ist aber nicht zwingend für die Schutzentscheidung erforderlich.',
    'SECOND_BATTERY_POWER_TOPIC': 'Vollständiges MQTT-Topic der Primärspeicher-Leistung. Dieses Topic ist nur im benutzerdefinierten MQTT-Profil Pflicht.',
    'SECOND_BATTERY_SOC_TOPIC': "Optionales MQTT-Topic für den Ladezustand des Primärspeichers in Prozent. Das native Sunny-Island-Template liest den SOC direkt per Modbus und benötigt dieses MQTT-Topic nicht.",
    'SECOND_BATTERY_EVCC_BASE_TOPIC': 'Basis-Topic des Primärspeichers bei EVCC-Standardstruktur, z. B. evcc/site/battery/devices/1. Daraus werden Leistung, SOC und Kapazität automatisch als /power, /soc und /capacity abgeleitet.',
    'SECOND_BATTERY_CAPACITY_JSON_PATH': 'Feldpfad innerhalb eines JSON-Payloads, z. B. capacity oder battery.capacity. Nur relevant, wenn Kapazitäts-Payload = JSON gewählt ist.',
    'SECOND_BATTERY_CAPACITY_PAYLOAD_TYPE': 'Gibt an, ob das Kapazitäts-Topic direkt eine Zahl enthält oder ein JSON-Objekt liefert.',
    'SECOND_BATTERY_POWER_JSON_PATH': 'Feldpfad innerhalb eines JSON-Payloads, z. B. power oder battery.power. Nur relevant, wenn Leistungs-Payload = JSON gewählt ist.',
    'SECOND_BATTERY_POWER_PAYLOAD_TYPE': 'Gibt an, ob das Leistungs-Topic direkt eine Zahl enthält oder ein JSON-Objekt liefert.',
    'SECOND_BATTERY_SOC_JSON_PATH': 'Feldpfad innerhalb eines JSON-Payloads, z. B. soc oder battery.soc. Nur relevant, wenn SOC-Payload = JSON gewählt ist.',
    'SECOND_BATTERY_SOC_PAYLOAD_TYPE': 'Gibt an, ob das SOC-Topic direkt eine Zahl enthält oder ein JSON-Objekt liefert.',
    'SECOND_BATTERY_CAPACITY_UNIT': 'Einheit des Kapazitätswerts der Zusatzbatterie. Die Statusseite zeigt den Wert in kWh an.',
    'SECOND_BATTERY_DISCHARGE_SIGN': '+1 bedeutet: positive MQTT-Leistung = Zusatzbatterie entlädt. -1 bedeutet: negative MQTT-Leistung = Zusatzbatterie entlädt. Die Statusanzeige normiert danach auf positiv = Ladung, negativ = Entladung.',
    'SECOND_BATTERY_POWER_UNIT': 'Einheit des Leistungswerts der Zusatzbatterie. Intern wird immer auf Watt normalisiert.',
    'SECOND_BATTERY_MAX_CHARGE_POWER_W': 'Maximale Ladeleistung des Primärspeichers bzw. der Zweitbatterie. Dieser Wert steht meist im Datenblatt des Wechselrichters/Batteriesystems. Leer bedeutet: Restüberschuss-Ernte bleibt nicht wirksam. Für SMA Sunny Island 3.0M-11 sind aus ZEC-Sicht 2300 W passend.',
    'REST_SURPLUS_HARVEST_ENABLED': 'Aktiviert eine spezielle AUTO-Funktion: Wenn der Primärspeicher über längere Zeit nahe seiner Ladegrenze lädt und trotzdem Netzexport übrig bleibt, darf Zendure diesen Restüberschuss zusätzlich laden. Die Funktion startet nicht bei kurzen Spitzen und darf nur laden, niemals Entladung auslösen.',
    'HARVEST_FAST_CAPTURE_MODE': 'Legt fest, ob Fast Capture ausgeschaltet bleibt, nur mögliche zusätzliche Ladung berechnet oder diese bei geeignetem PV-Überschuss tatsächlich anfordern darf. Die Wahlmöglichkeiten heißen „Aus“, „Shadow (nur Diagnose)“ und „Aktiv“. Eine zusätzliche Ladeanforderung ist nur zulässig, wenn der Primärspeicher voll ist und praktisch nicht mehr lädt oder fast seine Ladeleistungsgrenze erreicht hat. Alle Schutzgrenzen gelten weiterhin.',
    'REST_SURPLUS_MIN_EXPORT_W': 'Mindestexport am Netzanschlusspunkt, ab dem die Restüberschuss-Ernte für den Entry qualifiziert. Dieser Wert ist nur eine Aktivierungs-/Rauschschwelle, kein dauerhaft gewünschter Restexport. Default: 80 W.',
    'CROSS_CHARGE_ENABLED': 'Aktiviert den Cross-Charge-Schutz auf Basis der bereits separat konfigurierten Primärspeicher-Integration. Die Datenquelle selbst wird über „Primärspeicher-Integration aktiv“ gesteuert.',
    'SECOND_BATTERY_STALE_BLOCK_CHARGE': 'Konservativer Fallback: Wenn der Cross-Charge-Schutz aktiv ist, aber keine frischen Zusatzbatteriedaten vorliegen, wird Zendure-Ladung blockiert.',
    'CROSS_CHARGE_SIGNIFICANT_W': 'Ab diesem gegenläufigen Leistungsfluss zwischen Zusatzbatterie und Zendure wird der Cross-Charge-Schutz aktiv. Eine interne niedrigere Freigabeschwelle verhindert hektisches Ein-/Ausschalten.',
    'COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS': 'Wenn ZEC aus Sicherheitsgründen 0 W anfordert, muss innerhalb dieser Zeit an der gemeldeten Istleistung erkennbar sein, dass das Gerät nicht mehr lädt oder entlädt. Bei fortbestehender Leistung sendet ZEC AC-Modus sowie beide Limits als vollständige 0-W-Zustandsneutralisierung erneut.',
    'ZENDURE_COMMAND_STATE_FRESH_SECONDS': 'Maximales Alter der rückgelesenen Werte smartMode, acMode, inputLimit und outputLimit. Dynamische Limitänderungen werden nur bei bestätigtem smartMode=1 freigegeben.',
    'ZENDURE_COMMAND_STATE_RETRY_SECONDS': 'Mindestabstand für einen erneuten vollständigen Modus-/Limit-Abgleich, solange die Rücklesung noch nicht konsistent ist.',
    'ZENDURE_SMART_MODE_RETRY_SECONDS': 'Mindestabstand für erneutes smartMode=ON, wenn der volatile Flash-Schutz noch nicht rückgelesen wurde.',
    'COMMAND_RESYNC_STALE_MIN_SECONDS': 'Mindestdauer eines unsicheren Zendure-MQTT-Zustands, bevor Recovery einen Command-Resync auslöst.',
    'COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS': 'Notfall-/Legacy-Schalter: erzwingt Resync bei jeder Zendure-MQTT-Recovery. Standardmäßig ist die Option deaktiviert, damit kurze STALE-Phasen keinen unnötigen Resync-Sturm auslösen.',
    'COMMAND_EFFECT_FORCE_RESEND_SECONDS': 'Nach dieser Zeit sendet ZEC einen weiterhin unwirksamen aktiven Sollzustand vollständig erneut. Resync-Versand und anschließend bestätigte Gerätewirkung werden getrennt dokumentiert.',
    'COMMAND_RESYNC_COOLDOWN_SECONDS': 'Unterdrückt identische Resync-Wiederholungen im Cooldown, außer bei weiter bestätigtem Mismatch nach Ablauf des Cooldowns.',
    'COMMAND_EFFECT_TOLERANCE_PERCENT': 'Relative Toleranz für hohe Sollwerte. Sie verändert nur die Wirkungsdiagnose, niemals den Regler-Sollwert oder eine Gerätegrenze.',
    'COMMAND_EFFECT_TOLERANCE_W': 'Absolute Mindesttoleranz für das Zielwerttracking. Verwendet wird der größere Wert aus dieser absoluten Toleranz und der relativen Prozenttoleranz.',
    'COMMAND_EFFECT_MIN_TARGET_W': 'Unterhalb dieser Schwelle ist die physische Wirkung nicht belastbar bewertbar; der Zustand wird nicht als COMMAND_EFFECTIVE ausgegeben.',
    'COMMAND_EFFECT_MIN_W': 'Schwellwert, ab dem eine unabhängige Istleistungsbeobachtung als belastbare Reaktion in Lade- oder Entladerichtung gilt. Das beweist noch kein vollständiges Sollwerttracking.',
    'COMMAND_EFFECT_TIMEOUT_SECONDS': 'Wenn das Gerät während dieser Zeit trotz einer Lade- oder Entladeanforderung die Leistungsrichtung nicht übernimmt oder dauerhaft deutlich weniger Leistung liefert als angefordert, wertet ZEC die Anforderung als nicht ausreichend wirksam. Kleine Wattänderungen derselben Richtung starten die Zeit nicht neu.',
    'MEASUREMENT_LOG_MAX_BYTES': 'Bei Überschreitung wird rotiert. Zusammen mit der Dateianzahl bestimmt dieser Wert die geschätzte Aufbewahrung.',
    'MEASUREMENT_LOG_ALLOW_SD_FALLBACK': 'Wenn das externe Speicherziel nicht verfügbar ist, darf begrenzt auf die interne SD geschrieben werden. Der Fallback wird sichtbar markiert und enger rotiert.',
    'MEASUREMENT_LOG_FALLBACK_DIR': 'Begrenztes Fallback-Verzeichnis auf der internen SD, falls ein externes Logziel ausfällt.',
    'MEASUREMENT_LOG_FALLBACK_MAX_BYTES': 'Kleinere Rotationsgrenze für den SD-Fallback, damit ein USB-Ausfall die SD nicht unbegrenzt belastet.',
    'MEASUREMENT_LOG_FILE': 'Dateiname der aktuellen Measurement-V4-Datei. Beim Standardnamen schreibt der Controller automatisch zendure_measurements_v4.csv; produktive Messdaten werden ausschließlich im V4-Vertrag erzeugt.',
    'MEASUREMENT_LOG_MODE': 'Aus: keine zyklischen Messdaten, schont die SD-Karte. Standard: vollständige Reglerdiagnose inklusive Datenaktualität, MQTT-Veraltet-Aggregat, Sollwertkaskade, Kommando und Szenario ohne Zendure. Erweitert: Standard plus Detaildaten für Simulation, What-if und tiefe MQTT-/Aktualitätsanalyse; erzeugt größere Dateien und sollte gezielt genutzt werden.',
    'MEASUREMENT_DB_ENABLED': 'Schreibt parallel zu CSV/V4 einen leichten SQLite-Store für schnelle Status- und Graphdaten. Läuft auch, wenn Messdaten-CSV deaktiviert ist; die Regelung wird bei DB-Fehlern nicht blockiert.',
    'MEASUREMENT_DB_PATH': 'Optionaler absoluter Pfad zur SQLite-Datei. Leer bedeutet: automatisch neben den Messdaten im aktiven Speicherziel.',
    'MEASUREMENT_LOG_FLUSH_EVERY_ROWS': 'Schreibt gepufferte Messdaten periodisch aus dem Python-Puffer. Kein hartes fsync pro Zeile; bei Stromausfall können letzte Messdaten fehlen.',
    'MEASUREMENT_LOG_FLUSH_EVERY_SECONDS': 'Zeitbasierte Flush-Grenze für gepuffertes Logging. Reduziert kleine Sync-Schreibvorgänge gegenüber hartem Schreiben pro Messpunkt.',
    'MEASUREMENT_LOG_MIN_FREE_DISK_MB': 'Mindestfreier Speicher am aktuell aktiven Messdatenziel: interne SD, externer USB-/Mountpoint oder bei aktivem Fallback der SD-Fallback-Pfad. Wenn weniger Speicher frei ist, pausiert das Messdaten-Logging; die Regelung läuft weiter.',
    'MEASUREMENT_LOG_DIR': 'Verzeichnis für ZEC-MEASUREMENT-Messdaten. Bei internal_sd/custom_path wird dieses Feld direkt verwendet. Bei external_mount wird es als Unterordner auf dem USB-/Mountpoint verwendet, z. B. USB + ZEC/logs.',
    'MEASUREMENT_LOG_MOUNTPOINT': 'Optionaler Mountpoint für externes Messdaten-Logging, z. B. /media/pi/USBSTICK oder /mnt/zec-logs. Wenn leer, wird bei Speicherziel external_mount ein erkannter schreibbarer USB-/Mountpoint automatisch verwendet.',
    'MEASUREMENT_LOG_STORAGE_TARGET': 'Legt fest, wo Messdaten primär geschrieben werden. Bei erkanntem USB-/Mountpoint wird ein schreibbarer externer Mount automatisch verwendet; das Feld USB-/Mountpoint kann optional einen bestimmten Mountpoint festlegen.',
    'GRAPH_HISTORY_LIMIT': 'Anzahl der im RAM gehaltenen Graph-Datenpunkte. Diese Historie ist unabhängig vom dauerhaften Messdaten-Logging.',
    'SOC_DAY_GRAPH_BOOTSTRAP_FROM_MEASUREMENTS': 'Versucht beim Abruf der SOC-Tageskurve, heutige Measurement-V4-Logs best-effort einzulesen. Fehler sind nicht kritisch; die Kurve startet dann ab jetzt.',
    'SOC_DAY_GRAPH_ENABLED': 'Zeigt auf der Statusseite eine leichte 24h-Zendure-SOC-Kurve für den aktuellen lokalen Tag.',
    'SOC_DAY_GRAPH_SAMPLE_SECONDS': 'Samplingintervall der SOC-Tageskurve im RAM. Default 60 Sekunden; der Controller hält maximal etwa 1440 Punkte pro Tag.',
    'MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_ROWS': 'Schreibt das V4-Manifest gepuffert statt pro Zyklus. Niedrigere Werte sind aktueller, höhere Werte reduzieren I/O.',
    'MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_SECONDS': 'Spätester gepufferter V4-Manifest-Update. Beim Schließen wird immer final aktualisiert.',
    'MQTT_TOPIC_DIAGNOSTIC_ENABLED': 'Wenn aktiv, abonniert das Script zusätzlich das konfigurierte Diagnose-Topic, standardmäßig Zendure/#, und zeigt die letzten MQTT-Nachrichten unter /mqtt-diagnostics an. Nur für Analysephasen empfohlen, weil dadurch mehr MQTT-Daten verarbeitet werden.',
    'MQTT_TOPIC_DIAGNOSTIC_FILTER': 'MQTT-Topic-Filter für den Diagnosemitschnitt, z. B. Zendure/# oder evcc/#. MQTT Topic Matching ist groß-/kleinschreibungssensitiv; EVCC/# passt also nicht auf evcc/site/... . Änderungen an diesem Filter erfordern meist einen Neustart oder erneutes Speichern der Config.',
    'MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT': 'Anzahl der letzten MQTT-Diagnosemeldungen, die im RAM gehalten werden. Höhere Werte brauchen mehr Speicher, sind aber für Topic-Analyse hilfreich.',
    'MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE': 'filtered speichert/zeigt nur Nachrichten, die zum MQTT Topic-Diagnose Filter passen. all speichert alle vom Controller empfangenen MQTT-Nachrichten und ist nur für kurze Fehlersuche empfohlen.',
    'MQTT_BROKER': 'Adresse des MQTT-Brokers. Meist der Raspberry Pi selbst.',
    'MQTT_PASSWORD': 'Passwort für MQTT. Wird in der lokalen config.json gespeichert.',
    'MQTT_PORT': 'Port des MQTT-Brokers. Standard ist 1883.',
    'MQTT_USER': 'Benutzername für MQTT. Leer lassen, wenn keine Authentifizierung verwendet wird.',
    'GRID_POWER_PLAUSIBILITY_MAX_ABS_W': 'Absolute Obergrenze für plausible Netzleistungswerte. Messwerte oberhalb dieser Grenze werden verworfen und nicht für AUTO-Regelung oder Glättung verwendet. Default 30000 W schützt vor offensichtlich defekten SMA-/Shelly-Ausreißern.',
    'SMA_ENERGY_METER_LOG_DIAGNOSTICS': 'Schreibt kompakte SMA-Socket-/Paketdiagnosen in das Runtime-Textlog. Zusätzlich muss Datei-Logging aktiv sein, damit die Meldungen in zendure_runtime.log landen.',
    'SMA_ENERGY_METER_LOG_INTERVAL_SECONDS': 'Mindestabstand zwischen periodischen SMA_DIAG-Zeilen im Runtime-Log, wenn SMA-Diagnoselogging aktiv ist.',
    'SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS': 'Ab dieser Lücke zwischen empfangenen SMA-Speedwire-Paketen wird die Lücke in der SMA-Diagnose markiert. Der Stream kommt typischerweise ungefähr sekündlich.',
    'SMA_ENERGY_METER_GROUP': 'Multicast-Adresse der SMA Energy Meter Daten. Typischer Standard: 239.12.255.254.',
    'SMA_ENERGY_METER_INTERFACE': 'Optional: lokale IPv4-Adresse oder Interface-Name wie eth0 für den Multicast-Join. Bei mehreren Netzwerkinterfaces bevorzugt eth0 eintragen.',
    'SMA_ENERGY_METER_PASSIVE_ENABLED': 'Nur relevant, wenn als Netzleistungsquelle die Shelly-kompatible HTTP-Quelle gewählt ist: startet zusätzlich einen passiven SMA Energy Meter / Sunny Home Manager 2.0 Listener zum Vergleich. Wenn SMA Home Manager direkt als Netzleistungsquelle gewählt ist, wird der Listener automatisch aktiviert; dieser Schalter ist dann fachlich redundant.',
    'SMA_ENERGY_METER_PORT': 'UDP-Port für SMA Energy Meter / Sunny Home Manager 2.0 Multicast. Typischer Standard: 9522.',
    'SMA_ENERGY_METER_SERIAL': 'Optionaler Filter auf die Seriennummer des Energy Meters am Netzbezugspunkt. Bei mehreren SMA Energy Metern vor produktiver Nutzung zwingend empfohlen.',
    'SMA_ENERGY_METER_SOCKET_MODE': 'Experten-/Diagnoseoption für die Koexistenz mit EVCC, UniMeter oder weiteren SMA-Speedwire-Listenern auf demselben Host. Default group_bind bindet auf die SMA-Multicast-Gruppe und war im Nachtlauf mit EVCC auf demselben Raspberry Pi stabil. Wildcard-Modi auf 0.0.0.0:9522 bleiben reine Diagnoseoptionen und können EVCC stören.',
    'SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS': 'Maximales Alter eines direkt per SMA Energy Meter empfangenen Netzleistungswerts, falls die direkte SMA-Quelle als Regelquelle verwendet wird.',
    'SMA_ENERGY_METER_SUSY_ID': 'Optionaler Filter auf die SMA SUSy-ID des gewünschten Energy Meters. Bei mehreren SMA Energy Metern empfohlen. Beispiel: <SMA-SUSY-ID>.',
    'SHELLY_IP': 'IP-Adresse der Shelly- oder Shelly-kompatiblen Messdatenquelle. Das kann ein echter Shelly Pro 3EM oder ein anderer Shelly-kompatibler HTTP-Endpunkt sein.',
    'SHELLY_STALE_TIMEOUT_SECONDS': 'Maximales Alter des letzten gültigen Netzleistungswerts.',
    'GRID_METER_SOURCE': 'Quelle für die Netzleistung am Hausanschlusspunkt. Shelly-kompatibles HTTP bleibt dauerhaft als Alternative für echte Shelly Pro 3EM und kompatible Endpunkte erhalten. SMA direkt nutzt das lokale SMA Energy Meter / Sunny Home Manager UDP-Multicast-Protokoll.',
    'ZENDURE_LOCAL_API_ENABLED': 'Aktiviert den Diagnose-Endpunkt /zendure-properties. Diese Option steuert die Web-Diagnoseseite; die Telemetrie-Fallback-Nutzung wird separat über die folgenden Optionen gesteuert.',
    'ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS': 'Pause nach einem Timeout oder Fehler der lokalen Zendure-API, bevor der Controller erneut /properties/report abfragt. Schützt EVCC und die Zendure-Headunit vor aggressiven Wiederholungen.',
    'ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS': 'Mindestabstand zwischen zwei lokalen Zendure-API-Abfragen für Telemetrie und Temperaturdiagnose.',
    'ZENDURE_LOCAL_API_SOC_PRIORITY': 'Legt fest, welcher SOC-Wert aus /properties/report bevorzugt wird, falls sowohl properties.electricLevel als auch packData[0].socLevel vorhanden sind.',
    'ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY': 'Wenn aktiv, bleibt MQTT die bevorzugte Quelle für SOC und Istleistung. Die lokale API aktualisiert den aktiven SOC nur dann, wenn MQTT fehlt oder veraltet ist. Sobald MQTT wieder gültige Werte liefert, wechselt die Anzeige automatisch zurück zu MQTT.',
    'ZENDURE_LOCAL_API_USE_FOR_TELEMETRY': 'Wenn aktiv, darf der Controller die lokale Zendure-API als zusätzliche Telemetriequelle für SOC, Istleistung und Akkutemperatur verwenden. Das ist ein Fallback gegen den bekannten Fall, dass Zendure nach Broker-/Raspberry-Neustart keine MQTT-Sensordaten mehr publiziert.',
    'ZENDURE_LOCAL_IP': 'IP-Adresse der Zendure-Headunit für lokale Abfragen wie /properties/report. Wird sowohl für die Diagnose-Webseite als auch für den optionalen Telemetrie-Fallback verwendet.',
    'ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS': 'Begrenzt den Hintergrundrequest unabhängig vom höheren allgemeinen API-Timeout. Die lokale API arbeitet asynchron und blockiert den Regelzyklus nicht.',
    'ZENDURE_LOCAL_API_TIMEOUT_SECONDS': 'Maximale Wartezeit eines asynchronen lokalen Zendure-API-Requests. Der Regelzyklus wartet nicht auf diesen Request.',
    'WEB_SERVICE_RESTART_ENABLED': 'Erlaubt der Weboberfläche, nach dem Speichern neustartrelevanter Einstellungen den systemd-Dienst kontrolliert neu zu starten. Aus Sicherheitsgründen ist diese Funktion standardmäßig deaktiviert und benötigt zusätzlich ein freigegebenes Restart-Hilfsscript mit sudoers-Regel.',
    'ANALYSIS_EXTENDED_MAX_FILES': 'Erweiterte Dateianzahl für bewusst bestätigte größere Analysen. Auf dem Raspberry Pi nur mit Warnung verwenden.',
    'ANALYSIS_EXTENDED_MAX_ROWS': 'Erweiterte Messpunktzahl für bewusst bestätigte größere Analysen. Alles darüber wird fail-closed abgelehnt.',
    'ANALYSIS_EXTENDED_MAX_TOTAL_BYTES': 'Erweiterte Gesamtgröße für bewusst bestätigte größere Analysen. Alles darüber wird lokal abgelehnt und sollte offline/auf dem PC analysiert werden.',
    'ANALYSIS_EXTENDED_WORKER_MEMORY_LIMIT_MB': 'Speicherlimit für bewusst bestätigte größere Analyse-Worker.',
    'ANALYSIS_EXTENDED_WORKER_TIMEOUT_SECONDS': 'Zeitlimit für bewusst bestätigte größere Analyse-Worker.',
    'ANALYSIS_MAX_FILES': 'Maximale Dateianzahl für normale lokale Analysen auf dem Raspberry Pi. Standard ist bewusst konservativ, um EVCC, MQTT und Live-Regler zu schützen.',
    'ANALYSIS_MAX_ROWS': 'Maximale Messpunktzahl für normale lokale Analysen. Das Limit wird bereits beim Lesen geprüft; zusätzlich läuft die Analyse in einem isolierten Worker.',
    'ANALYSIS_MAX_TOTAL_BYTES': 'Maximale Gesamtgröße der ausgewählten CSV-Dateien für normale lokale Analysen. Standard ist bewusst konservativ, weil Python-/HTML-/Diagrammstrukturen deutlich mehr RAM benötigen als die CSV-Datei auf der SD-Karte.',
    'ANALYSIS_WORKER_MEMORY_LIMIT_MB': 'Speicherlimit für normale Analyse-Worker. Bei Überschreitung wird nur der Analyse-Worker beendet, nicht der Live-Controller.',
    'ANALYSIS_WORKER_TIMEOUT_SECONDS': 'Zeitlimit für normale Analyse-Worker. Bei Überschreitung wird der Worker abgebrochen.',
    'REPLAY_WEB_PORT': 'Port des optionalen separaten Analyse-/Replay-Webdienstes. Der Dienst wird mitgeliefert, aber nicht automatisch aktiviert.',
    'UI_DARK_MODE': 'Aktiviert ein dunkles Farbschema für Statusseite, Settings, Graph, Diagnose, Analyse-Linkseiten und Headless-Hinweisseite. Die Änderung wird nach dem Speichern sofort bei neu geladenen Webseiten sichtbar.',
    'UI_MODE': 'Vorbereitung für eine reduzierte Standardansicht und eine vollständige Expertenansicht. Expertenmodus ist fachlich ein Superset des Standardmodus: Kernstatus und Warnungen bleiben immer sichtbar, Expert-only-Details kommen zusätzlich hinzu.',
    'SLOW_CYCLE_WARN_MS': 'Schreibt einen Runtime-Hinweis, wenn ein Reglerzyklus ohne Sleep länger dauert. Dient der Laufzeit- und Timingdiagnose.',
    'FILE_LOG_BACKUP_COUNT': 'Anzahl alter Text-Logdateien, die behalten werden.',
    'FILE_LOG_DIR': 'Relatives oder absolutes Verzeichnis für die Text-Logdatei.',
    'FILE_LOG_ENABLED': 'Schreibt Betriebs-, Fehler- und Diagnosemeldungen zusätzlich rollierend in eine Text-Logdatei. Das ersetzt nicht das CSV-Datenlogging.',
    'FILE_LOG_FILE': 'Dateiname der aktuellen Runtime-Text-Logdatei, standardmäßig zendure_runtime.log.',
    'FILE_LOG_MAX_BYTES': 'Bei Überschreitung wird die Text-Logdatei rotiert. Alte Dateien werden nach dem Schema zendure_runtime_1.log, zendure_runtime_2.log usw. gehalten.',
    'DEBUG': 'Allgemeine Konsolenausgaben.',
    'LOG_CONTROL': 'Schreibt zusätzliche menschenlesbare Debug-Meldungen zu Zielwerten und Regelentscheidungen ins Runtime-Textlog. Das ist kein strukturiertes Measurement-Logging; die V4-Standard-Messdaten enthalten die Reglerdiagnose bereits.',
    'LOG_MANUAL': 'Loggt Aktionen des manuellen Modus, z. B. Start, Ziel erreicht und automatische Umschaltung nach Ziel-SOC.',
    'LOG_MQTT': 'Loggt MQTT-Kommandos an Zendure.',
    'LOG_RAW_RESPONSE': 'Loggt vollständige Shelly-JSON-Antworten. Nur für Fehlersuche verwenden.',
    'LOG_SOC': 'Loggt empfangene Zendure-SOC-Werte.',
    'LOG_VALUES': 'Loggt Shelly-Rohwert und geglättete Netzleistung.',
    'MAX_CONSECUTIVE_ERRORS': 'Nach dieser Anzahl direkt aufeinanderfolgender Fehler aktiviert der Controller den Safe-State. Safe-State bedeutet: Ladeleistung und Entladeleistung werden per MQTT auf 0 W gesetzt, der Modus wird auf SAFE_STATE gestellt und die Regelung versucht nicht weiter aktiv Leistung zu verschieben, bis wieder gültige Daten vorliegen und der nächste Regelzyklus sauber laufen kann.',
    'MQTT_DISCONNECTED_SAFE_STATE': 'Wenn aktiv, setzt der Controller bei erkannter MQTT-Trennung Lade- und Entladeleistung auf 0 W. Das ist die konservativste Variante, weil ohne MQTT keine zuverlässigen neuen Befehle und teilweise keine aktuellen Rückmeldungen möglich sind. Wenn diese Option nicht aktiv ist, läuft die Logik weiter und zeigt den MQTT-Fehler an; bereits zuletzt an Zendure gesendete Werte können dort aber weiter gültig bleiben, weil der Controller sie während der Trennung nicht sicher ändern kann. Nicht aktiv ist daher toleranter bei kurzen Broker-Aussetzern, aber weniger sicher bei längeren MQTT-Problemen.',
    'SAFE_STATE_ON_SHELLY_ERROR': 'Wenn aktiv, fährt der Controller bei anhaltenden Messfehlern auf 0 W.',
    'SOC_STALE_TIMEOUT_SECONDS': 'Maximales Alter des Zendure-SOC. Bei Überschreitung wird Entladung blockiert.',
    'ZENDURE_POWER_STALE_TIMEOUT_SECONDS': 'Alter der Zendure-Istleistungswerte, ab dem eine Warnung gesetzt wird.',
    'HEADLESS_MODE': 'Schaltet die Weboberflächen ab. Beim Aufruf der Web-URLs wird nur noch eine Hinweisseite angezeigt. Die Regelung läuft weiter; Änderungen sind dann ausschließlich über die config.json und den regulären Config-Reload möglich. Ein Neustart ist zum Beenden des Headless Mode nicht erforderlich, wenn die config.json während des laufenden Programms angepasst wird.',
    'WEB_PORT': 'HTTP-Port des Webinterfaces. Änderung erfordert Neustart.',
    'ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS': 'Wartezeit nach MQTT-Reconnect/Broker-Neustart, bevor fehlende nicht-retained Live-Werte als Neustart-/App-Neuspeicherproblem gemeldet werden.',
    'ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS': 'Maximales Alter kritischer Zendure-MQTT-Gruppen für die Live-/Partial-Stale-Diagnose. Warnungen verschwinden automatisch, sobald wieder frische nicht-retained Live-Werte eintreffen.',
}


# Explicit replacements for descriptions that were missing or were tied to one
# particular installation.  These are the operative user-facing truths.
SHORT_HELP.update({
    "ZENDURE_BATTERY_CAPACITY_WH": "Gesamtkapazität der installierten Zendure-Batterien in Wh für Prognose und Diagnose. Leer bedeutet: Kapazität ist nicht bekannt; ZEC erfindet keinen Anlagenwert.",
    "SECOND_BATTERY_MAX_CHARGE_POWER_W": "Maximale Ladeleistung des Primärspeichers bzw. der Zweitbatterie. Dieser installationsabhängige Wert muss aus der konkreten Anlage bzw. deren Datenblatt stammen; leer bedeutet unbekannt.",
    "REST_SURPLUS_MIN_EXPORT_W": "Mindest-Netzexport, der den Near-Limit-/Restüberschuss-Eintritt qualifiziert. Der Wert ist eine Eintrittsschwelle und ausdrücklich kein gewünschter verbleibender Export.",
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS": "Zeit, über die die High-SOC-Eintrittsbedingungen bestätigt sein müssen. Das Tageszeitprofil kann in festen Profilfenstern eine profilbezogene Bestätigungszeit verwenden.",
    "HARVEST_HIGH_SMA_SOC_HOLD_SECONDS": "Begrenzte Haltezeit eines bereits aktiven High-SOC-Harvest-Zustands nach kurzfristigem Wegfall der Freigabebedingung. Sie ist keine maximale Harvest-Aktivdauer.",
    "HARVEST_HIGH_SMA_SOC_ENABLED": "Aktiviert den High-SOC-Parallel-Harvest als Teil der ZEC-Harveststrategie. Der Primärspeicher bleibt priorisiert; die Funktion ist kein allgemeiner Ladefreigabeschalter.",
    "HARVEST_HIGH_SMA_SOC_ENTER_PERCENT": "Primärspeicher-SOC-Schwelle für den Eintritt in den High-SOC-Bereich. Der niedrigere Austrittswert sorgt dafür, dass die Funktion nicht bei jeder kleinen Ladezustandsschwankung sofort wieder ein- und ausgeschaltet wird.",
    "HARVEST_HIGH_SMA_SOC_EXIT_PERCENT": "Primärspeicher-SOC-Schwelle zum Verlassen des High-SOC-Bereichs. Sie muss unter der Eintrittsschwelle liegen.",
    "HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W": "Mindest-Netzexport für die High-SOC-Freigabebedingung. Der Wert ist eine Eintrittsschwelle und kein gewünschter Restexport.",
    "HARVEST_SMA_FULL_SOC_PERCENT": "SOC-Schwelle, ab der der Primärspeicher für den Harvest-Voll-/Idle-Zweig als voll eingeordnet werden kann.",
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": "Bestätigungszeit für Near-Limit-/Restexportbedingungen, bevor die Restüberschuss-Ernte eintritt.",
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO": "Unterer Primärspeicher-Ladeanteil relativ zur bekannten maximalen Primärspeicher-Ladeleistung. Ein positiver absoluter Floor-Wert übersteuert dieses Verhältnis.",
    "HARVEST_PRIMARY_CHARGE_FLOOR_W": "Optionaler absoluter Primärspeicher-Floor in Watt. Ein positiver Wert ersetzt den zugehörigen Ratio-Wert; leer bzw. automatisch nutzt das Verhältnis.",
    "HARVEST_PRIMARY_CHARGE_RESTART_RATIO": "Primärspeicher-Wiederanlaufschwelle relativ zur maximalen Ladeleistung. Ein positiver absoluter Restart-Wert übersteuert dieses Verhältnis.",
    "HARVEST_PRIMARY_CHARGE_RESTART_W": "Optionaler absoluter Wiederanlaufwert in Watt. Ein positiver Wert ersetzt den zugehörigen Ratio-Wert.",
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO": "Near-Limit-Schwelle des Primärspeichers relativ zur maximalen Ladeleistung. Ein positiver absoluter Near-Limit-Wert übersteuert dieses Verhältnis.",
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W": "Optionaler absoluter Near-Limit-Wert in Watt. Ein positiver Wert ersetzt den zugehörigen Ratio-Wert.",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING": "Primärspeicher-Zielanteil des Harvest-Zeitprofils am Morgen. Ein höherer Anteil reserviert in dieser Strategie grundsätzlich mehr Leistung für den Primärspeicher.",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY": "Primärspeicher-Zielanteil des Harvest-Zeitprofils zur Mittagsphase.",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON": "Primärspeicher-Zielanteil des Harvest-Zeitprofils am Nachmittag.",
    "SOC_DAY_GRAPH_BOOTSTRAP_CACHE_SECONDS": "Zeit, für die ein aus Messdaten aufgebauter SOC-Tagesgraph-Bootstrap im Speicher wiederverwendet werden darf.",
    "WEB_HOST": "Bind-Adresse des HTTP-Webservers. Eine Änderung betrifft den Netzwerkzugriff und wird erst nach Dienstneustart wirksam.",
    "CROSS_CHARGE_SIGNIFICANT_W": "Leistungsschwelle, ab der ein gegenläufiger Zweitbatteriefluss als relevanter Cross-Charge-Konflikt behandelt wird. Bei aktivem Cross-Charge muss der Wert größer als 0 W sein.",
})

SEARCH_SYNONYMS = {
    "DEADBAND_W": ("Totzone", "Deadband", "Nullzone", "0 W", "Restabweichung"),
    "CONTROL_GAIN": ("Verstärkung", "Gain", "Reaktion", "Nachregelung"),
    "SMOOTHING_FACTOR": ("Glättung", "Smoothing", "Filter", "Trägheit"),
    "MAX_POWER_STEP_W": ("Schrittweite", "Rampe", "Step", "W pro Zyklus"),
    "MIN_COMMAND_CHANGE_W": ("Publish", "MQTT Auflösung", "Mindeständerung", "Deduplizierung"),
    "CROSS_CHARGE_SIGNIFICANT_W": ("Cross-Charge", "Gegenfluss", "Umladen", "Schwelle", "Hysterese"),
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO": ("Floor", "Mindestladeanteil", "Primärspeicher", "SMA", "Verhältnis"),
    "HARVEST_PRIMARY_CHARGE_RESTART_RATIO": ("Restart", "Wiederanlauf", "Primärspeicher", "Verhältnis"),
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO": ("Near Limit", "Ladegrenze", "Primärspeicher", "Verhältnis"),
    "COMMAND_EFFECT_TOLERANCE_W": ("Tracking", "Toleranz", "Soll-Ist", "Wirkung"),
    "COMMAND_EFFECT_MIN_TARGET_W": ("Diagnosegrenze", "not evaluable", "Mindest-Sollwert"),
    "NIGHT_DISCHARGE_POWER_W": ("Nachtleistung", "Grundlast", "feste Entladung", "Einspeisung"),
    "REST_SURPLUS_MIN_EXPORT_W": ("Restexport", "Entry", "Harvest", "Mindestexport"),
}

# Per-key extended/effect contracts for the RICH areas.  Shared templates below
# fill the remaining RICH fields without inventing new thresholds.
RICH_EXTENDED = {
    "MANUAL_MODE": "Legt die Priorität der normalen Regelung fest. AUTO überlässt die Leistung der Netzregelung; STOP/HOLD hält das Gerät neutral; feste Lade-/Entlademodi verwenden ihre hinterlegten Profile bis zum Ziel-SOC. Schutz- und Safe-State-Bedingungen bleiben übergeordnet.",
    "MAX_CHARGE_POWER_W": "Harte installationsbezogene Obergrenze für Zendure-Ladeziele. AUTO, Harvest und feste Ladeprofile werden auf diese Grenze begrenzt. Der Wert muss zur konkreten Headunit/Batteriekonfiguration passen.",
    "MAX_DISCHARGE_POWER_W": "Harte installationsbezogene Obergrenze für Zendure-Entladeziele. AUTO, Nacht- und feste Entladeprofile werden auf diese Grenze begrenzt.",
    "MIN_SOC_PERCENT": "Untere globale SOC-Schutzgrenze. Unterhalb bzw. an dieser Grenze wird Entladung blockiert; Nachtreserve und manuelle Entladeziele dürfen diese Grenze nicht unterschreiten.",
    "MAX_SOC_PERCENT": "Obere globale SOC-Schutzgrenze. Ab dieser Grenze wird weitere Ladung blockiert; feste Ladeziele müssen innerhalb des Schutzfensters liegen.",
    "CONTROL_GAIN": "Bestimmt, welcher Anteil der aktuellen wirksamen Netzabweichung in die nächste rohe Zielwertkorrektur eingeht. Nach der Rohkorrektur wirken weitere Limiter wie Maximalleistung, Smoothing, Step-Limit, Cross-Charge und Commandpfad.",
    "SMOOTHING_FACTOR": "Gewichtet den neuen Rohzielwert gegen den bisherigen Zielwert. 1,0 bedeutet keine zusätzliche Glättung; kleinere Werte machen die Reaktion weicher und langsamer.",
    "MAX_POWER_STEP_W": "Begrenzt die Änderung des Leistungsziels pro Regelzyklus. Der Wert bestimmt nicht das absolute Leistungsmaximum, sondern die maximale Zielwertänderung zwischen zwei Schritten.",
    "DEADBAND_W": "Definiert die normale Totzone um 0 W Netzleistung. Innerhalb der Totzone wird HOLD bevorzugt; ausdrücklich spezifizierte Harvest-Spezialzweige können davon abweichen.",
    "MIN_COMMAND_CHANGE_W": "Bestimmt die Mindeständerung, ab der ein neues Leistungsupdate publiziert wird. Die interne Zielwertrechnung bleibt davon unabhängig.",
    "MOVING_AVERAGE_SAMPLES": "Legt die Anzahl der Netzleistungsmessungen im gleitenden Mittel fest. Zusammen mit dem Regelintervall ergibt sich näherungsweise das Beobachtungsfenster.",
    "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W": "Normale AUTO-Ladung wird erst freigegeben, wenn der wirksame Überschuss mindestens die größere Schwelle aus Totzone und dieser Ladefreigabe erreicht.",
    "SMA_GUARD_RAMP_DOWN_W": "Schrittweite für den Abbau einer bereits bestehenden AUTO-Ladung in den dafür vorgesehenen Schutz-/Ramp-down-Pfaden. Nicht mit dem allgemeinen MAX_POWER_STEP_W gleichsetzen.",
    "INTERVAL_SECONDS": "Nominale Zyklusbasis. Der reale Zyklusabstand besteht aus aktiver Arbeit plus Wartezeit; der Wert beeinflusst gemeinsam mit Mittelwertfenster, Step und Aktualität der Daten die Reaktionsdynamik.",
    "NIGHT_DISCHARGE_ENABLED": "Aktiviert nur innerhalb des gültigen Nachtfensters eine feste Basisentladung, sofern MANUAL_MODE=AUTO und die Schutzbedingungen erfüllt sind.",
    "NIGHT_DISCHARGE_POWER_W": "Feste Entladeleistung im Nachtmodus. Sie wird nicht fortlaufend an die aktuelle Haus-Netzleistung angepasst. Ein zu hoher Wert kann deshalb bei geringer Hauslast Einspeisung verursachen und muss zur eigenen Anlage passen.",
    "NIGHT_DISCHARGE_STOP_SOC_PERCENT": "Optionale zusätzliche Nachtreserve. Bei Erreichen wird die feste Nacht-Basisentladung pausiert; normale AUTO-Regelung darf im selben Nachtfenster weiterarbeiten, solange globale Schutzbedingungen dies zulassen.",
    "REST_SURPLUS_HARVEST_ENABLED": "Masterfreigabe der Restüberschuss-Ernte. Die Funktion darf zusätzliche Ladung nutzen, wenn die spezifizierten Harvestbedingungen erfüllt sind, darf aber keine Entladung auslösen und die Primärspeicherpriorität nicht strategisch verletzen.",
    "HARVEST_FAST_CAPTURE_MODE": "Fast Capture ist ein strikt zusätzliches Overlay auf der bestehenden langsamen Baseline. FULL_IDLE und NEAR_LIMIT dürfen A400/R100 nutzen; RESERVE_UNKNOWN erzeugt kein Fast-Overlay. Shadow berechnet dieselbe Kandidatenlogik, verändert aber weder Zielwert noch Command. Roh-SOC, unabhängige Leistungsbeobachtung, Cross-Charge, Command-Safety und vorhandene Gerätegrenzen bleiben autoritativ.",
    "HARVEST_HIGH_SMA_SOC_ENABLED": "Schaltet den High-SOC-Parallel-Harvest innerhalb der Gesamt-Harvestlogik frei. Eintritt, Hysterese, Export und Zeitprofil bestimmen, wann er tatsächlich aktiv werden darf.",
    "HARVEST_HIGH_SMA_SOC_ENTER_PERCENT": "Eintrittsschwelle der High-SOC-Hysterese. Sie muss oberhalb des Austrittswerts und höchstens an der Voll-SOC-Schwelle liegen.",
    "HARVEST_HIGH_SMA_SOC_EXIT_PERCENT": "Austrittsschwelle der High-SOC-Hysterese. Der Abstand zur Eintrittsschwelle verhindert unmittelbares Flattern um einen einzelnen SOC-Wert.",
    "HARVEST_SMA_FULL_SOC_PERCENT": "Grenze für den Voll-/Idle-Zweig des Primärspeichers innerhalb Harvest. Sie ist Teil der geordneten SOC-Schwellen und kein allgemeines Batterie-Maximum.",
    "HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W": "Freigabeschwelle für den High-SOC-Eintritt. Der Wert ist kein Netz-Zielwert und beschreibt nicht, wie viel Export nach der Regelung verbleiben soll.",
    "REST_SURPLUS_MIN_EXPORT_W": "Entry-Schwelle für den Near-Limit-/Restüberschusszweig. Ein Restexportwert ist nicht automatisch der absolute Zendure-Ladesollwert.",
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS": "Bestätigt High-SOC-Freigabebedingung über reale Zeit. Profilfenster können abweichende, bereits spezifizierte Bestätigungszeiten verwenden; daher ist dieser Wert nicht zu jeder Tageszeit allein maßgeblich.",
    "HARVEST_HIGH_SMA_SOC_HOLD_SECONDS": "Hält einen zuvor aktiven Harvestzustand nach kurzfristigem Wegfall der Freigabebedingung begrenzt aufrecht, solange insbesondere die Exit-SOC-Bedingung nicht verletzt ist.",
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": "Bestätigt Near-Limit-/Restexportbedingungen über Zeit, damit kurze Spitzen nicht sofort einen Harvest-Eintritt auslösen.",
    "CROSS_CHARGE_ENABLED": "Aktiviert die symmetrische Konfliktprüfung zwischen Zendure-Sollrichtung und frischer Zweitbatterieleistung. Der Schutz reduziert gegenläufige Ziele proportional und kehrt die Richtung nicht selbst um.",
    "SECOND_BATTERY_STALE_BLOCK_CHARGE": "Konservativer Fallback bei veralteten Zweitbatteriedaten. Aktiv bedeutet, dass neue Zendure-Ladung bei fehlender verlässlicher Gegenflussbewertung blockiert werden kann.",
    "CROSS_CHARGE_SIGNIFICANT_W": "Engage-Schwelle für relevanten Gegenfluss. Die interne Release-Hysterese beträgt bei positivem Engage max(20 W, Engage/2). Bei aktivem Cross-Charge muss Engage größer als 0 W sein.",
    "COMMAND_EFFECT_MIN_TARGET_W": "Diagnosegrenze für ausreichend große Sollwerte. Unterhalb dieser Grenze ist Kommandowirkung nicht robust bewertbar; der Wert ist keine Mindestleistung des Geräts.",
    "COMMAND_EFFECT_MIN_W": "Mindest-Istleistung für eine belastbare Richtungsreaktion. Eine erreichte Richtungsreaktion ist noch kein vollständiger Sollwerttracking-Nachweis.",
    "COMMAND_EFFECT_TIMEOUT_SECONDS": "Zeit für die Bestätigung persistenter Nichtwirkung desselben Intents. Kleine Zieländerungen in derselben Richtung sollen die zusammenhängende Nichtwirkungs-Episode nicht ständig neu starten.",
    "COMMAND_EFFECT_TOLERANCE_W": "Absolute Komponente der Sollwerttracking-Toleranz. Wirksam ist das Maximum aus diesem Wert und der relativen Prozenttoleranz.",
    "COMMAND_EFFECT_TOLERANCE_PERCENT": "Relative Komponente der Sollwerttracking-Toleranz. Wirksam ist das Maximum aus absoluter W-Toleranz und |Soll| mal Prozenttoleranz.",
    "COMMAND_EFFECT_FORCE_RESEND_SECONDS": "Recovery-Zeit für einen erzwungenen vollständigen Resend bei anhaltender bestätigter Nichtwirkung. Keine normale periodische Command-Wiederholung.",
    "COMMAND_RESYNC_COOLDOWN_SECONDS": "Drosselt identische Resync-/Recovery-Wiederholungen und verhindert unnötige Publish-Schleifen.",
    "COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS": "Überwacht die physische Wirkung einer aktiven sicherheitsrelevanten 0-W-Neutralisierung.",
    "ZENDURE_COMMAND_STATE_FRESH_SECONDS": "Aktualitätsgrenze für den vollständig rückgelesenen Command-State aus smartMode, acMode, inputLimit und outputLimit.",
    "ZENDURE_COMMAND_STATE_RETRY_SECONDS": "Abstand für das erneute Anfordern/Herstellen eines vollständigen Command-States im vorgesehenen Recoverypfad.",
    "ZENDURE_SMART_MODE_RETRY_SECONDS": "Abstand für SmartMode-bezogene Wiederholungsversuche, wenn der erforderliche Gerätevertrag noch nicht bestätigt ist.",
    "COMMAND_RESYNC_STALE_MIN_SECONDS": "Mindestalter für einen auf veralteten Daten basierenden MQTT-Recovery-/Resyncfall. Der Wert beschreibt Recovery, nicht normale Stellgeschwindigkeit.",
    "COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS": "Legacy-/Notfalloption für aggressiveren Resync nach MQTT-Recovery. Sie erhöht potenziell Recovery-Publishes und ist keine normale Regeloption.",
}

for _key in (
    "MANUAL_FIXED_DISCHARGE_POWER_W", "MANUAL_FIXED_DISCHARGE_TARGET_SOC", "MANUAL_DISCHARGE_AFTER_TARGET",
    "MANUAL_FIXED_CHARGE_POWER_W", "MANUAL_FIXED_CHARGE_TARGET_SOC", "MANUAL_CHARGE_AFTER_TARGET",
):
    RICH_EXTENDED.setdefault(_key, SHORT_HELP.get(_key, "") + " Der Parameter wirkt nur im zugehörigen festen manuellen Profil und bleibt durch globale SOC-/Leistungsgrenzen geschützt.")
for _key in ("NIGHT_START_HOUR", "NIGHT_START_MINUTE", "NIGHT_END_HOUR", "NIGHT_END_MINUTE"):
    RICH_EXTENDED[_key] = "Teil des logischen Nachtzeitfensters. Die Oberfläche fasst Stunde und Minute zu Start- bzw. Endzeit im Format HH:MM zusammen; Über-Mitternacht-Fenster sind zulässig, identische Start-/Endzeit nicht."
for _key in (
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO", "HARVEST_PRIMARY_CHARGE_FLOOR_W",
    "HARVEST_PRIMARY_CHARGE_RESTART_RATIO", "HARVEST_PRIMARY_CHARGE_RESTART_W",
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W",
):
    RICH_EXTENDED[_key] = SHORT_HELP[_key] + " Zusammen gilt die Invariante Floor <= Restart <= Near-Limit <= bekannte maximale Primärspeicher-Ladeleistung."
for _key in (
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING", "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY", "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON",
):
    RICH_EXTENDED[_key] = SHORT_HELP[_key] + " Der Anteil beschreibt eine Strategieallokation und ist kein direkter Zendure-Leistungssollwert."


# V12.12.1: RICH help must answer the operational "when" question explicitly.
# These texts describe existing contracts only; they introduce no new thresholds.
RICH_WHEN = {
    "MANUAL_MODE": "Die Betriebsart wird in jedem Regelzyklus vor Nacht- und AUTO-Regelung ausgewertet. Ein manueller Modus ungleich AUTO hat Vorrang vor beiden; Schutz- und Safe-State-Bedingungen können das angeforderte Ziel weiterhin begrenzen oder neutralisieren.",
    "MANUAL_FIXED_DISCHARGE_POWER_W": "Der Wert wird nur verwendet, wenn MANUAL_MODE auf Feste Entladung steht, der aktuelle Zendure-SOC gültig ist und das Entlade-Ziel noch nicht erreicht wurde. Die globale maximale Entladeleistung und der Mindest-SOC bleiben harte Grenzen.",
    "MANUAL_FIXED_DISCHARGE_TARGET_SOC": "Der Ziel-SOC wird nur im manuellen Modus Feste Entladung ausgewertet. Er muss unter dem aktuellen SOC liegen und darf die globale MIN-SOC-Grenze nicht unterschreiten.",
    "MANUAL_DISCHARGE_AFTER_TARGET": "Die Folgeaktion wird genau dann ausgewertet, wenn eine aktive feste Entladung ihren Ziel-SOC erreicht. AUTO gibt anschließend wieder an die normale Regelung zurück; STOP/HOLD fordert aktive 0-W-Neutralität.",
    "MANUAL_FIXED_CHARGE_POWER_W": "Der Wert wird nur verwendet, wenn MANUAL_MODE auf Feste Ladung steht, der aktuelle Zendure-SOC gültig ist und das Lade-Ziel noch nicht erreicht wurde. Die globale maximale Ladeleistung und der Maximal-SOC bleiben harte Grenzen.",
    "MANUAL_FIXED_CHARGE_TARGET_SOC": "Der Ziel-SOC wird nur im manuellen Modus Feste Ladung ausgewertet. Er muss über dem aktuellen SOC liegen und darf die globale MAX-SOC-Grenze nicht überschreiten.",
    "MANUAL_CHARGE_AFTER_TARGET": "Die Folgeaktion wird genau dann ausgewertet, wenn eine aktive feste Ladung ihren Ziel-SOC erreicht. AUTO gibt anschließend wieder an die normale Regelung zurück; STOP/HOLD fordert aktive 0-W-Neutralität.",
    "MAX_CHARGE_POWER_W": "Die Grenze wirkt in jedem Zweig, der Zendure-Ladung anfordern kann: AUTO, Harvest und feste Ladung. Sie begrenzt den berechneten Zielwert unabhängig davon, welcher Zweig ihn erzeugt hat.",
    "MAX_DISCHARGE_POWER_W": "Die Grenze wirkt in jedem Zweig, der Zendure-Entladung anfordern kann: AUTO, Nachtbetrieb und feste Entladung. Sie begrenzt den berechneten Zielwert unabhängig davon, welcher Zweig ihn erzeugt hat.",
    "MIN_SOC_PERCENT": "Die Untergrenze wird bei allen Entladeentscheidungen geprüft. Erreichen der Grenze ist bei gültigen Daten ein normaler Schutz-/HOLD-Zustand; Entladeprofile und Nachtreserve dürfen sie nicht unterschreiten.",
    "MAX_SOC_PERCENT": "Die Obergrenze wird bei allen Ladeentscheidungen geprüft. Erreichen der Grenze ist bei gültigen Daten ein normaler Schutz-/HOLD-Zustand; Ladeprofile dürfen sie nicht überschreiten.",
    "DEADBAND_W": "Die Totzone wird in der normalen AUTO-Netzregelung ausgewertet, wenn keine höher priorisierte Betriebs- oder Schutzbedingung greift. Innerhalb der Totzone wird keine unnötige Nachregelung angestrebt; ausdrücklich definierte Harvest-Spezialzweige besitzen eigene Eintrittsbedingungen.",
    "CONTROL_GAIN": "Der Gain wirkt bei einer aktiven AUTO-Korrektur auf die aktuelle wirksame Netzabweichung. Nach dieser Rohkorrektur folgen Glättung, Schrittbegrenzung, Leistungs-/SOC-Limits, Cross-Charge-Schutz und der Commandpfad.",
    "SMOOTHING_FACTOR": "Die Glättung wirkt nach der Rohzielberechnung auf Änderungen des AUTO-Zielwerts. Sie wird relevant, sobald sich das Rohziel gegenüber dem bisherigen Ziel verändert.",
    "MAX_POWER_STEP_W": "Die Schrittbegrenzung wirkt bei Zielwertänderungen der normalen Reglerpfade und begrenzt die Änderung von einem Regelzyklus zum nächsten. Sie ersetzt keine absolute Leistungsgrenze.",
    "MIN_COMMAND_CHANGE_W": "Der Wert wirkt erst im Commandpfad nach der internen Zielwertberechnung. Er entscheidet, ob eine kleine Zielwertänderung tatsächlich erneut per MQTT publiziert werden muss.",
    "MOVING_AVERAGE_SAMPLES": "Die Mittelwertbildung wirkt auf die für AUTO verwendete Netzleistung, sobald mehrere Messwerte vorliegen. Zusammen mit dem Regelintervall bestimmt die Samplezahl die zeitliche Glättung der Eingangsgröße.",
    "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W": "Die Schwelle wird bei normaler AUTO-Ladung geprüft. Erst wenn nach den relevanten Abzügen und Reserven ausreichend wirksamer Überschuss verbleibt, wird normale AUTO-Ladung freigegeben.",
    "SMA_GUARD_RAMP_DOWN_W": "Die Schrittweite wird nur in den dafür vorgesehenen AUTO-Schutz-/Ramp-down-Pfaden verwendet, wenn eine bestehende Ladung kontrolliert reduziert werden muss. Sie ist nicht die allgemeine Stellschrittgrenze.",
    "INTERVAL_SECONDS": "Der Wert bestimmt den nominalen Abstand zwischen Regelzyklen. Er beeinflusst deshalb zeitlich alle zyklischen AUTO-/Harvest-/Diagnosebewertungen, ohne deren fachliche Eintrittsbedingungen zu ersetzen.",
    "NIGHT_DISCHARGE_ENABLED": "Der Nachtmodus kann nur im konfigurierten Zeitfenster und bei MANUAL_MODE=AUTO aktiv werden. Gültiger SOC, globale Schutzgrenzen und weitere Safety-Bedingungen bleiben Voraussetzung.",
    "NIGHT_DISCHARGE_POWER_W": "Die feste Leistung wird nur während eines aktiven Nachtfensters verwendet, wenn Nachtbetrieb freigegeben ist und keine Reserve-/SOC-/Safety-Bedingung die Entladung stoppt. Sie wird nicht anhand der aktuellen Hauslast nachgeführt.",
    "NIGHT_DISCHARGE_STOP_SOC_PERCENT": "Die zusätzliche Nachtreserve wird nur ausgewertet, wenn sie gesetzt ist und die feste Nachtentladung aktiv werden könnte. Bei Erreichen pausiert sie die feste Basisentladung; die globale MIN-SOC-Grenze bleibt zusätzlich wirksam.",
    "NIGHT_START_HOUR": "Startstunde und Startminute bilden gemeinsam die logische Startzeit des Nachtfensters. Die UI behandelt beide technischen Werte als ein HH:MM-Feld; ein Fenster über Mitternacht ist zulässig.",
    "NIGHT_START_MINUTE": "Startstunde und Startminute bilden gemeinsam die logische Startzeit des Nachtfensters. Die UI behandelt beide technischen Werte als ein HH:MM-Feld; ein Fenster über Mitternacht ist zulässig.",
    "NIGHT_END_HOUR": "Endstunde und Endminute bilden gemeinsam die logische Endzeit des Nachtfensters. Beim Verlassen des Fensters ist eine aktive 0-W-Neutralisierung Teil des Sicherheitsvertrags.",
    "NIGHT_END_MINUTE": "Endstunde und Endminute bilden gemeinsam die logische Endzeit des Nachtfensters. Beim Verlassen des Fensters ist eine aktive 0-W-Neutralisierung Teil des Sicherheitsvertrags.",
    "REST_SURPLUS_HARVEST_ENABLED": "Die Masterfreigabe wird nur in AUTO-Betrieb berücksichtigt. Erst zusätzliche Harvest-Freigabebedingungen wie Primärspeicherzustand, Export, Zeitprofil und Schutzgrenzen entscheiden, ob tatsächlich zusätzliche Zendure-Ladung angefordert wird.",
    "HARVEST_FAST_CAPTURE_MODE": "Fast Capture wird ausschließlich in AUTO mit frischen, gültigen Netz-, Primärspeicher-, Zendure-SOC- und unabhängigen Zendure-Leistungsdaten bewertet. Aktiv darf erst nach erfolgreicher Shadow-Evidenz produktiv verwendet werden; Hard-Aborts, Cross-Charge und Command-Recovery besitzen Vorrang.",
    "HARVEST_HIGH_SMA_SOC_ENABLED": "Der Schalter wirkt nur bei aktivierter Restüberschuss-Ernte. Für einen tatsächlichen High-SOC-Eintritt müssen zusätzlich Primärspeicher-SOC, Exportbedingung, Zeitprofil und Bestätigungszeit passen.",
    "HARVEST_HIGH_SMA_SOC_ENTER_PERCENT": "Die Eintrittsschwelle wird nur bei aktivem High-SOC-Parallel-Harvest und gültigem aktuellem Primärspeicher-SOC ausgewertet. Ein Eintritt benötigt zusätzlich die Export-/Zeit-/Bestätigungsbedingungen; der niedrigere Austrittswert beendet den Zustand wieder.",
    "HARVEST_HIGH_SMA_SOC_EXIT_PERCENT": "Die Austrittsschwelle wird ausgewertet, wenn ein High-SOC-Harvestzustand aktiv ist. Fällt der Primärspeicher-SOC auf bzw. unter diese Grenze, wird der High-SOC-Zustand verlassen; der Abstand zur Eintrittsschwelle verhindert häufiges Hin- und Herschalten.",
    "HARVEST_SMA_FULL_SOC_PERCENT": "Die Schwelle wird für den Voll-/Idle-Zweig des Primärspeichers innerhalb Harvest ausgewertet. Sie ist nicht mit dem globalen Zendure-MAX-SOC gleichzusetzen.",
    "HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W": "Die Exportgrenze wird beim Eintritt in High-SOC-Harvest geprüft. Sie qualifiziert die Freigabe; sie ist ausdrücklich kein gewünschter Restexport nach der Regelung.",
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS": "Die Bestätigungszeit läuft nur, solange die High-SOC-Freigabebedingungen zusammenhängend erfüllt bleiben. Profilfenster können spezifizierte abweichende Zeiten verwenden.",
    "HARVEST_HIGH_SMA_SOC_HOLD_SECONDS": "Die Haltezeit wird erst relevant, nachdem High-SOC-Harvest bereits aktiv war und eine Freigabebedingung kurzzeitig wegfällt. Harte Exit-/Schutzbedingungen können den Zustand trotzdem sofort beenden.",
    "REST_SURPLUS_MIN_EXPORT_W": "Die Schwelle wird für den Near-Limit-/Restüberschuss-Eintritt geprüft. Sie entscheidet über die Freigabe des Zweigs, nicht über den endgültigen absoluten Zendure-Ladesollwert.",
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": "Die Bestätigungszeit läuft nur, solange die Near-Limit-/Restexport-Freigabebedingungen zusammenhängend erfüllt bleiben. Kurze Exportspitzen sollen dadurch nicht sofort einen Eintritt auslösen.",
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO": "Der Ratio-Wert wird nur verwendet, wenn kein positiver absoluter Floor-Wert gesetzt ist. Er wird aus der bekannten maximalen Primärspeicher-Ladeleistung abgeleitet und bildet die untere Harvest-Schwelle.",
    "HARVEST_PRIMARY_CHARGE_RESTART_RATIO": "Der Ratio-Wert wird nur verwendet, wenn kein positiver absoluter Restart-Wert gesetzt ist. Er bildet die Wiederanlaufschwelle oberhalb des Floors.",
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO": "Der Ratio-Wert wird nur verwendet, wenn kein positiver absoluter Near-Limit-Wert gesetzt ist. Er kennzeichnet den Bereich nahe der Primärspeicher-Ladegrenze.",
    "HARVEST_PRIMARY_CHARGE_FLOOR_W": "Ein positiver Wert ersetzt den zugehörigen Floor-Ratio-Wert vollständig. Leer bzw. automatisch bedeutet, dass ZEC wieder die Ratio-Ableitung aus der maximalen Primärspeicher-Ladeleistung verwendet.",
    "HARVEST_PRIMARY_CHARGE_RESTART_W": "Ein positiver Wert ersetzt den zugehörigen Restart-Ratio-Wert vollständig. Leer bzw. automatisch bedeutet, dass ZEC wieder die Ratio-Ableitung verwendet.",
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W": "Ein positiver Wert ersetzt den zugehörigen Near-Limit-Ratio-Wert vollständig. Leer bzw. automatisch bedeutet, dass ZEC wieder die Ratio-Ableitung verwendet.",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING": "Der Anteil wird nur im zugehörigen morgendlichen Harvest-Zeitprofil verwendet, wenn der betreffende Harvestzweig aktiv ist. Er beschreibt eine Strategieallokation für den Primärspeicher und ist kein direkter Zendure-Sollwert.",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY": "Der Anteil wird nur im zugehörigen mittäglichen Harvest-Zeitprofil verwendet, wenn der betreffende Harvestzweig aktiv ist. Er beschreibt eine Strategieallokation für den Primärspeicher und ist kein direkter Zendure-Sollwert.",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON": "Der Anteil wird nur im zugehörigen nachmittäglichen Harvest-Zeitprofil verwendet, wenn der betreffende Harvestzweig aktiv ist. Er beschreibt eine Strategieallokation für den Primärspeicher und ist kein direkter Zendure-Sollwert.",
    "CROSS_CHARGE_ENABLED": "Der Schutz wird nur wirksam, wenn ausreichend aktuelle Zweitbatteriedaten für eine belastbare Gegenflussbewertung vorliegen. Er reduziert gegenläufige Zendure-Ziele proportional und kehrt die Richtung nicht selbst um.",
    "SECOND_BATTERY_STALE_BLOCK_CHARGE": "Die Option wird relevant, wenn Zweitbatteriedaten die zulässige Aktualitätsgrenze überschreiten. Sie bestimmt dann, ob neue Zendure-Ladung vorsorglich blockiert wird, weil Gegenfluss nicht zuverlässig bewertet werden kann.",
    "CROSS_CHARGE_SIGNIFICANT_W": "Die Schwelle wird bei aktuellem Zweitbatterie-Leistungswert und aktivem Cross-Charge-Schutz ausgewertet. Ab dieser Gegenflussstärke greift die Schutzlogik; die niedrigere Rücknahmeschwelle verhindert häufiges Ein-/Ausschalten nahe der Grenze.",
    "COMMAND_EFFECT_MIN_TARGET_W": "Die Diagnosegrenze wird nur für aktive Sollwerte ungleich 0 W verwendet. Unterhalb dieser Größe wird die Wirkung als nicht robust bewertbar behandelt und nicht fälschlich als bestätigt gewertet.",
    "COMMAND_EFFECT_MIN_W": "Die Mindest-Istleistung wird bei der Prüfung einer angeforderten Lade- oder Entladerichtung verwendet. Sie belegt höchstens eine belastbare Richtungsreaktion, nicht automatisch das Sollwerttracking.",
    "COMMAND_EFFECT_TIMEOUT_SECONDS": "Der Timeout läuft während einer zusammenhängenden Wirkungsprüfung desselben fachlichen Intents. Kleine Sollwertänderungen innerhalb derselben Richtung sollen eine anhaltende Nichtwirkung nicht analytisch verstecken.",
    "COMMAND_EFFECT_TOLERANCE_W": "Die absolute Toleranz wird beim Sollwerttracking mit der relativen Prozenttoleranz verglichen. Für die Bewertung gilt jeweils die größere der beiden Grenzen.",
    "COMMAND_EFFECT_TOLERANCE_PERCENT": "Die relative Toleranz wird aus dem Betrag des Sollwerts berechnet und mit der absoluten W-Toleranz verglichen. Für die Bewertung gilt jeweils die größere Grenze.",
    "COMMAND_EFFECT_FORCE_RESEND_SECONDS": "Die Zeit wird erst bei anhaltender bestätigter Nichtwirkung relevant. Danach darf ZEC im spezifizierten Recoverypfad den vollständigen Gerätezustand erneut senden; dies ist keine zyklische Normalwiederholung.",
    "COMMAND_RESYNC_COOLDOWN_SECONDS": "Der Cooldown wird nach einem Resync-/Recovery-Versuch ausgewertet. Er verhindert, dass derselbe vollständige Wiederabgleich unnötig häufig wiederholt wird.",
    "COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS": "Der Timeout wird bei sicherheitsrelevanten 0-W-Zielen verwendet. Bleibt physische Leistung bestehen, kann ZEC die vollständige 0-W-Zustandsneutralisierung mit AC-Modus und beiden Limits erneut anfordern.",
    "ZENDURE_COMMAND_STATE_FRESH_SECONDS": "Die Grenze wird auf den vollständig rückgelesenen Gerätezustand aus smartMode, acMode, inputLimit und outputLimit angewandt. Überschreitet dessen Datenalter die Grenze, gilt der Zustand nicht mehr als aktuell genug für einen belastbaren Commandnachweis.",
    "ZENDURE_COMMAND_STATE_RETRY_SECONDS": "Das Intervall wird verwendet, wenn der vollständige Gerätezustand noch nicht konsistent bestätigt ist und im vorgesehenen Recoverypfad erneut angefordert bzw. hergestellt werden muss.",
    "ZENDURE_SMART_MODE_RETRY_SECONDS": "Das Intervall wird relevant, wenn der erforderliche smartMode noch nicht bestätigt ist. Wiederholungen bleiben auf den Recoverypfad beschränkt und sollen keine dauerhafte Schreibschleife erzeugen.",
    "COMMAND_RESYNC_STALE_MIN_SECONDS": "Die Mindestdauer wird nur für Recovery nach ausreichend lange veralteten MQTT-/Command-Daten ausgewertet. Sie ist keine normale Stell- oder Regelverzögerung.",
    "COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS": "Die Legacy-/Notfalloption wird beim Wiederkehren der MQTT-Verbindung ausgewertet. Aktiv erzwingt sie aggressiver einen vollständigen Wiederabgleich und kann dadurch zusätzliche Publishes verursachen.",
}

RICH_RISK_BY_CATEGORY = {
    "Betriebsart & manuelle Steuerung": "Fehlkonfiguration kann eine feste Lade-/Entladeanforderung oder einen unerwarteten Folgeübergang auslösen. Globale SOC-/Leistungsgrenzen und Safe-State bleiben übergeordnet.",
    "Leistungsgrenzen & SOC-Schutz": "Diese Werte sind anlagenbezogene Schutzgrenzen. Zu hohe Grenzen können Hardware-/Batterieschutz schwächen; unpassend niedrige Grenzen können nutzbare Leistung oder SOC-Bereich unnötig einschränken.",
    "AUTO-Regelung": "Unpassend aggressive Kombinationen können Pendeln, häufigere Sollwertänderungen und unnötige Commandaktivität begünstigen; zu träge Kombinationen können Netzabweichungen länger bestehen lassen.",
    "Nachtbetrieb": "Eine unpassende feste Nachtleistung kann bei geringer Hauslast Einspeisung verursachen. Zeitfenster, Reserve-SOC und globale SOC-Grenzen müssen zur eigenen Anlage und Nutzung passen.",
    "Harvest / Restüberschuss": "Unpassende Schwellen oder Allokationen können Restexport unnötig bestehen lassen oder die gewünschte Primärspeicherpriorität verschieben. Die geordneten Schwellen und Override-Regeln müssen konsistent bleiben.",
    "Cross-Charge-Schutz": "Eine zu hohe Gegenflussschwelle kann relevanten Cross-Charge übersehen; eine zu niedrige Schwelle kann bei Messrauschen unnötig eingreifen. Aktuelle und eindeutig interpretierbare Zweitbatteriedaten sind Voraussetzung.",
    "Kommandowirkung & Resync": "Zu aggressive Diagnose-/Recovery-Zeiten können unnötige Wiederholpublishes erzeugen; zu großzügige Zeiten verzögern die Erkennung echter Nichtwirkung. Publish allein bleibt kein Wirkungsnachweis.",
}

RICH_DEPENDENCY_HELP = {
    "Betriebsart & manuelle Steuerung": "Die unten genannten Werte bestimmen Profil, Leistungs-/SOC-Grenzen oder Folgeaktion des gewählten manuellen Modus.",
    "Leistungsgrenzen & SOC-Schutz": "Die unten genannten Einstellungen stehen in direkter Schutz- oder Zielbeziehung zu dieser Grenze.",
    "AUTO-Regelung": "AUTO-Parameter wirken als aufeinanderfolgende Teile derselben Zielwertpipeline; die unten genannten Beziehungen zeigen die wichtigsten Kopplungen.",
    "Nachtbetrieb": "Nachtbetrieb ist an Aktivierung, logisches Zeitfenster, feste Leistung und SOC-Schutz gekoppelt. Die unten genannten Beziehungen zeigen die direkte Abhängigkeit.",
    "Harvest / Restüberschuss": "Harvest nutzt mehrere Freigabeschwellen und Allokationswerte gemeinsam. Positive absolute W-Werte können zugehörige Ratio-Werte ersetzen; die unten genannten Beziehungen zeigen diese Kopplungen.",
    "Cross-Charge-Schutz": "Der Schutz benötigt aktuelle Zweitbatteriedaten und eine konsistente Gegenflussschwelle. Die unten genannten Beziehungen bestimmen Freigabe und Fallback.",
    "Kommandowirkung & Resync": "Wirkungsdiagnose und Recovery verwenden getrennte Schwellen, Toleranzen und Zeitbedingungen. Die unten genannten Beziehungen zeigen die wichtigsten Abhängigkeiten.",
}

EFFECT_INCREASE = {
    "MAX_CHARGE_POWER_W": "Erlaubt höhere Ladeziele, soweit Hardware, SOC und weitere Limiter dies zulassen.",
    "MAX_DISCHARGE_POWER_W": "Erlaubt höhere Entladeziele, soweit Hardware, SOC und weitere Limiter dies zulassen.",
    "MIN_SOC_PERCENT": "Schützt mehr Restenergie; Entladung wird früher begrenzt.",
    "MAX_SOC_PERCENT": "Erlaubt Ladung bis zu einem höheren SOC; längere hohe SOC-Verweilzeiten können zunehmen.",
    "CONTROL_GAIN": "Korrigiert einen größeren Anteil der Netzabweichung pro Zyklus; reagiert schneller, kann aber nervöser werden.",
    "SMOOTHING_FACTOR": "Gewichtet das neue Ziel stärker; reagiert schneller und glättet weniger.",
    "MAX_POWER_STEP_W": "Erlaubt größere Zielwertsprünge pro Regelzyklus.",
    "DEADBAND_W": "Toleriert mehr Restabweichung um 0 W und reduziert Nachregelaktivität.",
    "MIN_COMMAND_CHANGE_W": "Unterdrückt mehr kleine MQTT-Updates; reduziert Publish-Frequenz, kann Feinkorrektur verzögern.",
    "MOVING_AVERAGE_SAMPLES": "Vergrößert das Beobachtungsfenster; ruhiger, aber träger.",
    "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W": "Verlangt mehr Überschuss, bevor normale AUTO-Ladung freigegeben wird.",
    "SMA_GUARD_RAMP_DOWN_W": "Baut eine bestehende Ladung in den zugehörigen Ramp-down-Pfaden schneller ab.",
    "INTERVAL_SECONDS": "Vergrößert den nominalen Zyklusabstand; reduziert Reaktionshäufigkeit.",
    "NIGHT_DISCHARGE_POWER_W": "Erhöht die feste Nachtentladung. Bei kleiner Hauslast steigt das Risiko von Netzeinspeisung.",
    "NIGHT_DISCHARGE_STOP_SOC_PERCENT": "Pausiert die feste Nachtentladung bei höherem SOC und hält mehr Nachtreserve zurück.",
    "HARVEST_HIGH_SMA_SOC_ENTER_PERCENT": "Der High-SOC-Eintritt erfolgt erst bei höherem Primärspeicher-SOC.",
    "HARVEST_HIGH_SMA_SOC_EXIT_PERCENT": "Der High-SOC-Bereich wird früher verlassen; die Hysterese wird bei unverändertem Enter kleiner.",
    "HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W": "Verlangt mehr Netzexport für den High-SOC-Eintritt.",
    "REST_SURPLUS_MIN_EXPORT_W": "Verlangt mehr Netzexport für Near-Limit-/Restüberschuss-Entry.",
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS": "Verlangt eine länger bestätigte Freigabebedingung und filtert kurze Ereignisse stärker.",
    "HARVEST_HIGH_SMA_SOC_HOLD_SECONDS": "Hält einen zuvor aktiven Harvestzustand länger über kurze kurze Lücken der Freigabebedingung.",
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": "Verlangt einen länger bestätigten Restexportzustand vor Entry.",
    "CROSS_CHARGE_SIGNIFICANT_W": "Ignoriert kleinere Gegenflüsse und greift erst bei stärkerem Konflikt ein.",
    "COMMAND_EFFECT_MIN_TARGET_W": "Mehr kleine Sollwerte werden als nicht robust bewertbar eingestuft.",
    "COMMAND_EFFECT_MIN_W": "Erfordert eine größere Istleistung, bevor eine Richtungsreaktion als belastbar gilt.",
    "COMMAND_EFFECT_TIMEOUT_SECONDS": "Gibt einer Intention länger Zeit, bevor persistente Nichtwirkung bestätigt wird.",
    "COMMAND_EFFECT_TOLERANCE_W": "Erweitert die absolute Soll-Ist-Toleranz und macht Tracking großzügiger.",
    "COMMAND_EFFECT_TOLERANCE_PERCENT": "Erweitert die relative Soll-Ist-Toleranz besonders bei größeren Sollwerten.",
    "COMMAND_EFFECT_FORCE_RESEND_SECONDS": "Wartet länger bis zu einem möglichen erzwungenen Recovery-Resend.",
    "COMMAND_RESYNC_COOLDOWN_SECONDS": "Drosselt wiederholte Resyncs stärker.",
    "COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS": "Gibt der 0-W-Neutralisierung länger Zeit, bevor Nichtwirkung bestätigt werden kann.",
}
EFFECT_DECREASE = {
    "CONTROL_GAIN": "Korrigiert sanfter und langsamer.",
    "SMOOTHING_FACTOR": "Glättet stärker und reagiert langsamer.",
    "MAX_POWER_STEP_W": "Begrenzt Zieländerungen stärker und kann die Konvergenz verlangsamen.",
    "DEADBAND_W": "Verfolgt das 0-W-Ziel enger, reagiert aber empfindlicher auf Rauschen.",
    "MIN_COMMAND_CHANGE_W": "Erlaubt feinere Leistungsupdates, erhöht aber die mögliche Publish-Frequenz.",
    "MOVING_AVERAGE_SAMPLES": "Reagiert schneller auf Einzeländerungen und glättet weniger.",
    "INTERVAL_SECONDS": "Erhöht die Regelhäufigkeit; aktive Arbeit und externe Pfade bleiben zusätzliche Laufzeitanteile.",
    "CROSS_CHARGE_SIGNIFICANT_W": "Reagiert bereits auf kleinere Gegenflüsse; der Wert muss bei aktivem Schutz trotzdem > 0 bleiben.",
    "COMMAND_RESYNC_COOLDOWN_SECONDS": "Erlaubt häufigere Recovery-Versuche; bei 0 besteht erhöhte Publish-Sturmgefahr.",
}

EFFECT_ENABLE = {
    "CROSS_CHARGE_ENABLED": "Aktiviert die Gegenfluss-Schutzlogik bei frischen Zweitbatteriedaten.",
    "SECOND_BATTERY_STALE_BLOCK_CHARGE": "Blockiert konservativ neue Ladung, wenn die erforderliche Zweitbatteriebewertung veraltet ist.",
    "NIGHT_DISCHARGE_ENABLED": "Erlaubt die feste Nacht-Basisentladung im gültigen Fenster, sofern MANUAL_MODE=AUTO und Schutzbedingungen erfüllt sind.",
    "REST_SURPLUS_HARVEST_ENABLED": "Erlaubt die spezifizierten Harvestzweige; die einzelnen Eintritts- und Schutzbedingungen gelten weiterhin.",
    "HARVEST_FAST_CAPTURE_MODE": "Shadow aktiviert nur Kandidaten-/Evidenzberechnung; Aktiv erlaubt zusätzlich das A400/R100-Overlay innerhalb aller bestehenden Schutz- und Headroomgrenzen.",
    "HARVEST_HIGH_SMA_SOC_ENABLED": "Erlaubt zusätzlich den High-SOC-Harvestzweig innerhalb der Master-Harvestlogik.",
    "COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS": "Erweitert das Legacy-/Notfall-Resyncverhalten nach MQTT-Recovery.",
}
EFFECT_DISABLE = {
    "CROSS_CHARGE_ENABLED": "Deaktiviert diese zusätzliche Gegenfluss-Schutzschicht; normale SOC-/Leistungsgrenzen bleiben bestehen.",
    "SECOND_BATTERY_STALE_BLOCK_CHARGE": "Entfernt den konservativen Stale-Block und reduziert damit einen Schutzmechanismus.",
    "NIGHT_DISCHARGE_ENABLED": "Die Nachtwerte bleiben gespeichert, erzeugen aber keine feste Nacht-Basisentladung.",
    "REST_SURPLUS_HARVEST_ENABLED": "Alle davon abhängigen Harvestwerte bleiben gespeichert, sind aber derzeit ohne Wirkung.",
    "HARVEST_FAST_CAPTURE_MODE": "Aus entfernt jede Fast-Capture-Wirkung und setzt ein bestehendes Overlay sicher auf die normale Baseline zurück.",
    "HARVEST_HIGH_SMA_SOC_ENABLED": "Deaktiviert nur den High-SOC-Zweig; andere freigegebene Harvestzweige können weiterhin arbeiten.",
}

FORMULAS = {
    "CONTROL_GAIN": "raw_target = previous_target + effective_grid_deviation × CONTROL_GAIN",
    "SMOOTHING_FACTOR": "smoothed = old × (1 - factor) + target × factor",
    "MAX_POWER_STEP_W": "nominale maximale Zieländerungsrate ≈ MAX_POWER_STEP_W / INTERVAL_SECONDS",
    "MOVING_AVERAGE_SAMPLES": "ungefähres Beobachtungsfenster ≈ MOVING_AVERAGE_SAMPLES × INTERVAL_SECONDS",
    "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W": "normale Ladefreigabe mindestens bei max(DEADBAND_W, MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W)",
    "CROSS_CHARGE_SIGNIFICANT_W": "release_threshold = max(20 W, engage_threshold / 2) bei engage_threshold > 0",
    "COMMAND_EFFECT_TOLERANCE_W": "wirksame Toleranz = max(COMMAND_EFFECT_TOLERANCE_W, |target_w| × COMMAND_EFFECT_TOLERANCE_PERCENT / 100)",
    "COMMAND_EFFECT_TOLERANCE_PERCENT": "wirksame Toleranz = max(COMMAND_EFFECT_TOLERANCE_W, |target_w| × COMMAND_EFFECT_TOLERANCE_PERCENT / 100)",
}
for _key in ("HARVEST_PRIMARY_CHARGE_FLOOR_RATIO", "HARVEST_PRIMARY_CHARGE_FLOOR_W", "HARVEST_PRIMARY_CHARGE_RESTART_RATIO", "HARVEST_PRIMARY_CHARGE_RESTART_W", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W"):
    FORMULAS[_key] = "ohne positiven W-Override: Schwelle = Pmax Primärspeicher × Ratio; geordnet: Floor <= Restart <= Near-Limit <= Pmax"

EXAMPLES = {
    "CONTROL_GAIN": HelpExample("Reglerverstärkung", ("letzte Ladeanforderung = 600 W", "wirksamer Export = 500 W", "CONTROL_GAIN = 0,30"), "600 W + 500 W × 0,30", "rohes Ziel = 750 W", "Beispiel für die Rohkorrektur; danach wirken weitere Limiter. Kein Empfehlungswert."),
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO": HelpExample("Primärspeicher-Schwellen", ("Pmax = 2400 W", "Floor = 30 %", "Restart = 85 %", "Near-Limit = 95 %"), "2400 W × 0,30 / 0,85 / 0,95", "720 W / 2040 W / 2280 W", "Reines Rechenbeispiel. Positive W-Overrides ersetzen jeweils den zugehörigen Ratio-Wert."),
    "CROSS_CHARGE_SIGNIFICANT_W": HelpExample("Cross-Charge-Hysterese", ("Engage = 80 W",), "max(20 W, 80 W / 2)", "Release = 40 W", "Beispiel der internen Release-Hysterese, keine Empfehlung für die Engage-Schwelle."),
    "COMMAND_EFFECT_TOLERANCE_W": HelpExample("Sollwerttracking", ("Sollwert = 2000 W", "absolute Toleranz = 80 W", "relative Toleranz = 10 %"), "max(80 W, 2000 W × 10 %)", "wirksame Toleranz = 200 W", "Die größere Toleranzkomponente bestimmt das Trackingfenster."),
}
for _key in ("HARVEST_PRIMARY_CHARGE_RESTART_RATIO", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO", "HARVEST_PRIMARY_CHARGE_FLOOR_W", "HARVEST_PRIMARY_CHARGE_RESTART_W", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W"):
    EXAMPLES[_key] = EXAMPLES["HARVEST_PRIMARY_CHARGE_FLOOR_RATIO"]
EXAMPLES["COMMAND_EFFECT_TOLERANCE_PERCENT"] = EXAMPLES["COMMAND_EFFECT_TOLERANCE_W"]

OVERRIDE_HELP = {
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO": "Ein positiver HARVEST_PRIMARY_CHARGE_FLOOR_W übersteuert diesen Ratio-Wert.",
    "HARVEST_PRIMARY_CHARGE_RESTART_RATIO": "Ein positiver HARVEST_PRIMARY_CHARGE_RESTART_W übersteuert diesen Ratio-Wert.",
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO": "Ein positiver HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W übersteuert diesen Ratio-Wert.",
    "HARVEST_PRIMARY_CHARGE_FLOOR_W": "Bei positivem Wert ist der zugehörige Floor-Ratio für die effektive Schwelle nicht wirksam.",
    "HARVEST_PRIMARY_CHARGE_RESTART_W": "Bei positivem Wert ist der zugehörige Restart-Ratio für die effektive Schwelle nicht wirksam.",
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W": "Bei positivem Wert ist der zugehörige Near-Limit-Ratio für die effektive Schwelle nicht wirksam.",
}

RELATION_OVERRIDES = {
    "NIGHT_DISCHARGE_POWER_W": (("GATES", "NIGHT_DISCHARGE_ENABLED"), ("LIMITS", "MAX_DISCHARGE_POWER_W")),
    "NIGHT_DISCHARGE_STOP_SOC_PERCENT": (("GATES", "NIGHT_DISCHARGE_ENABLED"), ("LIMITS", "MIN_SOC_PERCENT"), ("LIMITS", "MAX_SOC_PERCENT")),
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO": (("OVERRIDDEN_BY", "HARVEST_PRIMARY_CHARGE_FLOOR_W"), ("SOURCE_FOR", "SECOND_BATTERY_MAX_CHARGE_POWER_W")),
    "HARVEST_PRIMARY_CHARGE_RESTART_RATIO": (("OVERRIDDEN_BY", "HARVEST_PRIMARY_CHARGE_RESTART_W"), ("SOURCE_FOR", "SECOND_BATTERY_MAX_CHARGE_POWER_W")),
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO": (("OVERRIDDEN_BY", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W"), ("SOURCE_FOR", "SECOND_BATTERY_MAX_CHARGE_POWER_W")),
    "HARVEST_PRIMARY_CHARGE_FLOOR_W": (("OVERRIDES", "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO"),),
    "HARVEST_PRIMARY_CHARGE_RESTART_W": (("OVERRIDES", "HARVEST_PRIMARY_CHARGE_RESTART_RATIO"),),
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W": (("OVERRIDES", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO"),),
    "HARVEST_FAST_CAPTURE_MODE": (("GATES", "REST_SURPLUS_HARVEST_ENABLED"), ("GATES", "CROSS_CHARGE_ENABLED"), ("GATES", "SECOND_BATTERY_INTEGRATION_ENABLED"), ("LIMITS", "SECOND_BATTERY_MAX_CHARGE_POWER_W"), ("LIMITS", "MAX_CHARGE_POWER_W")),
    "CROSS_CHARGE_SIGNIFICANT_W": (("GATES", "CROSS_CHARGE_ENABLED"),),
    "COMMAND_EFFECT_TOLERANCE_W": (("PAIRED_WITH", "COMMAND_EFFECT_TOLERANCE_PERCENT"),),
    "COMMAND_EFFECT_TOLERANCE_PERCENT": (("PAIRED_WITH", "COMMAND_EFFECT_TOLERANCE_W"),),
}

GUIDANCE_RULE_IDS = {
    "DEADBAND_W": ("GUIDE-AUTO-AGGRESSIVE", "GUIDE-CMD-DEADBAND"),
    "CONTROL_GAIN": ("GUIDE-AUTO-AGGRESSIVE",),
    "MAX_POWER_STEP_W": ("GUIDE-AUTO-AGGRESSIVE", "GUIDE-HARVEST-STEP"),
    "MOVING_AVERAGE_SAMPLES": ("GUIDE-AUTO-LATENCY", "GUIDE-AUTO-FAST"),
    "SMOOTHING_FACTOR": ("GUIDE-AUTO-FAST", "GUIDE-HARVEST-LATENCY"),
    "INTERVAL_SECONDS": ("GUIDE-AUTO-FAST", "GUIDE-HARVEST-ENTRY", "GUIDE-HARVEST-LATENCY", "GUIDE-LOCAL-API-TIMEOUT"),
    "MIN_COMMAND_CHANGE_W": ("GUIDE-CMD-STEP", "GUIDE-CMD-DEADBAND", "GUIDE-HARVEST-CMD"),
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS": ("GUIDE-HARVEST-ENTRY",),
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": ("GUIDE-HARVEST-ENTRY",),
    "REST_SURPLUS_MIN_EXPORT_W": ("GUIDE-HARVEST-CMD", "GUIDE-HARVEST-DEADBAND", "GUIDE-HARVEST-STEP"),
    "COMMAND_RESYNC_COOLDOWN_SECONDS": ("GUIDE-RESYNC-COOLDOWN",),
    "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": ("GUIDE-LOCAL-API-TIMEOUT",),
    "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": ("GUIDE-LOCAL-API-TIMEOUT",),
}

VERY_HIGH_EXTRA = frozenset({
    "SECOND_BATTERY_DISCHARGE_SIGN", "MQTT_BROKER", "MQTT_PASSWORD", "MQTT_PORT", "MQTT_USER",
    "GRID_POWER_PLAUSIBILITY_MAX_ABS_W", "SMA_ENERGY_METER_SOCKET_MODE", "SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS",
    "SHELLY_STALE_TIMEOUT_SECONDS", "GRID_METER_SOURCE", "WEB_SERVICE_RESTART_ENABLED", "MAX_CONSECUTIVE_ERRORS",
    "MQTT_DISCONNECTED_SAFE_STATE", "SAFE_STATE_ON_SHELLY_ERROR", "SOC_STALE_TIMEOUT_SECONDS", "HEADLESS_MODE", "WEB_HOST",
    "ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS", "ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS",
})

RISK_HELP = {
    "HARVEST_FAST_CAPTURE_MODE": "Aktiv verändert die reale Ladeanforderung schneller als die normale Baseline. Deshalb bleiben A400/R100 fest, Schutz-/Cross-Charge-/Command-Gates übergeordnet und der Rollout erfolgt über Shadow vor Aktiv.",
    "SECOND_BATTERY_DISCHARGE_SIGN": "Falsches Vorzeichen kann Lade- und Entladerichtung der Zweitbatterie falsch interpretieren und damit den Cross-Charge-Schutz entwerten.",
    "GRID_METER_SOURCE": "Eine falsche oder nicht verfügbare Netzleistungsquelle verhindert eine korrekte Regelabweichung und kann Ready/Safety blockieren.",
    "MAX_CONSECUTIVE_ERRORS": "Sehr niedrige Werte können Safe-State früh auslösen; sehr hohe Werte verzögern die Reaktion auf anhaltende Fehler.",
    "MQTT_DISCONNECTED_SAFE_STATE": "Deaktivieren reduziert den konservativen Schutz bei längeren Broker-/MQTT-Problemen.",
    "SAFE_STATE_ON_SHELLY_ERROR": "Deaktivieren reduziert den konservativen Schutz bei anhaltend fehlerhafter Netzleistungsmessung.",
    "SOC_STALE_TIMEOUT_SECONDS": "Zu große Aktualitätsfenster können Entladung mit veraltetem SOC länger zulassen; zu kleine Fenster können bei kurzen Telemetrielücken unnötig blockieren.",
    "WEB_HOST": "Eine breite Bind-Adresse kann das Webinterface in mehr Netzsegmenten erreichbar machen. Zugriffsschutz erfolgt außerhalb dieses Parameters.",
}

OPTION_HELP = {
    "HARVEST_FAST_CAPTURE_MODE": (("off", "„Aus“: keine zusätzliche Ladeanforderung; die normale Automatik bleibt aktiv."), ("shadow", "„Shadow (nur Diagnose)“: zusätzliche Lademöglichkeiten werden berechnet und aufgezeichnet, aber keine Geräteanforderung verändert."), ("active", "„Aktiv“: ZEC darf bei geeignetem echtem Überschuss und frischen Messwerten zusätzliche Ladung anfordern; Geräte- und Schutzgrenzen haben Vorrang.")),
    "MANUAL_MODE": (("AUTO", "„Automatik“: normale Netzleistungsregelung."), ("STOP_HOLD", "„Stop/Hold“: ZEC fordert 0 W an und prüft den Gerätezustand."), ("FIXED_DISCHARGE", "„Feste Entladung“: entlädt innerhalb der Schutzgrenzen bis zum eingestellten Ziel-SOC."), ("FIXED_CHARGE", "„Feste Beladung“: lädt innerhalb der Schutzgrenzen bis zum eingestellten Ziel-SOC.")),
    "MEASUREMENT_LOG_MODE": (("off", "„Aus“: keine neuen Messwertzeilen über diesen Aufzeichnungspfad."), ("standard", "„Standard“: reguläre Mess- und Diagnosedaten mit begrenztem Speicherbedarf."), ("extended", "„Erweitert“: zusätzliche Detailfelder für die Analyse; höherer Speicherbedarf.")),
}


def _handbook_ref(category: str) -> Optional[HandbookRef]:
    item = HANDBOOK_SECTIONS.get(category)
    return HandbookRef(*item) if item else None


def _generic_extended(short: str, row: Mapping[str, Any]) -> str:
    apply_text = str(row.get("apply_text") or "")
    dep = tuple(row.get("dependency_keys") or ())
    suffix = f" Wirksamkeit nach Speichern: {apply_text}." if apply_text else ""
    if dep:
        suffix += " Die Einstellung steht in Beziehung zu: " + ", ".join(dep) + "."
    return (short.rstrip(".") + "." + suffix).strip()


def _dependencies(row: Mapping[str, Any]) -> Tuple[HelpDependency, ...]:
    key = str(row.get("key") or "")
    explicit = RELATION_OVERRIDES.get(key)
    if explicit:
        return tuple(HelpDependency(relation, dep) for relation, dep in explicit)
    return tuple(HelpDependency("PAIRED_WITH", str(dep)) for dep in tuple(row.get("dependency_keys") or ()))


def _search_terms(row: Mapping[str, Any], short: str) -> Tuple[str, ...]:
    key = str(row.get("key") or "")
    label = LABEL_OVERRIDES.get(key, str(row.get("label") or key))
    terms = [label, key, str(row.get("category") or ""), str(row.get("section") or "")]
    terms.extend(SEARCH_SYNONYMS.get(key, ()))
    # A few deterministic key tokens make technical searches useful without
    # exposing any current secret value.
    terms.extend(token for token in key.replace("_", " ").split() if len(token) > 2)
    seen = []
    for term in terms:
        text = str(term).strip()
        if text and text.lower() not in {x.lower() for x in seen}:
            seen.append(text)
    return tuple(seen)



# Source-verified S3 user explanations.  These texts intentionally explain the
# physical *role* of a setting, its relationship to neighboring controls and the
# conditions under which it has no effect.  Internal keys stay in expert metadata.
S3_USER_GUIDANCE: Mapping[str, Mapping[str, str]] = MappingProxyType({
    "HARVEST_SEASON_POLICY_ENABLED": {
        "short": "Erlaubt ZEC, die unten gewählte Saisonstrategie für die zusätzliche Verteilung von PV-Überschuss zwischen Primärspeicher und Zendure zu nutzen. Bei Aus bleibt die bisherige Ladeverteilung erhalten – auch wenn darunter bereits SMA-Priorität ausgewählt ist.",
        "purpose": "Dieser Schalter bestimmt nicht, ob Zendure generell PV-Überschuss laden darf. Er entscheidet nur, ob die neu wählbare Saisonstrategie den strategischen High-SOC-Harvest-Zweig beeinflussen darf. Die normale Restüberschussaufnahme, Fast Capture, MIN-/MAX-SOC und Geräteschutz arbeiten weiterhin nach ihren eigenen Regeln. Die Tagesprofile haben einen separaten Aktivierungsschalter.",
        "when": "Erst nach bestätigter Änderung und nur in einem dafür geeigneten High-SOC-Harvest-Zustand. Bei ausgeschaltetem Schalter verwendet ZEC unverändert die bisherige Strategie, unabhängig von der gespeicherten Saisonwahl.",
        "on": "Aktiviert die gewählte Saisonstrategie für die zusätzliche strategische Ladeverteilung, soweit der High-SOC-Harvest-Zweig tatsächlich anwendbar ist. Dadurch kann sich die Leistungsaufteilung ändern; es wird keine eigene Netzladung gestartet.",
        "off": "Belässt die Ladeverteilung im bisherigen Parallelverfahren. Eine gespeicherte Auswahl wie SMA-Priorität bleibt ohne Saisonwirkung. Restüberschussaufnahme und andere Schutzfunktionen bleiben erhalten.",
    },
    "HARVEST_SEASON_MODE": {
        "short": "Wählt, wie ZEC die zusätzliche strategische Ladeverteilung in geeigneten High-SOC-Situationen behandelt: Parallel, SMA-Priorität oder jahreszeitabhängig. Die Auswahl wirkt nur, wenn „Saisonale Strategie aktivieren“ eingeschaltet ist.",
        "purpose": "Parallel erlaubt im bisherigen High-SOC-Harvest-Zweig eine zusätzliche Aufteilung zugunsten von Zendure. SMA-Priorität unterdrückt nur diese zusätzliche strategische Umlenkung; verbleibender echter PV-Überschuss darf weiterhin in Zendure gespeichert werden. Die Kalenderoption entscheidet nach dem Datum zwischen beiden Verhaltensweisen. Fast Capture und die Sicherheitsschranken sind davon getrennt.",
        "when": "Nur bei aktivierter Saisonstrategie UND einem tatsächlich durchlaufenen strategischen High-SOC-Zweig. Bei normalem HOLD, bei fehlenden Eingangsdaten oder bei vorrangigem Export Capture hat die Auswahl möglicherweise keine zusätzliche Sollwertwirkung.",
        "options": "Parallel: bisherige zusätzliche Verteilung bei High-SOC. SMA-Priorität: keine zusätzliche strategische Umlenkung von Primärspeicher zu Zendure; Aufnahme von Restexport bleibt möglich. Kalender: Parallel während des gewählten Jahreszeitraums, außerhalb SMA-Priorität.",
    },
    "HARVEST_SEASON_PARALLEL_START_MM_DD": {
        "short": "Erster Kalendertag, an dem die Parallelstrategie gelten soll. Gemeinsam mit „Parallel-Harvest-Saison bis“ legt er den jährlich wiederkehrenden Zeitraum fest; außerhalb davon hat SMA-Priorität Vorrang.",
        "purpose": "Dieses Datum ist nur für die Auswahl „Kalender“ relevant, wenn die Saisonstrategie eingeschaltet ist. Es steuert keine Ladeleistung direkt und startet keinen eigenen Ladezyklus. ZEC bewertet es zusammen mit dem Enddatum und den High-SOC-Bedingungen.",
        "when": "Nur wenn Saisonstrategie aktiviert und Modus „Kalender“ ausgewählt ist. Der Starttag zählt mit; ein Zeitraum über den Jahreswechsel ist zulässig. Ohne gültiges Enddatum kann Kalender nicht aktiviert werden.",
    },
    "HARVEST_SEASON_PARALLEL_END_MM_DD": {
        "short": "Letzter Kalendertag, an dem die Parallelstrategie gelten soll. Zusammen mit dem Startdatum begrenzt er das jährliche Parallel-Zeitfenster; danach nutzt ZEC in geeigneten High-SOC-Situationen SMA-Priorität.",
        "purpose": "Das Enddatum ergänzt ausschließlich das Startdatum für die Kalenderentscheidung. Es beeinflusst weder die normale PV-Überschussaufnahme noch SOC-Grenzen oder Gerätebefehle unmittelbar.",
        "when": "Nur bei eingeschalteter Saisonstrategie und Modus „Kalender“. Der Endtag zählt mit; auch Zeiträume über Silvester sind erlaubt. Ungültige oder fehlende Datumsgrenzen werden beim Aktivieren abgewiesen.",
    },
    "HARVEST_HIGH_SMA_SOC_PROFILE_START_TIME": {
        "short": "Ab dieser Uhrzeit beginnt das Morgenprofil der High-SOC-Ladeverteilung. Es verwendet den eingestellten Morgenanteil für den Primärspeicher und die Morgen-Bestätigungszeit – sofern das Tagesprofil aktiv und High-SOC-Harvest anwendbar ist.",
        "purpose": "Zusammen mit den Übergangszeiten für Mittag und Nachmittag und der Endzeit teilt dieser Wert den Tag in Profile. Er gibt keine sofortige Ladeleistung vor. Die saisonale Strategie besitzt einen eigenen Aktivierungsschalter.",
        "when": "Gilt bei aktiviertem High-SOC-Tagesprofil. Das Morgenfenster reicht von dieser Zeit einschließlich bis zum Mittagsbeginn ausschließlich; außerhalb der Profilzeiten gilt das bestehende Standardprofil.",
    },
    "HARVEST_HIGH_SMA_SOC_PROFILE_MIDDAY_START_TIME": {
        "short": "Ab dieser Uhrzeit wechselt das High-SOC-Tagesprofil von Morgen auf Mittag. ZEC nutzt dann den Mittaganteil des Primärspeichers und die Bestätigungszeit für Mittag statt der Morgenwerte.",
        "purpose": "Die Uhrzeit teilt nur die strategischen Tagesprofile auf und ist kein Startkommando für eine Batterie. Das High-SOC-Tagesprofil muss separat aktiviert sein; Schutzgrenzen gelten unverändert.",
        "when": "Nur bei aktiviertem Tagesprofil und geeigneter High-SOC-Regelsituation; die Zeitpunkte müssen streng aufeinanderfolgen.",
    },
    "HARVEST_HIGH_SMA_SOC_PROFILE_AFTERNOON_START_TIME": {
        "short": "Ab dieser Uhrzeit verwendet ZEC das Nachmittagsprofil mit dessen Primärspeicheranteil und Bestätigungszeit, statt weiterhin die Mittagwerte zu nutzen.",
        "purpose": "Der Umschaltpunkt verändert die strategische Aufteilung nur, wenn das Tagesprofil und der High-SOC-Regelzweig aktiv sind. Er schaltet weder einen Speicher ein noch verändert er die Schutzlimits.",
        "when": "Nur im aktivierten High-SOC-Tagesprofil zwischen Mittagsbeginn und Ende des Zeitfensters.",
    },
    "HARVEST_HIGH_SMA_SOC_PROFILE_END_TIME": {
        "short": "Beendet das zeitabhängige Nachmittagsprofil. Danach verwendet ZEC wieder die bestehenden allgemeinen High-SOC-Standardwerte statt der Morgen-, Mittag- oder Nachmittagswerte.",
        "purpose": "Das ist kein Ausschalter für den gesamten Harvest-Betrieb: Nur die zeitliche Profilzuordnung endet. Export Capture, die allgemeine Ladeverteilung und sämtliche Batteriegrenzen bleiben bestehen.",
        "when": "Nur relevant, wenn das High-SOC-Tagesprofil aktiviert ist; Endzeit liegt nach den anderen drei Zeitgrenzen.",
    },
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_MORNING_SECONDS": {
        "short": "So lange müssen die High-SOC-Eintrittsbedingungen morgens ununterbrochen bestätigt sein, bevor ZEC die zusätzliche strategische Ladeverteilung freigibt. Kurze Ausschläge werden dadurch gefiltert.",
        "purpose": "Dieser Wert ersetzt im Morgenfenster die allgemeine High-SOC-Bestätigungszeit, wenn das Tagesprofil eingeschaltet ist. Er verändert weder die Höhe der Ladeleistung noch eine harte SOC-Grenze; dafür sind andere Einstellungen verantwortlich.",
        "when": "Nur bei aktivem Tagesprofil im Morgenfenster und bei grundsätzlich zulässigem High-SOC-Eintritt.",
    },
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_MIDDAY_SECONDS": {
        "short": "Mindestdauer für die Bestätigung eines High-SOC-Eintritts während des Mittagsprofils. Längere Werte vermeiden häufige Freigaben bei kurzzeitigem Überschuss.",
        "purpose": "Dieser Wert tritt mittags an die Stelle der allgemeinen High-SOC-Eintrittsbestätigung, falls das Tagesprofil aktiviert ist. Die spätere Leistungsaufteilung bestimmt der Mittagsanteil, nicht diese Zeitangabe.",
        "when": "Nur bei aktivem Tagesprofil im Mittagsfenster und erfüllten High-SOC-Schwellen.",
    },
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_AFTERNOON_SECONDS": {
        "short": "Mindestdauer für die Bestätigung eines High-SOC-Eintritts am Nachmittag. Erst nach dieser Zeit darf der entsprechende strategische Harvest-Zweig beginnen.",
        "purpose": "Dieser Wert ersetzt im Nachmittagsfenster die allgemeine Eintrittsbestätigung, wenn das Tagesprofil aktiv ist. Er steuert die zeitliche Freigabe, nicht die Ladeleistung selbst; dabei bleibt die normale PV-Überschussaufnahme unabhängig.",
        "when": "Nur bei aktivem Tagesprofil im Nachmittagsfenster und zulässigen High-SOC-Bedingungen.",
    },
})

S3_SETTING_EFFECTS: Mapping[str, Mapping[str, str]] = MappingProxyType({
    "HARVEST_SEASON_POLICY_ENABLED": {"on": S3_USER_GUIDANCE["HARVEST_SEASON_POLICY_ENABLED"]["on"], "off": S3_USER_GUIDANCE["HARVEST_SEASON_POLICY_ENABLED"]["off"]},
})

S3_OPTION_HELP = (
    ("parallel", "Bei geeigneter High-SOC-Situation darf ZEC die bislang vorgesehene strategische Ladeaufteilung zwischen Primärspeicher und Zendure zusätzlich anwenden. Export Capture hat Vorrang."),
    ("sma_priority", "Keine zusätzliche strategische Umlenkung aus dem High-SOC-Share-Zweig zu Zendure. Echter verbleibender PV-Überschuss kann weiterhin zum Laden genutzt werden."),
    ("calendar", "Während des konfigurierten jährlichen Datumsfensters gilt Parallel, außerhalb SMA-Priorität. Beide MM-DD-Grenzen müssen gültig sein."),
)


# Previously cryptic one-line UI descriptions: explain observable purpose,
# relationship to the controlling mode and absence of any implicit commands.
GENERAL_SHORT_HELP_VNEXT = MappingProxyType({
    "DEVICE_ID": "Kennung der Zendure-Headunit, für die ZEC MQTT-Telemetrie empfängt und Leistungsbefehle erstellt. Sie muss zu den Topics des tatsächlich gesteuerten Geräts passen und schaltet keine zusätzliche Headunit frei.",
    "MAX_CHARGE_POWER_W": "Globale Obergrenze für Zendure-Ladung aus allen zulässigen Regelpfaden. AUTO, Harvest und feste Ladeanforderungen dürfen sie nicht überschreiten; sie erzwingt keine Ladung und ersetzt keine Gerätelimits.",
    "MAX_DISCHARGE_POWER_W": "Globale Obergrenze für die Entladeleistung von Zendure. Sie begrenzt AUTO, Nacht- und manuelle Entladung, unabhängig von der gewünschten Netzleistung; der tatsächliche Akku- und SOC-Schutz hat weiterhin Vorrang.",
    "MAX_SOC_PERCENT": "Ab diesem oberen Zendure-Ladezustand wird weitere Ladung begrenzt. Das gilt auch bei PV-Überschuss und manuell gewünschter Ladung; die Einstellung ändert nicht den Ladezustand des Primärspeichers.",
    "MIN_SOC_PERCENT": "Unterhalb der globalen Zendure-Reserve darf ZEC keine weitere Entladung anfordern, unabhängig von AUTO-, Nacht- oder manuellem Modus. Zulässiges Laden aus tatsächlichem PV-Export bleibt möglich, sofern alle anderen Schutzgrenzen erfüllt sind.",
    "MOVING_AVERAGE_SAMPLES": "Bestimmt, wie viele aktuelle Netzleistungsmessungen in den Mittelwert für AUTO eingehen. Mehr Werte glätten Lastspitzen, verzögern aber die Reaktion; die separate Reglerverstärkung und Schrittbegrenzung wirken danach.",
    "MAX_POWER_STEP_W": "Begrenzt, wie stark ZEC das Leistungsziel in einem normalen Regelzyklus ändern darf. Kleine Schritte beruhigen die Geräteansteuerung, verzögern aber Lastsprünge; übergeordnete Schutz- und Neutralisierungspfade bleiben wirksam.",
    "NIGHT_DISCHARGE_ENABLED": "Erlaubt eine feste Zendure-Entladung im gewählten Nacht-Zeitfenster statt normaler AUTO-Nachführung, sofern kein vorrangiger manueller Modus aktiv ist. Das Reserve-SOC und alle globalen Schutzlimits bleiben verbindlich.",
    "NIGHT_DISCHARGE_POWER_W": "Legt die gewünschte feste Zendure-Entladeleistung während des aktivierten Nachtfensters fest. Anders als AUTO wird sie nicht automatisch an die momentane Hauslast angepasst; der Wert muss unter der globalen Entladegrenze bleiben.",
    "NIGHT_END_HOUR": "Stunde, zu der das aktivierte Nachtfenster endet. Zusammen mit der Endminute und der Startzeit begrenzt sie die feste Nachtentladung; nach dem Ende gelten wieder die regulären Betriebs- und Sicherheitsentscheidungen.",
    "NIGHT_START_HOUR": "Stunde, zu der die feste Nachtentladung grundsätzlich erlaubt wird. Sie wirkt nur zusammen mit Startminute, Ende und aktiviertem Nachtmodus; manuelle Modi sowie SOC-Schutz können die Entladung verhindern.",
    "NIGHT_START_MINUTE": "Minutenanteil des Beginns der aktivierten Nachtentladung. Zusammen mit der Startstunde legt er das Zeitfenster fest, löst allein jedoch keinen Lade-/Entladebefehl aus.",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON": "Anteil der im High-SOC-Nachmittagsprofil strategisch dem Primärspeicher zugeordneten Ladeleistung. Ein höherer Wert bevorzugt den Primärspeicher; der reale Restexport und übergeordnete Schutzregeln können dennoch Zendure-Ladung erlauben.",
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY": "Anteil der im High-SOC-Mittagsprofil strategisch für den Primärspeicher vorgesehenen Leistung. Dieser Wert ist nur im passenden aktiven Profil anwendbar, kein fester Gerätebefehl und keine eigene Ladefreigabe.",
    "MQTT_BROKER": "Netzwerkadresse des MQTT-Brokers, über den ZEC Zendure-Gerätedaten und Befehle austauscht. Der Broker muss erreichbar sein; ein falscher Wert kann Telemetrie und sichere Gerätesteuerung unterbrechen.",
    "MQTT_PASSWORD": "Kennwort für die Anmeldung am konfigurierten MQTT-Broker. Es ist nur erforderlich, wenn der Broker Authentifizierung verlangt; fehlende Anmeldung verhindert aktuelle Gerätedaten und Befehlsübertragung.",
    "MQTT_PORT": "Netzwerkport des eingestellten MQTT-Brokers (häufig 1883). Er gehört zur Brokeradresse und zur optionalen Anmeldung; bei falschem Port kann ZEC keine verlässlichen Zendure-MQTT-Daten oder Kommandos übertragen.",
    "SHELLY_STALE_TIMEOUT_SECONDS": "Maximales Alter einer gültigen Netzleistungsmessung aus der Shelly-kompatiblen Quelle. Wird der Wert zu alt, darf ZEC ihn nicht als frische Grundlage für AUTO interpretieren; die direkte SMA-Quelle hat eigene Frischegrenzen.",
    "ANALYSIS_EXTENDED_WORKER_MEMORY_LIMIT_MB": "Begrenzt den Arbeitsspeicher bewusst freigegebener größerer Analysejobs. Ein höherer Wert kann komplexere Auswertungen erlauben, erhöht aber das Risiko, den Raspberry Pi zu überlasten; die Reglerfunktion selbst wird nicht umgestellt.",
    "ANALYSIS_EXTENDED_WORKER_TIMEOUT_SECONDS": "Legt die maximale Laufzeit eines bewusst erweiterten Analysejobs fest. Ein langer Timeout gestattet umfangreichere Auswertungen, kann Ressourcen länger binden; er beschleunigt oder verändert keine Reglerentscheidung.",
    "FILE_LOG_BACKUP_COUNT": "Anzahl älterer Laufzeit-Logdateien, die ZEC nach einer Rotation aufbewahrt. Mehr Backups erleichtern die rückblickende Fehlersuche, brauchen aber mehr Speicherplatz; das verändert keine Batteriekommandos.",
    "FILE_LOG_DIR": "Speicherverzeichnis für die normalen Controller-Textprotokolle. Es wirkt zusammen mit aktiviertem Datei-Logging und der Rotationsgrenze; ein falscher Pfad beeinträchtigt die Diagnoseaufzeichnung, nicht die Sollwertformel.",
    "DEBUG": "Schaltet zusätzliche technische Konsolenmeldungen für die Fehlersuche ein. Die Meldungen können unübersichtlich werden und Ressourcen beanspruchen; sie verändern nicht die gewählte AUTO-/Nacht-/Harvest-Strategie.",
    "LOG_MQTT": "Protokolliert MQTT-Kommandos an die Zendure-Headunit zur Diagnose des Befehlsablaufs. Mehr Logeinträge sind kein Beweis für eine physische Gerätewirkung und aktivieren keine zusätzlichen Kommandos.",
    "LOG_RAW_RESPONSE": "Schreibt bei aktivem Diagnoselogging vollständige Antworten der Shelly-kompatiblen Netzleistungsquelle. Nur zur Fehlersuche einschalten: die Texte können groß sein; der Regler verwendet weiterhin dieselben validierten Messwerte.",
    "LOG_SOC": "Protokolliert empfangene Zendure-Ladezustände, um Datenlücken und Reserveentscheidungen nachzuvollziehen. Das Logging verändert weder den tatsächlich gemeldeten SOC noch die Schutzgrenzen.",
    "LOG_VALUES": "Protokolliert Netzleistungs-Rohwerte und die von ZEC verwendete Glättung zur Fehleranalyse. Die zusätzlichen Ausgaben beeinflussen nicht die Auswahl der Netzleistungsquelle oder die Reglerformel.",
    "SAFE_STATE_ON_SHELLY_ERROR": "Bei anhaltendem Fehler der Shelly-kompatiblen Netzmessung darf ZEC sicherheitshalber 0 W anfordern statt mit veralteten Leistungswerten weiterzuregeln. Das betrifft nicht automatisch die unabhängig konfigurierte SMA-Direktquelle.",
    "SOC_STALE_TIMEOUT_SECONDS": "Legt fest, wie alt ein Zendure-Ladezustand höchstens sein darf, bevor er für eine sichere Entladefreigabe nicht mehr genügt. Die Grenze schützt insbesondere Nacht-/AUTO-/manuelle Entladung vor Entscheidungen auf alten Akkudaten.",
    "ZENDURE_POWER_STALE_TIMEOUT_SECONDS": "Nach diesem Datenalter markiert ZEC die Zendure-Istleistungsmessung als veraltet. Das ist eine Aktualitäts- und Diagnosegrenze, keine neue Sollleistung und kein Beweis, dass ein zuvor gesendeter Befehl ausgeführt wurde.",
    "WEB_PORT": "Port, über den du die ZEC-Weboberfläche im Netzwerk erreichst. Eine Änderung betrifft den HTTP-Zugang und erfordert einen geeigneten Dienstneustart; sie verändert nicht die Lade-/Entladestrategie.",
})


# Editorially reviewed purpose text for interfaces, storage and diagnostics.
# Per-key descriptions are not generated from their labels. Use plain language
# to explain actual consumers and relationships to other user controls.
EXPLICIT_PURPOSE_VNEXT: Mapping[str, str] = MappingProxyType({
    "ZENDURE_BATTERY_CAPACITY_WH": "Die Kapazitätsangabe hilft ZEC, aus einem bekannten Ladezustand eine verbleibende Energiemenge und Nachtprognose darzustellen. Sie ist kein Befehl und setzt weder die maximale Ladeleistung noch die SOC-Grenzen herauf. Nur den tatsächlichen Gesamtwert der installierten Akkus eintragen; bei unbekanntem Wert bleibt die Energieberechnung ohne erfundene Ersatzkapazität.",
    "DEVICE_ID": "ZEC kann nur dann zuverlässig die richtige Zendure-Headunit erreichen, wenn diese Kennung mit den MQTT-Topics des Geräts übereinstimmt. Sie verbindet eingehende Telemetrie und ausgehende Leistungsanforderungen mit demselben Gerät. Hiermit wird kein zweiter eigenständiger Zendure-Regler aktiviert; nach einem Gerätewechsel sind Verbindung, Anzeige und Sicherheitszustand zu prüfen.",
    "SECOND_BATTERY_STALE_TIMEOUT_SECONDS": "Diese Zeitgrenze legt fest, ab wann der letzte vollständige Primärspeicherwert für eine sichere Allokations-/Cross-Charge-Entscheidung zu alt ist. Sie gilt unabhängig davon, ob du EVCC, eigenes MQTT oder Modbus nutzt. Ein veralteter Wert darf nicht so aussehen, als hätte der Primärspeicher gerade Leistung verfügbar; zu knappe Grenzen können bei normaler Kommunikationsverzögerung häufiger sperren.",
    "SECOND_BATTERY_DISPLAY_NAME": "Mit diesem Namen kannst du den Primärspeicher in Status, Graphen und Fehlerdiagnosen eindeutig erkennen. Der Name ist ausschließlich eine Anzeigehilfe und verändert weder die gewählte EVCC-/MQTT-/Modbus-Datenquelle noch die Batterieleistung oder den SOC. Gerätekennungen, historische Messwerte und Schutzentscheidungen bleiben getrennt.",
    "SECOND_BATTERY_SOURCE_PROFILE": "Die Auswahl bestimmt, woher ZEC den tatsächlichen SOC, die aktuelle Lade-/Entladeleistung und gegebenenfalls die Kapazität des Primärspeichers bekommt. EVCC und benutzerdefiniertes MQTT benötigen passende Topics; Modbus liest ein geprüftes Gerätetemplate direkt, ohne Schreibzugriff. Diese Wege sind Alternativen. Erst frische, korrekt normalisierte Werte dürfen die dazugehörigen Harvest-/Cross-Charge-Entscheidungen unterstützen.",
    "SECOND_BATTERY_MODBUS_TEMPLATE": "Das Geräteprofil legt unveränderlich fest, welche Modbus-Register für Leistung, SOC und weitere unterstützte Merkmale gelesen werden. ZEC verwendet das Template nur, wenn die Modbus-Anbindung gewählt und der Primärspeicher aktiviert ist; Host, Port und Unit-ID stellen separat die konkrete Verbindung her. Das Template darf weder neue Schreibzugriffe noch erfundene Gerätefunktionen freigeben.",
    "SECOND_BATTERY_MODBUS_HOST": "Hier gibst du an, unter welcher Adresse der echte Primärspeicher im lokalen Netz erreichbar ist. Dieser Wert wirkt nur mit der Datenquelle „Modbus“ zusammen mit Port, Unit-ID und Geräteprofil. Bei einer falschen Adresse erhält ZEC keine belastbaren Speicherwerte; die Reglersicherheit darf dann nicht auf alten Daten beruhen.",
    "SECOND_BATTERY_MODBUS_PORT": "Der TCP-Port ergänzt die Adresse des Primärspeichers für den lesenden Modbus-Zugriff. Für das geprüfte Sunny-Island-Profil ist 502 ein typischer Standard, kann aber installationsabhängig abweichen. Ohne passende Hostadresse, Unit-ID und Template gibt es keine gültige Datenquelle; der Port schaltet keine Gerätesteuerung ein.",
    "SECOND_BATTERY_MODBUS_UNIT_ID": "Die Unit-ID benennt das logische Modbus-Gerät auf der Verbindung; bei Sunny Island wird üblicherweise 3 verwendet. Sie ist nur bei gewähltem Modbus-Template relevant und muss zusammen mit IP, Port und Template korrekt sein. Falsche Werte führen zu ungültigen oder fehlenden Lesedaten, nicht zu einer zulässigen Primärspeicher-Ansteuerung.",
    "SECOND_BATTERY_CAPACITY_TOPIC": "Wenn du den Primärspeicher per eigenem MQTT einbindest, kann dieses zusätzliche Topic eine Gerätekapazität liefern. Sie ergänzt die Leistungs- und SOC-Topics für Status und Diagnose; sie ist keine Ladefreigabe und ersetzt nicht die Einstellung für maximale Ladeleistung. Das Feld wird nicht für EVCC-Standard oder Modbus gebraucht.",
    "SECOND_BATTERY_POWER_TOPIC": "Über dieses Topic erhält ZEC beim benutzerdefinierten MQTT-Profil den tatsächlichen Lade- oder Entladefluss des Primärspeichers. Erst zusammen mit Payloadformat, Leistungseinheit, Vorzeichenregel und Freshness entsteht ein sicher interpretierbarer Wert. Der gemeldete Istwert ist kein Befehl an das Gerät und muss sich auf den richtigen Speicher beziehen.",
    "SECOND_BATTERY_SOC_TOPIC": "Dieses optionale Topic liefert beim eigenen MQTT-Profil den Ladezustand des Primärspeichers. Es ergänzt das Leistungsthema, ist jedoch nicht mit der Zendure-SOC-Grenze gleichzusetzen. Beim Sunny-Island-Modbusprofil stammt SOC stattdessen aus geprüften Registern; alte SOC-Nachrichten müssen als veraltet gelten.",
    "SECOND_BATTERY_EVCC_BASE_TOPIC": "Bei einer EVCC-Standardanbindung entsteht aus diesem Stamm automatisch die Adresse für Leistung, SOC und Kapazität. Du brauchst daher nicht die benutzerdefinierten Einzel-Topics auszufüllen. Die gewählte EVCC-Quelle und ihre Nachrichtengültigkeit entscheiden, ob ZEC den Speicher in Schutz- und Allokationspfaden berücksichtigen darf.",
    "SECOND_BATTERY_CAPACITY_JSON_PATH": "Wenn die Kapazität im eigenen MQTT-Profil als JSON veröffentlicht wird, zeigt dieser Pfad ZEC das tatsächliche Zahlenfeld. Du benötigst ihn nur zusammen mit einem konfigurierten Kapazitäts-Topic und Payloadformat JSON. Ein falscher Pfad macht die Kapazitätsanzeige unbekannt, ändert aber keine Hardwarekapazität oder Ladegrenze.",
    "SECOND_BATTERY_CAPACITY_PAYLOAD_TYPE": "Hier sagst du ZEC, ob das Kapazitäts-Topic eine einzelne Zahl oder ein JSON-Dokument liefert. Bei JSON muss zusätzlich das Feld mit dem eigentlichen Wert angegeben werden. Die Angabe dient der korrekten Auswertung und Energieanzeige, nicht der Steuerung einer Ladeanforderung.",
    "SECOND_BATTERY_POWER_JSON_PATH": "Nur beim eigenen MQTT-Profil mit Leistungs-Payload als JSON wird hier das Feld gewählt, aus dem ZEC die aktuelle Primärspeicherleistung liest. Das Vorzeichen und die Einheit werden separat festgelegt. Ein falscher Pfad darf nicht durch einen angenommenen Nullwert als echter Lade-/Entladestillstand erscheinen.",
    "SECOND_BATTERY_POWER_PAYLOAD_TYPE": "Die Quelle kann Primärspeicherleistung als schlichte Zahl oder innerhalb eines JSON-Dokuments veröffentlichen. Mit dieser Auswahl entscheidet ZEC, wie es die MQTT-Nachricht ausliest. Die Einheiten- und Vorzeicheneinstellungen bestimmen erst anschließend ihre fachliche Bedeutung und Sicherheit.",
    "SECOND_BATTERY_SOC_JSON_PATH": "Wenn dein eigener Primärspeicher-SOC-Topic JSON sendet, wählt dieser Feldpfad den darin enthaltenen Prozentwert. Er wirkt nicht bei direkter numerischer Payload oder EVCC-/Modbus-Anbindung. Ein nicht lesbarer Wert bleibt unbekannt statt als aktuelle Batterie-Reserve behauptet zu werden.",
    "SECOND_BATTERY_SOC_PAYLOAD_TYPE": "Legt fest, ob der SOC des Primärspeichers aus einer einfachen MQTT-Zahl oder aus einem JSON-Feld gelesen wird. Bei JSON muss der dazugehörige Feldpfad stimmen. Dieser SOC dient der fachlichen Einordnung des Primärspeichers und ersetzt niemals den aktuellen Zendure-SOC für dessen harte Schutzgrenzen.",
    "SECOND_BATTERY_CAPACITY_UNIT": "Die Datenquelle kann die Primärspeicherkapazität in unterschiedlichen Energieeinheiten melden. ZEC muss die gewählte Einheit kennen, um den tatsächlichen Wert korrekt in kWh darzustellen. Diese Auswahl verändert keine Kapazität im Gerät und ist von der Leistungs-Einheit Watt/kW ausdrücklich zu unterscheiden.",
    "SECOND_BATTERY_DISCHARGE_SIGN": "Je nach MQTT-Quelle bedeutet eine positive Leistung Laden oder Entladen. Hier ordnest du diese Richtung eindeutig zu, damit ZEC den Primärspeicherfluss richtig für Anzeige, Harvest und Cross-Charge-Schutz interpretiert. Eine verkehrte Zuordnung kann Schutzentscheidungen verfälschen; die wirkliche physische Leistung wird dadurch nicht geändert.",
    "SECOND_BATTERY_POWER_UNIT": "Die Quelle kann Primärspeicherleistung in Watt oder Kilowatt melden. Diese Auswahl übersetzt den eingehenden Istwert in die von ZEC verwendeten Watt; das Vorzeichen wird separat eingestellt. Eine falsche Einheit würde Ladegrenzen und Gegenflussdetektion um Größenordnungen verfälschen, ohne das reale Gerät zu beeinflussen.",
    "SECOND_BATTERY_MAX_CHARGE_POWER_W": "Dieser Wert beschreibt die belastbare maximale Aufnahmeleistung des echten Primärspeichers. Er hilft, Lade-Headroom und Harvest-Schwellen sachgerecht einzuordnen; sofern das Profil verlässlich direkt gelesene technische Daten bereitstellt, haben diese Vorrang. Hiermit erteilt ZEC keine Schreibanweisung an den Primärspeicher und es entsteht keine automatisierte Netzladung.",
    "MEASUREMENT_LOG_MAX_BYTES": "Damit eine einzelne Measurement-V4-CSV nicht unbegrenzt wächst, wird sie beim Erreichen dieses Limits gewechselt. Zusammen mit Speicherziel, Rotation und Mindestfreiplatz entscheidet das über Datenträgerverbrauch und verfügbare Historie. Kleinere Dateien erzeugen mehr Rotation, beeinflussen aber keine Steuerentscheidung.",
    "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": "Wenn das bevorzugte externe Messlaufwerk nicht erreichbar ist, kann ZEC eine begrenzte Aufzeichnung auf der internen SD fortsetzen. Dafür gelten eigenes Fallback-Verzeichnis, engere Dateigrenzen und Freiplatzschutz. Dies bewahrt einige Diagnosedaten, nicht die zuvor fehlenden Messpunkte; die eigentliche Regelung läuft unabhängig vom Logging.",
    "MEASUREMENT_LOG_FALLBACK_DIR": "Dieses Verzeichnis nimmt Messdaten ausschließlich dann auf, wenn ein freigegebener SD-Fallback nach Ausfall des externen Speicherziels aktiv ist. Es wirkt mit dem Fallback-Schalter und dessen strengem Rotationslimit zusammen. Ein nicht beschreibbarer Pfad soll einen transparenten Logausfall zeigen und nicht den Controller blockieren.",
    "MEASUREMENT_LOG_FALLBACK_MAX_BYTES": "Die kleinere Größenbegrenzung im SD-Fallback verhindert, dass ein zeitweiser USB-Ausfall sehr große zusätzliche Dateien auf der Systemkarte erzeugt. Sie wirkt nur, wenn der Fallback tatsächlich aktiviert wurde; reguläre CSV-Rotation und Freiplatzgrenzen sind davon getrennte Schutzmaßnahmen.",
    "MEASUREMENT_LOG_FILE": "Dieser Name bestimmt die aktuelle Measurement-V4-Datei, in der ZEC Reglerzustände und Messwerte für spätere Untersuchung aufzeichnet. Speicherziel, Logmodus, Rotation und Flush kontrollieren gemeinsam die tatsächliche Ablage. Eine Namensänderung verändert weder das Measurement-Schema noch die aktuelle Regelung.",
    "MEASUREMENT_LOG_MODE": "Hier bestimmst du, ob ZEC überhaupt neue zyklische Measurement-V4-Daten schreibt und wie viele Detailfelder später für Analysen verfügbar sind. Aus spart Speicher, liefert aber keine neue Messhistorie; Standard genügt für viele Diagnosefälle; Erweitert bietet mehr Details mit entsprechendem I/O-Aufwand. Die unabhängig vorhandene Reglerfunktion und der Graphstore müssen davon unterschieden werden.",
    "MEASUREMENT_DB_ENABLED": "Der SQLite-Graphstore hält aufbereitete Messwerte für schnellere Status- und Graphabfragen bereit, unabhängig vom CSV-Logmodus. Wird er deaktiviert, fehlen künftige DB-Punkte; er setzt keine Batterieleistung und erlaubt keine bislang gesperrte Ladefunktion. Speicherziel, Datenbankpfad und Fallback haben jeweils eigene Verträge.",
    "MEASUREMENT_DB_PATH": "Mit diesem Pfad wählst du die SQLite-Datei des Graphstores, falls die automatische Platzierung neben dem aktiven Messdatenziel nicht passt. Schreibbarkeit und Datenbestand müssen beim Wechsel geprüft werden. Die Einstellung ist ein Speicherverwaltungsvertrag, keine Anweisung zum Löschen alter Messwerte und keine Änderung der Regelstrategie.",
    "MEASUREMENT_LOG_FLUSH_EVERY_ROWS": "Um die SD-Karte zu schonen, hält ZEC einige Measurement-V4-Zeilen im Schreibpuffer. Dieser Wert legt fest, nach wie vielen Zeilen der Puffer normal geleert werden soll. Höhere Werte vermindern häufige Schreibzugriffe, können aber im Störfall mehr noch nicht persistierte Daten kosten; die Sekunden-Grenze wirkt zusätzlich.",
    "MEASUREMENT_LOG_FLUSH_EVERY_SECONDS": "Zusätzlich zur Zeilenzahl gibt dieser Wert an, wie lange Messdaten spätestens im Puffer verbleiben sollen, bevor sie geschrieben werden. Eine kleine Zeit bedeutet häufigere Datenträgerarbeit, eine größere Zeit mehr potenziell verlorene letzte Zeilen bei Stromausfall. Die Regelung darf nicht auf das Schreiben warten.",
    "MEASUREMENT_LOG_MIN_FREE_DISK_MB": "Diese Freiplatzschwelle schützt sowohl den normalerweise gewählten Datenträger als auch einen aktiven SD-Fallback vor volllaufenden Logs. Unterschreitet der verfügbare Platz die Grenze, muss ZEC die Messaufzeichnung bremsen oder unterlassen und dies diagnostizieren, nicht weiterhin unbegrenzt schreiben oder die Batterie-Regelung blockieren.",
    "MEASUREMENT_LOG_DIR": "Das Datenverzeichnis legt fest, wo die aktuellen CSV-Messdateien innerhalb des gewählten Speicherziels liegen. Bei externem Mount ist es ein Unterordner, bei internem/custom Ziel der eigentliche Pfad. Der Freiplatzschutz und die Rotationsregeln bleiben davon unabhängig und keine bereits fehlenden Messwerte werden nachträglich erzeugt.",
    "MEASUREMENT_LOG_MOUNTPOINT": "Wenn ein bestimmtes USB-Laufwerk für Messdaten genutzt werden soll, benennt dieser Pfad den Mountpoint. Bei automatischer Erkennung kann er leer bleiben. ZEC muss das Laufwerk tatsächlich als eingebunden und schreibbar erkennen; sonst gelten die vereinbarten Fallback- und Freiplatzregeln, nicht ein stillschweigender SD-Schreibzwang.",
    "MEASUREMENT_LOG_STORAGE_TARGET": "Damit entscheidest du, ob Messdaten auf der SD-Karte, einem externen Datenträger oder einem eigenen Pfad gespeichert werden sollen. Zusammen mit Mountpoint, Unterordner und Fallback bestimmt dies die Zuverlässigkeit und Schreibbelastung der Archivierung. Der Speicherort ändert keine Ladeentscheidung und ist nicht mit der Auswahl einer Netzleistungsquelle zu verwechseln.",
    "GRAPH_HISTORY_LIMIT": "Diese Zahl begrenzt die im Arbeitsspeicher gehaltenen Status-Graphpunkte. Sie beeinflusst, wie weit eine RAM-basierte kleine Verlaufsgrafik zurückblicken kann, nicht wie oft der echte Netzsensor misst. Langfristige, zeitgetreue Graphdaten stammen aus der getrennten Persistenz; mehr RAM-Punkte sind kein Ersatz für längere Historienabfragen.",
    "SOC_DAY_GRAPH_BOOTSTRAP_CACHE_SECONDS": "Beim Aufruf des heutigen SOC-Tagesgraphen kann ZEC Daten aus bestehenden Messdateien ergänzen und das Ergebnis kurz zwischenspeichern. Diese Zeit begrenzt, wie lange ein solcher aufbereiteter Tagesstand wiederverwendet wird. Sie ist kein Samplingintervall des Akkus und darf alte Punkte nicht als aktuelle Sensormessungen ausgeben.",
    "SOC_DAY_GRAPH_BOOTSTRAP_FROM_MEASUREMENTS": "Der SOC-Tagesgraph kann frühere heutige Messpunkte aus vorhandenen Measurement-V4-Dateien lesen, statt nur die seit dem aktuellen Start gesammelten Punkte zu zeigen. Fehlen Dateien oder ist das Lesen nicht möglich, beginnt die Kurve aus den aktuell verfügbaren Werten. Dies verändert weder die SOC-Grenzen noch die Regelung und muss ressourcenschonend erfolgen.",
    "SOC_DAY_GRAPH_ENABLED": "Dieser Schalter zeigt die Zendure-SOC-Entwicklung des aktuellen lokalen Tages an. Das Diagramm verwendet sein eigenes Sampling und gegebenenfalls einen begrenzten Bootstrap aus alten V4-Dateien. Ausschalten spart Darstellungskosten, ändert aber nicht den physischen Ladezustand oder die Schutzentscheidungen.",
    "SOC_DAY_GRAPH_SAMPLE_SECONDS": "Mit diesem Zeitabstand speichert ZEC neue Punkte für die tägliche SOC-Kurve. Größere Abstände ergeben weniger Details und geringere RAM-Last, kleinere mehr Zeitauflösung; das ist unabhängig vom sekündlichen Browser-Status und der physischen SOC-Melderate der Zendure-Hardware.",
    "MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_ROWS": "Das Measurement-V4-Manifest beschreibt, welche Messdateien zu welcher Aufzeichnung gehören. Dieser Zeilenwert erlaubt es, Metadaten gebündelt statt nach jedem Messpunkt zu schreiben. Ein größeres Intervall schont den Datenträger, kann aber bis zum nächsten Flush vorübergehend einen älteren Manifeststand anzeigen; die Messdaten selbst müssen separat konsistent bleiben.",
    "MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_SECONDS": "Mit dieser Zeitgrenze hält ZEC selbst bei langsamer Messdatenerzeugung die Manifest-Metadaten regelmäßig nach. Zusammen mit der Zeilen-Grenze bestimmt das die Aktualität des Verzeichnisses. Sie beeinflusst nicht die Frequenz der eigentlichen Sensorsamples oder der Batteriekommandos; beim Dateischluss wird das Manifest finalisiert.",
})


INTERFACE_PURPOSE_VNEXT: Mapping[str, str] = MappingProxyType({
    "MQTT_TOPIC_DIAGNOSTIC_ENABLED": "Diese Option schaltet einen zusätzlichen Diagnosemitschnitt von MQTT-Nachrichten ein. Das ist nur bei gezielter Fehlersuche nötig und darf nicht mit dem normalen MQTT-Kommando-/Telemetriepfad verwechselt werden. Welche Nachrichten sichtbar werden und wie lange sie erhalten bleiben, regeln Filter, Ansichtsmodus und RAM-Historie getrennt.",
    "MQTT_TOPIC_DIAGNOSTIC_FILTER": "Mit diesem Topic-Muster begrenzt du, welche Nachrichten im Diagnosemitschnitt betrachtet werden. Es wirkt zusammen mit dem Diagnose-Einschalter und dem Ansichtsmodus „gefiltert“; der Modus „alle“ kann zusätzlich andere empfangene Topics zeigen. Der Filter ist case-sensitiv und ändert nicht, an welches Zendure-Gerät ZEC Kommandos sendet.",
    "MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT": "Diese Zahl bestimmt nur, wie viele der zuletzt für die Diagnose erfassten MQTT-Nachrichten im Arbeitsspeicher sichtbar bleiben. Höhere Werte helfen bei längerer Fehlersuche, benötigen aber mehr RAM. Es handelt sich nicht um die Aufbewahrung der Measurement-V4-Messdaten und nicht um eine andere Regler-Eingangsdatenfrequenz.",
    "MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE": "Hier wählst du, ob die Diagnose nur Topics passend zum eingestellten Muster anzeigt oder alle vom Controller empfangenen Nachrichten betrachtet. Für eine gezielte Fehlersuche ist „gefiltert“ übersichtlicher und weniger belastend; „alle“ ist nur zeitweise sinnvoll. Der Modus ändert keine MQTT-Abonnements für normale Regelungskommandos.",
    "MQTT_BROKER": "Ohne erreichbaren MQTT-Broker kann ZEC Zendure-Telemetrie oder Leistungsbefehle nicht zuverlässig übertragen. Diese Adresse wirkt zusammen mit Port und optionalem Zugang, unabhängig von der eigens gewählten Netzleistungsmessung durch SMA oder Shelly. Der Broker kann lokal oder im eigenen Netzwerk betrieben werden; ein nicht erreichbarer Broker darf nicht als gesunde Verbindung angezeigt werden.",
    "MQTT_PASSWORD": "Das Kennwort gehört ausschließlich zur Anmeldung am gewählten MQTT-Broker und ergänzt dessen Adresse, Port und gegebenenfalls Benutzername. Ist für den Broker kein Login vorgesehen, kann es leer bleiben. Falsche Zugangsdaten verhindern unter Umständen aktuelle Zendure-Werte und Befehle; dieses Feld ist keine Einstellung einer Batterie-Regelstrategie.",
    "MQTT_PORT": "Brokeradresse und Port gehören zusammen und bestimmen den erreichbaren MQTT-Dienst, über den ZEC Zendure-Telemetrie und Kommandos austauscht. Ein nicht passender Port unterbricht möglicherweise die Verbindung, obwohl die gewählte SMA-/Shelly-Netzmessung weiterhin funktioniert. Der Port legt weder Ladeleistung noch Controller-Regeltakt fest.",
    "MQTT_USER": "Der Benutzername wird nur für einen MQTT-Broker benötigt, der eine Anmeldung verlangt. Er ergänzt Kennwort, Brokeradresse und Port; sein Inhalt beeinflusst weder die Netzleistungsquelle noch direkt eine Ladeentscheidung. Bei Anmeldefehlern darf ZEC keine vermeintlich frischen Zendure-Daten aus alten MQTT-Nachrichten ableiten.",
    "GRID_POWER_PLAUSIBILITY_MAX_ABS_W": "Diese Grenze verwirft Netzleistungs-Rohwerte, die für die reale Anlage offenkundig unplausibel hoch sind. Sie schützt die AUTO-Regelung vor Ausreißern, egal ob die Quelle SMA oder Shelly heißt. Sie ist keine maximale Hauslast und kein gewünschter Netzleistungssollwert; Quellidentität und Frischeprüfung bleiben getrennte notwendige Schutzschichten.",
    "SMA_ENERGY_METER_LOG_DIAGNOSTICS": "Damit kannst du bei SMA-Empfangsproblemen Details zu UDP-Socket, Paketlücken oder Filterung sichtbar machen. Die Meldungen werden erst bei passender Runtime-Logging-Konfiguration in Dateien geschrieben. Sie aktivieren keinen zweiten Netzleistungsregler, ändern die Zählerauswahl nicht und dienen nur der nachvollziehbaren Diagnose.",
    "SMA_ENERGY_METER_LOG_INTERVAL_SECONDS": "Diese Zeit begrenzt die Häufigkeit wiederholter SMA-Diagnosemeldungen, damit das Runtime-Log bei intakter Messung nicht unnötig wächst. Sie ist nur bei aktiviertem SMA-Diagnoselogging relevant und ändert weder den eigentlichen Speedwire-Empfang noch den Aktualisierungstakt der Netzleistung.",
    "SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS": "Überschreitet der Abstand zwischen empfangenen SMA-Telegrammen diese Zeit, kennzeichnet die SMA-Diagnose eine verdächtige Empfangslücke. Das hilft, Netzwerk- und Quellprobleme zu unterscheiden. Diese Warnschwelle ist nicht mit dem separat wirksamen Messdaten-Stale-Timeout zu verwechseln und schaltet den Controller nicht selbst um.",
    "SMA_ENERGY_METER_GROUP": "Die Multicast-Gruppe gibt vor, von welcher Netzwerkgruppe der lokale SMA-Empfänger Speedwire-Telegramme empfängt. Sie wirkt zusammen mit UDP-Port und gewählter Netzwerkschnittstelle. Eine falsche Gruppe verhindert aktuelle Zählerwerte; die Seriennummerfilterung muss zusätzlich sicherstellen, dass der richtige Zähler für den Hausanschlusspunkt ausgewertet wird.",
    "SMA_ENERGY_METER_INTERFACE": "Bei mehreren Netzwerkschnittstellen kann dieser Wert den lokalen Netzwerkadapter für den SMA-Multicast-Empfang festlegen. Er ergänzt Gruppenadresse und UDP-Port und muss den tatsächlichen SMA-Datenpfad erreichen. Das Feld entscheidet nicht, welcher von mehreren SMA-Zählern fachlich richtig ist – dafür sind Seriennummer und gegebenenfalls SUSy-ID maßgeblich.",
    "SMA_ENERGY_METER_PASSIVE_ENABLED": "Wenn die eigentliche Netzleistungsquelle Shelly-kompatibles HTTP ist, kann ZEC SMA-Daten zusätzlich nur zur Gegenprüfung mitlesen. Diese passive Messung darf nicht stillschweigend den aktiven Reglerwert ersetzen. Bei direkt ausgewählter SMA-Netzleistungsquelle wird der nötige Empfänger ohnehin verwendet; dieser Schalter gibt dann keine zusätzliche Funktion frei.",
    "SMA_ENERGY_METER_PORT": "Der UDP-Port ergänzt die SMA-Speedwire-Multicast-Gruppe und die ausgewählte Netzwerkschnittstelle. Standardmäßig verwenden SMA-Energy-Meter-Telegramme häufig 9522. Ein anderer Wert kann die Netzleistungsquelle unbrauchbar machen, ändert aber weder die Seriennummer des auszuwertenden Geräts noch die zulässige Zendure-Leistung.",
    "SMA_ENERGY_METER_SERIAL": "In einer Anlage mit mehreren SMA-Zählern schützt die Seriennummer davor, den Produktionszähler anstelle des Hausanschlusspunktzählers für die AUTO-Regelung zu verwenden. Sie ist zusammen mit korrektem Multicast-Empfang und Protokollvalidierung zu prüfen. Die Identität ist daher sicherheitsrelevant und nicht bloß ein Anzeigename.",
    "SMA_ENERGY_METER_SOCKET_MODE": "Diese Expertenoption bestimmt, wie der SMA-UDP-Socket auf dem Raspberry Pi gebunden wird, insbesondere bei parallelem EVCC- oder anderem SMA-Empfang. Sie wirkt nur auf den Netzwerk-Empfänger und kann bei ungünstiger Wahl andere Listener stören. Die Zahl der Messpunkte oder die AUTO-Reglergeschwindigkeit wird dadurch nicht automatisch erhöht.",
    "SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS": "Nach dieser Dauer ohne neue gültige SMA-Messung muss ZEC den Hausnetzleistungswert als veraltet einstufen, falls SMA als aktive Netzquelle gewählt ist. Alte Werte dürfen nicht für neue AUTO-Korrekturen herangezogen werden. Sie ist unabhängig von der Diagnosewarnung für einzelne Telegrammlücken und von der Shelly-Frischegrenze.",
    "SMA_ENERGY_METER_SUSY_ID": "Zusätzlich zur Seriennummer kann die SMA-SUSy-ID die Herkunft der eingehenden Speedwire-Daten präzisieren. Besonders bei mehreren SMA-Geräten hilft sie, den richtigen Netzanschlusspunktzähler zu identifizieren. Ein falscher Filter darf nicht durch willkürliche Fremdzählerwerte ersetzt werden; auch die Frame-/Plausibilitätsprüfung bleibt verbindlich.",
    "SHELLY_IP": "Bei aktiv ausgewählter Shelly-kompatibler Netzleistungsquelle sendet ZEC lesende HTTP-Anfragen an diese Adresse. Der Endpunkt muss die tatsächliche Hausnetzleistung mit richtigem Vorzeichen liefern; die dazugehörige Stale-Grenze verhindert die Nutzung zu alter Daten. Das Feld ist bei direkter SMA-Regelquelle nicht die aktive Zähleradresse.",
    "SHELLY_STALE_TIMEOUT_SECONDS": "Diese maximale Messaltergrenze gilt speziell für die Shelly-kompatible HTTP-Netzleistungsquelle. Ohne frische Werte darf AUTO nicht mit einem alten Hausnetzfluss weiterrechnen; die direkte SMA-Quelle verwendet stattdessen ihren eigenen Receiver-Timeout. Der Timeout ist keine Reglerverzögerung und darf Datenfehler nicht verdecken.",
    "GRID_METER_SOURCE": "Mit dieser Auswahl entscheidest du, aus welchem echten Zähler ZEC Hausnetzbezug und Einspeisung für die Leistungsregelung ableitet. SMA-Direktquelle liest lokale Speedwire-Telegramme; Shelly-kompatibles HTTP bezieht einen Endpunkt. Beide Wege haben eigene Adressen, Identitäts- und Frischeprüfungen. Ein falsch gewählter Zähler kann echte Export- und Importwerte verwechseln; Diagnose-Receiver sind kein stiller Ersatz.",
    "ZENDURE_LOCAL_API_ENABLED": "Dieser Schalter macht die lokale Zendure-Gerätediagnose über die Weboberfläche zugänglich. Er erlaubt für sich allein nicht, lokale Messwerte anstelle von MQTT für die normale Regelung zu verwenden. Dafür sind der getrennte Telemetrie-Schalter, die Fallback-Regel und die lokale Geräte-IP erforderlich; die Kommandosteuerung bleibt weiterhin dem bestehenden autorisierten Pfad vorbehalten.",
    "ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS": "Wenn die lokale Zendure-API nicht antwortet, wartet ZEC diese Mindestzeit bis zum nächsten Versuch. Das reduziert Last und störende Wiederholungsanfragen an Headunit und lokale Dienste. Es wirkt zusammen mit Pollintervall und Timeout, nicht mit der normalen 3-s-Reglerberechnung oder MQTT-Command-Recovery.",
    "ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS": "Dieses Intervall begrenzt, wie häufig der Hintergrundworker lokale Zendure-Telemetrie abfragen darf. Kürzere Werte bedeuten mehr Netzwerk-/Gerätelast, garantieren aber keine schnelleren physischen Sensorsamples. Sie sind nicht mit dem 1-s-Webstatus-Poll und nicht mit der MQTT-Messaktualität gleichzusetzen.",
    "ZENDURE_LOCAL_API_SOC_PRIORITY": "Liefert die lokale Geräte-API mehrere unterschiedliche SOC-Felder, bestimmt diese Auswahl, welches bevorzugt gelesen wird. Die Wahl beeinflusst nur die Interpretation dieser Quelle, nicht den tatsächlichen Ladezustand; ob API-Werte überhaupt den aktiven ZEC-SOC ergänzen dürfen, entscheiden separate Telemetrie- und Fallback-Schalter.",
    "ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY": "Bei aktivem Fallback bleibt MQTT die bevorzugte Quelle für Zendure-SOC und Istleistung. Nur wenn passende MQTT-Daten fehlen oder veraltet sind, kann die freigegebene lokale API einspringen; nach MQTT-Recovery wechselt ZEC zurück. Der Modus wirkt nur, wenn die lokale API-Nutzung für Telemetrie überhaupt aktiviert ist.",
    "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": "Damit darf ZEC die lesende lokale Zendure-API zusätzlich für SOC, Istleistung und gegebenenfalls Temperatur heranziehen. Welche Quelle Vorrang hat, regelt der separate Nur-Fallback-Schalter; MQTT bleibt der autorisierte Kommando-Transport. Eine API-Abfrage allein ist kein Nachweis neuer Gerätedaten und nicht jede lokale Quelle muss sekündlich liefern.",
    "ZENDURE_LOCAL_IP": "Diese IP bezeichnet die echte Zendure-Headunit für lesende lokale API-Anfragen und Gerätediagnose. Sie wirkt zusammen mit Diagnose-/Telemetrie-Aktivierung, Pollintervall und Timeout. Eine falsche Adresse darf keine alten MQTT-Werte als neue API-Proben erscheinen lassen; die Adresse gibt keine neue Gerätelschreibberechtigung frei.",
    "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": "Der getrennte kurze Zeitdeckel begrenzt einzelne lokale API-Hintergrundaufrufe, selbst wenn das allgemeine Timeout großzügiger gewählt wurde. Damit soll eine langsame Headunit den laufenden Controller nicht ausbremsen. Er verändert weder das Regler-Sollwertziel noch die sichere MQTT-Rückmeldung eines Leistungsbefehls.",
    "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": "Diese Wartezeit begrenzt einen einzelnen lokalen Zendure-API-Aufruf im asynchronen Hintergrundworker. Zu lange Zeiten halten Ressourcen beschäftigt, sehr kurze können gültige langsamere Antworten verwerfen. Zusammen mit Pollintervall und Fehlerpause entsteht ein begrenzter Diagnose-/Telemetriepfad, kein blockierendes I/O im Regelzyklus.",
})


SYSTEM_PURPOSE_VNEXT: Mapping[str, str] = MappingProxyType({
    "WEB_SERVICE_RESTART_ENABLED": "Mit dieser Option darf die Weboberfläche bei bestätigten neustartpflichtigen Settings den ZEC-Dienst über einen gesondert autorisierten Helper neu starten. Das ist eine Zugriffs-/Betriebsfunktion, kein Reglermodus. Fehlt die Betriebssystemfreigabe, bleibt der Neustart trotz Schalter gesperrt; ungespeicherte Änderungen werden nicht dadurch automatisch übernommen.",
    "ANALYSIS_EXTENDED_MAX_FILES": "Diese höhere Dateianzahl ist ausschließlich für bewusst genehmigte umfangreichere Offline-/Replay-Untersuchungen gedacht. Normale Analysen bleiben durch die kleineren Standardlimits begrenzt, damit der Raspberry Pi für Regler, MQTT und EVCC reaktionsfähig bleibt. Mehr Dateien bedeuten mehr potenzielle RAM- und CPU-Last, nicht präzisere aktuelle Batteriekommandos.",
    "ANALYSIS_EXTENDED_MAX_ROWS": "Hier legst du die maximale Zahl von Messpunkten für einen ausdrücklich erweiterten Analysejob fest. Das Limit wird vor zu großer Verarbeitung geprüft und ist von der normalen kleineren Zeilenbegrenzung getrennt. Sehr große Werte können RAM und Laufzeit trotzdem erhöhen; für Langzeitforensik bevorzugt ZEC begrenzte Streamingextrakte statt vollständige RAM-Materialisierung.",
    "ANALYSIS_EXTENDED_MAX_TOTAL_BYTES": "Diese Obergrenze schützt vor dem Versuch, zu große Messdateisammlungen auf dem produktiven Pi zu laden. Sie greift zusätzlich zu Dateianzahl und Zeilenlimit; ein größerer Bytewert hebt weder Worker-Speicherlimit noch Laufzeitgrenze auf. Sehr große Auswertungen sind eher offline auf einem leistungsfähigeren Rechner sinnvoll.",
    "ANALYSIS_EXTENDED_WORKER_MEMORY_LIMIT_MB": "Bei einem bewusst erweiterten Analyseauftrag begrenzt dieser Wert den Speicherverbrauch des getrennten Analyseworkers. Er wirkt zusätzlich zu Datei-, Zeilen- und Bytebudget. Höhere Grenzen können größere Auswertungen erlauben, den Pi aber so stark beanspruchen, dass Live-Dienste leiden; das ist keine Ladeleistungs- oder Speichergröße der Batterien.",
    "ANALYSIS_EXTENDED_WORKER_TIMEOUT_SECONDS": "Diese Grenze beendet bewusst erweiterte lokale Analysen, die zu lange dauern. Sie ergänzt deren Speicher- und Eingabedatenlimits; ein längerer Timeout kann ressourcenintensive Jobs länger auf dem Pi halten. Die Steuerung von Zendure arbeitet unabhängig und darf nicht auf eine Analyse warten.",
    "ANALYSIS_MAX_FILES": "Damit bestimmst du, wie viele ausgewählte Messdateien der normale lokale Analysedienst höchstens verarbeitet. Zusammen mit Zeilen-, Byte-, RAM- und Laufzeitlimits schützt das die laufende Regelung vor Ressourcenengpässen. Eine zu geringe Grenze lehnt sehr große Untersuchungen kontrolliert ab, ohne Messdaten zu löschen.",
    "ANALYSIS_MAX_ROWS": "Diese maximale Zeilenzahl begrenzt normale Auswertungen bereits während der Eingabeverarbeitung. Sie ist unabhängig von Dateigröße und Worker-Speichergrenze; alle Limits müssen passen. Wird ein Job abgewiesen, bedeutet das keine fehlerhaften Realmesswerte und keine Änderung des Controllerbetriebs.",
    "ANALYSIS_MAX_TOTAL_BYTES": "Dieses Limit schützt vor großen CSV-Eingaben, die im Speicher viel mehr Platz als ihre Dateigröße benötigen können. Es greift zusätzlich zur Datei- und Zeilenbegrenzung. Auf dem Raspberry Pi sind größere Forensikfenster daher vorab zu extrahieren oder offline auszuwerten, statt den laufenden Controller zu gefährden.",
    "ANALYSIS_WORKER_MEMORY_LIMIT_MB": "Normale Analysen laufen in einem begrenzten Worker statt im Reglerprozess. Diese Grenze verhindert, dass eine aufwendige Untersuchung den gesamten Pi-Speicher verbraucht. Bei Überschreitung wird der Analysejob beendet; seine Resultate sind dann unvollständig und dürfen nicht als erfolgreicher Energienachweis behandelt werden.",
    "ANALYSIS_WORKER_TIMEOUT_SECONDS": "Wenn eine normale Analyse länger als dieser Wert benötigt, bricht ZEC den getrennten Worker ab. Zusammen mit Speicher-, Datei- und Zeilenlimits bleibt die Last des Analysedienstes begrenzt. Ein Timeout ändert weder die historische Messung noch den Sollwert für Zendure und rechtfertigt keine automatische Wiederholung ohne Rücksicht auf Ressourcen.",
    "REPLAY_WEB_PORT": "Dieser Port gehört ausschließlich zum optionalen eigenständigen Analyse-/Replay-Webdienst, nicht zum normalen ZEC-Status- und Settings-Portal. Der Replay-Dienst muss gesondert gestartet beziehungsweise freigegeben werden; eine Portangabe aktiviert keine zusätzliche Controllerinstanz oder Befehlssteuerung.",
    "UI_DARK_MODE": "Mit dieser Einstellung wählst du ein dunkles oder helles Erscheinungsbild der ZEC-Webseiten. Es betrifft Status, Settings und Diagramme, nicht den Lade-/Entladealgorithmus, Datenquellen oder aktive Sicherheitsgrenzen. Nach Übernahme wird das Farbschema bei neu dargestellten Seiten sichtbar.",
    "UI_MODE": "Der Standardmodus zeigt die wichtigsten Informationen und Einstellungen ohne unnötige technische Details. Im Expertenmodus kommen zusätzliche Diagnosefelder und technische Optionen hinzu; entscheidende Warnungen und Basisinformationen bleiben sichtbar. Der Ansichtsmodus erteilt keine neuen Gerätebefehle und schaltet keine bisher gesperrte Schutzfunktion aus.",
    "SLOW_CYCLE_WARN_MS": "Diese Zeit ist eine Warnschwelle für ungewöhnlich lange Ausführung eines einzelnen Controllerzyklus. Sie hilft zu erkennen, ob CPU, Datenträger oder andere lokale Pfade den Regelbetrieb verzögern. Der eingestellte Warnwert verändert weder das eigentliche Regelintervall noch die physische Ladeleistung und ist kein Leistungsoptimierungsparameter.",
    "FILE_LOG_BACKUP_COUNT": "Hier wählst du, wie viele alte Runtime-Textprotokolle nach einer Rotation erhalten bleiben. Zusammen mit maximaler Dateigröße und dem Logverzeichnis ergibt sich der ungefähre Speicherbedarf. Mehr Historie erleichtert die Fehlersuche, ist aber nicht mit der langfristigen CSV-Messdatenaufbewahrung zu verwechseln.",
    "FILE_LOG_DIR": "Wenn Datei-Logging eingeschaltet ist, legt dieser Pfad fest, wohin ZEC Betriebs- und Fehlermeldungen schreibt. Der Dateiname und die Rotationsgrenzen werden separat eingestellt. Ein falscher oder unbeschreibbarer Pfad vermindert die Diagnosehistorie, darf aber weder Reglerparameter ändern noch die Headunit aggressiver ansteuern.",
    "FILE_LOG_ENABLED": "Zusätzlich zu systemd/journald kann ZEC normale Laufzeitmeldungen in einer rotierenden Textdatei sammeln. Dies hilft bei längeren Fehlersuchen, ist aber nicht dasselbe wie das strukturierte Measurement-V4-Log mit echten Regler- und Energiemesspunkten. Speicherort, Dateigröße und Aufbewahrung werden separat begrenzt.",
    "FILE_LOG_FILE": "Dieser Wert benennt die aktuell beschriebene Runtime-Textdatei, sofern das Datei-Logging eingeschaltet ist. Verzeichnis, maximale Dateigröße und Zahl älterer Backups kontrollieren den tatsächlichen Speicherbedarf. Ein Name allein aktiviert keine zusätzlichen Diagnosen, keine Messdatenspeicherung und keine Regleränderung.",
    "FILE_LOG_MAX_BYTES": "Erreicht die laufende Textlogdatei diese Größe, rotiert ZEC zu einer neuen Datei und hält gemäß Backupzahl ältere Fassungen vor. Niedrigere Limits erzeugen mehr Dateiwechsel, höhere längere Einzelprotokolle. Das betrifft nur Laufzeittexte; Measurement-V4 und SQLite-Graphdaten haben andere Speicherverträge.",
    "DEBUG": "Dieser Schalter erhöht die allgemeine Konsolen-Ausführlichkeit und kann beim Nachvollziehen seltener Fehler helfen. Er ist keine Freigabe für die separate MQTT-Diagnose oder für zusätzliche Command-Publishes. Dauerhaft unnötig viele Meldungen machen Logs unübersichtlich und können Ressourcen beanspruchen.",
    "LOG_CONTROL": "Zusätzliche menschlich lesbare Zeilen helfen beim Nachvollziehen, wie ZEC aktuelle Messwerte zu Leistungszielen verarbeitet hat. Sie ergänzen die strukturierte Measurement-V4-Diagnose, ersetzen sie aber nicht. Mehr Protokolltext darf weder das Zielwertrechnen noch die sicherheitsrelevanten Command-Wirkungsprüfungen verändern.",
    "LOG_MANUAL": "Mit diesem Detailkanal protokolliert ZEC die Ausführung fester Lade-/Entlademodi, deren Ziel-SOC und den anschließenden Moduswechsel. Die Aufzeichnung ist nur zur Diagnose gedacht; ob ein manueller Modus tatsächlich aktiv ist, entscheidet weiterhin die betreffende Betriebsarteinstellung.",
    "LOG_MQTT": "Dieser Logkanal macht sichtbar, welche MQTT-Kommandos ZEC gesendet hat und unterstützt den Vergleich mit Command-Readback und beobachteter Istleistung. Ein veröffentlichter Befehl ist noch kein Beweis, dass das Gerät ihn umgesetzt hat. Das Logging erhöht weder die normale Wiederholungsfrequenz noch die erlaubten Leistungsgrenzen.",
    "LOG_RAW_RESPONSE": "Beim Shelly-kompatiblen Netzmesspfad kann ZEC vollständige HTTP-Antworten zur gezielten Fehleranalyse protokollieren. Das erzeugt umfangreichere Textdaten und kann Nutzungsinformationen enthalten. Es wirkt nur auf die Nachvollziehbarkeit der bereits verwendeten Quelle; die Auswahl des Zählers und Plausibilitätsfilter bleiben unabhängig.",
    "LOG_SOC": "Hier zeichnest du zusätzlich auf, wann Zendure neue Ladezustände gemeldet hat. Das hilft, Stale-Ereignisse und die Anwendung von Mindest-/Maximal-SOC nachzuvollziehen. Es ändert weder den realen Batterie-SOC noch die Schwellen und liefert nicht automatisch ein neues physisches Sample.",
    "LOG_VALUES": "Dieser Detailkanal stellt gemessene Netzleistungswerte und ihre Glättung gegenüber. Er hilft zu verstehen, weshalb AUTO auf eine Schwankung ruhiger oder schneller reagiert. Die Logausgabe ändert nicht die Wahl zwischen Shelly und SMA, und die Settings für Mittelung/Gain bleiben weiterhin für die Regelung verantwortlich.",
    "MAX_CONSECUTIVE_ERRORS": "Diese Fehlerzahl verhindert, dass ZEC bei einer Serie unzuverlässiger Mess- oder Laufzeitfehler unendlich weiter aktiv nachregelt. Nach genug direkt aufeinanderfolgenden Fehlern wechselt es in den Schutzbetrieb und fordert soweit über den verfügbaren Kommandoverbindungspfad möglich neutrale Leistung an. Der Wert ist kein allgemeiner Retry- oder Netzfilter und darf nicht zu großzügig gewählt werden.",
    "MQTT_DISCONNECTED_SAFE_STATE": "Bei erkannter MQTT-Verbindungsunterbrechung ist eine sichere aktuelle Geräteansteuerung nicht mehr gewährleistet. Mit aktivem Schalter versucht ZEC konservativ auf Neutralität zu gehen; ohne Verbindung kann ein 0-W-Kommando aber nicht garantiert physisch ankommen. Bei Aus wird nicht pauschal neutralisiert, sodass alte zuletzt bestätigte Gerätezustände fortbestehen können. Das ist eine echte Sicherheitsabwägung, kein bloßer Warnschalter.",
    "SAFE_STATE_ON_SHELLY_ERROR": "Wenn die Shelly-kompatible Hausnetzmessung dauerhaft fehlerhaft ist, kann ZEC auf eine konservative neutrale Ansteuerung zurückfallen, statt mit alten Netzleistungswerten zu rechnen. Diese Option hängt an der gewählten Shelly-Messquelle und deren Frischeprüfung; direkte SMA-Messungen haben einen eigenen Datenpfad und dürfen nicht blind mit Shelly-Ausfällen gleichgesetzt werden.",
    "SOC_STALE_TIMEOUT_SECONDS": "Der Zendure-SOC muss frisch genug sein, damit ZEC nicht auf Grundlage eines alten Ladezustands weiter entlädt. Nach dieser Zeit ohne neue gültige Meldung werden die entsprechenden Entladefreigaben konservativ blockiert; das betrifft AUTO, Nacht und feste Entladung. Die Grenze ist unabhängig vom Höchst-/Mindest-SOC-Wert selbst.",
    "ZENDURE_POWER_STALE_TIMEOUT_SECONDS": "Hier bestimmst du, ab welchem Datenalter die gemeldete Zendure-Istleistung als veraltet gekennzeichnet werden soll. Ein alter Istwert eignet sich nicht als aktueller Nachweis dafür, dass ein Kommando ausgeführt wurde. Diese Einstellung setzt keinen Sollwert und darf nicht mit dem Messalter der Hausnetzleistung oder dem UI-Pollintervall verwechselt werden.",
    "HEADLESS_MODE": "ZEC kann die normalen Webseiten durch eine kurze Hinweisseite ersetzen, während der Controller im Hintergrund weiterarbeitet. Dadurch wird insbesondere der lokale Zugang zu Einstellungen und Diagnose bewusst eingeschränkt. Den Modus darf man nicht mit „Regelung deaktivieren“ verwechseln; zum Rückwechsel wird die reale Konfiguration auf einem erlaubten Weg geändert.",
    "WEB_HOST": "Diese Bind-Adresse legt fest, auf welchen Netzwerkadressen ZEC seinen HTTP-Server anbietet. In Verbindung mit dem Webport entscheidet sie, ob die Oberfläche nur lokal oder auch im Heimnetz erreichbar ist. Eine falsche Wahl kann den Zugriff blockieren; sie verändert weder MQTT-Verbindung noch die Batterie-Regelstrategie.",
    "WEB_PORT": "Dieser Port bildet zusammen mit der Webhost-Bindung die Adresse der ZEC-Oberfläche. Eine Änderung braucht den vorgesehenen Neustart beziehungsweise die abgesicherte Deployment-Konfiguration und kann den gespeicherten Browserlink ungültig machen. Der Port ist kein MQTT-Brokerport und ändert nicht den Controllerzyklus.",
    "ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS": "Direkt nach Broker-/Controller-Wiederanlauf können einige nicht dauerhaft gespeicherte Zendure-Sensortopics vorübergehend fehlen. Dieses Zeitfenster verhindert vorschnelle Diagnosen eines permanenten Fehlers. Es macht fehlende Livewerte aber nicht zu frischen Messdaten und hebt keine SOC-/Command-Sicherheitsgrenzen auf.",
    "ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS": "Wenn wesentliche Zendure-MQTT-Datengruppen länger nicht aktualisiert wurden, soll ZEC dies klar als Teil- oder Vollstaleness anzeigen. Zusammen mit der Restart-Gnadenzeit trennt der Wert normale Wiederverbindung von anhaltendem Quellproblem. Eine Warnung allein beweist keine neue Istleistung und darf nicht als Erlaubnis für riskante Befehle gelten.",
})


# Complete the previously very terse control/recovery help with the real
# interaction between observation, final command and safety handling.
RICH_EXTENDED.update({
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": "Diese Zeit verhindert, dass eine kurze Netzexportspitze sofort den speziellen Near-Limit-/Restüberschuss-Zweig auslöst. Erst wenn die passende Primärspeicher-Ladeannahme- und Exportlage lange genug bestätigt ist, darf ZEC zusätzlichen Restexport für Zendure prüfen. Mindestexport, Primärspeicher-Schwelle, Fast Capture und die unveränderten SOC-/Cross-Charge-Grenzen bleiben jeweils eigene Bedingungen.",
    "COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS": "Wenn ZEC aus Sicherheitsgründen aktiv 0 W anfordert, muss die gemeldete Zendure-Istleistung innerhalb eines begrenzten Zeitfensters plausibel nachziehen. Diese Grenze entscheidet, ab wann eine ausbleibende physische Neutralisierung als möglicher Commandfehler weiterbehandelt wird. Sie erzeugt kein dauerndes Nullkommando und ist von der normalen AUTO-Reglerverzögerung und dem Resync-Cooldown getrennt.",
    "ZENDURE_COMMAND_STATE_FRESH_SECONDS": "Für eine verlässliche Command-Rückmeldung muss ZEC den vollständigen Gerätezustand aus Betriebsart und Lade-/Entladegrenzen aktuell kennen. Diese Zeit legt fest, wann solche Readbackwerte zu alt werden, um eine neue Zustandsbestätigung zu behaupten. Sie unterscheidet sich vom SOC- und Istleistungsalter und erlaubt weder neue Geräteschreibbefehle noch eine Umgehung des Single-Owner-Schutzes.",
    "ZENDURE_COMMAND_STATE_RETRY_SECONDS": "Wenn nach einer Kommandoumstellung noch keine belastbare Bestätigung aller relevanten Gerätezustandsfelder vorliegt, darf der Recoverypfad nach dieser Zeit erneut prüfen oder den zulässigen Zustand herstellen. Das ist kein periodisches Senden des normalen AUTO-Ziels. Zusammen mit SmartMode-Retry, Aktualitätsgrenze und Resync-Cooldown soll der Wert unbestätigte Zustände erkennen, ohne die Headunit mit Wiederholbefehlen zu belasten.",
    "ZENDURE_SMART_MODE_RETRY_SECONDS": "SmartMode ist Teil des erwarteten vollständigen Zendure-Gerätezustands. Bleibt der gewünschte Modus trotz zulässiger Anforderung unbestätigt, kann ZEC erst nach dieser Wartezeit im vorgesehenen Recoveryverfahren erneut handeln. Die Zeit beeinflusst nicht, wie schnell AUTO auf die Netzleistung reagiert, und umgeht weder die Command-State-Prüfung noch die allgemeine Drosselung von Wiederabgleichen.",
    "COMMAND_RESYNC_COOLDOWN_SECONDS": "Nach einem vollständigen Wiederabgleich von Zendure-Betriebsart und Leistungsgrenzen verhindert dieser Cooldown, dass ZEC denselben Recoveryversuch unmittelbar immer wieder startet. So wird die Headunit vor unnötig vielen Publish-/Modewechseln geschützt. Ein kleinerer Wert kann echte Störungen schneller erneut behandeln, erhöht aber das Risiko einer Kommandoschleife; normales AUTO und die gesonderte 0-W-Neutralisierung bleiben andere Pfade.",
})


# V17.1.3: Explicit inactive behaviour for all operational boolean controls.
# Each text describes ONLY the named feature; other independent protection
# and observation paths are not implicitly turned off.
BOOLEAN_DISABLED_EXPLAINED = MappingProxyType({
    "NIGHT_DISCHARGE_ENABLED": "Ohne Aktivierung findet keine feste Nachtentladung statt. Die gespeicherten Nachtzeiten und Leistungswerte lösen dann keine Nachtbefehle aus; AUTO und die normalen Schutzgrenzen bleiben bestehen.",
    "SECOND_BATTERY_INTEGRATION_ENABLED": "Ohne diese Anbindung nutzt ZEC keine Primärspeicherwerte für die zusätzliche Speicherkoordination. Die Zendure-Automatik bleibt mit ihren eigenen Schutzgrenzen nutzbar; es werden keine fehlenden Primärspeicherwerte erfunden.",
    "HARVEST_HIGH_SMA_SOC_ENABLED": "Der zusätzliche High-SOC-Verteilungszweig bleibt ausgeschaltet. Normale Ladeautomatik und unabhängig erlaubte Restüberschussaufnahme arbeiten weiter.",
    "REST_SURPLUS_HARVEST_ENABLED": "Die zusätzliche Restüberschuss-Ernte und ihre davon abhängigen Einstellungen bleiben ohne Wirkung. Die normale AUTO-Regelung und sämtliche Sicherheitsgrenzen bleiben aktiv.",
    "HARVEST_SEASON_POLICY_ENABLED": "Die zusätzliche saisonale Verteilung bleibt ausgeschaltet; ZEC nutzt die bisherige parallele Strategie. Eine bereits gespeicherte Saisonwahl wirkt nicht, normale Restüberschussaufnahme bleibt möglich.",
    "CROSS_CHARGE_ENABLED": "ZEC führt bei ausgeschalteter Option nicht die zusätzliche Gegenflussbegrenzung zwischen den Speichern aus. Die übrigen SOC-, Geräte- und Befehlsgrenzen gelten weiterhin. Bei zwei Speichern kann das Risiko unerwünschten Umladens steigen.",
    "SECOND_BATTERY_STALE_BLOCK_CHARGE": "Veraltete Primärspeicherdaten bewirken durch diese Option dann keinen zusätzlichen Ladeblock. Andere Frische- und Sicherheitsprüfungen bleiben bestehen; fehlende Werte gelten nicht automatisch als aktuell.",
    "COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS": "Nach jeder MQTT-Wiederverbindung wird nicht allein aufgrund dieser Einstellung ein vollständiger zusätzlicher Wiederabgleich angefordert. Andere erforderliche Command-Recovery- und Sicherheitsprüfungen bleiben bestehen.",
    "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": "Wenn das bevorzugte externe Speicherziel ausfällt, wechselt die Messwertaufzeichnung nicht durch diese Option automatisch auf die SD-Karte. ZEC darf deshalb fehlgeschlagene Schreibversuche nicht als gespeicherte Messdaten melden.",
    "MEASUREMENT_DB_ENABLED": "Der zusätzliche SQLite-Graphdatenpfad wird nicht durch diese Einstellung mit neuen Daten versorgt. Das Measurement-V4-Logging ist eine getrennte Funktion; der Regler arbeitet unabhängig davon weiter.",
    "SOC_DAY_GRAPH_BOOTSTRAP_FROM_MEASUREMENTS": "Vorhandene Measurement-Daten werden nicht für den zusätzlichen Aufbau des SOC-Tagesgraphen verwendet. Andere bereits gespeicherte Tageswerte bleiben davon unberührt.",
    "SOC_DAY_GRAPH_ENABLED": "Der SOC-Tagesgraph wird nicht als aktive Zusatzansicht geführt. Die Speicherregelung und sonstige Messwerterfassung laufen unabhängig weiter.",
    "MQTT_TOPIC_DIAGNOSTIC_ENABLED": "Die zusätzliche MQTT-Topic-Diagnose wird nicht aufgezeichnet oder angezeigt. Die reguläre MQTT-Kommunikation des Controllers läuft unverändert weiter.",
    "SMA_ENERGY_METER_LOG_DIAGNOSTICS": "Es werden keine zusätzlichen Diagnosemeldungen dieser SMA-Direktquelle ins Runtime-Log geschrieben. Eine konfigurierte aktive Quelle wird dennoch weiterhin gelesen.",
    "SMA_ENERGY_METER_PASSIVE_ENABLED": "Eine nicht als aktive Netzleistungsquelle gewählte SMA-Quelle wird nicht zusätzlich passiv zur Diagnose beobachtet. Das ändert die aktive Netzleistungsmessung nicht.",
    "ZENDURE_LOCAL_API_ENABLED": "Die lokale Zendure-API wird nicht als zusätzliche Diagnosequelle angefragt. MQTT bleibt der normale Command- und Telemetriepfad.",
    "ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY": "Diese Einschränkung auf Ersatzdaten gilt dann nicht als zusätzliche Bedingung; ob Daten der lokalen API überhaupt benutzt werden dürfen, hängt weiterhin von den getrennten Aktivierungs- und Quellenoptionen ab.",
    "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": "Werte aus der lokalen Zendure-API werden nicht in den normalen Telemetriepfad übernommen. Ein separater API-Diagnoseaufruf kann bei entsprechender Freigabe weiterhin möglich sein.",
    "WEB_SERVICE_RESTART_ENABLED": "Die administrative Neustartaktion bleibt in der Weboberfläche gesperrt. Der Controller und seine normalen automatischen Abläufe werden dadurch nicht abgeschaltet.",
    "UI_DARK_MODE": "Die Oberfläche bleibt im hellen Darstellungsmodus. Die Regelung und gespeicherten Leistungsziele ändern sich dadurch nicht.",
    "FILE_LOG_ENABLED": "Zusätzliche Textprotokolldateien werden nicht über diese Option geschrieben. Sicherheitsereignisse, notwendige Laufzeitmeldungen und andere konfigurierte Datenpfade sind gesondert zu betrachten.",
    "DEBUG": "Zusätzliche ausführliche Debugmeldungen bleiben ausgeschaltet. Normale Betriebs- und Fehlermeldungen sind hiervon unabhängig.",
    "LOG_CONTROL": "Keine zusätzlichen detaillierten Meldungen zu jeder Regelentscheidung im Textlog. Die eigentliche Regelung bleibt aktiv.",
    "LOG_MANUAL": "Die zusätzliche Protokollierung manueller Modusentscheidungen entfällt; die manuelle Steuerungsfunktion bleibt vorhanden.",
    "LOG_MQTT": "Zusätzliche MQTT-Debugmeldungen entfallen. Die normale MQTT-Verbindung und Kommandos werden dadurch nicht deaktiviert.",
    "LOG_RAW_RESPONSE": "Unverarbeitete Shelly-Antworten werden nicht zusätzlich ins Textlog geschrieben. Die aktive Quellenverarbeitung funktioniert unverändert.",
    "LOG_SOC": "Zusätzliche SOC-Debugmeldungen entfallen; der Ladezustand wird weiterhin aus der konfigurierten Quelle verarbeitet.",
    "LOG_VALUES": "Zusätzliche rohe Wertemeldungen entfallen. Regelung und erforderliche Messdatenverarbeitung bleiben erhalten.",
    "MQTT_DISCONNECTED_SAFE_STATE": "Eine reine MQTT-Trennung aktiviert nicht durch diesen Schalter einen zusätzlichen sicheren Halt. Andere bestehende Kommunikations-, Geräte- und Command-Schutzprüfungen bleiben verbindlich.",
    "SAFE_STATE_ON_SHELLY_ERROR": "Der besondere Safe-State-Auslöser dieser Einstellung bei Ausfall der aktiven Netzleistungsquelle ist deaktiviert. Andere Frische- und Sicherheitsprüfungen bleiben bestehen; alte Werte dürfen nicht als frisch behandelt werden.",
    "HEADLESS_MODE": "Die gewohnten Status-, Graph- und Settings-Seiten bleiben erreichbar, sofern Webserver und Zugriffsrechte dies zulassen. Die automatische Speicherregelung ist davon unabhängig.",
})


def build_setting_help(row: Mapping[str, Any]) -> SettingHelpSpec:
    key = str(row["key"])
    category = str(row["category"])
    s3_help = S3_USER_GUIDANCE.get(key) or PRIMARY_HELP_VNEXT.get(key)
    short = (FAST_CAPTURE_PLAIN[key]["short"] if key in FAST_CAPTURE_PLAIN else
             s3_help["short"] if s3_help else
             (GENERAL_SHORT_HELP_VNEXT.get(key) or SHORT_HELP.get(key) or f"Konfiguration für {LABEL_OVERRIDES.get(key, row.get('label', key))}."))
    rich = category in RICH_CATEGORIES
    extended = (FAST_CAPTURE_PLAIN[key]["purpose"] if key in FAST_CAPTURE_PLAIN else
                s3_help["purpose"] if s3_help else
                (EXPLICIT_PURPOSE_VNEXT.get(key) or INTERFACE_PURPOSE_VNEXT.get(key) or SYSTEM_PURPOSE_VNEXT.get(key) or RICH_EXTENDED.get(key) or _generic_extended(short, row)))
    when = (FAST_CAPTURE_PLAIN[key]["when"] if key in FAST_CAPTURE_PLAIN else
            s3_help["when"] if s3_help else
            (RICH_WHEN.get(key) or WHEN_V1712.get(key)))
    deps = _dependencies(row)
    dep_help = None
    if deps:
        # Do not repeat one generic category slogan for dozens of unrelated
        # operational settings. Each text must start from the actual consumer
        # of THIS setting; the UI follows it with typed dependency links.
        if key == "HARVEST_FAST_CAPTURE_MODE":
            dep_help = ("Normale Restüberschussregelung, eingeschaltete Primärspeichermessung, "
                        "Schutz gegen unerwünschtes Umladen und die Zendure-Ladeobergrenze "
                        "bestimmen gemeinsam, ob der zusätzliche Anteil überhaupt zulässig ist. "
                        "Die normale AUTO-Schrittbegrenzung wird weder ersetzt noch verändert.")
        elif key == "MAX_POWER_STEP_W":
            dep_help = ("Die Glättung und das Regelintervall bestimmen mit, wie schnell die normale "
                        "Regelung reagiert. Mindeständerungen für MQTT beeinflussen erst den "
                        "Befehlsversand; die zusätzliche Fast-Capture-Rate ist davon getrennt.")
        elif key.startswith("HARVEST_SEASON_"):
            dep_help = ("Die Saisonstrategie wirkt erst nach eigenständiger Aktivierung und nur "
                        "innerhalb geeigneter strategischer High-SOC-Situationen. Restexportaufnahme, "
                        "Tagesprofil und Schutzgrenzen werden nicht ausgeschaltet.")
        elif when:
            dep_help = ("Voraussetzung und Grenze dieser Einstellung: " + when +
                        " Die unten aufgeführten verknüpften Einstellungen steuern "
                        "zusätzliche Freigaben, Grenzen oder Datenquellen.")
        else:
            # Guarded by the operational registry quality gate. For hidden
            # target-only keys we retain the original conservative fallback.
            dep_help = RICH_DEPENDENCY_HELP.get(category) or "Die unten verknüpften Einstellungen müssen ebenfalls berücksichtigt werden."
    risk = RISK_HELP.get(key)
    if rich and not risk:
        risk = RICH_RISK_BY_CATEGORY.get(category)
    if key in VERY_HIGH_EXTRA and not risk:
        risk = "Sehr hohes Änderungsrisiko. Fehlkonfiguration kann Datenquelle, Zugriff, Schutz-/Aktualitätsverhalten oder Dienstverfügbarkeit beeinträchtigen."
    evidence = tuple(filter(None, (
        "SettingsRegistry",
        *(f"settings_validation:{validator}" for validator in tuple(row.get("validator_ids") or ())),
    )))
    return SettingHelpSpec(
        short_help=short,
        extended_help=extended,
        when_help=when,
        help_level="rich" if rich else "base",
        search_terms=_search_terms(row, short),
        handbook_ref=_handbook_ref(category),
        effect_increase=EFFECT_INCREASE.get(key),
        effect_decrease=EFFECT_DECREASE.get(key),
        effect_enable=S3_SETTING_EFFECTS.get(key, {}).get("on") or EFFECT_ENABLE.get(key),
        effect_disable=BOOLEAN_DISABLED_EXPLAINED.get(key) or S3_SETTING_EFFECTS.get(key, {}).get("off") or EFFECT_DISABLE.get(key),
        option_help=S3_OPTION_HELP if key == "HARVEST_SEASON_MODE" else OPTION_HELP.get(key, ()),
        dependencies=deps,
        dependency_help=dep_help,
        override_help=OVERRIDE_HELP.get(key),
        risk_help=risk,
        example=EXAMPLES.get(key),
        formula_text=FORMULAS.get(key),
        guidance_rule_ids=GUIDANCE_RULE_IDS.get(key, ()),
        evidence_refs=evidence,
    )


def build_category_specs() -> Mapping[str, CategorySpec]:
    return MappingProxyType({
        name: CategorySpec(name, CATEGORY_GROUPS[name], CATEGORY_DESCRIPTIONS[name], CATEGORY_HELP_TEXT[name], _handbook_ref(name))
        for name in CATEGORY_GROUPS
    })



# Purpose text is always visible beneath section headings, not hidden inside
# an info icon. Each entry describes the impact and the neighboring control.
SECTION_PURPOSE_VNEXT: Mapping[Tuple[str, str], str] = MappingProxyType({
    ("Betriebsart & manuelle Steuerung", "Betriebsart"): "Hier wählst du, wer über das Laden und Entladen von Zendure entscheidet: die automatische Netzregelung, eine feste Vorgabe oder ein aktiver Halt. Manuelle Vorgaben haben Vorrang vor AUTO; Lade-/SOC-Grenzen und Sicherheitsabschaltungen gelten trotzdem.",
    ("Betriebsart & manuelle Steuerung", "Profil Feste Entladung"): "Nur im Modus „Feste Entladung“: Leistung und Ziel-Ladezustand bestimmen, wie stark und bis wohin Zendure entlädt. Eine separate Folgeoption legt fest, ob ZEC danach in AUTO zurückkehrt oder bei 0 W hält. Der globale Mindest-SOC bleibt verbindlich.",
    ("Betriebsart & manuelle Steuerung", "Profil Feste Ladung"): "Nur im Modus „Feste Ladung“: Ladeleistung und Ziel-Ladezustand bestimmen den festen Ladewunsch. Die Folgeoption legt den anschließenden Betriebsmodus fest; maximale Ladeleistung und oberer SOC-Schutz bleiben übergeordnet.",
    ("Zendure-Geräte", "Batteriekapazität"): "Hier beschreibst du die tatsächlich installierte Batteriekapazität. ZEC benötigt sie für Energieprognosen und Diagnose, nicht um automatisch mehr Leistung oder einen höheren Ladezustand zu erlauben; unbekannte Werte bleiben unbekannt.",
    ("Zendure-Geräte", "Gerätezuordnung"): "Hier legst du fest, welche Zendure-Headunit ZEC über MQTT anspricht. Die Gerätekennung muss zur Installation und zu den MQTT-Topics passen; sie ist keine Freigabe für den gleichzeitigen unabhängigen Betrieb mehrerer Zendure-Controller.",
    ("Leistungsgrenzen & SOC-Schutz", "Leistungsgrenzen"): "Hier setzt du Obergrenzen für Zendure-Ladung und -Entladung. Sie begrenzen die Zielwerte aus AUTO, Nachtbetrieb und manuellen Modi; höhere Grenzen erzwingen keine höhere Geräteleistung und dürfen die reale Hardware nicht überfordern.",
    ("Leistungsgrenzen & SOC-Schutz", "SOC-Schutzfenster"): "Die beiden Ladezustandsgrenzen verhindern Entladung unter den Mindest-SOC und Laden oberhalb des Maximal-SOC. Sie stehen über Strategie-, Nacht- und manuellen Sollwerten; eine Ladefreigabe bei Mindest-SOC bedeutet nicht die Erlaubnis zum weiteren Entladen.",
    ("AUTO-Regelung", "Kommandoauflösung & Stellruhe"): "Kleine Sollwertänderungen können ausgefiltert werden, um unnötige Gerätekommandos zu vermeiden. Das beeinflusst die Häufigkeit von Leistungsbefehlen, nicht die Messung der Netzleistung; größere Schwellen können die Feinregelung verzögern.",
    ("AUTO-Regelung", "Messwert-Glättung"): "Hier bestimmst du, wie stark einzelne Netzleistungsschwankungen in die Regelentscheidung eingehen. Mehr Mittelung beruhigt die Reaktion, kann aber echte Lastsprünge verzögert erkennen; die eigentliche Leistungsänderung wird zusätzlich begrenzt.",
    ("AUTO-Regelung", "Netzziel & Ladefreigabe"): "ZEC versucht den Hausnetzfluss in der Nähe von 0 W zu halten. Diese Einstellungen bestimmen, wann eine gemessene Abweichung toleriert wird und wie viel echter PV-Überschuss für eine zulässige Ladung mindestens verfügbar sein muss.",
    ("AUTO-Regelung", "Reaktionsgeschwindigkeit"): "Hier begrenzt du, wie stark ZEC das Leistungsziel zwischen Regelzyklen verändern darf. Kleine Schritte schonen Gerät und Kommandopfad, reagieren aber langsamer; Schutz- und Gegenflussregeln können unabhängig davon schneller neutralisieren.",
    ("AUTO-Regelung", "Reglerberechnung"): "Reglerverstärkung und Zielwertglättung entscheiden gemeinsam, wie deutlich die Netzabweichung in eine neue Lade- oder Entladeanforderung umgesetzt wird. Erst danach greifen Leistungs-, SOC- und Sicherheitsbegrenzungen.",
    ("AUTO-Regelung", "Zyklus & Ressourcen"): "Dieser Bereich bestimmt den Takt des eigentlichen Controllers, nicht den sekündlichen Statusbildschirm. Kürzere Intervalle steigern Reaktionshäufigkeit und Rechen-/Kommunikationsbedarf; die physische Mess- und Befehlsaktualität hängt zusätzlich von den Quellen ab.",
    ("Nachtbetrieb", "Aktivierung"): "Mit diesem Schalter darf ZEC innerhalb des eingestellten Nachtfensters eine feste Basisentladung ausführen. Das ist keine normale 0-W-Netzregelung und greift nicht bei einem vorrangigen manuellen Modus oder unzulässigen Schutzbedingungen.",
    ("Nachtbetrieb", "Feste Basisentladung"): "Die feste Entladeleistung ist ein Nacht-Sollwert, keine automatische Anpassung an die jeweilige Hauslast. Ist die Hauslast niedriger, kann dadurch Netzexport entstehen; globale Leistungs- und SOC-Grenzen bleiben aktiv.",
    ("Nachtbetrieb", "Reserve & Folgeverhalten"): "Hier legst du fest, wann ZEC die feste Nachtentladung zum Schutz einer Akku-Reserve pausiert und wie nach dem Nachtfenster weitergearbeitet wird. Der globale Mindest-SOC hat weiterhin Vorrang; zulässige Ladung aus echtem PV-Export darf nicht dadurch blindgelegt werden.",
    ("Nachtbetrieb", "Zeitfenster"): "Start- und Enduhrzeit bestimmen, wann eine aktivierte feste Nachtentladung erlaubt sein kann. Ein Zeitfenster darf über Mitternacht reichen. Die Uhrzeiten allein senden keinen Befehl und umgehen keine manuellen oder Batterieschutzregeln.",
    ("Primärspeicher", "Integration & Status"): "Hier schaltest du die Nutzung eines zusätzlichen Primärspeichers in ZEC ein oder aus. Nur bei aktivierter Integration verwendet ZEC dessen Daten für entsprechende Allokations- und Schutzentscheidungen; ohne Verbindung dürfen keine angeblich aktuellen Werte entstehen.",
    ("Primärspeicher", "Integration & Identität"): "Die Identitätsfelder legen fest, welche externe Speicheranlage gemeint ist und wie sie angezeigt wird. Der Anzeigename ist nur Oberfläche, Geräte- oder Quellenkennung muss zur tatsächlichen Anbindung passen.",
    ("Primärspeicher", "Anbindung"): "Wähle genau eine Datenquelle für den Primärspeicher: EVCC, benutzerdefiniertes MQTT oder ein geprüftes lesendes Modbus-Template. Davon hängen die folgenden Verbindungsparameter und die Beurteilung von SOC, Leistung und Datenalter ab; ZEC übernimmt darüber keine eigenständige Schreibsteuerung des Primärspeichers.",
    ("Primärspeicher", "Gerät & Verbindung · Modbus"): "Bei Modbus-Anbindung bestimmen Adresse, Port, Geräte-ID und Template, welche Werte ZEC direkt lesen darf. Die Daten dienen der Diagnose und freigegebenen Allokationslogik; fehlerhafte Verbindung darf keine erfundenen Leistungs- oder SOC-Werte erzeugen.",
    ("Primärspeicher", "MQTT-Datenquelle · Benutzerdefiniert"): "Wenn der Primärspeicher über eigene MQTT-Topics eingebunden wird, werden hier Topics und Transportparameter zugeordnet. Sie sind nur für diese gewählte Anbindungsart relevant; falsche Zuordnung kann zu unbrauchbaren oder veralteten Speicherwerten führen.",
    ("Primärspeicher", "MQTT-Datenquelle · EVCC Standard"): "Für EVCC legt dieser Abschnitt fest, wie die vorhandenen Speicherdaten empfangen werden. Er ist nicht mit direkter Modbus-Anbindung zu kombinieren; EVCC bleibt die Datenquelle und ZEC bewertet Aktualität sowie Vorzeichen getrennt.",
    ("Primärspeicher", "MQTT-Payload · Benutzerdefiniert"): "Bei eigener MQTT-Anbindung beschreibt dieser Abschnitt die Feldnamen und Struktur der empfangenen Payload. Damit ZEC aus den Daten richtige Lade-/Entladeleistung und SOC ableiten kann, müssen die Angaben zur realen Quelle passen.",
    ("Primärspeicher", "Normalisierung"): "Hier wird die Bedeutung von Leistung, Vorzeichen und Einheiten aus der gewählten Quelle auf das ZEC-Speichermodell abgebildet. Ein falsches Vorzeichen könnte Laden und Entladen vertauschen; unabhängige Sicherheitsprüfungen bleiben notwendig.",
    ("Primärspeicher", "Freshness & Verfügbarkeit"): "Diese Grenzen bestimmen, wie lange empfangene Werte als aktuell betrachtet werden dürfen. Veraltete Speicherwerte dürfen keine neuen physischen Lade-/Entladeentscheidungen legitimieren; die UI soll Quelle und Datenalter ehrlich zeigen.",
    ("Primärspeicher", "Technische Leistungsdaten"): "Nennkapazität und maximale Lade-/Entladeleistung beschreiben die tatsächliche Primärspeicheranlage. Verlässliche Werte verbessern Grenzen, Darstellung und Beurteilung des Lade-Headrooms; unbekannte Gerätedaten dürfen nicht durch frei erfundene Defaults ersetzt werden.",
    ("Harvest / Restüberschuss", "Entry & Hysterese"): "Hier bestimmst du, wie lange der Eintritt in High-SOC-Harvest bestätigt sein muss und wie kurze Unterbrechungen abgefangen werden. Damit vermeidet ZEC ständiges Ein-/Ausschalten; die Schwellen des Primärspeichers und aktuelle Überschussmessung bleiben zusätzlich maßgeblich.",
    ("Harvest / Restüberschuss", "High-SOC & Vollspeicher"): "ZEC kann bei hohem oder vollem Primärspeicher-SOC zusätzliche Zendure-Ladung ermöglichen. Unterschiedliche Ein- und Ausschaltschwellen verhindern ständiges Umschalten; Mindestüberschuss und voller Speicherzustand entscheiden zusätzlich, wann ZEC eingreifen darf; aktuell vermeidbarer Export und Schutzgrenzen bleiben vorrangig.",
    ("Harvest / Restüberschuss", "Fast Capture"): "Fast Capture ergänzt die normale Ladeautomatik bei echtem Solarüberschuss. Ist der Primärspeicher voll und lädt kaum noch oder erreicht fast seine Ladeleistungsgrenze, kann ZEC dadurch eine zusätzliche Zendure-Ladeanforderung schneller aufbauen. Die Funktion ändert weder die normale Entladesteuerung noch die Speicherpriorität. Ob sie nur beobachtet oder auch Ladung anfordert, bestimmst du in der einzelnen Einstellung; sämtliche Leistungs- und Schutzgrenzen bleiben verbindlich.",
    ("Harvest / Restüberschuss", "Master & Zielbild"): "Hier aktivierst du die vorhandenen Restüberschuss-Harvest-Pfade. Sie dürfen überschüssige Solarenergie nutzen, während ZEC weiterhin das Hausnetzziel, die Primärspeicherpriorität und alle SOC-/Cross-Charge-Schutzbedingungen beachtet.",
    ("Harvest / Restüberschuss", "Near-Limit-Entry"): "Diese Werte erkennen, ob der Primärspeicher in die Nähe seiner aktuellen Ladeannahmegrenze kommt und zugleich echter Export vorliegt. Erst ausreichend bestätigte Bedingungen können den zusätzlichen Restüberschusspfad freigeben; es wird kein fester Exportwert angestrebt.",
    ("Harvest / Restüberschuss", "Primärspeicher-Schwellen"): "Minimum, Wiederanlauf und Near-Limit werden aus verlässlicher maximaler Primärspeicher-Ladeleistung abgeleitet. Absolute positive Wattvorgaben ersetzen ihren jeweiligen Prozent-/Ratio-Wert; die Reihenfolge der Schwellen muss erhalten bleiben.",
    ("Harvest / Restüberschuss", "Saisonale Strategie"): "Hier legst du fest, ob die zusätzliche strategische Aufteilung bei hohem Primärspeicher-SOC abhängig von einer gewählten Saisonpolicy erfolgen darf. Aktivieren und Modusauswahl sind getrennt. Ohne Aktivierung bleibt die bisherige Ladeverteilung erhalten; echte Restüberschussaufnahme kann unabhängig davon weiterlaufen.",
    ("Harvest / Restüberschuss", "Tagesprofile"): "Die Tagesprofile passen die zusätzliche Ladeverteilung an den Tagesverlauf an: Zuerst bestimmt der eigene Tagesprofil-Schalter, ob ZEC zwischen Morgen, Mittag und Nachmittag unterscheiden darf. Die Uhrzeiten legen die zeitlichen Abschnitte fest; die Bestätigungszeiten verhindern einen vorschnellen Wechsel aufgrund kurzer Ladezustandsschwankungen. Die Profilanteile beeinflussen nur eine bereits zulässige strategische Verteilung, nicht die verfügbaren Watt am Gerät. Ist das Tagesprofil deaktiviert, bleibt die normale bisherige Strategie erhalten. Die separate Saisonstrategie wird dadurch weder aktiviert noch umgangen; echter Restüberschuss und alle Schutzgrenzen bleiben vorrangig.",
    ("Harvest / Restüberschuss", "Tageszeitprofil"): "Hier bestimmst du den gewünschten Anteil der strategisch verteilten Ladeleistung für den Primärspeicher in Morgen-, Mittags- und Nachmittagsfenster. Die Werte wirken nur im entsprechend aktivierten und anwendbaren High-SOC-Profil, nicht als absolute Ladeleistung oder unabhängig von Schutzlimits.",
    ("Cross-Charge-Schutz", "Aktivierung"): "Der Cross-Charge-Schutz erkennt Situationen, in denen ein Speicher unerwünscht den anderen beladen könnte. Bei aktivem Schutz werden widersprüchliche Zendure-Ziele begrenzt; frische und eindeutig interpretierbare Primärspeicherdaten bleiben nötig.",
    ("Cross-Charge-Schutz", "Fallback bei fehlenden Daten"): "Sind Primärspeicherwerte veraltet oder fehlen, muss ZEC konservativ entscheiden, statt fiktiv freie Ladeleistung anzunehmen. Hier bestimmst du, ob neue Ladung bis zu frischen Informationen gesperrt werden soll.",
    ("Cross-Charge-Schutz", "Schaltschwelle & Hysterese"): "Hier legst du fest, ab welcher gegenläufigen Leistung der Schutz eingreift und wann er wieder freigeben darf. Unterschiedliche Schwellen für das Einschalten und die Freigabe vermeiden ständiges Hin- und Herschalten bei schwankenden Messwerten. Der Schutz darf selbst keine umgekehrte Leistungsrichtung anfordern.",
    ("Kommandowirkung & Resync", "0-W-Neutralisierung"): "Fordert ZEC 0 W an, soll die Zendure weder laden noch entladen. Hier legst du fest, wie lange ZEC auf die tatsächliche Reaktion des Geräts wartet und wann Betriebsart und Leistungsgrenzen erneut abgeglichen werden müssen.",
    ("Kommandowirkung & Resync", "Command-State & Flash-Schutz"): "Bevor ZEC Gerätekommandos als bestätigt ansieht, müssen Betriebsart und Lade-/Entladegrenzen konsistent und aktuell rückgelesen sein. Hier stellst du Aktualitäts- und Wiederholgrenzen ein, um unbestätigte Zustände und unnötige Geräteschreibzugriffe zu vermeiden.",
    ("Kommandowirkung & Resync", "MQTT-Recovery"): "Nach Unterbrechung oder veralteter MQTT-Rückmeldung benötigt ZEC wieder belastbare Geräte- und Command-Daten. Diese Parameter steuern die konservative Rückkehr, nicht die normale Geschwindigkeit der Netzregelung.",
    ("Kommandowirkung & Resync", "Notfall-/Legacy-Verhalten"): "Dieser Abschnitt enthält besondere Wiederherstellungsoptionen für Störungen und ältere Kompatibilitätsfälle. Eine Aktivierung kann nach einem Verbindungsabbruch einen erneuten Abgleich der Gerätebetriebsart und Leistungsgrenzen auslösen. ZEC muss anschließend weiterhin prüfen, ob das Gerät die angeforderte Leistung tatsächlich umsetzt.",
    ("Kommandowirkung & Resync", "Recovery nach bestätigtem Mismatch"): "Wenn ZEC wiederholt eine Abweichung zwischen angeforderter und beobachteter Leistung bestätigt, kann ein begrenzter vollständiger Wiederabgleich nötig sein. Diese Zeiten bestimmen, wann das überhaupt erlaubt wird; ein einzelnes MQTT-Publish beweist keine Wirkung.",
    ("Kommandowirkung & Resync", "Recovery-Drosselung"): "Die Cooldownzeiten verhindern, dass wiederholte fehlgeschlagene Kommandos zu einer Schreibschleife werden. Kürzere Zeiten können bei echten Störungen schneller reagieren, aber die Headunit unnötig oft belasten.",
    ("Kommandowirkung & Resync", "Sollwerttracking"): "Die tatsächlich gemeldete Zendure-Leistung darf abhängig von Watt- und Prozenttoleranzen vom Zielwert abweichen, ohne sofort als Fehler zu gelten. ZEC verwendet die jeweils größere zulässige Toleranz; Richtungsreaktion allein ist noch kein korrektes Tracking.",
    ("Kommandowirkung & Resync", "Wirkungsbewertung"): "Hier bestimmst du, wie groß eine Messung sein muss und wie lange eine Reaktion dauern darf, bevor ZEC einen Befehl als wirksam, verzögert oder nicht bewertbar einstuft. Diagnose und physische Schutzentscheidung bleiben getrennte Ebenen.",
    ("Messdaten & Speicherung", "CSV-Messdaten & Rotation"): "Hier bestimmst du Umfang, Dateigröße und Wechsel der langfristig geschriebenen Messdaten. Diese Aufzeichnung dient Diagnose und späterer Analyse; sie darf die laufende Regelung nicht ausbremsen.",
    ("Messdaten & Speicherung", "Fallback"): "Wenn der bevorzugte Datenträger ausfällt oder voll ist, entscheidet ZEC nach dem definierten Speicher-Fallback und Warnvertrag über weiteres Logging. Fehlende Aufzeichnungen dürfen nicht als vorhandene Messwerte erscheinen; der Regler bleibt unabhängig.",
    ("Messdaten & Speicherung", "Measurement-V4"): "Hier legst du fest, ob und mit welchem Detailumfang ZEC die Regler- und Messdaten zur späteren Analyse protokolliert. Mehr Daten erhöhen den Speicherbedarf, ändern aber nicht automatisch die Lade-/Entladestrategie.",
    ("Messdaten & Speicherung", "SQLite-Graphstore"): "Der Graphstore stellt längerfristige Messwerte für Diagramme bereit. Hier wird sein Speicherverhalten eingestellt; eine Graphdarstellung ist keine eigenständige Regelentscheidung und fehlende Daten dürfen nicht interpoliert vorgetäuscht werden.",
    ("Messdaten & Speicherung", "Schreibstrategie"): "Pufferung und Schreibintervalle begrenzen Datenträgerlast und wirken auf die Verzögerung der Datenpersistenz. Änderungen daran steuern keine Batteriekommandos; ein sicherer Flush-/Fallbackvertrag bleibt notwendig.",
    ("Messdaten & Speicherung", "Speicherschutz"): "Die Mindestfreiplatzgrenzen schützen SD-Karte oder externen Datenträger vor volllaufenden Messdateien. Bei zu wenig Platz muss ZEC Aufzeichnungen begrenzen, nicht die Sicherheitslogik oder physische Regelung blockieren.",
    ("Messdaten & Speicherung", "Speicherziel"): "Hier wählst du, wohin Messdaten geschrieben werden: SD-Karte, externes Laufwerk oder eigener Pfad. Die tatsächliche Verfügbarkeit wird geprüft; diese Entscheidung verändert keine Ladekriterien oder SOC-Grenzen.",
    ("Messdaten & Speicherung", "Tageskurve & RAM-Historie"): "Diese Einstellungen steuern, wie viele Punkte und welche Zeitbereiche die schnellen Status- und SOC-Kurven im Arbeitsspeicher vorhalten. Sie verändern Anzeige und Speicherverbrauch, nicht den Netzregelungsalgorithmus.",
    ("Messdaten & Speicherung", "V4-Manifest & I/O"): "Das V4-Manifest dokumentiert aufgezeichnete Messdateien. Seltenere Schreibvorgänge schonen den Datenträger, können aber die Aktualität der Metadaten bis zum nächsten Flush verzögern; Datenintegrität und Abschlussprüfung bleiben Pflicht.",
    ("Schnittstellen & Datenquellen", "MQTT-Diagnose"): "Dieser Bereich aktiviert bei Bedarf eine zusätzliche Sicht auf empfangene MQTT-Nachrichten. Breite Topic-Filter können die Last erhöhen oder sensible Nutzdaten zeigen; das Diagnose-Abo ist kein zusätzlicher Regler oder Batteriekommandopfad.",
    ("Schnittstellen & Datenquellen", "MQTT-Verbindung"): "Brokeradresse, Port und Zugangsdaten verbinden ZEC mit der Zendure-Telemetrie und dem Gerätekommandopfad. Falsche Angaben können frische SOC-/Leistungsdaten und die sichere Befehlsausführung verhindern; ein lokaler Mosquitto-Dienst ist nicht zwingend.",
    ("Schnittstellen & Datenquellen", "Netzleistung · Plausibilität"): "Hier bestimmst du, ab welchen unrealistischen Leistungsgrößen eine Netz-Messung verworfen wird. Das schützt die AUTO-Regelung vor defekten Rohwerten; ein Plausibilitätsfilter ersetzt weder die richtige Quellenzuordnung noch eine robuste Protokollauswertung.",
    ("Schnittstellen & Datenquellen", "Netzleistung · SMA Diagnose"): "Die SMA-Diagnose protokolliert Empfangslücken und Paket-/Socketzustände der lokalen Speedwire-Daten. Sie hilft bei der Ursachenanalyse, ist aber kein Schalter für eine neue Reglermessquelle oder eine zusätzliche Batterieansteuerung.",
    ("Schnittstellen & Datenquellen", "Netzleistung · SMA Direkt"): "Die direkte SMA-Netzleistungsquelle liest passende Energy-Meter-/Sunny-Home-Manager-Datagramme. Multicast, Netzwerkschnittstelle und Geräte-Seriennummer müssen zur Anlage passen; bei mehreren SMA-Geräten ist die richtige Zähleridentität sicherheitsrelevant.",
    ("Schnittstellen & Datenquellen", "Netzleistung · Shelly-kompatibel"): "Bei Shelly-kompatibler HTTP-Messung benötigt ZEC die richtige Adresse und eine verlässliche Aktualitätsgrenze. Dieser Pfad ist eine Alternative zur direkten SMA-Quelle, kein zusätzlicher Regler; alte Werte dürfen die AUTO-Regelung nicht unbemerkt weiterführen.",
    ("Schnittstellen & Datenquellen", "Netzleistung · aktive Quelle"): "Hier wählst du, welcher Zählerwert den tatsächlichen Hausnetzbezug oder die Einspeisung für die Regelung liefert. Die gewählte Quelle entscheidet über Aktualität, Vorzeichen und Fehlerschutz; ein passiver zweiter Empfänger dient nur der Diagnose.",
    ("Schnittstellen & Datenquellen", "Zendure Local API"): "Die lokale Zendure-API kann Gerätedaten für Diagnose oder als getrennt aktivierten Telemetrie-Fallback liefern. Sie ersetzt nicht automatisch MQTT-Kommandos; Vorrang und Nutzung bei stale MQTT-Werten werden separat eingestellt.",
    ("Schnittstellen & Datenquellen", "Zendure Local API · Timeouts"): "Mindestabstand, Timeout und Fehlerpause begrenzen lokale API-Abfragen, damit Gerät und Controller nicht durch zu häufige Wiederholungen belastet werden. Der API-Worker läuft unabhängig vom normalen Reglerzyklus.",
    ("System & Diagnose", "Administrative Aktionen"): "Dienstneustart und Reparatur des Last-Good-Zeigers sind eigenständige geschützte Aktionen, keine normale Änderung eines Einstellungswerts. Sie können die aktuelle Dienstverfügbarkeit beeinflussen und verlangen ausdrückliche Bestätigung.",
    ("System & Diagnose", "Analyse-/Replay-Service"): "Diese Limits begrenzen, wie viele Dateien und Messdaten eine lokale Untersuchung laden darf. Sie schützen gerade schwächere Raspberry Pis vor Speichermangel; Analysen dürfen keine Reglerkommandos senden oder Messdaten als simulierte Realität ausgeben.",
    ("System & Diagnose", "Darstellung"): "Hier stellst du ein, welche Informationen die Weboberfläche zeigt und wie sie dargestellt werden. Anzeigeoptionen verändern normalerweise weder das tatsächliche Batteriekommando noch die Werte der Regelung; technische Daten müssen dennoch korrekt als aktuell oder veraltet erkennbar bleiben.",
    ("System & Diagnose", "Laufzeitdiagnose"): "Die Diagnostik macht Ausführungszeiten, Fehler und Datenalter nachvollziehbar. Solche Anzeigen helfen bei der Fehlersuche, dürfen den Controller aber nicht mit zusätzlichen synchronen Netzabfragen oder Schreibbefehlen belasten.",
    ("System & Diagnose", "Runtime-Logging"): "Datei-Logging zeichnet interne Zustands- und Fehlermeldungen auf, damit sich Störungen später untersuchen lassen. Verzeichnis, Dateigröße und Rotation betreffen den Datenträger, nicht die freigegebene Lade-/Entladeleistung.",
    ("System & Diagnose", "Runtime-Logging · Detailkanäle"): "Einzelne Zusatzkanäle erhöhen die Tiefe der Protokollierung, benötigen aber auch CPU-/Speicher-/Schreibbudget. Aktivieren nur für eine konkrete Fragestellung; das Logging ist kein Ersatz für tatsächliche Sensor- oder Command-Evidenz.",
    ("System & Diagnose", "Safe-State & Datenqualität"): "Hier wird festgelegt, wann ZEC bei fehlenden Netz-/MQTT-/SOC-Daten konservativ auf sichere Werte zurückfällt oder Warnungen meldet. Fehlende aktuelle Daten dürfen nicht wie frische Steuerungsgrundlagen behandelt werden; SOC- und Hardwaregrenzen bleiben übergeordnet.",
    ("System & Diagnose", "Webserver & Zugriff"): "Port, Dienstzugriff und Headless-Darstellung bestimmen, wie du ZEC erreichst. Fehlerhafte Einstellungen können die Weboberfläche unzugänglich machen, ohne dass damit die Reglerfunktion bewusst verändert werden soll.",
    ("System & Diagnose", "Zendure MQTT-Datenqualität"): "Hier stellst du ein, nach welcher Wartezeit fehlende oder veraltete Zendure-MQTT-Daten als Problem erkennbar werden. Ein Broker-Reconnect ist noch kein Beleg für aktuelle Akkudaten; der Zustand muss im Status und in Schutzentscheidungen konsistent bleiben.",
})

PRIMARY_HELP_VNEXT: Mapping[str, Mapping[str, str]] = MappingProxyType({
    "SECOND_BATTERY_INTEGRATION_ENABLED": {
        "short":"Erlaubt ZEC, einen zusätzlichen Primärspeicher bei der Ladeverteilung und beim Schutz vor gegenseitigem Laden zu berücksichtigen. Aus: ZEC arbeitet ohne diese Speicherintegration; andere Quellenwerte dürfen nicht einfach als aktueller Primärspeicher gelten.",
        "purpose":"Dieser Schalter schaltet die ZEC-Integration des Primärspeichers ein, nicht dessen physische Stromversorgung. Erst mit aktivierter Integration und einer gültigen, frischen Datenquelle können entsprechende Harvest- und Cross-Charge-Entscheidungen auf diesen Speicher Bezug nehmen. Die Anbindungsart (EVCC/MQTT/Modbus) und die Leistungsdaten werden separat festgelegt; die Anbindung ist nicht automatisch ein schreibender Primärspeicher-Regler.",
        "when":"Die Integration beeinflusst nur entsprechende Strategie- und Schutzpfade, wenn eine passende Datenquelle vorhanden und aktuell ist. Ist sie deaktiviert oder stale, darf ZEC keine verlässliche Primärspeicherleistung vortäuschen.",
    },
    "SECOND_BATTERY_CAPACITY_WH": {
        "short":"Trägt die tatsächliche Kapazität des Primärspeichers für die Anzeige und die Berechnung seiner verbleibenden Energiemenge ein, wenn keine belastbare Gerätedatenquelle dafür existiert. Der Wert ist kein neuer Ladebefehl und darf nicht geraten werden.",
        "purpose":"Diese Angabe beschreibt die Speichergröße der realen Anlage; sie dient dem kWh-Status und verwandten Diagnosen. Eine im Gerät ausgelesene verlässliche Kapazität hat Vorrang, danach folgt ein vorhandener manueller Fallback. Die Einstellungen zu maximaler Lade- und Entladeleistung sind getrennt und legen andere Grenzen fest.",
        "when":"Nur bei aktivierter Primärspeicher-Integration und wenn ZEC für die betreffende Anzeige keine vorrangigen belastbaren Kapazitätsdaten hat. Es entsteht dadurch keine automatische SOC- oder strategische Kapazitätsgewichtung.",
    },
    "SECOND_BATTERY_MAX_DISCHARGE_POWER_W": {
        "short":"Gibt die maximale reale Entladeleistung des Primärspeichers für Statusbalken und technische Einordnung an, falls die gewählte Quelle diesen Wert nicht selbst liefert. Sie ist kein Befehl, den Primärspeicher mit dieser Leistung zu entladen.",
        "purpose":"ZEC benötigt eine belastbare Leistungsreferenz, um den aktuellen Primärspeicherfluss verständlich anzuzeigen. Diese technische Angabe darf nicht mit Zendures globaler maximaler Entladeleistung verwechselt werden; die Primärspeicher-Datenquelle und tatsächliche Istleistung haben jeweils eigene Aufgaben.",
        "when":"Nur bei aktivierter Primärspeicher-Integration und fehlender vorrangiger verlässlicher Geräteangabe. Es werden keine neuen Modbus-Schreibkommandos oder Entladestrategien freigegeben.",
    },
})

def build_section_specs(category_sections: Sequence[Tuple[str, str]]) -> Mapping[Tuple[str, str], SectionSpec]:
    out: Dict[Tuple[str, str], SectionSpec] = {}
    overrides = {
        ("Betriebsart & manuelle Steuerung", "Betriebsart"): "Wählt die aktive Steuerungspriorität. Schutzbedingungen bleiben über jedem manuellen oder automatischen Modus.",
        ("Nachtbetrieb", "Zeitfenster"): "Start und Ende bilden ein logisches HH:MM-Zeitfenster; ein Verlauf über Mitternacht ist zulässig.",
        ("Harvest / Restüberschuss", "Fast Capture"): "Dieser Bereich beschreibt eine Ergänzung der normalen Ladeautomatik zur schnelleren Nutzung eines bereits gemessenen Solarüberschusses. ZEC prüft dafür den Ladezustand und die aktuelle Ladeleistung des Primärspeichers sowie die verfügbare Zendure-Ladeleistung. Ohne geeignete Bedingungen bleibt die normale Ladeautomatik allein zuständig. Die Betriebsart der Zusatzfunktion wird in der darunterstehenden Einstellung ausgewählt.",
        ("Harvest / Restüberschuss", "Primärspeicher-Schwellen"): "Floor <= Restart <= Near-Limit <= Pmax. Positive absolute W-Overrides ersetzen jeweils den zugehörigen Ratio-Wert.",
        ("Harvest / Restüberschuss", "High-SOC & Vollspeicher"): "High-SOC Enter/Exit bilden eine Hysterese; Full-SOC grenzt den Voll-/Idle-Zweig ab. Exportwerte sind Eintrittsschwellen, keine Restexportziele.",
        ("Harvest / Restüberschuss", "Saisonale Strategie"): "Diese Gruppe ordnet die zusätzliche strategische Ladeverteilung dem Jahresverlauf zu. Die Saisonstrategie wirkt nur nach ausdrücklichem Einschalten und nur in geeigneten Situationen mit hohem Ladezustand des Primärspeichers. Ohne Aktivierung bleibt die bisherige Verteilung unverändert. Tagesprofile werden unabhängig aktiviert. Gemessenen echten Solarüberschuss darf ZEC weiterhin nutzen; SOC-, Geräte- und Gegenflussschutz haben immer Vorrang.",
        ("Harvest / Restüberschuss", "Tagesprofile"): "Mit den Tagesprofilen kann ZEC die zusätzliche strategische Ladeverteilung an verschiedene Tagesabschnitte anpassen. Der eigene Aktivierungsschalter entscheidet zuerst, ob die Tagesprofile überhaupt genutzt werden. Die Uhrzeiten begrenzen Morgen, Mittag und Nachmittag; separate Bestätigungszeiten verhindern häufige Wechsel durch kurze Ladezustandsschwankungen. Die Profilwerte beeinflussen erst danach, wie eine grundsätzlich zulässige zusätzliche Ladung verteilt wird. Bei ausgeschalteten Tagesprofilen läuft die normale Strategie weiter; die getrennt aktivierbare Saisonstrategie wird dadurch nicht ein- oder ausgeschaltet. Echten Solarüberschuss darf ZEC weiterhin unter allen Schutzgrenzen nutzen.",
        ("Harvest / Restüberschuss", "Tageszeitprofil"): "Die Profilanteile verändern die Strategieallokation zwischen Primärspeicher und Zendure. Sie sind keine direkten Zendure-Sollwerte.",
        ("AUTO-Regelung", "Reglerberechnung"): "Gain erzeugt die Rohkorrektur, Smoothing glättet das Ziel danach. Weitere Limiter wirken anschließend.",
        ("AUTO-Regelung", "Reaktionsgeschwindigkeit"): "Step und Guard-Ramp begrenzen unterschiedliche Änderungspfade; höhere Werte bedeuten nicht automatisch bessere Regelqualität.",
        ("Cross-Charge-Schutz", "Schaltschwelle & Hysterese"): "Die Einschaltgrenze legt fest, ab welchem unerwünschten Stromfluss zwischen den Speichern ZEC eingreift. Eine niedrigere Ausschaltgrenze verhindert, dass die Schutzfunktion bei kleinen Messschwankungen ständig an- und ausgeht. Bei ausgeschaltetem Cross-Charge-Schutz findet dieser zusätzliche Eingriff nicht statt; die übrigen SOC- und Gerätegrenzen gelten weiterhin.",
        ("Kommandowirkung & Resync", "Sollwerttracking"): "Diese Einstellungen legen fest, wie stark die gemessene Lade- oder Entladeleistung vom angeforderten Wert abweichen darf, bevor ZEC eine unzureichende Befehlswirkung meldet. Dass ein Speicher in die richtige Richtung arbeitet, genügt noch nicht: Er muss der gewünschten Leistung auch ausreichend folgen.",
        ("Kommandowirkung & Resync", "Wirkungsbewertung"): "Diagnosegrenze, Mindest-Istleistung und Timeout bestimmen unterschiedliche Qualitätsstufen der Kommandowirkung.",
        ("Schnittstellen & Datenquellen", "MQTT-Verbindung"): "Broker, Port und optionale Authentifizierung bilden den zentralen Command-/Telemetriepfad. Installationswerte werden nicht als Produktdefaults empfohlen.",
        ("Schnittstellen & Datenquellen", "Netzleistung · aktive Quelle"): "Die aktive Netzleistungsquelle ist eine Anlagenentscheidung. Quellspezifische Pflichtdaten müssen vollständig sein, bevor sie produktiv genutzt wird.",
        ("Messdaten & Speicherung", "Measurement-V4"): "Measurement V4 ist der produktive Vertrag. Logging kann aus sein oder standard/extended schreiben; es bleibt nachgelagert zum Regelzyklus.",
        ("System & Diagnose", "Administrative Aktionen"): "Neustart und Last-Good-Pointer-Reparatur sind explizite geschützte Aktionen und keine normalen Settings-Commits.",
    }
    for category, section in category_sections:
        text = SECTION_PURPOSE_VNEXT.get((category, section)) or overrides.get((category, section))
        if text is None:
            raise ValueError(f"Missing user-facing section-purpose: {category} / {section}")
        out[(category, section)] = SectionSpec(category, section, text, _handbook_ref(category))
    return MappingProxyType(out)
