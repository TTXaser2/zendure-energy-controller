# Technical Notes V12.11.0-RC6

V12.11.0-RC6 ist ein Hotfix-/Stabilisierungsrelease auf Basis von RC5. Der Live-Regelalgorithmus, Nachtmodus, Cross-Charge-Logik, Restüberschuss-Ernte, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

## Anlass

Nach RC5 wurden die SMA-Speedwire-Socketmodi im produktionsnahen Setup mit EVCC auf demselben Raspberry Pi systematisch getestet:

- EVCC ohne ZEC-SMA-Listener: stabil.
- `unimeter_like`: ZEC empfängt SMA-Pakete, EVCC meldet `login failed: no packet received in timeout` und `pv 1/2 ... outdated`.
- `reuseaddr_only`: ZEC empfängt SMA-Pakete, EVCC meldet wieder SMA-/PV-Timeouts.
- `rc3_compatible`: ZEC empfängt SMA-Pakete, EVCC meldet wieder SMA-/PV-Timeouts.
- `group_bind`: ZEC empfängt stabil und EVCC bleibt fehlerfrei.

Der anschließende Nachtlauf mit `group_bind` blieb über viele Stunden stabil: EVCC meldete keine SMA-/PV-Fehler, ZEC zeigte kontinuierliche SMA-Diagnosewerte mit ca. 120 Paketen/min, ausgewähltem Energy Meter und ohne große Paketlücken.

## Änderungen gegenüber RC5

- Default für `SMA_ENERGY_METER_SOCKET_MODE` von `rc3_compatible` auf `group_bind` geändert.
- `auto` und ungültige Socketmoduswerte fallen nun auf `group_bind` zurück.
- `config.example.json`, `DEFAULT_CONFIG`, State-Defaults, Validator-Default und UI-Fallback zeigen `group_bind` als Standard.
- Settings-Hilfetext markiert `group_bind` als empfohlenen EVCC-Koexistenzmodus.
- Wildcard-Bind-Modi auf `0.0.0.0:9522` bleiben verfügbar, sind aber als Experten-/Diagnoseoptionen beschrieben:
  - `rc3_compatible`
  - `reuseaddr_only`
  - `unimeter_like`
- Validator-Warnung für produktive SMA-Direktquelle nennt den bestätigten `group_bind`-Nachtlauf und warnt vor Wildcard-Modi.
- Diagnosepaket-Summary ergänzt eine einfache Socket-Bewertung:
  - `OK_GROUP_BIND` bei `group_bind`/Gruppen-Bind.
  - `WILDCARD_BIND_RISK` bei Wildcard-Bind oder aktivem `SO_REUSEPORT`.
  - zusätzliche Kurzbewertung für ausgewähltes Gerät, Paket-Rate und Paketlücken.

## Empfohlene Konfiguration im getesteten Setup

```text
GRID_METER_SOURCE=sma_energy_meter_udp
SMA_ENERGY_METER_GROUP=239.12.255.254
SMA_ENERGY_METER_PORT=9522
SMA_ENERGY_METER_INTERFACE=eth0
SMA_ENERGY_METER_SUSY_ID=372
SMA_ENERGY_METER_SERIAL=3011954105
SMA_ENERGY_METER_SOCKET_MODE=group_bind
SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS=5
ZENDURE_LOCAL_API_ENABLED=false
ZENDURE_LOCAL_API_USE_FOR_TELEMETRY=false
```

## Empfohlene Diagnose-Settings

```text
FILE_LOG_ENABLED=true
SMA_ENERGY_METER_LOG_DIAGNOSTICS=true
SMA_ENERGY_METER_LOG_INTERVAL_SECONDS=60
SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS=5
```

`DEBUG=true` ist nur für kurze Live-Fehlersuche nötig, wenn die `[SMA_DIAG]`-Zeilen zusätzlich im systemd-Journal sichtbar sein sollen. Für spätere Diagnosepakete reicht normalerweise Datei-Logging.

## Nicht geändert

- Keine Änderung an AUTO-Regelstrategie.
- Keine Änderung an Restüberschuss-Ernte Entry/Stay/Exit.
- Keine Änderung an Cross-Charge-Regelwirkung.
- Keine Änderung an Nachtmodus-Regelwirkung.
- Keine Änderung an Zendure-MQTT-Kommandostruktur.
- Keine Änderung an Zendure-MQTT-Topicstruktur.
- Kein Entfernen der Shelly-kompatiblen HTTP-Quelle.
- Kein automatischer Socket-Modus-Wechsel zur Laufzeit.
- Keine Änderung an finaler Excel-Lernsimulation.
