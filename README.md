# Zendure Energy Controller V12.11.2-RC4

## Statusseite V2 – gezielter UI-/Graph-Feinschliff

V12.11.2-RC4 basiert auf der produktiv bewährten Statusseite aus RC3. Der Neuaufbau, das responsive Kartenlayout und die zentrale Snapshot-/Polling-Architektur bleiben unverändert. RC4 behebt ausschließlich die gemeinsam identifizierten Funktions- und Konsistenzpunkte.

### Änderungen der Statusseite

- Produktkopf visuell korrigiert: `ZENDURE Energy Controller | Navigation`.
- Betriebsmodus-Details als konsistente Bezeichnungs-/Wertzeilen mit rechtsbündigen Werten.
- Primärspeicher-Ring einheitlich mit `SOC aktuell` beschriftet.
- Redundanter Untertitel des Speicher-SOC-Tagesgraphen entfernt.
- Expertenmenü als robustes, nativ klickbares Dropdown umgesetzt.
- Datum des Tagesgraphen ist direkt anklickbar und öffnet den nativen Kalenderwähler; `Zurück`, `Heute` und `Vor` bleiben erhalten.
- Graphlegende erklärt nun dynamisch Zendure, Primärspeicher, Max-SOC, Nachtreserve, Min-SOC, Nachtfenster und den aktuellen Zeitpunkt.

### Historischer Regelgrund im SOC-Tooltip

Der SQLite-Graphspeicher persistiert ab RC4 zusätzlich den Regelgrund:

- `measurement_raw.control_reason`
- `measurement_1min.control_reason_last`

Neue Messwerte zeigen den Grund damit dauerhaft im Tagesgraph-Tooltip. Die Schemaerweiterung erfolgt beim Start als additive SQLite-Migration; vorhandene Messwerte und Tabellen bleiben erhalten.

Für bereits bestehende historische SQLite-Daten liegt das idempotente Wartungsskript `tools/backfill_measurement_reasons.py` bei. Es liest vorhandene V4-CSV-Dateien streamingbasiert, verändert keine CSV, füllt nur leere Reason-Felder und erstellt vor `--apply` ein Rollback-Backup.

### Refresh und Lastschutz

- Zentrale Snapshot-Single-Source-of-Truth über `/status-view-data` bleibt erhalten.
- Keine vollständigen Seitenreloads und keine unabhängigen Poller je Karte.
- Keine synchronen DB-, MQTT-, Netzwerk- oder Dateisystemoperationen im Reglerpfad ergänzt.
- Der Tagesgraph liest weiterhin ausschließlich den indizierten 1-Minuten-Speicher für den ausgewählten Tag.

### Unveränderte Regelung

AUTO, Harvest, Cross-Charge, NIGHT_DISCHARGE, Fixed-Modi, Safe-State und MQTT-Command-Lifecycle sind gegenüber RC3 unverändert. RC4 erzeugt keine neuen Reglerzustände, Latches, Race Conditions oder Prioritätsumkehrungen.

## Installation

Siehe `README_INSTALLATION.md`.
