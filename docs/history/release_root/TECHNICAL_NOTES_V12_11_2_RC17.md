# Technical Notes V12.11.2-RC17

## 1. Mathematisches Zielmodell

```text
E = max(0, -control_grid_power_w)
C = unabhängig beobachtete positive Zendure-AC-Ladung
S = positive SMA-Ladung
T = S + C + E
```

### Export-Capture

```text
Z_export_capture = C + E
```

Diese Größe ist in jedem Harvest-Ladezweig die harte Untergrenze. Sie verhindert, dass eine Speicheraufteilung absichtlich nutzbaren Export erzeugt.

### Strategischer Share

```text
S_profile = profile_share × T
S_required = min(SMA_max, max(SMA_floor, S_profile))
Z_share = max(0, T - S_required)
```

Für die High-SOC-Branches:

```text
Z_target = max(Z_share, Z_export_capture)
```

Damit kann Zendure SMA-Ladeleistung weiterhin gezielt verdrängen, ohne den Netzexport zu erhöhen.

## 2. Branch-Matrix

```text
SMA_NEAR_LIMIT                  -> C + E
HIGH_SMA_SOC                    -> max(Z_share, C + E)
HIGH_SMA_SOC_SMA_NEAR_LIMIT     -> max(Z_share, C + E)
SMA_FULL_OR_IDLE                -> C + E
EXPORT_HOLD ohne Origin-Reason  -> C + E
```

Bei unsicherer physischer Referenz:

```text
last_input_power + CONTROL_GAIN × effective_export_power
```

Der Fallback ist inkrementell und wird nicht als physisch bestätigtes Absolutziel ausgegeben.

## 3. Profilrollen

Zeitprofile behalten unverändert:

```text
09:30–11:30  SMA-Share 60 %  Entry 60 s
11:30–14:30  SMA-Share 50 %  Entry 30 s
14:30–18:00  SMA-Share 35 %  Entry 15 s
sonst         SMA-Share 50 %  konfigurierte Entry-Zeit
```

Die frühere operationale Exportreserve ist in allen Profilen 0 W. `HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W` bleibt ausschließlich Entry-/Rauschschwelle.

## 4. Physische Referenz

Gültige positive Referenz:

```text
zendure_power_observation_direction = CHARGE
zendure_power_observation_confidence = HIGH
zendure_power_observation_signed_w > 0
Alter <= 15 s
kein CONFLICT
```

Gültige Neutralreferenz:

```text
direction = NEUTRAL
confidence = MEDIUM
beide expliziten AC-Richtungstopics frisch
```

Unzulässig:

```text
last_input_power
Desired Target
inputLimit-Readback
Command-Intent / Sollrichtung
outputPackPower / packInputPower
gridOffPower
Headunit-PV-Leistung
SMA-Leistung
```

## 5. Hold-/Stay-Vertrag

RC17 konserviert den RC16-Iststand vollständig. `HARVEST_HIGH_SMA_SOC_HOLD_SECONDS` ist weiterhin keine zwingende maximale Stay-Dauer. Nach Ablauf kann der vorherige Origin-Reason unter `PRIMARY_BAND_LIMIT` aktiv bleiben.

Diese Semantik ist ausdrücklich durch Differentialtests geschützt und wird nicht beiläufig „bereinigt“.

## 6. Command-Pipeline

RC17 berechnet den Desired-State weiter, auch wenn die Steuerbarkeit noch nicht bestätigt ist. Die bestehende Pipeline bleibt alleinige Freigabeschicht:

```text
smartMode=1 frisch
Command-State vollständig
acMode/Gegenlimit konsistent
Flash-Schutz
Publish-Deduplizierung
Command-Effect
Mismatch/Resync
Late-Effect-Guard
```

`harvest_command_path_eligible` und `harvest_command_path_block_reason` sind reine Diagnosefelder. Sie blockieren keine Zielrechnung und ersetzen keine Recovery-Logik.

## 7. Nachgeschaltete Pipeline

Unverändert:

```text
MAX_CHARGE_POWER_W
read-only chargeMaxLimit
MAX_SOC_PERCENT
RC14 Acceptance/Taper
Smoothing
MAX_POWER_STEP_W
MIN_COMMAND_CHANGE_W
symmetrischer Cross-Charge-Schutz
Command-State-Gate
Flash-Schutz
RC15 Publish-Deduplizierung
Command-Effect/Recovery
Late-Effect-Guard
```

## 8. Measurement-V4-Semantik

```text
harvest_network_target_w              = 0 W
harvest_total_available_charge_w      = T
harvest_primary_share_target_w        = SMA-Ziel nach Floor und Max-Kappung
harvest_zendure_share_target_w        = T - SMA-Ziel
harvest_export_capture_target_w       = C + E
harvest_target_selected_by            = STRATEGIC_SHARE / EXPORT_CAPTURE / BOTH_EQUAL / FALLBACK
harvest_calculation_branch            = tatsächlich verwendeter Rechenzweig
harvest_entry_min_export_w            = Entry-Schwelle, kein Netz-Ziel
harvest_command_path_eligible         = reine Steuerbarkeitsdiagnose
harvest_command_path_block_reason     = bestehender Gate-/Freshness-Grund
```

Bestehende Felder:

```text
harvest_profile_reserve_w = 0.0
harvest_candidate_delta_w = E
harvest_candidate_absolute_w = C + E bei gültiger Referenz, sonst 0
harvest_candidate_raw_w = ausgewähltes Branch-Rohziel
harvest_primary_share_reserve_w = profile_share × T vor Floor/Max-Kappung
harvest_primary_required_w = SMA-Share-Ziel nach Floor/Max-Kappung
```

## 9. Hardwareschonung

RC17 führt nicht ein:

- zusätzliche `acMode`-Wechsel;
- 0-W-Zwischenphasen innerhalb derselben Laderichtung;
- neue Lade-/Entladerichtungswechsel;
- Same-State-Publish-Schleifen;
- persistente Geräteschreibvorgänge;
- zyklusbasierte Timer;
- zusätzliche Neutralisierungsschleifen.

Die höhere Energieaufnahme ist nur bei echtem PV-Überschuss oder beabsichtigter gleichgerichteter SMA-Verdrängung zulässig.
