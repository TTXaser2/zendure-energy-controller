# ZEC V13.0.2 – Hotfix-Spezifikation

**Titel:** Config-State-/Import-UX, CSRF-Lebenszyklus, SQLite-Writer-Härtung und UI-Korrekturen  
**Stand:** 12.08.2026  
**Status:** konsolidierte Spezifikation V1.1 zur Buildfreigabe – noch keine Codeänderung  
**Zielversion:** `13.0.2`  
**vorgesehene Build-ID:** `v13.0.2-20260812`

---

**Revision V1.1 gegenüber V1.0:** Die zuvor aus dem Hotfixscope ausgeschlossenen Punkte
`historische Graphlegendenfolge` und `Audit benutzerseitiger Release-/RC-Bezüge`
sind nun verbindlicher Bestandteil von V13.0.2. Es handelt sich um klar abgegrenzte
Bugfix-/Cleanup-Themen des bestehenden UI-/Dokumentationsvertrags, nicht um neue Features.



## 1. Verbindliche Ausgangsbasis

Ausschließliche Buildbasis ist das tatsächlich ausgelieferte und produktiv installierte Hotfix-Paket:

```text
zendure_controller_v13_0_1.zip
SHA256 = ffd38d3102913f378338bae8337fb356615be9737edb757090bab794042e1bdb
APP_VERSION = 13.0.1
APP_BUILD_ID = v13.0.1-20260811
V13_0_1_SOURCE_MANIFEST.sha256 =
2d7458fdb8a00d6df2c022916ffce8ea7badbcf0469c4f59e2202742a1c21540
```

Die Spezifikation wurde gegen den realen V13.0.1-Code geprüft. Historische Chats oder ältere Releasequellen sind keine Buildbasis.

Versionierung gemäß Projektregel: Fehlerkorrektur innerhalb des bestehenden V13-Themas → `13.0.1 + 0.0.1 = 13.0.2`.

---

## 2. Ziel und Scope

V13.0.2 ist ein eng begrenzter Robustheits-/UX-Hotfix für die in der produktiven V13.0.1-Feldabnahme bestätigten Fehlerklassen:

1. SQLite-Graphstore-Writer kann nach einem externen DB-/Backfill-Schreibkonflikt in einem nicht selbstheilenden Zustand verbleiben.
2. Der SQLite-Status kann einen echten Writerfehler durch nachfolgendes `queued` verschleiern.
3. Lokaler Config-State mit Scope `portable_profile` wird als falscher Artifact-Kind geschrieben und danach selbst als beschädigt erkannt.
4. Beschädigte, aber dateisicher identifizierbare Config-States sind über UI/API nicht löschbar.
5. Config-State-/Import-Unterdialoge besitzen keinen korrekten Parent-Modal-Stack.
6. Fehler innerhalb eines Modals werden nur als schlecht sichtbarer globaler Toast angezeigt.
7. Lang geöffnete Settings-Seiten können nach Ablauf des CSRF-Cookies mit `CSRF_TOKEN_INVALID` ausfallen.
8. Ein Preview ohne wirksame Änderung bietet trotzdem einen Commit an.
9. `INHERITED_DEFAULT_CHANGED` kann wegen unterschiedlicher Resolve-Semantik fälschlich ausgelöst werden.
10. Benutzerterminologie `Teilbares Profil` wird auf `Verteilbares Profil` umgestellt.
11. Historische Graphlegenden deduplizieren wiederkehrende Konfigurationswerte global und können dadurch eine reale Folge wie `99 % → 80 % → 99 %` fälschlich als `99 % → 80 %` darstellen.
12. Benutzerseitig sichtbare UI-/Hilfetexte und das aktuelle Benutzerhandbuch enthalten historische Release-/RC-Bezüge ohne aktuellen Bedien- oder Diagnosemehrwert.

Der Live-Regelalgorithmus wird durch diesen Release **nicht verändert**.

---

## 3. Feldbefunde / reproduzierte Evidenz

### 3.1 SQLite-Writer

Produktiver V13.0.1-Befund:

```text
Controllerstart/Installation: 11.08.2026 ca. 22:42
letzter erfolgreicher SQLite-Punkt: 11.08.2026 22:42:34
rows_written nach Start: 6
SQLite-Status danach: queued
Queue: ca. 1
CSV-V4-Protokoll: weiter aktiv
```

Die produktive SQLite-Datei war gesund:

```text
PRAGMA quick_check = ok
```

Der reale V13.0.1-`write_points()`-Pfad schrieb gegen eine Onlinekopie derselben DB erfolgreich.

