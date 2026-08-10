# Zendure Energy Controller V12.12.2

**Build-ID:** `v12.12.2-20260810`

V12.12.2 konsolidiert zwei bereits im Entwicklungschat bestätigte Status-/Graph-UX-Feldbefunde mit vier bestätigten Produktivbefunden aus der V12.12.0-Analyse. Schwerpunkt sind eine hostweit eindeutige produktive Controller-Ownership, reale monotone Harvest-Zeitsemantik mit frischen/distinkten Beobachtungen, konsistente Harvest-Diagnose, belastbare Measurement-Manifestdaten sowie zwei gezielte Status-/Graph-UI-Korrekturen.

## 1. Single-Instance / Command Owner

Vor Config-Laden, MQTT-Start, Measurement-Writer, Webserver und Regelzyklus muss der Prozess einen absoluten hostweiten Kernel-Lock erwerben:

```text
/opt/zendure-controller/zendure_controller.instance.lock
```

Der Pfad ist unabhängig vom aktuellen Working Directory. Ein zweiter Prozess endet fail closed mit Exit-Code `73`; er erzeugt weder produktiven Measurement-Stream noch Gerätekommandos. Die Datei selbst darf dauerhaft existieren: authoritative Ownership ist der Kernel-`flock`, der bei sauberem Close wie auch bei hartem Prozessende automatisch freigegeben wird.

Owner-PID und Build-ID werden in `/health`, `/ready` und `Controller & Schnittstellen` diagnostisch ausgewiesen.

## 2. Harvest-Zeitsemantik

Entry-/Hold-Hysterese verwendet nicht mehr nominelle Sekunden aus gezählten Regelzyklen. Zeitfortschritt basiert auf `time.monotonic()` und wird nur bei einer neuen Quellbeobachtung berücksichtigt.

- wiederholte identische Quellbeobachtungen zählen nicht erneut;
- Wall-Clock-Sprünge beeinflussen die Zeitführung nicht;
- nach einem langen Host-/Prozess-Stall wird nicht die gesamte Stallzeit als Folge vieler Beobachtungen gutgeschrieben;
- bei normalem 3-s-Zyklus bleibt das bisherige nominelle Timing erhalten.

Die Harvest-Leistungs-/Zielwertformeln bleiben unverändert.

## 3. Harvest-Diagnose

`harvest_limiter_reason` ist wieder ein Current-State-Feld. Bei deaktiviertem/nicht anwendbarem bzw. zurückgesetztem Harvest wird kein alter Limitergrund als aktueller Zustand fortgeführt.

## 4. Measurement-Manifest

Der V4-Writer pflegt den Manifest-Lifecycle nun aus seinem eigenen Writerzustand:

- tatsächlicher Rotationsgrund für neu eröffnete Dateien (`SIZE_LIMIT`, `HEADER_CHANGED`, Fallback-Wechsel usw.);
- finaler `row_count` aus dem Writer-eigenen Zähler;
- `closed_time_utc` bei sauber abgeschlossenem File;
- bei hartem Prozessabbruch bleibt `closed_time_utc` leer und der offene Zustand ist erkennbar.

Dafür wird **kein Dateivollscan im Live-Regelpfad** eingeführt. Measurement-V4-Header und Feldvertrag bleiben unverändert.

## 5. Status-/Graph-UX

### Controller & Schnittstellen

Desktop verwendet nun ein klickfixiertes Diagnosepanel statt eines Hover-Lebenszyklus. Mausrad und Scrollbar scrollen den Panelinhalt; `×`, Escape oder Klick außerhalb schließen es. Das mobile Panel aus V12.12.1 bleibt erhalten.

### Mobiler Speicher-SOC-Tagesgraph

Auf kleinen Viewports überdeckt die Messwertanzeige den untersuchten Plot nicht mehr. Auswahlmarkierung und Kurven bleiben im Canvas sichtbar; die Detailwerte werden darunter angedockt. Desktop behält den schwebenden Tooltip.

## 6. Settings Help bleibt erhalten

V12.12.1 Help-/Terminologie-/Glossar-, Such-, Default-/Profil-, Compound-Validation- und Mobile-Settings-Verträge bleiben unverändert. Das bestehende V12.12.1-Handbuch bleibt die aktuelle Settings-Hilfeedition dieses Bugfix-Releases.

## 7. No-Regression

Explizit geschützt sind insbesondere:

- AUTO_GRID_EXPORT / AUTO_GRID_IMPORT / HOLD und Totzonenkonvergenz;
- Harvest `SMA_FULL_OR_IDLE`-/`SMA_NEAR_LIMIT`-Absolutzielbildung, High-SOC-Share/Export-Capture, Floor/Restart/Near-Limit und Primärspeicherpriorität;
- proportionale/symmetrische Cross-Charge-Korrektur;
- NIGHT_DISCHARGE, Reserve-SOC, aktive 0-W-Neutralisierung und Folgeübergang;
- MAX_SOC als normaler Limiter/HOLD;
- Command-Effect-/Readback-/Resync-/SmartMode-/Gegenlimitvertrag;
- Measurement-V4-Header/Contract;
- Excel-Lernsimulation.

Der externe 14-Minuten-Raspberry-Backup-/Host-Freeze ist ausdrücklich kein ZEC-Fix-Scope. Ebenso werden keine zusätzliche Installed-Tree-Provenance und kein V3-Legacy-Cleanup eingeführt.

## 8. Releasebelege

Siehe:

```text
README_INSTALLATION.md
BUILD_VALIDATION_V12_12_2.md
RELEASE_INFO_V12_12_2.md
TECHNICAL_NOTES_V12_12_2.md
ZEC_V12_12_2_RELEASE_REPORT.md
SPEZIFIKATION_ZEC_V12_12_2_SINGLE_OWNER_HARVEST_MANIFEST_UI_FINAL.md
V12_12_1_TO_V12_12_2_CHANGED_FILES.txt
```
