# Build-Validierung – Zendure Energy Controller V12.11.5

**Version:** `12.11.5`  
**Build-ID:** `v12.11.5-20260807`  
**Basis:** `V12.11.4 / v12.11.4-20260807`

## 1. Baseline-Preflight

Die eingebettete V12.11.4-Referenz wurde vor jeder fachlichen Codeänderung verifiziert:

```text
Referenz-ZIP SHA256: 55bb0b24360b92cfd4f3e8b919ba5ebe75bf154c7903c6d091f025706dde2f57
Source-Manifest:      PASS · 316 Einträge
Python-Syntax:        145 Dateien · PASS
JavaScript-Syntax:      2 Dateien · PASS
Shell-Syntax:           9 Dateien · PASS
JSON-Parse:             6 Dateien · PASS
unittest:             652 bestanden
ResourceWarning=Error:652 bestanden
pytest collection:    652
pytest:               652 bestanden
pytest subtests:      677 bestanden
```

## 2. V12.11.5 Test- und Collection-Gates

```text
unittest-Collection:                 662
unittest:                            662 bestanden
unittest mit ResourceWarning=Error:  662 bestanden
pytest-Collection:                   662
pytest:                              662 bestanden
pytest-Subtests:                     677 bestanden
ResourceWarnings:                      0
```

## 3. Syntax-Gates

```text
Python-Dateien:                       146 · PASS
JavaScript-Dateien:                     2 · PASS
Shell-Dateien:                          9 · PASS
JSON-Dateien:                           6 · PASS
```

## 4. V12.11.5 Regressionen

```text
Desktop: ausschließlich Content primär vertikal scrollbar          PASS
Sidebar separat scrollbar                                           PASS
Kategoriewechsel setzt Content auf Anfang                           PASS
Kein horizontaler Dokumentoverflow                                  PASS
Nacht Start/Ende als zwei HH:MM-Felder                              PASS
Technischer Nacht-Payload paarweise atomar                          PASS
Nacht-Preview als logisches Nachtfenster                            PASS
Client-Time/Number/Enum-Prüfung                                     PASS
Serverseitiger Multi-Field-Preview HTTP 422/status=blocked          PASS
422 wird im Browser als Validierungsdialog behandelt                PASS
Feldmarkierung und Sprung zum Setting                               PASS
Draft bleibt nach blockiertem Preview erhalten                      PASS
Korrigieren und erneut prüfen                                       PASS
409/403/unerwartete Fehler verständlich gekapselt                   PASS
Last-Good-Pointer nur im Expert/System-Adminbereich                 PASS
Command/Resync Standard: Empty-State und sichtbarer Count 0         PASS
Expertmodus: 13 Command/Resync-Settings sichtbar                    PASS
Mobiler Drawer: Body-Lock, eigener Scroll, Escape/Kategorie close   PASS
Globale mobile Navigation weiterhin intern horizontal scrollbar     PASS
```

Die bestehenden zentralen Settings-Validationstests decken zusätzlich Integer-/Float-Grenzen, Enum/Codecs, Nachtfensterrelation, SOC-Mehrfeldrelation, High-SOC-Hysterese, Floor/Restart/Near-Limit, Integrations-/Source-Dependencies, Warning/Confirmation, Secret-Redaction und Revision/CAS ab.

## 5. Browser-Smokes

Chromium 144, produktives V12.11.5-HTML/CSS/JavaScript:

```text
Desktop 1440 × 900    PASS
Mobile  360 × 800     PASS
Mobile  390 × 844     PASS
Mobile  430 × 932     PASS
Page errors              0
Console errors           0
```

Die Sandbox blockiert direkte lokale URL-Navigation in Chromium per Administrator-Policy. Deshalb wurde für den Browser-Smoke ausschließlich der Transport (`fetch`) durch einen eingebetteten Testadapter ersetzt; Renderer, CSS, produktives `settings_v2.js`, DOM und Interaktionen sind unverändert. Der reale FastAPI-Endpoint `/settings/preview` wurde separat direkt geprüft und lieferte für den Multi-Field-Fehler den erwarteten strukturierten HTTP-422-Body.

## 6. No-Regression / Byteidentität

Die sieben geschützten Regler-/Command-/Measurementdateien sind gegenüber der verifizierten V12.11.4-Quelle byteidentisch:

```text
controller_logic.py                 435a6d30975bf4673e6640e98761b95d178fd4075cfed84d2fbeffcd30a4ea3b
command_lifecycle.py                6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176
mqtt_bridge.py                      ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791
cross_charge.py                     cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7
zendure_power_observation.py        ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a
measurement_v4.py                   374687009b19c51551b3a65763a73ee7c257a716a000aca8fc19aff3c251dd81
measurement_v4_contract.py          4896dc12c3810ed06614e9f0504d94bcd7252857348a6366bb52ebec92cc0f27
```

Die Excel-Lernsimulation bleibt ebenfalls bitidentisch:

```text
zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx
SHA256: 15f699008c82fe71367604fcb97e1900c023fe8929b40d3fc7210ee2117e79fe
```

## 7. Installer-Gate

- V12.11.4 wird ausdrücklich als Quellidentität erkannt.
- Paket-/Source-Manifest-Prüfung läuft vor Dienststopp.
- Keine Node.js-Produktivabhängigkeit.
- Vollständiges `/opt`-Rollbackbackup, Configbackup und Root-Artefaktbackup bleiben erhalten.
- Bestehende Configmigration bleibt idempotent.
- Lokaler Testbestand läuft vor und nach Kopie mit `ResourceWarning=error`.
- Sicherer Transitional-Readback-Vertrag bleibt unverändert.

## 8. Exit-Gate

```text
BUILD EXIT-GATE: PASS
```

Die produktive Feldabnahme auf dem Raspberry Pi bleibt als separater letzter Schritt erforderlich.
