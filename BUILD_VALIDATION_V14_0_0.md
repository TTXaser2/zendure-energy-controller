# ZEC V14.0.0 – Build Validation

**Build-ID:** `v14.0.0-20260904-r2`  
**Quellbasis:** V13.0.3 / `v13.0.3-20260814`  
**Engineering-Basis:** V14 WP1–WP9 finaler Checkpoint

## Implementierter Scope

- produktive V14.0.0 Releaseidentität;
- V4→Graph-Core-V3 Rebuild in separater Kandidaten-DB;
- vollständige V3-Validierung vor atomarem Swap;
- separates DB/WAL/SHM-Cutover-Backup mit Größen-/SHA256-Nachweis;
- fail-closed Restore: Backupquellen zuerst verifizieren, temporäre Restore-Artefakte vollständig aufbauen und verifizieren, erst danach produktive Umschaltung;
- automatischer Installer-Rollback bei echtem Fehler;
- automatisches redigiertes Diagnosepaket bei Preflight-/Updatefehlern;
- getrennte Controller-Readiness und Graph-History-Readiness;
- read-only V14-Feldabnahmewerkzeug;
- V14 Installations- und Release-Dokumentation;
- R2-Installer-Härtung: keine Build-Testframework-Abhängigkeit auf dem Produktiv-Pi, manifestgeschützte Buildevidenz und installierte Source-Manifestprüfung.

## Tests im finalen Arbeitsbaum vor Paketierung

- vollständige pytest-Suite: **932 Tests + 679 Subtests PASS**;
- vollständige Suite mit `ResourceWarning=error`: **932 + 679 PASS**;
- dedizierte WP10-Cutover-/Restore-/Tamper-Suite: **10/10 PASS**;
- Python `compileall`: **PASS**;
- Bash `bash -n`: **10/10 PASS**;
- Browser-JavaScript `node --check`: **2/2 PASS**;
- Measurement V4: **246 Standard / 249 Extended PASS**;
- R2 Installer-/Release-Regressionsblock: **70 Tests + 10 Subtests PASS**.

Der monolithische pytest-Aufruf überschreitet in der Engineering-Runtime die maximale Dauer eines einzelnen Toolaufrufs. Daher wurde die vollständige, sortierte Menge aller 120 `test_*.py`-Dateien deterministisch in vier disjunkte Gruppen aufgeteilt. Die Summen ergeben exakt 932 Tests + 679 Subtests; jede Datei wurde als Testziel genau einmal ausgeführt.

## No-Regression

`controller_logic.py` bleibt byteidentisch zum geschützten Stand seit WP2:

`56f854bbe5bbecc9a7ce305af3915bd461615cc425e444b0c3e427c38e4184b1`

Keine fachliche Änderung an Regler-, Command-, Safety- oder Hardwareschonungssemantik. Measurement V4 bleibt unverändert 246/249.

## Bewusst offen / nicht erfunden

WP10 setzt keine produktive Retentiondauer, keinen Retention-Scheduler und keine automatische VACUUM-Policy fest.

## Produktivstatus

Build-PASS ist nicht Produktiv-PASS. Nach Installation auf dem realen Pi muss `tools/v14_field_acceptance.py` ausgeführt und der resultierende Report geprüft werden.

## Fresh-Package Test-Harness-Härtung

Beim ersten Fresh-ZIP-Gate trat einmalig ein Test-Harness-Flake in `test_nearly_simultaneous_starts_have_exactly_one_owner` auf: Unter Fresh-Extract-I/O-Last startete der zweite Interpreter erst nach Ablauf des früheren festen 0,5-s-Haltefensters und beide Prozesse wurden nacheinander Owner. Produktive Locklogik war nicht betroffen.

Der Test verwendet nun eine explizite Zwei-Prozess-Barriere und hält den Gewinner-Lock bis beide Resultate vorliegen. `instance_owner.py` blieb unverändert. Der gehärtete Einzeltest lief anschließend 10-mal hintereinander PASS; das finale Fresh-ZIP-Gesamtgate wird auf dem neu gebauten Paket erneut vollständig ausgeführt.
