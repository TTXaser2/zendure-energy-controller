# ZEC Battery Care – CP22 zeitkorrekte Konfigurationsprovenienz des SOC-Tagesgraphs

**Status:** 26.10.2026 · `ZEC-BL-BATCARE-001` · `ENGINEERING_AS_BUILT / DEVELOPMENT_NOT_INSTALLABLE`

## Konkreter Sourcevertrag

- `csv_logger.py`: Alle sieben Care-Konfigurationsschlüssel sind nun Bestandteil von `CONTROL_HASH_KEYS`. Saisonstart/-ende, Ein/Aus, R/N/E oder Netzladeleistungscap unterscheiden den `config_control_hash` schon dann, wenn die übrigen SOC-Limits unverändert bleiben. Bestehende Measurement-V4-Schema-/Messwertspalten bleiben unverändert. Historische ältere Hashes behalten ihre frühere Bedeutung; **kein Hash-Rewrite** alter Messdaten.
- `graph_config_timeline.py`: Die bestehende SQLite-Tabelle `graph_config_timeline` besitzt zusätzlich `care_enabled`, `care_start`, `care_end`, `care_r`, `care_n`, `care_e`. Die Migration fügt fehlende Spalten einzeln hinzu; alte Zeilen bekommen SQL-`NULL`, niemals den heute konfigurierten Wert. Lesende Abfragen mutieren eine alte Datenbank nicht.
- `overlay_from_parameters` bildet `care_enabled` nur aus tatsächlichem Python-`bool` auf 0/1 ab; fehlende/nicht belegbare Provenienz bleibt `NULL`. Die sechs Felder werden über Runtime-Schreiber, Backfill, Query, Semantikvergleich und Graph-Konfigurationssegmente unverändert propagiert. Die siebenfach gehashte Netzladeleistungsgrenze bleibt eine dokumentierte Konfigurationsänderung, wird aber **nicht als SOC-Linie** dargestellt.
- Care-Segmentwechsel werden auch dann nicht wegoptimiert, wenn `MIN_SOC_PERCENT`, `MAX_SOC_PERCENT` und die Nachtreserve gleich bleiben. Ein unbekannter Care-Wert innerhalb eines bekannten historischen Grund-SOC-Segments wird ausdrücklich nicht als Care-Aus ausgelegt.
- Für Vergangenheitsdaten ohne Care-Snapshot oder ohne frühere Care-Spalten bleibt Care **historisch unbekannt**. Nur das Tagessegment, in dem `now_dt` liegt, darf aus der derzeitigen effektiven Konfiguration einen *jetzt wirksamen Konfigurationsstand* ergänzen. Das ist keine Bestätigung physischer Lade- oder Entladewirkung.

## Sicherheits-/Releasegrenze

**Keine Änderungen** an Batterie-Sollwerten, Command-/Safety-/Readback-Pfaden, Incident-Logik, Einstellungen, produktivem SQLite-Schema der Operational Events oder MQTT. Keine rückwirkend rekonstruierte Battery-Care-Schwelle auf dem SOC-Graphen. Historische R/N/E-Linien und Care-Ereignismarker sind erst nach gesondertem Quellen-/Frontend-/Legendenvertrag mit echten Zeitpunkten darzustellen. Die Care-Policy-Konfiguration allein belegt nicht, ob Care zu jedem Zeitpunkt tatsächlich wirksam war (STOP, Quelle stale, Out-of-Season oder MANUAL).

## Nachweise und offene Arbeit

- Legacy-SQLite-Migration, Idempotenz, alte Snapshots, `NULL` vs. disabled, sieben einzelne Hashänderungen, historische Segmentwechsel, nicht rückwirkende Tagesprojektion durch neue `tests/test_battery_care_historical_config_provenance.py` geprüft.
- Alle vorhandenen Graph-Core-/V13-Timeline-Funktionen bleiben erhalten; vollständige `unittest`-/ResourceWarning-Regression wird als getrenntes QA-Artefakt nach Sourcefreeze dokumentiert.
- UML-Impact: Graph-Config-Timeline-/Measurement-Historienquellen wurden geändert. Bestehender UML-Regleratlas beschreibt primär den Command-/Control-Pfad, dessen Diagramme bleiben in diesem Block unverändert; die Graph-History-Ablaufdarstellung und erneute Gesamt-UML-Abnahme gehören zwingend zum kommenden Graph-Visualisierungs- und Releaseblock. Kein `DOC_UML_RELEASE_GATE` behauptet.
- Weiter offen: UI-Graphlinien/-marker, Marker-Persistenz/Quellenprovenienz, Browser-/iPhone-/Responsive-Visualgate, echte Feldhistorie, Release-/Installer-Gates. Pi verbleibt auf V17.1.3, Termius-Ferninstallation erst bei freigegebenem Installerpaket.

Master-Ledger-Autorität bleibt allein `05_ZEC_BACKLOG_AND_ROADMAP.md`, dort unverändert `ZEC-BL-BATCARE-001`.
