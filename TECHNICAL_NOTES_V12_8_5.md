# Technische Notizen V12.8.5

V12.8.5 ist ein Stabilitäts- und Bedienbarkeitsrelease. Schwerpunkt ist der Schutz des Raspberry Pi vor zu großen oder parallelen Replay-/Analyse-Läufen.

## 1. Analyse-/Replay-Schutz

Die Analyse-Weboberfläche startet nicht mehr automatisch beim Seitenaufruf. Eine Analyse wird nur noch explizit per Button gestartet.

Neue Standardlimits für lokale Pi-Analyse:

```text
ANALYSIS_MAX_FILES = 4
ANALYSIS_MAX_TOTAL_BYTES = 12 MiB
ANALYSIS_MAX_ROWS = 40.000
```

Erweiterte Analyse nach aktiver Bestätigung:

```text
ANALYSIS_EXTENDED_MAX_FILES = 5
ANALYSIS_EXTENDED_MAX_TOTAL_BYTES = 18 MiB
ANALYSIS_EXTENDED_MAX_ROWS = 70.000
```

Alles darüber wird lokal abgelehnt. Große Mehrtages-/Langzeitanalysen sollen auf einem PC/offline oder später über eine DB-/Aggregationslösung erfolgen.

## 2. Bedienführung der Analyse-Seite

Die Analyse läuft nun als Hintergrundjob:

- sofortige Rückmeldung nach Klick auf „Analyse starten“
- Startbutton während laufender Analyse deaktiviert
- Phasen-/Statusanzeige mit Fortschrittsbalken
- Abbrechen-Button
- serverseitiger Single-Flight-Lock gegen parallele Analysen
- Reload oder zweiter Browser-Tab kann keine zweite Analyse parallel starten

## 3. Snapshot und Cache

Vor der Analyse werden die ausgewählten CSV-Dateien in ein temporäres Snapshot-Verzeichnis kopiert. Dadurch wird nicht direkt auf der aktiven `zendure_measurements.csv` gearbeitet.

Report-Downloads nutzen das gecachte Ergebnis des letzten Analyselaufs:

```text
/report.txt
/report.json
/summary.csv
```

Diese Endpunkte lösen keine erneute Vollanalyse mehr aus.

## 4. systemd-Ressourcenschutz

`zendure-replay.service` enthält nun Schutzgrenzen:

```ini
MemoryAccounting=yes
CPUAccounting=yes
IOAccounting=yes
MemoryHigh=200M
MemoryMax=300M
CPUQuota=50%
Nice=10
IOSchedulingClass=idle
IOSchedulingPriority=7
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=3
```

Ziel: Eine zu große Analyse soll im Fehlerfall den Analyse-Dienst abbrechen oder drosseln, aber nicht EVCC, MQTT oder den Live-Regler blockieren.

## 5. Analyse-Verständlichkeit

Die Analyse-Seite wurde erklärender aufgebaut:

- echtes Kurzfazit mit Gesamturteil und Handlungsdruck
- Abschnittseinleitungen unter den Blocküberschriften
- erweiterte Info-Texte für Begriffe wie Deadband, Soll/Ist, MQTT-Wirkung, nicht bewertbar, dt_s, Moduswechsel und Cross-Charge-Kennzahlen
- Ampel-Info nicht mehr fälschlich nur als Cross-Charge-Erklärung
- Dark Mode abhängig von `UI_DARK_MODE`

## 6. Zendure-Istleistung bei Nachtentladung

Die Ableitung der Zendure-System-Istleistung wurde korrigiert/robuster gemacht:

- Positive Rohwerte aus Pack-/DC-Flüssen können bei aktiver Entladeanforderung eine interne Pack→Headunit-Leistung darstellen.
- In diesem Fall wird die systemische Istleistung als Entladung dargestellt, also negativ.
- Die Statusseite und Graph-Erläuterung beschreiben den Unterschied zwischen externer Systemleistung und internen Pack-/Headunit-Flüssen klarer.

## 7. UI_MODE vorbereitet

`UI_MODE` wurde als Config-Parameter mit den Werten `standard` und `expert` vorbereitet.

Die vollständige Umsetzung eines Standard-/Expertenmodus bleibt bewusst ein eigener UI-/UX-Block, damit V12.8.5 nicht zu breit und riskant wird. Expertenmodus soll fachlich ein Superset des Standardmodus sein.

## 8. Tests

Ausgeführt:

```bash
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -v
```

Ergebnis:

```text
Ran 53 tests
OK
```
