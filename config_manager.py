# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import json
import os
import shutil
import tempfile
import threading
import time
from copy import deepcopy
from typing import Any, Dict, Tuple


DEFAULT_CONFIG: Dict[str, Any] = {
    # Netzwerk / Infrastruktur
    "SHELLY_IP": "192.168.0.40",
    # Netzleistungsquelle / SMA Home Manager Direktdiagnose
    "GRID_METER_SOURCE": "shelly_http",
    "SMA_ENERGY_METER_PASSIVE_ENABLED": False,
    "SMA_ENERGY_METER_GROUP": "239.12.255.254",
    "SMA_ENERGY_METER_PORT": 9522,
    "SMA_ENERGY_METER_INTERFACE": "",
    "SMA_ENERGY_METER_SUSY_ID": "",
    "SMA_ENERGY_METER_SERIAL": "",
    "SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS": 15,
    "SMA_ENERGY_METER_SOCKET_MODE": "group_bind",
    "SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS": 5,
    "SMA_ENERGY_METER_LOG_DIAGNOSTICS": False,
    "SMA_ENERGY_METER_LOG_INTERVAL_SECONDS": 60,
    "GRID_POWER_PLAUSIBILITY_MAX_ABS_W": 30000,
    "MQTT_BROKER": "192.168.0.40",
    "MQTT_PORT": 1883,
    "MQTT_USER": "mqttuser",
    # Sicherheitsbewusst leerer Default. Eine bestehende config.json bleibt unverändert.
    "MQTT_PASSWORD": "",
    "DEVICE_ID": "REPLACE_WITH_ZENDURE_DEVICE_ID",
    "WEB_HOST": "0.0.0.0",
    "WEB_PORT": 8080,
    "REPLAY_WEB_PORT": 8090,
    "HEADLESS_MODE": False,

    # Weboberfläche / Darstellung
    "UI_DARK_MODE": True,
    "UI_MODE": "standard",
    "SOC_DAY_GRAPH_ENABLED": True,
    "SOC_DAY_GRAPH_SAMPLE_SECONDS": 60,
    "SOC_DAY_GRAPH_BOOTSTRAP_FROM_MEASUREMENTS": True,
    "SOC_DAY_GRAPH_BOOTSTRAP_CACHE_SECONDS": 300,
    "WEB_SERVICE_RESTART_ENABLED": False,
    "SERVICE_RESTART_COMMAND": "sudo /usr/local/sbin/zendure-controller-restart",

    # Diagnose / Zendure lokal / MQTT Topic-Mitschnitt
    "ZENDURE_LOCAL_API_ENABLED": False,
    "ZENDURE_LOCAL_IP": "",
    "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": 5,
    "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": 1.5,
    "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": False,
    "ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY": True,
    "ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS": 5,
    "ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS": 30,
    "ZENDURE_LOCAL_API_SOC_PRIORITY": "properties_first",
    "MQTT_TOPIC_DIAGNOSTIC_ENABLED": False,
    "MQTT_TOPIC_DIAGNOSTIC_FILTER": "Zendure/#",
    "MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE": "filtered",
    "MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT": 200,

    # Regelung
    "INTERVAL_SECONDS": 3,
    "SLOW_CYCLE_WARN_MS": 5000,
    "DEADBAND_W": 80,
    "MOVING_AVERAGE_SAMPLES": 10,
    "SMOOTHING_FACTOR": 0.25,
    "MAX_POWER_STEP_W": 150,
    "MAX_DISCHARGE_POWER_W": 2100,
    "MAX_CHARGE_POWER_W": 2100,
    "MIN_SOC_PERCENT": 15,
    "MAX_SOC_PERCENT": 99,
    "CONTROL_GAIN": 0.30,
    "MIN_COMMAND_CHANGE_W": 50,
    "MODE_CHANGE_LOCK_SECONDS": 4,
    "COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS": False,
    "COMMAND_RESYNC_STALE_MIN_SECONDS": 30,
    "COMMAND_RESYNC_STALE_MIN_CYCLES": 3,
    "COMMAND_RESYNC_COOLDOWN_SECONDS": 120,
    "COMMAND_EFFECT_MIN_TARGET_W": 120,
    "COMMAND_EFFECT_MIN_W": 80,
    "COMMAND_EFFECT_TOLERANCE_W": 80,
    "COMMAND_EFFECT_TIMEOUT_SECONDS": 90,
    "COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS": 30,
    "ZENDURE_COMMAND_STATE_FRESH_SECONDS": 30,
    "ZENDURE_SMART_MODE_RETRY_SECONDS": 30,
    "ZENDURE_COMMAND_STATE_RETRY_SECONDS": 30,
    "COMMAND_EFFECT_FORCE_RESEND_SECONDS": 120,

    # Manueller Modus
    "MANUAL_MODE": "AUTO",
    "MANUAL_FIXED_DISCHARGE_POWER_W": 400,
    "MANUAL_FIXED_DISCHARGE_TARGET_SOC": 30,
    "MANUAL_DISCHARGE_AFTER_TARGET": "AUTO",
    "MANUAL_FIXED_CHARGE_POWER_W": 800,
    "MANUAL_FIXED_CHARGE_TARGET_SOC": 90,
    "MANUAL_CHARGE_AFTER_TARGET": "AUTO",

    # Cross-Charge-Schutz / externe Zusatzbatterie
    "CROSS_CHARGE_ENABLED": False,
    "SECOND_BATTERY_DISPLAY_NAME": "SMA Sunny Island",
    "SECOND_BATTERY_SOURCE_PROFILE": "evcc_standard",
    "SECOND_BATTERY_EVCC_BASE_TOPIC": "evcc/site/battery/devices/1",
    "SECOND_BATTERY_POWER_TOPIC": "evcc/site/battery/devices/1/power",
    "SECOND_BATTERY_SOC_TOPIC": "evcc/site/battery/devices/1/soc",
    "SECOND_BATTERY_CAPACITY_TOPIC": "evcc/site/battery/devices/1/capacity",
    "SECOND_BATTERY_POWER_PAYLOAD_TYPE": "number",
    "SECOND_BATTERY_POWER_JSON_PATH": "power",
    "SECOND_BATTERY_SOC_PAYLOAD_TYPE": "number",
    "SECOND_BATTERY_SOC_JSON_PATH": "soc",
    "SECOND_BATTERY_CAPACITY_PAYLOAD_TYPE": "number",
    "SECOND_BATTERY_CAPACITY_JSON_PATH": "capacity",
    "SECOND_BATTERY_POWER_UNIT": "W",
    "SECOND_BATTERY_CAPACITY_UNIT": "kWh",
    "SECOND_BATTERY_DISCHARGE_SIGN": 1,
    "SMA_DISCHARGE_BLOCK_W": 80,
    "CROSS_CHARGE_SIGNIFICANT_W": 80,
    "CROSS_CHARGE_RESERVE_W": 100,
    "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W": 150,
    "SMA_GUARD_RAMP_DOWN_W": 250,
    "SECOND_BATTERY_STALE_TIMEOUT_SECONDS": 30,
    "SECOND_BATTERY_STALE_BLOCK_CHARGE": True,
    "REST_SURPLUS_HARVEST_ENABLED": False,
    "SECOND_BATTERY_MAX_CHARGE_POWER_W": None,
    "REST_SURPLUS_MIN_EXPORT_W": 80,
    "REST_SURPLUS_ENTRY_CONFIRM_SECONDS": 30,
    "SECOND_BATTERY_CHARGE_SATURATION_MARGIN_W": 100,
    "HARVEST_HIGH_SMA_SOC_ENABLED": True,
    "HARVEST_HIGH_SMA_SOC_ENTER_PERCENT": 75,
    "HARVEST_HIGH_SMA_SOC_EXIT_PERCENT": 70,
    "HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W": 300,
    "HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS": 30,
    "HARVEST_HIGH_SMA_SOC_HOLD_SECONDS": 180,
    "HARVEST_SMA_FULL_SOC_PERCENT": 98,
    "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO": 0.30,
    "HARVEST_PRIMARY_CHARGE_FLOOR_W": None,
    "HARVEST_PRIMARY_CHARGE_RESTART_RATIO": 0.85,
    "HARVEST_PRIMARY_CHARGE_RESTART_W": None,
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO": 0.95,
    "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W": None,
    "HARVEST_PRIMARY_BELOW_FLOOR_CONFIRM_SECONDS": 6,
    "HARVEST_PRIMARY_RESTART_CONFIRM_SECONDS": 30,
    "HARVEST_IMPORT_REDUCE_CONFIRM_SECONDS": 6,
    "HARVEST_IMPORT_EXIT_CONFIRM_SECONDS": 30,
    "HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED": True,
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING": 0.60,
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY": 0.50,
    "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON": 0.35,
    "HARVEST_CAPACITY_WEIGHTING_MODE": "diagnostic",
    "ZENDURE_BATTERY_CAPACITY_KWH": None,


    # Nachtmodus
    "NIGHT_DISCHARGE_ENABLED": False,
    "NIGHT_START_HOUR": 20,
    "NIGHT_START_MINUTE": 30,
    "NIGHT_END_HOUR": 5,
    "NIGHT_END_MINUTE": 0,
    "NIGHT_DISCHARGE_POWER_W": 400,
    # Optional: eigener Stop-/Reserve-SOC für den Nachtmodus. None/leer = bisheriges Verhalten.
    "NIGHT_DISCHARGE_STOP_SOC_PERCENT": None,
    "ZENDURE_BATTERY_CAPACITY_WH": None,

    # Sicherheits-/Fallback-Optionen
    "MAX_CONSECUTIVE_ERRORS": 5,
    "SHELLY_STALE_TIMEOUT_SECONDS": 15,
    "SOC_STALE_TIMEOUT_SECONDS": 90,
    "MQTT_DISCONNECTED_SAFE_STATE": False,
    "ZENDURE_POWER_STALE_TIMEOUT_SECONDS": 90,
    "ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS": 90,
    "ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS": 90,
    "SAFE_STATE_ON_SHELLY_ERROR": True,

    # Historie / Messdaten-Logging
    "GRAPH_HISTORY_LIMIT": 300,
    "MEASUREMENT_LOG_MODE": "off",
    "MEASUREMENT_SCHEMA_VERSION": "4",
    "MEASUREMENT_DB_ENABLED": True,
    "MEASUREMENT_DB_FILE": "zec_measurements.sqlite3",
    "MEASUREMENT_DB_PATH": "",
    "MEASUREMENT_DB_MAX_QUEUE_ROWS": 5000,
    "MEASUREMENT_LOG_STORAGE_TARGET": "internal_sd",
    "MEASUREMENT_LOG_MOUNTPOINT": "",
    "MEASUREMENT_LOG_DIR": "logs",
    "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
    "MEASUREMENT_LOG_MAX_BYTES": 25_000_000,
    "MEASUREMENT_LOG_BACKUP_COUNT": 5,
    "MEASUREMENT_LOG_MIN_FREE_DISK_MB": 500,
    "MEASUREMENT_LOG_ESTIMATED_ROW_BYTES": 650,
    "MEASUREMENT_LOG_FLUSH_EVERY_ROWS": 100,
    "MEASUREMENT_LOG_FLUSH_EVERY_SECONDS": 60,
    "MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_ROWS": 25,
    "MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_SECONDS": 30,
    "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": True,
    "MEASUREMENT_LOG_FALLBACK_DIR": "logs/fallback",
    "MEASUREMENT_LOG_FALLBACK_MAX_BYTES": 10_000_000,
    "MEASUREMENT_LOG_FALLBACK_BACKUP_COUNT": 2,
    # Analyse-/Replay-Service Schutzlimits
    "ANALYSIS_MAX_FILES": 2,
    "ANALYSIS_MAX_TOTAL_BYTES": 6 * 1024 * 1024,
    "ANALYSIS_MAX_ROWS": 20_000,
    "ANALYSIS_EXTENDED_MAX_FILES": 3,
    "ANALYSIS_EXTENDED_MAX_TOTAL_BYTES": 10 * 1024 * 1024,
    "ANALYSIS_EXTENDED_MAX_ROWS": 35_000,
    "ANALYSIS_WORKER_MEMORY_LIMIT_MB": 300,
    "ANALYSIS_EXTENDED_WORKER_MEMORY_LIMIT_MB": 380,
    "ANALYSIS_WORKER_TIMEOUT_SECONDS": 180,
    "ANALYSIS_EXTENDED_WORKER_TIMEOUT_SECONDS": 300,

    # Logging
    "FILE_LOG_ENABLED": False,
    "FILE_LOG_DIR": "logs",
    "FILE_LOG_FILE": "zendure_runtime.log",
    "FILE_LOG_MAX_BYTES": 2_000_000,
    "FILE_LOG_BACKUP_COUNT": 3,
    "DEBUG": False,
    "LOG_VALUES": False,
    "LOG_CONTROL": False,
    "LOG_MANUAL": True,
    "LOG_MQTT": False,
    "LOG_SOC": False,
    "LOG_RAW_RESPONSE": False,
}


