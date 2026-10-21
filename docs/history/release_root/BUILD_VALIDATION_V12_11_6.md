# Build-Validierung – Zendure Energy Controller V12.11.6

**Version:** `12.11.6`  
**Build-ID:** `v12.11.6-20260808`  
**Basis:** verifiziertes V12.11.5-Release

## 1. Basis-Preflight

Vor Codeänderungen wurde V12.11.5 vollständig geprüft:

```text
Source-Manifest:            322/322 PASS
unittest:                   662/662 PASS
ResourceWarning=error:      662/662 PASS
pytest:                     662/662 PASS
pytest Subtests:            677/677 PASS
Python/JS/Shell/JSON:       PASS
```

## 2. V12.11.6 Testgates

Arbeitsbaum nach Implementierung:

```text
unittest:                   670/670 PASS
ResourceWarning=error:      670/670 PASS
pytest:                     670/670 PASS
pytest Subtests:            677/677 PASS
```

Statische Arbeitsbaum-Gates:

```text
Source-Manifest:            328/328 PASS
Python-Syntax:              147 Dateien PASS
JavaScript-Syntax:            2 Dateien PASS
Shell-Syntax:                 9 .sh-Dateien PASS
Restart-Helper bash -n:       PASS
JSON:                         6 Dateien PASS
```

Die vollständige Prüfung wird nach Erzeugung des Releasepakets nochmals direkt aus einer frischen ZIP-Extraktion ausgeführt.

## 3. Browser-Smokes

Chromium mit produktivem V12.11.6-HTML/CSS/JavaScript und ausschließlich gemocktem HTTP-Transport:

```text
Settings Desktop 1440×900:  PASS
Settings Mobil 360×800:     PASS
Settings Mobil 390×844:     PASS
Settings Mobil 430×932:     PASS
Status Desktop 1440×900:    PASS
Page Errors:                0
Console Errors:             0
Native Browserdialoge:      0
Horizontales Overflow:      0 px
Info-Popover Desktopbreite: 560 px
Info-Popover Abschnitte:    4
```

Geprüft:

- `25:30` wird bereits beim Verlassen des Felds sichtbar blockiert;
- Nachtzeit-Reihenfolge Start → Ende;
- semantische Reserve-SOC-Entfernen-Aktion;
- installationsabhängiger MQTT-Broker ohne generischen Reset;
- serverseitig blockierter Preview mit sichtbar deaktiviertem **Speichern nicht möglich**;
- Restart- und Pointer-Adminaktion als ZEC-Modal ohne `window.confirm()`;
- strukturierter `Controller & Schnittstellen`-Popover;
- Desktop und drei Smartphonebreiten ohne horizontales Dokumentoverflow.

## 4. No-Regression

Die sieben geschützten Regler-/Command-/Measurementdateien sowie die Excel-Lernsimulation sind gegenüber V12.11.5 byteidentisch:

```text
controller_logic.py             435a6d30975bf4673e6640e98761b95d178fd4075cfed84d2fbeffcd30a4ea3b
command_lifecycle.py            6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176
mqtt_bridge.py                  ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791
cross_charge.py                 cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7
zendure_power_observation.py    ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a
measurement_v4.py               374687009b19c51551b3a65763a73ee7c257a716a000aca8fc19aff3c251dd81
measurement_v4_contract.py      4896dc12c3810ed06614e9f0504d94bcd7252857348a6366bb52ebec92cc0f27
Excel-Lernsimulation            15f699008c82fe71367604fcb97e1900c023fe8929b40d3fc7210ee2117e79fe
```

## 5. Finale ZIP-Abnahme und Exit-Gate

Die Releaseabnahme wurde aus einer frischen Extraktion des erzeugten ZIPs wiederholt:

```text
Source-Manifest:            328/328 PASS
Python-Syntax:              147/147 PASS
JavaScript-Syntax:            2/2 PASS
Shell-Syntax:                 9/9 PASS
Restart-Helper bash -n:       PASS
JSON:                         6/6 PASS
unittest:                   670/670 PASS
ResourceWarning=error:      670/670 PASS
pytest Collection:          670
pytest:                     670/670 PASS
pytest Subtests:            677/677 PASS
Browser-Smokes:             PASS
Protected Byte Identity:      7/7 PASS
Excel Byte Identity:          PASS
```

**Build-Exit-Gate: PASS.**
