# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# V12.12.1 registry-native help/guidance metadata.  This module is deliberately
# static: opening help never performs I/O, network access or controller work.

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


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
    "Zendure-Geräte": "Zendure-Gerät und anlagenbezogene Geräteparameter.",
    "Schnittstellen & Datenquellen": "MQTT, Netzleistungsquelle und externe Datenpfade.",
    "Messdaten & Speicherung": "Measurement V4, SQLite-Graphstore und Speicherschutz.",
    "System & Diagnose": "Webserver, Darstellung, Logging, Analyse und Sicherheitsfallbacks.",
}

CATEGORY_HELP_TEXT = {
    "Betriebsart & manuelle Steuerung": "AUTO nutzt die normale Netzleistungsregelung. STOP/HOLD und feste manuelle Modi haben Vorrang vor AUTO; ein manueller Modus ungleich AUTO verhindert den Nachtmodus im betreffenden Zyklus. Feste Lade- und Entlademodi arbeiten mit festen Leistungszielen bis zum Ziel-SOC. Safe-State sowie harte SOC- und Gerätegrenzen behalten immer Vorrang.",
    "Leistungsgrenzen & SOC-Schutz": "Lade-/Entladegrenzen sowie MIN/MAX-SOC sind anlagen- und geräteabhängige Schutzwerte. Sie begrenzen auch manuelle, Nacht- und AUTO-Ziele. Diese Werte sind keine universellen Empfehlungen und müssen zur konkreten Hardware passen.",
    "AUTO-Regelung": "Die Netzabweichung wird über Mittelwert, Totzone, Gain, Smoothing und Step kontrolliert nachgeführt. MIN_COMMAND_CHANGE_W beeinflusst die Publish-Auflösung, nicht die interne Sollwertrechnung. Mehr Reaktionsgeschwindigkeit ist nicht automatisch bessere Regelung.",
    "Nachtbetrieb": "Der Nachtmodus erzeugt eine feste Basisentladung und ist keine netzleistungsnachgeführte AUTO-Entladung. Start und Ende dürfen über Mitternacht laufen. Eine optionale Nachtreserve pausiert die feste Basisentladung; globale MIN-SOC-Grenzen und aktive 0-W-Neutralisierung beim Exit bleiben Schutzinvarianten.",
    "Primärspeicher & SMA": "Die Datenquelle des Primärspeichers liefert Leistung, SOC und optional Kapazität für Cross-Charge und Harvest. Vorzeichen- und Einheitsnormalisierung sind sicherheitsrelevant. EVCC-Standardprofil und benutzerdefinierte Topics sind getrennte Quellpfade.",
    "Harvest / Restüberschuss": "Der Primärspeicher hat grundsätzlich Vorrang. Harvest nutzt nur Restüberschuss oder ausdrücklich spezifizierte Parallel-Harvest-Leistung. Floor, Restart und Near-Limit sind geordnete Schwellen; positive W-Overrides ersetzen den jeweiligen Ratio-Wert. Restexport ist nicht automatisch ein absoluter Zendure-Sollwert.",
    "Cross-Charge-Schutz": "Cross-Charge wird symmetrisch behandelt. Gegenläufiger Zendure-Sollwert wird proportional reduziert, aber der Schutz kehrt die Richtung nicht selbstständig um. Frische Zweitbatteriedaten sind erforderlich; Sollwertkonflikt und tatsächlich beobachteter Gegenfluss bleiben getrennte Sachverhalte.",
    "Kommandowirkung & Resync": "Ein MQTT-Publish ist kein Wirkungsnachweis. Diagnose trennt Publish, Richtungsreaktion, Sollwerttracking und Systemziel. 0-W-Neutralisierung ist ein aktives Kommando. Resync-Parameter steuern Recovery bei bestätigter Nichtwirkung und sind keine normale Reglerdynamik.",
    "Zendure-Geräte": "Geräte-ID und Batteriekapazität sind installationsabhängig. Unbekannte Hardwarewerte werden nicht erfunden; Kapazität dient vor allem Prognose und Diagnose.",
    "Schnittstellen & Datenquellen": "MQTT ist Command-/Telemetriepfad. Die Netzleistungsquelle ist eine bewusste Anlagenentscheidung. SMA-Direktquelle und Shelly-kompatibler HTTP-Pfad besitzen unterschiedliche Voraussetzungen. Die lokale Zendure-API kann ergänzend oder als Fallback arbeiten.",
    "Messdaten & Speicherung": "Measurement V4 ist die produktive Messdatengrundlage. Logging ist nachgelagert und darf die Regelung nicht blockieren. off, standard und extended unterscheiden Umfang und Speichervolumen; Fallback- und Storagezustände müssen sichtbar bleiben.",
    "System & Diagnose": "Diagnose- und Loggingparameter verändern nicht automatisch die physische Regelfunktion. Administrative Aktionen sind keine normalen Settings-Änderungen und bleiben explizit geschützt.",
}