Nur der Controllerprozess hielt die produktive DB/WAL/SHM offen; kein Backfill- oder Fremdprozess war nach dem Vorfall noch aktiv.

Ein geschützter UI-Dienstneustart stellte den Writer sofort wieder her:

```text
MANUAL_WEB_SERVICE_RESTART vorhanden
SQLite letzter Write danach wieder aktuell
```

Die entstandene Lücke wurde erfolgreich aus Measurement V4 rekonstruiert:

```text
Lücke: 11.08.2026 22:42:34 → 12.08.2026 10:16:43
Dauer: 11,569 h
fehlende CSV-Zeitpunkte: 13.659
Duplikatkonflikte: 0
quick_check nach Reparatur: ok
größte Restlücke: 9,717 s
Graph: 721 Minutenpunkte, 00:00 → 11:59, complete=True
```

Recovery-Backup:

```text
/home/pi/zec_measurements.pre-gap-repair.20260812_115109.sqlite3
```

### 3.2 Config-State `portable_profile`

Produktiv erzeugtes fehlerhaftes Artefakt:

```text
state_id = af6704e0c11f4a4d9057a24397b385d5
SHA256 = 831fc21c03c7df1fb6b0a9246902b835281da5a6b2cd169f2ffd90c9671efe85
artifact_kind = portable_profile
scope.mode = portable_profile
55 Keys
```

V13.0.1 `ConfigStateStore.create()` fordert `artifact_kind="named_state"`, `build_bundle()` normalisiert bei `scope_mode="portable_profile"` jedoch auf `artifact_kind="portable_profile"`. Die Datei wird bereits geschrieben; `_read()` akzeptiert danach für den lokalen Store nur `named_state` und wirft `CONFIG_STATE_KIND_INVALID`.

Das Artefakt wurde feldseitig hashgesichert aus dem aktiven Store in Quarantäne verschoben. Aktiver State blieb unberührt.

### 3.3 CSRF

Feldbestätigt nach längerer offener Settings-Seite:

```text
config-import/inspect → CSRF_TOKEN_INVALID
config-state preview „Prüfen & laden“ → CSRF_TOKEN_INVALID
```

Nach `Ctrl+F5` funktionieren beide Pfade wieder.

Codebefund V13.0.1:

```text
Cookie zec_settings_csrf max_age = 3600 s
settings_v2.js csrf() bevorzugt statischen Meta-Token
vor app.model.csrf_token
```

### 3.4 Import-/State-Preview

Verteilbares Profil:

```text
ZEC-CONFIG-BUNDLE v1
artifact_kind = portable_profile
scope = 55/55 portable Keys
Secrets = 0
Integrität = PASS
parse_bundle = PASS
```

Feld-Inspect nach Reload:

```text
Quelle 13.0.1
55 Scope-Keys
0 Migrationen
Keine wirksame Änderung erkannt
```

Trotzdem bleibt `Speichern` aktiv und `Zurück` beendet den gesamten Workflow.

### 3.5 Falscher `INHERITED_DEFAULT_CHANGED`

Beim lokalen `Standard-Konfiguration`-State:

```text
Quelle = V13.0.1
Ziel = V13.0.1
Registry-Schema identisch
Registry-Hash identisch
```

False Positive:

```text
Key = SECOND_BATTERY_INTEGRATION_ENABLED
source_resolved = True
target_inherited = False
aktuell explizit = False
im State explizit = False
```

Ursache: `parse_full_candidate()` leitet den fehlenden Integrationsschalter kompatibilitätsbedingt aus `CROSS_CHARGE_ENABLED || REST_SURPLUS_HARVEST_ENABLED` ab. `ConfigArtifactCoordinator._materialize_candidate()` verwendet dagegen `configured_view_from_raw()`, das nur den Registry-Default `False` einsetzt.


### 3.7 Historische Graphlegende

Feldbestätigt nach erfolgreichem V4-Config-Timeline-Backfill:

- historische Graphsegmente selbst sind zeitlich korrekt,
- Configwechsel innerhalb eines Tages werden korrekt rekonstruiert,
- bei einer tatsächlichen Folge wie `MAX_SOC 99 % → 80 % → 99 %` zeigt die V13.0.1-Legende wegen globaler Deduplizierung nur `99 % → 80 %`.

Damit ist die Fehlerklasse ausdrücklich **Darstellungs-/Legendensemantik**, nicht historische Datenhaltung oder Backfill.

### 3.8 Historische Release-/RC-Bezüge in Benutzertexten

Feldbestätigte Beispiele in V13.0.1:

