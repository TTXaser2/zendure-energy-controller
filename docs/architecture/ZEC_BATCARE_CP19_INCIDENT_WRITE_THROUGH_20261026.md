# Battery Care CP19 – Notlade-Warnvorfall mit Write-through (Entwicklungs-As-built)

**Stand:** 26.10.2026 · **Status:** `DEVELOPMENT_NOT_INSTALLABLE` · **Basis:** bytegeprüfter CP18 SHA256 `8fcf20ec041e0280f1f313ad5ed7b3d8b747f2d0f5271e63183e355e1f876888`.

## Technischer Pfad

1. Nur der bereits bestätigende `_mark_mismatch()`-Watchdog korreliert einen positiven Stufe-3-Notlade-Command-Batch mit der aktiven Grid-Episode. Er erzeugt genau eine Failure-ID und hält die beim Episodenbeginn gültige Reserve R unverändert.
2. Der neue `OperationalEventJournal.persist_confirmed_emergency_failure()` speichert beim **ersten** bestätigten Nichtwirkungsereignis direkt über dieselbe `operational_events`-Tabelle mit SQLite WAL, `synchronous=FULL` und kurzer Busy-Timeout-Grenze (0,2 s). Die Hintergrundbeobachtung erhält weiter ihren 2-s-Takt und `NORMAL`. `BEGIN IMMEDIATE` serialisiert konkurrierende Notlade-Inserts mit der Hintergrundbeobachtung.
3. Ein Schreiben gilt erst dann als bestätigt, wenn **genau die eigene Failure-ID** nach dem Commit in SQLite nachweisbar ist. Der State-Snapshot liefert `care_emergency_incident_persisted` und `care_emergency_incident_persistence_error`. Bei Lock/DB-Fehler wird kein persistierter Vorfall behauptet; die nächste echte Watchdog-Nichtwirkungsbestätigung versucht **dieselbe ID** erneut zu sichern.
4. `OperationalEventJournal` bleibt allein für das Öffnen und die spätere Auflösung von Vorfällen zuständig. Reale physische Batterieladung oder ACK ersetzen weiterhin weder die bestätigte Nichtwirkung noch die Wiederherstellung der ursprünglichen Reserve mit frischen unterschiedlichen SOC-Samples.

## Bekannte Abgrenzung und Risiken

- Nur ein bereits bestätigter Nichtwirkungsfall löst den seltenen SQLite-Write-through-Commit im Controllerzyklus aus; ein fehlgeschlagener/schwer verzögerter Dateisystemzugriff lässt sich durch den SQLite Busy-Timeout **nicht** absolut zeitlich begrenzen. Keine Netz- oder Geräteschreiboperation wird hinzugefügt.
- Bei nicht verfügbarem, korruptem oder dauerhaft gesperrtem SQLite-Store bleibt der Warnvorfall **nicht garantiert persistent**; das ist explizit `EVENT_WRITE_FAILED`, nicht `PASS`. Ein dauerhafter Disk-Fehler kann ohne erfolgreiche spätere Wiederholung nicht korrigiert werden.
- Es ist derzeit weiterhin nur **ein gleichzeitig offener** `battery_care_emergency_failure`-Incident pro Journal implementiert. Eine zweite bestätigte Episode während eines noch offenen ersten Vorfalls wird nicht fälschlich als persistiert gemeldet; die eigenständige Multi-Incident-Darstellung bleibt ein offenes QA-/Design-Follow-up vor Release.
- Keine reale Raspberry-Pi-Neustart-, Stromausfall-, Hardware-, UX-, Full-Release- oder Installationsfreigabe folgt aus dieser lokalen SQLite-Integrationsprüfung.

## UML-Impact

Im Atlas `docs/architecture/uml/` sind **08** (Command-Effect/Recovery) und **09** (Komponenten- und Datenfluss) aktualisiert, DOT und die Offline-SVG-/PNG-Darstellung neu erzeugt. Übrige 20 Diagramme fachlich reviewt als unverändert; die frühere V17.1.3-Release-Abnahme wird nicht pauschal auf CP19 übertragen (`MANUAL_RELEASE_GATE=PENDING`).
