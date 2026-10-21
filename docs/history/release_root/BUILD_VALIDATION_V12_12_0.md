# Build Validation – Zendure Energy Controller V12.12.0

## Status

**BUILD EXIT-GATE: PASS**

Diese Datei dokumentiert die buildseitige Abnahme. Das finale Releasepaket wird zusätzlich nach frischer ZIP-Extraktion nochmals gegen dieselben Paket-/Test-/No-Regression-Gates geprüft.

## Quellbasis

```text
V12.11.7
APP_VERSION  = 12.11.7
APP_BUILD_ID = v12.11.7-20260808
SHA256       = 99caee1848cd5d7af3a241b8e1bf00de8724df4c7e9244cb8b186a11798edd67
```

Baseline-Gates:

```text
Source manifest        334 / 334 PASS
unittest               682 / 682 PASS
ResourceWarning hard   PASS
pytest collection      682
pytest                  682 / 682 PASS
pytest subtests         677 PASS
```

## V12.12.0 Help-Coverage

```text
Registry-Settings                  212 / 212
operative Settings                 171 / 171
BASE-Hilfe                         171 / 171
RICH priorisierte Settings          62 / 62
Kategoriehilfe                       12 / 12
Abschnittshilfe                      69 / 69
```

## V12.12.0 Teststand

```text
unittest unter ResourceWarning=error   698 / 698 PASS
pytest collection                      698
pytest                                  698 / 698 PASS
pytest subtests                          677 PASS
ResourceWarnings                           0
```

## Browser-Smoke

Produktive HTML-/CSS-/JS-Assets wurden in Chromium mit deterministisch gemocktem Transport geprüft:

```text
1440 x 900      PASS
360  x 800      PASS
390  x 844      PASS
430  x 932      PASS
Page Errors       0
Console Errors    0
Horizontal overflow 0 px
```

Geprüft wurden Setting-/Kategorie-/Abschnittshilfe, Expert-Gate, Synonymsuche, Guided Configuration, Harvest-Override, serverseitig blockierter Preview mit `Warum?`, Help-Scroll-Lock und responsive Help-Modal.

## Handbuch

```text
DOCX-Seiten gerendert und visuell geprüft    14 / 14 PASS
PDF-Seiten separat gerendert/verifiziert     14 / 14 PASS
Handbuchanker                                  PASS
alte anlagenbezogene Pseudodefaults           nicht übernommen
```

## No-Regression

Folgende Dateien müssen gegenüber V12.11.7 byteidentisch bleiben und werden im finalen Paket erneut geprüft:

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

Der historische V3-Kompatibilitätspfad ist nicht Bestandteil von V12.12.0. Measurement V4 bleibt unverändert produktiv.
