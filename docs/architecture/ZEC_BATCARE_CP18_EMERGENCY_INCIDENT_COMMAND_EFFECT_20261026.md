# ZEC Battery Care – CP18 Notlade-Command-Effect / Incident-Bridge (Entwicklungs-As-built)

**Stand:** 26.10.2026 · **Freigabe:** `DEVELOPMENT_NOT_INSTALLABLE` · **Sourcebasis:** extern geprüfter CP17 · **Master-Ledger:** `ZEC-BL-BATCARE-001` in `05_ZEC_BACKLOG_AND_ROADMAP.md`.

## Quellengebundener Datenfluss

1. Die laufende Stufe-3-Episode liegt im vorhandenen `CareEpisodeStore` (gleiche Operational-Events-SQLite-DB) mit beim Start fixiertem `target_reserve_soc`. Das Grid-Intent geht nur über `_battery_care_grid_dispatch()` und `_publish_signed_target()`.
2. Erst `_mark_mismatch()` des **vorhandenen** Command-Effect-Monitors bei bestätigter positiver Lade-Nichtwirkung korreliert `DesiredCommandBatch.reason == BATTERY_CARE_EMERGENCY`, positiven identischen Zielwert, aktive Grid-Care-Intention und aktive Stufe-3-Episode. 0-W-, Fremd-/S2-/PV-Ziele öffnen keinen Notladevorfall. Diese Ergänzung sendet selbst keinerlei Gerätekommando.
3. Das erstmalige bestätigte Failure-Signal pro Episode wird mit einer Event-ID und dem **ursprünglichen** Reserve-SOC im `ControllerState` latched. `snapshot()` exponiert `care_emergency_failure_confirmed`, `care_emergency_failure_event_id`, `care_emergency_failure_reason`, `care_emergency_incident_reserve_soc`, `care_episode_id`. `care_soc_sample_id` basiert auf dem realen SOC-Ingestion-Zeitstempel, **nicht** auf UI-/Event-Pollzeit. Für `care_physical_charge_confirmed` werden frische, unabhängig gerichtete AC-Istleistung **und** frischer positiver Batteriepack-Ladefluss verlangt.
4. Der bereits vor CP18 vorhandene `_observe_battery_care_incident()` im `OperationalEventJournal` übernimmt das bestätigte Failure-Signal in den bestehenden `operational_events`-Store. Offen bleibt der Notladevorfall über Restart, STOP, Care-Off, Saisongrenzen und zwischenzeitliche physische Ladung; Recovery verlangt zwei unterschiedliche frische SOC-Ingestion-IDs und mindestens drei Sekunden monotonic elapsed time bei `SOC >= incident_reserve_soc`. Die beim Incident gespeicherte Reserve wird auch bei späterer Konfigurationsabsenkung **nicht** überschrieben.
5. Vorhandene `/operational-events`-, Status- und Warnkomponenten erfassen weiter offene `severity=error`-Events auch jenseits der normalen Tageauswahl. Keine zusätzliche Notlade-UI-Karte und kein zweiter Eventstore.

## Grenzen / offene Gates

- **Noch kein physischer Nachweis** der Netzladung oder der erfolgreichen BMS-Ladeannahme; ein positiver Sollwert bleibt `REQUESTED`, kein Wirkungs-PASS.
- Journal arbeitet best-effort im vorhandenen 2-s-Observer: bei plötzlichem Stromausfall **zwischen** Watchdog-Bestätigung und SQLite-Commit gibt es noch kein garantierendes synchrones Write-Ahead; dieser Persistenz-Race ist als verbleibendes Risiko für die spätere Release-/Fault-Injection-Prüfung offenzulegen und nötigenfalls abzusichern.
- Es fehlen die vollumfängliche kompakte Care-Status-UX, SOC-Graph-/Historiensemantik, updatefähiger UML-Atlas, Release-/Installer-/Feldgates. Unveränderte produktive Installation V17.1.3.

## Quellprüfungen

- Fokussierte Controller+SQLite+Source-Frische-/Incident-/Restart-/Netz-Gates: 36/36 PASS.
- Vollständiger `unittest discover` mit `-W error::ResourceWarning`: **1.040/1.040 PASS**, Laufzeit 42,1 s, CP18 QA-Log separat.
- Änderung an veröffentlichter Produktquelle: **keine**. Kein realer Installationslauf; keine Aussage über Hardware-Wirksamkeit.
