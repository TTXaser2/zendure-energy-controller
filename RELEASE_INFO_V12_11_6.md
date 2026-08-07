# Release-Informationen – Zendure Energy Controller V12.11.6

```text
Version:  12.11.6
Label:    V12.11.6
Build-ID: v12.11.6-20260808
Basis:    V12.11.5 / v12.11.5-20260807
```

## Scope

Settings-/Status-UX-Qualitätsrelease ohne Regellogikänderung:

- unmittelbare lokale Format-/Rangevalidierung;
- fachliche Feldreihenfolge;
- differenzierte Default-/Reset-Semantik;
- sichere 0-W-Neuinstallationswerte für feste Nacht-/manuelle Leistungsprofile;
- ZEC-eigene Admin-Modals statt `window.confirm()`;
- strukturierter Controller-&-Schnittstellen-Info-Popover;
- bessere Labels für technisch benannte Harvest-Settings.

## Default-Sicherheitsentscheidung

Nur `default_new_install` beziehungsweise die korrespondierenden frischen Defaults werden für diese drei Profile auf 0 W gesetzt:

```text
NIGHT_DISCHARGE_POWER_W           0 W
MANUAL_FIXED_DISCHARGE_POWER_W    0 W
MANUAL_FIXED_CHARGE_POWER_W       0 W
```

Historische Registry-Migrationswerte bleiben:

```text
400 W / 400 W / 800 W
```

Eine vorhandene produktive `config.json` wird beim Update nicht auf die neuen Neuinstallationswerte umgeschrieben.

## Measurement

Aktiv und unverändert:

```text
ZEC-MEASUREMENT-V4
MEASUREMENT_SCHEMA_VERSION = 4
Standard = 246 Felder
Extended = 249 Felder
```

`version.CSV_SCHEMA = "ZEC-MEASUREMENT-V3"` bleibt eine Legacy-Konstante und ist nicht die aktive Schemaauswahl. V3-Cleanup ist nicht Teil dieses Releases.

## Geschützte No-Regression-Dateien

Byteidentität zur V12.11.5-Basis ist Releasegate für:

```text
controller_logic.py
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
measurement_v4.py
measurement_v4_contract.py
```

Auch `tools/zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx` muss bitidentisch bleiben.
