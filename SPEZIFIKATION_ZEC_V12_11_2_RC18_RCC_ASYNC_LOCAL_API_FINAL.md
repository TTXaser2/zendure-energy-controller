# Spezifikation ZEC V12.11.2-RC18 – RC-C asynchrone lokale Zendure-API

**Dokumentstatus:** finaler Build-, Differentialtest- und Produktivabnahmevertrag; keine Implementierung  
**Stand:** 31.07.2026  
**Zielversion:** V12.11.2-RC18  
**Entwicklungsblock:** RC-C  
**Arbeitsname:** Async Local API Latest-Snapshot  
**Verbindliche Codebasis:** finales unverändertes V12.11.2-RC17-ZIP  
**RC17-ZIP SHA256:** `0a5def2f8df824e52ea648ee087e7667435555a98d8821db3d8a7e4872161602`  
**Status der Folgeversion:** nicht gebaut; keine Buildfreigabe durch dieses Dokument

---

## 1. Executive Summary

Die lokale Zendure-API `/properties/report` wird in RC17 synchron innerhalb des zeitkritischen Regelzyklus aufgerufen. Produktivmessungen früherer Releases belegen Antwortzeiten von typischerweise etwa 2–3 Sekunden und dadurch verzögerte Regelzyklen. RC-C verschiebt ausschließlich Netzwerk-I/O, HTTP-Timeout, Backoff und Parsing in genau einen Hintergrundworker.

Zielbild:

```text
ZendureLocalApiWorker – ein Daemon-Hintergrundthread
  ├─ monotone Pollplanung
  ├─ genau eine requests.Session
  ├─ GET /properties/report
  ├─ Timeout, Fehler-Backoff, Parsing
  └─ genau ein unveränderlicher Latest-Snapshot
                         ↓
Controller-Hauptthread
  ├─ atomarer Snapshot-Read O(1)
  ├─ neuen Snapshot höchstens einmal anwenden
  ├─ bestehende MQTT/API-Quellenpriorität beibehalten
  └─ niemals auf Netzwerk oder Worker warten
```

RC-C ist eine Architektur- und Timingänderung. Es ist ausdrücklich **keine** Änderung von:

- AUTO-, HOLD-, NIGHT-, Fixed- oder Harvest-Zielwerten;
- RC17-Harvest-Formeln und 0-W-Netzziel;
- Cross-Charge;
- Command-Lifecycle, Resync, Late-Effect-Guard oder Neutralisierung;
- Flash-/Smart-Mode-Schutz;
- Offgrid-Semantik;
- Gerätecaps;
- produktiven Configwerten;
- Excel-Lernsimulation.

---

## 2. Verbindliche Ausgangslage in RC17

### 2.1 Aktueller synchroner Pfad

`controller_logic.py` führt zu Beginn jedes Regelzyklus aus:

```text
_timed_local_api_phase(cfg)
  → update_zendure_telemetry_from_local_api(cfg)
    → ZendureLocalApiClient.should_poll(cfg)
    → ZendureLocalApiClient.fetch_report(cfg)
      → requests.Session.get(...)
```

Der HTTP-Aufruf liegt damit vor manuellen Modi, NIGHT und AUTO im selben Hauptthread. Ein langsamer Request verzögert sämtliche nachfolgenden Regelentscheidungen dieses Zyklus.

### 2.2 Bestehende lokale API-Funktionen

Der RC17-Client besitzt bereits:

- read-only GET auf `/properties/report`;
- Pollintervall;
- effektiven Timeoutdeckel;
- Fehler-Backoff;
- eine persistente `requests.Session`;
- Temperatur-Normalisierung.

Der Controller übernimmt aus erfolgreicher Antwort:

- SOC aus `properties.electricLevel` beziehungsweise `packData[0].socLevel`;
- Headunit-/Netz-/Pack-Leistungsrohwerte;
- Batterie-/Packmetriken und Temperaturen;
- Command-/Konfigurations-Readback:
  - `smartMode`
  - `acMode`
  - `inputLimit`
  - `outputLimit`
  - `inverseMaxPower`
  - `chargeMaxLimit`
  - `gridOffMode`

### 2.3 Bestehende Quellenpriorität

Diese Semantik bleibt unverändert:

```text
MQTT frisch
→ MQTT bleibt primäre aktive SOC-/Leistungsquelle

MQTT stale/fehlend + API-Fallback aktiviert + API frisch
→ lokale API darf aktive SOC-/Leistungsquelle werden

beide Quellen stale/fehlend
→ bestehende Freshness-/Safe-State-Logik
```

Command-/Konfigurations-Readback aus der lokalen API ist unabhängig von `TELEMETRY_FALLBACK_ONLY` weiterhin zulässig, wie in RC17.

---

## 3. Intended Delta

RC18 darf fachlich nur folgende Änderungen enthalten:

