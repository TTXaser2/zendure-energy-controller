# Releasebericht – Zendure Energy Controller V12.11.6

## 1. Zweck

V12.11.6 setzt die nach der produktiven V12.11.5-Abnahme identifizierten Settings-/Status-UX-Befunde konsolidiert um. Der Release bleibt außerhalb der energetischen Regel-, Command- und Measurement-V4-Schicht.

## 2. Fachliche Korrekturen

1. sofortige eindeutige Einzelwertvalidierung beim Verlassen eines Felds;
2. blockierter Save-Button eindeutig disabled;
3. Nachtzeit Start vor Ende;
4. Default-, Entfernen-, Automatik-, Installations- und Referenzsemantik getrennt;
5. feste Nacht-/manuelle Leistung für neue Installationen sicher 0 W statt nutzerspezifischer Leistungsannahmen;
6. benutzerlogische Feld- und Abschnittsreihenfolge in allen relevanten Kategorien;
7. verständliche Harvest-Labels;
8. administrative Aktionen in ZEC-Modals statt Browser-Systemprompt;
9. strukturierter Info-Popover `Controller & Schnittstellen`.

## 3. Default-Audit

Die Settings-Oberfläche inventarisiert 171 dargestellte Settings, davon 169 editierbar. Die UI-Defaultklassifikation verhindert generische Resetaktionen für installations-/hardwareabhängige und hochriskante Referenzwerte. `None`/Leerwerte erhalten nur dort eine Aktion, wo deren Semantik fachlich eindeutig ist, z. B. Nacht-Reserve entfernen oder automatische Harvest-Ratio wieder verwenden.

Bestehende produktive Configwerte werden nicht auf neue Defaults migriert.

## 4. Measurement / Legacy V3

Aktives Produktivschema bleibt Measurement V4 (`MEASUREMENT_SCHEMA_VERSION=4`). Die separate technische Bereinigung des Legacy-V3-Schreib-/Reader-Unterbaus bleibt außerhalb dieses Releases, damit keine geschützten Measurement-/Replay-Pfade mit dem UX-Block vermischt werden.

## 5. No-Regression

Geschützte Regler-/Command-/Measurementdateien und Excel sind im Arbeitsbaum byteidentisch gegen V12.11.5. Die Releaseabnahme wiederholt diesen Nachweis aus einer frischen ZIP-Extraktion.

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

Arbeitsbaum-Gates: 328/328 Manifest, 147 Python-, 2 JavaScript-, 9 Shell- und 6 JSON-Dateien syntaktisch geprüft; 670/670 unittest mit `ResourceWarning=error`; 670/670 pytest plus 677 Subtests; Chromium-Smokes Desktop und drei Mobilbreiten ohne Page-/Console-Fehler.

## 6. Offene spätere Blöcke

- V4-only Runtime / Legacy-V3-Cleanup;
- Measurement-Storage-Härtung;
- Konfigurationsprofile/Import/Export;
- Graph-Redesign;
- weitergehende Expertenansicht;
- Simulation.

## 7. Exit-Gate

Die vollständige Abnahme aus einer frischen Release-ZIP-Extraktion besteht: 328/328 Source-Manifest, 147 Python-, 2 JavaScript-, 9 Shell- und 6 JSON-Syntaxgates, 670/670 unittest unter `ResourceWarning=error`, 670/670 pytest plus 677 Subtests, Browser-Smokes auf Desktop und drei Mobilbreiten sowie 7/7 geschützte Byteidentitäten und Excel-Bitidentität.

**Ergebnis: PASS.**
