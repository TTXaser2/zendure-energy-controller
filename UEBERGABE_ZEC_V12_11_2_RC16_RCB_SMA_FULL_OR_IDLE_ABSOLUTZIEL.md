# Übergabe Zendure Energy Controller – V12.11.2-RC16
## RC-B: `SMA_FULL_OR_IDLE` als absolutes Ladeziel

**Stand:** 30.07.2026  
**Basis:** V12.11.2-RC15  
**Normative Grundlagen:** `ZEC_ANALYSE_REGELWERK_V1.1.md`, `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md`, finale RC16-Spezifikation

## 1. Anlass

Produktiv wurde nachgewiesen, dass `SMA_FULL_OR_IDLE` den nach bereits laufender Zendure-Ladung verbleibenden Netzexport als absolutes Ziel interpretiert. In 3.920 stabilen Zyklen lag das Ziel in 77,9 % mindestens 200 W zu niedrig; der Median der konservativen Unterallokation betrug 288,7 W.

## 2. RC16-Invariante

```text
absolutes Ladeziel
= unabhängig beobachtete Zendure-AC-Ladung
+ verbleibender Netzexport
- aktive Profilreserve
```

Die physische Referenz stammt ausschließlich vom Zendure-Netzport. Sollwerte, Command-Readback, Pack-, Offgrid-, PV- und SMA-Werte dürfen die Referenz nicht ersetzen.

## 3. Fallback

Bei stale, fehlender, unbekannter, konfliktbehafteter, entladender oder zeitlich inkohärenter Referenz verwendet RC16 den bestehenden inkrementellen AUTO-Exportregler. Der Fallback ist explizit diagnostiziert und gilt nicht als physisch bestätigtes Absolutziel.

## 4. Neue Diagnosefelder

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

## 5. Unverändert

- Harvest Entry/Hold/Exit und andere Harvest-Gründe;
- AUTO außerhalb `SMA_FULL_OR_IDLE`;
- NIGHT und feste Modi;
- Cross-Charge;
- RC14-Taper;
- RC15-Command-Safety und Hardwareschonung;
- Offgrid und lokale API;
- Config-Schema und Excel-Lernsimulation.

## 6. Produktivtestpflichten

Nach Installation zunächst Version, Dienste, Flash-Schutz, Command-State, RC15-Guard und RC16-Felder prüfen.

Die fachliche Freigabe benötigt eine natürliche `SMA_FULL_OR_IDLE`-Episode. Je Zyklus ist nachzuweisen:

```text
harvest_candidate_absolute_w
≈ harvest_reference_charge_w
 + rest_surplus_export_w
 - harvest_profile_reserve_w
```

Anschließend getrennt prüfen:

- Zielwertpipeline und Geräte-Readback;
- tatsächliche AC-Ladeleistung und SOC-/Energiebilanz;
- Konvergenz des Restexports zur Profilreserve;
- keine Command-Nichtwirkung oder Same-State-Publish-Serie;
- keine zusätzlichen `acMode`-, 0-W- oder physischen Richtungswechsel.

Bevorzugte Datenbasis: mindestens zwei natürliche Episoden oder mindestens 30 Minuten auswertbare Gesamtdauer.

## 7. Produktive Zielgrenzen

Für ausreichend stationäre, nicht gecappte, nicht getaperte und nicht Cross-Charge-limitierte Episoden:

```text
Median |Restexport - Profilreserve|
<= max(DEADBAND_W, 100 W)

p95
<= max(2 × DEADBAND_W, 200 W)
```

Dynamische Wolken-/Lastphasen werden separat als nicht stationär klassifiziert.

## 8. No-Regression

Insbesondere müssen unverändert grün bleiben:

- Nachtmodus und Reserve-SOC;
- feste Lade-/Entlademodi;
- symmetrischer Cross-Charge-Schutz;
- Flash-Schutz und Command-State-Gate;
- Neutralization-Dedupe;
- RC14-Acceptance/Taper;
- RC15-Publish-/Readback-Trennung und Late-Effect-Guard;
- Offgrid-Trennung;
- `inverseMaxPower` read-only;
- Excel bitidentisch.

## 9. Weiterer Entwicklungsweg

```text
RC16 installieren
→ natürliche SMA_FULL_OR_IDLE-Episode erfassen
→ branchenspezifische Produktivabnahme
→ erst danach RC-C asynchrone lokale Zendure-API
→ anschließend Settings-Redesign
```

Keine Folgeversion oder Scope-Erweiterung ohne ausdrückliche Freigabe.
