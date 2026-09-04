# ZEC V14 – WP2 Graph-Core V3 Live Writer & Integration Foundation

**Stand:** 02.09.2026  
**Status:** Engineering-Handoff; **kein produktiv installierbarer V14-Release**  
**Basis:** verifiziertes ZEC V13.0.3 plus freigegebenes WP1

## 1. Scope

WP2 integriert die in WP1 geschaffene Graph-Core-V3-Persistenz in den bestehenden Measurement-Pfad, ohne die fachliche Regelentscheidung oder Gerätecommand-Semantik zu verändern.

Umgesetzt:

- asynchroner Graph-Core-V3-Livewriter;
- V2/V3/unknown schemabewusste Backendwahl;
- V3-Kompatibilitätsleser für bestehende historische Status-/Graphpfade;
- eindeutige Live-`run_id` je Controllerprozess;
- monotone Sample- und Publish-Zeit für innerhalb-eines-Runs-Latenzen;
- dichte Command-Korrelation in `measurement_raw` statt Eventexplosion;
- sparse Command-/State-/Effect-Intervalle und echte Publish-/Resync-/Neutralization-Events;
- Restart-Grenze für offene sparse Live-Intervalle;
- erweiterte DB-Diagnostik im `ControllerState`;
- Entfernung der wirkungslosen aktiven Registry-Einstellung `MEASUREMENT_DB_MAX_QUEUE_ROWS`, während Legacy-Migration sie weiterhin entfernt;
- Offline-Rebuild auf denselben geschärften V3-Vertrag aktualisiert.

Nicht umgesetzt:

- keine Änderung der fachlichen Regelalgorithmen;
- kein V14-Produktionsinstaller/Cutover;
- keine automatische Mutation einer bestehenden V2-DB;
- keine neue Graph-UI;
- keine vollständige per-Entity-/Multi-Zendure-Livepersistenz;
- keine Retention-Enforcement-Implementierung;
- keine V4-Storage-Härtung/Kompression.

## 2. Backend- und Cutover-Sicherheit

`MeasurementDbWriter` entscheidet anhand des tatsächlich vorhandenen DB-Schemas:

- DB fehlt -> V3 neu anlegen;
- V2 vorhanden -> V2-Kompatibilitätswriter, **keine stille Migration**;
- V3 vorhanden -> V3-Livewriter;
- unbekanntes Schema -> `MEASUREMENT_DB_UNKNOWN_SCHEMA`, fail closed und keine Mutation.

Es gibt kein Dual-Write.

Damit kann WP2 den neuen Writer entwickeln und testen, ohne eine existierende produktive V2-Datenbank unbemerkt umzubauen. Der spätere produktive V3-Cutover bleibt eine separate, kontrollierte Offline-Rebuild-/Installationsaktion.

## 3. Command- und Zeitsemantik

Der einzige WP2-Diff in `controller_logic.py` ist die zusätzliche Erfassung:

```python
self.state.command_publish_monotonic_ns = time.monotonic_ns()
```

Sie liegt im bereits bestehenden Branch, der nur nach einem tatsächlichen Publish ausgeführt wird. Publishentscheidung, Felder, Limits, AC-Modus, Deduplizierung und Effect-Reset bleiben unverändert.

Der Graph Core speichert nun für Live-Daten:

- Wallclock-Zeit für die historische X-Achse;
- `measurement_monotonic_ns` für Samplezeit;
- `command_publish_monotonic_ns` für tatsächliche Publishes;
- `run_id` als Gültigkeitsdomäne der monotonen Zeit und laufzeitlokalen IDs.

Damit sind belastbare Laufzeitdifferenzen innerhalb eines Runs möglich, ohne Publish mit Geräteempfang oder Wirkung gleichzusetzen.

## 4. Data-Placement-Finding und Korrektur

Der erste WP2-Prototyp erzeugte bei 10.000 dynamischen Samples ca. 12.000 vermeintlich sparse Command-Events, weil Desired- und numerische Readback-Zieländerungen als Events materialisiert wurden.

Dies wurde korrigiert:

Dense in `measurement_raw`:

- `command_desired_sequence_id`;
- `command_publish_event_id`;
- `command_desired_target_dw`;
- `command_readback_target_dw`.

Sparse:

- Command-Lifecycle;
- Effect-State;
- Desired Intent;
- Readback SmartMode/AC-Mode;
- Match/Mismatch und Mismatch-Felder;
- echte `PUBLISHED`-/`RESYNC`-/`NEUTRALIZATION`-Events.

Damit wird die DB kleiner und gleichzeitig der synchrone Soll->Readback->physische-Wirkung-Zeitbezug besser abfragbar.