1. neue Worker-/Snapshot-Architektur in `zendure_local_api.py`;
2. Worker-Lifecycle in `ZendureController.py` und `controller_logic.py`;
3. synchrone Snapshot-Anwendung statt synchronem HTTP-Aufruf;
4. additive Worker-/Freshness-/Timingdiagnose in State, Measurement und UI;
5. neue Tests und Release-/Technikdokumentation;
6. notwendige V4-Schemarotation wegen additiver Felder.

Jede weitere fachliche Änderung ist Scope-Erweiterung und vor Build gesondert freizugeben.

---

## 4. Verbindliche Architektur

### 4.1 Verantwortungsgrenzen

#### `ZendureLocalApiWorker`

Der Worker ist ausschließlich verantwortlich für:

- Pollplanung;
- HTTP-Kommunikation;
- HTTP-/JSON-Fehlerklassifikation;
- Parsing und Normalisierung;
- Backoff;
- Bildung und atomare Veröffentlichung des Latest-Snapshots;
- eigene Lifecycle-Diagnose.

Der Worker darf niemals:

- `ControllerState` direkt ändern;
- MQTT publizieren;
- Geräteeinstellungen schreiben;
- Zielwerte berechnen;
- Modi wechseln;
- Safe-State oder Resync auslösen;
- Configdateien schreiben;
- eine unbeschränkte Queue oder Historie halten.

#### Controller-Hauptthread

Nur der bestehende Controller-Hauptthread darf:

- einen neuen Snapshot in `ControllerState` übernehmen;
- MQTT/API-Quellenpriorität entscheiden;
- aktive SOC-/Power-Fallbacks anwenden;
- Command-Readback aktualisieren;
- Batterie-/Temperaturmetriken aktualisieren;
- Limiter setzen;
- daraus resultierende bestehende Control-Freshness verwenden.

Damit bleibt die Reihenfolge aller regelungsrelevanten State-Änderungen deterministisch.

### 4.2 Threadmodell

```text
Hauptprozess
├─ Paho-MQTT-Loop
├─ Controller-Hauptschleife
├─ Uvicorn-Webserver
├─ SMA-Energy-Meter-Client
└─ ZendureLocalApiWorker – genau ein zusätzlicher Daemon-Thread
```

Es darf weder pro Request noch pro Configänderung ein neuer Thread erzeugt werden.

### 4.3 Kein Queue-Modell

Zulässig ist genau ein Latest-Snapshot:

```text
_worker_snapshot = immutable snapshot
```

Ein neuer Snapshot ersetzt atomar den alten. Es gibt:

- keine Requestqueue;
- keine Resultqueue;
- keine wachsende Historie;
- keine Futuresammlung;
- keinen Threadpool.

Langsame oder ältere Ergebnisse dürfen niemals nach einem neueren Configstand als gültige Daten veröffentlicht werden.

---

## 5. Unveränderliche Datentypen

### 5.1 Relevante Worker-Config

In `zendure_local_api.py` ist eine `@dataclass(frozen=True)` vorzusehen, beispielsweise:

```python
ZendureLocalApiConfigSnapshot
```

Verbindliche Inhalte:

```text
generation
use_for_telemetry
local_ip
poll_interval_s
configured_timeout_s
effective_timeout_s
error_backoff_s
soc_priority
fallback_only
device_id
```

Nur diese relevante Configsicht wird an den Worker übergeben. Keine veränderliche globale Config-Map wird zwischen Threads geteilt.

### 5.2 Normalisierte erfolgreiche Nutzdaten

Ein erfolgreicher Parse erzeugt unveränderliche, bereits normalisierte Daten:

```text
electric_level
pack_soc_level
selected_api_soc
pack_input_power_w
output_home_power_w
grid_input_power_w
output_pack_power_w
grid_off_power_w
solar_input_power_w
smart_mode
ac_mode
input_limit_w
output_limit_w
inverse_max_power_w
charge_max_limit_w
grid_off_mode
headunit_temperature
pack_metrics als tuple unveränderlicher Pack-Snapshots
parse_warnings als begrenztes tuple
```

Der rohe JSON-Response wird nach dem Parsing nicht im Worker-Snapshot gehalten.

### 5.3 Worker-Latest-Snapshot

Verbindlich ist ein `@dataclass(frozen=True)`, das Versuch und letzten Erfolg getrennt abbildet:

```text
snapshot_sequence                 erhöht sich bei neuem Workerzustand/Versuch
data_success_sequence             erhöht sich nur bei neuem erfolgreichem Parse
config_generation
worker_state                      DISABLED / IDLE / REQUESTING / BACKOFF / STOPPING / STOPPED
latest_attempt_ok
last_attempt_wall_epoch
last_attempt_monotonic
last_success_wall_epoch
last_success_monotonic
request_duration_ms
consecutive_error_count
backoff_until_monotonic
latest_error_code
latest_error_text
successful_data                   letzter erfolgreicher Datensatz oder None
```

Ein fehlgeschlagener Versuch aktualisiert Fehler-/Attemptdiagnose, zerstört aber `successful_data` und dessen Success-Zeitpunkt nicht.

