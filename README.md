# Zendure Energy Controller V12.11.2-RC17

V12.11.2-RC17 implementiert die eng abgegrenzte **Harvest-Revision mit verbindlichem 0-W-Netzziel** auf Basis des finalen RC16-Stands.

## 1. Systemziel

Für alle Harvest-Ladezweige gilt:

```text
PV-Erzeugung
→ zuerst Hauslast
→ danach verfügbare Speicherladung
→ nur technisch nicht aufnehmbarer Rest ins Netz
```

```text
harvest_network_target_w = 0 W
intentional_export_bias_w = 0 W
```

Share, Floor, Zeitprofil und Entry-Schwellen dürfen keinen absichtlichen Restexport mehr erzeugen.

## 2. Parallel-Harvest bleibt erhalten

SMA bleibt Primärspeicher mit Vorrang, aber nicht mit Exklusivität. Ab dem bestehenden High-SOC-Eintritt darf Zendure weiterhin gezielt mehr als den momentanen Restexport übernehmen und dadurch SMA-Ladeleistung reduzieren, damit beide Speicher länger parallel Aufnahmeleistung für spätere PV-Spitzen bereitstellen.

Für `HIGH_SMA_SOC` und `HIGH_SMA_SOC_SMA_NEAR_LIMIT` gilt:

```text
Zendure-Ziel = max(
    strategisches Zendure-Share-Ziel,
    physisches Export-Capture-Ziel
)
```

Das Export-Capture-Ziel ist eine harte Untergrenze.

## 3. Zielwertformeln

```text
E = verbleibender Netzexport
C = unabhängig beobachtete Zendure-AC-Ladung
S = aktuelle positive SMA-Ladung
T = S + C + E
```

### SMA_NEAR_LIMIT

```text
Ziel = C + E
```

### HIGH_SMA_SOC / HIGH_SMA_SOC_SMA_NEAR_LIMIT

```text
SMA-Share-Ziel = min(
    SECOND_BATTERY_MAX_CHARGE_POWER_W,
    max(SMA-Floor, Profilanteil × T)
)

Zendure-Share-Ziel = T - SMA-Share-Ziel
Export-Capture      = C + E
Ziel                = max(Zendure-Share-Ziel, Export-Capture)
```

### SMA_FULL_OR_IDLE

```text
Ziel = C + E
```

Keine Profilreserve, kein SMA-Share und kein Floor-Abzug.

## 4. Physische Referenz und Fallback

Als physische Baseline ist ausschließlich die frische unabhängige Zendure-Netzportbeobachtung zulässig:

- `CHARGE` mit Confidence `HIGH` und positivem signed Wert;
- bestätigte `NEUTRAL`-Beobachtung mit Confidence `MEDIUM` und frischen expliziten AC-Richtungstopics.

Sollwert, `inputLimit`-Readback, Pack-, Offgrid-, PV- oder SMA-Leistung werden nicht als AC-Istleistung verwendet.

Bei stale, `UNKNOWN`, `CONFLICT`, `DISCHARGE`, fehlender Referenz oder unzulässigem Zeitversatz greift der bestehende inkrementelle AUTO-Exportregler. Der Fallback ist ausdrücklich als `INCREMENTAL_FALLBACK` diagnostiziert.

## 5. Unverändert

- Harvest Entry, Reason-Priorität, Hysterese, Hold und Exit;
- Zeitfenster, Share-Prozente, Floor, Restart und Near-Limit-Schwellen;
- normale AUTO-, DEADBAND-, NIGHT-, STOP- und feste Modi;
- symmetrischer Cross-Charge-Schutz;
- MAX-/MIN-SOC und RC14-Acceptance/Taper;
- RC15-Publish-/Readback-Trennung und Late-Effect-Guard;
- Command-State-Gate und Smart-Mode-/Flash-Schutz;
- lokale Zendure-API, Offgrid-Semantik und Gerätecaps;
- Config-Schema und Excel-Lernsimulation.

RC17 führt keine neuen Config-Keys, keinen neuen Timer und keinen Zendure-Langzeitausfall-Regelmodus ein.

## 6. Measurement V4

RC17 ergänzt zehn additive Standardfelder:

```text
harvest_network_target_w
harvest_total_available_charge_w
harvest_primary_share_target_w
harvest_zendure_share_target_w
harvest_export_capture_target_w
harvest_target_selected_by
harvest_calculation_branch
harvest_entry_min_export_w
harvest_command_path_eligible
harvest_command_path_block_reason
```

Der Standardheader umfasst 238 Felder. Ein RC16-Header mit 228 Feldern wird unverändert belassen; die Fortsetzung erfolgt in einer neuen Datei mit `schema_rc17` im Namen.

## 7. Dokumentation

```text
RELEASE_INFO_V12_11_2_RC17.md
TECHNICAL_NOTES_V12_11_2_RC17.md
UEBERGABE_ZEC_V12_11_2_RC17_HARVEST_0W_NETZZIEL.md
SPEZIFIKATION_ZEC_V12_11_2_RC17_HARVEST_0W_NETZZIEL_FINAL.md
```

Installation und unmittelbare Verifikation: `README_INSTALLATION.md`.
