Zendure Energy Controller Version 12.8.6

# Zendure Energy Controller V12.8.6

Lokaler MQTT-basierter Controller für Zendure SolarFlow 2400 AC+ mit Weboberfläche, Regelalgorithmus, CSV-Logging, Cross-Charge-Schutz, lokaler Zendure-API als Telemetrie-Fallback, optionaler Analyse-Weboberfläche und systemd-Betrieb.

Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

Lizenziert unter AGPL-3.0-or-later. Siehe `LICENSE`, `NOTICE` und `DISCLAIMER.md`.


## Wichtige Änderungen in V12.8.6

V12.8.6 ist eine gezielte Hotfix-Version für Housekeeping und Ablaufkonsistenz im Live-Controller:

- Zweitbatterie-/SMA-Anzeigewerte werden nun auch in Nachtentladung, Stop/Hold und festen Modi aktualisiert.
- `update_sma_metrics()` wurde fachlich getrennt: Anzeige-/CSV-Ableitung läuft unabhängig von AUTO, Cross-Charge-Regelmetriken nur nach gültiger Grid-Messung im AUTO-Zweig.
- Zendure-Istleistung wird am Zyklusende erneut aus Rohsensoren und aktuellen Soll-Limits abgeleitet, damit Vorzeichen nach Moduswechseln nicht stale bleiben.
- Neue Freshness-/Validitätsfelder für Grid, Zweitbatterie und effective export helfen, Anzeige/CSV/Analyse sauberer zu interpretieren.
- Zweitbatterie-MQTT-Rohwerte werden unter `state.lock` aktualisiert.
- Zusätzliche Tests sichern frühe Return-Pfade und per-cycle Housekeeping ab.

## Wichtige Änderungen in V12.8.5

V12.8.5 ist eine Stabilitäts- und Bedienbarkeitsversion mit Schwerpunkt Analyse-/Replay-Sicherheit auf dem Raspberry Pi:

- Analyse-Weboberfläche startet Analysen nicht mehr automatisch beim Seitenaufruf. Eine Analyse beginnt erst nach explizitem Klick auf „Analyse starten“.
- Neue Pi-Safe-Analysegrenzen: standardmäßig 4 Dateien, 12 MiB Gesamtgröße und 40.000 Messpunkte.
- Erweiterter Analysemodus mit aktiver Warn-/Bestätigung: 5 Dateien, 18 MiB und 70.000 Messpunkte. Alles darüber wird lokal auf dem Raspberry Pi abgelehnt.
- Auswahlprüfung vor Analyse: Dateianzahl, Gesamtgröße, geschätzte Messpunkte, Zeitraum und Risiko-Klassifikation.
- Single-Flight-Lock: Reloads, Mehrfachklicks oder zweite Tabs starten keine parallelen Analysen.
- Analyse läuft in einem Hintergrundjob mit Status-/Phasenanzeige, deaktiviertem Startbutton und Abbrechen-Funktion.
- Analyse verwendet Snapshot-Kopien der CSV-Dateien statt direkt auf der aktiven Logdatei zu arbeiten.
- Report-Downloads (`report.txt`, `report.json`, `summary.csv`) verwenden das gecachte Analyseergebnis statt eine teure Neuanalyse zu starten.
- `zendure-replay.service` enthält Ressourcenschutz (`MemoryHigh`, `MemoryMax`, `CPUQuota`, niedrigere CPU-/I/O-Priorität), damit eine zu große Analyse nicht den gesamten Pi blockieren soll.
- Analyse-Dark-Mode nutzt `UI_DARK_MODE` aus `config.json`.
- Analyse-Kurzfazit wurde zu einem echten Gesamturteil mit Handlungsdruck erweitert; Blockeinleitungen und Info-Texte wurden ausgebaut.
- Vorzeicheninterpretation der Zendure-Istleistung bei Nachtentladung verbessert: positive interne Pack-&gt;Headunit-Leistung wird bei aktiver Entladeanforderung systemisch als Entladung dargestellt.
- Vorbereitung für `UI_MODE` (`standard`/`expert`) in der Config; vollständige Standard-/Expertenansicht bleibt als größerer UI-Block offen.

## Wichtige Änderungen in V12.8.4

V12.8.4 ist eine Bugfix-Version für die Ablaufreihenfolge des Live-Controllers:

- Nachtmodus ist nicht mehr von Shelly-/UniMeter-Netzleistungsdaten abhängig. Bei fehlender Netzmessung läuft die feste Nachtentladung weiter, sofern SOC und MQTT-Pfad gültig sind.
- Manuelle Betriebsarten `STOP_HOLD`, `FIXED_DISCHARGE` und `FIXED_CHARGE` werden vor der Shelly-/UniMeter-Abfrage behandelt und hängen dadurch nicht unnötig an der Netzleistungsmessung.
- Wenn ein Shelly-/UniMeter-Fehler im normalen Automatikbetrieb zum Safe-State führt, beendet der Regelzyklus sofort und läuft nicht mit altem/0-W-Netzwert weiter.
- Zusätzliche Tests sichern Nachtmodus, feste Entladung, feste Beladung, Stop/Hold und normales AUTO-Verhalten ab.
- Defaultwerte für neu erzeugte Konfigurationen sind im Produktivbetrieb weniger verbose: `DEBUG`, `LOG_VALUES`, `LOG_CONTROL`, `LOG_MQTT` und `LOG_SOC` sind standardmäßig `false`. Bestehende `config.json` bleibt unverändert.
- Keine Änderung an Priorität oder Ressourceneinstellungen des Replay-Service in V12.8.4; V12.8.5 ergänzt nun bewusst Ressourcenschutz für den Replay-Service.

