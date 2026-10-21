# Technical Notes V12.11.2-RC16

## 1. Mathematischer Anlass

Mit:

```text
S = Überschuss vor Zendure
C = aktuelle Zendure-AC-Ladung
E = verbleibender Netzexport = S - C
R = Profilreserve
```

verwendete der bisherige Zweig sinngemäß:

```text
C_neu = E - R
```

Dadurch entsteht stationär:

```text
C = (S - R) / 2
```

RC16 verwendet:

```text
C_neu = C + E - R = S - R
```

Damit verschwindet das systematische Halbierungsgleichgewicht.

## 2. Branchengrenze

Die Änderung liegt ausschließlich in `_rest_surplus_charge_pressure_target()` bei:

```text
rest_surplus_harvest_reason = SMA_FULL_OR_IDLE
```

Entry, Bestätigung, Hold, Exit und alle anderen Harvest-Gründe bleiben unverändert. Ein bereits aktiver Hold-Zustand bleibt auch bei Restexport unterhalb der Eintrittsschwelle in der Absolutsemantik; dadurch kann ein signed negatives Delta das bestehende Ladeziel korrekt reduzieren.

## 3. Physische Referenz

Gültige positive Referenz:

```text
zendure_power_observation_direction = CHARGE
zendure_power_observation_confidence = HIGH
zendure_power_observation_signed_w > 0
Alter <= 15 s
kein CONFLICT
```

Gültige neutrale Referenz:

```text
direction = NEUTRAL
confidence = MEDIUM
beide expliziten AC-Richtungstopics frisch
```

Unzulässig als Referenz sind insbesondere:

```text
last_input_power
gewünschter Sollwert
inputLimit-Readback
outputPackPower / packInputPower
gridOffPower
Headunit-PV-Leistung
SMA-Leistung
Sollrichtung
```

## 4. Zeitliche Kohärenz

Standort-Netzleistung und Zendure-Netzportbeobachtung müssen jeweils frisch sein. Zusätzlich darf ihr Zeitversatz 15 s nicht überschreiten. Grid-Spikes bleiben durch die bestehende Plausibilitätsfilterung ausgeschlossen.

RC16 führt keinen neuen Timer und keine zykluszahlabhängige Bestätigung ein.

## 5. Fallback

Bei unsicherer Referenz:

```text
fallback_raw_target_w
= last_input_power + CONTROL_GAIN * effective_export_power
```

Dieser Wert ist ein inkrementelles Reglerziel, kein physisch bestätigter Absolutkandidat. Deshalb gilt diagnostisch:

```text
harvest_target_semantics = INCREMENTAL_FALLBACK
harvest_candidate_absolute_w = 0
harvest_reference_charge_valid = false
```

Sobald die physische Referenz wieder gültig ist, erfolgt automatisch die Rückkehr zu `ABSOLUTE` ohne Latch.

## 6. Nachgeschaltete Pipeline

Unverändert bleiben:

```text
MAX_CHARGE_POWER_W
Smoothing
MAX_POWER_STEP_W
MIN_COMMAND_CHANGE_W
Cross-Charge
read-only Gerätebegrenzungen
Command-State-Gate
smartMode-/Flash-Schutz
RC15-Publish-Deduplizierung
Command-Effect und Recovery
```

Auf einen gültigen Absolutkandidaten wird `CONTROL_GAIN` nicht nochmals angewandt.

## 7. Neue Measurement-V4-Felder

```text
harvest_target_semantics
harvest_reference_charge_w
harvest_reference_charge_source
harvest_reference_charge_confidence
harvest_reference_charge_age_s
harvest_reference_charge_valid
harvest_reference_fallback_reason
harvest_profile_reserve_w
harvest_candidate_delta_w
harvest_candidate_absolute_w
harvest_input_time_skew_s
```

`harvest_candidate_raw_w` enthält im `SMA_FULL_OR_IDLE`-Zweig weiterhin den tatsächlich weiterverarbeiteten, nichtnegativen Rohkandidaten. Die neuen Felder trennen Referenz, Delta, Absolutkandidat und Fallback explizit.

## 8. Regressionstests

Die RC16-Tests decken unter anderem ab:

- 300 + 600 − 250 = 650 W;
- Restexport gleich Reserve hält die beobachtete aktuelle Ladung;
- negatives Delta reduziert ein bestehendes Ladeziel;
- neutrale frische AC-Beobachtung als 0-W-Referenz;
- stale, fehlende, `UNKNOWN`, `CONFLICT` und `DISCHARGE` als Fallback;
- Zeitversatz;
- unveränderte Smoothing-/Step-/Command-Pipeline;
- keine zusätzlichen `acMode`- oder Gegenrichtungsbefehle;
- produktive Unterallokationsfixture;
- V4-Rotation RC15→RC16.

## 9. Unveränderte Sicherheitsverträge

- RC14-High-SOC-Acceptance/Taper;
- RC15-Publish-/Readback-Isolation;
- RC15-Late-Effect-Guard;
- Neutralization-Dedupe;
- Flash-Schutz und Schreib-Whitelist;
- Cross-Charge und Offgrid-Trennung;
- `inverseMaxPower` read-only;
- keine persistente Gerätekonfiguration.

## 10. Buildvalidierung

```text
Python-Compile:              OK
JavaScript-Syntax:           OK
Update-Shell-Syntax:         OK
Config-Beispiel JSON:        OK
Unit-Tests:                  449, OK
RC16-V4-Standardfelder:      228
rekonstruierter RC15-Header: 217
rekonstruierter RC14-Header: 203
```

Die bekannten Python-3.13-SQLite-`ResourceWarning`-Hinweise verursachten keinen Testfehler.
