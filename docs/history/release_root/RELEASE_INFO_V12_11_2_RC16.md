# Release Information V12.11.2-RC16

## Releaseziel

RC16 implementiert ausschließlich RC-B: die Korrektur des Delta-/Absolutwertfehlers im bestehenden Harvest-Zweig `SMA_FULL_OR_IDLE`.

Bisher wurde der nach bereits laufender Zendure-Ladung verbleibende Netzexport abzüglich Profilreserve als absolutes Ladeziel verwendet. RC16 bildet daraus gemeinsam mit der unabhängig beobachteten aktuellen Zendure-AC-Ladung ein physikalisch korrektes absolutes Ziel.

## Änderungen

- Absolutformel für `SMA_FULL_OR_IDLE`:
  ```text
  aktuelle Zendure-AC-Ladung + Restexport - Profilreserve
  ```
- ausschließlich unabhängige Zendure-Netzportbeobachtung als physische Referenz;
- bestätigte frische Neutralität als gültige 0-W-Referenz;
- kein Sollwert, Readback, Pack-, Offgrid-, PV- oder SMA-Wert als AC-Referenz;
- inkrementeller AUTO-Fallback bei stale, fehlender, konfliktbehafteter, entladender oder zeitlich inkohärenter Referenz;
- elf additive Status-/Measurement-V4-Felder;
- RC15→RC16-Headerrotation;
- Regressionfixture aus produktiver `SMA_FULL_OR_IDLE`-Unterallokation;
- Statusseite zeigt Absolutrechnung beziehungsweise Fallbackgrund.

## Nicht enthalten

- keine Änderung von Harvest Entry/Hold/Exit;
- keine Änderung von `HIGH_SMA_SOC`, `SMA_NEAR_LIMIT`, Primary Floor/Restart/Share;
- keine Änderung anderer AUTO-Zweige, NIGHT oder fester Modi;
- keine Änderung von Cross-Charge;
- keine Änderung von RC14-Taper oder RC15-Command-Safety;
- keine asynchrone lokale API;
- keine Readiness-, Settings- oder Offgrid-Änderung;
- keine neuen Config-Keys;
- keine Änderung persistenter Geräteeigenschaften;
- keine Änderung der Excel-Lernsimulation.

## Installation

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc16
```

## Produktivtestgrenze

RC16 ist nach dem Build regressionstestvalidiert, aber erst nach einer natürlichen, branchenspezifisch ausgewerteten `SMA_FULL_OR_IDLE`-Episode produktiv freigabefähig. Positive Zielwerte allein sind kein Funktionsnachweis.

## Buildvalidierung

```text
python3 -m py_compile *.py tools/*.py      OK
node --check static/status_v2.js           OK
bash -n tools/update_zendure_controller.sh OK
python3 -m json.tool config.example.json   OK
python3 -m unittest discover -s tests -q   452 Tests, OK
Measurement-V4 RC16 Standardfelder         228
Rekonstruierter RC15-Header                217
Rekonstruierter RC14-Header                203
```

Bekannte Python-3.13-`ResourceWarning`-Hinweise älterer SQLite-Tests bleiben bestehen; kein Test schlug fehl.

## Fachlich geänderte Dateien

```text
controller_logic.py
state.py
measurement_v4.py
measurement_v4_contract.py
status_page_v2.py
web_ui.py
static/status_v2.js
version.py
README.md
README_INSTALLATION.md
bestehende Versions-/Headerrotationstests
```

## Neu

```text
tests/test_v12_11_2_rc16_rcb_sma_full_or_idle_absolute_target.py
tests/fixtures/rc10_sma_full_or_idle_underallocation.csv
tests/fixtures/rc16_expected_sma_full_or_idle.json
RELEASE_INFO_V12_11_2_RC16.md
TECHNICAL_NOTES_V12_11_2_RC16.md
UEBERGABE_ZEC_V12_11_2_RC16_RCB_SMA_FULL_OR_IDLE_ABSOLUTZIEL.md
SPEZIFIKATION_ZEC_V12_11_2_RC16_RCB_SMA_FULL_OR_IDLE_ABSOLUTZIEL_FINAL.md
```

Gelöscht oder umbenannt: keine Dateien.