---

## 6. Poll-, Timeout- und Backoff-Vertrag

### 6.1 Monotone Planung

Pollintervall, Backoff und Freshness werden intern ausschließlich über `time.monotonic()` beziehungsweise `time.monotonic_ns()` bestimmt.

Wall-Clock-Zeit wird nur für Anzeige, Logs und V4-Zeitbezug gespeichert.

### 6.2 Pollintervall

Unverändert gilt:

```text
Intervall = max(1 s, ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS)
```

Der nächste Polltermin wird aus monotoner Zeit berechnet. Der Worker driftet nach einem langen Request nicht in eine sofortige Requestserie.

Verbindlich:

```text
next_poll = Ende des letzten Versuchs + Pollintervall
```

Bei Fehlerbackoff:

```text
next_poll = max(regulärer Polltermin, backoff_until)
```

### 6.3 Timeout

Zur Semantik- und Lastkompatibilität bleibt der bestehende effektive Timeout erhalten:

```text
effective_timeout = max(
    0,2 s,
    min(
        ZENDURE_LOCAL_API_TIMEOUT_SECONDS,
        ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS
    )
)
```

Der historisch benannte `CONTROL_TIMEOUT_CAP` begrenzt in RC18 den Hintergrundrequest. Es wird kein neuer Config-Key eingeführt.

### 6.4 Fehlerbackoff

Nach jedem Request-, HTTP- oder JSON-Fehler:

```text
consecutive_error_count += 1
backoff_until = now_monotonic + ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS
```

Bei Erfolg:

```text
consecutive_error_count = 0
backoff_until = None
```

Keine exponentielle oder zusätzliche Backoff-Logik wird in RC18 eingeführt.

### 6.5 Disable-/IP-Leerzustand

Wenn `USE_FOR_TELEMETRY=false` oder `ZENDURE_LOCAL_IP` leer ist:

- Worker bleibt als einzelner Thread vorhanden, aber `DISABLED`/dormant;
- keine HTTP-Requests;
- kein unmittelbares Löschen bestehender Controllerwerte;
- zuvor angewandte API-Daten altern nach bestehender Freshness aus;
- kein neuer Safe-State nur durch das Umschalten der Option.

---

## 7. Config-Reload und IP-Wechsel

### 7.1 Initialisierung

Beim Start:

1. Config laden;
2. Worker mit erster immutable Configsicht erzeugen;
3. Worker starten;
4. Controller-Hauptschleife startet ohne Warten auf ersten API-Snapshot.

### 7.2 Reload

Bei `ConfigManager.reload_if_needed()` und tatsächlicher Änderung:

```text
worker.update_config(new_frozen_config)
```

Der Austausch erfolgt atomar. Der Hauptthread wartet nicht auf einen laufenden Request.

### 7.3 Generation Guard

Jeder Request merkt sich die Configgeneration beim Start. Vor Veröffentlichung eines Erfolgs wird geprüft:

```text
request_generation == current_generation
```

Ist dies falsch, wird das Ergebnis als `SUPERSEDED_CONFIG` verworfen und nicht als erfolgreicher Datensatz veröffentlicht.

### 7.4 IP-Wechsel

Bei geänderter lokaler IP:

- laufender alter Request darf bis zum Timeout enden;
- dessen Ergebnis wird durch den Generation Guard verworfen;
- alte Session wird im Workerthread geschlossen;
- neue Session wird im Workerthread erzeugt;
- Backoff wird für die neue Zieladresse zurückgesetzt;
- kein gleichzeitiger Zugriff zweier Threads auf dieselbe Session.

---

## 8. Snapshot-Anwendung im Regelzyklus

### 8.1 Aufrufstelle

Der bisherige synchrone Block:

```text
_timed_local_api_phase(cfg)
```

wird ersetzt durch:

```text
_timed_local_api_snapshot_apply_phase(cfg)
```

Die Aufrufposition bleibt vor Display-Housekeeping und den bestehenden frühen Modusentscheidungen, damit erfolgreiche API-Telemetrie im selben Zyklus wie bisher nutzbar ist.

### 8.2 Atomarer Read

```python
snapshot = worker.latest_snapshot()
```

Der Read darf:

- höchstens einen sehr kurzen Lock für den Referenzaustausch verwenden;
- keine Kopie des Rohpayloads erzeugen;
- niemals auf Worker oder Netzwerk warten.

### 8.3 Apply-once

Der Controller hält mindestens:

```text
_last_seen_local_api_snapshot_sequence
_last_applied_local_api_success_sequence
```

Regeln:

- neue Attempt-/Fehlerdiagnose wird je `snapshot_sequence` höchstens einmal übernommen;
- erfolgreiche Telemetrie wird je `data_success_sequence` höchstens einmal angewandt;
- wiederholte Regelzyklen dürfen denselben API-Erfolg nicht erneut als frisches Update verbuchen;
- ein Fehler nach einem Erfolg darf den alten Erfolg nicht erneut anwenden.

