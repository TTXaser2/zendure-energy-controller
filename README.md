Zendure Energy Controller Version 12.8.12

# Zendure Energy Controller V12.8.12

Lokaler MQTT-basierter Controller für Zendure SolarFlow 2400 AC+ mit Weboberfläche, Regelalgorithmus, CSV-Logging, Cross-Charge-Schutz, lokaler Zendure-API als Telemetrie-Fallback, optionaler Analyse-Weboberfläche und systemd-Betrieb.

Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

Lizenziert unter AGPL-3.0-or-later. Siehe `LICENSE`, `NOTICE` und `DISCLAIMER.md`.



## Wichtige Änderungen in V12.8.12

V12.8.12 ist ein begrenzter Diagnose-/Settings-UI-Hotfix und eine Nachhärtung von V12.8.11. Die eigentliche Regelstrategie bleibt unverändert.

- MQTT-Topic-Diagnoseseite hat nun einen Button `Diagnosetabelle leeren`. Der serverseitige Diagnosepuffer wird geleert; die Diagnose läuft weiter und neue MQTT-Werte erscheinen danach wieder in der Tabelle.
- Nach `Dienst jetzt neu starten` leitet die Settings-Webseite nun auf die Hauptseite `/` des konfigurierten Web-Ports weiter statt auf `/status`.
- Restart-Seite spricht nun von Hauptseite statt Statusseite und nutzt den absoluten Ziel-URL mit dem konfigurierten `WEB_PORT`.
- Zusätzliche Tests sichern den Diagnosepuffer-Clear, neue MQTT-Werte nach dem Leeren und den korrigierten Restart-Redirect ab.
- Keine Änderung am Live-Regelalgorithmus.
- Finale Excel-Lernsimulation bleibt unverändert unter `tools/` enthalten.

## Wichtige Änderungen in V12.8.11

V12.8.11 ist ein vorsichtiger Controller-Housekeeping-/Diagnose-Build mit Schwerpunkt Ablaufvertrag, Freshness-/Validitätsmodell und MQTT-Diagnosefilter. Der bestehende Regelalgorithmus bleibt fachlich erhalten; die Änderungen machen die Regelentscheidungen besser prüfbar und verhindern stale Diagnose-/CSV-Aussagen.

- Neuer schlanker Freshness-/Validitätsvertrag für externe Datenquellen: Grid/Shelly-UniMeter, Zendure-SOC, MQTT-Kommandopfad und Zweitbatterie/EVCC werden pro Zyklus mit `available`, `fresh`, `valid`, `used_for_control`, Alter und Grund bewertet.
- Zentrale `finish_cycle()`-/Housekeeping-Phase dokumentiert nun, welche Quellen ein Modus tatsächlich benötigt und welche davon fehlen oder stale sind. Nachtentladung bleibt dabei bewusst ohne Grid-Abhängigkeit.
- CSV-/Graph-Datensatz enthält zusätzliche Diagnosefelder für Datenqualität, genutzte Quellen und Missing-/Stale-Gründe.
- `effective_export_power_valid` wird in Modi ohne Grid-Regelpfad nicht mehr stale aus einem früheren AUTO-Zyklus weitergeführt.
- MQTT-Topic-Diagnosefilter korrigiert: Im Standardmodus `filtered` werden nur noch Nachrichten gespeichert/angezeigt, die wirklich zum konfigurierten MQTT-Filter passen.
- Neuer MQTT-Diagnose-Anzeigemodus `MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE`: `filtered` oder `all`. `all` zeigt bewusst alle empfangenen Controller-Topics für kurze Fehlersuche.
- MQTT-Wildcards `#` und `+` werden inklusive case-sensitiver Topic-Prüfung getestet; die Diagnose-Webseite weist auf Groß-/Kleinschreibung hin.
- Finale Excel-Lernsimulation `zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx` wird unverändert unter `tools/` mit ausgeliefert.
- Neue Tests sichern Mode-/Datenquellen-Vertrag, Freshness-Felder, CSV-Diagnosefelder und MQTT-Diagnosefilter ab.

