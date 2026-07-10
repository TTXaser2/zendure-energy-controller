# Technical Notes – V12.11.1-RC2

## 1. Zweck

V12.11.1-RC2 ist ein kleiner Nachprüf- und Diagnosekorrektur-Release auf Basis von V12.11.1-RC1. Ziel ist nicht eine neue Harvest-Strategie, sondern die Absicherung des nach der RC1-Produktivprüfung gefundenen Cross-Charge-Diagnosebefunds.

## 2. Befund aus RC1

In produktiven V4-Daten traten kurze Phasen auf, in denen der Primärspeicher entlud (`second_battery_power_w < 0`) und Zendure weiter ein positives Ladeziel hatte. Die V4-Diagnose meldete jedoch `control_cross_charge_detected=0` und `target_final_reason=AUTO_GRID_EXPORT`.

Die Codeprüfung zeigte: Der bestehende Cross-Charge-Guard kann ein bereits aktives AUTO-/HOLD-Ziel proportional korrigieren. Die V4-Abbildung konnte diese Korrektur aber übersehen, wenn der generische Reason noch wie ein normaler AUTO-Export-Grund aussah.

## 3. Änderungen

- V4-Mapping wertet `cross_charge_guard_active`, `cross_charge_guard_limited` und `technical_limiters=CROSS_CHARGE` als maßgebliche Cross-Charge-Signale.
- `target_final_reason` wird in solchen Fällen als `CROSS_CHARGE_REDUCED` bzw. `CROSS_CHARGE_BLOCKED` abgebildet.
- `control_cross_charge_detected`, `control_cross_charge_limited` und `target_changed_by_cross_charge` werden auch dann korrekt gesetzt, wenn der ursprüngliche Control-Reason noch `AUTO_GRID_EXPORT` lautet.
- Neue Regressionstests bilden das reale RC1-Muster nach: bestehendes Zendure-Ladeziel, Primärspeicher entlädt, Cross-Charge reduziert das Ziel proportional.
- Die diagnostische Zendure-Restkapazität fällt nun von `ZENDURE_BATTERY_CAPACITY_KWH` auf `ZENDURE_BATTERY_CAPACITY_WH / 1000` zurück, wenn der kWh-Wert nicht gesetzt ist.

## 4. Nicht geändert

- Keine Änderung an MQTT-Topic- oder Kommandostruktur.
- Keine Änderung an NIGHT_DISCHARGE oder festen Modi.
- Keine Änderung an der HARVEST_HIGH_SMA_SOC-Strategie aus RC1.
- Keine UI-Umsetzung.

## 5. Tests

Zusätzliche Tests in `tests/test_v12_11_1_rc2_cross_charge_diagnostics.py` prüfen:

- Cross-Charge-Flags aus Guard-Feldern trotz generischem AUTO-Reason.
- Cross-Charge-Erkennung aus Limiter-Summary.
- reales RC1-Muster mit bestehendem AUTO-Ladeziel und entladendem Primärspeicher.
- Fallback der Zendure-Kapazitätsdiagnose von Wh auf kWh.
