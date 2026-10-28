# CP25 – Battery-Care-Stufenereignisse und SOC-Graph-Marker

**Stand:** 27.10.2026 · Entwicklungs-As-built · `DEVELOPMENT_NOT_INSTALLABLE` · Basis: extern gesicherter CP24 (SHA256 `be5268578b7ed3c3a0768d47bf7e7935d01bb11122d847ca4463110e780fea48`).

## Quellenbeweis und Sicherheitsvertrag

- Neue rein diagnostische Komponente `battery_care_stage_events.py`: ermittelt Stufen ausschließlich aus `ControllerState.snapshot()` mit übereinstimmenden `loop_counter` und `care_completed_cycle_id`, letztere erst mit dem bereits vorhandenen `set_cycle_timing()` nach dem abgeschlossenen Regelzyklus veröffentlicht. In-flight-Snapshots, wiederholte Polls derselben Zyklus-ID, hypothetische PV-Shadow-Ziele und MQTT-Publish/ACK sind **keine Ereignisnachweise**.
- Quelle für positive Stufen: tatsächliches `care_dispatched_stage` (`PV_PRIORITY_REQUESTED`, `GRID_REQUESTED`, `EMERGENCY_REQUESTED`) **mit positivem über den einzigen Command-Owner angefordertem Ziel** und gleichzeitig gültiger `care_policy_valid`-Policy. Der separat vorhandene `RESERVE_POLICY`-Zustand dokumentiert die wirksame konfigurierte Policy-Untergrenze; `STOP_HOLD` dokumentiert einen beobachteten Controller-STOP, `NONE` die fehlende bestätigte Care-Policy/Anforderung. Keiner dieser Zustände ist eine Hardware-Wirkungsbestätigung.
- `OperationalEventJournal` fordert zwei **verschiedene abgeschlossene Reglerzyklen** derselben Stufe/Untergrenze, ehe ein Wechsel als `battery_care_stage_transition` im existierenden SQLite-Eventstore gespeichert wird. Es gibt keine weiteren Care-Gerätekommandos oder zusätzliche MQTT-Publisher.
- Ein eindeutiger persistenter Singleton-Cursor (`battery_care_stage_cursor`, `id=1`) merkt Stufe, Untergrenze und letzte Event-ID über Journal-/Prozessneustarts; Eintrag und Cursorwechsel erfolgen in derselben kurzen SQLite-Transaktion (`BEGIN IMMEDIATE`). Identische Zustände werden nicht dupliziert. Das erste generische NONE/STOP ohne vorherige Care-Aktivierung erzeugt keinen Marker. Im Datenbankfehlerfall wird die Kandidatenstufe nicht fälschlich als persistiert bestätigt. Beim Neustart werden laufende Probenzähler nicht als frisch übernommen; erst neue abgeschlossene Zyklen dürfen einen fehlenden Übergang nachtragen.
- Einwechsel zwischen PV/Grid/Emergency, Reserve-Policy, STOP und Ende sowie eine **Änderung der wirksamen Reserveuntergrenze** erhalten je eine separate gespeicherte Übergangszeile. Normale Leistungsrampen innerhalb derselben Stufe führen zu keinem Event-Spam. Der Zeitstempel bezeichnet die **persistierte Erkennung** nach Entprellung, nicht die physikalische Schaltsekunde.

## Historische Darstellung

- `care_day_incidents()` ergänzt aus denselben persistenten Events read-only Markierungen `kind=stage_transition`, ausschließlich wenn strukturierte `stage_from`, `stage_to`, Provenienz und `physical_effect_confirmed=false` glaubwürdig vorliegen. Alte Einzelvorfall-Schemas ohne `detail_json` bleiben für die bereits vorhandenen Notlade-Wirkungsfehler lesbar. Kein Fake-Marker aus historischen SOC-Abfällen.
- Im SOC-Graphen erscheinen die Übergänge weiterhin nur über **Care-Details** (zur Kompaktheit); die Marker und Tooltips kennzeichnen explizit *Regleranforderung, nicht physische Wirkung*. Zeitabhängige R-/N-/E-/AUTO-/NIGHT-Linien aus CP22–CP24 bleiben unabhängig.

## Evidenzgrenzen / Releasegates

- Getestete Unit-/SQLite-Restart-/historische Graph-Provenienz ist kein realer Pi-Process-Powerloss, kein nachgewiesener Stromfluss und kein Batteriewirkungsnachweis. Ein sehr kurzer tatsächlich stattfindender Zustand, der nicht in zwei verschiedenen **abgeschlossenen und beobachteten** Reglerzyklen vorkommt, wird absichtlich nicht als dauerhaftes Ereignis behauptet.
- Ausfall der Ereignis-DB blockiert keine sicherheitskritische Kommandoregelung: das Ereignisjournal ist Diagnostik, kein Command-Gate. Ein beim Crash noch nicht bestätigter/committeter Stage-Marker kann fehlen und muss als Evidenzlücke behandelt werden; bereits persistierte Marker bleiben erhalten.
- Noch offen: vollständige Release-/Visual-/UML-/Datenblatt-/Installer-/Recovery-/Pi-Evidenzgates sowie die unabhängige physische Battery-Care-Wirksamkeit. Produktiver Pi unverändert V17.1.3. Installations- und Rollbackanleitung erst für eine später freigegebene Version, über iPhone-Termius.