```text
„Standard in V12.11.2-RC1 ist aus ...“
„Seit RC18 ...“
„Dient der RC3-Timingdiagnose.“
```

Solche Texte erklären Entwicklungsgeschichte statt den aktuellen Funktionsvertrag. Für den Benutzer existiert die installierte aktuelle Version; historische Versionsvergleiche sind nur zulässig, wenn sie für eine aktuelle Bedien-, Kompatibilitäts-, Import-/Migrations- oder Diagnoseentscheidung konkret notwendig sind.

---

## 4. SQLite-Writer-Härtung

### 4.1 Keine stille Fehlersituation

`MeasurementDbWriter` muss DB-Schreibfehler als persistente Diagnose führen.

Neu bzw. verbindlich:

```text
measurement_db_last_error
measurement_db_last_error_epoch_s
measurement_db_consecutive_failures
measurement_db_last_success_epoch_s
measurement_db_write_stale
```

`enqueue()` darf einen vorhandenen Writerfehler **nicht** allein dadurch löschen, dass ein neuer Punkt erfolgreich in die Queue gelegt wurde.

Ein erfolgreicher Write darf:

- `consecutive_failures` auf 0 setzen,
- den aktiven Fehlerstatus auflösen,
- `last_success_epoch_s` aktualisieren.

Historischer `last_error` und aktueller Zustand müssen diagnostisch unterscheidbar sein.

### 4.2 Connection-Recovery nach `_flush()`-Fehler

Bei jeder Exception im Writer-Flush:

1. Exception dokumentieren.
2. Falls möglich `rollback()` auf der aktuellen Connection.
3. Connection im Writerthread schließen.
4. `_conn = None`, `_conn_thread_id = None`, `_path = ""`.
5. Den fehlgeschlagenen Batch **nicht still verwerfen**.
6. Batch als pending halten und mit frischer Connection erneut versuchen.
7. Retry findet ausschließlich im asynchronen Writerthread statt; der Regelzyklus darf nicht blockieren.
8. Während eines längeren DB-Ausfalls darf die bestehende bounded Queue weiter puffern.
9. Wird die Queue voll, werden verworfene neue Punkte explizit in `measurement_db_rows_dropped` gezählt und als aktive Warnung sichtbar.

Ein transienter `database is locked`-/busy-/I/O-artiger Fehler muss sich nach Freigabe der Ursache ohne Dienstneustart selbst heilen können.

### 4.3 Stale-Write-Erkennung

Wenn Measurement-DB aktiviert ist, Enqueues stattfinden, aber für einen definierten Diagnosezeitraum kein erfolgreicher Write erfolgt, muss der Storage-Status warnen.

V13.0.2 verwendet dafür einen internen Diagnosevertrag, keinen neuen User-Setting-Key:

```text
write_stale = true,
wenn seit dem letzten erfolgreichen Write >= 120 s vergangen sind
und der DB-Writer weiterhin Messpunkte erhält.
```

Bei frisch gestarteter DB ohne bisherigen Erfolg beginnt die Frist mit dem ersten Enqueue.

UI darf dann nicht mehr ausschließlich `Aktiv · asynchron` / `queued` als unauffällig darstellen.

### 4.4 Backfill-/Runtime-Koordination

Der V13.0.1-Backfill läuft nach erfolgreicher Controller-Abnahme parallel zum bereits aktiven Runtime-Writer. V13.0.2 muss diesen konkurrierenden Main-DB-Schreibpfad deterministisch absichern.

Zielarchitektur:

- gemeinsamer dateibasierter Interprozess-Maintenance-Lock pro Measurement-DB,
- Runtime-Flush beteiligt sich am Lock ausschließlich im Writerthread,
- Backfill führt die lange CSV-Suche/Stagingarbeit **nicht unter Main-DB-Lock** aus,
- historische Transitions werden in einer separaten TEMP-/Staging-DB gesammelt,
- erst die kurze finale Übernahme in `graph_config_timeline` erhält den exklusiven Maintenance-Lock,
- anschließend Commit, Connection schließen, Lock freigeben,
- Runtime-Writer arbeitet danach automatisch weiter.

Der Installer darf den historischen Backfill weiterhin als nicht readiness-kritischen Schritt nach dem gesunden Produktivstart ausführen; der neue Lock-/Recoveryvertrag verhindert dabei einen nicht selbstheilenden Writerzustand.

### 4.5 Backfill-CSV-Robustheit

Der Feldscan fand eine historische V4-Datei mit NUL-Zeichen. Sie lag außerhalb des aktuellen Recovery-Zeitraums, zeigt aber eine Diagnoseblindstelle.

