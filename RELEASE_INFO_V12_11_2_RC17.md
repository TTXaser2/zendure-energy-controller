# Release Information V12.11.2-RC17

## 1. Releaseziel

RC17 implementiert ausschließlich die freigegebene Harvest-Revision mit strategischer Parallel-Allokation und verbindlichem 0-W-Netzziel.

Die vorhandene High-SOC-Strategie bleibt erhalten: Zendure darf bei gleichzeitigem Laden bewusst SMA-Leistung verdrängen. Neu ist die harte Invariante, dass Share, Floor oder Zeitprofil keinen technisch aufnehmbaren Export mehr stehen lassen dürfen.

## 2. Fachliche Änderungen

- `SMA_NEAR_LIMIT`: physisches Absolutziel `C + E`;
- `HIGH_SMA_SOC`: `max(Zendure-Share-Ziel, C + E)`;
- `HIGH_SMA_SOC_SMA_NEAR_LIMIT`: identische Max-Verknüpfung, Near-Limit-Capture als harte Untergrenze;
- `SMA_FULL_OR_IDLE`: `C + E` ohne Profilreserve;
- SMA-Share auf `SECOND_BATTERY_MAX_CHARGE_POWER_W` gekappt;
- Profilreserve 250/150/100/typisch 300 W aus allen Zielwertformeln entfernt;
- `HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W` bleibt ausschließlich Entry-/Rauschschwelle;
- alle absoluten Harvest-Zweige verwenden dieselbe unabhängige Zendure-AC-Netzportreferenz;
- unsichere Referenz führt in allen Branches in den klar diagnostizierten inkrementellen AUTO-Fallback;
- Latch-Recovery verwendet branchengerechte Absolutsemantik statt nacktem Restexport;
- Command-Path-Steuerbarkeit wird diagnostiziert, aber nicht als zweites Gate implementiert.

## 3. Erhaltene Strategien und Schutzschichten

Unverändert:

- Entry, Reason-Priorität, Hysterese, Hold und Exit;
- Zeitfenster und Share-Prozente;
- Floor, Restart und Near-Limit-Schwellen;
- AUTO außerhalb Harvest, DEADBAND, NIGHT, STOP und feste Modi;
- Cross-Charge, MAX-/MIN-SOC und Gerätecaps;
- RC14-Acceptance/Taper;
- RC15-Publish-/Readback-Trennung und Late-Effect-Guard;
- Command-State-Gate und Flash-Schutz;
- Offgrid-Semantik und lokale API;
- Config und Excel-Lernsimulation.

Kein neuer Timer, kein Langzeitausfallmodus und keine aktive SMA-Steuerung.

## 4. Measurement V4

Zehn additive RC17-Felder machen Netz-Ziel, gesamtes Ladeangebot, strategische Aufteilung, Export-Capture, Auswahl und Command-Path-Diagnose reproduzierbar.

```text
RC17 Standardheader: 238 Felder
RC16 rekonstruiert:  228 Felder
RC15 rekonstruiert:  217 Felder
RC14 rekonstruiert:  203 Felder
```

Headerrotation: vorhandene ältere Datei bleibt unverändert; Fortsetzung in `schema_rc17`.

## 5. Tests

Neu:

```text
tests/test_v12_11_2_rc17_harvest_zero_grid_target.py
tests/fixtures/rc17_harvest_branch_matrix.json
```

Die neuen Differentialtests decken unter anderem ab:

- Near-Limit `C + E`;
- Strategic Share gewinnt;
- Export-Capture gewinnt;
- kombinierter Near-Limit-Zweig;
- SMA-Max-Kappung;
- Full/Idle ohne Reserve;
- frische Neutralreferenz;
- unsichere Referenz ohne Sollwert-Istverwechslung;
- Command-Path nur als Diagnose;
- Hold ohne Origin-Reason;
- konservierte `PRIMARY_BAND_LIMIT`-Stay-Semantik;
- alle Zeitprofile mit 0 W operationaler Reserve;
- RC16→RC17-Headerrotation.

## 6. Buildvalidierung

Die finalen Zahlen und die SHA256-Prüfsumme stehen im externen `RELEASE_MANIFEST_V12_11_2_RC17.md`.

Bekannte Python-3.13-`ResourceWarning`-Hinweise älterer SQLite-Tests bleiben bestehen; sie verursachen keinen Testfehler.

## 7. Installation

```bash
cd /home/pi/Downloads
sha256sum -c zendure_controller_v12_11_2_rc17.zip.sha256
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc17
```

## 8. Produktivstatus

Build- und Regressionstestvalidiert. Die produktive Freigabe erfolgt branchenspezifisch anhand natürlicher Harvest-Episoden; ein positiver Zielwert oder Publish allein ist kein Funktionsnachweis.