### 8.4 Zeitstempel

Bei erfolgreicher Anwendung werden bestehende API-/SOC-/Power-Zeitfelder auf den **Erfolgszeitpunkt des Requests**, nicht auf den späteren Apply-Zeitpunkt gesetzt.

Damit wird ein bereits älterer Snapshot nicht künstlich verjüngt.

### 8.5 Quellenpriorität

Die Entscheidung wird im Hauptthread zum Apply-Zeitpunkt mit dem aktuellen MQTT-Freshness-Zustand getroffen.

#### SOC

```text
api_soc vorhanden
UND
(fallback_only=false ODER MQTT-SOC aktuell stale/fehlend)
→ API-SOC aktiv anwenden
```

#### Power

```text
mindestens ein verwertbarer API-Powerrohwert vorhanden
UND
(fallback_only=false ODER Zendure-MQTT-Power aktuell stale/fehlend)
→ API-Power aktiv anwenden
```

#### Command-State

Vorhandene API-Command-Properties werden wie in RC17 unabhängig vom Telemetrie-Fallback aktualisiert.

### 8.6 Stale-Regel des Worker-Snapshots

Für die Verwendbarkeit eines erfolgreichen API-Datensatzes gilt:

```text
local_api_snapshot_stale_after_s = max(
    30 s,
    3 × ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS
)
```

Ein erfolgreicher Datensatz, dessen monotones Alter diese Grenze überschreitet, darf nicht neu als aktiver API-Fallback angewandt werden.

Die bestehende globale SOC-/Power-Freshness bleibt nach Anwendung unverändert zuständig. RC18 führt keinen neuen Safe-State-Timer ein.

---

## 9. Fehler- und Lifecycle-Semantik

### 9.1 Workerfehler

Ein Workerfehler:

- setzt keinen allgemeinen `ControllerState.last_error`;
- erhöht nicht `consecutive_errors` des Regelzyklus;
- löst keinen Safe-State unmittelbar aus;
- löst keinen MQTT-Resync aus;
- aktualisiert ausschließlich lokale API-Diagnose;
- lässt den letzten erfolgreichen Snapshot bis zu dessen natürlichem Stale-Zeitpunkt bestehen.

### 9.2 Startup

- Kein Warten auf API.
- Kein API-erzwungener Startup-Safe-State.
- MQTT-/bestehende Freshness entscheidet wie bisher.
- Ein erster API-Erfolg kann in einem späteren Zyklus angewandt werden.

### 9.3 Shutdown

`request_stop()` setzt zusätzlich das Worker-Stop-Event.

`close()`:

1. Worker-Stop anfordern;
2. begrenzter Join;
3. Worker schließt seine Session ausschließlich im Workerthread in `finally`;
4. bei Join-Timeout Warnung protokollieren;
5. Prozessbeendigung nicht unbegrenzt blockieren.

Der Workerthread ist als Daemon auszuführen. Der reguläre Join-Timeout beträgt:

```text
min(3,0 s, effective_timeout + 0,75 s)
```

mindestens jedoch 1,0 s.

### 9.4 Keine Request-Abbruchsimulation

Die `requests`-Bibliothek erhält keinen unsicheren externen Session-Close während eines laufenden Requests. Ein Request endet durch Erfolg oder seinen wirksamen Timeout.

---

## 10. Timing- und Diagnosevertrag

### 10.1 Regelzyklus

Der HTTP-Request gehört ab RC18 nicht mehr zu `cycle_total_without_sleep_ms`.

Neuer synchroner Timing-Key:

```text
zendure_local_api_snapshot_apply_ms
```

Er wird nur gesetzt, wenn tatsächlich eine neue Snapshot-/Attemptinformation verarbeitet wurde. Ein No-op-Read wird nicht als 0-ms-Phase ausgewiesen.

### 10.2 Asynchroner Request

Separat, nicht als Zyklusphase:

```text
zendure_local_api_request_duration_ms
```

Dieser Wert beschreibt den letzten abgeschlossenen Workerrequest und darf niemals in die Summe der synchronen Zyklusphasen eingehen.

### 10.3 Alter und Status

Status/API/UI müssen getrennt zeigen:

```text
Workerzustand
letzter Versuch
letzter Versuch erfolgreich ja/nein
letzter Erfolg
Alter letzter Erfolg
Snapshot gültig/stale
Requestdauer
Fehleranzahl in Folge
Backoff verbleibend
Fallback aktiv ja/nein
```

### 10.4 Bestehender Timing-Key

`zendure_local_api_ms` darf ab RC18 nicht mehr mit HTTP-Dauer befüllt werden.

In UI-/Analysekompatibilität ist er als historischer synchroner RC17-und-früher-Key zu kennzeichnen. RC18 verwendet ausschließlich:

```text
zendure_local_api_snapshot_apply_ms
zendure_local_api_request_duration_ms
```

---

## 11. Measurement-V4-Vertrag

### 11.1 Rotation