V13.0.2:

- Backfill zählt und meldet übersprungene/fehlerhafte Dateien explizit,
- `csv.Error`, Unicode-/NUL-Probleme werden nicht still verschluckt,
- historische Overlay-Segmente bleiben bei nicht lesbaren Quellen weiterhin `unknown` statt geraten,
- keine V3-Runtime-Reaktivierung.

Eine generische produktive Gap-Recovery-UI ist **nicht** Bestandteil dieses Hotfixes; sie gehört gegebenenfalls in die spätere Measurement-Storage-Härtung.

---

## 5. Config-State-/Artifact-Fix

### 5.1 Artifact-Kind und Scope entkoppeln

Ein lokaler gespeicherter Konfigurationsstand bleibt immer:

```text
artifact_kind = named_state
```

Ein State darf jedoch auf die Registry-Menge der verteilbaren Einstellungen begrenzt sein:

```text
scope.mode = portable_profile
```

`build_bundle()` darf daher `artifact_kind="named_state"` nicht allein wegen `scope.mode="portable_profile"` in `portable_profile` umschreiben.

Nur ein expliziter Export mit:

```text
artifact_kind = portable_profile
```

ist ein echtes verteilbares Austauschprofil.

Damit sind **Artifact-Typ** und **Scope** zwei getrennte Dimensionen.

### 5.2 UI-Begriffe

Benutzertexte werden geändert:

```text
Teilbares Profil           → Verteilbares Profil
Teilbares Regelprofil      → Verteilbares Regelprofil
```

Beim Anlegen eines lokalen State lautet die Scope-Option semantisch:

```text
Nur verteilbare Einstellungen
```

und nicht `Verteilbares Profil`, weil der lokale State selbst ein `named_state` bleibt.

Interne stabile Contracts/Enums wie `portable_profile` bleiben unverändert.

### 5.3 Beschädigte States sicher löschen

`delete()` darf nicht voraussetzen, dass ein State als gültiges Bundle parsebar ist.

Neuer Low-Level-Vertrag:

1. State-ID strikt validieren.
2. Pfad ausschließlich im `config-states`-Root bilden.
3. `lstat()`.
4. Symlink / Nicht-Regular / >1 MiB / unsichere Dateirechte weiterhin fail closed.
5. Raw-Bytes lesen.
6. `state_revision = SHA256(raw_bytes)` bestimmen.
7. CAS gegen vom Client übergebene Revision.
8. Datei unlinken.
9. Directory fsync.

Damit können syntaktisch/semantisch korrupte, aber **dateisichere** States kontrolliert gelöscht werden.

Unsichere Symlinks, Fremdobjekte oder permission-unsafe Dateien bleiben über UI/API nicht löschbar und benötigen Admin-/Shell-Diagnose.

`list()` liefert für korrupte sichere States zusätzlich:

```text
safe_deletable = true|false
```

UI zeigt dann `Löschen` auch für einen beschädigten sicheren State an; `Prüfen & laden`, Export und Umbenennen bleiben gesperrt.

---

## 6. Modal-/Workflow-Härtung

### 6.1 Parent-Modal-Vertrag

`Konfigurationsstände · Import · Export` ist Parent-Workflow.

Unteraktionen wie:

- Umbenennen,
- Löschen,
- State-Preview,
- Import-Preview,
- Secret-Export-Bestätigung

öffnen einen Child-Dialog, ohne den Parentzustand zu verlieren.

Verbindliche Navigation:

```text
Parent Config-States
  → Child
  → Abbrechen/Zurück
  → Parent Config-States im vorherigen Zustand
```

Nach erfolgreichem Rename/Delete:

- Parent bleibt bzw. wird unmittelbar wieder sichtbar,
- Liste wird aktualisiert,
- Scrollposition wird möglichst erhalten,
- Erfolgsmeldung ist im Parent sichtbar.

Beim Import-Preview bleiben Dateiname und Inspect-Ergebnis erhalten, solange der Nutzer den Workflow nicht bewusst beendet.

### 6.2 Modaler Fehlerkanal

Fehler, die durch eine Aktion innerhalb eines Modals entstehen, müssen primär **innerhalb dieses Modals** sichtbar werden.

Pflicht:

- persistentes Inline-/Banner-Feedback im aktiven Dialog,
- verständlicher Benutzertext plus technischer Fehlercode im Expertenmodus,
- Toast darf ergänzen, ist aber nicht alleiniger Fehlerkanal.

Dies gilt mindestens für Config-State-, Import-, Export- und Admin-Child-Aktionen.

---

## 7. CSRF-Lebenszyklus

