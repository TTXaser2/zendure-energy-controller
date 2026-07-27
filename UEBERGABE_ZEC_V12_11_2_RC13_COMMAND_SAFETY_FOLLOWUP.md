# Übergabe Zendure Energy Controller – V12.11.2-RC13
## Command-State-Gate, Neutralization-Dedupe, Taper und Publish-Vertrag

**Stand:** 27.07.2026  
**Basis:** V12.11.2-RC12  
**Normative Analysegrundlage:** `ZEC_ANALYSE_REGELWERK_V1.1.md`

## 1. Anlass

Der RC12-Morgenzyklus bestätigte Flash-Schutz und korrekte Power-Semantik, zeigte aber drei Fehler:

1. zyklusweise vollständige Nullbatches in stabilen Neutralisierungszuständen;
2. Umgehung des 30-s-Gates durch wechselnde VERIFY/APPLY-Signaturen;
3. falsche Mismatch-/Resync-Serien während natürlicher Ladeannahmereduktion.

## 2. RC13-Invarianten

- Kein nicht neutrales Limit ohne frisch bestätigtes `smartMode=1`.
- Safety-Neutralisierung bei unsicherem State höchstens einmal je Retry-Fenster.
- Nach bestätigter 0-W-Wirkung kein weiterer Publish innerhalb derselben physischen Episode.
- Reason-Wechsel bei identischem 0/0-Zustand ist nur Diagnoseänderung.
- Exakte Zielwertänderungen derselben Richtung beeinflussen das Gate-Retry-Fenster nicht.
- Full-State-Resync und physische Recovery bleiben getrennt.
- Offgrid-Last bleibt von netzseitiger Command-Wirkung getrennt.

## 3. Neue Diagnosefelder

```text
command_publish_event_id
command_publish_epoch_s
command_state_gate_state
command_state_retry_remaining_s
command_neutralization_episode_id
```

## 4. Produktivtestpflichten

- längere MIN-/MAX-SOC-Episode ohne zyklusweise Nullbatches;
- Reconnect: erst Smart-Mode-Rücklesung, dann aktiver Full-State;
- wechselnde Wolkenziele ohne Gate-Umgehung;
- Ladeendphase ohne periodische False-Positive-Resyncs;
- echte Nichtwirkung bei niedrigem SOC bleibt recoveryfähig;
- Nacht-/Cross-Charge-Neutralisierung bleibt physisch wirksam;
- später separater Offgrid-Test.

## 5. No-Regression

Unverändert bleiben müssen:

- AUTO-, NIGHT-, feste Modi und Deadband-Zielwerte;
- Cross-Charge-Zielwertlogik;
- alle Harvest-Formeln einschließlich HIGH_SMA_SOC;
- Gerätecaps und Offgrid-Konfiguration read-only;
- finale Excel-Lernsimulation.

## 6. Weiterer Entwicklungsplan

Erst nach RC13-Produktivvalidierung folgt RC-B mit der bekannten `SMA_FULL_OR_IDLE`-Korrektur:

```text
absolute charge target
≈ current Zendure charge + remaining export − profile reserve
```

Danach separat die asynchrone Entkopplung der lokalen Zendure-API.
