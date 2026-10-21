# Technical Notes V12.11.0-RC5

V12.11.0-RC5 ist ein Hotfix-/Diagnoserelease auf Basis von RC4. Der Live-Regelalgorithmus, Nachtmodus, Cross-Charge-Logik, Restüberschuss-Ernte, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

## 1. Anlass

Der Live-Test von RC4 zeigte mit gestopptem UniMeter erneut EVCC-SMA-Fehler (`login failed: no packet received in timeout`, `pv 1/2 outdated`). RC3 war im gleichen Setup stabil. Der auffällige Unterschied war das in RC4 entfernte best-effort `SO_REUSEPORT` beim SMA-Multicast-Socket.

RC5 stellt deshalb das RC3-kompatible Socketverhalten als Default wieder her und ergänzt Diagnoseoptionen, damit künftige Koexistenztests mit EVCC, UniMeter oder weiterer SMA-Speedwire-Software nachvollziehbar im Status und Runtime-Log bewertet werden können.

## 2. Änderungen

- Neuer Expertenparameter `SMA_ENERGY_METER_SOCKET_MODE`:
  - `rc3_compatible` = Default, `SO_REUSEADDR` + best-effort `SO_REUSEPORT`, Wildcard-Bind, Multicast-Join auf Interface/IP.
  - `reuseaddr_only` = RC4-Testpfad ohne `SO_REUSEPORT`.
  - `unimeter_like` = Diagnosepfad ohne `IP_MULTICAST_IF`, näher an einfachem passiven Join.
  - `group_bind` = Diagnosepfad mit Bind auf Multicast-Gruppe.
- Default ist wieder `rc3_compatible`, weil dieser Modus im Live-Test mit EVCC + ZEC stabil war.
- Neue SMA-Paketlücken-Diagnose:
  - `SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS`, Default 5 s.
  - Status zeigt letzte Paketlücke, maximale Paketlücke, letzte große Paketlücke und Paket-/Minutenrate.
- Neue Runtime-Log-Diagnose:
  - `SMA_ENERGY_METER_LOG_DIAGNOSTICS` aktiviert periodische `[SMA_DIAG]`-Zeilen.
  - `SMA_ENERGY_METER_LOG_INTERVAL_SECONDS` steuert das Intervall.
  - Die Meldungen landen im Runtime-Log, wenn zusätzlich `FILE_LOG_ENABLED=true` gesetzt ist.
  - `DEBUG=true` spiegelt diese Zeilen zusätzlich auf stdout/systemd journal.
- Die Statuskarte `SMA Direktquelle` zeigt Socket-Modus, Bind-Adresse, Reuse-Optionen, Multicast-IF, Paketlücken und erkannte Geräte.
- Die Option `SMA_ENERGY_METER_PASSIVE_ENABLED` wurde fachlich umbenannt zu `SMA-Direktquelle zusätzlich passiv beobachten`.
  - Bei `GRID_METER_SOURCE=sma_energy_meter_udp` wird der SMA-Listener automatisch aktiviert.
  - Bei `GRID_METER_SOURCE=shelly_http` aktiviert die Option nur die zusätzliche passive Vergleichsdiagnose.
- Das Diagnosepaket nimmt nun zusätzlich auf:
  - `status_snapshot.json`, falls die lokale Status-API erreichbar ist,
  - `SMA_DIAGNOSTICS_SUMMARY.txt`, kompakter Auszug relevanter SMA-Diagnosefelder,
  - `sma_runtime_events.txt`, gefilterte Runtime-Log-Zeilen zu `SMA_DIAG`/SMA-Ereignissen.

## 3. Empfohlene Diagnose-Konfiguration

Für normalen stabilen Betrieb im getesteten Setup:

```text
GRID_METER_SOURCE=sma_energy_meter_udp
SMA_ENERGY_METER_INTERFACE=eth0
SMA_ENERGY_METER_SUSY_ID=<SMA-SUSY-ID>
SMA_ENERGY_METER_SERIAL=<SMA-SERIENNUMMER>
SMA_ENERGY_METER_SOCKET_MODE=rc3_compatible
ZENDURE_LOCAL_API_USE_FOR_TELEMETRY=false
```

Für gezielte SMA-Koexistenzdiagnose zusätzlich:

```text
FILE_LOG_ENABLED=true
SMA_ENERGY_METER_LOG_DIAGNOSTICS=true
SMA_ENERGY_METER_LOG_INTERVAL_SECONDS=30
SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS=5
```

Optional nur für kurze Tests:

```text
DEBUG=true
```

`DEBUG=true` ist nicht für Dauerbetrieb nötig. Für spätere Diagnosepakete reicht normalerweise `FILE_LOG_ENABLED=true` plus `SMA_ENERGY_METER_LOG_DIAGNOSTICS=true`.

## 4. Nicht geändert

- keine Änderung an AUTO-Regelstrategie,
- keine Änderung an Nachtentladung,
- keine Änderung an Cross-Charge,
- keine Änderung an Restüberschuss-Ernte Entry/Stay/Exit,
- keine Änderung an Zendure-MQTT-Kommandostruktur,
- keine Änderung an Zendure-MQTT-Topicstruktur,
- keine Entfernung der Shelly-kompatiblen HTTP-Quelle,
- keine Änderung an finaler Excel-Lernsimulation.
