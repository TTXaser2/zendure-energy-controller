# Build Validation – Zendure Energy Controller V12.12.2

## Status

**BUILD EXIT-GATE: PASS**, vorbehaltlich der getrennten produktiven Feldabnahme nach Installation. Das finale ZIP wird vor Freigabe nochmals frisch entpackt und aus genau dieser Extraktion verifiziert.

## Quellbasis

```text
V12.12.1
APP_VERSION  = 12.12.1
APP_BUILD_ID = v12.12.1-20260810
ZIP SHA256   = 899df26b135ab87af1ed0cf42bd9684ffc2a21770f953b612de2bc2d11ded478
```

Baseline V12.12.1:

```text
Source manifest        350 / 350 PASS
unittest               709 / 709 PASS
ResourceWarning hard   PASS
pytest collection      709
pytest                  709 / 709 PASS
pytest subtests         677 PASS
```

## V12.12.2 Source-Manifest

```text
Source manifest        359 / 359 PASS
```

## V12.12.2 Teststand vor Packaging

```text
Python AST/Syntax                  153 PASS
JavaScript                           2 / 2 PASS
Shell                                9 / 9 PASS
JSON                                 6 / 6 PASS
unittest ResourceWarning=error     731 / 731 PASS
ResourceWarnings                     0
pytest collection                  731
pytest                              731 / 731 PASS
pytest subtests                    677 / 677 PASS
```

## P0 Single-Instance-Matrix

```text
absoluter CWD-unabhängiger Lockpfad               PASS
zweiter Start gleiches CWD                        PASS / Exit 73
zweiter Start anderes CWD                         PASS / Exit 73
nahezu simultane Starts                           PASS / exakt 1 Owner
saubere Freigabe -> neuer Owner                   PASS
Hard-Kill -> Kernel-Lock frei                     PASS
rejected main vor Runtime-/I/O-Imports            PASS
reale Main-Integration aus /tmp bei aktivem Lock  PASS / Exit 73
Ownerdiagnose in health/status                    PASS
```

Die abgewiesene Instanz erreicht weder Config-/MQTT-/Measurement-/Web-/Controller-Runtime-Imports noch Initialisierung. Ein Feldtest gegen den laufenden systemd-Owner bleibt Teil der Installationsabnahme.

## Harvest-Zeit-/Diagnose-Gate

```text
nominal 30 s = bisher 10 x 3-s-Verhalten          PASS
Jitter nutzt monotonic elapsed                    PASS
identische Observation zählt nicht erneut         PASS
langer Stall kreditiert keine Stallzeit           PASS
Hold nur bei distinct Observation                 PASS
Hold nach langem Stall max. nominales Intervall   PASS
Wall-Clock-Sprung ohne Wirkung                    PASS
Reset verwirft alte Observation-Time              PASS
aktueller harvest_limiter_reason nach Reset leer  PASS
```

Die Harvest-Zielwertfunktion `_rest_surplus_charge_pressure_target()` ist AST-identisch zu V12.12.1.

## Measurement-Manifest-Gate

```text
Service-Start initialer Filegrund                 PASS
Size-Rotation -> neuer Filegrund SIZE_LIMIT       PASS
vorheriges File bei Rotation clean geschlossen    PASS
clean close -> closed_time_utc gesetzt            PASS
open/Crash-Semantik -> closed_time_utc leer       PASS
finaler row_count = reale CSV-Datenzeilen         PASS
Finalizer verwendet Writer-Zähler, kein File-Scan PASS
Measurement-V4-Contract byteidentisch             PASS
Standardheader 246 / Extended 249                  PASS
```

## Browser-Smoke vor Packaging

Chromium:

```text
Desktop 1440 x 900
  Diagnosepanel intern scrollbar                  PASS
  echter Wheel-Scroll scrollTop 0 -> 600          PASS
  Panel bleibt dabei offen                        PASS
  Outside Click schließt                          PASS
  horizontal overflow                             0 px

Mobile 360 x 800 / 390 x 844 / 430 x 932
  SOC-Details sichtbar unter Canvas               PASS
  Floating Tooltip ausgeblendet                   PASS
  Auswahlgraph bleibt sichtbar                    PASS
  horizontal overflow                             0 px

Page Errors                                        0
Console Errors                                     0
```

Automatisiertes WebKit wird nicht als PASS behauptet; die reale iPhone-Abnahme bleibt für Mobile-Verhalten maßgeblich.

## Protected-Diff / No-Regression

Bewusst geändert:

```text
controller_logic.py   Harvest time/current-state/sample timestamps only
measurement_v4.py     manifest lifecycle only
```

Byteidentisch zu V12.12.1:

```text
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
measurement_v4_contract.py
tools/zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx
```

AST-identisch sind u. a. Cross-Charge-Limiter, Harvest-Zielwertfunktion, feste manuelle Modi, NIGHT, Discharge, Command-Effect und Command-Publish. Details siehe `V12_12_2_TARGETED_PROTECTED_DIFF.md`.

## Ausdrücklich nicht verändert

- AUTO-/HOLD-Tuning;
- Harvest-Leistungs-/Zielwertformeln;
- Cross-Charge-Tuning;
- NIGHT-/MAX_SOC-Logik;
- Command-Effect-/Resync-Vertrag;
- Measurement-V4-Feldschema;
- Settings Help / Guided Configuration;
- V3-Legacy-Pfad;
- Local-API-/SQLite-/MQTT-Performance aufgrund des externen Backup-/Host-Freezes;
- Installed-Tree-/Supply-Chain-Provenance.
