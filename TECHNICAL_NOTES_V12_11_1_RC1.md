# Technical Notes – V12.11.1-RC1

## Zweck

V12.11.1-RC1 erweitert die bestehende Restüberschuss-Ernte um `HARVEST_HIGH_SMA_SOC` als vollständigen Parallel-Harvest-Regelzweig. Ziel ist nicht nur die Behebung des beobachteten 0-W-Harvest-Latches bei vollem SMA-Speicher, sondern ein tageszeitabhängiges Betriebskonzept, das ab konfigurierbarem Primärspeicher-SOC echte solare Lade-/Überschussleistung zwischen Primärspeicher und Zendure verteilt.

## Regelstrategie

- Hauptmodus bleibt AUTO/CHARGE; es wird kein neuer Hauptmodus eingeführt.
- `target_final_reason` bleibt `REST_SURPLUS_HARVEST`; der konkrete Untergrund wird in `rest_surplus_harvest_reason` diagnostiziert.
- Unterstützte Harvest-Gründe:
  - `SMA_NEAR_LIMIT`: bestehende Basis-Ernte bei Primärspeicher nahe Ladeleistungsgrenze.
  - `HIGH_SMA_SOC`: Parallel-Harvest ab konfigurierbarer Primärspeicher-SOC-Schwelle.
  - `HIGH_SMA_SOC_SMA_NEAR_LIMIT`: beide Bedingungen aktiv.
  - `SMA_FULL_OR_IDLE`: Primärspeicher voll/nahe voll, lädt kaum noch, echter Export vorhanden.
  - `LATCH_RECOVERY`: Schutz gegen aktiven Harvest mit dauerhaft 0 W trotz belastbarem Export.
- Charge-Pressure-Allokation statt reiner Exportformel:
  - `charge_pressure_w = grid_export_w + primary_charge_w + zendure_charge_w`.
  - Daraus wird eine Primärspeicher-Reserve aus Floor und Zielanteil abgezogen.
  - Ergebnis wird durch Max-Ladeleistung, SOC, Cross-Charge, Rampen, Smoothing und Mindeständerung begrenzt.

## Wichtige Defaults

- `HARVEST_HIGH_SMA_SOC_ENABLED = true`
- `HARVEST_HIGH_SMA_SOC_ENTER_PERCENT = 75`
- `HARVEST_HIGH_SMA_SOC_EXIT_PERCENT = 70`
- `HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W = 300`
- `HARVEST_HIGH_SMA_SOC_HOLD_SECONDS = 180`
- `HARVEST_PRIMARY_CHARGE_FLOOR_RATIO = 0.30`
- `HARVEST_PRIMARY_CHARGE_RESTART_RATIO = 0.85`
- `HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO = 0.95`
- Zeitprofil aktiv:
  - morgens: Primärspeicher-Anteil 0.60, Reserve 250 W, Entry 60 s
  - mittags: Primärspeicher-Anteil 0.50, Reserve 150 W, Entry 30 s
  - nachmittags: Primärspeicher-Anteil 0.35, Reserve 100 W, Entry 15 s

Absolute Watt-Overrides sind möglich, damit Primärspeicher mit anderen Leistungsparametern sinnvoll justiert werden können.

## Diagnose und Measurement V4

V4 wurde um kompakte Harvest-Diagnosefelder erweitert, unter anderem:

- `rest_surplus_harvest_reason`
- `rest_surplus_harvest_profile`
- `rest_surplus_hold_remaining_s`
- `harvest_primary_floor_w`
- `harvest_primary_restart_w`
- `harvest_primary_near_limit_w`
- `harvest_primary_target_share`
- `harvest_primary_required_w`
- `harvest_primary_share_reserve_w`
- `harvest_candidate_raw_w`
- `harvest_candidate_after_primary_w`
- `harvest_limiter_reason`
- `harvest_capacity_mode`
- `primary_remaining_capacity_kwh`
- `zendure_remaining_capacity_kwh`

Kapazität wird in RC1 nur diagnostisch ausgewertet. Eine spätere weiche Kapazitätsgewichtung bleibt als prüfbarer Backlog-Punkt vorbereitet, verändert aber in RC1 den Zielwert nicht hart.

## Sicherheits- und Regressionsleitplanken

- Symmetrischer Cross-Charge-Schutz bleibt vorrangig.
- `NIGHT_DISCHARGE`, `FIXED_CHARGE`, `FIXED_DISCHARGE` und Safe-State werden nicht durch High-SOC-Harvest geändert.
- Wenn `REST_SURPLUS_HARVEST_ENABLED=false`, bleibt das normale AUTO-Verhalten unverändert.
- Bestehende Basis-Harvest-Tests wurden auf High-SOC-off abgesichert.

## Tests

Zusätzliche Tests in `tests/test_v12_11_1_rc1_high_sma_harvest.py` prüfen:

1. realen 0-W-Latch-Bugfall mit SMA 100 %, Export, Zendure SOC 82 % und MQTT OK,
2. Entry ab 75 % Primärspeicher-SOC,
3. kein Entry unterhalb der Enter-Schwelle,
4. Primärspeicher-Share/Floor begrenzt Zendure-Ladung,
5. Cross-Charge bleibt vorrangig,
6. Kapazität ist diagnostisch verfügbar, aber kein harter Echtzeit-Regler.

Validierung:

```bash
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -v
```

Ergebnis im Build: 265 Tests OK.
