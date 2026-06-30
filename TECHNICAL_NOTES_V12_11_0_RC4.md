# Technical Notes V12.11.0-RC4

V12.11.0-RC4 ist eine Integrations- und Diagnose-Nacharbeit zu V12.11.0-RC3. Der Live-Regelalgorithmus, Nachtmodus, Cross-Charge-Logik, Restüberschuss-Ernte, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

## 1. Anlass

Im Live-Test mit EVCC, UniMeter und ZEC auf demselben Raspberry Pi zeigte sich, dass drei parallele SMA-Speedwire-/Energy-Meter-Listener auf `239.12.255.254:9522` EVCC-Messwerte stören können. Mit gestopptem UniMeter liefen EVCC und ZEC mit direkter SMA-Quelle stabil. Außerdem zeigte die Statuskarte „Netzleistung“ weiterhin die historische Quelle `Shelly/UniMeter`, obwohl ZEC bereits `GRID_METER_SOURCE=sma_energy_meter_udp` nutzte.

## 2. Änderungen

- Der SMA-Multicast-Listener setzt `SO_REUSEPORT` nicht mehr standardmäßig. Für passives Multicast-Mithören soll jeder kompatible lokale Listener dieselben Datagramme erhalten; Lastverteilungs- oder Koexistenznebeneffekte durch `SO_REUSEPORT` werden vermieden.
- Die aktive Netzleistungsquelle wird in Status, State und Measurement dynamisch geführt:
  - `SMA Home Manager direkt (UDP)` bei `GRID_METER_SOURCE=sma_energy_meter_udp`,
  - `Shelly-kompatible HTTP-Quelle` bei `GRID_METER_SOURCE=shelly_http`.
- V4-Measurement schreibt dadurch `grid_power_source=SMA` bei aktiver SMA-Direktquelle statt fälschlich `UNIMETER`.
- UI- und Settings-Texte wurden von UniMeter als Primärbegriff auf Shelly-/Shelly-kompatible HTTP-Quelle neutralisiert. Die Shelly-kompatible Quelle bleibt dauerhaft erhalten.
- Die lokale Zendure-API-Telemetrie ist in Defaults/Beispielkonfiguration deaktiviert und bleibt eindeutig abschaltbar.
- Die lokale Zendure-API erhält Fehler-Backoff: Fehlgeschlagene `/properties/report`-Abfragen zählen als Pollversuch und sperren weitere zyklische Abfragen für `ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS` Sekunden.

## 3. Betriebsbewertung

Empfohlener Zielpfad im getesteten Setup:

```text
UniMeter deaktiviert
GRID_METER_SOURCE=sma_energy_meter_udp
SMA_ENERGY_METER_INTERFACE=eth0
SMA_ENERGY_METER_SUSY_ID=372
SMA_ENERGY_METER_SERIAL=3011954105
ZENDURE_LOCAL_API_USE_FOR_TELEMETRY=false
```

UniMeter sollte nicht deinstalliert werden, solange Rollback gewünscht ist. Wenn es nur für ZEC lief, kann der systemd-Dienst deaktiviert werden, damit er nach Reboot nicht wieder startet.

## 4. Nicht geändert

- keine Änderung an AUTO-Regelstrategie,
- keine Änderung an Nachtentladung,
- keine Änderung an Cross-Charge,
- keine Änderung an MQTT-Kommandostruktur,
- keine Änderung an Zendure-MQTT-Topicstruktur,
- keine Änderung an finaler Excel-Lernsimulation.
