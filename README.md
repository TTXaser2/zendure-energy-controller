# Zendure Energy Controller V12.11.2-RC14

## Aktueller Release

V12.11.2-RC14 ist die eng abgegrenzte High-SOC-Ladeannahme-Nachkorrektur zu RC13. RC13 hat Flash-Schutz, Command-State-Gate, Publish-Vertrag und Neutralization-Dedupe produktiv deutlich verbessert; die reale Ladeendepisode vom 27.07.2026 zeigte jedoch weiterhin falsche Command-Mismatches und zwei wirkungslose Full-State-Resyncs während des BMS-Tapers.

RC14 korrigiert ausschließlich diese Wirkungsklassifikation und die dafür fehlende Measurement-/Config-Reproduzierbarkeit.

Wesentliche Änderungen:

- High-SOC-Ladeannahme wird anhand frisch bestätigter **statischer Command-Invarianten** bewertet:
  - `smartMode=1`,
  - vollständiger Command-State,
  - `acMode=Input mode`,
  - `outputLimit=0`.
- Exakte Gleichheit zwischen neuestem dynamischem Soll und rückgelesenem `inputLimit` ist nicht mehr erforderlich.
- Der bestätigte Referenzwert lautet:

  ```text
  command_effect_reference_w = min(aktuelles positives Soll, rückgelesenes positives inputLimit)
  ```

- Standort-Netzexport ist bei real bestätigter, aber begrenzter Ladeleistung keine zwingende Voraussetzung mehr.
- Vollständige 0-W-Nichtannahme am/über Max-SOC wird nach drei Zyklen und mindestens sechs Sekunden als geräte-/BMS-seitige Ladeannahmebegrenzung klassifiziert.
- Unter Max-SOC bleibt der 0-W-Fall strenger und benötigt unabhängige Zusatzbelege wie Restexport, vorherigen Taper oder persistente Nichtannahmediagnose.
- Echte Nichtwirkung bei niedrigem SOC bleibt mismatch- und resyncfähig.
- Neue Measurement-V4-Felder:
  - `charge_acceptance_state`
  - `charge_acceptance_reason`
  - `command_effect_reference_w`
- `COMMAND_EFFECT_TOLERANCE_PERCENT` ist jetzt im Config-Snapshot und im `config_control_hash` enthalten.
- Bestehende RC13-V4-Dateien bleiben unverändert; RC14 beginnt automatisch eine neue `schema_rc14`-Datei.
- Die reale RC13-Taper-Episode mit 124 Produktivzyklen ist als Regressionstest enthalten.

## Produktive Grundlage

Vor dem RC14-Build wurde RC13 im Nachtbetrieb produktiv validiert:

- acht Stunden NIGHT_DISCHARGE mit Soll −400 W und Median −399 W,
- Nachtfenster-Exit mit genau einem Nullbatch,
- physische 0-W-Bestätigung,
- kein Nullspam,
- keine ungeschützten Leistungsbefehle,
- keine neue Resync-Serie.

Diese Funktionen bleiben in RC14 unverändert und werden durch No-Regression-Tests abgesichert.

## Sicherheitsabgrenzung

RC14 verändert keine Regler-Zielwertformel und insbesondere nicht:

- AUTO-Zielwertbildung,
- NIGHT_DISCHARGE,
- Cross-Charge-Zielwerte,
- Harvest-Entry/-Hold/-Exit,
- `SMA_FULL_OR_IDLE`,
- Gerätecaps oder Offgrid-Konfiguration.

Der Runtime-Schreibpfad bleibt begrenzt auf:

```text
smartMode = ON
acMode
inputLimit
outputLimit
```

ZEC schreibt weiterhin keine persistenten Gerätecaps, SOC-Grenzen oder Offgrid-Einstellungen.

## Bewusst nicht enthalten

- Korrektur des `SMA_FULL_OR_IDLE`-Absolutziels,
- asynchrone Entkopplung der lokalen Zendure-API,
- Readiness-/Sticky-Error-Nacharbeit,
- Änderung der Command-State-Gate-Steuerlogik,
- produktiver Offgrid-Test,
- Settings-Redesign,
- Änderung der Excel-Lernsimulation.

## Dokumentation

```text
RELEASE_INFO_V12_11_2_RC14.md
TECHNICAL_NOTES_V12_11_2_RC14.md
UEBERGABE_ZEC_V12_11_2_RC14_HIGH_SOC_ACCEPTANCE.md
SPEZIFIKATION_ZEC_V12_11_2_RC14_HIGH_SOC_ACCEPTANCE_FOLLOWUP.md
README_INSTALLATION.md
```
