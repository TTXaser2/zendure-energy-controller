# Technical Notes V12.10.0-RC2

V12.10.0-RC2 ist eine gezielte Nacharbeit zu RC1. V4-Logging bleibt aktiv, V3 bleibt als Legacy-/Rollback-Pfad verfügbar. Die AUTO-Regelstrategie, Nachtmodus-Logik, Cross-Charge-Strategie, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

## Änderungen gegenüber RC1

- Replay-/Analyse-Webdienst erkennt V4-Dateien und zeigt für V4 eine eigene Konsistenz-/Preflight-Prüfung statt den V3-Validator auf V4 anzuwenden.
- UI-Texte des Analyse-Webdienstes sprechen nicht mehr ausschließlich von `ZEC-MEASUREMENT-V3`.
- V4-Manifest: `created_time_utc` bleibt beim Aktualisieren eines bestehenden Eintrags stabil.
- V4-Manifest: Zeilenzähler/letzte Epoch werden nach dem CSV-Schreiben und Flush aktualisiert, damit Manifest und sichtbare CSV enger konsistent bleiben.
- V4-Builder: bekannte SOC-Limiter-Fälle werden nicht mehr pauschal als `SAFE_STATE`-Reason protokolliert; `MAX_SOC_LIMIT`/`MIN_SOC_LIMIT` werden bevorzugt abgebildet.
- V4-Builder: `command_suppressed_reason` verwendet `NO_CHANGE` für wiederholte/effektiv unveränderte Kommandos statt pauschal `UNKNOWN`.
- V4-Builder: `control_grid_power_w` und `control_effective_export_w` bekommen zusätzliche Fallbacks auf vorhandene V3-Feldnamen.
- V4-Builder: `SECOND_BATTERY_POWER` wird nur als missing-required gezählt, wenn die Zweitbatterie im aktuellen Kontext wirklich eine Pflichtquelle ist.
- Config-Snapshot ergänzt `CROSS_CHARGE_SIGNIFICANT_W` aus dem bestehenden Legacy-Wert `SMA_DISCHARGE_BLOCK_W`, wenn der neue Key noch nicht in der Config existiert.

## Tests

`python -m unittest discover -q` muss erfolgreich laufen.