## 5. Restart-Finding

Offene sparse Intervalle eines beendeten Controllerprozesses dürfen nicht über eine Downtime hinweg scheinbar weitergelten.

Beim ersten Sample eines neuen Live-Runs werden daher offene Intervalle älterer `LIVE`-Runs am letzten persistenten `graph_runs.end_ms` abgeschlossen. Die Downtime wird nicht mit erfundenem Zustand überbrückt. Reconstructed/V4-Runs werden dabei nicht verändert.

Ein eigener Regressionstest deckt den Fall ab.

## 6. Settings-/Technical-Debt-Cleanup

`MEASUREMENT_DB_MAX_QUEUE_ROWS` war in der Registry als `remove_no_runtime_effect` markiert, wurde vom produktiven Writer aber nie aus der Runtimekonfiguration gelesen. WP2 entfernt den Key aus der aktiven Registry und dem generierten Snapshot.

Die Legacy-Migrationsautorität enthält den Key weiterhin in `LEGACY_REMOVE_NO_EFFECT_KEYS`, sodass alte Configs deterministisch bereinigt werden.

Registry-Setting-Count: **212 -> 211**.

Der tatsächliche Writer besitzt weiterhin einen internen, getesteten Queue-Vertrag mit `DEFAULT_MAX_QUEUE = 5000`; dies ist jetzt klar eine Implementierungskonstante und kein wirkungsloses Benutzer-/Migrationssetting.

## 7. Tests

WP1-Gate:

- 819 Tests PASS
- 681 Subtests PASS

WP2 final:

- **829 Tests PASS**
- **679 Subtests PASS**
- normaler Full-Suite-Lauf: **32.52 s**
- Full Suite mit `ResourceWarning` als Error: **829 PASS / 679 Subtests PASS, 31.90 s**
- WP1+WP2 targeted unter ResourceWarning: **21 PASS**
- `python -m compileall -q .`: **PASS**

Die Reduktion um zwei Subtests ist die erwartete Folge der bewussten Entfernung eines Registry-Settings. Die Legacy-Migration des entfernten Keys bleibt separat getestet.

### ResourceWarning-/Shutdown-Finding

Die abschließende Warning-Prüfung deckte eine **testseitig** nicht geschlossene `sqlite3.Connection` in `test_v14_graph_core_v3_wp2.py` auf. Die Connection wurde auf expliziten `try/finally -> close()`-Lifecycle umgestellt.

Danach beendet sich die komplette Suite auch unter `-W error::ResourceWarning` sauber mit Exit Code 0. Eine zurückgelassene produktive Measurement-Writer-Threadinstanz war im finalen reproduzierbaren Zustand nicht vorhanden.

## 8. Storage-Benchmark – REAL vs scaled INTEGER

100.000 identische fachliche Samples, 5 Query-Wiederholungen:

| Kennzahl | REAL | scaled INTEGER |
|---|---:|---:|
| DB-Größe | 14,409,728 B | **7,225,344 B** |
| Bytes/Zeile | 144.097 | **72.253** |
| Write | **1.440 s** | 1.561 s |
| 24-h Query Median | 33.694 ms | **31.703 ms** |
| 48-h Query Median | 76.506 ms | **73.444 ms** |

DB-Reduktion: **49.86 %**.  
`integer_selected_if_no_regression = true`.

Damit bleibt `scaled_integer_v1` der bestätigte V3-Storagevertrag.

## 9. V3-Livewriter-Benchmark

10.000 dynamische Live-Samples mit einem tatsächlichen Publish je 20 Samples:

- Raw: **10,000**
- 1-min Buckets: **501**
- echte `PUBLISHED` Events: **500**
- sparse Intervalle: **10**
- Rows dropped: **0**
- `integrity_check`: **ok**
- DB-Größe nach sauberem Close: **1,142,784 B**
- WAL nach Close: **0 B**
- effektiver Durchsatz: **5,350.3 Rows/s**
- Enqueue Median: **0.0172 ms**
- Enqueue p95: **0.0442 ms**
- Enqueue p99: **0.1587 ms**
- Enqueue Maximum: **3.8444 ms**

Der Benchmark begrenzt die Queue bewusst auf <4000 Einträge und misst damit sustained throughput statt eines unrealistischen >5000-Zeilen-Instant-Bursts gegen die absichtlich begrenzte Queue.

## 10. Offline-Rebuild-Gate

50.000 Measurement-V4-Samples einschließlich des bestätigten **307-Byte `TRAILING_NUL_PADDING`**:

