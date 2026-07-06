# Übergabe ZEC nach V12.11.0-RC18 – SQLite, UI-Prozess und Entwicklungsbacklog

## 1. Kontext und Arbeitsweise

Projekt: **„uni-meter mit MQTT und Zendure“ / Zendure Energy Controller (ZEC)**.

Der Nutzer nennt den Assistenten im ZEC-Kontext **„Kico“**. Kommunikation auf Deutsch, technisch präzise, kritisch, handlungsorientiert. Der Nutzer ist technisch erfahren und erwartet fachliche Beratung, kritisches Gegenprüfen und klare Empfehlungen.

Verbindliche Arbeitsregel:

- Keine Codeänderung, keine neue Controller-Version und kein Deploymentvorschlag ohne ausdrückliche Freigabe.
- Stabilität, Resilienz, Reaktionsschnelligkeit und effektive Steuerung des Zendure-Speichers haben oberste Priorität.
- EVCC, SMA, UniMeter und MQTT-Basisdienste dürfen nicht gestört werden.
- Bei größeren Änderungen zuerst fachlich klären, Zustände/Verhaltensmatrix/Testvertrag definieren, dann erst umsetzen.

## 2. Systemkontext

Produktiver Zielhost:

- Raspberry Pi 3B+
- Controller-Installationspfad: `/opt/zendure-controller`
- Downloads: `/home/pi/Downloads`
- Controller-Web: Port `8080`
- Analyse/Replay-Web: Port `8090`
- Services:
  - `zendure-controller.service`
  - `zendure-replay.service`
- Runtime-Log:
  - `/opt/zendure-controller/logs/zendure_runtime.log`

Energie-/Messkontext:

- SMA Home Manager 2.0 / SMA Energy Meter
- SMA Sunny Island als Primärspeicher, ca. 13 kWh brutto, ca. 2300/2400 W Leistungsgrenze
- Zendure SolarFlow 2400 AC+ als Zweitspeicher, aktuell ca. 5,28 kWh brutto
- ZEC nutzt inzwischen erfolgreich direkte SMA-UDP-Netzleistungsquelle mit `group_bind`
- EVCC läuft ebenfalls auf dem Pi und darf durch SMA-Socket-/UDP-Änderungen nicht gestört werden
- Direkte SMA-Quelle:
  - Gruppe `239.12.255.254:9522`
  - Interface `eth0`
  - Socket-Modus `group_bind`
  - Seriennummer/SUSY produktiv gesetzt, nicht öffentlich dokumentieren

Wichtige produktive Konfigurationswerte:

```text
MAX_CHARGE_POWER_W = 2100
MAX_DISCHARGE_POWER_W = 2100
MAX_SOC_PERCENT = 99
MIN_COMMAND_CHANGE_W = 50
Cross-Charge aktiv
Nachtentladung 400 W, Fenster zuletzt im UI 21:30–05:30 sichtbar
CSV-/Messdatenlogging je nach Test zeitweise aktiv/deaktiviert
```

## 3. Aktueller technischer Stand: V12.11.0-RC18

Aktuell gebautes Übergaberelease:

```text
V12.11.0-RC18
ZIP: /mnt/data/zendure_controller_v12_11_0_rc18.zip
```

RC18 basiert auf RC17 und ergänzt ein Migrationstool für vorhandene Measurement-CSV-Logs in den SQLite-Graphspeicher.

Wichtig: RC18 ändert keine Regelungslogik.

Nicht geändert:

- AUTO
- Nachtmodus-Regelwirkung
- Cross-Charge
- Restüberschuss-Ernte
- Zendure-MQTT-Kommandos/Topics
- Measurement-V4-CSV-Schema
- finale Excel-Lernsimulation

## 4. RC17: SQLite Graph-/Measurement-Store

RC17 ergänzte einen parallelen SQLite-basierten Graph-/Measurement-Store als leichte Datenbasis für Status- und Graph-Webseiten.

Ziele:

- UI-Historie unabhängig von teuren CSV-Scans bereitstellen
- SOC-Tagesgraph und Graph-Webseite beschleunigen
- GUI-Daten auch dann verfügbar halten, wenn `MEASUREMENT_LOG_MODE=off` ist
- CSV/V4 weiterhin als Diagnose-/Exportformat beibehalten

Neue/maßgebliche Bestandteile:

- neues Modul `measurement_db.py`
- neue Settings:
  - `MEASUREMENT_DB_ENABLED=true`
  - `MEASUREMENT_DB_FILE=zec_measurements.sqlite3`
  - `MEASUREMENT_DB_PATH`
  - `MEASUREMENT_DB_MAX_QUEUE_ROWS`