### 7.1 Aktuelle Fehlerursache beseitigen

`settings_v2.js::csrf()` darf nicht dauerhaft den initialen Meta-Token über einen frischeren Model-Token stellen.

Neue Priorität:

```text
app.model.csrf_token
→ Meta-Token nur als initialer Bootstrap-Fallback
```

### 7.2 Automatischer Refresh und einmaliger Retry

Wenn eine schreibende API-Aktion mit `CSRF_TOKEN_INVALID` antwortet:

1. einmalig `GET /settings/model` aufrufen,
2. dadurch neuen Cookie-/Model-Token beziehen,
3. `app.model` bzw. mindestens den CSRF-Token aktualisieren,
4. ursprünglichen Request exakt einmal wiederholen.

Kein Endlos-Retry.

Schlägt der zweite Versuch ebenfalls fehl:

- Aktion bleibt fehlgeschlagen,
- verständliche Session-/Sicherheitsmeldung im aktuellen Modal,
- kein stilles Commit.

Origin-/Referer-/Host-Prüfung bleibt unverändert streng.

---

## 8. No-op-Preview / Commit-Vertrag

Wenn nach Migration, Materialisierung und Servervalidierung keine wirksame Änderung verbleibt:

```text
diff = []
```

muss der Preview semantisch ein No-op sein.

Ziel:

```text
status = no_changes
preview_id = null
commit_allowed = false
```

UI:

- Meldung `Keine wirksame Änderung erkannt.`,
- `Speichern` deaktiviert oder verborgen,
- `Zurück` führt korrekt zum Parent-Workflow.

Serverseitiger Commit mit einem nicht commitfähigen/no-op Preview wird ebenfalls abgewiesen. Clientlogik ist kein Sicherheitsvertrag.

---

## 9. Einheitliche Resolve-/Default-Semantik

### 9.1 Keine Parallelauflösung

Die Driftprüfung in `ConfigArtifactCoordinator._materialize_candidate()` darf nicht mehr `configured_view_from_raw()` als vereinfachte Defaultautorität verwenden, wenn die Runtime über `parse_full_candidate()` zusätzliche kanonische Ableitungen besitzt.

Alle Vergleiche `source_resolved` vs. `target_inherited` müssen dieselbe Resolve-Semantik benutzen wie SettingsRuntime/SettingsManager.

Für den bestätigten Fall muss V13.0.2 ergeben:

```text
SECOND_BATTERY_INTEGRATION_ENABLED:
source_resolved = True
target_resolved = True
→ KEIN INHERITED_DEFAULT_CHANGED
```

### 9.2 Herkunft eines Werts

Wo ohne Vertragsbruch möglich, führt die Artifact-/Previewlogik intern eine Herkunftskategorie:

```text
explicit
inherited_default
derived_compatibility
migrated
secret_keep
secret_replace
secret_clear
```

Mindestens die Default-Drift-Prüfung muss `inherited_default` von `derived_compatibility` unterscheiden.

Ein `INHERITED_DEFAULT_CHANGED` ist nur zulässig, wenn sich tatsächlich ein **geerbter Registry-Default** zwischen Quelle und Ziel unterscheidet.

---

## 10. Historische Graphlegenden – chronologische Semantik

### 10.1 Grundregel

Legenden historischer Konfigurations-Overlays müssen die **chronologische Folge tatsächlicher Zustandswechsel** abbilden.

Unzulässig ist eine globale Deduplizierung nach dem Muster:

```javascript
[...new Set(values)]
```

wenn dadurch ein später erneut auftretender Wert verloren geht.

Beispiel:

```text
historisch tatsächlich:
99 % → 80 % → 99 %

zulässige Legende:
Max-SOC 99 % → 80 % → 99 %

unzulässige Legende:
Max-SOC 99 % → 80 %
```

### 10.2 Zulässige Verdichtung

Nur **direkt aufeinanderfolgende identische Werte ohne echten Zustandswechsel** dürfen zusammengefasst werden.

Beispiel:

```text
99 → 99 → 80 → 80 → 99
```

darf semantisch zu

```text
99 → 80 → 99
```

verdichtet werden.

Ein späterer Rückkehrwert darf niemals wegen eines früheren Auftretens entfernt werden.

### 10.3 Geltungsbereich

Der Fix ist nicht nur auf `MAX_SOC_PERCENT` zu beschränken. Alle historischen Overlay-Legenden mit zeitlich segmentierbaren Konfigurationswerten sind auf dieselbe Fehlerklasse zu prüfen, mindestens:

- Max-SOC,
- Min-SOC,
- Nachtreserve,
- Nachtfenster.

Die zugrunde liegenden historischen Segmente, Config-Timeline und Measurement-V4-Daten werden nicht verändert.

---

## 11. Audit benutzerseitiger Release-/RC-Bezüge

### 11.1 Zielvertrag

Benutzertexte beschreiben den **aktuellen Funktions-, Bedien- und Diagnosevertrag**. Entwicklungsgeschichte gehört nicht in normale UI-, Hilfe- oder Handbuchtexte, wenn sie für die aktuelle Nutzung keinen konkreten Mehrwert besitzt.

Beispiel:

```text
vorher:
„Standard in V12.11.2-RC1 ist aus, damit kurze STALE-Phasen ...“

nachher:
„Standardmäßig ist die Option deaktiviert, damit kurze STALE-Phasen
keinen unnötigen Resync auslösen.“
```

### 11.2 Verbindlicher Audit-Scope

V13.0.2 prüft vollständig:

- sichtbare UI-Texte,
- Settings-Labels und Beschreibungen,
- Kategorie-/Abschnittshilfen,
- `short_help` / `extended_help`,
- Info-/`i`-Modals,
- Status-/Diagnosehilfen,
- aktuelle ausgelieferte Benutzerhandbuchtexte.

Jeder Treffer auf historische Versions-/RC-Sprache wird einzeln fachlich bewertet und nicht blind per Such/Ersetzen entfernt.

### 11.3 Zu entfernende bzw. umzuschreibende Bezüge

Insbesondere:

- „seit Vx.y.z ...“
- „ab RCn ...“
- „in Vx.y.z ...“
- „Standard in Vx.y.z-RCn ...“
- „Dient der RCn-Timingdiagnose“
- Entwicklungsvergleiche wie „im Vergleich zu Version ...“
- historische Aussagen darüber, wann ein aktuelles Verhalten eingeführt, deaktiviert oder geändert wurde, wenn diese Information heute keine Bedienentscheidung unterstützt.

### 11.4 Zulässige Ausnahmen

Versionsinformationen bleiben erhalten, wenn sie für den aktuellen Vertrag erforderlich sind, insbesondere:

- aktuelle Controller-Version / Build-ID,
- Quellversion eines importierten/exportierten Config-Bundles,
- Registry-/Schema-/Migrationskompatibilität,
- Installer-/Rollback-/Releasebelege,
- technische Diagnosemetadaten mit tatsächlicher Kompatibilitätsbedeutung,
- explizite historische Release Notes oder archivierte Entwicklungsdokumente.

Eine interne stabile Enum-/Kompatibilitätskennung darf erhalten bleiben. Ist ihre technische Bezeichnung historisch geprägt, erhält die Benutzeroberfläche eine zeitlose Anzeige, ohne den internen Vertrag unnötig umzubenennen.

### 11.5 Audit-Nachweis

Der Build muss eine dokumentierte Trefferliste des Audits erzeugen:

```text
Fundstelle
alter Benutzertext
Entscheidung:
  - entfernt/zeitlos umgeschrieben
  - zulässige Ausnahme
Begründung
```

Für zulässige Ausnahmen ist eine explizite Begründung erforderlich. Ein pauschales Allowlisting aller Versionsstrings ist unzulässig.

---

## 12. Nicht Bestandteil von V13.0.2

Diese bekannten Punkte bleiben ausdrücklich für den nächsten größeren Entwicklungsblock bzw. die spätere Roadmap offen:

- Graph-Redesign jenseits der konkret beschriebenen Legendenkorrektur,
- Statusseiten-Experten-/Diagnoseansicht,
- S2-Completion-Audit Primärspeicherintegration,
- S3-Completion-/Effectiveness-Audit Saison-/Tagesprofile,
- vollständige Measurement-Storage-Härtung S4/S5/S6/S7/S9 jenseits der konkret beschriebenen Writer-/Backfill-Härtung,
- separater Replay-/Simulationsdienst S8,
- Battery Care Mode.

V13.0.2 darf diese Themen nicht nebenbei implementieren.

---

## 13. No-Regression-Bereiche

Folgende Bereiche dürfen fachlich nicht verändert werden:

- AUTO-Regelalgorithmus,
- Harvest-Zielwertbildung,
- Cross-Charge-Regelalgorithmus,
- NIGHT-Regelalgorithmus,
- Command Lifecycle / Effect / Resync,
- Single-Owner-Vertrag,
- Measurement-V4-Feldvertrag 246/249,
- Last-Good-A/B-Recovery und Pointer-Reparatur,
- configured/effective/pending_restart-Grundvertrag,
- historische Graph-Overlay-Semantik,
- portable-profile Registry-Klassifikation 55/55,
- bestehender Secret-Vertrag `keep/replace/clear`.