# Die Settings-Seite wird aus diesem Schema erzeugt. Dadurch bleiben Validierung,
# UI und Defaults konsistent.
CONFIG_SCHEMA: Dict[str, Dict[str, Any]] = {
    "SHELLY_IP": {"group": "Netzwerk", "label": "Shelly-kompatible HTTP-Quelle IP", "type": "str", "description": "IP-Adresse der Shelly- oder Shelly-kompatiblen Messdatenquelle. Das kann ein echter Shelly Pro 3EM oder ein anderer Shelly-kompatibler HTTP-Endpunkt sein."},
    "GRID_METER_SOURCE": {"group": "Netzwerk", "label": "Netzleistungsquelle", "type": "select", "options": {"shelly_http": "Shelly-kompatible HTTP-Quelle", "sma_energy_meter_udp": "SMA Home Manager direkt (UDP)"}, "description": "Quelle für die Netzleistung am Hausanschlusspunkt. Shelly-kompatibles HTTP bleibt dauerhaft als Alternative für echte Shelly Pro 3EM und kompatible Endpunkte erhalten. SMA direkt nutzt das lokale SMA Energy Meter / Sunny Home Manager UDP-Multicast-Protokoll."},
    "SMA_ENERGY_METER_PASSIVE_ENABLED": {"group": "Netzwerk", "label": "SMA-Direktquelle zusätzlich passiv beobachten", "type": "bool", "description": "Nur relevant, wenn als Netzleistungsquelle die Shelly-kompatible HTTP-Quelle gewählt ist: startet zusätzlich einen passiven SMA Energy Meter / Sunny Home Manager 2.0 Listener zum Vergleich. Wenn SMA Home Manager direkt als Netzleistungsquelle gewählt ist, wird der Listener automatisch aktiviert; dieser Schalter ist dann fachlich redundant."},
    "SMA_ENERGY_METER_GROUP": {"group": "Netzwerk", "label": "SMA Energy Meter Multicast-Gruppe", "type": "str", "description": "Multicast-Adresse der SMA Energy Meter Daten. Typischer Standard: 239.12.255.254."},
    "SMA_ENERGY_METER_PORT": {"group": "Netzwerk", "label": "SMA Energy Meter UDP-Port", "type": "int", "min": 1, "max": 65535, "description": "UDP-Port für SMA Energy Meter / Sunny Home Manager 2.0 Multicast. Typischer Standard: 9522."},
    "SMA_ENERGY_METER_INTERFACE": {"group": "Netzwerk", "label": "SMA Energy Meter Interface/IP", "type": "str", "description": "Optional: lokale IPv4-Adresse oder Interface-Name wie eth0 für den Multicast-Join. Bei mehreren Netzwerkinterfaces bevorzugt eth0 eintragen."},
    "SMA_ENERGY_METER_SUSY_ID": {"group": "Netzwerk", "label": "SMA Energy Meter SUSy-ID", "type": "str", "description": "Optionaler Filter auf die SMA SUSy-ID des gewünschten Energy Meters. Bei mehreren SMA Energy Metern empfohlen. Beispiel: <SMA-SUSY-ID>."},
    "SMA_ENERGY_METER_SERIAL": {"group": "Netzwerk", "label": "SMA Energy Meter Seriennummer", "type": "str", "description": "Optionaler Filter auf die Seriennummer des Energy Meters am Netzbezugspunkt. Bei mehreren SMA Energy Metern vor produktiver Nutzung zwingend empfohlen."},
    "SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS": {"group": "Sicherheit / Fallback", "label": "SMA Direkt Timeout", "type": "int", "min": 5, "max": 600, "unit": "s", "description": "Maximales Alter eines direkt per SMA Energy Meter empfangenen Netzleistungswerts, falls die direkte SMA-Quelle als Regelquelle verwendet wird."},
    "SMA_ENERGY_METER_SOCKET_MODE": {"group": "Netzwerk", "label": "SMA Socket-Modus", "type": "select", "options": {"group_bind": "Empfohlen: Bind auf Multicast-Gruppe", "rc3_compatible": "Diagnose: RC3-kompatibel / SO_REUSEPORT best-effort", "reuseaddr_only": "Diagnose: nur SO_REUSEADDR", "unimeter_like": "Diagnose: UniMeter-naher Join ohne IP_MULTICAST_IF"}, "description": "Experten-/Diagnoseoption für die Koexistenz mit EVCC, UniMeter oder weiteren SMA-Speedwire-Listenern auf demselben Host. Default group_bind bindet auf die SMA-Multicast-Gruppe und war im Nachtlauf mit EVCC auf demselben Raspberry Pi stabil. Wildcard-Modi auf 0.0.0.0:9522 bleiben reine Diagnoseoptionen und können EVCC stören."},
    "SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS": {"group": "Netzwerk", "label": "SMA Paketlücken-Warnung", "type": "int", "min": 1, "max": 300, "unit": "s", "description": "Ab dieser Lücke zwischen empfangenen SMA-Speedwire-Paketen wird die Lücke in der SMA-Diagnose markiert. Der Stream kommt typischerweise ungefähr sekündlich."},
    "SMA_ENERGY_METER_LOG_DIAGNOSTICS": {"group": "Logging", "label": "SMA-Direktquelle Diagnose ins Runtime-Log", "type": "bool", "description": "Schreibt kompakte SMA-Socket-/Paketdiagnosen in das Runtime-Textlog. Zusätzlich muss Datei-Logging aktiv sein, damit die Meldungen in zendure_runtime.log landen."},
    "SMA_ENERGY_METER_LOG_INTERVAL_SECONDS": {"group": "Logging", "label": "SMA-Diagnose Log-Intervall", "type": "int", "min": 10, "max": 3600, "unit": "s", "description": "Mindestabstand zwischen periodischen SMA_DIAG-Zeilen im Runtime-Log, wenn SMA-Diagnoselogging aktiv ist."},
    "GRID_POWER_PLAUSIBILITY_MAX_ABS_W": {"group": "Sicherheit / Fallback", "label": "Netzleistungs-Plausibilitätsgrenze", "type": "int", "min": 1000, "max": 250000, "unit": "W", "description": "Absolute Obergrenze für plausible Netzleistungswerte. Messwerte oberhalb dieser Grenze werden verworfen und nicht für AUTO-Regelung oder Glättung verwendet. Default 30000 W schützt vor offensichtlich defekten SMA-/Shelly-Ausreißern."},
    "MQTT_BROKER": {"group": "Netzwerk", "label": "MQTT Broker", "type": "str", "description": "Adresse des MQTT-Brokers. Meist der Raspberry Pi selbst."},
    "MQTT_PORT": {"group": "Netzwerk", "label": "MQTT Port", "type": "int", "min": 1, "max": 65535, "description": "Port des MQTT-Brokers. Standard ist 1883."},
    "MQTT_USER": {"group": "Netzwerk", "label": "MQTT Benutzer", "type": "str", "description": "Benutzername für MQTT. Leer lassen, wenn keine Authentifizierung verwendet wird."},
    "MQTT_PASSWORD": {"group": "Netzwerk", "label": "MQTT Passwort", "type": "password", "description": "Passwort für MQTT. Wird in der lokalen config.json gespeichert."},
    "DEVICE_ID": {"group": "Netzwerk", "label": "Zendure Device ID", "type": "str", "description": "Identifier der Zendure Headunit für die MQTT-Topics."},
    "WEB_PORT": {"group": "Netzwerk", "label": "Web Port", "type": "int", "min": 1, "max": 65535, "description": "HTTP-Port des Webinterfaces. Änderung erfordert Neustart."},
    "REPLAY_WEB_PORT": {"group": "Weboberfläche", "label": "Analyse-Web Port", "type": "int", "min": 1, "max": 65535, "description": "Port des optionalen separaten Analyse-/Replay-Webdienstes. Der Dienst wird mitgeliefert, aber nicht automatisch aktiviert."},
    "HEADLESS_MODE": {"group": "Netzwerk", "label": "Headless Mode", "type": "bool", "description": "Schaltet die Weboberflächen ab. Beim Aufruf der Web-URLs wird nur noch eine Hinweisseite angezeigt. Die Regelung läuft weiter; Änderungen sind dann ausschließlich über die config.json und den regulären Config-Reload möglich. Ein Neustart ist zum Beenden des Headless Mode nicht erforderlich, wenn die config.json während des laufenden Programms angepasst wird."},

    "UI_DARK_MODE": {"group": "Weboberfläche", "label": "Dark Mode aktiv", "type": "bool", "description": "Aktiviert ein dunkles Farbschema für Statusseite, Settings, Graph, Diagnose, Analyse-Linkseiten und Headless-Hinweisseite. Die Änderung wird nach dem Speichern sofort bei neu geladenen Webseiten sichtbar."},
    "SOC_DAY_GRAPH_ENABLED": {"group": "Weboberfläche", "label": "SOC-Tageskurve anzeigen", "type": "bool", "description": "Zeigt auf der Statusseite eine leichte 24h-Zendure-SOC-Kurve für den aktuellen lokalen Tag."},
    "SOC_DAY_GRAPH_SAMPLE_SECONDS": {"group": "Weboberfläche", "label": "SOC-Tageskurve Sampling (s)", "type": "int", "description": "Samplingintervall der SOC-Tageskurve im RAM. Default 60 Sekunden; der Controller hält maximal etwa 1440 Punkte pro Tag."},
    "SOC_DAY_GRAPH_BOOTSTRAP_FROM_MEASUREMENTS": {"group": "Weboberfläche", "label": "SOC-Tageskurve aus Messdaten starten", "type": "bool", "description": "Versucht beim Abruf der SOC-Tageskurve, heutige Measurement-V4-Logs best-effort einzulesen. Fehler sind nicht kritisch; die Kurve startet dann ab jetzt."},
    "UI_MODE": {"group": "Weboberfläche", "label": "Oberflächenmodus", "type": "select", "options": {"standard": "Standard", "expert": "Experte"}, "description": "Vorbereitung für eine reduzierte Standardansicht und eine vollständige Expertenansicht. Expertenmodus ist fachlich ein Superset des Standardmodus: Kernstatus und Warnungen bleiben immer sichtbar, Expert-only-Details kommen zusätzlich hinzu."},
    "WEB_SERVICE_RESTART_ENABLED": {"group": "Weboberfläche", "label": "Service-Neustart aus Weboberfläche erlauben", "type": "bool", "description": "Erlaubt der Weboberfläche, nach dem Speichern neustartrelevanter Einstellungen den systemd-Dienst kontrolliert neu zu starten. Aus Sicherheitsgründen ist diese Funktion standardmäßig deaktiviert und benötigt zusätzlich ein freigegebenes Restart-Hilfsscript mit sudoers-Regel."},
    "SERVICE_RESTART_COMMAND": {"group": "Weboberfläche", "label": "Service-Neustart Befehl", "type": "str", "description": "Befehl, den die Weboberfläche für einen kontrollierten Dienstneustart ausführen darf, z. B. sudo /usr/local/sbin/zendure-controller-restart. Dieser Befehl sollte auf ein root-geschütztes Hilfsscript zeigen und nicht frei editierbar für untrusted Benutzer sein."},
    "ZENDURE_LOCAL_API_ENABLED": {"group": "Netzwerk", "label": "Zendure lokale API Diagnose aktiv", "type": "bool", "description": "Aktiviert den Diagnose-Endpunkt /zendure-properties. Diese Option steuert die Web-Diagnoseseite; die Telemetrie-Fallback-Nutzung wird separat über die folgenden Optionen gesteuert."},
    "ZENDURE_LOCAL_IP": {"group": "Netzwerk", "label": "Zendure lokale IP", "type": "str", "description": "IP-Adresse der Zendure-Headunit für lokale Abfragen wie /properties/report. Wird sowohl für die Diagnose-Webseite als auch für den optionalen Telemetrie-Fallback verwendet."},
    "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": {"group": "Netzwerk", "label": "Zendure lokale API Timeout", "type": "int", "min": 1, "max": 30, "unit": "s", "description": "Maximale Wartezeit für lokale Zendure-Abfragen in Sekunden."},
    "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": {"group": "Netzwerk", "label": "Zendure lokale API Regelzyklus-Timeoutdeckel", "type": "float", "min": 0.2, "max": 5.0, "unit": "s", "description": "Begrenzt die wirksame Wartezeit der optionalen lokalen Zendure-API im Live-Regelzyklus. Schützt die Reaktionszeit, auch wenn ältere Konfigurationen einen höheren API-Timeout enthalten."},
    "ZENDURE_LOCAL_API_USE_FOR_TELEMETRY": {"group": "Netzwerk", "label": "Zendure lokale API für Telemetrie nutzen", "type": "bool", "description": "Wenn aktiv, darf der Controller die lokale Zendure-API als zusätzliche Telemetriequelle für SOC, Istleistung und Akkutemperatur verwenden. Das ist ein Fallback gegen den bekannten Fall, dass Zendure nach Broker-/Raspberry-Neustart keine MQTT-Sensordaten mehr publiziert."},
    "ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY": {"group": "Netzwerk", "label": "Zendure lokale API nur als Fallback", "type": "bool", "description": "Wenn aktiv, bleibt MQTT die bevorzugte Quelle für SOC und Istleistung. Die lokale API aktualisiert den aktiven SOC nur dann, wenn MQTT fehlt oder veraltet ist. Sobald MQTT wieder gültige Werte liefert, wechselt die Anzeige automatisch zurück zu MQTT."},
    "ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS": {"group": "Netzwerk", "label": "Zendure lokale API Poll-Intervall", "type": "int", "min": 2, "max": 300, "unit": "s", "description": "Mindestabstand zwischen zwei lokalen Zendure-API-Abfragen für Telemetrie und Temperaturdiagnose."},
    "ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS": {"group": "Netzwerk", "label": "Zendure lokale API Fehler-Backoff", "type": "int", "min": 0, "max": 3600, "unit": "s", "description": "Pause nach einem Timeout oder Fehler der lokalen Zendure-API, bevor der Controller erneut /properties/report abfragt. Schützt EVCC und die Zendure-Headunit vor aggressiven Wiederholungen."},
    "ZENDURE_LOCAL_API_SOC_PRIORITY": {"group": "Netzwerk", "label": "Zendure lokale API SOC-Priorität", "type": "select", "options": {"properties_first": "properties.electricLevel bevorzugen", "pack_first": "packData[0].socLevel bevorzugen"}, "description": "Legt fest, welcher SOC-Wert aus /properties/report bevorzugt wird, falls sowohl properties.electricLevel als auch packData[0].socLevel vorhanden sind."},
    "MQTT_TOPIC_DIAGNOSTIC_ENABLED": {"group": "Netzwerk", "label": "MQTT Topic-Diagnose aktiv", "type": "bool", "description": "Wenn aktiv, abonniert das Script zusätzlich das konfigurierte Diagnose-Topic, standardmäßig Zendure/#, und zeigt die letzten MQTT-Nachrichten unter /mqtt-diagnostics an. Nur für Analysephasen empfohlen, weil dadurch mehr MQTT-Daten verarbeitet werden."},
    "MQTT_TOPIC_DIAGNOSTIC_FILTER": {"group": "Netzwerk", "label": "MQTT Topic-Diagnose Filter", "type": "str", "description": "MQTT-Topic-Filter für den Diagnosemitschnitt, z. B. Zendure/# oder evcc/#. MQTT Topic Matching ist groß-/kleinschreibungssensitiv; EVCC/# passt also nicht auf evcc/site/... . Änderungen an diesem Filter erfordern meist einen Neustart oder erneutes Speichern der Config."},
    "MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE": {"group": "Netzwerk", "label": "MQTT Diagnose Anzeige", "type": "select", "options": {"filtered": "Nur Diagnosefilter anzeigen", "all": "Alle empfangenen Controller-Topics anzeigen"}, "description": "filtered speichert/zeigt nur Nachrichten, die zum MQTT Topic-Diagnose Filter passen. all speichert alle vom Controller empfangenen MQTT-Nachrichten und ist nur für kurze Fehlersuche empfohlen."},
    "MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT": {"group": "Netzwerk", "label": "MQTT Topic-Diagnose Historie", "type": "int", "min": 10, "max": 5000, "description": "Anzahl der letzten MQTT-Diagnosemeldungen, die im RAM gehalten werden. Höhere Werte brauchen mehr Speicher, sind aber für Topic-Analyse hilfreich."},

    "INTERVAL_SECONDS": {"group": "Regelung", "label": "Regelintervall", "type": "int", "min": 1, "max": 30, "unit": "s", "description": "Zeit zwischen zwei Regelschritten. Kleinere Werte reagieren schneller, größere Werte laufen ruhiger."},
    "SLOW_CYCLE_WARN_MS": {"group": "Regelung", "label": "Warnschwelle langsamer Zyklus", "type": "int", "min": 1000, "max": 60000, "unit": "ms", "description": "Schreibt einen Runtime-Hinweis, wenn ein Reglerzyklus ohne Sleep länger dauert. Dient der RC3-Timingdiagnose."},
    "DEADBAND_W": {"group": "Regelung", "label": "Totzone", "type": "int", "min": 0, "max": 1000, "unit": "W", "description": "Bereich um 0 W Netzleistung, in dem die Leistung gehalten wird. Reduziert Pendeln und MQTT-Kommandos."},
    "MOVING_AVERAGE_SAMPLES": {"group": "Regelung", "label": "Mittelwertbildung", "type": "int", "min": 1, "max": 60, "description": "Anzahl der Messwerte im gleitenden Mittelwert. Höher = ruhiger, aber träger."},
    "SMOOTHING_FACTOR": {"group": "Regelung", "label": "Smoothing Factor", "type": "float", "min": 0.01, "max": 1.0, "step": 0.01, "description": "Zusätzliche Glättung der Zielwerte. 1.0 reagiert sofort, kleinere Werte sind weicher."},
    "MAX_POWER_STEP_W": {"group": "Regelung", "label": "Max Power Step", "type": "int", "min": 1, "max": 2400, "unit": "W", "description": "Maximale Änderung der Lade-/Entladeleistung pro Zyklus."},
    "MAX_DISCHARGE_POWER_W": {"group": "Regelung", "label": "Max Entladeleistung", "type": "int", "min": 0, "max": 2400, "unit": "W", "description": "Maximale Leistung, mit der Zendure das Haus versorgen darf."},
    "MAX_CHARGE_POWER_W": {"group": "Regelung", "label": "Max Ladeleistung", "type": "int", "min": 0, "max": 2400, "unit": "W", "description": "Maximale Leistung, mit der Zendure bei PV-Überschuss geladen werden darf."},
    "MIN_SOC_PERCENT": {"group": "Regelung", "label": "Min Zendure SOC", "type": "int", "min": 0, "max": 100, "unit": "%", "description": "Unterhalb dieses SOC wird Entladung verhindert."},
    "MAX_SOC_PERCENT": {"group": "Regelung", "label": "Max Zendure SOC", "type": "int", "min": 0, "max": 100, "unit": "%", "description": "Ab diesem SOC wird Ladung verhindert."},
    "CONTROL_GAIN": {"group": "Regelung", "label": "Control Gain", "type": "float", "min": 0.01, "max": 1.0, "step": 0.01, "description": "Reglerverstärkung. 0.30 bedeutet, dass nur 30 % der Abweichung pro Zyklus aufaddiert werden."},
    "MIN_COMMAND_CHANGE_W": {"group": "Regelung", "label": "Mindeständerung MQTT", "type": "int", "min": 0, "max": 500, "unit": "W", "description": "MQTT-Leistungsbefehle werden nur gesendet, wenn sich der Wert mindestens um diesen Betrag ändert. 0 deaktiviert die Optimierung."},
    "MODE_CHANGE_LOCK_SECONDS": {"group": "Regelung", "label": "Umschalt-Sperrzeit", "type": "int", "min": 0, "max": 120, "unit": "s", "description": "Mindestzeit vor direktem Wechsel zwischen Laden und Entladen. Verhindert hektisches Umschalten."},

    "MANUAL_MODE": {"group": "Manueller Modus", "label": "Manueller Betriebsmodus", "type": "select", "options": {"AUTO": "Automatik", "STOP_HOLD": "Stop/Hold", "FIXED_DISCHARGE": "Feste Entladung", "FIXED_CHARGE": "Feste Beladung"}, "description": "Automatik überlässt die Leistung der normalen Netz-/PV-Regelung. Stop/Hold setzt Lade- und Entladeleistung auf 0 W und hält diesen Zustand, bis hier wieder ein anderer Modus gespeichert wird. Feste Entladung oder Beladung übersteuern die Automatik bis zum eingestellten Ziel-SOC."},
    "MANUAL_FIXED_DISCHARGE_POWER_W": {"group": "Manueller Modus", "label": "Feste Entladeleistung", "type": "int", "min": 0, "max": 2400, "unit": "W", "description": "Leistung für den manuellen Modus Feste Entladung. Der Controller begrenzt diesen Wert zusätzlich auf die konfigurierte maximale Entladeleistung."},
    "MANUAL_FIXED_DISCHARGE_TARGET_SOC": {"group": "Manueller Modus", "label": "Entladen bis Zendure SOC", "type": "int", "min": 0, "max": 100, "unit": "%", "description": "Ziel-SOC für die feste Entladung. Zur Laufzeit wird dieser Wert mindestens auf den konfigurierten Min Zendure SOC angehoben, damit die allgemeine Akku-Schutzgrenze nicht unterschritten wird."},
    "MANUAL_DISCHARGE_AFTER_TARGET": {"group": "Manueller Modus", "label": "Nach Entlade-Ziel", "type": "select", "options": {"AUTO": "Automatik wieder aktivieren", "STOP_HOLD": "In Stop/Hold wechseln"}, "description": "Legt fest, was passiert, sobald der Ziel-SOC der festen Entladung erreicht ist. Automatik aktiviert wieder die normale Regelung; Stop/Hold setzt beide Leistungen auf 0 W und bleibt dort."},
    "MANUAL_FIXED_CHARGE_POWER_W": {"group": "Manueller Modus", "label": "Feste Ladeleistung", "type": "int", "min": 0, "max": 2400, "unit": "W", "description": "Leistung für den manuellen Modus Feste Beladung. Der Controller begrenzt diesen Wert zusätzlich auf die konfigurierte maximale Ladeleistung."},
    "MANUAL_FIXED_CHARGE_TARGET_SOC": {"group": "Manueller Modus", "label": "Laden bis Zendure SOC", "type": "int", "min": 0, "max": 100, "unit": "%", "description": "Ziel-SOC für die feste Beladung. Zur Laufzeit wird dieser Wert höchstens auf den konfigurierten Max Zendure SOC abgesenkt, damit die allgemeine obere Akku-Grenze eingehalten wird."},
    "MANUAL_CHARGE_AFTER_TARGET": {"group": "Manueller Modus", "label": "Nach Lade-Ziel", "type": "select", "options": {"AUTO": "Automatik wieder aktivieren", "STOP_HOLD": "In Stop/Hold wechseln"}, "description": "Legt fest, was passiert, sobald der Ziel-SOC der festen Beladung erreicht ist. Automatik aktiviert wieder die normale Regelung; Stop/Hold setzt beide Leistungen auf 0 W und bleibt dort."},
    "COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS": {"group": "Regelung", "label": "Zendure-Command-Resync bei jeder MQTT-Recovery", "type": "bool", "description": "Notfall-/Legacy-Schalter: erzwingt Resync bei jeder Zendure-MQTT-Recovery. Standard in V12.11.2-RC1 ist aus, damit kurze STALE-Phasen keinen Resync-Sturm auslösen."},
    "COMMAND_RESYNC_STALE_MIN_SECONDS": {"group": "Regelung", "label": "Resync ab Stale-Dauer", "type": "int", "min": 3, "max": 600, "unit": "s", "description": "Mindestdauer eines unsicheren Zendure-MQTT-Zustands, bevor Recovery einen Command-Resync auslöst."},
    "COMMAND_RESYNC_STALE_MIN_CYCLES": {"group": "Regelung", "label": "Resync ab Stale-Zyklen", "type": "int", "min": 1, "max": 100, "unit": "Zyklen", "description": "Mindestanzahl aufeinanderfolgender unsicherer Zyklen, bevor ein Recovery-Resync als belastbar gilt."},
    "COMMAND_RESYNC_COOLDOWN_SECONDS": {"group": "Regelung", "label": "Resync-Cooldown", "type": "int", "min": 0, "max": 1800, "unit": "s", "description": "Unterdrückt identische Resync-Wiederholungen im Cooldown, außer bei weiter bestätigtem Mismatch nach Ablauf des Cooldowns."},
    "COMMAND_EFFECT_MIN_TARGET_W": {"group": "Regelung", "label": "Mindest-Sollwert für Wirksamkeitsdiagnose", "type": "int", "min": 0, "max": 500, "unit": "W", "description": "Unterhalb dieser Schwelle ist die physische Wirkung nicht belastbar bewertbar; der Zustand wird nicht als COMMAND_EFFECTIVE ausgegeben."},
    "COMMAND_EFFECT_MIN_W": {"group": "Regelung", "label": "Mindest-Istleistung für Richtungsreaktion", "type": "int", "min": 30, "max": 500, "unit": "W", "description": "Schwellwert, ab dem eine unabhängige Istleistungsbeobachtung als belastbare Reaktion in Lade- oder Entladerichtung gilt. Das beweist noch kein vollständiges Sollwerttracking."},
    "COMMAND_EFFECT_TOLERANCE_W": {"group": "Regelung", "label": "Soll/Ist-Toleranz für Zielwerttracking", "type": "int", "min": 10, "max": 500, "unit": "W", "description": "Toleranz, innerhalb derer der aktuelle Sollwert und eine belastbare unabhängige Istleistungsbeobachtung als nachgeführt gelten."},
    "COMMAND_EFFECT_TIMEOUT_SECONDS": {"group": "Regelung", "label": "Warnzeit für fehlende oder unzureichende Wirkung", "type": "int", "min": 10, "max": 600, "unit": "s", "description": "Nach dieser zusammenhängenden Zeit desselben Lade-/Entlade-Intents bestätigt ZEC fehlende Richtungsreaktion oder dauerhaft erhebliches Untertracking. Kleine Wattänderungen derselben Richtung starten die Zeit nicht neu."},
    "COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS": {"group": "Regelung", "label": "Prüfzeit für 0-W-Neutralisierung", "type": "int", "min": 5, "max": 300, "unit": "s", "description": "Nach dieser Zeit muss eine sicherheitsrelevante 0-W-Neutralisierung physisch bestätigt sein. Bei fortbestehender Leistung sendet ZEC AC-Modus sowie beide Limits als Full-State-Neutralisierung erneut."},
    "ZENDURE_COMMAND_STATE_FRESH_SECONDS": {"group": "Regelung", "label": "Gültigkeit Zendure-Command-State", "type": "int", "min": 5, "max": 300, "unit": "s", "description": "Maximales Alter der rückgelesenen Werte smartMode, acMode, inputLimit und outputLimit. Dynamische Limitänderungen werden nur bei bestätigtem smartMode=1 freigegeben."},
    "ZENDURE_SMART_MODE_RETRY_SECONDS": {"group": "Regelung", "label": "Wiederholintervall Flash-Schutz", "type": "int", "min": 5, "max": 600, "unit": "s", "description": "Mindestabstand für erneutes smartMode=ON, wenn der volatile Flash-Schutz noch nicht rückgelesen wurde."},
    "ZENDURE_COMMAND_STATE_RETRY_SECONDS": {"group": "Regelung", "label": "Wiederholintervall vollständiger Command-State", "type": "int", "min": 5, "max": 600, "unit": "s", "description": "Mindestabstand für einen erneuten vollständigen Modus-/Limit-Abgleich, solange die Rücklesung noch nicht konsistent ist."},
    "COMMAND_EFFECT_FORCE_RESEND_SECONDS": {"group": "Regelung", "label": "Resend-Zeit bei anhaltender Nichtwirkung", "type": "int", "min": 30, "max": 900, "unit": "s", "description": "Nach dieser Zeit sendet ZEC einen weiterhin unwirksamen aktiven Sollzustand vollständig erneut. Resync-Versand und anschließend bestätigte Gerätewirkung werden getrennt dokumentiert."},

    "CROSS_CHARGE_ENABLED": {"group": "Zweitbatterie", "subgroup": "Cross-Charge-Schutz", "label": "Cross-Charge-Schutz aktiv", "type": "bool", "description": "Aktiviert das Einlesen einer externen Zusatzbatterie per MQTT und verhindert unerwünschtes Batterie-zu-Batterie-Laden."},
    "SECOND_BATTERY_DISPLAY_NAME": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Zusatzbatterie Anzeigename", "type": "str", "description": "Freier Anzeigename der externen Batterie auf Statusseite, Graph und CSV-Beschreibungen, z. B. SMA Sunny Island, Victron ESS oder Hausspeicher Keller."},
    "SECOND_BATTERY_SOURCE_PROFILE": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Datenquellen-Profil", "type": "select", "options": {"evcc_standard": "EVCC Standard", "custom": "Benutzerdefiniert"}, "description": "EVCC Standard ist eine Komfort-Vorlage: aus dem Basis-Topic werden /power, /soc und /capacity gebildet. Benutzerdefiniert erlaubt vollständig frei angegebene Einzel-Topics und optionale JSON-Feldpfade."},
    "SECOND_BATTERY_EVCC_BASE_TOPIC": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "EVCC Batterie-Basis-Topic", "type": "str", "description": "Basis-Topic der Zusatzbatterie bei EVCC-Standardstruktur, z. B. evcc/site/battery/devices/1. Daraus werden Leistung, SOC und Kapazität automatisch als /power, /soc und /capacity abgeleitet.", "cross_profile": "evcc"},
    "SECOND_BATTERY_POWER_TOPIC": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Leistungs-Topic", "type": "str", "description": "Vollständiges MQTT-Topic der Zusatzbatterie-Leistung. Dieses Topic ist im benutzerdefinierten Profil Pflicht, weil der Cross-Charge-Schutz primär aus der Leistung erkennt, ob die Zusatzbatterie entlädt.", "cross_profile": "custom"},
    "SECOND_BATTERY_SOC_TOPIC": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "SOC-Topic", "type": "str", "description": "Optionales MQTT-Topic für den Ladezustand der Zusatzbatterie in Prozent. Der Schutz kann auch ohne SOC arbeiten; die Anzeige zeigt dann 'nicht konfiguriert'.", "cross_profile": "custom"},
    "SECOND_BATTERY_CAPACITY_TOPIC": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Kapazitäts-Topic", "type": "str", "description": "Optionales MQTT-Topic für die Zusatzbatterie-Kapazität. Die Kapazität dient Anzeige und Diagnose, ist aber nicht zwingend für die Schutzentscheidung erforderlich.", "cross_profile": "custom"},
    "SECOND_BATTERY_POWER_PAYLOAD_TYPE": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Leistungs-Payload", "type": "select", "options": {"number": "Zahl direkt", "json": "JSON mit Feldpfad"}, "description": "Gibt an, ob das Leistungs-Topic direkt eine Zahl enthält oder ein JSON-Objekt liefert.", "cross_profile": "custom"},
    "SECOND_BATTERY_POWER_JSON_PATH": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Leistung JSON-Feldpfad", "type": "str", "description": "Feldpfad innerhalb eines JSON-Payloads, z. B. power oder battery.power. Nur relevant, wenn Leistungs-Payload = JSON gewählt ist.", "cross_profile": "custom"},
    "SECOND_BATTERY_SOC_PAYLOAD_TYPE": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "SOC-Payload", "type": "select", "options": {"number": "Zahl direkt", "json": "JSON mit Feldpfad"}, "description": "Gibt an, ob das SOC-Topic direkt eine Zahl enthält oder ein JSON-Objekt liefert.", "cross_profile": "custom"},
    "SECOND_BATTERY_SOC_JSON_PATH": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "SOC JSON-Feldpfad", "type": "str", "description": "Feldpfad innerhalb eines JSON-Payloads, z. B. soc oder battery.soc. Nur relevant, wenn SOC-Payload = JSON gewählt ist.", "cross_profile": "custom"},
    "SECOND_BATTERY_CAPACITY_PAYLOAD_TYPE": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Kapazitäts-Payload", "type": "select", "options": {"number": "Zahl direkt", "json": "JSON mit Feldpfad"}, "description": "Gibt an, ob das Kapazitäts-Topic direkt eine Zahl enthält oder ein JSON-Objekt liefert.", "cross_profile": "custom"},
    "SECOND_BATTERY_CAPACITY_JSON_PATH": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Kapazität JSON-Feldpfad", "type": "str", "description": "Feldpfad innerhalb eines JSON-Payloads, z. B. capacity oder battery.capacity. Nur relevant, wenn Kapazitäts-Payload = JSON gewählt ist.", "cross_profile": "custom"},
    "SECOND_BATTERY_POWER_UNIT": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Leistungseinheit", "type": "select", "options": {"W": "W", "kW": "kW"}, "description": "Einheit des Leistungswerts der Zusatzbatterie. Intern wird immer auf Watt normalisiert."},
    "SECOND_BATTERY_CAPACITY_UNIT": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Kapazitätseinheit", "type": "select", "options": {"kWh": "kWh", "Wh": "Wh"}, "description": "Einheit des Kapazitätswerts der Zusatzbatterie. Die Statusseite zeigt den Wert in kWh an."},
    "SECOND_BATTERY_DISCHARGE_SIGN": {"group": "Zweitbatterie", "subgroup": "Zweitbatterie-Messwerte", "label": "Zusatzbatterie Entlade-Vorzeichen", "type": "int", "min": -1, "max": 1, "description": "+1 bedeutet: positive MQTT-Leistung = Zusatzbatterie entlädt. -1 bedeutet: negative MQTT-Leistung = Zusatzbatterie entlädt. Die Statusanzeige normiert danach auf positiv = Ladung, negativ = Entladung."},
    "SMA_DISCHARGE_BLOCK_W": {"group": "Zweitbatterie", "subgroup": "Cross-Charge-Schutz", "label": "Entlade-Blockgrenze (Legacy)", "type": "int", "min": 0, "max": 5000, "unit": "W", "hidden": True, "description": "Legacy-Wert nur für Migration/Kompatibilität. Neue Installationen verwenden Cross-Charge-Signifikanzschwelle; dieses Feld wird nicht mehr in der normalen Settings-UI angezeigt."},
    "CROSS_CHARGE_SIGNIFICANT_W": {"group": "Zweitbatterie", "subgroup": "Cross-Charge-Schutz", "label": "Cross-Charge-Signifikanzschwelle", "type": "int", "min": 0, "max": 5000, "unit": "W", "description": "Ab diesem gegenläufigen Leistungsfluss zwischen Zusatzbatterie und Zendure wird der Cross-Charge-Schutz aktiv. Eine interne niedrigere Freigabeschwelle verhindert hektisches Ein-/Ausschalten."},
    "CROSS_CHARGE_RESERVE_W": {"group": "Zweitbatterie", "subgroup": "Cross-Charge-Schutz", "label": "Cross-Charge Reserve", "type": "int", "min": 0, "max": 1000, "unit": "W", "description": "Sicherheitsreserve, die vom sichtbaren Überschuss abgezogen wird, bevor Zendure lädt."},
    "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W": {"group": "Zweitbatterie", "subgroup": "Cross-Charge-Schutz", "label": "Mindest-Überschuss für Ladung", "type": "int", "min": 0, "max": 2000, "unit": "W", "description": "Zendure lädt nur, wenn nach Zusatzbatterie-Abzug und Reserve mindestens dieser Überschuss übrig bleibt."},
    "SMA_GUARD_RAMP_DOWN_W": {"group": "Zweitbatterie", "subgroup": "Cross-Charge-Schutz", "label": "Cross-Charge Ramp-Down", "type": "int", "min": 1, "max": 2400, "unit": "W", "description": "Schrittweite, mit der Zendure-Ladung reduziert wird, wenn der Cross-Charge-Schutz blockiert."},
    "SECOND_BATTERY_STALE_TIMEOUT_SECONDS": {"group": "Zweitbatterie", "subgroup": "Cross-Charge-Schutz", "label": "Daten-Timeout", "type": "int", "min": 5, "max": 600, "unit": "s", "description": "Nach dieser Zeit ohne Update auf einem konfigurierten Zusatzbatterie-MQTT-Topic gelten die Daten als veraltet. Je kleiner der Wert, desto schneller reagiert der Schutz auf fehlende Daten; je größer der Wert, desto toleranter ist das System gegenüber kurzen MQTT-Aussetzern."},
    "SECOND_BATTERY_STALE_BLOCK_CHARGE": {"group": "Zweitbatterie", "subgroup": "Cross-Charge-Schutz", "label": "Bei Daten-Timeout Ladung blockieren", "type": "bool", "description": "Konservativer Fallback: Wenn der Cross-Charge-Schutz aktiv ist, aber keine frischen Zusatzbatteriedaten vorliegen, wird Zendure-Ladung blockiert."},
    "REST_SURPLUS_HARVEST_ENABLED": {"group": "Zweitbatterie", "subgroup": "Restüberschuss-Ernte", "label": "Restüberschuss-Ernte aktivieren", "type": "bool", "description": "Aktiviert eine spezielle AUTO-Funktion: Wenn der Primärspeicher über längere Zeit nahe seiner Ladegrenze lädt und trotzdem Netzexport übrig bleibt, darf Zendure diesen Restüberschuss zusätzlich laden. Die Funktion startet nicht bei kurzen Spitzen und darf nur laden, niemals Entladung auslösen."},
    "SECOND_BATTERY_MAX_CHARGE_POWER_W": {"group": "Zweitbatterie", "subgroup": "Restüberschuss-Ernte", "label": "Maximale Ladeleistung Primärspeicher", "type": "optional_int", "min": 300, "max": 10000, "unit": "W", "description": "Maximale Ladeleistung des Primärspeichers bzw. der Zweitbatterie. Dieser Wert steht meist im Datenblatt des Wechselrichters/Batteriesystems. Leer bedeutet: Restüberschuss-Ernte bleibt nicht wirksam. Für SMA Sunny Island 3.0M-11 sind aus ZEC-Sicht 2300 W passend."},
    "REST_SURPLUS_MIN_EXPORT_W": {"group": "Zweitbatterie", "subgroup": "Restüberschuss-Ernte", "label": "Mindest-Netzexport zur Aktivierung", "type": "int", "min": 20, "max": 1000, "unit": "W", "description": "Mindestexport am Netzanschlusspunkt, ab dem die Restüberschuss-Ernte für den Entry qualifiziert. Dieser Wert ist nur eine Aktivierungs-/Rauschschwelle, kein dauerhaft gewünschter Restexport. Default: 80 W."},

    "NIGHT_DISCHARGE_ENABLED": {"group": "Nachtmodus", "label": "Nachtmodus aktiv", "type": "bool", "description": "Aktiviert eine feste Entladeleistung im konfigurierten Zeitfenster."},
    "NIGHT_START_HOUR": {"group": "Nachtmodus", "label": "Start Stunde", "type": "int", "min": 0, "max": 23, "description": "Startstunde des Nachtmodus."},
    "NIGHT_START_MINUTE": {"group": "Nachtmodus", "label": "Start Minute", "type": "int", "min": 0, "max": 59, "description": "Startminute des Nachtmodus."},
    "NIGHT_END_HOUR": {"group": "Nachtmodus", "label": "Ende Stunde", "type": "int", "min": 0, "max": 23, "description": "Endstunde des Nachtmodus."},
    "NIGHT_END_MINUTE": {"group": "Nachtmodus", "label": "Ende Minute", "type": "int", "min": 0, "max": 59, "description": "Endminute des Nachtmodus. Wird in der Weboberfläche zusammen mit der Stunde als hh:mm-Feld dargestellt."},
    "NIGHT_DISCHARGE_POWER_W": {"group": "Nachtmodus", "label": "Nachtleistung", "type": "int", "min": 0, "max": 2400, "unit": "W", "description": "Feste Entladeleistung im Nachtmodus."},
    "NIGHT_DISCHARGE_STOP_SOC_PERCENT": {"group": "Nachtmodus", "label": "Nachtmodus Reserve-SOC", "type": "optional_int", "min": 0, "max": 100, "unit": "%", "description": "Optionaler Reserve-/Stop-SOC für die Nachtentladung. Leer lassen für bisheriges Verhalten. Wenn gesetzt, stoppt die Nachtentladung bei SOC kleiner/gleich diesem Wert. Steigt der SOC später wieder über diesen Wert, darf die Nachtentladung im selben Nachtfenster wieder laufen. Der Wert muss mindestens dem globalen Mindest-SOC entsprechen."},
    "ZENDURE_BATTERY_CAPACITY_WH": {"group": "Nachtmodus", "label": "Zendure Batteriekapazität für Prognose", "type": "optional_int", "min": 100, "max": 50000, "unit": "Wh", "description": "Gesamtkapazität der Zendure-Batterien in Wh für die Nachtmodus-Prognose. Leer = Prognose nicht berechenbar. Beispiel: 5280 Wh bei 2,4 kWh Headunit plus 2,88 kWh Erweiterung."},

    "MAX_CONSECUTIVE_ERRORS": {"group": "Sicherheit / Fallback", "label": "Max Fehler in Folge", "type": "int", "min": 1, "max": 100, "description": "Nach dieser Anzahl direkt aufeinanderfolgender Fehler aktiviert der Controller den Safe-State. Safe-State bedeutet: Ladeleistung und Entladeleistung werden per MQTT auf 0 W gesetzt, der Modus wird auf SAFE_STATE gestellt und die Regelung versucht nicht weiter aktiv Leistung zu verschieben, bis wieder gültige Daten vorliegen und der nächste Regelzyklus sauber laufen kann."},
    "SHELLY_STALE_TIMEOUT_SECONDS": {"group": "Sicherheit / Fallback", "label": "Shelly Timeout", "type": "int", "min": 5, "max": 600, "unit": "s", "description": "Maximales Alter des letzten gültigen Netzleistungswerts."},
    "SOC_STALE_TIMEOUT_SECONDS": {"group": "Sicherheit / Fallback", "label": "SOC Timeout", "type": "int", "min": 10, "max": 3600, "unit": "s", "description": "Maximales Alter des Zendure-SOC. Bei Überschreitung wird Entladung blockiert."},
    "MQTT_DISCONNECTED_SAFE_STATE": {"group": "Sicherheit / Fallback", "label": "Safe-State bei MQTT-Trennung", "type": "bool", "description": "Wenn aktiv, setzt der Controller bei erkannter MQTT-Trennung Lade- und Entladeleistung auf 0 W. Das ist die konservativste Variante, weil ohne MQTT keine zuverlässigen neuen Befehle und teilweise keine aktuellen Rückmeldungen möglich sind. Wenn diese Option nicht aktiv ist, läuft die Logik weiter und zeigt den MQTT-Fehler an; bereits zuletzt an Zendure gesendete Werte können dort aber weiter gültig bleiben, weil der Controller sie während der Trennung nicht sicher ändern kann. Nicht aktiv ist daher toleranter bei kurzen Broker-Aussetzern, aber weniger sicher bei längeren MQTT-Problemen."},
    "ZENDURE_POWER_STALE_TIMEOUT_SECONDS": {"group": "Sicherheit / Fallback", "label": "Zendure Istwert Timeout", "type": "int", "min": 10, "max": 3600, "unit": "s", "description": "Alter der Zendure-Istleistungswerte, ab dem eine Warnung gesetzt wird."},
    "ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS": {"group": "Sicherheit / Fallback", "label": "Zendure MQTT Live-Timeout", "type": "int", "min": 10, "max": 3600, "unit": "s", "description": "Maximales Alter kritischer Zendure-MQTT-Gruppen für die Live-/Partial-Stale-Diagnose. Warnungen verschwinden automatisch, sobald wieder frische nicht-retained Live-Werte eintreffen."},
    "ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS": {"group": "Sicherheit / Fallback", "label": "Zendure MQTT Neustart-Toleranz", "type": "int", "min": 10, "max": 3600, "unit": "s", "description": "Wartezeit nach MQTT-Reconnect/Broker-Neustart, bevor fehlende nicht-retained Live-Werte als Neustart-/App-Neuspeicherproblem gemeldet werden."},
    "SAFE_STATE_ON_SHELLY_ERROR": {"group": "Sicherheit / Fallback", "label": "Safe-State bei Shelly-Fehlern", "type": "bool", "description": "Wenn aktiv, fährt der Controller bei anhaltenden Messfehlern auf 0 W."},

    "GRAPH_HISTORY_LIMIT": {"group": "Messdaten / Historie", "label": "Graph-Historie", "type": "int", "min": 50, "max": 5000, "description": "Anzahl der im RAM gehaltenen Graph-Datenpunkte. Diese Historie ist unabhängig vom dauerhaften Messdaten-Logging."},
    "MEASUREMENT_LOG_MODE": {"group": "Messdaten / Historie", "label": "Messdaten-Logging", "type": "select", "options": {"off": "Aus", "standard": "Standard", "extended": "Erweitert"}, "description": "Aus: keine zyklischen Messdaten, schont die SD-Karte. Standard: vollständige Reglerdiagnose inklusive Freshness, MQTT-Stale-Aggregat, Sollwertkaskade, Kommando und Szenario ohne Zendure. Erweitert: Standard plus Detaildaten für Simulation, What-if und tiefe MQTT-/Freshness-Analyse; erzeugt größere Dateien und sollte gezielt genutzt werden."},
    "MEASUREMENT_SCHEMA_VERSION": {"group": "Messdaten / Historie", "label": "Measurement-Schema", "type": "select", "options": {"4": "ZEC-MEASUREMENT-V4", "3": "Legacy V3"}, "description": "Legt das dauerhafte Measurement-Schema fest. V4 schreibt separate V4-CSV-Dateien plus Manifest, Config-Snapshots und Runtime-JSONL. Legacy V3 bleibt für Rollback/Altanalyse verfügbar."},
    "MEASUREMENT_DB_ENABLED": {"group": "Messdaten / Historie", "label": "SQLite-Graphspeicher", "type": "bool", "description": "Schreibt parallel zu CSV/V4 einen leichten SQLite-Store für schnelle Status- und Graphdaten. Läuft auch, wenn Messdaten-CSV deaktiviert ist; die Regelung wird bei DB-Fehlern nicht blockiert."},
    "MEASUREMENT_DB_FILE": {"group": "Messdaten / Historie", "label": "SQLite-Datei", "type": "str", "description": "Dateiname des SQLite-Graphspeichers im aktiven Messdatenverzeichnis, sofern kein absoluter SQLite-Pfad gesetzt ist."},
    "MEASUREMENT_DB_PATH": {"group": "Messdaten / Historie", "label": "SQLite-Pfad optional", "type": "str", "description": "Optionaler absoluter Pfad zur SQLite-Datei. Leer bedeutet: automatisch neben den Messdaten im aktiven Speicherziel."},
    "MEASUREMENT_DB_MAX_QUEUE_ROWS": {"group": "Messdaten / Historie", "label": "SQLite Queue-Größe", "type": "int", "min": 100, "max": 50000, "description": "Maximale Anzahl gepufferter DB-Messpunkte. Bei voller Queue wird verworfen statt die Regelung zu blockieren."},
    "MEASUREMENT_LOG_STORAGE_TARGET": {"group": "Messdaten / Historie", "label": "Speicherziel", "type": "select", "options": {"internal_sd": "Interne SD-Karte", "external_mount": "erkannter USB-/Mountpoint", "custom_path": "benutzerdefinierter Pfad"}, "description": "Legt fest, wo Messdaten primär geschrieben werden. Bei erkanntem USB-/Mountpoint wird ein schreibbarer externer Mount automatisch verwendet; das Feld USB-/Mountpoint kann optional einen bestimmten Mountpoint festlegen."},
    "MEASUREMENT_LOG_MOUNTPOINT": {"group": "Messdaten / Historie", "label": "USB-/Mountpoint", "type": "str", "description": "Optionaler Mountpoint für externes Messdaten-Logging, z. B. /media/pi/USBSTICK oder /mnt/zec-logs. Wenn leer, wird bei Speicherziel external_mount ein erkannter schreibbarer USB-/Mountpoint automatisch verwendet."},
    "MEASUREMENT_LOG_DIR": {"group": "Messdaten / Historie", "label": "Messdaten-Verzeichnis / Custom-Pfad", "type": "str", "description": "Verzeichnis für ZEC-MEASUREMENT-Messdaten. Bei internal_sd/custom_path wird dieses Feld direkt verwendet. Bei external_mount wird es als Unterordner auf dem USB-/Mountpoint verwendet, z. B. USB + ZEC/logs."},
    "MEASUREMENT_LOG_FILE": {"group": "Messdaten / Historie", "label": "Messdaten-Datei", "type": "str", "description": "Dateiname der aktuellen Measurement-Datei. Bei V4 und Standardname schreibt der Controller automatisch zendure_measurements_v4.csv, damit V3 und V4 nicht gemischt werden."},
    "MEASUREMENT_LOG_MAX_BYTES": {"group": "Messdaten / Historie", "label": "Max Dateigröße", "type": "int", "min": 100_000, "max": 100_000_000, "unit": "Bytes", "description": "Bei Überschreitung wird rotiert. Zusammen mit der Dateianzahl bestimmt dieser Wert die geschätzte Aufbewahrung."},
    "MEASUREMENT_LOG_BACKUP_COUNT": {"group": "Messdaten / Historie", "label": "Rotationsdateien", "type": "int", "min": 1, "max": 20, "description": "Anzahl der Messdaten-Dateien, die rollierend behalten werden. Höhere Werte verlängern die analysierbare Historie, benötigen aber mehr Speicherplatz."},
    "MEASUREMENT_LOG_MIN_FREE_DISK_MB": {"group": "Messdaten / Historie", "label": "Mindestfreier Speicher", "type": "int", "min": 100, "max": 100000, "unit": "MB", "description": "Mindestfreier Speicher am aktuell aktiven Messdatenziel: interne SD, externer USB-/Mountpoint oder bei aktivem Fallback der SD-Fallback-Pfad. Wenn weniger Speicher frei ist, pausiert das Messdaten-Logging; die Regelung läuft weiter."},
    "MEASUREMENT_LOG_ESTIMATED_ROW_BYTES": {"group": "Messdaten / Historie", "label": "Schätzgröße je Messpunkt", "type": "int", "min": 500, "max": 50000, "unit": "Bytes", "description": "Nur für die grobe Aufbewahrungsschätzung. Für V4-Standard ist der Standardwert anhand realer Logs praxisnah bemessen; Extended-Dateien können je nach JSON-Detailgrad größer sein."},
    "MEASUREMENT_LOG_FLUSH_EVERY_ROWS": {"group": "Messdaten / Historie", "label": "Flush alle X Zeilen", "type": "int", "min": 1, "max": 10000, "description": "Schreibt gepufferte Messdaten periodisch aus dem Python-Puffer. Kein hartes fsync pro Zeile; bei Stromausfall können letzte Messdaten fehlen."},
    "MEASUREMENT_LOG_FLUSH_EVERY_SECONDS": {"group": "Messdaten / Historie", "label": "Flush alle X Sekunden", "type": "int", "min": 1, "max": 3600, "unit": "s", "description": "Zeitbasierte Flush-Grenze für gepuffertes Logging. Reduziert kleine Sync-Schreibvorgänge gegenüber hartem Schreiben pro Messpunkt."},
    "MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_ROWS": {"group": "Messdaten / Historie", "label": "V4 Manifest-Update nach Zeilen", "type": "int", "min": 1, "max": 1000, "unit": "Zeilen", "description": "Schreibt das V4-Manifest gepuffert statt pro Zyklus. Niedrigere Werte sind aktueller, höhere Werte reduzieren I/O."},
    "MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_SECONDS": {"group": "Messdaten / Historie", "label": "V4 Manifest-Update spätestens nach Sekunden", "type": "int", "min": 5, "max": 600, "unit": "s", "description": "Spätester gepufferter V4-Manifest-Update. Beim Schließen wird immer final aktualisiert."},
    "MEASUREMENT_LOG_ALLOW_SD_FALLBACK": {"group": "Messdaten / Historie", "label": "SD-Fallback bei USB-Ausfall", "type": "bool", "description": "Wenn das externe Speicherziel nicht verfügbar ist, darf begrenzt auf die interne SD geschrieben werden. Der Fallback wird sichtbar markiert und enger rotiert."},
    "MEASUREMENT_LOG_FALLBACK_DIR": {"group": "Messdaten / Historie", "label": "SD-Fallback-Verzeichnis", "type": "str", "description": "Begrenztes Fallback-Verzeichnis auf der internen SD, falls ein externes Logziel ausfällt."},
    "MEASUREMENT_LOG_FALLBACK_MAX_BYTES": {"group": "Messdaten / Historie", "label": "Fallback Max Dateigröße", "type": "int", "min": 100_000, "max": 100_000_000, "unit": "Bytes", "description": "Kleinere Rotationsgrenze für den SD-Fallback, damit ein USB-Ausfall die SD nicht unbegrenzt belastet."},
    "MEASUREMENT_LOG_FALLBACK_BACKUP_COUNT": {"group": "Messdaten / Historie", "label": "Fallback Rotationsdateien", "type": "int", "min": 1, "max": 10, "description": "Anzahl der Fallback-Dateien auf SD. Bewusst kleiner halten als das primäre USB-Ziel."},

    "ANALYSIS_MAX_FILES": {"group": "Analyse / Replay", "label": "Analyse Pi-Safe Dateien", "type": "int", "min": 1, "max": 20, "description": "Maximale Dateianzahl für normale lokale Analysen auf dem Raspberry Pi. Standard ist bewusst konservativ, um EVCC, MQTT und Live-Regler zu schützen."},
    "ANALYSIS_MAX_TOTAL_BYTES": {"group": "Analyse / Replay", "label": "Analyse Pi-Safe Gesamtgröße", "type": "int", "min": 1_000_000, "max": 100_000_000, "unit": "Bytes", "description": "Maximale Gesamtgröße der ausgewählten CSV-Dateien für normale lokale Analysen. Standard ist bewusst konservativ, weil Python-/HTML-/Diagrammstrukturen deutlich mehr RAM benötigen als die CSV-Datei auf der SD-Karte."},
    "ANALYSIS_MAX_ROWS": {"group": "Analyse / Replay", "label": "Analyse Pi-Safe Messpunkte", "type": "int", "min": 1_000, "max": 500_000, "description": "Maximale Messpunktzahl für normale lokale Analysen. Das Limit wird bereits beim Lesen geprüft; zusätzlich läuft die Analyse in einem isolierten Worker."},
    "ANALYSIS_EXTENDED_MAX_FILES": {"group": "Analyse / Replay", "label": "Analyse Extended Dateien", "type": "int", "min": 1, "max": 20, "description": "Erweiterte Dateianzahl für bewusst bestätigte größere Analysen. Auf dem Raspberry Pi nur mit Warnung verwenden."},
    "ANALYSIS_EXTENDED_MAX_TOTAL_BYTES": {"group": "Analyse / Replay", "label": "Analyse Extended Gesamtgröße", "type": "int", "min": 1_000_000, "max": 100_000_000, "unit": "Bytes", "description": "Erweiterte Gesamtgröße für bewusst bestätigte größere Analysen. Alles darüber wird lokal abgelehnt und sollte offline/auf dem PC analysiert werden."},
    "ANALYSIS_EXTENDED_MAX_ROWS": {"group": "Analyse / Replay", "label": "Analyse Extended Messpunkte", "type": "int", "min": 1_000, "max": 500_000, "description": "Erweiterte Messpunktzahl für bewusst bestätigte größere Analysen. Alles darüber wird fail-closed abgelehnt."},
    "ANALYSIS_WORKER_MEMORY_LIMIT_MB": {"group": "Analyse / Replay", "label": "Analyse Worker Speicherlimit", "type": "int", "min": 128, "max": 900, "unit": "MB", "description": "Speicherlimit für normale Analyse-Worker. Bei Überschreitung wird nur der Analyse-Worker beendet, nicht der Live-Controller."},
    "ANALYSIS_EXTENDED_WORKER_MEMORY_LIMIT_MB": {"group": "Analyse / Replay", "label": "Analyse Extended Speicherlimit", "type": "int", "min": 128, "max": 900, "unit": "MB", "description": "Speicherlimit für bewusst bestätigte größere Analyse-Worker."},
    "ANALYSIS_WORKER_TIMEOUT_SECONDS": {"group": "Analyse / Replay", "label": "Analyse Timeout", "type": "int", "min": 30, "max": 1800, "unit": "s", "description": "Zeitlimit für normale Analyse-Worker. Bei Überschreitung wird der Worker abgebrochen."},
    "ANALYSIS_EXTENDED_WORKER_TIMEOUT_SECONDS": {"group": "Analyse / Replay", "label": "Analyse Extended Timeout", "type": "int", "min": 30, "max": 3600, "unit": "s", "description": "Zeitlimit für bewusst bestätigte größere Analyse-Worker."},

    "FILE_LOG_ENABLED": {"group": "Logging", "label": "Datei-Logging aktiv", "type": "bool", "description": "Schreibt Betriebs-, Fehler- und Diagnosemeldungen zusätzlich rollierend in eine Text-Logdatei. Das ersetzt nicht das CSV-Datenlogging."},
    "FILE_LOG_DIR": {"group": "Logging", "label": "Datei-Log Verzeichnis", "type": "str", "description": "Relatives oder absolutes Verzeichnis für die Text-Logdatei."},
    "FILE_LOG_FILE": {"group": "Logging", "label": "Datei-Log Dateiname", "type": "str", "description": "Dateiname der aktuellen Runtime-Text-Logdatei, standardmäßig zendure_runtime.log."},
    "FILE_LOG_MAX_BYTES": {"group": "Logging", "label": "Max Datei-Log Größe", "type": "int", "min": 100_000, "max": 100_000_000, "unit": "Bytes", "description": "Bei Überschreitung wird die Text-Logdatei rotiert. Alte Dateien werden nach dem Schema zendure_runtime_1.log, zendure_runtime_2.log usw. gehalten."},
    "FILE_LOG_BACKUP_COUNT": {"group": "Logging", "label": "Datei-Log Backup-Dateien", "type": "int", "min": 1, "max": 10, "description": "Anzahl alter Text-Logdateien, die behalten werden."},
    "DEBUG": {"group": "Logging", "label": "Debug Logging", "type": "bool", "description": "Allgemeine Konsolenausgaben."},
    "LOG_VALUES": {"group": "Logging", "label": "Werte loggen", "type": "bool", "description": "Loggt Shelly-Rohwert und geglättete Netzleistung."},
    "LOG_CONTROL": {"group": "Logging", "label": "Regelentscheidungen ins Textlog schreiben (Debug)", "type": "bool", "description": "Schreibt zusätzliche menschenlesbare Debug-Meldungen zu Zielwerten und Regelentscheidungen ins Runtime-Textlog. Das ist kein strukturiertes Measurement-Logging; die V4-Standard-Messdaten enthalten die Reglerdiagnose bereits."},
    "LOG_MANUAL": {"group": "Logging", "label": "Manuellen Modus loggen", "type": "bool", "description": "Loggt Aktionen des manuellen Modus, z. B. Start, Ziel erreicht und automatische Umschaltung nach Ziel-SOC."},
    "LOG_MQTT": {"group": "Logging", "label": "MQTT loggen", "type": "bool", "description": "Loggt MQTT-Kommandos an Zendure."},
    "LOG_SOC": {"group": "Logging", "label": "SOC loggen", "type": "bool", "description": "Loggt empfangene Zendure-SOC-Werte."},
    "LOG_RAW_RESPONSE": {"group": "Logging", "label": "Shelly RAW loggen", "type": "bool", "description": "Loggt vollständige Shelly-JSON-Antworten. Nur für Fehlersuche verwenden."},
}


