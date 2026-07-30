# Spezifikation V12.11.2-RC15 – Revision 2

**Stand:** 29.07.2026  
**Basis:** V12.11.2-RC14  
**Status:** revidierte Spezifikation zur Buildfreigabe; keine Codeänderung  
**Ersetzt:** `SPEZIFIKATION_ZEC_V12_11_2_RC15_COMMAND_PUBLISH_READBACK_GUARD.md`

## 1. Korrigierte Ausgangslage

`inverseMaxPower` und `outputLimit` sind getrennte Zendure-Eigenschaften und getrennte MQTT-State-Topics.

Im Analysebestand war:

```text
zendure_device_inverse_max_power_w = 2.000 W
```

bereits spätestens seit 27.07.2026 00:32:21 CEST vorhanden. Der manuelle Entladebefehl wurde erst am 28.07.2026 um 16:55:10 CEST aktiviert. Der Wert kann daher im konkreten Vorfall nicht die Rückspiegelung des ersten `outputLimit=2.000-W`-Kommandos gewesen sein.

Die genaue Herkunft bleibt separat zu validieren. Der Wert wird nicht als Hardwarecap bezeichnet, sondern als rückgelesene Gerätebegrenzung mit Source-/Freshness-Vertrag.

## 2. Kernfix

Publish-Historie und Geräte-Readback werden getrennt:

```text
last_published_value
last_publish_epoch
latest_device_readback
latest_readback_epoch
```

Geräte-State-Topics dürfen den lokalen Publish-Cache nicht überschreiben.

Bei unverändertem Soll und abweichendem Readback:

```text
ein Initialpublish
→ Wirkung beobachten
→ Mismatch
→ nur definierter Full-State-Resync nach Cooldown
```

Keine normalen `COMMAND_LIMIT_UPDATED` im Regelraster.

## 3. Eng begrenzter Late-Effect-Guard

### Aktivierung

Nur wenn gemeinsam gilt:

```text
vorheriger Intent = CHARGE oder DISCHARGE
COMMAND_MISMATCH_CONFIRMED oder RECOVERY_VERIFYING
keine physisch bestätigte Recovery
neuer fachlicher Wunsch = NEUTRAL oder Gegenrichtung
```

Kein Guard bei gleicher Richtung, normal wirksamer Regelung, reiner Zielwertänderung, HOLD innerhalb derselben Richtung, Reason-Wechsel oder bereits bestätigter Recovery.

### Neutralisierung

Während des Guards:

```text
inputLimit = 0
outputLimit = 0
```

Der vorhandene `acMode` bleibt grundsätzlich bestehen. Ein `acMode`-Wechsel erfolgt erst nach Guard-Freigabe und nur bei tatsächlich benötigter Gegenrichtung.

### Zeitsemantik

Die frühere Formulierung „3 Zyklen und mindestens 6 Sekunden“ entfällt.

Freigabe verlangt:

1. frischen vollständigen 0/0-Readback,
2. gültige physische Neutralbeobachtung,
3. mindestens zwei unabhängige frische gemeinsame Neutralbeobachtungen,
4. mindestens 6 Sekunden monotone reale Zeit seit erster gemeinsamer Neutralbestätigung,
5. keinen Richtungs-CONFLICT.

Unabhängige Beobachtung bedeutet neuer Measurement-/Power-Quellzeitstempel oder neue Sequenz. Identische Telemetrie darf nicht mehrfach gezählt werden.

`INTERVAL_SECONDS` wird nicht mit einer festen Zykluszahl multipliziert.

Beispiele:

```text
INTERVAL_SECONDS = 1 s  → frühestens nach 6 s
INTERVAL_SECONDS = 3 s  → typischerweise nach etwa 6–9 s
INTERVAL_SECONDS = 30 s → zweite frische Beobachtung typischerweise nach etwa 30 s;
                          keine Forderung nach 3 × 30 s
```

## 4. Verschleiß- und Reaktionsinvarianten

RC15 muss nachweisen:

- kein Guard bei normalen Modus- oder Zielwechseln,
- kein unnötiger `acMode`-Wechsel,
- kein wiederholter Nullpublish,
- kein Guard-Latch,
- gleiche Richtung bleibt reaktionsschnell,
- Gegenrichtung wird nur im unresolved-Mismatch-Fall verzögert,
- Guard-Dauer basiert auf realer Zeit und frischen Daten,
- keine persistenten Geräteschreibvorgänge,
- RC14-Taper, NIGHT, Cross-Charge und Harvest bleiben unverändert.

## 5. Diagnose

```text
command_readback_matches_desired
command_readback_mismatch_fields
command_late_effect_guard_active
command_late_effect_guard_previous_intent
command_late_effect_guard_pending_intent
command_late_effect_guard_pending_target_w
command_late_effect_guard_duration_s
command_late_effect_guard_reason
command_late_effect_guard_activation_count
command_late_effect_guard_blocked_command_count
command_ac_mode_change_count
physical_power_direction_change_count
```

## 6. Pflichtchecks für `inverseMaxPower`

- Quelle und Freshness loggen.
- Nicht als Hardwarefähigkeit bezeichnen.
- ZEC-Konfigurationslimit, rückgelesenes `inverseMaxPower`, offizielles Produktmaximum und angewandtes `outputLimit` getrennt darstellen.
- Keine Runtime-Schreibvorgänge an `inverseMaxPower`.
- Read-only-Produktivprüfung gegen MQTT und lokale API.

## 7. Tests

- unverändertes Soll 2.000 W, Readback 0 W: kein normales Wiederholungspublish;
- Nutzerwert 2.000→2.300 W bei rückgelesenem `inverseMaxPower=2.000 W`: kein neuer physischer Sollwert;
- unresolved DISCHARGE-Mismatch → CHARGE: Guard aktiv;
- unresolved DISCHARGE-Mismatch → weiterhin DISCHARGE: kein Guard;
- normal wirksamer Richtungswechsel: kein Late-Effect-Guard;
- `INTERVAL_SECONDS` 1, 3, 10 und 30: reale Zeit und frische Beobachtungen, keine starre Zyklusverzögerung;
- identische Telemetrie zählt nicht mehrfach;
- 0/0-Readback bei noch aktiver Altleistung: Guard bleibt;
- physisch neutral bei stale Readback: Guard bleibt.

## 8. Buildgrenze

RC15 darf erst nach ausdrücklicher Freigabe dieser Revision gebaut werden.

Bis dahin:

```text
RC14 in AUTO weiterbetreiben
keine weiteren festen Lade-/Entladetests
keine Schreibversuche an inverseMaxPower
```