RC18 erzeugt bei Standard- und Extended-Logging eine neue Sitzung wegen additiver Felder:

```text
Rotation reason: schema_rc18
```

RC17-Dateien bleiben unverändert.

### 11.2 Neue Standardfelder

Verbindlich 16 additive Felder:

```text
zendure_local_api_worker_state
zendure_local_api_worker_config_generation
zendure_local_api_snapshot_sequence
zendure_local_api_success_sequence
zendure_local_api_new_success_applied
zendure_local_api_latest_attempt_ok
zendure_local_api_last_attempt_age_s
zendure_local_api_last_success_age_s
zendure_local_api_snapshot_valid
zendure_local_api_snapshot_stale
zendure_local_api_request_duration_ms
zendure_local_api_snapshot_apply_ms
zendure_local_api_consecutive_errors
zendure_local_api_backoff_remaining_s
zendure_local_api_latest_error_code
zendure_local_api_parse_warning_count
```

Erwartete Feldzahlen:

```text
RC17 Standard: 238
RC18 Standard: 254

RC17 Extended: 241
RC18 Extended: 257
```

Die finalen Header-Hashes werden erst aus dem gebauten Vertrag erzeugt und im Release-Manifest festgehalten.

### 11.3 Semantik

- `snapshot_sequence`: letzter im Hauptthread gesehener Workerzustand;
- `success_sequence`: letzter erfolgreicher Datensatz;
- `new_success_applied`: per-cycle `0/1`, nur im tatsächlichen Apply-Zyklus `1`;
- `latest_attempt_ok`: Erfolg des letzten abgeschlossenen Versuchs, nicht Gültigkeit alter Daten;
- `snapshot_valid`: letzter Erfolg vorhanden und Configgeneration passend;
- `snapshot_stale`: monotones Erfolgsalter oberhalb Stale-Grenze;
- Requestdauer und Applydauer sind strikt getrennt.

### 11.4 Config-Control-Hash

Die bestehenden lokalen API-Configkeys bleiben im Config-Control-Hash. Es kommen keine neuen Keys hinzu.

---

## 12. UI-/Statusvertrag

### 12.1 Statuskarte

Die bestehende Local-API-Karte wird aufgeteilt in:

```text
Nutzung: deaktiviert / Diagnose / Fallback-only / aktive Quelle
Worker: Zustand
Letzter Versuch: Zeitpunkt, Ergebnis, Dauer
Letzter Erfolg: Zeitpunkt, Alter, fresh/stale
Fehler: Code/Text, Fehleranzahl, Backoff
Aktive Control-Quelle: MQTT / lokale API / keine
```

### 12.2 Timingdarstellung

Die Timingansicht zeigt zwei fachlich getrennte Werte:

```text
Asynchroner HTTP-Request – nicht Bestandteil des Regelzyklus
Synchrones Snapshot-Apply – Bestandteil des Regelzyklus
```

Die asynchrone Requestdauer darf nicht als langsamste Regelzyklusphase gewertet werden.

### 12.3 Diagnose-Webendpoint

Der bestehende manuelle Web-Diagnoseendpoint `/zendure-properties` bleibt außerhalb RC-C:

- ein Benutzeraufruf darf weiterhin synchron innerhalb des HTTP-Requesthandlers abfragen;
- er blockiert nicht den Controller-Hauptthread;
- keine Wiederverwendung des Worker-Snapshots als Ersatz für einen bewusst angeforderten Live-Diagnoseabruf in RC18;
- keine Änderung seiner Berechtigungs-/Enable-Semantik.

### 12.4 Readiness-/historischer Fehlerbefund

Die bereits identifizierte grobe `/ready`-SAFE_STATE-Semantik und das historisch stehenbleibende allgemeine `last_error` sind **nicht** Bestandteil RC-C. Keine stille Nebenänderung.

---

## 13. Hardware- und Ressourcenschutz

### 13.1 Keine zusätzlichen Gerätekommandos

Der Worker ist read-only. Differentialtests müssen beweisen:

```text
lokale API Workeraktivität
→ 0 zusätzliche MQTT-Publishes
→ 0 zusätzliche acMode-Wechsel
→ 0 zusätzliche inputLimit-/outputLimit-Kommandos
→ 0 zusätzliche Neutralisierungen
→ 0 zusätzliche Resyncs
```

### 13.2 Keine zusätzlichen Energiezyklen

Die asynchrone Architektur darf keine Änderung der Zielwertfolge oder Richtungsfolge erzeugen. Bei identischer Eingabesequenz müssen RC17 und RC18 dieselben fachlichen Targets und Limiter erzeugen, abgesehen vom Zeitpunkt, zu dem ein API-Snapshot verfügbar wird.

### 13.3 Speichergrenze

Nach dauerhaftem Fehlerbetrieb darf Speicher nicht mit der Versuchszahl wachsen.

Verbindlich:

