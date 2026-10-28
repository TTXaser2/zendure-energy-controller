# ZEC Battery Care – CP23 historischer SOC-Tagesgraph

**Status:** 27.10.2026 · `ZEC-BL-BATCARE-001` · `ENGINEERING_AS_BUILT / DEVELOPMENT_NOT_INSTALLABLE`

## Datenprovenienz

- CP22 `graph_config_timeline`: R/N/E, Saisonfenster und An/Aus werden nur aus *damals* dokumentierter Konfiguration gelesen; Legacy-`NULL`, Care-Off, außersaisonal oder formal unplausible Schwellen erzeugen **keine Care-Linie**. Eine heute konfigurierte Reserve darf keinen historischen Tag rückwirkend umdeuten. Für den Tagesgraph ist `care_day_lines()` rein lesend.
- Die vorhandenen historischen Tagesgraph-Messpunkte liefern die beobachtete `mode`-Zeitfolge. Die zusätzliche AUTO-Untergrenze `max(historisches MIN_SOC, historisches R)` wird nur über zusammenhängende, tatsächlich erfasste `AUTO`-Beobachtungen mit jeweils höchstens drei Minuten Abstand und ohne dazwischenliegenden STOP/Unknown-Mode angezeigt. Ein einzelner AUTO-Punkt ergibt keine Dauerlinie. Das ist **rekonstruierte Policy-Anwendbarkeit**, weder Geräte-Readback der App/BMS-Entladegrenze noch Nachweis physischer Wirkung. Bei NIGHT, FIXED, STOP, ausgelassener Mode-Provenienz und historischen Lücken erfolgt in CP23 keine Care-Line-Fortführung.
- Das bestehende `OperationalEventJournal` bleibt die einzige persistente Incidentautorität. Für den gewählten Tag liest CP23 **schreibgeschützt und zeitlich begrenzt** nur `battery_care_emergency_failure` mit echten `started_at`-/`ended_at`-Zeitstempeln. Start ist `failure_confirmed`, gespeichertes `resolved`/Ende `reserve_recovered`. Es werden keine Ereignisse aus Publish, ACK oder einer schlichten SOC-Schwellenkreuzung synthetisiert. Altbestände ohne Tabelle / DB erhalten `not_recorded`, Fehler `unavailable`, keine fiktiven Marker. Eine abrupte Kaltabschaltung während tatsächlich ungesichertem Datenbankschreiben kann nicht aus dem Graphen „repariert“ werden.

## Darstellung und mobile Semantik

- Bestehender `Speicher-SOC Tagesgraph` in `status_page_v2.py` erhält den Knopf **Care-Details** (`aria-pressed`). Standard: maximal eine zusätzliche dezente Care-AUTO-Untergrenze aus der abgegrenzten Policy-Zeitreihe. Details: N-/E-Schwellen in ihren echten Konfigurationssegmenten sowie Ereignismarker der persistierten Notlade-Nichtwirkung bzw. bestätigten SOC-Reserve-Wiederherstellung. Ein Marker ist keine Ladeleistungsmessung.
- Beschriftung lautet ausdrücklich `Care AUTO-Untergrenze (konfiguriert)`; Tooltips unterscheiden tatsächliche SOC-/Power-Messreihen von Schwellen und gespeicherten Ereignissen. Bestehende MIN/MAX/Nachtgrenzen, Primärspeicher-Graph, SOC-Gap-Splitting, Desktop-Tooltip und mobiles Detailpanel bleiben erhalten. Der SOC-Tagesgraph ruft keine zusätzliche 1-Hz-Messung ab.
- Der Browser-Cache erhält eine neue Version, damit das alte Sitzungsobjekt ohne Care-Historie nicht als unveränderter Tagesstand wiederverwendet wird.

## Scope, Restarbeiten und Gategrenzen

- Nur `battery_care_graph_history.py`, Tagesgraph-Dekorator, Status-V2-HTML/JS/CSS, Tests, Entwicklungs-As-built und kanonisches Ledger. Keine Änderung an Steuerbefehlen, Policy-Schwellen, Command-/Safety-/MQTT-/Readback, Runtime-Sampling, Operational-Events-Schreibern oder produktiven Datenbanktabellen.
- Grafische Zusatzlinie in CP23 ist bewusst auf belegtes AUTO begrenzt; die zusätzliche historisch korrekte NIGHT-Untergrenze und das vollständige Ereignisinventar aller Care-Stufen mit separatem Start-/End-Journal bleiben eigenständige Nacharbeiten. Ohne solches Journal werden PV-/Netzpflege-Episoden nicht erfunden. Der vorhandene UML-Regleratlas betrifft Command-/Control-Laufzeit und wird von diesem reinen Graph-/Read-Only-Block nicht verändert; Graph-Read-Flow ist in dieser Entwicklungs-As-built dokumentiert. Finale UML-Visualreview und Releasestand bleiben offen.
- Tests/Browsergeometrie/Library-Sicherungs- und Gesamtregressions- sowie Feld- und Releasegates werden separat als **tatsächlich ausgeführte** Artefakte dokumentiert. Produktiv-Pi V17.1.3 bleibt unverändert. Termius-iPhone-Installationsanleitung erst zum technischen freigegebenen Installationspaket.
