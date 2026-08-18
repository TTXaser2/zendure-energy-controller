# Zendure Energy Controller V13.0.3

**Build-ID:** `v13.0.3-20260814`

V13.0.3 ist ein enger UI-/UX-Hotfix auf Basis der produktiven V13.0.2. Der Live-Regelalgorithmus und alle Runtime-/Storage-Sicherheitsverträge bleiben fachlich unverändert.

## V13.0.3 Hotfix

- Config-State-/Import-Preview verwendet kontextbezogene Titel.
- No-op zeigt verständlich „Keine Änderungen erforderlich“, ohne Bestätigungscheckboxen oder toten Commitbutton.
- Der bekannte V13.0.1-Registry-Display-Metadata-Übergang bleibt technisch diagnostizierbar, zählt aber nicht mehr als nutzerrelevante Migration.
- Technische Codes erscheinen nur im Expertenbereich „Technische Details“.
- Echte Diffs, Validation, CAS, Commit und echte Bestätigungen bleiben erhalten.

## V13.0.2 Basisfunktionen

Der Release härtet die in V13 eingeführten Konfigurationsstände/Import-/Exportpfade sowie den asynchronen SQLite-Graphstore:

- SQLite-Writer recovern nach transienten Schreibfehlern mit Rollback, neuer Connection und erneutem Batchversuch; fehlgeschlagene Batches werden nicht still verworfen.
- Runtime-Writer und historischer Graph-Backfill koordinieren produktive DB-Schreibphasen über einen Maintenance-Lock.
- Writerdiagnose behält den letzten Fehler und erkennt einen überfälligen erfolgreichen DB-Write.
- Der Backfill meldet NUL-/CSV-Leseprobleme explizit, statt betroffene Dateien unbemerkt zu überspringen.
- Lokale benannte Stände können den Scope `portable_profile` verwenden, bleiben aber `artifact_kind=named_state`; ein Austauschprofil bleibt `artifact_kind=portable_profile`.
- Beschädigte, aber dateiseitig sicher identifizierbare Konfigurationsstände können revisionsgebunden gelöscht werden.
- Modalnavigation, Inline-Fehleranzeige, CSRF-Erneuerung und No-op-Preview wurden gehärtet.
- Default-/Inheritance-Prüfung verwendet dieselbe kanonische Resolve-Semantik wie die Runtime.
- Historische Graphlegenden erhalten chronologische Rückkehrwerte, z. B. `99 % → 80 % → 99 %`.
- Benutzertexte und aktuelles Handbuch wurden auf unnötige historische Release-/RC-Bezüge bereinigt.
- Benutzerbegriff: **verteilbares Regelprofil**. Der interne stabile Vertrag `portable_profile` bleibt unverändert.

## 1. Benannte Konfigurationsstände

- ZEC kann benannte Konfigurationsstände mit Name, Beschreibung, Erstellzeit, Quellversion, Registry-/Config-Schema, Scope und Integritätshash speichern.
- Lokaler Store: `/opt/zendure-controller/config-states/` mit restriktiven Rechten.
- Ein gespeicherter Stand wird **niemals direkt aktiviert**. Laden führt immer über Migration, vollständige Servervalidierung, Preview/Diff, explizite Bestätigung, CAS und atomischen Commit.
- Geerbte Defaults bleiben geerbt. Ein Stand materialisiert nicht still alte Defaults; echte Default-Abweichungen werden im Preview sichtbar.
- Konfigurationsstände sind strikt vom Last-Good-A/B-Recoverystore getrennt und niemals selbst Recoverycandidate.

## 2. Import und Export

Das Format ist `ZEC-CONFIG-BUNDLE`, Formatversion 1.

Unterstützt werden:

- vollständiger Export zur Sicherung bzw. kontrollierten Systemmigration;
- benannte lokale Konfigurationsstände;
- **verteilbares Regelprofil** für den Austausch ausdrücklich portabler Regelparameter zwischen ZEC-Installationen;
- Expert-Import einer historischen rohen `config.json`, weiterhin nur über Migration/Preview/Validation/Commit.

Die Bundle-Integritätsprüfung verwendet kanonisches JSON und SHA-256. Der Hash bestätigt **Integrität**, nicht Herkunft oder Authentizität. Unbekannte Registry-/Schema-Abweichungen werden ohne expliziten Migrationsvertrag fail closed abgewiesen.

V13.0.2 akzeptiert den exakt bekannten V13.0.1-Registryvertrag als ausschließlich darstellungsbezogenen Kompatibilitätsübergang. Beliebige Registry-Abweichungen bleiben gesperrt.

## 3. Scope und Portabilität

Die SettingsRegistry bleibt Schemaautorität. Alle 191 aktiven editierbaren LIVE/RESTART-Settings besitzen eine ausdrückliche Portabilitätsklasse.

Ein verteilbares Regelprofil enthält ausschließlich `portable_profile`-Settings. Insbesondere Secrets, lokale Runtime-/Pfadangaben und anlagen-/standortspezifische Einstellungen werden nicht automatisch als Regelprofil transportiert.

Auch ein verteilbares Profil wird auf dem Zielsystem vollständig validiert und niemals blind angewendet.

## 4. Secrets

