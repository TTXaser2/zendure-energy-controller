# Release Information V12.11.2-RC14

## Releaseziel

Korrektur der produktiv nicht greifenden RC13-High-SOC-Ladeannahme-/Taper-Reklassifikation ohne Änderung einer Regler-Zielwertformel.

## Änderungen

- statische statt exakt-dynamische Command-State-Bestätigung für High-SOC-Taper;
- bestätigtes rückgelesenes `inputLimit` als Command-Referenz;
- Standort-Netzexport nicht mehr zwingend für begrenzte reale Ladeannahme;
- separater bestätigter 0-W-Nichtannahmefall am/über Max-SOC;
- strenger Schutz gegen Verschleierung echter Niedrig-SOC-Nichtwirkung;
- neue V4-Felder `charge_acceptance_state`, `charge_acceptance_reason`, `command_effect_reference_w`;
- `COMMAND_EFFECT_TOLERANCE_PERCENT` im Config-Snapshot und Control-Hash;
- RC13→RC14-Headerrotation;
- reale RC13-Taper-Episode als 124-Zyklen-Regressionsfixture;
- gezielte Intended-Delta- und No-Regression-Tests.

## Produktive RC13-Basis

Vor dem Build produktiv bestätigt:

- acht Stunden NIGHT_DISCHARGE mit Soll −400 W und Median −399 W;
- Nachtfenster-Exit mit genau einem Nullbatch;
- physische 0-W-Bestätigung ohne Nullspam;
- kein ungeschützter AC-/Limit-Publish;
- MAX-SOC- und Cross-Charge-Neutralepisoden jeweils dedupliziert.

## Nicht enthalten

- `SMA_FULL_OR_IDLE`-Absolutzielkorrektur;
- asynchroner Zendure-API-Worker;
- Command-State-Gate-Steuerlogikänderung;
- Readiness-/Sticky-Error-Korrektur;
- Offgrid-Aktivierung;
- Settings-Redesign;
- Excel-Änderung.

## Installation

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc14
```

## Rollback

Das Update-Skript erzeugt vor dem Dateiaustausch ein Backup des Installationsverzeichnisses und erhält die produktive `config.json`.

## Buildvalidierung

```text
python3 -m py_compile *.py tools/*.py      OK
node --check static/status_v2.js           OK
bash -n tools/update_zendure_controller.sh OK
python3 -m unittest discover -s tests -q   419 Tests, OK
```

Bekannte `ResourceWarning`-Hinweise älterer SQLite-Tests unter Python 3.13 bleiben bestehen; es trat kein Testfehler auf.