## Wichtige Korrekturen seit V12.8.1 / V12.8.2

Die Zwischenversionen V12.8.1 und V12.8.2 korrigierten Analyse-Weboberfläche und Settings-UI:

- Cross-Charge-Ampel wird wieder als Badge statt als sichtbarer HTML-Code angezeigt.
- High-SOC-/Ladeannahme-Zustände werden lesbar statt als JSON/HTML-Escape ausgegeben.
- Controller-Link zur Analyse-Weboberfläche nutzt den dynamischen Host und den Analyse-Port 8090 bzw. `REPLAY_WEB_PORT`.
- Analyse-Tabellen enthalten anklickbare `info`-Erklärungen pro Begriff.
- Maximalwert für `CSV_LOG_BACKUP_COUNT` in den Settings auf 20 erhöht.
- Analyse-Weboberfläche und Textreport verwenden deutsche Zahlendarstellung mit Dezimalkomma. Technische Messdaten-CSV und JSON-Report bleiben unverändert mit Dezimalpunkt.
- V12.8.2 hatte die Schutzgrenze der Mehrdatei-Analyse auf maximal 20 CSV-Dateien erhöht; V12.8.5 reduziert diese Grenze wieder bewusst zugunsten der Raspberry-Pi-Betriebssicherheit.

## Wichtige Änderungen in V12.8

V12.8 erweitert gezielt die Analysefunktionen, ohne den Live-Regelalgorithmus zu verändern.

- Analyse-Weboberfläche V12.8 mit Mehrdatei-Auswahl für CSV-Dateien im Schema `ZEC-MEASUREMENT-V2`.
- Ursprüngliche V12.8-Schutzgrenzen waren 20 Dateien, 50 MB und 500.000 Messpunkte; V12.8.5 ersetzt diese Werte durch konservative Pi-Safe-/Extended-Grenzen.
- Datenqualitätsprüfung: Messdauer, `dt_s`, Datenlücken, fehlende Netz-/SOC-/Zendure-Istwerte, SAFE_STATE-Zeiten.
- Reglerqualitätsanalyse: mittlere/Median/95%-Netzabweichung, Zeit im Zielband, Netzbezug/Einspeisung über Schwellwert, MQTT-Kommandorate, Moduswechsel, Sollwertsprünge und Richtungswechsel.
- Erweiterte Cross-Charge-Analyse: Blockadezeit, kritische Überschneidung SMA-Entladung + Zendure-Ladung, Ampelbewertung und Ereignisliste.
- Nachtentladung und High-SOC werden angezeigt; High-SOC bleibt bewusst nur leichtgewichtig.
- Reports als Text, JSON und CSV-Summary.
- Controller → Analyse-Link nutzt nun dynamisch den aktuellen Hostnamen statt fest `127.0.0.1`.
- Analyse → Controller-Rücklink ergänzt.
- Statusseite: Diagnoseboxen umsortiert und Kurzverlauf-Graph mit stabiler Höhe gegen Layout-Sprünge.

## Bereits seit V12.7 enthalten

- CSV-Messdatenformat `ZEC-MEASUREMENT-V2` mit Semikolon-Trennzeichen und Punkt als Dezimalzeichen.
- Konsistente signierte Leistungswerte:
  - Netzleistung: positiv = Netzbezug, negativ = Einspeisung.
  - Zendure-/Speicherleistung: positiv = Laden, negativ = Entladen.
- Graph-Konsolidierung: Zendure Sollleistung und Zendure Istleistung werden primär als signierte Linien dargestellt.
- Optionaler, separater Replay-/Analyse-Webdienst auf Port 8090 (`zendure-replay.service`). Der Live-Regler importiert keinen Replay-Code.
- Paketbereinigung: nur noch `tools/`, kein zusätzliches `Tools/`; nur noch `ZendureController.py`, keine doppelte Controller-Startdatei.

## Start

```bash
cd /opt/zendure-controller
python3 ZendureController.py
```

## Dienstbetrieb

Siehe `README_INSTALLATION.md`.

## Analyse-Weboberfläche

Die Analyse-Weboberfläche ist optional und getrennt vom Live-Regler:

```bash
sudo systemctl start zendure-replay.service
```

Aufruf standardmäßig:

```text
http://<RASPBERRY-IP>:8090
```

Die Hauptoberfläche verlinkt dynamisch auf den gleichen Host mit Port 8090. In der Analyseoberfläche gibt es einen Rücklink auf den normalen Controller-Port.

## Dokumentation

Das vollständige DOCX/PDF-Handbuch wurde für diesen Zwischenstand bewusst noch nicht neu erzeugt. V12.8 aktualisiert die technische Basis, README, Installationshinweise und technische Notizen. Eine vollständige Handbuch-Aktualisierung ist für den nächsten größeren stabilen Meilenstein vorgesehen.
