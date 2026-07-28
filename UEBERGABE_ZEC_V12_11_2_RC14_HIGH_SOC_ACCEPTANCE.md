# Übergabe Zendure Energy Controller – V12.11.2-RC14
## High-SOC-Ladeannahme-Nachkorrektur und reproduzierbarer Diagnosevertrag

**Stand:** 28.07.2026  
**Basis:** V12.11.2-RC13  
**Normative Analysegrundlage:** `ZEC_ANALYSE_REGELWERK_V1.1.md`

## 1. Anlass

RC13 bestand produktiv Flash-Schutz, Publish-Vertrag, Neutralization-Dedupe, Nachtbetrieb und Nacht-Exit. Die reale Ladeendphase blieb jedoch fehlerhaft:

- natürliche Ladeannahmereduktion wurde als Command-Mismatch behandelt;
- zwei Full-State-Resyncs hatten keine Wirkung;
- bei 100 % SOC und 0 W Ladeannahme blieb die Kategorie Mismatch;
- Ladeannahmezustand und Referenzwert fehlten in Measurement V4;
- `COMMAND_EFFECT_TOLERANCE_PERCENT` fehlte im Config-Hash/Snapshot.

## 2. RC14-Invarianten

- Kein nicht neutrales Limit ohne frisch bestätigtes `smartMode=1`.
- High-SOC-Reklassifikation nur bei vollständigem statischem Ladevertrag.
- Keine Sollrichtung als Beweis physischer Istleistung.
- Rückgelesenes aktives `inputLimit` ist die bestätigte Command-Referenz.
- Begrenzte Ladeannahme bestätigt weder exaktes Tracking noch das Netz-Systemziel.
- Niedrig-SOC-Nichtwirkung bleibt mismatch- und recoveryfähig.
- Keine Änderung einer Regler-Zielwertformel.

## 3. Neue Diagnosefelder

```text
charge_acceptance_state
charge_acceptance_reason
command_effect_reference_w
```

## 4. Produktive RC13-Nachtvalidierung vor Build

Bestanden:

```text
NIGHT_DISCHARGE 21:30–05:30
Soll −400 W / Median Ist −399 W
genau ein Nullbatch am Exit
0/0-Readback nach ca. 3,2 s
physische 0 W nach ca. 6,3 s
kein Nullspam
keine ungeschützten Leistungsbefehle
kein Mismatch/Resync
```

Offen bleiben als spätere Produktivnachweise:

- Nachtreserve-Exit bei 35 %,
- globale MIN_SOC-Episode,
- echter Geräte-/Broker-Reconnect,
- Offgrid-Test.

## 5. RC14-Abnahme

Buildseitig erfüllt:

- reale 124-Zyklen-Taper-Fixture ohne Mismatch und Resync;
- beide 98-%-Produktivanker als `COMMAND_CHARGE_ACCEPTANCE_LIMITED`;
- 100-%-/0-W-Fall nach 3 Zyklen und 6 s als `HIGH_SOC_NOT_ACCEPTING`;
- Niedrig-SOC-0-W-Fall bleibt recoveryfähig;
- falscher AC-Modus/Gegenlimit verhindern Reklassifikation;
- neue V4-Felder vorhanden;
- RC13→RC14-Headerrotation;
- relative Toleranz verändert Config-Control-Hash;
- alle 419 Tests grün.

Produktiv folgt nach Installation erneut ein Ladeendtest.

## 6. No-Regression

Unverändert bleiben:

- AUTO-, NIGHT-, feste Modi und Deadband-Zielwerte;
- Cross-Charge-Zielwertlogik;
- alle Harvest-Formeln einschließlich HIGH_SMA_SOC;
- Flash-Schutz und Command-State-Gate;
- Neutralization-Dedupe und Publish-Event-Vertrag;
- Gerätecaps und Offgrid-Konfiguration read-only;
- finale Excel-Lernsimulation.

## 7. Weiterer Entwicklungsweg

Nach produktiver RC14-Ladeendvalidierung:

```text
RC-B – SMA_FULL_OR_IDLE-Absolutziel
→ produktive Konvergenz-/Energieprüfung
→ RC-C – asynchrone lokale Zendure-API
→ anschließend Settings-Redesign
```

Keine Folgeversion und keine weitere Codeänderung ohne ausdrückliche Freigabe.
