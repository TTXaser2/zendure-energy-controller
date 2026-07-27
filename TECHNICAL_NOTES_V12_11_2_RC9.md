# Technische Hinweise V12.11.2-RC9

## 1. Release-Ziel

RC9 korrigiert verbliebene UI-Semantik und Diagnoseaussagen aus der produktiven RC8-Sichtung und ergänzt gezielte Regressionstests. Die Regelstrategie bleibt unverändert.

## 2. Replay-Erreichbarkeit

Die bisherige Prüfung lud die vollständige Replay-Startseite mit einem Timeout von 0,75 Sekunden. Die Startseite enumeriert CSV-Dateien und kann auf dem Raspberry Pi länger benötigen, obwohl der Dienst vollständig erreichbar ist.

RC9 prüft daher:

```text
http://127.0.0.1:<REPLAY_WEB_PORT>/health
```

Anforderungen:

- HTTP-Erfolg,
- gültiges JSON,
- `status == "ok"`.

Positive Ergebnisse werden 30 Sekunden, negative nur 5 Sekunden gecacht. Dadurch wird ein kurz nach dem Controller gestarteter Replay-Dienst zeitnah erkannt. Die Prüfung erfolgt ausschließlich im Webpfad.

## 3. Optionale Zendure-Local-API-Phase

`update_zendure_telemetry_from_local_api()` wird pro Controllerzyklus aufgerufen, führt wegen Pollintervall oder Backoff jedoch häufig keinen HTTP-Poll aus. RC8 stellte die kurze No-op-Laufzeit als `0,0 ms` dar.

RC9 vergleicht diagnostisch `ZendureLocalApiClient.last_poll_epoch` vor und nach dem Aufruf. Nur wenn `fetch_report()` tatsächlich einen Pollversuch startete, bleibt `zendure_local_api_ms` in den Zykluszeiten erhalten. Bei übersprungenem Polling:

```text
Zendure Local API    nicht ausgeführt
```

Diese Änderung beeinflusst weder Pollingentscheidung noch API-Fehlerbehandlung.

## 4. Timing-Hierarchie

Freigegebene Reihenfolge:

```text
Aktiver Gesamtdurchlauf
ohne Wartezeit / Sleep
├─ synchrone Teilphasen
└─ synchrone Teilphasen
Zyklusabstand … · aktive Arbeit …
[Zeitverteilungsbalken]
Asynchrone Hintergrundarbeit
```

Nicht ausgeführte optionale Phasen bleiben im Linienbaum sichtbar, werden aber nicht in den Zeitverteilungsbalken oder dessen Prozentbasis aufgenommen.

## 5. Ereignisfooter

Der Footer priorisiert:

1. offene Störung,
2. offene Warnung,
3. offene Hinweise,
4. optionale technische Einschränkungen,
5. keine offene Betriebsstörung.

Eine optionale lokale API oder ein optionaler Replay-Dienst kann dadurch als technische Einschränkung sichtbar werden, ohne fälschlich eine offene Betriebsstörung zu behaupten.

## 6. Betriebsmodus-Regression

Der produktive Code wurde nicht geändert. Neue Tests sichern ab:

- `MANUAL_FIXED_DISCHARGE` erreicht Ziel-SOC, Folgeaktion `AUTO`, Nachtfenster aktiv und Reserve nicht erreicht → Abschlusszyklus `STOP_HOLD`, danach `NIGHT_DISCHARGE`.
- Nachtreserve bereits erreicht → AUTO-Regelpfad innerhalb des Nachtfensters, keine feste Nachtentladung.
- Nachtfenster inaktiv → AUTO-Regelpfad.
- Folgeaktion `STOP_HOLD` → STOP/HOLD bleibt aktiv.

## 7. Sicherheitsbewertung

- keine neue Steuerzustandsvariable,
- keine Änderung an AUTO/NIGHT/FIXED/Harvest/Cross-Charge/Safe-State,
- keine neue MQTT-Sendung,
- keine Unterdrückung notwendiger Sendungen,
- keine DB-/Datei-/Netzwerkoperation zusätzlich im Reglerpfad,
- kein neues Latch und keine Prioritätsumkehr.
