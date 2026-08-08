# Build-Validierung – Zendure Energy Controller V12.11.7

**Version:** `12.11.7`  
**Build-ID:** `v12.11.7-20260808`  
**Basis:** verifiziertes V12.11.6-Release

## 1. Basis-Preflight

Vor Codeänderungen wurde V12.11.6 vollständig geprüft:

```text
Source-Manifest:            328/328 PASS
unittest:                   670/670 PASS
ResourceWarning=error:      670/670 PASS
pytest:                     670/670 PASS
pytest Subtests:            677/677 PASS
Python/JS/Shell/JSON:       PASS
```

## 2. V12.11.7 Testgates

Nach Implementierung:

```text
unittest:                   682/682 PASS
ResourceWarning=error:      682/682 PASS
pytest:                     682/682 PASS
pytest Subtests:            677/677 PASS
```

Statische Arbeitsbaum-Gates:

```text
Python-Syntax:              148 Dateien PASS
JavaScript-Syntax:            2 Dateien PASS
Shell-Syntax:                 9 .sh-Dateien PASS
Restart-Helper bash -n:       PASS
JSON:                         6 Dateien PASS
```

Browser-Smokes mit produktivem HTML/CSS/JavaScript und ausschließlich gemocktem HTTP-Transport:

```text
Settings First Install 1440×900:  PASS
Settings First Install  360×800:  PASS
Settings First Install  390×844:  PASS
Settings First Install  430×932:  PASS
Page Errors:                       0
Console Errors:                    0
Native Browserdialoge:             0
Horizontales Overflow:             0 px
```

Geprüft wurden First-Install-Banner, leere Installationswerte, fehlender generischer Reset für Installationswerte, vorhandener Produktdefault-Reset, Sentinel-Beschriftung, Pflicht-Enum-Platzhalter sowie die Sichtbarkeit eines normalerweise geschützten Pflichtfelds (`DEVICE_ID`) bereits im Standardmodus der Erstinbetriebnahme.

## 3. Vertrags-/Regressionstests V12.11.7

Neue Abdeckung umfasst insbesondere:

- alle 212 Settings besitzen eine Default-Provenienz und Reset-Policy;
- installationsabhängige Werte sind serverseitig nicht generisch resetbar;
- echte Produktdefaults bleiben resetbar;
- First-Install verlangt explizite Anlagen-/Safetywerte;
- First-Install Preview → Commit → Reload ergibt eine kanonische NORMAL-Konfiguration;
- fehlende First-Install-Pflichtwerte blockieren;
- Nachtmodus kann mit sicherem 0-W-Sentinel nicht aktiviert werden;
- bestehende produktive Configwerte werden durch Bootstrap-Metadaten nicht umgeschrieben;
- `config.example.json` ist ein neutrales Setup-Template.

## 4. No-Regression

Byteidentität zur V12.11.6-Basis ist Pflicht für:

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

## 5. No-Regression-Hashes

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

Alle Werte sind gegenüber V12.11.6 byteidentisch.

## 6. Finale ZIP-Abnahme und Exit-Gate

Das finale Releasepaket wurde in ein neues leeres Verzeichnis extrahiert und vollständig erneut geprüft:

```text
Source-Manifest:            334/334 PASS
Python-Syntax:              148/148 PASS
JavaScript-Syntax:            2/2 PASS
Shell-Syntax:                 9/9 PASS
Restart-Helper bash -n:       PASS
JSON:                         6/6 PASS
unittest:                   682/682 PASS
ResourceWarning=error:      682/682 PASS
pytest Collection:          682
pytest:                     682/682 PASS
pytest Subtests:            677/677 PASS
Browser-Smokes:             PASS
Protected Byte Identity:      7/7 PASS
Excel Byte Identity:          PASS
```

Die frische ZIP-Abnahme bestätigte exakt diese Werte.

**Build-Exit-Gate: PASS.**