- Rows gesehen/importiert: **50,000 / 50,000**
- Raw: **50,000**
- 1-min Buckets: **2,501**
- Runs: **1**
- Command Events: **500**
- sparse Intervalle: **3,403**
- Source Errors: **0**
- Invalid Numeric Fields: **0**
- `TRAILING_NUL_PADDING`: **307 B**
- `integrity_check`: **ok**
- DB-Größe: **5,251,072 B**
- Rebuild-interne Dauer: **4.082 s**
- gemessene Wallclock: **4.96 s**
- Peak RSS: **101,832 kB** (~99.4 MiB)

Die bestehende NUL-Regel bleibt eng: nur ein ausschließlich aus NUL bestehender EOF-Suffix direkt nach vollständigem Record-Terminator wird toleriert und protokolliert; Embedded-NUL bzw. Daten hinter einem NUL-Block bleiben Fehler.

## 11. V4-No-Regression

Measurement V4 wurde nicht um neue Felder erweitert:

- `STANDARD_HEADER = 246`
- `EXTENDED_HEADER = 249`

Die neuen monotonic-/Graph-Core-Daten werden nicht in den V4-Vertrag gedrückt.

## 12. Source-Diff / No-Regression

Gegen das ursprüngliche V13.0.3-Manifest:

- 407 Manifest-Einträge geprüft;
- 0 ursprüngliche Dateien fehlen;
- 9 ursprüngliche Dateien sind absichtlich verändert:
  - `controller_logic.py`
  - `generated/SETTINGS_REGISTRY_SNAPSHOT.json`
  - `measurement_db.py`
  - `settings_registry.py`
  - `state.py`
  - vier bestehende Registry-/Regressionstests.

Der vollständige Diff von `controller_logic.py` enthält genau die eine zusätzliche monotone Publish-Zeile. Damit ist die Live-Regel-/Commandentscheidung selbst unverändert.

Gegen WP1 wurden zusätzlich `graph_core_v3.py`, `tools/rebuild_graph_core_v3.py` und der WP1-V14-Test an den geschärften Data-Placement-Vertrag angepasst sowie `graph_core_v3_live.py` und der WP2-Test neu hinzugefügt.

## 13. Bekannte Restpunkte

- Noch kein produktiver V14-Rebuild-/Cutover-Installer.
- Eine bereits vorhandene V2-DB wird absichtlich weiter als V2 betrieben; dadurch wird WP2 allein auf der Produktivinstallation noch nicht zum V3-Cutover.
- V3-Kompatibilitätsreader hält existierende Status-/Graph-History-Verträge funktionsfähig, ist aber noch nicht der geplante V14 Query Service.
- Multi-Zendure-/per-Entity-Schema ist vorbereitet; vollständige instance-aware Livebefüllung steht noch aus.
- Topologie-Livehistorie bildet derzeit mindestens `zendure_unit_count` ab; der reichere Entity-/Rollenvertrag folgt später.
- `graph_retention_ledger` ist Foundation; Retention-Enforcement ist noch nicht implementiert.
- Keine neue Graph-UI, Guided View, Inspector oder Comparison in WP2.
- Keine Produktionsinstallation aus diesem Engineering-Paket.

## 14. Final-Package-Testharness-Gate

Der zuvor sporadisch beobachtete Hänger nach bereits vollständig ausgegebenem pytest-Ergebnis wurde auf einen externen, global auto-geladenen Testharness-Plugin eingegrenzt. Im hängenden Prozess blieb u. a. ein `TelemetryWriter`-Thread des im Engineering-Container installierten `ddtrace`-Pakets aktiv. `ddtrace` ist keine ZEC-Abhängigkeit.

Aus dem frisch entpackten WP2-Paket wurden deshalb drei vollständige Läufe mit ausschließlich diesem externen Plugin deaktiviert ausgeführt (`-p no:ddtrace`): jeweils **829 Tests / 679 Subtests PASS**, Exit Code 0. Ein zusätzlicher vollständiger `ResourceWarning`-Gate lief ebenfalls mit **829 / 679 PASS**, Exit Code 0. Die Testzahl bleibt unverändert.

Klassifikation: `TEST_HARNESS_EXTERNAL_PLUGIN`; kein verbleibender ZEC-Writer-/Lock-Lifecycle-Defekt nachgewiesen. Details: `validation/V14_WP2_FINAL_PACKAGE_GATE.txt`.

## 15. Exit-Gate

**WP2 ENGINEERING EXIT-GATE: PASS**

WP2 ist als Entwicklungsfoundation abgeschlossen. Die Quellbasis bleibt absichtlich bei `APP_VERSION=13.0.3` / `APP_BUILD_ID=v13.0.3-20260814`, da noch kein produktiver V14-Release erzeugt oder installiert wird.
