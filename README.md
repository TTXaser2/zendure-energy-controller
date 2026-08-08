# Zendure Energy Controller V12.11.7

**Build-ID:** `v12.11.7-20260808`

V12.11.7 ist ein **Settings-/Config-Korrekturrelease** auf Basis der vollständig validierten V12.11.6. Schwerpunkt ist die saubere Trennung von Produktdefaults, Profilwerten, sicheren Sentinels, Installationswerten, Migration und First-Install. Die energetische Regellogik, Command-Safety, Cross-Charge- und Measurement-V4-Schicht bleiben unverändert.

## 1. Default- und Resetvertrag

Alle **212 SettingsRegistry-Einträge** besitzen eine explizite Default-Provenienz und Reset-Policy. Die Settings-UI und der Server verwenden denselben Registry-Vertrag.

Semantiken:

```text
Produktdefault       allgemeiner getesteter Standardwert
Profilpreset         nur im Kontext des gewählten Profils
Sicherer Sentinel    fail-safe Ausgangszustand, keine Empfehlung
Installation         anlagen-/hardware-/nutzerspezifisch
Nicht gesetzt/Auto   definierte Clear-/Automatiksemantik
Legacy/Internal      Migration/Deployment, kein Benutzerdefault
```

Ein generisches **Auf Default setzen** ist nur erlaubt, wenn die Registry dies ausdrücklich zulässt. Installationswerte wie MQTT-Broker, Geräte-ID, Leistungsgrenzen oder SOC-Grenzen können auch über die Settings-API nicht mehr auf historische Pseudodefaults zurückgesetzt werden.

## 2. First Install

Fehlt `config.json`, startet ZEC in:

```text
FIRST_INSTALL_SETUP
control_allowed = false
```

Vor dem ersten Commit müssen mindestens Device-ID, MQTT-Broker, Netzleistungsquelle, Lade-/Entladegrenzen sowie Min-/Max-SOC ausdrücklich festgelegt werden. Quellabhängige Verbindungsdaten werden ebenfalls geprüft.

Der First-Install-Preview benutzt ausschließlich den neuen Bootstrapvertrag. Historische RC19-/Legacydefaults werden dabei nicht als Neuinstallationswerte interpretiert.

Sichere Startzustände sind unter anderem:

```text
NIGHT_DISCHARGE_POWER_W           = 0 W
MANUAL_FIXED_DISCHARGE_POWER_W    = 0 W
MANUAL_FIXED_CHARGE_POWER_W       = 0 W
MEASUREMENT_LOG_MODE              = off
```

0 W ist dabei ausdrücklich ein **sicherer Sentinel**, keine empfohlene Betriebsleistung.

## 3. Bestehende Installationen

Das Update verändert eine vorhandene gültige `config.json` nicht aufgrund des neuen Defaultvertrags. Individuelle produktive Werte bleiben erhalten. Die bestehende Configmigration bleibt idempotent.

## 4. Measurement-Vertrag

Produktiv bleibt **ZEC-MEASUREMENT-V4** maßgeblich:

```text
MEASUREMENT_SCHEMA_VERSION = 4
V4 Standard                = 246 Felder
V4 Extended                = 249 Felder
```

Die historische `version.CSV_SCHEMA`-V3-Konstante gehört zum separaten Legacy-Kompatibilitätspfad. Der V3-only-Cleanup ist nicht Bestandteil dieses Releases.

## 5. No-Regression

V12.11.7 verändert insbesondere nicht:

- AUTO-, HOLD-, NIGHT- oder feste Regleralgorithmen;
- Harvest-Formeln und 0-W-Netzziel;
- Cross-Charge;
- Smart-Mode-/Flash-Schutz;
- Command-State, Readback, Effect, Resync und Late-Effect-Guard;
- Zendure Power Observation;
- Measurement-V4-Writer und -Contract;
- SQLite-Graphstore;
- Excel-Lernsimulation.

## 6. Installation und Releasebelege

Siehe:

```text
README_INSTALLATION.md
BUILD_VALIDATION_V12_11_7.md
RELEASE_INFO_V12_11_7.md
TECHNICAL_NOTES_V12_11_7.md
ZEC_V12_11_7_RELEASE_REPORT.md
```

## 7. Bewusst spätere Blöcke

Nicht Bestandteil von V12.11.7:

1. V4-only-Runtime / Entfernung des produktiven V3-Legacypfads;
2. Measurement-Storage-Härtung;
3. benannte Konfigurationsstände sowie Import/Export;
4. Graph-Redesign;
5. weitergehende Experten-/Diagnoseansicht;
6. separater Simulationsdienst.