- Benannte lokale Stände enthalten keinen Secret-Klartext.
- Normaler Export enthält standardmäßig keinen Secret-Klartext.
- Ein Secret-Klartextexport ist nur im Expertenmodus und nach separater ausdrücklicher Bestätigung möglich.
- Beim Import bleibt ein vorhandenes Zielsecret standardmäßig erhalten (`keep`).
- `replace` und `clear` sind explizite Expert-Operationen; `clear` benötigt zusätzlich eine Commit-Bestätigung.
- Preview, Diff, Audit und API-Antworten geben keine Secret-Klartexte zurück.

## 5. Config-Commit und Recovery

Der Whole-File-/CAS-Vertrag bleibt erhalten:

1. finale revisionsgebundene Reread-/CAS-Prüfung;
2. vollständige Servervalidierung des Whole Candidate;
3. atomischer Write;
4. exakte Post-Write-Reread-Prüfung;
5. bei Mismatch atomische Wiederherstellung der exakt zuvor gelesenen Bytes;
6. Runtime-Adoption erst nach erfolgreicher Endverifikation.

Schlägt auch die Rollback-Verifikation fehl, wird der Configzustand fail closed als invalid behandelt. Last-Good-Promotion bleibt an den bestehenden Stable-Ready-/Eligibility-Vertrag gebunden.

## 6. `configured`, `effective`, `pending_restart`

- `configured`: persistierter Nutzerstand;
- `effective`: aktuell laufender Wert;
- `pending_restart`: konfigurierte Änderung benötigt einen Dienstneustart, bevor sie wirksam wird.

Konfigurationsstände und Imports umgehen diesen Vertrag nicht.

## 7. Historisch korrekte SOC-Graph-Overlays

Historische Messpunkte und Konfigurations-Overlays sind getrennt:

- Measurement V4 bleibt unverändert und führt `config_control_hash`.
- Eine separate `graph_config_timeline` im SQLite-Graphstore ordnet historische Configwechsel zeitlich zu.
- Ein Configwechsel innerhalb eines Tages erzeugt ein neues Overlaysegment.
- Historische Tage verwenden die damals wirksame Config, nicht die heutige.
- Fehlt ein historischer Snapshot, wird der Abschnitt als unbekannt behandelt; aktuelle Werte werden nicht rückwirkend eingesetzt.
- Für vorhandene V4-Historie existiert ein idempotenter Backfill; danach pflegt die Runtime die Timeline bei Hashwechseln inkrementell weiter.
- Die Legende bildet chronologische Zustandswechsel ab und entfernt nur unmittelbar aufeinanderfolgende Dubletten.

## 8. SQLite-Graphstore

- SQLite bleibt ein nachgelagerter, asynchroner Mess-/Graphpfad und blockiert den Reglerzyklus nicht.
- Transiente DB-Fehler führen zu Rollback, Connection-Neuaufbau und Wiederholung des noch nicht bestätigten Batches.
- Die Queue bleibt bounded; echte Drops werden gezählt und diagnostiziert.
- Der letzte DB-Fehler bleibt sichtbar, bis ein neuer Fehler ihn ersetzt; ein späteres `queued` löscht die historische Fehlerinformation nicht.
- Runtime-Writer und Wartungs-/Backfillpfade verwenden einen separaten Interprozess-Maintenance-Lock für produktive Schreibphasen.

## 9. Measurement V4 bleibt produktiver Vertrag

- Produktive Runtime schreibt ausschließlich `ZEC-MEASUREMENT-V4`.
- Standardprofil: 246 Felder; Extended: 249 Felder.
- Historische V3-Dateien bleiben ausschließlich offline/read-only für Analyse, Replay oder kontrollierten Import.
- Es wird kein V3-Runtimepfad wieder eingeführt.
- `/graph-data.csv` bleibt der eigenständige Vertrag `ZEC-GRAPH-EXPORT-V1`.

## 10. No-Regression

Explizit geschützt sind insbesondere:

- AUTO_GRID_EXPORT / AUTO_GRID_IMPORT / HOLD und Totzonenkonvergenz;
- Harvest-Zielwertbildung, High-SOC-Logik und Primärspeicherpriorität;
- proportionale/symmetrische Cross-Charge-Korrektur;
- NIGHT_DISCHARGE, Reserve-SOC, aktive 0-W-Neutralisierung und Folgeübergang;
- Command-Effect-/Readback-/Resync-/SmartMode-/Gegenlimitvertrag;
- hostweite Single-Owner-/Command-Owner-Garantie;
- Measurement-V4-Header 246/249 und V4-Runtimevertrag;
- Last-Good-A/B-Recovery und `configured/effective/pending_restart`;
- historische V3-Offlinenutzung ohne produktiven V3-Writer.

## 11. Handbuch und Releasebelege

Aktuelles Benutzerhandbuch:

```text
docs/Zendure_Energy_Controller_Handbuch.pdf
```

V13.0.2-Releasebelege:

```text
README_INSTALLATION.md
RELEASE_INFO_V13_0_2.md
BUILD_VALIDATION_V13_0_2.md
V13_0_2_SOURCE_MANIFEST.sha256
V13_0_2_USER_TEXT_AUDIT.md
SPEZIFIKATION_ZEC_V13_0_2_HOTFIX_CONFIG_STATES_CSRF_SQLITE_HARDENING_UI_CLEANUP_V1_1.md
```
