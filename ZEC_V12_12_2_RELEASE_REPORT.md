# ZEC V12.12.2 – Release Report

## 1. Identität

```text
APP_VERSION       = 12.12.2
APP_VERSION_LABEL = V12.12.2
APP_BUILD_ID      = v12.12.2-20260810
```

Buildbasis ist das finale und produktiv installierte V12.12.1 / `v12.12.1-20260810`.

## 2. Konsolidierter Scope

V12.12.2 verbindet vier bestätigte Produktivbefunde mit zwei bereits bestätigten UI-Feldbefunden:

1. P0 Single-Instance-/Command-Owner-Safety;
2. Harvest Entry/Hold mit monotonic elapsed + distinct observations;
3. sticky Current-State `harvest_limiter_reason`;
4. Measurement-Manifest Rotation/Rowcount/Clean-Close;
5. Desktop `Controller & Schnittstellen` wirklich scroll-/bedienbar;
6. mobiler SOC-Graph ohne plotverdeckenden Detailtooltip.

## 3. P0 Ergebnis

Der bisherige CWD-basierte Lock wurde durch einen absoluten kernelbasierten Owner-Lock ersetzt. `main()` erwirbt ihn vor sämtlichen Runtime-/I/O-Komponenten. Ein Zweitstart endet mit Code 73; gleicher/anderer CWD, Race, Clean Restart und Hard-Kill-Recovery sind automatisiert geprüft. Ein zusätzlicher realer Main-Subprozess aus `/tmp` wurde bei gehaltenem globalem Lock ebenfalls mit Code 73 abgewiesen.

## 4. Harvest Ergebnis

Entry/Hold wird nur mit neuen Observation-Tokens fortgeschrieben. Monotone reale Zeit ersetzt die nominelle Zyklussekundenrechnung; ein langer Stall wird nicht als viele Beobachtungen gewertet. Das vorherige Timing im störungsfreien 3-s-Normalfall wird durch Differentialtest erhalten.

`harvest_limiter_reason` wird bei Reset/Exit/Inaktivität neutralisiert und ist damit wieder Current-State-Semantik.

Die Harvest-Zielwertformel bleibt unverändert und ist per AST-Differential belegt.

## 5. Measurement Ergebnis

Manifest-Einträge für neu rotierte Files erhalten den tatsächlichen Rotationsgrund. Sauber abgeschlossene Files erhalten einen finalen writer-eigenen Rowcount und `closed_time_utc`. Ein abnormaler Prozessabbruch kann diesen Clean-Close-Schritt nicht ausführen und bleibt damit unterscheidbar. Es wird kein CSV-Vollscan im Livepfad hinzugefügt.

## 6. UI Ergebnis

Desktop-Diagnoseinfo ist jetzt click-pinned und per Wheel/Scrollbar wirklich scrollbar. Mobile SOC-Auswahl zeigt Detailwerte unterhalb des Canvas; der ausgewählte Kurvenpunkt bleibt sichtbar. Die V12.12.1-Mobile-Settings-Navigation bleibt unverändert.

## 7. Test-/No-Regression-Status

Vor Packaging:

```text
unittest ResourceWarning=error   731 / 731 PASS
pytest                           731 / 731 PASS
pytest subtests                  677 / 677 PASS
ResourceWarnings                0
Chromium UX smoke               PASS
```

Zwei geschützte Dateien werden nur wegen des bestätigten Scope gezielt geändert (`controller_logic.py`, `measurement_v4.py`). Die übrigen Command-/Cross-Charge-/Power-Observation-/Measurement-Contract-Dateien und die Excel-Simulation bleiben byteidentisch.

## 8. File-Scope

```text
NEW                 11
CHANGED             34
DELETED/REPLACED     2
Source manifest     359 / 359
```

## 9. Feldabnahme nach Installation

Noch produktiv zu bestätigen:

- realer Zweitstart aus anderem CWD -> Exit 73 bei gesundem weiterlaufendem Owner;
- `/health`/`/ready` Ownerdiagnose;
- Desktop-Wheel-Scroll im Diagnosepanel;
- mobiler SOC-Detailblock;
- Harvest-Timing anhand normaler Runtimebeobachtung, keine riskante Provokation;
- Manifest nach einer natürlich eintretenden Rotation.

## 10. Nicht-Scope / Beobachtung

Der bekannte 14-Minuten-Host-Freeze gehört zum Raspberry-Backup-Projekt. Nicht ausreichend beobachtete HIGH_SMA_SOC-/MIN_SOC-/Mismatch-/Late-Effect-Fälle bleiben Beobachtungspunkte, nicht künstlich erzeugte Bugfixes. V3-Legacy-Cleanup bleibt separat.
