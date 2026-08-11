# Build Validation – Zendure Energy Controller V12.13.0

## Identität

```text
APP_VERSION       = 12.13.0
APP_VERSION_LABEL = V12.13.0
APP_BUILD_ID      = v12.13.0-20260811
```

Verifizierte Buildbasis:

```text
zendure_controller_v12_12_2.zip
SHA256 d2b80098a4fb9ae3d3070f3c009aaaa42a8146a54abda2cd7d6bb0bde4dd8c71
```

## Pre-Package-Teststand

```text
unittest ResourceWarning=error   748 / 748 PASS
ResourceWarnings                0
pytest collection               748
pytest                           748 / 748 PASS
pytest subtests                  677 / 677 PASS
Python AST                      154 PASS
python -m py_compile            PASS
JavaScript / node --check       2 / 2 PASS
Shell / bash -n                 9 / 9 PASS
Restart-Helper / bash -n        PASS
JSON                            6 / 6 PASS
Updater mode                    755
```

## V4-only-Vertrag

- kein produktiver Root-Python-Code enthält `ZEC-MEASUREMENT-V3`;
- kein produktiver V3-Writer-/Fallbackpfad bleibt im `CsvRotatingLogger`;
- fehlender/historischer Schemawert kann den produktiven Writer nicht auf V3 schalten;
- `MEASUREMENT_SCHEMA_VERSION=3` migriert idempotent auf `4`;
- Offline-V3-Reader bleiben erhalten;
- `/graph-data.csv` liefert `ZEC-GRAPH-EXPORT-V1` und weder V3- noch V4-Measurement-Identität.

## V4-Contract-No-Regression

```text
Standard fields: 246
Extended fields: 249
Standard header SHA256: 7842bfef39d47f93dc39689aa04da7658564af565e5051c24f90b32021d184a7
Extended header SHA256: 8f61d07e66428a6e8757333d35d5dd73dd3a0975ac9a16714b93dc9b86460e93
```

## UI-/Integration-Smoke

Der Graph-Export wurde gegen die echte `create_app()`-Route integriert geprüft. Der Browser-Render-Smoke wurde mit Chromium für Status und Settings bei 1440x900 und 390x844 ohne horizontalen Overflow, Page- oder Console-Fehler ausgeführt. Die Buildumgebung blockiert Chromium-Navigation zu localhost/file per Administratorpolicy; deshalb wurde der Render-Smoke über `page.set_content()` mit serverseitig erzeugtem HTML und ausgeliefertem CSS durchgeführt. Es wird kein vollständiger Live-Navigation-Browser-PASS behauptet.

## Handbuch

Das aktuelle generische Benutzerhandbuch wurde auf V12.13.0 aktualisiert. DOCX und PDF besitzen 17 Seiten; beide Renderfassungen wurden vollständig visuell geprüft. Historische V12.6-Handbücher bleiben unverändert als historische Artefakte erhalten.

## Final-ZIP-Gate

Die oben genannten Gates werden nach Packaging aus einer frischen Extraktion des finalen ZIP erneut ausgeführt. Der Release ist erst nach diesem zweiten Durchlauf final freigegeben.

## Paket-Scope vor finalem ZIP

```text
NEW                 9
CHANGED             56
DELETED             0
Source manifest     368 / 368
```
