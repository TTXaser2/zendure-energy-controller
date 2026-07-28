# Technical Notes V12.11.2-RC14

## 1. Scope

RC14 ist ein enger Nachkorrekturrelease der RC13-Command-Effect-Schicht. Die reale Ladeendepisode vom 27.07.2026 zeigte:

```text
SOC 98 %
Soll +914 bis +1.580 W
reale Ladeleistung +579 → +125 → +74 → +73 → 0 W
zwei Full-State-Resyncs ohne Verbesserung
anschließend SOC 100 %
```

Die RC13-Kategorie `COMMAND_CHARGE_ACCEPTANCE_LIMITED` griff nicht, weil gleichzeitig exakte Ziel-/Readback-Gleichheit, Standortexport und positive Mindestleistungen verlangt wurden.

## 2. Bestätigter Command-Referenzwert

RC14 bestätigt für eine High-SOC-Reklassifikation ausschließlich den statischen Ladevertrag:

```text
smartMode frisch = 1
Command-State vollständig
acMode = Input mode
outputLimit = 0
aktives inputLimit >= COMMAND_EFFECT_MIN_TARGET_W
```

Die Referenz ist:

```text
command_effect_reference_w = min(
    aktuelles positives Soll,
    rückgelesenes positives inputLimit
)
```

Das neueste fluktuierende Soll muss nicht exakt mit dem asynchron rückgelesenen Limit übereinstimmen.

## 3. `HIGH_SOC_CHARGE_LIMITED`

Zusätzlich erforderlich:

```text
SOC >= MAX_SOC_PERCENT - 10
Observation-Richtung = CHARGE
netzseitige Ladeleistung >= 20 W
Batterieladung >= 20 W
keine Batterieentladung
charge_acceptance_state in {limited, not_accepting}
```

Standort-Netzexport ist kein Pflichtprädikat der Command-Wirkungsreklassifikation.

Ergebnis:

```text
command_effect_category = COMMAND_CHARGE_ACCEPTANCE_LIMITED
command_lifecycle_state = ACTIVE_ACCEPTANCE_LIMITED
command_effect_confirmed = false
```

## 4. `HIGH_SOC_NOT_ACCEPTING`

Am/über Max-SOC kann vollständige Nichtannahme klassifiziert werden, wenn:

```text
statischer Ladevertrag bestätigt
aktives rückgelesenes inputLimit
Observation = NEUTRAL
Batterieladung < 20 W
keine Entladung
charge_acceptance_state = not_accepting
```

Bestätigung:

```text
mindestens 3 Zyklen
und mindestens 6 Sekunden
```

Unterhalb Max-SOC bleibt 0 W strenger. Zusätzlich ist unabhängige Unterstützung erforderlich:

- Restexport oberhalb Deadband,
- dokumentierter vorheriger Taper derselben Charge-Episode,
- oder persistente Nichtannahmediagnose.

## 5. Niedrig-SOC-Schutz

RC14 reklassifiziert keine Nichtwirkung bei niedrigem SOC. Beispiel:

```text
SOC 10 %
Soll/Readback +2.397 W
Ist 0 W
→ Mismatch
→ bestehender Full-State-Recovery-Pfad
```

Falscher AC-Modus, unvollständiger Command-State, Gegenlimit ungleich 0 sowie DISCHARGE/CONFLICT verhindern ebenfalls jede Acceptance-Reklassifikation.

## 6. Measurement V4

Additive RC14-Felder:

```text
charge_acceptance_state
charge_acceptance_reason
command_effect_reference_w
```

RC13-Header werden erkannt und in eine neue `schema_rc14`-Sitzungsdatei fortgeführt. RC10–RC12 werden ebenfalls direkt auf eine neue RC14-Datei rotiert. Alte Dateien bleiben unverändert.

`COMMAND_EFFECT_TOLERANCE_PERCENT` ist nun Bestandteil von:

```text
CONTROL_SNAPSHOT_KEYS
CONTROL_HASH_KEYS
zec_config_snapshots.json
Manifest-Reproduzierbarkeit
```

## 7. Produktive Regressionfixture

Enthalten:

```text
tests/fixtures/rc13_taper_episode_20260727.csv
tests/fixtures/rc14_expected_checkpoints.json
```

Die Fixture enthält 124 reale RC13-Zyklen und keine Zugangsdaten. Geprüft werden insbesondere:

- 16:26:59 – 98 %, Soll 1.449 W, Readback 1.400 W, Ist 125 W;
- 16:29:02 – 98 %, Soll 1.112 W, Readback 1.172 W, Ist 74 W, kein Export;
- 100-%-Nichtannahme mit 0 W;
- keine Mismatch-/Resync-Serie;
- Niedrig-SOC-Negativkontrolle.

## 8. Unveränderte Grenzen

- keine AUTO-/Harvest-Zielwertformel geändert;
- Flash-Schutz und Command-State-Gate unverändert;
- Neutralization-Dedupe unverändert;
- keine lokale-API-Architekturänderung;
- keine persistenten Zendure-Eigenschaften beschreibbar;
- Offgrid-Konfiguration unverändert;
- Excel-Lernsimulation bitidentisch.

## 9. Diagnosehinweis

`command_state_gate_state` bleibt ein Diagnose-/Last-Gate-State. Das Feld allein ist keine globale Readiness-Aussage und kann nach bereits bestätigter Wirkung noch einen zuvor gesetzten Wartezustand zeigen. RC14 verändert die Gate-Steuerlogik bewusst nicht.

## 10. Buildvalidierung

```text
Python-Compile:  OK
JavaScript:      OK
Update-Shell:    OK
Unit-Tests:      419, OK
```
