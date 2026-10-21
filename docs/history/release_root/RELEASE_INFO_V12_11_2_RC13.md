# Release Information V12.11.2-RC13

## Releaseziel

Korrektur der im RC12-Produktivlauf bestätigten Command-Safety-Nachprobleme ohne Änderung der Regel-Zielwertbildung.

## Änderungen

- physische Neutralisierungs-Episoden und Deduplizierung;
- maximal ein Safety-Nullbatch je Command-State-Retry-Fenster;
- einheitlicher Command-State-Gate-Zustandsautomat;
- aktive Limits ausschließlich bei frisch bestätigtem `smartMode=1`;
- relative Trackingtoleranz, Default 10 %;
- früher physikalisch abgesicherte Taper-Klassifikation;
- eindeutige Publish-Event-ID und Publish-Epoch in V4;
- RC13-Headerrotation;
- neue gezielte Regressionstests.

## Nicht enthalten

- `SMA_FULL_OR_IDLE`-Absolutzielkorrektur;
- asynchroner Zendure-API-Worker;
- Readiness-/Sticky-Error-Korrektur;
- Offgrid-Aktivierung;
- Settings-Redesign.

## Installation

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc13
```

## Rollback

Das Update-Skript erzeugt vor dem Dateiaustausch ein Backup des Installationsverzeichnisses und erhält die produktive `config.json`.

## Buildvalidierung

```text
python3 -m py_compile *.py tools/*.py      OK
node --check static/status_v2.js           OK
bash -n tools/update_zendure_controller.sh OK
python3 -m unittest discover -s tests -q   410 Tests, OK
```

Die bekannten `ResourceWarning`-Hinweise älterer SQLite-Tests unter Python 3.13 bleiben bestehen; es trat kein Testfehler auf.
