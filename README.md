# Zendure Energy Controller V13.0.1

**Build-ID:** `v13.0.1-20260811`

V13.0.1 enthält den vollständigen V13.0.0-Entwicklungsblock **Konfigurationsstände / Import / Export** und korrigiert gleichzeitig die historische Darstellung der SOC-Grenzen und Nachtfenster im Speicher-SOC-Tagesgraphen. Die produktive Regelung selbst bleibt fachlich unverändert: AUTO, Harvest-Zielwertbildung, Cross-Charge, NIGHT, Command Lifecycle/Resync, Single-Owner und Measurement V4 sind No-Regression-Bereiche.

## V13.0.1 Hotfix

V13.0.1 behebt ausschließlich den Installations-Abnahmefehler aus V13.0.0: Der Post-Install-Readiness-Evaluator hatte noch die alte V12.13.0-Identität hart codiert und konnte dadurch einen bereits `ready=true` laufenden V13.0.0-Controller fälschlich zurückrollen. Der Evaluator liest seine erwartete Version und Build-ID nun direkt aus der gemeinsam ausgelieferten `version.py`. Der historische Measurement-V4-Graph-Backfill bleibt unverändert und wird nach erfolgreicher Installations-Abnahme automatisch ausgeführt.

## 1. Benannte Konfigurationsstände

- ZEC kann benannte Konfigurationsstände mit Name, Beschreibung, Erstellzeit, Quellversion, Registry-/Config-Schema, Scope und Integritätshash speichern.
- Lokaler Store: `/opt/zendure-controller/config-states/` mit restriktiven Rechten.
- Ein gespeicherter Stand wird **niemals direkt aktiviert**. Laden führt immer über Migration, vollständige Servervalidierung, Preview/Diff, explizite Bestätigung, CAS und atomischen Commit.
- Geerbte Defaults bleiben geerbt. Ein Stand materialisiert nicht still alte Defaults; Default-Abweichungen werden im Preview sichtbar.
- Konfigurationsstände sind strikt vom Last-Good-A/B-Recoverystore getrennt und niemals selbst Recoverycandidate.

## 2. Import und Export

Das neue Format ist `ZEC-CONFIG-BUNDLE`, Formatversion 1.

Unterstützt werden:

- vollständiger Export zur Sicherung bzw. kontrollierten Systemmigration;
- benannte lokale Konfigurationsstände;
- **teilbares Regelprofil** für den Austausch ausdrücklich portabler Regelparameter zwischen ZEC-Installationen;
- Expert-Import einer historischen rohen `config.json`, weiterhin nur über Migration/Preview/Validation/Commit.

Die Bundle-Integritätsprüfung verwendet kanonisches JSON und SHA-256. Der Hash bestätigt **Integrität**, nicht Herkunft oder Authentizität. Unbekannte Registry-/Schema-Abweichungen werden ohne expliziten Migrationsvertrag fail closed abgewiesen.

## 3. Scope und Portabilität

Die SettingsRegistry bleibt Schemaautorität. Im V13-Entwicklungsblock sind alle 191 aktiven editierbaren LIVE/RESTART-Settings ausdrücklich einer Portabilitätsklasse zugeordnet.

Ein teilbares Regelprofil enthält ausschließlich `portable_profile`-Settings. Insbesondere Secrets, lokale Runtime-/Pfadangaben und anlagen-/standortspezifische Einstellungen werden nicht automatisch als Regelprofil transportiert.

Auch ein teilbares Profil wird auf dem Zielsystem vollständig validiert und niemals blind angewendet.

## 4. Secrets

- Benannte lokale Stände enthalten keinen Secret-Klartext.
- Normaler Export enthält standardmäßig keinen Secret-Klartext.
- Ein Secret-Klartextexport ist nur im Expertenmodus und nach separater ausdrücklicher Bestätigung möglich.
- Beim Import bleibt ein vorhandenes Zielsecret standardmäßig erhalten (`keep`).
- `replace` und `clear` sind explizite Expert-Operationen; `clear` benötigt zusätzlich eine Commit-Bestätigung.
- Preview, Diff, Audit und API-Antworten geben keine Secret-Klartexte zurück.

## 5. Config-Commit und Recovery

Der bestehende Whole-File-/CAS-Vertrag bleibt erhalten und wurde für V13 zusätzlich gehärtet:

