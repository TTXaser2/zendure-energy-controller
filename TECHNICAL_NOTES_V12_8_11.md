# Technical Notes V12.8.11

## 1. Ziel

V12.8.11 stabilisiert den Controller-Ablaufvertrag, ohne die fachliche Regelstrategie neu auszulegen. Schwerpunkt ist ein schlankes Freshness-/Validitätsmodell, das pro Regelzyklus sichtbar macht, welche externen Daten vorhanden, frisch, gültig und tatsächlich für die Regelentscheidung genutzt wurden.

## 2. Mode-/Datenquellen-Matrix

| Modus / Pfad | Grid erforderlich | SOC erforderlich | MQTT-Kommandopfad erforderlich | Zweitbatterie erforderlich | Bemerkung |
|---|---:|---:|---:|---:|---|
| `AUTO` / Grid-Regelung | ja | ja | ja | nur bei Cross-Charge-Pfad | Normale Netzleistungsregelung. |
| `NIGHT_DISCHARGE` | nein | ja | ja | nein | Feste Nachtentladung darf nicht an Shelly/UniMeter hängen. |
| `FIXED_DISCHARGE` | nein | ja | ja | nein | Feste manuelle Entladung nutzt keinen Grid-Wert. |
| `FIXED_CHARGE` | nein | ja | ja | nein | Feste manuelle Beladung nutzt keinen Grid-Wert. |
| `STOP_HOLD` | nein | nein | ja | nein | Setzt Lade-/Entladeleistung auf 0 W. |
| `SAFE_STATE` wegen SOC | nein | ja | ja | nein | SOC fehlt/stale oder Grenzwert blockiert. |
| `SAFE_STATE` wegen Shelly/UniMeter | ja | optional | ja | optional | Nur im AUTO-/Grid-Pfad. |
| `Cross-Charge` | ja | ja | ja | ja | Zusatzbatteriedaten werden nur im AUTO-/Grid-Kontext für Regelung genutzt. |

## 3. Freshness-/Validitätsfelder

Der neue Vertrag unterscheidet bewusst:

- `available`: Ein Wert bzw. eine Quelle ist grundsätzlich vorhanden.
- `fresh`: Der letzte gültige Zeitstempel liegt innerhalb des konfigurierten Timeouts.
- `valid`: Quelle ist vorhanden und frisch.
- `used_for_control`: Die Quelle wurde in diesem Zyklus tatsächlich für die Regelentscheidung benutzt.
- `*_age_s`: Alter der Quelle in Sekunden.
- `*_validity_reason`: maschinenlesbarer Grund, z. B. `OK`, `GRID_MISSING`, `GRID_STALE`, `SOC_STALE`, `MQTT_DISCONNECTED`.

Diese Felder sind Diagnose-/Vertragslogik. Die eigentliche Entscheidung über Safe-State, Hold, Laden oder Entladen bleibt in den bestehenden Mode-Handlern.

## 4. Zentrale Finalize-/Housekeeping-Phase

`finish_cycle()` setzt jetzt pro Zyklus:

- genutzte Quellen (`grid_power_used_for_control`, `soc_used_for_control`, `mqtt_command_path_used_for_control`, `second_battery_data_used_for_control`),
- erforderliche Quellen (`control_required_sources`),
- fehlende/stale Pflichtquellen (`control_missing_required_sources`),
- Gesamtbewertung (`control_data_quality`),
- und aktualisiert danach die bestehenden Anzeige-/CSV-/Graphwerte.

Wichtig: `effective_export_power_valid` wird außerhalb eines Grid-Regelpfads bewusst zurückgesetzt, damit Nachtmodus, Stop/Hold oder feste Modi keinen alten AUTO-Wert als gültig weitertragen.

## 5. MQTT-Diagnosefilter

Bisher wurden bei aktiver MQTT-Diagnose alle vom Controller empfangenen Topics in den Diagnosepuffer geschrieben. V12.8.11 trennt nun:

- `MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE = filtered`: nur Topics speichern/anzeigen, die zum Diagnosefilter passen.
- `MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE = all`: alle empfangenen Controller-Topics speichern/anzeigen.

MQTT-Matching ist case-sensitive. `EVCC/#` passt also nicht auf `evcc/site/...`.

## 6. Tests

Neue Tests in `tests/test_v12_8_11_flow_contract.py` prüfen:

- Nachtentladung ohne Grid-Abhängigkeit, aber mit SOC/MQTT-Vertrag,
- AUTO/Grid-Pfad mit gültigem Grid/SOC/MQTT-Vertrag,
- SOC-stale-Safe-State ohne fälschliche Grid-Pflicht,
- CSV-Felder für den Freshness-/Validitätsvertrag,
- MQTT-Wildcard-Matching `#` und `+`,
- case-sensitive Filterung,
- gefilterten und vollständigen MQTT-Diagnosemodus.

## 7. Excel-Lernsimulation

Die finale Datei `tools/zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx` wird unverändert mit ausgeliefert. Sie wurde nicht repariert, neu erzeugt, umbenannt oder inhaltlich angepasst.