# Page numbers are build-verified against the V12.12.1 generic manual.
HANDBOOK_GLOSSARY = HandbookRef("glossary", "Begriffe und Abkürzungen", 15)
HANDBOOK_SECTIONS = {
    "Betriebsart & manuelle Steuerung": ("manual-modes", "Betriebsarten und manuelle Steuerung", 4),
    "Leistungsgrenzen & SOC-Schutz": ("limits-soc", "Leistungsgrenzen und SOC-Schutz", 5),
    "AUTO-Regelung": ("auto-control", "AUTO-Regelung", 6),
    "Nachtbetrieb": ("night", "Nachtbetrieb", 7),
    "Primärspeicher & SMA": ("primary-storage", "Primärspeicher und SMA", 8),
    "Harvest / Restüberschuss": ("harvest", "Harvest / Restüberschuss", 9),
    "Cross-Charge-Schutz": ("cross-charge", "Cross-Charge-Schutz", 10),
    "Kommandowirkung & Resync": ("command-effect", "Kommandowirkung und Resync", 11),
    "Zendure-Geräte": ("interfaces", "Geräte und Schnittstellen", 12),
    "Schnittstellen & Datenquellen": ("interfaces", "Geräte und Schnittstellen", 12),
    "Messdaten & Speicherung": ("measurement-v4", "Measurement V4 und Speicherung", 13),
    "System & Diagnose": ("system-diagnostics", "System und Diagnose", 14),
}

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
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
    "REST_SURPLUS_MIN_EXPORT_W": {"key": "REST_SURPLUS_HARVEST_ENABLED", "equals": True},
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
    'SECOND_BATTERY_STALE_TIMEOUT_SECONDS': 'Nach dieser Zeit ohne Update auf einem konfigurierten Zusatzbatterie-MQTT-Topic gelten die Daten als veraltet. Je kleiner der Wert, desto schneller reagiert der Schutz auf fehlende Daten; je größer der Wert, desto toleranter ist das System gegenüber kurzen MQTT-Aussetzern.',
    'SECOND_BATTERY_DISPLAY_NAME': 'Freier Anzeigename der externen Batterie auf Statusseite, Graph und CSV-Beschreibungen, z. B. SMA Sunny Island, Victron ESS oder Hausspeicher Keller.',
    'SECOND_BATTERY_SOURCE_PROFILE': 'EVCC Standard ist eine Komfort-Vorlage: aus dem Basis-Topic werden /power, /soc und /capacity gebildet. Benutzerdefiniert erlaubt vollständig frei angegebene Einzel-Topics und optionale JSON-Feldpfade.',
    'SECOND_BATTERY_CAPACITY_TOPIC': 'Optionales MQTT-Topic für die Zusatzbatterie-Kapazität. Die Kapazität dient Anzeige und Diagnose, ist aber nicht zwingend für die Schutzentscheidung erforderlich.',
    'SECOND_BATTERY_POWER_TOPIC': 'Vollständiges MQTT-Topic der Zusatzbatterie-Leistung. Dieses Topic ist im benutzerdefinierten Profil Pflicht, weil der Cross-Charge-Schutz primär aus der Leistung erkennt, ob die Zusatzbatterie entlädt.',
    'SECOND_BATTERY_SOC_TOPIC': "Optionales MQTT-Topic für den Ladezustand der Zusatzbatterie in Prozent. Der Schutz kann auch ohne SOC arbeiten; die Anzeige zeigt dann 'nicht konfiguriert'.",
    'SECOND_BATTERY_EVCC_BASE_TOPIC': 'Basis-Topic der Zusatzbatterie bei EVCC-Standardstruktur, z. B. evcc/site/battery/devices/1. Daraus werden Leistung, SOC und Kapazität automatisch als /power, /soc und /capacity abgeleitet.',
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
    'REST_SURPLUS_MIN_EXPORT_W': 'Mindestexport am Netzanschlusspunkt, ab dem die Restüberschuss-Ernte für den Entry qualifiziert. Dieser Wert ist nur eine Aktivierungs-/Rauschschwelle, kein dauerhaft gewünschter Restexport. Default: 80 W.',
    'CROSS_CHARGE_ENABLED': 'Aktiviert das Einlesen einer externen Zusatzbatterie per MQTT und verhindert unerwünschtes Batterie-zu-Batterie-Laden.',
    'SECOND_BATTERY_STALE_BLOCK_CHARGE': 'Konservativer Fallback: Wenn der Cross-Charge-Schutz aktiv ist, aber keine frischen Zusatzbatteriedaten vorliegen, wird Zendure-Ladung blockiert.',
    'CROSS_CHARGE_SIGNIFICANT_W': 'Ab diesem gegenläufigen Leistungsfluss zwischen Zusatzbatterie und Zendure wird der Cross-Charge-Schutz aktiv. Eine interne niedrigere Freigabeschwelle verhindert hektisches Ein-/Ausschalten.',
    'COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS': 'Nach dieser Zeit muss eine sicherheitsrelevante 0-W-Neutralisierung physisch bestätigt sein. Bei fortbestehender Leistung sendet ZEC AC-Modus sowie beide Limits als vollständige 0-W-Zustandsneutralisierung erneut.',
    'ZENDURE_COMMAND_STATE_FRESH_SECONDS': 'Maximales Alter der rückgelesenen Werte smartMode, acMode, inputLimit und outputLimit. Dynamische Limitänderungen werden nur bei bestätigtem smartMode=1 freigegeben.',
    'ZENDURE_COMMAND_STATE_RETRY_SECONDS': 'Mindestabstand für einen erneuten vollständigen Modus-/Limit-Abgleich, solange die Rücklesung noch nicht konsistent ist.',
    'ZENDURE_SMART_MODE_RETRY_SECONDS': 'Mindestabstand für erneutes smartMode=ON, wenn der volatile Flash-Schutz noch nicht rückgelesen wurde.',
    'COMMAND_RESYNC_STALE_MIN_SECONDS': 'Mindestdauer eines unsicheren Zendure-MQTT-Zustands, bevor Recovery einen Command-Resync auslöst.',
    'COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS': 'Notfall-/Legacy-Schalter: erzwingt Resync bei jeder Zendure-MQTT-Recovery. Standard in V12.11.2-RC1 ist aus, damit kurze STALE-Phasen keinen Resync-Sturm auslösen.',
    'COMMAND_EFFECT_FORCE_RESEND_SECONDS': 'Nach dieser Zeit sendet ZEC einen weiterhin unwirksamen aktiven Sollzustand vollständig erneut. Resync-Versand und anschließend bestätigte Gerätewirkung werden getrennt dokumentiert.',
    'COMMAND_RESYNC_COOLDOWN_SECONDS': 'Unterdrückt identische Resync-Wiederholungen im Cooldown, außer bei weiter bestätigtem Mismatch nach Ablauf des Cooldowns.',
    'COMMAND_EFFECT_TOLERANCE_PERCENT': 'Relative Toleranz für hohe Sollwerte. Sie verändert nur die Wirkungsdiagnose, niemals den Regler-Sollwert oder eine Gerätegrenze.',
    'COMMAND_EFFECT_TOLERANCE_W': 'Absolute Mindesttoleranz für das Zielwerttracking. Verwendet wird der größere Wert aus dieser absoluten Toleranz und der relativen Prozenttoleranz.',
    'COMMAND_EFFECT_MIN_TARGET_W': 'Unterhalb dieser Schwelle ist die physische Wirkung nicht belastbar bewertbar; der Zustand wird nicht als COMMAND_EFFECTIVE ausgegeben.',
    'COMMAND_EFFECT_MIN_W': 'Schwellwert, ab dem eine unabhängige Istleistungsbeobachtung als belastbare Reaktion in Lade- oder Entladerichtung gilt. Das beweist noch kein vollständiges Sollwerttracking.',
    'COMMAND_EFFECT_TIMEOUT_SECONDS': 'Nach dieser zusammenhängenden Zeit desselben Lade-/Entlade-Intents bestätigt ZEC fehlende Richtungsreaktion oder dauerhaft erhebliches Untertracking. Kleine Wattänderungen derselben Richtung starten die Zeit nicht neu.',
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
    'ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS': 'Begrenzt den Hintergrundrequest unabhängig vom höheren allgemeinen API-Timeout. Seit RC18 blockiert die lokale API den Regelzyklus nicht mehr.',
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
    'SLOW_CYCLE_WARN_MS': 'Schreibt einen Runtime-Hinweis, wenn ein Reglerzyklus ohne Sleep länger dauert. Dient der RC3-Timingdiagnose.',
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
    "HARVEST_HIGH_SMA_SOC_ENTER_PERCENT": "SMA-SOC-Schwelle für den Eintritt in den High-SOC-Bereich. Zusammen mit dem niedrigeren Austrittswert bildet sie eine Hysterese.",
    "HARVEST_HIGH_SMA_SOC_EXIT_PERCENT": "SMA-SOC-Schwelle zum Verlassen des High-SOC-Bereichs. Sie muss unter der Eintrittsschwelle liegen.",
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
    "HARVEST_HIGH_SMA_SOC_ENABLED": "Erlaubt zusätzlich den High-SOC-Harvestzweig innerhalb der Master-Harvestlogik.",
    "COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS": "Erweitert das Legacy-/Notfall-Resyncverhalten nach MQTT-Recovery.",
}
EFFECT_DISABLE = {
    "CROSS_CHARGE_ENABLED": "Deaktiviert diese zusätzliche Gegenfluss-Schutzschicht; normale SOC-/Leistungsgrenzen bleiben bestehen.",
    "SECOND_BATTERY_STALE_BLOCK_CHARGE": "Entfernt den konservativen Stale-Block und reduziert damit einen Schutzmechanismus.",
    "NIGHT_DISCHARGE_ENABLED": "Die Nachtwerte bleiben gespeichert, erzeugen aber keine feste Nacht-Basisentladung.",
    "REST_SURPLUS_HARVEST_ENABLED": "Alle davon abhängigen Harvestwerte bleiben gespeichert, sind aber derzeit ohne Wirkung.",
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
    "SECOND_BATTERY_DISCHARGE_SIGN": "Falsches Vorzeichen kann Lade- und Entladerichtung der Zweitbatterie falsch interpretieren und damit den Cross-Charge-Schutz entwerten.",
    "GRID_METER_SOURCE": "Eine falsche oder nicht verfügbare Netzleistungsquelle verhindert eine korrekte Regelabweichung und kann Ready/Safety blockieren.",
    "MAX_CONSECUTIVE_ERRORS": "Sehr niedrige Werte können Safe-State früh auslösen; sehr hohe Werte verzögern die Reaktion auf anhaltende Fehler.",
    "MQTT_DISCONNECTED_SAFE_STATE": "Deaktivieren reduziert den konservativen Schutz bei längeren Broker-/MQTT-Problemen.",
    "SAFE_STATE_ON_SHELLY_ERROR": "Deaktivieren reduziert den konservativen Schutz bei anhaltend fehlerhafter Netzleistungsmessung.",
    "SOC_STALE_TIMEOUT_SECONDS": "Zu große Aktualitätsfenster können Entladung mit veraltetem SOC länger zulassen; zu kleine Fenster können bei kurzen Telemetrielücken unnötig blockieren.",
    "WEB_HOST": "Eine breite Bind-Adresse kann das Webinterface in mehr Netzsegmenten erreichbar machen. Zugriffsschutz erfolgt außerhalb dieses Parameters.",
}

