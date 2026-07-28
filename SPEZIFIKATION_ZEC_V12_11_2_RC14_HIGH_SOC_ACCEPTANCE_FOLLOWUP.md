# Spezifikation V12.11.2-RC14
## High-SOC-Ladeannahme-Nachkorrektur und Diagnosevertrag

**Stand:** 27.07.2026  
**Basis:** V12.11.2-RC13  
**Status:** Spezifikation zur Freigabe; keine Codeänderung  
**Normative Grundlage:** `ZEC_ANALYSE_REGELWERK_V1.1.md`

---

## 1. Ziel

RC14 korrigiert ausschließlich die produktiv nicht greifende High-SOC-Ladeannahme-/Taper-Reklassifikation von RC13 und ergänzt die dafür fehlende V4-/Config-Reproduzierbarkeit.

RC14 verändert keine Regler-Zielwertformel.

---

## 2. Produktiver Anlass

Reproduzierte RC13-Episode:

```text
SOC 98 %
Soll +914 → +1.580 W
reale Ladeleistung +579 → +125 → +74 → +73 W
zwei Full-State-Resyncs ohne Verbesserung
SOC anschließend 100 %
Soll +1.532 W, rückgelesenes inputLimit +1.532 W
reale Ladeleistung 0 W
```

`COMMAND_CHARGE_ACCEPTANCE_LIMITED` trat in 1.353 Zyklen kein einziges Mal auf.

Die aktuelle Bedingung verlangt gleichzeitig:

- exakte Gleichheit des rückgelesenen aktiven Limits mit dem neuesten dynamischen Ziel,
- mindestens 80 W Standort-Netzexport,
- beobachtete Laderichtung mit mindestens 20 W,
- mindestens 50 W Batterieladung.

Das verhindert sowohl dynamisches Taper als auch vollständiges `not_accepting` bei 0 W.

---

## 3. Verbindlicher Scope

### Bestandteil

1. Trennung von:
   - `HIGH_SOC_CHARGE_LIMITED`
   - `HIGH_SOC_NOT_ACCEPTING`
2. Statische statt exakt-dynamische Command-State-Bestätigung für Taper.
3. Verwendung des rückgelesenen aktiven Limits als Command-Referenz.
4. Keine zwingende Standort-Netzexport-Bedingung für die Command-Wirkungsreklassifikation.
5. Separater 0-W-Nichtannahmefall am/über Max-SOC.
6. Schutz gegen Verschleierung echter Niedrig-SOC-Nichtwirkung.
7. Additive V4-Felder für Ladeannahmediagnose.
8. Aufnahme von `COMMAND_EFFECT_TOLERANCE_PERCENT` in Config-Snapshot und Control-Hash.
9. Produktive RC13-Episode als Regressionstest.

### Nicht Bestandteil

- keine `SMA_FULL_OR_IDLE`-Absolutzielkorrektur;
- keine Änderung von AUTO-/Harvest-Zielwerten;
- keine API-Entkopplung;
- keine Readiness-/Sticky-Error-Korrektur;
- keine Änderung der Neutralization-Dedupe- oder Command-Gate-Logik;
- keine Offgrid-Konfigurationsänderung;
- kein Settings-Redesign.

---

## 4. Gemeinsame Sicherheitsvoraussetzungen

Eine High-SOC-Ladeannahme-Reklassifikation ist nur zulässig, wenn:

```text
smartMode frisch = 1
Command-State vollständig
acMode = Input mode
outputLimit = 0
kein Power-Richtungskonflikt
SOC frisch und >= MAX_SOC_PERCENT - 10
aktiver CHARGE-Intent
aktives rückgelesenes inputLimit >= COMMAND_EFFECT_MIN_TARGET_W
charge_acceptance_state in {limited, not_accepting}
```

Die exakte Gleichheit:

```text
rückgelesenes inputLimit == neuestes Soll
```

ist nicht erforderlich.

Das rückgelesene aktive Limit ist der tatsächlich bestätigte Command-Referenzwert:

```text
command_reference_w = min(
    aktuelles positives Soll,
    rückgelesenes positives inputLimit
)
```

Liegt das rückgelesene aktive Limit unter der Diagnosegrenze, ist keine Acceptance-Reklassifikation zulässig.

---

## 5. Fall A: `HIGH_SOC_CHARGE_LIMITED`

Voraussetzungen zusätzlich:

```text
Observation-Richtung = CHARGE
netzseitige Zendure-Ladeleistung >= 20 W
Batterieladung >= 20 W
keine Batterieentladung
charge_acceptance_state = limited oder not_accepting
```

Der Standort-Netzexport ist nur Diagnosefeld und keine zwingende Voraussetzung.

Ergebnis:

```text
command_effect_category = COMMAND_CHARGE_ACCEPTANCE_LIMITED
command_lifecycle_state = ACTIVE_ACCEPTANCE_LIMITED
command_effect_confirmed = false
kein Mismatch
kein periodischer Full-State-Resync
```

Die Kategorie bestätigt nicht das Sollwerttracking und nicht das Systemziel.

---

## 6. Fall B: `HIGH_SOC_NOT_ACCEPTING`

### 6.1 Am/über Max-SOC

Wenn:

```text
SOC >= MAX_SOC_PERCENT
Command-State statisch bestätigt
rückgelesenes inputLimit aktiv
Observation = NEUTRAL
Batterieladung < 20 W
keine Entladung
charge_acceptance_state = not_accepting
```

darf nach kurzer Bestätigung, beispielsweise 2–3 Zyklen beziehungsweise 6–10 s, klassifiziert werden:

```text
COMMAND_CHARGE_ACCEPTANCE_LIMITED
Reason: Gerät/BMS nimmt am Max-SOC keine weitere Ladeleistung an.
```