- DB-Writer über Queue/Hintergrundthread
- DB darf die Regelung nicht blockieren
- DB wird auch bei `MEASUREMENT_LOG_MODE=off` befüllt
- Tabellen:
  - `measurement_raw`
  - `measurement_1min`
  - `measurement_meta`
- `/graph-view-data` und `/soc-day-data` bevorzugen SQLite/1-Minuten-Aggregation, wenn vorhanden
- neuer Endpoint `/measurement-db-status`
- `/measurements/availability` enthält `measurement_db`
- Statuskarte „Messdaten / Logging“ zeigt SQLite-Graphspeicher/DB-Datei
- `collect_zec_trace.sh` misst zusätzlich:
  - `/grid-mini-sparkline`
  - `/measurement-db-status`

## 5. RC18: Migrationstool für vorhandene Measurement-Logs

RC18 ergänzt:

```text
tools/import_measurements_to_db.py
```

Zweck:

- vorhandene Measurement-CSV-Logs einmalig in die SQLite-Datenbank importieren
- sofort Echtdaten für Status-/Graph-Webseiten verfügbar machen
- verifizieren, dass `/soc-day-data` und `/graph-view-data` die DB-Daten anzeigen

Eigenschaften:

- streaming-basierte CSV-Verarbeitung
- keine großen In-Memory-Listen
- Pi-schonende Batch-Schreibweise
- automatische Ziel-DB-Ermittlung über `MEASUREMENT_DB_*`
- automatische Log-Verzeichnis-Ermittlung über Measurement-Konfiguration
- direkte Datei-/Glob-/Verzeichnisangabe möglich
- befüllt `measurement_raw` und `measurement_1min`
- nutzt dieselbe Extraktionslogik wie RC17 (`measurement_db.extract_measurement_point`)
- Fortschrittsausgaben
- `--dry-run` für Probeprüfung
- `--reset` für bewussten Neuaufbau der DB

Beispiele:

```bash
cd /opt/zendure-controller
python3 tools/import_measurements_to_db.py --log-dir /mnt/zec-usb/ZEC/logs
```

Mit bewusstem Neuaufbau:

```bash
python3 tools/import_measurements_to_db.py --reset --log-dir /mnt/zec-usb/ZEC/logs
```

Mit expliziten Dateien:

```bash
python3 tools/import_measurements_to_db.py /mnt/zec-usb/ZEC/logs/zendure_measurements*.csv
```

Nach Import prüfen:

```bash
curl -s http://127.0.0.1:8080/measurement-db-status | python3 -m json.tool
curl -s "http://127.0.0.1:8080/graph-view-data?range=24h&resolution=1min" | python3 -m json.tool | head -n 80
```

## 6. Performance-Ausgangslage vor SQLite

Vor RC16 wurden gemessen:

```text
/                         ca. 0,79 s
/status                   ca. 0,014 s
/soc-day-data             ca. 60,73 s
/graph-view-data 24h      ca. 207,64 s
```

Nach RC16:

```text
/                         ca. 0,77 s
/status                   ca. 0,020 s
/soc-day-data             ca. 17,73 s
/graph-view-data 24h      ca. 17,67 s
```

Bewertung:

- `/status` ist schnell, die Live-Regelung ist nicht das Problem.
- Historische UI-Endpunkte waren weiterhin zu langsam.
- Darum RC17 mit SQLite und RC18 mit Importtool.

Nächster Verifikationsschritt:

1. RC18 installieren.
2. Importtool ausführen.
3. Trace sammeln.
4. Prüfen, ob `/soc-day-data` und `/graph-view-data` nun aus SQLite deutlich schneller liefern.

## 7. Neuer UI-Prozess für die Statusseite

Die Statusseite wird künftig nicht mehr per langen Gesamtseiten-Feedbacktexten iteriert. Stattdessen wird sie elementweise spezifiziert.

Gemeinsame visuelle Arbeitskarte:

```text
/mnt/data/dashboard_design_mit_roten_markierungen.png
```

Elemente / Reihenfolge:

```text
1  Topbar / Navigation / Expertenmenü
2  Globale Systemhinweise / Status-Banner
3  Netzleistung
4  Betriebsmodus
5  Zendure (Batterie)
6  Netzleistungsquelle
7  Messdaten / Logging
8  Zendure SOC heute
9  Untere Systemkarten / Betriebsdiagnose
10 Expertenbereich / Legacy / Zusatzlinks
```

