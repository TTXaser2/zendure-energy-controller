# ZEC V13.0.2 – Build Validation

**Zielrelease:** V13.0.2  
**Build-ID:** `v13.0.2-20260812`  
**Ausgangsbasis:** V13.0.1 / `v13.0.1-20260811`  
**Status:** Pre-Package-Exit-Gate

## Umgesetzter Hotfixscope

- SQLite-Writer: fehlgeschlagene Batches bleiben erhalten; Rollback/Connection-Reopen und automatische Wiederholung.
- SQLite-/Backfill-Koordination über einen separaten Interprozess-Maintenance-Lock; lange CSV-Scans erfolgen außerhalb des exklusiven DB-Abschnitts.
- Backfill-Diagnose für NUL-/CSV-Lesefehler statt stiller Auslassung.
- Lokale benannte Konfigurationsstände und `portable_profile`-Scope semantisch getrennt.
- Sichere revisionsgebundene Löschung beschädigter Config-State-Dateien ohne erfolgreiche Bundle-Semantikprüfung.
- Config-State-/Import-Modalstack, Inline-Fehleranzeige und No-op-Preview/Commit-Vertrag korrigiert.
- CSRF-Lebenszyklus mit aktuellem Model-Token und exakt einem Refresh/Retry gehärtet.
- `INHERITED_DEFAULT_CHANGED` nutzt die kanonische Runtime-/Manager-Auflösung.
- Benutzerterminologie auf „Verteilbares Profil/Regelprofil“ korrigiert.
- Historische Graphlegenden erhalten chronologische Rückkehrwerte (`99 → 80 → 99`); nur direkt benachbarte Duplikate dürfen zusammengefasst werden.
- Vollständiger Audit der aktuellen Benutzertexte auf unbegründete historische Release-/RC-Bezüge; notwendige Kompatibilitäts-/Versionsinformationen bleiben erhalten.

## Pre-Package-Gatewerte

Die nachstehenden Werte wurden auf dem versiegelten V13.0.2-Arbeitsstand tatsächlich erreicht; sie werden im finalen ZIP-Exit-Gate erneut verifiziert:

- pytest: **799/799 PASS**, **681/681 Subtests PASS**, 63,69 s
- unittest unter `-W error::ResourceWarning`: **799/799 PASS**, 61,461 s, keine ResourceWarning
- Targeted Hotfix: **16/16 PASS**
- Python AST + `py_compile`: **168/168 PASS**
- JavaScript `node --check`: **2/2 PASS**
- Shell `bash -n`: **9/9 PASS** (8 Tools + 1 Shell-Test)
- JSON: **6/6 PASS**
- Geschützte Produktionspfade: **12/12 byteidentisch** zu V13.0.1

## No-Regression

Die in `V13_0_2_TARGETED_PROTECTED_DIFF.md` aufgeführten Kernpfade bleiben byteidentisch. Measurement-V4-Schema 246/249 wird nicht verändert. Last-Good-A/B, `configured/effective/pending_restart`, Secretvertrag und historische Graphdaten-/Timeline-Semantik bleiben erhalten.

## Feldstatus

Build-PASS ist nicht gleich Produktiv-PASS. Die V13.0.2-Feldabnahme erfolgt erst nach Installation. Die V13.0.1-Feldevidenz (SQLite-Writer-Ausfall, Dienstneustart-Recovery, CSV-Gap-Rekonstruktion, Config-State-/CSRF-/Modal-/Preview-Befunde und historischer Graph-Backfill) ist die Regressionsgrundlage dieses Hotfixes.