OPTION_HELP = {
    "MANUAL_MODE": (("AUTO", "Normale Netzleistungsregelung."), ("STOP_HOLD", "Aktive Neutralität mit 0-W-Ziel."), ("FIXED_DISCHARGE", "Feste Entladung bis Ziel-SOC."), ("FIXED_CHARGE", "Feste Ladung bis Ziel-SOC.")),
    "MEASUREMENT_LOG_MODE": (("off", "Keine neuen Measurement-V4-Zeilen schreiben."), ("standard", "Produktive Regler-/Diagnosedaten mit begrenztem Feldumfang."), ("extended", "Zusätzliche Detailfelder für tiefe Analyse/Simulation; höheres Datenvolumen.")),
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


def build_setting_help(row: Mapping[str, Any]) -> SettingHelpSpec:
    key = str(row["key"])
    category = str(row["category"])
    short = SHORT_HELP.get(key) or f"Konfiguration für {LABEL_OVERRIDES.get(key, row.get('label', key))}."
    rich = category in RICH_CATEGORIES
    extended = RICH_EXTENDED.get(key) or _generic_extended(short, row)
    deps = _dependencies(row)
    dep_help = None
    if deps:
        dep_help = RICH_DEPENDENCY_HELP.get(category) if rich else "Verknüpfte Einstellungen können Aktivierung, Grenzen, Quelle oder Vorrang beeinflussen. Die konkrete Beziehung ist unten aufgeführt."
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
        when_help=RICH_WHEN.get(key) if rich else None,
        help_level="rich" if rich else "base",
        search_terms=_search_terms(row, short),
        handbook_ref=_handbook_ref(category),
        effect_increase=EFFECT_INCREASE.get(key),
        effect_decrease=EFFECT_DECREASE.get(key),
        effect_enable=EFFECT_ENABLE.get(key),
        effect_disable=EFFECT_DISABLE.get(key),
        option_help=OPTION_HELP.get(key, ()),
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


def build_section_specs(category_sections: Sequence[Tuple[str, str]]) -> Mapping[Tuple[str, str], SectionSpec]:
    out: Dict[Tuple[str, str], SectionSpec] = {}
    overrides = {
        ("Betriebsart & manuelle Steuerung", "Betriebsart"): "Wählt die aktive Steuerungspriorität. Schutzbedingungen bleiben über jedem manuellen oder automatischen Modus.",
        ("Nachtbetrieb", "Zeitfenster"): "Start und Ende bilden ein logisches HH:MM-Zeitfenster; ein Verlauf über Mitternacht ist zulässig.",
        ("Harvest / Restüberschuss", "Primärspeicher-Schwellen"): "Floor <= Restart <= Near-Limit <= Pmax. Positive absolute W-Overrides ersetzen jeweils den zugehörigen Ratio-Wert.",
        ("Harvest / Restüberschuss", "High-SOC & Vollspeicher"): "High-SOC Enter/Exit bilden eine Hysterese; Full-SOC grenzt den Voll-/Idle-Zweig ab. Exportwerte sind Eintrittsschwellen, keine Restexportziele.",
        ("Harvest / Restüberschuss", "Tageszeitprofil"): "Die Profilanteile verändern die Strategieallokation zwischen Primärspeicher und Zendure. Sie sind keine direkten Zendure-Sollwerte.",
        ("AUTO-Regelung", "Reglerberechnung"): "Gain erzeugt die Rohkorrektur, Smoothing glättet das Ziel danach. Weitere Limiter wirken anschließend.",
        ("AUTO-Regelung", "Reaktionsgeschwindigkeit"): "Step und Guard-Ramp begrenzen unterschiedliche Änderungspfade; höhere Werte bedeuten nicht automatisch bessere Regelqualität.",
        ("Cross-Charge-Schutz", "Schaltschwelle & Hysterese"): "Engage nutzt die konfigurierte positive Schwelle; Release verwendet intern max(20 W, Engage/2).",
        ("Kommandowirkung & Resync", "Sollwerttracking"): "Tracking nutzt das Maximum aus absoluter und relativer Toleranz. Richtungsreaktion allein ist noch kein vollständiger Trackingnachweis.",
        ("Kommandowirkung & Resync", "Wirkungsbewertung"): "Diagnosegrenze, Mindest-Istleistung und Timeout bestimmen unterschiedliche Qualitätsstufen der Kommandowirkung.",
        ("Schnittstellen & Datenquellen", "MQTT-Verbindung"): "Broker, Port und optionale Authentifizierung bilden den zentralen Command-/Telemetriepfad. Installationswerte werden nicht als Produktdefaults empfohlen.",
        ("Schnittstellen & Datenquellen", "Netzleistung · aktive Quelle"): "Die aktive Netzleistungsquelle ist eine Anlagenentscheidung. Quellspezifische Pflichtdaten müssen vollständig sein, bevor sie produktiv genutzt wird.",
        ("Messdaten & Speicherung", "Measurement-V4"): "Measurement V4 ist der produktive Vertrag. Logging kann aus sein oder standard/extended schreiben; es bleibt nachgelagert zum Regelzyklus.",
        ("System & Diagnose", "Administrative Aktionen"): "Neustart und Last-Good-Pointer-Reparatur sind explizite geschützte Aktionen und keine normalen Settings-Commits.",
    }
    for category, section in category_sections:
        text = overrides.get((category, section)) or f"{section}: zusammengehörige Parameter innerhalb der Kategorie {category}. Die Detailhilfe der einzelnen Einstellungen beschreibt Wirkung, Abhängigkeiten und Wirksamkeit nach dem Speichern."
        out[(category, section)] = SectionSpec(category, section, text, _handbook_ref(category))
    return MappingProxyType(out)