1. finale revisionsgebundene Reread-/CAS-Prüfung;
2. vollständige Servervalidierung des Whole Candidate;
3. atomischer Write;
4. exakte Post-Write-Reread-Prüfung;
5. bei Mismatch atomische Wiederherstellung der exakt zuvor gelesenen Bytes;
6. Runtime-Adoption erst nach erfolgreicher Endverifikation.

Schlägt auch die Rollback-Verifikation fehl, wird der Configzustand fail closed als invalid behandelt. Last-Good-Promotion bleibt an den bestehenden Stable-Ready-/Eligibility-Vertrag gebunden.

## 6. `configured`, `effective`, `pending_restart`

Die bisherige Semantik bleibt unverändert:

- `configured`: persistierter Nutzerstand;
- `effective`: aktuell laufender Wert;
- `pending_restart`: konfigurierte Änderung benötigt einen Dienstneustart, bevor sie wirksam wird.

Konfigurationsstände und Imports umgehen diesen Vertrag nicht.

## 7. Historisch korrekte SOC-Graph-Overlays

V12.13.0 konnte historische Messpunkte korrekt cachen, aber dabei Max-/Min-SOC, Nachtreserve und Nachtfenster als Teil desselben Payloads veralten lassen. V13 trennt deshalb historische Messpunkte und Config-Overlays.

- Measurement V4 selbst bleibt unverändert und führt weiterhin `config_control_hash`.
- V13 nutzt daraus eine kleine separate `graph_config_timeline` im SQLite-Graphstore.
- Ein Configwechsel innerhalb eines Tages erzeugt ein neues zeitliches Overlaysegment.
- Historische Tage werden mit der damals wirksamen Config dargestellt, nicht mit der heutigen.
- Fehlt ein historischer Snapshot, wird der Abschnitt als „historische Konfiguration nicht verfügbar“ behandelt; aktuelle Werte werden nicht rückwirkend eingesetzt.
- Für vorhandene V4-Historie existiert ein einmaliger, idempotenter Backfill. Danach pflegt die Runtime die Timeline bei Hashwechseln inkrementell weiter.

Der Backfill ist ein historisches Graph-Enrichment. Ein Fehler dabei macht einen ansonsten gesunden Controller nicht `ready=false` und löst keinen Release-Rollback aus.

## 8. Measurement V4 bleibt produktiver Vertrag

- Produktive Runtime schreibt ausschließlich `ZEC-MEASUREMENT-V4`.
- Standardprofil: 246 Felder; Extended: 249 Felder.
- Historische V3-Dateien bleiben ausschließlich offline/read-only für Analyse, Replay oder kontrollierten Import.
- Es wird kein V3-Runtimepfad wieder eingeführt.
- `/graph-data.csv` bleibt der eigenständige Vertrag `ZEC-GRAPH-EXPORT-V1`.

## 9. No-Regression

Explizit geschützt sind insbesondere:

- AUTO_GRID_EXPORT / AUTO_GRID_IMPORT / HOLD und Totzonenkonvergenz;
- Harvest-Zielwertbildung, High-SOC-Logik und Primärspeicherpriorität;
- proportionale/symmetrische Cross-Charge-Korrektur;
- NIGHT_DISCHARGE, Reserve-SOC, aktive 0-W-Neutralisierung und Folgeübergang;
- Command-Effect-/Readback-/Resync-/SmartMode-/Gegenlimitvertrag;
- hostweite Single-Owner-/Command-Owner-Garantie;
- Measurement-V4-Header 246/249 und V4-Runtimevertrag;
- historische V3-Offlinenutzung ohne produktiven V3-Writer.

## 10. Handbuch und Releasebelege

Aktuelles Benutzerhandbuch:

```text
docs/Zendure_Energy_Controller_Handbuch.pdf
```

Releasebelege:

```text
README_INSTALLATION.md
RELEASE_INFO_V13_0_0.md
V13_0_0_FINAL_VALIDATION.md
SPEZIFIKATION_ZEC_V13_0_0_KONFIGURATIONSSTAENDE_IMPORT_EXPORT_UND_SOC_GRAPH_HISTORIE_V1_1.md
V13_0_1_SOURCE_MANIFEST.sha256
```
