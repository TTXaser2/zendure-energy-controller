# Technical Notes V12.11.2-RC13

## Scope

RC13 ist ein enger Nachkorrekturrelease der RC12-Command-/Wirkungsschicht. Die produktive Analyse des Morgenzyklus vom 27.07.2026 zeigte bei ansonsten funktionierendem Flash-Schutz:

- 2.118 logische Full-State-Neutralisierungsbatches,
- wechselnde `FULL_STATE_VERIFY`-/`FULL_STATE_APPLY`-Signaturen, welche das 30-s-Retry-Fenster aushebelten,
- unnötige Resyncs während einer plausiblen BMS-Taper-Phase.

## Neutralization-Dedupe

Die Episodenidentität wird über den physischen Nullzustand bestimmt:

```text
intent=NEUTRALIZE
acMode
inputLimit=0
outputLimit=0
```

Der fachliche Reason ist nicht Teil der physischen Signatur. Nach bestätigter Neutralität bleibt die Episode geschlossen, auch wenn der Grund beispielsweise von `MIN_SOC_LIMIT` auf `SAFE_STATE` wechselt.

## Command-State-Gate

Neue Zustände:

```text
UNPROTECTED
WAIT_SMART_MODE_READBACK
WAIT_FULL_STATE_READBACK
READY
SAFETY_NEUTRALIZATION_WAITING
```

Der Retry-Schlüssel enthält Gate-Phase und Intent, nicht den exakten Wattwert. Nicht neutrale Force-/Resync-Pfade umgehen den Smart-Mode-Schutz nicht.

## Effect Tracking

Neue effektive Toleranz:

```text
max(COMMAND_EFFECT_TOLERANCE_W,
    abs(target) * COMMAND_EFFECT_TOLERANCE_PERCENT / 100)
```

Default der relativen Toleranz: 10 %.

Die Ladeannahmediagnose betrachtet die obere 10-Prozentpunkte-Zone. `COMMAND_CHARGE_ACCEPTANCE_LIMITED` setzt weiterhin voraus:

- vollständig rückgelesenen gewünschten Lade-Command-State,
- bestätigte netzseitige Laderichtung,
- bestätigte Batterieladung,
- frischen hohen SOC,
- Diagnosezustand `limited` oder `not_accepting`.

## Measurement V4

Additive RC13-Felder:

```text
command_publish_event_id
command_publish_epoch_s
command_state_gate_state
command_state_retry_remaining_s
command_neutralization_episode_id
```

RC12-Header werden erkannt und in eine neue `schema_rc13`-Sitzungsdatei fortgeführt.

## Unveränderte Grenzen

- keine Harvest-Formel geändert;
- keine lokale-API-Architektur geändert;
- keine persistenten Zendure-Eigenschaften beschreibbar;
- Offgrid-Konfiguration unverändert;
- Excel-Lernsimulation bitidentisch.

## Buildvalidierung

```text
Python-Compile:  OK
JavaScript:      OK
Update-Shell:    OK
Unit-Tests:      410, OK
```
