# Übergabe Zendure Energy Controller – V12.11.2-RC17
## Harvest-Revision: strategische Parallel-Allokation mit 0-W-Netzziel

**Stand:** 30.07.2026  
**Basis:** finales V12.11.2-RC16-ZIP  
**Normative Grundlage:** `SPEZIFIKATION_ZEC_V12_11_2_RC17_HARVEST_0W_NETZZIEL_FINAL.md`

## 1. Anlass

RC16 korrigierte den Delta-/Absolutwertfehler in `SMA_FULL_OR_IDLE`, ließ aber weiterhin eine zeitprofilabhängige Exportreserve stehen. In den High-SOC-Branches konnte außerdem das strategische Share-Ziel die vollständige Restexportaufnahme unterschreiten; ein Sollwert konnte bei fehlender positiver Istleistung in die Charge-Pressure-Rechnung eingehen.

## 2. RC17-Invarianten

```text
Netz-Ziel = 0 W
absichtlicher Exportbias = 0 W
Parallel-Harvest bleibt erhalten
strategische SMA-Verdrängung bleibt erlaubt
Export-Capture ist harte Untergrenze
```

Formeln:

```text
SMA_NEAR_LIMIT              -> C + E
HIGH_SMA_SOC                -> max(Z_share, C + E)
HIGH_SMA_SOC_SMA_NEAR_LIMIT -> max(Z_share, C + E)
SMA_FULL_OR_IDLE            -> C + E
```

## 3. Nicht verändert

- Harvest Entry, Hysterese, Reason-Priorität, Hold und Exit;
- Share-Zeitfenster und Entry-Zeiten;
- Floor, Restart und Near-Limit-Schwellen;
- AUTO außerhalb Harvest, NIGHT und feste Modi;
- Cross-Charge, MAX-/MIN-SOC und Taper;
- Command-Safety, Publish-/Readback-Trennung und Late-Effect-Guard;
- lokale API, Offgrid, Config und Excel.

## 4. Measurement V4

```text
RC17 Standardheader: 238 Felder
RC16 Standardheader: 228 Felder
Rotation: schema_rc17
```

Zehn neue Felder trennen Netz-Ziel, Ladeangebot, SMA-/Zendure-Share, Export-Capture, Auswahl und Command-Path-Diagnose.

## 5. Buildabnahme

- vollständige Python-, JavaScript-, Shell- und JSON-Syntaxprüfung;
- gesamter Unit-Testbestand einschließlich neuer Branch-Matrix;
- RC16→RC17-Headerrotation;
- Excel bitidentisch;
- keine `config.json`, Credentials, Logs, SQLite- oder Pycache-Artefakte;
- geschützte Command-/Cross-Charge-/API-/Config-Dateien byteidentisch zu RC16.

Die exakten finalen Zahlen stehen im externen Release-Manifest.

## 6. Produktivabnahme

Branches getrennt anhand natürlicher Episoden prüfen:

```text
SMA_NEAR_LIMIT
HIGH_SMA_SOC
HIGH_SMA_SOC_SMA_NEAR_LIMIT
SMA_FULL_OR_IDLE
Hold, sobald natürlich vorhanden
```

Pflicht: Rechnung, Limiter, Readback, physische Leistung, SOC-/Energiebilanz, 0-W-Konvergenz, Recovery und Hardwareschonung.

## 7. Weiterer Entwicklungsweg

```text
RC17 installieren
→ unmittelbaren Sicherheits-/Statuscheck durchführen
→ natürliche Harvest-Episoden branchenspezifisch abnehmen
→ parallel RC-C vollständig spezifizieren
→ RC-C in eigenem Folge-Release umsetzen
→ anschließend Settings-Redesign fortsetzen
```
