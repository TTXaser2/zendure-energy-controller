# Release-Informationen – Zendure Energy Controller V12.11.7

```text
Version:  12.11.7
Label:    V12.11.7
Build-ID: v12.11.7-20260808
Basis:    V12.11.6 / v12.11.6-20260808
```

## Scope

V12.11.7 ist ein Settings-/Config-Korrekturrelease für den Default-, Reset- und First-Install-Vertrag. Es verändert keine energetische Regellogik, keine Command-Safety und keinen Measurement-V4-Vertrag.

Kernpunkte:

- alle 212 Registry-Settings besitzen explizite Default-Provenienz und Reset-Policy;
- Produktdefault, Profilpreset, sicherer Sentinel, Legacy/Internal, Installationswert und `nicht gesetzt/automatisch` sind getrennte Semantiken;
- generischer `reset_default` wird auch serverseitig durch die Registry-Policy begrenzt;
- Missing-Config startet als `FIRST_INSTALL_SETUP` fail-closed;
- sicherheits-/anlagenrelevante Pflichtwerte müssen bei der Erstinbetriebnahme ausdrücklich gesetzt werden;
- First-Install verwendet ausschließlich den neuen Bootstrapvertrag und nicht historische Migrationsdefaults;
- `config.example.json` enthält keine haus-/anlagenspezifischen Pseudodefaults mehr;
- bestehende produktive `config.json`-Werte werden nicht neu bewertet oder verändert.

## First-Install-Pflichtwerte

Vor dem ersten Commit sind mindestens ausdrücklich erforderlich:

```text
DEVICE_ID
MQTT_BROKER
GRID_METER_SOURCE
MAX_CHARGE_POWER_W
MAX_DISCHARGE_POWER_W
MIN_SOC_PERCENT
MAX_SOC_PERCENT
```

Quellabhängig kommen die erforderlichen Verbindungsparameter hinzu, z. B. `SHELLY_IP` für `shelly_http` oder SMA-Gruppe/-Port für `sma_energy_meter_udp`.

Bis zum erfolgreichen Preview/Commit bleibt der Startupmodus `FIRST_INSTALL_SETUP` und das Control-Gate geschlossen.

## Sichere Bootstrap-Semantik

Feste Leistungsprofile besitzen bei einer Erstinstallation weiterhin nur sichere Sentinels, keine Betriebswertempfehlung:

```text
NIGHT_DISCHARGE_POWER_W           = 0 W
MANUAL_FIXED_DISCHARGE_POWER_W    = 0 W
MANUAL_FIXED_CHARGE_POWER_W       = 0 W
```

`MEASUREMENT_LOG_MODE` startet bei einer Erstinstallation mit `off`. Eine bestehende produktive Einstellung `standard` bleibt beim Update unverändert.

## Measurement

Aktiv und unverändert:

```text
ZEC-MEASUREMENT-V4
MEASUREMENT_SCHEMA_VERSION = 4
Standard = 246 Felder
Extended = 249 Felder
```

Der separat geplante V3-Legacy-Cleanup ist nicht Bestandteil von V12.11.7.

## Geschützte No-Regression-Dateien

Byteidentität zur V12.11.6-Basis ist Releasegate für:

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
