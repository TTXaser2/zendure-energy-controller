# Build Validation – Zendure Energy Controller V12.12.1

## Status

**BUILD EXIT-GATE: PASS**. Das finale Releasepaket ist zusätzlich aus einer frischen ZIP-Extraktion gegen die Paket-/Test-/No-Regression-Gates zu verifizieren.

## Quellbasis

```text
V12.12.0
APP_VERSION  = 12.12.0
APP_BUILD_ID = v12.12.0-20260809
SHA256       = 6ff1ac7b902a65007a534d12cd1013439c7adca8241deddafbf0aef1ebefbaf9
```

Baseline:

```text
Source manifest        343 / 343 PASS
unittest               698 / 698 PASS
ResourceWarning hard   PASS
pytest collection      698
pytest                  698 / 698 PASS
pytest subtests         677 PASS
```

## V12.12.1 Qualitätsabdeckung

```text
Registry-Settings                  212 / 212
operative Settings                 171 / 171
BASE-Hilfe                         171 / 171
RICH-Settings                       62 / 62
RICH mit konkretem when/risk        62 / 62
Kategoriehilfe                       12 / 12
Abschnittshilfe                      69 / 69
```

## Teststand vor Packaging

```text
unittest unter ResourceWarning=error   709 / 709 PASS
pytest collection                      709
pytest                                  709 / 709 PASS
pytest subtests                          677 PASS
ResourceWarnings                           0
```

## Browser-Smoke vor Packaging

Chromium:

```text
Settings 1440 x 900   PASS
Settings  360 x 800   PASS
Settings  390 x 844   PASS
Settings  430 x 932   PASS
Status   1440 x 900   PASS
Status    360 x 800   PASS
Status    390 x 844   PASS
Status    430 x 932   PASS
Page Errors              0
Console Errors           0
Horizontal overflow      0 px
```

Geprüft wurden Suchranking, Help-Scroll-Reset, Glossarlink, strukturierte Defaultsemantik, Compound-Validation, logische `Warum?`-Navigation, mobile Top-/Context-/Change-Bar sowie internes Status-Info-Scrolling.

Automatisiertes WebKit: **nicht verfügbar**, da keine Engine installiert ist und deren Nachinstallation in der Buildumgebung wegen fehlender Netzwerk-/DNS-Erreichbarkeit nicht möglich war. Kein WebKit-PASS wird behauptet.

## Handbuch

```text
DOCX gerendert und visuell geprüft      17 / 17 PASS
PDF separat gerendert/verifiziert       17 / 17 PASS
bestehende Settings-Anker 4–14          stabil
Glossar                                 Seiten 15–17
```

## No-Regression

Folgende Dateien müssen gegenüber V12.12.0 byteidentisch bleiben und werden im finalen Paket erneut geprüft:

```text
controller_logic.py
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
measurement_v4.py
measurement_v4_contract.py
tools/zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx
```

## Bekannter separater Restpunkt

Der historische V3-Kompatibilitätspfad ist nicht Bestandteil von V12.12.1. Measurement V4 bleibt unverändert produktiv.
