# Technical Notes – V12.11.2-RC18

## 1. Workerarchitektur

`ZendureLocalApiWorker` ist allein für HTTP, Timeout, Backoff und Parsing zuständig. Er hält keine Queue, sondern ersetzt atomar genau einen `ZendureLocalApiSnapshot`.

Der Worker darf weder `ControllerState` schreiben noch MQTT publizieren oder Modi/Recovery auslösen. Der Hauptthread übernimmt einen neuen erfolgreichen Snapshot höchstens einmal.

## 2. Snapshotidentitäten

```text
snapshot_sequence     steigt bei jedem veröffentlichten Workerzustand
success_sequence      steigt nur bei erfolgreichem Parse
data_config_generation kennzeichnet die zugehörige Configgeneration
```

Ein Fehler überschreibt den letzten erfolgreichen Datensnapshot nicht. Ein Ergebnis einer veralteten Configgeneration wird als `SUPERSEDED_CONFIG` verworfen.

## 3. Freshness

```text
stale_after = max(30 s, 3 × Pollintervall)
```

Versuchszeit, Erfolgszeit und Backoff verwenden monotone Zeit. Wall-Clock-Zeit dient Anzeige und Logging.

API-Daten werden mit dem tatsächlichen Erfolgszeitpunkt in State übernommen; ein späterer Apply-Zyklus darf alte Daten nicht künstlich auffrischen.

## 4. Lifecycle

- Workerstart vor Controller-Hauptschleife;
- Configreload aktualisiert einen immutable Configsnapshot;
- IP-Wechsel erneuert die Worker-Session;
- Shutdown setzt ein Stop-Event und verwendet begrenzten Join;
- ein noch blockierter Request verlängert nicht den Regelzyklus.

## 5. Timing

```text
zendure_local_api_request_duration_ms   asynchron, außerhalb Regelzyklus
zendure_local_api_snapshot_apply_ms     synchron, nur Snapshotübernahme
```

Der alte Timing-Key `zendure_local_api_ms` bleibt ausschließlich für historische Datendarstellung lesbar.

## 6. Runtime-Events

Mindestens:

```text
local_api_worker_started
local_api_worker_stopped
local_api_config_generation_changed
local_api_attempt_completed
local_api_snapshot_applied
local_api_snapshot_discarded_generation_mismatch
local_api_backoff_entered
local_api_backoff_left
local_api_parse_warning
local_api_worker_error
```

## 7. Measurement-Zielpipeline

`target_limited_w` bildet ab RC18 die numerische Power-Cap-Stufe ab. Die Flags für Power-Limit, Smoothing und Step-Limit werden aus den tatsächlichen Stufendifferenzen abgeleitet.

Die Diagnoseänderung beeinflusst weder `target_final_w` noch MQTT-Publishes.

## 8. Fixed Modes

Die seit RC15 implementierte Publish-/Readback-Trennung und der Late-Effect-Guard werden unverändert übernommen. Der Codefix bleibt regressionstestvalidiert; der kontrollierte produktive End-to-End-Test für `FIXED_DISCHARGE` ist weiterhin offen.
