# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

from typing import Iterable, List

LIMITER_LABELS = {
    "DEADBAND": "Totzone aktiv",
    "RAMP_LIMIT": "Rampenbegrenzung aktiv",
    "MIN_SOC": "Mindest-SOC erreicht",
    "MAX_SOC": "Maximal-SOC erreicht",
    "SMA_DISCHARGE": "Zusatzbatterie-Entladung erkannt",
    "LOW_EFFECTIVE_SURPLUS": "Zu wenig echter PV-Überschuss",
    "SMA_OR_LOW_EFFECTIVE_SURPLUS": "Cross-Charge-Schutz / zu wenig echter PV-Überschuss",
    "MQTT_DISCONNECTED": "MQTT-Verbindung getrennt",
    "SOC_STALE": "Zendure-SOC zu alt oder fehlt",
    "EVCC_STALE": "Zusatzbatterie-MQTT-Daten zu alt",
    "SHELLY_STALE": "Netzleistungsdaten zu alt",
    "ZENDURE_API_FALLBACK": "Lokale Zendure-API als Fallback aktiv",
    "MODE_CHANGE_LOCK": "Umschalt-Sperrzeit aktiv",
    "MANUAL_MODE_INVALID": "Ungültiger manueller Modus",
    "NIGHT_RESERVE_SOC": "Nachtmodus Reserve-SOC erreicht",
}

PATH_LABELS = {
    "SAFE_STATE": "Safe-State: Lade- und Entladeleistung werden auf 0 W gesetzt",
    "MANUAL -> STOP_HOLD": "Manueller Stop/Hold: Regelung aus, Leistung 0 W",
    "MANUAL -> FIXED_DISCHARGE -> OUTPUT": "Manuelle feste Entladung aktiv",
    "MANUAL -> FIXED_CHARGE -> INPUT": "Manuelle feste Beladung aktiv",
    "GRID -> DEADBAND -> HOLD_POWER": "Totzone aktiv: Leistung wird gehalten",
    "NIGHT_MODE -> OUTPUT": "Nachtmodus: feste Entladung aktiv",
    "NIGHT_MODE -> RESERVE_SOC -> STOP_HOLD": "Nachtmodus gestoppt: Reserve-SOC erreicht",
    "NIGHT_MODE -> RESERVE_SOC -> AUTO": "Nachtmodus pausiert: Reserve-SOC erreicht, AUTO-Regelung aktiv",
    "GRID -> DISCHARGE_CONTROL -> OUTPUT": "Netzbezug erkannt: Zendure entlädt",
    "GRID -> CROSS_CHARGE -> CHARGE_CONTROL -> INPUT": "PV-Überschuss erkannt: Zendure lädt unter Berücksichtigung des Cross-Charge-Schutzes",
    "GRID -> CROSS_CHARGE -> CHARGE_RAMP_DOWN": "Cross-Charge-Schutz: Zendure-Ladung wird reduziert",
    "GRID -> DISCHARGE_RAMP_DOWN": "Entladeleistung wird kontrolliert reduziert",
}

MODE_LABELS = {
    "STARTUP": "Systemstart",
    "CHARGE": "Zendure lädt",
    "DISCHARGE": "Zendure entlädt",
    "NIGHT_DISCHARGE": "Nachtmodus: feste Entladung",
    "SAFE_STATE": "Safe-State",
    "BLOCKED_BY_SMA": "Ladung durch Cross-Charge-Schutz blockiert",
    "HOLD": "Halten / Totzone",
    "CHARGE_RAMP_DOWN": "Ladung wird reduziert",
    "DISCHARGE_RAMP_DOWN": "Entladung wird reduziert",
    "STOP_HOLD": "Manueller Stop/Hold",
    "MANUAL_FIXED_DISCHARGE": "Manuelle feste Entladung",
    "MANUAL_FIXED_CHARGE": "Manuelle feste Beladung",
}


def limiter_label(code: str) -> str:
    return LIMITER_LABELS.get(str(code), str(code))


def limiter_labels(codes: Iterable[str]) -> List[str]:
    return [limiter_label(code) for code in codes]


def limiter_text(codes: Iterable[str]) -> str:
    items = list(codes)
    if not items:
        return "Keine aktiv"
    return ", ".join(limiter_labels(items))


def technical_limiter_text(codes: Iterable[str]) -> str:
    items = list(codes)
    return ", ".join(str(code) for code in items) if items else "none"


def path_label(path: str) -> str:
    return PATH_LABELS.get(str(path), str(path) if path else "-")


def mode_label(mode: str) -> str:
    return MODE_LABELS.get(str(mode), str(mode))