Kein Full-State-Resync.

### 6.2 Unter Max-SOC, aber in High-SOC-Zone

Bei 0 W realer Ladeleistung unterhalb des Max-SOC bleibt der Schutz strenger.

Eine Acceptance-Reklassifikation ist nur zulässig, wenn zusätzlich mindestens eines der folgenden unabhängigen Signale vorliegt:

- persistenter Standort-Netzexport oberhalb Deadband,
- unmittelbar vorher dokumentierter monotoner Taper derselben Charge-Episode,
- geräteseitige Diagnose `not_accepting` über eine bestätigte Mindestdauer.

Andernfalls bleibt der normale Mismatch-/Recovery-Pfad erhalten.

---

## 7. Mismatch bleibt zwingend

Keine Acceptance-Reklassifikation bei:

```text
SOC deutlich unter High-SOC-Zone
smartMode nicht frisch 1
Command-State unvollständig
acMode falsch
outputLimit != 0
rückgelesenes inputLimit unter Diagnosegrenze
Power-Richtung DISCHARGE oder CONFLICT
SOC fällt physikalisch widersprüchlich
```

Mindestfall:

```text
SOC 10 %
Soll +2.397 W
rückgelesenes inputLimit +2.397 W
Ist 0 W
→ COMMAND_MISMATCH_CONFIRMED
→ Full-State-Resync bleibt möglich
```

---

## 8. Measurement- und Config-Vertrag

Additive V4-Felder:

```text
charge_acceptance_state
charge_acceptance_reason
command_effect_reference_w
```

Semantik:

- `charge_acceptance_state`: `ok`, `suspect`, `limited`, `not_accepting`
- `charge_acceptance_reason`: konkrete Diagnosebegründung
- `command_effect_reference_w`: für die Wirkungsbewertung verwendeter bestätigter Command-Referenzwert

Zusätzlich:

```text
COMMAND_EFFECT_TOLERANCE_PERCENT
```

in:

- `CONTROL_SNAPSHOT_KEYS`
- Config-Control-Hash
- `zec_config_snapshots.json`
- Manifest-Reproduzierbarkeit

Ältere RC13-Dateien bleiben unverändert; RC14 startet eine neue V4-Datei.

---

## 9. Intended-Delta-Tests

1. Produktivfall 16:26:59:
   ```text
   SOC 98, Soll 1.449, Readback 1.400, Ist/Batterie 125,
   Standort-Netz -60, acceptance=limited
   → COMMAND_CHARGE_ACCEPTANCE_LIMITED
   → kein Mismatch
   ```

2. Produktivfall 16:29:02:
   ```text
   SOC 98, Soll 1.112, Readback 1.172, Ist/Batterie 74,
   Standort-Netz +16, acceptance=limited
   → COMMAND_CHARGE_ACCEPTANCE_LIMITED
   → kein Resync
   ```

3. Produktivfall 16:31:14:
   ```text
   SOC 100, Soll/Readback 1.532, Ist/Batterie 0,
   Observation NEUTRAL, acceptance=not_accepting
   → nach kurzer Bestätigung Acceptance limited
   → kein Resync
   ```

4. Gesamte Produktivepisode 16:25:28–16:31:35:
   - keine Full-State-Resyncs;
   - finale Safe-State-Neutralisierung unverändert.

5. Niedrig-SOC-Nichtwirkung:
   ```text
   SOC 10, Soll/Readback 2.397, Ist 0
   → Mismatch und Recovery unverändert
   ```

6. Falscher AC-Modus:
   - keine Acceptance-Reklassifikation;
   - Command-State-Recovery bleibt aktiv.

7. Gegenlimit ungleich 0:
   - keine Acceptance-Reklassifikation.

8. Power-Konflikt:
   - `COMMAND_TELEMETRY_UNCERTAIN`, nicht Acceptance limited.

9. Dynamische Solländerungen:
   - Readback-Lag verhindert Acceptance nicht, solange statische Invarianten und aktives bestätigtes Limit ausreichen.

10. Config-Snapshot:
    - Änderung der Prozenttoleranz ändert Config-Control-Hash;
    - Snapshot enthält den Wert.

11. V4:
    - neue Felder im Header;
    - Headerrotation RC13→RC14;
    - Replay-/Analysekompatibilität.

---

## 10. No-Regression

Unverändert:

- Flash-Schutz und Command-State-Gate;
- Neutralization-Dedupe;
- Publish-Event-ID/Epoch;
- NIGHT_DISCHARGE;
- MIN-/MAX-SOC-Zielwertlogik;
- AUTO-, HOLD- und feste Modi;
- Cross-Charge-Zielwertlogik;
- sämtliche Harvest-Formeln;
- Geräte-Caps und Offgrid-Konfiguration read-only;
- echte Niedrig-SOC-Recovery;
- finale Excel-Lernsimulation.

---

## 11. Abnahmekriterien

RC14 gilt buildseitig als bestanden, wenn:

1. die aufgezeichnete RC13-Taper-Episode keinen Mismatch und keinen Resync mehr erzeugt;
2. echte Niedrig-SOC-Nichtwirkung unverändert erkannt und recoveryfähig bleibt;
3. kein aktives Kommando ohne Flash-Schutz möglich ist;
4. Neutralization-Dedupe unverändert grün bleibt;
5. Ladeannahmezustand und Referenzwert in V4 reproduzierbar sind;
6. die relative Trackingtoleranz im Config-Hash/Snapshot enthalten ist;
7. keine Regler-Zielwertformel geändert wurde;
8. alle bestehenden und neuen Tests grün sind.

Produktiv folgt danach erneut ein Ladeendtest. Der Nacht-/MIN-SOC-Test kann parallel bereits mit RC13 durchgeführt und separat bewertet werden.
