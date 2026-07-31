# Übergabe Zendure Energy Controller – V12.11.2-RC18
## RC-C: asynchrone lokale API und Measurement-Zielpipeline

**Stand:** 31.07.2026  
**Basis:** finales V12.11.2-RC17-ZIP  
**Status:** Build- und Regressionstestvalidierung; Produktivabnahme ausstehend

## 1. Ziel

RC18 entfernt den synchronen HTTP-Aufruf der lokalen Zendure-API aus dem Regelpfad. Der Controller liest nur einen immutable Latest-Snapshot. Zusätzlich wird der in der RC17-Produktivanalyse nachgewiesene Power-Cap-Diagnosefehler korrigiert.

## 2. Architektur

```text
ZendureLocalApiWorker
  → HTTP /properties/report
  → Timeout / Backoff / Parsing
  → immutable Latest-Snapshot

Controller-Hauptthread
  → O(1)-Read
  → Apply höchstens einmal pro success_sequence
  → bestehende MQTT/API-Priorität
  → kein Netzwerk-Warten
```

## 3. No-Regression

Unverändert bleiben:

- sämtliche RC17-Harvest-Ziele;
- AUTO, HOLD, NIGHT und feste Modi;
- Cross-Charge;
- Command-State-Gate, Publish-Dedupe und Resync;
- Late-Effect-Guard und Neutralisierung;
- Flash-Schutz und read-only Gerätecaps;
- Offgrid;
- Configschema/-werte;
- Storage-Lifecycle;
- Excel.

## 4. V4-Vertrag

```text
RC18 Standard 246
RC18 Extended 249
RC17 Standard 238 / Hash 192ccc890c2e1d80 bleibt reproduzierbar
```

Die acht zyklischen Felder entsprechen dem finalen RC18-Feldbudget. Worker-Fehler-/Backoffdetails werden eventbasiert geführt.

## 5. Zielpipeline-Erratum

```text
target_raw_w
→ target_limited_w = Power-Cap-Stufe
→ target_filtered_w
→ target_step_limited_w
→ target_final_w
```

Numerische Flags ersetzen die unvollständige Ableitung allein aus Reasons/Limitern.

## 6. Produktivabnahme

- 24-h-Timingvergleich RC17/RC18;
- absichtlich oder natürlich langsame API-Requests ohne Slow-Cycle-Korrelation;
- MQTT-frisch/API-frisch: MQTT bleibt primär;
- MQTT-stale/API-frisch: Fallback wie bisher;
- Fehler/Backoff ohne Datenverlust oder Controlfehler;
- keine zusätzlichen Commands, Resyncs oder Hardwarewechsel;
- NIGHT und natürliche Harvest-Episoden no-regression;
- V4-Power-Cap-Flag an realen gekappten Zeilen prüfen.

## 7. Offene Punkte

- Storage-Härtung bleibt eigener späterer Releaseblock.
- Fixed-Discharge-Codefix ist implementiert/testvalidiert, produktiver kontrollierter Nachweis bleibt offen.
- Seltene RC17-Harvest-Branches bleiben nach natürlichem Auftreten weiter abzudecken.
