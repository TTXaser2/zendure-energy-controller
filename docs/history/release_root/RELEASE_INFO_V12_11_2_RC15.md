# Release Information V12.11.2-RC15

## Releaseziel

Enger Command-Safety-Hotfix für einen produktiv nachgewiesenen festen Entladefall:

- unverändertes aktives Limit wurde wegen einer Vermischung von lokaler Publish-Historie und Geräte-Readback im Abstand von ungefähr sechs Sekunden erneut publiziert;
- ein lange unwirksames Entladekommando wurde erst beim späteren Intentwechsel physisch wirksam;
- eine sichere, aber eng begrenzte Übergabebarriere fehlte.

RC15 ändert keine Regler-Zielwertformel.

## Änderungen

- lokale MQTT-Publish-Historie und Zendure-Geräte-Readback vollständig getrennt;
- State-Topics überschreiben den lokalen Publish-Dedupe-Cache nicht mehr;
- bei unverändertem Soll keine normalen Limit-Wiederholungspublishes trotz abweichender Rücklesung;
- Full-State-Recovery bleibt über den bestehenden Cooldown erzwingbar;
- enger Late-Effect-Guard nur nach unaufgelöstem bestätigtem Aktiv-Mismatch und anschließendem Neutral-/Gegenrichtungswunsch;
- Guard neutralisiert ausschließlich `inputLimit=0` und `outputLimit=0`, ohne unnötigen `acMode`-Wechsel;
- Guard-Freigabe anhand monotoner Echtzeit, frischem 0/0-Readback und mindestens zwei unabhängigen physischen Neutralbeobachtungen;
- keine starre Multiplikation mit der konfigurierbaren Zyklusdauer;
- additive Status-/Measurement-V4-Diagnosefelder und RC14→RC15-Headerrotation;
- `inverseMaxPower` wird als getrennte, read-only rückgelesene Gerätebegrenzung mit Quelle und Alter dokumentiert, nicht als nachgewiesenes Hardwaremaximum;
- reale RC14-FIXED_DISCHARGE-Episode als credentialsfreie Regressionfixture;
- Hardwareschonungs-Regelwerk als verbindliche Entwicklungsleitplanke enthalten.

## Nicht enthalten

- keine Änderung von AUTO-, NIGHT-, HOLD- oder Festmodus-Zielwertformeln;
- keine Änderung des RC14-High-SOC-Tapers;
- keine `SMA_FULL_OR_IDLE`-Korrektur;
- keine asynchrone Zendure-API;
- keine Readiness-/Sticky-Error-Korrektur;
- keine Offgrid-Aktivierung;
- keine Settings-Änderung;
- keine Excel-Änderung;
- kein Runtime-Schreibpfad für `inverseMaxPower` oder andere persistente Gerätecaps.

## Installation

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc15
```

## Rollback

Das Update-Skript erzeugt vor dem Dateiaustausch ein Backup und erhält die produktive `config.json`. Ein Rollback auf RC14 ist nur bei einer neuen RC15-Regression angezeigt; der Publish-Sturm ist in RC14 bereits vorhanden.

## Produktivtestgrenze

RC15 ist build- und regressionstestvalidiert. Nach Installation folgt zunächst ein Status-/Publish-Check. Eine kontrollierte feste Entladung mit kleiner Leistung erfolgt erst nach gesonderter fachlicher Prüfung; ein Geräte-Mismatch wird nicht künstlich provoziert.

## Buildvalidierung

Auf frisch entpacktem ZIP:

```text
python3 -m py_compile *.py tools/*.py      OK
node --check static/status_v2.js           OK
bash -n tools/update_zendure_controller.sh OK
python3 -m json.tool config.example.json   OK
python3 -m unittest discover -s tests -q   437 Tests, OK
Measurement-V4 RC15 Standardfelder         217
Rekonstruierter RC14-Header                203
```

Bekannte Python-3.13-`ResourceWarning`-Hinweise älterer SQLite-Tests bleiben bestehen; kein Test schlug fehl.

## Fachlich geänderte Dateien

```text
controller_logic.py
mqtt_bridge.py
state.py
measurement_v4.py
measurement_v4_contract.py
version.py
README.md
README_INSTALLATION.md
bestehende Versions-/Headerrotationstests
```

## Neu

```text
tests/test_v12_11_2_rc15_command_publish_readback_guard.py
tests/fixtures/rc14_fixed_discharge_failure_20260728.csv
tests/fixtures/rc15_expected_command_events.json
RELEASE_INFO_V12_11_2_RC15.md
TECHNICAL_NOTES_V12_11_2_RC15.md
UEBERGABE_ZEC_V12_11_2_RC15_COMMAND_PUBLISH_READBACK_GUARD.md
SPEZIFIKATION_ZEC_V12_11_2_RC15_COMMAND_PUBLISH_READBACK_GUARD_REV2.md
ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md
```

Gelöscht oder umbenannt: keine Dateien.