class ConfigManager:
    def __init__(self, path: str = "config.json"):
        self.path = path
        self.last_good_path = f"{path}.last-good"
        self._config: Dict[str, Any] = deepcopy(DEFAULT_CONFIG)
        self._mtime: float = 0.0
        self._lock = threading.RLock()
        self.cleanup_stale_temp_files(max_age_seconds=0)

    def cleanup_stale_temp_files(self, max_age_seconds: int = 300) -> None:
        """Remove orphaned temporary config files from interrupted atomic saves.

        Atomic saving still creates a short-lived temporary file. If the process is
        interrupted exactly during a save, that temp file can remain in the working
        directory. This cleanup is intentionally best-effort; permission problems are
        ignored so the controller can continue running.
        """
        directory = os.path.dirname(os.path.abspath(self.path)) or "."
        if not os.path.isdir(directory):
            return
        base_name = os.path.basename(self.path)
        now = time.time()

        for file_name in os.listdir(directory):
            looks_like_old_temp = (
                file_name.startswith("config.") and file_name.endswith(".tmp")
            )
            looks_like_new_temp = (
                file_name.startswith(base_name + ".") and file_name.endswith(".tmp")
            )
            if not (looks_like_old_temp or looks_like_new_temp):
                continue

            tmp_path = os.path.join(directory, file_name)
            try:
                age = now - os.path.getmtime(tmp_path)
                if max_age_seconds <= 0 or age >= max_age_seconds or os.path.getsize(tmp_path) == 0:
                    os.remove(tmp_path)
            except Exception:
                pass

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._config)

    def get_value(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default)

    def load(self) -> Dict[str, Any]:
        with self._lock:
            self.cleanup_stale_temp_files(max_age_seconds=0)
            if not os.path.exists(self.path):
                self._config = deepcopy(DEFAULT_CONFIG)
                self.save(self._config, create_last_good=False)
                self._mtime = os.path.getmtime(self.path)
                return self.get()

            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
            except Exception:
                if os.path.exists(self.last_good_path):
                    shutil.copy2(self.last_good_path, self.path)
                    with open(self.path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                else:
                    raise

            validated, changed = validate_config(loaded)
            self._config = validated

            if changed:
                self.save(self._config)

            self._mtime = os.path.getmtime(self.path)
            return self.get()

    def reload_if_needed(self) -> Tuple[Dict[str, Any], bool]:
        with self._lock:
            if not os.path.exists(self.path):
                return self.load(), True

            current_mtime = os.path.getmtime(self.path)
            if current_mtime != self._mtime:
                return self.load(), True

            return self.get(), False

    def save(self, new_config: Dict[str, Any], create_last_good: bool = True) -> Dict[str, Any]:
        with self._lock:
            validated, _ = validate_config(new_config)
            directory = os.path.dirname(os.path.abspath(self.path)) or "."
            os.makedirs(directory, exist_ok=True)
            self.cleanup_stale_temp_files(max_age_seconds=0)

            if create_last_good and os.path.exists(self.path):
                try:
                    shutil.copy2(self.path, self.last_good_path)
                except Exception:
                    pass

            fd, tmp_path = tempfile.mkstemp(prefix=os.path.basename(self.path) + ".", suffix=".tmp", dir=directory)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(validated, f, indent=4, ensure_ascii=False)
                    f.write("\n")
                os.replace(tmp_path, self.path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            self._config = validated
            self._mtime = os.path.getmtime(self.path)
            return self.get()


def validate_config(candidate: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    changed = False
    result = deepcopy(DEFAULT_CONFIG)

    if isinstance(candidate, dict):
        for key, value in candidate.items():
            if key in DEFAULT_CONFIG:
                result[key] = value
            else:
                # Unbekannte Keys bewusst behalten, damit manuell ergänzte Werte
                # nicht beim Speichern verschwinden.
                result[key] = value

    for key, default_value in DEFAULT_CONFIG.items():
        if not isinstance(candidate, dict) or key not in candidate:
            changed = True

    for key, meta in CONFIG_SCHEMA.items():
        before = result.get(key)
        result[key] = coerce_and_clamp(before, meta, DEFAULT_CONFIG.get(key))
        if result[key] != before:
            changed = True

    if result["MIN_SOC_PERCENT"] > result["MAX_SOC_PERCENT"]:
        result["MIN_SOC_PERCENT"], result["MAX_SOC_PERCENT"] = result["MAX_SOC_PERCENT"], result["MIN_SOC_PERCENT"]
        changed = True

    # Migration from V12.5 EVCC-specific keys to generic Cross-Charge keys.
    if isinstance(candidate, dict):
        if "CROSS_CHARGE_ENABLED" not in candidate and "EVCC_ENABLED" in candidate:
            result["CROSS_CHARGE_ENABLED"] = bool(result.get("EVCC_ENABLED", False))
            changed = True
        if "SECOND_BATTERY_EVCC_BASE_TOPIC" not in candidate and result.get("EVCC_SMA_BATTERY_TOPIC"):
            result["SECOND_BATTERY_EVCC_BASE_TOPIC"] = str(result.get("EVCC_SMA_BATTERY_TOPIC", "")).strip()
            changed = True
        if "SECOND_BATTERY_DISCHARGE_SIGN" not in candidate:
            try:
                legacy_sign = int(float(result.get("EVCC_SMA_DISCHARGE_SIGN", 1)))
            except (TypeError, ValueError):
                legacy_sign = 1
            if legacy_sign in (-1, 1):
                result["SECOND_BATTERY_DISCHARGE_SIGN"] = legacy_sign
            changed = True
        if "SECOND_BATTERY_STALE_TIMEOUT_SECONDS" not in candidate and result.get("EVCC_STALE_TIMEOUT_SECONDS"):
            result["SECOND_BATTERY_STALE_TIMEOUT_SECONDS"] = int(result.get("EVCC_STALE_TIMEOUT_SECONDS", 30))
            changed = True
        if "SECOND_BATTERY_STALE_BLOCK_CHARGE" not in candidate and "EVCC_STALE_BLOCK_CHARGE" in result:
            result["SECOND_BATTERY_STALE_BLOCK_CHARGE"] = bool(result.get("EVCC_STALE_BLOCK_CHARGE", True))
            changed = True
        if "CROSS_CHARGE_SIGNIFICANT_W" not in candidate:
            try:
                result["CROSS_CHARGE_SIGNIFICANT_W"] = int(float(result.get("SMA_DISCHARGE_BLOCK_W", 80)))
            except Exception:
                result["CROSS_CHARGE_SIGNIFICANT_W"] = 80
            changed = True

    # V12.10: neue/normalisierte Installationen schreiben standardmäßig V4.
    # Bestehende Installationen können explizit auf Legacy V3 zurückgestellt werden.
    if isinstance(candidate, dict):
        if "MEASUREMENT_SCHEMA_VERSION" not in candidate and "MEASUREMENT_LOG_SCHEMA" not in candidate:
            result["MEASUREMENT_SCHEMA_VERSION"] = "4"
            changed = True

    # V12.9: einmalige Übersetzung alter CSV_LOG_*-Keys in das neue
    # betriebslogische Messdaten-Logging. Keine V2-Datenmigration.
    if isinstance(candidate, dict):
        if "MEASUREMENT_LOG_MODE" not in candidate and "CSV_LOG_ENABLED" in candidate:
            result["MEASUREMENT_LOG_MODE"] = "standard" if bool(result.get("CSV_LOG_ENABLED", False)) else "off"
            changed = True
        if "MEASUREMENT_LOG_DIR" not in candidate and "CSV_LOG_DIR" in candidate:
            result["MEASUREMENT_LOG_DIR"] = str(result.get("CSV_LOG_DIR") or result.get("MEASUREMENT_LOG_DIR") or "logs")
            changed = True
        if "MEASUREMENT_LOG_FILE" not in candidate and "CSV_LOG_FILE" in candidate:
            result["MEASUREMENT_LOG_FILE"] = str(result.get("CSV_LOG_FILE") or result.get("MEASUREMENT_LOG_FILE") or "zendure_measurements.csv")
            changed = True
        if "MEASUREMENT_LOG_MAX_BYTES" not in candidate and "CSV_LOG_MAX_BYTES" in candidate:
            try:
                result["MEASUREMENT_LOG_MAX_BYTES"] = max(100_000, int(result.get("CSV_LOG_MAX_BYTES", result.get("MEASUREMENT_LOG_MAX_BYTES", 25_000_000))))
            except Exception:
                result["MEASUREMENT_LOG_MAX_BYTES"] = 25_000_000
            changed = True
        if "MEASUREMENT_LOG_BACKUP_COUNT" not in candidate and "CSV_LOG_BACKUP_COUNT" in candidate:
            try:
                result["MEASUREMENT_LOG_BACKUP_COUNT"] = max(1, int(result.get("CSV_LOG_BACKUP_COUNT", result.get("MEASUREMENT_LOG_BACKUP_COUNT", 5))))
            except Exception:
                result["MEASUREMENT_LOG_BACKUP_COUNT"] = 5
            changed = True

    for sign_key in ("SECOND_BATTERY_DISCHARGE_SIGN", "EVCC_SMA_DISCHARGE_SIGN"):
        if result.get(sign_key) == 0:
            result[sign_key] = 1
            changed = True

    discharge_target = max(
        int(result.get("MIN_SOC_PERCENT", 15)),
        int(result.get("MANUAL_FIXED_DISCHARGE_TARGET_SOC", 30)),
    )
    if discharge_target != result.get("MANUAL_FIXED_DISCHARGE_TARGET_SOC"):
        result["MANUAL_FIXED_DISCHARGE_TARGET_SOC"] = discharge_target
        changed = True

    charge_target = min(
        int(result.get("MAX_SOC_PERCENT", 100)),
        int(result.get("MANUAL_FIXED_CHARGE_TARGET_SOC", 90)),
    )
    if charge_target != result.get("MANUAL_FIXED_CHARGE_TARGET_SOC"):
        result["MANUAL_FIXED_CHARGE_TARGET_SOC"] = charge_target
        changed = True

    return result, changed


def coerce_and_clamp(value: Any, meta: Dict[str, Any], default: Any) -> Any:
    value_type = meta.get("type")

    try:
        if value_type == "bool":
            if isinstance(value, bool):
                coerced = value
            elif isinstance(value, str):
                coerced = value.strip().lower() in {"1", "true", "yes", "on", "checked"}
            else:
                coerced = bool(value)

        elif value_type == "int":
            coerced = int(float(value))
            if "min" in meta:
                coerced = max(meta["min"], coerced)
            if "max" in meta:
                coerced = min(meta["max"], coerced)

        elif value_type == "optional_int":
            if value is None or (isinstance(value, str) and value.strip() == ""):
                coerced = None
            else:
                coerced = int(float(value))
                if "min" in meta:
                    coerced = max(meta["min"], coerced)
                if "max" in meta:
                    coerced = min(meta["max"], coerced)

        elif value_type == "float":
            coerced = float(value)
            if "min" in meta:
                coerced = max(float(meta["min"]), coerced)
            if "max" in meta:
                coerced = min(float(meta["max"]), coerced)

        elif value_type == "select":
            options = meta.get("options", {})
            coerced = "" if value is None else str(value)
            if options and coerced not in options:
                coerced = default

        elif value_type == "password":
            coerced = "" if value is None else str(value)

        else:
            coerced = "" if value is None else str(value).strip()

    except Exception:
        coerced = default

    return coerced