- genau ein Worker;
- genau ein Latest-Snapshot;
- genau ein letzter erfolgreicher Datensatz;
- Packtuple begrenzt auf die tatsächlich gemeldeten Packs, zusätzlich defensiv maximal 8 Einträge;
- Parsewarnungen defensiv maximal 16 Einträge;
- kein Rohpayload im Langzeitzustand;
- keine Queue.

### 13.4 CPU-/Lock-Vertrag

- kein Busy-Wait;
- Worker wartet über `StopEvent.wait(timeout)`;
- kein Lock über HTTP oder Parsing;
- Snapshot-Publish und Latest-Read nur als kurzer Referenzaustausch;
- `ControllerState.lock` nur während bestehender Apply-Operationen.

---

## 14. No-Regression-Vertrag

Gegenüber RC17 unverändert:

### 14.1 Regler

- SAFE_STATE;
- STOP_HOLD;
- MANUAL_FIXED_CHARGE;
- MANUAL_FIXED_DISCHARGE;
- NIGHT_DISCHARGE und Reserve-SOC;
- AUTO Import/Export;
- Deadband/HOLD;
- Ramp-Down und Richtungswechselvermeidung;
- MAX_SOC/MIN_SOC;
- Smoothing, Gain, Step, Mindeständerung.

### 14.2 Harvest

- Entry/Hold/Exit;
- `SMA_NEAR_LIMIT`;
- `HIGH_SMA_SOC`;
- `HIGH_SMA_SOC_SMA_NEAR_LIMIT`;
- `SMA_FULL_OR_IDLE`;
- `EXPORT_HOLD_EXPORT_CAPTURE`;
- `INCREMENTAL_FALLBACK`;
- RC17-0-W-Netzziel;
- alle RC17-Diagnosefelder.

### 14.3 Command-/Hardwarevertrag

- smartMode/Flash-Gate;
- Full-State-Command-Vertrag;
- Readback-Gate;
- Command-Effect-Kategorien;
- Neutralization-Watch;
- Late-Effect-Guard;
- Resync-Cooldown;
- Offgrid-Trennung;
- `inverseMaxPower` read-only;
- Cross-Charge.

### 14.4 Daten/UI

- bestehende V4-Felder unverändert;
- SQLite-/Graphstore;
- bestehende APIs außer additiver Diagnose;
- Config-Schema und Nutzerwerte;
- Excel-Lernsimulation bitidentisch.

---

## 15. Verbindliche Testmatrix

### 15.1 Worker-Unit-Tests

1. Disabled ohne IP: kein Request.
2. Disabled trotz IP: kein Request.
3. Pollintervall monotonic korrekt.
4. Erfolg erzeugt Success- und Snapshotsequenz.
5. HTTP-Fehler erhöht nur Snapshotsequenz, nicht Successsequenz.
6. JSON-Fehler dito.
7. Fehler behält letzten erfolgreichen Datensatz.
8. Erfolg setzt Fehlerzahl und Backoff zurück.
9. Backoff verhindert Requests bis monotone Frist abgelaufen ist.
10. Kein Busy-Wait während Disabled/Backoff.
11. Timeout entspricht bestehender Cap-Semantik.
12. Parsing aller bekannten Power-/SOC-/Commandfelder.
13. Temperatur-Normalisierung unverändert.
14. Pack- und Warnungsbegrenzung.
15. Kein Rohpayload im Snapshot.
16. Latest-only: 100.000 simulierte Erfolge erzeugen keine Historie.

### 15.2 Config-/Lifecycle-Tests

17. Start wartet nicht auf ersten Snapshot.
18. Configgeneration wird atomar übernommen.
19. IP-Wechsel verwirft altes verspätetes Ergebnis.
20. IP-Wechsel erneuert Session im Workerthread.
21. Disable während Request: Ergebnis wird nicht als aktive neue Generation publiziert.
22. Stop während Wait beendet zeitnah.
23. Stop während Request endet spätestens nach Timeout/Joinvertrag oder lässt nur Daemonrest zurück.
24. Session wird im Workerthread geschlossen.
25. Es existiert immer höchstens ein Workerthread.

### 15.3 Controller-Apply-Tests

26. No-op ohne neuen Snapshot.
27. Attemptdiagnose je Snapshotsequenz nur einmal.
28. erfolgreicher Datensatz je Successsequenz nur einmal.
29. Fehler nach Erfolg wendet alten Erfolg nicht erneut an.
30. Erfolg wird mit Success-Zeit, nicht Apply-Zeit gestempelt.
31. stale Snapshot wird nicht neu als Fallback angewandt.
32. MQTT frisch: API-SOC ohne aktive Control-Auswirkung.
33. MQTT stale + API frisch: bestehender SOC-Fallback.
34. MQTT-Power frisch: API-Power ohne aktive Control-Auswirkung.
35. MQTT-Power stale + API frisch: bestehender Power-Fallback.
36. beide stale: bestehende Safe-State-/Freshnessreaktion.
37. Command-State-Felder aus API weiterhin aktualisiert.
38. Teilantwort überschreibt nicht mit erfundenen Null-/None-Werten.
39. `ZENDURE_API_FALLBACK`-Limiter nur bei tatsächlichem Fallback.
40. Workerfehler verändert nicht allgemeinen Controllerfehlerzähler.