Für geschützte Produktionsmodule ist Byteidentität zu V13.0.1 nachzuweisen, soweit sie nicht zwingend zum freigegebenen Hotfixscope gehören.

---

## 14. Pflicht-Testmatrix

### 14.1 SQLite

Mindestens:

1. normaler Writerbetrieb.
2. transienter SQLite-Lock während Flush.
3. Lock wird freigegeben → Writer recovered ohne Prozessneustart.
4. Connection wird nach Flushfehler rollbacked/geschlossen und frisch geöffnet.
5. fehlgeschlagener Batch wird nicht still verworfen.
6. Queue bleibt bounded.
7. Queue-Full erhöht `rows_dropped` sichtbar.
8. `queued` löscht aktiven/letzten Writerfehler nicht.
9. erfolgreicher Write löst aktiven Fehlerzustand auf.
10. stale-write nach >=120 s wird diagnostiziert.
11. Backfill parallel zum Runtimewriter mit Maintenance-Lock.
12. Runtimewriter schreibt nach Backfill ohne Neustart weiter.
13. historischer Backfill bleibt idempotent.
14. nicht lesbare CSV wird gezählt/gemeldet, nicht still verschluckt.
15. Measurement-V4 246/249 byte-/schemaidentisch.

### 14.2 Config States

1. `named_state + full_managed`.
2. `named_state + portable_profile scope` bleibt `named_state`.
3. expliziter `portable_profile`-Export bleibt `portable_profile`.
4. 55/55 portable Scope-Keys.
5. keine Secrets im verteilbaren Profil.
6. beschädigtes JSON listbar als corrupt.
7. `CONFIG_STATE_KIND_INVALID`-Datei listbar als corrupt.
8. dateisicherer corrupt State revisionsgebunden löschbar.
9. falsche Revision → Conflict.
10. Symlink/nonregular/unsafe permissions → Löschung fail closed.
11. gültiger State nicht beeinträchtigt.

### 14.3 CSRF

1. initialer Meta-Bootstrap funktioniert.
2. `app.model.csrf_token` hat anschließend Priorität.
3. abgelaufener Cookie/alter Token → Model-Refresh.
4. ursprünglicher POST wird genau einmal erneut versucht.
5. Retry erfolgreich → Aktion läuft normal.
6. Retry erneut invalid → sichtbarer Fehler, kein zweiter Retry.
7. Origin mismatch bleibt abgewiesen.

### 14.4 Modalstack / UX

1. Rename Abbrechen → Config-State-Parent.
2. Rename Erfolg → Parent + aktualisierte Liste.
3. Delete Abbrechen → Parent.
4. Delete Erfolg → Parent + aktualisierte Liste.
5. State Preview Zurück → Parent.
6. Import Preview Zurück → Parent + Importkontext.
7. Modalfehler als Inlinebanner sichtbar.
8. globaler Toast nicht alleiniger Fehlerkanal.
9. Scrolllocking Desktop/Mobil ohne Hintergrundscroll.

### 14.5 Preview-/Resolve

1. identisches verteilbares Profil → `no_changes`, kein Commit.
2. identischer lokaler State → `no_changes`, kein Commit.
3. `SECOND_BATTERY_INTEGRATION_ENABLED` erzeugt bei identischer V13.0.2-Semantik keinen False Positive.
4. echter Registry-Defaultwechsel erzeugt weiterhin `INHERITED_DEFAULT_CHANGED`.
5. explizite Werte bleiben explizit.
6. geerbte Werte werden nicht gepinnt.
7. Secret keep/replace/clear unverändert.


### 14.6 Historische Graphlegende

1. `99 → 80 → 99` bleibt vollständig `99 → 80 → 99`.
2. `99 → 99 → 80 → 80 → 99` darf nur adjacent-komprimiert als `99 → 80 → 99` erscheinen.
3. Max-SOC, Min-SOC, Nachtreserve und Nachtfenster werden auf dieselbe Sequenzlogik geprüft.
4. Graphsegmente und Config-Timeline bleiben unverändert.
5. Historischer Cache-Hit darf die korrekte chronologische Legendenfolge nicht verlieren.

### 14.7 Benutzertext-Audit

