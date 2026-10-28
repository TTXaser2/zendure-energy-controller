# ZEC Battery Care – CP20 As-built: parallele Notlade-Warnvorfälle

**Datum:** 26.10.2026  
**Scope:** `ZEC-BL-BATCARE-001`, Entwicklung auf CP19, `DEVELOPMENT_NOT_INSTALLABLE`  
**Quellautorität:** `operational_events.py`, `web_ui.py`, `tests/test_battery_care_multi_incident.py`, bestehende CP18/19-Tests. Die finale fachliche Battery-Care-Spezifikation bleibt normativ; dieses Dokument beschreibt nur den aktuellen Entwicklungsstand.

## 1. Problem und Änderung

CP19 verwaltete genau den letzten offenen Notlade-Incident und einen einzigen prozesslokalen SOC-Recovery-Kandidaten. Eine weitere unabhängig vom Command-Effect-Watchdog bestätigte Notladeepisode mit neuer Failure-ID wurde bei noch offenem ersten Fall nicht als eigenständiger Event gespeichert. Der neue Entwicklungsstand verwaltet im **bestehenden Operational-Events-SQLite-Store** beliebig viele individuelle `battery_care_emergency_failure`-Datensätze mit jeweils eigenem `failure_event_id`, `incident_reserve_soc`, Status, Verlauf und eigenen Recovery-Zählern.

- Nur der vorhandene Command-Effect-Watchdog kann `care_emergency_failure_confirmed=True` setzen und den Write-through-Pfad auslösen; kein Publish-/ACK-/Readback-basierter Incident und keine zweite Command-Autorität.
- Dedupe-Key ist bei neuem Event `battery_care_emergency_failure:<failure_event_id>`; CP18/CP19-Bestandsdatensätze mit altem gemeinsamen Dedupe-Key bleiben per ihrem gespeicherten `detail_json.failure_event_id` erkennbar. Dieselbe Failure-ID erzeugt keinen zweiten Event, auch nach Resolution nicht.
- `persist_confirmed_emergency_failure()` darf Erfolg nur melden, wenn **seine eigene** ID und die unveränderliche Reserve im SQLite-Commit nachweisbar sind. Geändertes Reserve-Ziel unter derselben ID wird nicht als erfolgreich archiviert behauptet. SQLite-Locks/Fehler verhalten sich unverändert fail-closed.
- Der asynchrone Observer wertet **jede offene Zeile** separat aus. Pro Zeile gilt ihre ursprüngliche Reserve, frischer valider SOC, mindestens zwei unterschiedliche Quellproben und mindestens drei Sekunden bestätigende Beobachtung. Unterbrechung der Frische/Grenze setzt nur den jeweiligen Kandidaten zurück. Neustart übernimmt keine Kandidatenzähler, wohl aber die offenen Ereignisse.
- Bestehendes `list_recent()` priorisiert alle offenen Ereigniszeilen; Battery-Care-Fälle werden **nicht** in die Flap-Kompaktierung anderer Eventtypen aufgenommen. In `build_status_view_payload()` wird ihre Anzahl in einem platzsparenden Warntext ausgewiesen und die einzelne Ereignisliste bleibt vollständig. Der Einzelvorfalltext enthält das maßgebliche Reserve-Ziel.

## 2. Grenzen / Safety

Es wurden keine Änderungen am Reglerentscheid, MQTT-/Command-Publisher, Cross-Charge, SOC-Policy oder am produktiven Gerät vorgenommen. Persistierte Incidents sind **diagnostisch**, keine neuen Befehls-/Notladerechte. Ein DB-Ausfall lässt keine falsche Archivierungsbestätigung zu. Normale Event-Hintergrundbeobachtung und SQLite-WAL bleiben erhalten. Keine Garantie harter maximaler Dateisystem-I/O-Latenz. Das separate technische/visuelle UI-Gate, die vollständige Produktrelease-UML-Abnahme und reale Feld-/Power-Loss-Evidenz bleiben offen.

## 3. QA und Review

Fokussierte Unit-/Restart-/Mehrfach-Episoden-/Historik-/Status-/Parallel-Tests sowie ein mehrfach wiederholter gleichzeitiger Write-through-/Observer-Test. Exaktes Gesamttest- und Bibliotheks-Gate-Ergebnis ist nach dem Checkpoint getrennt im zugehörigen QA-Protokoll zu bewerten; keine Vorwegnahme von `TECHNICAL_BUILD_PASS`.

## 4. Quelle/Provenienz

CP19-Sicherung und seine SHA256 bleiben unverändert. Diese As-built-Ergänzung ist additiv; keine historische Spezifikation, UML oder Ledger-ID wurde entfernt. `05_ZEC_BACKLOG_AND_ROADMAP.md` bleibt die einzige Roadmap-/Backlog-Autorität.