### 15.4 Timingtests

41. künstlicher 3-s-Request verlängert `run_once()` nicht.
42. künstlicher Timeout verlängert `run_once()` nicht.
43. Requestdauer erscheint nicht in `cycle_total_without_sleep_ms`.
44. Snapshot-Apply erscheint als eigene synchrone Phase.
45. UI stuft Requestdauer nicht als langsamste Regelzyklusphase ein.
46. 10.000 Snapshot-No-op-Zyklen ohne messbares Speicherwachstum.

### 15.5 Differential-/No-Regression-Tests

47. identische MQTT-only-Sequenz RC17 versus RC18: identische Targets, Modi, Limiter und Publishentscheidungen.
48. MQTT frisch plus parallel API frisch: identische Controlfolge wie RC17.
49. MQTT stale/API frisch: identische Fallbackwerte und Controlfolge wie RC17 ab Verfügbarkeit des Erfolgs.
50. lokale API dauerhaft fehlerhaft: identische Controlfolge wie RC17 ohne synchrones Timingdelta.
51. alle AUTO-/HOLD-/NIGHT-/Fixed-/Cross-Charge-/Harvest-Fixtures.
52. alle RC11–RC17 Command-/Effect-/Acceptance-/Harvesttests.
53. kein zusätzliches Publish, acMode, 0-W oder Richtungsereignis.
54. Excel-Datei bitidentisch.

### 15.6 Measurement/UI/Packaging

55. RC17→RC18-Headerrotation Standard 238→254.
56. Extended 241→257.
57. 16 neue Felder in Vertrag, CSV, Statussnapshot und JSON konsistent.
58. Request- und Apply-Timing nicht verwechselt.
59. alte RC17-Dateien bleiben lesbar.
60. Paket enthält keine `config.json`, Credentials, Logs, SQLite-Dateien, Pycache oder Testausgaben.

---

## 16. Buildabnahme

Vor Bereitstellung eines ZIPs verpflichtend:

```text
python3 -m py_compile *.py tools/*.py
node --check static/status_v2.js
bash -n tools/update_zendure_controller.sh
python3 -m unittest discover -s tests -q
```

Baseline RC17:

```text
466 Tests bestanden
```

RC18 muss:

- alle 466 bestehenden Tests unverändert grün halten;
- sämtliche neuen RC-C-Tests bestehen;
- exakte Testzahl im Release-Manifest nennen;
- Differentialtest RC17→RC18 dokumentieren;
- neues ZIP mit eindeutiger SHA256 liefern;
- keine stille Revision unter gleicher Versionskennung durchführen.

---

## 17. Produktivabnahme

### 17.1 Reihenfolge

```text
RC17-Harvest-Produktivabnahme ausreichend abgeschlossen
→ ausdrückliche Buildfreigabe RC18
→ RC18 bauen und vollständig testen
→ installieren
→ unmittelbarer Sicherheits-/Statuscheck
→ Timing-/Worker-Abnahme
→ mindestens ein vollständiger Tag No-Regression
→ finale RC18-Freigabe
```

RC18 wird nicht vor ausreichender natürlicher RC17-Harvest-Evidenz gebaut, sofern der Nutzer keine abweichende ausdrückliche Priorisierung freigibt.

### 17.2 Unmittelbarer Check

Nach Installation:

- Version RC18;
- Dienste aktiv;
- MQTT aktiv;
- Workerzustand plausibel;
- Command-State vollständig;
- Flash-Schutz aktiv;
- kein neuer Safe-State;
- kein ungeplanter Publish/Resync;
- V4 schema_rc18 und 254 Felder;
- API-Requestdauer getrennt von Apply-/Zyklusdauer.

### 17.3 Timingkriterien

Bei aktivierter lokaler API:

```text
zendure_local_api_snapshot_apply_ms
Median <= 1,0 ms
p99    <= 5,0 ms
```

Einzelne Betriebssystemspikes werden separat beurteilt. Verbindlich ist zusätzlich:

```text
kein Zyklus >1 s mit lokaler API Snapshot-Anwendung als Ursache
kein HTTP-Requestanteil in cycle_total_without_sleep_ms
```

Ein asynchroner Request darf 1–3 Sekunden dauern, ohne den Regelzyklus entsprechend zu verlängern.

### 17.4 Control-/Hardwarekriterien

Über mindestens einen vollständigen Tag:

- keine zusätzliche Publish-/Resync-Serie;
- keine zusätzlichen acMode-Wechsel;
- keine zusätzlichen physischen Richtungswechsel;
- keine zusätzlichen 0-W-Zwischenzustände;
- NIGHT/AUTO/HOLD unverändert plausibel;
- natürliche Harvest-Episoden weiterhin gemäß RC17;
- API-Fehler ändern nicht die Regelzyklusreaktionszeit;
- kein Speicherwachstum durch Workerhistorie.

