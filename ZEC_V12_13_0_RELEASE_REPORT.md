# ZEC V12.13.0 – Release Report

## 1. Identität

```text
APP_VERSION       = 12.13.0
APP_VERSION_LABEL = V12.13.0
APP_BUILD_ID      = v12.13.0-20260811
```

Buildbasis ist das finale und produktiv installierte V12.12.2 / `v12.12.2-20260810`.

## 2. Ergebnis

V12.13.0 beendet die historische Doppelrolle von V3 und V4 in der produktiven Runtime:

- produktiver Measurement-Writer ausschließlich V4;
- kein fehlender-Key-/Legacy-Fallback auf V3;
- historischer Configmarker `3` wird kontrolliert auf `4` migriert;
- Registry/Config führen nur noch den versteckten festen V4-Kompatibilitätsmarker;
- interner Controller-Snapshot ist schema-neutral;
- globale `version.CSV_SCHEMA` ist entfernt;
- Graph-CSV besitzt den eigenen Vertrag `ZEC-GRAPH-EXPORT-V1`;
- historische V3-Dateien bleiben offline/read-only analysierbar.

## 3. V4-No-Regression

Der persistente Measurement-V4-Feldvertrag bleibt exakt erhalten:

```text
Standard 246 Felder
Extended 249 Felder
```

Header-Hashes sind gegenüber V12.12.2 identisch. Die Manifest-/Rotation-/Clean-Close-Härtung aus V12.12.2 bleibt bestehen.

## 4. Regler-/Command-No-Regression

Es gibt keine fachliche Änderung an AUTO, HOLD, Harvest-Zielwertbildung, Cross-Charge, NIGHT, Command Lifecycle/Resync oder Single-Owner-Safety. Die betroffenen Controller-/Measurement-Dateien wurden nur dort angepasst, wo die Measurement-Schemaidentität bzw. Dokumentation dies erfordert; Differential-/Hashnachweise liegen in `V12_13_0_TARGETED_PROTECTED_DIFF.md`.

## 5. Tests vor Packaging

```text
unittest ResourceWarning=error   748 / 748 PASS
pytest                           748 / 748 PASS
pytest subtests                  677 / 677 PASS
ResourceWarnings                0
```

Zusätzlich: 154 Python-AST-Prüfungen, `py_compile`, 2 JavaScript-, 9 Shell-, Restart-Helper- und 6 JSON-Prüfungen.

## 6. Handbuch

Das generische Benutzerhandbuch ist auf V12.13.0 aktualisiert und erklärt V4-only Runtime, historischen V3-Read-only-Support und den eigenständigen Graph-Exportvertrag. DOCX und PDF umfassen jeweils 17 Seiten und wurden visuell geprüft.

## 7. Installation

Der Installer akzeptiert V12.12.2 ausdrücklich als normalen direkten Ausgangsstand und erwartet Ziel `v12_13_0` / Build `v12.13.0-20260811`. Die Schema-3->4-Migration ist Bestandteil des idempotenten bestehenden Config-Migrationspfads.

## 8. Abgrenzung

Keine historischen V3-Messdateien werden gelöscht. Kein SQLite-/Storage-Redesign, kein Regler-Tuning und kein neues Measurement-Schema ist Bestandteil dieses Releases.

## 9. File-Scope

```text
NEW                 9
CHANGED             56
DELETED             0
Source manifest     368 / 368
```
