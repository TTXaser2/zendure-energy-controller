# Technical Notes V12.11.2-RC15

## 1. Produktiver Anlass

Am 28.07.2026 wurde `FIXED_DISCHARGE` mit einem wirksamen Soll von −2.000 W aktiviert. Das Gerät meldete über rund 17 Minuten weiterhin `outputLimit=0` und 0 W physische Leistung. RC14 erzeugte in dieser Episode:

```text
1   FULL_STATE_COMMAND_SENT
157 COMMAND_LIMIT_UPDATED
8   FULL_STATE_RESYNC_SENT
166 aktive Publish-Batches
```

Erst kurz vor dem Abbruch wurde `outputLimit=2.000 W` rückgelesen und ungefähr −1.999 W physische Entladung sichtbar. Die Wirkung trat damit verspätet während des Intentwechsels auf.

## 2. Publish-/Readback-Isolation

RC14 führte im MQTT-Bridge-Cache dieselbe Datenstruktur für zwei verschiedene Tatsachen:

```text
zuletzt lokal publizierter Wert
zuletzt vom Gerät rückgelesener Wert
```

RC15 trennt:

```text
last_published_values
last_published_epoch_by_topic
last_device_readback_values
last_device_readback_epoch_by_topic
```

Nur ein lokal erfolgreich angenommener MQTT-Publish aktualisiert `last_published_values`. Ein expliziter Paho-Fehlercode oder eine Publish-Ausnahme aktualisiert weder Cache noch Sendecounter.

Geräte-State-Topics aktualisieren ausschließlich den Readback und den `ControllerState`.

## 3. Recovery-Vertrag

Bei konstantem Soll und abweichendem Readback gilt:

```text
ein Initialpublish
→ Wirkung beobachten
→ bestätigter Mismatch
→ Full-State-Resync nur nach bestehendem Recovery-Cooldown
```

Ein Readback von 0 W löst keinen normalen `COMMAND_LIMIT_UPDATED` mehr aus. `force=True` und der Full-State-Resync bleiben ausdrücklich recoveryfähig.

## 4. Late-Effect-Guard

Der Guard ist kein allgemeiner Moduswechselmechanismus. Er aktiviert sich nur, wenn:

```text
vorheriger Desired Intent = CHARGE oder DISCHARGE
UND bestätigter Mismatch bzw. Recovery nach diesem Mismatch
UND keine physisch bestätigte Recovery
UND neuer Wunsch = NEUTRAL oder Gegenrichtung
```

Nicht aktiviert wird er bei:

- gleicher Richtung;
- normal wirksamer Richtungsänderung;
- Wolken-/Wattänderungen;
- HOLD innerhalb derselben Richtung;
- Reason-Wechseln;
- bereits bestätigter Recovery.

Während des Guards werden nur beide Limits auf 0 gesetzt. Der vorhandene `acMode` bleibt bestehen. Damit wird kein zusätzlicher Moduswechsel für den neutralen Zwischenzustand erzeugt.

## 5. Zeit- und Freshness-Vertrag

Die frühere Planungsformulierung „drei Zyklen und sechs Sekunden“ wurde verworfen. RC15 verlangt:

1. frischen vollständigen Smart-Mode-/0/0-Readback;
2. gültige physische Neutralbeobachtung innerhalb der bestehenden Toleranz;
3. mindestens zwei unterschiedliche frische Power-Beobachtungen;
4. mindestens sechs Sekunden monotone Echtzeit seit erster gemeinsamer Bestätigung;
5. keinen Richtungs-CONFLICT.

Der Power-Zeitstempel beziehungsweise die Power-Sequenz bildet die Unabhängigkeit der Beobachtungen. Derselbe Telemetriewert in mehreren Regelzyklen wird nicht mehrfach gezählt. Damit bleibt das Verhalten unabhängig von einer konfigurierbaren Zyklusdauer von beispielsweise 1, 3, 10 oder 30 Sekunden.

## 6. Hardwareschonung

RC15 folgt `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md`:

- kein Guard im normalen Livebetrieb;
- kein unnötiger `acMode`-Wechsel;
- kein wiederholter Nullpublish;
- keine persistenten Geräteschreibvorgänge;
- gleiche Richtung bleibt reaktionsschnell;
- Gegenrichtung wird nur im nachgewiesenen unresolved-Mismatch-Fall verzögert;
- Guard-Aktivierungen, Dauer, blockierte Aktivkommandos, AC-Moduswechsel und physische Richtungswechsel werden messbar.

Ein 0-W- oder `acMode`-Kommando wird nicht automatisch als mechanischer Relaisvorgang bezeichnet, solange dies nicht durch Gerätearchitektur oder Telemetrie belegt ist.

## 7. `inverseMaxPower`

`inverseMaxPower` und `outputLimit` sind getrennte Eigenschaften. Im Produktpaket war `inverseMaxPower=2.000 W` bereits vor dem manuellen Entladebefehl vorhanden. RC15:

- liest den Wert weiterhin nur;
- dokumentiert Quelle und Freshness;
- verwendet ihn weiterhin konservativ in der bestehenden Gerätebegrenzung;
- bezeichnet ihn nicht als bewiesenes physisches Hardwaremaximum;
- schreibt ihn niemals im Runtime-Pfad.

## 8. Neue Measurement-V4-Felder

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
zendure_device_inverse_max_power_source
zendure_device_inverse_max_power_age_s
```

RC14-Header werden erkannt und in eine neue `schema_rc15`-Datei rotiert. Ältere Dateien bleiben unverändert.

## 9. Produktive Regressionfixture

```text
tests/fixtures/rc14_fixed_discharge_failure_20260728.csv
tests/fixtures/rc15_expected_command_events.json
```

Die Fixture enthält 333 reale Zyklen der konstanten −2.000-W-Episode ohne Credentials oder Gerätekennung. Sie bestätigt:

- Desired Sequence ID bleibt 29;
- finales Soll bleibt −2.000 W trotz Config-Hash-Wechsel;
- RC14 erzeugte 157 normale Wiederholungspublishes;
- RC15-Bridge-Dedupe bleibt trotz 333 wiederholter 0-W-Readbacks bei einem normalen Initialpublish;
- `inverseMaxPower=2.000 W` war bereits vor Aktivierung des manuellen Commands vorhanden.

## 10. Unveränderte Grenzen

- keine Regler-Zielwertformel geändert;
- RC14-Taper unverändert;
- Flash-Schutz unverändert;
- NIGHT, Cross-Charge und Harvest unverändert;
- Offgrid-Trennung unverändert;
- lokale API weiterhin synchron;
- Excel-Lernsimulation bitidentisch.

## 11. Buildvalidierung

```text
Python-Compile:             OK
JavaScript-Syntax:          OK
Update-Shell-Syntax:        OK
Config-Beispiel JSON:       OK
Unit-Tests:                 437, OK
RC15-V4-Standardfelder:     217
rekonstruierter RC14-Header:203
```

Die bekannten Python-3.13-SQLite-`ResourceWarning`-Hinweise älterer Tests sind unverändert und verursachten keinen Testfehler.