Der in den Projektquellen hinterlegte Mockup bleibt das Look&Feel-Ziel. Aktuelle RC16/RC17/RC18-Screenshots sind Ist-Zustand, nicht Designziel.

Pro Element wird künftig definiert:

1. alter Statusseiten-Gegencheck / Informationsinventar
2. Zweck
3. Datenquellen
4. alle möglichen Betriebszustände
5. Warn-/Fehler-/Fallbackzustände
6. Layout Desktop/Tablet/Mobile
7. Aktualisierung / Refresh / Cache-Alter
8. was sichtbar/eingeklappt ist
9. was bewusst nicht mehr angezeigt wird
10. finale Definition
11. Abnahmekriterien

Wichtig: Der Gegencheck mit der alten Statusseite kommt **vor** der Elementdefinition, damit keine relevanten alten Diagnoseinformationen versehentlich verloren gehen.

## 8. Mobile/responsive Statusseite

Mobile muss von Anfang an mitgedacht werden.

Bevorzugt:

- keine separate Mobilephone-Seite
- eine responsive Statusseite mit gemeinsamen Komponenten

Zielbild:

```text
Desktop:
- 5 Hauptkarten nebeneinander
- SOC-Graph breit
- Systemkarten unten als Grid

Tablet:
- 2–3 Karten pro Zeile
- SOC-Graph volle Breite
- Navigation kompakter

Mobile:
- Karten einspaltig
- Topbar reduziert/einklappbar
- Graph nutzbar mit reduzierter Höhe oder horizontal sinnvoller Darstellung
- Details ggf. ausklappbar
```

Pro Element muss definiert werden:

- Was bleibt mobil sichtbar?
- Was wird eingeklappt?
- Was darf niemals verschwinden?
- Welche Warnungen bleiben immer prominent?

## 9. Offene Backlog-/Planungspunkte

### 9.1 Statusseiten-UI-Prozess

- Elementweise Spezifikation statt Gesamtseiten-Feedback.
- Alte Statusseite je Element gegenprüfen.
- Mockup bleibt Look&Feel-Ziel.
- Arbeitskarte mit Elementnummern verwenden.
- Nächster UI-Startpunkt nach RC18-Verifikation:
  1. Element 1 Topbar/Navigation kurz definieren.
  2. Element 2 globale Systemhinweise definieren.
  3. Element 3 Netzleistung detailliert ausarbeiten, weil der Mini-Graph bereits gelungen ist und als Referenzmuster dienen kann.

### 9.2 SQLite-/Graphdaten

- RC17/RC18 liefern die technische Basis.
- Nach Installation/Import Trace prüfen.
- Erwartung: `/soc-day-data` und `/graph-view-data` sollen DB bevorzugen und deutlich schneller werden.
- Falls DB auf vfat-USB liegt, SQLite/WAL-Verhalten im Blick behalten.
- Mittelfristig SSD/ext4 als deutlich besseres Ziel.

### 9.3 Restüberschuss-Ernte / Harvest-Algorithmus

Offener fachlicher Backlogpunkt.

Ziel:

- Zendure soll zusätzlichen echten Überschuss/PV-Spitzen speichern, die der SMA/Sunny Island nicht mehr aufnehmen kann.
- Cross-Charge-Schutz darf echten Restüberschuss nicht versehentlich blockieren.
- Gleichgerichtetes Laden von SMA und Zendure bei echtem Überschuss ist erlaubt und gewünscht.

Der Erntealgorithmus muss sauber unterscheiden:

- echter Netzexport / Restüberschuss vorhanden
- SMA lädt bereits, aber Restexport bleibt
- knapper 0-W-Pendelbereich
- stale/ungültige SMA-/Grid-/Zendure-Daten
- SOC-/Max-SOC-/Leistungsgrenzen
- Deadband/HOLD
- MQTT-Stale/Partial-Stale

Keine Umsetzung ohne eigene Spezifikation, Verhaltensmatrix und Tests.

### 9.4 NIGHT_DISCHARGE-Ende

Offener Planungs-/Umsetzungspunkt.

Beim Verlassen von `NIGHT_DISCHARGE` muss die feste Nachtentladung explizit neutralisiert werden.

Austrittsgründe:

- Reserve-SOC erreicht
- Nachtfenster endet

Ziel:

- kein alter Entlade-Sollwert darf über HOLD/Deadband weiterlaufen
- danach darf AUTO bei echtem Netzbezug wieder normal entladen

Tests erforderlich:

```text
NIGHT_DISCHARGE → Reserve-SOC erreicht → neutralisiert auf 0
NIGHT_DISCHARGE → Fensterende → neutralisiert auf 0
NIGHT_DISCHARGE → danach AUTO mit echtem Netzbezug → AUTO darf neu entladen
NIGHT_DISCHARGE → danach HOLD/Deadband → keine alte Nachtentladung
```

### 9.5 Symmetrischer Cross-Charge-Schutz

Offener Planungs-/Umsetzungspunkt.

Cross-Charge in beide Richtungen vermeiden:

```text
SMA entlädt + Zendure lädt
SMA lädt + Zendure entlädt
```

Schutz nur in:

```text
AUTO
HOLD / Deadband mit gehaltenem Wert
```

Nicht in:

```text
NIGHT_DISCHARGE
FIXED_CHARGE
FIXED_DISCHARGE
andere bewusst feste Modi
```

Strategie:

- SMA/Primärspeicher hat Vorrang, aber nicht Exklusivität.
- Gegenläufige Batterieflüsse proportional reduzieren, nicht pauschal hart auf 0 setzen.
- Gleichgerichtetes Laden bei echtem Überschuss ist erlaubt.
- Stale/missing Zweitbatteriedaten führen nicht zu harter Blockade, sondern zu Warnung/Diagnose.

Parameterplanung:

- `SMA_DISCHARGE_BLOCK_W` perspektivisch zu `CROSS_CHARGE_SIGNIFICANT_W` migrieren.
- Default 80 W.
- Update-Script soll Migration übernehmen.

Keine Umsetzung ohne:

- Verhaltensmatrix
- Intended-Delta-Tests
- No-Regression-/Golden-Behavior-Tests

### 9.6 ZEC-MEASUREMENT-V4

Offener größerer Architekturblock.

Grundsätze:

- CSV bleibt Standard, aber datenbankfreundlich modelliert.
- Measurement-Zeitreihe und Runtime-/Betriebslogging strikt trennen.
- Logger-/Dateisystemfelder aus Measurement entfernen.
- Config-Snapshot/Manifest je `config_control_hash`.
- Headunit- und Batterie-/Packtemperaturen getrennt modellieren.
- Standard ohne JSON.
- Extended nur gezielte Detail-JSONs.
- Profilwechsel Standard/Extended startet neue CSV-Datei.

Nächster fachlicher Schritt:

- konsolidierten ZEC-MEASUREMENT-V4 Feldvertrag V0.3 erstellen
- danach V4-Testvertrag
- danach erst Umsetzung planen/freigeben

### 9.7 Analyse-/Diagnosetools

- Pi-safe Streaming bleibt Pflicht.
- Keine großen In-Memory-Analysen auf dem Pi.
- Fortschrittsausgaben beibehalten.
- Diagnose-/Trace-Tools sollen Endpointzeiten und DB-Status enthalten.
- Große Rohlogs nicht dauerhaft als Projektquelle verwenden.

### 9.8 GitHub-/Releaseprozess

Perspektivisch Releasebau stärker nach GitHub/GitHub Actions verlagern.

Ziel:

- repo-zentrierter Build
- reproduzierbares ZIP
- weniger manuelles ZIP-Hochladen/Kopieren

Noch nicht umgesetzt. Vor Umsetzung separat besprechen und freigeben lassen. Keine Tokens im Chat teilen.

## 10. Nicht vergessen / fachliche Leitplanke

Keine Änderung darf die effiziente, stabile, resiliente und reaktionsschnelle Steuerung des Zendure-Speichers gefährden.

Insbesondere:

- Regler darf nicht auf DB-/UI-/Logging-Arbeiten warten.
- DB-/CSV-/Analysefunktionen müssen bei Fehlern degradieren, nicht die Steuerung blockieren.
- EVCC/SMA/UniMeter dürfen nicht gestört werden.
- UI darf wichtige Warnungen nie verstecken.
- Standardmodus darf nicht diagnostisch blind werden; Expertenmodus ist ein Superset.

## 11. Startsatz für neuen Chat

Bitte im neuen Chat im Projekt „uni-meter mit MQTT und Zendure“ auf der Übergabe `UEBERGABE_ZEC_V12_11_0_RC18_UI_SQLITE_BACKLOG.md` und dem Release `zendure_controller_v12_11_0_rc18.zip` aufsetzen; erster Schritt ist die RC18-Installation/SQLite-Import-Verifikation und danach der elementweise UI-Spezifikationsprozess anhand der nummerierten Arbeitskarte.
