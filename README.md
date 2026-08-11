# Zendure Energy Controller V12.13.0

**Build-ID:** `v12.13.0-20260811`

V12.13.0 trennt den produktiven Measurement-Vertrag vollständig von der historischen V3-Kompatibilität. Die produktive Runtime schreibt ausschließlich `ZEC-MEASUREMENT-V4`; historische V3-Dateien bleiben nur für Offline-Analyse, Replay und Import lesbar. Regler-, Command-, Cross-Charge-, NIGHT-, Harvest-Zielwert-, Single-Owner- und Measurement-Manifest-Verträge aus V12.12.2 werden nicht fachlich verändert.

## 1. Produktive Runtime: ausschließlich Measurement V4

- `CsvRotatingLogger` besitzt keinen produktiven V3-Schreibzweig mehr.
- Ein fehlender oder historischer Schema-Marker kann den Runtime-Writer nicht auf V3 umschalten.
- `MEASUREMENT_SCHEMA_VERSION` bleibt ausschließlich als versteckter Kompatibilitätsmarker mit festem Wert `4` erhalten.
- Historische Konfigurationen mit Schema `3` werden idempotent auf den Marker `4` migriert.
- Die frühere globale Runtime-Konstante `version.CSV_SCHEMA = "ZEC-MEASUREMENT-V3"` ist entfernt.

Der V4-Feldvertrag bleibt unverändert:

```text
Standard: 246 Felder
Extended: 249 Felder
```

## 2. Interner Controller-Snapshot

Der interne Zyklus-/Graph-Snapshot ist schema-neutral. Er trägt keine künstliche `ZEC-MEASUREMENT-V3`- oder `schema_version=3.0`-Identität mehr. Erst der produktive Measurement-V4-Writer bildet aus Controllerzustand, Config- und Runtimekontext den persistierten V4-Datensatz.

## 3. Graph-CSV ist kein Measurement-Paket

`/graph-data.csv` ist ein kompakter UI-/Graph-Export und verwendet den eigenständigen Vertrag:

```text
ZEC-GRAPH-EXPORT-V1
```

Der Export wird ausdrücklich weder als Measurement V3 noch als Measurement V4 ausgegeben. Dadurch kann er nicht mit einem vollständigen V4-Analysepaket verwechselt werden.

## 4. Historische V3-Dateien bleiben lesbar

V3-Unterstützung bleibt ausschließlich in Offline-Werkzeugen erhalten, insbesondere für:

- historische Analyse;
- Replay;
- kontrollierten Import alter Messdateien.

Diese Pfade sind read-only in Bezug auf das historische Eingabeformat. Sie können keinen produktiven V3-Writer aktivieren.

## 5. Settings-/Config-Semantik

`MEASUREMENT_SCHEMA_VERSION` ist keine Benutzerwahl mehr. Die Registry führt nur noch V4 und hält den Key verborgen als Rollback-/Migrationsmarker. `MEASUREMENT_LOG_MODE` hängt nicht mehr von einer Schemaauswahl ab.

Bei bestehender historischer Konfiguration gilt:

```text
3 -> kontrollierte Migration auf 4
4 -> no-op
fehlend -> normalisiert auf 4
```

## 6. Handbuch

Das aktuelle Benutzerhandbuch ist auf V12.13.0 aktualisiert. Es beschreibt:

- V4 als einziges produktives Messschema;
- V3 ausschließlich als historischen Offline-Lesepfad;
- `ZEC-GRAPH-EXPORT-V1` als eigenständigen Graph-CSV-Vertrag.

## 7. No-Regression

Explizit geschützt sind insbesondere:

- AUTO_GRID_EXPORT / AUTO_GRID_IMPORT / HOLD und Totzonenkonvergenz;
- Harvest-Zielwertbildung, High-SOC-Logik, monotone Entry-/Hold-Zeitsemantik und Primärspeicherpriorität;
- proportionale/symmetrische Cross-Charge-Korrektur;
- NIGHT_DISCHARGE, Reserve-SOC, aktive 0-W-Neutralisierung und Folgeübergang;
- Command-Effect-/Readback-/Resync-/SmartMode-/Gegenlimitvertrag;
- hostweite Single-Owner-/Command-Owner-Garantie;
- Measurement-V4-Manifest-/Rotation-/Close-Semantik;
- V4-Header und Feldvertrag 246/249;
- SQLite-/Storage-Hotpath-Vertrag;
- Excel-Lernsimulation.

Es gibt kein allgemeines Measurement-Schema-Redesign und keine Änderung der Live-Regelalgorithmen.

## 8. Releasebelege

Siehe:

```text
README_INSTALLATION.md
BUILD_VALIDATION_V12_13_0.md
RELEASE_INFO_V12_13_0.md
TECHNICAL_NOTES_V12_13_0.md
ZEC_V12_13_0_RELEASE_REPORT.md
SPEZIFIKATION_ZEC_V12_13_0_MEASUREMENT_V4_ONLY_LEGACY_V3_CLEANUP_V1.0.md
V12_12_2_TO_V12_13_0_CHANGED_FILES.txt
V12_13_0_TARGETED_PROTECTED_DIFF.md
```
