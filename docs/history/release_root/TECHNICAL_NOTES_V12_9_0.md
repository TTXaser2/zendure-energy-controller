# Technical Notes V12.9.0

V12.9.0 ist das Grundlagenrelease für `ZEC-MEASUREMENT-V3`. Es ist ein bewusster Breaking Change des Messdaten-/Logging-/Analysevertrags. Die AUTO-Regelstrategie, MQTT-Subscriptions und MQTT-Kommandostruktur werden nicht fachlich geändert.

## ZEC-MEASUREMENT-V3

- Neues CSV-Schema `ZEC-MEASUREMENT-V3` mit Semikolon-Trennzeichen und Dezimalpunkt.
- Eine Zeile entspricht einem Controller-Zyklus.
- Standard und Extended verwenden denselben Header; Extended-Detailfelder bleiben im Standardmodus leer. Dadurch bleiben Dateien auch bei späterem Moduswechsel stabil analysierbar.
- Der Standardmodus enthält vollständige Reglerdiagnose inklusive Roh-/Norm-Kernwerten, Freshness-/Validity-Feldern, Reglerentscheidung, Sollwert-Kaskade, MQTT-Kommando, Istwirkung, `scenario_grid_without_zendure_w` und aggregierter Zendure-MQTT Live-/Retained-/Partial-Stale-Diagnose.
- Der Extended-Modus ergänzt Detail-JSONs für Topic-/Pack-/Unit-/Limiter-/Freshness-Analysen.

## Logging-Betrieb

- Neues Setting `MEASUREMENT_LOG_MODE = off | standard | extended`.
- Alte `CSV_LOG_*`-Config-Keys werden einmalig in die neuen `MEASUREMENT_LOG_*`-Settings übersetzt.
- Settings-/Statusseite zeigen Schema, Modus, Datei, Rotation, freien Speicher, Logging-Status und eine grobe geschätzte Aufbewahrungsdauer.
- Logging ist nachgelagert: Schreibfehler, zu wenig Speicher oder deaktiviertes Logging blockieren die Regelung nicht.

## V2-Breaking-Change

- V2-Dateien werden nicht migriert.
- Analyse/Replay akzeptiert nur `ZEC-MEASUREMENT-V3`.
- Bei V2-Dateien wird eine klare Fehlermeldung ausgegeben.
- Das Update-Script löscht beim V12.9-Update gezielt bekannte alte V2-Messdaten-Dateien im Log-Verzeichnis. Es löscht keine beliebigen CSV-Dateien.

## Tests

Neue Tests prüfen insbesondere:

- V3-Schema und zentrale Pflichtfelder.
- Gemeinsamen Header für Standard/Extended und leere Extended-Detailfelder im Standardmodus.
- Einmalige Legacy-Config-Übersetzung.
- Freier-Speicher-Schutz des Messdaten-Loggings.
- Ablehnung von V2-Dateien im Replay.
- Zendure-MQTT Retained-only/Live-OK-Aggregatdiagnose.

## Nicht enthalten

- Kein Simulator.
- Keine SQLite-/DB-Persistenz.
- Keine V2-Migration und kein V2-Legacy-Parser.
- Keine neue Multi-Zendure-Steuerlogik.
- Keine bewusste Änderung der AUTO-Regelstrategie.