### 17.5 Fallbacknachweis

Mindestens buildseitig verpflichtend und produktiv nur kontrolliert/read-only, ohne absichtliche Störung des Gesamtsystems:

```text
MQTT frisch → API ohne aktive Controlwirkung
MQTT stale + API frisch → Fallback
beide stale → bestehender Safe-State
```

Ein produktiver MQTT-Ausfall wird nicht nur für diesen Test provoziert.

---

## 18. Voraussichtlich geänderte Dateien

### 18.1 Fachlich erforderlich

```text
ZendureController.py
zendure_local_api.py
controller_logic.py
state.py
measurement.py
measurement_v4.py
measurement_v4_contract.py
status_page_v2.py
web_ui.py
static/status_v2.js
version.py
README.md
README_INSTALLATION.md
RELEASE_INFO_V12_11_2_RC18.md
TECHNICAL_NOTES_V12_11_2_RC18.md
UEBERGABE_ZEC_V12_11_2_RC18_RCC_ASYNC_LOCAL_API.md
SPEZIFIKATION_ZEC_V12_11_2_RC18_RCC_ASYNC_LOCAL_API_FINAL.md
```

### 18.2 Neue Tests

```text
tests/test_v12_11_2_rc18_async_local_api_worker.py
tests/test_v12_11_2_rc18_async_local_api_controller_apply.py
tests/test_v12_11_2_rc18_async_local_api_timing.py
tests/test_v12_11_2_rc18_async_local_api_measurement.py
```

Zusätzliche Fixtures nur, wenn für deterministische Timing-/Configgenerationstests erforderlich.

### 18.3 Nur falls technisch erforderlich

```text
operational_events.py
translations.py
```

### 18.4 Nicht vorgesehen

```text
config_manager.py
config.example.json
mqtt_bridge.py
command_lifecycle.py
zendure_power_observation.py
cross_charge.py
Excel-Lernsimulation
update_zendure_controller.sh
```

Sollte eine dieser Dateien außer Dokumentations-/Versionsreferenzen fachlich geändert werden müssen, ist dies vor Build als Scopeabweichung zu begründen und freizugeben.

---

## 19. Explizite Nicht-Ziele

RC18 implementiert nicht:

- neue lokale API-Endpunkte;
- lokale API-Schreibzugriffe;
- MQTT-Command-Acknowledgement;
- neuen Recoverymodus;
- neuen Langzeitausfallmodus;
- zusätzliche Controltimer;
- Queue-/Eventbus-Architektur;
- mehrere parallele API-Requests;
- Umbau der SMA-Energy-Meter-Architektur;
- Settings-Redesign;
- `/ready`-Semantikfix;
- Bereinigung des allgemeinen historischen `last_error`;
- Änderungen der RC17-Harvest-Strategie.

---

## 20. Release- und Migrationsvertrag

```text
Version: V12.11.2-RC18
Basis:   finales unverändertes V12.11.2-RC17-ZIP
```

Config:

- keine Migration;
- keine neuen Pflichtparameter;
- keine Änderung produktiver Werte;
- bestehende lokale API-Keys behalten ihre wirksame Funktion.

Measurement:

- neue `schema_rc18`-Datei;
- RC17-Dateien bleiben unverändert;
- neue Analysewerkzeuge müssen historische Schemata tolerieren.

Artefakte:

- RC17-ZIP wird nicht überschrieben;
- eindeutiges RC18-ZIP;
- SHA256-Datei zusätzlich zum bekannten Hash im Text;
- Installationsbefehle verwenden den exakten versionierten Dateinamen;
- keine Voraussetzung, eine separate `.sha256`-Datei auf den Pi zu kopieren;
- keine Befehlsfolge, die eine interaktive SSH-Sitzung bei einem Diagnosefehler unnötig beendet.

---

## 21. Entwicklungsreihenfolge

```text
RC17 produktiv unverändert weiterlaufen lassen
→ natürliche RC17-Harvest-Episoden mit vorbereitetem Auswerter erfassen
→ RC17 branchenspezifisch abnehmen
→ RC18-Spezifikation prüfen
→ ausdrückliche RC18-Buildfreigabe
→ RC18 auf finalem RC17-ZIP bauen
→ vollständige Differential-/No-Regression-Tests
→ ZIP, SHA256, Release-Manifest und Installation
→ produktive Timing-/Worker-/No-Regression-Abnahme
→ anschließend Settings-Redesign fortsetzen
```

Keine Codeänderung, kein Build und kein Deployment durch dieses Dokument.

---

## 22. Freigabestatus

```text
Architektur:              final spezifiziert
Intended Delta:           final abgegrenzt
No-Regression-Vertrag:    final
Testmatrix:               final
Produktivabnahme:         final
Buildfreigabe:            NICHT ERTEILT
Implementierung:          NICHT BEGONNEN
```