## Wichtige Änderungen in V12.8.10

V12.8.10 ist ein kleiner Analyse-Webseiten-Hotfix ohne Änderung am Live-Regelalgorithmus:

- Info-Aufklapper im Diagramm-Bereich nutzen beim Öffnen die volle Breite des jeweiligen Diagramm-Elements. Dadurch bleiben Label, Balken und Werte stabil und die Erklärungstexte sind besser lesbar.
- Der Button `Analyse starten` wird sofort gesperrt, sobald sich die CSV-Auswahl ändert.
- Während die Auswahl-/Risikobox neu berechnet wird, zeigt der Button `Aktualisiere Dateiauswahl…`.
- Eine Analyse kann erst gestartet werden, wenn die Informationen zu den ausgewählten Dateien vollständig aktualisiert und gültig sind.
- Race-Condition-Schutz für schnelle Mehrfachänderungen der Dateiauswahl: veraltete Profilantworten werden ignoriert.

## Wichtige Änderungen in V12.8.9

V12.8.9 ist eine Analyse-Webseiten-Version mit Schwerpunkt Verständlichkeit, Bedienrückmeldung und Dark-Mode-Lesbarkeit:

- Extended-/Warn-Analysen geben wieder JSON-serialisierbare Auswahlprofile zurück; der Fehler `Object of type AnalysisLimits is not JSON serializable` ist behoben.
- Die Release-Hinweisbox wurde von der Analyse-Webseite entfernt; Release-Details stehen in README/Technical Notes.
- Auswahl-/Risikobox mit Überschrift und Erklärung ergänzt.
- Abbruch einer Analyse bestätigt nun klar, dass die Analyse abgebrochen wurde und eine neue Analyse gestartet werden kann.
- Kurzfazit-/Bewertungsboxen, Ampel-Badges und Statusbereiche wurden im Dark Mode kontrastreicher gestaltet.
- Ampelfarben sind systematischer: grün = ok, gelb/amber = prüfen, rot = kritisch, grau = nicht bewertbar.
- Info-Aufklapper sind layout-stabiler, damit Labels/Überschriften beim Öffnen nicht verrutschen.
- Diagrammblock semantisch überarbeitet: Abschnittserklärung, Info-Texte je Diagramm, Einheiten/Basiswerte direkt an den Balken, menschenlesbare Betriebszustandsdauer.
- Label `95%-Perzentil |Netz|` in der Soll-/Ist-Folge zu `95%-Perzentil Soll/Ist-Abweichung` korrigiert.
- Link `nach oben` führt wieder an den Seitenanfang.
- `zendure-replay.service`: `StartLimitIntervalSec`/`StartLimitBurst` stehen nun korrekt im `[Unit]`-Abschnitt; Kommentar zum optionalen Betrieb präzisiert.
- Keine Änderung am Live-Regelalgorithmus.

## Wichtige Änderungen in V12.8.8

V12.8.8 ist ein kleiner Hotfix für die Analyse-/Replay-Weboberfläche und korrigiert einen JavaScript-Syntaxfehler aus V12.8.7:

- Analyse-Button reagiert wieder zuverlässig.
- Status-/Fortschrittsanzeige und dynamische Auswahlprüfung initialisieren wieder korrekt.
- Dark-Mode-Kontrastkorrekturen aus V12.8.7 bleiben erhalten.

## Wichtige Änderungen in V12.8.7

V12.8.7 ist ein kleiner Hotfix für die Analyse-/Replay-Weboberfläche:

- Analyse-Startbutton wird robuster per JavaScript-Event angebunden.
- Status-/Fortschrittsbox ist im Dark Mode wieder gut lesbar.
- Fehler, Startstatus und Abschlussstatus werden deutlich sichtbar angezeigt.
- Änderung der CSV-Auswahl aktualisiert die Auswahl-/Risikobox dynamisch über `/selection-profile`.
- Der Startbutton wird abhängig von der gültigen Auswahl aktiviert bzw. deaktiviert.
- Keine Änderung am Live-Regelalgorithmus.

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
