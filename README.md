# Zendure Energy Controller V12.11.2-RC19

V12.11.2-RC19 ist ein eng abgegrenzter **Status- und Diagnose-Stabilisierungsrelease** auf Basis des finalen RC18-Stands.

## 1. RC19-Korrekturen

### Exakte Modus- und Pfadsemantik

Unsichere Teilstringprüfungen wurden durch exakte Tokens ersetzt:

```text
CHARGE     → Einspeisung wird reduziert
DISCHARGE  → Netzbezug wird reduziert
STOP_HOLD  → Manueller Stopp – Zendure bleibt neutral
```

Damit kann `DISCHARGE` nicht mehr wegen des enthaltenen Wortteils `CHARGE` als Ladepfad erscheinen und `STOP_HOLD` nicht mehr als normaler Deadband-HOLD.

### Kapazitätsdiagnose in allen Modi

Die Restkapazität bis Max-SOC wird in einer zentralen Housekeeping-Phase auf jedem Zykluspfad aktualisiert. Das gilt auch für SAFE_STATE, STOP_HOLD, NIGHT und feste Modi.

### Requested vs. Applied in festen Modi

Die Statusseite trennt bei `MANUAL_FIXED_CHARGE` und `MANUAL_FIXED_DISCHARGE`:

```text
Angefordert
Wirksames Ziel
Config-/Gerätebegrenzung
```

Die ETA verwendet das wirksame, bereits gecappte Ziel. Read-only Zendure-Gerätecaps werden weiterhin nicht verändert.

### Local-API-Worker sichtbar

„Controller & Schnittstellen“ zeigt nun:

- API-Nutzungsart und aktive Quelle;
- Workerzustand und letzten Erfolg;
- asynchrone HTTP-Dauer;
- synchrone Snapshotübernahme;
- Details zu Versuch, Snapshot, Fehlerfolge, Backoff und Fehlercode im Info-Popover.

### Installer-Ready-Check

Der Installer wartet bis zu 90 Sekunden auf valides JSON mit `ready=true`. Ein lediglich erreichbarer Endpoint mit `ready=false` gilt nicht mehr als erfolgreicher Abschluss.

## 2. RC18-Basis: asynchrone lokale Zendure-API

Der HTTP-Aufruf `/properties/report` läuft weiterhin in genau einem Hintergrundworker. Der Regelzyklus liest nur einen immutable Latest-Snapshot und wartet nicht auf Netzwerk-I/O.

Quellenpriorität:

```text
MQTT frisch
→ MQTT bleibt primäre SOC-/Leistungsquelle

MQTT stale/fehlend + API-Fallback aktiv + API-Snapshot frisch
→ lokale API darf als Fallback übernehmen

beide Quellen stale/fehlend
→ bestehende Freshness-/Safe-State-Logik
```

## 3. Measurement V4

RC19 erweitert das Schema nicht:

```text
Standard: 246 Felder · Hash 7842bfef39d47f93
Extended: 249 Felder · Hash 8f61d07e66428a6e
```

Die RC18-Zielpipeline-Diagnose bleibt erhalten:

```text
target_raw_w
→ target_limited_w
→ target_filtered_w
→ target_step_limited_w
→ target_final_w
```

## 4. Unverändert

RC19 verändert nicht:

- AUTO-, HOLD-, NIGHT-, STOP- oder feste Command-Algorithmen;
- RC17-Harvest-Formeln und 0-W-Netzziel;
- Cross-Charge;
- Command-Lifecycle, Resync und Late-Effect-Guard;
- Neutralisierung und Publish-Deduplizierung;
- Smart-Mode-/Flash-Schutz;
- Offgrid-Semantik und read-only Gerätecaps;
- produktive Configwerte oder Defaults;
- Storage-Retention/Kompression;
- Excel-Lernsimulation.

## 5. Dokumentation

```text
RELEASE_INFO_V12_11_2_RC19.md
TECHNICAL_NOTES_V12_11_2_RC19.md
UEBERGABE_ZEC_V12_11_2_RC19_STATUS_DIAGNOSE_STABILISIERUNG.md
BUILD_VALIDATION_V12_11_2_RC19.md
```

Die RC18-Spezifikationen und Errata bleiben als normative Vorgeschichte im Paket erhalten. Installation und unmittelbare Verifikation: `README_INSTALLATION.md`.
