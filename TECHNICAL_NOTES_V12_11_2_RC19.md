# Technical Notes – V12.11.2-RC19

## 1. Exakte Statussemantik

Technische Pfade werden in normalisierte `->`-Tokens zerlegt. Dadurch gelten nur exakte Tokens wie `CHARGE_CONTROL`, `DISCHARGE_CONTROL`, `STOP_HOLD` oder `REST_SURPLUS_HARVEST`.

Insbesondere ist künftig ausgeschlossen:

```text
DISCHARGE enthält als Zeichenfolge CHARGE
STOP_HOLD enthält als Zeichenfolge HOLD
```

Diese sprachliche Überlappung darf weder öffentliche Reason-Texte noch Diagnoseflags bestimmen.

## 2. Zentrale Kapazitäts-Housekeeping-Phase

`zendure_remaining_capacity_kwh` und die korrespondierenden Primärspeicher-/Share-Werte werden in `update_cycle_display_metrics()` auf jedem Zykluspfad aktualisiert. Das gilt auch für:

```text
SAFE_STATE
STOP_HOLD
NIGHT_DISCHARGE
MANUAL_FIXED_CHARGE
MANUAL_FIXED_DISCHARGE
AUTO/HOLD
```

Die ViewModel-Erzeugung berechnet die Zendure-Restkapazität zusätzlich read-only aus aktuellem SOC, Max-SOC und Kapazität, damit ein älterer Statewert nicht sichtbar fortgeführt wird.

## 3. Feste Modi: Requested vs. Applied

Die Command-Pipeline bleibt alleinige Begrenzungsstelle. RC19 speichert danach diagnostisch:

```text
target_raw_w                 = angeforderter manueller Festwert
target_after_power_limit_w   = nach Config- und read-only Gerätecap
target_final_w               = tatsächlich angewandter signed Zielwert
```

Limitergründe:

```text
CONFIG_MAX_CHARGE_POWER
CONFIG_MAX_DISCHARGE_POWER
ZENDURE_DEVICE_CHARGE_MAX_LIMIT
ZENDURE_DEVICE_INVERSE_MAX_POWER
```

Der MQTT-Befehl ist gegenüber RC18 unverändert. Nur die zuvor verlorene Rohziel-/Cap-Semantik bleibt erhalten und wird in Status und Measurement korrekt sichtbar.

Die ETA eines festen Modus verwendet das wirksame Ziel. Ein angeforderter 2.400-W-Entladefall mit 2.000-W-Gerätecap wird daher mit 2.000 W prognostiziert.

## 4. Local-API-Darstellung

Standardansicht in „Controller & Schnittstellen“:

- Local-API-Nutzung und aktive Quelle;
- Workerzustand und letzter Erfolg;
- letzter asynchroner HTTP-Request;
- synchrone Snapshotübernahme.

Info-Popover/Experteninhalt:

- Modus `Fallback-only`, aktive Quelle, Diagnose oder deaktiviert;
- letzter Versuch und letzter Erfolg;
- Snapshot valid/stale;
- Request-/Apply-Dauer;
- Fehlerfolge, Backoff und Fehlercode;
- aktive Zendure-Telemetriequelle.

Der HTTP-Request bleibt ausdrücklich außerhalb des synchronen Regelzyklus.

## 5. Ready-Check

Das Update-Skript wartet bis zu 90 Sekunden und akzeptiert Erfolg nur, wenn `/ready` valides JSON mit exakt:

```json
{"ready": true}
```

liefert. Ein erreichbarer Endpoint mit `ready=false` gilt nicht mehr als erfolgreicher Ready-Check.

## 6. No-Regression

Unverändert bleiben insbesondere:

- RC17-Harvest-0-W-Netzziel;
- RC18-Async-Local-API-Worker;
- feste Lade-/Entladebefehle und Gerätecaps;
- RC15 Publish-/Readback-Trennung und Late-Effect-Guard;
- NIGHT_DISCHARGE;
- Cross-Charge;
- Measurement-V4-Header;
- Configschema und produktive Werte;
- Storage-Lifecycle;
- Excel-Lernsimulation.