1. automatisierter Suchlauf auf typische Release-/RC-Muster in benutzerseitigen Textquellen.
2. jeder Treffer besitzt dokumentierte Entscheidung und Begründung.
3. bekannte Feldbeispiele sind entfernt bzw. zeitlos umgeschrieben.
4. aktuelle Versionsanzeige bleibt erhalten.
5. Import-/Export-Quellversion und Kompatibilitätsmetadaten bleiben erhalten.
6. interne technische Kennungen werden nicht unnötig umbenannt.
7. aktuelles Benutzerhandbuch enthält keine unbegründeten historischen Release-/RC-Bezüge.
8. gerenderte UI-/Hilfetexte enthalten keine unbegründeten historischen Release-/RC-Bezüge.

---

## 15. Exit-Gates

Vor Release mindestens:

- verifizierte V13.0.1-Quellbasis,
- neues V13.0.2-Source-Manifest vollständig PASS,
- vollständiger bestehender Testbestand + neue Regressionstests PASS,
- `unittest -W error::ResourceWarning` PASS,
- Python AST + `py_compile` PASS,
- JavaScript Syntax PASS,
- Shell `bash -n` PASS,
- JSON-Artefakte PASS,
- No-Regression-/Byteidentitätsnachweise,
- reale HTTP-Route-Smokes für Config-State/Import/CSRF,
- automatisierte Regression der chronologischen Graphlegende einschließlich `99 → 80 → 99`,
- dokumentierter vollständiger Benutzertext-Audit mit begründeter Allowlist zulässiger Versionsbezüge,
- aktuelles Benutzerhandbuch nach Textaudit neu erzeugt und visuell geprüft,
- SQLite transient-lock/recovery Integrationstest,
- Backfill/Runtimewriter-Konkurrenztest,
- finaler ZIP wird frisch entpackt,
- alle paketbezogenen Gates werden aus dieser Extraktion erneut verifiziert.

Pflichtausgabe:

```text
ZIP-Pfad / Dateiname
SHA256
Größe
ZIP-Root
APP_VERSION
APP_BUILD_ID
Source-Manifest + Hash
Test-/Collectionzahlen
Subtests
ResourceWarning-Ergebnis
Syntaxprüfungen
geänderte / neue / gelöschte Dateien
No-Regression-Nachweise
Exit-Gate
bekannte Restpunkte
Installationsbefehle
Rollbackhinweis
```

---

## 16. Produktive Feldabnahme V13.0.2

Nach Installation mindestens:

1. Version/Build-ID.
2. `/health` und `/ready`.
3. SQLite `last_write` läuft mindestens mehrere Minuten kontinuierlich weiter.
4. kein Writer-Stale-/Error-Zustand.
5. heutiger SOC-Graph wächst weiter.
6. historischer Backfill/Overlay bleibt korrekt.
7. lokaler State mit Scope `Nur verteilbare Einstellungen` lässt sich speichern und wieder lesen.
8. korrupter Test-State kann revisionsgebunden gelöscht werden.
9. verteilbares Profil exportiert weiterhin 55 Keys / 0 Secrets.
10. identischer Profilimport ergibt No-op ohne aktiven Speichern-Button.
11. State Preview desselben Stands erzeugt keinen falschen `INHERITED_DEFAULT_CHANGED`.
12. Rename/Delete/Preview `Zurück` kehren in den Parent-Dialog zurück.
13. historischer Graph zeigt bei vorhandener realer Folge `99 % → 80 % → 99 %` diese Folge vollständig in der Legende; alternativ wird derselbe Fall reproduzierbar mit historischem Testfixture nachgewiesen.
14. Nachtfenster-/Reserve-/Min-SOC-Legenden werden stichprobenartig auf chronologische Rückkehrwerte geprüft.
15. UI, Settings-Hilfen/Info-Modals und aktuelles Handbuch enthalten keine unbegründeten historischen Release-/RC-Bezüge mehr.
16. notwendige Versionsinformationen (aktuelle Version, Import-/Export-Quelle, Schema-/Migrationskompatibilität) bleiben korrekt sichtbar.
17. CSRF-Recovery wird über automatisierten Test vollständig belegt; im Feld muss kein künstliches einstündiges Warten erzwungen werden.

---

## 17. Freigabestatus

Diese Datei ist die konsolidierte V13.0.2-Hotfix-Spezifikation **V1.1** und ersetzt V1.0. Gegenüber V1.0 wurden die historische Graphlegendenkorrektur und der vollständige Audit benutzerseitiger Release-/RC-Bezüge verbindlich in Buildscope, Testmatrix, Exit-Gates und Feldabnahme aufgenommen.

**Bis zur ausdrücklichen Buildfreigabe werden keine Codeänderungen und kein V13.0.2-Build durchgeführt.**
