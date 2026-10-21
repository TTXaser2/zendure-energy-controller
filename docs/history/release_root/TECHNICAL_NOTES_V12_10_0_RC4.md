# Technical Notes V12.10.0-RC4

## Ziel

V12.10.0-RC4 erweitert die V4-RC-Serie um Status-/UI-Nacharbeit, V4-Ist-Datenanalyse im geschützten Analyse-Worker und eine gleichgezogene Diagnose-/CLI-Auswertung. Die Live-Regelstrategie bleibt unverändert.

## Nicht geändert

- Keine Änderung an AUTO-Regelstrategie.
- Keine Änderung an Nachtmodus-Regellogik.
- Keine Änderung an Cross-Charge-Strategie.
- Keine Änderung an MQTT-Subscriptions.
- Keine Änderung an MQTT-Kommandostruktur.

## Statusseite / UI

- Timing-Info-Texte enthalten keine Release-/Versionshistorie.
- `Gesamt ohne Sleep` wurde in der Statuskarte durch `Aktive Arbeitszeit` ersetzt.
- Info-Text erklärt die Bedeutung: aktive Arbeitszeit eines Regelzyklus ohne geplante Wartezeit bis zum nächsten Regelintervall.
- Lange Messdatenpfade werden in Datei und Verzeichnis getrennt dargestellt und per CSS robuster umgebrochen.
- Leere Fallback-Details werden nicht unnötig angezeigt.

## V4-Ist-Datenanalyse

- Der Analyse-Service erkennt V4-Dateien über `schema_version=4`.
- V4 wird nicht mehr als defekte V3-Datei behandelt.
- V4-Auswertung läuft im bestehenden isolierten Worker/Subprozess.
- Der Worker-Snapshot enthält neben ausgewählten CSV-Dateien auch:
  - `zec_measurement_manifest.json`
  - `zec_config_snapshots.json`
  - `zec_runtime_events.jsonl`, falls vorhanden
- V4 ohne Manifest oder ohne passenden Config-Snapshot/Hash wird fail-closed abgelehnt.
- V3/V4-Mischung wird fail-closed mit Dateiname abgelehnt.
- Runtime-JSONL fehlt/teilweise defekt erzeugt Warnungen, blockiert aber nicht, wenn CSV+Manifest+Config-Snapshots konsistent sind.

## Analyseumfang V4

RC4 analysiert geloggte V4-Istdaten. Es handelt sich noch nicht um eine What-if-/Simulator-Nachrechnung alternativer Reglerentscheidungen.

Ausgewertet werden u. a.:

- Zeitraum, Zeilenanzahl und Datenqualität.
- Grid-/Zendure-/SOC-/Zweitbatterie-Zeitreihen über vorhandene Analyseblöcke.
- Operating-Mode-Verteilung.
- `target_final_reason`-Verteilung.
- `safe_state_reason`-Verteilung.
- `command_suppressed_reason`-Verteilung.
- Zendure-MQTT-Status-Verteilung.
- Zyklusdauer-Kennzahlen aus `cycle_duration_ms`.
- UNKNOWN-Anteile in wichtigen V4-Diagnosefeldern.

## Pi-Schutz

- Webdienst analysiert nicht direkt im Webprozess.
- Analyse läuft im Worker/Subprozess.
- Parent-Prozess überwacht Timeout und RSS-Speicher.
- Worker setzt zusätzlich ein Address-Space-Limit; dieses ist getrennt vom RSS-Limit, damit kleine Analysen nicht durch Python-Reservierungen scheitern.
- Lokale Größen-/Zeilenlimits bleiben konservativ.

## Diagnose-/CLI-Tool

- `tools/replay_csv.py` akzeptiert V3- und V4-Dateien.
- V3 und V4 dürfen nicht gemeinsam ausgewertet werden.
- Fehlermeldungen nennen die problematische Datei bzw. bei fehlendem Snapshot den Hash.

## Altlasten-Strategie

Das Zielsystem ist eine einzelne Raspberry-Pi-Instanz. Alte RC1/RC2/RC3-Testartefakte sollen nicht dauerhaft kompatibel mitgeschleppt werden. Vor Installation/Validierung von RC4 sollten alte V4-RC-Messdateien und V4-Sidecars kontrolliert gelöscht werden, wenn eine saubere V4-Basis gewünscht ist.

## Tests

`python -m unittest discover -q` → 154 Tests OK.
